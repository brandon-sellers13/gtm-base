"""The caps on quiet, and a second change somebody makes by hand.

Findings V11, N5, N7 and N3 of the 2026-09-20 verification round. Two of the
caps could be got round by writing a day far enough in the future rather than
far enough in the past, one of them broke skipping outright on a base whose
confirmation window is longer than the cap, and a second hand edit to one
document could never be proposed at all because its identifier was fixed.
"""

import datetime
import os
import unittest

import support

from gtmbase import (
    compose_proposal,
    constants,
    formats,
    ids,
    join_flow,
    machine,
    state,
)

OWNER = "owner@example.com"
ICP = "context/strategy/icp.md"
TODAY = datetime.date(2026, 6, 5)


def a_base(sandbox, name="local"):
    root = os.path.join(sandbox.path, name)
    base_id = ids.base_id_random()
    support.make_base(root, base_id=base_id)
    support.write(os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n")
    support.write(
        os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n%s\n" % OWNER
    )
    support.write(os.path.join(root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a local base"], cwd=root)
    machine.append_joined(root=root, base_id=base_id, remote=None)
    return root, base_id


class TestADayFarEnoughAheadIsNotQuiet(unittest.TestCase):
    """V11. The cap turned down old days and let every future one through."""

    def a_seat(self, base_id, set_on):
        from gtmbase.fsutil import atomic_write_json
        from gtmbase import paths

        atomic_write_json(
            os.path.join(paths.seat_dir(base_id), state.SEAT_FILE),
            {
                "schema": 1,
                "silent_until": state.SILENT_UNTIL_ASKED,
                "silent_until_set_on": set_on,
            },
        )

    def test_a_day_in_the_year_nine_thousand_is_not_honoured(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            self.a_seat(base_id, "9999-12-31")

            seat, _problems = state.load_seat(base_id)

            self.assertFalse(state.is_silent(seat, datetime.date.today()))

    def test_tomorrow_is_not_honoured_either(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            self.a_seat(base_id, tomorrow.isoformat())

            seat, _problems = state.load_seat(base_id)

            self.assertFalse(state.is_silent(seat, datetime.date.today()))

    def test_a_day_that_is_no_day_at_all_is_not_honoured(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            self.a_seat(base_id, "2026-02-30")

            seat, _problems = state.load_seat(base_id)

            self.assertFalse(state.is_silent(seat, datetime.date.today()))

    def test_quiet_asked_for_today_is_still_honoured(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            self.a_seat(base_id, datetime.date.today().isoformat())

            seat, _problems = state.load_seat(base_id)

            self.assertTrue(state.is_silent(seat, datetime.date.today()))


class TestSkippingWorksOnALongerWindow(unittest.TestCase):
    """N5. The person was told a day and the record was thrown away on load."""

    def a_longer_window(self, root, days=90):
        path = os.path.join(root, constants.MAP_PATH)
        support.write(
            path,
            support.read(path).replace(
                "confirmation_threshold_days: 30",
                "confirmation_threshold_days: %d" % days,
            ),
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "a longer window"], cwd=root)

    def test_the_day_the_person_is_told_is_the_day_that_is_kept(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            self.a_longer_window(root)

            now = datetime.date.today()
            said = join_flow.skip_the_closing_question(root, base_id, today=now)

            kept, _problems = state.load_dismissals(base_id)
            self.assertIsNotNone(
                kept["ledger_behind_dismissed_until"],
                "the record was thrown away and the reminder comes straight back",
            )
            self.assertIn(kept["ledger_behind_dismissed_until"], said)

    def test_the_day_kept_is_never_further_out_than_the_longest_quiet(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            self.a_longer_window(root, days=400)

            now = datetime.date.today()
            join_flow.skip_the_closing_question(root, base_id, today=now)

            kept, _problems = state.load_dismissals(base_id)
            furthest = now + datetime.timedelta(days=state.SILENCE_DAYS)
            self.assertLessEqual(
                kept["ledger_behind_dismissed_until"], furthest.isoformat()
            )

    def test_a_day_written_straight_in_is_brought_back_to_the_cap(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            from gtmbase.fsutil import atomic_write_json
            from gtmbase import paths

            atomic_write_json(
                os.path.join(paths.seat_dir(base_id), state.DISMISSALS_FILE),
                {"schema": 1, "ledger_behind_dismissed_until": "9999-12-31"},
            )

            kept, problems = state.load_dismissals(base_id)

            furthest = datetime.date.today() + datetime.timedelta(
                days=state.SILENCE_DAYS
            )
            self.assertEqual(
                furthest.isoformat(), kept["ledger_behind_dismissed_until"]
            )
            self.assertIn("bad-value", problems)


class TestASeatFileWithASecondName(unittest.TestCase):
    """N7. A file with two names is a file somebody else can also write."""

    def test_it_is_not_read(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            from gtmbase import paths

            state.update_seat(base_id, session_id="sess-1")
            seat_file = os.path.join(paths.seat_dir(base_id), state.SEAT_FILE)
            os.link(seat_file, os.path.join(sandbox.path, "second-name"))

            seat, problems = state.load_seat(base_id)

            self.assertIsNone(seat.get("session_id"))
            self.assertIn("two-names", problems)


class TestASecondChangeMadeByHand(unittest.TestCase):
    """N3. The identifier was fixed, so a second one was always refused."""

    def hand_edit(self, root, was, words):
        path = os.path.join(root, ICP)
        support.write(path, support.read(path).replace(was, words))

    def test_two_hand_edits_to_one_document_each_get_an_identifier(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = support.NoRemoteRunner()

            self.hand_edit(
                root,
                "Companies of any size.",
                "Companies of twenty to two hundred people.",
            )
            first = compose_proposal.stage_local_edit(
                root,
                base_id,
                "The board deck said so, slide four.",
                runner=runner,
                now=TODAY,
                what_changed="We moved up market.",
                records_a_change=True,
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the first edit"], cwd=root)

            self.hand_edit(
                root,
                "Companies of twenty to two hundred people.",
                "Companies of fifty to five hundred people.",
            )
            second = compose_proposal.stage_local_edit(
                root,
                base_id,
                "The board deck said so again, slide nine.",
                runner=runner,
                now=TODAY,
                what_changed="We moved up market again.",
                records_a_change=True,
            )

            self.assertNotEqual(
                os.path.basename(first), os.path.basename(second)
            )
            self.assertTrue(os.path.isfile(second))
            staging = formats.ProposalStaging.parse(support.read(second))
            self.assertEqual(
                staging.staging_id, formats.ChangeEntry.parse(
                    staging.decision_block
                ).id
            )

    def test_an_identifier_a_record_already_holds_is_never_used_again(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = support.NoRemoteRunner()
            self.hand_edit(
                root,
                "Companies of any size.",
                "Companies of twenty to two hundred people.",
            )
            first = compose_proposal.stage_local_edit(
                root, base_id, "The deck said so.", runner=runner, now=TODAY
            )
            taken = os.path.basename(first)[: -len(".md")]
            # The prepared change is gone, and the record of what changed is
            # what remembers it. A second one must not take its name back.
            os.remove(first)
            support.write(
                os.path.join(
                    root,
                    constants.CORRECTIONS_DIR,
                    "%s-%s.md" % (TODAY.isoformat(), taken),
                ),
                "a record\n",
            )

            second = compose_proposal.stage_local_edit(
                root, base_id, "The deck said so.", runner=runner, now=TODAY
            )

            self.assertNotEqual(taken, os.path.basename(second)[: -len(".md")])


if __name__ == "__main__":
    unittest.main()
