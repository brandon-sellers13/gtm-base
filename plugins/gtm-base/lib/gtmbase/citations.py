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
The one exception is a customer the draft names, which `named_for` hands
back beside its code: the writer's own words, so it knows which to take out.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence

from . import constants, notes as notes_module

CITATION_RE = re.compile(r"\[\s*(n\d+(?:\s*,\s*n\d+)*)\s*\]")
_ID_RE = re.compile(r"n\d+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_ITEM_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_TABLE_RULE_RE = re.compile(r"^\s*\|?\s*:?-{3,}")
_MARKER_RE = re.compile(constants.YOUR_CALL_PATTERN, re.IGNORECASE)
# A figure, whole: its currency sign, its digits, and the unit right after it.
_FIGURE_RE = re.compile(
    r"(?<![\w.,])[$\u20ac\u00a3]?\s?\d(?:[\d,.]*\d)?"
    # The unit in any case, so "$900K" is read whole and never as a bare "$900".
    r"(?i:\s?(?:%|percent\b|per cent\b|k\b|m\b|bn\b|b\b|x\b|million\b|billion\b|thousand\b))?"
)
# The endings that make a company's name formal, left off when it is matched.
_NAME_ENDINGS = re.compile(
    r"[,\s]+(?:inc|incorporated|corp|corporation|co|company|ltd|limited|llc|plc|gmbh|group|holdings)\.?$",
    re.IGNORECASE,
)

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
CODE_HEADING_CITES = "a-heading-cites-a-note"
CODES = (
    CODE_UNCITED,
    CODE_UNKNOWN_NOTE,
    CODE_FIGURE,
    CODE_CUSTOMER,
    CODE_NOT_SETTLED,
    CODE_HEADING_CITES,
)

# The sections setup writes itself, which a draft never writes and review
# never checks as the draft's own sentences.
SETUP_HEADINGS = constants.SETUP_WRITTEN_HEADINGS
CODE_SETUP_SECTION = "writes-a-section-setup-writes"


class Block(object):
    """One paragraph, one item of a list, or one row of a table in a body."""

    __slots__ = ("section", "number", "kind", "text", "first", "last", "named")

    def __init__(self, section, number, kind, text, first, last):
        self.section = section
        self.number = number
        self.kind = kind
        self.text = text
        self.first = first
        self.last = last
        # The customer's name this block was refused for, as it stands in
        # the block, so the writer is told which words to take out.
        self.named = []

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
            # The row just above this line is the table's header, which
            # names columns and says nothing to cite.
            if found and found[-1].kind == "row" and found[-1].last == index - 1:
                gone = found.pop()
                state["counts"]["row"] -= 1
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


def _all_names_in(text: str, names: Iterable[str]) -> List[str]:
    """Every customer's name a line writes, as the material writes it.

    Matched in the line's own letter case, so an ordinary word that happens
    to be a customer's name, such as box, is not one. Where a short form
    stands inside a longer one, such as Acme inside Acme Corp, only the
    longer is given, so a refusal says "Acme Corp" once. In the order the
    line writes them, each once.
    """
    plain = " ".join(without_citations(text).split())
    spans = []
    for name in names:
        if not name:
            continue
        for match in re.finditer(r"(?<![\w])%s(?![\w])" % re.escape(name), plain):
            spans.append((match.start(), match.end(), name))
    kept = []
    for start, end, name in sorted(spans, key=lambda span: (span[0] - span[1], span[0])):
        if all(end <= first or start >= last for first, last, _name in kept):
            kept.append((start, end, name))
    found: List[str] = []
    for _start, _end, name in sorted(kept):
        if name not in found:
            found.append(name)
    return found


def _names_in(text: str, names: Iterable[str]) -> Optional[str]:
    """The longest customer's name a line writes, or None if it writes none."""
    found = _all_names_in(text, names)
    return max(found, key=len) if found else None


# A word standing in the material's own sentences, not inside an email
# address, a web address or a handle, where a customer's domain is written in
# lower case whatever the customer is called.
_IN_PROSE = r"(?<![\w@./#:-])%s(?![\w@/#-])(?!\.\w)"


def _ordinary(short: str, quotes: Sequence[str]) -> bool:
    """Whether the material uses a short name as an ordinary word.

    "enterprise buyers" or "a principal engineer" in the material's own
    words means "Enterprise" or "Principal" at the start of a sentence or in
    a job title is the word, not the customer whose formal name it begins.
    A name with no capital in it is never told apart this way, and neither
    is one the material writes in lower case only in an address, such as
    procurement@acme.com.
    """
    lower = short.lower()
    pattern = _IN_PROSE % re.escape(lower)
    return lower != short and any(re.search(pattern, quote) for quote in quotes)


def _forms_of(name: str, quotes: Sequence[str] = ()) -> List[str]:
    """A customer's name as written, and without its formal ending.

    The short form is left out when the material itself uses it as an
    ordinary word. The name as the material writes it is always kept.
    """
    written = " ".join(str(name or "").split())
    forms = [written] if written else []
    short = _NAME_ENDINGS.sub("", written).strip()
    if (
        short
        and short not in forms
        and len(short) > 1
        and not _ordinary(short, quotes)
    ):
        forms.append(short)
    return forms


def customer_names(
    found: Sequence["notes_module.Note"], company: str, segment_names: Sequence[str]
) -> List[str]:
    """The customers the notes name, in each form a draft might write them.

    A name that is also a segment's name, or that sits inside the company's
    own name or a segment's, is never a reason to refuse a sentence, and
    neither is the company's own name.
    """
    guarded = [notes_module.even_out(name) for name in [company] + list(segment_names) if name]
    quotes = [" ".join(str(item.quote or "").split()) for item in found]
    names: List[str] = []
    for item in found:
        if item.kind != notes_module.KIND_CUSTOMER or not item.customer:
            continue
        for form in _forms_of(item.customer, quotes):
            evened = notes_module.even_out(form)
            if not evened or form in names:
                continue
            if any(evened == other or evened in other or other in evened for other in guarded):
                continue
            names.append(form)
    return names


def _figures(text: str) -> List[str]:
    return [figure.strip() for figure in _FIGURE_RE.findall(without_citations(text))]


_A_UNIT = r"\s?(?:%|percent\b|per cent\b|k\b|m\b|bn\b|b\b|x\b|million\b|billion\b|thousand\b)"


def _figure_in(figure: str, quote: str) -> bool:
    """Whether a figure, unit and all, stands whole in one quote.

    A number written with no unit matches only where the quote gives it none
    either, so 14 never stands for 14%.
    """
    evened = notes_module.even_out(figure)
    if not evened:
        return False
    bare = not re.search(_A_UNIT + r"$", evened)
    tail = r"(?![\d])" + (r"(?!%s)" % _A_UNIT if bare else "")
    return bool(
        re.search(r"(?<![\d.,])%s%s" % (re.escape(evened), tail), notes_module.even_out(quote))
    )


def _fixed(text: str) -> bool:
    lines = [line.strip().lstrip("-*+ ").strip() for line in text.split("\n") if line.strip()]
    return bool(lines) and all(without_citations(line).strip() in _FIXED for line in lines)


def check(
    body: str,
    readable: Dict[str, "notes_module.Note"],
    customers: Sequence[str],
    allowed_headings: Sequence[str] = (),
) -> List[tuple]:
    """Every problem in one body, as (block, code) pairs, in reading order.

    `readable` holds the notes this draft read, by id. `customers` holds the
    names `customer_names` gave for every note of the run, so a customer the
    draft did not read about is still never named in its sentences.
    `allowed_headings` are the settled segments' names, which a heading may
    carry as they are, digits and all.
    """
    problems: List[tuple] = []
    allowed = set(notes_module.even_out(name) for name in allowed_headings)
    for number, line in enumerate(str(body or "").split("\n"), start=1):
        if any(line.strip().startswith(head) for head in SETUP_HEADINGS):
            problems.append((Block(0, number, "line", line, number - 1, number - 1), CODE_SETUP_SECTION))
            continue
        if _HEADING_RE.match(line):
            heading = Block(0, number, "heading", line, number - 1, number - 1)
            title = line.strip().lstrip("#").strip()
            if CITATION_RE.search(line):
                problems.append((heading, CODE_HEADING_CITES))
            heading.named = _all_names_in(title, customers)
            if heading.named:
                problems.append((heading, CODE_CUSTOMER))
            if _figures(title) and notes_module.even_out(title) not in allowed:
                problems.append((heading, CODE_FIGURE))
    for block in blocks(body):
        text = block.text
        if _fixed(text):
            continue
        ids = cited(text)
        if not ids:
            problems.append((block, CODE_UNCITED))
            continue
        if any(note_id not in readable for note_id in ids):
            problems.append((block, CODE_UNKNOWN_NOTE))
            continue
        quotes = [readable[i].quote for i in ids]
        for figure in _figures(text):
            if not any(_figure_in(figure, quote) for quote in quotes):
                problems.append((block, CODE_FIGURE))
                break
        block.named = _all_names_in(text, customers)
        if block.named:
            problems.append((block, CODE_CUSTOMER))
        if any(not readable[i].settled for i in ids) and not _MARKER_RE.search(text):
            problems.append((block, CODE_NOT_SETTLED))
    return problems


def codes_for(problems: Sequence[tuple]) -> List[str]:
    """The problems as codes a person can be told, each naming only where."""
    return ["%s:%s" % (code, block.where) for block, code in problems]


def named_for(problems: Sequence[tuple]) -> List[str]:
    """Each customer a refused block names, beside where it is, one apiece.

    The codes name only where a problem is. A writer refused for naming a
    customer was left to guess which words matched, and in the scored replay
    of 2026-11-25 cut ordinary words and real detail to get past it. These
    are the writer's own words handed back, the name as it stands in the
    block, so only that name is taken out.
    """
    return [
        "%s:%s" % (block.where, name)
        for block, code in problems
        if code == CODE_CUSTOMER
        for name in block.named
    ]


def take_out(body: str, problems: Sequence[tuple]) -> str:
    """The body with each failing block replaced by one question about it."""
    lines = str(body or "").split("\n")
    failing = sorted(set((block.first, block.last) for block, _code in problems), reverse=True)
    for first, last in failing:
        lines[first : last + 1] = ["", TAKEN_OUT, ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


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
CODE_SUPPORT_DRAFT_CHANGED = "support-draft-changed"


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
        lines[first : last + 1] = ["", BEYOND_TAKEN_OUT, ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


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


def _one_line(item):
    """A note as a document shows it: its words and names on one line each."""
    shown = notes_module.Note(item.row(), id=item.id)
    for field in ("quote", "customer", "segment"):
        setattr(shown, field, " ".join(str(getattr(item, field) or "").split()))
    return shown


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
        # A segment the person did not settle is named only when the file's
        # own words hold its name, which the notes check makes sure of.
        if item.kind in (notes_module.KIND_SEGMENT, notes_module.KIND_CUSTOMER):
            if item.segment and item.segment not in names:
                names.append(item.segment)
    found = [_one_line(item) for item in found]
    by_id = dict((item.id, item) for item in found)
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
        "- " + NOT_NOTED % file_names.get(number, "S%s" % number)
        for number in sorted(set(int(n) for n, _c in not_noted))
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
