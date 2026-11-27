"""What a base holds, and what it is missing, for each business it covers.

Unit 2.1 of Plan 1 (requirements P30 and P40). A person asks "what is my base
missing?" and gets one small table: each kind of document on the named list
(`constants.BASE_KINDS`), for each business the base's map lists, with
whether the base has it and the day its owner last confirmed it. A map that
lists no business gets one column for the whole company, exactly as a base
before Plan 1 would.

It reads and never writes. Nothing here records a refused path, asks a
question that could be answered, or keeps anything on this seat, and it
offers to draft only a kind this release can draft, saying for the rest that
drafting arrives later.

A document belongs to the business of the folder it sits in under `context`,
or to the business its settings name (`businesses.document_business`). For a
kind that differs by business, a flat document that names no business counts
for none of them and is listed once, so nobody is told the courier app has a
positioning when the only positioning was written for another business. A
kind one document serves for the whole company (the voice guide, the design
guide, the source map, a standard, a skill) needs no business line.

Every document is read once, here, and the same reading decides both what the
table says about it and what the stale library is handed to work out its
confirmation, so the two cannot describe two different files.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Dict, List, Optional, Tuple

from . import (
    base_reader,
    businesses,
    callmarkers,
    constants,
    docpaths,
    formats,
    layout,
    names,
    stale,
    state,
    validate,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import read_text
from .gitcmd import GitRunner, runner_or_default

# What one cell of the table can say about one kind for one business.
STATE_PRESENT = "present"
STATE_MISSING = "missing"
STATE_SKIPPED = "skipped"
STATE_UNREADABLE = "unreadable"

# The sentences a person reads. None of them is filled from a file name or a
# business's name; those appear only inside the table, held apart as data.
PURPOSE = (
    "This shows what your base holds against the list of documents a base can "
    "have, for each business it covers, so you can see what is missing."
)
NOT_STATED = (
    "%s do not say which business they are for, so for now they count for "
    "no business."
)
NOT_STATED_ONE = (
    "One of your documents does not say which business it is for, so for now "
    "it counts for no business."
)
UNLISTED = (
    "%s are kept for a business your base's map does not list, so they count "
    "for no business."
)
UNLISTED_ONE = (
    "One of your documents is kept for a business your base's map does not "
    "list, so it counts for no business."
)
DISAGREE = (
    "%s sit in one business's folder while their settings name another, so "
    "they count for neither."
)
DISAGREE_ONE = (
    "One of your documents sits in one business's folder while its settings "
    "name another, so it counts for neither."
)
SETTING_LATER = (
    "Saying which business a document is for arrives in a later version of "
    "GTM Base."
)
BUSINESSES_UNREADABLE = (
    "The list of businesses in your base's map could not be read, so this is "
    "shown for the whole company."
)
DATES_UNREADABLE = (
    "When each document was last confirmed could not be read, so those days "
    "are left out."
)
SCOPE_FINDING = (
    "Your customer profile says it does not cover every business your base's "
    "map lists, which is a context change worth recording."
)
SCOPE_OFFER = "Shall I record that context change now?"
DRAFT_OFFER = "Shall I draft %s for you now?"
DRAFTING_LATER = (
    "Drafting what is missing arrives in a later version of GTM Base."
)
DRAFTING_LATER_REST = (
    "Drafting the rest of what is missing arrives in a later version of GTM "
    "Base."
)
NOTHING_MISSING = (
    "Your base holds every kind of document on the list for each business it "
    "covers."
)

# The words a cell is written in. A date is the day, as everywhere else.
CELL_MISSING = "missing"
CELL_UNREADABLE = "could not be read"
CELL_SKIPPED = "skipped"
CELL_HERE = "here"
CELL_CONFIRMED = "confirmed %s"
CELL_NOT_CONFIRMED = "here, not confirmed yet"
CELL_QUESTION_OPEN = "here, a question is still open"
CELL_SEVERAL = "%s here"
CELL_SEVERAL_CONFIRMED = "%s here, oldest confirmation %s"
CELL_SEVERAL_NOT_ALL = "%s here, not all confirmed"
COLUMN_KIND = "Kind"
COLUMN_WHOLE_COMPANY = "The whole company"

# Words in the first paragraph of the customer profile that say what follows
# is left out. The scope finding is an offer and writes nothing, so a phrase
# this misses costs one offer not made, and the table still shows the gap.
_LEFT_OUT_WORDS = (
    r"not",
    r"nor",
    r"excluding",
    r"except",
    r"other than",
    r"outside(?: of)?",
    r"apart from",
)
# How many words may stand between such a word and the business it leaves
# out, as in "and not the courier app".
_LEFT_OUT_REACH = 3
# What may stand between two words inside one clause.
_GAP = r"[^\w.;:!?]+"


class Document(object):
    """One document the inventory read, once."""

    __slots__ = (
        "path",
        "kind",
        "flat",
        "business",
        "doubt",
        "state",
        "fields",
        "body",
        "open_questions",
        "owners",
        "sources_date",
        "status",
    )

    def __init__(self, path: str, kind: str, flat: bool):
        self.path = path
        self.kind = kind
        self.flat = flat
        self.business: Optional[str] = None
        self.doubt: Optional[str] = None
        self.state = STATE_UNREADABLE
        self.fields: Dict = {}
        self.body = ""
        self.open_questions: Tuple[str, ...] = ()
        self.owners: List[str] = []
        self.sources_date = None
        self.status = ""

    def __repr__(self) -> str:
        return "Document(%r, %r, %r)" % (self.path, self.kind, self.state)


class Cell(object):
    """What the base holds of one kind for one business, or for the whole company."""

    __slots__ = ("documents", "confirmed_on", "confirmations_known")

    def __init__(self, documents, confirmed: Dict[str, datetime.date], known: bool):
        self.documents = list(documents)
        self.confirmations_known = known
        present = [one for one in self.documents if one.state == STATE_PRESENT]
        days = [confirmed.get(one.path) for one in present]
        # The oldest day, and only when every document here has one, because
        # a cell saying "confirmed" about two documents must be true of both.
        self.confirmed_on = (
            min(days) if days and all(day is not None for day in days) else None
        )

    @property
    def paths(self) -> List[str]:
        return [one.path for one in self.documents]

    @property
    def state(self) -> str:
        states = [one.state for one in self.documents]
        if not states:
            return STATE_MISSING
        for wanted in (STATE_PRESENT, STATE_UNREADABLE, STATE_SKIPPED):
            if wanted in states:
                return wanted
        return STATE_UNREADABLE

    @property
    def open_question(self) -> bool:
        return any(
            one.open_questions
            for one in self.documents
            if one.state == STATE_PRESENT
        )

    def text(self) -> str:
        """What the cell says, in fixed words, a count and a day, and nothing else."""
        state_now = self.state
        if state_now == STATE_MISSING:
            return CELL_MISSING
        if state_now == STATE_UNREADABLE:
            return CELL_UNREADABLE
        if state_now == STATE_SKIPPED:
            return CELL_SKIPPED
        present = [one for one in self.documents if one.state == STATE_PRESENT]
        if not self.confirmations_known:
            # Nothing is said about confirmation that was not read.
            if len(present) > 1:
                return CELL_SEVERAL % names.counted(len(present))
            return CELL_HERE
        if len(present) > 1:
            count = names.counted(len(present))
            if self.confirmed_on is not None:
                return CELL_SEVERAL_CONFIRMED % (count, self.confirmed_on.isoformat())
            return CELL_SEVERAL_NOT_ALL % count
        if self.open_question:
            return CELL_QUESTION_OPEN
        if self.confirmed_on is not None:
            return CELL_CONFIRMED % self.confirmed_on.isoformat()
        return CELL_NOT_CONFIRMED

    def __repr__(self) -> str:
        return "Cell(%r, %r)" % (self.state, self.paths)


class Inventory(object):
    """The whole answer: the table, the documents in doubt, and the one offer."""

    def __init__(self):
        self.businesses: List[businesses.Business] = []
        self.columns: List[str] = []
        self.kinds: List[str] = []
        self.cells: Dict[Tuple[str, str], Optional[Cell]] = {}
        self.not_stated: List[str] = []
        self.unlisted: List[str] = []
        self.disagree: List[str] = []
        self.scope_left_out: List[str] = []
        self.businesses_unreadable = False
        self.confirmations_unreadable = False
        self.draftable_missing: List[Tuple[str, str]] = []
        # The skills GTM Base ships that this base could take (Track 4, T4.8).
        self.starter_offers: List[str] = []

    def _column_heading(self, column: str) -> str:
        for business in self.businesses:
            if business.slug == column:
                return businesses.as_data(business)
        return COLUMN_WHOLE_COMPANY

    def table(self) -> str:
        """The table, one row per kind, which is only ever shown held apart as data."""
        headings = [COLUMN_KIND] + [self._column_heading(one) for one in self.columns]
        lines = [
            "| " + " | ".join(headings) + " |",
            "|" + "|".join("---" for _heading in headings) + "|",
        ]
        for kind in self.kinds:
            row = [names.KIND_LABELS[kind]]
            for column in self.columns:
                found = self.cells.get((kind, column))
                row.append(found.text() if found is not None else "")
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def _all_present(self) -> bool:
        return all(
            found.state == STATE_PRESENT
            for found in self.cells.values()
            if found is not None
        )

    def _missing_anywhere(self) -> bool:
        return any(
            found is not None and found.state == STATE_MISSING
            for found in self.cells.values()
        )

    def sentences(self) -> List[str]:
        """What is said after the table, in order, before the one offer."""
        said: List[str] = []
        if self.businesses_unreadable:
            said.append(BUSINESSES_UNREADABLE)
        if self.confirmations_unreadable:
            said.append(DATES_UNREADABLE)
        for listed, many, one in (
            (self.not_stated, NOT_STATED, NOT_STATED_ONE),
            (self.unlisted, UNLISTED, UNLISTED_ONE),
            (self.disagree, DISAGREE, DISAGREE_ONE),
        ):
            if len(listed) == 1:
                said.append(one)
            elif listed:
                said.append(
                    many
                    % names.how_many(
                        len(listed), "of your documents", "of your documents", start=True
                    )
                )
        if self.not_stated or self.unlisted or self.disagree:
            said.append(SETTING_LATER)
        if self.scope_left_out:
            said.append(SCOPE_FINDING)
        if self._all_present():
            said.append(NOTHING_MISSING)
        elif not self._missing_anywhere():
            # Skipped or unreadable, which the table says, and nothing to draft.
            pass
        elif not self.draftable_missing:
            said.append(DRAFTING_LATER)
        elif self._missing_beyond_what_drafts():
            said.append(DRAFTING_LATER_REST)
        said.extend(self.starter_offers)
        return said

    def _missing_beyond_what_drafts(self) -> bool:
        offered = set(self.draftable_missing)
        return any(
            found is not None
            and found.state == STATE_MISSING
            and key not in offered
            for key, found in self.cells.items()
        )

    def ask(self) -> Optional[str]:
        """The one thing this step asks, or nothing (the UX standard: one ask).

        Recording the scope change comes first, because a draft written while
        the profile still says the base covers less would be written against
        the wrong scope.
        """
        if self.scope_left_out:
            return SCOPE_OFFER
        if self.draftable_missing:
            kinds_named: List[str] = []
            for kind, _column in self.draftable_missing:
                said = names.KIND_IN_A_SENTENCE[kind]
                if said not in kinds_named:
                    kinds_named.append(said)
            if len(kinds_named) > 1:
                joined = ", ".join(kinds_named[:-1]) + " and " + kinds_named[-1]
            else:
                joined = kinds_named[0]
            return DRAFT_OFFER % joined
        return None


# --- Finding the documents ------------------------------------------------------


def _context_kinds() -> Dict[str, str]:
    """Each kind kept under `context`, by the file name it is kept under."""
    return {
        kind.pattern.split("/")[-1]: kind.key
        for kind in constants.BASE_KINDS
        if kind.pattern.startswith(constants.CONTEXT_DIR + "/")
        and kind.pattern.count("/") == 1
    }


def _kind_by_pattern() -> Dict[str, str]:
    return {kind.pattern: kind.key for kind in constants.BASE_KINDS}


def _found_in_context(base_root: str) -> List[Document]:
    """Every document under `context` that is one of the kinds, flat or in a folder.

    The walk never follows a link to a folder, the context folder itself
    included, and a link to a file is read as a file that could not be read,
    so nothing outside the base is ever opened. A document a base laid out the
    older way holds is read where it is, as the kind it is now, unless the
    current path holds it too: then the current path is the document, as
    `layout.where_it_lives` says everywhere else.
    """
    by_pattern = _kind_by_pattern()
    by_name = _context_kinds()
    found: List[Document] = []
    context_root = os.path.join(base_root, constants.CONTEXT_DIR)
    if os.path.islink(context_root):
        return found
    for dirpath, dirnames, filenames in os.walk(context_root):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            relative = os.path.relpath(os.path.join(dirpath, name), base_root)
            relative = relative.replace(os.sep, "/")
            current = layout.current_of(relative) or relative
            kind = by_pattern.get(current)
            if current != relative and os.path.lexists(
                os.path.join(base_root, current.replace("/", os.sep))
            ):
                continue
            if kind is not None:
                found.append(Document(relative, kind, flat=True))
                continue
            parts = relative.split("/")
            if (
                len(parts) == 3
                and parts[1] not in businesses.RESERVED_SLUGS
                and parts[2] in by_name
            ):
                found.append(Document(relative, by_name[parts[2]], flat=False))
    return found


def _is_plain_entry(base_root: str, relative: str) -> bool:
    name = relative.split("/")[-1]
    return not name.startswith(".") and os.path.lexists(
        os.path.join(base_root, relative.replace("/", os.sep))
    )


def _found_elsewhere(base_root: str) -> List[Document]:
    """The source map, every standard, and every skill, each where the layout keeps it."""
    found: List[Document] = []
    access_root = os.path.join(base_root, constants.ACCESS_DIR)
    if not os.path.islink(access_root) and os.path.lexists(
        os.path.join(base_root, constants.STACK_PATH)
    ):
        found.append(Document(constants.STACK_PATH, "stack", flat=True))
    standards_root = os.path.join(base_root, constants.STANDARDS_DIR)
    if os.path.isdir(standards_root) and not os.path.islink(standards_root):
        for name in sorted(os.listdir(standards_root)):
            relative = constants.STANDARDS_DIR + "/" + name
            if name.endswith(".md") and _is_plain_entry(base_root, relative):
                found.append(Document(relative, "standard", flat=True))
    skills_root = os.path.join(base_root, constants.SKILLS_DIR)
    if os.path.isdir(skills_root) and not os.path.islink(skills_root):
        for job in sorted(os.listdir(skills_root)):
            folder = os.path.join(skills_root, job)
            if job.startswith(".") or os.path.islink(folder) or not os.path.isdir(folder):
                continue
            relative = constants.SKILLS_DIR + "/" + job + "/SKILL.md"
            if _is_plain_entry(base_root, relative):
                found.append(Document(relative, "skill", flat=True))
    return found


def _read(base_root: str, one: Document) -> None:
    """Read one document once, and keep everything the table and the check need."""
    text = read_text(os.path.join(base_root, one.path.replace("/", os.sep)))
    if text is None:
        one.state = STATE_UNREADABLE
        return
    try:
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        fields, body = {}, text
    one.fields = fields
    one.body = body
    one.status = str(fields.get("status") or "")
    one.open_questions = callmarkers.questions(text)
    try:
        one.owners = validate.validate_owner(fields.get("owner"))
    except ValidationError:
        one.owners = []
    try:
        one.sources_date = base_reader.newest_date_in(fields.get("sources"))
    except Exception:
        one.sources_date = None
    one.state = STATE_SKIPPED if one.status == stale.STATUS_SKIPPED else STATE_PRESENT


# --- Confirmations ---------------------------------------------------------------


def _confirmed_on(
    base_root: str,
    base_id: str,
    documents: List[Document],
    git: GitRunner,
    day: datetime.date,
) -> Optional[Dict[str, datetime.date]]:
    """The day an owner last said each context document is right, or None.

    The stale library is handed the documents exactly as they were read here,
    so a confirmation is counted against the same text the table describes.
    Every document a confirmation can name is handed over, a standard and the
    source map included; a skill's files are not confirmed this way. Nothing
    that is read is recorded: a refused path comes back in a list and is let
    go.
    """
    files = [
        stale.ContextFileInfo(
            path=one.path,
            owners=one.owners,
            exists=True,
            sources_date=one.sources_date,
            status=one.status,
            kind=str(one.fields.get("kind") or ""),
            open_questions=one.open_questions,
        )
        for one in documents
        if one.state != STATE_UNREADABLE
        and docpaths.may(docpaths.classify(one.path), docpaths.OP_CONFIRM)
    ]
    try:
        inputs = base_reader.read_base(
            base_root, base_id, runner=git, today=day, record_dropped=False
        )
        report = stale.compute(
            today=day,
            settings=inputs.settings,
            files=files,
            ledger=inputs.ledger,
            confirmations=inputs.confirmations,
            corrections=inputs.corrections,
            seat=inputs.seat,
        )
    except (GtmBaseError, OSError):
        return None
    return dict(report.confirmed_on)


# --- The scope of the customer profile ----------------------------------------


def _first_paragraph(body: str) -> str:
    """The first block of plain lines under the profile's title."""
    lines: List[str] = []
    for raw in str(body or "").split("\n"):
        line = raw.strip()
        if not line:
            if lines:
                break
            continue
        if line.startswith("#"):
            if lines:
                break
            continue
        lines.append(line)
    return " ".join(lines)


def _words_for(business: businesses.Business) -> List[str]:
    """The ways a profile may name a business, as patterns over its words.

    Its short name as written and with its hyphens as spaces, and its name in
    the map without an opening "the". Each is held by lookarounds rather than
    word edges, so a name that ends in a full stop is still found.
    """
    said = [business.slug, business.slug.replace("-", " ")]
    if business.name:
        name = business.name.lower()
        said.append(name[4:] if name.startswith("the ") else name)
    patterns = []
    for one in said:
        pattern = r"(?<!\w)%s(?!\w)" % r"\s+".join(re.escape(word) for word in one.split())
        if pattern not in patterns:
            patterns.append(pattern)
    return patterns


def _names(business: businesses.Business, text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in _words_for(business))


def _leaves_out(business: businesses.Business, text: str) -> bool:
    lowered = text.lower()
    for pattern in _words_for(business):
        for word in _LEFT_OUT_WORDS:
            # "Not only" and "not just" bring a business in rather than leave
            # it out.
            # The words between stay inside one clause: a full stop, a
            # semicolon or a colon ends what the negation can reach.
            if re.search(
                r"\b%s\b(?!\s+(?:only|just)\b)(?:%s\w+){0,%d}?%s%s"
                % (word, _GAP, _LEFT_OUT_REACH, _GAP, pattern),
                lowered,
            ):
                return True
    return False


def _scope_left_out(
    profile: Optional[Document], listed: List[businesses.Business]
) -> List[str]:
    """The listed businesses the customer profile says it does not cover.

    A profile that says which business it is for has a scope of its own and
    raises nothing. Otherwise its `covers` setting, written by setup from the
    person's own answer, decides; and when it has none, its first paragraph is
    read for a business it says it leaves out.
    """
    if profile is None or profile.state != STATE_PRESENT or not listed:
        return []
    if profile.business not in (None, businesses.WHOLE_COMPANY):
        return []
    covers = profile.fields.get(constants.COVERS_FIELD)
    if isinstance(covers, str) and covers.strip():
        return [one.slug for one in listed if not _names(one, covers)]
    paragraph = _first_paragraph(profile.body)
    return [one.slug for one in listed if _leaves_out(one, paragraph)]


# --- The whole answer ----------------------------------------------------------


def take(
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    today: Optional[datetime.date] = None,
) -> Inventory:
    """Read one base against the list of kinds, for each business its map lists."""
    git = runner_or_default(runner)
    day = today or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()

    answer = Inventory()
    answer.kinds = [kind.key for kind in constants.BASE_KINDS]
    try:
        listed = businesses.read_map_businesses(base_reader.map_text(base_root))
    except ValidationError:
        listed = []
        answer.businesses_unreadable = True
    answer.businesses = listed
    slugs = [one.slug for one in listed]
    answer.columns = slugs + [businesses.WHOLE_COMPANY]
    if not listed:
        answer.columns = [businesses.WHOLE_COMPANY]

    documents = _found_in_context(base_root) + _found_elsewhere(base_root)
    if not listed:
        # With no businesses listed, a folder under `context` is only a folder,
        # and the base is read exactly as it was before businesses existed.
        documents = [one for one in documents if one.flat]
    for one in documents:
        _read(base_root, one)
        if listed:
            one.business, one.doubt = businesses.document_business(
                one.path, one.fields, listed
            )
        else:
            one.business = businesses.WHOLE_COMPANY

    confirmed = _confirmed_on(base_root, base_id, documents, git, day)
    answer.confirmations_unreadable = confirmed is None
    known = confirmed is not None
    confirmed = confirmed or {}

    differs = {kind.key: kind.differs_by_business for kind in constants.BASE_KINDS}
    for kind in answer.kinds:
        mine = [one for one in documents if one.kind == kind and one.doubt is None]
        for column in answer.columns:
            if column == businesses.WHOLE_COMPANY:
                if listed and differs[kind]:
                    answer.cells[(kind, column)] = None
                    continue
                held = [
                    one
                    for one in mine
                    if one.business in (businesses.WHOLE_COMPANY, None)
                ]
            else:
                held = [
                    one
                    for one in mine
                    if one.business == column
                    or (differs[kind] and one.business == businesses.WHOLE_COMPANY)
                    # A flat document nobody could read might be this
                    # business's, so it is never called missing for it.
                    or (
                        differs[kind]
                        and one.flat
                        and one.business is None
                        and one.state == STATE_UNREADABLE
                    )
                ]
                if not held and not differs[kind]:
                    answer.cells[(kind, column)] = None
                    continue
            answer.cells[(kind, column)] = Cell(held, confirmed, known)

    for one in documents:
        if one.doubt == businesses.CODE_NOT_IN_MAP:
            answer.unlisted.append(one.path)
        elif one.doubt == businesses.CODE_DISAGREE:
            answer.disagree.append(one.path)
        elif (
            listed
            and differs[one.kind]
            and one.flat
            and one.business is None
            and one.state != STATE_UNREADABLE
        ):
            answer.not_stated.append(one.path)
    answer.unlisted.sort()
    answer.disagree.sort()
    answer.not_stated.sort()

    profile = next(
        (one for one in documents if one.kind == "icps" and one.flat), None
    )
    answer.scope_left_out = _scope_left_out(profile, listed)

    draftable = {kind.key for kind in constants.BASE_KINDS if kind.draftable}
    answer.draftable_missing = [
        (kind, column)
        for kind in answer.kinds
        for column in answer.columns
        if kind in draftable
        and answer.cells.get((kind, column)) is not None
        and answer.cells[(kind, column)].state == STATE_MISSING
    ]
    from . import starter

    answer.starter_offers = starter.offer_sentences(base_root)
    return answer
