"""Unit 4: the check that reads what a command would send before it runs."""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import support
from support import FakeGitRunner, Sandbox, commit, git, head_of, write

from gtmbase import constants, gate, marker, push_conditions, state

PLUGIN_DIR = support.PLUGIN_DIR
WRAPPER = os.path.join(PLUGIN_DIR, "hooks", "pre-push-gate.sh")

CLEAN_LINE = "[prospect, mid-market fintech] said pricing was the blocker."


@contextlib.contextmanager
def once_the_first_backup_review_ships():
    """Stand where the first backup review will stand once it is built.

    This release answers "never reviewed" to every base on purpose, and reads
    no record at all to decide it. Findings A1 and H1 of the 2026-09-20 review
    both turned on the same thing: nothing shipped sets that record honestly,
    so every value of it saying the review happened was put there by something
    that is not this plugin, and a plain write over one small file turned a
    refused send into an allowed one.

    Everything below this line is about what the check reads once a send gets
    past that rule, so each of those scenarios is run with the answer the
    review will give when it ships. The rule itself is not stood in for
    anywhere: it has its own scenarios, which call the check directly.
    """
    with mock.patch.object(
        push_conditions, "first_push_unreviewed", lambda base_id: False
    ):
        yield


def check(command, cwd, session_id="session-1", git_runner=None):
    with once_the_first_backup_review_ships():
        return gate.check_command(command, cwd, session_id, git=git_runner)


def check_now(command, cwd, session_id="session-1", git_runner=None):
    """The check exactly as this release runs it, with nothing stood in for."""
    return gate.check_command(command, cwd, session_id, git=git_runner)


def plain_repository(
    box,
    name="plain-repo",
    line="mail jane@acme.com",
    message="ask jane@acme.com about it",
):
    """A repository of the person's own: not a base, and never joined.

    It has a shared copy of its own and one saved change that has not reached
    it yet, and that change carries the two things the gate refuses inside a
    base: an address in a line being added, and an address in the note saved
    with the work. So a send from here is allowed only because it was never
    read, not because there was nothing in it to find.
    """
    root = os.path.join(box.path, name)
    remote = os.path.join(box.path, name + "-origin.git")
    git(["init", "--bare", "-q", "-b", "main", remote], cwd=box.path)
    os.makedirs(root)
    git(["init", "-b", "main", "-q"], cwd=root)
    git(["config", "--local", "user.email", "owner@example.com"], cwd=root)
    git(["config", "--local", "user.name", "Test Owner"], cwd=root)
    git(["remote", "add", "origin", remote], cwd=root)
    write(os.path.join(root, "readme.md"), "a repository of my own\n")
    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", "first"], cwd=root)
    git(["push", "-q", "-u", "origin", "main"], cwd=root)
    write(os.path.join(root, "notes.md"), line + "\n")
    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", message], cwd=root)
    return root


def a_working_folder():
    """A folder shaped like the ones this seat makes to prepare a change in.

    The gate reads a send from one of these, so a test that needs the reading
    to happen without a real base runs from here.
    """
    from gtmbase import ids, paths

    folder = os.path.join(paths.worktrees_dir(ids.base_id_random()), "w")
    os.makedirs(folder)
    return folder


# --- What a command is -------------------------------------------------------


class TestClassifyingACommand(unittest.TestCase):
    def test_a_plain_send_is_a_send(self):
        self.assertEqual(1, len(gate.classify("git push").pushes))

    def test_a_send_reached_through_a_folder_change_is_still_a_send(self):
        self.assertEqual(
            1, len(gate.classify("cd base && git push origin HEAD").pushes)
        )

    def test_a_send_with_settings_in_front_is_still_a_send(self):
        classified = gate.classify("env GIT_TERMINAL_PROMPT=0 git push")
        self.assertEqual(1, len(classified.pushes))
        self.assertIsNone(classified.deny_reason)

    def test_a_send_inside_another_shell_is_still_a_send(self):
        self.assertEqual(1, len(gate.classify("sh -c 'git push'").pushes))
        self.assertEqual(1, len(gate.classify('bash -c "git push origin main"').pushes))

    def test_a_word_that_merely_holds_the_letters_is_not_a_command(self):
        self.assertFalse(gate.mentions_git_or_gh("echo digit and ghost"))
        self.assertTrue(gate.mentions_git_or_gh("gh pr list"))
        self.assertTrue(gate.mentions_git_or_gh("/usr/bin/git push"))

    def test_a_subcommand_that_only_starts_with_push_is_not_a_send(self):
        classified = gate.classify("git pushover")
        self.assertEqual([], classified.pushes)
        self.assertIsNone(classified.deny_reason)

    def test_pointing_git_at_other_safeguards_is_refused(self):
        self.assertEqual(
            gate.REASON_HOOKS_PATH,
            gate.classify("git -c core.hooksPath=/tmp push").deny_reason,
        )
        self.assertEqual(
            gate.REASON_HOOKS_PATH,
            gate.classify("git -c hooks.path=/tmp push").deny_reason,
        )

    def test_skipping_the_safeguard_is_refused(self):
        self.assertEqual(
            gate.REASON_NO_VERIFY, gate.classify("git push --no-verify").deny_reason
        )

    def test_sending_every_part_at_once_is_refused(self):
        self.assertEqual(
            gate.REASON_MIRROR, gate.classify("git push --mirror origin").deny_reason
        )

    def test_a_command_that_cannot_be_read_is_refused(self):
        classified = gate.classify("git push 'unclosed")
        self.assertEqual(gate.REASON_UNTOKENIZABLE, classified.deny_reason)

    def test_a_name_broken_up_by_quotes_or_backslashes_is_still_git(self):
        for command in ('g""it push origin main', "gi\\t push", '"git" push'):
            self.assertTrue(gate.mentions_git_or_gh(command), command)
            self.assertEqual(1, len(gate.classify(command).pushes), command)

    def test_a_send_written_inside_another_command_is_still_a_send(self):
        for command in (
            "echo $(git push origin main)",
            "echo `git push origin main`",
            "echo main | xargs git push origin",
            "echo main | xargs -n 1 git push origin",
        ):
            classified = gate.classify(command)
            self.assertEqual(1, len(classified.pushes), command)
            self.assertIsNone(classified.deny_reason, command)

    def test_a_part_of_the_command_we_cannot_account_for_is_refused(self):
        for command in (
            'python3 -c "import subprocess; subprocess.run([\'git\',\'push\'])"',
            "python3 -c 'import os' && git push",
            "perl -e 'x' ; git push",
        ):
            self.assertEqual(
                gate.REASON_UNTOKENIZABLE, gate.classify(command).deny_reason, command
            )

    def test_a_harmless_word_beside_a_send_is_left_alone(self):
        for command in (
            "cd base && git push origin HEAD",
            "git push origin main 2>&1",
            "python3 tools/report.py && git push origin main",
        ):
            classified = gate.classify(command)
            self.assertIsNone(classified.deny_reason, command)
            self.assertEqual(1, len(classified.pushes), command)

    def test_a_line_carried_on_to_the_next_one_is_still_a_send(self):
        classified = gate.classify("git \\\npush origin main")
        self.assertIsNone(classified.deny_reason)
        self.assertEqual(1, len(classified.pushes))
        self.assertEqual("origin", classified.pushes[0].remote)
        self.assertEqual(["main"], classified.pushes[0].refspecs)

    def test_handing_git_another_program_to_run_is_refused(self):
        for command in (
            "git --exec-path=/tmp/x push origin main",
            "git push --receive-pack=/tmp/x origin main",
            "git push --exec=/tmp/x origin main",
            "git push --upload-pack /tmp/x origin main",
            "GIT_SSH_COMMAND=/tmp/x git push",
            "GIT_SSH=/tmp/x git push",
            "GIT_EXEC_PATH=/tmp/x git push",
            "GIT_ASKPASS=/tmp/x git push",
            "SSH_ASKPASS=/tmp/x git push",
            "LD_PRELOAD=/tmp/x.so git push",
            "DYLD_INSERT_LIBRARIES=/tmp/x.dylib git push",
            "env GIT_CONFIG=/tmp/x git push",
        ):
            self.assertEqual(
                gate.REASON_DENIED_COMMAND, gate.classify(command).deny_reason, command
            )


class TestGitHubCommands(unittest.TestCase):
    def test_the_commands_no_skill_uses_are_refused_outright(self):
        for command in (
            "gh repo edit --visibility public",
            "gh repo delete acme/base",
            "gh auth token",
            "gh auth setup-git",
            "gh secret set NAME",
            "gh workflow run build.yml",
            "gh codespace create",
        ):
            self.assertEqual(
                gate.REASON_DENIED_COMMAND,
                gate.classify(command).deny_reason,
                command,
            )

    def test_making_a_repository_and_sending_it_is_a_send(self):
        classified = gate.classify("gh repo create --private --source . --push")
        self.assertIsNone(classified.deny_reason)
        self.assertEqual(1, len(classified.pushes))
        self.assertEqual(1, len(classified.gh_writes))

    def test_a_github_call_that_writes_is_read_before_it_runs(self):
        for command in (
            "gh pr create --title x",
            "gh pr edit 4 --body hello",
            "gh issue comment 4 --body hello",
            "gh api -X PUT repos/x/y/collaborators/z",
            "gh api -f body=hello repos/x/y/issues",
        ):
            self.assertEqual(1, len(gate.classify(command).gh_writes), command)

    def test_a_github_call_that_only_reads_is_left_alone(self):
        for command in ("gh pr list", "gh api repos/x/y", "gh auth login"):
            classified = gate.classify(command)
            self.assertEqual([], classified.gh_writes, command)
            self.assertIsNone(classified.deny_reason, command)
            self.assertTrue(classified.has_gh)


# --- What a send would carry -------------------------------------------------


class TestReadingASend(unittest.TestCase):
    def test_a_redacted_excerpt_with_roles_only_is_allowed(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/strategy/icp.md", ["---", "kind: icp", "---", CLEAN_LINE])
            self.assertIsNone(check("git push", root))

    def test_a_file_from_a_folder_that_is_yours_alone_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            os.makedirs(os.path.join(root, "work", "inbox"), exist_ok=True)
            commit(root, "work/inbox/call.md", ["nothing unusual here"])
            reason = check("git push", root)
            self.assertIn("work/inbox/call.md", reason)
            self.assertIn("yours alone", reason)

    def test_a_file_from_the_proposals_folder_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "work/proposals/pending/stg-1.json", ["{}"])
            reason = check("git push", root)
            self.assertIn("work/proposals/pending/stg-1.json", reason)

    def test_an_address_in_a_saved_note_on_the_work_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            git(
                ["commit", "-q", "--allow-empty", "-m", "ask jane@acme.com about it"],
                cwd=root,
            )
            reason = check("git push", root)
            self.assertIn("an email address", reason)
            self.assertNotIn("jane@acme.com", reason)

    def test_a_share_link_and_a_home_folder_path_are_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(
                root,
                "context/strategy/icp.md",
                ["the plan is at https://docs.google.com/document/d/abc/edit"],
            )
            self.assertIn("shared document", check("git push", root))

            commit(root, "context/metrics/notes.md", ["copy at /Users/jane/plan.md"])
            self.assertIn("home folder", check("git push", root))

    def test_an_allowed_address_is_let_through_and_a_key_is_not(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            write(
                os.path.join(root, constants.ALLOWLIST_PATH),
                "# ours\njane@acme.com\n",
            )
            commit(root, "context/strategy/icp.md", ["Ask jane@acme.com about it."])
            self.assertIsNone(check("git push", root))

            commit(root, "context/metrics/notes.md", ["AKIAIOSFODNN7EXAMPLE"])
            self.assertIn("key or a token", check("git push", root))

    def test_a_send_to_a_branch_nobody_shares_yet_is_read_from_the_shared_branch(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            git(["checkout", "-q", "-b", "feature"], cwd=root)
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            self.assertIn("an email address", check("git push origin feature", root))

    def test_a_forced_send_to_the_shared_branch_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            self.assertIn(
                "overwrite the shared history",
                check("git push --force origin main", root),
            )

    def test_a_forced_send_to_another_branch_is_read_the_usual_way(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            git(["checkout", "-q", "-b", "feature"], cwd=root)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            self.assertIsNone(check("git push --force origin feature", root))
            commit(root, "context/metrics/more.md", ["mail jane@acme.com"])
            self.assertIn(
                "an email address", check("git push --force origin feature", root)
            )

    def test_a_command_that_cannot_be_read_but_names_git_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIn(
                "could not tell what this command does",
                check("git push 'unclosed", root),
            )

    def test_a_folder_name_in_the_command_itself_is_not_content(self):
        """Where a send is run from is not something that is being sent.

        Ordinary work runs a send from a folder inside the person's home
        folder, and a proposal is prepared in a working folder under the seat
        folder, which is inside the home folder too. Reading those as a leak
        would refuse every ordinary send, so the home folder class is the one
        class the command line itself is not read for.
        """
        with Sandbox() as box:
            root, _base_id = box.base(name="Users/me/base")
            self.assertIn("/Users/me/base", root)
            git(["checkout", "-q", "-b", "feature"], cwd=root)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            self.assertIsNone(
                check("cd %s && git push origin feature" % root, box.path)
            )

    def test_a_send_after_a_folder_change_is_read_in_that_folder(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            reason = check("cd %s && git push origin main" % root, box.path)
            self.assertIn("an email address", reason or "")
            self.assertNotIn("jane@acme.com", reason)

    def test_a_folder_change_written_the_short_way_is_followed_too(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            self.assertEqual(os.path.join(box.path, "base"), root)
            reason = check("cd base && git push origin main", box.path)
            self.assertIn("an email address", reason or "")

    def test_a_folder_change_holds_for_every_part_after_it(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            command = "cd %s && git status && git push origin main" % root
            self.assertIn("an email address", check(command, box.path) or "")

    def test_a_send_from_a_folder_that_is_not_a_base_at_all_is_left_alone(self):
        """A folder that is no repository cannot be a base, so it is not read."""
        with Sandbox() as box:
            plain = os.path.join(box.path, "plain")
            os.makedirs(plain)
            self.assertIsNone(check("git push origin main", plain))

    def test_a_send_from_a_working_folder_with_no_repository_is_refused(self):
        """Inside the seat's own folder the send is read, so it must be readable."""
        with Sandbox() as box:
            empty = a_working_folder()
            self.assertEqual(
                gate.sentence_for(gate.REASON_UNREADABLE),
                check("git push origin main", empty),
            )

    def test_a_folder_change_the_check_cannot_follow_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            for command in (
                "cd - && git push origin main",
                "cd $HOME/base && git push origin main",
                "cd one two && git push origin main",
            ):
                self.assertIn(
                    "could not tell what this command does",
                    check(command, root) or "",
                    command,
                )

    def test_a_clean_send_after_a_folder_change_is_allowed(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            git(["checkout", "-q", "-b", "feature"], cwd=root)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            self.assertIsNone(
                check("cd %s && git push origin feature" % root, box.path)
            )

    def test_a_folder_change_on_its_own_is_left_alone(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIsNone(check("cd %s" % root, box.path))

    def test_a_send_from_a_working_folder_under_the_seat_folder_is_allowed(self):
        with Sandbox() as box:
            root, base_id = box.base()
            work = self.working_folder(root, base_id, "proposal/stg-1")
            commit(work, "context/metrics/notes.md", [CLEAN_LINE])
            command = "git -C %s push origin proposal/stg-1" % work
            self.assertIsNone(check(command, root))

    def working_folder(self, root, base_id, branch):
        """A git working folder of the plugin's own, under the seat folder."""
        from gtmbase import paths

        work = os.path.join(paths.worktrees_dir(base_id), "w")
        git(["worktree", "add", "-q", "-b", branch, work], cwd=root)
        return work

    def test_a_send_is_read_against_the_folder_the_command_names(self):
        with Sandbox() as box:
            root, base_id = box.base()
            work = self.working_folder(root, base_id, "proposal/stg-2")
            commit(work, "context/metrics/notes.md", ["mail jane@acme.com"])
            command = "git -C %s push origin proposal/stg-2" % work
            self.assertIn("an email address", check(command, root))

    def test_a_send_from_a_folder_this_account_never_joined_is_left_alone(self):
        """A named folder that is not a base is outside what the gate reads.

        It used to be refused outright. Refusing it stopped ordinary work in
        every other repository on the machine, so the send is now allowed and
        git reports anything wrong with the folder itself.
        """
        with Sandbox() as box:
            root, _base_id = box.base()
            other = plain_repository(box, "elsewhere")
            self.assertIsNone(check("git -C %s push origin main" % other, root))
            self.assertIsNone(check("GIT_DIR=%s git push origin main" % other, root))

    def test_a_command_that_touches_the_seat_folder_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            for command in (
                "rm ~/.gtm-base/sources-read.json",
                'python3 -c "import os; os.remove(os.path.expanduser(\'~/.gtm-base/bases\'))"',
                "GTM_BASE_HOME=/tmp/elsewhere git push origin main",
                "rm -rf %s" % os.environ["GTM_BASE_HOME"],
            ):
                self.assertIn(
                    "GTM Base keeps its own records",
                    check(command, root) or "",
                    command,
                )

    def test_more_spellings_of_the_folder_name_are_refused_now(self):
        """Added 2026-09-20 for findings A1 and H1: five spellings got past.

        Three of them are cheap to catch, and these are those three: another
        letter case, and two names finished off with the characters a shell
        expands. The two that are left, a name built up out of a variable and
        a name joined together inside another program, cannot be caught by any
        pattern at all. They are covered by the fact that the check now fails
        closed: writing over a record in that folder gains nothing, because
        nothing the check decides is read out of it any more.
        """
        with Sandbox() as box:
            root, _base_id = box.base()
            for command in (
                "echo x > ~/.GTM-BASE/machine.json",
                "echo x > ~/.gtm-bas?/machine.json",
                "echo x > ~/.gtm*/machine.json",
                "cd ~ && cd .gtm-b* && echo '{}' > machine.json",
            ):
                self.assertIn(
                    "GTM Base keeps its own records",
                    check(command, root) or "",
                    command,
                )

    def test_the_two_spellings_no_pattern_can_catch_are_named_honestly(self):
        """A1 and H1: these are still allowed through the text rule, and the
        scenarios above them are what says why that is survivable."""
        with Sandbox() as box:
            root, _base_id = box.base()
            for command in (
                "d=.gtm; echo x > ~/$d-base/machine.json",
                "python3 -c \"import os;open(os.path.expanduser('~/.gtm'+"
                "'-base/machine.json'),'w').write('{}')\"",
            ):
                self.assertNotIn(
                    "GTM Base keeps its own records",
                    check(command, root) or "",
                    command,
                )

    def test_the_folder_name_exemption_never_reaches_what_is_being_sent(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["copy at /Users/jane/plan.md"])
            self.assertIn("home folder", check("git push", root))

    def test_a_body_file_named_by_its_full_path_is_read_not_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            folder = os.path.join(box.path, "Users", "me")
            os.makedirs(folder)
            body = os.path.join(folder, "body.md")
            write(body, CLEAN_LINE + "\n")
            self.assertIn("/Users/me/", body)
            self.assertIsNone(check("gh pr create --body-file %s" % body, root))

            write(body, "mail jane@acme.com\n")
            reason = check("gh pr create --body-file %s" % body, root)
            self.assertIn("an email address", reason)

    def test_sending_output_somewhere_is_not_hidden_text(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            for command in (
                "git push origin main 2>&1",
                "git push origin main 2>/dev/null",
                "git push origin main > out.txt",
            ):
                self.assertIsNone(check(command, root), command)

    def test_a_command_that_never_names_git_is_not_read_at_all(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIsNone(check("echo digit", root))
            self.assertIsNone(check("ls -la", root))


class TestReadingAGitHubCall(unittest.TestCase):
    def test_a_body_file_holding_an_address_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            write(os.path.join(root, "body.md"), "Please mail jane@acme.com.\n")
            reason = check("gh pr create --body-file body.md", root)
            self.assertIn("body.md", reason)
            self.assertIn("an email address", reason)
            self.assertNotIn("jane@acme.com", reason)

    def test_a_body_typed_into_the_command_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIn(
                "an email address",
                check('gh pr edit 4 --body "mail jane@acme.com"', root),
            )
            self.assertIn(
                "an email address",
                check("gh api -f body=mail-jane@acme.com repos/x/y/issues", root),
            )

    def test_the_typed_in_form_the_client_uses_is_refused_two_ways(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            command = (
                "gh pr create --body \"$(cat <<'EOF'\n"
                "call me on 415-555-0134\n"
                "EOF\n"
                ")\""
            )
            # The whole command is one quoted string, so it does tokenize; the
            # text it would send is read as part of the command line itself.
            self.assertIsNone(gate.classify(command).deny_reason)
            self.assertEqual(1, len(gate.classify(command).gh_writes))
            reason = check(command, root)
            self.assertIn("a phone number", reason)
            self.assertNotIn("415-555-0134", reason)

            # The other path: a command holding the same text that cannot be
            # tokenized at all is refused as well.
            broken = "gh pr create --body 'call me on 415-555-0134"
            self.assertEqual(
                gate.REASON_UNTOKENIZABLE, gate.classify(broken).deny_reason
            )
            broken_reason = check(broken, root)
            self.assertIn("a phone number", broken_reason)
            self.assertNotIn("415-555-0134", broken_reason)

    def test_a_body_read_from_what_a_person_types_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIn(
                "typed in", check("gh pr create --body-file - --title x", root)
            )

    def test_a_body_file_that_is_not_there_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.assertIn(
                "could not read the file",
                check("gh pr create --body-file missing.md", root),
            )

    def test_a_clean_body_file_is_allowed(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            write(os.path.join(root, "body.md"), CLEAN_LINE + "\n")
            self.assertIsNone(check("gh pr create --body-file body.md", root))


# --- Where the gate reads, and where it does not -----------------------------


class TestWhereTheGateReads(unittest.TestCase):
    """What a send would carry is read out of a base, and nowhere else.

    A joined base, any folder inside one, and the working folders this seat
    makes for itself are read. Every other repository on the machine is left
    alone, because the thing being stopped is a company's own writing leaving
    its base. Brandon's decision of 2026-09-06.
    """

    def test_a_send_from_a_plain_repository_is_not_read(self):
        with Sandbox() as box:
            other = plain_repository(box)
            self.assertIsNone(check("git push origin main", other))

    def test_the_same_send_from_a_joined_base_is_still_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            reason = check("git push", root)
            self.assertIn("an email address", reason or "")
            self.assertNotIn("jane@acme.com", reason)

    def test_a_send_from_a_folder_inside_a_joined_base_is_still_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            inside = os.path.join(root, "context", "metrics")
            self.assertIn("an email address", check("git push", inside) or "")

    def test_a_send_from_a_working_folder_of_our_own_is_still_refused(self):
        with Sandbox() as box:
            from gtmbase import paths

            root, base_id = box.base()
            work = os.path.join(paths.worktrees_dir(base_id), "w")
            git(["worktree", "add", "-q", "-b", "proposal/stg-9", work], cwd=root)
            commit(work, "context/metrics/notes.md", ["mail jane@acme.com"])
            self.assertIn(
                "an email address",
                check("git push origin proposal/stg-9", work) or "",
            )

    def test_a_github_body_from_a_plain_repository_is_not_read(self):
        with Sandbox() as box:
            other = plain_repository(box)
            write(os.path.join(other, "body.md"), "Please mail jane@acme.com.\n")
            self.assertIsNone(check("gh pr create --body-file body.md", other))
            self.assertIsNone(check('gh pr edit 4 --body "mail jane@acme.com"', other))

    def test_the_github_commands_no_skill_uses_are_still_refused(self):
        with Sandbox() as box:
            other = plain_repository(box)
            for command in ("gh repo edit --visibility public", "gh auth token"):
                self.assertIn(
                    "nothing GTM Base does needs that command",
                    check(command, other) or "",
                    command,
                )

    def test_the_refusals_that_read_nothing_still_hold(self):
        with Sandbox() as box:
            other = plain_repository(box)
            self.assertIn(
                "skip the safety check", check("git push --no-verify", other) or ""
            )
            self.assertIn(
                "a different set of safeguards",
                check("git -c core.hooksPath=/tmp push", other) or "",
            )
            self.assertIn(
                "nothing GTM Base does needs that command",
                check("GIT_SSH_COMMAND=/tmp/x git push", other) or "",
            )
            self.assertIn(
                "overwrite the shared history",
                check("git push --force origin main", other) or "",
            )

    def test_the_seat_folder_rule_still_holds(self):
        with Sandbox() as box:
            other = plain_repository(box)
            seat = os.environ["GTM_BASE_HOME"]
            for command in ("rm -rf %s" % seat, "cat %s/machine.json" % seat):
                self.assertIn(
                    "GTM Base keeps its own records",
                    check(command, other) or "",
                    command,
                )

    def test_a_folder_change_into_a_plain_repository_is_not_read(self):
        with Sandbox() as box:
            other = plain_repository(box)
            self.assertIsNone(
                check("cd %s && git push origin main" % other, box.path)
            )

    def test_a_folder_change_into_a_base_is_read(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            self.assertIn(
                "an email address",
                check("cd %s && git push origin main" % root, box.path) or "",
            )

    def test_reading_the_persons_own_files_still_stops_a_plain_repository(self):
        with Sandbox() as box:
            other = plain_repository(box)
            marker.write_sources_read_marker("session-1")
            for command in ("git push", "gh auth login"):
                self.assertIn(
                    "read your own documents",
                    check(command, other, session_id="session-1") or "",
                    command,
                )


# --- The two session conditions ---------------------------------------------


class TestTheSessionConditions(unittest.TestCase):
    def test_after_reading_the_persons_own_files_nothing_may_leave(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            marker.write_sources_read_marker("session-1")
            for command in ("git push", "gh auth login", "gh pr list"):
                reason = check(command, root, session_id="session-1")
                self.assertIsNotNone(reason, command)
                self.assertIn("read your own documents", reason)

    def test_another_recent_session_stops_a_send_from_a_base(self):
        """Changed 2026-09-20 for findings A1 and H1, and narrowed the same
        day after the first attempt at it went too wide.

        It used to be that only the record this very session wrote stopped a
        send. The session a record names is one more thing a file somebody
        wrote over can hold, so a record young enough to still be about now
        stops a send whichever session wrote it. Where that holds is the part
        that was narrowed: only where the check reads a send at all, which is
        a base or a working folder this seat made. The scenario below this one
        is the other half of that decision and says why.
        """
        with Sandbox() as box:
            root, _base_id = box.base()
            marker.write_sources_read_marker("session-other")
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            reason = check("git push", root, session_id="session-1")
            self.assertIn("read your own documents", reason or "")

    def test_another_recent_session_leaves_an_ordinary_repository_alone(self):
        """Narrowed 2026-09-20, after the wider rule was tried and rejected.

        A record lasts twelve hours and nothing in this release clears it, so
        asking for its age everywhere refused every push from every repository
        on the machine for half a day after any setup run. The owner works
        across many client repositories in a day, and the rule bought little:
        somebody who can write that file can delete it just as easily as they
        can put another session's name in it. So the age half holds only where
        a send is read, and this session's own record still holds everywhere
        (Brandon, 2026-09-20).
        """
        with Sandbox() as box:
            ordinary = plain_repository(box, name="not-a-base")
            marker.write_sources_read_marker("session-other")

            self.assertIsNone(check_now("git push", ordinary, session_id="session-1"))
            self.assertIsNone(
                check_now("gh auth login", ordinary, session_id="session-1")
            )

    def test_another_recent_session_leaves_this_plugins_own_shape_alone(self):
        """The same, on a repository shaped the way this plugin's own is."""
        with Sandbox() as box:
            ordinary = plain_repository(box, name="gtm-base-like")
            os.makedirs(os.path.join(ordinary, "plugins"))
            write(os.path.join(ordinary, "plugins", "notes.md"), "a plugin\n")
            git(["add", "-A"], cwd=ordinary)
            git(["commit", "-q", "-m", "a plugin"], cwd=ordinary)
            marker.write_sources_read_marker("session-other")

            self.assertIsNone(check_now("git push", ordinary, session_id="session-1"))

    def test_this_sessions_own_record_stops_a_send_from_anywhere(self):
        """The half that did not narrow: it holds in every repository, because
        the text this session is holding could be pasted into any of them."""
        with Sandbox() as box:
            ordinary = plain_repository(box, name="not-a-base")
            marker.write_sources_read_marker("session-1")

            for command in ("git push", "gh auth login"):
                reason = check_now(command, ordinary, session_id="session-1")
                self.assertIn("read your own documents", reason or "", command)

    def test_a_record_that_cannot_be_read_stops_a_send_from_anywhere(self):
        """A1 and H1: writing an empty object over it used to clear the rule.

        This half did not narrow either. A record nobody can read is the shape
        a record takes after it has been written over, and there is nothing in
        it to say which session it belongs to, so it stops a send wherever the
        send comes from.
        """
        with Sandbox() as box:
            root, _base_id = box.base()
            ordinary = plain_repository(box, name="not-a-base")
            marker.write_sources_read_marker("session-1")
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            with open(marker.marker_path(), "w", encoding="utf-8") as handle:
                handle.write("{}")

            for where in (root, ordinary):
                reason = check_now("git push", where, session_id="session-2")
                self.assertIn("read your own documents", reason or "", where)

    def test_the_safeguard_inside_a_base_still_asks_for_the_age(self):
        """It runs inside git with no session to compare against, and it is
        only ever installed in a base, so age is all it has and costs nothing
        outside one."""
        with Sandbox() as box:
            root, _base_id = box.base()
            marker.write_sources_read_marker("session-other")
            lines = "refs/heads/main %s refs/heads/main %s\n" % ("a" * 40, "b" * 40)

            self.assertIn(
                "read your own documents", gate.check_git_hook(lines, root) or ""
            )

    def test_clearing_the_marker_lets_a_send_through_again(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            marker.write_sources_read_marker("session-1")
            self.assertIsNotNone(check("git push", root))
            marker.clear_sources_read_marker()
            self.assertIsNone(check("git push", root))

    def test_the_first_backup_is_refused_and_no_record_can_say_otherwise(self):
        """Changed 2026-09-20 for findings A1 and H1, and it used to say the
        opposite about its second half.

        It used to say that writing yes into this seat's own record let the
        send through, which is exactly what both reviewers reproduced with one
        plain file write. The first backup review is not shipped, so nothing
        in this release sets that record honestly, and the check no longer
        reads it: the answer is always that the first backup is not reviewed.
        """
        with Sandbox() as box:
            root, base_id = box.base(reviewed=False)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            reason = check_now("git push", root)
            self.assertEqual(
                "This base has never been backed up before; run the first backup "
                "review in the join skill before anything leaves this computer.",
                reason,
            )
            self.assertIsNotNone(check_now("gh pr create --title x", root))

            state.update_seat(base_id, first_push_reviewed=True)
            self.assertEqual(reason, check_now("git push", root))

    def test_a_base_this_account_never_joined_is_held_back_too(self):
        """Changed 2026-09-20 for findings A1 and H1, and it used to say the
        opposite.

        A base counted as a base only when this account's own record named it,
        and that record is a file. Writing an empty object over it made a
        joined base read as no base at all, which took away the first backup
        rule and everything else the check reads before a send. A folder
        shaped like a base is now a base to the check whether the record names
        it or not.
        """
        with Sandbox() as box:
            root, _base_id = box.base(joined=False)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            self.assertIsNotNone(check_now("git push", root))

    def test_a_base_whose_record_was_written_over_is_still_a_base(self):
        """A1 and H1, reproduced: the record emptied, the send read all the same."""
        with Sandbox() as box:
            from gtmbase import paths

            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])
            with open(paths.machine_state_path(), "w", encoding="utf-8") as handle:
                handle.write("{}")

            self.assertTrue(gate.folder_is_in_scope(root))
            self.assertTrue(gate.first_push_is_unreviewed(root))
            self.assertIn("an email address", check("git push", root) or "")

    def test_another_recent_session_still_reaches_a_base_whose_record_was_emptied(self):
        """The narrowing turns on whether the folder is one the check reads,
        and that is decided by the folder's own shape, so emptying the record
        of joined bases does not take the rule away with it."""
        with Sandbox() as box:
            from gtmbase import paths

            root, _base_id = box.base()
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            with open(paths.machine_state_path(), "w", encoding="utf-8") as handle:
                handle.write("{}")
            marker.write_sources_read_marker("session-other")

            reason = check("git push", root, session_id="session-1")
            self.assertIn("read your own documents", reason or "")

    def test_an_ordinary_repository_is_still_left_alone_entirely(self):
        """The rule 0.1.4 settled on, checked again after the scope widened."""
        with Sandbox() as box:
            root = plain_repository(box, name="not-a-base")

            self.assertFalse(gate.folder_is_in_scope(root))
            self.assertFalse(gate.first_push_is_unreviewed(root))
            self.assertIsNone(check_now("git push", root))

    def test_this_plugins_own_repository_is_left_alone_entirely(self):
        """It is a repository with no map where a base keeps one, so it is not
        a base, and nothing about this release changes how it behaves."""
        self.assertFalse(gate.folder_is_in_scope(support.REPO_ROOT))
        self.assertFalse(gate.first_push_is_unreviewed(support.REPO_ROOT))

    def test_a_question_that_cannot_be_answered_is_answered_yes(self):
        """It used to be answered no, so anything that broke the question let
        the send through (gate.py 1073 to 1076, finding A1)."""
        with Sandbox() as box:
            root, _base_id = box.base()
            broken = FakeGitRunner()

            with mock.patch.object(
                gate.paths, "resolve_base", side_effect=RuntimeError("no")
            ):
                self.assertTrue(gate.first_push_is_unreviewed(root, git=broken))


# --- The caps ----------------------------------------------------------------


class TestTheSizeCaps(unittest.TestCase):
    def test_a_change_larger_than_the_cap_is_refused_without_being_read(self):
        runner = FakeGitRunner()
        runner.add(["rev-parse", "--show-toplevel"], stdout="/base\n")
        runner.add(
            ["diff", "%s..HEAD" % gate.EMPTY_TREE, "--stat", "--no-color"],
            stdout=" a file | 2 +\n 1 file changed, 900000 insertions(+), 5 deletions(-)\n",
        )
        with Sandbox() as box:
            folder = a_working_folder()
            reason = gate.check_command("git push", folder, "session-1", git=runner)
            self.assertIn("larger than the check can read", reason)
            for call in runner.calls:
                self.assertNotIn("--unified=0", call["args"])

    def test_more_saved_work_than_the_check_can_read_is_refused(self):
        runner = FakeGitRunner()
        runner.add(["rev-parse", "--show-toplevel"], stdout="/base\n")
        runner.add(
            [
                "rev-list",
                "--max-count=%d" % (gate.MAX_PUSH_COMMITS + 1),
                "--count",
                "HEAD",
            ],
            stdout="%d\n" % (gate.MAX_PUSH_COMMITS + 1),
        )
        with Sandbox() as box:
            folder = a_working_folder()
            reason = gate.check_command("git push", folder, "session-1", git=runner)
            self.assertIn("more saved work", reason)


# --- The wrapper -------------------------------------------------------------


def run_wrapper(payload, environment=None, path=None):
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_DIR
    if environment:
        env.update(environment)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        ["/bin/sh", WRAPPER, "claude"],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


class TestTheWrapper(unittest.TestCase):
    def test_both_shell_scripts_parse(self):
        for script in (WRAPPER,):
            finished = subprocess.run(
                ["/bin/sh", "-n", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(0, finished.returncode, finished.stderr)

    def test_a_harmless_command_produces_nothing(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            finished = run_wrapper(
                {
                    "session_id": "session-1",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git status"},
                    "cwd": root,
                }
            )
            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)

    def test_a_send_from_a_base_is_refused_in_the_clients_shape(self):
        """Changed 2026-09-20 for findings A1 and H1, and the sentence it
        reads back changed with it.

        It used to send from a base carrying a file that is one person's
        alone, and read back the sentence naming that file. This release
        refuses every send from a base before anything is read, because the
        first backup review is not shipped, so the sentence a real run reads
        back is that one. What the wrapper does with a refusal, which is what
        this scenario is for, is unchanged.
        """
        with Sandbox() as box:
            root, _base_id = box.base()
            commit(root, "work/inbox/call.md", ["nothing unusual here"])
            finished = run_wrapper(
                {
                    "session_id": "session-1",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git push"},
                    "cwd": root,
                }
            )
            self.assertEqual(0, finished.returncode)
            verdict = json.loads(finished.stdout.decode("utf-8"))
            output = verdict["hookSpecificOutput"]
            self.assertEqual("PreToolUse", output["hookEventName"])
            self.assertEqual("deny", output["permissionDecision"])
            self.assertIn(
                "never been backed up", output["permissionDecisionReason"]
            )
            self.assertNotIn("@", output["permissionDecisionReason"])

    def test_without_python_the_wrapper_refuses_by_itself(self):
        with Sandbox() as box:
            empty = os.path.join(box.path, "bin")
            os.makedirs(empty)
            os.symlink(shutil_which("cat"), os.path.join(empty, "cat"))
            finished = run_wrapper(
                {
                    "session_id": "session-1",
                    "tool_name": "Bash",
                    "tool_input": {"command": "git push"},
                    "cwd": box.path,
                },
                path=empty,
            )
            self.assertEqual(0, finished.returncode)
            verdict = json.loads(finished.stdout.decode("utf-8"))
            output = verdict["hookSpecificOutput"]
            self.assertEqual("deny", output["permissionDecision"])
            self.assertIn("python3 is missing", output["permissionDecisionReason"])

    def test_a_request_it_cannot_read_is_refused(self):
        finished = subprocess.run(
            ["/bin/sh", WRAPPER, "claude"],
            input=b"not json at all",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN_DIR),
        )
        verdict = json.loads(finished.stdout.decode("utf-8"))
        self.assertEqual(
            "deny", verdict["hookSpecificOutput"]["permissionDecision"]
        )

    def test_another_tool_is_not_this_hooks_business(self):
        finished = run_wrapper(
            {
                "session_id": "session-1",
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/x"},
                "cwd": "/tmp",
            }
        )
        self.assertEqual(b"", finished.stdout)

    def test_the_codex_verdict_has_the_same_shape(self):
        payload = gate.deny_payload("codex", "one sentence")
        self.assertEqual(
            json.loads(gate.deny_payload("claude", "one sentence")),
            json.loads(payload),
        )
        self.assertEqual(
            "deny", json.loads(payload)["hookSpecificOutput"]["permissionDecision"]
        )


def shutil_which(name):
    found = shutil.which(name)
    if found is None:
        raise unittest.SkipTest("%s is not on PATH" % name)
    return found


# --- The safeguard git itself runs ------------------------------------------


class TestTheSafeguardGitRuns(unittest.TestCase):
    def test_a_range_holding_a_transient_file_is_refused(self):
        with Sandbox() as box, once_the_first_backup_review_ships():
            root, _base_id = box.base()
            before = head_of(root)
            commit(root, "work/inbox/call.md", ["nothing unusual here"])
            after = head_of(root)
            lines = "refs/heads/main %s refs/heads/main %s\n" % (after, before)
            reason = gate.check_git_hook(lines, root)
            self.assertIn("work/inbox/call.md", reason)

    def test_a_clean_range_is_allowed(self):
        with Sandbox() as box, once_the_first_backup_review_ships():
            root, _base_id = box.base()
            before = head_of(root)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            after = head_of(root)
            lines = "refs/heads/main %s refs/heads/main %s\n" % (after, before)
            self.assertIsNone(gate.check_git_hook(lines, root))

    def test_the_first_backup_rule_holds_inside_the_base_too(self):
        """Added 2026-09-20 for findings A1 and H1: the safeguard git runs is
        the layer that still holds when a command is written in a way no
        pattern can read, so the rule has to hold there as well."""
        with Sandbox() as box:
            root, _base_id = box.base()
            before = head_of(root)
            commit(root, "context/metrics/notes.md", [CLEAN_LINE])
            after = head_of(root)
            lines = "refs/heads/main %s refs/heads/main %s\n" % (after, before)

            self.assertIn(
                "never been backed up", gate.check_git_hook(lines, root) or ""
            )

    def test_a_recent_reading_of_the_persons_files_refuses_every_send(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            marker.write_sources_read_marker("any-session")
            lines = "refs/heads/main %s refs/heads/main %s\n" % ("a" * 40, "b" * 40)
            self.assertIn("read your own documents", gate.check_git_hook(lines, root))


# --- V3, N1 and V7 of the 2026-09-20 verification round ----------------------


class TestWhatCountsAsABase(unittest.TestCase):
    """V3 and N1. Identity used to rest on one file nobody had saved.

    One rename of the map in the working folder took a base out of the gate's
    reach entirely, and the opposite error was there too: an ordinary
    repository that happened to hold a file of that name was held to a base's
    rules for ever.
    """

    def a_secret(self, root):
        commit(root, "context/metrics/notes.md", ["mail jane@acme.com"])

    def test_renaming_the_map_does_not_take_a_base_out_of_reach(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.a_secret(root)
            os.rename(
                os.path.join(root, "context", "map.md"),
                os.path.join(root, "context", "map.txt"),
            )

            self.assertTrue(gate.folder_is_in_scope(root))
            self.assertIn("an email address", check("git push", root) or "")

    def test_a_copy_of_a_base_with_the_map_taken_out_is_still_a_base(self):
        with Sandbox() as box:
            root, _base_id = box.base()
            self.a_secret(root)
            other = os.path.join(box.path, "other")
            git(["clone", "-q", root, other], cwd=box.path)
            os.remove(os.path.join(other, "context", "map.md"))

            self.assertTrue(gate.folder_is_in_scope(other))

    def test_an_ordinary_repository_holding_that_file_is_not_a_base(self):
        with Sandbox() as box:
            plain = os.path.join(box.path, "plain")
            os.makedirs(os.path.join(plain, "context"))
            git(["init", "-q", "-b", "main"], cwd=plain)
            git(["config", "--local", "user.email", "owner@example.com"], cwd=plain)
            git(["config", "--local", "user.name", "Test Owner"], cwd=plain)
            write(os.path.join(plain, "context", "map.md"), "a site map\n")
            write(os.path.join(plain, "notes.md"), "mail jane@acme.com\n")
            git(["add", "-A"], cwd=plain)
            git(["commit", "-q", "-m", "first"], cwd=plain)

            self.assertFalse(gate.folder_is_in_scope(plain))
            self.assertIsNone(check_now("git push origin main", plain))

    def test_the_record_of_joined_bases_emptied_leaves_a_base_in_reach(self):
        with Sandbox() as box:
            from gtmbase import paths as paths_module

            root, _base_id = box.base()
            self.a_secret(root)
            write(paths_module.machine_state_path(), "{}")

            self.assertTrue(gate.folder_is_in_scope(root))

    def test_a_shape_check_that_goes_wrong_leaves_a_base_in_reach(self):
        """A question that cannot be answered is never answered no."""
        with Sandbox() as box:
            root, _base_id = box.base()

            with mock.patch.object(
                gate.paths, "is_base_shaped", side_effect=OSError("no")
            ):
                self.assertTrue(gate.folder_is_in_scope(root))


class TestFirstBackupConsentIsCheckedWhereTheSendIs(unittest.TestCase):
    """V7. It used to be checked against the folder the command was typed in."""

    def test_a_send_named_with_a_folder_of_its_own_is_checked(self):
        with Sandbox() as box:
            root, _base_id = box.base(reviewed=False)
            elsewhere = os.path.join(box.path, "elsewhere")
            os.makedirs(elsewhere)

            reason = check_now(
                "git -C %s push origin main" % root, elsewhere
            )

            self.assertIn("backup", reason or "")

    def test_a_send_after_moving_into_the_base_is_checked(self):
        with Sandbox() as box:
            root, _base_id = box.base(reviewed=False)
            elsewhere = os.path.join(box.path, "elsewhere")
            os.makedirs(elsewhere)

            reason = check_now("cd %s && git push origin main" % root, elsewhere)

            self.assertIn("backup", reason or "")

    def test_an_ordinary_repository_is_still_let_through(self):
        with Sandbox() as box:
            other = plain_repository(box)

            self.assertIsNone(check_now("git push origin main", other))



# --- F3, M2 and L4 of the third look -----------------------------------------


class TestIdentityAcrossTheWholeSavedHistory(unittest.TestCase):
    """F3 and M2. Only the one commit standing in front of you was asked.

    A copy of a base standing on a line of work of its own, or one with a
    single saved removal of the map, answered no to every question about what
    it was, and a send of the main line went unread with every earlier commit
    of the base in it.
    """

    def a_copy_of_a_base(self, box):
        """A copy of a base, with something in it that must not be sent.

        The line being added is put in the copy rather than in the base, so
        the shared copy has never seen it and a send from here really would
        carry it off the computer.
        """
        root, _base_id = box.base()
        other = os.path.join(box.path, "copy")
        git(["clone", "-q", os.path.join(box.path, "base-origin.git"), other],
            cwd=box.path)
        git(["config", "--local", "user.email", "owner@example.com"], cwd=other)
        git(["config", "--local", "user.name", "Test Owner"], cwd=other)
        commit(other, "context/metrics/notes.md", ["mail jane@acme.com"])
        return root, other

    def test_a_copy_standing_on_a_line_of_its_own_is_still_a_base(self):
        with Sandbox() as box:
            _root, other = self.a_copy_of_a_base(box)
            git(["checkout", "-q", "--orphan", "side"], cwd=other)
            git(["rm", "-rqf", "."], cwd=other)
            write(os.path.join(other, "x.txt"), "x\n")
            git(["add", "-A"], cwd=other)
            git(["commit", "-q", "-m", "side"], cwd=other)

            self.assertTrue(gate._looks_like_a_base(other))
            self.assertIn(
                "an email address",
                check("git push origin main", other) or "",
            )

    def test_a_copy_standing_at_an_earlier_point_is_still_a_base(self):
        with Sandbox() as box:
            _root, other = self.a_copy_of_a_base(box)
            git(["checkout", "-q", "--detach", "HEAD~1"], cwd=other)

            self.assertTrue(gate._looks_like_a_base(other))

    def test_a_copy_with_the_map_taken_out_and_saved_is_still_a_base(self):
        with Sandbox() as box:
            _root, other = self.a_copy_of_a_base(box)
            git(["rm", "-r", "-q", "context/map.md"], cwd=other)
            git(["commit", "-q", "-m", "tidy"], cwd=other)

            self.assertTrue(gate._looks_like_a_base(other))
            self.assertIn(
                "an email address",
                check("git push origin main", other) or "",
            )

    def test_an_ordinary_repository_is_still_not_a_base(self):
        with Sandbox() as box:
            other = plain_repository(box)

            self.assertFalse(gate._looks_like_a_base(other))
            self.assertIsNone(check_now("git push origin main", other))

    def test_a_question_that_times_out_answers_yes(self):
        """L4. Nothing raised, so nothing was ever answered yes by accident."""
        with Sandbox() as box:
            root, _base_id = box.base()
            slow = support.SlowRunner(seconds=0.0)

            with mock.patch.object(
                gate.paths, "git_root", side_effect=lambda *a, **k: root
            ):
                with mock.patch.object(
                    gate, "_base_id_key", side_effect=OSError("no binary")
                ):
                    self.assertTrue(gate._looks_like_a_base(root, slow))

    def test_a_runner_that_only_ever_fails_leaves_a_joined_base_in_reach(self):
        with Sandbox() as box:
            root, _base_id = box.base()

            self.assertTrue(gate._looks_like_a_base(root, FakeGitRunner()))


class TestTheNameABaseIsKnownByCannotBeChanged(unittest.TestCase):
    """F3. Taking the name out of the folder's own settings went unremarked."""

    def test_unsetting_it_is_refused(self):
        with Sandbox() as box:
            root, _base_id = box.base()

            reason = check_now("git config --local --unset gtmbase.id", root)

            self.assertTrue(reason)

    def test_setting_it_is_refused_anywhere(self):
        with Sandbox() as box:
            other = plain_repository(box)

            reason = check_now("git config --local gtmbase.id anything", other)

            self.assertTrue(reason)

    def test_an_ordinary_setting_is_left_alone(self):
        with Sandbox() as box:
            other = plain_repository(box)

            self.assertIsNone(
                check_now("git config --local user.name Dana", other)
            )



if __name__ == "__main__":
    unittest.main()
