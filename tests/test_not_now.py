"""The "not now" answer, reached through the join skill.

The answer itself is written down by `offer_answer`, which shipped in 0.1.5
because a person answering the offer had to be recorded a release before there
was any setting up to do. `not_now` is the name the plan uses for it, and the
join skill's own script is the way the assistant reaches it now that the skill
exists. All three have to say the same one sentence, and it has to be the same
sentence the skill's description carries, because that sentence is the whole of
how a person who said no gets back in.
"""

import os
import subprocess
import sys
import unittest

import support

from gtmbase import constants, machine, not_now, offer_answer

SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "join")
SHIM = os.path.join(SKILL_DIR, "scripts", "join.py")


class TestTheNameThePlanUses(unittest.TestCase):
    """`not_now` is the other name for the module that records the answer."""

    def test_it_is_the_same_answer_and_the_same_sentences(self):
        self.assertIs(not_now.main, offer_answer.main)
        self.assertEqual(offer_answer.NOT_NOW, not_now.NOT_NOW)
        self.assertEqual(
            offer_answer.SETUP_RECORDS_ITSELF, not_now.SETUP_RECORDS_ITSELF
        )
        self.assertEqual(offer_answer.COULD_NOT_WRITE, not_now.COULD_NOT_WRITE)


class TestSayingNotNowThroughTheSkill(unittest.TestCase):
    """One command, one answer written down, one sentence said back."""

    def run_script(self, *arguments):
        return subprocess.run(
            [sys.executable, SHIM] + list(arguments),
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_the_answer_is_recorded_and_the_one_sentence_is_all_it_prints(self):
        with support.Sandbox():
            finished = self.run_script("not-now")

            self.assertEqual(0, finished.returncode, finished.stderr)
            self.assertEqual(
                constants.RESTART_SENTENCE + "\n", finished.stdout.decode("utf-8")
            )
            self.assertEqual(b"", finished.stderr)
            self.assertEqual("not-now", machine.load_machine_state().answer)

    def test_the_sentence_it_prints_is_the_one_the_skill_answers_to(self):
        with support.Sandbox():
            printed = self.run_script("not-now").stdout.decode("utf-8").strip()

        description = support.read(os.path.join(SKILL_DIR, "SKILL.md")).split("---")[1]

        self.assertEqual(constants.RESTART_SENTENCE, printed)
        self.assertIn(printed, description)

    def test_it_names_no_folder_and_no_web_address(self):
        with support.Sandbox():
            printed = self.run_script("not-now").stdout.decode("utf-8")

            self.assertNotIn("/", printed)
            self.assertNotIn("://", printed)
            self.assertNotIn(os.environ["GTM_BASE_HOME"], printed)


if __name__ == "__main__":
    unittest.main()
