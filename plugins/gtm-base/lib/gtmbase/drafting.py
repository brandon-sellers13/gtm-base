"""Assembling what the assistant is asked to draft, and reading back what it wrote.

Nothing here talks to a model. The assistant is the thing that drafts, and this
module is the two ends around it: it builds the text of the request out of a
prompt file and the fenced sources, and it reads the answer back into a
document this plugin is willing to write down.

Three steps, in the order setup runs them. The ideal customer profile first,
because everything else refers to it. Then the one decision entry, which needs
the profile's path. Then the positioning.

Reading the answer back is deliberately strict and deliberately quiet. Every
refusal is one short code carrying the step it belongs to, and none of them
repeats a word of what the model wrote, because a draft that has just been
refused is exactly the text that should not be quoted anywhere. Nothing here
retries. The caller goes back to the same step and asks again.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Sequence

from . import constants, formats, location, sources as sources_module
from .errors import DraftError, LocationError, PathError, ValidationError
from .fsutil import read_text

# --- The three steps ---------------------------------------------------------

STEP_ICP = "icp"
STEP_LEDGER = "ledger-entry"
STEP_POSITIONING = "positioning"

STEPS = (STEP_ICP, STEP_LEDGER, STEP_POSITIONING)

# The prompt file each step is built from.
PROMPT_FILES = {
    STEP_ICP: "draft-icp.md",
    STEP_LEDGER: "draft-ledger-entry.md",
    STEP_POSITIONING: "draft-positioning.md",
}

# Where in the plugin the prompt files live.
PROMPTS_DIR = os.path.join("skills", "join", "references", "prompts")

# Where in the base each step's work is written.
ICP_PATH = constants.CONTEXT_DIR + "/strategy/icp.md"
POSITIONING_PATH = constants.CONTEXT_DIR + "/strategy/positioning.md"

# What the settings block at the top of each file has to say the file is.
KINDS = {STEP_ICP: "icp", STEP_LEDGER: "decision", STEP_POSITIONING: "positioning"}

# The settings every context file this unit writes has to carry.
CONTEXT_FIELDS = ("kind", "owner", "last_confirmed", "sources", "status")

# The headings the profile always carries, whatever the sources held.
ALWAYS_SECTIONS = ("Firmographics", "Felt needs", "Use cases", "Current solutions")
# The headings the profile carries only when the sources actually said
# something about them. A heading with nothing behind it is worse than no
# heading, so these are left out whole rather than written empty.
ONLY_IF_SIGNAL_SECTIONS = (
    "Team structure",
    "Technographics",
    "Geography",
    "Trigger events",
)

# The one heading a skipped file is written with.
SKIPPED_HEADINGS = {
    STEP_ICP: "Ideal customer profile",
    STEP_POSITIONING: "Positioning",
}

# --- The codes a refusal carries ---------------------------------------------

CODE_NO_FENCE = "no-fence"
CODE_NO_FRONTMATTER = "no-frontmatter"
CODE_MISSING_FIELD = "missing-field:%s"
CODE_WRONG_KIND = "wrong-kind"
# One code covers the em dash and the en dash together. Both are the long dash
# this plugin never writes, the rule a person is told is the one about dashes,
# and two codes for one rule would only make the message longer.
CODE_EM_DASH = "em-dash"
CODE_BANNED_WORD = "banned-word:%s"
CODE_PLACEHOLDER = "placeholder"
# A heading that is missing altogether reports the same thing as a heading with
# nothing under it: the section the profile always carries is not there.
CODE_EMPTY_SECTION = "empty-section:%s"
# The sources at the end were left out because the whole was too long.
CODE_SOURCES_CAPPED = "sources-capped"
# A settings line this plugin does not write and does not read. It is refused
# rather than kept, because a line nothing checks is a line anything could be
# written on and nobody would ever look at it again.
CODE_UNKNOWN_FIELD = "unknown-field:%s"
# Material was named for this step and none of it survived, so there was
# nothing to draft from and no request was built.
CODE_NO_SOURCES = "no-sources"
# The company name is not a name a folder or a request may carry.
CODE_BAD_COMPANY = "bad-company"
# At least one source carried a date that was in the future and was pulled
# back to today, so the date on it is not the date the file claims.
CODE_DATE_CLAMPED = "date-clamped"

# The long dashes, written as escapes so this file holds neither of them.
EM_DASH = "\u2014"
EN_DASH = "\u2013"

# What a draft may never say, whatever the sentence around it is.
_PLACEHOLDER_WORDS = re.compile(r"\b(?:tbd|todo)\b", re.IGNORECASE)
_PLACEHOLDER_MARKS = ("lorem", "[insert", "<placeholder>")

_FENCE_OPEN = re.compile(r"^\s*```+\s*(?:markdown|md)?\s*$", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"^\s*```+\s*$")


def _banned_pattern(word: str) -> "re.Pattern":
    return re.compile(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", re.IGNORECASE)


_BANNED = [(word, _banned_pattern(word)) for word in constants.DRAFT_BANNED_WORDS]


# --- The sentences printed before each wait ---------------------------------
#
# They are fixed, they are short, and there is one for every point where the
# person is left waiting. Nothing here is built from anything a model wrote.

PROGRESS = {
    "reading": "Reading what you named.",
    STEP_ICP: "Drafting your ideal customer profile.",
    STEP_LEDGER: "Drafting the decision entry.",
    STEP_POSITIONING: "Drafting your positioning.",
    "saving": "Saving that into the base.",
}


# --- Building the request ----------------------------------------------------


class Assembly(object):
    """The text of one request, and what had to be left out to build it."""

    __slots__ = ("text", "codes", "included_labels", "dropped_labels")

    def __init__(self, text, codes=None, included_labels=None, dropped_labels=None):
        self.text = text
        self.codes = list(codes or [])
        self.included_labels = list(included_labels or [])
        self.dropped_labels = list(dropped_labels or [])

    def __repr__(self) -> str:
        return "Assembly(included=%r, dropped=%r)" % (
            self.included_labels,
            self.dropped_labels,
        )


def plugin_root_default() -> str:
    """The plugin folder this module is installed in."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def prompt_path(step: str, plugin_root: Optional[str] = None) -> str:
    """Where the prompt file for one step lives."""
    if step not in PROMPT_FILES:
        raise DraftError(step, "unknown-step")
    root = plugin_root or plugin_root_default()
    return os.path.join(root, PROMPTS_DIR, PROMPT_FILES[step])


def prompt_text(step: str, plugin_root: Optional[str] = None) -> str:
    """The prompt file for one step, read from the plugin."""
    text = read_text(prompt_path(step, plugin_root))
    if text is None:
        raise DraftError(step, "no-prompt-file")
    return text


def source_line(source) -> str:
    """One line of the list of sources, with the date when the source has one."""
    label = getattr(source, "label", "")
    date = getattr(source, "date", None)
    if date:
        return "%s (%s)" % (label, date)
    return str(label)


def assemble(
    step: str,
    sources: Sequence["sources_module.Source"],
    company: str,
    today,
    owner_email: str,
    icp_path: Optional[str] = None,
    plugin_root: Optional[str] = None,
) -> Assembly:
    """Build the request for one step out of the prompt file and the sources.

    Every source is fenced, so the sentence saying that what follows is the
    person's own writing rather than instructions is said once per source and
    said before the source says anything. When the sources together are longer
    than the cap, whole sources are dropped from the end, never the middle of
    one, and the caller is handed the labels of the ones that went.

    The company name is checked here as well as where the base's folder is
    named. The name is written into the request in the person's own words and
    it sits outside every fence, so it has to be a name and nothing else.

    When material was handed in and none of it survived, no request is built at
    all. A request carrying the person's company name and no material would
    produce a document written from nothing, which is the one thing setting a
    base up must never put in front of somebody.
    """
    template = prompt_text(step, plugin_root)
    name = _checked_company(step, company)

    included: List[str] = []
    dropped: List[str] = []
    fences: List[str] = []
    clamped = False
    used = 0
    for source in sources:
        fenced = sources_module.fence(source)
        if dropped or used + len(fenced) > constants.DRAFT_SOURCES_MAX_CHARS:
            dropped.append(source_line(source))
            continue
        used += len(fenced)
        fences.append(fenced)
        included.append(source_line(source))
        if getattr(source, "clamped", False):
            clamped = True

    if sources and not fences:
        raise DraftError(step, CODE_NO_SOURCES)

    listing = ["The sources you may read, with the date on each one that has a date:"]
    listing.extend("- " + line for line in included)
    block = "\n".join(listing) + "\n\n" + "\n".join(fences)

    values = {
        "sources": block,
        "company": name,
        "today": str(today or ""),
        "owner_email": str(owner_email or ""),
        "icp_path": str(icp_path or ICP_PATH),
    }
    text = template
    for field, value in values.items():
        text = text.replace("{{%s}}" % field, value)

    codes = [CODE_SOURCES_CAPPED] if dropped else []
    if clamped:
        codes.append(CODE_DATE_CLAMPED)
    return Assembly(text, codes, included, dropped)


def _checked_company(step: str, company) -> str:
    """The company name, or a refusal, before it goes anywhere near a request.

    It goes through the same check the folder name goes through, and then two
    more. A line break would let the name write its own line in the request,
    and either of the fence's own lines would let it close a fence and carry on
    as though it were the assistant's own words.
    """
    try:
        name = location.validate_company_name(company)
    except LocationError:
        raise DraftError(step, CODE_BAD_COMPANY)
    if "\n" in name or "\r" in name:
        raise DraftError(step, CODE_BAD_COMPANY)
    folded = name.casefold()
    footer = constants.SOURCE_FENCE_FOOTER.casefold()
    opener = constants.SOURCE_FENCE_HEADER.split("%s")[0].rstrip().casefold()
    if footer in folded or opener in folded:
        raise DraftError(step, CODE_BAD_COMPANY)
    return name


def what_is_wrong(draft, answer: str) -> str:
    """The note that asks for the same draft again with an answer applied.

    It writes nothing, anywhere. The answer is the person's own words, so it is
    fenced the same way a document is, and the request that follows says to
    draft the whole thing again rather than to patch the draft that was wrong.
    """
    source = sources_module.paste_source("what is wrong", str(answer or ""))
    return "\n".join(
        [
            "Here is what the person said is wrong with the draft you just wrote.",
            "",
            sources_module.fence(source).rstrip("\n"),
            "",
            "Write the whole document again with that applied. Keep everything "
            "they did not object to exactly as it was, change what they named, "
            "and return the whole document in one fence as before.",
        ]
    ) + "\n"


# --- Reading the answer back -------------------------------------------------


class Draft(object):
    """One document the assistant wrote back, read and checked."""

    __slots__ = ("step", "text", "fields", "body", "codes", "only_if_signal_present")

    def __init__(self, step, text, fields, body, codes=None, only_if_signal_present=None):
        self.step = step
        self.text = text
        self.fields = dict(fields or {})
        self.body = body
        self.codes = list(codes or [])
        self.only_if_signal_present = list(only_if_signal_present or [])

    @property
    def path(self) -> str:
        """Where in the base this draft belongs, for the two context files."""
        if self.step == STEP_ICP:
            return ICP_PATH
        if self.step == STEP_POSITIONING:
            return POSITIONING_PATH
        raise DraftError(self.step, "no-fixed-path")

    def __repr__(self) -> str:
        return "Draft(step=%r, sections=%r)" % (
            self.step,
            self.only_if_signal_present,
        )


def strip_fence(step: str, model_text: str) -> str:
    """The document inside the outermost fence, with the prose around it gone.

    The first fence line opens it and the last one closes it, so a fence inside
    the document survives untouched. A model that wrote no fence at all is
    refused rather than guessed at.
    """
    if not isinstance(model_text, str) or not model_text.strip():
        raise DraftError(step, CODE_NO_FENCE)
    lines = model_text.split("\n")
    opening = None
    for index, line in enumerate(lines):
        if _FENCE_OPEN.match(line):
            opening = index
            break
    if opening is None:
        raise DraftError(step, CODE_NO_FENCE)
    closing = None
    for index in range(len(lines) - 1, opening, -1):
        if _FENCE_CLOSE.match(lines[index]):
            closing = index
            break
    if closing is None:
        raise DraftError(step, CODE_NO_FENCE)
    inside = "\n".join(lines[opening + 1 : closing]).strip("\n")
    if not inside.strip():
        raise DraftError(step, CODE_NO_FENCE)
    return inside + "\n"


def check_words(step: str, text: str) -> None:
    """Refuse the long dash, the words that say nothing, and any placeholder."""
    if EM_DASH in text or EN_DASH in text:
        raise DraftError(step, CODE_EM_DASH)
    for word, pattern in _BANNED:
        if pattern.search(text):
            raise DraftError(step, CODE_BANNED_WORD % word)
    folded = text.lower()
    for mark in _PLACEHOLDER_MARKS:
        if mark in folded:
            raise DraftError(step, CODE_PLACEHOLDER)
    if _PLACEHOLDER_WORDS.search(text):
        raise DraftError(step, CODE_PLACEHOLDER)


def parse(step: str, model_text: str) -> Draft:
    """Read one answer back into a document this plugin is willing to write.

    The order is the order the failures matter in. The fence first, because
    without it there is no document. Then the words, because a draft using a
    word from the banned list is not worth checking the shape of. Then the
    settings block and the fields the step needs. Then, for the profile, the
    sections it always carries.
    """
    if step not in STEPS:
        raise DraftError(step, "unknown-step")
    text = strip_fence(step, model_text)
    check_words(step, text)

    try:
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        raise DraftError(step, CODE_NO_FRONTMATTER)

    required = (
        formats.LEDGER_REQUIRED if step == STEP_LEDGER else CONTEXT_FIELDS
    )
    for name in required:
        if name not in fields:
            raise DraftError(step, CODE_MISSING_FIELD % name)
    if step != STEP_LEDGER:
        # The two context files carry exactly the five settings this plugin
        # writes and reads. Anything else is refused rather than carried into
        # the base, because a setting nothing here checks would sit in the file
        # unread, and a line nobody reads is a line anything could be put on.
        for name in sorted(fields):
            if name not in CONTEXT_FIELDS:
                raise DraftError(step, CODE_UNKNOWN_FIELD % name)
    if str(fields.get("kind", "")).strip() != KINDS[step]:
        raise DraftError(step, CODE_WRONG_KIND)

    present: List[str] = []
    if step == STEP_ICP:
        sections = {
            name.strip().lower(): value
            for name, value in formats.split_sections(body).items()
        }
        for heading in ALWAYS_SECTIONS:
            if not sections.get(heading.lower(), "").strip():
                raise DraftError(step, CODE_EMPTY_SECTION % heading)
        present = [
            heading
            for heading in ONLY_IF_SIGNAL_SECTIONS
            if sections.get(heading.lower(), "").strip()
        ]

    return Draft(step, text, fields, body, [], present)


def skipped_text(step: str, owner_email: str, today) -> str:
    """The file a skipped step leaves behind: the settings, and one heading.

    It says `skipped` so that everything downstream knows the base is not
    finished, and it holds no body at all, because a skipped file the person
    never looked at must never read as a file somebody wrote.
    """
    if step not in SKIPPED_HEADINGS:
        raise DraftError(step, "cannot-skip")
    fields: Dict[str, object] = {
        "kind": KINDS[step],
        "owner": owner_email,
        "last_confirmed": str(today),
        "sources": [],
        "status": "skipped",
    }
    return formats.render_document(fields, "# " + SKIPPED_HEADINGS[step] + "\n")
