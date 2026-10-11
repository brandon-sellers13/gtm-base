"""Plan 1, Unit 4.2a, CS30: no approval in a conversation nobody is watching.

Once the runner marks a conversation unattended, the approval check refuses
every approval in it as the very first thing it does, before any ticket is
taken back or made, and whatever permission mode Claude Code is in. Release
B's call 60 lets an ordinary approval run unasked in bypassPermissions and
dontAsk, so this refusal is the one control that still holds there, and it is
tested in every mode.
"""

import os
import unittest

import support
import test_approval_ask as asking
import test_approval_table as table

from gtmbase import approval, authority

MODES = ("default", "acceptEdits", "plan", "auto", "bypassPermissions", "dontAsk", None)
OPERATIONS = os.path.join(support.PLUGIN_DIR, "skills", "propose-change", "scripts", "operations.py")


def command_for(script, arguments):
    where = os.path.join(support.PLUGIN_DIR, *approval.SCRIPTS[script])
    return " ".join(["python3", where] + ["'%s'" % one for one in arguments])


EVERY_APPROVAL = [command_for(script, arguments) for script, arguments, _s, _o in table.ASKED] + [
    "python3 %s --approve-creation stg-0123456789abcdef --shown abc" % OPERATIONS,
    "python3 %s --approve-setting stg-0123456789abcdef --operation map-owner --shown abc" % OPERATIONS,
]


class TestEveryApprovalIsRefusedInEveryMode(unittest.TestCase):
    def test_refused_without_a_question_and_without_a_ticket(self):
        with support.Sandbox():
            authority.mark_unattended("nobody-watching")
            for mode in MODES:
                for command in EVERY_APPROVAL:
                    with self.subTest(mode=mode, command=command[-60:]):
                        answer = asking.decided(command, mode=mode, session="nobody-watching")
                        output = answer["hookSpecificOutput"]
                        self.assertEqual("deny", output["permissionDecision"])
                        self.assertEqual(approval.UNATTENDED, output["permissionDecisionReason"])
                        self.assertNotIn("updatedInput", output)
                        self.assertEqual([], asking.tickets())

    def test_another_conversation_is_asked_as_before(self):
        with support.Sandbox():
            authority.mark_unattended("nobody-watching")
            for command in EVERY_APPROVAL:
                with self.subTest(command=command[-60:]):
                    output = asking.asked(self, command, session="somebody-here")
                    self.assertIn("updatedInput", output)

    def test_a_read_in_a_marked_conversation_is_left_alone(self):
        with support.Sandbox():
            authority.mark_unattended("nobody-watching")
            for script, arguments in table.NOT_ASKED:
                with self.subTest(script=script, arguments=arguments):
                    self.assertIsNone(
                        asking.decided(command_for(script, arguments), session="nobody-watching")
                    )

    def test_a_ticket_made_before_the_mark_is_refused_after_it(self):
        with support.Sandbox():
            command = EVERY_APPROVAL[0]
            output = asking.asked(self, command, session="later-unwatched")
            authority.mark_unattended("later-unwatched")
            answer = asking.decided(output["updatedInput"]["command"], session="later-unwatched")
            self.assertEqual("deny", answer["hookSpecificOutput"]["permissionDecision"])

    def test_a_line_naming_an_approval_script_that_cannot_be_read_is_refused(self):
        with support.Sandbox():
            authority.mark_unattended("nobody-watching")
            for command in (
                command_for("confirm.py", ["--answer", "maybe"]),
                command_for("confirm.py", ["--answer", "yes"]) + " && echo done",
                "echo $(%s)" % command_for("confirm.py", ["--answer", "yes"]),
            ):
                with self.subTest(command=command[-60:]):
                    answer = asking.decided(command, session="nobody-watching")
                    self.assertEqual(
                        approval.UNATTENDED, answer["hookSpecificOutput"]["permissionDecisionReason"]
                    )

    def test_a_record_that_cannot_be_read_refuses_every_conversation(self):
        with support.Sandbox():
            authority.mark_unattended("nobody-watching")
            import shutil

            shutil.rmtree(authority.unattended_path())
            support.write(authority.unattended_path(), "not a folder")
            answer = asking.decided(EVERY_APPROVAL[0], session="somebody-here")
            self.assertEqual("deny", answer["hookSpecificOutput"]["permissionDecision"])


class TestTheNewEntries(unittest.TestCase):
    """The create and settings approvals are asked with their own sentence."""

    def test_asked(self):
        for arguments, says in (
            (["--approve-creation", "stg-0123456789abcdef", "--shown", "x"], approval.SAYS_CREATE),
            (["--approve-setting", "stg-0123456789abcdef", "--operation", "business", "--shown", "x"],
             approval.SAYS_SET_BUSINESS),
        ):
            with self.subTest(arguments=arguments):
                self.assertEqual((says, ("operations.approve",)), table.what("operations.py", arguments))

    def test_preparing_asks_nothing(self):
        for arguments in (
            ["--create", "--path", "context/goals.md", "--document-file", "f", "--reason-file", "r"],
            ["--set", "business", "--path", "context/goals.md", "--value-file", "v", "--reason-file", "r"],
            ["--new-words-file", "reason"],
        ):
            with self.subTest(arguments=arguments):
                self.assertIsNone(table.what("operations.py", arguments))

    def test_two_things_at_once_are_refused(self):
        with self.assertRaises(approval.TwoThings):
            table.what(
                "operations.py",
                ["--approve-creation", "stg-0123456789abcdef", "--approve-setting", "stg-0123456789abcdef"],
            )


if __name__ == "__main__":
    unittest.main()
