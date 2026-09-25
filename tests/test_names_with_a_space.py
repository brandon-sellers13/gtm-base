"""A document whose name has a space in it is refused up front, everywhere.

The line that records an owner confirming a document separates its values with
spaces, so it can never carry such a name. Until that record changes shape in a
later release, every path that would end in writing one of those lines refuses
the document at its earliest point, with one sentence, before anything is
written and before any question is used up. The review and the moment of use
still list or flag such a document, because the person needs to know it is
behind, and the one thing they offer about it is renaming it.

The hand edit, which is where this was found, is proved through its script in
`tests/test_compose_proposal.py`. Every other entry point is proved here.
"""

import datetime
import os
import subprocess
import sys
import unittest

import support
from test_moment_of_use import (
    POSITIONING_TEXT,
    SESSION,
    Base,
    entry_text,
    run_moment,
)

from gtmbase import (
    approve_local,
    confirm,
    constants,
    formats,
    join_flow,
    moment,
    state,
)

SPACED = "context/strategy/our strategy.md"
APPROVE_SCRIPT = os.path.join(
    support.PLUGIN_DIR, "skills", "propose-change", "scripts", "approve_local.py"
)
TODAY = datetime.date(2026, 6, 5)
NOW = datetime.datetime(2026, 6, 5, 12, 30, 0)


def a_base_with_the_document(sandbox, change=True):
    """A base holding a document with a space in its name, flagged by a change."""
    base = Base(sandbox)
    base.write(SPACED, POSITIONING_TEXT)
    base.save("a document with a space in its name")
    if change:
        base.add_change(text=entry_text(affects=(SPACED,)))
    return base


def confirmations_of(base, relative=SPACED):
    return base.read(confirm.confirmations_path_for(relative))


def pending_files(base):
    folder = os.path.join(base.root, constants.PROPOSALS_PENDING_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder) if name.endswith(".md"))


class TestTheSentence(unittest.TestCase):
    def test_any_whitespace_counts_and_an_ordinary_name_does_not(self):
        self.assertTrue(formats.name_has_a_space("context/our strategy.md"))
        self.assertTrue(formats.name_has_a_space("context/our\tstrategy.md"))
        self.assertFalse(formats.name_has_a_space("context/our-strategy.md"))
        self.assertFalse(formats.name_has_a_space("context/stratégie.md"))

    def test_the_confirmation_line_itself_is_unchanged(self):
        """The shape of the record is a later release's to change, not this one's."""
        self.assertEqual(
            ("date", "time", "file", "trigger", "entry", "question", "run"),
            formats.CONFIRMATION_TOKENS,
        )


class TestApprovingHere(unittest.TestCase):
    """Local approval refuses the change before it is shown, and again at the yes."""

    def staged(self, base):
        text = support.read(
            os.path.join(support.TEMPLATES_DIR, "proposal-staging.md")
        ).replace("context/strategy/icp.md", SPACED)
        path = os.path.join(
            base.root,
            constants.PROPOSALS_PENDING_DIR,
            "stg-0000000000000000.md",
        )
        support.write(path, text)
        return path

    def test_show_and_approve_both_refuse_and_nothing_is_written(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox, change=False)
            staged = self.staged(base)
            before = support.read(base.path_to(SPACED))
            saved = support.status_of(base.root)

            shown = approve_local.show(
                staged, base.root, base.base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([formats.CODE_NAME_WITH_A_SPACE], shown.codes)
            self.assertEqual([formats.NAME_WITH_A_SPACE], shown.reasons)
            self.assertFalse(shown.artifact)

            applied = approve_local.approve(
                staged,
                base.root,
                base.base_id,
                "anything",
                runner=support.NoRemoteRunner(),
                now=NOW,
            )
            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual([formats.NAME_WITH_A_SPACE], applied.reasons)

            self.assertEqual(before, support.read(base.path_to(SPACED)))
            self.assertIsNone(confirmations_of(base))
            self.assertEqual(saved, support.status_of(base.root))
            # The prepared change is still there to drop.
            self.assertTrue(os.path.isfile(staged))

    def test_the_script_refuses_with_the_status_every_refusal_uses(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox, change=False)
            staged = self.staged(base)

            shown = subprocess.run(
                [sys.executable, APPROVE_SCRIPT, "--staging", staged],
                cwd=base.root,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            said = shown.stdout.decode("utf-8") + shown.stderr.decode("utf-8")
            self.assertEqual(1, shown.returncode, said)
            self.assertIn(formats.NAME_WITH_A_SPACE, said)
            self.assertNotIn("Shown value: ", said)


class TestAnsweringAQuestion(unittest.TestCase):
    def test_a_yes_is_refused_before_the_question_is_used_up(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox, change=False)
            question = state.issue_question_id(
                base.base_id, SPACED, "threshold", SESSION
            )

            result = confirm.answer(
                base.root,
                base.base_id,
                question,
                confirm.ANSWER_YES,
                SESSION,
                runner=support.NoRemoteRunner(),
            )

            self.assertEqual(confirm.STATUS_REFUSED, result.status)
            self.assertEqual([formats.CODE_NAME_WITH_A_SPACE], result.codes)
            self.assertEqual([formats.NAME_WITH_A_SPACE], result.reasons)
            still_open = [record["id"] for record in confirm.pending_questions(base.base_id)]
            self.assertIn(question, still_open)
            self.assertIsNone(confirmations_of(base))

    def test_the_closing_yes_against_a_change_is_refused(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)

            result = confirm.against_change(
                base.root,
                base.base_id,
                SPACED,
                "stg-" + "a" * 16,
                runner=support.NoRemoteRunner(),
            )

            self.assertEqual(confirm.STATUS_REFUSED, result.status)
            self.assertEqual([formats.NAME_WITH_A_SPACE], result.reasons)
            self.assertIsNone(confirmations_of(base))

    def test_the_line_written_with_a_new_document_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.write(SPACED, POSITIONING_TEXT)

            result = confirm.drafted(
                base.root,
                base.base_id,
                SPACED,
                "run-2026-06-05-00000000",
                runner=support.NoRemoteRunner(),
            )

            self.assertEqual(confirm.STATUS_REFUSED, result.status)
            self.assertEqual([formats.NAME_WITH_A_SPACE], result.reasons)
            self.assertIsNone(confirmations_of(base))

    def test_the_closing_reconciliation_yes_is_refused(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)

            result = join_flow.reconcile_yes(
                base.root,
                base.base_id,
                SPACED,
                "stg-" + "a" * 16,
                runner=support.NoRemoteRunner(),
            )

            self.assertFalse(result.answered_yes)
            self.assertEqual(formats.NAME_WITH_A_SPACE, result.sentence)
            self.assertEqual([formats.CODE_NAME_WITH_A_SPACE], result.codes)
            self.assertIsNone(confirmations_of(base))


class TestTheMomentOfUse(unittest.TestCase):
    def test_it_is_still_flagged_and_offers_only_the_rename(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)

            found = base.check(path=SPACED)

            self.assertTrue(found.flagged)
            self.assertIsNone(found.question_id)
            block = found.block()
            self.assertIn("has not caught up", block)
            self.assertTrue(block.rstrip().endswith(formats.NAME_WITH_A_SPACE))
            for offer in (
                moment.THREE_ANSWERS,
                moment.TWO_ANSWERS,
                moment.FIX_IS_READY,
                moment.FIX_CAN_BE_PREPARED,
            ):
                self.assertNotIn(offer, block)
            self.assertEqual([], confirm.pending_questions(base.base_id))

    def test_fix_it_first_is_refused_and_nothing_is_prepared(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)
            found = base.check(path=SPACED)

            said = moment.fix_it_first(base.root, base.base_id, found)

            self.assertTrue(said.refused)
            self.assertEqual([formats.NAME_WITH_A_SPACE], said.reasons)
            self.assertEqual([], pending_files(base))

    def test_it_already_reflects_this_is_refused(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)
            found = base.check(path=SPACED)

            said = moment.already_reflects(base.root, base.base_id, found, SESSION)

            self.assertEqual(confirm.STATUS_REFUSED, said.status)
            self.assertEqual([formats.NAME_WITH_A_SPACE], said.reasons)
            self.assertIsNone(confirmations_of(base))

    def test_the_script_refuses_both_answers_with_the_one_sentence(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)

            for answer in ("fix", "reflects"):
                said = run_moment(
                    ["--file", SPACED, "--answer", answer, "--question", "q-x"],
                    base.root,
                )
                self.assertEqual(1, said.code, said.out + said.err)
                self.assertIn(formats.NAME_WITH_A_SPACE, said.err)
            self.assertEqual([], pending_files(base))
            self.assertIsNone(confirmations_of(base))


class TestTheReview(unittest.TestCase):
    def test_it_is_listed_with_the_rename_and_asks_no_question(self):
        with support.Sandbox() as sandbox:
            base = a_base_with_the_document(sandbox)

            result = base.review()

            lines = [line for line in result.review if line.path == SPACED]
            self.assertEqual(1, len(lines))
            self.assertIsNone(lines[0].question_id)
            self.assertIn("has not caught up", lines[0].sentence)
            self.assertTrue(lines[0].sentence.endswith(formats.NAME_WITH_A_SPACE))
            self.assertIn(lines[0].sentence, result.sentences)
            asked = [
                record
                for record in confirm.pending_questions(base.base_id)
                if record.get("file") == SPACED
            ]
            self.assertEqual([], asked)
            # Every other document is still asked about as it always was.
            others = [line for line in result.review if line.path != SPACED]
            self.assertTrue(others)
            self.assertTrue(all(line.question_id for line in others))


if __name__ == "__main__":
    unittest.main()
