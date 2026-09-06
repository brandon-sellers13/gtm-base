"""Unit 2: identifiers, and the promise that the same work gives the same one."""

import datetime
import unittest

import support  # noqa: F401  (puts the library on the import path)

from gtmbase import ids


TRANSCRIPT = "Jane: we are going after companies of twenty to two hundred people."


class TestSourceIds(unittest.TestCase):
    def test_two_exports_differing_only_in_spacing_have_the_same_id(self):
        first = ids.source_id_for_text(TRANSCRIPT)
        second = ids.source_id_for_text(
            "  Jane:   we are going after companies of twenty to two hundred people.\n\n"
        )
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("src-"))
        self.assertEqual(28, len(first))

    def test_a_change_of_wording_or_of_case_changes_the_id(self):
        first = ids.source_id_for_text(TRANSCRIPT)
        self.assertNotEqual(first, ids.source_id_for_text(TRANSCRIPT.upper()))
        self.assertNotEqual(first, ids.source_id_for_text(TRANSCRIPT + " Sam: agreed."))

    def test_a_vendor_recording_keeps_the_name_the_vendor_gave_it(self):
        self.assertEqual(
            "src-fireflies-01HZX9", ids.source_id_for_vendor("fireflies", "01HZX9")
        )
        ids.check_source_id(ids.source_id_for_vendor("fathom", "abc_123-4"))

    def test_a_vendor_or_recording_name_we_do_not_allow_is_refused(self):
        for vendor, recording in (
            ("Fireflies", "01HZX9"),
            ("fire flies", "01HZX9"),
            ("fireflies", "01 HZX9"),
            ("fireflies", "../../etc/passwd"),
            ("", "01HZX9"),
        ):
            with self.assertRaises(ValueError):
                ids.source_id_for_vendor(vendor, recording)


class TestStagingIds(unittest.TestCase):
    def test_the_same_parts_give_the_same_id_across_runs(self):
        source = ids.source_id_for_text(TRANSCRIPT)
        first = ids.staging_id(source, "context/strategy/icp.md", "inbox", 0)
        second = ids.staging_id(source, "context/strategy/icp.md", "inbox", 0)
        self.assertEqual(first, second)
        self.assertEqual("stg-", first[:4])
        self.assertEqual(20, len(first))

    def test_changing_any_part_changes_the_id(self):
        source = ids.source_id_for_text(TRANSCRIPT)
        base = ids.staging_id(source, "context/strategy/icp.md", "inbox", 0)
        others = [
            ids.staging_id(source + "x", "context/strategy/icp.md", "inbox", 0),
            ids.staging_id(source, "context/plan/goals.md", "inbox", 0),
            ids.staging_id(source, "context/strategy/icp.md", "ledger", 0),
            ids.staging_id(source, "context/strategy/icp.md", "inbox", 1),
        ]
        for other in others:
            self.assertNotEqual(base, other)
        self.assertEqual(len(others), len(set(others)))

    def test_the_parts_cannot_be_run_together_to_forge_a_match(self):
        first = ids.staging_id("src-a" + "0" * 20, "b/c.md", "inbox", 0)
        second = ids.staging_id("src-a" + "0" * 20 + "b", "c.md", "inbox", 0)
        self.assertNotEqual(first, second)

    def test_a_separator_inside_a_part_is_refused(self):
        with self.assertRaises(ValueError):
            ids.staging_id("src-a\x1fb", "context/x.md", "inbox", 0)

    def test_a_ledger_entry_is_named_by_its_proposal(self):
        value = ids.staging_id("src-" + "0" * 24, "context/x.md", "inbox", 0)
        self.assertEqual(value, ids.entry_id_for(value))


class TestQuestionIds(unittest.TestCase):
    def test_the_same_question_asked_twice_gets_two_different_ids(self):
        first = ids.question_id("context/strategy/icp.md", "ledger", None, "session-1")
        second = ids.question_id("context/strategy/icp.md", "ledger", None, "session-1")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("q-"))
        self.assertEqual(22, len(first))

    def test_the_random_part_can_be_handed_in_for_a_test(self):
        first = ids.question_id("a", "ledger", None, "s", rand=b"\x00" * 16)
        second = ids.question_id("a", "ledger", None, "s", rand=b"\x00" * 16)
        self.assertEqual(first, second)
        self.assertNotEqual(first, ids.question_id("a", "ledger", None, "s", rand=b"\x01" * 16))

    def test_too_little_randomness_is_refused(self):
        with self.assertRaises(ValueError):
            ids.question_id("a", "ledger", None, "s", rand=b"\x00")


class TestRunAndBaseIds(unittest.TestCase):
    def test_a_run_id_carries_the_day_it_ran(self):
        value = ids.run_id(datetime.date(2026, 9, 5))
        self.assertTrue(value.startswith("run-2026-09-05-"))
        ids.check_run_id(value)

    def test_a_random_base_id_is_thirty_two_characters(self):
        value = ids.base_id_random()
        self.assertEqual(32, len(value))
        ids.check_base_id(value)
        self.assertNotEqual(value, ids.base_id_random())

    def test_every_way_of_writing_one_address_gives_one_base_id(self):
        addresses = [
            "git@github.com:Acme/base.git",
            "https://github.com/acme/base",
            "ssh://git@github.com/acme/base/",
            "https://GitHub.com/Acme/base.git/",
            "https://someone:token@github.com/acme/base.git",
        ]
        values = set(ids.base_id_for_remote(address) for address in addresses)
        self.assertEqual(1, len(values), values)
        ids.check_base_id(values.pop())

    def test_a_different_repository_gives_a_different_base_id(self):
        self.assertNotEqual(
            ids.base_id_for_remote("https://github.com/acme/base"),
            ids.base_id_for_remote("https://github.com/acme/other"),
        )
        self.assertNotEqual(
            ids.base_id_for_remote("https://github.com/acme/base"),
            ids.base_id_for_remote("https://gitlab.com/acme/base"),
        )

    def test_an_address_we_cannot_read_is_refused(self):
        for address in ("", "   ", "not an address", "https://github.com"):
            with self.assertRaises(ValueError):
                ids.base_id_for_remote(address)

    def test_a_sign_in_is_stripped_from_an_address(self):
        self.assertEqual(
            "https://github.com/acme/base.git",
            ids.strip_userinfo("https://someone:token@github.com/acme/base.git"),
        )
        self.assertEqual(
            "github.com:acme/base.git", ids.strip_userinfo("git@github.com:acme/base.git")
        )


class TestContentHash(unittest.TestCase):
    def test_line_endings_do_not_change_the_hash(self):
        self.assertEqual(
            ids.content_hash("one\ntwo\n"), ids.content_hash("one\r\ntwo\r\n")
        )
        self.assertEqual(64, len(ids.content_hash("one")))
        self.assertNotEqual(ids.content_hash("one"), ids.content_hash("two"))

    def test_a_path_is_recorded_by_its_hash_and_never_by_its_name(self):
        value = ids.path_hash("/Users/someone/secret/place.md")
        self.assertEqual(64, len(value))
        self.assertNotIn("someone", value)


class TestCharsetChecks(unittest.TestCase):
    def test_every_check_refuses_the_wrong_shape(self):
        cases = [
            (ids.check_source_id, ["src-", "src-zzzz", "stg-" + "0" * 16, "", None, 5]),
            (ids.check_staging_id, ["stg-" + "0" * 15, "stg-" + "g" * 16, "src-" + "0" * 24, ""]),
            (ids.check_question_id, ["q-" + "0" * 19, "q-" + "Z" * 20, ""]),
            (ids.check_run_id, ["run-2026-9-05-00000000", "run-00000000", ""]),
            (ids.check_base_id, ["0" * 31, "0" * 33, "G" * 32, ""]),
            (ids.check_content_hash, ["0" * 63, "z" * 64, ""]),
        ]
        for check, values in cases:
            for value in values:
                with self.assertRaises(ValueError):
                    check(value)

    def test_every_check_accepts_the_right_shape(self):
        ids.check_source_id("src-" + "0" * 24)
        ids.check_source_id("src-fireflies-01HZX9")
        ids.check_staging_id("stg-" + "a" * 16)
        ids.check_entry_id("stg-" + "a" * 16)
        ids.check_question_id("q-" + "b" * 20)
        ids.check_run_id("run-2026-09-05-abcdef01")
        ids.check_base_id("f" * 32)
        ids.check_content_hash("0" * 64)

    def test_the_yes_or_no_forms_never_raise(self):
        self.assertTrue(ids.is_base_id("f" * 32))
        self.assertFalse(ids.is_base_id("nope"))
        self.assertFalse(ids.is_source_id(None))
        self.assertFalse(ids.is_staging_id(""))
        self.assertFalse(ids.is_question_id(3))
        self.assertFalse(ids.is_run_id("run-x"))


if __name__ == "__main__":
    unittest.main()
