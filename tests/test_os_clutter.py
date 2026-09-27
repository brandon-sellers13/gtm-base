"""Release 0.3.2: files the computer makes on its own are not unsaved work.

Step 5 of the release A live check (2026-09-27) asks the person to open their
positioning in an editor, change a sentence, and keep it. Approving the edit
was refused with "You have edits in your base you have not saved", and the
only file besides the edit was a `.DS_Store` that Finder had written into the
folder. Every check that asks whether a base has unsaved work counted it, so
anybody on a Mac who browsed their base could not approve a hand edit, move
their context changes, or have the review bring the base up to date.

Every one of those checks now asks one shared question, `unsaved.look`, and
the proof is here: a base with untracked clutter in it goes through each of
them, a tracked clutter file that changed still counts, clutter is never
saved into a base, and the refusal says which files are unsaved.
"""

import os
import shutil
import subprocess
import unittest

import plain_language
import support
import test_approve_local as approving
import test_changes_migration as migration
import test_confirm as confirming
import test_session_start as starting
import test_stale_check as checking

from gtmbase import (
    approve_local,
    changes,
    confirm,
    create_base,
    drafting,
    location,
    review,
    session_start,
    stale_check,
    unsaved,
)
from gtmbase.errors import ReviewError
from gtmbase.gitcmd import GitRunner

ICP = approving.ICP
TODAY = approving.TODAY
NOW = approving.NOW

# One of each kind of file an operating system leaves in a folder, at the top
# of the base and deeper in it, including a folder that holds nothing else.
CLUTTER = (
    ".DS_Store",
    "._x",
    "context/.DS_Store",
    "context/strategy/._positioning.md",
    "context/new-folder/.DS_Store",
    "Thumbs.db",
    "context/desktop.ini",
    "Icon\r",
    ".Spotlight-V100/Store-V2/index",
    ".Trashes/501/gone.md",
    ".fseventsd/0000",
)


def scatter_clutter(root):
    for relative in CLUTTER:
        support.write(os.path.join(root, relative.replace("/", os.sep)), "made by the computer\n")


def clutter_on_disk(root):
    return [
        relative
        for relative in CLUTTER
        if os.path.isfile(os.path.join(root, relative.replace("/", os.sep)))
    ]


def tracked(root):
    finished = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE
    )
    return [name for name in finished.stdout.decode("utf-8").split("\0") if name]


def staged(root):
    finished = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"], cwd=root, stdout=subprocess.PIPE
    )
    return [name for name in finished.stdout.decode("utf-8").split("\0") if name]


class ClutterAssertions(object):
    def assert_no_clutter_saved(self, root):
        self.assertEqual([], [name for name in tracked(root) if unsaved.is_clutter(name)])
        self.assertEqual([], [name for name in staged(root) if unsaved.is_clutter(name)])
        # And none of it was deleted either. It is not ours to tidy away.
        self.assertEqual(list(CLUTTER), clutter_on_disk(root))


def save_a_ds_store(root):
    """A `.DS_Store` somebody saved into the base once, then changed by Finder."""
    path = os.path.join(root, "context", ".DS_Store")
    support.write(path, "first\n")
    support.git(["add", "-f", "--", "context/.DS_Store"], cwd=root)
    support.git(["commit", "-q", "-m", "a saved finder file"], cwd=root)
    support.write(path, "changed by finder\n")


# --- What counts ---------------------------------------------------------------


class TestWhatCountsAsClutter(unittest.TestCase):
    def test_every_kind_of_clutter_is_clutter(self):
        for relative in CLUTTER:
            self.assertTrue(unsaved.is_clutter(relative), repr(relative))
        for relative in ("THUMBS.DB", "Desktop.ini", "a/b/.ds_store", ".Trashes/"):
            self.assertTrue(unsaved.is_clutter(relative), repr(relative))

    def test_a_persons_own_files_are_not(self):
        for relative in (
            "context/strategy/positioning.md",
            "notes.md",
            "Icon",
            "Icons",
            "Icon1",
            "._",
            ".DS_Store.md",
            "context/DS_Store",
            "my.Trashes/file.md",
            ".gitignore",
            "",
        ):
            self.assertFalse(unsaved.is_clutter(relative), repr(relative))


class TestTheSharedLook(ClutterAssertions, unittest.TestCase):
    def base(self, sandbox):
        root = os.path.join(sandbox.path, "base")
        support.make_base(root)
        return root

    def test_untracked_clutter_leaves_a_base_clean(self):
        with support.Sandbox() as sandbox:
            root = self.base(sandbox)
            scatter_clutter(root)
            status = unsaved.look(root, GitRunner())
            self.assertTrue(status.clean, status.entries)

    def test_a_tracked_clutter_file_that_changed_still_counts(self):
        """It is part of what the base holds, so a change to it is a change.

        Leaving it out would let a write save over it, or save it, without
        anybody having read the difference.
        """
        with support.Sandbox() as sandbox:
            root = self.base(sandbox)
            save_a_ds_store(root)
            status = unsaved.look(root, GitRunner())
            self.assertFalse(status.clean)
            self.assertEqual(["context/.DS_Store"], status.paths())

    def test_clutter_somebody_lined_up_to_save_still_counts(self):
        with support.Sandbox() as sandbox:
            root = self.base(sandbox)
            support.write(os.path.join(root, ".DS_Store"), "x\n")
            support.git(["add", "-f", "--", ".DS_Store"], cwd=root)
            self.assertFalse(unsaved.look(root, GitRunner()).clean)

    def test_a_persons_file_beside_the_clutter_still_counts(self):
        with support.Sandbox() as sandbox:
            root = self.base(sandbox)
            scatter_clutter(root)
            support.write(os.path.join(root, "context", "notes.md"), "mine\n")
            status = unsaved.look(root, GitRunner())
            self.assertEqual(["context/notes.md"], status.paths())


# --- Saying which files --------------------------------------------------------


class TestNamingTheUnsavedFiles(unittest.TestCase):
    def test_a_context_document_is_named_the_way_a_person_calls_it(self):
        self.assertEqual(
            "They are in your positioning.",
            unsaved.where_sentence(["context/strategy/positioning.md"]),
        )

    def test_a_plain_file_name_is_said_as_it_is(self):
        self.assertEqual("They are in notes.txt.", unsaved.where_sentence(["notes.txt"]))

    def test_a_name_that_is_not_plain_is_never_read_out(self):
        for relative in ("bad$name.txt", "under_score.txt", "context/x/a`b.txt"):
            self.assertEqual(
                "They are in one of your files.",
                unsaved.where_sentence([relative]),
                relative,
            )

    def test_a_file_gtm_base_keeps_is_never_named_by_its_identifier(self):
        self.assertEqual(
            "They are in one of your files.",
            unsaved.where_sentence(["work/changes/stg-0d15637d82690cc7.md"]),
        )

    def test_a_file_the_computer_made_is_said_to_be_one(self):
        self.assertEqual(
            "They are in your customer profile and a file your computer made on "
            "its own.",
            unsaved.where_sentence([ICP, "context/.DS_Store"]),
        )
        self.assertEqual(
            "They are in two files your computer made on their own.",
            unsaved.where_sentence([".DS_Store", "context/Thumbs.db"]),
        )

    def test_a_context_file_whose_name_holds_no_words_is_counted(self):
        """Found in review: `-.md` made the name lookup raise, not refuse."""
        for relative in ("context/-.md", "context/_.md", "context/ .md", "context/..md"):
            self.assertEqual(
                "They are in one of your files.",
                unsaved.where_sentence([relative]),
                relative,
            )

    def test_a_name_made_of_punctuation_is_never_read_out(self):
        for relative in (" ", "...", "notes.", "-rf", ".hidden"):
            self.assertEqual(
                "They are in one of your files.",
                unsaved.where_sentence([relative]),
                repr(relative),
            )

    def test_two_files_that_read_out_the_same_are_counted_as_two(self):
        self.assertEqual(
            "They are in notes.txt and one other file.",
            unsaved.where_sentence(["a/notes.txt", "b/notes.txt"]),
        )
        self.assertEqual(
            "They are in two of your files.",
            unsaved.where_sentence(["context/x$.md", "context/y$.md"]),
        )

    def test_more_than_ten_are_counted_in_digits(self):
        self.assertEqual(
            "They are in 12 of your files.",
            unsaved.where_sentence(["f$%d" % number for number in range(12)]),
        )

    def test_many_files_are_counted_after_the_first_three(self):
        self.assertEqual(
            "They are in a.txt, b.txt, c.txt and two other files.",
            unsaved.where_sentence(["a.txt", "b.txt", "c.txt", "d.txt", "e$.txt"]),
        )

    def test_every_piece_passes_the_plain_language_lint(self):
        for text in (
            unsaved.WHERE,
            unsaved.COMPUTER_MADE_ONE,
            unsaved.COMPUTER_MADE_MANY,
            unsaved.ONE_OF_YOUR_FILES,
            unsaved.SOME_OF_YOUR_FILES,
            unsaved.ONE_OTHER_FILE,
            unsaved.OTHER_FILES,
        ):
            self.assertEqual([], plain_language.find_banned(text), text)
            self.assertEqual([], plain_language.find_dashes(text), text)
            self.assertEqual([], plain_language.find_banned_person_facing(text), text)


# --- Approving a hand edit, and a prepared change, here ------------------------


class TestApprovingPastClutter(ClutterAssertions, unittest.TestCase):
    def test_a_hand_edit_is_approved_with_finder_files_in_the_base(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            runner = approving.NoRemoteRunner()
            staged_path = approving.a_hand_edit(root, base_id, runner)
            scatter_clutter(root)
            ignore_before = support.read(os.path.join(root, ".gitignore"))

            shown, applied = approving.show_and_approve(root, base_id, staged_path, runner)

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertIn(
                approving.BIGGER_COMPANIES, support.read(os.path.join(root, ICP))
            )
            self.assert_no_clutter_saved(root)
            # An existing base's ignore file is never written without a yes.
            self.assertEqual(ignore_before, support.read(os.path.join(root, ".gitignore")))

    def test_a_prepared_change_is_approved_with_finder_files_in_the_base(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            staged_path = approving.stage(root)
            scatter_clutter(root)

            _shown, applied = approving.show_and_approve(
                root, base_id, staged_path, approving.NoRemoteRunner()
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assert_no_clutter_saved(root)

    def test_a_tracked_finder_file_that_changed_still_stops_it_and_is_named(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            runner = approving.NoRemoteRunner()
            save_a_ds_store(root)
            staged_path = approving.stage(root)

            _shown, applied = approving.show_and_approve(root, base_id, staged_path, runner)

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual(approve_local.CODE_UNSAVED_EDITS, applied.codes[0])
            self.assertEqual(
                [
                    approve_local.UNSAVED_EDITS_NAMED
                    % "They are in a file your computer made on its own."
                ],
                applied.reasons,
            )

    def test_the_refusal_names_the_real_unsaved_files_and_not_the_edit(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            runner = approving.NoRemoteRunner()
            staged_path = approving.a_hand_edit(root, base_id, runner)
            scatter_clutter(root)
            support.write(os.path.join(root, "context", "notes.md"), "# Notes\n\nMine.\n")
            support.write(os.path.join(root, "odd$name.txt"), "mine too\n")

            _shown, applied = approving.show_and_approve(root, base_id, staged_path, runner)

            self.assertEqual(approve_local.STATUS_REFUSED, applied.status)
            self.assertEqual(
                [
                    approve_local.UNSAVED_EDITS_NAMED
                    % "They are in your notes and one other file."
                ],
                applied.reasons,
            )
            self.assertTrue(os.path.isfile(os.path.join(root, "context", "notes.md")))


class TestTheApprovalScriptPastClutter(ClutterAssertions, unittest.TestCase):
    """The same yes, given through the script the skill runs."""

    run_in = approving.TestTheScriptRunsEveryAnswer.run_in
    script = approving.TestTheScriptRunsEveryAnswer.script

    def test_the_script_approves_a_hand_edit_past_finder_files(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            runner = approving.NoRemoteRunner()
            staged_path = approving.a_hand_edit(root, base_id, runner)
            scatter_clutter(root)
            shown = approve_local.show(
                staged_path, root, base_id, runner=runner, now=TODAY
            )

            code = self.run_in(
                root,
                ["--staging", staged_path, "--approve", "--shown", shown.shown_hash],
            )

            self.assertEqual(0, code)
            self.assertEqual(1, len(approving.corrections_in(root)))
            self.assert_no_clutter_saved(root)


# --- The move of the context changes -------------------------------------------


class TestTheMovePastClutter(ClutterAssertions, migration.MigrationCase):
    def test_the_move_runs_with_finder_files_in_the_base(self):
        self.old_layout()
        scatter_clutter(self.root)

        result = changes.migrate(self.root, self.base_id, today=migration.TODAY)

        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertEqual(
            [migration.ENTRY_ONE + ".md"], self.files_in(changes.constants.CHANGES_DIR)
        )
        self.assert_no_clutter_saved(self.root)

    def test_the_look_before_the_move_says_nothing_about_unsaved_work(self):
        self.old_layout()
        scatter_clutter(self.root)
        said = changes.what_would_happen(
            self.root, self.base_id, today=migration.TODAY
        )
        self.assertTrue(said.startswith("This would update one of"), said)
        self.assertEqual(
            changes.OFFER_NOW,
            changes.what_to_offer(self.root, self.base_id, today=migration.TODAY),
        )

    def test_a_tracked_finder_file_that_changed_still_stops_the_move(self):
        self.old_layout()
        save_a_ds_store(self.root)

        result = changes.migrate(self.root, self.base_id, today=migration.TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertEqual(
            changes.UNSAVED_EDITS_NAMED
            % "They are in a file your computer made on its own.",
            result.sentence,
        )

    def test_the_refusal_names_the_persons_file(self):
        self.old_layout()
        scatter_clutter(self.root)
        support.write(
            os.path.join(self.root, "context", "strategy", "positioning.md"), "half\n"
        )

        result = changes.migrate(self.root, self.base_id, today=migration.TODAY)

        self.assertEqual(
            changes.UNSAVED_EDITS_NAMED % "They are in your positioning.",
            result.sentence,
        )


class TestTheMovesRecoveryPastClutter(ClutterAssertions, migration.MigrationCase):
    """The recovery of a stopped move reads unsaved work through the same look."""

    def test_clutter_is_nobodys_words_when_a_stopped_move_is_finished(self):
        scatter_clutter(self.root)
        self.assertIsNone(
            changes._theirs_before_finishing(self.root, {"paths": []}, GitRunner())
        )
        self.assertIsNone(
            changes._anything_left_over(
                self.root, {"paths": [{"path": "context/strategy/positioning.md"}]}, GitRunner()
            )
        )

    def test_a_persons_file_is_theirs_and_named_plainly(self):
        scatter_clutter(self.root)
        support.write(os.path.join(self.root, "odd$name.md"), "mine\n")
        found = changes._theirs_before_finishing(self.root, {"paths": []}, GitRunner())
        self.assertEqual(changes.THEIR_WORDS % "one of your files", found)
        self.assertNotIn("odd$name", found)

    def test_a_tracked_finder_file_that_changed_is_still_theirs(self):
        save_a_ds_store(self.root)
        found = changes._theirs_before_finishing(self.root, {"paths": []}, GitRunner())
        self.assertEqual(
            changes.THEIR_WORDS % "a file your computer made on its own", found
        )


# --- The review, and the update at the start of a session -----------------------


class TestTheReviewPastClutter(ClutterAssertions, unittest.TestCase):
    def behind(self, sandbox):
        return checking.TestTheBaseHasToBeReady._behind(self, sandbox)

    def test_the_review_brings_the_base_up_to_date_past_finder_files(self):
        with support.Sandbox() as sandbox:
            base = self.behind(sandbox)
            scatter_clutter(base.root)

            result = checking.run_check(base)

            self.assertEqual(stale_check.STATUS_DONE, result.status, result.lines())
            self.assertIn(stale_check.CODE_BROUGHT_UP_TO_DATE, result.codes)
            self.assert_no_clutter_saved(base.root)

    def test_the_refusal_names_the_unsaved_document(self):
        with support.Sandbox() as sandbox:
            base = self.behind(sandbox)
            scatter_clutter(base.root)
            base.write(ICP, checking.context_text("icp", body="Something I typed."))

            result = checking.run_check(base)

            self.assertTrue(result.stopped)
            self.assertEqual(
                [stale_check.UNSAVED_EDITS_NAMED % "They are in your customer profile."],
                result.lines(),
            )


class TestTheSessionStartPastClutter(
    support.PastTheFirstBackupReview, starting.SessionStartHelpers
):
    def test_the_update_runs_with_finder_files_in_the_base(self):
        root, _base_id = self.joined_base()
        self.add_files(root)
        other = self.working_copy(root)
        support.commit(
            other,
            "context/notes/note.md",
            ["---", "kind: note", "owner: " + starting.OWNER, "---", "", "words"],
            "a note",
        )
        support.git(["push", "-q", "origin", "main"], cwd=other)
        scatter_clutter(root)

        result = self.run_hook(root)

        self.assertNotEqual(session_start.DIRTY_TREE, (result or {}).get("systemMessage"))
        self.assertTrue(os.path.isfile(os.path.join(root, "context", "notes", "note.md")))
        self.assertEqual(list(CLUTTER), clutter_on_disk(root))
        self.assertEqual(
            [], [name for name in tracked(root) + staged(root) if unsaved.is_clutter(name)]
        )

    def test_a_persons_unsaved_file_still_stops_it(self):
        root, _base_id = self.joined_base()
        self.add_files(root)
        scatter_clutter(root)
        support.write(os.path.join(root, "context", "notes", "scratch.md"), "hello\n")
        self.assertEqual(
            session_start.DIRTY_TREE, self.run_hook(root)["systemMessage"]
        )


# --- Writes during setup, and recording an answer ------------------------------


class TestWritesPastClutter(ClutterAssertions, unittest.TestCase):
    def test_setup_and_the_answers_write_past_finder_files(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            scatter_clutter(root)
            review.ready_to_write(root, GitRunner())

            # A setup step that writes and saves a document, past the clutter.
            done = review.skip(
                drafting.STEP_POSITIONING,
                root,
                base_id=base_id,
                owner_email=approving.OWNER,
                runner=GitRunner(),
            )

            self.assertIn(drafting.POSITIONING_PATH, tracked(root))
            self.assertEqual(drafting.POSITIONING_PATH, done.path)
            self.assert_no_clutter_saved(root)

    def test_setup_still_refuses_a_persons_unsaved_file(self):
        with support.Sandbox() as sandbox:
            root, _base_id = approving.local_base(sandbox)
            support.write(os.path.join(root, "context", "notes.md"), "mine\n")
            with self.assertRaises(ReviewError):
                review.ready_to_write(root, GitRunner())

    def test_a_yes_on_a_base_with_no_shared_copy_is_recorded_past_finder_files(self):
        with support.Sandbox() as sandbox:
            base = checking.BaseFixture(sandbox, remote=False)
            base.add_entry(push=False)
            scatter_clutter(base.root)
            question = confirming.ask(base)

            result = confirming.answer(base, question, "yes")

            self.assertEqual(confirm.STATUS_RECORDED, result.status, result.reasons)
            self.assert_no_clutter_saved(base.root)

    def test_it_already_reflects_this_names_the_unsaved_file(self):
        with support.Sandbox() as sandbox:
            base = checking.BaseFixture(sandbox, remote=False)
            base.add_entry(push=False)
            scatter_clutter(base.root)
            support.write(os.path.join(base.root, "notes.txt"), "mine\n")

            result = confirm.against_change(
                base.root, base.base_id, ICP, checking.ENTRY, runner=GitRunner()
            )

            self.assertEqual([confirm.CODE_UNSAVED_EDITS], result.codes)
            self.assertEqual(
                [
                    confirm.UNSAVED_EDITS_HERE_NAMED
                    % ("your customer profile", "They are in notes.txt.")
                ],
                result.reasons,
            )

    def test_a_folder_holding_only_clutter_holds_nothing_of_the_persons(self):
        with support.Sandbox() as sandbox:
            folder = os.path.join(sandbox.path, "material")
            for name in ("Thumbs.db", "desktop.ini", "Icon\r", ".DS_Store"):
                support.write(os.path.join(folder, name), "x\n")
            self.assertFalse(location._holds_content(folder))
            support.write(os.path.join(folder, "deck.md"), "mine\n")
            self.assertTrue(location._holds_content(folder))


# --- A new base ignores clutter from the start ----------------------------------


class TestANewBaseIgnoresClutter(unittest.TestCase):
    TEMPLATES = (
        os.path.join(support.REPO_ROOT, "templates", "company-base"),
        os.path.join(support.PLUGIN_DIR, "templates", "company-base"),
    )

    def test_both_templates_list_every_kind_of_clutter(self):
        for template in self.TEMPLATES:
            lines = support.read(os.path.join(template, ".gitignore")).splitlines()
            for wanted in unsaved.IGNORE_LINES:
                self.assertIn(wanted, lines, template)

    def test_the_ignore_lines_hide_every_kind_of_clutter_and_nothing_else(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "fresh")
            os.makedirs(root)
            support.git(["init", "-q", "-b", "main"], cwd=root)
            shutil.copyfile(
                os.path.join(self.TEMPLATES[1], ".gitignore"),
                os.path.join(root, ".gitignore"),
            )
            scatter_clutter(root)
            for name in ("Icon", "Icons", "notes.md"):
                support.write(os.path.join(root, name), "mine\n")
            finished = support.git(
                ["status", "--porcelain", "-z", "--untracked-files=all"], cwd=root
            )
            listed = sorted(
                field[3:]
                for field in finished.stdout.decode("utf-8").split("\0")
                if field
            )
            self.assertEqual([".gitignore", "Icon", "Icons", "notes.md"], listed)

    def test_a_template_copy_never_carries_clutter_into_a_new_base(self):
        with support.Sandbox() as sandbox:
            template = os.path.join(sandbox.path, "template")
            shutil.copytree(self.TEMPLATES[1], template)
            support.write(os.path.join(template, ".DS_Store"), "x\n")
            support.write(os.path.join(template, "context", "._map.md"), "x\n")
            support.write(os.path.join(template, ".Trashes", "501", "gone.md"), "x\n")
            destination = os.path.join(sandbox.path, "made")

            create_base._copy_template(template, destination, "owner@example.com")

            self.assertFalse(os.path.exists(os.path.join(destination, ".DS_Store")))
            self.assertFalse(
                os.path.exists(os.path.join(destination, "context", "._map.md"))
            )
            self.assertTrue(os.path.isfile(os.path.join(destination, ".gitignore")))
            self.assertFalse(os.path.exists(os.path.join(destination, ".Trashes")))


# --- What the skills say, for the rest of the live check -------------------------


class TestTheSkillsRelayRulesForTheLaterSteps(unittest.TestCase):
    """Four things the assistant did in steps 3 to 5 that steps 6 to 10 would hit.

    It said it needed a confirmation about other seats that the script never
    asked for, said a check before use had found nothing, asked Brandon to find
    the base and run a command himself, and explained that GTM Base keeps its
    commands away from its own records. Each skill now says never to.
    """

    SKILLS = ("stale-check", "propose-change", "confirm")

    def text_of(self, skill):
        text = support.read(os.path.join(support.PLUGIN_DIR, "skills", skill, "SKILL.md"))
        # Read as one line of words, because a phrase can wrap.
        return " ".join(text.lower().split())

    def test_each_skill_carries_all_four_rules(self):
        for skill in self.SKILLS:
            text = self.text_of(skill)
            for phrase in (
                "never send the person to a command line",
                "never ask them to find the base",
                "never describe how gtm base works inside",
                "finds nothing wrong, say nothing about the check",
                "unless a script's own sentence asks for it",
                "an older version reads an updated base as empty",
            ):
                with self.subTest(skill=skill, phrase=phrase):
                    self.assertIn(phrase, text)
            plain_language.assert_plain(
                self, os.path.join(support.PLUGIN_DIR, "skills", skill, "SKILL.md")
            )
            plain_language.assert_standard(
                self, os.path.join(support.PLUGIN_DIR, "skills", skill, "SKILL.md")
            )

    def test_the_update_never_asks_about_other_seats_on_its_own(self):
        text = self.text_of("stale-check")
        self.assertNotIn("the only way to know is to ask", text)
        self.assertIn(
            "the script's own sentence asked whether everyone who opens this base",
            text,
        )
        self.assertIn("never raise it, pass it, or say you left it out", text)


if __name__ == "__main__":
    unittest.main()
