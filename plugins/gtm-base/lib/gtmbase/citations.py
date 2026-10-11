"""Every line a draft writes says which notes it rests on, and is checked.

The fidelity replay of 2026-10-10 failed on lines nobody could trace (a
document listed its files and dates, but not which file a claim came from),
on a customer credited with what another customer bought, and on figures and
terms the material leaves open written as though they were settled. A draft
written from the notes now cites them, as `[n12]` or `[n3, n7]`, in every
paragraph and every item of a list, and review checks each one here:

- every paragraph and item cites at least one note this draft read, unless
  it is the one fixed sentence that says the material does not cover a part;
- every figure it writes is in the words of a note it cites;
- no customer is named in the draft's own sentences, because setup writes
  the list of customers itself, each beside the material's own words;
- a paragraph or item that cites a note the material has not settled carries
  a `[your call: ...]` question, so nothing open reads as decided.

Nothing here talks to a model. What comes back names where in the draft a
problem is, never the words, so nothing of the company's leaves in a code.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence

from . import constants, notes as notes_module

CITATION_RE = re.compile(r"\[\s*(n\d+(?:\s*,\s*n\d+)*)\s*\]")
_ID_RE = re.compile(r"n\d+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_ITEM_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_TABLE_RULE_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
_MARKER_RE = re.compile(constants.YOUR_CALL_PATTERN, re.IGNORECASE)
_FIGURE_RE = re.compile(r"\d(?:[\d,.]*\d)?")

# The one sentence a draft writes where the material does not cover a part
# it has to carry. It cites nothing, because there is nothing to cite.
NOT_COVERED = "Nothing in the material covers this."
# What a line that kept failing its check is replaced with after the third
# try, so it is asked about rather than refused for ever.
TAKEN_OUT = "[your call: a line here was taken out because no note supports it]"
# What a line the support check found saying more than its notes is replaced
# with, so the person is asked rather than told something the material never
# said.
BEYOND_TAKEN_OUT = (
    "[your call: a line here said more than its notes support, so it was taken out]"
)

# The sentences a draft writes word for word where setup's own rules say to,
# which cite nothing because they say nothing the material said.
_FIXED = (
    NOT_COVERED,
    TAKEN_OUT,
    constants.UMBRELLA_PENDING_SENTENCE,
    constants.UMBRELLA_LEFT_OUT_SENTENCE,
    BEYOND_TAKEN_OUT,
)

CODE_UNCITED = "uncited"
CODE_UNKNOWN_NOTE = "cites-a-note-it-did-not-read"
CODE_FIGURE = "figure-not-in-its-notes"
CODE_CUSTOMER = "customer-named"
CODE_NOT_SETTLED = "open-stated-as-settled"
CODES = (CODE_UNCITED, CODE_UNKNOWN_NOTE, CODE_FIGURE, CODE_CUSTOMER, CODE_NOT_SETTLED)

# The sections setup writes itself, which a draft never writes and review
# never checks as the draft's own sentences.
SETUP_HEADINGS = constants.SETUP_WRITTEN_HEADINGS
CODE_SETUP_SECTION = "writes-a-section-setup-writes"


class Block(object):
    """One paragraph, one item of a list, or one row of a table in a body."""

    __slots__ = ("section", "number", "kind", "text", "first", "last")

    def __init__(self, section, number, kind, text, first, last):
        self.section = section
        self.number = number
        self.kind = kind
        self.text = text
        self.first = first
        self.last = last

    @property
    def where(self) -> str:
        return "section-%d-%s-%d" % (self.section, self.kind, self.number)

    def __repr__(self) -> str:
        return "Block(%s)" % self.where


def blocks(body: str) -> List[Block]:
    """The body as the paragraphs, list items and table rows a reader sees.

    Headings are not blocks, and neither is anything under a heading setup
    writes itself. A line that is not an item or a row carries on the
    paragraph or item above it. Sections are counted from one at each
    heading, so a code can say where a problem is without repeating a word
    of it.
    """
    lines = str(body or "").split("\n")
    found: List[Block] = []
    state = {"section": 0, "counts": {}, "kind": None, "start": 0, "lines": []}

    def close(end):
        kind = state["kind"]
        if kind and any(line.strip() for line in state["lines"]):
            counts = state["counts"]
            counts[kind] = counts.get(kind, 0) + 1
            found.append(
                Block(
                    state["section"],
                    counts[kind],
                    kind,
                    "\n".join(state["lines"]).strip(),
                    state["start"],
                    end,
                )
            )
        state["kind"], state["lines"] = None, []

    def begin(kind, index, line):
        state["kind"], state["start"], state["lines"] = kind, index, [line]

    skipping = False
    for index, line in enumerate(lines):
        if _HEADING_RE.match(line):
            close(index - 1)
            state["section"] += 1
            state["counts"] = {}
            skipping = any(line.strip().startswith(head) for head in SETUP_HEADINGS)
            continue
        if skipping:
            continue
        if not line.strip():
            close(index - 1)
            continue
        if _TABLE_RULE_RE.match(line):
            continue
        if _ITEM_RE.match(line):
            close(index - 1)
            begin("item", index, line)
        elif line.strip().startswith("|"):
            close(index - 1)
            begin("row", index, line)
            close(index)
        elif state["kind"] in ("paragraph", "item"):
            state["lines"].append(line)
        else:
            begin("paragraph", index, line)
    close(len(lines) - 1)
    return found


def cited(text: str) -> List[str]:
    """The note ids one block cites, in order, once each."""
    ids: List[str] = []
    for match in CITATION_RE.finditer(text):
        for note_id in _ID_RE.findall(match.group(1)):
            if note_id not in ids:
                ids.append(note_id)
    return ids


def without_citations(text: str) -> str:
    return CITATION_RE.sub(" ", text)


def _names_in(text: str, names: Iterable[str]) -> bool:
    evened = notes_module.even_out(without_citations(text))
    for name in names:
        if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(name), evened):
            return True
    return False


def customer_names(
    found: Sequence["notes_module.Note"], company: str, segment_names: Sequence[str]
) -> List[str]:
    """The customers the notes name, as they are matched in a draft.

    A name that is also a segment's name, or that sits inside the company's
    own name or a segment's, is never a reason to refuse a sentence.
    """
    guarded = [notes_module.even_out(name) for name in [company] + list(segment_names)]
    names: List[str] = []
    for item in found:
        if item.kind != notes_module.KIND_CUSTOMER or not item.customer:
            continue
        evened = notes_module.even_out(item.customer)
        if not evened or evened in names:
            continue
        if any(evened == other or evened in other for other in guarded if other):
            continue
        names.append(evened)
    return names


def check(
    body: str,
    readable: Dict[str, "notes_module.Note"],
    customers: Sequence[str],
) -> List[tuple]:
    """Every problem in one body, as (block, code) pairs, in reading order.

    `readable` holds the notes this draft read, by id. `customers` holds the
    names `customer_names` gave for every note of the run, so a customer the
    draft did not read about is still never named in its sentences.
    """
    problems: List[tuple] = []
    for number, line in enumerate(str(body or "").split("\n"), start=1):
        if any(line.strip().startswith(head) for head in SETUP_HEADINGS):
            problems.append((Block(0, number, "line", line, number - 1, number - 1), CODE_SETUP_SECTION))
    for block in blocks(body):
        text = block.text
        bare = without_citations(text).strip()
        if bare in _FIXED:
            continue
        ids = cited(text)
        if not ids:
            problems.append((block, CODE_UNCITED))
            continue
        if any(note_id not in readable for note_id in ids):
            problems.append((block, CODE_UNKNOWN_NOTE))
            continue
        quotes = " ".join(notes_module.even_out(readable[i].quote) for i in ids)
        for figure in _FIGURE_RE.findall(without_citations(text)):
            if notes_module.even_out(figure) not in quotes:
                problems.append((block, CODE_FIGURE))
                break
        if _names_in(text, customers):
            problems.append((block, CODE_CUSTOMER))
        if any(not readable[i].settled for i in ids) and not _MARKER_RE.search(text):
            problems.append((block, CODE_NOT_SETTLED))
    return problems


def codes_for(problems: Sequence[tuple]) -> List[str]:
    """The problems as codes a person can be told, each naming only where."""
    return ["%s:%s" % (code, block.where) for block, code in problems]


def take_out(body: str, problems: Sequence[tuple]) -> str:
    """The body with each failing block replaced by one question about it."""
    lines = str(body or "").split("\n")
    failing = sorted(set((block.first, block.last) for block, _code in problems), reverse=True)
    for first, last in failing:
        lines[first : last + 1] = [TAKEN_OUT]
    return "\n".join(lines)


# --- The support check: an independent read of each line (U5) ----------------

VERDICT_SUPPORTED = "supported"
VERDICT_BEYOND = "beyond"
VERDICTS = (VERDICT_SUPPORTED, VERDICT_BEYOND)

# The most notes about the same segment shown beside one line, so a request
# stays readable; the line's own notes are always shown in full.
NEIGHBOURS_MAX = 12

CODE_SUPPORT_NO_FENCE = "support-no-fence"
CODE_SUPPORT_INCOMPLETE = "support-incomplete"
CODE_SUPPORT_NOT_CHECKED = "support-not-checked"


def checkable(body: str) -> List[Block]:
    """The blocks the support check reads: every one that cites a note."""
    return [block for block in blocks(body) if cited(block.text)]


def support_text(
    body: str, readable: Dict[str, "notes_module.Note"], every_note: Sequence["notes_module.Note"]
) -> str:
    """Each line of a draft beside its own notes and the notes near it.

    The notes near a line are the other notes about the same segments as the
    line's own notes, so a line that takes one side of something the
    material leaves open is read beside the other side.
    """
    parts: List[str] = []
    for number, block in enumerate(checkable(body), start=1):
        own = [readable[i] for i in cited(block.text) if i in readable]
        segments = set(item.segment for item in own)
        near = [
            item
            for item in every_note
            if item.segment in segments and item.id not in [o.id for o in own]
        ][:NEIGHBOURS_MAX]
        lines = ["B%d" % number, "The line:", block.text, "Its notes:"]
        lines.extend(
            '- %s (%s) "%s"' % (item.id, item.status, item.quote) for item in own
        )
        if near:
            lines.append("Other notes about the same segment:")
            lines.extend(
                '- %s (%s) "%s"' % (item.id, item.status, item.quote) for item in near
            )
        parts.append("\n".join(lines))
    return "\n\n".join(parts) if parts else "There are no lines to check."


def read_support(text: str, count: int):
    """The verdicts of a support answer, one per line, or the reason it fails."""
    lines = notes_module.notes_lines(text)
    if lines is None:
        return None, CODE_SUPPORT_NO_FENCE
    import json

    verdicts: Dict[int, str] = {}
    for raw in lines:
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except ValueError:
            return None, CODE_SUPPORT_INCOMPLETE
        if not isinstance(row, dict):
            return None, CODE_SUPPORT_INCOMPLETE
        match = re.match(r"^B?(\d+)$", str(row.get("line", "")).strip())
        verdict = row.get("verdict")
        if not match or verdict not in VERDICTS:
            return None, CODE_SUPPORT_INCOMPLETE
        verdicts[int(match.group(1))] = verdict
    if sorted(verdicts) != list(range(1, count + 1)):
        return None, CODE_SUPPORT_INCOMPLETE
    return verdicts, None


def take_out_beyond(body: str, verdicts: Dict[int, str]) -> str:
    """The body with each line found to say more than its notes taken out."""
    lines = str(body or "").split("\n")
    failing = [
        (block.first, block.last)
        for number, block in enumerate(checkable(body), start=1)
        if verdicts.get(number) == VERDICT_BEYOND
    ]
    for first, last in sorted(failing, reverse=True):
        lines[first : last + 1] = [BEYOND_TAKEN_OUT]
    return "\n".join(lines)


# --- What setup writes into the document itself (U6) --------------------------

NO_EVIDENCE = "The material names no customer as evidence for this segment."
NOT_ONE_SEGMENT = "Not tied to one segment"
NOTHING_OPEN = "The material leaves nothing open that these notes found."
NOT_NOTED = "A part of %s could not be noted, so nothing from it is here."
_STATUS_WORDS = {
    notes_module.PROPOSED: "proposed",
    notes_module.ON_HOLD: "on hold",
    notes_module.OPEN: "open",
}


class Rendered(object):
    """A document as setup writes it: the body, and the files it cites."""

    __slots__ = ("body", "sources")

    def __init__(self, body, sources):
        self.body = body
        self.sources = list(sources)


def _footnote_ref(match) -> str:
    return "".join("[^%s]" % note_id for note_id in _ID_RE.findall(match.group(1)))


def render(
    body: str,
    found: Sequence["notes_module.Note"],
    file_names: Dict[int, str],
    segment_order: Sequence[str],
    only_segment: str = None,
    not_noted: Sequence[tuple] = (),
) -> Rendered:
    """The body with its citations as footnotes and setup's three sections.

    `found` is every note this document is responsible for: all of them for
    the profile and the positioning, a segment's own and the company-wide
    ones for a segment. `file_names` holds each file's number and the name it
    is shown by, with its date. Setup writes the evidence and the open items
    from the notes themselves, so no customer and no open item depends on
    the draft remembering it, and every line it writes carries the
    material's own words and the footnote saying where they are.
    """
    by_id = dict((item.id, item) for item in found)
    used: List[str] = []

    def use(note_id):
        if note_id in by_id and note_id not in used:
            used.append(note_id)
        return "[^%s]" % note_id

    prose = CITATION_RE.sub(_footnote_ref, str(body or "").rstrip("\n"))
    for note_id in _ID_RE.findall(" ".join(m.group(1) for m in CITATION_RE.finditer(str(body or "")))):
        use(note_id)

    names = list(segment_order)
    for item in found:
        if item.kind in (notes_module.KIND_SEGMENT, notes_module.KIND_CUSTOMER):
            if item.segment and item.segment not in names:
                names.append(item.segment)
    if only_segment is not None:
        names = [only_segment]

    evidence = ["## Evidence by segment", ""]
    for name in names:
        # A label in bold, never a heading: the document's own headings name
        # each segment once, and a change edits a part by its heading.
        evidence.append("**%s**" % name)
        evidence.append("")
        lines = [
            '- %s: "%s" %s' % (item.customer, item.quote, use(item.id))
            for item in found
            if item.kind == notes_module.KIND_CUSTOMER and item.segment == name
        ]
        evidence.extend(lines or [NO_EVIDENCE])
        evidence.append("")
    loose = [
        item for item in found
        if item.kind == notes_module.KIND_CUSTOMER and not item.segment and only_segment is None
    ]
    if loose:
        evidence.extend(["**%s**" % NOT_ONE_SEGMENT, ""])
        evidence.extend('- %s: "%s" %s' % (item.customer, item.quote, use(item.id)) for item in loose)
        evidence.append("")

    still_open = ["## Still open in the material", ""]
    lines = [
        '- "%s" (%s) %s' % (item.quote, _STATUS_WORDS[item.status], use(item.id))
        for item in found
        if not item.settled
    ]
    lines.extend(
        "- " + NOT_NOTED % file_names.get(int(number), "S%s" % number)
        for number, _code in sorted(set((int(n), c) for n, c in not_noted))
    )
    still_open.extend(lines or [NOTHING_OPEN])
    still_open.append("")

    where = ["## Where this came from", ""]
    cited_files: List[str] = []
    for note_id in used:
        item = by_id[note_id]
        shown = file_names.get(int(item.source), "S%s" % item.source)
        where.append('[^%s]: %s, "%s"' % (note_id, shown, item.quote))
        if shown not in cited_files:
            cited_files.append(shown)
    if not used:
        where.append("Nothing in this document cites a note.")

    whole = "\n".join([prose, ""] + evidence + still_open + where).rstrip("\n") + "\n"
    return Rendered(whole, cited_files)
