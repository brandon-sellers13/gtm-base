"""Every line a draft writes says which notes it rests on (summarize-first, U4).

The fidelity replay of 2026-10-10 failed on claims nobody could trace to a
file, on a customer credited with what another customer bought, and on open
figures and terms written as settled. These tests hold the checks review now
runs on every draft written from the notes. Material is made up and lives in
a temporary home folder.
"""

import os
import unittest

import support
from test_notes import (
    TODAY,
    agreed,
    note,
    settle,
    take_notes,
    LENDERS,
    BANKS,
)

from gtmbase import citations, join_flow, notes

ABOUT = """# About us

We sell one platform to lenders and banks.

## Pricing, on hold

The pilot price is 40% below list.
"""


def rows(label, number):
    return {
        "icp-lenders.md": [
            note(number, "Lenders buy when defaults rise.", kind="segment", segment="Lenders"),
            note(number, "Harbor Lending signed for a year.", kind="customer",
                 segment="Lenders", customer="Harbor Lending"),
        ],
        "icp-banks.md": [
            note(number, "Banks buy after an audit.", kind="segment", segment="Banks"),
        ],
        "about.md": [
            note(number, "We sell one platform to lenders and banks."),
            note(number, "The pilot price is 40% below list.", figure="40%"),
        ],
    }.get(label)


def ids(run):
    """The note ids of a run, by their words, so a test cites the right one."""
    book = join_flow.notes_for_drafts(run, today=TODAY)
    return dict((item.quote, item.id) for item in book.notes)


POSITIONING = """```markdown
---
kind: positioning
owner: owner@example.com
last_confirmed: 2026-10-11
sources: []
status: draft
---

# Positioning

## What we sell

We sell one platform to lenders and banks. {platform}

## Who it is for

Lenders buy when defaults rise. {lenders}

- Banks buy after an audit. {banks}

## What makes it different

{extra}

## Their own words

Nothing in the material covers this.
```
"""


class Run(unittest.TestCase):
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

    def cite(self, quote):
        return "[%s]" % self.ids[quote]

    def draft(self, extra, **changes):
        values = {
            "platform": self.cite("We sell one platform to lenders and banks."),
            "lenders": self.cite("Lenders buy when defaults rise."),
            "banks": self.cite("Banks buy after an audit."),
            "extra": extra,
        }
        values.update(changes)
        support.write(self.path, POSITIONING.format(**values))
        return join_flow.review_step("positioning", self.path, run_id=self.run)


class TestADraftThatCitesItsNotes(Run):
    def test_every_paragraph_and_item_citing_its_notes_is_ready(self):
        reviewed = self.draft("One platform for both. %s" % self.cite("We sell one platform to lenders and banks."))
        self.assertTrue(reviewed.ready, reviewed.codes)

    def test_the_sentence_for_a_part_the_material_does_not_cover_cites_nothing(self):
        reviewed = self.draft(citations.NOT_COVERED)
        self.assertTrue(reviewed.ready, reviewed.codes)


class TestWhatIsRefused(Run):
    def test_a_paragraph_with_no_citation(self):
        reviewed = self.draft("One platform for both, and nobody else has one.")
        self.assertFalse(reviewed.ready)
        self.assertIn("uncited:section-4-paragraph-1", reviewed.codes)

    def test_an_item_with_no_citation(self):
        reviewed = self.draft(citations.NOT_COVERED, banks="")
        self.assertIn("uncited:section-3-item-1", reviewed.codes)

    def test_a_note_the_draft_never_read(self):
        reviewed = self.draft("One platform for both. [n99]")
        self.assertIn("cites-a-note-it-did-not-read:section-4-paragraph-1", reviewed.codes)

    def test_a_figure_its_notes_do_not_hold(self):
        reviewed = self.draft("Pilots run 12 weeks. %s" % self.cite("We sell one platform to lenders and banks."))
        self.assertIn("figure-not-in-its-notes:section-4-paragraph-1", reviewed.codes)

    def test_a_customer_named_in_the_drafts_own_sentences(self):
        # The replay's case one: a customer credited with what another bought.
        reviewed = self.draft(
            "Harbor Lending buys record level data. %s" % self.cite("Harbor Lending signed for a year.")
        )
        self.assertIn("customer-named:section-4-paragraph-1", reviewed.codes)
        self.assertEqual([], [code for code in reviewed.codes if "Harbor" in code])

    def test_an_open_figure_written_as_settled(self):
        # The replay's case two: figures the material holds on hold, as findings.
        quote = "The pilot price is 40% below list."
        reviewed = self.draft("Pilots cost 40% less. " + self.cite(quote))
        self.assertIn("open-stated-as-settled:section-4-paragraph-1", reviewed.codes)
        asked = self.draft("[your call: is the pilot price of 40% below list settled?] " + self.cite(quote))
        self.assertTrue(asked.ready, asked.codes)

    def test_the_umbrella_and_segments_need_the_run_and_so_do_these(self):
        support.write(self.path, POSITIONING.format(platform="", lenders="", banks="", extra=""))
        with self.assertRaises(join_flow.ReviewError):
            join_flow.review_step("positioning", self.path)


class TestTheThirdRefusal(Run):
    def test_the_failing_lines_become_one_question_each_and_the_rest_stands(self):
        for attempt in range(2):
            reviewed = self.draft("Harbor Lending buys more. [n1]")
            self.assertFalse(reviewed.ready)
            self.assertEqual(0, reviewed.taken_out)
        third = self.draft("Harbor Lending buys more. [n1]")
        self.assertTrue(third.ready, third.codes)
        self.assertEqual(1, third.taken_out)
        self.assertEqual(1, third.questions)
        written = support.read(self.path)
        self.assertIn(citations.TAKEN_OUT, written)
        self.assertNotIn("Harbor Lending buys more", written)
        self.assertIn("Lenders buy when defaults rise.", written)


class TestTheBlocksOfABody(unittest.TestCase):
    def test_paragraphs_items_and_rows_are_each_one_block(self):
        body = (
            "# Title\n\nFirst paragraph\nstill the first.\n\n- one\n  carried on\n- two\n\n"
            "| a | b |\n|---|---|\n| c | d |\n\n## Evidence by segment\n\nSetup's own words.\n"
        )
        found = citations.blocks(body)
        # The table's header row names columns and is not a block (the
        # correctness review of the summarize-first build, L13).
        self.assertEqual(
            ["paragraph", "item", "item", "row"], [block.kind for block in found]
        )
        self.assertEqual("First paragraph\nstill the first.", found[0].text)
        self.assertEqual("- one\n  carried on", found[1].text)

    def test_citations_are_read_in_both_forms(self):
        self.assertEqual(["n3", "n7", "n1"], citations.cited("x [n3, n7] y [n1] [n3]"))


if __name__ == "__main__":
    unittest.main()


# --- The support check (U5) ---------------------------------------------------

import json  # noqa: E402

from gtmbase import approval  # noqa: E402


def support_answer(*verdicts):
    return "```jsonl\n" + "\n".join(
        json.dumps({"line": "B%d" % number, "verdict": verdict})
        for number, verdict in enumerate(verdicts, start=1)
    ) + "\n```\n"


class TestTheSupportCheck(Run):
    def ready_draft(self):
        reviewed = self.draft(
            "One platform for both, and the best on the market. %s"
            % self.cite("We sell one platform to lenders and banks.")
        )
        self.assertTrue(reviewed.ready, reviewed.codes)

    def test_each_line_is_shown_beside_its_notes_and_the_notes_near_it(self):
        self.ready_draft()
        made = join_flow.support_assemble("positioning", self.run)
        text = support.read(made.prompt)
        self.assertEqual(4, made.lines)
        self.assertIn("[[source: the draft and its notes]]", text)
        self.assertIn("B4", text)
        self.assertIn('"Lenders buy when defaults rise."', text)
        self.assertIn("Other notes about the same segment:", text)
        self.assertIn('"Harbor Lending signed for a year."', text)
        self.assertNotIn("{{", text)

    def test_a_line_found_beyond_its_notes_becomes_a_question(self):
        self.ready_draft()
        made = join_flow.support_assemble("positioning", self.run)
        support.write(made.answer, support_answer("supported", "supported", "supported", "beyond"))
        checked = join_flow.support_check("positioning", self.run, made.answer)
        self.assertTrue(checked.complete)
        self.assertEqual(1, checked.taken_out)
        written = support.read(self.path)
        self.assertIn(citations.BEYOND_TAKEN_OUT, written)
        self.assertNotIn("best on the market", written)
        reviewed = join_flow.review_step("positioning", self.path, run_id=self.run)
        self.assertTrue(reviewed.ready, reviewed.codes)
        self.assertEqual(1, reviewed.questions)

    def test_an_answer_that_misses_a_line_is_not_a_check(self):
        self.ready_draft()
        made = join_flow.support_assemble("positioning", self.run)
        support.write(made.answer, support_answer("supported", "supported", "supported"))
        checked = join_flow.support_check("positioning", self.run, made.answer)
        self.assertFalse(checked.complete)
        self.assertEqual(citations.CODE_SUPPORT_INCOMPLETE, checked.code)

    def test_a_draft_nobody_checked_or_changed_since_is_not_written(self):
        self.ready_draft()
        with self.assertRaises(join_flow.ReviewError) as caught:
            join_flow.approve_step("positioning", self.path, self.run, parent=os.environ["HOME"], company="Acme")
        self.assertEqual(citations.CODE_SUPPORT_NOT_CHECKED, caught.exception.code)
        made = join_flow.support_assemble("positioning", self.run)
        support.write(made.answer, support_answer(*(["supported"] * 4)))
        self.assertTrue(join_flow.support_check("positioning", self.run, made.answer).complete)
        # The draft changed after it was checked, so the check no longer counts.
        support.write(self.path, support.read(self.path).replace("best on the market", "best around"))
        with self.assertRaises(join_flow.ReviewError) as caught:
            join_flow.approve_step("positioning", self.path, self.run, parent=os.environ["HOME"], company="Acme")
        self.assertEqual(citations.CODE_SUPPORT_NOT_CHECKED, caught.exception.code)

    def test_only_the_answer_file_setup_named_is_read(self):
        self.ready_draft()
        join_flow.support_assemble("positioning", self.run)
        other = os.path.join(join_flow.drafts_dir(self.run), "other.md")
        support.write(other, support_answer(*(["supported"] * 4)))
        checked = join_flow.support_check("positioning", self.run, other)
        self.assertFalse(checked.complete)


# --- What setup writes into the document (U6) ---------------------------------

from gtmbase import base_reader, formats  # noqa: E402


class TestTheDocumentSetupWrites(Run):
    def approved(self):
        reviewed = self.draft("One platform for both. %s" % self.cite("We sell one platform to lenders and banks."))
        self.assertTrue(reviewed.ready, reviewed.codes)
        made = join_flow.support_assemble("positioning", self.run)
        support.write(made.answer, support_answer(*(["supported"] * made.lines)))
        checked = join_flow.support_check("positioning", self.run, made.answer)
        self.assertTrue(checked.complete)
        parent = os.path.join(os.environ["HOME"], "bases")
        os.makedirs(parent, exist_ok=True)
        result = join_flow.approve_step(
            "positioning", self.path, self.run, parent=parent, company="Acme",
            email="owner@example.com",
        )
        self.root = result.root
        written = support.read(os.path.join(result.root, "context", "positioning.md"))
        return checked, written

    def test_every_citation_is_a_footnote_with_its_file_date_and_words(self):
        _checked, written = self.approved()
        self.assertNotRegex(written, r"\[n\d+\]")
        lenders = self.ids["Lenders buy when defaults rise."]
        self.assertIn("[^%s]" % lenders, written)
        self.assertRegex(
            written,
            r'\[\^%s\]: segments/icp-lenders\.md \(\d{4}-\d{2}-\d{2}\), "Lenders buy when defaults rise\."' % lenders,
        )

    def test_every_customer_sits_under_its_segment_beside_its_own_words(self):
        _checked, written = self.approved()
        evidence = written.split("## Evidence by segment")[1].split("## Still open")[0]
        lenders = evidence.split("**Lenders**")[1].split("**")[0]
        self.assertIn('- Harbor Lending: "Harbor Lending signed for a year."', lenders)
        self.assertNotIn("###", evidence)
        banks = evidence.split("**Banks**")[1]
        self.assertIn(citations.NO_EVIDENCE, banks)

    def test_every_note_the_material_has_not_settled_is_listed_as_open(self):
        _checked, written = self.approved()
        still = written.split("## Still open in the material")[1].split("## Where this came from")[0]
        self.assertIn('"The pilot price is 40% below list." (on hold)', still)

    def test_the_sources_line_is_the_files_cited_never_the_drafts_own(self):
        _checked, written = self.approved()
        fields = formats.parse_frontmatter(formats.split_document(written)[0])
        names = [entry.split(" (")[0] for entry in fields["sources"]]
        self.assertEqual(
            ["company/about.md", "segments/icp-lenders.md", "segments/icp-banks.md"],
            names,
        )

    def test_the_copy_shown_is_the_document_written(self):
        checked, written = self.approved()
        self.assertEqual(support.read(checked.shown), written)

    def test_a_draft_that_writes_one_of_setups_sections_is_refused(self):
        reviewed = self.draft(
            "One platform. %s\n\n## Evidence by segment\n\n- Granite Bank renewed."
            % self.cite("We sell one platform to lenders and banks.")
        )
        self.assertFalse(reviewed.ready)
        self.assertTrue(any(code.startswith("writes-a-section-setup-writes") for code in reviewed.codes))

    def test_the_materials_own_words_in_setups_sections_pass_the_word_checks(self):
        from gtmbase import drafting

        text = (
            "```markdown\n---\nkind: icp\nowner: o@example.com\nlast_confirmed: 2026-10-11\n"
            "sources: [segments/a.md (2026-10-11)]\nstatus: draft\n---\n\n# Ideal customer profile\n\n"
            "## Who we sell to\n\nBanks. [^n1]\n\n## Segments\n\n### Banks\n\nBanks buy.\n\n"
            "## What they share\n\nAudits.\n\n## Evidence by segment\n\n**Banks**\n\n"
            '- Acme: "a seamless — todo list" [^n1]\n\n## Where this came from\n\n'
            '[^n1]: segments/a.md (2026-10-11), "a seamless — todo list"\n```\n'
        )
        drafting.parse("umbrella", text)

    def test_the_base_reads_the_written_document(self):
        self.approved()
        files = base_reader.context_files(self.root)
        found = [info for info in files if str(getattr(info, "path", "")).endswith("positioning.md")]
        self.assertEqual(1, len(found), files)
        self.assertRegex(base_reader.newest_date_in(
            formats.parse_frontmatter(formats.split_document(
                support.read(os.path.join(self.root, "context", "positioning.md")))[0])["sources"]),
            r"^\d{4}-\d{2}-\d{2}$")


def drafting_text(shown):
    """A shown copy as the document inside its fence."""
    from gtmbase import drafting

    return drafting.strip_fence("positioning", shown)
