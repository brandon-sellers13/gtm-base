"""Assembling what the assistant is asked to draft, and reading back what it wrote.

Nothing here talks to a model. The assistant is the thing that drafts, and this
module is the two ends around it: it builds the text of the request out of a
prompt file and the fenced sources, and it reads the answer back into a
document this plugin is willing to write down.

Three steps, in the order setup runs them. The ideal customer profile first,
because everything else refers to it. Then the one decision entry, which needs
the profile's path. Then the positioning.

A company with several segments gets two more (Unit 1.7b of the 2026-09-19
plan). The umbrella takes the profile's place: it says who the company sells
to overall, gives each segment one short paragraph, and says what they share.
Then each segment that has no finished page is drafted into a file of its own,
at full depth. Both are steps of their own, with their own prompts and their
own checks, rather than the profile's checks loosened to let them through.

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

from . import constants, formats, location, sources as sources_module, validate
from .errors import DraftError, LocationError, PathError, ValidationError
from .fsutil import read_text

# --- The three steps ---------------------------------------------------------

STEP_ICP = "icp"
STEP_CHANGE = "change-entry"
STEP_POSITIONING = "positioning"
# Unit 1.7b: the umbrella over several segments, which is written where the
# profile is, and one segment at full depth, written into a file of its own.
STEP_UMBRELLA = "umbrella"
STEP_SEGMENT = "segment"

STEPS = (STEP_ICP, STEP_CHANGE, STEP_POSITIONING, STEP_UMBRELLA, STEP_SEGMENT)
# The steps that write a context file, and so carry the five settings.
CONTEXT_STEPS = (STEP_ICP, STEP_POSITIONING, STEP_UMBRELLA, STEP_SEGMENT)
# The steps whose document is the customer profile at its own path, which is
# the one that carries what the base covers.
PROFILE_STEPS = (STEP_ICP, STEP_UMBRELLA)

# Track 4, Units T4.2 and T4.3: the documents drafted after setup, on
# request, into a base that already exists. Each reads the material the
# person names directly, as the context change does, rather than through the
# notes setup takes, and each is written to its one fixed path and nowhere
# else. A buyer persona is never written under the segments' folder.
STEP_MESSAGING = "messaging"
STEP_VOICE = "voice"
STEP_BUYER_PERSONAS = "buyer-personas"
STEP_PRODUCT = "product"
# Track 4, Units T4.4 and T4.5: the competitors and the design guide, drafted
# the same way.
STEP_COMPETITORS = "competitors"
STEP_DESIGN = "design"
LATER_STEPS = (
    STEP_MESSAGING,
    STEP_VOICE,
    STEP_BUYER_PERSONAS,
    STEP_PRODUCT,
    STEP_COMPETITORS,
    STEP_DESIGN,
)
STEPS = STEPS + LATER_STEPS
CONTEXT_STEPS = CONTEXT_STEPS + LATER_STEPS

# Plan 1, Units 2.4a and 3.5: the goals, the metric definitions and a standard,
# drafted after setup the same way, from what the person says and the
# material they name. Each is asked for rather than inferred: a figure only
# the person can give comes from their own words, which travel as pasted
# text, and the figure rule refuses one neither carries. They differ from the
# documents above in where they go. Goals and metric definitions go in the
# folder of the business they are for when the base names one, and a
# standard is written for one job, so each carries the destination its
# request was given (`later_destination`).
STEP_GOALS = "goals"
STEP_METRICS = "metrics"
STEP_STANDARD = "standard"
DESTINED_STEPS = (STEP_GOALS, STEP_METRICS, STEP_STANDARD)
# Every document drafted after setup: Track 4's, which may also be taken in
# as they stand, and these three, which are only ever asked for.
DRAFTED_LATER = LATER_STEPS + DESTINED_STEPS
STEPS = STEPS + DESTINED_STEPS
CONTEXT_STEPS = CONTEXT_STEPS + DESTINED_STEPS

# What this step was called before the rename. A setup run somebody left
# halfway through may have saved that name, and coming back to it has to work.
LEGACY_STEP_CHANGE = "ledger-entry"


def step_named(name: str):
    """The step one name means, under either of the names it has had."""
    if name in STEPS:
        return name
    if name == LEGACY_STEP_CHANGE:
        return STEP_CHANGE
    return None

# The prompt file each step is built from.
PROMPT_FILES = {
    STEP_ICP: "draft-icp.md",
    STEP_CHANGE: "draft-change-entry.md",
    STEP_POSITIONING: "draft-positioning.md",
    STEP_UMBRELLA: "draft-umbrella.md",
    STEP_SEGMENT: "draft-segment.md",
}

PROMPT_FILES.update(
    {
        STEP_MESSAGING: "draft-messaging.md",
        STEP_VOICE: "draft-voice.md",
        STEP_BUYER_PERSONAS: "draft-buyer-personas.md",
        STEP_PRODUCT: "draft-product.md",
        STEP_COMPETITORS: "draft-competitors.md",
        STEP_DESIGN: "draft-design.md",
        STEP_GOALS: "draft-goals.md",
        STEP_METRICS: "draft-metric-definitions.md",
        STEP_STANDARD: "draft-standard.md",
    }
)

# Where in the plugin the prompt files live.
PROMPTS_DIR = os.path.join("skills", "join", "references", "prompts")

# Where in the base each step's work is written. Setup writes the current
# layout only (Unit 1.5b); a base laid out before it is read where it is.
ICP_PATH = constants.REQUIRED_CONTEXT_FILES[0]
POSITIONING_PATH = constants.REQUIRED_CONTEXT_FILES[1]
# The path the identifier of setup's context change is worked out from. It is
# the path the profile had when that identifier was first worked out, and it
# stays so, because a setup run picked up after an update has to work out the
# same identifier it worked out before, or it would write the change twice.
ENTRY_ID_SEED_PATH = constants.LEGACY_REQUIRED_CONTEXT_FILES[0]

# What the settings block at the top of each file has to say the file is.
KINDS = {
    STEP_ICP: "icp",
    STEP_CHANGE: constants.ENTRY_KIND,
    STEP_POSITIONING: "positioning",
    # The umbrella is the customer profile, so it calls itself one, and every
    # rule that knows the profile by its kind knows the umbrella the same way.
    STEP_UMBRELLA: "icp",
    STEP_SEGMENT: constants.SEGMENT_KIND,
}

# Each document drafted after setup calls itself by its kind's own key, and
# is written where the list of kinds keeps it.
KINDS.update({step: step for step in DRAFTED_LATER})
LATER_PATHS = {
    kind.key: kind.pattern
    for kind in constants.BASE_KINDS
    if kind.key in DRAFTED_LATER and "<" not in kind.pattern
}

def valid_destination(step: str, where: Optional[str]) -> bool:
    """Whether a remembered destination is one this step may be written to.

    The flat path of its kind, the kind's file in one business's folder
    directly under `context`, or for a standard one standard's path. Nothing
    deeper and nothing else.
    """
    from . import docpaths

    if not where or not isinstance(where, str):
        return False
    found = docpaths.classify(where)
    if found is None or found.path != where:
        return False
    if step == STEP_STANDARD:
        return found.kind == docpaths.KIND_STANDARD
    if step not in (STEP_GOALS, STEP_METRICS) or found.kind != docpaths.KIND_CONTEXT:
        return False
    if where == LATER_PATHS.get(step):
        return True
    parts = where.split("/")
    return (
        len(parts) == 3
        and parts[0] == constants.CONTEXT_DIR
        and re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", parts[1]) is not None
        and parts[2] == step + ".md"
    )


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

# The umbrella's three parts, always, in this order (requirement P18).
UMBRELLA_SECTIONS = constants.UMBRELLA_SECTIONS
# The part of the umbrella that holds one short paragraph per segment, each
# under a level three heading carrying that segment's name.
UMBRELLA_SEGMENTS_SECTION = constants.UMBRELLA_SECTIONS[1]

# The one heading a skipped file is written with.
SKIPPED_HEADINGS = {
    STEP_ICP: "Ideal customer profile",
    STEP_POSITIONING: "Positioning",
    STEP_MESSAGING: "Messaging",
    STEP_VOICE: "Voice guide",
    STEP_BUYER_PERSONAS: "Buyer personas",
    STEP_PRODUCT: "Product",
    STEP_COMPETITORS: "Competitors",
    STEP_DESIGN: "Design guide",
    STEP_GOALS: "Goals",
    STEP_METRICS: "Metric definitions",
}

# The section every document drafted after setup ends with: what the material
# did not show, so a gap is named rather than filled (Track 4).
GAPS_SECTION = "What the material does not show"
# The one sentence a section holds when the material says nothing about it.
# It is the same sentence the documents drafted from the notes write.
NOT_COVERED = "Nothing in the material covers this."
# The sections each one always carries, in this order.
LATER_SECTIONS = {
    STEP_MESSAGING: (
        "Core message",
        "Proof points",
        "Objections and answers",
        "Words we use and avoid",
        GAPS_SECTION,
    ),
    STEP_VOICE: (
        "Principles",
        "Words we use and avoid",
        "By channel",
        GAPS_SECTION,
    ),
    STEP_BUYER_PERSONAS: ("Personas", GAPS_SECTION),
    STEP_PRODUCT: (
        "What has shipped",
        "What is planned",
        "Where pricing lives",
        GAPS_SECTION,
    ),
    STEP_COMPETITORS: ("Alternatives", GAPS_SECTION),
    STEP_DESIGN: (
        "Colour by role",
        "Type",
        "Logo rules",
        "Forbidden devices",
        GAPS_SECTION,
    ),
}
# The part that holds one level three heading per principle, per persona or
# per alternative.
LATER_ITEMS_SECTION = {
    STEP_VOICE: "Principles",
    STEP_BUYER_PERSONAS: "Personas",
    STEP_COMPETITORS: "Alternatives",
}
# A part that may be empty, because an empty list is a real answer: a design
# guide that forbids nothing says so by leaving this part empty (call 3).
LATER_MAY_BE_EMPTY = {STEP_DESIGN: ("Forbidden devices",)}

# Plan 1, Units 2.4a and 3.5. The goals and the metric definitions end with
# what is not decided yet, because what they leave open is a decision nobody
# has made, not material that was missing.
UNDECIDED_SECTION = "What is not decided yet"
LATER_SECTIONS[STEP_GOALS] = ("Goals", UNDECIDED_SECTION)
LATER_SECTIONS[STEP_METRICS] = (
    "Definitions",
    "Counts that are different numbers",
    UNDECIDED_SECTION,
)
# A standard's five parts (Plan 1, Unit 3.5): the rules of a job in words,
# each number living in exactly one other place.
LATER_SECTIONS[STEP_STANDARD] = (
    "The job's goal",
    "What is unacceptable",
    "What needs approval",
    "Checks before work is handed back",
    "How each threshold relates to a goal",
)
LATER_ITEMS_SECTION[STEP_GOALS] = "Goals"
LATER_ITEMS_SECTION[STEP_METRICS] = "Definitions"
# The lines each goal and each definition carries, each holding the person's
# answer or a `[your call: ...]` marker in its place.
ITEM_LINES = {
    STEP_GOALS: ("Target:", "Measured in:"),
    STEP_METRICS: ("Counts:", "Where the number lives:"),
}
# The part a standard may leave as a real empty answer: a job that needs no
# approval says so, and that is kept rather than refused.
LATER_MAY_BE_EMPTY[STEP_STANDARD] = ("What needs approval",)

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
# The profile says which part of the company it covers in a way that is not a
# short name (Unit 1.7a).
CODE_BAD_COVERS = "bad-covers"

# The umbrella holds something a reader could follow somewhere: a link, a web
# address, or the name of a file. Nothing in the umbrella is a link, so it
# never says whether a segment's own file exists (requirement P19).
CODE_LINK = "link"
# The umbrella leaves out a segment the person settled, names one nobody
# settled, says a segment left out is anything but still to come, or says a
# segment that is being drafted or taken in is still to come.
CODE_SEGMENT_MISSING = "segment-missing:%s"
CODE_SEGMENT_NOT_SETTLED = "segment-not-settled"
CODE_SEGMENT_NOT_PENDING = "segment-not-pending:%s"
CODE_SEGMENT_SAID_PENDING = "segment-said-pending:%s"

# A principle of the voice guide with no sentence quoted from the company's
# own writing, a section meant to hold one heading per principle or persona
# that holds none, and prices written into the product rather than pointed at.
CODE_PRINCIPLE_UNQUOTED = "principle-without-a-quote"
CODE_NO_ITEMS = "no-items:%s"
CODE_PRICING_RESTATED = "pricing-restated"
# A figure the draft writes that none of the material it was handed carries.
# A colour code counts as a figure, so the design guide never writes a code
# the brand guide does not state.
CODE_FIGURE_NOT_IN_SOURCES = "figure-not-in-sources"
# A competitor fact without the date and the material it came from, which
# cannot be judged stale (Unit T4.4).
CODE_FACT_UNDATED = "fact-without-a-date-and-source"
# A design guide part the material covers none of, not named under what the
# material does not show (Unit T4.5).
CODE_GAP_UNNAMED = "gap-not-named:%s"
# A picture written into the design guide. Nothing but text is ever written
# into a base by this path (Unit T4.5).
CODE_IMAGE = "image"

# Plan 1, Units 2.4a and 3.5: a goal or a definition missing one of its
# lines, a standard's body holding a digit that is not part of a date, and a
# destination that is not a place this document may go.
CODE_ITEM_LINE = "item-line-missing:%s"
CODE_DIGIT_IN_STANDARD = "digit-in-standard"
CODE_NOT_A_DESTINATION = "not-a-destination"

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
    "condensing": "Condensing your notes.",
    STEP_ICP: "Drafting your ideal customer profile.",
    STEP_CHANGE: "Drafting the context change.",
    STEP_POSITIONING: "Drafting your positioning.",
    STEP_UMBRELLA: "Drafting your customer profile across your segments.",
    STEP_SEGMENT: "Drafting that segment.",
    STEP_MESSAGING: "Drafting your messaging.",
    STEP_VOICE: "Drafting your voice guide.",
    STEP_BUYER_PERSONAS: "Drafting your buyer personas.",
    STEP_PRODUCT: "Drafting your product document.",
    STEP_COMPETITORS: "Drafting your competitors document.",
    STEP_DESIGN: "Drafting your design guide.",
    STEP_GOALS: "Drafting your goals.",
    STEP_METRICS: "Drafting your metric definitions.",
    STEP_STANDARD: "Drafting the standard for that job.",
    "saving": "Saving that into the base.",
}


# --- Building the request ----------------------------------------------------


class Assembly(object):
    """The text of one request, and what had to be left out to build it."""

    __slots__ = (
        "text",
        "codes",
        "included_labels",
        "dropped_labels",
        "ordered_labels",
        "material",
    )

    def __init__(
        self,
        text,
        codes=None,
        included_labels=None,
        dropped_labels=None,
        ordered_labels=None,
        material="",
    ):
        self.text = text
        # The fenced material alone, without the prompt around it, which is
        # what a draft's figures are checked against (Track 4).
        self.material = material
        self.codes = list(codes or [])
        self.included_labels = list(included_labels or [])
        self.dropped_labels = list(dropped_labels or [])
        # Every source this step was handed, in the order the step wanted
        # them, whether it got to them or not.
        self.ordered_labels = list(ordered_labels or [])

    def __repr__(self) -> str:
        return "Assembly(included=%r, dropped=%r)" % (
            self.included_labels,
            self.dropped_labels,
        )


class SourcePlan(object):
    """Which sources one step reads, in which order, and which it cannot."""

    __slots__ = ("ordered", "included", "dropped", "fences")

    def __init__(self, ordered, included, dropped, fences):
        self.ordered = list(ordered)
        self.included = list(included)
        self.dropped = list(dropped)
        self.fences = list(fences)

    @property
    def ordered_labels(self):
        return [source_line(source) for source in self.ordered]

    @property
    def included_labels(self):
        return [source_line(source) for source in self.included]

    @property
    def dropped_labels(self):
        return [source_line(source) for source in self.dropped]

    @property
    def clamped(self) -> bool:
        return any(getattr(source, "clamped", False) for source in self.included)

    @property
    def codes(self):
        codes = [CODE_SOURCES_CAPPED] if self.dropped else []
        if self.clamped:
            codes.append(CODE_DATE_CLAMPED)
        return codes

    def __repr__(self) -> str:
        return "SourcePlan(included=%d, dropped=%d)" % (
            len(self.included),
            len(self.dropped),
        )


# How far into a source the first heading is looked for. A heading further
# down than this is not what the document is about.
HEADING_SEARCH_LINES = 40


def _first_heading(source) -> str:
    """The first heading line of a source, or nothing when it has none."""
    text = getattr(source, "text", "") or ""
    for line in text.split("\n", HEADING_SEARCH_LINES)[:HEADING_SEARCH_LINES]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped
    return ""


def _is_wanted_first(source, words) -> bool:
    """Whether the name of a source, or its first heading, says it belongs."""
    where = (str(getattr(source, "label", "")) + " " + _first_heading(source)).casefold()
    return any(word in where for word in words)


def order_sources(
    step: str, sources: Sequence["sources_module.Source"], first_path=None
):
    """Put the sources this step most wants first, and keep the rest in order.

    Nothing is dropped here. The cap is what drops things, and it drops from
    the end, so the only job of this is to make sure the end is the material
    the document being drafted has least to do with. The first real run showed
    why: a folder was read in the order the folder happened to hold it, the cap
    was reached, and every one of the fourteen files describing who the company
    sells to sat past it while the profile was drafted from one file about
    messaging.

    Templates and read-me files go last of all, whatever step it is and
    whatever their names say they are about (Unit 1.6). The third real run
    spent room on templates while a finished document sat past the cap, and a
    template is the shape of a document with nothing of the business in it,
    so it is the first thing the cap should reach.
    """
    ordered = _ordered(step, sources)
    if first_path:
        # A segment's own page goes first whatever its name says, so the cap
        # never leaves out the one document about it (finding 3 of Unit
        # 1.7b's correctness review).
        wanted = os.path.realpath(first_path)
        pinned = [
            source
            for source in ordered
            if getattr(source, "path", None)
            and os.path.realpath(source.path) == wanted
        ]
        ordered = pinned + [source for source in ordered if source not in pinned]
    return ordered


def _ordered(step: str, sources):
    listed = [source for source in sources if not is_template_or_readme(source)]
    last = [source for source in sources if is_template_or_readme(source)]
    if step == STEP_CHANGE:
        # What a context change wants first is the most recent material, so
        # the dated sources lead, newest first, and the undated follow in the
        # order they were listed.
        dated = [source for source in listed if getattr(source, "date", None)]
        undated = [source for source in listed if not getattr(source, "date", None)]
        dated.sort(key=lambda source: str(source.date), reverse=True)
        return dated + undated + last
    words = constants.DRAFT_RELEVANCE.get(step, ())
    if not words:
        return listed + last
    wanted = [source for source in listed if _is_wanted_first(source, words)]
    rest = [source for source in listed if not _is_wanted_first(source, words)]
    return wanted + rest + last


def _words_in(text: str):
    return [word for word in re.split(r"[^a-z0-9]+", str(text or "").casefold()) if word]


def is_template_or_readme(source) -> bool:
    """Whether a source is a template or a read-me, by its name or first heading.

    The words are matched whole, so a file of email templates and a finished
    positioning built on somebody's template are not taken for templates. A
    heading counts only when it is short, as the title of a template is, such
    as "Launch brief template" (finding 5 of the unit's correctness review).
    """
    label = str(getattr(source, "label", "") or "")
    name_words = _words_in(os.path.splitext(label)[0])
    if any(word in name_words for word in constants.DRAFT_LAST_NAMES):
        return True
    if any(word in name_words for word in constants.DRAFT_LAST_WORDS):
        return True
    heading_words = _words_in(_first_heading(source))
    return len(heading_words) <= 5 and any(
        word in heading_words for word in constants.DRAFT_LAST_WORDS
    )


def plan_sources(
    step: str, sources: Sequence["sources_module.Source"], first_path=None
) -> SourcePlan:
    """Order the sources for one step and say which of them fit in a request.

    Whole sources are dropped from the end of the ordered list, never the
    middle of one, because half a document read is worse than a document not
    read at all.
    """
    ordered = order_sources(step, sources, first_path)
    included: List["sources_module.Source"] = []
    dropped: List["sources_module.Source"] = []
    fences: List[str] = []
    used = 0
    for source in ordered:
        fenced = sources_module.fence(source)
        if dropped or used + len(fenced) > constants.DRAFT_SOURCES_MAX_CHARS:
            dropped.append(source)
            continue
        used += len(fenced)
        fences.append(fenced)
        included.append(source)
    return SourcePlan(ordered, included, dropped, fences)


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


def said_as_data(label: str, text: str) -> str:
    """Words the person gave, held apart as data inside the request.

    The names of their segments and what their base is for are their own
    words, so they go into a request exactly the way their documents do:
    inside a fence, after the sentence saying that what follows is data and
    not instructions.
    """
    source = sources_module.paste_source(label, str(text or ""))
    return sources_module.fence(source).rstrip("\n")


def assemble(
    step: str,
    sources: Sequence["sources_module.Source"],
    company: str,
    today,
    owner_email: str,
    icp_path: Optional[str] = None,
    plugin_root: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
    first_path: Optional[str] = None,
) -> Assembly:
    """Build the request for one step out of the prompt file and the sources.

    Every source is fenced, so the sentence saying that what follows is the
    person's own writing rather than instructions is said once per source and
    said before the source says anything. The sources are put in the order this
    step wants them first, and when they are together longer than the cap,
    whole sources are dropped from the end of that order, never the middle of
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

    plan = plan_sources(step, sources, first_path)
    included = plan.included_labels

    if sources and not plan.fences:
        raise DraftError(step, CODE_NO_SOURCES)

    listing = ["The sources you may read, with the date on each one that has a date:"]
    listing.extend("- " + line for line in included)
    block = "\n".join(listing) + "\n\n" + "\n".join(plan.fences)

    values = {
        "sources": block,
        "company": name,
        "today": str(today or ""),
        "owner_email": str(owner_email or ""),
        "icp_path": str(icp_path or ICP_PATH),
    }
    # What the umbrella and a segment are also told: the settled segments,
    # the one segment being drafted, and what the base is for. The caller
    # hands each in already held apart as data.
    for field, value in (extra or {}).items():
        values[field] = str(value or "")
    text = template
    for field, value in values.items():
        text = text.replace("{{%s}}" % field, value)

    return Assembly(
        text,
        plan.codes,
        included,
        plan.dropped_labels,
        plan.ordered_labels,
        # A competitor fact is dated with the date its material's label
        # carries, so for that document the listing counts as material too.
        material=block if step == STEP_COMPETITORS else "\n".join(plan.fences),
    )


def assemble_from_notes(
    step: str,
    notes_text: str,
    file_lines: Sequence[str],
    company: str,
    today,
    owner_email: str,
    codes: Sequence[str] = (),
    icp_path: Optional[str] = None,
    plugin_root: Optional[str] = None,
    extra: Optional[Dict[str, str]] = None,
) -> Assembly:
    """Build the request for one step from the checked notes (summarize-first).

    The draft reads the notes taken from every file, already fenced as data,
    and never the files themselves, so nothing is left out of it for room and
    every line it writes can say which note it rests on. The files are listed
    by their number in this run, the way the notes name them.
    """
    template = prompt_text(step, plugin_root)
    name = _checked_company(step, company)
    listing = ["The files these notes were taken from, each with its number:"]
    listing.extend("- " + line for line in file_lines)
    values = {
        "sources": "\n".join(listing) + "\n\n" + notes_text,
        "company": name,
        "today": str(today or ""),
        "owner_email": str(owner_email or ""),
        "icp_path": str(icp_path or ICP_PATH),
    }
    for field, value in (extra or {}).items():
        values[field] = str(value or "")
    text = template
    for field, value in values.items():
        text = text.replace("{{%s}}" % field, value)
    return Assembly(text, list(codes), list(file_lines), [], list(file_lines))


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

    __slots__ = (
        "step",
        "text",
        "fields",
        "body",
        "codes",
        "only_if_signal_present",
        "destination",
    )

    def __init__(
        self,
        step,
        text,
        fields,
        body,
        codes=None,
        only_if_signal_present=None,
        destination=None,
    ):
        self.step = step
        self.text = text
        self.fields = dict(fields or {})
        self.body = body
        self.codes = list(codes or [])
        self.only_if_signal_present = list(only_if_signal_present or [])
        # Where a segment's draft goes, worked out from the settled inventory
        # by the caller and never read off the draft.
        self.destination = destination

    @property
    def path(self) -> str:
        """Where in the base this draft belongs, for the context files."""
        if self.step in PROFILE_STEPS:
            return ICP_PATH
        if self.step == STEP_POSITIONING:
            return POSITIONING_PATH
        if self.step == STEP_SEGMENT and self.destination:
            return self.destination
        if self.step in DESTINED_STEPS and self.destination:
            return self.destination
        if self.step in LATER_PATHS:
            return LATER_PATHS[self.step]
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


_SOURCES_KEY_RE = re.compile(r"^(sources?)\s*:(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s*-(?:\s+(.*)|)$")
_FILE_LABEL_RE = re.compile(
    r"^[^\s\[\],][^\[\],]*(?:%s)(?: \(\d{4}-\d{2}-\d{2}\))?$"
    % "|".join(
        re.escape(suffix)
        for suffix in sorted(
            set(constants.SOURCE_READABLE_SUFFIXES) | set(constants.SOURCE_EXPORT_SUFFIXES)
        )
    ),
    re.IGNORECASE,
)


def _unquoted(item: str) -> str:
    item = item.strip()
    if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
        return item[1:-1].strip()
    return item


def _unnamed(items: Sequence[str]) -> List[str]:
    """The items that are not a file's name, which the word checks still read.

    A file's name ends in a file ending the plugin reads or lists, so text
    that only ends like one, such as "e.g" or "v2.1", is still read.
    """
    return [item for item in items if not _FILE_LABEL_RE.match(_unquoted(item))]


def _without_source_labels(text: str) -> str:
    """The draft as the word checks read it: the files it cites left out.

    A file is named whatever somebody called it, so a source called todo.md
    is a source and not a placeholder. Only an item of the sources line (or a
    change entry's source line, or one item per line under either) that is
    shaped like a file's name, with or without the date beside it, is left
    out. Anything else on that line, such as an unfilled TBD, is still read,
    and so is everything a draft says in its own words (the replay of
    2026-10-10, case two, and the correctness review of its fix).
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != formats.FRONTMATTER_FENCE:
        return text
    closing = None
    for index in range(1, len(lines)):
        if lines[index].strip() == formats.FRONTMATTER_FENCE:
            closing = index
            break
    if closing is None:
        return text
    kept = [lines[0]]
    in_sources = False
    for line in lines[1:closing]:
        key = _SOURCES_KEY_RE.match(line)
        item = _LIST_ITEM_RE.match(line)
        if key:
            value = key.group(2).strip()
            in_sources = not value
            if value.startswith("[") and value.endswith("]"):
                items = value[1:-1].split(",") if value[1:-1].strip() else []
                line = "%s: [%s]" % (key.group(1), ", ".join(i.strip() for i in _unnamed(items)))
            elif value:
                line = "%s: %s" % (key.group(1), ", ".join(i.strip() for i in _unnamed([value])))
        elif in_sources and item:
            if not _unnamed([item.group(1) or ""]):
                continue
        else:
            in_sources = False
        kept.append(line)
    return "\n".join(kept + lines[closing:])


def without_setup_sections(text: str) -> str:
    """A document without the sections setup writes itself from the notes.

    Those sections hold the material's own words, copied and checked against
    its files, and the file each came from, so they are not held to the words
    a draft may use, and a file's name in them is not a link. Review refuses
    any draft that writes one of these headings itself, so only setup's own
    sections are ever read this way.
    """
    kept: List[str] = []
    skipping = False
    for line in str(text or "").split("\n"):
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            skipping = any(stripped.startswith(head) for head in constants.SETUP_WRITTEN_HEADINGS)
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


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
    # Only a document written from the notes has sections setup writes, so
    # only its words are read without them (the correctness review, M12).
    exempt = step in (STEP_ICP, STEP_UMBRELLA, STEP_POSITIONING, STEP_SEGMENT)
    check_words(step, _without_source_labels(without_setup_sections(text) if exempt else text))

    try:
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        raise DraftError(step, CODE_NO_FRONTMATTER)

    if step == STEP_CHANGE:
        # A model that learned the older names for these two settings is not
        # wrong about the change, only about what it is called, so the older
        # spelling is read and the draft is saved under the name in use.
        # Nothing is written out again when nothing was folded, because
        # writing a draft out again is a change to it, and a draft that says
        # the right thing already should come back exactly as it arrived.
        try:
            folded = formats._fold_field_names(fields)
        except (ValidationError, PathError) as failure:
            raise DraftError(step, failure.code or CODE_MISSING_FIELD % "kind")
        if folded != fields:
            fields = folded
            try:
                text = formats.render_document(fields, body)
            except (ValidationError, PathError) as failure:
                raise DraftError(
                    step, failure.code or CODE_MISSING_FIELD % "kind"
                )

    required = (
        formats.CHANGE_REQUIRED if step == STEP_CHANGE else CONTEXT_FIELDS
    )
    for name in required:
        if name not in fields:
            raise DraftError(step, CODE_MISSING_FIELD % name)
    if step != STEP_CHANGE:
        # The two context files carry exactly the five settings this plugin
        # writes and reads. Anything else is refused rather than carried into
        # the base, because a setting nothing here checks would sit in the file
        # unread, and a line nobody reads is a line anything could be put on.
        for name in sorted(fields):
            if name == constants.COVERS_FIELD and step in PROFILE_STEPS:
                # Which part of the company the base is for (Unit 1.7a). It is
                # read here only so a profile carrying it can be read back;
                # what it says is always written by GTM Base from the answer
                # the person gave, never taken from a draft.
                try:
                    validate.validate_covers(fields[name])
                except ValidationError:
                    raise DraftError(step, CODE_BAD_COVERS)
                continue
            if name not in CONTEXT_FIELDS:
                raise DraftError(step, CODE_UNKNOWN_FIELD % name)
    said_kind = str(fields.get("kind", "")).strip()
    if step == STEP_CHANGE:
        # An entry that calls itself by the older name is still an entry, and
        # it is written back out under the name in use.
        if said_kind not in constants.ENTRY_KINDS:
            raise DraftError(step, CODE_WRONG_KIND)
        if said_kind != KINDS[step]:
            fields["kind"] = KINDS[step]
            try:
                text = formats.render_document(fields, body)
            except (ValidationError, PathError) as failure:
                raise DraftError(
                    step, failure.code or CODE_MISSING_FIELD % "kind"
                )
    elif said_kind != KINDS[step]:
        raise DraftError(step, CODE_WRONG_KIND)

    present: List[str] = []
    if step in (STEP_ICP, STEP_SEGMENT):
        # A segment is drafted at the depth of a whole profile, never as a
        # shorter summary of one, so it carries the same four parts.
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
    if step == STEP_UMBRELLA:
        sections = {
            name.strip().lower(): value
            for name, value in formats.split_sections(body).items()
        }
        for heading in UMBRELLA_SECTIONS:
            if not sections.get(heading.lower(), "").strip():
                raise DraftError(step, CODE_EMPTY_SECTION % heading)
        if _holds_a_link(without_setup_sections(body)):
            raise DraftError(step, CODE_LINK)
    if step in DRAFTED_LATER:
        check_later_shape(step, body)

    return Draft(step, text, fields, body, [], present)


# A sentence quoted from somebody's own writing: a quoted line, or words in
# quotation marks, straight or curly, at least three words long.
_QUOTE_RE = re.compile(
    r'(?m)^\s*>\s*\S|"[^"\n]*\S\s+\S+\s+\S[^"\n]*"|\u201c[^\u201d\n]*\S\s+\S+\s+\S[^\u201d\n]*\u201d'
)
# A price written out: a currency sign and a digit.
_PRICE_RE = re.compile(r"[$\u20ac\u00a3]\s?\d")


def _level_three(text: str) -> List[tuple]:
    """Each level three heading in a part, with the text under it."""
    found: List[tuple] = []
    heading = None
    lines: List[str] = []
    for line in str(text or "").split("\n"):
        match = re.match(r"^\s{0,3}###\s+(.*?)\s*#*\s*$", line)
        if match:
            if heading is not None:
                found.append((heading, "\n".join(lines)))
            heading, lines = match.group(1), []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        found.append((heading, "\n".join(lines)))
    return found


def check_later_shape(step: str, body: str) -> None:
    """The parts a document drafted after setup always carries, and their rules.

    Every part is there and holds something, if only the sentence saying the
    material covers none of it. The voice guide's principles each carry a
    sentence quoted from the company's own writing, because a voice guide
    written in the assistant's voice is worse than none. The principles and
    the personas each sit under a heading of their own. The product says
    where pricing lives and never writes a price.
    """
    sections = {
        name.strip().lower(): value
        for name, value in formats.split_sections(body).items()
    }
    may_be_empty = LATER_MAY_BE_EMPTY.get(step, ())
    for heading in LATER_SECTIONS[step]:
        if heading in may_be_empty and heading.lower() in sections:
            continue
        if not sections.get(heading.lower(), "").strip():
            raise DraftError(step, CODE_EMPTY_SECTION % heading)
    if step == STEP_STANDARD and digits_outside_dates(body):
        raise DraftError(step, CODE_DIGIT_IN_STANDARD)
    items_heading = LATER_ITEMS_SECTION.get(step)
    if items_heading is not None:
        part = sections.get(items_heading.lower(), "")
        if part.strip() != NOT_COVERED:
            items = _level_three(part)
            if not items:
                raise DraftError(step, CODE_NO_ITEMS % items_heading)
            if step == STEP_VOICE and any(
                not _QUOTE_RE.search(text) for _heading, text in items
            ):
                raise DraftError(step, CODE_PRINCIPLE_UNQUOTED)
            if step == STEP_COMPETITORS and any(
                not _facts_dated(text) for _heading, text in items
            ):
                raise DraftError(step, CODE_FACT_UNDATED)
            for label in ITEM_LINES.get(step, ()):
                for _heading, text in items:
                    if not _line_after(text, label):
                        raise DraftError(step, CODE_ITEM_LINE % label.rstrip(":"))
    if step == STEP_PRODUCT and _PRICE_RE.search(
        sections.get("where pricing lives", "")
    ):
        raise DraftError(step, CODE_PRICING_RESTATED)
    if step == STEP_DESIGN:
        if _IMAGE_RE.search(body):
            raise DraftError(step, CODE_IMAGE)
        gaps = " ".join(sections.get(GAPS_SECTION.lower(), "").lower().split())
        for heading in LATER_SECTIONS[step]:
            if heading == GAPS_SECTION:
                continue
            if sections.get(heading.lower(), "").strip() == NOT_COVERED and (
                _gap_word(heading) not in gaps
            ):
                raise DraftError(step, CODE_GAP_UNNAMED % heading)


# One competitor fact: a line of its own, ending with the material it came
# from and that material's date, as "(source: the pricing page, 2026-10-02)".
_FACT_RE = re.compile(r"\(source:\s*[^()\n]*\S[^()\n]*,\s*\d{4}-\d{2}-\d{2}\)\s*\.?\s*$")
# A picture in a document: the usual image markup, an image tag, or an image
# carried inside a link as data.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(|<img\b|data:image/", re.IGNORECASE)
# A colour code as a brand guide writes one: a hash and three, six or eight
# hexadecimal digits, or an rgb or hsl value.
_COLOUR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9A-Za-z])|\b(?:rgba?|hsla?)\([^)]*\)",
)


def _facts_dated(text: str) -> bool:
    """Whether every line under one alternative is a fact with its source and date.

    An alternative the material names with no claim about it is left empty,
    or holds only the sentence saying the material covers none of it.
    """
    lines = [line.strip() for line in str(text or "").split("\n") if line.strip()]
    if lines == [NOT_COVERED]:
        return True
    return all(_FACT_RE.search(line) for line in lines)


def _gap_word(heading: str) -> str:
    """The word a gap is named by: the heading's first word that says what it is."""
    return {
        "Colour by role": "colour",
        "Type": "type",
        "Logo rules": "logo",
        "Forbidden devices": "forbidden",
    }.get(heading, heading.lower())


def colour_codes_in(text: str) -> List[str]:
    """Every colour code a text carries, written the one way codes are compared."""
    found = []
    for match in _COLOUR_RE.finditer(str(text or "")):
        code = re.sub(r"\s+", "", match.group(0)).lower()
        if code not in found:
            found.append(code)
    return found


def _line_after(text: str, label: str) -> str:
    """What one labelled line of an item says, or nothing when it is missing or empty."""
    for line in str(text or "").split("\n"):
        cleaned = line.strip().lstrip("-*").strip()
        if cleaned.lower().startswith(label.lower()):
            return cleaned[len(label):].strip()
    return ""


# A date written the one way the base writes dates, which the digit lint
# lets through.
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def digits_outside_dates(body: str) -> List[int]:
    """The line numbers of a standard's body that hold a digit outside a date.

    A number lives in exactly one place: a business goal in the goals, an
    engine threshold in the engine's own settings (Plan 1, P41). So a
    standard holds none. Number words are not caught here; the prompt forbids
    them and the owner's read checks them.
    """
    found = []
    for number, line in enumerate(str(body or "").split("\n"), start=1):
        if re.search(r"\d", _DATE_RE.sub("", line)):
            found.append(number)
    return found


def later_destination(
    step: str,
    base_root: Optional[str] = None,
    business: Optional[str] = None,
    job: Optional[str] = None,
) -> str:
    """Where a goals, metric definitions or standard draft goes, or a refusal.

    Goals and metric definitions go flat at their kind's path when no
    business is named, and in the named business's folder under `context`
    when the map lists that business (Plan 1, call 1). A standard goes at
    `standards/<job>.md`, and a job is always named.
    """
    from . import businesses, docpaths

    if step == STEP_STANDARD:
        if business or not job:
            raise DraftError(step, CODE_NOT_A_DESTINATION)
        found = docpaths.classify("%s/%s.md" % (constants.STANDARDS_DIR, job))
        if found is None or found.kind != docpaths.KIND_STANDARD:
            raise DraftError(step, CODE_NOT_A_DESTINATION)
        return found.path
    if step not in (STEP_GOALS, STEP_METRICS) or job:
        raise DraftError(step, CODE_NOT_A_DESTINATION)
    if not business:
        return LATER_PATHS[step]
    from . import base_reader

    try:
        listed = [
            one.slug
            for one in businesses.read_map_businesses(base_reader.map_text(base_root))
        ] if base_root else []
    except (ValidationError, PathError):
        listed = []
    if business not in listed:
        raise DraftError(step, CODE_NOT_A_DESTINATION)
    return "%s/%s/%s.md" % (constants.CONTEXT_DIR, business, step)


def figures_in(text: str) -> List[str]:
    """Every figure the text carries, evened out the way a quote is matched."""
    from . import citations, notes as notes_module

    found = list(colour_codes_in(text))
    for figure in citations._figures(_COLOUR_RE.sub(" ", str(text or ""))):
        evened = notes_module.even_out(figure)
        if evened and evened not in found:
            found.append(evened)
    return found


def figures_beyond(body: str, allowed: Sequence[str]) -> List[str]:
    """The figures a draft's body writes that none of its material carries.

    A figure matches only whole, unit and all, so 14 never stands for 14% and
    a price never stands for a count (the same rule the notes are held to).
    """
    from . import citations

    pool = " ; ".join(str(one) for one in (allowed or ()))
    known = set(colour_codes_in(pool))
    written = _without_source_labels(str(body or ""))
    beyond = [code for code in colour_codes_in(written) if code not in known]
    # A colour code is read whole, so its digits are not also read as figures.
    written = _COLOUR_RE.sub(" ", written)
    return beyond + [
        figure
        for figure in citations._figures(written)
        if not citations._figure_in(figure, pool)
    ]


# Anything a reader could follow: a link written the usual way, a link in angle
# brackets, a web address, a wiki link, or the name of a document file.
_LINK_RE = re.compile(
    r"\]\(|\[\[|<\s*[a-z][a-z0-9+.-]*:|\b(?:https?|ftp|file)://|\bwww\.|"
    r"[A-Za-z0-9_/-]+\.md\b",
    re.IGNORECASE,
)


def _holds_a_link(text: str) -> bool:
    return bool(_LINK_RE.search(str(text or "")))


def segment_paragraphs(body: str) -> List[tuple]:
    """Each segment the umbrella names, and the paragraph under its name.

    A segment is a level three heading inside the part named Segments, and its
    paragraph runs to the next heading of any size. What comes back is the
    heading's words and the paragraph, in the order they were written.
    """
    found: List[tuple] = []
    inside = False
    current = None
    lines: List[str] = []
    for line in str(body or "").split("\n"):
        stripped = line.strip()
        level = len(stripped) - len(stripped.lstrip("#")) if stripped.startswith("#") else 0
        if level and stripped[level:level + 1] not in (" ", "\t"):
            level = 0
        if level == 2:
            if current is not None:
                found.append((current, "\n".join(lines).strip()))
                current = None
            inside = stripped[2:].strip().lower() == UMBRELLA_SEGMENTS_SECTION.lower()
            lines = []
            continue
        if level == 1:
            if current is not None:
                found.append((current, "\n".join(lines).strip()))
                current = None
            inside = False
            continue
        if not inside:
            continue
        if level == 3:
            if current is not None:
                found.append((current, "\n".join(lines).strip()))
            current = stripped[3:].strip()
            lines = []
            continue
        if level:
            # A heading smaller than a segment's belongs to that segment.
            lines.append(line)
            continue
        if current is not None:
            lines.append(line)
    if current is not None:
        found.append((current, "\n".join(lines).strip()))
    return found


def check_umbrella(draft, inventory) -> List[str]:
    """What is wrong with an umbrella, measured against the settled inventory.

    Every segment the person settled is named once, by its own name, under
    Segments; no segment nobody settled is named; a segment left out says it
    is still to come, in the fixed words, and nothing else does. Nothing here
    looks at whether any segment's file exists, because the umbrella never
    says, and the codes carry the file name GTM Base made and never a word
    the draft wrote.
    """
    from . import segments as segments_module

    codes: List[str] = []
    written = {}
    for heading, paragraph in segment_paragraphs(getattr(draft, "body", "")):
        slug = segments_module.slug_for(heading)
        if slug in written:
            codes.append(CODE_SEGMENT_NOT_SETTLED)
            continue
        written[slug] = paragraph
    settled = dict((segment.slug, segment) for segment in inventory.segments)
    pending = " ".join(constants.UMBRELLA_PENDING_SENTENCE.split()).casefold()
    for slug, segment in settled.items():
        paragraph = written.get(slug)
        if paragraph is None or not paragraph.strip():
            codes.append(CODE_SEGMENT_MISSING % slug)
            continue
        says_pending = pending in " ".join(paragraph.split()).casefold()
        if segment.answer == constants.SEGMENT_LEAVE_OUT and not says_pending:
            codes.append(CODE_SEGMENT_NOT_PENDING % slug)
        if segment.answer != constants.SEGMENT_LEAVE_OUT and says_pending:
            codes.append(CODE_SEGMENT_SAID_PENDING % slug)
    for slug in written:
        if slug not in settled and CODE_SEGMENT_NOT_SETTLED not in codes:
            codes.append(CODE_SEGMENT_NOT_SETTLED)
    return codes


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
