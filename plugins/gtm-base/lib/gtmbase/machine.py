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

from . import constants, folder_identity, ids
from .errors import StateError
from .fsutil import atomic_write_json, ensure_dir, read_json
from .gitcmd import GitRunner
from .paths import machine_state_path, read_base_id, seat_home, seat_home_path

SCHEMA = 1

OFFER_FIELDS = ("answer", "shown_at", "shown_session_id")
JOINED_FIELDS = ("root", "base_id", "remote", "content_root", "content_identity")
TOP_LEVEL_FIELDS = ("schema", "offer", "joined")

# The two fields that say which folder a base belongs with. They are read,
# written, and thrown away together, because one of them on its own is not a
# weaker association, it is no association at all.
LINK_FIELDS = ("content_root", "content_identity")

# Why a folder could not be recorded as the one a base belongs with.
CODE_CONTENT_TAKEN = "content-taken"
CODE_CONTENT_INSIDE_BASE = "content-inside-base"
CODE_CONTENT_MISSING = "content-missing"
CODE_STALE_LINK = "stale-link"

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


def _clean_link(entry: Dict[str, Any], index: int, problems: List[Tuple[str, int]]) -> None:
    """Read the folder a base belongs with, or drop that association whole.

    The two fields are checked together. A record with a folder and no evidence
    about it, or with evidence that is not the shape we write, is turned off and
    reported, and the base itself carries on being a joined base. A bad
    association must never cost somebody their base, and it must never be
    enough on its own to wake one.
    """
    root = entry.get("content_root")
    identity = entry.get("content_identity")
    if root is None and identity is None:
        return
    cleaned = folder_identity.clean(identity)
    if not isinstance(root, str) or not os.path.isabs(root) or cleaned is None:
        problems.append(("bad-link", index))
        entry["content_root"] = None
        entry["content_identity"] = None
        return
    entry["content_root"] = root
    entry["content_identity"] = cleaned


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
        entry: Dict[str, Any] = {name: None for name in JOINED_FIELDS}
        for key, value in raw.items():
            if key not in JOINED_FIELDS:
                problems.append(("unknown-key", index))
                continue
            entry[key] = value
        _clean_link(entry, index, problems)
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


def _checked_payload(state: MachineState) -> Dict[str, Any]:
    """The state as it will be written, refused rather than fixed when wrong."""
    payload = state.as_dict()
    if payload["offer"]["answer"] not in constants.OFFER_ANSWERS:
        raise StateError("that is not an answer we record", code="bad-value")
    cleaned = []
    for entry in payload["joined"]:
        root = entry.get("root")
        if not isinstance(root, str) or not os.path.isabs(root):
            raise StateError("a joined folder needs its full path", code="bad-value")
        ids.check_base_id(entry.get("base_id"))
        content_root = entry.get("content_root")
        identity = folder_identity.clean(entry.get("content_identity"))
        if content_root is not None and (
            not isinstance(content_root, str)
            or not os.path.isabs(content_root)
            or identity is None
        ):
            raise StateError(
                "a folder a base belongs with needs its full path and its evidence",
                code="bad-value",
            )
        if content_root is None:
            identity = None
        cleaned.append(
            {
                "root": root,
                "base_id": entry["base_id"],
                "remote": _clean_remote(entry.get("remote")),
                "content_root": content_root,
                "content_identity": identity,
            }
        )
    payload["joined"] = cleaned
    return payload


def _write_payload(payload: Dict[str, Any]) -> MachineState:
    """Put the file in place. The caller already holds the lock."""
    atomic_write_json(machine_state_path(), payload)
    return MachineState(offer=payload["offer"], joined=payload["joined"])


def save_machine_state(
    state: MachineState, wait_seconds: float = constants.LOCK_WAIT_SECONDS
) -> MachineState:
    """Write account state under a lock, in one move, owner only."""
    payload = _checked_payload(state)
    handle = _acquire_lock(wait_seconds)
    try:
        return _write_payload(payload)
    finally:
        _release_lock(handle)


def _locked_change(change, wait_seconds: float = constants.LOCK_WAIT_SECONDS) -> MachineState:
    """Read, decide, and write with the lock held for the whole of it.

    Every decision about which base a folder belongs with is made against the
    file as it stands and written before anything else may read it. Taking the
    lock only around the write would let two windows both find a folder free and
    both claim it, and the second write would quietly replace the first.
    """
    handle = _acquire_lock(wait_seconds)
    try:
        state = _load(None, False)
        change(state)
        return _write_payload(_checked_payload(state))
    finally:
        _release_lock(handle)


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
    root: str,
    base_id: str,
    remote: Optional[str] = None,
    runner=None,
    content_root: Optional[str] = None,
) -> Tuple[MachineState, List[str]]:
    """Add a joined base, with the folder it belongs with, in one move.

    The base and the folder it belongs with are written together, under one
    lock, because a base that is joined and then separately connected has a
    moment in between where a window that closed leaves the connection missing
    and nothing saying so.

    The base is never lost to a refusal about the folder. When the folder cannot
    be taken, the base is still joined and the code saying so comes back, so the
    caller can tell the person that one step is left rather than that setting up
    failed.
    """
    ids.check_base_id(base_id)
    absolute = os.path.abspath(root)
    identity = None
    if content_root:
        # Taken before the lock, because it asks the operating system and the
        # disk tool, and nothing else may be waiting while it does.
        identity = folder_identity.capture(content_root, runner=runner)
    codes: List[str] = []

    def change(state):
        del codes[:]
        existing = find_joined_by_root(state, absolute)
        entry = existing
        if existing is not None:
            if existing["base_id"] != base_id:
                raise StateError(
                    "that folder is already joined under a different identifier",
                    code="id-mismatch",
                )
            if remote and not existing.get("remote"):
                existing["remote"] = remote
        else:
            entry = {name: None for name in JOINED_FIELDS}
            entry["root"] = absolute
            entry["base_id"] = base_id
            entry["remote"] = remote
            state.joined.append(entry)
        if identity is None:
            return
        try:
            _refuse_inside_a_base(state, base_id, identity.path)
            _refuse_taken(state, base_id, identity, identity.path)
        except StateError as refusal:
            codes.append(refusal.code)
            return
        entry["content_root"] = identity.path
        entry["content_identity"] = identity.as_dict()

    return _locked_change(change), list(codes)


def check_content_free(
    content_root: str, base_id: Optional[str] = None, runner=None
) -> None:
    """Ask whether a folder could be taken, before anything at all is built.

    The same refusals run again when it is actually written down. This is the
    early one, so that somebody who names a folder another base already has is
    told at the moment they name it rather than after a base has been built for
    them. There is no base yet when this runs during setup, which is why the
    base to leave out of the comparison can be left unsaid.
    """
    identity = folder_identity.capture(content_root, runner=runner)
    state = load_machine_state_raw()
    _refuse_inside_a_base(state, base_id, identity.path)
    _refuse_taken(state, base_id, identity, identity.path)


def rewrite_joined_root(base_id: str, new_root: str, runner=None) -> MachineState:
    """Point a joined base at its new folder after the folder was renamed."""
    ids.check_base_id(base_id)
    absolute = os.path.abspath(new_root)

    def change(state):
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

    return _locked_change(change)


# --- The folder a base belongs with ------------------------------------------


def _inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def _refuse_inside_a_base(state: MachineState, base_id: str, folder: str) -> None:
    """Refuse a folder that is a base, sits inside one, or is our own records.

    A base's own insides must never be the doorway to a different base, because
    opening one company's context folder would then bring another company's base
    into the session. The folder GTM Base keeps for itself is refused for the
    same reason, and because nothing in it belongs to a company at all.
    """
    if _inside(folder, os.path.realpath(seat_home_path())) or _inside(
        folder, os.path.abspath(seat_home_path())
    ):
        raise StateError(
            "that folder is inside the folder GTM Base keeps for itself",
            code=CODE_CONTENT_INSIDE_BASE,
        )
    for entry in state.joined:
        root = entry.get("root")
        if not isinstance(root, str):
            continue
        real_root = os.path.realpath(root) if os.path.exists(root) else os.path.abspath(root)
        if _inside(folder, real_root):
            raise StateError(
                "that folder is a base or sits inside one", code=CODE_CONTENT_INSIDE_BASE
            )
        # A base sitting directly inside the folder always wins over any
        # association, so an association with a different base could never fire
        # from here and is refused rather than written down and never used.
        if entry.get("base_id") != base_id and os.path.dirname(real_root) == folder:
            if os.path.basename(real_root).casefold() == constants.BASE_FOLDER_NAME:
                raise StateError(
                    "another base already sits directly inside that folder",
                    code=CODE_CONTENT_INSIDE_BASE,
                )


def _refuse_taken(state: MachineState, base_id: str, identity, folder: str) -> None:
    """Refuse a folder another base already belongs with. One folder, one base."""
    for entry in state.joined:
        if entry.get("base_id") == base_id:
            continue
        recorded_root = entry.get("content_root")
        recorded = folder_identity.clean(entry.get("content_identity"))
        if recorded_root is None or recorded is None:
            continue
        taken = False
        if os.path.exists(recorded_root) and os.path.realpath(recorded_root) == folder:
            taken = True
        elif folder_identity.matches(recorded, identity, recorded_root) in (
            folder_identity.SAME,
            folder_identity.MOVED,
        ):
            taken = True
        if taken:
            failure = StateError(
                "that folder already belongs with another base",
                code=CODE_CONTENT_TAKEN,
            )
            failure.other_root = entry.get("root")
            raise failure


def link_content(base_id: str, content_root: str, runner=None) -> MachineState:
    """Record the folder a base belongs with, once the folder checks out.

    Reading the list, checking the folder against it, and writing the answer all
    happen with the lock held, so two windows cannot both find the folder free.
    """
    ids.check_base_id(base_id)
    identity = folder_identity.capture(content_root, runner=runner)
    folder = identity.path

    def change(state):
        entry = find_joined_by_id(state, base_id)
        if entry is None:
            raise StateError("that base is not joined", code="unknown-id")
        _refuse_inside_a_base(state, base_id, folder)
        _refuse_taken(state, base_id, identity, folder)
        entry["content_root"] = folder
        entry["content_identity"] = identity.as_dict()

    return _locked_change(change)


def unlink_content(base_id: str) -> MachineState:
    """Forget the folder a base belongs with. The base itself is untouched."""
    ids.check_base_id(base_id)

    def change(state):
        entry = find_joined_by_id(state, base_id)
        if entry is None:
            raise StateError("that base is not joined", code="unknown-id")
        entry["content_root"] = None
        entry["content_identity"] = None

    return _locked_change(change)


def relink_content(base_id: str, content_root: str, runner=None) -> MachineState:
    """Point a base at a different folder: forget the old one, take the new one."""
    unlink_content(base_id)
    return link_content(base_id, content_root, runner=runner)


def rewrite_content_root(
    base_id: str, new_root: str, expected_root: str, identity=None
) -> MachineState:
    """Follow a folder that was renamed, but only if nobody moved it first.

    The new path is written only when the path still recorded is the one this
    run read. Another window may have unlinked the base or pointed it somewhere
    else in the meantime, and a rename worked out from what was true a moment
    ago must never undo a choice somebody has since made.
    """
    ids.check_base_id(base_id)
    absolute = os.path.realpath(os.path.abspath(new_root))

    def change(state):
        entry = find_joined_by_id(state, base_id)
        if entry is None:
            raise StateError("that base is not joined", code="unknown-id")
        if entry.get("content_root") != expected_root:
            raise StateError(
                "that base belongs with a different folder now", code=CODE_STALE_LINK
            )
        _refuse_inside_a_base(state, base_id, absolute)
        entry["content_root"] = absolute
        if identity is not None:
            cleaned = folder_identity.clean(
                identity.as_dict() if hasattr(identity, "as_dict") else identity
            )
            if cleaned is not None:
                entry["content_identity"] = cleaned

    return _locked_change(change)


def find_joined_by_content(state: MachineState, folder: str) -> List[dict]:
    """Every joined base recorded as belonging with this folder.

    All of them, never the first one. Two bases claiming one folder is the case
    the whole check exists for, and a search that stopped at the first match
    would hand one company's base to a session opened for another.
    """
    try:
        identity = folder_identity.capture(folder)
    except StateError:
        return []
    found = []
    for entry in state.joined:
        recorded_root = entry.get("content_root")
        recorded = folder_identity.clean(entry.get("content_identity"))
        if recorded_root is None or recorded is None:
            continue
        if folder_identity.matches(recorded, identity, recorded_root) in (
            folder_identity.SAME,
            folder_identity.MOVED,
        ):
            found.append(entry)
    return found
