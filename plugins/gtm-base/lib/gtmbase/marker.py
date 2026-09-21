"""The marker that says this session already read the person's own documents.

Join reads a person's own files with the client's own tools, which means the
session holds text nobody else has vetted. From that moment until the session
ends, nothing may leave the computer. The marker is how the gate knows: it
holds the session that read, and the moment it was written.

It is deliberately small. The gate reads it, the join skill writes it and
clears it, and nothing else touches it.
"""

from __future__ import annotations

import datetime
import os
from typing import Optional

from . import constants
from .fsutil import atomic_write_json, read_json, remove
from .paths import seat_home


def marker_path() -> str:
    """The one file that records a session having read the person's files."""
    return os.path.join(seat_home(), constants.SOURCES_READ_MARKER_FILE)


def write_sources_read_marker(session_id: str) -> str:
    """Record that this session has read files nobody else has vetted."""
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("a marker needs the session it belongs to")
    payload = {
        "session_id": session_id.strip(),
        "written_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    home = seat_home()
    path = os.path.join(home, constants.SOURCES_READ_MARKER_FILE)
    atomic_write_json(path, payload, inside=home)
    return path


def read_sources_read_marker() -> Optional[dict]:
    """The marker as it stands, or None when there is none we can read."""
    path = marker_path()
    if os.path.islink(path):
        return None
    payload = read_json(path)
    if not isinstance(payload, dict):
        return None
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return None
    written_at = payload.get("written_at")
    return {
        "session_id": session_id,
        "written_at": written_at if isinstance(written_at, str) else None,
    }


def clear_sources_read_marker() -> bool:
    """Remove the marker. Returns whether there was one to remove."""
    return remove(marker_path())


def marker_matches_session(session_id: Optional[str]) -> bool:
    """Whether the marker belongs to the session asking."""
    if not session_id:
        return False
    marker = read_sources_read_marker()
    return bool(marker and marker["session_id"] == session_id)


def marker_is_recent(
    window_seconds: int = constants.SOURCES_READ_GIT_HOOK_WINDOW_SECONDS,
) -> bool:
    """Whether a marker exists and is young enough to still be about now.

    The installed safeguard runs inside git, where there is no session to
    compare against, so age is the only thing it can go by.
    """
    path = marker_path()
    marker = read_sources_read_marker()
    if marker is None:
        return False
    try:
        age = _now() - os.path.getmtime(path)
    except OSError:
        return True
    return age <= window_seconds


def marker_is_there_but_unreadable() -> bool:
    """Whether a marker is standing there that we cannot make sense of.

    A name that is not there at all is not this. A name that is there and is a
    link, or that holds anything other than the session it belongs to, is: it
    is the shape a marker takes after somebody has written over it, and the
    reviewers of the 2026-09-20 release wrote over it with an empty object to
    take away the rule that a session which read somebody's own documents may
    send nothing. So it stops a send rather than letting one through.
    """
    path = marker_path()
    if not os.path.lexists(path):
        return False
    return read_sources_read_marker() is None


def marker_blocks(
    session_id: Optional[str] = None, include_recent: bool = True
) -> bool:
    """Whether the marker stops anything leaving this computer right now.

    Three things stop it, and any one of them is enough.

    A marker standing there that cannot be read at all. That is the shape a
    marker takes after somebody has written over it, and it stops a send
    wherever the send comes from.

    A marker this very session wrote. That is the rule as it has always been,
    and it stops a send wherever the send comes from, because the text this
    session is holding could be pasted into anything.

    A marker young enough to still be about now that some other session wrote.
    This one is asked for rather than assumed, through `include_recent`, and
    the caller only asks for it where the send is one GTM Base reads at all: a
    base, or a working folder this seat made. A session identifier is one more
    thing a file somebody wrote over could hold, so age is worth having, but
    somebody who can write that file can delete it just as easily, so age buys
    little and costs a great deal: the marker lasts twelve hours and nothing
    clears it, and asking for it everywhere refused every push from every
    repository on the machine for half a day after any setup run. The
    safeguard the base itself runs has no session to compare against and only
    ever runs inside a base, so it asks for age and is right to.
    """
    if marker_is_there_but_unreadable():
        return True
    if marker_matches_session(session_id):
        return True
    return bool(include_recent) and marker_is_recent()


def _now() -> float:
    import time

    return time.time()
