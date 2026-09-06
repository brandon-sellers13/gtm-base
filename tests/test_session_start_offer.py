"""Unit 3: the setup offer the first session on an account shows on screen."""

import datetime
import json
import os
import sys
import threading
import time
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
from gtmbase import constants, ids, machine, session_start  # noqa: E402

NOW = datetime.datetime(2026, 9, 5, 12, 0, 0)
A_MONTH_LATER = datetime.datetime(2026, 10, 5, 12, 0, 0)


class OfferTest(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.elsewhere = os.path.join(self.sandbox.path, "an-unrelated-project")
        support.write(os.path.join(self.elsewhere, "notes.txt"), "hello\n")
        self.empty = os.path.join(self.sandbox.path, "an-empty-folder")
        os.makedirs(self.empty)

    def run_hook(self, cwd, source="startup", session="s-1", now=None, part="both"):
        return session_start.run(
            {"session_id": session, "source": source, "cwd": cwd},
            client="claude",
            now=now or NOW,
            plugin_root=PLUGIN_DIR,
            part=part,
        )

    def seat_files(self):
        """Every file this seat wrote, for the checks that read all of them."""
        found = []
        for dirpath, _dirnames, filenames in os.walk(os.environ["GTM_BASE_HOME"]):
            for name in filenames:
                found.append(os.path.join(dirpath, name))
        return found

    # --- the two parts ------------------------------------------------------

    def test_the_visible_part_offers_a_base_and_writes_nothing(self):
        result = self.run_hook(self.elsewhere, part="visible")
        self.assertEqual(["systemMessage"], list(result.keys()))
        self.assertIn("GTM Base is installed", result["systemMessage"])
        self.assertIn(constants.RESTART_SENTENCE, result["systemMessage"])

        self.assertEqual([], self.seat_files())
        self.assertIsNone(machine.load_machine_state().offer["shown_at"])

    def test_the_context_part_primes_the_assistant_as_plain_text_and_records(self):
        self.run_hook(self.elsewhere, part="visible")
        result = self.run_hook(self.elsewhere, part="context")

        self.assertIsInstance(result, str)
        self.assertFalse(result.lstrip().startswith("{"), result[:80])
        self.assertIn("setup offer", result)
        self.assertLessEqual(len(result), constants.MAX_INJECTION_CHARS)

        state = machine.load_machine_state()
        self.assertEqual("s-1", state.offer["shown_session_id"])
        self.assertTrue(state.offer["shown_at"])
        self.assertEqual("unset", state.answer)

    def test_a_second_pair_in_the_same_session_says_nothing_in_either_part(self):
        self.run_hook(self.elsewhere, part="visible")
        self.run_hook(self.elsewhere, part="context")

        for part in ("visible", "context"):
            self.assertIsNone(
                self.run_hook(self.elsewhere, source="resume", part=part), part
            )

    def test_the_offer_is_shown_whichever_part_the_client_runs_first(self):
        """The client runs the two parts at the same time rather than one after
        the other, so the part that prints what a person sees must not go quiet
        because the other part recorded this session a moment earlier."""
        self.run_hook(self.elsewhere, part="context")
        result = self.run_hook(self.elsewhere, part="visible")
        self.assertIn("GTM Base is installed", result["systemMessage"])

    # --- the first session --------------------------------------------------

    def test_a_fresh_account_is_offered_a_base_once_per_session(self):
        result = self.run_hook(self.elsewhere)
        self.assertIn("GTM Base is installed", result["systemMessage"])
        self.assertIn(constants.RESTART_SENTENCE, result["systemMessage"])
        self.assertIn(
            "setup offer", result["hookSpecificOutput"]["additionalContext"]
        )

        state = machine.load_machine_state()
        self.assertEqual("s-1", state.offer["shown_session_id"])
        self.assertTrue(state.offer["shown_at"])
        self.assertEqual("unset", state.answer)

        self.assertIsNone(self.run_hook(self.elsewhere, source="resume"))

    def test_an_unanswered_offer_does_not_follow_the_person_around(self):
        self.run_hook(self.elsewhere)
        self.assertIsNone(self.run_hook(self.elsewhere, session="s-2"))

    def test_an_unanswered_offer_comes_back_in_an_empty_folder(self):
        self.run_hook(self.elsewhere)
        result = self.run_hook(self.empty, session="s-2")
        self.assertIn("GTM Base is installed", result["systemMessage"])
        self.assertEqual("s-2", machine.load_machine_state().offer["shown_session_id"])

    def test_a_folder_that_looks_like_a_base_gets_the_question_not_the_offer(self):
        self.run_hook(self.elsewhere)
        root = support.trust_checkout(self.sandbox.path, name="acme")
        result = self.run_hook(root, session="s-2")
        self.assertIn("This folder looks like a company base", result["systemMessage"])
        self.assertNotIn("GTM Base is installed", result["systemMessage"])
        self.assertEqual("s-1", machine.load_machine_state().offer["shown_session_id"])

    def test_after_not_now_an_unrelated_folder_stays_quiet_a_month_later(self):
        self.run_hook(self.elsewhere)
        machine.record_offer_answer("not-now")
        self.assertIsNone(
            self.run_hook(self.elsewhere, session="s-2", now=A_MONTH_LATER)
        )
        result = self.run_hook(self.empty, session="s-3", now=A_MONTH_LATER)
        self.assertIn("GTM Base is installed", result["systemMessage"])

    def test_an_account_that_already_has_a_base_is_never_offered_another(self):
        root = os.path.join(self.sandbox.path, "base")
        base_id = ids.base_id_random()
        support.make_base(root, base_id=base_id)
        machine.append_joined(root=root, base_id=base_id)

        self.assertIsNone(self.run_hook(self.elsewhere))
        self.assertIsNone(self.run_hook(self.empty, session="s-2"))
        self.assertIsNone(machine.load_machine_state().offer["shown_at"])

    def test_the_offer_is_only_shown_when_a_session_begins(self):
        for source in ("compact", "clear", "fork"):
            self.assertIsNone(self.run_hook(self.elsewhere, source=source))
        self.assertIsNone(machine.load_machine_state().offer["shown_at"])

    # --- two windows at once ------------------------------------------------

    def test_two_sessions_starting_together_do_not_lose_a_thing(self):
        """One holds the lock while the other runs; both records survive."""
        root = os.path.join(self.sandbox.path, "base")
        base_id = ids.base_id_random()
        support.make_base(root, base_id=base_id)

        lock = os.path.join(os.environ["GTM_BASE_HOME"], "machine.lock")
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        with open(lock, "w") as handle:
            handle.write("held")

        def release():
            time.sleep(0.4)
            os.unlink(lock)

        releaser = threading.Thread(target=release)
        releaser.start()
        started = time.time()
        result = self.run_hook(self.elsewhere)
        releaser.join()

        self.assertGreater(time.time() - started, 0.3)
        self.assertIn("GTM Base is installed", result["systemMessage"])
        state = machine.load_machine_state()
        self.assertEqual("s-1", state.offer["shown_session_id"])

        machine.append_joined(root=root, base_id=base_id)
        after = machine.load_machine_state()
        self.assertEqual("s-1", after.offer["shown_session_id"])
        self.assertEqual(1, len(after.joined))

    # --- what the person reads ----------------------------------------------

    def test_the_offer_reads_plainly_and_carries_no_web_address(self):
        result = self.run_hook(self.elsewhere)
        for text in (
            result["systemMessage"],
            result["hookSpecificOutput"]["additionalContext"],
        ):
            self.assertEqual([], plain_language.find_banned(text))
            self.assertEqual([], plain_language.find_dashes(text))
            self.assertNotIn("://", text)
        payload = json.dumps(result)
        self.assertLessEqual(
            len(result["hookSpecificOutput"]["additionalContext"]),
            constants.MAX_INJECTION_CHARS,
        )
        self.assertNotIn("GTM_BASE_HOME", payload)


if __name__ == "__main__":
    unittest.main()
