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

# Anything that could carry a byte off this computer. `remote get-url` is not
# one of them: it reads the base's own settings and asks nobody anything.
REMOTE_COMMANDS = (
    "push",
    "fetch",
    "pull",
    "clone",
    "ls-remote",
    "request-pull",
    "submodule",
    "bundle",
    "daemon",
)


class NoRemoteRunner(object):
    """The real runner, with every command that could reach a remote refused.

    It fails the test rather than returning an error, because a path that tried
    to reach a remote and was politely refused is still a path that tried.
    """

    def __init__(self):
        self.inner = GitRunner()
        self.calls = []

    def _check(self, args):
        arguments = [str(item) for item in args]
        self.calls.append(arguments)
        words = [item for item in arguments if not item.startswith("-")]
        first = words[0] if words else ""
        if first in REMOTE_COMMANDS:
            raise AssertionError("this path tried to reach a remote: %s" % arguments)
        if first == "remote" and len(words) > 1:
            # Listing them, and reading one address out of the base's own
            # settings, are both local reads. Anything else changes something.
            if words[1] not in ("get-url", "show"):
                raise AssertionError("this path changed a remote: %s" % arguments)
        if first == "archive" and "--remote" in arguments:
            raise AssertionError("this path tried to reach a remote: %s" % arguments)

    def run(self, args, cwd=None, timeout=20, input=None):
        self._check(args)
        return self.inner.run(args, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        self._check(args)
        return self.inner.check(args, cwd=cwd, timeout=timeout, input=input)


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
            entry_path = "%s/%s.md" % (constants.DECISIONS_DIR, STAGING)
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

    def test_neither_of_the_two_files_that_hold_the_line_was_touched(self):
        """The check on commands and the two conditions are byte for byte as they were."""
        finished = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "HEAD",
                "--",
                "plugins/gtm-base/lib/gtmbase/gate.py",
                "plugins/gtm-base/lib/gtmbase/push_conditions.py",
            ],
            cwd=support.REPO_ROOT,
            stdout=subprocess.PIPE,
        )
        self.assertEqual("", finished.stdout.decode("utf-8").strip())


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
                os.path.join(root, constants.DECISIONS_DIR, HAND_ENTERED + ".md"),
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
            self.assertIn("decided_on: 2026-06-01", shown.artifact)

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
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = stage(root)
            shown = stop_once(root, base_id, staged, NoRemoteRunner())

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash,
                runner=FailingRunner(["checkout"]), now=NOW,
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
                os.path.join(root, constants.DECISIONS_DIR, STAGING + ".md"),
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
        os.chdir(root)
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


if __name__ == "__main__":
    unittest.main()
