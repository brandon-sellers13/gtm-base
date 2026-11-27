"""The source map's rows: where each kind of data lives, and what reads it.

Unit 2.5a of Plan 1 (requirement P31). The source map (`access/stack.md`)
holds one table under its "Where the material lives" heading, one row for
each kind of data a job needs, in five columns: the kind of data, the business
it is for (or the whole company), where it lives, which connected tool reads
it, and what to do when that tool is not connected. This module reads that
table into rows a skill can use, and says what is wrong with any row it could
not take.

It reads one file and the map beside it, and does nothing else. It never
runs a program and never reaches anything off this computer, so the rows say
where data lives and reading them never goes there; a skill's own procedure
calls its tools. A row naming a tool this seat has not connected is still a
good row, because the file is the team's record, not this seat's.

Every line of the file below its settings block goes through the screens a
prepared change goes through before it is raised, and the source map's own
check for an address carrying a password. A line holding anything shaped like
a key, a token or a contact detail is refused, and the row on it is not
returned; the problem says what kind of thing was found and on which line,
never the thing itself.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Sequence

from . import businesses, callmarkers, constants, formats, scan
from .errors import PathError, ValidationError
from .fsutil import read_text

# The heading the table sits under, and the five columns in their order.
SECTION = "Where the material lives"
COLUMNS = (
    "Kind of data",
    "Business",
    "Where it lives",
    "What reads it",
    "If that is not connected",
)
# The attribute each column is kept under on a row.
FIELDS = ("kind_of_data", "business", "where", "read_by", "if_not_connected")
# What a row's business cell says for data the whole company shares.
WHOLE_COMPANY = businesses.WHOLE_COMPANY
_WHOLE_COMPANY_WORDS = ("whole company", "the whole company", WHOLE_COMPANY)

# What can be wrong. A problem is reported, never said as it stands.
CODE_INCOMPLETE = "row-incomplete"
CODE_MALFORMED_ROW = "row-malformed"
CODE_OTHER_COLUMNS = "table-has-other-columns"
CODE_BUSINESS_NOT_IN_MAP = businesses.CODE_NOT_IN_MAP
CODE_BUSINESSES_UNREADABLE = businesses.CODE_UNREADABLE
CODE_SCREENED = "screened"
CODE_UNREADABLE = "unreadable"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
# A cell boundary is a bar no backslash stands in front of.
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")

# The sentence a person reads for each problem. It names neither the line
# nor what was on it: the line is on the problem for the assistant, and a
# count a person reads is always in words.
ROW_INCOMPLETE = "A row of your source map leaves a column empty, so it is not used."
ROW_MALFORMED = (
    "A row of your source map does not have the table's five columns, so it is "
    "not used."
)
OTHER_COLUMNS = (
    "A table in your source map does not have the five columns a source map "
    "uses, so its rows are not used."
)
BUSINESS_NOT_IN_MAP = (
    "A row of your source map names a business your base's map does not list."
)
BUSINESSES_UNREADABLE = (
    "The list of businesses in your base's map could not be read, so no row's "
    "business could be checked."
)
SCREENED = (
    "A line of your source map holds something that is never kept in a base, so "
    "it was left out."
)
UNREADABLE = "Your source map could not be read, so none of its rows were used."
_SENTENCES = {
    CODE_INCOMPLETE: ROW_INCOMPLETE,
    CODE_MALFORMED_ROW: ROW_MALFORMED,
    CODE_OTHER_COLUMNS: OTHER_COLUMNS,
    CODE_BUSINESS_NOT_IN_MAP: BUSINESS_NOT_IN_MAP,
    CODE_BUSINESSES_UNREADABLE: BUSINESSES_UNREADABLE,
    CODE_SCREENED: SCREENED,
    CODE_UNREADABLE: UNREADABLE,
}


class Problem(object):
    """One thing wrong with the source map, by line, with no value from the file."""

    __slots__ = ("code", "line_number", "pattern_class")

    def __init__(self, code: str, line_number: int = 0, pattern_class: str = ""):
        self.code = code
        self.line_number = line_number
        self.pattern_class = pattern_class

    def sentence(self) -> str:
        return _SENTENCES[self.code]

    def __repr__(self) -> str:
        return "Problem(%r, line=%d, class=%r)" % (
            self.code,
            self.line_number,
            self.pattern_class,
        )


class Row(object):
    """One row of the table, its five cells, and the line it came from."""

    __slots__ = FIELDS + ("line_number", "problems", "open_questions", "missing")

    def __init__(self, cells: Sequence[str], line_number: int):
        for name, value in zip(FIELDS, cells):
            setattr(self, name, value)
        self.line_number = line_number
        self.problems: List[str] = []
        self.missing = [name for name, value in zip(FIELDS, cells) if _blank(value)]
        self.open_questions = callmarkers.questions(" ".join(cells))

    def __repr__(self) -> str:
        return "Row(line=%d, problems=%r)" % (self.line_number, self.problems)


class SourceMap(object):
    """Everything the source map says, read once.

    `rows` are the rows that can be used, including one naming a business the
    map does not list, which is kept and reported. `incomplete` are rows with
    an empty column, reported and never used. `problems` lists everything
    wrong, in the order of the file.
    """

    def __init__(self):
        self.has_file = False
        self.has_table = False
        self.rows: List[Row] = []
        self.incomplete: List[Row] = []
        self.problems: List[Problem] = []


def _blank(value: str) -> bool:
    """Whether a cell says nothing: empty, or punctuation alone, such as a dash."""
    return not any(character.isalnum() for character in str(value or ""))


def _cells(line: str) -> List[str]:
    """The cells of one table line, each trimmed, with an escaped bar kept as a bar."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [
        " ".join(cell.replace("\\|", "|").split())
        for cell in _CELL_SPLIT_RE.split(text)
    ]


def _is_separator(line: str) -> bool:
    cells = _cells(line)
    return bool(cells) and all(_SEPARATOR_CELL_RE.match(cell) for cell in cells)


def _is_table_line(line: str) -> bool:
    return line.strip().startswith("|")


def _section_lines(body_lines: List[str]) -> List[int]:
    """The indexes of the body lines under the material heading, and no others."""
    inside = False
    level = 0
    in_code = False
    found: List[int] = []
    for index, line in enumerate(body_lines):
        # A line shaped like a heading inside a block of code is not a heading.
        if line.strip().startswith(("```", "~~~")):
            in_code = not in_code
        heading = None if in_code else _HEADING_RE.match(line.strip())
        if heading:
            this_level = len(heading.group(1))
            if inside and this_level <= level:
                break
            if not inside and heading.group(2).strip().lower() == SECTION.lower():
                inside = True
                level = this_level
                continue
        if inside:
            found.append(index)
    return found


def _business_of(
    value: str,
    listed: Sequence[str],
    named: Dict[str, Optional[str]],
) -> Optional[str]:
    """The short name of the business a cell names, the whole company, or None."""
    said = " ".join(value.split()).lower()
    if said in _WHOLE_COMPANY_WORDS:
        return WHOLE_COMPANY
    return businesses.matching(
        value, [businesses.Business(slug, named.get(slug)) for slug in listed]
    )


def _body_and_offset(text: str):
    """The text below the settings block, and how many file lines come before it.

    The body is what `formats.split_document` gives, so the line numbers a
    problem names are the file's own, counted from the top, settings included.
    A file whose settings block cannot be read is read whole.
    """
    try:
        _block, body = formats.split_document(text)
    except (ValidationError, PathError):
        return text, 0
    whole = text[1:] if text.startswith("﻿") else text
    if not body:
        return body, len(whole.split("\n"))
    return body, whole.count("\n", 0, len(whole) - len(body))


def _screened_lines(body_lines: List[str], allowlist) -> Dict[int, str]:
    """Each body line a screen refused, with the kind of thing found on it.

    The screens are handed one line at a time, numbered the way the table is
    read, because they split text into lines by a wider rule than this module
    does: a page break or a line separator pasted above the table would
    otherwise move every screen's line number by one and refuse the wrong row
    (the correctness review of 2026-10-10, finding 1).
    """
    refused: Dict[int, str] = {}
    for number, line in enumerate(body_lines, start=1):
        hits = scan.scan_text(line, allowlist, "the source map")
        hits += scan.scan_source_map(line, allowlist)
        if hits:
            refused[number] = hits[0].pattern_class
    return refused


def parse(
    text: str,
    listed: Sequence[str],
    names: Optional[Dict[str, Optional[str]]] = None,
    allowlist=None,
    check_businesses: bool = True,
) -> SourceMap:
    """Read the source map's table into rows, from its text and the map's businesses.

    `listed` is the short name of each business the map lists, and `names`
    what the map calls each, so a row may name a business either way. When
    the map's list could not be read, `check_businesses` is false and no row's
    business is judged against it.
    """
    found = SourceMap()
    found.has_file = True
    named = dict(names or {})
    body, offset = _body_and_offset(text or "")
    body_lines = body.split("\n")
    refused = _screened_lines(body_lines, allowlist)
    for number, pattern_class in sorted(refused.items()):
        found.problems.append(Problem(CODE_SCREENED, number + offset, pattern_class))

    section = _section_lines(body_lines)
    position = 0
    while position < len(section):
        index = section[position]
        line = body_lines[index]
        following = section[position + 1] if position + 1 < len(section) else None
        if not (
            _is_table_line(line)
            and following == index + 1
            and _is_separator(body_lines[following])
        ):
            position += 1
            continue
        header = [cell.lower() for cell in _cells(line)]
        matches = header == [column.lower() for column in COLUMNS]
        if matches:
            found.has_table = True
        else:
            found.problems.append(Problem(CODE_OTHER_COLUMNS, index + 1 + offset))
        position += 2
        while position < len(section) and _is_table_line(body_lines[section[position]]):
            row_index = section[position]
            position += 1
            if not matches or (row_index + 1) in refused:
                continue
            line_number = row_index + 1 + offset
            cells = _cells(body_lines[row_index])
            if len(cells) == len(COLUMNS) - 1:
                # The last column left off altogether is a row with no
                # fallback, which is what an empty last cell is too.
                cells.append("")
            if len(cells) != len(COLUMNS):
                found.problems.append(Problem(CODE_MALFORMED_ROW, line_number))
                continue
            row = Row(cells, line_number)
            if row.missing:
                found.incomplete.append(row)
                found.problems.append(Problem(CODE_INCOMPLETE, line_number))
                continue
            if check_businesses:
                business = _business_of(row.business, listed, named)
                if business is None:
                    row.problems.append(CODE_BUSINESS_NOT_IN_MAP)
                    found.problems.append(
                        Problem(CODE_BUSINESS_NOT_IN_MAP, line_number)
                    )
                else:
                    row.business = business
            found.rows.append(row)
    found.problems.sort(key=lambda problem: problem.line_number)
    return found


def read(base_root: str) -> SourceMap:
    """Read one base's source map, against the businesses its map lists.

    A base with no source map, and one whose source map is still the starter
    with no rows, both have no rows, which is not a problem.
    """
    full = os.path.join(base_root, constants.STACK_PATH.replace("/", os.sep))
    folder = os.path.join(base_root, constants.ACCESS_DIR)
    if not os.path.lexists(full):
        return SourceMap()
    # A folder reached through a link may be anywhere on this computer, so it
    # is never read; `read_text` already refuses a link at the file itself.
    text = None if os.path.islink(folder) else read_text(full)
    if text is None:
        found = SourceMap()
        found.has_file = True
        found.problems.append(Problem(CODE_UNREADABLE))
        return found
    unreadable = False
    map_text = read_text(os.path.join(base_root, constants.MAP_PATH)) or ""
    try:
        listed = businesses.read_map_businesses(map_text)
    except ValidationError:
        listed, unreadable = [], True
    allowlist, _code = scan.load_allowlist(base_root)
    found = parse(
        text,
        [one.slug for one in listed],
        names={one.slug: one.name for one in listed},
        allowlist=allowlist,
        check_businesses=not unreadable,
    )
    if unreadable:
        found.problems.insert(0, Problem(CODE_BUSINESSES_UNREADABLE))
    return found


# --- Rows drafted from what a person says (Track 4, Unit T4.6) ---------------

# A drafted row naming a place or a tool the person never named, and a draft
# holding no row at all.
CODE_NOT_NAMED = "not-named"
CODE_NO_ROWS = "no-rows"
NOT_NAMED = (
    "A drafted row names a place or a tool you did not name, so it is not used."
)
NO_ROWS = "The draft holds no rows, so there is nothing to add to your source map."
_SENTENCES[CODE_NOT_NAMED] = NOT_NAMED
_SENTENCES[CODE_NO_ROWS] = NO_ROWS
# What a person may say reads a kind of data when nothing does yet. Such a
# cell needs no tool named in their answers.
NOTHING_READS_IT = ("nothing", "none", "nothing yet", "no tool", "not connected")

_FENCE_LINE = re.compile(r"^\s*```")


def _without_fence(text: str) -> str:
    return "\n".join(
        line for line in str(text or "").split("\n") if not _FENCE_LINE.match(line)
    )


def _evened(text: str) -> str:
    from . import notes as notes_module

    return notes_module.even_out(str(text or ""))


def _said(value: str, answers: str) -> bool:
    """Whether a cell's words stand whole in what the person said."""
    wanted = _evened(value)
    if not wanted:
        return False
    return bool(
        re.search(r"(?<!\w)%s(?!\w)" % re.escape(wanted), _evened(answers))
    )


def check_drafted(
    draft_text: str,
    answers: str,
    listed: Sequence[str] = (),
    names: Optional[Dict[str, Optional[str]]] = None,
    allowlist=None,
    check_businesses: bool = True,
) -> SourceMap:
    """Read drafted rows exactly as the file's own rows are read, and more.

    The draft is the "Where the material lives" section with its table. Every
    row has to carry all five columns, nothing shaped like a key or a token,
    and a business the map lists, as any row of the file does. On top of that,
    where a kind of data lives and which tool reads it have to be words the
    person said, so a tool a company of that size usually has never becomes a
    row because nobody named it. A cell saying nothing reads it yet is let
    through. Rows that fail are left out of `rows` and named in `problems`.
    """
    found = parse(
        _without_fence(draft_text),
        listed,
        names=names,
        allowlist=allowlist,
        check_businesses=check_businesses,
    )
    kept: List[Row] = []
    for row in found.rows:
        reader = str(row.read_by or "").strip().lower().rstrip(".")
        if not _said(row.where, answers) or (
            reader not in NOTHING_READS_IT and not _said(row.read_by, answers)
        ):
            row.problems.append(CODE_NOT_NAMED)
            found.problems.append(Problem(CODE_NOT_NAMED, row.line_number))
            continue
        kept.append(row)
    found.rows = kept
    if not kept and not found.problems:
        found.problems.append(Problem(CODE_NO_ROWS))
    found.problems.sort(key=lambda problem: problem.line_number)
    return found


def check_drafted_in(base_root: str, draft_text: str, answers: str) -> SourceMap:
    """`check_drafted` against one base's businesses and its own allowlist."""
    unreadable = False
    map_text = read_text(os.path.join(base_root, constants.MAP_PATH)) or ""
    try:
        listed = businesses.read_map_businesses(map_text)
    except ValidationError:
        listed, unreadable = [], True
    allowlist, _code = scan.load_allowlist(base_root)
    return check_drafted(
        draft_text,
        answers,
        [one.slug for one in listed],
        names={one.slug: one.name for one in listed},
        allowlist=allowlist,
        check_businesses=not unreadable,
    )
