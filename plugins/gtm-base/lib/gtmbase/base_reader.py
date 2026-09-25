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
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import read_text
from .gitcmd import GitRunner, nul_fields, runner_or_default

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


# The code a file gets when the same entry sits in both folders saying two
# different things. Nothing chooses between them, because a reader that picks
# one is a reader that quietly throws the other away.
CODE_IN_BOTH_FOLDERS = "same-change-in-both-folders"
# The same identifier written twice inside one folder. It is its own code
# because it is a different thing to deal with: one of the two files is
# almost certainly a copy somebody made and forgot, and neither the folder
# nor a migration can tell which.
CODE_TWICE_IN_ONE_FOLDER = "same-change-twice-in-one-folder"
# A file whose name is not the identifier written inside it. Everything
# that goes looking for one change looks for a file named after it, so a
# file named anything else is a change half the product cannot find.
CODE_NAME_IS_NOT_THE_ID = "the-file-name-is-not-the-change-it-holds"

# The two folders a base may hold entries in, newest layout first. Only the
# first is ever written to. The second is what a base written before the
# rename holds, and it is read so that no entry is ever hidden, whatever a
# migration did or did not manage to finish.
ENTRY_DIRS = (constants.CHANGES_DIR, constants.LEGACY_CHANGES_DIR)


def _what_it_says(entry) -> tuple:
    """Everything one context change says, as plain values.

    Two copies are compared on this rather than on the text a writer would
    produce for them. Writing one out can fail on a value a reader accepted,
    such as a comma inside an affected path, and a reader that cannot read a
    base because one entry cannot be written back out is a reader that breaks
    the review, the confirm step, and the whole check at once.

    The one definition lives in `formats`, because the rename checks itself
    against it and two definitions of what a change says would be two answers
    to the same question.
    """
    return formats.entry_values(entry)


def entry_path_and_text(root: str, entry_id: str):
    """Where one context change is written on this base, and what it says.

    Both folders are looked in, the one written today first, because a base
    may hold either while a migration has not been run or a copy from before
    it came back. What comes back is the path relative to the base and the
    text, or a pair of Nones when no folder holds it.
    """
    for folder_name in ENTRY_DIRS:
        relative = folder_name + "/" + entry_id + ".md"
        text = read_text(os.path.join(root, relative.replace("/", os.sep)))
        if text is not None:
            return relative, text
    return None, None


def written_twice_about(root: str, base_id: str, path: str, today, runner=None):
    """The one context change about this document that disagrees with itself.

    It comes back as (the change's identifier, the files holding it), or None
    when there is no such change. It is here rather than in each caller
    because four different steps have to refuse the same thing, and four
    answers to one question is how one of them ends up not refusing.
    """
    from . import stale

    try:
        inputs = read_base(
            root, base_id, runner=runner, today=today, record_dropped=False
        )
        report = stale.compute(
            today=today,
            settings=inputs.settings,
            files=inputs.files,
            ledger=inputs.ledger,
            confirmations=inputs.confirmations,
            corrections=inputs.corrections,
            seat=inputs.seat,
            owner_email=None,
        )
    except (GtmBaseError, OSError):
        # Nothing can be said about a base that cannot be read, and a refusal
        # invented here would be a refusal nobody could act on.
        return None
    for conflict in report.conflicts:
        if path in conflict.affects:
            return conflict.entry_id, list(conflict.paths)
    return None


def where_to_write_the_entry(base_root: str, entry_id: str) -> str:
    """Where one context change belongs on this base, as a path.

    A base that has not been updated yet holds its changes in the older
    folder. Writing a second copy of one into the newer folder would leave
    two files with one identifier saying two different things, which is the
    one state nothing here can resolve. So a change the base already holds is
    written where it already is, and only a change nobody has written down
    goes in the folder everything is written to today.
    """
    relative, _text = entry_path_and_text(base_root, entry_id)
    if relative is not None:
        return relative
    return constants.CHANGES_DIR + "/" + entry_id + ".md"


def _read_entry_folder(root: str, folder_name: str):
    """Every file in one folder of entries, parsed or with the reason it was not."""
    read = []
    folder = os.path.join(root, folder_name.replace("/", os.sep))
    if not os.path.isdir(folder):
        return read
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        relative = folder_name + "/" + name
        text = read_text(os.path.join(folder, name))
        if text is None:
            read.append((relative, None, None, "unreadable"))
            continue
        try:
            entry = formats.ChangeEntry.parse(text)
        except (ValidationError, PathError) as failure:
            read.append((relative, None, text, failure.code))
            continue
        if name != entry.id + ".md":
            # Everything that looks one change up looks for a file named
            # after it, so a file named anything else is a change half of
            # this product cannot find. It is reported rather than read.
            read.append((relative, None, text, CODE_NAME_IS_NOT_THE_ID))
            continue
        read.append((relative, entry, text, None))
    return read


def ledger(
    root: str,
    base_id: str,
    today: datetime.date,
    collect: Optional[List[dict]] = None,
) -> "List[stale.LedgerInput]":
    """Every context change the base holds, with any path that leaves it dropped.

    Both folders are read and joined by the entry's own identifier, so an
    entry is never hidden by which folder it happens to sit in. One entry
    comes back per identifier. An identifier that sits in both folders saying
    two different things comes back as one problem naming it, and neither
    version is used, because choosing between them is not a reader's call.

    A refused path is normally recorded in this seat's own files as it is
    found. When the caller hands in a list, the refusals are put in that list
    and nothing is written, which is what lets a run that is only looking leave
    this seat's folder exactly as it was.
    """
    # Everything both folders hold, in the order it was read, so the answer is
    # the same on every run. For each identifier the first copy read is the one
    # that is kept, and a later copy of it only ever says whether the two
    # disagree.
    read: List[tuple] = []
    kept_by_id: "Dict[str, dict]" = {}
    for folder_name in ENTRY_DIRS:
        for relative, entry, _text, error in _read_entry_folder(root, folder_name):
            if entry is None:
                read.append(("problem", relative, error, None))
                continue
            # Two copies are the same entry when they say the same thing,
            # whichever spelling of the settings each was written with, so a
            # migrated copy and the one it was migrated from agree.
            said = _what_it_says(entry)
            held = kept_by_id.get(entry.id)
            if held is None:
                kept_by_id[entry.id] = {
                    "said": said,
                    "conflict": None,
                    "folder": folder_name,
                    "affects": list(entry.affects),
                    "copies": [relative],
                }
                read.append(("entry", relative, None, entry))
                continue
            held["copies"].append(relative)
            for path in entry.affects:
                if path not in held["affects"]:
                    held["affects"].append(path)
            if said == held["said"]:
                continue
            # Two files, one identifier, two different things said. Which of
            # the two problems it is depends on whether they sit in one folder
            # or in both, and the two are dealt with differently.
            held["conflict"] = (
                CODE_TWICE_IN_ONE_FOLDER
                if folder_name == held["folder"]
                else CODE_IN_BOTH_FOLDERS
            )
            read.append(("problem-copy", relative, held["conflict"], entry))

    # A file nothing can read, named after a change we did read somewhere
    # else, is two copies of one change and not one unnamed problem. Which of
    # the two is right is the person's to say, so it is named as a change
    # written down twice rather than counted as something unreadable.
    for what, relative, _error, _entry in read:
        if what != "problem":
            continue
        name = relative.split("/")[-1]
        if not name.endswith(".md"):
            continue
        held = kept_by_id.get(name[: -len(".md")])
        if held is not None:
            held["conflict"] = held["conflict"] or CODE_IN_BOTH_FOLDERS
            if relative not in held["copies"]:
                held["copies"].append(relative)

    entries: List[stale.LedgerInput] = []
    for what, relative, error, entry in read:
        if what == "problem":
            name = relative.split("/")[-1]
            entry_id = name[: -len(".md")] if name.endswith(".md") else ""
            held = kept_by_id.get(entry_id)
            if held is not None and held["conflict"]:
                entries.append(
                    stale.LedgerInput(
                        None,
                        relative,
                        held["conflict"],
                        entry_id=entry_id,
                        affects=held["affects"],
                    )
                )
                continue
            entries.append(stale.LedgerInput(None, relative, error))
            continue
        held = kept_by_id[entry.id]
        if what == "problem-copy":
            entries.append(
                stale.LedgerInput(
                    None,
                    relative,
                    held["conflict"],
                    entry_id=entry.id,
                    affects=held["affects"],
                )
            )
            continue
        if held["conflict"]:
            entries.append(
                stale.LedgerInput(
                    None,
                    relative,
                    held["conflict"],
                    entry_id=entry.id,
                    affects=held["affects"],
                )
            )
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


class AuthorsUnavailable(GtmBaseError):
    """Who wrote the lines could not be read, so nothing may be concluded.

    An empty answer and an unreadable answer mean opposite things here. Empty
    says nobody owns any of these lines, which makes every confirmation in the
    file count for nothing and every document it settles look out of date.
    Unreadable says the question was not answered. Handing the first back for
    the second is how a settled document gets flagged and somebody is asked to
    confirm something they already confirmed.
    """


def line_authors(root: str, relative: str, git: GitRunner) -> "Dict[int, str]":
    """Who added each line of one file, which is the only identity we trust.

    A file nobody has saved yet has no authors and that is an answer. A read
    that failed or ran out of time is not an answer, and it raises rather than
    coming back looking like the first one.
    """
    result = git.run(
        ["blame", "--line-porcelain", "--", relative],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not result.ok:
        raise AuthorsUnavailable(
            "who wrote the lines of %s could not be read" % relative,
            code="unreadable",
        )
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
    """Every confirmation line, paired with the person who added it.

    It raises when who wrote the lines cannot be read, because a confirmation
    with nobody behind it settles nothing, and a run that quietly treated one
    as unowned would flag documents their owners had already confirmed.
    """
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
            # Names end in a NUL and come out as they are, so a document with
            # an accent or a space in its name is matched by its real name.
            shown = git.run(
                ["show", "--name-only", "--format=", "-z", commit],
                cwd=root,
                timeout=LOCAL_TIMEOUT_SECONDS,
            )
            if shown.ok:
                co_modified = nul_fields(shown.stdout)
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
