"""The marker that says this session already read the person's own documents."""

import json
import os
import time
import unittest

import support
from support import Sandbox, write

from gtmbase import constants, marker


class TestWritingTheMarker(unittest.TestCase):
    def test_writing_records_the_session_and_the_moment(self):
        with Sandbox():
            path = marker.write_sources_read_marker("session-1")
            self.assertTrue(os.path.isfile(path))
            payload = json.loads(support.read(path))
            self.assertEqual("session-1", payload["session_id"])
            self.assertTrue(payload["written_at"].endswith("Z"))

    def test_the_marker_is_owner_only(self):
        with Sandbox():
            path = marker.write_sources_read_marker("session-1")
            self.assertEqual(0o600, os.stat(path).st_mode & 0o777)

    def test_a_marker_needs_a_session_to_belong_to(self):
        with Sandbox():
            for bad in ("", "   ", None, 7):
                self.assertRaises(
                    ValueError, marker.write_sources_read_marker, bad
                )

    def test_the_session_is_trimmed_before_it_is_recorded(self):
        with Sandbox():
            marker.write_sources_read_marker("  session-1  ")
            self.assertTrue(marker.marker_matches_session("session-1"))


class TestReadingTheMarker(unittest.TestCase):
    def test_no_marker_reads_as_nothing(self):
        with Sandbox():
            self.assertIsNone(marker.read_sources_read_marker())
            self.assertFalse(marker.marker_matches_session("session-1"))

    def test_only_the_session_that_read_is_matched(self):
        with Sandbox():
            marker.write_sources_read_marker("session-1")
            self.assertTrue(marker.marker_matches_session("session-1"))
            self.assertFalse(marker.marker_matches_session("session-2"))
            self.assertFalse(marker.marker_matches_session(None))

    def test_a_malformed_marker_reads_as_nothing(self):
        with Sandbox():
            marker.write_sources_read_marker("session-1")
            write(marker.marker_path(), "not a marker at all")
            self.assertIsNone(marker.read_sources_read_marker())

    def test_a_marker_with_no_session_reads_as_nothing(self):
        with Sandbox():
            marker.write_sources_read_marker("session-1")
            write(marker.marker_path(), json.dumps({"written_at": "2026-01-01Z"}))
            self.assertIsNone(marker.read_sources_read_marker())

    def test_a_marker_that_is_a_link_reads_as_nothing(self):
        with Sandbox() as box:
            real = os.path.join(box.path, "elsewhere.json")
            write(real, json.dumps({"session_id": "session-1"}))
            path = marker.marker_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.symlink(real, path)
            self.assertIsNone(marker.read_sources_read_marker())


class TestClearingTheMarker(unittest.TestCase):
    def test_clearing_says_whether_there_was_one(self):
        with Sandbox():
            self.assertFalse(marker.clear_sources_read_marker())
            marker.write_sources_read_marker("session-1")
            self.assertTrue(marker.clear_sources_read_marker())
            self.assertIsNone(marker.read_sources_read_marker())


class TestTheAgeOfTheMarker(unittest.TestCase):
    def test_no_marker_is_never_recent(self):
        with Sandbox():
            self.assertFalse(marker.marker_is_recent())

    def test_a_marker_written_now_is_recent(self):
        with Sandbox():
            marker.write_sources_read_marker("session-1")
            self.assertTrue(marker.marker_is_recent())

    def test_a_marker_older_than_the_window_is_not_recent(self):
        with Sandbox():
            path = marker.write_sources_read_marker("session-1")
            old = time.time() - constants.SOURCES_READ_GIT_HOOK_WINDOW_SECONDS - 60
            os.utime(path, (old, old))
            self.assertFalse(marker.marker_is_recent())


if __name__ == "__main__":
    unittest.main()
