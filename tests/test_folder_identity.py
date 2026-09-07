"""What makes one folder on this computer the same folder it was before.

The cases the filesystem cannot be asked to produce on demand, a recycled
inode number and a disk that came back as a different disk, are made by handing
the comparison a record written by the test rather than by the operating system.
That is the whole point of keeping the comparison in one small function that
takes two records: the rule can be tested without waiting for a rare accident.
"""

import os
import shutil
import sys
import tempfile
import unittest

import support  # noqa: F401

from gtmbase import folder_identity
from gtmbase.errors import StateError


class TempDir(object):
    def __enter__(self):
        self.path = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-identity-"))
        return self.path

    def __exit__(self, kind, value, trace):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


def folder(parent, name="marketing"):
    path = os.path.join(parent, name)
    os.makedirs(path)
    return path


class TestTakingTheRecord(unittest.TestCase):
    def test_the_record_holds_the_fields_we_write_down(self):
        with TempDir() as work:
            here = folder(work)

            taken = folder_identity.capture(here)

            self.assertEqual(here, taken.path)
            self.assertEqual(os.stat(here).st_dev, taken.dev)
            self.assertEqual(os.stat(here).st_ino, taken.ino)
            self.assertEqual(
                set(folder_identity.IDENTITY_FIELDS), set(taken.as_dict().keys())
            )
            self.assertIsNotNone(taken.mount)
            if sys.platform == "darwin":
                self.assertIsInstance(taken.birth, int)
            else:
                self.assertIsNone(taken.birth)

    def test_a_record_of_a_folder_that_is_not_there_is_refused(self):
        with TempDir() as work:
            with self.assertRaises(StateError) as caught:
                folder_identity.capture(os.path.join(work, "nowhere"))
            self.assertEqual(
                folder_identity.CODE_NOT_A_FOLDER, caught.exception.code
            )

    def test_a_file_is_not_a_folder(self):
        with TempDir() as work:
            path = support.write(os.path.join(work, "notes.md"), "hello\n")
            with self.assertRaises(StateError):
                folder_identity.capture(path)

    def test_a_record_read_back_from_a_stranger_is_checked_whole(self):
        good = {
            "dev": 1,
            "ino": 2,
            "birth": 3,
            "mount": "/",
            "volume": None,
            "remote": None,
        }
        self.assertEqual(good, folder_identity.clean(dict(good)))
        self.assertIsNone(folder_identity.clean(None))
        self.assertIsNone(folder_identity.clean("a folder"))
        for bad in (
            {"dev": "one", "ino": 2},
            {"dev": 1, "ino": True},
            {"dev": 1, "ino": 2, "birth": "yesterday"},
            {"dev": 1, "ino": 2, "mount": 5},
            {"dev": 1, "ino": 2, "surprise": 9},
            {"dev": 1, "ino": 2, "remote": "https://me:token@example.test/x"},
            {"ino": 2},
        ):
            self.assertIsNone(folder_identity.clean(bad), bad)


class TestComparingTwoRecords(unittest.TestCase):
    def record(self, **changes):
        base = {
            "dev": 100,
            "ino": 200,
            "birth": 300,
            "mount": "/Volumes/Work",
            "volume": "AAAA-BBBB",
            "remote": None,
        }
        base.update(changes)
        return base

    def test_the_same_folder_in_the_same_place_is_the_same(self):
        with TempDir() as work:
            here = folder(work)
            taken = folder_identity.capture(here)

            self.assertEqual(
                folder_identity.SAME,
                folder_identity.matches(taken.as_dict(), taken, here),
            )

    def test_a_renamed_folder_is_the_same_folder_moved(self):
        with TempDir() as work:
            here = folder(work)
            taken = folder_identity.capture(here)
            moved = os.path.join(work, "renamed")
            os.rename(here, moved)

            again = folder_identity.capture(moved)

            self.assertEqual(
                folder_identity.MOVED,
                folder_identity.matches(taken.as_dict(), again, here),
            )

    def test_a_different_device_number_is_a_disk_that_came_back(self):
        recorded = self.record()
        current = self.record(dev=101)

        self.assertEqual(
            folder_identity.REMOUNTED, folder_identity.matches(recorded, current, "/x")
        )

    def test_a_different_volume_identifier_is_a_disk_that_came_back(self):
        recorded = self.record()
        current = self.record(volume="CCCC-DDDD")

        self.assertEqual(
            folder_identity.REMOUNTED, folder_identity.matches(recorded, current, "/x")
        )

    def test_a_missing_volume_identifier_on_one_side_is_not_a_remount(self):
        """A disk tool that was slow one day never means the folder moved."""
        recorded = self.record()
        current = self.record(volume=None)

        self.assertEqual(
            folder_identity.SAME, folder_identity.matches(recorded, current)
        )

    def test_a_folder_deleted_and_built_again_is_a_different_folder(self):
        with TempDir() as work:
            here = folder(work)
            taken = folder_identity.capture(here)
            shutil.rmtree(here)
            os.makedirs(here)

            again = folder_identity.capture(here)

            self.assertEqual(
                folder_identity.DIFFERENT,
                folder_identity.matches(taken.as_dict(), again, here),
            )

    def test_a_recycled_number_with_another_day_of_birth_is_a_different_folder(self):
        recorded = self.record(birth=300)
        current = self.record(birth=999)

        self.assertEqual(
            folder_identity.DIFFERENT, folder_identity.matches(recorded, current, "/x")
        )

    def test_a_folder_now_pointed_at_other_work_is_a_different_folder(self):
        recorded = self.record(remote="github.com/acme/one")
        current = self.record(remote="github.com/acme/two")

        self.assertEqual(
            folder_identity.DIFFERENT, folder_identity.matches(recorded, current, "/x")
        )

    def test_a_folder_that_has_since_been_given_a_shared_copy_is_different(self):
        recorded = self.record(remote=None)
        current = self.record(remote="github.com/acme/two")

        self.assertEqual(
            folder_identity.DIFFERENT, folder_identity.matches(recorded, current, "/x")
        )

    def test_a_record_that_says_nothing_never_matches_anything(self):
        self.assertEqual(
            folder_identity.DIFFERENT, folder_identity.matches(None, self.record())
        )
        self.assertEqual(
            folder_identity.DIFFERENT, folder_identity.matches(self.record(), {"ino": 1})
        )


class TestLinksAndLetterCase(unittest.TestCase):
    def test_a_link_binds_the_folder_it_points_at(self):
        with TempDir() as work:
            real = folder(work, "real")
            link = os.path.join(work, "shortcut")
            os.symlink(real, link)

            taken = folder_identity.capture(link)

            self.assertEqual(real, taken.path)

    def test_pointing_the_link_somewhere_else_does_not_hand_over_the_folder(self):
        with TempDir() as work:
            real = folder(work, "real")
            other = folder(work, "other")
            link = os.path.join(work, "shortcut")
            os.symlink(real, link)
            taken = folder_identity.capture(link)

            os.unlink(link)
            os.symlink(other, link)
            again = folder_identity.capture(link)

            self.assertEqual(other, again.path)
            self.assertEqual(
                folder_identity.DIFFERENT,
                folder_identity.matches(taken.as_dict(), again, real),
            )

    def test_two_spellings_of_one_name_select_one_folder(self):
        with TempDir() as work:
            here = folder(work, "Marketing")
            other_case = os.path.join(work, "marketing")
            if not os.path.isdir(other_case):
                raise unittest.SkipTest("this disk tells the two spellings apart")
            taken = folder_identity.capture(here)

            again = folder_identity.capture(other_case)

            self.assertEqual(
                folder_identity.SAME,
                folder_identity.matches(taken.as_dict(), again, here),
            )
            self.assertTrue(folder_identity.points_at(other_case, taken))


class TestAFolderThatChangesWhileItIsBeingLookedAt(unittest.TestCase):
    """A record half from before a rename and half from after it is no record."""

    def test_a_path_that_leads_somewhere_else_the_second_time_is_refused(self):
        with TempDir() as work:
            here = folder(work, "marketing")
            other = folder(work, "other")
            answers = [here, other]
            real = folder_identity.resolve

            def moving(path):
                return answers.pop(0) if answers else real(path)

            folder_identity.resolve = moving
            try:
                with self.assertRaises(StateError) as caught:
                    folder_identity.capture(here)
            finally:
                folder_identity.resolve = real

            self.assertEqual(folder_identity.CODE_UNSTABLE, caught.exception.code)

    def test_the_ordinary_case_still_works_with_the_seam_in_place(self):
        with TempDir() as work:
            here = folder(work, "marketing")

            self.assertEqual(here, folder_identity.capture(here).path)


class TestTheAddressOfASharedCopy(unittest.TestCase):
    def test_only_the_top_of_a_repository_carries_its_address(self):
        with TempDir() as work:
            root = os.path.join(work, "project")
            os.makedirs(root)
            support.git(["init", "-b", "main", "-q"], cwd=root)
            support.git(
                ["remote", "add", "origin", "https://github.com/acme/one.git"], cwd=root
            )
            inside = folder(root, "marketing")

            self.assertEqual(
                "github.com/acme/one", folder_identity.capture(root).remote
            )
            self.assertIsNone(folder_identity.capture(inside).remote)

    def test_a_plain_folder_has_no_address(self):
        with TempDir() as work:
            self.assertIsNone(folder_identity.capture(folder(work)).remote)


if __name__ == "__main__":
    unittest.main()
