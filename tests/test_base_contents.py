"""Track 4, step 1: what a base holds (Units T4.1, T4.2, T4.3 and T4.6).

T4.1 is the table of what a recorded context change usually also overtakes,
read as suggestions. T4.2 and T4.3 are the messaging, the voice guide, the
buyer personas and the product, drafted after setup from material the person
names, or taken in as they stand. T4.6 is the source map's rows, drafted from
what the person says.

These validate written drafts, the checks and the writes. They do not claim a
model writes the right prose; the owner's own read is the test of that. The
company in every fixture is made up.
"""

import datetime
import io
import os
import re
import unittest

import support
import test_moment_of_use as moment_tests
import test_stale

from gtmbase import (
    adopt,
    base_reader,
    constants,
    drafting,
    inventory,
    join_flow,
    moment,
    names,
    stale,
    state,
    truth_map,
)
from gtmbase.errors import DraftError, ReviewError

DRAFTS = os.path.join(support.FIXTURES_DIR, "drafts")
BASE_KINDS_REFERENCE = os.path.join(
    support.PLUGIN_DIR, "skills", "stale-check", "references", "base-kinds.md"
)
STARTERS = os.path.join(support.PLUGIN_DIR, "starter")
NOW = datetime.datetime(2026, 11, 20, 9, 0, 0)
SESSION = "s-track-4"

SITE = """# Larkspur Freight

Every shipment, quoted in one place.

Larkspur gives small freight brokers one screen for every carrier quote.
Brokers using it answer a quote request in 4 minutes instead of 40.

"We already have a spreadsheet," brokers tell us. A spreadsheet goes out of
date the moment a carrier changes a rate.

We say quote, never bid. The pricing page on the company's website holds the
current prices.
"""

FINISHED_GUIDE = """---
author: someone on the team
tags: [messaging, final]
---

# Larkspur messaging guide

## Core message

Every shipment, quoted in one place.

## Proof points

Brokers answer a quote request in 4 minutes instead of 40.
"""


def captured(name):
    with io.open(os.path.join(DRAFTS, name), encoding="utf-8") as handle:
        return handle.read()


def info(path, kind, relates_to=()):
    return stale.ContextFileInfo(path, kind=kind, relates_to=relates_to)


A_BASE = [
    info("context/icps.md", "icp"),
    info("context/icps/mid-market.md", "segment"),
    info("context/positioning.md", "positioning"),
    info("context/messaging.md", "messaging"),
    info("context/voice.md", "voice"),
    info("context/goals.md", "goals"),
    info("standards/meta-creative-testing.md", "standard", ["context/goals.md (2026-11-01)"]),
    info("standards/outbound.md", "standard", ["context/icps.md (2026-11-01)"]),
]


# --- T4.1: a decision follows through ------------------------------------------


class TestAChangeFollowsThroughToWhatIsBuiltOnIt(unittest.TestCase):
    """Recording a change suggests the documents built on the ones it names."""

    def test_a_profile_change_suggests_what_the_base_holds_and_nothing_it_does_not(self):
        mentioned, following = stale.suggested_paths(A_BASE, "the icps changed")
        self.assertEqual(["context/icps.md"], mentioned)
        # Positioning and messaging are held; the buyer personas are not, so
        # they are never suggested.
        self.assertEqual(["context/messaging.md", "context/positioning.md"], following)

    def test_a_change_that_names_nothing_still_follows_from_the_fallback(self):
        held = A_BASE + [info("context/buyer-personas.md", "buyer-personas")]
        mentioned, following = stale.suggested_paths(held, "We moved up-market.")
        self.assertIn("context/icps.md", mentioned)
        self.assertIn("context/positioning.md", mentioned)
        self.assertEqual(
            ["context/buyer-personas.md", "context/messaging.md"], following
        )

    def test_a_voice_change_suggests_nothing_further(self):
        mentioned, following = stale.suggested_paths(A_BASE, "a new voice rule")
        self.assertEqual(["context/voice.md"], mentioned)
        self.assertEqual([], following)

    def test_a_goals_change_suggests_only_the_standards_that_relate_to_goals(self):
        _mentioned, following = stale.suggested_paths(A_BASE, "the goals moved")
        self.assertEqual(["standards/meta-creative-testing.md"], following)

    def test_the_review_proposals_follow_through_the_same_way(self):
        entry = test_stale.make_entry(affects=[], body="We changed the positioning.")
        report = test_stale.run(files=A_BASE, ledger=[test_stale.make_input(entry)])
        self.assertEqual(
            ["context/messaging.md", "context/positioning.md"],
            report.affected_files_proposals[0].candidate_paths,
        )

    def test_every_kind_in_the_table_and_every_follower_is_a_kind_on_the_list(self):
        keys = [kind.key for kind in constants.BASE_KINDS]
        for key, following in constants.KIND_FOLLOWS.items():
            with self.subTest(kind=key):
                self.assertIn(key, keys)
                for one in following:
                    self.assertIn(one, keys)

    def test_the_reference_says_what_the_table_says(self):
        text = support.read(BASE_KINDS_REFERENCE)
        said = {}
        for section in text.split("\n## ")[1:]:
            key = re.match(r".*\(`([a-z-]+)`\)", section.split("\n", 1)[0]).group(1)
            found = re.search(r"^Usually also overtakes: (.*?)\.$", section, re.MULTILINE)
            if found:
                said[key] = found.group(1)
        self.assertEqual(sorted(constants.KIND_FOLLOWS), sorted(said))
        for key, following in constants.KIND_FOLLOWS.items():
            with self.subTest(kind=key):
                words = re.sub(r"\s*\(.*\)", "", said[key])
                expected = (
                    ", ".join(names.KIND_LABELS[one].lower() for one in following)
                    or "nothing else"
                )
                self.assertEqual(expected, words)


# --- T4.2 and T4.3: the documents drafted after setup ---------------------------


class TestTheDraftsReadBack(unittest.TestCase):
    """Each fixture parses, and each rule refuses what it is for."""

    def test_each_fixture_parses_into_its_kind_and_its_one_path(self):
        for step in drafting.LATER_STEPS:
            with self.subTest(step=step):
                draft = drafting.parse(step, captured(step + ".md"))
                self.assertEqual(step, draft.fields["kind"])
                self.assertEqual("context/%s.md" % step, draft.path)

    def test_the_personas_are_never_written_under_the_segments_folder(self):
        draft = drafting.parse(
            drafting.STEP_BUYER_PERSONAS, captured("buyer-personas.md")
        )
        self.assertFalse(draft.path.startswith(constants.SEGMENTS_DIR + "/"))
        wrong = captured("buyer-personas.md").replace(
            "kind: buyer-personas", "kind: segment"
        )
        with self.assertRaises(DraftError) as raised:
            drafting.parse(drafting.STEP_BUYER_PERSONAS, wrong)
        self.assertEqual(drafting.CODE_WRONG_KIND, raised.exception.code)

    def refused(self, step, text):
        with self.assertRaises(DraftError) as raised:
            drafting.parse(step, text)
        return raised.exception.code

    def test_every_part_is_there_and_holds_something(self):
        for step in drafting.LATER_STEPS:
            text = captured(step + ".md")
            gaps = "## " + drafting.GAPS_SECTION
            with self.subTest(step=step):
                self.assertEqual(
                    drafting.CODE_EMPTY_SECTION % drafting.GAPS_SECTION,
                    self.refused(step, text[: text.index(gaps)] + "```\n"),
                )

    def test_a_principle_with_no_quoted_sentence_is_refused(self):
        text = captured("voice.md").replace(
            "> Every shipment, quoted in one place.\n", ""
        )
        self.assertEqual(
            drafting.CODE_PRINCIPLE_UNQUOTED, self.refused(drafting.STEP_VOICE, text)
        )

    def test_sources_with_nothing_about_voice_say_which_parts_had_no_signal(self):
        text = captured("voice.md")
        start = text.index("## Principles")
        end = text.index("## What the material does not show")
        empty = (
            text[:start]
            + "## Principles\n\nNothing in the material covers this.\n\n"
            + "## Words we use and avoid\n\nNothing in the material covers this.\n\n"
            + "## By channel\n\nNothing in the material covers this.\n\n"
            + "## What the material does not show\n\nThe material holds none of "
            "the company's own writing, so no principle, word or channel could "
            "be shown.\n```\n"
        )
        self.assertNotEqual(start, end)
        draft = drafting.parse(drafting.STEP_VOICE, empty)
        self.assertIn("no principle", draft.body)

    def test_a_persona_section_with_no_persona_under_it_is_refused(self):
        text = captured("buyer-personas.md").replace("### Operations lead\n\n", "")
        self.assertEqual(
            drafting.CODE_NO_ITEMS % "Personas",
            self.refused(drafting.STEP_BUYER_PERSONAS, text),
        )

    def test_the_product_keeps_shipped_apart_from_planned(self):
        text = captured("product.md").replace("## What is planned", "## Coming soon")
        self.assertEqual(
            drafting.CODE_EMPTY_SECTION % "What is planned",
            self.refused(drafting.STEP_PRODUCT, text),
        )

    def test_the_product_points_at_pricing_and_never_writes_a_price(self):
        text = captured("product.md").replace(
            "The pricing page", "Plans start at $49 a month. The pricing page"
        )
        self.assertEqual(
            drafting.CODE_PRICING_RESTATED, self.refused(drafting.STEP_PRODUCT, text)
        )

    def test_a_long_dash_and_a_banned_word_are_refused(self):
        dash = captured("messaging.md").replace("one screen", "one screen —")
        self.assertEqual(drafting.CODE_EM_DASH, self.refused(drafting.STEP_MESSAGING, dash))
        banned = captured("messaging.md").replace("one screen", "a seamless screen")
        self.assertEqual(
            drafting.CODE_BANNED_WORD % "seamless",
            self.refused(drafting.STEP_MESSAGING, banned),
        )

    def test_a_figure_the_material_lacks_is_found(self):
        allowed = drafting.figures_in(SITE)
        body = drafting.parse(drafting.STEP_MESSAGING, captured("messaging.md")).body
        self.assertEqual([], drafting.figures_beyond(body, allowed))
        self.assertEqual(
            ["3"], drafting.figures_beyond(body.replace("4 minutes", "3 minutes"), allowed)
        )
        # 14 never stands for 14%.
        self.assertEqual(["14%"], drafting.figures_beyond("a 14% lift", ["14"]))


class TestThePromptsAskForWhatTheChecksHold(unittest.TestCase):
    """Each prompt names the parts, the gap sentence and the figure rule."""

    def test_each_prompt_names_its_parts_and_the_rules_review_holds(self):
        for step in drafting.LATER_STEPS:
            with self.subTest(step=step):
                words = " ".join(
                    support.read(drafting.prompt_path(step, support.PLUGIN_DIR)).split()
                )
                for heading in drafting.LATER_SECTIONS[step]:
                    self.assertIn(heading, words)
                self.assertIn(drafting.NOT_COVERED, words)
                self.assertIn("A figure that is not in the material is refused", words)
                self.assertIn("`context/%s.md`" % step, words)

    def test_the_source_map_prompt_never_lets_an_unnamed_tool_in(self):
        path = os.path.join(
            support.PLUGIN_DIR, "skills", "join", "references", "prompts", "draft-stack-rows.md"
        )
        words = " ".join(support.read(path).split())
        for column in truth_map.COLUMNS:
            self.assertIn(column, words)
        self.assertIn("A place or a tool they did not name is never a row", words)
        self.assertIn("Never write a password, a key, a token", words)


class TestTheStartersMatchTheShapes(unittest.TestCase):
    """The shapes kept in the plugin are the shapes the checks hold drafts to."""

    def test_each_starter_carries_exactly_its_parts(self):
        for step in drafting.LATER_STEPS:
            with self.subTest(step=step):
                text = support.read(os.path.join(STARTERS, step + ".md"))
                headings = re.findall(r"^## (.*)$", text, re.MULTILINE)
                self.assertEqual(list(drafting.LATER_SECTIONS[step]), headings)
                self.assertIn("kind: %s" % step, text)

    def test_no_starter_is_in_the_company_template(self):
        for step in drafting.LATER_STEPS:
            self.assertFalse(
                os.path.exists(
                    os.path.join(support.TEMPLATES_DIR, "company-base", "context", step + ".md")
                )
            )


class AfterSetup(unittest.TestCase):
    """A base that exists, and a run that has agreed to one folder of material."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        support.write(
            os.path.join(os.environ["HOME"], ".gitconfig"),
            "[user]\n\temail = owner@example.com\n\tname = Dana\n",
        )
        self.base = moment_tests.Base(self.sandbox)
        self.content = os.path.join(os.environ["HOME"], "larkspur")
        support.write(os.path.join(self.content, "larkspur-site.md"), SITE)
        # The day the fixtures say the material was written, which a
        # competitor fact carries as its date (Unit T4.4).
        written = datetime.datetime(2026, 11, 2, 12, 0, 0).timestamp()
        os.utime(os.path.join(self.content, "larkspur-site.md"), (written, written))
        self.run_id = join_flow.new_run()
        join_flow.list_sources(self.content, self.run_id)
        join_flow.freeze_sources(self.content, SESSION, self.run_id)

    def assembled(self, step):
        return join_flow.assemble_step(step, self.run_id, "Larkspur", "owner@example.com")

    def draft(self, step, text=None):
        self.assembled(step)
        path = join_flow.draft_path(self.run_id, step)
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(text if text is not None else captured(step + ".md"))
        return path

    def reviewed(self, step, text=None):
        path = self.draft(step, text)
        return path, join_flow.review_step(
            step, path, base_root=self.base.root, run_id=self.run_id
        )

    def approved(self, step, text=None, now=NOW):
        path, reviewed = self.reviewed(step, text)
        self.assertTrue(reviewed.ready, reviewed.codes)
        return join_flow.approve_step(
            step, path, self.run_id, base_root=self.base.root, now=now
        )


class TestDraftedAfterSetup(AfterSetup):
    """Drafted from named material, checked, and written only into a base."""

    def test_each_document_is_reviewed_and_written_where_its_kind_is_kept(self):
        for step in drafting.LATER_STEPS:
            with self.subTest(step=step):
                result = self.approved(step)
                self.assertEqual("context/%s.md" % step, result.path)
                saved = support.read(os.path.join(self.base.root, result.path))
                self.assertIn("kind: %s" % step, saved)

    def test_a_figure_the_material_does_not_carry_is_refused(self):
        _path, reviewed = self.reviewed(
            drafting.STEP_MESSAGING,
            captured("messaging.md").replace("4 minutes", "3 minutes"),
        )
        self.assertFalse(reviewed.ready)
        self.assertIn(drafting.CODE_FIGURE_NOT_IN_SOURCES, reviewed.codes)

    def test_a_draft_carrying_a_contact_detail_goes_back_to_the_same_step(self):
        _path, reviewed = self.reviewed(
            drafting.STEP_MESSAGING,
            captured("messaging.md").replace(
                "We say quote", "Write to dana.reyes@larkspur.test. We say quote"
            ),
        )
        self.assertFalse(reviewed.ready)
        self.assertTrue(reviewed.codes)

    def test_review_needs_the_run(self):
        path = self.draft(drafting.STEP_VOICE)
        with self.assertRaises(ReviewError) as raised:
            join_flow.review_step(drafting.STEP_VOICE, path, base_root=self.base.root)
        self.assertEqual(join_flow.CODE_NO_RUN, raised.exception.code)

    def test_it_never_makes_a_base(self):
        path, reviewed = self.reviewed(drafting.STEP_PRODUCT)
        self.assertTrue(reviewed.ready, reviewed.codes)
        with self.assertRaises(ReviewError):
            join_flow.approve_step(
                drafting.STEP_PRODUCT, path, self.run_id, company="Larkspur", now=NOW
            )

    def test_nothing_is_written_over_a_document_already_there(self):
        self.approved(drafting.STEP_PRODUCT)
        path, reviewed = self.reviewed(drafting.STEP_PRODUCT)
        self.assertTrue(reviewed.ready, reviewed.codes)
        with self.assertRaises(ReviewError):
            join_flow.approve_step(
                drafting.STEP_PRODUCT, path, self.run_id, base_root=self.base.root, now=NOW
            )

    def test_the_request_reads_the_base_strategy_first_when_it_is_named(self):
        support.write(os.path.join(self.content, "aaa-notes.md"), "# Notes\n\nOdds and ends.\n")
        support.write(
            os.path.join(self.content, "positioning.md"), "# Positioning\n\nOne screen.\n"
        )
        run_id = join_flow.new_run()
        join_flow.list_sources(self.content, run_id)
        join_flow.freeze_sources(self.content, SESSION, run_id)
        made = join_flow.assemble_step(
            drafting.STEP_MESSAGING, run_id, "Larkspur", "owner@example.com"
        )
        self.assertTrue(made.included_labels[0].startswith("positioning.md"))


class TestReadOwnedConfirmedAndFlagged(AfterSetup):
    """Once written, each is an ordinary document of the base."""

    def test_each_is_read_and_flagged_by_a_change_that_names_it(self):
        earlier = datetime.datetime.combine(
            state.today() - datetime.timedelta(days=3), datetime.time(9, 0)
        )
        for step in (drafting.STEP_MESSAGING, drafting.STEP_VOICE):
            self.approved(step, now=earlier)
        held = {one.path: one for one in base_reader.context_files(self.base.root)}
        for step in (drafting.STEP_MESSAGING, drafting.STEP_VOICE):
            with self.subTest(step=step):
                path = "context/%s.md" % step
                self.assertIn(path, held)
                self.assertEqual(["owner@example.com"], held[path].owners)
        today = state.today().isoformat()
        self.base.add_change(
            moment_tests.entry_text(affects=("context/messaging.md",))
            .replace("decided_on: %s" % moment_tests.TUESDAY, "decided_on: %s" % today)
            .replace("written_on: %s" % moment_tests.THURSDAY, "written_on: %s" % today)
            .replace("review_by: 2026-09-01", "review_by: 2099-01-01")
        )
        flagged = lambda path: moment.check(  # noqa: E731
            self.base.root,
            self.base.base_id,
            path,
            session_id=moment_tests.SESSION,
            runner=support.NoRemoteRunner(),
            now=state.today(),
        ).flagged
        self.assertTrue(flagged("context/messaging.md"))
        self.assertFalse(flagged("context/voice.md"))


class TestTakenInAsItStands(AfterSetup):
    """A finished guide is adopted, with its own settings set aside."""

    def test_a_finished_messaging_guide_is_adopted_without_its_old_settings(self):
        source = os.path.join(self.content, "messaging-guide.md")
        support.write(source, FINISHED_GUIDE)
        run_id = join_flow.new_run()
        join_flow.list_sources(self.content, run_id)
        join_flow.freeze_sources(self.content, SESSION, run_id)
        shown = join_flow.document_adoption_show(
            run_id, drafting.STEP_MESSAGING, source, self.base.root
        )
        self.assertTrue(shown.settings_set_aside)
        result = join_flow.document_adoption_approve(
            run_id, drafting.STEP_MESSAGING, self.base.root, shown.digest, now=NOW
        )
        self.assertEqual("context/messaging.md", result.path)
        saved = support.read(os.path.join(self.base.root, result.path))
        self.assertIn("kind: messaging", saved)
        self.assertIn("status: %s" % adopt.STATUS_ADOPTED, saved)
        self.assertNotIn("author:", saved)
        self.assertNotIn("tags:", saved)

    def test_a_yes_to_anything_but_what_was_shown_writes_nothing(self):
        source = os.path.join(self.content, "messaging-guide.md")
        support.write(source, FINISHED_GUIDE)
        run_id = join_flow.new_run()
        join_flow.list_sources(self.content, run_id)
        join_flow.freeze_sources(self.content, SESSION, run_id)
        join_flow.document_adoption_show(
            run_id, drafting.STEP_MESSAGING, source, self.base.root
        )
        with self.assertRaises(adopt.AdoptionRefused):
            join_flow.document_adoption_approve(
                run_id, drafting.STEP_MESSAGING, self.base.root, "0" * 64, now=NOW
            )
        self.assertFalse(
            os.path.exists(os.path.join(self.base.root, "context", "messaging.md"))
        )


class TestTheInventoryOffersThem(AfterSetup):
    """Skipping leaves the base complete, and the inventory says what it holds."""

    def test_skipped_is_reported_and_the_rest_are_offered(self):
        join_flow.skip_step(
            drafting.STEP_VOICE, self.base.root, email="owner@example.com", now=NOW
        )
        self.approved(drafting.STEP_MESSAGING)
        answer = inventory.take(self.base.root, self.base.base_id, runner=support.NoRemoteRunner())
        cell = lambda kind: answer.cells[(kind, "whole-company")]  # noqa: E731
        self.assertEqual(inventory.STATE_SKIPPED, cell("voice").state)
        self.assertEqual(inventory.STATE_PRESENT, cell("messaging").state)
        offered = sorted(kind for kind, _column in answer.draftable_missing)
        # This base predates the source map's starter, so it is offered too,
        # and the goals, the definitions and a standard are offered since
        # Plan 1's Units 2.4a and 3.5.
        self.assertEqual(
            [
                "buyer-personas", "competitors", "design", "goals",
                "metrics", "product", "stack", "standard",
            ],
            offered,
        )
        self.assertIn("buyer personas", answer.ask().lower())
        self.assertEqual(2, len(constants.REQUIRED_CONTEXT_FILES))


# --- T4.6: the source map for any company ---------------------------------------

ROWS = """```markdown
## Where the material lives

| Kind of data | Business | Where it lives | What reads it | If that is not connected |
|---|---|---|---|---|
| Ad spend | whole company | Google Ads | the Google Ads connector | ask Dana for the export |
| Pipeline | whole company | HubSpot | nothing | ask Dana for the export |
```
"""
ANSWERS = (
    "Our ad spend is in Google Ads and the Google Ads connector reads it. "
    "Pipeline is in HubSpot and nothing reads it yet."
)


class TestTheSourceMapRows(unittest.TestCase):
    """Rows drafted from what a person said, held to the file's own rules."""

    def test_answers_produce_rows_with_all_five_columns(self):
        found = truth_map.check_drafted(ROWS, ANSWERS)
        self.assertEqual([], found.problems)
        self.assertEqual(["Ad spend", "Pipeline"], [row.kind_of_data for row in found.rows])
        for row in found.rows:
            for field in truth_map.FIELDS:
                self.assertTrue(getattr(row, field))

    def test_a_row_missing_its_fallback_is_reported_incomplete(self):
        found = truth_map.check_drafted(
            ROWS.replace("| nothing | ask Dana for the export |", "| nothing | |"), ANSWERS
        )
        self.assertEqual(["Ad spend"], [row.kind_of_data for row in found.rows])
        self.assertIn(truth_map.CODE_INCOMPLETE, [one.code for one in found.problems])

    def test_a_tool_the_person_did_not_name_never_becomes_a_row(self):
        found = truth_map.check_drafted(
            ROWS.replace("| HubSpot | nothing |", "| Salesforce | nothing |"), ANSWERS
        )
        self.assertEqual(["Ad spend"], [row.kind_of_data for row in found.rows])
        self.assertIn(truth_map.CODE_NOT_NAMED, [one.code for one in found.problems])
        reader = truth_map.check_drafted(
            ROWS.replace("the Google Ads connector", "Supermetrics"), ANSWERS
        )
        self.assertNotIn("Ad spend", [row.kind_of_data for row in reader.rows])

    def test_a_line_shaped_like_a_key_is_refused(self):
        found = truth_map.check_drafted(
            ROWS.replace("ask Dana for the export |\n| Pipeline", "AKIAABCDEFGHIJKLMNOP |\n| Pipeline"),
            ANSWERS,
        )
        self.assertIn(truth_map.CODE_SCREENED, [one.code for one in found.problems])
        self.assertNotIn("Ad spend", [row.kind_of_data for row in found.rows])

    def test_a_draft_with_no_rows_says_so(self):
        found = truth_map.check_drafted("## Where the material lives\n", ANSWERS)
        self.assertEqual([truth_map.CODE_NO_ROWS], [one.code for one in found.problems])

    def test_the_source_map_is_draftable_and_never_required(self):
        kinds = {kind.key: kind for kind in constants.BASE_KINDS}
        self.assertTrue(kinds["stack"].draftable)
        self.assertNotIn(constants.STACK_PATH, constants.REQUIRED_CONTEXT_FILES)

    def test_the_template_lists_what_each_skill_needs_installed(self):
        for root in (support.TEMPLATES_DIR, os.path.join(support.PLUGIN_DIR, "templates")):
            text = support.read(os.path.join(root, "company-base", "access", "stack.md"))
            self.assertIn("## What each skill needs installed", text)


class TestTheClosingOffersTheSourceMapOnce(unittest.TestCase):
    """Offered once, after the two setup documents, and never as a step."""

    def test_each_closing_message_offers_it_once(self):
        for content in (None, "/tmp/marketing"):
            with self.subTest(linked=bool(content)):
                message = join_flow.closing_message(
                    "/tmp/base", support.PLUGIN_DIR, content_root=content
                )
                self.assertEqual(1, message.count('"draft my source map"'))
                self.assertNotIn("?", message.split("draft my source map")[1].split("\n\n")[0])


if __name__ == "__main__":
    unittest.main()
