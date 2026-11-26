"""Unit 4.2a of Plan 1: a standard and the source map are base documents.

Before this unit a standard could never be owned, confirmed, flagged or
changed through a prepared change, because every check said "the context
folder" and nothing else. These tests hold the plan's end-to-end scenario: a
prepared change to a standard is approved, recorded with its hashes,
confirmed, clears its flag, and is read by the moment-of-use check as
current. They also hold Unit 2.1's integration scenario that waited for this
one: a context change naming a standard flags it, the review lists it, and the
moment-of-use check on its path returns the block.

Every fixture is written from scratch.
"""

import os
import unittest

import support
import test_approve_local as approving
import test_authority_everywhere as everywhere

from gtmbase import (
    approve_local,
    authority,
    base_reader,
    constants,
    formats,
    moment,
    stale,
    stale_check,
)

STANDARD = "standards/ad-testing.md"
TODAY = approving.TODAY
OWNER = approving.OWNER
NoRemoteRunner = support.NoRemoteRunner
ENTRY = "stg-" + "d" * 16

STANDARD_TEXT = """---
kind: standard
owner: %s
sources: []
status: draft
---

# Ad testing

## Firmographics

Kill a creative that has spent twice its target without a link.
""" % OWNER


def a_base_with_a_standard(sandbox):
    root, base_id = approving.local_base(sandbox)
    support.write(os.path.join(root, STANDARD), STANDARD_TEXT)
    support.write(
        os.path.join(root, constants.STACK_PATH),
        "---\nkind: stack\nowner: %s\nsources: []\nstatus: draft\n---\n\n# Stack\n" % OWNER,
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a standard"], cwd=root)
    return root, base_id


def a_change_naming(root, path):
    support.write(
        os.path.join(root, constants.CHANGES_DIR, ENTRY + ".md"),
        "\n".join(
            [
                "---",
                "id: %s" % ENTRY,
                "kind: change",
                "happened_on: 2026-06-01",
                "written_on: 2026-06-01",
                "noted_by: %s" % OWNER,
                "source: the weekly meeting",
                "affects: [%s]" % path,
                "review_by: 2026-09-01",
                "origin: ledger",
                "status: open",
                "---",
                "",
                "We now judge creative over seven days.",
                "",
            ]
        ),
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a change"], cwd=root)


def report_of(root, base_id):
    inputs = base_reader.read_base(root, base_id, today=TODAY, record_dropped=False)
    return inputs, stale.compute(
        today=TODAY,
        settings=inputs.settings,
        files=inputs.files,
        ledger=inputs.ledger,
        confirmations=inputs.confirmations,
        corrections=inputs.corrections,
        seat=inputs.seat,
    )


class TestReadAsDocuments(unittest.TestCase):
    def test_the_reader_holds_both_with_their_owners(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            inputs, _report = report_of(root, base_id)
            by_path = inputs.by_path
            for path in (STANDARD, constants.STACK_PATH):
                with self.subTest(path=path):
                    self.assertIn(path, by_path)
                    self.assertEqual([OWNER], by_path[path].owners)

    def test_a_standard_in_a_folder_or_a_link_is_not_one(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            support.write(os.path.join(root, "standards", "deeper", "one.md"), STANDARD_TEXT)
            os.symlink(
                os.path.join(root, STANDARD), os.path.join(root, "standards", "linked.md")
            )
            inputs, _report = report_of(root, base_id)
            self.assertNotIn("standards/deeper/one.md", inputs.by_path)
            self.assertNotIn("standards/linked.md", inputs.by_path)


class TestWhenTheReviewAsksAboutOne(unittest.TestCase):
    """A document outside the context folder joins the review's clock once confirmed.

    The source map every base starts with is a starter nobody has written in,
    so asking whether it is still right would ask about nothing. Until someone
    in its authority set first says it is right (an approval does, and so does
    creating one), only a context change naming it flags it.
    """

    def flags_of(self, root, base_id, today=TODAY):
        inputs = base_reader.read_base(root, base_id, today=today, record_dropped=False)
        report = stale.compute(
            today=today,
            settings=inputs.settings,
            files=inputs.files,
            ledger=inputs.ledger,
            confirmations=inputs.confirmations,
            corrections=inputs.corrections,
            seat=inputs.seat,
        )
        return [flag.path for flag in report.file_flags]

    def test_never_confirmed_is_not_asked_about(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            flagged = self.flags_of(root, base_id)
            self.assertNotIn(constants.STACK_PATH, flagged)
            self.assertNotIn(STANDARD, flagged)

    def test_once_confirmed_its_threshold_runs_like_any_documents(self):
        import datetime

        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            path = os.path.join(root, "work", "confirmations", STANDARD.replace("/", "--"))
            support.write(
                path,
                "date=2026-06-01 time=09:00:00Z file=%s trigger=threshold entry=- "
                "question=- run=-\n" % STANDARD,
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "confirmed"], cwd=root)
            self.assertNotIn(STANDARD, self.flags_of(root, base_id))
            later = datetime.date(2026, 9, 1)
            self.assertIn(STANDARD, self.flags_of(root, base_id, today=later))

    def test_a_standard_created_through_gtm_base_starts_confirmed(self):
        from gtmbase import operations

        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [(STANDARD, STANDARD_TEXT)], "A new job.",
                runner=NoRemoteRunner(),
            )
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=approving.NOW,
            )
            self.assertTrue(done.done, done.sentence)
            _inputs, report = report_of(root, base_id)
            self.assertEqual(TODAY, report.confirmed_on.get(STANDARD))


class TestAChangeNamingAStandard(unittest.TestCase):
    """Unit 2.1's scenario: flagged, listed in the review, and blocked at the moment of use."""

    def test_flagged_listed_and_blocked(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            a_change_naming(root, STANDARD)
            _inputs, report = report_of(root, base_id)
            self.assertIn(
                STANDARD,
                [flag.path for flag in report.file_flags if flag.trigger == stale.TRIGGER_LEDGER],
            )
            found = moment.check(root, base_id, STANDARD, runner=NoRemoteRunner(), now=TODAY)
            self.assertTrue(found.flagged)
            review = stale_check.run(
                root, base_id, mode="review", runner=NoRemoteRunner(), now=TODAY
            )
            self.assertIn(STANDARD, [line.path for line in review.review])


class TestTheWholeWayOnAStandard(unittest.TestCase):
    """Integration, end to end: approved, recorded, confirmed, current."""

    def test_end_to_end(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_with_a_standard(sandbox)
            staged = approving.stage(
                root,
                support.staging_template()
                .replace("context/strategy/icp.md", STANDARD)
                .replace("context/icps.md", STANDARD),
            )
            shown, applied = approving.show_and_approve(root, base_id, staged, NoRemoteRunner())
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            record = everywhere.the_record(root)
            self.assertEqual({STANDARD: authority.ROLE_OWNER}, record.approved_roles)
            self.assertEqual(
                {STANDARD: authority.file_hash(root, STANDARD)}, record.approved_hashes
            )
            self.assertIn("twenty to two hundred", support.read(os.path.join(root, STANDARD)))
            _inputs, report = report_of(root, base_id)
            self.assertNotIn(STANDARD, [flag.path for flag in report.file_flags])
            self.assertIsNotNone(report.confirmed_on.get(STANDARD))
            self.assertEqual([], [item for item in report.malformed if STANDARD in str(item)])
            found = moment.check(root, base_id, STANDARD, runner=NoRemoteRunner(), now=TODAY)
            self.assertFalse(found.flagged)
            self.assertEqual(moment.CODE_NOTHING_FLAGGED, found.code)


if __name__ == "__main__":
    unittest.main()
