"""Unit 4 of the join plan: the screen, and writing an approved draft into the base.

Every scenario that touches a base builds real repositories in temporary
folders, with a temporary home folder and a temporary seat folder, so nothing
here can reach the machine's own identity or the person's real seat folder.

The order the scenarios run in is the order setup runs them: the profile builds
the base, the decision entry lands next, and the positioning last.
"""

import datetime
import io
import os
import subprocess
import unittest

import support

from gtmbase import (
    base_reader,
    constants,
    drafting,
    formats,
    ids,
    review,
    stale,
)
from gtmbase.errors import DraftError, PathError, ReviewError
from gtmbase.gitcmd import GitRunner

DRAFTS = os.path.join(support.FIXTURES_DIR, "drafts")
TODAY = datetime.date(2026, 9, 6)
NOW = datetime.datetime(2026, 9, 6, 9, 15, 0)
EMAIL = "dana@acme.test"
ICP = drafting.ICP_PATH
POSITIONING = drafting.POSITIONING_PATH
PLUGIN_ROOT = support.PLUGIN_DIR

# The long dashes, written as escapes, so no file in this repository holds one.
EM_DASH = "\u2014"


def captured(name):
    with io.open(os.path.join(DRAFTS, name), encoding="utf-8") as handle:
        return handle.read()


def draft(step, name):
    return drafting.parse(step, captured(name))


def runner():
    return GitRunner()


def write_gitconfig(text=None):
    path = os.path.join(os.environ["HOME"], ".gitconfig")
    support.write(path, text or "[user]\n\temail = %s\n\tname = Dana\n" % EMAIL)
    return path


def content_folder(name="marketing"):
    folder = os.path.join(os.environ["HOME"], name)
    support.write(os.path.join(folder, "positioning.md"), "# Positioning\n")
    return folder


def files_in_head(root):
    finished = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
    )
    return sorted(
        line.strip()
        for line in finished.stdout.decode("utf-8").split("\n")
        if line.strip()
    )


def confirmations_of(root, relative):
    path = os.path.join(
        root, constants.CONFIRMATIONS_DIR, relative.replace("/", "--")
    )
    if not os.path.isfile(path):
        return []
    lines, _bad = formats.parse_confirmations_file(support.read(path))
    return lines


class Setup(object):
    """The three steps of a real setup run, in order, in a sandbox."""

    def __init__(self, sandbox, run=None):
        self.sandbox = sandbox
        self.run = run or ids.run_id(TODAY)
        self.git = runner()
        self.root = None
        self.base_id = None

    def profile(self, name="icp.md"):
        result = review.approve(
            draft(drafting.STEP_ICP, name),
            None,
            None,
            self.run,
            PLUGIN_ROOT,
            runner=self.git,
            now=NOW,
            first_file=True,
            parent=content_folder(),
        )
        self.root = result.root
        self.base_id = result.base_id
        return result

    def decision(self, name="ledger-entry.md"):
        return review.approve(
            draft(drafting.STEP_LEDGER, name),
            self.root,
            self.base_id,
            self.run,
            PLUGIN_ROOT,
            runner=self.git,
            now=NOW,
        )

    def positioning(self, name="positioning.md"):
        return review.approve(
            draft(drafting.STEP_POSITIONING, name),
            self.root,
            self.base_id,
            self.run,
            PLUGIN_ROOT,
            runner=self.git,
            now=NOW,
        )


# --- The screen --------------------------------------------------------------


class TestTheScreenFindsWhatMustNotBeWrittenDown(unittest.TestCase):
    """The classes come back. The values never do."""

    def test_a_character_a_reader_would_never_see_is_found(self):
        found = review.screen(draft(drafting.STEP_ICP, "icp-hidden-character.md"), EMAIL)
        self.assertEqual(["hidden-content"], found)

    def test_a_prospects_address_and_phone_number_are_both_found(self):
        found = review.screen(draft(drafting.STEP_ICP, "icp-contact-details.md"), EMAIL)
        self.assertEqual(["email", "phone"], sorted(found))

    def test_something_shaped_like_a_key_is_found(self):
        hostile = captured("icp.md").replace(
            "A spreadsheet nobody updates",
            "Their key is AKIA" + "A" * 16 + " in the notes",
        )
        found = review.screen(drafting.parse(drafting.STEP_ICP, hostile), EMAIL)
        self.assertEqual(["key-shape"], found)

    def test_the_value_that_matched_never_comes_back(self):
        found = review.screen(draft(drafting.STEP_ICP, "icp-contact-details.md"), EMAIL)
        for code in found:
            self.assertNotIn("priya", code)
            self.assertNotIn("@", code)
            self.assertNotIn("415", code)

    def test_the_owner_line_is_exempt(self):
        clean = draft(drafting.STEP_ICP, "icp.md")
        self.assertEqual([], review.screen(clean, "owner@example.com"))
        # And still exempt when the address on the line is somebody else's,
        # because this plugin writes the owner's own address there next.
        self.assertEqual([], review.screen(clean, "dana@acme.test"))

    def test_the_decision_entry_may_name_the_owner_as_the_person_who_decided(self):
        entry = draft(drafting.STEP_LEDGER, "ledger-entry.md")
        self.assertEqual([], review.screen(entry, "owner@example.com"))

    def test_an_address_in_the_body_is_still_found_when_it_is_the_owners_own(self):
        hostile = captured("icp.md").replace(
            "A spreadsheet nobody updates", "Write to owner@example.com about it"
        )
        found = review.screen(drafting.parse(drafting.STEP_ICP, hostile), "owner@example.com")
        self.assertEqual(["email"], found)


class TestTheScreenExemptsOnlyASettingsBlockItWasShown(unittest.TestCase):
    """join-02: any text opening with three dashes used to buy an exemption."""

    def test_a_note_that_merely_starts_with_three_dashes_gets_nothing(self):
        note = "---\nreach me at priya@example.test\n---\n"

        self.assertEqual(["email"], review.screen(note, EMAIL))

    def test_a_note_holding_a_hidden_comment_is_still_found(self):
        note = "---\nowner: someone@example.test\n---\n"

        self.assertEqual(["email"], review.screen(note, EMAIL))

    def test_a_parsed_draft_keeps_the_exemption_on_its_own_settings(self):
        clean = draft(drafting.STEP_ICP, "icp.md")

        self.assertEqual([], review.screen(clean, EMAIL))

    def test_named_settings_lines_are_the_only_ones_ever_let_through(self):
        clean = draft(drafting.STEP_ICP, "icp.md")

        self.assertEqual(["email"], review.screen(clean, EMAIL, frontmatter_lines=[]))


class TestStampingTheOwnerOnADraft(unittest.TestCase):
    """The base's own address goes on, whatever the draft said."""

    def test_the_owner_setting_is_replaced(self):
        stamped = review.stamp_owner(draft(drafting.STEP_ICP, "icp.md"), EMAIL)
        self.assertEqual(EMAIL, stamped.fields["owner"])
        self.assertIn("owner: " + EMAIL, stamped.text)

    def test_the_decision_entry_is_stamped_on_who_decided(self):
        stamped = review.stamp_owner(draft(drafting.STEP_LEDGER, "ledger-entry.md"), EMAIL)
        self.assertEqual(EMAIL, stamped.fields["decided_by"])

    def test_a_handle_line_is_taken_off_rather_than_left_as_it_was(self):
        """join-04: the handle line was exempt from the screen and never written.

        Setting a base up never records a handle for anybody, so whatever a
        draft put on that line would have gone into the base unchecked and
        unread. It comes off the document instead.
        """
        entry = drafting.parse(
            drafting.STEP_LEDGER,
            captured("ledger-entry.md").replace(
                "origin: join", "origin: join\nowner_handle: @somebody"
            ),
        )

        stamped = review.stamp_owner(entry, EMAIL)

        self.assertNotIn("owner_handle", stamped.fields)
        self.assertNotIn("@somebody", stamped.text)

    def test_every_settings_line_the_screen_lets_through_is_written_over(self):
        entry = drafting.parse(drafting.STEP_LEDGER, captured("ledger-entry.md"))

        stamped = review.stamp_owner(entry, EMAIL)

        for key in review._OWNER_KEYS:
            if key in stamped.fields:
                self.assertEqual(EMAIL, stamped.fields[key], key)


class TestTheFilesADecisionSaysItAffects(unittest.TestCase):
    """Every affected path is inside the context folder or it is refused."""

    def test_a_path_inside_the_context_folder_is_accepted(self):
        entry = draft(drafting.STEP_LEDGER, "ledger-entry.md")
        self.assertEqual([ICP], review.canonical_affects(entry))

    def test_a_path_climbing_out_of_the_base_is_refused(self):
        hostile = captured("ledger-entry.md").replace(
            "affects: [context/strategy/icp.md]", "affects: [../secrets.md]"
        )
        entry = drafting.parse(drafting.STEP_LEDGER, hostile)
        with self.assertRaises(PathError):
            review.canonical_affects(entry)

    def test_a_path_from_the_root_of_the_machine_is_refused(self):
        hostile = captured("ledger-entry.md").replace(
            "affects: [context/strategy/icp.md]", "affects: [/etc/passwd]"
        )
        entry = drafting.parse(drafting.STEP_LEDGER, hostile)
        with self.assertRaises(PathError):
            review.canonical_affects(entry)


class TestReadingAPersonsOwnRewriteBack(unittest.TestCase):
    """An edit is a draft, and it goes through everything a draft goes through."""

    def test_a_clean_rewrite_comes_back_with_nothing_against_it(self):
        original = draft(drafting.STEP_ICP, "icp.md")
        rewritten = captured("icp.md").replace(
            "twenty to two hundred people", "fifty to five hundred people"
        )
        fresh = review.edit(original, rewritten, "owner@example.com")
        self.assertEqual([], fresh.codes)
        self.assertIn("fifty to five hundred people", fresh.body)

    def test_a_rewrite_carrying_contact_details_comes_back_with_the_classes(self):
        original = draft(drafting.STEP_ICP, "icp.md")
        fresh = review.edit(
            original, captured("icp-contact-details.md"), "owner@example.com"
        )
        self.assertEqual(["email", "phone"], sorted(fresh.codes))

    def test_a_rewrite_with_a_long_dash_is_refused_outright(self):
        original = draft(drafting.STEP_ICP, "icp.md")
        hostile = captured("icp.md").replace(
            "A spreadsheet nobody updates", "A spreadsheet" + EM_DASH + " nobody updates"
        )
        with self.assertRaises(Exception) as caught:
            review.edit(original, hostile, "owner@example.com")
        self.assertEqual("em-dash", caught.exception.code)


class TestAskingWhatIsWrongWritesNothing(unittest.TestCase):
    """The one answer that changes nothing on disk."""

    def test_nothing_is_written_anywhere_in_the_base(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            before = support.head_of(setup.root)
            corrections = os.path.join(setup.root, constants.CORRECTIONS_DIR)
            listed_before = sorted(os.listdir(corrections))

            note = review.what_is_wrong(
                draft(drafting.STEP_ICP, "icp.md"), "The headcount is too low."
            )

            self.assertIn("The headcount is too low.", note)
            self.assertEqual(before, support.head_of(setup.root))
            self.assertEqual("", support.status_of(setup.root))
            self.assertEqual(listed_before, sorted(os.listdir(corrections)))


# --- Writing an approved draft into the base ---------------------------------


class TestTheFirstApprovedDraftBuildsTheBase(unittest.TestCase):
    """One yes, and there is a base with the profile and the record of the yes."""

    def test_the_profile_lands_with_its_owner_and_one_line_dated_today(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)

            result = setup.profile()

            self.assertEqual(ICP, result.path)
            self.assertTrue(os.path.isdir(result.root))
            block, _body = formats.split_document(
                support.read(os.path.join(result.root, ICP))
            )
            self.assertEqual(EMAIL, formats.parse_frontmatter(block)["owner"])

            lines = confirmations_of(result.root, ICP)
            self.assertEqual(1, len(lines))
            self.assertEqual(TODAY.isoformat(), lines[0].date)
            self.assertEqual("drafted", lines[0].trigger)
            self.assertEqual(setup.run, lines[0].run)

            self.assertIn(ICP, files_in_head(result.root))
            self.assertIn(
                constants.CONFIRMATIONS_DIR + "/" + ICP.replace("/", "--"),
                files_in_head(result.root),
            )

    def test_the_dates_of_the_sources_sit_in_the_file(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            result = setup.profile()

            block, _body = formats.split_document(
                support.read(os.path.join(result.root, ICP))
            )
            named = formats.parse_frontmatter(block)["sources"]
            self.assertIn("acme-icp.md (2026-08-14)", named)
            self.assertEqual(
                "2026-08-14", base_reader.newest_date_in(named)
            )


class TestTheDecisionEntryLandsAsOnePieceOfWork(unittest.TestCase):
    """The entry is named here, not by the model, and it says where it came from."""

    def test_the_entry_carries_this_plugins_own_identifiers(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()

            result = setup.decision()

            self.assertEqual(
                constants.DECISIONS_DIR + "/" + review.entry_id() + ".md", result.path
            )
            entry = formats.LedgerEntry.parse(
                support.read(os.path.join(setup.root, result.path))
            )
            entry.validate(today=TODAY)
            self.assertEqual("join", entry.origin)
            self.assertEqual(setup.run, entry.run_id)
            self.assertEqual(EMAIL, entry.decided_by)
            self.assertEqual([ICP], entry.affects)
            self.assertEqual("open", entry.status)

    def test_the_entry_is_the_only_thing_in_that_piece_of_work(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()

            result = setup.decision()

            self.assertEqual([result.path], files_in_head(setup.root))
            self.assertEqual("", support.status_of(setup.root))

    def test_no_line_says_the_owner_confirmed_a_file_outside_the_context_folder(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()

            result = setup.decision()

            self.assertEqual([review.CODE_NO_DRAFTED_LINE], result.codes)
            self.assertEqual([], confirmations_of(setup.root, result.path))


class TestThePositioningLandsWithItsOwnLine(unittest.TestCase):
    """The last file of the run, and the record of the yes beside it."""

    def test_the_file_and_the_line_are_saved_together(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            setup.decision()

            result = setup.positioning()

            self.assertEqual(POSITIONING, result.path)
            self.assertEqual(
                sorted(
                    [
                        POSITIONING,
                        constants.CONFIRMATIONS_DIR
                        + "/"
                        + POSITIONING.replace("/", "--"),
                    ]
                ),
                files_in_head(setup.root),
            )
            lines = confirmations_of(setup.root, POSITIONING)
            self.assertEqual(1, len(lines))
            self.assertEqual(TODAY.isoformat(), lines[0].date)
            self.assertEqual(setup.run, lines[0].run)

    def test_a_whole_run_leaves_three_files_one_entry_and_two_lines(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            entry = setup.decision()
            setup.positioning()

            for relative in (ICP, POSITIONING, entry.path):
                self.assertTrue(
                    os.path.isfile(os.path.join(setup.root, relative)), relative
                )
            self.assertEqual(1, len(confirmations_of(setup.root, ICP)))
            self.assertEqual(1, len(confirmations_of(setup.root, POSITIONING)))
            self.assertEqual("", support.status_of(setup.root))


class TestTheStaleLibraryCountsEachFileAsConfirmed(unittest.TestCase):
    """What setup wrote is what the stale rules read back."""

    def test_both_context_files_count_as_confirmed_for_their_owner(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            setup.decision()
            setup.positioning()

            inputs = base_reader.read_base(setup.root, setup.base_id, today=TODAY)
            confirmed = {
                record.line.file
                for record in inputs.confirmations
                if record.line.trigger == "drafted"
                and record.line.date == TODAY.isoformat()
                and record.author_email == EMAIL
            }
            self.assertEqual({ICP, POSITIONING}, confirmed)

    def test_the_positioning_and_the_profile_are_both_settled_by_the_same_run(self):
        """What the stale rules make of a run, exactly as they are today.

        The positioning has nothing pointing at it, so its own line settles it.
        The profile is the file the decision affects, and the decision and the
        profile were put in front of the owner together, in one run, which is
        what the run identifier on both of them records. This run wrote the
        entry today about a decision made in August, and the profile is settled
        against it all the same, because a base is never flagged as behind
        itself.
        """
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            setup.decision()
            setup.positioning()

            inputs = base_reader.read_base(setup.root, setup.base_id, today=TODAY)
            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
                owner_email=EMAIL,
            )
            reasons = {flag.path: flag.reason for flag in report.file_flags}
            self.assertNotIn(POSITIONING, reasons)
            self.assertNotIn(ICP, reasons)


class TestASecondLineForTheSameFileIsRefused(unittest.TestCase):
    """One drafted line per file, ever."""

    def test_the_second_one_is_refused_and_nothing_is_written(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            base_root, base_id = setup.root, setup.base_id
            os.remove(os.path.join(base_root, ICP))
            support.git(["add", "-A"], cwd=base_root)
            support.git(["commit", "-q", "-m", "take it away"], cwd=base_root)
            before = support.head_of(base_root)

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    draft(drafting.STEP_ICP, "icp.md"),
                    base_root,
                    base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual("already-drafted", caught.exception.code)
            self.assertEqual(before, support.head_of(base_root))


class TestSetupNeverEditsAFileTheBaseAlreadyHolds(unittest.TestCase):
    """Setting up writes files that were not there, and nothing else."""

    def test_a_file_already_in_the_base_is_refused(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            before = support.head_of(setup.root)
            held = support.read(os.path.join(setup.root, ICP))

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    draft(drafting.STEP_ICP, "icp.md"),
                    setup.root,
                    setup.base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual(review.CODE_FILE_EXISTS, caught.exception.code)
            self.assertEqual(before, support.head_of(setup.root))
            self.assertEqual(held, support.read(os.path.join(setup.root, ICP)))


class TestAFolderWithSomethingHalfDoneInItIsLeftAlone(unittest.TestCase):
    """Nothing is written while the person has unsaved work in the base."""

    def test_an_unsaved_edit_stops_the_next_file(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            support.write(
                os.path.join(setup.root, ICP),
                support.read(os.path.join(setup.root, ICP)) + "\nA hand edit.\n",
            )

            with self.assertRaises(ReviewError) as caught:
                setup.decision()

            self.assertEqual(review.CODE_UNSAVED_EDITS, caught.exception.code)
            self.assertFalse(
                os.path.isdir(
                    os.path.join(setup.root, constants.DECISIONS_DIR, "pending.md")
                )
            )

    def test_a_line_of_work_that_is_not_the_shared_one_stops_the_next_file(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            support.git(["checkout", "-q", "-b", "elsewhere"], cwd=setup.root)

            with self.assertRaises(ReviewError) as caught:
                setup.decision()

            self.assertEqual(review.CODE_NOT_DEFAULT_BRANCH, caught.exception.code)


# --- Security ----------------------------------------------------------------


class TestNothingScreenedOutIsEverWritten(unittest.TestCase):
    """A draft that fails the screen never reaches the disk."""

    def test_a_hidden_character_stops_the_first_file_before_a_base_exists(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            parent = content_folder()

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    draft(drafting.STEP_ICP, "icp-hidden-character.md"),
                    None,
                    None,
                    ids.run_id(TODAY),
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                    first_file=True,
                    parent=parent,
                )

            self.assertEqual(review.CODE_SCREENED, caught.exception.code)
            self.assertEqual(["hidden-content"], caught.exception.codes)
            self.assertFalse(
                os.path.isdir(os.path.join(parent, constants.BASE_FOLDER_NAME))
            )

    def test_contact_details_stop_a_later_file_and_the_base_is_untouched(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            before = support.head_of(setup.root)

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    drafting.parse(
                        drafting.STEP_POSITIONING,
                        captured("positioning.md").replace(
                            '"every prospect asked for the monthly number anyway"',
                            "Reach Priya on (415) 555 0147",
                        ),
                    ),
                    setup.root,
                    setup.base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual(review.CODE_SCREENED, caught.exception.code)
            self.assertEqual(["phone"], caught.exception.codes)
            self.assertFalse(os.path.isfile(os.path.join(setup.root, POSITIONING)))
            self.assertEqual(before, support.head_of(setup.root))

    def test_an_answer_that_cannot_be_read_back_leaves_the_base_as_it_was(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            before = support.head_of(setup.root)
            listed = sorted(os.listdir(setup.root))

            with self.assertRaises(DraftError) as caught:
                drafting.parse(
                    drafting.STEP_POSITIONING,
                    "Here you go.\n\n```markdown\nno settings block at all\n```\n",
                )

            self.assertEqual(drafting.STEP_POSITIONING, caught.exception.step)
            self.assertEqual("no-frontmatter", caught.exception.code)
            self.assertEqual(before, support.head_of(setup.root))
            self.assertEqual("", support.status_of(setup.root))
            self.assertEqual(listed, sorted(os.listdir(setup.root)))
            self.assertFalse(os.path.isfile(os.path.join(setup.root, POSITIONING)))

    def test_a_decision_affecting_a_path_outside_the_base_is_refused(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            before = support.head_of(setup.root)
            hostile = drafting.parse(
                drafting.STEP_LEDGER,
                captured("ledger-entry.md").replace(
                    "affects: [context/strategy/icp.md]", "affects: [../secrets.md]"
                ),
            )

            with self.assertRaises(ReviewError):
                review.approve(
                    hostile,
                    setup.root,
                    setup.base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual(before, support.head_of(setup.root))
            self.assertEqual("", support.status_of(setup.root))

    def test_a_bad_affected_path_comes_back_as_a_refusal_carrying_its_code(self):
        """The residual on approve: a path failure is a refusal, not a crash.

        It used to leave `approve` as a `PathError`, which the script has no
        answer for, so the person heard the sentence that says something went
        wrong instead of the sentence that says what was refused.
        """
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            hostile = drafting.parse(
                drafting.STEP_LEDGER,
                captured("ledger-entry.md").replace(
                    "affects: [context/strategy/icp.md]", "affects: [../secrets.md]"
                ),
            )

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    hostile,
                    setup.root,
                    setup.base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual("climbing-path", caught.exception.code)
            self.assertNotIsInstance(caught.exception, PathError)

    def test_an_approve_with_no_owner_address_anywhere_is_refused(self):
        """The residual on approve: never write an empty owner line."""
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            support.git(
                ["config", "--local", "--unset", "user.email"], cwd=setup.root
            )
            os.remove(os.path.join(os.environ["HOME"], ".gitconfig"))
            draft = drafting.parse(
                drafting.STEP_POSITIONING, captured("positioning.md")
            )

            with self.assertRaises(ReviewError) as caught:
                review.approve(
                    draft,
                    setup.root,
                    setup.base_id,
                    setup.run,
                    PLUGIN_ROOT,
                    runner=runner(),
                    now=NOW,
                )

            self.assertEqual(review.CODE_OWNER_MISSING, caught.exception.code)
            self.assertFalse(
                os.path.isfile(os.path.join(setup.root, POSITIONING))
            )


# --- Skipping a file ---------------------------------------------------------


class TestSkippingAFileLeavesTheBaseUnfinished(unittest.TestCase):
    """A skip is written down, and the next session offers to finish."""

    def test_the_file_says_skipped_and_no_line_says_anybody_approved_it(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()

            result = review.skip(
                drafting.STEP_POSITIONING,
                setup.root,
                setup.base_id,
                runner=runner(),
                now=NOW,
            )

            self.assertEqual(POSITIONING, result.path)
            block, body = formats.split_document(
                support.read(os.path.join(setup.root, POSITIONING))
            )
            fields = formats.parse_frontmatter(block)
            self.assertEqual("skipped", fields["status"])
            self.assertEqual(EMAIL, fields["owner"])
            self.assertEqual([], fields["sources"])
            self.assertEqual("# Positioning", body.strip())
            self.assertEqual([], confirmations_of(setup.root, POSITIONING))
            self.assertEqual([POSITIONING], files_in_head(setup.root))

    def test_the_base_still_counts_as_missing_that_file(self):
        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            review.skip(
                drafting.STEP_POSITIONING,
                setup.root,
                setup.base_id,
                runner=runner(),
                now=NOW,
            )

            files = {
                info.path: info for info in base_reader.context_files(setup.root)
            }
            self.assertEqual([POSITIONING], base_reader.missing_required(files))
            self.assertTrue(files[POSITIONING].skipped)


class TestTheSessionStartOffersToFinishAfterASkip(unittest.TestCase):
    """The way back in is the sentence the session start already says."""

    def test_the_next_session_says_the_base_is_missing_that_file(self):
        from gtmbase import session_start

        with support.Sandbox() as sandbox:
            write_gitconfig()
            setup = Setup(sandbox)
            setup.profile()
            review.skip(
                drafting.STEP_POSITIONING,
                setup.root,
                setup.base_id,
                runner=runner(),
                now=NOW,
            )

            said = session_start.run(
                {"session_id": "s1", "source": "startup", "cwd": setup.root},
                now=datetime.datetime(2026, 9, 7, 9, 0, 0),
                runner=runner(),
                plugin_root=PLUGIN_ROOT,
                part="context",
            )

            self.assertIsNotNone(said)
            self.assertIn("Setup is not finished", said)
            self.assertIn(POSITIONING, said)
            self.assertIn(constants.RESTART_SENTENCE, said)


if __name__ == "__main__":
    unittest.main()
