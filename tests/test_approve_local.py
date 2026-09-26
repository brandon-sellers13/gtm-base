"""Approving one prepared change on a base that has no shared copy.

Every scenario here builds a real repository in a temporary folder with no
shared copy at all, and no stand-in for one, because the whole point of this
path is the base that has nowhere to send anything. The runner used throughout
refuses any command that could reach a remote, so a scenario that passes has
proved that nothing left the computer rather than asserting that it did not.
"""

import datetime
import os
import subprocess
import unittest
from unittest import mock

import plain_language
import support

from gtmbase import (
    approve_local,
    compose_proposal,
    constants,
    formats,
    ids,
    machine,
    names,
    paths,
    report,
    stale_check,
    state,
)
from gtmbase.gitcmd import GitResult, GitRunner
from gtmbase.validate import marker_line

TODAY = datetime.date(2026, 6, 5)
NOW = datetime.datetime(2026, 6, 5, 12, 30, 0)
ICP = "context/strategy/icp.md"
OWNER = "owner@example.com"
STAGING = "stg-0000000000000000"
SOURCE = "src-000000000000000000000000"
OTHER_STAGING = "stg-" + "c" * 16
SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "propose-change")


# --- The runner every scenario uses ------------------------------------------

# It lives in `support.py` now, because Unit 1.3 needs the same proof for the
# moment-of-use check and two copies of one safety net is one copy too many.
REMOTE_COMMANDS = support.REMOTE_COMMANDS
NoRemoteRunner = support.NoRemoteRunner


# --- Fixtures ----------------------------------------------------------------


def local_base(sandbox, name="local"):
    """A base with no shared copy, and nothing anywhere pretending to be one."""
    root = os.path.join(sandbox.path, name)
    base_id = ids.base_id_random()
    support.make_base(root, base_id=base_id)
    support.write(
        os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n"
    )
    support.write(
        os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n%s\n" % OWNER
    )
    support.write(os.path.join(root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a local base"], cwd=root)
    machine.append_joined(root=root, base_id=base_id, remote=None)
    state.update_seat(base_id, first_push_reviewed=False)
    return root, base_id


def stage(root, text=None, staging_id=STAGING):
    """Put a prepared change where the stale check would have left it."""
    if text is None:
        text = support.read(os.path.join(support.TEMPLATES_DIR, "proposal-staging.md"))
    path = os.path.join(root, constants.PROPOSALS_PENDING_DIR, staging_id + ".md")
    support.write(path, text)
    return path


def commit_count(root):
    finished = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=root, stdout=subprocess.PIPE
    )
    return int(finished.stdout.decode("utf-8").strip() or "0")


def last_subject(root):
    finished = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


def confirmations_of(root, path=ICP):
    relative = constants.CONFIRMATIONS_DIR + "/" + path.replace("/", "--")
    full = os.path.join(root, relative)
    if not os.path.isfile(full):
        return []
    lines, _bad = formats.parse_confirmations_file(support.read(full))
    return lines


def corrections_in(root):
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder) if name.endswith(".md"))


def show_and_approve(root, base_id, staged, runner):
    shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
    applied = approve_local.approve(
        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
    )
    return shown, applied


# --- The happy path ----------------------------------------------------------


class TestAChangeApprovedHere(unittest.TestCase):
    def test_one_yes_applies_the_change_and_records_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            before = commit_count(root)

            shown, applied = show_and_approve(root, base_id, staged, runner)

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )

            # The file says what the change said.
            icp = support.read(os.path.join(root, ICP))
            self.assertIn("twenty to two hundred people", icp)
            self.assertNotIn("Companies of any size.", icp)

            # The context change it carried is written down.
            entry_path = "%s/%s.md" % (constants.CHANGES_DIR, STAGING)
            entry = formats.LedgerEntry.parse(
                support.read(os.path.join(root, entry_path))
            )
            entry.validate(TODAY)
            self.assertEqual(TODAY.isoformat(), entry.written_on)

            # One line says the owner approved it, and it names the change.
            lines = confirmations_of(root)
            self.assertEqual("ledger", lines[-1].trigger)
            self.assertEqual(STAGING, lines[-1].entry)
            self.assertEqual(TODAY.isoformat(), lines[-1].date)

            # The record of what changed parses and holds the hash of the file.
            names_found = corrections_in(root)
            self.assertEqual(1, len(names_found))
            record = formats.CorrectionsFile.parse(
                support.read(
                    os.path.join(root, constants.CORRECTIONS_DIR, names_found[0])
                )
            )
            record.validate()
            self.assertEqual(ids.content_hash(icp), record.content_hash)
            self.assertEqual([ICP, entry_path], record.touched_paths)

            # One piece of saved work holds all of it, and the tree is clean.
            self.assertEqual(before + 1, commit_count(root))
            self.assertTrue(
                last_subject(root).startswith(report.LOCAL_APPROVAL_COMMIT_PREFIX)
            )
            self.assertEqual("", support.status_of(root))

            # The prepared change is gone from where it was waiting.
            self.assertFalse(os.path.isfile(staged))
            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        root, constants.PROPOSALS_OPENED_DIR, STAGING + ".md"
                    )
                )
            )

    def test_the_whole_change_is_shown_in_the_four_line_form(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            artifact = shown.artifact
            self.assertTrue(artifact.startswith(approve_local.ARTIFACT_OPEN))
            self.assertIn(approve_local.ARTIFACT_CLOSE, artifact)
            self.assertEqual([], plain_language.find_malformed_changes(artifact))
            for label in plain_language.CHANGE_LABELS:
                self.assertIn(label, artifact)
            # The names a person reads, never the paths, in the four lines.
            four = artifact.split(approve_local.CHANGE_OPEN)[1].split(
                approve_local.CHANGE_CLOSE
            )[0]
            self.assertIn(names.document_name(ICP), four)
            self.assertNotIn(ICP, four)
            # The part of the file as it reads now, and as it would read after.
            self.assertIn("Companies of any size.", artifact)
            self.assertIn("twenty to two hundred people", artifact)
            self.assertEqual([approve_local.ASK], shown.reasons)

    def test_the_markers_are_the_ones_the_standard_sets(self):
        self.assertEqual(plain_language.ARTIFACT_OPEN, approve_local.ARTIFACT_OPEN)
        self.assertEqual(plain_language.ARTIFACT_CLOSE, approve_local.ARTIFACT_CLOSE)
        self.assertEqual(plain_language.CHANGE_OPEN, approve_local.CHANGE_OPEN)
        self.assertEqual(plain_language.CHANGE_CLOSE, approve_local.CHANGE_CLOSE)
        self.assertEqual(plain_language.CHANGE_LABELS, approve_local.CHANGE_LABELS)


class TestTheOtherTwoAnswers(unittest.TestCase):
    def test_not_yet_leaves_the_prepared_change_and_the_base_alone(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            before = commit_count(root)

            result = approve_local.keep(staged)

            self.assertEqual(approve_local.STATUS_KEPT, result.status)
            self.assertEqual([approve_local.KEPT], result.reasons)
            self.assertTrue(os.path.isfile(staged))
            self.assertEqual(before, commit_count(root))
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))
            self.assertEqual([], corrections_in(root))
            del base_id

    def test_drop_it_throws_the_prepared_change_away_and_leaves_the_file(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            before = commit_count(root)

            result = approve_local.drop(staged, root, base_id)

            self.assertEqual(approve_local.STATUS_DROPPED, result.status)
            self.assertEqual([approve_local.DROPPED], result.reasons)
            self.assertFalse(os.path.isfile(staged))
            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        root, constants.PROPOSALS_DROPPED_DIR, STAGING + ".md"
                    )
                )
            )
            self.assertEqual(before, commit_count(root))
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))
            self.assertEqual([], confirmations_of(root))


# --- The yes is bound to what was shown --------------------------------------


class TestTheYesIsBoundToWhatWasShown(unittest.TestCase):
    def test_a_prepared_change_that_moved_after_the_showing_applies_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            support.write(
                staged,
                support.read(staged).replace(
                    "two hundred people, with a marketing team of one to five.",
                    "five thousand people, with a marketing team of forty.",
                ),
            )
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_MOVED, applied.status)
            self.assertEqual([approve_local.MOVED], applied.reasons)
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))
            self.assertEqual([], corrections_in(root))
            self.assertEqual("", support.status_of(root))

    def test_a_file_that_moved_after_the_showing_applies_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            support.write(
                os.path.join(root, ICP),
                support.read(os.path.join(root, ICP)).replace(
                    "Companies of any size.", "Companies of any size at all."
                ),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the owner edited it"], cwd=root)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_MOVED, applied.status)
            self.assertEqual([], corrections_in(root))

    def test_a_yes_with_no_value_at_all_applies_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            applied = approve_local.approve(
                staged, root, base_id, "", runner=NoRemoteRunner(), now=NOW
            )

            self.assertEqual(approve_local.STATUS_MOVED, applied.status)
            self.assertEqual([], corrections_in(root))


class TestAChangeThatNoLongerFitsTheFile(unittest.TestCase):
    def test_the_part_it_rewrites_being_gone_is_reported_and_applies_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            support.write(
                os.path.join(root, ICP),
                support.read(os.path.join(root, ICP)).replace(
                    "## Firmographics", "## Who we sell to"
                ),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "renamed a part"], cwd=root)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_CONFLICT, shown.status)
            self.assertEqual(
                [approve_local.CONFLICT % names.document_name(ICP)], shown.reasons
            )
            self.assertIn("prepared again", shown.reasons[0])
            self.assertEqual("", support.status_of(root))
            self.assertEqual([], corrections_in(root))


# --- The state of the folder -------------------------------------------------


class TestTheStateOfTheFolder(unittest.TestCase):
    def test_edits_the_person_has_not_saved_stop_the_run(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            support.write(
                os.path.join(root, "context", "notes.md"), "# Notes\n\nMine.\n"
            )

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.UNSAVED_EDITS], applied.reasons)
            self.assertEqual([], corrections_in(root))
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))
            self.assertTrue(
                os.path.isfile(os.path.join(root, "context", "notes.md"))
            )


# --- A run that stopped halfway ----------------------------------------------


def final_state(root):
    """Everything about the base a finished run is judged by."""
    return {
        "icp": support.read(os.path.join(root, ICP)),
        "corrections": corrections_in(root),
        "confirmations": [line.render() for line in confirmations_of(root)],
        "commits": commit_count(root),
        "subject": last_subject(root),
        "status": support.status_of(root),
        "staged": os.path.isfile(
            os.path.join(root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md")
        ),
        "kept": os.path.isfile(
            os.path.join(root, constants.PROPOSALS_OPENED_DIR, STAGING + ".md")
        ),
    }


class TestARunThatStoppedHalfway(unittest.TestCase):
    """Whatever it stopped after, the retry ends in the one same state."""

    def finished_state(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            show_and_approve(root, base_id, staged, NoRemoteRunner())
            return final_state(root)

    def stop_after(self, target):
        """Stop one run at a named step, then run it again and see where it ends."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            with mock.patch.object(
                approve_local, target, side_effect=RuntimeError("stopped")
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )
            self.assertIsNotNone(approve_local._load_journal(base_id))

            again = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
            self.assertEqual(
                approve_local.STATUS_APPLIED, again.status, again.reasons
            )
            self.assertIsNone(approve_local._load_journal(base_id))
            return final_state(root)

    def test_stopping_after_the_file_write_ends_where_a_finished_run_ends(self):
        self.assertEqual(self.finished_state(), self.stop_after("_stage_the_files"))

    def test_stopping_after_the_staging_ends_where_a_finished_run_ends(self):
        self.assertEqual(
            self.finished_state(), self.stop_after("_write_the_confirmation_lines")
        )

    def test_stopping_after_the_confirmation_line_ends_where_a_finished_run_ends(self):
        self.assertEqual(self.finished_state(), self.stop_after("_save_the_work"))

    def test_stopping_after_the_saved_work_ends_where_a_finished_run_ends(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            with mock.patch.object(
                approve_local.compose_proposal,
                "retire",
                side_effect=RuntimeError("stopped"),
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )

            again = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_APPLIED, again.status)
            self.assertIn(approve_local.CODE_RESUMED, again.codes)
            self.assertIsNone(approve_local._load_journal(base_id))
            self.assertEqual(self.finished_state(), final_state(root))

    def test_nothing_is_ever_half_applied_while_a_run_is_stopped(self):
        """Between the stop and the retry the base holds no part of the change."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            before = commit_count(root)
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            with mock.patch.object(
                approve_local, "_save_the_work", side_effect=RuntimeError("stopped")
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )

            # Nothing was saved, so nothing in the base counts as approved yet.
            self.assertEqual(before, commit_count(root))
            approve_local._finish_unfinished_work(root, base_id, STAGING, runner, [])
            self.assertEqual("", support.status_of(root))
            self.assertEqual([], corrections_in(root))
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))

    def test_its_own_unfinished_work_is_told_apart_from_the_person_s_edits(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            with mock.patch.object(
                approve_local, "_save_the_work", side_effect=RuntimeError("stopped")
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )
            mine = os.path.join(root, "context", "notes.md")
            support.write(mine, "# Notes\n\nSomething I was in the middle of.\n")

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            # This run's own leavings were undone, the person's edit was not,
            # and the person's edit is what stopped the run.
            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.UNSAVED_EDITS], applied.reasons)
            self.assertEqual(
                "Something I was in the middle of.\n", support.read(mine)[9:]
            )
            self.assertEqual("?? context/notes.md", support.status_of(root))
            self.assertEqual([], corrections_in(root))
            self.assertIn("Companies of any size.", support.read(os.path.join(root, ICP)))


# --- Security ----------------------------------------------------------------


class TestWhatItRefusesToTouch(unittest.TestCase):
    def test_a_path_in_the_assistants_own_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
            ).replace(
                "path: context/strategy/icp.md",
                "path: context/.claude/settings.md",
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_ASSISTANT_FOLDER], shown.codes)
            self.assertEqual([], corrections_in(root))

    def test_a_path_outside_the_folders_a_change_may_touch_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
            ).replace(
                "affects: [context/strategy/icp.md]\nreview_by",
                "affects: [CODEOWNERS]\nreview_by",
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_OUTSIDE_ALLOWED], shown.codes)
            self.assertIn("CODEOWNERS", shown.reasons[0])
            self.assertEqual([], corrections_in(root))

    def test_a_change_to_the_map_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
            ).replace("context/strategy/icp.md", constants.MAP_PATH)
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn(compose_proposal.CODE_MAP_TARGET, shown.codes)

    def test_a_contact_detail_is_refused_by_class_and_never_by_value(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
            ).replace(
                "Companies of twenty to two hundred people, with a marketing "
                "team of one to five.",
                "Companies like the one run by prospect@example.test.",
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn("email", " ".join(shown.codes))
            self.assertNotIn("prospect@example.test", " ".join(shown.reasons))
            self.assertEqual([], corrections_in(root))

    def test_a_key_is_refused_by_class_and_never_by_value(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            secret = "sk-" + "a1b2c3d4e5" * 4
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
            ).replace(
                "Companies of twenty to two hundred people, with a marketing "
                "team of one to five.",
                "The reporting key is %s." % secret,
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertNotIn(secret, " ".join(shown.reasons))
            self.assertEqual([], corrections_in(root))


class TestOnlyAnOwnerMayApprove(unittest.TestCase):
    def test_somebody_who_is_not_an_owner_is_refused_and_told_who_is(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            support.git(
                ["config", "--local", "user.email", "someone@example.test"], cwd=root
            )

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], shown.codes)
            self.assertIn(OWNER, shown.reasons[0])
            self.assertIn(names.document_name(ICP), shown.reasons[0])

    def test_somebody_who_is_not_an_owner_cannot_apply_one_either(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            support.git(
                ["config", "--local", "user.email", "someone@example.test"], cwd=root
            )

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], applied.codes)
            self.assertEqual([], corrections_in(root))

    def test_a_file_that_says_nobody_owns_it_cannot_be_approved(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            support.write(
                os.path.join(root, ICP),
                support.read(os.path.join(root, ICP)).replace(
                    "owner: %s" % OWNER, "owner: []"
                ),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "took the owner off"], cwd=root)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NO_OWNER_RECORDED], shown.codes)


class TestNothingAboutLeavingTheComputerChanges(unittest.TestCase):
    def test_the_first_backup_is_still_unreviewed_after_a_change_is_approved(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            seat, _problems = state.load_seat(base_id)
            self.assertFalse(seat.get("first_push_reviewed"))

            _shown, applied = show_and_approve(root, base_id, staged, NoRemoteRunner())

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status)
            seat, _problems = state.load_seat(base_id)
            self.assertFalse(seat.get("first_push_reviewed"))

    def test_no_git_call_anywhere_in_the_path_can_reach_a_remote(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()

            # The runner fails the test on any command that could reach one, so
            # reaching the end of the run is the assertion. This only checks
            # that the runner was the one doing the work.
            _shown, applied = show_and_approve(root, base_id, staged, runner)

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status)
            self.assertTrue(any("commit" in call for call in runner.calls))
            self.assertTrue(
                any(call[:2] == ["remote", "get-url"] for call in runner.calls)
            )

    def test_the_runner_used_here_would_notice_a_command_reaching_a_remote(self):
        runner = NoRemoteRunner()
        for arguments in (
            ["push", "origin", "main"],
            ["fetch", "origin"],
            ["pull"],
            ["clone", "somewhere", "here"],
            ["ls-remote", "origin"],
            ["remote", "add", "origin", "somewhere"],
            ["archive", "--remote", "origin", "HEAD"],
        ):
            with self.assertRaises(AssertionError, msg=arguments):
                runner.run(arguments, cwd=".")

    def test_both_conditions_still_stop_everything_leaving(self):
        """Changed 2026-09-20 for findings A1 and H1, and it used to compare
        bytes.

        Unit 1.2b asserted that approving a change locally had touched neither
        of the two files holding the line about what leaves this computer, and
        byte for byte was the right bar while nothing else was meant to touch
        them. Both were changed on purpose for those two findings, and only
        for them, so the bar moved from the bytes to what the two files
        answer: both conditions still stop a send, and local approval still
        asks neither of them anything.
        """
        from gtmbase import push_conditions

        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            reasons = push_conditions.check(base_id, "some-session")
            codes = [code for code, _sentence in reasons]

            self.assertIn(push_conditions.CODE_FIRST_PUSH, codes)

            from gtmbase import marker

            marker.write_sources_read_marker("some-session")
            codes = [
                code
                for code, _sentence in push_conditions.check(base_id, "some-session")
            ]
            self.assertIn(push_conditions.CODE_SOURCES_READ, codes)

            # And approving a change locally asks neither of them anything: it
            # runs to the end on a base where both conditions say no.
            staged = stage(root)
            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status)


# --- A base that does have a shared copy -------------------------------------


class TestABaseThatHasSomewhereToSendIt(unittest.TestCase):
    def test_this_path_refuses_and_points_at_the_one_that_ships(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            staged = stage(root)

            shown = approve_local.show(staged, root, base_id, now=TODAY)
            applied = approve_local.approve(staged, root, base_id, "anything", now=NOW)

            for result in (shown, applied):
                self.assertEqual(approve_local.STATUS_REFUSED, result.status)
                self.assertEqual([approve_local.CODE_HAS_SHARED_COPY], result.codes)
                self.assertIn("propose-change", result.reasons[0])
            self.assertTrue(os.path.isfile(staged))
            self.assertEqual([], corrections_in(root))


# --- The handoff from the path that sends ------------------------------------


class TestTheHandoffFromProposing(unittest.TestCase):
    def test_a_base_with_no_shared_copy_keeps_the_change_and_says_so(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            result = compose_proposal.propose(
                staged, root, base_id, gh=support.RecordingGh(), now=TODAY,
                session_id="sess-1", runner=NoRemoteRunner(),
            )

            self.assertEqual(compose_proposal.STATUS_APPROVE_HERE, result.status)
            self.assertEqual([compose_proposal.CODE_NO_REMOTE], result.codes)
            self.assertEqual([compose_proposal.APPROVE_HERE], result.reasons)
            self.assertIn("approve it here", result.reasons[0])
            self.assertTrue(os.path.isfile(staged))

    def test_the_handoff_comes_before_the_first_backup_refusal(self):
        """The one real base has both problems, so the order is what matters."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            seat, _problems = state.load_seat(base_id)
            self.assertFalse(seat.get("first_push_reviewed"))
            staged = stage(root)

            result = compose_proposal.propose(
                staged, root, base_id, gh=support.RecordingGh(), now=TODAY,
                session_id="sess-1", runner=NoRemoteRunner(),
            )

            self.assertEqual(compose_proposal.STATUS_APPROVE_HERE, result.status)
            self.assertNotIn("first", " ".join(result.codes))


# --- What the stale check says -----------------------------------------------


class TestTheStaleCheckListsWhatIsWaiting(unittest.TestCase):
    def test_a_prepared_change_waiting_is_listed_by_the_name_of_its_document(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            stage(root)

            result = stale_check.run(
                root, base_id, runner=NoRemoteRunner(), gh=support.RecordingGh(),
                now=TODAY, session_id="sess-1",
            )

            expected = stale_check.AWAITING_LOCAL_APPROVAL % names.document_name(ICP)
            self.assertIn(expected, result.lines())

    def test_nothing_is_said_when_no_prepared_change_is_waiting(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)

            result = stale_check.run(
                root, base_id, runner=NoRemoteRunner(), gh=support.RecordingGh(),
                now=TODAY, session_id="sess-1",
            )

            for line in result.lines():
                self.assertNotIn("waiting for you to approve", line)

    def test_a_base_with_a_shared_copy_is_not_told_to_approve_anything_here(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            stage(root)

            result = stale_check.run(
                root, base_id, gh=support.RecordingGh(), now=TODAY, session_id="sess-1"
            )

            for line in result.lines():
                self.assertNotIn("waiting for you to approve", line)


# --- The skill and its reference ---------------------------------------------


class TestTheWordsAPersonReads(unittest.TestCase):
    def test_the_skill_and_its_reference_pass_the_whole_standard(self):
        for name in ("SKILL.md", "references/local-approval-rules.md"):
            path = os.path.join(SKILL_DIR, name.replace("/", os.sep))
            plain_language.assert_plain(self, path)
            plain_language.assert_standard(self, path)

    def test_the_local_approval_step_says_what_it_is_for_and_asks_one_thing(self):
        text = support.read(os.path.join(SKILL_DIR, "SKILL.md"))
        titles = [step.title for step in plain_language.find_steps(text)]
        self.assertIn(
            "Approving a prepared change here, when the base has no shared copy",
            titles,
        )
        self.assertIn(plain_language.ASK_OPEN, text)
        self.assertIn(approve_local.ASK, text)

    def test_every_new_sentence_is_written_in_the_words_of_the_product(self):
        """Nothing a person reads here calls a context change a decision."""
        for constant in (
            approve_local.HAS_SHARED_COPY,
            approve_local.NOT_WAITING_HERE,
            approve_local.MARKER_DISAGREES,
            approve_local.ALREADY_RECORDED,
            approve_local.NOTE_UNREADABLE,
            compose_proposal.CANNOT_TELL,
            approve_local.CONFLICT,
            approve_local.MOVED,
            approve_local.APPLIED,
            approve_local.KEPT,
            approve_local.DROPPED,
            approve_local.ASK,
            approve_local.OUTSIDE_THE_FOLDERS,
            compose_proposal.APPROVE_HERE,
            stale_check.AWAITING_LOCAL_APPROVAL,
        ):
            self.assertNotIn("decision", constant.lower(), constant)
            self.assertEqual([], plain_language.find_banned(constant), constant)
            self.assertEqual([], plain_language.find_dashes(constant), constant)


# --- The shim ----------------------------------------------------------------


class TestTheScript(unittest.TestCase):
    def test_it_carries_the_shared_loader_unchanged(self):
        template = support.read(
            os.path.join(support.PLUGIN_DIR, "scripts", "_shim_template.py")
        )
        start = template.index("# --- gtm-base shim (copy from here) ---")
        end = template.index("# --- end of shim ---") + len("# --- end of shim ---")
        script = support.read(
            os.path.join(SKILL_DIR, "scripts", "approve_local.py")
        )
        self.assertIn(template[start:end], script)

    def test_it_says_what_is_waiting_without_writing_anything(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            stage(root)

            waiting = approve_local.waiting(root)

            self.assertEqual([(STAGING, [ICP])], waiting)
            self.assertEqual("", support.status_of(root))
            del base_id


# --- The whole way through, on a base built the way one really is built ------


LATER = datetime.date(2026, 6, 12)
LATER_NOW = datetime.datetime(2026, 6, 12, 9, 0, 0)
HAND_ENTERED = "stg-" + "b" * 16

ICP_DRAFT = """---
kind: icp
owner: owner@example.com
last_confirmed: 2026-06-05
sources: []
status: draft
---

# Ideal customer profile

## Firmographics

Companies of any size.
"""

CHANGE_BY_HAND = """---
id: %s
kind: decision
decided_on: 2026-06-10
written_on: 2026-06-10
decided_by: owner@example.com
source: the weekly go to market meeting
affects: [context/strategy/icp.md]
review_by: 2026-09-10
origin: ledger
status: open
---

We now sell to companies of twenty to two hundred people. The Firmographics
section is the one that has to change.
""" % HAND_ENTERED


class TestTheWholeWayThroughOnARealBase(unittest.TestCase):
    """Built by the code that really builds a base, with nothing standing in.

    There is no shared copy anywhere in this scenario and nothing pretending to
    be one, because that is the base this whole path exists for.
    """

    def build(self):
        from gtmbase import create_base

        support.write(
            os.path.join(os.environ["HOME"], ".gitconfig"),
            "[user]\n\temail = %s\n\tname = Test Owner\n" % OWNER,
        )
        parent = os.path.join(os.environ["HOME"], "marketing")
        support.write(os.path.join(parent, "positioning.md"), "# Positioning\n")
        result = create_base.create(
            parent,
            create_base.ApprovedFile(ICP, ICP_DRAFT),
            ids.run_id(TODAY),
            support.PLUGIN_DIR,
            runner=NoRemoteRunner(),
            now=NOW,
            name="Acme",
        )
        return result.root, result.base_id

    def test_a_change_entered_by_hand_ends_applied_confirmed_and_counted(self):
        with support.Sandbox():
            root, base_id = self.build()
            runner = NoRemoteRunner()
            self.assertIsNone(paths.remote_url(root, runner=runner))

            # A context change the person wrote down themselves.
            support.write(
                os.path.join(root, constants.CHANGES_DIR, HAND_ENTERED + ".md"),
                CHANGE_BY_HAND,
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a change I wrote down"], cwd=root)
            saved_before = commit_count(root)

            # The flag, and the change prepared from it.
            flagged = stale_check.run(
                root, base_id, runner=runner, gh=support.RecordingGh(),
                now=LATER, session_id="sess-1",
            )
            self.assertEqual(1, len(flagged.staged), flagged.lines())
            staged = flagged.staged[0].path
            self.assertIn(
                stale_check.AWAITING_LOCAL_APPROVAL % names.document_name(ICP),
                flagged.lines(),
            )
            self.assertEqual(
                [ICP], [flag.path for flag in flagged.report.file_flags]
            )

            # The assistant writes the real wording into the prepared change
            # first, because the note GTM Base wrote asking for it is not
            # something anybody may approve (finding A6, 2026-09-20).
            support.write_the_replacement(
                staged, "We sell to companies of twenty to two hundred people.\n"
            )

            # The owner reads the whole change and says yes.
            shown = approve_local.show(staged, root, base_id, runner=runner, now=LATER)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn(approve_local.CHANGE_OPEN, shown.artifact)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=LATER_NOW
            )
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )

            # The file changed, and one line records the yes against the change.
            self.assertNotIn(
                "Companies of any size.", support.read(os.path.join(root, ICP))
            )
            line = confirmations_of(root)[-1]
            self.assertEqual("ledger", line.trigger)
            self.assertEqual(HAND_ENTERED, line.entry)
            self.assertEqual(LATER.isoformat(), line.date)

            # One piece of saved work holds it, and nothing is left unsaved.
            self.assertEqual(saved_before + 1, commit_count(root))
            self.assertEqual("", support.status_of(root))

            # The record of what changed is there, and the numbers count it.
            self.assertEqual(1, len(corrections_in(root)))
            summary = report.four_week_summary(
                root, base_id, runner=runner, gh=support.RecordingGh(), today=LATER
            )
            self.assertEqual(1, summary["catches"]["records_in_window"])

            # The flag is gone, and nothing is waiting to be approved.
            after = stale_check.run(
                root, base_id, runner=runner, gh=support.RecordingGh(),
                now=LATER, session_id="sess-1",
            )
            self.assertEqual([], [flag.path for flag in after.report.file_flags])
            self.assertEqual([], approve_local.waiting(root))
            self.assertFalse(os.path.isfile(staged))

            # And the base still has nowhere to send anything.
            seat, _problems = state.load_seat(base_id)
            self.assertFalse(seat.get("first_push_reviewed"))
            self.assertIsNone(paths.remote_url(root, runner=runner))


# --- Building a prepared change by hand --------------------------------------


def custom_staging(
    staging_id=STAGING,
    edits=None,
    decision=None,
    entry_id=None,
    source_id=None,
    why="The team decided this and the document was never brought in line.",
    before="The profile says we sell to companies of any size.",
    after="The profile says we sell to companies of twenty to two hundred people.",
    excerpt="so from now on we only go after companies of that size",
):
    """One prepared change, written the way another skill would have left it."""
    edits = list(edits or [formats.Edit(ICP, "## Firmographics", "replace", "Bigger.\n")])
    body = formats.render_pr_body(
        {
            "before": before,
            "after": after,
            "why": why,
            "evidence": excerpt,
            "confidence": "high",
            "rule_changed": "None",
            "marker": marker_line(staging_id, entry_id, source_id),
        }
    )
    targets = []
    for edit in edits:
        if edit.path not in targets:
            targets.append(edit.path)
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin="ledger",
        intake_path="ledger",
        target_paths=targets,
        sequence=0,
        rule_change=False,
        confidence="high",
        third_party=False,
        pr_body=body,
        source_id=source_id,
        decision_block=decision,
        edits=edits,
        excerpt=excerpt,
    )
    return staging.validate().render()


def entry_block(entry_id=STAGING, affects=(ICP,), body="We now sell to bigger companies."):
    return formats.LedgerEntry(
        id=entry_id,
        decided_on="2026-06-01",
        written_on="2026-06-02",
        decided_by=OWNER,
        source="the weekly go to market meeting",
        review_by="2026-09-01",
        origin="ledger",
        status="open",
        affects=list(affects),
        body=body,
    ).render()


class FailingRunner(NoRemoteRunner):
    """The runner, with one named command answering as though it went wrong."""

    def __init__(self, fail_on):
        NoRemoteRunner.__init__(self)
        self.fail_on = list(fail_on)

    def _is_the_one(self, args):
        arguments = [str(item) for item in args]
        return arguments[: len(self.fail_on)] == self.fail_on

    def run(self, args, cwd=None, timeout=20, input=None):
        if self._is_the_one(args):
            self._check(args)
            return GitResult(128, "", "it could not be read")
        return NoRemoteRunner.run(self, args, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        from gtmbase.errors import GitError

        if self._is_the_one(args):
            self._check(args)
            raise GitError("git-failed", code="git-failed")
        return NoRemoteRunner.check(self, args, cwd=cwd, timeout=timeout, input=input)


def stop_once(root, base_id, staged, runner, target="_save_the_work"):
    """Run it until it stops at a named step, and leave the note behind."""
    shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
    with mock.patch.object(approve_local, target, side_effect=RuntimeError("stopped")):
        try:
            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
        except RuntimeError:
            pass
    return shown


# --- S-H2 and C8: where a prepared change may be read from -------------------


class TestWhereAPreparedChangeMayBeReadFrom(unittest.TestCase):
    """A prepared change is only ever read from the one folder they wait in."""

    def elsewhere(self, sandbox, root):
        path = os.path.join(sandbox.path, "somewhere", "else.md")
        support.write(
            path,
            support.read(os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")),
        )
        del root
        return path

    def test_showing_one_from_anywhere_else_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            outside = self.elsewhere(sandbox, root)

            shown = approve_local.show(
                outside, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NOT_WAITING_HERE], shown.codes)
            self.assertTrue(os.path.isfile(outside))

    def test_approving_one_from_anywhere_else_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            outside = self.elsewhere(sandbox, root)

            applied = approve_local.approve(
                outside, root, base_id, "anything", runner=NoRemoteRunner(), now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.CODE_NOT_WAITING_HERE], applied.codes)
            self.assertEqual([], corrections_in(root))

    def test_dropping_one_from_anywhere_else_deletes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            mine = os.path.join(root, ICP)

            result = approve_local.drop(mine, root, base_id)

            self.assertEqual(approve_local.STATUS_REFUSED, result.status)
            self.assertEqual([approve_local.CODE_NOT_WAITING_HERE], result.codes)
            self.assertTrue(os.path.isfile(mine))

    def test_dropping_something_that_is_not_a_prepared_change_deletes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            path = os.path.join(
                root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md"
            )
            support.write(path, "this is not a prepared change at all\n")

            result = approve_local.drop(path, root, base_id)

            self.assertEqual(approve_local.STATUS_REFUSED, result.status)
            self.assertTrue(os.path.isfile(path))

    def test_a_name_that_is_not_an_identifier_we_issue_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            path = os.path.join(root, constants.PROPOSALS_PENDING_DIR, "notes.md")
            support.write(
                path,
                support.read(
                    os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
                ),
            )

            result = approve_local.drop(path, root, base_id)

            self.assertEqual(approve_local.STATUS_REFUSED, result.status)
            self.assertTrue(os.path.isfile(path))

    def test_a_dropped_change_is_not_prepared_again_by_the_next_check(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            result = approve_local.drop(staged, root, base_id)

            self.assertEqual(approve_local.STATUS_DROPPED, result.status)
            self.assertFalse(os.path.isfile(staged))
            self.assertEqual([], approve_local.waiting(root))
            self.assertTrue(
                stale_check._staging_exists(root, STAGING),
                "a dropped change still has to be recognised as done with",
            )


# --- C1 and S-L2: undoing only what this run wrote ---------------------------


class TestUndoingOnlyWhatThisRunWrote(unittest.TestCase):
    def test_an_edit_to_a_file_the_note_names_stops_the_run_and_survives(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = stop_once(root, base_id, staged, runner)

            mine = "# Ideal customer profile\n\n## Firmographics\n\nMy own words.\n"
            support.write(os.path.join(root, ICP), mine)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.UNSAVED_EDITS], applied.reasons)
            self.assertEqual(mine, support.read(os.path.join(root, ICP)))
            self.assertEqual([], corrections_in(root))
            self.assertIsNotNone(approve_local._load_journal(base_id))


# --- S-M1: the note is read as data, not trusted -----------------------------


class TestTheNoteIsNotTrusted(unittest.TestCase):
    def note(self, base_id, **fields):
        from gtmbase.fsutil import atomic_write_json

        payload = {
            "schema": approve_local.JOURNAL_SCHEMA,
            "staging_id": STAGING,
            "subject": "Approved prepared change %s: something" % STAGING,
            "head": "0" * 40,
            "paths": [],
        }
        payload.update(fields)
        atomic_write_json(approve_local._journal_path(base_id), payload)

    def test_a_note_naming_a_path_outside_the_base_touches_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            outside = os.path.join(sandbox.path, "theirs.md")
            support.write(outside, "somebody else's file\n")
            staged = stage(root)
            self.note(
                base_id,
                base_root=os.path.realpath(root),
                paths=[
                    {"path": "../../theirs.md", "hash": "0" * 64, "in_head": False},
                    {"path": outside, "hash": "0" * 64, "in_head": False},
                ],
            )

            applied = approve_local.approve(
                staged, root, base_id, "anything", runner=NoRemoteRunner(), now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.CODE_NOTE_UNREADABLE], applied.codes)
            self.assertTrue(os.path.isfile(outside))

    def test_a_note_about_another_base_touches_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            self.note(
                base_id,
                base_root=os.path.join(sandbox.path, "another"),
                paths=[{"path": ICP, "hash": "0" * 64, "in_head": True}],
            )

            applied = approve_local.approve(
                staged, root, base_id, "anything", runner=NoRemoteRunner(), now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.CODE_NOTE_UNREADABLE], applied.codes)
            self.assertIn(
                "Companies of any size.", support.read(os.path.join(root, ICP))
            )

    def test_a_note_naming_an_identifier_we_never_issued_touches_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            self.note(
                base_id,
                staging_id="../../../etc/passwd",
                base_root=os.path.realpath(root),
                paths=[],
            )

            applied = approve_local.approve(
                staged, root, base_id, "anything", runner=NoRemoteRunner(), now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.CODE_NOTE_UNREADABLE], applied.codes)


class TestAPlaceholderIsNeverApprovable(unittest.TestCase):
    """Finding A6 of the 2026-09-20 review, on a change that names a heading.

    The first draft GTM Base writes into a prepared change says "Update
    needed" and repeats the change back. Approving it used to put that note
    into the document and clear the flag, leaving the claim that had gone out
    of date exactly where it was. This is the scenario where the change names
    a heading the document holds, so the words really do go over something,
    and what has to be true afterwards is that the obsolete claim is gone and
    the approved wording is there in its place.
    """

    OBSOLETE = "Companies of any size."

    def a_change_about_the_firmographics(self, root):
        entry = "\n".join(
            [
                "---",
                "id: %s" % OTHER_STAGING,
                "kind: decision",
                "decided_on: 2026-06-02",
                "written_on: 2026-06-03",
                "decided_by: Jane Doe",
                "source: the weekly go to market meeting",
                "affects: [%s]" % ICP,
                "review_by: 2026-09-01",
                "origin: manual",
                "status: open",
                "---",
                "",
                "The Firmographics section is wrong now. We stopped selling to",
                "companies under twenty people.",
                "",
            ]
        )
        support.write(
            os.path.join(root, constants.CHANGES_DIR, OTHER_STAGING + ".md"), entry
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a context change"], cwd=root)

    def test_the_note_is_refused_and_the_replacement_takes_the_claim_away(self):
        with support.Sandbox() as sandbox:
            runner = NoRemoteRunner()
            root, base_id = local_base(sandbox)
            self.assertIn(self.OBSOLETE, support.read(os.path.join(root, ICP)))
            self.a_change_about_the_firmographics(root)

            run = stale_check.run(
                root,
                base_id,
                runner=runner,
                gh=support.RecordingGh(),
                now=TODAY,
                session_id="sess-1",
            )
            prepared = [item for item in run.staged if item.entry_id == OTHER_STAGING]
            self.assertEqual(1, len(prepared), run.lines())
            staged = prepared[0].path

            # It really does go over the section holding the obsolete claim.
            staging = compose_proposal.load_staging(staged)
            self.assertEqual("replace", staging.edits[0].op)
            self.assertIn(
                self.OBSOLETE,
                support.the_section_now(root, ICP, staging.edits[0].heading),
            )

            refused = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_REFUSED, refused.status)
            self.assertEqual(
                [approve_local.CODE_STILL_A_PLACEHOLDER], refused.codes
            )

            replacement = "Companies of twenty to two hundred people.\n"
            support.write_the_replacement(staged, replacement)

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )

            now_says = support.read(os.path.join(root, ICP))
            self.assertNotIn(self.OBSOLETE, now_says)
            self.assertNotIn("Update needed", now_says)
            self.assertIn(replacement.strip(), now_says)


class TestTheForgedNoteTheReviewersWrote(unittest.TestCase):
    """Finding H4, reproduced three ways and fixed three ways.

    A note is a file in this seat's own folder like any other, and before the
    2026-09-20 review nothing ran before a file write, so anybody who could get
    the assistant to write one file could write this one. What the reviewers
    got out of it was a prepared change dropped and reported as approved
    without anybody reading it, and a saved point handed to git that made git
    write a file of the attacker's choosing.
    """

    def note(self, base_id, **fields):
        from gtmbase.fsutil import atomic_write_json

        payload = {
            "schema": approve_local.JOURNAL_SCHEMA,
            "staging_id": STAGING,
            "subject": "a context change",
            "head": "0" * 40,
            "paths": [],
        }
        payload.update(fields)
        atomic_write_json(approve_local._journal_path(base_id), payload)

    def saved_point_before_a_change_elsewhere(self, root):
        head = support.git(
            ["rev-parse", "HEAD"], cwd=root
        ).stdout.decode("utf-8").strip()
        support.write(os.path.join(root, "context", "notes.md"), "# Notes\n")
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a context change"], cwd=root)
        return head

    def test_a_note_listing_no_paths_at_all_is_refused(self):
        """It said the run wrote nothing, so undoing it undid nothing, and the
        prepared change was dropped and reported applied all the same."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            head = self.saved_point_before_a_change_elsewhere(root)
            staged = stage(root)
            self.note(base_id, base_root=os.path.realpath(root), head=head, paths=[])

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NOTE_UNREADABLE], shown.codes)
            self.assertTrue(os.path.isfile(staged))

    def test_a_saved_point_that_is_not_one_is_refused_before_git_sees_it(self):
        """The reviewers wrote an option there, and git made a file of it."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            written_by_git = os.path.join(sandbox.path, "written-by-git")
            self.note(
                base_id,
                base_root=os.path.realpath(root),
                head="--output=" + written_by_git,
                paths=[{"path": ICP, "hash": "0" * 64, "in_head": True}],
            )

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NOTE_UNREADABLE], shown.codes)
            self.assertEqual(
                [],
                [
                    name
                    for name in os.listdir(sandbox.path)
                    if name.startswith("written-by-git")
                ],
            )

    def test_work_counts_as_saved_only_when_it_touched_the_noted_paths(self):
        """A subject matching any saved work since the noted point was enough,
        so a note naming a change nobody had read reported it applied."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            head = self.saved_point_before_a_change_elsewhere(root)
            staged = stage(root)
            self.note(
                base_id,
                base_root=os.path.realpath(root),
                head=head,
                paths=[{"path": ICP, "hash": "0" * 64, "in_head": True}],
            )

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            # The saved work carrying the noted subject touched another file,
            # so this run's own work was never saved, and the prepared change
            # is still waiting for somebody to read it.
            self.assertNotEqual(approve_local.STATUS_APPLIED, shown.status)
            self.assertTrue(os.path.isfile(staged))

    def test_work_that_really_was_saved_is_still_finished_off(self):
        """The other half: a run that stopped after saving still resumes."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            head = support.git(
                ["rev-parse", "HEAD"], cwd=root
            ).stdout.decode("utf-8").strip()
            support.write(
                os.path.join(root, ICP.replace("/", os.sep)),
                support.read(os.path.join(root, ICP)) + "\nSomething new.\n",
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a context change"], cwd=root)
            staged = stage(root)
            self.note(
                base_id,
                base_root=os.path.realpath(root),
                head=head,
                paths=[
                    {
                        "path": ICP,
                        "hash": ids.content_hash(
                            support.read(os.path.join(root, ICP))
                        ),
                        "in_head": True,
                    }
                ],
            )

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_APPLIED, shown.status)
            self.assertIn(approve_local.CODE_RESUMED, shown.codes)


# --- S-M2: not knowing is not the same as not having -------------------------


class TestTellingNoSharedCopyFromNotKnowing(unittest.TestCase):
    def test_a_base_whose_settings_cannot_be_read_is_not_called_one_without(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            shown = approve_local.show(
                staged, root, base_id, runner=FailingRunner(["remote"]), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_CANNOT_TELL], shown.codes)

    def test_the_path_that_sends_says_the_same_thing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            result = compose_proposal.propose(
                staged, root, base_id, gh=support.RecordingGh(), now=TODAY,
                session_id="sess-1", runner=FailingRunner(["remote"]),
            )

            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertEqual([compose_proposal.CODE_CANNOT_TELL], result.codes)

    def test_a_base_that_really_has_none_is_still_told_apart(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)

            self.assertEqual(
                compose_proposal.SHARED_COPY_ABSENT,
                compose_proposal.shared_copy_state(root, runner=NoRemoteRunner()),
            )

    def test_a_base_that_has_one_is_told_apart_too(self):
        with support.Sandbox() as sandbox:
            root, _base_id, _remote = support.base_with_a_shared_copy(sandbox)

            self.assertEqual(
                compose_proposal.SHARED_COPY_PRESENT,
                compose_proposal.shared_copy_state(root),
            )


# --- S-M3 and C2: what is shown is what is written ---------------------------


class TestWhatIsShownIsWhatIsWritten(unittest.TestCase):
    def shown_for(self, root, base_id, text):
        staged = stage(root, text=text)
        return staged, approve_local.show(
            staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
        )

    def test_the_whole_context_change_is_shown_as_it_will_be_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            body = (
                "We now sell to companies of twenty to two hundred people, and we "
                "have stopped calling on anyone smaller, because the last four of "
                "those took the longest to close and left the soonest, which is a "
                "sentence long enough to be cut short by anything that shortens."
            )
            _staged, shown = self.shown_for(
                root,
                base_id,
                custom_staging(decision=entry_block(body=body), entry_id=STAGING),
            )

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            for piece in body.split(", "):
                self.assertIn(piece, shown.artifact)
            self.assertIn("happened_on: 2026-06-01", shown.artifact)

    def test_the_full_reason_is_shown_and_never_cut_short(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            why = "Because " + ("of the way this keeps going on and on, " * 12)
            _staged, shown = self.shown_for(root, base_id, custom_staging(why=why))

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn(why.strip().rstrip(","), shown.artifact)
            self.assertNotIn("...", shown.artifact.split("What it affects:")[0])

    def test_what_it_affects_names_everything_the_change_affects(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            other = "context/strategy/positioning.md"
            support.write(
                os.path.join(root, other),
                support.read(os.path.join(root, ICP)).replace("icp", "positioning"),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "positioning"], cwd=root)
            _staged, shown = self.shown_for(
                root,
                base_id,
                custom_staging(
                    decision=entry_block(affects=(ICP, other)), entry_id=STAGING
                ),
            )

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            affects = [
                line
                for line in shown.artifact.splitlines()
                if line.startswith("What it affects:")
            ][0]
            self.assertIn(names.document_name(ICP), affects)
            self.assertIn(names.document_name(other), affects)

    def test_an_added_part_is_shown_as_the_file_will_really_read(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = custom_staging(
                edits=[
                    formats.Edit(
                        ICP, "## How they buy", "add", "They buy in committees.\n"
                    )
                ]
            )
            staged, shown = self.shown_for(root, base_id, text)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn("They buy in committees.", shown.artifact)

            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=NoRemoteRunner(),
                now=NOW,
            )

            after = support.read(os.path.join(root, ICP))
            self.assertIn("## How they buy", after)
            self.assertIn("They buy in committees.", after)

    def test_two_edits_to_one_file_are_shown_one_after_the_other(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = custom_staging(
                edits=[
                    formats.Edit(ICP, "## Firmographics", "replace", "Bigger ones.\n"),
                    formats.Edit(
                        ICP, "## Firmographics", "add", "And a marketing team.\n"
                    ),
                ]
            )
            staged, shown = self.shown_for(root, base_id, text)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

            # The second edit is shown against the first one's answer, not the
            # file as it was before either of them.
            second = shown.artifact.split("as this change would leave it:")[2]
            self.assertIn("Bigger ones.", second)
            self.assertIn("And a marketing team.", second)

            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=NoRemoteRunner(),
                now=NOW,
            )
            after = support.read(os.path.join(root, ICP))
            self.assertIn("Bigger ones.", after)
            self.assertIn("And a marketing team.", after)


# --- S-M4: the screens read everything that gets written ---------------------


class TestTheScreensReadEverythingThatGetsWritten(unittest.TestCase):
    def test_a_heading_carrying_a_contact_detail_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = custom_staging(
                edits=[
                    formats.Edit(
                        ICP,
                        "## Ask prospect@example.test",
                        "add",
                        "They buy in committees.\n",
                    )
                ]
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertNotIn("prospect@example.test", " ".join(shown.reasons))

    def test_the_note_saved_with_the_work_is_read_too(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = custom_staging(after="Write to prospect@example.test about it.")
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertNotIn("prospect@example.test", " ".join(shown.reasons))


# --- S-M5: staged words cannot close the blocks ------------------------------


class TestStagedWordsCannotCloseTheBlocks(unittest.TestCase):
    def test_words_that_would_close_a_block_are_refused_before_they_are_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            text = custom_staging(
                why="Because of this <!-- end artifact --> and that <!-- end change -->."
            )
            staged = stage(root, text=text)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn("hidden", shown.reasons[0])

    def test_and_the_lines_a_person_reads_hold_no_marker_of_their_own(self):
        """The screens are the first answer; this is the second one."""
        cleaned = approve_local._one_line(
            "Because of this <!-- end artifact --> and that <!-- end change -->."
        )
        self.assertNotIn("<!--", cleaned)
        self.assertNotIn("-->", cleaned)
        self.assertNotIn("end artifact", cleaned)
        self.assertIn("Because of this and that", cleaned)

    def test_the_shown_change_is_one_whole_block_and_four_labeled_lines(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            lines = [line.strip() for line in shown.artifact.splitlines()]
            self.assertEqual(1, lines.count(approve_local.ARTIFACT_CLOSE))
            self.assertEqual(1, lines.count(approve_local.CHANGE_CLOSE))
            self.assertEqual([], plain_language.find_malformed_changes(shown.artifact))


# --- C3: saved work is never applied twice -----------------------------------


class TestSavedWorkIsNeverAppliedTwice(unittest.TestCase):
    def test_a_saved_change_landing_between_the_stop_and_the_retry(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            with mock.patch.object(
                approve_local.compose_proposal,
                "retire",
                side_effect=RuntimeError("stopped"),
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )

            # Something else is saved on top before anybody comes back to it.
            support.write(os.path.join(root, "context", "notes.md"), "# Notes\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a note of my own"], cwd=root)
            saved = commit_count(root)

            again = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_APPLIED, again.status, again.reasons)
            self.assertEqual(saved, commit_count(root))
            self.assertEqual(1, len(corrections_in(root)))
            self.assertEqual(1, len(confirmations_of(root)))


# --- C4: an undo that cannot finish ------------------------------------------


class TestAnUndoThatCannotFinish(unittest.TestCase):
    def test_the_note_is_kept_and_the_run_says_it_could_not(self):
        """The record this run wrote cannot be taken off the list again.

        This used to make the command that puts a file back the way it was last
        saved fail. Since finding V4 that command is not how a document comes
        back, because the bytes kept before the run started are, so the command
        this stops is the one that takes a newly written record off the list.
        """
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            shown = stop_once(root, base_id, staged, NoRemoteRunner())

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash,
                runner=FailingRunner(["rm"]), now=NOW,
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.COULD_NOT_SAVE], applied.reasons)
            self.assertIsNotNone(approve_local._load_journal(base_id))

    def test_a_kept_copy_that_is_gone_stops_the_run_rather_than_guessing(self):
        """V4. Nothing is put back from anywhere but the bytes that were kept."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            shown = stop_once(root, base_id, staged, NoRemoteRunner())
            import shutil as _shutil

            _shutil.rmtree(approve_local._originals_dir(base_id))

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash,
                runner=NoRemoteRunner(), now=NOW,
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.COULD_NOT_SAVE], applied.reasons)
            self.assertIsNotNone(approve_local._load_journal(base_id))


# --- C5: the marker and the change entry have to agree -----------------------


class TestTheMarkerAndTheChangeEntryHaveToAgree(unittest.TestCase):
    def test_an_entry_its_own_marker_does_not_name_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root, text=custom_staging(decision=entry_block(), entry_id=None))

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_MARKER_DISAGREES], shown.codes)
            self.assertEqual([], corrections_in(root))

    def test_a_marker_naming_an_entry_that_is_not_carried_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root, text=custom_staging(entry_id=STAGING))

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn(compose_proposal.CODE_MARKER_ENTRY, shown.codes)


# --- S-L3: only once ---------------------------------------------------------


class TestOnlyOnce(unittest.TestCase):
    def test_a_change_already_recorded_here_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            show_and_approve(root, base_id, staged, NoRemoteRunner())
            again = stage(root)

            shown = approve_local.show(
                again, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_ALREADY_RECORDED], shown.codes)
            self.assertEqual(1, len(corrections_in(root)))


# --- C6: the day it is recorded on -------------------------------------------


class TestTheDayItIsRecordedOn(unittest.TestCase):
    def test_a_day_given_on_its_own_is_the_day_that_is_recorded(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertEqual(TODAY.isoformat(), confirmations_of(root)[-1].date)
            self.assertEqual(
                ["%s-%s.md" % (TODAY.isoformat(), STAGING)], corrections_in(root)
            )


# --- C7: showing and dropping see an unfinished run --------------------------


class TestShowingAndDroppingSeeAnUnfinishedRun(unittest.TestCase):
    def test_showing_finishes_a_run_that_was_saved_and_stopped(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            first = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            with mock.patch.object(
                approve_local.compose_proposal,
                "retire",
                side_effect=RuntimeError("stopped"),
            ):
                with self.assertRaises(RuntimeError):
                    approve_local.approve(
                        staged, root, base_id, first.shown_hash, runner=runner, now=NOW
                    )

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(approve_local.STATUS_APPLIED, shown.status)
            self.assertIsNone(approve_local._load_journal(base_id))

    def test_dropping_puts_back_what_a_stopped_run_wrote_first(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            stop_once(root, base_id, staged, NoRemoteRunner())

            result = approve_local.drop(staged, root, base_id)

            self.assertEqual(approve_local.STATUS_DROPPED, result.status)
            self.assertEqual("", support.status_of(root))
            self.assertEqual([], corrections_in(root))
            self.assertIsNone(approve_local._load_journal(base_id))


# --- C10: what is listed can actually be approved ----------------------------


class TestWhatIsListedCanActuallyBeApproved(unittest.TestCase):
    def test_a_prepared_change_whose_file_is_gone_is_not_listed(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            stage(root)
            support.git(["rm", "-q", "--", ICP], cwd=root)
            support.git(["commit", "-q", "-m", "took it out"], cwd=root)

            self.assertEqual([], approve_local.waiting(root))
            del base_id

    def test_a_prepared_change_for_a_file_somebody_else_owns_is_not_listed(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            stage(root)
            support.git(
                ["config", "--local", "user.email", "someone@example.test"], cwd=root
            )

            self.assertEqual([], approve_local.waiting(root))
            del base_id

    def test_a_missing_file_is_reported_as_the_change_no_longer_fitting(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            support.git(["rm", "-q", "--", ICP], cwd=root)
            support.git(["commit", "-q", "-m", "took it out"], cwd=root)

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_CONFLICT, shown.status)
            self.assertEqual(
                [approve_local.CONFLICT % names.document_name(ICP)], shown.reasons
            )


# --- S-L5: the value that stands for what was shown --------------------------


class TestTheShownValue(unittest.TestCase):
    def test_the_same_bytes_split_another_way_are_not_the_same_value(self):
        first = approve_local._hash_of_parts(["ab", "c"])
        second = approve_local._hash_of_parts(["a", "bc"])
        self.assertNotEqual(first, second)


# --- The gaps the reviewers named --------------------------------------------


class TestAChangeTouchingTwoFiles(unittest.TestCase):
    def test_both_files_end_changed_and_confirmed_against_the_change(self):
        with support.Sandbox() as sandbox:
            from gtmbase import base_reader, stale

            root, base_id = local_base(sandbox)
            other = "context/strategy/positioning.md"
            support.write(
                os.path.join(root, other),
                support.read(os.path.join(root, ICP)).replace("icp", "positioning"),
            )
            support.write(
                os.path.join(root, constants.CHANGES_DIR, STAGING + ".md"),
                entry_block(affects=(ICP, other)),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a change and a second document"], cwd=root)
            staged = stage(
                root,
                staging_id=OTHER_STAGING,
                text=custom_staging(
                    staging_id=OTHER_STAGING,
                    entry_id=STAGING,
                    edits=[
                        formats.Edit(ICP, "## Firmographics", "replace", "Bigger.\n"),
                        formats.Edit(other, "## Firmographics", "replace", "Bolder.\n"),
                    ],
                ),
            )
            runner = NoRemoteRunner()

            _shown, applied = show_and_approve(root, base_id, staged, runner)

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertIn("Bigger.", support.read(os.path.join(root, ICP)))
            self.assertIn("Bolder.", support.read(os.path.join(root, other)))
            self.assertEqual(STAGING, confirmations_of(root, ICP)[-1].entry)
            self.assertEqual(STAGING, confirmations_of(root, other)[-1].entry)
            self.assertEqual(1, len(corrections_in(root)))

            inputs = base_reader.read_base(root, base_id, runner=runner, today=TODAY)
            report_now = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
                owner_email=None,
            )
            self.assertEqual([], [flag.path for flag in report_now.file_flags])


class TestAFileWhoseLinesEndTheOtherWay(unittest.TestCase):
    def test_it_is_applied_and_the_value_shown_still_matches(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            full = os.path.join(root, ICP)
            as_it_was = support.read(full)
            with open(full, "w", encoding="utf-8", newline="") as handle:
                handle.write(as_it_was.replace("\n", "\r\n"))
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the other line ending"], cwd=root)
            staged = stage(root)

            _shown, applied = show_and_approve(root, base_id, staged, NoRemoteRunner())

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertIn("twenty to two hundred people", support.read(full))


class TestTheNumbersCountWhatApproveReallyWrote(unittest.TestCase):
    def test_a_change_approved_here_is_counted_as_one_gtm_base_caught(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            _shown, applied = show_and_approve(root, base_id, staged, NoRemoteRunner())
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)

            found = report.four_week_summary(
                root, base_id, runner=NoRemoteRunner(), gh=support.RecordingGh(),
                today=TODAY,
            )["catches"]

            self.assertEqual(1, found["count"])
            self.assertEqual([STAGING], [item["entry_id"] for item in found["entries"]])


class TestTheScriptRunsEveryAnswer(unittest.TestCase):
    """Every answer is run through the script itself, arguments and all.

    The one thing a test of the library alone cannot catch is the script
    calling it the wrong way, which is exactly what happened once.
    """

    def script(self):
        import importlib.util

        path = os.path.join(SKILL_DIR, "scripts", "approve_local.py")
        spec = importlib.util.spec_from_file_location("gtm_base_shim", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_in(self, root, arguments):
        import contextlib
        import io

        module = self.script()
        was = os.getcwd()
        os.chdir(support.where_a_script_runs(root))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    return module.main(arguments)
        finally:
            os.chdir(was)

    def test_it_lists_shows_leaves_and_drops(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            self.assertEqual(0, self.run_in(root, ["--list"]))
            self.assertEqual(0, self.run_in(root, ["--staging", staged, "--show"]))
            self.assertEqual(
                0, self.run_in(root, ["--staging", staged, "--not-yet"])
            )
            self.assertTrue(os.path.isfile(staged))
            self.assertEqual(0, self.run_in(root, ["--staging", staged, "--drop"]))
            self.assertFalse(os.path.isfile(staged))
            del base_id

    def test_a_yes_needs_the_value_the_showing_printed(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)

            self.assertEqual(
                2, self.run_in(root, ["--staging", staged, "--approve"])
            )
            self.assertEqual([], corrections_in(root))

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )
            code = self.run_in(
                root,
                ["--staging", staged, "--approve", "--shown", shown.shown_hash],
            )

            self.assertEqual(0, code)
            self.assertEqual(1, len(corrections_in(root)))


# --- V4 and V5 of the 2026-09-20 verification round --------------------------


HAND_EDIT_SOURCE = (
    "The quarterly review deck, slide four, said every customer we kept last "
    "year had between twenty and two hundred people."
)
BIGGER_COMPANIES = "Companies of twenty to two hundred people."


def a_second_section(root, body="Ten dollars a seat.\n"):
    """Give the customer profile a second part, saved, for the unrelated edit."""
    whole = support.read(os.path.join(root, ICP))
    support.write(os.path.join(root, ICP), whole + "\n## Pricing\n\n" + body)
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "pricing"], cwd=root)


def a_hand_edit(root, base_id, runner, words=BIGGER_COMPANIES):
    """The person edits the customer profile themselves, and it is prepared."""
    whole = support.read(os.path.join(root, ICP))
    support.write(
        os.path.join(root, ICP), whole.replace("Companies of any size.", words)
    )
    return compose_proposal.stage_local_edit(
        root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
    )


class TestAHandEditIsNeverLostWhenApprovalFails(unittest.TestCase):
    """V4. The rollback used to put the file back the way it was last saved.

    A change somebody made by hand is unsaved by definition, so putting the
    file back the way it was last saved throws their own words away. What has
    to come back is the bytes that were in front of them when they answered.
    """

    def failing_at(self, step):
        from gtmbase.errors import GitError

        return mock.patch.object(
            approve_local,
            step,
            side_effect=GitError("stopped", code=approve_local.CODE_GIT_FAILED),
        )

    def test_a_refused_save_leaves_their_own_words_byte_for_byte(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            theirs = support.read(os.path.join(root, ICP))
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

            with self.failing_at("_save_the_work"):
                applied = approve_local.approve(
                    staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual(
                theirs,
                support.read(os.path.join(root, ICP)),
                "the hand edit was not put back the way the person left it",
            )
            self.assertEqual([], corrections_in(root))

    def test_a_failure_at_every_step_leaves_their_own_words_byte_for_byte(self):
        for step in (
            "_write_the_files",
            "_stage_the_files",
            "_write_the_confirmation_lines",
            "_save_the_work",
        ):
            with support.Sandbox() as sandbox:
                root, base_id = local_base(sandbox)
                runner = NoRemoteRunner()
                staged = a_hand_edit(root, base_id, runner)
                theirs = support.read(os.path.join(root, ICP))
                shown = approve_local.show(
                    staged, root, base_id, runner=runner, now=TODAY
                )

                with self.failing_at(step):
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )

                self.assertEqual(
                    theirs, support.read(os.path.join(root, ICP)), step
                )

    def test_a_run_that_stopped_dead_puts_their_own_words_back_next_time(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            theirs = support.read(os.path.join(root, ICP))
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            with mock.patch.object(
                approve_local, "_save_the_work", side_effect=RuntimeError("stopped")
            ):
                try:
                    approve_local.approve(
                        staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                    )
                except RuntimeError:
                    pass

            approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(theirs, support.read(os.path.join(root, ICP)))


class TestOnlyAHandEditMayBeUnsaved(unittest.TestCase):
    """V5 and N8. Dirty target files were allowed for every prepared change."""

    def test_a_change_that_is_not_a_hand_edit_still_refuses_an_unsaved_target(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            runner = NoRemoteRunner()
            whole = support.read(os.path.join(root, ICP))
            support.write(
                os.path.join(root, ICP),
                whole.replace("Companies of any size.", "Companies I like."),
            )
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([approve_local.UNSAVED_EDITS], applied.reasons)
            self.assertEqual([], corrections_in(root))

    def test_the_whole_difference_is_what_a_hand_edit_is_approved_against(self):
        """Including what no part of the change is about.

        The settings at the top of a document are not a part of it that a
        change is ever described by, so nothing in the prepared change
        mentions this one. Saying yes saves it all the same, because what is
        saved is the document, so it has to be in what was shown.
        """
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            whole = os.path.join(root, ICP)
            support.write(
                whole,
                support.read(whole)
                .replace("Companies of any size.", BIGGER_COMPANIES)
                .replace("status: draft", "status: confirmed"),
            )
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            self.assertEqual(
                ["## Firmographics"],
                [one.heading for one in compose_proposal.load_staging(staged).edits],
                "the settings at the top are not described as a part",
            )

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn(
                "status: confirmed",
                shown.artifact,
                "a change no part of this one is about was not shown",
            )
            self.assertIn("status: draft", shown.artifact)

    def test_moving_anything_in_the_document_after_it_was_shown_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            a_second_section(root)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            whole = support.read(os.path.join(root, ICP))
            support.write(
                os.path.join(root, ICP),
                whole.replace("Ten dollars a seat.", "Twenty dollars a seat."),
            )

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_MOVED, applied.status)
            self.assertEqual([], corrections_in(root))



# --- H2 and L1 of the third look ---------------------------------------------


def bytes_of(path):
    """A file as it really is on the disk, with nothing translated."""
    with open(path, "rb") as handle:
        return handle.read()


def saved_bytes(root, relative):
    """One file as the base has saved it, with nothing translated."""
    finished = subprocess.run(
        ["git", "show", "HEAD:" + relative],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if finished.returncode != 0:
        raise AssertionError(finished.stderr.decode("utf-8", "replace"))
    return finished.stdout


class TestAHandEditThatMovedOnAgain(unittest.TestCase):
    """H2. The older prepared wording used to be saved over the newer work.

    Somebody edits a part of a document, the change is prepared from it, and
    then they keep working on the same part. What they were shown afterwards
    said two things at once: the prepared wording as what the change would
    leave, and their newer wording as what saying yes would write down. What
    it wrote was the older one, over the newer one, and the kept copy was
    thrown away because the run had succeeded.
    """

    def test_refining_the_same_part_again_stops_the_run(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            whole = os.path.join(root, ICP)
            support.write(
                whole,
                support.read(whole).replace(
                    BIGGER_COMPANIES,
                    "Companies of fifty to five hundred people, in logistics.",
                ),
            )
            theirs = bytes_of(whole)

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_MOVED, shown.status)
            self.assertEqual(
                [approve_local.PREPARED_FROM_OLDER % names.document_name(ICP)],
                shown.reasons,
            )
            self.assertEqual(theirs, bytes_of(whole))
            self.assertEqual([], corrections_in(root))

    def test_approving_it_writes_nothing_either(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            whole = os.path.join(root, ICP)
            support.write(
                whole,
                support.read(whole).replace(
                    BIGGER_COMPANIES,
                    "Companies of fifty to five hundred people, in logistics.",
                ),
            )
            theirs = bytes_of(whole)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_MOVED, applied.status)
            self.assertEqual(theirs, bytes_of(whole))
            self.assertEqual([], corrections_in(root))
            self.assertTrue(os.path.isfile(staged))


class TestWhatIsSavedIsWhatTheDifferenceShowed(unittest.TestCase):
    """H2. The whole difference is the promise, so it is held to the byte."""

    def test_one_document_is_saved_exactly_as_it_was_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            a_second_section(root)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            whole = os.path.join(root, ICP)
            theirs = bytes_of(whole)

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertEqual(theirs, saved_bytes(root, ICP))
            self.assertEqual(theirs, bytes_of(whole))

    def test_two_documents_are_saved_exactly_as_they_were_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            second = "context/strategy/positioning.md"
            support.write(
                os.path.join(root, second),
                support.ICP_TEXT.replace("kind: icp", "kind: positioning")
                .replace("# Ideal customer profile", "# Positioning")
                .replace("## Firmographics", "## Where we win"),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "positioning"], cwd=root)
            runner = NoRemoteRunner()

            for relative, words in (
                (ICP, "Companies of twenty to two hundred people."),
                (second, "Against the big suites, on setup time."),
            ):
                full = os.path.join(root, relative)
                support.write(
                    full,
                    support.read(full).replace("Companies of any size.", words),
                )
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            theirs = {
                relative: bytes_of(os.path.join(root, relative))
                for relative in (ICP, second)
            }

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            for relative in (ICP, second):
                self.assertEqual(theirs[relative], saved_bytes(root, relative))


class TestTheKeptCopyIsTheExactBytes(unittest.TestCase):
    """L1 and F4. It went through text, which translates line endings."""

    def a_document_whose_lines_end_the_other_way(self, root):
        full = os.path.join(root, ICP)
        with open(full, "r", encoding="utf-8") as handle:
            text = handle.read()
        with open(full, "w", encoding="utf-8", newline="") as handle:
            handle.write(text.replace("\n", "\r\n"))
        support.git(["-c", "core.autocrlf=false", "add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "the other line endings"], cwd=root)
        return full

    def test_a_failed_approval_gives_back_the_exact_bytes(self):
        from gtmbase.errors import GitError

        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            full = self.a_document_whose_lines_end_the_other_way(root)
            with open(full, "r", encoding="utf-8", newline="") as handle:
                text = handle.read()
            with open(full, "w", encoding="utf-8", newline="") as handle:
                handle.write(
                    text.replace("Companies of any size.", BIGGER_COMPANIES)
                )
            theirs = bytes_of(full)
            runner = NoRemoteRunner()
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

            with mock.patch.object(
                approve_local,
                "_save_the_work",
                side_effect=GitError("stopped", code=approve_local.CODE_GIT_FAILED),
            ):
                approve_local.approve(
                    staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                )

            self.assertEqual(theirs, bytes_of(full))
            self.assertEqual(theirs.count(b"\r"), bytes_of(full).count(b"\r"))

    def test_a_document_that_is_not_text_stops_the_run_rather_than_being_lost(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            full = os.path.join(root, ICP)
            with open(full, "wb") as handle:
                handle.write(b"\xff\xfe not text at all\n")
            theirs = bytes_of(full)

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertTrue(shown.refused, shown.status)
            self.assertEqual(theirs, bytes_of(full))




# --- N1 and N8 of the final confirmation pass --------------------------------


class TestEveryOrdinaryShapeOfHandEdit(unittest.TestCase):
    """N1. The check for a document that had moved on re-applied the edits.

    It took the edits a hand edit was described by, applied them again on top
    of a file that already held them, and asked for the result to equal the
    file. That only holds where applying an edit twice is the same as applying
    it once, and for six ordinary shapes of edit it is not, so a change was
    refused as moved straight after being prepared, with a sentence that was
    untrue and advice that failed the same way. What the reviewer wrote is the
    list below.

    Nothing is re-applied now. A change somebody made by hand is the document
    in front of them, so what is saved is that document, exactly as it sits on
    the disk, and what says it moved is the bytes themselves.
    """

    SHAPES = (
        (
            "a plain one-line edit",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ),
        ),
        (
            "a document with no newline at its end",
            lambda text: text.rstrip("\n"),
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ).rstrip("\n"),
        ),
        (
            "an edit that takes the final newline away",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ).rstrip("\n"),
        ),
        (
            "an edit leaving two blank lines at the end",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            )
            + "\n\n",
        ),
        (
            "a new part added by hand at the end",
            None,
            lambda text: text + "\n## Pricing\n\nTen dollars a seat.\n",
        ),
        (
            "a new part added by hand in the middle",
            None,
            lambda text: text.replace(
                "## Firmographics",
                "## Buyers\n\nHeads of operations.\n\n## Firmographics",
            ),
        ),
        (
            "a heading renamed",
            None,
            lambda text: text.replace("## Firmographics", "## Company size"),
        ),
        (
            "the words directly under a part that has smaller parts under it",
            lambda text: text
            + "\n## Segments\n\nIntro words.\n\n### Large\n\nBig ones.\n",
            lambda text: text.replace("Intro words.", "New intro words."),
        ),
        (
            "the same heading twice, the second one edited",
            lambda text: text
            + "\n## Notes\n\nFirst words.\n\n## Notes\n\nSecond words.\n",
            lambda text: text.replace("Second words.", "Second words, edited."),
        ),
        (
            "a document whose lines end the other way",
            lambda text: text.replace("\n", "\r\n"),
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ),
        ),
        (
            "two parts edited at once",
            lambda text: text + "\n## Pricing\n\nTen dollars a seat.\n",
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ).replace("Ten dollars", "Twenty dollars"),
        ),
        (
            "a part deleted and another edited",
            lambda text: text + "\n## Pricing\n\nTen dollars a seat.\n",
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ).replace("\n## Pricing\n\nTen dollars a seat.\n", ""),
        ),
        (
            "trailing spaces on the edited line",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred.   "
            ),
        ),
        (
            "a blank line added inside the part",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of any size.\n\nAnd growing."
            ),
        ),
        (
            "an edit alongside a change to the settings at the top",
            None,
            lambda text: text.replace(
                "Companies of any size.", "Companies of twenty to two hundred."
            ).replace("status: draft", "status: confirmed"),
        ),
    )

    def put(self, path, text):
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    def take(self, path):
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()

    def test_each_shape_ends_applied_with_the_bytes_the_person_had(self):
        for name, prepare, mutate in self.SHAPES:
            with self.subTest(shape=name):
                with support.Sandbox() as sandbox:
                    root, base_id = local_base(sandbox)
                    full = os.path.join(root, ICP)
                    if prepare is not None:
                        self.put(full, prepare(self.take(full)))
                        support.git(
                            ["-c", "core.autocrlf=false", "add", "-A"], cwd=root
                        )
                        support.git(["commit", "-q", "-m", "as it was"], cwd=root)
                    self.put(full, mutate(self.take(full)))
                    theirs = bytes_of(full)
                    runner = NoRemoteRunner()
                    staged = compose_proposal.stage_local_edit(
                        root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
                    )

                    shown = approve_local.show(
                        staged, root, base_id, runner=runner, now=TODAY
                    )
                    self.assertEqual(
                        approve_local.STATUS_SHOWN, shown.status, shown.reasons
                    )
                    applied = approve_local.approve(
                        staged, root, base_id, shown.shown_hash,
                        runner=runner, now=NOW,
                    )

                    self.assertEqual(
                        approve_local.STATUS_APPLIED, applied.status, applied.reasons
                    )
                    self.assertEqual(theirs, saved_bytes(root, ICP))
                    self.assertEqual(theirs, bytes_of(full))

    def test_a_document_that_really_moved_on_is_still_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            full = os.path.join(root, ICP)
            support.write(
                full,
                support.read(full).replace(
                    BIGGER_COMPANIES, "Companies of fifty to five hundred people."
                ),
            )
            theirs = bytes_of(full)

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_MOVED, shown.status)
            self.assertEqual(theirs, bytes_of(full))
            self.assertEqual([], corrections_in(root))

    def test_even_one_invisible_character_counts_as_moved(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            full = os.path.join(root, ICP)
            with open(full, "ab") as handle:
                handle.write(b" ")

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_MOVED, shown.status)


# --- R10 of Astra's third verification ---------------------------------------


def _put_exact(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _saved_as(root, relative, text):
    """Save one document as the base's last saved version."""
    _put_exact(os.path.join(root, relative), text)
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "as it was"], cwd=root)


class TestHandEditsTheSummaryCouldNotDescribe(unittest.TestCase):
    """R10. Two ordinary hand edits could not be prepared at all.

    Preparing a hand edit walked only the parts the document still had, and
    kept them in a table keyed by heading, so a second part with the same
    heading wrote over the first. Taking out a part that was no longer true,
    with nothing else changed, and editing the first of two parts with the
    same heading, with the second left alone, were both refused with a
    sentence saying the document had no headings in it. These are Astra's two
    scenarios exactly: in each one the change is the only change.
    """

    TWO_PARTS = support.ICP_TEXT + "\n## Pricing\n\nTen dollars a seat.\n"
    TWO_NOTES = (
        support.ICP_TEXT + "\n## Notes\n\nFirst words.\n\n## Notes\n\nSecond words.\n"
    )

    def test_a_part_taken_out_with_nothing_else_changed_is_approved(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _saved_as(root, ICP, self.TWO_PARTS)
            full = os.path.join(root, ICP)
            _put_exact(full, support.ICP_TEXT)
            theirs = bytes_of(full)
            runner = NoRemoteRunner()

            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            staging = compose_proposal.load_staging(staged)
            self.assertEqual(
                [("## Pricing", "remove")],
                [(edit.heading, edit.op) for edit in staging.edits],
            )
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            # The summary says the part is taken out, and shows what it said.
            self.assertIn("Pricing", shown.artifact)
            self.assertIn("takes out", shown.artifact)
            self.assertIn("Ten dollars a seat.", shown.artifact)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertEqual(theirs, saved_bytes(root, ICP))
            self.assertEqual(theirs, bytes_of(full))

    def test_the_first_of_two_parts_with_one_heading_is_approved(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _saved_as(root, ICP, self.TWO_NOTES)
            full = os.path.join(root, ICP)
            _put_exact(
                full, self.TWO_NOTES.replace("First words.", "First words, edited.")
            )
            theirs = bytes_of(full)
            runner = NoRemoteRunner()

            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            staging = compose_proposal.load_staging(staged)
            self.assertEqual(1, len(staging.edits))
            self.assertEqual("## Notes", staging.edits[0].heading)
            self.assertEqual("replace", staging.edits[0].op)
            self.assertEqual(1, staging.edits[0].occurrence)
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            # The part shown is the first one, before and after.
            summary = shown.artifact.split("different from the last time")[0]
            self.assertIn("First words.", summary)
            self.assertIn("First words, edited.", summary)
            self.assertNotIn("Second words.", summary)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertEqual(theirs, saved_bytes(root, ICP))

    def test_the_second_of_two_parts_with_one_heading_says_which_one(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _saved_as(root, ICP, self.TWO_NOTES)
            full = os.path.join(root, ICP)
            _put_exact(
                full, self.TWO_NOTES.replace("Second words.", "Second words, edited.")
            )
            runner = NoRemoteRunner()

            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            staging = compose_proposal.load_staging(staged)
            self.assertEqual(2, staging.edits[0].occurrence)
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            summary = shown.artifact.split("different from the last time")[0]
            self.assertIn("Second words.", summary)
            self.assertIn("Second words, edited.", summary)
            self.assertNotIn("First words.", summary)
            self.assertIn("second", summary)

    def test_one_of_two_parts_with_one_heading_taken_out(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _saved_as(root, ICP, self.TWO_NOTES)
            full = os.path.join(root, ICP)
            _put_exact(
                full, self.TWO_NOTES.replace("\n## Notes\n\nSecond words.\n", "")
            )
            runner = NoRemoteRunner()
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertEqual(bytes_of(full), saved_bytes(root, ICP))

    def _two_documents(self, root):
        other = "context/strategy/positioning.md"
        _saved_as(
            root,
            other,
            support.ICP_TEXT.replace("kind: icp", "kind: positioning").replace(
                "# Ideal customer profile", "# Positioning\n\nOld opening."
            ),
        )
        _put_exact(
            os.path.join(root, ICP),
            support.ICP_TEXT.replace("Companies of any size.", BIGGER_COMPANIES),
        )
        positioning = os.path.join(root, other)
        _put_exact(
            positioning,
            support.read(positioning).replace("Old opening.", "New opening."),
        )
        return other, positioning

    def test_every_changed_document_is_a_target_whatever_the_summary_says(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            other, positioning = self._two_documents(root)
            runner = NoRemoteRunner()

            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            staging = compose_proposal.load_staging(staged)
            self.assertEqual(sorted([ICP, other]), sorted(staging.target_paths))
            self.assertEqual(2, len(staging.target_bytes))
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn("New opening.", shown.artifact)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertEqual(bytes_of(positioning), saved_bytes(root, other))
            self.assertEqual(bytes_of(os.path.join(root, ICP)), saved_bytes(root, ICP))

    def test_a_target_whose_bytes_moved_is_refused_even_without_a_part(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _other, positioning = self._two_documents(root)
            runner = NoRemoteRunner()
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            with open(positioning, "ab") as handle:
                handle.write(b"More.\n")

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(approve_local.STATUS_MOVED, shown.status)

    def test_a_change_only_above_the_first_part_says_so_truthfully(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _put_exact(
                os.path.join(root, ICP),
                support.ICP_TEXT.replace(
                    "# Ideal customer profile", "# Ideal customer profile\n\nOpening."
                ),
            )
            runner = NoRemoteRunner()
            with self.assertRaises(compose_proposal.ValidationError) as caught:
                compose_proposal.stage_local_edit(
                    root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
                )
            self.assertEqual(
                compose_proposal.OUTSIDE_EVERY_PART % names.document_name(ICP),
                str(caught.exception),
            )

    def test_the_shared_copy_path_takes_a_part_out_and_finds_the_right_one(self):
        # A base with a shared copy applies the parts rather than saving the
        # document, so the two new shapes have to apply as well as show.
        removed = formats.Edit(ICP, "## Pricing", "remove", "")
        self.assertEqual(
            support.ICP_TEXT, compose_proposal.apply_edit(self.TWO_PARTS, removed)
        )
        second = formats.Edit(ICP, "## Notes", "replace", "Changed.\n", occurrence=2)
        self.assertEqual(
            self.TWO_NOTES.replace("Second words.", "Changed."),
            compose_proposal.apply_edit(self.TWO_NOTES, second),
        )

    def test_the_occurrence_survives_being_written_and_read_back(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            _saved_as(root, ICP, self.TWO_NOTES)
            _put_exact(
                os.path.join(root, ICP),
                self.TWO_NOTES.replace("Second words.", "Second words, edited."),
            )
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=NoRemoteRunner(), now=TODAY
            )
            again = formats.ProposalStaging.parse(
                compose_proposal.load_staging(staged).render()
            )
            self.assertEqual(2, again.edits[0].occurrence)



# --- R1 of Astra's third verification ----------------------------------------


def _index_entry(root, relative):
    """The mode and the stored version the index holds for one path."""
    finished = subprocess.run(
        ["git", "ls-files", "-s", "--", relative],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    line = finished.stdout.decode("utf-8").strip()
    return line.split("\t")[0] if line else ""


def _staged_bytes(root, relative):
    finished = subprocess.run(
        ["git", "show", ":" + relative],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return finished.stdout


def _a_hook_that_refuses_every_save(root):
    hooks = os.path.join(root, ".git", "hooks")
    os.makedirs(hooks, exist_ok=True)
    hook = os.path.join(hooks, "pre-commit")
    with open(hook, "w") as handle:
        handle.write("#!/bin/sh\nexit 1\n")
    os.chmod(hook, 0o755)


class TestAFailedApprovalLeavesTheIndexAsItWas(unittest.TestCase):
    """R1. A failed approval still lost what the person had lined up to save.

    Astra's scenario exactly: they line up version B of the customer profile
    to be saved, carry on editing it into C, prepare C as a hand edit, and
    approve it with a check before saving that refuses. Approval lines up C,
    the save is refused, and the rollback saw that the file on the disk was
    already C and put nothing back, so B was gone from what they had lined up
    and nothing said so. The file's permissions were forced to one value on
    the way back as well.
    """

    def scenario(self, sandbox, mode=0o640):
        root, base_id = local_base(sandbox)
        full = os.path.join(root, ICP)
        support.write(
            full,
            support.read(full).replace(
                "Companies of any size.", "Companies of fifty and up."
            ),
        )
        support.git(["add", "--", ICP], cwd=root)
        support.write(
            full,
            support.read(full).replace(
                "Companies of fifty and up.", BIGGER_COMPANIES
            ),
        )
        os.chmod(full, mode)
        return root, base_id, full

    def test_the_lined_up_version_and_the_permissions_come_back(self):
        with support.Sandbox() as sandbox:
            root, base_id, full = self.scenario(sandbox)
            lined_up = _staged_bytes(root, ICP)
            entry = _index_entry(root, ICP)
            theirs = bytes_of(full)
            runner = NoRemoteRunner()
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            _a_hook_that_refuses_every_save(root)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual(theirs, bytes_of(full))
            self.assertEqual(lined_up, _staged_bytes(root, ICP))
            self.assertEqual(entry, _index_entry(root, ICP))
            self.assertEqual(0o640, os.stat(full).st_mode & 0o7777)
            # Everything came back, so there is nothing left to recover.
            self.assertIsNone(approve_local._load_journal(base_id))

    def test_a_file_that_was_not_lined_up_is_not_lined_up_afterwards(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = NoRemoteRunner()
            staged = a_hand_edit(root, base_id, runner)
            entry = _index_entry(root, ICP)
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            _a_hook_that_refuses_every_save(root)

            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(entry, _index_entry(root, ICP))
            self.assertEqual(
                saved_bytes(root, ICP), _staged_bytes(root, ICP)
            )

    def test_the_permissions_come_back_when_the_bytes_had_to_be_written(self):
        # A change that is not a hand edit writes the document itself, so a
        # failure puts the kept bytes back, and it used to put them back with
        # permissions of its own choosing.
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            full = os.path.join(root, ICP)
            os.chmod(full, 0o600)
            theirs = bytes_of(full)
            staged = stage(root)
            runner = NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            _a_hook_that_refuses_every_save(root)

            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(theirs, bytes_of(full))
            self.assertEqual(0o600, os.stat(full).st_mode & 0o7777)

    def test_the_recovery_note_stays_when_the_index_cannot_be_put_back(self):
        with support.Sandbox() as sandbox:
            root, base_id, full = self.scenario(sandbox)
            runner = NoRemoteRunner()
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            _a_hook_that_refuses_every_save(root)
            real_run = runner.run

            def refusing_to_line_up(args, *rest, **options):
                if args and args[0] == "update-index":
                    return GitResult(1, "", "refused")
                return real_run(args, *rest, **options)

            with mock.patch.object(runner, "run", side_effect=refusing_to_line_up):
                applied = approve_local.approve(
                    staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                )

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertIsNotNone(approve_local._load_journal(base_id))

    def test_a_note_naming_an_index_value_we_never_write_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            state.update_seat(base_id)
            support.write(
                approve_local._journal_path(base_id),
                __import__("json").dumps(
                    {
                        "schema": approve_local.JOURNAL_SCHEMA,
                        "staging_id": STAGING,
                        "base_root": os.path.realpath(root),
                        "subject": "x",
                        "head": "a" * 40,
                        "paths": [{"path": ICP, "hash": ids.content_hash("x")}],
                        "originals": [
                            {
                                "path": ICP,
                                "hash": ids.content_hash("x"),
                                "copy": "0.bytes",
                                "index": {"mode": "100644", "blob": "--output=x"},
                            }
                        ],
                    }
                ),
            )

            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.CODE_NOTE_UNREADABLE, shown.codes[0])



# --- R8 of Astra's third verification ----------------------------------------


def _the_whole_difference(artifact):
    """The fenced block the whole difference is shown in, as it was written."""
    import re as _re

    after = artifact.split("which is all of what saying yes to this writes down:")[1]
    match = _re.search(r"\n(`{3,})diff\n(.*?)\n\1\n", after, _re.S)
    if match is None:
        raise AssertionError("the whole difference is not in a fenced block:\n" + after)
    return match.group(1), match.group(2), after


class TestTheWholeDifferenceIsShownAsItIs(unittest.TestCase):
    """R8. The whole difference was shown as quoted text a screen renders.

    An image added by hand showed as an image, a link showed its words and
    hid where it went, and spaces at the end of a line were taken off, so what
    a person read was not what saying yes would write down. Astra's probe
    added two spaces at the end of a line and watched them disappear.
    """

    def shown_for(self, sandbox, change):
        root, base_id = local_base(sandbox)
        full = os.path.join(root, ICP)
        _put_exact(full, change(support.read(full)))
        runner = NoRemoteRunner()
        staged = compose_proposal.stage_local_edit(
            root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
        )
        shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
        self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
        return shown

    def test_an_image_and_a_link_are_shown_as_the_words_that_make_them(self):
        with support.Sandbox() as sandbox:
            shown = self.shown_for(
                sandbox,
                lambda text: text.replace(
                    "Companies of any size.",
                    "Companies of any size. See [the deck](https://example.com/deck) "
                    "and ![a chart](https://example.com/chart.png).",
                ),
            )

            _fence, body, _after = _the_whole_difference(shown.artifact)
            self.assertIn(
                "+Companies of any size. See [the deck](https://example.com/deck) "
                "and ![a chart](https://example.com/chart.png).",
                body.split("\n"),
            )

    def test_spaces_at_the_end_of_a_line_are_kept_and_pointed_out(self):
        with support.Sandbox() as sandbox:
            shown = self.shown_for(
                sandbox,
                lambda text: text.replace(
                    "Companies of any size.", "Companies of any size.  "
                ),
            )

            _fence, body, after = _the_whole_difference(shown.artifact)
            self.assertIn("+Companies of any size.  ", body.split("\n"))
            self.assertIn(
                approve_local.WHITESPACE_ONLY % names.document_name(ICP), after
            )
            self.assertIn("+Companies\u00b7of\u00b7any\u00b7size.\u00b7\u00b7", after)

    def test_a_fence_in_the_document_cannot_close_the_block(self):
        with support.Sandbox() as sandbox:
            shown = self.shown_for(
                sandbox,
                lambda text: text.replace(
                    "Companies of any size.",
                    "Companies of any size.\n\n````\nAnything at all.\n````",
                ),
            )

            fence, body, _after = _the_whole_difference(shown.artifact)
            self.assertGreater(len(fence), 4)
            self.assertIn("+````", body.split("\n"))
            self.assertIn("+Anything at all.", body.split("\n"))

    def test_an_ordinary_change_says_nothing_about_spaces(self):
        with support.Sandbox() as sandbox:
            shown = self.shown_for(
                sandbox,
                lambda text: text.replace("Companies of any size.", BIGGER_COMPANIES),
            )

            _fence, body, after = _the_whole_difference(shown.artifact)
            self.assertIn("+" + BIGGER_COMPANIES, body.split("\n"))
            self.assertNotIn(
                approve_local.WHITESPACE_ONLY % names.document_name(ICP), after
            )


# --- N8 of Astra's fourth verification ---------------------------------------

ACCENTED = "context/strategy/stratégie.md"


class TestADocumentWhoseNameIsNotPlainLetters(unittest.TestCase):
    """N8. A document named with an accent could not be approved.

    Git writes such a name in quotes with escapes when it lists the index, so
    the entry kept before approval never matched the name it was read for and
    approval stopped before anything was written. Astra's path exactly.
    """

    def accented_base(self, sandbox):
        root, base_id = local_base(sandbox)
        _saved_as(root, ACCENTED, support.read(os.path.join(root, ICP)))
        return root, base_id

    def test_the_index_entry_is_read_for_an_accented_name(self):
        with support.Sandbox() as sandbox:
            root, _base_id = self.accented_base(sandbox)
            read, entry = approve_local._index_entry(root, ACCENTED, GitRunner())
            self.assertTrue(read)
            self.assertEqual("100644", entry[0])

    def test_a_prepared_change_to_an_accented_document_is_approved(self):
        with support.Sandbox() as sandbox:
            root, base_id = self.accented_base(sandbox)
            staged = stage(
                root,
                custom_staging(
                    edits=[
                        formats.Edit(
                            ACCENTED, "## Firmographics", "replace", BIGGER_COMPANIES + "\n"
                        )
                    ]
                ),
            )
            runner = NoRemoteRunner()

            shown, applied = show_and_approve(root, base_id, staged, runner)

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertIn(BIGGER_COMPANIES, saved_bytes(root, ACCENTED).decode("utf-8"))

    def test_a_plain_name_is_still_read_the_same_way(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            read, entry = approve_local._index_entry(root, ICP, GitRunner())
            self.assertTrue(read)
            self.assertEqual("100644", entry[0])
            read, entry = approve_local._index_entry(
                root, "context/strategy/nothing.md", GitRunner()
            )
            self.assertEqual((True, None), (read, entry))


# --- N1 of Astra's fourth verification ---------------------------------------


class TestRecoveryKeepsWhatCameAfterTheRun(unittest.TestCase):
    """N1. Recovery put back the index and permissions over newer ones.

    Astra's scenario: approval keeps staged B, working C, and permissions
    0640, and stops after lining up C. The owner then lines up D and sets
    0600, leaving the working bytes at C. Recovery saw the working bytes it
    kept and put back B and 0640 without asking what was there now, and said
    everything had come back.
    """

    scenario = TestAFailedApprovalLeavesTheIndexAsItWas.scenario

    def stopped(self, sandbox):
        root, base_id, full = self.scenario(sandbox)
        runner = NoRemoteRunner()
        staged = compose_proposal.stage_local_edit(
            root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
        )
        lined_up = _staged_bytes(root, ICP)
        stop_once(root, base_id, staged, runner)
        self.assertIsNotNone(approve_local._load_journal(base_id))
        return root, base_id, full, staged, runner, lined_up

    def recover(self, root, base_id, staged, runner):
        codes = []
        result = approve_local._finish_unfinished_work(
            root, base_id, os.path.basename(staged)[: -len(".md")], runner, codes
        )
        return result, codes

    def test_a_newer_index_entry_and_newer_permissions_are_kept(self):
        with support.Sandbox() as sandbox:
            root, base_id, full, staged, runner, _lined_up = self.stopped(sandbox)
            working = bytes_of(full)
            _put_exact(full, working.decode("utf-8") + "\nD, lined up later.\n")
            support.git(["add", "--", ICP], cwd=root)
            newer = _staged_bytes(root, ICP)
            with open(full, "wb") as handle:
                handle.write(working)
            os.chmod(full, 0o600)

            result, _codes = self.recover(root, base_id, staged, runner)

            self.assertEqual(newer, _staged_bytes(root, ICP))
            self.assertEqual(0o600, os.stat(full).st_mode & 0o7777)
            self.assertEqual(working, bytes_of(full))
            self.assertIsNotNone(result)
            self.assertEqual(approve_local.CODE_UNSAVED_EDITS, result.codes[0])
            self.assertIsNotNone(approve_local._load_journal(base_id))

    def test_newer_permissions_alone_are_kept_and_the_index_comes_back(self):
        with support.Sandbox() as sandbox:
            root, base_id, full, staged, runner, lined_up = self.stopped(sandbox)
            os.chmod(full, 0o600)

            result, codes = self.recover(root, base_id, staged, runner)

            self.assertIsNone(result)
            self.assertIn(approve_local.CODE_UNDONE, codes)
            self.assertEqual(lined_up, _staged_bytes(root, ICP))
            self.assertEqual(0o600, os.stat(full).st_mode & 0o7777)

    def test_a_newer_entry_that_was_then_saved_no_longer_holds_anything_up(self):
        with support.Sandbox() as sandbox:
            root, base_id, full, staged, runner, _lined_up = self.stopped(sandbox)
            _put_exact(full, bytes_of(full).decode("utf-8") + "\nD, saved.\n")
            support.git(["add", "--", ICP], cwd=root)
            support.git(["commit", "-q", "-m", "their own"], cwd=root)

            result, codes = self.recover(root, base_id, staged, runner)

            self.assertIsNone(result, result and result.reasons)
            self.assertIn(approve_local.CODE_UNDONE, codes)

    def test_with_nothing_newer_the_originals_come_back_as_before(self):
        with support.Sandbox() as sandbox:
            root, base_id, full, staged, runner, lined_up = self.stopped(sandbox)
            working = bytes_of(full)

            result, codes = self.recover(root, base_id, staged, runner)

            self.assertIsNone(result)
            self.assertIn(approve_local.CODE_UNDONE, codes)
            self.assertEqual(lined_up, _staged_bytes(root, ICP))
            self.assertEqual(0o640, os.stat(full).st_mode & 0o7777)
            self.assertEqual(working, bytes_of(full))
            self.assertIsNone(approve_local._load_journal(base_id))

    def test_a_written_file_whose_permissions_this_run_set_gets_its_own_back(self):
        # Not a hand edit: this run writes the document, with permissions of
        # its own, and those are this run's value to put back.
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            full = os.path.join(root, ICP)
            os.chmod(full, 0o600)
            theirs = bytes_of(full)
            staged = stage(root)
            runner = NoRemoteRunner()
            stop_once(root, base_id, staged, runner)
            self.assertEqual(0o644, os.stat(full).st_mode & 0o7777)

            result, codes = self.recover(root, base_id, staged, runner)

            self.assertIsNone(result, result and result.reasons)
            self.assertEqual(theirs, bytes_of(full))
            self.assertEqual(0o600, os.stat(full).st_mode & 0o7777)


if __name__ == "__main__":
    unittest.main()
