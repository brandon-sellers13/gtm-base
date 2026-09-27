"""0.3.3: a context change can be recorded at any time, without editing a document.

The 0.3.1 live check (2026-09-27) found the gap. A context change could be
written down at the closing of setting a base up, which needs a setup run, or
together with an edit somebody made to a document by hand. Somebody who learns
that something about the business changed, or that a fact the company states is
different now, had nowhere to say so on its own, and a change nobody writes
down flags nothing.

Every scenario here runs the real script the stale-check skill tells the
assistant to run, in the order a person lives through it, on a real base in a
temporary folder. The script-running classes run a second time from a folder
linked to the base (tests/run.sh), and one class runs from a linked folder
every time.
"""

import datetime
import importlib.util
import io
import os
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout

import plain_language
import support
import test_moment_of_use as moment_tests

from gtmbase import (
    changes,
    confirm,
    constants,
    formats,
    join_flow,
    machine,
    moment,
    paths,
    record_change,
    review,
    session_start,
    stale_check,
    state,
)

ICP = moment_tests.ICP
POSITIONING = moment_tests.POSITIONING
MESSAGING = "context/strategy/messaging.md"
SOMEBODY_ELSES = "context/strategy/pricing.md"
OWNER = moment_tests.OWNER

SKILL = os.path.join(support.PLUGIN_DIR, "skills", "stale-check", "SKILL.md")
INJECTION = os.path.join(support.TEMPLATES_DIR, "injection.md")

WHAT = (
    "Our verified driver count is over 1 million since 2017, replacing the 500k "
    "a year we used to cite."
)
WHY = "A review of the full earnings database showed the real number."
SOURCE = "The data team's review in September."

MESSAGING_TEXT = """---
kind: messaging
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Messaging

## The headline

Half a million drivers a year trust us.
"""

PRICING_TEXT = """---
kind: pricing
owner: somebody@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Pricing

## Plans

One plan.
"""


def run_script(argv, cwd):
    """The stale-check skill's own script, started where the person stands."""
    path = os.path.join(support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py")
    spec = importlib.util.spec_from_file_location("gtmbase_script_record", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    here = os.getcwd()
    out, err = io.StringIO(), io.StringIO()
    os.chdir(support.where_a_script_runs(cwd))
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = module.main([str(item) for item in argv])
    finally:
        os.chdir(here)
    return code, out.getvalue(), err.getvalue()


def value_on(printed, name):
    found = re.search(r"\b%s=(\S+)" % re.escape(name), printed)
    return found.group(1) if found else None


def head_of(root):
    return support.head_of(root)


def status_of(root):
    return support.git(
        ["status", "--porcelain", "--untracked-files=all"], cwd=root
    ).stdout.decode("utf-8")


def entry_files(root):
    found = []
    for folder in (constants.CHANGES_DIR, constants.LEGACY_CHANGES_DIR):
        full = os.path.join(root, folder)
        if os.path.isdir(full):
            found.extend(folder + "/" + name for name in sorted(os.listdir(full)))
    return found


def _started(flow, argv, cwd=None):
    """One step of the flow, started in the folder the test chose.

    A test that names a folder of its own is run there and never swapped for
    another. Otherwise the script starts where `support.where_a_script_runs`
    says, which is the base, or a folder linked to it on the second run.
    """
    where = cwd or flow.cwd
    if where == flow.root:
        return run_script(argv, flow.root)
    here = os.getcwd()
    out, err = io.StringIO(), io.StringIO()
    path = os.path.join(
        support.PLUGIN_DIR, "skills", "stale-check", "scripts", "stale_check.py"
    )
    spec = importlib.util.spec_from_file_location("gtmbase_script_rc2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    os.chdir(where)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = module.main([str(item) for item in argv])
    finally:
        os.chdir(here)
    return code, out.getvalue(), err.getvalue()


def _words_file(flow, kind, text):
    """Ask the script for a words file, the way the skill does, and fill it."""
    code, out, err = _started(flow, ["--new-words-file", kind])
    flow.case.assertEqual(0, code, out + err)
    path = value_on(out, "words")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def _shown(flow, numbers="1,2", what=WHAT, why=WHY, source=SOURCE, extra=()):
    argv = ["--record-change", "show", "--documents", numbers]
    if what is not None:
        argv += ["--what-changed-file", _words_file(flow, "what-changed", what)]
    if why is not None:
        argv += ["--reason-file", _words_file(flow, "reason", why)]
    if source is not None:
        argv += ["--source-file", _words_file(flow, "source", source)]
    return _started(flow, argv + list(extra))


def _shown_and_recorded(flow, numbers="1,2", **given):
    code, out, err = _shown(flow, numbers, **given)
    flow.case.assertEqual(0, code, out + err)
    shown = value_on(out, "shown")
    flow.case.assertTrue(shown, out)
    code, out, err = _started(flow, ["--record-change", "record", "--shown", shown])
    flow.case.assertEqual(0, code, out + err)
    return out


def _answered(flow, change, document, given):
    return _started(
        flow,
        [
            "--record-change",
            "answer",
            "--change",
            change,
            "--document",
            document,
            "--answer",
            given,
        ],
    )


class Flow(object):
    """One person recording one context change, step by step, through the script.

    Its methods only name the steps. What each one runs is a function of its
    own, so tests/test_linked_folder.py finds the classes that start a script
    by the steps they call, and this helper is not mistaken for one of them.
    """

    def __init__(self, case, root, cwd=None):
        self.case = case
        self.root = root
        self.cwd = cwd or root

    def run(self, argv, cwd=None):
        return _started(self, argv, cwd)

    def show(self, numbers="1,2", **given):
        return _shown(self, numbers, **given)

    def shown_and_recorded(self, numbers="1,2", **given):
        return _shown_and_recorded(self, numbers, **given)

    def answer(self, change, document, given):
        return _answered(self, change, document, given)


class LocalCase(unittest.TestCase):
    """A base with no shared copy, its customer profile and its positioning."""

    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)
        self.base = moment_tests.Base(self.sandbox)
        self.flow = Flow(self, self.base.root)


# --- The whole flow ----------------------------------------------------------


class TestTheWholeFlowThroughTheScript(LocalCase):
    def test_ask_documents_show_record_and_the_three_answers(self):
        code, out, _err = self.flow.run(["--record-change", "ask"])
        self.assertEqual(0, code)
        self.assertIn(record_change.EXPLAIN, out)
        self.assertIn(record_change.ASK, out)

        code, out, _err = self.flow.run(["--record-change", "documents"])
        self.assertEqual(0, code)
        self.assertEqual(
            [record_change.DOCUMENTS_INTRO, "1. your customer profile", "2. your positioning"],
            out.strip().split("\n"),
        )
        self.assertNotIn("map", out)

        before = head_of(self.base.root)
        code, out, err = self.flow.show("1,2")
        self.assertEqual(0, code, out + err)
        self.assertIn(join_flow.CHANGE_OPEN, out)
        self.assertIn("What changed: Our verified driver count", out)
        self.assertIn("Why: " + WHY, out)
        self.assertIn("What it affects: your customer profile, your positioning", out)
        self.assertIn(join_flow.ARTIFACT_OPEN, out)
        self.assertIn(moment.FENCE_NOTE, out)
        self.assertIn(record_change.PREVIEW_ASK, out)
        # The wrapper above the whole entry names documents the way a person does.
        wrapper = out.split(join_flow.ARTIFACT_OPEN)[0]
        self.assertNotIn("context/strategy", wrapper)
        self.assertNotIn("stg-", wrapper)

        # Nothing written before the yes.
        self.assertEqual(before, head_of(self.base.root))
        self.assertEqual("", status_of(self.base.root))
        self.assertEqual([], entry_files(self.base.root))

        shown = value_on(out, "shown")
        code, out, err = self.flow.run(["--record-change", "record", "--shown", shown])
        self.assertEqual(0, code, out + err)
        self.assertIn(record_change.RECORDED, out)
        self.assertIn("Does your customer profile already say what that change says?", out)
        self.assertIn("Does your positioning already say what that change says?", out)

        written = entry_files(self.base.root)
        self.assertEqual(1, len(written))
        self.assertTrue(written[0].startswith(constants.CHANGES_DIR + "/"))
        text = support.read(os.path.join(self.base.root, written[0]))
        entry = formats.ChangeEntry.parse(text)
        self.assertIsNone(entry.run_id)
        self.assertNotIn("run_id", text)
        self.assertEqual(record_change.ORIGIN, entry.origin)
        self.assertEqual(OWNER, entry.noted_by)
        self.assertEqual(SOURCE, entry.source)
        self.assertEqual([ICP, POSITIONING], entry.affects)
        self.assertEqual(WHAT + "\n\n" + WHY, entry.body)
        change = value_on(out, "change")
        self.assertEqual(entry.id, change)

        # One saved change holding the entry and nothing else.
        saved = support.git(
            ["show", "--name-only", "--format=%s", "HEAD"], cwd=self.base.root
        ).stdout.decode("utf-8").split()
        self.assertEqual([record_change.SAVE_MESSAGE.split()[0]], saved[:1])
        self.assertEqual(written[0], saved[-1])
        self.assertEqual("", status_of(self.base.root))

        # Both documents are flagged until somebody answers.
        self.assertTrue(self.base.flagged_today())

        # Not now: nothing written, still flagged.
        head = head_of(self.base.root)
        code, out, _err = self.flow.answer(change, ICP, "not-now")
        self.assertEqual(0, code)
        self.assertEqual(
            record_change.LEFT_FLAGGED % "Your customer profile", out.strip()
        )
        self.assertEqual(head, head_of(self.base.root))
        self.assertEqual("", status_of(self.base.root))
        self.assertTrue(self.base.flagged_today())

        # Yes: one confirmation line naming this change.
        code, out, err = self.flow.answer(change, POSITIONING, "yes")
        self.assertEqual(0, code, out + err)
        self.assertIn(
            join_flow.RECONCILE_RECORDED % "your positioning", out
        )
        line_file = os.path.join(
            self.base.root, confirm.confirmations_path_for(POSITIONING)
        )
        lines = [
            line
            for line in support.read(line_file).splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(1, len(lines))
        self.assertIn("entry=%s" % change, lines[0])
        self.assertFalse(
            moment.check(
                self.base.root, self.base.base_id, POSITIONING,
                session_id=moment_tests.SESSION, now=state.today(),
            ).flagged
        )

        # No: a fix prepared, waiting for its owner, the document still flagged.
        code, out, err = self.flow.answer(change, ICP, "no")
        self.assertEqual(0, code, out + err)
        prepared = value_on(out, "prepared")
        self.assertTrue(prepared and os.path.isfile(prepared), out)
        self.assertTrue(
            prepared.startswith(
                os.path.join(os.path.realpath(self.base.root), constants.PROPOSALS_PENDING_DIR)
            )
            or constants.PROPOSALS_PENDING_DIR.replace("/", os.sep) in prepared
        )
        self.assertTrue(self.base.flagged_today())

    def test_not_now_leaves_it_flagged_at_the_moment_of_use_and_in_the_review(self):
        code, out, _err = self.flow.run(["--review"])
        self.assertNotIn("has not caught up with a context change", out)

        out = self.flow.shown_and_recorded("1")
        change = value_on(out, "change")
        self.flow.answer(change, ICP, "not-now")

        ran = moment_tests.run_moment(
            ["--file", os.path.join(self.base.root, ICP)], self.base.root
        )
        self.assertIn("your customer profile has not caught up with a context change", ran.out)
        self.assertIn("What changed: Our verified driver count", ran.out)

        code, out, _err = self.flow.run(["--review"])
        self.assertEqual(0, code, out)
        self.assertIn(
            "your customer profile has not caught up with a context change recorded on %s"
            % state.today().isoformat(),
            out,
        )

    def test_a_document_nobody_answered_about_is_flagged_too(self):
        """Exactly as a closing change left without an answer is."""
        self.flow.shown_and_recorded("1,2")
        ran = moment_tests.run_moment(
            ["--file", os.path.join(self.base.root, POSITIONING)], self.base.root
        )
        self.assertIn("your positioning has not caught up", ran.out)


class TestNothingIsWrittenBeforeTheYes(LocalCase):
    def test_leave_it_writes_nothing_and_the_yes_is_gone(self):
        before = head_of(self.base.root)
        code, out, _err = self.flow.show("1")
        shown = value_on(out, "shown")
        code, out, _err = self.flow.run(["--record-change", "leave"])
        self.assertEqual(0, code)
        self.assertEqual(record_change.LEFT, out.strip())
        code, out, _err = self.flow.run(["--record-change", "record", "--shown", shown])
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOTHING_WAITING, out.strip())
        self.assertEqual(before, head_of(self.base.root))
        self.assertEqual([], entry_files(self.base.root))
        self.assertEqual("", status_of(self.base.root))

    def test_a_yes_bound_to_something_else_writes_nothing(self):
        self.flow.show("1")
        code, out, _err = self.flow.run(
            ["--record-change", "record", "--shown", "0" * 16]
        )
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOT_WHAT_WAS_SHOWN, out.strip())
        self.assertEqual([], entry_files(self.base.root))

    def test_a_record_with_nothing_shown_writes_nothing(self):
        code, out, _err = self.flow.run(["--record-change", "record", "--shown", "x"])
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOTHING_WAITING, out.strip())

    def test_a_correction_shows_it_again_and_only_the_last_showing_counts(self):
        _code, first, _err = self.flow.show("1")
        _code, second, _err = self.flow.show("1,2", why="Corrected reason.")
        code, out, _err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(first, "shown")]
        )
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOT_WHAT_WAS_SHOWN, out.strip())
        code, out, err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(second, "shown")]
        )
        self.assertEqual(0, code, out + err)
        entry = formats.ChangeEntry.parse(
            support.read(os.path.join(self.base.root, entry_files(self.base.root)[0]))
        )
        self.assertEqual([ICP, POSITIONING], entry.affects)
        self.assertIn("Corrected reason.", entry.body)

    def test_the_waiting_change_cannot_be_rewritten_from_the_base(self):
        """What is written is what was shown, held where no file tool writes."""
        _code, out, _err = self.flow.show("1")
        waiting = os.path.join(
            paths.seat_dir(self.base.base_id), record_change.WAITING_FILE
        )
        self.assertTrue(waiting.startswith(os.environ["GTM_BASE_HOME"]))
        payload = support.read(waiting).replace("Our verified", "Our invented")
        support.write(waiting, payload)
        code, said, _err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(out, "shown")]
        )
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOTHING_WAITING, said.strip())
        self.assertEqual([], entry_files(self.base.root))


class TestTheAsk(LocalCase):
    def test_explained_the_first_three_times_and_one_line_after(self):
        for _time in range(3):
            code, out, _err = self.flow.run(["--record-change", "ask"])
            self.assertIn(record_change.EXPLAIN, out)
            self.flow.shown_and_recorded("1", what="Change number %d." % _time)
        code, out, _err = self.flow.run(["--record-change", "ask"])
        self.assertEqual(record_change.ASK_SHORT, out.strip())
        code, out, _err = self.flow.run(["--record-change", "ask", "--long"])
        self.assertIn(record_change.EXPLAIN, out)
        self.assertEqual(3, record_change.times_recorded())

    def test_asking_does_not_count_and_leaving_does_not_count(self):
        for _time in range(4):
            self.flow.run(["--record-change", "ask"])
        self.flow.show("1")
        self.flow.run(["--record-change", "leave"])
        self.assertEqual(0, record_change.times_recorded())


class TestTheDocuments(LocalCase):
    def test_a_number_not_on_the_list_and_no_number_are_refused(self):
        for numbers, sentence in (
            ("3", record_change.NOT_ON_THE_LIST),
            ("0", record_change.NOT_ON_THE_LIST),
            ("one", record_change.NOT_ON_THE_LIST),
            ("", record_change.NEEDS_A_DOCUMENT),
        ):
            code, out, _err = self.flow.show(numbers)
            self.assertEqual(1, code, numbers)
            self.assertEqual(sentence, out.strip())

    def test_any_document_is_asked_about_and_one_nobody_here_owns_is_not(self):
        self.base.write(MESSAGING, MESSAGING_TEXT)
        self.base.write(SOMEBODY_ELSES, PRICING_TEXT)
        self.base.save("two more documents")
        code, out, _err = self.flow.run(["--record-change", "documents"])
        self.assertEqual(
            [
                record_change.DOCUMENTS_INTRO,
                "1. your customer profile",
                "2. your messaging",
                "3. your positioning",
                "4. your pricing",
            ],
            out.strip().split("\n"),
        )
        out = self.flow.shown_and_recorded("2,4")
        self.assertIn("Does your messaging already say what that change says?", out)
        self.assertNotIn("Does your pricing", out)
        self.assertIn(join_flow.NOT_OWNED_FLAGGED_ONE, out)
        change = value_on(out, "change")
        code, said, err = self.flow.answer(change, MESSAGING, "yes")
        self.assertEqual(0, code, said + err)
        self.assertIn(join_flow.RECONCILE_RECORDED % "your messaging", said)
        code, said, _err = self.flow.answer(change, SOMEBODY_ELSES, "yes")
        self.assertEqual(1, code)
        self.assertIn(confirm.NOT_YOUR_DOCUMENT % "your pricing", said)

    def test_an_answer_about_a_document_the_change_does_not_name_is_refused(self):
        out = self.flow.shown_and_recorded("1")
        change = value_on(out, "change")
        code, said, _err = self.flow.answer(change, POSITIONING, "yes")
        self.assertEqual(1, code)
        self.assertEqual(confirm.CHANGE_IS_NOT_ABOUT_IT % "your positioning", said.strip())
        code, said, _err = self.flow.answer(change, constants.MAP_PATH, "not-now")
        self.assertEqual(1, code)
        self.assertEqual(moment.NOT_A_CONTEXT_FILE, said.strip())
        code, said, _err = self.flow.answer(change, ICP, "maybe")
        self.assertEqual(1, code)
        self.assertEqual(record_change.ANSWER_UNKNOWN, said.strip())
        code, said, _err = self.flow.answer("stg-" + "0" * 16, ICP, "not-now")
        self.assertEqual(1, code)
        self.assertEqual(confirm.CHANGE_NOT_IN_THE_BASE % "your customer profile", said.strip())


class TestTheWords(LocalCase):
    def test_a_path_the_script_did_not_hand_out_is_refused(self):
        stray = os.path.join(self.sandbox.path, "notes.txt")
        support.write(stray, "private notes")
        code, out, _err = self.flow.run(
            ["--record-change", "show", "--documents", "1", "--what-changed-file", stray]
        )
        self.assertEqual(1, code)
        self.assertIn("That is not a file GTM Base handed out", out)
        self.assertEqual("private notes", support.read(stray))

    def test_a_contact_detail_is_refused_and_nothing_is_kept(self):
        code, out, _err = self.flow.show("1", source="Jane at jane@example.org told us.")
        self.assertEqual(1, code)
        self.assertIn("what you said contains", out)
        self.assertIn(record_change.SCREENED_NEXT, out)
        self.assertNotIn("jane@example.org", out)
        self.assertFalse(
            os.path.exists(
                os.path.join(paths.seat_dir(self.base.base_id), record_change.WAITING_FILE)
            )
        )

    def test_no_reason_and_no_source_still_show_honestly(self):
        code, out, err = self.flow.show("1", why=None, source=None)
        self.assertEqual(0, code, out + err)
        self.assertIn("Why: This was written down on", out)
        self.assertIn("source: %s" % record_change.SOURCE_WHEN_NONE, out)
        self.assertNotIn(join_flow.WHY_FROM_THE_CLOSING, out)

    def test_nothing_about_what_changed_is_refused(self):
        code, out, _err = self.flow.show("1", what="   ")
        self.assertEqual(1, code)
        self.assertEqual(record_change.NEEDS_WORDS, out.strip())

    def test_a_person_may_use_a_long_dash_and_quotes_in_their_own_words(self):
        dash = "—"
        code, out, err = self.flow.show(
            "1", what="We raised prices %s again." % dash, source='"The board", in June'
        )
        self.assertEqual(0, code, out + err)
        code, out, err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(out, "shown")]
        )
        self.assertEqual(0, code, out + err)
        entry = formats.ChangeEntry.parse(
            support.read(os.path.join(self.base.root, entry_files(self.base.root)[0]))
        )
        self.assertIn(dash, entry.body)
        self.assertEqual("'The board', in June", entry.source)

    def test_another_day_and_a_day_in_the_future(self):
        code, out, err = self.flow.show("1", extra=["--happened-on", "2026-01-15"])
        self.assertEqual(0, code, out + err)
        self.assertIn("The day it happened: 2026-01-15", out)
        tomorrow = (state.today() + datetime.timedelta(days=2)).isoformat()
        code, out, _err = self.flow.show("1", extra=["--happened-on", tomorrow])
        self.assertEqual(1, code)
        self.assertEqual(record_change.BAD_DAY, out.strip())


class TestTheIdentifier(LocalCase):
    def test_a_name_an_old_confirmation_still_carries_is_never_reused(self):
        """A change taken out by hand leaves lines behind that must not settle a new one."""
        first = review.entry_id(0)
        line = formats.ConfirmationLine(
            date="2026-01-02", time="10:00:00Z", file=ICP, trigger="ledger",
            entry=first, question=None, run=None,
        )
        path = os.path.join(self.base.root, confirm.confirmations_path_for(ICP))
        support.write(path, confirm.FILE_HEADER + line.render() + "\n")
        self.base.save("an old confirmation")
        out = self.flow.shown_and_recorded("1")
        change = value_on(out, "change")
        self.assertNotEqual(first, change)
        self.assertEqual(review.entry_id(1), change)
        self.assertTrue(self.base.flagged_today())


# --- Both layouts, and a base with a shared copy -----------------------------


class TestBothLayouts(unittest.TestCase):
    def test_a_base_still_on_the_older_folder(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            older = "stg-" + "b" * 16
            base.write(
                "%s/%s.md" % (constants.LEGACY_CHANGES_DIR, older),
                moment_tests.entry_text(entry_id=older, affects=(POSITIONING,)),
            )
            base.save("a change in the older folder")
            flow = Flow(self, base.root)
            out = flow.shown_and_recorded("1")
            change = value_on(out, "change")
            # Written where the closing writes one: the folder every change is
            # written to today, so one identifier never names two files.
            self.assertIn("%s/%s.md" % (constants.CHANGES_DIR, change), entry_files(base.root))
            self.assertIn("%s/%s.md" % (constants.LEGACY_CHANGES_DIR, older), entry_files(base.root))
            self.assertTrue(base.flagged_today())
            code, said, err = flow.answer(change, ICP, "yes")
            self.assertEqual(0, code, said + err)
            self.assertFalse(base.flagged_today())
            # The update of how changes are stored still works afterwards.
            code, said, err = flow.run(["--move-changes"])
            self.assertEqual(0, code, said + err)
            self.assertEqual(
                sorted(
                    [
                        "%s/%s.md" % (constants.CHANGES_DIR, change),
                        "%s/%s.md" % (constants.CHANGES_DIR, older),
                    ]
                ),
                sorted(entry_files(base.root)),
            )
            self.assertFalse(base.flagged_today())

    def test_a_base_on_the_newer_folder(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            base.add_change()
            flow = Flow(self, base.root)
            out = flow.shown_and_recorded("2")
            change = value_on(out, "change")
            self.assertEqual(
                sorted(
                    [
                        "%s/%s.md" % (constants.CHANGES_DIR, moment_tests.ENTRY),
                        "%s/%s.md" % (constants.CHANGES_DIR, change),
                    ]
                ),
                entry_files(base.root),
            )


class TestABaseWithASharedCopy(unittest.TestCase):
    def test_every_step_refuses_with_one_sentence_and_writes_nothing(self):
        with support.Sandbox() as sandbox:
            root, _base_id = sandbox.base()
            flow = Flow(self, root)
            before = head_of(root)
            for argv in (
                ["--record-change", "ask"],
                ["--record-change", "documents"],
                ["--record-change", "show", "--documents", "1"],
                ["--record-change", "record", "--shown", "x"],
                ["--record-change", "leave"],
                ["--record-change", "answer", "--change", "x", "--document", ICP, "--answer", "yes"],
            ):
                code, out, _err = flow.run(argv)
                self.assertEqual(1, code, argv)
                self.assertEqual(record_change.SHARED_COPY, out.strip(), argv)
            self.assertEqual(before, head_of(root))
            self.assertEqual([], entry_files(root))


# --- What stands in the way of a yes ----------------------------------------


class TestWhatStandsInTheWay(LocalCase):
    def test_a_finder_file_never_stops_it(self):
        _code, out, _err = self.flow.show("1")
        support.write(os.path.join(self.base.root, ".DS_Store"), "\x00\x00\x00\x01Bud1")
        support.write(os.path.join(self.base.root, "context", ".DS_Store"), "\x00Bud1")
        code, said, err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(out, "shown")]
        )
        self.assertEqual(0, code, said + err)
        self.assertEqual(1, len(entry_files(self.base.root)))
        saved = support.git(
            ["show", "--name-only", "--format=", "HEAD"], cwd=self.base.root
        ).stdout.decode("utf-8").split()
        self.assertEqual(entry_files(self.base.root), saved)

    def test_real_unsaved_work_stops_it_and_is_named(self):
        _code, out, _err = self.flow.show("1")
        support.write(os.path.join(self.base.root, "context", "notes.md"), "draft\n")
        before = head_of(self.base.root)
        code, said, _err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(out, "shown")]
        )
        self.assertEqual(1, code)
        self.assertEqual(
            record_change.UNSAVED_NAMED % "They are in your notes.", said.strip()
        )
        self.assertNotIn("context/notes.md", said)
        self.assertEqual(before, head_of(self.base.root))
        self.assertEqual([], entry_files(self.base.root))

    def test_off_the_main_line_it_stops(self):
        _code, out, _err = self.flow.show("1")
        support.git(["checkout", "-q", "-b", "elsewhere"], cwd=self.base.root)
        code, said, _err = self.flow.run(
            ["--record-change", "record", "--shown", value_on(out, "shown")]
        )
        self.assertEqual(1, code)
        self.assertEqual(record_change.NOT_ON_MAIN, said.strip())
        self.assertEqual([], entry_files(self.base.root))


# --- From a folder linked to the base, every time ---------------------------


class TestFromALinkedFolderEveryTime(unittest.TestCase):
    def test_the_whole_flow_from_the_folder_the_person_works_in(self):
        with support.Sandbox() as sandbox:
            base = moment_tests.Base(sandbox)
            folder = support.linked_folder_for(base.root)
            self.assertNotEqual(os.path.realpath(base.root), os.path.realpath(folder))
            flow = Flow(self, base.root, cwd=folder)
            code, out, _err = flow.run(["--record-change", "ask"])
            self.assertEqual(0, code, out)
            code, out, _err = flow.run(["--record-change", "documents"])
            self.assertIn("1. your customer profile", out)
            out = flow.shown_and_recorded("1")
            change = value_on(out, "change")
            code, said, err = flow.answer(change, ICP, "not-now")
            self.assertEqual(0, code, said + err)
            self.assertEqual(1, len(entry_files(base.root)))
            self.assertEqual([], [n for n in os.listdir(folder) if not n.startswith(".")])
            self.assertTrue(base.flagged_today())


# --- The rule the session carries, and the words ----------------------------


class TestTheRuleAndTheWords(unittest.TestCase):
    def test_the_session_rule_offers_once_and_never_records_without_a_yes(self):
        blocks = session_start.load_blocks(support.PLUGIN_DIR, "injection.md")
        moment_block = " ".join(blocks["moment"].split())
        self.assertIn("Shall I record that as a context change", moment_block)
        self.assertIn("Record nothing without", moment_block)
        self.assertIn("once", moment_block)

    def test_the_skill_says_it_the_way_the_lint_wants(self):
        plain_language.assert_plain(self, SKILL)
        plain_language.assert_standard(self, SKILL)
        # The rule is read by the assistant, and its older lines say "the
        # change" before the full term, so only the words and the dashes are
        # held to the lint here.
        rule = support.read(INJECTION)
        self.assertEqual([], plain_language.find_dashes(rule))
        self.assertEqual([], plain_language.find_banned(rule))
        self.assertEqual([], plain_language.find_banned_person_facing(rule))
        text = support.read(SKILL)
        self.assertIn("## Record a context change", text)
        self.assertIn("record a context change", text.split("---")[1])

    def test_every_sentence_this_added_is_registered_and_plain(self):
        registered = set(plain_language.PYTHON_SENTENCES)
        for module, name, _line in plain_language.library_sentence_constants(support.LIB_DIR):
            if module == "record_change":
                self.assertIn((module, name), registered)
        for name in (
            "EXPLAIN", "ASK", "ASK_SHORT", "PREVIEW_ASK", "RECORDED", "LEFT_FLAGGED",
            "SHARED_COPY", "UNSAVED_NAMED",
        ):
            text = getattr(record_change, name)
            self.assertEqual([], plain_language.find_dashes(text), name)
            self.assertEqual([], plain_language.find_banned(text), name)
            self.assertEqual([], plain_language.find_banned_person_facing(text), name)


if __name__ == "__main__":
    unittest.main()
