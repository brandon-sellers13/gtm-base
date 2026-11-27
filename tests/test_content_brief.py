"""Track 4, Unit T4.9: the content brief, the second skill GTM Base ships.

A brief a writer can work from, grounded in the base, with every gap named
rather than filled. It follows drift grade's pattern: written in the plugin,
installed like any company skill, run on the runner. These check the written
skill, its examples, its standard, the install and the runner's outcomes;
whether a brief is good is its owner's read of a real one.
"""

import re
import unittest

import starter_support as shared
import support
import test_drift_grade as drift

from gtmbase import moment, runner, starter

SKILL = starter.CONTENT_BRIEF
SKILL_MD = "skills/%s/SKILL.md" % SKILL
MESSAGING = "context/messaging.md"
VOICE = "context/voice.md"
PERSONAS = "context/buyer-personas.md"


def documents(segment=True, voice=True):
    found = drift.the_documents(messaging=True)
    found[PERSONAS] = shared.fixture(SKILL, "buyer-personas.md")
    if segment:
        found[shared.SEGMENT] = shared.fixture(SKILL, "long-distance.md")
    if voice:
        found[VOICE] = shared.fixture(SKILL, "voice.md")
    return found


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

    def test_a_named_segments_brief_uses_its_own_words_not_the_profiles(self):
        files = shared.examples(SKILL)["segment-brief"]
        self.assertIn("long-distance.md", files)
        self.assertIn("multi-day jobs", files["output.md"])
        self.assertIn(shared.SEGMENT, files["output.md"])
        # The wrong output used the profile's general words, and fails.
        _approved, wrong = shared.judged(files)
        self.assertTrue(wrong["wrong-generic-profile.md"])

    def test_a_segment_with_no_file_is_briefed_against_the_profile_and_says_so(self):
        files = shared.examples(SKILL)["no-segment-file"]
        self.assertNotIn("self-storage.md", files)
        self.assertIn(shared.PROFILE, files["output.md"])
        self.assertIn("no document for a self-storage segment", files["output.md"])

    def test_a_missing_voice_guide_is_a_named_gap_never_a_generic_voice(self):
        files = shared.examples(SKILL)["no-voice"]
        self.assertNotIn("voice.md", files)
        self.assertIn("Gaps: the voice guide", files["output.md"])
        _approved, wrong = shared.judged(files)
        self.assertTrue(wrong["wrong-generic-voice.md"])

    def test_it_declares_what_the_plan_says(self):
        declared = runner.declaration_of(shared.starter_files(SKILL)[SKILL_MD])
        self.assertEqual([], declared.problems)
        self.assertEqual([shared.PROFILE, shared.POSITIONING], declared.required)
        self.assertEqual(
            [runner.SEGMENTS_FOLDER, MESSAGING, VOICE, PERSONAS, "context/design.md"],
            declared.optional,
        )
        self.assertEqual("standards/content-brief.md", declared.standard)

    def test_the_body_names_no_command_so_a_chat_can_serve_it(self):
        for path, text in shared.starter_files(SKILL).items():
            if "/examples/" not in path:
                with self.subTest(path=path):
                    self.assertFalse(runner.names_a_command(text))
                    self.assertNotIn("python", text)

    def test_every_file_is_a_shape_a_base_admits(self):
        self.assertTrue(shared.admitted(shared.starter_files(SKILL)))

    def test_the_brief_cites_no_work_in_flight(self):
        for path, text in shared.starter_files(SKILL).items():
            self.assertNotIn("context/work", text, path)


class TheStandard(unittest.TestCase):
    def setUp(self):
        self.text = starter.standard_text(SKILL)

    def test_it_has_plan_ones_five_parts(self):
        self.assertEqual(
            shared.PLAN_ONE_HEADINGS, re.findall(r"^## (.*)$", self.text, re.MULTILINE)
        )

    def test_it_carries_no_digit_outside_a_date(self):
        self.assertTrue(shared.no_digit_outside_a_date(self.text))


class Running(unittest.TestCase):
    def test_a_named_segments_document_is_handed_to_the_skill(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(), SKILL)
            result = shared.run(root, base_id, SKILL)
            self.assertEqual(runner.OUTCOME_READY_WITH_GAPS, result.outcome)
            self.assertIn(shared.SEGMENT, result.documents)
            self.assertIn(shared.SEGMENT, result.checked)
            self.assertEqual(["context/design.md"], result.gaps)

    def test_a_base_with_no_segments_is_not_short_of_one(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(segment=False), SKILL)
            result = shared.run(root, base_id, SKILL)
            self.assertNotIn(runner.SEGMENTS_FOLDER, result.gaps)
            self.assertFalse(any(path.startswith("context/icps/") for path in result.documents))

    def test_a_missing_voice_guide_is_named_as_a_gap(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(voice=False), SKILL)
            result = shared.run(root, base_id, SKILL)
            self.assertIn(VOICE, result.gaps)

    def test_a_flagged_segment_pauses_the_run_before_any_brief(self):
        with support.Sandbox() as sandbox:
            root, base_id = shared.installed(sandbox, documents(), SKILL)
            import test_runner_contract as contract

            contract.a_change_about(root, shared.SEGMENT)
            result = shared.run(root, base_id, SKILL)
            self.assertTrue(result.waiting)
            self.assertNotIn("# Content brief", result.render())


class TheOffer(unittest.TestCase):
    def test_it_is_offered_once_the_base_holds_the_messaging(self):
        with support.Sandbox() as sandbox:
            root, _base_id = shared.a_base(sandbox, documents(), SKILL)
            self.assertIn(SKILL, starter.offered(root))

    def test_it_is_not_offered_without_the_messaging(self):
        with support.Sandbox() as sandbox:
            without = documents()
            del without[MESSAGING]
            root, _base_id = shared.a_base(sandbox, without, SKILL)
            self.assertNotIn(SKILL, starter.offered(root))
            self.assertIn(starter.DRIFT_GRADE, starter.offered(root))


if __name__ == "__main__":
    unittest.main()
