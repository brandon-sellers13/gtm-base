"""Unit 4 of the join plan: what every drafting prompt has to say before it is used.

These are guards rather than behaviour tests. The three prompt files are the
only place the donor's rules are written down, so a rule quietly dropped out of
one of them would never fail anywhere else.
"""

import io
import os
import unittest

import plain_language
import support

from gtmbase import constants, drafting


def prompt(step):
    path = drafting.prompt_path(step, support.PLUGIN_DIR)
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def flat(text):
    """One long line, so an assertion never depends on where a line wrapped."""
    return " ".join(text.split())


class TestEveryPromptCarriesTheFenceSentence(unittest.TestCase):
    """The sentence that says what the source text is comes before the sources."""

    def test_the_sentence_sits_between_the_heading_and_the_sources(self):
        for step in drafting.STEPS:
            text = prompt(step)
            self.assertIn(constants.SOURCE_FENCE_SENTENCE, text, step)
            heading = text.index("## The sources")
            sentence = text.index(constants.SOURCE_FENCE_SENTENCE)
            placeholder = text.index("{{sources}}")
            self.assertLess(heading, sentence, step)
            self.assertLess(sentence, placeholder, step)

    def test_every_prompt_file_exists_where_the_library_looks_for_it(self):
        for step in drafting.STEPS:
            self.assertTrue(os.path.isfile(drafting.prompt_path(step, support.PLUGIN_DIR)))


class TestEveryPromptAsksForOneWholeDocument(unittest.TestCase):
    """One fence, the whole file inside it, and nothing outside it."""

    def test_each_prompt_asks_for_the_whole_document_in_one_fence(self):
        for step in drafting.STEPS:
            text = prompt(step)
            self.assertIn(
                "Return the whole document, settings block and all, as markdown "
                "inside one fence, and nothing else.",
                flat(text),
                step,
            )
            self.assertIn("put nothing outside it", flat(text), step)


class TestEveryPromptEndsWithTheHypothesisRule(unittest.TestCase):
    """Draft the whole thing, mark the person's calls, ask nothing field by field."""

    def test_the_last_section_is_the_one_that_says_draft_first(self):
        for step in drafting.STEPS:
            text = prompt(step)
            self.assertIn("## Draft first, ask afterwards", text, step)
            self.assertIn("[your call:", text, step)
            self.assertIn("Write the whole document now", flat(text), step)
            self.assertIn("one field at a time", flat(text), step)
            after = text[text.index("## Draft first, ask afterwards") :]
            self.assertNotIn("\n## ", after, step)


class TestEveryPromptCarriesTheWordsADraftMayNotUse(unittest.TestCase):
    """The banned list is written out in full, and the long dash is refused."""

    def test_every_banned_word_is_named_in_every_prompt(self):
        for step in drafting.STEPS:
            text = prompt(step).lower()
            for word in constants.DRAFT_BANNED_WORDS:
                self.assertIn(word, text, "%s is missing %s" % (step, word))

    def test_every_prompt_refuses_the_long_dash(self):
        for step in drafting.STEPS:
            self.assertIn("Never use a long dash", prompt(step), step)

    def test_no_prompt_file_holds_a_long_dash_or_a_word_from_the_tool(self):
        for step in drafting.STEPS:
            plain_language.assert_plain(
                self, drafting.prompt_path(step, support.PLUGIN_DIR)
            )


class TestEveryPromptRefusesPlaceholdersAndContactDetails(unittest.TestCase):
    """Empty rather than invented, and nobody's details carried across."""

    def test_each_prompt_says_empty_is_better_than_invented(self):
        for step in drafting.STEPS:
            self.assertIn("Empty is better than invented", prompt(step), step)

    def test_each_prompt_keeps_names_and_figures_but_never_contact_details(self):
        for step in drafting.STEPS:
            text = prompt(step)
            self.assertIn("Keep the customer names", flat(text), step)
            self.assertIn(
                "Never carry a person's contact details across", flat(text), step
            )


class TestTheProfilePromptNamesItsSections(unittest.TestCase):
    """Four sections always, four only when the sources say something."""

    def test_the_four_sections_it_always_carries_are_named(self):
        text = prompt(drafting.STEP_ICP)
        for heading in drafting.ALWAYS_SECTIONS:
            self.assertIn("**%s.**" % heading, text, heading)

    def test_the_four_optional_sections_are_named_and_left_out_when_empty(self):
        text = prompt(drafting.STEP_ICP)
        for heading in drafting.ONLY_IF_SIGNAL_SECTIONS:
            self.assertIn("**%s.**" % heading, text, heading)
        self.assertIn("leave the heading out of the document altogether", flat(text))


class TestTheDecisionPromptPresentsTheDate(unittest.TestCase):
    """The one date everything is measured against is read back for correction."""

    def test_it_asks_for_the_decided_date_to_be_corrected(self):
        text = prompt(drafting.STEP_LEDGER)
        self.assertIn("## Say the date out loud and ask about it", text)
        self.assertIn("correct it if it is wrong", flat(text))
        self.assertIn("Tell me if that is the wrong day", flat(text))

    def test_it_names_the_profile_the_decision_affects(self):
        self.assertIn("{{icp_path}}", prompt(drafting.STEP_LEDGER))


class TestThePositioningPromptPutsTheirWordsFirst(unittest.TestCase):
    """Quote what they wrote, then sharpen it, and never the other way round."""

    def test_it_says_their_words_come_first(self):
        text = prompt(drafting.STEP_POSITIONING)
        self.assertIn("## Their words first, yours second", text)
        self.assertIn("put it down word for word", flat(text))
        self.assertIn(
            "Where you have no quote for a claim, you have no claim", flat(text)
        )


class TestEveryPlaceholderTheLibraryFillsIsUsed(unittest.TestCase):
    """A placeholder nothing fills is a rule the assistant never sees."""

    def test_each_prompt_uses_the_placeholders_it_is_given(self):
        for step in drafting.STEPS:
            text = prompt(step)
            for name in ("{{sources}}", "{{company}}", "{{today}}", "{{owner_email}}"):
                self.assertIn(name, text, "%s is missing %s" % (step, name))


if __name__ == "__main__":
    unittest.main()
