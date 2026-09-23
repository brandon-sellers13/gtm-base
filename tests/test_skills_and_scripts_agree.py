"""Every command a skill tells the assistant to run is one its script accepts.

Finding V10 of the 2026-09-20 verification round is the reason this exists. The
skill documented a command without the argument the fix had just made
necessary, every test supplied that argument by hand, and the shipped
invocation was the one nobody ran. So the commands are read out of the skills
themselves here, and each one is put to the parser of the script it names.

The same reading answers finding N2. A value on a command line that could have
come out of a document, off a file name, or out of somebody's typing is a value
whose author chooses what the shell does, so every one of those now travels in
a file the script itself handed out, or as a number off a list the script
printed. This checks that no command line in any skill carries one.
"""

import importlib.util
import os
import re
import shlex
import subprocess
import sys
import unittest

import support

SKILLS_DIR = os.path.join(support.PLUGIN_DIR, "skills")

# Where each script named in a skill really lives.
SCRIPTS = {
    "join.py": os.path.join(SKILLS_DIR, "join", "scripts", "join.py"),
    "propose.py": os.path.join(
        SKILLS_DIR, "propose-change", "scripts", "propose.py"
    ),
    "approve_local.py": os.path.join(
        SKILLS_DIR, "propose-change", "scripts", "approve_local.py"
    ),
    "confirm.py": os.path.join(SKILLS_DIR, "confirm", "scripts", "confirm.py"),
    "stale_check.py": os.path.join(
        SKILLS_DIR, "stale-check", "scripts", "stale_check.py"
    ),
    "moment.py": os.path.join(support.PLUGIN_DIR, "scripts", "moment.py"),
}

# A command line, wherever it appears: inside a fenced block or in backticks.
_COMMAND_RE = re.compile(r"python3\s+(?P<command>[^\n`]+\.py[^\n`]*)")

# A value somebody else wrote. Every one of these has to reach a script inside
# a file the script handed out, so none of them may stand on a command line.
THEIR_OWN_WORDS = (
    "--company",
    "--label",
    "--answer",
    "--got-in-the-way",
    "--source",
    "--what-changed",
    "--reason",
)
# The same flags with a file after them, which is how those values travel now.
BY_FILE = tuple(name + "-file" for name in THEIR_OWN_WORDS)


def every_skill_file():
    found = []
    for folder, _dirs, names in os.walk(SKILLS_DIR):
        for name in sorted(names):
            if name.endswith(".md"):
                found.append(os.path.join(folder, name))
    return sorted(found)


def commands_in(path):
    """Every command line one document tells the assistant to run."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    found = []
    for match in _COMMAND_RE.finditer(text):
        command = match.group("command").strip().rstrip("`").strip()
        line_number = text[: match.start()].count("\n") + 1
        found.append((line_number, command))
    return found


# A flag written in prose, in backticks, next to a command: "Add `--email
# <address>` when they gave one." Finding R9 of Astra's third look is why these
# are read at all: the walk ran only the command lines, so the optional
# additions a skill describes in its sentences were never run, and the sixth
# documented command that did not work as written was one of those.
_PROSE_FLAG_RE = re.compile(r"`(--[^`\n]+)`")
_HEADING_LINE_RE = re.compile(r"^#{1,6}\s")


def _is_a_hand_out(words):
    """Whether a command only hands out a file, which nothing is added to."""
    return "words-file" in words or "--new-words-file" in words


def _script_of(words):
    for word in words:
        if word.endswith(".py"):
            return os.path.basename(word)
    return None


_PARSERS = {}


def _actions_of(script):
    """Every flag one script accepts, and whether each one takes a value."""
    if script not in _PARSERS:
        taken = {}
        for action in parser_for(SCRIPTS[script])._actions:
            for name in action.option_strings:
                taken[name] = action.nargs != 0
        _PARSERS[script] = taken
    return _PARSERS[script]


def prose_flags_in(path):
    """Every flag a document names in its sentences, and what it belongs to.

    Each one comes back as (line, the words in backticks, the line of the
    command it belongs to, that command, and whether it is something to run).
    It belongs to the nearest command before it in the same section that does
    not only hand out a file and does not already carry that flag. A bare flag
    that needs a value, such as "what to pass to `--drop`", is a flag being
    named rather than an addition to run, and it is still checked against the
    script it belongs to.
    """
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    commands = []
    for match in _COMMAND_RE.finditer(text):
        command = match.group("command").strip().rstrip("`").strip()
        commands.append((match.start(), text[: match.start()].count("\n") + 1, command))
    headings = []
    offset = 0
    for line in text.split("\n"):
        if _HEADING_LINE_RE.match(line):
            headings.append(offset)
        offset += len(line) + 1
    found = []
    for match in _PROSE_FLAG_RE.finditer(text):
        span = match.group(1).strip()
        if "python3" in span:
            continue
        line_number = text[: match.start()].count("\n") + 1
        first = span.split()[0].split("=")[0]
        base = None
        for start, number, command in reversed(commands):
            if start >= match.start():
                continue
            if any(start < heading < match.start() for heading in headings):
                break
            words = words_of(command)
            if _is_a_hand_out(words) or first in words:
                continue
            base = (number, command)
            break
        runnable = False
        if base is not None:
            script = _script_of(words_of(base[1]))
            takes_value = _actions_of(script).get(first) if script in SCRIPTS else None
            runnable = not (len(span.split()) == 1 and takes_value)
        found.append(
            (
                line_number,
                span,
                base[0] if base else None,
                base[1] if base else None,
                runnable,
            )
        )
    return found


def commands_with_prose(path):
    """Every command line, and every command as a sentence says to extend it."""
    found = list(commands_in(path))
    for line_number, span, _base_line, base, runnable in prose_flags_in(path):
        if runnable:
            found.append((line_number, base + " " + span))
    return found


def words_of(command):
    """One command line split into words, with the placeholders kept whole."""
    words = []
    for piece in command.replace("'", " ").replace('"', " ").split():
        words.append(piece)
    return words


def parser_for(script_path):
    name = "script_" + os.path.basename(script_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_parser()


def known_flags(parser):
    found = set()
    for action in parser._actions:
        for name in action.option_strings:
            found.add(name)
    return found


class TestEverySkillCommandIsOneItsScriptAccepts(unittest.TestCase):
    def test_every_flag_a_skill_names_is_one_the_script_knows(self):
        problems = []
        parsers = {}
        for path in every_skill_file():
            for line_number, command in commands_with_prose(path):
                words = words_of(command)
                script = None
                for word in words:
                    if word.endswith(".py"):
                        script = os.path.basename(word)
                        break
                if script not in SCRIPTS:
                    problems.append(
                        "%s line %d names a script nobody knows: %s"
                        % (os.path.basename(path), line_number, script)
                    )
                    continue
                if script not in parsers:
                    parsers[script] = known_flags(parser_for(SCRIPTS[script]))
                for word in words:
                    if not word.startswith("--"):
                        continue
                    flag = word.split("=")[0]
                    if flag not in parsers[script]:
                        problems.append(
                            "%s line %d: %s does not accept %s"
                            % (os.path.basename(path), line_number, script, flag)
                        )
        self.assertEqual([], problems)

    def test_every_flag_named_in_a_sentence_is_one_its_script_knows(self):
        """R9. A flag in a sentence is still a flag somebody will type."""
        problems = []
        for path in every_skill_file():
            scripts = set(
                _script_of(words_of(command)) for _n, command in commands_in(path)
            )
            for line_number, span, _base_line, base, _runnable in prose_flags_in(path):
                first = span.split()[0].split("=")[0]
                if base is not None:
                    owners = [_script_of(words_of(base))]
                else:
                    owners = [name for name in scripts if name in SCRIPTS]
                if not any(
                    name in SCRIPTS and first in _actions_of(name) for name in owners
                ):
                    problems.append(
                        "%s line %d names %s, which %s does not accept"
                        % (
                            os.path.basename(path),
                            line_number,
                            first,
                            " or ".join(str(name) for name in owners) or "no script",
                        )
                    )
                if first in THEIR_OWN_WORDS:
                    problems.append(
                        "%s line %d tells the assistant to put somebody's words "
                        "on a command line with %s"
                        % (os.path.basename(path), line_number, first)
                    )
        self.assertEqual([], problems)

    def test_no_command_carries_words_somebody_else_wrote(self):
        """A fixed word such as yes is fine. Anything to be filled in is not."""
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_with_prose(path):
                words = words_of(command)
                for index, word in enumerate(words):
                    flag = word.split("=")[0]
                    if flag in BY_FILE or flag not in THEIR_OWN_WORDS:
                        continue
                    value = words[index + 1] if index + 1 < len(words) else ""
                    if "<" not in value:
                        continue
                    problems.append(
                        "%s line %d puts %s on a command line"
                        % (os.path.basename(path), line_number, flag)
                    )
        self.assertEqual([], problems)

    def test_the_files_to_draft_from_are_named_by_number(self):
        """N2. A file name is somebody else's text, and a number is not."""
        problems = []
        for path in every_skill_file():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for match in re.finditer(r"--only\s+(\S+)", text):
                value = match.group(1).strip("`'\"")
                line_number = text[: match.start()].count("\n") + 1
                if "label" in value or ".md" in value or ".csv" in value:
                    problems.append(
                        "%s line %d names files rather than numbering them"
                        % (os.path.basename(path), line_number)
                    )
        self.assertEqual([], problems)

    def test_every_command_that_reads_a_draft_says_which_run_it_is(self):
        """N9. A draft is only read from the folder that run was given."""
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_with_prose(path):
                words = words_of(command)
                if "--draft" not in words:
                    continue
                if "--run" not in words:
                    problems.append(
                        "%s line %d reads a draft without saying which run"
                        % (os.path.basename(path), line_number)
                    )
        self.assertEqual([], problems)



# --- H3 of the third look: run them, do not only parse them ------------------

# Every flag whose reader needs to know which run or session the file it names
# belongs to, and the flags that say so. A command carrying one without the
# other is a command that is refused every time it is run.
NEEDS_A_KEY = (
    "--answer-file",
    "--got-in-the-way-file",
    "--company-file",
    "--label-file",
    "--draft",
)
SAYS_THE_KEY = ("--run", "--session")

# The flags that read a words file and take it away, so the next step has to
# ask for one of its own.
# The ways a documented command line asks for a file in words rather than
# naming one a command before it printed.
NAMES_A_FILE_IN_WORDS = (
    "<a fresh company file>",
    "<a fresh folder file>",
    "<the path from step 4>",
    "<path to their words>",
    "<path to what they said>",
)

CONSUMES_WORDS = (
    "--folder-file",
    "--company-file",
    "--label-file",
    "--answer-file",
    "--got-in-the-way-file",
    "--reason-file",
    "--source-file",
    "--what-changed-file",
    "--words",
    "--content-folder-file",
    "--add-file",
)

# One documented command per script that is actually run, with the placeholders
# filled in, so that a command nobody has ever run cannot ship again.


class TestEveryCommandThatNamesAFileSaysWhichRunItIsFor(unittest.TestCase):
    """H3. The company step was refused every time for want of the run."""

    def test_no_documented_command_leaves_the_key_out(self):
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_with_prose(path):
                words = words_of(command)
                if not any(flag in words for flag in NEEDS_A_KEY):
                    continue
                script = None
                for word in words:
                    if word.endswith(".py"):
                        script = os.path.basename(word)
                if script != "join.py":
                    # The other scripts work out the key from the base the
                    # session is open in, so there is nothing to put on the
                    # command line.
                    continue
                if any(flag in words for flag in SAYS_THE_KEY):
                    continue
                problems.append(
                    "%s line %d names a file without saying which run it is for"
                    % (os.path.basename(path), line_number)
                )
        self.assertEqual([], problems)


class TestTheSkillsAsTheyAreWritten(unittest.TestCase):
    """Every command a skill prints, taken from the skill, filled in, and run.

    Finding G1 of the final confirmation pass, and the reason this is built
    the way it is. The walk before this held a hand-written copy of the
    commands, and the copy still said `--folder` after the skill had started
    saying `--folder-file`, so the documented step was never run and setting a
    base up could not be followed as written. That was the fourth round in a
    row to ship a documented command that does not work.

    So nothing is hand written here. The command lines come out of the skill
    documents as text, the angle-bracket placeholders are filled from one
    table, and a placeholder with no filler is a failure rather than a skip.
    At the end every documented command line must have been run.
    """

    # Which documents are walked, and which script each one is about. A
    # document not named here is still read by the checks above; it is only
    # the running that is listed, because running a command needs a state to
    # run it against.
    WALKED = (
        "join/SKILL.md",
        "propose-change/SKILL.md",
        "confirm/SKILL.md",
        "stale-check/SKILL.md",
    )

    # The commands a skill prints on purpose to say they are refused in this
    # release. They are run like everything else and have to be refused.
    REFUSED_ON_PURPOSE = ("backup", "invite", "join-link")

    def document(self, relative):
        return os.path.join(SKILLS_DIR, relative.replace("/", os.sep))

    # --- the sandbox this walk happens in ---------------------------------

    def material(self):
        """A folder of somebody's own marketing material, in two places."""
        home = os.environ["HOME"]
        support.write(
            os.path.join(home, ".gitconfig"),
            "[user]\n\temail = dana@acme.test\n\tname = Dana\n",
        )
        folder = os.path.join(home, "marketing")
        support.write(
            os.path.join(folder, "customers", "acme-icp.md"),
            "# Who we sell to\n\nSmall teams selling to other businesses.\n",
        )
        support.write(
            os.path.join(folder, "customers", "personas.md"),
            "# Buyer personas\n\nThe head of marketing.\n",
        )
        support.write(
            os.path.join(folder, "positioning", "messaging.md"),
            "# Messaging\n\nWe win on setup time.\n",
        )
        support.write(
            os.path.join(folder, "positioning", "pricing-notes.txt"),
            "We lead with the monthly number now.\n",
        )
        return folder

    def run_line(self, command, cwd):
        words = shlex.split(command)
        script = SCRIPTS[os.path.basename(words[0])]
        return subprocess.run(
            [sys.executable, script] + words[1:],
            cwd=cwd,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def value_of(self, printed, name):
        for line in printed.split("\n"):
            if line.startswith(name + "="):
                value = line[len(name) + 1 :].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                return value
        return None

    # --- filling in the angle brackets ------------------------------------

    def fill(self, command, state):
        """One documented command with every placeholder replaced.

        A placeholder nobody has a filler for stops the walk, because a
        command this cannot fill in is a command nobody has run.
        """
        found = re.findall(r"<[^<>]+>", command)
        for placeholder in found:
            filler = self.FILLERS.get(placeholder)
            if filler is None:
                raise AssertionError(
                    "no filler for %s, in: %s" % (placeholder, command)
                )
            value = filler(self, state, command)
            self.assertIsNotNone(
                value, "nothing to fill %s with, in: %s" % (placeholder, command)
            )
            # Quoted, because a real value holds spaces and a real folder
            # name can hold anything at all. The skill tells a person to put
            # the value in; what a shell does with it afterwards is the
            # shell's, and this stands in for that faithfully.
            command = command.replace(placeholder, shlex.quote(str(value)), 1)
        return command

    def a_words_file(self, state, kind, text):
        """Ask the skill's own command for a path, and put the words in it."""
        arguments = ["words-file", "--for", kind]
        if state.get("run"):
            arguments += ["--run", state["run"]]
        else:
            arguments += ["--base", state["base"]]
        finished = self.run_line(
            "join.py " + " ".join(shlex.quote(item) for item in arguments),
            state["cwd"],
        )
        printed = finished.stdout.decode("utf-8")
        self.assertEqual(0, finished.returncode, printed + finished.stderr.decode())
        path = self.value_of(printed, "words")
        self.assertTrue(path, printed)
        support.write(path, text)
        state.setdefault("handed", {})[kind] = path
        return path

    def a_run(self, state):
        """The run this walk is in, started the moment a command needs one.

        A skill says how words travel before it says how a setup run begins,
        so the first command that names a run comes before the one that makes
        it. Making one here rather than skipping that command is the point:
        every command the skill prints has to be one that runs.
        """
        if not state.get("run"):
            finished = self.run_line("join.py new-run", state["cwd"])
            printed = finished.stdout.decode("utf-8")
            self.assertEqual(0, finished.returncode, printed)
            state["run"] = self.value_of(printed, "run")
        return state["run"]

    # Which kind of words file each flag reads, so that a command carrying two
    # of them is filled with the two files it was handed, each by its own
    # hand-out, rather than with whichever was handed out last (R9).
    KIND_OF_FLAG = {
        "--words": "answer",
        "--folder-file": "folder",
        "--company-file": "company",
        "--label-file": "label",
        "--answer-file": "answer",
        "--got-in-the-way-file": "got-in-the-way",
        "--reason-file": "reason",
        "--source-file": "source",
        "--what-changed-file": "what-changed",
        "--content-folder-file": "folder",
        "--add-file": "folder",
    }

    def _flag_before(self, command, placeholder):
        before = command.split(placeholder, 1)[0].split()
        return before[-1] if before else ""

    def _the_path_it_printed(self, state, command):
        """The last path a command printed, which depends on the command.

        Two steps of the skill fill this in: one with the file a words command
        handed out, and one with the document the reconcile step named. The
        file handed out is the one of the kind the flag in front of it reads,
        and it has to have been handed out by a command before this one.
        """
        flag = self._flag_before(command, "<the path it printed>")
        if flag == "--file":
            return self.a_document_to_ask_about(state)
        kind = self.KIND_OF_FLAG.get(flag)
        if kind is not None:
            return (state.get("handed") or {}).get(kind)
        return state.get("words")

    def _a_fresh_folder_file(self, state, command):
        """A folder file the skill asks for in words: the folder they named, or
        for a folder to add, one folder inside it."""
        flag = self._flag_before(command, "<a fresh folder file>")
        text = "customers" if flag == "--add-file" else state["material"]
        return self.a_words_file(state, "folder", text)

    def _a_place_to_drop(self, state, command):
        """The number of a place the survey printed, never the only one."""
        numbers = state.get("place_numbers") or []
        return numbers[-1] if len(numbers) > 1 else None

    def a_kept_proposal(self, state):
        """A proposal that was raised and kept, which is what is raised again.

        The skill's last way of raising one is for a change that was turned
        down or set aside, so there is one of those waiting in the folder they
        are kept in. It is a second one, never the one still waiting to be
        approved, because a person has both.
        """
        from gtmbase import constants

        folder = os.path.join(state["base"], constants.PROPOSALS_OPENED_DIR)
        kept = state.get("kept_id")
        if kept is None:
            staged = state["staged"]
            kept = "stg-" + "d" * 16
            text = support.read(staged).replace(
                os.path.basename(staged)[: -len(".md")], kept
            )
            support.write(os.path.join(folder, kept + ".md"), text)
            state["kept_id"] = kept
        return kept

    def a_document_to_ask_about(self, state):
        """The next document the reconcile step said to ask about."""
        waiting = state.get("ask_about") or []
        if not waiting:
            return None
        return waiting.pop(0) if len(waiting) > 1 else waiting[0]

    FILLERS = {
        "<run identifier>": lambda self, state, command: self.a_run(state),
        "<session id>": lambda self, state, command: "sess-1",
        "<their address>": lambda self, state, command: "dana@acme.test",
        "<step>": lambda self, state, command: state.get("step", "icp"),
        "<number>": lambda self, state, command: state.get("folder_number", "1"),
        "<base folder>": lambda self, state, command: state.get("base"),
        "<base folder or company name>": lambda self, state, command: state.get("base"),
        "<the parent from step 4>": lambda self, state, command: state.get("parent"),
        "<draft file>": lambda self, state, command: state.get("draft"),
        "<the path it printed>": _the_path_it_printed,
        "<id>": lambda self, state, command: (
            state.get("question")
            if "--question" in shlex.split(command)
            else state.get("change")
        ),
        "<the id the approve printed>": lambda self, state, command: state.get("change"),
        "<folder>": lambda self, state, command: state.get("material"),
        "<kind>": lambda self, state, command: "answer",
        "<path>": lambda self, state, command: (
            state.get("document")
            if "--show-document" in shlex.split(command)
            else state.get("staged")
        ),
        "<a short label>": lambda self, state, command: "a note from the call",
        "<file you wrote it to>": lambda self, state, command: state.get("paste"),
        "<the path from step 4>": lambda self, state, command: state.get("words"),
        "<a fresh company file>": lambda self, state, command: self.a_words_file(
            state, "company", self.WORDS["company"]
        ),
        "<a fresh folder file>": _a_fresh_folder_file,
        "<place number>": _a_place_to_drop,
        "<the number they chose>": lambda self, state, command: "1",
        "<path to their words>": lambda self, state, command: state.get("words"),
        "<address>": lambda self, state, command: "dana@acme.test",
        "<the path add-paste printed>": lambda self, state, command: state.get(
            "held_paste"
        ),
        "<proposal id>": lambda self, state, command: self.a_kept_proposal(state),
        "<path to the staged file>": lambda self, state, command: state.get("staged"),
        "<the path it printed for the words>": lambda self, state, command: state.get("words"),
        "<path to the prepared change>": lambda self, state, command: state.get("staged"),
        "<the shown value>": lambda self, state, command: state.get("shown"),
    }

    # --- what each command needs before it, and what it leaves behind ------

    def before(self, mode, state, command):
        """Put the state this documented command needs in place first."""
        # A step the skill names outright, rather than leaving to be filled
        # in, says which document the commands around it are about.
        words = shlex.split(command)
        for index, word in enumerate(words):
            if word == "--step" and index + 1 < len(words):
                named = words[index + 1]
                if not named.startswith("<"):
                    state["step"] = named
        if mode == "words-file":
            return
        # A file is supplied here only when the documented line asks for one in
        # words. A line that says the path it printed is a line the skill has
        # to have printed a hand-out for, and finding W1 of the confirmation
        # round is what covering for that cost: a skill that stopped printing
        # one still passed the walk that exists to catch exactly that.
        asks_in_words = any(
            placeholder in command for placeholder in NAMES_A_FILE_IN_WORDS
        )
        for flag, kind in (
            ("--words", "answer"),
            ("--folder-file", "folder"),
            ("--company-file", "company"),
            ("--label-file", "label"),
            ("--answer-file", "answer"),
            ("--got-in-the-way-file", "got-in-the-way"),
            ("--reason-file", "reason"),
            ("--source-file", "source"),
            ("--what-changed-file", "what-changed"),
        ):
            if not asks_in_words:
                continue
            if flag in words and state.get("words_kind") != kind:
                # Only when the skill did not print the hand-out itself. A
                # step that prints one is walked through that one, which is
                # the whole point of reading the commands out of the skill.
                state["words"] = self.a_words_file(
                    state,
                    kind,
                    state["material"] if kind == "folder" else self.WORDS[kind],
                )
                state["words_kind"] = kind
        if "--local-edit" in words:
            # A change made by hand is a document the person has edited, so
            # there has to be one for this command to have anything to do.
            full = os.path.join(state["base"], state["document"])
            support.write(
                full,
                support.read(full).replace(
                    "Companies of any size.",
                    "Companies of twenty to two hundred people.",
                ),
            )
        if mode == "add-paste":
            state["paste"] = os.path.join(state["cwd"], "pasted.txt")
            support.write(state["paste"], "We win on setup time.\n")
        if mode in ("review", "approve", "preview-change") and state.get("draft"):
            support.write(state["draft"], self.a_draft_for(state["step"]))

    # What a walk writes into each kind of words file. They are the words a
    # person would really type at that step, and nothing here is the note GTM
    # Base writes asking for wording, which every path refuses.
    WORDS = {
        "answer": "We sell to companies of twenty to two hundred people.",
        "company": "Acme",
        "got-in-the-way": "The folder took a while to find.",
        "label": "a note from the call",
        "reason": "We moved up market, so this is out of date now.",
        "source": "The quarterly review deck, slide four, said so.",
        "what-changed": "We moved up market because the small ones churned.",
    }

    def handed_out(self, state, command, printed):
        """Fill in whatever a documented hand-out command just made room for."""
        words = shlex.split(command)
        kind = None
        for index, word in enumerate(words):
            if word in ("--for", "--new-words-file") and index + 1 < len(words):
                kind = words[index + 1]
        if kind is None:
            return
        path = self.value_of(printed, "words")
        if not path:
            return
        text = self.WORDS.get(kind)
        if kind == "folder":
            text = state["material"]
        self.assertIsNotNone(kind, command)
        support.write(path, text or "Acme")
        state["words"] = path
        state["words_kind"] = kind
        state.setdefault("handed", {})[kind] = path

    def after(self, mode, state, printed):
        """Read out of what it printed whatever the next commands need."""
        for name in ("run", "parent", "draft", "base", "change", "prompt"):
            value = self.value_of(printed, name)
            if value:
                state[name] = value
        if mode == "reconcile":
            state["ask_about"] = [
                line[len("file=") :].strip()
                for line in printed.split("\n")
                if line.startswith("file=")
            ]
        prepared = self.value_of(printed, "prepared")
        if prepared:
            state["staged"] = prepared
        shown = None
        for line in printed.split("\n"):
            if line.startswith("Shown value: "):
                shown = line[len("Shown value: ") :].strip()
        if shown:
            state["shown"] = shown
        if mode == "list-sources":
            for line in printed.split("\n"):
                if line.startswith("folder=") and " number=" in line:
                    state["folder_number"] = line.split(" number=")[1].split(" ")[0]
                    break
        if mode == "survey":
            state["place_numbers"] = [
                line.split(" number=")[1].split(" ")[0]
                for line in printed.split("\n")
                if line.startswith("place=") and " number=" in line
            ]
        if mode == "add-paste":
            held = self.value_of(printed, "paste")
            if held:
                state["held_paste"] = held

    def a_draft_for(self, step):
        import test_join_setup_flow as flow

        if step == "change-entry":
            # The change names the part of the document it is about, which is
            # what lets the wording go in without a part being named.
            return flow.change_draft(
                body="Firmographics changed: we stopped selling to companies "
                "under twenty people."
            )
        return flow.captured("icp.md" if step == "icp" else "positioning.md")

    # --- the walk itself ---------------------------------------------------

    # Some documented commands are alternative answers to one thing, and a
    # person gives one of them. Approving a document and skipping it are two
    # answers to one document; yes, no and not now are three answers to one
    # question; the wording names the part of a document or leaves it off.
    # The walk is made once for each alternative and every documented command
    # line has to have run in one of those passes.

    def _group_of(self, words, command):
        """Which set of alternatives this command belongs to, and which one."""
        script = os.path.basename(words[0])
        mode = words[1] if len(words) > 1 and not words[1].startswith("-") else ""
        if "--wording" in words:
            return "the wording", "--section" in words
        if "--answer" in words and script == "confirm.py":
            return "the answer", words[words.index("--answer") + 1]
        for answer in ("--approve", "--not-yet", "--drop"):
            if answer in words and script == "approve_local.py":
                # Approving a prepared change, leaving it, and throwing it
                # away are three answers to one change.
                return "the answer about a prepared change", answer
        if mode in ("approve", "skip") and "<step>" in command and "--parent" not in command:
            # A command that names its own step is about one document and has
            # no alternative, and the first document somebody approves is what
            # makes the base, so neither of those is in this set.
            return "the answer about a document", mode
        return None, None

    def _alternatives(self, lines):
        """Every set of alternatives this document prints, in the order shown."""
        found = {}
        for _number, command in lines:
            words = shlex.split(command)
            if not words or os.path.basename(words[0]) not in SCRIPTS:
                continue
            key, member = self._group_of(words, command)
            if key is None:
                continue
            members = found.setdefault(key, [])
            if member not in members:
                members.append(member)
        return found

    def _taken_this_pass(self, words, command, index):
        """Whether this line is the alternative this pass is taking."""
        key, member = self._group_of(words, command)
        if key is None:
            return True
        members = self.alternatives.get(key) or []
        if len(members) < 2:
            return True
        return member == members[index % len(members)]

    def _additions(self, path):
        """What sentences say to add to each command, keyed by its line."""
        found = {}
        for line_number, span, base_line, _base, runnable in prose_flags_in(path):
            if not runnable:
                continue
            found.setdefault(base_line, []).append((line_number, span))
        return found

    def test_every_documented_command_runs_as_it_is_written(self):
        for relative in self.WALKED:
            with self.subTest(document=relative):
                self.walk_everything(self.document(relative), relative)

    def walk_everything(self, path, relative):
        """Every command in one document, and every addition its sentences name."""
        lines = commands_in(path)
        self.assertTrue(lines, "no commands found in %s" % relative)
        self.document_walked = relative
        self.alternatives = self._alternatives(lines)
        self.additions = self._additions(path)
        self.additions_ran = set()
        self.times_taken = {}
        wanted = set(
            number
            for extra in self.additions.values()
            for number, _span in extra
        )
        passes = max(
            [2]
            + [len(members) for members in self.alternatives.values()]
            + [len(extra) + 1 for extra in self.additions.values()]
        )
        ran = set()
        index = 0
        # A command that is one of several alternatives is taken only on
        # some passes, so the walk goes on until every addition has run
        # on a pass that took its command, within a bound.
        while index < passes or (
            wanted - self.additions_ran and index < passes * 4
        ):
            ran.update(self.walk(lines, index))
            index += 1
        never = [
            "%d: %s" % (number, command)
            for number, command in lines
            if number not in ran
            and os.path.basename(shlex.split(command)[0]) in SCRIPTS
        ]
        self.assertEqual([], never, "a documented command was never run")
        never_added = [
            "%d: %s" % (number, span)
            for extra in self.additions.values()
            for number, span in extra
            if number not in self.additions_ran
        ]
        self.assertEqual(
            [], never_added, "an addition a sentence describes was never run"
        )

    def a_base_already_set_up(self, sandbox, state):
        """A base with a change recorded and a document behind it.

        Every skill but the one that sets a base up is run inside a base, so
        one is built here the way the other scenarios build one, with enough
        in it for the commands the skills print to have something to work on.
        """
        import test_first_draft_marker as first_draft
        import test_moment_of_use as moment_tests

        base = moment_tests.Base(sandbox)
        base.add_change()
        state["base"] = base.root
        state["cwd"] = base.root
        state["document"] = moment_tests.ICP
        # A first draft that says which part of the document it is about, so
        # that both shapes of the wording command the skills print can be run.
        state["staged"] = first_draft.a_first_draft(
            base.root, body=first_draft.NAMES_THE_PART
        )
        waiting = [line for line in base.review().review if line.question_id]
        state["question"] = waiting[0].question_id if waiting else None
        return base

    def walk(self, lines, index):
        ran = []
        with support.Sandbox() as sandbox:
            state = {
                "cwd": os.path.join(sandbox.path, "work"),
                "material": self.material(),
                "step": "icp",
            }
            os.makedirs(state["cwd"])
            if self.document_walked != "join/SKILL.md":
                self.a_base_already_set_up(sandbox, state)
            for line_number, command in lines:
                words = shlex.split(command)
                if os.path.basename(words[0]) not in SCRIPTS:
                    # Finding W2: this used to be passed over without a word,
                    # so a skill naming a script nobody knows was never run
                    # and nothing said so.
                    raise AssertionError(
                        "line %d names a script nobody knows: %s"
                        % (line_number, words[0])
                    )
                mode = words[1] if len(words) > 1 and not words[1].startswith("-") else ""
                if not self._taken_this_pass(words, command, index):
                    continue
                # One pass runs the command as it is printed, and each of the
                # others adds one of the things a sentence says to add to it.
                extra = (getattr(self, "additions", None) or {}).get(line_number) or []
                taken = getattr(self, "times_taken", None)
                if taken is None:
                    taken = self.times_taken = {}
                choice = taken.get(line_number, 0) % (len(extra) + 1)
                taken[line_number] = taken.get(line_number, 0) + 1
                if choice:
                    addition_line, addition = extra[choice - 1]
                    command = command + " " + addition
                    words = shlex.split(command)
                    self.additions_ran.add(addition_line)
                self.before(mode, state, command)
                filled = self.fill(command, state)
                finished = self.run_line(filled, state["cwd"])
                printed = finished.stdout.decode("utf-8")
                if mode in self.REFUSED_ON_PURPOSE:
                    self.assertNotEqual(
                        0, finished.returncode, "%d: %s" % (line_number, filled)
                    )
                    self.assertNotEqual(b"", finished.stdout)
                else:
                    self.assertEqual(
                        0,
                        finished.returncode,
                        "line %d was refused: %s\n%s\n%s"
                        % (
                            line_number,
                            filled,
                            printed,
                            finished.stderr.decode("utf-8"),
                        ),
                    )
                self.handed_out(state, filled, printed)
                self.after(mode, state, printed)
                if "--local-edit" in shlex.split(filled):
                    # The hand edit that story needed is put back, because the
                    # next story in the same skill is a different one and
                    # starts on a base with nothing half done in it.
                    support.git(
                        ["checkout", "HEAD", "--", state["document"]],
                        cwd=state["base"],
                    )
                if any(flag in shlex.split(filled) for flag in CONSUMES_WORDS):
                    # A words file is read once and taken away, so the next
                    # step has to ask for one of its own.
                    state.pop("words", None)
                    state.pop("words_kind", None)
                    for flag in shlex.split(filled):
                        kind = self.KIND_OF_FLAG.get(flag)
                        if kind is not None:
                            (state.get("handed") or {}).pop(kind, None)
                if mode in ("approve", "skip") and state.get("base"):
                    state["cwd"] = state["base"]
                    if state["step"] == "icp":
                        state["step"] = "positioning"
                ran.append(line_number)

        return ran



# --- F6 of the third look ----------------------------------------------------


class TestNoCommandCarriesAFolderNameEither(unittest.TestCase):
    """F6. Quotation marks are not a fix: a folder may be called anything.

    A folder called "Brandon's Docs" breaks a command that puts its name in
    quotation marks, and a folder whose name a document chose can do worse. So
    the folder somebody names travels in a file the way their other words do,
    and a folder chosen off a list is chosen by the number beside it.
    """

    # R9 added the three that were still left: the folder a base belongs
    # with, a folder to add to the places proposed, and a place to drop.
    BY_FILE_OR_NUMBER = (
        "--folder",
        "--only-folder",
        "--content-folder",
        "--add",
        "--drop",
    )
    NUMBERS = ("<number>", "<place number>")

    def test_no_documented_command_puts_a_folder_name_in_it(self):
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_with_prose(path):
                words = words_of(command)
                for index, word in enumerate(words):
                    if word.split("=")[0] not in self.BY_FILE_OR_NUMBER:
                        continue
                    value = words[index + 1] if index + 1 < len(words) else ""
                    two = " ".join(words[index + 1 : index + 3])
                    if "<" not in value or value in self.NUMBERS or two in self.NUMBERS:
                        # A number is not somebody else's text, so a command
                        # that takes one is a command anybody can type safely.
                        continue
                    problems.append(
                        "%s line %d puts %s on a command line"
                        % (os.path.basename(path), line_number, word)
                    )
        self.assertEqual([], problems)




class TestTheWalkCannotCoverForASkill(unittest.TestCase):
    """W1 and W2 of the confirmation round.

    The walk supplied a missing hand-out by itself, so a skill that stopped
    printing the command that hands out a file still passed, which is the one
    thing this whole test exists to catch. And a documented command for a
    script it does not know was skipped without a word.
    """

    def a_copy_without(self, relative, line):
        """One skill document, with a line taken out, in the scratch folder."""
        import tempfile

        source = os.path.join(SKILLS_DIR, relative.replace("/", os.sep))
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(line, text)
        folder = tempfile.mkdtemp(prefix="gtm-base-skill-")
        path = os.path.join(folder, "SKILL.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(line, ""))
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        return path

    def walk_of(self, path, relative):
        walk = TestTheSkillsAsTheyAreWritten(
            "test_every_documented_command_runs_as_it_is_written"
        )
        lines = commands_in(path)
        walk.document_walked = relative
        walk.alternatives = walk._alternatives(lines)
        return walk, lines

    def test_a_skill_that_stops_handing_out_a_file_fails(self):
        relative = "confirm/SKILL.md"
        path = self.a_copy_without(
            relative, "python3 scripts/confirm.py --new-words-file reason"
        )
        walk, lines = self.walk_of(path, relative)

        # Every pass, because the answer that needs their words is one of
        # three the skill offers and each pass takes one of them.
        raised = []
        for index in range(3):
            try:
                walk.walk(lines, index)
            except AssertionError as failure:
                raised.append(str(failure))

        self.assertTrue(raised, "the walk covered for the missing hand-out")
        self.assertTrue(
            any("path it printed" in message for message in raised), raised
        )

    def test_an_addition_named_in_a_sentence_is_run_and_can_fail(self):
        """R9. The optional additions a sentence names are run like the rest.

        This is the documented variant Astra found broken: the sentence said
        to narrow a draft with a folder by its name, which the script refuses.
        The walk ran only whole command lines, so it never ran this one.
        """
        relative = "join/SKILL.md"
        line = "`--only-folder <number>`, the number the list printed beside that folder,"
        path = self.a_copy_without(relative, line)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        # The copy is the old sentence, with a folder named by its name.
        source = os.path.join(SKILLS_DIR, "join", "SKILL.md")
        with open(source, encoding="utf-8") as handle:
            original = handle.read()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(original.replace(line, "`--only-folder <folder>`,"))
        del text
        walk = TestTheSkillsAsTheyAreWritten(
            "test_every_documented_command_runs_as_it_is_written"
        )

        with self.assertRaises(AssertionError) as caught:
            walk.walk_everything(path, relative)

        self.assertIn("--only-folder", str(caught.exception))

    def test_a_flag_a_sentence_names_must_be_one_the_script_knows(self):
        import tempfile

        folder = tempfile.mkdtemp(prefix="gtm-base-skill-")
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        path = os.path.join(folder, "SKILL.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "Run `python3 scripts/propose.py --staging <path to the staged file>`.\n"
                "Add `--invented-flag` when it helps.\n"
                "Their answer is passed as `--source`.\n"
            )

        found = prose_flags_in(path)

        self.assertEqual(
            ["--invented-flag", "--source"], [item[1] for item in found]
        )
        self.assertNotIn("--invented-flag", _actions_of("propose.py"))
        self.assertIn("--source", THEIR_OWN_WORDS)

    def test_a_command_for_a_script_nobody_knows_fails(self):
        import tempfile

        folder = tempfile.mkdtemp(prefix="gtm-base-skill-")
        self.addCleanup(__import__("shutil").rmtree, folder, True)
        path = os.path.join(folder, "SKILL.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Run `python3 scripts/invented.py --do-something`.\n")
        walk, lines = self.walk_of(path, "confirm/SKILL.md")

        with self.assertRaises(AssertionError) as caught:
            walk.walk(lines, 0)

        self.assertIn("invented.py", str(caught.exception))



if __name__ == "__main__":
    unittest.main()
