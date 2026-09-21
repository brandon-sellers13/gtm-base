"""The third look at release A: what two reviewers found on the second round.

Every scenario here is built from the reviewers' own reproduction scripts, and
each one runs the thing the finding is about rather than a stand-in for it.
Three lessons of that round are built into the shape of these tests. A payload
is shaped the way the real client sends one. A documented command is run, not
only read. And byte for byte means bytes.
"""

import datetime
import os
import subprocess
import sys
import unittest
from unittest import mock

import support

from gtmbase import (
    approve_local,
    compose_proposal,
    constants,
    formats,
    gate,
    ids,
    machine,
    paths,
    state,
    stale_check,
    write_hook,
)

OWNER = "owner@example.com"
TEAMMATE = "teammate@example.com"
ICP = "context/strategy/icp.md"
TODAY = datetime.date(2026, 6, 5)
NOW = datetime.datetime(2026, 6, 5, 12, 30, 0)
HAND_EDIT_SOURCE = "The quarterly review deck, slide four, said so."


def local_base(sandbox, name="local"):
    root = os.path.join(sandbox.path, name)
    base_id = ids.base_id_random()
    support.make_base(root, base_id=base_id)
    support.write(os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n")
    support.write(
        os.path.join(root, constants.ALLOWLIST_PATH),
        "# ours\n%s\n%s\n" % (OWNER, TEAMMATE),
    )
    support.write(os.path.join(root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a local base"], cwd=root)
    machine.append_joined(root=root, base_id=base_id, remote=None)
    state.update_seat(base_id, first_push_reviewed=False, session_id="sess-1")
    return root, base_id


# --- M3: a put-off day beyond the cap ----------------------------------------


class TestAForgedPutOffDayDoesNotRollForward(unittest.TestCase):
    """M3, a regression from the round before this one.

    Bringing a day back to the cap is right when GTM Base writes the day. It
    is wrong when reading a day somebody else wrote, because the cap moves
    with today, so a day in the year nine thousand became today plus the cap
    on every single read and the reminder never came back at all.
    """

    def read_it_on(self, base_id, days_ahead):
        real = datetime.date

        class Later(real):
            @classmethod
            def today(cls):
                return real.today() + datetime.timedelta(days=days_ahead)

        with mock.patch.object(state.datetime, "date", Later):
            return state.load_dismissals(base_id)

    def test_it_is_thrown_away_rather_than_brought_back(self):
        with support.Sandbox():
            base_id = ids.base_id_random()
            state._save_dismissals(
                base_id,
                {"inbox_ids": [], "ledger_behind_dismissed_until": "9999-12-31"},
            )

            for ahead in (0, 45, 400, 4000):
                value, problems = self.read_it_on(base_id, ahead)

                self.assertIsNone(
                    value["ledger_behind_dismissed_until"],
                    "a day nobody may ask for was honoured %d days out" % ahead,
                )
                self.assertIn("bad-value", problems)

    def test_a_day_gtm_base_wrote_is_still_brought_back_when_it_is_written(self):
        with support.Sandbox():
            base_id = ids.base_id_random()
            asked = datetime.date.today() + datetime.timedelta(days=400)

            kept = state.set_ledger_behind_dismissed_until(base_id, asked)

            self.assertEqual(state.furthest_quiet(), kept)
            value, problems = state.load_dismissals(base_id)
            self.assertEqual(kept.isoformat(), value["ledger_behind_dismissed_until"])
            self.assertEqual([], problems)


# --- M5: who owns the document --------------------------------------------


class TestWhoOwnsTheDocumentIsReadFromTheSavedVersion(unittest.TestCase):
    """M5. A hand edit to the owner line made its author the owner."""

    def test_rewriting_the_owner_line_by_hand_does_not_make_you_the_owner(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = support.NoRemoteRunner()
            support.git(["config", "--local", "user.email", TEAMMATE], cwd=root)
            full = os.path.join(root, ICP)
            support.write(
                full,
                support.read(full)
                .replace("owner: %s" % OWNER, "owner: %s" % TEAMMATE)
                .replace("Companies of any size.", "Companies the teammate likes."),
            )
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn(approve_local.CODE_NOT_AN_OWNER, shown.codes)

    def test_the_real_owner_can_still_approve_their_own_hand_edit(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            runner = support.NoRemoteRunner()
            full = os.path.join(root, ICP)
            support.write(
                full,
                support.read(full).replace(
                    "Companies of any size.", "Companies of twenty to two hundred."
                ),
            )
            staged = compose_proposal.stage_local_edit(
                root, base_id, HAND_EDIT_SOURCE, runner=runner, now=TODAY
            )

            shown = approve_local.show(
                staged, root, base_id, runner=runner, now=TODAY
            )

            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

    def test_a_document_that_is_not_saved_yet_is_read_where_it_is(self):
        """A new file has no saved version, so the working one is all there is."""
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            new_one = "context/strategy/positioning.md"
            support.write(
                os.path.join(root, new_one),
                support.ICP_TEXT.replace("kind: icp", "kind: positioning"),
            )

            self.assertEqual(
                [OWNER], approve_local.owners_of(root, new_one)
            )


# --- L2: the drafts of a run that is gone ------------------------------------


class TestTheDraftsAreSweptWhenARunBeginsAndEnds(unittest.TestCase):
    def test_a_new_run_sweeps_the_drafts_of_a_run_that_is_gone(self):
        from gtmbase import join_flow

        with support.Sandbox():
            old = join_flow.new_run()
            folder = join_flow.drafts_dir(old)
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")
            join_flow.clear_scratch(old)
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")

            join_flow.new_run()

            self.assertFalse(os.path.isdir(folder))

    def test_closing_a_run_sweeps_them_too(self):
        from gtmbase import join_flow

        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            old = join_flow.new_run()
            folder = join_flow.drafts_dir(old)
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")
            join_flow.clear_scratch(old)
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")
            current = join_flow.new_run()
            support.write(
                os.path.join(join_flow.drafts_dir(current), "icp-draft.md"), "x\n"
            )
            # The sweep at the start of that run already took the old one, so
            # put it back to prove the closing takes it too.
            support.write(os.path.join(folder, "icp-draft.md"), "a draft\n")

            join_flow.close_run(root, current)

            self.assertFalse(os.path.isdir(folder))


# --- L3: which run or session a words file belongs to ------------------------


class TestAWordsFileSurvivesASecondWindow(unittest.TestCase):
    """L3. They were keyed to the seat's latest session, which moves."""

    SCRIPTS = {
        "confirm": os.path.join(
            support.PLUGIN_DIR, "skills", "confirm", "scripts", "confirm.py"
        ),
        "propose": os.path.join(
            support.PLUGIN_DIR, "skills", "propose-change", "scripts", "propose.py"
        ),
        "approve_local": os.path.join(
            support.PLUGIN_DIR,
            "skills",
            "propose-change",
            "scripts",
            "approve_local.py",
        ),
    }

    def run_script(self, which, arguments, cwd):
        return subprocess.run(
            [sys.executable, self.SCRIPTS[which]] + [str(item) for item in arguments],
            cwd=cwd,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def value_of(self, printed, name):
        for line in printed.split("\n"):
            if line.startswith(name + "="):
                return line[len(name) + 1 :].strip()
        return None

    def test_a_second_window_between_handing_out_and_reading_changes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            for which in ("confirm", "propose", "approve_local"):
                with self.subTest(script=which):
                    handed = self.run_script(
                        which, ["--new-words-file", "reason"], root
                    )
                    self.assertEqual(0, handed.returncode, handed.stderr)
                    path = self.value_of(handed.stdout.decode("utf-8"), "words")
                    self.assertTrue(path)
                    support.write(path, "We moved up market.\n")

                    # Another window opens on the same base.
                    state.update_seat(base_id, session_id="sess-2")

                    from gtmbase import wordsfile

                    self.assertEqual(
                        "We moved up market.",
                        wordsfile.read_words(path, base_id),
                        "the file stopped being readable when a window opened",
                    )


# --- F5: the shared-copy path and the first draft ----------------------------


class TestTheSharedCopyPathRefusesAFirstDraftToo(unittest.TestCase):
    def a_first_draft(self, root):
        entry = formats.ChangeEntry(
            id="stg-" + "a" * 16,
            happened_on="2026-05-01",
            written_on="2026-05-02",
            noted_by=OWNER,
            source="what the owner said",
            affects=[ICP],
            review_by="2026-08-01",
            origin="ledger",
            status="open",
            run_id=None,
            body="Firmographics changed: we stopped selling to small companies.",
        )
        staging = stale_check.build_file_proposal(
            root, entry, constants.CHANGES_DIR + "/" + entry.id + ".md", ICP
        )
        path = os.path.join(
            root, constants.PROPOSALS_PENDING_DIR, staging.staging_id + ".md"
        )
        support.write(path, staging.render())
        return path

    def test_a_retyped_note_is_refused_on_the_shared_copy_path(self):
        with support.Sandbox() as sandbox:
            root, base_id, _remote = support.base_with_a_shared_copy(sandbox)
            staged = self.a_first_draft(root)
            support.write_the_wording_by_hand(
                staged, "Update needed: we stopped selling to small companies"
            )

            result = compose_proposal.propose(
                staged,
                root,
                base_id,
                gh=support.RecordingGh(),
                now=TODAY,
                session_id="sess-1",
            )

            self.assertEqual(compose_proposal.STATUS_REFUSED, result.status)
            self.assertIn(
                compose_proposal.STILL_A_PLACEHOLDER, result.reasons
            )



# --- The final confirmation pass ---------------------------------------------


class TestAFirstDraftCanAlwaysBeFinished(unittest.TestCase):
    """N4. It could be refused by approval and by the only command that clears it.

    Three ways, all of them honest users and no tampering: the marker line
    reading false, a prepared change written before that line existed, and a
    name left behind on this seat's record by a change that was dropped.
    """

    SCRIPT = os.path.join(
        support.PLUGIN_DIR, "skills", "propose-change", "scripts", "approve_local.py"
    )

    def a_draft(self, sandbox):
        import test_first_draft_marker as first_draft

        root, base_id = first_draft.local_base(sandbox)
        staged = first_draft.a_first_draft(root, body=first_draft.NAMES_THE_PART)
        return root, base_id, staged

    def wording(self, root, base_id, staged):
        part = compose_proposal.parts_of(
            root, compose_proposal.load_staging(staged)
        )[0]
        return compose_proposal.write_the_wording(
            root,
            staged,
            "We sell to companies of fifty people and up.",
            part=part,
            base_id=base_id,
        )

    def test_the_marker_line_reading_false_is_not_the_last_word(self):
        with support.Sandbox() as sandbox:
            root, base_id, staged = self.a_draft(sandbox)
            support.write(
                staged,
                support.read(staged).replace(
                    "first_draft: true", "first_draft: false"
                ),
            )

            shown = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)

            self.wording(root, base_id, staged)

            after = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, after.status, after.reasons)

    def test_a_change_written_before_the_marker_existed_can_be_finished(self):
        with support.Sandbox() as sandbox:
            root, base_id, staged = self.a_draft(sandbox)
            support.write(
                staged,
                support.read(staged).replace("first_draft: true\n", ""),
            )
            state.clear_first_draft(
                base_id, os.path.basename(staged)[: -len(".md")]
            )

            shown = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)

            self.wording(root, base_id, staged)

            after = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, after.status, after.reasons)

    def test_a_change_nobody_wanted_is_off_the_record(self):
        with support.Sandbox() as sandbox:
            root, base_id, staged = self.a_draft(sandbox)
            staging_id = os.path.basename(staged)[: -len(".md")]
            self.assertTrue(state.is_a_first_draft(base_id, staging_id))

            approve_local.drop(staged, root, base_id)

            self.assertFalse(state.is_a_first_draft(base_id, staging_id))

    def test_an_approved_change_is_off_the_record_too(self):
        with support.Sandbox() as sandbox:
            root, base_id, staged = self.a_draft(sandbox)
            staging_id = os.path.basename(staged)[: -len(".md")]
            self.wording(root, base_id, staged)
            runner = support.NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertFalse(state.is_a_first_draft(base_id, staging_id))


class TestACopyOfAFirstDraftUnderAnotherName(unittest.TestCase):
    """N5. The rules leaned on a field in the same unprotected file."""

    def test_the_origin_written_in_the_file_decides_nothing(self):
        import test_first_draft_marker as first_draft

        with support.Sandbox() as sandbox:
            root, base_id = first_draft.local_base(sandbox)
            staged = first_draft.a_first_draft(root)
            staging = compose_proposal.load_staging(staged)
            twin_id = "stg-" + "b" * 16
            text = (
                support.read(staged)
                .replace(staging.staging_id, twin_id)
                .replace("first_draft: true", "first_draft: false")
                .replace(
                    staging.edits[0].text.strip(),
                    "TODO rewrite this part to match the new direction",
                )
            )
            for origin in ("inbox", "ledger"):
                twin = os.path.join(os.path.dirname(staged), twin_id + ".md")
                support.write(
                    twin, text.replace("origin: %s" % staging.origin, "origin: %s" % origin)
                )

                shown = approve_local.show(
                    twin, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
                )

                self.assertEqual(
                    approve_local.STATUS_REFUSED, shown.status, origin
                )
                self.assertIn(
                    approve_local.CODE_STILL_A_PLACEHOLDER, shown.codes, origin
                )
                self.assertIn(
                    "Companies of any size.",
                    support.read(os.path.join(root, ICP)),
                )


class TestTheNameABaseIsKnownByAndTheCommandsAroundIt(unittest.TestCase):
    """N7. The section forms were missed and pure reads were refused."""

    def check(self, command, cwd):
        return gate.check_command(command, cwd, "sess-1")

    def test_taking_the_whole_section_away_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            for command in (
                "git config --local --remove-section gtmbase",
                "git config --local --rename-section gtmbase other",
                "git config --local --unset-all GTMBASE.ID",
            ):
                with self.subTest(command=command):
                    self.assertTrue(self.check(command, root))

    def test_reading_a_setting_changes_nothing_and_is_allowed(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            for command in (
                "git config --get gtmbase.id",
                "git config --local --list",
                "git config -f other.cfg gtmbase.id anything",
            ):
                with self.subTest(command=command):
                    self.assertIsNone(self.check(command, root))


class TestNoAllClearWhileAChangeIsWaiting(unittest.TestCase):
    """G5, which is the first round's A7 still open."""

    def test_a_prepared_change_waiting_is_said_instead_of_an_all_clear(self):
        import test_first_draft_marker as first_draft
        from gtmbase import stale, stale_check

        with support.Sandbox() as sandbox:
            root, base_id = first_draft.local_base(sandbox)
            # The base holds both documents a first run looks for, so that
            # what it says is about the change waiting rather than about a
            # document nobody has written.
            support.write(
                os.path.join(root, "context", "strategy", "positioning.md"),
                support.ICP_TEXT.replace("kind: icp", "kind: positioning"),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "positioning"], cwd=root)
            first_draft.a_first_draft(root, body=first_draft.NAMES_THE_PART)

            result = stale_check.run(
                root,
                base_id,
                runner=support.NoRemoteRunner(),
                gh=support.RecordingGh(),
                now=NOW,
                session_id="sess-1",
                mode="first-run",
            )

            self.assertEqual(
                stale.FINDING_CHANGE_WAITING, result.finding.code, result.sentences
            )
            self.assertIn("waiting for you to approve", result.finding_sentence)
            self.assertNotIn("Nothing is out of date", result.finding_sentence)




# --- The last six ------------------------------------------------------------


class TestWhatCountsAsAChangeWaiting(unittest.TestCase):
    """P1. Anything in the folder that parsed at all was counted.

    A file with a name GTM Base never issues, and a well-formed change about a
    document that is not in the base, both made every closing and every review
    say a change was waiting for ever while the review itself listed nothing
    to read. It happens honestly too, the moment somebody renames or deletes a
    document a change is waiting on.
    """

    def a_base_with_a_change_waiting(self, sandbox):
        import test_first_draft_marker as first_draft

        root, base_id = first_draft.local_base(sandbox)
        staged = first_draft.a_first_draft(
            root, body=first_draft.NAMES_THE_PART
        )
        return root, base_id, staged

    def pending(self, root):
        return os.path.join(root, constants.PROPOSALS_PENDING_DIR)

    OTHER = "context/strategy/positioning.md"

    def a_stray(self, root, staged, name):
        """A well-formed prepared change about a second document, misfiled."""
        support.write(
            os.path.join(root, self.OTHER),
            support.ICP_TEXT.replace("kind: icp", "kind: positioning"),
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "positioning"], cwd=root)
        support.write(
            os.path.join(self.pending(root), name),
            support.read(staged).replace(ICP, self.OTHER),
        )

    def test_a_file_with_a_name_we_never_issued_is_not_a_change(self):
        with support.Sandbox() as sandbox:
            root, _base_id, staged = self.a_base_with_a_change_waiting(sandbox)
            self.a_stray(root, staged, "notes.md")

            found, _orphaned = stale_check._documents_with_a_change_waiting(root)

            self.assertEqual([ICP], found)

    def test_a_file_whose_name_is_not_the_one_inside_it_is_not_a_change(self):
        with support.Sandbox() as sandbox:
            root, _base_id, staged = self.a_base_with_a_change_waiting(sandbox)
            self.a_stray(root, staged, "stg-" + "c" * 16 + ".md")

            found, _orphaned = stale_check._documents_with_a_change_waiting(root)

            self.assertEqual([ICP], found)

    def test_junk_in_the_folder_is_not_a_change(self):
        with support.Sandbox() as sandbox:
            root, _base_id, staged = self.a_base_with_a_change_waiting(sandbox)
            folder = self.pending(root)
            support.write(os.path.join(folder, "empty.md"), "")
            support.write(os.path.join(folder, "notmatter.md"), "just words\n")
            support.write(
                os.path.join(folder, "halfmatter.md"), "---\nschema: 1\n"
            )
            os.makedirs(os.path.join(folder, "folder.md"), exist_ok=True)
            with open(os.path.join(folder, "binary.md"), "wb") as handle:
                handle.write(os.urandom(2048))

            found, _orphaned = stale_check._documents_with_a_change_waiting(root)

            self.assertEqual([ICP], found)

    def test_a_change_about_a_document_that_is_gone_is_not_counted(self):
        with support.Sandbox() as sandbox:
            root, _base_id, staged = self.a_base_with_a_change_waiting(sandbox)
            os.remove(os.path.join(root, ICP))

            found, _orphaned = stale_check._documents_with_a_change_waiting(root)

            self.assertEqual([], found)

    def test_the_run_says_so_and_says_how_to_drop_it(self):
        from gtmbase import stale

        with support.Sandbox() as sandbox:
            root, base_id, _staged = self.a_base_with_a_change_waiting(sandbox)
            support.write(
                os.path.join(root, "context", "strategy", "positioning.md"),
                support.ICP_TEXT.replace("kind: icp", "kind: positioning"),
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "positioning"], cwd=root)
            support.git(["rm", "-q", ICP], cwd=root)
            support.git(["commit", "-q", "-m", "the document is gone"], cwd=root)

            result = stale_check.run(
                root,
                base_id,
                runner=support.NoRemoteRunner(),
                gh=support.RecordingGh(),
                now=NOW,
                session_id="sess-1",
                mode="first-run",
            )

            self.assertIn(
                stale_check.CHANGE_ABOUT_A_MISSING_DOCUMENT, result.sentences
            )
            self.assertNotEqual(
                stale.FINDING_CHANGE_WAITING, result.finding.code
            )


class TestADocumentWithNoPartsAtAll(unittest.TestCase):
    """P3. It could never be corrected, and nothing said why."""

    def a_document_with_no_parts(self, sandbox):
        import test_first_draft_marker as first_draft

        root, base_id = first_draft.local_base(sandbox)
        full = os.path.join(root, ICP)
        support.write(
            full, support.read(full).replace("## Firmographics\n\n", "")
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "no parts"], cwd=root)
        return root, base_id, full

    def test_the_wording_command_says_to_give_it_a_heading(self):
        import test_first_draft_marker as first_draft

        with support.Sandbox() as sandbox:
            root, base_id, _full = self.a_document_with_no_parts(sandbox)
            staged = first_draft.a_first_draft(root)

            with self.assertRaises(Exception) as caught:
                compose_proposal.write_the_wording(
                    root,
                    staged,
                    "We sell to companies of fifty people and up.",
                    base_id=base_id,
                )

            self.assertEqual(
                compose_proposal.CODE_NO_PARTS_AT_ALL,
                getattr(caught.exception, "code", None),
            )
            self.assertEqual(
                compose_proposal.NO_PARTS_AT_ALL, str(caught.exception)
            )

    def test_the_hand_edit_says_the_same_thing(self):
        with support.Sandbox() as sandbox:
            root, base_id, full = self.a_document_with_no_parts(sandbox)
            support.write(
                full,
                support.read(full).replace(
                    "Companies of any size.", "Companies of fifty and up."
                ),
            )

            with self.assertRaises(Exception) as caught:
                compose_proposal.stage_local_edit(
                    root,
                    base_id,
                    HAND_EDIT_SOURCE,
                    runner=support.NoRemoteRunner(),
                    now=TODAY,
                )

            self.assertEqual(
                compose_proposal.NO_PARTS_AT_ALL, str(caught.exception)
            )


class TestADenyAlwaysWinsOverAQuestion(unittest.TestCase):
    """P2. A link under the plugins folder into a base's own folders."""

    def decision(self, path):
        answer = write_hook.run(
            {
                "session_id": "sess-1",
                "transcript_path": os.path.join(
                    os.path.expanduser("~"), "." + "claude", "x.jsonl"
                ),
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "cwd": os.path.dirname(path),
                "tool_input": {"file_path": path, "content": "x"},
            }
        )
        return (
            answer["hookSpecificOutput"]["permissionDecision"]
            if answer
            else "nothing"
        )

    def test_a_link_from_the_plugins_folder_into_a_base_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            folder = write_hook.client_plugins_dir()
            os.makedirs(folder, exist_ok=True)
            os.symlink(
                os.path.join(root, "." + "g" + "it"),
                os.path.join(folder, "to-history"),
            )
            os.symlink(
                paths.seat_home_path(), os.path.join(folder, "to-records")
            )

            self.assertEqual(
                "deny",
                self.decision(
                    os.path.join(folder, "to-history", "hooks", "pre-push")
                ),
            )
            self.assertEqual(
                "deny",
                self.decision(os.path.join(folder, "to-records", "machine.json")),
            )

    def test_an_ordinary_file_under_the_plugins_folder_is_still_asked_about(self):
        with support.Sandbox() as sandbox:
            local_base(sandbox)
            folder = write_hook.client_plugins_dir()

            self.assertEqual(
                "ask", self.decision(os.path.join(folder, "config.json"))
            )


class TestTheFallbackAsksAboutTheSameThings(unittest.TestCase):
    """P4. While it is broken they were waved through instead."""

    def a_broken_copy(self, sandbox):
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(support.PLUGIN_DIR, root)
        support.write(
            os.path.join(root, "scripts", "write_check.py"),
            "raise SystemExit(70)\n",
        )
        return root

    def answer(self, path, root):
        import json
        import subprocess

        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = root
        payload = {
            "session_id": "sess-1",
            "transcript_path": os.path.join(
                os.path.expanduser("~"), "." + "claude", "x.jsonl"
            ),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": os.path.dirname(path),
            "tool_input": {"file_path": path, "content": "x"},
        }
        finished = subprocess.run(
            ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(0, finished.returncode)
        printed = finished.stdout
        if b'"deny"' in printed:
            return "deny"
        if b'"ask"' in printed:
            return "ask"
        return "nothing"

    def test_the_settings_and_the_plugins_folder_are_asked_about(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            home = os.path.expanduser("~")
            assistant = "." + "claude"
            for named in (
                os.path.join(home, assistant, "settings.json"),
                os.path.join(home, assistant, "settings.local.json"),
                os.path.join(home, assistant, "plugins", "config.json"),
            ):
                with self.subTest(file=named):
                    self.assertEqual("ask", self.answer(named, root))

    def test_what_it_refuses_and_what_it_leaves_alone_are_unchanged(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            base_root, _base_id = local_base(sandbox)

            self.assertEqual(
                "deny",
                self.answer(
                    os.path.join(base_root, "." + "g" + "it", "config"), root
                ),
            )
            self.assertEqual(
                "nothing",
                self.answer(os.path.join(sandbox.path, "notes.md"), root),
            )



if __name__ == "__main__":
    unittest.main()
