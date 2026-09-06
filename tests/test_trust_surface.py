"""Unit 3: whether a folder may be trusted as a base before anything acts on it."""

import json
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base", "lib")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")

for _path in (LIB_DIR, TESTS_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import support  # noqa: E402
from gtmbase import constants, trust_surface  # noqa: E402


class TrustSurfaceTest(unittest.TestCase):
    def setUp(self):
        self.parent = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-trust-"))
        self.addCleanup(shutil.rmtree, self.parent, True)

    def check(self, **kwargs):
        root = support.trust_checkout(self.parent, **kwargs)
        return root, trust_surface.check(root)

    # --- the clean folder ---------------------------------------------------

    def test_a_clean_checkout_passes(self):
        _root, result = self.check()
        self.assertTrue(result.ok, result.codes)
        self.assertEqual([], result.codes)

    # --- the hostile folders ------------------------------------------------

    def test_an_instruction_file_at_the_root_fails(self):
        _root, result = self.check(flaw="claude-md")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_INSTRUCTION_FILE, result.codes)

    def test_an_instruction_file_deeper_in_the_tree_fails(self):
        _root, result = self.check(flaw="nested-claude")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_INSTRUCTION_FILE, result.codes)

    def test_an_agents_file_deeper_in_the_tree_fails(self):
        _root, result = self.check(flaw="agents-md")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_INSTRUCTION_FILE, result.codes)

    def test_a_settings_folder_entry_in_another_letter_case_fails(self):
        _root, result = self.check(flaw="claude-folder")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_CLAUDE_FOLDER_ENTRY, result.codes)

    def test_a_code_file_anywhere_fails(self):
        _root, result = self.check(flaw="code-file")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_CODE_FILE, result.codes)

    def test_a_link_anywhere_fails(self):
        _root, result = self.check(flaw="symlink")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_SYMLINK, result.codes)

    def test_a_folder_of_plugins_fails(self):
        _root, result = self.check(flaw="plugins-folder")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_PLUGINS_FOLDER, result.codes)

    def test_a_map_that_is_a_link_fails(self):
        _root, result = self.check(flaw="symlinked-map")
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_MAP_NOT_A_FILE, result.codes)
        self.assertIn(trust_surface.CODE_SYMLINK, result.codes)

    def test_a_name_written_with_its_accent_apart_is_compared_as_one_name(self):
        # The fixture holds the name with the accent stored apart from its
        # letter. It is not one of the refused names, so the folder passes, and
        # the comparison the check uses reads both spellings as one name.
        _root, result = self.check(flaw="decomposed")
        self.assertTrue(result.ok, result.codes)

        composed = "CLAUDÉ.md"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(
            trust_surface.normalize_component(composed),
            trust_surface.normalize_component(decomposed),
        )
        self.assertEqual(
            "claude.md", trust_surface.normalize_component("CLAUDE.md")
        )

    # --- the settings file --------------------------------------------------

    def settings_with(self, change):
        payload = json.loads(support.SETTINGS_TEXT)
        change(payload)
        return json.dumps(payload, indent=2)

    def test_a_third_key_fails(self):
        text = self.settings_with(lambda payload: payload.update({"model": "opus"}))
        _root, result = self.check(flaw=None, name="third-key", settings_text=text)
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_SETTINGS_KEYS, result.codes)

    def test_a_moving_reference_instead_of_a_pinned_version_fails(self):
        def change(payload):
            payload["extraKnownMarketplaces"]["gtm-base"]["source"]["sha"] = "main"

        _root, result = self.check(
            flaw=None, name="branch-ref", settings_text=self.settings_with(change)
        )
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_MARKETPLACE_SHA, result.codes)

    def test_a_different_repository_fails(self):
        def change(payload):
            payload["extraKnownMarketplaces"]["gtm-base"]["source"]["repo"] = (
                "someone-else/gtm-base"
            )

        _root, result = self.check(
            flaw=None, name="other-repo", settings_text=self.settings_with(change)
        )
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_MARKETPLACE_REPO, result.codes)

    def test_a_different_plugin_key_fails(self):
        def change(payload):
            payload["enabledPlugins"] = {"someone-else@gtm-base": True}

        _root, result = self.check(
            flaw=None, name="other-plugin", settings_text=self.settings_with(change)
        )
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_PLUGIN_KEY, result.codes)

    def test_a_source_that_is_not_github_fails(self):
        def change(payload):
            payload["extraKnownMarketplaces"]["gtm-base"]["source"]["source"] = "git"

        _root, result = self.check(
            flaw=None, name="other-source", settings_text=self.settings_with(change)
        )
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_MARKETPLACE_SOURCE, result.codes)

    def test_a_settings_file_that_is_not_json_fails(self):
        _root, result = self.check(
            flaw=None, name="not-json", settings_text="not settings at all\n"
        )
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_SETTINGS_MALFORMED, result.codes)

    def test_a_missing_settings_file_fails(self):
        root = support.trust_checkout(self.parent, name="no-settings")
        os.remove(os.path.join(root, constants.SETTINGS_PATH))
        result = trust_surface.check(root)
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_SETTINGS_MISSING, result.codes)

    # --- the walk itself ----------------------------------------------------

    def test_the_codes_come_back_sorted_and_without_repeats(self):
        root = support.trust_checkout(self.parent, name="two-problems")
        support.write(os.path.join(root, "claude.md"), "one\n")
        support.write(os.path.join(root, "context", "CLAUDE.md"), "two\n")
        support.write(os.path.join(root, "context", "helper.py"), "x = 1\n")
        result = trust_surface.check(root)
        self.assertEqual(sorted(set(result.codes)), result.codes)
        self.assertEqual(
            [trust_surface.CODE_CODE_FILE, trust_surface.CODE_INSTRUCTION_FILE],
            result.codes,
        )

    def test_a_tree_larger_than_the_cap_is_refused_rather_than_walked(self):
        root = support.trust_checkout(self.parent, name="too-large")
        saved = constants.TRUST_WALK_CAP
        constants.TRUST_WALK_CAP = 2
        try:
            result = trust_surface.check(root)
        finally:
            constants.TRUST_WALK_CAP = saved
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_TREE_TOO_LARGE, result.codes)

    def test_a_folder_that_is_not_there_is_refused(self):
        result = trust_surface.check(os.path.join(self.parent, "nowhere"))
        self.assertFalse(result.ok)
        self.assertIn(trust_surface.CODE_TREE_UNREADABLE, result.codes)


class TestTheOneRefusedSet(unittest.TestCase):
    """`path_is_refused` is the set both the folder check and the update use."""

    def test_the_names_no_folder_may_hold_and_no_update_may_carry(self):
        import unicodedata

        for path in (
            ".Claude/settings.local.json",
            "claude.md",
            "context/CLAUDE.md",
            "ClAuDe.Md",
            unicodedata.normalize("NFD", "CLAUDE.md"),
            ".mcp.json",
            ".codex/config",
            "plugins/x.json",
            "tools/x.SH",
            "context/helper.py",
        ):
            self.assertTrue(
                trust_surface.path_is_refused(path.split("/")), path
            )

    def test_the_one_name_allowed_under_the_settings_folder(self):
        self.assertFalse(trust_surface.path_is_refused([".claude", "settings.json"]))
        self.assertTrue(
            trust_surface.path_is_refused(["work", ".claude", "settings.json"])
        )

    def test_the_ordinary_files_of_a_base_are_not_refused(self):
        for path in (
            "context/map.md",
            "context/strategy/icp.md",
            "work/decisions/2026-08-02-a-decision.md",
            "corrections/2026-08-02-a-correction.md",
            "CODEOWNERS",
        ):
            self.assertFalse(
                trust_surface.path_is_refused(path.split("/")), path
            )


if __name__ == "__main__":
    unittest.main()
