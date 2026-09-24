"""A first draft is tracked, not recognised by its words.

Findings V8 and N4 of the 2026-09-20 verification round. GTM Base writes a
first draft into a prepared change when a document has fallen behind a context
change, and that draft is a note asking for the real wording rather than a
correction anybody may approve. It used to be caught by matching its exact
words, and dropping the full stop, using lower case, or keeping only the first
half all got past that.

So the prepared change carries a marker saying it is a first draft, put there
by GTM Base itself, and nothing but the one command that writes the real
wording can take it off again.
"""

import datetime
import os
import subprocess
import sys
import unittest

import support

from gtmbase import (
    approve_local,
    compose_proposal,
    constants,
    formats,
    ids,
    machine,
    stale_check,
    state,
    wordsfile,
)

TODAY = datetime.date(2026, 6, 5)
NOW = datetime.datetime(2026, 6, 5, 12, 30, 0)
ICP = "context/strategy/icp.md"
OWNER = "owner@example.com"
SCRIPT = os.path.join(
    support.PLUGIN_DIR, "skills", "propose-change", "scripts", "approve_local.py"
)


def local_base(sandbox, name="local"):
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
    state.update_seat(base_id, first_push_reviewed=False, session_id="sess-1")
    return root, base_id


def an_entry(entry_id=None, body="We stopped selling to small companies."):
    return formats.ChangeEntry(
        id=entry_id or ("stg-" + "a" * 16),
        happened_on="2026-05-01",
        written_on="2026-05-02",
        noted_by=OWNER,
        source="what the owner said",
        affects=[ICP],
        review_by="2026-08-01",
        origin="ledger",
        status="open",
        run_id=None,
        body=body,
    )


# A change that says which part of the document it is about, and one that does
# not. The second one is where the first draft used to be allowed to land in a
# part of its own, leaving the claim it made obsolete standing (finding N4).
NAMES_THE_PART = (
    "Firmographics changed: we stopped selling to small companies."
)


def a_first_draft(root, body="We stopped selling to small companies."):
    """The prepared change GTM Base writes when a document has fallen behind."""
    entry = an_entry(body=body)
    staging = stale_check.build_file_proposal(
        root, entry, constants.CHANGES_DIR + "/" + entry.id + ".md", ICP
    )
    path = os.path.join(
        root, constants.PROPOSALS_PENDING_DIR, staging.staging_id + ".md"
    )
    support.write(path, staging.render())
    # And this seat's own record of it, which is what the check on a base
    # writes beside the prepared change itself (finding M1 of the third look).
    from gtmbase import machine, paths

    resolution = paths.resolve_base(root, machine.load_machine_state())
    if resolution.base_id:
        state.note_first_draft(resolution.base_id, staging.staging_id)
    return path


def run_script(root, arguments):
    return subprocess.run(
        [sys.executable, SCRIPT] + [str(item) for item in arguments],
        cwd=root,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def value_of(output, name):
    for line in output.split("\n"):
        if line.startswith(name + "="):
            return line[len(name) + 1 :].strip()
    return None


class TestTheMarkerItself(unittest.TestCase):
    def test_a_first_draft_is_written_with_the_marker_on_it(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root)

            staging = compose_proposal.load_staging(staged)

            self.assertTrue(staging.first_draft)

    def test_retyping_the_note_does_not_take_the_marker_off(self):
        """V8. Every one of these got past the rule that read the words."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root)
            tail = stale_check.PLACEHOLDER_TAIL
            for retyped in (
                "Update needed: we stopped selling to small companies. " + tail[:-1],
                ("Update needed: We stopped selling to small companies. " + tail).lower(),
                "Update needed: We stopped selling to small companies.  " + tail,
                "Update needed: We stopped selling to small companies. "
                + tail.replace("should reflect", "should\nreflect"),
                "Update needed: We stopped selling to small companies.",
            ):
                support.write_the_wording_by_hand(staged, retyped)

                shown = approve_local.show(
                    staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
                )

                self.assertEqual(
                    approve_local.STATUS_REFUSED, shown.status, retyped
                )
                self.assertIn(
                    approve_local.CODE_STILL_A_PLACEHOLDER, shown.codes, retyped
                )


class TestTheOneWayToClearIt(unittest.TestCase):
    def wording_file(self, root, text):
        handed = run_script(root, ["--new-words-file", "answer"])
        path = value_of(handed.stdout.decode("utf-8"), "words")
        if not path:
            raise AssertionError(handed.stdout + handed.stderr)
        support.write(path, text)
        return path

    def test_the_command_writes_the_wording_and_takes_the_marker_off(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            words = self.wording_file(
                root, "We sell to companies of twenty to two hundred people."
            )

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", words]
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            staging = compose_proposal.load_staging(staged)
            self.assertFalse(staging.first_draft)
            self.assertIn("twenty to two hundred", staging.edits[0].text)
            shown = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)

    def test_wording_that_is_still_the_note_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            words = self.wording_file(
                root,
                "update needed: we stopped selling to small companies  "
                "this section should reflect that change",
            )

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", words]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertTrue(compose_proposal.load_staging(staged).first_draft)

    def test_a_words_file_nobody_handed_out_is_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            mine = support.write(
                os.path.join(sandbox.path, "private.txt"), "Anything at all.\n"
            )

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", mine]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertIn(
                wordsfile.NOT_OURS,
                (done.stdout + done.stderr).decode("utf-8"),
            )
            self.assertTrue(compose_proposal.load_staging(staged).first_draft)


class TestTheObsoleteClaimIsGone(unittest.TestCase):
    """N4. The wording used to be allowed to land in a part of its own."""

    def test_the_wording_replaces_the_part_the_change_is_about(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root)
            staging = compose_proposal.load_staging(staged)
            # The change names no heading in the document, so GTM Base cannot
            # work out which part it is about and the command has to be told.
            self.assertEqual("add", staging.edits[0].op)

            listed = run_script(root, ["--staging", staged, "--sections"])
            self.assertEqual(0, listed.returncode, listed.stderr)
            printed = listed.stdout.decode("utf-8")
            self.assertIn("Firmographics", printed)
            number = None
            for line in printed.split("\n"):
                if line.startswith("section=") and "Firmographics" in line:
                    number = line[len("section=") :].split(" ")[0]
            self.assertIsNotNone(number, printed)

            handed = run_script(root, ["--new-words-file", "answer"])
            words = value_of(handed.stdout.decode("utf-8"), "words")
            support.write(
                words, "We sell to companies of twenty to two hundred people."
            )
            done = run_script(
                root,
                [
                    "--staging",
                    staged,
                    "--wording",
                    "--words",
                    words,
                    "--section",
                    number,
                ],
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

            runner = support.NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            whole = support.read(os.path.join(root, ICP))
            self.assertIn("twenty to two hundred people", whole)
            self.assertNotIn(
                "Companies of any size.",
                whole,
                "the claim the change made obsolete is still in the document",
            )

    def test_the_wording_without_a_part_named_is_refused_for_a_fallback(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root)
            handed = run_script(root, ["--new-words-file", "answer"])
            words = value_of(handed.stdout.decode("utf-8"), "words")
            support.write(words, "We sell to bigger companies now.")

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", words]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertTrue(compose_proposal.load_staging(staged).first_draft)



# --- M1 of the third look ----------------------------------------------------


class TestOneOrdinaryEditOfThePreparedChange(unittest.TestCase):
    """M1. The marker sat in a file any file tool may write.

    The prepared change is not in a folder GTM Base keeps, and it must not be:
    the assistant writes the real wording into it. So taking the marker line
    out of it with one ordinary edit cleared it, and a paraphrase of the note
    was then approved with the claim it should have corrected still standing.
    """

    def test_the_prepared_change_is_a_file_any_tool_may_write(self):
        from gtmbase import write_hook

        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root)

            answer = write_hook.run(
                {
                    "session_id": "sess-1",
                    "transcript_path": os.path.join(
                        os.path.expanduser("~"), "." + "claude", "x.jsonl"
                    ),
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Edit",
                    "cwd": root,
                    "tool_input": {
                        "file_path": staged,
                        "old_string": "first_draft: true",
                        "new_string": "first_draft: false",
                    },
                }
            )

            self.assertIsNone(
                answer, "this is the reason the record is kept elsewhere too"
            )

    def test_taking_the_line_out_and_rewording_the_note_changes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root)
            whole = support.read(staged)
            note = compose_proposal.load_staging(staged).edits[0].text.strip()
            support.write(
                staged,
                whole.replace("first_draft: true\n", "").replace(
                    note, "TODO rewrite this part to match the new direction"
                ),
            )

            shown = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )

            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertIn(approve_local.CODE_STILL_A_PLACEHOLDER, shown.codes)
            self.assertIn(
                "Companies of any size.", support.read(os.path.join(root, ICP))
            )

    def test_a_change_the_check_wrote_with_no_marker_at_all_is_a_first_draft(self):
        """A prepared change written by an older build says nothing here."""
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root)
            support.write(
                staged, support.read(staged).replace("first_draft: true\n", "")
            )
            state.clear_first_draft(base_id, os.path.basename(staged)[: -len(".md")])

            staging = compose_proposal.load_staging(staged)

            self.assertIsNone(staging.first_draft)
            self.assertTrue(compose_proposal.still_a_first_draft(staging))

    def test_the_wording_command_clears_the_record_as_well_as_the_line(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            staging_id = os.path.basename(staged)[: -len(".md")]
            self.assertTrue(state.is_a_first_draft(base_id, staging_id))
            handed = run_script(root, ["--new-words-file", "answer"])
            words = value_of(handed.stdout.decode("utf-8"), "words")
            support.write(words, "We sell to companies of twenty and up.")

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", words]
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertFalse(state.is_a_first_draft(base_id, staging_id))


# --- R7 of Astra's third verification ----------------------------------------


class TestTheWordingCanBeRevisedAgain(unittest.TestCase):
    """R7. A second wording correction was refused after its file was taken.

    The first wording took the marker and this seat's record off, which is
    right, and then the one command for writing wording refused the owner's
    next correction as not a first draft, after it had already read and
    thrown away the file holding their new words. This is Astra's scenario
    exactly, through the documented command.
    """

    def words(self, root, text):
        handed = run_script(root, ["--new-words-file", "answer"])
        path = value_of(handed.stdout.decode("utf-8"), "words")
        if not path:
            raise AssertionError(handed.stdout + handed.stderr)
        support.write(path, text)
        return path

    def first_wording(self, root, staged):
        done = run_script(
            root,
            [
                "--staging",
                staged,
                "--wording",
                "--words",
                self.words(root, "We sell to companies of twenty and up."),
            ],
        )
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_a_second_correction_through_the_documented_command_is_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            second = self.words(root, "We sell to companies of fifty and up.")

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", second]
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            staging = compose_proposal.load_staging(staged)
            self.assertIn("fifty and up", staging.edits[0].text)
            self.assertFalse(os.path.exists(second))
            shown = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            self.assertIn("fifty and up", shown.artifact)

    def test_any_number_of_revisions_may_follow(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            for number in ("thirty", "forty", "sixty"):
                path = self.words(root, "We sell to companies of %s and up." % number)
                done = run_script(
                    root, ["--staging", staged, "--wording", "--words", path]
                )
                self.assertEqual(0, done.returncode, done.stdout + done.stderr)
                self.assertIn(
                    number, compose_proposal.load_staging(staged).edits[0].text
                )

    def test_a_revision_needs_a_fresh_look_even_with_the_same_words(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            earlier = approve_local.show(
                staged, root, base_id, runner=support.NoRemoteRunner(), now=TODAY
            )
            self.assertEqual(approve_local.STATUS_SHOWN, earlier.status)
            same = self.words(root, "We sell to companies of twenty and up.")

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", same]
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

            applied = approve_local.approve(
                staged,
                root,
                base_id,
                earlier.shown_hash,
                runner=support.NoRemoteRunner(),
                now=NOW,
            )
            self.assertEqual(approve_local.STATUS_MOVED, applied.status)

    def test_a_revision_that_is_the_note_again_is_refused_and_keeps_the_file(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            before = support.read(staged)
            note = self.words(
                root,
                "update needed: we stopped selling to small companies  "
                "this section should reflect that change",
            )

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", note]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertEqual(before, support.read(staged))
            # Nothing was written, so the words are still there to be fixed.
            self.assertTrue(os.path.exists(note))

    def test_a_refused_first_wording_keeps_its_file_too(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root)
            path = self.words(root, "We sell to companies of twenty and up.")

            # The change names no part, so the first wording needs one.
            done = run_script(
                root, ["--staging", staged, "--wording", "--words", path]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertTrue(os.path.exists(path))
            done = run_script(
                root,
                ["--staging", staged, "--wording", "--words", path, "--section", "1"],
            )
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertFalse(os.path.exists(path))

    def test_a_change_made_by_hand_is_not_reworded_this_way(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            full = os.path.join(root, ICP)
            support.write(
                full,
                support.read(full).replace(
                    "Companies of any size.", "Companies of fifty and up."
                ),
            )
            staged = compose_proposal.stage_local_edit(
                root,
                base_id,
                "The quarterly review said so, on slide four of the deck.",
                runner=support.NoRemoteRunner(),
                now=TODAY,
            )
            before = support.read(staged)
            path = self.words(root, "Companies of eighty and up.")

            done = run_script(
                root, ["--staging", staged, "--wording", "--words", path]
            )

            self.assertNotEqual(0, done.returncode)
            self.assertIn(
                compose_proposal.MADE_BY_HAND_WORDING, done.stdout.decode("utf-8")
            )
            self.assertEqual(before, support.read(staged))
            self.assertTrue(os.path.exists(path))


# --- N2 of Astra's fourth verification ---------------------------------------


class TestARevisionThatLandsWhileApprovalReads(unittest.TestCase):
    """N2. A revision written during approval went through on the old yes.

    Approval read the prepared change once for the value the yes is checked
    against and again for what it validates and writes. A wording command
    landing between the two reads wrote revision two's words under revision
    one's value, which the owner had seen. Astra's scenario, with the second
    read made to see the revision exactly where it would land.
    """

    words = TestTheWordingCanBeRevisedAgain.words
    first_wording = TestTheWordingCanBeRevisedAgain.first_wording

    def revisions(self, root, staged):
        """The prepared change at revision one and at revision two, as text."""
        self.first_wording(root, staged)
        first = support.read(staged)
        done = run_script(
            root,
            [
                "--staging", staged, "--wording", "--words",
                self.words(root, "We sell to companies of fifty and up."),
            ],
        )
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        second = support.read(staged)
        support.write(staged, first)
        return first, second

    def test_what_is_written_is_what_was_shown(self):
        from unittest import mock

        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            _first, second = self.revisions(root, staged)
            runner = support.NoRemoteRunner()
            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
            real_read = approve_local.read_text
            landed = []

            def the_revision_lands_after_this_read(path, *rest, **named):
                got = real_read(path, *rest, **named)
                if not landed and os.path.realpath(path) == os.path.realpath(staged):
                    landed.append(True)
                    support.write(staged, second)
                return got

            with mock.patch.object(
                approve_local, "read_text", the_revision_lands_after_this_read
            ):
                applied = approve_local.approve(
                    staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
                )

            self.assertTrue(landed)
            written = support.read(os.path.join(root, ICP))
            self.assertNotIn("fifty and up", written)
            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertIn("twenty and up", written)

    def test_an_ordinary_revision_still_shows_and_applies(self):
        with support.Sandbox() as sandbox:
            root, base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            _first, second = self.revisions(root, staged)
            support.write(staged, second)
            runner = support.NoRemoteRunner()

            shown = approve_local.show(staged, root, base_id, runner=runner, now=TODAY)
            applied = approve_local.approve(
                staged, root, base_id, shown.shown_hash, runner=runner, now=NOW
            )

            self.assertEqual(
                approve_local.STATUS_APPLIED, applied.status, applied.reasons
            )
            self.assertIn("fifty and up", support.read(os.path.join(root, ICP)))


# --- N9 of Astra's fourth verification ---------------------------------------


def _the_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gtm_base_wording_shim", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_in(root, module, arguments):
    import contextlib
    import io

    was = os.getcwd()
    os.chdir(root)
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            code = module.main([str(item) for item in arguments])
    finally:
        os.chdir(was)
    return code, printed.getvalue()


class TestAWordsFileIsClaimedOnce(unittest.TestCase):
    """N9. A words file read without being taken could be used twice.

    The wording command reads the file, does its work, and only then takes
    the file away by its name. Two commands could read the same file before
    either finished, and a file the owner wrote again under that name while
    the first one ran was the file taken away. Astra's two probes, run through
    the command itself with the second command and the owner's rewrite landing
    while the first is writing.
    """

    words = TestTheWordingCanBeRevisedAgain.words
    first_wording = TestTheWordingCanBeRevisedAgain.first_wording

    def during_the_wording(self, root, staged, path, what_happens):
        """Run the wording command with something happening while it writes."""
        from unittest import mock

        module = _the_script()
        real = compose_proposal.write_the_wording
        seen = []

        def writing(*arguments, **named):
            if not seen:
                seen.append(None)
                seen[0] = what_happens()
            return real(*arguments, **named)

        with mock.patch.object(module.compose_proposal, "write_the_wording", writing):
            code, printed = _run_in(
                root, module, ["--staging", staged, "--wording", "--words", path]
            )
        return code, printed, seen[0] if seen else None

    def test_a_second_command_cannot_use_the_same_words(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            path = self.words(root, "We sell to companies of fifty and up.")

            def a_second_command():
                return _run_in(
                    root,
                    _the_script(),
                    ["--staging", staged, "--wording", "--words", path],
                )

            code, printed, second = self.during_the_wording(
                root, staged, path, a_second_command
            )

            self.assertEqual(0, code, printed)
            self.assertNotEqual(0, second[0], second[1])
            self.assertIn(wordsfile.NOT_OURS, second[1])

    def test_words_written_again_meanwhile_are_not_taken_away(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            path = self.words(root, "We sell to companies of fifty and up.")
            newer = "We sell to companies of sixty and up."

            code, printed, _ = self.during_the_wording(
                root, staged, path, lambda: support.write(path, newer)
            )

            self.assertEqual(0, code, printed)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(newer, support.read(path))
            self.assertIn(
                "fifty and up", compose_proposal.load_staging(staged).edits[0].text
            )

    def test_a_removal_that_fails_is_said_and_the_words_cannot_be_used_again(self):
        from unittest import mock

        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            path = self.words(root, "We sell to companies of fifty and up.")
            module = _the_script()

            with mock.patch.object(
                wordsfile, "_take_away", side_effect=OSError("refused")
            ):
                code, printed = _run_in(
                    root, module, ["--staging", staged, "--wording", "--words", path]
                )

            self.assertEqual(0, code, printed)
            self.assertIn(wordsfile.WORDS_STILL_THERE, printed)
            again, said = _run_in(
                root, _the_script(), ["--staging", staged, "--wording", "--words", path]
            )
            self.assertNotEqual(0, again, said)

    def test_a_refusal_keeps_the_words_under_their_own_name(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            path = self.words(root, "update needed: this section should reflect that change")
            before = support.read(path)

            code, printed = _run_in(
                root, _the_script(), ["--staging", staged, "--wording", "--words", path]
            )

            self.assertNotEqual(0, code, printed)
            self.assertEqual(before, support.read(path))
            self.assertEqual(
                [os.path.basename(path)], sorted(os.listdir(os.path.dirname(path)))
            )

    def test_an_ordinary_wording_takes_its_file_away(self):
        with support.Sandbox() as sandbox:
            root, _base_id = local_base(sandbox)
            staged = a_first_draft(root, body=NAMES_THE_PART)
            self.first_wording(root, staged)
            path = self.words(root, "We sell to companies of fifty and up.")

            code, printed = _run_in(
                root, _the_script(), ["--staging", staged, "--wording", "--words", path]
            )

            self.assertEqual(0, code, printed)
            self.assertNotIn(wordsfile.WORDS_STILL_THERE, printed)
            self.assertEqual([], os.listdir(os.path.dirname(path)))


if __name__ == "__main__":
    unittest.main()
