"""Unit 1.7e, option D (Brandon's call 57): every approval asks the person.

An approval is a command the assistant runs, and nothing about a command
proves a person wanted it: an assistant steered by text hidden in a document
could show a change and approve it in one breath (Astra's review of 0.3.3,
finding 2). So the check every command already passes through answers "ask"
for every approval, which makes Claude Code put its own question to the
person, with one plain sentence saying what the approval does. The command
the person allows carries a one-time ticket the assistant never saw before
the person said yes, and every library function that writes an approval
refuses without one, so an approval reached any other way writes nothing.

Claude Code's hook documentation, read on 2026-10-10 at
https://code.claude.com/docs/en/hooks: "`"ask"` prompts the user to
confirm"; the reason is "shown to the user in the permission prompt"; and
`updatedInput` can be combined "with `"ask"` to show the modified input to
the user".
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

import plain_language
import support
from test_approve_local import NoRemoteRunner

from gtmbase import approval, approve_local, constants, gate, ids, machine, state
from gtmbase.errors import GtmBaseError

PLUGIN = support.PLUGIN_DIR
APPROVE_LOCAL = os.path.join(PLUGIN, "skills", "propose-change", "scripts", "approve_local.py")
CONFIRM = os.path.join(PLUGIN, "skills", "confirm", "scripts", "confirm.py")
JOIN = os.path.join(PLUGIN, "skills", "join", "scripts", "join.py")
STALE = os.path.join(PLUGIN, "skills", "stale-check", "scripts", "stale_check.py")
MOMENT = os.path.join(PLUGIN, "scripts", "moment.py")
SEAT = os.path.join(PLUGIN, "scripts", "seat.py")
SESSION = "session-one"
OWNER = "owner@example.com"
TODAY = datetime.date(2026, 10, 10)


def payload(command, mode="default", session=SESSION, cwd=None, **extra):
    tool_input = {"command": command, "description": "a step of GTM Base"}
    tool_input.update(extra)
    return {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": tool_input,
        "cwd": cwd or os.getcwd(),
        "permission_mode": mode,
    }


def decided(command, client="claude", **given):
    return approval.decide(payload(command, **given), client=client)


def asked(test, command, **given):
    """The hook's answer for an approval, checked to be an ask."""
    answer = decided(command, **given)
    test.assertIsNotNone(answer, command)
    output = answer["hookSpecificOutput"]
    test.assertEqual("PreToolUse", output["hookEventName"])
    test.assertEqual("ask", output["permissionDecision"], output)
    return output


def nonce_in(output):
    command = output["updatedInput"]["command"]
    prefix = "export %s=" % approval.ENV
    assert command.startswith(prefix), command
    return command[len(prefix):].split(";", 1)[0]


def tickets():
    folder = approval.folder_path()
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder) if name.endswith(".json"))


class NotHeld(object):
    """Run as a process the person never allowed: no ticket held, none named."""

    def __enter__(self):
        self.was = approval._held
        approval._held = False
        self.env = mock.patch.dict(os.environ, {})
        self.env.start()
        os.environ.pop(approval.ENV, None)
        return self

    def __exit__(self, *exc):
        self.env.stop()
        approval._held = self.was
        return False


# --- What the person is asked ------------------------------------------------

APPROVALS = (
    ("python3 %s --staging s.md --approve --shown abc" % APPROVE_LOCAL, "SAYS_APPROVE_CHANGE"),
    ("python3 %s --staging s.md --drop" % APPROVE_LOCAL, "SAYS_DROP_CHANGE"),
    ("python3 %s --question q1 --answer yes" % CONFIRM, "SAYS_STILL_RIGHT"),
    ("python3 %s --question q1 --answer no --reason-file r.txt" % CONFIRM, "SAYS_NO_LONGER_RIGHT"),
    ("python3 %s --question q1 --answer=not-now" % CONFIRM, "SAYS_PUT_OFF"),
    ("python3 %s --file context/icps.md --answer fix --question q" % MOMENT, "SAYS_FIX_FIRST"),
    ("python3 %s --file context/icps.md --answer reflects --question q" % MOMENT, "SAYS_ALREADY_SAYS"),
    ("python3 %s approve --step icp --draft d.md --run r --base b" % JOIN, "SAYS_SAVE_DRAFT"),
    ("python3 %s adopt --run r --segment s --hash h --base b" % JOIN, "SAYS_ADOPT_PAGE"),
    ("python3 %s adopt-leave --run r --segment s --base b" % JOIN, "SAYS_LEAVE_PAGE_OUT"),
    ("python3 %s draft-leave --segment s --base b" % JOIN, "SAYS_LEAVE_SEGMENT_OUT"),
    ("python3 %s reconcile-answer --entry e --file f --answer yes --base b" % JOIN, "SAYS_ALREADY_SAYS"),
    ("python3 %s reconcile-answer --entry e --file f --answer no --base b" % JOIN, "SAYS_NOT_CAUGHT_UP"),
    ("python3 %s --record-change record --shown abc" % STALE, "SAYS_RECORD_CHANGE"),
    ("python3 %s --record-change answer --change c --document d --answer yes" % STALE, "SAYS_ALREADY_SAYS"),
    ("python3 %s --record-change answer --change c --document d --answer no" % STALE, "SAYS_NOT_CAUGHT_UP"),
    ("python3 %s --record-change answer --change c --document d --answer not-now" % STALE, "SAYS_LEFT_FLAGGED"),
    ("python3 %s --move-changes" % STALE, "SAYS_MOVE"),
    ("python3 %s --move-changes --every-seat-updated" % STALE, "SAYS_MOVE"),
    ("python3 %s --not-now-move" % STALE, "SAYS_MOVE_LATER"),
    ("python3 %s --quiet month" % SEAT, "SAYS_QUIET_MONTH"),
    ("python3 %s --quiet until-asked" % SEAT, "SAYS_QUIET_UNTIL_ASKED"),
)

NOT_APPROVALS = (
    "python3 %s --staging s.md --show" % APPROVE_LOCAL,
    "python3 %s --list" % APPROVE_LOCAL,
    "python3 %s --staging s.md --not-yet" % APPROVE_LOCAL,
    "python3 %s --pending" % CONFIRM,
    "python3 %s --file context/icps.md --answer as-is --question q" % MOMENT,
    "python3 %s --file context/icps.md" % MOMENT,
    "python3 %s review --step icp --draft d.md --run r" % JOIN,
    "python3 %s skip --step positioning --run r --base b" % JOIN,
    "python3 %s close --run r --base b" % JOIN,
    "python3 %s resume --base b" % JOIN,
    "python3 %s --review" % STALE,
    "python3 %s --abandon-move" % STALE,
    "python3 %s --record-change documents" % STALE,
    "python3 %s --record-change show --documents 1" % STALE,
    "python3 %s --answer-question q --answer-file a.txt" % STALE,
    "python3 %s --weekly-line off" % SEAT,
    "python3 %s --speak" % SEAT,
    "ls -la",
    "git status",
)


class TestEveryApprovalAsksThePerson(unittest.TestCase):
    def test_each_approval_is_asked_with_the_sentence_that_says_what_it_does(self):
        with support.Sandbox():
            for command, says in APPROVALS:
                output = asked(self, command)
                reason = output["permissionDecisionReason"]
                self.assertIn(getattr(approval, says), reason, command)
                self.assertTrue(reason.startswith(approval.ASK_OPENING), command)
                self.assertTrue(reason.endswith(approval.ASK_CLOSING), command)

    def test_the_relative_spelling_the_skills_use_is_asked_too(self):
        with support.Sandbox():
            output = asked(
                self,
                "cd %s && python3 scripts/confirm.py --question q --answer yes"
                % os.path.join(PLUGIN, "skills", "confirm"),
            )
            self.assertIn(approval.SAYS_STILL_RIGHT, output["permissionDecisionReason"])
            asked(self, "python3 scripts/approve_local.py --staging s.md --approve --shown x")
            asked(self, "python3 -I scripts/approve_local.py --staging s.md --approve --shown x")
            asked(self, "env TZ=UTC python3 scripts/approve_local.py --staging s.md --approve --shown x")

    def test_anything_else_is_left_alone(self):
        with support.Sandbox():
            for command in NOT_APPROVALS:
                self.assertIsNone(decided(command), command)

    def test_the_command_allowed_is_the_one_shown_with_a_ticket_in_front(self):
        with support.Sandbox():
            command = "python3 %s --question q1 --answer yes" % CONFIRM
            output = asked(self, command, timeout=60000)
            updated = output["updatedInput"]
            nonce = nonce_in(output)
            self.assertRegex(nonce, r"\A[0-9a-f]{48}\Z")
            self.assertEqual(
                "export %s=%s; %s" % (approval.ENV, nonce, command), updated["command"]
            )
            # Every other part of what the assistant asked for is kept.
            self.assertEqual("a step of GTM Base", updated["description"])
            self.assertEqual(60000, updated["timeout"])
            self.assertEqual(
                [hashlib.sha256(nonce.encode("ascii")).hexdigest() + ".json"], tickets()
            )
            # Two asks never share a ticket, and the second takes back the first.
            second = nonce_in(asked(self, command))
            self.assertNotEqual(nonce, second)
            self.assertEqual(1, len(tickets()))

    def test_an_approval_with_anything_else_on_its_line_is_refused(self):
        with support.Sandbox():
            for command in (
                "python3 %s --question q --answer yes; echo done" % CONFIRM,
                "python3 %s --question q --answer yes && python3 %s --staging s --approve --shown x"
                % (CONFIRM, APPROVE_LOCAL),
                "python3 do_something.py && python3 %s --question q --answer yes" % CONFIRM,
                "python3 %s --question q --answer yes | tee out.txt" % CONFIRM,
                "python3 %s --question q --answer yes $(rm -rf x)" % CONFIRM,
                "python3 %s --question q --answer yes `touch x`" % CONFIRM,
            ):
                answer = decided(command)
                self.assertIsNotNone(answer, command)
                self.assertEqual(
                    "deny", answer["hookSpecificOutput"]["permissionDecision"], command
                )
                self.assertEqual(
                    approval.ONE_LINE, answer["hookSpecificOutput"]["permissionDecisionReason"]
                )
            self.assertEqual([], tickets())

    def test_no_approval_runs_where_nobody_would_be_asked(self):
        # Claude Code's documentation does not say a hook's "ask" is shown
        # when it is set to run commands without asking, and the live check
        # could not show it, so an approval is refused there rather than run
        # with nobody asked (Brandon's call 60).
        with support.Sandbox():
            command = "python3 %s --question q --answer yes" % CONFIRM
            for mode in ("bypassPermissions", "dontAsk"):
                answer = decided(command, mode=mode)
                self.assertEqual("deny", answer["hookSpecificOutput"]["permissionDecision"])
                self.assertEqual(
                    approval.NOBODY_WOULD_BE_ASKED,
                    answer["hookSpecificOutput"]["permissionDecisionReason"],
                )
            self.assertEqual([], tickets())
            for mode in ("default", "acceptEdits", "auto", "plan", None):
                asked(self, command, mode=mode)

    def test_an_assistant_that_cannot_ask_is_refused(self):
        with support.Sandbox():
            answer = decided("python3 %s --question q --answer yes" % CONFIRM, client="codex")
            self.assertEqual("deny", answer["hookSpecificOutput"]["permissionDecision"])
            self.assertEqual(
                approval.CANNOT_ASK, answer["hookSpecificOutput"]["permissionDecisionReason"]
            )


class TestTheTicket(unittest.TestCase):
    def test_any_later_command_in_the_same_conversation_takes_it_back(self):
        # A ticket the person said no to must never be used, and the only way
        # to use one is to run something, which passes through here first.
        with support.Sandbox():
            asked(self, "python3 %s --question q --answer yes" % CONFIRM)
            self.assertEqual(1, len(tickets()))
            self.assertIsNone(decided("ls", session="another-conversation"))
            self.assertEqual(1, len(tickets()))
            self.assertIsNone(decided("ls"))
            self.assertEqual([], tickets())

    def test_the_command_it_was_made_for_passes_with_its_ticket_kept(self):
        # Should Claude Code ever run the check again on the command it
        # rewrote, that command is let through as it is.
        with support.Sandbox() as sandbox:
            output = asked(self, "python3 %s --question q --answer yes" % CONFIRM)
            rewritten = output["updatedInput"]["command"]
            self.assertIsNone(decided(rewritten))
            self.assertIsNone(gate.check_command(rewritten, sandbox.path, SESSION))
            self.assertEqual(1, len(tickets()))

    def test_a_command_that_sets_the_ticket_itself_is_refused_by_the_check(self):
        with support.Sandbox() as sandbox:
            for command in (
                "%s=%s python3 %s --question q --answer yes" % (approval.ENV, "a" * 48, CONFIRM),
                "export %s=%s; python3 %s --question q --answer yes" % (approval.ENV, "a" * 48, CONFIRM),
                "env %s=x sh run.sh" % approval.ENV,
                "unset %s" % approval.ENV,
                "echo $%s" % approval.ENV,
            ):
                reason = gate.check_command(command, sandbox.path, SESSION)
                self.assertEqual(
                    gate.sentence_for(gate.REASON_APPROVAL_TICKET), reason, command
                )

    def test_the_hook_itself_asks_through_the_check_every_command_passes(self):
        with support.Sandbox() as sandbox:
            command = "python3 %s --question q --answer yes" % CONFIRM
            finished = subprocess.run(
                ["sh", os.path.join(PLUGIN, "hooks", "pre-push-gate.sh"), "claude"],
                input=json.dumps(payload(command, cwd=sandbox.path)).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN),
            )
            answer = json.loads(finished.stdout.decode("utf-8"))
            self.assertEqual("ask", answer["hookSpecificOutput"]["permissionDecision"])
            self.assertIn(
                approval.SAYS_STILL_RIGHT,
                answer["hookSpecificOutput"]["permissionDecisionReason"],
            )


# --- The library refuses an approval nobody was asked about ------------------


def gated_calls():
    """Every library function that writes an approval, called with nothing real.

    Each must refuse for want of a ticket before it reads a single argument,
    so arguments that would fail any other check prove the order.
    """
    from gtmbase import changes, confirm, join_flow, moment, record_change

    nothing = "not-a-real-thing"
    return (
        ("approve_local.approve", lambda: approve_local.approve(nothing, nothing, nothing, nothing)),
        ("approve_local.drop", lambda: approve_local.drop(nothing, nothing, nothing)),
        ("confirm.answer", lambda: confirm.answer(nothing, nothing, nothing, nothing)),
        ("moment.fix_it_first", lambda: moment.fix_it_first(nothing, nothing, None, nothing)),
        ("join_flow.approve_step", lambda: join_flow.approve_step(nothing, nothing, nothing)),
        ("join_flow.adoption_approve", lambda: join_flow.adoption_approve(nothing, nothing, nothing)),
        ("join_flow.adoption_leave_out", lambda: join_flow.adoption_leave_out(nothing, nothing, nothing)),
        ("join_flow.draft_leave_out", lambda: join_flow.draft_leave_out(nothing, nothing)),
        ("join_flow.reconcile_yes", lambda: join_flow.reconcile_yes(nothing, nothing, nothing, nothing)),
        ("join_flow.reconcile_no", lambda: join_flow.reconcile_no(nothing, nothing, nothing, nothing)),
        ("record_change.record", lambda: record_change.record(nothing, nothing, nothing)),
        ("record_change.answer", lambda: record_change.answer(nothing, nothing, nothing, nothing, "yes")),
        ("changes.migrate", lambda: changes.migrate(nothing, nothing)),
        ("changes.not_now", lambda: changes.not_now(nothing)),
        ("state.go_quiet", lambda: state.go_quiet(nothing, "month")),
    )


class TestTheLibraryRefusesWithoutATicket(unittest.TestCase):
    def test_every_approval_writer_refuses_first(self):
        with support.Sandbox(), NotHeld():
            for name, call in gated_calls():
                with self.assertRaises(approval.ApprovalRefused, msg=name) as caught:
                    call()
                self.assertEqual(approval.NOT_ASKED, str(caught.exception), name)
                self.assertIsInstance(caught.exception, GtmBaseError)

    def test_a_ticket_is_used_once(self):
        with support.Sandbox(), NotHeld():
            output = asked(self, "python3 %s --question q --answer yes" % CONFIRM)
            os.environ[approval.ENV] = nonce_in(output)
            approval.require()
            self.assertEqual([], tickets())
            # The same process goes on holding it, for the writes one
            # approval makes.
            approval.require()
            approval._held = False
            with self.assertRaises(approval.ApprovalRefused):
                approval.require()

    def test_a_ticket_left_too_long_or_made_up_is_refused(self):
        with support.Sandbox(), NotHeld():
            output = asked(self, "python3 %s --question q --answer yes" % CONFIRM)
            os.environ[approval.ENV] = nonce_in(output)
            later = datetime.datetime.now() + datetime.timedelta(
                seconds=approval.KEPT_SECONDS + 60
            )
            with mock.patch.object(approval, "_now", return_value=later):
                with self.assertRaises(approval.ApprovalRefused):
                    approval.require()
            for made_up in ("b" * 48, "short", "../../x", ""):
                os.environ[approval.ENV] = made_up
                with self.assertRaises(approval.ApprovalRefused):
                    approval.require()


# --- Through the script, as the person would meet it --------------------------


def local_base(sandbox):
    root = os.path.join(sandbox.path, "local")
    base_id = ids.base_id_random()
    support.make_base(root, base_id=base_id)
    support.write(os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n")
    support.write(os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n%s\n" % OWNER)
    support.write(os.path.join(root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a local base"], cwd=root)
    machine.append_joined(root=root, base_id=base_id, remote=None)
    state.update_seat(base_id, first_push_reviewed=False)
    return root, base_id


class TestThroughTheScript(unittest.TestCase):
    def head(self, root):
        return support.git(["rev-parse", "HEAD"], cwd=root).stdout

    def run_script(self, root, arguments, env):
        finished = subprocess.run(
            [sys.executable, APPROVE_LOCAL] + arguments,
            cwd=support.where_a_script_runs(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        said = finished.stdout.decode("utf-8") + finished.stderr.decode("utf-8")
        return finished.returncode, said

    def test_an_approval_nobody_was_asked_about_writes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = os.path.join(
                root, constants.PROPOSALS_PENDING_DIR, "stg-" + "a" * 16 + ".md"
            )
            support.write(staged, support.staging_template())
            shown = approve_local.show(
                staged, root, base_id, runner=NoRemoteRunner(), now=TODAY
            )
            before = self.head(root)
            arguments = ["--staging", staged, "--approve", "--shown", shown.shown_hash]
            env = dict(os.environ)
            env.pop(approval.ENV, None)
            code, said = self.run_script(root, arguments, env)
            self.assertNotEqual(0, code, said)
            self.assertIn(approval.NOT_ASKED, said)
            self.assertNotIn("Traceback", said)
            self.assertEqual(before, self.head(root))
            self.assertTrue(os.path.isfile(staged))

            # The same command, allowed through the question, writes it.
            command = "python3 %s %s" % (APPROVE_LOCAL, " ".join(arguments))
            output = asked(self, command, cwd=root)
            env[approval.ENV] = nonce_in(output)
            code, said = self.run_script(root, arguments, env)
            self.assertEqual(0, code, said)
            self.assertNotEqual(before, self.head(root))
            self.assertEqual([], tickets())


class TestTheWordsAPersonReads(unittest.TestCase):
    def test_every_new_sentence_is_registered_and_plain(self):
        registered = set(
            name for module, name in plain_language.PYTHON_SENTENCES if module == "approval"
        )
        for name in approval.SENTENCE_NAMES:
            self.assertIn(name, registered)
            text = getattr(approval, name)
            self.assertEqual([], plain_language.find_banned(text), name)
            self.assertEqual([], plain_language.find_dashes(text), name)


if __name__ == "__main__":
    unittest.main()
