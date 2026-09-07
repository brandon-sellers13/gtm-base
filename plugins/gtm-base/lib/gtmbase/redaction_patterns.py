"""The shapes the outgoing-content scan refuses, and nothing else.

Every pattern here answers one question: does this line carry something that
should not leave the person's computer. A pattern never reports what it
matched, only which class it belongs to, because the whole point of the scan is
that a private value is not repeated into a hook message, a log, or a model's
context.

The classes are deliberately few and deliberately blunt. Money figures are not
a class: a base is full of numbers on purpose, and refusing them would refuse
the work itself.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# --- Class names -------------------------------------------------------------

EMAIL = "email"
PHONE = "phone"
KEY_SHAPE = "key-shape"
VENDOR_URL_TOKEN = "vendor-url-token"
DOCUMENT_SHARE_LINK = "document-share-link"
LOCAL_PATH = "local-path"
HIDDEN_CONTENT = "hidden-content"
# Not a pattern class: it is decided by the path of the file, not its text.
TRANSIENT_FOLDER = "transient-folder"

# What a person is told when a class is found. Never the value itself.
CLASS_LABELS: Dict[str, str] = {
    EMAIL: "an email address",
    PHONE: "a phone number",
    KEY_SHAPE: "something shaped like a key or a token",
    VENDOR_URL_TOKEN: "a web address carrying a key or a signature",
    DOCUMENT_SHARE_LINK: "a link to a shared document",
    LOCAL_PATH: "a path from inside a home folder on this computer",
    HIDDEN_CONTENT: "text that would be hidden from a reader",
    TRANSIENT_FOLDER: "a file from a folder that is yours alone",
}

# --- The patterns ------------------------------------------------------------

_EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
)

# A phone number is only a phone number when it is written like one: with
# separators, or with a country code in front, or with an area code in
# parentheses. A run of digits on its own is far more often an identifier.
_PHONE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:"
    r"\+[0-9]{1,3}[\s.\-]?(?:\([0-9]{1,4}\)[\s.\-]?)?[0-9]{2,4}(?:[\s.\-][0-9]{2,4}){1,4}"
    r"|\([0-9]{3}\)[\s.\-]?[0-9]{3}[\s.\-]?[0-9]{4}"
    r"|[0-9]{3}[\s.\-][0-9]{3}[\s.\-][0-9]{4}"
    r")"
    r"(?![0-9A-Za-z])"
)
# Fewer digits than this and it is not a phone number anyone could dial.
MIN_PHONE_DIGITS = 10

_KEY_SHAPE = re.compile(
    r"AKIA[0-9A-Z]{16}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|gh[pousr]_[A-Za-z0-9]{36}"
    r"|xox[abpors]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|(?i:api[_-]?key|secret|token|password)\s*[:=]\s*\S{12,}"
)

_VENDOR_URL_TOKEN = re.compile(
    r"https?://\S*?[?&](?:token|key|access_token|sig|signature|X-Amz-Signature)="
    r"|(?i:X-Amz-Signature)="
    r"|hooks\.slack\.com/services/"
    r"|fireflies\.ai/\S*?token"
)

_DOCUMENT_SHARE_LINK = re.compile(
    r"(?:https?://)?(?:[A-Za-z0-9-]+\.)?notion\.(?:so|site)/\S*?[0-9a-fA-F]{32}"
    r"|docs\.google\.com/(?:document|spreadsheets|presentation)/d/"
    r"|drive\.google\.com/file/d/"
    r"|dropbox\.com/(?:s/|scl/)"
    r"|box\.com/s/"
    r"|[A-Za-z0-9-]+\.sharepoint\.com/"
    r"|onedrive\.live\.com/"
)

_LOCAL_PATH = re.compile(r"/(?:Users|home)/[^/\s\"']+/")

# Zero-width characters, the two directional overrides, and anything that reads
# as markup. A reader sees none of these; a model reads all of them.
_HIDDEN_CONTENT = re.compile(
    r"<!--"
    r"|-->"
    r"|[\u200b\u200c\u200d\u2060\ufeff]"
    r"|[\u202a-\u202e]"
    r"|[\u2066-\u2069]"
    r"|<[a-zA-Z][^>]*>"
)

# The same three shapes again, one at a time, so a caller that takes hidden
# content out of a piece of text can say how much of each kind it took out.
# They are here rather than beside the caller because the class above is the
# thing they have to stay in step with.

# A comment, opening mark to closing mark, however many lines it runs over.
HIDDEN_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# An opening or closing comment mark with no partner, which is what is left
# when comments were nested inside one another.
HIDDEN_COMMENT_MARK = re.compile(r"<!--|-->")
# Anything that reads as a tag rather than as words.
HIDDEN_TAG = re.compile(r"<[a-zA-Z][^>]*>")
# The characters no reader ever sees: the zero-width ones and the two sets
# that reorder a line without changing a letter of it.
HIDDEN_CHARACTER = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069]"
)

# The order a line is read in. A key is reported before an address, because it
# is the more serious of the two and the message names one class.
PATTERN_CLASSES: List[Tuple[str, "re.Pattern", str]] = [
    (KEY_SHAPE, _KEY_SHAPE, CLASS_LABELS[KEY_SHAPE]),
    (VENDOR_URL_TOKEN, _VENDOR_URL_TOKEN, CLASS_LABELS[VENDOR_URL_TOKEN]),
    (DOCUMENT_SHARE_LINK, _DOCUMENT_SHARE_LINK, CLASS_LABELS[DOCUMENT_SHARE_LINK]),
    (LOCAL_PATH, _LOCAL_PATH, CLASS_LABELS[LOCAL_PATH]),
    (EMAIL, _EMAIL, CLASS_LABELS[EMAIL]),
    (PHONE, _PHONE, CLASS_LABELS[PHONE]),
    (HIDDEN_CONTENT, _HIDDEN_CONTENT, CLASS_LABELS[HIDDEN_CONTENT]),
]

# Classes an allowed-words entry can never excuse. A folder that is yours alone
# stays yours alone, and nobody gets to declare a key safe to send.
NEVER_ALLOWLISTED = (TRANSIENT_FOLDER, KEY_SHAPE)


def _phone_is_real(value: str) -> bool:
    """Whether a phone-shaped match holds enough digits to be a phone number."""
    digits = sum(1 for character in value if character.isdigit())
    return digits >= MIN_PHONE_DIGITS


_VALIDATORS = {PHONE: _phone_is_real}


def label_for(pattern_class: str) -> str:
    """The words a person is shown for a class, and never the value found."""
    return CLASS_LABELS.get(pattern_class, "something we do not send")


def redact_for_report(value: str) -> str:
    """Return only what a match may be called out loud.

    The argument is accepted and thrown away on purpose, so that a caller that
    reaches for the value gets the label instead of the value every time.
    """
    del value
    return "a value we do not repeat"


def find_in_line(line: str, classes=None) -> List[Tuple[str, str]]:
    """Return (class name, matched value) for every pattern found in one line.

    The matched value leaves this module only so the caller can compare it with
    the allowed-words list. Nothing else may keep it.
    """
    found: List[Tuple[str, str]] = []
    for name, pattern, _label in PATTERN_CLASSES:
        if classes is not None and name not in classes:
            continue
        for match in pattern.finditer(line):
            value = match.group(0)
            validator = _VALIDATORS.get(name)
            if validator is not None and not validator(value):
                continue
            found.append((name, value))
    return found
