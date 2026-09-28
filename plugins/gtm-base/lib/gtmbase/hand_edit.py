"""The hand edit: the one question it asks, and how its change is shown.

Somebody edits a document in their base themselves and wants the edit kept.
The 0.3.1 live check (2026-09-27, step 5) found three things wrong with how
that went. It asked two questions where one would do, and the bare "What
changed, and why?" did not say what it was asking or what the answer was for.
It filed a corrected fact as a correction that flagged nothing, so every other
document still repeating the old fact stayed unflagged. And it showed a five
word edit as the whole paragraph three times, under a "What changed:" line cut
off in the middle of a number.

Brandon decided all three on the same day (calls 33, 34 and 49 of the plan).
This module holds what those decisions say: the one question, in a long form
for the first three hand edits a person keeps on this computer and a short
form after that; the three kinds of answer; and the showing of a hand edit as
the changed sentence once, with what was taken out and put in marked.
"""

from __future__ import annotations

import difflib
import re
from typing import List, Optional, Tuple

from . import state

# --- The one question (call 33) ----------------------------------------------

# Brandon's wording, word for word, with the one change call 34 made to the
# question itself. The explanation comes first the first three times a person
# keeps a hand edit on this computer, and whenever they ask why they are being
# asked.
WHY_WE_ASK = (
    "Because you changed a document in your base, GTM Base keeps a short "
    "record of it. That gives you a history of why your context changed, and "
    "it lets GTM Base check your other documents against it, so anything that "
    "still says the old thing gets flagged. The record holds four things: what "
    "changed about the business, why, where it came from, and which documents "
    "it affects. I work out the last one myself."
)
LONG_ASK = (
    "So, in a sentence or two: what changed (in the business, or in a fact you "
    "state about it), why, and where did it come from? If this was only a "
    "wording fix and nothing about the business changed, just say so and "
    "nothing is recorded."
)
# From the fourth hand edit a person keeps.
SHORT_ASK = (
    "I'll keep a record of this edit so your other documents can be checked "
    "against it. What changed (in the business, or in a fact you state about "
    "it), why, and where did it come from? If it was only a wording fix, say so."
)
# How many hand edits a person keeps before the question is asked short.
LONG_FORM_TIMES = 3
# Where the count is kept, in this person's seat for the base.
SEAT_KEY = "hand_edits_kept"


def kept_so_far(base_id: str) -> int:
    """How many hand edits this person has kept in this base on this computer."""
    seat, _problems = state.load_seat(base_id)
    value = seat.get(SEAT_KEY)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def one_more_kept(base_id: str) -> int:
    """Count one more hand edit kept, and say how many that makes."""
    count = kept_so_far(base_id) + 1
    state.update_seat(base_id, **{SEAT_KEY: count})
    return count


def question(base_id: str, why: bool = False) -> str:
    """The one question a hand edit asks, long or short.

    Long for the first three hand edits a person keeps, and long whenever they
    ask why they are being asked; short from the fourth.
    """
    if why or kept_so_far(base_id) < LONG_FORM_TIMES:
        return "%s\n\n%s" % (WHY_WE_ASK, LONG_ASK)
    return SHORT_ASK


# --- The three answers (call 34) ---------------------------------------------

# Something about the business changed: a context change is recorded.
KIND_BUSINESS = "business"
# A fact the company states was corrected: a context change is recorded as
# well, worded as the corrected fact replacing the old one, so every document
# still repeating the old fact is flagged.
KIND_FACT = "fact"
# Only the wording changed: nothing is recorded, no correction record is
# written, and the edit takes the short route (call 49).
KIND_WORDING = "wording"
KINDS = (KIND_BUSINESS, KIND_FACT, KIND_WORDING)
# The kinds that record a context change.
RECORDS_A_CHANGE = (KIND_BUSINESS, KIND_FACT)
# The word a corrected fact is written with, so that what it replaced is in
# the change itself: "over 1 million since 2017, replacing the 500k a year we
# used to cite".
REPLACING = "replacing"

# What a fix to wording only is called, as "What changed:" and in the saved
# history (the live check, step 6, finding 1).
TYPO_FIX = "A typo fix."


# --- Plain words from a line of a document ----------------------------------

_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_|`)")
_WHITESPACE_RE = re.compile(r"\s+")


def plain_words(line: str) -> str:
    """One line of a document as a person would say it, marks taken off.

    The heading marks, the bullet, the quote mark and the emphasis marks go;
    every word stays, and nothing is ever cut short.
    """
    text = str(line or "").strip()
    text = text.lstrip("#").strip()
    text = text.lstrip(">").strip()
    text = _BULLET_RE.sub("", text)
    text = _EMPHASIS_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def changed_line(before: str, after: str) -> str:
    """The first line the change put in, in plain words, and all of it.

    "What changed:" used to carry the first line of the whole part, cut off
    after sixty characters, so it quoted a bullet nobody changed and stopped in
    the middle of a number (the live check, step 5, finding 3, and step 6,
    finding 1). It is the line that changed now, whole. A change that only
    takes words out has no line of its own, and says nothing here.
    """
    was = str(before or "").split("\n")
    now = str(after or "").split("\n")
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    for operation, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if operation not in ("replace", "insert"):
            continue
        for line in now[j1:j2]:
            words = plain_words(line)
            if words:
                return words
    return ""


def taken_out_line(before: str, after: str) -> str:
    """The first line a change only takes out, in plain words, and all of it."""
    was = str(before or "").split("\n")
    now = str(after or "").split("\n")
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    for operation, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if operation not in ("replace", "delete"):
            continue
        for line in was[i1:i2]:
            words = plain_words(line)
            if words:
                return words
    return ""


# --- The changed sentence, with the change marked (step 5, finding 1) --------

# The sentence a hand edit's marked changes are shown under. The heading and
# the words come out of the document, so they sit in the fence below it and
# never in it.
MARKED = (
    "What you changed in %s, under the heading each change sits in, with what "
    "you took out and what you put in marked:"
)

TOOK_OUT = "[took out: %s]"
PUT_IN = "[put in: %s]"

_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)
_SENTENCE_END = (".", "!", "?")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


def _marked_pieces(before: str, after: str) -> List[Tuple[bool, str]]:
    """The words of `after`, with each difference from `before` marked.

    Each piece says whether it is a mark or words that stayed the same.
    """
    was = _tokens(before)
    now = _tokens(after)
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    # Two differences with nothing but a space between them are one
    # difference to a reader, so "a year" becoming "since 2017" is marked
    # once rather than word by word.
    codes = matcher.get_opcodes()
    runs: List[Tuple[str, int, int, int, int]] = []
    index = 0
    while index < len(codes):
        operation, i1, i2, j1, j2 = codes[index]
        if operation == "equal":
            runs.append(("equal", i1, i2, j1, j2))
            index += 1
            continue
        # A change, carried on across any space that only separates it from
        # the next change.
        end_i, end_j = i2, j2
        index += 1
        while index < len(codes):
            following = codes[index]
            if following[0] != "equal":
                end_i, end_j = following[2], following[4]
                index += 1
                continue
            between = "".join(now[following[3] : following[4]])
            if (
                not between.strip()
                and index + 1 < len(codes)
                and codes[index + 1][0] != "equal"
            ):
                end_i, end_j = codes[index + 1][2], codes[index + 1][4]
                index += 2
                continue
            break
        runs.append(("change", i1, end_i, j1, end_j))
    pieces: List[Tuple[bool, str]] = []
    for operation, i1, i2, j1, j2 in runs:
        if operation != "change":
            pieces.append((False, "".join(now[j1:j2])))
            continue
        taken = "".join(was[i1:i2])
        put = "".join(now[j1:j2])
        if taken:
            pieces.append((True, TOOK_OUT % taken))
        if put:
            pieces.append((True, PUT_IN % put))
    return pieces


def _only_the_changed_sentences(pieces: List[Tuple[bool, str]]) -> str:
    """The sentences a mark falls in, from the first to the last, and no more.

    A sentence ends only inside words that stayed the same, after a full stop,
    a question mark or an exclamation mark followed by a space. The sentences
    before the first mark and after the last one are left off, because the
    point is to read the edit in seconds; the whole text is there on request.
    """
    # Split the unchanged runs at sentence ends, keeping every character.
    runs: List[Tuple[bool, str]] = []
    for is_mark, text in pieces:
        if is_mark:
            runs.append((True, text))
            continue
        start = 0
        for match in re.finditer(r"[.!?][\"')\]]*\s+", text):
            runs.append((False, text[start : match.end()]))
            runs.append((None, ""))  # a sentence ends here
            start = match.end()
        if start < len(text):
            runs.append((False, text[start:]))
    sentences: List[List[Tuple[bool, str]]] = [[]]
    for kind, text in runs:
        if kind is None:
            sentences.append([])
            continue
        sentences[-1].append((kind, text))
    marked = [
        index
        for index, sentence in enumerate(sentences)
        if any(kind for kind, _text in sentence)
    ]
    if not marked:
        return "".join(text for _kind, text in pieces)
    kept = sentences[marked[0] : marked[-1] + 1]
    return "".join(text for sentence in kept for _kind, text in sentence).strip()


def marked(before: str, after: str) -> str:
    """The changed sentences once, with what was taken out and put in marked."""
    return _only_the_changed_sentences(_marked_pieces(before, after))


def _heading_above(lines: List[str], index: int) -> str:
    """The nearest heading above one line of a document, or nothing."""
    for line in reversed(lines[:index]):
        if re.match(r"^#{1,6}\s+\S", line):
            return line.strip()
    return ""


def marked_changes(was_text: str, now_text: str) -> List[Tuple[str, str]]:
    """Every change between two versions of a document, each marked.

    One (heading, marked text) for each run of lines that changed, in the
    order they come, where the heading is the nearest one above the run in the
    document as it is now. Every line that differs is in one of them, so
    nothing saying yes would save goes unshown; only the unchanged sentences
    around a change are left off. A run of one line becoming one line is
    narrowed to the sentences that changed.
    """
    was = str(was_text or "").split("\n")
    now = str(now_text or "").split("\n")
    matcher = difflib.SequenceMatcher(None, was, now, autojunk=False)
    found: List[Tuple[str, str]] = []
    for operation, i1, i2, j1, j2 in matcher.get_opcodes():
        if operation == "equal":
            continue
        taken = "\n".join(was[i1:i2])
        put = "\n".join(now[j1:j2])
        heading = _heading_above(now, j1)
        if operation == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            text = marked(taken, put)
        elif operation == "delete":
            text = TOOK_OUT % taken
        elif operation == "insert":
            text = PUT_IN % put
        else:
            text = "".join(piece for _mark, piece in _marked_pieces(taken, put))
        found.append((heading, text))
    return found


def as_read(changes: List[Tuple[str, str]]) -> str:
    """The marked changes as one block, each under the heading it sits in."""
    blocks = []
    previous: Optional[str] = None
    for heading, text in changes:
        if heading and heading != previous:
            blocks.append(heading)
        previous = heading
        blocks.append(text)
    return "\n\n".join(blocks)
