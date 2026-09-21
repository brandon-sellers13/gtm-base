"""The backstop that runs as a context file is about to be read.

Every scenario builds a real base in a temporary folder with a temporary home,
and the wrapper is only ever run with the home override pointed at one of
those, so nothing here can see the person's own folders.

What the hook is allowed to do is narrow, and most of these scenarios are about
what it does not do: it never refuses a read, never decides a permission, never
writes into the base, never reaches anything, and says nothing at all for a
file that is not a context file in a base this account has joined.
"""

import datetime
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

import plain_language
import support

from gtmbase import (
    constants,
    formats,
    ids,
    machine,
    moment,
    read_hook,
    state,
)

TODAY = datetime.date(2026, 6, 5)
TUESDAY = "2026-06-02"
THURSDAY = "2026-06-04"
ENTRY = "stg-" + "a" * 16
ICP = "context/strategy/icp.md"
OWNER = "owner@example.com"
SESSION = "sess-1"

PLUGIN_DIR = support.PLUGIN_DIR
WRAPPER = os.path.join(PLUGIN_DIR, "hooks", "read-check.sh")
HOOKS_PATH = os.path.join(PLUGIN_DIR, "hooks", "hooks.json")
MANIFEST_PATH = os.path.join(PLUGIN_DIR, ".claude-plugin", "plugin.json")

CHANGE_BODY = (
    "We stopped selling to companies under twenty people.\n"
    "The last four of them took the longest to close and left the soonest."
)


def entry_text(affects=(ICP,)):
    return "\n".join(
        [
            "---",
            "id: %s" % ENTRY,
            "kind: decision",
            "decided_on: %s" % TUESDAY,
            "written_on: %s" % THURSDAY,
            "decided_by: Jane Doe",
            "source: the weekly go to market meeting",
            "affects: [%s]" % ", ".join(affects),
            "review_by: 2026-09-01",
            "origin: manual",
            "status: open",
            "---",
            "",
            CHANGE_BODY,
            "",
        ]
    )


class Base(object):
    """A base with no shared copy, and one context change in it."""

    def __init__(self, sandbox, name="local", joined=True):
        self.root = os.path.join(sandbox.path, name)
        self.base_id = ids.base_id_random()
        support.make_base(self.root, base_id=self.base_id)
        support.write(
            os.path.join(self.root, ".gitignore"), "work/inbox/\nwork/proposals/\n"
        )
        support.write(
            os.path.join(self.root, constants.ALLOWLIST_PATH), "# ours\n%s\n" % OWNER
        )
        self.save("a local base")
        if joined:
            machine.append_joined(
                root=self.root, base_id=self.base_id, remote=None
            )
            state.update_seat(
                self.base_id, first_push_reviewed=True, session_id=SESSION
            )

    def save(self, message="a change"):
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", message], cwd=self.root)

    def add_change(self, text=None):
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY + ".md"),
            text if text is not None else entry_text(),
        )
        self.save("a context change")

    def path_to(self, relative=ICP):
        return os.path.join(self.root, relative.replace("/", os.sep))


def request(path, session=SESSION, cwd=None, tool="Read"):
    """One request shaped the way the client sends one before a file read."""
    payload = {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": path},
    }
    if cwd is not None:
        payload["cwd"] = cwd
    return payload


def answer(base, path, runner=None, session=SESSION, cwd=None, tool="Read"):
    return read_hook.run(
        request(path, session=session, cwd=cwd, tool=tool),
        now=TODAY,
        runner=runner or support.NoRemoteRunner(),
    )


# --- What it says nothing about ----------------------------------------------


class TestWhatItLeavesAlone(unittest.TestCase):
    """Nearly every read on this computer, said in one word: nothing."""

    def test_a_file_outside_any_base_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            elsewhere = os.path.join(sandbox.path, "somewhere", "notes.md")
            support.write(elsewhere, "# Notes\n")

            self.assertIsNone(answer(base, elsewhere))

    def test_a_file_in_the_base_but_outside_context_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            self.assertIsNone(
                answer(base, base.path_to(constants.CHANGES_DIR + "/" + ENTRY + ".md"))
            )

    def test_a_context_file_nothing_has_overtaken_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)

            self.assertIsNone(answer(base, base.path_to()))

    def test_the_map_is_never_flagged(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change(text=entry_text(affects=(ICP, constants.MAP_PATH)))

            self.assertIsNone(answer(base, base.path_to(constants.MAP_PATH)))

    def test_an_unanswered_marker_alone_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            support.write(
                base.path_to(),
                support.ICP_TEXT + "\n[your call: which segment comes first?]\n",
            )
            base.save("a marker nobody has answered")

            self.assertIsNone(answer(base, base.path_to()))

    def test_another_tool_is_somebody_elses_business(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            self.assertIsNone(answer(base, base.path_to(), tool="Bash"))

    def test_a_file_that_is_not_there_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            self.assertIsNone(answer(base, base.path_to("context/strategy/gone.md")))

    def test_a_base_this_account_never_joined_says_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox, joined=False)
            base.add_change()

            self.assertIsNone(answer(base, base.path_to()))


class TestAChangeWrittenDownTwice(unittest.TestCase):
    """Finding M2 of the 2026-09-20 review.

    The check that reads the base says nothing quiets a change written down
    twice that does not agree with itself, and says so whether the document is
    otherwise flagged or not. This hook answered on the flag alone, so the one
    case the check refuses to be quiet about was the one case it said nothing
    about.
    """

    def twice(self, sandbox):
        base = Base(sandbox)
        support.write(
            os.path.join(base.root, constants.LEGACY_CHANGES_DIR, ENTRY + ".md"),
            entry_text(),
        )
        support.write(
            os.path.join(base.root, constants.CHANGES_DIR, ENTRY + ".md"),
            entry_text().replace("under twenty", "under fifty"),
        )
        base.save("the same change, written twice")
        return base

    def test_it_is_said_although_nothing_at_all_is_flagged(self):
        with support.Sandbox() as sandbox:
            base = self.twice(sandbox)

            found = moment.check(
                base.root,
                base.base_id,
                ICP,
                runner=support.NoRemoteRunner(),
                now=TODAY,
            )
            self.assertFalse(found.flagged)
            self.assertTrue(found.written_twice)

            said = answer(base, base.path_to())
            self.assertIsNotNone(said)
            self.assertIn(
                "written down twice",
                said["hookSpecificOutput"]["additionalContext"],
            )
            self.assertNotIn(
                "permissionDecision", said["hookSpecificOutput"]
            )

    def test_it_is_still_said_once_a_session(self):
        with support.Sandbox() as sandbox:
            base = self.twice(sandbox)

            self.assertIsNotNone(answer(base, base.path_to()))
            self.assertIsNone(answer(base, base.path_to()))

    def test_malformed_input_says_nothing_and_still_ends_well(self):
        for payload in (
            None,
            "",
            [],
            {},
            {"tool_input": "not an object"},
            {"tool_input": {"file_path": ""}},
            {"tool_input": {"file_path": 17}},
            {"tool_name": "Read", "tool_input": {"file_path": "relative/path.md"}},
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(read_hook.run(payload, now=TODAY))


# --- What it says when it speaks ---------------------------------------------


class TestWhatItSaysWhenItSpeaks(unittest.TestCase):
    """The one answer it ever gives, and what is deliberately not in it."""

    def test_a_flagged_file_comes_back_as_context_and_never_as_a_decision(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            said = answer(base, base.path_to())

            self.assertIsNotNone(said)
            self.assertEqual(["hookSpecificOutput"], list(said))
            inner = said["hookSpecificOutput"]
            self.assertEqual("PreToolUse", inner["hookEventName"])
            self.assertEqual(
                ["hookEventName", "additionalContext"], list(inner)
            )
            self.assertNotIn("permissionDecision", inner)
            self.assertNotIn("permissionDecisionReason", inner)
            self.assertNotIn("updatedInput", inner)
            # It is one object the client can read, whole.
            json.loads(json.dumps(said))

    def test_the_context_carries_the_flag_and_tells_the_assistant_to_wait(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            text = answer(base, base.path_to())["hookSpecificOutput"][
                "additionalContext"
            ]

            self.assertIn(moment.PAUSE_BEFORE_USING, text)
            self.assertIn("your customer profile", text)
            self.assertIn(TUESDAY, text)
            self.assertIn(moment.THREE_ANSWERS, text)
            for label in moment.CHANGE_LABELS:
                self.assertIn(label, text)
            self.assertNotIn(ICP, text)
            self.assertNotIn(ENTRY, text)

    def test_a_link_into_the_context_folder_is_treated_as_the_plain_path(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            link = os.path.join(base.root, "shortcut")
            os.symlink(os.path.join(base.root, "context"), link)

            said = answer(base, os.path.join(link, "strategy", "icp.md"))

            self.assertIsNotNone(said)
            self.assertIn(
                "your customer profile",
                said["hookSpecificOutput"]["additionalContext"],
            )

    def test_another_letter_case_is_treated_as_the_plain_path(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            shouted = os.path.join(base.root, "CONTEXT", "STRATEGY", "ICP.MD")
            if not os.path.isfile(shouted):
                self.skipTest("this file system tells one letter case from another")

            said = answer(base, shouted)

            self.assertIsNotNone(said)
            self.assertIn(
                "your customer profile",
                said["hookSpecificOutput"]["additionalContext"],
            )

    def test_a_link_pointing_out_of_the_base_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            outside = os.path.join(sandbox.path, "outside.md")
            support.write(outside, "# Somewhere else\n")
            link = os.path.join(base.root, "context", "strategy", "escape.md")
            os.symlink(outside, link)

            self.assertIsNone(answer(base, link))

    def test_a_session_opened_in_the_linked_folder_is_covered(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            folder = os.path.join(sandbox.path, "marketing")
            os.makedirs(folder)
            support.write(os.path.join(folder, "deck.md"), "# A deck\n")
            machine.link_content(base.base_id, folder)

            said = answer(base, base.path_to(), cwd=folder)

            self.assertIsNotNone(said)


# --- Being told once ---------------------------------------------------------


class TestOneSessionIsToldOnce(unittest.TestCase):
    """The hook and the rule's own script must not add up to two questions."""

    def test_the_same_file_read_twice_in_one_session_is_said_once(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            first = answer(base, base.path_to())
            second = answer(base, base.path_to())

            self.assertIsNotNone(first)
            self.assertIsNone(second)

    def test_a_new_change_in_the_same_session_is_told_about(self):
        """C10: told once was keyed by the document and not by the change."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            first = answer(base, base.path_to())
            self.assertIsNotNone(first)
            self.assertIsNone(answer(base, base.path_to()))

            second_entry = "stg-" + "b" * 16
            support.write(
                os.path.join(base.root, constants.CHANGES_DIR,
                             second_entry + ".md"),
                entry_text().replace(ENTRY, second_entry).replace(
                    "We stopped selling", "We moved upmarket and stopped selling"
                ),
            )
            base.save("a second context change")
            # The first change is settled, so the second is the live one.
            confirmed = formats.ConfirmationLine(
                date="2026-06-05",
                time="09:15:00Z",
                file=ICP,
                trigger="ledger",
                entry=ENTRY,
                question=None,
                run=None,
            )
            support.write(
                os.path.join(base.root, "work", "confirmations",
                             "context--strategy--icp.md"),
                confirmed.render() + "\n",
            )
            base.save("a yes about the first change")

            again = answer(base, base.path_to())

            self.assertIsNotNone(again)
            self.assertIn(
                "moved upmarket",
                again["hookSpecificOutput"]["additionalContext"],
            )

    def test_another_session_is_told_again(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            self.assertIsNotNone(answer(base, base.path_to()))
            self.assertIsNotNone(
                answer(base, base.path_to(), session="sess-2")
            )

    def test_the_hook_issues_no_question_of_its_own(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            answer(base, base.path_to())

            self.assertEqual([], state.load_question_ids(base.base_id)[0])
            self.assertEqual([], state.load_asked(base.base_id)[0])

    def test_the_script_after_the_hook_asks_once_and_not_twice(self):
        """The hook flags it, then the rule's own script runs for that file."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            runner = support.NoRemoteRunner()

            answer(base, base.path_to(), runner=runner)
            first = moment.check(
                base.root, base.base_id, ICP, session_id=SESSION,
                runner=runner, now=TODAY,
            )
            second = moment.check(
                base.root, base.base_id, ICP, session_id=SESSION,
                runner=runner, now=TODAY,
            )

            self.assertEqual(first.question_id, second.question_id)
            self.assertEqual(1, len(state.load_question_ids(base.base_id)[0]))
            self.assertEqual(1, len(state.load_asked(base.base_id)[0]))

    def test_what_it_writes_down_never_holds_the_path_itself(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            answer(base, base.path_to())

            rows, problems = state.load_read_notices(base.base_id)
            self.assertEqual([], problems)
            self.assertEqual(1, len(rows))
            self.assertEqual(ids.path_hash(ICP), rows[0]["path_hash"])
            self.assertNotIn("icp", json.dumps(rows).lower())


# --- What it may never touch -------------------------------------------------


class TestWhatItMayNeverTouch(unittest.TestCase):
    """Nothing leaves this computer, and nothing in the base is written."""

    def test_no_git_call_it_makes_can_reach_a_remote(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            runner = support.NoRemoteRunner()

            said = answer(base, base.path_to(), runner=runner)

            self.assertIsNotNone(said)
            self.assertTrue(runner.calls)

    def test_the_module_imports_nothing_that_can_reach_a_network(self):
        source = support.read(
            os.path.join(support.LIB_DIR, "gtmbase", "read_hook.py")
        )
        for name in (
            "socket",
            "urllib",
            "http.client",
            "ssl",
            "ftplib",
            "requests",
            "smtplib",
        ):
            self.assertNotIn("import %s" % name, source)
        loaded = sys.modules["gtmbase.read_hook"]
        for name in ("socket", "urllib", "ssl", "requests"):
            self.assertFalse(hasattr(loaded, name), name)

    def test_nothing_in_the_base_is_written_or_moved(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            before = {}
            for where, _folders, names in os.walk(base.root):
                if ".git" in where:
                    continue
                for name in names:
                    full = os.path.join(where, name)
                    before[full] = os.stat(full).st_mtime_ns

            answer(base, base.path_to())

            after = {}
            for where, _folders, names in os.walk(base.root):
                if ".git" in where:
                    continue
                for name in names:
                    full = os.path.join(where, name)
                    after[full] = os.stat(full).st_mtime_ns
            self.assertEqual(before, after)

    def test_a_run_that_cannot_read_the_records_says_nothing_rather_than_ok(self):
        """S6: an exhausted budget used to make a settled document look stale.

        Blame is how a confirmation gets an author. When it timed out every
        confirmation came back unowned, every settled document looked out of
        date, and the hook raised a flag on a document somebody had already
        confirmed. Saying nothing is the only honest answer, and saying nothing
        here does not mean the document is fine.
        """
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            confirmed = formats.ConfirmationLine(
                date="2026-06-05",
                time="09:15:00Z",
                file=ICP,
                trigger="ledger",
                entry=ENTRY,
                question=None,
                run=None,
            )
            support.write(
                os.path.join(base.root, "work", "confirmations",
                             "context--strategy--icp.md"),
                confirmed.render() + "\n",
            )
            base.save("a yes from its owner")

            # With the records readable, the document is settled and quiet.
            self.assertIsNone(answer(base, base.path_to()))

            # With blame too slow to answer, it is still quiet, and quiet for
            # the right reason: nothing was read, so nothing is claimed.
            slow = support.SlowRunner(seconds=0.6)
            self.assertIsNone(
                read_hook.run(request(base.path_to()), now=TODAY, runner=slow)
            )

    def test_it_stops_inside_its_own_budget_when_git_is_slow(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            runner = support.SlowRunner(seconds=2)

            started = datetime.datetime.now()
            said = read_hook.run(
                request(base.path_to()), now=TODAY, runner=runner
            )
            spent = (datetime.datetime.now() - started).total_seconds()

            # The result is what matters: a run that ran out of time says
            # nothing rather than guessing, and it stops inside its budget.
            self.assertIsNone(said)
            self.assertLess(spent, read_hook.GIT_BUDGET_SECONDS + 2)
            self.assertTrue(
                all(
                    timeout <= read_hook.GIT_BUDGET_SECONDS
                    for timeout in runner.timeouts
                ),
                runner.timeouts,
            )

    def test_the_miss_path_runs_no_command_at_all(self):
        """S4: nearly every read is a miss, so a miss has to cost nothing."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()
            elsewhere = os.path.join(sandbox.path, "elsewhere", "notes.md")
            support.write(elsewhere, "# Notes\n")
            runner = support.CountingRunner()
            started = []

            def watched(*arguments, **named):
                started.append(arguments)
                raise AssertionError("the miss path started a command")

            with mock.patch("subprocess.run", watched), mock.patch(
                "subprocess.Popen", watched
            ):
                said = read_hook.run(
                    request(elsewhere), now=TODAY, runner=runner
                )

            self.assertIsNone(said)
            self.assertEqual([], runner.calls)
            self.assertEqual([], started)

    def test_a_dead_folder_in_the_record_does_not_slow_the_miss_path(self):
        """A base on a drive that has gone away is never asked about."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            machine.append_joined(
                root=os.path.join(sandbox.path, "gone-away"),
                base_id=ids.base_id_random(),
                remote=None,
            )
            elsewhere = os.path.join(sandbox.path, "elsewhere", "notes.md")
            support.write(elsewhere, "# Notes\n")
            runner = support.CountingRunner()

            self.assertIsNone(
                read_hook.run(request(elsewhere), now=TODAY, runner=runner)
            )
            self.assertEqual([], runner.calls)
            del base


# --- The wrapper -------------------------------------------------------------


class TestTheWrapper(unittest.TestCase):
    """The shell script the client really runs, probed in a temporary home."""

    def call(self, payload, home, seat=None):
        """Run the wrapper with the home override pointed at a temporary home.

        The seat folder is handed in separately when a scenario needs the one
        the sandbox already filled in, because that is where the record of
        which bases this account has joined lives.
        """
        environment = dict(os.environ)
        environment["HOME"] = home
        environment["GTM_BASE_HOME"] = seat or os.path.join(home, "seat")
        environment["CLAUDE_PLUGIN_ROOT"] = PLUGIN_DIR
        return subprocess.run(
            ["sh", WRAPPER, "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_it_is_valid_shell_and_says_nothing_about_an_ordinary_file(self):
        with support.Sandbox() as sandbox:
            checked = subprocess.run(
                ["sh", "-n", WRAPPER], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(0, checked.returncode, checked.stderr)

            ordinary = os.path.join(sandbox.path, "notes.md")
            support.write(ordinary, "# Notes\n")
            home = os.path.join(sandbox.path, "home")

            finished = self.call(request(ordinary), home)

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)
            self.assertEqual(b"", finished.stderr)

    def test_a_flagged_file_comes_back_as_one_object_the_client_can_read(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.add_change()

            finished = self.call(
                request(base.path_to()),
                os.environ["HOME"],
                seat=os.environ["GTM_BASE_HOME"],
            )

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stderr)
            payload = json.loads(finished.stdout.decode("utf-8"))
            self.assertEqual(
                "PreToolUse", payload["hookSpecificOutput"]["hookEventName"]
            )
            self.assertIn(
                "additionalContext", payload["hookSpecificOutput"]
            )
            self.assertNotIn(
                "permissionDecision", payload["hookSpecificOutput"]
            )

    def test_input_that_is_not_an_object_at_all_still_ends_well(self):
        with support.Sandbox() as sandbox:
            home = os.path.join(sandbox.path, "home")
            environment = dict(os.environ)
            environment["HOME"] = home
            environment["GTM_BASE_HOME"] = os.path.join(home, "seat")
            environment["CLAUDE_PLUGIN_ROOT"] = PLUGIN_DIR
            finished = subprocess.run(
                ["sh", WRAPPER, "claude"],
                input=b"not json at all",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)


# --- How it is declared ------------------------------------------------------


class TestHowItIsDeclared(unittest.TestCase):
    """What the plugin says about this hook, and what it still does not say."""

    def test_the_read_entry_sits_beside_the_command_check_unchanged(self):
        with open(HOOKS_PATH, encoding="utf-8") as handle:
            declared = json.load(handle)

        entries = declared["hooks"]["PreToolUse"]
        matchers = [entry.get("matcher") for entry in entries]
        self.assertIn("Read", matchers)
        self.assertIn("Bash", matchers)

        # The check that reads every command is exactly as it was. Hooks for
        # one event run in parallel, so adding one beside it changes nothing
        # about when it runs or what it answers.
        bash = entries[matchers.index("Bash")]
        self.assertEqual(
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": '"${CLAUDE_PLUGIN_ROOT}"/hooks/pre-push-gate.sh claude',
                        "timeout": 20,
                    }
                ],
            },
            bash,
        )

    def test_the_read_entry_names_the_wrapper_and_a_small_time_limit(self):
        with open(HOOKS_PATH, encoding="utf-8") as handle:
            declared = json.load(handle)
        entries = declared["hooks"]["PreToolUse"]
        matchers = [entry.get("matcher") for entry in entries]
        entry = entries[matchers.index("Read")]

        self.assertEqual(
            '"${CLAUDE_PLUGIN_ROOT}"/hooks/read-check.sh claude',
            entry["hooks"][0]["command"],
        )
        self.assertEqual("command", entry["hooks"][0]["type"])
        self.assertLessEqual(entry["hooks"][0]["timeout"], 15)
        self.assertTrue(os.access(WRAPPER, os.X_OK))

    def test_the_manifest_still_does_not_name_the_hooks_file(self):
        """A live run in 0.1.4 showed naming it stops the hooks loading."""
        with open(MANIFEST_PATH, encoding="utf-8") as handle:
            manifest = json.load(handle)

        self.assertNotIn("hooks", manifest)
        self.assertNotIn("hooks.json", json.dumps(manifest))


# --- The words ---------------------------------------------------------------


class TestTheWords(unittest.TestCase):
    def test_the_wrapper_and_the_script_are_in_plain_words(self):
        for path in (
            WRAPPER,
            os.path.join(PLUGIN_DIR, "scripts", "read_check.py"),
            os.path.join(support.LIB_DIR, "gtmbase", "read_hook.py"),
        ):
            with self.subTest(path=os.path.basename(path)):
                plain_language.assert_plain(self, path)

    def test_the_one_sentence_it_adds_is_registered_and_plain(self):
        self.assertIn(
            ("moment", "PAUSE_BEFORE_USING"), plain_language.PYTHON_SENTENCES
        )
        self.assertEqual(
            [], plain_language.find_banned(moment.PAUSE_BEFORE_USING)
        )
        self.assertEqual(
            [], plain_language.find_dashes(moment.PAUSE_BEFORE_USING)
        )


if __name__ == "__main__":
    unittest.main()
