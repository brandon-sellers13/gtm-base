"""Unit 1.7a: the segment inventory, and the file name each segment would get.

Every scenario builds its material in a temporary folder with a temporary home
and seat folder, so nothing here can reach the person's real folders. The
plan's four inventory scenarios are here, and so is the safety of the file
name made from a segment's name, which is somebody's own words and is treated
as untrusted from the first character.
"""

import datetime
import io
import json
import os
import subprocess
import sys
import unittest

import plain_language
import support

from gtmbase import constants, join_flow, segments
from gtmbase.segments import InventoryRefused

SKILL_DIR = os.path.join(support.PLUGIN_DIR, "skills", "join")
SHIM = os.path.join(SKILL_DIR, "scripts", "join.py")
TODAY = datetime.date(2026, 9, 26)
SESSION = "s-segments"

# The twelve segments of a company like the one in the third real run, each
# with a finished page of its own.
TWELVE = (
    "Fintech lenders",
    "Regional banks",
    "Credit unions",
    "Payment processors",
    "Insurance carriers",
    "Wealth managers",
    "Mortgage brokers",
    "Neobanks",
    "Crypto exchanges",
    "Tax preparers",
    "Accounting firms",
    "Payroll providers",
)


def run_join(*arguments):
    """Run the join script the way the assistant runs it."""
    return subprocess.run(
        [sys.executable, SHIM] + [str(item) for item in arguments],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def pages(names, folder="segments"):
    """A folder of finished segment pages, one per name, and the folder above."""
    content = os.path.join(os.environ["HOME"], "company")
    for name in names:
        slug = segments.slug_for(name)
        support.write(
            os.path.join(content, folder, "icp-%s.md" % slug),
            "# Ideal customer profile: %s\n\nWho they are and why they buy.\n" % name,
        )
    support.write(
        os.path.join(content, folder, "positioning.md"),
        "# Positioning\n\nWhat we say about ourselves.\n",
    )
    return content


def agreed(content, run):
    """The whole folder listed and agreed to, as a plain yes would do it."""
    join_flow.list_sources(content, run, today=TODAY)
    return join_flow.freeze_sources(content, SESSION, run, today=TODAY)


def lines_for(candidates, answers):
    """One line per candidate, in the shape the join skill says to write."""
    written = []
    for candidate in candidates:
        answer, name = answers[candidate.label]
        written.append("%s %d %s" % (answer, candidate.number, name))
    return "\n".join(written) + "\n"


# --- The file name made from a segment's name --------------------------------


class TestTheFileNameMadeFromAName(unittest.TestCase):
    def test_an_ordinary_name_becomes_lower_case_words_joined_by_hyphens(self):
        self.assertEqual("fintech-lenders", segments.slug_for("Fintech lenders"))
        self.assertEqual("b2b-saas", segments.slug_for("  B2B   SaaS "))
        self.assertEqual("smb-10-50", segments.slug_for("SMB (10-50)"))

    def test_letter_case_is_folded_so_two_spellings_are_one_name(self):
        for spelling in ("Fintech", "FINTECH", "fintech", "FinTech"):
            self.assertEqual("fintech", segments.slug_for(spelling))

    def test_the_ways_one_letter_can_be_encoded_fold_to_one_name(self):
        composed = "Café owners"
        decomposed = "Café owners"
        self.assertEqual("cafe-owners", segments.slug_for(composed))
        self.assertEqual(segments.slug_for(composed), segments.slug_for(decomposed))
        # Full-width letters, a ligature, and a German sharp s.
        self.assertEqual("fintech", segments.slug_for("ＦＩＮＴＥＣＨ"))
        self.assertEqual("fintech", segments.slug_for("ﬁntech"))
        self.assertEqual("strasse", segments.slug_for("Straße"))

    def test_a_path_separator_or_a_leading_dot_never_survives(self):
        for name, expected in (
            ("../../etc/passwd", "etc-passwd"),
            (".hidden", "hidden"),
            ("a/b\\c", "a-b-c"),
            ("..", ""),
            ("/", ""),
            ("~/Documents", "documents"),
            ("name.md", "name-md"),
        ):
            with self.subTest(name=name):
                slug = segments.slug_for(name)
                self.assertEqual(expected, slug)
                self.assertNotIn("/", slug)
                self.assertNotIn("\\", slug)
                self.assertFalse(slug.startswith("."))

    def test_every_file_name_lands_directly_inside_the_segments_folder(self):
        for name in TWELVE + ("../../CLAUDE", "a/b/c", "x" * 200):
            slug = segments.slug_for(name)
            if segments.slug_problem(slug):
                continue
            where = segments.destination(slug)
            self.assertEqual(constants.SEGMENTS_DIR, os.path.dirname(where))
            self.assertEqual(where, os.path.normpath(where))

    def test_a_long_name_is_cut_at_a_word_and_never_past_the_cap(self):
        name = "The very large enterprise accounts with more than ten thousand employees worldwide"
        slug = segments.slug_for(name)
        self.assertLessEqual(len(slug), constants.SEGMENT_SLUG_MAX_CHARS)
        self.assertFalse(slug.endswith("-"))
        self.assertTrue(name.lower().replace(" ", "-").startswith(slug))
        self.assertIsNone(segments.slug_problem(slug))

    def test_a_name_with_no_letters_a_file_name_can_use_is_refused(self):
        for name in ("日本", "!!!", "--", "   "):
            with self.subTest(name=name):
                self.assertEqual(
                    segments.CODE_NO_USABLE_NAME,
                    segments.slug_problem(segments.slug_for(name)),
                )

    def test_a_name_the_trust_check_refuses_is_refused(self):
        for name in ("Claude", "CLAUDE", "Agents", "agents", "Plugins"):
            with self.subTest(name=name):
                self.assertEqual(
                    segments.CODE_RESERVED_NAME,
                    segments.slug_problem(segments.slug_for(name)),
                )

    def test_a_name_a_computer_keeps_for_itself_is_refused(self):
        for name in ("CON", "nul", "Com1", "LPT9", "aux"):
            with self.subTest(name=name):
                self.assertEqual(
                    segments.CODE_RESERVED_NAME,
                    segments.slug_problem(segments.slug_for(name)),
                )

    def test_a_file_name_not_made_here_is_checked_on_its_own(self):
        """A slug read back from a file is checked again, never trusted."""
        for slug in ("../x", ".x", "a/b", "A", "a--b", "-a", "a b", "x" * 61):
            with self.subTest(slug=slug):
                self.assertEqual(segments.CODE_NO_USABLE_NAME, segments.slug_problem(slug))
        self.assertIsNone(segments.slug_problem("fintech-lenders"))


# --- Reading the answers -----------------------------------------------------


class TestReadingTheAnswers(unittest.TestCase):
    def candidates(self, count=3):
        return [
            segments.Candidate(number, "/x/%d.md" % number, "%d.md" % number)
            for number in range(1, count + 1)
        ]

    def refused(self, text, candidates=None):
        with self.assertRaises(InventoryRefused) as caught:
            segments.settle(segments.read_lines(text), candidates or self.candidates())
        return caught.exception

    def test_the_three_answers_and_a_segment_with_no_document(self):
        inventory = segments.settle(
            segments.read_lines(
                "adopt 1 Fintech lenders\n\ndraft - Regional banks\nleave-out 3 Credit unions\n"
            ),
            self.candidates(),
        )
        self.assertEqual(
            [
                ("fintech-lenders", "adopt", 1, "/x/1.md"),
                ("regional-banks", "draft", None, ""),
                ("credit-unions", "leave-out", 3, "/x/3.md"),
            ],
            [(s.slug, s.answer, s.number, s.source) for s in inventory.segments],
        )
        self.assertEqual(
            ["context/icps/fintech-lenders.md", "context/icps/regional-banks.md"],
            inventory.segment_files(),
        )

    def test_a_line_of_the_wrong_shape_refuses_the_whole_list(self):
        for text in (
            "adopt 1\n",
            "keep 1 Fintech\n",
            "adopt one Fintech\n",
            "adopt ١ Fintech\n",
            "adopt 1 Fintech\nnonsense\n",
        ):
            with self.subTest(text=text):
                with self.assertRaises(InventoryRefused) as caught:
                    segments.read_lines(text)
                self.assertEqual(segments.CODE_UNREADABLE, caught.exception.code)

    def test_two_names_that_fold_to_one_file_name_are_caught_by_name(self):
        for first, second in (
            ("Fintech", "FINTECH"),
            ("Café owners", "Café owners"),
            ("Fintech lenders", "fintech-lenders"),
            ("Fintech lenders", "Fintech  Lenders!"),
        ):
            with self.subTest(first=first, second=second):
                refusal = self.refused(
                    "draft 1 %s\ndraft 2 %s\n" % (first, second)
                )
                self.assertEqual(segments.CODE_SAME_NAME, refusal.code)
                self.assertIn(first, refusal.sentence)
                self.assertIn(" ".join(second.split()), refusal.sentence)

    def test_one_document_named_for_two_segments_is_refused(self):
        refusal = self.refused("adopt 1 Fintech\ndraft 1 Lenders\n")
        self.assertEqual(segments.CODE_SAME_DOCUMENT, refusal.code)
        self.assertEqual(segments.SAME_DOCUMENT, refusal.sentence)

    def test_taking_a_finished_document_needs_its_number(self):
        refusal = self.refused("adopt - Fintech\n")
        self.assertEqual(segments.CODE_ADOPT_NEEDS_A_DOCUMENT, refusal.code)

    def test_a_number_nobody_was_shown_is_refused(self):
        refusal = self.refused("adopt 9 Fintech\n")
        self.assertEqual(segments.CODE_NO_SUCH_DOCUMENT, refusal.code)

    def test_a_reserved_or_unusable_name_is_refused_with_the_name_in_it(self):
        refusal = self.refused("draft - Claude\n")
        self.assertEqual(segments.CODE_RESERVED_NAME, refusal.code)
        self.assertEqual(segments.RESERVED_NAME % {"name": "Claude"}, refusal.sentence)
        refusal = self.refused("draft - 日本\n")
        self.assertEqual(segments.CODE_NO_USABLE_NAME, refusal.code)
        self.assertIn("日本", refusal.sentence)

    def test_a_name_that_is_too_long_is_refused(self):
        refusal = self.refused("draft - %s\n" % ("word " * 30))
        self.assertEqual(segments.CODE_NAME_UNUSABLE, refusal.code)

    def test_a_name_holding_a_control_character_is_refused(self):
        with self.assertRaises(InventoryRefused) as caught:
            segments.settle([("draft", None, "Fin\x1btech")], [])
        self.assertEqual(segments.CODE_NAME_UNUSABLE, caught.exception.code)

    def test_no_segment_at_all_and_too_many_are_refused(self):
        self.assertEqual(segments.CODE_NONE, self.refused("\n\n").code)
        many = "".join(
            "draft - Segment %d\n" % number
            for number in range(constants.SEGMENT_INVENTORY_MAX + 1)
        )
        self.assertEqual(segments.CODE_TOO_MANY, self.refused(many).code)


# --- The inventory through a real run ----------------------------------------


class TestTheInventoryOfARealRun(unittest.TestCase):
    def test_twelve_with_two_left_out_is_kept_and_read_back_identically(self):
        """Plan scenario: twelve, two left out, read back after the session."""
        with support.Sandbox():
            content = pages(TWELVE)
            run = join_flow.new_run(TODAY)
            agreed(content, run)

            candidates = join_flow.segment_candidates(run, today=TODAY)
            self.assertEqual(12, len(candidates))
            self.assertEqual(list(range(1, 13)), [c.number for c in candidates])
            answers = {}
            for index, candidate in enumerate(candidates):
                name = TWELVE[
                    [segments.slug_for(n) for n in TWELVE].index(
                        candidate.label[len("segments/icp-") : -len(".md")]
                    )
                ]
                answer = constants.SEGMENT_LEAVE_OUT if index in (4, 9) else constants.SEGMENT_ADOPT
                answers[candidate.label] = (answer, name)

            settled = join_flow.settle_segments(run, lines_for(candidates, answers))
            self.assertEqual(12, len(settled.segments))
            self.assertEqual(2, len(settled.left_out()))
            self.assertEqual(10, len(settled.segment_files()))

            # The session ends. Another process, knowing only the run, reads
            # back exactly what was kept.
            code = (
                "import json, sys\n"
                "from gtmbase import join_flow\n"
                "inventory = join_flow.load_inventory(sys.argv[1])\n"
                "print(json.dumps(inventory.to_payload(), sort_keys=True))\n"
            )
            finished = subprocess.run(
                [sys.executable, "-c", code, run],
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(0, finished.returncode, finished.stderr)
            self.assertEqual(
                segments.dumps(settled), finished.stdout.decode("utf-8").strip()
            )
            self.assertEqual(settled, join_flow.load_inventory(run))
            for segment in settled.segments:
                self.assertTrue(os.path.isfile(segment.source), segment)
                self.assertTrue(segment.label.startswith("segments/icp-"))

    def test_the_same_twelve_through_the_script(self):
        with support.Sandbox():
            content = pages(TWELVE)
            run = join_flow.new_run(TODAY)
            agreed(content, run)

            shown = run_join("segments", "--run", run)
            printed = shown.stdout.decode("utf-8")
            self.assertEqual(0, shown.returncode, shown.stderr)
            self.assertIn(segments.FOUND_SENTENCE % {"count": 12}, printed)
            self.assertIn(segments.ASK_SENTENCE, printed)
            self.assertIn("1. segments/", printed)
            self.assertIn("documents=12", printed)

            candidates = segments.load_candidates(join_flow.scratch_dir(run))
            by_slug = dict((segments.slug_for(name), name) for name in TWELVE)
            written = []
            for candidate in candidates:
                name = by_slug[candidate.label[len("segments/icp-") : -len(".md")]]
                answer = "leave-out" if name in ("Neobanks", "Tax preparers") else "adopt"
                written.append("%s %d %s" % (answer, candidate.number, name))
            handed = run_join("words-file", "--run", run, "--for", "segments")
            path = handed.stdout.decode("utf-8").strip().split("=", 1)[1]
            support.write(path, "\n".join(written) + "\n")

            settled = run_join("segments-settle", "--run", run, "--segments-file", path)
            said = settled.stdout.decode("utf-8")
            self.assertEqual(0, settled.returncode, said + settled.stderr.decode("utf-8"))
            self.assertIn(segments.WILL_LEAVE_OUT % {"name": "Neobanks"}, said)
            self.assertIn(segments.WILL_ADOPT % {"name": "Fintech lenders"}, said)
            self.assertIn(segments.SAVED_SENTENCE, said)
            self.assertEqual(12, said.count("segment="))
            kept = join_flow.load_inventory(run)
            self.assertEqual(2, len(kept.left_out()))
            self.assertEqual(
                ["neobanks", "tax-preparers"], sorted(s.slug for s in kept.left_out())
            )

    def test_a_company_with_one_segment_gets_only_the_profile(self):
        """Plan scenario: an inventory of one, and only the profile, at depth."""
        with support.Sandbox():
            content = pages(("Everyone we sell to",))
            run = join_flow.new_run(TODAY)
            agreed(content, run)

            candidates = join_flow.segment_candidates(run, today=TODAY)
            self.assertEqual(1, len(candidates))
            shown = run_join("segments", "--run", run)
            printed = shown.stdout.decode("utf-8")
            self.assertEqual(0, shown.returncode, shown.stderr)
            self.assertIn("codes=one-or-none", printed)
            self.assertNotIn(segments.ASK_SENTENCE, printed)

            # No numbered list was shown, so no number means a document, and
            # the one segment is named with a hyphen (finding 6 of the unit's
            # correctness review).
            with self.assertRaises(InventoryRefused) as caught:
                join_flow.settle_segments(run, "adopt 1 Everyone we sell to\n")
            self.assertEqual(segments.CODE_NO_SUCH_DOCUMENT, caught.exception.code)
            self.assertEqual([], segments.load_candidates(join_flow.scratch_dir(run)))
            inventory = join_flow.settle_segments(run, "draft - Everyone we sell to\n")
            self.assertTrue(inventory.is_single)
            self.assertEqual([], inventory.segment_files())
            self.assertEqual([segments.ONE_SEGMENT_SENTENCE], segments.readback(inventory))
            self.assertEqual(1, len(join_flow.load_inventory(run).segments))

            # The profile is drafted from the one prompt that asks for it whole.
            assembled = join_flow.assemble_step(
                "icp", run, "Acme", "dana@acme.test", today=TODAY
            )
            request = support.read(assembled.path)
            for heading in ("Firmographics", "Felt needs", "Use cases", "Current solutions"):
                self.assertIn(heading, request)

    def test_two_candidates_that_fold_to_one_name_are_caught_before_anything_is_written(self):
        """Plan scenario: the collision is caught at the inventory."""
        with support.Sandbox():
            content = pages(("Fintech lenders", "Regional banks"))
            run = join_flow.new_run(TODAY)
            agreed(content, run)
            candidates = join_flow.segment_candidates(run, today=TODAY)
            before = sorted(os.listdir(join_flow.scratch_dir(run)))

            with self.assertRaises(InventoryRefused) as caught:
                join_flow.settle_segments(
                    run,
                    "adopt %d Fintech Lenders\nadopt %d FINTECH-LENDERS\n"
                    % (candidates[0].number, candidates[1].number),
                )

            self.assertEqual(segments.CODE_SAME_NAME, caught.exception.code)
            self.assertEqual(before, sorted(os.listdir(join_flow.scratch_dir(run))))
            self.assertIsNone(join_flow.load_inventory(run))
            self.assertEqual([], [p for p in os.listdir(os.environ["HOME"]) if p == "GTM Bases"])

    def test_a_refusal_through_the_script_names_the_segments_and_keeps_nothing(self):
        with support.Sandbox():
            content = pages(("Fintech lenders", "Regional banks"))
            run = join_flow.new_run(TODAY)
            agreed(content, run)
            run_join("segments", "--run", run)
            handed = run_join("words-file", "--run", run, "--for", "segments")
            path = handed.stdout.decode("utf-8").strip().split("=", 1)[1]
            support.write(path, "draft 1 Fintech\ndraft 2 fintech\n")

            settled = run_join("segments-settle", "--run", run, "--segments-file", path)
            said = settled.stdout.decode("utf-8")

            self.assertEqual(1, settled.returncode)
            self.assertIn("codes=same-name", said)
            self.assertIn(
                segments.SAME_NAME % {"first": "Fintech", "second": "fintech"}, said
            )
            self.assertIsNone(join_flow.load_inventory(run))

    def test_versions_of_one_page_are_one_candidate_and_templates_none(self):
        with support.Sandbox():
            content = pages(("Fintech lenders", "Regional banks"))
            support.write(
                os.path.join(content, "segments", "icp-fintech-lenders-final.md"),
                "# Ideal customer profile: Fintech lenders\n\nThe signed-off one.\n",
            )
            support.write(
                os.path.join(content, "segments", "icp-template.md"),
                "# Ideal customer profile template\n\nFill this in.\n",
            )
            run = join_flow.new_run(TODAY)
            agreed(content, run)

            labels = [c.label for c in join_flow.segment_candidates(run, today=TODAY)]

            self.assertEqual(
                ["segments/icp-fintech-lenders-final.md", "segments/icp-regional-banks.md"],
                sorted(labels),
            )

    def test_nothing_is_asked_before_the_list_is_agreed_to(self):
        with support.Sandbox():
            run = join_flow.new_run(TODAY)
            shown = run_join("segments", "--run", run)
            self.assertEqual(1, shown.returncode)
            self.assertIn("codes=no-consent", shown.stdout.decode("utf-8"))

    def test_an_inventory_edited_by_hand_into_something_unsettleable_is_not_read(self):
        with support.Sandbox():
            run = join_flow.new_run(TODAY)
            join_flow.settle_segments(run, "draft - Fintech\ndraft - Banks\n")
            path = os.path.join(join_flow.scratch_dir(run), segments.INVENTORY_FILE)
            payload = json.loads(support.read(path))
            for change in (
                lambda p: p["segments"][0].update(slug="../../CLAUDE"),
                lambda p: p["segments"][1].update(slug="fintech", name="Fintech"),
                lambda p: p["segments"][0].update(answer="keep"),
                lambda p: p["segments"][0].update(name="Fin\ntech"),
                lambda p: p["segments"][0].update(answer="adopt"),
                lambda p: p.update(version=2),
            ):
                edited = json.loads(json.dumps(payload))
                change(edited)
                support.write(path, json.dumps(edited))
                with self.subTest(edited=edited):
                    self.assertIsNone(join_flow.load_inventory(run))


class TestTheWordsAPersonReads(unittest.TestCase):
    def test_every_sentence_is_registered_and_plain(self):
        registered = set(
            name for module, name in plain_language.PYTHON_SENTENCES if module == "segments"
        )
        for name in (
            "FOUND_SENTENCE",
            "ASK_SENTENCE",
            "WILL_ADOPT",
            "WILL_DRAFT",
            "WILL_LEAVE_OUT",
            "SAVED_SENTENCE",
            "ONE_SEGMENT_SENTENCE",
            "SAME_NAME",
            "NO_USABLE_NAME",
            "RESERVED_NAME",
            "SAME_DOCUMENT",
            "NAME_UNUSABLE",
            "TOO_MANY",
            "NONE_NAMED",
        ):
            self.assertIn(name, registered)
            text = getattr(segments, name)
            self.assertEqual([], plain_language.find_banned(text), name)
            self.assertEqual([], plain_language.find_dashes(text), name)
            self.assertEqual([], plain_language.find_old_paths(text), name)
            self.assertEqual([], plain_language.find_banned_person_facing(text), name)

    def test_the_skill_asks_the_question_the_script_prints(self):
        text = support.read(os.path.join(SKILL_DIR, "SKILL.md"))
        step = text.split("### Step 5d.")[1].split("### Step 6.")[0]
        self.assertIn(segments.ASK_SENTENCE, step)
        self.assertIn("segments-settle", step)
        self.assertIn("codes=one-or-none", step)


class TestTheInventoryAfterTheCorrectnessReview(unittest.TestCase):
    """Findings 3, 5 and 7 of the Unit 1.7a correctness review."""

    def test_an_inventory_settle_would_refuse_is_never_read(self):
        """Finding 3: load settles the answers again and compares the whole."""
        with support.Sandbox():
            content = pages(("Fintech lenders", "Regional banks"))
            run = join_flow.new_run(TODAY)
            agreed(content, run)
            candidates = join_flow.segment_candidates(run, today=TODAY)
            join_flow.settle_segments(
                run,
                "adopt %d Fintech lenders\ndraft %d Regional banks\n"
                % (candidates[0].number, candidates[1].number),
            )
            self.assertIsNotNone(join_flow.load_inventory(run))
            path = os.path.join(join_flow.scratch_dir(run), segments.INVENTORY_FILE)
            payload = json.loads(support.read(path))
            many = [
                {
                    "name": "Segment %d" % number,
                    "slug": "segment-%d" % number,
                    "answer": "draft",
                    "number": None,
                    "source": "",
                    "label": "",
                }
                for number in range(constants.SEGMENT_INVENTORY_MAX + 1)
            ]
            for change in (
                lambda p: p["segments"][0].update(source="/etc/hosts"),
                lambda p: p["segments"][0].update(label="elsewhere.md"),
                lambda p: p["segments"][1].update(number=p["segments"][0]["number"]),
                lambda p: p["segments"][1].update(source=p["segments"][0]["source"]),
                lambda p: p["segments"][1].update(number=0),
                lambda p: p["segments"][1].update(number=True),
                lambda p: p.update(segments=many),
                lambda p: p["segments"].append(dict(p["segments"][0], extra=1)),
            ):
                edited = json.loads(json.dumps(payload))
                change(edited)
                support.write(path, json.dumps(edited))
                with self.subTest(edited=edited):
                    self.assertIsNone(join_flow.load_inventory(run))
            support.write(path, json.dumps(payload))
            self.assertIsNotNone(join_flow.load_inventory(run))

    def test_a_lone_segment_left_out_is_read_back_as_left_out(self):
        """Finding 5: one segment left out is not a profile written in full."""
        inventory = segments.settle(
            segments.read_lines("leave-out - Credit unions\n"), []
        )
        self.assertFalse(inventory.is_single)
        self.assertEqual([], inventory.segment_files())
        self.assertEqual(
            [
                segments.WILL_LEAVE_OUT % {"name": "Credit unions"},
                segments.SAVED_SENTENCE,
            ],
            segments.readback(inventory),
        )

    def test_letters_outside_a_to_z_keep_the_words_apart(self):
        """Finding 7: a dash or a letter with no parts no longer vanishes."""
        for name, expected in (
            ("Retail\u2013Wholesale", "retail-wholesale"),
            ("\u00d8resund", "oresund"),
            ("\u0141\u00f3d\u017a Retail", "lodz-retail"),
            ("\u00c6sir", "aesir"),
            ("Hotels\u00b7Resorts", "hotels-resorts"),
        ):
            with self.subTest(name=name):
                self.assertEqual(expected, segments.slug_for(name))

    def test_the_newer_reserved_device_names_are_refused_too(self):
        for name in ("com0", "LPT0"):
            with self.subTest(name=name):
                self.assertEqual(
                    segments.CODE_RESERVED_NAME,
                    segments.slug_problem(segments.slug_for(name)),
                )


if __name__ == "__main__":
    unittest.main()
