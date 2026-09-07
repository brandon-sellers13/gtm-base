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
        self.assertEqual(set(machine.JOINED_FIELDS), set(state.joined[0].keys()))
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


class TestTheFolderABaseBelongsWith(MachineTestCase):
    """One folder, one base, decided and written with the lock held."""

    def content(self, name="marketing"):
        path = os.path.join(self.work, name)
        os.makedirs(path)
        return os.path.realpath(path)

    def test_a_folder_is_recorded_and_read_back(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        folder = self.content()

        machine.link_content(base_id, folder)

        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(folder, entry["content_root"])
        self.assertEqual(os.stat(folder).st_ino, entry["content_identity"]["ino"])

    def test_the_base_and_its_folder_are_written_in_one_move(self):
        root, base_id = self.base()
        folder = self.content()

        _state, codes = machine.append_joined(root, base_id, content_root=folder)

        self.assertEqual([], codes)
        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(folder, entry["content_root"])
        self.assertEqual(os.stat(folder).st_ino, entry["content_identity"]["ino"])

    def test_a_refused_folder_still_leaves_the_base_joined(self):
        first_root, first_id = self.base("first")
        second_root, second_id = self.base("second")
        folder = self.content()
        machine.append_joined(first_root, first_id, content_root=folder)

        _state, codes = machine.append_joined(
            second_root, second_id, content_root=folder
        )

        self.assertEqual([machine.CODE_CONTENT_TAKEN], codes)
        entry = machine.find_joined_by_id(machine.load_machine_state(), second_id)
        self.assertIsNotNone(entry)
        self.assertIsNone(entry["content_root"])

    def test_asking_first_says_no_without_writing_anything(self):
        root, base_id = self.base()
        folder = self.content()
        machine.append_joined(root, base_id, content_root=folder)

        with self.assertRaises(StateError) as caught:
            machine.check_content_free(folder)

        self.assertEqual(machine.CODE_CONTENT_TAKEN, caught.exception.code)
        self.assertEqual(root, getattr(caught.exception, "other_root", None))

    def test_asking_first_about_a_free_folder_says_nothing_at_all(self):
        machine.check_content_free(self.content("free"))

    def test_a_folder_can_be_let_go_and_taken_again(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        first = self.content("first")
        second = self.content("second")
        machine.link_content(base_id, first)

        machine.unlink_content(base_id)
        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertIsNone(entry["content_root"])
        self.assertIsNone(entry["content_identity"])

        machine.relink_content(base_id, second)
        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(second, entry["content_root"])

    def test_a_folder_another_base_already_belongs_with_is_refused_by_name(self):
        first, first_id = self.base("first")
        second, second_id = self.base("second")
        machine.append_joined(first, first_id)
        machine.append_joined(second, second_id)
        folder = self.content()
        machine.link_content(first_id, folder)

        with self.assertRaises(StateError) as caught:
            machine.link_content(second_id, folder)

        self.assertEqual(machine.CODE_CONTENT_TAKEN, caught.exception.code)
        self.assertEqual(first, caught.exception.other_root)
        entry = machine.find_joined_by_id(machine.load_machine_state(), second_id)
        self.assertIsNone(entry["content_root"])

    def test_a_folder_a_base_already_belongs_with_is_still_free_to_that_base(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        folder = self.content()
        machine.link_content(base_id, folder)

        machine.link_content(base_id, folder)

        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(folder, entry["content_root"])

    def test_a_base_a_folder_inside_one_and_our_own_records_are_all_refused(self):
        root, base_id = self.base()
        other, other_id = self.base("other")
        machine.append_joined(root, base_id)
        machine.append_joined(other, other_id)

        for folder in (
            other,
            os.path.join(other, "context"),
            paths.seat_home(),
            paths.bases_dir(),
        ):
            with self.assertRaises(StateError, msg=folder) as caught:
                machine.link_content(base_id, folder)
            self.assertEqual(
                machine.CODE_CONTENT_INSIDE_BASE, caught.exception.code, folder
            )

    def test_a_folder_another_base_sits_directly_inside_is_refused(self):
        """An association that could never fire is refused rather than written."""
        parent = os.path.join(self.work, "Acme")
        os.makedirs(parent)
        inner = os.path.realpath(
            make_base(os.path.join(parent, "gtm-base"), base_id=ids.base_id_random())
        )
        inner_id = ids.base_id_random()
        support.git(["config", "--local", "gtmbase.id", inner_id], cwd=inner)
        machine.append_joined(inner, inner_id)
        elsewhere, elsewhere_id = self.base("elsewhere")
        machine.append_joined(elsewhere, elsewhere_id)

        with self.assertRaises(StateError) as caught:
            machine.link_content(elsewhere_id, parent)
        self.assertEqual(machine.CODE_CONTENT_INSIDE_BASE, caught.exception.code)

    def test_a_link_through_a_link_binds_the_folder_it_points_at(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        real = self.content("real")
        shortcut = os.path.join(self.work, "shortcut")
        os.symlink(real, shortcut)

        machine.link_content(base_id, shortcut)

        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(real, entry["content_root"])

    def test_a_folder_that_is_not_there_is_refused(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)

        with self.assertRaises(StateError) as caught:
            machine.link_content(base_id, os.path.join(self.work, "nowhere"))
        self.assertEqual("not-a-folder", caught.exception.code)

    def test_a_base_this_account_never_joined_cannot_be_pointed_at_a_folder(self):
        with self.assertRaises(StateError) as caught:
            machine.link_content(ids.base_id_random(), self.work)
        self.assertEqual("unknown-id", caught.exception.code)

    def test_two_windows_cannot_both_claim_one_folder(self):
        """The second writer waits for the lock, then sees the first one's claim."""
        import threading

        first, first_id = self.base("first")
        second, second_id = self.base("second")
        machine.append_joined(first, first_id)
        machine.append_joined(second, second_id)
        folder = self.content()

        started = threading.Event()
        release = threading.Event()
        outcome = {}

        def slow_writer():
            handle = machine._acquire_lock()
            started.set()
            try:
                release.wait(5)
                state = machine._load(None, False)
                entry = machine.find_joined_by_id(state, first_id)
                taken = machine.folder_identity.capture(folder)
                entry["content_root"] = taken.path
                entry["content_identity"] = taken.as_dict()
                machine._write_payload(machine._checked_payload(state))
            finally:
                machine._release_lock(handle)

        worker = threading.Thread(target=slow_writer)
        worker.start()
        started.wait(5)
        release.set()
        worker.join(10)

        try:
            machine.link_content(second_id, folder)
            outcome["code"] = None
        except StateError as refusal:
            outcome["code"] = refusal.code

        self.assertEqual(machine.CODE_CONTENT_TAKEN, outcome["code"])
        state = machine.load_machine_state()
        holders = [
            entry["base_id"]
            for entry in state.joined
            if entry.get("content_root") == folder
        ]
        self.assertEqual([first_id], holders)


class TestFollowingAFolderThatWasRenamed(MachineTestCase):
    def test_the_new_path_is_written_when_nothing_moved_underneath(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        folder = os.path.join(self.work, "marketing")
        os.makedirs(folder)
        machine.link_content(base_id, folder)
        moved = os.path.join(self.work, "renamed")
        os.rename(folder, moved)

        machine.rewrite_content_root(base_id, moved, os.path.realpath(folder))

        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(os.path.realpath(moved), entry["content_root"])

    def test_a_rename_worked_out_from_stale_state_never_overwrites(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        first = os.path.join(self.work, "first")
        second = os.path.join(self.work, "second")
        os.makedirs(first)
        os.makedirs(second)
        machine.link_content(base_id, first)
        machine.relink_content(base_id, second)

        with self.assertRaises(StateError) as caught:
            machine.rewrite_content_root(
                base_id, os.path.join(self.work, "third"), os.path.realpath(first)
            )

        self.assertEqual(machine.CODE_STALE_LINK, caught.exception.code)
        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(os.path.realpath(second), entry["content_root"])


class TestALinkWeCannotRead(MachineTestCase):
    def test_a_malformed_link_is_turned_off_and_the_base_is_kept(self):
        root, base_id = self.base()
        self.write_state(
            {
                "schema": 1,
                "offer": {"answer": "set-up"},
                "joined": [
                    {
                        "root": root,
                        "base_id": base_id,
                        "remote": None,
                        "content_root": "/Users/example/Acme",
                        "content_identity": {"dev": "one", "ino": 2},
                    }
                ],
            }
        )

        state = machine.load_machine_state()

        self.assertEqual(1, len(state.joined))
        self.assertEqual(root, state.joined[0]["root"])
        self.assertIsNone(state.joined[0]["content_root"])
        self.assertIn(("bad-link", 0), state.problems)

    def test_a_folder_with_no_evidence_beside_it_is_turned_off(self):
        root, base_id = self.base()
        self.write_state(
            {
                "schema": 1,
                "offer": {"answer": "set-up"},
                "joined": [
                    {
                        "root": root,
                        "base_id": base_id,
                        "remote": None,
                        "content_root": "/Users/example/Acme",
                    }
                ],
            }
        )

        state = machine.load_machine_state()

        self.assertIsNone(state.joined[0]["content_root"])
        self.assertIn(("bad-link", 0), state.problems)

    def test_an_entry_from_before_this_release_loads_unchanged(self):
        root, base_id = self.base()
        self.write_state(
            {
                "schema": 1,
                "offer": {"answer": "set-up"},
                "joined": [{"root": root, "base_id": base_id, "remote": None}],
            }
        )

        state = machine.load_machine_state()

        self.assertEqual([], state.problems)
        self.assertEqual(root, state.joined[0]["root"])
        self.assertIsNone(state.joined[0]["content_root"])

    def test_a_folder_that_is_not_plugged_in_survives_an_unrelated_write(self):
        root, base_id = self.base()
        machine.append_joined(root, base_id)
        away = os.path.join(self.work, "on-a-drive")
        os.makedirs(away)
        machine.link_content(base_id, away)
        shutil.rmtree(away)

        machine.record_offer_answer("set-up")

        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(os.path.realpath(away), entry["content_root"])

    def test_half_a_link_is_never_written_down(self):
        root, base_id = self.base()
        state = machine.MachineState(
            joined=[
                {
                    "root": root,
                    "base_id": base_id,
                    "remote": None,
                    "content_root": "/Users/example/Acme",
                    "content_identity": None,
                }
            ]
        )
        with self.assertRaises(StateError) as caught:
            machine.save_machine_state(state)
        self.assertEqual("bad-value", caught.exception.code)


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
