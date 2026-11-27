"""Plan 1, Units 2.4a and 3.5: the goals, the metric definitions, and a standard.

Each is drafted after setup the way Track 4's documents are, but asked for
rather than inferred. A goal is a figure the person states and a definition a
rule they state, so the person's answers travel as pasted text and a figure
neither they nor the named material carry is refused. A target or a place of
measurement nobody stated stays a `[your call: ...]` marker. Goals and metric
definitions go in the folder of the business they are for when one is named,
and flat otherwise. A standard holds a job's rules in five parts and no digit
outside a date, because a number lives in exactly one other place.

These validate written drafts, the checks and the writes. They do not claim a
model writes the right prose; the owner's read is the test of that. Every
fixture is written from scratch for a made-up company, Larkspur Freight.
"""

import datetime
import io
import os
import re
import unittest

import support
import test_base_contents as contents
import test_moment_of_use as moment_tests

from gtmbase import (
    base_reader,
    constants,
    drafting,
    inventory,
    join_flow,
    moment,
    stale,
    state,
)
from gtmbase.errors import DraftError

NOW = contents.NOW
SESSION = contents.SESSION
ANSWERS = (
    "We want 200 paying brokers by 2026-12-31, counted in the billing system. "
    "We have not set a target for how fast quote requests are answered; the "
    "quote log counts them. A paying broker is one on a paid plan on the last "
    "day of the month, never a trial. Nobody knows yet where payback is counted."
)
STANDARD_ANSWERS = (
    "The engine pauses an ad when it passes the kill line, which serves the "
    "paying brokers goal and is looser because a new ad needs time to learn. "
    "Nobody spends without the owner's yes. Every pause in the summary is "
    "quoted from the engine's own log. Any change to the budget needs approval."
)


def captured(name):
    return contents.captured(name)


class TestTheDraftsReadBack(unittest.TestCase):
    """Each fixture parses, and each rule refuses what it is for."""

    def code_of(self, step, text):
        with self.assertRaises(DraftError) as raised:
            drafting.parse(step, text)
        return raised.exception.code

    def test_each_fixture_parses_into_its_kind(self):
        for step in drafting.DESTINED_STEPS:
            with self.subTest(step=step):
                draft = drafting.parse(step, captured(step + ".md"))
                self.assertEqual(step, draft.fields["kind"])

    def test_a_goal_without_a_figure_is_the_definition_and_the_question(self):
        draft = drafting.parse(drafting.STEP_GOALS, captured("goals.md"))
        self.assertIn("Target: [your call: what is the target for this?]", draft.body)

    def test_a_goal_missing_its_measured_in_line_is_refused(self):
        text = captured("goals.md").replace("Measured in: the quote log\n", "")
        self.assertEqual(
            drafting.CODE_ITEM_LINE % "Measured in", self.code_of(drafting.STEP_GOALS, text)
        )

    def test_a_definition_with_no_source_is_accepted_only_with_a_marker(self):
        draft = drafting.parse(drafting.STEP_METRICS, captured("metrics.md"))
        self.assertIn("Where the number lives: [your call: where is this counted?]", draft.body)
        text = captured("metrics.md").replace(
            "Where the number lives: [your call: where is this counted?]",
            "Where the number lives:",
        )
        self.assertEqual(
            drafting.CODE_ITEM_LINE % "Where the number lives",
            self.code_of(drafting.STEP_METRICS, text),
        )

    def test_the_definitions_name_the_counts_that_are_different_numbers(self):
        text = captured("metrics.md").replace(
            "The ad platform's own count of sign ups resembles a paying broker and is a "
            "different number, never to be mixed with it.\n",
            "",
        )
        self.assertEqual(
            drafting.CODE_EMPTY_SECTION % "Counts that are different numbers",
            self.code_of(drafting.STEP_METRICS, text),
        )

    def test_a_standard_naming_every_threshold_with_one_marker_is_accepted(self):
        draft = drafting.parse(drafting.STEP_STANDARD, captured("standard.md"))
        self.assertIn("[your call:", draft.body)

    def test_each_figure_in_a_standard_is_refused_and_a_date_passes(self):
        line = "The kill line serves the paying brokers goal."
        for figure in ("$40", "12%", "2x", "6 days"):
            with self.subTest(figure=figure):
                text = captured("standard.md").replace(line, line + " It is " + figure + ".")
                self.assertEqual(
                    drafting.CODE_DIGIT_IN_STANDARD, self.code_of(drafting.STEP_STANDARD, text)
                )
        dated = captured("standard.md").replace(line, line + " Set on 2026-11-01.")
        drafting.parse(drafting.STEP_STANDARD, dated)

    def test_an_empty_what_needs_approval_is_kept(self):
        text = captured("standard.md").replace("Any change to the budget.\n", "")
        draft = drafting.parse(drafting.STEP_STANDARD, text)
        self.assertIn("## What needs approval", draft.body)

    def test_the_drift_grade_starter_standard_passes(self):
        """Track 4's T4.8 starter, with the two lines the create operation stamps."""
        text = support.read(
            os.path.join(support.PLUGIN_DIR, "starter", "standards", "drift-grade.md")
        )
        self.assertNotIn("\nowner:", text)
        stamped = text.replace(
            "kind: standard\n",
            "kind: standard\nowner: owner@example.com\nlast_confirmed: 2026-11-27\n",
            1,
        )
        # A draft reaches `parse` inside one markdown fence, as a model returns it.
        draft = drafting.parse(drafting.STEP_STANDARD, "```markdown\n%s```\n" % stamped)
        self.assertEqual("standard", draft.fields["kind"])
        self.assertEqual([], drafting.digits_outside_dates(draft.body))

    def test_the_lint_names_the_lines_and_never_the_figures(self):
        found = drafting.digits_outside_dates("Fine.\nIt is $40.\nSet on 2026-11-01.\n")
        self.assertEqual([2], found)


class TestWhereEachGoes(unittest.TestCase):
    def test_the_destinations(self):
        self.assertEqual("context/goals.md", drafting.later_destination(drafting.STEP_GOALS))
        self.assertEqual(
            "standards/ad-creative-testing.md",
            drafting.later_destination(drafting.STEP_STANDARD, job="ad-creative-testing"),
        )
        for step, kwargs in (
            (drafting.STEP_STANDARD, {}),
            (drafting.STEP_STANDARD, {"job": "../escape"}),
            (drafting.STEP_GOALS, {"job": "outbound"}),
            (drafting.STEP_METRICS, {"business": "not-listed"}),
        ):
            with self.subTest(step=step, kwargs=kwargs):
                with self.assertRaises(DraftError):
                    drafting.later_destination(step, **kwargs)

    def test_a_remembered_destination_is_checked_again(self):
        good = ("context/goals.md", "context/courier-app/goals.md")
        for where in good:
            self.assertTrue(drafting.valid_destination(drafting.STEP_GOALS, where))
        for where in (
            "context/metrics.md",
            "context/a/b/goals.md",
            "standards/goals.md",
            "context/Courier/goals.md",
            None,
        ):
            with self.subTest(where=where):
                self.assertFalse(drafting.valid_destination(drafting.STEP_GOALS, where))
        self.assertTrue(drafting.valid_destination(drafting.STEP_STANDARD, "standards/outbound.md"))
        self.assertFalse(drafting.valid_destination(drafting.STEP_STANDARD, "context/goals.md"))


class TestTheStartersMatchTheShapes(unittest.TestCase):
    def test_each_starter_carries_exactly_its_parts_and_none_is_in_the_template(self):
        for step in drafting.DESTINED_STEPS:
            with self.subTest(step=step):
                text = support.read(os.path.join(contents.STARTERS, step + ".md"))
                headings = re.findall(r"^## (.*)$", text, re.MULTILINE)
                self.assertEqual(list(drafting.LATER_SECTIONS[step]), headings)
                self.assertIn("kind: %s" % step, text)
                self.assertFalse(
                    os.path.exists(
                        os.path.join(support.TEMPLATES_DIR, "company-base", "context", step + ".md")
                    )
                )

    def test_each_kind_is_draftable_and_never_adoptable(self):
        kinds = {kind.key: kind for kind in constants.BASE_KINDS}
        for key in ("goals", "metrics", "standard"):
            self.assertTrue(kinds[key].draftable)
            self.assertFalse(kinds[key].adoptable)
            self.assertNotIn(key, drafting.LATER_STEPS)


class AskedAfterSetup(contents.AfterSetup):
    """A base that exists, a run, and the person's answers held as pasted text."""

    def setUp(self):
        super().setUp()
        self.answers = join_flow.write_paste(self.run_id, "your-answers.md", ANSWERS, SESSION)

    def businesses(self, listed):
        map_path = os.path.join(self.base.root, constants.MAP_PATH)
        text = support.read(map_path)
        support.write(map_path, text.replace("---\n\n", "businesses: %s\n---\n\n" % listed, 1))
        support.git(["add", "-A"], cwd=self.base.root)
        support.git(["commit", "-q", "-m", "businesses"], cwd=self.base.root)

    def assembled(self, step, business=None, job=None, answers=None):
        destination = drafting.later_destination(
            step, self.base.root, business=business, job=job
        )
        return join_flow.assemble_step(
            step,
            self.run_id,
            "Larkspur",
            "owner@example.com",
            paste_files=[answers or self.answers],
            destination=destination,
        )

    def draft(self, step, text=None, **where):
        self.assembled(step, **where)
        path = join_flow.draft_path(self.run_id, step)
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(text if text is not None else captured(step + ".md"))
        return path

    def reviewed(self, step, text=None, **where):
        path = self.draft(step, text, **where)
        return path, join_flow.review_step(
            step, path, base_root=self.base.root, run_id=self.run_id
        )

    def approved(self, step, text=None, now=NOW, **where):
        path, reviewed = self.reviewed(step, text, **where)
        self.assertTrue(reviewed.ready, reviewed.codes)
        # Each fixture leaves one question open, as an asked document often
        # does; the person was asked and chose to save it with the question.
        return join_flow.approve_step(
            step, path, self.run_id, base_root=self.base.root, now=now,
            questions_open=True,
        )


class TestAskedAndWritten(AskedAfterSetup):
    def test_goals_and_definitions_go_flat_for_the_whole_company(self):
        for step in (drafting.STEP_GOALS, drafting.STEP_METRICS):
            with self.subTest(step=step):
                result = self.approved(step)
                self.assertEqual("context/%s.md" % step, result.path)

    def test_goals_go_in_the_named_business_folder(self):
        self.businesses("courier-app, insights")
        result = self.approved(drafting.STEP_GOALS, business="courier-app")
        self.assertEqual("context/courier-app/goals.md", result.path)
        self.assertTrue(os.path.isfile(os.path.join(self.base.root, result.path)))

    def test_a_standard_goes_at_its_jobs_path(self):
        self.answers = join_flow.write_paste(
            self.run_id, "your-answers.md", STANDARD_ANSWERS, SESSION
        )
        result = self.approved(drafting.STEP_STANDARD, job="ad-creative-testing")
        self.assertEqual("standards/ad-creative-testing.md", result.path)

    def test_a_figure_in_neither_the_material_nor_the_answers_is_refused(self):
        _path, reviewed = self.reviewed(
            drafting.STEP_GOALS,
            captured("goals.md").replace("200 paying brokers", "250 paying brokers"),
        )
        self.assertFalse(reviewed.ready)
        self.assertIn(drafting.CODE_FIGURE_NOT_IN_SOURCES, reviewed.codes)

    def test_a_tampered_destination_is_refused_at_review(self):
        path = self.draft(drafting.STEP_GOALS)
        join_flow._remember(
            self.run_id, "destinations", join_flow._file_stem(drafting.STEP_GOALS, None),
            "context/icps.md",
        )
        reviewed = join_flow.review_step(
            drafting.STEP_GOALS, path, base_root=self.base.root, run_id=self.run_id
        )
        self.assertEqual([drafting.CODE_NOT_A_DESTINATION], reviewed.codes)


class TestReadOwnedFlaggedAndCounted(AskedAfterSetup):
    def test_a_business_goals_document_is_read_and_flagged_by_a_change_naming_it(self):
        self.businesses("courier-app")
        earlier = datetime.datetime.combine(
            state.today() - datetime.timedelta(days=3), datetime.time(9, 0)
        )
        result = self.approved(drafting.STEP_GOALS, business="courier-app", now=earlier)
        held = {one.path: one for one in base_reader.context_files(self.base.root)}
        self.assertIn(result.path, held)
        self.assertEqual(["owner@example.com"], held[result.path].owners)
        today = state.today().isoformat()
        self.base.add_change(
            moment_tests.entry_text(affects=(result.path,))
            .replace("decided_on: %s" % moment_tests.TUESDAY, "decided_on: %s" % today)
            .replace("written_on: %s" % moment_tests.THURSDAY, "written_on: %s" % today)
            .replace("review_by: 2026-09-01", "review_by: 2099-01-01")
        )
        self.assertTrue(
            moment.check(
                self.base.root, self.base.base_id, result.path,
                session_id=moment_tests.SESSION, runner=support.NoRemoteRunner(),
                now=state.today(),
            ).flagged
        )

    def test_a_goals_change_suggests_a_standard_whose_sources_name_the_goals(self):
        """Track 4's suggestion table finds the standard through its sources setting."""
        self.approved(drafting.STEP_GOALS)
        self.answers = join_flow.write_paste(
            self.run_id, "standard-answers.md", STANDARD_ANSWERS, SESSION
        )
        self.approved(drafting.STEP_STANDARD, job="ad-creative-testing")
        held = base_reader.context_files(self.base.root)
        _mentioned, following = stale.suggested_paths(held, "the goals moved")
        self.assertEqual(["standards/ad-creative-testing.md"], following)

    def test_the_inventory_offers_goals_and_definitions_and_reports_them_held(self):
        answer = inventory.take(self.base.root, self.base.base_id, runner=support.NoRemoteRunner())
        offered = sorted(kind for kind, _column in answer.draftable_missing)
        self.assertIn("goals", offered)
        self.assertIn("metrics", offered)
        self.approved(drafting.STEP_GOALS)
        answer = inventory.take(self.base.root, self.base.base_id, runner=support.NoRemoteRunner())
        self.assertEqual(
            inventory.STATE_PRESENT, answer.cells[("goals", "whole-company")].state
        )


if __name__ == "__main__":
    unittest.main()
