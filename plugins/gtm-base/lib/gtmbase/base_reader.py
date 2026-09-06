"""Reading one base into the values the stale library works on.

The stale library never touches a disk, runs git, or looks at a clock. This is
the one module that does all three on its behalf, so the hook at the start of a
session and the stale check both read a base exactly the same way and can never
reach different conclusions about the same folder.

What it reads, in order: the map's two settings, every context file with its
owners and its source dates, every decision, every confirmation line with the
address of whoever added it, and every accepted record of a correction with the
files its own change touched, the one hash over those files, and the address and
day of whoever accepted it.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Dict, List, Optional, Sequence

from . import constants, formats, ids, paths, stale, state, validate
from .errors import PathError, ValidationError
from .fsutil import read_text
from .gitcmd import GitRunner, runner_or_default

# How long a local git call made while reading a base may take.
LOCAL_TIMEOUT_SECONDS = 5

_DATE_IN_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")
_BLAME_HEADER = re.compile(r"^[0-9a-f]{7,40} \d+ (\d+)(?: \d+)?$")

# Codes this module records. None of them is ever shown to a person as it is.
CODE_NO_MAP = "missing-map"
CODE_NO_EMAIL = "no-repo-email"


class BaseInputs(object):
    """Everything one base says about itself, ready for the stale library."""

    __slots__ = (
        "settings",
        "files",
        "ledger",
        "confirmations",
        "corrections",
        "seat",
        "seat_email",
        "default_branch",
        "has_remote",
        "codes",
        "map_text",
        "dropped_this_run",
    )

    def __init__(
        self,
        settings,
        files,
        ledger,
        confirmations,
        corrections,
        seat,
        seat_email=None,
        default_branch=None,
        has_remote=False,
        codes=None,
        map_text="",
        dropped_this_run=None,
    ):
        self.settings = settings
        self.files = list(files)
        self.ledger = list(ledger)
        self.confirmations = list(confirmations)
        self.corrections = list(corrections)
        self.seat = seat
        self.seat_email = seat_email
        self.default_branch = default_branch
        self.has_remote = bool(has_remote)
        self.codes = list(codes or [])
        self.map_text = map_text
        # The paths a decision named that this run refused, when the caller
        # asked for them rather than for them to be recorded.
        self.dropped_this_run = list(dropped_this_run or [])

    @property
    def by_path(self) -> "Dict[str, stale.ContextFileInfo]":
        return {info.path: info for info in self.files}

    def entry_files(self) -> "Dict[str, str]":
        """The file each decision was written down in, keyed by its identifier."""
        found: Dict[str, str] = {}
        for item in self.ledger:
            if item.entry is not None and item.entry.id:
                found[item.entry.id] = item.path or ""
        return found

    def __repr__(self) -> str:
        return "BaseInputs(files=%d, ledger=%d)" % (len(self.files), len(self.ledger))


# --- The pieces -------------------------------------------------------------


def map_text(root: str) -> str:
    return read_text(os.path.join(root, constants.MAP_PATH)) or ""


def settings_of(text: str) -> "stale.MapSettings":
    """The two numbers the map is allowed to set, or the defaults."""
    try:
        return stale.MapSettings.coerce(validate.read_map_settings(text))
    except ValidationError:
        return stale.MapSettings()


def repo_email(root: str, git: GitRunner) -> Optional[str]:
    """The address this folder records for the person working in it."""
    result = git.run(
        ["config", "--local", "--get", "user.email"],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not result.ok:
        return None
    value = result.out()
    return value if validate.is_valid_email(value) else None


def newest_date_in(value) -> Optional[str]:
    """The latest day named anywhere in a frontmatter value, or nothing."""
    items = value if isinstance(value, list) else [value]
    found = []
    for item in items:
        match = _DATE_IN_TEXT.search(str(item or ""))
        if match:
            found.append(match.group(0))
    return max(found) if found else None


def context_files(root: str) -> "List[stale.ContextFileInfo]":
    """Every context file the base holds, with its owners and its dates."""
    files: List[stale.ContextFileInfo] = []
    context_root = os.path.join(root, constants.CONTEXT_DIR)
    for dirpath, dirnames, filenames in os.walk(context_root):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            relative = os.path.relpath(full, root).replace(os.sep, "/")
            text = read_text(full)
            if text is None:
                continue
            try:
                block, _body = formats.split_document(text)
                fields = formats.parse_frontmatter(block)
            except (ValidationError, PathError):
                fields = {}
            try:
                owners = validate.validate_owner(fields.get("owner"))
            except ValidationError:
                owners = []
            try:
                sources_date = newest_date_in(fields.get("sources"))
            except Exception:
                sources_date = None
            files.append(
                stale.ContextFileInfo(
                    path=relative,
                    owners=owners,
                    exists=True,
                    sources_date=sources_date,
                    status=str(fields.get("status") or ""),
                    kind=str(fields.get("kind") or ""),
                )
            )
    return files


def ledger(
    root: str,
    base_id: str,
    today: datetime.date,
    collect: Optional[List[dict]] = None,
) -> "List[stale.LedgerInput]":
    """Every decision the base holds, with any path that leaves it dropped.

    A refused path is normally recorded in this seat's own files as it is
    found. When the caller hands in a list, the refusals are put in that list
    and nothing is written, which is what lets a run that is only looking leave
    this seat's folder exactly as it was.
    """
    entries: List[stale.LedgerInput] = []
    folder = os.path.join(root, constants.DECISIONS_DIR)
    if not os.path.isdir(folder):
        return entries
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        relative = constants.DECISIONS_DIR + "/" + name
        text = read_text(os.path.join(folder, name))
        if text is None:
            entries.append(stale.LedgerInput(None, relative, "unreadable"))
            continue
        try:
            entry = formats.LedgerEntry.parse(text)
        except (ValidationError, PathError) as failure:
            entries.append(stale.LedgerInput(None, relative, failure.code))
            continue
        kept = []
        for path in entry.affects:
            try:
                kept.append(paths.canonical_context_path(root, path))
            except (PathError, ValidationError):
                if collect is None:
                    state.append_dropped_path(
                        base_id, path, "dropped-path", entry.id, today
                    )
                else:
                    collect.append(
                        {
                            "path": path,
                            "code": "dropped-path",
                            "entry_id": entry.id,
                            "day": today,
                        }
                    )
        entry.affects = kept
        entries.append(stale.LedgerInput(entry, relative, None))
    return entries


def line_authors(root: str, relative: str, git: GitRunner) -> "Dict[int, str]":
    """Who added each line of one file, which is the only identity we trust."""
    result = git.run(
        ["blame", "--line-porcelain", "--", relative],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not result.ok:
        return {}
    authors: Dict[int, str] = {}
    current: Optional[int] = None
    for line in result.stdout.split("\n"):
        header = _BLAME_HEADER.match(line.strip())
        if header:
            current = int(header.group(1))
            continue
        if line.startswith("author-mail ") and current is not None:
            authors[current] = line[len("author-mail ") :].strip().strip("<>")
    return authors


def confirmations(root: str, git: GitRunner) -> "List[stale.ConfirmationRecord]":
    """Every confirmation line, paired with the person who added it."""
    records: List[stale.ConfirmationRecord] = []
    folder = os.path.join(root, constants.CONFIRMATIONS_DIR)
    if not os.path.isdir(folder):
        return records
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        relative = constants.CONFIRMATIONS_DIR + "/" + name
        text = read_text(os.path.join(folder, name))
        if text is None:
            continue
        authors = line_authors(root, relative, git)
        for number, raw in enumerate(text.split("\n"), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                parsed = formats.ConfirmationLine.parse(line)
            except (ValidationError, PathError):
                continue
            records.append(
                stale.ConfirmationRecord(parsed, authors.get(number), None)
            )
    return records


def _context_paths_of(correction) -> List[str]:
    """The files under the context folder a record lists, in its own order."""
    prefix = constants.CONTEXT_DIR + "/"
    return [
        path
        for path in getattr(correction, "touched_paths", []) or []
        if isinstance(path, str) and path.startswith(prefix)
    ]


def hash_at_commit(
    root: str, commit: str, correction, git: GitRunner
) -> Optional[str]:
    """The one hash over what an accepted change left behind.

    Every context file the record lists is read as that change left it, the
    texts are put end to end in the order the record lists them, and the whole
    lot is hashed. One file that cannot be read makes the answer nothing at all,
    because a hash over part of the files would say the record matched when
    nobody can tell whether it does.
    """
    parts: List[str] = []
    for path in _context_paths_of(correction):
        shown = git.run(
            ["show", commit + ":" + path], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
        )
        if not shown.ok:
            return None
        parts.append(shown.stdout)
    if not parts:
        return None
    return ids.content_hash("".join(parts))


def accepted_by(
    root: str, relative: str, default_branch: Optional[str], git: GitRunner
):
    """Who brought one file onto the shared line of work, and on what day.

    The shared line of work is read along its own first parent only, so the
    change that put the file there is the one the team accepted rather than the
    one somebody wrote on a side branch. Three shapes all end up here. When a
    proposal is accepted with a change of its own, that change is the answer,
    and on GitHub its author is the person who pressed the button, so this is
    the identity of whoever accepted it. When a proposal is squashed into one
    change, that change is the answer. When it goes on the end with no change
    of its own, the proposal's own change is the answer, and whoever accepted
    it cannot be told apart from whoever wrote it.

    Nothing at all comes back when the file is not on that line of work yet.
    """
    args = ["log", "--first-parent", "--format=%H%x1f%ae%x1f%ad", "--date=short"]
    if default_branch:
        args.append(default_branch)
    args.extend(["--", relative])
    found = git.run(args, cwd=root, timeout=LOCAL_TIMEOUT_SECONDS)
    if not found.ok:
        return None, None
    for line in found.stdout.split("\n"):
        parts = line.strip().split("\x1f")
        if len(parts) != 3:
            continue
        _commit, email, day = (part.strip() for part in parts)
        if not email or not _DATE_IN_TEXT.match(day):
            continue
        return email, day
    return None, None


def corrections(
    root: str, git: GitRunner, default_branch: Optional[str] = None
) -> "List[stale.CorrectionRecord]":
    """Every accepted record, with what its own change touched and its hash.

    Each record also carries the address and the day of whoever brought it onto
    the shared line of work, because an owner accepting a change is that owner
    saying the file is right.
    """
    records: List[stale.CorrectionRecord] = []
    if default_branch is None:
        default_branch = _default_branch(root, git)
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    if not os.path.isdir(folder):
        return records
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        relative = constants.CORRECTIONS_DIR + "/" + name
        text = read_text(os.path.join(folder, name))
        if text is None:
            continue
        try:
            correction = formats.CorrectionsFile.parse(text)
        except (ValidationError, PathError):
            continue
        introduced = git.run(
            ["log", "--diff-filter=A", "--format=%H", "--", relative],
            cwd=root,
            timeout=LOCAL_TIMEOUT_SECONDS,
        )
        commits = [
            line.strip() for line in introduced.stdout.split("\n") if line.strip()
        ]
        commit = commits[-1] if introduced.ok and commits else None
        co_modified: List[str] = []
        hashed = None
        if commit:
            shown = git.run(
                ["show", "--name-only", "--format=", commit],
                cwd=root,
                timeout=LOCAL_TIMEOUT_SECONDS,
            )
            if shown.ok:
                co_modified = [
                    line.strip() for line in shown.stdout.split("\n") if line.strip()
                ]
            hashed = hash_at_commit(root, commit, correction, git)
        merged_by, merged_on = accepted_by(root, relative, default_branch, git)
        records.append(
            stale.CorrectionRecord(
                correction,
                commit,
                co_modified,
                hashed,
                merged_by_email=merged_by,
                merged_on=merged_on,
            )
        )
    return records


def seat_input(base_id: str, has_remote: bool) -> "stale.SeatInput":
    """What this one seat remembers, which is never shared with the team."""
    dropped, _a = state.load_dropped_paths(base_id)
    asked, _b = state.load_asked(base_id)
    suppressions, _c = state.load_suppressions(base_id)
    dismissals, _d = state.load_dismissals(base_id)
    return stale.SeatInput(
        dropped_paths=dropped,
        asked_log=asked,
        suppressions=suppressions,
        ledger_behind_dismissed_until=dismissals.get(
            "ledger_behind_dismissed_until"
        ),
        has_remote=has_remote,
    )


def missing_required(files: "Dict[str, stale.ContextFileInfo]") -> List[str]:
    """The files a base needs before anyone can be asked to confirm anything."""
    missing = []
    for path in constants.REQUIRED_CONTEXT_FILES:
        info = files.get(path)
        if info is None or not info.present:
            missing.append(path)
    return missing


# --- The whole base ---------------------------------------------------------


def read_base(
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    today: Optional[datetime.date] = None,
    record_dropped: bool = True,
) -> BaseInputs:
    """Read one base into the values the stale library works on.

    Reading normally records a refused path in this seat's own files. A caller
    that is only looking asks for that not to happen, and gets the refusals
    back on the result instead.
    """
    git = runner_or_default(runner)
    day = today or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    codes: List[str] = []
    dropped: Optional[List[dict]] = None if record_dropped else []

    text = map_text(base_root)
    if not text:
        codes.append(CODE_NO_MAP)
    settings = settings_of(text)

    has_remote = paths.remote_url(base_root, runner=git) is not None
    default = _default_branch(base_root, git)
    email = repo_email(base_root, git)
    if email is None:
        codes.append(CODE_NO_EMAIL)

    return BaseInputs(
        settings=settings,
        files=context_files(base_root),
        ledger=ledger(base_root, base_id, day, collect=dropped),
        confirmations=confirmations(base_root, git),
        corrections=corrections(base_root, git, default),
        seat=seat_input(base_id, has_remote),
        seat_email=email,
        default_branch=default,
        has_remote=has_remote,
        codes=codes,
        map_text=text,
        dropped_this_run=dropped,
    )


def _default_branch(base_root: str, git: GitRunner) -> Optional[str]:
    """The line of work the team shares, as this folder understands it."""
    head = git.run(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        cwd=base_root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if head.ok and head.out():
        return head.out().split("/", 1)[-1]
    for candidate in ("main", "master"):
        exists = git.run(
            ["show-ref", "--verify", "--quiet", "refs/heads/" + candidate],
            cwd=base_root,
            timeout=LOCAL_TIMEOUT_SECONDS,
        )
        if exists.ok:
            return candidate
    return None


def entry_by_id(inputs: BaseInputs, entry_id: str):
    """One decision by its identifier, or nothing when the base holds none."""
    for item in inputs.ledger:
        if item.entry is not None and item.entry.id == entry_id:
            return item.entry
    return None


def usable_entries(inputs: BaseInputs) -> List["formats.LedgerEntry"]:
    """Every decision that could be read, in the order the base holds them."""
    return [item.entry for item in inputs.ledger if item.entry is not None]


def dropped_paths(base_id: str) -> Sequence[dict]:
    rows, _problems = state.load_dropped_paths(base_id)
    return rows
