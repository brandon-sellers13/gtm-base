"""Unit 2: the file formats, their parsers, and what each one refuses."""

import datetime
import json
import os
import unittest

import support
from support import FIXTURES_DIR, TEMPLATES_DIR, read

from gtmbase import formats
from gtmbase.errors import PathError, ValidationError
from gtmbase.validate import marker_line

TODAY = datetime.date(2026, 6, 1)
STG = "stg-" + "0" * 16
OTHER_STG = "stg-" + "1" * 16
SRC = "src-" + "0" * 24
RUN = "run-2026-01-01-00000000"
QID = "q-" + "0" * 20


def ledger_fields(**overrides):
    fields = {
        "id": STG,
        "decided_on": "2026-01-01",
        "written_on": "2026-01-02",
        "decided_by": "Jane Doe",
        "source": "the weekly go to market meeting",
        "review_by": "2026-04-01",
        "origin": "ledger",
        "status": "open",
        "affects": ["context/strategy/icp.md"],
        "body": "We sell to companies of twenty to two hundred people.",
    }
    fields.update(overrides)
    return fields


class TestFrontmatterParser(unittest.TestCase):
    def test_reads_scalars_lists_and_block_lists(self):
        text = (
            "---\n"
            "id: stg-0000000000000000\n"
            "count: 3\n"
            "ready: true\n"
            "day: 2026-01-01\n"
            "inline: [a, b]\n"
            "block:\n"
            "- one\n"
            "- two\n"
            "empty: []\n"
            "---\n"
            "\n"
            "Body text.\n"
        )
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
        self.assertEqual("stg-0000000000000000", fields["id"])
        self.assertEqual(3, fields["count"])
        self.assertIs(True, fields["ready"])
        self.assertEqual("2026-01-01", fields["day"])
        self.assertEqual(["a", "b"], fields["inline"])
        self.assertEqual(["one", "two"], fields["block"])
        self.assertEqual([], fields["empty"])
        self.assertEqual("Body text.\n", body)

    def test_refuses_tabs_nesting_duplicates_and_bad_keys(self):
        cases = {
            "tab": "---\nid:\tone\n---\n",
            "nested-mapping": "---\nowner:\n  name: jane\n---\n",
            "duplicate-key": "---\nid: one\nid: two\n---\n",
            "bad-key": "---\nOwner-Name: jane\n---\n",
            "orphan-list-item": "---\n- one\n---\n",
        }
        for expected, text in cases.items():
            with self.assertRaises(ValidationError) as caught:
                block, _body = formats.split_document(text)
                formats.parse_frontmatter(block)
            self.assertEqual(expected, caught.exception.code, expected)

    def test_field_order_survives_a_round_trip(self):
        fields = {"b": 1, "a": 2, "c": ["x", "y"]}
        text = formats.render_frontmatter(fields)
        self.assertEqual(["b: 1", "a: 2", "c: [x, y]"], text.strip().split("\n")[1:-1])
        self.assertEqual(fields, formats.parse_frontmatter(text.strip().split("\n", 1)[1].rsplit("\n---", 1)[0]))

    def test_a_file_with_no_settings_block_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            formats.split_document("# Just a heading\n")
        self.assertEqual("no-frontmatter", caught.exception.code)


class TestLedgerEntry(unittest.TestCase):
    def test_round_trip_keeps_every_field(self):
        entry = formats.LedgerEntry(run_id=RUN, **ledger_fields())
        text = entry.render()
        back = formats.LedgerEntry.parse(text)
        self.assertEqual(text, back.render())
        for name in ("id", "decided_on", "written_on", "decided_by", "source",
                     "review_by", "origin", "status", "run_id", "affects", "body"):
            self.assertEqual(getattr(entry, name), getattr(back, name), name)

    def test_an_entry_with_every_field_validates(self):
        entry = formats.LedgerEntry(run_id=RUN, **ledger_fields())
        self.assertIs(entry, entry.validate(TODAY))

    def test_the_same_entry_without_review_by_fails_and_names_the_field(self):
        entry = formats.LedgerEntry(**ledger_fields())
        text = entry.render().replace("review_by: 2026-04-01\n", "")
        with self.assertRaises(ValidationError) as caught:
            formats.LedgerEntry.parse(text)
        self.assertEqual("missing-field", caught.exception.code)
        self.assertIn("review_by", str(caught.exception))

    def test_a_decision_dated_in_the_future_is_malformed(self):
        entry = formats.LedgerEntry(
            **ledger_fields(decided_on="2026-12-01", written_on="2026-12-01", review_by="2027-01-01")
        )
        with self.assertRaises(ValidationError) as caught:
            entry.validate(TODAY)
        self.assertEqual("decided-in-future", caught.exception.code)

    def test_a_review_date_before_the_decision_is_malformed(self):
        entry = formats.LedgerEntry(**ledger_fields(review_by="2025-12-01"))
        with self.assertRaises(ValidationError) as caught:
            entry.validate(TODAY)
        self.assertEqual("review-before-decision", caught.exception.code)

    def test_writing_it_down_before_the_decision_is_malformed(self):
        entry = formats.LedgerEntry(**ledger_fields(written_on="2025-12-30"))
        with self.assertRaises(ValidationError) as caught:
            entry.validate(TODAY)
        self.assertEqual("written-before-decision", caught.exception.code)

    def test_an_affected_path_outside_context_is_refused(self):
        entry = formats.LedgerEntry(**ledger_fields(affects=["../.env"]))
        with self.assertRaises(PathError):
            entry.validate(TODAY)

    def test_a_field_we_do_not_know_is_refused(self):
        text = formats.LedgerEntry(**ledger_fields()).render()
        text = text.replace("status: open", "status: open\nsecret: yes")
        with self.assertRaises(ValidationError) as caught:
            formats.LedgerEntry.parse(text)
        self.assertEqual("unknown-field", caught.exception.code)


class TestConfirmationLine(unittest.TestCase):
    def test_round_trip_keeps_the_order_and_the_empty_values(self):
        line = formats.ConfirmationLine(
            "2026-09-05", "14:03:00Z", "context/strategy/icp.md", "ledger", STG, QID, None
        )
        text = line.render()
        self.assertEqual(
            "date=2026-09-05 time=14:03:00Z file=context/strategy/icp.md "
            "trigger=ledger entry=%s question=%s run=-" % (STG, QID),
            text,
        )
        back = formats.ConfirmationLine.parse(text)
        self.assertEqual(text, back.render())
        self.assertIsNone(back.run)

    def test_a_line_carries_no_author(self):
        line = formats.ConfirmationLine(
            "2026-09-05", "14:03:00Z", "context/strategy/icp.md", "threshold", None, QID, None
        )
        self.assertNotIn("author", line.render())
        self.assertNotIn("@", line.render())

    def test_one_malformed_line_is_reported_and_the_others_survive(self):
        good_one = formats.ConfirmationLine(
            "2026-09-01", "09:00:00Z", "context/strategy/icp.md", "threshold", None, QID, None
        ).render()
        good_two = formats.ConfirmationLine(
            "2026-09-05", "14:03:00Z", "context/strategy/icp.md", "ledger", STG, QID, None
        ).render()
        text = (
            "# a comment\n"
            "\n"
            + good_one
            + "\n"
            + "date=2026-09-03 file=context/strategy/icp.md trigger=threshold\n"
            + good_two
            + "\n"
        )
        lines, malformed = formats.parse_confirmations_file(text)
        self.assertEqual(2, len(lines))
        self.assertEqual([good_one, good_two], [line.render() for line in lines])
        self.assertEqual(1, len(malformed))
        self.assertEqual(4, malformed[0].number)
        self.assertEqual("wrong-token-count", malformed[0].code)

    def test_a_drafted_line_without_a_run_is_malformed(self):
        text = formats.ConfirmationLine(
            "2026-09-05", "14:03:00Z", "context/strategy/icp.md", "drafted", None, None, RUN
        ).render().replace("run=" + RUN, "run=-")
        with self.assertRaises(ValidationError) as caught:
            formats.ConfirmationLine.parse(text)
        self.assertEqual("drafted-without-run", caught.exception.code)

    def test_a_ledger_line_without_an_entry_is_malformed(self):
        text = formats.ConfirmationLine(
            "2026-09-05", "14:03:00Z", "context/strategy/icp.md", "ledger", STG, QID, None
        ).render().replace("entry=" + STG, "entry=-")
        with self.assertRaises(ValidationError) as caught:
            formats.ConfirmationLine.parse(text)
        self.assertEqual("ledger-without-entry", caught.exception.code)

    def test_values_out_of_order_are_malformed(self):
        with self.assertRaises(ValidationError) as caught:
            formats.ConfirmationLine.parse(
                "time=14:03:00Z date=2026-09-05 file=context/strategy/icp.md "
                "trigger=threshold entry=- question=- run=-"
            )
        self.assertEqual("wrong-token-order", caught.exception.code)

    def test_a_trigger_we_do_not_know_is_malformed(self):
        with self.assertRaises(ValidationError):
            formats.ConfirmationLine.parse(
                "date=2026-09-05 time=14:03:00Z file=context/strategy/icp.md "
                "trigger=guessed entry=- question=- run=-"
            )


class TestCorrectionsFile(unittest.TestCase):
    def build(self, **overrides):
        fields = {
            "kind": "correction",
            "date": "2026-01-13",
            "staging_id": STG,
            "entry_id": STG,
            "source_id": SRC,
            "intake_path": "drop",
            "mode": "decision",
            "third_party": False,
            "content_hash": "a" * 64,
            "correction_class": "wrong-definition",
            "marker": marker_line(STG, STG, SRC),
            "touched_paths": ["context/strategy/icp.md", "work/decisions/%s.md" % STG],
            "what_changed": "It said any size and now says twenty to two hundred people.",
            "why": "The meeting decided it and the document was never brought in line.",
        }
        fields.update(overrides)
        return formats.CorrectionsFile(**fields)

    def test_round_trip_keeps_every_field(self):
        correction = self.build()
        text = correction.render()
        back = formats.CorrectionsFile.parse(text)
        self.assertEqual(text, back.render())
        self.assertEqual("It said any size and now says twenty to two hundred people.", back.what_changed)
        self.assertFalse(back.third_party)
        correction.validate()

    def test_the_marker_is_plain_visible_text_and_never_a_hidden_comment(self):
        text = self.build().render()
        for line in text.split("\n"):
            self.assertNotIn("<!--", line)
        hidden = self.build(marker="<!-- %s -->" % marker_line(STG, STG, SRC))
        with self.assertRaises(ValidationError) as caught:
            hidden.validate()
        self.assertEqual("hidden-marker", caught.exception.code)

    def test_a_marker_naming_a_different_proposal_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            self.build(marker=marker_line(OTHER_STG, STG, SRC)).validate()
        self.assertEqual("marker-mismatch", caught.exception.code)

    def test_a_touched_path_outside_the_allowed_folders_is_refused(self):
        with self.assertRaises(PathError):
            self.build(touched_paths=["plugins/gtm-base/hooks/hooks.json"]).validate()

    def test_an_onboarding_note_is_a_kind_this_file_accepts(self):
        self.build(kind="onboarding-note").validate()


class TestPendingItem(unittest.TestCase):
    def payload(self, **overrides):
        value = json.loads(read(os.path.join(FIXTURES_DIR, "pending-item.json")))
        value.update(overrides)
        return value

    def test_the_fixture_loads_and_keeps_its_shape(self):
        item = formats.load_pending(os.path.join(FIXTURES_DIR, "pending-item.json"))
        self.assertEqual("decision", item.mode)
        self.assertEqual(1, len(item.edits))
        self.assertEqual("replace", item.edits[0].op)
        self.assertEqual(item.raw_span, item.redacted_excerpt)

    def test_a_field_we_do_not_know_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            formats.parse_pending(self.payload(extra="anything"))
        self.assertEqual("unknown-field", caught.exception.code)

    def test_a_missing_field_is_refused(self):
        value = self.payload()
        del value["confidence"]
        with self.assertRaises(ValidationError) as caught:
            formats.parse_pending(value)
        self.assertEqual("missing-field", caught.exception.code)

    def test_an_edit_outside_context_is_refused(self):
        value = self.payload()
        value["edits"][0]["path"] = "../.env"
        with self.assertRaises(PathError):
            formats.parse_pending(value)

    def test_a_file_larger_than_the_cap_is_refused(self):
        import tempfile

        from gtmbase import constants

        folder = tempfile.mkdtemp(prefix="gtm-base-pending-")
        try:
            path = os.path.join(folder, "big.json")
            support.write(path, " " * (constants.MAX_PENDING_ITEM_BYTES + 1))
            with self.assertRaises(ValidationError) as caught:
                formats.load_pending(path)
            self.assertEqual("too-large", caught.exception.code)
        finally:
            import shutil

            shutil.rmtree(folder, ignore_errors=True)


class TestPullRequestBody(unittest.TestCase):
    def fields(self, **overrides):
        value = {
            "before": "The customer profile says any size.",
            "after": "The customer profile says twenty to two hundred people.",
            "why": "The team decided it and the document was never brought in line.",
            "evidence": "Decision %s." % STG,
            "confidence": "high",
            "rule_changed": None,
            "marker": marker_line(STG, STG, SRC),
        }
        value.update(overrides)
        return value

    def test_round_trip_keeps_every_field(self):
        text = formats.render_pr_body(self.fields())
        back = formats.parse_pr_body(text)
        self.assertEqual(self.fields()["before"], back["before"])
        self.assertEqual(self.fields()["after"], back["after"])
        self.assertEqual("None", back["rule_changed"])
        self.assertEqual(text, formats.render_pr_body(back))

    def test_every_required_section_is_present_and_in_order(self):
        text = formats.render_pr_body(self.fields())
        present, missing = formats.required_sections_present(text)
        self.assertTrue(present)
        self.assertEqual([], missing)
        self.assertEqual(list(formats.PR_SECTIONS), formats.section_order(text))

    def test_a_missing_section_is_named(self):
        text = formats.render_pr_body(self.fields())
        without = text.replace("## Evidence\n\nDecision %s.\n\n" % STG, "")
        present, missing = formats.required_sections_present(without)
        self.assertFalse(present)
        self.assertEqual(["Evidence"], missing)
        with self.assertRaises(ValidationError) as caught:
            formats.parse_pr_body(without)
        self.assertEqual("missing-section", caught.exception.code)

    def test_sections_out_of_order_are_reported(self):
        text = formats.render_pr_body(self.fields())
        swapped = text.replace("## Why", "## Evidence", 1).replace(
            "## Evidence\n\nDecision", "## Why\n\nDecision", 1
        )
        present, missing = formats.required_sections_present(swapped)
        self.assertFalse(present)
        self.assertEqual(["out-of-order"], missing)

    def test_the_fixed_sentence_and_the_hint_are_both_there(self):
        text = formats.render_pr_body(self.fields())
        self.assertIn(formats.ABOUT_SENTENCE, text)
        self.assertIn(formats.KEEP_THE_DECISION_HINT, text)
        without = text.replace(formats.ABOUT_SENTENCE, "Written by a person.")
        with self.assertRaises(ValidationError) as caught:
            formats.parse_pr_body(without)
        self.assertEqual("missing-about-sentence", caught.exception.code)

    def test_the_marker_is_the_last_line_and_is_never_a_hidden_comment(self):
        text = formats.render_pr_body(self.fields())
        lines = [line for line in text.strip().split("\n") if line.strip()]
        self.assertEqual(marker_line(STG, STG, SRC), lines[-1])
        self.assertNotIn("<!--", text)
        with self.assertRaises(ValidationError):
            formats.render_pr_body(self.fields(marker="<!-- %s -->" % marker_line(STG)))


class TestProposalStaging(unittest.TestCase):
    def test_round_trip_keeps_the_decision_the_edits_and_the_body(self):
        text = read(os.path.join(FIXTURES_DIR, "proposal-staging.md"))
        staging = formats.ProposalStaging.parse(text)
        staging.validate()
        self.assertEqual(text, staging.render())
        self.assertEqual(1, len(staging.edits))
        self.assertEqual("context/strategy/icp.md", staging.edits[0].path)
        self.assertEqual("## Firmographics", staging.edits[0].heading)
        self.assertIn("---", staging.decision_block)
        self.assertTrue(staging.excerpt)

    def test_a_proposal_with_no_decision_block_still_round_trips(self):
        text = read(os.path.join(FIXTURES_DIR, "proposal-staging.md"))
        staging = formats.ProposalStaging.parse(text)
        staging.decision_block = None
        rendered = staging.render()
        self.assertNotIn("## Decision", rendered)
        back = formats.ProposalStaging.parse(rendered)
        back.validate()
        self.assertIsNone(back.decision_block)
        self.assertEqual(rendered, back.render())

    def test_edit_text_holding_a_fence_still_round_trips(self):
        text = read(os.path.join(FIXTURES_DIR, "proposal-staging.md"))
        staging = formats.ProposalStaging.parse(text)
        staging.edits[0].text = "Here is a block:\n\n```\nsome text\n```\n"
        rendered = staging.render()
        back = formats.ProposalStaging.parse(rendered)
        self.assertEqual(staging.edits[0].text, back.edits[0].text)
        self.assertEqual(rendered, back.render())

    def test_a_different_schema_is_refused(self):
        text = read(os.path.join(FIXTURES_DIR, "proposal-staging.md"))
        staging = formats.ProposalStaging.parse(text.replace("schema: 1", "schema: 2"))
        with self.assertRaises(ValidationError) as caught:
            staging.validate()
        self.assertEqual("wrong-schema", caught.exception.code)


class TestInboxItem(unittest.TestCase):
    def test_round_trip_keeps_every_field(self):
        text = read(os.path.join(FIXTURES_DIR, "inbox-item.md"))
        item = formats.InboxItem.parse(text)
        item.validate()
        self.assertEqual(text, item.render())
        self.assertEqual(["Jane Doe", "Sam Lee"], item.participants)
        self.assertEqual("private-channel", item.visibility)
        self.assertFalse(item.partial)


class TestTemplates(unittest.TestCase):
    def test_every_template_parses_with_its_own_parser(self):
        entry = formats.LedgerEntry.parse(read(os.path.join(TEMPLATES_DIR, "ledger-entry.md")))
        entry.validate(TODAY)

        lines, malformed = formats.parse_confirmations_file(
            read(os.path.join(TEMPLATES_DIR, "confirmation-line.md"))
        )
        self.assertEqual(3, len(lines))
        self.assertEqual([], malformed)

        correction = formats.CorrectionsFile.parse(
            read(os.path.join(TEMPLATES_DIR, "corrections-file.md"))
        )
        correction.validate()

        staging = formats.ProposalStaging.parse(
            read(os.path.join(TEMPLATES_DIR, "proposal-staging.md"))
        )
        staging.validate()

        body = formats.parse_pr_body(read(os.path.join(TEMPLATES_DIR, "pr-body.md")))
        self.assertEqual("high", body["confidence"])

        item = formats.load_pending(os.path.join(TEMPLATES_DIR, "pending-item.json"))
        self.assertEqual("decision", item.mode)

    def test_every_template_uses_the_placeholder_values(self):
        for name in ("ledger-entry.md", "corrections-file.md", "proposal-staging.md", "pr-body.md"):
            text = read(os.path.join(TEMPLATES_DIR, name))
            self.assertIn("stg-0000000000000000", text, name)

    def test_no_template_holds_an_em_dash_or_an_en_dash(self):
        import plain_language

        # The folder now holds the whole template a new base is built from as
        # well as the single files, so every file underneath it is read, not
        # only the names sitting at the top.
        for folder, _subfolders, filenames in os.walk(TEMPLATES_DIR):
            for name in sorted(filenames):
                path = os.path.join(folder, name)
                self.assertEqual([], plain_language.find_dashes(read(path)), path)


if __name__ == "__main__":
    unittest.main()
