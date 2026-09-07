"""What makes one folder on this computer the same folder as it was before.

A base can be told that it belongs with the folder a person keeps their
marketing material in, so that opening Claude Code in that folder brings the
base with it. The path alone is not enough evidence for that. A folder can be
renamed, in which case the path changed and the folder did not; a folder can be
deleted and another one built at the same path, in which case the path is the
same and the folder is not. So the record of that association keeps a small
piece of evidence about the folder itself beside the path, and this module is
the one place that evidence is taken and compared.

What is kept, and why each piece is there.

`dev` and `ino` are the two numbers the operating system uses to tell one
directory from another on one disk. They are the cheapest evidence there is,
two calls, which matters because this comparison runs inside a hook with
fifteen seconds for everything it does.

`birth` is the second the folder came into being, which macOS records and Linux
does not. It is what stops a folder that happens to be given a recycled
number from passing as the folder that used to hold that number. Where it is
not recorded it is null on both sides and the comparison simply does not use
it.

`mount` and `volume` say which disk the folder is on. An external disk can come
back with a different device number after it is plugged in again, and without
the volume's own identifier the folder would look like a different folder every
time. With it, the case is recognised for what it is and reported as such
rather than guessed at.

`remote` is the address of the shared copy when the folder is itself looked
after by another tool. It is never used to find a folder. It is only ever a
reason to stop: a folder whose address changed was pointed at different work,
whatever its numbers say.

Nothing here reads a single one of the person's documents. It asks the
operating system about the folder itself and, on a Mac, asks the disk tool for
the volume's identifier, and that is all.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, Optional

from .errors import StateError

# How long the disk tool may take before we carry on without a volume id.
VOLUME_TIMEOUT_SECONDS = 2

# What `matches` can say about two records of one folder.
SAME = "same"
MOVED = "moved"
REMOUNTED = "remounted"
DIFFERENT = "different"

# The fields the record carries, in the order they are written.
IDENTITY_FIELDS = ("dev", "ino", "birth", "mount", "volume", "remote")

CODE_UNSTABLE = "identity-unstable"
CODE_NOT_A_FOLDER = "not-a-folder"


class Identity(object):
    """One folder, as this computer knows it at one moment."""

    __slots__ = ("path",) + IDENTITY_FIELDS

    def __init__(self, path, dev, ino, birth=None, mount=None, volume=None, remote=None):
        self.path = path
        self.dev = dev
        self.ino = ino
        self.birth = birth
        self.mount = mount
        self.volume = volume
        self.remote = remote

    def as_dict(self) -> Dict[str, Any]:
        """The record as it is written down, without the path.

        The path is written beside the record rather than inside it, because
        the path is the thing that changes when a folder is renamed and the
        record is the thing that does not.
        """
        return {name: getattr(self, name) for name in IDENTITY_FIELDS}

    def __repr__(self) -> str:
        return "Identity(path=%r, dev=%r, ino=%r)" % (self.path, self.dev, self.ino)


def _is_darwin() -> bool:
    return sys.platform == "darwin"


def mount_point(path: str) -> Optional[str]:
    """The top of the disk this folder sits on, or nothing when we cannot tell."""
    try:
        here = os.path.realpath(path)
    except OSError:
        return None
    while True:
        try:
            if os.path.ismount(here):
                return here
        except OSError:
            return None
        parent = os.path.dirname(here)
        if parent == here:
            return here
        here = parent


def volume_id(mount: Optional[str], timeout: float = VOLUME_TIMEOUT_SECONDS) -> Optional[str]:
    """The disk's own identifier, which survives being unplugged and plugged in.

    Only macOS records one this module can read, and even there the disk tool
    can be slow or absent, so a failure of any kind comes back as nothing
    rather than as an error. Nothing depends on having it; having it turns one
    case that would otherwise look like a different folder into a case that is
    reported honestly.
    """
    if not mount or not _is_darwin():
        return None
    try:
        finished = subprocess.run(
            ["/usr/sbin/diskutil", "info", "-plist", mount],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if finished.returncode != 0 or not finished.stdout:
        return None
    try:
        import plistlib

        payload = plistlib.loads(finished.stdout)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("VolumeUUID")
    return value if isinstance(value, str) and value.strip() else None


def folder_remote(path: str, runner=None) -> Optional[str]:
    """The address of the shared copy, but only when this folder is its top.

    A folder inside somebody else's repository would otherwise inherit that
    repository's address, and two different folders in one repository would
    then look alike. So the address is read only when this folder is itself the
    top of the repository.
    """
    from . import paths

    try:
        top = paths.git_root(path, runner=runner)
    except Exception:
        return None
    if not top:
        return None
    try:
        if os.path.realpath(top) != os.path.realpath(path):
            return None
    except OSError:
        return None
    try:
        return paths.canonical_remote(path, runner=runner)
    except Exception:
        return None


def _stat_of(path: str):
    try:
        return os.stat(path)
    except OSError:
        raise StateError("that folder is not there", code=CODE_NOT_A_FOLDER)


def resolve(path: str) -> str:
    """Where this path really leads, right now.

    It is one named function rather than a line inside `capture` so that a test
    can make the answer change between the two passes below and prove that the
    refusal happens. Nothing else about it is special.
    """
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def capture(path: str, runner=None, with_volume: bool = True) -> Identity:
    """Take the record of one folder, with the path and the numbers agreeing.

    The path is resolved and the folder is asked about, and then both are done
    again and compared. A folder can be renamed in between those two calls, and
    a record whose path came from before the rename and whose numbers came from
    after it would be a record of a folder that never existed. When the two
    passes disagree the answer is a refusal rather than a guess.
    """
    first_real = resolve(path)
    first = _stat_of(first_real)
    second_real = resolve(path)
    second = _stat_of(second_real)
    if first_real != second_real or (first.st_dev, first.st_ino) != (
        second.st_dev,
        second.st_ino,
    ):
        raise StateError(
            "that folder changed while it was being looked at", code=CODE_UNSTABLE
        )
    if not os.path.isdir(second_real):
        raise StateError("that is not a folder", code=CODE_NOT_A_FOLDER)

    birth = None
    if _is_darwin():
        raw = getattr(second, "st_birthtime", None)
        if raw is not None:
            birth = int(raw)
    mount = mount_point(second_real)
    volume = volume_id(mount) if with_volume else None
    return Identity(
        second_real,
        int(second.st_dev),
        int(second.st_ino),
        birth,
        mount,
        volume,
        folder_remote(second_real, runner=runner),
    )


def clean(raw: Any) -> Optional[Dict[str, Any]]:
    """Read a record back as though a stranger wrote it, or refuse the whole of it.

    The fields are checked together rather than one at a time. Half a record is
    not a weaker record, it is a record that says nothing, and a record that
    says nothing must never be able to wake a base up.
    """
    if not isinstance(raw, dict):
        return None
    for key in raw:
        if key not in IDENTITY_FIELDS:
            return None
    for name in ("dev", "ino"):
        value = raw.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
    birth = raw.get("birth")
    if birth is not None and (not isinstance(birth, int) or isinstance(birth, bool)):
        return None
    for name in ("mount", "volume", "remote"):
        value = raw.get(name)
        if value is not None and not isinstance(value, str):
            return None
    remote = raw.get("remote")
    if isinstance(remote, str):
        host = remote.split("://", 1)[-1].split("/", 1)[0]
        if "@" in host:
            return None
    return {name: raw.get(name) for name in IDENTITY_FIELDS}


def _as_dict(value) -> Optional[Dict[str, Any]]:
    if isinstance(value, Identity):
        return value.as_dict()
    return clean(value)


def matches(recorded, current, recorded_path: Optional[str] = None) -> str:
    """What the two records say about each other, in one word.

    `same` means this is the folder that was recorded, where it was recorded.
    `moved` means it is the same folder under a different name. `remounted`
    means the folder is recognisable but the disk it sits on is not the disk it
    was on, which is a case for asking rather than for assuming. `different`
    means there is not enough agreement to call it the same folder at all, and
    is what an absent or unreadable record always comes back as.
    """
    left = _as_dict(recorded)
    right = _as_dict(current)
    if left is None or right is None:
        return DIFFERENT

    if left.get("ino") != right.get("ino"):
        return DIFFERENT
    if left.get("birth") != right.get("birth"):
        return DIFFERENT
    # A folder whose shared copy now points somewhere else was pointed at
    # different work, whatever its numbers say. This is a reason to stop and
    # ask, never a way of finding a folder.
    if left.get("remote") != right.get("remote"):
        return DIFFERENT

    # The volume identifier is only ever evidence when both records have one.
    # A disk tool that was slow on one of the two days is not a remount, and
    # treating it as one would ask a person to reconnect a folder that never
    # went anywhere.
    both_have_volume = left.get("volume") is not None and right.get("volume") is not None
    volumes_differ = both_have_volume and left.get("volume") != right.get("volume")
    if left.get("dev") != right.get("dev") or volumes_differ:
        return REMOUNTED

    if recorded_path is None:
        return SAME
    return SAME if points_at(recorded_path, right) else MOVED


def points_at(path: str, record) -> bool:
    """Whether the folder at this path is the folder the record describes.

    The two paths are never compared as text. On a disk that treats two
    spellings of one name as one folder, the text differs and the folder does
    not, so what is compared is the pair of numbers the operating system gives
    for whatever that path leads to.
    """
    wanted = _as_dict(record)
    if wanted is None or not path:
        return False
    try:
        found = os.stat(path)
    except OSError:
        return False
    return int(found.st_dev) == wanted.get("dev") and int(found.st_ino) == wanted.get(
        "ino"
    )
