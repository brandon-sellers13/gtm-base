"""Whether a base has unsaved work in it, and which files that work is in.

Every check in this plugin that asks "is anything unsaved in this base?" asks
it here, so the answer is the same wherever it is asked: approving a prepared
change or a hand edit, the move of the context changes, the review bringing a
base up to date, the session start update, setup, and every write that refuses
a folder somebody is still working in.

The answer leaves out the files an operating system makes on its own. A Mac
writes a `.DS_Store` file into every folder somebody opens in Finder, and the
release A live check (step 5, 2026-09-27) found that one of those, and nothing
else, was enough to refuse approving a hand edit, on the very step that asks
the person to open their base in an editor. Nobody wrote those files and
nobody can act on them, so they are not unsaved work.

They are only left out while they are untracked. A clutter file somebody saved
into the base once is part of what the base holds, and a change to it is a
change to the base like any other: leaving it out would let a write save over
it, or save it, without anybody having read the difference. So a tracked
`.DS_Store` that was changed still counts, and the refusal says it is only a
file the computer made.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Sequence, Tuple

from . import constants, names
from .gitcmd import DEFAULT_TIMEOUT_SECONDS, GitRunner, status_entries

# --- The files an operating system makes on its own ---------------------------

# Files, by their exact name, compared without regard to letter case because
# Windows writes both `desktop.ini` and `Desktop.ini`. `Icon\r` is the file a
# Mac writes when a folder is given a custom icon; its name really does end in
# a carriage return.
CLUTTER_FILE_NAMES = (".DS_Store", "Thumbs.db", "desktop.ini", "Icon\r")
# Folders a Mac keeps at the top of a disk, and anything inside them.
CLUTTER_FOLDER_NAMES = (".Spotlight-V100", ".Trashes", ".fseventsd")
# The start of every AppleDouble file, the `._` copy a Mac writes beside a file
# on a disk that cannot hold its extra details.
APPLEDOUBLE_PREFIX = "._"

_FILES_FOLDED = frozenset(name.casefold() for name in CLUTTER_FILE_NAMES)
_FOLDERS_FOLDED = frozenset(name.casefold() for name in CLUTTER_FOLDER_NAMES)

# The lines a new base's ignore file carries for the same files. `Icon\r` is
# written as a pattern rather than as its name, because a carriage return in
# the template would be read back as the end of a line, and `Icon` alone would
# hide a file somebody named Icon. The bracket matches exactly one character
# that is not a printable one, which is the carriage return and nothing a
# person types.
IGNORE_LINES = (
    ".DS_Store",
    "._*",
    "Thumbs.db",
    "desktop.ini",
    "Icon[^ -~]",
    ".Spotlight-V100/",
    ".Trashes/",
    ".fseventsd/",
)


def is_clutter(path: str) -> bool:
    """Whether a path is a file the operating system made, or inside one of its folders."""
    parts = [part for part in str(path).replace(os.sep, "/").split("/") if part]
    if not parts:
        return False
    for part in parts:
        if part.casefold() in _FOLDERS_FOLDED:
            return True
    last = parts[-1]
    if last.casefold() in _FILES_FOLDED:
        return True
    return last.startswith(APPLEDOUBLE_PREFIX) and len(last) > len(APPLEDOUBLE_PREFIX)


# --- Asking git ---------------------------------------------------------------

# Every untracked file is listed on its own rather than folded into the folder
# it sits in. Folded, a new folder holding nothing but a `.DS_Store` came back
# as the folder's name, which is not clutter by its name, and the check would
# have refused on it. `-z` keeps each name exactly as it is on the disk, which
# is how `Icon\r` and a name with an accent are compared as themselves.
STATUS_ARGS = ("status", "--porcelain", "-z", "--untracked-files=all")


class Status(object):
    """What one look at a base found.

    `ran` is false when git could not be asked at all. `entries` is None when
    git answered with something this cannot read, which every caller treats as
    unsaved work it may not write over, and otherwise the unsaved entries with
    untracked clutter already left out, each as (its two letters, its paths).
    """

    __slots__ = ("ran", "entries")

    def __init__(self, ran: bool, entries: Optional[List[Tuple[str, List[str]]]]):
        self.ran = ran
        self.entries = entries

    @property
    def clean(self) -> bool:
        return self.ran and self.entries is not None and not self.entries

    def paths(self) -> List[str]:
        """Every path an unsaved entry names, in the order git gave them."""
        found: List[str] = []
        for _letters, named in self.entries or []:
            for one in named:
                if one not in found:
                    found.append(one)
        return found


def _is_untracked_clutter(letters: str, named: Sequence[str]) -> bool:
    return letters == "??" and all(is_clutter(one) for one in named)


def look(
    base_root: str, git: GitRunner, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> Status:
    """The unsaved work in a base, leaving out files the computer made on its own."""
    result = git.run(list(STATUS_ARGS), cwd=base_root, timeout=timeout)
    if not result.ok:
        return Status(False, None)
    entries = status_entries(result.stdout)
    if entries is None:
        return Status(True, None)
    kept = [
        (letters, named)
        for letters, named in entries
        if not _is_untracked_clutter(letters, named)
    ]
    return Status(True, kept)


# --- Saying which files it is -------------------------------------------------

# The sentence that says where the unsaved work is. It sits between a refusal
# and its one request, so the refusal still ends in the one thing to do.
WHERE = "They are in %s."
# What a tracked file the computer made is called, since its own name is not
# one a person can be read.
COMPUTER_MADE_ONE = "a file your computer made on its own"
COMPUTER_MADE_MANY = "%s files your computer made on their own"
# What a file is called when its name cannot be read out safely.
ONE_OF_YOUR_FILES = "one of your files"
SOME_OF_YOUR_FILES = "%s of your files"
ONE_OTHER_FILE = "one other file"
# What a file holding one context change is called when a sentence names it on
# its own. Its file name is the change's identifier, which is never read out.
ONE_OF_YOUR_CONTEXT_CHANGES = "one of your context changes"
OTHER_FILES = "%s other files"

# How many files are named before the rest are counted.
MOST_NAMED = 3

_COUNT_WORDS = (
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

# A file name that may be read out: plain letters, digits, spaces, dots and
# hyphens, and nothing else. Anything more is not repeated back, because a
# name is read out in the middle of words the assistant relays. It has to
# start and end with a letter or a digit, so a name made only of dots or
# spaces, or one ending in a dot, never turns the sentence into punctuation.
_PLAIN_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9 .-]{0,78}[A-Za-z0-9])?$")

# The folders GTM Base keeps its own records in. A file there is named by what
# it is not, because its name is an identifier and nobody works in there.
_OWN_FOLDERS = ("work/", constants.CORRECTIONS_DIR + "/", ".claude/")


def _counted(number: int) -> str:
    if 0 <= number < len(_COUNT_WORDS):
        return _COUNT_WORDS[number]
    return str(number)


def _name_for(path: str) -> Optional[str]:
    """What one unsaved file is called, or None when it cannot be named."""
    normalized = str(path).replace(os.sep, "/")
    stem = normalized.rstrip("/").rsplit("/", 1)[-1]
    if normalized.startswith(constants.CONTEXT_DIR + "/") and normalized.endswith(".md"):
        # The document's own name only when its file name is plain words, so
        # a name such as `-.md` is counted rather than read out as nothing.
        if not _PLAIN_FILE_NAME_RE.match(stem[: -len(".md")]):
            return None
        try:
            return names.document_name(normalized)
        except ValueError:
            return None
    if normalized.startswith(_OWN_FOLDERS):
        return None
    if _PLAIN_FILE_NAME_RE.match(stem):
        return stem
    return None


def plain_name(path: str) -> str:
    """What one file is called when a sentence names it on its own."""
    if is_clutter(path):
        return COMPUTER_MADE_ONE
    normalized = str(path).replace(os.sep, "/")
    for folder in (constants.CHANGES_DIR, constants.LEGACY_CHANGES_DIR):
        if normalized.startswith(folder + "/"):
            return ONE_OF_YOUR_CONTEXT_CHANGES
    return _name_for(path) or ONE_OF_YOUR_FILES


def _joined(pieces: Sequence[str]) -> str:
    if len(pieces) == 1:
        return pieces[0]
    return "%s and %s" % (", ".join(pieces[:-1]), pieces[-1])


def where(paths: Sequence[str]) -> str:
    """The unsaved files as a person says them, for example "your positioning"."""
    named: List[str] = []
    unnamed = 0
    computer_made = 0
    for path in paths:
        if is_clutter(path):
            computer_made += 1
            continue
        name = _name_for(path)
        # Two files that read out the same are two files, so the second one
        # is counted rather than folded into the first.
        if name is None or name in named or len(named) >= MOST_NAMED:
            unnamed += 1
        else:
            named.append(name)
    pieces = list(named)
    if unnamed:
        if named:
            pieces.append(
                ONE_OTHER_FILE if unnamed == 1 else OTHER_FILES % _counted(unnamed)
            )
        else:
            pieces.append(
                ONE_OF_YOUR_FILES
                if unnamed == 1
                else SOME_OF_YOUR_FILES % _counted(unnamed)
            )
    if computer_made:
        pieces.append(
            COMPUTER_MADE_ONE
            if computer_made == 1
            else COMPUTER_MADE_MANY % _counted(computer_made)
        )
    if not pieces:
        return ""
    return _joined(pieces)


def where_sentence(paths: Sequence[str]) -> str:
    """The one sentence naming the unsaved files, or nothing when none are known."""
    said = where(paths)
    return WHERE % said if said else ""


def refusal(template: str, fallback: str, status: Status, allowed=()) -> str:
    """A refusal for unsaved work with the files it is about said in it.

    The template holds one `%s` where the sentence naming the files goes, just
    before its one request. When git's answer could not be read, or nothing
    unsaved is left once the allowed paths are taken out, the fallback is said
    as it always was.
    """
    if status.entries is None:
        return fallback
    left = [one for one in status.paths() if one not in set(allowed)]
    sentence = where_sentence(left)
    if not sentence:
        return fallback
    return template % sentence
