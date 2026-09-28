"""Moving a base to the layout GTM Base writes today, once, on its owner's yes.

A base is laid out by the five parts of the CLASS framework (Unit 1.5b of the
2026-09-19 plan): its documents flat in `context`, such as `context/icps.md`,
its context changes in `learning/changes`, and its records of what changed in
`learning/corrections`. A base set up earlier holds the same things at older
paths. Before the rename of Unit 1.4 its context changes sat in
`work/decisions`, each calling itself a decision and carrying `decided_on` and
`decided_by`. Between that rename and this layout they sat in `work/changes`.
Its profile and positioning sat in `context/strategy`, and its records sat in
`corrections`.

Every one of those is read everywhere, by `base_reader` and `layout`, so
nothing here has to run for a base to work. What this does is finish the move,
once, on a base its owner has said yes to, and it takes the base all the way to
the current layout in one move from wherever it starts: still on
`work/decisions`, on `work/changes`, or half way through an earlier move.

It is written as a recorded transaction, for the reason every write in this
library is: a run can stop in the middle, and the state it stops in has to be
one the next run can finish or put back rather than one a person has to unpick
by hand. The same note this module writes is the one `approve_local` writes for
a local approval, in the same folder and checked the same way: the identifier
of the run, the base it is about, where the base stood before anything was
written, and a hash of every path this run was going to write.

The order is fixed:

1. Read everything that moves, exactly as the bytes really are. Check that
   every context change parses, that renaming its settings would change
   nothing but the names, that no identifier sits in two folders saying two
   different things, that every file is named after the change inside it, and
   that nothing already sits where a file would move to saying something
   different. Anything else is refused by name and nothing is written.
2. Refuse on a tree the person has edits sitting in, apart from edits this
   module's own unfinished run left, which are dealt with first.
3. Write the note, recording where the base stood, what each path will hold,
   where each file came from and what it said there, and what this run will
   take away outright.
4. Save change one: the files move, older copies of files already at their
   new place are taken away, the placeholders of folders left empty go, and
   not one character of any file changes. A later look at which saved change
   first added a file follows it through a move, and `report.py` counts a
   catch by that look; git itself follows a confirmation file's lines, and a
   record's first change, the same way.
5. Save change two: the older setting names in each context change are
   renamed, and the map's paragraph about where things live is brought up to
   date when it is still the paragraph GTM Base wrote. This is the commit
   point.
6. Save the dated record in `learning/corrections`, in the shape `report.py`
   reads, with the placeholders of the folders the current layout adds.
7. Take the note away.

Two rules hold over all of it.

Nothing is ever written to a base in a form the reader cannot read back to
exactly the values it read before. The rename is checked against itself before
anything moves, so a file it cannot handle is a sentence naming that file
rather than a saved change nothing can read.

No recovery deletes a file unless another readable copy of that same thing is
confirmed to be somewhere else at that moment. A later run that finds a note
decides by what was saved. Nothing saved means nothing landed, so what this run
wrote and did not save is put back, what it took away is brought back, and only
then does the note go. Anything saved means the move has landed, and a base
whose files have moved without being renamed is one every reader here already
reads, so the run finishes what is left rather than unpicking what is done.

A note left by the release before this one, which moved context changes into
`work/changes` and nothing else, is still read, finished, or put back exactly
as that release would have. The next offer then takes the base the rest of the
way.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Dict, List, Optional, Tuple

from . import (
    base_reader,
    compose_proposal,
    constants,
    formats,
    ids,
    names,
    paths,
    state,
    unsaved,
)
from .errors import GitError, PathError, ValidationError
from .fsutil import (
    atomic_write_json,
    atomic_write_text,
    read_json,
    read_text,
    read_text_exactly,
    remove,
)
from .gitcmd import GitRunner, runner_or_default
from .validate import marker_line

# What this seat remembers about being asked, so it is asked once.
SEAT_PUT_OFF_KEY = "changes_move_put_off_until"
# The note this module leaves in the seat's own folder while it is working.
JOURNAL_FILE = "changes-migration.json"
JOURNAL_SCHEMA = 2
# The note the release before this one wrote. It moved context changes into
# `work/changes` and nothing else, and a run of it that stopped is finished or
# put back exactly as that release would have.
LEGACY_JOURNAL_SCHEMA = 1

# The notes saved with each of the three pieces of work, in the order they are
# saved. They are matched against what landed, so they never change casually.
MOVE_SUBJECT = constants.MOVE_TO_LAYOUT_SUBJECT
REWRITE_SUBJECT = constants.REWRITE_FOR_LAYOUT_SUBJECT
RECORD_SUBJECT = constants.RECORD_LAYOUT_SUBJECT
SUBJECTS = (MOVE_SUBJECT, REWRITE_SUBJECT, RECORD_SUBJECT)
# The three the release before this one saved, which a note it left names.
LEGACY_SUBJECTS = (
    constants.MOVE_TO_CHANGES_SUBJECT,
    "Write each context change under its plainer setting names",
    "Record the move to work/changes",
)

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
CODE_DOCUMENT_TAKEN = "a-different-copy-of-that-document-is-already-there"
CODE_CANNOT_READ_HISTORY = "cannot-read-what-was-saved"
CODE_TWICE_IN_ONE_FOLDER = base_reader.CODE_TWICE_IN_ONE_FOLDER
CODE_EVERY_SEAT_FIRST = "every-seat-updates-first"
CODE_CANNOT_FINISH = "cannot-finish-the-unfinished-update"
CODE_NAME_IS_NOT_THE_ID = base_reader.CODE_NAME_IS_NOT_THE_ID
CODE_CANNOT_PUT_BACK = "cannot-put-back-what-was-moved"

# --- The sentences a person reads -------------------------------------------

# The offer, in the way release notes say what a version changed: the version
# that brought the current layout in, and what in this base still sits where
# the older layout kept it, the documents by name and the rest counted in
# words (Brandon's call 40, from the 0.3.1 live check, step 2). It names no
# folder and no framework (call 41).
OFFER_ONE = (
    "GTM Base %(version)s introduced the current layout, which keeps "
    "documents, context changes, and records in new places. Your base still "
    "keeps %(what)s in the older place. Moving it changes nothing it says, and "
    "your base works either way until you do. Shall I move it now?"
)
OFFER_MANY = (
    "GTM Base %(version)s introduced the current layout, which keeps "
    "documents, context changes, and records in new places. Your base still "
    "keeps %(what)s in the older places. Moving them changes nothing they say, "
    "and your base works either way until you do. Shall I move them now?"
)
# The same, on a base other people can reach, with the condition and its
# one-line reason in place of the question.
EVERY_SEAT_FIRST_ONE = (
    "GTM Base %(version)s introduced the current layout, which keeps "
    "documents, context changes, and records in new places. Your base still "
    "keeps %(what)s in the older place. Everyone who opens this base has to be "
    "on the current version of GTM Base before it moves, because an older one "
    "would read the moved base as empty. Tell me once that is true and I will "
    "move it."
)
EVERY_SEAT_FIRST_MANY = (
    "GTM Base %(version)s introduced the current layout, which keeps "
    "documents, context changes, and records in new places. Your base still "
    "keeps %(what)s in the older places. Everyone who opens this base has to "
    "be on the current version of GTM Base before they move, because an older "
    "one would read the moved base as empty. Tell me once that is true and I "
    "will move them."
)
# Said instead of the offer on a base other people can reach. Everyone who
# opens it has to be on this release first, because an older one reads a
# moved base as though it held nothing at all.
EVERY_SEAT_FIRST = (
    "Your base is laid out the older way, and moving it to the current layout "
    "is one step. Everyone who opens this base has to be on the current "
    "version of GTM Base first, because an older one would read the moved "
    "base as empty. Tell me once that is true and I will do it."
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
# It says how many of each thing, in words, and never which ones by their
# identifiers: a person reads this, and an identifier is a name only GTM Base
# uses (finding 4 of the release A live check).
WOULD_MOVE = (
    "This would move %s to the current layout and write one dated record of "
    "it under today's date, %s. It would be saved as separate pieces of work. "
    "Nothing has been written."
)
# How many, the way a person says it, up to the point a person would say the
# number itself instead.
COUNT_WORDS = names.COUNT_WORDS
# What each kind of thing the move carries is called, one and more than one.
KIND_WORDS = {
    "document": ("document", "documents"),
    "entry": ("context change", "context changes"),
    "record": ("record", "records"),
}
WOULD_NOT = "This would not run right now. %s Nothing has been written."
PUT_OFF = (
    "GTM Base will not offer to move your base to the current layout again "
    "until %s."
)
# What a read-only look adds when the move would run and yet would not be
# offered, which is only ever because the person said not now. Every other
# reason is already the look's own sentence, and when the offer would be made
# the look adds nothing (the 0.3.1 live check, step 3, finding 1).
NOT_OFFERED_PUT_OFF = (
    "GTM Base is not offering it right now, because you said not now, and it "
    "will offer it again on %s."
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
LAYOUT_RECORD_WHAT_CHANGED = (
    "Before: the base was laid out the older way, with its documents, its "
    "context changes, and its records in older folders.\n\nAfter: it is laid "
    "out by the five parts of the CLASS framework, and every document, "
    "context change, and record in it says exactly what it said before. It "
    "moved %s."
)
LAYOUT_RECORD_WHY = (
    "A base is laid out by the five parts of the CLASS framework, so anyone "
    "who knows the framework can open it and find each part by the name of "
    "its folder."
)
# The dated record the release before this one wrote, kept word for word,
# because a run of it that stopped has to finish with the very record it
# meant to write, or the next run could not recognise its own work.
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
    "Your base is now laid out the current way, and every document and "
    "context change in it says exactly what it said before."
)
NOTHING_TO_MOVE = "Your base is already laid out the current way."
UNREADABLE_ENTRY = (
    "GTM Base could not read %s, so nothing was moved. Have a look at that "
    "file and ask again."
)
NAME_IS_NOT_THE_ID = (
    "One of your context changes says it is the context change %s, which is "
    "not the name it is saved under, so nothing was moved. Two files could end "
    "up with one identifier. Rename it to match and ask again."
)
SAME_CHANGE_TWICE = (
    "The context change %s is written in two folders and the two do not say "
    "the same thing, so nothing was moved. Decide which one is right, take the "
    "other one away, and ask again."
)
TWICE_IN_ONE_FOLDER = (
    "Two files say they are the context change %s, and they do not say the "
    "same thing, so nothing was moved. Decide which one is right, take the "
    "other one away, and ask again."
)
DESTINATION_TAKEN = (
    "There is already a file where %s would go, so nothing was moved."
)
# A document is named the way a person calls it, never by its path.
DOCUMENT_TAKEN = (
    "There are two copies of %s, one where it is now and one where the move "
    "would put it, and they do not say the same thing, so nothing was moved. "
    "Decide which one is right, take the other one away, and ask again."
)
UNSAVED_EDITS = (
    "You have unsaved edits in your base, so nothing was moved. Deal with "
    "those first and ask again."
)
# The same refusal with the unsaved files said in it. The one sentence naming
# them goes where the `%s` is, before the one thing to do.
UNSAVED_EDITS_NAMED = (
    "You have unsaved edits in your base, so nothing was moved. %s Deal with "
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

# How a file is named in a sentence a person reads. A file's own name comes
# out of the base, and a sentence carrying it is handed to the assistant
# outside any fence, so no name is ever read out as it is (Astra's review of
# Unit 1.5b, finding 7). A document gets the name a person calls it by, from
# `names`, and everything else gets one of these.
NAMED_CONTEXT_CHANGE = unsaved.ONE_OF_YOUR_CONTEXT_CHANGES
# A context change whose file is named by an identifier of the one shape
# GTM Base gives them is called by it, the way every other sentence here
# calls a context change, because that shape can carry nothing else.
NAMED_THE_CONTEXT_CHANGE = "the context change %s"
NAMED_RECORD = unsaved.ONE_OF_YOUR_RECORDS
NAMED_FILE = unsaved.ONE_OF_YOUR_FILES


def _named(relative) -> str:
    """What one path is called in a sentence, never the path itself."""
    text = str(relative or "")
    lowered = text.lower()
    if _is_an_entry_path(text):
        stem = text.split("/")[-1]
        stem = stem[: -len(".md")] if stem.endswith(".md") else ""
        if ids.is_staging_id(stem):
            return NAMED_THE_CONTEXT_CHANGE % stem
        return NAMED_CONTEXT_CHANGE
    for folder in constants.ALL_CORRECTIONS_DIRS:
        if lowered.startswith(folder + "/"):
            return NAMED_RECORD
    if lowered.startswith(constants.CONTEXT_DIR + "/") or text == constants.STACK_PATH:
        try:
            return names.document_name(text)
        except ValueError:
            return NAMED_FILE
    return NAMED_FILE


def _all_named(paths_found, base_root: Optional[str] = None) -> str:
    """Several paths holding the person's unsaved words, each name said once.

    They are named by the fixed labels every refusal about unsaved work uses
    (release 0.3.2), so a segment or a file the product does not know is
    never read out by its own name.
    """
    said = []
    for relative in sorted(paths_found):
        name = unsaved.plain_name(relative, base_root)
        if name not in said:
            said.append(name)
    return ", ".join(said)


# --- The map's paragraph about where things live ------------------------------

# The heading of the map's one paragraph a person reads rather than a setting.
MAP_WHERE_HEADING = "## Where things live"
# The paragraph as GTM Base writes it today. The template holds the same
# words, and a test holds the two to each other.
MAP_WHERE_TODAY = (
    "This base is laid out by the five parts of the CLASS framework. The `context`\n"
    "folder holds what is true about the business, one file for each subject:\n"
    "`goals.md`, `product.md`, `icps.md`, `buyer-personas.md`, `positioning.md`,\n"
    "`messaging.md`, `voice.md`, `design.md`, and `metrics.md`, with one file for\n"
    "each customer segment in `context/icps`. The `learning` folder holds how the\n"
    "base gets better, with one dated entry for each context change in\n"
    "`learning/changes` and what each approved fix changed in `learning/corrections`.\n"
    "The `access` folder holds `stack.md`, which says where the work comes from and\n"
    "where it goes. The `skills` folder is kept empty for now, and the `standards`\n"
    "folder holds what good work looks like for each job. The `work` folder holds\n"
    "the approvals, with the owner's confirmations in `work/confirmations`."
)
# The paragraph as earlier releases wrote it, word for word. Only a map still
# holding one of these exactly is brought up to date. A paragraph the person
# has changed in any way is theirs, and it is left exactly as it is.
MAP_WHERE_EARLIER = (
    "The `context` folder holds everything the AI reads for meaning, with strategy\n"
    "documents in `context/strategy`, numbers and their definitions in\n"
    "`context/metrics`, goals and targets in `context/plan`, and your own working\n"
    "notes in `context/notes`. The `work` folder holds the record of how the base\n"
    "stays current, with one dated entry per context change in `work/changes`\n"
    "and the owner's confirmations in `work/confirmations`. The `corrections` folder holds\n"
    "what each run found wrong and which rule changed because of it.",
    "The `context` folder holds everything the AI reads for meaning, with strategy\n"
    "documents in `context/strategy`, numbers and their definitions in\n"
    "`context/metrics`, goals and targets in `context/plan`, and your own working\n"
    "notes in `context/notes`. The `work` folder holds the record of how the base\n"
    "stays current, with one dated entry per decision in `work/decisions` and the\n"
    "owner's confirmations in `work/confirmations`. The `corrections` folder holds\n"
    "what each run found wrong and which rule changed because of it.",
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


def _full(base_root: str, relative: str) -> str:
    return os.path.join(base_root, relative.replace("/", os.sep))


def real_name_of(base_root: str, name: str) -> str:
    """One path spelled the way the disk really spells it.

    Most Macs do not tell two spellings of one folder name apart, so a base
    whose folder was made as `work/Decisions` is the same folder to every
    read. Git is not so forgiving: it holds the name it was given, and a move
    that names the other spelling fails. Everything that hands a path to git
    asks for the real one first. Every part of the path is looked up, so a
    document under `context/Strategy` is found as surely as a folder.
    """
    found = []
    where = base_root
    for wanted in [part for part in name.split("/") if part]:
        try:
            here = os.listdir(where)
        except OSError:
            here = []
        spelled = wanted
        if wanted not in here:
            for candidate in sorted(here):
                if candidate.lower() == wanted.lower():
                    spelled = candidate
                    break
        found.append(spelled)
        where = os.path.join(where, spelled)
    return "/".join(found) if found else name


def _entry_files(base_root: str, name: str) -> List[str]:
    """The names of every entry file in one folder, in a fixed order."""
    folder = _folder(base_root, name)
    if not os.path.isdir(folder):
        return []
    return sorted(
        item for item in os.listdir(folder) if item.endswith(".md")
    )


def _still_older_inside(base_root: str) -> bool:
    """Whether any entry in the folder written today still carries the older words.

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


def _older_documents(base_root: str) -> List[Tuple[str, str]]:
    """Every document still at its older path, as (older path, current path)."""
    found = []
    for older, current in constants.LEGACY_DOCUMENT_PATHS:
        real = real_name_of(base_root, older)
        if os.path.lexists(_full(base_root, real)):
            found.append((real, current))
    segments = real_name_of(base_root, constants.LEGACY_SEGMENTS_DIR)
    folder = _full(base_root, segments)
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".md"):
                continue
            if not os.path.lexists(os.path.join(folder, name)):
                continue
            found.append(
                (segments + "/" + name, constants.SEGMENTS_DIR + "/" + name)
            )
    return found


def _older_records(base_root: str) -> List[str]:
    """Every record still in the older folder, as paths spelled the disk's way."""
    older = real_name_of(base_root, constants.LEGACY_CORRECTIONS_DIR)
    return [older + "/" + name for name in _entry_files(base_root, older)]


def needed(base_root: str) -> bool:
    """Whether anything about how this base is laid out is unfinished.

    Four things count: a context change in an older folder, a record in the
    older folder, a document at its older path, and a context change already
    moved whose settings were never rewritten, which is the state a run that
    stopped between its saved pieces of work leaves behind. Only the last
    opens any file, and only files in the folder written today.
    """
    for folder in constants.OLDER_CHANGES_DIRS:
        if _entry_files(base_root, real_name_of(base_root, folder)):
            return True
    if _older_records(base_root):
        return True
    if _older_documents(base_root):
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

    There is only ever one offer. It takes a base from wherever it starts,
    on the folder the rename left or on the one before it, all the way to the
    current layout, so nobody is asked twice about what is one move to them.
    """
    if not needed(base_root):
        return OFFER_NONE
    if _put_off_until(base_id, today or state.today()):
        return OFFER_NONE
    runner = runner_or_default(git)
    if _ready_to_write(base_root, runner) is not None:
        return OFFER_NONE
    _plan, refused = _prevalidate(base_root)
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


# --- Where each older path goes ---------------------------------------------


KIND_ENTRY = "entry"
KIND_RECORD = "record"
KIND_DOCUMENT = "document"


def _inside_one_folder(lowered: str, folder: str) -> Optional[int]:
    """Where the file name starts, when a path is a file directly in a folder."""
    prefix = folder + "/"
    if not lowered.startswith(prefix):
        return None
    rest = lowered[len(prefix) :]
    if not rest or "/" in rest:
        return None
    return len(prefix)


def destination_of(source: str) -> Optional[Tuple[str, str]]:
    """Where a file at an older path belongs today, and what kind of file it is.

    The folders are compared without letter case, because the disk does not
    tell two spellings of one folder apart and a note records the one git
    holds. The file's own name is kept exactly as it is.
    """
    text = str(source or "")
    lowered = text.lower()
    for folder in constants.OLDER_CHANGES_DIRS:
        start = _inside_one_folder(lowered, folder)
        if start is not None and lowered.endswith(".md"):
            return constants.CHANGES_DIR + "/" + text[start:], KIND_ENTRY
    start = _inside_one_folder(lowered, constants.LEGACY_CORRECTIONS_DIR)
    if start is not None and lowered.endswith(".md"):
        return constants.CORRECTIONS_DIR + "/" + text[start:], KIND_RECORD
    for older, current in constants.LEGACY_DOCUMENT_PATHS:
        if lowered == older:
            return current, KIND_DOCUMENT
    start = _inside_one_folder(lowered, constants.LEGACY_SEGMENTS_DIR)
    if start is not None and lowered.endswith(".md"):
        return constants.SEGMENTS_DIR + "/" + text[start:], KIND_DOCUMENT
    return None


def _is_an_older_placeholder(relative: str) -> bool:
    lowered = str(relative or "").lower()
    for folder in constants.LEGACY_TEMPLATE_FOLDERS + (constants.LEGACY_SEGMENTS_DIR,):
        if lowered == folder + "/" + constants.PLACEHOLDER_NAME:
            return True
    return False


def _is_an_added_placeholder(relative: str) -> bool:
    return relative in [
        folder + "/" + constants.PLACEHOLDER_NAME
        for folder in constants.LAYOUT_EMPTY_FOLDERS
    ]


# --- Checking before anything is written --------------------------------------


class _Move(object):
    """One file the move carries, from where it is to where it belongs."""

    __slots__ = ("source", "destination", "kind", "entry_id")

    def __init__(self, source, destination, kind, entry_id=None):
        self.source = source
        self.destination = destination
        self.kind = kind
        self.entry_id = entry_id

    def __repr__(self) -> str:
        return "_Move(%r -> %r)" % (self.source, self.destination)


class _Plan(object):
    """Everything one run will do, worked out before anything is written."""

    __slots__ = (
        "moves",
        "drops",
        "gone",
        "rewrites",
        "map_texts",
        "owner_texts",
        "added",
        "stack_text",
        "record_path",
        "record_text",
    )

    def __init__(self):
        self.moves: List[_Move] = []
        # Older copies of a file that already sits at its new place saying
        # the same thing, taken away in change one.
        self.drops: List[str] = []
        # Placeholders of older folders the move leaves holding nothing else.
        self.gone: List[str] = []
        # Paths whose settings change two rewrites, as they will be after the
        # move, in a fixed order.
        self.rewrites: List[str] = []
        # The map before and after its paragraph is brought up to date, when
        # it is.
        self.map_texts: Optional[Tuple[str, str]] = None
        # The ownership list before and after its rules follow the move.
        self.owner_texts: Optional[Tuple[str, str]] = None
        # The placeholders of the folders the current layout adds.
        self.added: List[str] = []
        # The starter source map, when the base has none (finding 12).
        self.stack_text: Optional[str] = None
        # Where the dated record goes, a name nothing already holds, and what
        # it says (finding 2).
        self.record_path: Optional[str] = None
        self.record_text: Optional[str] = None

    @property
    def has_work(self) -> bool:
        return bool(self.moves or self.drops or self.rewrites)

    def counts(self) -> Dict[str, int]:
        found = {KIND_DOCUMENT: 0, KIND_ENTRY: 0, KIND_RECORD: 0}
        for move in self.moves:
            found[move.kind] += 1
        return found


class _Survey(object):
    """Every context change the three folders hold, read once, with its problems."""

    __slots__ = ("folders", "problems", "twice", "misnamed")

    def __init__(self):
        # {folder: {entry id: (file name, the entry, what it says as values)}}
        self.folders: Dict[str, Dict[str, Tuple[str, object, tuple]]] = {}
        self.problems: List[Tuple[str, str]] = []
        # (entry id, one file name, the other) for an identifier two files in
        # one folder both claim while saying different things.
        self.twice: List[Tuple[str, str, str]] = []
        # (path, the identifier inside it) for a file named after something
        # other than the change it holds.
        self.misnamed: List[Tuple[str, str]] = []


def _survey(base_root: str) -> "_Survey":
    found = _Survey()
    for folder_name in constants.ALL_CHANGES_DIRS:
        real = real_name_of(base_root, folder_name)
        into = found.folders.setdefault(folder_name, {})
        for name in _entry_files(base_root, real):
            relative = real + "/" + name
            # Read exactly, because these are the bytes the rename will work
            # on. Reading the ordinary way translates line endings, which is
            # how a file the rename could not handle used to pass the survey
            # and then fail with the move already underway.
            text = read_text_exactly(os.path.join(_folder(base_root, real), name))
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
            into[entry.id] = (real + "/" + name, entry, said)
    return found


def _same_bytes(base_root: str, one: str, other: str) -> bool:
    first = read_text_exactly(_full(base_root, one))
    second = read_text_exactly(_full(base_root, other))
    return first is not None and second is not None and first == second


def _prevalidate(
    base_root: str, today: Optional[datetime.date] = None
) -> Tuple[Optional["_Plan"], Optional[Result]]:
    """Read everything first, and refuse before a single file is touched.

    What stops a move: a file that cannot be read at all, because moving a
    file nobody can read is moving a problem somewhere new; one identifier
    written in two folders saying two different things, because picking one
    of them is a decision about the person's own words that nothing here is
    entitled to make; and a file already sitting where another would move to
    and saying something different, which the move would otherwise have to
    overwrite. Nothing here ever overwrites.
    """
    found = _survey(base_root)
    if found.problems:
        relative, _code = found.problems[0]
        return None, _refused(
            CODE_UNREADABLE_ENTRY, UNREADABLE_ENTRY % _named(relative)
        )
    if found.twice:
        entry_id, _one, _other = sorted(found.twice)[0]
        return None, _refused(
            CODE_TWICE_IN_ONE_FOLDER, TWICE_IN_ONE_FOLDER % entry_id
        )
    if found.misnamed:
        _relative, entry_id = sorted(found.misnamed)[0]
        return None, _refused(
            CODE_NAME_IS_NOT_THE_ID, NAME_IS_NOT_THE_ID % entry_id
        )

    plan = _Plan()
    current = found.folders.get(constants.CHANGES_DIR, {})
    every_id = set()
    for folder_name in constants.ALL_CHANGES_DIRS:
        every_id.update(found.folders.get(folder_name, {}).keys())
    for entry_id in sorted(every_id):
        copies = [
            found.folders[folder_name][entry_id]
            for folder_name in constants.ALL_CHANGES_DIRS
            if entry_id in found.folders.get(folder_name, {})
        ]
        if any(copy[2] != copies[0][2] for copy in copies[1:]):
            return None, _refused(CODE_IN_BOTH_FOLDERS, SAME_CHANGE_TWICE % entry_id)
        older = [
            found.folders[folder_name][entry_id]
            for folder_name in constants.OLDER_CHANGES_DIRS
            if entry_id in found.folders.get(folder_name, {})
        ]
        if entry_id in current:
            plan.drops.extend(copy[0] for copy in older)
            continue
        # The newest older copy moves, because it needs the least rewriting,
        # and any other older copy of the same change goes. They say the same
        # thing, which the check just above established.
        moving = older[0]
        destination = constants.CHANGES_DIR + "/" + moving[0].split("/")[-1]
        if os.path.lexists(_full(base_root, destination)):
            return None, _refused(
                CODE_DESTINATION_TAKEN, DESTINATION_TAKEN % _named(destination)
            )
        plan.moves.append(_Move(moving[0], destination, KIND_ENTRY, entry_id))
        plan.drops.extend(copy[0] for copy in older[1:])

    for source in _older_records(base_root):
        destination, _kind = destination_of(source)
        if read_text_exactly(_full(base_root, source)) is None:
            return None, _refused(CODE_UNREADABLE_ENTRY, UNREADABLE_ENTRY % _named(source))
        if os.path.lexists(_full(base_root, destination)):
            if _same_bytes(base_root, source, destination):
                plan.drops.append(source)
                continue
            return None, _refused(
                CODE_DESTINATION_TAKEN, DESTINATION_TAKEN % _named(destination)
            )
        plan.moves.append(_Move(source, destination, KIND_RECORD))

    for source, destination in _older_documents(base_root):
        if read_text_exactly(_full(base_root, source)) is None:
            return None, _refused(CODE_UNREADABLE_ENTRY, UNREADABLE_ENTRY % _named(source))
        if os.path.lexists(_full(base_root, destination)):
            if _same_bytes(base_root, source, destination):
                plan.drops.append(source)
                continue
            return None, _refused(
                CODE_DOCUMENT_TAKEN, DOCUMENT_TAKEN % _named(destination)
            )
        plan.moves.append(_Move(source, destination, KIND_DOCUMENT))

    seen = {}
    for move in plan.moves:
        folded = move.destination.lower()
        if folded in seen:
            return None, _refused(
                CODE_DESTINATION_TAKEN, DESTINATION_TAKEN % _named(move.destination)
            )
        seen[folded] = move
    leaving = set(move.source for move in plan.moves) | set(plan.drops)
    plan.gone = _placeholders_left_alone(base_root, leaving)

    for move in plan.moves:
        if move.kind != KIND_ENTRY:
            continue
        text = read_text_exactly(_full(base_root, move.source)) or ""
        if formats.rewritten_safely(text) != text:
            plan.rewrites.append(move.destination)
    for entry_id, (relative, _entry, _said) in sorted(current.items()):
        text = read_text_exactly(_full(base_root, relative)) or ""
        if formats.rewritten_safely(text) != text:
            plan.rewrites.append(relative)

    if plan.has_work:
        plan.map_texts = _map_brought_up_to_date(base_root)
        plan.owner_texts = _owners_brought_up_to_date(base_root)
        plan.added = [
            folder + "/" + constants.PLACEHOLDER_NAME
            for folder in constants.LAYOUT_EMPTY_FOLDERS
            if not _holds_anything(base_root, folder)
        ]
        if not os.path.lexists(_full(base_root, constants.STACK_PATH)):
            plan.stack_text = _stack_text(base_root)
        day = today or state.today()
        pairs = [(move.source, move.destination) for move in plan.moves]
        plan.record_text = _record_for(pairs, plan.rewrites, plan.drops, day)
        plan.record_path = _free_record_path(
            base_root,
            _record_name(day, pairs, plan.rewrites, plan.drops),
            plan.record_text,
        )
    return plan, None


def _free_record_path(base_root: str, name: str, text: str) -> str:
    """A path for the dated record that holds nothing, or holds exactly it.

    The name is worked out from the day and from what moved, so the same
    move on the same day works out the same name, and a file somebody put
    there by hand, or an earlier record, may already sit at it. That file is
    never written over: the next free name is used instead (Astra's review of
    Unit 1.5b, finding 2), and the note records the one that was used.
    """
    stem = name[: -len(".md")]
    for number in range(0, 1000):
        candidate = constants.CORRECTIONS_DIR + "/" + (
            name if number == 0 else "%s-%d.md" % (stem, number + 1)
        )
        full = _full(base_root, candidate)
        if not os.path.lexists(full):
            return candidate
        if read_text_exactly(full) == text:
            return candidate
    raise ValidationError(
        "there is no free name for the record of the move", code=CODE_DESTINATION_TAKEN
    )


def _stack_text(base_root: str) -> str:
    """The starter source map a fresh base gets, with this base's owner on it.

    It is the plugin's own template, so a moved base and a fresh one hold the
    same file. The owner is the one the map names, which is the owner every
    other document in the base was given when the base was made.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(
        os.path.dirname(os.path.dirname(here)),
        "templates",
        "company-base",
        "access",
        "stack.md",
    )
    text = read_text_exactly(template) or ""
    owner_line = None
    map_text = read_text_exactly(_full(base_root, constants.MAP_PATH)) or ""
    for line in map_text.split("\n")[1:40]:
        if line.startswith("owner:"):
            owner_line = line.rstrip("\r")
            break
        if line.strip() == "---":
            break
    placeholder = "owner: " + constants.OWNER_PLACEHOLDER_EMAIL
    if owner_line and placeholder in text:
        text = text.replace(placeholder, owner_line, 1)
    return text


# The ownership list's rules, followed from each older folder or document to
# where the move puts it. A rule naming something the move does not touch is
# left exactly as it is.
_OWNED_FOLDER_MOVES = (
    (constants.LEGACY_CORRECTIONS_DIR + "/", constants.CORRECTIONS_DIR + "/"),
    (constants.WORK_CHANGES_DIR + "/", constants.CHANGES_DIR + "/"),
    (constants.LEGACY_CHANGES_DIR + "/", constants.CHANGES_DIR + "/"),
    (constants.LEGACY_SEGMENTS_DIR + "/", constants.SEGMENTS_DIR + "/"),
)
# The parts of the current layout the template has the owner review, which a
# moved base gains with the owners its records rule already names.
_OWNED_NEW_PARTS = (
    constants.LESSONS_DIR + "/**",
    constants.ACCESS_DIR + "/**",
    constants.SKILLS_DIR + "/**",
    constants.STANDARDS_DIR + "/**",
)
_OLDER_OWNERS_COMMENT = (
    "# Nothing under work/changes or work/confirmations is listed, because those"
)
_CURRENT_OWNERS_COMMENT = (
    "# Nothing under learning/changes or work/confirmations is listed, because those"
)


def _owner_rule_moved(pattern: str) -> str:
    lead = "/" if pattern.startswith("/") else ""
    bare = pattern[len(lead):]
    for older, current in _OWNED_FOLDER_MOVES:
        if bare.startswith(older):
            return lead + current + bare[len(older):]
        if bare == older.rstrip("/"):
            return lead + current.rstrip("/")
    for older, current in constants.LEGACY_DOCUMENT_PATHS:
        if bare == older:
            return lead + current
    return pattern


# The only shapes of rule that cover the whole older folder of records. A rule
# for one record, or for some of them, is an exception somebody wrote, and it
# never decides who owns anything else.
_BROAD_RECORDS_RULES = (
    constants.LEGACY_CORRECTIONS_DIR,
    constants.LEGACY_CORRECTIONS_DIR + "/",
    constants.LEGACY_CORRECTIONS_DIR + "/*",
    constants.LEGACY_CORRECTIONS_DIR + "/**",
)


def _owners_moved(text: str) -> str:
    """The ownership list with each rule following the move (finding 5).

    Each rule naming an older folder or document names where it lives now,
    with exactly the owners it had, in the place it had. Every other rule is
    left as it is.

    The parts of the layout a fresh base has the owner review are added with
    the owners of the broad rule for the older folder of records, and only
    that rule: a rule for one record is an exception, and there are no
    defaults at all when there is no broad rule. They go in before every rule
    already there, because in this list the last rule that matches a file
    wins, and a rule somebody wrote by hand, such as one giving the source
    map to a security reviewer, has to keep winning (the confirmation pass
    on Unit 1.5b, finding 2).
    """
    lines = text.split("\n")
    broad_owners = None
    patterns = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        bare = parts[0].lstrip("/")
        patterns.add(_owner_rule_moved(parts[0]).lstrip("/"))
        if bare in _BROAD_RECORDS_RULES and len(parts) > 1:
            broad_owners = parts[1:]
    out = []
    first_rule = None
    for line in lines:
        stripped = line.strip()
        if line.rstrip("\r") == _OLDER_OWNERS_COMMENT:
            out.append(_CURRENT_OWNERS_COMMENT)
            continue
        if not stripped or stripped.startswith("#"):
            out.append(line)
            continue
        if first_rule is None:
            first_rule = len(out)
        parts = line.split()
        moved = _owner_rule_moved(parts[0])
        if moved != parts[0]:
            line = line.replace(parts[0], moved, 1)
        out.append(line)
    if broad_owners is not None and first_rule is not None:
        extra = [
            "%s %s" % (part, " ".join(broad_owners))
            for part in _OWNED_NEW_PARTS
            if part not in patterns
        ]
        out[first_rule:first_rule] = extra
    return "\n".join(out)


def _owners_brought_up_to_date(base_root: str) -> Optional[Tuple[str, str]]:
    text = read_text_exactly(_full(base_root, constants.CODEOWNERS_PATH))
    if text is None:
        return None
    after = _owners_moved(text)
    if after == text:
        return None
    return text, after


def _holds_anything(base_root: str, folder: str) -> bool:
    where = _folder(base_root, folder)
    if not os.path.isdir(where):
        return os.path.lexists(where)
    return bool(os.listdir(where))


def _placeholders_left_alone(base_root: str, leaving) -> List[str]:
    """The placeholders of older folders the move leaves with nothing else in.

    A folder still holding anything at all after the move, a note of the
    person's own or a file GTM Base never wrote, keeps its placeholder and is
    left exactly as it is.
    """
    gone = []
    folders = constants.LEGACY_TEMPLATE_FOLDERS + (constants.LEGACY_SEGMENTS_DIR,)
    for folder_name in folders:
        real = real_name_of(base_root, folder_name)
        where = _folder(base_root, real)
        if not os.path.isdir(where):
            continue
        placeholder = real + "/" + constants.PLACEHOLDER_NAME
        if not os.path.isfile(_full(base_root, placeholder)):
            continue
        left = []
        for top, _folders, files in os.walk(where):
            for name in files:
                relative = os.path.relpath(os.path.join(top, name), base_root)
                relative = relative.replace(os.sep, "/")
                if relative not in leaving:
                    left.append(relative)
        if left == [placeholder]:
            gone.append(placeholder)
    return sorted(gone)


def _where_section(text: str) -> Optional[Tuple[int, int]]:
    """Where the paragraph under the map's heading starts and ends, stripped."""
    lines = text.split("\n")
    offset = 0
    start = None
    for index, line in enumerate(lines):
        if start is None and line.rstrip("\r") == MAP_WHERE_HEADING:
            start = offset + len(line) + 1
        elif start is not None and line.startswith("#"):
            end = offset
            break
        offset += len(line) + 1
    else:
        end = len(text)
    if start is None or start > len(text):
        return None
    body = text[start:end]
    stripped = body.strip()
    if not stripped:
        return None
    first = start + body.index(stripped)
    return first, first + len(stripped)


def _map_brought_up_to_date(base_root: str) -> Optional[Tuple[str, str]]:
    """The map before and after, when its paragraph is still one GTM Base wrote."""
    text = read_text_exactly(_full(base_root, constants.MAP_PATH))
    if text is None:
        return None
    span = _where_section(text)
    if span is None:
        return None
    first, last = span
    if text[first:last] not in MAP_WHERE_EARLIER:
        return None
    return text, text[:first] + MAP_WHERE_TODAY + text[last:]


# --- The note -----------------------------------------------------------------


def _journal_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), JOURNAL_FILE)


# Where the base stood, written the one way git writes it.
_SAVED_POINT_RE = re.compile(r"^[0-9a-f]{40}$")

# The only folders a path this run writes may sit in. The note is only ever
# about files this module writes or moves, and it writes nowhere else.
NOTE_PATH_PREFIXES = (
    constants.CHANGES_DIR + "/",
    constants.CORRECTIONS_DIR + "/",
    constants.CONTEXT_DIR + "/",
    constants.ACCESS_DIR + "/",
    constants.LESSONS_DIR + "/",
    constants.SKILLS_DIR + "/",
    constants.STANDARDS_DIR + "/",
)
# The same, for a note the release before this one left.
LEGACY_NOTE_PATH_PREFIXES = (
    constants.WORK_CHANGES_DIR + "/",
    constants.LEGACY_CORRECTIONS_DIR + "/",
)
# The only folders a file this run moves may have come from, compared
# without letter case, and the one folder the release before this one moved
# files from.
MOVED_FROM_PREFIXES = tuple(
    folder + "/" for folder in constants.OLDER_CHANGES_DIRS
) + (constants.LEGACY_CORRECTIONS_DIR + "/", constants.CONTEXT_DIR + "/")
LEGACY_MOVED_FROM_PREFIXES = (constants.LEGACY_CHANGES_DIR + "/",)


def _inside(base_root: str, relative: str) -> bool:
    """Whether a path still lands inside this base once every link is followed."""
    real_base = os.path.realpath(base_root)
    settled = os.path.realpath(_full(base_root, relative))
    return settled == real_base or settled.startswith(real_base + os.sep)


def _legacy_destination_of(source: str) -> Optional[str]:
    """Where the release before this one moved a file: `work/changes`, and only there."""
    lowered = str(source or "").lower()
    start = _inside_one_folder(lowered, constants.LEGACY_CHANGES_DIR)
    if start is None or not lowered.endswith(".md"):
        return None
    return constants.WORK_CHANGES_DIR + "/" + str(source)[start:]


def _checked_journal(base_id: str, base_root: str):
    """The note, with every value in it checked, or the reason it was refused.

    The note is a file on the disk like any other, so nothing in it is
    believed on sight. Every value is checked to the same bar the note behind
    a local approval is held to: the base it is about, the saved point it
    started from written the one way git writes one, a path this module really
    writes for every path it will put back, an older path this module really
    moves for every file it moved, the one place that file belongs for where
    it says it went, a hash we could have written for each, and every one of
    them still landing inside this base once the links are followed.

    A note that fails any of those is not finished and not put back. The run
    refuses and touches nothing, because a note we cannot read is a run we
    cannot safely take apart.

    The note comes back with every file it moved carrying the place it went,
    which a note from the release before this one did not record and which is
    filled in here, the one place it went.
    """
    payload = read_json(_journal_path(base_id))
    if payload is None:
        return None, None
    if not isinstance(payload, dict):
        return None, "the note is not one we wrote"
    schema = payload.get("schema")
    if schema not in (JOURNAL_SCHEMA, LEGACY_JOURNAL_SCHEMA):
        return None, "the note is not one we wrote"
    legacy = schema == LEGACY_JOURNAL_SCHEMA
    recorded = str(payload.get("base_root") or "")
    if not recorded or os.path.realpath(recorded) != os.path.realpath(base_root):
        return None, "the note is about another base"
    if not _SAVED_POINT_RE.match(str(payload.get("head") or "")):
        return None, "the note does not say where the base stood"
    subjects = payload.get("subjects")
    expected = list(LEGACY_SUBJECTS if legacy else SUBJECTS)
    if subjects is not None and list(subjects) != expected:
        return None, "the note names saved work we never write"
    payload["subjects"] = expected

    written_prefixes = LEGACY_NOTE_PATH_PREFIXES if legacy else NOTE_PATH_PREFIXES
    items = payload.get("paths")
    if not isinstance(items, list) or not items:
        return None, "the note lists no paths"
    for item in items:
        if not isinstance(item, dict):
            return None, "the note holds something that is not a path"
        relative = str(item.get("path") or "")
        try:
            if legacy or relative != constants.CODEOWNERS_PATH:
                paths.check_repo_path_syntax(relative, written_prefixes)
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        if not _a_path_we_write(relative, legacy):
            return None, "the note names a path we never write"
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
        if legacy:
            belongs = _legacy_destination_of(relative)
            moved_from = LEGACY_MOVED_FROM_PREFIXES
        else:
            placed = destination_of(relative)
            belongs = placed[0] if placed else None
            moved_from = MOVED_FROM_PREFIXES
        try:
            paths.check_repo_path_syntax(relative.lower(), moved_from)
            ids.check_content_hash(str(item.get("hash") or ""))
        except (PathError, ValueError, TypeError):
            return None, "the note names a path or a value we never write"
        if belongs is None:
            return None, "the note names a path we never move"
        went = item.get("to")
        if went is not None and str(went) != belongs:
            return None, "the note says a file went somewhere we never put it"
        item["to"] = belongs
        if not _inside(base_root, relative) or not _inside(base_root, belongs):
            return None, "the note names a path outside this base"

    went_to = set(str(item.get("to")) for item in came_from)
    for item in items:
        relative = str(item.get("path") or "")
        if legacy or _is_the_record(relative):
            continue
        if _one_file_in(relative, constants.CORRECTIONS_DIR) and relative not in went_to:
            return None, "the note names a path we never write"

    removed = payload.get("removed")
    if removed is None:
        removed = []
    if not isinstance(removed, list):
        return None, "the note lists what it removed in a shape we never write"
    for item in removed:
        relative = str(item or "")
        try:
            # The same shape check every other path in the note gets, so a
            # path that climbs out of its folder is never taken for one in it.
            paths.check_repo_path_syntax(
                relative.lower(),
                LEGACY_MOVED_FROM_PREFIXES if legacy else MOVED_FROM_PREFIXES,
            )
        except (PathError, ValueError, TypeError):
            return None, "the note names a path we never remove"
        if legacy:
            allowed = _legacy_destination_of(relative) is not None
        else:
            allowed = destination_of(relative) is not None or _is_an_older_placeholder(
                relative
            )
        if not allowed or not _inside(base_root, relative):
            return None, "the note names a path we never remove"
    payload["came_from"] = came_from
    payload["removed"] = removed
    return payload, None


# The names the dated record of a move is given, today and by the release
# before this one. A record is the one kind of file a run writes that is not
# a copy of something else, so it is recognised by its name.
_RECORD_NAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}-move-to-the-class-layout-[0-9a-f]{8}(?:-[0-9]{1,3})?\.md$"
)
_LEGACY_RECORD_NAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}-move-to-work-changes-[0-9a-f]{8}\.md$"
)


def _one_file_in(relative: str, folder: str) -> Optional[str]:
    prefix = folder + "/"
    if not relative.startswith(prefix):
        return None
    rest = relative[len(prefix) :]
    if not rest or "/" in rest or not rest.endswith(".md"):
        return None
    return rest


def _is_the_record(relative: str, legacy: bool = False) -> bool:
    """Whether a path is the dated record a run of the move writes about itself."""
    if legacy:
        name = _one_file_in(relative, constants.LEGACY_CORRECTIONS_DIR)
        return bool(name and _LEGACY_RECORD_NAME_RE.match(name))
    name = _one_file_in(relative, constants.CORRECTIONS_DIR)
    return bool(name and _RECORD_NAME_RE.match(name))


def _a_path_we_write(relative: str, legacy: bool) -> bool:
    """Whether this run could have written this path, and nothing wider.

    A note is a file on the disk like any other. A note naming a path this
    module never writes could otherwise have a recovery put back, or take
    away, a file that is somebody's own, so the list is exact: a context
    change in the folder written today, a record the move carried or the one
    it writes about itself, a document at the place the current layout keeps
    it, the map, and the placeholders the current layout adds.
    """
    if legacy:
        return bool(
            _one_file_in(relative, constants.WORK_CHANGES_DIR)
            or _is_the_record(relative, legacy=True)
        )
    if _one_file_in(relative, constants.CHANGES_DIR):
        return True
    if _one_file_in(relative, constants.CORRECTIONS_DIR):
        return True
    if relative in (constants.MAP_PATH, constants.CODEOWNERS_PATH, constants.STACK_PATH):
        return True
    if relative in [current for _older, current in constants.LEGACY_DOCUMENT_PATHS]:
        return True
    if _one_file_in(relative, constants.SEGMENTS_DIR):
        return True
    return _is_an_added_placeholder(relative)


def _is_legacy(journal: dict) -> bool:
    return journal.get("schema") == LEGACY_JOURNAL_SCHEMA


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
            "subjects": list(SUBJECTS),
            "paths": list(plan),
            # Where each file was before the move, what it said there, and
            # where it went, so a run that stopped before anything was saved
            # can tell a file it moved away from one the person has edited
            # since.
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


def _allowed_hashes(journal: dict) -> Dict[str, set]:
    """Every path this run writes, with each value it may hold there."""
    wrote: Dict[str, set] = {}
    for item in journal.get("paths") or []:
        allowed = {str(item.get("hash"))}
        after = item.get("after_move")
        if after:
            allowed.add(str(after))
        wrote[str(item.get("path"))] = allowed
    return wrote


def _landed(base_root: str, journal: dict, saved, git: GitRunner) -> bool:
    """Whether any of this run's work is already saved, by it or by anybody."""
    if any(subject in saved for subject in journal.get("subjects") or []):
        return True
    return _move_has_landed(base_root, journal, git)


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
    wrote = _allowed_hashes(journal)
    for item in came_from:
        relative = str(item.get("path"))
        if _in_head(base_root, relative, git):
            return False
        went = str(item.get("to"))
        allowed = wrote.get(went)
        if not allowed:
            return False
        landed = _head_text(base_root, went, git)
        if landed is None or ids.exact_hash(landed) not in allowed:
            return False
    return True


# --- Refusing on a tree somebody is working in --------------------------------


def _ready_to_write(base_root: str, git: GitRunner) -> Optional[Result]:
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        return _refused(CODE_NOT_DEFAULT_BRANCH, NOT_ON_MAIN)
    # The shared look, which leaves out the files the computer made on its
    # own. A Finder file was enough to refuse the move before 0.3.2.
    status = unsaved.look(base_root, git)
    if not status.ran:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    if not status.clean:
        return _refused(
            CODE_UNSAVED_EDITS,
            unsaved.refusal(UNSAVED_EDITS_NAMED, UNSAVED_EDITS, status),
        )
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
        # because undoing the other half would leave that file nowhere.
        self.unrecoverable: List[str] = []


def _sort_out(base_root: str, journal: dict, git: GitRunner) -> "_Sorted":
    """Work out what each path in the note is, without changing any of them."""
    sorted_out = _Sorted()

    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        current = read_text_exactly(_full(base_root, relative))
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
        current = read_text_exactly(_full(base_root, relative))
        if current is None:
            # The move took it away. It is only ours to put back when the base
            # still holds it in what was last saved. A file that is not in
            # what was last saved cannot be put back by anything, and undoing
            # the copy the move made would then leave that file nowhere at
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

    for item in journal.get("removed") or []:
        relative = str(item)
        current = read_text_exactly(_full(base_root, relative))
        if current is None:
            continue
        # Still on the disk, so the run had not taken it away yet. Putting it
        # back from what was saved is only safe while it still says what was
        # saved; anything else is somebody's own work.
        saved_text = _head_text(base_root, relative, git)
        if saved_text is None or ids.exact_hash(saved_text) != ids.exact_hash(current):
            sorted_out.theirs.append(relative)
    return sorted_out


def _still_as_saved_or_gone(base_root: str, relative: str, git: GitRunner) -> bool:
    """Whether bringing this path back from what was saved loses nothing.

    It is safe when nothing is on the disk there, or when what is there is
    exactly what was saved. Anything else is somebody's own words.
    """
    current = read_text_exactly(_full(base_root, relative))
    if current is None and not os.path.lexists(_full(base_root, relative)):
        return True
    saved_text = _head_text(base_root, relative, git)
    return (
        current is not None
        and saved_text is not None
        and ids.exact_hash(current) == ids.exact_hash(saved_text)
    )


def _is_an_entry_path(relative: str) -> bool:
    """Whether this path holds a context change rather than a record of one."""
    lowered = relative.lower()
    return any(
        lowered.startswith(folder + "/") for folder in constants.ALL_CHANGES_DIRS
    )


def _source_of(journal: dict, relative: str) -> Optional[str]:
    """Where the file this run moved to this path came from, or None."""
    for item in journal.get("came_from") or []:
        if str(item.get("to")) == relative:
            return str(item.get("path"))
    return None


def _another_copy_is_there(base_root, relative, journal, sorted_out, git) -> bool:
    """Whether some other readable copy of this file exists right now.

    The rule every recovery obeys: nothing is deleted unless a copy of that
    same thing is confirmed to be somewhere else at that moment, either on
    the disk or in what was last saved. A deletion that cannot say yes to
    this is not a deletion this is allowed to make.

    The rule is about what cannot be got back: a context change, a document,
    and a record somebody else wrote. The dated record this run writes about
    its own work, and a placeholder it added, are not: they say what the run
    did, the run is being undone, and leaving them behind is what wedged the
    next run rather than what saved anything.
    """
    source = _source_of(journal, relative)
    if source is None and (
        _is_the_record(relative, _is_legacy(journal))
        or _is_an_added_placeholder(relative)
        or relative == constants.STACK_PATH
    ):
        return True
    places = []
    if source is not None:
        places.append(source)
    if _is_an_entry_path(relative):
        name = relative.split("/")[-1]
        for folder in constants.ALL_CHANGES_DIRS:
            places.append(real_name_of(base_root, folder) + "/" + name)
            places.append(folder + "/" + name)
    for where in places:
        if where == relative:
            continue
        on_disk = read_text_exactly(_full(base_root, where))
        if on_disk is not None:
            if not _is_an_entry_path(where):
                return True
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
        return THEIR_WORDS % unsaved.plain_name(
            sorted(sorted_out.theirs)[0], base_root
        )
    if sorted_out.unrecoverable:
        return CANNOT_PUT_BACK % _named(sorted(sorted_out.unrecoverable)[0])

    # Restoring comes first. Undoing first leaves a moment in which a file is
    # in neither place, and a run killed in that moment leaves it there.
    # Whatever the run took away outright comes back in the same breath.
    bringing_back = list(sorted_out.restore) + [
        str(relative)
        for relative in (journal.get("removed") or [])
        if _in_head(base_root, str(relative), git)
    ]
    for relative in bringing_back:
        if not _still_as_saved_or_gone(base_root, relative, git):
            return THEIR_WORDS % unsaved.plain_name(relative, base_root)
    if bringing_back:
        result = git.run(
            ["checkout", "HEAD", "--"] + [str(one) for one in bringing_back],
            cwd=base_root,
        )
        if not result.ok:
            return COULD_NOT_SAVE

    for relative, in_head in sorted_out.undo:
        full = _full(base_root, relative)
        current = read_text_exactly(full)
        if current is None:
            continue
        # Asked again, right now. Somebody may have saved this file between
        # the classification above and this moment, and their save must not
        # be undone by a decision made about what was there before it.
        if ids.exact_hash(current) != _what_this_run_wrote(journal, relative):
            return THEIR_WORDS % unsaved.plain_name(relative, base_root)
        try:
            if in_head:
                git.check(["checkout", "HEAD", "--", relative], cwd=base_root)
                continue
            if not _another_copy_is_there(base_root, relative, journal, sorted_out, git):
                return CANNOT_PUT_BACK % _named(relative)
            git.check(
                ["rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", relative],
                cwd=base_root,
            )
            if not _still_what_this_run_wrote(base_root, journal, relative):
                return THEIR_WORDS % unsaved.plain_name(relative, base_root)
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
    # The shared look names paths exactly as they are, so a path with an
    # accent or a space in it is compared as itself rather than as git's
    # quoted form of it, and it leaves out the files the computer made.
    status = unsaved.look(base_root, git)
    if not status.ran or status.entries is None:
        return COULD_NOT_SAVE
    for _letters, named in status.entries:
        for piece in named:
            if piece in touched:
                return COULD_NOT_SAVE
            for one in touched:
                if piece.endswith("/") and one.startswith(piece):
                    return COULD_NOT_SAVE
    return None


def _still_what_this_run_wrote(base_root: str, journal: dict, relative: str) -> bool:
    """Whether a path holds, right now, exactly what this run wrote there."""
    current = read_text_exactly(_full(base_root, relative))
    if current is None:
        return False
    return ids.exact_hash(current) == _what_this_run_wrote(journal, relative)


def _what_this_run_wrote(journal: dict, relative: str):
    """The hashes this run recorded for one path, as a set to compare against."""
    return _OneOf(_allowed_hashes(journal).get(relative, set()))


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


def _rewritten(relative: str, text: str) -> str:
    """One file's own bytes, with only what change two changes changed.

    For a context change that is its renamed settings, through the check that
    reads the answer back, so nothing is ever written that the reader cannot
    read back to the values it read before. For the map it is the one
    paragraph about where things live, and only when it is still one GTM Base
    wrote. This is the one place either happens, so what the note records and
    what the run writes can never say two different things.
    """
    if relative == constants.CODEOWNERS_PATH:
        return _owners_moved(text)
    if relative == constants.MAP_PATH:
        span = _where_section(text)
        if span is None:
            return text
        first, last = span
        if text[first:last] not in MAP_WHERE_EARLIER:
            return text
        return text[:first] + MAP_WHERE_TODAY + text[last:]
    return formats.rewritten_safely(text)


def _in_words(number: int, kind: str) -> str:
    one, many = KIND_WORDS[kind]
    return "%s %s" % (counted(number), one if number == 1 else many)


def _what_moves(counts: Dict[str, int]) -> str:
    """What a move carries, the way a person says it."""
    parts = [
        _in_words(counts[kind], kind)
        for kind in (KIND_DOCUMENT, KIND_ENTRY, KIND_RECORD)
        if counts.get(kind)
    ]
    if not parts:
        return _in_words(0, KIND_DOCUMENT)
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _record_touches(moves: List[Tuple[str, str]], rewrites, drops) -> List[str]:
    touched = [went for _came, went in moves]
    for relative in list(rewrites) + list(drops):
        if relative not in touched and relative not in (
            constants.MAP_PATH,
            constants.CODEOWNERS_PATH,
        ):
            touched.append(relative)
    return touched


def _record_for(moves, rewrites, drops, today: datetime.date) -> str:
    """The dated record of the move, in the shape `report.py` reads.

    It is a record like every other one, so the summary can parse it rather
    than skipping it, and its class is `other`, because the move found nothing
    wrong and changed no rule. It names no context change, so it settles
    nothing: the documents it moved are settled exactly as they were before.
    """
    touched = _record_touches(moves, rewrites, drops)
    counts = {KIND_DOCUMENT: 0, KIND_ENTRY: 0, KIND_RECORD: 0}
    for came, _went in moves:
        placed = destination_of(came)
        if placed:
            counts[placed[1]] += 1
    staging = ids.staging_id("layout-move", sorted(touched)[0], "move", 0)
    correction = formats.CorrectionsFile(
        kind="correction",
        date=today.isoformat(),
        staging_id=staging,
        entry_id=None,
        source_id=None,
        intake_path="none",
        mode="none",
        third_party=False,
        content_hash=ids.content_hash("\n".join(sorted(touched))),
        correction_class="other",
        marker=marker_line(staging, None, None),
        touched_paths=touched,
        what_changed=LAYOUT_RECORD_WHAT_CHANGED % _what_moves(counts),
        why=LAYOUT_RECORD_WHY,
    )
    return correction.validate().render()


def _record_name(today: datetime.date, moves, rewrites, drops) -> str:
    """A name no earlier record can already have.

    A base can be moved twice on one day, because an older seat can write into
    an older folder between the two. What each move carried is what makes the
    second record a different record, so it is what names it.
    """
    stamp = ids.content_hash(
        "\n".join(sorted(_record_touches(moves, rewrites, drops)))
    )[:8]
    return "%s-move-to-the-class-layout-%s.md" % (today.isoformat(), stamp)


def _legacy_record_for(moved_names: List[str], today: datetime.date) -> str:
    """The record the release before this one wrote, word for word."""
    entry_ids = [name[: -len(".md")] for name in moved_names]
    first = entry_ids[0]
    paths_touched = [
        constants.WORK_CHANGES_DIR + "/" + name for name in moved_names
    ]
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
        what_changed=RECORD_WHAT_CHANGED % ", ".join(entry_ids),
        why=RECORD_WHY,
    )
    return correction.validate().render()


def _legacy_record_name(today: datetime.date, moved_names: List[str]) -> str:
    stamp = ids.content_hash(
        "\n".join(sorted(name[: -len(".md")] for name in moved_names))
    )[:8]
    return "%s-move-to-work-changes-%s.md" % (today.isoformat(), stamp)


def _plan_the_writes(base_root: str, plan: "_Plan", today: datetime.date) -> List[dict]:
    """Every path this run will write, with a hash of what it will write there.

    This is what lets a later run tell its own unfinished work from the
    person's edits: a path holding exactly this is ours to put back, and a
    path holding anything else is theirs to keep.
    """
    written = []
    for move in plan.moves:
        # Read exactly, because these are the bytes the run will put back on
        # the disk and the hashes a later run will recognise them by.
        was = read_text_exactly(_full(base_root, move.source)) or ""
        final = (
            _rewritten(move.destination, was)
            if move.destination in plan.rewrites
            else was
        )
        written.append(
            {
                "path": move.destination,
                "hash": ids.exact_hash(final),
                # What the file holds after the move and before the rewrite.
                # A run that stopped between the two leaves this on the disk,
                # and it is as much this module's own work as the other one.
                "after_move": ids.exact_hash(was),
            }
        )
    moved_to = set(move.destination for move in plan.moves)
    for relative in plan.rewrites:
        if relative in moved_to:
            continue
        was = read_text_exactly(_full(base_root, relative)) or ""
        written.append(
            {
                "path": relative,
                "hash": ids.exact_hash(_rewritten(relative, was)),
                "after_move": ids.exact_hash(was),
            }
        )
    for relative, texts in (
        (constants.MAP_PATH, plan.map_texts),
        (constants.CODEOWNERS_PATH, plan.owner_texts),
    ):
        if texts is None:
            continue
        before, after = texts
        written.append(
            {
                "path": relative,
                "hash": ids.exact_hash(after),
                "after_move": ids.exact_hash(before),
            }
        )
    written.append(
        {"path": plan.record_path, "hash": ids.exact_hash(plan.record_text)}
    )
    for placeholder in plan.added:
        written.append({"path": placeholder, "hash": ids.exact_hash("")})
    if plan.stack_text is not None:
        written.append(
            {"path": constants.STACK_PATH, "hash": ids.exact_hash(plan.stack_text)}
        )
    return written


def _came_from(base_root: str, plan: "_Plan") -> List[dict]:
    """Where each file was before the move, what it said there, and where it went.

    The path is spelled the way the disk really spells it. Most Macs do not
    tell `work/Decisions` from `work/decisions`, but git does, and a note
    recording the spelling git does not hold is a note whose every question
    about that path comes back no. That is what made a recovery believe it
    had nothing to put back while it went on deleting what it had moved.
    """
    rows = []
    for move in plan.moves:
        was = read_text_exactly(_full(base_root, move.source))
        rows.append(
            {
                "path": move.source,
                "hash": ids.exact_hash(was or ""),
                "to": move.destination,
            }
        )
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
    moves: List[Tuple[str, str]],
    taken_away: List[str],
    subject: str,
    git: GitRunner,
) -> None:
    """Change one: the files move and not one character of them changes.

    The move is saved on its own so that a later look at which change first
    added a file follows it through. `report.py` counts a catch by that look,
    and a move saved together with a rewrite is a file git reads as newly
    added, which would quietly drop the catch it belongs to.

    An older copy of a file already at its new place is taken away in this
    same saved change. It says exactly what the copy that stays says, which
    the check before this established, so nothing is lost by it going. So is
    the placeholder of an older folder the move leaves holding nothing else.
    """
    for came, went in moves:
        destination = os.path.dirname(_full(base_root, went))
        if not os.path.isdir(destination):
            os.makedirs(destination)
        git.check(["mv", came, went], cwd=base_root)
    for relative in taken_away:
        try:
            git.check(["rm", "-q", "-f", "--", relative], cwd=base_root)
        except GitError:
            if _is_an_older_placeholder(relative):
                # It was never saved, so taking it off the disk is the whole
                # of it.
                remove(_full(base_root, relative))
                continue
            raise
    _save(base_root, subject, git)
    _tidy_empty_older_folders(base_root)


def _tidy_empty_older_folders(base_root: str) -> None:
    """Take away the older folders the move left with nothing in them at all.

    Git keeps no folders, only files, so an older folder the move emptied is
    already gone from everything the base has saved. Left on the disk it is
    an empty folder with an older name, which is the one thing a person
    opening the base would read as the layout still being the old one. A
    folder holding anything at all is left exactly as it is.
    """
    folders = (constants.LEGACY_SEGMENTS_DIR,) + constants.LEGACY_TEMPLATE_FOLDERS
    for folder_name in folders:
        where = _folder(base_root, real_name_of(base_root, folder_name))
        try:
            if os.path.isdir(where) and not os.path.islink(where) and not os.listdir(where):
                os.rmdir(where)
        except OSError:
            continue


def _do_the_rewrite(
    base_root: str, rewrites: List[str], subject: str, git: GitRunner
) -> None:
    """Change two, the commit point: each file brought up to date where it is.

    Each file is read as it stands and written back with only what change two
    changes changed. Every other byte of it, the body included, is left
    exactly as the person wrote it.
    """
    written = []
    for relative in rewrites:
        full = _full(base_root, relative)
        current = read_text_exactly(full)
        if current is None:
            continue
        updated = _rewritten(relative, current)
        if updated != current:
            atomic_write_text(full, updated, mode=0o644, inside=base_root)
        # Staged whether or not it was written just now, because a run that
        # stopped after writing it and before saving it left it written and
        # not staged, and picking that run up has to save it all the same.
        written.append(relative)
    if not written:
        return
    git.check(["add", "--"] + written, cwd=base_root)
    _save(base_root, subject, git)


def _do_the_record(
    base_root: str,
    record_path: str,
    record_text: str,
    added: List[Tuple[str, str]],
    subject: str,
    git: GitRunner,
) -> None:
    """Change three: the dated record, and the files the current layout adds.

    Nothing is written over. The record's path was chosen to hold nothing
    or exactly this record, and each added file is written only where
    nothing is, which the check before finishing makes sure of.
    """
    full_record = _full(base_root, record_path)
    if read_text_exactly(full_record) != record_text:
        atomic_write_text(full_record, record_text, mode=0o644, inside=base_root)
    staged = [record_path]
    for relative, text in added:
        full = _full(base_root, relative)
        if not os.path.lexists(full):
            atomic_write_text(full, text, mode=0o644, inside=base_root)
        # Staged whether or not it was written just now, for the same reason
        # the rewrite stages every file it owns: a run that stopped after the
        # write and before the save left it on the disk and nowhere else.
        staged.append(relative)
    git.check(["add", "--"] + staged, cwd=base_root)
    _save(base_root, subject, git)


def _pieces_from_note(journal: dict):
    """What a stopped run meant to do, read back off its own note.

    It comes back as the moves as (from, to) pairs in the order they were
    made, the paths change two rewrites, the paths change one took away, and
    the placeholders change three adds. Nothing here reads a file, because
    what has to be done is exactly what was planned.
    """
    moves = [
        (str(item.get("path")), str(item.get("to")))
        for item in journal.get("came_from") or []
    ]
    rewrites = []
    added = []
    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        after = item.get("after_move")
        if after and str(after) != str(item.get("hash")):
            rewrites.append(relative)
        if _is_an_added_placeholder(relative) and str(item.get("hash")) == ids.exact_hash(""):
            added.append(relative)
        if relative == constants.STACK_PATH:
            added.append(relative)
    drops = [
        str(item)
        for item in journal.get("removed") or []
        if not _is_an_older_placeholder(str(item))
    ]
    return moves, rewrites, drops, added


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
        current = read_text_exactly(_full(base_root, relative))
        if current is None:
            continue
        if ids.exact_hash(current) not in allowed:
            return THEIR_WORDS % unsaved.plain_name(relative, base_root)

    moved_away = set(str(item.get("path")) for item in journal.get("came_from") or [])
    moved_away.update(str(item) for item in journal.get("removed") or [])
    # The shared look names paths exactly as they are, so a path with an
    # accent or a space in it is its own name here and not git's quoted form,
    # and a file the computer made on its own is nobody's words.
    status = unsaved.look(base_root, git)
    if not status.ran or status.entries is None:
        return COULD_NOT_SAVE
    for letters, named in status.entries:
        # A rename names two paths, and both belong to this run when this run
        # is the thing that moved it. A file sitting at a path this run moved
        # away from and never saved is new, though, and nobody's but the
        # person's: the shared look lists each one by its own name rather than
        # folding it into a new folder, so it is caught here by its letters.
        for piece in named:
            if piece in moved_away and letters != "??":
                continue
            for unexplained in _what_is_really_there(base_root, piece, ours):
                return THEIR_WORDS % unsaved.plain_name(unexplained, base_root)
    return None


def _what_is_really_there(base_root: str, named: str, ours) -> List[str]:
    """The paths behind one line of what git says is unsaved, minus our own.

    Git names a whole folder when nothing inside it has ever been saved, so a
    run that had just written the first file into a new folder saw one line
    naming the folder and read it as somebody else's work. The folder is
    opened and what is really in it is compared instead.
    """
    lowered = named.lower()
    if lowered.startswith(constants.LEGACY_CHANGES_DIR + "/"):
        return []
    if not named.endswith("/"):
        return [] if named in ours else [named]
    folder = _full(base_root, named)
    if not os.path.isdir(folder):
        return [named]
    left = []
    for where, _folders, files in os.walk(folder):
        for name in sorted(files):
            full = os.path.join(where, name)
            relative = os.path.relpath(full, base_root).replace(os.sep, "/")
            if relative not in ours and not unsaved.is_clutter_file(full):
                left.append(relative)
    return left


def _finish_from_note(base_root, base_id, journal, saved, git) -> Result:
    """Carry out whatever a stopped run had not saved yet, and nothing more.

    The move has landed by the time this is called, and a base whose files
    have moved without being rewritten is one every reader here already
    reads, so there is nothing to unpick. The day comes off the note, so the
    dated record is the one the run would have written had it never stopped.

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

    moves, rewrites, drops, added = _pieces_from_note(journal)
    legacy = _is_legacy(journal)
    if legacy:
        # The release before this one rewrote every context change its note
        # names, in the order the note names them, which is also every file
        # it moved. A run of it that only finished a rewrite moved nothing,
        # so the note is what says which files those were.
        rewrites = [
            str(item.get("path"))
            for item in journal.get("paths") or []
            if _one_file_in(str(item.get("path")), constants.WORK_CHANGES_DIR)
        ]
    for relative in rewrites:
        text = read_text(_full(base_root, relative))
        if text is None:
            # A file this run had already moved is gone, renamed, or no longer
            # readable. It cannot be finished and it must not be guessed at,
            # so the document is named and the one way out is said in the same
            # breath.
            return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % _named(relative))
        if relative in (constants.MAP_PATH, constants.CODEOWNERS_PATH):
            continue
        try:
            formats.ChangeEntry.parse(text)
        except (ValidationError, PathError):
            return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % _named(relative))
    if not moves and not rewrites and not drops:
        return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % "one of them")
    day = _as_date(str(journal.get("day") or "")) or state.today()
    subjects = list(journal.get("subjects") or SUBJECTS)
    if legacy:
        moved_names = [relative.split("/")[-1] for relative in rewrites]
        record_text = _legacy_record_for(moved_names, day)
    else:
        record_text = _record_for(moves, rewrites, drops, day)
    # The record goes where the note says it goes, which is the name the run
    # chose because nothing else held it.
    went_to = set(went for _came, went in moves)
    record_path = None
    for item in journal.get("paths") or []:
        relative = str(item.get("path"))
        if relative in went_to or not _is_the_record(relative, legacy):
            continue
        record_path = relative
        if str(item.get("hash")) != ids.exact_hash(record_text):
            return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % NAMED_RECORD)
        break
    if record_path is None:
        return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % NAMED_RECORD)
    added_texts = []
    for relative in added:
        if relative == constants.STACK_PATH:
            text = _stack_text(base_root)
            planned = [
                str(item.get("hash"))
                for item in journal.get("paths") or []
                if str(item.get("path")) == relative
            ]
            if planned and ids.exact_hash(text) != planned[0]:
                return _refused(CODE_CANNOT_FINISH, CANNOT_FINISH % _named(relative))
            added_texts.append((relative, text))
        else:
            added_texts.append((relative, ""))
    try:
        if subjects[1] not in saved:
            _do_the_rewrite(base_root, rewrites, subjects[1], git)
        if subjects[2] not in saved:
            _do_the_record(
                base_root, record_path, record_text, added_texts, subjects[2], git
            )
    except GitError:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    _tidy_empty_older_folders(base_root)
    _clear_journal(base_id)
    return Result(
        STATUS_RESUMED,
        sentence=MIGRATED,
        moved=[went for _came, went in moves],
        entry_ids=[
            went.split("/")[-1][: -len(".md")]
            for came, went in moves
            if _is_an_entry_path(went)
        ],
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
    landed = _landed(base_root, journal, saved, runner)

    sorted_out = _sort_out(base_root, journal, runner)
    # A path holding the person's own words is left alone, and the copy the
    # move made is left with it: putting the older one back beside it would
    # leave one thing written down twice, which is worse than either.
    theirs = set(sorted_out.theirs)
    keep_back = set()
    for relative in theirs:
        source = _source_of(journal, relative)
        if source:
            keep_back.add(source)

    if not landed:
        # Nothing that holds their words is brought back over, whether the
        # move took it away outright or moved it, and every one is looked at
        # again right before, because they may have written to it since.
        bringing_back = [
            relative
            for relative in list(sorted_out.restore)
            + [str(one) for one in (journal.get("removed") or [])]
            if relative not in keep_back
            and relative not in theirs
            and _in_head(base_root, relative, runner)
            and _still_as_saved_or_gone(base_root, relative, runner)
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
        full = _full(base_root, relative)
        # Looked at again right before anything is done to it, because words
        # of theirs can arrive after everything was sorted, and a file holding
        # anything but what this run wrote is theirs and is named (the
        # confirmation pass on Unit 1.5b, finding 1).
        if not _still_what_this_run_wrote(base_root, journal, relative):
            if read_text_exactly(full) is not None or os.path.lexists(full):
                theirs.add(relative)
            continue
        try:
            if in_head:
                runner.check(["checkout", "HEAD", "--", relative], cwd=base_root)
                continue
            if not _another_copy_is_there(
                base_root, relative, journal, sorted_out, runner
            ):
                continue
            runner.check(
                ["rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", relative],
                cwd=base_root,
            )
            if not _still_what_this_run_wrote(base_root, journal, relative):
                theirs.add(relative)
                continue
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
            sentence=GAVE_UP_LEFT_ALONE % _all_named(theirs, base_root),
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
    """Move this base to the current layout, or say why it did not.

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
        if _landed(base_root, journal, saved, runner):
            finished = _finish_from_note(base_root, base_id, journal, saved, runner)
            if not finished.ok or not _is_legacy(journal):
                return finished
            # The release before this one moved its part and has now been
            # finished. What it did not do, this run does next, so the one
            # yes takes the base all the way.
            return _carry_on(base_root, base_id, day, runner, every_seat_updated, finished)
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

    return _move(base_root, base_id, day, runner, every_seat_updated, put_back)


def _carry_on(base_root, base_id, day, runner, every_seat_updated, finished) -> Result:
    """After finishing an older release's run, take the base the rest of the way."""
    rest = _move(base_root, base_id, day, runner, every_seat_updated, False)
    if rest.status == STATUS_NOT_NEEDED:
        return finished
    return rest


def _move(base_root, base_id, day, runner, every_seat_updated, put_back) -> Result:
    """The move itself, on a base with no unfinished run left on it."""
    refusal = _ready_to_write(base_root, runner)
    if refusal is not None:
        # A tree this module's own unfinished work dirtied was put back just
        # above, so anything left here is the person's own.
        return refusal

    plan, refused = _prevalidate(base_root, day)
    if refused is not None:
        return refused
    if (
        plan.has_work
        and not every_seat_updated
        and paths.remote_url(base_root, runner=runner) is not None
    ):
        return _refused(CODE_EVERY_SEAT_FIRST, EVERY_SEAT_FIRST)
    if not plan.has_work:
        return Result(
            STATUS_NOT_NEEDED,
            sentence=PUT_BACK if put_back else NOTHING_TO_MOVE,
        )

    head = _head(base_root, runner)
    if not head:
        return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE)
    written = _plan_the_writes(base_root, plan, day)
    _write_journal(
        base_id,
        base_root,
        head,
        written,
        _came_from(base_root, plan),
        day,
        list(plan.drops) + list(plan.gone),
    )

    pairs = [(move.source, move.destination) for move in plan.moves]
    rewrites = list(plan.rewrites)
    if plan.map_texts is not None:
        rewrites.append(constants.MAP_PATH)
    if plan.owner_texts is not None:
        rewrites.append(constants.CODEOWNERS_PATH)
    added_texts = [(relative, "") for relative in plan.added]
    if plan.stack_text is not None:
        added_texts.append((constants.STACK_PATH, plan.stack_text))
    try:
        _do_the_move(base_root, pairs, list(plan.drops) + list(plan.gone), MOVE_SUBJECT, runner)
        _do_the_rewrite(base_root, rewrites, REWRITE_SUBJECT, runner)
        _do_the_record(
            base_root,
            plan.record_path,
            plan.record_text,
            added_texts,
            RECORD_SUBJECT,
            runner,
        )
    except GitError:
        # Saying the base is as it was while half a move is still sitting in
        # the index is a sentence that is not true. It is put back first, and
        # what is said depends on whether that worked.
        journal, _problem = _checked_journal(base_id, base_root)
        saved = (
            _subjects_since(base_root, str(journal.get("head")), runner)
            if journal
            else None
        )
        if journal and (saved is None or _landed(base_root, journal, saved, runner)):
            # Something already landed, or nobody can say. Putting back now
            # would unpick saved work, so the note stays and the next run
            # finishes what is left.
            return _refused(CODE_GIT_FAILED, COULD_NOT_SAVE_LEFT_HALF_DONE)
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
        sentence=MIGRATED,
        moved=[move.destination for move in plan.moves],
        entry_ids=[move.entry_id for move in plan.moves if move.kind == KIND_ENTRY],
    )


def why_not_offered(
    base_id: str, state_of_the_offer: str, today: Optional[datetime.date] = None
) -> Optional[str]:
    """What a read-only look adds about the offer, or None when it adds nothing.

    The look's own sentence already says why a move would not run: unsaved
    edits, a change written down twice, a shared base whose seats are not yet
    updated, or nothing to move. The one reason it cannot see is the person's
    own not now, so that is the one thing said here. When the offer would be
    made, nothing is said about it at all.
    """
    if state_of_the_offer != OFFER_NONE:
        return None
    seat, _problems = state.load_seat(base_id)
    until = _as_date(str(seat.get(SEAT_PUT_OFF_KEY) or ""))
    if until is None or (today or state.today()) >= until:
        return None
    return NOT_OFFERED_PUT_OFF % until.isoformat()


def _named_moves(plan: "_Plan") -> Tuple[str, int]:
    """What still sits where the older layout kept it, and how many things.

    Each core document is named the way a person names it, segments and any
    other document are counted, and so are the context changes and the
    records, each in words and in the singular for one.
    """
    named: List[str] = []
    segments = 0
    others = 0
    for move in plan.moves:
        if move.kind != KIND_DOCUMENT:
            continue
        if move.destination in names.KNOWN_DOCUMENTS:
            named.append(names.document_name(move.destination))
        elif names.is_segment(move.destination):
            segments += 1
        else:
            others += 1
    counts = plan.counts()
    if not plan.moves:
        # Nothing moves, and only settings are brought up to date.
        counts[KIND_ENTRY] = len(plan.rewrites) or len(plan.drops)
    parts = list(named)
    if segments:
        parts.append(names.how_many(segments, "segment", "segments"))
    if others:
        parts.append(names.how_many(others, "other document", "other documents"))
    for kind in (KIND_ENTRY, KIND_RECORD):
        if counts.get(kind):
            one, many = KIND_WORDS[kind]
            parts.append(names.how_many(counts[kind], one, many))
    total = len(named) + segments + others + counts.get(KIND_ENTRY, 0) + counts.get(
        KIND_RECORD, 0
    )
    if not parts:
        return names.how_many(0, "document", "documents"), 0
    if len(parts) == 1:
        return parts[0], total
    return ", ".join(parts[:-1]) + " and " + parts[-1], total


def offer_sentence(base_root: str, every_seat_first: bool = False) -> str:
    """The offer to move this base, worked out from what this base holds."""
    plan, _refusal = _prevalidate(base_root)
    if plan is None:
        # Only asked once the checks the move runs have passed, so this is a
        # base that changed in between; it is described as holding nothing
        # rather than as holding something it may not.
        plan = _Plan()
    what, total = _named_moves(plan)
    if every_seat_first:
        template = EVERY_SEAT_FIRST_ONE if total == 1 else EVERY_SEAT_FIRST_MANY
    else:
        template = OFFER_ONE if total == 1 else OFFER_MANY
    return template % {"version": constants.CURRENT_LAYOUT_VERSION, "what": what}


def _opening() -> str:
    return OFFER_ONE.split(" Your base still keeps", 1)[0] % {
        "version": constants.CURRENT_LAYOUT_VERSION
    }


def is_the_offer(sentence: str) -> bool:
    """Whether a sentence is the offer to move this base, in either number."""
    text = str(sentence or "")
    return text.startswith(_opening()) and text.endswith(
        ("Shall I move it now?", "Shall I move them now?")
    )


def is_every_seat_first(sentence: str) -> bool:
    """Whether a sentence is the offer made on a base other people can reach."""
    text = str(sentence or "")
    return text.startswith(_opening()) and text.endswith(
        ("I will move it.", "I will move them.")
    )


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
    plan, refused = _prevalidate(base_root, day)
    if refused is not None:
        return WOULD_NOT % refused.sentence
    if not plan.has_work:
        return WOULD_NOT % NOTHING_TO_MOVE
    if paths.remote_url(base_root, runner=runner) is not None:
        return WOULD_NOT % EVERY_SEAT_FIRST
    counts = plan.counts()
    if not plan.moves:
        # Nothing moves, and only settings are brought up to date.
        counts[KIND_ENTRY] = len(plan.rewrites) or len(plan.drops)
    return WOULD_MOVE % (_what_moves(counts), day.isoformat())


def counted(number: int) -> str:
    """A count as a person says it: in words up to ten, as a number after."""
    return names.counted(number)


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
