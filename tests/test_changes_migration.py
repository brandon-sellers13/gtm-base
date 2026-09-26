"""Moving a base from `work/decisions` to `work/changes`, and picking it up again.

Every test here builds a base the shape the one real base is: a repository with
the map, the two required documents, and entries in the older folder. Nothing
here reaches the person's own home folder, their git settings, or a real base.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plain_language  # noqa: E402
import support  # noqa: E402

from gtmbase import base_reader, changes, constants, formats, report  # noqa: E402
from gtmbase.errors import GitError, ValidationError  # noqa: E402
from gtmbase.gitcmd import GitRunner  # noqa: E402

TODAY = datetime.date(2026, 9, 20)

OWNER = "owner@example.com"
SOURCE = "src-f9b4fc4d3b3d46561948ee51"

ENTRY_ONE = "stg-0d15637d82690cc7"
ENTRY_TWO = "stg-1d15637d82690cc8"
ENTRY_THREE = "stg-2d15637d82690cc9"


def old_entry(entry_id, body="We now sell to companies of twenty to two hundred people."):
    """One entry in the layout a base written before the rename holds."""
    return (
        "---\n"
        "id: %s\n"
        "kind: decision\n"
        "decided_on: 2026-01-12\n"
        "written_on: 2026-01-12\n"
        "decided_by: %s\n"
        "source: %s\n"
        "affects: [context/strategy/icp.md]\n"
        "review_by: 2026-04-12\n"
        "origin: inbox\n"
        "status: open\n"
        "---\n"
        "\n"
        "%s\n" % (entry_id, OWNER, SOURCE, body)
    )


def new_entry(entry_id, body="We now sell to companies of twenty to two hundred people."):
    """The same entry in the layout every writer writes today."""
    return (
        "---\n"
        "id: %s\n"
        "kind: change\n"
        "happened_on: 2026-01-12\n"
        "written_on: 2026-01-12\n"
        "noted_by: %s\n"
        "source: %s\n"
        "affects: [context/strategy/icp.md]\n"
        "review_by: 2026-04-12\n"
        "origin: inbox\n"
        "status: open\n"
        "---\n"
        "\n"
        "%s\n" % (entry_id, OWNER, SOURCE, body)
    )


class _StopAfter(object):
    """A real runner that stops the run at a chosen moment.

    It is how a failure is injected: the work up to that point really happened
    on the disk, and what comes next never ran at all, which is what a process
    killed at that moment leaves behind.

    The first version of this only ever stopped at a commit, which is why two
    critical findings went unnoticed. It now also stops between two file moves,
    which is where a base can be left with half its entries in each folder.
    """

    def __init__(
        self,
        stop_after_subject=None,
        stop_before_subject=None,
        stop_before_move=None,
        stop_after_move=None,
    ):
        self.inner = GitRunner()
        self.stop_after = stop_after_subject
        self.stop_before = stop_before_subject
        self.stop_before_move = stop_before_move
        self.stop_after_move = stop_after_move
        self.moves = 0

    def _is_commit_of(self, args, subject):
        return subject is not None and "commit" in args and subject in args

    def run(self, args, cwd=None, timeout=20, input=None):
        arguments = [str(item) for item in args]
        if self._is_commit_of(arguments, self.stop_before):
            raise _Stopped()
        moving = bool(arguments) and arguments[0] == "mv"
        if moving:
            self.moves += 1
            if self.moves == self.stop_before_move:
                raise _Stopped()
        result = self.inner.run(arguments, cwd=cwd, timeout=timeout, input=input)
        if moving and self.moves == self.stop_after_move:
            raise _Stopped()
        if self._is_commit_of(arguments, self.stop_after):
            raise _Stopped()
        return result

    def check(self, args, cwd=None, timeout=20, input=None):
        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result


class _StopOnWrite(object):
    """Kill the run part way through writing files, not at a git call.

    The rewrite writes every file and only then hands them to git, and the
    record is written before it is saved. A process killed between two of those
    writes leaves a state no git call can describe, so it is injected by
    standing in front of the one function that does the writing.
    """

    def __init__(self, after=1):
        self.after = after
        self.written = 0
        self.real = None

    def __enter__(self):
        self.real = changes.atomic_write_text

        def watched(*arguments, **options):
            self.written += 1
            if self.written > self.after:
                raise _Stopped()
            written = self.real(*arguments, **options)
            if self.written == self.after:
                # The write really happened and then the run died, which is
                # the state a file on the disk with nothing saved about it.
                raise _Stopped()
            return written

        changes.atomic_write_text = watched
        return self

    def __exit__(self, kind, value, trace):
        changes.atomic_write_text = self.real
        return False



class _FailOn(object):
    """A real runner with chosen commands failing instead of running.

    It is how an index somebody else has locked is injected: the command is
    refused, nothing happens, and the run has to deal with that honestly.
    """

    def __init__(self, words):
        self.inner = GitRunner()
        self.words = tuple(words)

    def run(self, args, cwd=None, timeout=20, input=None):
        arguments = [str(item) for item in args]
        if arguments and arguments[0] in self.words:
            return _Failed()
        return self.inner.run(arguments, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result


class _FailOnCommit(object):
    """A real runner where saving one named piece of work fails."""

    def __init__(self, subject):
        self.inner = GitRunner()
        self.subject = subject

    def run(self, args, cwd=None, timeout=20, input=None):
        arguments = [str(item) for item in args]
        if "commit" in arguments and self.subject in arguments:
            return _Failed()
        return self.inner.run(arguments, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result


class _Failed(object):
    """What a command that was refused rather than run comes back as."""

    ok = False
    code = 1
    stdout = ""
    stderr = "refused for this test"

    def out(self):
        return ""


class _Stopped(Exception):
    """The run was killed at a chosen moment."""



def build_base(sandbox):
    """A base shaped the way the one real base is, built the same way twice.

    Every comparison against an uninterrupted run builds a second base with
    this, so a difference between the two is a difference the migration made
    and never a difference in how the two were set up.
    """
    root, base_id = sandbox.base()
    support.write(
        os.path.join(root, "context", "strategy", "positioning.md"),
        "---\nkind: positioning\nowner: %s\nlast_confirmed: 2026-01-12\n"
        "sources: []\nstatus: approved\n---\n\n# Positioning\n\nWe sell to "
        "mid sized teams.\n" % OWNER,
    )
    # The two folders that belong to one seat and are never shared. A real
    # base is built with these already ignored, and without them every run
    # that prepares a change leaves the base looking edited.
    support.write(
        os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n"
    )
    support.git(["add", "-A"], cwd=root)
    support.git(["commit", "-q", "-m", "positioning"], cwd=root)
    # The one real base has no shared copy, so neither does this one. A test
    # that is about a base other people can reach puts one back itself.
    support.git(["remote", "remove", "origin"], cwd=root)
    return root, base_id


def give_it_a_shared_copy(sandbox, root, name="shared"):
    """Point this base at a copy other people could reach."""
    remote = os.path.join(sandbox.path, name + "-origin.git")
    if not os.path.isdir(remote):
        support.git(["init", "--bare", "-q", "-b", "main", remote], cwd=sandbox.path)
    support.git(["remote", "add", "origin", remote], cwd=root)
    support.git(["push", "-q", "-u", "origin", "main"], cwd=root)
    return remote


def state_of(root, base_id):
    """Everything about one base that an interrupted run must not change.

    It is a module-level helper because more than one test class compares a
    base against an uninterrupted run, and a comparison that leaves something
    out is the reason two critical findings were missed.
    """
    from gtmbase import stale

    rows = base_reader.ledger(root, base_id, TODAY, collect=[])
    entries = {}
    problems = []
    for row in rows:
        if row.entry is None:
            problems.append((row.path, row.error))
            continue
        entries[row.entry.id] = (
            row.entry.body,
            row.entry.happened_on,
            row.entry.noted_by,
            row.entry.status,
            tuple(row.entry.affects),
        )

    def listing(folder):
        where = os.path.join(root, folder.replace("/", os.sep))
        if not os.path.isdir(where):
            return None
        return sorted(os.listdir(where))

    confirmations = {}
    folder = os.path.join(root, constants.CONFIRMATIONS_DIR)
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            confirmations[name] = support.read(os.path.join(folder, name))

    inputs = base_reader.read_base(root, base_id, today=TODAY)
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
        (flag.path, flag.trigger, tuple(sorted(flag.entry_ids)))
        for flag in computed.file_flags
    )
    runner = GitRunner()
    return {
        "entries": entries,
        "problems": sorted(problems),
        "changes": listing(constants.CHANGES_DIR),
        "decisions": listing(constants.LEGACY_CHANGES_DIR),
        "corrections": [
            name
            for name in (listing(constants.CORRECTIONS_DIR) or [])
            if name.endswith(".md")
        ],
        "confirmations": confirmations,
        "flags": flags,
        "review_by": sorted(item.entry_id for item in computed.review_by_items),
        "unsaved": runner.run(["status", "--porcelain"], cwd=root).stdout,
        "staged": runner.run(
            ["diff", "--cached", "--name-status"], cwd=root
        ).stdout,
    }


class MigrationCase(unittest.TestCase):
    """One base, built the same way every time, with entries where a test wants."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.root, self.base_id = build_base(self.sandbox)

    def put(self, folder, entry_id, text):
        support.write(
            os.path.join(self.root, folder.replace("/", os.sep), entry_id + ".md"),
            text,
        )

    def save(self, message="entries"):
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", message], cwd=self.root)

    def old_layout(self, entry_ids=(ENTRY_ONE,)):
        for entry_id in entry_ids:
            self.put(constants.LEGACY_CHANGES_DIR, entry_id, old_entry(entry_id))
        self.save()

    def entries_now(self):
        """Every context change the base reads, by identifier."""
        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        return {row.entry.id: row.entry for row in rows if row.entry is not None}

    def problems_now(self):
        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        return [(row.path, row.error) for row in rows if row.entry is None]

    def files_in(self, folder):
        path = os.path.join(self.root, folder.replace("/", os.sep))
        if not os.path.isdir(path):
            return []
        return sorted(name for name in os.listdir(path) if name.endswith(".md"))

    def corrections(self):
        folder = os.path.join(self.root, constants.CORRECTIONS_DIR)
        if not os.path.isdir(folder):
            return []
        return sorted(name for name in os.listdir(folder) if name.endswith(".md"))


# --- The reader, which comes before anything is moved ------------------------


class TestBothLayoutsAreRead(MigrationCase):
    def test_an_old_layout_base_is_read_with_nothing_moved(self):
        self.old_layout()
        entries = self.entries_now()
        self.assertEqual([ENTRY_ONE], sorted(entries))
        self.assertEqual("2026-01-12", entries[ENTRY_ONE].happened_on)
        self.assertEqual(OWNER, entries[ENTRY_ONE].noted_by)

    def test_an_old_layout_entry_inside_the_new_folder_is_read(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        entries = self.entries_now()
        self.assertEqual([ENTRY_ONE], sorted(entries))
        self.assertEqual(OWNER, entries[ENTRY_ONE].noted_by)

    def test_both_folders_holding_different_entries_returns_all_of_them(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))
        self.assertEqual([], self.problems_now())

    def test_the_same_entry_in_both_folders_saying_the_same_thing_is_one_entry(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        self.assertEqual([ENTRY_ONE], sorted(self.entries_now()))
        self.assertEqual([], self.problems_now())

    def test_the_same_entry_saying_two_different_things_is_a_problem_and_neither_wins(
        self,
    ):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE, "One thing."))
        self.put(
            constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE, "Another thing.")
        )
        self.save()
        self.assertEqual({}, self.entries_now())
        # Both copies are named, because a person told only that something is
        # written twice still has to find the second file themselves.
        self.assertEqual(
            [
                (
                    constants.CHANGES_DIR + "/" + ENTRY_ONE + ".md",
                    base_reader.CODE_IN_BOTH_FOLDERS,
                ),
                (
                    constants.LEGACY_CHANGES_DIR + "/" + ENTRY_ONE + ".md",
                    base_reader.CODE_IN_BOTH_FOLDERS,
                ),
            ],
            sorted(self.problems_now()),
        )

    def test_a_refusal_then_a_writer_making_the_new_folder_hides_nothing(self):
        # The case Astra named: the migration refuses, something else creates
        # the newer folder, and a reader that stopped at the first folder it
        # found would ignore every older entry from that moment on.
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, "---\nkind: change\n---\nbroken\n")
        self.save()
        refused = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, refused.status)
        self.assertEqual([ENTRY_ONE + ".md", ENTRY_TWO + ".md"],
                         self.files_in(constants.LEGACY_CHANGES_DIR))

        self.put(constants.CHANGES_DIR, ENTRY_THREE, new_entry(ENTRY_THREE))
        self.save("a writer made the new folder")
        self.assertEqual([ENTRY_ONE, ENTRY_THREE], sorted(self.entries_now()))


# --- The move itself ----------------------------------------------------------


class TestMigrating(MigrationCase):
    def test_three_entries_move_keep_their_ids_and_are_rewritten(self):
        self.old_layout((ENTRY_ONE, ENTRY_TWO, ENTRY_THREE))
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status)
        self.assertEqual(
            [ENTRY_ONE, ENTRY_TWO, ENTRY_THREE], sorted(result.entry_ids)
        )
        self.assertEqual([], self.files_in(constants.LEGACY_CHANGES_DIR))
        self.assertEqual(
            [ENTRY_ONE + ".md", ENTRY_TWO + ".md", ENTRY_THREE + ".md"],
            self.files_in(constants.CHANGES_DIR),
        )
        for entry_id in (ENTRY_ONE, ENTRY_TWO, ENTRY_THREE):
            text = support.read(
                os.path.join(self.root, constants.CHANGES_DIR, entry_id + ".md")
            )
            self.assertIn("kind: change", text)
            self.assertIn("happened_on: 2026-01-12", text)
            self.assertIn("noted_by: " + OWNER, text)
            self.assertNotIn("decided_on", text)
            self.assertNotIn("decided_by", text)
        self.assertEqual(
            [ENTRY_ONE, ENTRY_TWO, ENTRY_THREE], sorted(self.entries_now())
        )

    def test_the_move_and_the_rewrite_are_two_separate_saved_changes(self):
        self.old_layout()
        before = support.head_of(self.root)
        changes.migrate(self.root, self.base_id, today=TODAY)
        saved = GitRunner().run(
            ["log", "--format=%s", before + "..HEAD"], cwd=self.root
        ).stdout.strip().split("\n")
        self.assertEqual(
            [changes.RECORD_SUBJECT, changes.REWRITE_SUBJECT, changes.MOVE_SUBJECT],
            [line.strip() for line in saved],
        )

    def test_the_record_it_leaves_parses_as_a_corrections_file(self):
        self.old_layout()
        changes.migrate(self.root, self.base_id, today=TODAY)
        written = self.corrections()
        self.assertEqual(1, len(written))
        text = support.read(
            os.path.join(self.root, constants.CORRECTIONS_DIR, written[0])
        )
        parsed = formats.CorrectionsFile.parse(text)
        parsed.validate()
        self.assertEqual(TODAY.isoformat(), parsed.date)
        self.assertIn(constants.CHANGES_DIR + "/" + ENTRY_ONE + ".md",
                      parsed.touched_paths)

    def test_running_it_again_changes_nothing(self):
        self.old_layout()
        changes.migrate(self.root, self.base_id, today=TODAY)
        after = support.head_of(self.root)
        again = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_NOT_NEEDED, again.status)
        self.assertEqual(after, support.head_of(self.root))

    def test_a_base_already_in_the_new_layout_is_left_alone(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.save()
        before = support.head_of(self.root)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_NOT_NEEDED, result.status)
        self.assertEqual(changes.NOTHING_TO_MOVE, result.sentence)
        self.assertEqual(before, support.head_of(self.root))

    def test_both_folders_with_no_clash_moves_only_what_is_still_in_the_old_one(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status)
        self.assertEqual([ENTRY_TWO], result.entry_ids)
        self.assertEqual([], self.files_in(constants.LEGACY_CHANGES_DIR))
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def test_the_same_id_in_both_folders_disagreeing_is_refused_by_name(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE, "One thing."))
        self.put(
            constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE, "Another thing.")
        )
        self.save()
        before = support.head_of(self.root)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(base_reader.CODE_IN_BOTH_FOLDERS, result.code)
        self.assertIn(ENTRY_ONE, result.sentence)
        self.assertEqual(before, support.head_of(self.root))

    def test_an_entry_nothing_can_read_is_refused_and_nothing_moves(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, "not a settings block at all\n")
        self.save()
        before = support.head_of(self.root)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNREADABLE_ENTRY, result.code)
        self.assertEqual(before, support.head_of(self.root))
        self.assertEqual(
            [ENTRY_ONE + ".md", ENTRY_TWO + ".md"],
            self.files_in(constants.LEGACY_CHANGES_DIR),
        )

    def test_a_tree_the_person_dirtied_is_refused_with_one_sentence(self):
        self.old_layout()
        support.write(
            os.path.join(self.root, "context", "strategy", "icp.md"),
            "---\nkind: icp\nowner: %s\nlast_confirmed: 2026-01-12\nsources: []\n"
            "status: approved\n---\n\n# Profile\n\nHalf a sentence the person is "
            "still writing.\n" % OWNER,
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertEqual(changes.UNSAVED_EDITS, result.sentence)
        self.assertEqual([ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR))


# --- A run that stopped -------------------------------------------------------


class TestStoppingPartway(MigrationCase):
    """A failure after each mutation in turn, against an uninterrupted run."""

    def uninterrupted(self, entries=None):
        """What a run that never stopped leaves behind, as plain values.

        The second base is built by the same helper the first one is, so the
        only difference between the two can be what the migration did.
        """
        rows = entries or (
            (ENTRY_ONE, old_entry(ENTRY_ONE)),
            (
                ENTRY_TWO,
                old_entry(ENTRY_TWO, "We stopped calling on the smallest accounts."),
            ),
        )
        with support.Sandbox() as other:
            root, base_id = build_base(other)
            for entry_id, text in rows:
                support.write(
                    os.path.join(
                        root, constants.LEGACY_CHANGES_DIR, entry_id + ".md"
                    ),
                    text,
                )
            support.git(["add", "-A"], cwd=root)
            support.git(["commit", "-q", "-m", "entries"], cwd=root)
            changes.migrate(root, base_id, today=TODAY)
            return state_of(root, base_id)

    def state_of(self, root, base_id):
        """Everything a retry has to leave the same as an uninterrupted run.

        The first version of this compared entries and folder listings only,
        which is how a retry that staged a deletion, left the index dirty, or
        quietly unflagged a document could still look identical. It now also
        compares the confirmations, the flags the stale rules compute, what git
        says is unsaved, and what is staged.
        """
        return state_of(root, base_id)

    def two_entries(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.LEGACY_CHANGES_DIR,
            ENTRY_TWO,
            old_entry(ENTRY_TWO, "We stopped calling on the smallest accounts."),
        )
        self.save()

    def stop(self, after=None, before=None, before_move=None, after_move=None):
        runner = _StopAfter(
            stop_after_subject=after,
            stop_before_subject=before,
            stop_before_move=before_move,
            stop_after_move=after_move,
        )
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def stop_on_write(self, after=1):
        with _StopOnWrite(after=after):
            try:
                changes.migrate(self.root, self.base_id, today=TODAY)
            except _Stopped:
                return
        self.fail("the run was meant to stop and did not")

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def test_stopping_before_the_move_is_saved_puts_everything_back(self):
        self.two_entries()
        before = support.head_of(self.root)
        self.stop(before=changes.MOVE_SUBJECT)
        self.assertTrue(os.path.exists(self.note_path()))
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))
        self.assertNotEqual(before, support.head_of(self.root))

    def test_stopping_after_the_move_is_saved_finishes_the_rest(self):
        self.two_entries()
        self.stop(after=changes.MOVE_SUBJECT)
        self.assertTrue(os.path.exists(self.note_path()))
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_RESUMED, result.status)
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_stopping_after_the_rewrite_is_saved_finishes_the_record(self):
        self.two_entries()
        self.stop(after=changes.REWRITE_SUBJECT)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_RESUMED, result.status)
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_stopping_after_the_record_is_saved_only_takes_the_note_away(self):
        self.two_entries()
        self.stop(after=changes.RECORD_SUBJECT)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_a_run_its_own_note_dirtied_is_not_blocked_from_trying_again(self):
        self.two_entries()
        self.stop(before=changes.MOVE_SUBJECT)
        dirty = GitRunner().run(["status", "--porcelain"], cwd=self.root).stdout
        self.assertTrue(dirty.strip(), "the stopped run was meant to leave the tree dirty")
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)

    def test_the_persons_own_edit_on_a_path_the_run_wrote_keeps_the_note(self):
        self.two_entries()
        self.stop(before=changes.MOVE_SUBJECT)
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md"),
            "their own words, not ours\n",
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertTrue(os.path.exists(self.note_path()))
        self.assertEqual(
            "their own words, not ours\n",
            support.read(
                os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
            ),
        )

    def test_stopping_between_two_moves_leaves_nothing_in_neither_folder(self):
        self.two_entries()
        self.stop(after_move=1)

        somewhere = self.files_in(constants.CHANGES_DIR) + self.files_in(
            constants.LEGACY_CHANGES_DIR
        )
        self.assertEqual(
            [ENTRY_ONE + ".md", ENTRY_TWO + ".md"], sorted(somewhere)
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_stopping_part_way_through_the_rewrite_finishes_the_same_way(self):
        self.two_entries()
        self.stop(after_move=2)
        # The move is on the disk and not saved. Now the rewrite is killed
        # after it has written the first file and before the second.
        with _StopOnWrite(after=1):
            try:
                changes.migrate(self.root, self.base_id, today=TODAY)
            except _Stopped:
                pass

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_stopping_between_writing_the_record_and_saving_it(self):
        self.two_entries()
        # Two entries are written by the rewrite, then the record. Killing
        # the run after the third write leaves the record on the disk with
        # nothing saved about it.
        self.stop_on_write(after=3)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual(self.uninterrupted(), self.state_of(self.root, self.base_id))

    def test_a_note_we_never_wrote_stops_the_run_and_touches_nothing(self):
        from gtmbase import fsutil, paths

        self.two_entries()
        fsutil.atomic_write_json(
            os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE),
            {"schema": 1, "base_root": "/somewhere/else", "head": "abc", "paths": []},
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_NOTE_UNREADABLE, result.code)
        self.assertEqual(
            [ENTRY_ONE + ".md", ENTRY_TWO + ".md"],
            self.files_in(constants.LEGACY_CHANGES_DIR),
        )


# --- Nothing is touched until everything has been classified ------------------


class TestPuttingBackTouchesNothingUntilItHasLookedAtEverything(MigrationCase):
    """D-C1 and D-C2: the governing rule, proved on the two ways it was broken.

    Classify every path first. If any one of them holds the person's own
    words, the run stops before it has changed anything at all, and the
    sentence names the document.
    """

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def two_entries(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.LEGACY_CHANGES_DIR,
            ENTRY_TWO,
            old_entry(ENTRY_TWO, "We stopped calling on the smallest accounts."),
        )
        self.save()

    def stopped_before_the_move_was_saved(self):
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_an_edit_on_one_moved_path_leaves_the_other_one_alone(self):
        """D-C1. The run used to take the first one away before it noticed."""
        self.two_entries()
        self.stopped_before_the_move_was_saved()
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_TWO + ".md"),
            "their own words, not ours\n",
        )
        before = state_of(self.root, self.base_id)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertIn(ENTRY_TWO, result.sentence)
        self.assertTrue(os.path.exists(self.note_path()))
        # Nothing at all moved, and the other entry is still readable.
        self.assertEqual(before, state_of(self.root, self.base_id))
        self.assertIn(ENTRY_ONE, self.entries_now())

    def test_it_never_reaches_a_state_where_an_entry_is_in_neither_folder(self):
        """D-C1, said as the thing that must never happen."""
        self.two_entries()
        self.stopped_before_the_move_was_saved()
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_TWO + ".md"),
            "their own words, not ours\n",
        )
        for _try in range(3):
            changes.migrate(self.root, self.base_id, today=TODAY)
            somewhere = self.files_in(constants.CHANGES_DIR) + self.files_in(
                constants.LEGACY_CHANGES_DIR
            )
            self.assertIn(ENTRY_ONE + ".md", somewhere)

    def test_an_edit_to_an_entry_the_move_had_not_reached_is_never_written_over(self):
        """D-C2. The run put the older path back without looking at it."""
        self.two_entries()
        # Killed between the two moves, so one entry has moved and the other
        # is still sitting in the older folder, unmoved and unsaved.
        runner = _StopAfter(stop_after_move=1)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass
        else:
            self.fail("the run was meant to stop between the two moves")

        still_old = [
            name
            for name in self.files_in(constants.LEGACY_CHANGES_DIR)
        ]
        self.assertTrue(still_old, "one entry should not have moved yet")
        theirs = "My own correction to this entry, not saved yet.\n"
        left_behind = still_old[0]
        support.write(
            os.path.join(self.root, constants.LEGACY_CHANGES_DIR, left_behind),
            old_entry(left_behind[: -len(".md")], theirs.strip()),
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertIn(left_behind[: -len(".md")], result.sentence)
        self.assertIn(
            theirs.strip(),
            support.read(
                os.path.join(self.root, constants.LEGACY_CHANGES_DIR, left_behind)
            ),
        )

    def test_a_put_back_still_restores_a_file_the_move_really_took_away(self):
        """The ordinary case has to keep working: nothing of theirs is there."""
        self.two_entries()
        runner = _StopAfter(stop_after_move=1)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertEqual(
            [ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now())
        )


class TestTheSameEntryInBothFoldersSayingTheSameThing(MigrationCase):
    """D-H1: the restored-backup case the plan says has to work."""

    def both_copies(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

    def test_it_migrates_and_takes_the_older_copy_away(self):
        self.both_copies()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([], self.files_in(constants.LEGACY_CHANGES_DIR))
        self.assertEqual(
            [ENTRY_ONE + ".md", ENTRY_TWO + ".md"],
            self.files_in(constants.CHANGES_DIR),
        )
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def test_the_committed_copy_is_never_deleted_from_the_working_tree(self):
        self.both_copies()
        changes.migrate(self.root, self.base_id, today=TODAY)
        runner = GitRunner()
        self.assertEqual(
            "", runner.run(["status", "--porcelain"], cwd=self.root).stdout.strip()
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    self.root,
                    constants.CHANGES_DIR.replace("/", os.sep),
                    ENTRY_ONE + ".md",
                )
            )
        )

    def test_running_it_three_times_never_wedges(self):
        self.both_copies()
        for _try in range(3):
            result = changes.migrate(self.root, self.base_id, today=TODAY)
            self.assertTrue(result.ok, "%s: %s" % (result.code, result.sentence))
            self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))


class TestTheNoteIsReadAsAStranger(MigrationCase):
    """D-H2: a note that cannot be trusted refuses and touches nothing."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def stopped_after_the_move(self):
        runner = _StopAfter(stop_after_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def rewrite_note(self, **values):
        import json

        payload = json.load(open(self.note_path(), encoding="utf-8"))
        payload.update(values)
        with open(self.note_path(), "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def test_a_note_whose_head_cannot_be_read_refuses_and_moves_nothing(self):
        """D-H2. A failing log used to read as "nothing was saved"."""
        self.old_layout()
        self.stopped_after_the_move()
        self.rewrite_note(head="0" * 40)
        before = state_of(self.root, self.base_id)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_CANNOT_READ_HISTORY, result.code)
        self.assertEqual(before, state_of(self.root, self.base_id))
        self.assertTrue(os.path.exists(self.note_path()))
        self.assertTrue(self.entries_now(), "the base must not read as empty")

    def test_a_head_that_is_not_forty_hex_characters_is_refused(self):
        self.old_layout()
        self.stopped_after_the_move()
        self.rewrite_note(head="not a saved point")
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.CODE_NOTE_UNREADABLE, result.code)
        self.assertTrue(self.entries_now())

    def test_a_came_from_path_outside_the_older_folder_is_refused(self):
        self.old_layout()
        self.stopped_after_the_move()
        self.rewrite_note(came_from=["context/strategy/icp.md"])
        before = state_of(self.root, self.base_id)
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.CODE_NOTE_UNREADABLE, result.code)
        self.assertEqual(before, state_of(self.root, self.base_id))


class TestFinishingNeverCommitsSomebodyElsesWork(MigrationCase):
    """D-H3: the finish path used to save the person's edit as its own."""

    def stopped_after_the_move(self):
        runner = _StopAfter(stop_after_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_an_edit_to_a_moved_file_stops_the_finish_and_names_it(self):
        self.old_layout()
        self.stopped_after_the_move()
        theirs = old_entry(ENTRY_ONE, "half a sentence I am still writing")
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md"),
            theirs,
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        self.assertIn(ENTRY_ONE, result.sentence)
        self.assertEqual(
            theirs,
            support.read(
                os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
            ),
        )
        saved = GitRunner().run(
            ["log", "--format=%s", "-1"], cwd=self.root
        ).stdout.strip()
        self.assertEqual(changes.MOVE_SUBJECT, saved)

    def test_an_unrelated_unsaved_edit_stops_the_finish_too(self):
        self.old_layout()
        self.stopped_after_the_move()
        support.write(
            os.path.join(self.root, "context", "strategy", "icp.md"),
            "---\nkind: icp\nowner: %s\nlast_confirmed: 2026-01-12\nsources: []\n"
            "status: approved\n---\n\n# Profile\n\nStill writing this.\n" % OWNER,
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)


# --- An entry that parses but cannot be written back out ----------------------


def unrenderable_entry(entry_id):
    """An entry the parser accepts and the writer refuses.

    A comma inside an affected path parses as one list item and cannot be
    written back out as one, because a comma is how the list is separated.
    Somebody typed one, which is enough.
    """
    return old_entry(entry_id).replace(
        "affects: [context/strategy/icp.md]",
        'affects:\n  - "context/a,b.md"',
    )


class TestAnEntryThatCannotBeWrittenBackOut(MigrationCase):
    """D-H5: comparing two copies must never be able to break the reader."""

    def test_the_reader_reports_it_as_a_problem_rather_than_raising(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, unrenderable_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])

        readable = [row.entry.id for row in rows if row.entry is not None]
        self.assertIn(ENTRY_TWO, readable)

    def test_the_review_still_runs_with_one_of_those_in_the_base(self):
        from gtmbase import stale_check

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, unrenderable_entry(ENTRY_ONE))
        self.save()

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )
        self.assertTrue(result.sentences)

    def test_the_migration_moves_it_and_keeps_the_value_nobody_could_rewrite(self):
        """It moves, because the rewrite never writes the whole file out.

        A value a writer would refuse is carried through untouched, which is
        the point of renaming the settings line by line instead of parsing
        the file and writing a fresh one in its place.
        """
        was = unrenderable_entry(ENTRY_ONE)
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, was)
        self.save()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        now = support.read(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.assertIn('- "context/a,b.md"', now)
        self.assertEqual(
            was.replace("kind: decision", "kind: change")
            .replace("decided_on:", "happened_on:")
            .replace("decided_by:", "noted_by:"),
            now,
        )

    def test_the_same_one_in_both_folders_is_still_compared(self):
        """Two copies are compared on their fields, not on rendered text."""
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, unrenderable_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            unrenderable_entry(ENTRY_ONE).replace("kind: decision", "kind: change"),
        )
        self.save()

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])

        kept = [row for row in rows if row.entry is not None]
        problems = [row.error for row in rows if row.entry is None]
        self.assertEqual(1, len(kept) + len(problems))
        self.assertNotIn(base_reader.CODE_IN_BOTH_FOLDERS, problems)


# --- A conflict is said out loud, and nothing is quietly settled --------------


class TestAConflictIsNeverSilent(MigrationCase):
    """D-H4. Two copies that disagree used to unflag every document silently."""

    ICP = "context/strategy/icp.md"

    def in_conflict(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save()

    def run_check(self, mode="normal"):
        from gtmbase import stale_check

        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode=mode,
            dry_run=True,
        )

    def test_the_run_names_the_change_that_is_written_twice(self):
        self.in_conflict()
        said = " ".join(self.run_check().sentences)
        self.assertIn(ENTRY_ONE, said)

    def test_the_run_never_says_the_base_has_nothing_recorded(self):
        from gtmbase import stale_check

        self.in_conflict()
        self.assertNotIn(
            stale_check.LEDGER_BEHIND_EMPTY % 30, self.run_check().sentences
        )

    def test_the_affected_document_is_still_named_as_one_it_cannot_vouch_for(self):
        from gtmbase import names, stale_check

        self.in_conflict()

        said = self.run_check().sentences

        # The sentence itself, with the document's own name in it. Matching
        # the path alone passed with this sentence deleted, because the path
        # appears in another sentence entirely.
        self.assertIn(
            stale_check.CANNOT_VOUCH % names.document_name(self.ICP), said
        )

    def test_the_review_says_it_too(self):
        self.in_conflict()
        said = " ".join(self.run_check(mode="review").sentences)
        self.assertIn(ENTRY_ONE, said)

    def test_the_moment_of_use_check_says_it_rather_than_saying_nothing(self):
        from gtmbase import moment

        self.in_conflict()
        flag = moment.check(
            self.root, self.base_id, self.ICP, session_id="sess-1", now=TODAY
        )
        self.assertIn(ENTRY_ONE, " ".join(flag.sentences()))

    def test_the_four_week_numbers_do_not_count_a_change_written_twice(self):
        self.in_conflict()
        found = report.catches(self.root, GitRunner(), TODAY)
        self.assertEqual([], found["entries"])

    def test_the_migration_still_refuses_and_names_it(self):
        self.in_conflict()
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn(ENTRY_ONE, result.sentence)


class TestTheSameIdTwiceInsideOneFolder(MigrationCase):
    """K9, and the rule that made most of it unreachable.

    Every file has to be named after the change inside it, and one folder
    cannot hold two files of one name, so two files in one folder claiming
    one identifier can only happen when at least one of them is misnamed.
    That is caught first and by name, and each of the two files is reported
    on its own so a person can see both. The code for two in one folder is
    kept for the case a disk that does not tell two names apart could still
    produce, and it is checked against the values directly.
    """

    def two_files_one_id(self):
        self.put(constants.LEGACY_CHANGES_DIR, "a-note", old_entry(ENTRY_ONE))
        self.put(
            constants.LEGACY_CHANGES_DIR,
            "b-note",
            old_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save()

    def test_each_of_the_two_files_is_reported_on_its_own(self):
        self.two_files_one_id()

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        problems = sorted(
            (row.path, row.error) for row in rows if row.entry is None
        )

        self.assertEqual(
            [
                (
                    constants.LEGACY_CHANGES_DIR + "/a-note.md",
                    base_reader.CODE_NAME_IS_NOT_THE_ID,
                ),
                (
                    constants.LEGACY_CHANGES_DIR + "/b-note.md",
                    base_reader.CODE_NAME_IS_NOT_THE_ID,
                ),
            ],
            problems,
        )

    def test_the_two_codes_are_different_things(self):
        self.assertNotEqual(
            base_reader.CODE_TWICE_IN_ONE_FOLDER,
            base_reader.CODE_IN_BOTH_FOLDERS,
        )
        self.assertNotEqual(
            base_reader.CODE_TWICE_IN_ONE_FOLDER,
            base_reader.CODE_NAME_IS_NOT_THE_ID,
        )

    def test_the_migration_refuses_and_moves_neither_of_them(self):
        self.two_files_one_id()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_NAME_IS_NOT_THE_ID, result.code)
        self.assertEqual(
            ["a-note.md", "b-note.md"],
            self.files_in(constants.LEGACY_CHANGES_DIR),
        )


# --- The rewrite changes the renamed keys and nothing else --------------------


def bytes_of(path):
    """One file's bytes, read without anything translating its line endings."""
    with open(path, "rb") as handle:
        return handle.read()


class TestTheRewriteIsALineLevelRename(MigrationCase):
    """D-M3. A re-render was rewriting the person's whole file underneath them."""

    AWKWARD = (
        "---\r\n"
        "id: %s\r\n"
        "kind: decision\r\n"
        "decided_on: 2026-01-12\r\n"
        "written_on: 2026-01-12\r\n"
        'decided_by: "owner@example.com"\r\n'
        "source: %s\r\n"
        "affects: [context/strategy/icp.md]\r\n"
        "review_by: 2026-04-12\r\n"
        "origin: inbox\r\n"
        "status: open\r\n"
        "---\r\n"
        "\r\n"
        "\r\n"
        "Line one, with two spaces after it.  \r\n"
        "\r\n"
        "\r\n"
        "Line two.\r\n"
        "\r\n"
        "\r\n"
    )

    def awkward_entry(self, entry_id=ENTRY_ONE):
        return self.AWKWARD % (entry_id, SOURCE)

    def test_only_the_three_renamed_pieces_change_and_nothing_else(self):
        was = self.awkward_entry()
        now = formats.rewrite_entry_keys(was)

        self.assertEqual(
            was.replace("kind: decision", "kind: change")
            .replace("decided_on:", "happened_on:")
            .replace("decided_by:", "noted_by:"),
            now,
        )

    def test_every_other_byte_survives_the_migration(self):
        was = self.awkward_entry()
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, was)
        self.save()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        now = bytes_of(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        ).decode("utf-8")
        self.assertEqual(
            was.replace("kind: decision", "kind: change")
            .replace("decided_on:", "happened_on:")
            .replace("decided_by:", "noted_by:"),
            now,
        )
        # Said the other way round, so the proof does not rest on one string.
        self.assertIn("\r\n", now)
        self.assertIn("Line one, with two spaces after it.  \r\n", now)
        self.assertIn("\r\n\r\n\r\nLine two.", now)
        self.assertIn('noted_by: "owner@example.com"', now)
        self.assertNotIn("decided_", now)

    def test_a_word_in_the_body_that_looks_like_a_setting_is_left_alone(self):
        was = self.awkward_entry().replace(
            "Line two.", "decided_on: is a phrase somebody wrote in the body."
        )
        now = formats.rewrite_entry_keys(was)
        self.assertIn("decided_on: is a phrase somebody wrote", now)
        self.assertNotIn("happened_on: is a phrase", now)

    def test_a_kind_that_is_neither_word_is_left_exactly_as_it_is(self):
        was = self.awkward_entry().replace("kind: decision", "kind: something-else")
        self.assertIn("kind: something-else", formats.rewrite_entry_keys(was))

    def test_a_file_already_in_the_new_layout_is_returned_unchanged(self):
        was = new_entry(ENTRY_ONE)
        self.assertEqual(was, formats.rewrite_entry_keys(was))


class TestBothSpellingsOfOneSetting(MigrationCase):
    """D-M3 and K6: two spellings that disagree are never silently resolved."""

    def two_spellings(self, older="2026-01-12", newer="2026-01-05"):
        return old_entry(ENTRY_ONE).replace(
            "decided_on: 2026-01-12",
            "decided_on: %s\nhappened_on: %s" % (older, newer),
        )

    def test_the_parser_refuses_a_file_that_gives_both_and_disagrees(self):
        with self.assertRaises(ValidationError) as caught:
            formats.ChangeEntry.parse(self.two_spellings())
        self.assertEqual("two-spellings-disagree", caught.exception.code)

    def test_the_constructor_refuses_the_same_thing(self):
        with self.assertRaises(ValidationError) as caught:
            formats.ChangeEntry(
                id=ENTRY_ONE,
                happened_on="2026-01-05",
                decided_on="2026-01-12",
                written_on="2026-01-12",
                noted_by=OWNER,
                source=SOURCE,
                review_by="2026-04-12",
                origin="inbox",
                status="open",
            )
        self.assertEqual("two-spellings-disagree", caught.exception.code)

    def test_both_spellings_agreeing_is_accepted(self):
        entry = formats.ChangeEntry.parse(
            self.two_spellings(older="2026-01-12", newer="2026-01-12")
        )
        self.assertEqual("2026-01-12", entry.happened_on)

    def test_the_reader_reports_it_rather_than_choosing(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, self.two_spellings())
        self.save()
        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        self.assertEqual(
            ["two-spellings-disagree"],
            [row.error for row in rows if row.entry is None],
        )

    def test_the_migration_refuses_and_names_the_file(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, self.two_spellings())
        self.save()
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn(ENTRY_ONE, result.sentence)

    def test_a_required_value_that_folds_away_to_nothing_is_a_plain_refusal(self):
        """K6. It used to die on an attribute, which nothing above catches."""
        text = old_entry(ENTRY_ONE).replace(
            "decided_by: %s" % OWNER, 'decided_by: ""'
        )
        with self.assertRaises(ValidationError) as caught:
            formats.ChangeEntry.parse(text)
        self.assertEqual("missing-field", caught.exception.code)

    def test_one_bad_entry_never_takes_the_whole_check_down_with_it(self):
        from gtmbase import stale_check

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, self.two_spellings())
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            dry_run=True,
        )
        self.assertTrue(result.sentences)
        self.assertIn(ENTRY_TWO, self.entries_now())


# --- The offer is a real offer, and it is made once ---------------------------


class TestWhenTheOfferIsMade(MigrationCase):
    """D-M1. An offer made when the move would refuse is not an offer."""

    def review(self, root=None, base_id=None):
        from gtmbase import stale_check

        return stale_check.run(
            root or self.root,
            base_id or self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
            dry_run=True,
        )

    def shared_base(self):
        """The same base with a copy other people could reach."""
        give_it_a_shared_copy(self.sandbox, self.root)

    def test_no_offer_while_one_change_is_written_down_twice(self):
        from gtmbase import stale_check

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE, "Different.")
        )
        self.save()

        result = self.review()

        self.assertNotIn(changes.OFFER, result.sentences)
        self.assertNotIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)

    def test_no_offer_while_there_are_unsaved_edits(self):
        from gtmbase import stale_check

        self.old_layout()
        support.write(
            os.path.join(self.root, "context", "notes", "wip.md"), "still writing\n"
        )

        result = self.review()

        self.assertNotIn(changes.OFFER, result.sentences)
        self.assertNotIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)

    def test_a_base_with_a_shared_copy_is_told_the_condition_instead(self):
        self.shared_base()
        from gtmbase import stale_check

        self.old_layout()

        result = self.review()

        self.assertNotIn(changes.OFFER, result.sentences)
        self.assertIn(changes.EVERY_SEAT_FIRST, result.sentences)
        self.assertIn(stale_check.CODE_EVERY_SEAT_FIRST, result.codes)

    def test_the_move_itself_refuses_on_a_base_with_a_shared_copy(self):
        self.shared_base()
        self.old_layout()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_EVERY_SEAT_FIRST, result.code)
        self.assertEqual(
            [ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR)
        )

    def test_it_runs_on_a_shared_base_once_the_person_says_every_seat_is_ready(self):
        self.shared_base()
        self.old_layout()

        result = changes.migrate(
            self.root, self.base_id, today=TODAY, every_seat_updated=True
        )

        self.assertTrue(result.ok, result.sentence)

    def test_a_decline_stops_the_offer_coming_back_until_the_window_passes(self):
        from gtmbase import stale_check

        self.old_layout()
        self.assertIn(changes.OFFER, self.review().sentences)

        changes.not_now(self.base_id, TODAY)

        self.assertNotIn(changes.OFFER, self.review().sentences)

    def test_the_offer_comes_back_once_the_window_has_passed(self):
        import datetime as when

        self.old_layout()
        changes.not_now(self.base_id, TODAY)
        later = TODAY + when.timedelta(days=31)

        from gtmbase import stale_check

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=later,
            session_id="sess-2",
            mode="review",
            dry_run=True,
        )
        self.assertIn(changes.OFFER, result.sentences)

    def test_the_offer_names_no_folder_path(self):
        self.assertNotIn("work/", changes.OFFER)
        self.assertNotIn("/", changes.OFFER)


class TestAWayOutOfAStoppedRun(MigrationCase):
    """D-M2. A note nothing can finish must not be a base nobody can use."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def stopped_after_the_move(self):
        runner = _StopAfter(stop_after_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_a_moved_file_that_was_taken_away_names_the_document(self):
        self.old_layout()
        self.stopped_after_the_move()
        os.unlink(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn(ENTRY_ONE, result.sentence)

    def test_giving_up_on_it_clears_the_note_and_says_what_it_left_alone(self):
        # Before the move is saved, because after it is saved there is
        # nothing of this run's to put back and the answer is a different one.
        self.old_layout()
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass
        theirs = old_entry(ENTRY_ONE, "words of my own")
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md"),
            theirs,
        )

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertIn(ENTRY_ONE, result.sentence)
        self.assertEqual(
            theirs,
            support.read(
                os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
            ),
        )

    def test_giving_up_with_nothing_of_theirs_puts_our_own_work_back(self):
        self.two_entries_then_stop()
        result = changes.abandon(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertFalse(os.path.exists(self.note_path()))
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def two_entries_then_stop(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")


class TestTheCatchesNumberUnderATidyUp(MigrationCase):
    """D-M4. It rested on a note, and a note is the one thing people rewrite."""

    def base_with_a_catch(self):
        from gtmbase import ids

        entry_id = ENTRY_ONE
        self.put(constants.LEGACY_CHANGES_DIR, entry_id, old_entry(entry_id))
        support.git(["add", "-A"], cwd=self.root)
        support.git(
            ["commit", "-q", "-m", "Proposal %s applied" % entry_id], cwd=self.root
        )
        correction = formats.CorrectionsFile(
            kind="correction",
            date=TODAY.isoformat(),
            staging_id=entry_id,
            entry_id=entry_id,
            source_id=SOURCE,
            intake_path="ledger",
            mode="none",
            third_party=False,
            content_hash=ids.content_hash("anything"),
            correction_class="new-decision",
            marker="gtm-base proposal %s entry %s source %s"
            % (entry_id, entry_id, SOURCE),
            touched_paths=["context/strategy/icp.md"],
            what_changed="Before: one thing.\n\nAfter: another thing.",
            why="Because the change said so.",
        )
        support.write(
            os.path.join(
                self.root, constants.CORRECTIONS_DIR, TODAY.isoformat() + "-one.md"
            ),
            correction.validate().render(),
        )
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", "the record"], cwd=self.root)

    def test_the_number_survives_the_three_saves_being_folded_into_one(self):
        self.base_with_a_catch()
        runner = GitRunner()
        before = report.catches(self.root, runner, TODAY)["count"]
        self.assertEqual(1, before)
        head = support.head_of(self.root)

        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(before, report.catches(self.root, runner, TODAY)["count"])

        support.git(["reset", "-q", "--soft", head], cwd=self.root)
        support.git(
            ["commit", "-q", "-m", "tidy: move to work/changes"], cwd=self.root
        )

        self.assertEqual(before, report.catches(self.root, runner, TODAY)["count"])


class TestARetriedApprovalNeverWritesASecondCopy(MigrationCase):
    """D-M5 and K8. It wrote a second copy and made the conflict itself.

    Everything that writes one context change down asks where that change
    already is first. On a base that has not been updated yet the answer is
    the older folder, and writing a second copy into the newer one would
    leave two files with one identifier saying two different things.
    """

    def test_a_change_already_in_the_older_folder_is_written_where_it_is(self):
        self.old_layout()
        self.assertEqual(
            constants.LEGACY_CHANGES_DIR + "/" + ENTRY_ONE + ".md",
            base_reader.where_to_write_the_entry(self.root, ENTRY_ONE),
        )

    def test_a_change_nobody_has_written_down_goes_where_they_go_today(self):
        self.assertEqual(
            constants.CHANGES_DIR + "/" + ENTRY_TWO + ".md",
            base_reader.where_to_write_the_entry(self.root, ENTRY_TWO),
        )

    def test_a_change_in_the_newer_folder_stays_in_the_newer_folder(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.save()
        self.assertEqual(
            constants.CHANGES_DIR + "/" + ENTRY_ONE + ".md",
            base_reader.where_to_write_the_entry(self.root, ENTRY_ONE),
        )


class TestTheRecordTheMoveLeaves(MigrationCase):
    """The low findings about the dated record it writes."""

    def test_a_second_move_on_the_same_day_never_writes_over_the_first(self):
        self.old_layout()
        changes.migrate(self.root, self.base_id, today=TODAY)
        first = self.corrections()
        self.assertEqual(1, len(first))

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save("something written by an older seat")
        changes.migrate(self.root, self.base_id, today=TODAY)

        after = self.corrections()
        self.assertEqual(2, len(after), after)
        self.assertIn(first[0], after)

    def test_the_record_never_says_the_older_word(self):
        self.old_layout()
        changes.migrate(self.root, self.base_id, today=TODAY)
        written = support.read(
            os.path.join(self.root, constants.CORRECTIONS_DIR, self.corrections()[0])
        )
        import plain_language

        self.assertEqual([], plain_language.find_banned_person_facing(written))


class TestAFileWhoseNameDisagreesWithWhatIsInIt(MigrationCase):
    """A low finding: one identifier must never end up on two files."""

    def test_it_is_reported_as_a_problem_naming_the_file(self):
        self.put(constants.LEGACY_CHANGES_DIR, "some-note", old_entry(ENTRY_ONE))
        self.save()

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        problems = [(row.path, row.error) for row in rows if row.entry is None]

        self.assertEqual(
            [
                (
                    constants.LEGACY_CHANGES_DIR + "/some-note.md",
                    base_reader.CODE_NAME_IS_NOT_THE_ID,
                )
            ],
            problems,
        )

    def test_the_migration_refuses_rather_than_moving_it(self):
        self.put(constants.LEGACY_CHANGES_DIR, "some-note", old_entry(ENTRY_ONE))
        self.save()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn("some-note.md", result.sentence)


class TestAnEmptyOlderFolderFromAnEarlierRelease(MigrationCase):
    """K10: a folder holding nothing but its placeholder is taken away."""

    def test_the_move_takes_the_placeholder_and_the_folder_with_it(self):
        support.write(
            os.path.join(self.root, constants.LEGACY_CHANGES_DIR, ".gitkeep"), ""
        )
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()

        changes.migrate(self.root, self.base_id, today=TODAY)

        left = os.path.join(
            self.root, constants.LEGACY_CHANGES_DIR.replace("/", os.sep)
        )
        self.assertFalse(
            os.path.isdir(left) and os.listdir(left),
            "nothing should be left in the older folder",
        )


# --- The pieces around the edges ---------------------------------------------


class TestTheOlderNameOfTheDismissOption(MigrationCase):
    """K1. A session holding the older skill text must not be refused."""

    def test_both_spellings_of_the_option_are_accepted(self):
        import subprocess

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        for option in ("--dismiss-quiet-record", "--dismiss-ledger-behind"):
            finished = subprocess.run(
                [sys.executable, script, option],
                cwd=support.where_a_script_runs(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ, TZ="America/Los_Angeles"),
            )
            self.assertNotEqual(
                2, finished.returncode, finished.stderr.decode("utf-8")[:400]
            )

    def test_the_older_keyword_still_reaches_the_run(self):
        from gtmbase import stale_check

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            dismiss_ledger_behind=True,
        )
        self.assertTrue(
            any(
                sentence.startswith("GTM Base will not mention")
                for sentence in result.sentences
            ),
            result.sentences,
        )


class TestTheMoveStepOfTheSkill(MigrationCase):
    """K2. A look only writes nothing, and an error is a sentence."""

    def run_script(self, *options):
        import subprocess

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        return subprocess.run(
            [sys.executable, script] + list(options),
            cwd=support.where_a_script_runs(self.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, TZ="America/Los_Angeles"),
        )

    def test_a_look_only_saves_nothing(self):
        self.old_layout()
        before = support.head_of(self.root)

        finished = self.run_script("--move-changes", "--dry-run")

        self.assertEqual(before, support.head_of(self.root))
        self.assertEqual(
            [ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR)
        )
        self.assertIn("would", finished.stdout.decode("utf-8").lower())

    def test_giving_up_is_a_step_of_its_own(self):
        finished = self.run_script("--abandon-move")
        self.assertNotEqual(2, finished.returncode)

    def test_a_base_that_is_not_one_says_so_rather_than_going_wrong(self):
        import subprocess
        import tempfile

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        elsewhere = tempfile.mkdtemp(prefix="gtm-base-not-a-base-")
        finished = subprocess.run(
            [sys.executable, script, "--move-changes"],
            cwd=elsewhere,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, TZ="America/Los_Angeles"),
        )
        self.assertNotIn("Traceback", finished.stderr.decode("utf-8"))


class TestADraftThatUsesTheOlderSpelling(MigrationCase):
    """K7. Writing the draft back out must never raise out of the parse."""

    def test_a_draft_in_the_older_spelling_is_folded_and_accepted(self):
        from gtmbase import drafting

        older = (
            "```markdown\n"
            + old_entry(ENTRY_ONE).replace("id: " + ENTRY_ONE, "id: pending")
            .replace("origin: inbox", "origin: join")
            .replace("status: open", "run_id: pending\nstatus: open")
            + "```\n"
        )
        draft = drafting.parse(drafting.STEP_CHANGE, older)
        self.assertEqual("change", draft.fields["kind"])
        self.assertIn("happened_on", draft.fields)

    def test_a_draft_already_in_the_new_spelling_is_left_alone(self):
        from gtmbase import drafting

        text = (
            "```markdown\n"
            + new_entry(ENTRY_ONE).replace("id: " + ENTRY_ONE, "id: pending")
            .replace("origin: inbox", "origin: join")
            .replace("status: open", "run_id: pending\nstatus: open")
            + "```\n"
        )
        draft = drafting.parse(drafting.STEP_CHANGE, text)
        self.assertEqual(text.split("```markdown\n")[1][: -len("```\n")], draft.text)

    def test_a_draft_that_cannot_be_written_back_out_is_a_plain_refusal(self):
        from gtmbase import drafting
        from gtmbase.errors import DraftError

        broken = (
            "```markdown\n"
            + old_entry(ENTRY_ONE)
            .replace("id: " + ENTRY_ONE, "id: pending")
            .replace("origin: inbox", "origin: join")
            .replace("status: open", "run_id: pending\nstatus: open")
            .replace("---\n\nWe now", "\nWe now")
            + "```\n"
        )
        with self.assertRaises(DraftError):
            drafting.parse(drafting.STEP_CHANGE, broken)


class TestTheOlderStepName(MigrationCase):
    """A setup run saved under the older step name still resumes."""

    def test_the_older_step_name_still_names_the_same_step(self):
        from gtmbase import drafting

        self.assertEqual(
            drafting.STEP_CHANGE, drafting.step_named("ledger-entry")
        )
        self.assertEqual(
            drafting.STEP_CHANGE, drafting.step_named(drafting.STEP_CHANGE)
        )
        self.assertIsNone(drafting.step_named("something-else"))


class TestTheOlderConstantName(MigrationCase):
    """The plan said the old value stays readable, so it does."""

    def test_the_older_name_still_reads_the_older_folder(self):
        self.assertEqual(constants.LEGACY_CHANGES_DIR, constants.DECISIONS_DIR)


# --- A disk that does not tell two spellings of one name apart ----------------


class TestAFolderNamedWithACapitalLetter(MigrationCase):
    """A low finding: `work/Decisions` must not wedge anything.

    Most Macs do not tell two spellings of one folder name apart, so a base
    whose folder was made with a capital letter is the same folder to the
    disk. Nothing here should notice, and this says so out loud rather than
    leaving it to luck.
    """

    def setUp(self):
        super(TestAFolderNamedWithACapitalLetter, self).setUp()
        self.capital = os.path.join(self.root, "work", "Decisions")
        os.makedirs(self.capital, exist_ok=True)
        support.write(
            os.path.join(self.capital, ENTRY_ONE + ".md"), old_entry(ENTRY_ONE)
        )
        self.save("an entry under a capital letter")
        same = os.path.isdir(
            os.path.join(self.root, constants.LEGACY_CHANGES_DIR)
        )
        if not same:
            self.skipTest("this disk tells the two spellings apart")

    def test_the_change_is_read(self):
        self.assertIn(ENTRY_ONE, self.entries_now())

    def test_it_migrates_and_does_not_wedge(self):
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertIn(ENTRY_ONE, self.entries_now())
        again = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(again.ok, again.sentence)


# --- Nothing is written that cannot be read back to the same values ----------


def exact_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_exactly(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


class TestTheRewriteIsCheckedAgainstItself(MigrationCase):
    """The invariant: read back every rewritten entry, or refuse by name.

    An entry may only be written in a form the reader reads back to exactly
    the same values. Everything below is a file the rename could not handle,
    and every one of them has to be a named refusal before anything is
    written to the base, rather than a saved file nothing can read.
    """

    def put_exactly(self, entry_id, text, folder=None):
        write_exactly(
            os.path.join(
                self.root,
                (folder or constants.LEGACY_CHANGES_DIR).replace("/", os.sep),
                entry_id + ".md",
            ),
            text,
        )
        self.save()

    def both_spellings(self, value="2026-01-12"):
        return old_entry(ENTRY_ONE).replace(
            "decided_on: 2026-01-12\n",
            "decided_on: 2026-01-12\nhappened_on: %s\n" % value,
        )

    # --- N2: both spellings, agreeing ---------------------------------------

    def test_both_spellings_agreeing_are_folded_into_one_line(self):
        out = formats.rewrite_entry_keys(self.both_spellings())
        self.assertEqual(1, out.count("happened_on:"), out)
        self.assertNotIn("decided_on:", out.split("---")[1])
        formats.ChangeEntry.parse(out)

    def test_the_folded_file_reads_back_to_the_same_values(self):
        was = self.both_spellings()
        out = formats.rewrite_entry_keys(was)
        self.assertEqual(
            base_reader._what_it_says(formats.ChangeEntry.parse(was)),
            base_reader._what_it_says(formats.ChangeEntry.parse(out)),
        )

    def test_both_of_the_other_setting_agreeing_fold_the_same_way(self):
        was = old_entry(ENTRY_ONE).replace(
            "decided_by: %s\n" % OWNER,
            "decided_by: %s\nnoted_by: %s\n" % (OWNER, OWNER),
        )
        out = formats.rewrite_entry_keys(was)
        self.assertEqual(1, out.count("noted_by:"), out)
        formats.ChangeEntry.parse(out)

    def test_the_whole_migration_leaves_something_the_reader_can_read(self):
        self.put_exactly(ENTRY_ONE, self.both_spellings())

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        self.assertEqual(
            [ENTRY_ONE], [row.entry.id for row in rows if row.entry is not None]
        )

    def test_both_spellings_disagreeing_are_refused_by_name(self):
        self.put_exactly(ENTRY_ONE, self.both_spellings(value="2026-01-05"))

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn(ENTRY_ONE, result.sentence)

    # --- N4: a byte-order mark ----------------------------------------------

    def with_a_mark(self):
        body = (
            "Intro.\n\n---\n\ndecided_by: the board, in March\n"
            "kind: decision\n\n---\n\nTail.\n"
        )
        return "\ufeff" + old_entry(ENTRY_ONE).replace(
            "We now sell to companies of twenty to two hundred people.\n", body
        )

    def test_a_file_that_starts_with_a_mark_has_its_settings_renamed(self):
        out = formats.rewrite_entry_keys(self.with_a_mark())
        block = out.split("---")[1]
        self.assertIn("happened_on:", block)
        self.assertIn("noted_by:", block)
        self.assertIn("kind: change", block)

    def test_the_mark_itself_survives(self):
        out = formats.rewrite_entry_keys(self.with_a_mark())
        self.assertTrue(out.startswith("\ufeff"), repr(out[:4]))

    def test_the_body_of_a_marked_file_is_never_edited(self):
        was = self.with_a_mark()
        out = formats.rewrite_entry_keys(was)
        self.assertEqual(
            formats.ChangeEntry.parse(was).body,
            formats.ChangeEntry.parse(out).body,
        )
        self.assertIn("decided_by: the board, in March", out)

    def test_a_marked_file_migrates_and_reads_back(self):
        self.put_exactly(ENTRY_ONE, self.with_a_mark())

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        landed = exact_bytes(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        ).decode("utf-8")
        self.assertTrue(landed.startswith("\ufeff"))
        self.assertIn("kind: change", landed.split("---")[1])
        self.assertIn(ENTRY_ONE, self.entries_now())

    # --- The lows the invariant closes --------------------------------------

    def test_a_file_whose_lines_end_the_oldest_way_is_refused_by_name(self):
        self.put_exactly(ENTRY_ONE, old_entry(ENTRY_ONE).replace("\n", "\r"))

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertIn(ENTRY_ONE, result.sentence)
        self.assertEqual(
            [ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR)
        )

    def test_a_quoted_kind_is_renamed_too(self):
        was = old_entry(ENTRY_ONE).replace("kind: decision", 'kind: "decision"')
        out = formats.rewrite_entry_keys(was)
        self.assertNotIn("decision", out.split("---")[1])
        self.assertIn("change", out.split("---")[1])

    def test_a_quoted_kind_migrates_and_reads_back_as_the_new_word(self):
        was = old_entry(ENTRY_ONE).replace("kind: decision", 'kind: "decision"')
        self.put_exactly(ENTRY_ONE, was)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        landed = support.read(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.assertNotIn(constants.LEGACY_ENTRY_KIND, landed.split("---")[1])

    def test_the_check_runs_in_the_survey_before_anything_is_written(self):
        """A file the rename cannot handle never reaches a saved change."""
        self.put_exactly(ENTRY_ONE, self.both_spellings(value="2026-01-05"))
        before = support.head_of(self.root)

        changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(before, support.head_of(self.root))
        self.assertFalse(
            os.path.isdir(
                os.path.join(self.root, constants.CHANGES_DIR.replace("/", os.sep))
            )
        )


# --- No recovery ever deletes the only copy of a change -----------------------


class TestNothingIsDeletedUnlessAnotherCopyIsThere(MigrationCase):
    """N1. The rule, stated as the thing that must never happen.

    A capital-letter folder made every one of these fail at once: the note
    recorded a path git did not hold, the question of whether HEAD held it
    came back no, the restore list came back empty, and the undo list deleted
    the only copy anyway. Every entry ended in neither folder, on every retry.
    """

    CAPITAL = "work/Decisions"

    def setUp(self):
        super(TestNothingIsDeletedUnlessAnotherCopyIsThere, self).setUp()
        self.capital = os.path.join(self.root, "work", "Decisions")
        os.makedirs(self.capital, exist_ok=True)
        for entry_id in (ENTRY_ONE, ENTRY_TWO):
            support.write(
                os.path.join(self.capital, entry_id + ".md"), old_entry(entry_id)
            )
        self.save("two entries under a capital letter")
        if not os.path.isdir(
            os.path.join(self.root, constants.LEGACY_CHANGES_DIR)
        ):
            self.skipTest("this disk tells the two spellings apart")

    def stopped_before_the_move_was_saved(self):
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_every_change_is_still_somewhere_after_a_retry(self):
        self.stopped_before_the_move_was_saved()

        changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(
            [ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()), "a change is gone"
        )

    def test_three_retries_never_lose_one(self):
        self.stopped_before_the_move_was_saved()
        for _try in range(3):
            changes.migrate(self.root, self.base_id, today=TODAY)
            self.assertEqual(
                [ENTRY_ONE, ENTRY_TWO],
                sorted(self.entries_now()),
                "a change went missing on retry %d" % _try,
            )

    def test_the_capital_folder_is_the_one_the_note_records(self):
        self.stopped_before_the_move_was_saved()
        from gtmbase import paths

        import json

        note = json.load(
            open(
                os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE),
                encoding="utf-8",
            )
        )
        came_from = [str(item.get("path")) for item in note["came_from"]]
        self.assertTrue(
            all(path.startswith(self.CAPITAL + "/") for path in came_from),
            came_from,
        )

    def test_it_finishes_cleanly_when_it_is_allowed_to(self):
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))


class TestTheRuleItself(MigrationCase):
    """N1's general rule, tested where a copy really is the only one."""

    def test_a_path_never_saved_and_gone_from_disk_stops_the_recovery(self):
        """The file the move took away is not in HEAD, so it cannot come back.

        Deleting the copy in the new folder would leave the change nowhere at
        all, so the recovery stops and says so instead.
        """
        # An entry that was never saved: written, moved, and neither committed.
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        # ENTRY_TWO is on the disk and has never been saved.
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass

        changes.migrate(self.root, self.base_id, today=TODAY)

        # Whatever it decided, both changes are still readable somewhere.
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))


# --- Nothing settles a document while a change about it disagrees with itself -


class TestNoQuestionIsAskedWhileAConflictStands(MigrationCase):
    """N3. A yes given while the two copies disagreed hid the change for good."""

    ICP = "context/strategy/icp.md"

    def in_conflict(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save()

    def review(self):
        from gtmbase import stale_check

        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )

    def test_the_review_issues_no_question_for_the_document_it_cannot_vouch_for(
        self,
    ):
        self.in_conflict()

        result = self.review()

        named = [line for line in result.review if line.path == self.ICP]
        self.assertTrue(
            all(line.question_id is None for line in named),
            [(line.path, line.question_id) for line in named],
        )

    def test_the_review_still_says_what_is_wrong_with_it(self):
        self.in_conflict()
        said = " ".join(self.review().sentences)
        self.assertIn(ENTRY_ONE, said)

    def a_question_about_the_profile(self):
        """One question this seat really issued about the profile."""
        from gtmbase import stale_check

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )
        for line in result.review:
            if line.path == self.ICP and line.question_id:
                return line.question_id
        return None

    def test_answering_yes_about_that_document_is_refused(self):
        from gtmbase import confirm

        # The question is issued before the conflict arrives, so there really
        # is one to answer when the conflict is standing.
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        question = self.a_question_about_the_profile()
        self.assertIsNotNone(question)
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save("the conflict arrives")

        result = confirm.answer(
            self.root,
            self.base_id,
            question,
            confirm.ANSWER_YES,
            "sess-1",
            now=TODAY,
        )

        self.assertEqual(confirm.STATUS_REFUSED, result.status)
        self.assertTrue(
            any(ENTRY_ONE in reason for reason in result.reasons), result.reasons
        )

    def test_it_writes_no_confirmation_while_the_conflict_stands(self):
        from gtmbase import confirm

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        question = self.a_question_about_the_profile()
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save("the conflict arrives")
        before = state_of(self.root, self.base_id)["confirmations"]

        confirm.answer(
            self.root,
            self.base_id,
            question,
            confirm.ANSWER_YES,
            "sess-1",
            now=TODAY,
        )

        self.assertEqual(
            before, state_of(self.root, self.base_id)["confirmations"]
        )

    def test_the_change_is_still_there_once_the_conflict_is_resolved(self):
        """The whole point: a yes must not be able to hide it for good."""
        from gtmbase import confirm, stale

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        question = self.a_question_about_the_profile()
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save("the conflict arrives")
        confirm.answer(
            self.root,
            self.base_id,
            question,
            confirm.ANSWER_YES,
            "sess-1",
            now=TODAY,
        )

        os.unlink(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.save("resolved: kept the older copy")

        flags = state_of(self.root, self.base_id)["flags"]
        self.assertTrue(
            any(
                path == self.ICP and trigger == stale.TRIGGER_LEDGER
                for path, trigger, _ids in flags
            ),
            flags,
        )

    def test_approving_a_prepared_change_for_that_document_is_refused(self):
        from gtmbase import approve_local, stale_check

        # A change is prepared before the conflict exists, then the conflict
        # appears, and only then is the change approved.
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        run = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
        )
        prepared = [item for item in run.staged if item.entry_id == ENTRY_ONE]
        self.assertEqual(1, len(prepared), run.lines())
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save("the conflict arrives")

        shown = approve_local.show(
            prepared[0].path, self.root, self.base_id, now=TODAY
        )

        self.assertEqual(approve_local.STATUS_REFUSED, shown.status)
        self.assertTrue(
            any(ENTRY_ONE in reason for reason in shown.reasons), shown.reasons
        )


class TestAConflictIsNeverQuieted(MigrationCase):
    """A low finding: no setting hides a change that disagrees with itself."""

    ICP = "context/strategy/icp.md"

    def in_conflict(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE, "Something else entirely."),
        )
        self.save()

    def test_asking_for_quiet_does_not_hide_it_at_the_moment_of_use(self):
        from gtmbase import moment, state

        self.in_conflict()
        state.set_silent_until(self.base_id, state.SILENT_UNTIL_ASKED)

        flag = moment.check(
            self.root, self.base_id, self.ICP, session_id="sess-1", now=TODAY
        )

        self.assertIn(ENTRY_ONE, " ".join(flag.sentences()))

    def test_a_month_of_quiet_does_not_hide_it_either(self):
        import datetime as when

        from gtmbase import moment, state

        self.in_conflict()
        state.set_silent_until(self.base_id, TODAY + when.timedelta(days=30))

        flag = moment.check(
            self.root, self.base_id, self.ICP, session_id="sess-1", now=TODAY
        )

        self.assertIn(ENTRY_ONE, " ".join(flag.sentences()))

    def test_declining_the_update_does_not_hide_it(self):
        from gtmbase import stale_check

        self.in_conflict()
        changes.not_now(self.base_id, TODAY)

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )

        self.assertIn(ENTRY_ONE, " ".join(result.sentences))


# --- What the run removed is put back too -------------------------------------


class TestWhatCommitOneRemovedComesBackAsWell(MigrationCase):
    """N5. Putting back knew about what it moved and not about what it removed."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def with_a_placeholder(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        support.write(
            os.path.join(
                self.root, constants.LEGACY_CHANGES_DIR, ".gitkeep"
            ),
            "",
        )
        self.save()

    def with_an_identical_duplicate(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

    def stopped_before_the_move_was_saved(self):
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def unsaved(self):
        return GitRunner().run(
            ["status", "--porcelain"], cwd=self.root
        ).stdout.strip()

    def test_a_placeholder_it_removed_is_put_back(self):
        self.with_a_placeholder()
        self.stopped_before_the_move_was_saved()

        changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual("", self.unsaved(), "it left work nobody did")

    def test_an_identical_copy_it_removed_is_put_back(self):
        self.with_an_identical_duplicate()
        self.stopped_before_the_move_was_saved()

        changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual("", self.unsaved(), "it left work nobody did")
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def test_the_note_is_kept_while_anything_it_touched_still_differs(self):
        self.with_a_placeholder()
        self.stopped_before_the_move_was_saved()
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        if not result.ok:
            self.assertTrue(
                os.path.exists(self.note_path()),
                "a run that could not put everything back kept no note",
            )

    def test_it_finishes_on_the_next_try(self):
        self.with_a_placeholder()
        self.stopped_before_the_move_was_saved()
        for _try in range(3):
            result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE], sorted(self.entries_now()))


class TestGivingUpTellsTheTruth(MigrationCase):
    """N6. It reported a clean base in three states that were not clean."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def two_entries(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

    def stop(self, **options):
        runner = _StopAfter(**options)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_it_never_manufactures_a_change_written_down_twice(self):
        """N6 (a). It put the older copy back beside the person's own edit."""
        self.two_entries()
        self.stop(stop_before_subject=changes.MOVE_SUBJECT)
        support.write(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_TWO + ".md"),
            old_entry(ENTRY_TWO, "words of my own"),
        )

        changes.abandon(self.root, self.base_id, today=TODAY)

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        problems = [row.error for row in rows if row.entry is None]
        self.assertNotIn(base_reader.CODE_IN_BOTH_FOLDERS, problems)

    def test_after_the_move_is_saved_it_says_what_state_the_base_is_in(self):
        """N6 (b). It said the base was as it was, and it was not."""
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        self.stop(stop_after_subject=changes.MOVE_SUBJECT)

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertNotIn("as it was", result.sentence)
        self.assertIn("half", result.sentence.lower())

    def test_the_rest_can_still_be_offered_and_finished_afterwards(self):
        """N6 (b). A half updated base must not fall off the edge."""
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        self.stop(stop_after_subject=changes.MOVE_SUBJECT)
        changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertTrue(changes.needed(self.root), "there is still work to do")
        self.assertEqual(
            changes.OFFER_NOW,
            changes.what_to_offer(self.root, self.base_id, today=TODAY),
        )
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertTrue(result.ok, result.sentence)
        landed = support.read(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.assertIn("happened_on:", landed)
        self.assertNotIn("decided_", landed)

    def test_it_keeps_the_note_when_it_could_not_do_what_it_said(self):
        """N6 (c). It cleared the note even when every act failed."""
        self.two_entries()
        self.stop(stop_before_subject=changes.MOVE_SUBJECT)

        result = changes.abandon(
            self.root, self.base_id, today=TODAY, git=_FailOn(("rm", "checkout"))
        )

        self.assertFalse(result.ok, result.sentence)
        self.assertTrue(os.path.exists(self.note_path()))

    def test_a_note_it_cannot_read_is_kept_and_said_so(self):
        """N6 (d). It deleted the note and claimed it had put things back."""
        import json

        self.two_entries()
        self.stop(stop_before_subject=changes.MOVE_SUBJECT)
        with open(self.note_path(), "w", encoding="utf-8") as handle:
            json.dump({"schema": 1, "base_root": "/somewhere/else"}, handle)

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertFalse(result.ok, result.sentence)
        self.assertTrue(os.path.exists(self.note_path()))
        self.assertNotIn("as it was", result.sentence)


class TestAnUnreadableCopyBesideAReadableOne(MigrationCase):
    """N7. One copy nothing can read is still two copies of one change."""

    def test_it_is_named_as_a_change_written_down_twice(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE).replace("status: open", "status: open\nextra: x"),
        )
        self.save()

        rows = base_reader.ledger(self.root, self.base_id, TODAY, collect=[])
        problems = [row.error for row in rows if row.entry is None]

        self.assertIn(base_reader.CODE_IN_BOTH_FOLDERS, problems)

    def test_the_run_names_it_rather_than_counting_it(self):
        from gtmbase import stale_check

        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(
            constants.CHANGES_DIR,
            ENTRY_ONE,
            new_entry(ENTRY_ONE).replace("status: open", "status: open\nextra: x"),
        )
        self.save()

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            dry_run=True,
        )

        self.assertIn(ENTRY_ONE, " ".join(result.sentences))

    def test_one_thing_is_said_as_one_thing(self):
        from gtmbase import stale_check

        self.put(constants.LEGACY_CHANGES_DIR, "a-note", old_entry(ENTRY_TWO))
        self.save()

        result = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            dry_run=True,
        )

        said = " ".join(result.sentences)
        self.assertNotIn("1 things", said)
        self.assertIn("1 thing ", said)


class TestAFailedFirstRunReallyLeavesItAsItWas(MigrationCase):
    """N8. It said so while renames were still staged."""

    def test_it_puts_back_before_it_says_the_base_is_as_it_was(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

        result = changes.migrate(
            self.root,
            self.base_id,
            today=TODAY,
            git=_FailOnCommit(changes.MOVE_SUBJECT),
        )

        self.assertFalse(result.ok, result.sentence)
        if "as it was" in result.sentence:
            self.assertEqual(
                "",
                GitRunner().run(
                    ["status", "--porcelain"], cwd=self.root
                ).stdout.strip(),
                "it said the base was as it was and it was not",
            )

    def test_a_retry_after_that_still_works(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.save()
        changes.migrate(
            self.root,
            self.base_id,
            today=TODAY,
            git=_FailOnCommit(changes.MOVE_SUBJECT),
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE], sorted(self.entries_now()))


class TestTheDeclineCanActuallyBeGiven(MigrationCase):
    """D-M1's remainder: nothing could record a decline outside a test."""

    def run_script(self, *options):
        import subprocess

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        return subprocess.run(
            [sys.executable, script] + list(options),
            cwd=support.where_a_script_runs(self.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, TZ="America/Los_Angeles"),
        )

    def test_the_step_records_it_and_the_offer_goes_quiet(self):
        self.old_layout()
        self.assertEqual(
            changes.OFFER_NOW,
            changes.what_to_offer(self.root, self.base_id, today=TODAY),
        )

        finished = self.run_script("--not-now-move")

        self.assertEqual(0, finished.returncode, finished.stderr.decode("utf-8"))
        self.assertEqual(
            changes.OFFER_NONE,
            changes.what_to_offer(self.root, self.base_id, today=TODAY),
        )

    def test_the_skill_names_the_step(self):
        text = support.read(
            os.path.join(
                support.PLUGIN_DIR, "skills", "stale-check", "SKILL.md"
            )
        )
        self.assertIn("--not-now-move", text)


class TestTheReadOnlyCheck(MigrationCase):
    """The pre-flight the owner can run on a real base before anything."""

    def run_script(self, *options):
        import subprocess

        script = os.path.join(
            support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
        )
        return subprocess.run(
            [sys.executable, script] + list(options),
            cwd=support.where_a_script_runs(self.root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(os.environ, TZ="America/Los_Angeles"),
        )

    def test_it_says_what_would_happen_and_writes_nothing(self):
        self.old_layout()
        before = support.head_of(self.root)

        finished = self.run_script("--check-move")

        self.assertEqual(0, finished.returncode, finished.stderr.decode("utf-8"))
        self.assertEqual(before, support.head_of(self.root))
        self.assertEqual(
            [ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR)
        )
        said = finished.stdout.decode("utf-8")
        # How many, in words, and never which ones by identifier (finding 4
        # of the release A live check: this used to print the change's id).
        self.assertIn("update one of your context changes", said)
        self.assertNotIn(ENTRY_ONE, said)

    def test_it_counts_in_words_and_names_no_identifier(self):
        """Finding 4 of the release A live check, with more than one change."""
        self.old_layout((ENTRY_ONE, ENTRY_TWO))

        said = self.run_script("--check-move").stdout.decode("utf-8")

        self.assertIn("update two of your context changes", said)
        for entry_id in (ENTRY_ONE, ENTRY_TWO):
            self.assertNotIn(entry_id, said)
        self.assertNotIn("stg-", said)
        self.assertEqual([], plain_language.find_dashes(said))

    def test_a_count_reads_as_a_person_says_it(self):
        self.assertEqual("one", changes.counted(1))
        self.assertEqual("three", changes.counted(3))
        self.assertEqual("ten", changes.counted(10))
        self.assertEqual("11", changes.counted(11))

    def test_it_names_the_document_that_would_stop_it(self):
        self.put(
            constants.LEGACY_CHANGES_DIR,
            ENTRY_ONE,
            old_entry(ENTRY_ONE).replace(
                "decided_on: 2026-01-12\n",
                "decided_on: 2026-01-12\nhappened_on: 2026-01-05\n",
            ),
        )
        self.save()

        finished = self.run_script("--check-move")

        said = finished.stdout.decode("utf-8") + finished.stderr.decode("utf-8")
        self.assertIn(ENTRY_ONE, said)

    def test_it_says_whether_the_offer_would_be_made(self):
        self.old_layout()
        said = self.run_script("--check-move").stdout.decode("utf-8")
        self.assertIn("offer", said.lower())


# --- The last of the smaller things -------------------------------------------


class TestWhatCountsAsThisRunsOwnWork(MigrationCase):
    """A low finding: an edit that only changes line endings is still an edit."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def test_changing_only_the_line_endings_counts_as_the_persons_own_work(self):
        self.old_layout()
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass
        landed = os.path.join(
            self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md"
        )
        theirs = support.read(landed).replace("\n", "\r\n")
        write_exactly(landed, theirs)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertEqual(changes.STATUS_REFUSED, result.status)
        self.assertEqual(changes.CODE_UNSAVED_EDITS, result.code)
        with open(landed, "rb") as handle:
            self.assertIn(b"\r\n", handle.read())


class TestPuttingBackIsItselfInterrupted(MigrationCase):
    """Injection inside the act phase, and around the removals in commit one."""

    def two_entries(self):
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

    def stopped_before_the_move_was_saved(self):
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            return
        self.fail("the run was meant to stop and did not")

    def test_a_put_back_that_fails_half_way_can_still_be_finished(self):
        self.two_entries()
        self.stopped_before_the_move_was_saved()

        # The second undo is refused, so the put-back gets half way.
        counted = {"seen": 0}

        class _FailOnTheSecondRemoval(object):
            def __init__(self):
                self.inner = GitRunner()

            def run(self, args, cwd=None, timeout=20, input=None):
                arguments = [str(item) for item in args]
                if arguments and arguments[0] == "rm":
                    counted["seen"] += 1
                    if counted["seen"] == 2:
                        return _Failed()
                return self.inner.run(
                    arguments, cwd=cwd, timeout=timeout, input=input
                )

            def check(self, args, cwd=None, timeout=20, input=None):
                result = self.run(args, cwd=cwd, timeout=timeout, input=input)
                if not result.ok:
                    raise GitError("git-failed", code="git-failed", result=result)
                return result

        changes.migrate(
            self.root, self.base_id, today=TODAY, git=_FailOnTheSecondRemoval()
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def test_every_change_survives_a_put_back_that_was_killed_in_the_middle(self):
        self.two_entries()
        self.stopped_before_the_move_was_saved()
        # Killed between taking one out of the index and taking it off the
        # disk, which is a state no single command leaves behind.
        GitRunner().run(
            [
                "rm",
                "-q",
                "-f",
                "--cached",
                "--",
                constants.CHANGES_DIR + "/" + ENTRY_ONE + ".md",
            ],
            cwd=self.root,
        )

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))

    def test_a_removal_in_the_first_saved_change_can_be_interrupted(self):
        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_ONE, old_entry(ENTRY_ONE))
        self.put(constants.LEGACY_CHANGES_DIR, ENTRY_TWO, old_entry(ENTRY_TWO))
        self.save()

        class _StopOnTheRemoval(object):
            def __init__(self):
                self.inner = GitRunner()

            def run(self, args, cwd=None, timeout=20, input=None):
                arguments = [str(item) for item in args]
                if arguments and arguments[0] == "rm" and "-f" in arguments:
                    raise _Stopped()
                return self.inner.run(
                    arguments, cwd=cwd, timeout=timeout, input=input
                )

            def check(self, args, cwd=None, timeout=20, input=None):
                result = self.run(args, cwd=cwd, timeout=timeout, input=input)
                if not result.ok:
                    raise GitError("git-failed", code="git-failed", result=result)
                return result

        try:
            changes.migrate(
                self.root, self.base_id, today=TODAY, git=_StopOnTheRemoval()
            )
        except _Stopped:
            pass

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([ENTRY_ONE, ENTRY_TWO], sorted(self.entries_now()))


# --- The person saves the half done move themselves ---------------------------


class TestTheyCommittedTheMoveThemselves(MigrationCase):
    """R1. A run killed before its first save, then saved by the person.

    GTM Base had not saved the move, so its note says it never landed. The
    person saved it anyway, which is a perfectly ordinary thing to do with a
    staged change sitting in front of them. Every retry then refused with a
    sentence saying the file was never saved and telling them to save their
    base, on a base with nothing left to save, and never mentioned the one
    step that would have got them out of it.
    """

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def they_saved_it(self):
        self.old_layout()
        runner = _StopAfter(stop_before_subject=changes.MOVE_SUBJECT)
        try:
            changes.migrate(self.root, self.base_id, today=TODAY, git=runner)
        except _Stopped:
            pass
        support.git(["add", "-A"], cwd=self.root)
        support.git(
            ["commit", "-q", "-m", "wip: my own save of everything"],
            cwd=self.root,
        )

    def test_the_next_run_finishes_it_rather_than_refusing(self):
        self.they_saved_it()

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, "%s: %s" % (result.code, result.sentence))
        self.assertFalse(os.path.exists(self.note_path()))
        landed = support.read(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.assertIn("happened_on:", landed)
        self.assertNotIn("decided_", landed)

    def test_it_leaves_the_base_clean(self):
        self.they_saved_it()
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(
            "",
            GitRunner().run(
                ["status", "--porcelain"], cwd=self.root
            ).stdout.strip(),
        )
        self.assertEqual([ENTRY_ONE], sorted(self.entries_now()))

    def test_the_record_it_writes_is_the_one_it_would_have_written(self):
        self.they_saved_it()
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(1, len(self.corrections()), self.corrections())

    def test_giving_up_is_named_wherever_it_is_still_the_way_out(self):
        """The sentence that wedged them never said what to do instead."""
        self.assertIn("give up", changes.CANNOT_PUT_BACK.lower())


# --- Giving up with the record written and not saved --------------------------


class TestGivingUpTakesAwayItsOwnLeftovers(MigrationCase):
    """R2. The record it had written stayed, and every later run refused."""

    def note_path(self):
        from gtmbase import paths

        return os.path.join(paths.seat_dir(self.base_id), changes.JOURNAL_FILE)

    def stopped_with_the_record_written(self):
        self.old_layout()
        # One entry is rewritten, then the record is written, and the run is
        # killed before that record is saved.
        with _StopOnWrite(after=2):
            try:
                changes.migrate(self.root, self.base_id, today=TODAY)
            except _Stopped:
                return
        self.fail("the run was meant to stop and did not")

    def test_giving_up_takes_the_unsaved_record_away(self):
        self.stopped_with_the_record_written()
        self.assertEqual(1, len(self.corrections()), "the record should be there")

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, result.sentence)
        self.assertEqual([], self.corrections())

    def test_it_leaves_nothing_for_the_next_run_to_trip_over(self):
        self.stopped_with_the_record_written()
        changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertEqual(
            "",
            GitRunner().run(
                ["status", "--porcelain"], cwd=self.root
            ).stdout.strip(),
        )

    def test_the_next_run_really_does_finish(self):
        self.stopped_with_the_record_written()
        changes.abandon(self.root, self.base_id, today=TODAY)

        result = changes.migrate(self.root, self.base_id, today=TODAY)

        self.assertTrue(result.ok, "%s: %s" % (result.code, result.sentence))
        self.assertEqual([ENTRY_ONE], sorted(self.entries_now()))

    def test_it_keeps_the_note_when_it_cannot_clear_up_after_itself(self):
        self.stopped_with_the_record_written()

        result = changes.abandon(
            self.root,
            self.base_id,
            today=TODAY,
            git=_FailOn(("rm", "checkout")),
        )

        self.assertFalse(result.ok, result.sentence)
        self.assertTrue(os.path.exists(self.note_path()))

    def test_it_claims_nothing_about_what_the_files_now_say(self):
        """The rewrite had already landed, so saying otherwise is a lie.

        Giving up after the record was written is giving up on a base whose
        settings really were renamed and saved. An earlier wording said they
        still carried their older names, which was true in one of the two
        states this sentence covers and false in the other.
        """
        self.stopped_with_the_record_written()

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        landed = support.read(
            os.path.join(self.root, constants.CHANGES_DIR, ENTRY_ONE + ".md")
        )
        self.assertIn("happened_on:", landed)
        self.assertNotIn("older setting names", result.sentence)
        self.assertIn("half", result.sentence)

    def test_a_record_the_person_edited_is_left_alone_and_named(self):
        self.stopped_with_the_record_written()
        written = self.corrections()[0]
        support.write(
            os.path.join(self.root, constants.CORRECTIONS_DIR, written),
            "words of my own\n",
        )

        result = changes.abandon(self.root, self.base_id, today=TODAY)

        self.assertIn(written, result.sentence)
        self.assertEqual(
            "words of my own\n",
            support.read(
                os.path.join(self.root, constants.CORRECTIONS_DIR, written)
            ),
        )


# --- What everything else reads afterwards ------------------------------------


class TestWhatSurvivesTheMove(MigrationCase):
    def test_the_catches_number_is_the_same_before_and_after(self):
        from gtmbase import ids

        entry_id = ENTRY_ONE
        self.put(constants.LEGACY_CHANGES_DIR, entry_id, old_entry(entry_id))
        support.git(["add", "-A"], cwd=self.root)
        # The note a prepared proposal saves, which is what makes this a catch
        # rather than something the person typed out themselves.
        support.git(
            ["commit", "-q", "-m", "Proposal %s applied" % entry_id], cwd=self.root
        )
        correction = formats.CorrectionsFile(
            kind="correction",
            date=TODAY.isoformat(),
            staging_id=entry_id,
            entry_id=entry_id,
            source_id=SOURCE,
            intake_path="ledger",
            mode="none",
            third_party=False,
            content_hash=ids.content_hash("anything"),
            correction_class="new-decision",
            marker="gtm-base proposal %s entry %s source %s"
            % (entry_id, entry_id, SOURCE),
            touched_paths=["context/strategy/icp.md"],
            what_changed="Before: one thing.\n\nAfter: another thing.",
            why="Because the change said so.",
        )
        support.write(
            os.path.join(
                self.root, constants.CORRECTIONS_DIR, TODAY.isoformat() + "-one.md"
            ),
            correction.validate().render(),
        )
        support.git(["add", "-A"], cwd=self.root)
        support.git(["commit", "-q", "-m", "the record"], cwd=self.root)

        runner = GitRunner()
        before = report.catches(self.root, runner, TODAY)
        self.assertEqual(1, before["count"])

        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status)
        after = report.catches(self.root, runner, TODAY)
        self.assertEqual(before["count"], after["count"])
        self.assertEqual([entry_id], [item["entry_id"] for item in after["entries"]])

    def test_a_staged_proposal_naming_the_older_folder_is_still_accepted(self):
        from gtmbase import paths

        relative = constants.LEGACY_CHANGES_DIR + "/" + ENTRY_ONE + ".md"
        self.assertEqual(
            relative,
            paths.check_repo_path_syntax(relative, paths.PROPOSAL_PATH_PREFIXES),
        )

    def test_a_confirmation_naming_an_entry_still_settles_that_file(self):
        """A yes given before the move still settles the same file afterwards.

        The confirmation names the change by its identifier, and identifiers
        are the one thing the move never touches, so the file it settled has
        to be settled still. It is checked through the stale rules rather than
        by reading the line back, because what matters is the answer the rest
        of the product gets.
        """
        from gtmbase import base_reader as reader
        from gtmbase import stale

        self.old_layout()
        line = formats.ConfirmationLine(
            date="2026-01-13",
            time="12:00:00Z",
            file="context/strategy/icp.md",
            trigger=stale.TRIGGER_LEDGER,
            entry=ENTRY_ONE,
        )
        support.write(
            os.path.join(
                self.root,
                constants.CONFIRMATIONS_DIR,
                "context--strategy--icp.md",
            ),
            line.render() + "\n",
        )
        self.save("a confirmation")

        def flagged():
            inputs = reader.read_base(self.root, self.base_id, today=TODAY)
            report_now = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
                owner_email=None,
            )
            return [
                (flag.path, flag.entry_id)
                for flag in report_now.file_flags
                if flag.trigger == stale.TRIGGER_LEDGER
            ]

        before = flagged()
        self.assertEqual([], before, "the yes should have settled it already")
        result = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, result.status)
        self.assertEqual(before, flagged())
        after = self.entries_now()[ENTRY_ONE]
        self.assertEqual(ENTRY_ONE, after.id)


class TestTheOfferAndTheYes(MigrationCase):
    """Nothing moves until the person says so, and the review is where it asks."""

    def review(self):
        from gtmbase import stale_check

        return stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )

    def test_the_review_offers_the_move_and_moves_nothing(self):
        from gtmbase import stale_check

        self.old_layout()
        before = support.head_of(self.root)

        result = self.review()

        self.assertIn(changes.OFFER, result.sentences)
        self.assertIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)
        self.assertEqual(before, support.head_of(self.root))
        self.assertEqual(
            [ENTRY_ONE + ".md"], self.files_in(constants.LEGACY_CHANGES_DIR)
        )

    def test_a_base_with_nothing_to_move_is_never_offered_it(self):
        from gtmbase import stale_check

        self.put(constants.CHANGES_DIR, ENTRY_ONE, new_entry(ENTRY_ONE))
        self.save()

        result = self.review()

        self.assertNotIn(changes.OFFER, result.sentences)
        self.assertNotIn(stale_check.CODE_CHANGES_CAN_MOVE, result.codes)

    def test_the_offer_is_gone_once_the_move_has_been_made(self):
        self.old_layout()
        self.assertTrue(changes.needed(self.root))
        changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertFalse(changes.needed(self.root))
        self.assertNotIn(changes.OFFER, self.review().sentences)

    def test_asking_whether_it_is_needed_opens_no_file(self):
        """The question is cheap enough to ask on the way past."""
        self.old_layout()
        opened = []
        real_open = open

        def watched(path, *rest, **options):
            opened.append(str(path))
            return real_open(path, *rest, **options)

        import builtins

        builtins.open = watched
        try:
            self.assertTrue(changes.needed(self.root))
        finally:
            builtins.open = real_open
        self.assertEqual([], opened)


class TestTheWholeWayThroughOnAMigratedBase(MigrationCase):
    """Setup, a local edit, a review, a local approval, and the check at use."""

    def test_every_step_works_on_a_base_that_has_just_been_migrated(self):
        from gtmbase import approve_local, moment, stale_check

        self.old_layout()
        moved = changes.migrate(self.root, self.base_id, today=TODAY)
        self.assertEqual(changes.STATUS_MIGRATED, moved.status)

        # The moment of use: the profile has not caught up with the change.
        flag = moment.check(
            self.root,
            self.base_id,
            "context/strategy/icp.md",
            session_id="sess-1",
            now=TODAY,
        )
        self.assertTrue(flag.flagged, flag.sentences())
        self.assertEqual(ENTRY_ONE, flag.entry_id)

        # The review a person asks for lists it and prepares nothing twice.
        review = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
            mode="review",
        )
        self.assertIn(
            "context/strategy/icp.md",
            " ".join(review.sentences) + " ".join(line.path for line in review.review),
        )
        # The offer to move is gone, because there is nothing left to move.
        self.assertNotIn(stale_check.CODE_CHANGES_CAN_MOVE, review.codes)
        self.assertNotIn(changes.OFFER, review.sentences)

        # An ordinary run prepares one edit, and the owner approves it here,
        # because this base has no shared copy of its own to send it to.
        run = stale_check.run(
            self.root,
            self.base_id,
            gh=support.RecordingGh(),
            now=TODAY,
            session_id="sess-1",
        )
        prepared = [item for item in run.staged if item.entry_id == ENTRY_ONE]
        self.assertEqual(1, len(prepared), run.lines())

        # The real wording goes in before anybody is asked, because the note
        # GTM Base wrote asking for it is not approvable (finding A6 of the
        # 2026-09-20 review).
        support.write_the_replacement(
            prepared[0].path, "We sell to companies of twenty to two hundred people.\n"
        )

        shown = approve_local.show(
            prepared[0].path, self.root, self.base_id, now=TODAY
        )
        self.assertEqual(approve_local.STATUS_SHOWN, shown.status, shown.reasons)
        # The four lines are built from the migrated change, so the day it
        # happened is read off the file the move left behind.
        self.assertIn("What changed:", shown.artifact)
        self.assertIn("2026-01-12", shown.artifact)
        self.assertIn("When to look again: 2026-04-12", shown.artifact)

        applied = approve_local.approve(
            prepared[0].path,
            self.root,
            self.base_id,
            shown.shown_hash,
            now=datetime.datetime(2026, 9, 20, 12, 0, 0),
        )
        self.assertEqual(
            approve_local.STATUS_APPLIED, applied.status, applied.reasons
        )

        # And the file it changed is settled afterwards, so the same flag does
        # not come back the moment the person looks at it again.
        settled = moment.check(
            self.root,
            self.base_id,
            "context/strategy/icp.md",
            session_id="sess-2",
            now=TODAY,
        )
        self.assertFalse(settled.flagged, settled.sentences())


# --- The limit this release does not fix --------------------------------------


# The rule the entry parser shipped in 0.2.6 used, copied here as a frozen
# snapshot so this test says what that release does rather than what the
# library does today. It is deliberately not imported: the point of the test is
# that the shipped code and the code here have parted ways.
V026_REQUIRED = (
    "id",
    "kind",
    "decided_on",
    "written_on",
    "decided_by",
    "source",
    "review_by",
    "origin",
    "status",
)
V026_KIND = "decision"


def parses_on_0_2_6(text):
    """Whether the parser shipped in 0.2.6 would have read this entry."""
    try:
        block, _body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except Exception:
        return False
    for name in V026_REQUIRED:
        if name not in fields:
            return False
    return str(fields["kind"]).strip() == V026_KIND


class TestTheRecordedLimit(unittest.TestCase):
    """A seat on 0.2.6 reads a migrated base as empty. This is not fixed here.

    It is written down as a test so the limit is something the next release
    reads rather than something a second person finds out by being told their
    base is empty. Every seat updates before a base is migrated.
    """

    def test_the_0_2_6_parser_reads_no_entry_in_the_new_layout(self):
        self.assertFalse(parses_on_0_2_6(new_entry(ENTRY_ONE)))

    def test_the_0_2_6_parser_still_reads_the_older_layout(self):
        self.assertTrue(parses_on_0_2_6(old_entry(ENTRY_ONE)))

    def test_the_parser_shipped_today_reads_both(self):
        self.assertEqual(ENTRY_ONE, formats.ChangeEntry.parse(new_entry(ENTRY_ONE)).id)
        self.assertEqual(ENTRY_ONE, formats.ChangeEntry.parse(old_entry(ENTRY_ONE)).id)


if __name__ == "__main__":
    unittest.main()
