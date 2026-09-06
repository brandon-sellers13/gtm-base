"""Every identifier GTM Base writes down, and the checks that keep them clean.

Identifiers are derived from facts the plugin controls (a source's text, a file
path, a sequence number, a remote address), never from anything a model wrote,
so the same run repeated gives the same identifier and a rerun can recognise
work it already did.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
import unicodedata
from typing import Optional, Sequence

# The separator used when several parts are hashed together. It is a control
# character, so it can never appear in a path, an identifier, or a vendor name.
JOIN_SEPARATOR = "\x1f"

SOURCE_HASH_PREFIX = "src-"
STAGING_PREFIX = "stg-"
QUESTION_PREFIX = "q-"
RUN_PREFIX = "run-"

SOURCE_HASH_LENGTH = 24
STAGING_LENGTH = 16
QUESTION_LENGTH = 20
BASE_ID_LENGTH = 32

_WHITESPACE = re.compile(r"\s+")
_SOURCE_HASH_RE = re.compile(r"^src-[0-9a-f]{%d}$" % SOURCE_HASH_LENGTH)
_SOURCE_VENDOR_RE = re.compile(r"^src-[a-z0-9]{2,32}-[A-Za-z0-9_-]{1,64}$")
_STAGING_RE = re.compile(r"^stg-[0-9a-f]{%d}$" % STAGING_LENGTH)
_QUESTION_RE = re.compile(r"^q-[0-9a-f]{%d}$" % QUESTION_LENGTH)
_RUN_RE = re.compile(r"^run-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$")
_BASE_ID_RE = re.compile(r"^[0-9a-f]{%d}$" % BASE_ID_LENGTH)
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_VENDOR_RE = re.compile(r"^[a-z0-9]{2,32}$")
_RECORDING_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Remote addresses this library understands, reduced to host, owner, and name.
_SCP_RE = re.compile(r"^(?:(?P<user>[^@/]+)@)?(?P<host>[A-Za-z0-9._-]+):(?P<path>.+)$")
_URL_RE = re.compile(
    r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://"
    r"(?:(?P<user>[^/@]+)@)?"
    r"(?P<host>[^/:]+)"
    r"(?::(?P<port>\d+))?"
    r"(?P<path>/.*)?$"
)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    """Reduce text to the form two exports of the same call always share.

    Leading and trailing space is removed, every run of whitespace becomes one
    space, and the result is normalised to Unicode NFC. Letter case is left
    alone, because a change of case is a change of content.
    """
    if text is None:
        raise ValueError("text is required")
    collapsed = _WHITESPACE.sub(" ", text).strip()
    return unicodedata.normalize("NFC", collapsed)


def source_id_for_text(text: str) -> str:
    """The identifier of a transcript or note that carries no vendor identifier."""
    return SOURCE_HASH_PREFIX + _sha256_hex(normalize_text(text))[:SOURCE_HASH_LENGTH]


def source_id_for_vendor(vendor: str, recording_id: str) -> str:
    """The identifier of a recording the vendor already named."""
    if not _VENDOR_RE.match(vendor or ""):
        raise ValueError("vendor name is not allowed")
    if not _RECORDING_ID_RE.match(recording_id or ""):
        raise ValueError("recording id is not allowed")
    return "%s%s-%s" % (SOURCE_HASH_PREFIX, vendor, recording_id)


def _join_parts(parts: Sequence[str]) -> str:
    for part in parts:
        if JOIN_SEPARATOR in part:
            raise ValueError("a part of an identifier held the separator")
    return JOIN_SEPARATOR.join(parts)


def staging_id(source_id: str, target_path: str, origin: str, sequence: int) -> str:
    """The identifier of one staged proposal, stable across runs.

    It is derived from the source, the file the proposal changes, where the
    proposal came from, and its position within that source. It never depends
    on anything a model wrote, so the same work twice gives the same id.
    """
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise ValueError("sequence must be a whole number of zero or more")
    if not source_id or not target_path or not origin:
        raise ValueError("source id, target path, and origin are all required")
    digest = _sha256_hex(
        _join_parts([str(source_id), str(target_path), str(origin), str(sequence)])
    )
    return STAGING_PREFIX + digest[:STAGING_LENGTH]


def entry_id_for(staging_id_value: str) -> str:
    """A ledger entry is named by the proposal that carries it."""
    check_staging_id(staging_id_value)
    return staging_id_value


def question_id(
    file_path: str,
    trigger: str,
    entry_id: Optional[str],
    session_id: str,
    rand: Optional[bytes] = None,
) -> str:
    """A single-use identifier for one confirmation question.

    The random part is what makes it single use: two questions about the same
    file in the same session are still different questions.
    """
    suffix = rand if rand is not None else os.urandom(16)
    if len(suffix) < 16:
        raise ValueError("the random part must be at least sixteen bytes")
    material = _join_parts(
        [
            str(file_path),
            str(trigger),
            str(entry_id or "-"),
            str(session_id),
            suffix.hex(),
        ]
    )
    return QUESTION_PREFIX + _sha256_hex(material)[:QUESTION_LENGTH]


def run_id(today: Optional[datetime.date] = None) -> str:
    """The identifier of one run of a skill, dated so a person can read it."""
    day = today or datetime.date.today()
    return "%s%s-%s" % (RUN_PREFIX, day.isoformat(), os.urandom(4).hex())


def base_id_random() -> str:
    """A fresh identifier for a base that has no remote address yet."""
    return os.urandom(16).hex()


def strip_userinfo(url: str) -> str:
    """Return the address with any user name or password removed."""
    text = (url or "").strip()
    match = _URL_RE.match(text)
    if match:
        host = match.group("host")
        port = match.group("port")
        path = match.group("path") or ""
        authority = host + (":" + port if port else "")
        return "%s://%s%s" % (match.group("scheme"), authority, path)
    scp = _SCP_RE.match(text)
    if scp:
        return "%s:%s" % (scp.group("host"), scp.group("path"))
    return text


def canonical_remote_address(url: str) -> str:
    """Reduce every way of writing one repository address to a single form.

    The three addresses a person can copy for the same repository, the browser
    address, the one the tool prints, and the one used over a secure shell, all
    reduce to `host/owner/name`. The host and the path are lowercased, because
    the hosts this plugin supports treat them that way, any user name is
    dropped, and a trailing slash or `.git` is removed.
    """
    text = (url or "").strip()
    if not text:
        raise ValueError("a remote address is required")

    match = _URL_RE.match(text)
    if match:
        host = match.group("host")
        path = match.group("path") or ""
    else:
        scp = _SCP_RE.match(text)
        if not scp:
            raise ValueError("this remote address is not one this library reads")
        host = scp.group("host")
        path = scp.group("path")

    host = host.strip().lower()
    path = path.strip().strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    path = path.strip("/").lower()
    if not host or not path:
        raise ValueError("this remote address names no repository")
    return "%s/%s" % (host, path)


def base_id_for_remote(url: str) -> str:
    """The identifier every seat computes for the same remote repository."""
    return _sha256_hex(canonical_remote_address(url))[:BASE_ID_LENGTH]


def content_hash(text: str) -> str:
    """The hash of a piece of content, with line endings made uniform first."""
    if text is None:
        raise ValueError("text is required")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return _sha256_hex(normalized)


def path_hash(path: str) -> str:
    """The hash of a path, recorded when the path itself must not be stored."""
    return _sha256_hex(str(path))


# --- Charset checks ---------------------------------------------------------


def _check(pattern, value, kind):
    if not isinstance(value, str) or not pattern.match(value):
        raise ValueError("this is not a valid %s" % kind)
    return value


def check_source_id(value: str) -> str:
    if isinstance(value, str) and (
        _SOURCE_HASH_RE.match(value) or _SOURCE_VENDOR_RE.match(value)
    ):
        return value
    raise ValueError("this is not a valid source id")


def check_staging_id(value: str) -> str:
    return _check(_STAGING_RE, value, "staging id")


def check_entry_id(value: str) -> str:
    return _check(_STAGING_RE, value, "entry id")


def check_question_id(value: str) -> str:
    return _check(_QUESTION_RE, value, "question id")


def check_run_id(value: str) -> str:
    return _check(_RUN_RE, value, "run id")


def check_base_id(value: str) -> str:
    return _check(_BASE_ID_RE, value, "base id")


def check_content_hash(value: str) -> str:
    return _check(_CONTENT_HASH_RE, value, "content hash")


def is_source_id(value) -> bool:
    try:
        check_source_id(value)
        return True
    except ValueError:
        return False


def is_staging_id(value) -> bool:
    try:
        check_staging_id(value)
        return True
    except ValueError:
        return False


def is_question_id(value) -> bool:
    try:
        check_question_id(value)
        return True
    except ValueError:
        return False


def is_run_id(value) -> bool:
    try:
        check_run_id(value)
        return True
    except ValueError:
        return False


def is_base_id(value) -> bool:
    try:
        check_base_id(value)
        return True
    except ValueError:
        return False
