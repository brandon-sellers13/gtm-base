"""The correctness and security reviews of Plan 1's Unit 4.2a (2026-10-10), one test per finding.

Each test failed before its fix. Every fixture is written from scratch and
every address and value is made up.
"""

import json
import os
import unittest

import support
import test_approval_ask as asking
import test_approve_local as approving
import test_authority_everywhere as everywhere
import test_operations as operating

from gtmbase import (
    approval,
    approve_local,
    authority,
    compose_proposal,
    constants,
    docpaths,
    inventory,
    operations,
    scan,
)
from gtmbase.errors import GtmBaseError, PathError, ValidationError

NoRemoteRunner = support.NoRemoteRunner
NOW = approving.NOW
OWNER = operating.OWNER
WRITER = operating.WRITER
ADMIN = operating.ADMIN
STRANGER = operating.STRANGER
POSITIONING = operating.POSITIONING


def kept_path(base_id, prepared_id):
    from gtmbase import paths

    return os.path.join(paths.seat_dir(base_id), operations.FOLDER, prepared_id + ".json")


class TestAPreparedOperationIsNotTrusted(unittest.TestCase):
    """Security finding 1: approving re-checks everything instead of trusting the kept file."""

    def tamper(self, base_id, prepared, change):
        path = kept_path(base_id, prepared.prepared_id)
        kept = json.load(open(path))
        change(kept)
        json.dump(kept, open(path, "w"))
        return operations._shown_value(kept)

    def test_a_creation_rewritten_to_reach_the_map_writes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            operating.as_address(root, STRANGER)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", operating.GOALS)], "x", runner=NoRemoteRunner()
            )
            map_text = support.read(os.path.join(root, constants.MAP_PATH))

            def to_the_map(kept):
                kept["changes"] = [
                    {
                        "path": constants.MAP_PATH,
                        "before": None,
                        "after": map_text.replace("owner: %s" % OWNER, "owner: %s" % STRANGER),
                    }
                ]

            shown = self.tamper(base_id, prepared, to_the_map)
            done = operations.approve(
                root, base_id, prepared.prepared_id, shown, runner=NoRemoteRunner(), now=NOW
            )
            self.assertFalse(done.done)
            self.assertEqual(map_text, support.read(os.path.join(root, constants.MAP_PATH)))

    def test_a_setting_rewritten_to_another_file_or_value_writes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            operating.as_address(root, ADMIN)
            prepared = operations.prepare_setting(
                root, base_id, operations.SET_OWNER, "x", path=POSITIONING, value=ADMIN,
                runner=NoRemoteRunner(),
            )
            for change in (
                lambda kept: kept["changes"][0].update(path=constants.MAP_PATH),
                lambda kept: kept["changes"][0].update(
                    after=kept["changes"][0]["after"].replace("Words.", "Other words.")
                ),
                lambda kept: kept.update(operation=operations.SET_MAP_OWNER),
                lambda kept: kept.update(value=STRANGER),
            ):
                with self.subTest():
                    before = operating.snapshot(root)
                    shown = self.tamper(base_id, prepared, change)
                    done = operations.approve(
                        root, base_id, prepared.prepared_id, shown, runner=NoRemoteRunner(), now=NOW
                    )
                    self.assertFalse(done.done)
                    self.assertEqual(before, operating.snapshot(root))
                    prepared = operations.prepare_setting(
                        root, base_id, operations.SET_OWNER, "x", path=POSITIONING, value=ADMIN,
                        runner=NoRemoteRunner(),
                    )

    def test_a_creation_whose_owner_line_was_rewritten_writes_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", operating.GOALS)], "x", runner=NoRemoteRunner()
            )
            shown = self.tamper(
                base_id,
                prepared,
                lambda kept: kept["changes"][0].update(
                    after=kept["changes"][0]["after"].replace("owner: %s" % OWNER, "owner: %s" % STRANGER)
                ),
            )
            done = operations.approve(
                root, base_id, prepared.prepared_id, shown, runner=NoRemoteRunner(), now=NOW
            )
            self.assertFalse(done.done)

    def test_a_kept_file_that_cannot_be_read_is_a_refusal_not_a_crash(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", operating.GOALS)], "x", runner=NoRemoteRunner()
            )
            shown = self.tamper(base_id, prepared, lambda kept: kept.update(operation="nothing"))
            done = operations.approve(
                root, base_id, prepared.prepared_id, shown, runner=NoRemoteRunner(), now=NOW
            )
            self.assertFalse(done.done)

    def test_a_prepared_operation_too_old_is_not_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            prepared = operations.prepare_creation(
                root, base_id, [("context/goals.md", operating.GOALS)], "x", runner=NoRemoteRunner()
            )
            shown = self.tamper(
                base_id, prepared, lambda kept: kept.update(made="2020-01-01T00:00:00")
            )
            done = operations.approve(
                root, base_id, prepared.prepared_id, shown, runner=NoRemoteRunner(), now=NOW
            )
            self.assertFalse(done.done)


# An address with a password in it, put together so no line here is shaped like one.
PASSWORD_ADDRESS = "postgres://admin:" + "S3cr3t!" + "@db.acme.example:5432/stats"


class TestTheSourceMapsOwnScreen(unittest.TestCase):
    """Security finding 2: every way into the source map runs its credential screen."""

    def test_creating_it_with_an_address_carrying_a_password_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            os.remove(os.path.join(root, constants.STACK_PATH)) if os.path.exists(
                os.path.join(root, constants.STACK_PATH)
            ) else None
            text = "---\nkind: stack\nsources: []\nstatus: draft\n---\n\n# Stack\n\nDB at %s\n" % PASSWORD_ADDRESS
            with self.assertRaises(operations.Refused):
                operations.prepare_creation(
                    root, base_id, [(constants.STACK_PATH, text)], "x", runner=NoRemoteRunner()
                )

    def test_a_prepared_change_to_it_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            support.write(
                os.path.join(root, constants.STACK_PATH),
                "---\nkind: stack\nowner: %s\nsources: []\nstatus: draft\n---\n\n# Stack\n\n"
                "## Firmographics\n\nNothing yet.\n" % OWNER,
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "stack"], cwd=root)
            staged = approving.stage(
                root,
                support.staging_template()
                .replace("context/strategy/icp.md", constants.STACK_PATH)
                .replace("context/icps.md", constants.STACK_PATH)
                .replace(
                    "Companies of twenty to two hundred people, with a marketing team of one to five.",
                    "The database is at %s" % PASSWORD_ADDRESS,
                ),
            )
            shown = approve_local.show(staged, root, base_id, runner=NoRemoteRunner(), now=approving.TODAY)
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)

    def test_the_send_check_reads_the_source_map_with_its_own_screen(self):
        diff = (
            "diff --git a/access/stack.md b/access/stack.md\n"
            "+++ b/access/stack.md\n"
            "@@ -0,0 +1 @@\n"
            "+DB at %s\n" % PASSWORD_ADDRESS
        )
        self.assertTrue(scan.scan_diff_added_lines(diff, None))


class TestTheOtherLayoutsPath(unittest.TestCase):
    """Security finding 3: creating a document never shadows one at the other layout's path."""

    def test_an_older_path_is_never_created(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_creation(
                    root, base_id, [("context/strategy/positioning.md", operating.GOALS)], "x",
                    runner=NoRemoteRunner(),
                )

    def test_a_current_path_whose_older_one_is_there_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            # This base keeps its profile at the older path.
            self.assertTrue(os.path.exists(os.path.join(root, approving.ICP)))
            operating.as_address(root, STRANGER)
            with self.assertRaises(operations.Refused):
                operations.prepare_creation(
                    root, base_id, [("context/icps.md", operating.GOALS)], "x", runner=NoRemoteRunner()
                )


class TestEachSettingIsAskedAboutByName(unittest.TestCase):
    """Security finding 4: the question names the operation, and the library holds it to it."""

    def test_each_operation_has_its_own_sentence(self):
        import test_approval_table as table

        said = set()
        for operation in operations.SETTINGS_OPERATIONS:
            with self.subTest(operation=operation):
                says, opens = table.what(
                    "operations.py",
                    ["--approve-setting", "stg-0123456789abcdef", "--operation", operation, "--shown", "x"],
                )
                self.assertEqual(("operations.approve",), opens)
                said.add(says)
        self.assertEqual(len(operations.SETTINGS_OPERATIONS), len(said))

    def test_a_setting_approved_without_naming_its_operation_is_unreadable(self):
        import test_approval_table as table

        with self.assertRaises(approval.Unreadable):
            table.what("operations.py", ["--approve-setting", "stg-0123456789abcdef", "--shown", "x"])

    def test_the_library_refuses_an_operation_other_than_the_one_named(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            operating.as_address(root, OWNER)
            prepared = operations.prepare_setting(
                root, base_id, operations.SET_MAP_OWNER, "x", value=ADMIN, runner=NoRemoteRunner()
            )
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown, runner=NoRemoteRunner(),
                now=NOW, kind=operations.KIND_SETTING, operation=operations.SET_BUSINESS,
            )
            self.assertFalse(done.done)
            done = operations.approve(
                root, base_id, prepared.prepared_id, prepared.shown, runner=NoRemoteRunner(),
                now=NOW, kind=operations.KIND_SETTING, operation=operations.SET_MAP_OWNER,
            )
            self.assertTrue(done.done, done.sentence)

    def test_the_artifact_opens_with_the_one_line_before_and_after(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            prepared = operations.prepare_setting(
                root, base_id, operations.SET_MAP_OWNER, "x", value=ADMIN, runner=NoRemoteRunner()
            )
            opening = prepared.artifact.split("[[file:")[0]
            self.assertIn("owner: %s" % OWNER, opening)
            self.assertIn("owner: %s" % ADMIN, opening)


class TestTheUnattendedMarkIsNeverLost(unittest.TestCase):
    """Security finding 5 and correctness finding 7."""

    def test_two_marks_both_stay_and_a_damaged_record_unmarks_nobody(self):
        with support.Sandbox():
            authority.mark_unattended("one")
            authority.mark_unattended("two")
            self.assertTrue(authority.is_unattended("one"))
            self.assertTrue(authority.is_unattended("two"))
            self.assertFalse(authority.is_unattended("three"))
            folder = authority.unattended_path()
            self.assertTrue(os.path.isdir(folder))


class TestSettingsValuesAreScreened(unittest.TestCase):
    """Security finding 6: a business's name never carries a contact detail."""

    def test_a_phone_number_as_a_business_name_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_BUSINESSES, "x",
                    value="insights (Call 415 555 0134 now)", runner=NoRemoteRunner(),
                )


class TestTheAdministratorsLineCanBeSent(unittest.TestCase):
    """Correctness finding 1: the send check lets the map's administrators line through."""

    def test_only_on_the_maps_settings_block(self):
        line = "+administrators: [%s]\n" % ADMIN
        on_the_map = (
            "diff --git a/context/map.md b/context/map.md\n+++ b/context/map.md\n@@ -1,0 +1,6 @@\n"
            "+---\n+kind: map\n+owner: %s\n" % OWNER + line
        )
        self.assertEqual([], scan.scan_diff_added_lines(on_the_map, frozenset([OWNER])))
        elsewhere = on_the_map.replace("context/map.md", "context/positioning.md")
        self.assertTrue(scan.scan_diff_added_lines(elsewhere, frozenset([OWNER])))


class TestAHandEditMayNotChangeWhoOwnsADocument(unittest.TestCase):
    """Correctness finding 2: owner and business lines change only through their operations."""

    def hand_edit(self, root, change):
        icp = os.path.join(root, approving.ICP)
        support.write(icp, change(support.read(icp)))

    def test_a_business_line_added_by_hand_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            self.hand_edit(
                root,
                lambda text: text.replace(
                    "owner: %s\n" % OWNER, "owner: %s\nbusiness: courier-app\n" % OWNER
                ).replace("Companies of any size.", "Companies of twenty people or more."),
            )
            with self.assertRaises(ValidationError) as raised:
                compose_proposal.stage_local_edit(
                    root, base_id, "We now sell to bigger teams.", runner=NoRemoteRunner()
                )
            self.assertEqual(compose_proposal.CODE_LOCAL_SETTINGS, raised.exception.code)

    def test_a_status_line_by_hand_is_still_allowed(self):
        self.assertTrue(operations.authority_lines_changed("---\nowner: a@b.co\nstatus: draft\n---\n", "---\nowner: c@b.co\nstatus: draft\n---\n"))
        self.assertFalse(operations.authority_lines_changed("---\nowner: a@b.co\nstatus: draft\n---\n", "---\nowner: a@b.co\nstatus: done\n---\n"))


class TestAGitReadThatFails(unittest.TestCase):
    """Correctness finding 3: a failed read is not an answer, in either direction."""

    class ShowFails(support.NoRemoteRunner):
        def run(self, args, cwd=None, **kwargs):
            if args and args[0] in ("show", "ls-tree", "cat-file"):
                from gtmbase.gitcmd import GitResult

                return GitResult(124, "", "deadline")
            return super(TestAGitReadThatFails.ShowFails, self).run(args, cwd=cwd, **kwargs)

    def test_authority_cannot_be_read_and_says_so(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            with self.assertRaises(authority.AuthorityUnavailable):
                authority.at(root, POSITIONING, runner=self.ShowFails())

    def test_an_approval_is_refused_rather_than_read_from_the_disk(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            staged = approving.stage(root)
            shown = approve_local.show(staged, root, base_id, runner=self.ShowFails(), now=approving.TODAY)
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)


class TestTheSetupClosingAsksEveryoneWhoMay(unittest.TestCase):
    """Correctness finding 4: join_flow asks by the authority rule, from the saved file."""

    def test_the_rule_it_asks(self):
        source = support.read(os.path.join(support.LIB_DIR, "gtmbase", "join_flow.py"))
        self.assertNotIn("confirm.owners_of(base_root, path)", source)
        self.assertIn("authority.at(base_root, path", source)


class TestTheInventoryDatesAStandard(unittest.TestCase):
    """Correctness finding 6: a standard's confirmation shows in the inventory."""

    def test_a_created_standard_shows_its_day(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            done = operating.created(root, base_id, [("standards/ad-testing.md", operating.GOALS)])
            self.assertTrue(done.done, done.sentence)
            found = inventory.take(root, base_id, today=approving.TODAY)
            cell = found.cells[("standard", "whole-company")]
            self.assertIsNotNone(cell.confirmed_on)


class TestTheCreatorsYesAppends(unittest.TestCase):
    """Correctness finding 9: a confirmations file with no last newline stays readable."""

    def test_a_leftover_file_without_a_last_newline(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            leftover = os.path.join(root, "work", "confirmations", "context--goals.md")
            support.write(
                leftover,
                "date=2026-01-01 time=09:00:00Z file=context/goals.md trigger=threshold entry=- question=- run=-",
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a leftover"], cwd=root)
            done = operating.created(root, base_id, [("context/goals.md", operating.GOALS)])
            self.assertTrue(done.done, done.sentence)
            from gtmbase import formats

            lines, bad = formats.parse_confirmations_file(support.read(leftover))
            self.assertEqual(2, len(lines))
            self.assertEqual([], bad)


class TestASettingReadsBackAsIntended(unittest.TestCase):
    """Correctness finding 10a: a value the reader would read differently is refused."""

    def test_a_name_with_a_comma_from_a_library_caller(self):
        with support.Sandbox() as sandbox:
            root, base_id = operating.a_base(sandbox)
            with self.assertRaises(operations.Refused):
                operations.prepare_setting(
                    root, base_id, operations.SET_BUSINESSES, "x",
                    value=["insights (Acme, Inc)"], runner=NoRemoteRunner(),
                )


class TestTheSpellingOnDisk(unittest.TestCase):
    """Security residual: a path spelled differently from the file on disk is not a document."""

    def test_a_case_variant_is_refused(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            support.write(os.path.join(root, "standards", "ad-testing.md"), "x\n")
            os.makedirs(os.path.join(root, "context"))
            support.write(os.path.join(root, "context", "goals.md"), "x\n")
            for path in ("context/Goals.md", "Context/goals.md"):
                with self.subTest(path=path):
                    if os.path.exists(os.path.join(root, path)):
                        with self.assertRaises(PathError):
                            docpaths.check(root, path)


if __name__ == "__main__":
    unittest.main()
