"""Account state: the one file per person on this machine.

It holds two things. What this person answered when GTM Base offered to set a
base up, and the list of bases this account has joined. It is the only record
of a joined base, because before a base exists there is no base folder to keep
a record in, and because two windows can start at the same moment.

It is read as though a stranger wrote it. An entry survives a read only when
its folder is still there, still a repository, still holds the map, and still
carries the identifier the entry claims. Everything else is dropped and
reported by code, because an invented entry would otherwise be enough to make a
hook act on any folder on the machine.
"""

from __future__ import annotations

import datetime
import errno
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from . import constants, ids
from .errors import StateError
from .fsutil import atomic_write_json, ensure_dir, read_json
from .gitcmd import GitRunner
from .paths import machine_state_path, read_base_id, seat_home

SCHEMA = 1

OFFER_FIELDS = ("answer", "shown_at", "shown_session_id")
JOINED_FIELDS = ("root", "base_id", "remote")
TOP_LEVEL_FIELDS = ("schema", "offer", "joined")

# A later answer never undoes a stronger one.
ANSWER_RANK = {"unset": 0, "not-now": 1, "set-up": 2, "join": 2}

LOCK_NAME = "machine.lock"


class MachineState(object):
    """What this account answered, and which bases it joined."""

    __slots__ = ("offer", "joined", "problems")

    def __init__(self, offer=None, joined=None, problems=None):
        self.offer = offer or {"answer": "unset", "shown_at": None, "shown_session_id": None}
        self.joined = list(joined or [])
        self.problems: List[Tuple[str, int]] = list(problems or [])

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "offer": {
                "answer": self.offer.get("answer", "unset"),
                "shown_at": self.offer.get("shown_at"),
                "shown_session_id": self.offer.get("shown_session_id"),
            },
            "joined": [dict(entry) for entry in self.joined],
        }

    @property
    def answer(self) -> str:
        return self.offer.get("answer", "unset")

    def __repr__(self) -> str:
        return "MachineState(answer=%r, joined=%d)" % (self.answer, len(self.joined))


def _clean_offer(raw: Any, problems: List[Tuple[str, int]]) -> Dict[str, Any]:
    offer = {"answer": "unset", "shown_at": None, "shown_session_id": None}
    if raw is None:
        return offer
    if not isinstance(raw, dict):
        problems.append(("malformed", -1))
        return offer
    for key, value in raw.items():
        if key not in OFFER_FIELDS:
            problems.append(("unknown-key", -1))
            continue
        offer[key] = value
    if offer["answer"] not in constants.OFFER_ANSWERS:
        problems.append(("bad-value", -1))
        offer["answer"] = "unset"
    for key in ("shown_at", "shown_session_id"):
        if offer[key] is not None and not isinstance(offer[key], str):
            problems.append(("bad-value", -1))
            offer[key] = None
    return offer


def _entry_is_real(entry: Dict[str, Any], runner: Optional[GitRunner]) -> Optional[str]:
    """Return the code for why an entry is not usable, or None when it is."""
    root = entry.get("root")
    if not isinstance(root, str) or not os.path.isabs(root):
        return "bad-value"
    if not os.path.isdir(root):
        return "missing-root"
    if not os.path.exists(os.path.join(root, ".git")):
        return "missing-git"
    map_path = os.path.join(root, constants.MAP_PATH)
    if os.path.islink(map_path) or not os.path.isfile(map_path):
        return "missing-map"
    if not ids.is_base_id(entry.get("base_id")):
        return "bad-value"
    if read_base_id(root, runner=runner) != entry.get("base_id"):
        return "id-mismatch"
    return None


def _load(runner: Optional[GitRunner], check_real: bool) -> MachineState:
    """Read the file. With check_real, an entry survives only if it still holds."""
    problems: List[Tuple[str, int]] = []
    path = machine_state_path()
    if os.path.islink(path):
        return MachineState(problems=[("symlink", -1)])
    if not os.path.lexists(path):
        return MachineState()
    payload = read_json(path)
    if payload is None or not isinstance(payload, dict):
        return MachineState(problems=[("malformed", -1)])

    known: Dict[str, Any] = {}
    for key, value in payload.items():
        if key not in TOP_LEVEL_FIELDS:
            problems.append(("unknown-key", -1))
            continue
        known[key] = value

    offer = _clean_offer(known.get("offer"), problems)

    joined: List[Dict[str, Any]] = []
    raw_joined = known.get("joined")
    if raw_joined is None:
        raw_joined = []
    if not isinstance(raw_joined, list):
        problems.append(("malformed", -1))
        raw_joined = []
    for index, raw in enumerate(raw_joined):
        if not isinstance(raw, dict):
            problems.append(("bad-row", index))
            continue
        entry: Dict[str, Any] = {"root": None, "base_id": None, "remote": None}
        for key, value in raw.items():
            if key not in JOINED_FIELDS:
                problems.append(("unknown-key", index))
                continue
            entry[key] = value
        if entry["remote"] is not None and not isinstance(entry["remote"], str):
            problems.append(("bad-value", index))
            entry["remote"] = None
        if isinstance(entry["remote"], str) and "@" in entry["remote"].split("://")[-1].split("/")[0]:
            problems.append(("userinfo", index))
            entry["remote"] = None
        if not isinstance(entry["root"], str) or not os.path.isabs(entry["root"]):
            problems.append(("bad-value", index))
            continue
        if not ids.is_base_id(entry["base_id"]):
            problems.append(("bad-value", index))
            continue
        if check_real:
            code = _entry_is_real(entry, runner)
            if code is not None:
                problems.append((code, index))
                continue
        joined.append(entry)

    return MachineState(offer=offer, joined=joined, problems=problems)


def load_machine_state(runner: Optional[GitRunner] = None) -> MachineState:
    """Read account state, keeping only the joined bases that still check out."""
    return _load(runner, True)


def load_machine_state_raw() -> MachineState:
    """Read account state without checking the folders.

    Every write starts here, so a base whose folder is missing right now, an
    external drive that is not plugged in, or a folder in the middle of being
    renamed, is not quietly dropped from the file by an unrelated write.
    """
    return _load(None, False)


# --- Writing -----------------------------------------------------------------


def _lock_path() -> str:
    return os.path.join(seat_home(), LOCK_NAME)


def _acquire_lock(wait_seconds: float = constants.LOCK_WAIT_SECONDS) -> int:
    path = _lock_path()
    ensure_dir(os.path.dirname(path))
    deadline = time.time() + wait_seconds
    while True:
        try:
            return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError as failure:
            if failure.errno != errno.EEXIST:
                raise StateError("the lock could not be taken", code="write-failed")
            try:
                age = time.time() - os.path.getmtime(path)
            except OSError:
                age = 0.0
            if age > constants.LOCK_STALE_SECONDS:
                try:
                    os.unlink(path)
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                raise StateError("another writer holds the file", code="locked")
            time.sleep(0.05)


def _release_lock(handle: int) -> None:
    try:
        os.close(handle)
    except OSError:
        pass
    try:
        os.unlink(_lock_path())
    except OSError:
        pass


def _clean_remote(remote: Optional[str]) -> Optional[str]:
    """Keep a plain address and refuse one that still carries a sign-in."""
    if remote is None:
        return None
    if not isinstance(remote, str) or not remote.strip():
        return None
    stripped = ids.strip_userinfo(remote.strip())
    host_part = stripped.split("://", 1)[-1].split("/", 1)[0]
    if "@" in host_part:
        raise StateError("the address carried a sign-in", code="userinfo")
    return stripped


def save_machine_state(
    state: MachineState, wait_seconds: float = constants.LOCK_WAIT_SECONDS
) -> MachineState:
    """Write account state under a lock, in one move, owner only."""
    payload = state.as_dict()
    if payload["offer"]["answer"] not in constants.OFFER_ANSWERS:
        raise StateError("that is not an answer we record", code="bad-value")
    cleaned = []
    for entry in payload["joined"]:
        root = entry.get("root")
        if not isinstance(root, str) or not os.path.isabs(root):
            raise StateError("a joined folder needs its full path", code="bad-value")
        ids.check_base_id(entry.get("base_id"))
        cleaned.append(
            {
                "root": root,
                "base_id": entry["base_id"],
                "remote": _clean_remote(entry.get("remote")),
            }
        )
    payload["joined"] = cleaned

    handle = _acquire_lock(wait_seconds)
    try:
        atomic_write_json(machine_state_path(), payload)
    finally:
        _release_lock(handle)
    return MachineState(offer=payload["offer"], joined=payload["joined"])


# --- The offer ---------------------------------------------------------------


def record_offer_shown(
    session_id: str, now: Optional[datetime.datetime] = None, runner=None
) -> MachineState:
    """Record that the offer was shown, which holds it to once a session.

    This is a note of what happened, never an answer. Showing the offer and
    hearing nothing back leaves the answer where it was, so a later session in
    any folder offers again until the person says set up, join, or not now.
    """
    from .state import iso_utc  # imported here to keep the import order simple

    state = load_machine_state_raw()
    state.offer["shown_at"] = iso_utc(now)
    state.offer["shown_session_id"] = session_id
    return save_machine_state(state)


def record_offer_answer(answer: str, runner=None) -> MachineState:
    """Record an answer, never replacing a stronger one with a weaker one.

    Set up and join beat not now, not now beats unset, and nothing ever moves
    an answer back down. Only these three words are answers; being shown the
    offer is not one of them.
    """
    if answer not in constants.OFFER_ANSWERS:
        raise StateError("that is not an answer we record", code="bad-value")
    state = load_machine_state_raw()
    current = state.offer.get("answer", "unset")
    if ANSWER_RANK.get(answer, 0) >= ANSWER_RANK.get(current, 0):
        state.offer["answer"] = answer
    return save_machine_state(state)


def offer_was_shown_this_session(state: MachineState, session_id: str) -> bool:
    return bool(session_id) and state.offer.get("shown_session_id") == session_id


# --- The joined list ---------------------------------------------------------


def find_joined_by_root(state: MachineState, root: str) -> Optional[dict]:
    wanted = os.path.realpath(root)
    for entry in state.joined:
        if os.path.realpath(entry["root"]) == wanted:
            return entry
    return None


def find_joined_by_id(state: MachineState, base_id: str) -> Optional[dict]:
    for entry in state.joined:
        if entry["base_id"] == base_id:
            return entry
    return None


def append_joined(
    root: str, base_id: str, remote: Optional[str] = None, runner=None
) -> MachineState:
    """Add a joined base. The list only ever grows, one entry per folder."""
    ids.check_base_id(base_id)
    absolute = os.path.abspath(root)
    state = load_machine_state_raw()
    existing = find_joined_by_root(state, absolute)
    if existing is not None:
        if existing["base_id"] != base_id:
            raise StateError(
                "that folder is already joined under a different identifier",
                code="id-mismatch",
            )
        if remote and not existing.get("remote"):
            existing["remote"] = remote
            return save_machine_state(state)
        return state
    state.joined.append({"root": absolute, "base_id": base_id, "remote": remote})
    return save_machine_state(state)


def rewrite_joined_root(base_id: str, new_root: str, runner=None) -> MachineState:
    """Point a joined base at its new folder after the folder was renamed."""
    ids.check_base_id(base_id)
    absolute = os.path.abspath(new_root)
    state = load_machine_state_raw()
    entry = find_joined_by_id(state, base_id)
    if entry is None:
        raise StateError("that base is not joined", code="unknown-id")
    claimed = find_joined_by_root(state, absolute)
    if claimed is not None and claimed.get("base_id") != base_id:
        raise StateError(
            "that folder is already joined under a different identifier",
            code="id-mismatch",
        )
    entry["root"] = absolute
    return save_machine_state(state)
