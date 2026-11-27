"""The plain-language lint every user-facing document must pass.

User-facing documents are written for a marketer, so they never use the words a
version-control tool uses, and they never use an em dash or an en dash. Later
units import this helper rather than repeating the rules.

Unit 1.1b adds four mechanical checks on top of those two, a registry of the
sentences a person reads that are held in Python rather than in a document, and
an exemption list for the texts that fail a check today. The four checks are a
floor and nothing more. What the standard is actually judged by is the owner
reading a step aloud, which no program can do. `docs/ux-standard.md` says so in
the same words.

The four checks are:

1. A step opens by saying what it is for, before it tells anybody to do
   anything.
2. A step asks for at most one thing, counted as delimited request blocks
   rather than as question marks, because a request can be an imperative.
3. What a person is shown in a step can be read in seconds, measured as a run
   of plain prose lines against a cap. A complete artifact a person approves,
   such as a whole cleaned document, sits in its own marked block and the cap
   does not apply to it.
4. A context change shown to a person is the four labeled lines, in order.

Checks one, two and three read a step section. A step section is a heading
whose title begins with the word "Step", or any section carrying the step
marker on the line under its heading. Sections nobody has marked are not
checked, so a later unit opts its own rewritten step in by marking it.
"""

import ast
import os
import re

from gtmbase import constants


EM_DASH = "\u2014"  # the em dash, written as an escape so the file holds none
EN_DASH = "\u2013"  # the en dash, written as an escape so the file holds none

# Inflections the lint must catch alongside each banned word.
_INFLECTIONS = {
    "commit": ["commit", "commits", "commited", "committed", "committing"],
    "branch": ["branch", "branches", "branched", "branching"],
    "pull request": ["pull request", "pull requests"],
    "merge": ["merge", "merges", "merged", "merging"],
    "rebase": ["rebase", "rebases", "rebased", "rebasing"],
    "clone": ["clone", "clones", "cloned", "cloning"],
}


def _pattern_for(word):
    forms = _INFLECTIONS.get(word, [word])
    alternatives = "|".join(re.escape(form).replace("\\ ", r"\s+") for form in forms)
    return re.compile(r"\b(?:" + alternatives + r")\b", re.IGNORECASE)


_PATTERNS = [(word, _pattern_for(word)) for word in constants.BANNED_GIT_WORDS]


def find_banned(text):
    """Return a list of (word, line_number) for every banned word found."""
    found = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for word, pattern in _PATTERNS:
            if pattern.search(line):
                found.append((word, line_number))
    return found


def find_dashes(text):
    """Return a list of (dash, line_number) for every em dash and en dash."""
    found = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line:
            found.append((EM_DASH, line_number))
        if EN_DASH in line:
            found.append((EN_DASH, line_number))
    return found


# --- The words the rename took out of everything a person reads --------------

# The two words Unit 1.4 took out of every sentence a person reads. "Decision"
# is too narrow for what the base tracks, because a competitor's launch and a
# price change are not decisions anybody made, and the live run needed three
# explanations of it. "Ledger" is a bookkeeping word for a folder of dated
# notes and nobody outside this code used it.
FRONTMATTER_FENCE = "---"

# A whole line of `name=value` pairs and nothing else, which is how a
# confirmation is written down. It is a record, not a sentence, and each of its
# values comes from a fixed vocabulary the file formats check.
_RECORD_LINE_RE = re.compile(r"^(?:[a-z_]+=\S+)(?:\s+[a-z_]+=\S+)+$")

# A span between backticks, which is a literal being named and not a word.
_CODE_SPAN_RE = re.compile(r"`[^`]*`")

# A settings line, which is what has to follow a line of three dashes before
# that line counts as the top of a settings block.
_SETTING_RE = re.compile(r"^[A-Za-z0-9_-]+:")

# Settings whose value is a sentence somebody reads rather than a machine
# value. A skill's description is shown in the list of skills.
READ_AS_SENTENCES = ("description",)


def _opens_a_block(lines, index):
    """Whether the line of three dashes at this index opens a settings block."""
    if index == 0:
        return True
    for line in lines[index + 1 :]:
        if not line.strip():
            continue
        return bool(_SETTING_RE.match(line.strip()))
    return False

_PERSON_FACING_INFLECTIONS = {
    "decision": ["decision", "decisions"],
    "ledger": ["ledger", "ledgers"],
}

_PERSON_FACING_PATTERNS = [
    (
        word,
        re.compile(
            r"\b(?:"
            + "|".join(
                re.escape(form) for form in _PERSON_FACING_INFLECTIONS[word]
            )
            + r")\b",
            re.IGNORECASE,
        ),
    )
    for word in constants.BANNED_PERSON_FACING_WORDS
]


# The one place the older word still has to be written out: the name of the
# folder a base set up before the rename really holds. A path is not a word for
# what the base tracks, and a person told to look in the wrong folder is worse
# off than one who read the word once.
_LEGACY_FOLDER = constants.LEGACY_CHANGES_DIR

# The other places the older word is somebody else's name for something and
# not ours. The client's own tool-use interface calls the yes or no it returns
# a permission decision, and its fields are spelled that way, so a file that
# explains what it does with them has to write the name it is given.
_NOT_OUR_WORD = (
    "permission decision",
    "permissionDecision",
    "permissionDecisionReason",
    "decision-control",
)


def _prose_lines(text):
    """Every line of a document that a person reads as a sentence.

    The settings block at the top of a file, and any settings block shown
    inside an example, are left out. What is in one is a value from a fixed
    vocabulary that the file formats check for themselves, such as `origin` or
    `mode`. Some of those vocabularies were written before the rename and are
    recorded in the files of every base that already exists, so they cannot be
    spelled differently now without making those files unreadable. Nobody
    reads them as words, and every sentence around them is checked.
    """
    lines = text.splitlines()
    inside = False
    for line_number, line in enumerate(lines, start=1):
        if line.strip() == FRONTMATTER_FENCE:
            if inside:
                inside = False
                continue
            # A line of three dashes on its own is a rule far more often than
            # it is the top of a settings block. It only opens one at the very
            # top of a file, or when a setting really follows it. Reading
            # every one of them as a block is how a rule halfway down a file
            # switched the whole check off for everything below it.
            if _opens_a_block(lines, line_number - 1):
                inside = True
            continue
        if inside:
            # The value of a description is the first thing a person reads
            # about a skill, so it is read as a sentence and not as a setting.
            name, separator, value = line.partition(":")
            if separator and name.strip() in READ_AS_SENTENCES:
                yield line_number, value
            continue
        if _RECORD_LINE_RE.match(line.strip()):
            continue
        yield line_number, line


def find_banned_person_facing(text):
    """Return a list of (word, line_number) for each word a person must not read."""
    found = []
    for line_number, line in _prose_lines(text):
        # Anything in backticks is a literal being named rather than a word
        # being used, which is how a file path, a setting, and this standard's
        # own table of what is banned all say the older word without a person
        # ever reading it as our name for anything.
        readable = _CODE_SPAN_RE.sub(" ", line)
        readable = readable.replace(_LEGACY_FOLDER, " ")
        for phrase in _NOT_OUR_WORD:
            readable = readable.replace(phrase, " ")
        for word, pattern in _PERSON_FACING_PATTERNS:
            if pattern.search(readable):
                found.append((word, line_number))
    return found


# The short form only counts where it is being used as the name of a thing,
# which in practice means a word like "the" or "this" in front of it. "Changes"
# on its own is the ordinary English verb far more often than it is the name of
# what the base tracks, and a check that fired on every one of those would be
# turned off inside a week.
_SHORT_FORM_RE = re.compile(
    r"\b(?:the|a|an|this|that|each|one|every|these|those|its|their)\s+changes?\b",
    re.IGNORECASE,
)


def find_short_form_first(text):
    """Return the line number where "change" is read before "context change".

    The short form is allowed, and the rule is only about which comes first.
    A reader who meets a bare "change" before the full term has not been told
    what kind of change is meant.

    This is a floor and it says so. It only checks a text that uses the full
    term somewhere, because "change" in ordinary English is the commonest word
    in this whole repository and a check that fired on every one of them would
    be turned off inside a week. A text that talks about what the base tracks
    and never once says the full term is caught by the owner reading it aloud,
    which is what `docs/ux-standard.md` says the standard is judged by.
    """
    # Line breaks become single spaces so a term wrapped across two lines is
    # still one term. Nothing else moves, so every offset still points at the
    # same character of the original.
    flat = text.replace("\n", " ")
    full_at = flat.lower().find(constants.CONTEXT_CHANGE_TERM)
    if full_at < 0:
        return None
    short = _SHORT_FORM_RE.search(flat)
    if short is None or short.start() >= full_at:
        return None
    return text.count("\n", 0, short.start()) + 1


# --- The paths the move to the CLASS layout left behind (Unit 1.5b) ---------

# A base is laid out by the five CLASS parts, and a person is never told to
# look in a folder the current layout does not have. Each pattern is one older
# path. The records folder is only older on its own: `learning/corrections`
# is the current one, and "corrections" as a plain word is not a path.
_OLD_PATH_PATTERNS = (
    re.compile(r"(?<![\w/.-])context/(?:strategy|plan|metrics|notes)\b"),
    re.compile(r"(?<![\w/.-])work/(?:changes|decisions)\b"),
    re.compile(r"(?<![\w/.-])corrections/"),
    re.compile(r"`corrections`"),
)


def find_old_paths(text):
    """Return (path, line_number) for every older path a person would read."""
    found = []
    for line_number, line in enumerate(str(text or "").splitlines(), start=1):
        for pattern in _OLD_PATH_PATTERNS:
            match = pattern.search(line)
            if match:
                found.append((match.group(0), line_number))
    return found


# --- The markers a document uses to say what a piece of it is ----------------

# A section nobody named "Step something" opts itself in with this line.
STEP_MARKER = "<!-- step -->"
# The words said to the person that ask them for something.
ASK_OPEN = "<!-- ask -->"
ASK_CLOSE = "<!-- end ask -->"
# A complete thing a person reads and approves, shown whole on purpose.
ARTIFACT_OPEN = "<!-- artifact -->"
ARTIFACT_CLOSE = "<!-- end artifact -->"
# One context change, shown to a person.
CHANGE_OPEN = "<!-- change -->"
CHANGE_CLOSE = "<!-- end change -->"

# How many plain prose lines may run before what is shown stops being
# readable in seconds. A table, a short list, or a marked artifact block is
# not prose and does not count.
PROSE_RUN_CAP = 5

# The four lines a context change is shown as, in this order.
CHANGE_LABELS = (
    "What changed:",
    "Why:",
    "What it affects:",
    "When to look again:",
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")
_STEP_TITLE_RE = re.compile(r"^Step\b", re.IGNORECASE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")

# The words that open a clause saying when or why, before the real verb.
_LEADING_CLAUSE_WORDS = (
    "before",
    "after",
    "when",
    "while",
    "if",
    "once",
    "then",
    "to",
    "as",
    "unless",
    "until",
    "where",
    "whenever",
)

# First words that make a sentence an instruction rather than a purpose.
IMPERATIVE_VERBS = (
    "add",
    "always",
    "answer",
    "apply",
    "ask",
    "avoid",
    "bring",
    "build",
    "call",
    "check",
    "choose",
    "confirm",
    "copy",
    "create",
    "do",
    "draft",
    "drop",
    "explain",
    "follow",
    "give",
    "go",
    "hand",
    "keep",
    "leave",
    "let",
    "list",
    "look",
    "make",
    "mention",
    "name",
    "never",
    "note",
    "offer",
    "open",
    "paste",
    "pick",
    "point",
    "print",
    "put",
    "quote",
    "read",
    "record",
    "remember",
    "remove",
    "repeat",
    "reply",
    "review",
    "run",
    "save",
    "say",
    "see",
    "send",
    "set",
    "show",
    "skip",
    "start",
    "state",
    "stop",
    "take",
    "tell",
    "treat",
    "use",
    "wait",
    "write",
)

_SENTENCE_END_RE = re.compile(r"(?<=[.?!])\s+")


class Step(object):
    """One step section of a document, with the lines under its heading."""

    __slots__ = ("title", "heading_line", "lines")

    def __init__(self, title, heading_line, lines):
        self.title = title
        self.heading_line = heading_line
        # lines is a list of (line_number, text) under the heading.
        self.lines = lines


def find_steps(text):
    """Return every step section of the document, in the order they appear."""
    lines = text.splitlines()
    headings = []
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    steps = []
    for position, (index, level, title) in enumerate(headings):
        end = len(lines)
        for later_index, later_level, _title in headings[position + 1:]:
            if later_level <= level:
                end = later_index
                break
        body = [
            (number, lines[number - 1])
            for number in range(index + 2, end + 1)
        ]
        marked = any(
            line.strip() == STEP_MARKER for _number, line in body[:2]
        )
        if not (_STEP_TITLE_RE.match(title) or marked):
            continue
        body = [
            (number, line)
            for number, line in body
            if line.strip() != STEP_MARKER
        ]
        steps.append(Step(title, index + 1, body))
    return steps


def _is_imperative(sentence):
    """True when the sentence tells somebody to do something."""
    words = sentence.strip()
    if not words:
        return False
    if "," in words:
        opener = words.split(",", 1)[0].strip().lower()
        first = re.sub(r"[^a-z]", "", opener.split(" ")[0] if opener else "")
        if first in _LEADING_CLAUSE_WORDS:
            words = words.split(",", 1)[1].strip()
    first_word = words.split(" ", 1)[0] if words else ""
    first_word = re.sub(r"[^a-zA-Z]", "", first_word).lower()
    return first_word in IMPERATIVE_VERBS


def _opening_paragraph(step):
    """The first run of plain prose lines under the heading, as one string."""
    collected = []
    started = False
    for _number, line in step.lines:
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if (
            _HEADING_RE.match(line)
            or _LIST_RE.match(line)
            or _FENCE_RE.match(line)
            or stripped.startswith("|")
            or stripped.startswith(">")
            or stripped.startswith("<!--")
        ):
            break
        started = True
        collected.append(stripped)
    return " ".join(collected)


def find_missing_purpose(text):
    """Return (title, line_number) for every step that opens with an order."""
    found = []
    for step in find_steps(text):
        paragraph = _opening_paragraph(step)
        if not paragraph:
            found.append((step.title, step.heading_line))
            continue
        sentences = [
            piece.strip()
            for piece in _SENTENCE_END_RE.split(paragraph)
            if piece.strip()
        ]
        if not sentences or _is_imperative(sentences[0]):
            found.append((step.title, step.heading_line))
    return found


def _blocks_in(step, opener, closer):
    """Every (start_line, end_line) pair for one kind of marked block."""
    blocks = []
    start = None
    for number, line in step.lines:
        stripped = line.strip()
        if stripped == opener:
            start = number
        elif stripped == closer and start is not None:
            blocks.append((start, number))
            start = None
    if start is not None:
        blocks.append((start, None))
    return blocks


def _last_line_number(step):
    """The number of the last line under the step's heading."""
    return step.lines[-1][0] if step.lines else step.heading_line


def find_extra_requests(text):
    """Return (title, count, line_number) for every step asking for two things."""
    found = []
    for step in find_steps(text):
        blocks = _blocks_in(step, ASK_OPEN, ASK_CLOSE)
        unclosed = [start for start, end in blocks if end is None]
        if unclosed:
            found.append((step.title, len(blocks), unclosed[0]))
            continue
        if len(blocks) > 1:
            found.append((step.title, len(blocks), blocks[1][0]))
    return found


def _marked_ranges(step):
    """Every line number inside an ask, artifact, or change block."""
    inside = set()
    for opener, closer in (
        (ASK_OPEN, ASK_CLOSE),
        (ARTIFACT_OPEN, ARTIFACT_CLOSE),
        (CHANGE_OPEN, CHANGE_CLOSE),
    ):
        for start, end in _blocks_in(step, opener, closer):
            last = end if end is not None else _last_line_number(step)
            for number in range(start, last + 1):
                inside.add(number)
    return inside


def find_long_prose(text):
    """Return (title, run_length, line_number) for prose over the cap."""
    found = []
    for step in find_steps(text):
        inside = _marked_ranges(step)
        run = 0
        run_started = None
        in_fence = False
        for number, line in step.lines:
            stripped = line.strip()
            if _FENCE_RE.match(line):
                in_fence = not in_fence
                run = 0
                run_started = None
                continue
            if in_fence or number in inside:
                run = 0
                run_started = None
                continue
            if not stripped:
                continue
            if (
                _HEADING_RE.match(line)
                or _LIST_RE.match(line)
                or stripped.startswith("|")
                or stripped.startswith(">")
                or stripped.startswith("<!--")
            ):
                run = 0
                run_started = None
                continue
            run += 1
            if run_started is None:
                run_started = number
            if run == PROSE_RUN_CAP + 1:
                found.append((step.title, run, run_started))
    return found


def find_malformed_changes(text):
    """Return (line_number, reason) for every change not shown as four lines."""
    found = []
    lines = text.splitlines()
    start = None
    body = []
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == CHANGE_OPEN:
            start = number
            body = []
            continue
        if stripped == CHANGE_CLOSE:
            if start is None:
                found.append((number, "a change block ends without starting"))
                continue
            found.extend(_change_body_findings(start, body))
            start = None
            body = []
            continue
        if start is not None and stripped:
            body.append(stripped)
    if start is not None:
        found.append((start, "a change block never ends"))
    return found


def _change_body_findings(start, body):
    """What is wrong with the lines inside one change block, if anything."""
    if len(body) != len(CHANGE_LABELS):
        return [
            (
                start,
                "a change is %d lines and the four labeled lines are %d"
                % (len(body), len(CHANGE_LABELS)),
            )
        ]
    findings = []
    for index, label in enumerate(CHANGE_LABELS):
        line = body[index]
        cleaned = line.lstrip("-*+ ").lstrip()
        if not cleaned.lower().startswith(label.lower()):
            findings.append(
                (start + index, "line %d does not open with %r" % (index + 1, label))
            )
    return findings


# --- The sentences a person reads that are held in Python --------------------

# Every sentence a person reads that lives as a Python string rather than in a
# document a person can edit. The completeness test below walks the library and
# fails on any sentence-shaped constant that is in neither this registry nor
# NOT_PERSON_FACING, so the registry can never quietly fall behind the code.
PYTHON_SENTENCES = (
    ("approve_local", "HAS_SHARED_COPY"),
    ("write_hook", "REFUSED"),
    ("write_hook", "ASK_ABOUT_SETTINGS"),
    ("write_hook", "COULD_NOT_CHECK"),
    ("compose_proposal", "MADE_BY_HAND_WORDING"),
    ("compose_proposal", "STILL_THE_NOTE"),
    ("compose_proposal", "NEEDS_A_PART"),
    ("wordsfile", "NOT_OURS"),
    ("wordsfile", "NOT_A_DRAFT"),
    ("wordsfile", "NO_PLACE_FOR_WORDS"),
    ("wordsfile", "WORDS_STILL_THERE"),
    ("approve_local", "NOT_WAITING_HERE"),
    ("approve_local", "MARKER_DISAGREES"),
    ("approve_local", "ALREADY_RECORDED"),
    ("approve_local", "NOTE_UNREADABLE"),
    ("approve_local", "NOT_AN_OWNER"),
    ("approve_local", "NO_OWNER_RECORDED"),
    ("approve_local", "NO_ADDRESS"),
    ("approve_local", "OUTSIDE_THE_FOLDERS"),
    ("approve_local", "ASSISTANT_FOLDER"),
    ("approve_local", "CONFLICT"),
    ("approve_local", "MOVED"),
    ("approve_local", "PREPARED_FROM_OLDER"),
    ("approve_local", "COULD_NOT_KEEP"),
    ("approve_local", "UNSAVED_EDITS"),
    ("approve_local", "UNSAVED_EDITS_NAMED"),
    ("approve_local", "NOT_ON_MAIN"),
    ("approve_local", "COULD_NOT_SAVE"),
    ("approve_local", "UNREADABLE"),
    ("approve_local", "STILL_A_PLACEHOLDER"),
    ("approve_local", "APPLIED"),
    ("approve_local", "KEPT"),
    ("approve_local", "DROPPED"),
    ("approve_local", "ASK"),
    ("approve_local", "WHITESPACE_ONLY"),
    ("approve_local", "NOTHING_DIFFERENT"),
    ("changes", "OFFER_ONE"),
    ("changes", "OFFER_MANY"),
    ("changes", "EVERY_SEAT_FIRST_ONE"),
    ("changes", "EVERY_SEAT_FIRST_MANY"),
    ("changes", "NOT_OFFERED_PUT_OFF"),
    ("changes", "MIGRATED"),
    ("changes", "NOTHING_TO_MOVE"),
    ("changes", "UNREADABLE_ENTRY"),
    ("changes", "SAME_CHANGE_TWICE"),
    ("changes", "TWICE_IN_ONE_FOLDER"),
    ("changes", "THEIR_WORDS"),
    ("changes", "CANNOT_READ_HISTORY"),
    ("changes", "EVERY_SEAT_FIRST"),
    ("changes", "CANNOT_FINISH"),
    ("changes", "GAVE_UP"),
    ("changes", "GAVE_UP_HALF_DONE"),
    ("changes", "GAVE_UP_COULD_NOT"),
    ("changes", "GAVE_UP_NOTE_UNREADABLE"),
    ("changes", "CANNOT_PUT_BACK"),
    ("changes", "COULD_NOT_SAVE_LEFT_HALF_DONE"),
    ("changes", "PUT_OFF"),
    ("confirm", "WRITTEN_TWICE"),
    ("confirm", "CHANGE_NOT_IN_THE_BASE"),
    ("confirm", "CHANGE_IS_NOT_ABOUT_IT"),
    ("confirm", "NOT_ONE_OF_THE_TWO"),
    ("confirm", "NOT_YOUR_DOCUMENT"),
    ("confirm", "UNSAVED_EDITS_HERE"),
    ("confirm", "UNSAVED_EDITS_HERE_NAMED"),
    ("confirm", "NOT_ON_THE_MAIN_LINE"),
    ("stale_check", "MALFORMED_ONE"),
    ("stale_check", "DROPPED_ONE"),
    ("stale_check", "CHANGE_ABOUT_A_MISSING_DOCUMENT"),
    ("compose_proposal", "NO_PARTS_AT_ALL"),
    ("compose_proposal", "OUTSIDE_EVERY_PART"),
    ("stale_check", "FINDING_CHANGE_WAITING"),
    ("stale_check", "PLACEHOLDER_SHAPE"),
    ("stale_check", "PLACEHOLDER_TAIL"),
    ("changes", "GAVE_UP_LEFT_ALONE"),
    ("changes", "WOULD_MOVE"),
    ("changes", "WOULD_NOT"),
    ("changes", "WOULD_FINISH"),
    ("changes", "RECORD_WHAT_CHANGED"),
    ("changes", "RECORD_WHY"),
    ("changes", "NAME_IS_NOT_THE_ID"),
    ("changes", "DESTINATION_TAKEN"),
    ("changes", "UNSAVED_EDITS"),
    ("changes", "UNSAVED_EDITS_NAMED"),
    ("changes", "NOT_ON_MAIN"),
    ("changes", "COULD_NOT_SAVE"),
    ("changes", "NOTE_UNREADABLE"),
    ("changes", "PUT_BACK"),
    ("compose_proposal", "APPROVE_HERE"),
    ("compose_proposal", "CANNOT_TELL"),
    ("compose_proposal", "STILL_A_PLACEHOLDER"),
    ("confirm", "UNKNOWN_ID"),
    ("confirm", "ALREADY_ANSWERED"),
    ("confirm", "WRONG_SESSION"),
    ("confirm", "TOO_OLD"),
    ("confirm", "MALFORMED_QUESTION"),
    ("confirm", "DROPPED_PATH"),
    ("confirm", "INBOX_WAITING"),
    ("confirm", "NO_OWNER_ADDRESS"),
    ("confirm", "NO_DEFAULT_BRANCH"),
    ("confirm", "RECORDED"),
    ("confirm", "RECORDED_LOCALLY"),
    ("confirm", "SENT_FOR_REVIEW"),
    ("confirm", "PENDING_SENTENCE"),
    ("confirm", "UNSAVED_EDITS"),
    ("confirm", "NOT_NOW_SENTENCE"),
    ("confirm", "ASK_WHAT_CHANGED"),
    ("confirm", "PROPOSAL_STAGED"),
    ("confirm", "ENTRY_MISSING"),
    ("confirm", "DRAFTED_ALREADY"),
    ("confirm", "NOT_A_NEW_FILE"),
    ("confirm", "NOTHING_TO_SEND"),
    ("constants", "RESTART_SENTENCE"),
    ("constants", "CONSENT_NARROW_SENTENCE"),
    ("constants", "SURVEY_SENTENCE"),
    ("constants", "SURVEY_ONE_PLACE_SENTENCE"),
    ("constants", "SURVEY_NOTHING_SENTENCE"),
    ("constants", "SHARING_NOTICE"),
    ("constants", "BACKUP_NOT_IN_THIS_RELEASE"),
    ("constants", "INVITE_NOT_IN_THIS_RELEASE"),
    ("constants", "JOIN_LINK_NOT_IN_THIS_RELEASE"),
    ("constants", "SOURCES_READ_REFUSAL"),
    ("formats", "ABOUT_SENTENCE"),
    ("formats", "KEEP_THE_CHANGE_HINT"),
    ("formats", "NAME_WITH_A_SPACE"),
    ("citations", "NOT_COVERED"),
    ("citations", "NO_EVIDENCE"),
    ("citations", "NOTHING_OPEN"),
    ("citations", "NOT_NOTED"),
    ("join_flow", "NOTE_NOT_WRITTEN"),
    ("join_flow", "NEEDS_THE_BASE"),
    ("join_flow", "WHY_FROM_THE_CLOSING"),
    ("join_flow", "NOTED_BY_IS_THE_BASES_RECORD"),
    ("join_flow", "ENTRY_PREVIEW_ASK"),
    ("join_flow", "RECONCILE_ASK"),
    ("join_flow", "RECONCILE_RECORDED"),
    ("join_flow", "RECONCILE_FLAGGED"),
    ("join_flow", "RECONCILE_NOT_PREPARED"),
    ("join_flow", "OTHERS_FLAGGED_ONE"),
    ("join_flow", "OTHERS_FLAGGED_MANY"),
    ("join_flow", "SKIP_RECORDED"),
    ("moment", "ABOUT_TO_USE"),
    ("moment", "FIX_IS_READY"),
    ("moment", "FIX_CAN_BE_PREPARED"),
    ("moment", "THREE_ANSWERS"),
    ("moment", "USED_AS_IS"),
    ("moment", "FIX_FIRST"),
    ("moment", "NOTHING_TO_FIX"),
    ("moment", "CHANGE_IS_GONE"),
    ("moment", "FENCE_NOTE"),
    ("moment", "PAUSE_BEFORE_USING"),
    ("moment", "RELAY_ONLY"),
    ("moment", "NOT_A_CONTEXT_FILE"),
    ("moment", "COULD_NOT_READ"),
    ("moment", "INBOX_WAITING"),
    ("moment", "ALREADY_DECIDED"),
    ("moment", "WRITTEN_TWICE"),
    ("moment", "NOT_YOUR_DOCUMENT"),
    ("moment", "TWO_ANSWERS"),
    ("join_flow", "NOTE_NOT_SAVED_MESSAGE"),
    ("join_flow", "ADDED_NOT_DIRECTLY_INSIDE"),
    ("offer_answer", "SETUP_RECORDS_ITSELF"),
    ("offer_answer", "COULD_NOT_WRITE"),
    ("report", "SEAT_LABEL"),
    ("session_start", "NOT_DEFAULT_BRANCH"),
    ("session_start", "DIRTY_TREE"),
    ("session_start", "UNREACHABLE"),
    ("session_start", "COULD_NOT_UPDATE"),
    ("session_start", "PULL_REFUSED"),
    ("session_start", "TRUST_FAILED"),
    ("session_start", "COPY_FOUND"),
    ("session_start", "MULTIPLE_CHILDREN"),
    ("session_start", "LINK_CONFLICT"),
    ("session_start", "LINK_MISMATCH"),
    ("session_start", "CONTENT_INSIDE_BASE"),
    ("session_start", "AS_OF"),
    ("session_start", "TRUST_AFTER_UPDATE"),
    ("stale_check", "NOT_ON_DEFAULT"),
    ("stale_check", "UNREACHABLE"),
    ("stale_check", "UNSAVED_EDITS"),
    ("stale_check", "UNSAVED_EDITS_NAMED"),
    ("stale_check", "COULD_NOT_UPDATE"),
    ("stale_check", "BROUGHT_UP_TO_DATE"),
    ("stale_check", "UNPROCESSED"),
    ("stale_check", "NOTHING_FLAGGED"),
    ("stale_check", "DRY_RUN_NOTE"),
    ("stale_check", "LEDGER_BEHIND"),
    ("stale_check", "LEDGER_BEHIND_EMPTY"),
    ("stale_check", "LEDGER_BEHIND_DISMISSED"),
    ("stale_check", "REVIEW_BY"),
    ("stale_check", "MALFORMED"),
    ("stale_check", "WRITTEN_TWICE"),
    ("stale_check", "CANNOT_VOUCH"),
    ("stale_check", "DROPPED"),
    ("stale_check", "FINDING_REQUIRED_FILE"),
    ("stale_check", "FINDING_BASELINE_CONFIRMED_ONE_DAY"),
    ("stale_check", "FINDING_BASELINE_CONFIRMED_TWO_DAYS"),
    ("stale_check", "FINDING_BASELINE_NOTHING_TO_CHECK"),
    ("stale_check", "FINDING_BASELINE_ASK_ONE_DAY"),
    ("stale_check", "FINDING_BASELINE_ASK_TWO_DAYS"),
    ("stale_check", "FINDING_BASELINE_UNCONFIRMED"),
    ("stale_check", "FINDING_DOCUMENT_OLDER"),
    ("stale_check", "FINDING_DOCUMENT_BEHIND"),
    ("stale_check", "FINDING_WRITTEN_TWICE"),
    ("stale_check", "FINDING_NOTHING_YET"),
    ("stale_check", "FINDING_NOTHING_YET_NO_DATE"),
    ("stale_check", "AWAITING_LOCAL_APPROVAL"),
    ("stale_check", "REVIEW_OPENING"),
    ("stale_check", "REVIEW_NOTHING"),
    ("stale_check", "REVIEW_ITEM_CHANGE"),
    ("stale_check", "REVIEW_ITEM_THRESHOLD"),
    ("stale_check", "REVIEW_NO_SESSION"),
    ("stale_check", "REVIEW_NOTHING_OWNED"),
    ("stale_check", "REVIEW_ITEM_WAITING_HERE"),
    ("stale_check", "REVIEW_ITEM_WAITING_THERE"),
    ("stale_check", "REVIEW_INBOX_WAITING"),
    ("stale_check", "REVIEW_SPEAKING_AGAIN"),
    ("changes", "DOCUMENT_TAKEN"),
    ("changes", "LAYOUT_RECORD_WHAT_CHANGED"),
    ("changes", "LAYOUT_RECORD_WHY"),
    ("changes", "MAP_WHERE_TODAY"),
    ("write_hook", "SKILLS_REFUSED"),
    ("write_hook", "STACK_REFUSED"),
    # Unit 1.6: the count after an explicit choice, the preview's count and
    # the reason a draft reads a limited amount, the versions of a document,
    # and the narrowing question asked only after a plain yes.
    ("constants", "EXPLICIT_COUNT_SENTENCE"),
    ("constants", "PREVIEW_READS_ALL"),
    ("constants", "PREVIEW_READS_THE_ONE"),
    ("constants", "PREVIEW_READS_SOME"),
    ("constants", "PREVIEW_WHY_LIMITED"),
    ("constants", "PREVIEW_NOTES_CONDENSED"),
    ("constants", "PREVIEW_NOTES_FOLDED_ONE"),
    ("constants", "PREVIEW_NOTES_FOLDED"),
    ("constants", "PREVIEW_NOTES_LEFT_OUT"),
    ("constants", "PREVIEW_NOTES_OVER"),
    ("constants", "DIGESTS_OVER"),
    ("constants", "VERSION_NOT_USED_FINAL"),
    ("constants", "VERSION_NOT_USED_FINAL_OVER_NEWER"),
    ("constants", "VERSION_NOT_USED_NEWER"),
    ("constants", "VERSION_NOT_USED_SAME_DAY"),
    ("constants", "VERSION_NOT_USED_SET_ASIDE"),
    ("constants", "VERSION_NOT_USED_LATER_NUMBER"),
    ("constants", "PREVIEW_READS_ALL_CHOSEN"),
    ("constants", "PREVIEW_READS_THE_ONE_CHOSEN"),
    ("constants", "PREVIEW_READS_SOME_CHOSEN"),
    ("constants", "VERSION_CONFLICT"),
    ("constants", "PREVIEW_NARROW_ASK_ALL"),
    ("constants", "PREVIEW_NARROW_ASK_SOME"),
    # Unit 1.7a: what the base is for, said back once it is held, and the
    # inventory of segments, its question, its read-back, and its refusals.
    ("constants", "SCOPE_SPLITS_SENTENCE"),
    ("constants", "SCOPE_HELD_SENTENCE"),
    ("constants", "SCOPE_WHOLE_SENTENCE"),
    ("segments", "FOUND_SENTENCE"),
    ("segments", "ASK_SENTENCE"),
    ("segments", "WILL_ADOPT"),
    ("segments", "WILL_DRAFT"),
    ("segments", "WILL_LEAVE_OUT"),
    ("segments", "SAVED_SENTENCE"),
    ("segments", "ONE_SEGMENT_SENTENCE"),
    ("segments", "SAME_NAME"),
    ("segments", "NO_USABLE_NAME"),
    ("segments", "RESERVED_NAME"),
    ("segments", "SAME_DOCUMENT"),
    ("segments", "NAME_UNUSABLE"),
    ("segments", "TOO_MANY"),
    ("segments", "NONE_NAMED"),
    # Unit 1.7b: the umbrella's words for a segment left out, a segment file
    # that would collide, the questions a draft leaves open, the review line
    # for each, answering one, and the refusals while one is open.
    ("constants", "UMBRELLA_PENDING_SENTENCE"),
    ("constants", "UMBRELLA_LEFT_OUT_SENTENCE"),
    ("join_flow", "UMBRELLA_CHANGE_WAITING"),
    ("join_flow", "UMBRELLA_CHANGE_WHY"),
    ("segments", "FILE_TAKEN"),
    ("segments", "FOLDER_NOT_ORDINARY"),
    ("join_flow", "DRAFT_HAS_ONE_QUESTION"),
    ("join_flow", "DRAFT_HAS_QUESTIONS"),
    ("confirm", "QUESTION_STILL_OPEN"),
    ("compose_proposal", "STILL_ASKS"),
    ("stale_check", "FINDING_OPEN_QUESTION_ONE"),
    ("stale_check", "FINDING_OPEN_QUESTIONS"),
    ("stale_check", "REVIEW_ITEM_QUESTION"),
    ("stale_check", "REVIEW_ITEM_QUESTION_PREPARED"),
    ("stale_check", "ANSWER_PREPARED"),
    ("stale_check", "ANSWER_ALREADY_PREPARED"),
    ("stale_check", "ANOTHER_ANSWER_WAITING"),
    ("stale_check", "QUESTION_GONE"),
    ("stale_check", "QUESTION_ABOVE_EVERY_PART"),
    ("stale_check", "ANSWER_NEEDED"),
    ("stale_check", "NOT_A_DOCUMENT"),
    # Unit 1.7c: taking a finished page into the base, what the person is
    # shown about it, the one ask, and each refusal with its offer to draft.
    ("adopt", "SHOW_OPENING"),
    ("adopt", "SETTINGS_SET_ASIDE"),
    ("adopt", "NOTHING_TAKEN_OUT"),
    ("adopt", "OPENING_SAID"),
    ("adopt", "WHOLE_FILE"),
    ("adopt", "ONE_QUESTION"),
    ("adopt", "QUESTIONS"),
    ("adopt", "ASK"),
    ("adopt", "ASK_WITH_QUESTIONS"),
    ("adopt", "TAKEN_IN"),
    ("adopt", "DRAFT_INSTEAD"),
    ("adopt", "NOT_MARKDOWN"),
    ("adopt", "UNREADABLE"),
    ("adopt", "MALFORMED_SETTINGS"),
    ("adopt", "FENCE_MARKER"),
    ("adopt", "SCREENED"),
    ("adopt", "DUPLICATE_HEADING"),
    ("adopt", "HEADING_IN_CODE"),
    ("adopt", "UNDERLINED_HEADING"),
    ("adopt", "NO_PARTS"),
    ("adopt", "QUESTION_UNREACHABLE"),
    ("adopt", "QUESTION_SPLIT"),
    ("adopt", "WIDER_THAN_SCOPE"),
    ("adopt", "NOT_TO_ADOPT"),
    ("adopt", "BASE_NOT_READY"),
    ("adopt", "NOT_SHOWN"),
    ("adopt", "CHANGED"),
    ("adopt", "QUESTIONS_NOT_LEFT_OPEN"),
    ("adopt", "UNSAVED_EDITS"),
    ("adopt", "NOT_ON_THE_MAIN_LINE"),
    # Unit 1.7d: finishing an import that stopped, a page left out, the
    # closing's line about pages still to come, and a save that cannot be
    # read or a page something was put in place of.
    ("join_flow", "LEFT_OUT_SAID"),
    ("join_flow", "RESUME_NOTHING"),
    ("join_flow", "RESUME_UNREADABLE"),
    ("join_flow", "RESUME_RUN_HAS_ITS_OWN"),
    ("join_flow", "RESUME_FINISHED_ONE"),
    ("join_flow", "RESUME_FINISHED"),
    ("join_flow", "RESUME_CHANGED"),
    ("join_flow", "RESUME_TAKEN"),
    ("join_flow", "RESUME_TO_SHOW_ONE"),
    ("join_flow", "RESUME_TO_SHOW"),
    ("join_flow", "RESUME_DONE"),
    ("join_flow", "CLOSING_IMPORT_UNFINISHED"),
    ("join_flow", "SAVE_UNCERTAIN"),
    ("join_flow", "PAGE_REPLACED"),
    ("join_flow", "RESUME_EDITED"),
    ("join_flow", "RESUME_CANNOT_READ"),
    ("join_flow", "RESUME_RECHECKED"),
    ("join_flow", "CLEANED_AGAIN_SAID"),
    ("join_flow", "KEPT_ASIDE"),
    ("join_flow", "NO_LOCK"),
    ("join_flow", "LOCKS_NOT_PRIVATE"),
    ("join_flow", "RESUME_STOPPED"),
    ("join_flow", "PAGE_EDITED_SAID"),
    ("join_flow", "ALREADY_SAVED"),
    ("join_flow", "IMPORT_PENDING"),
    ("join_flow", "LOCKED"),
    ("join_flow", "WRITE_FAILED"),
    # Brandon's call 29: a segment settled to be drafted and not drafted
    # before the closing, finished by a later session after a fresh yes.
    ("join_flow", "CLOSING_DRAFTS_UNFINISHED"),
    ("join_flow", "RESUME_DRAFT_SAVED_ONE"),
    ("join_flow", "RESUME_DRAFT_SAVED"),
    ("join_flow", "RESUME_DRAFT_AGAIN"),
    ("join_flow", "RESUME_TO_DRAFT_ONE"),
    ("join_flow", "RESUME_TO_DRAFT"),
    ("join_flow", "RESUME_ALL_SETTLED"),
    ("join_flow", "DRAFT_LIST_OFFER"),
    ("join_flow", "DRAFT_MATERIAL_GONE"),
    ("join_flow", "DRAFT_NOTHING_ON_THE_LIST"),
    ("join_flow", "DRAFT_NOT_TO_FINISH"),
    ("join_flow", "DRAFT_RUN_TAKEN"),
    ("join_flow", "DRAFT_IN_PROGRESS"),
    ("join_flow", "DRAFT_NO_SUCH_NUMBER"),
    ("join_flow", "DRAFT_FOLDER_MISSING"),
    ("join_flow", "DRAFT_LIST_CHANGED"),
    ("join_flow", "DRAFT_NO_LIST"),
    ("join_flow", "DRAFT_NOT_AGREED"),
    ("join_flow", "DRAFT_LEFT_OUT"),
    # The live-check follow-up unit (calls 33, 34 and 49): the one question a
    # hand edit asks, the one yes a fix to wording only asks, and the two
    # refusals a corrected fact can meet.
    ("hand_edit", "WHY_WE_ASK"),
    ("hand_edit", "LONG_ASK"),
    ("hand_edit", "SHORT_ASK"),
    ("approve_local", "WORDING_ASK"),
    ("compose_proposal", "FACT_NOT_REPLACING"),
    ("compose_proposal", "NOT_A_DOCUMENT_HERE"),
    # 0.3.3: recording a context change at any time.
    ("join_flow", "NOT_OWNED_FLAGGED_ONE"),
    ("join_flow", "NOT_OWNED_FLAGGED_MANY"),
    # Unit 1.7e: what Claude Code's own question says, and the refusals.
    ("moment", "NAMES_NOTE"),
    ("approval", "ASK_OPENING"),
    # Plan 1, Unit 4.2a.
    ("approval", "SAYS_CREATE"),
    ("approval", "SAYS_SET_OWNER"),
    ("approval", "SAYS_SET_BUSINESS"),
    ("approval", "SAYS_SET_MAP_OWNER"),
    ("approval", "SAYS_SET_ADMINISTRATORS"),
    ("approval", "SAYS_SET_BUSINESSES"),
    ("approval", "UNATTENDED"),
    # Plan 1, Unit 3.1: the thin runner.
    ("approval", "NOT_MARKED"),
    ("runner", "REFUSED_INVALID_SAYS"),
    ("runner", "REFUSED_NO_STANDARD"),
    ("runner", "REFUSED_UNTRUSTED_SAYS"),
    ("runner", "REFUSED_NO_SKILL"),
    ("runner", "REFUSED_UNREADABLE_SAYS"),
    ("runner", "REFUSED_REQUIRED_SAYS"),
    ("runner", "NOT_CHECKED_SAYS"),
    ("runner", "FLAGGED_ATTENDED_SAYS"),
    ("runner", "FLAGGED_UNATTENDED_SAYS"),
    ("runner", "WRITTEN_TWICE_UNATTENDED_SAYS"),
    ("runner", "GAP_SAYS"),
    ("runner", "UNSAVED_SAYS"),
    ("runner", "INSTRUCTIONS_SAYS"),
    ("runner", "DOCUMENTS_SAYS"),
    ("runner", "FINISH_SCREENED"),
    ("runner", "FINISH_FIGURE"),
    ("runner", "FINISH_ENGINE"),
    ("runner", "FINISH_ENGINE_UNNAMED"),
    ("runner", "FINISH_NO_RUN"),
    ("runner", "FINISH_DONE"),
    ("runner", "EXPECTED_MISSING"),
    ("runner", "EXPECTED_PRESENT"),
    ("runner", "EXAMPLE_INCOMPLETE"),
    ("runner", "EXAMPLE_NO_WRONG"),
    ("runner", "EXAMPLE_EXPECTS_NOTHING"),
    ("runner", "EXAMPLE_APPROVED_FAILS"),
    ("runner", "EXAMPLE_WRONG_PASSES"),
    ("runner", "SKILL_NO_EXAMPLES"),
    ("runner", "SKILL_NAMES_A_COMMAND"),
    # Plan 1, Unit 4.2b: the skills folder.
    ("runner", "OFFER_SHOWING"),
    ("approval", "SAYS_INSTALL_SKILL"),
    ("approval", "SAYS_ACCEPT_SKILL"),
    ("skill_install", "NOT_A_SKILL"),
    ("skill_install", "SHAPE_REFUSED"),
    ("skill_install", "SCREENED"),
    ("skill_install", "CONTRACT_FAILS"),
    ("skill_install", "NO_ADDRESS"),
    ("skill_install", "NOT_WAITING"),
    ("skill_install", "MOVED"),
    ("skill_install", "NOT_ALLOWED"),
    ("skill_install", "WAITING_FOR_THE_BASE_OWNER"),
    ("skill_install", "UNSAVED"),
    ("skill_install", "NOT_ON_MAIN"),
    ("skill_install", "COULD_NOT_SAVE"),
    ("skill_install", "INSTALLED"),
    ("skill_install", "CHANGED"),
    ("skill_install", "ACCEPTED"),
    ("skill_install", "ALREADY_TRUSTED"),
    ("skill_install", "NO_APPROVAL"),
    ("skill_install", "SHOWING_WHO"),
    ("skill_install", "SHOWING_CHANGED"),
    ("skill_install", "SHOWING_FIRST"),
    ("approval", "ASK_CLOSING"),
    ("approval", "SAYS_APPROVE_CHANGE"),
    ("approval", "SAYS_DROP_CHANGE"),
    ("approval", "SAYS_BACKUP"),
    ("approval", "SAYS_STILL_RIGHT"),
    ("approval", "SAYS_NO_LONGER_RIGHT"),
    ("approval", "SAYS_PUT_OFF"),
    ("approval", "SAYS_FIX_FIRST"),
    ("approval", "SAYS_ALREADY_SAYS"),
    ("approval", "SAYS_NOT_CAUGHT_UP"),
    ("approval", "SAYS_LEFT_FLAGGED"),
    ("approval", "SAYS_SAVE_DRAFT"),
    ("approval", "SAYS_ADOPT_PAGE"),
    ("approval", "SAYS_LEAVE_PAGE_OUT"),
    ("approval", "SAYS_LEAVE_SEGMENT_OUT"),
    ("approval", "SAYS_RECORD_CHANGE"),
    ("approval", "SAYS_MOVE"),
    ("approval", "SAYS_MOVE_LATER"),
    ("approval", "SAYS_QUIET_MONTH"),
    ("approval", "SAYS_QUIET_UNTIL_ASKED"),
    ("approval", "NOT_ASKED"),
    ("approval", "ONE_LINE"),
    ("approval", "TWO_THINGS"),
    ("approval", "UNREADABLE"),
    ("approval", "SAYS_SKIP"),
    ("approval", "SAYS_SKIP_CLOSING"),
    ("approval", "SAYS_CLOSE_NOTE"),
    ("approval", "SAYS_WEEKLY_LINE_OFF"),
    ("approval", "SAYS_REMINDER_LATER"),
    ("approval", "NOT_OURS"),
    ("approval", "CANNOT_ASK"),
    ("approval", "COULD_NOT_PREPARE"),
    ("record_change", "EXPLAIN"),
    ("record_change", "ASK"),
    ("record_change", "ASK_SHORT"),
    ("record_change", "DOCUMENTS_INTRO"),
    ("record_change", "NO_DOCUMENTS"),
    ("record_change", "PREVIEW_ASK"),
    ("record_change", "RECORDED"),
    ("record_change", "LEFT"),
    ("record_change", "LEFT_FLAGGED"),
    ("record_change", "SHARED_COPY"),
    ("record_change", "NEEDS_WORDS"),
    ("record_change", "TOO_LONG"),
    ("record_change", "NOT_ON_THE_LIST"),
    ("record_change", "NEEDS_A_DOCUMENT"),
    ("record_change", "BAD_DAY"),
    ("record_change", "SCREENED_NEXT"),
    ("record_change", "NOTHING_WAITING"),
    ("record_change", "NOT_WHAT_WAS_SHOWN"),
    ("record_change", "MOVED_ON"),
    ("record_change", "NOT_ON_MAIN"),
    ("record_change", "UNSAVED"),
    ("record_change", "UNSAVED_NAMED"),
    ("record_change", "COULD_NOT_SAVE"),
    ("record_change", "NO_ADDRESS"),
    ("record_change", "NO_ROOM"),
    ("record_change", "ANSWER_UNKNOWN"),
    ("record_change", "NOT_ASKED"),
    ("record_change", "NO_LIST_YET"),
    ("record_change", "LIST_CHANGED"),
    ("record_change", "TOO_MANY_DOCUMENTS"),
    ("record_change", "CHANGE_CHANGED"),
    ("record_change", "RUNS_A_PROGRAM"),
    ("record_change", "NOT_ALL_TAKEN_BACK"),
    ("record_change", "BUSY"),
    ("record_change", "SAVING_ELSEWHERE"),
    # Plan 1, Unit 4.2a: creating a document and the five settings operations.
    ("operations", "NOT_A_DOCUMENT"),
    ("operations", "ALREADY_THERE"),
    ("operations", "SCREENED"),
    ("operations", "NO_ADDRESS"),
    ("operations", "BAD_VALUE"),
    ("operations", "NOT_AN_OPERATION"),
    ("operations", "NOT_WAITING"),
    ("operations", "MOVED"),
    ("operations", "NOT_ALLOWED"),
    ("operations", "UNSAVED"),
    ("operations", "NOT_ON_MAIN"),
    ("operations", "COULD_NOT_SAVE"),
    ("operations", "DONE_CREATED"),
    ("operations", "DONE_SETTING"),
    ("write_hook", "UNATTENDED_REFUSED"),
    ("approve_local", "AUTHORITY_UNREADABLE"),
    ("approve_local", "OWNER_LINE_BY_HAND"),
    ("approve_local", "SOURCE_MAP_SECRET"),
    # Plan 1, Unit 2.1: the inventory.
    ("inventory", "PURPOSE"),
    ("inventory", "NOT_STATED"),
    ("inventory", "NOT_STATED_ONE"),
    ("inventory", "UNLISTED"),
    ("inventory", "UNLISTED_ONE"),
    ("inventory", "DISAGREE"),
    ("inventory", "DISAGREE_ONE"),
    ("inventory", "SETTING_LATER"),
    ("inventory", "BUSINESSES_UNREADABLE"),
    ("inventory", "DATES_UNREADABLE"),
    ("inventory", "SCOPE_FINDING"),
    ("inventory", "SCOPE_OFFER"),
    ("inventory", "DRAFT_OFFER"),
    ("inventory", "DRAFTING_LATER"),
    ("inventory", "DRAFTING_LATER_REST"),
    ("inventory", "NOTHING_MISSING"),
    # Plan 1, Unit 2.5a: the source map's rows.
    ("truth_map", "ROW_INCOMPLETE"),
    ("truth_map", "ROW_MALFORMED"),
    ("truth_map", "OTHER_COLUMNS"),
    ("truth_map", "BUSINESS_NOT_IN_MAP"),
    ("truth_map", "BUSINESSES_UNREADABLE"),
    ("truth_map", "SCREENED"),
    ("truth_map", "UNREADABLE"),
    # Track 4, step 1.
    ("truth_map", "NOT_NAMED"),
    ("truth_map", "NO_ROWS"),
    ("record_change", "SUGGESTED_INTRO"),
    ("drafting", "NOT_COVERED"),
    # Track 4, Unit T4.8: drift grade.
    ("starter", "NOT_A_STARTER"),
    ("starter", "STANDARD_KEPT"),
    ("starter", "OFFER"),
)

# Constants that read like a sentence but that no person ever reads. Each one
# says why, so the completeness test is never quieted by an empty claim.
NOT_PERSON_FACING = (
    (
        "confirm",
        "FILE_HEADER",
        "The comment at the top of a machine-read records file, never shown.",
    ),
    (
        "constants",
        "SOURCE_FENCE_SENTENCE",
        "An instruction to the assistant inside a rendered request, not a "
        "sentence said to a person.",
    ),
    (
        "formats",
        "LEGACY_KEEP_HINT",
        "The words this sentence had before Unit 1.4. Nothing writes them any "
        "more. It is here only so that a proposal raised before the rename, "
        "which carries them, can still be read, so it is a thing searched for "
        "rather than a thing said.",
    ),
)


class Exemption(object):
    """One text that fails a check today, and the unit that will fix it."""

    __slots__ = ("path", "check", "step", "reason", "removed_by")

    def __init__(self, path, check, step, reason, removed_by):
        self.path = path
        self.check = check
        # The title of the one step this excuses, or "*" for the whole file.
        self.step = step
        self.reason = reason
        self.removed_by = removed_by

    def covers(self, path, step_title):
        """True when this entry excuses that step of that file."""
        normalized = str(path).replace(os.sep, "/")
        if not normalized.endswith(self.path):
            return False
        return self.step == "*" or self.step == step_title


# The names of the four checks, used by the exemption list and by the tests.
CHECK_NAMES = ("purpose", "one-request", "prose", "four-lines")

# Unit 1.1b changed no sentence anybody reads. Every text that failed one of
# the four checks was listed here with the reason it failed and the unit that
# owned the rewrite, and each of those units cleared its own entries as it
# rewrote its own step. Unit 1.8 rewrote the last five, the first four steps of
# setting up a base, which no behavior unit owned, so the list is empty. A
# later text that cannot meet a check goes back on it only with a reason that
# will still be true once that text is finished, and never with "later".

EXEMPTIONS = ()


def exemption_problems(entry):
    """What is wrong with one exemption entry, as a list of plain reasons.

    An entry has to say two things: why the text fails today, and which unit
    removes it. An entry that says neither is the thing this check exists to
    stop, because an exemption with no owner is a rule quietly deleted.
    """
    problems = []
    if not str(entry.path).strip():
        problems.append("an exemption names no file")
    if entry.check not in CHECK_NAMES:
        problems.append("%r is not one of the four checks" % (entry.check,))
    if not str(entry.step).strip():
        problems.append("an exemption names no step")
    reason = str(entry.reason or "").strip()
    if len(reason.split()) < 8:
        problems.append("the reason does not say why the text fails today")
    if "later" in reason.lower().split():
        problems.append('"later" is not a reason')
    owner = str(entry.removed_by or "").strip()
    if not re.match(r"^1\.\d[a-d]?$", owner):
        problems.append("the entry does not name the unit that removes it")
    return problems


def exemptions_for(path):
    """Every exemption that covers the file at this path."""
    normalized = str(path).replace(os.sep, "/")
    return tuple(
        entry for entry in EXEMPTIONS if normalized.endswith(entry.path)
    )


def is_exempt(path, check, step_title):
    """True when the exemption list excuses that check for that step."""
    return any(
        entry.check == check and entry.covers(path, step_title)
        for entry in EXEMPTIONS
    )


# --- Reading the library's own constants -------------------------------------

def _is_sentence_shaped(value):
    """True when a string is long enough and shaped enough to be a sentence."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if len(text) < 25:
        return False
    if len([word for word in text.split() if word]) < 5:
        return False
    return text.endswith((".", "?", "!"))


def library_sentence_constants(lib_dir):
    """Every module-level constant in the library that reads like a sentence.

    Returns a list of (module_name, constant_name, line_number). The library is
    read rather than imported, so the walk cannot be changed by anything a
    module does when it loads.
    """
    found = []
    package = os.path.join(lib_dir, "gtmbase")
    for name in sorted(os.listdir(package)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(package, name), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        module = name[: -len(".py")]
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = [
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                ]
                value_node = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(
                node.target, ast.Name
            ):
                targets = [node.target.id]
                value_node = node.value
            else:
                continue
            if value_node is None:
                continue
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, SyntaxError):
                continue
            if not _is_sentence_shaped(value):
                continue
            for target in targets:
                found.append((module, target, node.lineno))
    return found


# --- No sentence is filled from a file name (Unit 1.8) ------------------------

# A file name is whatever somebody typed, and a sentence a person reads is
# handed to the assistant to say word for word. A name short and tidy enough
# to pass any shape check can still read as an instruction, which the review
# of 0.3.2 and its confirmation both found. So no registered sentence may be
# filled from a file name: a document the product knows is called by its fixed
# name, and a segment or any other file is counted. This check reads the code
# that fills each sentence, which is the only place the rule can be held.

# The words the code uses for a value that is, or came out of, a file name or
# a folder name. A context change's identifier is not one of them: the ones a
# sentence says are read from inside the change and checked against the one
# shape GTM Base gives them, which can carry nothing else, and in the few
# refusals that still say one it is the only thing that tells two copies of a
# change apart.
FILE_NAME_WORDS = frozenset(
    (
        "path",
        "paths",
        "relative",
        "relative_context",
        "destination",
        "moved",
        "file",
        "files",
        "filename",
        "file_name",
        "stem",
        "slug",
        "candidate",
        "target",
        "affects",
        "root",
        "roots",
        "old_root",
        "folder",
    )
)

# `source` is left out on purpose: in a context change it is the person's own
# words for where the change came from, which are theirs to read back.


def _names_a_file(identifier):
    """True when a name in the code says it holds a file name or a path.

    A name counts when it is one of the words above, or is made of words
    joined by underscores and ends in one of them, so `entry_file` and
    `target_paths` count and `file_flags` does not. A lookup named for its
    key, such as `by_slug`, does not count.
    """
    if str(identifier).startswith("by_"):
        # A lookup keyed by a file name, such as `by_slug`, holds something
        # else as its values, and what is looked up is what is said.
        return False
    last = str(identifier).rsplit("_", 1)[-1]
    # A plural is the same word, so `candidates` and `targets` count.
    return last in FILE_NAME_WORDS or (
        last.endswith("s") and last[:-1] in FILE_NAME_WORDS
    )


# Calls trusted only when made through the one module that defines them,
# because another module has a function of the same name that does hand a
# path back (`location.describe` says where a base would go).
SAFE_QUALIFIED_CALLS = frozenset((("trust_surface", "describe"),))

# Calls that read a name out of a path.
FILE_NAME_READERS = frozenset(
    ("basename", "splitext", "relpath", "abspath", "realpath", "dirname")
)

# The functions that turn a path into what a person calls it without reading
# the file name, each tested for it by name, and the few that turn one into
# something that is not a name at all: a date, a count, the reasons a check
# gave, the addresses of a document's owners, or what a file holds rather than
# what it is called. What they are given is not read. Any other function given
# a path is taken to hand the path back.
SAFE_CALLS = frozenset(
    (
        "words_from",
        "read_words",
        "isoformat",
        "_as_of",
        "_happened_on",
        "owners_of",
        # The addresses in a document's authority set (Plan 1, Unit 4.2a):
        # its owners, the base owner and the administrators, never a name.
        "who_may_approve",
        "document_name",
        "documents_named",
        "plain_name",
        "where",
        "where_sentence",
        "_named",
        "_all_named",
        "_named_moves",
        "_what_moves",
        "safe_name",
        "change_name",
        "_the_change_called",
        "how_many",
        "counted",
        # The namer a step of recording a change is handed, which is only
        # ever `names.document_name`, `record_change.safe_name`, or what
        # `record_change.names_for` returns; test_segment_names checks every
        # namer the plugin hands over is one of those (Brandon's call 59).
        "name_of",
    )
)

# The few sentences that name a folder on this computer on purpose, each with
# the reason that will still be true once its text is finished. A folder the
# person has to go to, or has to recognise as their own before anything is
# read, can only be told to them by its location.
FILE_NAME_FILL_EXEMPTIONS = (
    (
        "sources",
        "SURVEY_SENTENCE",
        "Names the folders of the person's own material, which they must "
        "recognise before a single file in them is read.",
    ),
    (
        "sources",
        "SURVEY_ONE_PLACE_SENTENCE",
        "Names the one folder of the person's own material, which they must "
        "recognise before a single file in it is read.",
    ),
    (
        "sources",
        "SURVEY_NOTHING_SENTENCE",
        "Names the folder the person just named themselves, to say nothing "
        "in it looked like marketing material.",
    ),
    (
        "session_start",
        "COPY_FOUND",
        "Names where on this computer the base already joined is, which is "
        "the one fact the person needs to tell the two copies apart.",
    ),
    (
        "session_start",
        "LINK_CONFLICT",
        "Names where on this computer the two bases are, because the person "
        "has to choose which one lets go and only the locations tell them.",
    ),
    (
        "location",
        "Your base will go in a new folder at",
        "Says where on this computer the base would be made, which the person "
        "is asked to agree to before anything is created there.",
    ),
)


def _callee(node):
    """The name a call is made by, whether it is written plainly or dotted."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _bindings(target, value):
    """Every (name, value) an assignment binds.

    A tuple of names given a tuple written out beside it is taken apart
    element by element. A tuple of names unpacked from anything else binds
    nothing here: which part went where cannot be read, and a name that says
    it holds a path is caught by its own name wherever it is used.
    """
    if isinstance(target, ast.Name):
        return [(target.id, value)]
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(
        value, (ast.Tuple, ast.List)
    ):
        if len(target.elts) != len(value.elts):
            return []
        found = []
        for one, other in zip(target.elts, value.elts):
            found.extend(_bindings(one, other))
        return found
    return []


# Methods that put a value into a list or a set, which is an assignment in
# all but name.
_ADDERS = ("append", "extend", "add", "insert")


def _assignments(function):
    """Every assignment in one function, as name to the values given.

    A tuple written out on both sides is taken apart, and a value added to
    a list or a set with `append`, `extend`, `add` or `insert` counts as
    given to it.
    """
    found = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for name, value in _bindings(target, node.value):
                    found.setdefault(name, []).append(value)
        elif isinstance(node, (ast.For, ast.comprehension)):
            for name, value in _bindings(node.target, node.iter):
                found.setdefault(name, []).append(value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if node.value is not None:
                for name, value in _bindings(node.target, node.value):
                    found.setdefault(name, []).append(value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _ADDERS
            and isinstance(node.func.value, ast.Name)
        ):
            found.setdefault(node.func.value.id, []).extend(node.args)
    return found


def _reads_a_file_name(node, assigned, seen=()):
    """True when this expression carries a file name into a sentence."""
    if isinstance(node, ast.Call):
        name = _callee(node)
        if name in SAFE_CALLS:
            return False
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and (func.value.id, func.attr) in SAFE_QUALIFIED_CALLS
        ):
            return False
        if name in FILE_NAME_READERS:
            return True
        # A method is read through what it is called on, so `path.lower()`
        # still carries the path, and so do its arguments.
        parts = list(node.args) + [keyword.value for keyword in node.keywords]
        if isinstance(node.func, ast.Attribute):
            parts.append(node.func.value)
        return any(_reads_a_file_name(part, assigned, seen) for part in parts)
    if isinstance(node, ast.Subscript):
        # What is looked up is what is said, never the key it is found by.
        return _reads_a_file_name(node.value, assigned, seen)
    if isinstance(node, ast.Compare):
        # A comparison is true or false, never a name.
        return False
    if isinstance(node, ast.IfExp):
        # Only what either side gives is said, never what chose between them.
        return _reads_a_file_name(
            node.body, assigned, seen
        ) or _reads_a_file_name(node.orelse, assigned, seen)
    if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
        # What a comprehension carries into the sentence is what it yields.
        # Its loop variable is read through the assignments, like any other.
        return _reads_a_file_name(node.elt, assigned, seen)
    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            return False
        if _names_a_file(node.id):
            return True
        if node.id in assigned and node.id not in seen:
            return any(
                _reads_a_file_name(value, assigned, seen + (node.id,))
                for value in assigned[node.id]
            )
        return False
    if isinstance(node, ast.Attribute):
        # A field is judged by its own name: `finding.path` is a path, and a
        # segment's `name` is the name the person gave, from the inventory.
        return _names_a_file(node.attr)
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.Lambda, ast.FunctionDef)):
            continue
        if _reads_a_file_name(child, assigned, seen):
            return True
    return False


def _added_pieces(node):
    """The pieces of a chain of `+`, in order."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _added_pieces(node.left) + _added_pieces(node.right)
    return [node]


def _text_with_holes(pieces):
    """The words a sentence built from pieces reads as, a hole for each value.

    Returns None when a piece is neither a string nor a value that fills one.
    """
    words = []
    for piece in pieces:
        if isinstance(piece, ast.Constant):
            if not isinstance(piece.value, str):
                return None
            words.append(piece.value)
        elif isinstance(piece, ast.FormattedValue):
            words.append("%s")
        else:
            words.append("%s")
    return "".join(words)


def _templates(template, assigned):
    """What a template may be: itself, both sides of an `if`, or what a local
    name was given."""
    if isinstance(template, ast.IfExp):
        return _templates(template.body, assigned) + _templates(
            template.orelse, assigned
        )
    found = [template]
    if isinstance(template, ast.Name):
        for value in assigned.get(template.id, []):
            if isinstance(value, (ast.Name, ast.Attribute, ast.Constant)):
                found.append(value)
    return found


def _fills(node, assigned=None):
    """Every (sentence, values, inline) a node fills: the sentence, the values
    it is filled with, and whether it is written right there rather than
    kept as a constant."""
    assigned = assigned or {}
    if isinstance(node, ast.JoinedStr):
        text = _text_with_holes(node.values)
        if text and _is_sentence_shaped(text):
            values = [
                piece.value
                for piece in node.values
                if isinstance(piece, ast.FormattedValue)
            ]
            return [(text, values, True)]
        return []
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
        and not isinstance(getattr(node, "_parent", None), ast.BinOp)
    ):
        pieces = _added_pieces(node)
        strings = [
            piece
            for piece in pieces
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str)
        ]
        text = _text_with_holes(pieces) if strings else None
        if text and _is_sentence_shaped(text):
            values = [piece for piece in pieces if piece not in strings]
            return [(text, values, True)]
        return []
    found = []
    for template, values in _one_fill(node):
        for each in _templates(template, assigned):
            key, inline = _template_key(each)
            if key is not None:
                found.append((key, values, inline))
    return found


def _template_key(template):
    if isinstance(template, ast.Name):
        return template.id, False
    if isinstance(template, ast.Attribute):
        return template.attr, False
    if (
        isinstance(template, ast.Constant)
        and isinstance(template.value, str)
        and _is_sentence_shaped(template.value)
    ):
        # A sentence written where it is filled, rather than kept as a named
        # constant, is read by a person just the same.
        return template.value, True
    return None, False


def _one_fill(node):
    """The template a `%` or a `.format` fills, and the values it is given."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        template = node.left
        right = node.right
        if isinstance(right, ast.Tuple):
            values = list(right.elts)
        elif isinstance(right, ast.Dict):
            values = list(right.values)
        else:
            values = [right]
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        template = node.func.value
        values = list(node.args) + [keyword.value for keyword in node.keywords]
    else:
        return []
    return [(template, values)]


def _is_excused(module, template, exemptions):
    """True when the exemptions name this fill with a reason."""
    for owner, opening, _reason in exemptions:
        if owner != module:
            continue
        if template == opening or (
            len(opening.split()) > 3 and str(template).startswith(opening)
        ):
            return True
    return False


def find_file_name_fills(source, registered, module="", exemptions=None):
    """Return (line, sentence) for each sentence a person reads filled from a file name.

    `registered` is the set of constant names that are sentences a person
    reads, and a sentence-shaped string filled where it is written counts as
    well. A fill is excused only when FILE_NAME_FILL_EXEMPTIONS names that
    module and that sentence, by its constant or its opening words, with its
    reason. `exemptions` replaces that list, which is how a test proves each
    exemption on it is still needed.

    The sentence may be filled with `%`, with `.format`, as an f-string, or
    by joining strings with `+`, and it may be a constant, a sentence written
    in place, either side of an `if`, or a local name given one of those.
    """
    if exemptions is None:
        exemptions = FILE_NAME_FILL_EXEMPTIONS
    tree = ast.parse(source)
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._parent = parent
    scopes = [tree] + [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    found = {}
    for scope in scopes:
        assigned = _assignments(scope) if scope is not tree else {}
        for node in ast.walk(scope):
            for constant, values, inline in _fills(node, assigned):
                if not inline and constant not in registered:
                    continue
                if _is_excused(module, constant, exemptions):
                    continue
                if any(_reads_a_file_name(value, assigned) for value in values):
                    found.setdefault(
                        node.lineno, constant if not inline else constant[:60]
                    )
    return sorted(found.items())


def plugin_python_files():
    """Every Python file of the plugin: the library and each skill's scripts."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plugin = os.path.join(here, "plugins", "gtm-base")
    found = []
    for folder in ("lib", "skills", "hooks"):
        for base, dirs, files in os.walk(os.path.join(plugin, folder)):
            dirs[:] = [name for name in dirs if name != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".py"):
                    found.append(os.path.join(base, name))
    return sorted(found)


# --- What a test calls -------------------------------------------------------

def plugin_description_files():
    """The two files holding the first sentence anybody reads about this.

    They are JSON rather than markdown, so nothing else in this lint would
    ever have looked at them, and they are the one sentence somebody reads
    before they have installed anything at all.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [
        os.path.join(here, "plugins", "gtm-base", ".claude-plugin", "plugin.json"),
        os.path.join(here, ".claude-plugin", "marketplace.json"),
    ]


def assert_plain(testcase, path):
    """Fail the test case when the file at path breaks either rule."""
    with open(str(path), encoding="utf-8") as handle:
        text = handle.read()
    banned = find_banned(text)
    testcase.assertEqual(
        [], banned, "banned words in %s: %s" % (path, banned)
    )
    dashes = find_dashes(text)
    testcase.assertEqual(
        [], dashes, "em or en dashes in %s: %s" % (path, dashes)
    )
    words = find_banned_person_facing(text)
    testcase.assertEqual(
        [],
        words,
        "words a person must never read in %s: %s" % (path, words),
    )
    short = find_short_form_first(text)
    testcase.assertIsNone(
        short,
        '"change" is read before "context change" in %s, on line %s'
        % (path, short),
    )


def assert_standard(testcase, path):
    """Fail the test case when a step in the file breaks the four checks."""
    with open(str(path), encoding="utf-8") as handle:
        text = handle.read()
    missing = [
        finding
        for finding in find_missing_purpose(text)
        if not is_exempt(path, "purpose", finding[0])
    ]
    testcase.assertEqual(
        [], missing, "steps that open with an order in %s: %s" % (path, missing)
    )
    extra = [
        finding
        for finding in find_extra_requests(text)
        if not is_exempt(path, "one-request", finding[0])
    ]
    testcase.assertEqual(
        [], extra, "steps asking for more than one thing in %s: %s" % (path, extra)
    )
    long_prose = [
        finding
        for finding in find_long_prose(text)
        if not is_exempt(path, "prose", finding[0])
    ]
    testcase.assertEqual(
        [], long_prose, "prose over the cap in %s: %s" % (path, long_prose)
    )
    changes = (
        []
        if is_exempt(path, "four-lines", "*")
        else find_malformed_changes(text)
    )
    testcase.assertEqual(
        [], changes, "changes not shown as four lines in %s: %s" % (path, changes)
    )
