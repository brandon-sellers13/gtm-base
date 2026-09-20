"""The names a person reads for the things in their base.

A marketing lead does not have a file called `context/strategy/icp.md` and does
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

# The name each file the product knows about is read aloud by.
KNOWN_DOCUMENTS = {
    "context/strategy/icp.md": "your customer profile",
    "context/strategy/positioning.md": "your positioning",
    constants.MAP_PATH: "your base's map",
}

# Where one segment of the customer profile lives.
SEGMENTS_DIR = "context/strategy/segments"

# What a change with nothing written in it yet is called.
CHANGE_WITHOUT_A_LINE = "the change you recorded"

_SEPARATORS_RE = re.compile(r"[-_]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(path: str) -> str:
    """The path as the base stores it, with the separators this machine uses."""
    return str(path).replace(os.sep, "/").strip().lstrip("./")


def _words(stem: str) -> str:
    """A file stem read as words, so `mid-market` becomes `mid market`."""
    return _WHITESPACE_RE.sub(" ", _SEPARATORS_RE.sub(" ", stem)).strip()


def is_segment(path: str) -> bool:
    """True when the path is one segment of the customer profile."""
    normalized = _normalize(path)
    return normalized.startswith(SEGMENTS_DIR + "/") and normalized.endswith(".md")


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
    words = _words(stem)
    if not words:
        raise ValueError("a document name needs a file name to work from")
    if is_segment(normalized):
        return "your %s segment" % words
    return "your %s" % words


def change_name(first_line: Optional[str], happened_on: Optional[str] = None) -> str:
    """What a person calls one context change: its first line and its date.

    The first line is the sentence the person gave. The date is the day the
    change happened, not the day it was written down, because the day it
    happened is the one they remember.
    """
    line = _first_sentence(first_line)
    day = (happened_on or "").strip()
    if not line:
        line = CHANGE_WITHOUT_A_LINE
    if day:
        return "%s (%s)" % (line, day)
    return line


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
