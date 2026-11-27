"""Joining a base from a link (P2), end to end against a local repository.

GitHub is stood in for the way tests/test_backup.py stands it in: git's own
address rewriting in the sandbox's git settings reads `https://github.com/` as
a folder of bare repositories, so the plugin copies from the address a person
would paste and nothing reaches the network.
"""

import os
import subprocess
import sys
import unittest
from unittest import mock

import support
from support import Sandbox, git, head_of, trust_checkout, write

from gtmbase import (
    approval,
    backup,
    constants,
    gate,
    ids,
    install_git_hook,
    join_link,
    machine,
    push_conditions,
    state,
)

ADDRESS = "https://github.com/acme-co/acme-base"
SHIM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins",
    "gtm-base",
    "skills",
    "join",
    "scripts",
    "join.py",
)


def _bare(path):
    os.makedirs(path, exist_ok=True)
    git(["init", "--bare", "-q", "-b", "main", path], cwd=os.path.dirname(path))
    return path


class JoinCase(unittest.TestCase):
    """A teammate's computer, and a base the owner already backed up."""

    flaw = None

    def setUp(self):
        self.box = Sandbox().__enter__()
        self.addCleanup(self.box.__exit__, None, None, None)
        self.remotes = os.path.join(self.box.path, "remotes")
        self.bare = _bare(os.path.join(self.remotes, "acme-co", "acme-base.git"))
        subprocess.run(
            ["git", "config", "--global", "url.%s/.insteadOf" % self.remotes, "https://github.com/"],
            check=True,
        )
        subprocess.run(["git", "config", "--global", "user.email", "mate@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Mate"], check=True)
        # The owner's base, on the owner's computer, sent to the shared copy.
        owner = trust_checkout(os.path.join(self.box.path, "owner"), flaw=self.flaw, name="acme")
        write(os.path.join(owner, constants.ALLOWLIST_PATH), "owner@example.com\n")
        write(os.path.join(owner, constants.CODEOWNERS_PATH), "/context/ @owner\n")
        git(["add", "-A"], cwd=owner)
        git(["commit", "-q", "-m", "the rest of the base"], cwd=owner)
        git(["push", "-q", self.bare, "main"], cwd=owner)
        self.owner = owner
        # A private repository needs a sign-in; a local one never does, so the
        # public-repository check has a scenario of its own below.
        private = mock.patch.object(backup, "readable_without_sign_in", lambda *a, **k: False)
        private.start()
        self.addCleanup(private.stop)
        self.bases = os.path.join(os.environ["HOME"], constants.BASES_FOLDER_NAME)

    def target(self, name="acme-base"):
        return os.path.realpath(os.path.join(self.bases, name, constants.BASE_FOLDER_NAME))

    def refused(self, code, call):
        with self.assertRaises(join_link.GtmBaseError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def plugin_root(self):
        return os.path.dirname(os.path.dirname(os.path.dirname(SHIM)))


class TestTheReview(JoinCase):
    def test_the_review_names_the_usual_place_and_writes_nothing(self):
        found = join_link.review(ADDRESS)
        self.assertEqual(found.address, ADDRESS + ".git")
        self.assertEqual(
            found.target,
            os.path.join(os.environ["HOME"], constants.BASES_FOLDER_NAME, "acme-base", "gtm-base"),
        )
        self.assertEqual(found.base_id, ids.base_id_for_remote(ADDRESS))
        self.assertFalse(os.path.exists(self.bases))
        self.assertEqual([], machine.load_machine_state_raw().joined)
        said = join_link.describe(found)
        # The address and the folder go on lines of their own, never inside a sentence.
        self.assertFalse(any("acme" in sentence for sentence in said))

    def test_only_a_plain_github_address_is_taken(self):
        for bad in (
            "https://someone:ghp_secret@github.com/acme-co/acme-base",
            "https://gitlab.com/acme-co/acme-base",
            "git@github.com:acme-co/acme-base.git",
            "file:///tmp/acme-base",
            "",
        ):
            self.refused(join_link.CODE_BAD_ADDRESS, lambda: join_link.review(bad))

    def test_a_repository_this_computer_cannot_read_is_refused(self):
        self.refused(
            join_link.CODE_CANNOT_REACH,
            lambda: join_link.review("https://github.com/acme-co/no-such-base"),
        )

    def test_an_empty_repository_is_refused(self):
        _bare(os.path.join(self.remotes, "acme-co", "empty-base.git"))
        self.refused(join_link.CODE_EMPTY, lambda: join_link.review("https://github.com/acme-co/empty-base"))

    def test_a_repository_anybody_can_read_is_refused(self):
        with mock.patch.object(backup, "readable_without_sign_in", lambda *a, **k: True):
            self.refused(join_link.CODE_PUBLIC, lambda: join_link.review(ADDRESS))

    def test_a_folder_already_standing_in_the_usual_place_is_refused(self):
        os.makedirs(os.path.join(self.bases, "acme-base"))
        self.refused(join_link.CODE_FOLDER_TAKEN, lambda: join_link.review(ADDRESS))


class TestJoining(JoinCase):
    def test_the_base_is_copied_and_this_computer_becomes_a_seat(self):
        joined = join_link.join(ADDRESS, self.plugin_root())
        root = self.target()
        self.assertEqual(os.path.realpath(joined.root), root)
        self.assertEqual(head_of(root), head_of(self.owner))
        self.assertEqual(joined.branch, "main")
        self.assertTrue(os.path.isfile(os.path.join(root, constants.MAP_PATH)))
        # Known by the identifier every seat works out from the address.
        base_id = ids.base_id_for_remote(ADDRESS)
        self.assertEqual(joined.base_id, base_id)
        self.assertEqual(git(["config", "--local", "--get", "gtmbase.id"], cwd=root).stdout.decode().strip(), base_id)
        self.assertEqual(
            git(["config", "--local", "--get", "remote.origin.url"], cwd=root).stdout.decode().strip(),
            ADDRESS + ".git",
        )
        self.assertEqual(git(["config", "--local", "--get", "core.symlinks"], cwd=root).stdout.decode().strip(), "false")
        # Work saved here says who saved it, from the person's own git settings.
        self.assertEqual(
            git(["config", "--local", "--get", "user.email"], cwd=root).stdout.decode().strip(),
            "mate@example.com",
        )
        entry = machine.find_joined_by_id(machine.load_machine_state(), base_id)
        self.assertEqual(os.path.realpath(entry["root"]), root)
        seat, problems = state.load_seat(base_id)
        self.assertEqual([], problems)
        self.assertEqual(seat["joined_from"]["address"], ADDRESS + ".git")
        self.assertEqual(seat["client"], "claude")
        self.assertIn(joined.hook_code, (install_git_hook.CODE_OK, install_git_hook.CODE_CHAINED))
        self.assertTrue(os.path.isfile(os.path.join(root, ".git", "hooks", "pre-push")))
        self.assertEqual("join", machine.load_machine_state_raw().offer["answer"])
        # Nothing half built is left beside it.
        self.assertEqual(["gtm-base"], os.listdir(os.path.dirname(root)))

    def test_a_seat_sends_only_to_the_repository_it_was_copied_from(self):
        joined = join_link.join(ADDRESS, self.plugin_root())
        self.assertFalse(push_conditions.first_push_unreviewed(joined.base_id, joined.root))
        self.assertTrue(backup.destination_allowed(joined.base_id, joined.root, ADDRESS))
        self.assertTrue(backup.destination_allowed(joined.base_id, joined.root, "git@github.com:acme-co/acme-base.git"))
        for elsewhere in ("https://github.com/acme-co/other-base", "https://attacker.example/x.git", None):
            self.assertFalse(backup.destination_allowed(joined.base_id, joined.root, elsewhere), elsewhere)
        # Pointed somewhere else afterwards, it is held back altogether.
        git(["remote", "set-url", "origin", "https://github.com/attacker/stolen"], cwd=joined.root)
        self.assertTrue(push_conditions.first_push_unreviewed(joined.base_id, joined.root))

    def test_a_seat_never_sends_its_whole_history_as_a_backup(self):
        joined = join_link.join(ADDRESS, self.plugin_root())
        self.refused(backup.CODE_ALREADY, lambda: backup.review(joined.root, joined.base_id, ADDRESS))

    def test_joining_the_same_base_twice_is_refused(self):
        join_link.join(ADDRESS, self.plugin_root())
        self.refused(join_link.CODE_ALREADY_HERE, lambda: join_link.join(ADDRESS, self.plugin_root()))
        self.assertEqual(os.path.realpath(join_link.already_here(ADDRESS + ".git")), self.target())

    def test_a_base_this_computer_backed_up_itself_is_already_here(self):
        machine.append_joined(root=self.owner, base_id=ids.base_id_random(), remote=ADDRESS + ".git")
        self.refused(join_link.CODE_ALREADY_HERE, lambda: join_link.review(ADDRESS))

    def test_a_record_written_by_hand_cannot_point_a_seat_anywhere_but_github(self):
        joined = join_link.join(ADDRESS, self.plugin_root())
        state.update_seat(
            joined.base_id,
            joined_from={"address": "https://attacker.example/x.git", "joined_at": "2026-11-27T00:00:00Z"},
        )
        self.assertIsNone(join_link.joined_address(joined.base_id))
        self.assertFalse(backup.destination_allowed(joined.base_id, joined.root, "https://attacker.example/x.git"))
        state.update_seat(joined.base_id, joined_from={"address": ADDRESS + ".git", "extra": "x"})
        seat, problems = state.load_seat(joined.base_id)
        self.assertIsNone(seat["joined_from"])
        self.assertIn("bad-value", problems)


class TestARepositoryThatIsNotABase(JoinCase):
    def test_a_repository_without_a_base_in_it_is_removed_whole(self):
        _bare(os.path.join(self.remotes, "acme-co", "notes.git"))
        other = os.path.join(self.box.path, "notes")
        os.makedirs(other)
        git(["init", "-q", "-b", "main"], cwd=other)
        write(os.path.join(other, "README.md"), "# Notes\n")
        git(["add", "-A"], cwd=other)
        git(["-c", "user.email=a@example.com", "-c", "user.name=A", "commit", "-q", "-m", "x"], cwd=other)
        git(["push", "-q", os.path.join(self.remotes, "acme-co", "notes.git"), "main"], cwd=other)
        self.refused(join_link.CODE_NOT_A_BASE, lambda: join_link.join("https://github.com/acme-co/notes", self.plugin_root()))
        self.assertFalse(os.path.exists(os.path.join(self.bases, "notes")))
        self.assertEqual([], machine.load_machine_state_raw().joined)


class TestABaseHoldingALink(JoinCase):
    flaw = "symlink"

    def test_a_link_is_refused_before_a_single_file_is_written(self):
        self.refused(join_link.CODE_NOT_A_BASE, lambda: join_link.join(ADDRESS, self.plugin_root()))
        self.assertFalse(os.path.exists(os.path.join(self.bases, "acme-base")))


class TestABaseHoldingInstructions(JoinCase):
    flaw = "claude-md"

    def test_a_file_an_assistant_would_follow_stops_the_join(self):
        self.refused(join_link.CODE_NOT_TRUSTED, lambda: join_link.join(ADDRESS, self.plugin_root()))
        self.assertFalse(os.path.exists(os.path.join(self.bases, "acme-base")))
        self.assertEqual([], machine.load_machine_state_raw().joined)


class TestTheSharedLine(JoinCase):
    """A seat's changes go as proposals; only confirmation lines go straight to main."""

    def setUp(self):
        super(TestTheSharedLine, self).setUp()
        self.joined = join_link.join(ADDRESS, self.plugin_root())
        self.root = self.joined.root
        git(["config", "--local", "user.email", "mate@example.com"], cwd=self.root)
        git(["config", "--local", "user.name", "Mate"], cwd=self.root)
        # The check on commands resolves where a send goes the way git does,
        # which here is the folder the sandbox's address rewriting points at.
        # On a real computer it is the GitHub address, so it is answered so.
        where = mock.patch.object(gate, "push_destinations", lambda *a, **k: [ADDRESS + ".git"])
        where.start()
        self.addCleanup(where.stop)

    def hook_line(self, ref="refs/heads/main"):
        return "refs/heads/main %s %s %s\n" % (head_of(self.root), ref, head_of(self.owner))

    def test_a_change_to_a_document_never_goes_straight_to_main(self):
        support.commit(self.root, "context/strategy/icp.md", ["# Who we sell to", "", "Somebody new."])
        refused = gate.sentence_for(gate.REASON_SHARED_LINE)
        self.assertEqual(refused, gate.check_git_hook(self.hook_line(), self.root, None, "origin", ADDRESS + ".git"))
        self.assertEqual(refused, gate.check_command("git push origin main", self.root, "s1"))
        self.assertEqual(refused, gate.check_command("git push", self.root, "s1"))
        self.assertEqual(refused, gate.check_command("git push origin HEAD:refs/heads/main", self.root, "s1"))
        self.assertEqual(refused, gate.check_command("git push --all origin", self.root, "s1"))

    def test_the_same_change_on_a_proposal_line_is_allowed(self):
        git(["checkout", "-q", "-b", "gtm-base/proposal-x"], cwd=self.root)
        support.commit(self.root, "context/strategy/icp.md", ["# Who we sell to", "", "Somebody new."])
        line = "refs/heads/gtm-base/proposal-x %s refs/heads/gtm-base/proposal-x %s\n" % (
            head_of(self.root),
            "0" * 40,
        )
        self.assertIsNone(gate.check_git_hook(line, self.root, None, "origin", ADDRESS + ".git"))
        self.assertIsNone(gate.check_command("git push origin gtm-base/proposal-x", self.root, "s1"))

    def test_a_confirmation_line_alone_may_go_straight_to_main(self):
        support.commit(self.root, "work/confirmations/2026-11.md", ["- context/strategy/icp.md confirmed"])
        self.assertIsNone(gate.check_git_hook(self.hook_line(), self.root, None, "origin", ADDRESS + ".git"))
        self.assertIsNone(gate.check_command("git push origin main", self.root, "s1"))

    def test_a_document_change_hidden_behind_a_confirmation_is_still_seen(self):
        support.commit(self.root, "context/strategy/icp.md", ["# Who we sell to", "", "Somebody new."])
        support.commit(self.root, "work/confirmations/2026-11.md", ["- confirmed"])
        self.assertEqual(
            gate.sentence_for(gate.REASON_SHARED_LINE),
            gate.check_git_hook(self.hook_line(), self.root, None, "origin", ADDRESS + ".git"),
        )

    def test_taking_the_shared_line_away_is_refused(self):
        line = "(delete) %s refs/heads/main %s\n" % ("0" * 40, head_of(self.owner))
        self.assertEqual(
            gate.sentence_for(gate.REASON_SHARED_LINE),
            gate.check_git_hook(line, self.root, None, "origin", ADDRESS + ".git"),
        )

    def test_git_itself_refuses_the_send_from_a_plain_terminal(self):
        support.commit(self.root, "context/strategy/icp.md", ["# Who we sell to", "", "Somebody new."])
        before = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"], cwd=self.bare, stdout=subprocess.PIPE
        ).stdout
        pushed = subprocess.run(
            ["git", "push", "-q", "origin", "main"],
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(0, pushed.returncode)
        after = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"], cwd=self.bare, stdout=subprocess.PIPE
        ).stdout
        self.assertEqual(before, after)


class TestTheScript(JoinCase):
    def run_join(self, *arguments):
        # The script runs in its own process, which does not inherit the
        # test's stand-in for a private repository, so tests/held tells it.
        environment = dict(os.environ)
        environment["GTM_BASE_TESTS_PRIVATE_STAND_IN"] = "1"
        return subprocess.run(
            [sys.executable, SHIM] + list(arguments),
            env=environment,
            cwd=os.environ["HOME"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_the_review_then_the_join(self):
        reviewed = self.run_join("join-review", "--address", ADDRESS)
        said = reviewed.stdout.decode()
        self.assertEqual(0, reviewed.returncode, said)
        self.assertIn("status=reviewed", said)
        self.assertIn("folder=", said)
        self.assertFalse(os.path.exists(self.bases))
        joined = self.run_join("join-link", "--address", ADDRESS)
        said = joined.stdout.decode()
        self.assertEqual(0, joined.returncode, said)
        self.assertIn("status=joined", said)
        self.assertTrue(os.path.isdir(self.target()))

    def test_a_refusal_says_one_sentence_and_names_no_secret(self):
        finished = self.run_join("join-review", "--address", "https://me:ghp_abc@github.com/acme-co/acme-base")
        said = finished.stdout.decode()
        self.assertEqual(1, finished.returncode)
        self.assertIn("codes=%s" % join_link.CODE_BAD_ADDRESS, said)
        self.assertNotIn("ghp_abc", said + finished.stderr.decode())


class TestTheApproval(unittest.TestCase):
    def test_only_the_join_is_an_approval(self):
        self.assertEqual(
            approval._what("join.py", approval._read_settings("join.py", ["join-link", "--address", ADDRESS])),
            (approval.SAYS_JOIN, ("join_link.join",)),
        )
        self.assertIsNone(
            approval._what("join.py", approval._read_settings("join.py", ["join-review", "--address", ADDRESS]))
        )

    def test_the_join_refuses_without_the_persons_yes(self):
        held = approval._held
        approval._held = frozenset()
        try:
            with Sandbox():
                with self.assertRaises(approval.ApprovalRefused):
                    join_link.join(ADDRESS, "/nowhere")
        finally:
            approval._held = held


if __name__ == "__main__":
    unittest.main()
