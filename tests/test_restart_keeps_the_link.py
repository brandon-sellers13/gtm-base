"""A restart of the computer no longer drops the link between a base and its folder.

Finding 1 of step 7 of the Release A live check (2026-10-10). macOS hands out
device numbers when a disk is mounted, so the same internal disk can come back
from a restart with a new one. The comparison called that a disk that came
back as a different disk, the resolver treated it as a different folder, and
every GTM Base command in the linked folder refused until the person linked it
again. The record also carries the disk's own identifier, kept for exactly this
case, and it agreed. When both records carry that identifier and it agrees, a
changed device number is now the same folder, and the stored number is brought
up to date. A different identifier is still a disk that came back as another.

Finding 2 of the same step is here too: linking the folder again took two
failed commands. The step that hands out a file for the folder's name could
not find the base from a folder whose link had been dropped, or from a company
name, which are the two ways the skill told the assistant to name it.

The device numbers and the disk identifier here are made up by the test. The
disk tool is never asked, so the tests run the same on any computer.
"""

import contextlib
import os
import subprocess
import sys
import unittest
from unittest import mock

import support

from gtmbase import folder_identity, machine, paths, session_start

PLUGIN_ROOT = support.PLUGIN_DIR
SHIM = os.path.join(PLUGIN_ROOT, "skills", "join", "scripts", "join.py")
SKILL = os.path.join(PLUGIN_ROOT, "skills", "join", "SKILL.md")
NOW = __import__("datetime").datetime(2026, 10, 10, 9, 0, 0)

THE_DISK = "1A2B3C4D-0000-4000-8000-00000000AAAA"
ANOTHER_DISK = "1A2B3C4D-0000-4000-8000-00000000BBBB"


def record(**changes):
    base = {
        "dev": 16777230,
        "ino": 4242,
        "birth": 1700000000,
        "mount": "/System/Volumes/Data",
        "volume": THE_DISK,
        "remote": None,
    }
    base.update(changes)
    return base


@contextlib.contextmanager
def the_disk_says(volume):
    """The disk tool's answer for every folder, for the length of a block."""
    with mock.patch.object(folder_identity, "volume_id", return_value=volume):
        yield


class TestTheComparison(unittest.TestCase):
    def test_a_new_device_number_on_the_same_disk_is_the_same_folder(self):
        """Fails on 0.3.5, which called this a disk that came back."""
        self.assertEqual(
            folder_identity.SAME,
            folder_identity.matches(record(), record(dev=16777231)),
        )

    def test_a_new_device_number_on_another_disk_is_still_a_remount(self):
        self.assertEqual(
            folder_identity.REMOUNTED,
            folder_identity.matches(
                record(), record(dev=16777231, volume=ANOTHER_DISK)
            ),
        )

    def test_a_new_device_number_with_no_disk_identifier_is_still_a_remount(self):
        """Without the disk's own identifier there is nothing to vouch for it."""
        for recorded, current in (
            (record(volume=None), record(dev=16777231)),
            (record(), record(dev=16777231, volume=None)),
            (record(volume=None), record(dev=16777231, volume=None)),
        ):
            self.assertEqual(
                folder_identity.REMOUNTED,
                folder_identity.matches(recorded, current),
                (recorded, current),
            )

    def test_a_new_device_number_in_a_new_place_is_still_a_remount(self):
        """A copy of the whole disk mounted somewhere else carries the same
        disk identifier, folder number and birth. A restart never moves the
        folder, so a new number together with a new place is not one."""
        import tempfile

        here = tempfile.mkdtemp(prefix="gtm-base-restart-")
        try:
            current = record(dev=16777231)
            current["dev"] = os.stat(here).st_dev
            current["ino"] = os.stat(here).st_ino
            recorded = dict(current, dev=current["dev"] + 7)
            elsewhere = os.path.join(here, "not-the-recorded-place")

            self.assertEqual(
                folder_identity.SAME, folder_identity.matches(recorded, current, here)
            )
            self.assertEqual(
                folder_identity.REMOUNTED,
                folder_identity.matches(recorded, current, elsewhere),
            )
        finally:
            os.rmdir(here)

    def test_the_other_evidence_still_has_to_agree(self):
        for changed in (
            {"ino": 4243},
            {"birth": 1700000001},
            {"remote": "https://example.test/acme/marketing"},
        ):
            current = record(dev=16777231)
            current.update(changed)
            self.assertEqual(
                folder_identity.DIFFERENT,
                folder_identity.matches(record(), current),
                changed,
            )


class TestTheLinkAfterARestart(unittest.TestCase):
    """The resolver and the session start, with the stored number made stale."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.root, self.base_id = self.sandbox.base("Acme")
        self.folder = os.path.realpath(os.path.join(self.sandbox.path, "marketing"))
        os.makedirs(self.folder)
        support.write(os.path.join(self.folder, "deck.md"), "# A deck\n")
        with the_disk_says(THE_DISK):
            machine.link_content(self.base_id, self.folder)

    def stored(self):
        entry = machine.find_joined_by_id(
            machine.load_machine_state_raw(), self.base_id
        )
        return entry["content_root"], dict(entry["content_identity"])

    def restart(self):
        """Write the record down as a restart leaves it: an older device number."""
        state = machine.load_machine_state_raw()
        entry = machine.find_joined_by_id(state, self.base_id)
        entry["content_identity"]["dev"] = os.stat(self.folder).st_dev + 7
        machine.save_machine_state(state)
        return entry["content_identity"]["dev"]

    def test_the_link_was_taken_with_the_disk_identifier(self):
        _root, identity = self.stored()
        self.assertEqual(THE_DISK, identity["volume"])

    def test_the_folder_still_opens_its_base_after_a_restart(self):
        """Fails on 0.3.5, which answered that the link no longer matched."""
        self.restart()
        with the_disk_says(THE_DISK):
            found = paths.resolve_base(self.folder, machine.load_machine_state())

        self.assertEqual(paths.CODE_LINKED, found.code)
        self.assertEqual(os.path.realpath(self.root), found.root)

    def test_the_session_start_brings_the_stored_number_up_to_date(self):
        self.restart()
        with the_disk_says(THE_DISK):
            primed = session_start.run(
                {"session_id": "s-1", "source": "startup", "cwd": self.folder},
                now=NOW,
                plugin_root=PLUGIN_ROOT,
                part="context",
            )

        self.assertIsInstance(primed, str)
        self.assertIn("# Map", primed)
        self.assertNotIn(session_start.LINK_MISMATCH, primed)
        root, identity = self.stored()
        self.assertEqual(self.folder, root)
        self.assertEqual(os.stat(self.folder).st_dev, identity["dev"])
        self.assertEqual(THE_DISK, identity["volume"])

    def test_the_half_a_person_reads_opens_the_base_and_writes_nothing(self):
        stale = self.restart()
        with the_disk_says(THE_DISK):
            shown = session_start.run(
                {"session_id": "s-1", "source": "startup", "cwd": self.folder},
                now=NOW,
                plugin_root=PLUGIN_ROOT,
                part="visible",
            )

        self.assertNotEqual(
            session_start.LINK_MISMATCH, (shown or {}).get("systemMessage")
        )
        self.assertEqual(stale, self.stored()[1]["dev"])

    def test_another_disk_is_still_told_to_link_the_folder_again(self):
        stale = self.restart()
        with the_disk_says(ANOTHER_DISK):
            primed = session_start.run(
                {"session_id": "s-1", "source": "startup", "cwd": self.folder},
                now=NOW,
                plugin_root=PLUGIN_ROOT,
                part="context",
            )

        self.assertEqual(session_start.LINK_MISMATCH, primed)
        self.assertEqual(stale, self.stored()[1]["dev"])

    def test_a_disk_tool_that_says_nothing_changes_nothing(self):
        stale = self.restart()
        with the_disk_says(None):
            found = paths.resolve_base(self.folder, machine.load_machine_state())

        self.assertEqual(paths.CODE_LINK_MISMATCH, found.code)
        self.assertEqual(stale, self.stored()[1]["dev"])


def shim(cwd, *arguments):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = support.LIB_DIR
    return subprocess.run(
        [sys.executable, SHIM] + list(arguments),
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def value_of(output, name):
    for row in output.decode("utf-8").splitlines():
        if row.startswith(name + "="):
            return row[len(name) + 1 :].strip('"')
    return None


class TestLinkingTheFolderAgain(unittest.TestCase):
    """The commands the skill shows, run from a folder whose link was dropped."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        support.write(
            os.path.join(os.environ["HOME"], ".gitconfig"),
            "[user]\n\temail = dana@acme.test\n\tname = Dana\n",
        )
        # Laid out the way a base built centrally is, in a folder named for
        # the company, which is what naming a base by its company matches.
        self.root, self.base_id = self.sandbox.base(os.path.join("Acme", "gtm-base"))
        self.folder = os.path.realpath(os.path.join(self.sandbox.path, "marketing"))
        os.makedirs(self.folder)

    def linked_folder(self):
        entry = machine.find_joined_by_id(
            machine.load_machine_state_raw(), self.base_id
        )
        return entry.get("content_root")

    def test_a_file_for_the_folder_is_handed_out_from_the_folder_itself(self):
        """Fails on 0.3.5: the step could not tell which base the file was for."""
        made = shim(self.folder, "words-file", "--for", "folder")

        self.assertEqual(0, made.returncode, made.stdout)
        self.assertTrue(value_of(made.stdout, "words"))

    def test_a_file_for_the_folder_is_handed_out_by_the_company_name(self):
        """Fails on 0.3.5: a company name was read as the name of a folder."""
        made = shim(self.folder, "words-file", "--base", "Acme", "--for", "folder")

        self.assertEqual(0, made.returncode, made.stdout)
        path = value_of(made.stdout, "words")
        support.write(path, self.folder + "\n")

        linked = shim(
            self.folder, "link", "--base", "Acme", "--folder-file", path
        )

        self.assertEqual(0, linked.returncode, linked.stdout)
        self.assertEqual(self.folder, self.linked_folder())

    def test_the_folder_the_command_runs_in_is_linked_when_none_is_named(self):
        """The command the skill shows for the ordinary case, exactly as written."""
        linked = shim(self.folder, "link")

        self.assertEqual(0, linked.returncode, linked.stdout)
        self.assertIn(b"now linked", linked.stdout)
        self.assertEqual(self.folder, self.linked_folder())

    def test_the_home_folder_is_never_linked(self):
        linked = shim(os.environ["HOME"], "link")

        self.assertNotEqual(0, linked.returncode)
        self.assertIn(b"holds all of your other folders", linked.stdout)
        self.assertIsNone(self.linked_folder())

    def test_with_two_bases_the_file_step_names_both_rather_than_a_setup_run(self):
        self.sandbox.base(os.path.join("Other", "gtm-base"))

        made = shim(self.folder, "words-file", "--for", "folder")

        self.assertNotEqual(0, made.returncode)
        self.assertIn(os.path.realpath(self.root).encode("utf-8"), made.stdout)
        self.assertNotIn(b"setup run", made.stdout)
        named = shim(self.folder, "words-file", "--base", "Acme", "--for", "folder")
        self.assertEqual(0, named.returncode, named.stdout)

    def test_the_skill_shows_that_command_exactly_as_it_is_run(self):
        with open(SKILL, encoding="utf-8") as handle:
            text = handle.read()
        section = text.split("## Linking a folder", 1)[1].split("\n## ", 1)[0]

        # The skill's own folder, which the client writes in when the skill
        # loads, so the command runs from whatever folder the person is in.
        self.assertIn(
            '```\npython3 "${CLAUDE_SKILL_DIR}/scripts/join.py" link\n```', section
        )
        self.assertNotIn("python3 scripts/join.py", section)
        self.assertNotIn("words-file --base", section)


if __name__ == "__main__":
    unittest.main()
