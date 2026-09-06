"""Turning one staged proposal into a review anybody on the team can read.

The order matters, and every step is safe to repeat. The staged file is read
and checked, the two conditions that stop anything leaving this computer are
asked, everything the proposal would carry is read for things that must never
leave, and only then is a working folder made. The edits are applied there, the
decision and the record of what changed are written beside them, and the whole
lot is sent as one review.

Nothing here touches the person's own folder. A run that stops halfway leaves a
working folder behind, and the next run picks it up where it was.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from . import (
    constants,
    duplicate_check,
    formats,
    gate,
    ghcmd,
    ids,
    paths,
    push_conditions,
    scan,
    state,
    worktree,
)
from .errors import GitError, GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_text, ensure_dir, read_text, remove
from .gitcmd import GitRunner, runner_or_default
from .validate import find_marker, marker_line

# What a run can end as.
STATUS_OPENED = "opened"
STATUS_ALREADY_OPEN = "already-open"
STATUS_CLOSED_SKIPPED = "closed-skipped"
STATUS_MERGED_SKIPPED = "merged-skipped"
STATUS_REFUSED = "refused"
STATUS_CONFLICT = "conflict"
STATUS_RESUMED = "resumed"

# Codes recorded on the result. They are for the log, not for a person.
CODE_UNREADABLE = "staging-unreadable"
CODE_INVALID = "staging-invalid"
CODE_MAP_TARGET = "edit-targets-the-map"
CODE_FRONTMATTER_TARGET = "edit-targets-the-settings-block"
CODE_OUTSIDE_CONTEXT = "edit-outside-context"
CODE_NO_EDITS = "no-edits"
CODE_MISSING_FILE = "edit-file-missing"
CODE_HEADING_MISSING = "heading-missing"
CODE_MARKER_ENTRY = "marker-names-a-decision-with-none-carried"
CODE_ENTRY_MISMATCH = "decision-names-another-proposal"
CODE_NO_REMOTE = "no-shared-copy"
CODE_PUSH_FAILED = "send-failed"
CODE_REVIEW_FAILED = "review-not-opened"
CODE_REVIEW_UNREADABLE = "review-answer-unreadable"
CODE_AUTHOR_FALLBACK = "author-address-missing"
CODE_ALLOWLIST_REJECTED = scan.ALLOWLIST_REJECTED
CODE_COMMIT_REUSED = "saved-work-reused"
CODE_REVIEW_REUSED = "review-reused"
CODE_ROW_MISSING_SOURCE = "no-source-row"
CODE_GIT_FAILED = "git-failed"

# What the saved work in a working folder is called, so a repeat run knows it.
COMMIT_SUBJECT_PREFIX = "Proposal "
# How much of the summary the saved work's note carries.
COMMIT_SUMMARY_CHARS = 60
# How much of the summary the title of a review carries.
TITLE_SUMMARY_CHARS = 80

_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_PULL_NUMBER_RE = re.compile(r"/pull/(\d+)")
_WHITESPACE_RE = re.compile(r"\s+")


class ProposalResult(object):
    """How one run ended, in the terms the skill reports to the person."""

    __slots__ = (
        "status",
        "staging_id",
        "pr_number",
        "pr_url",
        "codes",
        "reasons",
        "branch",
        "written_paths",
    )

    def __init__(
        self,
        status,
        staging_id=None,
        pr_number=None,
        pr_url=None,
        codes=None,
        reasons=None,
        branch=None,
        written_paths=None,
    ):
        self.status = status
        self.staging_id = staging_id
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.codes = list(codes or [])
        self.reasons = list(reasons or [])
        self.branch = branch
        self.written_paths = list(written_paths or [])

    @property
    def opened(self) -> bool:
        return self.status in (STATUS_OPENED, STATUS_ALREADY_OPEN)

    def __repr__(self) -> str:
        return "ProposalResult(status=%r, pr_number=%r)" % (self.status, self.pr_number)


# --- Reading and checking the staged file ------------------------------------


def load_staging(path: str) -> "formats.ProposalStaging":
    """Read one staged proposal, or say plainly that it cannot be read."""
    text = read_text(path)
    if text is None:
        raise ValidationError(
            "GTM Base could not read the staged proposal at %s." % path,
            code=CODE_UNREADABLE,
        )
    if len(text.encode("utf-8", "replace")) > constants.MAX_ARTIFACT_BYTES:
        raise ValidationError(
            "That staged proposal is larger than GTM Base will read.",
            code=CODE_UNREADABLE,
        )
    return formats.ProposalStaging.parse(text).validate()


def check_edits(base_root: str, staging) -> List[Tuple[str, str]]:
    """Everything about the edits that stops the proposal before it starts.

    The map is out of bounds because it is what tells the assistant where
    everything lives. The settings block at the top of a file is out of bounds
    because it carries who owns the file and when it was last confirmed, and a
    proposal that could rewrite those could confirm itself.
    """
    reasons: List[Tuple[str, str]] = []
    if not staging.edits:
        reasons.append(
            (CODE_NO_EDITS, "This proposal changes nothing, so there is nothing to send.")
        )
    for edit in staging.edits:
        try:
            relative = paths.canonical_context_path(base_root, edit.path)
        except PathError:
            reasons.append(
                (
                    CODE_OUTSIDE_CONTEXT,
                    "A proposal may only change files in the context folder, and "
                    "this one names %s." % edit.path,
                )
            )
            continue
        if relative == constants.MAP_PATH:
            reasons.append(
                (
                    CODE_MAP_TARGET,
                    "A proposal may never change the map, which is the file that "
                    "says where everything lives.",
                )
            )
            continue
        heading = (edit.heading or "").strip()
        if not heading or not _HEADING_RE.match(heading):
            reasons.append(
                (
                    CODE_FRONTMATTER_TARGET,
                    "Every edit has to name the heading it changes, and %s is not "
                    "a heading." % (heading if heading else "an empty value"),
                )
            )
    return reasons


# --- Applying one edit -------------------------------------------------------


class ConflictError(GtmBaseError):
    """The file moved on, and the part this edit changes is no longer there."""


def _heading_level(line: str) -> int:
    match = _HEADING_RE.match(line)
    return len(match.group(1)) if match else 0


def frontmatter_end(lines: List[str]) -> int:
    """The line the body starts on, counting past the settings block."""
    if not lines or lines[0].strip() != formats.FRONTMATTER_FENCE:
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == formats.FRONTMATTER_FENCE:
            return index + 1
    return 0


def find_heading(lines: List[str], heading: str, start: int = 0) -> int:
    """Where a heading is, matched as a whole line and nothing else."""
    wanted = heading.strip()
    for index in range(start, len(lines)):
        if lines[index].strip() == wanted:
            return index
    return -1


def section_end(lines: List[str], index: int) -> int:
    """Where the part under a heading stops: at the next heading as big or bigger."""
    level = _heading_level(lines[index])
    for position in range(index + 1, len(lines)):
        found = _heading_level(lines[position])
        if found and found <= level:
            return position
    return len(lines)


def apply_edit(text: str, edit) -> str:
    """The file as this edit would leave it.

    A replacement keeps the heading and puts the new words under it, up to the
    next heading of the same size or bigger. An addition puts the new words at
    the end of the part that heading names, or at the end of the file when the
    heading is not there yet.
    """
    lines = text.split("\n")
    body_starts = frontmatter_end(lines)
    heading = (edit.heading or "").strip()
    block = [""] + edit.text.strip("\n").split("\n") + [""]
    index = find_heading(lines, heading, body_starts)

    if edit.op == "replace":
        if index < 0:
            raise ConflictError(
                "the heading is no longer in the file", code=CODE_HEADING_MISSING
            )
        stop = section_end(lines, index)
        result = lines[: index + 1] + block + lines[stop:]
    elif index >= 0:
        stop = section_end(lines, index)
        result = lines[:stop] + block + lines[stop:]
    else:
        result = lines + [""] + [heading] + block
    return "\n".join(result).rstrip("\n") + "\n"


# --- The pieces the proposal carries -----------------------------------------


def edited_paths(staging) -> List[str]:
    """The context files this proposal changes, in the order it names them."""
    from_edits: List[str] = []
    for edit in staging.edits:
        if edit.path not in from_edits:
            from_edits.append(edit.path)
    ordered = [path for path in staging.target_paths if path in from_edits]
    for path in from_edits:
        if path not in ordered:
            ordered.append(path)
    return ordered


def content_hash_for(worktree_path: str, ordered_paths: List[str]) -> str:
    """The hash of what the proposal leaves behind.

    It is taken over the finished text of every context file the proposal
    changes, one after another in the order the record of what changed lists
    them, so the same hash can be worked out again from the change itself when
    somebody comes to accept it. The record lists those same files first and in
    that same order, which is what makes the two agree.
    """
    parts = []
    for relative in ordered_paths:
        checked = paths.canonical_context_path(worktree_path, relative)
        text = read_text(os.path.join(worktree_path, checked))
        if text is None:
            raise ValidationError(
                "GTM Base could not read %s after changing it." % relative,
                code=CODE_MISSING_FILE,
            )
        parts.append(text)
    return ids.content_hash("".join(parts))


def summary_of(staging) -> str:
    """The short line that says what the proposal does, in the author's words."""
    try:
        body = formats.parse_pr_body(staging.pr_body)
    except ValidationError:
        return staging.staging_id
    return _WHITESPACE_RE.sub(" ", body.get("after") or "").strip()


def commit_subject(staging) -> str:
    """The note saved with the change, which a repeat run recognises."""
    return "%s%s: %s" % (
        COMMIT_SUBJECT_PREFIX,
        staging.staging_id,
        summary_of(staging)[:COMMIT_SUMMARY_CHARS].strip(),
    )


def review_title(staging) -> str:
    """The title a reviewer sees, in plain words and naming the file."""
    ordered = edited_paths(staging)
    where = ordered[0] if ordered else "the base"
    if len(ordered) > 1:
        where = "%s and %d more" % (where, len(ordered) - 1)
    return ("Proposed change to %s: %s" % (where, summary_of(staging)))[
        : TITLE_SUMMARY_CHARS + 60
    ].strip()


def ledger_entry_for(staging, today: datetime.date) -> "formats.LedgerEntry":
    """The decision this proposal carries, dated the day it was written down."""
    entry = formats.LedgerEntry.parse(staging.decision_block)
    if entry.id != staging.staging_id:
        raise ValidationError(
            "The decision in this proposal is named after a different proposal.",
            code=CODE_ENTRY_MISMATCH,
        )
    entry.written_on = today.isoformat()
    return entry.validate(today)


def corrections_for(
    staging,
    today: datetime.date,
    hash_value: str,
    touched: List[str],
    entry_id: Optional[str],
    source_id: Optional[str],
) -> "formats.CorrectionsFile":
    """The record of what changed, which is what says later that this was accepted."""
    body = formats.parse_pr_body(staging.pr_body)
    correction = formats.CorrectionsFile(
        kind="correction",
        date=today.isoformat(),
        staging_id=staging.staging_id,
        entry_id=entry_id,
        source_id=source_id,
        intake_path=staging.intake_path,
        mode="decision" if staging.decision_block else "none",
        third_party=bool(staging.third_party),
        content_hash=hash_value,
        correction_class="new-decision" if entry_id else "other",
        marker=marker_line(staging.staging_id, entry_id, source_id),
        touched_paths=list(touched),
        what_changed="Before: %s\n\nAfter: %s" % (body["before"], body["after"]),
        why=body["why"],
    )
    return correction.validate()


# --- Reading everything the proposal would carry ------------------------------


def scan_everything(staging, base_root: str, extra: Optional[List[str]] = None):
    """Read every piece of text the proposal would send, and report the classes.

    The value that matched is never carried out of here. A refusal names the
    kind of thing found and the piece of the proposal it was found in.
    """
    allowlist, code = scan.load_allowlist(base_root)
    hits = []
    pieces = [("the evidence", staging.excerpt), ("the proposal", staging.pr_body)]
    if staging.decision_block:
        pieces.append(("the decision", staging.decision_block))
    for number, edit in enumerate(staging.edits, start=1):
        pieces.append(("edit %d" % number, edit.text))
    for text in extra or []:
        pieces.append(("the note saved with the change", text))
    for context, text in pieces:
        hits.extend(scan.scan_text(text, allowlist, context))
    return hits, code


# --- The run -----------------------------------------------------------------


def _seat_session_id(base_id: str) -> Optional[str]:
    seat, _problems = state.load_seat(base_id)
    value = seat.get("session_id")
    return value if isinstance(value, str) and value else None


def _author(base_root: str, git: GitRunner) -> Tuple[str, str, List[str]]:
    """The name and address saved work is recorded under, and why."""
    name = git.run(["config", "--local", "--get", "user.name"], cwd=base_root)
    email = git.run(["config", "--local", "--get", "user.email"], cwd=base_root)
    if email.ok and email.out():
        return (
            (name.out() if name.ok and name.out() else constants.COMMIT_AUTHOR_FALLBACK_NAME),
            email.out(),
            [],
        )
    return (
        constants.COMMIT_AUTHOR_FALLBACK_NAME,
        constants.COMMIT_AUTHOR_FALLBACK_EMAIL,
        [CODE_AUTHOR_FALLBACK],
    )


def _last_subject(path: str, git: GitRunner) -> str:
    result = git.run(["log", "-1", "--format=%s"], cwd=path)
    return result.out() if result.ok else ""


def _row_proposal_id(base_id: str, source_id: Optional[str], staging_id: str):
    """The review already recorded for this proposal, if this seat wrote one."""
    if not source_id:
        return None
    index, _problems = state.load_index(base_id)
    row = index.get(source_id)
    if not row:
        return None
    for value in row.get("proposal_ids") or []:
        if str(value).startswith(staging_id + ":"):
            tail = str(value).split(":", 1)[1]
            return int(tail) if tail.isdigit() else None
    return None


def _record_row(base_id: str, source_id: Optional[str], staging_id: str, number, codes):
    if not source_id:
        codes.append(CODE_ROW_MISSING_SOURCE)
        return
    index, _problems = state.load_index(base_id)
    row = index.get(source_id) or {}
    proposals = [
        value
        for value in (row.get("proposal_ids") or [])
        if not str(value).startswith(staging_id + ":")
    ]
    proposals.append("%s:%s" % (staging_id, number if number is not None else "-"))
    staged = list(row.get("staging_ids") or [])
    if staging_id not in staged:
        staged.append(staging_id)
    state.upsert_row(
        base_id,
        source_id,
        proposal_ids=proposals,
        staging_ids=staged,
        status="processed",
    )


def retire(base_root: str, staging_path: str, staging_id: str) -> str:
    """Put the staged file where a proposal that is under review is kept."""
    folder = ensure_dir(os.path.join(base_root, constants.PROPOSALS_OPENED_DIR))
    destination = os.path.join(folder, staging_id + ".md")
    if os.path.abspath(staging_path) != os.path.abspath(destination):
        if os.path.isfile(staging_path):
            shutil.move(staging_path, destination)
    return destination


def _parse_review_answer(output: str) -> Tuple[Optional[int], Optional[str]]:
    """Read the answer to opening a review, whichever shape it arrives in.

    The real tool prints the web address of the new review. The stand-in used
    in tests prints the same facts as a small block of data. Both are read.
    """
    text = (output or "").strip()
    if not text:
        return None, None
    try:
        payload = json.loads(text)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        number = payload.get("number")
        url = payload.get("url")
        return (
            int(number) if isinstance(number, int) and not isinstance(number, bool) else None,
            str(url) if isinstance(url, str) else None,
        )
    for line in reversed(text.splitlines()):
        match = _PULL_NUMBER_RE.search(line)
        if match:
            return int(match.group(1)), line.strip()
    return None, None


def propose(
    staging_path: str,
    base_root: str,
    base_id: str,
    gh=None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
    allow_reproposal: bool = False,
    session_id: Optional[str] = None,
) -> ProposalResult:
    """Turn one staged proposal into a review, in the one order it happens in."""
    git = runner_or_default(runner)
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    codes: List[str] = []
    reasons: List[str] = []

    # 1. Read the staged file and check what it would change.
    try:
        staging = load_staging(staging_path)
    except GtmBaseError as failure:
        return ProposalResult(
            STATUS_REFUSED, codes=[failure.code or CODE_INVALID], reasons=[str(failure)]
        )
    edit_problems = check_edits(base_root, staging)
    if edit_problems:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[code for code, _ in edit_problems],
            reasons=[sentence for _, sentence in edit_problems],
        )

    marker = duplicate_check.marker_for(staging)
    parsed_marker = find_marker(marker)
    entry_id = parsed_marker[1] if parsed_marker else None
    source_id = parsed_marker[2] if parsed_marker else staging.source_id
    # A marker naming this proposal's own identifier as the decision means the
    # proposal creates that decision, so it has to carry it. A marker naming any
    # other decision means one the base already holds, quoted as evidence, and
    # the proposal must not carry a second copy of it.
    if entry_id == staging.staging_id and not staging.decision_block:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[CODE_MARKER_ENTRY],
            reasons=[
                "This proposal says it carries a decision, but no decision is "
                "written in it."
            ],
        )
    if entry_id and entry_id != staging.staging_id and staging.decision_block:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[CODE_ENTRY_MISMATCH],
            reasons=[
                "This proposal names a decision the base already holds and "
                "writes out a second copy of it, which it may not do."
            ],
        )

    # 2. The two conditions that stop anything leaving this computer.
    session = session_id if session_id is not None else _seat_session_id(base_id)
    blocked = push_conditions.check(base_id, session)
    if blocked:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[code for code, _ in blocked],
            reasons=[sentence for _, sentence in blocked],
        )

    # 3. Read everything the proposal would carry.
    subject = commit_subject(staging)
    hits, allowlist_code = scan_everything(staging, base_root, extra=[subject])
    if allowlist_code:
        codes.append(allowlist_code)
    if hits:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[hit.pattern_class for hit in hits],
            reasons=[hit.sentence() for hit in hits],
        )

    # 4. Has anybody already proposed this. A review on this proposal's own
    # line of work is this seat's own earlier run, which step 5 finishes.
    branch = constants.PROPOSAL_BRANCH_PREFIX + staging.staging_id
    duplicate = duplicate_check.check(
        staging, base_root, gh=gh, runner=git, own_branch=branch
    )
    codes.extend(duplicate.codes)
    if duplicate.kind == duplicate_check.KIND_MERGED:
        return ProposalResult(
            STATUS_MERGED_SKIPPED,
            staging_id=staging.staging_id,
            pr_number=duplicate.pr_number,
            pr_url=duplicate.pr_url,
            codes=codes,
            reasons=["This change is already part of the shared copy."],
        )
    if duplicate.kind == duplicate_check.KIND_OPEN:
        if source_id:
            state.upsert_row(
                base_id,
                source_id,
                status="processed-elsewhere",
                foreign_pr=duplicate.pr_number,
            )
        return ProposalResult(
            STATUS_ALREADY_OPEN,
            staging_id=staging.staging_id,
            pr_number=duplicate.pr_number,
            pr_url=duplicate.pr_url,
            codes=codes,
            reasons=["Somebody is already reviewing this exact change."],
        )
    if duplicate.kind == duplicate_check.KIND_CLOSED and not allow_reproposal:
        return ProposalResult(
            STATUS_CLOSED_SKIPPED,
            staging_id=staging.staging_id,
            pr_number=duplicate.pr_number,
            pr_url=duplicate.pr_url,
            codes=codes,
            reasons=[
                "This exact change was turned down before, so it was not sent "
                "again. Say so if you want it raised anyway."
            ],
        )

    # 5. A review this seat already opened means the run only has to finish.
    recorded = _row_proposal_id(base_id, source_id, staging.staging_id)
    existing = duplicate_check.open_review_for_branch(branch, base_root, gh=gh)
    if recorded or existing:
        number = existing.get("number") if existing else recorded
        url = existing.get("url") if existing else None
        retire(base_root, staging_path, staging.staging_id)
        folder = os.path.join(paths.worktrees_dir(base_id), staging.staging_id)
        worktree.remove_worktree(base_root, folder, runner=git)
        _record_row(base_id, source_id, staging.staging_id, number, codes)
        codes.append(CODE_REVIEW_REUSED)
        return ProposalResult(
            STATUS_RESUMED,
            staging_id=staging.staging_id,
            pr_number=number,
            pr_url=url,
            codes=codes,
            reasons=["This proposal was already sent, so it was tidied up."],
            branch=branch,
        )

    default = gate.default_branch(git, base_root)
    if not default:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=["no-default-branch"],
            reasons=["GTM Base could not tell which line of work the team shares."],
        )
    if not git.run(["remote", "get-url", "origin"], cwd=base_root).ok:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[CODE_NO_REMOTE],
            reasons=[
                "This base has no shared copy yet, so there is nowhere to send a "
                "proposal. Set one up first."
            ],
        )

    # 6. The working folder, made or picked up where it was left.
    made = None
    written: List[str] = []

    try:
        made = worktree.ensure_worktree(
            base_root, base_id, staging.staging_id, default, git
        )
        codes.extend(made.codes)
        already_saved = _last_subject(made.path, git).startswith(
            "%s%s:" % (COMMIT_SUBJECT_PREFIX, staging.staging_id)
        )
        if already_saved:
            codes.append(CODE_COMMIT_REUSED)
            written = _touched_from_saved(made.path, git)
        else:
            written = _prepare(
                made.path, staging, today, entry_id, source_id, git, base_root, codes
            )
    except ConflictError as clash:
        files = ", ".join(edited_paths(staging))
        worktree.remove_worktree(base_root, made.path, runner=git)
        return ProposalResult(
            STATUS_CONFLICT,
            staging_id=staging.staging_id,
            codes=[clash.code or CODE_HEADING_MISSING],
            reasons=[
                "The part of %s this proposal changes is not there any more, so "
                "it was not sent. Ask for it to be prepared again." % files
            ],
            branch=made.branch,
        )
    except (ValidationError, PathError) as failure:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[failure.code or CODE_INVALID],
            reasons=[str(failure)],
            branch=made.branch if made is not None else branch,
        )
    except GitError as failure:
        # Preparing the proposal happens in a working folder of this seat's
        # own, so a failure there is this run's to report and never something
        # for the person to see as a crash.
        if made is not None:
            worktree.remove_worktree(base_root, made.path, runner=git)
        codes.append(failure.code or CODE_GIT_FAILED)
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=codes,
            reasons=[
                "GTM Base could not prepare this proposal in its own working "
                "folder, so nothing was sent. Nothing was lost; try again."
            ],
            branch=branch,
        )

    # 7. Send it, and open the review.
    sent = git.run(["push", "origin", made.branch], cwd=made.path, timeout=60)
    if not sent.ok:
        codes.append(CODE_PUSH_FAILED)
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=codes,
            reasons=[
                "GTM Base prepared the proposal but could not send it to the "
                "shared copy. Nothing was lost; try again."
            ],
            branch=made.branch,
            written_paths=written,
        )

    body_file = os.path.join(
        paths.worktrees_dir(base_id), staging.staging_id + "-proposal.md"
    )
    atomic_write_text(body_file, staging.pr_body)
    try:
        code, output = ghcmd.call(
            gh,
            [
                "pr",
                "create",
                "--base",
                default,
                "--head",
                made.branch,
                "--title",
                review_title(staging),
                "--body-file",
                body_file,
            ],
            cwd=made.path,
        )
    finally:
        remove(body_file)
    if code != 0:
        codes.append(CODE_REVIEW_FAILED)
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=codes,
            reasons=[
                "GTM Base sent the proposal but could not open the review for "
                "it. Nothing was lost; try again."
            ],
            branch=made.branch,
            written_paths=written,
        )
    number, url = _parse_review_answer(output)
    if number is None:
        codes.append(CODE_REVIEW_UNREADABLE)

    _record_row(base_id, source_id, staging.staging_id, number, codes)
    retire(base_root, staging_path, staging.staging_id)
    worktree.remove_worktree(base_root, made.path, runner=git)
    return ProposalResult(
        STATUS_OPENED,
        staging_id=staging.staging_id,
        pr_number=number,
        pr_url=url,
        codes=codes,
        reasons=reasons,
        branch=made.branch,
        written_paths=written,
    )


def _touched_from_saved(worktree_path: str, git: GitRunner) -> List[str]:
    result = git.run(["show", "--name-only", "--format=", "HEAD"], cwd=worktree_path)
    if not result.ok:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _prepare(
    worktree_path: str,
    staging,
    today: datetime.date,
    entry_id: Optional[str],
    source_id: Optional[str],
    git: GitRunner,
    base_root: str,
    codes: List[str],
) -> List[str]:
    """Apply the edits, write the decision and the record, and save the lot."""
    ordered = edited_paths(staging)
    for edit in staging.edits:
        # Checked here and not only against the clone, because the same name
        # can be an ordinary file in one copy of a base and a link pointing
        # somewhere else entirely in another.
        checked = paths.canonical_context_path(worktree_path, edit.path)
        target = os.path.join(worktree_path, checked)
        text = read_text(target)
        if text is None:
            raise ValidationError(
                "The file %s is not in the shared copy, so it cannot be changed."
                % edit.path,
                code=CODE_MISSING_FILE,
            )
        atomic_write_text(
            target, apply_edit(text, edit), mode=0o644, inside=worktree_path
        )

    touched = list(ordered)
    entry_path = None
    if staging.decision_block:
        entry = ledger_entry_for(staging, today)
        entry_path = "%s/%s.md" % (constants.DECISIONS_DIR, entry.id)
        atomic_write_text(
            os.path.join(worktree_path, entry_path),
            entry.render(),
            mode=0o644,
            inside=worktree_path,
        )
        touched.append(entry_path)

    hash_value = content_hash_for(worktree_path, ordered)
    correction = corrections_for(
        staging, today, hash_value, touched, entry_id, source_id
    )
    correction_path = "%s/%s-%s.md" % (
        constants.CORRECTIONS_DIR,
        today.isoformat(),
        staging.staging_id,
    )
    atomic_write_text(
        os.path.join(worktree_path, correction_path),
        correction.render(),
        mode=0o644,
        inside=worktree_path,
    )

    written = touched + [correction_path]
    git.check(["add", "--"] + written, cwd=worktree_path)
    name, email, author_codes = _author(base_root, git)
    codes.extend(author_codes)
    git.check(
        [
            "-c",
            "user.name=%s" % name,
            "-c",
            "user.email=%s" % email,
            "commit",
            "-q",
            "-m",
            commit_subject(staging),
        ],
        cwd=worktree_path,
    )
    return written


def reopen_from_opened(
    staging_id: str,
    base_root: str,
    base_id: str,
    gh=None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
    session_id: Optional[str] = None,
) -> ProposalResult:
    """Raise a proposal again from the copy kept when it was first sent."""
    ids.check_staging_id(staging_id)
    pending = os.path.join(
        base_root, constants.PROPOSALS_PENDING_DIR, staging_id + ".md"
    )
    kept = os.path.join(base_root, constants.PROPOSALS_OPENED_DIR, staging_id + ".md")
    text = read_text(kept)
    if text is None:
        # A proposal that never opened is still waiting where it was staged.
        text = read_text(pending)
    if text is None:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging_id,
            codes=[CODE_UNREADABLE],
            reasons=["GTM Base has no copy of that proposal to raise again."],
        )
    ensure_dir(os.path.dirname(pending))
    atomic_write_text(pending, text, mode=0o600)
    return propose(
        pending,
        base_root,
        base_id,
        gh=gh,
        runner=runner,
        now=now,
        allow_reproposal=True,
        session_id=session_id,
    )


# --- The path for a person who edited a file themselves -----------------------


LOCAL_EDIT_ORIGIN = "local-edit"
CODE_LOCAL_OUTSIDE = "hand-edit-outside-context"
CODE_LOCAL_MAP = "hand-edit-touches-the-map"
CODE_LOCAL_TOO_LONG = "hand-edit-too-long"
CODE_LOCAL_NOTHING = "no-hand-edit"
CODE_LOCAL_NO_SECTION = "hand-edit-outside-any-heading"


def _changed_files(base_root: str, git: GitRunner) -> Tuple[List[str], str]:
    """Every file the person has changed and not yet saved, and the change itself."""
    result = git.run(["diff", "HEAD", "--unified=0"], cwd=base_root)
    if not result.ok:
        return [], ""
    diff = result.stdout
    changed = []
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                continue
            if target.startswith("b/"):
                target = target[2:]
            path = target.split("\t")[0]
            if path not in changed:
                changed.append(path)
    return changed, diff


def _added_characters(diff: str) -> int:
    total = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            total += len(line) - 1
    return total


def _committed_text(base_root: str, relative: str, git: GitRunner) -> str:
    result = git.run(["show", "HEAD:" + relative], cwd=base_root)
    return result.stdout if result.ok else ""


def _sections_with_levels(text: str) -> "Dict[str, str]":
    """Every part of a file that a change can be described by, keyed by heading.

    Only the words directly under a heading count, and the title of the file is
    left out. A heading that has smaller headings under it is described by those
    instead, so one change is never reported twice.
    """
    lines = text.split("\n")
    found: Dict[str, str] = {}
    index = frontmatter_end(lines)
    while index < len(lines):
        level = _heading_level(lines[index])
        if level >= 2:
            stop = index + 1
            while stop < len(lines) and not _heading_level(lines[stop]):
                stop += 1
            found[lines[index].strip()] = "\n".join(lines[index + 1 : stop]).strip("\n")
            index = stop
            continue
        index += 1
    return found


def stage_local_edit(
    base_root: str,
    base_id: str,
    source_text: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
) -> str:
    """Turn a change the person made by hand into a staged proposal.

    Their own copy of the file is left exactly as they left it. What they read
    before making the change is the evidence, and it is read for things that
    must never leave before anything else happens.
    """
    git = runner_or_default(runner)
    del now  # the staged file carries no date of its own.

    if not isinstance(source_text, str) or not source_text.strip():
        raise ValidationError(
            "A change made by hand needs the source you read, in your own words.",
            code="no-source",
        )
    allowlist, _code = scan.load_allowlist(base_root)
    hits = scan.scan_text(source_text, allowlist, "the source you gave")
    if hits:
        raise ValidationError(hits[0].sentence(), code=hits[0].pattern_class)
    if len(source_text) > constants.MAX_EXCERPT_CHARS:
        raise ValidationError(
            "The source you gave is longer than a proposal may carry.",
            code="too-long",
        )

    changed, diff = _changed_files(base_root, git)
    if not changed:
        raise ValidationError(
            "Nothing in this base has been changed by hand, so there is nothing "
            "to propose.",
            code=CODE_LOCAL_NOTHING,
        )
    for relative in changed:
        if relative == constants.MAP_PATH:
            raise ValidationError(
                "The map is not a file a proposal may change.", code=CODE_LOCAL_MAP
            )
        try:
            paths.canonical_context_path(base_root, relative)
        except PathError:
            raise ValidationError(
                "Only files in the context folder can be proposed this way, and "
                "%s is not one of them." % relative,
                code=CODE_LOCAL_OUTSIDE,
            )
    if _added_characters(diff) > constants.LOCAL_EDIT_MAX_CHARS:
        raise ValidationError(
            "That change is larger than this path will carry. Propose it in "
            "smaller pieces.",
            code=CODE_LOCAL_TOO_LONG,
        )

    edits: List[formats.Edit] = []
    before_parts: List[str] = []
    after_parts: List[str] = []
    for relative in changed:
        now_text = read_text(os.path.join(base_root, relative)) or ""
        was_text = _committed_text(base_root, relative, git)
        current = _sections_with_levels(now_text)
        previous = _sections_with_levels(was_text)
        for heading, body in current.items():
            if previous.get(heading) == body:
                continue
            operation = "replace" if heading in previous else "add"
            edits.append(formats.Edit(relative, heading, operation, body + "\n"))
            before_parts.append(
                previous.get(heading)
                or "This part of %s was not there before." % relative
            )
            after_parts.append(body)
    if not edits:
        raise ValidationError(
            "The change you made is not inside any part of the file that has a "
            "heading, so GTM Base cannot describe it.",
            code=CODE_LOCAL_NO_SECTION,
        )

    first = edits[0].path
    staging_id = ids.staging_id(LOCAL_EDIT_ORIGIN, first, LOCAL_EDIT_ORIGIN, 0)
    marker = marker_line(staging_id, None, None)
    body = formats.render_pr_body(
        {
            "before": _WHITESPACE_RE.sub(" ", " ".join(before_parts)).strip(),
            "after": _WHITESPACE_RE.sub(" ", " ".join(after_parts)).strip(),
            "why": (
                "The owner read the source quoted below and brought the file in "
                "line with it by hand."
            ),
            "evidence": source_text.strip(),
            "confidence": "high",
            "rule_changed": "None",
            "marker": marker,
        }
    )
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin=LOCAL_EDIT_ORIGIN,
        intake_path=LOCAL_EDIT_ORIGIN,
        target_paths=[edit.path for edit in edits],
        sequence=0,
        rule_change=False,
        confidence="high",
        third_party=True,
        pr_body=body,
        source_id=None,
        decision_block=None,
        edits=edits,
        excerpt=source_text.strip(),
    )
    ordered: List[str] = []
    for path in staging.target_paths:
        if path not in ordered:
            ordered.append(path)
    staging.target_paths = ordered
    staging.validate()

    folder = ensure_dir(os.path.join(base_root, constants.PROPOSALS_PENDING_DIR))
    destination = os.path.join(folder, staging_id + ".md")
    atomic_write_text(destination, staging.render(), mode=0o600)
    return destination
