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
from gtmbase.errors import PathError


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


class TestOneLockingSystem(unittest.TestCase):
    """Release B carries 0.3.3: Unit 1.7d's locks and 0.3.3's are one module.

    Every lock file lives in the seat folder's own checked folder of locks,
    the operating system's lock is used where there is one, and a lock file
    only where there is not. A writer's shared hold on a folder and a sweep's
    exclusive one are the same lock file, and where shared holds cannot be
    seen, a sweep never takes a folder.
    """

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.folder = os.path.join(self.sandbox.path, "somewhere")
        os.makedirs(self.folder)

    def test_every_lock_file_lives_in_the_one_private_folder(self):
        from gtmbase import fsutil, join_flow

        home = locks.lock_home()
        self.assertEqual(home, fsutil._lock_home())
        self.assertEqual(home, os.path.dirname(locks.folder_lock_path(self.folder)))
        self.assertEqual(home, os.path.dirname(locks.file_lock_path(self.folder)))
        self.assertEqual(0o700, os.stat(home).st_mode & 0o777)
        self.assertIs(fsutil.FolderLock, locks.FolderLock)
        self.assertIs(fsutil.HeldLock, locks.HeldLock)
        self.assertIs(join_flow.HeldLock, locks.HeldLock)
        self.assertNotEqual(
            locks.folder_lock_path(self.folder), locks.file_lock_path(self.folder)
        )

    def test_a_sweep_takes_a_folder_only_when_no_writer_holds_it(self):
        with locks.FolderLock(self.folder) as writing:
            self.assertTrue(writing.held)
            with locks.FolderLock(self.folder) as another_writer:
                self.assertTrue(another_writer.held)
            with locks.FolderLock(self.folder, exclusive=True) as sweeping:
                self.assertFalse(sweeping.held)
        with locks.FolderLock(self.folder, exclusive=True) as sweeping:
            self.assertTrue(sweeping.held)

    def test_without_the_systems_lock_a_writer_writes_and_a_sweep_takes_nothing(self):
        with mock.patch.object(locks, "IMPLEMENTATION", locks.FileLock):
            with locks.FolderLock(self.folder) as writing:
                self.assertTrue(writing.held)
            with locks.FolderLock(self.folder, exclusive=True) as sweeping:
                self.assertFalse(sweeping.held)
            # A lock on one small file still keeps a second holder out.
            with locks.HeldLock(os.path.join(self.folder, "record.json")):
                with self.assertRaises(PathError):
                    with locks.HeldLock(
                        os.path.join(self.folder, "record.json"), wait_seconds=0.2
                    ):
                        pass

    def test_a_held_file_lock_is_never_removed(self):
        guarded = os.path.join(self.folder, "record.json")
        with locks.HeldLock(guarded):
            pass
        self.assertTrue(os.path.exists(locks.file_lock_path(guarded)))

    def test_reentrant_only_for_the_thread_that_holds_it(self):
        import threading

        guarded = os.path.join(self.folder, "record.json")
        outcome = []
        with locks.HeldLock(guarded, reentrant=True):
            with locks.HeldLock(guarded, reentrant=True, wait_seconds=0.2):
                outcome.append("same thread let through")

            def elsewhere():
                try:
                    with locks.HeldLock(guarded, reentrant=True, wait_seconds=0.2):
                        outcome.append("other thread let through")
                except PathError:
                    outcome.append("other thread waited")

            worker = threading.Thread(target=elsewhere)
            worker.start()
            worker.join(10)
        self.assertEqual(["same thread let through", "other thread waited"], outcome)

    def test_a_lock_folder_somebody_else_can_write_refuses_every_lock(self):
        home = locks.lock_home()
        os.chmod(home, 0o777)
        try:
            with self.assertRaises(PathError) as caught:
                with locks.HeldLock(os.path.join(self.folder, "record.json")):
                    pass
            self.assertEqual(locks.CODE_LOCKS_NOT_PRIVATE, caught.exception.code)
            from gtmbase import ids

            from gtmbase import join_flow

            # The questions about a context change, and the base's writing
            # lock, are refused the same way, each with its one sentence.
            base_id = ids.base_id_random()
            with self.assertRaises(record_change.Refused) as refused:
                with record_change._locked(base_id):
                    pass
            self.assertEqual(join_flow.LOCKS_NOT_PRIVATE, str(refused.exception))
            with self.assertRaises(record_change.Refused) as refused:
                with record_change._writing(base_id):
                    pass
            self.assertEqual(join_flow.LOCKS_NOT_PRIVATE, str(refused.exception))
            with self.assertRaises(Exception) as caught:
                with join_flow.writing(base_id):
                    pass
            self.assertEqual(locks.CODE_LOCKS_NOT_PRIVATE, caught.exception.code)
        finally:
            os.chmod(home, 0o700)


if __name__ == "__main__":
    unittest.main()
