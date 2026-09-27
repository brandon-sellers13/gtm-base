"""The live-check follow-up unit: what the 0.3.1 live check found, built.

Brandon ran the 0.3.1 live check in ~/Gridwise on 2026-09-27 and decided the
calls it raised the same day (calls 32, 33, 34, 36, 37, 40, 45 and 49 of the
plan's For Brandon table). Every test here failed before the change it covers.

The hand edit (calls 33, 34 and 49, and step 5's showing findings) asks one
question, long the first three times and short after that, and takes one of
three answers: the business changed, a fact the company states was corrected,
or only the wording changed. Its change is shown as the changed sentence once,
with what was taken out and what was put in marked, under a "What changed:"
line that is never cut off and a "Why:" line in the person's own words.
"""

import os
import subprocess
import sys
import unittest

import support
import test_approve_local as approve_tests

from gtmbase import (
    approve_local,
    compose_proposal,
    constants,
    formats,
    hand_edit,
    moment,
    names,
    state,
)

TODAY = approve_tests.TODAY
NOW = approve_tests.NOW
OWNER = approve_tests.OWNER
ICP = approve_tests.ICP
POSITIONING = "context/strategy/positioning.md"
NoRemoteRunner = support.NoRemoteRunner

SKILLS_DIR = os.path.join(support.PLUGIN_DIR, "skills")
PROPOSE = os.path.join(SKILLS_DIR, "propose-change", "scripts", "propose.py")
APPROVE = os.path.join(SKILLS_DIR, "propose-change", "scripts", "approve_local.py")
PROPOSE_SKILL = os.path.join(SKILLS_DIR, "propose-change", "SKILL.md")

# The part of the profile the live check's edit was in, as a paragraph of
# three sentences and a list, so the showing can be seen to show one sentence.
WHAT_WE_SELL = (
    "## What we sell\n\n"
    "We collect earnings and trip data directly from drivers. We hold data on "
    "500k drivers a year. Buyers who try it, buy it.\n\n"
    "- **It answers the questions company disclosures cannot.** Analysts use it.\n"
    "- **It is current.** Updated every week.\n"
)
THE_CORRECTED_LINE = (
    "We collect earnings and trip data directly from drivers. We hold data on "
    "over 1 million drivers since 2017. Buyers who try it, buy it."
)
FACT_ANSWER = (
    "Nothing about the business changed. A review against the full earnings "
    "database back to 2017 showed we can claim over 1 million drivers, where "
    "we used to cite 500k a year."
)
FACT_LINE = (
    "Our verified driver count is over 1 million since 2017, replacing the "
    "500k a year we used to cite"
)
POSITIONING_TEXT = (
    "---\nkind: positioning\nowner: owner@example.com\nlast_confirmed: "
    "2026-01-01\nsources: []\nstatus: draft\n---\n\n# Positioning\n\n## Proof\n\n"
    "Data on 500k drivers a year.\n"
)


def a_base(sandbox):
    """A base with no shared copy, its profile holding the part above, saved."""
    root, base_id = approve_tests.local_base(sandbox)
    whole = os.path.join(root, ICP)
    support.write(whole, support.read(whole) + "\n" + WHAT_WE_SELL)
    support.write(os.path.join(root, POSITIONING), POSITIONING_TEXT)
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "what we sell"], cwd=root)
    return root, base_id


def edit(root, old, new):
    whole = os.path.join(root, ICP)
    support.write(whole, support.read(whole).replace(old, new))


def correct_the_fact(root):
    edit(root, "500k drivers a year", "over 1 million drivers since 2017")


def fix_the_comma(root):
    edit(root, "Buyers who try it, buy it.", "Buyers who try it buy it.")


def run(script, root, *arguments):
    finished = subprocess.run(
        [sys.executable, script] + [str(item) for item in arguments],
        cwd=support.where_a_script_runs(root),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (
        finished.returncode,
        finished.stdout.decode("utf-8"),
        finished.stderr.decode("utf-8"),
    )


def handed(root, kind, text):
    """A words file of one kind, handed out by the script, holding the text."""
    code, printed, errors = run(PROPOSE, root, "--new-words-file", kind)
    assert code == 0, printed + errors
    path = [
        line[len("words=") :].strip()
        for line in printed.split("\n")
        if line.startswith("words=")
    ][0]
    support.write(path, text)
    return path


def pending_one(root):
    folder = os.path.join(root, constants.PROPOSALS_PENDING_DIR)
    waiting = sorted(name for name in os.listdir(folder) if name.endswith(".md"))
    assert len(waiting) == 1, waiting
    return os.path.join(folder, waiting[0])


def correction_records(root):
    found = []
    for folder in constants.ALL_CORRECTIONS_DIRS:
        whole = os.path.join(root, folder.replace("/", os.sep))
        if os.path.isdir(whole):
            found += [name for name in os.listdir(whole) if name.endswith(".md")]
    return [name for name in found if not name.startswith(".")]


def last_subject(root):
    return subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=root,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8").strip()


def four_line(artifact, label):
    for line in artifact.split("\n"):
        if line.startswith(label):
            return line[len(label) :].strip()
    return None


class TestTheOneQuestion(unittest.TestCase):
    """Call 33: one question, in Brandon's words, long three times then short."""

    def test_the_words_are_brandons(self):
        self.assertEqual(
            "Because you changed a document in your base, GTM Base keeps a short "
            "record of it. That gives you a history of why your context changed, "
            "and it lets GTM Base check your other documents against it, so "
            "anything that still says the old thing gets flagged. The record "
            "holds four things: what changed about the business, why, where it "
            "came from, and which documents it affects. I work out the last one "
            "myself.",
            hand_edit.WHY_WE_ASK,
        )
        self.assertEqual(
            "So, in a sentence or two: what changed (in the business, or in a "
            "fact you state about it), why, and where did it come from? If this "
            "was only a wording fix and nothing about the business changed, just "
            "say so and nothing is recorded.",
            hand_edit.LONG_ASK,
        )
        self.assertEqual(
            "I'll keep a record of this edit so your other documents can be "
            "checked against it. What changed (in the business, or in a fact you "
            "state about it), why, and where did it come from? If it was only a "
            "wording fix, say so.",
            hand_edit.SHORT_ASK,
        )

    def test_long_for_the_first_three_and_short_from_the_fourth(self):
        with support.Sandbox() as sandbox:
            _root, base_id = a_base(sandbox)
            long_form = hand_edit.WHY_WE_ASK + "\n\n" + hand_edit.LONG_ASK
            for _time in range(3):
                self.assertEqual(long_form, hand_edit.question(base_id))
                hand_edit.one_more_kept(base_id)
            self.assertEqual(hand_edit.SHORT_ASK, hand_edit.question(base_id))
            # "Why are you asking this?" gets the long version at any time.
            self.assertEqual(long_form, hand_edit.question(base_id, why=True))

    def test_the_script_asks_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            code, printed, errors = run(PROPOSE, root, "--hand-edit-question")
            self.assertEqual(0, code, errors)
            self.assertEqual(
                hand_edit.WHY_WE_ASK + "\n\n" + hand_edit.LONG_ASK, printed.strip()
            )
            state.update_seat(base_id, hand_edits_kept=3)
            code, printed, _errors = run(PROPOSE, root, "--hand-edit-question")
            self.assertEqual(hand_edit.SHORT_ASK, printed.strip())
            code, printed, _errors = run(
                PROPOSE, root, "--hand-edit-question", "--why"
            )
            self.assertEqual(
                hand_edit.WHY_WE_ASK + "\n\n" + hand_edit.LONG_ASK, printed.strip()
            )

    def test_keeping_a_hand_edit_counts_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            fix_the_comma(root)
            staged = compose_proposal.stage_local_edit(
                root, base_id, None, runner=runner, now=TODAY,
                kind=hand_edit.KIND_WORDING,
            )
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(0, hand_edit.kept_so_far(base_id))
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertEqual(1, hand_edit.kept_so_far(base_id))


class TestTheThreeAnswers(unittest.TestCase):
    """Call 34: the business changed, a fact was corrected, or only the words."""

    def test_the_business_changed_records_a_change_in_their_own_words(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            edit(root, "Buyers who try it, buy it.", "We now sell to retail firms.")
            answer = (
                "We started selling the marketing use case to retail firms "
                "this month, after two pilots closed."
            )
            staged = compose_proposal.stage_local_edit(
                root, base_id, answer, runner=runner, now=TODAY,
                kind=hand_edit.KIND_BUSINESS,
                what_changed="We now sell the marketing use case to retail firms.",
            )
            staging = compose_proposal.load_staging(staged)
            entry = formats.ChangeEntry.parse(staging.decision_block)
            self.assertIn("retail firms", entry.body)

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertTrue(
                four_line(shown.artifact, "What changed:").startswith(
                    "We now sell the marketing use case to retail firms."
                ),
                shown.artifact,
            )
            self.assertEqual(answer, four_line(shown.artifact, "Why:"))
            self.assertNotIn("The owner read", shown.artifact)
            self.assertNotIn("review", shown.artifact.lower())

    def test_a_corrected_fact_records_a_change_that_flags_the_other_documents(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            correct_the_fact(root)
            staged = compose_proposal.stage_local_edit(
                root, base_id, FACT_ANSWER, runner=runner, now=TODAY,
                kind=hand_edit.KIND_FACT,
                what_changed=FACT_LINE,
                also_affects=[POSITIONING],
            )
            entry = formats.ChangeEntry.parse(
                compose_proposal.load_staging(staged).decision_block
            )
            self.assertEqual([ICP, POSITIONING], list(entry.affects))
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn(
                names.document_name(POSITIONING),
                four_line(shown.artifact, "What it affects:"),
            )

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            # The document still repeating the old fact is flagged, and the
            # one the person corrected is not.
            self.assertTrue(
                moment.check(root, base_id, POSITIONING, runner=runner, now=TODAY).flagged
            )
            self.assertFalse(
                moment.check(root, base_id, ICP, runner=runner, now=TODAY).flagged
            )

    def test_a_corrected_fact_is_worded_as_replacing_the_old_one(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            correct_the_fact(root)
            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(
                    root, base_id, FACT_ANSWER, runner=NoRemoteRunner(), now=TODAY,
                    kind=hand_edit.KIND_FACT,
                    what_changed="Our verified driver count is over 1 million.",
                )
            self.assertEqual(
                compose_proposal.CODE_FACT_NOT_REPLACING,
                getattr(caught.exception, "code", None),
            )

    def test_a_document_it_also_affects_has_to_be_in_the_base(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            correct_the_fact(root)
            for wrong in ("context/nowhere.md", "../outside.md", constants.MAP_PATH):
                with self.subTest(path=wrong):
                    with self.assertRaises(Exception) as caught:
                        compose_proposal.stage_local_edit(
                            root, base_id, FACT_ANSWER, runner=NoRemoteRunner(),
                            now=TODAY, kind=hand_edit.KIND_FACT,
                            what_changed=FACT_LINE, also_affects=[wrong],
                        )
                    self.assertEqual(
                        compose_proposal.CODE_NOT_A_DOCUMENT_HERE,
                        getattr(caught.exception, "code", None),
                    )

    def test_a_wording_fix_records_nothing_and_takes_the_short_route(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            fix_the_comma(root)
            staged = compose_proposal.stage_local_edit(
                root, base_id, None, runner=runner, now=TODAY,
                kind=hand_edit.KIND_WORDING,
            )
            staging = compose_proposal.load_staging(staged)
            self.assertIsNone(staging.decision_block)
            self.assertTrue(staging.wording_only)

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertEqual([approve_local.WORDING_ASK], shown.reasons)
            self.assertNotIn("What changed:", shown.artifact)
            self.assertIn("Buyers who try it[took out: ,] buy it.", shown.artifact)
            self.assertIn("## What we sell", shown.artifact)
            self.assertNotIn("Analysts use it", shown.artifact)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            # Call 49: no correction record, and no context change.
            self.assertEqual([], correction_records(root))
            self.assertEqual(
                [],
                [
                    name
                    for name in os.listdir(os.path.join(root, constants.CHANGES_DIR))
                    if name.endswith(".md")
                ]
                if os.path.isdir(os.path.join(root, constants.CHANGES_DIR))
                else [],
            )
            self.assertTrue(last_subject(root).endswith(": " + hand_edit.TYPO_FIX))
            self.assertIn(
                "Buyers who try it buy it.", support.read(os.path.join(root, ICP))
            )
            self.assertEqual("", support.status_of(root))

    def test_the_script_takes_each_answer(self):
        with support.Sandbox() as sandbox:
            root, _base_id = a_base(sandbox)
            correct_the_fact(root)
            answer = handed(root, "source", FACT_ANSWER)
            line = handed(root, "what-changed", FACT_LINE)
            code, printed, errors = run(
                PROPOSE, root, "--local-edit", "--kind", "fact",
                "--source-file", answer, "--what-changed-file", line,
                "--also-affects", POSITIONING,
            )
            self.assertEqual(0, code, printed + errors)
            staging = compose_proposal.load_staging(pending_one(root))
            entry = formats.ChangeEntry.parse(staging.decision_block)
            self.assertIn("replacing the 500k a year", entry.body)
            self.assertIn(POSITIONING, entry.affects)

    def test_the_script_takes_a_wording_fix_with_no_answer_file(self):
        with support.Sandbox() as sandbox:
            root, _base_id = a_base(sandbox)
            fix_the_comma(root)
            code, printed, errors = run(
                PROPOSE, root, "--local-edit", "--kind", "wording"
            )
            self.assertEqual(0, code, printed + errors)
            self.assertTrue(compose_proposal.load_staging(pending_one(root)).wording_only)

    def test_the_script_names_the_exact_difference_before_a_typo_is_accepted(self):
        with support.Sandbox() as sandbox:
            root, _base_id = a_base(sandbox)
            correct_the_fact(root)
            code, printed, errors = run(PROPOSE, root, "--hand-edit-difference")
            self.assertEqual(0, code, errors)
            self.assertIn(
                "We hold data on [took out: 500k drivers a year][put in: over 1 "
                "million drivers since 2017].",
                printed,
            )
            self.assertIn("## What we sell", printed)
            self.assertNotIn("Buyers who try it", printed)
            # Nothing was prepared by looking.
            folder = os.path.join(root, constants.PROPOSALS_PENDING_DIR)
            self.assertFalse(
                os.path.isdir(folder)
                and [name for name in os.listdir(folder) if name.endswith(".md")]
            )


class TestTheShowingOfAHandEdit(unittest.TestCase):
    """Step 5's four findings about the showing, and step 6's first."""

    def stage_the_fact(self, root, base_id, runner):
        correct_the_fact(root)
        return compose_proposal.stage_local_edit(
            root, base_id, FACT_ANSWER, runner=runner, now=TODAY,
            kind=hand_edit.KIND_FACT, what_changed=FACT_LINE,
        )

    def test_the_changed_sentence_once_with_the_change_marked(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            staged = self.stage_the_fact(root, base_id, runner)

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            marked = (
                "We hold data on [took out: 500k drivers a year][put in: over 1 "
                "million drivers since 2017]."
            )
            self.assertEqual(1, shown.artifact.count(marked), shown.artifact)
            self.assertIn("## What we sell", shown.artifact)
            # The sentences around it, and the rest of the part, are not shown.
            self.assertNotIn("Buyers who try it", shown.artifact)
            self.assertNotIn("Analysts use it", shown.artifact)
            self.assertNotIn(approve_local.DIFFERENCE % names.document_name(ICP), shown.artifact)
            self.assertNotIn(approve_local.CARRIES, shown.artifact)

    def test_the_whole_text_on_request(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            staged = self.stage_the_fact(root, base_id, runner)

            whole = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY, whole=True
            )
            short = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertIn(approve_local.DIFFERENCE % names.document_name(ICP), whole.artifact)
            self.assertIn(THE_CORRECTED_LINE, whole.artifact)
            # One yes is bound to the same bytes whichever was shown.
            self.assertEqual(short.shown_hash, whole.shown_hash)

    def test_the_whole_text_through_the_script(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            staged = self.stage_the_fact(root, base_id, NoRemoteRunner())
            code, printed, errors = run(
                APPROVE, root, "--staging", staged, "--show", "--whole"
            )
            self.assertEqual(0, code, errors)
            self.assertIn(THE_CORRECTED_LINE, printed)

    def test_what_changed_is_whole_and_why_is_their_own_sentence(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            staged = self.stage_the_fact(root, base_id, runner)

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertTrue(
                four_line(shown.artifact, "What changed:").startswith(FACT_LINE),
                shown.artifact,
            )
            self.assertNotIn("...", four_line(shown.artifact, "What changed:"))
            self.assertEqual(FACT_ANSWER, four_line(shown.artifact, "Why:"))
            self.assertNotIn("The owner read", shown.artifact)

    def test_the_saved_history_says_the_whole_line(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            staged = self.stage_the_fact(root, base_id, runner)
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
            self.assertTrue(last_subject(root).endswith(": " + FACT_LINE), last_subject(root))

    def test_a_hand_edit_prepared_without_an_answer_names_the_line_that_changed(self):
        """Step 6, finding 1: it quoted the first bullet of the part."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            runner = NoRemoteRunner()
            edit(root, "Updated every week.", "Updated every day.")
            staged = compose_proposal.stage_local_edit(
                root, base_id, approve_tests.HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)

            self.assertEqual(
                "It is current. Updated every day.",
                four_line(shown.artifact, "What changed:"),
            )

    def test_the_prepared_change_says_why_in_their_words(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            staged = self.stage_the_fact(root, base_id, NoRemoteRunner())
            body = formats.parse_pr_body(compose_proposal.load_staging(staged).pr_body)
            self.assertEqual(FACT_ANSWER, body["why"])


class TestNoReviewerOnTheLocalPath(unittest.TestCase):
    """Step 5, finding 2: the local path described a review that does not exist."""

    def test_the_hand_edit_step_of_the_skill_names_no_reviewer(self):
        text = support.read(PROPOSE_SKILL)
        start = text.index("## The hand edit")
        end = text.index("\n## ", start + 1)
        self.assertNotIn("review", text[start:end].lower())

    def test_the_script_names_no_reviewer(self):
        text = support.read(PROPOSE)
        self.assertNotIn("reviewer", text)

    def test_the_skill_writes_the_typo_guard_down_as_a_rule(self):
        text = support.read(PROPOSE_SKILL)
        self.assertIn("--hand-edit-difference", text)
        self.assertIn("only a wording fix", text)
        self.assertIn("--hand-edit-question", text)


if __name__ == "__main__":
    unittest.main()
