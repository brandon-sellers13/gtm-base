"""Unit 1.5b: a base is laid out by the five CLASS parts.

A base holds `context/` (the nine files of the context standard, segments under
`context/icps/`), `learning/` (changes, corrections, and a reserved lessons
folder), `access/stack.md`, `skills/` (refused until a trust model exists), and
`standards/`, with `work/` for the approvals. Both layouts are read and only
the current one is written. A base on an older layout is offered one move in
"review my base", never moved on its own, and that one move takes it all the
way from wherever it starts.

Every scenario the plan lists for Unit 1.5b is here, named for what it proves.
Nothing here reaches the person's own home folder, their git settings, or a
real base.
"""

import datetime
import json
import os
import unittest

import plain_language
import support
import test_changes_migration as migration
import test_join_setup_flow as setup_flow

from gtmbase import (
    approve_local,
    base_reader,
    changes,
    compose_proposal,
    constants,
    drafting,
    formats,
    gate,
    ids,
    layout,
    moment,
    names,
    paths,
    read_hook,
    report,
    scan,
    session_start,
    stale,
    stale_check,
    trust_surface,
    write_hook,
)
from gtmbase.gitcmd import GitRunner

TODAY = migration.TODAY
OWNER = migration.OWNER
SOURCE = migration.SOURCE

# One change the profile has caught up with, one it has not, and one the
# positioning was fixed for by an accepted record.
SETTLED = "stg-3d15637d82690cca"
OPEN = "stg-4d15637d82690ccb"
FIXED = "stg-5d15637d82690ccc"

OLD_ICP = "context/strategy/icp.md"
OLD_POSITIONING = "context/strategy/positioning.md"
ICP = "context/icps.md"
POSITIONING = "context/positioning.md"
QUESTION = "q-" + "0" * 20
# The day the owner accepted the fix for the positioning, well before any move.
ACCEPTED_ON = "2026-08-01"


def entry_text(entry_id, affects, older=False, origin="manual", body=None):
    """One context change, in either spelling of its settings."""
    return "\n".join(
        [
            "---",
            "id: %s" % entry_id,
            "kind: %s" % ("decision" if older else "change"),
            "%s: 2026-09-01" % ("decided_on" if older else "happened_on"),
            "written_on: 2026-09-01",
            "%s: %s" % ("decided_by" if older else "noted_by", OWNER),
            "source: %s" % SOURCE,
            "affects: [%s]" % ", ".join(affects),
            "review_by: 2026-12-01",
            "origin: %s" % origin,
            "status: open",
            "---",
            "",
            body or "Something about the business changed for %s." % entry_id,
            "",
        ]
    )


class LayoutCase(unittest.TestCase):
    """A base the shape the one real base is, on the older layout."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.root, self.base_id = migration.build_base(self.sandbox)

    # --- Building one --------------------------------------------------------

    def put(self, relative, text):
        support.write(os.path.join(self.root, relative.replace("/", os.sep)), text)

    def save(self, message="a change"):
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", message], cwd=self.root)

    def save_on(self, message, day):
        """Save everything, dated as though it was saved on an earlier day.

        A record's acceptance is read off the day its change was saved, and a
        move made today must never be mistaken for it, which only shows when
        the two days differ (Astra's review of Unit 1.5b, finding 4).
        """
        import subprocess

        stamp = "%sT10:00:00" % day
        environment = dict(os.environ)
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Test Owner",
                "GIT_AUTHOR_EMAIL": OWNER,
                "GIT_COMMITTER_NAME": "Test Owner",
                "GIT_COMMITTER_EMAIL": OWNER,
                "GIT_AUTHOR_DATE": stamp,
                "GIT_COMMITTER_DATE": stamp,
                "GIT_CONFIG_NOSYSTEM": "1",
            }
        )
        for args in (["add", "-A"], ["commit", "-q", "-m", message]):
            subprocess.run(["git"] + args, cwd=self.root, env=environment, check=True)

    def with_changes(self, folder, older=False):
        """Two context changes about the profile in one older folder."""
        for entry_id in (SETTLED, OPEN):
            self.put(
                "%s/%s.md" % (folder, entry_id),
                entry_text(entry_id, [OLD_ICP], older=older),
            )
        # The owner said the profile already reflects the first one, on the
        # line written the way a base laid out before this writes it.
        self.put(
            constants.CONFIRMATIONS_DIR + "/context--strategy--icp.md",
            "date=2026-09-02 time=10:00:00Z file=%s trigger=ledger entry=%s "
            "question=%s run=-\n" % (OLD_ICP, SETTLED, QUESTION),
        )
        self.save("two context changes and a confirmation")

    def with_a_caught_change_fixed_by_a_record(self, folder=constants.WORK_CHANGES_DIR):
        """A change a run caught, fixed by an approved proposal with its record.

        The record sits in the older folder of records. It settles the change
        for the positioning, and because it was accepted by the owner it
        counts as the owner confirming the positioning that day. It is also
        the one catch the summary counts.
        """
        positioning = (
            "---\nkind: positioning\nowner: %s\nlast_confirmed: 2026-01-12\n"
            "sources: []\nstatus: approved\n---\n\n# Positioning\n\nWe sell to "
            "teams of twenty to two hundred people.\n" % OWNER
        )
        self.put(OLD_POSITIONING, positioning)
        self.put(
            "%s/%s.md" % (folder, FIXED),
            entry_text(FIXED, [OLD_POSITIONING], origin="inbox"),
        )
        record = formats.CorrectionsFile(
            kind="correction",
            date=TODAY.isoformat(),
            staging_id=FIXED,
            entry_id=FIXED,
            source_id=SOURCE,
            intake_path="ledger",
            mode="none",
            third_party=False,
            content_hash=ids.content_hash(positioning),
            correction_class="new-decision",
            marker="gtm-base proposal %s entry %s source %s" % (FIXED, FIXED, SOURCE),
            touched_paths=[OLD_POSITIONING],
            what_changed="Before: one thing.\n\nAfter: another thing.",
            why="Because the change said so.",
        )
        self.put(
            constants.LEGACY_CORRECTIONS_DIR + "/%s-%s.md" % (TODAY.isoformat(), FIXED),
            record.validate().render(),
        )
        self.save_on("Proposal %s applied" % FIXED, ACCEPTED_ON)

    def with_the_older_template_folders(self):
        """The placeholders the older template made, and its map paragraph."""
        for folder in (
            "context/metrics",
            "context/plan",
            "context/notes",
            constants.LEGACY_CORRECTIONS_DIR,
        ):
            self.put(folder + "/" + constants.PLACEHOLDER_NAME, "")
        text = support.read(os.path.join(self.root, constants.MAP_PATH))
        self.put(
            constants.MAP_PATH,
            text + "\n" + changes.MAP_WHERE_HEADING + "\n\n"
            + changes.MAP_WHERE_EARLIER[0] + "\n",
        )
        self.save("the older template")

    def older_base(self, folder=constants.WORK_CHANGES_DIR, older=False):
        self.with_the_older_template_folders()
        self.with_changes(folder, older=older)
        self.with_a_caught_change_fixed_by_a_record()

    # --- Reading one ---------------------------------------------------------

    def reading(self):
        """Everything a person could be told about this base, by document name.

        Paths change in a move and nothing a person reads names one, so every
        document is keyed by the name a person calls it.
        """
        inputs = base_reader.read_base(
            self.root, self.base_id, today=TODAY, record_dropped=False
        )
        computed = stale.compute(
            today=TODAY,
            settings=inputs.settings,
            files=inputs.files,
            ledger=inputs.ledger,
            confirmations=inputs.confirmations,
            corrections=inputs.corrections,
            seat=inputs.seat,
            owner_email=None,
        )
        flags = sorted(
            (
                names.document_name(flag.path),
                flag.reason,
                flag.trigger,
                tuple(sorted(flag.entry_ids)),
                str(flag.newest_confirmation or ""),
            )
            for flag in computed.file_flags
        )
        entries = {}
        for row in inputs.ledger:
            if row.entry is None:
                continue
            entries[row.entry.id] = (
                row.entry.body,
                str(row.entry.happened_on),
                str(row.entry.noted_by),
                row.entry.status,
                tuple(names.document_name(path) for path in row.entry.affects),
            )
        confirmed = {
            names.document_name(path): str(day)
            for path, day in computed.confirmed_on.items()
        }
        return {
            "flags": flags,
            "entries": entries,
            "confirmed": confirmed,
            "malformed": sorted(item.code for item in computed.malformed),
            "catches": report.catches(self.root, GitRunner(), TODAY)["count"],
            "missing": base_reader.missing_required(inputs.by_path),
        }

    def review(self, session="sess-1"):
        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id=session,
            mode="review",
            dry_run=True,
        )

    def subjects_since(self, head):
        found = support.git(
            ["log", "--format=%s", "%s..HEAD" % head], cwd=self.root
        ).stdout.decode("utf-8")
        return [line for line in found.split("\n") if line]

    def listing(self, folder):
        where = os.path.join(self.root, folder.replace("/", os.sep))
        if not os.path.isdir(where):
            return []
        return sorted(os.listdir(where))


# --- Happy path: the older layout, read the same before and after the move ---


class TestAnOlderBaseReadsTheSameBeforeAndAfterTheMove(LayoutCase):
    """Happy path: read identically, offered the move, moved, read identically."""

    def test_on_work_changes(self):
        self.older_base(constants.WORK_CHANGES_DIR)
        self.assert_the_whole_move()

    def test_on_work_decisions(self):
        self.older_base(constants.LEGACY_CHANGES_DIR, older=True)
        self.assert_the_whole_move()

    def assert_the_whole_move(self):
        before = self.reading()
        # The confirmation settles the first change, the record settles the
        # third, and the second is the one still open against the profile.
        self.assertTrue(
            any(
                flag[0] == "your customer profile" and flag[3] == (OPEN,)
                for flag in before["flags"]
            ),
            before["flags"],
        )
        self.assertFalse(
            any(FIXED in flag[3] for flag in before["flags"]), before["flags"]
        )
        self.assertEqual(1, before["catches"])
        self.assertEqual([], before["missing"])

        offered = self.review()
        self.assertIn(changes.offer_sentence(self.root), offered.sentences)
        self.assertEqual(1, offered.sentences.count(changes.offer_sentence(self.root)))

        head = support.head_of(self.root)
        moved = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, moved.status, moved.sentence)
        self.assertEqual(changes.MIGRATED, moved.sentence)

        self.assertEqual(before, self.reading())
        after = self.review(session="sess-2")
        self.assertFalse(any(changes.is_the_offer(line) for line in after.sentences))
        self.assertEqual(
            [line for line in offered.sentences if not changes.is_the_offer(line)],
            after.sentences,
        )
        self.assertFalse(changes.needed(self.root))

        # Change one is a pure rename, and the settings and the record are
        # saved after it on their own.
        subjects = self.subjects_since(head)
        self.assertEqual(changes.MOVE_SUBJECT, subjects[-1])
        self.assertEqual(changes.RECORD_SUBJECT, subjects[0])
        move = support.git(
            ["rev-list", "--reverse", "%s..HEAD" % head], cwd=self.root
        ).stdout.decode("utf-8").split()[0]
        shown = support.git(
            ["show", "-M", "--name-status", "--format=", move], cwd=self.root
        ).stdout.decode("utf-8")
        for line in shown.strip().split("\n"):
            letter = line.split("\t")[0]
            self.assertTrue(letter in ("R100", "D"), line)
        self.assertEqual("", support.status_of(self.root))

    def test_every_file_is_where_the_current_layout_keeps_it(self):
        self.older_base(constants.LEGACY_CHANGES_DIR, older=True)
        changes.migrate(self.root, self.base_id, today=TODAY)

        for relative in (ICP, POSITIONING):
            self.assertTrue(os.path.isfile(os.path.join(self.root, relative)))
        self.assertFalse(os.path.exists(os.path.join(self.root, "context", "strategy")))
        for folder in ("context/metrics", "context/plan", "context/notes"):
            self.assertFalse(os.path.exists(os.path.join(self.root, folder)), folder)
        self.assertEqual(
            sorted([SETTLED + ".md", OPEN + ".md", FIXED + ".md"]),
            self.listing(constants.CHANGES_DIR),
        )
        self.assertEqual([], self.listing(constants.WORK_CHANGES_DIR))
        self.assertEqual([], self.listing(constants.LEGACY_CHANGES_DIR))
        self.assertEqual([], self.listing(constants.LEGACY_CORRECTIONS_DIR))
        records = self.listing(constants.CORRECTIONS_DIR)
        self.assertIn("%s-%s.md" % (TODAY.isoformat(), FIXED), records)
        self.assertEqual(
            1, len([name for name in records if "move-to-the-class-layout" in name])
        )
        for folder in constants.LAYOUT_EMPTY_FOLDERS:
            self.assertEqual([constants.PLACEHOLDER_NAME], self.listing(folder))
        # The map's paragraph was still the one GTM Base wrote, so it now says
        # where things live today.
        text = support.read(os.path.join(self.root, constants.MAP_PATH))
        self.assertIn(changes.MAP_WHERE_TODAY, text)
        self.assertNotIn("context/strategy", text)

    def test_every_confirmation_still_settles_its_file(self):
        self.older_base()
        changes.migrate(self.root, self.base_id, today=TODAY)
        inputs = base_reader.read_base(self.root, self.base_id, today=TODAY)
        lines = [
            record.line
            for record in inputs.confirmations
            if record.line.entry == SETTLED
        ]
        self.assertEqual([ICP], [line.file for line in lines])
        # Git still says the owner wrote it, through the move.
        self.assertEqual(
            [OWNER],
            [
                record.author_email
                for record in inputs.confirmations
                if record.line.entry == SETTLED
            ],
        )

    def test_a_map_paragraph_the_person_changed_is_left_exactly_as_it_is(self):
        self.older_base()
        text = support.read(os.path.join(self.root, constants.MAP_PATH))
        edited = text.replace("strategy\ndocuments", "strategy\nwriting")
        self.assertNotEqual(text, edited)
        self.put(constants.MAP_PATH, edited)
        self.save("my own words")
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(
            edited, support.read(os.path.join(self.root, constants.MAP_PATH))
        )


# --- The three starting states and the one offer -------------------------------


class TestOneOfferTakesABaseAllTheWay(LayoutCase):
    """Unit 1.4's offer and this one are one offer, whatever state a base is in."""

    def offers(self):
        return [
            sentence
            for sentence in self.review().sentences
            if changes.is_the_offer(sentence) or changes.is_every_seat_first(sentence)
        ]

    def assert_one_offer_then_none(self):
        # Every day a document was last confirmed is the same afterwards, in
        # every starting state (Astra's review of Unit 1.5b, finding 4).
        confirmed = self.reading()["confirmed"]
        self.assertEqual([changes.offer_sentence(self.root)], self.offers())
        moved = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(moved.ok, moved.sentence)
        self.assertEqual(confirmed, self.reading()["confirmed"])
        self.assertFalse(changes.needed(self.root))
        self.assertEqual([], self.offers())
        again = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_NOT_NEEDED, again.status)

    def test_a_base_still_on_work_decisions(self):
        self.with_changes(constants.LEGACY_CHANGES_DIR, older=True)
        self.with_a_caught_change_fixed_by_a_record(constants.LEGACY_CHANGES_DIR)
        self.assertEqual(ACCEPTED_ON, self.reading()["confirmed"]["your positioning"])
        self.assert_one_offer_then_none()
        for entry_id in (SETTLED, OPEN):
            text = support.read(
                os.path.join(self.root, constants.CHANGES_DIR, entry_id + ".md")
            )
            self.assertIn("kind: change", text)
            self.assertIn("noted_by:", text)

    def test_a_base_on_work_changes(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        self.with_a_caught_change_fixed_by_a_record()
        self.assertEqual(ACCEPTED_ON, self.reading()["confirmed"]["your positioning"])
        self.assert_one_offer_then_none()

    def test_a_base_holding_both_older_folders(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        self.put(
            constants.LEGACY_CHANGES_DIR + "/%s.md" % FIXED,
            entry_text(FIXED, [OLD_ICP], older=True),
        )
        self.save("one more from an older seat")
        self.assert_one_offer_then_none()
        self.assertEqual(
            sorted([SETTLED + ".md", OPEN + ".md", FIXED + ".md"]),
            self.listing(constants.CHANGES_DIR),
        )

    def test_a_base_already_moved_is_never_offered_anything(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        self.with_a_caught_change_fixed_by_a_record()
        confirmed = self.reading()["confirmed"]
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(confirmed, self.reading()["confirmed"])
        head = support.head_of(self.root)
        self.assertEqual([], self.offers())
        self.assertEqual(
            changes.STATUS_NOT_NEEDED,
            changes.migrate(self.root, self.base_id, today=TODAY).status,
        )
        self.assertEqual(head, support.head_of(self.root))

    def test_an_older_seat_writing_after_the_move_brings_one_offer_back(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.put(
            constants.WORK_CHANGES_DIR + "/%s.md" % FIXED,
            entry_text(FIXED, [ICP]),
        )
        self.save("written by a seat on 0.3.1")
        self.assert_one_offer_then_none()

    def test_a_run_the_release_before_left_unfinished_is_finished_and_carried_on(self):
        """A note from the 0.3.x move is finished as it was, then the rest is done.

        This is the state of a base whose owner said yes to the 0.3.x offer and
        whose run stopped after its first saved piece: its changes moved into
        `work/changes` under the older setting names, the record not written.
        """
        self.with_changes(constants.LEGACY_CHANGES_DIR, older=True)
        head = support.head_of(self.root)
        moved = []
        for entry_id in (SETTLED, OPEN):
            name = entry_id + ".md"
            os.makedirs(
                os.path.join(self.root, constants.WORK_CHANGES_DIR), exist_ok=True
            )
            text = support.read(
                os.path.join(self.root, constants.LEGACY_CHANGES_DIR, name)
            )
            support.git(
                [
                    "mv",
                    constants.LEGACY_CHANGES_DIR + "/" + name,
                    constants.WORK_CHANGES_DIR + "/" + name,
                ],
                cwd=self.root,
            )
            moved.append((name, text))
        support.git(
            ["commit", "-q", "-m", constants.MOVE_TO_CHANGES_SUBJECT], cwd=self.root
        )
        names_moved = [name for name, _text in moved]
        note = {
            "schema": 1,
            "base_root": os.path.realpath(self.root),
            "head": head,
            "subjects": list(changes.LEGACY_SUBJECTS),
            "paths": [
                {
                    "path": constants.WORK_CHANGES_DIR + "/" + name,
                    "hash": ids.exact_hash(formats.rewritten_safely(text)),
                    "after_move": ids.exact_hash(text),
                }
                for name, text in moved
            ]
            + [
                {
                    "path": constants.LEGACY_CORRECTIONS_DIR
                    + "/"
                    + changes._legacy_record_name(TODAY, names_moved),
                    "hash": ids.exact_hash(
                        changes._legacy_record_for(names_moved, TODAY)
                    ),
                }
            ],
            "came_from": [
                {
                    "path": constants.LEGACY_CHANGES_DIR + "/" + name,
                    "hash": ids.exact_hash(text),
                }
                for name, text in moved
            ],
            "removed": [],
            "day": TODAY.isoformat(),
            "started_at": "2026-09-20T10:00:00Z",
        }
        support.write(
            os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE),
            json.dumps(note),
        )

        finished = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(finished.ok, finished.sentence)
        self.assertFalse(changes.needed(self.root))
        self.assertFalse(
            os.path.exists(
                os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)
            )
        )
        self.assertEqual(
            sorted(names_moved), self.listing(constants.CHANGES_DIR)
        )
        for name in names_moved:
            self.assertIn(
                "kind: change",
                support.read(os.path.join(self.root, constants.CHANGES_DIR, name)),
            )
        # The record the release before meant to write was written, and then
        # carried into the current folder of records with everything else.
        records = self.listing(constants.CORRECTIONS_DIR)
        self.assertIn(changes._legacy_record_name(TODAY, names_moved), records)
        self.assertTrue(os.path.isfile(os.path.join(self.root, ICP)))
        subjects = self.subjects_since(head)
        self.assertIn(changes.LEGACY_SUBJECTS[1], subjects)
        self.assertIn(changes.LEGACY_SUBJECTS[2], subjects)
        self.assertIn(changes.MOVE_SUBJECT, subjects)
        self.assertEqual("", support.status_of(self.root))

    def test_nothing_moves_without_a_yes(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        head = support.head_of(self.root)
        self.review()
        self.review(session="sess-2")
        stale_check.run(
            self.root, self.base_id, gh=support.RecordingGh(), now=TODAY,
            session_id="sess-3",
        )
        self.assertEqual(head, support.head_of(self.root))
        self.assertTrue(changes.needed(self.root))
        self.assertTrue(os.path.isfile(os.path.join(self.root, OLD_ICP)))


# --- Setup on a fresh folder writes the current layout -------------------------


class TestSetupWritesTheCurrentLayout(unittest.TestCase):
    """Happy path: setup writes the two documents where the standard keeps them."""

    def test_the_two_documents_land_at_the_current_paths_and_are_named_plainly(self):
        with support.Sandbox() as sandbox:
            run = setup_flow.SetupRun(sandbox).two_documents()
            root = run.root

            self.assertEqual(ICP, drafting.ICP_PATH)
            self.assertEqual(POSITIONING, drafting.POSITIONING_PATH)
            for relative in (ICP, POSITIONING, constants.MAP_PATH, constants.STACK_PATH):
                self.assertTrue(os.path.isfile(os.path.join(root, relative)), relative)
            for folder in (
                "context/strategy",
                constants.WORK_CHANGES_DIR,
                constants.LEGACY_CORRECTIONS_DIR,
            ):
                self.assertFalse(os.path.exists(os.path.join(root, folder)), folder)
            for folder in constants.LAYOUT_EMPTY_FOLDERS + (
                constants.CHANGES_DIR,
                constants.CORRECTIONS_DIR,
            ):
                self.assertTrue(os.path.isdir(os.path.join(root, folder)), folder)
            # The owner's own address is on the source map, as on the documents.
            stack = support.read(os.path.join(root, constants.STACK_PATH))
            self.assertNotIn(constants.OWNER_PLACEHOLDER_EMAIL, stack)
            self.assertEqual("", support.status_of(root))
            self.assertFalse(changes.needed(root))

            closed = run.close()
            self.assertIn("your customer profile", closed.finding)
            for said in (closed.finding, closed.closing):
                self.assertNotIn("context/", said)

            base_id = paths.resolve_base(
                root, setup_flow.machine.load_machine_state()
            ).base_id
            review = stale_check.run(
                root, base_id, gh=support.RecordingGh(), now=setup_flow.TODAY,
                session_id="sess-1", mode="review", dry_run=True,
            )
            for sentence in review.sentences:
                self.assertNotIn("context/", sentence)

            flag = moment.check(root, base_id, ICP, session_id="sess-1")
            self.assertEqual(ICP, flag.path)
            for sentence in flag.sentences():
                self.assertNotIn("context/", sentence)

    def test_the_identifier_of_setups_context_change_did_not_move(self):
        """Worked out from where the profile used to be, so a resumed run agrees."""
        from gtmbase import review

        self.assertEqual(
            ids.staging_id("join", OLD_ICP, "join", 0), review.entry_id(0)
        )


# --- Error path: a stop at every boundary finishes or puts back ---------------

# The ownership list a base set up by 0.3.1 holds, word for word, with an
# owner of its own.
OLDER_CODEOWNERS = """# Files listed here need the owner's review before a change to them is accepted.
# Replace @owner-handle with the account that owns this base.
# Nothing under work/changes or work/confirmations is listed, because those
# folders are appended to by everyone on the team.

context/** @acme-owner
corrections/** @acme-owner
plugins/** @acme-owner
.claude/** @acme-owner
CLAUDE.md @acme-owner
AGENTS.md @acme-owner
.gitignore @acme-owner
gate-allowlist.txt @acme-owner
CODEOWNERS @acme-owner
"""


class Boundaries(object):
    """Every step of a run that changes the base or its note, counted.

    A step is one git command that changes the base (a move, a removal,
    staging, putting a file back, or a save), one file written, the note
    written, or a file or the note taken away. Asked to, it stops the run
    just before or just after one numbered step, and it says whether it did,
    so a test can never pass because the stop it asked for never came (Astra's
    review of Unit 1.5b, finding 13).
    """

    CHANGING = ("mv", "rm", "add", "checkout")

    def __init__(self, stop_before=None, stop_after=None):
        self.stop_before = stop_before
        self.stop_after = stop_after
        self.count = 0
        self.kinds = []
        self.fired = False
        self.inner = GitRunner()
        self.saved = {}

    def _step(self, kind, action):
        self.count += 1
        number = self.count
        self.kinds.append(kind)
        if number == self.stop_before:
            self.fired = True
            raise migration._Stopped()
        result = action()
        if number == self.stop_after:
            self.fired = True
            raise migration._Stopped()
        return result

    def run(self, args, cwd=None, timeout=20, input=None):
        arguments = [str(item) for item in args]

        def action():
            return self.inner.run(arguments, cwd=cwd, timeout=timeout, input=input)

        if "commit" in arguments:
            return self._step("git commit", action)
        if arguments and arguments[0] in self.CHANGING:
            return self._step("git " + arguments[0], action)
        return action()

    def check(self, args, cwd=None, timeout=20, input=None):
        from gtmbase.errors import GitError

        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result

    def __enter__(self):
        for name, kind in (
            ("atomic_write_text", "file written"),
            ("atomic_write_json", "note written"),
            ("remove", "file taken away"),
        ):
            real = getattr(changes, name)
            self.saved[name] = real

            def watched(*arguments, _real=real, _kind=kind, **options):
                return self._step(_kind, lambda: _real(*arguments, **options))

            setattr(changes, name, watched)
        return self

    def __exit__(self, kind, value, trace):
        for name, real in self.saved.items():
            setattr(changes, name, real)
        return False


class TestAStopAtEveryBoundary(LayoutCase):
    """Error path: the same bytes, index, and flags as an uninterrupted run."""

    def build(self):
        self.older_base(constants.LEGACY_CHANGES_DIR, older=True)
        # A segment at its older path, so every kind of file is carried.
        self.put(
            constants.LEGACY_SEGMENTS_DIR + "/mid-market.md",
            "---\nkind: segment\nowner: %s\nsources: []\nstatus: approved\n---\n\n"
            "# Mid market\n\nTeams of fifty.\n" % OWNER,
        )
        # The same change written in both older folders, so a copy is taken
        # away as well as moved.
        self.put(
            constants.LEGACY_CHANGES_DIR + "/%s.md" % FIXED,
            support.read(
                os.path.join(self.root, constants.WORK_CHANGES_DIR, FIXED + ".md")
            ),
        )
        # The ownership list 0.3.1 wrote, so its rules are brought along.
        self.put(constants.CODEOWNERS_PATH, OLDER_CODEOWNERS)
        self.save("a segment, a second copy, and the ownership list")

    def snapshot(self):
        """Every byte under the base but its history, the index, and the flags."""
        files = {}
        for top, folders, found in os.walk(self.root):
            folders[:] = [name for name in folders if name != "." + "git"]
            for name in found:
                full = os.path.join(top, name)
                relative = os.path.relpath(full, self.root).replace(os.sep, "/")
                with open(full, "rb") as handle:
                    files[relative] = handle.read()
        index = support.git(["ls-files", "-s"], cwd=self.root).stdout
        return files, index, self.reading(), support.status_of(self.root)

    def fresh(self):
        """A fresh base in a fresh sandbox, built the same way."""
        self.sandbox.__exit__(None, None, None)
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.root, self.base_id = migration.build_base(self.sandbox)
        self.build()

    def uninterrupted(self):
        """What one run that nothing stopped leaves, and every step it took."""
        self.fresh()
        counted = Boundaries()
        with counted:
            result = changes.migrate(self.root, self.base_id, today=TODAY, git=counted)
        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertFalse(counted.fired)
        return self.snapshot(), counted

    def test_every_boundary_before_and_after(self):
        expected, counted = self.uninterrupted()
        # The steps really are all of these kinds, so every kind is stopped at.
        for kind in (
            "note written",
            "git mv",
            "git rm",
            "git add",
            "git commit",
            "file written",
            "file taken away",
        ):
            self.assertIn(kind, counted.kinds)
        self.assertGreaterEqual(counted.count, 20)
        for number in range(1, counted.count + 1):
            for when in ("before", "after"):
                with self.subTest(step=number, kind=counted.kinds[number - 1], when=when):
                    self.fresh()
                    stopper = Boundaries(**{"stop_" + when: number})
                    with stopper:
                        with self.assertRaises(migration._Stopped):
                            changes.migrate(
                                self.root, self.base_id, today=TODAY, git=stopper
                            )
                    self.assertTrue(stopper.fired)
                    result = changes.migrate(self.root, self.base_id, today=TODAY)
                    self.assertTrue(result.ok, result.sentence)
                    files, index, reading, status = self.snapshot()
                    self.assertEqual(sorted(expected[0]), sorted(files))
                    self.assertEqual(expected[0], files)
                    self.assertEqual(expected[1], index)
                    self.assertEqual(expected[2], reading)
                    self.assertEqual("", status)


# --- The note is never trusted with more than the move writes ----------------


class TestTheNoteIsReadAsAStranger(LayoutCase):
    """A note is a file on the disk, so it is held to exactly what a run writes.

    Found by the correctness review of this unit: allowing every path under
    the context folder let an edited note have a recovery take away a
    document nobody had saved.
    """

    def note_path(self):
        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def write_note(self, payload):
        support.write(self.note_path(), json.dumps(payload))

    def test_a_note_naming_a_document_the_move_never_writes_touches_nothing(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        draft = "context/positioning-draft.md"
        text = "---\nkind: note\n---\n\nMy only copy.\n"
        self.put(draft, text)
        self.write_note(
            {
                "schema": 2,
                "base_root": os.path.realpath(self.root),
                "head": support.head_of(self.root),
                "subjects": list(changes.SUBJECTS),
                "paths": [{"path": draft, "hash": ids.exact_hash(text)}],
                "came_from": [],
                "removed": [],
                "day": TODAY.isoformat(),
            }
        )

        for run in (changes.migrate, changes.abandon):
            result = run(self.root, self.base_id, today=TODAY)
            self.assertEqual(changes.CODE_NOTE_UNREADABLE, result.code, run)
        self.assertEqual(text, support.read(os.path.join(self.root, draft)))
        self.assertTrue(os.path.isfile(self.note_path()))

    def test_a_note_naming_a_path_that_climbs_out_touches_nothing(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        before = support.read(os.path.join(self.root, OLD_POSITIONING))
        edited = before + "\nMy unsaved line.\n"
        self.put(OLD_POSITIONING, edited)
        self.write_note(
            {
                "schema": 1,
                "base_root": os.path.realpath(self.root),
                "head": support.head_of(self.root),
                "subjects": list(changes.LEGACY_SUBJECTS),
                "paths": [
                    {
                        "path": constants.WORK_CHANGES_DIR + "/%s.md" % OPEN,
                        "hash": ids.exact_hash("x"),
                    }
                ],
                "came_from": [],
                "removed": ["work/decisions/../../" + OLD_POSITIONING],
                "day": TODAY.isoformat(),
            }
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.CODE_NOTE_UNREADABLE, result.code)
        self.assertEqual(edited, support.read(os.path.join(self.root, OLD_POSITIONING)))

    def test_a_rewrite_only_run_of_the_release_before_is_finished(self):
        """The 0.3.x run that only rewrote settings, stopped before its record."""
        for entry_id in (SETTLED, OPEN):
            self.put(
                constants.WORK_CHANGES_DIR + "/%s.md" % entry_id,
                entry_text(entry_id, [OLD_ICP], older=True),
            )
        self.save("moved long ago, never rewritten")
        head = support.head_of(self.root)
        names_rewritten = []
        planned = []
        for entry_id in (SETTLED, OPEN):
            relative = constants.WORK_CHANGES_DIR + "/%s.md" % entry_id
            text = support.read(os.path.join(self.root, relative))
            rewritten = formats.rewritten_safely(text)
            planned.append(
                {
                    "path": relative,
                    "hash": ids.exact_hash(rewritten),
                    "after_move": ids.exact_hash(text),
                }
            )
            self.put(relative, rewritten)
            names_rewritten.append(entry_id + ".md")
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", changes.LEGACY_SUBJECTS[1]], cwd=self.root)
        record = changes._legacy_record_name(TODAY, names_rewritten)
        planned.append(
            {
                "path": constants.LEGACY_CORRECTIONS_DIR + "/" + record,
                "hash": ids.exact_hash(
                    changes._legacy_record_for(names_rewritten, TODAY)
                ),
            }
        )
        self.write_note(
            {
                "schema": 1,
                "base_root": os.path.realpath(self.root),
                "head": head,
                "subjects": list(changes.LEGACY_SUBJECTS),
                "paths": planned,
                "came_from": [],
                "removed": [],
                "day": TODAY.isoformat(),
            }
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertIn(record, self.listing(constants.CORRECTIONS_DIR))
        self.assertFalse(os.path.isfile(self.note_path()))
        self.assertFalse(changes.needed(self.root))
        self.assertEqual("", support.status_of(self.root))

    def test_a_copy_to_take_away_that_somebody_edited_is_theirs(self):
        """A run that stopped before taking an older copy away leaves it theirs."""
        self.put(
            constants.CHANGES_DIR + "/%s.md" % OPEN, entry_text(OPEN, [ICP])
        )
        self.put(
            constants.WORK_CHANGES_DIR + "/%s.md" % OPEN, entry_text(OPEN, [ICP])
        )
        self.save("the same change in two folders")
        runner = migration._StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except migration._Stopped:
            pass
        older = os.path.join(self.root, constants.WORK_CHANGES_DIR, OPEN + ".md")
        if not os.path.isfile(older):
            # The copy was already taken away before the stop; put it back as
            # the person might, with words of their own in it.
            support.git(
                ["checkout", "HEAD", "--", constants.WORK_CHANGES_DIR + "/%s.md" % OPEN],
                cwd=self.root,
            )
        edited = support.read(older) + "\nA line of my own.\n"
        support.write(older, edited)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(edited, support.read(older))


# --- Edge: a file already where another would go -------------------------------


class TestNothingIsEverOverwritten(LayoutCase):
    """Edge case: a different file at a new path is a named refusal."""

    def test_a_different_profile_at_the_new_path(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        self.put(
            ICP,
            "---\nkind: icp\nowner: %s\nsources: []\nstatus: draft\n---\n\n# Mine\n"
            % OWNER,
        )
        self.save("a second profile")
        head = support.head_of(self.root)
        before = support.read(os.path.join(self.root, ICP))

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_DOCUMENT_TAKEN, result.code)
        self.assertIn("your customer profile", result.sentence)
        self.assertNotIn("context/", result.sentence)
        self.assertEqual(head, support.head_of(self.root))
        self.assertEqual(before, support.read(os.path.join(self.root, ICP)))
        self.assertTrue(os.path.isfile(os.path.join(self.root, OLD_ICP)))
        # And the review does not offer a move that would be refused.
        self.assertFalse(any(changes.is_the_offer(line) for line in self.review().sentences))

    def test_a_different_record_of_the_same_name(self):
        self.with_a_caught_change_fixed_by_a_record()
        name = "%s-%s.md" % (TODAY.isoformat(), FIXED)
        self.put(constants.CORRECTIONS_DIR + "/" + name, "something else\n")
        self.save("a second record")
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.CODE_DESTINATION_TAKEN, result.code)
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.root, constants.LEGACY_CORRECTIONS_DIR, name)
            )
        )

    def test_the_same_file_in_both_places_leaves_one_copy(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        self.put(ICP, support.read(os.path.join(self.root, OLD_ICP)))
        self.save("a copy somebody made")
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status, result.sentence)
        self.assertFalse(os.path.exists(os.path.join(self.root, OLD_ICP)))
        self.assertTrue(os.path.isfile(os.path.join(self.root, ICP)))


# --- Edge: the record of context changes, all three folders ------------------


class TestTheRecordOfChangesAcrossThreeFolders(LayoutCase):
    """Edge case: every id kept, every entry read, the catches counted the same."""

    def test_every_entry_is_read_from_all_three_folders(self):
        self.put(
            constants.LEGACY_CHANGES_DIR + "/%s.md" % SETTLED,
            entry_text(SETTLED, [OLD_ICP], older=True),
        )
        self.put(
            constants.WORK_CHANGES_DIR + "/%s.md" % OPEN, entry_text(OPEN, [OLD_ICP])
        )
        self.put(constants.CHANGES_DIR + "/%s.md" % FIXED, entry_text(FIXED, [ICP]))
        self.save("one in each folder")

        read = sorted(
            row.entry.id
            for row in base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
            if row.entry is not None
        )
        self.assertEqual(sorted([SETTLED, OPEN, FIXED]), read)
        # Every one of them is about the profile, wherever each names it.
        for row in base_reader.ledger(self.root, self.base_id, TODAY, collect=[]):
            self.assertEqual([OLD_ICP], list(row.entry.affects))

        changes.migrate(self.root, self.base_id, today=TODAY)

        after = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        self.assertEqual(sorted([SETTLED, OPEN, FIXED]), sorted(r.entry.id for r in after))
        for row in after:
            self.assertEqual([ICP], list(row.entry.affects))
            self.assertTrue(row.path.startswith(constants.CHANGES_DIR + "/"))

    def test_the_catches_are_counted_the_same_before_and_after(self):
        self.with_a_caught_change_fixed_by_a_record(constants.LEGACY_CHANGES_DIR)
        runner = GitRunner()
        before = report.catches(self.root, runner, TODAY)
        self.assertEqual(1, before["count"])
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(before["count"], report.catches(self.root, runner, TODAY)["count"])

    def test_a_change_the_move_carried_is_still_found_by_every_step(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        changes.migrate(self.root, self.base_id, today=TODAY)
        relative, text = base_reader.entry_path_and_text(self.root, OPEN)
        self.assertEqual(constants.CHANGES_DIR + "/%s.md" % OPEN, relative)
        self.assertIsNotNone(text)
        # A new change is written where the current layout keeps them.
        self.assertEqual(
            constants.CHANGES_DIR + "/%s.md" % FIXED,
            base_reader.where_to_write_the_entry(self.root, FIXED),
        )


# --- Security: the skills folder -------------------------------------------------


class TestTheSkillsFolderIsRefused(unittest.TestCase):
    """Security: a file under skills is refused however it arrives."""

    def test_by_the_trust_check_which_every_pull_and_every_open_asks(self):
        with support.Sandbox() as sandbox:
            root = support.trust_checkout(sandbox.path)
            self.assertTrue(trust_surface.check(root).ok)

            support.write(os.path.join(root, "skills", constants.PLACEHOLDER_NAME), "")
            self.assertTrue(trust_surface.check(root).ok)

            support.write(os.path.join(root, "skills", "outbound", "SKILL.md"), "do it\n")
            verdict = trust_surface.check(root)
            self.assertFalse(verdict.ok)
            self.assertIn(trust_surface.CODE_SKILLS_FILE, verdict.codes)

    def test_by_the_update_from_the_shared_copy(self):
        refused = session_start._is_refused_path
        # Plan 1, Unit 4.2b admits a skill's own shapes by name; what such a
        # file holds is read separately (tests/test_skills_folder.py).
        self.assertFalse(refused("skills/outbound/SKILL.md"))
        self.assertTrue(refused("skills/outbound/run.py"))
        self.assertTrue(refused("skills/notes.md"))
        self.assertTrue(refused("Skills/notes.md"))
        self.assertFalse(refused("skills/" + constants.PLACEHOLDER_NAME))
        self.assertFalse(refused("context/skills.md"))
        self.assertFalse(refused("standards/outbound.md"))

    def test_by_the_file_writing_tools(self):
        with support.Sandbox() as sandbox:
            base = sandbox.base()[0]
            inside = os.path.join(base, "skills", "outbound", "SKILL.md")
            answer = write_hook.run(
                {"tool_name": "Write", "tool_input": {"file_path": inside}}
            )
            self.assertEqual(
                "deny", answer["hookSpecificOutput"]["permissionDecision"]
            )
            self.assertEqual(
                write_hook.SKILLS_REFUSED,
                answer["hookSpecificOutput"]["permissionDecisionReason"],
            )
            placeholder = os.path.join(base, "skills", constants.PLACEHOLDER_NAME)
            self.assertIsNone(
                write_hook.run(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": placeholder, "content": ""},
                    }
                )
            )
            # A skills folder anywhere else on the computer is not ours.
            elsewhere = os.path.join(sandbox.path, "home", "skills", "x.md")
            self.assertIsNone(
                write_hook.run(
                    {"tool_name": "Write", "tool_input": {"file_path": elsewhere}}
                )
            )

    def test_by_the_check_before_a_send(self):
        with support.Sandbox() as sandbox:
            root = sandbox.base()[0]
            start = support.head_of(root)
            support.write(
                os.path.join(root, "skills", constants.PLACEHOLDER_NAME), ""
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the empty folder"], cwd=root)
            self.assertIsNone(
                gate.scan_range(GitRunner(), root, start, support.head_of(root))
            )
            middle = support.head_of(root)
            support.write(os.path.join(root, "skills", "outbound.md"), "steps\n")
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "a skill"], cwd=root)
            said = gate.scan_range(GitRunner(), root, middle, support.head_of(root))
            self.assertEqual(gate.sentence_for(gate.REASON_SKILLS_FILE), said)

    def test_every_sentence_is_plain(self):
        for sentence in (
            write_hook.SKILLS_REFUSED,
            gate.sentence_for(gate.REASON_SKILLS_FILE),
        ):
            self.assertEqual([], plain_language.find_banned(sentence))
            self.assertEqual([], plain_language.find_dashes(sentence))
            self.assertEqual([], plain_language.find_old_paths(sentence))


# --- Happy path: the source map holds no credential -----------------------------


class TestTheSourceMapHoldsNoCredential(unittest.TestCase):
    """Happy path: access/stack.md is clean, and a key in it is refused."""

    def test_the_template_passes_the_screens_a_proposal_gets(self):
        for root in (support.REPO_ROOT, support.PLUGIN_DIR):
            template = os.path.join(root, "templates", "company-base")
            text = support.read(os.path.join(template, "access", "stack.md"))
            # The owner's address is the one thing the base's own list lets
            # through, exactly as it does for every document in a base.
            allowlist, _code = scan.load_allowlist(template)
            self.assertEqual([], scan.scan_text(text, allowlist, "the source map"))
            self.assertIn("never holds a password, a key, or a token", text)

    def test_a_line_shaped_like_a_key_is_refused_by_those_screens(self):
        path = os.path.join(
            support.REPO_ROOT, "templates", "company-base", "access", "stack.md"
        )
        text = support.read(path) + "\nCRM key: sk-" + "a1B2c3D4e5F6g7H8i9J0k1L2" + "\n"
        allowlist, _code = scan.load_allowlist(os.path.dirname(os.path.dirname(path)))
        self.assertTrue(scan.scan_text(text, allowlist, "the source map"))

    def test_a_send_carrying_a_key_in_the_source_map_is_refused(self):
        with support.Sandbox() as sandbox:
            root = sandbox.base()[0]
            start = support.head_of(root)
            support.write(
                os.path.join(root, constants.STACK_PATH),
                "# Stack\n\nCRM token: ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8" + "\n",
            )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "the source map"], cwd=root)
            self.assertIsNotNone(
                gate.scan_range(GitRunner(), root, start, support.head_of(root))
            )


# --- Edge: every step on a moved base, and a change staged before the move ------


class TestEveryStepOnAMovedBase(LayoutCase):
    """Edge case: a hand edit, a local approval, and the read check all work."""

    def test_a_change_prepared_before_the_move_is_still_accepted(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        run = stale_check.run(
            self.root, self.base_id, gh=support.RecordingGh(), now=TODAY,
            session_id="sess-1",
        )
        prepared = [item for item in run.staged if item.entry_id == OPEN]
        self.assertEqual(1, len(prepared), run.lines())
        staged_text = support.read(prepared[0].path)
        self.assertIn(OLD_ICP, staged_text)
        support.write_the_replacement(
            prepared[0].path, "We sell to companies of twenty to two hundred people.\n"
        )

        moved = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, moved.status, moved.sentence)
        self.assertIn(OLD_ICP, support.read(prepared[0].path))

        shown = approve_local.show(prepared[0].path, self.root, self.base_id, now=TODAY)
        self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
        applied = approve_local.approve(
            prepared[0].path, self.root, self.base_id, shown.shown_hash,
            now=datetime.datetime(2026, 9, 20, 12, 0, 0),
        )
        self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)
        self.assertIn(
            "twenty to two hundred", support.read(os.path.join(self.root, ICP))
        )
        self.assertFalse(os.path.exists(os.path.join(self.root, OLD_ICP)))
        # The record of it is written where the current layout keeps records.
        self.assertTrue(
            any(
                name.endswith(prepared[0].staging_id + ".md")
                for name in self.listing(constants.CORRECTIONS_DIR)
            )
        )
        settled = moment.check(self.root, self.base_id, ICP, session_id="sess-2", now=TODAY)
        self.assertFalse(settled.flagged, settled.sentences())

    def test_a_hand_edit_on_a_moved_base(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        changes.migrate(self.root, self.base_id, today=TODAY)
        path = os.path.join(self.root, ICP)
        support.write(
            path, support.read(path).replace("Companies of any size.", "Teams of ten.")
        )
        staged = compose_proposal.stage_local_edit(
            self.root,
            self.base_id,
            "The quarterly review deck, slide four, said so.",
            runner=support.NoRemoteRunner(),
            now=TODAY,
        )
        self.assertIn(
            [ICP], [compose_proposal.load_staging(staged).target_paths]
        )
        shown = approve_local.show(staged, self.root, self.base_id, now=TODAY)
        self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
        applied = approve_local.approve(
            staged, self.root, self.base_id, shown.shown_hash,
            now=datetime.datetime(2026, 9, 20, 12, 0, 0),
        )
        self.assertEqual(approve_local.STATUS_APPLIED, applied.status, applied.reasons)

    def test_the_read_check_on_a_moved_base(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        from gtmbase import machine, state

        changes.migrate(self.root, self.base_id, today=TODAY)
        state.update_seat(self.base_id, session_id="sess-1")
        said = read_hook.run(
            {
                "session_id": "sess-1",
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": os.path.join(self.root, ICP)},
            },
            now=TODAY,
            runner=support.NoRemoteRunner(),
        )
        self.assertIsNotNone(said)
        self.assertIn("your customer profile", json.dumps(said))

    def test_the_check_at_use_follows_an_older_name_to_the_document(self):
        self.with_changes(constants.WORK_CHANGES_DIR)
        changes.migrate(self.root, self.base_id, today=TODAY)
        flag = moment.check(self.root, self.base_id, OLD_ICP, session_id="sess-1", now=TODAY)
        self.assertTrue(flag.flagged, flag.sentences())
        self.assertEqual(ICP, flag.path)


# --- The layout itself --------------------------------------------------------


class TestTheLayout(unittest.TestCase):
    """The table from each older path to its new one, and the templates."""

    def test_each_older_document_path_has_one_current_path(self):
        self.assertEqual(ICP, layout.current_of(OLD_ICP))
        self.assertEqual(POSITIONING, layout.current_of(OLD_POSITIONING))
        self.assertEqual("context/goals.md", layout.current_of("context/plan/goals.md"))
        self.assertEqual(
            "context/metrics.md", layout.current_of("context/metrics/definitions.md")
        )
        self.assertEqual(
            "context/icps/mid-market.md",
            layout.current_of("context/strategy/segments/mid-market.md"),
        )
        self.assertEqual(OLD_ICP, layout.older_of(ICP))
        self.assertIsNone(layout.current_of("context/notes/idea.md"))
        self.assertIsNone(layout.current_of(ICP))

    def test_every_current_path_is_a_file_of_the_standard(self):
        for _older, current in constants.LEGACY_DOCUMENT_PATHS:
            self.assertIn(current, constants.CONTEXT_STANDARD_FILES)
        self.assertEqual(9, len(constants.CONTEXT_STANDARD_FILES))
        self.assertEqual(
            tuple(constants.REQUIRED_CONTEXT_FILES), (ICP, POSITIONING)
        )

    def test_every_file_of_the_standard_has_a_plain_name(self):
        for relative in constants.CONTEXT_STANDARD_FILES + (constants.STACK_PATH,):
            name = names.document_name(relative)
            self.assertTrue(name.startswith("your "), name)
            self.assertNotIn("/", name)
        for older, current in constants.LEGACY_DOCUMENT_PATHS:
            self.assertEqual(names.document_name(current), names.document_name(older))

    def test_both_templates_hold_the_five_parts_and_the_approvals(self):
        for root in (support.REPO_ROOT, support.PLUGIN_DIR):
            template = os.path.join(root, "templates", "company-base")
            for relative in (
                ICP,
                constants.MAP_PATH,
                constants.STACK_PATH,
                constants.CHANGES_DIR + "/" + constants.PLACEHOLDER_NAME,
                constants.CORRECTIONS_DIR + "/" + constants.PLACEHOLDER_NAME,
                constants.LESSONS_DIR + "/" + constants.PLACEHOLDER_NAME,
                constants.SKILLS_DIR + "/" + constants.PLACEHOLDER_NAME,
                constants.STANDARDS_DIR + "/" + constants.PLACEHOLDER_NAME,
            ):
                self.assertTrue(
                    os.path.isfile(os.path.join(template, relative)), (root, relative)
                )
            for older in ("context/strategy", "work/changes", "corrections"):
                self.assertFalse(
                    os.path.exists(os.path.join(template, older)), (root, older)
                )
            self.assertEqual(
                ["." + "gitkeep"], sorted(os.listdir(os.path.join(template, "skills")))
            )

    def test_the_map_paragraph_the_move_writes_is_the_templates_own(self):
        text = support.read(
            os.path.join(support.REPO_ROOT, "templates", "company-base", "context", "map.md")
        )
        self.assertIn(changes.MAP_WHERE_HEADING + "\n\n" + changes.MAP_WHERE_TODAY, text)

    def test_a_base_on_the_older_layout_finds_both_required_documents(self):
        with support.Sandbox() as sandbox:
            root, _base_id = migration.build_base(sandbox)
            self.assertEqual(
                (OLD_ICP, OLD_POSITIONING), layout.required_paths(root)
            )
            self.assertEqual((ICP, POSITIONING), layout.required_paths(sandbox.path))


# --- Lint: no text a person reads names an old path ---------------------------


class TestNoTextAPersonReadsNamesAnOldPath(unittest.TestCase):
    """Lint: the sentences, the skills, the templates, and the join guide."""

    def person_facing_files(self):
        found = []
        skills = os.path.join(support.PLUGIN_DIR, "skills")
        for top, _folders, files in os.walk(skills):
            for name in files:
                if name.endswith(".md"):
                    found.append(os.path.join(top, name))
        for root in (
            os.path.join(support.PLUGIN_DIR, "templates"),
            os.path.join(support.REPO_ROOT, "templates", "company-base"),
        ):
            for top, _folders, files in os.walk(root):
                for name in files:
                    if name.endswith((".md", ".json")) or name == "CODEOWNERS":
                        found.append(os.path.join(top, name))
        found.append(os.path.join(support.REPO_ROOT, "docs", "join-guide.md"))
        return found

    def test_no_file_a_person_reads_names_one(self):
        for path in self.person_facing_files():
            with self.subTest(path=path):
                self.assertEqual(
                    [], plain_language.find_old_paths(support.read(path)), path
                )

    def test_no_registered_sentence_names_one(self):
        import importlib

        for module_name, constant in plain_language.PYTHON_SENTENCES:
            value = getattr(importlib.import_module("gtmbase." + module_name), constant)
            with self.subTest(sentence=constant):
                self.assertEqual([], plain_language.find_old_paths(value))

    def test_the_check_catches_every_older_path(self):
        for older in (
            "context/strategy/icp.md",
            "context/plan/goals.md",
            "context/metrics/definitions.md",
            "context/notes",
            "work/changes",
            "work/decisions",
            "the `corrections` folder",
            "corrections/2026-01-01.md",
        ):
            self.assertTrue(plain_language.find_old_paths("See %s here." % older), older)
        for current in (
            "context/icps.md",
            "learning/changes",
            "learning/corrections/2026-01-01.md",
            "the corrections a person accepted",
        ):
            self.assertEqual([], plain_language.find_old_paths("See %s." % current))


if __name__ == "__main__":
    unittest.main()
