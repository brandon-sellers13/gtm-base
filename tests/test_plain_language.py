"""The plain-language lint's own tests, which it did not have until Unit 1.1b.

The lint is a floor. These tests prove the floor is where it is meant to be,
and nothing here claims that a document passing them reads well. What the
standard is judged by is the owner reading a step aloud, and
`docs/ux-standard.md` says so in those words.
"""

import os
import unittest

import plain_language
import support
from support import PLUGIN_DIR, REPO_ROOT

from gtmbase import constants


UX_STANDARD = os.path.join(REPO_ROOT, "docs", "ux-standard.md")
CHANGE_TEMPLATE = os.path.join(PLUGIN_DIR, "templates", "change-four-lines.md")
JOIN_SKILL = os.path.join(PLUGIN_DIR, "skills", "join", "SKILL.md")
LIB_DIR = os.path.join(PLUGIN_DIR, "lib")


def step(body):
    """One step section, written the way a skill document writes one."""
    return "### Step 1. A step\n\n" + body + "\n"


class TestTheStepsTheLintReads(unittest.TestCase):
    def test_a_heading_that_is_not_a_step_is_not_read(self):
        text = "## What you are shown\n\nRun the script and read the answer.\n"
        self.assertEqual([], plain_language.find_steps(text))
        self.assertEqual([], plain_language.find_missing_purpose(text))

    def test_a_section_opts_itself_in_with_the_marker(self):
        text = (
            "## What you are shown\n"
            + plain_language.STEP_MARKER
            + "\n\nRun the script and read the answer.\n"
        )
        steps = plain_language.find_steps(text)
        self.assertEqual(1, len(steps))
        self.assertEqual("What you are shown", steps[0].title)

    def test_a_step_ends_where_the_next_heading_of_its_level_begins(self):
        text = (
            "### Step 1. A step\n\nThis step exists to show the ending.\n\n"
            "### Step 2. Another step\n\nThis step exists to be separate.\n"
        )
        steps = plain_language.find_steps(text)
        self.assertEqual(2, len(steps))
        body = " ".join(line for _number, line in steps[0].lines)
        self.assertNotIn("separate", body)


class TestTheStepOpensWithItsPurpose(unittest.TestCase):
    def test_a_step_that_opens_with_an_order_fails(self):
        text = step("Say the sharing notice, and then wait.")
        self.assertEqual(
            [("Step 1. A step", 1)], plain_language.find_missing_purpose(text)
        )

    def test_a_step_that_opens_with_a_purpose_sentence_passes(self):
        text = step(
            "This step is where the person learns who may end up reading the\n"
            "documents they approve. Say the sharing notice, and then wait."
        )
        self.assertEqual([], plain_language.find_missing_purpose(text))

    def test_an_order_behind_a_clause_about_timing_still_fails(self):
        text = step("Before running anything, say these three things.")
        self.assertEqual(
            [("Step 1. A step", 1)], plain_language.find_missing_purpose(text)
        )

    def test_a_purpose_sentence_behind_a_clause_about_timing_passes(self):
        text = step(
            "Before anything is written, the person needs to know what setting "
            "up a base does. Say these three things."
        )
        self.assertEqual([], plain_language.find_missing_purpose(text))

    def test_a_step_that_opens_with_a_list_fails(self):
        text = step("- The first thing this step does.\n- The second thing.")
        self.assertEqual(
            [("Step 1. A step", 1)], plain_language.find_missing_purpose(text)
        )

    def test_a_step_with_nothing_under_its_heading_fails(self):
        text = "### Step 1. A step\n\n### Step 2. Another\n\nThis is the second.\n"
        self.assertEqual(
            [("Step 1. A step", 1)], plain_language.find_missing_purpose(text)
        )


class TestTheStepAsksForOneThing(unittest.TestCase):
    def ask(self, words):
        return (
            plain_language.ASK_OPEN
            + "\n"
            + words
            + "\n"
            + plain_language.ASK_CLOSE
        )

    def test_a_step_that_makes_two_requests_fails(self):
        text = step(
            "This step settles the company name and the folder.\n\n"
            + self.ask("What is the company called?")
            + "\n\n"
            + self.ask("Where should the base go?")
        )
        found = plain_language.find_extra_requests(text)
        self.assertEqual(1, len(found))
        self.assertEqual("Step 1. A step", found[0][0])
        self.assertEqual(2, found[0][1])

    def test_a_step_that_makes_one_request_passes(self):
        text = step(
            "This step settles the company name.\n\n"
            + self.ask("What is the company called?")
        )
        self.assertEqual([], plain_language.find_extra_requests(text))

    def test_the_required_closing_wording_passes_although_it_asks_nothing(self):
        """P4's wording has no question mark, and revision 1 would have failed it."""
        wording = (
            "Tell me if anything about the context of the business changed "
            "that we should account for. One sentence is enough, or say skip."
        )
        text = step(
            "This step is the one chance to record what changed while the base "
            "was being set up.\n\n" + self.ask(wording)
        )
        self.assertEqual([], plain_language.find_extra_requests(text))
        self.assertNotIn("?", wording)

    def test_a_step_that_asks_for_nothing_passes(self):
        text = step("This step exists only to say the sharing notice.")
        self.assertEqual([], plain_language.find_extra_requests(text))

    def test_a_request_block_that_never_ends_fails(self):
        text = step(
            "This step settles the company name.\n\n"
            + plain_language.ASK_OPEN
            + "\nWhat is the company called?"
        )
        self.assertEqual(1, len(plain_language.find_extra_requests(text)))


class TestWhatIsShownCanBeReadInSeconds(unittest.TestCase):
    def prose(self, count):
        return "\n".join(
            "This is prose line number %d of the evidence." % number
            for number in range(1, count + 1)
        )

    def test_six_prose_lines_fail(self):
        text = step(self.prose(6))
        found = plain_language.find_long_prose(text)
        self.assertEqual(1, len(found))
        self.assertEqual("Step 1. A step", found[0][0])

    def test_the_same_content_as_a_five_row_table_passes(self):
        rows = "\n".join(
            "| Row %d | Something |" % number for number in range(1, 6)
        )
        text = step(
            "This step shows what was found.\n\n| What | Where |\n|---|---|\n"
            + rows
        )
        self.assertEqual([], plain_language.find_long_prose(text))

    def test_five_prose_lines_pass(self):
        text = step(self.prose(5))
        self.assertEqual([], plain_language.find_long_prose(text))

    def test_a_blank_line_does_not_reset_the_run(self):
        text = step(self.prose(3) + "\n\n" + self.prose(4))
        self.assertEqual(1, len(plain_language.find_long_prose(text)))

    def test_a_whole_document_inside_a_marked_artifact_block_passes(self):
        whole = self.prose(40)
        text = step(
            "This step shows the cleaned document so it can be read whole.\n\n"
            + plain_language.ARTIFACT_OPEN
            + "\n"
            + whole
            + "\n"
            + plain_language.ARTIFACT_CLOSE
        )
        self.assertEqual([], plain_language.find_long_prose(text))

    def test_a_long_code_block_is_not_prose(self):
        text = step(
            "This step runs the script.\n\n```\n"
            + self.prose(9)
            + "\n```\n"
        )
        self.assertEqual([], plain_language.find_long_prose(text))


class TestAChangeIsFourLabeledLines(unittest.TestCase):
    def block(self, body):
        return (
            plain_language.CHANGE_OPEN
            + "\n"
            + body
            + "\n"
            + plain_language.CHANGE_CLOSE
            + "\n"
        )

    def four_lines(self):
        return (
            "What changed: We stopped selling to companies under twenty people.\n"
            "Why: The last four took the longest to close and left the soonest.\n"
            "What it affects: your customer profile, your positioning\n"
            "When to look again: 2026-12-19"
        )

    def test_a_change_shown_as_a_paragraph_fails(self):
        text = self.block(
            "We stopped selling to companies under twenty people, because the "
            "last four of them took the longest to close, which affects the "
            "customer profile and the positioning, and it is worth another "
            "look in December."
        )
        found = plain_language.find_malformed_changes(text)
        self.assertEqual(1, len(found))

    def test_the_same_change_as_four_labeled_lines_passes(self):
        self.assertEqual(
            [], plain_language.find_malformed_changes(self.block(self.four_lines()))
        )

    def test_the_four_labels_must_come_in_order(self):
        lines = self.four_lines().splitlines()
        swapped = "\n".join([lines[1], lines[0], lines[2], lines[3]])
        self.assertNotEqual(
            [], plain_language.find_malformed_changes(self.block(swapped))
        )

    def test_a_missing_label_fails(self):
        lines = self.four_lines().splitlines()
        self.assertNotEqual(
            [],
            plain_language.find_malformed_changes(self.block("\n".join(lines[:3]))),
        )

    def test_the_four_lines_may_be_written_as_a_list(self):
        listed = "\n".join(
            "- " + line for line in self.four_lines().splitlines()
        )
        self.assertEqual(
            [], plain_language.find_malformed_changes(self.block(listed))
        )

    def test_a_change_block_that_never_ends_fails(self):
        text = plain_language.CHANGE_OPEN + "\n" + self.four_lines() + "\n"
        self.assertNotEqual([], plain_language.find_malformed_changes(text))

    def test_the_template_holds_the_form_the_check_accepts(self):
        with open(CHANGE_TEMPLATE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual([], plain_language.find_malformed_changes(text))
        for label in plain_language.CHANGE_LABELS:
            self.assertIn(label, text)


class TestTheOldChecksStillCatchWhatTheyCaught(unittest.TestCase):
    def test_every_banned_word_and_its_inflections_are_still_caught(self):
        for word in constants.BANNED_GIT_WORDS:
            found = plain_language.find_banned("Please %s the file." % word)
            self.assertEqual([(word, 1)], found, word)
        for phrase, word in (
            ("We committed the file.", "commit"),
            ("Two branches were opened.", "branch"),
            ("It was rebased yesterday.", "rebase"),
            ("Open a pull  request.", "pull request"),
            ("The folder was cloned.", "clone"),
            ("It was merging cleanly.", "merge"),
        ):
            self.assertEqual(
                [(word, 1)], plain_language.find_banned(phrase), phrase
            )

    def test_plain_words_are_not_caught(self):
        self.assertEqual(
            [], plain_language.find_banned("Your base was brought up to date.")
        )

    def test_both_long_dashes_are_still_caught(self):
        text = "One" + plain_language.EM_DASH + "two\nthree" + plain_language.EN_DASH
        found = plain_language.find_dashes(text)
        self.assertEqual(
            [(plain_language.EM_DASH, 1), (plain_language.EN_DASH, 2)], found
        )

    def test_a_file_with_neither_passes_the_old_assertion(self):
        plain_language.assert_plain(self, UX_STANDARD)


class TestTheRegistryOfSentencesHeldInPython(unittest.TestCase):
    def registered(self):
        return set(plain_language.PYTHON_SENTENCES)

    def excused(self):
        return set(
            (module, name)
            for module, name, _reason in plain_language.NOT_PERSON_FACING
        )

    def test_the_registry_is_complete(self):
        """No sentence-shaped constant may sit outside the registry unnamed."""
        known = self.registered() | self.excused()
        missing = [
            (module, name, line)
            for module, name, line in plain_language.library_sentence_constants(
                LIB_DIR
            )
            if (module, name) not in known
        ]
        self.assertEqual([], missing, "sentences outside the registry: %s" % missing)

    def test_the_registry_holds_the_four_modules_the_review_named(self):
        modules = set(module for module, _name in plain_language.PYTHON_SENTENCES)
        for named in ("stale_check", "constants", "confirm", "join_flow"):
            self.assertIn(named, modules)

    def test_nothing_is_both_registered_and_excused(self):
        self.assertEqual(set(), self.registered() & self.excused())

    def test_every_registered_sentence_exists_and_is_a_sentence(self):
        found = dict(
            ((module, name), line)
            for module, name, line in plain_language.library_sentence_constants(
                LIB_DIR
            )
        )
        for entry in plain_language.PYTHON_SENTENCES:
            self.assertIn(entry, found, "%s is registered but not in the library" % (entry,))

    def test_every_registered_sentence_passes_the_banned_words_and_dashes(self):
        import importlib

        for module_name, constant_name in plain_language.PYTHON_SENTENCES:
            module = importlib.import_module("gtmbase." + module_name)
            text = getattr(module, constant_name)
            self.assertEqual(
                [],
                plain_language.find_banned(text),
                "%s.%s" % (module_name, constant_name),
            )
            self.assertEqual(
                [],
                plain_language.find_dashes(text),
                "%s.%s" % (module_name, constant_name),
            )

    def test_a_sentence_shaped_constant_left_out_of_the_registry_is_caught(self):
        """A fixture library with one unregistered sentence must fail the walk."""
        with support.Sandbox() as sandbox:
            package = os.path.join(sandbox.path, "lib", "gtmbase")
            os.makedirs(package)
            support.write(os.path.join(package, "__init__.py"), "")
            support.write(
                os.path.join(package, "later.py"),
                'NEW_SENTENCE = (\n'
                '    "GTM Base could not do that just now, so nothing was '
                'written down."\n'
                ')\n'
                'A_NUMBER = 40\n'
                'A_LABEL = "open"\n',
            )
            found = plain_language.library_sentence_constants(
                os.path.join(sandbox.path, "lib")
            )
            self.assertIn(("later", "NEW_SENTENCE", 1), found)
            self.assertEqual(1, len(found))

    def test_every_excused_constant_says_why_it_is_excused(self):
        self.assertNotEqual((), plain_language.NOT_PERSON_FACING)
        for module, name, reason in plain_language.NOT_PERSON_FACING:
            self.assertTrue(module and name)
            self.assertGreater(len(reason.split()), 5, name)


class TestTheExemptionList(unittest.TestCase):
    def test_every_exemption_carries_a_reason_and_the_unit_that_removes_it(self):
        self.assertNotEqual((), plain_language.EXEMPTIONS)
        for entry in plain_language.EXEMPTIONS:
            self.assertEqual(
                [],
                plain_language.exemption_problems(entry),
                "%s, %s" % (entry.path, entry.step),
            )

    def test_an_entry_with_neither_a_reason_nor_a_unit_fails(self):
        empty = plain_language.Exemption("a/path.md", "purpose", "A step", "", "")
        problems = plain_language.exemption_problems(empty)
        self.assertIn("the reason does not say why the text fails today", problems)
        self.assertIn("the entry does not name the unit that removes it", problems)

    def test_an_entry_whose_only_reason_is_later_fails(self):
        entry = plain_language.Exemption(
            "a/path.md",
            "purpose",
            "A step",
            "This is broken and will be dealt with later by somebody.",
            "1.8",
        )
        self.assertIn('"later" is not a reason', plain_language.exemption_problems(entry))

    def test_an_entry_naming_a_check_that_does_not_exist_fails(self):
        entry = plain_language.Exemption(
            "a/path.md",
            "tone",
            "A step",
            "The step does not sound the way the owner would say it out loud.",
            "1.8",
        )
        self.assertIn(
            "'tone' is not one of the four checks",
            plain_language.exemption_problems(entry),
        )

    def test_an_exemption_covers_only_the_step_it_names(self):
        entry = plain_language.Exemption(
            "skills/join/SKILL.md", "purpose", "Step 7. The closing", "a reason", "1.5"
        )
        self.assertTrue(
            entry.covers("plugins/gtm-base/skills/join/SKILL.md", "Step 7. The closing")
        )
        self.assertFalse(
            entry.covers("plugins/gtm-base/skills/join/SKILL.md", "Step 1. A step")
        )
        self.assertFalse(entry.covers("somewhere/else/SKILL.md", "Step 7. The closing"))

    def test_every_exemption_names_a_file_that_exists(self):
        for entry in plain_language.EXEMPTIONS:
            self.assertTrue(
                os.path.isfile(os.path.join(REPO_ROOT, entry.path)), entry.path
            )

    def test_every_exemption_is_still_earning_its_place(self):
        """An entry whose text now passes is an entry somebody forgot to delete."""
        by_path = {}
        for entry in plain_language.EXEMPTIONS:
            by_path.setdefault(entry.path, []).append(entry)
        for path, entries in by_path.items():
            with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as handle:
                text = handle.read()
            failing = set()
            for title, _line in plain_language.find_missing_purpose(text):
                failing.add(("purpose", title))
            for title, _count, _line in plain_language.find_extra_requests(text):
                failing.add(("one-request", title))
            for title, _run, _line in plain_language.find_long_prose(text):
                failing.add(("prose", title))
            for entry in entries:
                self.assertIn(
                    (entry.check, entry.step),
                    failing,
                    "%s no longer fails %s and can be deleted" % (entry.step, entry.check),
                )


class TestTheLintOverTheRealDocuments(unittest.TestCase):
    def user_facing_files(self):
        """Every skill document and template, which is what a person reads.

        The plugin's own CHANGELOG and README are written for the people who
        build GTM Base, so they are not in here. Everything under `skills/` and
        `templates/` is read by the person whose base it is.
        """
        found = []
        for folder in ("skills", "templates"):
            for base, dirs, files in os.walk(os.path.join(PLUGIN_DIR, folder)):
                dirs[:] = [name for name in dirs if name != "__pycache__"]
                for name in sorted(files):
                    if name.endswith(".md"):
                        found.append(os.path.join(base, name))
        found.append(UX_STANDARD)
        found.append(os.path.join(REPO_ROOT, "docs", "join-guide.md"))
        return sorted(found)

    def test_every_user_facing_document_passes_the_whole_standard(self):
        files = self.user_facing_files()
        self.assertGreater(len(files), 20)
        for path in files:
            plain_language.assert_plain(self, path)
            plain_language.assert_standard(self, path)

    def test_the_join_steps_the_exemptions_do_not_cover_still_pass(self):
        """The exemption list excuses named steps, never a whole file."""
        covered = set(
            entry.step
            for entry in plain_language.exemptions_for(JOIN_SKILL)
        )
        with open(JOIN_SKILL, encoding="utf-8") as handle:
            text = handle.read()
        titles = set(one.title for one in plain_language.find_steps(text))
        self.assertTrue(covered)
        self.assertTrue(covered.issubset(titles), covered - titles)

    def test_the_ux_standard_says_the_lint_is_a_floor(self):
        with open(UX_STANDARD, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("The lint is a floor", text)
        self.assertIn("reading the steps aloud", text)
        self.assertIn("context change", text)

    def test_the_ux_standard_records_the_four_questions_as_a_draft(self):
        with open(UX_STANDARD, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("The four questions a base answers", text)
        self.assertIn("DRAFT", text)
        for question in (
            "What's true?",
            "Where's the rest?",
            "What changed?",
            "Who said yes?",
        ):
            self.assertIn(question, text)


if __name__ == "__main__":
    unittest.main()
