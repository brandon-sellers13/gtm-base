"""Astra's confirmation pass on Unit 1.5b, 2026-09-26: its five findings.

The pass is docs/reviews/2026-09-26-unit-1-5b-verify-astra.md in the main
checkout. Each test here was run first against the branch as it stood at
2a6fd91 and seen to fail there, before the fix beside it was made. The last
class is the merge regression the pass asked for under finding 6 of the
first review. Nothing here reaches the person's own home folder, their git
settings, or a real base.
"""

import datetime
import json
import os
import shutil
import subprocess
import unittest
from unittest import mock

import support
import test_changes_migration as migration
import test_context_standard as standard
import test_session_start as session_tests

from gtmbase import (
    changes,
    constants,
    gate,
    machine,
    session_start,
    state,
    write_hook,
)
from gtmbase.gitcmd import GitRunner

TODAY = standard.TODAY
OWNER = standard.OWNER

# Lines a source map ordinarily holds, none of which is a credential. Every
# one of them has to pass every check the source map goes through.
ORDINARY_LINES = (
    "Deals live in HubSpot at <https://app.hubspot.com>.",
    "The pipeline report is https://app.hubspot.com/reports/123/pipeline",
    "The launch board is [in Notion](https://www.notion.so/acme/Launch-abc123).",
    "Sales calls are in Gong, read by the Gong connector.",
    "Leads arrive in the shared inbox, leads@acme.com, which the Gmail tool reads.",
    "Ad drafts are saved in the LinkedIn Campaign Manager account.",
)
# Lines that carry a credential, each of which has to be refused.
CREDENTIAL_LINES = (
    "CRM token: ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
    "api_key = " + "abcdef0123456789abcdef",
    "The export is at https://dana:" + "hunter2secret@crm.acme.com/export",
    "The feed is https://feeds.acme.com/leads.csv?token=" + "a1b2c3d4e5f6g7h8",
)


def denied(answer):
    return bool(answer) and answer["hookSpecificOutput"]["permissionDecision"] == "deny"


def write_request(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit_request(path, old, new):
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": path, "old_string": old, "new_string": new},
    }


def multi_request(path, pairs):
    return {
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": path,
            "edits": [{"old_string": old, "new_string": new} for old, new in pairs],
        },
    }


# --- Finding 1 (high): an edit arriving while giving up is still theirs ------


class TestAnEditArrivingWhileGivingUp(standard.LayoutCase):
    """The undo loop itself looks at the bytes right before it acts."""

    def edit_after_the_look(self, relative, words):
        """Write the person's words the moment everything has been sorted."""
        real = changes._sort_out

        def sorted_then_edited(*arguments, **options):
            found = real(*arguments, **options)
            full = os.path.join(self.root, relative.replace("/", os.sep))
            with open(full, "a", encoding="utf-8") as handle:
                handle.write(words)
            return found

        return mock.patch.object(changes, "_sort_out", sorted_then_edited)

    def test_a_record_the_run_wrote_and_had_not_saved(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        runner = migration._StopAfter(stop_before_subject=changes.RECORD_SUBJECT)
        with self.assertRaises(migration._Stopped):
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        records = [
            name
            for name in self.listing(constants.CORRECTIONS_DIR)
            if "move-to-the-class-layout" in name
        ]
        self.assertEqual(1, len(records))
        record = constants.CORRECTIONS_DIR + "/" + records[0]

        with self.edit_after_the_look(record, "\nA line of my own.\n"):
            given_up = changes.abandon(self.root, self.base_id, today=TODAY)

        text = support.read(os.path.join(self.root, record))
        self.assertIn("A line of my own.", text)
        self.assertIn(changes.NAMED_RECORD, given_up.sentence)

    def test_a_file_the_base_had_saved_and_the_run_rewrote(self):
        self.with_the_older_template_folders()
        self.with_changes(constants.WORK_CHANGES_DIR)
        runner = migration._StopAfter(stop_before_subject=changes.REWRITE_SUBJECT)
        with self.assertRaises(migration._Stopped):
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)

        with self.edit_after_the_look(constants.MAP_PATH, "\nMy own note.\n"):
            given_up = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertIn(
            "My own note.", support.read(os.path.join(self.root, constants.MAP_PATH))
        )
        self.assertIn("your base's map", given_up.sentence)


# --- Finding 2 (high): a rule written by hand keeps winning -------------------


class TestTheOwnershipDefaultsNeverOverrideAHandRule(unittest.TestCase):
    def rules(self, text):
        return [
            line for line in text.split("\n") if line.strip() and not line.startswith("#")
        ]

    def test_a_security_rule_for_the_source_map_still_wins(self):
        before = (
            "context/** @acme-owner\n"
            "access/stack.md @security\n"
            "corrections/** @acme-owner\n"
        )
        rules = self.rules(changes._owners_moved(before))
        self.assertIn("access/** @acme-owner", rules)
        # The last matching rule wins, so the hand rule has to come after.
        self.assertLess(
            rules.index("access/** @acme-owner"), rules.index("access/stack.md @security")
        )
        self.assertIn("learning/corrections/** @acme-owner", rules)

    def test_defaults_come_before_every_rule_already_there(self):
        before = "context/** @acme-owner\ncorrections/** @acme-owner\n"
        rules = self.rules(changes._owners_moved(before))
        for default in (
            "learning/lessons/** @acme-owner",
            "access/** @acme-owner",
            "skills/** @acme-owner",
            "standards/** @acme-owner",
        ):
            self.assertLess(rules.index(default), rules.index("context/** @acme-owner"))

    def test_a_narrow_exception_never_owns_the_new_folders(self):
        before = "context/** @acme-owner\ncorrections/private.md @legal\n"
        rules = self.rules(changes._owners_moved(before))
        self.assertIn("learning/corrections/private.md @legal", rules)
        for rule in rules:
            self.assertFalse(rule.startswith(("access/", "skills/", "standards/")), rule)
            self.assertFalse(rule.startswith("learning/lessons"), rule)

    def test_the_broad_rule_gives_the_owners_whatever_follows_it(self):
        before = "corrections/** @acme-owner\ncorrections/legal.md @legal\n"
        rules = self.rules(changes._owners_moved(before))
        self.assertIn("access/** @acme-owner", rules)
        self.assertNotIn("access/** @legal", rules)


# --- Findings 3 and 4 (medium): the source map, screened whole and fairly ----


class SourceMapCase(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.root = self.sandbox.base()[0]
        self.stack = os.path.join(self.root, constants.STACK_PATH)
        support.write(self.stack, "# Stack\n\nDeals live in the CRM.\n")


class TestFinding3AnEditIsScreenedAsTheWholeFile(SourceMapCase):
    def test_an_edit_that_completes_a_token(self):
        token = CREDENTIAL_LINES[0]
        support.write(self.stack, "# Stack\n\n" + token[:-6] + "\n")
        answer = write_hook.run(edit_request(self.stack, token[-12:-6], token[-12:]))
        self.assertTrue(denied(answer))

    def test_a_multi_edit_that_assembles_a_token(self):
        token = CREDENTIAL_LINES[0]
        support.write(self.stack, "# Stack\n\nfirst\nsecond\n")
        answer = write_hook.run(
            multi_request(
                self.stack, [("first", token[:20]), ("\nsecond", token[20:])]
            )
        )
        self.assertTrue(denied(answer))


class TestFinding4OrdinaryLinesAreNeverRefused(SourceMapCase):
    def test_a_write(self):
        for line in ORDINARY_LINES:
            with self.subTest(line=line):
                self.assertIsNone(
                    write_hook.run(write_request(self.stack, "# Stack\n\n%s\n" % line))
                )
        for line in CREDENTIAL_LINES:
            with self.subTest(line=line):
                self.assertTrue(
                    denied(write_hook.run(write_request(self.stack, line + "\n")))
                )

    def test_an_edit(self):
        for line in ORDINARY_LINES:
            with self.subTest(line=line):
                self.assertIsNone(
                    write_hook.run(edit_request(self.stack, "Deals live in the CRM.", line))
                )
        for line in CREDENTIAL_LINES:
            with self.subTest(line=line):
                self.assertTrue(
                    denied(
                        write_hook.run(
                            edit_request(self.stack, "Deals live in the CRM.", line)
                        )
                    )
                )

    def test_a_multi_edit(self):
        self.assertIsNone(
            write_hook.run(
                multi_request(
                    self.stack,
                    [("# Stack", "# Stack\n\n" + "\n".join(ORDINARY_LINES))],
                )
            )
        )
        self.assertTrue(
            denied(
                write_hook.run(
                    multi_request(self.stack, [("# Stack", CREDENTIAL_LINES[2])])
                )
            )
        )


class TestFinding4AnUpdateFromTheSharedCopy(
    support.PastTheFirstBackupReview, session_tests.SessionStartHelpers
):
    """The real update a session start makes, not only its helper."""

    def an_update_carrying(self, text):
        root, base_id = self.joined_base()
        self.add_files(root)
        other = self.working_copy(root)
        support.write(os.path.join(other, constants.STACK_PATH), text)
        support.git(["add", "-A"], cwd=other)
        support.git(["commit", "-q", "-m", "the source map"], cwd=other)
        support.git(["push", "-q", "origin", "main"], cwd=other)
        before = support.head_of(root)
        self.run_hook(root, part="context")
        return root, base_id, before

    def test_ordinary_lines_are_taken(self):
        text = "# Stack\n\n" + "\n".join(ORDINARY_LINES) + "\n"
        root, base_id, before = self.an_update_carrying(text)
        self.assertNotEqual(before, support.head_of(root))
        self.assertEqual(
            text, support.read(os.path.join(root, constants.STACK_PATH))
        )
        seat, _problems = state.load_seat(base_id)
        self.assertNotEqual(
            session_start.CODE_PULL_REFUSED, seat.get("pending_visible_note")
        )

    def test_a_credential_is_refused(self):
        for line in CREDENTIAL_LINES:
            with self.subTest(line=line):
                root, base_id, before = self.an_update_carrying(
                    "# Stack\n\n%s\n" % line
                )
                self.assertEqual(before, support.head_of(root))
                seat, _problems = state.load_seat(base_id)
                self.assertEqual(
                    session_start.CODE_PULL_REFUSED, seat["pending_visible_note"]
                )
                self.sandbox.__exit__(None, None, None)
                self.sandbox = support.Sandbox()
                self.sandbox.__enter__()


# --- Finding 5 (medium): the smaller check stays inside bases ------------------


class TestFinding5TheSmallerCheckStaysInsideBases(unittest.TestCase):
    def a_broken_copy(self, sandbox):
        installed = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(installed), exist_ok=True)
        shutil.copytree(support.PLUGIN_DIR, installed)
        support.write(
            os.path.join(installed, "scripts", "write_check.py"),
            "raise SystemExit(70)\n",
        )
        return installed

    def refused(self, installed, path):
        finished = subprocess.run(
            ["sh", os.path.join(installed, "hooks", "write-check.sh"), "claude"],
            input=json.dumps(write_request(path, "x")).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, CLAUDE_PLUGIN_ROOT=installed),
        )
        return b'"deny"' in finished.stdout

    def test_a_copied_template_with_no_repository(self):
        with support.Sandbox() as sandbox:
            installed = self.a_broken_copy(sandbox)
            copied = os.path.join(sandbox.path, "a-copy")
            shutil.copytree(
                os.path.join(support.REPO_ROOT, "templates", "company-base"), copied
            )
            self.assertFalse(
                self.refused(installed, os.path.join(copied, "skills", "x.md"))
            )

    def test_an_ordinary_linked_project_folder(self):
        with support.Sandbox() as sandbox:
            installed = self.a_broken_copy(sandbox)
            root, base_id = sandbox.base()
            project = os.path.join(sandbox.path, "project")
            os.makedirs(os.path.join(project, "skills"))
            support.git(["init", "-q", "-b", "main"], cwd=project)
            machine.link_content(base_id, project)
            self.assertFalse(
                self.refused(installed, os.path.join(project, "skills", "x.md"))
            )
            # The base itself is still refused.
            self.assertTrue(self.refused(installed, os.path.join(root, "skills", "x.md")))


# --- Finding 6 of the first review: a skill that only a merge carries ---------


class TestASkillOnlyAMergeCarries(unittest.TestCase):
    """A merge that adds a file neither side had, taken away again after.

    The difference between the two ends holds no skill, and no ordinary
    piece of work adds one: only the merge does. The check before 2a6fd91
    read the difference between the ends and let this through.
    """

    def test_it_is_refused(self):
        with support.Sandbox() as sandbox:
            root = sandbox.base()[0]
            start = support.head_of(root)
            support.git(["checkout", "-q", "-b", "side"], cwd=root)
            support.write(os.path.join(root, "context", "side.md"), "side\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a side change"], cwd=root)
            support.git(["checkout", "-q", "main"], cwd=root)
            support.write(os.path.join(root, "context", "main.md"), "main\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a main change"], cwd=root)
            support.git(["merge", "-q", "--no-ff", "--no-commit", "side"], cwd=root)
            support.write(os.path.join(root, "skills", "outbound.md"), "steps\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the merge, with a skill in it"], cwd=root)
            support.git(["rm", "-q", "skills/outbound.md"], cwd=root)
            support.git(["commit", "-q", "-m", "gone again"], cwd=root)

            said = gate.scan_range(GitRunner(), root, start, support.head_of(root))

            self.assertEqual(gate.sentence_for(gate.REASON_SKILLS_FILE), said)


if __name__ == "__main__":
    unittest.main()
