"""No test run writes into the seat folder of whoever runs the suite.

A test with no seat folder of its own used to fall back to the real one in the
home folder of the person running the tests, and the sources test left its
read marker there. The suite now points the seat folder at a temporary one
before any test module's code runs, and tests/run.sh fails a run that wrote
anything into it. Everything here is proved inside temporary folders: the real
seat folder is never read, listed or touched.
"""

import os
import subprocess
import sys
import tempfile
import shutil
import unittest

import support

from gtmbase import constants, paths


class TestTheSeatFolderIsNeverTheRealOne(unittest.TestCase):
    def test_the_suite_starts_with_a_temporary_seat_folder(self):
        where = paths.seat_home_path()
        real = os.path.abspath(os.path.expanduser(constants.SEAT_HOME_DEFAULT))
        self.assertNotEqual(real, where)
        self.assertFalse(where.startswith(real + os.sep), where)
        # Compared as clean paths: the run makes the folder under the
        # computer's temporary folder, whose name can end in a slash.
        unowned = os.path.abspath(os.environ[support.UNOWNED_SEAT_VARIABLE])
        self.assertTrue(where.startswith(unowned + os.sep), where)

    def run_forgetful_test(self, unowned, preset=None):
        """A child that imports the test helpers and writes a seat, as a forgetful test would."""
        environment = dict(os.environ)
        environment[support.UNOWNED_SEAT_VARIABLE] = unowned
        if preset is None:
            environment.pop(support.SEAT_HOME_VARIABLE, None)
        else:
            environment[support.SEAT_HOME_VARIABLE] = preset
        code = (
            "import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            "import support\n"
            "from gtmbase import paths\n"
            "print(paths.seat_home())\n"
        ) % (os.path.join(support.REPO_ROOT, "tests"), support.LIB_DIR)
        finished = subprocess.run(
            [sys.executable, "-c", code],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, finished.returncode, finished.stderr.decode("utf-8"))
        return finished.stdout.decode("utf-8").strip()

    def test_a_test_that_makes_no_seat_folder_writes_into_the_temporary_one(self):
        sandbox = tempfile.mkdtemp(prefix="gtm-base-isolation-")
        self.addCleanup(shutil.rmtree, sandbox, True)
        unowned = os.path.join(sandbox, "unowned")
        os.makedirs(unowned)

        written = self.run_forgetful_test(unowned)

        self.assertEqual(os.path.join(unowned, "seat"), written)
        self.assertTrue(os.path.isdir(written))

    def test_a_seat_folder_set_by_the_person_running_the_suite_is_left_alone(self):
        sandbox = tempfile.mkdtemp(prefix="gtm-base-isolation-")
        self.addCleanup(shutil.rmtree, sandbox, True)
        unowned = os.path.join(sandbox, "unowned")
        os.makedirs(unowned)
        theirs = os.path.join(sandbox, "their-own-seat")

        written = self.run_forgetful_test(unowned, preset=theirs)

        self.assertEqual(os.path.join(unowned, "seat"), written)
        self.assertFalse(os.path.exists(theirs))

    def test_the_run_fails_when_anything_was_written_there(self):
        text = support.read(os.path.join(support.REPO_ROOT, "tests", "run.sh"))
        guard = "nothing_written_to_a_seat_nobody_made"
        self.assertIn(guard + "() {", text)
        # Once after each of the two runs.
        self.assertEqual(3, text.count(guard), text)
        self.assertIn(support.UNOWNED_SEAT_VARIABLE, text)


if __name__ == "__main__":
    unittest.main()
