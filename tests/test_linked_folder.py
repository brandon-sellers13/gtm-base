"""Release 0.3.1: every script works from the folder a person actually works in.

The release A live check was paused at its second step on 2026-09-26. Brandon
works in ~/Gridwise, which is linked to his base, and every script a skill runs
refused that folder with "This folder is not a company base you have joined
yet", because each one asked for a base joined in that very folder. Session
start reached the base from there, so the base woke up and then nothing worked.
Every test ran every script from inside the base, which is why none of them
saw it.

The same run found three smaller things, and each has its proof here too: the
review never made the update offer when nothing was due, `--check-move` read a
change's identifier out to the person, and the skills let the assistant put
the review in its own words.

Every folder linked to a base here is linked the way the join skill links one,
through `machine.link_content`, never by standing in for the resolver.
"""

import os
import re
import subprocess
import sys
import unittest

import plain_language
import support
import test_changes_migration as migration
import test_first_draft_marker as first_draft
import test_moment_of_use as moment_tests

from gtmbase import (
    changes,
    constants,
    formats,
    machine,
    paths,
    stale_check,
    state,
)

SKILLS_DIR = os.path.join(support.PLUGIN_DIR, "skills")
STALE = os.path.join(SKILLS_DIR, "stale-check", "scripts", "stale_check.py")
CONFIRM = os.path.join(SKILLS_DIR, "confirm", "scripts", "confirm.py")
PROPOSE = os.path.join(SKILLS_DIR, "propose-change", "scripts", "propose.py")
APPROVE = os.path.join(SKILLS_DIR, "propose-change", "scripts", "approve_local.py")
MOMENT = os.path.join(support.PLUGIN_DIR, "scripts", "moment.py")
SEAT = os.path.join(support.PLUGIN_DIR, "scripts", "seat.py")

ICP = moment_tests.ICP
POSITIONING = moment_tests.POSITIONING

# The sentence each script says to a folder that is neither a base nor linked
# to one, which has to stay exactly as it was.
NOT_JOINED_START = "This folder is not a company base you have joined yet"


def run(script, arguments, cwd):
    """One script, started in one folder, the way the assistant starts it."""
    finished = subprocess.run(
        [sys.executable, script] + [str(item) for item in arguments],
        cwd=cwd,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (
        finished.returncode,
        finished.stdout.decode("utf-8"),
        finished.stderr.decode("utf-8"),
    )


def value_on(printed, name):
    """One value off the line marked for the assistant, or off a name=value line."""
    match = re.search(r"\b%s=(\S+)" % re.escape(name), printed)
    return match.group(1) if match else None


class LinkedCase(unittest.TestCase):
    """A base with a context change in it, and a folder linked to it."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.base = moment_tests.Base(self.sandbox)
        self.base.add_change()
        self.folder = support.linked_folder_for(self.base.root)

    def from_both(self, script, arguments):
        """The same command from inside the base and from the linked folder."""
        return (
            run(script, arguments, self.base.root),
            run(script, arguments, self.folder),
        )

    def assert_not_refused(self, ran):
        code, out, err = ran
        self.assertNotIn(NOT_JOINED_START, out + err)
        self.assertEqual(0, code, out + err)


class TestTheFolderIsReallyLinked(LinkedCase):
    def test_it_is_linked_and_not_joined(self):
        """What the resolver says here is exactly what it says in ~/Gridwise."""
        resolution = paths.resolve_base(self.folder, machine.load_machine_state())

        self.assertEqual(paths.CODE_LINKED, resolution.code)
        self.assertFalse(resolution.joined)
        self.assertTrue(resolution.active)
        self.assertEqual(os.path.realpath(self.base.root), resolution.root)
        self.assertEqual(self.base.base_id, resolution.base_id)
        self.assertNotEqual(os.path.realpath(self.base.root), self.folder)

    def test_the_second_run_really_starts_scripts_in_the_linked_folder(self):
        """The runners' switch, which the second run in tests/run.sh sets."""
        saved = os.environ.get(support.FROM_A_LINKED_FOLDER)
        try:
            os.environ.pop(support.FROM_A_LINKED_FOLDER, None)
            self.assertEqual(
                self.base.root, support.where_a_script_runs(self.base.root)
            )
            os.environ[support.FROM_A_LINKED_FOLDER] = "1"
            self.assertEqual(
                self.folder, support.where_a_script_runs(self.base.root)
            )
            # A folder that is not a base is left as the test wrote it.
            elsewhere = os.path.join(self.sandbox.path, "elsewhere")
            os.makedirs(elsewhere)
            self.assertEqual(elsewhere, support.where_a_script_runs(elsewhere))
        finally:
            if saved is None:
                os.environ.pop(support.FROM_A_LINKED_FOLDER, None)
            else:
                os.environ[support.FROM_A_LINKED_FOLDER] = saved


class TestEveryScriptFromALinkedFolder(LinkedCase):
    """Finding 1: each of the six scripts works from the linked folder."""

    def test_the_review_says_the_same_from_either_folder(self):
        inside, linked = self.from_both(STALE, ["--review", "--dry-run"])

        self.assert_not_refused(inside)
        self.assert_not_refused(linked)
        self.assertEqual(inside[1], linked[1])
        self.assertIn("your customer profile", linked[1])

    def test_the_review_asks_its_questions_from_the_linked_folder(self):
        code, out, err = run(STALE, ["--review"], self.folder)

        self.assert_not_refused((code, out, err))
        self.assertTrue(value_on(out, "question"), out)

    def test_the_other_stale_check_commands_answer_from_the_linked_folder(self):
        for arguments in (
            ["--dry-run"],
            ["--report"],
            ["--check-move"],
            ["--show-document", ICP],
        ):
            with self.subTest(arguments=arguments):
                inside, linked = self.from_both(STALE, arguments)
                self.assert_not_refused(linked)
                self.assertEqual(inside[1], linked[1])

    def test_an_answer_is_recorded_from_the_linked_folder(self):
        _code, out, _err = run(STALE, ["--review"], self.folder)
        question = value_on(out, "question")
        self.assertTrue(question, out)

        inside, linked = self.from_both(CONFIRM, ["--pending"])
        self.assert_not_refused(linked)
        self.assertEqual(inside[1], linked[1])

        answered = run(
            CONFIRM, ["--question", question, "--answer", "not-now"], self.folder
        )
        self.assert_not_refused(answered)

    def test_the_moment_check_flags_the_same_from_either_folder(self):
        inside, linked = self.from_both(MOMENT, ["--file", ICP])

        self.assert_not_refused(inside)
        self.assert_not_refused(linked)
        # The question each run is given is its own, so that line is left out.
        def without_the_id(text):
            return [line for line in text.split("\n") if "question id" not in line]

        self.assertEqual(without_the_id(inside[1]), without_the_id(linked[1]))
        self.assertIn("your customer profile", linked[1])

    def test_a_seat_setting_changes_from_the_linked_folder(self):
        ran = run(SEAT, ["--weekly-line", "on"], self.folder)

        self.assert_not_refused(ran)
        seat, _problems = state.load_seat(self.base.base_id)
        self.assertTrue(seat.get("weekly_line"), seat)

    def test_propose_shows_a_document_from_the_linked_folder(self):
        inside, linked = self.from_both(PROPOSE, ["--show-document", ICP])

        self.assert_not_refused(linked)
        self.assertEqual(inside[1], linked[1])

    def test_a_words_file_is_handed_out_from_the_linked_folder(self):
        for script in (PROPOSE, CONFIRM, APPROVE):
            with self.subTest(script=os.path.basename(script)):
                ran = run(script, ["--new-words-file", "answer"], self.folder)
                self.assert_not_refused(ran)
                self.assertTrue(value_on(ran[1], "words"), ran[1])


class TestAPathInsideTheBase(LinkedCase):
    """Finding 1, second half: a path inside the base is read against the base.

    The skills say where prepared changes wait as a path inside the base, and
    the scripts used to join that path onto the folder the command ran in. From
    a linked folder it pointed into that folder, where nothing is waiting.
    """

    def a_prepared_change(self, worded=False):
        """A prepared change, as its whole path and as a path inside the base.

        Worded, it carries real words rather than GTM Base's note asking for
        them, which is what showing and approving it need. The wording goes in
        from inside the base, so only the command under test runs from the
        linked folder.
        """
        staged = first_draft.a_first_draft(
            self.base.root, body=first_draft.NAMES_THE_PART
        )
        if worded:
            handed = run(APPROVE, ["--new-words-file", "answer"], self.base.root)
            words = value_on(handed[1], "words")
            support.write(
                words, "We sell to companies of twenty to two hundred people."
            )
            written = run(
                APPROVE,
                ["--staging", staged, "--wording", "--words", words],
                self.base.root,
            )
            self.assert_not_refused(written)
        return staged, os.path.relpath(staged, self.base.root)

    def test_the_whole_change_is_shown_from_either_folder(self):
        _staged, inside_the_base = self.a_prepared_change(worded=True)

        inside, linked = self.from_both(
            APPROVE, ["--staging", inside_the_base, "--show"]
        )

        self.assert_not_refused(inside)
        self.assert_not_refused(linked)
        self.assertIn("Shown value: ", linked[1])
        self.assertEqual(inside[1], linked[1])

    def test_the_waiting_list_is_the_same_from_either_folder(self):
        self.a_prepared_change()

        inside, linked = self.from_both(APPROVE, ["--list"])

        self.assert_not_refused(linked)
        self.assertEqual(inside[1], linked[1])

    def test_the_wording_goes_in_and_the_change_is_raised_from_the_linked_folder(self):
        _staged, inside_the_base = self.a_prepared_change()
        handed = run(APPROVE, ["--new-words-file", "answer"], self.folder)
        words = value_on(handed[1], "words")
        support.write(words, "We sell to companies of twenty to two hundred people.")

        written = run(
            APPROVE,
            ["--staging", inside_the_base, "--wording", "--words", words],
            self.folder,
        )
        self.assert_not_refused(written)

        raised = run(PROPOSE, ["--staging", inside_the_base], self.folder)
        self.assert_not_refused(raised)

    def test_a_whole_path_still_works_as_it_always_did(self):
        staged, _inside_the_base = self.a_prepared_change(worded=True)

        ran = run(APPROVE, ["--staging", staged, "--show"], self.folder)

        self.assert_not_refused(ran)

    def test_a_path_inside_the_base_is_read_against_the_base(self):
        root = os.path.realpath(self.base.root)
        self.assertEqual(
            os.path.join(root, "work", "x.md"),
            paths.in_the_base(root, os.path.join("work", "x.md")),
        )
        self.assertEqual("/elsewhere/x.md", paths.in_the_base(root, "/elsewhere/x.md"))


class TestTheSecondRunCoversEveryClassThatStartsAScript(unittest.TestCase):
    """tests/run.sh runs, from a linked folder, every class that starts a script.

    The second run lists classes rather than whole modules, to keep the time
    it adds small, and a list like that falls behind the moment somebody adds
    a class. So the classes are found here by what they call, and one that
    starts a script and is not in the list fails this.
    """

    # The runner each module starts its scripts through.
    RUNNERS = {
        "test_moment_of_use": (
            "run_script",
            "run_moment",
            "run_seat",
            "run_plugin_script",
        ),
        "test_approve_local": ("run_in",),
        "test_compose_proposal": ("script", "approving"),
        "test_changes_migration": ("run_script", "where_a_script_runs"),
        "test_first_draft_marker": ("run_script",),
        "test_names_with_a_space": ("run_moment", "where_a_script_runs"),
        "test_third_look": ("run_script",),
        "test_words_files": ("script",),
    }

    def listed(self):
        text = support.read(os.path.join(support.REPO_ROOT, "tests", "run.sh"))
        second = text.split(support.FROM_A_LINKED_FOLDER, 1)[1]
        return set(re.findall(r"\b(test_[a-z_]+\.Test[A-Za-z]+)\b", second))

    def starting_a_script(self):
        import ast

        found = set()
        for module, runners in self.RUNNERS.items():
            path = os.path.join(support.REPO_ROOT, "tests", module + ".py")
            tree = ast.parse(support.read(path))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    name = getattr(call.func, "attr", None) or getattr(
                        call.func, "id", None
                    )
                    if name in runners:
                        found.add("%s.%s" % (module, node.name))
                        break
        return found

    def test_every_class_that_starts_a_script_is_run_again(self):
        self.assertEqual(set(), self.starting_a_script() - self.listed())

    def test_every_class_listed_is_one_that_starts_a_script(self):
        self.assertEqual(set(), self.listed() - self.starting_a_script())


class TestAFolderThatIsNeither(unittest.TestCase):
    """The refusal stays for a folder that is neither a base nor linked to one."""

    def test_every_script_still_refuses_it_with_the_same_sentence(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            support.linked_folder_for(base.root)
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere)

            for script, arguments in (
                (STALE, ["--review"]),
                (CONFIRM, ["--pending"]),
                (PROPOSE, ["--staging", "x.md"]),
                (APPROVE, ["--list"]),
                (MOMENT, ["--file", ICP]),
                (SEAT, ["--weekly-line", "on"]),
            ):
                with self.subTest(script=os.path.basename(script)):
                    code, out, err = run(script, arguments, elsewhere)
                    self.assertEqual(2, code, out + err)
                    self.assertIn(NOT_JOINED_START, err)


class TestTheOfferWhenNothingIsDue(unittest.TestCase):
    """Finding 2: a base with nothing due still hears the update offer.

    The review returned as soon as it found nothing due, before it reached the
    offer, while `--check-move` on the same base said the offer would be made.
    Brandon's base was exactly this: nothing due, and one context change in
    the older folder.
    """

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.root, self.base_id = migration.build_base(self.sandbox)
        state.update_seat(self.base_id, session_id="sess-1")
        support.write(
            os.path.join(
                self.root,
                constants.LEGACY_CHANGES_DIR,
                migration.ENTRY_ONE + ".md",
            ),
            migration.old_entry(migration.ENTRY_ONE),
        )
        # Both documents said to be right today, the profile against the one
        # context change, so nothing at all is due a look.
        today = state.today().isoformat()
        for path, trigger, entry in (
            (ICP, "ledger", migration.ENTRY_ONE),
            (POSITIONING, "threshold", None),
        ):
            line = formats.ConfirmationLine(
                date=today, time="12:00:00Z", file=path, trigger=trigger, entry=entry
            )
            support.write(
                os.path.join(
                    self.root, constants.CONFIRMATIONS_DIR, path.replace("/", "--")
                ),
                line.render() + "\n",
            )
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", "one change in the older folder"], cwd=self.root)

    def review(self, dry_run):
        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=state.today(),
            session_id="sess-1",
            mode="review",
            dry_run=dry_run,
        )

    def assert_offered_once_after_nothing_due(self, sentences):
        self.assertIn(stale_check.REVIEW_NOTHING, sentences)
        self.assertEqual(1, sentences.count(changes.OFFER), sentences)
        self.assertLess(
            sentences.index(stale_check.REVIEW_NOTHING),
            sentences.index(changes.OFFER),
        )
        # The offer is the last thing said, after the quiet record ask too.
        self.assertEqual(changes.OFFER, sentences[-1])

    def test_the_look_says_it_would_be_offered(self):
        self.assertEqual(
            changes.OFFER_NOW, changes.what_to_offer(self.root, self.base_id)
        )

    def test_a_dry_run_review_makes_the_offer_once(self):
        result = self.review(dry_run=True)

        self.assertEqual([], result.review)
        self.assert_offered_once_after_nothing_due(result.lines())
        self.assertIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)

    def test_a_real_review_makes_the_offer_once(self):
        result = self.review(dry_run=False)

        self.assertEqual([], result.review)
        self.assert_offered_once_after_nothing_due(result.lines())
        self.assertIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)

    def test_the_script_says_it_once_in_both_modes_and_from_either_folder(self):
        folder = support.linked_folder_for(self.root)
        for cwd in (self.root, folder):
            for arguments in (["--review", "--dry-run"], ["--review"]):
                with self.subTest(cwd=cwd, arguments=arguments):
                    code, out, err = run(STALE, arguments, cwd)
                    self.assertEqual(0, code, out + err)
                    self.assertIn(stale_check.REVIEW_NOTHING, out)
                    self.assertEqual(1, out.count(changes.OFFER), out)
                    self.assertLess(
                        out.index(stale_check.REVIEW_NOTHING),
                        out.index(changes.OFFER),
                    )

    def test_the_offer_and_the_look_agree(self):
        code, out, _err = run(STALE, ["--check-move"], self.root)

        self.assertEqual(0, code)
        self.assertIn(changes.OFFER_STATE_NOW, out)
        self.assertIn("update one of your context changes", out)
        self.assertNotIn(migration.ENTRY_ONE, out)
        self.assertEqual([], plain_language.find_dashes(out))


class TestTheSkillsSayToRelay(unittest.TestCase):
    """Finding 3: the skills tell the assistant to say the scripts' sentences.

    In the live run the assistant said "Your base is up to date", named file
    paths, told Brandon the review only runs from inside the base folder, and
    suggested what to put in his base. The stale check skill opened its
    commands with "From inside the base", which is where the last of those
    came from.
    """

    SKILLS = ("stale-check", "confirm", "propose-change")

    def text_of(self, skill):
        return support.read(os.path.join(SKILLS_DIR, skill, "SKILL.md"))

    def test_no_skill_says_to_run_from_inside_the_base(self):
        for skill in self.SKILLS + ("join",):
            with self.subTest(skill=skill):
                self.assertNotIn("From inside the base", self.text_of(skill))

    def test_each_skill_says_where_its_commands_run_and_to_relay(self):
        for skill in self.SKILLS:
            with self.subTest(skill=skill):
                # Read as one line of words, because a phrase can wrap.
                text = " ".join(self.text_of(skill).lower().split())
                for phrase in (
                    "a folder linked to it",
                    "never go looking for the base",
                    "as it is",
                    "never read out a path",
                    "[for the assistant]",
                ):
                    self.assertTrue(phrase in text, "%s is missing %r" % (skill, phrase))
                plain_language.assert_plain(
                    self, os.path.join(SKILLS_DIR, skill, "SKILL.md")
                )


if __name__ == "__main__":
    unittest.main()
