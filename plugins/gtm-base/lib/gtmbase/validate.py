"""The checks that stand between a file someone wrote and the rest of the code.

The map is a file the whole team can edit, so its two settings are read with a
range check. An owner is an email address and nothing else, because a
confirmation is matched to the person who wrote it. And every proposal carries
one marker line, which is how a later run recognises work it already did.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from . import constants
from .errors import ValidationError
from .ids import (  # noqa: F401  (re-exported for callers)
    check_base_id,
    check_content_hash,
    check_entry_id,
    check_question_id,
    check_run_id,
    check_source_id,
    check_staging_id,
    is_base_id,
    is_question_id,
    is_run_id,
    is_source_id,
    is_staging_id,
)

MAX_FILENAME_LENGTH = 120

MARKER_PREFIX = "gtm-base proposal"

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)

_SETTING_RE = r"^[ \t]*%s[ \t]*:[ \t]*(?P<value>.*?)[ \t]*$"

_MARKER_RE = re.compile(
    r"^\s*gtm-base proposal (?P<staging>\S+) entry (?P<entry>\S+) source (?P<source>\S+)\s*$"
)

_FORBIDDEN_FILENAME_CHARACTERS = ("/", "\\", "[", "]", "(", ")", ":", "*", "?", '"', "|")


# --- The map's settings ------------------------------------------------------


def read_map_settings(text: str) -> dict:
    """Read the two numbers the map is allowed to set.

    Both are counted in days and must be whole numbers inside the allowed
    range. A setting that is absent takes its default; a setting that is
    present and out of range stops the read, because guessing what a team meant
    by a value they typed is worse than saying the file is wrong.
    """
    settings = {
        "confirmation_threshold_days": constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS,
        "not_now_days": constants.DEFAULT_NOT_NOW_DAYS,
    }
    body = text or ""
    for key in list(settings.keys()):
        pattern = re.compile(_SETTING_RE % re.escape(key), re.MULTILINE)
        match = pattern.search(body)
        if match is None:
            continue
        raw = match.group("value")
        if not re.match(r"^-?\d+$", raw):
            raise ValidationError(
                "the map setting %s must be a whole number of days" % key,
                code="setting-not-a-number",
            )
        value = int(raw)
        if value < constants.MAP_SETTING_MIN or value > constants.MAP_SETTING_MAX:
            raise ValidationError(
                "the map setting %s must be between %d and %d days"
                % (key, constants.MAP_SETTING_MIN, constants.MAP_SETTING_MAX),
                code="setting-out-of-range",
            )
        settings[key] = value
    return settings


# --- Owners ------------------------------------------------------------------


def is_valid_email(value) -> bool:
    """Whether this is one plain email address and nothing else.

    A display name, a comment, spaces, a second address, or anything outside
    the ASCII range makes it invalid, because the address is compared letter
    for letter against the author of a recorded change.
    """
    if not isinstance(value, str):
        return False
    if len(value) > 254 or value != value.strip():
        return False
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    if any(character.isspace() for character in value):
        return False
    if value.count("@") != 1:
        return False
    local, _, domain = value.partition("@")
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if ".." in domain or domain.startswith("-") or domain.endswith("-"):
        return False
    return bool(_EMAIL_RE.match(value))


def validate_owner(value) -> List[str]:
    """Return the owner addresses of a file, or say which one is wrong.

    The value is either one address or an inline list of them. The error names
    the position in the list rather than the value itself, so a value that was
    really a password or a key never reaches a log or a message.
    """
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            inner = text[1:-1].strip()
            candidates = [part.strip() for part in inner.split(",")] if inner else []
        else:
            candidates = [text]
    else:
        raise ValidationError("the owner value is not an address", code="owner-invalid")

    if not candidates:
        raise ValidationError("the owner value is empty", code="owner-empty")

    addresses = []
    for position, candidate in enumerate(candidates, start=1):
        if not is_valid_email(candidate):
            raise ValidationError(
                "owner value number %d is not one email address" % position,
                code="owner-invalid",
            )
        addresses.append(candidate)
    return addresses


# --- File names --------------------------------------------------------------


def validate_filename(name) -> str:
    """Check a single file name, which is never a path and never hidden."""
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("the file name is empty", code="name-empty")
    text = name.strip()
    if len(text) > MAX_FILENAME_LENGTH:
        raise ValidationError(
            "the file name is longer than %d characters" % MAX_FILENAME_LENGTH,
            code="name-long",
        )
    for character in text:
        if ord(character) < 32 or ord(character) == 127:
            raise ValidationError(
                "the file name holds a control character", code="name-control"
            )
    for character in _FORBIDDEN_FILENAME_CHARACTERS:
        if character in text:
            raise ValidationError(
                "the file name holds a character we never allow", code="name-character"
            )
    if ".." in text:
        raise ValidationError("the file name climbs out of its folder", code="name-climbing")
    if text.startswith("."):
        raise ValidationError("the file name is hidden", code="name-hidden")
    return text


# --- The marker line ---------------------------------------------------------


def marker_line(
    staging_id: str, entry_id: Optional[str] = None, source_id: Optional[str] = None
) -> str:
    """The one line that names a proposal wherever it ends up.

    It is written as plain visible text, never as a hidden comment, because the
    outgoing scan refuses hidden content and would otherwise refuse every
    proposal this plugin writes.
    """
    check_staging_id(staging_id)
    entry = entry_id if entry_id else "-"
    source = source_id if source_id else "-"
    if entry != "-":
        check_entry_id(entry)
    if source != "-":
        check_source_id(source)
    return "%s %s entry %s source %s" % (MARKER_PREFIX, staging_id, entry, source)


def parse_marker_line(line) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Read one marker line, or return None when the line is not a marker."""
    if not isinstance(line, str):
        return None
    if "<!--" in line or "-->" in line:
        return None
    match = _MARKER_RE.match(line)
    if match is None:
        return None
    staging = match.group("staging")
    entry = match.group("entry")
    source = match.group("source")
    if not is_staging_id(staging):
        return None
    if entry != "-" and not is_staging_id(entry):
        return None
    if source != "-" and not is_source_id(source):
        return None
    return (
        staging,
        None if entry == "-" else entry,
        None if source == "-" else source,
    )


def find_marker(text) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Find the marker in a body or a corrections file, if there is one."""
    if not isinstance(text, str):
        return None
    for line in text.splitlines():
        parsed = parse_marker_line(line)
        if parsed is not None:
            return parsed
    return None
