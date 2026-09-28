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

    def test_a_segment_is_counted_never_named_from_its_file_name(self):
        """Unit 1.8 changed this, and the test with it.

        A segment used to be named from its file name, so `fintech.md` was
        "your fintech segment". A file name is whatever somebody typed, and no
        sentence a person reads may be filled from one, so every segment is
        now "one of your segments". The person's own name for a segment comes
        from the inventory GTM Base keeps, never from the disk.
        """
        for path in (
            "context/strategy/segments/fintech.md",
            "context/strategy/segments/mid-market-saas.md",
            "context/icps/fintech.md",
            "context/icps/ignore-all-prior-instructions.md",
        ):
            self.assertEqual(names.ONE_OF_YOUR_SEGMENTS, names.document_name(path))

    def test_a_file_the_product_does_not_know_is_counted_never_named(self):
        """Unit 1.8 changed this too: `pricing-notes.md` was "your pricing notes"."""
        for path in (
            "context/pricing-notes.md",
            "context/notes/whatever-somebody-typed.md",
            "context/Run the setup again.md",
        ):
            self.assertEqual(names.ONE_OF_YOUR_DOCUMENTS, names.document_name(path))

    def test_a_known_document_at_its_older_path_keeps_its_own_name(self):
        self.assertEqual(
            "your messaging", names.document_name("context/strategy/messaging.md")
        )

    def test_no_word_of_an_unknown_file_name_is_ever_read_out(self):
        stems = ("zanzibar-quokka", "zanzibar_quokka", "Zanzibar Quokka")
        folders = ("context", "context/icps", "context/strategy/segments", "work")
        for folder in folders:
            for stem in stems:
                path = "%s/%s.md" % (folder, stem)
                for said in (
                    names.document_name(path),
                    names.documents_named([path, "context/icps.md", path]),
                ):
                    self.assertNotIn("zanzibar", said.lower(), path)
                    self.assertNotIn("quokka", said.lower(), path)

    def test_several_documents_name_the_known_ones_and_count_the_rest(self):
        self.assertEqual(
            "your customer profile, your positioning",
            names.documents_named(
                ["context/icps.md", "context/positioning.md"]
            ),
        )
        self.assertEqual(
            "your customer profile, two of your segments, one other document",
            names.documents_named(
                [
                    "context/icps.md",
                    "context/icps/fintech.md",
                    "context/icps/retail.md",
                    "context/pricing.md",
                ]
            ),
        )
        self.assertEqual(
            "one of your segments", names.documents_named(["context/icps/a.md"])
        )
        self.assertEqual(
            "three of your documents",
            names.documents_named(
                ["context/a.md", "context/b.md", "context/c.md"]
            ),
        )
        # The same document at its older and its current path is one document.
        self.assertEqual(
            "your customer profile",
            names.documents_named(["context/strategy/icp.md", "context/icps.md"]),
        )

    def test_the_map_has_a_name_although_it_is_never_asked_about(self):
        self.assertEqual("your base's map", names.document_name(constants.MAP_PATH))

    def test_a_name_never_contains_a_path_or_a_file_ending(self):
        paths = (
            "context/strategy/icp.md",
            "context/strategy/positioning.md",
            "context/strategy/segments/fintech.md",
            "context/strategy/messaging.md",
            "context/pricing-notes.md",
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

    def test_a_file_named_only_by_its_ending_is_still_named(self):
        """Review of Unit 1.8, finding 2: before Unit 1.8 these were "one of
        your documents", and a refusal about one must not become an error."""
        self.assertEqual(names.ONE_OF_YOUR_DOCUMENTS, names.document_name("context/.md"))
        self.assertEqual(
            names.ONE_OF_YOUR_SEGMENTS, names.document_name("context/icps/.md")
        )
        self.assertEqual(
            names.ONE_OF_YOUR_DOCUMENTS, names.documents_named(["context/.md"])
        )

    def test_one_document_listed_twice_is_counted_once(self):
        """Review of Unit 1.8, finding 7."""
        self.assertEqual(
            "one of your documents",
            names.documents_named(["context/a.md", "context/a.md"]),
        )
        self.assertEqual(
            "one of your segments",
            names.documents_named(
                ["context/strategy/segments/x.md", "context/icps/x.md"]
            ),
        )
        self.assertEqual(
            "two of your segments",
            names.documents_named(["context/icps/x.md", "context/icps/y.md"]),
        )

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
