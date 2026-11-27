"""Unit 4.2a of Plan 1: approval, confirmation, the stale computation and the
moment of use all ask the one authority rule.

The signed company-skills requirements, CS3, CS4 and CS9. A change may be
approved, and a document confirmed, only by its owners, the base owner, or an
administrator, judged from the saved versions of the document and the map at
that moment; every approval records who approved it, in which role, and a
hash of the exact bytes approved.

The proof that a person answered Claude Code's own question is Release B's
(Unit 1.7e) and is held by the suite the way every other approval test holds
it; tests/test_approval_ask.py proves it unheld. Every fixture is written from
scratch and every address is made up.
"""

import os
import unittest

import support
import test_approve_local as approving

from gtmbase import (
    approve_local,
    authority,
    base_reader,
    confirm,
    constants,
    formats,
    moment,
    stale,
)

TODAY = approving.TODAY
NOW = approving.NOW
ICP = approving.ICP
OWNER = approving.OWNER
WRITER = "writer@example.com"
ADMIN = "admin@example.com"
STRANGER = "stranger@example.com"
NoRemoteRunner = support.NoRemoteRunner


def with_roles(root, administrators=(ADMIN,), document_owner=WRITER):
    """The map names its owner and an administrator; the profile has its own owner."""
    map_path = os.path.join(root, constants.MAP_PATH)
    text = support.read(map_path)
    text = text.replace(
        "owner: %s\n" % OWNER,
        "owner: %s\nadministrators: [%s]\n" % (OWNER, ", ".join(administrators)),
        1,
    )
    support.write(map_path, text)
    icp = os.path.join(root, ICP)
    support.write(
        icp, support.read(icp).replace("owner: %s" % OWNER, "owner: %s" % document_owner, 1)
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "roles"], cwd=root)


def seat_address(root, address):
    support.git(["config", "--local", "user.email", address], cwd=root)


def author_of_newest_record(root):
    """Who saved the newest record of corrections, which is who approved it.

    The address is never written into the record (an address in it would be
    refused by the check before a send unless it is the base owner's), so the
    saved history says who, as it always has for a confirmation line.
    """
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    names = sorted(name for name in os.listdir(folder) if name.endswith(".md"))
    relative = constants.CORRECTIONS_DIR + "/" + names[-1]
    shown = support.git(["log", "-1", "--format=%ae", "--", relative], cwd=root)
    return shown.stdout.decode("utf-8").strip(), support.read(os.path.join(root, relative))


def the_record(root):
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    names = sorted(name for name in os.listdir(folder) if name.endswith(".md"))
    return formats.CorrectionsFile.parse(support.read(os.path.join(folder, names[-1])))


class TestEachRoleMayApproveAndIsRecorded(unittest.TestCase):
    """Happy path: the owner, the base owner and an administrator each approve."""

    def test_each_role(self):
        for address, role in (
            (WRITER, authority.ROLE_OWNER),
            (OWNER, authority.ROLE_BASE_OWNER),
            (ADMIN, authority.ROLE_ADMINISTRATOR),
        ):
            with self.subTest(role=role), support.Sandbox() as sandbox:
                root, base_id = approving.local_base(sandbox)
                with_roles(root)
                staged = approving.stage(root)
                seat_address(root, address)
                shown, applied = approving.show_and_approve(
                    root, base_id, staged, NoRemoteRunner()
                )
                self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
                record = the_record(root)
                saved_by, text = author_of_newest_record(root)
                self.assertEqual(address, saved_by)
                if address != OWNER:
                    self.assertNotIn(address, text)
                self.assertEqual({ICP: role}, record.approved_roles)
                self.assertEqual(
                    {ICP: authority.file_hash(root, ICP)}, record.approved_hashes
                )
                # The approval is also that address saying the document is
                # right, recorded with who and in which role (CS9).
                line = approving.confirmations_of(root)[-1]
                self.assertEqual(role, line.role)
                self.assertNotIn("@", line.render())

    def test_a_record_written_before_this_unit_still_reads(self):
        text = support.read(
            os.path.join(support.TEMPLATES_DIR, "corrections-file.md")
        )
        record = formats.CorrectionsFile.parse(text)
        self.assertEqual({}, record.approved_roles)
        self.assertEqual({}, record.approved_hashes)
        self.assertEqual(text, record.render())


class TestNobodyElse(unittest.TestCase):
    """Security: an address outside the authority set is refused, by name."""

    def test_refused_naming_the_document_and_who_may(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            staged = approving.stage(root)
            seat_address(root, STRANGER)
            shown = approve_local.show(staged, root, base_id, runner=NoRemoteRunner(), now=TODAY)
            self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], shown.codes)
            for named in (WRITER, OWNER, ADMIN):
                self.assertIn(named, shown.reasons[0])

    def test_an_unsaved_edit_making_oneself_an_administrator_grants_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            staged = approving.stage(root)
            map_path = os.path.join(root, constants.MAP_PATH)
            support.write(
                map_path,
                support.read(map_path).replace(
                    "administrators: [%s]" % ADMIN, "administrators: [%s]" % STRANGER
                ),
            )
            seat_address(root, STRANGER)
            shown = approve_local.show(staged, root, base_id, runner=NoRemoteRunner(), now=TODAY)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], shown.codes)

    def test_a_document_with_no_owner_is_still_the_base_owners_to_approve(self):
        """CS3 replaces the rule that a document with no owner line had nobody."""
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root, document_owner="[]")
            staged = approving.stage(root)
            seat_address(root, STRANGER)
            shown = approve_local.show(staged, root, base_id, runner=NoRemoteRunner(), now=TODAY)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], shown.codes)
            seat_address(root, OWNER)
            _shown, applied = approving.show_and_approve(root, base_id, staged, NoRemoteRunner())
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status)
            self.assertEqual({ICP: authority.ROLE_BASE_OWNER}, the_record(root).approved_roles)


ENTRY = "stg-" + "e" * 16


def a_change_about_the_profile(root, author=OWNER):
    entry = os.path.join(root, constants.CHANGES_DIR, ENTRY + ".md")
    support.write(
        entry,
        "\n".join(
            [
                "---",
                "id: %s" % ENTRY,
                "kind: change",
                "happened_on: 2026-06-01",
                "written_on: 2026-06-01",
                "noted_by: %s" % OWNER,
                "source: the weekly meeting",
                "affects: [%s]" % ICP,
                "review_by: 2026-09-01",
                "origin: ledger",
                "status: open",
                "---",
                "",
                "We now sell to bigger companies.",
                "",
            ]
        ),
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a change"], cwd=root, author=author)


def a_confirmation_line(root, author, day="2026-06-02", entry=ENTRY):
    """One confirmation line, saved under the address of whoever gave it."""
    path = os.path.join(root, confirm.confirmations_path_for(ICP))
    line = (
        "date=%s time=09:00:00Z file=%s trigger=ledger entry=%s question=- run=-\n"
        % (day, ICP, entry)
    )
    existing = support.read(path) if os.path.exists(path) else ""
    support.write(path, existing + line)
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "a confirmation"], cwd=root, author=author)


def flagged(root, base_id):
    inputs = base_reader.read_base(root, base_id, today=TODAY, record_dropped=False)
    report = stale.compute(
        today=TODAY,
        settings=inputs.settings,
        files=inputs.files,
        ledger=inputs.ledger,
        confirmations=inputs.confirmations,
        corrections=inputs.corrections,
        seat=inputs.seat,
    )
    return [flag.path for flag in report.file_flags if flag.trigger == stale.TRIGGER_LEDGER]


class TestAnAdministratorsConfirmationCounts(unittest.TestCase):
    """Integration: through `stale.compute` and `moment.check`."""

    def test_it_settles_the_change_and_clears_the_flag(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            self.assertEqual([ICP], flagged(root, base_id))
            self.assertTrue(
                moment.check(root, base_id, ICP, runner=NoRemoteRunner(), now=TODAY).flagged
            )
            a_confirmation_line(root, ADMIN)
            self.assertEqual([], flagged(root, base_id))
            self.assertFalse(
                moment.check(root, base_id, ICP, runner=NoRemoteRunner(), now=TODAY).flagged
            )

    def test_a_strangers_line_settles_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            a_confirmation_line(root, STRANGER)
            self.assertEqual([ICP], flagged(root, base_id))

    def test_the_confirm_step_takes_an_administrators_yes(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            for address, refused in ((STRANGER, True), (ADMIN, False)):
                with self.subTest(address=address):
                    seat_address(root, address)
                    result = confirm.against_change(
                        root, base_id, ICP, ENTRY, now=NOW, runner=NoRemoteRunner()
                    )
                    self.assertEqual(refused, result.refused, result.reasons)
            self.assertEqual([], flagged(root, base_id))

    def test_the_line_records_who_confirmed_and_in_which_role(self):
        """CS9: a confirmation is recorded with the address and the role."""
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            seat_address(root, ADMIN)
            result = confirm.against_change(
                root, base_id, ICP, ENTRY, now=NOW, runner=NoRemoteRunner()
            )
            self.assertFalse(result.refused, result.reasons)
            self.assertEqual(authority.ROLE_ADMINISTRATOR, result.line.role)
            self.assertNotIn(ADMIN, result.line.render())
            lines = approving.confirmations_of(root)
            self.assertEqual(authority.ROLE_ADMINISTRATOR, lines[-1].role)

    def test_a_line_written_before_this_unit_has_no_role_and_still_reads(self):
        line = formats.ConfirmationLine.parse(
            "date=2026-06-02 time=09:00:00Z file=%s trigger=ledger entry=%s "
            "question=- run=-" % (ICP, ENTRY)
        )
        self.assertIsNone(line.role)
        self.assertNotIn("role=", line.render())


class TestWhenADocumentChangesHands(unittest.TestCase):
    """Integration: a confirmation counts as authority stood when it was given."""

    def pass_the_profile(self, root, to):
        icp = os.path.join(root, ICP)
        support.write(icp, support.read(icp).replace("owner: %s" % WRITER, "owner: %s" % to))
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "passed on"], cwd=root)

    def test_before_the_transfer_counts_and_after_does_not(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root, administrators=())
            a_change_about_the_profile(root)
            a_confirmation_line(root, WRITER)
            self.pass_the_profile(root, STRANGER)
            self.assertEqual([], flagged(root, base_id))

        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root, administrators=())
            a_change_about_the_profile(root)
            self.pass_the_profile(root, STRANGER)
            a_confirmation_line(root, WRITER)
            self.assertEqual([ICP], flagged(root, base_id))


class TestAnAdministratorRemoved(unittest.TestCase):
    """Integration: no longer approves or confirms; what they did before stands."""

    def remove_administrators(self, root):
        map_path = os.path.join(root, constants.MAP_PATH)
        support.write(
            map_path,
            support.read(map_path).replace("administrators: [%s]" % ADMIN, "administrators: []"),
        )
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "no administrators"], cwd=root)

    def test_their_earlier_confirmation_still_counts(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            a_confirmation_line(root, ADMIN)
            self.remove_administrators(root)
            self.assertEqual([], flagged(root, base_id))

    def test_a_later_confirmation_counts_for_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            self.remove_administrators(root)
            a_confirmation_line(root, ADMIN)
            self.assertEqual([ICP], flagged(root, base_id))

    def test_they_can_no_longer_approve(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            self.remove_administrators(root)
            staged = approving.stage(root)
            seat_address(root, ADMIN)
            shown = approve_local.show(staged, root, base_id, runner=NoRemoteRunner(), now=TODAY)
            self.assertEqual([approve_local.CODE_NOT_AN_OWNER], shown.codes)

    def test_an_approval_they_made_while_they_held_the_role_stays_a_confirmation(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            staged = approving.stage(root)
            seat_address(root, ADMIN)
            _shown, applied = approving.show_and_approve(root, base_id, staged, NoRemoteRunner())
            self.assertEqual(approve_local.STATUS_APPLIED, applied.status)
            seat_address(root, OWNER)
            self.remove_administrators(root)
            inputs = base_reader.read_base(root, base_id, today=TODAY, record_dropped=False)
            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
            )
            # The approval still counts as their yes about the document.
            self.assertIsNotNone(report.confirmed_on.get(ICP))
            self.assertNotIn(
                ICP,
                [flag.path for flag in report.file_flags if flag.trigger == stale.TRIGGER_LEDGER],
            )


class TestTheReviewAsksEveryoneWhoMayAnswer(unittest.TestCase):
    """The review and the flag ask an address in the authority set, not only owners."""

    def test_an_administrator_is_asked_about_a_document_someone_else_owns(self):
        with support.Sandbox() as sandbox:
            root, base_id = approving.local_base(sandbox)
            with_roles(root)
            a_change_about_the_profile(root)
            seat_address(root, ADMIN)
            found = moment.check(root, base_id, ICP, runner=NoRemoteRunner(), now=TODAY)
            self.assertTrue(found.flagged)
            self.assertTrue(found.owned)
            seat_address(root, STRANGER)
            found = moment.check(root, base_id, ICP, runner=NoRemoteRunner(), now=TODAY)
            self.assertFalse(found.owned)


if __name__ == "__main__":
    unittest.main()
