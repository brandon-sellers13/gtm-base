"""Turning the first approved file into a base, and recovering a run that stopped.

Every scenario builds real repositories in temporary folders, with a temporary
home folder holding its own git settings file, so the machine's own identity,
its default branch setting, and the person's real seat folder are never read
and never written.
"""

import datetime
import filecmp
import hashlib
import json
import os
import subprocess
import unittest
from unittest import mock

import plain_language
import support
import test_stale_check as builders

from gtmbase import (
    base_reader,
    constants,
    create_base,
    formats,
    ids,
    install_git_hook,
    location,
    machine,
    paths,
    stale,
    state,
)
from gtmbase.errors import CreateFailed, IdentityNeeded, LocationError
from gtmbase.gitcmd import GitRunner

TODAY = datetime.date(2026, 6, 5)
NOW = datetime.datetime(2026, 6, 5, 12, 30, 0)
ICP = "context/strategy/icp.md"
EMAIL = "dana@acme.test"
PLUGIN_ROOT = support.PLUGIN_DIR

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


def runner():
    return GitRunner()


def approved(text=ICP_DRAFT, path=ICP):
    return create_base.ApprovedFile(path, text)


def write_gitconfig(text):
    path = os.path.join(os.environ["HOME"], ".gitconfig")
    support.write(path, text)
    return path


def content_folder(name="marketing"):
    folder = os.path.join(os.environ["HOME"], name)
    support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
    return folder


def local_config(root, key):
    finished = subprocess.run(
        ["git", "config", "--local", "--get", key], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


def commit_count(root):
    finished = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=root, stdout=subprocess.PIPE
    )
    return int(finished.stdout.decode("utf-8").strip() or "0")


def files_in_head(root):
    finished = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
    )
    return sorted(
        line.strip()
        for line in finished.stdout.decode("utf-8").split("\n")
        if line.strip()
    )


def digest_of(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def listing_of(folder, skip=()):
    """Every file under a folder with its contents hashed, leaving some out."""
    skipped = tuple(os.path.realpath(item) for item in skip)
    found = {}
    for here, subfolders, filenames in os.walk(folder):
        real_here = os.path.realpath(here)
        if any(
            real_here == item or real_here.startswith(item + os.sep)
            for item in skipped
        ):
            subfolders[:] = []
            continue
        for name in filenames:
            path = os.path.join(here, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            found[os.path.relpath(path, folder)] = digest_of(path)
    return found


def make(parent, run=None, **options):
    return create_base.create(
        parent,
        options.pop("approved_file", approved()),
        run or ids.run_id(TODAY),
        options.pop("plugin_root", PLUGIN_ROOT),
        runner=options.pop("runner", None) or runner(),
        now=options.pop("now", NOW),
        **options
    )


class TestTheFirstApprovedFileBecomesABase(unittest.TestCase):
    """One yes, and the person has a base beside the material they already had."""

    def test_the_base_holds_everything_it_needs_after_one_approval(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n\tname = Dana\n")
            parent = content_folder()
            run = ids.run_id(TODAY)

            result = make(parent, run=run, name="Acme")

            root = result.root
            self.assertEqual(os.path.join(os.path.realpath(parent), "gtm-base"), root)
            self.assertTrue(os.path.isdir(os.path.join(root, ".git")))
            self.assertEqual("main", support.branch_of(root))
            self.assertEqual(EMAIL, local_config(root, "user.email"))
            self.assertEqual(result.base_id, local_config(root, "gtmbase.id"))
            self.assertEqual(EMAIL, result.email)

            for folder in constants.TEMPLATE_TREE_DIRS:
                self.assertTrue(
                    os.path.isdir(os.path.join(root, folder.replace("/", os.sep))),
                    folder,
                )

            settings = json.loads(support.read(os.path.join(root, constants.SETTINGS_PATH)))
            self.assertEqual(
                sorted(["extraKnownMarketplaces", "enabledPlugins"]),
                sorted(settings.keys()),
            )
            source = settings["extraKnownMarketplaces"][constants.MARKETPLACE_NAME][
                "source"
            ]
            self.assertEqual(constants.MARKETPLACE_REPO, source["repo"])
            self.assertEqual(constants.PINNED_SHA_PLACEHOLDER, source["sha"])
            self.assertEqual({constants.PLUGIN_KEY: True}, settings["enabledPlugins"])

            allowlist = support.read(os.path.join(root, constants.ALLOWLIST_PATH))
            self.assertIn(EMAIL, allowlist)
            self.assertNotIn(constants.OWNER_PLACEHOLDER_EMAIL, allowlist)

            self.assertEqual(1, commit_count(root))
            confirmations = constants.CONFIRMATIONS_DIR + "/" + ICP.replace("/", "--")
            self.assertIn(ICP, files_in_head(root))
            self.assertIn(confirmations, files_in_head(root))

            block, _body = formats.split_document(
                support.read(os.path.join(root, ICP))
            )
            self.assertEqual(EMAIL, formats.parse_frontmatter(block)["owner"])

            lines, bad = formats.parse_confirmations_file(
                support.read(os.path.join(root, confirmations))
            )
            self.assertEqual([], bad)
            self.assertEqual(1, len(lines))
            self.assertEqual("drafted", lines[0].trigger)
            self.assertEqual(run, lines[0].run)
            self.assertEqual(TODAY.isoformat(), lines[0].date)

            state_now = machine.load_machine_state(runner=runner())
            entry = machine.find_joined_by_root(state_now, root)
            self.assertIsNotNone(entry)
            self.assertEqual(result.base_id, entry["base_id"])

            hook = os.path.join(root, ".git", "hooks", install_git_hook.HOOK_NAME)
            self.assertTrue(os.path.isfile(hook))

            seat, _problems = state.load_seat(result.base_id)
            self.assertFalse(seat["first_push_reviewed"])

    def test_the_map_carries_the_owners_own_address(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            result = make(content_folder())

            text = support.read(os.path.join(result.root, constants.MAP_PATH))
            self.assertIn("owner: " + EMAIL, text)
            self.assertNotIn(constants.OWNER_PLACEHOLDER_EMAIL, text)


class TestTheIdentityTheBaseIsBuiltWith(unittest.TestCase):
    """The address stays inside the base, and the machine's own is never touched."""

    def test_the_machines_default_branch_setting_is_ignored(self):
        with support.Sandbox() as sandbox:
            write_gitconfig(
                "[user]\n\temail = dana@acme.test\n[init]\n\tdefaultBranch = trunk\n"
            )

            result = make(content_folder())

            self.assertEqual("main", support.branch_of(result.root))

    def test_the_machines_own_address_is_used_and_written_into_the_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            result = make(content_folder())

            self.assertEqual(EMAIL, result.email)
            self.assertEqual(EMAIL, local_config(result.root, "user.email"))

    def test_no_address_anywhere_asks_the_person_and_leaves_nothing_behind(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[init]\n\tdefaultBranch = main\n")
            parent = content_folder()
            before = sorted(os.listdir(parent))

            with self.assertRaises(IdentityNeeded):
                make(parent)

            self.assertEqual(before, sorted(os.listdir(parent)))
            self.assertEqual([], create_base.find_partial_folders(parent))

    def test_the_address_the_person_gave_is_written_inside_the_base_only(self):
        with support.Sandbox() as sandbox:
            config = write_gitconfig("[init]\n\tdefaultBranch = main\n")
            before = digest_of(config)

            result = make(content_folder(), email="jess@acme.test", name="Acme")

            self.assertEqual("jess@acme.test", result.email)
            self.assertEqual(
                "jess@acme.test", local_config(result.root, "user.email")
            )
            self.assertEqual("Acme", local_config(result.root, "user.name"))
            self.assertEqual(before, digest_of(config))

    def test_an_address_that_is_not_one_plain_address_is_refused(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("")

            with self.assertRaises(IdentityNeeded) as caught:
                make(content_folder(), email="Dana <dana@acme.test>")
            self.assertEqual(create_base.CODE_BAD_EMAIL, caught.exception.code)


class TestARunThatStoppedPartWay(unittest.TestCase):
    """Every place a run can stop has a rule, and none of them loses the yes."""

    def test_stopping_before_the_rename_leaves_the_half_built_folder_named(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            parent = content_folder()

            def refuse(source, destination):
                raise OSError("no")

            with mock.patch.object(create_base.os, "rename", refuse):
                with self.assertRaises(CreateFailed) as caught:
                    make(parent)

            failure = caught.exception
            self.assertEqual(create_base.CODE_RENAME_FAILED, failure.code)
            self.assertFalse(os.path.exists(os.path.join(parent, "gtm-base")))
            partials = create_base.find_partial_folders(parent)
            self.assertEqual([failure.partial_path], partials)
            self.assertTrue(os.path.isdir(failure.partial_path))
            # The failure carries the code and the folder, and nothing else.
            self.assertEqual((failure.code,), failure.args)
            self.assertEqual(
                {"code", "partial_path"},
                {
                    name
                    for name in vars(failure)
                    if not name.startswith("_")
                },
            )

            self.assertTrue(create_base.remove_partial(failure.partial_path, parent))
            self.assertEqual([], create_base.find_partial_folders(parent))

    def test_a_half_built_folder_is_never_taken_for_a_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            parent = content_folder()
            with mock.patch.object(
                create_base.os, "rename", lambda a, b: (_ for _ in ()).throw(OSError())
            ):
                with self.assertRaises(CreateFailed) as caught:
                    make(parent)

            found = paths.resolve_base(parent, machine.load_machine_state())

            self.assertEqual(paths.CODE_NONE, found.code)

    def test_only_a_half_built_folder_can_be_deleted(self):
        with support.Sandbox() as sandbox:
            parent = content_folder()
            with self.assertRaises(CreateFailed):
                create_base.remove_partial(parent)
            other = os.path.join(os.environ["HOME"], "elsewhere")
            os.makedirs(other)
            partial = os.path.join(other, constants.PARTIAL_FOLDER_PREFIX + "abcd1234")
            os.makedirs(partial)
            with self.assertRaises(CreateFailed):
                create_base.remove_partial(partial, parent)
            self.assertTrue(os.path.isdir(partial))

    def test_stopping_after_the_rename_leaves_a_folder_shaped_like_a_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            parent = content_folder()

            def refuse(**options):
                raise RuntimeError("stopped")

            with mock.patch.object(create_base.machine, "append_joined", refuse):
                with self.assertRaises(RuntimeError):
                    make(parent)

            root = os.path.join(os.path.realpath(parent), "gtm-base")
            self.assertTrue(os.path.isdir(root))
            self.assertTrue(paths.is_base_shaped(root))
            found = paths.resolve_base(parent, machine.load_machine_state())
            self.assertIn(found.code, (paths.CODE_UNJOINED, paths.CODE_BASE_SHAPED))
            self.assertEqual(root, found.root)

    def test_stopping_before_the_safeguard_is_put_in_place_is_repaired(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            parent = content_folder()

            def refuse(*arguments, **options):
                raise RuntimeError("stopped")

            with mock.patch.object(create_base.install_git_hook, "install", refuse):
                with self.assertRaises(RuntimeError):
                    make(parent)

            root = os.path.join(os.path.realpath(parent), "gtm-base")
            hook = os.path.join(root, ".git", "hooks", install_git_hook.HOOK_NAME)
            self.assertFalse(os.path.isfile(hook))

            codes = create_base.repair(root, PLUGIN_ROOT, runner())

            self.assertIn(create_base.CODE_HOOK_INSTALLED, codes)
            self.assertTrue(os.path.isfile(hook))

    def test_repairing_a_folder_nobody_joined_does_nothing(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(os.environ["HOME"], "lonely")
            support.make_base(folder, base_id=ids.base_id_random())

            self.assertEqual(
                [create_base.CODE_NOTHING_TO_REPAIR],
                create_base.repair(folder, PLUGIN_ROOT, runner()),
            )


class TestSeatFoldersLeftBehind(unittest.TestCase):
    """What this seat remembers about a base that never got built is cleared."""

    def test_a_seat_folder_for_a_base_with_nothing_saved_is_removed(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            stale_root = os.path.join(os.environ["HOME"], "half-made")
            os.makedirs(stale_root)
            support.git(["init", "-b", "main", "-q"], cwd=stale_root)
            support.write(os.path.join(stale_root, "context", "map.md"), support.MAP_TEXT)
            stale_id = ids.base_id_random()
            support.git(["config", "--local", "gtmbase.id", stale_id], cwd=stale_root)
            machine.append_joined(root=stale_root, base_id=stale_id, remote=None)
            state.update_seat(stale_id, first_push_reviewed=False)
            seat_folder = os.path.join(paths.bases_dir(), stale_id)
            self.assertTrue(os.path.isdir(seat_folder))

            make(content_folder())

            self.assertFalse(os.path.isdir(seat_folder))

    def test_a_seat_folder_for_a_finished_base_is_left_alone(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            first = make(content_folder("one"))
            seat_folder = os.path.join(paths.bases_dir(), first.base_id)

            make(content_folder("two"))

            self.assertTrue(os.path.isdir(seat_folder))


class TestNothingOutsideTheBaseIsTouched(unittest.TestCase):
    """The one thing a person is promised: nothing of theirs changes."""

    def test_every_file_that_was_already_there_is_byte_for_byte_the_same(self):
        with support.Sandbox() as sandbox:
            config = write_gitconfig("[user]\n\temail = dana@acme.test\n")
            claude_settings = support.write(
                os.path.join(os.environ["HOME"], ".claude", "settings.json"),
                '{"permissions": {"allow": []}}\n',
            )
            parent = content_folder()
            support.write(os.path.join(parent, "notes", "icp.md"), "# Our customers\n")
            support.write(os.path.join(parent, "CLAUDE.md"), "read me\n")
            before = listing_of(os.environ["HOME"])

            result = make(parent)

            after = listing_of(os.environ["HOME"], skip=(result.root,))
            self.assertEqual(before, after)
            self.assertEqual(before[".gitconfig"], digest_of(config))
            self.assertEqual(
                before[os.path.join(".claude", "settings.json")],
                digest_of(claude_settings),
            )
            self.assertEqual([], create_base.find_partial_folders(parent))


class TestTheBaseTheStaleLibraryReads(unittest.TestCase):
    """A base built this way answers the stale rules the way it should."""

    def test_the_first_file_counts_as_confirmed_against_its_own_decision(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            run = ids.run_id(TODAY)
            result = make(content_folder(), run=run)
            entry_id = "stg-" + "d" * 16
            support.write(
                os.path.join(
                    result.root, constants.DECISIONS_DIR, entry_id + ".md"
                ),
                builders.entry_text(
                    entry_id=entry_id,
                    affects=(ICP,),
                    decided_on=TODAY.isoformat(),
                    written_on=TODAY.isoformat(),
                    origin="join",
                    run_id=run,
                ),
            )
            support.git(["add", "-A"], cwd=result.root)
            support.git(["commit", "-q", "-m", "a decision"], cwd=result.root)

            inputs = base_reader.read_base(result.root, result.base_id, today=TODAY)
            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
                owner_email=result.email,
            )

            named = [
                flag
                for flag in report.file_flags
                if flag.path == ICP and entry_id in flag.entry_ids
            ]
            self.assertEqual([], named)


class TestThePlaceIsCheckedAgainAtTheMomentTheBaseIsBuilt(unittest.TestCase):
    """join-05: creation used to take whatever folder it was handed.

    The place is proposed at one moment and approved at another. Between the
    two, the folder can become somewhere a base may never go, and creation was
    the one step that never looked again.
    """

    def test_the_home_folder_is_refused_without_a_second_yes(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            with self.assertRaises(LocationError) as caught:
                make(os.environ["HOME"])

            self.assertEqual(location.CODE_HOME_DIRECTORY, caught.exception.code)
            self.assertFalse(
                os.path.isdir(os.path.join(os.environ["HOME"], "gtm-base"))
            )

    def test_the_home_folder_is_built_in_after_the_second_yes(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            result = make(os.environ["HOME"], confirmed_home=True)

            self.assertTrue(os.path.isdir(os.path.join(result.root, ".git")))

    def test_a_folder_inside_the_seat_folder_is_refused(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            inside = os.path.join(paths.seat_home(), "somewhere")

            with self.assertRaises(LocationError) as caught:
                make(inside)

            self.assertEqual(location.CODE_INSIDE_SEAT_HOME, caught.exception.code)
            self.assertFalse(os.path.isdir(os.path.join(inside, "gtm-base")))

    def test_a_folder_that_grew_a_base_since_the_proposal_is_refused(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            parent = content_folder()
            # Something named like a base turns up between the proposal and the
            # yes, which is exactly what the stray-base rule is there for.
            support.write(os.path.join(parent, "GTM-Base", "README.md"), "hello\n")

            with self.assertRaises(LocationError) as caught:
                make(parent)

            # Which of the two refusals it is depends on whether this computer
            # tells one letter case from another in a folder name. Either way
            # the base is not built on top of what is already there.
            self.assertIn(
                caught.exception.code,
                (location.CODE_STRAY_BASE, location.CODE_TARGET_EXISTS),
            )
            self.assertTrue(
                os.path.isfile(
                    os.path.join(parent, "GTM-Base", "README.md")
                )
            )

    def test_nothing_is_left_behind_when_the_place_is_refused(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            self.assertRaises(LocationError, make, os.environ["HOME"])

            left = [
                name
                for name in os.listdir(os.environ["HOME"])
                if name.startswith(constants.PARTIAL_FOLDER_PREFIX)
            ]
            self.assertEqual([], left)


class TestTheOfferAnswerIsRecordedWhenTheBaseExists(unittest.TestCase):
    """C5: the answer used to be recorded only at the closing."""

    def test_one_approved_file_is_enough_to_record_that_they_set_one_up(self):
        with support.Sandbox():
            write_gitconfig("[user]\n\temail = dana@acme.test\n")
            self.assertEqual("unset", machine.load_machine_state().answer)

            make(content_folder())

            self.assertEqual("set-up", machine.load_machine_state().answer)


class TestTwoBasesOnOneMachine(unittest.TestCase):
    """Two companies, two folders, and neither one knows about the other."""

    def test_each_folder_resolves_to_its_own_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig("[user]\n\temail = dana@acme.test\n")

            first = make(content_folder("acme"))
            second = make(content_folder("beta"))

            self.assertNotEqual(first.base_id, second.base_id)
            state_now = machine.load_machine_state(runner=runner())
            for result in (first, second):
                found = paths.resolve_base(result.root, state_now)
                self.assertEqual(paths.CODE_JOINED, found.code)
                self.assertEqual(result.base_id, found.base_id)
                parent_found = paths.resolve_base(
                    os.path.dirname(result.root), state_now
                )
                self.assertEqual(result.base_id, parent_found.base_id)


class TestTheTemplateTheBaseIsBuiltFrom(unittest.TestCase):
    """The plugin carries its own copy, and it is the one a real run uses."""

    def test_the_plugins_copy_and_the_repositorys_copy_are_the_same(self):
        plugin_copy = os.path.join(support.PLUGIN_DIR, "templates", "company-base")
        repository_copy = os.path.join(support.REPO_ROOT, "templates", "company-base")
        self.assertTrue(os.path.isdir(plugin_copy))
        self.assertTrue(os.path.isdir(repository_copy))
        self.assertEqual(
            listing_of(plugin_copy), listing_of(repository_copy)
        )
        comparison = filecmp.dircmp(plugin_copy, repository_copy)
        self.assertEqual([], comparison.left_only + comparison.right_only)

    def test_the_copy_inside_the_plugin_is_the_one_a_run_uses(self):
        self.assertEqual(
            os.path.join(support.PLUGIN_DIR, "templates", "company-base"),
            create_base.template_root(support.PLUGIN_DIR),
        )


class TestTheSentencesThisModuleProduces(unittest.TestCase):
    """Anything a person could be shown reads as plain language."""

    def test_every_code_and_message_is_plain(self):
        sentences = [
            create_base.CODE_NO_TEMPLATE,
            create_base.CODE_BAD_EMAIL,
            create_base.CODE_NO_OWNER_FIELD,
            create_base.CODE_GIT_FAILED,
            create_base.CODE_RENAME_FAILED,
            create_base.CODE_HOOK_INSTALLED,
            create_base.CODE_NOTHING_TO_REPAIR,
        ]
        with support.Sandbox() as sandbox:
            write_gitconfig("")
            try:
                make(content_folder())
            except IdentityNeeded as failure:
                sentences.append(str(failure))
        for sentence in sentences:
            self.assertEqual([], plain_language.find_banned(sentence), sentence)
            self.assertEqual([], plain_language.find_dashes(sentence), sentence)


if __name__ == "__main__":
    unittest.main()
