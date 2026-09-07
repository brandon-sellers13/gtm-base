"""Unit 2: the seat folder, the base identifier, and where a path may point."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

import support
from support import TempHome, git, make_base, write

from gtmbase import constants, folder_identity, ids, paths
from gtmbase.errors import PathError, StateError
from gtmbase.machine import MachineState

REMOTE = "https://github.com/acme/base.git"


class TempDir(object):
    def __enter__(self):
        self.path = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-test-"))
        return self.path

    def __exit__(self, kind, value, trace):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


class TestContextPaths(unittest.TestCase):
    def test_a_path_inside_context_passes(self):
        with TempDir() as folder:
            make_base(os.path.join(folder, "base"))
            root = os.path.join(folder, "base")
            self.assertEqual(
                "context/strategy/icp.md",
                paths.canonical_context_path(root, "context/strategy/icp.md"),
            )

    def test_climbing_out_of_the_base_is_refused(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            for candidate in ("../.env", "context/../../.env", "context/../.git/config"):
                with self.assertRaises(PathError, msg=candidate):
                    paths.canonical_context_path(root, candidate)

    def test_an_absolute_path_outside_the_base_is_refused(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            with self.assertRaises(PathError) as caught:
                paths.canonical_context_path(root, "/etc/passwd")
            self.assertEqual("absolute-path", caught.exception.code)
            with self.assertRaises(PathError):
                paths.canonical_context_path(root, os.path.join(folder, "elsewhere.md"))

    def test_a_link_that_leaves_the_context_folder_is_refused(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            outside = write(os.path.join(folder, "secret.md"), "a secret\n")
            link = os.path.join(root, "context", "strategy", "escape.md")
            os.symlink(outside, link)
            with self.assertRaises(PathError) as caught:
                paths.canonical_context_path(root, "context/strategy/escape.md")
            self.assertEqual("outside-context", caught.exception.code)

    def test_a_link_that_stays_inside_the_context_folder_is_allowed(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            link = os.path.join(root, "context", "strategy", "same.md")
            os.symlink(os.path.join(root, "context", "strategy", "icp.md"), link)
            self.assertEqual(
                "context/strategy/same.md",
                paths.canonical_context_path(root, "context/strategy/same.md"),
            )

    def test_a_name_with_a_line_break_or_link_punctuation_is_refused(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            for candidate in (
                "context/strategy/icp\n.md",
                "context/strategy/[icp](http://x).md",
                "context/strategy/icp\t.md",
                "context/strategy/icp\\x.md",
            ):
                with self.assertRaises(PathError, msg=repr(candidate)):
                    paths.canonical_context_path(root, candidate)

    def test_the_context_folder_itself_is_not_a_context_path(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "base"))
            with self.assertRaises(PathError):
                paths.canonical_context_path(root, "context")
            with self.assertRaises(PathError):
                paths.canonical_context_path(root, "work/decisions/a.md")

    def test_a_proposal_may_also_name_the_ledger_and_the_corrections_folders(self):
        paths.check_repo_path_syntax(
            "work/decisions/stg-0000000000000000.md", paths.PROPOSAL_PATH_PREFIXES
        )
        paths.check_repo_path_syntax(
            "corrections/2026-01-13-note.md", paths.PROPOSAL_PATH_PREFIXES
        )
        with self.assertRaises(PathError):
            paths.check_repo_path_syntax("CODEOWNERS", paths.PROPOSAL_PATH_PREFIXES)


class TestSeatFolder(unittest.TestCase):
    def test_the_seat_folder_ignores_the_plugin_data_variable(self):
        with TempHome():
            previous = os.environ.get("CLAUDE_PLUGIN_DATA")
            first = paths.seat_home()
            os.environ["CLAUDE_PLUGIN_DATA"] = "/somewhere/else"
            try:
                self.assertEqual(first, paths.seat_home())
            finally:
                if previous is None:
                    os.environ.pop("CLAUDE_PLUGIN_DATA", None)
                else:
                    os.environ["CLAUDE_PLUGIN_DATA"] = previous

    def test_the_seat_folder_and_its_children_are_owner_only(self):
        with TempHome():
            home = paths.seat_home()
            base_id = ids.base_id_random()
            seat = paths.seat_dir(base_id)
            worktrees = paths.worktrees_dir(base_id)
            for folder in (home, seat, worktrees):
                self.assertEqual(0o700, os.stat(folder).st_mode & 0o777, folder)
            self.assertTrue(seat.endswith(os.path.join("bases", base_id)))
            self.assertTrue(worktrees.startswith(seat))

    def test_a_base_id_we_do_not_recognise_never_becomes_a_folder(self):
        with TempHome():
            for value in ("../escape", "not-an-id", ""):
                with self.assertRaises(ValueError):
                    paths.seat_dir(value)


class TestBaseId(unittest.TestCase):
    def test_two_clones_of_one_remote_agree_without_any_id_written_down(self):
        with TempDir() as folder:
            first = make_base(os.path.join(folder, "one"), remote=REMOTE)
            second = make_base(os.path.join(folder, "two"), remote="git@github.com:Acme/base.git")
            self.assertEqual(paths.read_base_id(first), paths.read_base_id(second))
            self.assertEqual(ids.base_id_for_remote(REMOTE), paths.read_base_id(first))

    def test_an_id_written_into_the_clone_wins_in_either_folder(self):
        with TempDir() as folder:
            written = ids.base_id_random()
            first = make_base(os.path.join(folder, "one"), base_id=written, remote=REMOTE)
            second = make_base(os.path.join(folder, "two"), base_id=written)
            self.assertEqual(written, paths.read_base_id(first))
            self.assertEqual(written, paths.read_base_id(second))

    def test_a_base_with_no_remote_and_no_id_has_none(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            self.assertIsNone(paths.read_base_id(root))

    def test_an_id_that_is_not_ours_is_ignored(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            git(["config", "--local", "gtmbase.id", "not-an-id"], cwd=root)
            self.assertIsNone(paths.read_base_id(root))

    def test_writing_the_id_puts_it_where_the_next_read_finds_it(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            value = ids.base_id_random()
            paths.write_base_id(root, value)
            self.assertEqual(value, paths.read_base_id(root))
            with self.assertRaises(ValueError):
                paths.write_base_id(root, "nope")

    def test_the_remote_address_comes_back_without_a_sign_in(self):
        with TempDir() as folder:
            root = make_base(
                os.path.join(folder, "one"),
                remote="https://someone:token@github.com/acme/base.git",
            )
            self.assertEqual("https://github.com/acme/base.git", paths.remote_url(root))
            self.assertEqual("github.com/acme/base", paths.canonical_remote(root))
            self.assertNotIn("token", paths.remote_url(root))

    def test_a_folder_with_no_remote_reports_none(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            self.assertIsNone(paths.remote_url(root))
            self.assertIsNone(paths.canonical_remote(root))


class TestDefaultBranch(unittest.TestCase):
    def test_a_fresh_base_on_main_is_on_the_default_branch(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            self.assertEqual((True, "default-branch"), paths.head_is_default_branch(root))

    def test_another_branch_is_not_the_default_branch(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            git(["checkout", "-q", "-b", "proposal"], cwd=root)
            self.assertEqual(
                (False, "not-default-branch"), paths.head_is_default_branch(root)
            )

    def test_a_detached_head_is_reported_as_detached(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            head = git(["rev-parse", "HEAD"], cwd=root).stdout.decode().strip()
            git(["checkout", "-q", head], cwd=root)
            self.assertEqual((False, "detached"), paths.head_is_default_branch(root))

    def test_a_folder_that_is_not_a_repository_is_reported_and_never_raises(self):
        with TempDir() as folder:
            answer, code = paths.head_is_default_branch(folder)
            self.assertFalse(answer)
            self.assertEqual("git-failed", code)


class TestGitRoot(unittest.TestCase):
    def test_inside_a_base_the_root_is_found_and_outside_it_is_not(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "one"))
            inside = os.path.join(root, "context", "strategy")
            self.assertEqual(os.path.realpath(root), paths.git_root(inside))
            self.assertIsNone(paths.git_root(folder))


def joined_state(*entries):
    return MachineState(joined=[dict(entry) for entry in entries])


class TestResolveBase(unittest.TestCase):
    def test_a_joined_folder_resolves_as_joined(self):
        with TempDir() as folder:
            base_id = ids.base_id_random()
            root = make_base(os.path.join(folder, "gtm-base"), base_id=base_id)
            state = joined_state({"root": root, "base_id": base_id, "remote": None})
            answer = paths.resolve_base(root, state)
            self.assertEqual("joined", answer.code)
            self.assertEqual(os.path.realpath(root), answer.root)
            self.assertEqual(base_id, answer.base_id)
            self.assertTrue(answer.joined)

    def test_a_joined_child_of_the_current_folder_resolves_as_joined(self):
        with TempDir() as folder:
            base_id = ids.base_id_random()
            parent = os.path.join(folder, "Acme")
            os.makedirs(parent)
            root = make_base(os.path.join(parent, "gtm-base"), base_id=base_id)
            state = joined_state({"root": root, "base_id": base_id, "remote": None})
            answer = paths.resolve_base(parent, state)
            self.assertEqual("joined", answer.code)
            self.assertEqual(os.path.realpath(root), answer.root)

    def test_the_current_folder_wins_when_both_it_and_its_child_are_joined(self):
        with TempDir() as folder:
            outer_id = ids.base_id_random()
            inner_id = ids.base_id_random()
            outer = make_base(os.path.join(folder, "outer"), base_id=outer_id)
            inner = make_base(os.path.join(outer, "gtm-base"), base_id=inner_id)
            state = joined_state(
                {"root": outer, "base_id": outer_id, "remote": None},
                {"root": inner, "base_id": inner_id, "remote": None},
            )
            answer = paths.resolve_base(outer, state)
            self.assertEqual("joined", answer.code)
            self.assertEqual(os.path.realpath(outer), answer.root)

    def test_two_children_with_the_same_name_stop_everything(self):
        # A folder holding both `gtm-base` and `GTM-Base` cannot be built on a
        # Mac, where the two names are the same folder, so the listing itself
        # is stood in for. The rule is what is under test.
        with TempDir() as folder:
            parent = os.path.join(folder, "Acme")
            os.makedirs(parent)
            make_base(os.path.join(parent, "gtm-base"))
            with mock.patch("os.listdir", return_value=["gtm-base", "GTM-Base"]):
                with mock.patch("os.path.isdir", return_value=True):
                    answer = paths.resolve_base(parent, joined_state())
            self.assertEqual("multiple-children", answer.code)
            self.assertIsNone(answer.root)
            self.assertIsNone(answer.base_id)

    def test_a_base_layout_that_was_never_joined_is_base_shaped(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "gtm-base"))
            answer = paths.resolve_base(root, joined_state())
            self.assertEqual("base-shaped", answer.code)
            self.assertEqual(os.path.realpath(root), answer.root)
            self.assertIsNone(answer.base_id)

    def test_a_base_that_carries_an_id_nobody_joined_is_unjoined(self):
        with TempDir() as folder:
            base_id = ids.base_id_random()
            root = make_base(os.path.join(folder, "gtm-base"), base_id=base_id)
            answer = paths.resolve_base(root, joined_state())
            self.assertEqual("unjoined", answer.code)
            self.assertEqual(base_id, answer.base_id)

    def test_an_entry_whose_id_does_not_match_the_folder_is_ignored(self):
        with TempDir() as folder:
            base_id = ids.base_id_random()
            root = make_base(os.path.join(folder, "gtm-base"), base_id=base_id)
            state = joined_state(
                {"root": root, "base_id": ids.base_id_random(), "remote": None}
            )
            answer = paths.resolve_base(root, state)
            self.assertEqual("unjoined", answer.code)
            self.assertIsNone(answer.entry)

    def test_an_unrelated_folder_resolves_to_nothing(self):
        with TempDir() as folder:
            os.makedirs(os.path.join(folder, "Pictures"))
            answer = paths.resolve_base(os.path.join(folder, "Pictures"), joined_state())
            self.assertEqual("none", answer.code)
            self.assertIsNone(answer.root)

    def test_a_repository_without_the_map_is_not_a_base(self):
        with TempDir() as folder:
            root = os.path.join(folder, "code")
            os.makedirs(root)
            git(["init", "-b", "main", "-q"], cwd=root)
            self.assertFalse(paths.is_base_shaped(root))
            self.assertEqual("none", paths.resolve_base(root, joined_state()).code)

    def test_a_map_that_is_a_link_is_not_a_base(self):
        with TempDir() as folder:
            root = make_base(os.path.join(folder, "gtm-base"))
            real = os.path.join(root, "context", "map.md")
            elsewhere = write(os.path.join(folder, "map.md"), support.MAP_TEXT)
            os.unlink(real)
            os.symlink(elsewhere, real)
            self.assertFalse(paths.is_base_shaped(root))


class TestResolvingThroughTheFolderABaseBelongsWith(unittest.TestCase):
    """Opening the folder your material lives in brings its base with it."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)

    def base(self, name="Acme"):
        from gtmbase import machine

        root = os.path.join(
            os.environ["HOME"], "GTM Bases", name, "gtm-base"
        )
        base_id = ids.base_id_random()
        make_base(root, base_id=base_id)
        machine.append_joined(root=root, base_id=base_id)
        return os.path.realpath(root), base_id

    def content(self, name="marketing"):
        folder = os.path.join(os.environ["HOME"], name)
        os.makedirs(folder)
        return os.path.realpath(folder)

    def state(self):
        from gtmbase import machine

        return machine.load_machine_state()

    def test_a_folder_a_base_belongs_with_opens_that_base(self):
        from gtmbase import machine

        root, base_id = self.base()
        folder = self.content()
        machine.link_content(base_id, folder)

        answer = paths.resolve_base(folder, self.state())

        self.assertEqual(paths.CODE_LINKED, answer.code)
        self.assertTrue(answer.active)
        self.assertFalse(answer.joined)
        self.assertEqual(root, answer.root)
        self.assertEqual(base_id, answer.base_id)
        self.assertEqual(folder, answer.content_root)
        self.assertIsNone(answer.repair_root)

    def test_a_base_in_the_folder_itself_beats_any_association(self):
        from gtmbase import machine

        root, base_id = self.base()
        other_root, other_id = self.base("Other")
        parent = os.path.dirname(other_root)
        # Registration refuses this, because the base sitting inside the folder
        # would always win. So it is written by hand, to show that the resolver
        # would refuse to be fooled by it too.
        state = machine.load_machine_state_raw()
        taken = folder_identity.capture(parent)
        entry = machine.find_joined_by_id(state, base_id)
        entry["content_root"] = taken.path
        entry["content_identity"] = taken.as_dict()
        machine.save_machine_state(state)

        answer = paths.resolve_base(parent, self.state())

        self.assertEqual(paths.CODE_JOINED, answer.code)
        self.assertEqual(other_root, answer.root)

    def test_two_base_folders_in_one_place_still_stop_everything_first(self):
        from gtmbase import machine

        root, base_id = self.base()
        parent = os.path.join(os.environ["HOME"], "Acme-work")
        os.makedirs(parent)
        machine.link_content(base_id, parent)
        make_base(os.path.join(parent, "gtm-base"))

        with mock.patch("os.listdir", return_value=["gtm-base", "GTM-Base"]):
            with mock.patch("os.path.isdir", return_value=True):
                answer = paths.resolve_base(parent, self.state())

        self.assertEqual(paths.CODE_MULTIPLE_CHILDREN, answer.code)

    def test_a_renamed_folder_opens_the_base_and_asks_for_the_record_to_follow(self):
        from gtmbase import machine

        root, base_id = self.base()
        folder = self.content()
        machine.link_content(base_id, folder)
        moved = os.path.join(os.environ["HOME"], "renamed")
        os.rename(folder, moved)

        answer = paths.resolve_base(moved, self.state())

        self.assertEqual(paths.CODE_LINKED, answer.code)
        self.assertEqual(root, answer.root)
        self.assertEqual(os.path.realpath(moved), answer.repair_root)

    def test_two_bases_claiming_one_folder_open_neither_and_name_both(self):
        from gtmbase import machine

        first, first_id = self.base("First")
        second, second_id = self.base("Second")
        folder = self.content()
        machine.link_content(first_id, folder)
        # The second claim is written straight into the file, because
        # registration is what refuses it and this is the case where a file
        # written by hand, or by an older release, holds two claims anyway.
        state = machine.load_machine_state_raw()
        taken = machine.find_joined_by_id(state, first_id)["content_identity"]
        machine.find_joined_by_id(state, second_id)["content_root"] = folder
        machine.find_joined_by_id(state, second_id)["content_identity"] = dict(taken)
        machine.save_machine_state(state)

        answer = paths.resolve_base(folder, self.state())

        self.assertEqual(paths.CODE_LINK_CONFLICT, answer.code)
        self.assertIsNone(answer.root)
        self.assertEqual(sorted([first, second]), answer.conflict_roots)

    def test_a_folder_built_again_at_the_same_path_opens_nothing(self):
        from gtmbase import machine

        root, base_id = self.base()
        folder = self.content()
        machine.link_content(base_id, folder)
        shutil.rmtree(folder)
        os.makedirs(folder)

        answer = paths.resolve_base(folder, self.state())

        self.assertEqual(paths.CODE_LINK_MISMATCH, answer.code)
        self.assertIsNone(answer.root)

    def test_a_folder_that_has_come_to_sit_inside_another_base_opens_nothing(self):
        from gtmbase import machine

        root, base_id = self.base()
        other_root, _other_id = self.base("Other")
        folder = os.path.join(os.environ["HOME"], "marketing")
        os.makedirs(folder)
        machine.link_content(base_id, folder)
        moved = os.path.join(other_root, "context", "marketing")
        os.rename(folder, moved)

        answer = paths.resolve_base(moved, self.state())

        self.assertEqual(paths.CODE_CONTENT_INSIDE_BASE, answer.code)
        self.assertIsNone(answer.root)

    def test_a_folder_nobody_claims_falls_through_to_the_offer_rules(self):
        from gtmbase import machine

        root, base_id = self.base()
        machine.link_content(base_id, self.content())
        elsewhere = self.content("Pictures")

        answer = paths.resolve_base(elsewhere, self.state())

        self.assertEqual(paths.CODE_NONE, answer.code)

    def test_a_copy_of_a_base_is_still_a_copy_and_never_adopted_by_a_link(self):
        from gtmbase import machine

        root, base_id = self.base()
        folder = self.content()
        machine.link_content(base_id, folder)
        copy = os.path.join(os.environ["HOME"], "copy-of-base")
        shutil.copytree(root, copy, symlinks=True)

        answer = paths.resolve_base(copy, self.state())

        self.assertEqual(paths.CODE_UNJOINED, answer.code)
        self.assertEqual(base_id, answer.base_id)

    def test_only_the_base_that_was_chosen_is_asked_about(self):
        """The hook has fifteen seconds, so it never checks every base it holds."""
        from gtmbase import machine

        root, base_id = self.base()
        for name in ("B", "C", "D"):
            self.base(name)
        folder = self.content()
        machine.link_content(base_id, folder)
        state = self.state()

        watched = support.CountingRunner()
        answer = paths.resolve_base(folder, state, runner=watched)

        self.assertEqual(paths.CODE_LINKED, answer.code)
        looked_at = set(
            call["cwd"] for call in watched.calls if call["cwd"] is not None
        )
        self.assertEqual({folder, root}, looked_at)


class TestMigration(unittest.TestCase):
    def test_moving_a_seat_folder_is_not_available_yet(self):
        with self.assertRaises(StateError) as caught:
            paths.migrate("0" * 32, "1" * 32)
        self.assertEqual("migration-not-available", caught.exception.code)


if __name__ == "__main__":
    unittest.main()


class TestAWriteStaysWhereItBelongs(unittest.TestCase):
    """`fsutil` refuses a write whose folder resolves outside the one named."""

    def test_a_link_out_of_the_folder_is_refused(self):
        from gtmbase import fsutil

        with TempDir() as folder:
            root = os.path.join(folder, "base")
            away = os.path.join(folder, "away")
            os.makedirs(root)
            os.makedirs(away)
            os.symlink(away, os.path.join(root, "context"))

            with self.assertRaises(PathError):
                fsutil.atomic_write_text(
                    os.path.join(root, "context", "icp.md"), "hello", inside=root
                )
            self.assertFalse(os.path.exists(os.path.join(away, "icp.md")))

            with self.assertRaises(PathError):
                fsutil.atomic_write_json(
                    os.path.join(root, "context", "icp.json"), {}, inside=root
                )
            self.assertFalse(os.path.exists(os.path.join(away, "icp.json")))

    def test_a_write_inside_the_folder_is_allowed(self):
        from gtmbase import fsutil

        with TempDir() as folder:
            root = os.path.join(folder, "base")
            os.makedirs(root)
            written = fsutil.atomic_write_text(
                os.path.join(root, "context", "icp.md"), "hello", inside=root
            )
            self.assertEqual("hello", support.read(written))
