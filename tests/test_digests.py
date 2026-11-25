"""Digests of the notes, for a draft whose notes do not fit one request.

The case three rehearsal of 2026-11-24 found the notes about as large as the
files they come from, so a draft whose notes did not fit one request lost
whole segments from the end of the list. These tests hold the digest to its
plan: the fewest groups condensed, largest first; every customer and segment
note still read; every note the material leaves open carried; and every
digest line checked against the notes it cites. Every company, customer,
figure and sentence here is invented.
"""

import datetime
import json
import os
import subprocess
import sys
import unittest

import support

from gtmbase import constants, digests, join_flow, notes

FENCE = lambda text: "<<notes>>\n" + text + "\n<<end>>"  # noqa: E731


def note(number, kind="fact", segment="", customer="", figure="", status="settled", quote=None, source=1):
    quote = quote or ("Plain words for note %d about the widget trade." % number)
    return notes.Note(
        {
            "source": source,
            "kind": kind,
            "segment": segment,
            "customer": customer,
            "figure": figure,
            "status": status,
            "quote": quote,
        },
        id="n%d" % number,
    )


def many(start, count, segment, kind="fact", status="settled"):
    return [note(start + i, kind=kind, segment=segment, status=status) for i in range(count)]


def answer(*rows):
    return "```jsonl\n" + "\n".join(json.dumps(row) for row in rows) + "\n```\n"


def no_screen(_text):
    return []


def a_book():
    """Three segments of very different sizes, and the whole company."""
    found = []
    found += many(1, 4, "")                                    # company-wide
    found += many(10, 40, "Harbour fleets")                    # large
    found.append(note(60, kind="customer", segment="Harbour fleets", customer="Gullwing Ferries",
                      quote="Gullwing Ferries bought the harbour feed in spring."))
    found.append(note(61, kind="segment", segment="Harbour fleets",
                      quote="Harbour fleets are the first market."))
    found.append(note(62, segment="Harbour fleets", status="open",
                      quote="Whether harbour fleets pay per berth is to be confirmed."))
    found += many(70, 12, "Inland depots")                     # middle
    found.append(note(90, kind="customer", segment="Inland depots", customer="Corran Haulage",
                      quote="Corran Haulage tried the depot view and stopped."))
    found += many(100, 3, "Airfields")                         # small
    return found


ORDER = ["Harbour fleets", "Inland depots", "Airfields"]


class TestThePlan(unittest.TestCase):
    def test_nothing_is_condensed_when_every_note_fits(self):
        planned = digests.plan(a_book(), ORDER, FENCE, 10 ** 6)
        self.assertEqual([], planned.groups)
        self.assertEqual([], planned.batches)

    def test_the_largest_group_is_condensed_first_and_no_more_than_needed(self):
        found = a_book()
        whole = len(FENCE("\n\n".join(
            digests._raw_block(n, m) for n, m in notes.group_notes(found, ORDER))))
        planned = digests.plan(found, ORDER, FENCE, int(whole * 0.7))
        self.assertEqual(["Harbour fleets"], planned.groups)
        self.assertEqual({"Harbour fleets"}, set(b.group for b in planned.batches))

    def test_a_tighter_limit_condenses_more_groups_in_order_of_size(self):
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 2500)
        self.assertEqual("Harbour fleets", planned.groups[0])
        self.assertIn("Inland depots", planned.groups)

    def test_only_facts_go_to_a_digest_and_open_ones_must_be_carried(self):
        planned = digests.plan(a_book(), ORDER, FENCE, 4000)
        harbour = [b for b in planned.batches if b.group == "Harbour fleets"]
        ids = [i for b in harbour for i in b.ids]
        self.assertNotIn("n60", ids)   # the customer note
        self.assertNotIn("n61", ids)   # the segment note
        self.assertIn("n62", ids)
        self.assertIn("n62", [i for b in harbour for i in b.must_carry])

    def test_a_group_too_large_for_one_request_is_split_and_nothing_is_lost(self):
        found = many(1, 200, "Harbour fleets")
        planned = digests.plan(found, ORDER, FENCE, 6000)
        self.assertGreater(len(planned.batches), 1)
        ids = [i for b in planned.batches for i in b.ids]
        self.assertEqual(sorted(item.id for item in found), sorted(ids))
        for batch in planned.batches:
            text = "\n".join(digests._fact_line(item) for item in batch.notes)
            self.assertLessEqual(len(FENCE(text)), 6000)

    def test_the_same_notes_always_plan_the_same_way_and_a_change_shows(self):
        first = digests.plan(a_book(), ORDER, FENCE, 3000)
        again = digests.plan(a_book(), ORDER, FENCE, 3000)
        self.assertEqual(first.digest, again.digest)
        changed = a_book()
        changed[20].quote = "Different words entirely for this note."
        self.assertNotEqual(first.digest, digests.plan(changed, ORDER, FENCE, 3000).digest)

    def test_a_batch_that_is_not_in_the_plan_is_refused(self):
        planned = digests.plan(a_book(), ORDER, FENCE, 3000)
        with self.assertRaises(digests.DigestRefused) as caught:
            planned.batch(99)
        self.assertEqual(digests.CODE_NO_SUCH_DIGEST, caught.exception.code)


class TestTheCheck(unittest.TestCase):
    def setUp(self):
        self.batch = digests.DigestBatch(1, "Harbour fleets", [
            note(1, segment="Harbour fleets", figure="40%", quote="Harbour fleets renew at 40% a year."),
            note(2, segment="Harbour fleets", status="open",
                 quote="Whether berths are priced singly is to be confirmed."),
            note(3, segment="Harbour fleets", quote="Gullwing Ferries wants the night feed."),
        ], 5000)
        self.customers = ["Gullwing Ferries", "Corran Haulage"]

    def check(self, *rows, raw=None, screen=no_screen):
        return digests.check(raw if raw is not None else answer(*rows), self.batch, screen, self.customers)

    def test_lines_that_rest_on_their_notes_are_kept(self):
        got = self.check(
            {"line": "Renewals run at 40% a year.", "notes": ["n1"], "status": "settled"},
            {"line": "Per-berth pricing is not settled.", "notes": ["n2"], "status": "open"},
        )
        self.assertEqual([], got.problems)
        self.assertEqual(2, len(got.rows))

    def test_a_note_the_material_leaves_open_must_be_carried(self):
        got = self.check({"line": "Renewals run at 40% a year.", "notes": ["n1"], "status": "settled"})
        self.assertIn("open-note-not-carried:n2", got.problems)
        self.assertEqual(["n2"], got.uncarried)

    def test_a_line_firmer_than_its_notes_is_refused(self):
        got = self.check(
            {"line": "Berths are priced singly.", "notes": ["n2"], "status": "settled"},
        )
        self.assertIn("line-1:firmer-than-its-notes", got.problems)

    def test_a_line_joining_notes_takes_the_weakest_status(self):
        got = self.check(
            {"line": "Renewals and berth pricing.", "notes": ["n1", "n2"], "status": "settled"},
        )
        self.assertIn("line-1:firmer-than-its-notes", got.problems)

    def test_a_figure_not_in_its_notes_is_refused(self):
        got = self.check(
            {"line": "Renewals run at 45% a year.", "notes": ["n1"], "status": "settled"},
            {"line": "Per-berth pricing is open.", "notes": ["n2"], "status": "open"},
        )
        self.assertIn("line-1:figure-not-in-its-notes", got.problems)

    def test_a_customer_not_in_its_notes_is_refused(self):
        got = self.check(
            {"line": "Corran Haulage renews at 40% a year.", "notes": ["n1"], "status": "settled"},
            {"line": "Gullwing Ferries wants the night feed.", "notes": ["n3"], "status": "settled"},
            {"line": "Per-berth pricing is open.", "notes": ["n2"], "status": "open"},
        )
        self.assertEqual(["line-1:customer-not-in-its-notes"], got.problems)

    def test_a_note_from_another_digest_is_refused(self):
        got = self.check({"line": "Something.", "notes": ["n9"], "status": "settled"})
        self.assertIn("line-1:cites-a-note-not-in-this-digest", got.problems)

    def test_markup_length_contact_details_and_unreadable_lines(self):
        got = self.check(
            {"line": "A line with [n1] inside.", "notes": ["n1"], "status": "settled"},
            {"line": "x" * 301, "notes": ["n1"], "status": "settled"},
            {"line": "Write to sales.", "notes": ["n1"], "status": "settled"},
            raw=None,
            screen=lambda text: ["email"] if "Write to" in text else [],
        )
        self.assertIn("line-1:markup-in-a-line", got.problems)
        self.assertIn("line-2:line-too-long", got.problems)
        self.assertIn("line-3:screened-email", got.problems)
        broken = self.check(raw="```jsonl\nnot json\n```\n")
        self.assertIn("line-1:not-a-line", broken.problems)
        self.assertEqual([notes.CODE_NO_FENCE], self.check(raw="no fence").problems)

    def test_a_digest_over_its_room_is_refused(self):
        self.batch.room = 30
        got = self.check(
            {"line": "Renewals run at 40% a year.", "notes": ["n1"], "status": "settled"},
            {"line": "Per-berth pricing is not settled.", "notes": ["n2"], "status": "open"},
        )
        self.assertIn("over-its-room", got.problems)

    def test_the_room_counts_the_words_the_request_asks_for(self):
        # The second rehearsal of 2026-11-24: digests whose words fitted the
        # room the request gave were refused because the check counted each
        # line with its note numbers and status as well.
        line = "x" * 80
        rows = [{"line": line, "notes": ["n1", "n2", "n3"], "status": "open"}] * 2
        self.batch.room = 2 * len(line)
        got = self.check(*rows)
        self.assertNotIn("over-its-room", got.problems)
        self.batch.room = 2 * len(line) - 1
        self.assertIn("over-its-room", self.check(*rows).problems)

    def test_after_the_last_try_setup_carries_every_open_note_in_its_own_words(self):
        rows = digests.carried_by_setup(self.batch, ["n2"])
        self.assertEqual(1, len(rows))
        self.assertEqual(["n2"], rows[0]["notes"])
        self.assertEqual("open", rows[0]["status"])
        self.assertIn("to be confirmed", rows[0]["line"])


class TestWhatADraftReads(unittest.TestCase):
    def lines(self, planned, found):
        """A digest for each planned batch: one line per open note, one for the rest."""
        by_group = {}
        for batch in planned.batches:
            rows = [{"line": "Open point.", "notes": [i], "status": "open"} for i in batch.must_carry]
            settled = [i for i in batch.ids if i not in batch.must_carry][:3]
            if settled:
                rows.append({"line": "Settled points.", "notes": settled, "status": "settled"})
            by_group.setdefault(batch.group, []).extend(rows)
        return by_group

    def test_everything_fits_and_nothing_is_condensed(self):
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 10 ** 6)
        got = digests.render(found, ORDER, FENCE, 10 ** 6, planned, {})
        self.assertEqual([], got.condensed)
        self.assertEqual(sorted(i.id for i in found), sorted(got.ids))
        self.assertEqual([], got.codes)

    def test_a_condensed_group_keeps_every_customer_and_segment_and_open_note(self):
        found = a_book()
        limit = 4000
        planned = digests.plan(found, ORDER, FENCE, limit)
        got = digests.render(found, ORDER, FENCE, limit, planned, self.lines(planned, found))
        self.assertIn("Harbour fleets", got.condensed)
        self.assertLessEqual(len(got.text), limit)
        for kept in ("n60", "n61", "n62", "n90"):
            self.assertIn(kept, got.ids)
        self.assertIn("Gullwing Ferries", got.text)
        self.assertNotIn("bought the harbour feed in spring", got.text)
        self.assertIn("[n62]", got.text)
        self.assertGreater(got.folded, 0)
        self.assertIn(digests.CODE_NOTES_CONDENSED, got.codes)
        self.assertEqual([], got.dropped)

    def test_a_digest_line_citing_a_note_this_draft_may_not_read_is_left_out(self):
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 4000)
        lines = self.lines(planned, found)
        narrowed = [item for item in found if item.id != "n62"]
        got = digests.render(narrowed, ORDER, FENCE, 4000, planned, lines)
        self.assertNotIn("n62", got.ids)
        self.assertNotIn("[n62]", got.text)

    def test_a_request_never_goes_over_the_limit_and_open_lines_are_kept_longest(self):
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 4000)
        lines = self.lines(planned, found)
        for rows in lines.values():
            rows.extend(
                {"line": "A settled point at some length, repeated %d." % i, "notes": [rows[-1]["notes"][0]],
                 "status": "settled"}
                for i in range(80)
            )
        got = digests.render(found, ORDER, FENCE, 2600, planned, lines)
        self.assertLessEqual(len(got.text), 2600)
        self.assertIn("[n62]", got.text)
        self.assertIn("n60", got.ids)
        self.assertFalse(got.over)

    def test_whole_groups_with_customers_never_push_a_request_over(self):
        # The review of 2026-11-24, finding 1: the last resort sized whole
        # groups with customer words held back and then printed them in full.
        found = many(1, 20, "Harbour fleets")
        found += [note(100 + i, kind="customer", segment="Inland depots", customer="Depot %d" % i,
                       status="open", quote="Depot %d asked about the yard feed at length." % i)
                  for i in range(30)]
        # The review's case: the facts condensed with no lines yet kept, and
        # the customers read whole.
        planned = digests.DigestPlan(["Harbour fleets"], [])
        for limit in (2500, 1500):
            got = digests.render(found, ORDER, FENCE, limit, planned, {})
            self.assertLessEqual(len(got.text), limit)
            self.assertFalse(got.over)
        self.assertTrue(got.dropped)

    def test_a_request_that_cannot_fit_what_it_must_carry_says_so(self):
        found = [note(100 + i, kind="customer", segment="Inland depots", customer="Depot %d" % i)
                 for i in range(60)]
        got = digests.render(found, ORDER, FENCE, 1000, digests.DigestPlan(["Inland depots"], []), {})
        self.assertTrue(got.over)
        self.assertIn(digests.CODE_NOTES_OVER, got.codes)

    def test_open_notes_read_whole_outlive_settled_shorter_lines(self):
        # Finding 2: open notes were left out while settled lines stayed.
        found = many(1, 60, "Harbour fleets")
        found += many(200, 10, "Inland depots", status="open")
        planned = digests.plan(found, ORDER, FENCE, 3000)
        self.assertEqual(["Harbour fleets"], planned.groups)
        lines = {"Harbour fleets": [
            {"line": "Settled point %d at some length to fill the room." % i, "notes": ["n%d" % (i + 1)],
             "status": "settled"} for i in range(29)]}
        got = digests.render(found, ORDER, FENCE, 2600, planned, lines)
        self.assertLessEqual(len(got.text), 2600)
        for i in range(200, 210):
            self.assertIn("n%d" % i, got.ids)

    def test_a_narrowed_draft_still_reads_every_open_note_it_may_read(self):
        # Finding 3: a line citing an open note in view and a note out of
        # view was left out, and the open note was counted as settled.
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 4000)
        lines = {"Harbour fleets": [{"line": "Berth pricing.", "notes": ["n62", "n10"], "status": "open"}]}
        narrowed = [item for item in found if item.id != "n10"]
        got = digests.render(narrowed, ORDER, FENCE, 4000, planned, lines)
        self.assertIn("n62", got.ids)
        self.assertIn("to be confirmed", got.text)
        settled_facts = [i for i in narrowed if i.segment == "Harbour fleets" and i.kind == "fact" and i.settled]
        self.assertEqual(len(settled_facts), got.folded)

    def test_when_even_condensed_it_does_not_fit_the_rest_is_left_out_and_said(self):
        found = a_book()
        planned = digests.plan(found, ORDER, FENCE, 4000)
        got = digests.render(found, ORDER, FENCE, 1500, planned, self.lines(planned, found))
        self.assertTrue(got.dropped)
        self.assertIn(notes.CODE_NOTES_CAPPED, got.codes)
        for kept in ("n60", "n61", "n62"):
            self.assertIn(kept, got.ids)


# --- Through setup: a run whose notes do not fit one draft (D2 to D4) ---------

TODAY = datetime.date(2026, 11, 24)
SESSION = "s-digests"
SHIM = os.path.join(support.PLUGIN_DIR, "skills", "join", "scripts", "join.py")

HARBOUR = "# Harbour fleets\n\n" + "\n\n".join(
    "Harbour fleets point %d: the berth feed refreshes every %d minutes." % (i, i + 1)
    for i in range(1, 41)
) + "\n\nHarbour fleets pricing per berth is to be confirmed.\n\nHarbour fleets: Gullwing Ferries bought the feed.\n"
AIRFIELDS = "# Airfields\n\nAirfields buy the apron view.\n"


class Limit(object):
    def __init__(self, chars):
        self.chars = chars

    def __enter__(self):
        self.previous = constants.DRAFT_SOURCES_MAX_CHARS
        constants.DRAFT_SOURCES_MAX_CHARS = self.chars
        return self

    def __exit__(self, *_):
        constants.DRAFT_SOURCES_MAX_CHARS = self.previous
        return False


def run_join(*arguments):
    return subprocess.run(
        [sys.executable, SHIM] + [str(item) for item in arguments],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class ThroughSetup(unittest.TestCase):
    """A run with two files, its notes taken and accepted, read at a low limit."""

    # Both files fit one batch of notes, and their notes do not fit one draft.
    LIMIT = 4000

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.limit = Limit(self.LIMIT)
        self.limit.__enter__()
        self.addCleanup(self.limit.__exit__)
        content = os.path.join(os.environ["HOME"], "company")
        support.write(os.path.join(content, "harbour.md"), HARBOUR)
        support.write(os.path.join(content, "airfields.md"), AIRFIELDS)
        self.run_id = join_flow.new_run(TODAY)
        join_flow.list_sources(content, self.run_id, today=TODAY)
        join_flow.freeze_sources(content, SESSION, self.run_id, today=TODAY)
        planned = join_flow.notes_plan(self.run_id, today=TODAY)
        number = dict((s.label, n) for n, s in enumerate(planned.sources, start=1))
        harbour, airfields = number["harbour.md"], number["airfields.md"]
        rows = [
            {"source": harbour, "kind": "fact", "segment": "Harbour fleets", "customer": "",
             "figure": "", "status": "settled",
             "quote": "Harbour fleets point %d: the berth feed refreshes every %d minutes." % (i, i + 1)}
            for i in range(1, 41)
        ]
        rows.append({"source": harbour, "kind": "fact", "segment": "Harbour fleets", "customer": "",
                     "figure": "", "status": "open",
                     "quote": "Harbour fleets pricing per berth is to be confirmed."})
        rows.append({"source": harbour, "kind": "customer", "segment": "Harbour fleets",
                     "customer": "Gullwing Ferries", "figure": "", "status": "settled",
                     "quote": "Harbour fleets: Gullwing Ferries bought the feed."})
        rows.append({"source": airfields, "kind": "segment", "segment": "Airfields", "customer": "",
                     "figure": "", "status": "settled", "quote": "Airfields buy the apron view."})
        self.assertEqual(1, len(planned.batches))
        self.rows = rows
        self.take_notes(rows)

    def take_notes(self, rows):
        path = join_flow.notes_file(self.run_id, 1)
        support.write(path, answer(*rows))
        checked = join_flow.notes_check(self.run_id, 1, path, today=TODAY)
        self.assertTrue(checked.accepted, checked.problems)

    def book(self):
        return join_flow.notes_for_drafts(self.run_id, today=TODAY)

    def open_id(self):
        return [item.id for item in self.book().notes if item.status == "open"][0]

    def write_digest(self, number, *rows):
        made = join_flow.digest_assemble(self.run_id, number, "Northwind", today=TODAY)
        support.write(made.answer, answer(*rows))
        return made

    def good_rows(self, batch):
        settled = [i for i in batch.ids if i not in batch.must_carry]
        rows = [{"line": "The berth feed refreshes often.", "notes": settled[:5], "status": "settled"}]
        if batch.must_carry:
            rows.append({"line": "Pricing per berth is not settled.", "notes": batch.must_carry, "status": "open"})
        return rows

    def digest_everything(self):
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        cited = set()
        for batch in planned.batches:
            rows = self.good_rows(batch)
            cited.update(i for row in rows for i in row["notes"])
            made = self.write_digest(batch.number, *rows)
            checked = join_flow.digest_check(self.run_id, batch.number, made.answer, today=TODAY)
            self.assertTrue(checked.accepted, checked.problems)
        # How many facts the lines leave out: every fact no line cites.
        return 41 - len(cited)

    def holding_the_open_note(self):
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        return [b for b in planned.batches if b.must_carry][0]


class TestDigestsThroughSetup(ThroughSetup):
    def test_the_plan_condenses_the_large_group_and_nothing_when_it_fits(self):
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        self.assertEqual(["Harbour fleets"], planned.groups)
        self.assertEqual(2, len(planned.batches))
        self.assertEqual({"Harbour fleets"}, set(b.group for b in planned.batches))

    def test_the_request_holds_the_facts_fenced_and_the_rules(self):
        made = join_flow.digest_assemble(self.run_id, 1, "Northwind", today=TODAY)
        text = support.read(made.prompt)
        self.assertTrue(made.prompt.startswith(join_flow.scratch_dir(self.run_id)))
        self.assertTrue(made.answer.startswith(join_flow.drafts_dir(self.run_id)))
        self.assertNotIn("{{", text)
        self.assertIn("Northwind", text)
        self.assertIn(constants.SOURCE_FENCE_SENTENCE, text)
        self.assertIn("refreshes every 7 minutes", text)
        self.assertNotIn("Gullwing Ferries bought", text)
        self.assertIn("email address", text)

    def test_a_draft_waits_for_its_digest(self):
        with self.assertRaises(notes.NotesRefused) as caught:
            join_flow.preview_step(self.run_id, "icp", today=TODAY)
        self.assertEqual(digests.CODE_DIGESTS_WAITING, caught.exception.code)
        self.assertEqual([(1, "waiting"), (2, "waiting")], join_flow.digest_status(self.run_id, today=TODAY))

    def test_a_good_digest_is_kept_and_the_draft_reads_it(self):
        folded = self.digest_everything()
        self.assertEqual([(1, "done"), (2, "done")], join_flow.digest_status(self.run_id, today=TODAY))
        taken = join_flow.notes_for_a_draft(self.run_id, "icp", today=TODAY)
        self.assertEqual(["Harbour fleets"], taken.rendered.condensed)
        self.assertIn("Gullwing Ferries", taken.rendered.text)
        self.assertIn("[%s]" % self.open_id(), taken.rendered.text)
        self.assertLessEqual(len(taken.rendered.text), self.LIMIT)
        self.assertIn(self.open_id(), taken.rendered.ids)
        previewed = join_flow.preview_step(self.run_id, "icp", today=TODAY)
        self.assertEqual(["Harbour fleets"], previewed.condensed)
        self.assertEqual(folded, previewed.folded)

    def test_a_refused_digest_is_tried_again_then_setup_carries_what_is_open(self):
        self.digest_everything()
        batch = self.holding_the_open_note()
        settled = [i for i in batch.ids if i not in batch.must_carry][:1]
        made = self.write_digest(batch.number, {"line": "The feed refreshes.", "notes": settled, "status": "settled"})
        os.remove(join_flow._digest_record(self.run_id, batch.number))
        for attempt in (1, 2):
            checked = join_flow.digest_check(self.run_id, batch.number, made.answer, today=TODAY)
            self.assertFalse(checked.accepted)
            self.assertEqual(attempt, checked.attempt)
            self.assertIn("open-note-not-carried:%s" % self.open_id(), checked.problems)
        checked = join_flow.digest_check(self.run_id, batch.number, made.answer, today=TODAY)
        self.assertTrue(checked.accepted)
        self.assertEqual(1, checked.by_setup)
        taken = join_flow.notes_for_a_draft(self.run_id, "icp", today=TODAY)
        self.assertIn("to be confirmed", taken.rendered.text)
        self.assertIn(self.open_id(), taken.rendered.ids)

    def test_checking_a_done_digest_again_keeps_it(self):
        # Finding 5: a second check of a done digest wiped it.
        self.digest_everything()
        made = join_flow.digest_assemble(self.run_id, 1, "Northwind", today=TODAY)
        support.write(made.answer, "nothing readable")
        checked = join_flow.digest_check(self.run_id, 1, made.answer, today=TODAY)
        self.assertTrue(checked.accepted)
        self.assertEqual([(1, "done"), (2, "done")], join_flow.digest_status(self.run_id, today=TODAY))

    def test_review_reads_the_notes_the_request_held(self):
        # Finding 4: review and support took the full view's notes, not the
        # notes the narrowed request showed.
        self.digest_everything()
        number = dict((s.label, n) for n, s in enumerate(
            join_flow.notes_plan(self.run_id, today=TODAY).sources, start=1))
        join_flow.assemble_step("icp", self.run_id, "Northwind", "", today=TODAY,
                                only_index=[number["harbour.md"]])
        held = join_flow.request_ids(self.run_id, "icp")
        narrowed = join_flow.notes_for_a_draft(self.run_id, "icp", today=TODAY,
                                               only_index=[number["harbour.md"]])
        self.assertEqual(sorted(narrowed.rendered.ids), sorted(held))

    def test_only_the_file_setup_named_is_checked(self):
        self.write_digest(1, {"line": "x", "notes": ["n1"], "status": "settled"})
        elsewhere = os.path.join(os.environ["HOME"], "digest.md")
        support.write(elsewhere, "")
        with self.assertRaises(digests.DigestRefused) as caught:
            join_flow.digest_check(self.run_id, 1, elsewhere, today=TODAY)
        self.assertEqual(digests.CODE_NOT_THE_DIGEST_FILE, caught.exception.code)

    def test_new_notes_make_the_digest_wait_again(self):
        self.digest_everything()
        self.take_notes(self.rows[1:])
        self.assertIn("waiting", [state for _n, state in join_flow.digest_status(self.run_id, today=TODAY)])


class TestTheScriptAtTheShippedLimit(ThroughSetup):
    LIMIT = constants.DRAFT_SOURCES_MAX_CHARS

    def test_digest_plan_and_status_say_there_is_nothing_to_condense(self):
        # The script runs at the shipped limit, where these notes fit, so it
        # says no digest is needed; the lowered limit is tested in process.
        finished = run_join("digest-status", "--run", self.run_id)
        self.assertEqual(0, finished.returncode, finished.stderr)
        self.assertIn(b"waiting=0", finished.stdout)
        finished = run_join("digest-plan", "--run", self.run_id)
        self.assertIn(b"digests=0", finished.stdout)
        finished = run_join("digest-assemble", "--run", self.run_id, "--batch", "1",
                            "--company-file", "/nowhere")
        self.assertNotEqual(0, finished.returncode)


class TestDigestsThroughTheScript(ThroughSetup):
    def script(self, *arguments):
        env = dict(os.environ, GTM_BASE_TESTS_READING_LIMIT=str(self.LIMIT))
        return subprocess.run(
            [sys.executable, SHIM] + [str(item) for item in arguments],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def value(self, finished, name):
        for line in finished.stdout.decode("utf-8").split("\n"):
            if line.startswith(name + "="):
                return line[len(name) + 1:].strip().strip('"')
        return None

    def company_file(self):
        finished = self.script("words-file", "--run", self.run_id, "--for", "company")
        path = self.value(finished, "words")
        support.write(path, "Northwind")
        return path

    def test_plan_assemble_check_and_status_through_the_script(self):
        finished = self.script("digest-plan", "--run", self.run_id)
        self.assertEqual(0, finished.returncode, finished.stdout + finished.stderr)
        self.assertEqual("1", self.value(finished, "groups"))
        self.assertEqual("2", self.value(finished, "digests"))
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        for batch in planned.batches:
            finished = self.script("digest-assemble", "--run", self.run_id, "--batch", batch.number,
                                   "--company-file", self.company_file())
            self.assertEqual(0, finished.returncode, finished.stdout + finished.stderr)
            answer_file = self.value(finished, "digest")
            support.write(answer_file, answer(*self.good_rows(batch)))
            finished = self.script("digest-check", "--run", self.run_id, "--batch", batch.number,
                                   "--digest", answer_file)
            self.assertEqual(0, finished.returncode, finished.stdout + finished.stderr)
            self.assertEqual("yes", self.value(finished, "accepted"))
        finished = self.script("digest-status", "--run", self.run_id)
        self.assertIn(b"digest=1 done", finished.stdout)
        self.assertIn(b"waiting=0", finished.stdout)
        finished = self.script("preview", "--step", "icp", "--run", self.run_id)
        self.assertEqual(0, finished.returncode, finished.stdout + finished.stderr)
        self.assertIn(b"note=notes-condensed", finished.stdout)
        self.assertIn(b"were condensed first into shorter lines", finished.stdout)

    def test_the_skills_digest_lines_run_as_they_are_written(self):
        # The walk of the skill follows it past step 5f when there is nothing
        # to condense, so the lines of step 5f are run here as written, with
        # each placeholder filled the way the skill says.
        import re

        skill = support.read(os.path.join(os.path.dirname(os.path.dirname(SHIM)), "SKILL.md"))
        step = skill.split("### Step 5f.")[1].split("### Step 6.")[0]
        lines = [
            line.strip() for line in step.split("\n")
            if line.strip().startswith("python3 scripts/join.py digest-")
        ]
        self.assertEqual(
            ["digest-plan", "digest-assemble", "digest-check"],
            [line.split()[2] for line in lines],
        )
        self.assertIn("python3 scripts/join.py digest-status --run <run identifier>", step)
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        state = {"<run identifier>": self.run_id}
        for batch in planned.batches:
            state["<digest number>"] = str(batch.number)
            for line in lines:
                if "<the path it printed>" in line:
                    state["<the path it printed>"] = self.company_file()
                filled = line
                for name, value in state.items():
                    filled = filled.replace(name, value)
                self.assertNotIn("<", filled, filled)
                words = filled.split()[2:]
                if words[0] == "digest-check":
                    support.write(state["<digest file>"], answer(*self.good_rows(batch)))
                finished = self.script(*words)
                self.assertEqual(0, finished.returncode, filled + finished.stdout.decode())
                if words[0] == "digest-assemble":
                    state["<digest file>"] = self.value(finished, "digest")
        finished = self.script("digest-status", "--run", self.run_id)
        self.assertIn(b"waiting=0", finished.stdout)

    def test_a_draft_waiting_for_its_digest_says_so_through_the_script(self):
        finished = self.script("preview", "--step", "icp", "--run", self.run_id)
        self.assertNotEqual(0, finished.returncode)
        self.assertIn(b"codes=digests-waiting", finished.stdout)
        self.assertIn(b"Run digest-status", finished.stdout)

    def test_the_preview_sentences(self):
        import io

        sys.path.insert(0, os.path.dirname(SHIM))
        try:
            import join as join_script
        finally:
            sys.path.pop(0)
        folded = self.digest_everything()
        previewed = join_flow.preview_step(self.run_id, "icp", today=TODAY)
        out = io.StringIO()
        join_script.say_condensed(out, previewed)
        said = out.getvalue()
        self.assertIn("the facts about Harbour fleets were condensed", said)
        self.assertIn("leave out %d facts" % folded, said)


if __name__ == "__main__":
    unittest.main()
