"""What one seat remembers about one base, and nothing the team ever sees.

All of it lives under the seat folder, never in the clone, so deleting the
inbox or making a fresh copy of the base loses nothing that matters. Every file
is read as though a stranger wrote it: a file that cannot be read is treated as
empty and reported by code, and no read ever raises into a hook.

Nothing here ever stores a web address, an option a person typed, a payload
from a hook, or anything shaped like a key. Detail is stored as one of the
fixed codes in CODES, so a state file can be read out loud safely.
"""

from __future__ import annotations

import calendar
import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from . import constants, ids
from .errors import StateError
from .fsutil import atomic_write_json, atomic_write_text, read_json, read_text, remove
from .paths import armed_sentinel_path, seat_dir

# The only detail any seat state file is allowed to record.
CODES = {
    "ok": "nothing went wrong",
    "unreadable": "the file could not be read",
    "malformed": "the file did not hold what it should",
    "unknown-key": "the file held a setting we do not know",
    "bad-value": "a value in the file was not one we allow",
    "bad-row": "a line of the file could not be read",
    "expired": "it was there but too old to use",
    "symlink": "the file was a link to somewhere else",
    "not-a-file": "the name was there but it was not a file",
    "missing-file": "the file was not there",
    "missing-root": "the folder is no longer there",
    "missing-git": "the folder is no longer a repository",
    "missing-map": "the folder no longer holds the map",
    "id-mismatch": "the folder carries a different identifier",
    "unknown-id": "we never issued that",
    "consumed": "it was already used",
    "wrong-session": "it belongs to a different session",
    "too-old": "it was issued too long ago",
    "locked": "another writer holds the file",
    "stale-lock": "an old lock was cleared",
    "userinfo": "the address carried a sign-in",
    "redacted": "the value looked like a secret and was not stored",
    "write-failed": "the file could not be written",
    "hook-not-installed": "the terminal safeguard is not in place",
    "hook-chained": "the terminal safeguard runs after another one",
    "hook-renamed": "an existing safeguard was renamed and still runs",
    "pending-push": "a confirmation is waiting to be sent",
    "dropped-path": "a path was refused and the work was skipped",
    "pull-refused-paths": "an update carried files we never take on our own",
    "first-push-not-reviewed": "the first send from this base is not reviewed yet",
    "hooks-path-not-writable": "the folder the safeguard belongs in cannot be written",
    "existing-hook-unmovable": "an existing safeguard could not be moved aside",
    "hooks-dir-tracked": "the safeguard folder is part of the shared files",
    "allowlist-rejected": "the allowed-words file held something we never accept",
    "migration-not-available": "moving a seat folder is not available yet",
}

INBOX_INDEX_FILE = "inbox_index.jsonl"
SEAT_FILE = "seat.json"
QUESTION_IDS_FILE = "question_ids.json"
ASKED_LOG_FILE = "asked_log.jsonl"
SUPPRESSIONS_FILE = "suppressions.json"
DISMISSALS_FILE = "dismissals.json"
DROPPED_PATHS_FILE = "dropped_paths.jsonl"
CAPTURE_MARKER_FILE = "capture_marker.json"

_KEY_SHAPE = re.compile(
    r"(?:sk|pk|rk|ghp|gho|ghs|ghu|ghr|github_pat|xox[baprs]|AKIA|ASIA)[-_A-Za-z0-9]{10,}"
)
_LONG_SECRET = re.compile(r"[A-Za-z0-9+/=_]{32,}")


def check_code(code: Optional[str]) -> Optional[str]:
    """Refuse to store anything but one of the fixed codes."""
    if code is None:
        return None
    if code not in CODES:
        raise StateError("this is not a code we record", code="bad-value")
    return code


def now_utc() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(microsecond=0)


def now_local() -> datetime.datetime:
    """The moment it is where the person is sitting, to the second."""
    return datetime.datetime.now().replace(microsecond=0)


def local_date_of(moment: datetime.datetime) -> datetime.date:
    """The day it was where the person is, for a moment in universal time."""
    if moment.tzinfo is not None:
        return moment.astimezone().date()
    return datetime.datetime.fromtimestamp(
        calendar.timegm(moment.timetuple())
    ).date()


def today(moment: Optional[datetime.datetime] = None) -> datetime.date:
    """The day it is where the person is sitting.

    Every date that is compared with a date already in the base comes from
    here, so a run late in the evening west of London cannot decide that today
    is tomorrow while the person reading the answer is still on today. The only
    values kept in coordinated universal time are the time on a confirmation
    line and the moments in this seat's own files, and both say so where they
    are written. Handed a moment, this gives the day that moment fell on here.
    There is one clock behind all of it, so a test that fixes the moment fixes
    the day every part of a run agrees on.
    """
    if moment is None:
        return local_date_of(now_utc())
    if isinstance(moment, datetime.datetime):
        return local_date_of(moment)
    return moment


def now_local_iso(moment: Optional[datetime.datetime] = None) -> str:
    """A local moment written the one way, with no zone letter on the end."""
    stamp = moment or now_local()
    return stamp.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")


def iso_utc(moment: Optional[datetime.datetime] = None) -> str:
    """A moment written the one way every file here writes it."""
    stamp = moment or now_utc()
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return stamp.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(text: str) -> Optional[datetime.datetime]:
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def looks_like_a_secret(value: Any) -> bool:
    """Whether a value is the sort of thing a state file must never hold.

    Three things count: a web address of any kind, a run of characters shaped
    like one of the token prefixes the well known services use, and a long
    unbroken run that mixes upper case, lower case, and digits, which is what
    an encoded key looks like. A commit name and an identifier written in plain
    lower case digits and letters are not caught, which is the point: those are
    values these files are meant to hold.
    """
    if not isinstance(value, str):
        return False
    if "://" in value:
        return True
    if _KEY_SHAPE.search(value):
        return True
    for run in _LONG_SECRET.findall(value):
        has_upper = any(character.isupper() for character in run)
        has_lower = any(character.islower() for character in run)
        has_digit = any(character.isdigit() for character in run)
        if has_upper and has_lower and has_digit:
            return True
    return False


def safe_value(value: Any) -> Any:
    """Return the value, or the redacted code when it looks like a secret."""
    if looks_like_a_secret(value):
        return "redacted"
    return value


def _path(base_id: str, name: str) -> str:
    return os.path.join(seat_dir(base_id), name)


def _read_jsonl(path: str) -> Tuple[List[dict], List[str]]:
    problems: List[str] = []
    text = read_text(path)
    if text is None:
        if os.path.lexists(path):
            problems.append("unreadable")
        return [], problems
    rows = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            problems.append("bad-row")
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            problems.append("bad-row")
    return rows, problems


def _write_jsonl(path: str, rows: List[dict]) -> None:
    text = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows
    )
    atomic_write_text(path, text)


# --- The inbox index ---------------------------------------------------------

INDEX_FIELDS = (
    "source_id",
    "status",
    "landed_at",
    "seat",
    "source",
    "visibility",
    "intake_path",
    "staging_ids",
    "proposal_ids",
    "foreign_pr",
    "run_marker",
)


def _clean_index_row(row: dict, problems: List[str]) -> Optional[dict]:
    if not isinstance(row, dict):
        problems.append("bad-row")
        return None
    cleaned: Dict[str, Any] = {}
    for key, value in row.items():
        if key not in INDEX_FIELDS:
            problems.append("unknown-key")
            continue
        cleaned[key] = value
    source_id = cleaned.get("source_id")
    if not ids.is_source_id(source_id):
        problems.append("bad-row")
        return None
    status = cleaned.get("status")
    if status not in constants.INBOX_STATUSES:
        problems.append("bad-value")
        return None
    for name in ("staging_ids", "proposal_ids"):
        value = cleaned.get(name)
        cleaned[name] = [str(item) for item in value] if isinstance(value, list) else []
    foreign = cleaned.get("foreign_pr")
    cleaned["foreign_pr"] = foreign if isinstance(foreign, int) and not isinstance(foreign, bool) else None
    for name in ("landed_at", "seat", "source", "visibility", "intake_path", "run_marker"):
        value = cleaned.get(name)
        cleaned[name] = safe_value(value) if isinstance(value, str) else None
    return cleaned


def load_index(base_id: str) -> Tuple["Dict[str, dict]", List[str]]:
    """Every inbox row this seat knows about, keyed by the source's identifier."""
    rows, problems = _read_jsonl(_path(base_id, INBOX_INDEX_FILE))
    index: Dict[str, dict] = {}
    for row in rows:
        cleaned = _clean_index_row(row, problems)
        if cleaned is not None:
            index[cleaned["source_id"]] = cleaned
    return index, problems


def save_index(base_id: str, index: "Dict[str, dict]") -> None:
    """Write the whole index at once, so an interrupted write changes nothing."""
    _write_jsonl(_path(base_id, INBOX_INDEX_FILE), list(index.values()))


def upsert_row(base_id: str, source_id: str, **values) -> dict:
    """Add a row or update the parts of one, leaving the rest alone."""
    ids.check_source_id(source_id)
    index, _problems = load_index(base_id)
    row = index.get(source_id, {"source_id": source_id, "status": "landing"})
    for key, value in values.items():
        if key not in INDEX_FIELDS:
            raise StateError("the index has no field named %s" % key, code="bad-value")
        row[key] = safe_value(value) if isinstance(value, str) else value
    if row.get("status") not in constants.INBOX_STATUSES:
        raise StateError("that is not a status an inbox row can hold", code="bad-value")
    index[source_id] = row
    save_index(base_id, index)
    return row


def set_status(base_id: str, source_id: str, status: str) -> dict:
    if status not in constants.INBOX_STATUSES:
        raise StateError("that is not a status an inbox row can hold", code="bad-value")
    return upsert_row(base_id, source_id, status=status)


def unprocessed_rows(base_id: str) -> List[dict]:
    """The rows still waiting to be read, oldest first."""
    index, _problems = load_index(base_id)
    rows = [row for row in index.values() if row.get("status") in ("landing", "landed")]
    return sorted(rows, key=lambda row: (row.get("landed_at") or "", row["source_id"]))


def rows_with_missing_files(base_id: str, base_root: str) -> List[dict]:
    """Rows whose inbox file is gone, which are reported and never analysed."""
    index, _problems = load_index(base_id)
    missing = []
    for row in index.values():
        if row.get("status") not in ("landing", "landed"):
            continue
        item = os.path.join(base_root, constants.INBOX_DIR, row["source_id"] + ".md")
        if not os.path.isfile(item):
            missing.append(row)
    return sorted(missing, key=lambda row: row["source_id"])


# --- Seat state --------------------------------------------------------------

SEAT_DEFAULTS = {
    "schema": 1,
    "client": None,
    "vendor_substring": None,
    "slice_cursor": None,
    "first_run_path": None,
    "last_seen_commit": None,
    "session_id": None,
    "pending_confirmation": None,
    "pending_confirmation_line": None,
    "pending_confirmations": None,
    "last_pull_refusal": None,
    "last_pull_refusal_code": None,
    "last_pull_refusal_path_hashes": None,
    "first_push_reviewed": False,
    "git_hook_installed": False,
    "git_hook_code": None,
}


# What one held confirmation remembers while it waits to be sent.
PENDING_CONFIRMATION_FIELDS = ("line", "file", "held_at")


def _clean_pending_confirmations(value, problems: List[str]) -> List[dict]:
    """The answers waiting to be sent, with anything unreadable left out."""
    if value is None:
        return []
    if not isinstance(value, list):
        problems.append("bad-value")
        return []
    kept: List[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            problems.append("bad-row")
            continue
        held = {"line": None, "file": None, "held_at": None}
        for key, item in raw.items():
            if key not in PENDING_CONFIRMATION_FIELDS:
                problems.append("unknown-key")
                continue
            held[key] = item
        if not isinstance(held["line"], str) or not held["line"].strip():
            problems.append("bad-row")
            continue
        if looks_like_a_secret(held["line"]):
            problems.append("redacted")
            continue
        for key in ("file", "held_at"):
            if held[key] is not None and not isinstance(held[key], str):
                problems.append("bad-value")
                held[key] = None
        if any(held["line"] == already["line"] for already in kept):
            continue
        kept.append(held)
    return kept


def load_seat(base_id: str) -> Tuple[dict, List[str]]:
    """This seat's own settings, with anything unexpected dropped."""
    problems: List[str] = []
    path = _path(base_id, SEAT_FILE)
    seat = dict(SEAT_DEFAULTS)
    if os.path.lexists(path) and os.path.islink(path):
        return seat, ["symlink"]
    payload = read_json(path)
    if payload is None:
        if os.path.lexists(path):
            problems.append("malformed")
        return seat, problems
    if not isinstance(payload, dict):
        return seat, ["malformed"]
    for key, value in payload.items():
        if key not in SEAT_DEFAULTS:
            problems.append("unknown-key")
            continue
        seat[key] = value
    if seat["client"] is not None and seat["client"] not in constants.CLIENTS:
        seat["client"] = None
        problems.append("bad-value")
    for name in ("first_push_reviewed", "git_hook_installed"):
        if not isinstance(seat[name], bool):
            seat[name] = False
            problems.append("bad-value")
    for name in ("pending_confirmation", "git_hook_code", "last_pull_refusal_code"):
        if seat[name] is not None and seat[name] not in CODES:
            seat[name] = None
            problems.append("bad-value")
    seat["pending_confirmations"] = _clean_pending_confirmations(
        seat.get("pending_confirmations"), problems
    )
    for key, value in list(seat.items()):
        if isinstance(value, str) and looks_like_a_secret(value):
            seat[key] = "redacted"
            problems.append("redacted")
    # A seat written before answers were held as a list carries one answer on
    # its own, so it is read as a list of one and nothing is lost.
    legacy = seat.get("pending_confirmation_line")
    if (
        not seat["pending_confirmations"]
        and isinstance(legacy, str)
        and legacy.strip()
        and legacy != "redacted"
    ):
        seat["pending_confirmations"] = [
            {"line": legacy, "file": None, "held_at": None}
        ]
    return seat, problems


def save_seat(base_id: str, seat: dict) -> dict:
    """Write this seat's settings, dropping anything that looks like a secret."""
    cleaned = dict(SEAT_DEFAULTS)
    for key, value in seat.items():
        if key not in SEAT_DEFAULTS:
            raise StateError("seat state has no field named %s" % key, code="bad-value")
        cleaned[key] = safe_value(value) if isinstance(value, str) else value
    if cleaned["client"] is not None and cleaned["client"] not in constants.CLIENTS:
        raise StateError("that is not a client we know", code="bad-value")
    cleaned["pending_confirmations"] = _clean_pending_confirmations(
        cleaned.get("pending_confirmations"), []
    )
    check_code(cleaned["pending_confirmation"])
    check_code(cleaned["git_hook_code"])
    check_code(cleaned["last_pull_refusal_code"])
    atomic_write_json(_path(base_id, SEAT_FILE), cleaned)
    return cleaned


def update_seat(base_id: str, **values) -> dict:
    seat, _problems = load_seat(base_id)
    seat.update(values)
    return save_seat(base_id, seat)


# --- Question ids ------------------------------------------------------------

QUESTION_RECORD_FIELDS = (
    "id",
    "session_id",
    "issued_at",
    "consumed",
    "file",
    "trigger",
    "entry_id",
)


def load_question_ids(base_id: str) -> Tuple[List[dict], List[str]]:
    problems: List[str] = []
    payload = read_json(_path(base_id, QUESTION_IDS_FILE))
    if payload is None:
        return [], problems
    if not isinstance(payload, dict) or not isinstance(payload.get("ids"), list):
        return [], ["malformed"]
    records = []
    for raw in payload["ids"]:
        if not isinstance(raw, dict):
            problems.append("bad-row")
            continue
        record = {}
        for key, value in raw.items():
            if key not in QUESTION_RECORD_FIELDS:
                problems.append("unknown-key")
                continue
            record[key] = value
        if not ids.is_question_id(record.get("id")):
            problems.append("bad-row")
            continue
        record["consumed"] = bool(record.get("consumed"))
        records.append(record)
    return records, problems


def _save_question_ids(base_id: str, records: List[dict]) -> None:
    atomic_write_json(_path(base_id, QUESTION_IDS_FILE), {"schema": 1, "ids": records})


def prune_question_ids(
    base_id: str, now: Optional[datetime.datetime] = None
) -> List[dict]:
    """Throw away issued questions older than the keep window."""
    moment = now or now_utc()
    records, _problems = load_question_ids(base_id)
    cutoff = moment - datetime.timedelta(days=constants.QUESTION_ID_KEEP_DAYS)
    kept = []
    for record in records:
        issued = parse_iso_utc(record.get("issued_at", ""))
        if issued is not None and issued >= cutoff:
            kept.append(record)
    if len(kept) != len(records):
        _save_question_ids(base_id, kept)
    return kept


def issue_question_id(
    base_id: str,
    file_path: str,
    trigger: str,
    session_id: str,
    entry_id: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
) -> str:
    """Issue one single-use question id, bound to this session."""
    moment = now or now_utc()
    records = prune_question_ids(base_id, moment)
    question = ids.question_id(file_path, trigger, entry_id, session_id)
    records.append(
        {
            "id": question,
            "session_id": session_id,
            "issued_at": iso_utc(moment),
            "consumed": False,
            "file": file_path,
            "trigger": trigger,
            "entry_id": entry_id,
        }
    )
    _save_question_ids(base_id, records)
    return question


def consume_question_id(
    base_id: str,
    question: str,
    session_id: str,
    now: Optional[datetime.datetime] = None,
) -> Tuple[bool, str]:
    """Use a question id once. Every later attempt is refused with a code."""
    moment = now or now_utc()
    records, _problems = load_question_ids(base_id)
    for record in records:
        if record.get("id") != question:
            continue
        if record.get("consumed"):
            return False, "consumed"
        if record.get("session_id") != session_id:
            return False, "wrong-session"
        issued = parse_iso_utc(record.get("issued_at", ""))
        if issued is None:
            return False, "malformed"
        age = (moment - issued).total_seconds()
        if age > constants.QUESTION_ID_WINDOW_SECONDS:
            return False, "too-old"
        record["consumed"] = True
        _save_question_ids(base_id, records)
        return True, "ok"
    return False, "unknown-id"


# --- The asked-questions log -------------------------------------------------

ASKED_FIELDS = ("question_id", "date", "file", "trigger", "outcome")


def load_asked(base_id: str) -> Tuple[List[dict], List[str]]:
    rows, problems = _read_jsonl(_path(base_id, ASKED_LOG_FILE))
    kept = []
    for row in rows:
        record = {}
        for key, value in row.items():
            if key not in ASKED_FIELDS:
                problems.append("unknown-key")
                continue
            record[key] = value
        if record.get("outcome") not in constants.ASKED_OUTCOMES:
            problems.append("bad-value")
            continue
        kept.append(record)
    return kept, problems


def append_asked(
    base_id: str,
    question: str,
    file_path: str,
    trigger: str,
    outcome: str = "unanswered",
    day: Optional[datetime.date] = None,
) -> dict:
    """Record that a question was asked, which is the yes rate's denominator.

    The date is the day it is where the person is sitting, so it lines up with
    the dates the report counts over.
    """
    if outcome not in constants.ASKED_OUTCOMES:
        raise StateError("that is not an answer we record", code="bad-value")
    ids.check_question_id(question)
    row = {
        "question_id": question,
        "date": (day or today()).isoformat(),
        "file": file_path,
        "trigger": trigger,
        "outcome": outcome,
    }
    rows, _problems = load_asked(base_id)
    rows.append(row)
    _write_jsonl(_path(base_id, ASKED_LOG_FILE), rows)
    return row


def set_outcome(base_id: str, question: str, outcome: str) -> bool:
    if outcome not in constants.ASKED_OUTCOMES:
        raise StateError("that is not an answer we record", code="bad-value")
    rows, _problems = load_asked(base_id)
    found = False
    for row in rows:
        if row.get("question_id") == question:
            row["outcome"] = outcome
            found = True
    if found:
        _write_jsonl(_path(base_id, ASKED_LOG_FILE), rows)
    return found


# --- Suppressions ------------------------------------------------------------


def load_suppressions(base_id: str) -> Tuple["Dict[str, str]", List[str]]:
    payload = read_json(_path(base_id, SUPPRESSIONS_FILE))
    if payload is None:
        return {}, []
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), dict):
        return {}, ["malformed"]
    problems: List[str] = []
    files = {}
    for path, until in payload["files"].items():
        if not isinstance(until, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", until):
            problems.append("bad-value")
            continue
        files[path] = until
    return files, problems


def suppress(base_id: str, path: str, until: datetime.date) -> str:
    """Stop asking about one file until the given day."""
    files, _problems = load_suppressions(base_id)
    files[path] = until.isoformat() if isinstance(until, datetime.date) else str(until)
    atomic_write_json(
        _path(base_id, SUPPRESSIONS_FILE), {"schema": 1, "files": files}
    )
    return files[path]


def is_suppressed(base_id: str, path: str, today: datetime.date) -> bool:
    """A file is left alone up to, but not including, the day it comes back."""
    files, _problems = load_suppressions(base_id)
    until = files.get(path)
    if not until:
        return False
    day = today.isoformat() if isinstance(today, datetime.date) else str(today)
    return day < until


# --- Dismissals --------------------------------------------------------------


def load_dismissals(base_id: str) -> Tuple[dict, List[str]]:
    payload = read_json(_path(base_id, DISMISSALS_FILE))
    empty = {"inbox_ids": [], "ledger_behind_dismissed_until": None}
    if payload is None:
        return empty, []
    if not isinstance(payload, dict):
        return empty, ["malformed"]
    problems: List[str] = []
    result = dict(empty)
    for key, value in payload.items():
        if key == "schema":
            continue
        if key not in empty:
            problems.append("unknown-key")
            continue
        result[key] = value
    if not isinstance(result["inbox_ids"], list):
        result["inbox_ids"] = []
        problems.append("bad-value")
    result["inbox_ids"] = [
        item for item in result["inbox_ids"] if ids.is_source_id(item)
    ]
    until = result["ledger_behind_dismissed_until"]
    if until is not None and not (
        isinstance(until, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", until)
    ):
        result["ledger_behind_dismissed_until"] = None
        problems.append("bad-value")
    return result, problems


def _save_dismissals(base_id: str, value: dict) -> None:
    payload = {"schema": 1}
    payload.update(value)
    atomic_write_json(_path(base_id, DISMISSALS_FILE), payload)


def dismiss_inbox_item(base_id: str, source_id: str) -> dict:
    ids.check_source_id(source_id)
    value, _problems = load_dismissals(base_id)
    if source_id not in value["inbox_ids"]:
        value["inbox_ids"].append(source_id)
        _save_dismissals(base_id, value)
    return value


def is_dismissed(base_id: str, source_id: str) -> bool:
    value, _problems = load_dismissals(base_id)
    return source_id in value["inbox_ids"]


def set_ledger_behind_dismissed_until(base_id: str, until: datetime.date) -> dict:
    value, _problems = load_dismissals(base_id)
    value["ledger_behind_dismissed_until"] = (
        until.isoformat() if isinstance(until, datetime.date) else str(until)
    )
    _save_dismissals(base_id, value)
    return value


# --- Dropped paths -----------------------------------------------------------


def append_dropped_path(
    base_id: str,
    path: str,
    code: str,
    entry_id: Optional[str] = None,
    day: Optional[datetime.date] = None,
) -> dict:
    """Record that a path was refused, by its hash and never by its name.

    The same refusal is only ever recorded once. Reading a base is something
    that happens many times a day, and one bad path in one decision would
    otherwise add a row every single time until the file was the largest thing
    this seat holds. A row already there for the same path, the same reason,
    and the same decision is left as it is, keeping the day it was first seen.
    """
    check_code(code)
    row = {
        "date": (day or today()).isoformat(),
        "path_hash": ids.path_hash(path),
        "code": code,
        "entry_id": entry_id,
    }
    rows, _problems = _read_jsonl(_path(base_id, DROPPED_PATHS_FILE))
    for existing in rows:
        if (
            existing.get("path_hash") == row["path_hash"]
            and existing.get("code") == row["code"]
            and existing.get("entry_id") == row["entry_id"]
        ):
            return existing
    rows.append(row)
    _write_jsonl(_path(base_id, DROPPED_PATHS_FILE), rows)
    return row


def load_dropped_paths(base_id: str) -> Tuple[List[dict], List[str]]:
    return _read_jsonl(_path(base_id, DROPPED_PATHS_FILE))


# --- The capture run marker --------------------------------------------------

MARKER_FIELDS = ("session_id", "vendor_substring", "selected_ids", "armed_at", "expires_at")


def arm_capture(
    base_id: str,
    session_id: str,
    vendor_substring: str,
    selected_ids: List[str],
    now: Optional[datetime.datetime] = None,
) -> dict:
    """Say that a capture run is on, here and for the next few minutes only."""
    moment = now or now_utc()
    expires = moment + datetime.timedelta(
        seconds=constants.CAPTURE_MARKER_EXPIRY_SECONDS
    )
    marker = {
        "session_id": safe_value(session_id),
        "vendor_substring": safe_value(vendor_substring),
        "selected_ids": [str(safe_value(item)) for item in selected_ids],
        "armed_at": iso_utc(moment),
        "expires_at": iso_utc(expires),
    }
    atomic_write_json(_path(base_id, CAPTURE_MARKER_FILE), marker)
    atomic_write_text(armed_sentinel_path(), base_id + "\n")
    return marker


def read_capture_marker(
    base_id: str, now: Optional[datetime.datetime] = None
) -> Tuple[Optional[dict], str]:
    """The armed run, or nothing at all. An expired or bad marker is deleted."""
    moment = now or now_utc()
    path = _path(base_id, CAPTURE_MARKER_FILE)
    payload = read_json(path)
    if payload is None:
        if os.path.lexists(path):
            disarm_capture(base_id)
            return None, "malformed"
        return None, "missing-file"
    if not isinstance(payload, dict) or set(payload.keys()) != set(MARKER_FIELDS):
        disarm_capture(base_id)
        return None, "malformed"
    expires = parse_iso_utc(payload.get("expires_at", ""))
    if expires is None:
        disarm_capture(base_id)
        return None, "malformed"
    if moment >= expires:
        disarm_capture(base_id)
        return None, "expired"
    return payload, "ok"


def disarm_capture(base_id: str) -> None:
    """Clear the marker and the sentinel together, so neither outlives the other."""
    remove(_path(base_id, CAPTURE_MARKER_FILE))
    remove(armed_sentinel_path())


def is_armed() -> bool:
    """The cheap check a hook makes before it reads anything else."""
    return os.path.isfile(armed_sentinel_path())
