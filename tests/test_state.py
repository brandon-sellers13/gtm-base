"""Unit 2: what one seat remembers, and what it refuses to remember."""

import datetime
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import support
from support import TempHome, make_base

from gtmbase import constants, fsutil, ids, paths, state
from gtmbase.errors import StateError

BASE_ID = "0123456789abcdef0123456789abcdef"
SOURCE = "src-" + "0" * 24
OTHER_SOURCE = "src-" + "1" * 24
SESSION = "6f1c2d34-5678-4abc-9def-0123456789ab"
NOW = datetime.datetime(2026, 9, 5, 14, 3, 0)
TODAY = datetime.date(2026, 9, 5)


class SeatTestCase(unittest.TestCase):
    def setUp(self):
        self.home = TempHome()
        self.home.__enter__()
        self.addCleanup(self.home.__exit__, None, None, None)


class TestTimestamps(SeatTestCase):
    def test_every_time_is_written_the_same_way_and_reads_back(self):
        text = state.iso_utc(NOW)
        self.assertEqual("2026-09-05T14:03:00Z", text)
        self.assertEqual(NOW, state.parse_iso_utc(text))
        self.assertIsNone(state.parse_iso_utc("2026-09-05 14:03"))


class TestInboxIndex(SeatTestCase):
    def test_rows_are_added_updated_and_read_back(self):
        state.upsert_row(
            BASE_ID, SOURCE, status="landed", landed_at=state.iso_utc(NOW),
            source="fireflies", intake_path="drop", visibility="private-channel",
        )
        index, problems = state.load_index(BASE_ID)
        self.assertEqual([], problems)
        self.assertEqual("landed", index[SOURCE]["status"])
        self.assertEqual([], index[SOURCE]["staging_ids"])

        state.set_status(BASE_ID, SOURCE, "processed")
        index, _problems = state.load_index(BASE_ID)
        self.assertEqual("processed", index[SOURCE]["status"])
        self.assertEqual("fireflies", index[SOURCE]["source"])

    def test_a_status_we_do_not_know_is_refused(self):
        with self.assertRaises(StateError):
            state.set_status(BASE_ID, SOURCE, "finished")
        with self.assertRaises(StateError):
            state.upsert_row(BASE_ID, SOURCE, unknown_field="x")

    def test_unprocessed_rows_come_back_oldest_first(self):
        state.upsert_row(BASE_ID, OTHER_SOURCE, status="landed", landed_at="2026-09-01T00:00:00Z")
        state.upsert_row(BASE_ID, SOURCE, status="landed", landed_at="2026-09-04T00:00:00Z")
        state.upsert_row(BASE_ID, "src-" + "2" * 24, status="closed")
        rows = state.unprocessed_rows(BASE_ID)
        self.assertEqual([OTHER_SOURCE, SOURCE], [row["source_id"] for row in rows])

    def test_a_row_whose_file_is_gone_is_reported(self):
        folder = tempfile.mkdtemp(prefix="gtm-base-root-")
        self.addCleanup(shutil.rmtree, folder, True)
        os.makedirs(os.path.join(folder, constants.INBOX_DIR))
        support.write(os.path.join(folder, constants.INBOX_DIR, SOURCE + ".md"), "here\n")
        state.upsert_row(BASE_ID, SOURCE, status="landed")
        state.upsert_row(BASE_ID, OTHER_SOURCE, status="landed")
        missing = state.rows_with_missing_files(BASE_ID, folder)
        self.assertEqual([OTHER_SOURCE], [row["source_id"] for row in missing])

    def test_a_row_we_cannot_read_is_reported_and_the_others_survive(self):
        state.upsert_row(BASE_ID, SOURCE, status="landed")
        path = os.path.join(paths.seat_dir(BASE_ID), state.INBOX_INDEX_FILE)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("this is not a record\n")
            handle.write(json.dumps({"source_id": "nope", "status": "landed"}) + "\n")
            handle.write(json.dumps({"source_id": OTHER_SOURCE, "status": "landed", "x": 1}) + "\n")
        index, problems = state.load_index(BASE_ID)
        self.assertEqual({SOURCE, OTHER_SOURCE}, set(index.keys()))
        self.assertIn("bad-row", problems)
        self.assertIn("unknown-key", problems)

    def test_an_interrupted_write_leaves_the_previous_index_untouched(self):
        state.upsert_row(BASE_ID, SOURCE, status="landed")
        path = os.path.join(paths.seat_dir(BASE_ID), state.INBOX_INDEX_FILE)
        before = support.read(path)

        with mock.patch.object(fsutil.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                state.upsert_row(BASE_ID, OTHER_SOURCE, status="landed")

        self.assertEqual(before, support.read(path))
        index, problems = state.load_index(BASE_ID)
        self.assertEqual([SOURCE], list(index.keys()))
        self.assertEqual([], problems)
        leftovers = [
            name
            for name in os.listdir(paths.seat_dir(BASE_ID))
            if name.startswith(".gtmbase-")
        ]
        self.assertEqual([], leftovers)


class TestSeatState(SeatTestCase):
    def test_the_defaults_are_returned_when_there_is_no_file(self):
        seat, problems = state.load_seat(BASE_ID)
        self.assertEqual([], problems)
        self.assertIsNone(seat["client"])
        self.assertFalse(seat["first_push_reviewed"])
        self.assertNotIn("joined", seat)

    def test_values_are_written_and_read_back(self):
        state.update_seat(BASE_ID, client="claude", session_id=SESSION, first_push_reviewed=True)
        seat, problems = state.load_seat(BASE_ID)
        self.assertEqual([], problems)
        self.assertEqual("claude", seat["client"])
        self.assertEqual(SESSION, seat["session_id"])
        self.assertTrue(seat["first_push_reviewed"])

    def test_a_key_we_do_not_know_is_dropped_and_reported(self):
        path = os.path.join(paths.seat_dir(BASE_ID), state.SEAT_FILE)
        fsutil.atomic_write_json(path, {"client": "claude", "joined": True, "token": "x"})
        seat, problems = state.load_seat(BASE_ID)
        self.assertEqual("claude", seat["client"])
        self.assertNotIn("joined", seat)
        self.assertNotIn("token", seat)
        self.assertEqual(["unknown-key", "unknown-key"], problems)

    def test_a_file_we_cannot_read_is_treated_as_empty_and_reported(self):
        path = os.path.join(paths.seat_dir(BASE_ID), state.SEAT_FILE)
        support.write(path, "{not json")
        seat, problems = state.load_seat(BASE_ID)
        self.assertEqual(["malformed"], problems)
        self.assertIsNone(seat["client"])

    def test_a_value_we_do_not_allow_is_dropped_and_reported(self):
        path = os.path.join(paths.seat_dir(BASE_ID), state.SEAT_FILE)
        fsutil.atomic_write_json(
            path,
            {"client": "emacs", "first_push_reviewed": "yes", "git_hook_code": "whatever"},
        )
        seat, problems = state.load_seat(BASE_ID)
        self.assertIsNone(seat["client"])
        self.assertFalse(seat["first_push_reviewed"])
        self.assertIsNone(seat["git_hook_code"])
        self.assertEqual(3, problems.count("bad-value"))

    def test_only_a_fixed_code_may_be_recorded_as_detail(self):
        state.update_seat(BASE_ID, git_hook_code="hook-chained")
        seat, _problems = state.load_seat(BASE_ID)
        self.assertEqual("hook-chained", seat["git_hook_code"])
        with self.assertRaises(StateError):
            state.update_seat(BASE_ID, git_hook_code="could not write /Users/jane/.git/hooks")

    def test_a_hostile_value_is_stored_as_a_code_and_never_as_itself(self):
        hostile = [
            "https://someone:token@github.com/acme/base.git",
            "ghp_0123456789abcdefghijklmnopqrstuvwxyz",
            "AKIAIOSFODNN7EXAMPLE",
            "eyJhbGciOiJIUzI1NiJ9aGVsbG8gdGhlcmUgZnJpZW5k1234",
        ]
        for value in hostile:
            state.update_seat(BASE_ID, vendor_substring=value)
            seat, _problems = state.load_seat(BASE_ID)
            self.assertEqual("redacted", seat["vendor_substring"], value)
        text = support.read(os.path.join(paths.seat_dir(BASE_ID), state.SEAT_FILE))
        self.assertNotIn("://", text)
        self.assertNotIn("ghp_", text)
        self.assertNotIn("AKIA", text)

    def test_an_ordinary_value_is_kept_as_it_is(self):
        state.update_seat(
            BASE_ID, vendor_substring="fireflies", last_seen_commit="9f2c1b0a" * 5
        )
        seat, _problems = state.load_seat(BASE_ID)
        self.assertEqual("fireflies", seat["vendor_substring"])
        self.assertEqual("9f2c1b0a" * 5, seat["last_seen_commit"])


class TestQuestionIds(SeatTestCase):
    def issue(self, now=NOW, session=SESSION):
        return state.issue_question_id(
            BASE_ID, "context/strategy/icp.md", "ledger", session,
            entry_id="stg-" + "0" * 16, now=now,
        )

    def test_a_question_id_is_used_once_and_refused_after_that(self):
        question = self.issue()
        ids.check_question_id(question)
        self.assertEqual((True, "ok"), state.consume_question_id(BASE_ID, question, SESSION, NOW))
        self.assertEqual(
            (False, "consumed"), state.consume_question_id(BASE_ID, question, SESSION, NOW)
        )

    def test_a_question_id_from_another_session_is_refused(self):
        question = self.issue()
        self.assertEqual(
            (False, "wrong-session"),
            state.consume_question_id(BASE_ID, question, "another-session", NOW),
        )

    def test_a_question_id_older_than_the_window_is_refused(self):
        question = self.issue()
        later = NOW + datetime.timedelta(seconds=constants.QUESTION_ID_WINDOW_SECONDS + 1)
        self.assertEqual(
            (False, "too-old"), state.consume_question_id(BASE_ID, question, SESSION, later)
        )

    def test_an_id_we_never_issued_is_refused(self):
        self.assertEqual(
            (False, "unknown-id"),
            state.consume_question_id(BASE_ID, "q-" + "0" * 20, SESSION, NOW),
        )

    def test_ids_older_than_the_keep_window_are_thrown_away(self):
        old = self.issue(now=NOW - datetime.timedelta(days=constants.QUESTION_ID_KEEP_DAYS + 1))
        fresh = self.issue()
        kept = state.prune_question_ids(BASE_ID, NOW)
        self.assertEqual([fresh], [record["id"] for record in kept])
        self.assertEqual(
            (False, "unknown-id"), state.consume_question_id(BASE_ID, old, SESSION, NOW)
        )


class TestAskedLog(SeatTestCase):
    def test_a_question_is_recorded_unanswered_and_the_answer_is_filled_in_later(self):
        question = "q-" + "a" * 20
        state.append_asked(BASE_ID, question, "context/strategy/icp.md", "ledger", day=TODAY)
        rows, problems = state.load_asked(BASE_ID)
        self.assertEqual([], problems)
        self.assertEqual("unanswered", rows[0]["outcome"])
        self.assertEqual("2026-09-05", rows[0]["date"])

        self.assertTrue(state.set_outcome(BASE_ID, question, "yes"))
        rows, _problems = state.load_asked(BASE_ID)
        self.assertEqual("yes", rows[0]["outcome"])
        self.assertFalse(state.set_outcome(BASE_ID, "q-" + "b" * 20, "yes"))

    def test_an_answer_we_do_not_record_is_refused(self):
        with self.assertRaises(StateError):
            state.append_asked(BASE_ID, "q-" + "a" * 20, "context/x.md", "ledger", "maybe")
        with self.assertRaises(StateError):
            state.set_outcome(BASE_ID, "q-" + "a" * 20, "maybe")


class TestSuppressions(SeatTestCase):
    def test_a_file_is_left_alone_until_the_day_it_comes_back(self):
        path = "context/strategy/icp.md"
        state.suppress(BASE_ID, path, datetime.date(2026, 9, 12))
        self.assertTrue(state.is_suppressed(BASE_ID, path, datetime.date(2026, 9, 5)))
        self.assertTrue(state.is_suppressed(BASE_ID, path, datetime.date(2026, 9, 11)))
        self.assertFalse(state.is_suppressed(BASE_ID, path, datetime.date(2026, 9, 12)))
        self.assertFalse(state.is_suppressed(BASE_ID, path, datetime.date(2026, 9, 20)))
        self.assertFalse(state.is_suppressed(BASE_ID, "context/plan/goals.md", TODAY))

    def test_a_date_we_cannot_read_is_dropped_and_reported(self):
        path = os.path.join(paths.seat_dir(BASE_ID), state.SUPPRESSIONS_FILE)
        fsutil.atomic_write_json(path, {"schema": 1, "files": {"context/x.md": "soon"}})
        files, problems = state.load_suppressions(BASE_ID)
        self.assertEqual({}, files)
        self.assertEqual(["bad-value"], problems)


class TestDismissals(SeatTestCase):
    def test_an_item_is_dismissed_and_stays_dismissed(self):
        state.dismiss_inbox_item(BASE_ID, SOURCE)
        state.dismiss_inbox_item(BASE_ID, SOURCE)
        value, problems = state.load_dismissals(BASE_ID)
        self.assertEqual([SOURCE], value["inbox_ids"])
        self.assertEqual([], problems)
        self.assertTrue(state.is_dismissed(BASE_ID, SOURCE))
        self.assertFalse(state.is_dismissed(BASE_ID, OTHER_SOURCE))

    def test_the_ledger_reminder_can_be_put_off_to_a_date(self):
        state.set_ledger_behind_dismissed_until(BASE_ID, datetime.date(2026, 10, 1))
        value, _problems = state.load_dismissals(BASE_ID)
        self.assertEqual("2026-10-01", value["ledger_behind_dismissed_until"])


class TestDroppedPaths(SeatTestCase):
    def test_a_refused_path_is_recorded_by_its_hash_and_never_by_its_name(self):
        state.append_dropped_path(
            BASE_ID, "../../Users/jane/.ssh/id_rsa", "dropped-path",
            entry_id="stg-" + "0" * 16, day=TODAY,
        )
        rows, problems = state.load_dropped_paths(BASE_ID)
        self.assertEqual([], problems)
        self.assertEqual(1, len(rows))
        self.assertEqual(ids.path_hash("../../Users/jane/.ssh/id_rsa"), rows[0]["path_hash"])
        text = support.read(os.path.join(paths.seat_dir(BASE_ID), state.DROPPED_PATHS_FILE))
        self.assertNotIn("id_rsa", text)
        self.assertNotIn("jane", text)

    def test_only_a_fixed_code_may_be_recorded(self):
        with self.assertRaises(StateError):
            state.append_dropped_path(BASE_ID, "x", "it went outside the base")


class TestCaptureMarker(SeatTestCase):
    def test_arming_writes_the_marker_and_the_sentinel_together(self):
        state.arm_capture(BASE_ID, SESSION, "fireflies", ["01HZX9"], now=NOW)
        self.assertTrue(state.is_armed())
        marker, code = state.read_capture_marker(BASE_ID, NOW)
        self.assertEqual("ok", code)
        self.assertEqual(SESSION, marker["session_id"])
        self.assertEqual(["01HZX9"], marker["selected_ids"])

    def test_an_expired_marker_is_deleted_and_reported(self):
        state.arm_capture(BASE_ID, SESSION, "fireflies", ["01HZX9"], now=NOW)
        later = NOW + datetime.timedelta(seconds=constants.CAPTURE_MARKER_EXPIRY_SECONDS + 1)
        marker, code = state.read_capture_marker(BASE_ID, later)
        self.assertIsNone(marker)
        self.assertEqual("expired", code)
        self.assertFalse(state.is_armed())
        self.assertFalse(
            os.path.exists(os.path.join(paths.seat_dir(BASE_ID), state.CAPTURE_MARKER_FILE))
        )

    def test_a_marker_we_cannot_read_is_deleted_and_reported(self):
        state.arm_capture(BASE_ID, SESSION, "fireflies", ["01HZX9"], now=NOW)
        support.write(
            os.path.join(paths.seat_dir(BASE_ID), state.CAPTURE_MARKER_FILE), "{not json"
        )
        marker, code = state.read_capture_marker(BASE_ID, NOW)
        self.assertIsNone(marker)
        self.assertEqual("malformed", code)
        self.assertFalse(state.is_armed())

    def test_a_marker_missing_a_field_is_treated_as_disarmed(self):
        state.arm_capture(BASE_ID, SESSION, "fireflies", [], now=NOW)
        path = os.path.join(paths.seat_dir(BASE_ID), state.CAPTURE_MARKER_FILE)
        fsutil.atomic_write_json(path, {"session_id": SESSION})
        marker, code = state.read_capture_marker(BASE_ID, NOW)
        self.assertIsNone(marker)
        self.assertEqual("malformed", code)

    def test_nothing_armed_reads_as_nothing(self):
        marker, code = state.read_capture_marker(BASE_ID, NOW)
        self.assertIsNone(marker)
        self.assertEqual("missing-file", code)
        self.assertFalse(state.is_armed())


class TestFileModes(SeatTestCase):
    def test_every_state_file_is_owner_only_and_every_folder_too(self):
        state.upsert_row(BASE_ID, SOURCE, status="landed")
        state.update_seat(BASE_ID, client="claude")
        state.issue_question_id(BASE_ID, "context/strategy/icp.md", "ledger", SESSION, now=NOW)
        state.append_asked(BASE_ID, "q-" + "a" * 20, "context/strategy/icp.md", "ledger")
        state.suppress(BASE_ID, "context/strategy/icp.md", TODAY)
        state.dismiss_inbox_item(BASE_ID, SOURCE)
        state.append_dropped_path(BASE_ID, "../x", "dropped-path")
        state.arm_capture(BASE_ID, SESSION, "fireflies", [], now=NOW)

        seat = paths.seat_dir(BASE_ID)
        self.assertEqual(0o700, os.stat(seat).st_mode & 0o777)
        self.assertEqual(0o700, os.stat(paths.seat_home()).st_mode & 0o777)
        names = os.listdir(seat)
        self.assertEqual(8, len([name for name in names if os.path.isfile(os.path.join(seat, name))]))
        for name in names:
            path = os.path.join(seat, name)
            if os.path.isfile(path):
                self.assertEqual(0o600, os.stat(path).st_mode & 0o777, name)
        self.assertEqual(0o600, os.stat(paths.armed_sentinel_path()).st_mode & 0o777)

    def test_no_state_file_carries_a_sign_in_or_a_key(self):
        state.update_seat(
            BASE_ID,
            vendor_substring="https://someone:token@github.com/acme/base.git",
            pending_confirmation_line="ghp_0123456789abcdefghijklmnop",
        )
        state.upsert_row(BASE_ID, SOURCE, status="landed", source="https://x:y@z/w")
        seat = paths.seat_dir(BASE_ID)
        for name in os.listdir(seat):
            path = os.path.join(seat, name)
            if not os.path.isfile(path):
                continue
            text = support.read(path)
            self.assertNotIn("://", text, name)
            self.assertNotIn("ghp_", text, name)


class TestCodes(unittest.TestCase):
    def test_every_code_is_a_short_word_with_a_plain_meaning(self):
        for code, meaning in state.CODES.items():
            self.assertRegex(code, r"^[a-z][a-z-]{1,40}$")
            self.assertTrue(meaning[0].islower(), code)
        self.assertIsNone(state.check_code(None))
        self.assertEqual("expired", state.check_code("expired"))
        with self.assertRaises(StateError):
            state.check_code("anything else")


if __name__ == "__main__":
    unittest.main()
