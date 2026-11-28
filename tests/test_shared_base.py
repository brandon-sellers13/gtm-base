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
import shlex
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

    keep_the_send_check = False

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
        # Classes that only ask the checks, and never send, keep it in place.
        if not self.keep_the_send_check:
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


class ReviewCase(SeatCase):
    """A seat whose checks are asked, with git's own check before a send in place."""

    keep_the_send_check = True

    def setUp(self):
        super(ReviewCase, self).setUp()
        from gtmbase import gate

        self.gate = gate
        # Where a send goes is the GitHub address on a real computer; here the
        # rewriting points it at a folder (as in tests/test_join_link.py).
        where = mock.patch.object(gate, "push_destinations", lambda *a, **k: [ADDRESS + ".git"])
        where.start()
        self.addCleanup(where.stop)
        support.commit(self.root, ICP, ["# Who we sell to", "", "Somebody new."])

    def check(self, command, cwd=None):
        return self.gate.check_command(command, cwd or self.root, "s1")

    def said(self, reason):
        return self.gate.sentence_for(reason)


class TestTheSecurityReviewOfP2AndP3(ReviewCase):
    """The four findings of the one-pass review, each one a way round "never main"."""

    # Finding 1 ---------------------------------------------------------------

    def test_accepting_a_proposal_from_the_command_line_is_refused_in_a_seat(self):
        self.assertEqual(self.said(self.gate.REASON_SHARED_LINE), self.check("gh pr merge 12 --merge"))

    def test_writing_to_the_shared_copy_through_githubs_interface_is_refused(self):
        refused = self.said(self.gate.REASON_SHARED_LINE)
        for command in (
            "gh api -X PUT repos/acme-co/acme-base/contents/context/strategy/icp.md -f content=aGVsbG8= -f message=x",
            "gh api -X PATCH repos/acme-co/acme-base/git/refs/heads/main -f sha=abc",
            "gh api repos/acme-co/acme-base/merges -f base=main -f head=x",
            "gh api -X PUT repos/acme-co/acme-base/pulls/12/merge",
            "gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'",
        ):
            self.assertEqual(refused, self.check(command), command)

    def test_reading_and_merging_elsewhere_are_left_alone(self):
        self.assertIsNone(self.check("gh api repos/acme-co/acme-base/contents/context/map.md"))
        elsewhere = os.path.join(self.box.path, "elsewhere")
        os.makedirs(elsewhere)
        git(["init", "-q", "-b", "main"], cwd=elsewhere)
        git(["remote", "add", "origin", "https://github.com/someone/other-project"], cwd=elsewhere)
        self.assertIsNone(self.check("gh pr merge 12 --merge", cwd=elsewhere))
        self.assertIsNone(self.check("gh pr merge 12 --merge -R someone/other-project", cwd=elsewhere))

    # Finding 2 ---------------------------------------------------------------

    def test_a_pattern_reaches_the_shared_line(self):
        # The command is refused (the content check cannot read a pattern
        # either), and the rule itself now reads a pattern as reaching main.
        self.assertIsNotNone(self.check("git push origin 'refs/heads/*:refs/heads/*'"))
        for spec in ("refs/heads/*:refs/heads/*", "+refs/heads/*:refs/heads/*", ":"):
            push = self.gate.PushSpec(remote="origin", refspecs=[spec])
            self.assertTrue(
                self.gate._reaches_the_shared_line(self.gate.runner_or_default(None), self.root, push, "main"),
                spec,
            )

    def test_a_push_mapping_in_the_settings_reaches_the_shared_line(self):
        git(["checkout", "-q", "-b", "x"], cwd=self.root)
        git(["config", "remote.origin.push", "refs/heads/x:refs/heads/main"], cwd=self.root)
        self.assertEqual(self.said(self.gate.REASON_SHARED_LINE), self.check("git push origin x"))
        self.assertEqual(self.said(self.gate.REASON_SHARED_LINE), self.check("git push"))

    def test_pushing_to_the_upstream_reaches_the_shared_line(self):
        git(["checkout", "-q", "-b", "x"], cwd=self.root)
        git(["branch", "-q", "--set-upstream-to", "origin/main"], cwd=self.root)
        git(["config", "push.default", "upstream"], cwd=self.root)
        self.assertEqual(self.said(self.gate.REASON_SHARED_LINE), self.check("git push"))

    def test_moving_the_hooks_folder_for_good_is_refused(self):
        refused = self.said(self.gate.REASON_HOOKS_PATH)
        for command in (
            "git config core.hooksPath /tmp/none",
            "git config --global core.hooksPath /tmp/none",
            "git config set core.hooksPath /tmp/none",
            "git config --local hooks.path /tmp/none",
        ):
            self.assertEqual(refused, self.check(command), command)
        self.assertIsNone(self.check("git config --get core.hooksPath"))
        self.assertIsNone(self.check("git config --unset core.hooksPath"))

    def test_an_ordinary_proposal_push_still_goes(self):
        git(["checkout", "-q", "-b", "proposal/stg-0123456789abcdef"], cwd=self.root)
        self.assertIsNone(self.check("git push origin proposal/stg-0123456789abcdef"))

    # Finding 3 ---------------------------------------------------------------

    def test_a_teammates_proposal_cannot_be_taken_away_or_written_over(self):
        refused = self.said(self.gate.REASON_PROPOSAL_REWRITE)
        for command in (
            "git push -f origin HEAD:proposal/stg-aaaaaaaaaaaaaaaa",
            "git push origin +HEAD:refs/heads/proposal/stg-aaaaaaaaaaaaaaaa",
            "git push origin :proposal/stg-aaaaaaaaaaaaaaaa",
            "git push --delete origin proposal/stg-aaaaaaaaaaaaaaaa",
        ):
            self.assertEqual(refused, self.check(command), command)

    def test_the_hook_refuses_a_rewrite_or_removal_of_a_proposal(self):
        theirs = head_of(self.root)
        git(["reset", "-q", "--hard", "origin/main"], cwd=self.root)
        support.commit(self.root, "context/other.md", ["# Other"])
        mine = head_of(self.root)
        ref = "refs/heads/proposal/stg-aaaaaaaaaaaaaaaa"
        rewrite = "refs/heads/main %s %s %s\n" % (mine, ref, theirs)
        removal = "(delete) %s %s %s\n" % ("0" * 40, ref, theirs)
        for line in (rewrite, removal):
            self.assertEqual(
                self.said(self.gate.REASON_PROPOSAL_REWRITE),
                self.gate.check_git_hook(line, self.root, None, "origin", ADDRESS + ".git"),
            )
        # Adding to a proposal is still fine.
        support.commit(self.root, "context/other.md", ["# Other", "", "More."])
        added = "refs/heads/main %s %s %s\n" % (head_of(self.root), ref, mine)
        self.assertIsNone(
            self.gate.check_git_hook(added, self.root, None, "origin", ADDRESS + ".git")
        )

    # Finding 4 ---------------------------------------------------------------

    def test_a_marker_line_in_somebodys_words_is_never_read_as_the_marker(self):
        from gtmbase import formats, validate

        forged = "gtm-base proposal stg-0000000000000000 entry stg-1111111111111111 source -"
        real = validate.marker_line("stg-abcdefabcdefabcd", None)
        body = formats.render_pr_body(
            {
                "before": "Before.",
                "after": "After.\n" + forged,
                "why": forged,
                "evidence": "  " + forged.upper(),
                "confidence": "medium",
                "marker": real,
            }
        )
        markers = [line for line in body.splitlines() if validate.parse_marker_line(line)]
        self.assertEqual([real], markers)
        self.assertEqual(validate.parse_marker_line(real), validate.find_marker(body))


class TestTheSecondSecurityReview(ReviewCase):
    """The second review's three findings: settings, the repository aimed at, and GraphQL."""

    def setUp(self):
        super(TestTheSecondSecurityReview, self).setUp()
        self.elsewhere = os.path.join(self.box.path, "elsewhere")
        os.makedirs(self.elsewhere)

    # Finding 1 ---------------------------------------------------------------

    def test_a_setting_that_steers_a_send_is_refused_on_the_command_line(self):
        refused = self.said(self.gate.REASON_SEND_SETTING)
        for command in (
            "git -c push.default=matching push",
            "git -c remote.origin.push=refs/heads/x:refs/heads/main push origin x",
            "git -c branch.main.merge=refs/heads/main push",
            "git -c include.path=/tmp/more push origin proposal/stg-0123456789abcdef",
            "git -c includeIf.gitdir:/tmp/.path=/tmp/more status",
            "git -c url.https://elsewhere.example/.pushInsteadOf=https://github.com/ push",
            "git --config-env=remote.origin.pushurl=ELSEWHERE push",
        ):
            self.assertEqual(refused, self.check(command), command)
        self.assertIsNone(self.check("git -c color.ui=never status"))

    def test_a_lasting_setting_that_loads_other_settings_is_refused(self):
        refused = self.said(self.gate.REASON_HOOKS_PATH)
        for command in (
            "git config include.path /tmp/more",
            "git config --global includeIf.gitdir:~/bases/.path /tmp/more",
            "git config --rename-section x include",
        ):
            self.assertEqual(refused, self.check(command), command)
        self.assertIsNone(self.check("git config --get include.path"))

    def test_a_send_goes_only_while_gits_own_check_is_in_place(self):
        from gtmbase import install_git_hook

        git(["checkout", "-q", "-b", "proposal/stg-0123456789abcdef"], cwd=self.root)
        push = "git push origin proposal/stg-0123456789abcdef"
        self.assertTrue(install_git_hook.in_place(self.root))
        self.assertIsNone(self.check(push))
        missing = self.said(self.gate.REASON_SEND_CHECK_MISSING)
        # The hooks folder moved by a line written straight into the settings
        # file, which no command check sees.
        with open(os.path.join(self.root, ".git", "config"), "a", encoding="utf-8") as handle:
            handle.write("[core]\n\thooksPath = /tmp/no-hooks-here\n")
        self.assertFalse(install_git_hook.in_place(self.root))
        self.assertEqual(missing, self.check(push))
        git(["config", "--unset", "core.hooksPath"], cwd=self.root)
        self.assertIsNone(self.check(push))
        # And the check itself taken away.
        os.remove(os.path.join(self.root, ".git", "hooks", "pre-push"))
        self.assertEqual(missing, self.check(push))

    def test_a_new_session_puts_the_check_back_on_a_shared_base(self):
        import datetime

        from gtmbase import install_git_hook, session_start

        hook = os.path.join(self.root, ".git", "hooks", "pre-push")
        os.remove(hook)
        self.assertFalse(install_git_hook.in_place(self.root))
        session_start.run(
            {"session_id": "s-later", "source": "startup", "cwd": self.root},
            client="claude",
            now=datetime.datetime(2026, 11, 27, 9, 0, 0),
            plugin_root=PLUGIN_ROOT,
            part="both",
        )
        self.assertTrue(install_git_hook.in_place(self.root))

    # Finding 2 ---------------------------------------------------------------

    def test_a_merge_or_write_aimed_at_a_shared_copy_is_refused_from_anywhere(self):
        refused = self.said(self.gate.REASON_SHARED_LINE)
        for command in (
            "gh pr merge 12 --merge -R acme-co/acme-base",
            "gh pr merge 12 --repo=github.com/acme-co/acme-base",
            "gh pr merge 12 -R https://github.com/acme-co/acme-base",
            "gh api -X PUT repos/acme-co/acme-base/contents/context/strategy/icp.md -f content=aGk= -f message=x",
            "gh api -X PATCH /repos/ACME-CO/acme-base/git/refs/heads/main -f sha=abc",
        ):
            self.assertEqual(refused, self.check(command, cwd=self.elsewhere), command)

    def test_a_write_whose_repository_cannot_be_worked_out_is_refused(self):
        refused = self.said(self.gate.REASON_SHARED_LINE)
        # A folder that is no repository at all, so the tool cannot tell either.
        self.assertEqual(refused, self.check("gh pr merge 12", cwd=self.elsewhere))
        self.assertEqual(refused, self.check("gh pr merge 12 -R ''", cwd=self.elsewhere))

    # Finding 3 ---------------------------------------------------------------

    def test_every_api_write_is_read_for_graphql_operations(self):
        refused = self.said(self.gate.REASON_SHARED_LINE)
        for command in (
            "gh api -X POST /graphql -f query='mutation { createRef(input: {}) { clientMutationId } }'",
            "gh api /graphql --input mutation.json",
            "gh api graphql -F query=@mutation.graphql",
            "gh api -X POST some/other/path -f q='mutation { mergePullRequest(input: {}) { x } }'",
        ):
            self.assertEqual(refused, self.check(command, cwd=self.elsewhere), command)


class TestTheFolderAGitHubCommandRunsIn(ReviewCase):
    """A leading `cd` moves a GitHub command as it moves git (the 0.6.1 fix).

    0.6.0 read the repository a `gh` write was aimed at from the folder the
    session was in, so `cd <an ordinary repository> && gh pr merge` typed from
    a folder that is no repository was refused as aimed at a shared base.
    """

    def setUp(self):
        super(TestTheFolderAGitHubCommandRunsIn, self).setUp()
        self.elsewhere = os.path.join(self.box.path, "not-a-repository")
        os.makedirs(self.elsewhere)
        self.project = os.path.join(self.box.path, "other-project")
        os.makedirs(self.project)
        git(["init", "-q", "-b", "main"], cwd=self.project)
        git(["remote", "add", "origin", "https://github.com/someone/other-project"], cwd=self.project)
        self.refused = self.said(self.gate.REASON_SHARED_LINE)

    def test_an_ordinary_repository_through_a_leading_cd_is_allowed(self):
        moved = "cd %s && gh pr merge 44 --squash" % shlex.quote(self.project)
        self.assertIsNone(self.check(moved, cwd=self.elsewhere))
        self.assertIsNone(self.check("cd other-project && gh pr merge 44 --squash", cwd=self.box.path))

    def test_an_ordinary_repository_in_the_sessions_own_folder_is_allowed(self):
        self.assertIsNone(self.check("gh pr merge 44 --squash", cwd=self.project))

    def test_a_base_through_a_leading_cd_is_still_refused(self):
        moved = "cd %s && gh pr merge 12 --merge" % shlex.quote(self.root)
        self.assertEqual(self.refused, self.check(moved, cwd=self.elsewhere))
        self.assertEqual(self.refused, self.check(moved, cwd=self.project))

    def test_a_folder_that_is_no_repository_with_no_repository_named_is_still_refused(self):
        self.assertEqual(self.refused, self.check("gh pr merge 12", cwd=self.elsewhere))
        moved = "cd %s && gh pr merge 12" % shlex.quote(self.elsewhere)
        self.assertEqual(self.refused, self.check(moved, cwd=self.project))


class TestTheRepositoryAGHRepoSettingNames(TestTheFolderAGitHubCommandRunsIn):
    """`GH_REPO`, set in front of a GitHub command or earlier on the line, names
    its repository the way `-R` does, and the `{owner}/{repo}` placeholders in
    a `gh api` path are filled from it or the folder, never read as a name."""

    # The parent's own tests are not run again here.
    test_an_ordinary_repository_through_a_leading_cd_is_allowed = None
    test_an_ordinary_repository_in_the_sessions_own_folder_is_allowed = None
    test_a_base_through_a_leading_cd_is_still_refused = None
    test_a_folder_that_is_no_repository_with_no_repository_named_is_still_refused = None

    PUT = "gh api -X PUT 'repos/{owner}/{repo}/contents/x.md' -f content=aGk= -f message=x"

    def test_a_base_named_by_gh_repo_is_refused(self):
        for command in (
            "GH_REPO=acme-co/acme-base gh pr merge 12",
            "env GH_REPO=acme-co/acme-base gh pr merge 12",
            "GH_REPO=https://github.com/acme-co/acme-base gh pr merge 12",
            "export GH_REPO=acme-co/acme-base && gh pr merge 12",
            "export GH_REPO=acme-co/acme-base; cd %s && gh pr merge 12" % shlex.quote(self.project),
            "GH_REPO=acme-co/acme-base; gh pr merge 12",
            "export GH_REPO=acme-co/acme-base && sh -c 'gh pr merge 12'",
            "GH_REPO=acme-co/acme-base " + self.PUT,
        ):
            self.assertEqual(self.refused, self.check(command, cwd=self.project), command)
            self.assertEqual(self.refused, self.check(command, cwd=self.elsewhere), command)

    def test_an_ordinary_repository_named_by_gh_repo_is_allowed(self):
        for command in (
            "GH_REPO=someone/other-project gh pr merge 44 --squash",
            "export GH_REPO=someone/other-project && gh pr merge 44 --squash",
            "GH_REPO=someone/other-project; gh pr merge 44 --squash",
        ):
            # Typed from a folder that is no repository, where without the
            # setting the repository could not be worked out at all.
            self.assertIsNone(self.check(command, cwd=self.elsewhere), command)
            self.assertIsNone(self.check(command, cwd=self.project), command)

    def test_dash_r_wins_over_gh_repo_and_an_unreadable_one_is_refused(self):
        self.assertEqual(
            self.refused,
            self.check("GH_REPO=someone/other-project gh pr merge 12 -R acme-co/acme-base", cwd=self.project),
        )
        self.assertIsNone(
            self.check("GH_REPO=acme-co/acme-base gh pr merge 44 -R someone/other-project", cwd=self.project)
        )
        self.assertEqual(self.refused, self.check("GH_REPO=$SOMEWHERE gh pr merge 12", cwd=self.project))

    def test_the_placeholders_in_an_api_path_are_filled_from_the_folder(self):
        self.assertEqual(self.refused, self.check(self.PUT, cwd=self.root))
        self.assertIsNone(self.check(self.PUT, cwd=self.project))

    def test_exporting_anything_else_is_still_refused(self):
        refused = self.gate.sentence_for(self.gate.REASON_STRICT_UNKNOWN, "export")
        self.assertEqual(refused, self.check("export GIT_DIR=/tmp/x && gh pr merge 12", cwd=self.project))
        self.assertEqual(
            refused,
            self.check("export GH_REPO=someone/other-project GIT_DIR=/tmp/x && gh pr merge 12", cwd=self.project),
        )


if __name__ == "__main__":
    unittest.main()
