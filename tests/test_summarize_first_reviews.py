"""The correctness and security reviews of the summarize-first build (2026-10-11).

Each test here failed before its fix. Material is made up and lives in a
temporary home folder.
"""

import json
import os
import unittest

import support
from test_notes import TODAY, agreed, fenced_notes, note, settle, take_notes, LENDERS, BANKS
from test_citations import ABOUT, POSITIONING, rows, ids, support_answer

from gtmbase import citations, drafting, join_flow, notes


def fake(note_id, quote, status="settled", kind="fact", customer="", segment="", source=1):
    item = notes.Note(
        {"source": source, "kind": kind, "segment": segment, "customer": customer,
         "figure": "", "status": status, "quote": quote},
        id=note_id,
    )
    return item


class TestFiguresKeepTheirUnits(unittest.TestCase):
    """Correctness H1: a figure is matched whole, with its unit, in one quote."""

    def test_a_figure_inside_a_larger_number_or_with_another_unit_is_refused(self):
        readable = {"n1": fake("n1", "Churn fell 14% in Q3 to $40 per seat")}
        for line in ("Churn fell 4% [n1]", "Price is 40% off [n1]", "Churn fell 14 points [n1]"):
            found = citations.check(line, readable, [])
            self.assertIn(citations.CODE_FIGURE, [code for _b, code in found], line)
        for line in ("Churn fell 14% [n1]", "It costs $40 per seat [n1]", "In Q3 churn fell [n1]"):
            self.assertEqual([], citations.check(line, readable, []), line)

    def test_an_amount_written_with_a_capital_unit_stands_when_its_quote_has_it(self):
        # Found in the scored re-run of 2026-11-25: "$900K" was read as "$900",
        # which no quote holds bare, so a figure word for word in its note was refused.
        readable = {"n1": fake("n1", "The pilot costs $900K a year, about $1.4M in all, 3X the old price")}
        for line in ("The pilot costs $900K a year [n1]", "About $1.4M in all [n1]", "3X the old price [n1]"):
            self.assertEqual([], citations.check(line, readable, []), line)
        for line in ("The pilot costs $900M a year [n1]", "The pilot costs $900 a year [n1]"):
            found = citations.check(line, readable, [])
            self.assertIn(citations.CODE_FIGURE, [code for _b, code in found], line)

    def test_each_figure_must_sit_in_one_cited_quote(self):
        readable = {"n1": fake("n1", "Plan A is 12"), "n2": fake("n2", "Plan B is 0.5% off")}
        found = citations.check("Plan A is 12.5% off [n1, n2]", readable, [])
        self.assertIn(citations.CODE_FIGURE, [code for _b, code in found])


class TestHeadingsAreCheckedToo(unittest.TestCase):
    """Correctness H4: a heading the draft writes is held to the same rules."""

    def test_a_heading_with_a_citation_a_customer_or_a_figure_is_refused(self):
        readable = {"n1": fake("n1", "Churn fell 14%")}
        found = citations.check(
            "### Acme cut churn by 99% [n1]\n\nChurn fell 14% [n1]", readable, ["Acme"]
        )
        codes = [code for _b, code in found]
        self.assertIn(citations.CODE_HEADING_CITES, codes)
        self.assertIn(citations.CODE_CUSTOMER, codes)
        self.assertIn(citations.CODE_FIGURE, codes)

    def test_a_segments_own_name_may_carry_digits(self):
        readable = {"n1": fake("n1", "Small firms buy first")}
        body = "### SMB (10-50)\n\nSmall firms buy first [n1]"
        self.assertEqual([], citations.check(body, readable, [], allowed_headings=["SMB (10-50)"]))


class TestCustomersByTheirNames(unittest.TestCase):
    """Correctness M11: a name is matched as written, short forms included."""

    def test_an_ordinary_word_is_not_a_customer_but_a_short_name_is(self):
        found = [fake("n1", "Box renewed", kind="customer", customer="Box"),
                 fake("n2", "Acme Corporation bought", kind="customer", customer="Acme Corporation")]
        names = citations.customer_names(found, "Bakehouse", [])
        readable = {"n3": fake("n3", "It works out of the box")}
        self.assertEqual([], citations.check("It works out of the box [n3]", readable, names))
        refused = citations.check("Acme bought it first [n3]", readable, names)
        self.assertIn(citations.CODE_CUSTOMER, [code for _b, code in refused])

    def test_the_company_itself_is_never_taken_for_a_customer(self):
        found = [fake("n1", "Bakehouse Supply sold", kind="customer", customer="Bakehouse Supply")]
        self.assertEqual([], citations.customer_names(found, "Bakehouse Supply", []))


class TestTakingLinesOutLeavesAReadableDraft(unittest.TestCase):
    """Correctness M10 and L13."""

    def test_two_items_taken_out_side_by_side_pass_the_check_again(self):
        body = "## Part\n\n- a [n9]\n- b [n9]\n"
        problems = citations.check(body, {}, [])
        again = citations.take_out(body, problems)
        self.assertEqual([], citations.check(again, {}, []))

    def test_a_table_header_needs_no_citation(self):
        readable = {"n1": fake("n1", "churn 14%")}
        body = "| Metric | Value |\n|---|---|\n| churn | 14% [n1] |\n"
        self.assertEqual([], citations.check(body, readable, []))


PAGES = {
    "segments/icp-lenders.md": LENDERS,
    "segments/icp-banks.md": BANKS,
    "about.md": ABOUT,
    "contact.md": "# Contact\n\nContact jane@acme.test for pricing.\n",
    "table.md": "# Table\n\n| Acme | 40 |\n| Beta | 400 |\n",
    "plans.md": (
        "# Plans\n\n## Paused work\n\n### Pricing\n\nThe pilot is $40 per seat.\n\n"
        "## Messaging\n\nOur value proposition is speed.\n\nWe plan to charge $55 per seat.\n"
    ),
}


class Notes(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        _content, self.run = agreed(PAGES)
        settle(self.run)
        planned = join_flow.notes_plan(self.run, today=TODAY)
        self.number = dict((s.label, n) for n, s in enumerate(planned.sources, start=1))
        self.batch = planned.batches[0]
        self.path = join_flow.notes_file(self.run, 1)

    def every_file(self, *extra):
        rows_ = list(extra)
        for number in self.batch.numbers:
            if not any(row.get("source") == number for row in rows_):
                rows_.append(note(number, "", kind="nothing"))
        return rows_

    def check(self, *rows_, raw=None, again=False):
        if not again:
            record = os.path.join(join_flow.scratch_dir(self.run), "notes", "batch-1.json")
            if os.path.exists(record):
                os.remove(record)
        support.write(self.path, raw if raw is not None else fenced_notes(*self.every_file(*rows_)))
        return join_flow.notes_check(self.run, 1, self.path, today=TODAY)


class TestWhatANoteKeeps(Notes):
    def test_the_note_keeps_the_files_own_words_never_the_copy(self):
        """Security S2: a disguised address is matched to the file and screened."""
        checked = self.check(note(self.number["contact.md"], "Contact jane＠acme．test for pricing."))
        self.assertFalse(checked.accepted)
        self.assertTrue(any("screened" in p for p in checked.problems), checked.problems)

    def test_a_quote_across_lines_or_rows_or_holding_markup_is_refused(self):
        """Correctness H3 and M7, security S5."""
        table = self.number["table.md"]
        self.assertIn("note-1:quote-spans-rows", self.check(
            note(table, "40 | Beta", kind="customer", customer="Beta", figure="40")).problems)
        self.assertIn("note-1:markup-in-a-field", self.check(
            note(self.number["about.md"], "We sell one platform", kind="customer",
                 customer="We\n```")).problems)

    def test_a_segment_the_quote_does_not_name_and_no_list_holds_is_refused(self):
        """Security S1: a segment is a settled one, or a name the file's words hold."""
        about = self.number["about.md"]
        bad = note(about, "We sell one platform to lenders and banks.", kind="segment",
                   segment="Enterprise ![x](https://evil.example)")
        self.assertIn("note-1:unknown-segment", self.check(bad).problems)
        good = note(about, "We sell one platform to lenders and banks.", kind="segment", segment="lenders")
        self.assertTrue(self.check(good).accepted)

    def test_a_note_under_a_segments_heading_belongs_to_that_segment(self):
        """Correctness M7: the heading the words sit under names the segment."""
        page = self.number["icp-banks.md"]
        wrong = note(page, "Banks buy after an audit.", kind="segment", segment="Lenders")
        self.assertIn("note-1:segment-not-its-section", self.check(wrong).problems)

    def test_no_fence_or_no_file_records_every_file_as_not_noted(self):
        """Correctness H2."""
        for attempt in range(3):
            last = self.check(raw="no fence here", again=attempt > 0)
        self.assertTrue(last.accepted)
        book = join_flow.notes_for_drafts(self.run, today=TODAY)
        self.assertEqual(sorted(self.batch.numbers), sorted(set(n for n, _c in book.not_noted)))

    def test_lines_that_cannot_be_read_mark_the_batch_as_not_fully_noted(self):
        """Correctness L14."""
        raw = fenced_notes(*self.every_file()) .replace("```jsonl\n", "```jsonl\n{broken\n")
        for attempt in range(3):
            last = self.check(raw=raw, again=attempt > 0)
        self.assertTrue(last.accepted)
        book = join_flow.notes_for_drafts(self.run, today=TODAY)
        self.assertTrue(book.not_noted)


class TestTheStatusFloor(unittest.TestCase):
    """Correctness M8."""

    def test_a_parent_heading_the_sentence_and_only_real_proposals_count(self):
        text = PAGES["plans.md"]
        self.assertEqual(notes.ON_HOLD, notes.floor_status(notes.SETTLED, "The pilot is $40 per seat.", text))
        self.assertEqual(notes.SETTLED, notes.floor_status(notes.SETTLED, "Our value proposition is speed.", text))
        self.assertEqual(notes.PROPOSED, notes.floor_status(notes.SETTLED, "$55 per seat", text))


class Drafting(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        _content, self.run = agreed(
            {"segments/icp-lenders.md": LENDERS, "segments/icp-banks.md": BANKS, "about.md": ABOUT}
        )
        settle(self.run)
        take_notes(self.run, rows)
        self.ids = ids(self.run)
        self.path = join_flow.draft_path(self.run, "positioning")

    def write(self, extra="One platform for both. [n1]"):
        support.write(self.path, POSITIONING.format(
            platform="[%s]" % self.ids["We sell one platform to lenders and banks."],
            lenders="[%s]" % self.ids["Lenders buy when defaults rise."],
            banks="[%s]" % self.ids["Banks buy after an audit."],
            extra=extra.replace("[n1]", "[%s]" % self.ids["We sell one platform to lenders and banks."]),
        ))

    def review(self):
        return join_flow.review_step("positioning", self.path, run_id=self.run)

    def retake(self):
        """The notes taken again with one more valid note first, so ids shift."""
        def more(label, number):
            found = rows(label, number) or []
            if label == "about.md":
                found = [note(number, "We sell one platform to lenders and banks.")] + found
            return found
        take_notes(self.run, more)


class TestTheSupportCheckReadsTheDraftItJudged(Drafting):
    def test_an_answer_for_another_draft_is_not_a_check(self):
        """Correctness H5."""
        self.write()
        made = join_flow.support_assemble("positioning", self.run)
        self.write("Both buy the one platform. [n1]")
        self.assertTrue(self.review().ready)
        support.write(made.answer, support_answer(*(["supported"] * made.lines)))
        checked = join_flow.support_check("positioning", self.run, made.answer)
        self.assertFalse(checked.complete)
        self.assertEqual(citations.CODE_SUPPORT_DRAFT_CHANGED, checked.code)

    def test_notes_taken_again_after_the_check_stop_the_approval(self):
        """Correctness M6, security S3."""
        self.write()
        support.support_checked(self.run, "positioning")
        self.retake()
        with self.assertRaises(join_flow.ReviewError) as caught:
            join_flow.approve_step("positioning", self.path, self.run,
                                   parent=os.path.join(os.environ["HOME"], "bases"), company="Acme",
                                   email="owner@example.com")
        self.assertIn(caught.exception.code, (citations.CODE_SUPPORT_NOT_CHECKED, "screened"))

    def test_a_draft_written_from_an_older_request_is_refused(self):
        """Correctness M6: ids are read against the notes the request held."""
        join_flow.assemble_step("positioning", self.run, "Acme", "o@example.com", today=TODAY)
        self.retake()
        self.write()
        self.assertIn(join_flow.CODE_NOTES_CHANGED, self.review().codes)


class TestTheAttemptCountResets(Drafting):
    def test_a_ready_review_starts_the_count_again(self):
        """Correctness M9."""
        for _ in range(2):
            self.write("Harbor Lending buys more. [n1]")
            self.assertFalse(self.review().ready)
        self.write()
        self.assertTrue(self.review().ready)
        self.write("Harbor Lending buys more. [n1]")
        again = self.review()
        self.assertFalse(again.ready)
        self.assertEqual(0, again.taken_out)


class TestTheExemptionIsForSetupsOwnSectionsOnly(unittest.TestCase):
    def test_a_context_change_cannot_hide_words_under_setups_headings(self):
        """Correctness M12."""
        from test_drafting import captured

        good = captured("change-entry.md")
        drafting.parse(drafting.STEP_CHANGE, good)
        head, fence, tail = good.rpartition("\n```")
        hidden = head + "\n\n## Where this came from\n\nWe will leverage this." + fence + tail
        self.assertNotEqual(good, hidden)
        with self.assertRaises(drafting.DraftError) as caught:
            drafting.parse(drafting.STEP_CHANGE, hidden)
        self.assertIn("leverage", str(caught.exception.code))


class TestPastesComeFromTheRunsOwnFolder(unittest.TestCase):
    def test_a_file_named_as_a_paste_from_anywhere_else_is_refused(self):
        """Security S4."""
        with support.Sandbox():
            run = join_flow.new_run(TODAY)
            elsewhere = os.path.join(os.environ["HOME"], "secret.txt")
            support.write(elsewhere, "not for the base\n")
            with self.assertRaises(Exception) as caught:
                join_flow.read_sources(run, [elsewhere], today=TODAY)
            self.assertEqual("no-paste-file", getattr(caught.exception, "code", None))


class TestFootnotesNameTheFileNotTheHomeFolder(unittest.TestCase):
    def test_a_file_is_named_by_its_folder_and_its_own_name(self):
        """Security S6."""
        source = type("S", (), {"path": os.path.join(os.path.expanduser("~"), "Personal", "job", "pricing.md"),
                                "label": "pricing.md", "date": None})()
        self.assertEqual("job/pricing.md", join_flow._shown_name(1, source))


if __name__ == "__main__":
    unittest.main()
