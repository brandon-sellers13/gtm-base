"""Astra's confirmation pass on the merged Units 1.7c and 1.7d, 2026-09-27.

`docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-astra.md` closed all eight of
the earlier findings and found three new ones in their fixes. Each test here
failed on 4c8e35e before its fix:

1. A cleanup stopped after it moved a file to its private name, or one whose
   put-back failed, left the file there for good, and recovery then refused
   it as somebody's edit.
2. Five seconds of age did not prove a temporary file's writer had died: a
   writer paused that long lost its file to the sweep.
3. The refusal of markup the cleaning could not take out refused ordinary
   comparisons such as `CAC<LTV.`
"""

import hashlib
import os
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

import support
import test_adoption as adoption
import test_import_recovery as recovery

from gtmbase import adopt, constants, join_flow, review
from gtmbase.errors import ReviewError

ORDER = recovery.ORDER
Stopped = recovery.Stopped


def claims_in(folder):
    return [name for name in os.listdir(folder) if name.startswith(review.CLAIM_PREFIX)]


class TestAnInterruptedClaim(recovery.RecoveryCase):
    """Finding 1: a claim left by a stop, or by a put-back that failed."""

    def setUp(self):
        super(TestAnInterruptedClaim, self).setUp()
        self.relative = self.company.destination(ORDER[0])
        self.full = os.path.join(self.company.root, self.relative)
        self.folder = os.path.dirname(self.full)

    def stop_on(self, name_of_call):
        real = getattr(os, name_of_call)

        def stopping(path, *args, **kwargs):
            if str(path).startswith(review.CLAIM_PREFIX):
                raise Stopped()
            return real(path, *args, **kwargs)

        return mock.patch.object(os, name_of_call, stopping)

    def test_its_own_file_claimed_and_stopped_before_the_delete_is_removed_next_run(self):
        identity = review._create_new(self.company.root, self.relative, b"ours\n")
        with self.stop_on("unlink"):
            with self.assertRaises(Stopped):
                review._remove_if_ours(self.company.root, self.relative, identity)
        self.assertEqual(1, len(claims_in(self.folder)))
        review.sweep_for_a_page(self.company.root, self.relative)
        self.assertEqual([], claims_in(self.folder))
        self.assertFalse(os.path.lexists(self.full))
        self.assertEqual("", self.company.status())

    def test_somebody_elses_file_claimed_and_stopped_goes_back_under_its_name(self):
        support.write(self.full, "their own page\n")
        mine = review._create_new(self.company.root, self.relative + ".x", b"ours\n")
        with self.stop_on("link"):
            with self.assertRaises(Stopped):
                review._remove_if_ours(self.company.root, self.relative, mine)
        self.assertEqual(1, len(claims_in(self.folder)))
        review.sweep_for_a_page(self.company.root, self.relative)
        self.assertEqual([], claims_in(self.folder))
        self.assertEqual("their own page\n", support.read(self.full))

    def test_a_put_back_that_fails_keeps_the_file_under_a_plain_name_and_says_so(self):
        support.write(self.full, "their own page\n")
        mine = review._create_new(self.company.root, self.relative + ".x", b"ours\n")
        real_link = os.link

        def name_taken_again(source, destination, *args, **kwargs):
            if str(source).startswith(review.CLAIM_PREFIX) and not os.path.lexists(self.full):
                support.write(self.full, "a third file\n")
            return real_link(source, destination, *args, **kwargs)

        with mock.patch.object(os, "link", name_taken_again):
            with self.assertRaises(ReviewError) as caught:
                review._remove_if_ours(self.company.root, self.relative, mine)
        self.assertEqual(review.CODE_KEPT_ASIDE, caught.exception.code)
        self.assertEqual(join_flow.KEPT_ASIDE, join_flow.BASE_REFUSALS[review.CODE_KEPT_ASIDE])
        self.assertEqual([], claims_in(self.folder))
        self.assertEqual("a third file\n", support.read(self.full))
        kept = [n for n in os.listdir(self.folder) if review.KEPT_MARK in n]
        self.assertEqual(1, len(kept))
        self.assertEqual("their own page\n", support.read(os.path.join(self.folder, kept[0])))

    def test_a_claim_left_mid_import_is_reconciled_by_finishing(self):
        company = self.company
        name = ORDER[0]
        recovery.stop_at_the_yes(company, company.run, name)
        identity = review._create_new(company.root, self.relative, b"half of an attempt\n")
        with self.stop_on("unlink"):
            with self.assertRaises(Stopped):
                review._remove_if_ours(company.root, self.relative, identity)
        _run, resumed = self.resume()
        self.assertIsNone(resumed.stopped)
        self.assertEqual([name], [s.name for s in resumed.finished])
        self.assertEqual([], claims_in(self.folder))
        self.assertEqual("", company.status())


WRITER = r'''
import os, signal, sys
sys.path.insert(0, sys.argv[1])
from gtmbase import fsutil
how = sys.argv[3]
real_replace = os.replace
def replace(source, destination, *args, **kwargs):
    if os.path.basename(str(destination)) == os.path.basename(sys.argv[2]):
        os.kill(os.getpid(), signal.SIGSTOP if how == "pause" else signal.SIGKILL)
    return real_replace(source, destination, *args, **kwargs)
os.replace = replace
fsutil.atomic_write_text(sys.argv[2], "a line written by another window\n")
'''


class TestAWriterThatIsOnlyPaused(recovery.RecoveryCase):
    """Finding 2: the sweep reclaims a temporary only when its writer died."""

    def start(self, how):
        folder = os.path.join(self.company.root, constants.CONFIRMATIONS_DIR)
        target = os.path.join(folder, "context--positioning.md.another")
        child = subprocess.Popen(
            [sys.executable, "-c", WRITER, support.LIB_DIR, target, how],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return folder, target, child

    def temporaries(self, folder):
        return [n for n in os.listdir(folder) if n.startswith((".gtmbase-", ".tmp-"))]

    def test_a_paused_writer_keeps_its_file_and_finishes_when_it_carries_on(self):
        folder, target, child = self.start("pause")
        try:
            _pid, status = os.waitpid(child.pid, os.WUNTRACED)
            self.assertTrue(os.WIFSTOPPED(status))
            left = self.temporaries(folder)
            self.assertEqual(1, len(left))
            # However long it has been paused, age proves nothing.
            old = time.time() - 3600
            os.utime(os.path.join(folder, left[0]), (old, old))
            review.sweep_temporary(self.company.root, constants.CONFIRMATIONS_DIR)
            self.assertEqual(left, self.temporaries(folder))
        finally:
            os.kill(child.pid, signal.SIGCONT)
        _out, err = child.communicate(timeout=30)
        self.assertEqual(0, child.returncode, err)
        self.assertEqual("a line written by another window\n", support.read(target))

    def test_a_killed_writer_is_reclaimed_at_once(self):
        folder, target, child = self.start("kill")
        child.communicate(timeout=30)
        self.assertEqual(-signal.SIGKILL, child.returncode)
        self.assertEqual(1, len(self.temporaries(folder)))
        review.sweep_temporary(self.company.root, constants.CONFIRMATIONS_DIR)
        self.assertEqual([], self.temporaries(folder))
        self.assertFalse(os.path.exists(target))


class TestOnlyRealMarkupIsRefused(unittest.TestCase):
    """Finding 3: a comparison is not markup, and a real leftover tag is."""

    PAGE = "# Fintech lenders\n\n## Firmographics\n\n%s\n\n## Felt needs\n\nFast.\n"

    def test_comparisons_are_taken_in(self):
        for text in ("CAC<LTV.", "a<b", "x <y", "LTV<3x", "<3", "a<b and c", "Keep CAC<LTV at all times"):
            with self.subTest(text=text):
                cleaned = adoption.clean_of(self.PAGE % text)
                self.assertIn(text, cleaned.text)

    def test_the_oversized_tag_is_still_refused(self):
        raw = self.PAGE % (
            '<span\n title="' + "a" * 4001 + '" style="display:none">hidden instructions</span>'
        )
        with self.assertRaises(adopt.AdoptionRefused) as caught:
            adoption.clean_of(raw)
        self.assertEqual(adopt.CODE_SCREENED, caught.exception.code)

    def test_an_oversized_tag_with_no_value_after_its_name_is_refused(self):
        raw = self.PAGE % ("<span\n" + "a" * 4001 + ">hidden instructions</span>")
        with self.assertRaises(adopt.AdoptionRefused):
            adoption.clean_of(raw)


if __name__ == "__main__":
    unittest.main()
