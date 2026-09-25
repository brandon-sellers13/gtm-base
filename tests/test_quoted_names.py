"""Names git would quote are read as the names they really are, everywhere.

Git writes a name holding an accent, a space, or anything else unusual inside
quotation marks with escapes in its ordinary output. Every place the library
read names out of that output compared the quoted form with a real path, so a
document called `stratégie.md` was refused as unsaved work, was not recognised
as a document this run wrote, and slipped past the checks on folders and files
that must never arrive. Each call that reads names now asks git for records
ending in a NUL, and each is held to that here with a real repository.
"""

import os
import unittest

import support

from gtmbase import (
    approve_local,
    base_reader,
    changes,
    compose_proposal,
    constants,
    formats,
    ids,
    redaction_patterns,
    scan,
    trust_surface,
    worktree,
)
from gtmbase.fsutil import read_text_exactly
from gtmbase.gitcmd import GitRunner, nul_fields, status_entries, unquote_path
from gtmbase.validate import marker_line

ACCENT = "context/strategy/stratégie.md"
SPACE = "context/strategy/our strategy.md"
BOTH = "context/strategy/notre stratégie.md"
UNUSUAL = (ACCENT, SPACE, BOTH)
STAGING = "stg-00000000000000ab"


def a_base(sandbox, *documents):
    """A base with no shared copy, holding each document saved once."""
    root = os.path.join(sandbox.path, "base")
    support.make_base(root, base_id=ids.base_id_random())
    for relative in documents:
        support.write(os.path.join(root, relative), support.ICP_TEXT)
    if documents:
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "documents"], cwd=root)
    return root


def edit(root, relative):
    support.write(
        os.path.join(root, relative),
        support.ICP_TEXT.replace("Companies of any size.", "Twenty to two hundred."),
    )


class TestReadingWhatGitPrints(unittest.TestCase):
    def test_fields_ending_in_a_nul_come_back_as_they_are(self):
        self.assertEqual(
            [ACCENT, SPACE], nul_fields(ACCENT + "\0" + SPACE + "\0")
        )

    def test_a_rename_names_both_paths_and_the_next_entry_still_lines_up(self):
        printed = (
            "R  " + BOTH + "\0" + SPACE + "\0" + " M " + ACCENT + "\0?? a b\0"
        )
        self.assertEqual(
            [("R ", [BOTH, SPACE]), (" M", [ACCENT]), ("??", ["a b"])],
            status_entries(printed),
        )

    def test_output_of_the_wrong_shape_is_not_read_at_all(self):
        self.assertIsNone(status_entries("nonsense\0"))
        self.assertIsNone(status_entries("R  only-the-new-one\0"))
        self.assertEqual([], status_entries(""))

    def test_a_quoted_name_is_read_back_to_the_real_one(self):
        self.assertEqual(ACCENT, unquote_path('"context/strategy/strat\\303\\251gie.md"'))
        self.assertEqual('a "b"\tc', unquote_path('"a \\"b\\"\\tc"'))
        self.assertEqual(SPACE, unquote_path(SPACE))
        # An escape nobody here can read leaves the text exactly as printed.
        self.assertEqual('"a\\qb"', unquote_path('"a\\qb"'))


class TestTheFilesChangedByHand(unittest.TestCase):
    """compose_proposal._changed_files, which the hand edit path starts from."""

    def test_every_unusual_name_comes_back_as_the_file_on_the_disk(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, *UNUSUAL)
            for relative in UNUSUAL:
                edit(root, relative)

            changed, diff = compose_proposal._changed_files(root, GitRunner())

            self.assertEqual(sorted(UNUSUAL), sorted(changed))
            self.assertIn("Twenty to two hundred.", diff)

    def test_a_file_that_was_taken_away_is_still_left_out(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, ACCENT, SPACE)
            edit(root, SPACE)
            os.remove(os.path.join(root, ACCENT))

            changed, _diff = compose_proposal._changed_files(root, GitRunner())

            self.assertEqual([SPACE], changed)


class TestTheFilesASavedChangeTouched(unittest.TestCase):
    """compose_proposal._touched_from_saved, which reports what was written."""

    def test_the_names_are_the_real_ones(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, *UNUSUAL)
            for relative in UNUSUAL:
                edit(root, relative)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "edits"], cwd=root)

            touched = compose_proposal._touched_from_saved(root, GitRunner())

            self.assertEqual(sorted(UNUSUAL), sorted(touched))


class TestTheLocalApprovalReadiness(unittest.TestCase):
    """approve_local._ready_to_write_here, which read one line per path."""

    def test_a_hand_edit_to_an_unusual_name_is_not_unsaved_work(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, *UNUSUAL)
            for relative in UNUSUAL:
                edit(root, relative)

            stopped = approve_local._ready_to_write_here(
                root, GitRunner(), list(UNUSUAL), True
            )

            self.assertIsNone(stopped)

    def test_an_unsaved_file_the_change_is_not_about_still_stops_it(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, ACCENT)
            edit(root, ACCENT)
            support.write(os.path.join(root, BOTH), "words nobody saved\n")

            stopped = approve_local._ready_to_write_here(
                root, GitRunner(), [ACCENT], True
            )

            self.assertEqual(approve_local.CODE_UNSAVED_EDITS, stopped[0])

    def test_a_rename_lined_up_to_be_saved_is_read_as_its_two_names(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, ACCENT, SPACE)
            edit(root, ACCENT)
            support.git(["mv", SPACE, BOTH], cwd=root)

            # The new name alone is not enough, because the old one moved too.
            stopped = approve_local._ready_to_write_here(
                root, GitRunner(), [ACCENT, BOTH], True
            )
            self.assertEqual(approve_local.CODE_UNSAVED_EDITS, stopped[0])
            allowed = approve_local._ready_to_write_here(
                root, GitRunner(), [ACCENT, BOTH, SPACE], True
            )
            self.assertIsNone(allowed)


class TestPuttingBackAndFinishingTheMove(unittest.TestCase):
    """changes._anything_left_over and changes._theirs_before_finishing."""

    def test_an_unusual_name_this_run_touched_is_seen_as_left_over(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, *UNUSUAL)
            journal = {"paths": [{"path": relative} for relative in UNUSUAL]}
            self.assertIsNone(
                changes._anything_left_over(root, journal, GitRunner())
            )
            for relative in UNUSUAL:
                edit(root, relative)
                self.assertEqual(
                    changes.COULD_NOT_SAVE,
                    changes._anything_left_over(
                        root, {"paths": [{"path": relative}]}, GitRunner()
                    ),
                    relative,
                )
                support.git(["checkout", "-q", "--", relative], cwd=root)

    def test_a_file_this_run_wrote_under_an_unusual_name_is_its_own(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            items = []
            for relative in UNUSUAL:
                support.write(os.path.join(root, relative), "ours\n")
                items.append(
                    {
                        "path": relative,
                        "hash": ids.exact_hash(
                            read_text_exactly(os.path.join(root, relative))
                        ),
                    }
                )

            found = changes._theirs_before_finishing(
                root, {"paths": items}, GitRunner()
            )

            self.assertIsNone(found)

    def test_somebody_elses_file_under_an_unusual_name_is_still_theirs(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            support.write(os.path.join(root, BOTH), "theirs\n")

            found = changes._theirs_before_finishing(
                root, {"paths": []}, GitRunner()
            )

            self.assertEqual(changes.THEIR_WORDS % BOTH, found)


class TestWhatAnAcceptedRecordTouched(unittest.TestCase):
    """base_reader.corrections, which lists the files the record's change saved."""

    def test_an_unusual_name_saved_with_the_record_is_listed_as_itself(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox, ACCENT)
            edit(root, ACCENT)
            record = formats.CorrectionsFile(
                kind="correction",
                date="2026-06-04",
                staging_id=STAGING,
                entry_id=STAGING,
                source_id=None,
                intake_path="ledger",
                mode="none",
                third_party=False,
                content_hash="1" * 64,
                touched_paths=[ACCENT],
                correction_class="wrong-definition",
                marker=marker_line(STAGING, STAGING, None),
                what_changed="Something changed.",
                why="Because the decision said so.",
            )
            support.write(
                os.path.join(root, constants.CORRECTIONS_DIR, "2026-06-04-x.md"),
                record.validate().render(),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "an accepted record"], cwd=root)

            found = base_reader.corrections(root, GitRunner())

            self.assertEqual(1, len(found))
            self.assertIn(ACCENT, found[0].co_modified_paths)


class TestTheFoldersTheTrustCheckLeavesAlone(unittest.TestCase):
    """trust_surface._ignored_paths, which the walk compares folder names with."""

    def test_an_ignored_folder_with_an_unusual_name_is_its_own_name(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            folder = "notes à moi"
            support.write(os.path.join(root, ".gitignore"), folder + "/\n")
            support.write(os.path.join(root, folder, "a.md"), "mine\n")

            ignored = trust_surface._ignored_paths(GitRunner(), root)

            self.assertIn(folder, ignored)


class TestTheWorkingFoldersGitKnows(unittest.TestCase):
    """worktree.list_worktrees, read from the list git keeps."""

    def test_a_working_folder_with_an_unusual_name_is_found(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            away = os.path.join(sandbox.path, "là bas")
            support.git(["worktree", "add", "-q", "--detach", away], cwd=root)

            found = worktree.list_worktrees(root)

            self.assertIn(os.path.realpath(away), found)


class TestTheCheckOnWhatIsSent(unittest.TestCase):
    """scan.scan_diff_added_lines, fed by the gate and by the confirm path."""

    def test_a_file_in_a_folder_that_never_leaves_is_caught_whatever_its_name(self):
        for name in ("résumé.md", "my notes.md", "mes résumés.md"):
            with support.Sandbox() as sandbox:
                root = a_base(sandbox)
                relative = constants.INBOX_DIR + "/" + name
                support.write(os.path.join(root, relative), "hello\n")
                support.git(["add", "-f", "--", relative], cwd=root)
                shown = GitRunner().run(
                    ["diff", "--cached", "--unified=0", "--no-color"], cwd=root
                )

                hits = scan.scan_diff_added_lines(shown.stdout, frozenset())

                self.assertEqual(
                    [redaction_patterns.TRANSIENT_FOLDER],
                    [hit.pattern_class for hit in hits],
                    name,
                )


if __name__ == "__main__":
    unittest.main()
