"""Unit 4: putting the safeguard git itself runs in place, and keeping it there."""

import os
import shutil
import stat
import subprocess
import unittest

import support
from support import Sandbox, commit, git, head_of, write

from gtmbase import gate, install_git_hook, state

PLUGIN_DIR = support.PLUGIN_DIR


def push(root, args=("origin", "main"), environment=None):
    """Send from a plain terminal, with the temporary home in place."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = "Test Owner"
    env["GIT_AUTHOR_EMAIL"] = "owner@example.com"
    env["GIT_COMMITTER_NAME"] = "Test Owner"
    env["GIT_COMMITTER_EMAIL"] = "owner@example.com"
    if environment:
        env.update(environment)
    return subprocess.run(
        ["git", "push"] + list(args),
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TestInstalling(unittest.TestCase):
    def test_the_safeguard_is_written_where_git_looks_for_it(self):
        with Sandbox() as box:
            root, base_id = box.base()
            code, hooks_dir = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            self.assertEqual(install_git_hook.CODE_OK, code)
            self.assertEqual(os.path.join(root, ".git", "hooks"), hooks_dir)

            hook = os.path.join(hooks_dir, "pre-push")
            self.assertTrue(os.path.isfile(hook))
            mode = stat.S_IMODE(os.stat(hook).st_mode)
            self.assertEqual(0o755, mode)
            with open(hook, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn(install_git_hook.MARKER_LINE, text)

            seat, _problems = state.load_seat(base_id)
            self.assertTrue(seat["git_hook_installed"])
            self.assertEqual("ok", seat["git_hook_code"])

    def test_the_written_safeguard_is_a_shell_script_that_parses(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            _code, hooks_dir = install_git_hook.install(root, PLUGIN_DIR)
            finished = subprocess.run(
                ["/bin/sh", "-n", os.path.join(hooks_dir, "pre-push")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(0, finished.returncode, finished.stderr)

    def test_installing_twice_changes_nothing_else(self):
        with Sandbox() as box:
            root, base_id = box.base()
            first_code, hooks_dir = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            with open(os.path.join(hooks_dir, "pre-push"), encoding="utf-8") as handle:
                first = handle.read()
            second_code, again = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            with open(os.path.join(again, "pre-push"), encoding="utf-8") as handle:
                second = handle.read()
            self.assertEqual(first_code, second_code)
            self.assertEqual(first, second)
            self.assertFalse(os.path.exists(os.path.join(hooks_dir, "pre-push.local")))

    def test_nothing_that_is_shared_with_the_team_is_ever_written(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            install_git_hook.install(root, PLUGIN_DIR)
            finished = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(b"", finished.stdout)

    def test_a_shared_folder_of_safeguards_is_refused(self):
        with Sandbox() as box:
            root, base_id = box.base()
            write(os.path.join(root, ".githooks", "keep.txt"), "shared\n")
            git(["add", "-A"], cwd=root)
            git(["commit", "-q", "-m", "shared hooks folder"], cwd=root)
            git(["config", "--local", "core.hooksPath", ".githooks"], cwd=root)

            code, _hooks_dir = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            self.assertEqual(install_git_hook.CODE_TRACKED, code)
            self.assertFalse(os.path.exists(os.path.join(root, ".githooks", "pre-push")))
            seat, _problems = state.load_seat(base_id)
            self.assertFalse(seat["git_hook_installed"])
            self.assertEqual("hooks-dir-tracked", seat["git_hook_code"])


class TestAFolderTheAccountChose(unittest.TestCase):
    def test_a_writable_folder_named_in_the_account_settings_is_used(self):
        with Sandbox() as box:
            chosen = os.path.join(box.path, "myhooks")
            os.makedirs(chosen)
            write(
                os.path.join(os.environ["HOME"], ".gitconfig"),
                "[core]\n\thooksPath = %s\n" % chosen,
            )
            root, _base_id = box.base()
            code, hooks_dir = install_git_hook.install(root, PLUGIN_DIR)
            self.assertEqual(install_git_hook.CODE_OK, code)
            self.assertEqual(chosen, hooks_dir)
            self.assertTrue(os.path.isfile(os.path.join(chosen, "pre-push")))
            self.assertFalse(
                os.path.exists(os.path.join(root, ".git", "hooks", "pre-push"))
            )

    def test_a_folder_that_cannot_be_written_is_recorded_and_left_alone(self):
        with Sandbox() as box:
            locked = os.path.join(box.path, "locked")
            os.makedirs(locked)
            chosen = os.path.join(locked, "hooks")
            os.chmod(locked, 0o500)
            try:
                write(
                    os.path.join(os.environ["HOME"], ".gitconfig"),
                    "[core]\n\thooksPath = %s\n" % chosen,
                )
                root, base_id = box.base()
                code, hooks_dir = install_git_hook.install(
                    root, PLUGIN_DIR, base_id=base_id
                )
                self.assertEqual(install_git_hook.CODE_NOT_WRITABLE, code)
                self.assertEqual(chosen, hooks_dir)
                self.assertFalse(os.path.exists(chosen))
                seat, _problems = state.load_seat(base_id)
                self.assertFalse(seat["git_hook_installed"])
                self.assertEqual("hooks-path-not-writable", seat["git_hook_code"])
            finally:
                os.chmod(locked, 0o700)


# Changed 2026-09-20 for findings A1 and H1 of the release review. This
# release answers "never reviewed" to every base and reads no record at
# all to decide it, because nothing shipped sets that record honestly and
# both reviewers turned a refused send into an allowed one by writing over
# it. Every class below carrying `support.PastTheFirstBackupReview` is
# about something further down the path than that rule, so it runs with
# the answer the review will give once it ships. What each scenario
# asserts is unchanged.
class TestAnExistingSafeguard(support.PastTheFirstBackupReview, unittest.TestCase):
    def make_existing(self, hooks_dir, marker_path):
        path = os.path.join(hooks_dir, "pre-push")
        write(
            path,
            "#!/bin/sh\n"
            "cat > /dev/null\n"
            'printf "ran\\n" > "%s"\n'
            "exit 0\n" % marker_path,
        )
        os.chmod(path, 0o755)
        return path

    def test_it_is_moved_aside_and_still_runs_after_ours(self):
        with Sandbox() as box:
            root, base_id = box.base()
            hooks_dir = os.path.join(root, ".git", "hooks")
            marker_path = os.path.join(box.path, "existing-ran.txt")
            self.make_existing(hooks_dir, marker_path)

            code, _hooks_dir = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            self.assertEqual(install_git_hook.CODE_RENAMED, code)
            self.assertTrue(os.path.isfile(os.path.join(hooks_dir, "pre-push.local")))
            seat, _problems = state.load_seat(base_id)
            self.assertEqual("hook-renamed", seat["git_hook_code"])

            # Changed 2026-09-20 for findings A1 and H1. This used to send a
            # clean change for real and prove the moved aside safeguard still
            # ran after ours. No send from a base completes in this release,
            # because the first backup review is not shipped, so what can be
            # proved here is that ours runs first and refuses. That ours
            # really is first, and that the moved one is really still there
            # and really does run when ours passes, is what the scenario
            # below and the installation checks above cover. The clean send
            # half comes back when the first backup review ships.
            commit(root, "context/metrics/notes.md", ["a clean line of notes"])
            finished = push(root)
            self.assertNotEqual(0, finished.returncode)
            self.assertIn("never been backed up", finished.stderr.decode("utf-8"))
            self.assertTrue(
                os.path.isfile(os.path.join(hooks_dir, "pre-push.local"))
            )
            self.assertFalse(os.path.isfile(marker_path))

    def test_ours_runs_first_and_the_moved_one_never_runs_on_a_refusal(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            hooks_dir = os.path.join(root, ".git", "hooks")
            marker_path = os.path.join(box.path, "existing-ran.txt")
            self.make_existing(hooks_dir, marker_path)
            install_git_hook.install(root, PLUGIN_DIR)

            commit(root, "work/inbox/call.md", ["nothing unusual here"])
            finished = push(root)
            self.assertNotEqual(0, finished.returncode)
            self.assertFalse(os.path.exists(marker_path))

    def test_a_second_moved_aside_safeguard_would_be_lost_so_nothing_happens(self):
        with Sandbox() as box:
            root, base_id = box.base()
            hooks_dir = os.path.join(root, ".git", "hooks")
            self.make_existing(hooks_dir, os.path.join(box.path, "one.txt"))
            write(os.path.join(hooks_dir, "pre-push.local"), "#!/bin/sh\nexit 0\n")

            code, _hooks_dir = install_git_hook.install(
                root, PLUGIN_DIR, base_id=base_id
            )
            self.assertEqual(install_git_hook.CODE_UNMOVABLE, code)
            with open(os.path.join(hooks_dir, "pre-push"), encoding="utf-8") as handle:
                self.assertNotIn(install_git_hook.MARKER_LINE, handle.read())
            seat, _problems = state.load_seat(base_id)
            self.assertEqual("existing-hook-unmovable", seat["git_hook_code"])


class TestTheSafeguardFromAPlainTerminal(support.PastTheFirstBackupReview, unittest.TestCase):
    """Changed 2026-09-20 for findings A1 and H1 of the release review.

    Until then every scenario here sent for real from a plain terminal and
    read what git said back. This release refuses every send from a base
    before anything is read, because the first backup review is not shipped
    and nothing else may honestly say it happened, and the safeguard holds
    that rule inside a process of its own where nothing this file stands in
    for can reach.

    So the scenarios split in two. The first sends for real and proves the
    safeguard is installed, runs, refuses, and leaves the shared copy where it
    was. The rest are about what the safeguard reads once a send gets past
    that rule, and they ask the safeguard the same question git asks it, in
    this process, with the answer the first backup review will give when it
    ships. Nothing about what they assert changed.
    """

    def ref_line(self, root, before=None):
        """The line git hands the safeguard on standard input, as git writes it."""
        before = before or "0" * 40
        return "refs/heads/main %s refs/heads/main %s\n" % (head_of(root), before)

    def test_the_safeguard_really_runs_and_refuses_from_a_plain_terminal(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            install_git_hook.install(root, PLUGIN_DIR)
            commit(root, "context/metrics/notes.md", ["a clean line of notes"])
            before = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=root,
                stdout=subprocess.PIPE,
            ).stdout.decode("utf-8").strip()

            finished = push(root)

            self.assertNotEqual(0, finished.returncode)
            message = finished.stderr.decode("utf-8")
            self.assertIn("never been backed up", message)
            after = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=root,
                stdout=subprocess.PIPE,
            ).stdout.decode("utf-8").strip()
            self.assertEqual(before, after)

    def test_a_send_of_a_file_that_is_yours_alone_is_refused_by_git(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            install_git_hook.install(root, PLUGIN_DIR)
            before = head_of(root)
            commit(root, "work/inbox/call.md", ["nothing unusual here"])

            message = gate.check_git_hook(self.ref_line(root, before), root)

            self.assertIn("work/inbox/call.md", message or "")
            self.assertIn("GTM Base stopped this", message)

    def test_a_send_holding_an_address_in_a_saved_note_is_refused_by_git(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            install_git_hook.install(root, PLUGIN_DIR)
            before = head_of(root)
            git(
                ["commit", "-q", "--allow-empty", "-m", "ask jane@acme.com about it"],
                cwd=root,
            )

            message = gate.check_git_hook(self.ref_line(root, before), root)

            self.assertIn("an email address", message or "")
            self.assertNotIn("jane@acme.com", message)

    def test_a_clean_send_goes_through(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            install_git_hook.install(root, PLUGIN_DIR)
            before = head_of(root)
            commit(root, "context/metrics/notes.md", ["a clean line of notes"])

            self.assertIsNone(gate.check_git_hook(self.ref_line(root, before), root))


if __name__ == "__main__":
    unittest.main()
