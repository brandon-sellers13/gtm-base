"""The first backup review and send (P1), end to end against a local repository.

GitHub is stood in for by git's own address rewriting in the sandbox's git
settings: `https://github.com/` is read as a folder of bare repositories, so
the plugin sends to the address a person would use and nothing reaches the
network.
"""

import datetime
import os
import subprocess
import unittest

from support import Sandbox, git, head_of, make_base, write  # noqa: F401

from gtmbase import approval, backup, constants, ids, machine, push_conditions, state

ADDRESS = "https://github.com/acme-co/acme-base"


def _bare(path):
    os.makedirs(path, exist_ok=True)
    git(["init", "--bare", "-q", "-b", "main", path], cwd=os.path.dirname(path))
    return path


class BackupCase(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox().__enter__()
        self.addCleanup(self.box.__exit__, None, None, None)
        remotes = os.path.join(self.box.path, "remotes")
        self.bare = _bare(os.path.join(remotes, "acme-co", "acme-base.git"))
        # Everything addressed to GitHub goes to the folder of bare repositories.
        subprocess.run(
            ["git", "config", "--global", "url.%s/.insteadOf" % remotes, "https://github.com/"],
            check=True,
        )
        self.base_id = ids.base_id_random()
        self.root = make_base(os.path.join(self.box.path, "base"), base_id=self.base_id, commit=False)
        write(os.path.join(self.root, constants.ALLOWLIST_PATH), "owner@example.com\n")
        write(os.path.join(self.root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
        git(["add", "-A"], cwd=self.root)
        git(["commit", "-q", "-m", "first"], cwd=self.root)
        machine.append_joined(root=self.root, base_id=self.base_id, remote=None)
        # A local repository can always be read without signing in; the
        # private-repository check has scenarios of its own below.
        from unittest import mock

        private = mock.patch.object(backup, "readable_without_sign_in", lambda *a, **k: False)
        private.start()
        self.addCleanup(private.stop)

    def remote_head(self):
        found = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "refs/heads/main"], cwd=self.bare, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        return found.stdout.decode().strip() or None

    def record(self):
        return state.load_seat(self.base_id)[0]["first_backup"]


class AddressTests(unittest.TestCase):
    def test_only_a_plain_github_repository_address_is_taken(self):
        self.assertEqual(backup.parse_address(ADDRESS), ADDRESS + ".git")
        self.assertEqual(backup.parse_address(ADDRESS + ".git/"), ADDRESS + ".git")
        for bad in (
            "http://github.com/acme-co/acme-base",
            "https://gitlab.com/acme-co/acme-base",
            "https://someone:secret@github.com/acme-co/acme-base",
            "https://github.com/acme-co/acme-base/tree/main",
            "git@github.com:acme-co/acme-base.git",
            "https://github.com/-acme/acme-base",
            "",
        ):
            with self.assertRaises(backup.GtmBaseError) as caught:
                backup.parse_address(bad)
            self.assertEqual(caught.exception.code, backup.CODE_BAD_ADDRESS)


class ReviewTests(BackupCase):
    def test_a_clean_base_and_an_empty_repository_is_reviewed_and_recorded(self):
        found = backup.review(self.root, self.base_id, ADDRESS)
        self.assertIsNone(found.problem)
        self.assertEqual(found.head, head_of(self.root))
        self.assertEqual(found.documents_by_part.get("context"), 2)
        record = self.record()
        self.assertEqual(record["address"], ADDRESS + ".git")
        self.assertEqual(record["reviewed_head"], found.head)
        self.assertIsNone(record["sent_at"])
        # Reviewing sends nothing and points the base nowhere.
        self.assertIsNone(self.remote_head())
        self.assertNotIn("origin", git(["remote"], cwd=self.root).stdout.decode())
        said = backup.describe(found)
        self.assertIn("It holds 4 files.", said)
        self.assertIn("2 are context documents.", said)
        # The address is never put inside a sentence; join.py prints it on a line of its own.
        self.assertFalse(any("acme" in line for line in said))

    def test_a_repository_that_already_holds_something_is_refused(self):
        other = os.path.join(self.box.path, "other")
        make_base(other)
        git(["push", "-q", self.bare, "main"], cwd=other)
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.review(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_NOT_EMPTY)
        self.assertIsNone(self.record())

    def test_a_repository_that_cannot_be_reached_is_refused(self):
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.review(self.root, self.base_id, "https://github.com/acme-co/no-such-base")
        self.assertEqual(caught.exception.code, backup.CODE_CANNOT_REACH)

    def test_a_key_in_the_base_is_shown_and_nothing_is_recorded(self):
        write(
            os.path.join(self.root, "context", "notes.md"),
            "token: ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8\n",
        )
        git(["add", "-A"], cwd=self.root)
        git(["commit", "-q", "-m", "oops"], cwd=self.root)
        found = backup.review(self.root, self.base_id, ADDRESS)
        self.assertIsNotNone(found.problem)
        self.assertIsNone(self.record())

    def test_a_base_that_already_sends_somewhere_else_is_refused(self):
        git(["remote", "add", "origin", "https://github.com/acme-co/elsewhere"], cwd=self.root)
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.review(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_OTHER_REMOTE)


class SendTests(BackupCase):
    def test_the_reviewed_version_goes_to_the_reviewed_repository(self):
        found = backup.review(self.root, self.base_id, ADDRESS)
        self.assertTrue(push_conditions.first_push_unreviewed(self.base_id, self.root))
        address = backup.send(self.root, self.base_id, ADDRESS)
        self.assertIsNone(self.record()["approved_at"])
        self.assertEqual(address, ADDRESS + ".git")
        self.assertEqual(self.remote_head(), found.head)
        record = self.record()
        self.assertIsNotNone(record["sent_at"])
        entry = machine.find_joined_by_id(machine.load_machine_state(), self.base_id)
        self.assertIn("acme-co/acme-base", entry["remote"])
        # After the first backup, sends to that repository are no longer held back.
        self.assertFalse(push_conditions.first_push_unreviewed(self.base_id, self.root))

    def test_sending_with_no_review_is_refused(self):
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.send(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_REVIEW_AGAIN)
        self.assertIsNone(self.remote_head())

    def test_a_change_saved_after_the_review_is_not_sent_unseen(self):
        backup.review(self.root, self.base_id, ADDRESS)
        write(os.path.join(self.root, "context", "later.md"), "# Later\n")
        git(["add", "-A"], cwd=self.root)
        git(["commit", "-q", "-m", "after the review"], cwd=self.root)
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.send(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_REVIEW_AGAIN)
        self.assertIsNone(self.remote_head())

    def test_a_different_address_from_the_reviewed_one_is_refused(self):
        backup.review(self.root, self.base_id, ADDRESS)
        _bare(os.path.join(self.box.path, "remotes", "acme-co", "other-base.git"))
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.send(self.root, self.base_id, "https://github.com/acme-co/other-base")
        self.assertEqual(caught.exception.code, backup.CODE_REVIEW_AGAIN)

    def test_a_stale_review_is_refused(self):
        backup.review(self.root, self.base_id, ADDRESS)
        record = self.record()
        old = state.now_utc() - datetime.timedelta(hours=2)
        record["reviewed_at"] = state.iso_utc(old)
        state.update_seat(self.base_id, first_backup=record)
        with self.assertRaises(backup.GtmBaseError) as caught:
            backup.send(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_REVIEW_AGAIN)

    def test_a_failed_send_leaves_the_base_as_it_was(self):
        backup.review(self.root, self.base_id, ADDRESS)
        # The repository disappears between the review and the send.
        subprocess.run(["rm", "-rf", self.bare], check=True)
        with self.assertRaises(backup.GtmBaseError):
            backup.send(self.root, self.base_id, ADDRESS)
        self.assertNotIn("origin", git(["remote"], cwd=self.root).stdout.decode())
        self.assertIsNone(self.record()["sent_at"])
        self.assertTrue(push_conditions.first_push_unreviewed(self.base_id, self.root))


class RuleTests(BackupCase):
    def test_a_record_somebody_wrote_by_hand_does_not_unlock_another_address(self):
        state.update_seat(
            self.base_id,
            first_backup={
                "address": ADDRESS + ".git",
                "reviewed_head": head_of(self.root),
                "reviewed_at": None,
                "approved_at": None,
                "sent_at": "2026-01-01T00:00:00Z",
            },
        )
        git(["remote", "add", "origin", "https://github.com/acme-co/elsewhere"], cwd=self.root)
        self.assertTrue(push_conditions.first_push_unreviewed(self.base_id, self.root))

    def test_a_malformed_record_is_dropped(self):
        state.update_seat(self.base_id, first_backup={"address": 3, "extra": "x"})
        seat, problems = state.load_seat(self.base_id)
        self.assertIsNone(seat["first_backup"])
        self.assertIn("bad-value", problems)


class NetworkSettingsTests(unittest.TestCase):
    def test_network_commands_get_a_known_sign_in_helper_and_nothing_else(self):
        from unittest import mock

        from gtmbase import gitcmd

        seen = {}

        def fake_run(command, cwd=None, env=None, **kwargs):
            for name in ("ls-remote", "push", "log"):
                if name in command:
                    seen[name] = (list(command), env.get("GIT_CONFIG_NOSYSTEM"))

            class Done(object):
                returncode = 0
                stdout = b""
                stderr = b""

            return Done()

        with mock.patch.object(gitcmd, "_system_helpers", ("osxkeychain",)), mock.patch.object(
            gitcmd.subprocess, "run", fake_run
        ):
            runner = gitcmd.GitRunner()
            runner.run(["ls-remote", ADDRESS])
            runner.run(["push", "origin"])
            runner.run(["log", "-1"])
            runner.run(["-c", "credential.helper=", "ls-remote", ADDRESS])
        # System settings stay off for every command.
        for name in ("ls-remote", "push", "log"):
            self.assertEqual(seen[name][1], "1")
        self.assertIn("credential.helper=osxkeychain", seen["push"][0])
        self.assertNotIn("credential.helper=osxkeychain", seen["log"][0])
        # An explicit "no helper" is never overridden.
        self.assertNotIn("credential.helper=osxkeychain", seen["ls-remote"][0])

    def test_only_well_known_helpers_are_taken_from_the_system_settings(self):
        self.assertNotIn("!evil-program", __import__("gtmbase.gitcmd").gitcmd.KNOWN_SIGN_IN_HELPERS)


class PublicRepositoryTests(BackupCase):
    def test_a_repository_anybody_can_read_is_refused(self):
        from unittest import mock

        with mock.patch.object(backup, "readable_without_sign_in", lambda *a, **k: True):
            with self.assertRaises(backup.GtmBaseError) as caught:
                backup.review(self.root, self.base_id, ADDRESS)
        self.assertEqual(caught.exception.code, backup.CODE_PUBLIC)
        self.assertIsNone(self.record())


class DestinationTests(BackupCase):
    def sent(self):
        backup.review(self.root, self.base_id, ADDRESS)
        backup.send(self.root, self.base_id, ADDRESS)

    def test_after_the_backup_only_its_own_repository_is_allowed(self):
        self.sent()
        self.assertTrue(backup.destination_allowed(self.base_id, self.root, ADDRESS))
        self.assertTrue(backup.destination_allowed(self.base_id, self.root, "git@github.com:acme-co/acme-base.git"))
        for elsewhere in (
            "https://github.com/acme-co/other-base",
            "https://anon-git.attacker.example/x.git",
            "/tmp/somewhere.git",
            None,
        ):
            self.assertFalse(backup.destination_allowed(self.base_id, self.root, elsewhere), elsewhere)

    def test_the_hook_refuses_a_send_to_another_address_after_the_backup(self):
        from gtmbase import gate

        self.sent()
        head = head_of(self.root)
        line = "refs/heads/main %s refs/heads/main %s\n" % (head, "0" * 40)
        self.assertIsNone(gate.check_git_hook(line, self.root, None, "origin", ADDRESS + ".git"))
        refused = gate.check_git_hook(line, self.root, None, "x", "https://anon-git.attacker.example/x.git")
        self.assertEqual(refused, gate.sentence_for(gate.REASON_FIRST_PUSH))

    def test_a_push_address_setting_cannot_redirect_the_backup(self):
        from gtmbase import gate

        self.sent()
        git(["config", "remote.origin.pushurl", "https://github.com/attacker/stolen-base"], cwd=self.root)
        push = gate.PushSpec(remote="origin", refspecs=["main"])
        destinations = gate.push_destinations(gate.runner_or_default(None), self.root, push)
        self.assertTrue(destinations)
        self.assertFalse(
            all(gate.send_from_a_base_allowed(self.root, url, None) for url in destinations)
        )

    def test_before_the_backup_only_the_hook_lets_the_reviewed_version_through(self):
        found = backup.review(self.root, self.base_id, ADDRESS)
        record = self.record()
        record["approved_at"] = state.iso_utc(state.now_utc())
        state.update_seat(self.base_id, first_backup=record)
        right = [(found.head, "refs/heads/main")]
        self.assertFalse(backup.destination_allowed(self.base_id, self.root, ADDRESS))
        self.assertTrue(backup.destination_allowed(self.base_id, self.root, ADDRESS, right))
        self.assertFalse(
            backup.destination_allowed(self.base_id, self.root, ADDRESS, [(found.head, "refs/heads/other")])
        )
        self.assertFalse(
            backup.destination_allowed(self.base_id, self.root, ADDRESS, right + [("f" * 40, "refs/tags/x")])
        )

    def test_a_forged_record_can_only_ever_name_a_github_repository(self):
        state.update_seat(
            self.base_id,
            first_backup={"address": "https://anon-git.attacker.example/x.git", "sent_at": "2026-01-01T00:00:00Z"},
        )
        self.assertFalse(
            backup.destination_allowed(self.base_id, self.root, "https://anon-git.attacker.example/x.git")
        )

    def test_the_first_send_is_read_from_nothing_not_from_a_local_branch(self):
        from gtmbase import gate

        runner = gate.runner_or_default(None)
        self.assertIsNone(gate.shared_branch_ref(runner, self.root, "origin"))
        push = gate.PushSpec(remote="origin", refspecs=["main"])
        self.assertEqual(gate.ranges_for_push(runner, self.root, push), [(gate.EMPTY_TREE, "main")])


class ApprovalTests(unittest.TestCase):
    def test_only_the_send_is_an_approval(self):
        self.assertEqual(
            approval._what("join.py", approval._read_settings("join.py", ["backup", "--address", ADDRESS])),
            (approval.SAYS_BACKUP, ("backup.send",)),
        )
        self.assertIsNone(
            approval._what("join.py", approval._read_settings("join.py", ["backup-review", "--address", ADDRESS]))
        )


if __name__ == "__main__":
    unittest.main()
