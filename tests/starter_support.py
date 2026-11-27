"""What the tests of each skill GTM Base ships share (Track 4, Units T4.8 to T4.10).

Each shipped skill is read from the plugin, installed into a sandbox base the
way any company skill is, and started on the runner. The company in every
fixture is made up.
"""

import datetime
import os
import re

import support
import test_runner_contract as contract

from gtmbase import formats, operations, runner, skill_install, skillshape, starter

FIXTURES = os.path.join(support.FIXTURES_DIR, "base-skills")
TODAY = contract.TODAY
NOW = datetime.datetime(2026, 6, 15, 9, 0, 0)
REASON = "We want this job done the way our base says."
PROFILE = "context/icps.md"
POSITIONING = "context/positioning.md"
SEGMENT = "context/icps/long-distance.md"


def fixture(skill, name):
    return support.read(os.path.join(FIXTURES, skill, name))


def starter_files(skill):
    return skill_install.files_from_folder(starter.skill_folder(skill), skill)


def examples(skill):
    found = {}
    for path, text in starter_files(skill).items():
        parts = path.split("/")
        if len(parts) == 5 and parts[2] == "examples":
            found.setdefault(parts[3], {})[parts[4]] = text
    return found


def judged(files):
    """Each example's approved output and wrong outputs, judged by the contract check's rules."""
    expectations = runner.expectations_of(files["expectations.md"])
    outputs = {"output.md", "expectations.md"} | {one for one in files if one.startswith("wrong-")}
    sources = {one: text for one, text in files.items() if one not in outputs}
    approved = runner.judge_output(files["output.md"], expectations, sources)
    wrong = {
        one: runner.judge_output(files[one], expectations, sources)
        for one in files
        if one.startswith("wrong-")
    }
    return approved, wrong


def a_base(sandbox, documents, skill):
    return support.skill_base(sandbox, documents=documents, skill=skill, files={}, trust=False)


def installed(sandbox, documents, skill):
    root, base_id = a_base(sandbox, documents, skill)
    prepared = starter.prepare(root, base_id, skill, REASON, runner=support.NoRemoteRunner())
    if prepared.standard is not None:
        done = operations.approve(
            root, base_id, prepared.standard.prepared_id, prepared.standard.shown,
            runner=support.NoRemoteRunner(), now=NOW, kind=operations.KIND_CREATE,
        )
        assert done.done, done.sentence
    done = skill_install.approve(
        root, base_id, prepared.skill.prepared_id, prepared.skill.shown,
        runner_=support.NoRemoteRunner(), now=NOW,
    )
    assert done.done, done.sentence
    return root, base_id


def run(root, base_id, skill, unattended=False):
    return runner.start(
        root, base_id, skill, unattended=unattended,
        conversation=contract.CONVERSATION, runner=support.NoRemoteRunner(), now=TODAY,
    )


def no_digit_outside_a_date(text):
    _block, body = formats.split_document(text)
    return re.search(r"\d", re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", body)) is None


def admitted(files):
    return all(
        skillshape.file_problem(path, text.encode("utf-8"), skillshape.REGULAR_MODE) is None
        for path, text in files.items()
    ) and not skillshape.too_many(files)


PLAN_ONE_HEADINGS = [
    "The job's goal",
    "What is unacceptable",
    "What needs approval",
    "Checks before work is handed back",
    "How each threshold relates to a goal",
]
