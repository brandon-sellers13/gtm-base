"""Where a person's own words are allowed to reach a script from.

Finding V6 of the 2026-09-20 verification round, and N9 beside it. Every flag
that read somebody's words out of a file read any file on this computer, so a
document could have somebody's private notes read into their base and written
down with nobody asked. The scripts hand out the path now, and a path they did
not hand out is refused.

Every scenario here runs the real script in another process, because the
library was the only thing ever tested and that is how the gap stayed open.
"""

import os
import subprocess
import sys
import unittest

import support

from gtmbase import constants, ids, machine, state, wordsfile

JOIN = os.path.join(support.PLUGIN_DIR, "skills", "join", "scripts", "join.py")
PROPOSE = os.path.join(
    support.PLUGIN_DIR, "skills", "propose-change", "scripts", "propose.py"
)
CONFIRM = os.path.join(
    support.PLUGIN_DIR, "skills", "confirm", "scripts", "confirm.py"
)
OWNER = "owner@example.com"
PRIVATE = "The board pack says we are running out of money in March."


def script(path, arguments, cwd):
    return subprocess.run(
        [sys.executable, path] + [str(item) for item in arguments],
        cwd=support.where_a_script_runs(cwd),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def value_of(output, name):
    """One name and value line out of what a script printed."""
    for line in output.split("\n"):
        if line.startswith(name + "="):
            value = line[len(name) + 1 :]
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            return value
    return None


def a_private_file(sandbox, text=PRIVATE):
    """A document of the person's own that no step ever agreed to read."""
    return support.write(os.path.join(sandbox.path, "private-notes.txt"), text)


def local_base(sandbox, name="local"):
    root = os.path.join(sandbox.path, name)
    base_id = ids.base_id_random()
    support.make_base(root, base_id=base_id)
    support.write(os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n")
    support.write(
        os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n%s\n" % OWNER
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a local base"], cwd=root)
    machine.append_joined(root=root, base_id=base_id, remote=None)
    state.update_seat(base_id, first_push_reviewed=True, session_id="sess-1")
    return root, base_id


class TestAPathTheScriptsDidNotHandOut(unittest.TestCase):
    def test_the_setup_answer_flag_refuses_a_document_of_their_own(self):
        with support.Sandbox() as sandbox:
            mine = a_private_file(sandbox)
            run_id = ids.run_id()

            done = script(
                JOIN,
                [
                    "what-is-wrong",
                    "--step",
                    "icp",
                    "--run",
                    run_id,
                    "--answer-file",
                    mine,
                ],
                sandbox.path,
            )

            whole = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
            self.assertNotEqual(0, done.returncode)
            self.assertIn(wordsfile.NOT_OURS, whole)
            self.assertNotIn("running out of money", whole)
            self.assertTrue(os.path.isfile(mine))

    def test_the_closing_flag_refuses_a_document_of_their_own(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            mine = a_private_file(sandbox)
            run_id = ids.run_id()

            done = script(
                JOIN,
                [
                    "close",
                    "--run",
                    run_id,
                    "--base",
                    root,
                    "--got-in-the-way-file",
                    mine,
                ],
                root,
            )

            whole = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
            self.assertIn(wordsfile.NOT_OURS, whole)
            self.assertNotIn("running out of money", whole)
            self.assertTrue(os.path.isfile(mine))

    def test_the_proposal_flags_refuse_a_document_of_their_own(self):
        for flag in ("--source-file", "--what-changed-file"):
            with support.Sandbox() as sandbox:
                root, _base_id = local_base(sandbox)
                mine = a_private_file(sandbox)
                arguments = ["--local-edit", flag, mine]
                if flag != "--source-file":
                    # The source is asked for first, so it has to be a real one
                    # for the second flag to be the thing that is refused.
                    handed = script(PROPOSE, ["--new-words-file", "source"], root)
                    ours = value_of(handed.stdout.decode("utf-8"), "words")
                    support.write(ours, "The deck said so.")
                    arguments += ["--source-file", ours]

                done = script(PROPOSE, arguments, root)

                whole = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
                self.assertIn(wordsfile.NOT_OURS, whole, flag)
                self.assertNotIn("running out of money", whole)
                self.assertTrue(os.path.isfile(mine))

    def test_the_confirmation_flag_refuses_a_document_of_their_own(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            mine = a_private_file(sandbox)

            done = script(
                CONFIRM,
                [
                    "--question",
                    "q-" + "a" * 16,
                    "--answer",
                    "no",
                    "--reason-file",
                    mine,
                ],
                root,
            )

            whole = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
            self.assertIn(wordsfile.NOT_OURS, whole)
            self.assertNotIn("running out of money", whole)
            self.assertTrue(os.path.isfile(mine))


class TestThePathTheScriptsDoHandOut(unittest.TestCase):
    def test_the_setup_script_hands_one_out_and_reads_it_back(self):
        with support.Sandbox() as sandbox:
            run_id = ids.run_id()

            handed = script(
                JOIN,
                ["words-file", "--run", run_id, "--for", "answer"],
                sandbox.path,
            )
            self.assertEqual(0, handed.returncode, handed.stderr)
            path = value_of(handed.stdout.decode("utf-8"), "words")
            self.assertTrue(path)
            support.write(path, "The wording is too formal for us.")

            done = script(
                JOIN,
                [
                    "what-is-wrong",
                    "--step",
                    "icp",
                    "--run",
                    run_id,
                    "--answer-file",
                    path,
                ],
                sandbox.path,
            )

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertIn("too formal", done.stdout.decode("utf-8"))
            self.assertFalse(
                os.path.exists(path), "their words were left sitting on the disk"
            )

    def test_the_proposal_script_hands_one_out(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)

            handed = script(PROPOSE, ["--new-words-file", "source"], root)

            self.assertEqual(0, handed.returncode, handed.stderr)
            path = value_of(handed.stdout.decode("utf-8"), "words")
            self.assertTrue(path)
            self.assertTrue(os.path.isdir(os.path.dirname(path)))

    def test_the_confirmation_script_hands_one_out(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)

            handed = script(CONFIRM, ["--new-words-file", "reason"], root)

            self.assertEqual(0, handed.returncode, handed.stderr)
            path = value_of(handed.stdout.decode("utf-8"), "words")
            self.assertTrue(path)


class TestTheFolderItself(unittest.TestCase):
    def test_a_link_standing_in_the_folders_place_is_refused(self):
        with support.Sandbox() as sandbox:
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere)
            path = os.path.join(sandbox.path, "a-link")
            os.symlink(elsewhere, path)

            with self.assertRaises(Exception):
                wordsfile.private_dir(path)

    def test_a_words_file_that_is_a_link_is_refused(self):
        with support.Sandbox() as sandbox:
            run_id = ids.run_id()
            handed = wordsfile.new_words_path(run_id, "answer")
            mine = a_private_file(sandbox)
            os.symlink(mine, handed)

            self.assertIsNone(wordsfile.read_words(handed, run_id))

    def test_a_words_file_with_a_second_name_is_refused(self):
        with support.Sandbox() as sandbox:
            run_id = ids.run_id()
            handed = wordsfile.new_words_path(run_id, "answer")
            support.write(handed, "their words")
            os.link(handed, os.path.join(sandbox.path, "second-name"))

            self.assertIsNone(wordsfile.read_words(handed, run_id))

    def test_a_words_file_larger_than_an_answer_is_refused(self):
        with support.Sandbox():
            run_id = ids.run_id()
            handed = wordsfile.new_words_path(run_id, "answer")
            support.write(handed, "x" * (wordsfile.MAX_WORDS_BYTES + 1))

            self.assertIsNone(wordsfile.read_words(handed, run_id))

    def test_one_run_cannot_read_another_runs_words(self):
        with support.Sandbox():
            mine = ids.run_id()
            handed = wordsfile.new_words_path(mine, "answer")
            support.write(handed, "their words")
            other = ids.run_id()
            while other == mine:
                other = ids.run_id()

            self.assertIsNone(wordsfile.read_words(handed, other))
            self.assertEqual("their words", wordsfile.read_words(handed, mine))

    def test_a_taken_parent_folder_is_not_used(self):
        """N9. On a shared computer somebody else can get there first."""
        import tempfile

        with support.Sandbox():
            taken = os.path.join(
                tempfile.gettempdir(),
                "%s-%d" % (wordsfile.PARENT_NAME, os.getuid()),
            )
            os.makedirs(taken, 0o777)
            os.chmod(taken, 0o777)

            chosen = wordsfile.parent_dir()

            self.assertNotEqual(os.path.realpath(taken), os.path.realpath(chosen))
            self.assertEqual(0, os.lstat(chosen).st_mode & 0o077)


class TestTheDraftFileToo(unittest.TestCase):
    """N9. A draft is read from the folder the run named, and nowhere else."""

    def test_a_draft_from_anywhere_else_is_refused(self):
        with support.Sandbox() as sandbox:
            mine = a_private_file(sandbox)
            run_id = ids.run_id()

            done = script(
                JOIN,
                ["review", "--step", "icp", "--run", run_id, "--draft", mine],
                sandbox.path,
            )

            whole = done.stdout.decode("utf-8") + done.stderr.decode("utf-8")
            self.assertIn(wordsfile.NOT_A_DRAFT, whole)
            self.assertNotIn("running out of money", whole)


class TestSweepingUp(unittest.TestCase):
    def test_a_folder_whose_run_is_gone_is_swept(self):
        from gtmbase import join_flow

        with support.Sandbox():
            run_id = join_flow.new_run()
            folder = join_flow.drafts_dir(run_id)
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")
            join_flow.clear_scratch(run_id)
            # Put it back, the way a run that stopped part way leaves it.
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")

            join_flow.sweep_drafts_without_a_run()

            self.assertFalse(os.path.isdir(folder))


if __name__ == "__main__":
    unittest.main()
