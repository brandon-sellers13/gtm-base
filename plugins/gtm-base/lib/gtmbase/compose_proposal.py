"""Turning one staged proposal into a review anybody on the team can read.

The order matters, and every step is safe to repeat. The staged file is read
and checked, the two conditions that stop anything leaving this computer are
asked, everything the proposal would carry is read for things that must never
leave, and only then is a working folder made. The edits are applied there, the
context change and the record of what changed are written beside them, and the whole
lot is sent as one review.

A base with no shared copy has nowhere to send a proposal, so it never reaches
any of that. The run stops at the second step, keeps the prepared change
exactly where it is, and says it can be approved in Claude instead, which is
what `approve_local.py` does.

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
    base_reader,
    constants,
    duplicate_check,
    formats,
    gate,
    ghcmd,
    ids,
    names,
    paths,
    push_conditions,
    scan,
    state,
    worktree,
)
from .errors import GitError, GtmBaseError, PathError, ValidationError
from .fsutil import (
    atomic_write_text,
    ensure_dir,
    read_bytes,
    read_text,
    remove,
)
from .gitcmd import GitRunner, nul_fields, runner_or_default
from .validate import find_marker, marker_line

# What a run can end as.
STATUS_OPENED = "opened"
STATUS_ALREADY_OPEN = "already-open"
STATUS_CLOSED_SKIPPED = "closed-skipped"
STATUS_MERGED_SKIPPED = "merged-skipped"
STATUS_REFUSED = "refused"
STATUS_CONFLICT = "conflict"
STATUS_RESUMED = "resumed"
# The base has no shared copy, so this is a handoff rather than a refusal: the
# prepared change is kept exactly where it is and approved in Claude instead.
STATUS_APPROVE_HERE = "approve-here"

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
CODE_CANNOT_TELL = "cannot-tell-about-the-shared-copy"
# The words the prepared change would put in the file are still the first
# draft GTM Base wrote, which is a note asking for the real wording.
CODE_STILL_A_PLACEHOLDER = "still-the-first-draft"

# What the base's own settings say about a shared copy. Not knowing is its own
# answer, because a settings file that could not be read for a moment is not a
# base without a shared copy.
SHARED_COPY_PRESENT = "present"
SHARED_COPY_ABSENT = "absent"
SHARED_COPY_UNKNOWN = "unknown"

# What the saved work in a working folder is called, so a repeat run knows it.
COMMIT_SUBJECT_PREFIX = "Proposal "
# How much of the summary the saved work's note carries.
COMMIT_SUMMARY_CHARS = 60
# How much of the summary the title of a review carries.
TITLE_SUMMARY_CHARS = 80

# What a person is told when the base has nowhere to send a proposed change.
APPROVE_HERE = (
    "This base has no shared copy yet, so there is nowhere to send this "
    "prepared change. It is still here, and you can approve it here instead."
)
# What a person is told when that question could not be answered at all.
CANNOT_TELL = (
    "GTM Base could not tell whether this base has a shared copy, so it did "
    "nothing at all. Ask again in a moment."
)
# What a person is told when the words are still the note asking for words.
STILL_A_PLACEHOLDER = (
    "The words this change would put in your document are still the note GTM "
    "Base wrote asking for the real wording, so nothing was raised. Write "
    "what the document should say now, show it beside what it says today, and "
    "ask again."
)


# What a prepared change written by the check on a base says it came from.
LEDGER_ORIGIN = "ledger"


def still_a_first_draft(staging, base_id=None) -> bool:
    """Whether this prepared change still holds GTM Base's own note.

    There is one description of that, here, and every path that could apply a
    prepared change asks it. Four things say yes and any one of them is enough,
    because each of the first three was got round on its own.

    This seat's own record says so. That record lives in the folder no file
    tool may write, which is finding M1 of the third look: one ordinary edit
    took the marker line out of the prepared change and cleared it.

    The prepared change carries the marker. A change the check on a base wrote
    carries no marker at all, which is the shape of a file written by an older
    build, and for that origin an absent marker is read as yes rather than no.

    A change the check wrote still adds a part of its own rather than replacing
    the part that went out of date, which means the claim it corrects would
    still be standing afterwards whatever the words now say.

    Or the words are the note over again, however they have been respaced.
    """
    from . import stale_check, state

    if base_id and state.is_a_first_draft(base_id, staging.staging_id):
        return True
    marked = getattr(staging, "first_draft", None)
    if marked:
        return True
    if marked is None:
        # A prepared change that says nothing about this is one an older
        # build wrote, and nothing is not the same as no. Finding N5 of the
        # final confirmation pass took the origin out of this: the origin is
        # a field in the same unprotected file, so a copy of a first draft
        # under a new name with another origin was approved with the note
        # still in it.
        return True
    for edit in staging.edits:
        if edit.op == "add" and edit.heading == stale_check.FALLBACK_HEADING:
            # It would add a part of its own rather than replacing the part
            # that went out of date, so the claim it corrects would still be
            # standing afterwards, whatever the words now say.
            return True
        if edit.op == "remove":
            # A part taken out puts no words in at all (finding R10).
            continue
        if stale_check.still_the_note(getattr(edit, "text", None)):
            return True
    return False


def _still_the_first_draft(text) -> bool:
    """Whether some words are the note GTM Base wrote, read as words alone."""
    from . import stale_check

    return stale_check.still_the_note(text)

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
    return staging_from_text(text)


def staging_from_text(text: str) -> "formats.ProposalStaging":
    """One staged proposal from text already read, held to the same limits.

    Approval parses, checks, hashes, and writes from the one reading it took
    (finding N2 of Astra's fourth look), so it needs this without a second
    read of the file.
    """
    if len(text.encode("utf-8", "replace")) > constants.MAX_ARTIFACT_BYTES:
        raise ValidationError(
            "That staged proposal is larger than GTM Base will read.",
            code=CODE_UNREADABLE,
        )
    return formats.ProposalStaging.parse(text).validate()


def shared_copy_state(base_root: str, runner: Optional[GitRunner] = None) -> str:
    """Whether this base has somewhere to send a proposed change, or is unclear.

    Only the base's own settings are read, and nothing leaves the computer to
    answer it. A failure to read them is its own answer rather than a no,
    because treating a moment's trouble as "this base has no shared copy"
    would quietly send a base that does have one down the path meant for a
    base that does not.
    """
    git = runner_or_default(runner)
    found = git.run(["remote", "get-url", "origin"], cwd=base_root)
    if found.ok and found.out():
        return SHARED_COPY_PRESENT
    listed = git.run(["remote"], cwd=base_root)
    if listed.ok and not listed.out():
        return SHARED_COPY_ABSENT
    return SHARED_COPY_UNKNOWN


def marker_of(staging) -> str:
    """The one line this proposal carries wherever it ends up."""
    return duplicate_check.marker_for(staging)


def marker_problems(staging) -> List[Tuple[str, str]]:
    """Whether the marker and the change entry this proposal carries agree.

    A marker naming this proposal's own identifier as the change means the
    proposal creates that change, so it has to carry it. A marker naming any
    other change means one the base already holds, quoted as evidence, and the
    proposal must not carry a second copy of it.
    """
    parsed = find_marker(marker_of(staging))
    entry_id = parsed[1] if parsed else None
    if entry_id == staging.staging_id and not staging.decision_block:
        return [
            (
                CODE_MARKER_ENTRY,
                "This proposal says it carries a context change, but no "
                "change is written in it.",
            )
        ]
    if entry_id and entry_id != staging.staging_id and staging.decision_block:
        return [
            (
                CODE_ENTRY_MISMATCH,
                "This proposal names a context change the base already holds "
                "and writes out a second copy of it, which it may not do.",
            )
        ]
    return []


def _name_is_the_file(base_root: str, relative: str) -> bool:
    """Whether the file this path really points at sits at this very name.

    A link in the middle of a path, and a machine that treats two spellings as
    one file, both make a path mean a file that is filed under another name.
    Following the path and asking where the answer sits is what tells them
    apart, and it is asked of every edit rather than only of the map.
    """
    real_base = os.path.realpath(base_root)
    real_target = os.path.realpath(os.path.join(base_root, relative))
    try:
        settled = os.path.relpath(real_target, real_base)
    except ValueError:
        return False
    return settled.replace(os.sep, "/") == relative


def _is_the_map(base_root: str, relative: str) -> bool:
    """Whether this path means the map itself, whatever it calls it."""
    named = os.path.join(base_root, relative.replace("/", os.sep))
    the_map = os.path.join(base_root, constants.MAP_PATH.replace("/", os.sep))
    if not os.path.exists(named) or not os.path.exists(the_map):
        return False
    try:
        return os.path.samefile(named, the_map)
    except OSError:
        return False


def check_edits(base_root: str, staging) -> List[Tuple[str, str]]:
    """Everything about the edits that stops the proposal before it starts.

    The map is out of bounds because it is what tells the assistant where
    everything lives. The settings block at the top of a file is out of bounds
    because it carries who owns the file and when it was last confirmed, and a
    proposal that could rewrite those could confirm itself.

    The name an edit gives a file also has to be the file it really is. A
    folder link inside the context folder, and a difference of letter case on a
    machine that treats two such names as one file, both let an edit read as an
    ordinary file and land on the map. So the path is followed to the file it
    really means, that file has to sit at the very name the edit gave, and the
    map is recognised as the same file rather than as the same spelling.
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
        if relative == constants.MAP_PATH or _is_the_map(base_root, relative):
            reasons.append(
                (
                    CODE_MAP_TARGET,
                    "A proposal may never change the map, which is the file that "
                    "says where everything lives.",
                )
            )
            continue
        if not _name_is_the_file(base_root, relative):
            reasons.append(
                (
                    CODE_OUTSIDE_CONTEXT,
                    "A proposal may only change files in the context folder, and "
                    "%s is a name for a file somewhere else." % edit.path,
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


def find_heading(
    lines: List[str], heading: str, start: int = 0, occurrence: int = 1
) -> int:
    """Where a heading is, matched as a whole line and nothing else.

    The occurrence says which one is meant when the same heading is there more
    than once, counting from one (finding R10 of Astra's third look).
    """
    wanted = heading.strip()
    seen = 0
    for index in range(start, len(lines)):
        if lines[index].strip() == wanted:
            seen += 1
            if seen >= max(1, int(occurrence or 1)):
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
    heading is not there yet. Taking a part out removes the heading and
    everything under it, up to the next heading of the same size or bigger.
    """
    lines = text.split("\n")
    body_starts = frontmatter_end(lines)
    heading = (edit.heading or "").strip()
    block = [""] + edit.text.strip("\n").split("\n") + [""]
    index = find_heading(
        lines, heading, body_starts, getattr(edit, "occurrence", 1)
    )

    if edit.op == "remove":
        if index < 0:
            raise ConflictError(
                "the heading is no longer in the file", code=CODE_HEADING_MISSING
            )
        stop = section_end(lines, index)
        start = index
        # The blank lines between this part and the one above it go with it,
        # so the document reads as if the part had never been there.
        while start > body_starts and not lines[start - 1].strip():
            start -= 1
        if stop >= len(lines):
            result = lines[:start]
        else:
            result = lines[:start] + [""] + lines[stop:]
        return "\n".join(result).rstrip("\n") + "\n"
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


def in_original_positions(edits) -> list:
    """The edits, each numbered in the document as it was before any of them.

    A part is named by its heading and which of the parts with that heading
    it is, counted in the document as it stood. Edits are applied one after
    another, and taking out an earlier part with the same heading makes every
    later one a number smaller, so taking out the second and the third of
    three found no third (the shared hand edits Astra's fourth look named).
    Each later edit is moved down by the parts before it already taken out.
    """
    taken: Dict[Tuple[str, str], List[int]] = {}
    placed = []
    for one in edits:
        key = (str(one.path), (one.heading or "").strip())
        which = max(1, int(getattr(one, "occurrence", 1) or 1))
        earlier = sum(1 for gone in taken.get(key, []) if gone < which)
        if earlier:
            one = formats.Edit(
                one.path, one.heading, one.op, one.text, occurrence=which - earlier
            )
        if one.op == "remove":
            taken.setdefault(key, []).append(which)
        placed.append(one)
    return placed


# --- The pieces the proposal carries -----------------------------------------


def hand_edit_targets(staging) -> List[str]:
    """Every document a change made by hand is about, in the order it names them.

    Finding R10 of Astra's third look. These come from the files the person
    changed and the bytes recorded for each, not from the parts the change is
    described by, so a document whose change no part describes is still one
    this change saves, shows the whole difference of, and checks for having
    moved. A change prepared before that carries its targets only through its
    parts, and for that one the parts are the answer.
    """
    ordered: List[str] = []
    for path in list(staging.target_paths or []):
        if path not in ordered:
            ordered.append(path)
    recorded = list(getattr(staging, "target_bytes", None) or [])
    if ordered and len(recorded) == len(ordered):
        return ordered
    return edited_paths(staging)


def targets_of(staging) -> List[str]:
    """Every document one prepared change is about, whatever made it."""
    if str(getattr(staging, "origin", "")) == LOCAL_EDIT_ORIGIN:
        return hand_edit_targets(staging)
    return edited_paths(staging)


class WaitingChange(object):
    """One prepared change that is really waiting, read and checked once."""

    __slots__ = ("staging_id", "path", "staging", "targets", "missing")

    def __init__(self, staging_id, path, staging, targets, missing):
        self.staging_id = staging_id
        self.path = path
        self.staging = staging
        self.targets = list(targets)
        # The documents it is about that are no longer in the base. A change
        # with any is one nothing can ever be done with, and it is said out
        # loud rather than listed as something to approve.
        self.missing = list(missing)


def waiting_changes(base_root: str) -> List[WaitingChange]:
    """Every prepared change waiting in this base, by one reading of the folder.

    Finding R11 of Astra's third look. The closing learned to count only a
    change filed under a name GTM Base issued, with that name written inside
    it, and the two readers that list what is waiting in a review went on
    counting anything that parsed, so a change renamed to notes.md was listed
    by both, pointing at a file name that was not there any more. Every one of
    them reads this now, so none of them can disagree.

    What comes back holds every change whose file is a plain file named after
    an identifier GTM Base issued, holding that same identifier, that parses,
    and that is about at least one document. Whether each of those documents
    is still in the base is recorded rather than filtered, because the closing
    has to say when one is gone and the readers have to leave it out.
    """
    found: List[WaitingChange] = []
    folder = os.path.join(base_root, constants.PROPOSALS_PENDING_DIR)
    if not os.path.isdir(folder):
        return found
    try:
        names_here = sorted(os.listdir(folder))
    except OSError:
        return found
    for name in names_here:
        if not name.endswith(".md"):
            continue
        whole = os.path.join(folder, name)
        if os.path.islink(whole) or not os.path.isfile(whole):
            continue
        staging_id = name[: -len(".md")]
        try:
            ids.check_staging_id(staging_id)
        except (ValueError, TypeError):
            continue
        text = read_text(whole)
        if text is None:
            continue
        try:
            staging = formats.ProposalStaging.parse(text).validate()
        except (ValidationError, PathError):
            continue
        if staging.staging_id != staging_id:
            continue
        targets = targets_of(staging)
        if not targets:
            continue
        missing = [
            path
            for path in targets
            if not os.path.isfile(os.path.join(base_root, path.replace("/", os.sep)))
        ]
        found.append(WaitingChange(staging_id, whole, staging, targets, missing))
    return found


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
    """The context change this proposal carries, dated the day it was written."""
    entry = formats.LedgerEntry.parse(staging.decision_block)
    if entry.id != staging.staging_id:
        raise ValidationError(
            "The context change in this proposal is named after a different "
            "proposal.",
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
        pieces.append(("the context change", staging.decision_block))
    for number, edit in enumerate(staging.edits, start=1):
        pieces.append(("edit %d" % number, edit.text))
        # The heading is written into the file too, whenever an edit adds a
        # part that is not there yet, so it is read like any other text.
        pieces.append(("the heading edit %d names" % number, edit.heading or ""))
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


def _forget_the_first_draft(base_id, staging_id) -> None:
    """Take a prepared change off this seat's record of unfinished notes.

    Finding N4. That record only ever grew, so a name reused after a change
    was dropped or raised carried the old one's refusal with it.
    """
    if not base_id:
        return
    try:
        state.clear_first_draft(base_id, staging_id)
    except Exception:
        pass


def retire(
    base_root: str, staging_path: str, staging_id: str, base_id=None
) -> str:
    """Put the staged file where a proposal that is under review is kept."""
    _forget_the_first_draft(base_id, staging_id)
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

    # The same rule the local path holds to, for the same reason: the first
    # draft GTM Base writes into a prepared change is a note asking for the
    # real wording, and nobody should be asked to accept one as a correction
    # to their document (finding A6 of the 2026-09-20 review).
    if still_a_first_draft(staging, base_id):
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[CODE_STILL_A_PLACEHOLDER],
            reasons=[STILL_A_PLACEHOLDER],
        )

    marker = marker_of(staging)
    parsed_marker = find_marker(marker)
    entry_id = parsed_marker[1] if parsed_marker else None
    source_id = parsed_marker[2] if parsed_marker else staging.source_id
    disagreements = marker_problems(staging)
    if disagreements:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[code for code, _ in disagreements],
            reasons=[sentence for _, sentence in disagreements],
        )

    # 2. A base with no shared copy has nowhere to send anything, so the run
    # stops here and hands the prepared change to the path that approves it in
    # Claude. It is asked before the two conditions below because those are
    # about what may leave this computer, and nothing is going to leave it.
    state_of_it = shared_copy_state(base_root, runner=git)
    if state_of_it == SHARED_COPY_ABSENT:
        return ProposalResult(
            STATUS_APPROVE_HERE,
            staging_id=staging.staging_id,
            codes=[CODE_NO_REMOTE],
            reasons=[APPROVE_HERE],
        )
    if state_of_it != SHARED_COPY_PRESENT:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[CODE_CANNOT_TELL],
            reasons=[CANNOT_TELL],
        )

    # 3. The two conditions that stop anything leaving this computer.
    session = session_id if session_id is not None else _seat_session_id(base_id)
    blocked = push_conditions.check(base_id, session)
    if blocked:
        return ProposalResult(
            STATUS_REFUSED,
            staging_id=staging.staging_id,
            codes=[code for code, _ in blocked],
            reasons=[sentence for _, sentence in blocked],
        )

    # 4. Read everything the proposal would carry.
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

    # 5. Has anybody already proposed this. A review on this proposal's own
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

    # 6. A review this seat already opened means the run only has to finish.
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
    # 7. The working folder, made or picked up where it was left.
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

    # 8. Send it, and open the review.
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
    # Names end in a NUL and come out as they are, so a name with an accent or
    # a space in it is the name on the disk rather than git's quoted form.
    result = git.run(
        ["show", "--name-only", "--format=", "-z", "HEAD"], cwd=worktree_path
    )
    if not result.ok:
        return []
    return nul_fields(result.stdout)


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
    """Apply the edits, write the context change and the record, and save it."""
    ordered = edited_paths(staging)
    for edit in in_original_positions(staging.edits):
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
        entry_path = base_reader.where_to_write_the_entry(worktree_path, entry.id)
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


# --- Writing the real wording into a first draft ------------------------------


CODE_STILL_THE_NOTE = "still-the-note"
CODE_NEEDS_A_PART = "needs-the-part-of-the-document"
CODE_NO_PARTS_AT_ALL = "the-document-has-no-parts"

# A change somebody made by hand is worded by their document, so the wording
# command has nothing of its own to write into one (finding R7 of Astra's
# third look, which let every other prepared change be reworded).
MADE_BY_HAND_WORDING = (
    "That change is one you made by hand, so its wording is what your document "
    "says. Change the document itself and ask for the change to be prepared "
    "again."
)
CODE_MADE_BY_HAND_WORDING = "wording-of-a-hand-edit"
STILL_THE_NOTE = (
    "What you handed in is the note GTM Base wrote over again rather than the "
    "wording, so nothing was written. Say what the document should say now, "
    "in the document's own voice."
)
NEEDS_A_PART = (
    "That change does not say which part of the document it is about, so the "
    "wording has nowhere to go and would leave what it corrects standing. "
    "List the parts, ask which one this is about, and name it."
)
# Said when the document has no parts at all, which is the one state the
# sentence above cannot be acted on in (finding P3 of the confirmation round:
# every way of correcting such a document refused, and none of them said why).
NO_PARTS_AT_ALL = (
    "That document is one run of words with no headings in it, so there is no "
    "part of it to correct. Give it a heading for each thing it covers, and "
    "GTM Base can work with it after that."
)


def parts_of(base_root: str, staging) -> List[Tuple[str, str, int]]:
    """Every part of the document one first draft could be written into.

    Each one comes back as the path, the heading, and which one of that
    heading it is, in the order they are read, so a caller can put a number
    beside each and take the number back. The third is what tells two parts
    with the same heading apart (finding R10 of Astra's third look).
    """
    found: List[Tuple[str, str, int]] = []
    for relative in edited_paths(staging):
        text = read_text(
            os.path.join(base_root, relative.replace("/", os.sep))
        ) or ""
        lines = text.split("\n")
        seen: Dict[str, int] = {}
        for line in lines[frontmatter_end(lines) :]:
            if _heading_level(line) == 2:
                heading = line.strip()
                seen[heading] = seen.get(heading, 0) + 1
                found.append((relative, heading, seen[heading]))
    return found


def write_the_wording(
    base_root: str, staging_path: str, words: str, part=None, base_id=None
):
    """Put the real wording into a prepared change, and take the marker off it.

    This is the only way the marker comes off. Findings V8 and N4 of the
    2026-09-20 verification round: it used to be enough to retype the note
    slightly, and the wording was allowed to land in a part of its own while
    the claim it corrected went on standing in the part above.

    It is also how the wording of a change still waiting is revised, as many
    times as the owner asks. Finding R7 of Astra's third look: the first
    wording took the marker off, and the next correction the owner asked for
    was refused as not a first draft, after the words for it had been read
    and thrown away. Every revision is held to the same rules as the first,
    and every one moves the change on, so what was shown before it is never
    what gets approved.
    """
    from . import approve_local

    try:
        resolved, _named = approve_local.checked_staging_path(base_root, staging_path)
    except PathError:
        raise ValidationError(
            approve_local.NOT_WAITING_HERE, code=approve_local.CODE_NOT_WAITING_HERE
        )
    staging = load_staging(resolved)
    if staging.origin == LOCAL_EDIT_ORIGIN:
        raise ValidationError(MADE_BY_HAND_WORDING, code=CODE_MADE_BY_HAND_WORDING)
    if not staging.edits:
        raise ValidationError(
            "This proposal changes nothing, so there is nothing to send.",
            code=CODE_NO_EDITS,
        )
    from . import stale_check

    if stale_check.still_the_note(words):
        raise ValidationError(STILL_THE_NOTE, code=CODE_STILL_THE_NOTE)
    text = str(words).strip() + "\n"
    needs_a_part = any(edit.op == "add" for edit in staging.edits)
    if needs_a_part and part is None:
        if not parts_of(base_root, staging):
            raise ValidationError(NO_PARTS_AT_ALL, code=CODE_NO_PARTS_AT_ALL)
        raise ValidationError(NEEDS_A_PART, code=CODE_NEEDS_A_PART)
    for edit in staging.edits:
        if part is not None:
            edit.path, edit.heading = part[0], part[1]
            edit.occurrence = int(part[2]) if len(part) > 2 else 1
            edit.op = "replace"
        edit.text = text
    staging.first_draft = False
    staging.revision = int(getattr(staging, "revision", 0) or 0) + 1
    atomic_write_text(resolved, staging.validate().render(), mode=0o600)
    if base_id:
        state.clear_first_draft(base_id, staging.staging_id)
    return staging


# --- The path for a person who edited a file themselves -----------------------


LOCAL_EDIT_ORIGIN = "local-edit"
CODE_LOCAL_OUTSIDE = "hand-edit-outside-context"
CODE_LOCAL_MAP = "hand-edit-touches-the-map"
CODE_LOCAL_TOO_LONG = "hand-edit-too-long"
CODE_LOCAL_NOTHING = "no-hand-edit"
CODE_LOCAL_NO_SECTION = "hand-edit-outside-any-heading"


def _changed_files(base_root: str, git: GitRunner) -> Tuple[List[str], str]:
    """Every file the person has changed and not yet saved, and the change itself.

    The names come from a list of their own ending in NULs rather than from the
    headers of the change, because git quotes a name with an accent or a space
    in those headers and the quoted form is not a path in this base. A file
    that was taken away is left out, as it always was.
    """
    named = git.run(
        ["diff", "HEAD", "--name-only", "-z", "--diff-filter=d"], cwd=base_root
    )
    if not named.ok:
        return [], ""
    result = git.run(["diff", "HEAD", "--unified=0"], cwd=base_root)
    if not result.ok:
        return [], ""
    changed: List[str] = []
    for path in nul_fields(named.stdout):
        if path not in changed:
            changed.append(path)
    return changed, result.stdout


def _added_characters(diff: str) -> int:
    total = 0
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            total += len(line) - 1
    return total


def _committed_text(base_root: str, relative: str, git: GitRunner) -> str:
    result = git.run(["show", "HEAD:" + relative], cwd=base_root)
    return result.stdout if result.ok else ""


def _sections_with_levels(text: str) -> "Dict[Tuple[str, int], str]":
    """Every part of a file that a change can be described by.

    Each part is keyed by its heading and by which one of that heading it is,
    counting from one, because a document can hold the same heading twice and
    a table keyed by the heading alone kept only the last of them (finding R10
    of Astra's third look). Only the words directly under a heading count, and
    the title of the file is left out. A heading that has smaller headings
    under it is described by those instead, so one change is never reported
    twice.
    """
    lines = text.split("\n")
    found: Dict[Tuple[str, int], str] = {}
    seen: Dict[str, int] = {}
    index = frontmatter_end(lines)
    while index < len(lines):
        level = _heading_level(lines[index])
        if level >= 2:
            stop = index + 1
            while stop < len(lines) and not _heading_level(lines[stop]):
                stop += 1
            heading = lines[index].strip()
            seen[heading] = seen.get(heading, 0) + 1
            found[(heading, seen[heading])] = "\n".join(
                lines[index + 1 : stop]
            ).strip("\n")
            index = stop
            continue
        index += 1
    return found


def _has_parts(text: str) -> bool:
    """Whether a document has any part below its title at all."""
    lines = text.split("\n")
    return any(
        _heading_level(line) >= 2 for line in lines[frontmatter_end(lines) :]
    )


# What a person is told when every change they made to a document with parts
# in it is outside all of them: above the first heading, in the title, or in
# the settings at the top. The sentence saying a document has no headings was
# said here before, which was untrue of a document that has them (finding R10
# of Astra's third look).
OUTSIDE_EVERY_PART = (
    "Everything you changed in %s is above its first heading, so no part of it "
    "changed. Make the change in the part it is about, and ask again."
)
# What the change says a part will read afterwards, when the person took that
# part out.
PART_TAKEN_OUT = "This part is taken out."


# The one thing this path asks on top of where the material came from. It is
# short on purpose: requirement P16 asks one question here, not two.
LOCAL_EDIT_ASK = "What changed, and why?"
# What the change says it came from, when a hand edit becomes one. It is the
# person's own editing, so there is no label from a document to name.
LOCAL_EDIT_SOURCE = "what the owner said when they raised their own edit"
CODE_NO_CHANGE_WORDS = "no-words-for-the-change"


def local_edit_entry(
    base_root: str,
    staging_id: str,
    what_changed: str,
    affects: List[str],
    today: datetime.date,
    git: GitRunner,
) -> "formats.ChangeEntry":
    """The context change that travels with one hand edit, from their words.

    Requirement P16. Somebody who edits a context file by hand because the
    business moved has just told the base something it had no other way to
    learn, so what they said travels with the prepared change and is written
    down when that change is approved. The change is named after the proposal
    carrying it, which is the rule every carried change already follows.
    """
    settings = base_reader.settings_of(base_reader.map_text(base_root))
    _name, address, _codes = _author(base_root, git)
    entry = formats.ChangeEntry(
        id=staging_id,
        happened_on=today.isoformat(),
        written_on=today.isoformat(),
        noted_by=address,
        source=LOCAL_EDIT_SOURCE,
        affects=list(affects),
        review_by=(
            today
            + datetime.timedelta(days=int(settings.confirmation_threshold_days))
        ).isoformat(),
        origin=LOCAL_EDIT_ORIGIN,
        status="open",
        run_id=None,
        body=str(what_changed).strip(),
    )
    return entry.validate(today)


# How many identifiers a second hand edit to one document will try before it
# gives up. It is the number of hand edits one document can carry a record of,
# which is a long way past anything a person does in a year.
LOCAL_EDIT_SEQUENCE_CAP = 200


def free_local_edit_id(base_root: str, path: str) -> str:
    """The first identifier for a hand edit that nothing in this base holds.

    Finding N3 of the 2026-09-20 verification round. The identifier was worked
    out from three fixed things and the number zero, so the second change
    somebody made by hand to one document always asked for the name the first
    one already had, and the second one could never be recorded at all. Every
    place a name is remembered is looked in: the changes waiting, the ones
    raised, the ones nobody wanted, the record of what was corrected, and both
    of the folders a base keeps its context changes in.
    """
    for sequence in range(LOCAL_EDIT_SEQUENCE_CAP):
        candidate = ids.staging_id(
            LOCAL_EDIT_ORIGIN, path, LOCAL_EDIT_ORIGIN, sequence
        )
        if not _name_is_taken(base_root, candidate):
            return candidate
    raise ValidationError(
        "There are too many changes recorded for that document already.",
        code="no-room-for-a-change",
    )


def _name_is_taken(base_root: str, staging_id: str) -> bool:
    """Whether anything in this base already remembers this identifier."""
    for folder in (
        constants.PROPOSALS_PENDING_DIR,
        constants.PROPOSALS_OPENED_DIR,
        constants.PROPOSALS_DROPPED_DIR,
        constants.CHANGES_DIR,
        constants.LEGACY_CHANGES_DIR,
    ):
        whole = os.path.join(base_root, folder.replace("/", os.sep))
        if os.path.lexists(os.path.join(whole, staging_id + ".md")):
            return True
    corrections = os.path.join(base_root, constants.CORRECTIONS_DIR)
    wanted = "-%s.md" % staging_id
    try:
        names = os.listdir(corrections)
    except OSError:
        names = []
    return any(name.endswith(wanted) for name in names)


def stage_local_edit(
    base_root: str,
    base_id: str,
    source_text: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
    what_changed: Optional[str] = None,
    records_a_change: bool = False,
) -> str:
    """Turn a change the person made by hand into a staged proposal.

    Their own copy of the file is left exactly as they left it. What they read
    before making the change is the evidence, and it is read for things that
    must never leave before anything else happens.

    The person is asked one more thing on this path, what changed and why, and
    their answer decides one thing only: whether a context change travels with
    the proposal. An answer about the business becomes that change, and the
    caller says so by passing `records_a_change`. An answer about a spelling
    mistake records nothing at all, which is the other half of requirement
    P16: nobody fixing a typo is made to invent a change to get it fixed, and
    what they get is exactly the proposal this path has always produced.
    """
    git = runner_or_default(runner)
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()

    if records_a_change and not str(what_changed or "").strip():
        raise ValidationError(
            "A context change needs the words you would use for what changed.",
            code=CODE_NO_CHANGE_WORDS,
        )

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

    # The documents this change is about are the documents the person changed,
    # every one of them, whatever the parts below manage to describe. Finding
    # R10 of Astra's third look: they used to be read off the parts, so a
    # change the parts could not describe could not be prepared at all.
    edits: List[formats.Edit] = []
    before_parts: List[str] = []
    after_parts: List[str] = []
    any_parts = False
    for relative in changed:
        now_text = read_text(os.path.join(base_root, relative)) or ""
        was_text = _committed_text(base_root, relative, git)
        any_parts = any_parts or _has_parts(now_text) or _has_parts(was_text)
        current = _sections_with_levels(now_text)
        previous = _sections_with_levels(was_text)
        for (heading, occurrence), body in current.items():
            if previous.get((heading, occurrence)) == body:
                continue
            operation = "replace" if (heading, occurrence) in previous else "add"
            edits.append(
                formats.Edit(
                    relative, heading, operation, body + "\n", occurrence=occurrence
                )
            )
            before_parts.append(
                previous.get((heading, occurrence))
                or "This part of %s was not there before." % relative
            )
            after_parts.append(body)
        # A part that is gone is described as taken out, which is all a person
        # who deleted an obsolete part did.
        for (heading, occurrence), body in previous.items():
            if (heading, occurrence) in current:
                continue
            edits.append(
                formats.Edit(relative, heading, "remove", "", occurrence=occurrence)
            )
            before_parts.append(body)
            after_parts.append(PART_TAKEN_OUT)
    if not edits:
        if any_parts:
            raise ValidationError(
                OUTSIDE_EVERY_PART % names.document_name(changed[0]),
                code=CODE_LOCAL_NO_SECTION,
            )
        # The same sentence the wording command says, because it is the same
        # thing wrong with the document and the same thing to do about it
        # (finding P3).
        raise ValidationError(NO_PARTS_AT_ALL, code=CODE_LOCAL_NO_SECTION)

    first = changed[0]
    staging_id = free_local_edit_id(base_root, first)
    ordered_targets: List[str] = list(changed)
    entry = None
    if records_a_change:
        entry = local_edit_entry(
            base_root, staging_id, what_changed, ordered_targets, today, git
        )
    # A proposal that carries a change names that change in its own marker, and
    # one that carries none names none. `marker_problems` refuses either half
    # of that written without the other.
    marker = marker_line(staging_id, staging_id if entry is not None else None, None)
    body = formats.render_pr_body(
        {
            "before": _WHITESPACE_RE.sub(" ", " ".join(before_parts)).strip(),
            "after": _WHITESPACE_RE.sub(" ", " ".join(after_parts)).strip(),
            "why": (
                (
                    "The owner read the source quoted below and brought the file "
                    "in line with it by hand, and said what changed: %s"
                    % _WHITESPACE_RE.sub(" ", str(what_changed or "")).strip()
                )
                if entry is not None
                else (
                    "The owner read the source quoted below and brought the file "
                    "in line with it by hand."
                )
            ),
            "evidence": source_text.strip(),
            "confidence": "high",
            "rule_changed": "None",
            "marker": marker,
        }
    )
    # The exact bytes of each document this change was made from, so that
    # whether it has moved on since is a question about the document rather
    # than about what happens when the edits are applied twice (finding N1).
    target_bytes = []
    for relative in ordered_targets:
        data = read_bytes(os.path.join(base_root, relative.replace("/", os.sep)))
        if data is None:
            raise ValidationError(
                "GTM Base could not read %s as it stands, so it prepared "
                "nothing." % relative,
                code=CODE_UNREADABLE,
            )
        target_bytes.append(ids.bytes_hash(data))

    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin=LOCAL_EDIT_ORIGIN,
        intake_path=LOCAL_EDIT_ORIGIN,
        target_paths=list(ordered_targets),
        sequence=0,
        rule_change=False,
        confidence="high",
        third_party=True,
        pr_body=body,
        source_id=None,
        decision_block=entry.render() if entry is not None else None,
        edits=edits,
        excerpt=source_text.strip(),
        target_bytes=target_bytes,
    )
    staging.validate()

    folder = ensure_dir(os.path.join(base_root, constants.PROPOSALS_PENDING_DIR))
    destination = os.path.join(folder, staging_id + ".md")
    atomic_write_text(destination, staging.render(), mode=0o600)
    return destination
