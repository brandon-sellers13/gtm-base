"""Every lock GTM Base takes, in one place, held one way.

Release B and 0.3.3 each built a lock of their own. Unit 1.7d's writing locks
(`fsutil.FolderLock` and `fsutil.HeldLock`, and the per-base writing lock on
top of them) are held by the operating system on a file that is never taken
away, in a folder of this person's own inside the seat folder that is checked
before it is trusted, and a writer that cannot take its lock writes nothing.
0.3.3's lock (`locks.held`, for answering the questions about a context change
one at a time) worked on any computer, including one without `fcntl`, but put
its lock file wherever the caller named and checked nothing about the folder.
Two systems guarding the same base is how one path ends up holding one lock
while another path guards the same thing with a different one, so there is
now one, and it is Unit 1.7d's design with 0.3.3's reach:

- Every lock file lives in the seat folder's own `locks` folder, owner only,
  one file per thing guarded, named by a hash of what it guards, so nothing
  appears in a base or beside a record. Each folder on the way that this code
  makes is checked before it is trusted: a real folder and not a link, owned
  by this account, and writable by nobody else (Astra's second confirmation
  pass on the merged Units 1.7c and 1.7d, finding 1).
- `PosixLock`, where `fcntl` exists. The operating system holds it and lets
  go of it the moment its holder stops, however it stops, and the file is
  never removed, so no holder can ever take a lock away from another (the
  reviews of Unit 1.7d). It can be held shared, by every writer into one
  folder, or exclusive.
- `FileLock` everywhere else, 0.3.3's lock file made with exclusive creation
  and holding who made it. A lock whose holder has stopped is taken away and
  taken again, and a lock whose holder is still running is never taken away
  (Astra's confirmation of 0.3.3, defect 4). It is only ever held exclusive:
  on such a computer a writer's shared hold on a folder is granted without a
  file, and a sweep never takes a folder, so nothing a live writer made is
  ever swept.
- A hold can be reentrant for one thread, so a call that already holds a lock,
  such as a resume finishing one of its pages, never waits on itself, while
  another thread still waits like any other window.

Nothing here reaches the network, and nothing read out of a lock file is ever
an instruction.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import os
import socket
import stat
import threading
import time
from typing import Optional

from .errors import PathError

try:  # pragma: no cover - which branch runs depends on the computer
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

# How long a wait for a lock lasts before the caller is told it is busy.
DEFAULT_WAIT_SECONDS = 5.0
# How long a writer waits for its shared hold on a folder. Only a sweep holds
# a folder exclusively, and only for as long as a look at the folder takes.
FOLDER_WAIT_SECONDS = 30.0
# How old an empty lock file has to be before it counts as a holder that
# stopped between making it and writing its name in it, which takes no time.
EMPTY_STALE_SECONDS = 60.0
# How old a lock has to be before it counts as abandoned on a computer where
# whether its holder is still running cannot be asked. Everything held under
# one of these locks is over in seconds.
UNASKABLE_STALE_SECONDS = 600.0
POLL_SECONDS = 0.05

# The seat folder's own folder of lock files.
LOCKS_FOLDER = "locks"
FILE_MODE = 0o600
DIR_MODE = 0o700
_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)

# A writer could not take its lock, so nothing was written (Astra's
# confirmation pass on the merged Units 1.7c and 1.7d, finding 2).
CODE_NO_LOCK = "no-writing-lock"
# The folder the locks live in is not one this account alone controls.
CODE_LOCKS_NOT_PRIVATE = "locks-not-private"
# Another writer held one small file for longer than the wait.
CODE_LOCKED = "locked"


class Busy(Exception):
    """Somebody else held the lock for the whole of the wait."""


# --- Where every lock file lives ---------------------------------------------


def _private_folder(path: str) -> str:
    """Make a folder owner only when it is missing, and check it either way."""
    if not os.path.lexists(path):
        try:
            os.mkdir(path, DIR_MODE)
        except FileExistsError:
            pass
        except OSError:
            raise PathError("the locks folder could not be made", code=CODE_LOCKS_NOT_PRIVATE)
    info = os.lstat(path)
    owner = getattr(os, "getuid", None)
    if (
        not stat.S_ISDIR(info.st_mode)
        or (owner is not None and info.st_uid != owner())
        or (os.name == "posix" and info.st_mode & 0o022)
    ):
        raise PathError("the locks folder is not this account's alone", code=CODE_LOCKS_NOT_PRIVATE)
    return path


def lock_home() -> str:
    """The seat folder's own folder of locks, checked at every step it makes."""
    from . import paths

    home = paths.seat_home_path()
    parent = os.path.dirname(home)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, DIR_MODE, exist_ok=True)
    _private_folder(home)
    return _private_folder(os.path.join(home, LOCKS_FOLDER))


def _named(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:40]
    return os.path.join(lock_home(), digest + ".lock")


def folder_lock_path(folder: str) -> str:
    """The lock file for every writer into one folder, and for its sweep."""
    return _named(os.path.realpath(folder))


def file_lock_path(path: str) -> str:
    """The lock file for one small file, or one named thing, held one at a time."""
    return _named("file:" + os.path.abspath(path))


# --- The two ways of holding one ---------------------------------------------


class PosixLock(object):
    """A lock the operating system holds, and lets go of when its holder stops.

    The file is opened without following a link and is never removed, so no
    holder can take away a lock somebody else has just taken.
    """

    name = "posix"

    def __init__(self, path: str, shared: bool = False):
        self.path = path
        self.shared = shared
        self.handle: Optional[int] = None

    def try_acquire(self) -> bool:
        if self.handle is None:
            try:
                self.handle = os.open(
                    self.path, os.O_CREAT | os.O_RDWR | _NO_FOLLOW, FILE_MODE
                )
            except OSError:
                raise PathError("the lock could not be taken", code=CODE_NO_LOCK)
        how = fcntl.LOCK_SH if self.shared else fcntl.LOCK_EX
        try:
            fcntl.flock(self.handle, how | fcntl.LOCK_NB)
            return True
        except OSError as failure:
            if failure.errno in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                return False
            self.release()
            raise PathError("the lock could not be taken", code=CODE_NO_LOCK)

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(self.handle)
        except OSError:
            pass
        self.handle = None


def _holder_of(text: str):
    """The process and computer a lock file names, or nothing."""
    parts = (text or "").split()
    if len(parts) < 2 or not parts[0].isdigit():
        return None
    return int(parts[0]), parts[1]


def _still_running(pid: int) -> Optional[bool]:
    """Whether a process on this computer is still running, or None if unaskable.

    Only asked where signal 0 means "just ask". On Windows the same call would
    stop the process, so it is never made there.
    """
    if os.name != "posix":
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


class FileLock(object):
    """A lock that is a file, for a computer without `fcntl`. Exclusive only.

    The file is made with exclusive creation and holds its maker's process
    number and computer name, so a second window finds it taken. A lock is
    only ever taken away when its holder has certainly stopped: the process
    it names is gone from this computer, or the file was left empty far
    longer than writing a name takes, or, where neither can be asked, the lock
    is far older than anything held under it could take. A lock is only taken
    away while it still holds exactly what was read, so two windows cannot
    both take away one lock and both think they hold it.
    """

    name = "file"

    def __init__(self, path: str, shared: bool = False):
        if shared:
            raise ValueError("a lock file is only ever held by one holder")
        self.path = path
        self.token = ""

    def _mine(self) -> str:
        return "%d %s %s\n" % (os.getpid(), socket.gethostname() or "-", self.token)

    def try_acquire(self) -> bool:
        self.token = os.urandom(8).hex()
        try:
            handle = os.open(
                self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | _NO_FOLLOW, FILE_MODE
            )
        except FileExistsError:
            self._take_away_if_abandoned()
            return False
        except OSError:
            raise PathError("the lock could not be taken", code=CODE_NO_LOCK)
        try:
            os.write(handle, self._mine().encode("utf-8"))
        finally:
            os.close(handle)
        return True

    def _read(self):
        try:
            with open(self.path, encoding="utf-8", errors="replace") as handle:
                text = handle.read(512)
            age = time.time() - os.path.getmtime(self.path)
        except OSError:
            return None, 0.0
        return text, age

    def _abandoned(self, text: str, age: float) -> bool:
        holder = _holder_of(text)
        if holder is None:
            return age > EMPTY_STALE_SECONDS
        pid, host = holder
        if host == (socket.gethostname() or "-"):
            running = _still_running(pid)
            if running is not None:
                return not running
        return age > UNASKABLE_STALE_SECONDS

    def _take_away_if_abandoned(self) -> None:
        """Take an abandoned lock away without ever taking away a live one.

        The lock is moved aside in one step first, and only what was moved is
        looked at. If it is still exactly the abandoned lock, it goes. If
        another window had already replaced it with a live lock of its own,
        that lock is put back, and when it cannot be put back because a third
        lock is already there, it is left where it was moved rather than
        taken away.
        """
        text, age = self._read()
        if text is None or not self._abandoned(text, age):
            return
        aside = "%s.abandoned-%s" % (self.path, os.urandom(6).hex())
        try:
            os.rename(self.path, aside)
        except OSError:
            return
        try:
            with open(aside, encoding="utf-8", errors="replace") as handle:
                moved = handle.read(512)
        except OSError:
            return
        if moved == text:
            try:
                os.unlink(aside)
            except OSError:
                pass
            return
        try:
            os.link(aside, self.path)
        except OSError:
            return
        try:
            os.unlink(aside)
        except OSError:
            pass

    def release(self) -> None:
        text, _age = self._read()
        if text == self._mine():
            try:
                os.unlink(self.path)
            except OSError:
                pass


# Chosen once, when this module is loaded.
IMPLEMENTATION = PosixLock if fcntl is not None else FileLock


def shared_holds_are_real(kind=None) -> bool:
    """Whether a shared hold on this computer is a lock anybody can see."""
    return (kind or IMPLEMENTATION) is PosixLock


# --- Holding one ---------------------------------------------------------------

# How many times this thread holds each reentrant lock.
_REENTRANT = threading.local()


def _counts() -> dict:
    counts = getattr(_REENTRANT, "counts", None)
    if counts is None:
        counts = _REENTRANT.counts = {}
    return counts


@contextlib.contextmanager
def held(
    path: str,
    wait_seconds: float = DEFAULT_WAIT_SECONDS,
    kind=None,
    shared: bool = False,
    reentrant: bool = False,
):
    """Hold the lock at `path` for the length of a `with` block, or raise Busy.

    `path` is a lock file, which every caller in the library gets from
    `folder_lock_path` or `file_lock_path`. A lock file that cannot be opened
    raises the refusal that says so, and nothing is done without the lock.
    `shared` is the writers' hold on a folder; where shared holds are not real
    it is granted without a file. `reentrant` lets a thread that already holds
    this lock through without waiting on itself.
    """
    counts = _counts()
    if reentrant and counts.get(path, 0) > 0:
        counts[path] += 1
        try:
            yield None
        finally:
            counts[path] -= 1
        return
    chosen = kind or IMPLEMENTATION
    if shared and chosen is not PosixLock:
        yield None
        return
    lock = chosen(path, shared=shared) if shared else chosen(path)
    deadline = time.monotonic() + wait_seconds
    try:
        while not lock.try_acquire():
            if time.monotonic() >= deadline:
                raise Busy(path)
            time.sleep(POLL_SECONDS)
    except BaseException:
        lock.release()
        raise
    if reentrant:
        counts[path] = 1
    try:
        yield lock
    finally:
        if reentrant:
            counts.pop(path, None)
        lock.release()


def try_exclusive(path: str, kind=None):
    """Take a lock exclusively without waiting, or come back with nothing.

    For a sweep, which takes nothing unless it holds the lock. Where shared
    holds are not real, a sweep never holds one, because a live writer there
    would not be seen.
    """
    chosen = kind or IMPLEMENTATION
    if chosen is not PosixLock:
        return None
    lock = chosen(path)
    try:
        if lock.try_acquire():
            return lock
    except PathError:
        pass
    lock.release()
    return None


# --- The two holds the library's writers use ---------------------------------


class FolderLock(object):
    """A shared hold on a folder while writing into it, or an exclusive one to sweep it.

    Every writer holds its folder shared for the whole of its write and its
    move, and a sweep takes it exclusively, without waiting, only when no
    writer holds it. The operating system lets go of a writer's hold the
    moment it dies, so a sweep that gets the lock knows every temporary file
    in the folder belongs to a writer that is gone. `exclusive=True` never
    waits and never refuses: `held` says whether it was taken, and a sweep
    that did not take it takes nothing. A writer that cannot take its hold
    refuses to write at all, because a write made without it is one a sweep
    could take away half done.
    """

    def __init__(self, folder: str, exclusive: bool = False):
        self.folder = folder
        self.exclusive = exclusive
        self.held = False
        self._lock = None
        self._context = None

    def __enter__(self):
        if self.exclusive:
            try:
                self._lock = try_exclusive(folder_lock_path(self.folder))
            except PathError:
                self._lock = None
            self.held = self._lock is not None
            return self
        try:
            self._context = held(
                folder_lock_path(self.folder),
                wait_seconds=FOLDER_WAIT_SECONDS,
                shared=True,
            )
            self._context.__enter__()
        except (PathError, Busy):
            self._context = None
            raise PathError("the writing lock could not be taken", code=CODE_NO_LOCK)
        self.held = True
        return self

    def __exit__(self, *exc):
        if self._lock is not None:
            self._lock.release()
            self._lock = None
        if self._context is not None:
            context, self._context = self._context, None
            context.__exit__(None, None, None)
        return False


# How long a writer waits for another to finish with one small file.
LOCK_WAIT_SECONDS = 10.0


class HeldLock(object):
    """One writer at a time for one small file, or one named thing, while held.

    The operating system holds it for exactly as long as the writer does, so
    a writer that dies, however it dies, lets go of it at that moment, and no
    writer can take it away from another (the reviews of Unit 1.7d, which
    found an earlier version, a file made and removed, letting two writers in
    at once). Waiting longer than the limit gives up with a refusal rather
    than writing without it, because a record two writers each read and then
    each wrote is a record one of them lost. `reentrant` lets a thread that
    already holds it through, which the per-base writing lock needs.
    """

    def __init__(
        self,
        path: str,
        wait_seconds: float = LOCK_WAIT_SECONDS,
        reentrant: bool = False,
        kind=None,
    ):
        self.guarded = path
        self.wait_seconds = wait_seconds
        self.reentrant = reentrant
        self.kind = kind
        self._context = None

    def __enter__(self):
        try:
            context = held(
                file_lock_path(self.guarded),
                wait_seconds=self.wait_seconds,
                kind=self.kind,
                reentrant=self.reentrant,
            )
            context.__enter__()
        except Busy:
            raise PathError("another writer holds the file", code=CODE_LOCKED)
        except PathError as failure:
            if failure.code == CODE_LOCKS_NOT_PRIVATE:
                raise
            raise PathError("the lock could not be taken", code=CODE_LOCKED)
        self._context = context
        return self

    def __exit__(self, *exc):
        if self._context is not None:
            context, self._context = self._context, None
            context.__exit__(None, None, None)
        return False
