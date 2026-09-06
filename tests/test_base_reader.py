"""Reading a real base into the values the stale library works on."""

import datetime
import os
import unittest

import support

from gtmbase import (
    base_reader,
    compose_proposal,
    constants,
    formats,
    ids,
    stale,
)
from gtmbase.validate import marker_line

TODAY = datetime.date(2026, 6, 5)
STAGING = "stg-" + "d" * 16
ICP = "context/strategy/icp.md"
POSITIONING = "context/strategy/positioning.md"
OWNER = "owner@example.com"
STRANGER = "stranger@example.com"

POSITIONING_TEXT = (
    "---\n"
    "kind: positioning\n"
    "owner: owner@example.com\n"
    "last_confirmed: 2026-01-01\n"
    "sources: [a note dated 2026-02-01]\n"
    "status: draft\n"
    "---\n"
    "\n"
    "# Positioning\n"
    "\n"
    "## Where we sit\n"
    "\n"
    "Somewhere.\n"
)


def day_of_the_newest_change(root):
    """The day the shared line of work last moved, as git itself writes it."""
    return (
        support.git(
            ["log", "-1", "--format=%ad", "--date=short", "main"], cwd=root
        )
        .stdout.decode("utf-8")
        .strip()
    )


def two_file_staging():
    """One prepared change carrying a new decision and touching two files."""
    entry = formats.LedgerEntry(
        id=STAGING,
        decided_on="2026-06-02",
        written_on="2026-06-04",
        decided_by="Jane Doe",
        source="the weekly go to market meeting",
        review_by="2026-09-01",
        origin="ledger",
        status="open",
        affects=[ICP, POSITIONING],
        body="We now sell to companies of twenty to two hundred people.",
    )
    body = formats.render_pr_body(
        {
            "before": "Neither document says which companies we sell to.",
            "after": "Both documents say we sell to companies of twenty to two hundred people.",
            "why": "The team decided it and neither document was brought in line.",
            "evidence": "The team said so at the weekly go to market meeting.",
            "confidence": "high",
            "rule_changed": "None",
            "marker": marker_line(STAGING, STAGING, None),
        }
    )
    staging = formats.ProposalStaging(
        staging_id=STAGING,
        origin="ledger",
        intake_path="ledger",
        target_paths=[ICP, POSITIONING],
        sequence=0,
        rule_change=False,
        confidence="high",
        third_party=False,
        pr_body=body,
        source_id=None,
        decision_block=entry.render(),
        edits=[
            formats.Edit(
                ICP,
                "## Decisions to reflect",
                "add",
                "We sell to companies of twenty to two hundred people.\n",
            ),
            formats.Edit(
                POSITIONING,
                "## Decisions to reflect",
                "add",
                "We are the choice for companies of twenty to two hundred people.\n",
            ),
        ],
        excerpt="so from now on we only go after companies of that size",
    )
    return staging.validate()


class TestReadingABase(unittest.TestCase):
    def test_it_reads_the_settings_the_documents_and_the_decisions(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            support.write(os.path.join(root, POSITIONING), POSITIONING_TEXT)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a second document"], cwd=root)

            inputs = base_reader.read_base(root, base_id, today=TODAY)

            self.assertEqual(30, inputs.settings.confirmation_threshold_days)
            self.assertEqual(7, inputs.settings.not_now_days)
            by_path = inputs.by_path
            self.assertIn(ICP, by_path)
            self.assertIn(POSITIONING, by_path)
            self.assertEqual([OWNER], by_path[ICP].owners)
            self.assertEqual(
                datetime.date(2026, 2, 1), by_path[POSITIONING].sources_date
            )
            self.assertEqual(OWNER, inputs.seat_email)
            self.assertEqual("main", inputs.default_branch)
            self.assertTrue(inputs.has_remote)
            self.assertEqual([], inputs.ledger)
            self.assertEqual([], inputs.corrections)

    def test_a_base_with_no_shared_copy_says_so(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "alone")
            base_id = ids.base_id_random()
            support.make_base(root, base_id=base_id)

            inputs = base_reader.read_base(root, base_id, today=TODAY)

            self.assertFalse(inputs.has_remote)
            self.assertFalse(inputs.seat.has_remote)

    def test_a_confirmation_is_paired_with_whoever_saved_it(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            line = formats.ConfirmationLine(
                date="2026-06-05", time="12:00:00Z", file=ICP, trigger="threshold"
            )
            support.write(
                os.path.join(
                    root, constants.CONFIRMATIONS_DIR, ICP.replace("/", "--")
                ),
                line.render() + "\n",
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a confirmation"], cwd=root)

            inputs = base_reader.read_base(root, base_id, today=TODAY)

            self.assertEqual(1, len(inputs.confirmations))
            self.assertEqual(OWNER, inputs.confirmations[0].author_email)


class TestTheOneHashOverEveryFileAProposalTouched(unittest.TestCase):
    """Fix A, the whole way round: two files, accepted, read back, both settled."""

    def test_a_two_file_proposal_settles_both_files_once_it_is_accepted(self):
        with support.Sandbox() as sandbox:
            root, base_id, remote = support.base_with_a_shared_copy(sandbox)
            support.write(os.path.join(root, POSITIONING), POSITIONING_TEXT)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a second document"], cwd=root)
            support.git(["push", "-q", "origin", "main"], cwd=root)
            staged = os.path.join(
                root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md"
            )
            support.write(staged, two_file_staging().render())

            opened = compose_proposal.propose(
                staged,
                root,
                base_id,
                gh=support.RecordingGh(),
                now=TODAY,
                session_id="sess-1",
            )
            self.assertEqual(
                compose_proposal.STATUS_OPENED, opened.status, opened.reasons
            )

            # Accepting it, the way the GitHub page would.
            reviewer = os.path.join(sandbox.path, "reviewer")
            support.git(["clone", "-q", remote, reviewer], cwd=sandbox.path)
            support.git(
                ["fetch", "-q", "origin", constants.PROPOSAL_BRANCH_PREFIX + STAGING],
                cwd=reviewer,
            )
            support.git(["merge", "--ff-only", "-q", "FETCH_HEAD"], cwd=reviewer)
            support.git(["push", "-q", "origin", "main"], cwd=reviewer)

            fresh = os.path.join(sandbox.path, "fresh")
            support.git(["clone", "-q", remote, fresh], cwd=sandbox.path)

            inputs = base_reader.read_base(fresh, base_id, today=TODAY)

            self.assertEqual(1, len(inputs.corrections))
            record = inputs.corrections[0]
            self.assertEqual(
                record.file.content_hash, record.content_hash_at_commit
            )
            self.assertIn(ICP, record.co_modified_paths)
            self.assertIn(POSITIONING, record.co_modified_paths)

            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
            )
            self.assertEqual([], [item.code for item in report.malformed])
            # The change went on the end, so whoever accepted it cannot be told
            # apart from the seat that wrote it, and that seat owns both files.
            # By Brandon's rule of 2026-09-05 that is the owner saying both
            # files are right, so neither is flagged at all. The map is a
            # context file nothing touched, so it stays on the list.
            self.assertEqual(
                [ICP, POSITIONING],
                sorted(set([ICP, POSITIONING]) - set(
                    flag.path for flag in report.file_flags
                )),
            )
            accepted_on = day_of_the_newest_change(fresh)
            for path in (ICP, POSITIONING):
                self.assertEqual(OWNER, report.merge_confirmations[path].merged_by)
                self.assertEqual(
                    accepted_on, report.merge_confirmations[path].date.isoformat()
                )

    def test_a_record_whose_hash_no_longer_matches_settles_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            record = formats.CorrectionsFile(
                kind="correction",
                date="2026-06-04",
                staging_id=STAGING,
                entry_id=STAGING,
                source_id=None,
                intake_path="ledger",
                mode="none",
                third_party=False,
                content_hash="1" * 64,
                touched_paths=[ICP],
                correction_class="wrong-definition",
                marker=marker_line(STAGING, STAGING, None),
                what_changed="Something changed.",
                why="Because the decision said so.",
            )
            support.write(
                os.path.join(root, constants.CORRECTIONS_DIR, "2026-06-04-x.md"),
                record.validate().render(),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "an accepted record"], cwd=root)

            inputs = base_reader.read_base(root, base_id, today=TODAY)

            self.assertEqual(1, len(inputs.corrections))
            self.assertNotEqual(
                "1" * 64, inputs.corrections[0].content_hash_at_commit
            )


class TestWhoAcceptedTheChange(unittest.TestCase):
    """The address and the day on the change that put a record in the base."""

    def _accepted(self, sandbox, how, author=None):
        """Open a proposal, accept it the way `how` says, and read it back."""
        root, base_id, remote = support.base_with_a_shared_copy(sandbox)
        support.write(os.path.join(root, POSITIONING), POSITIONING_TEXT)
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a second document"], cwd=root)
        support.git(["push", "-q", "origin", "main"], cwd=root)
        staged = os.path.join(root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md")
        support.write(staged, two_file_staging().render())

        opened = compose_proposal.propose(
            staged,
            root,
            base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
        )
        self.assertEqual(compose_proposal.STATUS_OPENED, opened.status, opened.reasons)

        reviewer = os.path.join(sandbox.path, "reviewer")
        support.git(["clone", "-q", remote, reviewer], cwd=sandbox.path)
        support.git(
            ["fetch", "-q", "origin", constants.PROPOSAL_BRANCH_PREFIX + STAGING],
            cwd=reviewer,
        )
        proposed_author = support.git(
            ["log", "-1", "--format=%ae", "FETCH_HEAD"], cwd=reviewer
        ).stdout.decode("utf-8").strip()
        support.git(how + ["-q", "FETCH_HEAD"], cwd=reviewer, author=author)
        support.git(["push", "-q", "origin", "main"], cwd=reviewer)

        fresh = os.path.join(sandbox.path, "fresh")
        support.git(["clone", "-q", remote, fresh], cwd=sandbox.path)
        inputs = base_reader.read_base(fresh, base_id, today=TODAY)
        self.assertEqual(1, len(inputs.corrections))
        return inputs.corrections[0], proposed_author, fresh

    def test_a_change_of_its_own_names_whoever_accepted_it(self):
        with support.Sandbox() as sandbox:
            record, _proposed, fresh = self._accepted(
                sandbox, ["merge", "--no-ff", "-m", "accepting it"]
            )

            self.assertEqual(OWNER, record.merged_by_email)
            self.assertEqual(
                day_of_the_newest_change(fresh), record.merged_on.isoformat()
            )

    def test_a_change_of_its_own_names_the_accepter_and_not_the_writer(self):
        with support.Sandbox() as sandbox:
            record, proposed, _fresh = self._accepted(
                sandbox,
                ["merge", "--no-ff", "-m", "accepting it"],
                author=STRANGER,
            )

            self.assertEqual(OWNER, proposed)
            self.assertEqual(STRANGER, record.merged_by_email)

    def test_a_change_put_on_the_end_names_whoever_wrote_it(self):
        with support.Sandbox() as sandbox:
            record, proposed, _fresh = self._accepted(
                sandbox, ["merge", "--ff-only"]
            )

            self.assertEqual(proposed, record.merged_by_email)
            self.assertEqual(OWNER, record.merged_by_email)


class TestTheOwnerAcceptingTheChangeIsAYes(unittest.TestCase):
    """SC1 the whole way round, with Brandon's rule of 2026-09-05 applied."""

    def test_the_file_is_confirmed_and_nothing_at_all_is_flagged(self):
        with support.Sandbox() as sandbox:
            root, base_id, remote = support.base_with_a_shared_copy(sandbox)
            support.write(os.path.join(root, POSITIONING), POSITIONING_TEXT)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a second document"], cwd=root)
            support.git(["push", "-q", "origin", "main"], cwd=root)
            staged = os.path.join(
                root, constants.PROPOSALS_PENDING_DIR, STAGING + ".md"
            )
            support.write(staged, two_file_staging().render())

            opened = compose_proposal.propose(
                staged,
                root,
                base_id,
                gh=support.RecordingGh(),
                now=TODAY,
                session_id="sess-1",
            )
            self.assertEqual(
                compose_proposal.STATUS_OPENED, opened.status, opened.reasons
            )

            # The owner accepts it with a change of their own, which is what
            # the button on the review page writes.
            reviewer = os.path.join(sandbox.path, "reviewer")
            support.git(["clone", "-q", remote, reviewer], cwd=sandbox.path)
            support.git(
                ["fetch", "-q", "origin", constants.PROPOSAL_BRANCH_PREFIX + STAGING],
                cwd=reviewer,
            )
            support.git(
                ["merge", "--no-ff", "-q", "-m", "accepting it", "FETCH_HEAD"],
                cwd=reviewer,
            )
            support.git(["push", "-q", "origin", "main"], cwd=reviewer)

            fresh = os.path.join(sandbox.path, "fresh")
            support.git(["clone", "-q", remote, fresh], cwd=sandbox.path)
            inputs = base_reader.read_base(fresh, base_id, today=TODAY)

            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
            )

            self.assertEqual([], [item.code for item in report.malformed])
            # Neither touched file is flagged for any reason, and neither is
            # anything the owner would be asked about. The map is a context
            # file this proposal never touched, so it is left out of both.
            flagged = set(flag.path for flag in report.file_flags)
            asked = set(item.path for item in report.candidate_questions(OWNER))
            accepted_on = day_of_the_newest_change(fresh)
            for path in (ICP, POSITIONING):
                self.assertNotIn(path, flagged)
                self.assertNotIn(path, asked)
                accepted = report.merge_confirmations[path]
                self.assertEqual(OWNER, accepted.merged_by)
                self.assertEqual(accepted_on, accepted.date.isoformat())
                self.assertEqual(STAGING, accepted.entry_id)


if __name__ == "__main__":
    unittest.main()
