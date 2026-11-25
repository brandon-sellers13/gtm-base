"""Digests of the notes, for a draft whose notes do not fit one request.

The summarize-first stage reads every file into checked notes, and every
draft is written from them. The case three rehearsal of 2026-11-24 found
that the notes are about as large as the files they come from, because each
note carries the file's own words, so a draft whose notes did not fit one
request was written with whole segments left out from the end of the list.

So when the notes do not fit, setup condenses the fewest groups it can,
largest first: a group is the notes about one segment, or about the whole
company. In a condensed group every customer note and every segment note
still reaches the draft, as a short line setup writes itself, and the fact
notes are condensed by the assistant into short lines that each cite the
notes they rest on. Setup checks every line here before any draft reads it:
what it cites, its status, its figures and customers, contact details, its
length, and that every note the material leaves open is carried.

Drafts still cite the notes, never a digest line, so review, the support
check and the sections setup writes itself read the notes as before.
Nothing here talks to a model, and a refusal names where a problem is,
never the words.
"""

import hashlib
import json
import re
from typing import Dict, List, Optional, Sequence

from . import citations, constants, notes as notes_module

# A digest is planned at no more than this share of the facts it condenses,
# so the plan condenses enough groups for the draft to fit.
PLANNED_SHARE = 0.25
# The least room one digest batch is ever given, so a group is never asked
# for a digest too small to carry what the material leaves open.
ROOM_FLOOR = 2000
# The longest one digest line may be.
LINE_MAX = 300
# How many times one digest batch is checked before what held up is kept.
ATTEMPTS = 3

CODE_DIGESTS_WAITING = "digests-waiting"
CODE_NO_SUCH_DIGEST = "no-such-digest"
CODE_NOT_THE_DIGEST_FILE = "not-the-digest-file"
CODE_NOTES_CONDENSED = "notes-condensed"
CODE_NOTES_OVER = "notes-over-the-limit"

# What a digest line may never hold: line breaks and the marks that build a
# heading, a table, a link, a fence, a tag, or a citation of its own.
_MARKUP = re.compile(r"[\n\r`#|<>\[\]{}]")


class DigestRefused(notes_module.NotesRefused):
    """A step of condensing the notes that could not be done."""

    default_code = "digest-refused"


# --- Which groups are condensed, and how much room each has (D1) -------------


def _kept_line(note) -> str:
    """A customer or segment note as setup writes it into a condensed group.

    A segment note keeps its words, which are short and say what the segment
    is. A customer note keeps its name and status and not its words, which
    setup writes into the evidence for its segment beside the footnote.
    """
    return notes_module._note_line(note, note.kind != notes_module.KIND_CUSTOMER)


def _fact_line(note) -> str:
    return notes_module._note_line(note, True)


def _title(name: str, condensed: bool) -> str:
    said = name or notes_module.COMPANY_WIDE
    if condensed:
        return "Notes about %s (the facts condensed into shorter lines):" % said
    return "Notes about %s:" % said


def _raw_block(name: str, members) -> str:
    return _title(name, False) + "\n" + "\n".join(_fact_line(item) for item in members)


def _facts(members) -> list:
    return [item for item in members if item.kind == notes_module.KIND_FACT]


def _kept(members) -> list:
    return [item for item in members if item.kind != notes_module.KIND_FACT]


def _kept_size(name: str, members) -> int:
    lines = [_title(name, True)] + [_kept_line(item) for item in _kept(members)]
    return sum(len(line) + 1 for line in lines)


def _facts_size(members) -> int:
    return sum(len(_fact_line(item)) + 1 for item in _facts(members))


class DigestBatch(object):
    """One request's worth of one group's facts, and the room its digest has."""

    __slots__ = ("number", "group", "notes", "room")

    def __init__(self, number, group, found, room):
        self.number = number
        self.group = group
        self.notes = list(found)
        self.room = int(room)

    @property
    def ids(self) -> List[str]:
        return [item.id for item in self.notes]

    @property
    def must_carry(self) -> List[str]:
        """The notes the material does not settle, which a digest always keeps."""
        return [item.id for item in self.notes if not item.settled]

    @property
    def digest(self) -> str:
        held = [self.group, str(self.room)] + [
            "%s|%s|%s|%s" % (item.id, item.status, item.figure, item.quote)
            for item in self.notes
        ]
        return hashlib.sha256("\n".join(held).encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return "DigestBatch(%d, group=%r, notes=%d, room=%d)" % (
            self.number, self.group, len(self.notes), self.room,
        )


class DigestPlan(object):
    """The groups condensed for this run, largest first, and their batches."""

    __slots__ = ("groups", "batches")

    def __init__(self, groups, batches):
        self.groups = list(groups)
        self.batches = list(batches)

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            "\n".join(batch.digest for batch in self.batches).encode("utf-8")
        ).hexdigest()

    def batch(self, number) -> DigestBatch:
        for batch in self.batches:
            if str(batch.number) == str(number):
                return batch
        raise DigestRefused("there is no digest with that number", CODE_NO_SUCH_DIGEST)

    def __repr__(self) -> str:
        return "DigestPlan(groups=%d, batches=%d)" % (len(self.groups), len(self.batches))


def plan(found, order: Sequence[str], fence, limit: int) -> DigestPlan:
    """Which groups to condense so a draft reading every note fits `limit`.

    None when every note fits as it is. Otherwise the largest groups are
    condensed first, one at a time, until the notes left whole, the lines
    setup writes for the condensed groups, and digests a quarter the size of
    the facts they condense would fit. The room left is shared among the
    condensed groups by the size of their facts, and a group whose facts do
    not fit one request is condensed in batches that each do.
    """
    groups = notes_module.group_notes(found, order)
    whole = fence("\n\n".join(_raw_block(name, members) for name, members in groups))
    if len(whole) <= limit:
        return DigestPlan([], [])
    overhead = len(fence("")) + 2 * len(groups)
    raw = dict((name, len(_raw_block(name, members)) + 2) for name, members in groups)
    by_size = sorted(groups, key=lambda group: (-raw[group[0]], groups.index(group)))
    chosen: List[tuple] = []

    def estimate(picked) -> float:
        names = set(name for name, _members in picked)
        return (
            overhead
            + sum(raw[name] for name, _members in groups if name not in names)
            + sum(_kept_size(name, members) + PLANNED_SHARE * _facts_size(members) for name, members in picked)
        )

    for group in by_size:
        if estimate(chosen) <= limit:
            break
        chosen.append(group)
    names = set(name for name, _members in chosen)
    room = (
        limit
        - overhead
        - sum(raw[name] for name, _members in groups if name not in names)
        - sum(_kept_size(name, members) for name, members in chosen)
    )
    facts_total = sum(_facts_size(members) for _name, members in chosen) or 1
    batches: List[DigestBatch] = []
    # Numbered in the order the draft reads the groups, so the numbers are
    # the same whichever group happened to be largest.
    in_order = [group for group in groups if group[0] in names]
    request_room = limit - len(fence(""))
    for name, members in in_order:
        facts = _facts(members)
        if not facts:
            continue
        share = max(room, 0) * _facts_size(members) / facts_total
        parts: List[list] = [[]]
        used = 0
        for item in facts:
            size = len(_fact_line(item)) + 1
            if parts[-1] and used + size > request_room:
                parts.append([])
                used = 0
            parts[-1].append(item)
            used += size
        size_of_group = _facts_size(members) or 1
        for part in parts:
            part_room = int(share * _facts_size(part) / size_of_group)
            batches.append(
                DigestBatch(len(batches) + 1, name, part, max(part_room, ROOM_FLOOR))
            )
    return DigestPlan([name for name, _members in chosen], batches)


# --- The request for one digest (D2) -----------------------------------------


def assemble(template: str, batch: DigestBatch, company: str, group_block: str, total: int, fence) -> str:
    """The request for one digest batch, out of the digest prompt."""
    values = {
        "company": company,
        "group": group_block,
        "batch": "%d of %d" % (batch.number, total),
        "room": "{:,}".format(batch.room),
        "carry": str(len(batch.must_carry)),
        "notes": fence("\n".join(_fact_line(item) for item in batch.notes)),
    }
    return re.sub(
        r"\{\{(%s)\}\}" % "|".join(values),
        lambda match: values[match.group(1)],
        template,
    )


# --- Checking one digest (D3) ------------------------------------------------


class DigestChecked(object):
    """What came of checking one digest: the lines that held, and what did not."""

    __slots__ = ("rows", "problems", "uncarried")

    def __init__(self, rows, problems, uncarried):
        self.rows = rows
        self.problems = problems
        self.uncarried = uncarried


def _weakest(statuses) -> str:
    return min(statuses, key=lambda status: notes_module._FIRMNESS[status])


def check(text: str, batch: DigestBatch, screen, customers: Sequence[str]) -> DigestChecked:
    """Check one digest against the notes its batch condenses.

    `screen` is the check every draft goes through for contact details and
    keys, and `customers` are the names the notes give customers, as
    `citations.customer_names` finds them.
    """
    lines = notes_module.notes_lines(text)
    if lines is None:
        return DigestChecked([], [notes_module.CODE_NO_FENCE], batch.must_carry)
    by_id = dict((item.id, item) for item in batch.notes)
    rows: List[dict] = []
    problems: List[str] = []
    number = 0
    for raw in lines:
        if not raw.strip():
            continue
        number += 1
        row, code = _one_line(raw, by_id, screen, customers)
        if code:
            problems.append("line-%d:%s" % (number, code))
            continue
        rows.append(row)
    carried = set(note_id for row in rows for note_id in row["notes"])
    uncarried = [note_id for note_id in batch.must_carry if note_id not in carried]
    problems.extend("%s:%s" % ("open-note-not-carried", note_id) for note_id in uncarried)
    # The words the request asks to fit its room, as it says them. The note
    # numbers and status setup adds to each line are its own to fit, and the
    # last resort in render keeps a draft inside the limit whatever they add.
    used = sum(len(row["line"]) for row in rows)
    if used > batch.room:
        problems.append("over-its-room")
    return DigestChecked(rows, problems, uncarried)


def _one_line(raw: str, by_id: Dict[str, object], screen, customers):
    try:
        row = json.loads(raw)
    except ValueError:
        return None, "not-a-line"
    if not isinstance(row, dict):
        return None, "not-a-line"
    line = row.get("line")
    cited = row.get("notes")
    status = row.get("status")
    if not isinstance(line, str) or not line.strip():
        return None, "no-line"
    line = " ".join(line.split())
    if len(line) > LINE_MAX:
        return None, "line-too-long"
    if _MARKUP.search(line):
        return None, "markup-in-a-line"
    if isinstance(cited, str):
        cited = [cited]
    if not isinstance(cited, list) or not cited or not all(isinstance(i, str) for i in cited):
        return None, "cites-no-note"
    cited = [note_id.strip() for note_id in cited]
    if any(note_id not in by_id for note_id in cited):
        return None, "cites-a-note-not-in-this-digest"
    own = [by_id[note_id] for note_id in cited]
    if status not in notes_module.STATUSES:
        return None, "unknown-status"
    weakest = _weakest([item.status for item in own])
    if notes_module._FIRMNESS[status] > notes_module._FIRMNESS[weakest]:
        return None, "firmer-than-its-notes"
    for figure in citations._figures(line):
        if not any(citations._figure_in(figure, item.quote) for item in own):
            return None, "figure-not-in-its-notes"
    for name in customers:
        if citations._names_in(line, [name]) and not any(
            item.customer == name or citations._names_in(item.quote, [name]) for item in own
        ):
            return None, "customer-not-in-its-notes"
    found = screen(line)
    if found:
        return None, "screened-%s" % found[0]
    return {"line": line, "notes": cited, "status": status}, None


def carried_by_setup(batch: DigestBatch, uncarried: Sequence[str]) -> List[dict]:
    """The lines setup writes itself, after the third refusal, for every note
    the material leaves open that no line carried: the material's own words,
    shortened only when they must be, so nothing open is lost to a loop."""
    by_id = dict((item.id, item) for item in batch.notes)
    rows = []
    for note_id in uncarried:
        item = by_id.get(note_id)
        if item is None:
            continue
        words = " ".join(str(item.quote).split())
        if len(words) > LINE_MAX - 2:
            words = words[: LINE_MAX - 5].rstrip() + "..."
        rows.append({"line": '"%s"' % words, "notes": [note_id], "status": item.status, "by": "setup"})
    return rows


# --- What a draft reads (D4) --------------------------------------------------


class DigestRendered(notes_module.Rendered):
    """The notes one draft reads, with which groups were condensed."""

    __slots__ = ("condensed", "folded", "over")

    def __init__(self, text, ids, shortened, dropped, condensed, folded):
        notes_module.Rendered.__init__(self, text, ids, shortened, dropped)
        self.condensed = list(condensed)
        self.folded = int(folded)
        # Whether the request is still over the limit with nothing left that
        # may be taken out: what condensed groups must always carry.
        self.over = False

    @property
    def codes(self) -> List[str]:
        codes = [CODE_NOTES_CONDENSED] if self.condensed else []
        codes += notes_module.Rendered.codes.fget(self)
        return codes + ([CODE_NOTES_OVER] if self.over else [])


def _digest_line(row: dict) -> str:
    return "- %s [%s] (%s)" % (row["line"], ", ".join(row["notes"]), row["status"])


def render(found, order, fence, limit: int, digest_plan: DigestPlan,
           lines_by_group: Dict[str, List[dict]], company_first: bool = True) -> DigestRendered:
    """The notes as one draft reads them, condensing planned groups as needed.

    Every group is read whole when everything fits. Otherwise the groups the
    plan condensed are read condensed, largest first, until it fits. A digest
    line is read only when every note it cites is one this draft may read,
    and any note the material leaves open that no line it may read carries
    is carried by setup in the material's own words, so a draft narrowed to
    some files never reads past them and never loses an open note.

    If it still does not fit, the last resort goes in this order, each step
    only as far as it must (the correctness review of 2026-11-24, findings 1
    and 2): settled shorter lines, from the group holding the most; the
    words of customer notes in groups read whole; settled facts in groups
    read whole, from the end; and only then anything else in groups read
    whole, from the end. A customer or segment line in a condensed group, and
    a line the material leaves open, are never left out. What is left out is
    named in `dropped`, and a request still over the limit says so.
    """
    groups = notes_module.group_notes(found, order, company_first)
    in_view = set(item.id for item in found)
    condensed: List[str] = []
    rows_for: Dict[str, List[dict]] = {}
    for name, members in groups:
        rows = [
            row for row in lines_by_group.get(name, [])
            if all(note_id in in_view for note_id in row["notes"])
        ]
        carried = set(note_id for row in rows for note_id in row["notes"])
        facts = _facts(members)
        missing = [item.id for item in facts if not item.settled and item.id not in carried]
        if missing:
            rows = rows + carried_by_setup(DigestBatch(0, name, facts, 0), missing)
        rows_for[name] = rows
    short = set()
    left: List[str] = []

    def whole_block(name, members) -> Optional[str]:
        kept = [item for item in members if item.id not in left]
        if not kept:
            return None
        return _title(name, False) + "\n" + "\n".join(
            notes_module._note_line(item, item.id not in short) for item in kept
        )

    def text() -> str:
        out = []
        for name, members in groups:
            if name in condensed:
                lines = [_title(name, True)] + [_kept_line(item) for item in _kept(members)]
                lines += [_digest_line(row) for row in rows_for[name]]
                out.append("\n".join(lines))
            else:
                block = whole_block(name, members)
                if block is not None:
                    out.append(block)
        return fence("\n\n".join(out) if out else "There are no notes.")

    names = [name for name, _members in groups]
    for name in digest_plan.groups:
        if len(text()) <= limit:
            break
        if name in names:
            condensed.append(name)

    folded = 0
    for name, members in groups:
        if name in condensed:
            cited = set(note_id for row in rows_for[name] for note_id in row["notes"])
            folded += sum(1 for item in _facts(members) if item.settled and item.id not in cited)

    dropped: List[str] = []
    rendered = text()

    def shed(candidates, take):
        """Take candidates out from the end, about as many as the overshoot."""
        nonlocal rendered
        while len(rendered) > limit and candidates:
            over = len(rendered) - limit
            while over > 0 and candidates:
                over -= take(candidates.pop())
            rendered = text()

    # 1. Settled shorter lines, from the group holding the most.
    def most_settled():
        holding = [
            name for name in condensed
            if any(row["status"] == notes_module.SETTLED for row in rows_for[name])
        ]
        return max(holding, key=lambda name: len(rows_for[name])) if holding else None

    while len(rendered) > limit:
        over = len(rendered) - limit
        gone = []
        while over > 0:
            name = most_settled()
            if name is None:
                break
            rows = rows_for[name]
            last = max(i for i, row in enumerate(rows) if row["status"] == notes_module.SETTLED)
            row = rows.pop(last)
            gone.append(row)
            over -= len(_digest_line(row)) + 1
        if not gone:
            break
        still = set(n for name in condensed for row in rows_for[name] for n in row["notes"])
        dropped.extend(
            n for row in gone for n in row["notes"] if n not in still and n not in dropped
        )
        rendered = text()

    whole = [item for name, members in groups if name not in condensed for item in members]
    # 2. The words of customer notes in groups read whole.
    if len(rendered) > limit:
        short.update(item.id for item in whole if item.kind == notes_module.KIND_CUSTOMER)
        rendered = text()

    def take_note(item) -> int:
        left.append(item.id)
        dropped.append(item.id)
        return len(notes_module._note_line(item, item.id not in short)) + 1

    # 3. Settled facts in groups read whole, from the end.
    shed([item for item in whole if item.kind == notes_module.KIND_FACT and item.settled], take_note)
    # 4. Anything else in groups read whole, from the end.
    shed([item for item in whole if item.id not in left], take_note)

    ids: List[str] = []
    for name, members in groups:
        if name in condensed:
            ids.extend(item.id for item in _kept(members))
            cited = set(note_id for row in rows_for[name] for note_id in row["notes"])
            ids.extend(item.id for item in _facts(members) if item.id in cited)
        else:
            ids.extend(item.id for item in members if item.id not in left)
    result = DigestRendered(rendered, ids, sorted(short), dropped, condensed, folded)
    result.over = len(rendered) > limit
    return result
