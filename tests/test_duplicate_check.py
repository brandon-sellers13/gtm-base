"""Has this exact change already been raised, accepted, or turned down."""

import json
import os
import unittest

import support

from gtmbase import constants, duplicate_check, formats
from gtmbase.validate import marker_line

STAGING = "stg-0000000000000000"
SOURCE = "src-000000000000000000000000"


class RecordingGh(object):
    """A stand-in for the GitHub tool that answers from a script and records."""

    def __init__(self, search=None, head=None, code=0):
        self.search = search if search is not None else []
        self.head = head if head is not None else []
        self.code = code
        self.calls = []

    def __call__(self, args, cwd=None, stdin=None):
        arguments = list(args)
        self.calls.append(arguments)
        if arguments[:2] == ["pr", "list"]:
            if "--head" in arguments:
                return self.code, json.dumps(self.head)
            return self.code, json.dumps(self.search)
        return self.code, ""


def review(number, state, marker, url=None):
    return {
        "number": number,
        "state": state,
        "url": url or "https://example.test/pull/%d" % number,
        "body": "## What changed\n\nsomething\n\n%s\n" % marker,
    }


def staged():
    text = support.read(os.path.join(support.TEMPLATES_DIR, "proposal-staging.md"))
    return formats.ProposalStaging.parse(text)


class TestTheMarkerItSearchesFor(unittest.TestCase):
    def test_it_uses_the_line_the_body_already_carries(self):
        self.assertEqual(
            marker_line(STAGING, STAGING, SOURCE), duplicate_check.marker_for(staged())
        )

    def test_a_body_with_no_line_falls_back_to_the_proposals_own_names(self):
        staging = staged()
        staging.pr_body = staging.pr_body.replace(
            marker_line(STAGING, STAGING, SOURCE), "nothing to see"
        )
        self.assertEqual(
            marker_line(STAGING, None, SOURCE), duplicate_check.marker_for(staging)
        )


class TestSearchingTheReviews(unittest.TestCase):
    def setUp(self):
        self.marker = marker_line(STAGING, STAGING, SOURCE)

    def test_nothing_anywhere_is_reported_as_nothing(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            gh = RecordingGh()
            found = duplicate_check.check(staged(), root, gh=gh)
            self.assertEqual(duplicate_check.KIND_NONE, found.kind)
            self.assertFalse(found.found)
            self.assertEqual(["pr", "list"], gh.calls[0][:2])
            self.assertIn("--state", gh.calls[0])
            self.assertIn("all", gh.calls[0])

    def test_an_open_review_carrying_the_line_is_somebody_elses(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            gh = RecordingGh(search=[review(7, "OPEN", self.marker)])
            found = duplicate_check.check(staged(), root, gh=gh)
            self.assertEqual(duplicate_check.KIND_OPEN, found.kind)
            self.assertEqual(7, found.pr_number)

    def test_a_closed_review_carrying_the_line_is_reported_as_closed(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            gh = RecordingGh(search=[review(8, "CLOSED", self.marker)])
            found = duplicate_check.check(staged(), root, gh=gh)
            self.assertEqual(duplicate_check.KIND_CLOSED, found.kind)
            self.assertEqual(8, found.pr_number)

    def test_a_review_that_only_mentions_the_proposal_does_not_count(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            other = review(9, "OPEN", marker_line("stg-1111111111111111"))
            gh = RecordingGh(search=[other])
            found = duplicate_check.check(staged(), root, gh=gh)
            self.assertEqual(duplicate_check.KIND_NONE, found.kind)

    def test_an_answer_that_cannot_be_read_is_recorded_and_stops_nothing(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()

            class Broken(RecordingGh):
                def __call__(self, args, cwd=None, stdin=None):
                    self.calls.append(list(args))
                    return 0, "not data at all"

            found = duplicate_check.check(staged(), root, gh=Broken())
            self.assertEqual(duplicate_check.KIND_NONE, found.kind)
            self.assertIn(duplicate_check.CODE_LIST_UNREADABLE, found.codes)

    def test_a_search_that_fails_is_recorded(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            found = duplicate_check.check(staged(), root, gh=RecordingGh(code=1))
            self.assertEqual(duplicate_check.KIND_NONE, found.kind)
            self.assertIn(duplicate_check.CODE_LIST_FAILED, found.codes)


class TestSearchingWhatIsAlreadyAccepted(unittest.TestCase):
    def test_an_accepted_record_naming_this_proposal_stops_the_run(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            text = support.read(
                os.path.join(support.TEMPLATES_DIR, "corrections-file.md")
            )
            support.write(
                os.path.join(root, constants.CORRECTIONS_DIR, "2026-01-15-%s.md" % STAGING),
                text,
            )
            found = duplicate_check.check(staged(), root, gh=RecordingGh())
            self.assertEqual(duplicate_check.KIND_MERGED, found.kind)
            self.assertTrue(found.path.endswith("2026-01-15-%s.md" % STAGING))

    def test_a_record_that_cannot_be_read_is_recorded_and_counts_as_no_match(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            support.write(
                os.path.join(root, constants.CORRECTIONS_DIR, "broken.md"),
                "this is not a record of anything\n",
            )
            found = duplicate_check.check(staged(), root, gh=RecordingGh())
            self.assertEqual(duplicate_check.KIND_NONE, found.kind)
            self.assertIn(duplicate_check.CODE_CORRECTIONS_UNREADABLE, found.codes)


class TestTheReviewAlreadyOpenForOneLineOfWork(unittest.TestCase):
    def test_it_is_found_again_rather_than_opened_twice(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            gh = RecordingGh(head=[{"number": 12, "url": "https://example.test/pull/12"}])
            found = duplicate_check.open_review_for_branch(
                constants.PROPOSAL_BRANCH_PREFIX + STAGING, root, gh=gh
            )
            self.assertEqual(12, found["number"])
            self.assertIn("--head", gh.calls[0])

    def test_no_review_for_that_line_of_work_is_reported_as_none(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            self.assertIsNone(
                duplicate_check.open_review_for_branch("proposal/nothing", root, gh=RecordingGh())
            )


if __name__ == "__main__":
    unittest.main()
