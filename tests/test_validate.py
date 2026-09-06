"""Unit 2: the checks on the map's settings, on owners, names, and the marker."""

import unittest

import support  # noqa: F401  (puts the library on the import path)

from gtmbase import constants, validate
from gtmbase.errors import ValidationError

STG = "stg-" + "0" * 16
SRC = "src-" + "0" * 24


class TestMapSettings(unittest.TestCase):
    def test_both_settings_are_read(self):
        text = "## Settings\n\nconfirmation_threshold_days: 45\nnot_now_days: 3\n"
        self.assertEqual(
            {"confirmation_threshold_days": 45, "not_now_days": 3},
            validate.read_map_settings(text),
        )

    def test_a_missing_setting_takes_its_default(self):
        settings = validate.read_map_settings("# Map\n\nNothing here.\n")
        self.assertEqual(
            constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS,
            settings["confirmation_threshold_days"],
        )
        self.assertEqual(constants.DEFAULT_NOT_NOW_DAYS, settings["not_now_days"])

    def test_a_value_outside_the_allowed_range_is_refused(self):
        for value in (0, -1, 366, 100000):
            with self.assertRaises(ValidationError) as caught:
                validate.read_map_settings("confirmation_threshold_days: %d\n" % value)
            self.assertEqual("setting-out-of-range", caught.exception.code)

    def test_a_value_that_is_not_a_whole_number_is_refused(self):
        for value in ("thirty", "30.5", "30 days", "0x1e"):
            with self.assertRaises(ValidationError) as caught:
                validate.read_map_settings("not_now_days: %s\n" % value)
            self.assertEqual("setting-not-a-number", caught.exception.code)

    def test_the_smallest_and_largest_allowed_values_pass(self):
        text = "confirmation_threshold_days: 1\nnot_now_days: 365\n"
        self.assertEqual(
            {"confirmation_threshold_days": 1, "not_now_days": 365},
            validate.read_map_settings(text),
        )


class TestOwners(unittest.TestCase):
    def test_one_plain_address_passes(self):
        self.assertEqual(["jane@acme.com"], validate.validate_owner("jane@acme.com"))
        self.assertEqual(
            ["jane.doe+base@sub.acme.co.uk"],
            validate.validate_owner("jane.doe+base@sub.acme.co.uk"),
        )

    def test_a_list_of_two_addresses_passes(self):
        self.assertEqual(
            ["jane@acme.com", "sam@acme.com"],
            validate.validate_owner("[jane@acme.com, sam@acme.com]"),
        )
        self.assertEqual(
            ["jane@acme.com", "sam@acme.com"],
            validate.validate_owner(["jane@acme.com", "sam@acme.com"]),
        )

    def test_a_value_that_is_not_an_address_fails(self):
        for value in ("jane", "@acme.com", "jane@", "jane doe <jane@acme.com>",
                      "jane@acme", "jane@@acme.com", "jane@acme..com", ""):
            with self.assertRaises(ValidationError):
                validate.validate_owner(value)

    def test_the_error_names_the_position_and_never_repeats_the_value(self):
        with self.assertRaises(ValidationError) as caught:
            validate.validate_owner("[jane@acme.com, ghp_0123456789abcdefghij]")
        message = str(caught.exception)
        self.assertIn("number 2", message)
        self.assertNotIn("ghp_", message)

    def test_the_address_check_on_its_own(self):
        self.assertTrue(validate.is_valid_email("jane@acme.com"))
        self.assertFalse(validate.is_valid_email(" jane@acme.com"))
        self.assertFalse(validate.is_valid_email("jane@acme.com, sam@acme.com"))
        self.assertFalse(validate.is_valid_email("jané@acme.com"))
        self.assertFalse(validate.is_valid_email(None))


class TestFilenames(unittest.TestCase):
    def test_an_ordinary_name_passes(self):
        self.assertEqual("icp.md", validate.validate_filename("icp.md"))
        self.assertEqual(
            "2026-01-13-wrong-definition.md",
            validate.validate_filename("2026-01-13-wrong-definition.md"),
        )

    def test_the_names_we_never_accept(self):
        cases = {
            "name-empty": "   ",
            "name-long": "a" * 121,
            "name-control": "icp\nname.md",
            "name-character": "work/icp.md",
            "name-climbing": "..secret.md",
            "name-hidden": ".env",
        }
        for expected, value in cases.items():
            with self.assertRaises(ValidationError) as caught:
                validate.validate_filename(value)
            self.assertEqual(expected, caught.exception.code, value)

    def test_a_name_with_markdown_link_punctuation_is_refused(self):
        for value in ("a[b].md", "a(b).md", "a\\b.md"):
            with self.assertRaises(ValidationError):
                validate.validate_filename(value)


class TestMarker(unittest.TestCase):
    def test_render_and_parse_are_a_round_trip(self):
        line = validate.marker_line(STG, STG, SRC)
        self.assertEqual(
            "gtm-base proposal %s entry %s source %s" % (STG, STG, SRC), line
        )
        self.assertEqual((STG, STG, SRC), validate.parse_marker_line(line))

    def test_the_empty_parts_are_written_as_a_dash_and_read_back_as_nothing(self):
        line = validate.marker_line(STG)
        self.assertEqual("gtm-base proposal %s entry - source -" % STG, line)
        self.assertEqual((STG, None, None), validate.parse_marker_line(line))

    def test_a_hidden_comment_is_never_a_marker(self):
        line = validate.marker_line(STG, STG, SRC)
        self.assertIsNone(validate.parse_marker_line("<!-- %s -->" % line))
        self.assertIsNone(validate.find_marker("<!-- %s -->" % line))

    def test_a_marker_is_found_inside_a_body(self):
        line = validate.marker_line(STG, None, SRC)
        body = "## Why\n\nBecause of the meeting.\n\n%s\n" % line
        self.assertEqual((STG, None, SRC), validate.find_marker(body))
        self.assertIsNone(validate.find_marker("## Why\n\nNothing here.\n"))

    def test_a_marker_with_a_part_we_cannot_read_is_refused(self):
        self.assertIsNone(validate.parse_marker_line("gtm-base proposal nope entry - source -"))
        self.assertIsNone(
            validate.parse_marker_line("gtm-base proposal %s entry nope source -" % STG)
        )
        self.assertIsNone(validate.parse_marker_line("gtm-base proposal %s" % STG))
        with self.assertRaises(ValueError):
            validate.marker_line("nope")


if __name__ == "__main__":
    unittest.main()
