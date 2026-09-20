"""The names a person reads for the documents and the changes in their base."""

import unittest

import support  # noqa: F401  (puts the library on the path)

from gtmbase import constants, names


class TestDocumentNames(unittest.TestCase):
    def test_the_two_required_documents_have_names_a_person_uses(self):
        self.assertEqual(
            "your customer profile", names.document_name("context/strategy/icp.md")
        )
        self.assertEqual(
            "your positioning",
            names.document_name("context/strategy/positioning.md"),
        )

    def test_every_required_file_has_a_name_of_its_own(self):
        """The completion contract and the names must never fall out of step."""
        for path in constants.REQUIRED_CONTEXT_FILES:
            self.assertIn(path, names.KNOWN_DOCUMENTS)

    def test_a_segment_file_is_named_by_its_segment(self):
        self.assertEqual(
            "your fintech segment",
            names.document_name("context/strategy/segments/fintech.md"),
        )

    def test_a_segment_slug_of_several_words_reads_as_words(self):
        self.assertEqual(
            "your mid market saas segment",
            names.document_name("context/strategy/segments/mid-market-saas.md"),
        )

    def test_a_file_the_product_does_not_know_is_named_by_its_file_name(self):
        self.assertEqual(
            "your messaging", names.document_name("context/strategy/messaging.md")
        )

    def test_the_map_has_a_name_although_it_is_never_asked_about(self):
        self.assertEqual("your base's map", names.document_name(constants.MAP_PATH))

    def test_a_name_never_contains_a_path_or_a_file_ending(self):
        paths = (
            "context/strategy/icp.md",
            "context/strategy/positioning.md",
            "context/strategy/segments/fintech.md",
            "context/strategy/messaging.md",
            constants.MAP_PATH,
        )
        for path in paths:
            name = names.document_name(path)
            self.assertNotIn("/", name)
            self.assertNotIn(".md", name)

    def test_a_path_written_with_this_machine_s_separator_is_read_the_same(self):
        import os

        path = os.path.join("context", "strategy", "icp.md")
        self.assertEqual("your customer profile", names.document_name(path))

    def test_a_path_with_nothing_in_it_is_refused(self):
        for bad in ("", "   ", "./"):
            self.assertRaises(ValueError, names.document_name, bad)

    def test_a_segment_is_recognized_only_under_the_segments_folder(self):
        self.assertTrue(names.is_segment("context/strategy/segments/fintech.md"))
        self.assertFalse(names.is_segment("context/strategy/icp.md"))
        self.assertFalse(names.is_segment("context/strategy/segments-notes.md"))


class TestChangeNames(unittest.TestCase):
    def test_a_change_is_its_first_line_and_the_day_it_happened(self):
        self.assertEqual(
            "We stopped selling to companies under twenty people. (2026-09-19)",
            names.change_name(
                "We stopped selling to companies under twenty people.\n\nThe last"
                " four took the longest to close.",
                "2026-09-19",
            ),
        )

    def test_a_change_name_never_carries_an_identifier(self):
        name = names.change_name("We moved pricing to three tiers.", "2026-09-19")
        self.assertNotIn("stg-", name)
        self.assertNotIn("src-", name)

    def test_a_long_first_line_is_cut_at_a_word(self):
        line = (
            "We stopped selling to companies under twenty people because the "
            "last four of them took the longest to close and left the soonest."
        )
        name = names.change_name(line, "2026-09-19")
        self.assertTrue(name.endswith("... (2026-09-19)"), name)
        self.assertLessEqual(len(name.split(" (")[0]), names.CHANGE_LINE_CHARS + 3)
        self.assertNotIn("  ", name)

    def test_a_heading_marker_is_not_read_aloud(self):
        self.assertEqual(
            "Pricing moved to three tiers (2026-09-19)",
            names.change_name("# Pricing moved to three tiers", "2026-09-19"),
        )

    def test_a_change_with_no_first_line_still_gets_a_name(self):
        self.assertEqual(
            names.CHANGE_WITHOUT_A_LINE + " (2026-09-19)",
            names.change_name("", "2026-09-19"),
        )
        self.assertEqual(
            names.CHANGE_WITHOUT_A_LINE + " (2026-09-19)",
            names.change_name(None, "2026-09-19"),
        )

    def test_a_change_with_no_date_is_named_by_its_line_alone(self):
        self.assertEqual(
            "We moved pricing to three tiers.",
            names.change_name("We moved pricing to three tiers.", None),
        )

    def test_blank_opening_lines_are_stepped_over(self):
        self.assertEqual(
            "We moved pricing to three tiers. (2026-09-19)",
            names.change_name(
                "\n\n   \nWe moved pricing to three tiers.\nAnd we said so.",
                "2026-09-19",
            ),
        )


if __name__ == "__main__":
    unittest.main()
