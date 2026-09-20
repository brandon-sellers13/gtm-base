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
    ("constants", "DRAFT_TOO_MUCH_MATERIAL"),
    ("constants", "SHARING_NOTICE"),
    ("constants", "BACKUP_NOT_IN_THIS_RELEASE"),
    ("constants", "INVITE_NOT_IN_THIS_RELEASE"),
    ("constants", "JOIN_LINK_NOT_IN_THIS_RELEASE"),
    ("constants", "SOURCES_READ_REFUSAL"),
    ("formats", "ABOUT_SENTENCE"),
    ("formats", "KEEP_THE_DECISION_HINT"),
    ("join_flow", "NOTE_NOT_WRITTEN"),
    ("join_flow", "NOTE_NOT_SAVED_MESSAGE"),
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
    ("stale_check", "DROPPED"),
    ("stale_check", "FINDING_REQUIRED_FILE"),
    ("stale_check", "FINDING_REQUIRED_ENTRY"),
    ("stale_check", "FINDING_DOCUMENT_OLDER"),
    ("stale_check", "FINDING_NOTHING_YET"),
    ("stale_check", "FINDING_NOTHING_YET_NO_DATE"),
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

# Unit 1.1b changes no sentence anybody reads. Every text that fails one of the
# four checks today is listed here with the reason it fails and the unit that
# owns the rewrite. Each of those units clears its own entries as it rewrites
# its own step, and Unit 1.8 empties whatever is left.
_JOIN_SKILL = "plugins/gtm-base/skills/join/SKILL.md"

EXEMPTIONS = (
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 1. Say what setting up a base does",
        "The step opens by telling the assistant what to say, before it says "
        "what the step is for. No behavior unit of Phase 1 owns this step.",
        "1.8",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 2. The sharing notice",
        "The step opens with an order to say the notice, before it says what "
        "the notice is for. No behavior unit of Phase 1 owns this step.",
        "1.8",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 3. The one opening question",
        "The step opens with an order to ask the question, before it says "
        "what the question is for. No behavior unit of Phase 1 owns this step.",
        "1.8",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 4. The company name, and where the base will go",
        "The step opens with an order to ask for the company name. No "
        "behavior unit of Phase 1 owns this step.",
        "1.8",
    ),
    Exemption(
        _JOIN_SKILL,
        "prose",
        "Step 4. The company name, and where the base will go",
        "The step runs six plain prose lines before anything a person can "
        "read at a glance. No behavior unit of Phase 1 owns this step.",
        "1.8",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 5. What will be read, and the yes that fixes the list",
        "The consent step opens with an order to run the survey. Unit 1.6 "
        "rewrites this step under ruling 1 of the acceptance matrix.",
        "1.6",
    ),
    Exemption(
        _JOIN_SKILL,
        "prose",
        "Step 5. What will be read, and the yes that fixes the list",
        "The consent paragraph runs to seven sentences before the question "
        "arrives. Ruling 1 of the acceptance matrix cuts it to three short "
        "lines and the question, in Unit 1.6.",
        "1.6",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 6. The two drafts, one at a time",
        "The drafting step opens with an order rather than with what the "
        "step is for. Unit 1.6 rewrites this step under ruling 2.",
        "1.6",
    ),
    Exemption(
        _JOIN_SKILL,
        "prose",
        "Step 6. The two drafts, one at a time",
        "The step carries several prose runs over the cap, including the "
        "per-draft narrowing ask ruling 2 removes. Unit 1.6 owns it.",
        "1.6",
    ),
    Exemption(
        _JOIN_SKILL,
        "purpose",
        "Step 7. The closing",
        "The closing step opens with an order. Unit 1.5 rewrites this step "
        "when it adds the closing question and the reconciliation.",
        "1.5",
    ),
    Exemption(
        _JOIN_SKILL,
        "prose",
        "Step 7. The closing",
        "The closing runs six plain prose lines. Unit 1.5 rewrites the "
        "closing under ruling 4 of the acceptance matrix.",
        "1.5",
    ),
)


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


# --- What a test calls -------------------------------------------------------

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
