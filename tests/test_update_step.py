"""Track 4, Unit T4.7: update GTM Base.

"Update GTM Base" says the installed version and the one step that updates
it, makes no network call, runs nothing, and claims nothing about a newer
release (call 4). In a base it then says what the base can now take that it
does not hold, and writes nothing.
"""

import json
import os
import subprocess
import unittest
from unittest import mock

import support
import test_drift_grade as drift

from gtmbase import update_check


def a_plugin_json(sandbox, value):
    path = os.path.join(sandbox.path, "plugin.json")
    support.write(path, value if isinstance(value, str) else json.dumps(value))
    return path


class TheVersionAndTheStep(unittest.TestCase):
    def test_it_names_the_installed_version_and_the_step(self):
        version = json.loads(support.read(update_check.PLUGIN_JSON))["version"]
        found = update_check.check()
        self.assertIsNone(found.code)
        self.assertEqual(version, found.version)
        self.assertIn(version, found.sentence)
        for command in (
            update_check.REFRESH_COMMAND,
            update_check.UPDATE_COMMAND,
            update_check.RELOAD_COMMAND,
        ):
            self.assertIn(command, found.sentence)

    def test_it_claims_nothing_about_a_newer_release(self):
        sentence = update_check.check().sentence.lower()
        self.assertIn("cannot say whether a newer version is out", sentence)
        self.assertNotIn("is available", sentence)
        self.assertNotIn("up to date", sentence)

    def test_it_runs_nothing_and_looks_nothing_up(self):
        with mock.patch.object(subprocess, "run") as ran, mock.patch.object(
            subprocess, "Popen"
        ) as opened, mock.patch("socket.socket") as sockets:
            update_check.check()
        ran.assert_not_called()
        opened.assert_not_called()
        sockets.assert_not_called()

    def test_a_version_it_cannot_read_is_one_sentence_and_a_code(self):
        with support.Sandbox() as sandbox:
            for value in ("not json", {"name": "gtm-base"}, {"version": "soon"}, {"version": 5}):
                with self.subTest(value=value):
                    found = update_check.check(a_plugin_json(sandbox, value))
                    self.assertEqual(update_check.CODE_VERSION_UNREADABLE, found.code)
                    self.assertIsNone(found.version)
                    self.assertNotIn("installed. ", found.sentence)
            missing = update_check.check(os.path.join(sandbox.path, "nothing.json"))
            self.assertEqual(update_check.CODE_VERSION_UNREADABLE, missing.code)

    def test_saying_it_twice_says_the_same_thing(self):
        self.assertEqual(update_check.check().sentence, update_check.check().sentence)


class WhatTheBaseCanTake(unittest.TestCase):
    def test_a_base_is_told_the_kinds_and_skills_it_can_now_take(self):
        with support.Sandbox() as sandbox:
            root, base_id = drift.a_base(sandbox)
            items = update_check.base_can_take(root, base_id, runner=support.NoRemoteRunner())
            self.assertIn("your competitors document", items)
            self.assertIn("your design guide", items)
            self.assertIn("the drift grade skill", items)

    def test_it_writes_nothing_and_says_the_same_thing_twice(self):
        with support.Sandbox() as sandbox:
            root, base_id = drift.a_base(sandbox)
            before = support.status_of(root)
            first = update_check.base_sentence(root, base_id, runner=support.NoRemoteRunner())
            second = update_check.base_sentence(root, base_id, runner=support.NoRemoteRunner())
            self.assertEqual(first, second)
            self.assertEqual(before, support.status_of(root))
            self.assertFalse(
                os.path.exists(os.path.join(root, "context", "competitors.md"))
            )

    def test_a_skill_the_base_holds_is_not_listed(self):
        with support.Sandbox() as sandbox:
            root, base_id = drift.installed(sandbox)
            items = update_check.base_can_take(root, base_id, runner=support.NoRemoteRunner())
            self.assertNotIn("the drift grade skill", items)


if __name__ == "__main__":
    unittest.main()
