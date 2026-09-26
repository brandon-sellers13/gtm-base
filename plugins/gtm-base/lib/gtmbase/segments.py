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
from .fsutil import atomic_write_json, read_json

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
    text = text.encode("ascii", "ignore").decode("ascii")
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
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
        return None
    found: List[Candidate] = []
    for item in payload["candidates"]:
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
        """Whether there is one segment, which the profile describes in full."""
        return len(self.segments) == 1

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
    payload = read_json(os.path.join(folder, INVENTORY_FILE))
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != INVENTORY_VERSION:
        return None
    items = payload.get("segments")
    if not isinstance(items, list) or not items:
        return None
    segments: List[Segment] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        slug = item.get("slug")
        answer = item.get("answer")
        number = item.get("number")
        try:
            if clean_name(name) != name:
                return None
        except InventoryRefused:
            return None
        if slug != slug_for(name) or slug_problem(slug) is not None or slug in seen:
            return None
        if answer not in constants.SEGMENT_ANSWERS:
            return None
        if number is not None and (
            not isinstance(number, int) or isinstance(number, bool)
        ):
            return None
        source = item.get("source") or ""
        label = item.get("label") or ""
        if not isinstance(source, str) or not isinstance(label, str):
            return None
        if answer == constants.SEGMENT_ADOPT and (number is None or not source):
            return None
        seen.add(slug)
        segments.append(Segment(name, slug, answer, number, source, label))
    return Inventory(segments)


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
