"""The questions a draft leaves open for the person, marked `[your call: ...]`.

A draft is written whole and first, and where something is the person's call
rather than the drafter's, the draft says its best reading and marks the spot
with the question, such as `[your call: is it twenty people or fifty?]`. The
third real run saved a file with one of those still in it, and nothing in the
base knew it was there.

Unit 1.7b of the 2026-09-19 plan makes an unanswered marker a state of its own
(requirement P27). It is worked out from the body every time the file is read
and never stored, so it can never drift out of step with the file, and it is
independent of the file's status, so a retained draft can never pass as
finished. A file holding one is neither confirmed nor complete. The review
lists each one and asks, and the answer becomes a prepared change the owner
approves, never a setup step writing over a file.

This module only finds them. Everything it hands back came out of a file
somebody could type into, so it is data, and every caller that shows a
question to the assistant holds it apart as data first.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from . import constants

_MARKER_RE = re.compile(constants.YOUR_CALL_PATTERN, re.IGNORECASE)
# A heading of any size, which is how the proposal editor reads one.
_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_FENCE = "---"


class Mark(object):
    """One open question, where it sits, and the part of the file it is in.

    `heading` is the part of the file the question sits in, as the level two
    heading line that opens that part, and `occurrence` says which one it is
    when the same heading appears more than once, counting the way the
    proposal editor counts. Both are None and zero when the question sits
    above the first such heading, where no prepared change can reach it.
    """

    __slots__ = ("number", "question", "marker", "heading", "occurrence", "line")

    def __init__(self, number, question, marker, heading, occurrence, line):
        self.number = number
        self.question = question
        self.marker = marker
        self.heading = heading
        self.occurrence = occurrence
        self.line = line

    @property
    def token(self) -> str:
        """A short name for this question that does not move when another goes.

        A number counts the questions in the document, so it points at a
        different one the moment an earlier one is answered. This is worked
        out from the part the question sits in and the question itself, so a
        review's token still names the same question later, or none at all
        (finding 2 of the unit's correctness review).
        """
        seed = "\n".join([str(self.heading), str(self.occurrence), self.question])
        return "q" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]

    def __repr__(self) -> str:
        return "Mark(number=%r, heading=%r)" % (self.number, self.heading)


def _body_start(lines: List[str]) -> int:
    """The first line after the settings block, or zero when there is none."""
    if not lines or lines[0].strip() != _FENCE:
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == _FENCE:
            return index + 1
    return 0


def _level(line: str) -> int:
    match = _HEADING_RE.match(line)
    return len(match.group(1)) if match else 0


def clean(question) -> str:
    """A question on one line, its spacing closed up, cut to the cap."""
    text = " ".join(str(question or "").split())
    cap = constants.YOUR_CALL_MAX_CHARS
    if len(text) > cap:
        text = text[:cap].rstrip() + "..."
    return text


def find(text) -> List[Mark]:
    """Every open question in a document's body, in the order they appear.

    The settings block is not read, because a marker belongs to what the
    document says and not to its settings.
    """
    lines = str(text or "").split("\n")
    start = _body_start(lines)
    marks: List[Mark] = []
    heading: Optional[str] = None
    occurrence = 0
    seen = {}
    for index in range(start, len(lines)):
        line = lines[index]
        stripped = line.strip()
        # Every line equal to a heading counts toward which one it is, the
        # way the proposal editor finds a heading again, so the part named
        # here is the part a prepared change will land in.
        if stripped:
            seen[stripped] = seen.get(stripped, 0) + 1
        if _level(line) == 2:
            heading = stripped
            occurrence = seen[stripped]
        elif _level(line) == 1:
            heading = None
            occurrence = 0
        for match in _MARKER_RE.finditer(line):
            marks.append(
                Mark(
                    len(marks) + 1,
                    clean(match.group(1)),
                    match.group(0),
                    heading,
                    occurrence,
                    index + 1,
                )
            )
    return marks


def count(text) -> int:
    """How many open questions a document holds."""
    return len(find(text))


def questions(text) -> tuple:
    """The open questions a document holds, as plain one line questions."""
    return tuple(mark.question for mark in find(text))


def holds(text, marker) -> bool:
    """Whether some text still holds this exact question, however it is spaced.

    The question is compared with its spacing closed up and its letter case
    folded, so writing it again on two lines or in capitals is still writing
    it again.
    """
    wanted = clean(_question_of(marker)).casefold()
    if not wanted and not str(marker or "").strip():
        return False
    # Read as written, line by line, the way the document itself is read, and
    # read again with the lines closed up, so a question wrapped over two
    # lines is found either way (finding 4 of the unit's correctness review).
    for version in (str(text or ""), " ".join(str(text or "").split())):
        for mark in find(version):
            if mark.question.casefold() == wanted:
                return True
    return False


def by_token(text, token) -> Optional[Mark]:
    """The open question in some text that a review's token names, or None."""
    for mark in find(text):
        if mark.token == str(token or ""):
            return mark
    return None


def _question_of(marker) -> str:
    match = _MARKER_RE.search(str(marker or ""))
    return match.group(1) if match else ""


def markers_in(text) -> List[str]:
    """The exact marker text of every open question in some text."""
    return [match.group(0) for match in _MARKER_RE.finditer(str(text or ""))]
