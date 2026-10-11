"""Which businesses one base covers, and which business a document is for.

One base can cover more than one business (requirement P40 of Plan 1, and
Brandon's decision D1). The map lists them in one setting, and each document
belongs to the business of the folder it sits in under `context`, or to the
business its own settings name, or to the whole company. For a kind each
business keeps its own of (`constants.BASE_KINDS`), a document that says
neither counts for no business. For a kind one document serves for the whole
company, such as the voice guide or a standard, a flat document with no line
is the whole company's; this reading of requirement P40 is recorded for
Brandon to confirm, because P40 says "counts for no business" without that
split.

This module only reads. Unit 4.2a of Plan 1 owns the grammar of both settings
and the operations that change them, and it adopts or replaces this reader
when it is built; until then nothing in GTM Base writes either setting. The
grammar here is the smallest one that fits the map's existing settings, one
`name: value` line under the map's Settings heading:

    businesses: insights (Acme Insights), courier-app (the courier app)

Each business is a short lower-case name made of letters, digits and hyphens,
which is also the name of its folder under `context`, followed by the name a
person calls it, in brackets, when they want one. A document says its
business with one line in its settings block, `business: courier-app`, or
`business: whole-company` for a document that serves every business.

A business's names are somebody's typing, so they are only ever shown inside
text held apart as data, in quotation marks, and never fill a sentence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Sequence, Tuple

from . import constants, formats
from .errors import PathError, ValidationError

# The setting in the map's Settings that lists the businesses.
BUSINESSES_SETTING = "businesses"
# The line in a document's settings block that says which business it is for.
BUSINESS_FIELD = "business"
# What that line says for a document that serves every business, and the key
# the inventory files the whole company's documents under.
WHOLE_COMPANY = "whole-company"

# The reasons a document's business is in doubt. Neither is ever said as it
# is; the inventory counts the documents each one covers.
CODE_NOT_IN_MAP = "business-not-in-map"
CODE_DISAGREE = "folder-and-settings-disagree"
# Why the map's list could not be read.
CODE_UNREADABLE = "businesses-unreadable"

# The one shape a business's short name may take, which is also the folder
# name under `context`.
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# One business in the list: its short name, then its name in brackets.
_ITEM_RE = re.compile(r"^(?P<slug>[^\s()]+)(?:\s*\((?P<name>[^()]*)\))?$")
_SETTING_RE = re.compile(
    r"^[ \t]*%s[ \t]*:(?P<value>.*)$" % re.escape(BUSINESSES_SETTING), re.MULTILINE
)

# Folders under `context` that are something else already, so no business may
# be called by their names: the segments of the customer profile, and every
# folder the older layout used.
RESERVED_SLUGS = frozenset(
    [constants.SEGMENTS_DIR.split("/")[-1], WHOLE_COMPANY]
    + [
        folder.split("/")[1]
        for folder in constants.LEGACY_TEMPLATE_FOLDERS
        if folder.startswith(constants.CONTEXT_DIR + "/")
    ]
)

# The punctuation a business's name may hold beside letters, digits and
# spaces. Brackets, commas and colons are left out because they shape the
# list itself, and quotation marks, backticks and anything that draws nothing
# are left out so a name can never close the quotation it is shown in.
_NAME_PUNCTUATION = frozenset("&'.-/+")


class Business(object):
    """One business the map lists: its short name and, when given, its name."""

    __slots__ = ("slug", "name")

    def __init__(self, slug: str, name: Optional[str] = None):
        self.slug = slug
        self.name = name

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Business)
            and other.slug == self.slug
            and other.name == self.name
        )

    def __repr__(self) -> str:
        return "Business(%r, %r)" % (self.slug, self.name)


def _plain_name(text: str) -> Optional[str]:
    """A business's name when its words are plain, or None when any are in doubt."""
    words = " ".join(str(text or "").split())
    if not words or len(words) > constants.SEGMENT_NAME_MAX_CHARS:
        return None
    if not any(character.isalpha() for character in words):
        return None
    for character in words:
        if character == " " or character in _NAME_PUNCTUATION:
            continue
        category = unicodedata.category(character)
        if category[0] not in ("L", "N") or category == "Lm":
            return None
        if "FILLER" in unicodedata.name(character, "FILLER"):
            return None
    return words


def check_slug(value: str) -> str:
    """One business's short name, or a refusal saying the shape is wrong."""
    slug = str(value or "").strip()
    if (
        not _SLUG_RE.match(slug)
        or len(slug) > constants.SEGMENT_SLUG_MAX_CHARS
        or slug in RESERVED_SLUGS
    ):
        raise ValidationError(
            "a business in the map is not a short lower-case name",
            code=CODE_UNREADABLE,
        )
    return slug


def _body_of(map_text: str) -> str:
    """The map below its settings block, or all of it when it has none."""
    try:
        _block, body = formats.split_document(map_text or "")
    except (ValidationError, PathError):
        return map_text or ""
    return body


def read_map_businesses(map_text: str) -> List[Business]:
    """The businesses the map lists, in its order, or none for the whole company.

    A list that cannot be read is refused rather than guessed at, the way a
    map setting out of range is: a business dropped by a guess is a business
    whose missing documents nobody is told about.
    """
    found = _SETTING_RE.findall(_body_of(map_text))
    if not found:
        return []
    if len(found) > 1:
        raise ValidationError(
            "the map lists its businesses more than once", code=CODE_UNREADABLE
        )
    value = found[0].strip()
    if not value:
        return []
    listed: List[Business] = []
    for raw in value.split(","):
        match = _ITEM_RE.match(raw.strip())
        if match is None:
            raise ValidationError(
                "a business in the map cannot be read", code=CODE_UNREADABLE
            )
        slug = check_slug(match.group("slug"))
        name = None
        if match.group("name") is not None:
            name = _plain_name(match.group("name"))
            if name is None:
                raise ValidationError(
                    "a business's name in the map is not plain words",
                    code=CODE_UNREADABLE,
                )
        if any(one.slug == slug for one in listed):
            raise ValidationError(
                "the map lists one business twice", code=CODE_UNREADABLE
            )
        listed.append(Business(slug, name))
    return listed


def folder_of(path: str) -> Optional[str]:
    """The folder directly under `context` a document sits in, or None when flat."""
    parts = str(path or "").replace("\\", "/").split("/")
    if len(parts) < 3 or parts[0] != constants.CONTEXT_DIR:
        return None
    return parts[1]


def document_business(
    path: str, fields: Dict, listed: Sequence[Business]
) -> Tuple[Optional[str], Optional[str]]:
    """Which business one document is for, and the reason when that is in doubt.

    What comes back is the business's short name, `WHOLE_COMPANY`, or None,
    with None or a code beside it. The folder decides first. A folder that is
    a business the map does not list, a line naming one, and a folder and a
    line that disagree each count for no business, and the code says which,
    because choosing between two answers is not a reader's call.
    """
    slugs = [one.slug for one in listed]
    stated = fields.get(BUSINESS_FIELD) if isinstance(fields, dict) else None
    line = str(stated).strip().lower() if stated not in (None, "") else None

    folder = folder_of(path)
    if folder is not None and folder not in RESERVED_SLUGS:
        if folder not in slugs:
            return None, CODE_NOT_IN_MAP
        if line is not None and matching(line, listed) != folder:
            return None, CODE_DISAGREE
        return folder, None

    if line is None:
        return None, None
    if line == WHOLE_COMPANY:
        return WHOLE_COMPANY, None
    named = matching(line, listed)
    if named is not None:
        return named, None
    return None, CODE_NOT_IN_MAP


def as_data(business: Business) -> str:
    """A business as it is shown inside text held apart as data, never elsewhere.

    Its name in quotation marks when the map gives one, or its short name in
    quotation marks, which the list's grammar has already kept to letters,
    digits and hyphens.
    """
    return '"%s"' % (business.name or business.slug)


def matching(value: str, listed: Sequence[Business]) -> Optional[str]:
    """The short name of the listed business a person's words name, or None.

    A business is named by its short name, or by its name in the map with any
    opening "the" and the letter case set aside.
    """
    said = " ".join(str(value or "").split()).lower()
    if not said:
        return None
    for business in listed:
        if said == business.slug:
            return business.slug
        if business.name and _without_the(said) == _without_the(business.name.lower()):
            return business.slug
    return None


def _without_the(text: str) -> str:
    return text[4:] if text.startswith("the ") else text
