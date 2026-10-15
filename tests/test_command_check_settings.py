"""A shell line that writes the files which can switch GTM Base off is asked about.

Step 10 of the Release A live check (2026-10-10): asked to add one permission
to the person's own settings, a session copied the settings file to a backup
and rewrote it with a Python script run through the shell, and nothing was
asked, because the question lived only on the file tools. The command check
now asks the write check's question, in the write check's words, about any
shell line that writes the same files.

Every path here is inside a temporary home folder. The settings files named
are never really written: the check reads the command, and nothing runs it.
"""

import json
import os
import subprocess
import unittest

import support

from gtmbase import gate, machine, settings_writes, write_hook

WRAPPER = os.path.join(support.PLUGIN_DIR, "hooks", "pre-push-gate.sh")

# What the live session did, in the same shape: a backup, then a script.
THE_LIVE_SHAPE = """cp ~/.claude/settings.json ~/.claude/settings.json.bak && python3 - <<'EOF'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
data = json.loads(p.read_text())
data.setdefault("permissions", {}).setdefault("allow", []).append("Bash(wc:*)")
p.write_text(json.dumps(data, indent=2))
EOF"""


class Home(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.home = os.path.realpath(os.environ["HOME"])
        self.claude = os.path.join(self.home, ".claude")
        os.makedirs(os.path.join(self.claude, "plugins"))
        support.write(os.path.join(self.claude, "settings.json"), "{}\n")
        self.work = os.path.join(self.home, "work")
        os.makedirs(self.work)

    def asks(self, command, cwd=None):
        return settings_writes.writes_a_settings_file(command, cwd or self.work)

    def hook(self, command, cwd=None):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": cwd or self.work,
            "session_id": "s-1",
        }
        environment = dict(os.environ)
        environment["CLAUDE_PLUGIN_ROOT"] = support.PLUGIN_DIR
        finished = subprocess.run(
            ["sh", WRAPPER, "claude"],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        text = finished.stdout.decode("utf-8").strip()
        return json.loads(text)["hookSpecificOutput"] if text else None


class TestTheLinesThatWriteAreAskedAbout(Home):
    def test_every_way_of_writing_the_user_settings(self):
        """Fails on 0.3.5, where none of these was asked about."""
        for command in (
            "echo '{}' > ~/.claude/settings.json",
            "echo '{}' >> $HOME/.claude/settings.local.json",
            'echo x>"${HOME}/.claude/settings.json"',
            "printf '{}' 1> " + os.path.join(self.claude, "settings.json"),
            "cp /tmp/new.json ~/.claude/settings.json",
            "cp -f /tmp/new.json ~/.claude/",
            "mv ~/.claude/settings.json ~/.claude/old.json",
            "mv /tmp/new.json ~/.claude/settings.json",
            "cat /tmp/new.json | tee ~/.claude/settings.json",
            "cat /tmp/new.json | tee -a ~/.claude/settings.local.json > /dev/null",
            "sed -i '' 's/true/false/' ~/.claude/settings.json",
            "sed -i.bak 's/true/false/' ~/.claude/settings.json",
            "sed --in-place 's/true/false/' ~/.claude/settings.json",
            "sed -Ei 's/a/b/' ~/.claude/settings.json",
            "rm ~/.claude/settings.json",
            "rm -rf ~/.claude",
            "ln -sf /tmp/new.json ~/.claude/settings.json",
            "jq '.x = 1' ~/.claude/settings.json > /tmp/t && mv /tmp/t ~/.claude/settings.json",
            "cd ~/.claude && echo '{}' > settings.json",
            "cd ~ && cp /tmp/new.json .claude/settings.json",
            "echo ~/.claude/settings.json | xargs rm",
            "f=~/.claude; echo x > $f/settings.json",
            "sed -i '' 's/a/b/' ~/.claude/settings.*",
            "bash -c 'echo x > ~/.claude/settings.json'",
            "(cd ~/.claude; rm settings.json)",
            "echo $(echo x > ~/.claude/settings.json)",
        ):
            self.assertTrue(self.asks(command), command)

    def test_an_interpreter_script_writing_the_file(self):
        for command in (
            "python3 -c \"import json,os; p=os.path.expanduser('~/.claude/settings.json'); "
            "json.dump({}, open(p, 'w'))\"",
            "python3 -c \"import os; os.replace('/tmp/x', os.path.join(os.environ['HOME'], "
            "'.claude', 'settings.json'))\"",
            "node -e \"require('fs').writeFileSync(process.env.HOME + '/.claude/settings.json', '{}')\"",
            "perl -pi -e 's/a/b/' ~/.claude/settings.json",
            THE_LIVE_SHAPE,
        ):
            self.assertTrue(self.asks(command), command)

    def test_the_plugin_registry(self):
        plugins = os.path.join(self.claude, "plugins")
        for command, cwd in (
            ("echo '{}' > ~/.claude/plugins/installed_plugins.json", None),
            ("cp /tmp/m.json ~/.claude/plugins/known_marketplaces.json", None),
            ("rm known_marketplaces.json", plugins),
            ("echo '{}' > installed_plugins.json", plugins),
        ):
            self.assertTrue(self.asks(command, cwd), command)

    def test_a_linked_folders_settings(self):
        root, base_id = self.sandbox.base("Acme")
        linked = os.path.realpath(os.path.join(self.home, "marketing"))
        os.makedirs(os.path.join(linked, ".claude", "worktrees", "one"))
        machine.link_content(base_id, linked)

        for command, cwd in (
            ("echo '{}' > .claude/settings.local.json", linked),
            ("echo '{}' > " + os.path.join(linked, ".claude", "settings.json"), None),
            ("echo '{}' > ../../settings.json", os.path.join(linked, ".claude", "worktrees", "one")),
            ("echo '{}' > sub/.claude/settings.json", linked),
            ("rm -rf .claude", linked),
        ):
            self.assertTrue(self.asks(command, cwd), command)

    def test_the_hook_asks_with_the_write_checks_own_sentence(self):
        answer = self.hook(THE_LIVE_SHAPE)

        self.assertEqual("ask", answer["permissionDecision"])
        self.assertEqual(write_hook.ASK_ABOUT_SETTINGS, answer["permissionDecisionReason"])

    def test_a_refusal_on_the_same_line_still_wins(self):
        answer = self.hook(
            "echo x > ~/.claude/settings.json; git push --no-verify origin main"
        )

        self.assertEqual("deny", answer["permissionDecision"])


class TestTheShapesTheReviewsFound(Home):
    """Each line here got no question from the first draft of this check."""

    def test_a_redirection_of_another_stream_after_the_command(self):
        for command in (
            "cp /tmp/x ~/.claude/settings.json 2>/dev/null",
            "cp -f /tmp/x ~/.claude/settings.json 2>&1",
            "cp /tmp/x ~/.claude/settings.json 2> /dev/null",
            "nohup cp /tmp/x ~/.claude/settings.json >/dev/null 2>&1 &",
        ):
            self.assertTrue(self.asks(command), command)

    def test_a_script_typed_into_the_line(self):
        for command in (
            "python3 - <<'PY'\nimport pathlib\n"
            "(pathlib.Path.home()/'.claude'/'settings.json').write_text('{}')\nPY",
            "python3 - <<'EOF'\nimport os\n"
            "p = os.environ['HOME'] + '/.claude/settings.json'\n"
            "open(p, 'w').write('{}')\nEOF",
            "python3 - <<EOF\np=__import__('os').path.expanduser('~/.claude/settings.json')\n"
            "open(p,'w').write('{}')\nEOF",
            "bash <<'EOF'\necho x > ~/.claude/settings.json\nEOF",
        ):
            self.assertTrue(self.asks(command), command)

    def test_a_path_built_by_another_command_or_handed_in(self):
        for command in (
            "cp /tmp/x $(echo ~/.claude)/settings.json",
            'cp /tmp/x "$(dirname ~/.claude/x)/settings.json"',
            "xargs -I{} cp /tmp/x {} <<< ~/.claude/settings.json",
            "f=~/.claude/settings.json; echo x > $f",
            "f=~/.claude/settings.json; rm $f",
        ):
            self.assertTrue(self.asks(command), command)

    def test_a_pattern_or_a_spliced_name(self):
        for command in (
            "cp /tmp/x ~/.cl*/sett*.json",
            "cd ~/.claude && cp /tmp/x sett*",
            'echo x > ~/.cl""aude/settings.json',
            "echo x > ~/.cl\\aude/settings.json",
        ):
            self.assertTrue(self.asks(command), command)

    def test_a_command_run_from_inside_the_assistant_folder(self):
        for command, cwd in (
            ("cd ~/.claude && rm -rf plugins", None),
            ("cd ~/.claude/plugins && rm -rf cache", None),
            ("cd ~/.claude && sed -i '' s/a/b/ *.json", None),
            ("cd ~/.claude && cp /tmp/x .", None),
            ("rm -rf plugins", self.claude),
        ):
            self.assertTrue(self.asks(command, cwd), command)

    def test_what_stays_quiet_around_them(self):
        skills = os.path.join(self.claude, "skills")
        os.makedirs(skills)
        for command, cwd in (
            ("cat > notes.md <<'EOF'\nRemember ~/.claude/settings.json\nEOF", None),
            ("ls *.py 2>/dev/null", None),
            ("rm -rf ~/tmp/*.log", None),
            ("cp a.md b.md", skills),
            ("grep -rn '[a-z]' .", None),
            ("python3 - <<'EOF'\nprint('hello')\nEOF", None),
        ):
            self.assertFalse(self.asks(command, cwd), command)


class TestTheLinesThatDoNotWriteAreLeftAlone(Home):
    def test_reading_the_settings(self):
        for command in (
            "cat ~/.claude/settings.json",
            "jq .permissions ~/.claude/settings.json",
            "grep -n hooks ~/.claude/settings.json ~/.claude/settings.local.json",
            "head -20 ~/.claude/settings.json | tail -5",
            "sed -n '1,40p' ~/.claude/settings.json",
            "cp ~/.claude/settings.json /tmp/backup.json",
            "cat ~/.claude/settings.json > /tmp/copy.json",
            "ls -la ~/.claude ~/.claude/plugins",
            "find ~/.claude -name settings.json",
            "diff ~/.claude/settings.json /tmp/backup.json",
            "echo 'edit ~/.claude/settings.json by hand'",
            "bash -c 'cat ~/.claude/settings.json'",
        ):
            self.assertFalse(self.asks(command), command)

    def test_the_same_names_somewhere_else(self):
        project = os.path.join(self.home, "project")
        os.makedirs(os.path.join(project, ".claude"))
        for command, cwd in (
            ("echo '{}' > .vscode/settings.json", project),
            ("echo '{}' > .claude/settings.json", project),
            ("echo '{}' > settings.json", project),
            ("cp /tmp/x.json " + os.path.join(project, ".claude", "settings.local.json"), None),
            ("rm -rf .claude/worktrees/old", project),
            ("echo '{}' > ~/.claude/settings.json.bak", None),
        ):
            self.assertFalse(self.asks(command, cwd), command)

    def test_ordinary_commands_take_the_cheap_way_out(self):
        for command in ("ls -la", "npm test", "git status", "python3 -m pytest -q"):
            self.assertFalse(self.asks(command), command)

    def test_the_hook_says_nothing_about_a_read(self):
        self.assertIsNone(self.hook("cat ~/.claude/settings.json"))


class TestTheOtherFoldersInsideTheAssistantFolder(Home):
    """0.3.7. In 0.3.6 every folder inside the assistant folder counted as
    one of its own, so a line that moved into the folder where the client
    keeps a session's tool results and read one with an interpreter was asked
    about, about sixty times in one session, and nothing it ran wrote."""

    def setUp(self):
        super().setUp()
        self.results = os.path.join(
            self.claude, "projects", "a-project", "a-session", "tool-results"
        )
        os.makedirs(self.results)

    def test_reading_a_tool_result_with_an_interpreter(self):
        """Fails on 0.3.6, where every one of these was asked about."""
        for command, cwd in (
            (
                "cd ~/.claude/projects/a-project/a-session/tool-results/; "
                "python3 -c \"import json; d=json.load(open('result.txt')); "
                "print({k: 1 for k in d})\"",
                None,
            ),
            (
                "python3 -c \"import json; d=json.load(open('result.txt')); "
                "print(d[0]['text'][:500])\"",
                self.results,
            ),
            ("node -e \"console.log(require('./result.json'))\"", self.results),
            ("cd ~/.claude/skills && python3 -c \"print({1: 2})\"", None),
            ("cd ~/.claude/commands && cp a.md b.md", None),
        ):
            self.assertFalse(self.asks(command, cwd), command)
            self.assertIsNone(self.hook(command, cwd), command)

    def test_the_files_are_still_found_from_there(self):
        for command, cwd in (
            ("echo '{}' > ~/.claude/settings.local.json", self.results),
            ("rm -rf ../../../../plugins", self.results),
            ("cd ../../../.. && rm -rf plugins", self.results),
            (
                "python3 -c \"open('" + os.path.join(self.claude, "settings.json")
                + "','w')\"",
                self.results,
            ),
        ):
            self.assertTrue(self.asks(command, cwd), command)

    def test_the_assistant_folder_itself_is_still_guarded(self):
        for command, cwd in (
            ("cd ~/.claude && rm -rf plugins", None),
            ("cd ~/.claude && python3 -c \"open('settings.json','w')\"", None),
            ("cd ~/.claude/plugins/cache && python3 -c \"print({1: 2})\"", None),
        ):
            self.assertTrue(self.asks(command, cwd), command)

    def test_a_redirect_into_the_local_settings_from_anywhere(self):
        for cwd in (self.work, self.results, self.home, "/"):
            self.assertTrue(
                self.asks("echo '{}' > ~/.claude/settings.local.json", cwd), cwd
            )


class TestTheGateEntryPoint(Home):
    def test_a_check_that_cannot_finish_asks(self):
        real = settings_writes.writes_a_settings_file

        def broken(command, cwd):
            raise RuntimeError("could not finish")

        settings_writes.writes_a_settings_file = broken
        try:
            self.assertTrue(gate._asks_about_settings("anything", self.work))
        finally:
            settings_writes.writes_a_settings_file = real


if __name__ == "__main__":
    unittest.main()
