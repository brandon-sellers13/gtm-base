"""Plan 1, Unit 4.2b: what a base's skills folder admits, and who may write there.

The signed company-skills requirements CS19 to CS22. Admission and writing
are two rules, tested apart. The folder admits a skill's `SKILL.md`, its
references and its examples in exact shapes, on disk when a base is opened,
on an update from the shared copy, and in a send; everything else stays
refused on all three. A file tool writing even an admitted shape stays
refused, because only GTM Base's own operations write a skill. One hostile
fixture per clause. Every fixture is written from scratch.
"""

import os
import stat
import unittest

import support

from gtmbase import constants, gate, layout, session_start, skillshape, trust_surface, write_hook
from gtmbase.gitcmd import GitRunner

SKILL_MD = "skills/weekly-readout/SKILL.md"
REFERENCE = "skills/weekly-readout/references/how-to-read.md"
EXAMPLE = "skills/weekly-readout/examples/a-quiet-week/input.md"
EXAMPLE_TXT = "skills/weekly-readout/examples/a-quiet-week/summary.txt"

GOOD_SKILL = """---
name: weekly-readout
description: Write the weekly readout.
owner: owner@example.com
kind: skill
sources: []
status: draft
reads_required: [context/goals.md]
standard: standards/weekly-readout.md
---

# Weekly readout

Read the goals.
"""

ADMITTED = {
    SKILL_MD: GOOD_SKILL,
    REFERENCE: "# How to read\n",
    EXAMPLE: "Summarise the week.\n",
    EXAMPLE_TXT: "Spend: $1,200\n",
}

# One hostile fixture per clause of CS19 to CS21: (path, text, executable).
REFUSED = (
    ("a script", "skills/weekly-readout/run.py", "print('hi')\n", False),
    ("a shell file", "skills/weekly-readout/references/run.sh", "echo hi\n", False),
    ("a hidden file", "skills/weekly-readout/.notes.md", "# Notes\n", False),
    ("too deep", "skills/weekly-readout/examples/a/b/input.md", "Deep.\n", False),
    ("a reference that is text", "skills/weekly-readout/references/notes.txt", "Notes.\n", False),
    ("a name in capitals", "skills/weekly-readout/references/How.md", "# How\n", False),
    ("an executable file", REFERENCE, "# How to read\n", True),
    ("a power-granting key", SKILL_MD, GOOD_SKILL.replace("kind: skill\n", "kind: skill\nallowed-tools: Bash\n"), False),
    ("a hooks key", SKILL_MD, GOOD_SKILL.replace("kind: skill\n", "kind: skill\nhooks: {}\n"), False),
    ("too large", REFERENCE, "# Big\n" + "words " * 12000, False),
    # The security pass on Unit 4.2b, finding 6: a key hidden behind a lone carriage return.
    ("a hidden key", SKILL_MD, GOOD_SKILL.replace("kind: skill\n", "kind: skill\rallowed-tools: Bash\n"), False),
)


def a_base(sandbox):
    root, _base_id = sandbox.base()
    return root


def put(root, files, executable=()):
    for path, text in files.items():
        full = support.write(os.path.join(root, path), text)
        if path in executable:
            os.chmod(full, os.stat(full).st_mode | stat.S_IXUSR)


def trust_codes(root):
    return trust_surface.check(root, runner=GitRunner()).codes


class TestTheShapes(unittest.TestCase):
    def test_the_admitted_shapes_by_name(self):
        for path in ADMITTED:
            with self.subTest(path=path):
                parts = [part.casefold() for part in path.split("/")]
                self.assertFalse(layout.is_refused_in_skills(parts))
        for folder in ("skills/weekly-readout", "skills/weekly-readout/references",
                       "skills/weekly-readout/examples", "skills/weekly-readout/examples/a-quiet-week"):
            with self.subTest(folder=folder):
                self.assertFalse(layout.is_refused_in_skills(folder.split("/"), True))

    def test_each_refused_file_by_its_content(self):
        for clause, path, text, executable in REFUSED:
            with self.subTest(clause=clause):
                mode = "100755" if executable else skillshape.REGULAR_MODE
                self.assertIsNotNone(skillshape.file_problem(path, text.encode("utf-8"), mode))

    def test_more_than_fifty_files_in_one_skill(self):
        paths = ["skills/big/examples/e%d/input.md" % number for number in range(51)]
        self.assertTrue(skillshape.too_many(paths))
        self.assertFalse(skillshape.too_many(paths[:50]))


class TestOnTheDisk(unittest.TestCase):
    def test_an_admitted_skill_is_trusted_when_the_base_is_opened(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            put(root, ADMITTED)
            self.assertNotIn(trust_surface.CODE_SKILLS_FILE, trust_codes(root))

    def test_each_refused_file_is_refused_when_the_base_is_opened(self):
        for clause, path, text, executable in REFUSED:
            with self.subTest(clause=clause), support.Sandbox() as sandbox:
                root = a_base(sandbox)
                put(root, ADMITTED)
                put(root, {path: text}, executable=(path,) if executable else ())
                codes = trust_codes(root)
                self.assertTrue(
                    trust_surface.CODE_SKILLS_FILE in codes or trust_surface.CODE_CODE_FILE in codes,
                    codes,
                )

    def test_a_link_in_the_skills_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            put(root, ADMITTED)
            os.symlink(os.path.join(root, SKILL_MD), os.path.join(root, REFERENCE + ".md"))
            self.assertIn(trust_surface.CODE_SYMLINK, trust_codes(root))


class TestOnAnUpdate(unittest.TestCase):
    def incoming(self, root, files, executable=()):
        support.git(["checkout", "-q", "-b", "incoming"], cwd=root)
        put(root, files, executable)
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "incoming"], cwd=root)
        support.git(["checkout", "-q", "main"], cwd=root)
        return session_start._incoming_contents_refused(
            root, "incoming", sorted(files), GitRunner()
        )

    def test_an_admitted_skill_arrives(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            self.assertEqual([], self.incoming(root, ADMITTED))
            for path in ADMITTED:
                self.assertFalse(session_start._is_refused_path(path))

    def test_each_refused_content_does_not_arrive(self):
        for clause, path, text, executable in REFUSED:
            if not skillshape.admitted_shape([part.casefold() for part in path.split("/")]):
                # Refused by its name alone, which the next test holds.
                continue
            with self.subTest(clause=clause), support.Sandbox() as sandbox:
                root = a_base(sandbox)
                found = self.incoming(root, {path: text}, executable=(path,) if executable else ())
                self.assertEqual([path], found)

    def test_a_name_outside_the_shapes_is_refused_by_name(self):
        for clause, path, _text, _executable in REFUSED:
            if skillshape.admitted_shape([part.casefold() for part in path.split("/")]):
                continue
            with self.subTest(clause=clause):
                parts = [part.casefold() for part in path.split("/")]
                if clause == "a name in capitals":
                    # Case folded names cannot tell; the content check reads the exact case.
                    self.assertIsNotNone(skillshape.file_problem(path, b"# How\n", skillshape.REGULAR_MODE))
                    continue
                self.assertTrue(trust_surface.path_is_refused(parts), clause)


class TestInASend(unittest.TestCase):
    def sent(self, root, files, executable=()):
        start = support.head_of(root)
        put(root, files, executable)
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a skill"], cwd=root)
        return gate._skills_in_every_piece_of_work(GitRunner(), root, start, support.head_of(root))

    def test_an_admitted_skill_may_be_sent(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            self.assertFalse(self.sent(root, ADMITTED))

    def test_each_refused_file_may_not_be_sent(self):
        for clause, path, text, executable in REFUSED:
            with self.subTest(clause=clause), support.Sandbox() as sandbox:
                root = a_base(sandbox)
                files = dict(ADMITTED)
                files[path] = text
                self.assertTrue(self.sent(root, files, executable=(path,) if executable else ()))


class TestWritingIsSeparate(unittest.TestCase):
    def test_a_file_tool_writing_an_admitted_shape_is_refused(self):
        with support.Sandbox() as sandbox:
            root = a_base(sandbox)
            for path in ADMITTED:
                with self.subTest(path=path):
                    found = write_hook._into_a_bases_skills(
                        os.path.join(root, path), os.path.join(root, path)
                    )
                    self.assertEqual(write_hook.CODE_SKILLS_FILE, found)

    def test_the_placeholder_stays_as_it_was(self):
        self.assertFalse(
            skillshape.written_only_by_gtm_base([constants.SKILLS_DIR, constants.PLACEHOLDER_NAME])
        )


if __name__ == "__main__":
    unittest.main()
