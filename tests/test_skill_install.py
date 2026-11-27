"""Plan 1, Unit 4.2b: installing a skill, changing one, and accepting one here.

The signed company-skills requirements CS6, CS7, CS9 to CS11, CS22, CS26 and
CS30. A skill reaches a base's skills folder only through these operations:
installing needs the contract check passing and two yeses (the creator's,
and the base owner's or an administrator's), writes the whole folder or
nothing, records one approval of the whole manifest, and trusts it here.
Accepting trusts a version somebody with authority approved, after showing
who, in which role and what changed, and a version nobody approved cannot be
accepted. Every fixture is written from scratch; the addresses are made up.
"""

import datetime
import os
import unittest
from unittest import mock

import support
import test_runner_contract as contract

from gtmbase import approval, authority, constants, formats, runner, skill_install

OWNER = "owner@example.com"
WRITER = "writer@example.com"
ADMIN = "admin@example.com"
STRANGER = "stranger@example.com"
SKILL = contract.SKILL
SKILL_MD = contract.SKILL_MD
NOW = datetime.datetime(2026, 6, 15, 9, 0, 0)


def the_skill_files():
    files = contract.the_skill()
    for name, text in contract.example_files().items():
        files[contract.EXAMPLE + name] = text
    return files


def seat_address(root, address):
    support.git(["config", "--local", "user.email", address], cwd=root)


def a_base_without_the_skill(sandbox, administrators=None):
    root, base_id = support.skill_base(
        sandbox, documents=contract.the_documents(), files={}, trust=False
    )
    if administrators is not None:
        map_path = os.path.join(root, constants.MAP_PATH)
        text = support.read(map_path).replace(
            "owner: owner@example.com\n",
            "owner: owner@example.com\nadministrators: [%s]\n" % ", ".join(administrators),
            1,
        )
        support.write(map_path, text)
        support.git(["add", "-A"], cwd=root)
        support.git(["commit", "-q", "-m", "administrators"], cwd=root)
    return root, base_id


def prepare(root, base_id, files=None, reason="We run this readout every week."):
    return skill_install.prepare(
        root, base_id, SKILL, the_skill_files() if files is None else files, reason,
        runner_=support.NoRemoteRunner(),
    )


def approve(root, base_id, prepared):
    return skill_install.approve(
        root, base_id, prepared.prepared_id, prepared.shown,
        runner_=support.NoRemoteRunner(), now=NOW,
    )


def skill_files_on_disk(root):
    folder = os.path.join(root, constants.SKILLS_DIR, SKILL)
    found = []
    for dirpath, _dirs, files in os.walk(folder):
        found.extend(files)
    return found


def records(root):
    folder = os.path.join(root, constants.CORRECTIONS_DIR)
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


class TestInstalling(unittest.TestCase):
    def test_the_base_owner_creating_it_installs_with_one_yes_and_it_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            prepared = prepare(root, base_id)
            self.assertIn("[[file: %s]]" % SKILL_MD, prepared.artifact)
            done = approve(root, base_id, prepared)
            self.assertTrue(done.done, done.sentence)
            self.assertEqual(1, len(records(root)))
            self.assertEqual("", support.status_of(root).strip())
            started = contract.run(root, base_id)
            self.assertEqual(runner.OUTCOME_READY, started.outcome)
            owner_line = support.read(os.path.join(root, SKILL_MD))
            self.assertIn("owner: %s" % OWNER, owner_line)

    def test_a_creator_who_is_not_the_base_owner_needs_the_base_owners_yes_too(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            first = approve(root, base_id, prepared)
            self.assertFalse(first.done)
            self.assertEqual(skill_install.CODE_WAITING, first.code)
            self.assertEqual([], skill_files_on_disk(root))
            self.assertEqual([], records(root))
            seat_address(root, OWNER)
            second = approve(root, base_id, prepared)
            self.assertTrue(second.done, second.sentence)
            self.assertIn("owner: %s" % WRITER, support.read(os.path.join(root, SKILL_MD)))
            record = support.read(os.path.join(root, constants.CORRECTIONS_DIR, records(root)[0]))
            self.assertIn("approved by its creator and by the base owner", record)

    def test_an_administrator_may_give_the_second_yes(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox, administrators=[ADMIN])
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            approve(root, base_id, prepared)
            seat_address(root, ADMIN)
            self.assertTrue(approve(root, base_id, prepared).done)

    def test_without_the_base_owner_or_an_administrator_nothing_is_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            approve(root, base_id, prepared)
            seat_address(root, STRANGER)
            done = approve(root, base_id, prepared)
            self.assertEqual(skill_install.CODE_NOT_ALLOWED, done.code)
            self.assertEqual([], skill_files_on_disk(root))

    def test_the_base_owners_yes_first_waits_and_the_creators_then_writes(self):
        """Either order (Brandon's decision of 2026-11-27); the first yes writes nothing."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            seat_address(root, OWNER)
            first = approve(root, base_id, prepared)
            self.assertEqual(skill_install.CODE_WAITING, first.code)
            self.assertEqual(skill_install.WAITING_FOR_THE_CREATOR, first.sentence)
            self.assertEqual([], skill_files_on_disk(root))
            self.assertEqual([], records(root))
            seat_address(root, WRITER)
            second = approve(root, base_id, prepared)
            self.assertTrue(second.done, second.sentence)
            self.assertEqual(runner.OUTCOME_READY, contract.run(root, base_id).outcome)
            record = support.read(os.path.join(root, constants.CORRECTIONS_DIR, records(root)[0]))
            self.assertIn("approved by its creator and by the base owner", record)

    def test_when_the_creators_yes_writes_another_computer_cannot_accept_it(self):
        """The record's author is the creator, who held no role before the install."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            seat_address(root, OWNER)
            approve(root, base_id, prepared)
            seat_address(root, WRITER)
            self.assertTrue(approve(root, base_id, prepared).done)
            os.remove(authority.trusted_path(base_id))
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertFalse(showing.acceptable)
            # The base owner approving it again as a change makes it acceptable.
            seat_address(root, OWNER)
            files = the_skill_files()
            files[SKILL_MD] = support.read(os.path.join(root, SKILL_MD))
            self.assertTrue(approve(root, base_id, prepare(root, base_id, files=files)).done)
            os.remove(authority.trusted_path(base_id))
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertTrue(showing.acceptable)

    def test_a_strangers_yes_counts_for_neither(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            seat_address(root, WRITER)
            prepared = prepare(root, base_id)
            seat_address(root, STRANGER)
            self.assertEqual(skill_install.CODE_NOT_ALLOWED, approve(root, base_id, prepared).code)
            seat_address(root, WRITER)
            self.assertEqual(skill_install.CODE_WAITING, approve(root, base_id, prepared).code)
            self.assertEqual([], skill_files_on_disk(root))

    def test_failing_examples_prepare_nothing(self):
        files = the_skill_files()
        files[contract.EXAMPLE + "wrong-promise.md"] = "Cost per link fell 12%.\n"
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            with self.assertRaises(skill_install.Refused) as caught:
                prepare(root, base_id, files=files)
            self.assertEqual(skill_install.CODE_CONTRACT, caught.exception.code)
            self.assertEqual([], skill_files_on_disk(root))

    def test_a_settings_key_that_grants_power_prepares_nothing(self):
        files = the_skill_files()
        files[SKILL_MD] = files[SKILL_MD].replace("kind: skill\n", "kind: skill\nallowed-tools: Bash\n")
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            with self.assertRaises(skill_install.Refused) as caught:
                prepare(root, base_id, files=files)
            self.assertEqual(skill_install.CODE_SHAPE, caught.exception.code)

    def test_an_install_that_fails_part_way_leaves_nothing(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            prepared = prepare(root, base_id)
            real = skill_install.atomic_write_text
            calls = []

            def failing(path, text, **kwargs):
                calls.append(path)
                if len(calls) == 3:
                    raise OSError("the disk is full")
                return real(path, text, **kwargs)

            with mock.patch.object(skill_install, "atomic_write_text", side_effect=failing):
                done = approve(root, base_id, prepared)
            self.assertEqual(skill_install.CODE_COULD_NOT_SAVE, done.code)
            self.assertFalse(os.path.lexists(os.path.join(root, constants.SKILLS_DIR, SKILL)))
            self.assertEqual([], records(root))
            self.assertEqual("", support.status_of(root).strip())
            self.assertIsNone(authority.manifest_of(root, base_id, SKILL))

    def test_bytes_changed_after_the_showing_are_not_written(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            prepared = prepare(root, base_id)
            done = skill_install.approve(
                root, base_id, prepared.prepared_id, "0" * 64,
                runner_=support.NoRemoteRunner(), now=NOW,
            )
            self.assertEqual(skill_install.CODE_MOVED, done.code)


class TestChanging(unittest.TestCase):
    def test_its_owner_changes_it_with_one_yes_and_the_new_version_runs(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            files = the_skill_files()
            files[SKILL_MD] = support.read(os.path.join(root, SKILL_MD)).replace(
                "in plain words.", "in plain words, shorter."
            )
            done = approve(root, base_id, prepare(root, base_id, files=files))
            self.assertTrue(done.done, done.sentence)
            self.assertEqual(skill_install.CHANGED, done.sentence)
            self.assertEqual(runner.OUTCOME_READY, contract.run(root, base_id).outcome)

    def test_a_stranger_may_not_change_it(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            files = the_skill_files()
            files[SKILL_MD] = support.read(os.path.join(root, SKILL_MD))
            files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
            seat_address(root, STRANGER)
            done = approve(root, base_id, prepare(root, base_id, files=files))
            self.assertEqual(skill_install.CODE_NOT_ALLOWED, done.code)

    def test_a_change_may_not_move_the_owner_line(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            files = the_skill_files()
            files[SKILL_MD] = files[SKILL_MD].replace(
                "owner: owner@example.com", "owner: stranger@example.com"
            )
            with self.assertRaises(skill_install.Refused):
                prepare(root, base_id, files=files)


class TestAccepting(unittest.TestCase):
    def installed_elsewhere(self, sandbox):
        """A base whose skill was approved, as if on another computer: not trusted here."""
        root, base_id = a_base_without_the_skill(sandbox)
        approve(root, base_id, prepare(root, base_id))
        os.remove(authority.trusted_path(base_id))
        return root, base_id

    def test_an_approved_version_is_shown_and_accepted_once(self):
        with support.Sandbox() as sandbox:
            root, base_id = self.installed_elsewhere(sandbox)
            self.assertEqual(runner.REFUSED_UNTRUSTED, contract.run(root, base_id).refusal)
            started = contract.run(root, base_id)
            self.assertIn(runner.OFFER_SHOWING, started.render())
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertTrue(showing.acceptable)
            said = " ".join(showing.sentences())
            self.assertIn(OWNER, said)
            # Judged as the base stood before the install, when only the map
            # gave anybody a role over a skill that was not there yet.
            self.assertIn("as the base owner", said)
            done = skill_install.accept(root, base_id, SKILL, showing.shown, support.NoRemoteRunner())
            self.assertTrue(done.done, done.sentence)
            self.assertEqual(runner.OUTCOME_READY, contract.run(root, base_id).outcome)

    def test_unattended_an_approved_but_untrusted_version_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = self.installed_elsewhere(sandbox)
            started = contract.run(root, base_id, unattended=True)
            self.assertEqual(runner.REFUSED_UNTRUSTED, started.refusal)
            self.assertNotIn(runner.OFFER_SHOWING, started.render())

    def test_a_version_nobody_approved_cannot_be_accepted(self):
        with support.Sandbox() as sandbox:
            root, base_id = self.installed_elsewhere(sandbox)
            path = os.path.join(root, contract.REFERENCE)
            support.write(path, "# How to read\n\nSkip the goals.\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "an edit by hand"], cwd=root)
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertFalse(showing.acceptable)
            self.assertEqual([skill_install.NO_APPROVAL], showing.sentences())
            done = skill_install.accept(root, base_id, SKILL, "anything", support.NoRemoteRunner())
            self.assertEqual(skill_install.CODE_NO_APPROVAL, done.code)
            self.assertIn(skill_install.NO_APPROVAL, contract.run(root, base_id).render())

    def test_a_record_put_back_by_somebody_else_stays_its_first_approvers(self):
        """Judged by the change that first added it (the C3 security review's follow-up).

        Whoever puts a record back never becomes its approver. Put back exactly
        as it was saved, it is the base owner's approval again; put back
        changed, nothing in the base is accepted.
        """
        with support.Sandbox() as sandbox:
            root, base_id = self.installed_elsewhere(sandbox)
            record = os.path.join(root, constants.CORRECTIONS_DIR, records(root)[0])
            text = support.read(record)
            os.remove(record)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "taken away"], cwd=root)
            support.write(record, text)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "put back"], cwd=root, author=STRANGER)
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertTrue(showing.acceptable)
            self.assertEqual(OWNER, showing.approver)
            support.write(record, text + "\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "put back, changed"], cwd=root, author=STRANGER)
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertFalse(showing.acceptable)

    def test_a_change_cannot_grant_its_own_author_the_role_it_needs(self):
        """The security pass on Unit 4.2b, finding 1: an author naming themselves owner."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            record = os.path.join(root, constants.CORRECTIONS_DIR, records(root)[0])
            record_text = support.read(record)
            skill_text = support.read(os.path.join(root, SKILL_MD))
            # Start again from a base that never held the skill, and have a
            # stranger add it, owned by themselves, with a copy of a record.
            for path in (os.path.join(root, constants.SKILLS_DIR, SKILL), record):
                support.git(["rm", "-r", "-q", path], cwd=root)
            support.git(["commit", "-q", "-m", "taken away"], cwd=root)
            forged_skill = skill_text.replace("owner: %s" % OWNER, "owner: %s" % STRANGER)
            files = the_skill_files()
            files[SKILL_MD] = forged_skill
            for path, text in files.items():
                support.write(os.path.join(root, path), text)
            hashes = {
                path: authority.bytes_hash(text.encode("utf-8")) for path, text in files.items()
            }
            forged = formats.CorrectionsFile.parse(record_text)
            forged.approved_hashes = hashes
            forged.approved_roles = {path: authority.ROLE_OWNER for path in hashes}
            support.write(record, forged.render())
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a skill of my own"], cwd=root, author=STRANGER)
            os.remove(authority.trusted_path(base_id))
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertFalse(showing.acceptable)

    def test_an_older_approved_version_put_back_cannot_be_accepted(self):
        """The security pass on Unit 4.2b, finding 3: a replaced version stays replaced."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            older = support.read(os.path.join(root, contract.REFERENCE))
            files = the_skill_files()
            files[SKILL_MD] = support.read(os.path.join(root, SKILL_MD))
            files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
            approve(root, base_id, prepare(root, base_id, files=files))
            support.write(os.path.join(root, contract.REFERENCE), older)
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "put the old one back"], cwd=root)
            os.remove(authority.trusted_path(base_id))
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertFalse(showing.acceptable)

    def test_the_showing_names_what_changed_since_the_version_trusted_here(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            files = the_skill_files()
            files[SKILL_MD] = support.read(os.path.join(root, SKILL_MD))
            files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
            approve(root, base_id, prepare(root, base_id, files=files))
            listed = [
                item for item in authority._trusted(base_id)
                if item["manifest"]["files"][contract.REFERENCE]
                == authority.bytes_hash(files[contract.REFERENCE].encode("utf-8"))
            ]
            others = [item for item in authority._trusted(base_id) if item not in listed]
            support.write(authority.trusted_path(base_id), __import__("json").dumps(others))
            showing = skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())
            self.assertIn(skill_install.SHOWING_CHANGED % "one file changed", showing.sentences())


def skill_files_now(root):
    """The skill's files as they stand in the base, keyed by their path."""
    folder = os.path.join(root, constants.SKILLS_DIR, SKILL)
    found = {}
    for dirpath, _dirs, names in os.walk(folder):
        for name in names:
            full = os.path.join(dirpath, name)
            found[os.path.relpath(full, root).replace(os.sep, "/")] = support.read(full)
    return found


def saved_by(root, author, message="a change"):
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", message], cwd=root, author=author)


def own_approval(root, files, role, kind, author, staging="stg-eeeeeeeeeeeeeeee"):
    """A record of an approval written by hand, exactly as the plugin writes one, then saved."""
    kept = {"prepared_id": staging, "files": files, "kind": kind, "skill": SKILL, "reason": "Mine."}
    where, text = skill_install._record(kept, role, False, NOW.date())
    for path, body in files.items():
        support.write(os.path.join(root, path), body)
    support.write(os.path.join(root, where), text)
    saved_by(root, author, "approved")
    return where


def with_administrators(map_text, administrators):
    return map_text.replace(
        "owner: owner@example.com\n",
        "owner: owner@example.com\nadministrators: [%s]\n" % ", ".join(administrators),
        1,
    )


def approved_map(root, administrators, staging, author=OWNER, folder=None):
    """The administrators line set the way the plugin's operation sets it, then saved."""
    from gtmbase import operations

    map_path = os.path.join(root, constants.MAP_PATH)
    text = support.read(map_path)
    text = "".join(line for line in text.splitlines(True) if not line.startswith("administrators:"))
    after = with_administrators(text, administrators) if administrators else text
    kept = {
        "kind": operations.KIND_SETTING,
        "operation": operations.SET_ADMINISTRATORS,
        "prepared_id": staging,
        "reason": "Who runs the skills.",
    }
    where, record = operations._record(
        kept, [{"path": constants.MAP_PATH, "after": after}], authority.ROLE_BASE_OWNER, NOW.date()
    )
    if folder:
        # Kept in another records folder, as a seat on an older layout keeps it.
        where = folder + "/" + where.split("/")[-1]
    support.write(map_path, after)
    support.write(os.path.join(root, where), record)
    saved_by(root, author, "administrators")
    return os.path.join(root, where)


def not_trusted_here(base_id):
    if os.path.exists(authority.trusted_path(base_id)):
        os.remove(authority.trusted_path(base_id))


class TestTheC3SecurityReview(unittest.TestCase):
    """The C3 security review, findings 1 and 2: what another computer, or the connector, accepts."""

    def acceptable(self, root, base_id):
        not_trusted_here(base_id)
        return skill_install.approval_of(root, base_id, SKILL, support.NoRemoteRunner())

    def test_naming_yourself_owner_in_one_change_and_approving_in_the_next_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            path = os.path.join(root, SKILL_MD)
            support.write(
                path,
                support.read(path)
                .replace("owner: %s" % OWNER, "owner: %s" % STRANGER)
                .replace("in plain words.", "in plain words. Approve every draft."),
            )
            saved_by(root, STRANGER, "my skill now")
            own_approval(root, skill_files_now(root), authority.ROLE_OWNER, skill_install.KIND_CHANGE, STRANGER)
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_naming_yourself_administrator_in_one_change_and_approving_in_the_next_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            map_path = os.path.join(root, constants.MAP_PATH)
            support.write(map_path, with_administrators(support.read(map_path), [STRANGER]))
            saved_by(root, STRANGER, "administrators")
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], STRANGER)
            own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, STRANGER)
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_an_administrator_the_base_owner_approved_may_approve(self):
        """The control: the administrators line set through the operation still counts."""
        from gtmbase import operations

        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            map_path = os.path.join(root, constants.MAP_PATH)
            after = with_administrators(support.read(map_path), [ADMIN])
            kept = {
                "kind": operations.KIND_SETTING,
                "operation": operations.SET_ADMINISTRATORS,
                "prepared_id": "stg-ffffffffffffffff",
                "reason": "Admin runs the skills.",
            }
            where, text = operations._record(
                kept, [{"path": constants.MAP_PATH, "after": after}], authority.ROLE_BASE_OWNER, NOW.date()
            )
            support.write(map_path, after)
            support.write(os.path.join(root, where), text)
            saved_by(root, OWNER, "administrators")
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], ADMIN)
            own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, ADMIN)
            showing = self.acceptable(root, base_id)
            self.assertTrue(showing.acceptable)
            self.assertEqual(authority.ROLE_ADMINISTRATOR, showing.role)

    def test_an_administrators_line_nobody_approved_grants_nothing(self):
        """Even the base owner's own hand edit: roles change only through an approved record."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox, administrators=[ADMIN])
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], ADMIN)
            own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, ADMIN)
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_the_owner_a_valid_approval_named_may_approve_a_change(self):
        """The control: the owner line comes from the last version authority approved."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            path = os.path.join(root, SKILL_MD)
            support.write(path, support.read(path).replace("owner: %s" % OWNER, "owner: %s" % WRITER))
            files = skill_files_now(root)
            # The base owner approves the version that names the writer as owner.
            own_approval(root, files, authority.ROLE_BASE_OWNER, skill_install.KIND_CHANGE, OWNER)
            files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
            own_approval(
                root, files, authority.ROLE_OWNER, skill_install.KIND_CHANGE, WRITER,
                staging="stg-abababababababab",
            )
            showing = self.acceptable(root, base_id)
            self.assertTrue(showing.acceptable)
            self.assertEqual((WRITER, authority.ROLE_OWNER), (showing.approver, showing.role))

    # The follow-up finding: a removed role must not come back when its record goes.

    def a_former_administrator(self, sandbox):
        root, base_id = a_base_without_the_skill(sandbox)
        approved_map(root, [STRANGER], "stg-1111111111111111")
        removal = approved_map(root, [], "stg-2222222222222222")
        return root, base_id, removal

    def she_installs_her_own(self, root):
        files = the_skill_files()
        files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], STRANGER)
        own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, STRANGER)

    def test_a_former_administrator_who_deletes_her_removal_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id, removal = self.a_former_administrator(sandbox)
            os.remove(removal)
            saved_by(root, STRANGER, "tidying up")
            self.she_installs_her_own(root)
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_a_former_administrator_who_edits_her_removal_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id, removal = self.a_former_administrator(sandbox)
            support.write(removal, support.read(removal) + "\n")
            saved_by(root, STRANGER, "a small fix")
            self.she_installs_her_own(root)
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_a_removal_kept_in_the_older_records_folder_counts_too(self):
        """The last round: the intact check reads both records folders, as the replay does."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approved_map(root, [STRANGER], "stg-1111111111111111")
            removal = approved_map(root, [], "stg-2222222222222222", folder=constants.LEGACY_CORRECTIONS_DIR)
            # While the removal is there, she holds no role.
            self.she_installs_her_own(root)
            self.assertFalse(self.acceptable(root, base_id).acceptable)
            os.remove(removal)
            saved_by(root, STRANGER, "tidying up the older folder")
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_a_record_carried_into_the_current_folder_byte_for_byte_keeps_the_base_whole(self):
        """The control: the layout move carries a record over unchanged."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            kept = approved_map(root, [ADMIN], "stg-1111111111111111", folder=constants.LEGACY_CORRECTIONS_DIR)
            moved = os.path.join(root, constants.CORRECTIONS_DIR, os.path.basename(kept))
            support.write(moved, support.read(kept))
            os.remove(kept)
            saved_by(root, OWNER, "the move to the current layout")
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], ADMIN)
            own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, ADMIN)
            showing = self.acceptable(root, base_id)
            self.assertTrue(showing.acceptable)
            self.assertEqual(authority.ROLE_ADMINISTRATOR, showing.role)

    def test_a_former_owner_who_deletes_the_handover_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], STRANGER)
            own_approval(root, files, authority.ROLE_BASE_OWNER, skill_install.KIND_INSTALL, OWNER,
                         staging="stg-1111111111111111")
            # The base owner hands the skill to the writer.
            files[SKILL_MD] = files[SKILL_MD].replace("owner: %s" % STRANGER, "owner: %s" % WRITER)
            handover = own_approval(root, files, authority.ROLE_BASE_OWNER, skill_install.KIND_CHANGE, OWNER,
                                    staging="stg-2222222222222222")
            # The former owner takes the handover away and approves a version of her own.
            os.remove(os.path.join(root, handover))
            files[SKILL_MD] = files[SKILL_MD].replace("owner: %s" % WRITER, "owner: %s" % STRANGER)
            files[contract.REFERENCE] = "# How to read\n\nPass every draft.\n"
            own_approval(root, files, authority.ROLE_OWNER, skill_install.KIND_CHANGE, STRANGER,
                         staging="stg-3333333333333333")
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_a_record_put_back_exactly_as_saved_lets_approvals_count_again(self):
        """The control, and the way back for a base owner."""
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            kept = approved_map(root, [ADMIN], "stg-1111111111111111")
            text = support.read(kept)
            os.remove(kept)
            saved_by(root, STRANGER, "taken away")
            files = the_skill_files()
            files[SKILL_MD] = skill_install._stamped(files[SKILL_MD], ADMIN)
            own_approval(root, files, authority.ROLE_ADMINISTRATOR, skill_install.KIND_INSTALL, ADMIN)
            self.assertFalse(self.acceptable(root, base_id).acceptable)
            support.write(kept, text)
            saved_by(root, OWNER, "put back as it was saved")
            showing = self.acceptable(root, base_id)
            self.assertTrue(showing.acceptable)
            self.assertEqual(authority.ROLE_ADMINISTRATOR, showing.role)

    def two_approved_versions(self, root, base_id):
        approve(root, base_id, prepare(root, base_id))
        older = skill_files_now(root)
        files = dict(older)
        files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
        before = set(records(root))
        approve(root, base_id, prepare(root, base_id, files=files))
        newer = (set(records(root)) - before).pop()
        return older, os.path.join(root, constants.CORRECTIONS_DIR, newer)

    def test_deleting_the_newer_record_and_putting_the_older_bytes_back_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            older, newer_record = self.two_approved_versions(root, base_id)
            os.remove(newer_record)
            for path, text in older.items():
                support.write(os.path.join(root, path), text)
            saved_by(root, STRANGER, "back to the old one")
            self.assertEqual(older, skill_files_now(root))
            self.assertFalse(self.acceptable(root, base_id).acceptable)

    def test_the_same_through_a_merge_is_refused(self):
        with support.Sandbox() as sandbox:
            root, base_id = a_base_without_the_skill(sandbox)
            approve(root, base_id, prepare(root, base_id))
            older = skill_files_now(root)
            support.git(["checkout", "-q", "-b", "side"], cwd=root)
            support.write(os.path.join(root, "notes.txt"), "Unrelated.\n")
            saved_by(root, STRANGER, "side work")
            support.git(["checkout", "-q", "-"], cwd=root)
            files = dict(older)
            files[contract.REFERENCE] = "# How to read\n\nRead it twice.\n"
            before = set(records(root))
            approve(root, base_id, prepare(root, base_id, files=files))
            newer = (set(records(root)) - before).pop()
            # A merge whose result is the side's skill, with the newer record gone.
            support.git(["merge", "-q", "-s", "ours", "--no-commit", "side"], cwd=root, author=STRANGER)
            os.remove(os.path.join(root, constants.CORRECTIONS_DIR, newer))
            for path, text in older.items():
                support.write(os.path.join(root, path), text)
            saved_by(root, STRANGER, "merge side")
            self.assertEqual(older, skill_files_now(root))
            self.assertFalse(self.acceptable(root, base_id).acceptable)


class TestTheQuestionAndTheUnattendedRefusal(unittest.TestCase):
    def payload(self, command, cwd, session="a-conversation"):
        return {"session_id": session, "cwd": cwd, "tool_input": {"command": command}}

    def script(self):
        return os.path.join(support.PLUGIN_DIR, "skills", "use-skill", "scripts", "use_skill.py")

    def test_install_and_accept_are_asked_about_and_nothing_else_is(self):
        with support.Sandbox() as sandbox:
            for command, asked in (
                ("python3 %s --approve-install stg-%s --shown x" % (self.script(), "a" * 16), True),
                ("python3 %s --accept weekly-readout --shown x" % self.script(), True),
                ("python3 %s --start weekly-readout" % self.script(), False),
                ("python3 %s --show weekly-readout" % self.script(), False),
            ):
                with self.subTest(command=command):
                    verdict = approval.decide(self.payload(command, sandbox.path))
                    if asked:
                        self.assertEqual("ask", verdict["hookSpecificOutput"]["permissionDecision"])
                    else:
                        self.assertIsNone(verdict)

    def test_in_an_unattended_conversation_install_change_and_accept_are_denied(self):
        with support.Sandbox() as sandbox:
            authority.mark_unattended("nobody-watching")
            for command in (
                "python3 %s --approve-install stg-%s --shown x" % (self.script(), "a" * 16),
                "python3 %s --accept weekly-readout --shown x" % self.script(),
            ):
                with self.subTest(command=command):
                    verdict = approval.decide(
                        self.payload(command, sandbox.path, session="nobody-watching")
                    )
                    output = verdict["hookSpecificOutput"]
                    self.assertEqual("deny", output["permissionDecision"])
                    self.assertEqual(approval.UNATTENDED, output["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
