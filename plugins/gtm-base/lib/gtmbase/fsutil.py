"""Atomic, owner-only reads and writes.

Every file this plugin owns is written to a temporary file in the same folder,
flushed to disk, and then moved into place, so an interrupted run leaves the
previous file exactly as it was. Files are readable and writable by their owner
only, and the folders that hold them are owner only as well.

A writer that knows which folder a file belongs in passes `inside`. The folder
the file would land in is then resolved all the way through any link before
anything is written, and a folder that turns out to sit outside the one named
is refused. Every writer that puts a file into a base should pass it, so a link
planted in the shared copy cannot make a write land somewhere else on this
computer. The proposal and confirmation writers pass the base root; the marker
and the account state pass the seat folder.
"""

from __future__ import annotations

import errno
import json
import os
import tempfile
from typing import Any, Optional

from .errors import PathError

FILE_MODE = 0o600
DIR_MODE = 0o700


def ensure_dir(path: str, mode: int = DIR_MODE) -> str:
    """Create a folder and every parent, owner only, and return its path."""
    if not os.path.isdir(path):
        try:
            os.makedirs(path, mode)
        except OSError as failure:
            if failure.errno != errno.EEXIST:
                raise
        else:
            try:
                os.chmod(path, mode)
            except OSError:
                pass
    return path


def _check_inside(folder: str, inside: str) -> None:
    """Refuse a write whose folder resolves outside the one it belongs in."""
    root = os.path.realpath(inside)
    real = os.path.realpath(folder)
    if real != root and not real.startswith(root.rstrip(os.sep) + os.sep):
        raise PathError(
            "this file would land outside the folder it belongs in",
            code="outside-root",
        )


# --- Who owns the temporary files in a folder ---------------------------------
#
# A writer puts its bytes in a temporary file beside the real one and then
# moves it into place. A writer that dies between the two leaves the
# temporary file behind, and something has to take it away; a writer that is
# only paused must keep it. Age cannot tell the two apart, and neither can a
# clock that is set forward or back (Astra's confirmation pass on the merged
# Units 1.7c and 1.7d, finding 2). So every writer holds a shared lock on the
# folder it writes into for the whole of its write and its move, and a sweep
# takes that lock exclusively, without waiting, only when no writer holds it.
# The operating system lets go of a writer's lock the moment it dies, so a
# sweep that gets the lock knows every temporary file in the folder belongs to
# a writer that is gone. A sweep that does not get it takes nothing.
#
# The lock files live in a folder of this person's own inside the seat folder,
# the one folder every session of this account resolves the same way whatever
# its temporary folder is, one file per folder written into, never in the
# folder itself, so nothing appears in a base. Each folder on the way that
# this code makes is checked before it is trusted: a real folder and not a
# link, owned by this account, and writable by nobody else. Anything else is
# refused, because whoever controls the lock files decides when a sweep may
# take a writer's file (Astra's second confirmation pass on the merged Units
# 1.7c and 1.7d, finding 1).

# A writer could not take its lock, so nothing was written (finding 2).
CODE_NO_LOCK = "no-writing-lock"
# The folder the locks live in is not one this account alone controls.
CODE_LOCKS_NOT_PRIVATE = "locks-not-private"


def _private_folder(path: str) -> str:
    """Make a folder owner only when it is missing, and check it either way."""
    import stat

    if not os.path.lexists(path):
        try:
            os.mkdir(path, DIR_MODE)
        except FileExistsError:
            pass
        except OSError:
            raise PathError("the locks folder could not be made", code=CODE_LOCKS_NOT_PRIVATE)
    info = os.lstat(path)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or (info.st_mode & 0o022)
    ):
        raise PathError("the locks folder is not this account's alone", code=CODE_LOCKS_NOT_PRIVATE)
    return path


def _lock_home() -> str:
    """The seat folder's own folder of locks, checked at every step it makes."""
    from . import paths

    home = paths.seat_home_path()
    parent = os.path.dirname(home)
    if parent and not os.path.isdir(parent):
        ensure_dir(parent)
    _private_folder(home)
    return _private_folder(os.path.join(home, "locks"))


def _folder_lock_path(folder: str) -> str:
    import hashlib

    key = hashlib.sha256(os.path.realpath(folder).encode("utf-8")).hexdigest()[:40]
    return os.path.join(_lock_home(), key + ".lock")


class FolderLock(object):
    """A shared hold on a folder while writing into it, or an exclusive one to sweep it.

    `exclusive=True` never waits and never refuses: `held` says whether it was
    taken, and a sweep that did not take it takes nothing. A writer that
    cannot take its hold refuses to write at all, because a write made
    without it is one a sweep could take away half done (finding 2).
    """

    def __init__(self, folder: str, exclusive: bool = False):
        self.folder = folder
        self.exclusive = exclusive
        self.handle = None
        self.held = False

    def __enter__(self):
        try:
            import fcntl
        except ImportError:
            # A computer with no such locks: nothing is ever swept there, so
            # a writer has nothing to hold off.
            self.held = not self.exclusive
            return self
        try:
            self.handle = os.open(
                _folder_lock_path(self.folder),
                os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
                FILE_MODE,
            )
        except (OSError, PathError):
            if self.exclusive:
                return self
            raise PathError("the writing lock could not be taken", code=CODE_NO_LOCK)
        if self.exclusive:
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.held = True
            except OSError:
                self.held = False
            return self
        try:
            fcntl.flock(self.handle, fcntl.LOCK_SH)
        except OSError:
            self._close()
            raise PathError("the writing lock could not be taken", code=CODE_NO_LOCK)
        self.held = True
        return self

    def _close(self):
        if self.handle is not None:
            try:
                os.close(self.handle)
            except OSError:
                pass
            self.handle = None

    def __exit__(self, *_exc):
        self._close()
        return False


def atomic_write_text(
    path: str, text: str, mode: int = FILE_MODE, inside: Optional[str] = None
) -> str:
    """Write text to path so that readers see either the old file or the new one.

    When `inside` names a folder, the folder the file would land in is resolved
    through every link first and the write is refused when it lands outside.
    """
    folder = os.path.dirname(os.path.abspath(path))
    ensure_dir(folder)
    if inside:
        _check_inside(folder, inside)
    with FolderLock(folder):
        handle, temp_path = tempfile.mkstemp(prefix=".gtmbase-", dir=folder)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp_path, mode)
            os.replace(temp_path, path)
        except BaseException:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    _sync_folder(folder)
    return path


def atomic_write_json(
    path: str, value: Any, mode: int = FILE_MODE, inside: Optional[str] = None
) -> str:
    """Write a value as formatted JSON, atomically and owner only."""
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return atomic_write_text(path, text, mode, inside=inside)


def read_text(path: str) -> Optional[str]:
    """Return the contents of a file, or None when it is not there or not a file."""
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as stream:
            return stream.read()
    except (OSError, UnicodeDecodeError):
        return None


def read_text_exactly(path: str) -> Optional[str]:
    """The contents of a file with not one character translated on the way in.

    `read_text` above reads the ordinary way, which quietly turns every line
    ending into the one this library writes. That is right for everything that
    only wants to know what a file says. It is wrong for anything that will
    write the same file back out, because the difference then lands in the
    person's own file as though somebody had meant it.
    """
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", newline="") as stream:
            return stream.read()
    except (OSError, UnicodeDecodeError):
        return None


def read_bytes(path: str) -> Optional[bytes]:
    """A file exactly as it sits on the disk, whatever it holds.

    Neither reader above can answer for a file that is not text, and finding
    L1 of the third look is about what that silence cost: the copy kept before
    a local approval went through text, so a file with an unusual byte in it
    was quietly not kept at all and a failed run lost the person's own edit.
    """
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as stream:
            return stream.read()
    except OSError:
        return None


def atomic_write_bytes(
    path: str, data: bytes, mode: int = FILE_MODE, inside: Optional[str] = None
) -> str:
    """Put bytes down whole, the same way text is put down whole."""
    folder = os.path.dirname(os.path.abspath(path))
    if inside is not None:
        _check_inside(folder, inside)
    ensure_dir(folder)
    with FolderLock(folder):
        handle, temporary = tempfile.mkstemp(dir=folder, prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, mode)
            os.replace(temporary, path)
            _sync_folder(folder)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
    return path


def read_json(path: str) -> Any:
    """Return the parsed JSON at path, or None when it is missing or malformed."""
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


# How long a writer waits for another to finish with one small file.
LOCK_WAIT_SECONDS = 10.0


class HeldLock(object):
    """One writer at a time for one small file, for as long as it is held.

    The lock is taken on a file of its own beside the file it guards, which
    is made once and never taken away, and the operating system holds it for
    exactly as long as the writer does. A writer that dies, however it dies,
    lets go of it at that moment, so there is no age to guess at and no lock
    one writer could take away from another (the reviews of Unit 1.7d, which
    found the earlier version, a file made and removed, letting two writers in
    at once). Waiting longer than the limit gives up with a refusal rather
    than writing without it, because a record two writers each read and then
    each wrote is a record one of them lost.
    """

    def __init__(self, path: str, wait_seconds: float = LOCK_WAIT_SECONDS):
        self.path = path + ".lock"
        self.wait_seconds = wait_seconds
        self.handle = None

    def __enter__(self):
        import fcntl
        import time

        ensure_dir(os.path.dirname(os.path.abspath(self.path)))
        try:
            self.handle = os.open(
                self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), FILE_MODE
            )
        except OSError:
            raise PathError("the lock could not be taken", code="locked")
        deadline = time.time() + self.wait_seconds
        while True:
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as failure:
                if failure.errno not in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                    self._close()
                    raise PathError("the lock could not be taken", code="locked")
            if time.time() >= deadline:
                self._close()
                raise PathError("another writer holds the file", code="locked")
            time.sleep(0.05)

    def _close(self):
        try:
            os.close(self.handle)
        except (OSError, TypeError):
            pass
        self.handle = None

    def __exit__(self, *_exc):
        # Closing the file lets go of the lock. The file itself stays, so no
        # writer ever removes a lock somebody else has just taken.
        self._close()
        return False


def remove(path: str) -> bool:
    """Delete a file if it is there. Return whether anything was deleted."""
    try:
        os.unlink(path)
        return True
    except OSError:
        return False


def _sync_folder(folder: str) -> None:
    """Ask the operating system to record the new directory entry."""
    try:
        handle = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)
