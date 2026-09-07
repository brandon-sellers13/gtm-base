"""Unit 1: the repository scaffold, the manifests, and the company-base template."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base", "lib")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")

for _path in (LIB_DIR, TESTS_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from gtmbase import constants, session_start  # noqa: E402
import plain_language  # noqa: E402


MARKETPLACE_PATH = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")
PLUGIN_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base")
PLUGIN_MANIFEST_PATH = os.path.join(PLUGIN_DIR, ".claude-plugin", "plugin.json")
HOOKS_PATH = os.path.join(PLUGIN_DIR, "hooks", "hooks.json")
TEMPLATE_DIR = os.path.join(REPO_ROOT, "templates", "company-base")
JOIN_GUIDE_PATH = os.path.join(REPO_ROOT, "docs", "join-guide.md")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def frontmatter(text):
    """Return the top-level frontmatter of a markdown file as a dict of strings."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def codeowners_rules(text):
    """Return the (pattern, owners) pairs of a CODEOWNERS file."""
    rules = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        rules.append((parts[0], parts[1:]))
    return rules


def codeowners_pattern_matches(pattern, path):
    """Whether a CODEOWNERS pattern matches a repository-relative path."""
    cleaned = pattern
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
        anchored = True
    else:
        anchored = "/" in cleaned.rstrip("/")[:-2] if cleaned.endswith("/**") else "/" in cleaned.rstrip("/")
    if cleaned.endswith("/"):
        cleaned = cleaned + "**"

    regex = ""
    index = 0
    while index < len(cleaned):
        if cleaned.startswith("**/", index):
            regex += "(?:.*/)?"
            index += 3
        elif cleaned.startswith("**", index):
            regex += ".*"
            index += 2
        elif cleaned[index] == "*":
            regex += "[^/]*"
            index += 1
        elif cleaned[index] == "?":
            regex += "[^/]"
            index += 1
        else:
            regex += re.escape(cleaned[index])
            index += 1

    if not anchored:
        regex = "(?:.*/)?" + regex
    return re.match("^" + regex + "$", path) is not None


def any_rule_matches(rules, path):
    return any(codeowners_pattern_matches(pattern, path) for pattern, _ in rules)


class TestManifests(unittest.TestCase):
    def test_both_manifests_parse_and_source_resolves(self):
        marketplace = read_json(MARKETPLACE_PATH)
        plugin = read_json(PLUGIN_MANIFEST_PATH)

        self.assertEqual(constants.MARKETPLACE_NAME, marketplace["name"])
        self.assertEqual("Brandon Sellers", marketplace["owner"]["name"])
        self.assertEqual(1, len(marketplace["plugins"]))

        entry = marketplace["plugins"][0]
        self.assertEqual("gtm-base", entry["name"])
        self.assertEqual("./plugins/gtm-base", entry["source"])

        resolved = os.path.normpath(
            os.path.join(os.path.dirname(MARKETPLACE_PATH), "..", entry["source"])
        )
        self.assertTrue(os.path.isdir(resolved), resolved)
        self.assertTrue(
            os.path.isfile(os.path.join(resolved, ".claude-plugin", "plugin.json"))
        )
        self.assertEqual(
            os.path.realpath(PLUGIN_DIR), os.path.realpath(resolved)
        )

        self.assertEqual("gtm-base", plugin["name"])
        self.assertEqual("0.2.1", plugin["version"])
        self.assertEqual("Brandon Sellers", plugin["author"]["name"])
        self.assertEqual("MIT", plugin["license"])
        self.assertTrue(plugin["keywords"])

        plugin_key = "%s@%s" % (plugin["name"], marketplace["name"])
        self.assertEqual(constants.PLUGIN_KEY, plugin_key)

    def test_no_mcp_servers_and_both_hooks_point_at_scripts_that_are_there(self):
        plugin = read_json(PLUGIN_MANIFEST_PATH)
        self.assertNotIn("mcpServers", plugin)
        # Claude Code loads hooks/hooks.json on its own; naming it in the
        # manifest as well makes the plugin fail to load (seen live 2026-09-06).
        self.assertNotIn("hooks", plugin)

        hooks = read_json(HOOKS_PATH)
        self.assertEqual({"PreToolUse", "SessionStart"}, set(hooks["hooks"].keys()))

        before_a_send = hooks["hooks"]["PreToolUse"]
        self.assertEqual(1, len(before_a_send))
        self.assertEqual("Bash", before_a_send[0]["matcher"])
        self.assertEqual(1, len(before_a_send[0]["hooks"]))

        declared = before_a_send[0]["hooks"][0]
        self.assertEqual("command", declared["type"])
        self.assertEqual(20, declared["timeout"])
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", declared["command"])
        self.assertTrue(declared["command"].endswith("/hooks/pre-push-gate.sh claude"))

        # Two entries: the first prints only what the person sees, the second
        # only what the assistant reads, because a client reads a hook's output
        # as one object or as plain text and never as both.
        at_session_start = hooks["hooks"]["SessionStart"]
        self.assertEqual(2, len(at_session_start))
        self.assertEqual(("visible", "context"), session_start.SESSION_START_PARTS)

        for entry, part in zip(at_session_start, session_start.SESSION_START_PARTS):
            # No matcher, so every kind of session start is seen.
            self.assertNotIn("matcher", entry)
            self.assertEqual(1, len(entry["hooks"]))

            session = entry["hooks"][0]
            self.assertEqual("command", session["type"])
            self.assertEqual(
                constants.SESSION_START_TIMEOUT_SECONDS, session["timeout"]
            )
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", session["command"])
            self.assertTrue(
                session["command"].endswith(
                    "/hooks/session-start.sh claude %s" % part
                ),
                session["command"],
            )

        for name in ("pre-push-gate.sh", "session-start.sh"):
            script = os.path.join(PLUGIN_DIR, "hooks", name)
            self.assertTrue(os.path.isfile(script), name)
            self.assertTrue(os.access(script, os.X_OK), "%s must be executable" % name)


class TestTemplateTree(unittest.TestCase):
    def test_template_holds_every_required_folder(self):
        for relative in constants.TEMPLATE_TREE_DIRS:
            path = os.path.join(TEMPLATE_DIR, relative)
            self.assertTrue(os.path.isdir(path), "missing folder: %s" % relative)

    def test_gitignore_covers_every_transient_folder(self):
        text = read_text(os.path.join(TEMPLATE_DIR, ".gitignore"))
        entries = set()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                entries.add(stripped.rstrip("/"))
        for relative in constants.TRANSIENT_DIRS:
            self.assertIn(relative, entries)

    def test_codeowners_gates_the_right_paths_and_leaves_the_team_folders_open(self):
        rules = codeowners_rules(read_text(os.path.join(TEMPLATE_DIR, "CODEOWNERS")))
        self.assertTrue(rules)
        for _, owners in rules:
            self.assertEqual(["@owner-handle"], owners)

        for open_path in (
            "work/confirmations/context--strategy--icp.md",
            "work/confirmations/.gitkeep",
            "work/decisions/2026-01-01-a-decision.md",
            "work/decisions/.gitkeep",
        ):
            self.assertFalse(
                any_rule_matches(rules, open_path),
                "%s must not be gated" % open_path,
            )

        for gated_path in (
            "corrections/2026-01-01.md",
            "context/strategy/icp.md",
            "plugins/gtm-base/README.md",
            ".claude/settings.json",
            "CLAUDE.md",
            "AGENTS.md",
            ".gitignore",
            "gate-allowlist.txt",
            "CODEOWNERS",
        ):
            self.assertTrue(
                any_rule_matches(rules, gated_path),
                "%s must be gated" % gated_path,
            )

    def test_every_context_file_carries_the_placeholder_owner_email(self):
        context_dir = os.path.join(TEMPLATE_DIR, constants.CONTEXT_DIR)
        seen = []
        for dirpath, _dirnames, filenames in os.walk(context_dir):
            for filename in filenames:
                if not filename.endswith(".md"):
                    continue
                path = os.path.join(dirpath, filename)
                seen.append(path)
                fields = frontmatter(read_text(path))
                owner = fields.get("owner", "")
                self.assertTrue(
                    EMAIL_RE.match(owner),
                    "owner in %s is not one valid email: %r" % (path, owner),
                )
                self.assertEqual(constants.OWNER_PLACEHOLDER_EMAIL, owner)
                self.assertIn("kind", fields)
                self.assertIn("last_confirmed", fields)
                self.assertIn("sources", fields)
                self.assertIn("status", fields)
        self.assertTrue(seen, "no template context files were found")

    def test_settings_file_has_exactly_two_keys_and_the_pinned_marketplace(self):
        settings = read_json(os.path.join(TEMPLATE_DIR, constants.SETTINGS_PATH))
        self.assertEqual(
            {"extraKnownMarketplaces", "enabledPlugins"}, set(settings.keys())
        )

        marketplaces = settings["extraKnownMarketplaces"]
        self.assertEqual([constants.MARKETPLACE_NAME], list(marketplaces.keys()))
        source = marketplaces[constants.MARKETPLACE_NAME]["source"]
        self.assertEqual("github", source["source"])
        self.assertEqual(constants.MARKETPLACE_REPO, source["repo"])
        self.assertTrue(SHA_RE.match(source["sha"]), source["sha"])

        self.assertEqual(
            {constants.PLUGIN_KEY: True}, settings["enabledPlugins"]
        )

    def test_map_carries_both_settings_lines_with_the_default_values(self):
        text = read_text(os.path.join(TEMPLATE_DIR, constants.MAP_PATH))
        self.assertIn(
            "confirmation_threshold_days: %d"
            % constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS,
            text,
        )
        self.assertIn(
            "not_now_days: %d" % constants.DEFAULT_NOT_NOW_DAYS, text
        )

    def test_allowlist_holds_only_the_placeholder_owner_email(self):
        text = read_text(os.path.join(TEMPLATE_DIR, constants.ALLOWLIST_PATH))
        self.assertTrue(text.startswith("#"))
        entries = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertEqual([constants.OWNER_PLACEHOLDER_EMAIL], entries)


class TestPlainLanguage(unittest.TestCase):
    def test_user_facing_documents_pass_the_lint(self):
        for path in (
            JOIN_GUIDE_PATH,
            os.path.join(TEMPLATE_DIR, "README.md"),
        ):
            plain_language.assert_plain(self, path)

    def test_the_lint_itself_catches_what_it_should(self):
        text = "We merged the branch.\nThen cloning the pull requests.\n"
        found = plain_language.find_banned(text)
        words = set(word for word, _line in found)
        self.assertEqual(
            {"merge", "branch", "clone", "pull request"}, words
        )
        self.assertEqual(
            [("\u2014", 1)], plain_language.find_dashes("a \u2014 b")
        )
        self.assertEqual([], plain_language.find_banned("a straightforward guide"))


class TestFakeGh(unittest.TestCase):
    def test_fake_gh_records_the_call_and_returns_the_canned_json(self):
        gh_path = shutil.which("gh")
        self.assertIsNotNone(gh_path, "the fake gh must be on PATH")
        self.assertEqual(
            os.path.realpath(os.path.join(TESTS_DIR, "fakes", "gh")),
            os.path.realpath(gh_path),
        )

        workdir = tempfile.mkdtemp(prefix="gtm-base-test-")
        try:
            log_path = os.path.join(workdir, "calls.jsonl")
            environment = dict(os.environ)
            environment["GH_FAKE_LOG"] = log_path
            result = subprocess.run(
                ["gh", "pr", "create", "--title", "Proposal"],
                cwd=workdir,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout.decode("utf-8"))
            self.assertEqual(1, payload["number"])
            self.assertEqual(
                "https://github.com/example/example/pull/1", payload["url"]
            )

            with open(log_path, encoding="utf-8") as handle:
                lines = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual(1, len(lines))
            self.assertEqual(
                ["pr", "create", "--title", "Proposal"], lines[0]["argv"]
            )
            self.assertEqual(
                os.path.realpath(workdir), os.path.realpath(lines[0]["cwd"])
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


class TestConstants(unittest.TestCase):
    def test_constants_import_and_every_path_is_relative(self):
        self.assertEqual("0.2.1", __import__("gtmbase").__version__)
        for name in dir(constants):
            if name.startswith("_"):
                continue
            if not (name.endswith("_DIR") or name.endswith("_PATH") or name.endswith("_DIRS")):
                continue
            value = getattr(constants, name)
            values = value if isinstance(value, tuple) else (value,)
            for item in values:
                self.assertIsInstance(item, str, name)
                self.assertFalse(
                    item.startswith("/"), "%s must be relative: %r" % (name, item)
                )
                self.assertFalse(
                    item.startswith("~"), "%s must be relative: %r" % (name, item)
                )
                self.assertFalse(
                    item.startswith(".."), "%s must be relative: %r" % (name, item)
                )


if __name__ == "__main__":
    unittest.main()
