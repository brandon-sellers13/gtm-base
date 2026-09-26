"""Unit 1.7b: the umbrella over several segments, and each segment at depth.

Every scenario builds its material and its base in a temporary folder with a
temporary home and seat folder, so nothing here reaches the person's real
folders. The plan's drafting scenarios are here, and so are the checks Unit
1.7a asked for before any segment's file is written: a file already in the
base under a name that folds to the same one, in either folder segments have
been kept in, is refused by name and never written over.
"""

import datetime
import io
import os
import subprocess
import sys
import unicodedata
import unittest

import plain_language
import support

from gtmbase import (
    base_reader,
    callmarkers,
    constants,
    drafting,
    formats,
    join_flow,
    machine,
    paths,
    segments,
    stale_check,
)
from gtmbase.errors import DraftError, ReviewError

DRAFTS = os.path.join(support.FIXTURES_DIR, "drafts")
SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "join")
SHIM = os.path.join(SKILL_DIR, "scripts", "join.py")
TODAY = datetime.date(2026, 9, 26)
NOW = datetime.datetime(2026, 9, 26, 9, 15, 0)
EMAIL = "dana@acme.test"
SESSION = "s-umbrella"

THREE = ("Fintech lenders", "Regional banks", "Credit unions")
ICP = "context/icps.md"


def captured(name):
    with io.open(os.path.join(DRAFTS, name), encoding="utf-8") as handle:
        return handle.read()


def run_join(*arguments):
    """Run the join script the way the assistant runs it."""
    return subprocess.run(
        [sys.executable, SHIM] + [str(item) for item in arguments],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def pending_umbrella(left_out="Credit unions"):
    """The umbrella fixture with one segment left out, said the fixed way."""
    text = captured("umbrella.md")
    start = text.index("### %s" % left_out)
    stop = text.index("\n## ", start)
    return (
        text[:start]
        + "### %s\n\n%s\n" % (left_out, constants.UMBRELLA_PENDING_SENTENCE)
        + text[stop:]
    )


def umbrella_text(drafted=(), left_out=()):
    """An umbrella over the named segments, drafted ones and ones left out."""
    parts = [
        "```markdown",
        "---",
        "kind: icp",
        "owner: owner@example.com",
        "last_confirmed: 2026-09-26",
        "sources: [segments/icp-fintech-lenders.md]",
        "status: draft",
        "---",
        "",
        "# Ideal customer profile",
        "",
        "## Who we sell to",
        "",
        "Lenders that underwrite small business credit by hand.",
        "",
        "## Segments",
        "",
    ]
    for name in drafted:
        parts += [
            "### %s" % name,
            "",
            "A group of lenders that buys for its own reasons.",
            "",
        ]
    for name in left_out:
        parts += ["### %s" % name, "", constants.UMBRELLA_PENDING_SENTENCE, ""]
    parts += [
        "## What they share",
        "",
        "Each of them reads bank statements by hand.",
        "```",
        "",
    ]
    return "\n".join(parts)


def segment_text(name):
    """The segment fixture, written about one named segment."""
    return captured("segment.md").replace("# Fintech lenders", "# %s" % name)


class Company(object):
    """A company with one finished page per segment, set up to the inventory."""

    def __init__(self, names=THREE, answers=None):
        support.write(
            os.path.join(os.environ["HOME"], ".gitconfig"),
            "[user]\n\temail = %s\n\tname = Dana\n" % EMAIL,
        )
        self.content = os.path.join(os.environ["HOME"], "company")
        for name in names:
            support.write(
                os.path.join(
                    self.content, "segments", "icp-%s.md" % segments.slug_for(name)
                ),
                "# Ideal customer profile: %s\n\nWho %s are and why they buy.\n"
                % (name, name),
            )
        support.write(
            os.path.join(self.content, "segments", "positioning.md"),
            "# Positioning\n\nWhat we say about ourselves.\n",
        )
        self.run = join_flow.new_run(TODAY)
        join_flow.list_sources(self.content, self.run, today=TODAY)
        join_flow.freeze_sources(self.content, SESSION, self.run, today=TODAY)
        candidates = join_flow.segment_candidates(self.run, today=TODAY)
        answers = answers or {}
        written = []
        if len(candidates) < 2:
            # With one document no numbered list is shown, so each segment is
            # named with a hyphen, the way the join skill says.
            candidates = []
            written = [
                "%s - %s" % (answers.get(name, constants.SEGMENT_DRAFT), name)
                for name in names
            ]
        for candidate in candidates:
            slug = candidate.label[len("segments/icp-") : -len(".md")]
            name = [n for n in names if segments.slug_for(n) == slug][0]
            written.append(
                "%s %d %s"
                % (answers.get(name, constants.SEGMENT_DRAFT), candidate.number, name)
            )
        self.inventory = join_flow.settle_segments(self.run, "\n".join(written) + "\n")
        self.root = None

    def write_draft(self, step, text, segment=None):
        settled = (
            join_flow.segment_to_draft(self.run, segment) if segment else None
        )
        path = join_flow.draft_path(self.run, step, settled)
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def review(self, step, text, segment=None):
        path = self.write_draft(step, text, segment)
        return join_flow.review_step(
            step, path, base_root=self.root, run_id=self.run, segment=segment
        )

    def approve(self, step, text, segment=None, questions_open=False):
        path = self.write_draft(step, text, segment)
        if self.root is None:
            result = join_flow.approve_step(
                step,
                path,
                self.run,
                parent=join_flow.propose_location("Acme", cwd=self.content).parent,
                company="Acme",
                now=NOW,
                segment=segment,
                questions_open=questions_open,
            )
            self.root = result.root
            return result
        return join_flow.approve_step(
            step,
            path,
            self.run,
            base_root=self.root,
            now=NOW,
            segment=segment,
            questions_open=questions_open,
        )

    def umbrella_and_positioning(self, umbrella=None):
        self.approve(drafting.STEP_UMBRELLA, umbrella or captured("umbrella.md"))
        self.approve(drafting.STEP_POSITIONING, captured("positioning.md"))
        return self

    def read(self, relative):
        return support.read(os.path.join(self.root, relative))

    def base_id(self):
        return paths.resolve_base(self.root, machine.load_machine_state()).base_id


# --- The happy path ----------------------------------------------------------


class TestThreeSegments(unittest.TestCase):
    """Plan scenario: three segments, an umbrella of three short paragraphs,
    and three segment drafts at depth."""

    def test_an_umbrella_and_three_segment_drafts_at_depth(self):
        with support.Sandbox():
            company = Company()
            self.assertEqual(drafting.STEP_UMBRELLA, join_flow.profile_step(company.run))

            request = support.read(
                join_flow.assemble_step(
                    drafting.STEP_UMBRELLA, company.run, "Acme", EMAIL, today=TODAY
                ).path
            )
            for name in THREE:
                self.assertIn(name, request)
            for heading in constants.UMBRELLA_SECTIONS:
                self.assertIn("**%s.**" % heading, request)

            company.umbrella_and_positioning()
            umbrella = company.read(ICP)
            paragraphs = drafting.segment_paragraphs(formats.split_document(umbrella)[1])
            self.assertEqual(list(THREE), [heading for heading, _p in paragraphs])
            for _heading, paragraph in paragraphs:
                self.assertTrue(paragraph)
                self.assertLess(len(paragraph.split()), 80, paragraph)

            for name in THREE:
                slug = segments.slug_for(name)
                result = company.approve(
                    drafting.STEP_SEGMENT, segment_text(name), segment=slug
                )
                self.assertEqual(segments.destination(slug), result.path)
                block, body = formats.split_document(company.read(result.path))
                fields = formats.parse_frontmatter(block)
                self.assertEqual(constants.SEGMENT_KIND, fields["kind"])
                self.assertEqual(EMAIL, fields["owner"])
                self.assertTrue(body.startswith("\n# %s" % name) or ("# %s" % name) in body)
                for heading in drafting.ALWAYS_SECTIONS:
                    self.assertIn("## %s" % heading, body)
                self.assertIn(
                    "\n\n".join(segment_text(name).split("## Firmographics")[1:2])[:60],
                    body,
                )

            files = dict(
                (info.path, info)
                for info in base_reader.context_files(company.root)
            )
            for name in THREE:
                self.assertIn(segments.destination(segments.slug_for(name)), files)
            # Each segment was approved with its own dated yes, like any draft.
            lines = support.read(
                os.path.join(
                    company.root,
                    constants.CONFIRMATIONS_DIR,
                    segments.destination("fintech-lenders").replace("/", "--"),
                )
            )
            self.assertIn("trigger=drafted", lines)

    def test_a_segment_request_reads_its_own_page_first_and_holds_its_name_as_data(self):
        with support.Sandbox():
            company = Company()
            assembled = join_flow.assemble_step(
                drafting.STEP_SEGMENT,
                company.run,
                "Acme",
                EMAIL,
                today=TODAY,
                segment="regional-banks",
            )
            self.assertTrue(
                assembled.included_labels[0].split(" (")[0].endswith(
                    "icp-regional-banks.md"
                ),
                assembled.included_labels,
            )
            request = support.read(assembled.path)
            self.assertIn("do not compress", request.lower())
            name_at = request.index("Regional banks")
            self.assertLess(request.index(constants.SOURCE_FENCE_SENTENCE), name_at)
            for field in ("{{segment}}", "{{inventory}}", "{{scope}}", "{{sources}}"):
                self.assertNotIn(field, request)
            self.assertEqual(
                "segment-regional-banks-draft.md",
                os.path.basename(
                    join_flow.draft_path(
                        company.run,
                        drafting.STEP_SEGMENT,
                        join_flow.segment_to_draft(company.run, "regional-banks"),
                    )
                ),
            )


# --- What the umbrella may and may not say ------------------------------------


class TestWhatTheUmbrellaSays(unittest.TestCase):
    def test_a_segment_left_out_is_named_as_pending_in_words_and_nothing_is_a_link(self):
        """Plan scenario: pending in words, and nothing in the umbrella a link."""
        with support.Sandbox():
            company = Company(answers={"Credit unions": constants.SEGMENT_LEAVE_OUT})
            reviewed = company.review(drafting.STEP_UMBRELLA, pending_umbrella())
            self.assertTrue(reviewed.ready, reviewed.codes)
            company.umbrella_and_positioning(pending_umbrella())
            body = formats.split_document(company.read(ICP))[1]
            paragraphs = dict(drafting.segment_paragraphs(body))
            self.assertEqual(constants.UMBRELLA_PENDING_SENTENCE, paragraphs["Credit unions"])
            self.assertNotIn("](", body)
            self.assertNotIn(".md", body)
            self.assertNotIn(constants.SEGMENTS_DIR, body)

    def test_a_segment_left_out_but_described_is_refused(self):
        with support.Sandbox():
            company = Company(answers={"Credit unions": constants.SEGMENT_LEAVE_OUT})
            reviewed = company.review(drafting.STEP_UMBRELLA, captured("umbrella.md"))
            self.assertFalse(reviewed.ready)
            self.assertIn(
                drafting.CODE_SEGMENT_NOT_PENDING % "credit-unions", reviewed.codes
            )

    def test_a_segment_being_drafted_is_never_said_to_be_pending(self):
        with support.Sandbox():
            company = Company()
            reviewed = company.review(drafting.STEP_UMBRELLA, pending_umbrella())
            self.assertFalse(reviewed.ready)
            self.assertIn(
                drafting.CODE_SEGMENT_SAID_PENDING % "credit-unions", reviewed.codes
            )

    def test_a_missing_segment_or_one_nobody_settled_is_refused(self):
        with support.Sandbox():
            company = Company()
            text = captured("umbrella.md")
            missing = text.replace("### Regional banks", "### Savings banks")
            reviewed = company.review(drafting.STEP_UMBRELLA, missing)
            self.assertFalse(reviewed.ready)
            self.assertIn(drafting.CODE_SEGMENT_MISSING % "regional-banks", reviewed.codes)
            self.assertIn(drafting.CODE_SEGMENT_NOT_SETTLED, reviewed.codes)
            for code in reviewed.codes:
                self.assertNotIn("Savings", code)

    def test_a_link_a_web_address_or_a_file_name_is_refused(self):
        text = captured("umbrella.md")
        for linked in (
            "See [the page](context/icps/fintech-lenders.md).",
            "More at https://acme.test/segments.",
            "The detail is in fintech-lenders.md.",
            "See [[Fintech lenders]].",
            "Write to <mailto:someone>.",
        ):
            with self.subTest(linked=linked):
                with self.assertRaises(DraftError) as caught:
                    drafting.parse(
                        drafting.STEP_UMBRELLA,
                        text.replace(
                            "Their credit teams are small",
                            linked + " Their credit teams are small",
                        ),
                    )
                self.assertEqual(drafting.CODE_LINK, caught.exception.code)

    def test_the_three_parts_are_required(self):
        for heading in constants.UMBRELLA_SECTIONS:
            with self.subTest(heading=heading):
                text = captured("umbrella.md").replace("## %s" % heading, "## Something")
                with self.assertRaises(DraftError) as caught:
                    drafting.parse(drafting.STEP_UMBRELLA, text)
                self.assertEqual(
                    drafting.CODE_EMPTY_SECTION % heading, caught.exception.code
                )

    def test_the_umbrella_carries_what_the_base_covers_from_the_held_answer(self):
        with support.Sandbox():
            company = Company()
            # The scope cannot be held after the list is agreed to, so it is
            # put where the list keeps it, as a yes given with a scope would.
            from gtmbase.fsutil import atomic_write_json, read_json

            consent = os.path.join(join_flow.scratch_dir(company.run), join_flow.CONSENT_FILE)
            payload = read_json(consent)
            payload["scope"] = "Lending"
            atomic_write_json(consent, payload, inside=paths.seat_home())
            company.umbrella_and_positioning()
            fields = formats.parse_frontmatter(formats.split_document(company.read(ICP))[0])
            self.assertEqual("Lending", fields[constants.COVERS_FIELD])


# --- Which step drafts the profile -------------------------------------------


class TestTheStepTheInventoryAllows(unittest.TestCase):
    def test_several_segments_are_never_folded_into_one_profile(self):
        with support.Sandbox():
            company = Company()
            with self.assertRaises(ReviewError) as caught:
                join_flow.assemble_step("icp", company.run, "Acme", EMAIL, today=TODAY)
            self.assertEqual(join_flow.CODE_UMBRELLA_INSTEAD, caught.exception.code)
            path = company.write_draft("icp", captured("icp.md"))
            with self.assertRaises(ReviewError):
                join_flow.approve_step(
                    "icp",
                    path,
                    company.run,
                    parent=join_flow.propose_location("Acme", cwd=company.content).parent,
                    company="Acme",
                    now=NOW,
                )

            shown = run_join("preview", "--step", "icp", "--run", company.run)
            said = shown.stdout.decode("utf-8")
            self.assertIn("codes=%s" % join_flow.CODE_UMBRELLA_INSTEAD, said)
            self.assertIn("drafted across all of them", said)

    def test_one_segment_keeps_the_profile_and_refuses_the_umbrella(self):
        with support.Sandbox():
            company = Company(names=("Everyone",))
            self.assertEqual(drafting.STEP_ICP, join_flow.profile_step(company.run))
            with self.assertRaises(ReviewError) as caught:
                join_flow.preview_step(company.run, drafting.STEP_UMBRELLA, today=TODAY)
            self.assertEqual(join_flow.CODE_NO_SEVERAL_SEGMENTS, caught.exception.code)

    def test_only_a_segment_settled_to_be_drafted_can_be_drafted(self):
        with support.Sandbox():
            company = Company(
                answers={
                    "Credit unions": constants.SEGMENT_LEAVE_OUT,
                    "Regional banks": constants.SEGMENT_ADOPT,
                }
            )
            for slug in ("credit-unions", "regional-banks", "savings-banks", None):
                with self.subTest(slug=slug):
                    with self.assertRaises(ReviewError) as caught:
                        join_flow.preview_step(
                            company.run, drafting.STEP_SEGMENT, today=TODAY, segment=slug
                        )
                    self.assertEqual(segments.CODE_NOT_TO_DRAFT, caught.exception.code)
            join_flow.preview_step(
                company.run, drafting.STEP_SEGMENT, today=TODAY, segment="fintech-lenders"
            )

    def test_a_segment_never_makes_a_base_and_is_never_skipped(self):
        with support.Sandbox():
            company = Company()
            path = company.write_draft(
                drafting.STEP_SEGMENT, segment_text("Fintech lenders"), "fintech-lenders"
            )
            with self.assertRaises(ReviewError):
                join_flow.approve_step(
                    drafting.STEP_SEGMENT,
                    path,
                    company.run,
                    parent=join_flow.propose_location("Acme", cwd=company.content).parent,
                    company="Acme",
                    now=NOW,
                    segment="fintech-lenders",
                )
            company.umbrella_and_positioning()
            with self.assertRaises(ReviewError):
                join_flow.skip_step(drafting.STEP_SEGMENT, company.root, now=NOW)
            self.assertFalse(
                os.path.exists(
                    os.path.join(company.root, segments.destination("fintech-lenders"))
                )
            )


# --- A file already in the way -----------------------------------------------


class TestAFileAlreadyInTheWay(unittest.TestCase):
    """Unit 1.7a's note: settle never looks at the base, so this does."""

    def _refused_and_untouched(self, company, relative, text):
        before = company.read(relative)
        path = company.write_draft(
            drafting.STEP_SEGMENT, segment_text("Fintech lenders"), "fintech-lenders"
        )
        with self.assertRaises(ReviewError) as caught:
            join_flow.approve_step(
                drafting.STEP_SEGMENT,
                path,
                company.run,
                base_root=company.root,
                now=NOW,
                segment="fintech-lenders",
            )
        self.assertEqual(segments.CODE_FILE_TAKEN, caught.exception.code)
        self.assertEqual(before, company.read(relative))
        self.assertEqual(text, before)

    def _put(self, company, relative, text="# Somebody's own page\n"):
        support.write(os.path.join(company.root, relative), text)
        support.git(["add", "-A"], cwd=company.root)
        support.git(["commit", "-q", "-m", "their own page"], cwd=company.root)
        return text

    def test_a_file_differing_only_in_letter_case_is_refused(self):
        with support.Sandbox():
            company = Company().umbrella_and_positioning()
            names = sorted(os.listdir(os.path.join(company.root, constants.SEGMENTS_DIR)))
            relative = constants.SEGMENTS_DIR + "/Fintech-Lenders.md"
            text = self._put(company, relative)
            self._refused_and_untouched(company, relative, text)
            self.assertEqual(
                sorted(names + ["Fintech-Lenders.md"]),
                sorted(os.listdir(os.path.join(company.root, constants.SEGMENTS_DIR))),
            )

    def test_a_file_whose_letters_are_encoded_another_way_is_refused(self):
        with support.Sandbox():
            company = Company().umbrella_and_positioning()
            # "Fintech" with the i written as a letter and a separate mark.
            name = unicodedata.normalize("NFD", "Fïntech lenders.md")
            relative = constants.SEGMENTS_DIR + "/" + name
            text = self._put(company, relative)
            self.assertEqual("fintech-lenders", segments.slug_for(name[: -len(".md")]))
            self._refused_and_untouched(company, relative, text)

    def test_a_file_a_move_left_under_its_original_name_is_refused(self):
        """A base moved by Unit 1.5b keeps a segment under its older name."""
        with support.Sandbox():
            company = Company().umbrella_and_positioning()
            relative = constants.SEGMENTS_DIR + "/fintech_lenders.md"
            text = self._put(company, relative)
            self._refused_and_untouched(company, relative, text)

    def test_a_file_in_the_older_segment_folder_is_refused(self):
        with support.Sandbox():
            company = Company().umbrella_and_positioning()
            relative = constants.LEGACY_SEGMENTS_DIR + "/fintech-lenders.md"
            text = self._put(company, relative)
            self._refused_and_untouched(company, relative, text)

    def test_the_refusal_names_the_segment_through_the_script(self):
        with support.Sandbox():
            company = Company().umbrella_and_positioning()
            self._put(company, constants.SEGMENTS_DIR + "/FINTECH-LENDERS.md")
            path = company.write_draft(
                drafting.STEP_SEGMENT, segment_text("Fintech lenders"), "fintech-lenders"
            )
            finished = run_join(
                "approve",
                "--step",
                "segment",
                "--segment",
                "fintech-lenders",
                "--draft",
                path,
                "--run",
                company.run,
                "--base",
                company.root,
            )
            said = finished.stdout.decode("utf-8")
            self.assertEqual(1, finished.returncode, said)
            self.assertIn(segments.FILE_TAKEN % {"name": "Fintech lenders"}, said)
            self.assertIn("codes=%s" % segments.CODE_FILE_TAKEN, said)

    def test_a_segment_folder_that_is_a_link_is_refused(self):
        with support.Sandbox() as sandbox:
            company = Company().umbrella_and_positioning()
            folder = os.path.join(company.root, constants.SEGMENTS_DIR)
            for name in os.listdir(folder):
                os.remove(os.path.join(folder, name))
            os.rmdir(folder)
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere)
            os.symlink(elsewhere, folder)
            support.git(["add", "-A"], cwd=company.root)
            support.git(["commit", "-q", "-m", "a link"], cwd=company.root)
            path = company.write_draft(
                drafting.STEP_SEGMENT, segment_text("Fintech lenders"), "fintech-lenders"
            )
            with self.assertRaises(ReviewError) as caught:
                join_flow.approve_step(
                    drafting.STEP_SEGMENT,
                    path,
                    company.run,
                    base_root=company.root,
                    now=NOW,
                    segment="fintech-lenders",
                )
            self.assertEqual(segments.CODE_FOLDER_NOT_ORDINARY, caught.exception.code)
            self.assertEqual([], os.listdir(elsewhere))

    def test_a_link_is_caught_by_the_check_itself(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            os.makedirs(os.path.join(root, "context"))
            elsewhere = os.path.join(sandbox.path, "elsewhere")
            os.makedirs(elsewhere)
            self.assertTrue(segments.folder_is_ordinary(root))
            os.symlink(elsewhere, os.path.join(root, constants.SEGMENTS_DIR))
            self.assertFalse(segments.folder_is_ordinary(root))


# --- A draft that leaves questions for the person ------------------------------


class TestADraftThatAsksSomething(unittest.TestCase):
    """The third real run saved an approved file with a marker nobody saw."""

    MARKED = "[your call: is it forty people or fifty?]"

    def test_the_count_is_said_and_approval_waits_for_the_persons_choice(self):
        with support.Sandbox():
            company = Company()
            text = captured("umbrella.md").replace(
                "from about forty people", "from about forty people %s" % self.MARKED
            )
            reviewed = company.review(drafting.STEP_UMBRELLA, text)
            self.assertTrue(reviewed.ready, reviewed.codes)
            self.assertEqual(1, reviewed.questions)

            path = company.write_draft(drafting.STEP_UMBRELLA, text)
            said = run_join(
                "review", "--step", "umbrella", "--draft", path, "--run", company.run
            ).stdout.decode("utf-8")
            self.assertIn("ready", said)
            self.assertIn("questions=1", said)
            self.assertIn(join_flow.DRAFT_HAS_ONE_QUESTION, said)
            self.assertNotIn("forty people or fifty", said)

            with self.assertRaises(ReviewError) as caught:
                company.approve(drafting.STEP_UMBRELLA, text)
            self.assertEqual(join_flow.CODE_QUESTIONS_OPEN, caught.exception.code)
            self.assertIsNone(company.root)

            company.approve(drafting.STEP_UMBRELLA, text, questions_open=True)
            self.assertIn(self.MARKED, company.read(ICP))

    def test_a_question_left_open_is_the_closing_finding(self):
        with support.Sandbox():
            company = Company()
            text = captured("umbrella.md").replace(
                "from about forty people", "from about forty people %s" % self.MARKED
            )
            company.approve(drafting.STEP_UMBRELLA, text, questions_open=True)
            company.approve(drafting.STEP_POSITIONING, captured("positioning.md"))
            closed = join_flow.close_run(company.root, company.run, now=TODAY)
            self.assertEqual(
                stale_check.FINDING_OPEN_QUESTION_ONE % "your customer profile",
                closed.finding,
            )
            self.assertNotIn("forty people or fifty", closed.finding)

    def test_the_sentence_counts_several(self):
        self.assertEqual(
            join_flow.DRAFT_HAS_QUESTIONS % 3, join_flow.draft_questions_sentence(3)
        )
        self.assertEqual("", join_flow.draft_questions_sentence(0))


# --- The prompts -------------------------------------------------------------


def prompt(step):
    return support.read(drafting.prompt_path(step, support.PLUGIN_DIR))


def flat(text):
    return " ".join(text.split())


class TestThePrompts(unittest.TestCase):
    def test_the_umbrella_prompt_names_its_parts_and_the_pending_words(self):
        text = prompt(drafting.STEP_UMBRELLA)
        for heading in constants.UMBRELLA_SECTIONS:
            self.assertIn("**%s.**" % heading, text)
        self.assertIn(constants.UMBRELLA_PENDING_SENTENCE, text)
        self.assertIn("Nothing in this document is a link", flat(text))
        self.assertIn("Never say whether a segment has a document of its own", flat(text))

    def test_the_segment_prompt_asks_for_depth_and_forbids_compression(self):
        text = flat(prompt(drafting.STEP_SEGMENT))
        self.assertIn("So do not compress", text)
        self.assertIn("do not fold this segment into the others", text)
        for heading in drafting.ALWAYS_SECTIONS:
            self.assertIn("**%s.**" % heading, text)

    def test_what_the_person_said_arrives_after_the_fence_sentence(self):
        for step in (drafting.STEP_UMBRELLA, drafting.STEP_SEGMENT):
            text = prompt(step)
            sentence = text.index(constants.SOURCE_FENCE_SENTENCE)
            for field in ("{{inventory}}", "{{scope}}"):
                self.assertLess(sentence, text.index(field), (step, field))
        self.assertLess(
            prompt(drafting.STEP_SEGMENT).index(constants.SOURCE_FENCE_SENTENCE),
            prompt(drafting.STEP_SEGMENT).index("{{segment}}"),
        )

    def test_every_prompt_says_what_an_open_question_costs(self):
        """Both older prompts asked for the marker; each now says the rule."""
        for step in drafting.CONTEXT_STEPS:
            text = flat(prompt(step))
            self.assertIn("counts as unfinished until they answer it", text, step)
            self.assertIn("never in the settings block and never in a heading", text, step)

    def test_the_one_segment_prompt_is_still_the_profile(self):
        self.assertEqual("draft-icp.md", drafting.PROMPT_FILES[drafting.STEP_ICP])


class TestTheWordsAPersonReads(unittest.TestCase):
    def test_every_new_sentence_is_registered_and_plain(self):
        registered = set(plain_language.PYTHON_SENTENCES)
        for pair in (
            ("constants", "UMBRELLA_PENDING_SENTENCE"),
            ("segments", "FILE_TAKEN"),
            ("segments", "FOLDER_NOT_ORDINARY"),
            ("join_flow", "DRAFT_HAS_ONE_QUESTION"),
            ("join_flow", "DRAFT_HAS_QUESTIONS"),
        ):
            self.assertIn(pair, registered)

    def test_the_skill_carries_the_segment_step_and_the_wait_lines(self):
        text = support.read(os.path.join(SKILL_DIR, "SKILL.md"))
        self.assertIn("### Step 6c. Each segment to draft, at full depth", text)
        self.assertIn(drafting.PROGRESS[drafting.STEP_UMBRELLA], text)
        self.assertIn(drafting.PROGRESS[drafting.STEP_SEGMENT], text)
        self.assertIn("--questions-open", text)


if __name__ == "__main__":
    unittest.main()
