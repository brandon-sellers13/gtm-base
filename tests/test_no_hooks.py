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

Release B's save paths are covered the same way: the move to the CLASS layout
and its recovery, taking a finished page in and finishing an import that
stopped, a segment drafted in a later session, leaving one out and approving
the umbrella change that prepares, keeping a document edited by hand, and
every save setting a base up makes, from its first save to the closing note.
"""

import os
import stat
import unittest
from unittest import mock

import support
import test_adoption as adoption
import test_approve_local as approving
import test_changes_migration as migration
import test_confirm as confirming
import test_import_recovery as recovery
import test_live_check_follow_up as follow_up
import test_moment_of_use as moment_tests
import test_record_change as recording
import test_segments_left_to_draft as later
import test_session_start as starting
import test_stale_check as checking

from gtmbase import (
    approve_local,
    changes,
    compose_proposal,
    confirm,
    constants,
    drafting,
    gitcmd,
    hand_edit,
    join_flow,
    paths,
    record_change,
    review,
    segments,
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


def _hooks_and_monitor(hooks, marker):
    """Every hook in one folder, and a file monitor, each writing its name."""
    os.makedirs(hooks, exist_ok=True)
    for name in HOOKS:
        path = os.path.join(hooks, name)
        support.write(path, "#!/bin/sh\necho %s >> '%s'\nexit 0\n" % (name, marker))
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    # The file monitor a status runs is a program the base names too.
    monitor = os.path.join(os.path.dirname(marker), "monitor")
    support.write(monitor, "#!/bin/sh\necho fsmonitor >> '%s'\nexit 1\n" % marker)
    os.chmod(monitor, 0o755)
    return monitor


def plant(root, marker, folder=None):
    """A hook of every kind in one base, each writing its name when it runs."""
    hooks = folder or os.path.join(root, ".git", "hooks")
    monitor = _hooks_and_monitor(hooks, marker)
    support.git(["config", "--local", "core.fsmonitor", monitor], cwd=root)
    return marker


def plant_in_the_persons_settings(sandbox, marker):
    """The same hooks and monitor, named by the person's own git settings.

    A base that does not exist yet has no folder to plant a hook in, and the
    person's own settings reach every base they make, including the first
    save of a new one.
    """
    hooks = os.path.join(sandbox.path, "everywhere-hooks")
    monitor = _hooks_and_monitor(hooks, marker)
    support.git(["config", "--global", "core.hooksPath", hooks], cwd=sandbox.path)
    support.git(["config", "--global", "core.fsmonitor", monitor], cwd=sandbox.path)
    return marker


def ran(marker):
    return support.read(marker).split() if os.path.exists(marker) else []


# Reading back what a save left, with nothing the base names running, so the
# proof that a save happened never adds a line to the marker of its own.
QUIET = ["-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false"]


def at_head(root, relative):
    """What the newest saved work holds at one path, or None."""
    finished = support.git(QUIET + ["show", "HEAD:" + relative], cwd=root, check=False)
    if finished.returncode != 0:
        return None
    return finished.stdout.decode("utf-8")


def unsaved_in(root):
    finished = support.git(QUIET + ["status", "--porcelain"], cwd=root)
    return finished.stdout.decode("utf-8").strip()


def spying(module, name):
    """Record the calls to one library function while it still does its work."""
    return mock.patch.object(module, name, wraps=getattr(module, name))


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
            ["config", "--get", "core.hooksPath"],
            ["rev-parse", "--git-path", "hooks"],
        ):
            self.assertEqual(args, gitcmd.hook_free(args))
        # A send keeps its hooks, and signs nothing (Astra's confirmation of
        # 0.3.3, defect 2).
        self.assertEqual(
            ["-c", "push.gpgSign=false", "push", "origin", "main"],
            gitcmd.hook_free(["push", "origin", "main"]),
        )

    def test_checking_a_signature_is_switched_off_too(self):
        made = gitcmd.hook_free(["log", "-1"])
        self.assertIn("log.showSignature=false", made)
        self.assertIn("merge.verifySignatures=false", made)

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


OLDER_PROFILE = "context/strategy/icp.md"
CLASS_PROFILE = "context/icps.md"


class TestTheMoveRunsNoHook(migration.MigrationCase):
    def plant(self):
        return plant(self.root, os.path.join(self.sandbox.path, "ran"))

    def stop(self, **where):
        """Stop the move at one moment, before any hook is planted."""
        stopping = migration._StopAfter(**where)
        with self.assertRaises(migration._Stopped):
            changes.migrate(self.root, self.base_id, today=migration.TODAY, git=stopping)
        self.assertTrue(os.path.exists(self.note_path()))

    def note_path(self):
        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def assert_on_the_class_layout(self):
        self.assertIsNotNone(at_head(self.root, CLASS_PROFILE))
        self.assertIsNone(at_head(self.root, OLDER_PROFILE))
        self.assertFalse(os.path.exists(self.note_path()))

    def test_moving_the_context_changes(self):
        self.old_layout()
        marker = self.plant()
        result = changes.migrate(self.root, self.base_id, today=migration.TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertEqual([], ran(marker))
        self.assert_on_the_class_layout()

    def test_finishing_a_move_that_stopped_after_its_first_save(self):
        self.old_layout()
        self.stop(stop_after_subject=changes.MOVE_SUBJECT)
        marker = self.plant()
        result = changes.resume(self.root, self.base_id, today=migration.TODAY)
        self.assertEqual(changes.STATUS_RESUMED, result.status, result.sentence)
        self.assertEqual([], ran(marker))
        self.assert_on_the_class_layout()

    def test_putting_back_a_move_that_stopped_before_its_first_save(self):
        self.old_layout()
        self.stop(stop_before_subject=changes.MOVE_SUBJECT)
        marker = self.plant()
        with spying(changes, "_put_back") as put_back:
            result = changes.migrate(self.root, self.base_id, today=migration.TODAY)
        self.assertTrue(put_back.called)
        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertEqual([], ran(marker))
        self.assert_on_the_class_layout()

    def test_giving_up_on_a_move_that_stopped(self):
        self.old_layout()
        self.stop(stop_before_subject=changes.MOVE_SUBJECT)
        marker = self.plant()
        result = changes.abandon(self.root, self.base_id, today=migration.TODAY)
        self.assertEqual(changes.STATUS_UNDONE, result.status, result.sentence)
        self.assertEqual([], ran(marker))
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertTrue(os.path.isfile(os.path.join(self.root, OLDER_PROFILE)))
        self.assertFalse(os.path.exists(os.path.join(self.root, CLASS_PROFILE)))
        self.assertEqual("", unsaved_in(self.root))


FIRST = "Fintech lenders"


class TestTakingFinishedPagesInRunsNoHook(unittest.TestCase):
    """Unit 1.7c and 1.7d: a finished page taken in, and an import finished."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.company = adoption.Company(
            [(name, adoption.clean_page(name), "icp-%s.md" % segments.slug_for(name))
             for name in (FIRST, "Regional banks")]
        )
        self.relative = self.company.destination(FIRST)

    def plant(self):
        return plant(self.company.root, os.path.join(self.sandbox.path, "ran"))

    def stop_after_staging(self):
        shown = recovery.show(self.company.run, self.company, FIRST)
        with recovery.StopAfter(review, "_stage_bytes", lambda *a, **k: True) as stop:
            with self.assertRaises(recovery.Stopped):
                recovery.approve(self.company.run, self.company, FIRST, shown.digest)
        self.assertTrue(stop.fired)

    def finish_it(self):
        resumed = join_flow.resume_import(
            join_flow.new_run(recovery.TODAY),
            self.company.root,
            recovery.SESSION_TWO,
            runner=GitRunner(),
            now=recovery.NOW,
        )
        self.assertEqual([FIRST], [segment.name for segment in resumed.finished])

    def assert_saved_with_its_line(self):
        self.assertEqual(self.company.read(self.relative), at_head(self.company.root, self.relative))
        line = at_head(self.company.root, confirm.confirmations_path_for(self.relative))
        self.assertIsNotNone(line)
        self.assertIn(self.company.run, line)
        self.assertEqual("", unsaved_in(self.company.root))

    def test_taking_a_finished_page_in(self):
        shown = recovery.show(self.company.run, self.company, FIRST)
        marker = self.plant()
        with spying(review, "approve_adopted") as approving_it:
            result = recovery.approve(
                self.company.run, self.company, FIRST, shown.digest, runner=GitRunner()
            )
        self.assertTrue(approving_it.called)
        self.assertEqual(self.relative, result.path)
        self.assertEqual([], ran(marker))
        self.assert_saved_with_its_line()

    def test_finishing_an_import_that_stopped_after_the_write(self):
        self.stop_after_staging()
        marker = self.plant()
        with spying(review, "finish_adopted") as finishing:
            self.finish_it()
        self.assertTrue(finishing.called)
        self.assertEqual([], ran(marker))
        self.assert_saved_with_its_line()

    def test_finishing_an_import_saved_without_its_line(self):
        self.stop_after_staging()
        # Another window saves what was staged: the page, and no line.
        support.git(["commit", "-q", "-m", "saved in another window"], cwd=self.company.root)
        self.assertIsNone(
            at_head(self.company.root, confirm.confirmations_path_for(self.relative))
        )
        marker = self.plant()
        with spying(review, "confirm_saved") as confirming_it:
            self.finish_it()
        self.assertTrue(confirming_it.called)
        self.assertEqual([], ran(marker))
        self.assert_saved_with_its_line()

    def test_finishing_an_import_whose_page_went_before_its_save(self):
        self.stop_after_staging()
        # The page is staged and then gone from its name, so what the import
        # staged is taken back first and the page is written again.
        os.remove(os.path.join(self.company.root, self.relative))
        marker = self.plant()
        with spying(review, "put_back_unwritten") as putting_back:
            with spying(review, "approve_adopted") as approving_it:
                self.finish_it()
        self.assertTrue(putting_back.called)
        self.assertTrue(approving_it.called)
        self.assertEqual([], ran(marker))
        self.assert_saved_with_its_line()


class TestSegmentsFinishedLaterRunNoHook(later.Case):
    """Brandon's calls 29 and 36: a segment drafted, or left out, later."""

    def closed(self):
        company = later.a_company()
        later.set_up_and_close(company)
        run_id, _shown = later.listed(company, later.LATER)
        join_flow.draft_freeze(run_id, later.SESSION_TWO, today=later.TODAY)
        return company, run_id

    def test_a_segment_drafted_and_approved_in_a_later_session(self):
        company, run_id = self.closed()
        join_flow.assemble_step(
            drafting.STEP_SEGMENT, run_id, "Acme", later.EMAIL, today=later.TODAY,
            segment=later.slug(later.LATER),
        )
        marker = plant(company.root, os.path.join(self.sandbox.path, "ran"))
        with spying(review, "approve_adopted") as approving_it:
            result = later.approve(run_id, company, later.LATER, runner=GitRunner())
        self.assertTrue(approving_it.called)
        relative = company.destination(later.LATER)
        self.assertEqual(relative, result.path)
        self.assertEqual([], ran(marker))
        self.assertEqual(company.read(relative), at_head(company.root, relative))
        self.assertEqual("", unsaved_in(company.root))

    def test_leaving_one_out_and_approving_the_umbrella_change_here(self):
        company, run_id = self.closed()
        with recovery.StopAfter(review, "_create_new") as stop:
            with self.assertRaises(recovery.Stopped):
                later.approve(run_id, company, later.LATER)
        self.assertTrue(stop.fired)
        marker = plant(company.root, os.path.join(self.sandbox.path, "ran"))
        runner = GitRunner()
        with spying(review, "take_back_unsaved") as taking_back:
            said = join_flow.draft_leave_out(
                later.slug(later.LATER), company.root, runner=runner
            )
        self.assertTrue(taking_back.called)
        self.assertIn(join_flow.UMBRELLA_CHANGE_WAITING % {"name": later.LATER}, said)
        self.assertIsNone(company.read(company.destination(later.LATER)))
        staged = follow_up.pending_changes(company.root)[0]
        shown = approve_local.show(staged, company.root, company.base_id, runner=runner)
        self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
        applied = approve_local.approve(
            staged, company.root, company.base_id, shown.shown_hash, runner=runner
        )
        self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
        self.assertEqual([], ran(marker))
        umbrella = at_head(company.root, later.UMBRELLA)
        self.assertIn(
            constants.UMBRELLA_LEFT_OUT_SENTENCE,
            umbrella[umbrella.index("### %s" % later.LATER):],
        )
        self.assertEqual("", unsaved_in(company.root))


class TestKeepingAHandEditRunsNoHook(unittest.TestCase):
    """Calls 33, 34 and 49: a document edited by hand, kept three ways."""

    def keep(self, sandbox, change, answer, **kind):
        root, base_id = follow_up.a_base(sandbox)
        change(root)
        marker = plant(root, os.path.join(sandbox.path, "ran"))
        runner = GitRunner()
        staged = compose_proposal.stage_local_edit(
            root, base_id, answer, runner=runner, now=follow_up.TODAY, **kind
        )
        with spying(approve_local, "_walk_a_hand_edit") as walking:
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=follow_up.TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=follow_up.NOW
            )
        self.assertTrue(walking.called)
        self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
        self.assertEqual([], ran(marker))
        self.assertEqual(
            support.read(os.path.join(root, follow_up.ICP)), at_head(root, follow_up.ICP)
        )
        self.assertEqual("", unsaved_in(root))
        return root

    def changes_saved(self, root):
        folder = os.path.join(root, constants.CHANGES_DIR)
        return [
            name
            for name in (os.listdir(folder) if os.path.isdir(folder) else [])
            if name.endswith(".md")
            and at_head(root, "%s/%s" % (constants.CHANGES_DIR, name)) is not None
        ]

    def test_keeping_a_wording_only_fix(self):
        with support.Sandbox() as sandbox:
            root = self.keep(
                sandbox, follow_up.fix_the_comma, None, kind=hand_edit.KIND_WORDING
            )
            self.assertIn("Buyers who try it buy it.", at_head(root, follow_up.ICP))
            self.assertEqual([], self.changes_saved(root))

    def test_keeping_a_corrected_fact_that_records_a_context_change(self):
        with support.Sandbox() as sandbox:
            root = self.keep(
                sandbox,
                follow_up.correct_the_fact,
                follow_up.FACT_ANSWER,
                kind=hand_edit.KIND_FACT,
                what_changed=follow_up.FACT_LINE,
                also_affects=[follow_up.POSITIONING],
            )
            self.assertIn("over 1 million drivers", at_head(root, follow_up.ICP))
            self.assertEqual(1, len(self.changes_saved(root)))

    def test_keeping_a_change_to_the_business(self):
        with support.Sandbox() as sandbox:
            root = self.keep(
                sandbox,
                lambda root: follow_up.edit(
                    root, "Buyers who try it, buy it.", "We now sell to retail firms."
                ),
                "We started selling to retail firms this month, after two pilots closed.",
                kind=hand_edit.KIND_BUSINESS,
                what_changed="We now sell the marketing use case to retail firms.",
            )
            self.assertIn("We now sell to retail firms.", at_head(root, follow_up.ICP))
            self.assertEqual(1, len(self.changes_saved(root)))


class TestSettingUpABaseRunsNoHook(unittest.TestCase):
    """Every save setup makes, from the base's first save to the closing note."""

    def test_setting_up_a_base_from_its_first_save_to_the_closing_note(self):
        with support.Sandbox() as sandbox:
            company = later.a_company(build=False)
            marker = plant_in_the_persons_settings(
                sandbox, os.path.join(sandbox.path, "ran")
            )
            company.build()
            company.adopt(later.TAKEN_IN)
            later.approve(company.run, company, later.DRAFTED)
            closed = join_flow.close_run(
                company.root,
                company.run,
                got_in_the_way="The material was spread across three folders.",
                now=later.TODAY,
                plugin_root=support.PLUGIN_DIR,
                runner=GitRunner(),
            )
            self.assertEqual([], ran(marker))
            self.assertEqual([], closed.note_codes)
            for relative in (
                later.UMBRELLA,
                drafting.POSITIONING_PATH,
                company.destination(later.TAKEN_IN),
                company.destination(later.DRAFTED),
                closed.note_path,
            ):
                self.assertIsNotNone(at_head(company.root, relative), relative)
            self.assertEqual("", unsaved_in(company.root))


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


# A stand-in for the signing program, which writes down every time it is run.
FAKE_SIGNER = """#!/bin/sh
echo "$@" >> '%s'
case "$*" in *--verify*) exit 0;; esac
cat > /dev/null
echo "[GNUPG:] SIG_CREATED D 1 8 00 1 X" >&2
printf -- '-----BEGIN PGP SIGNATURE-----\n\nfake\n-----END PGP SIGNATURE-----\n'
"""


class TestNoSignatureProgramRuns(unittest.TestCase):
    """Astra's confirmation of 0.3.3, defect 2."""

    def signer(self, sandbox):
        marker = os.path.join(sandbox.path, "signed")
        program = os.path.join(sandbox.path, "signer")
        support.write(program, FAKE_SIGNER % marker)
        os.chmod(program, 0o755)
        return program, marker

    def signed_save(self, root, program, text="signed\n"):
        support.write(os.path.join(root, "context", "signed.md"), text)
        support.git(["add", "-A"], cwd=root)
        support.git(
            [
                "-c", "gpg.program=" + program,
                "-c", "user.signingKey=x",
                "commit", "-q", "-S", "-m", "a signed save",
            ],
            cwd=root,
        )

    def test_reading_the_history_never_checks_a_signature(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            program, marker = self.signer(sandbox)
            self.signed_save(root, program)
            if os.path.exists(marker):
                os.remove(marker)
            support.git(["config", "--local", "gpg.program", program], cwd=root)
            support.git(["config", "--local", "log.showSignature", "true"], cwd=root)
            self.assertTrue(GitRunner().run(["log", "-1", "--format=%s"], cwd=root).ok)
            self.assertTrue(GitRunner().run(["show", "-s", "HEAD"], cwd=root).ok)
            self.assertEqual([], ran(marker))

    def test_an_update_never_checks_a_signature(self):
        with support.Sandbox() as sandbox:
            base = checking.BaseFixture(sandbox)
            base.add_entry()
            program, marker = self.signer(sandbox)
            other = os.path.join(sandbox.path, "other")
            support.git(["clone", "-q", base.remote, other], cwd=sandbox.path)
            support.git(["config", "--local", "user.email", "owner@example.com"], cwd=other)
            support.git(["config", "--local", "user.name", "Test Owner"], cwd=other)
            self.signed_save(other, program)
            support.git(["push", "-q", "origin", "main"], cwd=other)
            if os.path.exists(marker):
                os.remove(marker)
            support.git(["config", "--local", "gpg.program", program], cwd=base.root)
            support.git(
                ["config", "--local", "merge.verifySignatures", "true"], cwd=base.root
            )
            result = checking.run_check(base)
            self.assertIn(stale_check.CODE_BROUGHT_UP_TO_DATE, result.codes)
            self.assertEqual([], ran(marker))

    def test_a_send_runs_its_hook_and_no_signing_program(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            remote = support.git(
                ["remote", "get-url", "origin"], cwd=root
            ).stdout.decode("utf-8").strip()
            support.git(["config", "receive.certNonceSeed", "seed"], cwd=remote)
            program, marker = self.signer(sandbox)
            support.git(["config", "--local", "gpg.program", program], cwd=root)
            support.git(["config", "--local", "user.signingKey", "x"], cwd=root)
            support.git(["config", "--local", "push.gpgSign", "true"], cwd=root)
            hook_ran = os.path.join(sandbox.path, "hook")
            hook = os.path.join(root, ".git", "hooks", "pre-push")
            support.write(hook, "#!/bin/sh\necho pre-push >> '%s'\nexit 0\n" % hook_ran)
            os.chmod(hook, 0o755)
            support.write(os.path.join(root, "context", "x.md"), "x\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "x"], cwd=root)
            self.assertTrue(GitRunner().run(["push", "-q", "origin", "main"], cwd=root).ok)
            self.assertEqual(["pre-push"], ran(hook_ran))
            self.assertEqual([], ran(marker))


class TestAttributesAreReadTheWayGitReadsThem(unittest.TestCase):
    """Astra's confirmation of 0.3.3, defect 1."""

    def configure(self, root, marker):
        program = "sh -c 'echo filter >> \"%s\"; cat'" % marker
        for part in ("clean", "smudge"):
            support.git(["config", "--local", "filter.evil." + part, program], cwd=root)

    def test_a_relative_attributes_file_is_read_from_the_base(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            marker = os.path.join(sandbox.path, "ran")
            support.write(os.path.join(root, "tools", "attributes"), "*.md filter=evil\n")
            support.git(["config", "--local", "core.attributesFile", "tools/attributes"], cwd=root)
            self.configure(root, marker)
            here = os.getcwd()
            os.chdir(sandbox.path)
            try:
                self.assertEqual(["evil"], gitcmd.executable_drivers(root))
            finally:
                os.chdir(here)
            support.write(os.path.join(root, "context", "new.md"), "words\n")
            result = GitRunner().run(["add", "--", "context/new.md"], cwd=root)
            self.assertEqual(gitcmd.DRIVER_CODE, result.code)
            self.assertEqual([], ran(marker))

    def test_an_attribute_file_too_long_to_read_whole_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            marker = os.path.join(sandbox.path, "ran")
            padding = ("# nothing to see here\n" * 60000)
            support.write(
                os.path.join(root, ".gitattributes"), padding + "*.md filter=evil\n"
            )
            self.configure(root, marker)
            self.assertNotEqual([], gitcmd.executable_drivers(root))
            support.write(os.path.join(root, "context", "new.md"), "words\n")
            result = GitRunner().run(["add", "--", "context/new.md"], cwd=root)
            self.assertEqual(gitcmd.DRIVER_CODE, result.code)
            self.assertEqual([], ran(marker))

    def test_attributes_only_lined_up_to_be_saved_still_count(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            marker = os.path.join(sandbox.path, "ran")
            support.write(os.path.join(root, ".gitattributes"), "*.md filter=evil\n")
            support.git(["add", "--", ".gitattributes"], cwd=root)
            os.remove(os.path.join(root, ".gitattributes"))
            self.configure(root, marker)
            os.remove(os.path.join(root, "context", "strategy", "icp.md"))
            result = GitRunner().run(
                ["checkout", "HEAD", "--", "context/strategy/icp.md"], cwd=root
            )
            self.assertEqual(gitcmd.DRIVER_CODE, result.code)
            self.assertEqual([], ran(marker))

    def test_a_working_folder_made_from_a_fetched_tree_is_refused_first(self):
        with support.Sandbox() as sandbox:
            base = checking.BaseFixture(sandbox)
            base.add_entry()
            marker = os.path.join(sandbox.path, "ran")
            other = os.path.join(sandbox.path, "other")
            support.git(["clone", "-q", base.remote, other], cwd=sandbox.path)
            support.git(["config", "--local", "user.email", "owner@example.com"], cwd=other)
            support.git(["config", "--local", "user.name", "Test Owner"], cwd=other)
            support.write(os.path.join(other, ".gitattributes"), "*.md filter=evil\n")
            support.write(os.path.join(other, "context", "more.md"), "more\n")
            support.git(["add", "-A"], cwd=other)
            support.git(["commit", "-q", "-m", "attributes"], cwd=other)
            support.git(["push", "-q", "origin", "main"], cwd=other)
            self.configure(base.root, marker)
            self.assertTrue(
                GitRunner().run(["fetch", "-q", "origin", "main"], cwd=base.root).ok
            )
            folder = os.path.join(sandbox.path, "proposal")
            result = GitRunner().run(
                ["worktree", "add", "--detach", folder, "origin/main"], cwd=base.root
            )
            self.assertEqual(gitcmd.DRIVER_CODE, result.code)
            self.assertFalse(os.path.exists(os.path.join(folder, "context", "more.md")))
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

    def test_the_look_for_a_filter_starts_no_monitor_the_base_names(self):
        """Found while merging 0.3.3 into Release B.

        The look for a filter reads what is lined up to be saved, and that
        read asked the base's file monitor, before every save and every look
        at what is unsaved, for anybody whose own settings name any filter at
        all, as installing a large-file tool does.
        """
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            marker = plant(root, os.path.join(sandbox.path, "ran"))
            support.git(
                ["config", "--global", "filter.lfs.clean", "git-lfs clean -- %f"],
                cwd=sandbox.path,
            )
            self.assertTrue(GitRunner().run(["status", "--porcelain"], cwd=root).ok)
            support.write(os.path.join(root, "context", "new.md"), "words\n")
            self.assertTrue(GitRunner().run(["add", "--", "context/new.md"], cwd=root).ok)
            self.assertTrue(
                GitRunner().run(["commit", "-q", "-m", "new"], cwd=root).ok
            )
            self.assertEqual("words\n", at_head(root, "context/new.md"))
            self.assertEqual([], ran(marker))


if __name__ == "__main__":
    unittest.main()
