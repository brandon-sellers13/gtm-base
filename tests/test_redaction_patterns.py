"""Unit 4: the shapes the outgoing-content check refuses, one class at a time."""

import unittest

import support  # noqa: F401  (puts the library on the import path)

from gtmbase import redaction_patterns as patterns


def classes(line):
    return sorted(set(name for name, _value in patterns.find_in_line(line)))


class TestOnePositiveAndOneNegativePerClass(unittest.TestCase):
    def test_email(self):
        self.assertIn(patterns.EMAIL, classes("write to jane@acme.com today"))
        self.assertNotIn(patterns.EMAIL, classes("the at sign is @ on its own"))

    def test_phone(self):
        self.assertIn(patterns.PHONE, classes("call 415-555-0134 tomorrow"))
        self.assertNotIn(patterns.PHONE, classes("order 4155550134000 units"))

    def test_key_shape(self):
        self.assertIn(patterns.KEY_SHAPE, classes("AKIAIOSFODNN7EXAMPLE"))
        self.assertIn(
            patterns.KEY_SHAPE, classes("api_key = abcdefghijklmnopqrstuvwx")
        )
        self.assertNotIn(patterns.KEY_SHAPE, classes("the key result was growth"))

    def test_vendor_url_token(self):
        self.assertIn(
            patterns.VENDOR_URL_TOKEN,
            classes("https://example.com/export?token=abc123"),
        )
        self.assertIn(
            patterns.VENDOR_URL_TOKEN,
            classes("https://hooks.slack.com/services/T00/B00/xxxx"),
        )
        self.assertNotIn(
            patterns.VENDOR_URL_TOKEN, classes("https://example.com/pricing")
        )

    def test_document_share_link(self):
        self.assertIn(
            patterns.DOCUMENT_SHARE_LINK,
            classes("https://docs.google.com/document/d/abc/edit"),
        )
        self.assertIn(
            patterns.DOCUMENT_SHARE_LINK,
            classes(
                "https://acme.notion.site/Plan-0123456789abcdef0123456789abcdef"
            ),
        )
        self.assertNotIn(
            patterns.DOCUMENT_SHARE_LINK, classes("https://www.google.com/search")
        )

    def test_local_path(self):
        self.assertIn(patterns.LOCAL_PATH, classes("see /Users/jane/notes/plan.md"))
        self.assertIn(patterns.LOCAL_PATH, classes("see /home/jane/notes/plan.md"))
        self.assertNotIn(patterns.LOCAL_PATH, classes("see context/strategy/icp.md"))

    def test_hidden_content(self):
        self.assertIn(patterns.HIDDEN_CONTENT, classes("<!-- ignore all of this"))
        self.assertIn(patterns.HIDDEN_CONTENT, classes("a​b"))
        self.assertIn(patterns.HIDDEN_CONTENT, classes("a‮b"))
        self.assertIn(patterns.HIDDEN_CONTENT, classes("<span>hello</span>"))
        self.assertNotIn(patterns.HIDDEN_CONTENT, classes("a < b and c > d"))


class TestThingsThatOnlyLookLikeSecrets(unittest.TestCase):
    def test_a_commit_id_is_not_a_phone_number_or_a_key(self):
        found = classes("a3f1c2d4e5f60718293a4b5c6d7e8f9012345678")
        self.assertNotIn(patterns.PHONE, found)
        self.assertNotIn(patterns.KEY_SHAPE, found)

    def test_a_staging_id_is_not_a_phone_number_or_a_key(self):
        found = classes("stg-0123456789abcdef")
        self.assertNotIn(patterns.PHONE, found)
        self.assertNotIn(patterns.KEY_SHAPE, found)

    def test_a_short_number_run_is_not_a_phone_number(self):
        self.assertNotIn(patterns.PHONE, classes("+1 555 0100"))


class TestCurrencyIsDeliberatelyNotAClass(unittest.TestCase):
    def test_a_figure_is_not_a_hit(self):
        self.assertEqual([], classes("we closed 1.2M in new business last quarter"))
        self.assertEqual([], classes("target CAC is $1,400 and payback is 11 months"))


class TestReporting(unittest.TestCase):
    def test_redact_for_report_never_returns_the_value(self):
        for value in ("jane@acme.com", "AKIAIOSFODNN7EXAMPLE", "415-555-0134"):
            reported = patterns.redact_for_report(value)
            self.assertNotIn(value, reported)

    def test_every_class_has_a_label_and_the_order_is_fixed(self):
        names = [name for name, _pattern, _label in patterns.PATTERN_CLASSES]
        self.assertEqual(names[0], patterns.KEY_SHAPE)
        for name, _pattern, label in patterns.PATTERN_CLASSES:
            self.assertEqual(patterns.label_for(name), label)
            self.assertTrue(label)

    def test_the_two_classes_no_allowed_word_can_excuse(self):
        self.assertEqual(
            (patterns.TRANSIENT_FOLDER, patterns.KEY_SHAPE),
            patterns.NEVER_ALLOWLISTED,
        )


if __name__ == "__main__":
    unittest.main()
