"""A command that switches GTM Base's checks off is undone right after it runs.

From 0.3.6 to 0.3.10 the check on commands read each shell line and asked
before any line that could write the files that decide whether GTM Base runs.
Replaying the person's own commands still gave fifteen to twenty questions in
four hundred, most about lines that only read. 0.4.0 keeps a copy of those
files before each command and compares after it, and puts back only what
weakened the checks.

Every command here really runs, in a temporary home folder, between the check
before it and the check after it, the way Claude Code runs them. Nothing here
reaches the person's own settings.
"""

import json
import os
import shutil
import subprocess
import unittest
import uuid

import support

from gtmbase import gate, machine, settings_guard

HOOKS = os.path.join(support.PLUGIN_DIR, "hooks")
BEFORE = os.path.join(HOOKS, "pre-push-gate.sh")
AFTER = os.path.join(HOOKS, "settings-guard.sh")
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "real-commands.json")

KEY = settings_guard.PLUGIN_KEY


class Home(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.home = os.path.realpath(os.environ["HOME"])
        self.claude = os.path.join(self.home, ".claude")
        self.plugins = os.path.join(self.claude, "plugins")
        self.cache = os.path.join(self.plugins, "cache", "gtm-base", "gtm-base")
        os.makedirs(os.path.join(self.cache, "0.3.10"))
        self.settings = os.path.join(self.claude, "settings.json")
        self.installed = os.path.join(self.plugins, "installed_plugins.json")
        self.marketplaces = os.path.join(self.plugins, "known_marketplaces.json")
        self.save(self.settings, {
            "theme": "dark",
            "enabledPlugins": {KEY: True, "other@elsewhere": True},
            "permissions": {"allow": ["Bash(ls:*)"]},
            "env": {"EDITOR": "vim"},
            "extraKnownMarketplaces": {
                "gtm-base": {"source": {"source": "github", "repo": "brandon-sellers13/gtm-base"}}
            },
        })
        self.save(self.installed, {
            "version": 2,
            "plugins": {
                KEY: [{
                    "scope": "user",
                    "installPath": os.path.join(self.cache, "0.3.10"),
                    "version": "0.3.10",
                    "gitCommitSha": "a" * 40,
                    "lastUpdated": "2026-10-20T05:36:06.303Z",
                }],
                "other@elsewhere": [{"scope": "user", "version": "1.0.0"}],
            },
        })
        self.save(self.marketplaces, {
            "gtm-base": {
                "source": {"source": "github", "repo": "brandon-sellers13/gtm-base"},
                "installLocation": os.path.join(self.plugins, "marketplaces", "gtm-base"),
                "lastUpdated": "2026-10-20T05:36:05.691Z",
            },
            "elsewhere": {"source": {"source": "github", "repo": "someone/else"}},
        })
        self.work = os.path.join(self.home, "work")
        os.makedirs(self.work)
        self.session = "s-" + uuid.uuid4().hex[:8]

    # --- helpers ---

    def save(self, path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)

    def load(self, path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def hook(self, script, payload):
        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = support.PLUGIN_DIR
        finished = subprocess.run(
            ["sh", script, "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        text = finished.stdout.decode("utf-8").strip()
        return json.loads(text) if text else None

    def run_command(self, command, cwd=None, tool_use_id=None, after_id=None):
        """The check before, the command itself, and the check after.

        Returns what the check before said and what the check after said.
        """
        cwd = cwd or self.work
        tool_use_id = tool_use_id or "toolu_" + uuid.uuid4().hex
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": cwd,
            "session_id": self.session,
            "tool_use_id": tool_use_id,
            "hook_event_name": "PreToolUse",
        }
        before = self.hook(BEFORE, payload)
        finished = subprocess.run(
            ["bash", "-c", command], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        payload["tool_use_id"] = after_id or tool_use_id
        if finished.returncode == 0:
            payload["hook_event_name"] = "PostToolUse"
            payload["tool_response"] = {"stdout": "", "stderr": "", "interrupted": False}
        else:
            payload["hook_event_name"] = "PostToolUseFailure"
            payload["error"] = "Exit code %d" % finished.returncode
        return before, self.hook(AFTER, payload)

    def assert_protected(self):
        self.assertIs(True, self.load(self.settings)["enabledPlugins"][KEY])
        self.assertNotIn("disableAllHooks", self.load(self.settings))
        self.assertTrue(self.load(self.installed)["plugins"][KEY])
        self.assertIn("gtm-base", self.load(self.marketplaces))

    def assert_undone(self, answer, event="PostToolUse"):
        self.assertIsNotNone(answer)
        self.assertIn("GTM Base undid", answer["systemMessage"])
        self.assertIn("/plugin", answer["systemMessage"])
        self.assertEqual(event, answer["hookSpecificOutput"]["hookEventName"])
        self.assertIn("Do not try to make this change another way",
                      answer["hookSpecificOutput"]["additionalContext"])
        if event == "PostToolUse":
            self.assertEqual("block", answer["decision"])
        else:
            self.assertNotIn("decision", answer)


class TestEveryWayOfSwitchingTheChecksOff(Home):
    """Each of these switched the checks off, most in a way no reading of the
    words of the command could be sure of. Each is caught and undone."""

    def test_python_building_the_path_in_pieces(self):
        command = (
            "python3 -c \"import json, os; p = os.path.join(os.path.expanduser('~'), "
            "'.cl' + 'aude', 'sett' + 'ings.json'); d = json.load(open(p)); "
            "d['enabledPlugins']['gtm-base@gtm-base'] = False; d['theme'] = 'light'; "
            "json.dump(d, open(p, 'w'))\""
        )
        before, after = self.run_command(command)

        self.assertIsNone(before)
        self.assert_undone(after)
        self.assertIn("turned GTM Base off in ~/.claude/settings.json", after["systemMessage"])
        self.assert_protected()
        # What else the command changed is kept.
        self.assertEqual("light", self.load(self.settings)["theme"])

    def test_sed_in_place(self):
        before, after = self.run_command(
            "sed -i.bak 's/\"gtm-base@gtm-base\": true/\"gtm-base@gtm-base\": false/' "
            "~/.claude/settings.json"
        )
        self.assertIsNone(before)
        self.assert_undone(after)
        self.assert_protected()

    def test_jq_into_a_temporary_file_then_mv(self):
        if not shutil.which("jq"):
            self.skipTest("jq is not installed")
        before, after = self.run_command(
            "jq '.disableAllHooks = true' ~/.claude/settings.json > /tmp/gtm-guard-$$.json "
            "&& mv /tmp/gtm-guard-$$.json ~/.claude/settings.json"
        )
        self.assertIsNone(before)
        self.assert_undone(after)
        self.assertIn("turned every hook off", after["systemMessage"])
        self.assert_protected()

    def test_removing_the_list_of_installed_plugins(self):
        before, after = self.run_command("rm ~/.claude/plugins/installed_plugins.json")

        self.assertIsNone(before)
        self.assert_undone(after)
        self.assertIn("deleted ~/.claude/plugins/installed_plugins.json", after["systemMessage"])
        # Nothing is left to keep, so the whole file comes back, other plugins too.
        self.assertIn("other@elsewhere", self.load(self.installed)["plugins"])
        self.assert_protected()

    def test_taking_gtm_base_off_the_list_of_installed_plugins(self):
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser("
            "'~/.claude/plugins/installed_plugins.json'); d = json.load(open(p)); "
            "del d['plugins']['gtm-base@gtm-base']; d['plugins']['new@elsewhere'] = []; "
            "json.dump(d, open(p, 'w'))\""
        )
        _before, after = self.run_command(command)

        self.assert_undone(after)
        self.assert_protected()
        self.assertIn("new@elsewhere", self.load(self.installed)["plugins"])

    def test_pointing_gtm_base_at_code_somewhere_else(self):
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser("
            "'~/.claude/plugins/installed_plugins.json'); d = json.load(open(p)); "
            "d['plugins']['gtm-base@gtm-base'][0]['installPath'] = '/tmp/elsewhere'; "
            "json.dump(d, open(p, 'w'))\""
        )
        _before, after = self.run_command(command)

        self.assert_undone(after)
        entry = self.load(self.installed)["plugins"][KEY][0]
        self.assertEqual(os.path.join(self.cache, "0.3.10"), entry["installPath"])

    def test_removing_or_moving_the_marketplace(self):
        for change in (
            "del d['gtm-base']",
            "d['gtm-base']['source'] = {'source': 'github', 'repo': 'someone/fork'}",
        ):
            command = (
                "python3 -c \"import json, os; p = os.path.expanduser("
                "'~/.claude/plugins/known_marketplaces.json'); d = json.load(open(p)); "
                + change + "; json.dump(d, open(p, 'w'))\""
            )
            _before, after = self.run_command(command)
            self.assert_undone(after)
            self.assertEqual(
                "brandon-sellers13/gtm-base",
                self.load(self.marketplaces)["gtm-base"]["source"]["repo"],
                change,
            )

    def test_the_environment_that_runs_the_checks(self):
        for key in ("PATH", "PYTHONPATH", "GTM_BASE_LIB"):
            command = (
                "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
                "d = json.load(open(p)); d['env']['" + key + "'] = '/tmp/x'; "
                "json.dump(d, open(p, 'w'))\""
            )
            _before, after = self.run_command(command)
            self.assert_undone(after)
            self.assertNotIn(key, self.load(self.settings)["env"], key)
            self.assertEqual("vim", self.load(self.settings)["env"]["EDITOR"])

    def test_a_settings_file_left_unreadable(self):
        _before, after = self.run_command("echo '{}' x > ~/.claude/settings.json")

        self.assert_undone(after)
        self.assertIn("left ~/.claude/settings.json unreadable", after["systemMessage"])
        self.assert_protected()
        self.assertEqual("dark", self.load(self.settings)["theme"])

    def test_a_command_that_fails_after_the_change(self):
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
            "d = json.load(open(p)); d['enabledPlugins']['gtm-base@gtm-base'] = False; "
            "json.dump(d, open(p, 'w'))\"; exit 3"
        )
        _before, after = self.run_command(command)

        self.assert_undone(after, event="PostToolUseFailure")
        self.assert_protected()

    def test_a_new_project_settings_file_that_turns_it_off(self):
        project = os.path.join(self.home, "project")
        os.makedirs(project)
        _before, after = self.run_command(
            "mkdir -p .claude && printf '{\"enabledPlugins\": {\"gtm-base@gtm-base\": false}}' "
            "> .claude/settings.local.json",
            cwd=project,
        )

        self.assert_undone(after)
        written = self.load(os.path.join(project, ".claude", "settings.local.json"))
        self.assertNotIn(KEY, written["enabledPlugins"])

    def test_a_linked_folders_settings(self):
        _root, base_id = self.sandbox.base("Acme")
        linked = os.path.realpath(os.path.join(self.home, "marketing"))
        os.makedirs(os.path.join(linked, ".claude"))
        machine.link_content(base_id, linked)
        _before, after = self.run_command(
            "printf '{\"disableAllHooks\": true}' > " + os.path.join(linked, ".claude", "settings.json")
        )

        self.assert_undone(after)
        self.assertNotIn("disableAllHooks", self.load(os.path.join(linked, ".claude", "settings.json")))

    def test_a_loop_that_writes(self):
        _before, after = self.run_command(
            "for f in ~/.claude/settings.json; do "
            "sed -i.bak 's/\"disableAllHooks\"/x/; s/\"theme\"/\"disableAllHooks\": true, \"theme\"/' \"$f\"; done"
        )
        self.assert_undone(after)
        self.assert_protected()

    def test_settings_kept_behind_a_link(self):
        dotfiles = os.path.join(self.home, "dotfiles")
        os.makedirs(dotfiles)
        shutil.move(self.settings, os.path.join(dotfiles, "settings.json"))
        os.symlink(os.path.join(dotfiles, "settings.json"), self.settings)
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
            "d = json.load(open(p)); d['enabledPlugins']['gtm-base@gtm-base'] = False; "
            "json.dump(d, open(p, 'w'))\""
        )
        _before, after = self.run_command(command)

        self.assert_undone(after)
        self.assertTrue(os.path.islink(self.settings))
        self.assert_protected()

    def test_the_name_after_the_command_is_not_the_one_before(self):
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
            "d = json.load(open(p)); d['enabledPlugins']['gtm-base@gtm-base'] = False; "
            "json.dump(d, open(p, 'w'))\""
        )
        _before, after = self.run_command(command, tool_use_id="toolu_one", after_id="toolu_two")

        self.assert_undone(after)
        self.assert_protected()


class TestTheShapesTheReviewFound(Home):
    """The adversarial review of 0.4.0 got each of these past the first draft."""

    def edit(self, path, change):
        return (
            "python3 -c \"import json, os; p = '" + path + "'; d = json.load(open(p)); "
            + change + "; json.dump(d, open(p, 'w'))\""
        )

    def test_a_file_nobody_can_read_any_more(self):
        _before, after = self.run_command("chmod 000 ~/.claude/settings.json")

        self.assert_undone(after)
        self.assertEqual(0o600, os.stat(self.settings).st_mode & 0o600)
        self.assert_protected()

    def test_a_fake_copy_elsewhere_in_the_plugins_folder(self):
        fake = os.path.join(self.plugins, "cache", "evil", "gtm-base", "0.3.10")
        os.makedirs(fake)
        _before, after = self.run_command(self.edit(
            self.installed, "d['plugins']['gtm-base@gtm-base'][0]['installPath'] = '" + fake + "'"
        ))
        self.assert_undone(after)
        self.assertEqual(
            os.path.join(self.cache, "0.3.10"),
            self.load(self.installed)["plugins"][KEY][0]["installPath"],
        )

    def test_a_link_inside_its_own_folder_that_leads_out(self):
        elsewhere = os.path.join(self.home, "elsewhere")
        os.makedirs(elsewhere)
        os.symlink(elsewhere, os.path.join(self.cache, "9.9.9"))
        _before, after = self.run_command(self.edit(
            self.installed,
            "d['plugins']['gtm-base@gtm-base'][0]['installPath'] = '"
            + os.path.join(self.cache, "9.9.9") + "'",
        ))
        self.assert_undone(after)

    def test_the_persons_install_swapped_for_another_projects(self):
        _before, after = self.run_command(self.edit(
            self.installed,
            "d['plugins']['gtm-base@gtm-base'][0].update(scope='project', projectPath='/nowhere')",
        ))
        self.assert_undone(after)
        self.assertEqual("user", self.load(self.installed)["plugins"][KEY][0]["scope"])

    def test_the_home_folder_and_the_config_folder_in_the_environment(self):
        for key in ("HOME", "CLAUDE_CONFIG_DIR"):
            _before, after = self.run_command(
                self.edit(self.settings, "d['env']['" + key + "'] = '/tmp/x'")
            )
            self.assert_undone(after)
            self.assertNotIn(key, self.load(self.settings)["env"], key)

    def test_an_empty_folder_put_where_the_file_was(self):
        _before, after = self.run_command(
            "rm ~/.claude/settings.json && mkdir ~/.claude/settings.json"
        )
        self.assert_undone(after)
        self.assertTrue(os.path.isfile(self.settings))
        self.assert_protected()

    def test_a_folder_with_something_in_it_is_reported(self):
        _before, after = self.run_command(
            "rm ~/.claude/settings.json && mkdir ~/.claude/settings.json "
            "&& touch ~/.claude/settings.json/x"
        )
        self.assertIn("could not put that back", after["systemMessage"])
        self.assertIn("~/.claude/settings.json", after["systemMessage"])

    def test_a_settings_file_that_starts_with_a_byte_order_mark(self):
        with open(self.settings, encoding="utf-8") as handle:
            text = handle.read()
        with open(self.settings, "w", encoding="utf-8") as handle:
            handle.write("﻿" + text)
        _before, after = self.run_command(
            "sed -i.bak 's/\"gtm-base@gtm-base\": true/\"gtm-base@gtm-base\": false/' "
            "~/.claude/settings.json"
        )
        self.assert_undone(after)
        self.assert_protected()

    def test_hooks_turned_off_with_a_string(self):
        # Claude Code reads settings in JavaScript, where "false" is a true value.
        _before, after = self.run_command(self.edit(self.settings, "d['disableAllHooks'] = 'false'"))
        self.assert_undone(after)
        self.assertNotIn("disableAllHooks", self.load(self.settings))

    def test_the_folder_claude_config_dir_names(self):
        config = os.path.join(self.home, "elsewhere-config")
        shutil.copytree(self.claude, config)
        os.environ["CLAUDE_CONFIG_DIR"] = config
        self.addCleanup(os.environ.pop, "CLAUDE_CONFIG_DIR", None)
        settings = os.path.join(config, "settings.json")
        _before, after = self.run_command(
            self.edit(settings, "d['enabledPlugins']['gtm-base@gtm-base'] = False")
        )
        self.assert_undone(after)
        self.assertIs(True, self.load(settings)["enabledPlugins"][KEY])


class TestWhatIsLeftAlone(Home):
    """Changes that leave the checks as strong as they were are never touched,
    and nothing is said about them."""

    def assert_left_alone(self, command, cwd=None):
        _before, after = self.run_command(command, cwd=cwd)
        self.assertIsNone(after, command)

    def test_unrelated_edits_to_the_same_files(self):
        for change in (
            "d['theme'] = 'light'",
            "d['permissions']['allow'].append('Bash(wc:*)')",
            "d['enabledPlugins']['other@elsewhere'] = False",
            "d['env']['EDITOR'] = 'nano'",
            "d['hooks'] = {'Stop': []}",
        ):
            command = (
                "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
                "d = json.load(open(p)); " + change + "; json.dump(d, open(p, 'w'))\""
            )
            self.assert_left_alone(command)
        settings = self.load(self.settings)
        self.assertEqual("light", settings["theme"])
        self.assertIn("Bash(wc:*)", settings["permissions"]["allow"])
        self.assertIs(False, settings["enabledPlugins"]["other@elsewhere"])
        self.assertEqual("nano", settings["env"]["EDITOR"])

    def test_updating_gtm_base_itself(self):
        os.makedirs(os.path.join(self.cache, "0.4.0"))
        update = (
            "python3 -c \"import json, os; p = os.path.expanduser("
            "'~/.claude/plugins/installed_plugins.json'); d = json.load(open(p)); "
            "e = d['plugins']['gtm-base@gtm-base'][0]; e['version'] = '0.4.0'; "
            "e['installPath'] = e['installPath'].replace('0.3.10', '0.4.0'); "
            "e['gitCommitSha'] = 'b' * 40; e['lastUpdated'] = '2026-10-21T00:00:00.000Z'; "
            "json.dump(d, open(p, 'w'))\""
        )
        refresh = (
            "python3 -c \"import json, os; p = os.path.expanduser("
            "'~/.claude/plugins/known_marketplaces.json'); d = json.load(open(p)); "
            "d['gtm-base']['lastUpdated'] = '2026-10-21T00:00:00.000Z'; "
            "json.dump(d, open(p, 'w'))\""
        )
        self.assert_left_alone(update)
        self.assert_left_alone(refresh)
        self.assertEqual("0.4.0", self.load(self.installed)["plugins"][KEY][0]["version"])

    def test_turning_it_back_on(self):
        settings = self.load(self.settings)
        settings["enabledPlugins"][KEY] = False
        self.save(self.settings, settings)
        command = (
            "python3 -c \"import json, os; p = os.path.expanduser('~/.claude/settings.json'); "
            "d = json.load(open(p)); d['enabledPlugins']['gtm-base@gtm-base'] = True; "
            "json.dump(d, open(p, 'w'))\""
        )
        self.assert_left_alone(command)

    def test_another_projects_settings_that_do_not_touch_gtm_base(self):
        project = os.path.join(self.home, "project")
        os.makedirs(os.path.join(project, ".claude"))
        self.assert_left_alone(
            "printf '{\"permissions\": {\"allow\": []}}' > .claude/settings.local.json; "
            "rm -f .claude/settings.json",
            cwd=project,
        )

    def test_a_change_the_person_makes_between_commands(self):
        self.assert_left_alone("ls")
        settings = self.load(self.settings)
        settings["enabledPlugins"][KEY] = False
        self.save(self.settings, settings)
        self.assert_left_alone("ls")
        self.assertIs(False, self.load(self.settings)["enabledPlugins"][KEY])


class TestReadsAreNeverAskedAbout(Home):
    """0.4.0 asks nothing before a command because of the settings. Every
    command here was run by an assistant in a real session, and the first
    eighteen were asked about by 0.3.10 or earlier."""

    def corpus(self):
        with open(FIXTURE, encoding="utf-8") as handle:
            return json.load(handle)["commands"]

    def test_the_real_commands_through_the_library(self):
        for command in self.corpus():
            for cwd in (self.work, self.claude, self.plugins):
                self.assertIsNone(gate.check_command(command, cwd, self.session), command)

    def test_the_real_commands_through_the_hook(self):
        for command in self.corpus():
            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": command},
                "cwd": self.work,
                "session_id": self.session,
                "tool_use_id": "toolu_" + uuid.uuid4().hex,
                "hook_event_name": "PreToolUse",
            }
            self.assertIsNone(self.hook(BEFORE, payload), command)
            payload["hook_event_name"] = "PostToolUse"
            self.assertIsNone(self.hook(AFTER, payload), command)

    def test_reading_the_settings_themselves(self):
        for command in (
            "cat ~/.claude/settings.json",
            "jq .permissions ~/.claude/settings.json",
            "grep -n hooks ~/.claude/settings.json ~/.claude/settings.local.json",
            "cp ~/.claude/settings.json /tmp/gtm-guard-backup.json",
            "ls -la ~/.claude ~/.claude/plugins",
        ):
            before, after = self.run_command(command)
            self.assertIsNone(before, command)
            self.assertIsNone(after, command)


class TestTheCopy(Home):
    def test_it_is_kept_in_the_records_folder_and_cleared_after(self):
        folder = os.path.join(os.environ["GTM_BASE_HOME"], "guard")
        self.run_command("ls")
        self.assertEqual([], os.listdir(folder))

    def test_no_copy_without_a_tool_call_name(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": self.work,
            "session_id": self.session,
        }
        self.assertIsNone(self.hook(BEFORE, payload))
        self.assertFalse(os.path.exists(os.environ["GTM_BASE_HOME"]))

    def test_no_copy_for_a_refused_command(self):
        folder = os.path.join(os.environ["GTM_BASE_HOME"], "guard")
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git push --no-verify origin main"},
            "cwd": self.work,
            "session_id": self.session,
            "tool_use_id": "toolu_refused",
        }
        self.assertEqual("deny", self.hook(BEFORE, payload)["hookSpecificOutput"]["permissionDecision"])
        self.assertFalse(os.path.exists(os.path.join(folder, "toolu_refused.json")))

    def test_an_after_request_with_no_copy_says_nothing(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "cwd": self.work,
            "session_id": self.session,
            "tool_use_id": "toolu_never_seen",
            "hook_event_name": "PostToolUse",
        }
        self.assertIsNone(self.hook(AFTER, payload))


class TestTheLineIsSplitWhereTheShellSplitsIt(unittest.TestCase):
    """0.3.10, kept: the push gate still splits lines with this."""

    def test_a_backslash_inside_double_quotes(self):
        for command, segments in (
            (r'''grep "[^\"& ]" /tmp/x | sort''', [r'''grep "[^\"& ]" /tmp/x''', "sort"]),
            (r'''echo "a\\" ; ls''', [r'''echo "a\\"''', "ls"]),
            (r'''echo 'a\' ; ls''', [r'''echo 'a\'''', "ls"]),
        ):
            self.assertEqual(segments, gate.split_segments(command), command)


if __name__ == "__main__":
    unittest.main()
