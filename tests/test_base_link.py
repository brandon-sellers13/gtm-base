"""Building a base in its own drawer and linking it to the folder you work in.

The scenarios here are the ones a person lives through. They name the folder
their marketing material is in, their base is built somewhere else, and from
then on opening Claude Code in their own folder brings the base with it. Then
they rename that folder, then they disconnect it, then they connect it again.

The last class is the acceptance run. A live session cannot be started from a
test, so it is done at the level below: the same calls the hook makes, in the
same order, against a base built the same way.
"""

import datetime
import os
import subprocess
import sys
import unittest

import plain_language
import support

from gtmbase import (
    constants,
    create_base,
    folder_identity,
    ids,
    join_flow,
    machine,
    paths,
    session_start,
    state,
)
from gtmbase.errors import StateError
from gtmbase.gitcmd import GitRunner

TODAY = datetime.date(2026, 9, 7)
NOW = datetime.datetime(2026, 9, 7, 12, 30, 0)
EMAIL = "dana@acme.test"
ICP = "context/strategy/icp.md"
PLUGIN_ROOT = support.PLUGIN_DIR
SHIM = os.path.join(PLUGIN_ROOT, "skills", "join", "scripts", "join.py")

ICP_DRAFT = """---
kind: icp
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Ideal customer profile

## Firmographics

Companies of twenty to two hundred people that sell software to other businesses.
"""


def write_gitconfig():
    support.write(
        os.path.join(os.environ["HOME"], ".gitconfig"),
        "[user]\n\temail = %s\n\tname = Dana\n" % EMAIL,
    )


def content_folder(name="marketing"):
    folder = os.path.join(os.environ["HOME"], name)
    support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
    return os.path.realpath(folder)


def central(name="Acme"):
    return os.path.join(
        os.path.realpath(os.environ["HOME"]), constants.BASES_FOLDER_NAME, name
    )


def build(parent, content_root=None, **options):
    return create_base.create(
        parent,
        create_base.ApprovedFile(ICP, ICP_DRAFT),
        ids.run_id(TODAY),
        PLUGIN_ROOT,
        runner=GitRunner(),
        now=NOW,
        name="Acme",
        content_root=content_root,
        **options
    )


class failing_registration(object):
    """Make the one write that records the folder fail, and only that one.

    The base is built, renamed into place, and then the record of it is written.
    This makes that write refuse the folder the first time it is asked, which is
    the case where a person ends up with a real base and no connection to their
    own folder, and it lets the joining itself go through on the second call so
    the base is not lost as well.
    """

    def __enter__(self):
        self.real = machine.append_joined
        calls = []

        def once(*arguments, **options):
            calls.append(1)
            if len(calls) == 1:
                raise StateError("the record could not be written", code="write-failed")
            return self.real(*arguments, **options)

        machine.append_joined = once
        return self

    def __exit__(self, kind, value, trace):
        machine.append_joined = self.real
        return False


def shim(*arguments):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = support.LIB_DIR
    return subprocess.run(
        [sys.executable, SHIM] + list(arguments),
        cwd=os.environ["HOME"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TestBuildingABaseThatBelongsWithAFolder(unittest.TestCase):
    def test_the_base_is_built_centrally_and_linked_to_the_folder_they_named(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()

            result = build(central(), content_root=folder)

            self.assertEqual(os.path.join(central(), "gtm-base"), result.root)
            self.assertEqual(folder, result.content_root)
            self.assertNotIn(create_base.CODE_LINK_FAILED, result.codes)
            entry = machine.find_joined_by_id(
                machine.load_machine_state(), result.base_id
            )
            self.assertEqual(folder, entry["content_root"])
            self.assertEqual(
                os.stat(folder).st_ino, entry["content_identity"]["ino"]
            )

    def test_nothing_in_the_folder_they_named_is_touched(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            before = sorted(os.listdir(folder))

            build(central(), content_root=folder)

            self.assertEqual(before, sorted(os.listdir(folder)))

    def test_a_base_with_no_folder_named_belongs_with_nothing(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()

            result = build(central())

            self.assertIsNone(result.content_root)
            entry = machine.find_joined_by_id(
                machine.load_machine_state(), result.base_id
            )
            self.assertIsNone(entry["content_root"])

    def test_a_failure_after_the_base_exists_keeps_the_base_and_says_so(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            broken = dict(machine.__dict__)

            with failing_registration():
                result = build(central(), content_root=folder)

            self.assertTrue(os.path.isdir(result.root))
            self.assertIn(create_base.CODE_LINK_FAILED, result.codes)
            self.assertIsNone(result.content_root)
            entry = machine.find_joined_by_id(
                machine.load_machine_state(), result.base_id
            )
            self.assertIsNone(entry["content_root"])
            self.assertEqual(broken.keys(), machine.__dict__.keys())

    def test_a_folder_another_base_has_is_refused_before_anything_is_built(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            first = build(central("First"), content_root=folder).root

            with self.assertRaises(StateError) as caught:
                build(central("Second"), content_root=folder)

            self.assertEqual(machine.CODE_CONTENT_TAKEN, caught.exception.code)
            self.assertEqual(first, getattr(caught.exception, "other_root", None))
            self.assertFalse(os.path.isdir(central("Second")))
            self.assertEqual(1, len(machine.load_machine_state().joined))

    def test_running_the_one_missing_step_again_builds_no_second_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            with failing_registration():
                result = build(central(), content_root=folder)

            join_flow.link_folder(result.root, folder)

            state_now = machine.load_machine_state()
            self.assertEqual(1, len(state_now.joined))
            self.assertEqual(folder, state_now.joined[0]["content_root"])
            self.assertEqual(result.base_id, state_now.joined[0]["base_id"])

    def test_a_place_the_rules_refuse_is_refused_before_anything_is_written(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            outer = os.path.join(os.environ["HOME"], "project")
            os.makedirs(outer)
            support.git(["init", "-b", "main", "-q"], cwd=outer)
            parent = os.path.join(outer, "Acme")

            with self.assertRaises(Exception) as caught:
                build(parent)

            self.assertEqual("inside-repository", getattr(caught.exception, "code", None))
            self.assertFalse(os.path.exists(parent))
            self.assertEqual([".git"], sorted(os.listdir(outer)))

    def test_a_folder_another_program_copies_is_refused_at_the_moment_of_building(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            parent = os.path.join(
                os.environ["HOME"], "Library", "CloudStorage", "Acme"
            )

            with self.assertRaises(Exception) as caught:
                build(parent)

            self.assertEqual("synced-folder", getattr(caught.exception, "code", None))
            self.assertFalse(os.path.exists(parent))


class TestTheShimCommands(unittest.TestCase):
    """The three sentences a person says about the folder their base belongs with."""

    def base(self, name="Acme"):
        write_gitconfig()
        result = build(central(name))
        return result.root, result.base_id

    def test_a_folder_is_linked_unlinked_and_listed(self):
        with support.Sandbox() as sandbox:
            root, base_id = self.base()
            folder = content_folder()

            linked = shim("link", "--base", root, "--folder", folder)
            self.assertEqual(0, linked.returncode, linked.stderr)
            printed = linked.stdout.decode("utf-8")
            self.assertIn("belongs-with=", printed)
            self.assertIn("brings the base with it", printed)

            listed = shim("links")
            self.assertEqual(0, listed.returncode, listed.stderr)
            self.assertIn(folder, listed.stdout.decode("utf-8"))

            unlinked = shim("unlink", "--base", root)
            self.assertEqual(0, unlinked.returncode, unlinked.stderr)
            self.assertIn("no longer linked", unlinked.stdout.decode("utf-8"))

            after = shim("links").stdout.decode("utf-8")
            self.assertIn("belongs-with=none", after)

    def test_a_folder_another_base_belongs_with_is_refused_by_name(self):
        with support.Sandbox() as sandbox:
            first, _first_id = self.base("First")
            second, _second_id = self.base("Second")
            folder = content_folder()
            shim("link", "--base", first, "--folder", folder)

            refused = shim("link", "--base", second, "--folder", folder)

            printed = refused.stdout.decode("utf-8")
            self.assertEqual(1, refused.returncode)
            self.assertIn(first, printed)
            self.assertIn("only one base", printed)
            self.assertIn("codes=content-taken", printed)

    def test_a_folder_inside_a_base_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = self.base()

            refused = shim(
                "link", "--base", root, "--folder", os.path.join(root, "context")
            )

            printed = refused.stdout.decode("utf-8")
            self.assertEqual(1, refused.returncode)
            self.assertIn("codes=content-inside-base", printed)
            self.assertIn("Name a folder of your own instead.", printed)

    def test_a_folder_that_is_not_there_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = self.base()

            refused = shim(
                "link",
                "--base",
                root,
                "--folder",
                os.path.join(os.environ["HOME"], "nowhere"),
            )

            self.assertEqual(1, refused.returncode)
            self.assertIn(
                "not on this computer", refused.stdout.decode("utf-8")
            )


class TestTheMessageThatEndsTheFirstSession(unittest.TestCase):
    """The person is told which folder to open, and it is their own one."""

    def test_it_names_both_folders_when_a_folder_is_linked(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            root = build(central(), content_root=folder).root

            message = join_flow.closing_message(
                root, PLUGIN_ROOT, content_root=folder
            )

            self.assertIn("Open the folder you named, %s" % folder, message)
            self.assertIn("your base will be there", message)
            self.assertIn(root, message)
            self.assertNotIn("{{", message)
            self.assertEqual([], plain_language.find_banned(message), message)
            self.assertEqual([], plain_language.find_dashes(message), message)

    def test_it_names_the_base_alone_when_no_folder_is_linked(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            root = build(central()).root

            message = join_flow.closing_message(root, PLUGIN_ROOT)

            self.assertIn("/cd " + root, message)
            self.assertNotIn("Open the folder you named", message)
            self.assertNotIn("{{", message)

    def test_the_closing_step_reads_the_folder_from_the_record(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            root = build(central(), content_root=folder).root
            run_id = join_flow.new_run()

            closed = join_flow.close_run(
                root, run_id, plugin_root=PLUGIN_ROOT, now=TODAY
            )

            self.assertIn("Open the folder you named, %s" % folder, closed.closing)


class TestNamingTheBaseByTheCompanyItIsFor(unittest.TestCase):
    """Connecting a folder happens from that folder, which is never a base."""

    def base(self, name="Acme"):
        write_gitconfig()
        result = build(central(name))
        return result.root, result.base_id

    def test_a_folder_is_linked_and_unlinked_by_the_company_name(self):
        with support.Sandbox() as sandbox:
            root, _base_id = self.base("Acme")
            folder = content_folder()

            linked = shim("link", "--base", "acme", "--folder", folder)

            self.assertEqual(0, linked.returncode, linked.stderr)
            self.assertIn(folder, shim("links").stdout.decode("utf-8"))

            unlinked = shim("unlink", "--base", "Acme")

            self.assertEqual(0, unlinked.returncode, unlinked.stderr)
            self.assertIn("belongs-with=none", shim("links").stdout.decode("utf-8"))

    def test_naming_no_base_at_all_uses_the_only_one_there_is(self):
        with support.Sandbox() as sandbox:
            self.base("Acme")
            folder = content_folder()

            linked = shim("link", "--folder", folder)

            self.assertEqual(0, linked.returncode, linked.stderr)
            self.assertIn(folder, shim("links").stdout.decode("utf-8"))

    def test_naming_no_base_with_two_of_them_changes_nothing(self):
        with support.Sandbox() as sandbox:
            first, _first = self.base("Acme")
            second, _second = self.base("Beta")
            folder = content_folder()

            refused = shim("link", "--folder", folder)

            printed = refused.stdout.decode("utf-8")
            self.assertEqual(1, refused.returncode)
            self.assertIn(first, printed)
            self.assertIn(second, printed)
            self.assertIn("codes=more-than-one-base", printed)

    def test_the_listing_names_every_base_so_one_can_be_named_back(self):
        with support.Sandbox() as sandbox:
            self.base("Acme")
            self.base("Beta")

            printed = shim("links").stdout.decode("utf-8")

            self.assertIn("name=Acme", printed)
            self.assertIn("name=Beta", printed)

    def test_a_name_no_base_goes_by_is_refused_with_a_way_forward(self):
        with support.Sandbox() as sandbox:
            self.base("Acme")
            folder = content_folder()

            refused = shim("link", "--base", "Nowhere", "--folder", folder)

            printed = refused.stdout.decode("utf-8")
            self.assertEqual(1, refused.returncode)
            self.assertIn("show my linked folders", printed)
            self.assertIn("codes=no-base", printed)

    def test_two_bases_of_one_name_change_nothing_and_name_both(self):
        with support.Sandbox() as sandbox:
            first, _first_id = self.base("Acme")
            second_parent = os.path.join(os.environ["HOME"], "elsewhere", "Acme")
            os.makedirs(second_parent)
            second = build(second_parent).root
            folder = content_folder()

            refused = shim("link", "--base", "Acme", "--folder", folder)

            printed = refused.stdout.decode("utf-8")
            self.assertEqual(1, refused.returncode)
            self.assertIn(first, printed)
            self.assertIn(second, printed)
            self.assertIn("codes=more-than-one-base", printed)


class TestTwoFoldersFromOneSharedCopy(unittest.TestCase):
    """A second copy of one project is not the folder that was connected."""

    def test_a_second_copy_of_the_same_project_wakes_nothing(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            root = build(central()).root
            first = content_folder("project-one")
            support.git(["init", "-b", "main", "-q"], cwd=first)
            support.git(
                ["remote", "add", "origin", "https://github.com/acme/one.git"],
                cwd=first,
            )
            machine.link_content(paths.read_base_id(root), first)

            second = content_folder("project-two")
            support.git(["init", "-b", "main", "-q"], cwd=second)
            support.git(
                ["remote", "add", "origin", "https://github.com/acme/one.git"],
                cwd=second,
            )

            found = paths.resolve_base(
                second, machine.load_machine_state(), GitRunner()
            )

            self.assertEqual(paths.CODE_NONE, found.code)
            self.assertIsNone(found.root)


class TestTheSentencesAreAllPlain(unittest.TestCase):
    def test_the_link_sentences_are_readable_by_a_marketer(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("join_shim", SHIM)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sentences = [
            module.WILL_BE_LINKED % "/Users/example/Acme",
            module.LINKED,
            module.UNLINKED,
            module.FOLDER_TAKEN % "/Users/example/GTM Bases/Acme/gtm-base",
            module.FOLDER_INSIDE_BASE,
            module.FOLDER_MISSING,
            module.NO_LINKS,
            module.NO_BASE_OF_THAT_NAME,
            module.NO_BASE_AT_ALL,
            module.MORE_THAN_ONE_BASE % ("/one/gtm-base", "/two/gtm-base"),
            module.NAME_ALREADY_USED,
            module.PLACE_KEEPS_HISTORY,
            module.PLACE_IS_COPIED,
            module.PLACE_MIGHT_BE_COPIED,
            module.PLACE_IS_A_BASE,
            module.PLACE_TAKEN,
            module.LINK_NOT_RECORDED % "/Users/example/Acme",
            session_start.LINK_MISMATCH,
            session_start.CONTENT_INSIDE_BASE,
            session_start.LINK_CONFLICT % ("/one/gtm-base", "/two/gtm-base"),
        ]
        for sentence in sentences:
            self.assertEqual([], plain_language.find_banned(sentence), sentence)
            self.assertEqual([], plain_language.find_dashes(sentence), sentence)


class TestComingBackToTheBaseFromYourOwnFolder(unittest.TestCase):
    """The acceptance run, one call at a time, in the order a person lives it."""

    def hook(self, cwd, part="context"):
        return session_start.run(
            {"session_id": "s-1", "source": "startup", "cwd": cwd},
            client="claude",
            now=NOW,
            plugin_root=PLUGIN_ROOT,
            part=part,
        )

    def finish(self, root):
        """Give the new base the second and third documents a setup leaves."""
        support.write(
            os.path.join(root, "context", "strategy", "positioning.md"),
            ICP_DRAFT.replace("kind: icp", "kind: positioning").replace(
                "owner: owner@example.com", "owner: " + EMAIL
            ),
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "positioning"], cwd=root, author=EMAIL)

    def test_the_whole_round_trip(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()

            result = build(central(), content_root=folder)
            self.finish(result.root)

            opened = self.hook(folder)
            self.assertIsInstance(opened, str)
            self.assertIn("# Map", opened)

            moved = os.path.realpath(os.path.join(os.environ["HOME"], "renamed"))
            os.rename(folder, moved)

            again = self.hook(moved)
            self.assertIsInstance(again, str)
            self.assertIn("# Map", again)
            entry = machine.find_joined_by_id(
                machine.load_machine_state_raw(), result.base_id
            )
            self.assertEqual(moved, entry["content_root"])

            machine.unlink_content(result.base_id)
            self.assertIsNone(self.hook(moved))

            machine.link_content(result.base_id, moved)
            back = self.hook(moved)
            self.assertIsInstance(back, str)
            self.assertIn("# Map", back)

            self.assertEqual(
                sorted(["positioning.md"]), sorted(os.listdir(moved))
            )

    def test_the_base_itself_still_opens_in_its_own_folder(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            folder = content_folder()
            result = build(central(), content_root=folder)
            self.finish(result.root)

            opened = self.hook(result.root)

            self.assertIsInstance(opened, str)
            self.assertIn("# Map", opened)


if __name__ == "__main__":
    unittest.main()
