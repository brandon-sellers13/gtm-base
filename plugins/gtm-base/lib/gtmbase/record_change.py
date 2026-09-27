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

import datetime
import os
from typing import List, Optional, Sequence, Tuple

from . import (
    base_reader,
    compose_proposal,
    confirm,
    constants,
    formats,
    ids,
    join_flow,
    moment,
    names,
    paths,
    review,
    scan,
    state,
    unsaved,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_json, read_json, read_text, remove
from .gitcmd import GitRunner, runner_or_default

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

# Most characters any one of the three answers may hold. A person answering in
# a sentence or two writes far less than this.
WORDS_CHARS = constants.MAX_EXCERPT_CHARS

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
        if path == constants.MAP_PATH:
            continue
        if any(mark in path for mark in (",", "[", "]")):
            continue
        try:
            if paths.canonical_context_path(base_root, path) != path:
                continue
        except (PathError, ValidationError):
            continue
        try:
            name = names.document_name(path)
        except ValueError:
            continue
        found.append((len(found) + 1, path, name))
    return found


def chosen_documents(base_root: str, numbers: Sequence[str]) -> List[str]:
    """The documents the person named, by the numbers on the list."""
    listed = documents(base_root)
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
    behind in the confirmation lines that named it, and a new change under
    that name would inherit every one of them, settling documents nobody was
    asked about. So a name any confirmation line still carries is taken too.
    """
    relative, _text = base_reader.entry_path_and_text(base_root, entry_id)
    if relative is not None:
        return True
    folder = os.path.join(base_root, constants.CONFIRMATIONS_DIR.replace("/", os.sep))
    try:
        listed = sorted(os.listdir(folder))
    except OSError:
        return False
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
    # The whole entry through the closing's own screen, as it will be written,
    # with the base's address let through on the line that carries it.
    codes = review.screen(
        _ScreenedDraft(text), address
    )
    if codes:
        raise _refuse(SCREENED_NEXT, CODE_SCREENED)
    return entry


class _ScreenedDraft(object):
    """The shape `review.screen` reads: a document with a settings block."""

    __slots__ = ("text",)

    def __init__(self, text: str):
        self.text = text


def why_when_none(entry) -> str:
    """What the four lines say for why when the person gave no reason.

    It is the sentence the moment of use says about the same change, so the
    preview and the flag never disagree about one change.
    """
    return moment._why_of(entry)


class Shown(object):
    """One context change as it was shown, and the value the yes is bound to."""

    __slots__ = ("entry", "text", "shown", "proposed")

    def __init__(self, entry, text, shown, proposed):
        self.entry = entry
        self.text = text
        self.shown = shown
        self.proposed = proposed


def _waiting_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), WAITING_FILE)


def shown_value(text: str) -> str:
    return ids.content_hash(text)[:16]


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
    """Show the whole context change, and keep it for the yes. Writes nothing.

    Nothing goes into the base here. The one thing kept is the entry as shown,
    in this seat's own folder, so the yes writes exactly those words.
    """
    git = runner_or_default(runner)
    day = today or state.today()
    refuse_a_shared_copy(base_root, runner=git)
    affects = chosen_documents(base_root, numbers)
    entry = build_entry(
        base_root, what, why, source, affects, day, happened_on, runner=git
    )
    text = entry.render()
    proposed = join_flow.show_entry(text, why_when_none(entry))
    shown = shown_value(text)
    atomic_write_json(
        _waiting_path(base_id),
        {"schema": 1, "text": text, "shown": shown, "day": day.isoformat()},
    )
    return Shown(entry, text, shown, proposed)


def leave(base_id: str) -> str:
    """Leave it: nothing is written, and the change shown is let go."""
    remove(_waiting_path(base_id))
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


def _take_it_back(base_root: str, relative: str, git: GitRunner) -> None:
    """Put the base back the way it was when the save did not go through."""
    git.run(["reset", "-q", "HEAD", "--", relative], cwd=base_root)
    remove(os.path.join(base_root, relative.replace("/", os.sep)))


def record(
    base_root: str,
    base_id: str,
    shown: str,
    today: Optional[datetime.date] = None,
    runner: Optional[GitRunner] = None,
) -> Recorded:
    """Write the context change that was shown, on the person's yes.

    The yes is bound to what was shown. Anything that moved since then, the
    change kept for the yes or the identifier it was given, stops it, and the
    change is shown again rather than written.
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
            paths.canonical_context_path(base_root, path)
    except (ValidationError, PathError):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)
    if entry.run_id is not None or _named_anywhere(base_root, entry.id):
        raise _refuse(MOVED_ON, CODE_MOVED_ON)

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
    try:
        folder = os.path.dirname(full)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(full, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        git.check(["add", "--", relative], cwd=base_root)
        git.check(
            ["commit", "-q", "-m", SAVE_MESSAGE, "--", relative], cwd=base_root
        )
    except (GtmBaseError, OSError):
        _take_it_back(base_root, relative, git)
        raise _refuse(COULD_NOT_SAVE, CODE_COULD_NOT_SAVE)

    remove(_waiting_path(base_id))
    try:
        _count_one_more()
    except (GtmBaseError, OSError):
        # The change is written. A count that could not be kept only means
        # the whole explanation is given once more than it had to be.
        pass
    plan = join_flow.reconcile_plan(
        base_root, base_id, entry.affects, today=day, runner=git, every_document=True
    )
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
    """
    git = runner_or_default(runner)
    if given not in ANSWERS:
        raise _refuse(ANSWER_UNKNOWN, CODE_BAD_ANSWER)
    relative = moment.context_path_of(base_root, document)
    if relative is None or relative == constants.MAP_PATH:
        raise _refuse(moment.NOT_A_CONTEXT_FILE, CODE_NOT_A_DOCUMENT)
    named = names.document_name(relative)
    day = now or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    entry, _file = join_flow.entry_in_base(base_root, base_id, entry_id, day)
    if entry is None:
        raise _refuse(
            confirm.CHANGE_NOT_IN_THE_BASE % named, confirm.CODE_ENTRY_MISSING
        )
    if relative not in list(entry.affects):
        raise _refuse(
            confirm.CHANGE_IS_NOT_ABOUT_IT % named, confirm.CODE_NOT_ABOUT_THIS_FILE
        )
    if given == ANSWER_NOT_NOW:
        return join_flow.Reconciled(relative, False, LEFT_FLAGGED % _capital(named))
    if given == ANSWER_YES:
        return join_flow.reconcile_yes(
            base_root, base_id, relative, entry_id, now=now, runner=git,
            any_document=True,
        )
    return join_flow.reconcile_no(
        base_root, base_id, relative, entry_id, now=now, runner=git
    )


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text
