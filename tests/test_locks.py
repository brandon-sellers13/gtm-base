"""0.3.3: the lock the questions are answered under works on any computer.

Astra's confirmation of 0.3.3, defect 4. `record_change` imported `fcntl`,
which native Windows Python does not have, so the stale-check script stopped
before it ran. Every lock now goes through `gtmbase.locks`, which uses the
operating system's lock where there is one and a lock file where there is
not, chosen when it is loaded. The lock file way is tested here on this
computer by choosing it on purpose.
"""

import os
import subprocess
import sys
import time
import unittest
from unittest import mock

import support
import test_moment_of_use as moment_tests
import test_record_change as recording

from gtmbase import locks, record_change


class TestItLoadsWithoutFcntl(unittest.TestCase):
    def test_the_script_side_imports_and_chooses_the_lock_file(self):
        code = (
            "import sys\n"
            "sys.modules['fcntl'] = None\n"
            "from gtmbase import locks, record_change\n"
            "print(locks.IMPLEMENTATION.name)\n"
        )
        finished = subprocess.run(
            [sys.executable, "-c", code],
            env=dict(os.environ, PYTHONPATH=support.LIB_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, finished.returncode, finished.stderr.decode("utf-8"))
        self.assertEqual("file", finished.stdout.decode("utf-8").strip())

    def test_this_computer_uses_its_own_lock(self):
        self.assertEqual("posix", locks.IMPLEMENTATION.name)


class TestTheLockFile(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.path = os.path.join(self.sandbox.path, "a.lock")

    def test_a_held_lock_keeps_a_second_holder_out(self):
        with locks.held(self.path, kind=locks.FileLock):
            with self.assertRaises(locks.Busy):
                with locks.held(self.path, wait_seconds=0.2, kind=locks.FileLock):
                    pass
        self.assertFalse(os.path.exists(self.path))
        with locks.held(self.path, wait_seconds=0.2, kind=locks.FileLock):
            pass

    def test_a_lock_whose_holder_stopped_is_taken_again(self):
        finished = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"],
                                  stdout=subprocess.PIPE)
        gone = int(finished.stdout.decode("utf-8").strip())
        import socket

        support.write(self.path, "%d %s abc\n" % (gone, socket.gethostname() or "-"))
        with locks.held(self.path, wait_seconds=1, kind=locks.FileLock):
            self.assertIn(str(os.getpid()), support.read(self.path))

    def test_a_live_holders_lock_is_never_taken_away(self):
        import socket

        live = "%d %s somebody-else\n" % (os.getpid(), socket.gethostname() or "-")
        support.write(self.path, live)
        old = time.time() - 3600
        os.utime(self.path, (old, old))
        with self.assertRaises(locks.Busy):
            with locks.held(self.path, wait_seconds=0.3, kind=locks.FileLock):
                pass
        self.assertEqual(live, support.read(self.path))

    def test_where_the_holder_cannot_be_asked_only_a_very_old_lock_is_taken(self):
        support.write(self.path, "12345 another-computer x\n")
        with self.assertRaises(locks.Busy):
            with locks.held(self.path, wait_seconds=0.2, kind=locks.FileLock):
                pass
        old = time.time() - locks.UNASKABLE_STALE_SECONDS - 60
        os.utime(self.path, (old, old))
        with locks.held(self.path, wait_seconds=1, kind=locks.FileLock):
            pass

    def test_an_abandoned_lock_replaced_meanwhile_is_put_back_not_taken(self):
        import socket

        dead = "999999 %s gone\n" % (socket.gethostname() or "-")
        support.write(self.path, dead)
        lock = locks.FileLock(self.path)
        live = "%d %s theirs\n" % (os.getpid(), socket.gethostname() or "-")
        real_read = lock._read
        calls = []

        def read_then_replace():
            answer = real_read()
            if not calls:
                calls.append(1)
                # Another window takes the abandoned lock and makes its own
                # between this window's look and its move.
                support.write(self.path, live)
            return answer

        with mock.patch.object(locks, "_still_running", return_value=False):
            with mock.patch.object(lock, "_read", side_effect=read_then_replace):
                lock._take_away_if_abandoned()
        self.assertEqual(live, support.read(self.path))


class TestTheQuestionsUnderTheLockFile(recording.LocalCase):
    """The answers, one at a time, with the lock file chosen on purpose."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(record_change, "LOCK_KIND", locks.FileLock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_answers_are_taken_once_each(self):
        out = recording._shown_and_recorded(self.flow, "1,2")
        change = recording.value_on(out, "change")
        for document in (moment_tests.ICP, moment_tests.POSITIONING):
            record_change.answer(
                self.base.root, self.base.base_id, change, document, "not-now"
            )
            with self.assertRaises(record_change.Refused):
                record_change.answer(
                    self.base.root, self.base.base_id, change, document, "not-now"
                )

    def test_an_answer_while_the_lock_is_held_is_busy(self):
        out = recording._shown_and_recorded(self.flow, "1")
        change = recording.value_on(out, "change")
        with mock.patch.object(record_change, "LOCK_WAIT_SECONDS", 0.2):
            with record_change._locked(self.base.base_id):
                with self.assertRaises(record_change.Refused) as refused:
                    record_change.answer(
                        self.base.root, self.base.base_id, change,
                        moment_tests.ICP, "not-now",
                    )
        self.assertEqual(record_change.BUSY, str(refused.exception))


if __name__ == "__main__":
    unittest.main()
