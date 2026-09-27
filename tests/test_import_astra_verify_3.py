"""Astra's third confirmation pass on the merged Units 1.7c and 1.7d, 2026-09-27.

`docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-3-astra.md` said ready with
one change: a comparison in one paragraph and a `>` in a later one, such as a
quoted reply, read together as a tag and refused an ordinary page. Each
combined case here failed on fa7d9ca. The refusals it must keep are here too,
and so is the orchestrator's rewording of the sentence said when the records
folder is not the person's alone.
"""

import unittest

import test_adoption as adoption

from gtmbase import adopt, join_flow


PAGE = "# Fintech lenders\n\n## Firmographics\n\n%s\n\n## Felt needs\n\nFast.\n"


class TestProseIsNotMarkup(unittest.TestCase):
    PROSE = (
        "CAC<LTV.\n\n> Our customers want faster reporting.",
        "Keep CAC<LTV at all times.\n\n> We heard the same from the lenders.",
        "CAC<LTV.\n\nWin rate >20%.",
        "Keep CAC<LTV at all times.\n\nWin rate >20% this quarter.",
    )
    EARLIER = (
        "CAC<LTV.", "a<b", "x <y", "LTV<3x", "<3", "a<b and c",
        "Keep CAC<LTV at all times", "a < b and c > d",
    )

    def test_comparisons_before_a_quoted_reply_or_a_later_greater_than_pass(self):
        for text in self.PROSE:
            with self.subTest(text=text):
                self.assertIn(text, adoption.clean_of(PAGE % text).text)

    def test_every_earlier_comparison_still_passes(self):
        for text in self.EARLIER:
            with self.subTest(text=text):
                self.assertIn(text, adoption.clean_of(PAGE % text).text)


class TestMarkupIsStillRefused(unittest.TestCase):
    MARKUP = (
        '<script\n data-x="ok\n\nmore">hidden instructions</script>',
        "<div\n title='a\n\nb'>hidden instructions</div>",
        '<span\n title="' + "a" * 4001 + '" style="display:none">hidden instructions</span>',
        "<span\n" + "a" * 4001 + ">hidden instructions</span>",
        '<x-hidden\n style="display:none\n\n">hidden instructions',
        # A made up name is not an element, but a value set on it is how a
        # page hides text all the same.
        '<note\n style="display:none\n\n">hidden instructions',
    )

    def test_real_markup_is_refused(self):
        for raw in self.MARKUP:
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(adopt.AdoptionRefused) as caught:
                    adoption.clean_of(PAGE % raw)
                self.assertEqual(adopt.CODE_SCREENED, caught.exception.code)


class TestTheRecordsFolderSentence(unittest.TestCase):
    def test_it_sends_the_person_to_whoever_looks_after_the_computer(self):
        self.assertEqual(
            "The folder GTM Base keeps its own records in can be changed by "
            "somebody other than you, so nothing was written. Ask whoever looks "
            "after this computer to make it yours alone, then ask again.",
            join_flow.LOCKS_NOT_PRIVATE,
        )
        self.assertEqual(
            "GTM Base could not make sure no other window was writing to the "
            "same place, so nothing was written. Ask again in a moment.",
            join_flow.NO_LOCK,
        )


if __name__ == "__main__":
    unittest.main()
