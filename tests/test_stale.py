"""Unit 9a: the stale-check library, which computes and never fetches."""

import ast
import datetime
import inspect
import os
import unittest

import plain_language
import support  # noqa: F401  (puts the library on the path)

from gtmbase import formats, stale
from gtmbase.validate import marker_line

OWNER = "owner@example.com"
OTHER_OWNER = "second@example.com"
STRANGER = "stranger@example.com"

ICP = "context/strategy/icp.md"
POSITIONING = "context/strategy/positioning.md"
PRICING = "context/plan/pricing.md"

STG = "stg-" + "a" * 16
STG_TWO = "stg-" + "b" * 16
SRC = "src-" + "0" * 24
RUN = "run-2026-06-01-0000aaaa"
OTHER_RUN = "run-2026-06-01-0000bbbb"
HASH = "e" * 64
OTHER_HASH = "f" * 64

# The week SC5 talks about: a decision made on the Tuesday and written down on
# the Thursday, read on the Friday.
TUESDAY = "2026-06-02"
WEDNESDAY = "2026-06-03"
THURSDAY = "2026-06-04"
FRIDAY = "2026-06-05"
TODAY = datetime.date(2026, 6, 5)


def make_entry(**overrides):
    fields = {
        "id": STG,
        "decided_on": TUESDAY,
        "written_on": THURSDAY,
        "decided_by": "Jane Doe",
        "source": "the weekly go to market meeting",
        "review_by": "2026-09-01",
        "origin": "ledger",
        "status": "open",
        "affects": [ICP],
        "run_id": None,
        "body": "We sell to companies of twenty to two hundred people.",
    }
    fields.update(overrides)
    return formats.LedgerEntry(**fields)


def make_input(entry=None, path=None, error=None):
    if path is None:
        path = "work/decisions/%s.md" % (entry.id if entry is not None else STG)
    return stale.LedgerInput(entry=entry, path=path, error=error)


def make_line(path, date, trigger="threshold", entry=None, run=None):
    return formats.ConfirmationLine(
        date=date, time="12:00:00Z", file=path, trigger=trigger, entry=entry, run=run
    )


def make_record(path, date, author=OWNER, trigger="threshold", entry=None, run=None):
    return stale.ConfirmationRecord(
        line=make_line(path, date, trigger=trigger, entry=entry, run=run),
        author_email=author,
        commit="0" * 40,
    )


def make_file(path, owners=(OWNER,), exists=True, sources_date=None, status="draft", kind=""):
    return stale.ContextFileInfo(
        path=path,
        owners=list(owners),
        exists=exists,
        sources_date=sources_date,
        status=status,
        kind=kind,
    )


def make_correction(entry_id=STG, touched=(ICP,), content_hash=HASH):
    return formats.CorrectionsFile(
        kind="correction",
        date=THURSDAY,
        staging_id=STG_TWO,
        entry_id=entry_id,
        source_id=SRC,
        intake_path="ledger",
        mode="decision",
        third_party=False,
        content_hash=content_hash,
        touched_paths=list(touched),
        correction_class="wrong-definition",
        marker=marker_line(STG_TWO, entry_id, SRC),
        what_changed="The profile now says twenty to two hundred people.",
        why="The document was written before the decision.",
    )


def run(
    files,
    ledger=(),
    confirmations=(),
    corrections=(),
    seat=None,
    today=TODAY,
    settings=None,
    owner_email=None,
    map_hints=None,
):
    return stale.compute(
        today,
        settings or stale.MapSettings(),
        files,
        ledger,
        confirmations,
        corrections,
        seat or stale.SeatInput(),
        owner_email=owner_email,
        map_hints=map_hints,
    )


class TestLedgerNewerThanTheFile(unittest.TestCase):
    """SC5 and the confirmations that settle it or fail to."""

    def test_sc5_confirmed_the_day_before_the_entry_was_written_is_flagged(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, WEDNESDAY)],
        )
        self.assertEqual(1, len(report.file_flags))
        flag = report.file_flags[0]
        self.assertEqual(ICP, flag.path)
        self.assertEqual(stale.REASON_LEDGER_NEWER, flag.reason)
        self.assertEqual(stale.TRIGGER_LEDGER, flag.trigger)
        self.assertEqual([STG], flag.entry_ids)
        self.assertEqual(datetime.date(2026, 6, 3), flag.newest_confirmation)

    def test_confirmed_after_the_entry_was_written_is_not_flagged(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, FRIDAY)],
        )
        self.assertEqual([], report.file_flags)

    def test_confirmed_on_the_writing_day_carrying_the_entry_id_is_not_flagged(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, THURSDAY, trigger="ledger", entry=STG)],
        )
        self.assertEqual([], report.file_flags)

    def test_confirmed_on_the_decision_day_without_the_entry_id_is_flagged(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, TUESDAY)],
        )
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual([STG], report.file_flags[0].entry_ids)


class TestCorrectionsFileConfirmation(unittest.TestCase):
    """A merged corrections file only counts with the file and the hash."""

    def _report(self, co_modified, hash_at_commit):
        return run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[],
            corrections=[
                stale.CorrectionRecord(
                    file=make_correction(),
                    introducing_commit="1" * 40,
                    co_modified_paths=co_modified,
                    content_hash_at_commit=hash_at_commit,
                )
            ],
        )

    def test_co_modified_with_a_matching_hash_confirms(self):
        report = self._report([ICP], HASH)
        self.assertEqual([], report.malformed)
        # The decision is settled, so nothing is flagged against the entry. The
        # threshold clock still runs on owner lines only, and there are none.
        self.assertEqual([], report.file_flags[0].entry_ids)
        self.assertEqual(stale.TRIGGER_THRESHOLD, report.file_flags[0].trigger)

    def test_co_modification_settles_the_entry_for_a_file_with_an_old_line(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, WEDNESDAY)],
            corrections=[
                stale.CorrectionRecord(
                    file=make_correction(),
                    introducing_commit="1" * 40,
                    co_modified_paths=[ICP],
                    content_hash_at_commit=HASH,
                )
            ],
        )
        self.assertEqual([], report.file_flags)

    def test_without_co_modification_it_is_malformed_and_confirms_nothing(self):
        report = self._report([], None)
        self.assertEqual([STG], report.file_flags[0].entry_ids)
        self.assertEqual(
            [("corrections", STG_TWO, stale.MALFORMED_NOT_CO_MODIFIED)],
            [tuple(item) for item in report.malformed],
        )

    def test_with_a_different_hash_it_is_malformed_and_confirms_nothing(self):
        report = self._report([ICP], OTHER_HASH)
        self.assertEqual([STG], report.file_flags[0].entry_ids)
        self.assertEqual(
            [("corrections", STG_TWO, stale.MALFORMED_HASH_MISMATCH)],
            [tuple(item) for item in report.malformed],
        )


class TestAcceptingAChangeAsTheOwner(unittest.TestCase):
    """Brandon's rule of 2026-09-05: the owner accepting a change is a yes.

    An accepted record that already settles a decision does one more thing when
    the person who accepted it owns the file: it counts as that owner saying
    the file is right on the day they accepted it, so the clock starts again.
    """

    def _record(self, merged_by=OWNER, merged_on=WEDNESDAY, content_hash=HASH):
        return stale.CorrectionRecord(
            file=make_correction(content_hash=content_hash),
            introducing_commit="1" * 40,
            co_modified_paths=[ICP],
            content_hash_at_commit=HASH,
            merged_by_email=merged_by,
            merged_on=merged_on,
        )

    def test_the_owner_accepting_it_starts_the_clock_again(self):
        # Accepted three days ago, and the file carries no line of its own.
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            corrections=[self._record(merged_on="2026-06-02")],
        )

        self.assertEqual([], report.malformed)
        self.assertEqual([], report.file_flags)
        accepted = report.merge_confirmations[ICP]
        self.assertEqual(datetime.date(2026, 6, 2), accepted.date)
        self.assertEqual(OWNER, accepted.merged_by)
        self.assertEqual(STG, accepted.entry_id)

    def test_an_acceptance_older_than_the_threshold_is_flagged_for_the_calendar(self):
        # The same acceptance, thirty one days back against a thirty day rule.
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            corrections=[self._record(merged_on="2026-05-05")],
        )

        self.assertEqual([], report.malformed)
        self.assertEqual(1, len(report.file_flags))
        flag = report.file_flags[0]
        self.assertEqual(stale.REASON_THRESHOLD, flag.reason)
        self.assertEqual(stale.TRIGGER_THRESHOLD, flag.trigger)
        self.assertEqual([], flag.entry_ids)
        self.assertEqual(datetime.date(2026, 5, 5), flag.newest_confirmation)
        self.assertEqual(0, flag.non_owner_lines)

    def test_somebody_else_accepting_it_settles_the_decision_and_no_more(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            corrections=[self._record(merged_by=STRANGER, merged_on="2026-06-02")],
        )

        self.assertEqual([], report.malformed)
        self.assertEqual({}, report.merge_confirmations)
        self.assertEqual(1, len(report.file_flags))
        flag = report.file_flags[0]
        # The decision is settled, so this is the calendar asking, not the
        # ledger, and nobody has ever said the file itself is right.
        self.assertEqual([], flag.entry_ids)
        self.assertEqual(stale.TRIGGER_THRESHOLD, flag.trigger)
        self.assertEqual(stale.REASON_UNCONFIRMED, flag.reason)
        self.assertIsNone(flag.newest_confirmation)

    def test_a_record_that_fails_the_hash_confers_nothing_even_from_the_owner(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            corrections=[self._record(content_hash=OTHER_HASH, merged_on="2026-06-02")],
        )

        self.assertEqual(
            [("corrections", STG_TWO, stale.MALFORMED_HASH_MISMATCH)],
            [tuple(item) for item in report.malformed],
        )
        self.assertEqual({}, report.merge_confirmations)
        self.assertEqual(1, len(report.file_flags))
        flag = report.file_flags[0]
        self.assertEqual([STG], flag.entry_ids)
        self.assertIsNone(flag.newest_confirmation)

    def test_an_acceptance_settles_a_second_decision_it_never_names(self):
        # The rule says an acceptance counts wherever an owner line counts, so
        # a decision written before it is settled by its date alone.
        report = run(
            files=[make_file(ICP)],
            ledger=[
                make_input(make_entry()),
                make_input(
                    make_entry(
                        id=STG_TWO,
                        decided_on=TUESDAY,
                        written_on=THURSDAY,
                        affects=[ICP],
                    ),
                    path="work/decisions/%s.md" % STG_TWO,
                ),
            ],
            corrections=[self._record(merged_on=FRIDAY)],
        )

        self.assertEqual([], report.file_flags)


class TestNonOwnerLines(unittest.TestCase):
    def test_a_newer_line_from_someone_else_confirms_nothing_and_is_counted(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[
                make_record(ICP, WEDNESDAY),
                make_record(ICP, FRIDAY, author=STRANGER),
            ],
        )
        self.assertEqual(1, len(report.file_flags))
        flag = report.file_flags[0]
        self.assertEqual(stale.REASON_LEDGER_NEWER, flag.reason)
        self.assertEqual(1, flag.non_owner_lines)
        self.assertEqual(datetime.date(2026, 6, 3), flag.newest_confirmation)

    def test_a_line_with_no_known_author_is_a_non_owner_line(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[],
            confirmations=[make_record(ICP, FRIDAY, author=None)],
        )
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual(stale.REASON_UNCONFIRMED, report.file_flags[0].reason)
        self.assertEqual(1, report.file_flags[0].non_owner_lines)


class TestAffectedFilesProposals(unittest.TestCase):
    def test_a_blank_affects_list_proposes_the_file_the_entry_names(self):
        entry = make_entry(
            affects=[],
            body="We are raising pricing for the smallest plan.",
        )
        report = run(
            files=[make_file(PRICING, kind="pricing")],
            ledger=[make_input(entry)],
            confirmations=[make_record(PRICING, FRIDAY)],
        )
        self.assertEqual(
            [(STG, [PRICING])],
            [(item.entry_id, item.candidate_paths) for item in report.affected_files_proposals],
        )
        self.assertEqual([], report.file_flags)

    def test_an_entry_that_names_nothing_falls_back_to_the_profile_files(self):
        entry = make_entry(affects=[], body="We agreed to move faster.")
        report = run(
            files=[
                make_file(ICP, kind="icp"),
                make_file(POSITIONING, kind="positioning"),
                make_file(PRICING, kind="pricing"),
            ],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(ICP, FRIDAY),
                make_record(POSITIONING, FRIDAY),
                make_record(PRICING, FRIDAY),
            ],
        )
        self.assertEqual(
            [ICP, POSITIONING], report.affected_files_proposals[0].candidate_paths
        )

    def test_map_hints_add_the_files_a_word_points_at(self):
        entry = make_entry(affects=[], body="The launch changes how we sound.")
        report = run(
            files=[make_file(POSITIONING, kind="positioning")],
            ledger=[make_input(entry)],
            confirmations=[make_record(POSITIONING, FRIDAY)],
            map_hints={"how we sound": [POSITIONING]},
        )
        self.assertEqual(
            [POSITIONING], report.affected_files_proposals[0].candidate_paths
        )


class TestMissingAndUnconfirmedFiles(unittest.TestCase):
    def test_an_entry_whose_file_is_gone_flags_the_entry_not_a_file(self):
        report = run(
            files=[make_file(POSITIONING)],
            ledger=[make_input(make_entry(affects=[ICP]))],
            confirmations=[make_record(POSITIONING, FRIDAY)],
        )
        self.assertEqual([], report.file_flags)
        self.assertEqual(
            [(STG, ICP, stale.REASON_ENTRY_MISSING_FILE)],
            [tuple(item) for item in report.entry_flags],
        )

    def test_a_file_recorded_as_absent_flags_the_entry(self):
        report = run(
            files=[make_file(ICP, exists=False)],
            ledger=[make_input(make_entry())],
        )
        self.assertEqual([], report.file_flags)
        self.assertEqual(1, len(report.entry_flags))

    def test_a_file_with_no_line_is_unconfirmed_against_an_affecting_entry(self):
        report = run(files=[make_file(ICP)], ledger=[make_input(make_entry())])
        flag = report.file_flags[0]
        self.assertEqual(stale.REASON_UNCONFIRMED, flag.reason)
        self.assertEqual(stale.TRIGGER_LEDGER, flag.trigger)
        self.assertEqual([STG], flag.entry_ids)
        self.assertIsNone(flag.newest_confirmation)

    def test_a_file_with_no_line_and_no_entry_is_flagged_on_the_threshold(self):
        report = run(files=[make_file(ICP)], ledger=[])
        flag = report.file_flags[0]
        self.assertEqual(stale.REASON_UNCONFIRMED, flag.reason)
        self.assertEqual(stale.TRIGGER_THRESHOLD, flag.trigger)
        self.assertEqual([], flag.entry_ids)

    def test_a_skipped_file_is_never_flagged(self):
        report = run(
            files=[make_file(ICP, status="skipped")],
            ledger=[make_input(make_entry())],
        )
        self.assertEqual([], report.file_flags)
        self.assertEqual([], report.entry_flags)


class TestThreshold(unittest.TestCase):
    def test_a_line_a_day_past_the_threshold_is_flagged(self):
        report = run(
            files=[make_file(ICP)],
            confirmations=[make_record(ICP, str(TODAY - datetime.timedelta(days=31)))],
        )
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual(stale.REASON_THRESHOLD, report.file_flags[0].reason)
        self.assertEqual(stale.TRIGGER_THRESHOLD, report.file_flags[0].trigger)

    def test_a_line_exactly_at_the_threshold_is_not_flagged(self):
        report = run(
            files=[make_file(ICP)],
            confirmations=[make_record(ICP, str(TODAY - datetime.timedelta(days=30)))],
        )
        self.assertEqual([], report.file_flags)

    def test_the_map_setting_moves_the_threshold(self):
        report = run(
            files=[make_file(ICP)],
            confirmations=[make_record(ICP, str(TODAY - datetime.timedelta(days=8)))],
            settings=stale.MapSettings(confirmation_threshold_days=7),
        )
        self.assertEqual(stale.REASON_THRESHOLD, report.file_flags[0].reason)

    def test_settings_can_be_read_from_the_map_text(self):
        settings = stale.MapSettings.from_map_text(support.MAP_TEXT)
        self.assertEqual(30, settings.confirmation_threshold_days)
        self.assertEqual(7, settings.not_now_days)


class TestLedgerBehind(unittest.TestCase):
    def test_no_entry_inside_the_window_reads_as_behind(self):
        entry = make_entry(decided_on="2026-04-01", written_on="2026-04-01")
        report = run(files=[make_file(ICP)], ledger=[make_input(entry)])
        self.assertTrue(report.ledger_behind.behind)
        self.assertEqual(datetime.date(2026, 4, 1), report.ledger_behind.newest_entry_date)
        self.assertEqual(30, report.ledger_behind.window_days)

    def test_a_recent_entry_is_not_behind(self):
        report = run(files=[make_file(ICP)], ledger=[make_input(make_entry())])
        self.assertFalse(report.ledger_behind.behind)

    def test_a_dismissal_reaching_past_today_silences_it(self):
        entry = make_entry(decided_on="2026-04-01", written_on="2026-04-01")
        seat = stale.SeatInput(
            ledger_behind_dismissed_until=TODAY + datetime.timedelta(days=1)
        )
        report = run(files=[make_file(ICP)], ledger=[make_input(entry)], seat=seat)
        self.assertIsNone(report.ledger_behind)

    def test_the_day_it_comes_back_is_the_day_it_is_said_again(self):
        """Put off up to, but not including, the day it comes back.

        This is the same boundary a file put off for now is left alone by, so
        the two ways of putting something off cannot disagree by a day.
        """
        entry = make_entry(decided_on="2026-04-01", written_on="2026-04-01")
        seat = stale.SeatInput(ledger_behind_dismissed_until=TODAY)
        report = run(files=[make_file(ICP)], ledger=[make_input(entry)], seat=seat)
        self.assertIsNotNone(report.ledger_behind)
        self.assertTrue(report.ledger_behind.behind)

    def test_a_dismissal_that_has_run_out_does_not_silence_it(self):
        entry = make_entry(decided_on="2026-04-01", written_on="2026-04-01")
        seat = stale.SeatInput(
            ledger_behind_dismissed_until=TODAY - datetime.timedelta(days=1)
        )
        report = run(files=[make_file(ICP)], ledger=[make_input(entry)], seat=seat)
        self.assertTrue(report.ledger_behind.behind)

    def test_an_empty_ledger_reads_as_behind(self):
        report = run(files=[make_file(ICP)], ledger=[])
        self.assertTrue(report.ledger_behind.behind)
        self.assertIsNone(report.ledger_behind.newest_entry_date)


class TestMalformedInput(unittest.TestCase):
    def test_review_by_before_the_decision_is_malformed_and_excluded(self):
        entry = make_entry(review_by="2026-05-01")
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(entry)],
            confirmations=[make_record(ICP, FRIDAY)],
        )
        self.assertEqual([], report.file_flags)
        self.assertEqual(
            [("ledger", "work/decisions/%s.md" % STG, "review-before-decision")],
            [tuple(item) for item in report.malformed],
        )

    def test_a_ledger_file_the_caller_could_not_read_is_malformed(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(path="work/decisions/broken.md", error="no-frontmatter")],
            confirmations=[make_record(ICP, FRIDAY)],
        )
        self.assertEqual(
            [("ledger", "work/decisions/broken.md", "no-frontmatter")],
            [tuple(item) for item in report.malformed],
        )
        self.assertEqual([], report.entries)

    def test_a_confirmation_line_that_breaks_a_rule_is_malformed(self):
        broken = stale.ConfirmationRecord(
            line=make_line(ICP, "2026-13-40"), author_email=OWNER
        )
        report = run(
            files=[make_file(ICP)],
            confirmations=[broken, make_record(ICP, FRIDAY)],
        )
        self.assertEqual(
            [("confirmation", ICP, "bad-date")],
            [tuple(item) for item in report.malformed],
        )


class TestCandidateQuestions(unittest.TestCase):
    def _report(self):
        second = "context/plan/goals.md"
        suppressed = "context/notes/notes.md"
        skipped = "context/strategy/positioning.md"
        seat = stale.SeatInput(
            suppressions={suppressed: str(TODAY + datetime.timedelta(days=3))}
        )
        return run(
            files=[
                make_file(ICP, owners=[OWNER]),
                make_file(second, owners=[OWNER]),
                make_file(suppressed, owners=[OWNER]),
                make_file(skipped, owners=[OWNER], status="skipped"),
                make_file(PRICING, owners=[OTHER_OWNER]),
            ],
            ledger=[make_input(make_entry(affects=[ICP]))],
            confirmations=[],
            seat=seat,
        )

    def test_owner_a_gets_the_ledger_question_first(self):
        questions = self._report().candidate_questions(OWNER)
        # The suppressed file and the file the person set aside are both gone,
        # and the decision comes before the calendar.
        self.assertEqual(
            [
                (ICP, stale.TRIGGER_LEDGER, STG),
                ("context/plan/goals.md", stale.TRIGGER_THRESHOLD, None),
            ],
            [(q.path, q.trigger, q.entry_id) for q in questions],
        )

    def test_a_suppression_that_has_run_out_brings_the_file_back(self):
        report = run(
            files=[make_file(ICP)],
            seat=stale.SeatInput(suppressions={ICP: str(TODAY)}),
        )
        self.assertEqual([ICP], [q.path for q in report.candidate_questions(OWNER)])

    def test_owner_b_gets_a_different_list(self):
        questions = self._report().candidate_questions(OTHER_OWNER)
        self.assertEqual([PRICING], [q.path for q in questions])
        self.assertEqual([stale.TRIGGER_THRESHOLD], [q.trigger for q in questions])

    def test_one_decision_raises_one_question_even_across_two_files(self):
        report = run(
            files=[make_file(ICP), make_file(POSITIONING)],
            ledger=[make_input(make_entry(affects=[ICP, POSITIONING]))],
            confirmations=[
                make_record(ICP, WEDNESDAY),
                make_record(POSITIONING, WEDNESDAY),
            ],
        )
        questions = report.candidate_questions(OWNER)
        ledger_questions = [q for q in questions if q.trigger == stale.TRIGGER_LEDGER]
        self.assertEqual(1, len(ledger_questions))
        self.assertEqual(ICP, ledger_questions[0].path)


class TestDraftedLines(unittest.TestCase):
    """Setup writes the file, the decision, and the yes in one run."""

    def _report(self, run_on_line):
        entry = make_entry(origin="join", run_id=RUN, affects=[ICP])
        return run(
            files=[make_file(ICP)],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(ICP, TUESDAY, trigger="drafted", run=run_on_line)
            ],
        )

    def test_the_same_run_confirms_on_the_decision_day(self):
        self.assertEqual([], self._report(RUN).file_flags)

    def test_another_run_does_not_confirm_on_the_decision_day(self):
        report = self._report(OTHER_RUN)
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual([STG], report.file_flags[0].entry_ids)

    def _old_decision(self, run_on_line):
        """A decision made weeks ago, written down today, drafted today.

        This is the shape every first setup run has: the person tells GTM Base
        about something they decided weeks ago, the decision is written down
        today, and the document it affects is drafted and approved in the same
        sitting.
        """
        entry = make_entry(
            origin="join",
            run_id=RUN,
            affects=[ICP],
            decided_on="2026-04-10",
            written_on=TODAY.isoformat(),
        )
        return run(
            files=[make_file(ICP)],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(
                    ICP, TODAY.isoformat(), trigger="drafted", run=run_on_line
                )
            ],
        )

    def test_the_same_run_confirms_a_decision_made_weeks_before_it(self):
        self.assertEqual([], self._old_decision(RUN).file_flags)

    def test_a_different_run_leaves_that_decision_open(self):
        report = self._old_decision(OTHER_RUN)
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual("ledger-newer", report.file_flags[0].reason)
        self.assertEqual([STG], report.file_flags[0].entry_ids)


class TestALineThatNamesTheDecision(unittest.TestCase):
    """The owner was shown the decision and the file together and said yes.

    That is what a line carrying the decision's identifier means, and it is
    exactly what an answer given on the day the decision was written down looks
    like, so the day it carries must not throw it away.
    """

    def _report(self, entry_id_on_line):
        entry = make_entry(decided_on=FRIDAY, written_on=FRIDAY)
        return run(
            files=[make_file(ICP)],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(ICP, FRIDAY, trigger="ledger", entry=entry_id_on_line)
            ],
        )

    def test_a_line_naming_the_decision_settles_it_the_same_day(self):
        self.assertEqual([], self._report(STG).file_flags)

    def test_a_line_naming_no_decision_settles_nothing_the_same_day(self):
        report = self._report(None)
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual([STG], report.file_flags[0].entry_ids)

    def test_a_line_naming_another_decision_settles_nothing(self):
        report = self._report(STG_TWO)
        self.assertEqual(1, len(report.file_flags))
        self.assertEqual([STG], report.file_flags[0].entry_ids)


class TestReviewItems(unittest.TestCase):
    """A document written from material older than the decision it follows."""

    SEPTEMBER = datetime.date(2026, 9, 5)

    def _report(self, sources_date):
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            origin="join",
            run_id=RUN,
            affects=[ICP],
        )
        return run(
            files=[make_file(ICP, sources_date=sources_date, kind="icp")],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(ICP, "2026-09-05", trigger="drafted", run=RUN)
            ],
            today=self.SEPTEMBER,
        )

    def test_an_august_source_under_a_september_decision_is_a_review_item(self):
        report = self._report("2026-08-10")
        self.assertEqual(1, len(report.review_items))
        item = report.review_items[0]
        self.assertEqual(ICP, item.path)
        self.assertEqual(STG, item.entry_id)
        self.assertEqual(datetime.date(2026, 8, 10), item.sources_date)
        self.assertEqual(stale.FINDING_DOCUMENT_OLDER, item.reason)

    def test_a_file_with_no_source_date_is_left_out_of_the_comparison(self):
        self.assertEqual([], self._report(None).review_items)

    def test_a_source_newer_than_the_decision_is_not_a_review_item(self):
        self.assertEqual([], self._report("2026-09-03").review_items)

    def _rekeyed(self, files, entries, confirmations):
        return run(
            files=files,
            ledger=[make_input(entry) for entry in entries],
            confirmations=confirmations,
            today=self.SEPTEMBER,
        )

    def test_an_entry_with_no_run_behind_it_still_raises_the_item(self):
        """The changes a person records at the closing carry no run id at all."""
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            run_id=None,
            affects=[ICP],
        )
        report = self._rekeyed(
            [make_file(ICP, sources_date="2026-08-10", kind="icp")],
            [entry],
            [make_record(ICP, "2026-09-05", trigger="drafted", run=OTHER_RUN)],
        )

        self.assertEqual([ICP], [item.path for item in report.review_items])
        self.assertEqual([STG], [item.entry_id for item in report.review_items])

    def test_a_closed_change_raises_nothing_and_the_same_one_open_raises_one(self):
        """The dates are identical in both halves, so only the status differs."""
        made = dict(
            decided_on="2026-09-04",
            written_on="2026-09-04",
            review_by="2026-12-01",
            run_id=None,
            affects=[ICP],
        )
        files = [make_file(ICP, sources_date="2026-09-02", kind="icp")]
        lines = [make_record(ICP, "2026-09-05", trigger="drafted", run=OTHER_RUN)]

        closed = self._rekeyed(files, [make_entry(status="closed", **made)], lines)
        opened = self._rekeyed(files, [make_entry(status="open", **made)], lines)

        self.assertEqual([], closed.review_items)
        self.assertEqual([ICP], [item.path for item in opened.review_items])

    def test_one_change_affecting_two_of_twelve_files_raises_two_items(self):
        paths = ["context/strategy/segments/s%02d.md" % number for number in range(12)]
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            run_id=None,
            affects=[paths[3], paths[7]],
        )
        report = self._rekeyed(
            [make_file(path, sources_date="2026-08-10", kind="segment") for path in paths],
            [entry],
            [
                make_record(path, "2026-09-05", trigger="drafted", run=OTHER_RUN)
                for path in paths
            ],
        )

        self.assertEqual(
            [paths[3], paths[7]], [item.path for item in report.review_items]
        )

    def test_a_file_with_no_drafted_line_raises_nothing(self):
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            run_id=None,
            affects=[ICP],
        )
        report = self._rekeyed(
            [make_file(ICP, sources_date="2026-08-10", kind="icp")],
            [entry],
            [make_record(ICP, "2026-09-05", trigger="threshold")],
        )

        self.assertEqual([], report.review_items)

    def test_a_change_that_does_not_affect_the_file_raises_nothing(self):
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            run_id=RUN,
            affects=[POSITIONING],
        )
        report = self._rekeyed(
            [
                make_file(ICP, sources_date="2026-08-10", kind="icp"),
                make_file(POSITIONING, sources_date="2026-09-04", kind="positioning"),
            ],
            [entry],
            [
                make_record(ICP, "2026-09-05", trigger="drafted", run=RUN),
                make_record(POSITIONING, "2026-09-05", trigger="drafted", run=RUN),
            ],
        )

        self.assertEqual([], report.review_items)


class TestFirstRunFinding(unittest.TestCase):
    SEPTEMBER = datetime.date(2026, 9, 5)

    def _report(self, positioning_status="draft", sources_date="2026-08-10"):
        entry = make_entry(
            decided_on="2026-09-01",
            written_on="2026-09-01",
            review_by="2026-12-01",
            origin="join",
            run_id=RUN,
            affects=[ICP],
        )
        return run(
            files=[
                make_file(ICP, sources_date=sources_date, kind="icp"),
                make_file(POSITIONING, status=positioning_status, kind="positioning"),
            ],
            ledger=[make_input(entry)],
            confirmations=[
                make_record(ICP, "2026-09-05", trigger="drafted", run=RUN),
                make_record(POSITIONING, "2026-09-05", trigger="drafted", run=RUN),
            ],
            today=self.SEPTEMBER,
        )

    def test_the_unanswered_marker_slot_is_there_and_is_still_empty(self):
        """The second place in the order belongs to Unit 1.7 and nothing else.

        The slot is asserted here rather than left to be discovered, because
        the closing rules promise five findings in one order and this module
        has to run that order from the day the baseline lands. Empty means the
        computation cannot reach it: it is handed values and never a file body,
        so no marker can be seen here yet.
        """
        source = inspect.getsource(stale.StaleReport.first_run_finding)
        slot = source.index("# The unanswered-marker slot.")
        self.assertLess(source.index("FINDING_REQUIRED_FILE_MISSING"), slot)
        self.assertLess(slot, source.index("self.review_items"))
        self.assertEqual(
            [],
            [name for name in dir(stale) if name.startswith("FINDING_") and "MARKER" in name],
        )

    def test_a_skipped_required_file_wins(self):
        finding = self._report(positioning_status="skipped").first_run_finding()
        self.assertEqual(stale.FINDING_REQUIRED_FILE_MISSING, finding.code)
        self.assertEqual(POSITIONING, finding.path)

    def test_the_review_item_wins_over_nothing_out_of_date(self):
        finding = self._report().first_run_finding()
        self.assertEqual(stale.FINDING_DOCUMENT_OLDER, finding.code)
        self.assertEqual(ICP, finding.path)
        self.assertEqual(datetime.date(2026, 8, 10), finding.date)

    def test_nothing_out_of_date_names_the_earliest_review_by(self):
        finding = self._report(sources_date=None).first_run_finding()
        self.assertEqual(stale.FINDING_NOTHING_OUT_OF_DATE, finding.code)
        self.assertIsNone(finding.path)
        self.assertEqual(datetime.date(2026, 12, 1), finding.date)
        self.assertEqual(STG, finding.entry_id)

    def test_a_missing_required_file_wins_when_it_was_never_written(self):
        report = run(
            files=[make_file(ICP)],
            ledger=[make_input(make_entry())],
            confirmations=[make_record(ICP, FRIDAY)],
        )
        finding = report.first_run_finding()
        self.assertEqual(stale.FINDING_REQUIRED_FILE_MISSING, finding.code)
        self.assertEqual(POSITIONING, finding.path)

    def baseline_report(self, positioning_date=FRIDAY, confirm_positioning=True):
        """A base with both documents confirmed and nothing recorded against it."""
        confirmations = [make_record(ICP, FRIDAY, trigger="drafted", run=RUN)]
        if confirm_positioning:
            confirmations.append(
                make_record(POSITIONING, positioning_date, trigger="drafted", run=RUN)
            )
        return run(
            files=[
                make_file(ICP, kind="icp"),
                make_file(POSITIONING, kind="positioning"),
            ],
            ledger=[],
            confirmations=confirmations,
        )

    def test_two_confirmed_files_and_no_change_give_the_honest_baseline(self):
        """Rewritten by Unit 1.2 on 2026-09-19.

        This scenario used to assert that a base holding no entry was reported
        as missing a required one. Setup no longer requires a context change to
        be drafted (P1), so that finding was taken out of the order and the
        honest baseline took its place (P2).
        """
        report = self.baseline_report()
        finding = report.first_run_finding()

        self.assertEqual(stale.FINDING_BASELINE_NO_CHANGES, finding.code)
        self.assertIsNone(finding.path)
        self.assertIsNone(finding.entry_id)
        self.assertEqual(
            [
                (ICP, datetime.date(2026, 6, 5), datetime.date(2026, 7, 6)),
                (POSITIONING, datetime.date(2026, 6, 5), datetime.date(2026, 7, 6)),
            ],
            [
                (item.path, item.confirmed_on, item.review_on)
                for item in report.baseline_items()
            ],
        )
        self.assertEqual(datetime.date(2026, 7, 6), finding.date)

    def test_a_setup_resumed_on_a_later_day_keeps_each_date_apart(self):
        report = self.baseline_report(positioning_date=WEDNESDAY)
        items = report.baseline_items()

        self.assertEqual(
            [datetime.date(2026, 6, 5), datetime.date(2026, 6, 3)],
            [item.confirmed_on for item in items],
        )
        self.assertEqual(
            [datetime.date(2026, 7, 6), datetime.date(2026, 7, 4)],
            [item.review_on for item in items],
        )
        # The finding carries the earlier of the two, which is the first day
        # the base has anything to say at all.
        self.assertEqual(datetime.date(2026, 7, 4), report.first_run_finding().date)

    def test_the_review_date_is_one_day_past_the_threshold(self):
        report = self.baseline_report()
        threshold = report.settings.confirmation_threshold_days

        confirmed = report.baseline_items()[0].confirmed_on
        self.assertEqual(
            confirmed + datetime.timedelta(days=threshold + 1),
            report.review_on(ICP),
        )

    def test_a_required_file_nobody_confirmed_is_named_by_the_baseline(self):
        report = self.baseline_report(confirm_positioning=False)
        finding = report.first_run_finding()

        self.assertEqual(stale.FINDING_BASELINE_NO_CHANGES, finding.code)
        self.assertEqual(POSITIONING, finding.path)
        self.assertIsNone(report.review_on(POSITIONING))

    def test_one_recorded_change_takes_the_base_past_the_baseline(self):
        report = run(
            files=[make_file(ICP), make_file(POSITIONING)],
            ledger=[make_input(make_entry(affects=[ICP]))],
            confirmations=[make_record(ICP, FRIDAY), make_record(POSITIONING, FRIDAY)],
        )
        self.assertEqual(
            stale.FINDING_NOTHING_OUT_OF_DATE, report.first_run_finding().code
        )


class TestTheMapIsLeftOutByItsKind(unittest.TestCase):
    """The map holds settings, so no context change can make it wrong."""

    MAP = "context/map.md"

    def _report(self, kind="map", confirmations=()):
        return run(
            files=[
                make_file(self.MAP, kind=kind),
                make_file(ICP, kind="icp"),
            ],
            ledger=[make_input(make_entry(affects=[self.MAP, ICP]))],
            confirmations=list(confirmations),
        )

    def test_it_is_never_flagged_and_never_asked_about(self):
        report = self._report()

        self.assertEqual([ICP], [flag.path for flag in report.file_flags])
        self.assertEqual(
            [ICP], [question.path for question in report.candidate_questions(OWNER)]
        )

    def test_a_base_made_before_this_rule_is_covered_too(self):
        """That base's map carries no confirmation line, and never needs one."""
        report = self._report(confirmations=[make_record(ICP, FRIDAY)])

        self.assertEqual([], [flag.path for flag in report.file_flags if flag.path == self.MAP])
        self.assertNotIn(self.MAP, report.confirmed_on)

    def test_it_is_never_a_review_item(self):
        report = run(
            files=[make_file(self.MAP, kind="map", sources_date="2026-01-01")],
            ledger=[
                make_input(
                    make_entry(
                        decided_on="2026-06-01",
                        written_on="2026-06-02",
                        affects=[self.MAP],
                    )
                )
            ],
            confirmations=[make_record(self.MAP, FRIDAY, trigger="drafted", run=RUN)],
        )
        self.assertEqual([], report.review_items)

    def test_a_file_of_any_other_kind_is_still_flagged(self):
        report = self._report(kind="notes")

        self.assertEqual(
            [self.MAP, ICP], sorted(set(flag.path for flag in report.file_flags))
        )


class TestReviewByAndSeatEchoes(unittest.TestCase):
    def test_a_review_by_date_that_has_passed_is_reported_with_the_days(self):
        entry = make_entry(
            decided_on="2026-04-01", written_on="2026-04-01", review_by="2026-06-01"
        )
        report = run(files=[make_file(ICP)], ledger=[make_input(entry)])
        self.assertEqual(
            [(STG, datetime.date(2026, 6, 1), 4)],
            [tuple(item) for item in report.review_by_items],
        )

    def test_dropped_paths_are_echoed_by_their_hash(self):
        seat = stale.SeatInput(
            dropped_paths=[{"path_hash": "c" * 64, "code": "dropped-path", "entry_id": STG}]
        )
        report = run(files=[make_file(ICP)], seat=seat)
        self.assertEqual(
            [("c" * 64, "dropped-path", STG)], [tuple(item) for item in report.dropped]
        )

    def test_a_base_with_nowhere_to_send_work_is_treated_as_up_to_date(self):
        report = run(files=[make_file(ICP)], seat=stale.SeatInput(has_remote=False))
        self.assertTrue(report.treat_as_fast_forwarded)
        self.assertFalse(run(files=[make_file(ICP)]).treat_as_fast_forwarded)

    def test_the_summary_counts_what_the_report_holds(self):
        report = run(files=[make_file(ICP)], ledger=[make_input(make_entry())])
        counts = report.summary_counts
        self.assertEqual(1, counts["files_flagged"])
        self.assertEqual(0, counts["entries_flagged"])
        self.assertEqual(0, counts["ledger_behind"])


class TestNoGitAndNoNetwork(unittest.TestCase):
    def test_the_library_imports_nothing_that_could_fetch_anything(self):
        path = os.path.join(
            support.PLUGIN_DIR, "lib", "gtmbase", "stale.py"
        )
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                imported.update(alias.name for alias in node.names)
        for forbidden in ("subprocess", "gitcmd", "socket", "urllib", "os", "fsutil", "state"):
            self.assertNotIn(forbidden, imported)

    def test_the_library_holds_no_em_dash_or_en_dash(self):
        path = os.path.join(support.PLUGIN_DIR, "lib", "gtmbase", "stale.py")
        assert_no_dashes = plain_language.find_dashes
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertEqual([], assert_no_dashes(source))


if __name__ == "__main__":
    unittest.main()
