"""Where a new base is allowed to go, and which places are refused.

Every scenario runs inside a temporary home folder, so nothing here can look at
or touch the person's own folders.
"""

import os
import unittest

import plain_language
import support

from gtmbase import constants, location, paths
from gtmbase.errors import LocationError


def sentences_of(proposal):
    return [location.describe(proposal)]


class TestTheCompanyName(unittest.TestCase):
    """A company is called what it is called, unless that makes a path."""

    def test_an_ordinary_name_is_kept_as_it_is(self):
        self.assertEqual("Acme", location.validate_company_name("  Acme  "))

    def test_spaces_and_ordinary_punctuation_are_kept(self):
        self.assertEqual(
            "Acme & Co., Inc.", location.validate_company_name("Acme & Co., Inc.")
        )

    def test_an_empty_name_is_refused(self):
        with self.assertRaises(LocationError) as caught:
            location.validate_company_name("   ")
        self.assertEqual(location.CODE_EMPTY_NAME, caught.exception.code)

    def test_a_hidden_folder_name_is_refused(self):
        with self.assertRaises(LocationError) as caught:
            location.validate_company_name(".ssh")
        self.assertEqual(location.CODE_LEADING_DOT, caught.exception.code)

    def test_a_name_holding_a_separator_is_refused(self):
        for name in ("a/b", "a\\b", "a:b"):
            with self.assertRaises(LocationError) as caught:
                location.validate_company_name(name)
            self.assertEqual(location.CODE_PATH_SEPARATOR, caught.exception.code)

    def test_a_name_that_climbs_out_of_its_folder_is_refused(self):
        with self.assertRaises(LocationError) as caught:
            location.validate_company_name("..")
        self.assertEqual(location.CODE_CLIMBING_NAME, caught.exception.code)

    def test_a_name_of_sixty_one_characters_is_refused(self):
        with self.assertRaises(LocationError) as caught:
            location.validate_company_name("a" * (constants.COMPANY_NAME_MAX + 1))
        self.assertEqual(location.CODE_LONG_NAME, caught.exception.code)
        self.assertEqual(
            "a" * constants.COMPANY_NAME_MAX,
            location.validate_company_name("a" * constants.COMPANY_NAME_MAX),
        )

    def test_a_name_holding_a_control_character_is_refused(self):
        with self.assertRaises(LocationError) as caught:
            location.validate_company_name("Acme\nInc")
        self.assertEqual(location.CODE_CONTROL_CHARACTER, caught.exception.code)


class TestWhereTheBaseGoes(unittest.TestCase):
    """The folder the person is working in, or a folder named for the company."""

    def content_folder(self, sandbox, name="marketing"):
        folder = os.path.join(os.environ["HOME"], name)
        support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
        return folder

    def test_a_folder_holding_their_material_gets_the_base_beside_it(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox)

            proposal = location.propose_target(folder, "Acme")

            self.assertEqual(
                os.path.join(os.path.realpath(folder), "gtm-base"),
                proposal.target_path,
            )
            self.assertEqual(location.REASON_BESIDE_CONTENT, proposal.reason_code)
            self.assertIsNone(proposal.warning_code)

    def test_a_folder_the_person_named_is_used_over_the_folder_they_are_in(self):
        with support.Sandbox() as sandbox:
            named = self.content_folder(sandbox, "named")
            here = self.content_folder(sandbox, "here")

            proposal = location.propose_target(here, "Acme", named_content_folder=named)

            self.assertEqual(
                os.path.join(os.path.realpath(named), "gtm-base"), proposal.target_path
            )

    def test_an_empty_folder_sends_the_base_to_a_folder_named_for_the_company(self):
        with support.Sandbox() as sandbox:
            empty = os.path.join(os.environ["HOME"], "empty")
            os.makedirs(empty)

            proposal = location.propose_target(empty, "Acme")

            self.assertEqual(
                os.path.join(location.home_path(), "Acme", "gtm-base"),
                proposal.target_path,
            )
            self.assertEqual(location.REASON_HOME_FOLDER, proposal.reason_code)

    def test_a_folder_already_looked_after_by_another_tool_is_warned_about(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox, "project")
            support.git(["init", "-b", "main", "-q"], cwd=folder)

            proposal = location.propose_target(folder, "Acme")

            self.assertEqual(
                location.WARNING_PARENT_IS_REPOSITORY, proposal.warning_code
            )
            self.assertEqual(
                os.path.join(location.home_path(), "Acme", "gtm-base"),
                proposal.target_path,
            )

    def test_the_home_folder_is_refused_until_the_person_says_yes_a_second_time(self):
        with support.Sandbox() as sandbox:
            support.write(os.path.join(os.environ["HOME"], "notes.md"), "# Notes\n")

            with self.assertRaises(LocationError) as caught:
                location.propose_target(os.environ["HOME"], "Acme")
            self.assertEqual(location.CODE_HOME_DIRECTORY, caught.exception.code)

            proposal = location.propose_target(
                os.environ["HOME"], "Acme", confirmed_home=True
            )
            self.assertEqual(
                os.path.join(location.home_path(), "gtm-base"), proposal.target_path
            )

    def test_a_folder_holding_the_home_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            above = os.path.dirname(location.home_path())

            with self.assertRaises(LocationError) as caught:
                location.propose_target(above, "Acme")
            self.assertEqual(location.CODE_HOME_DIRECTORY, caught.exception.code)

    def test_a_folder_that_already_holds_a_base_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox)
            os.makedirs(os.path.join(folder, "gtm-base"))

            with self.assertRaises(LocationError) as caught:
                location.propose_target(folder, "Acme")
            self.assertEqual(location.CODE_TARGET_EXISTS, caught.exception.code)

    def test_a_folder_holding_a_stray_base_of_another_letter_case_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox)
            os.makedirs(os.path.join(folder, "GTM-Base"))

            with self.assertRaises(LocationError) as caught:
                location.propose_target(folder, "Acme")
            self.assertIn(
                caught.exception.code,
                (location.CODE_STRAY_BASE, location.CODE_TARGET_EXISTS),
            )

    def test_a_place_inside_the_folder_gtm_base_keeps_for_itself_is_refused(self):
        with support.Sandbox() as sandbox:
            inside = os.path.join(paths.seat_home_path(), "mine")
            support.write(os.path.join(inside, "notes.md"), "# Notes\n")

            with self.assertRaises(LocationError) as caught:
                location.propose_target(inside, "Acme")
            self.assertEqual(location.CODE_INSIDE_SEAT_HOME, caught.exception.code)


class TestTheSentenceThePersonReads(unittest.TestCase):
    """Every sentence this module produces is one a marketer can read."""

    def test_every_sentence_is_plain(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(os.environ["HOME"], "marketing")
            support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
            beside = location.propose_target(folder, "Acme")
            empty = os.path.join(os.environ["HOME"], "empty")
            os.makedirs(empty)
            home = location.propose_target(empty, "Acme")
            support.git(["init", "-b", "main", "-q"], cwd=folder)
            warned = location.propose_target(folder, "Acme")

            sentences = []
            for proposal in (beside, home, warned):
                sentences.extend(sentences_of(proposal))
            for code in (
                location.CODE_EMPTY_NAME,
                location.CODE_LEADING_DOT,
                location.CODE_PATH_SEPARATOR,
                location.CODE_CLIMBING_NAME,
                location.CODE_CONTROL_CHARACTER,
                location.CODE_LONG_NAME,
            ):
                sentences.append(code)
            for name in ("", ".ssh", "a/b", "..", "Acme\nInc", "a" * 61):
                try:
                    location.validate_company_name(name)
                except LocationError as failure:
                    sentences.append(str(failure))

            for sentence in sentences:
                self.assertEqual([], plain_language.find_banned(sentence), sentence)
                self.assertEqual([], plain_language.find_dashes(sentence), sentence)


if __name__ == "__main__":
    unittest.main()
