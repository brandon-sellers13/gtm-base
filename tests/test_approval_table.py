"""Every approval Release B put in the table still classifies exactly as it did.

Plan 1's Unit 4.2a adds to `approval.py` (the new approval commands, and the
unattended refusal as the first thing `decide` does), on the condition that no
existing approval changes behavior. This test was written against Release
B's `approval.py` before either edit and passes unchanged after both: for
every branch of the table, the sentence a person is asked with and the
library writes the ticket opens are pinned, and so is every read that asks
nothing.
"""

import os
import unittest

import support

from gtmbase import approval


def what(script, arguments):
    return approval._what(script, approval._read_settings(script, arguments))


# (script, its arguments, the sentence, the writes it opens), one per branch.
ASKED = (
    ("approve_local.py", ["--approve", "--staging", "x", "--shown", "h"],
     approval.SAYS_APPROVE_CHANGE, ("approve_local.approve",)),
    ("approve_local.py", ["--drop", "--staging", "x"],
     approval.SAYS_DROP_CHANGE, ("approve_local.drop",)),
    ("confirm.py", ["--answer", "yes"], approval.SAYS_STILL_RIGHT, ("confirm.answer",)),
    ("confirm.py", ["--answer", "no"], approval.SAYS_NO_LONGER_RIGHT, ("confirm.answer",)),
    ("confirm.py", ["--answer", "not-now"], approval.SAYS_PUT_OFF, ("confirm.answer",)),
    ("moment.py", ["--answer", "fix"], approval.SAYS_FIX_FIRST, ("moment.fix_it_first",)),
    ("moment.py", ["--answer", "reflects"], approval.SAYS_ALREADY_SAYS, ("confirm.answer",)),
    ("join.py", ["approve"], approval.SAYS_SAVE_DRAFT, ("join_flow.approve_step",)),
    ("join.py", ["adopt"], approval.SAYS_ADOPT_PAGE, ("join_flow.adoption_approve",)),
    ("join.py", ["adopt-document"], approval.SAYS_ADOPT_PAGE,
     ("join_flow.document_adoption_approve",)),
    ("join.py", ["adopt-leave"], approval.SAYS_LEAVE_PAGE_OUT,
     ("join_flow.adoption_leave_out",)),
    ("join.py", ["draft-leave"], approval.SAYS_LEAVE_SEGMENT_OUT,
     ("join_flow.draft_leave_out",)),
    ("join.py", ["skip"], approval.SAYS_SKIP,
     ("join_flow.skip_step", "join_flow.skip_the_closing_question")),
    ("join.py", ["skip-change"], approval.SAYS_SKIP_CLOSING,
     ("join_flow.skip_the_closing_question",)),
    ("join.py", ["close", "--got-in-the-way-file", "f"], approval.SAYS_CLOSE_NOTE,
     ("join_flow.write_onboarding_note",)),
    ("join.py", ["reconcile-answer", "--answer", "yes"], approval.SAYS_ALREADY_SAYS,
     ("join_flow.reconcile_yes",)),
    ("join.py", ["reconcile-answer", "--answer", "no"], approval.SAYS_NOT_CAUGHT_UP,
     ("join_flow.reconcile_no",)),
    ("stale_check.py", ["--move-changes"], approval.SAYS_MOVE, ("changes.migrate",)),
    ("stale_check.py", ["--not-now-move"], approval.SAYS_MOVE_LATER, ("changes.not_now",)),
    ("stale_check.py", ["--record-change", "record"], approval.SAYS_RECORD_CHANGE,
     ("record_change.record",)),
    ("stale_check.py", ["--dismiss-quiet-record"], approval.SAYS_REMINDER_LATER,
     ("stale_check.dismiss_quiet_record",)),
    ("stale_check.py", ["--record-change", "answer", "--answer", "yes"],
     approval.SAYS_ALREADY_SAYS, ("record_change.answer", "join_flow.reconcile_yes")),
    ("stale_check.py", ["--record-change", "answer", "--answer", "no"],
     approval.SAYS_NOT_CAUGHT_UP, ("record_change.answer", "join_flow.reconcile_no")),
    ("stale_check.py", ["--record-change", "answer", "--answer", "not-now"],
     approval.SAYS_LEFT_FLAGGED, ("record_change.answer",)),
    ("seat.py", ["--quiet", "month"], approval.SAYS_QUIET_MONTH, ("state.go_quiet",)),
    ("seat.py", ["--quiet", "until-asked"], approval.SAYS_QUIET_UNTIL_ASKED, ("state.go_quiet",)),
    ("seat.py", ["--weekly-line", "off"], approval.SAYS_WEEKLY_LINE_OFF,
     ("state.stop_weekly_line",)),
)

# Runs that approve nothing, so nobody is asked.
NOT_ASKED = (
    ("approve_local.py", ["--show", "--staging", "x"]),
    ("approve_local.py", ["--list"]),
    ("moment.py", ["--show"]),
    ("join.py", ["close"]),
    ("join.py", ["adopt-document-show"]),
    ("join.py", ["stack-rows-check"]),
    ("stale_check.py", ["--review"]),
    ("stale_check.py", ["--inventory"]),
    ("stale_check.py", ["--move-changes", "--dry-run"]),
    ("stale_check.py", ["--dismiss-quiet-record", "--dry-run"]),
    ("stale_check.py", ["--record-change", "show"]),
    ("seat.py", ["--weekly-line", "on"]),
)

# Runs whose answer the table does not know, which are never asked with a guess.
UNREADABLE = (
    ("confirm.py", ["--answer", "maybe"]),
    ("join.py", ["reconcile-answer", "--answer", "maybe"]),
    ("stale_check.py", ["--record-change", "answer", "--answer", "maybe"]),
)


class TestEveryEntryStillClassifiesAsBefore(unittest.TestCase):
    def test_every_approval_is_asked_with_its_sentence_and_opens_its_writes(self):
        for script, arguments, says, opens in ASKED:
            with self.subTest(script=script, arguments=arguments):
                self.assertEqual((says, opens), what(script, arguments))

    def test_every_read_asks_nothing(self):
        for script, arguments in NOT_ASKED:
            with self.subTest(script=script, arguments=arguments):
                self.assertIsNone(what(script, arguments))

    def test_an_answer_nobody_knows_is_unreadable(self):
        for script, arguments in UNREADABLE:
            with self.subTest(script=script, arguments=arguments):
                with self.assertRaises(approval.Unreadable):
                    what(script, arguments)

    def test_the_scripts_release_b_named_are_named_the_same(self):
        for script in ("approve_local.py", "confirm.py", "moment.py", "join.py",
                       "stale_check.py", "seat.py"):
            with self.subTest(script=script):
                self.assertTrue(
                    os.path.isfile(os.path.join(support.PLUGIN_DIR, *approval.SCRIPTS[script]))
                )


if __name__ == "__main__":
    unittest.main()
