"""The summarize-first stage: the notes setup takes before anything is drafted.

The fidelity replay of 2026-10-10 failed: drafts dropped customers and
segments that sat past the reading limit, or in files they read and did not
keep. So every file the person agreed to is now read in full, in batches that
each fit one request, and nothing is dropped on the way. These tests build
their material in a temporary home and seat folder, so nothing here reaches
the person's real folders.
"""

import datetime
import json
import os
import subprocess
import sys
import unittest

import support

from gtmbase import constants, join_flow, notes, sources

SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "join")
SHIM = os.path.join(SKILL_DIR, "scripts", "join.py")
TODAY = datetime.date(2026, 10, 11)
SESSION = "s-notes"


class Limit(object):
    """The reading limit, set for the length of one test."""

    def __init__(self, chars):
        self.chars = chars
        self.previous = None

    def __enter__(self):
        self.previous = constants.DRAFT_SOURCES_MAX_CHARS
        constants.DRAFT_SOURCES_MAX_CHARS = self.chars
        return self

    def __exit__(self, kind, value, trace):
        constants.DRAFT_SOURCES_MAX_CHARS = self.previous
        return False


def screened(label, text, path=None):
    return sources.make_source(label, text, "markdown", date=TODAY, path=path)


def page(heading, paragraphs, words=60):
    """A made-up page: a heading, then paragraphs of plain words."""
    body = []
    for number in range(paragraphs):
        body.append("## Part %d\n\n%s\n" % (number + 1, " ".join(["word%d" % number] * words)))
    return "# %s\n\n%s" % (heading, "\n".join(body))


def agreed(files):
    """A folder of made-up files, listed and agreed to as a plain yes would."""
    content = os.path.join(os.environ["HOME"], "company")
    for name, text in files.items():
        support.write(os.path.join(content, name), text)
    run = join_flow.new_run(TODAY)
    join_flow.list_sources(content, run, today=TODAY)
    join_flow.freeze_sources(content, SESSION, run, today=TODAY)
    return content, run


def run_join(*arguments):
    return subprocess.run(
        [sys.executable, SHIM] + [str(item) for item in arguments],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# --- Splitting one file that is longer than one request -----------------------


class TestALongFileIsSplitNeverCut(unittest.TestCase):
    def test_the_parts_join_back_to_the_exact_text(self):
        text = page("Pricing", 40)
        for budget in (500, 1200, 5000):
            parts = notes.split_text(text, budget)
            self.assertEqual(text, "".join(parts), budget)
            self.assertTrue(all(0 < len(part) <= budget for part in parts), budget)

    def test_a_part_ends_before_a_heading_or_at_a_blank_line(self):
        text = page("Pricing", 12)
        parts = notes.split_text(text, 1000)
        self.assertGreater(len(parts), 1)
        for part in parts[1:]:
            self.assertTrue(part.startswith("## ") or part.startswith("\n"), part[:40])

    def test_one_line_longer_than_a_part_is_still_split_and_kept(self):
        text = "x" * 2500
        parts = notes.split_text(text, 1000)
        self.assertEqual(text, "".join(parts))
        self.assertEqual(3, len(parts))

    def test_text_that_fits_is_one_part(self):
        self.assertEqual(["short"], notes.split_text("short", 1000))
        self.assertEqual([""], notes.split_text("", 1000))


# --- Packing every file into batches that each fit one request ----------------


class TestEveryFileIsReadAndNoneIsDropped(unittest.TestCase):
    def check(self, found, limit):
        with Limit(limit):
            batches = notes.pack(found)
        for batch in batches:
            self.assertLessEqual(len(batch.fenced), limit)
        read = {}
        for batch in batches:
            for part in batch.parts:
                read.setdefault(part.number, []).append(part)
        self.assertEqual(sorted(read), list(range(1, len(found) + 1)))
        for number, source in enumerate(found, start=1):
            parts = read[number]
            self.assertEqual([part.index for part in parts], list(range(1, len(parts) + 1)))
            self.assertTrue(all(part.count == len(parts) for part in parts))
            self.assertEqual(source.text, "".join(part.text for part in parts))
        return batches

    def test_at_the_full_limit_and_at_the_replay_limit(self):
        found = [
            screened("notes-%d.md" % number, page("Page %d" % number, 6 + number % 5))
            for number in range(17)
        ]
        found.append(screened("long.md", page("Long", 400)))
        self.check(found, constants.DRAFT_SOURCES_MAX_CHARS)
        batches = self.check(found, 40000)
        self.assertGreater(len(batches), 1)

    def test_a_file_longer_than_one_request_is_split_into_labelled_parts(self):
        found = [screened("analysis.md", page("Analysis", 300))]
        batches = self.check(found, 40000)
        parts = [part for batch in batches for part in batch.parts]
        self.assertGreater(len(parts), 1)
        self.assertEqual("S1 analysis.md part 1 of %d" % len(parts), parts[0].label)

    def test_the_order_of_the_files_is_kept(self):
        found = [screened("f%d.md" % number, page("F", 3)) for number in range(9)]
        batches = self.check(found, 40000)
        numbers = [part.number for batch in batches for part in batch.parts]
        self.assertEqual(sorted(numbers), numbers)

    def test_a_label_too_long_for_a_fence_is_shortened_and_still_numbered(self):
        found = [screened("a" * 80, "text")]
        label = notes.pack(found)[0].parts[0].label
        self.assertTrue(label.startswith("S1 "))
        self.assertLessEqual(len(label), 80)
        sources.fence(notes.pack(found)[0].parts[0].source())

    def test_the_same_material_always_packs_the_same_way(self):
        found = [screened("f%d.md" % number, page("F", 5)) for number in range(6)]
        with Limit(40000):
            first = [batch.digest for batch in notes.pack(found)]
            second = [batch.digest for batch in notes.pack(found)]
        self.assertEqual(first, second)
        changed = list(found)
        changed[2] = screened("f2.md", page("F", 5) + "\nOne more line.\n")
        with Limit(40000):
            third = [batch.digest for batch in notes.pack(changed)]
        self.assertNotEqual(first, third)


# --- The batches of one run, and the request for each ------------------------


class TestTheNotesOfOneRun(unittest.TestCase):
    def test_the_plan_numbers_every_file_on_the_list_and_keeps_one_version(self):
        with support.Sandbox():
            _content, run = agreed(
                {
                    "segments/widgets.md": "# Widgets\n\nAn older version.\n",
                    "segments/widgets.final.md": "# Widgets\n\nThe version signed off.\n",
                    "positioning.md": "# Positioning\n\nWhat we say.\n",
                }
            )
            planned = join_flow.notes_plan(run, today=TODAY)
            labels = [source.label for source in planned.sources]
            self.assertIn("widgets.final.md", labels)
            self.assertNotIn("widgets.md", labels)
            self.assertEqual(2, len(planned.sources))
            self.assertEqual(1, len(planned.batches))
            self.assertEqual(["widgets.md"], [v.older for v in planned.superseded])

    def test_the_request_holds_every_part_of_its_batch_fenced_as_data(self):
        with support.Sandbox():
            _content, run = agreed(
                {"a.md": page("Alpha", 30), "b.md": page("Beta", 30), "c.md": page("Gamma", 30)}
            )
            with Limit(9000):
                planned = join_flow.notes_plan(run, today=TODAY)
                self.assertGreater(len(planned.batches), 1)
                made = join_flow.notes_assemble(run, 1, "Acme", today=TODAY)
            text = support.read(made.prompt)
            self.assertTrue(made.prompt.startswith(join_flow.scratch_dir(run)))
            self.assertTrue(made.notes.startswith(join_flow.drafts_dir(run)))
            self.assertIn(constants.SOURCE_FENCE_SENTENCE, text)
            for part in planned.batches[0].parts:
                self.assertIn(constants.SOURCE_FENCE_HEADER % part.label, text)
            self.assertNotIn("{{", text)
            self.assertIn("Acme", text)

    def test_a_batch_that_is_not_in_the_plan_is_refused(self):
        with support.Sandbox():
            _content, run = agreed({"a.md": "# A\n\nText.\n"})
            with self.assertRaises(notes.NotesRefused) as caught:
                join_flow.notes_assemble(run, 2, "Acme", today=TODAY)
            self.assertEqual(notes.CODE_NO_SUCH_BATCH, caught.exception.code)

    def test_the_settled_segments_go_into_the_request_as_data(self):
        with support.Sandbox():
            content, run = agreed(
                {
                    "segments/icp-lenders.md": "# Ideal customer profile: Lenders\n\nWho.\n",
                    "segments/icp-banks.md": "# Ideal customer profile: Banks\n\nWho.\n",
                }
            )
            candidates = join_flow.segment_candidates(run, today=TODAY)
            lines = "\n".join(
                "draft %d %s" % (c.number, c.label.split("icp-")[1][:-3].title())
                for c in candidates
            )
            join_flow.settle_segments(run, lines + "\n")
            made = join_flow.notes_assemble(run, 1, "Acme", today=TODAY)
            text = support.read(made.prompt)
            self.assertIn("[[source: the segments]]", text)
            self.assertIn("Lenders", text)
            self.assertIn("Banks", text)


class TestThroughTheScript(unittest.TestCase):
    def test_notes_plan_and_notes_assemble(self):
        with support.Sandbox():
            _content, run = agreed({"a.md": "# A\n\nText.\n", "b.md": "# B\n\nMore.\n"})
            planned = run_join("notes-plan", "--run", run)
            self.assertEqual(0, planned.returncode, planned.stderr)
            said = planned.stdout.decode("utf-8")
            self.assertIn("batches=1", said)
            self.assertIn("files=2", said)
            made = run_join("notes-assemble", "--run", run, "--batch", "1", "--company", "Acme")
            self.assertEqual(0, made.returncode, made.stderr)
            said = made.stdout.decode("utf-8")
            self.assertIn("prompt=", said)
            self.assertIn("notes=", said)


class TestTheNotesPrompt(unittest.TestCase):
    def test_every_placeholder_the_library_fills_is_in_the_prompt(self):
        text = support.read(
            os.path.join(SKILL_DIR, "references", "prompts", "notes.md")
        )
        for field in ("company", "sources", "segments", "batch"):
            self.assertIn("{{%s}}" % field, text)
        self.assertIn(constants.SOURCE_FENCE_SENTENCE, text)


if __name__ == "__main__":
    unittest.main()


# --- Checking the notes the assistant wrote (U2) ------------------------------


def fenced_notes(*rows):
    return "```jsonl\n" + "\n".join(json.dumps(row) for row in rows) + "\n```\n"


def note(source, quote, kind="fact", segment="", customer="", figure="", status="settled"):
    return {
        "source": source,
        "kind": kind,
        "segment": segment,
        "customer": customer,
        "figure": figure,
        "status": status,
        "quote": quote,
    }


PRICING = """# Pricing

## What we charge

We charge “per seat” at $40 a month, and Acme Bank pays it for **all 300 seats**.

| Plan | Price |
|------|-------|
| Team | $40 a month |

## Insurance analysis, on hold

Claims fall 12% for drivers who use the app.

## Open questions

Resale terms are to be clarified by the data owners.
The partner channel proposes a 20% referral fee.
"""

SEGMENTS = """# Who we sell to

Regional banks buy first. Northwind Credit Union tried it and dropped it.
"""


class Checked(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        _content, self.run = agreed({"pricing.md": PRICING, "segments.md": SEGMENTS})
        planned = join_flow.notes_plan(self.run, today=TODAY)
        self.numbers = {source.label: number for number, source in enumerate(planned.sources, start=1)}
        self.pricing = self.numbers["pricing.md"]
        self.segments = self.numbers["segments.md"]
        self.path = join_flow.notes_file(self.run, 1)

    def write(self, *rows, raw=None):
        support.write(self.path, raw if raw is not None else fenced_notes(*rows))

    def check(self, *rows, raw=None, again=False):
        """Check one batch; a fresh first attempt unless `again` is said."""
        if not again:
            record = os.path.join(join_flow.scratch_dir(self.run), "notes", "batch-1.json")
            if os.path.exists(record):
                os.remove(record)
        self.write(*rows, raw=raw)
        return join_flow.notes_check(self.run, 1, self.path, today=TODAY)

    def good(self):
        return [
            note(self.pricing, 'We charge "per seat" at $40 a month, and Acme Bank pays it for all 300 seats.',
                 kind="customer", segment="Regional banks", customer="Acme Bank", figure="$40"),
            note(self.pricing, "| Team | $40 a month |", figure="$40"),
            note(self.segments, "Regional banks buy first.", kind="segment", segment="Regional banks"),
        ]


class TestNotesThatHoldUp(Checked):
    def test_words_copied_from_the_file_are_accepted_and_numbered(self):
        checked = self.check(*self.good())
        self.assertTrue(checked.accepted, checked.problems)
        self.assertEqual([], checked.problems)
        book = join_flow.notes_for_drafts(self.run, today=TODAY)
        self.assertEqual(["n1", "n2", "n3"], [item.id for item in book.notes])
        self.assertEqual("Acme Bank", book.notes[0].customer)

    def test_spacing_quote_marks_emphasis_and_table_marks_are_evened_out(self):
        rows = [
            note(self.pricing, "We charge “per seat” at $40 a month,\nand Acme Bank pays it for all 300 seats."),
            note(self.pricing, "Team $40 a month"),
        ]
        checked = self.check(*rows, note(self.segments, "", kind="nothing"))
        self.assertTrue(checked.accepted, checked.problems)

    def test_a_file_with_nothing_to_note_says_so_in_one_line(self):
        checked = self.check(self.good()[0], note(self.segments, "", kind="nothing"))
        self.assertTrue(checked.accepted, checked.problems)


class TestNotesThatAreRefused(Checked):
    def refused(self, rows, code):
        checked = self.check(*rows)
        self.assertFalse(checked.accepted)
        self.assertIn(code, checked.problems)
        self.assertEqual([], [p for p in checked.problems if "Acme" in p or "$" in p])
        return checked

    def test_words_that_are_not_in_the_file(self):
        rows = self.good() + [note(self.pricing, "We charge per seat, and every bank pays it.")]
        self.refused(rows, "note-4:quote-not-in-file")

    def test_a_customer_or_a_figure_outside_its_own_words(self):
        rows = self.good()
        rows[2] = note(self.segments, "Regional banks buy first.", kind="customer",
                       segment="Regional banks", customer="Northwind Credit Union")
        self.refused(rows, "note-3:customer-not-in-quote")
        rows = self.good()
        rows[1]["figure"] = "$45"
        self.refused(rows, "note-2:figure-not-in-quote")

    def test_a_file_left_without_a_note(self):
        self.refused(self.good()[:2], "file-not-noted:S%d" % self.segments)

    def test_a_file_this_batch_does_not_read(self):
        rows = self.good() + [note(9, "Regional banks buy first.")]
        self.refused(rows, "note-4:not-in-this-batch")

    def test_words_too_long_contact_details_and_broken_lines(self):
        long_quote = "word " * 70
        rows = self.good() + [note(self.pricing, long_quote.strip())]
        self.refused(rows, "note-4:quote-too-long")
        rows = self.good()
        rows[0]["quote"] = "Write to sales@example.com today."
        checked = self.check(*rows)
        self.assertFalse(checked.accepted)
        self.assertTrue(any(p.startswith("note-1:") for p in checked.problems), checked.problems)
        checked = self.check(raw="```jsonl\n{not json}\n```\n")
        self.assertIn("note-1:not-a-note", checked.problems)
        rows = self.good()
        rows[1]["kind"] = "opinion"
        self.refused(rows, "note-2:unknown-kind")
        rows = self.good()
        rows[1]["status"] = "maybe"
        self.refused(rows, "note-2:unknown-status")

    def test_notes_written_without_their_fence(self):
        checked = self.check(raw=json.dumps(self.good()[0]) + "\n")
        self.assertFalse(checked.accepted)
        self.assertEqual(["no-fence"], checked.problems)


class TestTheStatusIsNeverStrongerThanTheMaterial(Checked):
    def statuses(self, rows):
        checked = self.check(*rows, note(self.segments, "", kind="nothing"))
        self.assertTrue(checked.accepted, checked.problems)
        return [item.status for item in join_flow.notes_for_drafts(self.run, today=TODAY).notes]

    def test_a_heading_that_says_on_hold_holds_every_note_under_it(self):
        found = self.statuses([note(self.pricing, "Claims fall 12% for drivers who use the app.", figure="12%")])
        self.assertEqual(["on-hold"], found)

    def test_words_that_propose_or_leave_open_lower_a_settled_note(self):
        found = self.statuses([
            note(self.pricing, "The partner channel proposes a 20% referral fee.", figure="20%"),
            note(self.pricing, "Resale terms are to be clarified by the data owners."),
        ])
        self.assertEqual(["open", "open"], found)

    def test_a_note_is_never_raised_above_what_the_assistant_said(self):
        found = self.statuses([note(self.pricing, "| Team | $40 a month |", status="open")])
        self.assertEqual(["open"], found)

    def test_a_proposal_outside_an_open_section_is_proposed(self):
        with support.Sandbox():
            _content, run = agreed({"plan.md": "# Plan\n\nWe propose airport pickups for fleets.\n"})
            path = join_flow.notes_file(run, 1)
            support.write(path, fenced_notes(note(1, "We propose airport pickups for fleets.")))
            self.assertTrue(join_flow.notes_check(run, 1, path, today=TODAY).accepted)
            book = join_flow.notes_for_drafts(run, today=TODAY)
            self.assertEqual(["proposed"], [item.status for item in book.notes])


class TestAttemptsResumeAndAChangedList(Checked):
    def test_the_third_refusal_keeps_what_held_up_and_records_the_rest(self):
        rows = self.good() + [note(self.pricing, "Words nobody wrote.")]
        self.assertFalse(self.check(*rows).accepted)
        self.assertFalse(self.check(*rows, again=True).accepted)
        third = self.check(*rows, again=True)
        self.assertTrue(third.accepted)
        self.assertEqual(["note-4:quote-not-in-file"], third.dropped)
        book = join_flow.notes_for_drafts(self.run, today=TODAY)
        self.assertEqual(3, len(book.notes))
        self.assertEqual([(self.pricing, "quote-not-in-file")], book.not_noted)

    def test_a_file_never_noted_after_three_tries_is_recorded_as_not_read(self):
        rows = self.good()[:2]
        for attempt in range(3):
            last = self.check(*rows, again=attempt > 0)
        self.assertTrue(last.accepted)
        book = join_flow.notes_for_drafts(self.run, today=TODAY)
        self.assertIn((self.segments, "file-not-noted"), book.not_noted)

    def test_drafts_wait_until_every_batch_is_noted(self):
        with Limit(700):
            planned = join_flow.notes_plan(self.run, today=TODAY)
            self.assertGreater(len(planned.batches), 1)
            status = join_flow.notes_status(self.run, today=TODAY)
            self.assertEqual(["waiting"] * len(planned.batches), [state for _n, state in status])
            with self.assertRaises(notes.NotesRefused) as caught:
                join_flow.notes_for_drafts(self.run, today=TODAY)
            self.assertEqual(notes.CODE_NOTES_WAITING, caught.exception.code)

    def test_notes_taken_before_the_list_changed_no_longer_count(self):
        self.assertTrue(self.check(*self.good()).accepted)
        self.assertEqual([(1, "done")], join_flow.notes_status(self.run, today=TODAY))
        support.write(
            os.path.join(os.environ["HOME"], "company", "pricing.md"),
            PRICING + "\nA line added after the notes.\n",
        )
        self.assertEqual([(1, "waiting")], join_flow.notes_status(self.run, today=TODAY))

    def test_only_the_file_setup_named_is_read(self):
        other = os.path.join(join_flow.drafts_dir(self.run), "elsewhere.md")
        support.write(other, fenced_notes(*self.good()))
        with self.assertRaises(notes.NotesRefused) as caught:
            join_flow.notes_check(self.run, 1, other, today=TODAY)
        self.assertEqual(notes.CODE_NOT_THE_NOTES_FILE, caught.exception.code)


class TestCheckingThroughTheScript(Checked):
    def test_notes_check_and_notes_status(self):
        self.write(*self.good())
        ran = run_join("notes-check", "--run", self.run, "--batch", "1", "--notes", self.path)
        self.assertEqual(0, ran.returncode, ran.stderr)
        said = ran.stdout.decode("utf-8")
        self.assertIn("accepted=yes", said)
        self.assertIn("notes=3", said)
        ran = run_join("notes-status", "--run", self.run)
        said = ran.stdout.decode("utf-8")
        self.assertIn("batch=1 done", said)
        self.assertIn("waiting=0", said)
