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
import difflib
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
from .fsutil import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    ensure_dir,
    read_bytes,
    read_json,
    read_text,
    read_text_exactly,
    remove,
)
from .gitcmd import GitRunner, runner_or_default, status_entries
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
# The prepared hand edit says one thing and the document says another, because
# the person went on working on it after the change was prepared.
CODE_PREPARED_FROM_OLDER = "prepared-from-an-older-version"
# A copy of the document could not be taken, so nothing may be written.
CODE_COULD_NOT_KEEP = "could-not-keep-a-copy"

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
JOURNAL_SCHEMA = 3

# The folder beside that note holding the exact bytes each file it names had
# before this run touched anything. Finding V4 of the 2026-09-20 verification
# round: a change somebody made by hand is unsaved by definition, so putting a
# file back the way it was last saved is how their own words were lost.
ORIGINALS_DIR = "local-approval-originals"

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
PREPARED_FROM_OLDER = (
    "You have kept working on %s since this change was prepared from it, so "
    "what the change holds is not what your document says now and nothing was "
    "applied. Ask for it to be prepared again from what it says today."
)
COULD_NOT_KEEP = (
    "GTM Base could not take a copy of %s to put back if anything went wrong, "
    "so it did nothing at all rather than risk your own writing."
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
# How a part taken out by a change is introduced in what a person reads, and
# how one of several parts with the same heading is named (finding R10 of
# Astra's third look).
PART_TAKEN_OUT_NOW = (
    "The part of %s called %s, which this change takes out, as it reads now:"
)
PART_OF_SEVERAL = "%s, the %s part with that heading"
# Said under the whole difference of a document when some of what changed is
# only spaces, tabs, or line endings, which a reader cannot see in the literal
# difference above it (finding R8 of Astra's third look).
WHITESPACE_ONLY = (
    "Some of what changed in %s is only spaces, tabs, or line endings, which "
    "do not show above. Here are those lines again with every space shown as "
    "\u00b7, every tab as \u2192, and every extra line-ending character as "
    "\u240d."
)


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


def owners_of(base_root: str, relative: str, git=None) -> List[str]:
    """The addresses written on one context file as owning it.

    The saved version answers, not the one in front of the person. Finding M5
    of the third look: on the hand-edit path the working file is by definition
    edited, and somebody who is not an owner made themselves one by rewriting
    that line in the same edit they were asking to have approved. A file the
    base has never saved has no saved version, and there the working one is
    all there is.
    """
    runner = runner_or_default(git)
    text = _head_text(base_root, relative, runner)
    if text is None:
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


def _owner_problems(
    base_root: str, ordered: List[str], address: Optional[str], git=None
):
    """Why the person answering may not approve this change, if they may not."""
    if not address:
        return [(CODE_NO_ADDRESS, NO_ADDRESS)]
    found = []
    for relative in ordered:
        owners = owners_of(base_root, relative, git)
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

    __slots__ = ("texts", "steps", "ordered", "leave_alone", "kinds")

    def __init__(self, texts, steps, ordered, leave_alone=None, kinds=None):
        # texts maps a path to the whole file as this change would leave it.
        self.texts = texts
        # steps is one (path, heading, before, after) for each edit, in order.
        self.steps = steps
        self.ordered = ordered
        # The paths this change does not write at all, because the file in
        # front of the person already is the change (finding N1).
        self.leave_alone = set(leave_alone or [])
        # One (operation, which of its heading, how many share that heading)
        # for each step, so a part taken out and one of two parts with the
        # same heading can be said as what they are (finding R10).
        self.kinds = list(kinds or [(None, 1, 1)] * len(steps))


def _walk_a_hand_edit(base_root: str, staging, git: GitRunner) -> "_Walk":
    """What a change somebody made by hand would leave, which is what is there.

    Finding N1 of the final confirmation pass. This used to apply the staged
    edits on top of the document they were taken from and ask for the answer
    to equal the document. That only holds where applying an edit twice is the
    same as applying it once, and six ordinary shapes of edit are not: a
    document with no newline at its end, an edit that takes that newline away
    or leaves two blank lines, a part added by hand, a heading renamed, and
    words under a part that has smaller parts under it. Every one of them was
    refused as moved straight after being prepared.

    So nothing is applied. The document as it sits on the disk is what saying
    yes saves, byte for byte, which also stops a document whose lines end the
    other way being rewritten on the way through (finding N8). What each part
    said before is read from the last saved version, and what it says now is
    read from the document.
    """
    texts: Dict[str, str] = {}
    steps: List[Tuple[str, str, str, str]] = []
    kinds: List[Tuple[Optional[str], int, int]] = []
    # Every document the person changed, whatever the parts describe (R10).
    ordered = compose_proposal.hand_edit_targets(staging)
    for relative in ordered:
        now = read_text_exactly(
            os.path.join(base_root, relative.replace("/", os.sep))
        )
        if now is None:
            raise compose_proposal.ConflictError(
                "the file is not there any more", code=CODE_CONFLICT
            )
        texts[relative] = now
    for one in staging.edits:
        relative = paths.canonical_context_path(base_root, one.path)
        was = _head_text(base_root, relative, git) or ""
        now = texts.get(relative)
        if now is None:
            now = read_text_exactly(
                os.path.join(base_root, relative.replace("/", os.sep))
            ) or ""
        which = getattr(one, "occurrence", 1)
        steps.append(
            (
                relative,
                one.heading,
                _section_now(was, one.heading, which),
                "" if one.op == "remove" else _section_now(now, one.heading, which),
            )
        )
        kinds.append(
            (one.op, which, max(_how_many(was, one.heading), _how_many(now, one.heading)))
        )
    return _Walk(texts, steps, ordered, leave_alone=ordered, kinds=kinds)


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
    kinds: List[Tuple[Optional[str], int, int]] = []
    for said, edit in zip(
        staging.edits, compose_proposal.in_original_positions(staging.edits)
    ):
        relative = paths.canonical_context_path(base_root, edit.path)
        if relative not in texts:
            text = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
            if text is None:
                raise compose_proposal.ConflictError(
                    "the file is not there any more", code=CODE_CONFLICT
                )
            texts[relative] = text
        which = getattr(edit, "occurrence", 1)
        before = _section_now(texts[relative], edit.heading, which)
        after_text = compose_proposal.apply_edit(texts[relative], edit)
        steps.append(
            (
                relative,
                edit.heading,
                before,
                ""
                if edit.op == "remove"
                else _section_now(after_text, edit.heading, which),
            )
        )
        kinds.append(
            (
                edit.op,
                # Which part it was in the document as it stood, which is the
                # one the person reads about.
                getattr(said, "occurrence", 1),
                max(
                    _how_many(texts[relative], edit.heading),
                    _how_many(after_text, edit.heading),
                ),
            )
        )
        texts[relative] = after_text
    return _Walk(
        texts, steps, compose_proposal.edited_paths(staging), kinds=kinds
    )


def _how_many(text: str, heading: str) -> int:
    """How many parts of this version of the file carry this heading."""
    lines = text.split("\n")
    wanted = (heading or "").strip()
    return sum(
        1
        for line in lines[compose_proposal.frontmatter_end(lines) :]
        if wanted and line.strip() == wanted
    )


def _section_now(text: str, heading: str, occurrence: int = 1) -> str:
    """The words under one heading as this version of the file reads."""
    lines = text.split("\n")
    index = compose_proposal.find_heading(
        lines, heading, compose_proposal.frontmatter_end(lines), occurrence
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


_BACKTICKS_RE = re.compile(r"`+")


def _fenced(text: str, language: str = "") -> str:
    """Text inside a fence no run of backticks in it can close.

    Finding R8 of Astra's third look. The whole difference was shown as quoted
    text, which a screen renders: an image added by hand showed as a picture,
    a link hid where it went, and spaces at the end of a line were taken off.
    Inside a fence it is shown as the characters it is, and the fence is one
    backtick longer than the longest run of them in the text.
    """
    longest = max((len(run) for run in _BACKTICKS_RE.findall(text)), default=0)
    fence = "`" * max(3, longest + 1)
    return "%s%s\n%s\n%s" % (fence, language, text, fence)


def _visible(line: str) -> str:
    """One line with its spaces, tabs, and return characters made visible."""
    return (
        line.replace(" ", "\u00b7").replace("\t", "\u2192").replace("\r", "\u240d")
    )


def _whitespace_lines(difference: str) -> List[str]:
    """The lines of a difference whose change a reader could not see.

    A line with spaces or tabs at its end, a line holding a tab or a return
    character, a line of nothing but spaces, and a line taken out and put back
    with only its spacing changed.
    """
    found: List[str] = []
    taken: List[str] = []
    added: List[str] = []
    for line in difference.split("\n"):
        if not line or line[0] not in "+-":
            continue
        body = line[1:]
        (taken if line[0] == "-" else added).append(line)
        if (
            body != body.rstrip()
            or "\t" in body
            or "\r" in body
            or (body and not body.strip())
        ):
            if line not in found:
                found.append(line)
    squeezed = lambda text: re.sub(r"\s+", "", text[1:])
    for one in taken:
        for other in added:
            if one[1:] != other[1:] and squeezed(one) == squeezed(other):
                for line in (one, other):
                    if line not in found:
                        found.append(line)
    return found


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


def whole_difference(base_root: str, ordered: List[str], git: GitRunner) -> Dict[str, str]:
    """Everything each of these files says now that it did not say when saved.

    Finding V5 of the 2026-09-20 verification round. A change somebody made by
    hand is approved with the file still unsaved, and approval saves the whole
    file rather than the part the change is about, so an unrelated edit further
    down the same document went in unread. The answer is not to save less, it
    is to show all of it: this is the whole of what saving the file would put
    down, and it is what the yes is bound to.
    """
    found: Dict[str, str] = {}
    for relative in ordered:
        was = _head_text(base_root, relative, git) or ""
        now = (
            read_text_exactly(
                os.path.join(base_root, relative.replace("/", os.sep))
            )
            or ""
        )
        lines = list(
            difflib.unified_diff(
                was.split("\n"), now.split("\n"), n=3, lineterm=""
            )
        )
        # The first two lines of that form name the two sides, which a person
        # reading this already knows, so they are left out.
        found[relative] = "\n".join(lines[2:]) if len(lines) > 2 else ""
    return found


def artifact_for(base_root: str, staging, entry, walk, today, differences=None) -> str:
    """The whole prepared change, written out so nothing about it is hidden.

    The four labeled lines come first. Then, when the change carries a context
    change of its own, that change exactly as it will be written down, because
    a first sentence is not what gets written. Then every part of every file it
    changes, as that part reads now and as the change would leave it. This is
    what the yes is bound to, so none of it is ever shortened.

    A change somebody made by hand ends with one more thing: everything in each
    document that is different from the last time it was saved, all of it,
    because that is what saying yes to one of those writes down.
    """
    pieces = [ARTIFACT_OPEN, four_lines(base_root, staging, entry, walk, today), ""]
    carried = _carried_entry(staging)
    if carried is not None:
        pieces.append("The context change this carries, as it will be written down:")
        pieces.append("")
        pieces.append(_quoted(carried.render()))
        pieces.append("")
    for (relative, heading, before, after), (operation, which, count) in zip(
        walk.steps, walk.kinds
    ):
        document = names.document_name(relative)
        part = _one_line(heading.lstrip("#"))
        if count > 1:
            part = PART_OF_SEVERAL % (part, _ordinal(which))
        if operation == "remove":
            pieces.append(PART_TAKEN_OUT_NOW % (document, part))
            pieces.append("")
            pieces.append(_quoted(before) if before.strip() else "> (nothing there)")
            pieces.append("")
            continue
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
    for relative in walk.ordered:
        text = (differences or {}).get(relative)
        if text is None:
            continue
        document = names.document_name(relative)
        pieces.append(
            "Everything in %s that is different from the last time it was "
            "saved, which is all of what saying yes to this writes down:"
            % document
        )
        pieces.append("")
        if not text.strip():
            pieces.append("> (nothing is different)")
            pieces.append("")
            continue
        pieces.append(_fenced(text, "diff"))
        pieces.append("")
        hidden = _whitespace_lines(text)
        if hidden:
            pieces.append(WHITESPACE_ONLY % document)
            pieces.append("")
            pieces.append(_fenced("\n".join(_visible(line) for line in hidden)))
            pieces.append("")
    pieces.append(ARTIFACT_CLOSE)
    return "\n".join(pieces).rstrip("\n") + "\n"


_ORDINALS = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
)


def _ordinal(which: int) -> str:
    """The word for which one, counting from one, as a person would say it."""
    if 1 <= which <= len(_ORDINALS):
        return _ORDINALS[which - 1]
    return "number %d" % which


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
            read_text_exactly(
                os.path.join(base_root, relative.replace("/", os.sep))
            )
            or ""
        )
    return _hash_of_parts(parts)


# --- Reading and checking, which both calls do the same way -------------------


class _Reading(object):
    """One prepared change, read and checked once, ready to show or to write."""

    __slots__ = (
        "staging",
        "walk",
        "entry_id",
        "source_id",
        "artifact",
        "shown_hash",
        "by_hand",
    )

    def __init__(
        self, staging, walk, entry_id, source_id, artifact, shown_hash, by_hand=False
    ):
        self.staging = staging
        self.walk = walk
        self.entry_id = entry_id
        self.source_id = source_id
        self.artifact = artifact
        self.shown_hash = shown_hash
        self.by_hand = by_hand


def _a_document_that_moved_on(base_root: str, staging) -> Optional[str]:
    """The first document this change was made from that is not what it was.

    Findings H2 of the third look and N1 of the final pass together. A change
    somebody made by hand is the document in front of them, so the question is
    whether that document still holds the bytes the change was prepared from,
    and the prepared change carries those bytes as a value. A change prepared
    by an older build carries none, and for that one there is nothing to
    compare, so it is left to the rest of the checks.
    """
    ordered = compose_proposal.hand_edit_targets(staging)
    recorded = list(getattr(staging, "target_bytes", None) or [])
    if len(recorded) != len(ordered):
        return None
    for relative, wanted in zip(ordered, recorded):
        data = read_bytes(os.path.join(base_root, relative.replace("/", os.sep)))
        if data is None or ids.bytes_hash(data) != wanted:
            return relative
    return None


def _made_by_hand(staging) -> bool:
    """Whether this prepared change is a change the person made themselves.

    It is the one kind that is allowed to be sitting unsaved in the base while
    it is approved, because the unsaved edit is the change.
    """
    return str(getattr(staging, "origin", "")) == compose_proposal.LOCAL_EDIT_ORIGIN


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
    # The one reading is parsed, checked, hashed, and written from. Finding N2
    # of Astra's fourth look: the file was read again here, so a revision that
    # landed between the two reads was written under the value of the one
    # before it, which the owner had seen.
    try:
        staging = compose_proposal.staging_from_text(staged_text)
    except GtmBaseError as failure:
        return (
            _refused(
                STATUS_REFUSED, failure.code or CODE_UNREADABLE, UNREADABLE, staging_id
            ),
            None,
        )

    # Approving writes a line recording the owner's yes about every document
    # this change edits, and that line cannot carry a name with a space in it.
    # Refused before it is shown, so nobody reads a change they cannot approve.
    for relative in list(staging.target_paths) + [edit.path for edit in staging.edits]:
        if formats.name_has_a_space(relative):
            return (
                _refused(
                    STATUS_REFUSED,
                    formats.CODE_NAME_WITH_A_SPACE,
                    formats.NAME_WITH_A_SPACE,
                    staging.staging_id,
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

    by_hand = _made_by_hand(staging)
    if by_hand:
        moved = _a_document_that_moved_on(base_root, staging)
        if moved is not None:
            return (
                _refused(
                    STATUS_MOVED,
                    CODE_PREPARED_FROM_OLDER,
                    PREPARED_FROM_OLDER % names.document_name(moved),
                    staging.staging_id,
                ),
                None,
            )
    try:
        walk = (
            _walk_a_hand_edit(base_root, staging, git)
            if by_hand
            else _walk_the_edits(base_root, staging)
        )
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

    # A part taken out puts no words in, so there are no words of it to be
    # the note (finding R10).
    written_words = [
        after
        for (_relative, _heading, _before, after), kind in zip(walk.steps, walk.kinds)
        if kind[0] != "remove"
    ]
    if compose_proposal.still_a_first_draft(staging, base_id) or any(
        stale_check.still_the_note(after) for after in written_words
    ):
        return (
            _refused(
                STATUS_REFUSED,
                CODE_STILL_A_PLACEHOLDER,
                STILL_A_PLACEHOLDER,
                staging.staging_id,
            ),
            None,
        )
    for after in written_words:
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
        base_root, walk.ordered, _who_is_approving(base_root, git), git
    )
    if owner_problems:
        return _many(STATUS_REFUSED, staging.staging_id, owner_problems), None

    differences = (
        whole_difference(base_root, walk.ordered, git) if by_hand else None
    )
    if differences:
        # What the yes writes down is the whole of each file, so the whole of
        # each file's difference is read for things that must never leave.
        allowlist, _code = compose_proposal.scan.load_allowlist(base_root)
        hits = []
        for relative in walk.ordered:
            hits.extend(
                compose_proposal.scan.scan_text(
                    differences.get(relative) or "",
                    allowlist,
                    "what you changed in %s" % names.document_name(relative),
                )
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

    entry = _entry_for(base_root, staging, entry_id)
    return None, _Reading(
        staging,
        walk,
        entry_id,
        source_id,
        artifact_for(base_root, staging, entry, walk, today, differences),
        _shown_hash(staged_text, base_root, walk.ordered),
        by_hand,
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

    __slots__ = (
        "files",
        "confirmations",
        "subject",
        "staging",
        "ordered",
        "leave_alone",
    )

    def __init__(
        self, files, confirmations, subject, staging, ordered, leave_alone=None
    ):
        # Each item is (path, text, whether the base already holds that path).
        self.files = files
        self.confirmations = confirmations
        self.subject = subject
        self.staging = staging
        self.ordered = ordered
        # The paths already holding what this change says, which are saved as
        # they stand rather than written over (finding N1).
        self.leave_alone = set(leave_alone or [])

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
    leave_alone = set(walk.leave_alone)

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

    return _Plan(
        files,
        confirmations,
        _subject(staging),
        staging,
        list(walk.ordered),
        leave_alone,
    )


# --- The note that makes a half finished run recoverable ----------------------


def _journal_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), JOURNAL_FILE)


def _originals_dir(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), ORIGINALS_DIR)


def _staged_paths(base_root: str, git: GitRunner):
    """Every path whose change is already lined up to be saved."""
    found = git.run(["diff", "--name-only", "--cached", "-z"], cwd=base_root)
    if not found.ok:
        return set()
    return set(name for name in found.stdout.split("\0") if name)


# What a line of the index says about one path, as the note keeps it. Both go
# onto a git command line when a failed run puts the index back, so the note
# is only believed when each is written the one way git writes it.
_INDEX_MODES = ("100644", "100755", "120000")
_OBJECT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _index_entry(base_root: str, relative: str, git: GitRunner):
    """What the index holds for one path: (read, (mode, object) or None).

    Finding R1 of Astra's third look. The note kept only whether a path was
    lined up to be saved, so a failed run put back a different version from
    the one the person had lined up, and when the file on the disk already
    matched it put nothing back at all. This is the exact entry, so exactly
    that can be put back and checked.
    """
    # Records end in a NUL and names come out as they are (finding N8 of
    # Astra's fourth look): without it git quotes and escapes a name with an
    # accent in it, which then never matched the name it was read for.
    found = git.run(["ls-files", "-s", "-z", "--", relative], cwd=base_root)
    if not found.ok:
        return False, None
    lines = [line for line in found.stdout.split("\0") if line]
    if not lines:
        return True, None
    if len(lines) != 1:
        # More than one entry is a path in the middle of a clash, which this
        # module will not try to put back.
        return False, None
    head, _tab, name = lines[0].partition("\t")
    parts = head.split()
    if (
        len(parts) != 3
        or parts[2] != "0"
        or name != relative
        or parts[0] not in _INDEX_MODES
        or not _OBJECT_RE.match(parts[1])
    ):
        return False, None
    return True, (parts[0], parts[1])


def _this_runs_blob(
    base_root: str, relative: str, text: Optional[str], git: GitRunner
) -> Optional[str]:
    """The stored version this run will line up for a path, worked out first.

    Finding N1 of Astra's fourth look. Recovery has to tell the index entry
    this run lined up from one the person lined up afterwards, so the value
    this run will put there is kept before anything is written. `text` is
    None for a file this run saves as it stands, whose bytes are already on
    the disk.
    """
    if text is None:
        found = git.run(["hash-object", "--", relative], cwd=base_root)
    else:
        found = git.run(
            ["hash-object", "--path=" + relative, "--stdin"], cwd=base_root, input=text
        )
    value = found.out() if found.ok else ""
    return value if _OBJECT_RE.match(value) else None


def _save_originals(
    base_id: str, base_root: str, ordered: List[str], git: GitRunner, plan=None
):
    """Keep the exact bytes of every file this run is about to write over.

    Finding V4 of the 2026-09-20 verification round. Putting a file back the
    way it was last saved is only the right answer when nothing was unsaved in
    it, and the whole point of the hand-edit path is that something is. So the
    bytes that were in front of the person when they answered are kept beside
    the note, and those are what comes back if anything goes wrong.
    """
    folder = _originals_dir(base_id)
    shutil.rmtree(folder, ignore_errors=True)
    ensure_dir(folder)
    staged_now = _staged_paths(base_root, git)
    saved: List[dict] = []
    for index, relative in enumerate(ordered):
        # Bytes, not text. Finding L1 of the third look: reading this as text
        # translated line endings on the way in and answered nothing at all for
        # a file that is not text, so a failed run put back a file that was not
        # the one the person had, or did not put it back at all.
        data = read_bytes(os.path.join(base_root, relative.replace("/", os.sep)))
        if data is None:
            raise ValidationError(
                COULD_NOT_KEEP % names.document_name(relative),
                code=CODE_COULD_NOT_KEEP,
            )
        # What the index holds for it and who may read and write it are kept
        # apart from the bytes, because either can differ while the bytes are
        # the same (finding R1 of Astra's third look). A path whose index entry
        # cannot be read exactly is one this run could not put back, so it
        # stops the run before anything is written.
        read, entry = _index_entry(base_root, relative, git)
        if not read:
            raise ValidationError(
                COULD_NOT_KEEP % names.document_name(relative),
                code=CODE_COULD_NOT_KEEP,
            )
        try:
            file_mode = os.stat(
                os.path.join(base_root, relative.replace("/", os.sep))
            ).st_mode & 0o7777
        except OSError:
            raise ValidationError(
                COULD_NOT_KEEP % names.document_name(relative),
                code=CODE_COULD_NOT_KEEP,
            )
        # And what this run will leave there itself, so that recovery puts
        # back only what is still this run's and keeps anything newer
        # (finding N1 of Astra's fourth look). A file saved as it stands
        # keeps its permissions; a file this run writes gets the ones it
        # writes with.
        ours_blob = None
        ours_mode = file_mode
        if plan is not None:
            texts = dict((path, text) for path, text, _in_head in plan.files)
            leave = relative in plan.leave_alone or relative not in texts
            ours_blob = _this_runs_blob(
                base_root, relative, None if leave else texts[relative], git
            )
            if ours_blob is None:
                raise ValidationError(
                    COULD_NOT_KEEP % names.document_name(relative),
                    code=CODE_COULD_NOT_KEEP,
                )
            if not leave:
                ours_mode = _WRITTEN_MODE
        name = "%d.bytes" % index
        atomic_write_bytes(os.path.join(folder, name), data, mode=0o600)
        record = {
            "path": relative,
            "hash": ids.bytes_hash(data),
            "copy": name,
            "staged": relative in staged_now,
            "index": (
                {"mode": entry[0], "blob": entry[1]} if entry is not None else None
            ),
            "file_mode": file_mode,
        }
        if ours_blob is not None:
            record["ours_blob"] = ours_blob
            record["ours_file_mode"] = ours_mode
        saved.append(record)
    return saved


def _kept_copies(base_id: str, journal: Optional[dict]) -> Dict[str, dict]:
    """The kept bytes the note names, keyed by the path each one belongs to."""
    found: Dict[str, dict] = {}
    for item in (journal or {}).get("originals") or []:
        if isinstance(item, dict) and item.get("path"):
            found[str(item.get("path"))] = item
    del base_id
    return found


def _kept_mode(kept: dict, key: str = "file_mode") -> Optional[int]:
    """The permissions the note kept for a file, when it kept any."""
    value = kept.get(key)
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0o7777:
        return value
    return None


# What putting back the index and the permissions came to.
_BACK = "back"
_STUCK = "stuck"
_NEWER = "newer"


def _mode_to_end_with(full: str, kept: dict) -> Optional[int]:
    """The permissions a file should end with, or None to leave them be.

    The kept ones while the file still has the kept ones or this run's own;
    anything else was set after this run, by somebody else, and it is left
    exactly as it is (finding N1 of Astra's fourth look). A note that never
    said what this run's own were is only trusted to put back its own kept
    ones over the ones this run writes with.
    """
    mode = _kept_mode(kept)
    if mode is None:
        return None
    try:
        now = os.stat(full).st_mode & 0o7777
    except OSError:
        return mode
    ours = _kept_mode(kept, "ours_file_mode")
    if ours is None and "ours_blob" not in kept:
        ours = _WRITTEN_MODE
    if now == mode or now == ours:
        return mode
    return None


def _head_entry(base_root: str, relative: str, git: GitRunner):
    """What the last save holds for one path, as (read, (mode, object) or None)."""
    found = git.run(["ls-tree", "-z", "HEAD", "--", relative], cwd=base_root)
    if not found.ok:
        return False, None
    records = [record for record in found.stdout.split("\0") if record]
    if not records:
        return True, None
    head, _tab, name = records[0].partition("\t")
    parts = head.split()
    if len(records) != 1 or len(parts) != 3 or name != relative:
        return False, None
    return True, (parts[0], parts[2])


def _put_the_rest_back(base_root: str, kept: dict, git: GitRunner) -> str:
    """Put back what the index held and who may read the file, and check both.

    Finding R1 of Astra's third look. This used to run only when the bytes had
    to be written, it forced one set of permissions, and it ignored whether
    git had done what it was asked. Now it runs whether or not the bytes
    already match, and it checks that the index and the permissions
    afterwards are exactly what was kept.

    Finding N1 of Astra's fourth look. Each is put back only while it still
    holds the kept value or this run's own. Permissions set since are left as
    they are. An index entry lined up since is left as it is too, and it
    comes back as newer, so the note stays, until that entry has been saved.
    """
    relative = str(kept.get("path"))
    full = os.path.join(base_root, relative.replace("/", os.sep))
    mode = _mode_to_end_with(full, kept)
    if mode is not None:
        try:
            os.chmod(full, mode)
            if os.stat(full).st_mode & 0o7777 != mode:
                return _STUCK
        except OSError:
            return _STUCK
    if "index" not in kept:
        # A note written before the index was kept says only whether the
        # path was lined up, which is the best that can be put back for it.
        if kept.get("staged"):
            done = git.run(["add", "--", relative], cwd=base_root).ok
        else:
            done = git.run(["reset", "-q", "HEAD", "--", relative], cwd=base_root).ok
        return _BACK if done else _STUCK
    entry = kept.get("index")
    original = (
        None if entry is None else (str(entry.get("mode")), str(entry.get("blob")))
    )
    read, now = _index_entry(base_root, relative, git)
    if not read:
        return _STUCK
    if now == original:
        return _BACK
    ours = str(kept.get("ours_blob") or "")
    if now is None or not ours or now[1] != ours:
        # Lined up after this run by somebody else. It is theirs and it stays;
        # once they have saved it there is nothing left of this run's in it.
        saved, held = _head_entry(base_root, relative, git)
        return _BACK if saved and held == now else _NEWER
    if entry is None:
        result = git.run(
            ["rm", "-q", "--cached", "--ignore-unmatch", "--", relative],
            cwd=base_root,
        )
        wanted = None
    else:
        wanted = (str(entry.get("mode")), str(entry.get("blob")))
        result = git.run(
            [
                "update-index",
                "--add",
                "--cacheinfo",
                "%s,%s,%s" % (wanted[0], wanted[1], relative),
            ],
            cwd=base_root,
        )
    if not result.ok:
        return _STUCK
    read, now = _index_entry(base_root, relative, git)
    return _BACK if read and now == wanted else _STUCK


def _put_their_own_back(base_root: str, base_id: str, kept: dict, git: GitRunner) -> str:
    """Write one file back to the bytes it held before this run, and check it.

    It comes back true only when the bytes on the disk afterwards are the bytes
    that were kept, read back and measured, and the index and the permissions
    are what was kept as well, because a restore nobody checked is not a
    restore anybody should report.
    """
    relative = str(kept.get("path"))
    wanted = str(kept.get("hash") or "")
    data = read_bytes(
        os.path.join(_originals_dir(base_id), str(kept.get("copy") or ""))
    )
    if data is None or ids.bytes_hash(data) != wanted:
        return _STUCK
    full = os.path.join(base_root, relative.replace("/", os.sep))
    mode = _mode_to_end_with(full, kept)
    if mode is None:
        # Permissions set since this run are kept on the bytes put back.
        try:
            mode = os.stat(full).st_mode & 0o7777
        except OSError:
            mode = _kept_mode(kept)
    try:
        atomic_write_bytes(
            full, data, mode=mode if mode is not None else 0o644, inside=base_root
        )
    except (OSError, GtmBaseError):
        return _STUCK
    back = read_bytes(full)
    if back is None or ids.bytes_hash(back) != wanted:
        return _STUCK
    return _put_the_rest_back(base_root, kept, git)


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
    kept = payload.get("originals")
    if kept is not None and not isinstance(kept, list):
        return None, "the note holds something that is not a set of kept files"
    for item in kept or []:
        if not isinstance(item, dict):
            return None, "the note holds something that is not a kept file"
        relative = str(item.get("path") or "")
        name = str(item.get("copy") or "")
        try:
            paths.check_repo_path_syntax(relative, NOTE_PATH_PREFIXES)
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        if not name.endswith(".bytes") and not name.endswith(".txt"):
            return None, "the note names a kept file we never wrote"
        if not name or name != os.path.basename(name) or name in (".", ".."):
            return None, "the note names a kept file we never wrote"
        # What the index held goes onto a git command line when it is put
        # back, so it is believed only in the one shape git writes it (R1).
        entry = item.get("index")
        if entry is not None:
            if (
                not isinstance(entry, dict)
                or str(entry.get("mode")) not in _INDEX_MODES
                or not _OBJECT_RE.match(str(entry.get("blob") or ""))
            ):
                return None, "the note names an index entry we never write"
        if "file_mode" in item and _kept_mode(item) is None:
            return None, "the note names permissions we never write"
        if "ours_blob" in item and not _OBJECT_RE.match(str(item.get("ours_blob"))):
            return None, "the note names an index entry we never write"
        if "ours_file_mode" in item and _kept_mode(item, "ours_file_mode") is None:
            return None, "the note names permissions we never write"
    return payload, None


def _write_journal(
    base_id: str, base_root: str, plan: "_Plan", head: str, originals=None
) -> None:
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
            "originals": list(originals or []),
            "started_at": state.iso_utc(),
        },
    )


def _clear_journal(base_id: str) -> None:
    remove(_journal_path(base_id))
    shutil.rmtree(_originals_dir(base_id), ignore_errors=True)


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


def _undo_own_work(
    base_root: str, base_id: str, items: List[dict], git: GitRunner, kept=None
):
    """Put back every path this run wrote and did not save, and nothing else.

    A path is only put back when what is on the disk is exactly what this run
    was going to write there. A path holding what the base already held is
    left alone, because nothing was ever written to it. Anything else on one
    of those paths is the person's own work, and it is left exactly as they
    left it.

    Where this run kept a file's own bytes from before it started, those bytes
    are what goes back, not the last saved version. That is finding V4: a
    change made by hand is unsaved by definition, and the last saved version of
    such a file is the version without their change in it.

    What comes back is two lists: the paths holding the person's own work, and
    the paths this run could not put back at all. They are kept apart because
    they are two different sentences, and the person can do something about
    the first one.
    """
    theirs: List[str] = []
    stuck: List[str] = []
    kept = kept or {}
    for item in items:
        relative = str(item.get("path"))
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text(full)
        if current is None:
            continue
        mine = kept.get(relative)
        exactly = read_bytes(full)
        if (
            mine is not None
            and exactly is not None
            and ids.bytes_hash(exactly) == str(mine.get("hash"))
        ):
            # The bytes are already exactly what they had, which says nothing
            # about what they had lined up to be saved or who could read the
            # file. Finding R1 of Astra's third look: this is where a version
            # lined up by hand was lost, because nothing past the bytes was
            # put back. Both are put back and checked here as well.
            came_to = _put_the_rest_back(base_root, mine, git)
            if came_to == _STUCK:
                stuck.append(relative)
            elif came_to == _NEWER:
                theirs.append(relative)
            continue
        ours = ids.content_hash(current) == str(item.get("hash"))
        if ours and mine is not None:
            came_to = _put_their_own_back(base_root, base_id, mine, git)
            if came_to == _STUCK:
                stuck.append(relative)
            elif came_to == _NEWER:
                theirs.append(relative)
            continue
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
        compose_proposal.retire(base_root, staged, its_id, base_id=base_id)
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

    theirs, stuck = _undo_own_work(
        base_root, base_id, items, git, _kept_copies(base_id, journal)
    )
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


# The permissions this run writes a document with.
_WRITTEN_MODE = 0o644


def _write_the_files(base_root: str, plan: "_Plan") -> List[str]:
    """Put down every file this change rewrites, and the records beside them."""
    written = []
    for relative, text, _in_head in plan.files:
        if relative not in plan.leave_alone:
            atomic_write_text(
                os.path.join(base_root, relative.replace("/", os.sep)),
                text,
                mode=_WRITTEN_MODE,
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


def _ready_to_write_here(
    base_root: str, git: GitRunner, changing: List[str], by_hand: bool
):
    """Refuse on a folder with anything half done in it that is not this change.

    The ordinary rule is that nothing is written into a base while there is
    anything unsaved in it. A change the person made by hand breaks that rule
    by existing: their edit is the unsaved work, and it is the very thing they
    are approving, so the ordinary rule refused every hand edit on a base with
    no shared copy and the habit had nowhere to end (findings A4 and H2).

    So the files a change made by hand is about are allowed to be unsaved, and
    nothing else is, and every other kind of prepared change is held to the
    ordinary rule exactly as it always was. That narrowing is finding V5 of the
    verification round: a change that came from somewhere else has no reason to
    find its own target file already edited, and allowing it there let an
    unrelated unsaved edit be saved without anybody reading it.

    Nothing is weakened for the one kind that is allowed. The yes is bound to a
    value taken over the staged change and over the current bytes of exactly
    these files, and what was shown was the whole of each file's difference, so
    a file that moved between being shown and being approved is still refused.
    """
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        return CODE_NOT_DEFAULT_BRANCH, NOT_ON_MAIN
    # Entries end in a NUL and names come out exactly as they are. Without it
    # git quotes a name holding an accent or a space, the quoted form never
    # matched the file the change is about, and every hand edit to such a
    # document was refused as unsaved work.
    status = git.run(["status", "--porcelain", "-z"], cwd=base_root)
    if not status.ok:
        return CODE_GIT_FAILED, COULD_NOT_SAVE
    allowed = set(changing) if by_hand else set()
    entries = status_entries(status.stdout)
    if entries is None:
        # Output nobody here can read is treated as unsaved work it may not
        # write over. Guessing at it would be the one way this check could let
        # something through.
        return CODE_UNSAVED_EDITS, UNSAVED_EDITS
    for _letters, named in entries:
        if any(item not in allowed for item in named):
            return CODE_UNSAVED_EDITS, UNSAVED_EDITS
    return None


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

    stopped = _ready_to_write_here(
        base_root, git, reading.walk.ordered, reading.by_hand
    )
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
    # Their own bytes are kept before one byte of this run's work is written,
    # so there is never a moment where the only copy of a hand edit is the one
    # this run is about to write over.
    originals = _save_originals(base_id, base_root, reading.walk.ordered, git, plan)
    _write_journal(base_id, base_root, plan, head, originals)
    kept = {str(item["path"]): item for item in originals}

    try:
        written = _write_the_files(base_root, plan)
        _stage_the_files(base_root, written, git)
        written.extend(_write_the_confirmation_lines(base_root, plan, git))
        saved = _save_the_work(base_root, plan, git, codes)
    except GtmBaseError as failure:
        theirs, stuck = _undo_own_work(
            base_root,
            base_id,
            [
                {
                    "path": relative,
                    "hash": ids.content_hash(text),
                    "in_head": in_head,
                }
                for relative, text, in_head in plan.everything()
            ],
            git,
            kept,
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

    compose_proposal.retire(
        base_root, staging_path, plan.staging.staging_id, base_id=base_id
    )
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
    # A change nobody wanted is off this seat's record of unfinished notes,
    # which only ever grew before (finding N4).
    compose_proposal._forget_the_first_draft(base_id, staging_id)
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
    # One reading of the folder, the same one the closing and the other review
    # reader take (finding R11 of Astra's third look).
    changes = [
        change
        for change in compose_proposal.waiting_changes(base_root)
        if not change.missing
    ]
    if not changes:
        return []
    address = _who_is_approving(base_root, git)
    found: List[Tuple[str, List[str]]] = []
    for change in changes:
        if _owner_problems(base_root, change.targets, address, git):
            continue
        found.append((change.staging_id, change.targets))
    return found
