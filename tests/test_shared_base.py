"""Working on a shared base (P3): writes go to the owner as proposals.

Recording a context change, the setup closing's change, a document drafted
after setup and the closing's note each used to write a save onto the shared
line, which on a base with a shared copy would sit on this computer and never
reach anybody (or, since P2, be refused at the send). Each now goes as a
proposal, made in a working folder of this seat's own, and the person's own
folder is left exactly as it was.

GitHub is stood in for the way tests/test_backup.py stands it in: git's own
address rewriting reads `https://github.com/` as a folder of bare
repositories, and the stand-in GitHub tool in tests/fakes records every call.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest import mock

import support
from support import Sandbox, git, head_of, show, trust_checkout, write

from gtmbase import (
    backup,
    constants,
    join_link,
    marker,
    record_change,
    review,
    shared_send,
)

ADDRESS = "https://github.com/acme-co/acme-base"
PLUGIN_ROOT = support.PLUGIN_DIR
STALE_CHECK = os.path.join(PLUGIN_ROOT, "skills", "stale-check", "scripts", "stale_check.py")
ICP = "context/strategy/icp.md"

WHAT = "We now sell to clinics with more than twenty staff."
WHY = "The last two quarters of closed deals were all that size."
SOURCE = "The October pipeline review."


def _bare(path):
    os.makedirs(path, exist_ok=True)
    git(["init", "--bare", "-q", "-b", "main", path], cwd=os.path.dirname(path))
    return path


class SeatCase(unittest.TestCase):
    """A teammate's seat on a base the owner already backed up."""

    def setUp(self):
        self.box = Sandbox().__enter__()
        self.addCleanup(self.box.__exit__, None, None, None)
        remotes = os.path.join(self.box.path, "remotes")
        self.bare = _bare(os.path.join(remotes, "acme-co", "acme-base.git"))
        for setting in (
            ("url.%s/.insteadOf" % remotes, "https://github.com/"),
            ("user.email", "mate@example.com"),
            ("user.name", "Mate"),
        ):
            subprocess.run(["git", "config", "--global", setting[0], setting[1]], check=True)
        owner = trust_checkout(os.path.join(self.box.path, "owner"), name="acme")
        write(os.path.join(owner, constants.ALLOWLIST_PATH), "owner@example.com\nmate@example.com\n")
        write(os.path.join(owner, constants.CODEOWNERS_PATH), "/context/ @owner\n")
        write(os.path.join(owner, ".gitignore"), "work/inbox/\nwork/proposals/\n")
        git(["add", "-A"], cwd=owner)
        git(["commit", "-q", "-m", "the rest of the base"], cwd=owner)
        git(["push", "-q", self.bare, "main"], cwd=owner)
        private = mock.patch.object(backup, "readable_without_sign_in", lambda *a, **k: False)
        private.start()
        self.addCleanup(private.stop)
        self.seat = join_link.join(ADDRESS, PLUGIN_ROOT)
        self.root = self.seat.root
        # Git hands its own check before a send the address after rewriting,
        # which here is the folder of bare repositories rather than GitHub, so
        # that check would refuse every send. On a real computer it is handed
        # the GitHub address; tests/test_join_link.py proves what it allows.
        os.remove(os.path.join(self.root, ".git", "hooks", "pre-push"))
        self.gh_log = os.path.join(self.box.path, "gh-calls.jsonl")
        os.environ["GH_FAKE_LOG"] = self.gh_log
        self.addCleanup(os.environ.pop, "GH_FAKE_LOG", None)

    def gh_calls(self):
        if not os.path.isfile(self.gh_log):
            return []
        with open(self.gh_log, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def created(self):
        return [call for call in self.gh_calls() if call["argv"][:2] == ["pr", "create"]]

    def proposal_branches(self):
        listed = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/proposal/"],
            cwd=self.bare,
            stdout=subprocess.PIPE,
        ).stdout.decode()
        return [line for line in listed.splitlines() if line]

    def shared_main(self):
        return subprocess.run(
            ["git", "rev-parse", "refs/heads/main"], cwd=self.bare, stdout=subprocess.PIPE
        ).stdout.decode().strip()


class TestRecordingAContextChange(SeatCase):
    def test_the_yes_sends_a_proposal_and_writes_nothing_here(self):
        before_here, before_shared = head_of(self.root), self.shared_main()
        token, listed = record_change.show_list(self.root, self.seat.base_id)
        self.assertTrue(listed)
        shown = record_change.preview(
            self.root, self.seat.base_id, WHAT, WHY, SOURCE, ["1"], list_token=token
        )
        # A fresh random name, never the first free one, so two seats cannot collide.
        self.assertTrue(shown.entry.id.startswith("stg-"))
        done = record_change.record(self.root, self.seat.base_id, shown.shown)

        self.assertIsNotNone(done.proposal)
        self.assertEqual([], done.plan.ask_about)
        # Nothing in the person's own folder, and nothing on the shared line.
        self.assertEqual(before_here, head_of(self.root))
        self.assertEqual("", git(["status", "--porcelain"], cwd=self.root).stdout.decode())
        self.assertEqual(before_shared, self.shared_main())
        # One proposal line, holding exactly the change that was shown.
        branches = self.proposal_branches()
        self.assertEqual(["proposal/%s" % done.proposal.staging_id], branches)
        self.assertEqual(shown.text, show(self.bare, branches[0], done.relative))
        changed = git(
            ["diff", "--name-only", "main", branches[0]], cwd=self.bare
        ).stdout.decode().split()
        self.assertEqual([done.relative], changed)
        # The review carries the proposal line the app's inbox reads.
        created = self.created()
        self.assertEqual(1, len(created))
        argv = created[0]["argv"]
        self.assertEqual("main", argv[argv.index("--base") + 1])
        self.assertEqual(branches[0], argv[argv.index("--head") + 1])
        # The working folder is gone again.
        self.assertFalse(os.path.exists(os.path.join(
            os.environ["GTM_BASE_HOME"], "bases", self.seat.base_id, "worktrees", done.proposal.staging_id
        )))

    def test_a_session_that_read_the_persons_documents_sends_nothing(self):
        token, _listed = record_change.show_list(self.root, self.seat.base_id)
        shown = record_change.preview(
            self.root, self.seat.base_id, WHAT, WHY, SOURCE, ["1"], list_token=token
        )
        marker.write_sources_read_marker("this-session")
        with self.assertRaises(shared_send.Refused):
            record_change.record(
                self.root, self.seat.base_id, shown.shown, session_id="this-session"
            )
        self.assertEqual([], self.proposal_branches())
        self.assertEqual([], self.created())

    def test_through_the_script(self):
        def run(*argv):
            finished = subprocess.run(
                [sys.executable, STALE_CHECK] + list(argv),
                cwd=self.root,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return finished.returncode, finished.stdout.decode(), finished.stderr.decode()

        def words(kind, text):
            code, out, err = run("--new-words-file", kind)
            self.assertEqual(0, code, out + err)
            path = out.split("words=", 1)[1].split()[0]
            write(path, text)
            return path

        code, out, err = run("--record-change", "documents")
        self.assertEqual(0, code, out + err)
        token = out.split("list=", 1)[1].split()[0]
        code, out, err = run(
            "--record-change", "show", "--documents", "1", "--list", token,
            "--what-changed-file", words("what-changed", WHAT),
            "--reason-file", words("reason", WHY),
            "--source-file", words("source", SOURCE),
        )
        self.assertEqual(0, code, out + err)
        shown = out.split("shown=", 1)[1].split()[0]
        code, out, err = run("--record-change", "record", "--shown", shown)
        self.assertEqual(0, code, out + err)
        self.assertIn(record_change.PROPOSED, out)
        self.assertIn("status=proposed", out)
        self.assertEqual(1, len(self.proposal_branches()))
        self.assertEqual(1, len(self.created()))


class TestDraftsAfterSetup(SeatCase):
    def draft(self, step, name):
        from gtmbase import drafting

        with open(os.path.join(support.FIXTURES_DIR, "drafts", name), encoding="utf-8") as handle:
            return drafting.parse(step, handle.read())

    def test_the_closing_change_goes_as_a_proposal(self):
        from gtmbase import drafting

        before_here, before_shared = head_of(self.root), self.shared_main()
        result = review.approve(
            self.draft(drafting.STEP_CHANGE, "change-entry.md"),
            self.root,
            self.seat.base_id,
            "run-2026-11-27-0123abcd",
            PLUGIN_ROOT,
        )
        self.assertEqual([review.CODE_SENT_AS_PROPOSAL], result.codes)
        self.assertEqual(before_here, head_of(self.root))
        self.assertEqual(before_shared, self.shared_main())
        branches = self.proposal_branches()
        self.assertEqual(1, len(branches))
        self.assertTrue(os.path.basename(result.path).startswith("stg-"))
        self.assertIn("kind: change", show(self.bare, branches[0], result.path))
        self.assertEqual(1, len(self.created()))

    def test_a_document_goes_with_the_line_recording_the_yes(self):
        from gtmbase import drafting

        # The base holds a customer profile and no positioning yet.
        before_here = head_of(self.root)
        result = review.approve(
            self.draft(drafting.STEP_POSITIONING, "positioning.md"),
            self.root,
            self.seat.base_id,
            "run-2026-11-27-0123abcd",
            PLUGIN_ROOT,
        )
        self.assertEqual([review.CODE_SENT_AS_PROPOSAL], result.codes)
        self.assertEqual(before_here, head_of(self.root))
        self.assertFalse(os.path.exists(os.path.join(self.root, result.path)))
        branch = self.proposal_branches()[0]
        changed = sorted(git(["diff", "--name-only", "main", branch], cwd=self.bare).stdout.decode().split())
        self.assertIn(result.path, changed)
        self.assertTrue(any(name.startswith(constants.CONFIRMATIONS_DIR + "/") for name in changed), changed)


if __name__ == "__main__":
    unittest.main()
