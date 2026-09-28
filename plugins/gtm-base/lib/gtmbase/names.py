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
from typing import Optional

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

_SEPARATORS_RE = re.compile(r"[-_]+")
_WHITESPACE_RE = re.compile(r"\s+")
# What a file name may be made of before it is read aloud. A name comes out of
# the base, and a name is read out in the middle of an instruction the
# assistant follows, so a name carrying anything else is not repeated back. The
# session-start hook held file names to the same rule before Unit 1.3 moved the
# text it was guarding, and this is that rule in the one place names are made.
_PLAIN_STEM_RE = re.compile(r"^[A-Za-z0-9 ._-]{1,80}$")

# What a document with a name nobody can safely read aloud is called instead.
DOCUMENT_WITHOUT_A_PLAIN_NAME = "one of your documents"


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


def _words(stem: str) -> str:
    """A file stem read as words, so `mid-market` becomes `mid market`."""
    return _WHITESPACE_RE.sub(" ", _SEPARATORS_RE.sub(" ", stem)).strip()


def is_segment(path: str) -> bool:
    """True when the path is one segment of the customer profile."""
    normalized = _normalize(path)
    if not normalized.endswith(".md"):
        return False
    return any(normalized.startswith(folder + "/") for folder in SEGMENT_DIRS)


def document_name(path: str) -> str:
    """What a person calls the context file at this path.

    The two required documents and the map have names of their own. A segment
    is named by the segment it covers. Anything else is named by the words in
    its file name, because a person who named a file `messaging.md` calls it
    their messaging.
    """
    normalized = _normalize(path)
    if not normalized:
        raise ValueError("a document name needs a path to work from")
    known = KNOWN_DOCUMENTS.get(normalized)
    if known:
        return known
    stem = os.path.basename(normalized)
    if stem.endswith(".md"):
        stem = stem[: -len(".md")]
    if not _PLAIN_STEM_RE.fullmatch(stem):
        return DOCUMENT_WITHOUT_A_PLAIN_NAME
    words = _words(stem)
    if not words:
        raise ValueError("a document name needs a file name to work from")
    if is_segment(normalized):
        return "your %s segment" % words
    return "your %s" % words


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
