"""Track 4, Unit T4.10: the outbound sequence, the third skill GTM Base ships.

A sequence grounded in one segment's own language, with every claim traced to
the document behind it, as the reviewed Unit 1.4c text of the 2026-09-19
roadmap describes, reaching a base as a shipped skill like drift grade.

These check what code can prove: which documents were read, the claims table
naming only those, the contact and key screens, a dropped claim reported, and
the gaps. They do not prove the sequence is good or that no prospect's name
slipped in, because the screens do not detect arbitrary names. That is what
the owner's replay and SC-C are for, and the two are kept apart.
"""

import os
import re
import unittest

import starter_support as shared
import support
import test_drift_grade as drift
import test_runner_contract as contract

from gtmbase import runner, starter

SKILL = starter.OUTBOUND_SEQUENCE
SKILL_MD = "skills/%s/SKILL.md" % SKILL
STANDARD = "standards/outbound-sequence.md"
MESSAGING = "context/messaging.md"


def documents(segment=True, messaging=True):
    found = drift.the_documents(messaging=messaging)
    if segment:
        found[shared.SEGMENT] = shared.fixture(SKILL, "long-distance.md")
    return found


def claims_documents(output):
    """Every document the claims table under a sequence names."""
    table = output.split("Claims and where each comes from:", 1)[-1].split("\nDropped:", 1)[0]
    return [
        cells[-1].strip()
        for cells in (
            [cell for cell in line.strip().strip("|").split("|")]
            for line in table.splitlines()
            if line.strip().startswith("|")
        )
        if cells[-1].strip().startswith("context/")
    ]


class TheStarterSkill(unittest.TestCase):
    def test_it_passes_the_contract_check(self):
        result = runner.check_skill(SKILL, shared.starter_files(SKILL))
        self.assertTrue(result.passed, result.problems)

    def test_each_approved_output_passes_and_each_wrong_output_fails(self):
        for name, files in sorted(shared.examples(SKILL).items()):
            with self.subTest(example=name):
                approved, wrong = shared.judged(files)
                self.assertEqual([], approved)
                self.assertTrue(wrong)
                for one, problems in wrong.items():
                    self.assertTrue(problems, one)

    def test_every_claims_row_names_a_document_the_example_ran_against(self):
        for name, files in sorted(shared.examples(SKILL).items()):
            held = {
                "context/%s" % one
                for one in files
                if one not in ("input.md", "output.md", "expectations.md")
                and not one.startswith("wrong-")
            }
            # A segment's document sits in the segments folder of the base.
            held = {
                shared.SEGMENT if one == "context/long-distance.md" else one for one in held
            }
            with self.subTest(example=name):
                named = claims_documents(files["output.md"])
                self.assertTrue(named)
                self.assertTrue(set(named) <= held, set(named) - held)

    def test_a_row_naming_a_document_that_was_not_read_fails(self):
        files = shared.examples(SKILL)["segment-sequence"]
        self.assertIn("context/case-studies.md", claims_documents(files["wrong-unread-document.md"]))
        _approved, wrong = shared.judged(files)
        self.assertTrue(wrong["wrong-unread-document.md"])

    def test_a_claim_with_no_grounding_is_dropped_and_reported_not_softened(self):
        files = shared.examples(SKILL)["dropped-claim"]
        self.assertIn("cuts dispatch time in half", files["input.md"])
        self.assertIn('Dropped: "cuts dispatch time in half"', files["output.md"])
        _approved, wrong = shared.judged(files)
        self.assertTrue(wrong["wrong-keeps-the-claim.md"])
        self.assertTrue(wrong["wrong-softens-it.md"])

    def test_each_missing_document_is_a_named_gap(self):
        output = shared.examples(SKILL)["gaps-named"]["output.md"]
        self.assertIn("Gaps: the messaging, the voice guide and the competitors", output)
        self.assertIn("in the words of %s" % shared.PROFILE, output)

    def test_a_segment_the_base_does_not_hold_stops_the_sequence(self):
        text = shared.starter_files(SKILL)[SKILL_MD]
        self.assertIn("list the segments it does hold and stop", text)

    def test_it_declares_what_the_plan_says(self):
        declared = runner.declaration_of(shared.starter_files(SKILL)[SKILL_MD])
        self.assertEqual([], declared.problems)
        self.assertEqual([shared.PROFILE, shared.POSITIONING], declared.required)
        self.assertEqual(
            [runner.SEGMENTS_FOLDER, MESSAGING, "context/voice.md", "context/competitors.md"],
            declared.optional,
        )
        self.assertEqual(STANDARD, declared.standard)

    def test_the_body_names_no_command_and_reads_no_work_in_flight(self):
        for path, text in shared.starter_files(SKILL).items():
            if "/examples/" not in path:
                with self.subTest(path=path):
                    self.assertFalse(runner.names_a_command(text))
                    self.assertNotIn("context/work", text)

    def test_every_file_is_a_shape_a_base_admits(self):
        self.assertTrue(shared.admitted(shared.starter_files(SKILL)))


class TheScreens(unittest.TestCase):
    """Security: no email address, phone number or key leaves a run."""

    def test_finish_refuses_a_sequence_holding_contact_details(self):
        clean = shared.examples(SKILL)["segment-sequence"]["output.md"]
        sources = {"positioning.md": drift.the_documents()[shared.POSITIONING]}
        for leaked in (
            "Reach Pat at pat.moreno@example.com.",
            "Call Pat on 415-555-0142.",
        ):
            with self.subTest(leaked=leaked):
                self.assertTrue(runner.screen_work(clean + "\n" + leaked, sources))


class TheStandard(unittest.TestCase):
    def setUp(self):
        self.text = starter.standard_text(SKILL)

    def test_it_has_plan_ones_five_parts(self):
        self.assertEqual(
            shared.PLAN_ONE_HEADINGS, re.findall(r"^## (.*)$", self.text, re.MULTILINE)
        )

    def test_it_carries_no_digit_outside_a_date(self):
        self.assertTrue(shared.no_digit_outside_a_date(self.text))


class InstallingAndRunning(unittest.TestCase):
    def test_a_named_segment_is_read_and_its_path_handed_on(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(), SKILL)
            result = shared.run(root, base_id, SKILL)
            self.assertEqual(runner.OUTCOME_READY_WITH_GAPS, result.outcome)
            self.assertIn(shared.SEGMENT, result.documents)
            self.assertEqual(["context/voice.md", "context/competitors.md"], result.gaps)

    def test_on_a_base_with_no_segments_it_reads_the_profile(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(segment=False, messaging=False), SKILL)
            result = shared.run(root, base_id, SKILL)
            self.assertIn(shared.PROFILE, result.documents)
            self.assertEqual(
                [MESSAGING, "context/voice.md", "context/competitors.md"], result.gaps
            )

    def test_without_its_rules_file_nothing_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.a_base(sandbox, documents(), SKILL)
            prepared = starter.prepare(root, base_id, SKILL, shared.REASON, runner=support.NoRemoteRunner())
            from gtmbase import skill_install

            done = skill_install.approve(
                root, base_id, prepared.skill.prepared_id, prepared.skill.shown,
                runner_=support.NoRemoteRunner(), now=shared.NOW,
            )
            self.assertTrue(done.done, done.sentence)
            self.assertFalse(os.path.exists(os.path.join(root, STANDARD)))
            result = shared.run(root, base_id, SKILL)
            self.assertEqual(runner.REFUSED_REQUIRED, result.refusal)

    def test_a_rules_file_the_base_already_holds_is_never_offered_over(self):
        with support.Sandbox() as sandbox:
            own = support.skill_document("standard", "Our own outbound rules")
            root, base_id = shared.a_base(sandbox, dict(documents(), **{STANDARD: own}), SKILL)
            prepared = starter.prepare(root, base_id, SKILL, shared.REASON, runner=support.NoRemoteRunner())
            self.assertIsNone(prepared.standard)
            self.assertEqual(own, support.read(os.path.join(root, STANDARD)))

    def test_a_flagged_profile_pauses_the_run_before_any_sequence(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(), SKILL)
            contract.a_change_about(root, shared.PROFILE)
            result = shared.run(root, base_id, SKILL)
            self.assertTrue(result.waiting)
            self.assertFalse(result.hands_back)
            self.assertNotIn("# Outbound sequence", result.render())


if __name__ == "__main__":
    unittest.main()
