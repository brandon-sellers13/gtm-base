"""Moving a base from the older folder of entries to `work/changes`.

A base set up before the rename keeps its entries in `work/decisions`, with
each one calling itself a decision and carrying `decided_on` and `decided_by`.
A base set up today keeps them in `work/changes`, with each one calling itself
a change and carrying `happened_on` and `noted_by`. Both are read everywhere,
by `base_reader.ledger` and by the parser in `formats`, so nothing here has to
run for a base to work. What this does is finish the move, once, on a base its
owner has said yes to.

It is written as a recorded transaction, for the reason every write in this
library is: a run can stop in the middle, and the state it stops in has to be
one the next run can finish or put back rather than one a person has to unpick
by hand. The same note this module writes is the one `approve_local` writes for
a local approval, in the same folder and checked the same way: the identifier
of the run, the base it is about, where the base stood before anything was
written, and a hash of every path this run was going to write.

The order is fixed:

1. Read both folders, exactly as the bytes really are. Check that every entry
   parses, that renaming its settings would change nothing but the names, that
   no identifier sits in both folders saying two different things, and that
   every file is named after the change inside it. Anything else is refused by
   name and nothing is written.
2. Refuse on a tree the person has edits sitting in, apart from edits this
   module's own unfinished run left, which are dealt with first.
3. Write the note, recording where the base stood, what each path will hold,
   where each file came from and what it said there, and what this run will
   take away outright.
4. Save change one: the files move, the older copies of entries the newer
   folder already holds are taken away, and not one character of any file
   changes. A later look at which saved change first added a file follows it
   through a move, and `report.py` counts a catch by that look.
5. Save change two, the rename of the settings in each file. This is the
   commit point.
6. Write the dated record in `corrections/`, in the shape `report.py` reads.
7. Take the note away.

Two rules hold over all of it.

Nothing is ever written to a base in a form the reader cannot read back to
exactly the values it read before. The rename is checked against itself before
anything moves, so a file it cannot handle is a sentence naming that file
rather than a saved change nothing can read.

No recovery deletes a file unless another readable copy of that same change is
confirmed to be somewhere else at that moment. A later run that finds a note
decides by what was saved. Nothing saved means nothing landed, so what this run
wrote and did not save is put back, what it took away is brought back, and only
then does the note go. Anything saved means the move has landed, and a base
whose files have moved without being renamed is one every reader here already
reads, so the run finishes what is left rather than unpicking what is done.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Dict, List, Optional, Tuple

from . import base_reader, compose_proposal, constants, formats, ids, paths, state
from .errors import GitError, PathError, ValidationError
from .fsutil import (
    atomic_write_json,
    atomic_write_text,
    read_json,
    read_text,
    read_text_exactly,
    remove,
)
from .gitcmd import GitRunner, runner_or_default, status_entries
from .validate import marker_line

# The note this module leaves in the seat's own folder while it is working.
# What this seat remembers about being asked, so it is asked once.
SEAT_PUT_OFF_KEY = "changes_move_put_off_until"
JOURNAL_FILE = "changes-migration.json"
JOURNAL_SCHEMA = 1

# The notes saved with each of the three pieces of work, in the order they are
# saved. They are matched against what landed, so they never change casually.
MOVE_SUBJECT = constants.MOVE_TO_CHANGES_SUBJECT
REWRITE_SUBJECT = "Write each context change under its plainer setting names"
RECORD_SUBJECT = "Record the move to work/changes"

# What one run can end as.
STATUS_NOT_NEEDED = "not-needed"
STATUS_MIGRATED = "migrated"
STATUS_REFUSED = "refused"
STATUS_RESUMED = "resumed"
STATUS_UNDONE = "undone"

# Why a run refused. None of these is shown to a person as it is.
CODE_UNREADABLE_ENTRY = "a-change-could-not-be-read"
CODE_IN_BOTH_FOLDERS = base_reader.CODE_IN_BOTH_FOLDERS
CODE_UNSAVED_EDITS = "unsaved-edits"
CODE_NOT_DEFAULT_BRANCH = "not-the-shared-line-of-work"
CODE_GIT_FAILED = "git-failed"
CODE_NOTE_UNREADABLE = "note-of-unfinished-work-unreadable"
CODE_DESTINATION_TAKEN = "a-file-of-that-name-is-already-there"
CODE_CANNOT_READ_HISTORY = "cannot-read-what-was-saved"
CODE_TWICE_IN_ONE_FOLDER = base_reader.CODE_TWICE_IN_ONE_FOLDER
CODE_EVERY_SEAT_FIRST = "every-seat-updates-first"
CODE_CANNOT_FINISH = "cannot-finish-the-unfinished-update"
CODE_NAME_IS_NOT_THE_ID = base_reader.CODE_NAME_IS_NOT_THE_ID
CODE_CANNOT_PUT_BACK = "cannot-put-back-what-was-moved"

# --- The sentences a person reads -------------------------------------------

OFFER = (
    "Your context changes are stored the old way. Updating them takes one step "
    "and changes nothing they say. Shall I do it?"
)
# Said instead of the offer on a base other people can reach. Everyone who
# opens it has to be on this release first, because an older one reads an
# updated base as though it held nothing at all.
EVERY_SEAT_FIRST = (
    "Your context changes are stored the old way, and updating them is one "
    "step. Everyone who opens this base has to be on the current version of "
    "GTM Base first, because an older one would read the updated base as "
    "empty. Tell me once that is true and I will do it."
)
CANNOT_FINISH = (
    "An earlier update stopped partway and GTM Base can no longer read %s, so "
    "it cannot finish on its own and has touched nothing. Put that file back "
    "as it was and ask again, or tell me to give up on the unfinished update "
    "and I will put back what I still recognise and leave the rest alone."
)
GAVE_UP = (
    "The unfinished update was given up on and your base is as it was."
)
# Said when part of the update was already saved. Putting that back would be
# undoing something the base has already recorded, so it is left where it is
# and the truth about it is said instead.
#
# It names no setting and no folder, because how far the update got before it
# stopped is not the same every time, and a sentence that says which half is
# done is a sentence that is wrong half the time.
GAVE_UP_HALF_DONE = (
    "The unfinished update was given up on. Whatever it had already saved is "
    "kept, so your base is half updated and everything reads exactly as it "
    "read before. Ask for the update again whenever you like and it will "
    "finish whatever is left."
)
GAVE_UP_COULD_NOT = (
    "GTM Base could not put back what the unfinished update had done, so it "
    "changed nothing and kept its note. Ask again in a moment."
)
GAVE_UP_NOTE_UNREADABLE = (
    "GTM Base left a note about unfinished work here and cannot read it, so it "
    "has touched nothing and kept the note. Nothing of yours was changed."
)
# What a look only says. It says what a real run would do and stops there.
# It says how many context changes, in words, and never which ones by their
# identifiers: a person reads this, and an identifier is a name only GTM Base
# uses (finding 4 of the release A live check).
WOULD_MOVE = (
    "This would update %s of your context changes and write one dated record "
    "of it under today's date, %s. It would be saved as two separate pieces "
    "of work. Nothing has been written."
)
# How many, the way a person says it, up to the point a person would say the
# number itself instead.
COUNT_WORDS = (
    "no",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)
WOULD_NOT = "This would not run right now. %s Nothing has been written."
PUT_OFF = (
    "GTM Base will not offer to update how your context changes are stored "
    "again until %s."
)
# What a read-only look says about whether the offer would be made at all.
OFFER_STATE_NOW = "As things stand, GTM Base would offer this."
OFFER_STATE_EVERY_SEAT_FIRST = (
    "As things stand, GTM Base would not offer this. It would tell you "
    "instead that everyone who opens this base has to be on the current "
    "version first."
)
OFFER_STATE_NONE = (
    "As things stand, GTM Base would not offer this at all."
)
WOULD_FINISH = (
    "An earlier update stopped partway and this would pick it up where it "
    "stopped. Nothing has been written."
)
GAVE_UP_LEFT_ALONE = (
    "The unfinished update was given up on. Your base is as it was apart from "
    "%s, which holds words of your own and was left exactly as you left it."
)
# The dated record the move leaves behind. It is here with the other
# sentences rather than built where it is written, so it is checked by the
# same test every other sentence a person reads is checked by.
RECORD_WHAT_CHANGED = (
    "Before: the context changes were stored the older way, in their own "
    "folder and under their older setting names.\n\nAfter: they are stored "
    "the way GTM Base stores them today, and every one of them says exactly "
    "what it said before. The changes moved: %s."
)
RECORD_WHY = (
    "The word for what this base tracks is a context change, because what "
    "makes a document wrong is often nothing anybody chose. The folder and "
    "the settings inside each file now say the same words the rest of GTM "
    "Base says."
)
# It names no folder, because the skills tell the assistant to say this back
# as it is and never to read a path out to anybody.
MIGRATED = (
    "Your context changes are now stored the way GTM Base stores them today, "
    "and all %d of them say exactly what they said before."
)
NOTHING_TO_MOVE = "Your context changes are already where they belong."
UNREADABLE_ENTRY = (
    "GTM Base could not read %s, so nothing was moved. Have a look at that "
    "file and ask again."
)
NAME_IS_NOT_THE_ID = (
    "The file %s says it is the context change %s, which is not what it is "
    "called, so nothing was moved. Two files could end up with one identifier. "
    "Rename it to match and ask again."
)
SAME_CHANGE_TWICE = (
    "The context change %s is written in both folders and the two do not say "
    "the same thing, so nothing was moved. Decide which one is right, take the "
    "other one away, and ask again."
)
TWICE_IN_ONE_FOLDER = (
    "Two files say they are the context change %s, %s and %s, and they do not "
    "say the same thing, so nothing was moved. Decide which one is right, take "
    "the other one away, and ask again."
)
DESTINATION_TAKEN = (
    "There is already a file called %s where the older one would go, so "
    "nothing was moved."
)
UNSAVED_EDITS = (
    "You have unsaved edits in your base, so nothing was moved. Deal with "
    "those first and ask again."
)
NOT_ON_MAIN = (
    "Your base is on a line of work the team does not share, so nothing was "
    "moved."
)
COULD_NOT_SAVE = (
    "GTM Base could not finish saving the move, so it stopped and left your "
    "base as it was."
)
# The same, for the case where putting it back did not work either. It says
# less, because less is true.
COULD_NOT_SAVE_LEFT_HALF_DONE = (
    "GTM Base could not finish the update and could not put back what it had "
    "already done, so it stopped and kept its note. Nothing of yours was "
    "changed. Ask again in a moment."
)
NOTE_UNREADABLE = (
    "GTM Base left a note about unfinished work here and cannot read it, so "
    "nothing was moved. Nothing of yours was touched."
)
PUT_BACK = (
    "An earlier run of this stopped partway, so it was put back and your base "
    "is as it was. Ask again whenever you like."
)
# Said whenever a path this run would otherwise touch holds something it did
# not write. It names the document, because a person told only that something
# is unsaved has to go looking for it themselves.
THEIR_WORDS = (
    "There are words in %s that you have not saved, so nothing was moved and "
    "nothing was touched. Deal with that file first and ask again."
)
CANNOT_READ_HISTORY = (
    "GTM Base could not read what your base has already saved, so it stopped "
    "and touched nothing. Ask again in a moment."
)
# Said when putting something back would be the only way to keep a change and
# there is nothing to put back from. Nothing is deleted in that state.
CANNOT_PUT_BACK = (
    "An earlier update moved %s, and that file is not in anything your base "
    "has saved, so GTM Base cannot put it back and will not take away the "
    "copy it made. Nothing was touched. Save your base and ask again, or tell "
    "me to give up on the unfinished update and I will put back what I still "
    "recognise and leave the rest alone."
)


class Result(object):
    """What one run of the migration did, and the one thing it has to say."""

    __slots__ = ("status", "code", "sentence", "moved", "entry_ids", "codes")

    def __init__(self, status, code=None, sentence="", moved=None, entry_ids=None):
        self.status = status
        self.code = code
        self.sentence = sentence
        self.moved = list(moved or [])
        self.entry_ids = list(entry_ids or [])
        self.codes: List[str] = []

    @property
    def ok(self) -> bool:
        return self.status in (
            STATUS_MIGRATED,
            STATUS_NOT_NEEDED,
            STATUS_RESUMED,
            STATUS_UNDONE,
        )

    def __repr__(self) -> str:
        return "Result(%r, %r)" % (self.status, self.code)


def _refused(code: str, sentence: str) -> Result:
    return Result(STATUS_REFUSED, code, sentence)


# --- What is there ------------------------------------------------------------


def _folder(base_root: str, name: str) -> str:
    return os.path.join(base_root, name.replace("/", os.sep))


def real_name_of(base_root: str, name: str) -> str:
    """One folder's path spelled the way the disk really spells it.

    Most Macs do not tell two spellings of one folder name apart, so a base
    whose folder was made as `work/Decisions` is the same folder to every
    read. Git is not so forgiving: it holds the name it was given, and a move
    that names the other spelling fails. Everything that hands a path to git
    asks for the real one first.
    """
    parent, _slash, wanted = name.rpartition("/")
    where = os.path.join(base_root, parent.replace("/", os.sep)) if parent else base_root
    try:
        here = os.listdir(where)
    except OSError:
        return name
    if wanted in here:
        return name
    for found in sorted(here):
        if found.lower() == wanted.lower():
            return (parent + "/" + found) if parent else found
    return name


def _entry_files(base_root: str, name: str) -> List[str]:
    """The names of every entry file in one folder, in a fixed order."""
    folder = _folder(base_root, name)
    if not os.path.isdir(folder):
        return []
    return sorted(
        item for item in os.listdir(folder) if item.endswith(".md")
    )


def _still_older_inside(base_root: str) -> bool:
    """Whether any entry in the newer folder still carries the older words.

    A base whose files were moved and never rewritten is half updated. It
    reads exactly as it always did, so nothing is broken, but there is still
    work to finish and something has to notice that there is.
    """
    folder = _folder(base_root, constants.CHANGES_DIR)
    for name in _entry_files(base_root, constants.CHANGES_DIR):
        text = read_text_exactly(os.path.join(folder, name))
        if text is None:
            continue
        try:
            block, _body = formats.split_document(text)
            fields = formats.parse_frontmatter(block)
        except (ValidationError, PathError):
            continue
        if any(old in fields for _new, old in constants.ENTRY_FIELD_PAIRS):
            return True
        said = str(fields.get("kind", "")).strip().strip("\"'")
        if said == constants.LEGACY_ENTRY_KIND:
            return True
    return False


def needed(base_root: str) -> bool:
    """Whether anything about how this base stores its changes is unfinished.

    Two things count. An entry still in the older folder, which is one
    listing of one folder. And an entry already moved whose settings were
    never rewritten, which is the state a run that stopped between its two
    saved pieces of work leaves behind. Only the second opens any file, and
    only when the newer folder exists at all.
    """
    if _entry_files(base_root, constants.LEGACY_CHANGES_DIR):
        return True
    return _still_older_inside(base_root)


# What the offer should say, worked out before it is made.
OFFER_NONE = "none"
OFFER_NOW = "now"
OFFER_EVERY_SEAT_FIRST = "every-seat-first"


def what_to_offer(
    base_root: str,
    base_id: str,
    today: Optional[datetime.date] = None,
    git: Optional[GitRunner] = None,
) -> str:
    """Whether to offer the move, and which of the two offers to make.

    An offer that would be refused the moment somebody said yes is not an
    offer, so the same checks the move runs are run here first, read-only.
    A base with something written down twice, a base with unsaved edits, a
    base on another line of work, and a base whose owner has already said not
    now are all reasons to say nothing about it this time.
    """
    if not needed(base_root):
        return OFFER_NONE
    if _put_off_until(base_id, today or state.today()):
        return OFFER_NONE
    runner = runner_or_default(git)
    if _ready_to_write(base_root, runner) is not None:
        return OFFER_NONE
    _found, refused = _prevalidate(base_root)
    if refused is not None:
        return OFFER_NONE
    if paths.remote_url(base_root, runner=runner) is not None:
        return OFFER_EVERY_SEAT_FIRST
    return OFFER_NOW


def _put_off_until(base_id: str, today: datetime.date) -> bool:
    """Whether the owner has said not now and the window has not passed."""
    seat, _problems = state.load_seat(base_id)
    until = _as_date(str(seat.get(SEAT_PUT_OFF_KEY) or ""))
    return until is not None and today < until


def not_now(base_id: str, today: Optional[datetime.date] = None, days: int = None):
    """Record that the owner does not want to be asked about this yet.

    It comes back after the same window a set-aside document comes back
    after, because it is the same kind of answer: not no, just not now.
    """
    day = today or state.today()
    window = (
        constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS if days is None else days
    )
    until = day + datetime.timedelta(days=window)
    state.update_seat(base_id, **{SEAT_PUT_OFF_KEY: until.isoformat()})
    return until


# --- Checking before anything is written --------------------------------------


class _Survey(object):
    """Every entry both folders hold, read once, with what is wrong with it."""

    __slots__ = ("old", "new", "problems", "twice", "misnamed")

    def __init__(self):
        # Each is {entry id: (file name, the entry, what it says as values)}.
        self.old: Dict[str, Tuple[str, object, tuple]] = {}
        self.new: Dict[str, Tuple[str, object, tuple]] = {}
        self.problems: List[Tuple[str, str]] = []
        # (entry id, one file name, the other) for an identifier two files in
        # one folder both claim while saying different things.
        self.twice: List[Tuple[str, str, str]] = []
        # (path, the identifier inside it) for a file named after something
        # other than the change it holds.
        self.misnamed: List[Tuple[str, str]] = []


def _survey(base_root: str) -> "_Survey":
    found = _Survey()
    for folder_name, into in (
        (constants.LEGACY_CHANGES_DIR, found.old),
        (constants.CHANGES_DIR, found.new),
    ):
        for name in _entry_files(base_root, folder_name):
            relative = folder_name + "/" + name
            # Read exactly, because these are the bytes the rename will work
            # on. Reading the ordinary way translates line endings, which is
            # how a file the rename could not handle used to pass the survey
            # and then fail with the move already underway.
            text = read_text_exactly(
                os.path.join(_folder(base_root, folder_name), name)
            )
            if text is None:
                found.problems.append((relative, "unreadable"))
                continue
            try:
                entry = formats.ChangeEntry.parse(text)
            except (ValidationError, PathError) as failure:
                found.problems.append((relative, failure.code))
                continue
            try:
                # The invariant, run here so that a file the rename cannot
                # handle is a named refusal before one thing has been written
                # to the base, and never a saved file nothing can read.
                formats.rewritten_safely(text)
            except (ValidationError, PathError) as failure:
                found.problems.append((relative, failure.code))
                continue
            if name != entry.id + ".md":
                found.misnamed.append((relative, entry.id))
                continue
            said = base_reader._what_it_says(entry)
            held = into.get(entry.id)
            if held is not None:
                if held[2] != said:
                    found.twice.append((entry.id, held[0], name))
                continue
            into[entry.id] = (name, entry, said)
    return found


def _prevalidate(base_root: str) -> Tuple[Optional["_Survey"], Optional[Result]]:
    """Read everything first, and refuse before a single file is touched.

    Two things stop a move. A file that cannot be read at all, because moving
    a file nobody can read is moving a problem somewhere new. And one
    identifier written in both folders saying two different things, because
    picking one of them is a decision about the person's own words that
    nothing here is entitled to make.
    """
    found = _survey(base_root)
    if found.problems:
        relative, _code = found.problems[0]
        return None, _refused(CODE_UNREADABLE_ENTRY, UNREADABLE_ENTRY % relative)
    if found.twice:
        entry_id, one, other = sorted(found.twice)[0]
        return None, _refused(
            CODE_TWICE_IN_ONE_FOLDER, TWICE_IN_ONE_FOLDER % (entry_id, one, other)
        )
    if found.misnamed:
        relative, entry_id = sorted(found.misnamed)[0]
        return None, _refused(
            CODE_NAME_IS_NOT_THE_ID, NAME_IS_NOT_THE_ID % (relative, entry_id)
        )
    for entry_id, (_name, _entry, said) in sorted(found.old.items()):
        held = found.new.get(entry_id)
        if held is not None and held[2] != said:
            return None, _refused(
                CODE_IN_BOTH_FOLDERS, SAME_CHANGE_TWICE % entry_id
            )
    for entry_id, (name, _entry, _said) in sorted(found.old.items()):
        if entry_id in found.new:
            continue
        if os.path.lexists(os.path.join(_folder(base_root, constants.CHANGES_DIR), name)):
            return None, _refused(
                CODE_DESTINATION_TAKEN,
                DESTINATION_TAKEN % (constants.CHANGES_DIR + "/" + name),
            )
    return found, None


def _to_move(found: "_Survey") -> List[Tuple[str, str, object]]:
    """The entries still sitting only in the older folder, as (id, name, entry).

    An identifier the newer folder already holds is not moved, because there
    is already a file of that name where it would go. The older copy of it is
    taken away instead, which `_to_drop` below lists. The two say the same
    thing, because the check before this refused the case where they do not.
    """
    return [
        (entry_id, name, entry)
        for entry_id, (name, entry, _said) in sorted(found.old.items())
        if entry_id not in found.new
    ]


def _to_drop(found: "_Survey") -> List[str]:
    """The older copies of entries the newer folder already holds, as paths.

    This is the restored-backup case: somebody brought a copy of the base back
    and both folders ended up with the same entry saying the same thing. The
    older copy is taken away in the same saved change as the move, so the base
    ends with one copy of each entry and nothing is lost, because the copy
    that stays says exactly what the one that goes said.
    """
    return [
        constants.LEGACY_CHANGES_DIR + "/" + name
        for entry_id, (name, _entry, _said) in sorted(found.old.items())
        if entry_id in found.new
    ]


# --- The note -----------------------------------------------------------------


def _journal_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), JOURNAL_FILE)


# Where the base stood, written the one way git writes it.
_SAVED_POINT_RE = re.compile(r"^[0-9a-f]{40}$")

# The only folders a path in the note may sit in. The note is only ever about
# files this module writes or moves, and it writes nowhere else.
NOTE_PATH_PREFIXES = (
    constants.CHANGES_DIR + "/",
    constants.CORRECTIONS_DIR + "/",
)


def _inside(base_root: str, relative: str) -> bool:
    """Whether a path still lands inside this base once every link is followed."""
    real_base = os.path.realpath(base_root)
    settled = os.path.realpath(os.path.join(base_root, relative.replace("/", os.sep)))
    return settled == real_base or settled.startswith(real_base + os.sep)


def _checked_journal(base_id: str, base_root: str):
    """The note, with every value in it checked, or the reason it was refused.

    The note is a file on the disk like any other, so nothing in it is
    believed on sight. Every value is checked to the same bar the note behind
    a local approval is held to: the base it is about, the saved point it
    started from written the one way git writes one, a path this module really
    writes for every path it will put back, a path inside the older folder for
    every file it moved, a hash we could have written for each, and every one
    of them still landing inside this base once the links are followed.

    A note that fails any of those is not finished and not put back. The run
    refuses and touches nothing, because a note we cannot read is a run we
    cannot safely take apart.
    """
    payload = read_json(_journal_path(base_id))
    if payload is None:
        return None, None
    if not isinstance(payload, dict) or payload.get("schema") != JOURNAL_SCHEMA:
        return None, "the note is not one we wrote"
    recorded = str(payload.get("base_root") or "")
    if not recorded or os.path.realpath(recorded) != os.path.realpath(base_root):
        return None, "the note is about another base"
    if not _SAVED_POINT_RE.match(str(payload.get("head") or "")):
        return None, "the note does not say where the base stood"

    items = payload.get("paths")
    if not isinstance(items, list) or not items:
        return None, "the note lists no paths"
    for item in items:
        if not isinstance(item, dict):
            return None, "the note holds something that is not a path"
        relative = str(item.get("path") or "")
        try:
            paths.check_repo_path_syntax(relative, NOTE_PATH_PREFIXES)
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        after = item.get("after_move")
        if after is not None:
            try:
                ids.check_content_hash(str(after))
            except (ValueError, TypeError):
                return None, "the note names a value we never write"
        if not _inside(base_root, relative):
            return None, "the note names a path outside this base"

    came_from = payload.get("came_from")
    if came_from is None:
        came_from = []
    if not isinstance(came_from, list):
        return None, "the note lists what it moved in a shape we never write"
    for item in came_from:
        if not isinstance(item, dict):
            return None, "the note holds something that is not a path"
        relative = str(item.get("path") or "")
        # The folder is compared without case, because the disk does not tell
        # two spellings of it apart and the note records the one git holds.
        lowered = relative.lower()
        try:
            paths.check_repo_path_syntax(
                lowered, (constants.LEGACY_CHANGES_DIR + "/",)
            )
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        if not _inside(base_root, relative):
            return None, "the note names a path outside this base"

    removed = payload.get("removed")
    if removed is None:
        removed = []
    if not isinstance(removed, list):
        return None, "the note lists what it removed in a shape we never write"
    for item in removed:
        relative = str(item or "")
        if not relative.lower().startswith(
            constants.LEGACY_CHANGES_DIR + "/"
        ) or not _inside(base_root, relative):
            return None, "the note names a path we never remove"
    return payload, None


def _to_be_removed(base_root: str, dropped: List[str]) -> List[str]:
    """Every path this run will take away, so putting back can bring it back.

    Commit one does two things a later put-back has to know about: it moves
    files, and it removes two kinds of file outright, an older copy of a
    change the newer folder already holds and the placeholder an earlier
    release left behind. A put-back that knew only about the moves left those
    removals staged, and every run after it said the person had unsaved work
    they had never done.
    """
    removing = [real_name_of(base_root, relative) for relative in dropped]
    older = real_name_of(base_root, constants.LEGACY_CHANGES_DIR)
    placeholder = older + "/.gitkeep"
    if os.path.isfile(
        os.path.join(base_root, placeholder.replace("/", os.sep))
    ):
        removing.append(placeholder)
    return removing


def _write_journal(
    base_id: str,
    base_root: str,
    head: str,
    plan: List[dict],
    came_from: List[dict],
    day: datetime.date,
    removed: Optional[List[str]] = None,
) -> None:
    atomic_write_json(
        _journal_path(base_id),
        {
            "schema": JOURNAL_SCHEMA,
            "base_root": os.path.realpath(base_root),
            "head": head,
            "subjects": [MOVE_SUBJECT, REWRITE_SUBJECT, RECORD_SUBJECT],
            "paths": list(plan),
            # Where each file was before the move, and what it said there, so
            # a run that stopped before anything was saved can tell a file it
            # moved away from one the person has edited since.
            "came_from": list(came_from),
            # Paths this run takes away outright. A put-back brings each of
            # them back from what was last saved, because leaving one removed
            # is leaving work nobody did.
            "removed": list(removed or []),
            # The day the run started, so a run picked up on another day
            # writes the same dated record an uninterrupted run would have.
            "day": day.isoformat(),
            "started_at": state.iso_utc(),
        },
    )


def _clear_journal(base_id: str) -> None:
    remove(_journal_path(base_id))


# --- Reading what was saved ---------------------------------------------------


def _head(base_root: str, git: GitRunner) -> str:
    result = git.run(["rev-parse", "HEAD"], cwd=base_root)
    return result.out() if result.ok else ""


def _subjects_since(base_root: str, head: str, git: GitRunner):
    """The notes saved since the base stood where the note says it stood.

    None comes back when the question could not be answered at all. An empty
    list and an unanswered question mean opposite things here: empty says
    nothing landed, which sends the run down the path that puts work back, and
    unanswered says we do not know, which must stop the run instead. Returning
    empty for both is what let a base with a saved move read as a base with
    nothing saved, and then be taken apart.
    """
    found = git.run(["log", "--format=%s", "%s..HEAD" % head], cwd=base_root)
    if not found.ok:
        return None
    return [line.strip() for line in found.stdout.split("\n") if line.strip()]


def _in_head(base_root: str, relative: str, git: GitRunner) -> bool:
    """Whether the base already had this path when it was last saved."""
    return git.run(
        ["cat-file", "-e", "HEAD:" + relative], cwd=base_root
    ).ok


def _head_text(base_root: str, relative: str, git: GitRunner):
    """What the base held at this path when it was last saved, or None."""
    found = git.run(["show", "HEAD:" + relative], cwd=base_root)
    return found.stdout if found.ok else None


def _move_has_landed(base_root: str, journal: dict, git: GitRunner) -> bool:
    """Whether the move this note describes is already saved, by anybody.

    The note records what this run saved, which is how a run knows what it
    did. It cannot record what somebody else did afterwards, and a person who
    finds a staged move sitting in front of them and saves it has done a
    perfectly ordinary thing. So the question is asked of the base rather
    than of the note: is every file this run moved gone from what was last
    saved, and is every copy it made there instead, holding what this run
    wrote? If so the move has landed, whatever it was saved under, and
    finishing is the only sensible thing left to do.
    """
    came_from = journal.get("came_from") or []
    if not came_from:
        return False
    wrote = {}
    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        allowed = {str(item.get("hash"))}
        after = item.get("after_move")
        if after:
            allowed.add(str(after))
        wrote[relative.split("/")[-1]] = allowed
    for item in came_from:
        relative = str(item.get("path"))
        if _in_head(base_root, relative, git):
            return False
        name = relative.split("/")[-1]
        allowed = wrote.get(name)
        if not allowed:
            return False
        landed = _head_text(
            base_root, constants.CHANGES_DIR + "/" + name, git
        )
        if landed is None or ids.exact_hash(landed) not in allowed:
            return False
    return True


# --- Refusing on a tree somebody is working in --------------------------------


def _ready_to_write(base_root: str, git: GitRunner) -> Optional[Result]:
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        return _refused(CODE_NOT_DEFAULT_BRANCH, NOT_ON_MAIN)
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    if status.out():
        return _refused(CODE_UNSAVED_EDITS, UNSAVED_EDITS)
    return None


# --- Putting back what was never saved ----------------------------------------


class _Sorted(object):
    """Every path a recovery would touch, sorted before anything is touched.

    This is the whole of the rule. A run that undoes one path, then discovers
    the next one is the person's, has already changed their base, and the
    first version of this did exactly that: it took one entry away and then
    stopped, leaving that entry in neither folder and a deletion staged.
    """

    __slots__ = ("undo", "restore", "theirs", "unrecoverable")

    def __init__(self):
        # (relative, whether the base already had it when last saved)
        self.undo: List[Tuple[str, bool]] = []
        # Paths the move took away that are still in what was last saved.
        self.restore: List[str] = []
        # Paths holding something this run did not write. Any one of these
        # stops everything.
        self.theirs: List[str] = []
        # Paths the move took away that are not in what was last saved, so
        # nothing can put them back. Each of these stops everything too,
        # because undoing the other half would leave that change nowhere.
        self.unrecoverable: List[str] = []


def _sort_out(base_root: str, journal: dict, git: GitRunner) -> "_Sorted":
    """Work out what each path in the note is, without changing any of them."""
    sorted_out = _Sorted()

    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text_exactly(full)
        if current is None:
            # Never written, or already put back. Either way there is nothing
            # of ours here and nothing of theirs to protect.
            continue
        ours = [str(item.get("hash"))]
        after = item.get("after_move")
        if after:
            ours.append(str(after))
        if ids.exact_hash(current) not in ours:
            sorted_out.theirs.append(relative)
            continue
        sorted_out.undo.append((relative, _in_head(base_root, relative, git)))

    for item in journal.get("came_from") or []:
        relative = str(item.get("path"))
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text_exactly(full)
        if current is None:
            # The move took it away. It is only ours to put back when the base
            # still holds it in what was last saved. A file that is not in
            # what was last saved cannot be put back by anything, and undoing
            # the copy the move made would then leave that change nowhere at
            # all, so it stops the recovery rather than being passed over.
            if _in_head(base_root, relative, git):
                sorted_out.restore.append(relative)
            else:
                sorted_out.unrecoverable.append(relative)
            continue
        if ids.exact_hash(current) != str(item.get("hash")):
            # Still where it was, and changed since. That is their own work on
            # a file this run had not reached yet.
            sorted_out.theirs.append(relative)
    return sorted_out


def _is_an_entry_path(relative: str) -> bool:
    """Whether this path holds a context change rather than a record of one."""
    lowered = relative.lower()
    return lowered.startswith(
        constants.CHANGES_DIR + "/"
    ) or lowered.startswith(constants.LEGACY_CHANGES_DIR + "/")


def _another_copy_is_there(base_root, relative, sorted_out, git) -> bool:
    """Whether some other readable copy of this change exists right now.

    The rule every recovery obeys: nothing is deleted unless a copy of that
    same change is confirmed to be somewhere else at that moment, either on
    the disk or in what was last saved. A deletion that cannot say yes to
    this is not a deletion this is allowed to make.

    The rule is about context changes, because a context change is the thing
    that cannot be got back. The dated record this run writes about its own
    work is not one: it says what the run did, the run is being undone, and
    leaving it behind is what wedged the next run rather than what saved
    anything.
    """
    if not _is_an_entry_path(relative):
        return True
    name = relative.split("/")[-1]
    for where in (
        real_name_of(base_root, constants.LEGACY_CHANGES_DIR) + "/" + name,
        constants.LEGACY_CHANGES_DIR + "/" + name,
        constants.CHANGES_DIR + "/" + name,
    ):
        if where == relative:
            continue
        on_disk = read_text_exactly(
            os.path.join(base_root, where.replace("/", os.sep))
        )
        if on_disk is not None:
            try:
                formats.ChangeEntry.parse(on_disk)
                return True
            except (ValidationError, PathError):
                pass
        if where in sorted_out.restore or _in_head(base_root, where, git):
            return True
    return False


def _put_back(base_root: str, journal: dict, git: GitRunner) -> Optional[str]:
    """Undo every path this module wrote and did not save, and nothing else.

    Everything is classified first. If one path holds the person's own words
    the run stops there, before it has changed anything at all, and the note
    stays so the next run can finish once they have dealt with it.

    A path the base already held when it was last saved is put back to what it
    said then and never removed, because removing one would throw away work
    somebody had already saved.
    """
    sorted_out = _sort_out(base_root, journal, git)
    if sorted_out.theirs:
        return THEIR_WORDS % sorted(sorted_out.theirs)[0]
    if sorted_out.unrecoverable:
        return CANNOT_PUT_BACK % sorted(sorted_out.unrecoverable)[0]

    # Restoring comes first. Undoing first leaves a moment in which a change
    # is in neither folder, and a run killed in that moment leaves it there.
    # Whatever the run took away outright comes back in the same breath.
    bringing_back = list(sorted_out.restore) + [
        relative
        for relative in (journal.get("removed") or [])
        if _in_head(base_root, str(relative), git)
    ]
    if bringing_back:
        result = git.run(
            ["checkout", "HEAD", "--"] + [str(one) for one in bringing_back],
            cwd=base_root,
        )
        if not result.ok:
            return COULD_NOT_SAVE

    for relative, in_head in sorted_out.undo:
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text_exactly(full)
        if current is None:
            continue
        # Asked again, right now. Somebody may have saved this file between
        # the classification above and this moment, and their save must not
        # be undone by a decision made about what was there before it.
        if ids.exact_hash(current) != _what_this_run_wrote(journal, relative):
            return THEIR_WORDS % relative
        try:
            if in_head:
                git.check(["checkout", "HEAD", "--", relative], cwd=base_root)
                continue
            if not _another_copy_is_there(base_root, relative, sorted_out, git):
                return CANNOT_PUT_BACK % relative
            git.check(
                ["rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", relative],
                cwd=base_root,
            )
            remove(full)
        except GitError:
            return COULD_NOT_SAVE
    return None


def _anything_left_over(base_root: str, journal: dict, git: GitRunner):
    """Whether any path this run touched still differs from what was saved.

    The note is only ever taken away when the answer is no. Clearing it while
    something this run did is still sitting there unsaved leaves a base that
    reports edits nobody made and no way left to put them right.
    """
    touched = set()
    for item in journal.get("paths") or []:
        touched.add(str(item.get("path")))
    for item in journal.get("came_from") or []:
        touched.add(str(item.get("path")))
    for item in journal.get("removed") or []:
        touched.add(str(item))
    # Names end in a NUL and come out exactly as they are, so a path with an
    # accent or a space in it is compared as itself rather than as git's
    # quoted form of it.
    status = git.run(["status", "--porcelain", "-z"], cwd=base_root)
    if not status.ok:
        return COULD_NOT_SAVE
    entries = status_entries(status.stdout)
    if entries is None:
        return COULD_NOT_SAVE
    for _letters, named in entries:
        for piece in named:
            if piece in touched:
                return COULD_NOT_SAVE
            for one in touched:
                if piece.endswith("/") and one.startswith(piece):
                    return COULD_NOT_SAVE
    return None


def _what_this_run_wrote(journal: dict, relative: str):
    """The hashes this run recorded for one path, as a set to compare against."""
    for item in journal.get("paths") or []:
        if str(item.get("path")) != relative:
            continue
        allowed = {str(item.get("hash"))}
        after = item.get("after_move")
        if after:
            allowed.add(str(after))
        return _OneOf(allowed)
    return _OneOf(set())


class _OneOf(object):
    """Compares equal to any one of a set of values."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = set(values)

    def __eq__(self, other):
        return other in self.values

    def __ne__(self, other):
        return other not in self.values


# --- Doing it -----------------------------------------------------------------


def _rewritten(text: str) -> str:
    """One entry's own bytes, with only its renamed settings changed.

    This is the one place the rewrite happens, so what the note records and
    what the run writes can never say two different things. It goes through
    the check that reads the answer back, so nothing is ever written that the
    reader cannot read back to the values it read before.
    """
    return formats.rewritten_safely(text)


def _moved_text(entry) -> str:
    """The name this had before the rewrite became a line-level one."""
    return entry.render()


def _record_for(
    base_root: str, moved: List[Tuple[str, str, object]], today: datetime.date
) -> str:
    """The dated record of the move, in the shape `report.py` reads.

    It is a corrections file like every other one, so the summary can parse it
    rather than skipping it, and its class is `other`, because the move found
    nothing wrong and changed no rule. It names no proposal of its own beyond
    the identifier of the first entry it moved, which is what gives the marker
    line something real to name.
    """
    first = moved[0][0]
    paths_touched = [
        constants.CHANGES_DIR + "/" + name for _entry_id, name, _entry in moved
    ]
    named = ", ".join(entry_id for entry_id, _name, _entry in moved)
    correction = formats.CorrectionsFile(
        kind="correction",
        date=today.isoformat(),
        staging_id=first,
        entry_id=None,
        source_id=None,
        intake_path="none",
        mode="none",
        third_party=False,
        content_hash=ids.content_hash("\n".join(sorted(paths_touched))),
        correction_class="other",
        marker=marker_line(first, None, None),
        touched_paths=paths_touched,
        what_changed=RECORD_WHAT_CHANGED % named,
        why=RECORD_WHY,
    )
    return correction.validate().render()


def _record_name(today: datetime.date, moved) -> str:
    """A name no earlier record can already have.

    A base can be moved twice on one day, because an older seat can write into
    the older folder between the two. The changes it moved are what make the
    second record a different record, so they are what name it.
    """
    stamp = ids.content_hash(
        "\n".join(sorted(entry_id for entry_id, _name, _entry in moved))
    )[:8]
    return "%s-move-to-work-changes-%s.md" % (today.isoformat(), stamp)


def _plan_the_writes(
    base_root: str, moved: List[Tuple[str, str, object]], today: datetime.date
) -> List[dict]:
    """Every path this run will write, with a hash of what it will write there.

    This is what lets a later run tell its own unfinished work from the
    person's edits: a path holding exactly this is ours to put back, and a
    path holding anything else is theirs to keep.
    """
    plan = []
    for _entry_id, name, entry in moved:
        source = os.path.join(
            _folder(base_root, constants.LEGACY_CHANGES_DIR), name
        )
        # Read exactly, because these are the bytes the run will put back on
        # the disk and the hashes a later run will recognise them by.
        was = read_text_exactly(source) or ""
        plan.append(
            {
                "path": constants.CHANGES_DIR + "/" + name,
                "hash": ids.exact_hash(_rewritten(was)),
                # What the file holds after the move and before the rewrite.
                # A run that stopped between the two leaves this on the disk,
                # and it is as much this module's own work as the other one.
                "after_move": ids.exact_hash(was),
            }
        )
    plan.append(
        {
            "path": constants.CORRECTIONS_DIR + "/" + _record_name(today, moved),
            "hash": ids.exact_hash(_record_for(base_root, moved, today)),
        }
    )
    return plan


def _came_from(base_root: str, moved: List[Tuple[str, str, object]]) -> List[dict]:
    """Where each file was before the move, and what it said when it was there.

    The folder is named the way the disk really names it. Most Macs do not
    tell `work/Decisions` from `work/decisions`, but git does, and a note
    recording the spelling git does not hold is a note whose every question
    about that path comes back no. That is what made a recovery believe it
    had nothing to put back while it went on deleting what it had moved.
    """
    older = real_name_of(base_root, constants.LEGACY_CHANGES_DIR)
    rows = []
    for _entry_id, name, _entry in moved:
        relative = older + "/" + name
        was = read_text_exactly(
            os.path.join(base_root, relative.replace("/", os.sep))
        )
        rows.append({"path": relative, "hash": ids.exact_hash(was or "")})
    return rows


def _save(base_root: str, subject: str, git: GitRunner) -> None:
    """Save what is staged, unless there is nothing staged to save.

    A rewrite of a file that already said the right thing leaves nothing
    staged, which is a run that had nothing to do rather than a run that
    failed, so it is allowed to pass quietly.
    """
    staged = git.run(["diff", "--cached", "--quiet"], cwd=base_root)
    if staged.ok:
        return
    name, address, _codes = compose_proposal._author(base_root, git)
    git.check(
        [
            "-c",
            "user.name=%s" % name,
            "-c",
            "user.email=%s" % address,
            "commit",
            "-q",
            "-m",
            subject,
        ],
        cwd=base_root,
    )


def _do_the_move(
    base_root: str,
    moved: List[Tuple[str, str, object]],
    dropped: List[str],
    git: GitRunner,
) -> None:
    """Change one: the files move and not one character of them changes.

    The move is saved on its own so that a later look at which change first
    added a file follows it through. `report.py` counts a catch by that look,
    and a move saved together with a rewrite is a file git reads as newly
    added, which would quietly drop the catch it belongs to.

    An older copy of an entry the newer folder already holds is taken away in
    this same saved change. It says exactly what the copy that stays says,
    which the check before this established, so nothing is lost by it going.
    """
    destination = _folder(base_root, constants.CHANGES_DIR)
    if not os.path.isdir(destination):
        os.makedirs(destination)
    older = real_name_of(base_root, constants.LEGACY_CHANGES_DIR)
    for _entry_id, name, _entry in moved:
        git.check(
            ["mv", older + "/" + name, constants.CHANGES_DIR + "/" + name],
            cwd=base_root,
        )
    for relative in dropped:
        git.check(
            ["rm", "-q", "-f", "--", real_name_of(base_root, relative)],
            cwd=base_root,
        )
    _take_the_placeholder(base_root, git)
    _save(base_root, MOVE_SUBJECT, git)


def _take_the_placeholder(base_root: str, git: GitRunner) -> None:
    """Take away the older folder once it holds nothing but its placeholder.

    A base built by an earlier release keeps an empty file there so the folder
    itself could be shared. Once every change has left, that file is the only
    thing holding a folder nothing writes to any more, so it goes in the same
    saved change.
    """
    older = real_name_of(base_root, constants.LEGACY_CHANGES_DIR)
    folder = _folder(base_root, older)
    if not os.path.isdir(folder):
        return
    left = sorted(os.listdir(folder))
    if left != [".gitkeep"]:
        return
    relative = older + "/.gitkeep"
    try:
        git.check(["rm", "-q", "-f", "--", relative], cwd=base_root)
    except GitError:
        # It was never saved, so taking it off the disk is the whole of it.
        remove(os.path.join(folder, ".gitkeep"))


def _do_the_rewrite(
    base_root: str, moved: List[Tuple[str, str, object]], git: GitRunner
) -> None:
    """Change two, the commit point: each file under the names in use today.

    Each file is read as it stands and written back with only its renamed
    settings changed. Every other byte of it, the body included, is left
    exactly as the person wrote it.
    """
    written = []
    for _entry_id, name, _entry in moved:
        relative = constants.CHANGES_DIR + "/" + name
        full = os.path.join(base_root, relative.replace("/", os.sep))
        current = read_text_exactly(full)
        if current is None:
            continue
        atomic_write_text(
            full, _rewritten(current), mode=0o644, inside=base_root
        )
        written.append(relative)
    if not written:
        return
    git.check(["add", "--"] + written, cwd=base_root)
    _save(base_root, REWRITE_SUBJECT, git)


def _do_the_record(
    base_root: str,
    moved: List[Tuple[str, str, object]],
    today: datetime.date,
    git: GitRunner,
) -> None:
    relative = constants.CORRECTIONS_DIR + "/" + _record_name(today, moved)
    atomic_write_text(
        os.path.join(base_root, relative.replace("/", os.sep)),
        _record_for(base_root, moved, today),
        mode=0o644,
        inside=base_root,
    )
    git.check(["add", "--", relative], cwd=base_root)
    _save(base_root, RECORD_SUBJECT, git)


def _moved_from_note(base_root: str, journal: dict):
    """The entries a stopped run had already moved, read back off the disk.

    They are read from where the move put them rather than from the note,
    because what has to be written is what each file says, and the note holds
    only a hash of it. A file that cannot be read back is the one case this
    cannot finish, and it says so rather than guessing.
    """
    moved = []
    for item in journal.get("paths") or []:
        relative = str(item.get("path") or "")
        if not relative.startswith(constants.CHANGES_DIR + "/"):
            continue
        name = relative.split("/")[-1]
        text = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
        if text is None:
            return relative
        try:
            entry = formats.ChangeEntry.parse(text)
        except (ValidationError, PathError):
            return relative
        moved.append((entry.id, name, entry))
    return moved


def _theirs_before_finishing(base_root, journal, git) -> Optional[str]:
    """Whether anything this run would write to holds somebody else's work.

    Same rule as putting back, applied to finishing. Every path the note names
    has to hold either what the move left there or what the rewrite was going
    to leave there. Anything else is the person's, and it is named.

    What is unsaved anywhere else in the base stops it too. A run that saved
    the person's half written sentence as its own rewrite is exactly what this
    is here to stop, and the only paths it is entitled to save are the ones it
    wrote itself.
    """
    ours = {}
    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        allowed = [str(item.get("hash"))]
        after = item.get("after_move")
        if after:
            allowed.append(str(after))
        ours[relative] = allowed

    for relative, allowed in sorted(ours.items()):
        current = read_text_exactly(
            os.path.join(base_root, relative.replace("/", os.sep))
        )
        if current is None:
            continue
        if ids.exact_hash(current) not in allowed:
            return THEIR_WORDS % relative

    # Names end in a NUL and come out exactly as they are, so a path with an
    # accent or a space in it is its own name here and not git's quoted form.
    status = git.run(["status", "--porcelain", "-z"], cwd=base_root)
    if not status.ok:
        return COULD_NOT_SAVE
    entries = status_entries(status.stdout)
    if entries is None:
        return COULD_NOT_SAVE
    for _letters, named in entries:
        # A rename names two paths, and both belong to this run when this run
        # is the thing that moved it.
        for piece in named:
            for unexplained in _what_is_really_there(base_root, piece, ours):
                return THEIR_WORDS % unexplained
    return None


def _what_is_really_there(base_root: str, named: str, ours) -> List[str]:
    """The paths behind one line of what git says is unsaved, minus our own.

    Git names a whole folder when nothing inside it has ever been saved, so a
    run that had just written the first file into `corrections` saw one line
    naming the folder and read it as somebody else's work. The folder is
    opened and what is really in it is compared instead.
    """
    if named.startswith(constants.LEGACY_CHANGES_DIR + "/"):
        return []
    if named == constants.LEGACY_CHANGES_DIR + "/":
        return []
    if not named.endswith("/"):
        return [] if named in ours else [named]
    folder = os.path.join(base_root, named.replace("/", os.sep))
    if not os.path.isdir(folder):
        return [named]
    left = []
    for where, _folders, files in os.walk(folder):
        for name in sorted(files):
            full = os.path.join(where, name)
            relative = os.path.relpath(full, base_root).replace(os.sep, "/")
            if relative not in ours:
                left.append(relative)
    return left


def _finish_from_note(base_root, base_id, journal, saved, git) -> Result:
    """Carry out whatever a stopped run had not saved yet, and nothing more.

    The move has landed by the time this is called, and a base whose entries
    have moved without being rewritten is one every reader here already reads,
    so there is nothing to unpick. The day comes off the note, so the dated
    record is the one the run would have written had it never stopped.

    Everything is classified before anything is written, the same way putting
    back classifies everything first.
    """
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        return _refused(CODE_NOT_DEFAULT_BRANCH, NOT_ON_MAIN)
    stopped = _theirs_before_finishing(base_root, journal, git)
    if stopped is not None:
        code = CODE_GIT_FAILED if stopped == COULD_NOT_SAVE else CODE_UNSAVED_EDITS
        return _refused(code, stopped)

    moved = _moved_from_note(base_root, journal)
    if isinstance(moved, str):
        # A file this run had already moved is gone, renamed, or no longer
        # readable. It cannot be finished and it must not be guessed at, so
        # the document is named and the one way out is said in the same
        # breath.
        return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % moved)
    if not moved:
        return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % "one of them")
    day = _as_date(str(journal.get("day") or "")) or state.today()
    try:
        if REWRITE_SUBJECT not in saved:
            _do_the_rewrite(base_root, moved, git)
        if RECORD_SUBJECT not in saved:
            _do_the_record(base_root, moved, day, git)
    except GitError:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    _clear_journal(base_id)
    return Result(
        STATUS_RESUMED,
        sentence=MIGRATED % len(moved),
        moved=[constants.CHANGES_DIR + "/" + name for _id, name, _e in moved],
        entry_ids=[entry_id for entry_id, _name, _entry in moved],
    )


def _as_date(text: str) -> Optional[datetime.date]:
    try:
        return datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
    except (ValueError, IndexError, TypeError):
        return None


def abandon(
    base_root: str,
    base_id: str,
    today: Optional[datetime.date] = None,
    git: Optional[GitRunner] = None,
) -> Result:
    """Give up on a run that stopped, and say what was left alone.

    It is the one way out of a run nothing can finish, which is a real state:
    a file the run had moved can be deleted, renamed, or edited into
    something nothing can read, and without this the note would stay and the
    same sentence would come back for ever.

    It puts back only what still matches what the note recorded, leaves
    everything else exactly as it is, names what it left, and takes the note
    away either way, because the whole point is that the base stops being
    stuck.
    """
    runner = runner_or_default(git)
    journal, problem = _checked_journal(base_id, base_root)
    if problem is not None:
        # A note nothing can read is not a note to act on, and deleting it
        # while claiming everything was put back is the one thing giving up
        # must never do.
        return _refused(CODE_NOTE_UNREADABLE, GAVE_UP_NOTE_UNREADABLE)
    if not journal:
        return Result(STATUS_NOT_NEEDED, sentence=NOTHING_TO_MOVE)

    saved = _subjects_since(base_root, str(journal.get("head")), runner)
    if saved is None:
        return _refused(CODE_CANNOT_READ_HISTORY, CANNOT_READ_HISTORY)
    landed = MOVE_SUBJECT in saved or _move_has_landed(base_root, journal, runner)

    sorted_out = _sort_out(base_root, journal, runner)
    # A path holding the person's own words is left alone, and the copy the
    # move made is left with it: putting the older one back beside it would
    # leave one change written down twice, which is worse than either.
    theirs = set(sorted_out.theirs)
    came_from_of = {}
    for item in journal.get("came_from") or []:
        name = str(item.get("path")).split("/")[-1]
        came_from_of[name] = str(item.get("path"))
    keep_back = set()
    for relative in theirs:
        keep_back.add(came_from_of.get(relative.split("/")[-1], ""))

    if not landed:
        bringing_back = [
            relative
            for relative in list(sorted_out.restore)
            + [str(one) for one in (journal.get("removed") or [])]
            if relative not in keep_back and _in_head(base_root, relative, runner)
        ]
        if bringing_back:
            result = runner.run(
                ["checkout", "HEAD", "--"] + bringing_back, cwd=base_root
            )
            if not result.ok:
                return _refused(CODE_GIT_FAILED, GAVE_UP_COULD_NOT)

    # Whatever this run left behind and never saved is taken away, whether or
    # not the move landed. A file the base already holds is put back to what
    # it says there, and one it does not is removed. This is what was missed:
    # giving up on a run that had written its dated record and not saved it
    # used to leave that record sitting there, and every run afterwards said
    # the person had unsaved work they had never done.
    for relative, in_head in sorted_out.undo:
        if relative in theirs:
            continue
        full = os.path.join(base_root, relative.replace("/", os.sep))
        if read_text_exactly(full) is None:
            continue
        try:
            if in_head:
                runner.check(["checkout", "HEAD", "--", relative], cwd=base_root)
                continue
            if not _another_copy_is_there(base_root, relative, sorted_out, runner):
                continue
            runner.check(
                ["rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", relative],
                cwd=base_root,
            )
            remove(full)
        except GitError:
            # Nothing is claimed that was not done. The note stays so this can
            # be tried again once whatever refused the write has let go.
            return _refused(CODE_GIT_FAILED, GAVE_UP_COULD_NOT)

    # The note is only ever taken away once nothing of this run's is left,
    # which is the same rule putting back already follows. Anything the
    # person's own hands are on is theirs and is named instead.
    if not theirs:
        left_over = _anything_left_over(base_root, journal, runner)
        if left_over is not None:
            return _refused(CODE_GIT_FAILED, GAVE_UP_COULD_NOT)

    _clear_journal(base_id)
    if theirs:
        return Result(
            STATUS_UNDONE,
            sentence=GAVE_UP_LEFT_ALONE % ", ".join(sorted(theirs)),
        )
    if landed:
        return Result(STATUS_UNDONE, sentence=GAVE_UP_HALF_DONE)
    return Result(STATUS_UNDONE, sentence=GAVE_UP)


def migrate(
    base_root: str,
    base_id: str,
    today: Optional[datetime.date] = None,
    git: Optional[GitRunner] = None,
    every_seat_updated: bool = False,
) -> Result:
    """Move this base's entries into `work/changes`, or say why it did not.

    Nothing here runs on its own. The caller asks only after the owner has
    said yes, because this writes to their base and the standing rule is that
    nothing is applied without one.

    On a base other people can reach it asks for one thing more. A seat on an
    older release reads a moved base as though it held nothing, so the owner
    has to say that everyone who opens this base is on this release before it
    will touch it.
    """
    runner = runner_or_default(git)
    day = today or state.today()

    journal, problem = _checked_journal(base_id, base_root)
    if problem is not None:
        return _refused(CODE_NOTE_UNREADABLE, NOTE_UNREADABLE)
    put_back = False
    if journal:
        saved = _subjects_since(base_root, str(journal.get("head")), runner)
        if saved is None:
            # We could not find out what landed. Not knowing is not the same
            # as nothing having landed, and treating it as the second is what
            # took a saved move apart.
            return _refused(CODE_CANNOT_READ_HISTORY, CANNOT_READ_HISTORY)
        if MOVE_SUBJECT in saved or _move_has_landed(base_root, journal, runner):
            return _finish_from_note(base_root, base_id, journal, saved, runner)
        stopped = _put_back(base_root, journal, runner)
        if stopped is None:
            stopped = _anything_left_over(base_root, journal, runner)
        if stopped is not None:
            # The note stays, because a note thrown away is a run nobody can
            # finish. Their own words sitting on one of these paths is a
            # different sentence from git giving up, so it keeps its own code.
            if stopped == COULD_NOT_SAVE:
                code = CODE_GIT_FAILED
            elif stopped.startswith(CANNOT_PUT_BACK.split("%s")[0]):
                code = CODE_CANNOT_PUT_BACK
            else:
                code = CODE_UNSAVED_EDITS
            return _refused(code, stopped)
        _clear_journal(base_id)
        put_back = True

    refusal = _ready_to_write(base_root, runner)
    if refusal is not None:
        # A tree this module's own unfinished work dirtied was put back just
        # above, so anything left here is the person's own.
        return refusal

    found, refused = _prevalidate(base_root)
    if refused is not None:
        return refused
    moved = _to_move(found)
    dropped = _to_drop(found)
    if (
        (moved or dropped)
        and not every_seat_updated
        and paths.remote_url(base_root, runner=runner) is not None
    ):
        return _refused(CODE_EVERY_SEAT_FIRST, EVERY_SEAT_FIRST)
    if not moved and not dropped:
        # Nothing left to move. There may still be entries a stopped run
        # moved and never rewrote, and finishing those is what was asked for.
        left_over = _left_to_rewrite(base_root, found)
        if left_over:
            return _finish_the_rewrite(base_root, base_id, left_over, day, runner)
        return Result(
            STATUS_NOT_NEEDED,
            sentence=PUT_BACK if put_back else NOTHING_TO_MOVE,
        )

    head = _head(base_root, runner)
    if not head:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    plan = _plan_the_writes(base_root, moved, day)
    _write_journal(
        base_id,
        base_root,
        head,
        plan,
        _came_from(base_root, moved),
        day,
        _to_be_removed(base_root, dropped),
    )

    try:
        _do_the_move(base_root, moved, dropped, runner)
        _do_the_rewrite(base_root, moved, runner)
        _do_the_record(base_root, moved, day, runner)
    except GitError:
        # Saying the base is as it was while half a move is still sitting in
        # the index is a sentence that is not true. It is put back first, and
        # what is said depends on whether that worked.
        journal, _problem = _checked_journal(base_id, base_root)
        if journal:
            stopped = _put_back(base_root, journal, runner)
            if stopped is None:
                stopped = _anything_left_over(base_root, journal, runner)
            if stopped is None:
                _clear_journal(base_id)
                return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
            return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE_LEFT_HALF_DONE)
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)

    _clear_journal(base_id)
    return Result(
        STATUS_MIGRATED,
        sentence=MIGRATED % len(moved),
        moved=[constants.CHANGES_DIR + "/" + name for _id, name, _e in moved],
        entry_ids=[entry_id for entry_id, _name, _entry in moved],
    )


def _left_to_rewrite(base_root: str, found: "_Survey"):
    """Entries already in the newer folder that still carry the older words."""
    folder = _folder(base_root, constants.CHANGES_DIR)
    left = []
    for entry_id, (name, entry, _said) in sorted(found.new.items()):
        text = read_text_exactly(os.path.join(folder, name))
        if text is None:
            continue
        try:
            if formats.rewritten_safely(text) != text:
                left.append((entry_id, name, entry))
        except (ValidationError, PathError):
            continue
    return left


def _finish_the_rewrite(base_root, base_id, left_over, day, git) -> Result:
    """Rewrite entries a stopped run moved and never got round to renaming.

    It is the second half of the update on its own, saved as its own piece of
    work, because a base can be left exactly there by a run that was given up
    on after its first half had already been saved.
    """
    refusal = _ready_to_write(base_root, git)
    if refusal is not None:
        return refusal
    head = _head(base_root, git)
    if not head:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    plan = []
    for _entry_id, name, _entry in left_over:
        relative = constants.CHANGES_DIR + "/" + name
        was = read_text_exactly(
            os.path.join(base_root, relative.replace("/", os.sep))
        )
        plan.append(
            {
                "path": relative,
                "hash": ids.exact_hash(_rewritten(was or "")),
                "after_move": ids.exact_hash(was or ""),
            }
        )
    plan.append(
        {
            "path": constants.CORRECTIONS_DIR + "/" + _record_name(day, left_over),
            "hash": ids.exact_hash(_record_for(base_root, left_over, day)),
        }
    )
    _write_journal(base_id, base_root, head, plan, [], day, [])
    try:
        _do_the_rewrite(base_root, left_over, git)
        _do_the_record(base_root, left_over, day, git)
    except GitError:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    _clear_journal(base_id)
    return Result(
        STATUS_MIGRATED,
        sentence=MIGRATED % len(left_over),
        moved=[constants.CHANGES_DIR + "/" + name for _id, name, _e in left_over],
        entry_ids=[entry_id for entry_id, _name, _entry in left_over],
    )


def offer_state_sentence(state_of_the_offer: str) -> str:
    """What a read-only look says about whether the offer would be made."""
    if state_of_the_offer == OFFER_NOW:
        return OFFER_STATE_NOW
    if state_of_the_offer == OFFER_EVERY_SEAT_FIRST:
        return OFFER_STATE_EVERY_SEAT_FIRST
    return OFFER_STATE_NONE


def what_would_happen(
    base_root: str,
    base_id: str,
    today: Optional[datetime.date] = None,
    git: Optional[GitRunner] = None,
) -> str:
    """What a run would do, worked out without writing one single thing.

    Every check the run itself makes is made here and nothing else is, so a
    look is a look. It is what the skill means when it says that a look only
    writes nothing at all.
    """
    runner = runner_or_default(git)
    day = today or state.today()
    journal, problem = _checked_journal(base_id, base_root)
    if problem is not None:
        return WOULD_NOT % NOTE_UNREADABLE
    if journal:
        return WOULD_FINISH
    refusal = _ready_to_write(base_root, runner)
    if refusal is not None:
        return WOULD_NOT % refusal.sentence
    found, refused = _prevalidate(base_root)
    if refused is not None:
        return WOULD_NOT % refused.sentence
    moved = _to_move(found)
    dropped = _to_drop(found)
    if not moved and not dropped:
        return WOULD_NOT % NOTHING_TO_MOVE
    if paths.remote_url(base_root, runner=runner) is not None:
        return WOULD_NOT % EVERY_SEAT_FIRST
    return WOULD_MOVE % (counted(len(moved) + len(dropped)), day.isoformat())


def counted(number: int) -> str:
    """A count as a person says it: in words up to ten, as a number after."""
    if 0 <= number < len(COUNT_WORDS):
        return COUNT_WORDS[number]
    return str(number)


def resume(
    base_root: str,
    base_id: str,
    today: Optional[datetime.date] = None,
    git: Optional[GitRunner] = None,
) -> Result:
    """Finish or put back a run of this that stopped, and then carry on.

    It is the same call as `migrate`, named for what it is doing when a note
    is already there, so that a caller picking a run back up says so.
    """
    return migrate(base_root, base_id, today=today, git=git)
