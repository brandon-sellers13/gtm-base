"""Track 4, Units T4.9 and T4.10: a skill may declare the segments folder.

The runner is security-reviewed code, so the one folder declaration it now
takes is held to these edges, one test each:

1. `reads_optional` may name exactly `context/icps/`, and no other folder,
   and never among what a skill requires.
2. Only `.md` files sitting directly in that folder are handed back, as the
   base last saved them: no subfolder, no link, nothing outside the base.
3. Each goes through the moment-of-use check like any other document.
4. An empty or missing folder is not a gap.

Every fixture is written from scratch; the company is made up.
"""

import os
import unittest
from unittest import mock

import support
import test_runner_contract as contract

from gtmbase import moment, runner

FOLDER = runner.SEGMENTS_FOLDER
SEGMENT = "context/icps/long-distance.md"
OTHER = "context/icps/storage.md"


def a_segment(title):
    return support.skill_document("segment", title)


def a_base(sandbox, segments=None, optional=(FOLDER,)):
    documents = contract.the_documents()
    documents.update(segments if segments is not None else {SEGMENT: a_segment("Long-distance movers")})
    return contract.a_base(
        sandbox, documents=documents, files=contract.the_skill(optional=optional)
    )


def saved(root, message="more files"):
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", message], cwd=root)


class TheDeclaration(unittest.TestCase):
    def test_the_segments_folder_may_be_declared_among_what_a_skill_reads_if_present(self):
        declared = runner.declaration_of(contract.skill_text(optional=(FOLDER,)))
        self.assertEqual([], declared.problems)
        self.assertEqual([FOLDER], declared.optional)

    def test_no_other_folder_may_be_declared(self):
        for folder in ("context/", "context/strategy/", "context/icps", "context/icps/x/", "standards/"):
            with self.subTest(folder=folder):
                declared = runner.declaration_of(contract.skill_text(optional=(folder,)))
                self.assertTrue(declared.problems, folder)

    def test_the_folder_may_never_be_required(self):
        declared = runner.declaration_of(
            contract.skill_text(required=(contract.GOALS, FOLDER))
        )
        self.assertIn((runner.READS_REQUIRED, FOLDER), declared.problems)

    def test_a_skill_declaring_another_folder_is_refused_at_start(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox, optional=("context/strategy/",))
            result = contract.run(root, base_id)
            self.assertEqual(runner.REFUSED_INVALID, result.refusal)


class WhatIsHandedBack(unittest.TestCase):
    def test_each_saved_segment_is_handed_back_in_order(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(
                sandbox, {SEGMENT: a_segment("Long-distance"), OTHER: a_segment("Storage")}
            )
            result = contract.run(root, base_id)
            self.assertEqual(runner.OUTCOME_READY, result.outcome)
            self.assertEqual(
                [contract.STANDARD, contract.GOALS, contract.POSITIONING, SEGMENT, OTHER],
                list(result.documents),
            )

    def test_only_markdown_sitting_directly_in_the_folder(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            support.write(os.path.join(root, "context", "icps", "notes.txt"), "Some notes.\n")
            support.write(
                os.path.join(root, "context", "icps", "older", "deep.md"),
                a_segment("A segment one folder down"),
            )
            saved(root)
            result = contract.run(root, base_id)
            segments = [path for path in result.documents if path.startswith(FOLDER)]
            self.assertEqual([SEGMENT], segments)

    def test_a_link_is_never_followed_or_handed_back(self):
        with support.Sandbox() as sandbox:
            outside = os.path.join(sandbox.path, "outside.md")
            support.write(outside, a_segment("Outside the base"))
            root, base_id = a_base(sandbox)
            os.symlink(outside, os.path.join(root, "context", "icps", "outside.md"))
            os.symlink(
                os.path.join("..", "positioning.md"),
                os.path.join(root, "context", "icps", "inside.md"),
            )
            saved(root, "links")
            result = contract.run(root, base_id)
            segments = [path for path in result.documents if path.startswith(FOLDER)]
            self.assertEqual([SEGMENT], segments)
            self.assertNotIn("Outside the base", "".join(result.documents.values()))

    def test_a_segment_only_on_the_disk_is_not_handed_back(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            support.write(os.path.join(root, OTHER), a_segment("Not saved yet"))
            result = contract.run(root, base_id)
            self.assertNotIn(OTHER, result.documents)

    def test_each_segment_goes_through_the_moment_of_use_check(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(
                sandbox, {SEGMENT: a_segment("Long-distance"), OTHER: a_segment("Storage")}
            )
            checked = []
            real = moment.check

            def recording(base_root, base_id_, path, **kwargs):
                checked.append(path)
                return real(base_root, base_id_, path, **kwargs)

            with mock.patch.object(moment, "check", side_effect=recording):
                contract.run(root, base_id)
            self.assertIn(SEGMENT, checked)
            self.assertIn(OTHER, checked)

    def test_a_flagged_segment_flags_the_run(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            contract.a_change_about(root, SEGMENT)
            result = contract.run(root, base_id)
            self.assertEqual(runner.OUTCOME_FLAGGED, result.outcome)
            self.assertEqual([SEGMENT], result.flagged)


class NoSegmentsIsNotAGap(unittest.TestCase):
    def test_a_missing_folder_is_not_a_gap(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox, segments={})
            self.assertFalse(os.path.exists(os.path.join(root, "context", "icps")))
            result = contract.run(root, base_id)
            self.assertEqual(runner.OUTCOME_READY, result.outcome)
            self.assertEqual([], result.gaps)

    def test_a_folder_holding_nothing_it_hands_back_is_not_a_gap(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox, segments={})
            support.write(os.path.join(root, "context", "icps", "readme.txt"), "Nothing yet.\n")
            saved(root)
            result = contract.run(root, base_id)
            self.assertEqual(runner.OUTCOME_READY, result.outcome)
            self.assertEqual([], result.gaps)


if __name__ == "__main__":
    unittest.main()
