"""Every file GTM Base reads or writes, with one parser and one writer each.

The files are markdown with a short block of settings at the top, because a
person has to be able to read a proposal in a review and a context change
without any tool at all. The block is a deliberately small part of YAML:
plain values, lists, and nothing nested. Anything more, and a file the whole
team can edit becomes a place to hide behaviour.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from . import constants
from .errors import PathError, ValidationError
from .paths import check_context_path_syntax, check_repo_path_syntax, PROPOSAL_PATH_PREFIXES
from .validate import (
    check_content_hash,
    check_run_id,
    check_source_id,
    check_staging_id,
    find_marker,
    is_run_id,
    is_source_id,
    is_staging_id,
    marker_line,
    parse_marker_line,
)

FRONTMATTER_FENCE = "---"
_KEY_RE = re.compile(r"^[a-z0-9_]+$")
_INT_RE = re.compile(r"^-?\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}Z$")
_FENCE_RE = re.compile(r"^(`{3,})\s*([A-Za-z0-9_-]*)\s*$")

EMPTY = "-"


# --- The settings block at the top of a file --------------------------------


def split_document(text: str) -> Tuple[str, str]:
    """Separate the settings block at the top of a file from its body."""
    if not isinstance(text, str):
        raise ValidationError("this file is not text", code="not-text")
    body = text
    if body.startswith("﻿"):
        body = body[1:]
    lines = body.split("\n")
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        raise ValidationError(
            "this file does not start with a settings block", code="no-frontmatter"
        )
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_FENCE:
            block = "\n".join(lines[1:index])
            rest = "\n".join(lines[index + 1 :])
            if rest.startswith("\n"):
                rest = rest[1:]
            return block, rest
    raise ValidationError(
        "the settings block at the top of this file is never closed",
        code="unclosed-frontmatter",
    )


def parse_scalar(text: str) -> Any:
    """Read one plain value: a word, a number, a yes or no, or a date."""
    value = text.strip()
    if value.startswith("{"):
        raise ValidationError(
            "a settings value may not hold another block of settings",
            code="nested-mapping",
        )
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        inner = value[1:-1]
        if value[0] in inner:
            raise ValidationError("this quoted value is not closed", code="bad-quote")
        return inner
    if value == "true":
        return True
    if value == "false":
        return False
    if _INT_RE.match(value):
        return int(value)
    return value


def _parse_inline_list(text: str) -> List[Any]:
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    if "[" in inner or "]" in inner:
        raise ValidationError("a list may not hold another list", code="nested-list")
    return [parse_scalar(part) for part in inner.split(",")]


def parse_frontmatter(block: str) -> Dict[str, Any]:
    """Read the settings block into plain values, lists, and nothing else."""
    fields: Dict[str, Any] = {}
    open_list_key: Optional[str] = None
    for number, raw in enumerate(block.split("\n"), start=1):
        if "\t" in raw:
            raise ValidationError(
                "line %d of the settings block holds a tab" % number, code="tab"
            )
        if not raw.strip():
            open_list_key = None
            continue
        stripped = raw.lstrip(" ")
        if stripped.startswith("- ") or stripped == "-":
            if open_list_key is None:
                raise ValidationError(
                    "line %d starts a list under no setting" % number,
                    code="orphan-list-item",
                )
            item = stripped[1:].strip()
            fields[open_list_key].append(parse_scalar(item) if item else "")
            continue
        if raw != stripped:
            raise ValidationError(
                "line %d is indented, and settings never nest" % number,
                code="nested-mapping",
            )
        if ":" not in raw:
            raise ValidationError(
                "line %d of the settings block is not a setting" % number,
                code="not-a-setting",
            )
        key, _, value = raw.partition(":")
        key = key.strip()
        if not _KEY_RE.match(key):
            raise ValidationError(
                "the setting name on line %d holds characters we never allow" % number,
                code="bad-key",
            )
        if key in fields:
            raise ValidationError(
                "the setting %s appears twice" % key, code="duplicate-key"
            )
        value = value.strip()
        if not value:
            fields[key] = []
            open_list_key = key
            continue
        open_list_key = None
        if value.startswith("[") and value.endswith("]"):
            fields[key] = _parse_inline_list(value)
        else:
            fields[key] = parse_scalar(value)
    return fields


def render_scalar(value: Any) -> str:
    """Write one plain value so that reading it back gives the same value."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return EMPTY
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValidationError("a settings value may not hold a line break", code="multiline")
    needs_quotes = (
        text == ""
        or text != text.strip()
        or text in ("true", "false")
        or bool(_INT_RE.match(text))
        or text.startswith(("[", "{", "#", '"', "'", "- "))
    )
    if needs_quotes:
        if '"' in text:
            raise ValidationError(
                "a settings value may not hold a quotation mark", code="bad-quote"
            )
        return '"%s"' % text
    return text


def render_frontmatter(fields: Dict[str, Any]) -> str:
    """Write the settings block, keeping the order the caller gave."""
    lines = [FRONTMATTER_FENCE]
    for key, value in fields.items():
        if not _KEY_RE.match(key):
            raise ValidationError(
                "the setting name %s holds characters we never allow" % key,
                code="bad-key",
            )
        if isinstance(value, (list, tuple)):
            parts = []
            for item in value:
                rendered = render_scalar(item)
                if "," in rendered or "[" in rendered or "]" in rendered:
                    raise ValidationError(
                        "a list value may not hold a comma or a bracket",
                        code="bad-list-item",
                    )
                parts.append(rendered)
            lines.append("%s: [%s]" % (key, ", ".join(parts)))
        else:
            lines.append("%s: %s" % (key, render_scalar(value)))
    lines.append(FRONTMATTER_FENCE)
    return "\n".join(lines) + "\n"


def render_document(fields: Dict[str, Any], body: str) -> str:
    """Write a whole file: the settings block, a blank line, then the body."""
    text = body if body.endswith("\n") or body == "" else body + "\n"
    return render_frontmatter(fields) + "\n" + text


# --- Small helpers the artifacts share ---------------------------------------


def _require(fields: Dict[str, Any], name: str, kind: str) -> Any:
    if name not in fields:
        raise ValidationError(
            "the %s is missing %s" % (kind, name), code="missing-field"
        )
    value = fields[name]
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError("the %s is missing %s" % (kind, name), code="missing-field")
    return value


def _reject_unknown(fields: Dict[str, Any], allowed: Tuple[str, ...], kind: str) -> None:
    for name in fields:
        if name not in allowed:
            raise ValidationError(
                "the %s carries a setting we do not know: %s" % (kind, name),
                code="unknown-field",
            )


def _as_date(value: Any, name: str, kind: str) -> datetime.date:
    text = value.isoformat() if isinstance(value, datetime.date) else str(value).strip()
    if not _DATE_RE.match(text):
        raise ValidationError(
            "the %s field %s is not a date written as year, month, day" % (kind, name),
            code="bad-date",
        )
    try:
        return datetime.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))
    except ValueError:
        raise ValidationError(
            "the %s field %s is not a real date" % (kind, name), code="bad-date"
        )


def _as_list(value: Any, name: str, kind: str) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if value in (None, "", EMPTY):
        return []
    raise ValidationError(
        "the %s field %s is not a list" % (kind, name), code="not-a-list"
    )


def _as_bool(value: Any, name: str, kind: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip() in ("true", "false"):
        return value.strip() == "true"
    raise ValidationError(
        "the %s field %s is not a yes or no value" % (kind, name), code="not-a-boolean"
    )


def _in_vocabulary(value: Any, allowed, name: str, kind: str) -> str:
    text = str(value).strip()
    if text not in allowed:
        raise ValidationError(
            "the %s field %s holds a value we do not know" % (kind, name),
            code="unknown-value",
        )
    return text


def _optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return None if text in ("", EMPTY) else text


def _fence_for(text: str) -> str:
    longest = 0
    for run in re.findall(r"`+", text or ""):
        longest = max(longest, len(run))
    return "`" * max(3, longest + 1)


def _fenced(text: str, info: str = "text") -> str:
    fence = _fence_for(text)
    body = text if text.endswith("\n") or text == "" else text + "\n"
    return "%s%s\n%s%s\n" % (fence, info, body, fence)


def _read_fenced(lines: List[str], start: int) -> Tuple[str, int]:
    """Read a fenced block starting at `start`. Return its text and the next line."""
    match = _FENCE_RE.match(lines[start])
    if match is None:
        raise ValidationError("a fenced block was expected here", code="no-fence")
    fence = match.group(1)
    collected = []
    index = start + 1
    while index < len(lines):
        if lines[index].strip() == fence:
            text = "\n".join(collected)
            return (text + "\n" if text else ""), index + 1
        collected.append(lines[index])
        index += 1
    raise ValidationError("a fenced block is never closed", code="unclosed-fence")


def split_sections(body: str, level: int = 2) -> "Dict[str, str]":
    """Split a body into its headings and the text under each one."""
    marker = "#" * level + " "
    sections: Dict[str, str] = {}
    name = None
    collected: List[str] = []
    for line in body.split("\n"):
        if line.startswith(marker):
            if name is not None:
                sections[name] = "\n".join(collected).strip("\n")
            name = line[len(marker) :].strip()
            collected = []
        elif name is not None:
            collected.append(line)
    if name is not None:
        sections[name] = "\n".join(collected).strip("\n")
    return sections


def section_order(body: str, level: int = 2) -> List[str]:
    """The headings of a body, in the order they appear."""
    marker = "#" * level + " "
    return [
        line[len(marker) :].strip()
        for line in body.split("\n")
        if line.startswith(marker)
    ]


# --- The context change entry ------------------------------------------------

# The settings an entry is written with today. A base written before the
# rename holds `decided_on` and `decided_by` instead, so both spellings of
# each are accepted when an entry is read and only these are ever written.
CHANGE_FIELDS = (
    "id",
    "kind",
    "happened_on",
    "written_on",
    "noted_by",
    "source",
    "affects",
    "review_by",
    "origin",
    "run_id",
    "status",
)
CHANGE_REQUIRED = (
    "id",
    "kind",
    "happened_on",
    "written_on",
    "noted_by",
    "source",
    "review_by",
    "origin",
    "status",
)
# Every name a reader will accept, which is the list above plus the older
# spelling of the two settings that were renamed.
CHANGE_FIELDS_READ = CHANGE_FIELDS + tuple(
    old for _new, old in constants.ENTRY_FIELD_PAIRS
)


def _same_value(one: Any, other: Any) -> bool:
    """Whether two settings values say the same thing, written either way."""
    if isinstance(one, datetime.date):
        one = one.isoformat()
    if isinstance(other, datetime.date):
        other = other.isoformat()
    return str(one).strip() == str(other).strip()


def _fold_field_names(fields: Dict[str, Any]) -> Dict[str, Any]:
    """The same settings with each older name replaced by the name in use.

    A file that gives one setting under both of its names and says two
    different things in them is refused rather than resolved. Picking one of
    the two dates somebody wrote is a statement about their business that
    nothing here is entitled to make, and the version of this that quietly
    kept one of them made exactly that statement without saying so.

    Both names saying the same thing is not a problem and is folded into one.
    """
    folded = dict(fields)
    for new, old in constants.ENTRY_FIELD_PAIRS:
        if old not in folded:
            continue
        older = folded.pop(old)
        current = folded.get(new)
        empty = current is None or (
            isinstance(current, str) and not current.strip()
        )
        if empty:
            folded[new] = older
            continue
        if not _same_value(current, older):
            raise ValidationError(
                "the context change gives %s and %s and they do not say the "
                "same thing" % (new, old),
                code="two-spellings-disagree",
            )
    return folded


# The names Unit 1.4 replaced. They are kept pointing at the new lists so a
# caller that still imports them reads the same thing.
LEDGER_FIELDS = CHANGE_FIELDS
LEDGER_REQUIRED = CHANGE_REQUIRED


class ChangeEntry(object):
    """One context change the base was told about, written down when it was.

    A context change is anything that happened that makes a document no longer
    true: something the team settled, a competitor's launch, a price change,
    something learned about how customers describe the problem.

    An entry written before the rename says `kind: decision` and carries
    `decided_on` and `decided_by`. It is read here exactly as a new one is,
    and writing always produces the new spelling.
    """

    kind = constants.ENTRY_KIND

    def __init__(
        self,
        id,
        happened_on=None,
        written_on=None,
        noted_by=None,
        source=None,
        review_by=None,
        origin=None,
        status=None,
        affects=None,
        run_id=None,
        body="",
        decided_on=None,
        decided_by=None,
    ):
        # The two settings that were renamed are accepted under either name,
        # for the same reason the parser accepts either: a caller that says
        # `decided_on` is not wrong about the change, only about what it is
        # called, and every one of them would otherwise have had to change on
        # the day the folder moved. A caller that gives both names and says
        # two different things in them is refused rather than resolved, which
        # is the same rule the parser follows.
        for new, old, given, older in (
            ("happened_on", "decided_on", happened_on, decided_on),
            ("noted_by", "decided_by", noted_by, decided_by),
        ):
            if given is None or older is None:
                continue
            if not _same_value(given, older):
                raise ValidationError(
                    "the context change gives %s and %s and they do not say "
                    "the same thing" % (new, old),
                    code="two-spellings-disagree",
                )
        if happened_on is None:
            happened_on = decided_on
        if noted_by is None:
            noted_by = decided_by
        self.id = id
        self.happened_on = happened_on
        self.written_on = written_on
        self.noted_by = noted_by
        self.source = source
        self.review_by = review_by
        self.origin = origin
        self.status = status
        self.affects = list(affects or [])
        self.run_id = run_id
        self.body = body

    # The two settings that were renamed, still readable under the name they
    # had before, because a caller reading an entry is not what this rename is
    # about and every one of them would otherwise have to change on the same
    # day the folder moved.
    @property
    def decided_on(self):
        return self.happened_on

    @decided_on.setter
    def decided_on(self, value):
        self.happened_on = value

    @property
    def decided_by(self):
        return self.noted_by

    @decided_by.setter
    def decided_by(self, value):
        self.noted_by = value

    @classmethod
    def parse(cls, text: str) -> "ChangeEntry":
        block, body = split_document(text)
        fields = _fold_field_names(parse_frontmatter(block))
        _reject_unknown(fields, CHANGE_FIELDS, "context change")
        for name in CHANGE_REQUIRED:
            _require(fields, name, "context change")
        if str(fields["kind"]).strip() not in constants.ENTRY_KINDS:
            raise ValidationError(
                "this file is not a context change", code="wrong-kind"
            )
        return cls(
            id=str(fields["id"]).strip(),
            happened_on=str(fields["happened_on"]).strip(),
            written_on=str(fields["written_on"]).strip(),
            noted_by=str(fields["noted_by"]).strip(),
            source=str(fields["source"]).strip(),
            review_by=str(fields["review_by"]).strip(),
            origin=str(fields["origin"]).strip(),
            status=str(fields["status"]).strip(),
            affects=_as_list(fields.get("affects", []), "affects", "context change"),
            run_id=_optional(fields.get("run_id")),
            body=body.strip("\n"),
        )

    def frontmatter(self) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "happened_on": self.happened_on,
            "written_on": self.written_on,
            "noted_by": self.noted_by,
            "source": self.source,
            "affects": list(self.affects),
            "review_by": self.review_by,
            "origin": self.origin,
        }
        if self.run_id:
            fields["run_id"] = self.run_id
        fields["status"] = self.status
        return fields

    def frontmatter_block(self) -> str:
        """The settings block on its own, which a proposal carries verbatim."""
        return render_frontmatter(self.frontmatter())

    def render(self) -> str:
        return render_document(self.frontmatter(), self.body)

    def validate(self, today: Optional[datetime.date] = None) -> "ChangeEntry":
        """Check every field, and the three rules the dates have to obey.

        The codes below are older than the rename and are left as they are.
        Nothing shows one to a person, and every seat's own records already
        hold them, so changing them would only make old records unreadable.
        """
        check_staging_id(self.id)
        # A value that is not there at all is a missing setting, not a crash.
        # It used to die on an attribute here, and the step that reads a base
        # catches a refusal and not that, so one entry took the whole check
        # down with it.
        for name in CHANGE_REQUIRED:
            if name == "kind":
                continue
            if getattr(self, name, None) is None:
                raise ValidationError(
                    "the context change is missing %s" % name,
                    code="missing-field",
                )
        if not self.noted_by.strip():
            raise ValidationError(
                "the context change does not say who noted it",
                code="missing-field",
            )
        if not self.source.strip():
            raise ValidationError(
                "the context change is missing source", code="missing-field"
            )
        happened = _as_date(self.happened_on, "happened_on", "context change")
        written = _as_date(self.written_on, "written_on", "context change")
        review = _as_date(self.review_by, "review_by", "context change")
        day = today or datetime.date.today()
        if happened > day:
            raise ValidationError(
                "the context change says it happened in the future",
                code="decided-in-future",
            )
        if review < happened:
            raise ValidationError(
                "the context change asks to look at it again before it happened",
                code="review-before-decision",
            )
        if written < happened:
            raise ValidationError(
                "the context change says it was written down before it happened",
                code="written-before-decision",
            )
        _in_vocabulary(
            self.origin, constants.LEDGER_ORIGINS, "origin", "context change"
        )
        _in_vocabulary(
            self.status, constants.LEDGER_STATUSES, "status", "context change"
        )
        if self.run_id is not None:
            check_run_id(self.run_id)
        for path in self.affects:
            check_context_path_syntax(path)
        if not self.body.strip():
            raise ValidationError(
                "the context change does not say what changed", code="missing-body"
            )
        return self


# The name this class had before Unit 1.4. It is kept so that nothing that
# reads an entry had to change on the day the folder moved.
LedgerEntry = ChangeEntry


# The mark some editors put at the very start of a file. It is invisible, it
# is not whitespace, and a scan that does not expect it reads the first fence
# as part of the body.
BYTE_ORDER_MARK = "\ufeff"


def _value_of(raw: str) -> str:
    """One settings value as it is meant, with any quotation marks taken off."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def rewrite_entry_keys(text: str) -> str:
    """One entry's own bytes with only its renamed settings changed.

    Written as a line-level rename rather than as a parse and a re-render,
    because a re-render is a rewrite of the whole file: it turns every line
    ending into the one this library happens to use, folds runs of blank
    lines, requotes values, and puts the settings back in its own order. None
    of that is the rename, and all of it is the person's own file being
    changed underneath them.

    Three things change and nothing else. The two renamed setting names, each
    at the start of its own line inside the settings block. The value of
    `kind`, when it is the word this rename replaces, quoted or not. And a
    line giving one setting under its older name when the same setting is
    already there under its newer name saying the same thing, which is taken
    away, because leaving both would put the same name on two lines and make
    a file nothing can read.

    Nothing here is trusted to have worked. `rewritten_safely` below reads the
    answer back and refuses unless it says exactly what the file said.
    """
    if not isinstance(text, str):
        raise ValidationError("this file is not text", code="not-text")
    block, _body = split_document(text)
    fields = parse_frontmatter(block)
    # A setting given under both names is folded into one here, and this is
    # what refuses the two of them disagreeing, so the rename below can never
    # quietly keep one of two different answers.
    _fold_field_names(fields)

    mark = BYTE_ORDER_MARK if text.startswith(BYTE_ORDER_MARK) else ""
    body = text[len(mark) :]
    lines = body.split("\n")
    fences = [
        number
        for number, line in enumerate(lines)
        if line.strip() == FRONTMATTER_FENCE
    ]
    if len(fences) < 2:
        raise ValidationError(
            "the settings block at the top of this file is never closed",
            code="unclosed-frontmatter",
        )
    start, stop = fences[0], fences[1]
    renames = dict((old, new) for new, old in constants.ENTRY_FIELD_PAIRS)
    kept = []
    for number, line in enumerate(lines):
        if not (start < number < stop):
            kept.append(line)
            continue
        name, separator, value = line.partition(":")
        if not separator:
            kept.append(line)
            continue
        plain = name.strip()
        if plain in renames:
            newer = renames[plain]
            if newer in fields and newer in parse_frontmatter(block):
                # The newer name is already on a line of its own, and the two
                # agree, or the fold above would have refused. One of the two
                # lines has to go, and it is the older one.
                continue
            kept.append(name.replace(plain, renames[plain], 1) + ":" + value)
            continue
        if plain == "kind" and _value_of(value) == constants.LEGACY_ENTRY_KIND:
            kept.append(
                name
                + ":"
                + value.replace(
                    constants.LEGACY_ENTRY_KIND, constants.ENTRY_KIND, 1
                )
            )
            continue
        kept.append(line)
    return mark + "\n".join(kept)


# What the rewrite refuses with, each of them a file it will not touch.
CODE_REWRITE_CHANGES_IT = "the-rename-would-change-what-it-says"
CODE_REWRITE_LEAVES_OLDER = "the-rename-left-the-older-words-behind"


def entry_values(entry) -> tuple:
    """Everything one context change says, as plain values.

    It is the one definition, used to compare two copies of a change and to
    check that a rename changed nothing but the names.
    """
    return (
        entry.id,
        str(entry.happened_on),
        str(entry.written_on),
        str(entry.noted_by),
        str(entry.source),
        str(entry.review_by),
        str(entry.origin),
        str(entry.status),
        str(entry.run_id or ""),
        tuple(str(path) for path in entry.affects),
        entry.body,
    )


def rewritten_safely(text: str) -> str:
    """The entry renamed, read back, and refused unless it says the same thing.

    This is the invariant the whole move rests on: nothing is ever written to
    a base in a form the reader cannot read back to exactly the values it read
    before. A rename that produces something unreadable, something that says
    anything different, or something still carrying the older words is a
    refusal here, where nothing has been written yet, rather than a saved file
    somebody finds out about later.
    """
    before = ChangeEntry.parse(text)
    written = rewrite_entry_keys(text)
    after = ChangeEntry.parse(written)
    if entry_values(before) != entry_values(after):
        raise ValidationError(
            "renaming the settings in this file would change what it says",
            code=CODE_REWRITE_CHANGES_IT,
        )
    block, _body = split_document(written)
    fields = parse_frontmatter(block)
    older = [old for _new, old in constants.ENTRY_FIELD_PAIRS if old in fields]
    if older or _value_of(str(fields.get("kind", ""))) != constants.ENTRY_KIND:
        raise ValidationError(
            "renaming the settings in this file would leave the older words "
            "behind",
            code=CODE_REWRITE_LEAVES_OLDER,
        )
    # Doing it twice has to give the same answer, or the file is one this
    # cannot be run on again safely.
    if rewrite_entry_keys(written) != written:
        raise ValidationError(
            "renaming the settings in this file does not settle",
            code=CODE_REWRITE_CHANGES_IT,
        )
    return written


# --- The confirmation line ---------------------------------------------------

CONFIRMATION_TOKENS = ("date", "time", "file", "trigger", "entry", "question", "run")


class ConfirmationLine(object):
    """One line saying an owner confirmed one file on one day."""

    def __init__(self, date, time, file, trigger, entry=None, question=None, run=None):
        self.date = date
        self.time = time
        self.file = file
        self.trigger = trigger
        self.entry = entry
        self.question = question
        self.run = run

    def values(self) -> Dict[str, str]:
        return {
            "date": self.date,
            "time": self.time,
            "file": self.file,
            "trigger": self.trigger,
            "entry": self.entry or EMPTY,
            "question": self.question or EMPTY,
            "run": self.run or EMPTY,
        }

    def render(self) -> str:
        values = self.values()
        for name, value in values.items():
            if not value or " " in str(value):
                raise ValidationError(
                    "the confirmation value for %s is empty or holds a space" % name,
                    code="bad-token",
                )
        return " ".join("%s=%s" % (name, values[name]) for name in CONFIRMATION_TOKENS)

    @classmethod
    def parse(cls, line: str) -> "ConfirmationLine":
        """Read one confirmation line, or say which rule it broke."""
        if not isinstance(line, str):
            raise ValidationError("this line is not text", code="not-text")
        parts = line.strip().split(" ")
        parts = [part for part in parts if part]
        if len(parts) != len(CONFIRMATION_TOKENS):
            raise ValidationError(
                "a confirmation line carries exactly %d values"
                % len(CONFIRMATION_TOKENS),
                code="wrong-token-count",
            )
        values = {}
        for expected, part in zip(CONFIRMATION_TOKENS, parts):
            name, separator, value = part.partition("=")
            if not separator or name != expected:
                raise ValidationError(
                    "a confirmation line names %s in position %d"
                    % (expected, CONFIRMATION_TOKENS.index(expected) + 1),
                    code="wrong-token-order",
                )
            values[name] = value
        entry = cls(
            date=values["date"],
            time=values["time"],
            file=values["file"],
            trigger=values["trigger"],
            entry=_optional(values["entry"]),
            question=_optional(values["question"]),
            run=_optional(values["run"]),
        )
        entry.validate()
        return entry

    def validate(self) -> "ConfirmationLine":
        if not _DATE_RE.match(str(self.date)):
            raise ValidationError(
                "the confirmation date is not a date", code="bad-date"
            )
        _as_date(self.date, "date", "confirmation line")
        if not _TIME_RE.match(str(self.time)):
            raise ValidationError(
                "the confirmation time is not a time in the standard form",
                code="bad-time",
            )
        check_context_path_syntax(self.file)
        _in_vocabulary(
            self.trigger, constants.CONFIRMATION_TRIGGERS, "trigger", "confirmation line"
        )
        if self.entry is not None:
            check_staging_id(self.entry)
        if self.question is not None and not re.match(r"^q-[0-9a-f]{20}$", self.question):
            raise ValidationError(
                "the confirmation question id is not one we issued", code="bad-question-id"
            )
        if self.run is not None:
            check_run_id(self.run)
        if self.trigger == "drafted" and self.run is None:
            raise ValidationError(
                "a drafted confirmation has to name the run that drafted it",
                code="drafted-without-run",
            )
        if self.trigger == "ledger" and self.entry is None:
            raise ValidationError(
                "a confirmation about a decision has to name the decision",
                code="ledger-without-entry",
            )
        return self


class MalformedLine(object):
    """A line of a confirmations file that could not be read."""

    __slots__ = ("number", "code", "message")

    def __init__(self, number: int, code: str, message: str):
        self.number = number
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return "MalformedLine(number=%r, code=%r)" % (self.number, self.code)


def parse_confirmations_file(
    text: str,
) -> Tuple[List[ConfirmationLine], List[MalformedLine]]:
    """Read a confirmations file, reporting bad lines instead of stopping.

    One unreadable line must never hide the confirmations around it, so the
    bad lines come back as a list the caller can report.
    """
    good: List[ConfirmationLine] = []
    bad: List[MalformedLine] = []
    for number, raw in enumerate((text or "").split("\n"), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            good.append(ConfirmationLine.parse(line))
        except (ValidationError, PathError) as failure:
            bad.append(MalformedLine(number, failure.code, str(failure)))
    return good, bad


def render_confirmations_file(lines: List[ConfirmationLine], header: str = "") -> str:
    """Write a whole confirmations file, header comments included."""
    parts = []
    if header:
        for line in header.strip().split("\n"):
            parts.append("# " + line if not line.startswith("#") else line)
    parts.extend(line.render() for line in lines)
    return "\n".join(parts) + "\n"


# --- The corrections file ----------------------------------------------------

CORRECTIONS_FIELDS = (
    "kind",
    "date",
    "staging_id",
    "entry_id",
    "source_id",
    "intake_path",
    "mode",
    "third_party",
    "content_hash",
    "touched_paths",
    "correction_class",
    "marker",
)

WHAT_CHANGED = "What changed"
WHY = "Why"


class CorrectionsFile(object):
    """What one run found wrong, and which rule changed because of it."""

    def __init__(
        self,
        kind,
        date,
        staging_id,
        intake_path,
        mode,
        third_party,
        content_hash,
        correction_class,
        marker,
        entry_id=None,
        source_id=None,
        touched_paths=None,
        what_changed="",
        why="",
    ):
        self.kind = kind
        self.date = date
        self.staging_id = staging_id
        self.entry_id = entry_id
        self.source_id = source_id
        self.intake_path = intake_path
        self.mode = mode
        self.third_party = third_party
        self.content_hash = content_hash
        self.touched_paths = list(touched_paths or [])
        self.correction_class = correction_class
        self.marker = marker
        self.what_changed = what_changed
        self.why = why

    @classmethod
    def parse(cls, text: str) -> "CorrectionsFile":
        block, body = split_document(text)
        fields = parse_frontmatter(block)
        _reject_unknown(fields, CORRECTIONS_FIELDS, "corrections file")
        for name in (
            "kind",
            "date",
            "staging_id",
            "intake_path",
            "mode",
            "content_hash",
            "correction_class",
            "marker",
        ):
            _require(fields, name, "corrections file")
        if "third_party" not in fields:
            raise ValidationError(
                "the corrections file is missing third_party", code="missing-field"
            )
        sections = split_sections(body)
        return cls(
            kind=str(fields["kind"]).strip(),
            date=str(fields["date"]).strip(),
            staging_id=str(fields["staging_id"]).strip(),
            entry_id=_optional(fields.get("entry_id")),
            source_id=_optional(fields.get("source_id")),
            intake_path=str(fields["intake_path"]).strip(),
            mode=str(fields["mode"]).strip(),
            third_party=_as_bool(
                fields["third_party"], "third_party", "corrections file"
            ),
            content_hash=str(fields["content_hash"]).strip(),
            touched_paths=_as_list(
                fields.get("touched_paths", []), "touched_paths", "corrections file"
            ),
            correction_class=str(fields["correction_class"]).strip(),
            marker=str(fields["marker"]).strip(),
            what_changed=sections.get(WHAT_CHANGED, ""),
            why=sections.get(WHY, ""),
        )

    def frontmatter(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "date": self.date,
            "staging_id": self.staging_id,
            "entry_id": self.entry_id or EMPTY,
            "source_id": self.source_id or EMPTY,
            "intake_path": self.intake_path,
            "mode": self.mode,
            "third_party": bool(self.third_party),
            "content_hash": self.content_hash,
            "touched_paths": list(self.touched_paths),
            "correction_class": self.correction_class,
            "marker": self.marker,
        }

    def render(self) -> str:
        body = "## %s\n\n%s\n\n## %s\n\n%s\n" % (
            WHAT_CHANGED,
            self.what_changed.strip("\n"),
            WHY,
            self.why.strip("\n"),
        )
        return render_document(self.frontmatter(), body)

    def validate(self) -> "CorrectionsFile":
        _in_vocabulary(self.kind, constants.CORRECTION_KINDS, "kind", "corrections file")
        _as_date(self.date, "date", "corrections file")
        check_staging_id(self.staging_id)
        if self.entry_id is not None:
            check_staging_id(self.entry_id)
        if self.source_id is not None:
            check_source_id(self.source_id)
        _in_vocabulary(
            self.intake_path, constants.INTAKE_PATHS, "intake_path", "corrections file"
        )
        _in_vocabulary(self.mode, constants.ANALYSIS_MODES, "mode", "corrections file")
        if not isinstance(self.third_party, bool):
            raise ValidationError(
                "the corrections file field third_party is not a yes or no value",
                code="not-a-boolean",
            )
        check_content_hash(self.content_hash)
        _in_vocabulary(
            self.correction_class,
            constants.CORRECTION_CLASSES,
            "correction_class",
            "corrections file",
        )
        for path in self.touched_paths:
            check_repo_path_syntax(path, PROPOSAL_PATH_PREFIXES)
        if "<!--" in self.marker or "-->" in self.marker:
            raise ValidationError(
                "the marker is written as a hidden comment, and hidden content is refused",
                code="hidden-marker",
            )
        parsed = parse_marker_line(self.marker)
        if parsed is None:
            raise ValidationError("the marker line cannot be read", code="bad-marker")
        staging, entry, source = parsed
        if staging != self.staging_id:
            raise ValidationError(
                "the marker names a different proposal", code="marker-mismatch"
            )
        if entry != self.entry_id or source != self.source_id:
            raise ValidationError(
                "the marker names a different context change or source",
                code="marker-mismatch",
            )
        if not self.what_changed.strip():
            raise ValidationError(
                "the corrections file is missing What changed", code="missing-section"
            )
        if not self.why.strip():
            raise ValidationError(
                "the corrections file is missing Why", code="missing-section"
            )
        return self


# --- The pending file the analysis step writes -------------------------------

PENDING_FIELDS = (
    "source_id",
    "item_path",
    "mode",
    "rule_change",
    "decision",
    "edits",
    "raw_span",
    "redacted_excerpt",
    "confidence",
)
EDIT_FIELDS = ("path", "heading", "op", "text")


class Edit(object):
    """One change to one section of one context file."""

    __slots__ = ("path", "heading", "op", "text")

    def __init__(self, path: str, heading: str, op: str, text: str):
        self.path = path
        self.heading = heading
        self.op = op
        self.text = text

    def as_dict(self) -> Dict[str, str]:
        return {
            "path": self.path,
            "heading": self.heading,
            "op": self.op,
            "text": self.text,
        }

    def validate(self) -> "Edit":
        check_context_path_syntax(self.path)
        _in_vocabulary(self.op, constants.EDIT_OPERATIONS, "op", "edit")
        if not isinstance(self.heading, str) or "\n" in self.heading:
            raise ValidationError("an edit heading is one line", code="bad-heading")
        if not isinstance(self.text, str):
            raise ValidationError("an edit carries text", code="bad-edit-text")
        return self


class PendingItem(object):
    """What the analysis step proposes for one inbox item, before any check."""

    def __init__(
        self,
        source_id,
        item_path,
        mode,
        rule_change,
        decision,
        edits,
        raw_span,
        redacted_excerpt,
        confidence,
    ):
        self.source_id = source_id
        self.item_path = item_path
        self.mode = mode
        self.rule_change = rule_change
        self.decision = decision
        self.edits = edits
        self.raw_span = raw_span
        self.redacted_excerpt = redacted_excerpt
        self.confidence = confidence

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "item_path": self.item_path,
            "mode": self.mode,
            "rule_change": self.rule_change,
            "decision": self.decision,
            "edits": [edit.as_dict() for edit in self.edits],
            "raw_span": self.raw_span,
            "redacted_excerpt": self.redacted_excerpt,
            "confidence": self.confidence,
        }


def parse_pending(payload: Any) -> PendingItem:
    """Read the pending file's shape, refusing anything it does not name."""
    if not isinstance(payload, dict):
        raise ValidationError("the pending file is not a record", code="not-a-record")
    for name in payload:
        if name not in PENDING_FIELDS:
            raise ValidationError(
                "the pending file carries a field we do not know: %s" % name,
                code="unknown-field",
            )
    for name in PENDING_FIELDS:
        if name not in payload:
            raise ValidationError(
                "the pending file is missing %s" % name, code="missing-field"
            )
    check_source_id(payload["source_id"])
    if not isinstance(payload["item_path"], str) or not payload["item_path"]:
        raise ValidationError("the pending file names no inbox item", code="missing-field")
    check_repo_path_syntax(payload["item_path"], (constants.INBOX_DIR + "/",))
    _in_vocabulary(payload["mode"], constants.ANALYSIS_MODES, "mode", "pending file")
    if not isinstance(payload["rule_change"], bool):
        raise ValidationError(
            "the pending file field rule_change is not a yes or no value",
            code="not-a-boolean",
        )
    _in_vocabulary(
        payload["confidence"], constants.CONFIDENCE_LEVELS, "confidence", "pending file"
    )
    decision = payload["decision"]
    if decision is not None and not isinstance(decision, dict):
        raise ValidationError(
            "the pending file's decision is neither a record nor empty",
            code="bad-decision",
        )
    raw_span = payload["raw_span"]
    excerpt = payload["redacted_excerpt"]
    for name, value, cap in (
        ("raw_span", raw_span, constants.MAX_RAW_SPAN_CHARS),
        ("redacted_excerpt", excerpt, constants.MAX_EXCERPT_CHARS),
    ):
        if not isinstance(value, str):
            raise ValidationError(
                "the pending file field %s is not text" % name, code="not-text"
            )
        if len(value) > cap:
            raise ValidationError(
                "the pending file field %s is longer than we allow" % name,
                code="too-long",
            )
    raw_edits = payload["edits"]
    if not isinstance(raw_edits, list):
        raise ValidationError("the pending file's edits are not a list", code="not-a-list")
    edits = []
    for item in raw_edits:
        if not isinstance(item, dict):
            raise ValidationError("an edit is not a record", code="not-a-record")
        for name in item:
            if name not in EDIT_FIELDS:
                raise ValidationError(
                    "an edit carries a field we do not know: %s" % name,
                    code="unknown-field",
                )
        for name in EDIT_FIELDS:
            if name not in item:
                raise ValidationError(
                    "an edit is missing %s" % name, code="missing-field"
                )
        edits.append(
            Edit(item["path"], item["heading"], item["op"], item["text"]).validate()
        )
    return PendingItem(
        source_id=payload["source_id"],
        item_path=payload["item_path"],
        mode=payload["mode"],
        rule_change=payload["rule_change"],
        decision=decision,
        edits=edits,
        raw_span=raw_span,
        redacted_excerpt=excerpt,
        confidence=payload["confidence"],
    )


def load_pending(path: str) -> PendingItem:
    """Read a pending file from disk, with a size limit and no surprises."""
    try:
        size = os.path.getsize(path)
    except OSError:
        raise ValidationError("the pending file is not there", code="missing-file")
    if size > constants.MAX_PENDING_ITEM_BYTES:
        raise ValidationError("the pending file is too large", code="too-large")
    with open(path, encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except ValueError:
            raise ValidationError("the pending file cannot be read", code="malformed")
    return parse_pending(payload)


# --- The pull request body ---------------------------------------------------

PR_SECTIONS = (
    "What changed",
    "Why",
    "Evidence",
    "Confidence",
    "Rule being changed",
    "About this proposal",
)
ABOUT_SENTENCE = (
    "This proposal was drafted by an AI assistant from the evidence above and "
    "has not been reviewed by a person yet."
)
KEEP_THE_CHANGE_HINT = (
    "If the context change is right but the edit is wrong, say keep the change "
    "and drop the edit."
)
# The name this sentence had before Unit 1.4, kept so nothing that imports it
# breaks. Its words are the ones above.
KEEP_THE_DECISION_HINT = KEEP_THE_CHANGE_HINT
# The words it had before Unit 1.4. Nothing writes them any more, and a
# proposal raised before the rename still carries them, so they are read.
LEGACY_KEEP_HINT = (
    "If the decision is right but the edit is wrong, say keep the decision and "
    "drop the edit."
)
PR_FIELDS = ("before", "after", "why", "evidence", "confidence", "rule_changed", "marker")


def render_pr_body(fields: Dict[str, Any]) -> str:
    """Write the one document a reviewer reads, in the one order it has."""
    for name in ("before", "after", "why", "evidence", "confidence", "marker"):
        value = fields.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                "the proposal body is missing %s" % name, code="missing-field"
            )
    _in_vocabulary(
        fields["confidence"], constants.CONFIDENCE_LEVELS, "confidence", "proposal body"
    )
    marker = fields["marker"].strip()
    if parse_marker_line(marker) is None:
        raise ValidationError("the marker line cannot be read", code="bad-marker")
    rule = fields.get("rule_changed") or "None"
    return (
        "## What changed\n\n"
        "Before: %s\n\n"
        "After: %s\n\n"
        "## Why\n\n%s\n\n"
        "## Evidence\n\n%s\n\n"
        "## Confidence\n\n%s\n\n"
        "## Rule being changed\n\n%s\n\n"
        "## About this proposal\n\n%s\n\n%s\n\n%s\n"
        % (
            fields["before"].strip(),
            fields["after"].strip(),
            fields["why"].strip(),
            fields["evidence"].strip(),
            fields["confidence"].strip(),
            str(rule).strip(),
            ABOUT_SENTENCE,
            KEEP_THE_CHANGE_HINT,
            marker,
        )
    )


def required_sections_present(text: str) -> Tuple[bool, List[str]]:
    """Whether every required heading is there, in the order it has to be in."""
    found = [name for name in section_order(text) if name in PR_SECTIONS]
    missing = [name for name in PR_SECTIONS if name not in found]
    if missing:
        return False, missing
    if found != list(PR_SECTIONS):
        return False, ["out-of-order"]
    return True, []


def parse_pr_body(text: str) -> Dict[str, Any]:
    """Read a proposal body back into the fields it was written from."""
    present, missing = required_sections_present(text)
    if not present:
        raise ValidationError(
            "the proposal body is missing or misorders: %s" % ", ".join(missing),
            code="missing-section",
        )
    sections = split_sections(text)
    changed = sections["What changed"]
    before = None
    after = None
    for paragraph in changed.split("\n\n"):
        stripped = paragraph.strip()
        if stripped.startswith("Before:"):
            before = stripped[len("Before:") :].strip()
        elif stripped.startswith("After:"):
            after = stripped[len("After:") :].strip()
    if not before or not after:
        raise ValidationError(
            "What changed has to say what it was before and what it is after",
            code="missing-before-after",
        )
    about = sections["About this proposal"]
    if ABOUT_SENTENCE not in about:
        raise ValidationError(
            "the proposal body does not say that an assistant drafted it",
            code="missing-about-sentence",
        )
    # A proposal raised before the rename carries the older sentence. It is
    # still a proposal somebody is waiting on, so it is read as it is written.
    if KEEP_THE_CHANGE_HINT not in about and LEGACY_KEEP_HINT not in about:
        raise ValidationError(
            "the proposal body does not say how to keep the change and drop the edit",
            code="missing-hint",
        )
    lines = [line for line in text.strip().split("\n") if line.strip()]
    marker = lines[-1].strip() if lines else ""
    if parse_marker_line(marker) is None:
        raise ValidationError(
            "the last line of the proposal body is not the marker", code="bad-marker"
        )
    return {
        "before": before,
        "after": after,
        "why": sections["Why"].strip(),
        "evidence": sections["Evidence"].strip(),
        "confidence": sections["Confidence"].strip(),
        "rule_changed": sections["Rule being changed"].strip(),
        "marker": marker,
    }


# --- The proposal staging file -----------------------------------------------

STAGING_FIELDS = (
    "schema",
    "staging_id",
    "origin",
    "source_id",
    "intake_path",
    "target_paths",
    "sequence",
    "rule_change",
    "confidence",
    "third_party",
    "first_draft",
)
STAGING_SCHEMA = 1

# The heading the entry a proposal carries sits under. A proposal staged
# before the rename says "Decision" instead, and both are read so that a
# proposal already waiting is not thrown away by the rename.
CHANGE_SECTION = "Context change"
LEGACY_CHANGE_SECTION = "Decision"
CHANGE_SECTIONS = (CHANGE_SECTION, LEGACY_CHANGE_SECTION)
# The name this had before Unit 1.4, kept so nothing that imports it breaks.
DECISION_SECTION = CHANGE_SECTION
EDITS_SECTION = "Edits"
EXCERPT_SECTION = "Excerpt"


class ProposalStaging(object):
    """One staged proposal: what it changes, why, and the body a reviewer reads.

    The edits are in the body rather than the settings block, because an edit
    carries whole paragraphs of text and the settings block never nests.
    """

    def __init__(
        self,
        staging_id,
        origin,
        intake_path,
        target_paths,
        sequence,
        rule_change,
        confidence,
        third_party,
        pr_body,
        source_id=None,
        decision_block=None,
        edits=None,
        excerpt="",
        schema=STAGING_SCHEMA,
        first_draft=False,
    ):
        self.schema = schema
        self.staging_id = staging_id
        self.origin = origin
        self.source_id = source_id
        self.intake_path = intake_path
        self.target_paths = list(target_paths or [])
        self.sequence = sequence
        self.rule_change = rule_change
        self.confidence = confidence
        self.third_party = third_party
        self.decision_block = decision_block
        self.edits = list(edits or [])
        self.excerpt = excerpt
        self.pr_body = pr_body
        # Whether the words in the edits are still the note GTM Base wrote
        # asking for the real wording. Findings V8 and N4 of the 2026-09-20
        # verification round: this used to be worked out by reading the words,
        # and every small retyping of them got past that, so it is written
        # down by whoever put the note there instead. Nothing at all is kept
        # as nothing at all, because a file written before this setting
        # existed says nothing rather than saying no (finding M1).
        self.first_draft = first_draft if first_draft is None else bool(first_draft)

    def frontmatter(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "staging_id": self.staging_id,
            "origin": self.origin,
            "source_id": self.source_id or EMPTY,
            "intake_path": self.intake_path,
            "target_paths": list(self.target_paths),
            "sequence": self.sequence,
            "rule_change": bool(self.rule_change),
            "confidence": self.confidence,
            "third_party": bool(self.third_party),
            "first_draft": bool(self.first_draft),
        }

    def render(self) -> str:
        parts = []
        if self.decision_block:
            parts.append("## %s\n\n%s" % (CHANGE_SECTION, _fenced(self.decision_block)))
        parts.append("## %s\n" % EDITS_SECTION)
        for number, edit in enumerate(self.edits, start=1):
            parts.append(
                "### Edit %d\n\npath: %s\nheading: %s\nop: %s\n\n%s"
                % (
                    number,
                    edit.path,
                    edit.heading if edit.heading else EMPTY,
                    edit.op,
                    _fenced(edit.text),
                )
            )
        parts.append("## %s\n\n%s" % (EXCERPT_SECTION, _fenced(self.excerpt)))
        parts.append(self.pr_body)
        body = "\n".join(parts)
        return render_document(self.frontmatter(), body)

    @classmethod
    def parse(cls, text: str) -> "ProposalStaging":
        block, body = split_document(text)
        fields = parse_frontmatter(block)
        _reject_unknown(fields, STAGING_FIELDS, "proposal")
        for name in (
            "schema",
            "staging_id",
            "origin",
            "intake_path",
            "sequence",
            "confidence",
        ):
            _require(fields, name, "proposal")
        sections = split_sections(body)
        decision_block = None
        for heading in CHANGE_SECTIONS:
            if heading not in sections:
                continue
            carried = sections[heading].strip("\n")
            if carried:
                decision_block, _ = _read_fenced(carried.split("\n"), 0)
                break
        excerpt = ""
        if EXCERPT_SECTION in sections:
            excerpt_text = sections[EXCERPT_SECTION].strip("\n")
            if excerpt_text:
                excerpt, _ = _read_fenced(excerpt_text.split("\n"), 0)
        edits = cls._parse_edits(sections.get(EDITS_SECTION, ""))
        pr_start = body.find("## " + PR_SECTIONS[0])
        if pr_start < 0:
            raise ValidationError(
                "the proposal carries no body for a reviewer to read",
                code="missing-section",
            )
        pr_body = body[pr_start:].strip("\n") + "\n"
        return cls(
            schema=fields["schema"],
            staging_id=str(fields["staging_id"]).strip(),
            origin=str(fields["origin"]).strip(),
            source_id=_optional(fields.get("source_id")),
            intake_path=str(fields["intake_path"]).strip(),
            target_paths=_as_list(
                fields.get("target_paths", []), "target_paths", "proposal"
            ),
            sequence=fields["sequence"],
            rule_change=_as_bool(
                fields.get("rule_change", False), "rule_change", "proposal"
            ),
            confidence=str(fields["confidence"]).strip(),
            third_party=_as_bool(
                fields.get("third_party", False), "third_party", "proposal"
            ),
            first_draft=(
                _as_bool(fields["first_draft"], "first_draft", "proposal")
                if "first_draft" in fields
                else None
            ),
            decision_block=decision_block,
            edits=edits,
            excerpt=excerpt,
            pr_body=pr_body,
        )

    @staticmethod
    def _parse_edits(section: str) -> List[Edit]:
        if not section.strip():
            return []
        edits: List[Edit] = []
        current: Optional[Dict[str, Any]] = None
        lines = section.split("\n")
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.startswith("### Edit"):
                current = {"path": None, "heading": None, "op": None, "text": None}
                edits.append(current)  # type: ignore[arg-type]
                index += 1
                continue
            if current is None:
                index += 1
                continue
            for name in ("path", "heading", "op"):
                prefix = name + ":"
                if line.startswith(prefix):
                    current[name] = line[len(prefix) :].strip()
                    break
            else:
                if _FENCE_RE.match(line):
                    current["text"], index = _read_fenced(lines, index)
                    continue
            index += 1
        built = []
        for raw in edits:
            if raw["path"] is None or raw["op"] is None or raw["text"] is None:
                raise ValidationError(
                    "an edit in this proposal is missing its path, its change, or its text",
                    code="missing-field",
                )
            heading = raw["heading"] or ""
            built.append(
                Edit(
                    raw["path"],
                    "" if heading == EMPTY else heading,
                    raw["op"],
                    raw["text"],
                )
            )
        return built

    def validate(self) -> "ProposalStaging":
        if self.schema != STAGING_SCHEMA:
            raise ValidationError(
                "this proposal was written by a different version", code="wrong-schema"
            )
        check_staging_id(self.staging_id)
        _in_vocabulary(self.origin, constants.LEDGER_ORIGINS, "origin", "proposal")
        if self.source_id is not None:
            check_source_id(self.source_id)
        _in_vocabulary(
            self.intake_path, constants.INTAKE_PATHS, "intake_path", "proposal"
        )
        _in_vocabulary(
            self.confidence, constants.CONFIDENCE_LEVELS, "confidence", "proposal"
        )
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool):
            raise ValidationError(
                "the proposal's sequence is not a whole number", code="bad-sequence"
            )
        for path in self.target_paths:
            check_context_path_syntax(path)
        for edit in self.edits:
            edit.validate()
        if len(self.excerpt) > constants.MAX_EXCERPT_CHARS:
            raise ValidationError(
                "the excerpt is longer than we allow", code="too-long"
            )
        if self.decision_block:
            block, _ = split_document(self.decision_block)
            parse_frontmatter(block)
        parse_pr_body(self.pr_body)
        return self


# --- The inbox item ----------------------------------------------------------

INBOX_FIELDS = (
    "source_id",
    "title",
    "date",
    "participants",
    "source",
    "visibility",
    "intake_path",
    "partial",
    "derived_from",
)


class InboxItem(object):
    """One transcript or note waiting to be read.

    The settings block names where it came from and who was in the room. The
    body is the text itself, and it never leaves this seat: only a redacted
    excerpt of it ever reaches a proposal.
    """

    def __init__(
        self,
        source_id,
        title,
        date,
        source,
        intake_path,
        participants=None,
        visibility=None,
        partial=False,
        derived_from=None,
        body="",
    ):
        self.source_id = source_id
        self.title = title
        self.date = date
        self.source = source
        self.intake_path = intake_path
        self.participants = list(participants or [])
        self.visibility = visibility
        self.partial = partial
        self.derived_from = derived_from
        self.body = body

    @classmethod
    def parse(cls, text: str) -> "InboxItem":
        block, body = split_document(text)
        fields = parse_frontmatter(block)
        _reject_unknown(fields, INBOX_FIELDS, "inbox item")
        for name in ("source_id", "title", "date", "source", "intake_path"):
            _require(fields, name, "inbox item")
        return cls(
            source_id=str(fields["source_id"]).strip(),
            title=str(fields["title"]).strip(),
            date=str(fields["date"]).strip(),
            source=str(fields["source"]).strip(),
            intake_path=str(fields["intake_path"]).strip(),
            participants=_as_list(
                fields.get("participants", []), "participants", "inbox item"
            ),
            visibility=_optional(fields.get("visibility")),
            partial=_as_bool(fields.get("partial", False), "partial", "inbox item"),
            derived_from=_optional(fields.get("derived_from")),
            body=body.strip("\n"),
        )

    def frontmatter(self) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "source_id": self.source_id,
            "title": self.title,
            "date": self.date,
            "participants": list(self.participants),
            "source": self.source,
            "visibility": self.visibility or EMPTY,
            "intake_path": self.intake_path,
            "partial": bool(self.partial),
        }
        if self.derived_from:
            fields["derived_from"] = self.derived_from
        return fields

    def render(self) -> str:
        return render_document(self.frontmatter(), self.body)

    def validate(self) -> "InboxItem":
        check_source_id(self.source_id)
        _as_date(self.date, "date", "inbox item")
        if self.visibility is not None:
            _in_vocabulary(
                self.visibility,
                constants.INBOX_VISIBILITIES,
                "visibility",
                "inbox item",
            )
        _in_vocabulary(
            self.intake_path, constants.INBOX_INTAKE_PATHS, "intake_path", "inbox item"
        )
        if self.derived_from is not None:
            check_source_id(self.derived_from)
        return self
