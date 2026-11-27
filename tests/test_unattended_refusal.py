"""Unit 4.2a of Plan 1, CS30: nothing is written into a base in a run nobody watches.

A conversation is marked unattended when the runner is started as unattended
(Unit 3.1 builds that start; `authority.mark_unattended` is the record), and
the mark stays for the rest of the conversation. From then on a file tool may
not write into any base in it. The other half of CS30, every approval refused
as the first thing the approval check does, sits in Release B's `approval.py`
and is the part of this unit left for the orchestrating session to clear.
"""

import os
import unittest

import support
import test_write_hook

from gtmbase import authority, write_hook


class TestAFileToolInAMarkedConversation(unittest.TestCase):
    def a_base(self, sandbox):
        root = os.path.join(sandbox.path, "base")
        support.make_base(root)
        return root

    def write_to(self, path, session):
        payload = test_write_hook.request(path, content="words\n")
        payload["session_id"] = session
        return write_hook.run(payload)

    def test_refused_inside_a_base_and_only_in_that_conversation(self):
        with support.Sandbox() as sandbox:
            root = self.a_base(sandbox)
            target = os.path.join(root, "context", "goals.md")
            self.assertIsNone(self.write_to(target, "watched"))
            authority.mark_unattended("unwatched")
            refused = self.write_to(target, "unwatched")
            self.assertEqual(
                "deny", refused["hookSpecificOutput"]["permissionDecision"]
            )
            self.assertEqual(
                write_hook.UNATTENDED_REFUSED,
                refused["hookSpecificOutput"]["permissionDecisionReason"],
            )
            self.assertIsNone(self.write_to(target, "watched"))

    def test_a_write_outside_every_base_is_left_alone(self):
        with support.Sandbox() as sandbox:
            self.a_base(sandbox)
            authority.mark_unattended("unwatched")
            elsewhere = os.path.join(sandbox.path, "notes", "today.md")
            self.assertIsNone(self.write_to(elsewhere, "unwatched"))

    def test_a_base_reached_through_a_link_is_still_a_base(self):
        with support.Sandbox() as sandbox:
            root = self.a_base(sandbox)
            link = os.path.join(sandbox.path, "shortcut")
            os.symlink(root, link)
            authority.mark_unattended("unwatched")
            refused = self.write_to(os.path.join(link, "context", "goals.md"), "unwatched")
            self.assertEqual("deny", refused["hookSpecificOutput"]["permissionDecision"])


if __name__ == "__main__":
    unittest.main()
