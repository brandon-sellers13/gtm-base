"""Unit 2.5a of Plan 1: the source map's rows, parsed and checked, read only.

The source map (`access/stack.md`) says, for each kind of data a job needs,
where it lives, which connected tool reads it, and what to do when that tool
is not connected. These tests hold the parser that turns its table into rows
a skill can read. Nothing here writes a row: adding one is a prepared change
approved through Unit 4.2a, which is built later, so that scenario of the plan
waits for it and is listed in the hand-over.

Every fixture is written from scratch for these tests. The company, its two
businesses and every row are made up.
"""

import os
import socket
import subprocess
import unittest
from unittest import mock

import support
import test_session_start

from gtmbase import constants, truth_map

TEMPLATE_STACK = os.path.join(
    support.REPO_ROOT, "templates", "company-base", "access", "stack.md"
)
PLUGIN_TEMPLATE_STACK = os.path.join(
    support.TEMPLATES_DIR, "company-base", "access", "stack.md"
)

HEADER = (
    "| Kind of data | Business | Where it lives | What reads it "
    "| If that is not connected |\n"
    "|---|---|---|---|---|\n"
)

SETTINGS = """---
kind: stack
owner: owner@example.com
sources: []
status: draft
---

# Stack

This file tells the AI where the work comes from and where it goes.

## Where the material lives

For each kind of material, where it lives and which connected tool reads it.

"""

AFTER = """
## Where the work goes

Ad drafts in the ad account.
"""


def stack_with(rows, header=HEADER):
    return SETTINGS + header + "".join(row + "\n" for row in rows) + AFTER


SPEND = (
    "| Ad spend | courier-app | The paid media dashboard | The dashboard tool "
    "| Ask the owner for the weekly export |"
)
TRIALS = (
    "| Trials | courier-app | The product analytics workspace | The analytics "
    "connector | Read the Monday summary |"
)
NO_FALLBACK = (
    "| Subscribers | courier-app | The billing system | The billing connector |  |"
)

MAP_WITH_TWO = """---
kind: map
owner: owner@example.com
sources: []
status: draft
---

# Map

## Settings

confirmation_threshold_days: 30
not_now_days: 7
businesses: insights (Acme Insights), courier-app (the courier app)
"""


class TestTheTable(unittest.TestCase):
    """Happy path: a well-formed table parses into rows with all five columns."""

    def test_a_well_formed_table_parses_into_rows(self):
        found = truth_map.parse(stack_with([SPEND, TRIALS]), ["insights", "courier-app"])
        self.assertTrue(found.has_table)
        self.assertEqual([], found.problems)
        self.assertEqual(2, len(found.rows))
        first = found.rows[0]
        self.assertEqual("Ad spend", first.kind_of_data)
        self.assertEqual("courier-app", first.business)
        self.assertEqual("The paid media dashboard", first.where)
        self.assertEqual("The dashboard tool", first.read_by)
        self.assertEqual("Ask the owner for the weekly export", first.if_not_connected)
        self.assertEqual([], first.problems)

    def test_each_row_says_the_line_it_came_from(self):
        text = stack_with([SPEND, TRIALS])
        found = truth_map.parse(text, ["courier-app"])
        lines = text.split("\n")
        for row in found.rows:
            self.assertIn(row.kind_of_data, lines[row.line_number - 1])

    def test_a_row_missing_its_fallback_is_incomplete_not_accepted(self):
        found = truth_map.parse(stack_with([SPEND, NO_FALLBACK]), ["courier-app"])
        self.assertEqual(["Ad spend"], [row.kind_of_data for row in found.rows])
        self.assertEqual(1, len(found.incomplete))
        self.assertEqual(["if_not_connected"], found.incomplete[0].missing)
        self.assertIn(
            truth_map.CODE_INCOMPLETE, [problem.code for problem in found.problems]
        )

    def test_whole_company_is_a_business_every_map_has(self):
        row = (
            "| The creative registry | the whole company | The team workspace "
            "| The workspace connector | Ask the owner |"
        )
        for listed in ([], ["courier-app"]):
            with self.subTest(listed=listed):
                found = truth_map.parse(stack_with([row]), listed)
                self.assertEqual([], found.problems)
                self.assertEqual(truth_map.WHOLE_COMPANY, found.rows[0].business)

    def test_a_business_may_be_named_by_its_name_in_the_map(self):
        row = SPEND.replace("| courier-app |", "| The Courier App |")
        found = truth_map.parse(
            stack_with([row]), ["courier-app"], names={"courier-app": "the courier app"}
        )
        self.assertEqual([], found.problems)
        self.assertEqual("courier-app", found.rows[0].business)

    def test_a_question_left_open_keeps_the_row_and_says_so(self):
        row = (
            "| Account links | courier-app | [your call: which tool counts them "
            "for the goal?] | Not known yet | Leave the comparison out |"
        )
        found = truth_map.parse(stack_with([row]), ["courier-app"])
        self.assertEqual(1, len(found.rows))
        self.assertEqual(
            ("which tool counts them for the goal?",), found.rows[0].open_questions
        )

    def test_a_pipe_written_with_a_backslash_stays_inside_its_cell(self):
        row = SPEND.replace("The dashboard tool", "The dashboard \\| reports tool")
        found = truth_map.parse(stack_with([row]), ["courier-app"])
        self.assertEqual([], found.problems)
        self.assertEqual("The dashboard | reports tool", found.rows[0].read_by)

    def test_a_row_with_the_wrong_number_of_cells_is_reported(self):
        found = truth_map.parse(
            stack_with([SPEND, "| Trials | courier-app | somewhere |"]),
            ["courier-app"],
        )
        self.assertEqual(1, len(found.rows))
        self.assertIn(
            truth_map.CODE_MALFORMED_ROW, [problem.code for problem in found.problems]
        )

    def test_a_table_with_other_columns_is_reported_and_gives_no_rows(self):
        header = "| What | Where |\n|---|---|\n"
        found = truth_map.parse(
            stack_with(["| Ad spend | the dashboard |"], header=header), []
        )
        self.assertEqual([], found.rows)
        self.assertIn(
            truth_map.CODE_OTHER_COLUMNS, [problem.code for problem in found.problems]
        )

    def test_the_header_is_matched_however_it_is_spaced_or_capitalised(self):
        header = (
            "|kind of data|BUSINESS|  Where it lives |What reads it|"
            "If that is not connected|\n| :--- | --- | --- | --- | ---: |\n"
        )
        found = truth_map.parse(stack_with([SPEND], header=header), ["courier-app"])
        self.assertEqual([], found.problems)
        self.assertEqual(1, len(found.rows))

    def test_only_the_material_section_is_read(self):
        text = stack_with([SPEND]).replace(
            "Ad drafts in the ad account.", HEADER + TRIALS
        )
        found = truth_map.parse(text, ["courier-app"])
        self.assertEqual(["Ad spend"], [row.kind_of_data for row in found.rows])


class TestThePlainStarter(unittest.TestCase):
    """Edge case: the prose starter with no table is no rows and no error."""

    def test_the_older_prose_starter_parses_as_no_rows_and_no_error(self):
        text = support.read(TEMPLATE_STACK)
        prose_only = text.split("| Kind of data")[0]
        for given in (text, prose_only):
            with self.subTest(table="| Kind of data" in given):
                found = truth_map.parse(given, [])
                self.assertEqual([], found.rows)
                self.assertEqual([], found.incomplete)
                self.assertEqual([], found.problems)

    def test_the_template_holds_the_empty_table_with_its_five_columns(self):
        found = truth_map.parse(support.read(TEMPLATE_STACK), [])
        self.assertTrue(found.has_table)
        self.assertEqual([], found.rows)

    def test_the_plugin_copy_of_the_template_is_the_same_file(self):
        self.assertEqual(support.read(TEMPLATE_STACK), support.read(PLUGIN_TEMPLATE_STACK))

    def test_a_base_with_no_source_map_reads_as_no_rows(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            found = truth_map.read(root)
            self.assertFalse(found.has_file)
            self.assertEqual([], found.rows)
            self.assertEqual([], found.problems)

    def test_a_settings_block_never_closed_still_reads_the_table(self):
        """The whole file is screened then, so the owner line is reported, honestly."""
        text = stack_with([SPEND]).replace("status: draft\n---\n", "status: draft\n", 1)
        found = truth_map.parse(text, ["courier-app"])
        self.assertEqual(1, len(found.rows))
        self.assertEqual(
            [(truth_map.CODE_SCREENED, 3)],
            [(p.code, p.line_number) for p in found.problems],
        )


class TestABusinessTheMapDoesNotList(unittest.TestCase):
    """Edge case: a row whose business is not in the map is reported, not dropped."""

    def test_the_row_is_kept_and_reported(self):
        row = SPEND.replace("| courier-app |", "| wholesale |")
        found = truth_map.parse(stack_with([row, TRIALS]), ["insights", "courier-app"])
        self.assertEqual(2, len(found.rows))
        kept = found.rows[0]
        self.assertEqual([truth_map.CODE_BUSINESS_NOT_IN_MAP], kept.problems)
        self.assertEqual(
            [kept.line_number],
            [
                problem.line_number
                for problem in found.problems
                if problem.code == truth_map.CODE_BUSINESS_NOT_IN_MAP
            ],
        )

    def test_a_map_listing_no_businesses_reports_every_named_business(self):
        found = truth_map.parse(stack_with([SPEND]), [])
        self.assertEqual(1, len(found.rows))
        self.assertEqual(
            [truth_map.CODE_BUSINESS_NOT_IN_MAP],
            [problem.code for problem in found.problems],
        )

    def test_read_takes_the_businesses_from_the_base_map(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            support.write(os.path.join(root, constants.MAP_PATH), MAP_WITH_TWO)
            support.write(
                os.path.join(root, constants.STACK_PATH),
                stack_with([SPEND, SPEND.replace("courier-app", "wholesale")]),
            )
            found = truth_map.read(root)
            self.assertTrue(found.has_file)
            self.assertEqual([[], [truth_map.CODE_BUSINESS_NOT_IN_MAP]],
                             [row.problems for row in found.rows])

    def test_a_map_whose_businesses_cannot_be_read_is_said_once(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            support.write(
                os.path.join(root, constants.MAP_PATH),
                MAP_WITH_TWO.replace("courier-app (", "Courier App! ("),
            )
            support.write(os.path.join(root, constants.STACK_PATH), stack_with([SPEND]))
            found = truth_map.read(root)
            self.assertEqual(1, len(found.rows))
            self.assertIn(
                truth_map.CODE_BUSINESSES_UNREADABLE,
                [problem.code for problem in found.problems],
            )


class TestTheReviewOfThisUnit(unittest.TestCase):
    """The correctness review of 2026-10-10, one test per finding about the parser."""

    def test_a_line_separator_above_the_table_never_lets_a_key_row_through(self):
        """Finding 1: the screens and the table counted lines two different ways."""
        for separator in ("\u2028", "\u2029", "\x85", "\x0c", "\x1e"):
            with self.subTest(separator=repr(separator)):
                text = stack_with([SPEND, TestTheScreens.KEY_ROW]).replace(
                    "which connected tool reads it.",
                    "which connected tool" + separator + " reads it.",
                )
                found = truth_map.parse(text, ["courier-app"])
                self.assertEqual(["Ad spend"], [row.kind_of_data for row in found.rows])
                self.assertEqual("The dashboard tool", found.rows[0].read_by)
                lines = text.split("\n")
                refused = [p for p in found.problems if p.code == truth_map.CODE_SCREENED]
                self.assertEqual(1, len(refused))
                self.assertIn("the key sk-", lines[refused[0].line_number - 1])

    def test_a_row_that_leaves_off_its_fallback_column_is_incomplete(self):
        """Finding 6: four cells is a row missing its fallback, not a malformed one."""
        row = "| Subscribers | courier-app | The billing system | The billing connector |"
        found = truth_map.parse(stack_with([row]), ["courier-app"])
        self.assertEqual([], found.rows)
        self.assertEqual(["if_not_connected"], found.incomplete[0].missing)
        self.assertEqual([truth_map.CODE_INCOMPLETE], [p.code for p in found.problems])

    def test_a_cell_holding_only_a_dash_is_empty(self):
        row = NO_FALLBACK.replace("|  |", "| - |")
        found = truth_map.parse(stack_with([row]), ["courier-app"])
        self.assertEqual([], found.rows)
        self.assertEqual(1, len(found.incomplete))

    def test_a_heading_inside_a_block_of_code_does_not_end_the_section(self):
        text = stack_with([SPEND]).replace(
            "For each kind of material, where it lives and which connected tool reads it.",
            "For each kind of material.\n\n```\n# not a heading\n```\n",
        )
        found = truth_map.parse(text, ["courier-app"])
        self.assertEqual(1, len(found.rows))

    def test_when_the_businesses_cannot_be_read_no_row_is_called_unlisted(self):
        """A residual risk the review named: two sentences that contradicted each other."""
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            support.write(
                os.path.join(root, constants.MAP_PATH),
                MAP_WITH_TWO.replace("courier-app (", "Courier App! ("),
            )
            support.write(os.path.join(root, constants.STACK_PATH), stack_with([SPEND]))
            found = truth_map.read(root)
            self.assertEqual(
                [truth_map.CODE_BUSINESSES_UNREADABLE], [p.code for p in found.problems]
            )
            self.assertEqual([], found.rows[0].problems)

    def test_a_source_map_reached_through_a_linked_folder_is_not_read(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            support.write(os.path.join(elsewhere, "stack.md"), stack_with([SPEND]))
            os.symlink(elsewhere, os.path.join(root, "access"))
            found = truth_map.read(root)
            self.assertEqual([], found.rows)
            self.assertEqual([truth_map.CODE_UNREADABLE], [p.code for p in found.problems])


class TestNothingIsReachedFor(unittest.TestCase):
    """Security: reading the source map calls nothing, on this computer or off it."""

    def test_reading_makes_no_network_call_and_runs_no_program(self):
        def refuse(*_args, **_kwargs):
            raise AssertionError("the source map reader reached for something")

        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            support.write(os.path.join(root, constants.MAP_PATH), MAP_WITH_TWO)
            support.write(os.path.join(root, constants.STACK_PATH), stack_with([SPEND]))
            with mock.patch.object(socket.socket, "connect", refuse), mock.patch.object(
                socket, "create_connection", refuse
            ), mock.patch.object(subprocess, "Popen", refuse), mock.patch.object(
                subprocess, "run", refuse
            ), mock.patch(
                "gtmbase.gitcmd.GitRunner.run", refuse
            ):
                found = truth_map.read(root)
            self.assertEqual(1, len(found.rows))

    def test_the_module_names_no_way_to_reach_anything(self):
        source = support.read(
            os.path.join(support.LIB_DIR, "gtmbase", "truth_map.py")
        )
        for word in ("subprocess", "socket", "urllib", "gitcmd", "GitRunner", "http"):
            with self.subTest(word=word):
                self.assertNotIn(word, source)


class TestTheScreens(unittest.TestCase):
    """Security: a line shaped like a key or token is refused by the proposal screens."""

    # Made up, and put together here so no line of this file is shaped like one.
    KEY_ROW = (
        "| Ad spend | courier-app | The dashboard | the key sk-"
        + "a1B2c3D4e5F6g7H8i9J0k1L2"
        + " | Ask the owner |"
    )

    def test_a_row_holding_a_key_is_refused_and_the_key_is_never_carried(self):
        found = truth_map.parse(stack_with([self.KEY_ROW, TRIALS]), ["courier-app"])
        self.assertEqual(["Trials"], [row.kind_of_data for row in found.rows])
        refused = [p for p in found.problems if p.code == truth_map.CODE_SCREENED]
        self.assertEqual(1, len(refused))
        self.assertTrue(refused[0].pattern_class)
        for problem in found.problems:
            self.assertNotIn("a1B2c3D4", repr(problem))
            self.assertNotIn("a1B2c3D4", problem.sentence())

    def test_the_screens_are_the_ones_a_proposal_gets(self):
        from gtmbase import scan

        for row in (
            self.KEY_ROW,
            SPEND.replace("The dashboard tool", "ops@acme.example"),
            SPEND.replace(
                "The dashboard tool", "https://reader:hunter2secret@dash.acme.example"
            ),
        ):
            with self.subTest(row=row[30:70]):
                self.assertTrue(
                    scan.scan_text(row, None, "the source map")
                    or scan.scan_source_map(row, None)
                )
                found = truth_map.parse(stack_with([row]), ["courier-app"])
                self.assertEqual([], found.rows)
                self.assertEqual(
                    [truth_map.CODE_SCREENED], [p.code for p in found.problems]
                )

    def test_an_address_carrying_a_password_is_refused_even_when_allowed(self):
        """The source map's own screen, which the base's allowed words never open."""
        address = "reader:hunter2secret@dash.acme.example"
        row = SPEND.replace("The dashboard tool", "https://" + address)
        found = truth_map.parse(
            stack_with([row]), ["courier-app"], allowlist=frozenset([address.split(":")[1]])
        )
        self.assertEqual([], found.rows)
        self.assertEqual([truth_map.CODE_SCREENED], [p.code for p in found.problems])

    def test_a_key_outside_the_table_is_refused_too(self):
        text = stack_with([SPEND]).replace(
            "Ad drafts in the ad account.",
            "Token: ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
        )
        found = truth_map.parse(text, ["courier-app"])
        self.assertEqual(1, len(found.rows))
        self.assertEqual([truth_map.CODE_SCREENED], [p.code for p in found.problems])

    def test_the_owner_line_in_the_settings_block_is_not_a_finding(self):
        found = truth_map.parse(stack_with([SPEND]), ["courier-app"])
        self.assertEqual([], found.problems)

    def test_the_base_allowed_words_are_honoured_as_a_proposal_honours_them(self):
        row = SPEND.replace("The dashboard tool", "ops@acme.example")
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.make_base(root)
            support.write(os.path.join(root, constants.MAP_PATH), MAP_WITH_TWO)
            support.write(os.path.join(root, constants.STACK_PATH), stack_with([row]))
            self.assertEqual([], truth_map.read(root).rows)
            support.write(
                os.path.join(root, constants.ALLOWLIST_PATH), "ops@acme.example\n"
            )
            self.assertEqual(1, len(truth_map.read(root).rows))


class TestSessionStartLeavesTheSourceMapOut(
    support.PastTheFirstBackupReview, test_session_start.SessionStartHelpers
):
    """Edge case: session start injects the map and does not inject the source map."""

    def test_the_map_is_injected_and_the_source_map_is_not(self):
        root, _base_id = self.joined_base()
        self.add_files(root)
        support.write(os.path.join(root, constants.STACK_PATH), stack_with([SPEND]))
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "the source map"], cwd=root)
        support.git(["push", "-q", "origin", "main"], cwd=root)
        injected = self.run_hook(root, part="context")
        self.assertIsInstance(injected, str)
        self.assertIn("confirmation_threshold_days", injected)
        self.assertNotIn("The paid media dashboard", injected)
        self.assertNotIn("Kind of data", injected)


if __name__ == "__main__":
    unittest.main()
