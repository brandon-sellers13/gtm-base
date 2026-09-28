"""0.3.3: no save the plugin makes runs anything the base names to run.

Astra's review of 0.3.3, finding 1 (critical). A base is a folder of somebody's
files, and git runs programs a folder can name. A `post-commit` hook in a base
with no shared copy uploaded its private files the moment the owner approved a
local save, and no outgoing-content check ever saw it, because nothing was
sent through a command the plugin reads. The fix is one helper in the one
runner every git call goes through (`gitcmd.hook_free` and
`gitcmd.executable_drivers`), and the proof is here: each save and update the
plugin makes runs with a planted hook of every kind in the base, and not one
of them runs. A send keeps its hooks, because the plugin's own safeguard
before anything leaves the computer is one.
"""

import os
import stat
import unittest

import support
import test_approve_local as approving
import test_changes_migration as migration
import test_confirm as confirming
import test_moment_of_use as moment_tests
import test_record_change as recording
import test_session_start as starting
import test_stale_check as checking

from gtmbase import (
    approve_local,
    changes,
    confirm,
    drafting,
    gitcmd,
    record_change,
    review,
    stale_check,
)
from gtmbase.gitcmd import GitRunner

# Every hook a save, an update, a checkout, a rewrite or a change of any
# reference can run.
HOOKS = (
    "pre-commit",
    "prepare-commit-msg",
    "commit-msg",
    "post-commit",
    "post-merge",
    "post-checkout",
    "reference-transaction",
    "pre-auto-gc",
    "post-rewrite",
    "pre-rebase",
)


def plant(root, marker, folder=None):
    """A hook of every kind in one base, each writing its name when it runs."""
    hooks = folder or os.path.join(root, ".git", "hooks")
    os.makedirs(hooks, exist_ok=True)
    for name in HOOKS:
        path = os.path.join(hooks, name)
        support.write(path, "#!/bin/sh\necho %s >> '%s'\nexit 0\n" % (name, marker))
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    # The file monitor a status runs is a program the base names too.
    monitor = os.path.join(os.path.dirname(marker), "monitor")
    support.write(monitor, "#!/bin/sh\necho fsmonitor >> '%s'\nexit 1\n" % marker)
    os.chmod(monitor, 0o755)
    support.git(["config", "--local", "core.fsmonitor", monitor], cwd=root)
    return marker


def ran(marker):
    return support.read(marker).split() if os.path.exists(marker) else []


class TestTheHelper(unittest.TestCase):
    def test_every_command_but_a_send_runs_with_hooks_off(self):
        for args in (
            ["commit", "-q", "-m", "x"],
            ["merge", "--ff-only", "x"],
            ["checkout", "HEAD", "--", "a"],
            ["worktree", "add", "--detach", "p", "HEAD"],
            ["-c", "user.name=x", "commit", "-m", "y"],
            ["status", "--porcelain"],
        ):
            made = gitcmd.hook_free(args)
            self.assertEqual(["-c", "core.hooksPath=" + os.devnull], made[:2], args)
            self.assertIn("core.fsmonitor=false", made)
            self.assertIn("commit.gpgSign=false", made)
            self.assertEqual(args, made[-len(args):])

    def test_a_send_keeps_its_hooks_and_settings_read_back_are_the_bases(self):
        for args in (
            ["push", "origin", "main"],
            ["config", "--get", "core.hooksPath"],
            ["rev-parse", "--git-path", "hooks"],
        ):
            self.assertEqual(args, gitcmd.hook_free(args))

    def test_a_difference_is_never_shown_through_a_program_the_base_names(self):
        self.assertEqual(
            ["diff", "--no-ext-diff", "--no-textconv", "--name-only"],
            gitcmd.hook_free(["diff", "--name-only"])[-4:],
        )
        self.assertIn("--no-textconv", gitcmd.hook_free(["show", "HEAD"]))


class TestThePluginsOwnSafeguardStillRuns(unittest.TestCase):
    def test_a_send_still_runs_the_pre_push_hook(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            marker = os.path.join(sandbox.path, "ran")
            hook = os.path.join(root, ".git", "hooks", "pre-push")
            support.write(hook, "#!/bin/sh\necho pre-push >> '%s'\nexit 0\n" % marker)
            os.chmod(hook, 0o755)
            support.write(os.path.join(root, "context", "x.md"), "x\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "x"], cwd=root)
            self.assertTrue(GitRunner().run(["push", "-q", "origin", "main"], cwd=root).ok)
            self.assertEqual(["pre-push"], ran(marker))


class TestEverySaveRunsNoHook(unittest.TestCase):
    def test_recording_a_context_change(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            marker = plant(base.root, os.path.join(sandbox.path, "ran"))
            flow = recording.Flow(self, base.root)
            flow.shown_and_recorded("1")
            self.assertEqual(1, len(recording.entry_files(base.root)))
            self.assertEqual([], ran(marker))

    def test_recording_one_when_the_base_points_its_hooks_elsewhere(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            elsewhere = os.path.join(base.root, "tools", "hooks")
            marker = plant(base.root, os.path.join(sandbox.path, "ran"), elsewhere)
            support.git(["config", "--local", "core.hooksPath", elsewhere], cwd=base.root)
            base.save("tools")
            os.remove(marker)
            flow = recording.Flow(self, base.root)
            flow.shown_and_recorded("1")
            self.assertEqual([], ran(marker))

    def test_approving_a_prepared_change_here(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            staged = approving.stage(root)
            marker = plant(root, os.path.join(sandbox.path, "ran"))
            _shown, applied = approving.show_and_approve(
                root, base_id, staged, approving.NoRemoteRunner()
            )
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertEqual([], ran(marker))

    def test_the_closings_saves(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            marker = plant(root, os.path.join(sandbox.path, "ran"))
            done = review.skip(
                drafting.STEP_POSITIONING,
                root,
                base_id=base_id,
                owner_email=approving.OWNER,
                runner=GitRunner(),
            )
            self.assertEqual(drafting.POSITIONING_PATH, done.path)
            self.assertEqual([], ran(marker))

    def test_a_yes_kept_in_a_base_with_no_shared_copy(self):
        with support.Sandbox() as sandbox:
            base = checking.BaseFixture(sandbox, remote=False)
            base.add_entry(push=False)
            question = confirming.ask(base)
            marker = plant(base.root, os.path.join(sandbox.path, "ran"))
            result = confirming.answer(base, question, "yes")
            self.assertEqual(confirm.STATUS_RECORDED, result.status, result.reasons)
            self.assertEqual([], ran(marker))

    def test_the_review_bringing_a_base_up_to_date(self):
        with support.Sandbox() as sandbox:
            base = checking.TestTheBaseHasToBeReady._behind(self, sandbox)
            marker = plant(base.root, os.path.join(sandbox.path, "ran"))
            result = checking.run_check(base)
            self.assertIn(stale_check.CODE_BROUGHT_UP_TO_DATE, result.codes)
            self.assertEqual([], ran(marker))


class TestTheMoveRunsNoHook(migration.MigrationCase):
    def test_moving_the_context_changes(self):
        self.old_layout()
        marker = plant(self.root, os.path.join(self.sandbox.path, "ran"))
        result = changes.migrate(self.root, self.base_id, today=migration.TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertEqual([], ran(marker))


class TestTheSessionStartUpdateRunsNoHook(
    support.PastTheFirstBackupReview, starting.SessionStartHelpers
):
    def test_the_update_at_session_start(self):
        root, _base_id = self.joined_base()
        self.add_files(root)
        other = self.working_copy(root)
        support.commit(
            other,
            "context/notes/note.md",
            ["---", "kind: note", "owner: " + starting.OWNER, "---", "", "words"],
            "a note",
        )
        support.git(["push", "-q", "origin", "main"], cwd=other)
        marker = plant(root, os.path.join(self.sandbox.path, "ran"))
        self.run_hook(root)
        self.assertTrue(os.path.isfile(os.path.join(root, "context", "notes", "note.md")))
        self.assertEqual([], ran(marker))


class TestAFilterTheBaseNamesIsRefused(unittest.TestCase):
    """The other half of finding 1: a clean or smudge program is never run."""

    def evil(self, root, marker):
        support.write(os.path.join(root, ".gitattributes"), "*.md filter=evil\n")
        support.git(["add", "--", ".gitattributes"], cwd=root)
        support.git(["commit", "-q", "-m", "attributes"], cwd=root)
        program = "sh -c 'echo filter >> \"%s\"; cat'" % marker
        support.git(["config", "--local", "filter.evil.clean", program], cwd=root)
        support.git(["config", "--local", "filter.evil.smudge", program], cwd=root)

    def test_recording_a_context_change_is_refused_and_writes_nothing(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            marker = os.path.join(sandbox.path, "ran")
            self.evil(base.root, marker)
            flow = recording.Flow(self, base.root)
            _code, out, _err = flow.show("1")
            head = support.head_of(base.root)
            code, said, _err = flow.run(
                ["--record-change", "record", "--shown", recording.value_on(out, "shown")]
            )
            self.assertEqual(1, code)
            self.assertIn(record_change.RUNS_A_PROGRAM, said)
            self.assertEqual([], ran(marker))
            self.assertEqual(head, support.head_of(base.root))
            self.assertEqual([], recording.entry_files(base.root))

    def test_any_save_through_the_runner_is_refused_before_it_runs(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            marker = os.path.join(sandbox.path, "ran")
            self.evil(root, marker)
            support.write(os.path.join(root, "context", "new.md"), "words\n")
            result = GitRunner().run(["add", "--", "context/new.md"], cwd=root)
            self.assertEqual(gitcmd.DRIVER_CODE, result.code)
            self.assertEqual(["evil"], gitcmd.executable_drivers(root))
            self.assertEqual([], ran(marker))

    def test_a_filter_the_base_never_names_refuses_nothing(self):
        """Somebody's own settings for another kind of project are not a refusal."""
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            support.git(
                ["config", "--local", "filter.lfs.clean", "git-lfs clean -- %f"], cwd=root
            )
            self.assertEqual([], gitcmd.executable_drivers(root))
            self.assertTrue(GitRunner().run(["status", "--porcelain"], cwd=root).ok)


if __name__ == "__main__":
    unittest.main()
