"""Unit 2: the loader every script copies, tried from three folder layouts."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import support
from support import PLUGIN_DIR, read

from gtmbase import shim

SCRIPTS_DIR = os.path.join(PLUGIN_DIR, "scripts")
TEMPLATE_PATH = os.path.join(SCRIPTS_DIR, "_shim_template.py")
VERSION_SCRIPT = os.path.join(SCRIPTS_DIR, "gtmbase_version.py")
LIB_DIR = os.path.join(PLUGIN_DIR, "lib")

SENTENCE = (
    "GTM Base could not find its library; reinstall the plugin with: "
    "claude plugin install gtm-base@gtm-base"
)


def bare_environment(**extra):
    """An environment with nothing in it that could point at the library."""
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "LC_ALL": "C",
    }
    environment.update(extra)
    return environment


def run_script(path, environment):
    return subprocess.run(
        [sys.executable, path],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TestTheCopyableShim(unittest.TestCase):
    def test_the_version_script_carries_the_template_block_unchanged(self):
        template = read(TEMPLATE_PATH)
        start = template.index("# --- gtm-base shim (copy from here) ---")
        end = template.index("# --- end of shim ---") + len("# --- end of shim ---")
        block = template[start:end]
        self.assertIn(block, read(VERSION_SCRIPT))

    def test_the_shim_never_imports_the_library_before_it_finds_it(self):
        for path in (TEMPLATE_PATH, VERSION_SCRIPT):
            text = read(path)
            shim_end = text.index("# --- end of shim ---")
            for line in text[:shim_end].split("\n"):
                stripped = line.strip()
                self.assertFalse(stripped.startswith("from gtmbase"), path)
                self.assertFalse(stripped.startswith("import gtmbase"), path)

    def test_the_module_holds_the_snippet_and_the_one_sentence(self):
        self.assertEqual(SENTENCE, shim.NOT_FOUND_SENTENCE)
        self.assertIn("def locate_lib(start)", shim.__doc__)
        self.assertIn("claude plugin install gtm-base@gtm-base", shim.__doc__)


class TestFindingTheLibrary(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="gtm-base-shim-")
        self.addCleanup(shutil.rmtree, self.folder, True)

    def copied_script(self):
        """The script copied into a skill folder, away from the plugin tree."""
        target = os.path.join(self.folder, "skills", "learn-from-call", "scripts")
        os.makedirs(target)
        path = os.path.join(target, "gtmbase_version.py")
        shutil.copyfile(VERSION_SCRIPT, path)
        return path

    def test_it_finds_the_library_beside_the_script_in_the_plugin(self):
        finished = run_script(VERSION_SCRIPT, bare_environment())
        self.assertEqual(0, finished.returncode, finished.stderr)
        self.assertEqual("0.1.0", finished.stdout.decode().strip())
        self.assertEqual(b"", finished.stderr)

    def test_it_finds_the_library_through_the_plugin_folder_the_client_names(self):
        path = self.copied_script()
        finished = run_script(path, bare_environment(CLAUDE_PLUGIN_ROOT=PLUGIN_DIR))
        self.assertEqual(0, finished.returncode, finished.stderr)
        self.assertEqual("0.1.0", finished.stdout.decode().strip())

    def test_it_finds_the_library_through_the_override(self):
        path = self.copied_script()
        finished = run_script(path, bare_environment(GTM_BASE_LIB=LIB_DIR))
        self.assertEqual(0, finished.returncode, finished.stderr)
        self.assertEqual("0.1.0", finished.stdout.decode().strip())

    def test_with_none_of_the_three_it_says_one_sentence_and_stops(self):
        path = self.copied_script()
        finished = run_script(path, bare_environment())
        self.assertEqual(3, finished.returncode)
        self.assertEqual(b"", finished.stdout)
        self.assertEqual(SENTENCE + "\n", finished.stderr.decode())

    def test_a_plugin_folder_that_holds_no_library_is_not_used(self):
        path = self.copied_script()
        empty = os.path.join(self.folder, "empty-plugin")
        os.makedirs(os.path.join(empty, "lib"))
        finished = run_script(path, bare_environment(CLAUDE_PLUGIN_ROOT=empty))
        self.assertEqual(3, finished.returncode)
        self.assertEqual(SENTENCE + "\n", finished.stderr.decode())


class TestTheLibraryCopyOfTheLoader(unittest.TestCase):
    def test_locate_lib_finds_the_plugin_layout(self):
        self.assertEqual(
            os.path.realpath(LIB_DIR),
            os.path.realpath(shim.locate_lib(VERSION_SCRIPT)),
        )

    def test_locate_lib_returns_nothing_when_there_is_nothing_to_find(self):
        folder = tempfile.mkdtemp(prefix="gtm-base-shim-")
        self.addCleanup(shutil.rmtree, folder, True)
        previous = {name: os.environ.get(name) for name in ("CLAUDE_PLUGIN_ROOT", "GTM_BASE_LIB")}
        for name in previous:
            os.environ.pop(name, None)
        try:
            self.assertIsNone(shim.locate_lib(os.path.join(folder, "script.py")))
        finally:
            for name, value in previous.items():
                if value is not None:
                    os.environ[name] = value

    def test_ensure_lib_puts_the_library_on_the_path(self):
        folder = shim.ensure_lib(VERSION_SCRIPT)
        self.assertIn(folder, sys.path)


if __name__ == "__main__":
    unittest.main()
