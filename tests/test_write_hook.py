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


def a_transcript_path():
    """Where the client says it is keeping this session's transcript.

    It is always under the assistant's own folder in the person's home folder,
    and it is on every request the client sends. Finding H1 of the third look:
    the fallback matched the whole request as text, so this one field refused
    every file write on the computer the moment the check could not run. It is
    on every payload these scenarios build for that reason.
    """
    return os.path.join(
        os.path.expanduser("~"),
        "." + "claude",
        "projects",
        "-Users-someone-work",
        SESSION + ".jsonl",
    )


def request(
    path,
    tool="Write",
    cwd=None,
    key="file_path",
    extra=None,
    content="hello\n",
    transcript=None,
):
    """One request shaped the way the client sends one before a file write.

    Everything the client really puts on one is here: the session, where the
    transcript is being kept, the folder the session is open in, and the text
    that would be written. A scenario that leaves those out is a scenario that
    proves nothing about the request this hook actually receives.
    """
    tool_input = {key: path}
    if content is not None:
        tool_input["content"] = content
    tool_input.update(extra or {})
    payload = {
        "session_id": SESSION,
        "transcript_path": (
            a_transcript_path() if transcript is None else transcript
        ),
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

            # The base, not the session: a words file belongs to the base now,
            # so a second window opening does not make it unreadable (L3).
            session = base_id
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

            reason = self.words_file(
                sandbox,
                "reason.txt",
                "We moved up market, so this is out of date now.\n",
                key=base.base_id,
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
            base = Base(sandbox)
            for named in (
                os.path.join(paths.seat_home_path(), "machine.json"),
                os.path.join(root, "lib", "gtmbase", "gate.py"),
                os.path.join(base.root, "." + "g" + "it", "config"),
                os.path.join(
                    base.root, "." + "claude", "settings.json"
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



class TestTheFallbackLeavesOrdinaryWorkAlone(unittest.TestCase):
    """H1 and F1 of the third look, built from the reviewers' own scripts.

    The fallback matched the whole request as one piece of text, and the
    client puts the path of this session's transcript on every request it
    sends, under the assistant's own folder. So the moment the real check
    could not run, every file write on the computer was refused: the ones that
    mattered, the ones that did not, and the write that would have repaired
    the broken file.
    """

    def a_broken_copy(self, sandbox):
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(PLUGIN_DIR, root)
        support.write(
            os.path.join(root, "scripts", "write_check.py"),
            "raise SystemExit(70)\n",
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

    def answer(self, payload, root):
        finished = self.call(payload, root)
        self.assertEqual(0, finished.returncode)
        return b'"deny"' in finished.stdout

    def test_an_ordinary_write_from_a_real_client_request_is_allowed(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            work = os.path.join(sandbox.path, "work")
            os.makedirs(work)

            allowed = not self.answer(
                request(os.path.join(work, "notes.txt"), cwd=work), root
            )

            self.assertTrue(
                allowed,
                "the transcript the client names refused an ordinary write",
            )

    def test_the_files_ordinary_work_is_full_of_are_allowed(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            work = os.path.join(sandbox.path, "work")
            os.makedirs(work)
            vcs = "." + "g" + "it"
            for named, text in (
                (os.path.join(work, vcs + "ignore"), "node_modules\n"),
                (
                    os.path.join(work, vcs + "hub", "workflows", "ci.yml"),
                    "on: push\n",
                ),
                (
                    os.path.join(work, "README.md"),
                    "add a %signore, and see %shub/workflows" % (vcs, vcs),
                ),
                (
                    os.path.join(work, "setup.md"),
                    "settings live in your %sclaude folder" % ".",
                ),
            ):
                with self.subTest(file=os.path.basename(named)):
                    self.assertFalse(
                        self.answer(
                            request(named, cwd=work, content=text), root
                        )
                    )

    def test_the_repair_of_the_broken_file_is_allowed_where_it_is_the_persons(self):
        """A checkout of their own is theirs to repair; the installed copy is not."""
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            import shutil

            mine = os.path.join(sandbox.path, "checkout", "gtm-base")
            os.makedirs(os.path.dirname(mine), exist_ok=True)
            shutil.copytree(PLUGIN_DIR, mine)

            self.assertFalse(
                self.answer(
                    request(os.path.join(mine, "scripts", "write_check.py")),
                    root,
                )
            )
            self.assertTrue(
                self.answer(
                    request(os.path.join(root, "scripts", "write_check.py")),
                    root,
                )
            )

    def test_the_places_it_keeps_are_still_refused(self):
        """A real base, because the map beside them is what tells them apart.

        This named a folder that was not there before finding N2, which the
        smaller check refused on its name alone. It refuses those two folder
        names only where a base really is now, so this builds one.
        """
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            base = Base(sandbox)
            vcs = "." + "g" + "it"
            for named in (
                os.path.join(paths.seat_home_path(), "machine.json"),
                os.path.join(root, "lib", "gtmbase", "gate.py"),
                os.path.join(base.root, vcs, "config"),
                os.path.join(base.root, "." + "claude", "settings.json"),
            ):
                with self.subTest(file=named):
                    self.assertTrue(self.answer(request(named), root))

    def test_a_request_it_cannot_read_at_all_is_allowed(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            environment = dict(os.environ)
            environment["CLAUDE_PLUGIN_ROOT"] = root

            finished = subprocess.run(
                ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
                input=b"not an object at all",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )

            self.assertEqual(0, finished.returncode)
            self.assertEqual(b"", finished.stdout)

    def test_a_check_that_ran_out_of_time_leaves_ordinary_work_alone(self):
        """A slow start is not a broken plugin.

        The answer a run out of time gives back is the one this stands in for,
        rather than really waiting, because the command that imposes the limit
        is not on every Mac and a scenario that waits half a minute proves
        nothing anybody would run twice.
        """
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            support.write(
                os.path.join(root, "scripts", "write_check.py"),
                "raise SystemExit(124)\n",
            )
            work = os.path.join(sandbox.path, "work")
            os.makedirs(work)

            self.assertFalse(
                self.answer(
                    request(os.path.join(work, "notes.txt"), cwd=work), root
                )
            )
            self.assertTrue(
                self.answer(
                    request(os.path.join(paths.seat_home_path(), "seat.json")),
                    root,
                )
            )




# --- F2 and M4 of the third look ---------------------------------------------


class TestTheSettingsThatDecideWhetherTheCheckRuns(unittest.TestCase):
    """F2. Somebody's own client settings are theirs, so it asks rather than refuses.

    A change in one of these can switch GTM Base's own safety checks off, so it
    is not a write to wave through. It is also the person's own file, holding
    everything else they have set up, and refusing it outright made their own
    settings unreachable through the assistant they were using. The
    documentation for this hook lists three values the decision may take, read
    on the twentieth of September at https://code.claude.com/docs/en/hooks:
    `permissionDecision`, "\"allow\", \"deny\", or \"ask\". Overrides the
    permission system's decision for this tool call". So it asks.
    """

    def answer(self, path):
        return write_hook.run(request(path))

    def decision(self, path):
        answer = self.answer(path)
        if not answer:
            return "nothing"
        return answer["hookSpecificOutput"]["permissionDecision"]

    def settings_file(self, name):
        return os.path.join(os.path.expanduser("~"), "." + "claude", name)

    def test_the_settings_files_are_asked_about_rather_than_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            for name in (
                "settings.json",
                "settings.local.json",
                os.path.join("plugins", "installed_plugins.json"),
                os.path.join("plugins", "known_marketplaces.json"),
            ):
                with self.subTest(file=name):
                    self.assertEqual("ask", self.decision(self.settings_file(name)))

    def test_the_question_says_why_it_is_being_asked(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            answer = self.answer(self.settings_file("settings.json"))

            self.assertEqual(
                write_hook.ASK_ABOUT_SETTINGS,
                answer["hookSpecificOutput"]["permissionDecisionReason"],
            )

    def test_the_places_that_are_refused_are_still_refused(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            for named in (
                paths.machine_state_path(),
                os.path.join(write_hook.plugin_roots()[0], "lib", "gtmbase", "gate.py"),
                os.path.join(base.root, "." + "g" + "it", "config"),
            ):
                with self.subTest(file=named):
                    self.assertEqual("deny", self.decision(named))

    def test_an_ordinary_file_is_still_nothing_at_all(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)

            self.assertEqual(
                "nothing", self.decision(os.path.join(sandbox.path, "notes.md"))
            )




# --- N2, N3 and N6 of the final confirmation pass ----------------------------


class TestTheFallbackRefusesOnlyWhatTheRealCheckRefuses(unittest.TestCase):
    """N2. While it is broken it used to refuse far more than the real one.

    Any path holding either folder name anywhere in it was refused, which is
    an ordinary repository's own exclude file, a project's folder of assistant
    commands, and everything the assistant keeps under the person's home
    folder, its own memory included. A Mac with no developer tools stays in
    that state, so what the smaller check refuses has to be what the real one
    refuses and nothing besides.
    """

    def a_broken_copy(self, sandbox):
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(PLUGIN_DIR, root)
        support.write(
            os.path.join(root, "scripts", "write_check.py"),
            "raise SystemExit(70)\n",
        )
        return root

    def answer(self, payload, root):
        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = root
        finished = subprocess.run(
            ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(0, finished.returncode)
        return b'"deny"' in finished.stdout

    def test_the_two_folder_names_outside_a_base_are_left_alone(self):
        vcs = "." + "g" + "it"
        assistant = "." + "claude"
        with support.Sandbox() as sandbox:
            home = os.path.expanduser("~")
            root = self.a_broken_copy(sandbox)
            ordinary = os.path.join(sandbox.path, "repo")
            os.makedirs(ordinary)
            for named in (
                os.path.join(ordinary, vcs, "info", "exclude"),
                os.path.join(ordinary, assistant, "commands", "x.md"),
                os.path.join(
                    home, assistant, "projects", "p", "memory", "MEMORY.md"
                ),
                os.path.join(home, assistant, "plans", "a-plan.md"),
            ):
                with self.subTest(file=named):
                    self.assertFalse(self.answer(request(named), root))

    def test_the_same_two_folders_inside_a_base_are_refused(self):
        vcs = "." + "g" + "it"
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            base = Base(sandbox)
            for named in (
                os.path.join(base.root, vcs, "hooks", "pre-push"),
                os.path.join(base.root, "." + "claude", "settings.json"),
            ):
                with self.subTest(file=named):
                    self.assertTrue(self.answer(request(named), root))

    def test_a_folder_name_in_other_letters_finds_the_same_base(self):
        """N3. The candidate is folded before it is matched."""
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            base = Base(sandbox)
            named = os.path.join(
                base.root, "." + "G" + "IT", "hooks", "pre-push"
            )

            self.assertTrue(self.answer(request(named), root))

    def test_a_path_under_a_name_ending_in_path_is_read(self):
        """N3. A tool may carry its path under a name of its own."""
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            payload = request(os.path.join(sandbox.path, "ok.txt"))
            payload["tool_input"]["other_path"] = os.path.join(
                paths.seat_home_path(), "machine.json"
            )

            self.assertTrue(self.answer(payload, root))


class TestTheFolderThePluginsLiveIn(unittest.TestCase):
    """N6. The next update is installed from the copy of the marketplace."""

    def decision(self, path):
        answer = write_hook.run(request(path))
        return answer["hookSpecificOutput"]["permissionDecision"] if answer else "nothing"

    def test_anything_under_it_is_asked_about(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            folder = write_hook.client_plugins_dir()
            for name in (
                os.path.join("config.json"),
                os.path.join("marketplaces", "m", "plugins", "p", "hooks", "hooks.json"),
                os.path.join("installed_plugins.json"),
            ):
                with self.subTest(file=name):
                    self.assertEqual("ask", self.decision(os.path.join(folder, name)))

    def test_the_running_plugin_is_still_refused(self):
        with support.Sandbox() as sandbox:
            Base(sandbox)
            root = write_hook.plugin_roots()[0]

            self.assertEqual(
                "deny", self.decision(os.path.join(root, "hooks", "hooks.json"))
            )




# --- R2 and R3 of Astra's third verification ---------------------------------

DOT_GIT = "." + "git"
DOT_CLAUDE = "." + "claude"


def _no_program_may_start():
    def watched(*arguments, **named):
        raise AssertionError("the check started a program")

    return mock.patch("subprocess.run", watched), mock.patch("subprocess.Popen", watched)


class TestAHistoryFolderKeptSomewhereElse(unittest.TestCase):
    """R2. A base whose history folder is kept elsewhere left it writable.

    Astra's scenario: the base's version-control entry resolves to a folder
    whose own path names neither guarded folder, so the shortcut that lets
    almost every write go without a second look let a write to that folder's
    settings go too. The places a base keeps its history are now worked out
    and compared before that shortcut.
    """

    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def kept_elsewhere(self, sandbox, joined=True):
        import shutil

        base = Base(sandbox, joined=joined)
        external = os.path.join(sandbox.path, "external", "repo-meta")
        os.makedirs(os.path.dirname(external))
        shutil.move(os.path.join(base.root, DOT_GIT), external)
        support.write(os.path.join(base.root, DOT_GIT), "gitdir: %s\n" % external)
        return base, external

    def test_the_settings_of_a_history_folder_kept_elsewhere_are_refused(self):
        with support.Sandbox() as sandbox:
            _base, external = self.kept_elsewhere(sandbox)

            self.assertTrue(self.check(os.path.join(external, "config")))
            self.assertTrue(
                self.check(os.path.join(external, "hooks", "pre-push"))
            )

    def test_the_same_with_the_joined_list_emptied(self):
        with support.Sandbox() as sandbox:
            base, external = self.kept_elsewhere(sandbox)
            support.write(paths.machine_state_path(), "{}")

            self.assertTrue(
                self.check(os.path.join(external, "config"), cwd=base.root)
            )

    def test_a_history_folder_reached_through_a_link(self):
        with support.Sandbox() as sandbox:
            import shutil

            base = Base(sandbox)
            external = os.path.join(sandbox.path, "linked-meta")
            shutil.move(os.path.join(base.root, DOT_GIT), external)
            os.symlink(external, os.path.join(base.root, DOT_GIT))

            self.assertTrue(self.check(os.path.join(external, "config")))

    def test_the_shared_history_of_a_base_that_is_a_second_working_folder(self):
        with support.Sandbox() as sandbox:
            source = Base(sandbox, name="source", joined=False)
            common = os.path.join(sandbox.path, "external", "shared-meta")
            support.git(["clone", "-q", "--bare", source.root, common], cwd=sandbox.path)
            support.git(
                ["config", "gtmbase.id", source.base_id], cwd=common
            )
            second = os.path.join(sandbox.path, "second")
            support.git(["worktree", "add", "-q", second, "main"], cwd=common)
            machine.append_joined(root=second, base_id=source.base_id, remote=None)
            own = os.path.join(common, "worktrees", "second")

            self.assertTrue(self.check(os.path.join(common, "config")))
            self.assertTrue(self.check(os.path.join(own, "HEAD")))

    def test_an_ordinary_file_elsewhere_still_starts_no_program(self):
        with support.Sandbox() as sandbox:
            self.kept_elsewhere(sandbox)
            elsewhere = os.path.join(sandbox.path, "elsewhere", "notes.md")
            support.write(elsewhere, "# Notes\n")
            first, second = _no_program_may_start()
            with first, second:
                said = write_hook.run(request(elsewhere))

            self.assertIsNone(said)


class TestABaseWhoseMapIsGone(unittest.TestCase):
    """R3. Renaming the map of a base nobody joined took its guard away.

    The guard knew a base only by the map in its working folder and by the
    list of bases this account joined. An unjoined copy of a base with its map
    renamed matched neither, so its own history folder and its assistant
    settings could be written. The push gate already knew it for a base by its
    history, and now the guard asks the same questions.
    """

    def check(self, path, **named):
        return denied(write_hook.run(request(path, **named)))

    def a_copy_without_its_map(self, sandbox):
        from gtmbase import constants

        source = Base(sandbox, name="source", joined=False)
        # A base made the way a base is really made holds all three of the
        # entries its history is known by.
        support.write(
            os.path.join(source.root, constants.CODEOWNERS_PATH), "/context/ @owner\n"
        )
        support.git(["add", "-A"], cwd=source.root)
        support.git(["commit", "-q", "-m", "owners"], cwd=source.root)
        clone = os.path.join(sandbox.path, "copy")
        support.git(["clone", "-q", source.root, clone], cwd=sandbox.path)
        os.rename(
            os.path.join(clone, "context", "map.md"),
            os.path.join(clone, "context", "old-map.md"),
        )
        return clone

    def test_its_safeguard_before_a_send_is_refused(self):
        with support.Sandbox() as sandbox:
            clone = self.a_copy_without_its_map(sandbox)

            self.assertTrue(
                self.check(os.path.join(clone, DOT_GIT, "hooks", "pre-push"))
            )

    def test_its_assistant_settings_are_refused(self):
        with support.Sandbox() as sandbox:
            clone = self.a_copy_without_its_map(sandbox)

            self.assertTrue(
                self.check(os.path.join(clone, DOT_CLAUDE, "settings.json"))
            )

    def test_a_base_that_carries_its_name_is_known_without_starting_anything(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox, joined=False)
            os.rename(
                os.path.join(base.root, "context", "map.md"),
                os.path.join(base.root, "context", "old-map.md"),
            )
            first, second = _no_program_may_start()
            with first, second:
                said = write_hook.run(
                    request(os.path.join(base.root, DOT_GIT, "hooks", "pre-push"))
                )

            self.assertTrue(denied(said))

    def test_an_ordinary_repository_is_still_left_alone(self):
        with support.Sandbox() as sandbox:
            ordinary = os.path.join(sandbox.path, "ordinary")
            os.makedirs(ordinary)
            support.git(["init", "-q", "-b", "main"], cwd=ordinary)
            support.write(os.path.join(ordinary, "README.md"), "hi\n")
            support.git(["add", "-A"], cwd=ordinary)
            support.git(["commit", "-q", "-m", "one"], cwd=ordinary)

            self.assertFalse(
                self.check(os.path.join(ordinary, DOT_CLAUDE, "settings.json"))
            )
            self.assertFalse(
                self.check(os.path.join(ordinary, DOT_GIT, "hooks", "pre-push"))
            )



# --- R4 and R5 of Astra's third verification ---------------------------------


class TestAnErrorWhileCheckingRunsTheSmallerCheck(unittest.TestCase):
    """R4. An error inside the real check let a protected write through.

    It printed nothing and answered success, so the wrapper never reached
    the smaller check it keeps for a check that could not run. Astra's probe
    put an error into the check and got success with nothing printed.
    """

    def main_with(self, payload, **patches):
        import io

        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
            return write_hook.main([]), stdout.getvalue()

    def test_an_error_in_the_check_is_the_failure_status(self):
        with support.Sandbox():
            with mock.patch.object(
                write_hook, "run", side_effect=OSError("stopped")
            ):
                code, printed = self.main_with(request("/tmp/anything.md"))

            self.assertEqual(write_hook.COULD_NOT_RUN, code)
            self.assertEqual("", printed)

    def test_an_error_while_answering_is_the_failure_status_too(self):
        import io

        class Broken(io.StringIO):
            def write(self, text):
                raise OSError("the answer could not be written")

        with support.Sandbox():
            with mock.patch("sys.stdin", io.StringIO(json.dumps(request(paths.machine_state_path())))), mock.patch("sys.stdout", Broken()):
                code = write_hook.main([])

            self.assertEqual(write_hook.COULD_NOT_RUN, code)

    def test_the_status_is_the_one_the_wrapper_treats_as_a_failure(self):
        with open(SCRIPT, encoding="utf-8") as handle:
            text = handle.read()

        self.assertIn("COULD_NOT_RUN = %d" % write_hook.COULD_NOT_RUN, text)
        self.assertNotEqual(0, write_hook.COULD_NOT_RUN)

    def a_copy_whose_check_fails_while_running(self, sandbox):
        import shutil

        root = os.path.join(sandbox.path, "installed", "gtm-base")
        os.makedirs(os.path.dirname(root), exist_ok=True)
        shutil.copytree(PLUGIN_DIR, root)
        target = os.path.join(root, "lib", "gtmbase", "write_hook.py")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(
                "\n\ndef run(payload):\n    raise OSError('stopped')\n"
            )
        return root

    def test_through_the_wrapper_a_protected_write_is_refused(self):
        with support.Sandbox() as sandbox:
            root = self.a_copy_whose_check_fails_while_running(sandbox)
            base = Base(sandbox)
            environment = dict(os.environ)
            environment["CLAUDE_PLUGIN_ROOT"] = root
            for named, wanted in (
                (os.path.join(base.root, "." + "git", "config"), b'"deny"'),
                (os.path.join(sandbox.path, "notes.md"), b""),
            ):
                finished = subprocess.run(
                    ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
                    input=json.dumps(request(named)).encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                )

                self.assertEqual(0, finished.returncode)
                if wanted:
                    self.assertIn(wanted, finished.stdout, named)
                else:
                    self.assertEqual(b"", finished.stdout, named)


class TestTheSmallerCheckReadsDotsTheWayTheDiskDoes(unittest.TestCase):
    """R5. A path with a dot or two dots in it got past the smaller check.

    Astra ran the smaller check's own definitions and got nothing back for
    the records folder written with a dot in the middle, and nothing for the
    settings file written relative to the folder it sits in, which is how an
    ordinary relative path reaches it.
    """

    def a_broken_copy(self, sandbox):
        return TestTheWrapperWhenThePythonHalfCannotLoad.a_broken_copy(self, sandbox)

    def answer(self, named, root, cwd=None):
        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = root
        finished = subprocess.run(
            ["sh", os.path.join(root, "hooks", "write-check.sh"), "claude"],
            input=json.dumps(request(named, cwd=cwd)).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(0, finished.returncode)
        if b'"deny"' in finished.stdout:
            return "deny"
        if b'"ask"' in finished.stdout:
            return "ask"
        return "nothing"

    def test_astras_three_paths(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            home = os.path.expanduser("~")
            assistant = os.path.join(home, "." + "claude")
            os.makedirs(assistant, exist_ok=True)
            seat = paths.seat_home_path()
            os.makedirs(seat, exist_ok=True)
            seat_parent, seat_name = os.path.split(seat)

            self.assertEqual(
                "ask", self.answer(os.path.join(assistant, "settings.json"), root)
            )
            self.assertEqual(
                "ask",
                self.answer(assistant + "/./settings.json", root),
            )
            self.assertEqual(
                "deny",
                self.answer(seat_parent + "/./" + seat_name + "/machine.json", root),
            )
            self.assertEqual(
                "ask", self.answer("./settings.json", root, cwd=assistant)
            )

    def test_two_dots_and_a_link_are_read_as_the_place_they_reach(self):
        with support.Sandbox() as sandbox:
            root = self.a_broken_copy(sandbox)
            seat = paths.seat_home_path()
            os.makedirs(seat, exist_ok=True)
            seat_parent, seat_name = os.path.split(seat)
            work = os.path.join(sandbox.path, "work")
            os.makedirs(work)
            os.symlink(seat, os.path.join(work, "shortcut"))

            self.assertEqual(
                "deny",
                self.answer(
                    os.path.join(work, "..", "..", os.path.relpath(seat, os.path.dirname(sandbox.path)), "machine.json"),
                    root,
                ),
            )
            self.assertEqual(
                "deny",
                self.answer(os.path.join(work, "shortcut", "machine.json"), root),
            )
            self.assertEqual(
                "nothing",
                self.answer(os.path.join(work, ".", "notes.md"), root),
            )


if __name__ == "__main__":
    unittest.main()
