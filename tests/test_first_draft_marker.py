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


if __name__ == "__main__":
    unittest.main()
