"""Unit 2: account state, the one record of what this person joined."""

import datetime
import json
import os
import shutil
import tempfile
import time
import unittest

import support
from support import TempHome, make_base, write

from gtmbase import fsutil, ids, machine, paths
from gtmbase.errors import StateError

SESSION = "6f1c2d34-5678-4abc-9def-0123456789ab"
NOW = datetime.datetime(2026, 9, 5, 14, 3, 0)


class MachineTestCase(unittest.TestCase):
    def setUp(self):
        self.home = TempHome()
        self.home.__enter__()
        self.addCleanup(self.home.__exit__, None, None, None)
        self.work = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-work-"))
        self.addCleanup(shutil.rmtree, self.work, True)

    def base(self, name="gtm-base", base_id=None, remote=None):
        value = base_id or ids.base_id_random()
        root = make_base(os.path.join(self.work, name), base_id=value, remote=remote)
        return os.path.realpath(root), value

    def write_state(self, payload):
        fsutil.atomic_write_json(paths.machine_state_path(), payload)


class TestEmptyAndBrokenState(MachineTestCase):
    def test_no_file_means_nothing_answered_and_nothing_joined(self):
        state = machine.load_machine_state()
        self.assertEqual("unset", state.answer)
        self.assertEqual([], state.joined)
        self.assertEqual([], state.problems)

    def test_a_file_we_cannot_read_is_treated_as_empty_and_reported(self):
        write(paths.machine_state_path(), "{not json")
        state = machine.load_machine_state()
        self.assertEqual("unset", state.answer)
        self.assertEqual([("malformed", -1)], state.problems)

    def test_a_file_that_is_a_link_is_refused(self):
        elsewhere = write(os.path.join(self.work, "elsewhere.json"), json.dumps(
            {"schema": 1, "offer": {"answer": "join"}, "joined": []}
        ))
        os.symlink(elsewhere, paths.machine_state_path())
        state = machine.load_machine_state()
        self.assertEqual("unset", state.answer)
        self.assertEqual([("symlink", -1)], state.problems)

    def test_a_key_we_do_not_know_is_dropped_and_reported(self):
        root, base_id = self.base()
        self.write_state(
            {
                "schema": 1,
                "token": "secret",
                "offer": {"answer": "join", "surprise": 1},
                "joined": [{"root": root, "base_id": base_id, "remote": None, "extra": 2}],
            }
        )
        state = machine.load_machine_state()
        self.assertEqual("join", state.answer)
        self.assertEqual(1, len(state.joined))
        self.assertEqual({"root", "base_id", "remote"}, set(state.joined[0].keys()))
        self.assertIn(("unknown-key", -1), state.problems)
        self.assertIn(("unknown-key", 0), state.problems)

    def test_an_answer_we_do_not_know_is_dropped_and_reported(self):
        self.write_state({"schema": 1, "offer": {"answer": "maybe"}, "joined": []})
        state = machine.load_machine_state()
        self.assertEqual("unset", state.answer)
        self.assertIn(("bad-value", -1), state.problems)


class TestJoinedEntriesAreChecked(MachineTestCase):
    def test_an_entry_that_still_holds_survives(self):
        root, base_id = self.base()
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": root, "base_id": base_id, "remote": None}]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.problems)
        self.assertEqual(root, state.joined[0]["root"])

    def test_an_entry_whose_folder_is_gone_is_dropped_and_reported(self):
        root, base_id = self.base()
        shutil.rmtree(root)
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": root, "base_id": base_id, "remote": None}]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.joined)
        self.assertEqual([("missing-root", 0)], state.problems)

    def test_an_entry_whose_map_is_gone_is_dropped_and_reported(self):
        root, base_id = self.base()
        os.unlink(os.path.join(root, "context", "map.md"))
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": root, "base_id": base_id, "remote": None}]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.joined)
        self.assertEqual([("missing-map", 0)], state.problems)

    def test_an_entry_whose_identifier_does_not_match_is_dropped_and_reported(self):
        root, _base_id = self.base()
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": root, "base_id": ids.base_id_random(), "remote": None}]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.joined)
        self.assertEqual([("id-mismatch", 0)], state.problems)

    def test_an_invented_entry_for_an_ordinary_folder_is_dropped(self):
        ordinary = os.path.join(self.work, "Pictures")
        os.makedirs(ordinary)
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": ordinary, "base_id": ids.base_id_random(), "remote": None}]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.joined)
        self.assertEqual([("missing-git", 0)], state.problems)

    def test_a_relative_path_or_a_bad_identifier_is_dropped(self):
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [
                 {"root": "gtm-base", "base_id": ids.base_id_random(), "remote": None},
                 {"root": self.work, "base_id": "nope", "remote": None},
                 "not a record",
             ]}
        )
        state = machine.load_machine_state()
        self.assertEqual([], state.joined)
        self.assertIn(("bad-value", 0), state.problems)
        self.assertIn(("bad-value", 1), state.problems)
        self.assertIn(("bad-row", 2), state.problems)

    def test_an_address_carrying_a_sign_in_is_dropped_and_reported(self):
        root, base_id = self.base()
        self.write_state(
            {"schema": 1, "offer": {"answer": "set-up"},
             "joined": [{"root": root, "base_id": base_id,
                         "remote": "https://someone:token@github.com/acme/base.git"}]}
        )
        state = machine.load_machine_state()
        self.assertEqual(1, len(state.joined))
        self.assertIsNone(state.joined[0]["remote"])
        self.assertIn(("userinfo", 0), state.problems)


class TestTheOffer(MachineTestCase):
    def test_showing_the_offer_records_the_session_it_was_shown_in(self):
        machine.record_offer_shown(SESSION, NOW)
        state = machine.load_machine_state()
        self.assertEqual("2026-09-05T14:03:00Z", state.offer["shown_at"])
        self.assertTrue(machine.offer_was_shown_this_session(state, SESSION))
        self.assertFalse(machine.offer_was_shown_this_session(state, "another"))

    def test_a_stronger_answer_replaces_a_weaker_one(self):
        machine.record_offer_answer("not-now")
        self.assertEqual("not-now", machine.load_machine_state().answer)
        machine.record_offer_answer("set-up")
        self.assertEqual("set-up", machine.load_machine_state().answer)

    def test_a_weaker_answer_never_replaces_a_stronger_one(self):
        machine.record_offer_answer("set-up")
        machine.record_offer_answer("not-now")
        self.assertEqual("set-up", machine.load_machine_state().answer)
        machine.record_offer_answer("unset")
        self.assertEqual("set-up", machine.load_machine_state().answer)

    def test_setting_up_and_joining_are_the_same_strength(self):
        machine.record_offer_answer("join")
        machine.record_offer_answer("set-up")
        self.assertEqual("set-up", machine.load_machine_state().answer)

    def test_an_answer_we_do_not_record_is_refused(self):
        with self.assertRaises(StateError):
            machine.record_offer_answer("maybe")


class TestTheJoinedList(MachineTestCase):
    def test_a_base_is_appended_once_and_never_twice(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id, "https://github.com/acme/base")
        machine.append_joined(root, base_id, "https://github.com/acme/base")
        state = machine.load_machine_state()
        self.assertEqual(1, len(state.joined))
        self.assertEqual(root, state.joined[0]["root"])
        self.assertEqual("https://github.com/acme/base", state.joined[0]["remote"])

    def test_two_bases_both_stay_in_the_list(self):
        first, first_id = self.base("one")
        second, second_id = self.base("two")
        machine.append_joined(first, first_id)
        machine.append_joined(second, second_id)
        state = machine.load_machine_state()
        self.assertEqual([first, second], [entry["root"] for entry in state.joined])

    def test_a_different_identifier_for_the_same_folder_is_refused(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        with self.assertRaises(StateError) as caught:
            machine.append_joined(root, ids.base_id_random())
        self.assertEqual("id-mismatch", caught.exception.code)

    def test_a_renamed_folder_is_pointed_at_its_new_place(self):
        root, base_id = self.base("Acme-base")
        machine.append_joined(root, base_id)
        moved = os.path.join(self.work, "Acme-renamed")
        os.rename(root, moved)
        machine.rewrite_joined_root(base_id, moved)
        state = machine.load_machine_state()
        self.assertEqual([os.path.realpath(moved)], [entry["root"] for entry in state.joined])

    def test_a_folder_another_base_already_claims_is_refused(self):
        """Two bases can never both be recorded as living in one folder."""
        first, first_id = self.base("first")
        second, second_id = self.base("second")
        machine.append_joined(first, first_id)
        machine.append_joined(second, second_id)

        with self.assertRaises(StateError) as caught:
            machine.rewrite_joined_root(second_id, first)

        self.assertEqual("id-mismatch", caught.exception.code)
        state = machine.load_machine_state()
        self.assertEqual(
            sorted([first, second]), sorted(entry["root"] for entry in state.joined)
        )

    def test_a_base_we_never_joined_cannot_be_pointed_anywhere(self):
        with self.assertRaises(StateError) as caught:
            machine.rewrite_joined_root(ids.base_id_random(), self.work)
        self.assertEqual("unknown-id", caught.exception.code)

    def test_a_base_whose_folder_is_missing_right_now_is_not_lost_by_another_write(self):
        away, away_id = self.base("on-a-drive")
        machine.append_joined(away, away_id)
        here, here_id = self.base("here")
        moved = os.path.join(self.work, "unplugged")
        os.rename(away, moved)

        machine.append_joined(here, here_id)
        os.rename(moved, away)

        state = machine.load_machine_state()
        self.assertEqual(
            sorted([away, here]), sorted(entry["root"] for entry in state.joined)
        )

    def test_the_entries_are_found_by_folder_and_by_identifier(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        state = machine.load_machine_state()
        self.assertIsNotNone(machine.find_joined_by_root(state, root))
        self.assertIsNotNone(machine.find_joined_by_id(state, base_id))
        self.assertIsNone(machine.find_joined_by_id(state, ids.base_id_random()))
        self.assertIsNone(machine.find_joined_by_root(state, self.work))


class TestSaving(MachineTestCase):
    def test_a_sign_in_is_stripped_from_an_address_before_it_is_written(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id, "https://github.com/acme/base.git")
        state = machine.load_machine_state()
        state.joined[0]["remote"] = "https://someone:token@github.com/acme/base.git"
        machine.save_machine_state(state)
        text = support.read(paths.machine_state_path())
        self.assertNotIn("token", text)
        self.assertNotIn("someone", text)
        self.assertEqual(
            "https://github.com/acme/base.git",
            machine.load_machine_state().joined[0]["remote"],
        )

    def test_an_address_that_still_carries_a_sign_in_is_refused(self):
        state = machine.MachineState(
            joined=[{"root": self.work, "base_id": ids.base_id_random(),
                     "remote": "ssh://someone@@github.com/acme/base"}]
        )
        with self.assertRaises(StateError) as caught:
            machine.save_machine_state(state)
        self.assertEqual("userinfo", caught.exception.code)

    def test_the_file_and_the_folder_are_owner_only(self):
        machine.record_offer_answer("not-now")
        self.assertEqual(0o600, os.stat(paths.machine_state_path()).st_mode & 0o777)
        self.assertEqual(0o700, os.stat(paths.seat_home()).st_mode & 0o777)

    def test_a_relative_folder_or_a_bad_identifier_is_never_written(self):
        with self.assertRaises(StateError):
            machine.save_machine_state(
                machine.MachineState(joined=[{"root": "gtm-base", "base_id": "0" * 32}])
            )
        with self.assertRaises(ValueError):
            machine.save_machine_state(
                machine.MachineState(joined=[{"root": self.work, "base_id": "nope"}])
            )


class TestTheLock(MachineTestCase):
    def lock_path(self):
        return os.path.join(paths.seat_home(), machine.LOCK_NAME)

    def test_a_writer_waits_for_the_lock_and_gives_up_saying_so(self):
        handle = os.open(self.lock_path(), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with self.assertRaises(StateError) as caught:
                machine.record_offer_answer("not-now")
            self.assertEqual("locked", caught.exception.code)
        finally:
            os.close(handle)
            os.unlink(self.lock_path())

    def test_a_lock_left_behind_by_a_run_that_died_is_broken(self):
        handle = os.open(self.lock_path(), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(handle)
        old = time.time() - (machine.constants.LOCK_STALE_SECONDS + 30)
        os.utime(self.lock_path(), (old, old))
        machine.record_offer_answer("not-now")
        self.assertEqual("not-now", machine.load_machine_state().answer)
        self.assertFalse(os.path.exists(self.lock_path()))

    def test_the_lock_is_released_after_a_write(self):
        machine.record_offer_answer("not-now")
        self.assertFalse(os.path.exists(self.lock_path()))
        machine.record_offer_answer("set-up")
        self.assertEqual("set-up", machine.load_machine_state().answer)


class TestFixture(unittest.TestCase):
    def test_the_fixture_holds_the_shape_this_module_writes(self):
        payload = json.loads(support.read(os.path.join(support.FIXTURES_DIR, "machine.json")))
        self.assertEqual({"schema", "offer", "joined"}, set(payload.keys()))
        self.assertEqual(set(machine.OFFER_FIELDS), set(payload["offer"].keys()))
        self.assertEqual(set(machine.JOINED_FIELDS), set(payload["joined"][0].keys()))
        self.assertIn(payload["offer"]["answer"], machine.ANSWER_RANK)
        ids.check_base_id(payload["joined"][0]["base_id"])


if __name__ == "__main__":
    unittest.main()
