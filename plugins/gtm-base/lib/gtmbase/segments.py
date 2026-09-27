"""Which customer segments a base will hold, settled before anything is drafted.

Unit 1.7a of the 2026-09-19 plan. The third real run read twelve finished,
reviewed segment pages and wrote one profile out of them, so a person's
finished work was summarized away. Before the customer profile is drafted,
the person now settles the inventory: for each segment, whether its finished
document is taken as the authoritative version, whether the segment is
drafted, or whether it is left out for now. The profile that is then drafted
names every segment, and a segment left out is named as still to come.

This module is the inventory and nothing else. It works out the file name
each segment would be saved under, checks that name before anything is
written, reads the person's answers, and keeps the settled inventory in the
run's own folder so a later step, or a later session of the same run, reads
back exactly what was said. Taking a finished document into the base is Unit
1.7c's, drafting a segment is Unit 1.7b's, and finishing an import that
stopped is Unit 1.7d's. Nothing here writes into a base.

A segment's name is the person's own words, and the file name made from it is
treated as untrusted: only lower-case letters from A to Z, digits and single
hyphens survive, letter case and the different ways one letter can be encoded
are folded away first, and a name that folds to the same file name as another
segment, to nothing at all, or to a name the base or the computer keeps for
itself is refused before anything is saved.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Dict, List, Optional, Sequence

from . import constants, trust_surface
from .errors import GtmBaseError
from .fsutil import HeldLock, atomic_write_json, read_json, remove

# The file inside a run's folder holding the candidates shown, and the one
# holding the settled inventory.
CANDIDATES_FILE = "segment-candidates.json"
INVENTORY_FILE = "segments.json"
# The shape of the inventory file, so a later unit that adds to it can tell
# an inventory written before it apart.
INVENTORY_VERSION = 1

# Why an inventory was refused. Each has one sentence below, except the
# first, which is about the shape of what the assistant wrote rather than
# anything the person said.
CODE_UNREADABLE = "segments-unreadable"
CODE_NO_SUCH_DOCUMENT = "no-such-document"
CODE_ADOPT_NEEDS_A_DOCUMENT = "adopt-needs-a-document"
CODE_SAME_NAME = "same-name"
CODE_NO_USABLE_NAME = "no-usable-name"
CODE_RESERVED_NAME = "reserved-name"
CODE_SAME_DOCUMENT = "same-document"
CODE_NAME_UNUSABLE = "name-unusable"
CODE_TOO_MANY = "too-many-segments"
CODE_NONE = "no-segments"

# --- The sentences a person reads --------------------------------------------

# Said above the numbered list of documents that each describe one segment.
FOUND_SENTENCE = (
    "Your material holds %(count)d documents that each describe one group of "
    "customers."
)
# The one thing this step asks.
ASK_SENTENCE = (
    "For each one, say whether to use the finished document, draft that "
    "segment fresh, or leave it out for now, and name any segment that has no "
    "document yet."
)
# What each settled segment will become, one line each, read back.
WILL_ADOPT = "%(name)s will be taken from its finished document."
WILL_DRAFT = "%(name)s will be drafted from your material."
WILL_LEAVE_OUT = (
    "%(name)s is left out for now, and your customer profile will name it as "
    "still to come."
)
# Said after the lines, once the inventory is kept.
SAVED_SENTENCE = "That is the list of segments your base will hold."
# Said instead when there turns out to be one segment.
ONE_SEGMENT_SENTENCE = (
    "With one segment, your customer profile describes it in full, so it needs "
    "no file of its own."
)
# Said when the inventory could not be kept, naming what to change.
SAME_NAME = (
    "%(first)s and %(second)s would be saved under the same name, so nothing "
    "was saved. Give one of them a different name."
)
NO_USABLE_NAME = (
    "%(name)s has no letters or numbers a file name can be made from, so "
    "nothing was saved. Give that segment a name written in the letters A to Z."
)
RESERVED_NAME = (
    "%(name)s is a name the base keeps for itself, so nothing was saved. Give "
    "that segment a different name."
)
SAME_DOCUMENT = (
    "One finished document was named for two segments, so nothing was saved. "
    "Each finished document can stand for one segment only."
)
NAME_UNUSABLE = (
    "One of those names is too long or runs over more than one line, so "
    "nothing was saved. Give that segment a shorter name."
)
TOO_MANY = (
    "That is more segments than one base can hold, so nothing was saved. "
    "Leave out the ones that matter least, or group them."
)
NONE_NAMED = (
    "No segment was named, so nothing was saved. Name at least one segment."
)

SENTENCES = {
    CODE_SAME_NAME: SAME_NAME,
    CODE_NO_USABLE_NAME: NO_USABLE_NAME,
    CODE_RESERVED_NAME: RESERVED_NAME,
    CODE_SAME_DOCUMENT: SAME_DOCUMENT,
    CODE_NAME_UNUSABLE: NAME_UNUSABLE,
    CODE_TOO_MANY: TOO_MANY,
    CODE_NONE: NONE_NAMED,
}

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NOT_SLUG_RE = re.compile(r"[^a-z0-9]+")
# Letters that do not come apart into a base letter and a mark, written the
# way they are usually spelled in the letters A to Z. Any other character
# outside A to Z becomes a hyphen, so two words it joined stay two words
# (finding 7 of the unit's correctness review).
_SPELLED_OUT = {
    "\u00e6": "ae",
    "\u00f8": "o",
    "\u0153": "oe",
    "\u0142": "l",
    "\u0111": "d",
    "\u00f0": "d",
    "\u00fe": "th",
    "\u0131": "i",
    "\u00df": "ss",
}


class InventoryRefused(GtmBaseError):
    """The inventory could not be kept, with the one sentence that says why."""

    default_code = CODE_UNREADABLE

    def __init__(self, code, sentence=""):
        super(InventoryRefused, self).__init__(code, code)
        self.sentence = sentence


# --- File names made from a segment's name -----------------------------------


def slug_for(name) -> str:
    """The file name, without its ending, a segment of this name is saved under.

    Letter case is folded first, then every letter is taken apart into its
    base letter and its marks and the marks are dropped, so "Fintech",
    "FINTECH", "Fìntech" and a name typed in full-width letters all come out
    the same. Anything that is not a letter from A to Z or a digit becomes a
    single hyphen, and hyphens at either end are taken off. A name left
    longer than the cap is cut at the last hyphen before it, so a word is
    never cut in half when that can be helped.
    """
    text = unicodedata.normalize("NFKD", str(name or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(
        ch if ch.isascii() else _SPELLED_OUT.get(ch, "-")
        for ch in text
        if not unicodedata.combining(ch)
    )
    text = _NOT_SLUG_RE.sub("-", text).strip("-")
    cap = constants.SEGMENT_SLUG_MAX_CHARS
    if len(text) > cap:
        cut = text[: cap + 1]
        at = cut.rfind("-")
        text = (cut[:at] if at > 0 else text[:cap]).strip("-")
    return text


def destination(slug: str) -> str:
    """Where in a base the segment saved under this name lives."""
    return constants.SEGMENTS_DIR + "/" + slug + ".md"


def slug_problem(slug) -> Optional[str]:
    """Why a file name may not be used for a segment, or None when it may.

    The file name has to be made of lower-case letters, digits and single
    hyphens only, so it can never climb out of its folder, never be hidden,
    and never mean two things on two computers. It may not be one of the names
    a computer keeps for itself, and the path it makes may not be one the
    check a base must pass before it is opened refuses, which is how a
    segment named "Claude" or "Agents" is caught before it could put an
    instruction file into the base.
    """
    text = str(slug or "")
    if not text:
        return CODE_NO_USABLE_NAME
    if (
        not _SLUG_RE.match(text)
        or text.startswith(".")
        or "/" in text
        or "\\" in text
        or len(text) > constants.SEGMENT_SLUG_MAX_CHARS
    ):
        return CODE_NO_USABLE_NAME
    if text in constants.SEGMENT_RESERVED_SLUGS:
        return CODE_RESERVED_NAME
    if trust_surface.path_is_refused(destination(text).split("/")):
        return CODE_RESERVED_NAME
    for name in constants.TRUST_REFUSED_TREE_NAMES:
        folded = trust_surface.normalize_component(name)
        if text == folded or text + ".md" == folded:
            return CODE_RESERVED_NAME
    return None


def clean_name(name) -> str:
    """A segment's name, kept the way the person said it, or a refusal.

    Runs of spaces are closed up. A name holding a line break or any other
    control character, or longer than the cap, is refused, because the name
    is read back to the person and later written into the profile as prose.
    """
    if not isinstance(name, str):
        raise InventoryRefused(CODE_NAME_UNUSABLE, NAME_UNUSABLE)
    for character in name:
        if ord(character) < 32 or ord(character) == 127:
            raise InventoryRefused(CODE_NAME_UNUSABLE, NAME_UNUSABLE)
    text = " ".join(name.split())
    if not text or len(text) > constants.SEGMENT_NAME_MAX_CHARS:
        raise InventoryRefused(CODE_NAME_UNUSABLE, NAME_UNUSABLE)
    return text


# --- The documents that each describe one segment ----------------------------


class Candidate(object):
    """One document on the agreed list that looks like it describes a segment."""

    __slots__ = ("number", "path", "label")

    def __init__(self, number, path, label):
        self.number = int(number)
        self.path = str(path)
        self.label = str(label)

    def to_payload(self) -> Dict[str, object]:
        return {"number": self.number, "path": self.path, "label": self.label}

    def __eq__(self, other):
        return isinstance(other, Candidate) and self.to_payload() == other.to_payload()

    def __repr__(self) -> str:
        return "Candidate(%d, %r)" % (self.number, self.label)


def save_candidates(folder: str, candidates: Sequence[Candidate], inside: str) -> str:
    """Keep the numbered documents exactly as they were shown."""
    path = os.path.join(folder, CANDIDATES_FILE)
    atomic_write_json(
        path,
        {"candidates": [candidate.to_payload() for candidate in candidates]},
        inside=inside,
    )
    return path


def load_candidates(folder: str) -> Optional[List[Candidate]]:
    """The numbered documents this run showed, or None when none were shown."""
    payload = read_json(os.path.join(folder, CANDIDATES_FILE))
    if not isinstance(payload, dict):
        return None
    return candidates_from(payload.get("candidates"))


def candidates_from(items) -> Optional[List[Candidate]]:
    """The numbered documents read back from a kept list, or None."""
    if not isinstance(items, list):
        return None
    found: List[Candidate] = []
    for item in items:
        if not isinstance(item, dict):
            return None
        try:
            found.append(Candidate(item["number"], item["path"], item["label"]))
        except (KeyError, TypeError, ValueError):
            return None
    return found


# --- The settled inventory ---------------------------------------------------


class Segment(object):
    """One segment of the inventory, as the person settled it.

    `number` is the number of the finished document it was named with, or
    None when it was named with no document, and `source` and `label` are that
    document's real path and its name as it was shown.
    """

    __slots__ = ("name", "slug", "answer", "number", "source", "label")

    def __init__(self, name, slug, answer, number=None, source="", label=""):
        self.name = name
        self.slug = slug
        self.answer = answer
        self.number = number
        self.source = source or ""
        self.label = label or ""

    @property
    def destination(self) -> str:
        return destination(self.slug)

    def to_payload(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "slug": self.slug,
            "answer": self.answer,
            "number": self.number,
            "source": self.source,
            "label": self.label,
        }

    def __eq__(self, other):
        return isinstance(other, Segment) and self.to_payload() == other.to_payload()

    def __repr__(self) -> str:
        return "Segment(%r, %r)" % (self.slug, self.answer)


class Inventory(object):
    """Every segment a base will hold, in the order the person named them."""

    __slots__ = ("segments",)

    def __init__(self, segments):
        self.segments = list(segments)

    @property
    def is_single(self) -> bool:
        """Whether there is one segment, which the profile describes in full.

        A lone segment left out is not that: it is named as still to come,
        like any other segment left out (finding 5 of the unit's correctness
        review).
        """
        return (
            len(self.segments) == 1
            and self.segments[0].answer != constants.SEGMENT_LEAVE_OUT
        )

    def left_out(self) -> List[Segment]:
        return [
            segment
            for segment in self.segments
            if segment.answer == constants.SEGMENT_LEAVE_OUT
        ]

    def segment_files(self) -> List[str]:
        """Where each segment that gets a file of its own will live.

        A company with one segment gets only the profile, at full depth, and
        a segment left out gets no file until somebody asks for one.
        """
        if self.is_single:
            return []
        return [
            segment.destination
            for segment in self.segments
            if segment.answer != constants.SEGMENT_LEAVE_OUT
        ]

    def to_payload(self) -> Dict[str, object]:
        return {
            "version": INVENTORY_VERSION,
            "segments": [segment.to_payload() for segment in self.segments],
        }

    def __eq__(self, other):
        return isinstance(other, Inventory) and self.to_payload() == other.to_payload()

    def __repr__(self) -> str:
        return "Inventory(segments=%d)" % len(self.segments)


def read_lines(text) -> List[tuple]:
    """The assistant's lines, one per segment, as (answer, number, name).

    Each line is the answer, then the number of the finished document the
    segment was named with or a hyphen, then the segment's name:

        adopt 3 Fintech lenders
        draft - Regional banks
        leave-out 7 Credit unions

    Blank lines are skipped. A line that does not have that shape refuses the
    whole list, because a list read partly is a list the person did not give.
    """
    found: List[tuple] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if len(parts) != 3:
            raise InventoryRefused(CODE_UNREADABLE)
        answer, number, name = parts
        if answer not in constants.SEGMENT_ANSWERS:
            raise InventoryRefused(CODE_UNREADABLE)
        if number == "-":
            found.append((answer, None, name))
            continue
        if not number.isdigit() or not number.isascii():
            raise InventoryRefused(CODE_UNREADABLE)
        found.append((answer, int(number), name))
    return found


def settle(lines: Sequence[tuple], candidates: Sequence[Candidate]) -> Inventory:
    """Check every answer and every file name, and return the inventory.

    Everything is checked before anything is kept, so a list with one name
    that cannot be used keeps nothing at all, and the sentence names the
    segment to change. Two names that fold to one file name are caught here,
    before any file exists that could be written over.
    """
    if not lines:
        raise InventoryRefused(CODE_NONE, NONE_NAMED)
    if len(lines) > constants.SEGMENT_INVENTORY_MAX:
        raise InventoryRefused(CODE_TOO_MANY, TOO_MANY)
    by_number = dict((candidate.number, candidate) for candidate in candidates)
    segments: List[Segment] = []
    used_documents: Dict[int, str] = {}
    by_slug: Dict[str, str] = {}
    for answer, number, raw_name in lines:
        name = clean_name(raw_name)
        candidate = None
        if number is not None:
            candidate = by_number.get(number)
            if candidate is None:
                raise InventoryRefused(CODE_NO_SUCH_DOCUMENT)
            if number in used_documents:
                raise InventoryRefused(CODE_SAME_DOCUMENT, SAME_DOCUMENT)
            used_documents[number] = name
        elif answer == constants.SEGMENT_ADOPT:
            raise InventoryRefused(CODE_ADOPT_NEEDS_A_DOCUMENT)
        slug = slug_for(name)
        problem = slug_problem(slug)
        if problem is not None:
            raise InventoryRefused(problem, SENTENCES[problem] % {"name": name})
        if slug in by_slug:
            raise InventoryRefused(
                CODE_SAME_NAME,
                SAME_NAME % {"first": by_slug[slug], "second": name},
            )
        by_slug[slug] = name
        segments.append(
            Segment(
                name,
                slug,
                answer,
                number,
                candidate.path if candidate else "",
                candidate.label if candidate else "",
            )
        )
    return Inventory(segments)


def save(folder: str, inventory: Inventory, inside: str) -> str:
    """Keep the settled inventory in the run's own folder."""
    path = os.path.join(folder, INVENTORY_FILE)
    atomic_write_json(path, inventory.to_payload(), inside=inside)
    return path


def load(folder: str) -> Optional[Inventory]:
    """The inventory this run settled, read back exactly, or None.

    Every segment is checked again as it is read, the file name worked out
    again from the name and compared, so an inventory somebody edited by hand
    into something that could not have been settled is not read at all.
    """
    return inventory_from(
        read_json(os.path.join(folder, INVENTORY_FILE)), load_candidates(folder) or []
    )


def inventory_from(payload, candidates: Sequence[Candidate]) -> Optional[Inventory]:
    """An inventory read back from what was kept, settled again, or None.

    The same check `load` makes, for an inventory kept anywhere: in the run's
    own folder, or in the record an import keeps past the closing (Unit 1.7d).
    """
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != INVENTORY_VERSION:
        return None
    items = payload.get("segments")
    if not isinstance(items, list) or not items:
        return None
    lines = []
    for item in items:
        if not isinstance(item, dict):
            return None
        number = item.get("number")
        if number is not None and (
            not isinstance(number, int) or isinstance(number, bool)
        ):
            return None
        lines.append((item.get("answer"), number, item.get("name")))
    # Settled again from the answers alone, against the documents this run
    # kept as shown, and compared whole: a source, a label, a number used
    # twice, or anything else settle would refuse makes the file unreadable
    # (finding 3 of the unit's correctness review).
    if any(answer not in constants.SEGMENT_ANSWERS for answer, _n, _name in lines):
        return None
    try:
        again = settle(lines, candidates)
    except InventoryRefused:
        return None
    if again.to_payload() != payload:
        return None
    return again


def readback(inventory: Inventory) -> List[str]:
    """The lines read back to the person, one per segment, then the last one."""
    if inventory.is_single:
        return [ONE_SEGMENT_SENTENCE]
    lines = []
    for segment in inventory.segments:
        form = {
            constants.SEGMENT_ADOPT: WILL_ADOPT,
            constants.SEGMENT_DRAFT: WILL_DRAFT,
            constants.SEGMENT_LEAVE_OUT: WILL_LEAVE_OUT,
        }[segment.answer]
        lines.append(form % {"name": segment.name})
    lines.append(SAVED_SENTENCE)
    return lines


def dumps(inventory: Inventory) -> str:
    """The inventory as the text it is kept as, for a test to compare."""
    return json.dumps(inventory.to_payload(), sort_keys=True)


# --- Before a segment's file is written into a base (Unit 1.7b) --------------

CODE_FILE_TAKEN = "segment-file-taken"
CODE_FOLDER_NOT_ORDINARY = "segment-folder-not-ordinary"
CODE_NOT_TO_DRAFT = "not-a-segment-to-draft"

# Said when the base already holds a file whose name comes out the same as the
# one this segment would be saved under, in either folder segments have been
# kept in. Nothing is ever written over it.
FILE_TAKEN = (
    "Your base already holds a document under the name this segment would be "
    "saved under, so nothing was written over it. Give that segment a "
    "different name, or leave it out."
)
# Said when the folder segments are kept in is a link, or leads outside the
# base, which is never somewhere a document is written.
FOLDER_NOT_ORDINARY = (
    "The folder your segments are kept in is not an ordinary folder inside "
    "your base, so nothing was written."
)


def already_in_base(base_root: str, slug: str) -> Optional[str]:
    """A file the base already holds that this segment's file would collide with.

    `settle` looks only at the names the person gave, so this is the look at
    the base itself, made before anything is written. Both folders segments
    have been kept in are read, because a base moved by Unit 1.5b keeps each
    segment under the name it had before the move, and that name may differ
    from the one GTM Base would make now only in its letter case or in the way
    one letter is encoded, which one computer treats as the same file and
    another does not. So every name is folded the way a segment's name is, and
    two names that fold to one file name are one file.
    """
    wanted = str(slug or "")
    for folder in (constants.SEGMENTS_DIR, constants.LEGACY_SEGMENTS_DIR):
        full = os.path.join(base_root, folder.replace("/", os.sep))
        try:
            names = sorted(os.listdir(full))
        except OSError:
            continue
        for name in names:
            stem = name[: -len(".md")] if name.casefold().endswith(".md") else name
            if slug_for(stem) == wanted:
                return folder + "/" + name
    return None


def folder_is_ordinary(base_root: str) -> bool:
    """Whether the segment folder may be written into: no link on the way.

    Each folder from the top of the base down to the segment folder is either
    not there yet or an ordinary folder, and none of them is a link, so a file
    written there lands inside the base and nowhere else.
    """
    root = os.path.realpath(base_root)
    here = root
    for part in constants.SEGMENTS_DIR.split("/"):
        here = os.path.join(here, part)
        if os.path.islink(here):
            return False
        if os.path.lexists(here) and not os.path.isdir(here):
            return False
    real = os.path.realpath(here)
    return real == here or real.startswith(root + os.sep)


# --- The import, kept past the closing (Unit 1.7d) ---------------------------
#
# Everything above keeps the inventory in the run's own folder, and the closing
# deletes that folder, as does the next run started on a later day. An import
# that stopped partway, in the middle of one page or between two, has to be
# finished by a later session that knows nothing of the run it started in, and
# Brandon's call 18 is that the inventory outlives the closing so that it can.
#
# So once a base exists, what the import needs is kept in this seat's own
# folder for that base, beside the other things this seat remembers about it.
# Not in the base: nothing in it is the team's, it names files on this one
# computer, and a record in the base would be shared with every seat, which is
# exactly what a second seat must not depend on. Not in the run folder: that
# is what the closing clears. It holds the settled inventory, the numbered
# documents its numbers point at, the narrowest yes that can still read the
# pages to take in (those pages and no other file), what the base is for, the
# run the import belongs to, and one line per page saying how far that page
# got. It is read and written with one writer at a time.
#
# Only four states are ever written down: the person's yes (the hash of the
# bytes they approved and the day those bytes were shown), saved, left out
# (their no), and refused by the contract. Whether a page with a yes has been
# written, staged or given its line is read from the base itself every time,
# because a state written down beside each of those steps is one more step a
# run can stop after, and the base already says.

IMPORT_FILE = "segments-import.json"
IMPORT_VERSION = 1

# What is written down about one page.
STATE_APPROVED = "approved"
STATE_COMMITTED = "committed"
STATE_LEFT_OUT = "left-out"
STATE_REFUSED = "refused"
STORED_STATES = (STATE_APPROVED, STATE_COMMITTED, STATE_LEFT_OUT, STATE_REFUSED)
# A page nobody has answered for yet.
STATE_NOT_ANSWERED = "not-answered"
# The states in which nothing more is asked or written for a page.
ANSWERED_AND_DONE = (STATE_COMMITTED, STATE_LEFT_OUT, STATE_REFUSED)

_DIGEST_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_EMPTY_CONSENT = {
    "root": "",
    "paths": [],
    "dropped": [],
    "scope": None,
    "frozen_at": "",
    "choice": "",
}
# What a record nobody can read is renamed to, so a new one can be kept.
UNREADABLE_SUFFIX = ".unreadable"


def _is_a_day(value) -> bool:
    """Whether a value is a real calendar day written the one way days are."""
    import datetime

    text = str(value or "")
    if not re.match(r"\A\d{4}-\d{2}-\d{2}\Z", text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


class ImportRecord(object):
    """What an import needs to be finished by a later session, and how far it got."""

    __slots__ = ("base_id", "run", "inventory", "candidates", "consent", "files")

    def __init__(self, base_id, run, inventory, candidates, consent, files=None):
        self.base_id = base_id
        self.run = run
        self.inventory = inventory
        self.candidates = list(candidates)
        self.consent = dict(consent)
        self.files = dict((slug, dict(item)) for slug, item in (files or {}).items())

    def to_adopt(self) -> List[Segment]:
        """The segments settled to be taken from their finished page, in order."""
        if self.inventory.is_single:
            return []
        return [
            segment
            for segment in self.inventory.segments
            if segment.answer == constants.SEGMENT_ADOPT
            and segment.number is not None
            and segment.source
        ]

    def state_of(self, slug: str) -> str:
        item = self.files.get(slug)
        if not item:
            return STATE_NOT_ANSWERED
        return item["state"]

    def approved(self, slug: str) -> Optional[dict]:
        """The yes kept for one page, its hash and the day it was shown, or None."""
        item = self.files.get(slug)
        if not item or item.get("state") not in (STATE_APPROVED, STATE_COMMITTED):
            return None
        return item

    def unfinished(self) -> List[Segment]:
        """Every page to take in that is not yet saved, left out, or refused."""
        return [
            segment
            for segment in self.to_adopt()
            if self.state_of(segment.slug) not in ANSWERED_AND_DONE
        ]

    def to_payload(self) -> Dict[str, object]:
        return {
            "version": IMPORT_VERSION,
            "base_id": self.base_id,
            "run": self.run,
            "inventory": self.inventory.to_payload(),
            "candidates": [candidate.to_payload() for candidate in self.candidates],
            "consent": dict(self.consent),
            "files": dict((slug, dict(item)) for slug, item in self.files.items()),
        }

    def __repr__(self) -> str:
        return "ImportRecord(pages=%d, unfinished=%d)" % (
            len(self.to_adopt()),
            len(self.unfinished()),
        )


def import_path(base_id: str) -> str:
    """Where this seat keeps the import of one base, past the closing.

    Working the place out makes nothing, so a session start that only asks
    whether an import stopped writes nothing to find out.
    """
    from . import ids, paths

    ids.check_base_id(base_id)
    return os.path.join(paths.seat_home_path(), "bases", base_id, IMPORT_FILE)


def _record_lock(base_id: str) -> HeldLock:
    """The lock on the record, with its folders made owner only, one at a time."""
    from . import paths

    paths.seat_dir(base_id)
    return HeldLock(import_path(base_id))


def _consent_from(value, sources: Sequence[str]) -> Optional[dict]:
    """The narrow yes kept for an import, checked, or None.

    It may name only the pages to take in, each by the real path it had when
    the person settled the list, so a later session that finishes the import
    can read those pages and nothing else of what the person once agreed to.
    The paths are compared as they were kept and never worked out again from
    the disk, so a folder moved and left behind as a link does not make the
    record unreadable; the check every read goes through looks at the disk
    when a page is read (the reviews of Unit 1.7d).
    """
    if not isinstance(value, dict):
        return None
    wanted = value.get("paths")
    if not isinstance(wanted, list) or not all(isinstance(p, str) for p in wanted):
        return None
    allowed = set(str(source) for source in sources)
    if any(path not in allowed for path in wanted):
        return None
    dropped = value.get("dropped") or []
    if not isinstance(dropped, list) or not all(isinstance(d, str) for d in dropped):
        return None
    for key in ("root", "scope", "frozen_at", "choice"):
        if value.get(key) is not None and not isinstance(value.get(key), str):
            return None
    return {
        "root": value.get("root") or "",
        "paths": list(wanted),
        "dropped": list(dropped),
        "scope": value.get("scope"),
        "frozen_at": value.get("frozen_at") or "",
        "choice": value.get("choice") or "",
    }


def _files_from(value, slugs: Sequence[str]) -> Optional[Dict[str, dict]]:
    if not isinstance(value, dict):
        return None
    files: Dict[str, dict] = {}
    for slug, item in value.items():
        if slug not in slugs or not isinstance(item, dict):
            return None
        state = item.get("state")
        if state not in STORED_STATES:
            return None
        if state in (STATE_APPROVED, STATE_COMMITTED):
            if not _DIGEST_RE.match(str(item.get("approved") or "")):
                return None
            if not _is_a_day(item.get("day")):
                return None
            files[slug] = {"state": state, "approved": item["approved"], "day": item["day"]}
            if item.get("original") is not None:
                if not _DIGEST_RE.match(str(item.get("original"))):
                    return None
                files[slug]["original"] = item["original"]
        else:
            files[slug] = {"state": state}
    return files


def record_from(payload, base_id: str) -> Optional[ImportRecord]:
    """An import record read back and checked whole, or None.

    Every part is checked again the way it was checked when it was settled,
    so a record somebody edited by hand into something no run could have
    written is not read at all, and nothing is written from it.
    """
    from . import ids

    if not isinstance(payload, dict) or payload.get("version") != IMPORT_VERSION:
        return None
    if payload.get("base_id") != base_id or not ids.is_run_id(payload.get("run")):
        return None
    candidates = candidates_from(payload.get("candidates"))
    if candidates is None:
        return None
    inventory = inventory_from(payload.get("inventory"), candidates)
    if inventory is None:
        return None
    record = ImportRecord(base_id, payload["run"], inventory, candidates, {})
    consent = _consent_from(
        payload.get("consent"), [segment.source for segment in record.to_adopt()]
    )
    if consent is None:
        return None
    files = _files_from(payload.get("files", {}), [s.slug for s in record.to_adopt()])
    if files is None:
        return None
    record.consent = consent
    record.files = files
    return record


def load_import(base_id: str) -> Optional[ImportRecord]:
    """The import this seat keeps for one base, or None when there is none."""
    return record_from(read_json(import_path(base_id)), base_id)


def has_import(base_id: str) -> bool:
    """Whether anything, readable or not, is kept for an import of this base."""
    return os.path.lexists(import_path(base_id))


def _keep_import(record: ImportRecord) -> None:
    from . import paths

    atomic_write_json(
        import_path(record.base_id), record.to_payload(), inside=paths.seat_home()
    )


def _set_aside(base_id: str) -> None:
    """Rename a record nobody can read out of the way, never deleting it."""
    path = import_path(base_id)
    if os.path.lexists(path) and load_import(base_id) is None:
        os.replace(path, path + UNREADABLE_SUFFIX)


def set_aside_unreadable(base_id: str) -> bool:
    """Put an unreadable record aside so the base can keep a new one.

    The record is renamed rather than deleted, so whatever it held is still
    there to look at by hand, and a record that can be read is never touched.
    """
    with _record_lock(base_id):
        if not has_import(base_id) or load_import(base_id) is not None:
            return False
        _set_aside(base_id)
        return True


def _referred_to(inventory: Inventory, candidates) -> List[Candidate]:
    """Only the numbered documents the settled list points at, and no others."""
    used = set(segment.number for segment in inventory.segments if segment.number is not None)
    return [candidate for candidate in candidates if candidate.number in used]


# What `carry_import` found when another import is kept for the base and
# still waits on a page, so this run's pages cannot be kept beside it.
CODE_ANOTHER_IMPORT = "another-import-unfinished"


def carry_import(
    base_id: str, run_id: str, inventory: Inventory, candidates, consent: dict
) -> Optional[ImportRecord]:
    """Keep what this run's import needs past the closing, and return the record.

    Nothing is kept when the inventory takes no finished page in. A record
    already kept for this list is left exactly as it is, because it holds how
    far the import got and the run it belongs to; a later run is seeded from
    it rather than writing over it. A record for another list is replaced
    only when nothing in it is still waiting on a page: every page settled,
    or none answered at all (a setup that stopped before any page and was
    set up again). One still waiting refuses, because its yes must not be
    lost. A record nobody can read is renamed aside, never deleted, and a new
    one is kept.
    """
    fresh = ImportRecord(
        base_id, run_id, inventory, _referred_to(inventory, candidates or []), {}
    )
    pages = fresh.to_adopt()
    if not pages:
        return None
    wanted = set(segment.source for segment in pages)
    given = dict(consent or {})
    given["paths"] = [
        path for path in (given.get("paths") or []) if isinstance(path, str) and path in wanted
    ]
    fresh.consent = _consent_from(given, [segment.source for segment in pages]) or dict(
        _EMPTY_CONSENT
    )
    with _record_lock(base_id):
        held = load_import(base_id)
        if held is not None:
            if held.inventory == inventory:
                return held
            if held.files and held.unfinished():
                raise InventoryRefused(CODE_ANOTHER_IMPORT)
        elif has_import(base_id):
            _set_aside(base_id)
        _keep_import(fresh)
    return fresh


def mark(
    base_id: str, slug: str, state: str, approved=None, day=None, run=None, original=None
) -> ImportRecord:
    """Write down how far one page got, with no other writer in between.

    `approved` and `day` go with the yes and with a save: the hash of the
    bytes approved and the day those bytes were shown. `original` is the
    hash of the original file as it was when the yes was given, so a later
    run can tell an original that changed from one cleaned differently by a
    later release (Unit 1.7d, after Unit 1.7c's stricter cleaning). `run` is the import
    the caller is working for, and a record for any other import is refused,
    so a yes is never written into somebody else's list. A page already
    saved is never marked left out or refused, and the check is made with
    the lock held, so a save another window has just written down stands.
    """
    if state not in STORED_STATES:
        raise ValueError("not a state an import keeps")
    item = {"state": state}
    if state in (STATE_APPROVED, STATE_COMMITTED):
        item["approved"] = str(approved or "")
        item["day"] = str(day or "")
        if not _DIGEST_RE.match(item["approved"]) or not _is_a_day(item["day"]):
            raise ValueError("a yes needs its hash and its day")
        if original is not None:
            if not _DIGEST_RE.match(str(original)):
                raise ValueError("not the hash of an original")
            item["original"] = str(original)
    with _record_lock(base_id):
        record = load_import(base_id)
        if record is None or slug not in [s.slug for s in record.to_adopt()]:
            raise InventoryRefused(CODE_UNREADABLE)
        if run is not None and record.run != run:
            raise InventoryRefused(CODE_ANOTHER_IMPORT)
        if state in (STATE_LEFT_OUT, STATE_REFUSED) and (
            record.state_of(slug) == STATE_COMMITTED
        ):
            return record
        held = record.files.get(slug) or {}
        if (
            state == STATE_COMMITTED
            and "original" not in item
            and held.get("approved") == item.get("approved")
            and held.get("original")
        ):
            item["original"] = held["original"]
        record.files[slug] = item
        _keep_import(record)
        return record


def clear(base_id: str, slug: str, run=None) -> ImportRecord:
    """Take one page back to not answered, because the yes no longer stands.

    Used only when the original changed after the yes, so the page is shown
    again. A page already saved is never taken back to not answered.
    """
    with _record_lock(base_id):
        record = load_import(base_id)
        if record is None:
            raise InventoryRefused(CODE_UNREADABLE)
        if run is not None and record.run != run:
            raise InventoryRefused(CODE_ANOTHER_IMPORT)
        if record.state_of(slug) != STATE_COMMITTED:
            record.files.pop(slug, None)
            _keep_import(record)
        return record


def forget_import(base_id: str) -> bool:
    """Take the record away once every page is saved, left out, or refused.

    It names files on this computer, so it is not kept a moment longer than
    the import needs it. A record still waiting on a page is never taken.
    """
    with _record_lock(base_id):
        record = load_import(base_id)
        if record is None or record.unfinished():
            return False
        return remove(import_path(base_id))
