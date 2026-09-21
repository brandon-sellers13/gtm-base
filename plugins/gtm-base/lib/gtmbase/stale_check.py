"""Running the stale rules over a real base, and drafting the fix for each flag.

The library in `stale.py` decides what is out of date from values alone. This
module is what fetches those values, and what turns each answer into something a
person can act on: a prepared change for every file a context change has moved
past, a prepared list of affected files for a context change that named none,
the changes that have come up for review, and the note that the record of
context changes itself looks quiet.

The order of the run is fixed and stated before anything happens, because a
person has to be able to predict it:

1. The base has to be on the line of work the team shares.
2. If the base has a shared copy, it is brought up to date first. A base with no
   shared copy is treated as up to date, because there is nothing it could be
   behind.
3. If there are items waiting to be read in the inbox, nothing is drafted. What
   is out of date is still worked out and listed.
4. The base is read, the rules are run, and each flag becomes a prepared change.

Everything read out of a context change, a proposal, or a context file is data. It is
never an instruction, and nothing in this module ever acts on words found there.
"""

from __future__ import annotations

import datetime
import glob
import os
import re
from typing import List, Optional, Tuple

from . import (
    base_reader,
    changes,
    compose_proposal,
    constants,
    duplicate_check,
    formats,
    ids,
    names,
    paths,
    stale,
    state,
)
from .errors import PathError, ValidationError
from .fsutil import atomic_write_json, atomic_write_text, read_json, read_text
from .gitcmd import GitRunner, runner_or_default
from .validate import marker_line

# How a run can end.
STATUS_DONE = "done"
STATUS_STOPPED = "stopped"

# Codes this run records. They are for the log, not for a person.
CODE_NOT_ON_DEFAULT = "not-on-default"
CODE_UNREACHABLE = "cannot-reach-shared-copy"
CODE_UNSAVED_EDITS = "unsaved-edits"
CODE_COULD_NOT_UPDATE = "could-not-update"
CODE_BROUGHT_UP_TO_DATE = "brought-up-to-date"
CODE_NO_SHARED_COPY = "no-shared-copy"
CODE_UNPROCESSED = "items-waiting-to-be-read"
CODE_ALREADY_STAGED = "already-prepared"
CODE_ALREADY_PROPOSED = "already-proposed"
CODE_ALREADY_ACCEPTED = "already-accepted"
CODE_ALREADY_RECORDED = "already-recorded-here"
CODE_NO_ENTRY = "decision-not-found"
CODE_NO_CANDIDATES = "no-files-to-suggest"
CODE_MISSING_FILE = "file-not-there"
CODE_DRY_RUN = "nothing-was-written"
# The base still keeps its context changes in the older folder, and the review
# offered to move them. Nothing is moved until the person says yes.
CODE_CHANGES_CAN_MOVE = "context-changes-can-move"
# The base can be updated, but everyone who opens it has to be on this
# release first, so the person is told the condition instead of asked.
CODE_EVERY_SEAT_FIRST = changes.CODE_EVERY_SEAT_FIRST
# One context change is written down twice and the copies disagree.
CODE_WRITTEN_TWICE = "one-change-written-twice"

# What the run writes for the hook to pick up later.
REVIEW_BY_FILE = "review_by_items.json"

# How much of a context change the first draft of an edit quotes.
DRAFT_QUOTE_CHARS = 300
# How much of a piece of a file the before and after lines carry.
SUMMARY_CHARS = 300
# The heading an edit is added under when the context change names no other.
FALLBACK_HEADING = "## Context changes to reflect"

# The first draft this module writes into a prepared change, and the part of
# it that never varies. Nothing may be approved while it still carries these
# words: they are a note asking the assistant to write the real replacement,
# and finding A6 of the 2026-09-20 review was that approving them cleared the
# flag on a document whose obsolete claim was still sitting in it.
PLACEHOLDER_SHAPE = "Update needed: %s. This section should reflect that change."
PLACEHOLDER_TAIL = "This section should reflect that change."
# The first half of the same note, which is what was left when somebody cut
# the second half off and the rule stopped recognising it (finding V8).
PLACEHOLDER_HEAD = "Update needed:"

# What a prepared change says while it is still a first draft.
DRAFT_CONFIDENCE = "medium"

_HEADING_RE = re.compile(r"^(#{2})\s+(\S.*)$")
_WHITESPACE_RE = re.compile(r"\s+")

# --- The sentences a person reads -------------------------------------------

NOT_ON_DEFAULT = (
    "Your base is not on its main line right now, so nothing was checked. Ask "
    "GTM Base to put it back."
)
UNREACHABLE = (
    "GTM Base could not reach the shared copy of your base, so nothing was "
    "checked this time."
)
UNSAVED_EDITS = (
    "Your base is behind the shared copy and you have edits you have not saved, "
    "so nothing was checked. Put those edits somewhere safe and ask again."
)
COULD_NOT_UPDATE = (
    "GTM Base could not bring your base up to date on its own, so nothing was "
    "checked this time."
)
BROUGHT_UP_TO_DATE = "Your base was brought up to date with the shared copy first."
UNPROCESSED = (
    "There are %d items waiting to be read in your inbox, so nothing was "
    "prepared. Everything that is out of date is still listed below, and the "
    "changes can be prepared once those items have been read."
)
NOTHING_FLAGGED = "Nothing in your base is out of date today."
DRY_RUN_NOTE = "This was a look only, so nothing was written."
# The day this names is the day the change was written down, not the day it
# happened, because that is the date the rule behind it really compares. An
# earlier wording said "is from", which reads as the day it happened.
LEDGER_BEHIND = (
    "The last context change in your base was written down on %s, which is "
    "more than %d days ago. If nothing about the business has changed since "
    "then, say so and GTM Base will stop mentioning it for %d days."
)
LEDGER_BEHIND_EMPTY = (
    "Your base has no context change recorded yet. If there is nothing to write "
    "down, say so and GTM Base will stop mentioning it for %d days."
)
LEDGER_BEHIND_DISMISSED = (
    "GTM Base will not mention the quiet record of context changes again until "
    "%s."
)
REVIEW_BY = (
    "Context change %s came up for review on %s, which was %d days ago."
)
MALFORMED = (
    "%d things in your base could not be read, so they were left alone."
)
MALFORMED_ONE = (
    "1 thing in your base could not be read, so it was left alone."
)
# Said whenever one context change is written down twice and the two copies
# do not agree. It names the change and both files, because the answer is the
# person's to give and they cannot give it without knowing where to look.
WRITTEN_TWICE = (
    "The context change %s is written down twice, in %s, and the two do not "
    "say the same thing. GTM Base is not choosing between them. Decide which "
    "one is right and take the other one away."
)
# Said about the documents that change is about, because a change nobody can
# read is not a reason to treat those documents as settled.
CANNOT_VOUCH = (
    "Until those two agree, GTM Base cannot vouch for %s."
)
DROPPED = (
    "%d file names in your context changes point outside the base, so they "
    "were skipped."
)

# The first-run findings, in the order the first run looks for them.
FINDING_REQUIRED_FILE = (
    "You have not written %s yet, so there is nothing there to keep current."
)
# The honest baseline, for a base whose two documents are confirmed and whose
# record of context changes is empty. It says what was confirmed and when, it
# says plainly what the base cannot do yet, and it names the day each document
# comes back. It never says that nothing is out of date, because nothing has
# been checked against anything, and it never says there is no date to watch,
# because each confirmation has one. It replaces the older sentence that said
# nothing had been written down yet, which made a missing habit sound like a
# missing step.
# It is three short lines, one thought each, rather than the one long
# sentence it was when Unit 1.2 wrote it. Both dates are named once when they
# are one date, which is what setting a base up in a single sitting produces,
# and separately when setting up was resumed on a later day and they really
# are two days. Each line is true in every state that reaches it.
FINDING_BASELINE_CONFIRMED_ONE_DAY = "You confirmed %s and %s on %s."
FINDING_BASELINE_CONFIRMED_TWO_DAYS = "You confirmed %s on %s and %s on %s."
FINDING_BASELINE_NOTHING_TO_CHECK = (
    "No context change is recorded yet, so there is nothing to check either "
    "document against."
)
FINDING_BASELINE_ASK_ONE_DAY = (
    "GTM Base will ask about both of them again on %s."
)
FINDING_BASELINE_ASK_TWO_DAYS = (
    "GTM Base will ask about %s again on %s, and about %s on %s."
)
# The same baseline for a base where a required document carries no owner
# confirmation at all, which is the one case where there is no date to name.
FINDING_BASELINE_UNCONFIRMED = (
    "No context change is recorded yet, so GTM Base cannot yet check whether a "
    "change has made either document out of date, and %s carries no "
    "confirmation from its owner, so GTM Base will ask about it the next time "
    "you review your base."
)
FINDING_DOCUMENT_OLDER = (
    "The material behind %s is dated %s, and context change %s happened on %s, "
    "so that document is older than the change it is meant to reflect. It is "
    "worth a read."
)
# Said when a document has not caught up with a context change. It says only
# what is true in every state that reaches it: the document is behind, and the
# review is where it gets dealt with. It never says a fix is ready, because
# whether one has been prepared varies, and a sentence claiming it would be
# wrong half the time.
FINDING_DOCUMENT_BEHIND = (
    "%s has not caught up with a context change you recorded. Ask for a review "
    "of your base to go through it."
)
# Said when one context change is written down twice and the two copies
# disagree. Nothing else about the base can be worked out while that is true,
# so this claims nothing about any other document.
FINDING_WRITTEN_TWICE = (
    "One of your context changes is written down twice and the two copies do "
    "not say the same thing, so GTM Base cannot tell you yet whether anything "
    "is out of date."
)
FINDING_NOTHING_YET = (
    "Nothing is out of date yet. The first date GTM Base will watch is %s, for "
    "the change about %s."
)
# Said when GTM Base has prepared a change and nobody has answered it yet. It
# is said instead of any all-clear, because a base with one waiting has
# something to do (finding G5).
# Said when a prepared change is waiting on a document that is not in the base
# any more. Nothing can ever be done with one of those, so the one thing to say
# is what it is and how to be rid of it (finding P1).
CHANGE_ABOUT_A_MISSING_DOCUMENT = (
    "A change is waiting about a document that is not in your base any more, "
    "so there is nothing left for it to change. Say: drop that change, and "
    "GTM Base will put it aside."
)
FINDING_CHANGE_WAITING = (
    "%s has a change waiting for you to approve it, so there is something to "
    "do before anything here is settled. Ask for a review of your base to read "
    "it."
)
# Reached when the base holds context changes but none of the open ones asks to
# be looked at again. The older wording said there was no date to watch and
# stopped there, which reads as though the base were finished with. It says
# instead what is true and what would give it a date, in the same honest shape
# as the baseline finding above.
FINDING_NOTHING_YET_NO_DATE = (
    "Nothing is out of date yet. Every context change your base holds is either "
    "closed or carries no date to look at it again, so there is no date ahead "
    "for GTM Base to watch. The next context change you record will give it one."
)
# Said once for each prepared change still waiting on a base with no shared
# copy, which is the one kind of base where the owner approves one in Claude.
AWAITING_LOCAL_APPROVAL = (
    "%s has a prepared change waiting for you to approve it here."
)

# --- The review a person asks for --------------------------------------------
#
# Amendment r2.5 moved the question out of the start of a session and into the
# review. The question identifiers, the log of what was asked, a not now, and a
# no that becomes a prepared change all work exactly as they did; the review
# issues them instead of the session-start hook. Ruling 3 of the acceptance
# matrix is why each item is one line and the document is there on request.

REVIEW_OPENING = (
    "Here is everything in your base due a look today, one line each. Say the "
    "number of any one of them to read the document itself."
)
REVIEW_NOTHING = (
    "Nothing in your base is due a look today, and no change is waiting for "
    "you to approve it."
)
REVIEW_ITEM_CHANGE = (
    "%s. %s has not caught up with a context change recorded on %s."
)
REVIEW_ITEM_THRESHOLD = (
    "%s. Nobody has said %s is still right for longer than this base allows."
)
REVIEW_NO_SESSION = (
    "GTM Base does not know which session this is, so it listed what is due "
    "without anything to answer with. Start a new session and ask again."
)
REVIEW_NOTHING_OWNED = (
    "No document in this base is recorded as yours, so there is nothing here "
    "for you to answer. Whoever owns them is asked about them on their own "
    "computer."
)
REVIEW_ITEM_WAITING_HERE = (
    "%s. %s has not caught up with a context change recorded on %s, and a "
    "change for it is prepared and waiting for you to approve it."
)
REVIEW_ITEM_WAITING_THERE = (
    "%s. %s has a prepared change waiting for somebody to review it."
)
REVIEW_INBOX_WAITING = (
    "There are %d items waiting to be read in your inbox, so nothing can be "
    "answered yet. Read those first and ask for the review again."
)
REVIEW_SPEAKING_AGAIN = (
    "You asked GTM Base to stay quiet until you asked for a review. This is "
    "that review, so it will speak up again from now on."
)


# --- What comes back ---------------------------------------------------------


class Staged(object):
    """One prepared change, and where it was written."""

    __slots__ = ("staging_id", "path", "target_paths", "entry_id", "kind")

    def __init__(self, staging_id, path, target_paths, entry_id, kind):
        self.staging_id = staging_id
        self.path = path
        self.target_paths = list(target_paths)
        self.entry_id = entry_id
        self.kind = kind

    def __repr__(self) -> str:
        return "Staged(staging_id=%r, kind=%r)" % (self.staging_id, self.kind)


class Skipped(object):
    """One flag that was not prepared, and the reason in one code."""

    __slots__ = ("staging_id", "entry_id", "path", "code")

    def __init__(self, staging_id, entry_id, path, code):
        self.staging_id = staging_id
        self.entry_id = entry_id
        self.path = path
        self.code = code

    def __repr__(self) -> str:
        return "Skipped(staging_id=%r, code=%r)" % (self.staging_id, self.code)


class ReviewLine(object):
    """One thing the review listed, and the question it asked about it.

    A line about a document carries the single-use question this session may
    answer it with. A line about a prepared change carries none, because what
    happens to a prepared change is approving it and not answering a question.
    """

    __slots__ = ("number", "path", "kind", "trigger", "entry_id", "question_id", "sentence")

    def __init__(self, number, path, kind, trigger, entry_id, question_id, sentence):
        self.number = number
        self.path = path
        self.kind = kind
        self.trigger = trigger
        self.entry_id = entry_id
        self.question_id = question_id
        self.sentence = sentence

    def __repr__(self) -> str:
        return "ReviewLine(number=%r, kind=%r, path=%r)" % (
            self.number,
            self.kind,
            self.path,
        )


class StaleCheckResult(object):
    """Everything one run of the stale check has to say."""

    def __init__(self, status=STATUS_DONE, mode="normal"):
        self.status = status
        self.mode = mode
        self.codes: List[str] = []
        self.sentences: List[str] = []
        self.staged: List[Staged] = []
        self.skipped: List[Skipped] = []
        self.report = None
        self.finding = None
        self.finding_sentence = ""
        self.drafting_refused = False
        self.unprocessed_count = 0
        self.dry_run = False
        # One entry per thing the review walked, in the order it listed them.
        self.review: List[ReviewLine] = []

    @property
    def stopped(self) -> bool:
        return self.status == STATUS_STOPPED

    def lines(self) -> List[str]:
        """Every sentence this run prints, in the order it prints them."""
        return list(self.sentences)

    def __repr__(self) -> str:
        return "StaleCheckResult(status=%r, staged=%d)" % (
            self.status,
            len(self.staged),
        )


# --- Small helpers -----------------------------------------------------------


def _collapse(text: str, cap: int = SUMMARY_CHARS) -> str:
    """One line of plain words, short enough to sit in a sentence."""
    single = _WHITESPACE_RE.sub(" ", str(text or "")).strip()
    if len(single) <= cap:
        return single
    return single[:cap].rstrip() + "..."


def _quote(text: str) -> str:
    """A piece of the base, marked as something read rather than written."""
    lines = [line.strip() for line in str(text or "").strip().split("\n")]
    return "\n".join("> " + line if line else ">" for line in lines)


def _headings_of(text: str) -> List[str]:
    """Every second level heading in a file, as it is written."""
    found = []
    for line in (text or "").split("\n"):
        match = _HEADING_RE.match(line.rstrip())
        if match:
            found.append(line.strip())
    return found


def _section_text(text: str, heading: str) -> str:
    """The words under one heading, up to the next heading as big or bigger."""
    lines = (text or "").split("\n")
    wanted = heading.strip()
    for index, line in enumerate(lines):
        if line.strip() != wanted:
            continue
        collected = []
        for following in lines[index + 1 :]:
            if following.startswith("#"):
                break
            collected.append(following)
        return "\n".join(collected).strip()
    return ""


def _heading_named_by(entry_text: str, file_text: str) -> Optional[str]:
    """The heading in the file that the context change itself talks about."""
    haystack = (entry_text or "").lower()
    for heading in _headings_of(file_text):
        title = heading.lstrip("#").strip()
        if title and title.lower() in haystack:
            return heading
    return None


def _entry_citation(entry, entry_file: str) -> str:
    """The one sentence that says which context change this came from."""
    name = (entry_file or "").rsplit("/", 1)[-1]
    return "Context change %s, written down in %s, and it happened on %s." % (
        entry.id,
        name or "the record of context changes",
        entry.decided_on,
    )


def _proposals_glob(base_root: str) -> List[str]:
    folder = os.path.join(base_root, constants.PROPOSALS_DIR)
    return glob.glob(os.path.join(folder, "**", "*.md"), recursive=True)


def _staging_exists(base_root: str, staging_id: str) -> bool:
    """Whether a prepared change with this identifier is already waiting."""
    wanted = staging_id + ".md"
    return any(os.path.basename(path) == wanted for path in _proposals_glob(base_root))


def awaiting_local_approval(
    base_root: str, runner: Optional[GitRunner] = None
) -> List[Tuple[str, List[str]]]:
    """Every prepared change waiting on a yes that could actually be given.

    The answer comes from the one module that applies them, so this list and
    that path can never disagree about what is waiting, and a change nobody
    here could approve is never named as though somebody could. It is imported
    inside the function because that module reads this one.
    """
    from . import approve_local

    return approve_local.waiting(base_root, runner=runner)


def _documents_with_a_change_waiting(base_root: str):
    """Every document a prepared change is really waiting on, and the strays.

    A change nobody can approve yet counts exactly as much as one they can:
    either way there is something to do and nothing is settled (finding G5).
    What does not count is anything else that happens to be in the folder,
    which is finding P1 of the confirmation round: a file with a name GTM Base
    never issues, and a well-formed change about a document that is not in the
    base, both made every closing say a change was waiting for ever while the
    review listed nothing to read. The second one happens honestly the moment
    somebody renames or deletes a document a change is waiting on.

    So the same reading the review itself does is done here, without the
    question of who owns what: the file has to be named after an identifier
    GTM Base issued, that name has to be the one written inside it, and every
    document it would change has to be in the base. What comes back is the
    documents that are really waiting, and separately the changes waiting on a
    document that is gone, which somebody has to be told about because nothing
    can ever be done with one.
    """
    found: List[str] = []
    orphaned: List[str] = []
    folder = os.path.join(base_root, constants.PROPOSALS_PENDING_DIR)
    if not os.path.isdir(folder):
        return found, orphaned
    for name in sorted(os.listdir(folder)):
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
        targets = compose_proposal.edited_paths(staging)
        if not targets:
            continue
        missing = [
            path
            for path in targets
            if not os.path.isfile(
                os.path.join(base_root, path.replace("/", os.sep))
            )
        ]
        if missing:
            orphaned.append(staging_id)
            continue
        for path in targets:
            if path not in found:
                found.append(path)
    return found, orphaned


def _list_awaiting_local_approval(result, base_root: str, git) -> None:
    """Say, once per document, that a prepared change is waiting on a yes."""
    said: List[str] = []
    for _staging_id, targets in awaiting_local_approval(base_root, runner=git):
        for path in targets:
            if path in said:
                continue
            said.append(path)
            result.sentences.append(
                AWAITING_LOCAL_APPROVAL % names.document_name(path)
            )


def _corrections_citing(base_root: str) -> List["formats.CorrectionsFile"]:
    """Every accepted record the base holds, as far as it can be read."""
    found = []
    folder = os.path.join(base_root, constants.CORRECTIONS_DIR)
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        text = read_text(path)
        if text is None:
            continue
        try:
            found.append(formats.CorrectionsFile.parse(text))
        except (ValidationError, PathError):
            continue
    return found


def _recorded_in_index(base_id: str, staging_id: str) -> bool:
    """Whether this seat already recorded a proposal for this identifier."""
    index, _problems = state.load_index(base_id)
    for row in index.values():
        for value in row.get("staging_ids") or []:
            if str(value) == staging_id:
                return True
        for value in row.get("proposal_ids") or []:
            if str(value).startswith(staging_id + ":"):
                return True
    return False


# --- Writing one prepared change ---------------------------------------------


def draft_text_for(entry) -> str:
    """The first draft of the words that go into the file.

    It is deliberately a plain sentence naming the change, because the words
    that end up in the file are the assistant's job to write from the change
    and the file, and a first draft that pretends to be finished is worse than
    one that says what it is.
    """
    quoted = _collapse(entry.body, DRAFT_QUOTE_CHARS).rstrip(".")
    return PLACEHOLDER_SHAPE % quoted


def is_the_placeholder(text) -> bool:
    """Whether some words are the first draft, exactly as this module writes it.

    This is not what stops a first draft being approved. What stops that is the
    marker the prepared change carries, because an exact-text rule was got past
    by dropping the full stop (finding V8). This is kept for the one thing text
    can honestly answer: whether some words handed in as the real wording are
    the note again.
    """
    if not isinstance(text, str):
        return False
    return PLACEHOLDER_TAIL in text


def _flattened(text) -> str:
    """One run of words with its spacing and its letter case taken out."""
    return " ".join(str(text or "").split()).lower()


def still_the_note(text) -> bool:
    """Whether words handed in as the real wording are the note over again.

    Whitespace and letter case are taken out first, and both halves of the note
    are looked for, because what got past the old rule was a full stop dropped,
    a line rewrapped, a double space, lower case, and the second half cut off
    altogether. Empty words count as the note too: nothing is not a wording.
    """
    flat = _flattened(text)
    if not flat:
        return True
    return (
        _flattened(PLACEHOLDER_TAIL).rstrip(".") in flat
        or flat.startswith(_flattened(PLACEHOLDER_HEAD).rstrip(":"))
    )


def build_file_proposal(
    base_root: str, entry, entry_file: str, path: str
) -> "formats.ProposalStaging":
    """The prepared edit for one file one context change has moved past."""
    staging_id = ids.staging_id(entry.id, path, "ledger", 0)
    text = read_text(os.path.join(base_root, path))
    if text is None:
        raise ValidationError(
            "GTM Base could not read %s, so it prepared nothing for it." % path,
            code=CODE_MISSING_FILE,
        )
    heading = _heading_named_by(entry.body, text)
    if heading is not None:
        operation = "replace"
        before = _collapse(_section_text(text, heading))
    else:
        heading = FALLBACK_HEADING
        operation = "add"
        before = ""
    if not before:
        before = "This part of %s does not say anything about that change yet." % path
    drafted = draft_text_for(entry)

    body = formats.render_pr_body(
        {
            "before": before,
            "after": _collapse(drafted),
            "why": (
                "This context change was written down and %s was never brought in "
                "line with it. The words below are a first draft for the owner "
                "to correct or replace." % path
            ),
            "evidence": "%s\n\n%s" % (_entry_citation(entry, entry_file), _quote(entry.body)),
            "confidence": DRAFT_CONFIDENCE,
            "rule_changed": "None",
            "marker": marker_line(staging_id, entry.id, None),
        }
    )
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin="ledger",
        intake_path="ledger",
        target_paths=[path],
        sequence=0,
        rule_change=False,
        confidence=DRAFT_CONFIDENCE,
        third_party=False,
        pr_body=body,
        source_id=None,
        decision_block=None,
        edits=[formats.Edit(path, heading, operation, drafted + "\n")],
        excerpt=_collapse(entry.body, constants.MAX_EXCERPT_CHARS),
        first_draft=True,
    )
    return staging.validate()


def build_affected_files_proposal(
    entry, entry_file: str, candidates: List[str]
) -> "formats.ProposalStaging":
    """The prepared list of files a context change touches, when it named none.

    A context change that names no files is not an edit to any one file, so this
    proposal asks the owner to approve the list itself. Each named file gets one
    line saying it was named by GTM Base, and accepting the proposal is the
    owner saying the list is right.
    """
    staging_id = ids.staging_id(entry.id, constants.MAP_PATH, "ledger", 1)
    edits = [
        formats.Edit(
            path,
            FALLBACK_HEADING,
            "add",
            "This file was named by GTM Base as affected by context change %s; confirm "
            "or remove it.\n" % entry.id,
        )
        for path in candidates
    ]
    body = formats.render_pr_body(
        {
            "before": "Context change %s does not say which files it affects."
            % entry.id,
            "after": "Context change %s is marked as affecting %s."
            % (entry.id, ", ".join(candidates)),
            "why": (
                "Whoever wrote this context change down left the list of files it "
                "affects blank, so GTM Base worked out which files it most "
                "likely touches. The owner is approving that list. Accepting "
                "this marks each file named above as one the change touches, "
                "and turning it down leaves the list as it was."
            ),
            "evidence": "%s\n\n%s" % (_entry_citation(entry, entry_file), _quote(entry.body)),
            "confidence": DRAFT_CONFIDENCE,
            "rule_changed": "None",
            "marker": marker_line(staging_id, entry.id, None),
        }
    )
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin="ledger",
        intake_path="ledger",
        target_paths=list(candidates),
        sequence=1,
        rule_change=False,
        confidence=DRAFT_CONFIDENCE,
        third_party=False,
        pr_body=body,
        source_id=None,
        decision_block=None,
        edits=edits,
        excerpt=_collapse(entry.body, constants.MAX_EXCERPT_CHARS),
    )
    return staging.validate()


def staging_path_for(base_root: str, staging_id: str) -> str:
    return os.path.join(
        base_root, constants.PROPOSALS_PENDING_DIR, staging_id + ".md"
    )


def save_staging(base_root: str, staging) -> str:
    """Write one prepared change where the review skill looks for it.

    Both this module and the confirmation flow prepare changes, and both write
    them the same way, so the writing lives in one place.
    """
    path = staging_path_for(base_root, staging.staging_id)
    atomic_write_text(path, staging.render(), mode=0o600)
    return path


# --- The review-by list the hook picks up ------------------------------------


def save_review_by_items(base_id: str, items, today: datetime.date) -> str:
    """Write the context changes that have come up for review, for the next session."""
    payload = {
        "schema": 1,
        "date": today.isoformat(),
        "items": [
            {
                "entry_id": item.entry_id,
                "review_by": item.review_by.isoformat()
                if hasattr(item.review_by, "isoformat")
                else str(item.review_by),
                "days_overdue": int(item.days_overdue),
            }
            for item in items
        ],
    }
    path = os.path.join(paths.seat_dir(base_id), REVIEW_BY_FILE)
    atomic_write_json(path, payload)
    return path


def load_review_by_items(base_id: str) -> List[dict]:
    """The context changes the last run found waiting for review, or none."""
    payload = read_json(os.path.join(paths.seat_dir(base_id), REVIEW_BY_FILE))
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


# --- Getting the base ready --------------------------------------------------


def _fast_forward(base_root: str, branch: str, git: GitRunner, result) -> bool:
    """Bring the base up to date, or say in one sentence why it was not."""
    fetched = git.run(
        ["fetch", "origin", branch, "--quiet"],
        cwd=base_root,
        timeout=constants.FETCH_TIMEOUT_SECONDS,
    )
    if not fetched.ok:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_UNREACHABLE)
        result.sentences.append(UNREACHABLE)
        return False
    target = "origin/" + branch
    counted = git.run(
        ["rev-list", "--count", "HEAD.." + target], cwd=base_root
    )
    try:
        behind = int(counted.out()) if counted.ok else 0
    except ValueError:
        behind = 0
    if behind <= 0:
        return True
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok or status.out():
        result.status = STATUS_STOPPED
        result.codes.append(CODE_UNSAVED_EDITS)
        result.sentences.append(UNSAVED_EDITS)
        return False
    merged = git.run(
        ["merge", "--ff-only", target],
        cwd=base_root,
        timeout=constants.FETCH_TIMEOUT_SECONDS,
    )
    if not merged.ok:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_COULD_NOT_UPDATE)
        result.sentences.append(COULD_NOT_UPDATE)
        return False
    result.codes.append(CODE_BROUGHT_UP_TO_DATE)
    result.sentences.append(BROUGHT_UP_TO_DATE)
    return True


def _retry_pending(base_id: str, base_root: str, git: GitRunner) -> None:
    """Send a confirmation that could not be sent last time, if we can yet."""
    try:
        from . import confirm  # noqa: F401
    except ImportError:
        return
    retry = getattr(confirm, "retry_pending", None)
    if retry is None:
        return
    try:
        retry(base_id=base_id, base_root=base_root, runner=git)
    except Exception:
        return


# --- The first run's one finding ---------------------------------------------


def _baseline_sentence(report, finding) -> str:
    """The honest baseline, said about the two documents the base holds.

    Each document is named the way a person names it. A date is named once
    when both documents share it and twice when they do not, because setting
    up can be resumed on a later day and then the two confirmations really do
    fall on different days. A document nobody has confirmed has no review date
    to give, so that case is said in its own words rather than with a date
    invented for it.

    What comes back is three short lines: what was confirmed and when, that
    nothing is recorded to check it against, and when the base will ask again.
    """
    items = report.baseline_items()
    unnamed = [item for item in items if item.confirmed_on is None]
    if unnamed or len(items) != 2:
        path = finding.path or (items[0].path if items else constants.REQUIRED_CONTEXT_FILES[0])
        return FINDING_BASELINE_UNCONFIRMED % names.document_name(path)
    first, second = items[0], items[1]
    one_name = names.document_name(first.path)
    other_name = names.document_name(second.path)
    if str(first.confirmed_on) == str(second.confirmed_on):
        confirmed = FINDING_BASELINE_CONFIRMED_ONE_DAY % (
            one_name,
            other_name,
            first.confirmed_on,
        )
    else:
        confirmed = FINDING_BASELINE_CONFIRMED_TWO_DAYS % (
            one_name,
            first.confirmed_on,
            other_name,
            second.confirmed_on,
        )
    if str(first.review_on) == str(second.review_on):
        ask_again = FINDING_BASELINE_ASK_ONE_DAY % first.review_on
    else:
        ask_again = FINDING_BASELINE_ASK_TWO_DAYS % (
            one_name,
            first.review_on,
            other_name,
            second.review_on,
        )
    return "\n".join([confirmed, FINDING_BASELINE_NOTHING_TO_CHECK, ask_again])


def finding_sentence(report, finding) -> str:
    """The one honest thing a first run says, in plain words.

    It never claims more than the dates show. A base with nothing recorded
    against it gets the baseline sentence, which says what it cannot check yet
    rather than saying that nothing is out of date. Only a base that does hold
    a context change is ever told that nothing is out of date.
    """
    if finding.code == stale.FINDING_REQUIRED_FILE_MISSING:
        return FINDING_REQUIRED_FILE % finding.path
    if finding.code == stale.FINDING_BASELINE_NO_CHANGES:
        return _baseline_sentence(report, finding)
    if finding.code == stale.FINDING_CHANGE_WRITTEN_TWICE:
        return FINDING_WRITTEN_TWICE
    if finding.code == stale.FINDING_DOCUMENT_BEHIND:
        return FINDING_DOCUMENT_BEHIND % names.document_name(finding.path)
    if finding.code == stale.FINDING_DOCUMENT_OLDER:
        decided = None
        for item in report.review_items:
            if item.path == finding.path and item.entry_id == finding.entry_id:
                decided = item.decided_on
                break
        return FINDING_DOCUMENT_OLDER % (
            finding.path,
            finding.date,
            finding.entry_id,
            decided,
        )
    if finding.code == stale.FINDING_CHANGE_WAITING:
        return FINDING_CHANGE_WAITING % names.document_name(finding.path)
    if finding.date is None:
        return FINDING_NOTHING_YET_NO_DATE
    # The change is named the way a person names one, never by its identifier
    # (finding G5, and the standard every other sentence already follows).
    return FINDING_NOTHING_YET % (
        finding.date,
        _the_change_called(report, finding.entry_id),
    )


def _the_change_called(report, entry_id) -> str:
    """One context change, named the way somebody would say it out loud."""
    for entry in getattr(report, "entries", None) or []:
        if getattr(entry, "id", None) == entry_id:
            return names.change_name(
                getattr(entry, "body", ""), getattr(entry, "decided_on", None)
            )
    return "the one you recorded"


def first_run_text(result) -> str:
    """The one sentence a first run has to say, ready to be read out loud.

    It is the finding the run already worked out, in the fixed order: a file
    the person did not write, then a document older than the change it is meant
    to reflect, then the baseline for a base with no context change recorded,
    then the plain statement that nothing is out of date yet with the first
    date it will watch. When the run stopped before it could
    look at anything, what comes back is the reason it stopped, because that is
    the only honest thing there is to say.
    """
    sentence = getattr(result, "finding_sentence", None)
    if sentence:
        return sentence
    report = getattr(result, "report", None)
    finding = getattr(result, "finding", None)
    if report is not None and finding is not None:
        return finding_sentence(report, finding)
    sentences = list(getattr(result, "sentences", []) or [])
    return sentences[0] if sentences else ""


# --- The run -----------------------------------------------------------------


def run(
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    gh=None,
    now: Optional[datetime.date] = None,
    session_id: Optional[str] = None,
    mode: str = "normal",
    dismiss_quiet_record: bool = False,
    dry_run: bool = False,
    dismiss_ledger_behind: bool = False,
) -> StaleCheckResult:
    """Work out what is out of date, and prepare the change for each answer.

    There are three ways to run this. The normal run prepares a change for
    every flag. The first run says the one honest thing a base with nothing
    recorded against it can be told. The review walks what is due and what has
    been prepared as one short list, one line per item, and it is the one that
    asks, because nothing asks at the start of a session any more.
    """
    git = runner_or_default(runner)
    # The older name for this is still answered to, for the same reason the
    # option on the command line is: a session holding the older instructions
    # asks by that name, and refusing it loses the answer just given.
    dismiss_quiet_record = dismiss_quiet_record or dismiss_ledger_behind
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    known = ("first-run", "review")
    result = StaleCheckResult(mode=mode if mode in known else "normal")
    result.dry_run = bool(dry_run)

    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_NOT_ON_DEFAULT)
        result.sentences.append(NOT_ON_DEFAULT)
        return result

    has_remote = paths.remote_url(base_root, runner=git) is not None
    branch = git.run(
        ["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=base_root
    ).out()
    if has_remote:
        if not _fast_forward(base_root, branch, git, result):
            return result
    else:
        result.codes.append(CODE_NO_SHARED_COPY)

    seat, _problems = state.load_seat(base_id)
    if seat.get("pending_confirmation"):
        _retry_pending(base_id, base_root, git)

    waiting = state.unprocessed_rows(base_id)
    result.unprocessed_count = len(waiting)
    if waiting:
        result.drafting_refused = True
        result.codes.append(CODE_UNPROCESSED)
        result.sentences.append(UNPROCESSED % len(waiting))

    inputs = base_reader.read_base(
        base_root, base_id, runner=git, today=today, record_dropped=not dry_run
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
    result.report = report
    # Every document with a change waiting on an answer, which is checked
    # before any all-clear (finding G5). It is read here, where the folder is,
    # rather than worked out from the record, because a prepared change is a
    # file and the record does not know about it.
    report.changes_waiting, orphaned = _documents_with_a_change_waiting(
        base_root
    )
    if orphaned:
        result.sentences.append(CHANGE_ABOUT_A_MISSING_DOCUMENT)
    entry_files = inputs.entry_files()

    if result.mode == "first-run":
        finding = report.first_run_finding()
        result.finding = finding
        result.finding_sentence = finding_sentence(report, finding)
        result.sentences.append(result.finding_sentence)
        _report_the_rest(result, report, base_id, today, dry_run)
        if not has_remote:
            _list_awaiting_local_approval(result, base_root, git)
        return result

    if result.mode == "review":
        _review(
            result,
            report,
            inputs,
            base_root,
            base_id,
            session_id,
            today,
            git,
            dry_run,
        )
        return result

    if not result.drafting_refused:
        _prepare_everything(
            result, report, inputs, entry_files, base_root, base_id, gh, dry_run
        )
    else:
        _list_without_preparing(result, report)

    _report_the_rest(result, report, base_id, today, dry_run)

    # A base with no shared copy has nowhere to send a prepared change, so the
    # ones waiting are waiting on the owner here rather than on a reviewer.
    if not has_remote:
        _list_awaiting_local_approval(result, base_root, git)

    if dismiss_quiet_record and not dry_run:
        window = report.settings.confirmation_threshold_days
        until = today + datetime.timedelta(days=window)
        kept = state.set_ledger_behind_dismissed_until(
            base_id, until, today=today
        )
        result.sentences.append(LEDGER_BEHIND_DISMISSED % kept.isoformat())

    if dry_run:
        result.codes.append(CODE_DRY_RUN)
        result.sentences.append(DRY_RUN_NOTE)
    return result


def _happened_on(inputs, entry_id: Optional[str]) -> str:
    """The day one context change happened, read off the change itself."""
    if not entry_id:
        return ""
    entry = base_reader.entry_by_id(inputs, entry_id)
    return getattr(entry, "decided_on", "") or ""


def _review(
    result, report, inputs, base_root, base_id, session_id, today, git, dry_run
) -> None:
    """Walk what is due and what has been prepared, as one short list.

    Every document due a look gets one line and one single-use question bound
    to this session, issued here exactly as the session-start hook used to
    issue it, and written into the log of what was asked with no answer yet. A
    document that also has a change prepared for it is one line and not two,
    because it is one document and somebody is going to deal with it once.
    Prepared changes that belong to no listed document are listed after them.
    The three answers are explained once by the skill, at the top, and never
    once per item.
    """
    # Quiet asked for until the person asks again ends here, because asking
    # for a review is the asking it was waiting for.
    seat, _problems = state.load_seat(base_id)
    if state.silent_until_asked(seat) and not dry_run:
        state.set_silent_until(base_id, None)
        result.sentences.append(REVIEW_SPEAKING_AGAIN)

    _say_what_is_written_twice(result, report)

    waiting_to_be_read = state.unprocessed_rows(base_id)
    email = base_reader.repo_email(base_root, git)
    lines = _review_documents(
        result, report, inputs, base_root, base_id, email, today, dry_run
    )
    _review_prepared_changes(result, report, base_root, git, lines)

    for number, line in enumerate(lines, start=1):
        line.number = number
        line.sentence = line.sentence % number

    if not lines:
        result.sentences.append(
            REVIEW_NOTHING_OWNED if _owns_nothing(report, email) else REVIEW_NOTHING
        )
        # A base with nothing due is exactly the base whose record of context
        # changes is most likely to be the thing that is quiet, so the ask
        # happens here too rather than only when something was listed.
        _quiet_record_ask(result, report, base_id, session_id, dry_run)
        return

    result.sentences.append(REVIEW_OPENING)
    if waiting_to_be_read:
        # Every question below would be refused while these are unread, so it
        # is said once at the top rather than found out one answer at a time.
        result.sentences.append(REVIEW_INBOX_WAITING % len(waiting_to_be_read))
    if not session_id:
        result.sentences.append(REVIEW_NO_SESSION)
    for line in lines:
        result.sentences.append(line.sentence)
    result.review = lines

    _quiet_record_ask(result, report, base_id, session_id, dry_run)
    _offer_the_update(result, base_root, base_id, today, git)

    if session_id and not dry_run and not waiting_to_be_read:
        # No question is issued while something is waiting to be read, because
        # every one of them would be refused on the way back, and a question
        # nobody can answer is a question that only spoils the yes rate.
        # A document a change disagrees with itself about gets no question
        # either. A yes there would settle that change against the document
        # for good, and neither copy of it has been read by anybody yet.
        cannot_vouch = _cannot_vouch_for(report)
        for line in lines:
            if line.kind != "document":
                continue
            if line.path in cannot_vouch:
                continue
            line.question_id = _question_for_review(
                base_id, line.path, line.trigger, line.entry_id, session_id, today
            )


def _owns_nothing(report, email) -> bool:
    """Whether this seat's address owns no document in the base at all."""
    if not email:
        return True
    for info in report.files.values():
        if getattr(info, "present", False) and email in (info.owners or []):
            return False
    return True


def _question_for_review(base_id, path, trigger, entry_id, session_id, today):
    """One question for one item, reusing an open one rather than adding one.

    The review can be asked for twice in one sitting, and a document can be
    listed by two runs of it. Issuing a second question each time would say the
    base asked twice and heard nothing twice, and the yes rate is worked out
    over exactly those lines.
    """
    from . import confirm

    for record in confirm.pending_questions(base_id):
        if (
            record.get("file") == path
            and record.get("trigger") == trigger
            and record.get("session_id") == session_id
            and (record.get("entry_id") or None) == (entry_id or None)
            and record.get("id")
        ):
            return record.get("id")
    question = state.issue_question_id(
        base_id, path, trigger, session_id, entry_id, None
    )
    rows, _problems = state.load_asked(base_id)
    if not any(row.get("question_id") == question for row in rows):
        state.append_asked(base_id, question, path, trigger, "unanswered", today)
    return question


def _cannot_vouch_for(report) -> set:
    """Every document a change that disagrees with itself is about."""
    named = set()
    for conflict in report.conflicts:
        named.update(conflict.affects)
    return named


def _review_documents(
    result, report, inputs, base_root, base_id, email, today, dry_run
) -> List["ReviewLine"]:
    """One line per document due a look, and every document, not one per change.

    The flags are read rather than the questions, because one context change
    can leave three documents behind and a review that names one of them is a
    review that hides two. The filters are the ones the questions use: a
    document this seat's address owns, not one set aside for now, and never the
    base's own map.
    """
    lines: List[ReviewLine] = []
    for flag in report.file_flags:
        info = report.files.get(flag.path)
        if info is None or not info.present:
            continue
        if stale.is_map(info):
            continue
        if email is not None and email not in (info.owners or []):
            continue
        if report.suppressions and flag.path in report.suppressions:
            if state.is_suppressed(base_id, flag.path, today):
                continue
        try:
            path = paths.canonical_context_path(base_root, flag.path)
        except (PathError, ValidationError):
            if not dry_run:
                entry_id = flag.entry_ids[0] if flag.entry_ids else None
                state.append_dropped_path(
                    base_id, flag.path, "dropped-path", entry_id, today
                )
            continue
        entry_id = flag.entry_ids[0] if flag.entry_ids else None
        if flag.trigger == stale.TRIGGER_LEDGER:
            sentence = REVIEW_ITEM_CHANGE % (
                "%s",
                names.document_name(path),
                _happened_on(inputs, entry_id),
            )
        else:
            sentence = REVIEW_ITEM_THRESHOLD % ("%s", names.document_name(path))
        lines.append(
            ReviewLine(
                None, path, "document", flag.trigger, entry_id, None, sentence
            )
        )
    del result
    return lines


def _review_prepared_changes(result, report, base_root, git, lines) -> None:
    """Every prepared change, folded into its document's line or added after.

    A base with a shared copy has its prepared changes reviewed there, so they
    are listed all the same and said differently, because a person who is told
    nothing is waiting when something is waiting will believe it.
    """
    del result
    here = not report.has_remote
    waiting = (
        awaiting_local_approval(base_root, runner=git)
        if here
        else _prepared_elsewhere(base_root)
    )
    for staging_id, targets in waiting:
        for path in targets:
            folded = False
            for line in lines:
                if line.path != path or line.kind != "document":
                    continue
                folded = True
                if line.trigger != stale.TRIGGER_LEDGER:
                    line.sentence = (
                        line.sentence.rstrip(".")
                        + ", and a prepared change for it is waiting."
                    )
                    continue
                when = line.sentence.split("recorded on ")[-1].rstrip(".")
                if here:
                    line.sentence = REVIEW_ITEM_WAITING_HERE % (
                        "%s",
                        names.document_name(path),
                        when,
                    )
                else:
                    line.sentence = REVIEW_ITEM_CHANGE % (
                        "%s",
                        names.document_name(path),
                        when,
                    )
                    line.sentence = (
                        line.sentence.rstrip(".")
                        + ", and a prepared change for it is waiting for "
                        "somebody to review it."
                    )
            if folded:
                continue
            if any(line.path == path and line.kind == "change" for line in lines):
                continue
            sentence = (
                "%s. " + (AWAITING_LOCAL_APPROVAL % names.document_name(path))
                if here
                else REVIEW_ITEM_WAITING_THERE % ("%s", names.document_name(path))
            )
            lines.append(
                ReviewLine(None, path, "change", None, staging_id, None, sentence)
            )


def _prepared_elsewhere(base_root: str):
    """Every prepared change waiting, on a base whose review happens elsewhere."""
    found = []
    folder = os.path.join(base_root, constants.PROPOSALS_PENDING_DIR)
    if not os.path.isdir(folder):
        return found
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
        if targets:
            found.append((staging.staging_id, targets))
    return found


def _ledger_flags(report) -> List[Tuple[str, str]]:
    """Every (change, file) pair a context change has moved past, in a fixed order."""
    pairs = []
    for flag in report.file_flags:
        if flag.trigger != stale.TRIGGER_LEDGER:
            continue
        for entry_id in flag.entry_ids:
            pairs.append((entry_id, flag.path))
    return sorted(set(pairs))


def _list_without_preparing(result, report) -> None:
    """Say what a context change has moved past without preparing anything for it."""
    for entry_id, path in _ledger_flags(report):
        result.sentences.append(
            "%s is out of date against context change %s." % (path, entry_id)
        )


def _list_waiting_on_the_owner(result, report) -> None:
    """The documents nobody has said are still right, which nothing can fix."""
    for flag in report.file_flags:
        if flag.trigger == stale.TRIGGER_LEDGER:
            continue
        if flag.newest_confirmation is None:
            result.sentences.append(
                "Nobody has ever said %s is still right." % flag.path
            )
        else:
            accepted = report.merge_confirmations.get(flag.path)
            if accepted is not None and accepted.date == flag.newest_confirmation:
                result.sentences.append(
                    "%s was last said to be right on %s, when its owner accepted "
                    "the change that rewrote it, which is longer ago than this "
                    "base allows." % (flag.path, accepted.date.isoformat())
                )
            else:
                result.sentences.append(
                    "%s was last said to be right on %s, which is longer ago than "
                    "this base allows."
                    % (flag.path, flag.newest_confirmation.isoformat())
                )


def already_prepared(
    base_root: str, base_id: str, staging, entry_id: str, target_paths, gh=None
) -> Optional[str]:
    """Whether this exact change has already been prepared or decided about.

    Every path that prepares a change asks this, so a change prepared at the
    moment somebody was about to use a document is held to the same rule as one
    prepared by an ordinary run: never twice, and never one somebody has
    already turned down.

    Only what this computer holds is read. The moment-of-use flag promises to
    reach nothing, and asking a shared copy what proposals are open on it is
    reaching something, so that question belongs to the run that is allowed to
    ask it and not to this one.
    """
    return _already_here(base_root, base_id, staging, entry_id, target_paths)


def _already_here(
    base_root: str, base_id: str, staging, entry_id: str, target_paths
) -> Optional[str]:
    """The reason this change is already dealt with on this computer."""
    if _staging_exists(base_root, staging.staging_id):
        return CODE_ALREADY_STAGED
    if _recorded_in_index(base_id, staging.staging_id):
        return CODE_ALREADY_RECORDED
    for correction in _corrections_citing(base_root):
        if correction.staging_id == staging.staging_id:
            return CODE_ALREADY_ACCEPTED
        if correction.entry_id != entry_id:
            continue
        if any(path in correction.touched_paths for path in target_paths):
            return CODE_ALREADY_ACCEPTED
    return None


def _already_done(
    base_root: str, base_id: str, staging, entry_id: str, target_paths, gh
) -> Optional[str]:
    """The reason this exact change does not need preparing again, or nothing."""
    here = _already_here(base_root, base_id, staging, entry_id, target_paths)
    if here is not None:
        return here
    found = duplicate_check.check(staging, base_root, gh=gh)
    if found.kind == duplicate_check.KIND_MERGED:
        return CODE_ALREADY_ACCEPTED
    if found.kind in (duplicate_check.KIND_OPEN, duplicate_check.KIND_CLOSED):
        return CODE_ALREADY_PROPOSED
    return None


def _prepare_everything(
    result, report, inputs, entry_files, base_root, base_id, gh, dry_run
) -> None:
    """One prepared edit per flag, and one per context change that named no files."""
    for entry_id, path in _ledger_flags(report):
        entry = base_reader.entry_by_id(inputs, entry_id)
        if entry is None:
            result.skipped.append(Skipped(None, entry_id, path, CODE_NO_ENTRY))
            continue
        try:
            staging = build_file_proposal(
                base_root, entry, entry_files.get(entry_id, ""), path
            )
        except (ValidationError, PathError) as failure:
            result.skipped.append(
                Skipped(None, entry_id, path, failure.code or CODE_MISSING_FILE)
            )
            continue
        _write_one(
            result, base_root, base_id, staging, entry_id, [path], "file", gh, dry_run
        )

    for proposal in report.affected_files_proposals:
        entry = base_reader.entry_by_id(inputs, proposal.entry_id)
        if entry is None:
            continue
        if not proposal.candidate_paths:
            result.skipped.append(
                Skipped(None, proposal.entry_id, None, CODE_NO_CANDIDATES)
            )
            result.sentences.append(
                "Context change %s does not say which files it affects, and GTM Base "
                "could not work out which files it touches." % proposal.entry_id
            )
            continue
        staging = build_affected_files_proposal(
            entry, entry_files.get(proposal.entry_id, ""), list(proposal.candidate_paths)
        )
        _write_one(
            result,
            base_root,
            base_id,
            staging,
            proposal.entry_id,
            list(proposal.candidate_paths),
            "affected-files",
            gh,
            dry_run,
        )


def _write_one(
    result, base_root, base_id, staging, entry_id, target_paths, kind, gh, dry_run
) -> None:
    reason = _already_done(base_root, base_id, staging, entry_id, target_paths, gh)
    if reason is not None:
        result.skipped.append(Skipped(staging.staging_id, entry_id, target_paths[0], reason))
        return
    path = staging_path_for(base_root, staging.staging_id)
    if not dry_run:
        save_staging(base_root, staging)
        if getattr(staging, "first_draft", False):
            # Written where no file tool may write it, so taking the marker
            # line out of the prepared change changes nothing (finding M1).
            state.note_first_draft(base_id, staging.staging_id)
    result.staged.append(
        Staged(staging.staging_id, path, target_paths, entry_id, kind)
    )
    if kind == "affected-files":
        result.sentences.append(
            "Context change %s named no files, so GTM Base prepared a list of the %d "
            "files it looks like it touches, for you to approve."
            % (entry_id, len(target_paths))
        )
    else:
        result.sentences.append(
            "%s is out of date against context change %s, and an edit for it is "
            "prepared as %s." % (target_paths[0], entry_id, staging.staging_id)
        )


def _offer_the_update(result, base_root, base_id, today, git) -> None:
    """Offer to store this base's context changes the way they are stored now.

    It comes after the review's own list, because the person asked for the
    review and this is an aside. Nothing is applied on the strength of it: the
    move runs only on their yes.

    What to say is worked out rather than assumed. An offer somebody could say
    yes to and then have refused is not an offer, so the checks the move
    itself runs are run here first, and none of them writes anything.
    """
    offer = changes.what_to_offer(base_root, base_id, today=today, git=git)
    if offer == changes.OFFER_NOW:
        result.sentences.append(changes.OFFER)
        result.codes.append(CODE_CHANGES_CAN_MOVE)
    elif offer == changes.OFFER_EVERY_SEAT_FIRST:
        result.sentences.append(changes.EVERY_SEAT_FIRST)
        result.codes.append(CODE_EVERY_SEAT_FIRST)


def _say_what_is_written_twice(result, report) -> None:
    """Name every change written down twice, and the documents it is about.

    Nothing else in the run knows about these, because a change nobody can
    read is not in the record the rules are worked out from. Saying nothing
    is what made a disagreement look like a base with nothing recorded in it,
    with every document it was about quietly unflagged.
    """
    for conflict in report.conflicts:
        result.sentences.append(
            WRITTEN_TWICE % (conflict.entry_id, " and ".join(conflict.paths))
        )
        if conflict.affects:
            result.sentences.append(
                CANNOT_VOUCH
                % ", ".join(names.document_name(path) for path in conflict.affects)
            )
        result.codes.append(CODE_WRITTEN_TWICE)


def _quiet_record_ask(result, report, base_id, session_id, dry_run) -> None:
    """Mention the quiet record of context changes, inside the review only.

    Requirement P17, and Codex condition C. Nothing says this at the start of
    a session any more, because the base is quiet until somebody asks it
    something, and nothing says it twice in one sitting: asking for the review
    a second time is not a second reason to be told. A dismissal is what
    `stale.compute` already reads, so a dismissed reminder never gets here at
    all until the window it was dismissed for has passed.
    """
    behind = report.ledger_behind
    if behind is None or not behind.behind:
        return
    seat, _problems = state.load_seat(base_id)
    if session_id and seat.get("quiet_record_said_in_session") == session_id:
        return
    window = report.settings.confirmation_threshold_days
    if behind.newest_entry_date is None:
        # A base whose only change is written down twice is not a base with
        # nothing recorded in it, and telling somebody it is would send them
        # to write down what they already wrote.
        if report.conflicts:
            return
        result.sentences.append(LEDGER_BEHIND_EMPTY % window)
    else:
        result.sentences.append(
            LEDGER_BEHIND
            % (behind.newest_entry_date.isoformat(), behind.window_days, window)
        )
    if session_id and not dry_run:
        state.update_seat(base_id, quiet_record_said_in_session=session_id)


def _report_the_rest(result, report, base_id, today, dry_run) -> None:
    """The parts of the answer that are the same whatever else happened."""
    _say_what_is_written_twice(result, report)
    if report.review_by_items:
        for item in report.review_by_items:
            result.sentences.append(
                REVIEW_BY
                % (
                    item.entry_id,
                    item.review_by.isoformat()
                    if hasattr(item.review_by, "isoformat")
                    else str(item.review_by),
                    item.days_overdue,
                )
            )
        if not dry_run:
            save_review_by_items(base_id, report.review_by_items, today)

    _list_waiting_on_the_owner(result, report)

    if report.malformed:
        result.sentences.append(
            MALFORMED_ONE
            if len(report.malformed) == 1
            else MALFORMED % len(report.malformed)
        )
    if report.dropped:
        result.sentences.append(DROPPED % len(report.dropped))

    if (
        result.mode == "normal"
        and not result.staged
        and not report.file_flags
        and not result.drafting_refused
    ):
        result.sentences.append(NOTHING_FLAGGED)
