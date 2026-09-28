"""Recording a context change at any time, without editing a document.

Until 0.3.3 a context change could be written down in two places only: at the
closing of setting a base up, which needs a setup run, and together with an
edit somebody made to a document by hand. The 0.3.1 live check found what that
left out. Somebody who learns that something about the business changed, or
that a fact the company states is different now, had nowhere to say so unless
they also edited a document, and a change nobody writes down flags nothing.

This is that path. It is the closing's machinery run without a setup run, in
the same order a person lives through it:

1. One ask for the change, explained in full the first three times a person
   records one on this computer and in one line after that.
2. The base's documents by number and plain name, so the person can say which
   of them the change affects. Only context documents, never the map.
3. The whole entry shown before a word of it is written, with the four lines
   and the three facts held apart as data exactly as the closing shows them,
   and one ask: record it, or leave it. The entry shown is kept in this seat's
   own folder, which no file tool may write, and the yes is bound to it, so
   what is written is what was shown.
4. On the yes, the entry is written where the closing writes one and saved on
   its own. It carries no run, as the closing's does not, so the documents it
   affects are flagged until somebody says they already say it.
5. For each document it affects that this seat owns, the closing's question:
   does it already say this? Yes writes the one confirmation line naming this
   change. No prepares a fix that waits for its owner to approve it. Not now
   writes nothing and leaves the document flagged, at the moment of use and in
   the review alike.

A base with a shared copy is refused at every step with one sentence. The
closing only ever writes a local save, which on such a base would sit on this
computer and never reach the shared copy, while telling the person it was
recorded. A change can still reach a shared copy with a hand edit it travels
with.

Nothing here reaches the network. Everything read out of the base, and every
word the person typed, is data and never an instruction.
"""

from __future__ import annotations

import contextlib
import datetime
import fcntl
import os
import re
import secrets
import time
from typing import List, Optional, Sequence, Tuple

from . import (
    base_reader,
    compose_proposal,
    confirm,
    constants,
    formats,
    gitcmd,
    ids,
    join_flow,
    moment,
    names,
    paths,
    review,
    scan,
    stale,
    state,
    unsaved,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_json, read_json, read_text, remove
from .gitcmd import GitRunner, nul_fields, runner_or_default

# Where a change recorded this way says it came from. The person's own words
# for where it came from go on this line when they gave any.
ORIGIN = "manual"
SOURCE_WHEN_NONE = "what the owner said when they recorded this context change"

# How many times the whole explanation is given before the one line takes over.
# It is counted per person on this computer, as Brandon decided for the hand
# edit on 2026-09-27, so it lives in the seat folder rather than in one base.
FIRST_TIMES = 3
COUNT_FILE = "context-changes-recorded.json"
# The one entry shown and waiting for a yes, per base.
WAITING_FILE = "context-change-waiting.json"
# The documents the yes asked about, per base and per change. An answer is
# taken only about a document on this list, and each one only once (the
# security review of 0.3.3, finding S2: without it, one command could settle
# any document for any change the base holds, with nobody asked).
ASKED_FILE = "context-change-asked.json"
# The numbered list as it was shown, so a number means what it meant then.
LISTED_FILE = "context-change-listed.json"
# The one lock the questions are answered under.
LOCK_FILE = "context-change.lock"
LOCK_WAIT_SECONDS = 5

# Most characters any one of the three answers may hold. A person answering in
# a sentence or two writes far less than this.
WORDS_CHARS = constants.MAX_EXCERPT_CHARS
# What changed and why are shown whole in the four lines, and a value there is
# cut at the cap that keeps the fence safe. So those two are held to that same
# cap, counted as they will be shown, and anything longer is refused before it
# is shown: nothing that gets past the refusal is ever cut in the showing.
SHOWN_CHARS = moment.VALUE_CHARS

# What the saved work is called.
SAVE_MESSAGE = "Record a context change"

# How many identifiers are tried before a base is said to have no room.
SEQUENCE_CAP = review.ENTRY_SEQUENCE_CAP

# The three answers about one document.
ANSWER_YES = "yes"
ANSWER_NO = "no"
ANSWER_NOT_NOW = "not-now"
ANSWERS = (ANSWER_YES, ANSWER_NO, ANSWER_NOT_NOW)

# Codes, for the log and the tests. None is shown to a person.
CODE_SHARED_COPY = "has-a-shared-copy"
CODE_CANNOT_TELL = compose_proposal.CODE_CANNOT_TELL
CODE_NO_WORDS = "no-words-for-the-change"
CODE_TOO_LONG = "too-long"
CODE_NO_DOCUMENTS = "no-documents"
CODE_NOT_ON_THE_LIST = "not-on-the-list"
CODE_NO_DOCUMENT_CHOSEN = "no-document-chosen"
CODE_SCREENED = review.CODE_SCREENED
CODE_BAD_DAY = "bad-day"
CODE_NOTHING_WAITING = "nothing-waiting"
CODE_NOT_WHAT_WAS_SHOWN = "not-what-was-shown"
CODE_MOVED_ON = "the-base-moved-on"
CODE_NOT_ON_MAIN = review.CODE_NOT_DEFAULT_BRANCH
CODE_UNSAVED = review.CODE_UNSAVED_EDITS
CODE_COULD_NOT_SAVE = "could-not-save"
CODE_NO_ADDRESS = review.CODE_OWNER_MISSING
CODE_BAD_ANSWER = "answer-not-one-we-know"
CODE_NOT_A_DOCUMENT = moment.CODE_NOT_A_CONTEXT_FILE
CODE_NO_ROOM = review.CODE_NO_ROOM_FOR_A_CHANGE
CODE_NOT_ASKED = "not-asked-about-here"
CODE_NO_LIST_YET = "no-list-shown-yet"
CODE_LIST_CHANGED = "the-list-changed"
CODE_TOO_MANY_DOCUMENTS = "too-many-documents"
CODE_CHANGE_CHANGED = "the-change-changed"
CODE_RUNS_A_PROGRAM = gitcmd.CODE_EXECUTABLE_DRIVER
CODE_NOT_ALL_TAKEN_BACK = "not-all-taken-back"
CODE_BUSY = "busy"

# What a document is called in anything this path says, when its file name is
# not one a sentence may safely repeat (finding S1 of the same review).
UNNAMED_DOCUMENT = names.DOCUMENT_WITHOUT_A_PLAIN_NAME
# A file name read out in a sentence is at most a few plain words, lower case,
# joined by hyphens or underscores. Anything else is not repeated back.
_SAFE_STEM_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+){0,5}$")
SAFE_STEM_CHARS = 40

# --- The sentences a person reads -------------------------------------------

# Brandon's decided hand-edit wording of 2026-09-27, adapted to a change
# recorded on its own: the explanation for the first three times, the ask, and
# the one line from the fourth time on.
EXPLAIN = (
    "GTM Base keeps a short record of each context change, so you have a "
    "history of why your context changed and so your documents can be checked "
    "against it; anything that still says the old thing gets flagged. The "
    "record holds what changed (in the business, or in a fact you state about "
    "it), why, where it came from, and which documents it affects."
)
ASK = "In a sentence or two: what changed, why, and where did it come from?"
ASK_SHORT = (
    "I'll keep a record of this context change so your documents can be "
    "checked against it. What changed, why, and where did it come from?"
)
DOCUMENTS_INTRO = "These are the documents in your base, by number."
NO_DOCUMENTS = (
    "Your base holds no documents yet besides its map, so there is nothing a "
    "context change could affect. Set up your company base first."
)
PREVIEW_ASK = "Record this context change, or leave it?"
RECORDED = "That context change is recorded."
LEFT = "Nothing was recorded, and your base is exactly as it was."
LEFT_FLAGGED = (
    "%s stays flagged, so GTM Base will say so when it is about to be used and "
    "in your next review."
)
SHARED_COPY = (
    "This base has a shared copy, and GTM Base cannot yet record a context "
    "change there on its own, so nothing was written. It can still be recorded "
    "together with an edit to a document it affects."
)
NEEDS_WORDS = (
    "A context change needs what changed, in their words, so nothing was "
    "shown. Ask again and write their answer to a new file."
)
TOO_LONG = (
    "That is longer than a context change can hold, so nothing was shown. Ask "
    "for it again in a sentence or two."
)
NOT_ON_THE_LIST = (
    "That is not one of the numbers beside the documents on the list, so "
    "nothing was shown. Read the list out again and ask which of those."
)
NEEDS_A_DOCUMENT = (
    "A context change has to affect at least one document, so nothing was "
    "shown. Ask which of the numbered documents it affects."
)
BAD_DAY = (
    "That is not a day a context change can have happened on, so nothing was "
    "shown. Ask for the day again, written as year, month and day."
)
SCREENED_NEXT = "Nothing was shown. Ask for it again without that part."
NOTHING_WAITING = (
    "No context change is waiting to be recorded, so nothing was written. Show "
    "it again and ask again."
)
NOT_WHAT_WAS_SHOWN = (
    "That is not the context change that was shown, so nothing was written. "
    "Show it again and ask again."
)
MOVED_ON = (
    "Your base changed after that context change was shown, so nothing was "
    "written. Show it again and ask again."
)
NOT_ON_MAIN = (
    "Your base is not on its main line right now, so nothing was recorded. Ask "
    "GTM Base to put it back, then ask again."
)
UNSAVED = (
    "There are words in your base that you have not saved, so nothing was "
    "recorded. Save them or put them aside and ask again."
)
# The same refusal with the unsaved files said in it, where the `%s` is.
UNSAVED_NAMED = (
    "There are words in your base that you have not saved, so nothing was "
    "recorded. %s Save them or put them aside and ask again."
)
COULD_NOT_SAVE = (
    "GTM Base could not save that context change into your base, so nothing "
    "was written. Ask again in a moment."
)
NO_ADDRESS = (
    "GTM Base does not know which address your base records your work under, "
    "so nothing was shown. Set your address on this base and ask again."
)
NO_ROOM = (
    "Your base already holds as many context changes as GTM Base can name, so "
    "nothing was written."
)
ANSWER_UNKNOWN = (
    "That answer has to be yes, no, or not now, so nothing was recorded. Ask "
    "again and run this with the answer they gave."
)
NOT_ASKED = (
    "GTM Base did not ask about that document for that context change, or it "
    "was answered already, so nothing was recorded."
)
NO_LIST_YET = (
    "No list of your documents has been shown yet, so nothing was shown. Show "
    "the list first and ask which of them it affects."
)
LIST_CHANGED = (
    "Your documents changed after the list was shown, so nothing was shown. "
    "Show the list again and ask again."
)
TOO_MANY_DOCUMENTS = (
    "That is more documents than one context change can list, so nothing was "
    "shown. Choose fewer, or record two."
)
CHANGE_CHANGED = (
    "That context change is not what it was when the question was asked, so "
    "nothing was recorded, and the document stays flagged for your next "
    "review."
)
RUNS_A_PROGRAM = (
    "Your base is set up to run a program of its own on its files when they "
    "are saved, and GTM Base never runs one, so nothing was written."
)
NOT_ALL_TAKEN_BACK = (
    "GTM Base could not save that context change, and something else changed "
    "the same file while it was trying, so it left that file exactly as it is "
    "now rather than take it back."
)
BUSY = (
    "Another window is answering about this base right now, so nothing was "
    "recorded. Ask again in a moment."
)


class Refused(GtmBaseError):
    """A step that stopped, with the one sentence that says why."""

    default_code = "refused"


def _refuse(sentence: str, code: str) -> Refused:
    return Refused(sentence, code=code)


# --- The shared copy ---------------------------------------------------------


def refuse_a_shared_copy(base_root: str, runner: Optional[GitRunner] = None) -> None:
    """Stop at once on a base with a shared copy, or one nobody can tell about.

    Not being able to read whether there is one is its own answer and never a
    no, the rule `compose_proposal.shared_copy_state` already keeps.
    """
    found = compose_proposal.shared_copy_state(base_root, runner=runner)
    if found == compose_proposal.SHARED_COPY_PRESENT:
        raise _refuse(SHARED_COPY, CODE_SHARED_COPY)
    if found != compose_proposal.SHARED_COPY_ABSENT:
        raise _refuse(compose_proposal.CANNOT_TELL, CODE_CANNOT_TELL)


# --- Step 1: the ask ---------------------------------------------------------


def _count_path() -> str:
    return os.path.join(paths.seat_home(), COUNT_FILE)


def times_recorded() -> int:
    """How many context changes this person has recorded this way here."""
    payload = read_json(_count_path())
    if not isinstance(payload, dict):
        return 0
    count = payload.get("count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return 0
    return count


def _count_one_more() -> None:
    atomic_write_json(
        _count_path(),
        {"schema": 1, "count": times_recorded() + 1},
        inside=paths.seat_home(),
    )


def ask(long: bool = False) -> List[str]:
    """What is said before the one ask, and the ask itself.

    The whole explanation for the first three times, and whenever somebody
    asks why they are being asked; the one line after that.
    """
    if long or times_recorded() < FIRST_TIMES:
        return [EXPLAIN, ASK]
    return [ASK_SHORT]


# --- Step 2: which documents -------------------------------------------------


def safe_name(path: str) -> str:
    """What a document is called in anything this path says out loud.

    The documents the product knows keep their own names, and a file named in
    a few plain lower-case words is called by those words. Every other name is
    "one of your documents", because a file name is whatever somebody typed,
    and a name shaped like an instruction was read out as one (the same class
    0.3.2 closed for the refusal that names unsaved files).
    """
    normalized = str(path or "").replace(os.sep, "/")
    if normalized in names.KNOWN_DOCUMENTS:
        return names.KNOWN_DOCUMENTS[normalized]
    stem = os.path.basename(normalized)
    if stem.endswith(".md"):
        stem = stem[: -len(".md")]
    if len(stem) > SAFE_STEM_CHARS or not _SAFE_STEM_RE.match(stem):
        return UNNAMED_DOCUMENT
    try:
        return names.document_name(normalized)
    except ValueError:
        return UNNAMED_DOCUMENT


def can_be_asked_about(path: str) -> bool:
    """Whether the questions and answers may name this document at all.

    Every sentence the questions and the answers print names the document the
    way the closing does, so only a document whose name is safe to repeat, and
    whose name has no space in it (which no confirmation line can carry yet),
    is asked about. Any other stays flagged for the review, which names it.
    """
    try:
        closing_name = names.document_name(path)
    except ValueError:
        return False
    return (
        not formats.name_has_a_space(path)
        and safe_name(path) == closing_name
        and closing_name != UNNAMED_DOCUMENT
    )


def documents(base_root: str) -> List[Tuple[int, str, str]]:
    """The base's context documents, numbered, with the name a person reads.

    The map is never one of them: nothing about the business can make it
    wrong. A document a context change could not name safely, such as one
    reached through a link out of the base or one whose name a list setting
    cannot hold, is left off rather than offered and refused later.
    """
    found: List[Tuple[int, str, str]] = []
    for info in base_reader.context_files(base_root):
        path = info.path
        # A map is left off by what it says it is, wherever it sits (Astra's
        # review of 0.3.3, finding 12).
        if path == constants.MAP_PATH or stale.is_map(info):
            continue
        if any(mark in path for mark in (",", "[", "]")):
            continue
        try:
            if paths.canonical_context_path(base_root, path) != path:
                continue
        except (PathError, ValidationError):
            continue
        found.append((len(found) + 1, path, safe_name(path)))
    return found


def show_list(base_root: str, base_id: str) -> List[Tuple[int, str, str]]:
    """The numbered list, kept as it was shown so a number keeps its meaning."""
    listed = documents(base_root)
    atomic_write_json(
        os.path.join(paths.seat_dir(base_id), LISTED_FILE),
        {"schema": 1, "paths": [path for _number, path, _name in listed]},
    )
    return listed


def chosen_documents(
    base_root: str, numbers: Sequence[str], base_id: Optional[str] = None
) -> List[str]:
    """The documents the person named, by the numbers on the list they saw.

    The numbers are read against the list as it was shown, and the list has
    to be exactly what the base holds now. A document added or taken away
    since would move every number after it, and two documents can be called
    the same thing, so a changed list is refused and shown again rather than
    read (Astra's review of 0.3.3, finding 5).
    """
    current = [(number, path, name) for number, path, name in documents(base_root)]
    if base_id is not None:
        kept = read_json(os.path.join(paths.seat_dir(base_id), LISTED_FILE))
        shown = kept.get("paths") if isinstance(kept, dict) else None
        if not isinstance(shown, list):
            raise _refuse(NO_LIST_YET, CODE_NO_LIST_YET)
        if [str(path) for path in shown] != [path for _n, path, _name in current]:
            raise _refuse(LIST_CHANGED, CODE_LIST_CHANGED)
    listed = current
    chosen: List[str] = []
    for raw in numbers:
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit():
                raise _refuse(NOT_ON_THE_LIST, CODE_NOT_ON_THE_LIST)
            number = int(part)
            if number < 1 or number > len(listed):
                raise _refuse(NOT_ON_THE_LIST, CODE_NOT_ON_THE_LIST)
            path = listed[number - 1][1]
            if path not in chosen:
                chosen.append(path)
    if not chosen:
        raise _refuse(NEEDS_A_DOCUMENT, CODE_NO_DOCUMENT_CHOSEN)
    return chosen


# --- Step 3: the whole entry, shown -----------------------------------------


def _one_line(text: Optional[str]) -> str:
    return " ".join(str(text or "").split())


def as_shown(text: Optional[str]) -> str:
    """One answer the way the four lines will show it, before any cap.

    One line, with anything shaped like a marker taken apart, which is
    `moment._one_line` without its cut. Taking a marker apart adds spaces, so
    this, and not the words as typed, is what the cap is measured against.
    """
    single = _one_line(text)
    return moment._MARKERS_RE.sub(lambda found: " ".join(found.group(0)), single)


def _screened(text: str, allowlist) -> None:
    """Refuse a person's words holding a contact detail or a key.

    The same classes the closing's screen refuses in a draft, read the way the
    hand edit reads the source somebody gave, so the sentence names the kind
    of thing found and never the thing.
    """
    hits = scan.scan_text(text, allowlist, "what you said", review.SKIPPED_CLASSES)
    if hits:
        raise _refuse(hits[0].sentence() + " " + SCREENED_NEXT, CODE_SCREENED)


def _source_value(source: str) -> str:
    """Where it came from, as one settings value that reads back the same.

    A settings value is one line, and one that has to be quoted cannot hold a
    double quotation mark. Those are turned into single ones rather than
    refused, because a person quoting somebody is not a reason to stop.
    """
    value = _one_line(source) or SOURCE_WHEN_NONE
    for candidate in (value, value.replace('"', "'")):
        try:
            rendered = formats.render_scalar(candidate)
            if formats.parse_scalar(rendered) == candidate:
                return candidate
        except (ValidationError, PathError):
            continue
    return SOURCE_WHEN_NONE


def _named_anywhere(base_root: str, entry_id: str) -> bool:
    """Whether anything in this base already names this identifier.

    The closing's rule is that an identifier is free when no folder of changes
    holds it. A change somebody took out of the base by hand leaves its name
    behind in the confirmation lines that named it, in the record of what was
    corrected, and in any prepared change made from it, and a new change under
    that name would inherit every one of them, settling documents nobody was
    asked about. So a name any of those still carries is taken too.
    """
    relative, _text = base_reader.entry_path_and_text(base_root, entry_id)
    if relative is not None:
        return True
    for where in (
        constants.CONFIRMATIONS_DIR,
        constants.CORRECTIONS_DIR,
        constants.PROPOSALS_PENDING_DIR,
        constants.PROPOSALS_OPENED_DIR,
        constants.PROPOSALS_DROPPED_DIR,
    ):
        folder = os.path.join(base_root, where.replace("/", os.sep))
        try:
            listed = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in listed:
            text = read_text(os.path.join(folder, name))
            if text and entry_id in text:
                return True
    return False


def free_id(base_root: str) -> str:
    """The first identifier for a context change nothing in this base names."""
    for sequence in range(SEQUENCE_CAP):
        candidate = review.entry_id(sequence)
        if not _named_anywhere(base_root, candidate):
            return candidate
    raise _refuse(NO_ROOM, CODE_NO_ROOM)


def _day(value: Optional[str], today: datetime.date) -> datetime.date:
    if not value:
        return today
    try:
        day = datetime.date.fromisoformat(str(value).strip())
    except ValueError:
        raise _refuse(BAD_DAY, CODE_BAD_DAY)
    if day > today:
        raise _refuse(BAD_DAY, CODE_BAD_DAY)
    return day


def build_entry(
    base_root: str,
    what: str,
    why: str,
    source: str,
    affects: Sequence[str],
    today: datetime.date,
    happened_on: Optional[str] = None,
    runner: Optional[GitRunner] = None,
) -> formats.ChangeEntry:
    """The whole context change, from the person's own words.

    The words are never put through the check a model's draft goes through,
    which refuses a long dash or a word from the house list: those are rules
    for what GTM Base writes, and these are the person's own words. What is
    refused is what the closing's screen refuses, a contact detail or a key.

    The body is what changed, then why, each on a line of its own, so the four
    lines read them back the same way at the closing, at the moment of use and
    in the review. It carries no run, for the reason `review.stamp_entry`
    gives: nothing here was shown beside a document drafted in the same run.
    """
    git = runner_or_default(runner)
    what = _one_line(what)
    why = _one_line(why)
    source = _one_line(source)
    if not what:
        raise _refuse(NEEDS_WORDS, CODE_NO_WORDS)
    if any(len(words) > WORDS_CHARS for words in (what, why, source)):
        raise _refuse(TOO_LONG, CODE_TOO_LONG)
    if any(len(as_shown(words)) > SHOWN_CHARS for words in (what, why)):
        raise _refuse(TOO_LONG, CODE_TOO_LONG)
    allowlist, _code = scan.load_allowlist(base_root)
    for words in (what, why, source):
        _screened(words, allowlist)
    address = base_reader.repo_email(base_root, git) or ""
    if not address:
        raise _refuse(NO_ADDRESS, CODE_NO_ADDRESS)
    happened = _day(happened_on, today)
    settings = base_reader.settings_of(base_reader.map_text(base_root))
    look_again = today + datetime.timedelta(
        days=int(settings.confirmation_threshold_days)
    )
    body = what + ("\n\n" + why if why else "")
    entry = formats.ChangeEntry(
        id=free_id(base_root),
        happened_on=happened.isoformat(),
        written_on=today.isoformat(),
        noted_by=address,
        source=_source_value(source),
        affects=list(affects),
        review_by=look_again.isoformat(),
        origin=ORIGIN,
        status="open",
        run_id=None,
        body=body,
    )
    try:
        entry.validate(today)
        text = entry.render()
        formats.ChangeEntry.parse(text).validate(today)
    except (ValidationError, PathError):
        raise _refuse(NEEDS_WORDS, CODE_NO_WORDS)
    _screened_whole(text, address, allowlist)
    return entry


def _screened_whole(text: str, address: str, allowlist) -> None:
    """The whole entry, as it will be written, read the way the words were.

    The classes the closing's screen refuses, with the base's own list of
    allowed words, so the two readings never disagree; the one line that
    carries the base's own address is let through, as the closing lets it
    through (the correctness review of 0.3.3, finding 3).
    """
    exempt = set()
    for number, line in enumerate(text.split("\n"), start=1):
        name, _sep, value = line.partition(":")
        if name.strip() == "noted_by" and value.strip() == address:
            exempt.add(number)
    hits = [
        hit
        for hit in scan.scan_text(
            text, allowlist, "what you said", review.SKIPPED_CLASSES
        )
        if hit.line_number not in exempt
    ]
    if hits:
        raise _refuse(hits[0].sentence() + " " + SCREENED_NEXT, CODE_SCREENED)


def why_when_none(entry) -> str:
    """What the four lines say for why when the person gave no reason.

    It is the sentence the moment of use says about the same change, so the
    preview and the flag never disagree about one change.
    """
    return moment._why_of(entry)


class Shown(object):
    """One context change as it was shown, and the value the yes is bound to.

    `showing` is what the person reads: the four labeled lines inside the
    data fence and nothing else. `text` is the whole entry the yes writes.
    """

    __slots__ = ("entry", "text", "shown", "showing")

    def __init__(self, entry, text, shown, showing):
        self.entry = entry
        self.text = text
        self.shown = shown
        self.showing = showing


def _waiting_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), WAITING_FILE)


def _listed_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), LISTED_FILE)


def shown_value(text: str) -> str:
    return ids.content_hash(text)[:16]


def forget_showing(base_id: str) -> None:
    """Let go of the change shown last, before anything else about a new one.

    The show step calls this first, before it reads a single word, so a new
    showing refused for any reason at all, a words file included, never
    leaves the one before it standing to be recorded (Astra's review of
    0.3.3, finding 11).
    """
    remove(_waiting_path(base_id))


def _affected_names(affects: Sequence[str]) -> str:
    return ", ".join(safe_name(path) for path in affects) or "nothing yet"


def preview(
    base_root: str,
    base_id: str,
    what: str,
    why: str,
    source: str,
    numbers: Sequence[str],
    happened_on: Optional[str] = None,
    today: Optional[datetime.date] = None,
    runner: Optional[GitRunner] = None,
) -> Shown:
    """Show the context change as four lines, and keep it for the yes.

    Nothing goes into the base here. The person reads the four labeled lines
    inside the data fence and nothing else: no identifier, no document path,
    and no settings block, as Brandon decided on 2026-09-27 for this path
    (the closing's own preview still shows the whole entry). The one thing
    kept is the whole entry, in this seat's own folder, so the yes writes
    exactly those words, bound to the revision the base was on when it was
    shown.
    """
    git = runner_or_default(runner)
    day = today or state.today()
    refuse_a_shared_copy(base_root, runner=git)
    # A new showing replaces the one before it even when it is refused, so a
    # yes can never land on a version the person was in the middle of
    # correcting (the correctness review of 0.3.3).
    forget_showing(base_id)
    affects = chosen_documents(base_root, numbers, base_id)
    # Every document the change affects is named in the four lines, whole,
    # and the list is held to the same cap the fence keeps, counted as shown.
    # A list longer than that is refused here, before anything is kept, so
    # the four lines never leave out a document the yes would write down
    # (Astra's review of 0.3.3, finding 4).
    if len(as_shown(_affected_names(affects))) > SHOWN_CHARS:
        raise _refuse(TOO_MANY_DOCUMENTS, CODE_TOO_MANY_DOCUMENTS)
    entry = build_entry(
        base_root, what, why, source, affects, day, happened_on, runner=git
    )
    text = entry.render()
    # The four lines come from this entry and from nothing else, the closing's
    # own `four_lines_for` reading the very text that will be written.
    showing = moment.fenced(
        join_flow.four_lines_for(
            entry, why_when_none(entry), what_in_full=True, name_of=safe_name
        )
    )
    # The yes is bound to the whole entry rather than to the four lines. That
    # is safe to do although the person reads only the four lines, because
    # the four lines are worked out from this one entry and nothing else, and
    # the entry is the only thing the yes writes: whatever the person read is
    # exactly what that entry says, and nothing written falls outside it. The
    # settings the lines leave out (the identifier, the day it was written,
    # who noted it, where it came from, and the paths behind the document
    # names) are the base's own record of those same four things.
    shown = shown_value(text)
    atomic_write_json(
        _waiting_path(base_id),
        {
            "schema": 1,
            "text": text,
            "shown": shown,
            "day": day.isoformat(),
            # The revision the base was on when it was shown. A yes given
            # after anything else was saved is refused and shown again
            # (Astra's review of 0.3.3, finding 5).
            "head": _head(base_root, git),
        },
    )
    return Shown(entry, text, shown, showing)


def leave(base_id: str) -> str:
    """Leave it: nothing is written, and the change shown is let go."""
    forget_showing(base_id)
    return LEFT


# --- Step 4: the yes ---------------------------------------------------------


class Recorded(object):
    """What the yes wrote, and the documents to ask about next."""

    __slots__ = ("entry", "relative", "plan")

    def __init__(self, entry, relative, plan):
        self.entry = entry
        self.relative = relative
        self.plan = plan


def _waiting(base_id: str):
    payload = read_json(_waiting_path(base_id))
    if not isinstance(payload, dict):
        return None
    text = payload.get("text")
    shown = payload.get("shown")
    if not isinstance(text, str) or not isinstance(shown, str):
        return None
    if shown_value(text) != shown:
        return None
    return payload


def _head(base_root: str, git: GitRunner) -> str:
    return git.run(["rev-parse", "--verify", "--quiet", "HEAD"], cwd=base_root).out()


@contextlib.contextmanager
def _locked(base_id: str):
    """Hold this base's questions for one answer or one yes at a time.

    Reading which questions are open, answering one, and taking it off the
    list happen under one lock, and so does a yes adding its questions, so
    two windows can never both answer the same question or bring back one
    already answered (Astra's review of 0.3.3, finding 10).
    """
    handle = os.open(
        os.path.join(paths.seat_dir(base_id), LOCK_FILE),
        os.O_CREAT | os.O_RDWR,
        0o600,
    )
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    try:
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise _refuse(BUSY, CODE_BUSY)
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(handle)


def _asked_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), ASKED_FILE)


def _asked(base_id: str) -> dict:
    """The questions still open, per change: its content hash and documents."""
    payload = read_json(_asked_path(base_id))
    held = payload.get("asked") if isinstance(payload, dict) else None
    if not isinstance(held, dict):
        return {}
    kept = {}
    for entry_id, item in held.items():
        if not isinstance(item, dict):
            continue
        digest = item.get("hash")
        documents = item.get("documents")
        if not isinstance(digest, str) or not isinstance(documents, list):
            continue
        kept[str(entry_id)] = {
            "hash": digest,
            "documents": [str(path) for path in documents if isinstance(path, str)],
        }
    return kept


def _save_asked(base_id: str, held: dict) -> None:
    kept = {
        entry_id: item for entry_id, item in held.items() if item.get("documents")
    }
    atomic_write_json(_asked_path(base_id), {"schema": 1, "asked": kept})


def _inside_the_base(base_root: str, full: str) -> bool:
    """Whether the folder a file goes in really sits inside the base."""
    root = os.path.realpath(base_root)
    folder = os.path.realpath(os.path.dirname(full))
    return folder == root or folder.startswith(root + os.sep)


def is_a_map(base_root: str, relative: str) -> bool:
    """Whether a context file is a map, by what it says it is, wherever it sits.

    A map that was moved or renamed is still a map, and nothing about the
    business makes a map wrong, so it is never offered, asked about or
    answered for (Astra's review of 0.3.3, finding 12). `stale.is_map` is the
    one rule, and it is asked here rather than repeated.
    """
    if str(relative) == constants.MAP_PATH:
        return True
    for info in base_reader.context_files(base_root):
        if info.path == relative:
            return stale.is_map(info)
    return False


def _still_what_this_path_writes(base_root: str, entry, text: str, git) -> bool:
    """The kept entry read again as strictly as when it was built.

    The kept entry lives where no file tool may write, and it is read back
    here as though it could have been, so the yes never depends on that alone
    (the security review of 0.3.3).
    """
    if entry.run_id is not None or entry.origin != ORIGIN:
        return False
    if entry.noted_by != (base_reader.repo_email(base_root, git) or ""):
        return False
    if not entry.affects:
        return False
    if any(is_a_map(base_root, path) for path in entry.affects):
        return False
    allowlist, _code = scan.load_allowlist(base_root)
    try:
        _screened_whole(text, entry.noted_by, allowlist)
    except Refused:
        return False
    return True


def _blob_of(base_root: str, text: str, git: GitRunner) -> str:
    """The identifier git gives these exact bytes, with no filter in the way."""
    return git.run(
        ["hash-object", "--no-filters", "--stdin"], cwd=base_root, input=text
    ).out()


def _staged_blob(base_root: str, relative: str, git: GitRunner) -> Optional[str]:
    """What is lined up to be saved at one path, or None when nothing is."""
    found = git.run(["ls-files", "-s", "-z", "--", relative], cwd=base_root)
    if not found.ok:
        return "unknown"
    for record in nul_fields(found.stdout):
        meta, _tab, _name = record.partition("\t")
        parts = meta.split()
        if len(parts) >= 2:
            return parts[1]
    return None


def _saved_in_head(base_root: str, relative: str, text: str, git: GitRunner) -> bool:
    """Whether the newest saved change holds exactly this entry at this path."""
    found = git.run(["cat-file", "blob", "HEAD:" + relative], cwd=base_root)
    return found.ok and found.stdout == text


def _write_all(handle: int, data: bytes) -> None:
    """Every byte into one open file, or an error; never a quiet part of them."""
    written = 0
    while written < len(data):
        written += os.write(handle, data[written:])


def _publish(full: str, text: str) -> Tuple[int, int]:
    """Write the entry whole, then put it in place without writing over anything.

    The words go into a file of their own that nothing else can have, and only
    a file that was written to the end is linked into place, which fails
    rather than replaces when a file of that name is already there. So a
    write that stops halfway never leaves a partial entry where the entry
    goes (Astra's review of 0.3.3, finding 9). What comes back is the placed
    file's identity, which is how the rollback knows the file is still ours.
    """
    folder = os.path.dirname(full)
    temporary = os.path.join(
        folder, ".%s.%s.writing" % (os.path.basename(full), secrets.token_hex(6))
    )
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        try:
            _write_all(handle, text.encode("utf-8"))
            os.fsync(handle)
        finally:
            os.close(handle)
        os.link(temporary, full)
        info = os.lstat(full)
        return info.st_dev, info.st_ino
    finally:
        try:
            os.unlink(temporary)
        except OSError:
            pass


def _take_it_back(
    base_root: str, relative: str, text: str, identity, blob: str, git: GitRunner
) -> bool:
    """Undo only what this run wrote, and say whether all of it was undone.

    The file is taken away only while it is still the file this run placed,
    holding exactly what it wrote, and the line-up to be saved is cleared
    only while it still holds exactly that. Anything another window put there
    since is left exactly as it is (Astra's review of 0.3.3, finding 7).
    """
    whole = True
    staged = _staged_blob(base_root, relative, git)
    if staged is not None:
        if staged == blob:
            if not git.run(
                ["rm", "-q", "--cached", "--", relative], cwd=base_root
            ).ok:
                whole = False
        else:
            whole = False
    full = os.path.join(base_root, relative.replace("/", os.sep))
    try:
        info = os.lstat(full)
    except OSError:
        return whole
    same_file = (info.st_dev, info.st_ino) == tuple(identity)
    if not same_file or read_text(full) != text:
        return False
    try:
        os.unlink(full)
    except OSError:
        return False
    return whole


def record(
    base_root: str,
    base_id: str,
    shown: str,
    today: Optional[datetime.date] = None,
    runner: Optional[GitRunner] = None,
) -> Recorded:
    """Write the context change that was shown, on the person's yes.

    The yes is bound to what was shown and to the revision the base was on.
    Anything that moved since then stops it, and the change is shown again
    rather than written. Success is claimed only once the newest saved change
    is seen to hold exactly the entry that was approved (Astra's review of
    0.3.3, finding 8).
    """
    git = runner_or_default(runner)
    day = today or state.today()
    refuse_a_shared_copy(base_root, runner=git)
    waiting = _waiting(base_id)
    if waiting is None:
        raise _refuse(NOTHING_WAITING, CODE_NOTHING_WAITING)
    if str(shown or "") != waiting["shown"]:
        raise _refuse(NOT_WHAT_WAS_SHOWN, CODE_NOT_WHAT_WAS_SHOWN)
    text = waiting["text"]
    try:
        entry = formats.ChangeEntry.parse(text).validate(day)
        for path in entry.affects:
            if paths.canonical_context_path(base_root, path) != path:
                raise PathError("moved", code=CODE_MOVED_ON)
    except (ValidationError, PathError):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    before = _head(base_root, git)
    if not before or waiting.get("head") != before:
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    if not _still_what_this_path_writes(base_root, entry, text, git):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    if _named_anywhere(base_root, entry.id):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    # Before anything is written: the base must not name a program for git to
    # run on its files when they are saved (Astra's review of 0.3.3, finding
    # 1). Every command the runner runs refuses one anyway; asking first means
    # the refusal says what it is about and nothing is left half done.
    if gitcmd.executable_drivers(base_root):
        raise _refuse(RUNS_A_PROGRAM, CODE_RUNS_A_PROGRAM)

    try:
        review.ready_to_write(base_root, git)
    except GtmBaseError as refusal:
        if refusal.code == review.CODE_NOT_DEFAULT_BRANCH:
            raise _refuse(NOT_ON_MAIN, CODE_NOT_ON_MAIN)
        said = unsaved.where_sentence(unsaved.look(base_root, git).paths(), base_root)
        if said:
            raise _refuse(UNSAVED_NAMED % said, CODE_UNSAVED)
        raise _refuse(UNSAVED, CODE_UNSAVED)

    # Where the closing writes one: the folder every change is written to
    # today, on either layout, so one identifier never names two files.
    relative = base_reader.where_to_write_the_entry(base_root, entry.id)
    full = os.path.join(base_root, relative.replace("/", os.sep))
    if os.path.lexists(full):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    folder = os.path.dirname(full)
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
    except OSError:
        raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)
    if not _inside_the_base(base_root, full):
        # A folder of changes that leads out of the base through a link is
        # never written through.
        raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)
    blob = _blob_of(base_root, text, git)
    if not blob:
        raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)
    try:
        identity = _publish(full, text)
    except FileExistsError:
        # Somebody else's file arrived in between. It is left exactly as it is.
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    except OSError:
        raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)
    try:
        git.check(["add", "--", relative], cwd=base_root)
        git.check(
            ["commit", "-q", "-m", SAVE_MESSAGE, "--", relative], cwd=base_root
        )
    except (GtmBaseError, OSError):
        # Whatever the command said, what counts is what was saved.
        pass
    after = _head(base_root, git)
    if not (after and after != before and _saved_in_head(base_root, relative, text, git)):
        if _take_it_back(base_root, relative, text, identity, blob, git):
            raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)
        raise _refuse(NOT_ALL_TAKEN_BACK, CODE_NOT_ALL_TAKEN_BACK)

    forget_showing(base_id)
    try:
        _count_one_more()
    except (GtmBaseError, OSError):
        # The change is written. A count that could not be kept only means
        # the whole explanation is given once more than it had to be.
        pass
    try:
        plan = join_flow.reconcile_plan(
            base_root,
            base_id,
            entry.affects,
            today=day,
            runner=git,
            every_document=True,
            ask_only=lambda path: can_be_asked_about(path)
            and not is_a_map(base_root, path),
        )
    except (GtmBaseError, OSError):
        # The change is written. Every document it affects stays flagged,
        # which is what the review then picks up.
        plan = join_flow.Reconciliation([], list(entry.affects))
    try:
        with _locked(base_id):
            held = _asked(base_id)
            held[entry.id] = {
                "hash": ids.content_hash(text),
                "documents": list(plan.ask_about),
            }
            _save_asked(base_id, held)
    except (GtmBaseError, OSError):
        plan = join_flow.Reconciliation([], list(entry.affects))
    return Recorded(entry, relative, plan)


# --- Step 5: one answer about one document -----------------------------------


def answer(
    base_root: str,
    base_id: str,
    entry_id: str,
    document: str,
    given: str,
    now=None,
    runner: Optional[GitRunner] = None,
) -> "join_flow.Reconciled":
    """Record one answer about one document this change affects.

    Yes and no are the closing's own, run over every document a change
    recorded this way affects. Not now writes nothing, so the document stays
    flagged exactly as a closing change left unanswered does.

    Only a question the yes asked is answered, about the change exactly as it
    was written then, and only once. Checking the question, answering it and
    taking it off the list happen under one lock.
    """
    git = runner_or_default(runner)
    if given not in ANSWERS:
        raise _refuse(ANSWER_UNKNOWN, CODE_BAD_ANSWER)
    relative = moment.context_path_of(base_root, document)
    if relative is None or is_a_map(base_root, relative):
        raise _refuse(moment.NOT_A_CONTEXT_FILE, CODE_NOT_A_DOCUMENT)
    with _locked(base_id):
        held = _asked(base_id)
        asked = held.get(str(entry_id))
        if not asked or relative not in asked["documents"]:
            raise _refuse(NOT_ASKED, CODE_NOT_ASKED)
        # The change has to be exactly what it was when the question was
        # asked. One changed in another window since is a different change,
        # and a yes about the first must not settle the second (Astra's
        # review of 0.3.3, finding 6).
        _where, text = base_reader.entry_path_and_text(base_root, str(entry_id))
        if text is None or ids.content_hash(text) != asked["hash"]:
            raise _refuse(CHANGE_CHANGED, CODE_CHANGE_CHANGED)
        try:
            entry = formats.ChangeEntry.parse(text)
        except (ValidationError, PathError):
            raise _refuse(CHANGE_CHANGED, CODE_CHANGE_CHANGED)
        if (
            relative not in list(entry.affects)
            or entry.origin != ORIGIN
            or entry.run_id is not None
        ):
            raise _refuse(NOT_ASKED, CODE_NOT_ASKED)
        named = safe_name(relative)
        if given == ANSWER_NOT_NOW:
            result = join_flow.Reconciled(
                relative, False, LEFT_FLAGGED % _capital(named)
            )
        elif given == ANSWER_YES:
            result = join_flow.reconcile_yes(
                base_root, base_id, relative, str(entry_id), now=now, runner=git,
                any_document=True,
            )
            if not result.answered_yes:
                # A refused yes can be given again once what stood in the way
                # is dealt with, so the question stays open.
                return result
        else:
            result = join_flow.reconcile_no(
                base_root, base_id, relative, str(entry_id), now=now, runner=git
            )
        asked["documents"] = [
            path for path in asked["documents"] if path != relative
        ]
        held[str(entry_id)] = asked
        _save_asked(base_id, held)
        return result


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text
