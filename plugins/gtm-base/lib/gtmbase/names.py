"""The names a person reads for the things in their base.

A marketing lead does not have a file called `context/icps.md` and does
not have a change called `stg-bbca9f0e11d24c77`. They have a customer profile,
and they have the day they decided to stop selling to companies under twenty
people. This module is the one place that turns what the machine stores into
what a person is read aloud.

Two rules hold for everything here. A name never contains a path, and a name
never contains an identifier. The paths and the identifiers stay in the
machine-readable lines, which nobody reads aloud. Acceptance matrix ruling 6 of
2026-09-19 is where this comes from.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from . import constants

# How much of a change's first line is read aloud before it is cut short.
CHANGE_LINE_CHARS = 72

# The name each file the product knows about is read aloud by. The nine core
# files of the context standard each have one (Unit 1.5b), and a document a
# base laid out before that still holds at its older path is called exactly
# what it is called at its new one, because it is the same document.
KNOWN_DOCUMENTS = {
    "context/goals.md": "your goals",
    "context/product.md": "your product document",
    "context/icps.md": "your customer profile",
    "context/buyer-personas.md": "your buyer personas",
    "context/positioning.md": "your positioning",
    "context/messaging.md": "your messaging",
    "context/voice.md": "your voice guide",
    "context/design.md": "your design guide",
    "context/metrics.md": "your metric definitions",
    constants.MAP_PATH: "your base's map",
    constants.STACK_PATH: "your source map",
}
for _older, _current in constants.LEGACY_DOCUMENT_PATHS:
    KNOWN_DOCUMENTS.setdefault(_older, KNOWN_DOCUMENTS[_current])

# Where one segment of the customer profile lives, and where a base laid out
# before Unit 1.5b planned to keep one.
SEGMENTS_DIR = constants.SEGMENTS_DIR
SEGMENT_DIRS = (constants.SEGMENTS_DIR, constants.LEGACY_SEGMENTS_DIR)

# What a change with nothing written in it yet is called.
CHANGE_WITHOUT_A_LINE = "the change you recorded"

_WHITESPACE_RE = re.compile(r"\s+")

# What a segment is called when a sentence names it. A segment's file name is
# made from whatever somebody typed, and a file name short and tidy enough to
# pass any shape check can still read as an instruction, so no segment is ever
# named out of its file name (Unit 1.8, and Astra's confirmation of 0.3.2 for
# the refusals about unsaved work). Where the person's own name for a segment
# is needed, it comes from the settled inventory GTM Base keeps, never from
# the disk.
ONE_OF_YOUR_SEGMENTS = "one of your segments"
SOME_OF_YOUR_SEGMENTS = "%s of your segments"

# What any other document is called, for the same reason: its file name is
# never read out. The older name is kept because two modules import it.
ONE_OF_YOUR_DOCUMENTS = "one of your documents"
SOME_OF_YOUR_DOCUMENTS = "%s of your documents"
ONE_OTHER_DOCUMENT = "one other document"
OTHER_DOCUMENTS = "%s other documents"
DOCUMENT_WITHOUT_A_PLAIN_NAME = ONE_OF_YOUR_DOCUMENTS


# How many, the way a person says it, up to the point a person would say the
# number itself instead. Every count a person reads goes through `counted` or
# `how_many`, so none of them says "1 items" or "all 1 of them" (the 0.3.1 live
# check, step 4, finding 1).
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


def counted(number: int) -> str:
    """A count as a person says it: in words up to ten, as a number after."""
    if 0 <= number < len(COUNT_WORDS):
        return COUNT_WORDS[number]
    return str(number)


def how_many(number: int, one: str, many: str, start: bool = False) -> str:
    """A count and what it counts, in the singular for one: "one item".

    `start` is for a count that opens a sentence, so it begins with a capital.
    """
    said = "%s %s" % (counted(number), one if number == 1 else many)
    return said[:1].upper() + said[1:] if start else said


def _normalize(path: str) -> str:
    """The path as the base stores it, with the separators this machine uses."""
    return str(path).replace(os.sep, "/").strip().lstrip("./")


def is_segment(path: str) -> bool:
    """True when the path is one segment of the customer profile."""
    normalized = _normalize(path)
    if not normalized.endswith(".md"):
        return False
    return any(normalized.startswith(folder + "/") for folder in SEGMENT_DIRS)


def document_name(path: str) -> str:
    """What a person calls the context file at this path.

    A document the product knows by its path has a fixed name of its own. A
    segment is "one of your segments" and any other document is "one of your
    documents", because a file name is whatever somebody typed and no
    sentence a person reads is ever filled from one (Unit 1.8). Only an empty
    path is refused; a file named by its ending alone is counted like any
    other, as it was before.
    """
    normalized = _normalize(path)
    if not normalized:
        raise ValueError("a document name needs a path to work from")
    known = KNOWN_DOCUMENTS.get(normalized)
    if known:
        return known
    if is_segment(normalized):
        return ONE_OF_YOUR_SEGMENTS
    return ONE_OF_YOUR_DOCUMENTS


def documents_named(paths, name_of=None) -> str:
    """Several documents as a person says them, each known one by its name.

    The documents the product knows are named, in the order given and each
    once, and the segments and any other documents are counted, so a list
    of three segments reads "three of your segments" rather than the same
    words three times, and nothing in it is read out of a file name.
    `name_of` is for a caller that names one document its own way, such as
    recording a context change at any time; it defaults to `document_name`.
    """
    name_of = name_of or document_name
    named: List[str] = []
    segments = 0
    others = 0
    seen = set()
    for path in paths:
        # One document listed twice, or a segment at its older folder and its
        # current one, is one document and is counted once.
        normalized = _normalize(path)
        key = (
            "segment:" + os.path.basename(normalized)
            if is_segment(normalized)
            else normalized
        )
        if key in seen:
            continue
        seen.add(key)
        name = name_of(path)
        if name == ONE_OF_YOUR_SEGMENTS:
            segments += 1
        elif name == ONE_OF_YOUR_DOCUMENTS:
            others += 1
        elif name not in named:
            named.append(name)
    pieces = list(named)
    if segments:
        pieces.append(
            ONE_OF_YOUR_SEGMENTS
            if segments == 1
            else SOME_OF_YOUR_SEGMENTS % counted(segments)
        )
    if others:
        if pieces:
            pieces.append(
                ONE_OTHER_DOCUMENT if others == 1 else OTHER_DOCUMENTS % counted(others)
            )
        else:
            pieces.append(
                ONE_OF_YOUR_DOCUMENTS
                if others == 1
                else SOME_OF_YOUR_DOCUMENTS % counted(others)
            )
    return ", ".join(pieces)


def change_name(
    first_line: Optional[str], happened_on: Optional[str] = None, whole: bool = False
) -> str:
    """What a person calls one context change: its first line and its date.

    The first line is the sentence the person gave. The date is the day the
    change happened, not the day it was written down, because the day it
    happened is the one they remember. A line read as "What changed:" is read
    whole, because a line cut short there stopped in the middle of a number
    (the 0.3.1 live check, step 5, finding 3).
    """
    line = first_line_of(first_line) if whole else _first_sentence(first_line)
    day = (happened_on or "").strip()
    if not line:
        line = CHANGE_WITHOUT_A_LINE
    if day:
        return "%s (%s)" % (line, day)
    return line


def first_line_of(body: Optional[str]) -> str:
    """The opening line of a change, whole, with its heading marks taken off."""
    if not body:
        return ""
    for raw in str(body).splitlines():
        line = _WHITESPACE_RE.sub(" ", raw).strip().lstrip("#").strip()
        if line:
            return line
    return ""


def _first_sentence(body: Optional[str]) -> str:
    """The opening line of a change, trimmed to what is read aloud."""
    if not body:
        return ""
    for raw in str(body).splitlines():
        line = _WHITESPACE_RE.sub(" ", raw).strip()
        if not line:
            continue
        line = line.lstrip("#").strip()
        if not line:
            continue
        if len(line) <= CHANGE_LINE_CHARS:
            return line
        cut = line[:CHANGE_LINE_CHARS].rstrip()
        if " " in cut:
            cut = cut[: cut.rindex(" ")].rstrip()
        return cut + "..."
    return ""


# What each kind a base can hold is called in the inventory's table (Unit 2.1
# of Plan 1), keyed as `constants.BASE_KINDS` keys them. A standard and a
# skill are named by their kind and counted, never by the job in their file
# name.
KIND_LABELS = {
    "goals": "Goals",
    "product": "Product",
    "icps": "Customer profile",
    "buyer-personas": "Buyer personas",
    "positioning": "Positioning",
    "messaging": "Messaging",
    "voice": "Voice guide",
    "design": "Design guide",
    "metrics": "Metric definitions",
    "stack": "Source map",
    "standard": "Standards",
    "skill": "Skills",
}
# What each kind is called inside a sentence, as "your goals" is.
KIND_IN_A_SENTENCE = {
    "goals": KNOWN_DOCUMENTS["context/goals.md"],
    "product": KNOWN_DOCUMENTS["context/product.md"],
    "icps": KNOWN_DOCUMENTS["context/icps.md"],
    "buyer-personas": KNOWN_DOCUMENTS["context/buyer-personas.md"],
    "positioning": KNOWN_DOCUMENTS["context/positioning.md"],
    "messaging": KNOWN_DOCUMENTS["context/messaging.md"],
    "voice": KNOWN_DOCUMENTS["context/voice.md"],
    "design": KNOWN_DOCUMENTS["context/design.md"],
    "metrics": KNOWN_DOCUMENTS["context/metrics.md"],
    "stack": KNOWN_DOCUMENTS[constants.STACK_PATH],
    "standard": "a standard for a job",
    "skill": "a skill",
}
