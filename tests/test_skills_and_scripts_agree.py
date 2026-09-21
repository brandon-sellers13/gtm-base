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
            for line_number, command in commands_in(path):
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

    def test_no_command_carries_words_somebody_else_wrote(self):
        """A fixed word such as yes is fine. Anything to be filled in is not."""
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_in(path):
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
            for line_number, command in commands_in(path):
                words = words_of(command)
                if "--draft" not in words:
                    continue
                if "--run" not in words:
                    problems.append(
                        "%s line %d reads a draft without saying which run"
                        % (os.path.basename(path), line_number)
                    )
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
