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


def run_script(script, root, *arguments):
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
    code, printed, errors = run_script(PROPOSE, root, "--new-words-file", kind)
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
            code, printed, errors = run_script(PROPOSE, root, "--hand-edit-question")
            self.assertEqual(0, code, errors)
            self.assertEqual(
                hand_edit.WHY_WE_ASK + "\n\n" + hand_edit.LONG_ASK, printed.strip()
            )
            state.update_seat(base_id, hand_edits_kept=3)
            code, printed, _errors = run_script(PROPOSE, root, "--hand-edit-question")
            self.assertEqual(hand_edit.SHORT_ASK, printed.strip())
            code, printed, _errors = run_script(
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
            code, printed, errors = run_script(
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
            code, printed, errors = run_script(
                PROPOSE, root, "--local-edit", "--kind", "wording"
            )
            self.assertEqual(0, code, printed + errors)
            self.assertTrue(compose_proposal.load_staging(pending_one(root)).wording_only)

    def test_the_script_names_the_exact_difference_before_a_typo_is_accepted(self):
        with support.Sandbox() as sandbox:
            root, _base_id = a_base(sandbox)
            correct_the_fact(root)
            code, printed, errors = run_script(PROPOSE, root, "--hand-edit-difference")
            self.assertEqual(0, code, errors)
            self.assertIn(
                "We hold data on [took out: 500k][put in: over 1 million] drivers "
                "[took out: a year][put in: since 2017].",
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
                "We hold data on [took out: 500k][put in: over 1 million] drivers "
                "[took out: a year][put in: since 2017]."
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
            code, printed, errors = run_script(
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


# --- Call 32: one ask, and notes after the approval ----------------------------

SKILL_FILES = {
    name: os.path.join(SKILLS_DIR, name, "SKILL.md")
    for name in ("propose-change", "stale-check", "confirm", "join")
}


def in_one_line(path):
    return " ".join(support.read(path).split())


class TestOneAskInEveryFlow(unittest.TestCase):
    """Call 32, and step 5's third and fourth findings and step 7's."""

    def test_every_skill_asks_one_thing_and_keeps_its_notes_for_after(self):
        for name, path in SKILL_FILES.items():
            with self.subTest(skill=name):
                text = in_one_line(path)
                self.assertIn(
                    "Ask only the one thing the step asks, and never several "
                    "questions at once.",
                    text,
                )
                self.assertIn(
                    "Keep anything you notice about the content yourself, such as "
                    "a figure that needs a source or a quote that does not match, "
                    "until after the approval, and then say it once as one short "
                    'note, such as "two things you may want to check".',
                    text,
                )
                self.assertIn("never mention a check that found nothing", text)


# --- Call 40 and step 3: the offer to move a base, and the look before it ------

import test_changes_migration as migration  # noqa: E402

from gtmbase import changes, stale_check  # noqa: E402


class TestTheMoveOffer(migration.MigrationCase):
    """Call 40: the version that brought the change in, and what moves."""

    def review(self):
        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=migration.TODAY,
            session_id="sess-1",
            mode="review",
            dry_run=True,
        )

    def test_the_offer_names_the_version_and_each_thing_that_moves(self):
        self.old_layout()

        offers = [line for line in self.review().sentences if changes.is_the_offer(line)]

        self.assertEqual(
            [
                "GTM Base %s introduced the current layout, which keeps documents, "
                "context changes, and records in new places. Your base still keeps "
                "your customer profile, your positioning and one context change in "
                "the older places. Moving them changes nothing they say, and your "
                "base works either way until you do. Shall I move them now?"
                % constants.CURRENT_LAYOUT_VERSION
            ],
            offers,
        )

    def test_one_thing_to_move_is_named_in_the_singular(self):
        self.documents_on_the_current_layout()
        self.old_layout()

        offers = [line for line in self.review().sentences if changes.is_the_offer(line)]

        self.assertEqual(1, len(offers), offers)
        self.assertIn(
            "Your base still keeps one context change in the older place. Moving "
            "it changes nothing it says",
            offers[0],
        )
        self.assertTrue(offers[0].endswith("Shall I move it now?"))

    def test_a_shared_base_is_told_the_version_and_the_condition(self):
        migration.give_it_a_shared_copy(self.sandbox, self.root)
        self.old_layout((migration.ENTRY_ONE, migration.ENTRY_TWO))

        said = self.review().sentences
        told = [line for line in said if changes.is_every_seat_first(line)]

        self.assertEqual(1, len(told), said)
        self.assertIn("two context changes", told[0])
        self.assertIn("an older one would read the moved base as empty", told[0])
        self.assertEqual([], [line for line in said if changes.is_the_offer(line)])


class TestTheLookBeforeTheMove(migration.MigrationCase):
    """Step 3, finding 1: the look said a sentence written for the builder."""

    def check_move(self):
        code, printed, errors = run_script(
            os.path.join(SKILLS_DIR, "stale-check", "scripts", "stale_check.py"),
            self.root,
            "--check-move",
        )
        self.assertEqual(0, code, errors)
        return printed

    def test_nothing_is_said_about_the_offer_when_it_would_be_made(self):
        self.old_layout()

        said = self.check_move()

        self.assertNotIn("As things stand", said)
        self.assertNotIn("would offer", said)
        self.assertEqual(1, len([line for line in said.split("\n") if line.strip()]))

    def test_the_plain_reason_when_it_would_not_be_offered(self):
        self.old_layout()
        changes.not_now(self.base_id, migration.TODAY)

        said = self.check_move()

        self.assertNotIn("As things stand", said)
        self.assertIn("because you said not now", said)

    def test_the_sentences_written_for_the_builder_are_gone(self):
        for name in ("OFFER_STATE_NOW", "OFFER_STATE_EVERY_SEAT_FIRST", "OFFER_STATE_NONE"):
            self.assertFalse(hasattr(changes, name), name)


# --- Call 45: the warning after a plain yes -----------------------------------


class TestTheListTooLargeToRead(unittest.TestCase):
    def test_it_says_the_list_is_larger_than_one_draft_can_read(self):
        from gtmbase import constants as known

        sentence = known.CONSENT_NARROW_SENTENCE % {"files": "45", "folders": "five"}
        self.assertEqual(
            "That folder holds 45 files across five folders, which is more than "
            "one draft can read. Which of these folders hold your customer "
            "profiles, positioning, messaging, or plans?",
            sentence,
        )
        self.assertNotIn("marketing material", in_one_line(SKILL_FILES["join"]))


# --- Every count in words, and the singular for one ---------------------------


class TestEveryCountIsInWords(unittest.TestCase):
    """No "all 1 of them" anywhere: every %d sentence was looked at."""

    def test_a_count_reads_as_a_person_says_it(self):
        self.assertEqual("one item", names.how_many(1, "item", "items"))
        self.assertEqual("two items", names.how_many(2, "item", "items"))
        self.assertEqual("ten items", names.how_many(10, "item", "items"))
        self.assertEqual("11 items", names.how_many(11, "item", "items"))
        self.assertEqual("One item", names.how_many(1, "item", "items", start=True))

    def test_no_sentence_a_person_reads_counts_in_digits(self):
        import re

        import plain_language

        # The four numbers of the report are figures read out beside their
        # labels, not counts in a sentence, and are left as figures.
        figures = ("report",)
        found = []
        for module, name, _line in plain_language.library_sentence_constants(
            support.LIB_DIR
        ):
            if module in figures:
                continue
            value = getattr(__import__("gtmbase." + module, fromlist=[name]), name)
            if re.search(r"%(\([a-z_]+\))?d", value):
                found.append((module, name))
        self.assertEqual([], found)

    def test_the_counts_said_in_code_are_in_words_too(self):
        for relative in (
            os.path.join("lib", "gtmbase", "stale_check.py"),
            os.path.join("skills", "join", "scripts", "join.py"),
            os.path.join("lib", "gtmbase", "sources.py"),
        ):
            text = support.read(os.path.join(support.PLUGIN_DIR, relative))
            with self.subTest(file=relative):
                self.assertNotIn('"1 file"', text)
                self.assertNotIn("a list of the %d", text)
                self.assertNotIn('"%d %s" % (count', text)

    def test_one_thing_that_could_not_be_read_is_said_in_words(self):
        self.assertEqual(
            "One thing in your base could not be read, so it was left alone.",
            stale_check.MALFORMED_ONE,
        )

    def test_one_item_waiting_is_said_in_the_singular(self):
        from gtmbase import confirm

        said = confirm.INBOX_WAITING % names.how_many(1, "item", "items")
        self.assertIn("one item", said)
        self.assertNotIn("items", said)
        self.assertNotIn("those", said)


if __name__ == "__main__":
    unittest.main()
