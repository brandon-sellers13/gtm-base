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


def central(name="Acme"):
    """Where every base goes now: one folder per company, kept for bases."""
    return os.path.join(
        location.home_path(), constants.BASES_FOLDER_NAME, name, "gtm-base"
    )


class TestWhereTheBaseGoes(unittest.TestCase):
    """Every base goes in the folder kept for bases, unless they ask otherwise."""

    def content_folder(self, sandbox, name="marketing"):
        folder = os.path.join(os.environ["HOME"], name)
        support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
        return folder

    def test_a_plain_folder_still_sends_the_base_to_the_folder_kept_for_bases(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox)

            proposal = location.propose_target(folder, "Acme")

            self.assertEqual(central(), proposal.target_path)
            self.assertEqual(location.REASON_BASES_FOLDER, proposal.reason_code)
            self.assertIsNone(proposal.warning_code)

    def test_a_folder_that_keeps_its_own_history_sends_the_base_to_the_same_place(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder(sandbox, "Gridwise")
            support.git(["init", "-b", "main", "-q"], cwd=folder)

            proposal = location.propose_target(
                folder, "Gridwise", named_content_folder=folder
            )

            self.assertEqual(central("Gridwise"), proposal.target_path)
            self.assertEqual(location.REASON_BASES_FOLDER, proposal.reason_code)

    def test_naming_no_folder_at_all_sends_the_base_to_the_same_place(self):
        with support.Sandbox() as sandbox:
            empty = os.path.join(os.environ["HOME"], "empty")
            os.makedirs(empty)

            proposal = location.propose_target(empty, "Acme")

            self.assertEqual(central(), proposal.target_path)

    def test_the_folder_they_named_never_changes_where_the_base_goes(self):
        with support.Sandbox() as sandbox:
            named = self.content_folder(sandbox, "named")
            here = self.content_folder(sandbox, "here")

            proposal = location.propose_target(here, "Acme", named_content_folder=named)

            self.assertEqual(central(), proposal.target_path)

    def test_the_sentence_names_the_folder_they_named_as_the_one_to_open(self):
        with support.Sandbox() as sandbox:
            named = self.content_folder(sandbox)

            proposal = location.propose_target(
                named, "Acme", named_content_folder=named
            )
            sentence = location.describe(proposal)

            self.assertEqual(
                "Your base will go in a new folder at %s, a folder kept for "
                "bases inside your home folder. To work with it, open Claude "
                "Code in the folder you named, %s, and it will be there. "
                "Nothing in the folder you named will be changed. Is that the "
                "right place for it?" % (central(), os.path.realpath(named)),
                sentence,
            )
            self.assertEqual([], plain_language.find_banned(sentence), sentence)
            self.assertEqual([], plain_language.find_dashes(sentence), sentence)

    def test_the_sentence_with_no_folder_named_names_only_the_base(self):
        with support.Sandbox() as sandbox:
            empty = os.path.join(os.environ["HOME"], "empty")
            os.makedirs(empty)

            proposal = location.propose_target(empty, "Acme")
            sentence = location.describe(proposal)

            self.assertEqual(
                "Your base will go in a new folder at %s, a folder kept for "
                "bases inside your home folder. To work with it, open Claude "
                "Code in that folder. Is that the right place for it?"
                % central(),
                sentence,
            )
            self.assertEqual([], plain_language.find_banned(sentence), sentence)
            self.assertEqual([], plain_language.find_dashes(sentence), sentence)

    def test_a_company_folder_that_is_already_there_is_refused_by_name(self):
        with support.Sandbox() as sandbox:
            os.makedirs(os.path.join(os.environ["HOME"], constants.BASES_FOLDER_NAME, "Acme"))

            with self.assertRaises(LocationError) as caught:
                location.propose_target(os.environ["HOME"], "Acme")

            self.assertEqual(
                location.CODE_COMPANY_FOLDER_EXISTS, caught.exception.code
            )

    def test_a_distinguishing_name_goes_to_a_folder_of_its_own(self):
        with support.Sandbox() as sandbox:
            os.makedirs(os.path.join(os.environ["HOME"], constants.BASES_FOLDER_NAME, "Acme"))

            proposal = location.propose_target(os.environ["HOME"], "Acme Europe")

            self.assertEqual(central("Acme Europe"), proposal.target_path)


class TestAskingForItBesideTheMaterial(unittest.TestCase):
    """The person can ask for the base beside their material, if it checks out."""

    def content_folder(self, name="marketing"):
        folder = os.path.join(os.environ["HOME"], name)
        support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
        return folder

    def test_a_clean_local_folder_is_allowed_when_they_ask_for_it(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder()

            proposal = location.propose_target(
                folder, "Acme", named_content_folder=folder, beside=True
            )

            self.assertEqual(
                os.path.join(os.path.realpath(folder), "gtm-base"),
                proposal.target_path,
            )
            self.assertEqual(location.REASON_BESIDE_CONTENT, proposal.reason_code)
            sentence = location.describe(proposal)
            self.assertIn("beside the material", sentence)
            self.assertEqual([], plain_language.find_banned(sentence), sentence)

    def test_a_folder_that_keeps_its_own_history_is_refused_even_when_they_ask(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder("project")
            support.git(["init", "-b", "main", "-q"], cwd=folder)

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    folder, "Acme", named_content_folder=folder, beside=True
                )
            self.assertEqual(location.CODE_INSIDE_REPOSITORY, caught.exception.code)

    def test_a_folder_inside_a_repository_is_refused(self):
        with support.Sandbox() as sandbox:
            outer = os.path.join(os.environ["HOME"], "project")
            os.makedirs(outer)
            support.git(["init", "-b", "main", "-q"], cwd=outer)
            inner = os.path.join(outer, "marketing")
            support.write(os.path.join(inner, "positioning.md"), "# Positioning\n")

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    inner, "Acme", named_content_folder=inner, beside=True
                )
            self.assertEqual(location.CODE_INSIDE_REPOSITORY, caught.exception.code)

    def test_a_destination_that_is_not_there_yet_is_checked_by_its_ancestors(self):
        with support.Sandbox() as sandbox:
            outer = os.path.join(os.environ["HOME"], "project")
            os.makedirs(outer)
            support.git(["init", "-b", "main", "-q"], cwd=outer)
            missing = os.path.join(outer, "not", "here", "yet")

            with self.assertRaises(LocationError) as caught:
                location.check_parent(missing)
            self.assertEqual(location.CODE_INSIDE_REPOSITORY, caught.exception.code)

    def test_a_folder_the_home_folder_sits_in_is_refused(self):
        with support.Sandbox() as sandbox:
            above = os.path.dirname(location.home_path())

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    above, "Acme", named_content_folder=above, beside=True
                )
            self.assertEqual(location.CODE_HOME_DIRECTORY, caught.exception.code)

    def test_the_home_folder_itself_needs_a_second_yes(self):
        with support.Sandbox() as sandbox:
            support.write(os.path.join(os.environ["HOME"], "notes.md"), "# Notes\n")
            home = os.environ["HOME"]

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    home, "Acme", named_content_folder=home, beside=True
                )
            self.assertEqual(location.CODE_HOME_DIRECTORY, caught.exception.code)

            proposal = location.propose_target(
                home, "Acme", named_content_folder=home, beside=True, confirmed_home=True
            )
            self.assertEqual(
                os.path.join(location.home_path(), "gtm-base"), proposal.target_path
            )

    def test_a_folder_that_already_holds_a_base_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder()
            os.makedirs(os.path.join(folder, "gtm-base"))

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    folder, "Acme", named_content_folder=folder, beside=True
                )
            self.assertEqual(location.CODE_TARGET_EXISTS, caught.exception.code)

    def test_a_folder_holding_a_stray_base_of_another_letter_case_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = self.content_folder()
            os.makedirs(os.path.join(folder, "GTM-Base"))

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    folder, "Acme", named_content_folder=folder, beside=True
                )
            self.assertIn(
                caught.exception.code,
                (location.CODE_STRAY_BASE, location.CODE_TARGET_EXISTS),
            )

    def test_a_place_inside_the_folder_gtm_base_keeps_for_itself_is_refused(self):
        with support.Sandbox() as sandbox:
            inside = os.path.join(paths.seat_home_path(), "mine")
            support.write(os.path.join(inside, "notes.md"), "# Notes\n")

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    inside, "Acme", named_content_folder=inside, beside=True
                )
            self.assertEqual(location.CODE_INSIDE_SEAT_HOME, caught.exception.code)

    def test_a_folder_inside_a_base_this_account_joined_is_refused(self):
        with support.Sandbox() as sandbox:
            from gtmbase import ids, machine

            root = os.path.join(os.environ["HOME"], "GTM Bases", "Acme", "gtm-base")
            base_id = ids.base_id_random()
            support.make_base(root, base_id=base_id)
            machine.append_joined(root=root, base_id=base_id)
            inside = os.path.join(root, "context", "notes")

            with self.assertRaises(LocationError) as caught:
                location.propose_target(
                    inside, "Other", named_content_folder=inside, beside=True
                )
            self.assertEqual(location.CODE_INSIDE_BASE, caught.exception.code)


class TestFoldersAnotherProgramCopies(unittest.TestCase):
    """A base never goes anywhere another program uploads on its own."""

    def refuse(self, folder, code):
        support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
        with self.assertRaises(LocationError) as caught:
            location.propose_target(
                folder, "Acme", named_content_folder=folder, beside=True
            )
        self.assertEqual(code, caught.exception.code)

    def test_the_folder_apple_keeps_documents_in_is_refused(self):
        with support.Sandbox() as sandbox:
            self.refuse(
                os.path.join(
                    os.environ["HOME"],
                    "Library",
                    "Mobile Documents",
                    "com~apple~CloudDocs",
                    "Acme",
                ),
                location.CODE_SYNCED,
            )

    def test_the_folder_other_cloud_storage_is_mounted_in_is_refused(self):
        with support.Sandbox() as sandbox:
            self.refuse(
                os.path.join(os.environ["HOME"], "Library", "CloudStorage", "Acme"),
                location.CODE_SYNCED,
            )

    def test_a_folder_named_for_another_company_cloud_drive_is_refused(self):
        with support.Sandbox() as sandbox:
            self.refuse(
                os.path.join(os.environ["HOME"], "Google Drive", "Acme"),
                location.CODE_SYNCED,
            )
            self.refuse(
                os.path.join(os.environ["HOME"], "Dropbox", "Acme"),
                location.CODE_SYNCED,
            )
            self.refuse(
                os.path.join(os.environ["HOME"], "OneDrive", "Acme"),
                location.CODE_SYNCED,
            )

    def test_desktop_is_refused_outright_when_the_marker_says_it_is_kept(self):
        with support.Sandbox() as sandbox:
            os.makedirs(
                os.path.join(
                    os.environ["HOME"], "Library", "Mobile Documents", "com~apple~CloudDocs"
                )
            )
            support.write(
                os.path.join(
                    os.environ["HOME"], "Desktop", "com.apple.icloud.desktop"
                ),
                "",
            )
            self.refuse(
                os.path.join(os.environ["HOME"], "Desktop", "Acme"),
                location.CODE_SYNCED,
            )

    def test_desktop_comes_back_as_unknown_when_it_cannot_be_told(self):
        """The one answer that is a question rather than a refusal."""
        with support.Sandbox() as sandbox:
            os.makedirs(
                os.path.join(
                    os.environ["HOME"], "Library", "Mobile Documents", "com~apple~CloudDocs"
                )
            )
            self.refuse(
                os.path.join(os.environ["HOME"], "Documents", "Acme"),
                location.CODE_SYNC_UNKNOWN,
            )

    def test_an_ordinary_folder_is_not_treated_as_kept_in_the_cloud(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(os.environ["HOME"], "marketing")
            support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")

            proposal = location.propose_target(
                folder, "Acme", named_content_folder=folder, beside=True
            )

            self.assertEqual(
                os.path.join(os.path.realpath(folder), "gtm-base"),
                proposal.target_path,
            )


class TestTheSentenceThePersonReads(unittest.TestCase):
    """Every sentence this module produces is one a marketer can read."""

    def test_every_sentence_is_plain(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(os.environ["HOME"], "marketing")
            support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
            beside = location.propose_target(
                folder, "Acme", named_content_folder=folder, beside=True
            )
            empty = os.path.join(os.environ["HOME"], "empty")
            os.makedirs(empty)
            home = location.propose_target(empty, "Acme")

            sentences = []
            for proposal in (beside, home):
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
