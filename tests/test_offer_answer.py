"""The script that writes down a "not now" answer to the setup offer.

Live on 2026-09-06 a person answered "not now", the assistant said the sentence
it was primed with, and the account still recorded no answer at all, so the
offer came back the next session. These tests cover the script that closes that
gap and the way the session start behaves once an answer is written down.
"""

import datetime
import io
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base", "lib")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")
PLUGIN_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base")

for _path in (LIB_DIR, TESTS_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import plain_language  # noqa: E402
import support  # noqa: E402
from gtmbase import constants, machine, offer_answer, session_start  # noqa: E402

SCRIPT = os.path.join(PLUGIN_DIR, "scripts", "offer_answer.py")
NOW = datetime.datetime(2026, 9, 6, 12, 0, 0)


class TestRecordingAnAnswer(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.project = os.path.join(self.sandbox.path, "an-unrelated-project")
        support.write(os.path.join(self.project, "notes.txt"), "hello\n")
        self.empty = os.path.join(self.sandbox.path, "an-empty-folder")
        os.makedirs(self.empty)

    def run_script(self, *arguments):
        """Run the script the way the assistant is told to run it.

        The environment carries this test's own seat folder, so nothing here
        can reach the seat folder of the person running the tests.
        """
        return subprocess.run(
            [sys.executable, SCRIPT] + list(arguments),
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_hook(self, cwd, session="s-1"):
        return session_start.run(
            {"session_id": session, "source": "startup", "cwd": cwd},
            client="claude",
            now=NOW,
            plugin_root=PLUGIN_DIR,
        )

    # --- the answer it does record ------------------------------------------

    def test_not_now_is_recorded_and_the_one_sentence_is_all_it_prints(self):
        finished = self.run_script("--answer", "not-now")

        self.assertEqual(0, finished.returncode, finished.stderr)
        self.assertEqual(
            constants.RESTART_SENTENCE + "\n", finished.stdout.decode("utf-8")
        )
        self.assertEqual(b"", finished.stderr)
        self.assertEqual("not-now", machine.load_machine_state().answer)

    def test_what_it_prints_names_no_path_and_no_web_address(self):
        finished = self.run_script("--answer", "not-now")
        printed = finished.stdout.decode("utf-8")

        self.assertNotIn("/", printed)
        self.assertNotIn("://", printed)
        self.assertNotIn(os.environ["GTM_BASE_HOME"], printed)

    def test_the_script_is_there_and_can_be_run(self):
        self.assertTrue(os.path.isfile(SCRIPT))
        self.assertTrue(os.access(SCRIPT, os.X_OK), "the script must be executable")

    # --- the answers it leaves to the setup ---------------------------------

    def test_set_up_is_left_to_the_setup_itself_and_records_nothing(self):
        finished = self.run_script("--answer", "set-up")

        self.assertEqual(1, finished.returncode)
        self.assertEqual(
            offer_answer.SETUP_RECORDS_ITSELF + "\n", finished.stdout.decode("utf-8")
        )
        self.assertEqual("unset", machine.load_machine_state().answer)

    def test_join_an_unknown_word_and_no_answer_at_all_record_nothing(self):
        for arguments in (
            ("--answer", "join"),
            ("--answer", "maybe"),
            ("--answer",),
            (),
        ):
            with self.subTest(arguments=arguments):
                finished = self.run_script(*arguments)
                self.assertEqual(1, finished.returncode)
                self.assertEqual(
                    offer_answer.SETUP_RECORDS_ITSELF + "\n",
                    finished.stdout.decode("utf-8"),
                )
                self.assertEqual("unset", machine.load_machine_state().answer)

    # --- what happens when it cannot write ----------------------------------

    def test_a_write_that_fails_says_so_plainly_and_stops(self):
        def refuse(answer, runner=None):
            raise RuntimeError("the file could not be written")

        saved = machine.record_offer_answer
        machine.record_offer_answer = refuse
        self.addCleanup(setattr, machine, "record_offer_answer", saved)

        printed = io.StringIO()
        held = sys.stdout
        sys.stdout = printed
        try:
            code = offer_answer.main(["--answer", "not-now"])
        finally:
            sys.stdout = held

        self.assertEqual(1, code)
        self.assertEqual(offer_answer.COULD_NOT_WRITE + "\n", printed.getvalue())

    # --- what the session start does afterwards -----------------------------

    def test_a_recorded_not_now_stops_the_offer_in_the_folders_they_work_in(self):
        self.assertEqual(0, self.run_script("--answer", "not-now").returncode)

        another = os.path.join(self.sandbox.path, "a-second-project")
        support.write(os.path.join(another, "plan.txt"), "hello\n")
        self.assertIsNone(self.run_hook(self.project, session="s-2"))
        self.assertIsNone(self.run_hook(another, session="s-3"))

    def test_a_recorded_not_now_still_offers_in_an_empty_folder(self):
        self.assertEqual(0, self.run_script("--answer", "not-now").returncode)

        result = self.run_hook(self.empty, session="s-4")
        self.assertIn("GTM Base is installed", result["systemMessage"])

    # --- what the person reads ----------------------------------------------

    def test_every_sentence_it_prints_reads_plainly(self):
        for sentence in (
            constants.RESTART_SENTENCE,
            offer_answer.SETUP_RECORDS_ITSELF,
            offer_answer.COULD_NOT_WRITE,
        ):
            self.assertEqual([], plain_language.find_banned(sentence), sentence)
            self.assertEqual([], plain_language.find_dashes(sentence), sentence)


if __name__ == "__main__":
    unittest.main()
