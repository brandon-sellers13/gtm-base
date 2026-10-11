"""The notes setup takes from every file before anything is drafted.

This is the summarize-first stage the fidelity replay of 2026-10-10 called
for. Drafts used to read the files themselves, as many as fitted one request,
and the replay showed what that cost: customers and segments past the limit
were never seen, some that were seen were not kept, and a line that went
beyond its source could not be traced to one. Now every file the person
agreed to is read in full, in batches that each fit one request, and the
assistant writes notes from each batch: what the material says about each
segment, each customer it names as evidence, and each fact, every one with
the material's own words beside it. Setup checks those words against the
file, and the drafts are written from the checked notes.

Nothing here talks to a model, and nothing here is ever dropped. A file
longer than one request is split into parts at its headings or its blank
lines, and the parts join back to exactly the text that was read.
"""

import hashlib
import json
import re
from typing import List, Optional, Sequence

from . import constants, sources as sources_module
from .errors import GtmBaseError

# Why a batch could not be prepared, as a code the script prints.
CODE_NO_SUCH_BATCH = "no-such-batch"
CODE_NOTHING_TO_READ = "nothing-to-read"

# How a part of a longer file is named, after the file's own number and name.
PART_SUFFIX = " part %d of %d"
# The longest a label can be inside a fence (sources._LABEL).
LABEL_MAX = 80
# The most parts any one file is assumed to need when the room a label
# takes is worked out, so the room is never underestimated.
PARTS_ASSUMED = 999


class NotesRefused(GtmBaseError):
    """A step of taking notes that could not be done, with a code to print."""

    default_code = "notes-refused"


class Part(object):
    """One file, or one part of a longer file, as one batch reads it."""

    __slots__ = ("number", "original", "index", "count", "text")

    def __init__(self, number, original, index, count, text):
        self.number = number
        self.original = original
        self.index = index
        self.count = count
        self.text = text

    @property
    def label(self) -> str:
        return part_label(self.number, self.original.label, self.index, self.count)

    def source(self) -> "sources_module.Source":
        """The part as a screened source, ready to be fenced."""
        return sources_module.Source(
            self.label,
            self.text,
            self.original.kind,
            date=self.original.date,
            path=self.original.path,
            screened=True,
        )

    @property
    def fenced(self) -> str:
        return sources_module.fence(self.source())

    def __repr__(self) -> str:
        return "Part(%r)" % (self.label,)


class Batch(object):
    """The parts one request reads, and a digest that says exactly which."""

    __slots__ = ("number", "parts")

    def __init__(self, number, parts):
        self.number = number
        self.parts = list(parts)

    @property
    def fenced(self) -> str:
        return "".join(part.fenced for part in self.parts)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.fenced.encode("utf-8")).hexdigest()

    @property
    def numbers(self) -> List[int]:
        """The files this batch reads, by their number in the run, once each."""
        seen: List[int] = []
        for part in self.parts:
            if part.number not in seen:
                seen.append(part.number)
        return seen

    def __repr__(self) -> str:
        return "Batch(%d, parts=%d)" % (self.number, len(self.parts))


def part_label(number: int, label: str, index: int = 1, count: int = 1) -> str:
    """The name a file, or a part of one, carries inside its fence.

    It starts with the file's number in this run, which is how a note says
    where it came from, so two files with the same name are never mistaken
    for each other. The file's own name is shortened, never the number or
    the part, when the whole would be too long for a fence.
    """
    head = "S%d " % number
    tail = PART_SUFFIX % (index, count) if count > 1 else ""
    room = LABEL_MAX - len(head) - len(tail)
    return head + str(label)[:room] + tail


def split_text(text: str, budget: int) -> List[str]:
    """Split text into parts no longer than `budget`, joining back exactly.

    A part ends just before a heading where one is far enough along, or else
    after a blank line, or after a line, or after a space, and only when none
    of those is found is a line cut where the room runs out. Nothing is ever
    left out, so the parts put together are the text that was read.
    """
    if budget < 1:
        raise ValueError("a part needs room for at least one character")
    pieces: List[str] = []
    rest = text
    while len(rest) > budget:
        cut = _best_cut(rest[:budget])
        pieces.append(rest[:cut])
        rest = rest[cut:]
    if rest or not pieces:
        pieces.append(rest)
    return pieces


_HEADING_START = re.compile(r"\n(?=#{1,6} )")


def _best_cut(window: str) -> int:
    half = len(window) // 2
    headings = [match.end() for match in _HEADING_START.finditer(window)]
    headings = [at for at in headings if at >= half]
    if headings:
        return headings[-1]
    for mark in ("\n\n", "\n", " "):
        at = window.rfind(mark)
        if at >= half or (mark != "\n\n" and at > 0):
            return at + len(mark)
    return len(window)


def _fence_room(number: int, original) -> int:
    """How much text one part of a file can hold inside one request."""
    widest = sources_module.Source(
        part_label(number, original.label, PARTS_ASSUMED, PARTS_ASSUMED),
        "",
        original.kind,
        screened=True,
    )
    return constants.DRAFT_SOURCES_MAX_CHARS - len(sources_module.fence(widest))


def parts_of(number: int, original) -> List[Part]:
    """One file as the parts it is read in: itself, or its parts in order."""
    whole = Part(number, original, 1, 1, original.text)
    if len(whole.fenced) <= constants.DRAFT_SOURCES_MAX_CHARS:
        return [whole]
    pieces = split_text(original.text, _fence_room(number, original))
    return [
        Part(number, original, index, len(pieces), piece)
        for index, piece in enumerate(pieces, start=1)
    ]


def pack(found: Sequence["sources_module.Source"]) -> List[Batch]:
    """Every file, in order, packed into batches that each fit one request.

    Files are numbered from one in the order given. A batch takes parts in
    order until the next would not fit, and then a new batch starts, so no
    part is ever left behind and the files stay in the order they were
    listed.
    """
    batches: List[Batch] = []
    current: List[Part] = []
    used = 0
    for number, original in enumerate(found, start=1):
        for part in parts_of(number, original):
            size = len(part.fenced)
            if current and used + size > constants.DRAFT_SOURCES_MAX_CHARS:
                batches.append(Batch(len(batches) + 1, current))
                current, used = [], 0
            current.append(part)
            used += size
    if current:
        batches.append(Batch(len(batches) + 1, current))
    return batches


def batch_listing(batch: Batch) -> str:
    """The list of what one batch reads, one line per file or part."""
    lines = ["The files in this batch, each with its number and its date where it has one:"]
    for part in batch.parts:
        date = getattr(part.original, "date", None)
        lines.append("- %s%s" % (part.label, " (%s)" % date if date else ""))
    return "\n".join(lines)


def plan_digest(batches: Sequence[Batch]) -> str:
    """One digest for every batch of a run, in order, and the limit they fit."""
    joined = "\n".join(
        [str(constants.DRAFT_SOURCES_MAX_CHARS)] + [batch.digest for batch in batches]
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def batch_numbered(batches: Sequence[Batch], number) -> Batch:
    """The batch with this number, or a refusal naming nothing but the code."""
    for batch in batches:
        if str(batch.number) == str(number):
            return batch
    raise NotesRefused("there is no batch with that number", CODE_NO_SUCH_BATCH)


def assemble(
    template: str,
    batch: Batch,
    company: str,
    segments_block: str,
    total: int,
) -> str:
    """The request for one batch, out of the notes prompt and its parts."""
    values = {
        "company": company,
        "segments": segments_block,
        "batch": "%d of %d" % (batch.number, total),
        "sources": batch_listing(batch) + "\n\n" + batch.fenced,
    }
    # One pass, so a value that happens to hold another placeholder is
    # never filled in a second time.
    return re.sub(
        r"\{\{(%s)\}\}" % "|".join(values),
        lambda match: values[match.group(1)],
        template,
    )


# --- Reading back and checking the notes (U2) ---------------------------------

KIND_SEGMENT = "segment"
KIND_CUSTOMER = "customer"
KIND_FACT = "fact"
KIND_NOTHING = "nothing"
KINDS = (KIND_SEGMENT, KIND_CUSTOMER, KIND_FACT, KIND_NOTHING)

SETTLED = "settled"
PROPOSED = "proposed"
ON_HOLD = "on-hold"
OPEN = "open"
STATUSES = (SETTLED, PROPOSED, ON_HOLD, OPEN)
# How firmly each status says a thing is so. A status is only ever lowered.
_FIRMNESS = {SETTLED: 3, PROPOSED: 2, ON_HOLD: 1, OPEN: 0}

# The longest stretch of the material one note may copy.
QUOTE_MAX = 300
# How many times one batch is checked before what held up is kept and the
# rest is recorded as not noted, so nobody is caught refusing forever.
ATTEMPTS = 3

CODE_NO_FENCE = "no-fence"
CODE_NOTES_WAITING = "notes-waiting"
CODE_NOT_THE_NOTES_FILE = "not-the-notes-file"
CODE_FILE_NOT_NOTED = "file-not-noted"
CODE_UNREADABLE_LINE = "a-line-could-not-be-read"
# What a customer, a figure or a segment may never hold: line breaks and the
# marks that build a heading, a table, a link, a fence or a tag.
_MARKUP = re.compile(r"[\n\r`#|<>\[\]{}]")

_FIELDS = ("source", "kind", "segment", "customer", "figure", "status", "quote")

# Words that say the material has not settled something. The firmest status
# the words allow is the one the note may carry, whatever the note says.
_ON_HOLD_WORDS = re.compile(r"\b(on hold|paused|parked|shelved|deprioriti[sz]ed)\b")
_PROPOSED_WORDS = re.compile(r"\b(propos(e|ed|es|al|als|ing)|plans? to|planned)\b")
_OPEN_WORDS = re.compile(
    r"\b(to be (clarified|confirmed|decided|determined|agreed)|tbc|tbd|open questions?"
    r"|unclear|unconfirmed|unknown|hypothes\w*|assum\w*|not yet (decided|confirmed|agreed))\b"
)


class Note(object):
    """One checked note: what the material says, in its own words, and where."""

    __slots__ = ("id",) + _FIELDS

    def __init__(self, row, id=None):
        self.id = id
        for field in _FIELDS:
            setattr(self, field, row.get(field, "" if field != "source" else 0))

    def row(self) -> dict:
        return dict((field, getattr(self, field)) for field in _FIELDS)

    @property
    def settled(self) -> bool:
        return self.status == SETTLED

    def __repr__(self) -> str:
        return "Note(%s, S%s, %s, %s)" % (self.id, self.source, self.kind, self.status)


def even_out(text: str) -> str:
    """Text as a quote is matched against its file.

    The same words, read the same way whatever a file did to them: letters
    in one form, curly quotation marks and every dash made plain, the marks
    of emphasis, tables, headings and lists taken out, letter case folded,
    and every run of spacing and line breaks made one space.
    """
    return evened_with_places(text)[0]


_LIST_MARK = re.compile(r"(?m)^[ \t]*(?:[-+*]|\d+[.)])[ \t]+")
_RULE_MARK = re.compile(r"(?<=\s)-{3,}(?=\s)")
_DROPPED = set("*_`~")
_AS_SPACE = set("|>#")
_TIGHT = set(".,;:!?")


def evened_with_places(text: str):
    """The evened text, and for each of its characters the place in `text`
    it came from, so a match can be read back as the file's own words."""
    import unicodedata

    raw = str(text or "")
    blank = set()
    for pattern in (_LIST_MARK, _RULE_MARK):
        for match in pattern.finditer(raw):
            blank.update(range(match.start(), match.end()))
    out: List[str] = []
    places: List[int] = []
    for index, character in enumerate(raw):
        pieces = " " if index in blank else unicodedata.normalize("NFKC", character)
        for piece in pieces:
            piece = piece.translate(_PLAIN_MARKS)
            if piece in _DROPPED:
                continue
            if piece in _AS_SPACE or piece.isspace():
                piece = " "
            for folded in piece.casefold():
                if folded == " ":
                    if not out or out[-1] == " ":
                        continue
                elif folded in _TIGHT and out and out[-1] == " ":
                    out.pop()
                    places.pop()
                out.append(folded)
                places.append(index)
    while out and out[-1] == " ":
        out.pop()
        places.pop()
    return "".join(out), places


_PLAIN_MARKS = dict(
    (ord(mark), plain)
    for mark, plain in (
        ("‘", "'"),
        ("’", "'"),
        ("‚", "'"),
        ("‛", "'"),
        ("“", '"'),
        ("”", '"'),
        ("„", '"'),
        ("‐", "-"),
        ("‑", "-"),
        ("‒", "-"),
        ("–", "-"),
        ("—", "-"),
        ("―", "-"),
        ("−", "-"),
        (" ", " "),
    )
)


def notes_lines(text: str) -> Optional[List[str]]:
    """The lines inside the notes' fence, or None when there is no fence."""
    lines = str(text or "").split("\n")
    opening = None
    for index, line in enumerate(lines):
        if re.match(r"^\s*```+\s*(jsonl|json)?\s*$", line):
            opening = index
            break
    if opening is None:
        return None
    for index in range(len(lines) - 1, opening, -1):
        if re.match(r"^\s*```+\s*$", lines[index]):
            return lines[opening + 1 : index]
    return None


def _sections(text: str):
    """A file as its headed sections: every heading above, and the text under."""
    sections = []
    chain: List[tuple] = []
    body: List[str] = []
    for line in str(text or "").split("\n"):
        match = re.match(r"^\s{0,3}(#{1,6})\s", line)
        if match:
            sections.append(([title for _level, title in chain], "\n".join(body)))
            level = len(match.group(1))
            chain = [(lvl, title) for lvl, title in chain if lvl < level] + [(level, line)]
            body = [line]
            continue
        body.append(line)
    sections.append(([title for _level, title in chain], "\n".join(body)))
    return sections


def _where(evened_quote: str, body: str):
    """The paragraph and the sentence a quote sits in, inside one section."""
    for paragraph in re.split(r"\n\s*\n", body):
        if evened_quote and evened_quote in even_out(paragraph):
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                if evened_quote in even_out(sentence):
                    return paragraph, sentence
            return paragraph, paragraph
    return "", ""


def _firmest(said: str, sentence: str) -> str:
    floor = SETTLED
    folded = said.casefold()
    if _PROPOSED_WORDS.search(folded):
        floor = PROPOSED
    if _ON_HOLD_WORDS.search(folded):
        floor = ON_HOLD
    if _OPEN_WORDS.search(folded) or "?" in sentence:
        floor = OPEN
    return floor


def floor_status(status: str, quote: str, whole_text: str) -> str:
    """The firmest status the material's own words allow for one note.

    The words of the quote count, and so do the sentence and paragraph it
    sits in and every heading above it, so a figure under a heading that says
    paused is paused however plainly it is stated (the replay of 2026-10-10,
    case two). Where the same words sit in more than one place, the least
    settled of those places counts.
    """
    evened_quote = even_out(quote)
    floor = _firmest(quote, quote)
    for headings, body in _sections(whole_text):
        paragraph, sentence = _where(evened_quote, body)
        if not paragraph:
            continue
        found = _firmest(" \n ".join([quote, paragraph] + headings), sentence + " " + quote)
        if _FIRMNESS[found] < _FIRMNESS[floor]:
            floor = found
    return status if _FIRMNESS[status] <= _FIRMNESS[floor] else floor


def _section_headings(evened_quote: str, whole_text: str) -> List[str]:
    """Every heading above the first place the words sit."""
    for headings, body in _sections(whole_text):
        if _where(evened_quote, body)[0]:
            return headings
    return []


class BatchChecked(object):
    """What came of checking one batch's notes."""

    __slots__ = ("rows", "problems", "not_noted")

    def __init__(self, rows, problems, not_noted):
        self.rows = rows
        self.problems = problems
        self.not_noted = not_noted


def check_batch(
    text: str, batch: Batch, screen, segment_names: Sequence[str] = ()
) -> BatchChecked:
    """Check one batch's notes against the files the batch read.

    Every refusal names the line of the notes and what is wrong with it,
    and never the words, the customer or the figure, because those are the
    company's own. `screen` is the check every draft goes through for
    contact details and keys, handed in so this module needs nothing of the
    setup flow.
    """
    lines = notes_lines(text)
    if lines is None:
        # Nothing could be read, so every file of the batch is not noted.
        return BatchChecked(
            [], [CODE_NO_FENCE], [(number, CODE_NO_FENCE) for number in batch.numbers]
        )
    whole = {}
    for part in batch.parts:
        whole[part.number] = part.original.text
    evened = dict((number, evened_with_places(text)) for number, text in whole.items())
    rows: List[dict] = []
    problems: List[str] = []
    not_noted: List[tuple] = []
    noted = set()
    line_number = 0
    unplaced = False
    for raw in lines:
        if not raw.strip():
            continue
        line_number += 1
        found, code = _one_note(raw, whole, evened, screen, segment_names)
        if code:
            problems.append("note-%d:%s" % (line_number, code))
            source = found.get("source") if isinstance(found, dict) else None
            if isinstance(source, int) and source in whole:
                not_noted.append((source, code))
            else:
                unplaced = True
            continue
        noted.add(found["source"])
        if found["kind"] != KIND_NOTHING:
            rows.append(found)
    for number in batch.numbers:
        if number not in noted:
            problems.append("%s:S%d" % (CODE_FILE_NOT_NOTED, number))
            not_noted.append((number, CODE_FILE_NOT_NOTED))
    if unplaced:
        # A line that could not be read says nothing about which file it
        # was for, so every file of the batch may be missing something.
        for number in batch.numbers:
            not_noted.append((number, CODE_UNREADABLE_LINE))
    return BatchChecked(rows, problems, not_noted)


def _one_note(raw: str, whole, evened, screen, segment_names=()):
    try:
        row = json.loads(raw)
    except ValueError:
        return None, "not-a-note"
    if not isinstance(row, dict):
        return None, "not-a-note"
    source = row.get("source")
    if isinstance(source, str) and re.match(r"^S?\d+$", source.strip()):
        source = int(source.strip().lstrip("S"))
    if not isinstance(source, int) or isinstance(source, bool):
        return row, "no-file-number"
    row["source"] = source
    if source not in whole:
        return row, "not-in-this-batch"
    kind = row.get("kind")
    if kind not in KINDS:
        return row, "unknown-kind"
    if kind == KIND_NOTHING:
        return {"source": source, "kind": KIND_NOTHING}, None
    clean = {"source": source, "kind": kind}
    for field in ("segment", "customer", "figure", "status", "quote"):
        value = row.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            return row, "not-a-note"
        clean[field] = value.strip()
    if clean["status"] not in STATUSES:
        return row, "unknown-status"
    quote = clean["quote"]
    if not quote:
        return row, "no-quote"
    if len(quote) > QUOTE_MAX:
        return row, "quote-too-long"
    for field in ("customer", "figure"):
        if _MARKUP.search(clean[field]):
            return row, "markup-in-a-field"
    found = screen(quote)
    if found:
        return row, "screened-%s" % found[0]
    evened_quote = even_out(quote)
    evened_file, places = evened[source]
    at = evened_file.find(evened_quote) if evened_quote else -1
    if at < 0:
        return row, "quote-not-in-file"
    # What is kept is the file's own words where the quote matched, never
    # the copy, so a disguised address or key is screened as the file has it.
    span = whole[source][places[at] : places[at + len(evened_quote) - 1] + 1]
    if re.search(r"\n[ \t]*[|#]|\|[ \t]*\n|\n[ \t]*\n", span):
        return row, "quote-spans-rows"
    kept = re.sub(r"\s+", " ", span).strip()
    if "```" in kept or "[[" in kept or "]]" in kept:
        return row, "quote-holds-markup"
    for text in (kept, re.sub(r"[*_`~]", "", _plain(kept))):
        found = screen(text)
        if found:
            return row, "screened-%s" % found[0]
    if kind == KIND_CUSTOMER and not clean["customer"]:
        return row, "no-customer"
    if clean["customer"] and even_out(clean["customer"]) not in evened_quote:
        return row, "customer-not-in-quote"
    if clean["figure"] and even_out(clean["figure"]) not in evened_quote:
        return row, "figure-not-in-quote"
    if kind == KIND_SEGMENT and not clean["segment"]:
        return row, "no-segment"
    settled = dict((_slug(name), name) for name in segment_names)
    if clean["segment"]:
        if _slug(clean["segment"]) in settled:
            clean["segment"] = settled[_slug(clean["segment"])]
        elif _MARKUP.search(clean["segment"]) or even_out(clean["segment"]) not in evened_quote:
            # A segment is one the person settled, or a name the file's own
            # words hold, and nothing else reaches the base as a label.
            return row, "unknown-segment"
    if kind in (KIND_CUSTOMER, KIND_SEGMENT) and settled:
        named = [
            name
            for slug, name in settled.items()
            if any(even_out(name) in even_out(title) for title in _section_headings(evened_quote, whole[source]))
        ]
        # A note naming no segment is placed by its page later; one naming a
        # segment its own heading does not is credited to the wrong one.
        if named and clean["segment"] and clean["segment"] not in named:
            return row, "segment-not-its-section"
    clean["quote"] = kept
    clean["status"] = floor_status(clean["status"], kept, whole[source])
    return clean, None


def _plain(text: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKC", text).translate(_PLAIN_MARKS)


def _slug(name: str) -> str:
    from . import segments

    return segments.slug_for(name)


# --- The notes a draft reads (U3) ---------------------------------------------

CODE_NOTES_CAPPED = "notes-capped"
COMPANY_WIDE = "the whole company"


class Rendered(object):
    """The notes one draft reads, as text, and what had to be shortened."""

    __slots__ = ("text", "ids", "shortened", "dropped")

    def __init__(self, text, ids, shortened, dropped):
        self.text = text
        self.ids = list(ids)
        self.shortened = list(shortened)
        self.dropped = list(dropped)

    @property
    def codes(self) -> List[str]:
        return [CODE_NOTES_CAPPED] if self.dropped else []


def _note_line(note: Note, with_words: bool = True) -> str:
    said = ["from S%d" % note.source, note.kind]
    if note.customer:
        said.append("customer: %s" % note.customer)
    if note.figure:
        said.append("figure: %s" % note.figure)
    said.append(note.status)
    words = '"%s"' % note.quote if with_words else "(words held back)"
    return "- %s (%s) %s" % (note.id, "; ".join(said), words)


def group_notes(
    found: Sequence[Note], order: Sequence[str] = (), company_first: bool = True
) -> List[tuple]:
    """Notes grouped by what they are about: the whole company, then each segment.

    Segments come in the order given, then any other segment the notes name in
    the order they first appear, so notes about one thing sit side by side and
    a disagreement in the material is seen as one.
    """
    names: List[str] = [""] if company_first else []
    for name in order:
        if name not in names:
            names.append(name)
    if "" not in names:
        names.append("")
    for item in found:
        if item.segment not in names:
            names.append(item.segment)
    return [
        (name, [item for item in found if item.segment == name])
        for name in names
        if any(item.segment == name for item in found)
    ]


def render_for_draft(
    found: Sequence[Note],
    order: Sequence[str],
    fence,
    limit: int,
    company_first: bool = True,
) -> Rendered:
    """The notes as one draft reads them, fenced by `fence`, within `limit`.

    All of them, with their words, when they fit. When they do not, the
    customer notes lose their words first, because setup writes the list of
    customers itself from the notes, words and all. Only when that is not
    enough are notes left out, from the end, and the draft is told so.
    """
    shortened: List[str] = []
    dropped: List[str] = []
    kept = list(found)

    def text_for(items, short):
        blocks = []
        for name, members in group_notes(items, order, company_first):
            title = "Notes about %s:" % (name or COMPANY_WIDE)
            lines = [
                _note_line(item, not (item.id in short and item.kind == KIND_CUSTOMER))
                for item in members
            ]
            blocks.append(title + "\n" + "\n".join(lines))
        return fence("\n\n".join(blocks) if blocks else "There are no notes.")

    text = text_for(kept, set())
    if len(text) > limit:
        shortened = [item.id for item in kept if item.kind == KIND_CUSTOMER]
        text = text_for(kept, set(shortened))
    while len(text) > limit and kept:
        # Leave out about as much as the overshoot from the end, then look again.
        over = len(text) - limit
        while over > 0 and kept:
            item = kept.pop()
            dropped.insert(0, item.id)
            over -= len(_note_line(item, item.id not in shortened)) + 1
        text = text_for(kept, set(shortened))
    return Rendered(text, [item.id for item in kept], shortened, dropped)
