"""Approving one prepared change on a base that has no shared copy.

A base with no shared copy has nowhere to send a proposed change, so until this
module existed every answer that became a prepared change ended at a refusal.
This is the local half of reviewing proposals: the owner reads the whole change
here, says yes, and it is applied to their own copy of the base with the same
screens, the same record of what changed, and the same confirmation a change
accepted on a shared copy gets.

Nothing here sends anything anywhere, and nothing here touches the two
conditions that stop anything leaving this computer. A base that does have a
shared copy is sent back to the path that already ships, and a base where that
question cannot be answered is left alone rather than treated as one without.

It is two calls on purpose, because a person answers between them, and the
person answering is the whole point: the permission prompt in front of the
second call is the human step this design rests on. `show` reads the prepared
change, screens it, and hands back the whole thing together with a value that
stands for exactly what was shown. `approve` takes that value back, and applies
nothing at all if the prepared change or the files it touches moved in between.
Both calls work the change out the same way, from the same reading, so what is
written can only be what was read out loud.

The order inside `approve` is fixed, and every step is safe to repeat. Before
anything is written, a note of what this run is about to write is left in this
seat's own folder, naming each path together with the content this run will put
there. A run that stops halfway is found by that note on the next run: work
that was already saved is finished, and work that was not is undone. A path is
only ever undone when what is on the disk is exactly what this run wrote, so an
edit the person made themselves is never lost and stops the run instead.

Everything read out of a prepared change is data, and so is everything read out
of that note. Neither is ever an instruction.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

from . import (
    base_reader,
    compose_proposal,
    confirm,
    constants,
    formats,
    ids,
    names,
    paths,
    report,
    review,
    stale_check,
    state,
)
from .errors import GitError, GtmBaseError, PathError, ReviewError, ValidationError
from .fsutil import atomic_write_json, atomic_write_text, ensure_dir, read_json, read_text, remove
from .gitcmd import GitRunner, runner_or_default
from .validate import find_marker, validate_owner

# How a run of this module can end.
STATUS_SHOWN = "shown"
STATUS_APPLIED = "applied"
STATUS_KEPT = "kept"
STATUS_DROPPED = "dropped"
STATUS_REFUSED = "refused"
STATUS_CONFLICT = "conflict"
STATUS_MOVED = "moved"

# Codes this module records. They are for the log, not for a person.
CODE_HAS_SHARED_COPY = "has-shared-copy"
CODE_CANNOT_TELL = compose_proposal.CODE_CANNOT_TELL
CODE_NOT_WAITING_HERE = "not-where-prepared-changes-wait"
CODE_NOT_AN_OWNER = "not-an-owner"
CODE_NO_OWNER_RECORDED = "no-owner-recorded"
CODE_NO_ADDRESS = "no-address-for-this-seat"
CODE_OUTSIDE_ALLOWED = "path-outside-the-folders-a-change-may-touch"
CODE_ASSISTANT_FOLDER = "path-in-the-assistant-folder"
CODE_MARKER_DISAGREES = "marker-names-no-change-entry"
CODE_ALREADY_RECORDED = "already-recorded-here"
CODE_MOVED = "content-moved"
CODE_CONFLICT = compose_proposal.CODE_HEADING_MISSING
CODE_UNSAVED_EDITS = review.CODE_UNSAVED_EDITS
CODE_NOT_DEFAULT_BRANCH = review.CODE_NOT_DEFAULT_BRANCH
CODE_GIT_FAILED = "git-failed"
CODE_UNREADABLE = compose_proposal.CODE_UNREADABLE
CODE_NOTE_UNREADABLE = "note-of-unfinished-work-unreadable"
CODE_RESUMED = "unfinished-work-finished"
# A context change about one of the documents this would change is
# written down twice, and the two copies do not agree.
CODE_WRITTEN_TWICE = "one-change-written-twice"
CODE_UNDONE = "unfinished-work-undone"
# The words the prepared change would put in the file are still the first
# draft GTM Base wrote, which is a note asking for the real replacement.
CODE_STILL_A_PLACEHOLDER = "still-the-first-draft"

# The folder the assistant keeps its own settings in, which a prepared change
# may never touch whatever else it names.
ASSISTANT_DIR = ".claude"

# The folders the note left by an unfinished run may name, and nothing else.
NOTE_PATH_PREFIXES = paths.PROPOSAL_PATH_PREFIXES + (
    constants.CONFIRMATIONS_DIR + "/",
)

# The markers `docs/ux-standard.md` sets for what a person is shown. The
# complete thing they approve sits inside the artifact markers, and the four
# labeled lines sit inside the change markers.
ARTIFACT_OPEN = "<!-- artifact -->"
ARTIFACT_CLOSE = "<!-- end artifact -->"
CHANGE_OPEN = "<!-- change -->"
CHANGE_CLOSE = "<!-- end change -->"

# The four labels, in the one order they are ever shown in.
CHANGE_LABELS = (
    "What changed:",
    "Why:",
    "What it affects:",
    "When to look again:",
)

# The note left in this seat's folder while a change is being applied.
JOURNAL_FILE = "local-approval.json"
JOURNAL_SCHEMA = 2

# A whole hidden comment, which never appears in a line a person is shown.
_COMMENT_RE = re.compile(r"<!--.*?-->")

# The one way a saved point in a base is ever written. The note carries one,
# and the note goes onto a git command line, so nothing that is not this shape
# is allowed anywhere near one. The older move's note has always held its own
# saved point to exactly this.
_SAVED_POINT_RE = re.compile(r"^[0-9a-f]{40}$")

# --- The sentences a person reads -------------------------------------------

HAS_SHARED_COPY = (
    "This base has a shared copy, so a prepared change is raised for review "
    "there rather than approved here. Hand it to the propose-change skill."
)
NOT_WAITING_HERE = (
    "A prepared change is only ever read from the folder GTM Base keeps them "
    "waiting in, and that is not where this one is, so nothing was done."
)
NOT_AN_OWNER = (
    "Only an owner of %s can approve a change to it, and this base is set up "
    "under a different address. It is owned by %s."
)
NO_OWNER_RECORDED = (
    "%s does not say who owns it, so nobody can approve a change to it here."
)
NO_ADDRESS = (
    "GTM Base does not know which address this base is yours under, so it "
    "cannot tell whether you own what this change touches."
)
OUTSIDE_THE_FOLDERS = (
    "A prepared change may only touch your context files, the record of "
    "context changes, and the record of what was corrected, and this one "
    "names %s."
)
ASSISTANT_FOLDER = (
    "A prepared change may never touch the assistant's own folder, and this "
    "one names %s."
)
MARKER_DISAGREES = (
    "This prepared change carries a context change that its own marker does "
    "not name, so nothing was applied. Ask for it to be prepared again."
)
ALREADY_RECORDED = (
    "This prepared change has already been approved on this base, so nothing "
    "was applied a second time."
)
CONFLICT = (
    "The part of %s this prepared change rewrites is not there any more, so "
    "nothing was applied. Ask for the change to be prepared again."
)
MOVED = (
    "This prepared change moved after it was shown to you, so nothing was "
    "applied. Read it again and answer again."
)
UNSAVED_EDITS = (
    "You have edits in your base you have not saved, so nothing was applied. "
    "Put those somewhere safe and ask again."
)
NOT_ON_MAIN = (
    "Your base is not on its main line right now, so nothing was applied."
)
COULD_NOT_SAVE = (
    "GTM Base could not save the approved change, so nothing was applied. "
    "Nothing was lost, so ask again."
)
UNREADABLE = (
    "GTM Base could not read that prepared change, so nothing was applied."
)
STILL_A_PLACEHOLDER = (
    "The words this change would put in your document are still the note GTM "
    "Base wrote asking for the real wording, so nothing was applied. Write "
    "what the document should say now, show it beside what it says today, and "
    "ask again."
)
NOTE_UNREADABLE = (
    "GTM Base left a note about an unfinished change that it cannot make "
    "sense of, so it touched nothing at all. Ask somebody to look at it."
)
APPLIED = "%s now says what this change said, and you are recorded as approving it."
KEPT = "The prepared change is still waiting, and nothing in your base changed."
DROPPED = "The prepared change is gone, and nothing in your base changed."
ASK = "Approve this change, leave it for now, or drop it?"


# --- What comes back ---------------------------------------------------------


class LocalResult(object):
    """How one call ended, in the terms the skill reports to the person."""

    __slots__ = (
        "status",
        "staging_id",
        "codes",
        "reasons",
        "artifact",
        "shown_hash",
        "paths",
        "written_paths",
        "saved_work",
    )

    def __init__(
        self,
        status,
        staging_id=None,
        codes=None,
        reasons=None,
        artifact="",
        shown_hash=None,
        paths=None,
        written_paths=None,
        saved_work=None,
    ):
        self.status = status
        self.staging_id = staging_id
        self.codes = list(codes or [])
        self.reasons = list(reasons or [])
        self.artifact = artifact
        self.shown_hash = shown_hash
        self.paths = list(paths or [])
        self.written_paths = list(written_paths or [])
        self.saved_work = saved_work

    @property
    def refused(self) -> bool:
        return self.status in (STATUS_REFUSED, STATUS_CONFLICT, STATUS_MOVED)

    def __repr__(self) -> str:
        return "LocalResult(status=%r, staging_id=%r)" % (self.status, self.staging_id)


def _refused(status, code, sentence, staging_id=None) -> LocalResult:
    return LocalResult(
        status, staging_id=staging_id, codes=[code], reasons=[sentence]
    )


# --- Where a prepared change may be read from --------------------------------


def checked_staging_path(base_root: str, staging_path: str) -> Tuple[str, str]:
    """The one folder a prepared change may be read from, checked on the disk.

    Show, approve, and drop all come through here, because every one of them
    reads, moves, or writes over the file it is given. The file has to sit
    directly in the folder prepared changes wait in once every link is
    followed, and it has to be named after an identifier GTM Base issues, so a
    path from anywhere else can never be read as a prepared change and can
    never be moved or thrown away as one either.
    """
    folder = os.path.realpath(
        os.path.join(base_root, constants.PROPOSALS_PENDING_DIR)
    )
    resolved = os.path.realpath(str(staging_path or ""))
    if os.path.dirname(resolved) != folder:
        raise PathError(NOT_WAITING_HERE, code=CODE_NOT_WAITING_HERE)
    name = os.path.basename(resolved)
    if not name.endswith(".md"):
        raise PathError(NOT_WAITING_HERE, code=CODE_NOT_WAITING_HERE)
    staging_id = name[: -len(".md")]
    try:
        ids.check_staging_id(staging_id)
    except (ValueError, TypeError):
        raise PathError(NOT_WAITING_HERE, code=CODE_NOT_WAITING_HERE)
    return resolved, staging_id


# --- Reading the prepared change ---------------------------------------------


def _in_the_assistant_folder(relative: str) -> bool:
    """Whether a path names the assistant's own folder anywhere along it."""
    parts = [
        part.strip().lower() for part in str(relative).replace("\\", "/").split("/")
    ]
    return ASSISTANT_DIR in parts


def path_problems(staging) -> List[Tuple[str, str]]:
    """Every path this prepared change names that it may not touch.

    The folders a change may touch are the ones every proposal is held to, and
    the assistant's own folder is refused on top of them, because a path under
    it can sit inside an allowed folder and still change how the assistant
    behaves.
    """
    found: List[Tuple[str, str]] = []
    candidates: List[str] = []
    for value in list(staging.target_paths) + [edit.path for edit in staging.edits]:
        if value not in candidates:
            candidates.append(value)
    for value in _affects_of(staging):
        if value not in candidates:
            candidates.append(value)
    for candidate in candidates:
        if _in_the_assistant_folder(candidate):
            found.append((CODE_ASSISTANT_FOLDER, ASSISTANT_FOLDER % candidate))
            continue
        try:
            paths.check_repo_path_syntax(candidate, paths.PROPOSAL_PATH_PREFIXES)
        except PathError:
            found.append((CODE_OUTSIDE_ALLOWED, OUTSIDE_THE_FOLDERS % candidate))
    return found


def _carried_entry(staging):
    """The context change written inside this prepared change, if it carries one."""
    if not staging.decision_block:
        return None
    try:
        return formats.LedgerEntry.parse(staging.decision_block)
    except (ValidationError, PathError):
        return None


def _affects_of(staging) -> List[str]:
    entry = _carried_entry(staging)
    return list(entry.affects) if entry is not None else []


def _who_is_approving(base_root: str, git: GitRunner) -> Optional[str]:
    """The address this base records work under, which is who is answering."""
    return base_reader.repo_email(base_root, git)


def owners_of(base_root: str, relative: str) -> List[str]:
    """The addresses written on one context file as owning it."""
    text = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
    if text is None:
        return []
    try:
        block, _body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        return []
    try:
        return validate_owner(fields.get("owner"))
    except ValidationError:
        return []


def _owner_problems(base_root: str, ordered: List[str], address: Optional[str]):
    """Why the person answering may not approve this change, if they may not."""
    if not address:
        return [(CODE_NO_ADDRESS, NO_ADDRESS)]
    found = []
    for relative in ordered:
        owners = owners_of(base_root, relative)
        if not owners:
            found.append(
                (
                    CODE_NO_OWNER_RECORDED,
                    NO_OWNER_RECORDED % names.document_name(relative),
                )
            )
            continue
        if address not in owners:
            found.append(
                (
                    CODE_NOT_AN_OWNER,
                    NOT_AN_OWNER % (names.document_name(relative), ", ".join(owners)),
                )
            )
    return found


def _recorded_already(base_root: str, staging_id: str) -> bool:
    """Whether the record of what changed already holds this exact change."""
    folder = os.path.join(base_root, constants.CORRECTIONS_DIR)
    if not os.path.isdir(folder):
        return False
    wanted = "-%s.md" % staging_id
    return any(name.endswith(wanted) for name in os.listdir(folder))


# --- Applying the edits in order ---------------------------------------------


class _Walk(object):
    """Every file this change rewrites, and what each part said before and after."""

    __slots__ = ("texts", "steps", "ordered")

    def __init__(self, texts, steps, ordered):
        # texts maps a path to the whole file as this change would leave it.
        self.texts = texts
        # steps is one (path, heading, before, after) for each edit, in order.
        self.steps = steps
        self.ordered = ordered


def _walk_the_edits(base_root: str, staging) -> "_Walk":
    """Apply every edit to a copy held in memory, keeping each part's two states.

    The edits are applied one after another to the same text, so a second edit
    to one file is worked out against the answer the first one gave rather than
    against the file as it was before either of them. Nothing on the disk is
    touched here, so a change that no longer fits is found before anything is
    written.
    """
    texts: Dict[str, str] = {}
    steps: List[Tuple[str, str, str, str]] = []
    for edit in staging.edits:
        relative = paths.canonical_context_path(base_root, edit.path)
        if relative not in texts:
            text = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
            if text is None:
                raise compose_proposal.ConflictError(
                    "the file is not there any more", code=CODE_CONFLICT
                )
            texts[relative] = text
        before = _section_now(texts[relative], edit.heading)
        after_text = compose_proposal.apply_edit(texts[relative], edit)
        steps.append(
            (relative, edit.heading, before, _section_now(after_text, edit.heading))
        )
        texts[relative] = after_text
    return _Walk(texts, steps, compose_proposal.edited_paths(staging))


def _section_now(text: str, heading: str) -> str:
    """The words under one heading as this version of the file reads."""
    lines = text.split("\n")
    index = compose_proposal.find_heading(
        lines, heading, compose_proposal.frontmatter_end(lines)
    )
    if index < 0:
        return ""
    stop = compose_proposal.section_end(lines, index)
    return "\n".join(lines[index + 1 : stop]).strip("\n")


# --- The whole thing a person reads ------------------------------------------


def _one_line(text: str) -> str:
    """One line of plain words, with nothing in it that could close a block.

    A whole hidden comment is taken out rather than only its two ends, because
    what is inside one was written to be unread. The screens refuse hidden
    content long before this, so this is the second answer and not the first.
    """
    single = " ".join(str(text or "").split())
    single = _COMMENT_RE.sub(" ", single)
    single = single.replace("<!--", " ").replace("-->", " ")
    return " ".join(single.split())


def _quoted(text: str) -> str:
    """A piece of a file, marked as something read rather than written."""
    lines = str(text or "").strip("\n").split("\n")
    return "\n".join(("> " + line.rstrip()) if line.strip() else ">" for line in lines)


def _entry_for(base_root: str, staging, entry_id: Optional[str]):
    """The context change behind this prepared change, wherever it is written."""
    carried = _carried_entry(staging)
    if carried is not None:
        return carried
    if not entry_id:
        return None
    _relative, text = base_reader.entry_path_and_text(base_root, entry_id)
    if text is None:
        return None
    try:
        return formats.ChangeEntry.parse(text)
    except (ValidationError, PathError):
        return None


def _look_again_on(base_root: str, entry, today: datetime.date) -> str:
    """The day to look at this again: the change's own day, or the base's."""
    if entry is not None and entry.review_by:
        return entry.review_by
    settings = base_reader.settings_of(base_reader.map_text(base_root))
    days = int(settings.confirmation_threshold_days)
    return (today + datetime.timedelta(days=days)).isoformat()


def _affected_names(walk: "_Walk", entry) -> str:
    """Every document this change affects, named the way a person names it.

    The files it rewrites are not the whole answer. A context change can say it
    affects a document this change does not touch, and leaving that out would
    tell somebody the change reaches less far than it does.
    """
    ordered = list(walk.ordered)
    for path in list(entry.affects) if entry is not None else []:
        if path not in ordered:
            ordered.append(path)
    return ", ".join(names.document_name(path) for path in ordered)


def four_lines(base_root: str, staging, entry, walk, today) -> str:
    """One context change as the four labeled lines, and nothing else."""
    if entry is not None:
        what = names.change_name(entry.body, entry.decided_on)
    else:
        what = names.change_name(compose_proposal.summary_of(staging), None)
    body = formats.parse_pr_body(staging.pr_body)
    values = (
        _one_line(what),
        _one_line(body.get("why", "")),
        _affected_names(walk, entry),
        _look_again_on(base_root, entry, today),
    )
    lines = [CHANGE_OPEN]
    for label, value in zip(CHANGE_LABELS, values):
        lines.append("%s %s" % (label, value))
    lines.append(CHANGE_CLOSE)
    return "\n".join(lines)


def artifact_for(base_root: str, staging, entry, walk, today) -> str:
    """The whole prepared change, written out so nothing about it is hidden.

    The four labeled lines come first. Then, when the change carries a context
    change of its own, that change exactly as it will be written down, because
    a first sentence is not what gets written. Then every part of every file it
    changes, as that part reads now and as the change would leave it. This is
    what the yes is bound to, so none of it is ever shortened.
    """
    pieces = [ARTIFACT_OPEN, four_lines(base_root, staging, entry, walk, today), ""]
    carried = _carried_entry(staging)
    if carried is not None:
        pieces.append("The context change this carries, as it will be written down:")
        pieces.append("")
        pieces.append(_quoted(carried.render()))
        pieces.append("")
    for relative, heading, before, after in walk.steps:
        document = names.document_name(relative)
        part = _one_line(heading.lstrip("#"))
        pieces.append("The part of %s called %s, as it reads now:" % (document, part))
        pieces.append("")
        pieces.append(_quoted(before) if before.strip() else "> (nothing there yet)")
        pieces.append("")
        pieces.append(
            "The part of %s called %s, as this change would leave it:"
            % (document, part)
        )
        pieces.append("")
        pieces.append(_quoted(after))
        pieces.append("")
    pieces.append(ARTIFACT_CLOSE)
    return "\n".join(pieces).rstrip("\n") + "\n"


def _hash_of_parts(parts: List[str]) -> str:
    """One value standing for several pieces of text, in the order given.

    Each piece carries its own length, so two different sets of pieces can
    never add up to the same value by running into one another.
    """
    return ids.content_hash(
        "".join("%d:%s" % (len(part), part) for part in parts)
    )


def _shown_hash(staged_text: str, base_root: str, ordered: List[str]) -> str:
    """The value standing for exactly what was shown.

    Both the prepared change and the files it touches are in it on purpose. A
    yes has to be about the words that were read, and it also has to be about
    the file those words were read against, because either one moving makes the
    yes an answer to a different question.
    """
    parts = [staged_text]
    for relative in ordered:
        parts.append(
            read_text(os.path.join(base_root, relative.replace("/", os.sep))) or ""
        )
    return _hash_of_parts(parts)


# --- Reading and checking, which both calls do the same way -------------------


class _Reading(object):
    """One prepared change, read and checked once, ready to show or to write."""

    __slots__ = ("staging", "walk", "entry_id", "source_id", "artifact", "shown_hash")

    def __init__(self, staging, walk, entry_id, source_id, artifact, shown_hash):
        self.staging = staging
        self.walk = walk
        self.entry_id = entry_id
        self.source_id = source_id
        self.artifact = artifact
        self.shown_hash = shown_hash


def _read_and_check(base_root, base_id, staging_path, git, today):
    """Everything show and approve both do, in the one order they both do it.

    What comes back is either the refusal to report or the reading to work
    from. Both calls work from the same reading, so the words that get written
    can only be the words that were read out loud.
    """
    state_of_it = compose_proposal.shared_copy_state(base_root, runner=git)
    if state_of_it == compose_proposal.SHARED_COPY_PRESENT:
        return _refused(STATUS_REFUSED, CODE_HAS_SHARED_COPY, HAS_SHARED_COPY), None
    if state_of_it != compose_proposal.SHARED_COPY_ABSENT:
        return (
            _refused(STATUS_REFUSED, CODE_CANNOT_TELL, compose_proposal.CANNOT_TELL),
            None,
        )

    try:
        resolved, staging_id = checked_staging_path(base_root, staging_path)
    except PathError:
        return _refused(STATUS_REFUSED, CODE_NOT_WAITING_HERE, NOT_WAITING_HERE), None

    staged_text = read_text(resolved)
    if staged_text is None:
        return _refused(STATUS_REFUSED, CODE_UNREADABLE, UNREADABLE, staging_id), None
    try:
        staging = compose_proposal.load_staging(resolved)
    except GtmBaseError as failure:
        return (
            _refused(
                STATUS_REFUSED, failure.code or CODE_UNREADABLE, UNREADABLE, staging_id
            ),
            None,
        )

    problems = path_problems(staging)
    if problems:
        return _many(STATUS_REFUSED, staging.staging_id, problems), None
    edit_problems = compose_proposal.check_edits(base_root, staging)
    if edit_problems:
        return _many(STATUS_REFUSED, staging.staging_id, edit_problems), None

    marker_problems = compose_proposal.marker_problems(staging)
    if marker_problems:
        return _many(STATUS_REFUSED, staging.staging_id, marker_problems), None
    entry_id, source_id = _entry_ids(staging)
    if staging.decision_block and not entry_id:
        # The confirmation this writes names the context change, so a change
        # carried without its own marker naming it would leave the file
        # flagged against the very change that was just approved.
        return (
            _refused(
                STATUS_REFUSED, CODE_MARKER_DISAGREES, MARKER_DISAGREES, staging.staging_id
            ),
            None,
        )

    if _recorded_already(base_root, staging.staging_id):
        return (
            _refused(
                STATUS_REFUSED, CODE_ALREADY_RECORDED, ALREADY_RECORDED, staging.staging_id
            ),
            None,
        )

    # A document a context change is written down twice about, with the two
    # copies disagreeing, is not one anybody can approve a change to yet.
    # Applying one writes a confirmation naming that change, which would
    # settle a change nobody has read either copy of.
    for relative in _affects_of(staging) or list(staging.target_paths):
        disagreeing = confirm.refusal_while_written_twice(
            base_root, base_id, relative, today, git=git
        )
        if disagreeing is not None:
            return (
                _refused(
                    STATUS_REFUSED,
                    CODE_WRITTEN_TWICE,
                    disagreeing,
                    staging.staging_id,
                ),
                None,
            )

    # The same screens an outgoing proposal gets, because a base with no shared
    # copy becomes the shared copy the first time it is backed up.
    hits, _allowlist_code = compose_proposal.scan_everything(
        staging, base_root, extra=[_subject(staging)]
    )
    if hits:
        return (
            LocalResult(
                STATUS_REFUSED,
                staging_id=staging.staging_id,
                codes=[hit.pattern_class for hit in hits],
                reasons=[hit.sentence() for hit in hits],
            ),
            None,
        )

    try:
        walk = _walk_the_edits(base_root, staging)
    except compose_proposal.ConflictError:
        first = compose_proposal.edited_paths(staging)
        return (
            _refused(
                STATUS_CONFLICT,
                CODE_CONFLICT,
                CONFLICT % names.document_name(first[0]),
                staging.staging_id,
            ),
            None,
        )

    for _relative, _heading, _before, after in walk.steps:
        if stale_check.is_the_placeholder(after):
            return (
                _refused(
                    STATUS_REFUSED,
                    CODE_STILL_A_PLACEHOLDER,
                    STILL_A_PLACEHOLDER,
                    staging.staging_id,
                ),
                None,
            )

    owner_problems = _owner_problems(
        base_root, walk.ordered, _who_is_approving(base_root, git)
    )
    if owner_problems:
        return _many(STATUS_REFUSED, staging.staging_id, owner_problems), None

    entry = _entry_for(base_root, staging, entry_id)
    return None, _Reading(
        staging,
        walk,
        entry_id,
        source_id,
        artifact_for(base_root, staging, entry, walk, today),
        _shown_hash(staged_text, base_root, walk.ordered),
    )


def _many(status, staging_id, problems) -> LocalResult:
    return LocalResult(
        status,
        staging_id=staging_id,
        codes=[code for code, _ in problems],
        reasons=[sentence for _, sentence in problems],
    )


def _entry_ids(staging) -> Tuple[Optional[str], Optional[str]]:
    """The change and the source this prepared change names, if it names any."""
    parsed = find_marker(compose_proposal.marker_of(staging))
    entry_id = parsed[1] if parsed else None
    source_id = parsed[2] if parsed else staging.source_id
    return entry_id, source_id


# --- Showing it --------------------------------------------------------------


def show(
    staging_path: str,
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
) -> LocalResult:
    """Read one prepared change, screen it, and hand back the whole of it."""
    git = runner_or_default(runner)
    today = _day_of(now)
    codes: List[str] = []

    finished = _finish_unfinished_work(
        base_root, base_id, _name_of(staging_path), git, codes
    )
    if finished is not None:
        return finished

    refusal, reading = _read_and_check(base_root, base_id, staging_path, git, today)
    if refusal is not None:
        return refusal
    return LocalResult(
        STATUS_SHOWN,
        staging_id=reading.staging.staging_id,
        codes=codes,
        reasons=[ASK],
        artifact=reading.artifact,
        shown_hash=reading.shown_hash,
        paths=list(reading.walk.ordered),
    )


def _day_of(now) -> datetime.date:
    """The day a caller meant, without moving it across a change of zone."""
    if isinstance(now, datetime.datetime):
        return state.today(now)
    if isinstance(now, datetime.date):
        return now
    return state.today()


def _moment_of(now) -> datetime.datetime:
    """The time of day to record, which a caller giving only a day leaves open."""
    if isinstance(now, datetime.datetime):
        return now
    if isinstance(now, datetime.date):
        return datetime.datetime(now.year, now.month, now.day)
    return state.now_utc()


def _name_of(staging_path: str) -> str:
    """The identifier a prepared change is filed under, read off its name."""
    name = os.path.basename(str(staging_path or ""))
    return name[: -len(".md")] if name.endswith(".md") else name


# --- What this run is about to write -----------------------------------------


class _Plan(object):
    """Every path this run will write, with the content it will put there."""

    __slots__ = ("files", "confirmations", "subject", "staging", "ordered")

    def __init__(self, files, confirmations, subject, staging, ordered):
        # Each item is (path, text, whether the base already holds that path).
        self.files = files
        self.confirmations = confirmations
        self.subject = subject
        self.staging = staging
        self.ordered = ordered

    def everything(self):
        return list(self.files) + list(self.confirmations)


def _in_head(base_root: str, relative: str, git: GitRunner) -> bool:
    return git.run(["cat-file", "-e", "HEAD:" + relative], cwd=base_root).ok


def _head_text(base_root: str, relative: str, git: GitRunner) -> Optional[str]:
    shown = git.run(["show", "HEAD:" + relative], cwd=base_root)
    return shown.stdout if shown.ok else None


def _subject(staging) -> str:
    """The note saved with the work, which a repeat run recognises."""
    return "%s%s: %s" % (
        report.LOCAL_APPROVAL_COMMIT_PREFIX,
        staging.staging_id,
        compose_proposal.summary_of(staging)[
            : compose_proposal.COMMIT_SUMMARY_CHARS
        ].strip(),
    )


def _plan_the_writes(base_root, reading, today, moment, git) -> "_Plan":
    """Work out every path and every byte before a single one is written."""
    staging = reading.staging
    walk = reading.walk
    files: List[Tuple[str, str, bool]] = []
    for relative in walk.ordered:
        files.append((relative, walk.texts[relative], _in_head(base_root, relative, git)))

    touched = list(walk.ordered)
    carried = _carried_entry(staging)
    if carried is not None:
        entry = compose_proposal.ledger_entry_for(staging, today)
        entry_path = base_reader.where_to_write_the_entry(base_root, entry.id)
        if os.path.lexists(os.path.join(base_root, entry_path.replace("/", os.sep))):
            raise ValidationError(ALREADY_RECORDED, code=CODE_ALREADY_RECORDED)
        files.append((entry_path, entry.render(), False))
        touched.append(entry_path)

    # The plain run of the finished files, which is the same value the record
    # of what changed is read back against later.
    hash_value = ids.content_hash("".join(walk.texts[path] for path in walk.ordered))
    correction = compose_proposal.corrections_for(
        staging, today, hash_value, touched, reading.entry_id, reading.source_id
    )
    correction_path = "%s/%s-%s.md" % (
        constants.CORRECTIONS_DIR,
        today.isoformat(),
        staging.staging_id,
    )
    if os.path.lexists(os.path.join(base_root, correction_path.replace("/", os.sep))):
        raise ValidationError(ALREADY_RECORDED, code=CODE_ALREADY_RECORDED)
    files.append((correction_path, correction.render(), False))

    confirmations: List[Tuple[str, str, bool]] = []
    for relative in walk.ordered:
        line = formats.ConfirmationLine(
            date=today.isoformat(),
            time=moment.strftime("%H:%M:%SZ"),
            file=relative,
            trigger="ledger" if reading.entry_id else "threshold",
            entry=reading.entry_id if reading.entry_id else None,
            question=None,
            run=None,
        )
        line.validate()
        target = confirm.confirmations_path_for(relative)
        full = confirm.checked_confirmations_path(base_root, target)
        existing = read_text(full)
        if existing is None:
            text = confirm.FILE_HEADER + line.render() + "\n"
        else:
            if existing and not existing.endswith("\n"):
                existing += "\n"
            text = existing + line.render() + "\n"
        confirmations.append((target, text, _in_head(base_root, target, git)))

    return _Plan(files, confirmations, _subject(staging), staging, list(walk.ordered))


# --- The note that makes a half finished run recoverable ----------------------


def _journal_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), JOURNAL_FILE)


def _load_journal(base_id: str) -> Optional[dict]:
    """The note as it was written, read as data and checked by the caller."""
    payload = read_json(_journal_path(base_id))
    if not isinstance(payload, dict):
        return None
    if payload.get("schema") != JOURNAL_SCHEMA:
        return None
    return payload


def _checked_journal(base_id: str, base_root: str):
    """The note, with every value in it checked, or the reason it was refused.

    The note is a file on the disk like any other, so nothing in it is believed
    on sight. A path it names has to be one of the folders this module writes
    to, it has to stay inside this base once every link is followed, and the
    note has to say it is about this base at all.

    Two more things are checked since the 2026-09-20 review, and the note
    behind the older move had been checked for both all along. The saved point
    has to be written the one way a saved point is written, because it goes
    onto a git command line and a reviewer wrote an option there instead and
    got git to write a file of their choosing. And the list of paths has to
    hold something: a run that wrote nothing leaves no note at all, so a note
    saying a run wrote nothing is not one this module left, and taking that at
    its word dropped a prepared change and called it approved.
    """
    payload = _load_journal(base_id)
    if payload is None:
        return None, None
    try:
        ids.check_staging_id(str(payload.get("staging_id") or ""))
    except (ValueError, TypeError):
        return None, "the note names no change we issued"
    recorded = str(payload.get("base_root") or "")
    if not recorded or os.path.realpath(recorded) != os.path.realpath(base_root):
        return None, "the note is about another base"
    if not _SAVED_POINT_RE.match(str(payload.get("head") or "")):
        return None, "the note does not say where the base stood"
    items = payload.get("paths")
    if not isinstance(items, list) or not items:
        return None, "the note lists no paths"
    real_base = os.path.realpath(base_root)
    for item in items:
        if not isinstance(item, dict):
            return None, "the note holds something that is not a path"
        relative = str(item.get("path") or "")
        try:
            paths.check_repo_path_syntax(relative, NOTE_PATH_PREFIXES)
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        settled = os.path.realpath(os.path.join(base_root, relative))
        if settled != real_base and not settled.startswith(real_base + os.sep):
            return None, "the note names a path outside this base"
    return payload, None


def _write_journal(base_id: str, base_root: str, plan: "_Plan", head: str) -> None:
    atomic_write_json(
        _journal_path(base_id),
        {
            "schema": JOURNAL_SCHEMA,
            "staging_id": plan.staging.staging_id,
            "base_root": os.path.realpath(base_root),
            "subject": plan.subject,
            "head": head,
            "paths": [
                {
                    "path": relative,
                    "hash": ids.content_hash(text),
                    "in_head": bool(in_head),
                }
                for relative, text, in_head in plan.everything()
            ],
            "started_at": state.iso_utc(),
        },
    )


def _clear_journal(base_id: str) -> None:
    remove(_journal_path(base_id))


def _already_saved(base_root: str, journal: dict, git: GitRunner) -> bool:
    """Whether this run's own work was already saved, whatever came after it.

    The note carries where the base stood before the run started, so the look
    is over what was saved since then rather than at the newest note alone. A
    run that stopped after saving, and was followed by somebody saving
    something else, is still a run whose work landed.

    Since the 2026-09-20 review the saved work has to have touched the paths
    the note names as well as carrying the words the note names. A subject on
    its own was enough before, and a subject is text anybody can save with any
    work at all, so a note naming a prepared change nobody had read reported
    it applied and dropped it.
    """
    head = str(journal.get("head") or "")
    subject = str(journal.get("subject") or "")
    wanted = [
        str(item.get("path"))
        for item in journal.get("paths") or []
        if isinstance(item, dict) and item.get("path")
    ]
    if not head or not subject or not wanted:
        return False
    found = git.run(
        ["log", "--format=%H %s", "%s..HEAD" % head, "--"] + wanted, cwd=base_root
    )
    if not found.ok:
        return False
    for line in found.stdout.split("\n"):
        if line.strip().split(" ", 1)[-1].strip() == subject:
            return True
    return False


def _undo_own_work(base_root: str, items: List[dict], git: GitRunner):
    """Put back every path this run wrote and did not save, and nothing else.

    A path is only put back when what is on the disk is exactly what this run
    was going to write there. A path holding what the base already held is
    left alone, because nothing was ever written to it. Anything else on one
    of those paths is the person's own work, and it is left exactly as they
    left it.

    What comes back is two lists: the paths holding the person's own work, and
    the paths this run could not put back at all. They are kept apart because
    they are two different sentences, and the person can do something about
    the first one.
    """
    theirs: List[str] = []
    stuck: List[str] = []
    for item in items:
        relative = str(item.get("path"))
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text(full)
        if current is None:
            continue
        ours = ids.content_hash(current) == str(item.get("hash"))
        if not ours:
            if item.get("in_head"):
                held = _head_text(base_root, relative, git)
                if held is not None and ids.content_hash(held) == ids.content_hash(
                    current
                ):
                    continue
            theirs.append(relative)
            continue
        try:
            if item.get("in_head"):
                git.check(["checkout", "HEAD", "--", relative], cwd=base_root)
            else:
                git.check(
                    ["rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", relative],
                    cwd=base_root,
                )
                remove(full)
                if os.path.lexists(full):
                    stuck.append(relative)
        except GitError:
            stuck.append(relative)
    return theirs, stuck


def _finish_unfinished_work(
    base_root: str, base_id: str, staging_id: str, git: GitRunner, codes: List[str]
) -> Optional[LocalResult]:
    """Deal with a run of this module that stopped halfway, before anything else.

    Work that was already saved is finished off, which is the same final state
    a run that never stopped would have left. Work that was not saved is
    undone, and a path that could not be put back keeps the note and stops the
    run, because a note thrown away is a run nobody can finish.
    """
    journal, problem = _checked_journal(base_id, base_root)
    if problem is not None:
        return _refused(STATUS_REFUSED, CODE_NOTE_UNREADABLE, NOTE_UNREADABLE)
    if not journal:
        return None
    items = [item for item in journal.get("paths") or []]
    its_id = str(journal.get("staging_id") or "")

    if _already_saved(base_root, journal, git):
        staged = os.path.join(
            base_root, constants.PROPOSALS_PENDING_DIR, its_id + ".md"
        )
        compose_proposal.retire(base_root, staged, its_id)
        _clear_journal(base_id)
        if its_id != staging_id:
            return None
        ordered = [
            str(item.get("path"))
            for item in items
            if str(item.get("path", "")).startswith(constants.CONTEXT_DIR + "/")
        ]
        codes.append(CODE_RESUMED)
        return LocalResult(
            STATUS_APPLIED,
            staging_id=its_id,
            codes=list(codes),
            reasons=[APPLIED % ", ".join(names.document_name(path) for path in ordered)],
            paths=ordered,
            written_paths=[str(item.get("path")) for item in items],
            saved_work=git.run(["rev-parse", "HEAD"], cwd=base_root).out(),
        )

    theirs, stuck = _undo_own_work(base_root, items, git)
    if stuck:
        return _refused(STATUS_REFUSED, CODE_GIT_FAILED, COULD_NOT_SAVE, its_id)
    if theirs:
        # Their own words are sitting on a path this run wrote to, so the note
        # stays and they are asked to deal with it. Nothing of theirs is lost.
        return _refused(STATUS_REFUSED, CODE_UNSAVED_EDITS, UNSAVED_EDITS, its_id)
    _clear_journal(base_id)
    codes.append(CODE_UNDONE)
    return None


# --- Writing it --------------------------------------------------------------


def _write_the_files(base_root: str, plan: "_Plan") -> List[str]:
    """Put down every file this change rewrites, and the records beside them."""
    written = []
    for relative, text, _in_head in plan.files:
        atomic_write_text(
            os.path.join(base_root, relative.replace("/", os.sep)),
            text,
            mode=0o644,
            inside=base_root,
        )
        written.append(relative)
    return written


def _stage_the_files(base_root: str, written: List[str], git: GitRunner) -> None:
    git.check(["add", "--"] + list(written), cwd=base_root)


def _write_the_confirmation_lines(
    base_root: str, plan: "_Plan", git: GitRunner
) -> List[str]:
    """Record the owner's yes about every file this change rewrites.

    An owner accepting a change is that owner saying the file is right, which
    was settled on the sixth of September, so the same yes that applies the
    change is what the currency check reads later.
    """
    written = []
    for relative, text, _in_head in plan.confirmations:
        full = confirm.checked_confirmations_path(base_root, relative)
        atomic_write_text(full, text, mode=0o644, inside=base_root)
        written.append(relative)
    git.check(["add", "--"] + written, cwd=base_root)
    return written


def _save_the_work(base_root: str, plan: "_Plan", git: GitRunner, codes) -> str:
    name, address, author_codes = compose_proposal._author(base_root, git)
    codes.extend(author_codes)
    git.check(
        [
            "-c",
            "user.name=%s" % name,
            "-c",
            "user.email=%s" % address,
            "commit",
            "-q",
            "-m",
            plan.subject,
        ],
        cwd=base_root,
    )
    return git.run(["rev-parse", "HEAD"], cwd=base_root).out()


def _ready_to_write_here(base_root: str, git: GitRunner, changing: List[str]):
    """Refuse on a folder with anything half done in it that is not this change.

    The ordinary rule is that nothing is written into a base while there is
    anything unsaved in it. A change the person made by hand breaks that rule
    by existing: their edit is the unsaved work, and it is the very thing they
    are approving, so the ordinary rule refused every hand edit on a base with
    no shared copy and the habit had nowhere to end (findings A4 and H2).

    So the files this change is about are allowed to be unsaved, and nothing
    else is. Nothing is weakened by that. The yes is still bound to a value
    taken over the staged change and over the current bytes of exactly these
    files, so an edit that moved between being shown and being approved is
    still refused, and any other unsaved work anywhere in the base still stops
    the run with the sentence it always did.
    """
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        return CODE_NOT_DEFAULT_BRANCH, NOT_ON_MAIN
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok:
        return CODE_GIT_FAILED, COULD_NOT_SAVE
    allowed = set(changing)
    # The whole output, not the trimmed form. The first two characters of a
    # line say what state a path is in and the first of them is often a space,
    # so trimming the output moves every path along by one character.
    for line in status.stdout.split("\n"):
        if not line.strip():
            continue
        named = _paths_on_a_status_line(line)
        if not named or any(item not in allowed for item in named):
            return CODE_UNSAVED_EDITS, UNSAVED_EDITS
    return None


def _paths_on_a_status_line(line: str) -> List[str]:
    """Every path one line of the folder's state names, or nothing at all.

    A line nobody here can read gives back nothing, which the caller treats as
    unsaved work it may not write over. Guessing at a line would be the one
    way this check could let something through.
    """
    body = line[3:] if len(line) > 3 else ""
    if not body:
        return []
    if " -> " in body:
        pieces = body.split(" -> ")
    else:
        pieces = [body]
    named = []
    for piece in pieces:
        value = piece.strip()
        if value.startswith('"') and value.endswith('"') and len(value) > 1:
            # A quoted name holds characters git escapes, so it is not a plain
            # path and this check will not read it.
            return []
        if not value:
            return []
        named.append(value)
    return named


def approve(
    staging_path: str,
    base_root: str,
    base_id: str,
    shown_hash: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> LocalResult:
    """Apply the prepared change the owner just read, and record their yes."""
    git = runner_or_default(runner)
    moment = _moment_of(now)
    today = _day_of(now)
    codes: List[str] = []

    if compose_proposal.shared_copy_state(base_root, runner=git) != (
        compose_proposal.SHARED_COPY_ABSENT
    ):
        return _read_and_check(base_root, base_id, staging_path, git, today)[0]

    finished = _finish_unfinished_work(
        base_root, base_id, _name_of(staging_path), git, codes
    )
    if finished is not None:
        return finished

    refusal, reading = _read_and_check(base_root, base_id, staging_path, git, today)
    if refusal is not None:
        return refusal
    if not shown_hash or shown_hash != reading.shown_hash:
        return _refused(STATUS_MOVED, CODE_MOVED, MOVED, reading.staging.staging_id)

    stopped = _ready_to_write_here(base_root, git, reading.walk.ordered)
    if stopped is not None:
        code, sentence = stopped
        return _refused(
            STATUS_REFUSED, code, sentence, reading.staging.staging_id
        )

    try:
        plan = _plan_the_writes(base_root, reading, today, moment, git)
    except GtmBaseError as failure:
        return _refused(
            STATUS_REFUSED,
            failure.code or CODE_GIT_FAILED,
            ALREADY_RECORDED
            if failure.code == CODE_ALREADY_RECORDED
            else COULD_NOT_SAVE,
            reading.staging.staging_id,
        )

    head = git.run(["rev-parse", "HEAD"], cwd=base_root).out()
    _write_journal(base_id, base_root, plan, head)

    try:
        written = _write_the_files(base_root, plan)
        _stage_the_files(base_root, written, git)
        written.extend(_write_the_confirmation_lines(base_root, plan, git))
        saved = _save_the_work(base_root, plan, git, codes)
    except GtmBaseError as failure:
        theirs, stuck = _undo_own_work(
            base_root,
            [
                {
                    "path": relative,
                    "hash": ids.content_hash(text),
                    "in_head": in_head,
                }
                for relative, text, in_head in plan.everything()
            ],
            git,
        )
        if not stuck and not theirs:
            _clear_journal(base_id)
        codes.append(failure.code or CODE_GIT_FAILED)
        return LocalResult(
            STATUS_REFUSED,
            staging_id=plan.staging.staging_id,
            codes=codes,
            reasons=[COULD_NOT_SAVE],
        )

    compose_proposal.retire(base_root, staging_path, plan.staging.staging_id)
    _clear_journal(base_id)
    return LocalResult(
        STATUS_APPLIED,
        staging_id=plan.staging.staging_id,
        codes=codes,
        reasons=[
            APPLIED % ", ".join(names.document_name(path) for path in plan.ordered)
        ],
        paths=list(plan.ordered),
        written_paths=written,
        saved_work=saved,
    )


# --- The two other answers ---------------------------------------------------


def keep(staging_path: str) -> LocalResult:
    """Leave the prepared change where it is, and write nothing anywhere."""
    return LocalResult(
        STATUS_KEPT, staging_id=_name_of(staging_path), reasons=[KEPT]
    )


def drop(
    staging_path: str,
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
) -> LocalResult:
    """Throw the prepared change away. The file it was about stays as it is.

    It is put in the folder of changes nobody wanted rather than deleted, for
    two reasons. Nothing this module does should ever delete a file outright,
    and the next check has to be able to tell that this change was decided
    about, so the same change is not prepared all over again tomorrow.
    """
    git = runner_or_default(runner)
    codes: List[str] = []

    finished = _finish_unfinished_work(
        base_root, base_id, _name_of(staging_path), git, codes
    )
    if finished is not None:
        return finished

    try:
        resolved, staging_id = checked_staging_path(base_root, staging_path)
        compose_proposal.load_staging(resolved)
    except PathError:
        return _refused(STATUS_REFUSED, CODE_NOT_WAITING_HERE, NOT_WAITING_HERE)
    except GtmBaseError as failure:
        return _refused(
            STATUS_REFUSED, failure.code or CODE_UNREADABLE, UNREADABLE, staging_id
        )

    folder = ensure_dir(os.path.join(base_root, constants.PROPOSALS_DROPPED_DIR))
    shutil.move(resolved, os.path.join(folder, staging_id + ".md"))
    return LocalResult(
        STATUS_DROPPED, staging_id=staging_id, codes=codes, reasons=[DROPPED]
    )


# --- What is waiting to be approved ------------------------------------------


def waiting(
    base_root: str, runner: Optional[GitRunner] = None
) -> List[Tuple[str, List[str]]]:
    """Every prepared change waiting on a yes that could actually be given.

    Only the folder prepared changes wait in is read. A change that cannot be
    read, one whose file is no longer in the base, and one about a file this
    seat does not own are all left out, because naming a change nobody here can
    approve is a list item that wastes somebody's afternoon.
    """
    git = runner_or_default(runner)
    folder = os.path.join(base_root, constants.PROPOSALS_PENDING_DIR)
    if not os.path.isdir(folder):
        return []
    address = _who_is_approving(base_root, git)
    found: List[Tuple[str, List[str]]] = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        text = read_text(os.path.join(folder, name))
        if text is None:
            continue
        try:
            staging = formats.ProposalStaging.parse(text).validate()
        except (ValidationError, PathError):
            continue
        targets = compose_proposal.edited_paths(staging)
        if not targets:
            continue
        if any(
            not os.path.isfile(
                os.path.join(base_root, path.replace("/", os.sep))
            )
            for path in targets
        ):
            continue
        if _owner_problems(base_root, targets, address):
            continue
        found.append((staging.staging_id, targets))
    return found
