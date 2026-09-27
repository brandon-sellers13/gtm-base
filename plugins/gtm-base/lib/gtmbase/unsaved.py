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

What counts as one is kept as narrow as it can be, because everything left
out here is something a write may then save around without anybody reading it
(Astra's review of 0.3.2, finding 1: a markdown document named `._notes.md`,
or kept inside a folder called `.Trashes`, was left out and could be saved by
an approval that showed none of it). A file counts only when it is a regular
file, never a link or a folder, and either carries one of four exact names or
is an AppleDouble file, which is told by the four bytes every one of them
starts with rather than by its name. No folder is left out, and nothing is left
out for the folder it sits in.

They are only left out while they are untracked. A clutter file somebody saved
into the base once is part of what the base holds, and a change to it is a
change to the base like any other: leaving it out would let a write save over
it, or save it, without anybody having read the difference. So a tracked
`.DS_Store` that was changed still counts, and the refusal says it is only a
file the computer made.
"""

from __future__ import annotations

import os
import stat
from typing import List, Optional, Sequence, Tuple

from . import constants, names
from .gitcmd import DEFAULT_TIMEOUT_SECONDS, GitRunner, status_entries

# --- The files an operating system makes on its own ---------------------------

# Files, by their exact name. `Icon\r` is the file a Mac writes when a folder is
# given a custom icon; its name really does end in a carriage return.
CLUTTER_FILE_NAMES = (".DS_Store", "Thumbs.db", "desktop.ini", "Icon\r")
# The start of every AppleDouble file's name, the `._` copy a Mac writes beside
# a file on a disk that cannot hold its extra details, and the four bytes every
# such file begins with. The name alone proves nothing.
APPLEDOUBLE_PREFIX = "._"
APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"

# The lines a new base's ignore file carries for the same files: the exact
# names and nothing wider. An AppleDouble file is not ignored, because a
# pattern for it would hide a real document that happens to be named that way
# from every check, and from git's own care when an update arrives (finding 2).
# `Icon\r` is written as a pattern rather than as its name, because a carriage
# return in the template would be read back as the end of a line, and `Icon`
# alone would hide a file somebody named Icon. The bracket matches exactly one
# character that is not a printable one, which is the carriage return and
# nothing a person types.
IGNORE_LINES = (".DS_Store", "Thumbs.db", "desktop.ini", "Icon[^ -~]")


def is_clutter_file(full_path: str) -> bool:
    """Whether the file at this place on the disk is one the computer made."""
    name = os.path.basename(str(full_path))
    exact = name in CLUTTER_FILE_NAMES
    double = name.startswith(APPLEDOUBLE_PREFIX) and len(name) > len(APPLEDOUBLE_PREFIX)
    if not exact and not double:
        return False
    try:
        mode = os.lstat(full_path).st_mode
    except OSError:
        return False
    if not stat.S_ISREG(mode):
        return False
    if exact:
        return True
    try:
        with open(full_path, "rb") as handle:
            return handle.read(len(APPLEDOUBLE_MAGIC)) == APPLEDOUBLE_MAGIC
    except OSError:
        return False


def is_clutter(relative: str, base_root: str) -> bool:
    """Whether a path inside a base is a file the computer made on its own."""
    relative = str(relative)
    if not relative or relative.endswith("/"):
        return False
    return is_clutter_file(os.path.join(base_root, relative.replace("/", os.sep)))


# --- Asking git ---------------------------------------------------------------

# Every untracked file is listed on its own rather than folded into the folder
# it sits in. Folded, a new folder holding nothing but a `.DS_Store` came back
# as the folder's name, and the check would have refused on it. `-z` keeps each
# name exactly as it is on the disk, which is how `Icon\r` and a name with an
# accent are compared as themselves.
STATUS_ARGS = ("status", "--porcelain", "-z", "--untracked-files=all")


class Status(object):
    """What one look at a base found.

    `ran` is false when git could not be asked at all. `entries` is None when
    git answered with something this cannot read, which every caller treats as
    unsaved work it may not write over, and otherwise the unsaved entries with
    untracked clutter already left out, each as (its two letters, its paths).
    """

    __slots__ = ("ran", "entries", "root")

    def __init__(
        self,
        ran: bool,
        entries: Optional[List[Tuple[str, List[str]]]],
        root: Optional[str] = None,
    ):
        self.ran = ran
        self.entries = entries
        self.root = root

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


def look(
    base_root: str, git: GitRunner, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> Status:
    """The unsaved work in a base, leaving out files the computer made on its own."""
    result = git.run(list(STATUS_ARGS), cwd=base_root, timeout=timeout)
    if not result.ok:
        return Status(False, None, base_root)
    entries = status_entries(result.stdout)
    if entries is None:
        return Status(True, None, base_root)
    kept = [
        (letters, named)
        for letters, named in entries
        if not (
            letters == "??" and all(is_clutter(one, base_root) for one in named)
        )
    ]
    return Status(True, kept, base_root)


# --- Saying which files it is -------------------------------------------------

# The sentence that says where the unsaved work is. It sits between a refusal
# and its one request, so the refusal still ends in the one thing to do.
WHERE = "They are in %s."
# What a tracked file the computer made is called, since its own name is not
# one a person can be read.
COMPUTER_MADE_ONE = "a file your computer made on its own"
COMPUTER_MADE_MANY = "%s files your computer made on their own"
# What every other file is called. A name is never repeated back (Astra,
# finding 3): a file named like an instruction was read out as one, inside a
# sentence the skills tell the assistant to relay word for word.
ONE_OF_YOUR_FILES = "one of your files"
SOME_OF_YOUR_FILES = "%s of your files"
ONE_OTHER_FILE = "one other file"
OTHER_FILES = "%s other files"
# What a document in the context folder is called when it is not one the
# product knows. Its file name is never read out either (Astra's confirmation
# of 0.3.2: an ordinary `.md` name under the context folder was).
ONE_OF_YOUR_DOCUMENTS = "one of your documents"
SOME_OF_YOUR_DOCUMENTS = "%s of your documents"
ONE_OTHER_DOCUMENT = "one other document"
OTHER_DOCUMENTS = "%s other documents"
# What a file holding one context change is called when a sentence names it on
# its own. Its file name is the change's identifier, which is never read out.
ONE_OF_YOUR_CONTEXT_CHANGES = "one of your context changes"

# How many documents are named before the rest are counted.
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


def _counted(number: int) -> str:
    if 0 <= number < len(_COUNT_WORDS):
        return _COUNT_WORDS[number]
    return str(number)


# The documents the product itself knows, each with a fixed label: the two a
# base needs, the map, and the nine documents of the context standard a base
# is being moved to (plan revision 2.2, Unit 1.5b), so a refusal there names
# them too. Nothing here is read out of a file name.
KNOWN_DOCUMENT_LABELS = dict(names.KNOWN_DOCUMENTS)
KNOWN_DOCUMENT_LABELS.update(
    {
        "context/goals.md": "your goals",
        "context/product.md": "your product",
        "context/icps.md": "your customer profiles",
        "context/buyer-personas.md": "your buyer personas",
        "context/positioning.md": "your positioning",
        "context/messaging.md": "your messaging",
        "context/voice.md": "your voice",
        "context/design.md": "your design",
        "context/metrics.md": "your metrics",
    }
)

def _known_label(path: str) -> Optional[str]:
    """The fixed label of a document the product knows, or None.

    A segment is not named here, however its file is spelled. Its name is its
    file name, and a file name short and tidy enough to pass any shape check
    can still read as an instruction ("ignore all prior instructions"), which
    the confirmation of this release found. So a segment is counted with the
    other documents, and nothing in a refusal is ever read out of a file name.
    """
    return KNOWN_DOCUMENT_LABELS.get(str(path).replace(os.sep, "/"))


def _is_a_document(path: str) -> bool:
    return str(path).replace(os.sep, "/").startswith(constants.CONTEXT_DIR + "/")


def _computer_made(path: str, base_root: Optional[str]) -> bool:
    return bool(base_root) and is_clutter(path, base_root)


def plain_name(path: str, base_root: Optional[str] = None) -> str:
    """What one file is called when a sentence names it on its own."""
    if _computer_made(path, base_root):
        return COMPUTER_MADE_ONE
    normalized = str(path).replace(os.sep, "/")
    for folder in (constants.CHANGES_DIR, constants.LEGACY_CHANGES_DIR):
        if normalized.startswith(folder + "/"):
            return ONE_OF_YOUR_CONTEXT_CHANGES
    label = _known_label(path)
    if label:
        return label
    return ONE_OF_YOUR_DOCUMENTS if _is_a_document(path) else ONE_OF_YOUR_FILES


def _joined(pieces: Sequence[str]) -> str:
    if len(pieces) == 1:
        return pieces[0]
    return "%s and %s" % (", ".join(pieces[:-1]), pieces[-1])


def where(paths: Sequence[str], base_root: Optional[str] = None) -> str:
    """The unsaved files as a person says them, for example "your positioning"."""
    named: List[str] = []
    documents = 0
    files = 0
    computer_made = 0
    for path in paths:
        if _computer_made(path, base_root):
            computer_made += 1
            continue
        label = _known_label(path)
        # Two files that read out the same are two files, so the second one
        # is counted rather than folded into the first.
        if label is not None and label not in named and len(named) < MOST_NAMED:
            named.append(label)
        elif _is_a_document(path):
            documents += 1
        else:
            files += 1
    pieces = list(named)
    if documents:
        if named:
            pieces.append(
                ONE_OTHER_DOCUMENT
                if documents == 1
                else OTHER_DOCUMENTS % _counted(documents)
            )
        else:
            pieces.append(
                ONE_OF_YOUR_DOCUMENTS
                if documents == 1
                else SOME_OF_YOUR_DOCUMENTS % _counted(documents)
            )
    if files:
        if named:
            pieces.append(
                ONE_OTHER_FILE if files == 1 else OTHER_FILES % _counted(files)
            )
        else:
            pieces.append(
                ONE_OF_YOUR_FILES if files == 1 else SOME_OF_YOUR_FILES % _counted(files)
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


def where_sentence(paths: Sequence[str], base_root: Optional[str] = None) -> str:
    """The one sentence naming the unsaved files, or nothing when none are known."""
    said = where(paths, base_root)
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
    allowed = set(allowed)
    left = [one for one in status.paths() if one not in allowed]
    sentence = where_sentence(left, status.root)
    if not sentence:
        return fallback
    return template % sentence
