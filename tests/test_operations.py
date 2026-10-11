"""Unit 4.2a of Plan 1: creating a document, and the five settings operations.

The signed company-skills requirements, CS1, CS5, CS9 and CS15 to CS17.
Creating is absent-only and all or nothing; the creator owns what they create.
A document's owner line and business line, and the map's owner,
administrators and businesses, each change only through their own operation,
which shows the whole new file first, is bound to what was shown, is approved
by the right people, and is recorded with its reason. Nothing else about a
settings block, or the map, can be changed through GTM Base.

The proof that a person answered Claude Code's question is Release B's, held
by the suite as for every approval. Every fixture is written from scratch.
"""

import os
import unittest
from unittest import mock

import support
import test_approve_local as approving

from gtmbase import authority, constants, formats, operations
from gtmbase.errors import GtmBaseError

NOW = approving.NOW
OWNER = approving.OWNER
WRITER = "writer@example.com"
ADMIN = "admin@example.com"
STRANGER = "stranger@example.com"
NoRemoteRunner = support.NoRemoteRunner
POSITIONING = "context/positioning.md"


def a_base(sandbox):
    """A base whose map names its owner, one administrator and two businesses."""
    root, base_id = approving.local_base(sandbox)
    map_path = os.path.join(root, constants.MAP_PATH)
    support.write(
        map_path,
        support.read(map_path).replace(
            "owner: %s\n" % OWNER,
            "owner: %s\nadministrators: [%s]\nbusinesses: insights, courier-app\n"
            % (OWNER, ADMIN),
            1,
        ),
    )
    support.write(
        os.path.join(root, POSITIONING),
        "---\nkind: positioning\nowner: %s\nsources: []\nstatus: draft\n---\n\n"
        "# Positioning\n\nWords.\n" % WRITER,
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "roles"], cwd=root)
    return root, base_id


def as_address(root, address):
    support.git(["config", "--local", "user.email", address], cwd=root)


def snapshot(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as handle:
                found[os.path.relpath(path, root)] = handle.read()
    return found


def head(root):
    return support.head_of(root)


def the_newest_record(root):
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    names = sorted(name for name in os.listdir(folder) if name.endswith(".md"))
    return formats.CorrectionsFile.parse(support.read(os.path.join(folder, names[-1])))


def created(root, base_id, files, reason="We need it.", runner=None):
    runner = runner or NoRemoteRunner()
    prepared = operations.prepare_creation(root, base_id, files, reason, runner=runner)
    return operations.approve(root, base_id, prepared.prepared_id, prepared.shown, runner=runner, now=NOW)


GOALS = "---\nkind: goals\nsources: []\nstatus: draft\n---\n\n# Goals\n\nGrow.\n"


class TestCreating(unittest.TestCase):
    """CS1 and CS5: anyone joined may create a document, and owns it."""

    def test_a_new_document_is_written_owned_by_its_creator_and_recorded(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, STRANGER)
            prepared = operations.prepare_creation(
                root, base_id, [("context/courier-app/goals.md", GOALS)], "We need goals.",
                runner=NoRemoteRunner(),
            )
            # The artifact is the whole of what will be written, owner and all.
            self.assertIn("owner: %s" % STRANGER, prepared.artifact)
            self.assertIn("Grow.", prepared.artifact)
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=NOW,
            )
            self.assertTrue(done.done, done.sentence)
            written = support.read(os.path.join(root, "context/courier-app/goals.md"))
            self.assertIn("owner: %s" % STRANGER, written)
            record = the_newest_record(root)
            import test_authority_everywhere as everywhere

            saved_by, text = everywhere.author_of_newest_record(root)
            self.assertEqual(STRANGER, saved_by)
            self.assertNotIn(STRANGER, text)
            self.assertEqual(
                {"context/courier-app/goals.md": authority.ROLE_OWNER}, record.approved_roles
            )
            self.assertEqual(
                {"context/courier-app/goals.md": authority.file_hash(root, "context/courier-app/goals.md")},
                record.approved_hashes,
            )
            self.assertIn("We need goals.", record.why)
            self.assertEqual(b"", support.git(["status", "--porcelain"], cwd=root).stdout)

    def test_a_standard_and_the_source_map_can_be_created(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            done = created(root, base_id, [("standards/ad-testing.md", GOALS)])
            self.assertTrue(done.done, done.sentence)

    def test_a_path_that_exists_is_refused(self):
        """Edge case: absent-only."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_creation(
                    root, base_id, [(POSITIONING, GOALS)], "again", runner=NoRemoteRunner()
                )

    def test_a_path_that_appears_after_the_showing_is_refused_and_written_over_by_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", GOALS)], "x", runner=NoRemoteRunner()
            )
            support.write(os.path.join(root, "context/goals.md"), "mine\n")
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=NOW,
            )
            self.assertFalse(done.done)
            self.assertEqual("mine\n", support.read(os.path.join(root, "context/goals.md")))

    def test_three_files_where_the_third_fails_leave_none_of_them(self):
        """Edge case: all or nothing."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            files = [
                ("context/goals.md", GOALS),
                ("context/metrics.md", GOALS),
                ("standards/ad-testing.md", GOALS),
            ]
            prepared = operations.prepare_creation(root, base_id, files, "x", runner=NoRemoteRunner())
            before, before_head = snapshot(root), head(root)
            real = operations.atomic_write_text
            calls = []

            def third_fails(path, text, *args, **kwargs):
                calls.append(path)
                if len(calls) == 3:
                    raise OSError("the disk is full")
                return real(path, text, *args, **kwargs)

            with mock.patch.object(operations, "atomic_write_text", third_fails):
                done = operations.approve(
                    root, base_id, prepared.prepared_id, prepared.shown,
                    runner=NoRemoteRunner(), now=NOW,
                )
            self.assertFalse(done.done)
            self.assertEqual(before, snapshot(root))
            self.assertEqual(before_head, head(root))
            self.assertEqual(b"", support.git(["status", "--porcelain"], cwd=root).stdout)

    def test_a_save_that_fails_leaves_nothing_either(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", GOALS)], "x", runner=NoRemoteRunner()
            )
            before, before_head = snapshot(root), head(root)
            with mock.patch.object(operations, "_save", side_effect=GtmBaseError("no", code="git-failed")):
                done = operations.approve(
                    root, base_id, prepared.prepared_id, prepared.shown,
                    runner=NoRemoteRunner(), now=NOW,
                )
            self.assertFalse(done.done)
            self.assertEqual(before, snapshot(root))
            self.assertEqual(before_head, head(root))
            self.assertEqual(b"", support.git(["status", "--porcelain"], cwd=root).stdout)

    def test_the_yes_is_bound_to_what_was_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", GOALS)], "x", runner=NoRemoteRunner()
            )
            done = operations.approve(
                root, base_id, prepared.prepared_id, "0" * 64, runner=NoRemoteRunner(), now=NOW
            )
            self.assertFalse(done.done)
            self.assertFalse(os.path.exists(os.path.join(root, "context/goals.md")))

    def test_a_document_holding_a_key_is_refused_before_it_is_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            text = GOALS.replace("Grow.", "Our key is sk-" + "a1B2c3D4e5F6g7H8i9J0k1L2")
            with self.assertRaises(operations.Refused):
                operations.prepare_creation(
                    root, base_id, [("context/goals.md", text)], "x", runner=NoRemoteRunner()
                )

    def test_what_is_not_a_document_or_may_not_be_created_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            for path in (
                constants.MAP_PATH,
                "learning/changes/stg-0000000000000000.md",
                "learning/corrections/2026-06-05-x.md",
                "work/confirmations/x.md",
                "skills/ad-testing/SKILL.md",
                "CLAUDE.md",
                "../outside.md",
            ):
                with self.subTest(path=path):
                    with self.assertRaises(operations.Refused):
                        operations.prepare_creation(
                            root, base_id, [(path, GOALS)], "x", runner=NoRemoteRunner()
                        )


class TestALesson(unittest.TestCase):
    """Happy path: a lesson is created, owned by its creator, and never edited."""

    def test_created_and_owned(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            done = created(root, base_id, [("learning/lessons/cheaper-hooks.md", GOALS)])
            self.assertTrue(done.done, done.sentence)
            text = support.read(os.path.join(root, "learning/lessons/cheaper-hooks.md"))
            self.assertIn("owner: %s" % WRITER, text)

    def test_never_changed_through_a_settings_operation(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            created(root, base_id, [("learning/lessons/cheaper-hooks.md", GOALS)])
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_OWNER, "x",
                    path="learning/lessons/cheaper-hooks.md", value=WRITER,
                    runner=NoRemoteRunner(),
                )


def set_it(root, base_id, operation, value, path=None, reason="Because.", runner=None):
    runner = runner or NoRemoteRunner()
    prepared = operations.prepare_setting(
        root, base_id, operation, reason, path=path, value=value, runner=runner
    )
    return prepared, operations.approve(
        root, base_id, prepared.prepared_id, prepared.shown, runner=runner, now=NOW
    )


class TestTheBaseOwnerRole(unittest.TestCase):
    """CS16: the map's owner line passes only by the current base owner's approval."""

    def test_the_base_owner_passes_it_previewed_approved_and_recorded(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, OWNER)
            prepared, done = set_it(
                root, base_id, operations.SET_MAP_OWNER, ADMIN, reason="Leaving in May."
            )
            self.assertIn("owner: %s" % ADMIN, prepared.artifact)
            self.assertTrue(done.done, done.sentence)
            self.assertEqual(
                ADMIN,
                authority.roles_from_map(
                    support.read(os.path.join(root, constants.MAP_PATH))
                ).base_owner,
            )
            record = the_newest_record(root)
            import test_authority_everywhere as everywhere

            self.assertEqual(OWNER, everywhere.author_of_newest_record(root)[0])
            self.assertEqual({constants.MAP_PATH: authority.ROLE_BASE_OWNER}, record.approved_roles)
            self.assertIn("Leaving in May.", record.why)

    def test_an_administrator_or_anybody_else_is_refused_and_nothing_is_written(self):
        for address in (ADMIN, WRITER, STRANGER):
            with self.subTest(address=address), support.Sandbox() as sandbox:
                root, base_id = a_base(sandbox)
                as_address(root, address)
                before, before_head = snapshot(root), head(root)
                _prepared, done = set_it(root, base_id, operations.SET_MAP_OWNER, address)
                self.assertFalse(done.done)
                self.assertEqual(before, snapshot(root))
                self.assertEqual(before_head, head(root))

    def test_removing_the_maps_owner_line_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            for value in ("", "[]", "[%s, %s]" % (OWNER, ADMIN)):
                with self.subTest(value=value):
                    with self.assertRaises(operations.Refused):
                        operations.prepare_setting(
                            root, base_id, operations.SET_MAP_OWNER, "x", value=value,
                            runner=NoRemoteRunner(),
                        )


class TestTheAdministrators(unittest.TestCase):
    """CS17: the administrators line changes only by the base owner's approval."""

    def test_an_administrator_setting_it_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, ADMIN)
            _prepared, done = set_it(root, base_id, operations.SET_ADMINISTRATORS, [ADMIN, STRANGER])
            self.assertFalse(done.done)

    def test_the_base_owner_doing_it_is_accepted(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, OWNER)
            _prepared, done = set_it(root, base_id, operations.SET_ADMINISTRATORS, [ADMIN, WRITER])
            self.assertTrue(done.done, done.sentence)
            roles = authority.roles_from_map(support.read(os.path.join(root, constants.MAP_PATH)))
            self.assertEqual([ADMIN, WRITER], roles.administrators)

    def test_emptying_it_is_allowed(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, OWNER)
            _prepared, done = set_it(root, base_id, operations.SET_ADMINISTRATORS, [])
            self.assertTrue(done.done, done.sentence)

    def test_a_value_that_is_not_addresses_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_ADMINISTRATORS, "x", value=["everyone"],
                    runner=NoRemoteRunner(),
                )


class TestTheBusinesses(unittest.TestCase):
    """CS17: the map's businesses by the base owner or an administrator."""

    def test_an_administrator_sets_them(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, ADMIN)
            prepared, done = set_it(
                root, base_id, operations.SET_BUSINESSES,
                "insights (Acme Insights), courier-app (the courier app), wholesale",
            )
            self.assertTrue(done.done, done.sentence)
            self.assertEqual({constants.MAP_PATH: authority.ROLE_ADMINISTRATOR},
                             the_newest_record(root).approved_roles)

    def test_anybody_else_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            _prepared, done = set_it(root, base_id, operations.SET_BUSINESSES, "insights")
            self.assertFalse(done.done)

    def test_a_list_that_cannot_be_read_is_refused_before_it_is_shown(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_BUSINESSES, "x", value="Courier App!",
                    runner=NoRemoteRunner(),
                )


class TestADocumentsBusinessLine(unittest.TestCase):
    """CS17: by the document's authority set, to a business the map lists."""

    def test_its_owner_sets_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            prepared, done = set_it(root, base_id, operations.SET_BUSINESS, "insights", path=POSITIONING)
            self.assertTrue(done.done, done.sentence)
            text = support.read(os.path.join(root, POSITIONING))
            self.assertIn("business: insights", text)
            # Only that line changed: the body and every other setting are as they were.
            self.assertTrue(text.endswith("# Positioning\n\nWords.\n"))
            self.assertIn("owner: %s" % WRITER, text)

    def test_somebody_outside_its_authority_set_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, STRANGER)
            _prepared, done = set_it(root, base_id, operations.SET_BUSINESS, "insights", path=POSITIONING)
            self.assertFalse(done.done)

    def test_a_business_the_map_does_not_list_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            for value in ("wholesale", "Courier App!", ""):
                with self.subTest(value=value):
                    with self.assertRaises(operations.Refused):
                        operations.prepare_setting(
                            root, base_id, operations.SET_BUSINESS, "x", path=POSITIONING,
                            value=value, runner=NoRemoteRunner(),
                        )

    def test_whole_company_is_a_business_line_too(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            _prepared, done = set_it(
                root, base_id, operations.SET_BUSINESS, "whole-company", path=POSITIONING
            )
            self.assertTrue(done.done, done.sentence)


class TestADocumentsOwnerLine(unittest.TestCase):
    """CS15: by the document's authority set, recorded with the reason."""

    def test_passed_on_by_its_owner(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            _prepared, done = set_it(
                root, base_id, operations.SET_OWNER, STRANGER, path=POSITIONING,
                reason="They run positioning now.",
            )
            self.assertTrue(done.done, done.sentence)
            self.assertIn("owner: %s" % STRANGER, support.read(os.path.join(root, POSITIONING)))
            self.assertIn("They run positioning now.", the_newest_record(root).why)

    def test_or_by_an_administrator_and_never_by_anybody_else(self):
        for address, allowed in ((ADMIN, True), (OWNER, True), (STRANGER, False)):
            with self.subTest(address=address), support.Sandbox() as sandbox:
                root, base_id = a_base(sandbox)
                as_address(root, address)
                _prepared, done = set_it(root, base_id, operations.SET_OWNER, STRANGER, path=POSITIONING)
                self.assertEqual(allowed, done.done, done.sentence)


class TestNothingElseCanBeChanged(unittest.TestCase):
    """Security: no other settings change is possible through these operations."""

    def test_an_operation_that_is_not_one_of_the_five_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            for operation in ("status", "kind", "sources", "confirmation_threshold_days"):
                with self.subTest(operation=operation):
                    with self.assertRaises(operations.Refused):
                        operations.prepare_setting(
                            root, base_id, operation, "x", path=POSITIONING, value="done",
                            runner=NoRemoteRunner(),
                        )

    def test_a_document_operation_never_reaches_the_map_and_the_other_way(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_OWNER, "x", path=constants.MAP_PATH,
                    value=STRANGER, runner=NoRemoteRunner(),
                )
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_MAP_OWNER, "x", path=POSITIONING,
                    value=STRANGER, runner=NoRemoteRunner(),
                )

    def test_a_value_carrying_a_second_setting_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            for value in ("%s\nstatus: done" % STRANGER, "%s status: done" % STRANGER):
                with self.subTest(value=value):
                    with self.assertRaises(operations.Refused):
                        operations.prepare_setting(
                            root, base_id, operations.SET_OWNER, "x", path=POSITIONING,
                            value=value, runner=NoRemoteRunner(),
                        )

    def test_the_file_changed_after_it_was_shown_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            prepared = operations.prepare_setting(
                root, base_id, operations.SET_BUSINESS, "x", path=POSITIONING,
                value="insights", runner=NoRemoteRunner(),
            )
            path = os.path.join(root, POSITIONING)
            support.write(path, support.read(path).replace("Words.", "Other words."))
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "edited"], cwd=root)
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=NOW,
            )
            self.assertFalse(done.done)
            self.assertNotIn("business:", support.read(path))

    def test_a_prepared_operation_is_used_once(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            prepared, done = set_it(root, base_id, operations.SET_BUSINESS, "insights", path=POSITIONING)
            self.assertTrue(done.done)
            again = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=NOW,
            )
            self.assertFalse(again.done)

    def test_unsaved_work_anywhere_in_the_base_stops_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base(sandbox)
            as_address(root, WRITER)
            prepared = operations.prepare_setting(
                root, base_id, operations.SET_BUSINESS, "x", path=POSITIONING,
                value="insights", runner=NoRemoteRunner(),
            )
            support.write(os.path.join(root, "context", "notes.md"), "half done\n")
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown,
                runner=NoRemoteRunner(), now=NOW,
            )
            self.assertFalse(done.done)


if __name__ == "__main__":
    unittest.main()
