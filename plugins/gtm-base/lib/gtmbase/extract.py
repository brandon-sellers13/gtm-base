"""Turning the three kinds of file the plugin opens itself into plain text.

Markdown, plain text, and rows of values are the only things read here. Every
other kind of document is read by the assistant's own file reader, or saved as
a PDF, or pasted in, which is why nothing in this module knows how to open a
slide file or a word processor file.

Three things are true of everything that comes out. It is text, never bytes.
It has one kind of line ending. And it came out of a file that was read once,
whole, with a cap on how much of it we would take.

Nothing here decides whether a file may be read. That question was already
answered by the list the person agreed to, and `sources.read_allowed` is what
holds the answer.
"""

from __future__ import annotations

import csv
import io
import os
from typing import List, Tuple

from . import constants
from .errors import SourceRejected

# How far into a file we look for a zero byte before calling it text. A file
# that only turns into bytes further in than this is still read as text: the
# question being answered is "was this ever meant to be read", and the answer
# to that is at the front.
BINARY_SNIFF_BYTES = 4096

# The note codes this module can return.
NOTE_ROWS_CAPPED = "rows-capped"
NOTE_CHARACTERS_REPLACED = "characters-replaced"
NOTE_EMPTY = "empty"

# What separates one value from the next when rows become lines of text.
CELL_SEPARATOR = " | "

# The mark some programs put at the front of a text file to say how it is
# written. A reader never sees it, so it never reaches a prompt either.
BYTE_ORDER_MARK = "﻿"


def extract(path: str, kind: str) -> Tuple[str, List[str]]:
    """Read one file and return its text and any notes about how it was read.

    The notes are codes, never sentences, so a caller can say what happened in
    its own words. `rows-capped` means there were more rows than we took.
    `characters-replaced` means the file was not written the way it claimed to
    be and some characters could not be turned into letters. `empty` means
    there was nothing in it.
    """
    if kind not in ("markdown", "text", "csv"):
        raise SourceRejected(
            "this kind of file is not one the plugin opens", code="unsupported"
        )
    payload = _read_bytes(path)
    if b"\x00" in payload[:BINARY_SNIFF_BYTES]:
        raise SourceRejected("this file is not text", code="binary")

    notes: List[str] = []
    text = _decode(payload, notes)
    if kind == "csv":
        text = _rows_as_text(text, notes)
    if not text.strip():
        notes.append(NOTE_EMPTY)
    return text, notes


def _read_bytes(path: str) -> bytes:
    """The whole file, or a refusal. A link is never opened."""
    if not path or os.path.islink(path) or not os.path.isfile(path):
        raise SourceRejected("this file could not be read", code="unreadable")
    try:
        size = os.path.getsize(path)
    except OSError:
        raise SourceRejected("this file could not be read", code="unreadable")
    if size > constants.SOURCE_MAX_BYTES:
        raise SourceRejected("this file is larger than we read", code="too-large")
    try:
        with open(path, "rb") as stream:
            return stream.read(constants.SOURCE_MAX_BYTES + 1)
    except OSError:
        raise SourceRejected("this file could not be read", code="unreadable")


def _decode(payload: bytes, notes: List[str]) -> str:
    """Bytes as text, with one kind of line ending and no mark at the front."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", errors="replace")
        notes.append(NOTE_CHARACTERS_REPLACED)
    if text.startswith(BYTE_ORDER_MARK):
        text = text[len(BYTE_ORDER_MARK) :]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _rows_as_text(text: str, notes: List[str]) -> str:
    """Rows of values as one heading line and one line per row.

    A value holding a line break is written on one line anyway, because a row
    that turns into two lines stops being a row a reader can follow.
    """
    lines: List[str] = []
    reader = csv.reader(io.StringIO(text))
    taken = 0
    capped = False
    for number, row in enumerate(reader):
        if number > constants.CSV_MAX_ROWS:
            capped = True
            break
        lines.append(CELL_SEPARATOR.join(_flatten(cell) for cell in row))
        taken += 1
    if capped:
        notes.append(NOTE_ROWS_CAPPED)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _flatten(cell: str) -> str:
    """One value written on one line."""
    return " ".join(str(cell).split())
