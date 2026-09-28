"""One lock held by one process at a time, on any computer.

Recording a context change answers its questions one at a time under a lock,
so two windows can never both answer the same question (Astra's review of
0.3.3, finding 10). That lock used to be `fcntl`, which does not exist on
Windows, so importing the module that needed it failed there before anything
ran (Astra's confirmation of 0.3.3, defect 4). This module is the one small
interface every lock goes through, with two ways of holding one, chosen once
when it is loaded:

- `PosixLock`, where `fcntl` exists. The operating system lets go of it the
  moment its holder stops, however it stops, so a lock is never left behind.
- `FileLock` everywhere else. The lock is a file made with exclusive
  creation, holding who made it. A lock whose holder has stopped is taken
  away and taken again, and a lock whose holder is still running is never
  taken away: on a computer where that cannot be asked, a lock is only
  treated as abandoned once it is far older than anything held under it
  could ever take.

Nothing here reaches the network, and nothing read out of a lock file is ever
an instruction.
"""

from __future__ import annotations

import contextlib
import os
import socket
import time
from typing import Optional

try:  # pragma: no cover - which branch runs depends on the computer
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

# How long a wait for a lock lasts before the caller is told it is busy.
DEFAULT_WAIT_SECONDS = 5.0
# How old an empty lock file has to be before it counts as a holder that
# stopped between making it and writing its name in it, which takes no time.
EMPTY_STALE_SECONDS = 60.0
# How old a lock has to be before it counts as abandoned on a computer where
# whether its holder is still running cannot be asked. Everything held under
# one of these locks is over in seconds.
UNASKABLE_STALE_SECONDS = 600.0
POLL_SECONDS = 0.05


class Busy(Exception):
    """Somebody else held the lock for the whole of the wait."""


class PosixLock(object):
    """A lock the operating system holds, and lets go of when its holder stops."""

    name = "posix"

    def __init__(self, path: str):
        self.path = path
        self.handle: Optional[int] = None

    def try_acquire(self) -> bool:
        if self.handle is None:
            self.handle = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            fcntl.flock(self.handle, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self.handle)
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
    """A lock that is a file, for a computer without `fcntl`.

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

    def __init__(self, path: str):
        self.path = path
        self.token = ""

    def _mine(self) -> str:
        return "%d %s %s\n" % (os.getpid(), socket.gethostname() or "-", self.token)

    def try_acquire(self) -> bool:
        self.token = os.urandom(8).hex()
        try:
            handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            self._take_away_if_abandoned()
            return False
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


@contextlib.contextmanager
def held(path: str, wait_seconds: float = DEFAULT_WAIT_SECONDS, kind=None):
    """Hold the lock at `path` for the length of a `with` block, or raise Busy."""
    lock = (kind or IMPLEMENTATION)(path)
    deadline = time.monotonic() + wait_seconds
    while not lock.try_acquire():
        if time.monotonic() >= deadline:
            lock.release()
            raise Busy(path)
        time.sleep(POLL_SECONDS)
    try:
        yield lock
    finally:
        lock.release()
