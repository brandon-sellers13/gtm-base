"""Turning a staged change into a review, from every direction it can go."""

import datetime
import json
import os
import shutil
import subprocess
import unittest

import plain_language
import support

from gtmbase import (
    compose_proposal,
    constants,
    formats,
    gate,
    ids,
    marker,
    paths,
    stale,
    state,
    worktree,
)
from gtmbase.gitcmd import GitRunner
from gtmbase.validate import marker_line

TODAY = datetime.date(2026, 1, 15)
STAGING = "stg-0000000000000000"
SOURCE = "src-000000000000000000000000"
ICP = "context/strategy/icp.md"
OWNER = "owner@example.com"
BRANCH = constants.PROPOSAL_BRANCH_PREFIX + STAGING
FAKES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fakes")


# --- Helpers -----------------------------------------------------------------


RecordingGh = support.RecordingGh
base_with_a_shared_copy = support.base_with_a_shared_copy


def stage(root, text=None, staging_id=STAGING):
    """Put a staged proposal where a producer would have left it."""
    if text is None:
        text = support.read(os.path.join(support.TEMPLATES_DIR, "proposal-staging.md"))
    path = os.path.join(
        root, constants.PROPOSALS_PENDING_DIR, staging_id + ".md"
    )
    support.write(path, text)
    return path


def template_text():
    return support.read(os.path.join(support.TEMPLATES_DIR, "proposal-staging.md"))


show = support.show


status_of = support.status_of


branch_of = support.branch_of


ref_of = support.ref_of


# --- The happy path ----------------------------------------------------------


class TestAProposalThatOpens(unittest.TestCase):
    def test_it_carries_the_change_the_decision_and_the_record_of_what_changed(self):
        with support.Sandbox() as sandbox:
            root, base_id, remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            head_before = support.head_of(root)
            gh = RecordingGh()

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(compose_proposal.STATUS_OPENED, result.status, result.reasons)
            self.assertEqual(41, result.pr_number)
            self.assertEqual("https://example.test/pull/41", result.pr_url)

            # The change is on the shared copy, under its own name.
            changed = show(remote, BRANCH, ICP)
            self.assertIn("twenty to two hundred people", changed)
            self.assertIn("## Firmographics", changed)
            self.assertNotIn("Companies of any size.", changed)

            # The decision it carries reads as a decision.
            entry_path = "%s/%s.md" % (constants.DECISIONS_DIR, STAGING)
            entry = formats.LedgerEntry.parse(show(remote, BRANCH, entry_path))
            entry.validate(TODAY)
            self.assertEqual(TODAY.isoformat(), entry.written_on)
            self.assertEqual([ICP], entry.affects)

            # The record of what changed carries the marker, the hash, and the paths.
            record_path = "%s/%s-%s.md" % (
                constants.CORRECTIONS_DIR,
                TODAY.isoformat(),
                STAGING,
            )
            record = formats.CorrectionsFile.parse(show(remote, BRANCH, record_path))
            record.validate()
            self.assertEqual(marker_line(STAGING, STAGING, SOURCE), record.marker)
            self.assertEqual(ids.content_hash(changed), record.content_hash)
            self.assertEqual([ICP, entry_path], record.touched_paths)
            self.assertEqual("new-decision", record.correction_class)
            self.assertEqual("decision", record.mode)
            self.assertEqual("ledger", record.intake_path)

            # The text handed over is the one document a reviewer reads.
            self.assertEqual(1, len(gh.bodies))
            body = gh.bodies[0]
            present, missing = formats.required_sections_present(body)
            self.assertTrue(present, missing)
            self.assertEqual(
                marker_line(STAGING, STAGING, SOURCE),
                [line for line in body.strip().split("\n") if line.strip()][-1],
            )
            self.assertEqual([], plain_language.find_banned(body))
            self.assertEqual([], plain_language.find_dashes(body))

            # The person's own folder is untouched.
            self.assertEqual(head_before, support.head_of(root))
            self.assertEqual("main", branch_of(root))
            self.assertEqual("", status_of(root))

            # The staged file is kept, and the working folder is gone.
            self.assertFalse(os.path.isfile(staged))
            self.assertTrue(
                os.path.isfile(
                    os.path.join(root, constants.PROPOSALS_OPENED_DIR, STAGING + ".md")
                )
            )
            folder = os.path.join(paths.worktrees_dir(base_id), STAGING)
            self.assertFalse(os.path.isdir(folder))
            self.assertEqual([os.path.realpath(root)], worktree.list_worktrees(root))

            # The row remembers the review.
            index, _problems = state.load_index(base_id)
            self.assertEqual("processed", index[SOURCE]["status"])
            self.assertIn("%s:41" % STAGING, index[SOURCE]["proposal_ids"])

    def test_the_title_and_the_saved_note_say_what_it_does_in_plain_words(self):
        staging = formats.ProposalStaging.parse(template_text())
        subject = compose_proposal.commit_subject(staging)
        self.assertTrue(subject.startswith("Proposal %s: " % STAGING), subject)
        title = compose_proposal.review_title(staging)
        self.assertIn(ICP, title)
        self.assertEqual([], plain_language.find_banned(title))


# --- What the floor refuses ---------------------------------------------------


class TestTheFloorRefuses(unittest.TestCase):
    def _run(self, sandbox, text):
        root, base_id, _remote = base_with_a_shared_copy(sandbox)
        staged = stage(root, text)
        gh = RecordingGh()
        result = compose_proposal.propose(
            staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
        )
        return root, base_id, gh, result

    def test_an_address_in_the_evidence_stops_the_run_and_is_never_repeated(self):
        with support.Sandbox() as sandbox:
            secret = "reach me at buyer.person@acme-fintech.example"
            text = template_text().replace(
                "so from now on we are only going after companies between twenty and two hundred people",
                secret,
                1,
            )
            root, base_id, gh, result = self._run(sandbox, text)

            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn("email", result.codes)
            for reason in result.reasons:
                self.assertNotIn("buyer.person@acme-fintech.example", reason)
                self.assertNotIn("acme-fintech", reason)
            self.assertEqual([], gh.created())
            self.assertFalse(os.path.isdir(os.path.join(paths.worktrees_dir(base_id), STAGING)))
            self.assertEqual([os.path.realpath(root)], worktree.list_worktrees(root))
            self.assertTrue(
                os.path.isfile(
                    os.path.join(root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md")
                )
            )

    def test_a_character_a_reader_cannot_see_stops_the_run(self):
        with support.Sandbox() as sandbox:
            text = template_text().replace(
                "so from now on we are only going after",
                "so from now on we​ are only going after",
                1,
            )
            root, base_id, gh, result = self._run(sandbox, text)
            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn("hidden-content", result.codes)
            self.assertEqual([], gh.created())
            self.assertFalse(
                os.path.isdir(os.path.join(paths.worktrees_dir(base_id), STAGING))
            )


# --- What a proposal may never change ----------------------------------------


class TestWhatAProposalMayNeverChange(unittest.TestCase):
    def _refusal(self, sandbox, text):
        root, base_id, _remote = base_with_a_shared_copy(sandbox)
        staged = stage(root, text)
        gh = RecordingGh()
        result = compose_proposal.propose(
            staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
        )
        self.assertEqual(compose_proposal.STATUS_REFUSED, result.status, result.reasons)
        self.assertEqual([], gh.calls)
        self.assertFalse(os.path.isdir(os.path.join(paths.worktrees_dir(base_id), STAGING)))
        return result

    def test_the_map_is_refused_before_any_folder_is_made(self):
        with support.Sandbox() as sandbox:
            text = template_text().replace("path: " + ICP, "path: " + constants.MAP_PATH)
            text = text.replace("target_paths: [%s]" % ICP, "target_paths: [%s]" % constants.MAP_PATH)
            result = self._refusal(sandbox, text)
            self.assertIn(compose_proposal.CODE_MAP_TARGET, result.codes)

    def test_a_settings_key_is_not_a_heading_and_is_refused(self):
        with support.Sandbox() as sandbox:
            text = template_text().replace("heading: ## Firmographics", "heading: owner:")
            result = self._refusal(sandbox, text)
            self.assertIn(compose_proposal.CODE_FRONTMATTER_TARGET, result.codes)

    def test_a_file_outside_the_context_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            text = template_text().replace("path: " + ICP, "path: work/decisions/secret.md")
            result = self._refusal(sandbox, text)
            self.assertTrue(result.reasons)


class TestAFolderThatIsALinkInTheSharedCopy(unittest.TestCase):
    """Where the change is written is checked in the folder it is written in.

    A name can be an ordinary folder in the person's own copy and a link
    pointing somewhere else in the shared copy. The proposal is prepared from
    the shared copy, so that is where the check has to happen.
    """

    SUB = "context/sub/icp.md"

    def _base_whose_shared_copy_holds_a_link(self, sandbox):
        root, base_id, remote = base_with_a_shared_copy(sandbox)
        support.write(os.path.join(root, self.SUB), support.ICP_TEXT)
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a folder"], cwd=root)
        support.git(["push", "-q", "origin", "main"], cwd=root)

        outside = os.path.join(sandbox.path, "outside")
        support.write(os.path.join(outside, "icp.md"), support.ICP_TEXT)
        helper = os.path.join(sandbox.path, "helper")
        support.git(["clone", "-q", remote, helper], cwd=sandbox.path)
        support.git(["config", "--local", "user.email", OWNER], cwd=helper)
        support.git(["config", "--local", "user.name", "Test Owner"], cwd=helper)
        shutil.rmtree(os.path.join(helper, "context", "sub"))
        os.symlink(outside, os.path.join(helper, "context", "sub"))
        support.git(["add", "-A"], cwd=helper)
        support.git(["commit", "-q", "-m", "a link"], cwd=helper)
        support.git(["push", "-q", "origin", "main"], cwd=helper)
        return root, base_id, outside

    def test_the_change_is_refused_and_nothing_outside_the_folder_is_written(self):
        with support.Sandbox() as sandbox:
            root, base_id, outside = self._base_whose_shared_copy_holds_a_link(
                sandbox
            )
            staged = stage(root, template_text().replace(ICP, self.SUB))
            gh = RecordingGh()

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(
                compose_proposal.STATUS_REFUSED, result.status, result.reasons
            )
            self.assertEqual([], gh.created())
            self.assertEqual(
                support.ICP_TEXT, support.read(os.path.join(outside, "icp.md"))
            )
            self.assertEqual(
                sorted(["icp.md"]), sorted(os.listdir(outside))
            )


# --- Somebody already raised this --------------------------------------------


class TestSomebodyAlreadyRaisedThis(unittest.TestCase):
    def _review(self, number, state_name):
        return {
            "number": number,
            "state": state_name,
            "url": "https://example.test/pull/%d" % number,
            "body": "text\n\n%s\n" % marker_line(STAGING, STAGING, SOURCE),
        }

    def test_an_open_review_elsewhere_is_recorded_against_the_source(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            gh = RecordingGh(search=[self._review(5, "OPEN")])

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_ALREADY_OPEN, result.status)
            self.assertEqual(5, result.pr_number)
            self.assertEqual([], gh.created())
            index, _problems = state.load_index(base_id)
            self.assertEqual("processed-elsewhere", index[SOURCE]["status"])
            self.assertEqual(5, index[SOURCE]["foreign_pr"])

    def test_a_review_that_was_turned_down_is_skipped_until_the_person_says_otherwise(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            gh = RecordingGh(search=[self._review(6, "CLOSED")])

            first = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_CLOSED_SKIPPED, first.status)
            self.assertEqual([], gh.created())

            again = compose_proposal.propose(
                staged,
                root,
                base_id,
                gh=gh,
                now=TODAY,
                session_id="sess-1",
                allow_reproposal=True,
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, again.status, again.reasons)
            self.assertEqual(1, len(gh.created()))

    def test_a_record_of_the_same_change_already_accepted_is_skipped(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            support.write(
                os.path.join(root, constants.CORRECTIONS_DIR, "2026-01-02-%s.md" % STAGING),
                support.read(os.path.join(support.TEMPLATES_DIR, "corrections-file.md")),
            )
            staged = stage(root)
            gh = RecordingGh()

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_MERGED_SKIPPED, result.status)
            self.assertEqual([], gh.created())


# --- A run that stopped halfway ----------------------------------------------


class TestARunThatStoppedHalfway(unittest.TestCase):
    def test_stopping_before_the_review_leaves_work_that_is_used_again(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)

            broken = RecordingGh(raise_on_create=True)
            with self.assertRaises(RuntimeError):
                compose_proposal.propose(
                    staged, root, base_id, gh=broken, now=TODAY, session_id="sess-1"
                )

            folder = os.path.join(paths.worktrees_dir(base_id), STAGING)
            self.assertTrue(os.path.isdir(folder))
            saved = ref_of(root, BRANCH)
            self.assertTrue(saved)
            self.assertTrue(os.path.isfile(staged))

            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, result.status, result.reasons)
            self.assertIn(compose_proposal.CODE_COMMIT_REUSED, result.codes)
            self.assertIn(worktree.CODE_REUSED, result.codes)
            self.assertEqual(1, len(gh.created()))
            self.assertEqual(saved, ref_of(root, BRANCH))
            self.assertFalse(os.path.isdir(folder))

    def test_stopping_after_the_review_finishes_from_what_was_recorded(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            first = compose_proposal.propose(
                staged, root, base_id, gh=RecordingGh(), now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, first.status)

            # As though the run had stopped before the staged file was put away.
            kept = os.path.join(root, constants.PROPOSALS_OPENED_DIR, STAGING + ".md")
            shutil.copyfile(kept, staged)

            gh = RecordingGh()
            again = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_RESUMED, again.status, again.reasons)
            self.assertEqual(41, again.pr_number)
            self.assertEqual([], gh.created())
            self.assertFalse(os.path.isfile(staged))

    def test_resuming_after_the_review_opened_tidies_up_and_does_not_report_others(self):
        """The seat's own open review is this run's, not somebody else's.

        The stand-in here answers a search the way the real tool does, with the
        review this seat just opened in it, which is what a repeated run really
        meets.
        """
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            gh = support.IndexingGh()
            first = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, first.status, first.reasons)

            # As though the run had stopped before the staged file was put away.
            kept = os.path.join(root, constants.PROPOSALS_OPENED_DIR, STAGING + ".md")
            shutil.copyfile(kept, staged)

            again = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(
                compose_proposal.STATUS_RESUMED, again.status, again.reasons
            )
            self.assertEqual(41, again.pr_number)
            self.assertEqual(1, len(gh.created()))
            self.assertFalse(os.path.isfile(staged))
            index, _problems = state.load_index(base_id)
            self.assertEqual("processed", index[SOURCE]["status"])
            self.assertIsNone(index[SOURCE]["foreign_pr"])

    def test_another_seats_review_of_the_same_change_is_still_reported(self):
        """Only this proposal's own line of work is treated as this seat's."""
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            elsewhere = {
                "number": 9,
                "state": "OPEN",
                "url": "https://example.test/pull/9",
                "body": "text\n\n%s\n" % marker_line(STAGING, STAGING, SOURCE),
                "headRefName": "somebody-elses-line",
            }
            gh = support.IndexingGh(search=[elsewhere])

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(compose_proposal.STATUS_ALREADY_OPEN, result.status)
            self.assertEqual(9, result.pr_number)
            self.assertEqual([], gh.created())

    def test_a_review_found_for_the_same_line_of_work_is_not_opened_twice(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            gh = RecordingGh(head=[{"number": 77, "url": "https://example.test/pull/77"}])

            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_RESUMED, result.status)
            self.assertEqual(77, result.pr_number)
            self.assertEqual([], gh.created())


    def test_a_folder_left_on_no_line_of_work_still_opens_the_review(self):
        """A folder with no name on it is put back on its own before sending."""
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            broken = RecordingGh(raise_on_create=True)
            with self.assertRaises(RuntimeError):
                compose_proposal.propose(
                    staged, root, base_id, gh=broken, now=TODAY, session_id="sess-1"
                )
            folder = os.path.join(paths.worktrees_dir(base_id), STAGING)
            support.git(["checkout", "-q", "--detach", "HEAD"], cwd=folder)
            support.git(["branch", "-q", "-D", BRANCH], cwd=folder)

            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(
                compose_proposal.STATUS_OPENED, result.status, result.reasons
            )
            self.assertEqual(BRANCH, result.branch)
            self.assertIn(worktree.CODE_REBRANCHED, result.codes)
            self.assertEqual(1, len(gh.created()))
            self.assertTrue(ref_of(root, "refs/remotes/origin/" + BRANCH))

    def test_a_working_folder_that_cannot_be_prepared_is_reported_not_raised(self):
        """A failure in this seat's own folder is this run's to report."""
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            gh = RecordingGh()

            result = compose_proposal.propose(
                staged,
                root,
                base_id,
                gh=gh,
                now=TODAY,
                session_id="sess-1",
                runner=RefusingGit(),
            )

            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn(compose_proposal.CODE_GIT_FAILED, result.codes)
            self.assertIn("could not prepare", result.reasons[0])
            self.assertEqual([], gh.created())
            self.assertEqual([], plain_language.find_banned(result.reasons[0]))


class RefusingGit(GitRunner):
    """A runner that answers everything but refuses to save anything."""

    def check(self, args, cwd=None, timeout=20, input=None):
        from gtmbase.errors import GitError

        if list(args)[:1] in (["commit"], ["add"]) or "commit" in [
            str(item) for item in args
        ]:
            raise GitError("git-failed", code="git-failed")
        return GitRunner.check(self, args, cwd=cwd, timeout=timeout, input=input)


# --- The file moved on --------------------------------------------------------


class TestTheFileMovedOn(unittest.TestCase):
    def test_a_heading_that_is_gone_is_reported_and_nothing_is_sent(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            without = support.ICP_TEXT.replace("## Firmographics", "## Who we sell to")
            support.write(os.path.join(root, ICP), without)
            support.git(["commit", "-q", "-am", "renamed"], cwd=root)
            support.git(["push", "-q", "origin", "main"], cwd=root)

            staged = stage(root)
            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )

            self.assertEqual(compose_proposal.STATUS_CONFLICT, result.status)
            self.assertIn(ICP, result.reasons[0])
            self.assertEqual([], gh.created())
            self.assertFalse(
                os.path.isdir(os.path.join(paths.worktrees_dir(base_id), STAGING))
            )

    def test_raising_it_again_once_the_heading_is_back_works(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            without = support.ICP_TEXT.replace("## Firmographics", "## Who we sell to")
            support.write(os.path.join(root, ICP), without)
            support.git(["commit", "-q", "-am", "renamed"], cwd=root)
            support.git(["push", "-q", "origin", "main"], cwd=root)
            staged = stage(root)
            compose_proposal.propose(
                staged, root, base_id, gh=RecordingGh(), now=TODAY, session_id="sess-1"
            )

            support.write(os.path.join(root, ICP), support.ICP_TEXT)
            support.git(["commit", "-q", "-am", "put back"], cwd=root)
            support.git(["push", "-q", "origin", "main"], cwd=root)

            gh = RecordingGh()
            again = compose_proposal.reopen_from_opened(
                STAGING, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, again.status, again.reasons)
            self.assertEqual(1, len(gh.created()))


# --- The two conditions on anything leaving the computer ----------------------


class TestNothingLeavesUntilBothConditionsHold(unittest.TestCase):
    def test_a_base_whose_first_backup_was_never_reviewed_refuses(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox, reviewed=False)
            staged = stage(root)
            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn(gate.sentence_for(gate.REASON_FIRST_PUSH), result.reasons)
            self.assertEqual([], gh.calls)

    def test_a_session_that_read_the_persons_own_documents_refuses(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            marker.write_sources_read_marker("sess-1")
            staged = stage(root)
            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn(gate.sentence_for(gate.REASON_SOURCES_READ), result.reasons)
            self.assertEqual([], gh.calls)

    def test_once_both_are_settled_the_proposal_opens(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox, reviewed=False)
            marker.write_sources_read_marker("sess-1")
            staged = stage(root)

            state.update_seat(base_id, first_push_reviewed=True)
            marker.clear_sources_read_marker()

            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, result.status, result.reasons)

    def test_the_session_is_read_from_this_seat_when_none_is_given(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            state.update_seat(base_id, session_id="sess-9")
            marker.write_sources_read_marker("sess-9")
            staged = stage(root)
            result = compose_proposal.propose(
                staged, root, base_id, gh=RecordingGh(), now=TODAY
            )
            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn(gate.sentence_for(gate.REASON_SOURCES_READ), result.reasons)


# --- A change somebody made by hand -------------------------------------------


NEW_SECTION = "Companies of twenty to two hundred people, with one to five marketers.\n"
STATED_SOURCE = (
    "The quarterly review deck, slide four, said every customer we kept last "
    "year had between twenty and two hundred people."
)


def hand_edit(root):
    text = support.ICP_TEXT.replace("Companies of any size.", NEW_SECTION.strip())
    support.write(os.path.join(root, ICP), text)


class TestAChangeSomebodyMadeByHand(unittest.TestCase):
    def test_it_becomes_a_proposal_and_the_change_stays_where_they_left_it(self):
        with support.Sandbox() as sandbox:
            root, base_id, remote = base_with_a_shared_copy(sandbox)
            hand_edit(root)

            staged = compose_proposal.stage_local_edit(
                root, base_id, STATED_SOURCE, now=TODAY
            )
            staging = formats.ProposalStaging.parse(support.read(staged)).validate()
            self.assertEqual("local-edit", staging.origin)
            self.assertEqual("local-edit", staging.intake_path)
            self.assertTrue(staging.third_party)
            self.assertIsNone(staging.source_id)
            self.assertEqual([ICP], staging.target_paths)
            self.assertEqual(
                ids.staging_id("local-edit", ICP, "local-edit", 0), staging.staging_id
            )
            self.assertIn(STATED_SOURCE, staging.excerpt)

            gh = RecordingGh()
            result = compose_proposal.propose(
                staged, root, base_id, gh=gh, now=TODAY, session_id="sess-1"
            )
            self.assertEqual(compose_proposal.STATUS_OPENED, result.status, result.reasons)

            branch = constants.PROPOSAL_BRANCH_PREFIX + staging.staging_id
            self.assertIn("one to five marketers", show(remote, branch, ICP))
            record_name = "%s/%s-%s.md" % (
                constants.CORRECTIONS_DIR,
                TODAY.isoformat(),
                staging.staging_id,
            )
            record = formats.CorrectionsFile.parse(show(remote, branch, record_name))
            record.validate()
            self.assertTrue(record.third_party)
            self.assertEqual("local-edit", record.intake_path)
            self.assertEqual("none", record.mode)
            self.assertIsNone(record.entry_id)

            # Their own change is still in front of them.
            self.assertIn("one to five marketers", support.read(os.path.join(root, ICP)))
            self.assertIn(ICP, status_of(root))

    def test_a_change_outside_the_context_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            support.write(
                os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n%s\nsomething\n" % OWNER
            )
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(root, base_id, STATED_SOURCE)
            self.assertEqual(
                compose_proposal.CODE_LOCAL_OUTSIDE, getattr(caught.exception, "code", None)
            )

    def test_a_change_to_the_map_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            support.write(
                os.path.join(root, constants.MAP_PATH),
                support.MAP_TEXT + "\nsomething new\n",
            )
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(root, base_id, STATED_SOURCE)
            self.assertEqual(
                compose_proposal.CODE_LOCAL_MAP, getattr(caught.exception, "code", None)
            )

    def test_a_change_larger_than_this_path_carries_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            long_text = "many more words about the customer profile " * 200
            support.write(
                os.path.join(root, ICP),
                support.ICP_TEXT.replace("Companies of any size.", long_text),
            )
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(root, base_id, STATED_SOURCE)
            self.assertEqual(
                compose_proposal.CODE_LOCAL_TOO_LONG, getattr(caught.exception, "code", None)
            )

    def test_a_source_holding_a_contact_detail_is_refused_before_anything_else(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            hand_edit(root)
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(
                    root, base_id, "told to me by buyer.person@acme-fintech.example"
                )
            self.assertEqual("email", getattr(caught.exception, "code", None))
            self.assertNotIn("acme-fintech", str(caught.exception))

    def test_nothing_changed_by_hand_is_said_plainly(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(root, base_id, STATED_SOURCE)
            self.assertEqual(
                compose_proposal.CODE_LOCAL_NOTHING, getattr(caught.exception, "code", None)
            )


# --- The whole way round ------------------------------------------------------


class TestTheWholeWayRound(unittest.TestCase):
    def test_the_tool_on_the_path_is_the_one_that_runs_when_none_is_handed_in(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            log = os.path.join(sandbox.path, "gh-calls.jsonl")
            saved_path = os.environ.get("PATH")
            saved_log = os.environ.get("GH_FAKE_LOG")
            os.environ["PATH"] = FAKES_DIR + os.pathsep + saved_path
            os.environ["GH_FAKE_LOG"] = log
            try:
                result = compose_proposal.propose(
                    staged, root, base_id, now=TODAY, session_id="sess-1"
                )
            finally:
                os.environ["PATH"] = saved_path
                if saved_log is None:
                    os.environ.pop("GH_FAKE_LOG", None)
                else:
                    os.environ["GH_FAKE_LOG"] = saved_log

            self.assertEqual(compose_proposal.STATUS_OPENED, result.status, result.reasons)
            recorded = [json.loads(line) for line in support.read(log).splitlines()]
            created = [row for row in recorded if row["argv"][:2] == ["pr", "create"]]
            self.assertEqual(1, len(created))
            self.assertIn("--body-file", created[0]["argv"])
            self.assertEqual(1, result.pr_number)

    def test_once_it_is_accepted_the_file_counts_as_confirmed_against_the_decision(self):
        with support.Sandbox() as sandbox:
            root, base_id, remote = base_with_a_shared_copy(sandbox)
            staged = stage(root)
            compose_proposal.propose(
                staged, root, base_id, gh=RecordingGh(), now=TODAY, session_id="sess-1"
            )

            # Accepting it, the way the GitHub page would.
            second = os.path.join(sandbox.path, "reviewer")
            support.git(["clone", "-q", remote, second], cwd=sandbox.path)
            support.git(["fetch", "-q", "origin", BRANCH], cwd=second)
            support.git(["merge", "--ff-only", "-q", "FETCH_HEAD"], cwd=second)
            support.git(["push", "-q", "origin", "main"], cwd=second)

            fresh = os.path.join(sandbox.path, "fresh")
            support.git(["clone", "-q", remote, fresh], cwd=sandbox.path)

            entry_path = "%s/%s.md" % (constants.DECISIONS_DIR, STAGING)
            record_path = "%s/%s-%s.md" % (
                constants.CORRECTIONS_DIR,
                TODAY.isoformat(),
                STAGING,
            )
            self.assertTrue(os.path.isfile(os.path.join(fresh, entry_path)))
            self.assertTrue(os.path.isfile(os.path.join(fresh, record_path)))

            entry = formats.LedgerEntry.parse(support.read(os.path.join(fresh, entry_path)))
            entry.validate(TODAY)
            record = formats.CorrectionsFile.parse(
                support.read(os.path.join(fresh, record_path))
            )
            record.validate()

            introduced = ref_of(fresh, "HEAD")
            names = subprocess.run(
                ["git", "show", "--name-only", "--format=", introduced],
                cwd=fresh,
                stdout=subprocess.PIPE,
            ).stdout.decode("utf-8").split()
            icp_text = support.read(os.path.join(fresh, ICP))

            report = stale.compute(
                TODAY,
                {},
                [stale.ContextFileInfo(ICP, owners=[OWNER], exists=True)],
                [stale.LedgerInput(entry=entry, path=entry_path)],
                [],
                [
                    stale.CorrectionRecord(
                        file=record,
                        introducing_commit=introduced,
                        co_modified_paths=names,
                        content_hash_at_commit=ids.content_hash(icp_text),
                    )
                ],
            )
            self.assertEqual([], [item.code for item in report.malformed])
            for flag in report.file_flags:
                self.assertNotIn(STAGING, flag.entry_ids or [])


# --- The skill a person reads -------------------------------------------------


SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "propose-change")


class TestTheSkillAPersonReads(unittest.TestCase):
    def test_the_skill_and_its_reference_are_written_in_plain_words(self):
        plain_language.assert_plain(self, os.path.join(SKILL_DIR, "SKILL.md"))
        plain_language.assert_plain(
            self, os.path.join(SKILL_DIR, "references", "pr-body-rules.md")
        )

    def test_the_skill_names_itself_and_says_when_to_use_it(self):
        text = support.read(os.path.join(SKILL_DIR, "SKILL.md"))
        self.assertTrue(text.startswith("---\n"))
        block = text.split("---\n")[1]
        self.assertIn("name: propose-change", block)
        self.assertIn("description:", block)
        self.assertIn("scripts/propose.py", text)
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", text)

    def test_the_script_finds_the_library_from_where_the_skill_sits(self):
        script = os.path.join(SKILL_DIR, "scripts", "propose.py")
        self.assertTrue(os.path.isfile(script))
        finished = subprocess.run(
            ["python3", script, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(script),
        )
        self.assertEqual(0, finished.returncode, finished.stderr.decode("utf-8"))
        self.assertIn("--staging", finished.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
