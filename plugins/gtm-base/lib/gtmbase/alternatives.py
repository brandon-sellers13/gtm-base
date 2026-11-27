"""A positioning that still holds the competitors in full (Track 4, Unit T4.4).

Competitors are their own document again (call 2). A base whose positioning
was written before that, with a long part about the alternatives, is told the
detail can move to a competitors document. It is said, never done: the move
reaches the positioning only as a change its owner approves, and nothing is
written by saying it.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from . import constants, formats
from .errors import PathError, ValidationError
from .fsutil import read_bytes

# A part counts as long past this many lines with words on them, or past this
# many level three headings, which is where the detail about each competitor
# outgrows the short list the positioning keeps.
LONG_LINES = 8
LONG_ITEMS = 3

_ABOUT_ALTERNATIVES = re.compile(r"alternative|competit", re.IGNORECASE)

MOVE_OFFER = (
    "Your positioning holds a long part about the alternatives. The detail "
    "about each one can move to a competitors document of its own, leaving the "
    "positioning a short list, through a change its owner approves. Say "
    "\"draft my competitors\" when you want to start; nothing moves before then."
)


def _long_part(text: str) -> bool:
    try:
        _block, body = formats.split_document(text)
    except (ValidationError, PathError):
        body = text
    for heading, part in formats.split_sections(body).items():
        if not _ABOUT_ALTERNATIVES.search(heading):
            continue
        lines = [line for line in part.split("\n") if line.strip()]
        items = [line for line in lines if re.match(r"^\s{0,3}###\s", line)]
        if len(lines) > LONG_LINES or len(items) > LONG_ITEMS:
            return True
    return False


def move_offer(base_root: str) -> Optional[str]:
    """The sentence to say when the positioning holds the competitors in full, or None.

    Only when the base holds no competitors document yet, because once it
    does the move is the owner's to make through an ordinary change.
    """
    if os.path.lexists(os.path.join(base_root, *constants.COMPETITORS_PATH.split("/"))):
        return None
    data = read_bytes(os.path.join(base_root, "context", "positioning.md"))
    if data is None:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return MOVE_OFFER if _long_part(text) else None
