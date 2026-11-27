"""The customer-name check, after the scored replay of 2026-11-25.

A draft, and a digest line, may never name a customer setup has not given
it, and review refuses one that does. In the replay, writers refused for
naming a customer were told only where the line was, never which name
matched, so they guessed: a job title that is also a customer's short name,
a two-letter abbreviation, the ordinary word "Enterprise", and city names,
and they cut those words out of their lines, detail and all.

Two things were wrong. The short name setup makes by dropping a formal
ending, such as "Enterprise" from "Enterprise Holdings", was matched
wherever the word stood with a capital, at the start of a sentence or in a
job title, though the material itself uses it as an ordinary word. And the
refusal never said what it matched. A two-letter short name such as "QA"
from "QA Ltd" is still matched, because real customers go by two letters
too, but the refusal now says "QA", so only that word is rewritten. Every
name here is made up.
"""

import importlib.util
import os
import subprocess
import sys
import unittest

import support
from test_citations import Run
from test_digests import SHIM, ThroughSetup, answer, note, no_screen
from test_notes import TODAY

from gtmbase import citations, digests, join_flow, notes


def fake(note_id, quote, kind="fact", customer=""):
    return notes.Note(
        {"source": 1, "kind": kind, "segment": "", "customer": customer,
         "figure": "", "status": "settled", "quote": quote},
        id=note_id,
    )


FOUND = [
    fake("n1", "Enterprise Holdings signed for three years.", kind="customer",
         customer="Enterprise Holdings"),
    fake("n2", "Most enterprise buyers ask for single sign-on first."),
    fake("n3", "QA Ltd renewed in March.", kind="customer", customer="QA Ltd"),
    fake("n4", "QA teams run the pilot before anyone else."),
    fake("n5", "Principal Group bought the audit pack.", kind="customer",
         customer="Principal Group"),
    fake("n6", "A principal engineer signs off on the tooling."),
    fake("n7", "Acme Corp bought it first.", kind="customer", customer="Acme Corp"),
    fake("n8", "Summit renewed for two years.", kind="customer", customer="Summit"),
    fake("n9", "The summit in May drew most of the leads."),
    fake("n10", "Globex Ltd moved its fleet over.", kind="customer", customer="Globex Ltd"),
    fake("n11", "Send renewals to procurement@globex.com before June, or see globex.com/terms."),
]
def join_script():
    """The setup script itself, for the sentences it prints."""
    spec = importlib.util.spec_from_file_location("gtm_base_join_names", SHIM)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


JOIN = join_script()

READABLE = dict((item.id, item) for item in FOUND)


def names():
    return citations.customer_names(FOUND, "Northwind", [])


def customer_codes(line):
    return [c for _b, c in citations.check(line, READABLE, names()) if c == citations.CODE_CUSTOMER]


class TestOrdinaryWordsAreNotCustomers(unittest.TestCase):
    def test_a_short_name_the_material_uses_as_an_ordinary_word_is_not_matched(self):
        self.assertEqual([], customer_codes("Enterprise buyers ask for single sign-on first. [n2]"))
        self.assertEqual([], customer_codes("They sell an Enterprise tier to big fleets. [n2]"))

    def test_a_job_title_that_is_also_a_short_name_is_not_matched(self):
        self.assertEqual([], customer_codes("The buyer is usually a Principal Engineer. [n6]"))
        self.assertEqual([], customer_codes("Principal engineers sign off on the tooling. [n6]"))

    def test_a_two_letter_short_name_is_still_matched_and_named(self):
        found = citations.check("QA teams run the pilot before anyone else. [n4]", READABLE, names())
        self.assertEqual(["section-0-paragraph-1:QA"], citations.named_for(found))

    def test_a_lower_case_address_does_not_make_a_short_name_ordinary(self):
        self.assertIn("Globex", names())
        self.assertEqual([citations.CODE_CUSTOMER], customer_codes("Globex moved its fleet over. [n11]"))

    def test_the_whole_name_is_still_refused(self):
        for line in (
            "Enterprise Holdings signed for three years. [n2]",
            "QA Ltd renewed in March. [n4]",
            "Principal Group bought the audit pack. [n6]",
        ):
            self.assertEqual([citations.CODE_CUSTOMER], customer_codes(line), line)

    def test_a_short_name_that_is_no_ordinary_word_is_still_refused(self):
        self.assertEqual([citations.CODE_CUSTOMER], customer_codes("Acme bought it first. [n2]"))
        self.assertEqual([citations.CODE_CUSTOMER], customer_codes("Acme's rollout took a month. [n2]"))

    def test_a_name_as_the_material_writes_it_is_refused_even_if_ordinary(self):
        # The material calls this customer Summit, so Summit with a capital
        # is the customer, whatever the word means in lower case.
        self.assertEqual([citations.CODE_CUSTOMER], customer_codes("Summit renewed for two years. [n9]"))
        self.assertEqual([], customer_codes("The summit in May drew most of the leads. [n9]"))

    def test_the_forms_given(self):
        given = names()
        for name in ("Enterprise Holdings", "QA Ltd", "QA", "Principal Group", "Acme Corp", "Acme",
                     "Summit", "Globex Ltd", "Globex"):
            self.assertIn(name, given)
        for name in ("Enterprise", "Principal"):
            self.assertNotIn(name, given)


class TestTheRefusalSaysWhatItMatched(unittest.TestCase):
    def test_names_in_gives_the_longest_form_it_matched(self):
        self.assertEqual("Acme Corp", citations._names_in("Acme Corp bought it.", ["Acme", "Acme Corp"]))
        self.assertEqual("Acme", citations._names_in("Acme bought it.", ["Acme Corp", "Acme"]))
        self.assertIsNone(citations._names_in("Nobody bought it.", ["Acme Corp", "Acme"]))

    def test_every_customer_a_line_names_is_given_once(self):
        found = citations.check("Globex and Acme Corp bought it, then Acme renewed. [n2]",
                                READABLE, names())
        self.assertEqual(
            ["section-0-paragraph-1:Globex", "section-0-paragraph-1:Acme Corp",
             "section-0-paragraph-1:Acme"],
            citations.named_for(found),
        )
        self.assertEqual(["Acme Corp"], citations._all_names_in("Acme Corp bought it.", ["Acme", "Acme Corp"]))

    def test_check_names_the_match_beside_where_it_is(self):
        found = citations.check("### Acme cut churn\n\nAcme bought it first. [n2]", READABLE, names())
        self.assertEqual(
            ["section-0-heading-1:Acme", "section-1-paragraph-1:Acme"], citations.named_for(found)
        )
        # The codes themselves still name only where.
        self.assertEqual([], [c for c in citations.codes_for(found) if "Acme" in c])

    def test_a_digest_line_names_its_match_and_its_code_does_not(self):
        batch = digests.DigestBatch(1, "Harbour fleets", [
            note(1, segment="Harbour fleets", quote="Harbour fleets renew every year."),
            note(3, segment="Harbour fleets", quote="Gullwing Ferries wants the night feed."),
        ], 5000)
        got = digests.check(
            answer({"line": "Corran Haulage renews every year.", "notes": ["n1"], "status": "settled"},
                   {"line": "Gullwing Ferries wants the night feed.", "notes": ["n3"], "status": "settled"}),
            batch, no_screen, ["Gullwing Ferries", "Corran Haulage"],
        )
        self.assertEqual(["line-1:customer-not-in-its-notes"], got.problems)
        self.assertEqual(["line-1:Corran Haulage"], got.named)
        both = digests.check(
            answer({"line": "Corran Haulage and Gullwing Ferries want the night feed.",
                    "notes": ["n1"], "status": "settled"}),
            batch, no_screen, ["Gullwing Ferries", "Corran Haulage"],
        )
        self.assertEqual(["line-1:Corran Haulage", "line-1:Gullwing Ferries"], both.named)


class TestTheReviewNamesTheMatch(Run):
    def test_review_step_names_the_customer_it_matched(self):
        reviewed = self.draft(
            "Harbor Lending buys record level data. %s" % self.cite("Harbor Lending signed for a year.")
        )
        self.assertIn("customer-named:section-4-paragraph-1", reviewed.codes)
        self.assertEqual(["section-4-paragraph-1:Harbor Lending"], reviewed.named)

    def test_nothing_is_named_once_the_third_refusal_takes_the_line_out(self):
        line = "Harbor Lending buys record level data. %s" % self.cite("Harbor Lending signed for a year.")
        for _attempt in range(2):
            self.assertTrue(self.draft(line).named)
        reviewed = self.draft(line)
        self.assertTrue(reviewed.ready, reviewed.codes)
        self.assertEqual([], reviewed.named)

    def test_the_script_prints_the_name_on_a_line_of_its_own(self):
        self.draft(
            "Harbor Lending buys record level data. %s" % self.cite("Harbor Lending signed for a year.")
        )
        finished = subprocess.run(
            [sys.executable, SHIM, "review", "--step", "positioning", "--run", self.run,
             "--draft", self.path],
            env=dict(os.environ), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        printed = finished.stdout.decode("utf-8")
        self.assertNotEqual(0, finished.returncode, printed)
        self.assertIn('named="section-4-paragraph-1:Harbor Lending"\n', printed)
        codes = [line for line in printed.split("\n") if line.startswith("codes=")]
        self.assertEqual(1, len(codes), printed)
        self.assertNotIn("Harbor", codes[0])
        # The refusal says how to fix it, for a name the draft needed as a
        # place (Brandon's decision of 2026-11-27, the Denver case).
        self.assertIn(JOIN.CITE_AGAIN + "\n" + JOIN.CUSTOMER_NAME_FIX + "\n", printed)


class TestTheDigestScriptNamesTheMatch(ThroughSetup):
    def test_digest_check_prints_the_name_on_a_line_of_its_own(self):
        planned = join_flow.digest_plan(self.run_id, today=TODAY)
        batch = planned.batches[0]
        settled = [i for i in batch.ids if i not in batch.must_carry][:1]
        made = self.write_digest(
            batch.number,
            {"line": "Gullwing Ferries renews often.", "notes": settled, "status": "settled"},
        )
        finished = subprocess.run(
            [sys.executable, SHIM, "digest-check", "--run", self.run_id, "--batch", str(batch.number),
             "--digest", made.answer],
            env=dict(os.environ, GTM_BASE_TESTS_READING_LIMIT=str(self.LIMIT)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        printed = finished.stdout.decode("utf-8")
        self.assertIn("problem=line-1:customer-not-in-its-notes\n", printed)
        self.assertIn('named="line-1:Gullwing Ferries"\n', printed)


if __name__ == "__main__":
    unittest.main()
