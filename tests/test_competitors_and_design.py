"""Track 4, Units T4.4 and T4.5: the competitors and the design guide.

Competitors are their own document again (call 2), so a competitor's move is
recorded against them and leaves the positioning alone, and every fact carries
the date and the material it came from. The design guide holds the visual
decisions a piece of work must respect as sentences, in four parts, with tone
left to the voice guide, no colour code the brand guide does not state, and
nothing but text written into the base.

These validate written drafts, the checks and the writes. They do not claim a
model writes the right prose. The company in every fixture is made up.
"""

import datetime
import os
import unittest

import support
import test_base_contents as contents
import test_moment_of_use as moment_tests

from gtmbase import (
    base_reader,
    constants,
    drafting,
    join_flow,
    moment,
    names,
    stale,
    state,
)
from gtmbase.errors import DraftError

COMPETITORS = constants.COMPETITORS_PATH
POSITIONING = "context/positioning.md"
DESIGN = "context/design.md"

BRAND_GUIDE = """# Larkspur brand guide

Our primary action colour is Larkspur Blue, #1F6FEB. Backgrounds are white.

Headlines are set in Inter Bold, and body text in Inter Regular.

The logo is the word Larkspur beside a small flower. It appears in Larkspur
Blue or in white, and is never stretched or outlined.

Never put text over a photograph.
"""

DESIGN_FROM_THE_GUIDE = """```markdown
---
kind: design
owner: owner@example.com
last_confirmed: 2026-11-20
sources: [larkspur-brand.md (2026-11-02)]
status: draft
---

# Design guide

## Colour by role

The primary action colour is Larkspur Blue, #1F6FEB. Backgrounds are white.

## Type

Headlines are set in Inter Bold, and body text in Inter Regular.

## Logo rules

The logo is the word Larkspur beside a small flower. It appears in Larkspur
Blue or in white, and is never stretched or outlined.

## Forbidden devices

- Text over a photograph.

## What the material does not show

The brand guide names no warning colour.
```
"""


def parsed(step, text):
    return drafting.parse(step, text)


class TestTheKindsAreListed(unittest.TestCase):
    def test_competitors_sit_after_the_positioning_and_differ_by_business(self):
        keys = [kind.key for kind in constants.BASE_KINDS]
        self.assertEqual(keys.index("positioning") + 1, keys.index("competitors"))
        kind = dict((one.key, one) for one in constants.BASE_KINDS)["competitors"]
        self.assertEqual(COMPETITORS, kind.pattern)
        self.assertTrue(kind.differs_by_business)
        self.assertTrue(kind.draftable and kind.adoptable)

    def test_the_design_guide_is_draftable_and_serves_the_whole_company(self):
        kind = dict((one.key, one) for one in constants.BASE_KINDS)["design"]
        self.assertFalse(kind.differs_by_business)
        self.assertTrue(kind.draftable and kind.adoptable)

    def test_each_has_a_plain_name(self):
        self.assertEqual("your competitors document", names.document_name(COMPETITORS))
        self.assertEqual("Competitors", names.KIND_LABELS["competitors"])

    def test_the_follow_through_rows_are_the_plans(self):
        follows = constants.KIND_FOLLOWS
        self.assertIn("competitors", follows["icps"])
        self.assertIn("competitors", follows["positioning"])
        self.assertIn("competitors", follows["product"])
        self.assertEqual(("positioning",), follows["competitors"])
        self.assertEqual((), follows["design"])


# --- T4.4: competitors -----------------------------------------------------------


class TestEveryFactIsDated(unittest.TestCase):
    def setUp(self):
        self.text = contents.captured("competitors.md")

    def test_the_fixture_parses_with_every_fact_dated_and_sourced(self):
        draft = parsed(drafting.STEP_COMPETITORS, self.text)
        self.assertEqual(COMPETITORS, draft.path)

    def test_a_fact_without_its_source_and_date_is_refused(self):
        undated = self.text.replace(
            " (source: larkspur-site.md, 2026-11-02)\n- Where", "\n- Where", 1
        )
        self.assertNotEqual(undated, self.text)
        with self.assertRaises(DraftError) as raised:
            parsed(drafting.STEP_COMPETITORS, undated)
        self.assertEqual(drafting.CODE_FACT_UNDATED, raised.exception.code)

    def test_a_fact_with_a_source_and_no_date_is_refused(self):
        undated = self.text.replace("larkspur-site.md, 2026-11-02)", "larkspur-site.md)", 1)
        with self.assertRaises(DraftError) as raised:
            parsed(drafting.STEP_COMPETITORS, undated)
        self.assertEqual(drafting.CODE_FACT_UNDATED, raised.exception.code)

    def test_a_competitor_named_with_no_claim_gets_an_empty_section(self):
        # The fixture's "Doing nothing" holds only the sentence for no claim.
        self.assertIn("### Doing nothing\n\n" + drafting.NOT_COVERED, self.text)
        empty = self.text.replace(
            "### Doing nothing\n\n" + drafting.NOT_COVERED + "\n",
            "### Doing nothing\n\n### Building it in house\n\n",
        )
        parsed(drafting.STEP_COMPETITORS, empty)


class TestACompetitorsMoveFlagsOnlyTheCompetitors(contents.AfterSetup):
    def test_a_price_change_flags_the_competitors_and_not_the_positioning(self):
        earlier = datetime.datetime.combine(
            state.today() - datetime.timedelta(days=3), datetime.time(9, 0)
        )
        self.approved(drafting.STEP_COMPETITORS, now=earlier)
        today = state.today().isoformat()
        self.base.add_change(
            moment_tests.entry_text(affects=(COMPETITORS,))
            .replace("decided_on: %s" % moment_tests.TUESDAY, "decided_on: %s" % today)
            .replace("written_on: %s" % moment_tests.THURSDAY, "written_on: %s" % today)
            .replace("review_by: 2026-09-01", "review_by: 2099-01-01")
        )

        def flagged(path):
            return moment.check(
                self.base.root,
                self.base.base_id,
                path,
                session_id=moment_tests.SESSION,
                runner=support.NoRemoteRunner(),
                now=state.today(),
            ).flagged

        self.assertTrue(flagged(COMPETITORS))
        self.assertFalse(flagged(POSITIONING))

    def test_it_is_read_and_owned_like_any_other_document(self):
        self.approved(drafting.STEP_COMPETITORS)
        held = {one.path: one for one in base_reader.context_files(self.base.root)}
        self.assertIn(COMPETITORS, held)
        self.assertEqual(["owner@example.com"], held[COMPETITORS].owners)


class TestTheFollowThrough(unittest.TestCase):
    HELD = [
        contents.info("context/icps.md", "icp"),
        contents.info(POSITIONING, "positioning"),
        contents.info(COMPETITORS, "competitors"),
    ]

    def test_a_competitors_change_suggests_the_positioning(self):
        mentioned, following = stale.suggested_paths(self.HELD, "the competitors changed")
        self.assertEqual([COMPETITORS], mentioned)
        self.assertEqual([POSITIONING], following)

    def test_a_profile_change_suggests_the_competitors_the_base_holds(self):
        _mentioned, following = stale.suggested_paths(self.HELD, "the icps changed")
        self.assertIn(COMPETITORS, following)

    def test_the_positioning_prompt_keeps_a_short_list_and_points_here(self):
        prompt = drafting.prompt_text(drafting.STEP_POSITIONING)
        self.assertIn("competitors document", prompt)


LONG_POSITIONING = """---
kind: positioning
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Positioning

## What we sell

One screen for every carrier quote.

## Alternatives and competitors

### A spreadsheet

Brokers keep quotes in a spreadsheet.

### Quote boards

A quote board lists loads.

### Email

Quotes arrive by email.

### Doing nothing

Some brokers call every carrier.
"""


class TestALongAlternativesPartIsOfferedTheMove(unittest.TestCase):
    def a_base(self, sandbox, positioning, competitors=None):
        import test_drift_grade as drift

        documents = drift.the_documents()
        documents[POSITIONING] = positioning
        if competitors is not None:
            documents[COMPETITORS] = competitors
        return drift.a_base(sandbox, documents)

    def inventory_output(self, root):
        import subprocess
        import sys

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        return subprocess.run(
            [sys.executable, script, "--inventory"],
            cwd=root,
            capture_output=True,
            text=True,
        ).stdout

    def test_it_is_offered_as_a_proposal_and_nothing_is_written(self):
        from gtmbase import alternatives

        with support.Sandbox() as sandbox:
            root, _base_id = self.a_base(sandbox, LONG_POSITIONING)
            before = support.status_of(root)
            said = self.inventory_output(root)
            self.assertIn(alternatives.MOVE_OFFER, said)
            self.assertEqual(before, support.status_of(root))
            self.assertFalse(os.path.exists(os.path.join(root, COMPETITORS)))
            self.assertEqual(LONG_POSITIONING, support.read(os.path.join(root, POSITIONING)))

    def test_a_short_list_is_not(self):
        from gtmbase import alternatives

        short = LONG_POSITIONING.split("### Quote boards")[0]
        with support.Sandbox() as sandbox:
            root, _base_id = self.a_base(sandbox, short)
            self.assertIsNone(alternatives.move_offer(root))

    def test_a_base_with_a_competitors_document_is_not(self):
        from gtmbase import alternatives

        with support.Sandbox() as sandbox:
            root, _base_id = self.a_base(
                sandbox, LONG_POSITIONING, competitors=support.skill_document("competitors", "Competitors")
            )
            self.assertIsNone(alternatives.move_offer(root))


# --- T4.5: the design guide ------------------------------------------------------


class TestTheDesignGuideReadsBack(unittest.TestCase):
    def setUp(self):
        self.text = contents.captured("design.md")

    def test_material_with_no_design_names_each_gap(self):
        draft = parsed(drafting.STEP_DESIGN, self.text)
        self.assertEqual(DESIGN, draft.path)

    def test_the_four_parts_and_the_gaps_in_order(self):
        import re

        headings = re.findall(r"^## (.*)$", self.text, re.MULTILINE)
        self.assertEqual(list(drafting.LATER_SECTIONS[drafting.STEP_DESIGN]), headings)

    def test_an_empty_forbidden_list_is_a_real_answer(self):
        self.assertIn("## Forbidden devices\n\n## What", self.text)
        parsed(drafting.STEP_DESIGN, self.text)

    def test_a_part_the_material_does_not_cover_must_be_named_as_a_gap(self):
        unnamed = self.text.replace("colour, type or the logo", "colour or type")
        with self.assertRaises(DraftError) as raised:
            parsed(drafting.STEP_DESIGN, unnamed)
        self.assertEqual(drafting.CODE_GAP_UNNAMED % "Logo rules", raised.exception.code)

    def test_a_picture_is_never_written(self):
        for picture in (
            "![the logo](logo.png)",
            '<img src="logo.png">',
            "(data:image/png;base64,AAAA)",
        ):
            with self.subTest(picture=picture):
                with self.assertRaises(DraftError) as raised:
                    parsed(
                        drafting.STEP_DESIGN,
                        DESIGN_FROM_THE_GUIDE.replace(
                            "beside a small flower.", "beside a small flower. " + picture
                        ),
                    )
                self.assertEqual(drafting.CODE_IMAGE, raised.exception.code)

    def test_the_starter_carries_exactly_its_parts(self):
        import re

        for step in (drafting.STEP_COMPETITORS, drafting.STEP_DESIGN):
            with self.subTest(step=step):
                text = support.read(os.path.join(contents.STARTERS, step + ".md"))
                headings = re.findall(r"^## (.*)$", text, re.MULTILINE)
                self.assertEqual(list(drafting.LATER_SECTIONS[step]), headings)


class TestADesignGuideFromABrandGuide(contents.AfterSetup):
    def setUp(self):
        super(TestADesignGuideFromABrandGuide, self).setUp()
        support.write(os.path.join(self.content, "larkspur-brand.md"), BRAND_GUIDE)
        self.run_id = join_flow.new_run()
        join_flow.list_sources(self.content, self.run_id)
        join_flow.freeze_sources(self.content, contents.SESSION, self.run_id)

    def test_the_brand_guides_own_colour_code_is_kept(self):
        _path, reviewed = self.reviewed(drafting.STEP_DESIGN, DESIGN_FROM_THE_GUIDE)
        self.assertTrue(reviewed.ready, reviewed.codes)

    def test_a_colour_code_the_guide_does_not_state_is_refused(self):
        _path, reviewed = self.reviewed(
            drafting.STEP_DESIGN,
            DESIGN_FROM_THE_GUIDE.replace("Backgrounds are white.", "Backgrounds are #F6F8FA."),
        )
        self.assertFalse(reviewed.ready)
        self.assertIn(drafting.CODE_FIGURE_NOT_IN_SOURCES, reviewed.codes)

    def test_only_the_one_text_file_is_written_into_the_base(self):
        result = self.approved(drafting.STEP_DESIGN, DESIGN_FROM_THE_GUIDE)
        self.assertEqual(DESIGN, result.path)
        for dirpath, _dirs, files in os.walk(self.base.root):
            if os.sep + ".git" in dirpath + os.sep:
                continue
            for name in files:
                self.assertFalse(
                    name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".otf", ".ttf", ".woff", ".woff2")),
                    name,
                )

    def test_it_is_owned_and_flagged_like_any_other(self):
        earlier = datetime.datetime.combine(
            state.today() - datetime.timedelta(days=3), datetime.time(9, 0)
        )
        self.approved(drafting.STEP_DESIGN, DESIGN_FROM_THE_GUIDE, now=earlier)
        held = {one.path: one for one in base_reader.context_files(self.base.root)}
        self.assertEqual(["owner@example.com"], held[DESIGN].owners)
        today = state.today().isoformat()
        self.base.add_change(
            moment_tests.entry_text(affects=(DESIGN,))
            .replace("decided_on: %s" % moment_tests.TUESDAY, "decided_on: %s" % today)
            .replace("written_on: %s" % moment_tests.THURSDAY, "written_on: %s" % today)
            .replace("review_by: 2026-09-01", "review_by: 2099-01-01")
        )
        self.assertTrue(
            moment.check(
                self.base.root,
                self.base.base_id,
                DESIGN,
                session_id=moment_tests.SESSION,
                runner=support.NoRemoteRunner(),
                now=state.today(),
            ).flagged
        )


if __name__ == "__main__":
    unittest.main()
