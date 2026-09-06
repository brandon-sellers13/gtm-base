"""The working folders where work is prepared, away from the person's folder."""

import os
import subprocess
import unittest

import support  # noqa: F401  (puts the library on the import path)

from gtmbase import constants, paths, worktree
from gtmbase.gitcmd import GitRunner


HEAD_ID = ["rev-parse", "HEAD"]


def head_of(path):
    finished = subprocess.run(
        ["git"] + HEAD_ID, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


def branch_of(path):
    finished = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return finished.stdout.decode("utf-8").strip()


STAGING = "stg-00000000000000aa"


class TestMakingAWorkingFolder(unittest.TestCase):
    def test_a_folder_is_made_on_its_own_line_of_work_from_the_shared_branch(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            before_head = head_of(root)
            made = worktree.ensure_worktree(root, base_id, STAGING, "main", GitRunner())

            self.assertTrue(os.path.isdir(made.path))
            self.assertEqual(constants.PROPOSAL_BRANCH_PREFIX + STAGING, made.branch)
            self.assertEqual(made.branch, branch_of(made.path))
            self.assertEqual("origin/main", made.start_point)
            self.assertIn(worktree.CODE_CREATED, made.codes)
            self.assertTrue(
                made.path.startswith(paths.worktrees_dir(base_id)),
                made.path,
            )

            self.assertEqual(before_head, head_of(root))
            self.assertEqual("main", branch_of(root))
            self.assertEqual("", self._status(root))

    def test_a_folder_that_is_already_there_is_used_as_it_stands(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            git = GitRunner()
            first = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            support.write(os.path.join(first.path, "context", "notes.md"), "kept\n")

            again = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            self.assertEqual(first.path, again.path)
            self.assertIn(worktree.CODE_REUSED, again.codes)
            self.assertTrue(os.path.isfile(os.path.join(again.path, "context", "notes.md")))

    def test_a_folder_left_on_no_line_of_work_is_put_back_on_its_own(self):
        """A run that stopped halfway can leave the folder with no name on it.

        Work saved there has nothing to send, so the folder is put back on the
        line of work this proposal belongs to before it is handed on, and the
        work that was already saved there is kept.
        """
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            git = GitRunner()
            first = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            support.write(os.path.join(first.path, "context", "notes.md"), "kept\n")
            support.git(["add", "-A"], cwd=first.path)
            support.git(["commit", "-q", "-m", "work saved halfway"], cwd=first.path)
            saved = head_of(first.path)
            support.git(["checkout", "-q", "--detach", "HEAD"], cwd=first.path)
            self.assertEqual("HEAD", branch_of(first.path))

            again = worktree.ensure_worktree(root, base_id, STAGING, "main", git)

            self.assertEqual(first.path, again.path)
            self.assertEqual(constants.PROPOSAL_BRANCH_PREFIX + STAGING, again.branch)
            self.assertEqual(again.branch, branch_of(again.path))
            self.assertEqual(saved, head_of(again.path))
            self.assertIn(worktree.CODE_REBRANCHED, again.codes)

    def test_a_folder_git_no_longer_knows_about_is_made_again(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            git = GitRunner()
            first = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            support.git(["worktree", "remove", "--force", first.path], cwd=root)
            os.makedirs(first.path)

            again = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            self.assertIn(worktree.CODE_REPLACED, again.codes)
            self.assertIn(worktree.CODE_CREATED, again.codes)
            self.assertTrue(worktree.worktree_exists(root, again.path, runner=git))

    def test_a_base_with_no_shared_copy_starts_from_its_own_branch(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "alone")
            support.make_base(root, base_id=None)
            base_id = "a" * 32
            made = worktree.ensure_worktree(root, base_id, STAGING, "main", GitRunner())
            self.assertEqual("main", made.start_point)
            self.assertIn(worktree.CODE_NO_REMOTE, made.codes)

    def test_a_shared_copy_that_cannot_be_reached_is_recorded_and_the_run_goes_on(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            support.git(["remote", "set-url", "origin", os.path.join(sandbox.path, "gone")], cwd=root)
            made = worktree.ensure_worktree(root, base_id, STAGING, "main", GitRunner())
            self.assertIn(worktree.CODE_FETCH_FAILED, made.codes)
            self.assertTrue(os.path.isdir(made.path))

    def _status(self, root):
        finished = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return finished.stdout.decode("utf-8").strip()


class TestTakingAWorkingFolderAway(unittest.TestCase):
    def test_a_folder_is_taken_away_and_forgotten(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            git = GitRunner()
            made = worktree.ensure_worktree(root, base_id, STAGING, "main", git)
            self.assertIn(os.path.realpath(made.path), worktree.list_worktrees(root))

            worktree.remove_worktree(root, made.path, runner=git)
            self.assertFalse(os.path.isdir(made.path))
            self.assertNotIn(os.path.realpath(made.path), worktree.list_worktrees(root))
            self.assertFalse(worktree.worktree_exists(root, made.path, runner=git))

    def test_taking_away_a_folder_that_is_not_there_says_so_and_does_no_harm(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            missing = os.path.join(paths.worktrees_dir(base_id), "never-made")
            self.assertFalse(worktree.remove_worktree(root, missing, runner=GitRunner()))


class TestTheConfirmationsFolder(unittest.TestCase):
    def test_it_sits_beside_the_others_on_a_line_of_work_named_for_this_seat(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            git = GitRunner()
            made = worktree.ensure_confirmations_worktree(root, base_id, "main", git)
            self.assertTrue(
                made.branch.startswith(constants.CONFIRMATIONS_BRANCH_PREFIX), made.branch
            )
            self.assertEqual(
                os.path.join(paths.worktrees_dir(base_id), "confirmations"), made.path
            )
            self.assertEqual(made.branch, branch_of(made.path))

            again = worktree.ensure_confirmations_worktree(root, base_id, "main", git)
            self.assertIn(worktree.CODE_REUSED, again.codes)

    def test_the_short_name_of_a_seat_holds_no_address(self):
        with support.Sandbox() as sandbox:
            root, base_id = sandbox.base()
            short = worktree.seat_short_id(root, base_id, runner=GitRunner())
            self.assertEqual(12, len(short))
            self.assertNotIn("@", short)


if __name__ == "__main__":
    unittest.main()
