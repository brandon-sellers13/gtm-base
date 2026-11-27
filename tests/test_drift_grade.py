"""Track 4, Unit T4.8: drift grade, the first skill GTM Base ships.

Drift grade checks a piece of marketing work against the versions of the
base's documents the team approved, and ends in fixes to the piece or a
proposed context change. It ships in the plugin and reaches a base only the
way a company's own skill does: the skill folder through the install of Plan 1
Unit 4.2b, and its standard through the create operation of Unit 4.2a. It then
runs on the thin runner of Unit 3.1.

These check the written skill, its examples, its standard, the install and the
runner's outcomes. Whether a grade is right is the approver's read of a real
run, which these do not claim to test. The company in every fixture is made
up.
"""

import datetime
import os
import re
import unittest

import support
import test_runner_contract as contract

from gtmbase import (
    constants,
    docpaths,
    formats,
    inventory,
    names,
    operations,
    runner,
    skill_install,
    skillshape,
    starter,
)

SKILL = starter.DRIFT_GRADE
SKILL_MD = "skills/%s/SKILL.md" % SKILL
REFERENCE = "skills/%s/references/what-to-check.md" % SKILL
STANDARD = "standards/drift-grade.md"
PROFILE = "context/icps.md"
POSITIONING = "context/positioning.md"
MESSAGING = "context/messaging.md"
OPTIONAL = [
    MESSAGING,
    "context/voice.md",
    "context/competitors.md",
    "context/buyer-personas.md",
]
FIXTURE = os.path.join(support.FIXTURES_DIR, "base-skills", "drift-grade")
OWNER = "owner@example.com"
WRITER = "writer@example.com"
STRANGER = "stranger@example.com"
TODAY = contract.TODAY
NOW = datetime.datetime(2026, 6, 15, 9, 0, 0)
REASON = "We want every page checked against the positioning we approved."


def the_starter_files():
    return skill_install.files_from_folder(starter.skill_folder(SKILL), SKILL)


def examples():
    found = {}
    for path, text in the_starter_files().items():
        parts = path.split("/")
        if len(parts) == 5 and parts[2] == "examples":
            found.setdefault(parts[3], {})[parts[4]] = text
    return found


def the_documents(messaging=False):
    found = {
        PROFILE: support.read(os.path.join(FIXTURE, "icps.md")),
        POSITIONING: support.read(os.path.join(FIXTURE, "positioning.md")),
    }
    if messaging:
        found[MESSAGING] = support.read(os.path.join(FIXTURE, "messaging.md"))
    return found


def a_base(sandbox, documents=None):
    return support.skill_base(
        sandbox,
        documents=the_documents() if documents is None else documents,
        skill=SKILL,
        files={},
        trust=False,
    )


def seat_address(root, address):
    support.git(["config", "--local", "user.email", address], cwd=root)


def prepare(root, base_id):
    return starter.prepare(root, base_id, SKILL, REASON, runner=support.NoRemoteRunner())


def approve_standard(root, base_id, prepared):
    return operations.approve(
        root, base_id, prepared.standard.prepared_id, prepared.standard.shown,
        runner=support.NoRemoteRunner(), now=NOW, kind=operations.KIND_CREATE,
    )


def approve_skill(root, base_id, prepared):
    return skill_install.approve(
        root, base_id, prepared.skill.prepared_id, prepared.skill.shown,
        runner_=support.NoRemoteRunner(), now=NOW,
    )


def installed(sandbox, documents=None):
    root, base_id = a_base(sandbox, documents)
    prepared = prepare(root, base_id)
    done = approve_standard(root, base_id, prepared)
    assert done.done, done.sentence
    done = approve_skill(root, base_id, prepared)
    assert done.done, done.sentence
    return root, base_id


def run(root, base_id, unattended=False):
    return runner.start(
        root, base_id, SKILL, unattended=unattended,
        conversation=contract.CONVERSATION, runner=support.NoRemoteRunner(), now=TODAY,
    )


def skill_files_on_disk(root):
    folder = os.path.join(root, constants.SKILLS_DIR, SKILL)
    found = []
    for dirpath, _dirs, files in os.walk(folder):
        found.extend(files)
    return found


class TheStarterSkill(unittest.TestCase):
    def test_it_passes_the_contract_check(self):
        contract_ = runner.check_skill(SKILL, the_starter_files())
        self.assertTrue(contract_.passed, contract_.problems)

    def test_each_approved_output_passes_and_each_wrong_output_fails(self):
        for name, files in sorted(examples().items()):
            expectations = runner.expectations_of(files["expectations.md"])
            outputs = {"output.md", "expectations.md"} | {
                one for one in files if one.startswith("wrong-")
            }
            sources = {one: text for one, text in files.items() if one not in outputs}
            with self.subTest(example=name):
                self.assertEqual([], runner.judge_output(files["output.md"], expectations, sources))
                wrong = [one for one in files if one.startswith("wrong-")]
                self.assertTrue(wrong)
                for one in wrong:
                    self.assertTrue(
                        runner.judge_output(files[one], expectations, sources), one
                    )

    def test_it_holds_the_three_examples_the_plan_names(self):
        found = examples()
        self.assertEqual({"on-message", "dropped-claim", "buyer-moved"}, set(found))
        proposes = {
            name: ("must include", "Proposed context change")
            in [(kind.rstrip(":"), words) for kind, words in runner.expectations_of(files["expectations.md"])]
            for name, files in found.items()
        }
        self.assertEqual({"on-message": False, "dropped-claim": False, "buyer-moved": True}, proposes)

    def test_the_wrong_outputs_are_the_ones_the_plan_names(self):
        found = examples()
        # A finding citing a document that was not read.
        self.assertIn(MESSAGING, found["on-message"]["wrong-cites-unread.md"])
        self.assertNotIn("messaging.md", found["on-message"])
        # A grade that edits the base instead of proposing.
        self.assertIn("I updated %s" % POSITIONING, found["dropped-claim"]["wrong-edits-positioning.md"])
        self.assertIn("I changed %s" % PROFILE, found["buyer-moved"]["wrong-edits-profile.md"])

    def test_it_declares_what_the_plan_says(self):
        declared = runner.declaration_of(the_starter_files()[SKILL_MD])
        self.assertEqual([], declared.problems)
        self.assertEqual([PROFILE, POSITIONING], declared.required)
        self.assertEqual(OPTIONAL, declared.optional)
        self.assertEqual(STANDARD, declared.standard)
        self.assertEqual(starter.standard_path(SKILL), declared.standard)

    def test_the_body_names_no_command_so_a_chat_can_serve_it(self):
        for path, text in the_starter_files().items():
            if "/examples/" in path:
                continue
            with self.subTest(path=path):
                self.assertFalse(runner.names_a_command(text))
                self.assertNotIn("python", text)
                self.assertNotIn("scripts/", text)

    def test_every_file_is_a_shape_a_base_admits(self):
        files = the_starter_files()
        for path, text in files.items():
            with self.subTest(path=path):
                self.assertIsNone(
                    skillshape.file_problem(path, text.encode("utf-8"), skillshape.REGULAR_MODE)
                )
        self.assertFalse(skillshape.too_many(files))

    def test_the_starter_names_no_owner_because_the_install_stamps_one(self):
        block, _body = formats.split_document(the_starter_files()[SKILL_MD])
        self.assertNotIn("owner", formats.parse_frontmatter(block))

    def test_the_starter_lives_in_the_plugin_and_never_in_the_company_template(self):
        self.assertTrue(os.path.isdir(starter.skill_folder(SKILL)))
        for template in (support.TEMPLATES_DIR, os.path.join(support.REPO_ROOT, "templates")):
            self.assertFalse(
                os.path.exists(os.path.join(template, "company-base", "skills", SKILL))
            )
            self.assertFalse(
                os.path.exists(os.path.join(template, "company-base", STANDARD))
            )

    def test_an_unknown_name_has_no_folder(self):
        self.assertIsNone(starter.skill_folder("weekly-readout"))
        self.assertIsNone(starter.skill_folder("../drift-grade"))


class TheStandard(unittest.TestCase):
    def setUp(self):
        self.text = starter.standard_text(SKILL)

    def test_it_is_a_standard_document(self):
        self.assertEqual(docpaths.KIND_STANDARD, docpaths.classify(STANDARD).kind)
        block, _body = formats.split_document(self.text)
        fields = formats.parse_frontmatter(block)
        self.assertEqual("standard", fields["kind"])
        self.assertNotIn("owner", fields)

    def test_it_has_the_five_sections_in_words(self):
        headings = re.findall(r"^## (.*)$", self.text, re.MULTILINE)
        self.assertEqual(
            [
                "The job's goal",
                "What is unacceptable",
                "What needs approval",
                "Checks before work is handed back",
                "How each threshold relates to a goal",
            ],
            headings,
        )

    def test_it_carries_no_digit_outside_a_date(self):
        """Plan 1 Unit 3.5's lint for a standard, applied here until that unit merges."""
        _block, body = formats.split_document(self.text)
        without_dates = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", body)
        self.assertIsNone(re.search(r"\d", without_dates))

    def test_it_says_what_the_plan_calls_unacceptable(self):
        lowered = self.text.lower()
        for words in (
            "no longer carries",
            "no document in the base supports",
            "competitor",
            "audience the customer profile does not name",
            "any change to a document in the base",
            "quotes the line in the piece and the line in the base",
        ):
            self.assertIn(words, lowered)


class Installing(unittest.TestCase):
    def test_a_creator_who_is_not_the_base_owner_needs_the_base_owners_yes(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            self.assertIn("[[file: %s]]" % SKILL_MD, prepared.skill.artifact)
            self.assertIn(STANDARD, prepared.standard.artifact)
            self.assertTrue(approve_standard(root, base_id, prepared).done)
            first = approve_skill(root, base_id, prepared)
            self.assertEqual(skill_install.CODE_WAITING, first.code)
            self.assertEqual([], skill_files_on_disk(root))
            seat_address(root, OWNER)
            second = approve_skill(root, base_id, prepared)
            self.assertTrue(second.done, second.sentence)
            self.assertIn("owner: %s" % WRITER, support.read(os.path.join(root, SKILL_MD)))
            self.assertIn("owner: %s" % WRITER, support.read(os.path.join(root, STANDARD)))
            self.assertEqual("", support.status_of(root).strip())

    def test_the_whole_folder_is_written_as_one_manifest(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox)
            written = sorted(
                os.path.relpath(os.path.join(dirpath, one), root).replace(os.sep, "/")
                for dirpath, _dirs, files in os.walk(os.path.join(root, constants.SKILLS_DIR, SKILL))
                for one in files
            )
            self.assertEqual(sorted(the_starter_files()), written)
            from gtmbase import authority

            manifest = authority.manifest_of(root, base_id, SKILL)
            self.assertEqual(set(the_starter_files()), set(manifest.files))
            self.assertTrue(authority.trusts(base_id, manifest))

    def test_without_the_base_owner_or_an_administrator_nothing_is_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            approve_skill(root, base_id, prepared)
            seat_address(root, STRANGER)
            done = approve_skill(root, base_id, prepared)
            self.assertEqual(skill_install.CODE_NOT_ALLOWED, done.code)
            self.assertEqual([], skill_files_on_disk(root))

    def test_a_base_that_already_holds_the_standard_keeps_its_own(self):
        with support.Sandbox() as sandbox:
            own = support.skill_document("standard", "Our own drift grade standard")
            documents = dict(the_documents(), **{STANDARD: own})
            root, base_id = a_base(sandbox, documents)
            prepared = prepare(root, base_id)
            self.assertIsNone(prepared.standard)
            self.assertTrue(approve_skill(root, base_id, prepared).done)
            self.assertEqual(own, support.read(os.path.join(root, STANDARD)))

    def test_a_name_gtm_base_does_not_ship_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            with self.assertRaises(Exception) as caught:
                starter.prepare(root, base_id, "weekly-readout", REASON, runner=support.NoRemoteRunner())
            self.assertEqual(starter.CODE_NOT_A_STARTER, getattr(caught.exception, "code", None))


class Running(unittest.TestCase):
    def test_on_a_base_without_messaging_it_is_ready_with_each_gap_named(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox)
            result = run(root, base_id)
            self.assertEqual(runner.OUTCOME_READY_WITH_GAPS, result.outcome)
            self.assertEqual(OPTIONAL, result.gaps)
            self.assertEqual([STANDARD, PROFILE, POSITIONING], list(result.documents))
            self.assertEqual([SKILL_MD, REFERENCE], list(result.instructions))
            rendered = result.render()
            self.assertIn(names.document_name(MESSAGING), rendered)
            # The skill's own instructions say what to do with a gap.
            self.assertIn("name it under the gaps", result.instructions[SKILL_MD])

    def test_with_messaging_it_is_read_and_is_not_a_gap(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox, the_documents(messaging=True))
            result = run(root, base_id)
            self.assertIn(MESSAGING, result.documents)
            self.assertNotIn(MESSAGING, result.gaps)

    def test_with_the_positioning_flagged_an_attended_run_returns_the_block_and_no_grade(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox)
            contract.a_change_about(root, POSITIONING)
            result = run(root, base_id)
            self.assertEqual(runner.OUTCOME_FLAGGED, result.outcome)
            self.assertTrue(result.waiting)
            self.assertFalse(result.hands_back)
            rendered = result.render()
            self.assertIn(runner.FLAGGED_ATTENDED_SAYS % SKILL, rendered)
            self.assertNotIn("# Drift grade", rendered)
            self.assertNotIn("Verdict:", rendered)

    def test_unattended_and_flagged_the_positioning_is_held(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox)
            contract.a_change_about(root, POSITIONING)
            result = run(root, base_id, unattended=True)
            self.assertEqual([POSITIONING], result.held)

    def test_without_its_standard_it_does_not_run(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            prepared = prepare(root, base_id)
            self.assertTrue(approve_skill(root, base_id, prepared).done)
            result = run(root, base_id)
            self.assertEqual(runner.REFUSED_REQUIRED, result.refusal)


class TheInventoryOffer(unittest.TestCase):
    def sentences(self, root, base_id):
        return inventory.take(root, base_id, runner=support.NoRemoteRunner(), today=TODAY).sentences()

    def offer(self):
        return starter.offer_sentence(SKILL)

    def test_a_base_with_a_profile_and_a_positioning_is_offered_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            self.assertIn(self.offer(), self.sentences(root, base_id))

    def test_a_base_without_a_positioning_is_not(self):
        with support.Sandbox() as sandbox:
            documents = the_documents()
            del documents[POSITIONING]
            root, base_id = a_base(sandbox, documents)
            self.assertNotIn(self.offer(), self.sentences(root, base_id))

    def test_a_base_that_has_it_is_not_offered_it_again(self):
        with support.Sandbox() as sandbox:
            root, base_id = installed(sandbox)
            self.assertNotIn(self.offer(), self.sentences(root, base_id))

    def test_the_offer_is_a_sentence_and_never_a_second_ask(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            ask = inventory.take(root, base_id, runner=support.NoRemoteRunner(), today=TODAY).ask()
            self.assertNotEqual(self.offer(), ask)


if __name__ == "__main__":
    unittest.main()
