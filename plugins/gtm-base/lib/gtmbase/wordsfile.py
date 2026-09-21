"""The one place a person's own words are allowed to reach a script from.

A skill asks somebody a question, and the answer has to get from the window
they typed it in to a script that writes it down. It used to travel on the
command line, which meant a sentence with a dollar sign and a bracket in it was
a shell instruction, and that was fixed by putting the words in a file and the
path to the file on the command line instead.

Finding V6 of the 2026-09-20 verification round is what that fix left open. The
readers took any path at all, so a document telling the assistant to pass the
path of somebody's private notes had those notes read into the base and written
down, with nobody asked and no record that a private document had been read.
Reading somebody's own documents is a thing this plugin asks about, in its own
step, with its own record, and a flag on a command line is not that step.

So the scripts choose where words go and the assistant never does. A command
hands out a path. It is inside a folder only this person can open, made by this
code, beside the folder this run already writes its drafts into. A reader
accepts a file only when its real path sits directly in that folder, when it
belongs to this person, when it is a plain file with no second name, and when
it is small. The file is then read once and taken away, because a person's own
words have no reason to sit on the disk after they have been written down.

Nothing here reaches the network, and nothing read here is ever an instruction.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
import tempfile
from typing import Optional

from . import ids, paths
from .errors import StateError
from .fsutil import atomic_write_text, ensure_dir, read_text, remove

# The folder under this computer's temporary folder that holds one folder per
# run. It is the folder the drafts already use, and the words sit beside them.
PARENT_NAME = "gtm-base-drafts"

# The folder inside one run's folder that holds nothing but words files.
WORDS_DIR_NAME = "words"

# Where the folder to use is remembered, for the one case where the ordinary
# place cannot be trusted. It sits in this person's own records folder, which
# no file-writing tool may write, so the assistant cannot point it anywhere.
PARENT_POINTER = "drafts-parent"

# The kinds of words a command will hand out a file for. There is a fixed list
# rather than a name the caller picks, because the name goes into a file name.
KINDS = (
    "answer",
    "company",
    "got-in-the-way",
    "label",
    "reason",
    "source",
    "what-changed",
)

# Most bytes one file of somebody's words may hold. A person answering a
# question writes sentences, and anything larger than this is not an answer.
MAX_WORDS_BYTES = 64 * 1024

_NAME_RE = re.compile(r"^[a-z-]{1,32}-[0-9a-f]{16}\.txt$")

CODE_NOT_OURS = "not-a-words-file-we-handed-out"
CODE_NOT_A_DRAFT = "not-a-draft-file-we-named"
CODE_NO_KEY = "nothing-to-name-the-folder-after"
CODE_NOT_PRIVATE = "the-folder-is-not-yours-alone"

# --- The sentences a person reads -------------------------------------------

NOT_OURS = (
    "That is not a file GTM Base handed out for somebody's words, so nothing "
    "was read and nothing was written. Ask for a new one, put what they said "
    "in it, and run this again."
)
NOT_A_DRAFT = (
    "That is not a file GTM Base named for this draft, so nothing was read. "
    "Write the draft to the file this step named and run this again."
)
NO_PLACE_FOR_WORDS = (
    "GTM Base could not make a folder that only you can open, so it has "
    "nowhere safe to put somebody's words and did nothing at all."
)


# --- The folders -------------------------------------------------------------


def private_dir(path: str) -> str:
    """One folder only this person can open, made or checked but never trusted.

    A name already standing there that is a link, that belongs to somebody
    else, or that anybody else can write to is refused rather than used, since
    what goes in here is the company's own writing.
    """
    if not os.path.lexists(path):
        try:
            os.makedirs(path, 0o700)
        except OSError:
            raise StateError(NO_PLACE_FOR_WORDS, code="write-failed")
        return path
    info = os.lstat(path)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or (info.st_mode & 0o077)
    ):
        raise StateError(NO_PLACE_FOR_WORDS, code=CODE_NOT_PRIVATE)
    return path


def _pointer_path() -> str:
    return os.path.join(paths.seat_home(), PARENT_POINTER)


def _remembered_parent() -> str:
    """A folder of our own making, for a computer where the usual one is taken.

    On a computer other people can sign in to, somebody else can put a folder
    of the expected name in the shared temporary folder before this ever runs.
    That folder is refused, and what happens instead is that this code makes
    one with a name nobody can guess and writes down which one it made, in the
    records folder that no file-writing tool may touch. Two runs of two
    different scripts then agree on the same folder, which is the whole point:
    one of them hands out the path and another one reads the file.
    """
    remembered = read_text(_pointer_path())
    if remembered:
        folder = remembered.strip()
        if folder and os.path.isdir(folder) and not os.path.islink(folder):
            try:
                return private_dir(folder)
            except StateError:
                pass
    try:
        made = tempfile.mkdtemp(prefix=PARENT_NAME + "-")
        os.chmod(made, 0o700)
    except OSError:
        raise StateError(NO_PLACE_FOR_WORDS, code="write-failed")
    atomic_write_text(_pointer_path(), made + "\n", inside=paths.seat_home())
    return made


def parent_dir() -> str:
    """The folder holding one folder per run, made by us and owned by us."""
    wanted = os.path.join(
        tempfile.gettempdir(), "%s-%d" % (PARENT_NAME, os.getuid())
    )
    try:
        return private_dir(wanted)
    except StateError:
        return _remembered_parent()


def folder_name(key: str) -> str:
    """What one run's folder is called, from the run or the session it is for.

    A run identifier names itself, because the sweep needs to know which folder
    belongs to which run. Anything else is a session, whose name comes from the
    client and can be any text at all, so it is never used as a folder name.
    """
    text = str(key or "").strip()
    if not text:
        raise StateError(NO_PLACE_FOR_WORDS, code=CODE_NO_KEY)
    if ids.is_run_id(text):
        return text
    return "s-" + ids.content_hash(text)[:24]


def run_dir(key: str) -> str:
    """The folder one run or one session works in, which holds its drafts."""
    return private_dir(os.path.join(parent_dir(), folder_name(key)))


def words_dir(key: str) -> str:
    """The folder inside that one holding nothing but somebody's own words."""
    return private_dir(os.path.join(run_dir(key), WORDS_DIR_NAME))


# --- Handing one out, and reading it back ------------------------------------


def new_words_path(key: str, kind: str) -> str:
    """A path for one answer, which the caller writes the words into.

    The file itself is not made here. What is handed out is a name nobody else
    could have guessed, inside a folder nobody else can open, so the file that
    turns up under that name can only be the one that was asked for.
    """
    if kind not in KINDS:
        raise StateError(NOT_OURS, code=CODE_NOT_OURS)
    return os.path.join(
        words_dir(key), "%s-%s.txt" % (kind, secrets.token_hex(8))
    )


def read_words(path: str, key: str) -> Optional[str]:
    """What somebody typed, read once out of a file this code handed out.

    Nothing comes back for a path this code did not hand out, which is finding
    V6: every other path on this computer used to be readable this way. The
    file is taken away once it has been read, because a person's own words have
    no reason to stay on the disk after they are written down.
    """
    given = str(path or "")
    if not given:
        return None
    try:
        folder = os.path.realpath(words_dir(key))
    except StateError:
        return None
    if os.path.islink(given):
        return None
    real = os.path.realpath(given)
    if os.path.dirname(real) != folder:
        return None
    if not _NAME_RE.match(os.path.basename(real)):
        return None
    try:
        info = os.lstat(real)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    if info.st_uid != os.getuid() or info.st_nlink != 1:
        return None
    if info.st_size > MAX_WORDS_BYTES:
        return None
    text = read_text(real)
    remove(real)
    return None if text is None else text.strip()


def clear_words(key: str) -> None:
    """Take away every words file this run still holds, whatever came of it."""
    try:
        folder = words_dir(key)
    except StateError:
        return
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if _NAME_RE.match(name):
            remove(os.path.join(folder, name))


def named_for_a_draft(path: str, key: str) -> bool:
    """Whether one path is a file this run named for a draft, and nothing else."""
    given = str(path or "")
    if not given or os.path.islink(given):
        return False
    try:
        folder = os.path.realpath(run_dir(key))
    except StateError:
        return False
    return os.path.dirname(os.path.realpath(given)) == folder


def ensure_words_dir(key: str) -> str:
    """Make the folder for one run's words, and hand back where it is."""
    return ensure_dir(words_dir(key))
