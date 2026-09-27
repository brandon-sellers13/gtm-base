"""Taking a finished segment page into a base under a per-file contract.

Unit 1.7c of the 2026-09-19 plan (requirements P20 to P23). On the third real
run, twelve finished, reviewed segment pages went into one drafted profile
and came out summarized. A person may now say that a finished page is the
authoritative version of one segment, and the page is taken into the base as
it stands instead of being rewritten, under a contract every page has to
pass on its own.

Everything in the page is untrusted. It is somebody's own writing, it passed
through nothing on its way in, and once it sits in the base it is handed to
the model every time the document is used. So the contract runs in a fixed
order, the order the decisions table of the plan sets, and a page that fails
any clause is refused with one sentence naming the class of thing found, never
the value, and the offer to draft that segment from the material instead:

1. The destination: a safe file name, no file already in the base whose name
   folds to the same one, no link on the way into the segment folder, and no
   name the trust check keeps for itself.
2. The original settings block at the top is discarded, and one that is not
   closed or cannot be read is refused, because nobody can say where the page
   itself begins.
3. Hidden content is taken out and counted, exactly as it is for a draft.
4. Then, on what is left, the check for the fence's own lines, which a
   comment could have been hiding, and the contact and key screens.
5. The heading grammar the proposal editor supports, so a later change lands
   in the part it names: no heading twice at one level, no heading-shaped line
   inside a block of code, no underlined heading, and at least one level two
   heading for a change to land under.
6. The part of the company the base is for: a page with a heading naming a
   place the person dropped for that scope covers more than the base is for.
7. A `[your call: ...]` question is kept only where a later change can reach
   it, and only on the person's say.
8. The library writes the settings block, and the whole file is screened
   again.
9. The yes is bound to a hash of exactly those bytes.

The person is shown what was removed, the opening lines, and where the whole
cleaned file is, and may read it whole before answering. Adoption never edits
or moves the original. Approval establishes which document was adopted; it
does not make an instruction inside it authoritative, which is why every path
that later hands the document to the model holds it inside the data fence.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Dict, List, Optional, Sequence

from . import callmarkers, constants, formats, redaction_patterns, review, segments
from . import sources as sources_module
from .errors import GtmBaseError, PathError, SourceRejected, ValidationError
from .fsutil import atomic_write_json, read_json

# What an adopted file says it is. It carries no freshness of its own: the
# owner's dated yes is what confirms it, exactly as it confirms a drafted file.
STATUS_ADOPTED = "adopted"
# The file in a run's folder holding, for each segment, the hash of the bytes
# the person was shown and the day they were shown, and which segments the
# contract refused, so the offer to draft one instead can be taken up.
STATE_FILE = "adoption.json"
STATE_VERSION = 1
# How many lines of the page are shown in the conversation. The whole page is
# readable in its own file.
OPENING_LINES = 6
# Longest one of those lines is shown, in characters.
OPENING_LINE_MAX_CHARS = 160
# File endings a page may have to be taken in as it stands.
MARKDOWN_SUFFIXES = (".md", ".markdown")

# --- Why a page was refused ---------------------------------------------------

CODE_NOT_TO_ADOPT = "not-a-segment-to-adopt"
CODE_BASE_NOT_READY = "adopt-base-not-ready"
CODE_NOT_MARKDOWN = "adopt-not-markdown"
CODE_UNREADABLE = "adopt-unreadable"
CODE_MALFORMED_SETTINGS = "adopt-malformed-settings"
CODE_FENCE_MARKER = "fence-marker"
CODE_SCREENED = "screened"
CODE_DUPLICATE_HEADING = "duplicate-heading"
CODE_HEADING_IN_CODE = "heading-in-code"
CODE_UNDERLINED_HEADING = "underlined-heading"
CODE_NO_PARTS = "no-parts"
CODE_QUESTION_UNREACHABLE = "question-above-every-part"
CODE_WIDER_THAN_SCOPE = "wider-than-scope"
CODE_FILE_TAKEN = segments.CODE_FILE_TAKEN
CODE_FOLDER_NOT_ORDINARY = segments.CODE_FOLDER_NOT_ORDINARY
CODE_RESERVED_NAME = segments.CODE_RESERVED_NAME
CODE_NOT_SHOWN = "adopt-not-shown"
CODE_CHANGED = "adopt-changed-since-shown"
CODE_QUESTIONS_OPEN = "questions-open"

# --- The sentences a person reads ---------------------------------------------

# Said first, for each document shown.
SHOW_OPENING = (
    "Here is what taking %(name)s from its finished document would save into "
    "your base."
)
# Said when the original carried a settings block of its own.
SETTINGS_SET_ASIDE = (
    "The settings at the top of the original are set aside, and GTM Base "
    "writes its own in their place."
)
# Said when nothing at all was taken out.
NOTHING_TAKEN_OUT = "Nothing was taken out of it."
# Said above the first lines of the page.
OPENING_SAID = "Its first lines, exactly as they will be saved, are below."
# Said after them: where the whole of it is, and that the original stays.
WHOLE_FILE = (
    "The whole cleaned document is saved in this setup's own folder, and I can "
    "show it to you in full, or tell you where it is, before you answer. Your "
    "original is not changed or moved."
)
# Said when the page leaves questions for the person, before the one ask.
ONE_QUESTION = (
    "It leaves one question for you to answer, marked where it comes up, and "
    "taking it in as it stands leaves that question open for your next review "
    "of your base."
)
QUESTIONS = (
    "It leaves %d questions for you to answer, each marked where it comes up, "
    "and taking it in as it stands leaves them open for your next review of "
    "your base."
)
# The one thing each showing asks.
ASK = "Shall I take this document into your base as it stands, or leave it out?"
ASK_WITH_QUESTIONS = (
    "Shall I take this document into your base as it stands, with its "
    "questions left open, or leave it out?"
)
# Said once it is written.
TAKEN_IN = (
    "That document is saved into your base as it stands, together with the "
    "record that you said yes."
)

# The offer every refusal of the page itself ends with.
DRAFT_INSTEAD = "I can draft this segment from your material instead."
NOT_MARKDOWN = (
    "That document is not written in Markdown, so it cannot be taken in as it "
    "stands, and nothing was saved. "
    "I can draft this segment from your material instead."
)
UNREADABLE = (
    "That document could not be read, so nothing was saved. "
    "I can draft this segment from your material instead."
)
MALFORMED_SETTINGS = (
    "The settings at the top of that document are not closed or cannot be "
    "read, so nobody can say where the document itself begins, and nothing "
    "was saved. "
    "I can draft this segment from your material instead."
)
FENCE_MARKER = (
    "That document holds a line GTM Base uses to keep your material apart from "
    "its own instructions, so nothing was saved. "
    "I can draft this segment from your material instead."
)
SCREENED = (
    "That document holds %(classes)s, which a base never keeps, so nothing was "
    "saved. "
    "I can draft this segment from your material instead."
)
DUPLICATE_HEADING = (
    "That document uses the same heading twice at one level, so a later "
    "change could land in the wrong part, and nothing was saved. "
    "I can draft this segment from your material instead."
)
HEADING_IN_CODE = (
    "That document has a line shaped like a heading inside a block of code, so "
    "a later change could land in the wrong part, and nothing was saved. "
    "I can draft this segment from your material instead."
)
UNDERLINED_HEADING = (
    "That document marks a heading by underlining it, which a later change "
    "cannot find, so nothing was saved. "
    "I can draft this segment from your material instead."
)
NO_PARTS = (
    "That document has no headings dividing it into parts, so a later change "
    "would have nowhere to land, and nothing was saved. "
    "I can draft this segment from your material instead."
)
QUESTION_UNREACHABLE = (
    "That document asks a question above its first part, where a later change "
    "cannot reach it, so nothing was saved. "
    "I can draft this segment from your material instead."
)
WIDER_THAN_SCOPE = (
    "That document covers more than %(covers)s, which is what this base is "
    "for, so nothing was saved. "
    "I can draft this segment from your material instead."
)
NOT_TO_ADOPT = (
    "That is not a segment this setup settled to take from its finished "
    "document, so nothing was done."
)
BASE_NOT_READY = (
    "Your customer profile and your positioning are saved first, so nothing "
    "was taken in yet."
)
NOT_SHOWN = (
    "That document has not been shown to you in this setup yet, so nothing "
    "was saved. Show it first, then ask."
)
CHANGED = (
    "That document changed after it was shown to you, so nothing was saved. "
    "Show it again, then ask again."
)
QUESTIONS_NOT_LEFT_OPEN = (
    "That document leaves questions open, so nothing was saved. Ask whether to "
    "take it in with them left open."
)
UNSAVED_EDITS = (
    "There are words in your base that you have not saved, so nothing was "
    "taken in. Save them or put them aside, then ask again."
)
NOT_ON_THE_MAIN_LINE = (
    "Your base is not on its main line right now, so nothing was taken in."
)

# Every sentence above, by name, for the plain-language checks.
PERSON_FACING = (
    "SHOW_OPENING",
    "SETTINGS_SET_ASIDE",
    "NOTHING_TAKEN_OUT",
    "OPENING_SAID",
    "WHOLE_FILE",
    "ONE_QUESTION",
    "QUESTIONS",
    "ASK",
    "ASK_WITH_QUESTIONS",
    "TAKEN_IN",
    "DRAFT_INSTEAD",
    "NOT_MARKDOWN",
    "UNREADABLE",
    "MALFORMED_SETTINGS",
    "FENCE_MARKER",
    "SCREENED",
    "DUPLICATE_HEADING",
    "HEADING_IN_CODE",
    "UNDERLINED_HEADING",
    "NO_PARTS",
    "QUESTION_UNREACHABLE",
    "WIDER_THAN_SCOPE",
    "NOT_TO_ADOPT",
    "BASE_NOT_READY",
    "NOT_SHOWN",
    "CHANGED",
    "QUESTIONS_NOT_LEFT_OPEN",
    "UNSAVED_EDITS",
    "NOT_ON_THE_MAIN_LINE",
)

# The refusals about the page itself, each of which offers a draft instead.
OFFERS_A_DRAFT = (
    CODE_NOT_MARKDOWN,
    CODE_UNREADABLE,
    CODE_MALFORMED_SETTINGS,
    CODE_FENCE_MARKER,
    CODE_SCREENED,
    CODE_DUPLICATE_HEADING,
    CODE_HEADING_IN_CODE,
    CODE_UNDERLINED_HEADING,
    CODE_NO_PARTS,
    CODE_QUESTION_UNREACHABLE,
    CODE_WIDER_THAN_SCOPE,
)

_SENTENCES = {
    CODE_NOT_TO_ADOPT: NOT_TO_ADOPT,
    CODE_BASE_NOT_READY: BASE_NOT_READY,
    CODE_NOT_MARKDOWN: NOT_MARKDOWN,
    CODE_UNREADABLE: UNREADABLE,
    CODE_MALFORMED_SETTINGS: MALFORMED_SETTINGS,
    CODE_FENCE_MARKER: FENCE_MARKER,
    CODE_DUPLICATE_HEADING: DUPLICATE_HEADING,
    CODE_HEADING_IN_CODE: HEADING_IN_CODE,
    CODE_UNDERLINED_HEADING: UNDERLINED_HEADING,
    CODE_NO_PARTS: NO_PARTS,
    CODE_QUESTION_UNREACHABLE: QUESTION_UNREACHABLE,
    CODE_FILE_TAKEN: segments.FILE_TAKEN,
    CODE_FOLDER_NOT_ORDINARY: segments.FOLDER_NOT_ORDINARY,
    CODE_NOT_SHOWN: NOT_SHOWN,
    CODE_CHANGED: CHANGED,
    CODE_QUESTIONS_OPEN: QUESTIONS_NOT_LEFT_OPEN,
}


class AdoptionRefused(GtmBaseError):
    """A page was not taken in, with the one sentence that says why.

    `classes` names what the screens found, and never the value itself.
    """

    default_code = CODE_UNREADABLE

    def __init__(self, code, sentence=None, classes=()):
        super(AdoptionRefused, self).__init__(code, code)
        self.sentence = sentence if sentence is not None else _SENTENCES.get(code, "")
        self.classes = list(classes)


# --- The heading grammar -------------------------------------------------------

# A heading as the proposal editor reads one: hashes at the very start of the
# line, then a space, then something.
_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
# A line that would read as a heading once its leading spaces were gone.
_HEADING_SHAPED_RE = re.compile(r"^\s+#{1,6}\s+\S")
# The line opening or closing a fenced block of code.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# The line underneath a heading written the underlined way.
_UNDERLINE_RE = re.compile(r"^ {0,3}(?:=+|-{2,})[ \t]*$")
# A line that starts an item of a list, a quotation, or a row of a table,
# none of which can be underlined into a heading.
_NOT_A_PARAGRAPH_RE = re.compile(r"^\s*(?:[-*+>]\s|\d+[.)]\s|\|)")


def _fence_closes(line: str, opener: str) -> bool:
    match = _FENCE_RE.match(line)
    if not match:
        return False
    marks = match.group(1)
    return (
        marks[0] == opener[0]
        and len(marks) >= len(opener)
        and not match.group(2).strip()
    )


def heading_problem(body: str) -> Optional[str]:
    """Why the proposal editor could not address this body, or None.

    The editor finds a part by matching a whole line and counts a part as
    running to the next heading as large or larger, where a heading is a line
    that begins with hashes and a space. So a heading-shaped line inside a
    block of code, fenced or indented, is found as a heading by one half of
    the editor and not by the other; an underlined heading is not found at
    all; and a heading used twice at one level sends a change to the first of
    them. A body with no level two heading has no part a change can land in.
    """
    lines = str(body or "").split("\n")
    fence: Optional[str] = None
    seen = set()
    parts = 0
    previous = ""
    for line in lines:
        if fence is not None:
            if _fence_closes(line, fence):
                fence = None
            elif _HEADING_RE.match(line.strip()):
                return CODE_HEADING_IN_CODE
            previous = ""
            continue
        opening = _FENCE_RE.match(line)
        if opening and not (
            opening.group(1)[0] == "`" and "`" in opening.group(2)
        ):
            fence = opening.group(1)
            previous = ""
            continue
        if _HEADING_SHAPED_RE.match(line):
            return CODE_HEADING_IN_CODE
        heading = _HEADING_RE.match(line)
        if heading:
            key = line.strip()
            if key in seen:
                return CODE_DUPLICATE_HEADING
            seen.add(key)
            if len(heading.group(1)) == 2:
                parts += 1
            previous = ""
            continue
        if (
            _UNDERLINE_RE.match(line)
            and previous.strip()
            and not _NOT_A_PARAGRAPH_RE.match(previous)
        ):
            return CODE_UNDERLINED_HEADING
        previous = line
    if parts == 0:
        return CODE_NO_PARTS
    return None


# --- The part of the company the base is for ---------------------------------


def scope_problem(body: str, covers: Optional[str], dropped: Sequence[str]) -> bool:
    """Whether the page covers more than the part of the company the base is for.

    There is no filter on the words inside a document (Unit 1.7a): what keeps
    another part's material out is the places the person dropped for the
    scope. A page is wider than the scope when one of its headings names one
    of those places, such as a heading about lending teams in a base for
    payments, after the person dropped the lending folder. Names are compared
    the way file names are made, whole words at a time, so "lending" matches
    "Lending teams" and not "Blending". A base for the whole company refuses
    nothing here.
    """
    if not covers:
        return False
    own = segments.slug_for(covers)
    names = []
    for place in dropped or ():
        folded = segments.slug_for(str(place or "").replace("_", " "))
        if folded and folded != own and folded not in names:
            names.append(folded)
    if not names:
        return False
    for line in str(body or "").split("\n"):
        if not _HEADING_RE.match(line):
            continue
        heading = "-" + segments.slug_for(line.lstrip("#")) + "-"
        for name in names:
            if "-" + name + "-" in heading:
                return True
    return False


# --- The contract ----------------------------------------------------------------


class Cleaned(object):
    """A page as it would be saved, and what was done to it on the way."""

    __slots__ = (
        "text",
        "body",
        "digest",
        "removed",
        "settings_set_aside",
        "questions",
        "label",
    )

    def __init__(self, text, body, removed, settings_set_aside, questions, label):
        self.text = text
        self.body = body
        self.digest = digest_of(text)
        self.removed = dict(removed or {})
        self.settings_set_aside = bool(settings_set_aside)
        self.questions = int(questions)
        self.label = label

    def opening(self) -> List[str]:
        """The first lines of the page with something on them, each capped."""
        found = []
        for line in self.body.split("\n"):
            if not line.strip():
                continue
            if len(line) > OPENING_LINE_MAX_CHARS:
                line = line[:OPENING_LINE_MAX_CHARS].rstrip() + "..."
            found.append(line)
            if len(found) >= OPENING_LINES:
                break
        return found

    def __repr__(self) -> str:
        return "Cleaned(digest=%r, questions=%d)" % (self.digest[:12], self.questions)


def digest_of(text: str) -> str:
    """The hash a yes is bound to: of the exact bytes that will be saved."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def destination_problem(base_root: str, slug: str) -> Optional[str]:
    """Why a segment of this file name may not be written into this base.

    Clause one. The file name is checked again rather than trusted from the
    inventory, then the folder on the way, then every file already in either
    folder segments have been kept in, whose name may fold to the same one.
    """
    problem = segments.slug_problem(slug)
    if problem is not None:
        return CODE_RESERVED_NAME if problem == segments.CODE_RESERVED_NAME else CODE_FILE_TAKEN
    if not segments.folder_is_ordinary(base_root):
        return CODE_FOLDER_NOT_ORDINARY
    if segments.already_in_base(base_root, slug) is not None:
        return CODE_FILE_TAKEN
    return None


def _discard_settings(text: str):
    """The page without its own settings block, and whether it had one.

    Clause two. A page that opens with a settings block has it taken off
    whole. One that is never closed, or that holds a line no settings block
    holds, is refused: without it nobody can say where the page begins, and a
    block half read is how a heading or an instruction could hide in it.
    """
    body = text[1:] if text.startswith("﻿") else text
    lines = body.split("\n")
    if not lines or lines[0].strip() != formats.FRONTMATTER_FENCE:
        return body, False
    try:
        block, rest = formats.split_document(body)
        formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        raise AdoptionRefused(CODE_MALFORMED_SETTINGS)
    return rest, True


def _screen(text: str, frontmatter_lines=None) -> List[str]:
    return review.screen(text, None, frontmatter_lines=frontmatter_lines or set())


def _classes_said(classes: Sequence[str]) -> str:
    labels = [redaction_patterns.label_for(name) for name in classes]
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def _refuse_screened(classes):
    raise AdoptionRefused(
        CODE_SCREENED,
        SCREENED % {"classes": _classes_said(classes)},
        classes=classes,
    )


def clean(
    raw_text: str,
    label: str,
    day,
    owner_email: str,
    source_line: str,
    covers: Optional[str] = None,
    dropped: Sequence[str] = (),
) -> Cleaned:
    """Run clauses two to eight on one page, and return what would be saved.

    `label` is the page's name as the person was shown it, used only to say
    what hidden parts were taken out of it. `source_line` is what the settings
    will name as the original, and `day` the date the file says it was last
    confirmed. Nothing here writes anything.
    """
    if not isinstance(raw_text, str):
        raise AdoptionRefused(CODE_UNREADABLE)
    body, had_settings = _discard_settings(raw_text)
    try:
        source = sources_module.make_source(label, body, "markdown")
    except SourceRejected as refusal:
        if refusal.code == CODE_FENCE_MARKER:
            raise AdoptionRefused(CODE_FENCE_MARKER)
        raise AdoptionRefused(CODE_UNREADABLE)
    cleaned = source.text
    found = _screen(cleaned)
    if found:
        _refuse_screened(found)
    problem = heading_problem(cleaned)
    if problem is not None:
        raise AdoptionRefused(problem)
    if scope_problem(cleaned, covers, dropped):
        raise AdoptionRefused(
            CODE_WIDER_THAN_SCOPE, WIDER_THAN_SCOPE % {"covers": covers}
        )
    marks = callmarkers.find(cleaned)
    if any(mark.heading is None for mark in marks):
        raise AdoptionRefused(CODE_QUESTION_UNREACHABLE)
    fields = {
        "kind": constants.SEGMENT_KIND,
        "owner": owner_email,
        "last_confirmed": day.isoformat() if hasattr(day, "isoformat") else str(day),
        "sources": [source_line],
        "status": STATUS_ADOPTED,
    }
    try:
        text = formats.render_document(fields, cleaned.lstrip("\n"))
    except (ValidationError, PathError):
        raise AdoptionRefused(CODE_UNREADABLE)
    # Clause eight: the whole file, settings and all, through the same screen,
    # with only the owner's own line let through, which this plugin wrote.
    found = _screen(text, review.frontmatter_line_numbers(text))
    if found:
        _refuse_screened(found)
    final_body = formats.split_document(text)[1]
    return Cleaned(
        text,
        final_body,
        source.removed,
        had_settings,
        len(marks),
        label,
    )


def source_line_for(label: str, day) -> str:
    """How the settings name the original: where it sat, and its date.

    The place is the one the person was shown, relative to the folder they
    named, never a path from inside their home folder, and anything a list of
    settings cannot carry is replaced.
    """
    text = "".join(
        character if (character.isalnum() or character in " ._-/") else "-"
        for character in str(label or "")
    ).strip()[:120] or "a finished document"
    when = day.isoformat() if hasattr(day, "isoformat") else str(day or "")
    return "%s (%s)" % (text, when) if when else text


def is_markdown(path: str) -> bool:
    return os.path.splitext(str(path or ""))[1].lower() in MARKDOWN_SUFFIXES


# --- What a run remembers about each page it showed -----------------------------


def _state(folder: str) -> Dict[str, dict]:
    payload = read_json(os.path.join(folder, STATE_FILE))
    if not isinstance(payload, dict) or payload.get("version") != STATE_VERSION:
        return {}
    held = payload.get("segments")
    if not isinstance(held, dict):
        return {}
    return dict(
        (str(slug), dict(item))
        for slug, item in held.items()
        if isinstance(item, dict)
    )


def _keep(folder: str, held: Dict[str, dict], inside: str) -> None:
    atomic_write_json(
        os.path.join(folder, STATE_FILE),
        {"version": STATE_VERSION, "segments": held},
        inside=inside,
    )


def record_shown(folder: str, slug: str, digest: str, day: str, inside: str) -> None:
    """Keep the hash of what the person was shown, which their yes is bound to."""
    held = _state(folder)
    held[slug] = {"shown": str(digest), "day": str(day)}
    _keep(folder, held, inside)


def record_refused(folder: str, slug: str, code: str, inside: str) -> None:
    """Keep that the contract refused this page, so it may be drafted instead."""
    held = _state(folder)
    held[slug] = {"refused": str(code)}
    _keep(folder, held, inside)


def shown(folder: str, slug: str) -> Optional[dict]:
    """What was shown for one segment, or None when nothing was."""
    item = _state(folder).get(slug)
    if not item or not isinstance(item.get("shown"), str) or not item.get("day"):
        return None
    if not re.match(r"^[0-9a-f]{64}$", item["shown"]):
        return None
    return item


def was_refused(folder: str, slug: str) -> bool:
    item = _state(folder).get(slug)
    return bool(item and item.get("refused"))
