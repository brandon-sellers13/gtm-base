"""Unit 4.2a of Plan 1: one authority rule, judged as of a saved version.

The signed company-skills requirements (CS1 to CS4, CS9 to CS11, CS30) are
what these tests hold: who may approve or confirm a document (its owners, the
base owner, and the administrators), read from the saved versions of the
document and the map at the moment in question; the manifest a skill is
approved and trusted as; this seat's list of trusted manifests; and the record
of conversations marked unattended.

The approvals themselves, and how the approve, confirm, stale and moment
modules ask this rule, are in tests/test_authority_everywhere.py. Every
fixture is written from scratch; the addresses are made up.
"""

import os
import unittest

import support

from gtmbase import authority, constants, ids

OWNER = "owner@example.com"
WRITER = "writer@example.com"
ADMIN = "admin@example.com"
STRANGER = "stranger@example.com"
BASE_ONE = ids.base_id_random()
BASE_TWO = ids.base_id_random()

MAP = """---
kind: map
owner: %(owner)s
administrators: %(administrators)s
sources: []
status: draft
---

# Map

## Settings

confirmation_threshold_days: 30
not_now_days: 7
"""


def map_text(owner=OWNER, administrators="[%s]" % ADMIN):
    return MAP % {"owner": owner, "administrators": administrators}


def document(owner=WRITER, body="Words."):
    return "---\nkind: positioning\nowner: %s\nsources: []\nstatus: draft\n---\n\n# Positioning\n\n%s\n" % (
        owner,
        body,
    )


class TestTheRolesInTheMap(unittest.TestCase):
    """CS2: one base owner, any number of administrators, in the settings block."""

    def test_the_owner_and_the_administrators(self):
        roles = authority.roles_from_map(map_text())
        self.assertEqual(OWNER, roles.base_owner)
        self.assertEqual([ADMIN], roles.administrators)
        self.assertEqual([], roles.problems)

    def test_administrators_may_be_empty_or_absent(self):
        for setting in ("[]", ""):
            with self.subTest(setting=setting):
                roles = authority.roles_from_map(map_text(administrators=setting))
                self.assertEqual([], roles.administrators)
                self.assertEqual([], roles.problems)
        text = map_text().replace("administrators: [%s]\n" % ADMIN, "")
        self.assertEqual([], authority.roles_from_map(text).administrators)

    def test_administrators_may_be_listed_line_by_line(self):
        text = map_text(administrators="\n- %s\n- %s" % (ADMIN, WRITER))
        self.assertEqual([ADMIN, WRITER], authority.roles_from_map(text).administrators)

    def test_a_map_owner_line_holding_two_addresses_names_no_base_owner(self):
        roles = authority.roles_from_map(map_text(owner="[%s, %s]" % (OWNER, ADMIN)))
        self.assertIsNone(roles.base_owner)
        self.assertIn(authority.CODE_MAP_OWNER_NOT_ONE, roles.problems)

    def test_an_administrator_that_is_not_an_address_names_none_of_them(self):
        """Fail closed: a list nobody can read grants nothing."""
        roles = authority.roles_from_map(map_text(administrators="[%s, everyone]" % ADMIN))
        self.assertEqual([], roles.administrators)
        self.assertIn(authority.CODE_ADMINISTRATORS_UNREADABLE, roles.problems)

    def test_a_map_that_cannot_be_read_names_nobody(self):
        roles = authority.roles_from_map(map_text().replace("status: draft", "\tstatus"))
        self.assertIsNone(roles.base_owner)
        self.assertEqual([], roles.administrators)
        self.assertIn(authority.CODE_MAP_UNREADABLE, roles.problems)


class TestTheAuthoritySet(unittest.TestCase):
    """CS3: a document's owners, the base owner, and the administrators."""

    def test_each_role_and_nobody_else(self):
        found = authority.authority_from(document(), map_text())
        self.assertEqual(authority.ROLE_OWNER, found.role_of(WRITER))
        self.assertEqual(authority.ROLE_BASE_OWNER, found.role_of(OWNER))
        self.assertEqual(authority.ROLE_ADMINISTRATOR, found.role_of(ADMIN))
        self.assertIsNone(found.role_of(STRANGER))
        self.assertIsNone(found.role_of(None))
        self.assertIsNone(found.role_of(""))
        self.assertEqual([WRITER, OWNER, ADMIN], found.addresses())

    def test_the_most_particular_role_is_the_one_recorded(self):
        found = authority.authority_from(document(owner=OWNER), map_text())
        self.assertEqual(authority.ROLE_OWNER, found.role_of(OWNER))

    def test_a_document_with_no_owner_still_has_the_base_owner(self):
        found = authority.authority_from(document(owner="[]"), map_text())
        self.assertEqual([], found.owners)
        self.assertEqual(authority.ROLE_BASE_OWNER, found.role_of(OWNER))

    def test_letter_case_is_compared_exactly_as_the_owner_line_always_was(self):
        found = authority.authority_from(document(), map_text())
        self.assertIsNone(found.role_of(WRITER.upper()))


class Base(object):
    """A base with a saved history, so authority can be judged at any point in it."""

    def __init__(self, sandbox):
        self.root = os.path.join(sandbox.path, "base")
        support.make_base(self.root, base_id=ids.base_id_random())
        self.write(constants.MAP_PATH, map_text())
        self.write("context/positioning.md", document())
        self.head = self.save("roles")

    def write(self, relative, text):
        support.write(os.path.join(self.root, relative), text)

    def save(self, message):
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", message], cwd=self.root)
        return support.head_of(self.root)


class TestJudgedAsItStoodThen(unittest.TestCase):
    """CS4: the saved versions of the document and the map, at that moment."""

    def test_an_unsaved_edit_to_an_owner_line_grants_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.write("context/positioning.md", document(owner=STRANGER))
            found = authority.at(base.root, "context/positioning.md")
            self.assertIsNone(found.role_of(STRANGER))
            self.assertEqual(authority.ROLE_OWNER, found.role_of(WRITER))

    def test_an_unsaved_edit_to_the_map_grants_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.write(constants.MAP_PATH, map_text(administrators="[%s]" % STRANGER))
            found = authority.at(base.root, "context/positioning.md")
            self.assertIsNone(found.role_of(STRANGER))

    def test_a_document_never_saved_is_judged_by_the_words_in_front_of_us(self):
        """There is no saved version, so the working one is all there is."""
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            base.write("context/messaging.md", document(owner=STRANGER))
            found = authority.at(base.root, "context/messaging.md")
            self.assertEqual(authority.ROLE_OWNER, found.role_of(STRANGER))

    def test_a_change_of_hands_is_judged_at_each_revision(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            before = base.head
            base.write("context/positioning.md", document(owner=STRANGER))
            after = base.save("passed to the stranger")
            path = "context/positioning.md"
            self.assertEqual(
                authority.ROLE_OWNER, authority.at(base.root, path, before).role_of(WRITER)
            )
            self.assertIsNone(authority.at(base.root, path, after).role_of(WRITER))
            self.assertEqual(
                authority.ROLE_OWNER, authority.at(base.root, path, after).role_of(STRANGER)
            )

    def test_an_administrator_removed_holds_the_role_only_before(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            before = base.head
            base.write(constants.MAP_PATH, map_text(administrators="[]"))
            after = base.save("no administrators")
            path = "context/positioning.md"
            self.assertEqual(
                authority.ROLE_ADMINISTRATOR,
                authority.at(base.root, path, before).role_of(ADMIN),
            )
            self.assertIsNone(authority.at(base.root, path, after).role_of(ADMIN))

    def test_a_document_at_its_older_path_then_is_found_there(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            older = base.head
            os.makedirs(os.path.join(base.root, "context", "strategy"), exist_ok=True)
            support.git(
                ["mv", "context/positioning.md", "context/strategy/positioning.md"],
                cwd=base.root,
            )
            base.save("an older layout")
            # Asked about the document by its current path, at a revision
            # where it sat at the older one.
            found = authority.at(base.root, "context/strategy/positioning.md", older)
            self.assertEqual(authority.ROLE_OWNER, found.role_of(WRITER))

    def test_a_revision_nobody_can_read_grants_nothing(self):
        with support.Sandbox() as sandbox:
            base = Base(sandbox)
            found = authority.at(base.root, "context/positioning.md", "0" * 40)
            self.assertEqual([], found.addresses())


class TestTheManifest(unittest.TestCase):
    """CS10: the base, the skill's name, every one of its files, and each file's hash."""

    def skill(self, root, files):
        for relative, text in files.items():
            support.write(os.path.join(root, relative), text)

    FILES = {
        "skills/ad-testing/SKILL.md": "---\nname: ad-testing\n---\n\nSteps.\n",
        "skills/ad-testing/references/rules.md": "Rules.\n",
        "skills/ad-testing/examples/one-night/input.md": "An input.\n",
    }

    def test_every_file_and_its_hash(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            self.skill(root, self.FILES)
            manifest = authority.manifest_of(root, BASE_ONE, "ad-testing")
            self.assertEqual(sorted(self.FILES), sorted(manifest.files))
            self.assertEqual(BASE_ONE, manifest.base_id)
            self.assertEqual("ad-testing", manifest.skill)

    def test_any_difference_is_a_different_manifest(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            self.skill(root, self.FILES)
            first = authority.manifest_of(root, BASE_ONE, "ad-testing").digest()
            for change in ("edit", "add", "remove"):
                with self.subTest(change=change):
                    extra = os.path.join(root, "skills/ad-testing/references/more.md")
                    rules = os.path.join(root, "skills/ad-testing/references/rules.md")
                    if change == "edit":
                        support.write(rules, "Rules, changed.\n")
                    elif change == "add":
                        support.write(extra, "More.\n")
                    else:
                        os.remove(rules)
                    self.assertNotEqual(
                        first, authority.manifest_of(root, BASE_ONE, "ad-testing").digest()
                    )
                    self.skill(root, self.FILES)
                    if os.path.exists(extra):
                        os.remove(extra)
            self.assertEqual(
                first, authority.manifest_of(root, BASE_ONE, "ad-testing").digest()
            )

    def test_the_same_files_in_another_base_are_another_manifest(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            self.skill(root, self.FILES)
            self.assertNotEqual(
                authority.manifest_of(root, BASE_ONE, "ad-testing").digest(),
                authority.manifest_of(root, BASE_TWO, "ad-testing").digest(),
            )

    def test_a_link_or_a_file_of_another_shape_cannot_make_a_manifest(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            self.skill(root, self.FILES)
            os.symlink(
                os.path.join(root, "skills/ad-testing/SKILL.md"),
                os.path.join(root, "skills/ad-testing/references/linked.md"),
            )
            self.assertIsNone(authority.manifest_of(root, BASE_ONE, "ad-testing"))
            os.remove(os.path.join(root, "skills/ad-testing/references/linked.md"))
            support.write(os.path.join(root, "skills/ad-testing/run.py"), "print()\n")
            self.assertIsNone(authority.manifest_of(root, BASE_ONE, "ad-testing"))


class TestWhatThisSeatTrusts(unittest.TestCase):
    """CS11: the list of trusted manifests lives on this seat, never in the base."""

    def test_a_manifest_is_trusted_only_once_trusted_and_only_whole(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            TestTheManifest().skill(root, TestTheManifest.FILES)
            manifest = authority.manifest_of(root, BASE_ONE, "ad-testing")
            self.assertFalse(authority.trusts(BASE_ONE, manifest))
            authority.trust(BASE_ONE, manifest, approver=OWNER, role=authority.ROLE_BASE_OWNER)
            self.assertTrue(authority.trusts(BASE_ONE, manifest))
            support.write(os.path.join(root, "skills/ad-testing/references/rules.md"), "x\n")
            changed = authority.manifest_of(root, BASE_ONE, "ad-testing")
            self.assertFalse(authority.trusts(BASE_ONE, changed))
            self.assertFalse(authority.trusts(BASE_TWO, manifest))
            self.assertFalse(os.path.exists(os.path.join(root, "work", "trusted.json")))

    def test_nothing_is_trusted_when_the_list_cannot_be_read(self):
        with support.Sandbox() as sandbox:
            root = os.path.join(sandbox.path, "base")
            TestTheManifest().skill(root, TestTheManifest.FILES)
            manifest = authority.manifest_of(root, BASE_ONE, "ad-testing")
            authority.trust(BASE_ONE, manifest, approver=OWNER, role=authority.ROLE_OWNER)
            support.write(authority.trusted_path(BASE_ONE), "not json")
            self.assertFalse(authority.trusts(BASE_ONE, manifest))
            self.assertIsNone(authority.trusts(BASE_ONE, None) or None)


class TestTheUnattendedMark(unittest.TestCase):
    """CS30: a conversation marked unattended stays marked, and only it."""

    def test_marked_and_not(self):
        with support.Sandbox():
            self.assertFalse(authority.is_unattended("conversation-one"))
            authority.mark_unattended("conversation-one")
            authority.mark_unattended("conversation-one")
            self.assertTrue(authority.is_unattended("conversation-one"))
            self.assertFalse(authority.is_unattended("conversation-two"))
            self.assertFalse(authority.is_unattended(None))
            self.assertFalse(authority.is_unattended(""))

    def test_a_mark_that_cannot_be_read_counts_as_marked_for_nobody_else(self):
        """A broken record never unmarks one that was readable before it broke."""
        with support.Sandbox():
            authority.mark_unattended("conversation-one")
            support.write(authority.unattended_path(), "not json")
            # Unreadable means the answer cannot be given, which refuses.
            self.assertTrue(authority.is_unattended("conversation-one"))
            self.assertTrue(authority.is_unattended("conversation-two"))

    def test_no_conversation_identifier_can_be_marked(self):
        with support.Sandbox():
            with self.assertRaises(ValueError):
                authority.mark_unattended("")


if __name__ == "__main__":
    unittest.main()
