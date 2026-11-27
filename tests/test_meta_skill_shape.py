"""Plan 1, Unit 3.6, the repository side: a nightly ad skill on the runner.

The real skill, its engine and its nights belong to Brandon's live session D
and stay outside this repository. What is tested here is the shape such a
skill takes on the runner, on a made-up copy written from scratch for a
made-up courier app (`tests/fixtures/base-skills/meta-ads/`): its declarations
and examples through the contract check, the outcomes the runner gives it on
the nights that matter (a flagged goals document, a missing standard, missing
goals), the session start naming it once this computer trusts it, and the
runner commands in a scheduled prompt run exactly as written. Whether the
skill does good work is the replay of real nights, which no test claims.
"""

import os
import shlex
import subprocess
import sys
import unittest

import support
import test_runner_contract as contract

from gtmbase import authority, constants, runner, session_start

SKILL = "meta-ads"
FIXTURE = os.path.join(support.FIXTURES_DIR, "base-skills", SKILL)
STANDARD = "standards/meta-creative-testing.md"
GOALS = "context/courier-app/goals.md"
METRICS = "context/courier-app/metrics.md"
USE_SKILL = os.path.join(support.PLUGIN_DIR, "skills", "use-skill", "scripts", "use_skill.py")

# The scheduled prompt's own words, with the runner's start as its first
# command, as the move of the real task will write it (Unit 3.6's checklist,
# step six). The test runs this command exactly as written.
SCHEDULED_PROMPT = (
    "This is a run nobody is watching. Run first, before anything else:\n"
    "python3 %s --start meta-ads --unattended\n" % USE_SKILL
)


def skill_files():
    """The fixture skill, keyed by the base paths it takes when installed."""
    found = {}
    for dirpath, _dirs, names in os.walk(FIXTURE):
        for name in names:
            full = os.path.join(dirpath, name)
            inside = os.path.relpath(full, FIXTURE).replace(os.sep, "/")
            found["%s/%s/%s" % (constants.SKILLS_DIR, SKILL, inside)] = support.read(full)
    return found


def the_documents(goals=True, standard=True):
    found = {
        METRICS: support.skill_document("metrics", "Metric definitions"),
        constants.STACK_PATH: support.skill_document("stack", "Source map"),
    }
    if goals:
        found[GOALS] = support.skill_document("goals", "Goals")
    if standard:
        found[STANDARD] = support.skill_document("standard", "Ad creative testing")
    return found


def a_base(sandbox, **documents):
    return support.skill_base(
        sandbox, documents=the_documents(**documents), skill=SKILL, files=skill_files()
    )


def run(root, base_id, unattended=False):
    return runner.start(
        root, base_id, SKILL, unattended=unattended, conversation="night-run",
        runner=support.NoRemoteRunner(), now=contract.TODAY,
    )


class TestTheContract(unittest.TestCase):
    def test_the_made_up_skill_passes_the_contract_check(self):
        self.assertEqual([], runner.check_skill(SKILL, skill_files()).problems)

    def test_each_wrong_output_fails_for_its_own_reason(self):
        example = "skills/%s/examples/a-quiet-night/" % SKILL
        files = skill_files()
        sources = {
            name: files[example + name]
            for name in ("input.md", "engine-summary.txt", "goals.md")
        }
        expectations = runner.expectations_of(files[example + "expectations.md"])
        made_up_figure = runner.judge_output(
            files[example + "wrong-made-up-figure.md"], expectations, sources
        )
        self.assertIn(runner.FINISH_FIGURE % "$450.00", made_up_figure)
        made_up_pause = runner.judge_output(
            files[example + "wrong-made-up-pause.md"], expectations, sources
        )
        self.assertIn(runner.FINISH_ENGINE % "engine-summary.txt", made_up_pause)
        claimed = runner.judge_output(
            files[example + "wrong-claims-an-action.md"], expectations, sources
        )
        self.assertIn(runner.EXPECTED_PRESENT % "we paused", claimed)

    def test_the_skill_text_names_no_runner_command(self):
        for path, text in skill_files().items():
            if "/examples/" not in path:
                self.assertFalse(runner.names_a_command(text), path)

    def test_the_fixture_is_made_up(self):
        """The orchestrator reviews it before merge; no scan is claimed to find real names."""
        readme = support.read(os.path.join(support.FIXTURES_DIR, "README.md"))
        self.assertIn("base-skills/meta-ads/", readme)
        self.assertIn("Every name, identifier and figure in it is invented", readme)


class TestTheNightsThatMatter(unittest.TestCase):
    def test_unattended_with_the_goals_flagged_reports_first_and_still_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            contract.a_change_about(root, GOALS)
            started = run(root, base_id, unattended=True)
            self.assertEqual(runner.OUTCOME_FLAGGED, started.outcome)
            self.assertEqual([GOALS], started.held)
            shown = " ".join(started.render().split())
            self.assertTrue(shown.startswith("Say this first in what you report"))
            self.assertIn("hold the goal relation section, and still report the engine check", shown)

    def test_a_missing_standard_is_refused_and_nothing_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox, standard=False)
            started = run(root, base_id, unattended=True)
            self.assertEqual(runner.REFUSED_REQUIRED, started.refusal)
            self.assertEqual({}, started.instructions)
            text = skill_files()["skills/%s/SKILL.md" % SKILL]
            self.assertIn("nothing is paused, promoted or", text)
            self.assertIn("written tonight, and the refusal is the night's report", text)

    def test_missing_goals_is_ready_with_gaps_and_the_check_still_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox, goals=False)
            started = run(root, base_id, unattended=True)
            self.assertEqual(runner.OUTCOME_READY_WITH_GAPS, started.outcome)
            self.assertEqual([GOALS], started.gaps)
            self.assertIn("The check always runs", started.render())


class TestTheSessionStartNamesIt(unittest.TestCase):
    def blocks(self):
        return session_start.load_blocks(support.PLUGIN_DIR, "injection.md")

    def test_a_trusted_skill_is_listed_in_one_line(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            said = session_start._skills_block(self.blocks(), root, base_id)
            listed = [line for line in said.split("\n") if line.startswith(SKILL + ":")]
            self.assertEqual(1, len(listed))
            self.assertIn("Check the night's ad creative tests", listed[0])

    def test_an_untrusted_skill_and_a_folder_with_no_base_list_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            os.remove(authority.trusted_path(base_id))
            self.assertEqual("", session_start._skills_block(self.blocks(), root, base_id))
            self.assertEqual("", session_start._skills_block(self.blocks(), None, None))


class TestTheScheduledPromptsCommand(unittest.TestCase):
    def as_scheduled(self, command, cwd):
        """The scheduled prompt's command, run exactly as its words are written."""
        environment = dict(os.environ)
        environment["CLAUDE_CODE_SESSION_ID"] = "night-run"
        return subprocess.run(
            [sys.executable] + shlex.split(command)[1:],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def test_the_command_runs_as_written_and_marks_the_night_unattended(self):
        command = [
            line for line in SCHEDULED_PROMPT.split("\n") if line.startswith("python3 ")
        ][0]
        with support.Sandbox() as sandbox:
            root, _base_id = a_base(sandbox)
            finished = self.as_scheduled(command, support.where_a_script_runs(root))
            said = finished.stdout.decode("utf-8")
            self.assertEqual(0, finished.returncode, finished.stderr)
            self.assertIn("Nightly ad creative check", said)
            self.assertTrue(authority.is_unattended("night-run"))


if __name__ == "__main__":
    unittest.main()
