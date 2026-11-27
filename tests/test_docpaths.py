"""Unit 4.2a of Plan 1: one rule for which paths are base documents.

Before this unit, "may this path be a base document" was answered in several
places, each saying the context folder and nothing else, so a standard or the
source map could never be confirmed, flagged or changed. `docpaths` is the one
answer now, and every module that answered part of the question asks it.
"""

import os
import unittest

import support

from gtmbase import constants, docpaths
from gtmbase.errors import PathError


class TestWhatIsADocument(unittest.TestCase):
    def kind_of(self, path):
        found = docpaths.classify(path)
        return found.kind if found is not None else None

    def test_the_kinds(self):
        for path, kind in (
            ("context/icps.md", docpaths.KIND_CONTEXT),
            ("context/icps/fintech.md", docpaths.KIND_CONTEXT),
            ("context/courier-app/goals.md", docpaths.KIND_CONTEXT),
            ("context/strategy/icp.md", docpaths.KIND_CONTEXT),
            ("standards/ad-testing.md", docpaths.KIND_STANDARD),
            (constants.STACK_PATH, docpaths.KIND_STACK),
            ("skills/ad-testing/SKILL.md", docpaths.KIND_SKILL),
            ("skills/ad-testing/references/rules.md", docpaths.KIND_SKILL),
            ("skills/ad-testing/examples/one-night/output.md", docpaths.KIND_SKILL),
            ("skills/ad-testing/examples/one-night/expected.txt", docpaths.KIND_SKILL),
            ("learning/lessons/cheaper-hooks.md", docpaths.KIND_LESSON),
        ):
            with self.subTest(path=path):
                self.assertEqual(kind, self.kind_of(path))

    def test_the_skill_a_skill_file_belongs_to(self):
        self.assertEqual("ad-testing", docpaths.classify("skills/ad-testing/SKILL.md").skill)
        self.assertIsNone(docpaths.classify("standards/ad-testing.md").skill)

    def test_refused(self):
        """Security: the map, work, the rest of learning, outside, and odd skill shapes."""
        for path in (
            constants.MAP_PATH,
            "work/confirmations/context--icps.md",
            "work/proposals/pending/stg-0000000000000000.md",
            "learning/changes/stg-0000000000000000.md",
            "learning/corrections/2026-10-10-stg-0000000000000000.md",
            "learning/lessons/deeper/one.md",
            "learning/lessons/Capital.md",
            "../outside.md",
            "/etc/passwd",
            "context/../work/x.md",
            "context/icps.txt",
            "standards/nested/one.md",
            "standards/Ad Testing.md",
            "standards/.hidden.md",
            "access/other.md",
            "skills/.gitkeep",
            "skills/ad-testing/run.py",
            "skills/ad-testing/script.sh",
            "skills/ad-testing/skill.md",
            "skills/ad-testing/references/rules.txt",
            "skills/ad-testing/references/deeper/rules.md",
            "skills/ad-testing/examples/one.md",
            "skills/ad-testing/examples/one/deeper/output.md",
            "skills/ad-testing/examples/one/output.json",
            "skills/Ad-Testing/SKILL.md",
            "skills/ad_testing/SKILL.md",
            "CLAUDE.md",
            ".claude/settings.json",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertIsNone(self.kind_of(path))


class TestWhichOperationMayWriteEach(unittest.TestCase):
    def test_the_table(self):
        allowed = {
            "context/icps.md": {"edit", "create", "confirm", "settings"},
            "standards/ad-testing.md": {"edit", "create", "confirm", "settings"},
            constants.STACK_PATH: {"edit", "create", "confirm", "settings"},
            # A lesson is created and never edited (the plan, Astra's finding 7).
            "learning/lessons/cheaper-hooks.md": {"create"},
            # The skills folder opens with Unit 4.2b, not here.
            "skills/ad-testing/SKILL.md": set(),
        }
        for path, operations in allowed.items():
            for operation in docpaths.OPERATIONS:
                with self.subTest(path=path, operation=operation):
                    self.assertEqual(
                        operation in operations,
                        docpaths.may(docpaths.classify(path), operation),
                    )

    def test_nothing_may_be_written_to_what_is_not_a_document(self):
        for operation in docpaths.OPERATIONS:
            self.assertFalse(docpaths.may(None, operation))
        with self.assertRaises(ValueError):
            docpaths.may(docpaths.classify("context/icps.md"), "delete")


class TestTheShapeCheck(unittest.TestCase):
    """The drop-in for the context-only shape check every format used to run."""

    def test_everything_the_context_check_took_is_still_taken(self):
        for path in ("context/icps.md", constants.MAP_PATH, "context/strategy/icp.md"):
            with self.subTest(path=path):
                self.assertEqual(path, docpaths.check_syntax(path))

    def test_and_the_documents_outside_context(self):
        for path in ("standards/ad-testing.md", constants.STACK_PATH):
            with self.subTest(path=path):
                self.assertEqual(path, docpaths.check_syntax(path))

    def test_never_anything_else(self):
        for path in ("work/confirmations/x.md", "../x.md", "standards/a/b.md", "access/x.md"):
            with self.subTest(path=path):
                with self.assertRaises(PathError):
                    docpaths.check_syntax(path)


class TestOnTheDisk(unittest.TestCase):
    """Security: a link, or a folder that is a link, is never a document."""

    def test_a_plain_file_is_its_path(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.write(os.path.join(root, "standards", "ad-testing.md"), "x\n")
            found = docpaths.check(root, "standards/ad-testing.md")
            self.assertEqual(docpaths.KIND_STANDARD, found.kind)

    def test_a_document_not_written_yet_is_its_path_too(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            os.makedirs(root)
            self.assertEqual(
                docpaths.KIND_CONTEXT, docpaths.check(root, "context/goals.md").kind
            )

    def test_links_are_refused(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            outside = os.path.join(sandbox.path, "outside")
            support.write(os.path.join(outside, "one.md"), "x\n")
            os.makedirs(os.path.join(root, "context"))
            os.symlink(os.path.join(outside, "one.md"), os.path.join(root, "context", "icps.md"))
            os.symlink(outside, os.path.join(root, "standards"))
            for path in ("context/icps.md", "standards/one.md"):
                with self.subTest(path=path):
                    with self.assertRaises(PathError):
                        docpaths.check(root, path)

    def test_a_path_that_is_not_a_document_is_refused(self):
        with support.Sandbox() as sandbox:
            with self.assertRaises(PathError):
                docpaths.check(sandbox.path, constants.MAP_PATH)


if __name__ == "__main__":
    unittest.main()
