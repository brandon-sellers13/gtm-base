"""The four numbers one seat can honestly report for the last four weeks."""

import datetime
import os
import unittest

import plain_language
import support

from gtmbase import constants, formats, ids, report, state
from gtmbase.validate import marker_line

TODAY = datetime.date(2026, 6, 5)
IN_WINDOW = "2026-05-20"
OUT_OF_WINDOW = "2026-04-01"

CAUGHT_ENTRY = "stg-" + "a" * 16
TYPED_ENTRY = "stg-" + "b" * 16
CAUGHT_RECORD = "stg-" + "c" * 16
TYPED_RECORD = "stg-" + "d" * 16
ICP = "context/strategy/icp.md"
OWNER = "owner@example.com"


def entry(entry_id, origin="ledger"):
    return formats.LedgerEntry(
        id=entry_id,
        decided_on="2026-05-18",
        written_on="2026-05-19",
        decided_by="Jane Doe",
        source="the weekly go to market meeting",
        review_by="2026-09-01",
        origin=origin,
        status="open",
        affects=[ICP],
        body="We now sell to companies of twenty to two hundred people.",
    ).render()


def record(staging_id, entry_id, date=IN_WINDOW):
    return formats.CorrectionsFile(
        kind="correction",
        date=date,
        staging_id=staging_id,
        entry_id=entry_id,
        source_id=None,
        intake_path="ledger",
        mode="none",
        third_party=False,
        content_hash="0" * 64,
        touched_paths=[ICP],
        correction_class="wrong-definition",
        marker=marker_line(staging_id, entry_id, None),
        what_changed="The profile now names the size of company.",
        why="The decision said so and the document did not.",
    ).validate().render()


def build_history(sandbox):
    """A base holding one decision GTM Base wrote down and one somebody typed."""
    root, base_id, _remote = support.base_with_a_shared_copy(sandbox)

    support.write(
        os.path.join(root, constants.DECISIONS_DIR, CAUGHT_ENTRY + ".md"),
        entry(CAUGHT_ENTRY),
    )
    support.git(["add", "-A"], cwd=root)
    support.git(
        ["commit", "-q", "-m", "Proposal %s: bring the profile in line" % CAUGHT_RECORD],
        cwd=root,
    )

    support.write(
        os.path.join(root, constants.DECISIONS_DIR, TYPED_ENTRY + ".md"),
        entry(TYPED_ENTRY),
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "wrote down what we decided"], cwd=root)

    support.write(
        os.path.join(
            root, constants.CORRECTIONS_DIR, "%s-%s.md" % (IN_WINDOW, CAUGHT_RECORD)
        ),
        record(CAUGHT_RECORD, CAUGHT_ENTRY),
    )
    support.write(
        os.path.join(
            root, constants.CORRECTIONS_DIR, "%s-%s.md" % (IN_WINDOW, TYPED_RECORD)
        ),
        record(TYPED_RECORD, TYPED_ENTRY),
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "two accepted records"], cwd=root)

    ask(base_id, "yes", IN_WINDOW)
    ask(base_id, "not-now", IN_WINDOW)
    ask(base_id, "no", IN_WINDOW)
    ask(base_id, "unanswered", IN_WINDOW)
    ask(base_id, "yes", OUT_OF_WINDOW)

    state.update_seat(base_id, first_run_path="drop")
    state.upsert_row(
        base_id,
        ids.source_id_for_text("a call somebody dropped in"),
        status="processed",
        intake_path="drop",
    )
    state.upsert_row(
        base_id,
        ids.source_id_for_text("a call a connected tool brought in"),
        status="processed",
        intake_path="connected",
    )
    return root, base_id


def ask(base_id, outcome, date):
    question = ids.question_id(ICP, "ledger", None, "sess-1")
    state.append_asked(
        base_id,
        question,
        ICP,
        "ledger",
        outcome,
        datetime.date(*[int(part) for part in date.split("-")]),
    )


def reviews():
    """Three proposals on the shared copy: one accepted, one turned down, one open."""
    return [
        {
            "number": 1,
            "state": "MERGED",
            "mergedAt": IN_WINDOW,
            "closedAt": IN_WINDOW,
            "createdAt": IN_WINDOW,
            "body": "words\n" + marker_line(CAUGHT_RECORD, CAUGHT_ENTRY, None),
        },
        {
            "number": 2,
            "state": "CLOSED",
            "mergedAt": None,
            "closedAt": IN_WINDOW,
            "createdAt": IN_WINDOW,
            "body": "words\n" + marker_line(TYPED_RECORD, TYPED_ENTRY, None),
        },
        {
            "number": 3,
            "state": "OPEN",
            "mergedAt": None,
            "closedAt": None,
            "createdAt": IN_WINDOW,
            "body": "words\n" + marker_line("stg-" + "e" * 16, None, None),
        },
        {
            "number": 4,
            "state": "CLOSED",
            "mergedAt": None,
            "closedAt": OUT_OF_WINDOW,
            "createdAt": OUT_OF_WINDOW,
            "body": "words\n" + marker_line("stg-" + "f" * 16, None, None),
        },
        {
            "number": 5,
            "state": "CLOSED",
            "mergedAt": None,
            "closedAt": IN_WINDOW,
            "createdAt": IN_WINDOW,
            "body": "somebody else's review, with no marker in it",
        },
    ]


class TestTheFourNumbers(unittest.TestCase):
    def summary(self, sandbox):
        root, base_id = build_history(sandbox)
        return report.four_week_summary(
            root, base_id, gh=support.RecordingGh(search=reviews()), today=TODAY
        )

    def test_a_decision_gtm_base_wrote_down_is_a_catch_and_a_typed_one_is_not(self):
        with support.Sandbox() as sandbox:
            found = self.summary(sandbox)["catches"]

            self.assertEqual(1, found["count"])
            self.assertEqual(2, found["records_in_window"])
            self.assertEqual([CAUGHT_ENTRY], [item["entry_id"] for item in found["entries"]])

    def test_the_yes_rate_counts_put_off_and_never_answered_as_well(self):
        with support.Sandbox() as sandbox:
            yes = self.summary(sandbox)["yes_rate"]

            self.assertEqual(4, yes["asked"])
            self.assertEqual(1, yes["yes"])
            self.assertEqual(1, yes["no"])
            self.assertEqual(1, yes["not_now"])
            self.assertEqual(1, yes["unanswered"])
            self.assertAlmostEqual(0.25, yes["rate"])

    def test_the_turned_down_rate_counts_only_this_base_and_only_this_window(self):
        with support.Sandbox() as sandbox:
            turned = self.summary(sandbox)["rejection_rate"]

            self.assertTrue(turned["read"])
            self.assertEqual(3, turned["opened"])
            self.assertEqual(1, turned["accepted"])
            self.assertEqual(1, turned["turned_down"])
            self.assertAlmostEqual(1.0 / 3.0, turned["rate"])

    def test_the_first_run_share_comes_from_the_rows_and_the_seat(self):
        with support.Sandbox() as sandbox:
            first = self.summary(sandbox)["first_run"]

            self.assertEqual("drop", first["first_run_path"])
            self.assertEqual(1, first["connected"])
            self.assertEqual(1, first["drop"])
            self.assertEqual(0, first["other"])
            self.assertAlmostEqual(0.5, first["share_connected"])

    def test_every_number_is_labelled_as_this_seat_and_reads_in_plain_words(self):
        with support.Sandbox() as sandbox:
            text = report.render_summary(self.summary(sandbox))

            self.assertIn("These are this seat's numbers.", text)
            self.assertIn("Things GTM Base caught: 1.", text)
            self.assertEqual([], plain_language.find_banned(text))
            self.assertEqual([], plain_language.find_dashes(text))


class TestTheWindow(unittest.TestCase):
    """The window is the 28 days the summary says it is, and not 29."""

    def test_today_counts_and_the_day_before_the_window_does_not(self):
        with support.Sandbox() as sandbox:
            root, base_id = build_history(sandbox)
            oldest = TODAY - datetime.timedelta(days=report.WINDOW_DAYS - 1)
            ask(base_id, "yes", TODAY.isoformat())
            ask(base_id, "yes", oldest.isoformat())
            ask(base_id, "yes", (oldest - datetime.timedelta(days=1)).isoformat())

            summary = report.four_week_summary(
                root, base_id, gh=support.RecordingGh(search=reviews()), today=TODAY
            )

            self.assertEqual(28, summary["window_days"])
            self.assertEqual(oldest.isoformat(), summary["from"])
            self.assertEqual(TODAY.isoformat(), summary["to"])
            # The four the history already holds, plus today and the oldest day
            # the window covers. The day before that one is left out.
            self.assertEqual(6, summary["yes_rate"]["asked"])

    def test_the_summary_says_the_number_of_days_it_counts(self):
        with support.Sandbox() as sandbox:
            root, base_id = build_history(sandbox)
            summary = report.four_week_summary(
                root, base_id, gh=support.RecordingGh(), today=TODAY
            )

            text = report.render_summary(summary)

            self.assertIn("The last 28 days, from 2026-05-09 to 2026-06-05.", text)


class TestABaseWithNoHistoryAtAll(unittest.TestCase):
    def test_every_number_is_reported_as_zero_and_no_rate_is_invented(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)

            summary = report.four_week_summary(
                root, base_id, gh=support.RecordingGh(), today=TODAY
            )

            self.assertEqual(0, summary["catches"]["count"])
            self.assertEqual(0, summary["yes_rate"]["asked"])
            self.assertIsNone(summary["yes_rate"]["rate"])
            self.assertEqual(0, summary["rejection_rate"]["opened"])
            self.assertIsNone(summary["rejection_rate"]["rate"])
            self.assertEqual(0, summary["first_run"]["connected"])
            self.assertEqual(0, summary["first_run"]["drop"])
            self.assertIsNone(summary["first_run"]["share_connected"])

            text = report.render_summary(summary)
            self.assertIn("Things GTM Base caught: 0.", text)
            self.assertIn("Questions asked: 0.", text)
            self.assertIn("Proposals raised: 0.", text)
            self.assertIn("no yes rate", text)
            self.assertEqual([], plain_language.find_banned(text))
            self.assertEqual([], plain_language.find_dashes(text))


class TestWhenTheSharedCopyCannotBeRead(unittest.TestCase):
    def test_it_says_it_has_no_number_rather_than_reporting_zero(self):
        class Refusing(object):
            def __call__(self, args, cwd=None, stdin=None):
                return 1, ""

        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)

            summary = report.four_week_summary(
                root, base_id, gh=Refusing(), today=TODAY
            )

            self.assertFalse(summary["rejection_rate"]["read"])
            self.assertIn("no number", report.render_summary(summary))


if __name__ == "__main__":
    unittest.main()
