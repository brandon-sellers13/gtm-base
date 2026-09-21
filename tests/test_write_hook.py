"""The check that runs as a file is about to be written.

Finding A1 from Astra's release A review and finding H1 from the second
reviewer are the same finding: the check before a command reads only commands,
so one plain write over one small file in GTM Base's own records folder undoes
what a person agreed to. Every scenario below writes the file the reviewers
wrote and then asks this check about it.

Every scenario builds a real base in a temporary folder with a temporary home,
and the wrapper is only ever run with the home override pointed at one of
those, so nothing here can reach the person's own folders.
"""

import json
import os
import subprocess
import unittest
from unittest import mock

import plain_language
import support

from gtmbase import approve_local, ids, machine, marker, paths, state, write_hook

PLUGIN_DIR = support.PLUGIN_DIR
WRAPPER = os.path.join(PLUGIN_DIR, "hooks", "write-check.sh")
SCRIPT = os.path.join(PLUGIN_DIR, "scripts", "write_check.py")
HOOKS_PATH = os.path.join(PLUGIN_DIR, "hooks", "hooks.json")

SESSION = "sess-1"


def request(path, tool="Write", cwd=None, key="file_path", extra=None):
    """One request shaped the way the client sends one before a file write."""
    tool_input = {key: path}
    tool_input.update(extra or {})
    payload = {
        "session_id": SESSION,
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
    }
    if cwd is not None:
        payload["cwd"] = cwd
    return payload


def run_skill_script(skill, name, argv, cwd):
    """Run one skill's own script the way the person runs it, and read it back.

    The scripts are the real entry points, and the words a person typed reach
    them through a file rather than a command line, so a scenario about what
    the assistant writes runs them rather than calling the library the way a
    well behaved caller would.
    """
    import importlib.util
    import io as _io
    from contextlib import redirect_stderr, redirect_stdout

    path = os.path.join(PLUGIN_DIR, "skills", skill, "scripts", name)
    spec = importlib.util.spec_from_file_location("gtmbase_written_" + skill, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    here = os.getcwd()
    out, err = _io.StringIO(), _io.StringIO()
    os.chdir(cwd)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = module.main(argv)
    finally:
        os.chdir(here)
    return code, out.getvalue() + err.getvalue()


def denied(answer):
    """Whether one answer is the refusal, read the way the client reads it."""
    if not answer:
        return False
    return answer["hookSpecificOutput"].get("permissionDecision") == "deny"


class Base(object):
    """A joined base, the same shape every other test builds one in."""

    def __init__(self, sandbox, name="local", joined=True):
        from gtmbase import constants

        self.root = os.path.join(sandbox.path, name)
        self.base_id = ids.base_id_random()
        support.make_base(self.root, base_id=self.base_id)
        support.write(
            os.path.join(self.root, constants.ALLOWLIST_PATH), "# ours\n"
        )
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", "a local base"], cwd=self.root)
        if joined:
            machine.append_joined(root=self.root, base_id=self.base_id, remote=None)
            state.update_seat(self.base_id, session_id=SESSION)


# --- The files the reviewers wrote -------------------------------------------


class TestTheRecordsTheReviewersForged(unittest.TestCase):
    """One file each, named by the reproduction that wrote it."""

    def check(self, path):
        return denied(write_hook.run(request(path)))

    def test_the_account_record_of_joined_bases_is_refused(self):
        """Emptying it made a joined base read as no base at all."""
        with support.Sandbox() as sandbox:
            Base(sandbox)

            self.assertTrue(self.check(paths.machine_state_path()))

    def test_this_seats_own_record_about_a_base_is_refused(self):
        """A forged first backup review turned a refused send into an allowed one."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            seat_file = os.path.join(paths.seat_dir(base.base_id), state.SEAT_FILE)

            self.assertTrue(self.check(seat_file))

    def test_the_record_of_reading_the_persons_own_documents_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            marker.write_sources_read_marker(SESSION)

            self.assertTrue(self.check(marker.marker_path()))

    def test_the_record_of_what_was_put_off_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(paths.seat_dir(base.base_id), state.DISMISSALS_FILE)

            self.assertTrue(self.check(path))

    def test_the_log_of_what_was_asked_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(paths.seat_dir(base.base_id), state.ASKED_LOG_FILE)

            self.assertTrue(self.check(path))

    def test_the_note_behind_a_local_approval_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(
                paths.seat_dir(base.base_id), approve_local.JOURNAL_FILE
            )

            self.assertTrue(self.check(path))

    def test_the_consent_records_of_a_setup_run_are_refused(self):
        from gtmbase import join_flow

        with support.Sandbox() as sandbox:
            Base(sandbox)
            run_id = join_flow.new_run()
            path = os.path.join(
                join_flow.scratch_dir(run_id), join_flow.CONSENT_FILE
            )

            self.assertTrue(self.check(path))

    def test_a_file_that_is_not_there_yet_is_refused_just_the_same(self):
        """Nothing is there to read, and the write is what has to be stopped."""
        with support.Sandbox() as sandbox:
            Base(sandbox)
            path = os.path.join(paths.seat_home_path(), "invented.json")

            self.assertTrue(self.check(path))


class TestABasesOwnFolders(unittest.TestCase):
    def check(self, path):
        return denied(write_hook.run(request(path)))

    def test_the_safeguard_the_base_runs_before_a_send_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(base.root, ".git", "hooks", "pre-push")

            self.assertTrue(self.check(path))

    def test_a_settings_file_in_the_bases_assistant_folder_is_refused(self):
        """It could point the records folder somewhere else through a setting."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(base.root, ".claude", "settings.json")

            self.assertTrue(self.check(path))

    def test_a_base_this_account_never_joined_is_protected_too(self):
        """Changed for finding N6 of the 2026-09-20 verification round.

        This used to say a base nobody had joined was left alone, because the
        protection was read off this account's list of joined bases. That list
        is a file, and a write that empties it took the protection with it, so
        the shape of the folder decides now and a folder shaped like a base is
        protected whether or not this account has joined it. Nothing is lost by
        that: the folders in question are the ones the safeguard and the
        assistant's own settings live in, and nobody has a reason to write
        either of them with a file-writing tool.
        """
        with support.Sandbox() as sandbox:
            base = Base(sandbox, joined=False)
            path = os.path.join(base.root, "." + "g" + "it", "hooks", "pre-push")

            self.assertTrue(self.check(path))


# --- What it must never refuse -----------------------------------------------


class TestWhatItLeavesAlone(unittest.TestCase):
    """Nearly every write on this computer, said in one word: nothing."""

    def check(self, path, **named):
        return write_hook.run(request(path, **named))

    def test_a_context_file_in_a_joined_base_is_left_alone(self):
        """A person hand edits these, and so may the assistant."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            path = os.path.join(base.root, "context", "strategy", "icp.md")

            self.assertIsNone(self.check(path))

    def test_the_map_and_every_other_file_in_the_base_are_left_alone(self):
        from gtmbase import constants

        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            for relative in (
                constants.MAP_PATH,
                constants.ALLOWLIST_PATH,
                "work/changes/anything.md",
                "readme.md",
            ):
                with self.subTest(relative=relative):
                    path = os.path.join(base.root, relative.replace("/", os.sep))
                    self.assertIsNone(self.check(path))

    def test_a_file_anywhere_else_on_the_computer_is_left_alone(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            path = os.path.join(sandbox.path, "somewhere", "notes.md")

            self.assertIsNone(self.check(path))

    def test_the_drafts_a_setup_run_asks_for_are_left_alone(self):
        """They were moved out of the records folder so this stays true."""
        from gtmbase import drafting, join_flow

        with support.Sandbox() as sandbox:
            Base(sandbox)
            run_id = join_flow.new_run()
            path = join_flow.draft_path(run_id, drafting.STEP_ICP)

            self.assertIsNone(self.check(path))
            self.assertFalse(
                path.startswith(paths.seat_home_path() + os.sep), path
            )

    def test_another_tool_is_somebody_elses_business(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            self.assertIsNone(
                self.check(paths.machine_state_path(), tool="Bash")
            )

    def test_a_call_naming_no_file_says_nothing(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            payload = {"tool_name": "Write", "tool_input": {"content": "hello"}}

            self.assertIsNone(write_hook.run(payload))

    def test_what_would_be_written_is_never_read_as_a_path(self):
        """A file whose words spell a record is still just a file of words."""
        with support.Sandbox() as sandbox:
            Base(sandbox)
            ordinary = os.path.join(sandbox.path, "notes.md")

            self.assertIsNone(
                self.check(
                    ordinary,
                    extra={"content": paths.machine_state_path()},
                )
            )


# --- The ways a path can be spelled ------------------------------------------


class TestTheWaysAPathCanBeSpelled(unittest.TestCase):
    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def test_a_path_written_relative_to_the_folder_the_session_is_in(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            seat = paths.seat_home()
            parent = os.path.dirname(seat)

            self.assertTrue(
                self.check(
                    os.path.join(os.path.basename(seat), "machine.json"), cwd=parent
                )
            )

    def test_a_path_that_climbs_back_in_with_two_dots(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            seat = paths.seat_home()

            self.assertTrue(
                self.check(os.path.join(seat, "bases", "..", "machine.json"))
            )

    def test_a_path_that_reaches_the_folder_through_a_link(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            seat = paths.seat_home()
            link = os.path.join(sandbox.path, "shortcut")
            os.symlink(seat, link)

            self.assertTrue(self.check(os.path.join(link, "machine.json")))

    def test_a_path_written_in_other_letter_case(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            seat = paths.seat_home()
            spelled = os.path.join(
                os.path.dirname(seat), os.path.basename(seat).upper(), "machine.json"
            )

            self.assertTrue(self.check(spelled))

    def test_a_path_written_with_the_home_sign(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            # The records folder is the one the override names, so a name
            # written with the home sign is only the same folder when it
            # resolves to it. This asks about the base's own folders instead,
            # which do sit under the temporary home in this scenario.
            base = Base(sandbox, name="second")
            inside = os.path.join(base.root, ".claude", "settings.json")

            self.assertTrue(self.check(inside))

    def test_every_file_writing_tool_is_covered(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            for tool in write_hook.TOOL_NAMES:
                with self.subTest(tool=tool):
                    self.assertTrue(
                        self.check(paths.machine_state_path(), tool=tool)
                    )

    def test_a_notebook_path_is_read_although_it_is_not_documented(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            self.assertTrue(
                self.check(
                    paths.machine_state_path(),
                    tool="NotebookEdit",
                    key="notebook_path",
                )
            )


# --- What the check costs ----------------------------------------------------


class TestWhatItCosts(unittest.TestCase):
    def test_the_miss_path_runs_no_command_at_all(self):
        """Nearly every write is a miss, so a miss has to cost nothing."""
        with support.Sandbox() as sandbox:
            Base(sandbox)
            elsewhere = os.path.join(sandbox.path, "elsewhere", "notes.md")
            support.write(elsewhere, "# Notes\n")
            started = []

            def watched(*arguments, **named):
                started.append(arguments)
                raise AssertionError("the miss path started a command")

            with mock.patch("subprocess.run", watched), mock.patch(
                "subprocess.Popen", watched
            ):
                said = write_hook.run(request(elsewhere))

            self.assertIsNone(said)
            self.assertEqual([], started)

    def test_the_refusing_path_runs_no_command_either(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            def watched(*arguments, **named):
                raise AssertionError("the check started a command")

            with mock.patch("subprocess.run", watched), mock.patch(
                "subprocess.Popen", watched
            ):
                said = write_hook.run(request(paths.machine_state_path()))

            self.assertTrue(denied(said))

    def test_a_dead_folder_in_the_record_does_not_slow_the_miss_path(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            machine.append_joined(
                root=os.path.join(sandbox.path, "gone-away"),
                base_id=ids.base_id_random(),
                remote=None,
            )
            elsewhere = os.path.join(sandbox.path, "elsewhere", "notes.md")

            self.assertIsNone(write_hook.run(request(elsewhere)))


# --- The product's own flows, with the check running -------------------------


class TestTheFlowsThatWriteFiles(unittest.TestCase):
    """Four real runs through the skills' own scripts, with the check asked.

    A check that refuses what the product itself needs to do is worse than no
    check, so each of these drives the real scripts and asks this check about
    every file the skills tell the assistant to write along the way. Nothing
    is stood in for: the scripts print the paths and the scenario writes to
    them, which is exactly what the assistant does.
    """

    def allowed(self, path):
        self.assertIsNone(
            write_hook.run(request(path)),
            "the check refused a file the product itself writes: %s" % path,
        )

    def words_file(self, sandbox, name, text, key=None):
        """Words somebody typed, in the file a script itself handed out.

        This used to be a file of the test's own anywhere in the sandbox.
        Finding V6 of the 2026-09-20 verification round: the readers took any
        path at all, so the scripts choose where words go now, and the check
        is asked about the path they chose before anything is written to it.
        """
        from gtmbase import wordsfile

        del sandbox
        kind = name.replace(".txt", "")
        wordsfile.ensure_words_dir(key)
        path = wordsfile.new_words_path(key, kind)
        self.allowed(path)
        support.write(path, text)
        return path

    def test_a_whole_setup_run_and_its_closing(self):
        import test_join_setup_flow as join_tests

        with support.Sandbox() as sandbox:
            setup = join_tests.SetupRun(sandbox)
            setup.agree_to_the_list()

            # The one file the assistant writes at each drafting step is the
            # draft, at the path the script prints.
            for step, text in (
                ("icp", join_tests.captured("icp.md")),
                ("positioning", join_tests.captured("positioning.md")),
            ):
                from gtmbase import join_flow

                self.allowed(join_flow.draft_path(setup.run, step))
                setup.approve(step, text)

            self.assertIsNotNone(setup.root)

            # And the closing, with the words they said about what got in the
            # way passed through a file.
            got_in_the_way = self.words_file(
                sandbox,
                "got-in-the-way.txt",
                "The folder took a while to find.\n",
                key=setup.run,
            )
            closed = setup.close(got_in_the_way=support.read(got_in_the_way))
            self.assertTrue(closed.closing)

    def test_a_hand_edit_with_a_reason_through_the_script(self):
        import test_approve_local as approve_tests

        with support.Sandbox() as sandbox:
            from gtmbase import compose_proposal

            root, base_id = approve_tests.local_base(sandbox)
            icp = os.path.join(root, approve_tests.ICP)

            # The person edits their own context file by hand, and the check
            # has to leave that alone whoever makes the edit.
            self.allowed(icp)
            support.write(
                icp,
                support.read(icp).replace(
                    "Companies of any size.",
                    "Companies of twenty to two hundred people.",
                ),
            )

            from gtmbase import state as state_module

            seat, _problems = state_module.load_seat(base_id)
            session = seat.get("session_id") or base_id
            source = self.words_file(
                sandbox,
                "source.txt",
                "The board deck said so, slide four.\n",
                key=session,
            )
            what_changed = self.words_file(
                sandbox,
                "what-changed.txt",
                "We moved up market because the small ones churned.\n",
                key=session,
            )

            code, printed = run_skill_script(
                "propose-change",
                "propose.py",
                [
                    "--local-edit",
                    "--source-file",
                    source,
                    "--what-changed-file",
                    what_changed,
                    "--records-a-change",
                ],
                root,
            )

            # The base has no shared copy, so the run ends by handing the
            # prepared change to the owner to approve here, which is the
            # ending this base is supposed to reach.
            self.assertIn("approve it here", printed)
            waiting = os.listdir(
                os.path.join(root, compose_proposal.constants.PROPOSALS_PENDING_DIR)
            )
            self.assertEqual(1, len(waiting), printed)
            del code

    def test_a_confirm_with_a_reason_through_the_script(self):
        import test_moment_of_use as moment_tests

        with support.Sandbox() as sandbox:
            from gtmbase import confirm

            base = moment_tests.Base(sandbox)
            base.add_change()
            item = [
                line for line in base.review().review if line.path == moment_tests.ICP
            ][0]

            from gtmbase import state as state_module

            seat, _problems = state_module.load_seat(base.base_id)
            reason = self.words_file(
                sandbox,
                "reason.txt",
                "We moved up market, so this is out of date now.\n",
                key=seat.get("session_id") or base.base_id,
            )

            code, printed = run_skill_script(
                "confirm",
                "confirm.py",
                [
                    "--question",
                    item.question_id,
                    "--answer",
                    "no",
                    "--reason-file",
                    reason,
                ],
                base.root,
            )

            self.assertEqual(0, code, printed)
            waiting = os.listdir(
                os.path.join(base.root, confirm.constants.PROPOSALS_PENDING_DIR)
            )
            self.assertEqual(1, len(waiting), printed)


# --- The wrapper -------------------------------------------------------------


class TestTheWrapper(unittest.TestCase):
    """The shell script the client really runs, probed in a temporary home."""

    def call(self, payload, home, seat=None):
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
            home = os.path.join(sandbox.path, "home")

            finished = self.call(request(ordinary), home)

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)
            self.assertEqual(b"", finished.stderr)

    def test_a_refused_write_comes_back_as_the_shape_the_client_reads(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            finished = self.call(
                request(paths.machine_state_path()),
                os.environ["HOME"],
                seat=os.environ["GTM_BASE_HOME"],
            )

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stderr)
            payload = json.loads(finished.stdout.decode("utf-8"))
            said = payload["hookSpecificOutput"]
            self.assertEqual("PreToolUse", said["hookEventName"])
            self.assertEqual("deny", said["permissionDecision"])
            self.assertEqual(write_hook.REFUSED, said["permissionDecisionReason"])

    def test_it_exits_zero_on_nonsense(self):
        with support.Sandbox() as sandbox:
            home = os.path.join(sandbox.path, "home")
            environment = dict(os.environ)
            environment["HOME"] = home
            environment["GTM_BASE_HOME"] = os.path.join(home, "seat")
            environment["CLAUDE_PLUGIN_ROOT"] = PLUGIN_DIR

            finished = subprocess.run(
                ["sh", WRAPPER, "claude"],
                input=b"not an object at all",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)


# --- What is declared --------------------------------------------------------


class TestWhatIsDeclared(unittest.TestCase):
    def test_the_entry_names_every_file_writing_tool_and_the_wrapper(self):
        with open(HOOKS_PATH, encoding="utf-8") as handle:
            declared = json.load(handle)
        entries = declared["hooks"]["PreToolUse"]
        matchers = [entry.get("matcher") for entry in entries]
        wanted = "|".join(write_hook.TOOL_NAMES)

        self.assertIn(wanted, matchers)
        entry = entries[matchers.index(wanted)]
        self.assertEqual(
            '"${CLAUDE_PLUGIN_ROOT}"/hooks/write-check.sh claude',
            entry["hooks"][0]["command"],
        )
        self.assertEqual("command", entry["hooks"][0]["type"])
        self.assertLessEqual(entry["hooks"][0]["timeout"], 15)
        self.assertTrue(os.access(WRAPPER, os.X_OK))


# --- The words ---------------------------------------------------------------


class TestTheWords(unittest.TestCase):
    def test_the_wrapper_and_the_script_are_in_plain_words(self):
        for path in (
            WRAPPER,
            SCRIPT,
            os.path.join(support.LIB_DIR, "gtmbase", "write_hook.py"),
        ):
            with self.subTest(path=os.path.basename(path)):
                plain_language.assert_plain(self, path)

    def test_the_one_sentence_it_adds_is_registered_and_plain(self):
        self.assertIn(("write_hook", "REFUSED"), plain_language.PYTHON_SENTENCES)
        self.assertEqual([], plain_language.find_banned(write_hook.REFUSED))
        self.assertEqual([], plain_language.find_dashes(write_hook.REFUSED))

    def test_the_refusal_names_no_folder_and_no_identifier(self):
        self.assertNotIn("/", write_hook.REFUSED)
        self.assertNotIn(".gtm", write_hook.REFUSED)


# --- V1, V2 and N6 of the 2026-09-20 verification round ----------------------


class TestThePathIsTheOneTheWriterWouldUse(unittest.TestCase):
    """V1. The check used to tidy the name up and then check the tidy one."""

    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def test_a_link_whose_name_begins_with_a_space_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            link = os.path.join(sandbox.path, " alias")
            os.symlink(paths.seat_home_path(), link)

            self.assertTrue(
                self.check(" alias/machine.json", cwd=sandbox.path),
                "the name was tidied up and the tidy one was checked",
            )

    def test_the_records_folder_itself_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            self.assertTrue(self.check(paths.seat_home_path()))

    def test_the_version_control_entry_itself_is_refused(self):
        """A working folder keeps that name as a file, not as a folder."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)

            self.assertTrue(self.check(os.path.join(base.root, "." + "git")))

    def test_a_version_control_entry_that_is_a_file_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox, name="worktree", joined=False)
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere)
            import shutil

            shutil.rmtree(os.path.join(base.root, "." + "git"))
            support.write(
                os.path.join(base.root, "." + "git"), "gitdir: %s\n" % elsewhere
            )
            machine.append_joined(
                root=base.root, base_id=base.base_id, remote=None
            )

            self.assertTrue(self.check(os.path.join(base.root, "." + "git")))

    def test_a_link_out_of_the_version_control_folder_is_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            outside = os.path.join(sandbox.path, "outside")
            os.makedirs(outside)
            support.write(os.path.join(outside, "config"), "x\n")
            link = os.path.join(base.root, "." + "git", "elsewhere")
            os.symlink(outside, link)

            self.assertTrue(self.check(os.path.join(link, "config")))


class TestTheGuardCannotBeTurnedOff(unittest.TestCase):
    """V2. Plugin code sat outside every protected place."""

    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def installed(self, sandbox):
        """A copy of the plugin standing where the client installed one."""
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(PLUGIN_DIR, root)
        return root

    def test_the_installed_guard_itself_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            root = self.installed(sandbox)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": root}):
                target = os.path.join(root, "lib", "gtmbase", "write_hook.py")

                self.assertTrue(self.check(target))

    def test_the_installed_gate_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            root = self.installed(sandbox)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": root}):
                target = os.path.join(root, "lib", "gtmbase", "gate.py")

                self.assertTrue(self.check(target))

    def test_the_declaration_that_loads_the_guard_is_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            root = self.installed(sandbox)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": root}):
                target = os.path.join(root, "hooks", "hooks.json")

                self.assertTrue(self.check(target))

    def test_a_source_checkout_somewhere_else_is_still_writable(self):
        """Working on the plugin must go on working while a copy is installed."""
        with support.Sandbox() as sandbox:
            Base(sandbox)
            root = self.installed(sandbox)
            import shutil

            checkout = os.path.join(sandbox.path, "checkout", "gtm-base")
            os.makedirs(os.path.dirname(checkout), exist_ok=True)
            shutil.copytree(PLUGIN_DIR, checkout)
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": root}):
                mine = os.path.join(checkout, "lib", "gtmbase", "write_hook.py")
                theirs = os.path.join(root, "lib", "gtmbase", "write_hook.py")

                self.assertFalse(self.check(mine))
                self.assertTrue(self.check(theirs))


class TestABasesOwnFoldersWithoutTheList(unittest.TestCase):
    """N6. The protection leaned on the account record, which a write can empty."""

    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def test_the_bases_own_settings_are_refused_with_the_list_emptied(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            support.write(paths.machine_state_path(), "{}")
            target = os.path.join(base.root, "." + "git", "config")

            self.assertTrue(self.check(target))

    def test_a_folder_deep_inside_a_base_is_still_protected(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            support.write(paths.machine_state_path(), "{}")
            target = os.path.join(base.root, "." + "claude", "settings.json")

            self.assertTrue(self.check(target))

    def test_the_settings_of_the_folder_the_base_belongs_with_are_refused(self):
        """That folder is the one a session is actually opened in."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            material = os.path.join(sandbox.path, "marketing")
            os.makedirs(material)
            machine.link_content(base.base_id, material)
            target = os.path.join(material, "." + "claude", "settings.json")

            self.assertTrue(self.check(target))

    def test_an_ordinary_repository_is_left_alone(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            ordinary = os.path.join(sandbox.path, "ordinary")
            os.makedirs(ordinary)
            support.git(["init", "-q", "-b", "main"], cwd=ordinary)
            target = os.path.join(ordinary, "." + "git", "config")

            self.assertFalse(self.check(target))


class TestTheWrapperWhenThePythonHalfCannotLoad(unittest.TestCase):
    """V2b. A broken library used to mean every write went through unlooked at."""

    def a_broken_copy(self, sandbox):
        """The plugin as it stands after somebody has written over its code."""
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(PLUGIN_DIR, root)
        support.write(
            os.path.join(root, "lib", "gtmbase", "write_hook.py"),
            "this is not python(\n",
        )
        return root

    def call(self, payload, root):
        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = root
        return subprocess.run(
            ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_a_write_naming_a_protected_place_is_refused(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            for named in (
                os.path.join(paths.seat_home_path(), "machine.json"),
                os.path.join(root, "lib", "gtmbase", "gate.py"),
                os.path.join(sandbox.path, "base", "." + "g" + "it", "config"),
                os.path.join(
                    sandbox.path, "base", "." + "claude", "settings.json"
                ),
            ):
                finished = self.call(request(named), root)

                self.assertEqual(0, finished.returncode, named)
                self.assertIn(b'"deny"', finished.stdout, named)
                payload = json.loads(finished.stdout.decode("utf-8"))
                self.assertEqual(
                    write_hook.COULD_NOT_CHECK,
                    payload["hookSpecificOutput"]["permissionDecisionReason"],
                )

    def test_an_ordinary_write_is_still_allowed(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)

            for named in (
                os.path.join(sandbox.path, "notes.md"),
                os.path.join(sandbox.path, "project", "src", "main.py"),
            ):
                finished = self.call(request(named), root)

                self.assertEqual(0, finished.returncode, named)
                self.assertEqual(b"", finished.stdout, named)

    def test_the_wrapper_says_the_same_words_the_library_holds(self):
        with open(WRAPPER, encoding="utf-8") as handle:
            text = handle.read()

        self.assertIn(write_hook.COULD_NOT_CHECK, text)


if __name__ == "__main__":
    unittest.main()
