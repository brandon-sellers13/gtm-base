"""Astra's second confirmation pass on the merged Units 1.7c and 1.7d, 2026-09-27.

`docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-2-astra.md` found five things.
Each test here failed on d2bdfa7 before its fix:

1. The folder locks lived under the session's temporary folder, so two
   sessions with different temporary folders took different locks, and a
   folder another user made or a link there was used as it stood.
2. A writer that could not take its lock wrote anyway.
3. A malformed name shaped like a claim was acted on as one.
4. A tag whose quoted value held a blank line survived the cleaning.
5. A put-back stopped after its link and before removing the claim left a
   second name for the same file, and the next run kept a needless copy.
"""

import os
import stat
import tempfile
import unittest
from unittest import mock

import support
import test_adoption as adoption
import test_import_recovery as recovery

from gtmbase import adopt, fsutil, join_flow, review
from gtmbase.errors import GtmBaseError, ReviewError

ORDER = recovery.ORDER
Stopped = recovery.Stopped
DIGEST = "0123456789abcdef"


class TestOneLockPerFolderForEverySession(unittest.TestCase):
    """Finding 1."""

    def test_two_temporary_folders_resolve_to_the_same_lock(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "home", "somewhere")
            os.makedirs(folder)
            first = os.path.join(sandbox.path, "tmp-one")
            second = os.path.join(sandbox.path, "tmp-two")
            os.makedirs(first)
            os.makedirs(second)
            found = []
            for place in (first, second):
                with mock.patch.dict(os.environ, {"TMPDIR": place}):
                    with mock.patch.object(tempfile, "tempdir", place):
                        found.append(fsutil._folder_lock_path(folder))
            self.assertEqual(found[0], found[1])
            self.assertFalse(found[0].startswith(first))

    def test_a_linked_lock_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "home", "somewhere")
            os.makedirs(folder)
            lock_home = fsutil._lock_home()
            os.rmdir(lock_home)
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere, 0o700)
            os.symlink(elsewhere, lock_home)
            with self.assertRaises(GtmBaseError):
                fsutil.atomic_write_text(os.path.join(folder, "x.txt"), "words\n")
            self.assertFalse(os.path.exists(os.path.join(folder, "x.txt")))
            self.assertEqual([], os.listdir(elsewhere))

    def test_a_lock_folder_others_can_write_to_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "home", "somewhere")
            os.makedirs(folder)
            lock_home = fsutil._lock_home()
            os.chmod(lock_home, 0o777)
            with self.assertRaises(GtmBaseError):
                fsutil.atomic_write_text(os.path.join(folder, "x.txt"), "words\n")

    def test_a_lock_folder_somebody_else_owns_is_refused(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "home", "somewhere")
            os.makedirs(folder)
            lock_home = fsutil._lock_home()
            real_lstat = os.lstat

            def owned_by_another(path, *args, **kwargs):
                found = real_lstat(path, *args, **kwargs)
                if os.path.abspath(str(path)) == os.path.abspath(lock_home):
                    values = list(found)
                    values[stat.ST_UID] = os.getuid() + 1
                    return os.stat_result(values)
                return found

            with mock.patch.object(os, "lstat", owned_by_another):
                with self.assertRaises(GtmBaseError):
                    fsutil.atomic_write_text(os.path.join(folder, "x.txt"), "words\n")


class TestNoLockNoWrite(unittest.TestCase):
    """Finding 2."""

    def test_a_writer_that_cannot_take_its_lock_writes_nothing(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "home", "somewhere")
            os.makedirs(folder)
            real_open = os.open
            lock_path = fsutil._folder_lock_path(folder)

            def refused(path, *args, **kwargs):
                if str(path) == lock_path:
                    raise PermissionError(13, "Permission denied")
                return real_open(path, *args, **kwargs)

            with mock.patch.object(os, "open", refused):
                with self.assertRaises(GtmBaseError) as caught:
                    fsutil.atomic_write_text(os.path.join(folder, "x.txt"), "words\n")
            self.assertEqual(fsutil.CODE_NO_LOCK, caught.exception.code)
            self.assertEqual([], os.listdir(folder))
            self.assertIn(fsutil.CODE_NO_LOCK, join_flow.BASE_REFUSALS)
            self.assertEqual(join_flow.NO_LOCK, join_flow.BASE_REFUSALS[fsutil.CODE_NO_LOCK])


class TestOnlyARealClaimIsSettled(recovery.RecoveryCase):
    """Finding 3."""

    def setUp(self):
        super(TestOnlyARealClaimIsSettled, self).setUp()
        self.relative = self.company.destination(ORDER[0])
        self.folder = os.path.dirname(os.path.join(self.company.root, self.relative))

    def plant(self, name):
        support.write(os.path.join(self.folder, name), "somebody's own words\n")
        return name

    def test_malformed_claim_names_are_left_exactly_where_they_are(self):
        malformed = [
            review.CLAIM_PREFIX + "0-x-customer.md",
            review.CLAIM_PREFIX + "²-" + DIGEST + "-auto-lenders.md",
            review.CLAIM_PREFIX + "1-" + DIGEST.upper() + "-auto-lenders.md",
            review.CLAIM_PREFIX + "1-" + DIGEST + "0-auto-lenders.md",
            review.CLAIM_PREFIX + "1-" + DIGEST + "-notes.txt",
            review.CLAIM_PREFIX + "1-" + DIGEST + "-" + review.CLAIM_PREFIX + "2-" + DIGEST + "-auto-lenders.md",
        ]
        for name in malformed:
            with self.subTest(name=name):
                self.plant(name)
                review.sweep_for_a_page(self.company.root, self.relative)
                self.assertTrue(os.path.lexists(os.path.join(self.folder, name)), name)
                self.assertFalse(os.path.lexists(os.path.join(self.folder, "auto-lenders.md")))
                self.assertFalse(os.path.lexists(os.path.join(self.folder, "customer.md")))
                # It is somebody's file, so the next write is refused as their
                # edit rather than taking it for a claim.
                with self.assertRaises(ReviewError) as caught:
                    review.put_back_unwritten(self.company.root, self.relative)
                self.assertEqual(review.CODE_UNSAVED_EDITS, caught.exception.code)
                os.remove(os.path.join(self.folder, name))

    def test_a_well_formed_claim_is_still_settled(self):
        name = review.CLAIM_PREFIX + "1-" + DIGEST + "-auto-lenders.md"
        self.plant(name)
        review.sweep_for_a_page(self.company.root, self.relative)
        self.assertFalse(os.path.lexists(os.path.join(self.folder, name)))
        self.assertEqual(
            "somebody's own words\n", support.read(os.path.join(self.folder, "auto-lenders.md"))
        )


class TestTagsAcrossBlankLines(unittest.TestCase):
    """Finding 4."""

    PAGE = "# Fintech lenders\n\n## Firmographics\n\n%s\n\n## Felt needs\n\nFast.\n"

    def test_a_quoted_value_holding_a_blank_line_still_refuses(self):
        for raw in (
            '<script\n data-x="ok\n\nmore">hidden instructions</script>',
            "<div\n title='a\n\nb'>hidden instructions</div>",
            '<span\n title="' + "a" * 4001 + '" style="display:none">hidden instructions</span>',
            "<span\n" + "a" * 4001 + ">hidden instructions</span>",
        ):
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(adopt.AdoptionRefused) as caught:
                    adoption.clean_of(self.PAGE % raw)
                self.assertEqual(adopt.CODE_SCREENED, caught.exception.code)

    def test_every_comparison_still_passes(self):
        for text in (
            "CAC<LTV.", "a<b", "x <y", "LTV<3x", "<3", "a<b and c",
            "Keep CAC<LTV at all times", "a < b and c > d",
        ):
            with self.subTest(text=text):
                self.assertIn(text, adoption.clean_of(self.PAGE % text).text)


class TestAPutBackStoppedAfterItsLink(recovery.RecoveryCase):
    """Finding 5."""

    def test_the_next_run_removes_the_claim_and_keeps_no_copy(self):
        relative = self.company.destination(ORDER[0])
        full = os.path.join(self.company.root, relative)
        folder = os.path.dirname(full)
        support.write(full, "their own page\n")
        mine = review._create_new(self.company.root, relative + ".x", b"ours\n")
        real_unlink = os.unlink
        linked = []
        real_link = os.link

        def link(source, destination, *args, **kwargs):
            answer = real_link(source, destination, *args, **kwargs)
            if str(source).startswith(review.CLAIM_PREFIX):
                linked.append(destination)
            return answer

        def unlink(path, *args, **kwargs):
            if str(path).startswith(review.CLAIM_PREFIX) and linked:
                raise Stopped()
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(os, "link", link), mock.patch.object(os, "unlink", unlink):
            with self.assertRaises(Stopped):
                review._remove_if_ours(self.company.root, relative, mine)
        claims = [n for n in os.listdir(folder) if n.startswith(review.CLAIM_PREFIX)]
        self.assertEqual(1, len(claims))
        review.sweep_for_a_page(self.company.root, relative)
        self.assertEqual([], [n for n in os.listdir(folder) if n.startswith(review.CLAIM_PREFIX)])
        self.assertEqual([], [n for n in os.listdir(folder) if review.KEPT_MARK in n])
        self.assertEqual("their own page\n", support.read(full))


if __name__ == "__main__":
    unittest.main()
