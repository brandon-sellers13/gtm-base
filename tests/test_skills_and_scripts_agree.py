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

# One documented command per script that is actually run, with the placeholders
# filled in, so that a command nobody has ever run cannot ship again.
import subprocess  # noqa: E402
import sys  # noqa: E402


class TestEveryCommandThatNamesAFileSaysWhichRunItIsFor(unittest.TestCase):
    """H3. The company step was refused every time for want of the run."""

    def test_no_documented_command_leaves_the_key_out(self):
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_in(path):
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


class TestTheWholeJoinSkillAsItIsWritten(unittest.TestCase):
    """H3. Every command the join skill prints, run in order, in a sandbox.

    Parsing a command proves it would be accepted. It does not prove it would
    do anything, and the company step was refused every single time while
    every test supplied an argument the skill does not print.
    """

    SCRIPT = SCRIPTS["join.py"]

    def run_join(self, arguments, cwd):
        return subprocess.run(
            [sys.executable, self.SCRIPT] + [str(item) for item in arguments],
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

    def done(self, finished, what):
        printed = finished.stdout.decode("utf-8")
        self.assertEqual(
            0,
            finished.returncode,
            "%s was refused: %s %s"
            % (what, printed, finished.stderr.decode("utf-8")),
        )
        return printed

    def words_file(self, cwd, run_id, kind, text):
        """Ask the skill for somewhere to put words, exactly as it says to."""
        printed = self.done(
            self.run_join(
                ["words-file", "--run", run_id, "--for", kind], cwd
            ),
            "words-file --for " + kind,
        )
        path = self.value_of(printed, "words")
        self.assertTrue(path, printed)
        support.write(path, text)
        return path

    def test_the_steps_the_skill_prints_all_run(self):
        with support.Sandbox() as sandbox:
            home = os.environ["HOME"]
            support.write(
                os.path.join(home, ".gitconfig"),
                "[user]\n\temail = dana@acme.test\n\tname = Dana\n",
            )
            material = os.path.join(home, "marketing")
            support.write(
                os.path.join(material, "acme-icp.md"),
                "# Who we sell to\n\nSmall teams selling to other businesses.\n",
            )
            support.write(
                os.path.join(material, "pricing-notes.txt"),
                "We lead with the monthly number now.\n",
            )
            work = os.path.join(sandbox.path, "work")
            os.makedirs(work)

            # Step 1. The run.
            printed = self.done(self.run_join(["new-run"], work), "new-run")
            run_id = self.value_of(printed, "run")
            self.assertTrue(run_id, printed)

            # Step 4. The company name, and where the base will go.
            company = self.words_file(work, run_id, "company", "Acme")
            printed = self.done(
                self.run_join(
                    ["propose-location", "--company-file", company,
                     "--run", run_id],
                    work,
                ),
                "propose-location",
            )
            parent = self.value_of(printed, "parent")
            self.assertTrue(parent, printed)

            # Step 5. What would be read, and the yes that fixes it.
            self.done(
                self.run_join(
                    ["survey", "--folder", material, "--run", run_id], work
                ),
                "survey",
            )
            printed = self.done(
                self.run_join(
                    ["list-sources", "--folder", material, "--run", run_id],
                    work,
                ),
                "list-sources",
            )
            self.assertIn("read=", printed)
            self.done(
                self.run_join(
                    ["freeze-sources", "--folder", material,
                     "--session", "sess-1", "--run", run_id],
                    work,
                ),
                "freeze-sources",
            )

            # Step 5, the pasted piece, with its label in a file.
            pasted = os.path.join(sandbox.path, "pasted.txt")
            support.write(pasted, "We win on setup time.\n")
            label = self.words_file(work, run_id, "label", "a note from the call")
            self.done(
                self.run_join(
                    ["add-paste", "--run", run_id, "--label-file", label,
                     "--session", "sess-1", "--from", pasted],
                    work,
                ),
                "add-paste",
            )

            # Step 6, for each drafted document in turn.
            root = None
            for step in ("icp", "positioning"):
                self.done(
                    self.run_join(
                        ["preview", "--step", step, "--run", run_id], work
                    ),
                    "preview " + step,
                )
                company = self.words_file(work, run_id, "company", "Acme")
                printed = self.done(
                    self.run_join(
                        ["assemble", "--step", step, "--run", run_id,
                         "--company-file", company,
                         "--email", "dana@acme.test"],
                        work,
                    ),
                    "assemble " + step,
                )
                draft = self.value_of(printed, "draft")
                self.assertTrue(draft, printed)
                support.write(draft, a_draft_for(step))

                # Step 7, the check before it is shown.
                printed = self.done(
                    self.run_join(
                        ["review", "--step", step, "--run", run_id,
                         "--draft", draft],
                        work,
                    ),
                    "review " + step,
                )
                self.assertIn("ready", printed)

                # Step 7, what is wrong with this.
                answer = self.words_file(
                    work, run_id, "answer", "The wording is too formal."
                )
                self.done(
                    self.run_join(
                        ["what-is-wrong", "--step", step, "--run", run_id,
                         "--answer-file", answer],
                        work,
                    ),
                    "what-is-wrong " + step,
                )

                # Step 7, approve the first document, which is what makes the
                # base, and skip the second, which is the other answer the
                # skill offers from the second document onward.
                if root is None:
                    company = self.words_file(work, run_id, "company", "Acme")
                    printed = self.done(
                        self.run_join(
                            ["approve", "--step", step, "--draft", draft,
                             "--run", run_id, "--parent", parent,
                             "--company-file", company],
                            work,
                        ),
                        "approve " + step,
                    )
                    root = self.value_of(printed, "base")
                    self.assertTrue(root, printed)
                else:
                    self.done(
                        self.run_join(
                            ["skip", "--step", step, "--base", root], root
                        ),
                        "skip " + step,
                    )

            # Step 8, the closing question and the change it leads to.
            self.done(self.run_join(["closing-question"], root), "closing-question")
            printed = self.done(
                self.run_join(
                    ["assemble", "--step", "change-entry", "--run", run_id,
                     "--company-file",
                     self.words_file(work, run_id, "company", "Acme"),
                     "--email", "dana@acme.test"],
                    root,
                ),
                "assemble change-entry",
            )
            change_draft_path = self.value_of(printed, "draft")
            support.write(change_draft_path, a_draft_for("change-entry"))
            self.done(
                self.run_join(
                    ["preview-change", "--draft", change_draft_path,
                     "--run", run_id, "--base", root],
                    root,
                ),
                "preview-change",
            )
            printed = self.done(
                self.run_join(
                    ["approve", "--step", "change-entry",
                     "--draft", change_draft_path, "--run", run_id,
                     "--base", root],
                    root,
                ),
                "approve change-entry",
            )
            change_id = self.value_of(printed, "change")
            self.assertTrue(change_id, printed)

            # Step 9, one question per document.
            printed = self.done(
                self.run_join(
                    ["reconcile", "--base", root, "--entry", change_id], root
                ),
                "reconcile",
            )
            asked = self.value_of(printed, "file")
            self.assertTrue(asked, printed)
            self.done(
                self.run_join(
                    ["reconcile-answer", "--base", root, "--entry", change_id,
                     "--file", asked, "--answer", "yes"],
                    root,
                ),
                "reconcile-answer",
            )

            # Step 10, the closing, with what got in the way.
            got = self.words_file(
                work, run_id, "got-in-the-way", "The folder took a while to find."
            )
            self.done(
                self.run_join(
                    ["close", "--base", root, "--run", run_id,
                     "--got-in-the-way-file", got],
                    root,
                ),
                "close",
            )

            # The folder commands, and the two that are refused on purpose.
            self.done(
                self.run_join(
                    ["link", "--base", root, "--folder", material], root
                ),
                "link",
            )
            self.done(self.run_join(["links"], root), "links")
            self.done(self.run_join(["unlink", "--base", root], root), "unlink")
            for mode in ("backup", "invite", "join-link"):
                finished = self.run_join([mode], root)
                self.assertEqual(1, finished.returncode, mode)
                self.assertNotEqual(b"", finished.stdout, mode)


def a_draft_for(step):
    """A draft of the shape each step's request asks for."""
    import test_join_setup_flow as flow

    if step == "change-entry":
        return flow.change_draft()
    return flow.captured("icp.md" if step == "icp" else "positioning.md")




# --- F6 of the third look ----------------------------------------------------


class TestNoCommandCarriesAFolderNameEither(unittest.TestCase):
    """F6. Quotation marks are not a fix: a folder may be called anything.

    A folder called "Brandon's Docs" breaks a command that puts its name in
    quotation marks, and a folder whose name a document chose can do worse. So
    the folder somebody names travels in a file the way their other words do,
    and a folder chosen off a list is chosen by the number beside it.
    """

    BY_FILE_OR_NUMBER = ("--folder", "--only-folder")

    def test_no_documented_command_puts_a_folder_name_in_it(self):
        problems = []
        for path in every_skill_file():
            for line_number, command in commands_in(path):
                words = words_of(command)
                for index, word in enumerate(words):
                    if word.split("=")[0] not in self.BY_FILE_OR_NUMBER:
                        continue
                    value = words[index + 1] if index + 1 < len(words) else ""
                    if "<" not in value or value == "<number>":
                        # A number is not somebody else's text, so a command
                        # that takes one is a command anybody can type safely.
                        continue
                    problems.append(
                        "%s line %d puts %s on a command line"
                        % (os.path.basename(path), line_number, word)
                    )
        self.assertEqual([], problems)



if __name__ == "__main__":
    unittest.main()
