"""The thin runner: one shape for every skill that reads a company base.

Unit 3.1 of Plan 1, from the signed company-skills requirements (CS3, CS10 to
CS12, CS21, CS26, CS30, CS31). A skill kept in a base declares, in its
settings block, the documents it reads (`reads_required`, `reads_optional`)
and its standard (`standard`, always required). The runner reads; it never
decides and never calls a tool. Three things live here.

`start` reads every file of the skill once, hashes what it read, compares the
whole with the manifests this seat trusts, reads each declared document as the
base last saved it, runs the moment-of-use check against that same saved
version, and hands back one named outcome. It works through seven steps in a
fixed order and the first that fails decides, so two problems at once always
give the more serious answer:

1. Every declared path is a document the check can run on. If not, refused
   (invalid declaration), whether it was declared required or optional.
2. The skill as it stands matches a manifest this seat trusts. If not,
   refused (untrusted).
3. The base can be read for the check. If not, refused (unreadable).
4. Every required document is saved and readable. If not, refused (required).
5. The seat is silenced. If so, not checked.
6. A declared document is flagged. If so, flagged, attended or unattended.
7. An optional document is missing. If so, ready with gaps. Otherwise ready.

`finish` takes the work product and the files it was built from, screens it
for contact details and keys, lints every currency figure and percentage
against those files, checks each marked engine block line for line against the
file it names, and writes the run's "completed" line. The figure lint catches
a made-up number and proves nothing about whether a figure belongs to the
right metric, platform or period.

`check_examples` is the contract check (CS26): each example's approved output
must meet its expectations and every deliberately wrong output must fail, with
no model called. It also holds the rule from the Track 4 plan that a skill's
own text never names the runner's commands, because in chat the connector
serves the skill and those commands do not exist there.

Both run lines live in this seat's own records, never in the base. A
"started" line with no "completed" line is an incomplete run, stopping point
unknown until it is compared with the skill's own records.

Everything read out of a document is data, handed on inside a fence. Only the
skill's own approved files are handed on as instructions.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

from . import (
    authority,
    base_reader,
    constants,
    docpaths,
    formats,
    ids,
    moment,
    names,
    paths,
    redaction_patterns,
    review,
    state,
)
from .errors import GtmBaseError, PathError, ValidationError
from .gitcmd import GitRunner, runner_or_default

# --- The outcomes ----------------------------------------------------------------

OUTCOME_REFUSED = "refused"
OUTCOME_NOT_CHECKED = "not-checked"
OUTCOME_FLAGGED = "flagged"
OUTCOME_READY_WITH_GAPS = "ready-with-gaps"
OUTCOME_READY = "ready"

# Why a start was refused, in the order the steps are worked through.
REFUSED_INVALID = "invalid-declaration"
REFUSED_UNTRUSTED = "untrusted"
REFUSED_UNREADABLE = "unreadable"
REFUSED_REQUIRED = "required"

# The outcomes that hand the skill's instructions back, so its procedure runs
# and the run stays open until `finish`.
HANDS_BACK = (OUTCOME_NOT_CHECKED, OUTCOME_FLAGGED, OUTCOME_READY_WITH_GAPS, OUTCOME_READY)

# The kinds of document a skill may declare: the ones the moment-of-use check
# runs on. A lesson is create-only and a skill's own files are not documents
# another skill reads.
READABLE_KINDS = (docpaths.KIND_CONTEXT, docpaths.KIND_STANDARD, docpaths.KIND_STACK)

# The settings a skill declares its reads with (CS21).
READS_REQUIRED = "reads_required"
READS_OPTIONAL = "reads_optional"
STANDARD = "standard"

# The seat's record of runs, one line per event.
RUNS_FILE = "skill-runs.jsonl"
EVENT_STARTED = "started"
EVENT_COMPLETED = "completed"

# The word on the command line that says nobody is watching this run.
UNATTENDED_WORD = "--unattended"
RUNNER_SCRIPT = "use_skill.py"

# The names of an example's files (CS19 keeps an example one flat folder).
EXAMPLE_INPUT = "input"
EXAMPLE_OUTPUT = "output"
EXAMPLE_EXPECTATIONS = "expectations"
EXAMPLE_WRONG_PREFIX = "wrong-"
EXPECT_INCLUDE = "must include:"
EXPECT_EXCLUDE = "must not include:"

# The marked block an engine fact sits in, naming the file it is quoted from.
# The markers are visible lines, never hidden comments, because the screen
# refuses text a reader would not see.
ENGINE_OPEN_RE = re.compile(r"^\[engine:\s*(.+?)\s*\]$")
ENGINE_CLOSE = "[end engine]"

# A currency figure or a percentage, the two shapes the figure lint reads.
_FIGURE_RE = re.compile(
    r"(?:[$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s?[kKmMbB]\b)?)|(?:\d[\d,]*(?:\.\d+)?\s?%)"
)

# What in a skill's own text would call the runner, which only Claude Code
# has. A skill names none of it, so the same text can be served in chat.
_RUNNER_COMMAND_RE = re.compile(r"use_skill\.py|gtmbase\.runner|\buse-skill\b")

# --- The sentences a person reads ---------------------------------------------------

REFUSED_INVALID_SAYS = (
    "GTM Base did not run %s, because it says it reads %s, which is not a "
    "document in this base it can check."
)
REFUSED_NO_STANDARD = (
    "GTM Base did not run %s, because it does not say which standard it "
    "follows, and every skill has to."
)
REFUSED_UNTRUSTED_SAYS = (
    "GTM Base did not run %s, because this computer has not approved or "
    "accepted the skill exactly as it stands now."
)
REFUSED_NO_SKILL = (
    "GTM Base did not run %s, because this base holds no skill by that name "
    "that it can read whole."
)
REFUSED_UNREADABLE_SAYS = (
    "GTM Base did not run %s, because it could not read this base well enough "
    "to check the documents the skill reads."
)
REFUSED_REQUIRED_SAYS = (
    "GTM Base did not run %s, because it needs %s, and the base has no saved "
    "copy of it that can be read."
)
NOT_CHECKED_SAYS = (
    "This base was asked to stay quiet, so GTM Base did not check whether the "
    "documents below are still current. That is not a statement that they are."
)
FLAGGED_ATTENDED_SAYS = (
    "Before %s runs, a document it reads needs a choice from you."
)
FLAGGED_UNATTENDED_SAYS = (
    "Say this first in what you report: %s has not caught up with a context "
    "change that was recorded on %s. Hold every part of the work that depends "
    "on it, and carry on with the rest."
)
WRITTEN_TWICE_UNATTENDED_SAYS = (
    "Say this first in what you report: a context change about %s is written "
    "down twice and the two copies disagree. Hold every part of the work that "
    "depends on it, and carry on with the rest."
)
GAP_SAYS = (
    "The base holds no saved copy of %s, so leave out whatever would have "
    "come from it and say that it is missing. Do not guess at it."
)
UNSAVED_SAYS = (
    "%s has changes on this computer that are not saved yet, and they were "
    "left out. The skill reads it as it was last saved."
)
INSTRUCTIONS_SAYS = (
    "The approved instructions for %s follow. Follow them as written."
)
DOCUMENTS_SAYS = (
    "The documents the skill reads follow, each as the base last saved it."
)
FINISH_SCREENED = (
    "GTM Base did not accept this work, because it holds %s. Take it out and "
    "finish again."
)
FINISH_FIGURE = (
    "GTM Base did not accept this work, because the figure %s appears in none "
    "of the files it was built from. Use a figure from those files, or leave "
    "it out."
)
FINISH_ENGINE = (
    "GTM Base did not accept this work, because a marked engine block is not "
    "quoted line for line from %s."
)
FINISH_ENGINE_UNNAMED = (
    "GTM Base did not accept this work, because a marked engine block names a "
    "file it was not handed, or is never closed."
)
FINISH_NO_RUN = (
    "GTM Base has no open run with that name on this computer, so nothing was "
    "recorded."
)
FINISH_DONE = "GTM Base checked this work and recorded the run as completed."
EXPECTED_MISSING = "The output does not say %s, which the expectations ask for."
EXPECTED_PRESENT = "The output says %s, which the expectations rule out."
EXAMPLE_INCOMPLETE = (
    "The example %s is missing its %s, so the contract check cannot run it."
)
EXAMPLE_NO_WRONG = (
    "The example %s has no deliberately wrong output, so nothing shows the "
    "check would catch a bad one."
)
EXAMPLE_EXPECTS_NOTHING = (
    "The example %s has an expectations file that asks for nothing."
)
EXAMPLE_APPROVED_FAILS = (
    "The approved output of the example %s does not meet its own expectations."
)
EXAMPLE_WRONG_PASSES = (
    "A deliberately wrong output of the example %s passes the check, so the "
    "check would not catch it."
)
SKILL_NO_EXAMPLES = (
    "The skill %s has no examples, and every skill needs at least one."
)
SKILL_NAMES_A_COMMAND = (
    "The skill %s names one of GTM Base's own commands in its instructions. A "
    "skill keeps its procedure in plain instructions, so the same words work "
    "wherever it is served."
)


# --- The declaration ----------------------------------------------------------------


class Declaration(object):
    """What a skill says it reads, in the order it says it."""

    __slots__ = ("required", "optional", "standard", "problems")

    def __init__(self, required=(), optional=(), standard=None, problems=()):
        self.required: List[str] = list(required)
        self.optional: List[str] = list(optional)
        self.standard: Optional[str] = standard
        self.problems: List[Tuple[str, str]] = list(problems)

    def required_paths(self) -> List[str]:
        """The standard first, then each required document, each once."""
        found: List[str] = []
        for path in ([self.standard] if self.standard else []) + self.required:
            if path not in found:
                found.append(path)
        return found

    def optional_paths(self) -> List[str]:
        required = self.required_paths()
        found: List[str] = []
        for path in self.optional:
            if path not in required and path not in found:
                found.append(path)
        return found


def _listed(value) -> Optional[List[str]]:
    if value is None or value == "" or value == []:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _document_path(candidate: str) -> Optional[str]:
    found = docpaths.classify(candidate)
    if found is None or found.kind not in READABLE_KINDS:
        return None
    return found.path


def declaration_of(skill_text: str) -> Declaration:
    """The reads a `SKILL.md` declares, with each problem named (step 1)."""
    try:
        block, _body = formats.split_document(skill_text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        return Declaration(problems=[("settings", "")])
    problems: List[Tuple[str, str]] = []
    lists = {}
    for key in (READS_REQUIRED, READS_OPTIONAL):
        value = _listed(fields.get(key))
        if value is None:
            problems.append((key, ""))
            value = []
        checked = []
        for item in value:
            path = _document_path(item)
            if path is None:
                problems.append((key, item))
            else:
                checked.append(path)
        lists[key] = checked
    standard_value = fields.get(STANDARD)
    standard = None
    if not isinstance(standard_value, str) or not standard_value.strip():
        problems.append((STANDARD, ""))
    else:
        found = docpaths.classify(standard_value.strip())
        if found is None or found.kind != docpaths.KIND_STANDARD:
            problems.append((STANDARD, standard_value.strip()))
        else:
            standard = found.path
    return Declaration(lists[READS_REQUIRED], lists[READS_OPTIONAL], standard, problems)


# --- What a start hands back ----------------------------------------------------------


class Start(object):
    """One named outcome, and what may be handed to the skill with it."""

    def __init__(self, skill: str, attended: bool):
        self.skill = skill
        self.attended = attended
        self.outcome: Optional[str] = None
        self.refusal: Optional[str] = None
        self.sentences: List[str] = []
        self.run_id: Optional[str] = None
        # Path to text, in the order they are handed on.
        self.instructions: Dict[str, str] = {}
        self.documents: Dict[str, str] = {}
        self.document_hashes: Dict[str, str] = {}
        self.moments: List[moment.Moment] = []
        self.flagged: List[str] = []
        self.held: List[str] = []
        self.gaps: List[str] = []
        self.unsaved: List[str] = []
        self.checked: List[str] = []
        # Attended, flagged, and the person has not chosen yet.
        self.waiting = False

    @property
    def hands_back(self) -> bool:
        return self.outcome in HANDS_BACK and not self.waiting

    @property
    def question_ids(self) -> List[str]:
        return [one.question_id for one in self.moments if one.question_id]

    def render(self) -> str:
        """Everything the assistant is handed, in the one order it is handed."""
        pieces: List[str] = []
        if self.outcome == OUTCOME_REFUSED:
            pieces.extend(self.sentences)
            return "\n".join(pieces)
        if self.waiting:
            pieces.append(FLAGGED_ATTENDED_SAYS % self.skill)
            for one in self.moments:
                pieces.extend(["", one.block()])
                if one.question_id:
                    pieces.append(
                        "[for the assistant] question=%s file=%s" % (one.question_id, one.path)
                    )
            return "\n".join(pieces)
        pieces.extend(self.sentences)
        pieces.extend(["", INSTRUCTIONS_SAYS % self.skill])
        for path, text in self.instructions.items():
            pieces.extend(["", "[for the assistant] instructions=%s" % path, text.rstrip("\n")])
        if self.documents:
            pieces.extend(["", DOCUMENTS_SAYS])
            for path, text in self.documents.items():
                pieces.extend(["", "[for the assistant] document=%s" % path, moment.fenced(text)])
        if self.run_id:
            pieces.extend(["", "[for the assistant] run=%s" % self.run_id])
        return "\n".join(pieces)


def _refuse(start: Start, why: str, sentence: str) -> Start:
    start.outcome = OUTCOME_REFUSED
    start.refusal = why
    start.sentences = [sentence]
    return start


def _opening(sentence: str) -> str:
    """A sentence that opens with a document's name, with its first letter a capital."""
    return sentence[:1].upper() + sentence[1:]


def _decode(data: Optional[bytes]) -> Optional[str]:
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _instruction_order(skill: str, contents: Dict[str, bytes]) -> List[str]:
    """`SKILL.md` first, then its references by name. Examples are never handed on."""
    head = "%s/%s/SKILL.md" % (constants.SKILLS_DIR, skill)
    references = sorted(
        path for path in contents if "/references/" in path
    )
    return [head] + references


def conversation_id(base_id: Optional[str] = None) -> Optional[str]:
    """Which conversation this run belongs to, as Claude Code names it.

    Claude Code hands its own session identifier to every command it runs,
    and it is the identifier the command check marks. Without it, the seat's
    last recorded session is the best there is.
    """
    value = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if value:
        return value
    if base_id:
        seat, _problems = state.load_seat(base_id)
        found = seat.get("session_id")
        if isinstance(found, str) and found:
            return found
    return None


def start(
    base_root: str,
    base_id: str,
    skill: str,
    unattended: bool = False,
    conversation: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.date] = None,
) -> Start:
    """Run the seven steps for one skill and hand back the outcome (Unit 3.1).

    Saying unattended marks the conversation for the rest of its life (CS30),
    so a later start in it without the word is unattended too.
    """
    git = runner_or_default(runner)
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    if unattended and conversation:
        authority.mark_unattended(conversation)
    attended = not (unattended or authority.is_unattended(conversation))
    result = Start(skill, attended)
    result.run_id = ids.run_id(today)
    try:
        _work(result, base_root, base_id, skill, conversation, git, today)
    finally:
        _record_start(base_id, result, today)
    if not result.hands_back:
        result.run_id = None
    return result


def _work(result, base_root, base_id, skill, conversation, git, today) -> None:
    read = authority.read_skill(base_root, base_id, skill)
    if read is None:
        _refuse(result, REFUSED_UNTRUSTED, REFUSED_NO_SKILL % skill)
        return
    manifest, contents = read
    head = _instruction_order(skill, contents)[0]
    declaration = declaration_of(_decode(contents.get(head)) or "")

    # Step 1: every declared path is a document the check can run on.
    if declaration.problems:
        key, value = declaration.problems[0]
        if value:
            _refuse(result, REFUSED_INVALID, REFUSED_INVALID_SAYS % (skill, value))
        elif key == STANDARD:
            _refuse(result, REFUSED_INVALID, REFUSED_NO_STANDARD % skill)
        else:
            _refuse(result, REFUSED_INVALID, REFUSED_INVALID_SAYS % (skill, key))
        return

    # Step 2: the skill as it stands is one this seat trusts (CS10, CS11).
    if not authority.trusts(base_id, manifest):
        _refuse(result, REFUSED_UNTRUSTED, REFUSED_UNTRUSTED_SAYS % skill)
        return

    # Step 3: the base can be read for the check.
    declared = declaration.required_paths() + declaration.optional_paths()
    saved: Dict[str, Optional[str]] = {}
    try:
        if not base_reader.map_text(base_root):
            raise GtmBaseError("the map could not be read", code="unreadable")
        for path in declared:
            saved[path] = _saved_document(base_root, path, git)
    except (GtmBaseError, OSError):
        _refuse(result, REFUSED_UNREADABLE, REFUSED_UNREADABLE_SAYS % skill)
        return

    # Step 4: every required document is saved and readable.
    for path in declaration.required_paths():
        if saved.get(path) is None:
            _refuse(result, REFUSED_REQUIRED, REFUSED_REQUIRED_SAYS % (skill, names.document_name(path)))
            return

    for path in _instruction_order(skill, contents):
        result.instructions[path] = _decode(contents[path]) or ""
    for path in declared:
        text = saved.get(path)
        if text is None:
            result.gaps.append(path)
            continue
        result.documents[path] = text
        result.document_hashes[path] = authority.bytes_hash(text.encode("utf-8"))
        on_disk = _disk_text(base_root, path)
        if on_disk != text:
            result.unsaved.append(path)

    # Step 5: a silenced seat is not checked, and never called current.
    seat, _problems = state.load_seat(base_id)
    if state.is_silent(seat, today):
        result.outcome = OUTCOME_NOT_CHECKED
        result.sentences = [NOT_CHECKED_SAYS] + _gap_and_unsaved_sentences(result)
        return

    # Step 6: the moment-of-use check on each saved document.
    asking = conversation if result.attended else None
    for path in result.documents:
        found = moment.check(
            base_root, base_id, path, session_id=asking, runner=git, now=today, saved=True
        )
        result.checked.append(path)
        if found.code == moment.CODE_UNREADABLE:
            _refuse(result, REFUSED_UNREADABLE, REFUSED_UNREADABLE_SAYS % skill)
            result.instructions = {}
            result.documents = {}
            return
        if found.flagged or found.written_twice:
            result.moments.append(found)
            result.flagged.append(path)
    if result.flagged:
        result.outcome = OUTCOME_FLAGGED
        if result.attended:
            # The block and nothing else, until the person has chosen. Once
            # they chose to use each flagged document as it stands, the run
            # goes ahead and says each is still flagged; nothing is held,
            # because holding it is what they chose not to do.
            chosen = [
                one for one in result.moments
                if one.flagged and _used_as_is(base_id, one.question_id)
            ]
            if len(chosen) < len(result.moments):
                result.waiting = True
                return
            result.sentences = [
                _opening(moment.USED_AS_IS % names.document_name(one.path)) for one in chosen
            ] + _gap_and_unsaved_sentences(result)
            return
        result.held = list(result.flagged)
        first: List[str] = []
        for one in result.moments:
            if one.flagged:
                first.append(FLAGGED_UNATTENDED_SAYS % (names.document_name(one.path), one.happened_on))
            else:
                first.append(WRITTEN_TWICE_UNATTENDED_SAYS % names.document_name(one.path))
        result.sentences = first + _gap_and_unsaved_sentences(result)
        return

    # Step 7: ready, with any gap named.
    result.outcome = OUTCOME_READY_WITH_GAPS if result.gaps else OUTCOME_READY
    result.sentences = _gap_and_unsaved_sentences(result)


def _used_as_is(base_id: str, question_id: Optional[str]) -> bool:
    """Whether the person answered this question by using the document as it stands."""
    if not question_id:
        return False
    rows, _problems = state.load_asked(base_id)
    return any(
        row.get("question_id") == question_id
        and row.get("outcome") == constants.OUTCOME_USED_AS_IS
        for row in rows
    )


def _gap_and_unsaved_sentences(result: Start) -> List[str]:
    said = [GAP_SAYS % names.document_name(path) for path in result.gaps]
    said.extend(_opening(UNSAVED_SAYS % names.document_name(path)) for path in result.unsaved)
    return said


def _saved_document(base_root: str, path: str, git: GitRunner) -> Optional[str]:
    """One declared document as last saved, None when no saved copy can be read."""
    text = authority.saved_file(base_root, path, runner=git)
    if text is None:
        return None
    return text


def _disk_text(base_root: str, path: str) -> Optional[str]:
    full = os.path.join(base_root, path.replace("/", os.sep))
    if os.path.islink(full) or not os.path.isfile(full):
        return None
    try:
        with open(full, encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


# --- The seat's record of runs ----------------------------------------------------------


def runs_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), RUNS_FILE)


def _append(base_id: str, row: dict) -> None:
    """One line added to this seat's record of runs, never through a link."""
    path = runs_path(base_id)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(path, flags, 0o600)
    try:
        os.write(handle, (json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
    finally:
        os.close(handle)


def _record_start(base_id: str, result: Start, today: datetime.date) -> None:
    row = {
        "event": EVENT_STARTED,
        "run": result.run_id,
        "job": result.skill,
        "date": today.isoformat(),
        "attended": result.attended,
        "outcome": result.outcome or OUTCOME_REFUSED,
        "refusal": result.refusal,
        "documents": dict(result.document_hashes),
        "flags": list(result.flagged),
        "held": list(result.held),
        "gaps": list(result.gaps),
        "unsaved": list(result.unsaved),
    }
    _append(base_id, row)
    # A start that hands nothing back ran nothing, so it is closed at once
    # and never looks like a run that stopped part way.
    if not result.hands_back:
        _append(
            base_id,
            {
                "event": EVENT_COMPLETED,
                "run": result.run_id,
                "job": result.skill,
                "date": today.isoformat(),
                "outcome": row["outcome"],
                "ran": False,
            },
        )


def runs(base_id: str) -> List[dict]:
    """Every line of this seat's record of runs that can be read."""
    path = runs_path(base_id)
    if not os.path.isfile(path) or os.path.islink(path):
        return []
    found: List[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                found.append(value)
    return found


def incomplete(base_id: str) -> List[dict]:
    """Every started run with no completed line: stopping point unknown."""
    rows = runs(base_id)
    done = {row.get("run") for row in rows if row.get("event") == EVENT_COMPLETED}
    return [
        row for row in rows
        if row.get("event") == EVENT_STARTED and row.get("run") not in done
    ]


# --- Finish ------------------------------------------------------------------------


class Finish(object):
    """What `finish` found, and whether the run was recorded as completed."""

    def __init__(self, accepted: bool, problems: Sequence[str]):
        self.accepted = accepted
        self.problems = list(problems)

    def render(self) -> str:
        return FINISH_DONE if self.accepted else "\n".join(self.problems)


def _normal_figure(text: str) -> str:
    return re.sub(r"[\s,]", "", text).lower()


def figures_in(text: str) -> List[str]:
    """Every currency figure and percentage in a text, as written."""
    return [match.group(0) for match in _FIGURE_RE.finditer(text or "")]


def screen_work(output: str, sources: Dict[str, str]) -> List[str]:
    """Every problem `finish` finds in a work product, as sentences, none when clean.

    The same screens the contract check runs on an example's outputs.
    """
    problems: List[str] = []
    for found in review.screen(output):
        problems.append(
            FINISH_SCREENED
            % redaction_patterns.CLASS_LABELS.get(found, "something that must not be written down")
        )
    known = set()
    for text in sources.values():
        known.update(_normal_figure(one) for one in figures_in(text))
    for figure in figures_in(output):
        if _normal_figure(figure) not in known:
            problems.append(FINISH_FIGURE % figure.strip())
    problems.extend(_engine_problems(output, sources))
    return problems


def _source_named(name: str, sources: Dict[str, str]) -> Optional[str]:
    if name in sources:
        return sources[name]
    matches = [text for path, text in sources.items() if os.path.basename(path) == name]
    return matches[0] if len(matches) == 1 else None


def _engine_problems(output: str, sources: Dict[str, str]) -> List[str]:
    """Each marked engine block must be quoted line for line, in order, from its file."""
    problems: List[str] = []
    lines = (output or "").splitlines()
    index = 0
    while index < len(lines):
        opened = ENGINE_OPEN_RE.match(lines[index].strip())
        if not opened:
            index += 1
            continue
        name = opened.group(1)
        block: List[str] = []
        index += 1
        closed = False
        while index < len(lines):
            if lines[index].strip() == ENGINE_CLOSE:
                closed = True
                break
            block.append(lines[index])
            index += 1
        index += 1
        source = _source_named(name, sources)
        if not closed or source is None:
            problems.append(FINISH_ENGINE_UNNAMED)
            continue
        if not _is_excerpt(block, source):
            problems.append(FINISH_ENGINE % name)
    return problems


def _is_excerpt(block: Sequence[str], source: str) -> bool:
    wanted = [line.rstrip() for line in block if line.strip()]
    have = [line.rstrip() for line in source.splitlines()]
    position = 0
    for line in wanted:
        while position < len(have) and have[position] != line:
            position += 1
        if position == len(have):
            return False
        position += 1
    return True


def finish(
    base_id: str,
    run_id: str,
    output: str,
    sources: Dict[str, str],
    now: Optional[datetime.date] = None,
) -> Finish:
    """Check one work product against the files it came from and close its run."""
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    open_runs = {row.get("run"): row for row in incomplete(base_id)}
    started = open_runs.get(run_id)
    if not run_id or started is None:
        return Finish(False, [FINISH_NO_RUN])
    problems = screen_work(output, sources)
    if problems:
        return Finish(False, problems)
    _append(
        base_id,
        {
            "event": EVENT_COMPLETED,
            "run": run_id,
            "job": started.get("job"),
            "date": today.isoformat(),
            "outcome": started.get("outcome"),
            "ran": True,
            "output": authority.bytes_hash(output.encode("utf-8")),
            "sources": {
                path: authority.bytes_hash(text.encode("utf-8"))
                for path, text in sorted(sources.items())
            },
        },
    )
    return Finish(True, [])


# --- The contract check (CS26) -------------------------------------------------------------


class Contract(object):
    """Whether a skill's examples hold, with each problem as a sentence."""

    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)

    @property
    def passed(self) -> bool:
        return not self.problems


def names_a_command(text: str) -> bool:
    """Whether a skill's text names one of the runner's own commands."""
    return bool(_RUNNER_COMMAND_RE.search(text or ""))


def expectations_of(text: str) -> List[Tuple[str, str]]:
    """The expectations an example sets, as (kind, words) pairs."""
    found: List[Tuple[str, str]] = []
    for line in (text or "").splitlines():
        cleaned = line.strip().lstrip("-*").strip()
        lowered = cleaned.lower()
        for kind in (EXPECT_EXCLUDE, EXPECT_INCLUDE):
            if lowered.startswith(kind):
                words = cleaned[len(kind):].strip()
                if words:
                    found.append((kind, words))
                break
    return found


def judge_output(output: str, expectations: Sequence[Tuple[str, str]], sources: Dict[str, str]) -> List[str]:
    """Every way one written output misses its expectations or the screens."""
    problems = screen_work(output, sources)
    folded = " ".join((output or "").split()).lower()
    for kind, words in expectations:
        present = " ".join(words.split()).lower() in folded
        if kind == EXPECT_INCLUDE and not present:
            problems.append(EXPECTED_MISSING % words)
        if kind == EXPECT_EXCLUDE and present:
            problems.append(EXPECTED_PRESENT % words)
    return problems


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def check_example(name: str, files: Dict[str, str]) -> List[str]:
    """One example folder, as its file names and texts: the problems, none when it holds."""
    by_stem: Dict[str, Tuple[str, str]] = {}
    for path, text in files.items():
        by_stem[_stem(path)] = (path, text)
    for needed, said in (
        (EXAMPLE_INPUT, "input"),
        (EXAMPLE_OUTPUT, "approved output"),
        (EXAMPLE_EXPECTATIONS, "expectations file"),
    ):
        if needed not in by_stem:
            return [EXAMPLE_INCOMPLETE % (name, said)]
    wrong = sorted(stem for stem in by_stem if stem.startswith(EXAMPLE_WRONG_PREFIX))
    if not wrong:
        return [EXAMPLE_NO_WRONG % name]
    expectations = expectations_of(by_stem[EXAMPLE_EXPECTATIONS][1])
    if not expectations:
        return [EXAMPLE_EXPECTS_NOTHING % name]
    outputs = {EXAMPLE_OUTPUT, EXAMPLE_EXPECTATIONS} | set(wrong)
    sources = {path: text for stem, (path, text) in by_stem.items() if stem not in outputs}
    problems: List[str] = []
    if judge_output(by_stem[EXAMPLE_OUTPUT][1], expectations, sources):
        problems.append(EXAMPLE_APPROVED_FAILS % name)
    for stem in wrong:
        if not judge_output(by_stem[stem][1], expectations, sources):
            problems.append(EXAMPLE_WRONG_PASSES % name)
    return problems


def check_skill(skill: str, files: Dict[str, str]) -> Contract:
    """The contract check over one skill's files, keyed by base path (CS26).

    It runs before any new or changed skill is shown for approval. No model is
    called; judgment is the approver's reading of a real replay.
    """
    problems: List[str] = []
    if any(
        names_a_command(text) for path, text in files.items() if "/examples/" not in path
    ):
        problems.append(SKILL_NAMES_A_COMMAND % skill)
    examples: Dict[str, Dict[str, str]] = {}
    for path, text in files.items():
        parts = path.split("/")
        if len(parts) == 5 and parts[2] == "examples":
            examples.setdefault(parts[3], {})[parts[4]] = text
    if not examples:
        problems.append(SKILL_NO_EXAMPLES % skill)
    for name in sorted(examples):
        problems.extend(check_example(name, examples[name]))
    return Contract(problems)


def check_examples(base_root: str, base_id: str, skill: str) -> Contract:
    """The contract check over one skill as it sits in a base."""
    read = authority.read_skill(base_root, base_id, skill)
    if read is None:
        return Contract([REFUSED_NO_SKILL % skill])
    _manifest, contents = read
    texts = {path: (_decode(data) or "") for path, data in contents.items()}
    return check_skill(skill, texts)


def starts_unattended(command: str) -> bool:
    """Whether a command line starts the runner with the unattended word.

    Read loosely on purpose: a wrong yes only marks a conversation whose
    approvals are then refused, which is the safe direction.
    """
    text = command or ""
    return RUNNER_SCRIPT in text and re.search(
        r"(?<!\S)%s(?!\S)" % re.escape(UNATTENDED_WORD), text
    ) is not None
