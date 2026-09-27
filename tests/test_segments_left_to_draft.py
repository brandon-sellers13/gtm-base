"""Brandon's call 29: a segment settled to be drafted but not drafted before the closing.

Setup settles which segments a base will hold (Unit 1.7a), and each segment
settled to be drafted is drafted in step 6c, before the closing. Drafting
reads the person's own material, and the yes to read it is the run's, which
the closing clears. So a segment nobody drafted before the closing could
never be finished. Brandon decided on 2026-09-27 that a later session asks
again for consent to the material and finishes it.

What is kept past the closing is the import record Unit 1.7d already keeps
in this seat's own folder for the base: the segment's name and settled
answer, which the inventory already holds, and one per-file state. It never
holds the material, a draft, or a yes to read anything. A later session
drafts the segment in a run of its own, after the same survey-free consent
step Unit 1.6 built: only the numbered document the record kept for that
segment is offered, the person may add a folder or drop a file, a changed
list asks again, and nothing is read before the yes. The draft is shown whole
and approved exactly as step 6c, and a stop at any step that changes anything
is finished, taken back, or drafted again by the next session.

Every scenario runs in a sandbox with a temporary home and a temporary seat
folder, so nothing here reaches anybody's real folders.
"""

import io
import json
import os
import shutil
import unittest

import plain_language
import support
import test_adoption as adoption
import test_import_recovery as recovery

from gtmbase import (
    confirm,
    constants,
    drafting,
    join_flow,
    review,
    segments,
    session_start,
)
from gtmbase.errors import ConsentError, DraftError, ReviewError

TODAY = adoption.TODAY
NOW = adoption.NOW
EMAIL = adoption.EMAIL
SESSION_TWO = "s-a-later-session"

# Taken in from its finished page during setup (Unit 1.7c).
TAKEN_IN = "Fintech lenders"
# Drafted during setup, in step 6c.
DRAFTED = "Credit unions"
# Settled to be drafted, and not drafted before the closing.
LATER = "Regional banks"
NAMES = (TAKEN_IN, LATER, DRAFTED)
ANSWERS = {LATER: constants.SEGMENT_DRAFT, DRAFTED: constants.SEGMENT_DRAFT}

FINISH = "finish setting up my base"
UMBRELLA = "context/icps.md"


def slug(name):
    return segments.slug_for(name)


def pages():
    return [(name, adoption.clean_page(name), "icp-%s.md" % slug(name)) for name in NAMES]


def segment_text(name):
    """The segment fixture, written about one named segment."""
    return adoption.drafted("segment.md").replace("# Fintech lenders", "# %s" % name)


def write_draft(run_id, name):
    settled = join_flow.segment_to_draft(run_id, slug(name))
    path = join_flow.draft_path(run_id, drafting.STEP_SEGMENT, settled)
    with io.open(path, "w", encoding="utf-8") as handle:
        handle.write(segment_text(name))
    return path


def approve(run_id, company, name, **kwargs):
    """Approve one segment's draft, exactly as step 6c does."""
    return join_flow.approve_step(
        drafting.STEP_SEGMENT,
        write_draft(run_id, name),
        run_id,
        base_root=company.root,
        now=NOW,
        segment=slug(name),
        **kwargs
    )


def close(company):
    return join_flow.close_run(
        company.root, company.run, now=TODAY, plugin_root=support.PLUGIN_DIR
    )


def resume(company, run_id=None):
    run_id = run_id or join_flow.new_run(TODAY)
    return run_id, join_flow.resume_import(run_id, company.root, SESSION_TWO, now=NOW)


def listed(company, name, run_id=None, **kwargs):
    run_id = run_id or join_flow.new_run(TODAY)
    return run_id, join_flow.draft_list(
        run_id, slug(name), company.root, today=TODAY, **kwargs
    )


def finish_later(company, name, run_id=None):
    """Draft one segment in a later session: the list, the yes, the draft, the approval."""
    run_id, shown = listed(company, name, run_id)
    join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
    join_flow.assemble_step(
        drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY, segment=slug(name)
    )
    return run_id, shown, approve(run_id, company, name)


def record_of(company):
    return segments.load_import(company.base_id)


def a_company(answers=None, build=True):
    return adoption.Company(pages(), answers=dict(ANSWERS, **(answers or {})), build=build)


def set_up_and_close(company, adopt_first=True, draft_one=True):
    """The setup this whole module starts from, up to and including the closing."""
    if adopt_first:
        company.adopt(TAKEN_IN)
    if draft_one:
        approve(company.run, company, DRAFTED)
    return close(company)


class Snapshot(object):
    """The whole sandbox at one moment, kept under a name and put back exactly."""

    PARTS = ("home", "seat", "tmp")

    def __init__(self, sandbox, name):
        self.sandbox = sandbox
        self.kept = os.path.join(sandbox.path, "kept-" + name)
        for part in self.PARTS:
            shutil.copytree(
                os.path.join(sandbox.path, part),
                os.path.join(self.kept, part),
                symlinks=True,
            )

    def restore(self):
        for part in self.PARTS:
            here = os.path.join(self.sandbox.path, part)
            shutil.rmtree(here)
            shutil.copytree(os.path.join(self.kept, part), here, symlinks=True)


class Case(unittest.TestCase):
    def setUp(self):
        self.sandbox = support.Sandbox()
        self.sandbox.__enter__()
        self.addCleanup(self.sandbox.__exit__, None, None, None)


# --- Happy path: kept past the closing, and finished after a fresh yes -----


class TestItSurvivesTheClosing(Case):
    def test_a_segment_left_to_draft_is_kept_and_a_later_session_finishes_it(self):
        company = a_company()
        closed = set_up_and_close(company)
        self.assertTrue(closed.import_unfinished)
        self.assertTrue(closed.drafts_unfinished)
        self.assertFalse(os.path.isdir(os.path.join(join_flow.join_home(), company.run)))

        record = record_of(company)
        self.assertEqual([LATER], [s.name for s in record.drafts_unfinished()])
        self.assertEqual([], record.pages_unfinished())
        payload = json.dumps(record.to_payload())
        # Names and settled answers only: no material, no draft, no yes to read it.
        self.assertNotIn("Firmographics", payload)
        self.assertNotIn(os.path.realpath(company.pages[LATER]), record.consent["paths"])
        self.assertEqual([], record.consent["paths"])

        # The next session is told once, and finishing names the segment.
        run_two, resumed = resume(company)
        self.assertEqual([LATER], [s.name for s in resumed.to_draft])
        self.assertIn(join_flow.RESUME_TO_DRAFT_ONE, resumed.sentences())
        self.assertFalse(resumed.done)

        # Consent is never carried over: nothing is read before a fresh yes.
        run_three, shown = listed(company, LATER)
        self.assertEqual([os.path.realpath(company.pages[LATER])], shown.paths)
        self.assertIn(join_flow.DRAFT_LIST_OFFER % {"name": LATER}, shown.sentences())
        with self.assertRaises(DraftError):
            join_flow.assemble_step(
                drafting.STEP_SEGMENT, run_three, "Acme", EMAIL, today=TODAY,
                segment=slug(LATER),
            )
        with self.assertRaises(ReviewError) as caught:
            approve(run_three, company, LATER)
        self.assertEqual(join_flow.CODE_DRAFT_NOT_AGREED, caught.exception.code)
        self.assertIsNone(company.read(company.destination(LATER)))

        join_flow.draft_freeze(run_three, SESSION_TWO, today=TODAY)
        request = support.read(
            join_flow.assemble_step(
                drafting.STEP_SEGMENT, run_three, "Acme", EMAIL, today=TODAY,
                segment=slug(LATER),
            ).path
        )
        # The page is read inside the data fence, and it is the only file read.
        fence_opens = constants.SOURCE_FENCE_HEADER.split("%")[0]
        self.assertEqual(1, request.count(fence_opens))
        self.assertLess(request.index(fence_opens), request.index("# %s" % LATER))
        self.assertNotIn("# %s" % TAKEN_IN, request)

        result = approve(run_three, company, LATER)
        self.assertEqual(company.destination(LATER), result.path)
        found, bad = recovery.lines_for(company, company.destination(LATER))
        self.assertEqual([], bad)
        self.assertEqual(["drafted"], [line.trigger for line in found])
        self.assertEqual(company.run, found[0].run)
        self.assertEqual("", company.status())

        _run, last = resume(company)
        self.assertTrue(last.done)
        self.assertIn(join_flow.RESUME_ALL_SETTLED, last.sentences())
        self.assertFalse(segments.has_import(company.base_id))

    def test_only_the_document_kept_for_that_segment_is_offered(self):
        company = a_company(answers={DRAFTED: constants.SEGMENT_DRAFT})
        set_up_and_close(company, draft_one=False)
        for name in (LATER, DRAFTED):
            _run, shown = listed(company, name)
            self.assertEqual([os.path.realpath(company.pages[name])], shown.paths, name)

    def test_setup_that_drafts_every_segment_keeps_nothing_past_the_closing(self):
        company = a_company(answers={LATER: constants.SEGMENT_ADOPT})
        company.adopt(TAKEN_IN)
        company.adopt(LATER)
        approve(company.run, company, DRAFTED)
        closed = close(company)
        self.assertFalse(closed.import_unfinished)
        self.assertFalse(closed.drafts_unfinished)
        self.assertFalse(segments.has_import(company.base_id))

    def test_a_company_with_no_finished_page_to_take_in_keeps_its_drafts_too(self):
        company = a_company(answers={TAKEN_IN: constants.SEGMENT_DRAFT})
        closed = set_up_and_close(company, adopt_first=False)
        self.assertTrue(closed.drafts_unfinished)
        self.assertEqual(
            [TAKEN_IN, LATER],
            sorted(s.name for s in record_of(company).drafts_unfinished()),
        )

    def test_the_umbrella_never_says_whether_a_segment_file_exists(self):
        company = a_company()
        before = company.read(UMBRELLA)
        set_up_and_close(company)
        finish_later(company, LATER)
        after = company.read(UMBRELLA)
        self.assertEqual(before, after)


# --- A changed list asks again, and narrowing only takes part of it ---------


class TestAChangedListAsksAgain(Case):
    def setUp(self):
        super(TestAChangedListAsksAgain, self).setUp()
        self.company = a_company()
        set_up_and_close(self.company)
        self.extra = os.path.join(os.environ["HOME"], "more-notes")
        support.write(
            os.path.join(self.extra, "regional-call-notes.md"),
            "# Call notes\n\nRegional banks ask about branch staff first.\n",
        )

    def test_a_list_changed_after_the_yes_needs_a_yes_of_its_own(self):
        company = self.company
        run_id, _shown = listed(company, LATER)
        join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        _run, grown = listed(company, LATER, run_id=run_id, added=[self.extra])
        self.assertEqual(
            [
                os.path.realpath(company.pages[LATER]),
                os.path.realpath(os.path.join(self.extra, "regional-call-notes.md")),
            ],
            grown.paths,
        )
        with self.assertRaises(ConsentError) as caught:
            join_flow.assemble_step(
                drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY,
                segment=slug(LATER),
            )
        self.assertEqual(join_flow.CODE_ASK_AGAIN, caught.exception.code)
        join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        request = support.read(
            join_flow.assemble_step(
                drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY,
                segment=slug(LATER),
            ).path
        )
        self.assertIn("branch staff first", request)

    def test_a_file_that_changes_between_the_showing_and_the_yes_asks_again(self):
        company = self.company
        run_id, _shown = listed(company, LATER, added=[self.extra])
        os.remove(os.path.join(self.extra, "regional-call-notes.md"))
        with self.assertRaises(ConsentError) as caught:
            join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        self.assertEqual(join_flow.CODE_DRAFT_LIST_CHANGED, caught.exception.code)
        self.assertIsNone(join_flow.load_consent(run_id))

    def test_dropping_takes_part_of_the_list_and_never_adds(self):
        company = self.company
        run_id, _shown = listed(company, LATER, added=[self.extra])
        _run, narrower = listed(company, LATER, run_id=run_id, dropped=[2])
        self.assertEqual([os.path.realpath(company.pages[LATER])], narrower.paths)
        with self.assertRaises(ConsentError) as caught:
            listed(company, LATER, run_id=run_id, dropped=[3])
        self.assertEqual(join_flow.CODE_DRAFT_NO_SUCH_NUMBER, caught.exception.code)

    def test_a_folder_to_add_that_is_not_there_adds_nothing(self):
        company = self.company
        run_id, _shown = listed(company, LATER)
        with self.assertRaises(ConsentError) as caught:
            listed(
                company, LATER, run_id=run_id,
                added=[os.path.join(os.environ["HOME"], "nowhere")],
            )
        self.assertEqual(join_flow.CODE_DRAFT_FOLDER_MISSING, caught.exception.code)



class TestOneListPerRun(Case):
    def test_a_run_holding_another_segments_list_is_refused(self):
        company = a_company()
        set_up_and_close(company, draft_one=False)
        run_id, _shown = listed(company, LATER)
        with self.assertRaises(ConsentError) as caught:
            listed(company, DRAFTED, run_id=run_id)
        self.assertEqual(join_flow.CODE_DRAFT_RUN_TAKEN, caught.exception.code)


# --- Missing material is said plainly, with the two choices ---------------------


class TestMissingMaterial(Case):
    def assert_nothing_to_agree_to(self, company, run_id):
        with self.assertRaises(ConsentError) as caught:
            join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        self.assertEqual(join_flow.CODE_NOTHING_ON_THE_LIST, caught.exception.code)
        with self.assertRaises(DraftError):
            join_flow.assemble_step(
                drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY,
                segment=slug(LATER),
            )
        self.assertIsNone(company.read(company.destination(LATER)))

    def test_a_document_that_is_gone_is_said_with_the_two_choices(self):
        company = a_company()
        set_up_and_close(company)
        os.remove(company.pages[LATER])
        run_id, shown = listed(company, LATER)
        self.assertEqual([], shown.paths)
        self.assertTrue(shown.gone)
        said = join_flow.DRAFT_MATERIAL_GONE % {"name": LATER}
        self.assertEqual([said], shown.sentences())
        self.assertIn("leave that segment out", said)
        self.assertIn("Name the folder", said)
        self.assert_nothing_to_agree_to(company, run_id)

    def test_a_document_changed_into_something_unreadable_is_gone_too(self):
        company = a_company()
        set_up_and_close(company)
        os.remove(company.pages[LATER])
        os.symlink(company.pages[TAKEN_IN], company.pages[LATER])
        run_id, shown = listed(company, LATER)
        self.assertEqual([], shown.paths)
        self.assertTrue(shown.gone)
        self.assert_nothing_to_agree_to(company, run_id)

    def test_new_material_named_after_it_went_is_drafted_from(self):
        company = a_company()
        set_up_and_close(company)
        moved = os.path.join(os.environ["HOME"], "moved")
        os.makedirs(moved)
        os.rename(company.pages[LATER], os.path.join(moved, "regional.md"))
        run_id, _shown = listed(company, LATER)
        _run, found = listed(company, LATER, run_id=run_id, added=[moved])
        self.assertEqual([os.path.realpath(os.path.join(moved, "regional.md"))], found.paths)
        self.assertEqual([join_flow.DRAFT_LIST_OFFER % {"name": LATER}], found.sentences())
        join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        join_flow.assemble_step(
            drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY, segment=slug(LATER)
        )
        approve(run_id, company, LATER)
        self.assertIsNotNone(company.read(company.destination(LATER)))

    def test_a_segment_named_with_no_document_has_nothing_on_its_list(self):
        company = a_company(build=False)
        lines = ["draft - Wholesale lenders"]
        for segment in company.inventory.segments:
            lines.append("%s %d %s" % (segment.answer, segment.number, segment.name))
        company.inventory = join_flow.settle_segments(company.run, "\n".join(lines) + "\n")
        company.names.append("Wholesale lenders")
        company.build()
        set_up_and_close(company)
        run_id, shown = listed(company, "Wholesale lenders")
        self.assertEqual([], shown.paths)
        self.assertFalse(shown.gone)
        self.assertEqual(
            [join_flow.DRAFT_NOTHING_ON_THE_LIST % {"name": "Wholesale lenders"}],
            shown.sentences(),
        )


# --- Leaving it out ends it ------------------------------------------------------


class TestLeavingItOutEndsIt(Case):
    def test_left_out_it_is_never_offered_again_and_nothing_is_written(self):
        company = a_company()
        set_up_and_close(company)
        head = company.head()
        said = join_flow.draft_leave_out(slug(LATER), company.root)
        self.assertEqual(join_flow.DRAFT_LEFT_OUT % {"name": LATER}, said)
        self.assertEqual(head, company.head())
        self.assertEqual("", company.status())
        # Nothing else was waiting, so the record is let go.
        self.assertFalse(segments.has_import(company.base_id))
        self.assertNotIn(FINISH, recovery.visible(company))
        with self.assertRaises(ConsentError) as caught:
            listed(company, LATER)
        self.assertEqual(join_flow.CODE_NOT_TO_FINISH, caught.exception.code)

    def test_left_out_is_not_to_finish_while_another_segment_still_is(self):
        company = a_company(answers={DRAFTED: constants.SEGMENT_DRAFT})
        set_up_and_close(company, draft_one=False)
        join_flow.draft_leave_out(slug(LATER), company.root)
        record = record_of(company)
        self.assertEqual(segments.STATE_LEFT_OUT, record.state_of(slug(LATER)))
        self.assertEqual([DRAFTED], [s.name for s in record.drafts_unfinished()])
        _run, resumed = resume(company)
        self.assertEqual([DRAFTED], [s.name for s in resumed.to_draft])

    def test_a_draft_approved_and_not_saved_is_taken_back_when_left_out(self):
        company = a_company()
        set_up_and_close(company)
        run_id, _shown = listed(company, LATER)
        join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        with recovery.StopAfter(review, "_create_new") as stop:
            with self.assertRaises(recovery.Stopped):
                approve(run_id, company, LATER)
        self.assertTrue(stop.fired)
        join_flow.draft_leave_out(slug(LATER), company.root)
        self.assertIsNone(company.read(company.destination(LATER)))
        self.assertEqual("", company.status())
        self.assertFalse(segments.has_import(company.base_id))


# --- The next session is told once ---------------------------------------------


class TestTheNoticeIsOne(Case):
    def blocks(self):
        return session_start.load_blocks(support.PLUGIN_DIR, "finish-import.md")

    def test_pages_and_segments_both_waiting_are_one_notice(self):
        company = a_company()
        approve(company.run, company, DRAFTED)
        close(company)
        record = record_of(company)
        self.assertTrue(record.pages_unfinished())
        self.assertTrue(record.drafts_unfinished())
        said = recovery.visible(company)
        self.assertEqual(1, said.count(FINISH))
        self.assertIn(self.blocks()["visible-segments"].splitlines()[0], said)
        self.assertNotIn(self.blocks()["visible"].splitlines()[0], said)

    def test_segments_alone_are_one_notice(self):
        company = a_company()
        set_up_and_close(company)
        said = recovery.visible(company)
        self.assertEqual(1, said.count(FINISH))
        self.assertIn(self.blocks()["visible-segments"].splitlines()[0], said)

    def test_pages_alone_keep_the_notice_they_had(self):
        company = a_company(answers={LATER: constants.SEGMENT_ADOPT})
        approve(company.run, company, DRAFTED)
        close(company)
        said = recovery.visible(company)
        self.assertEqual(1, said.count(FINISH))
        self.assertIn(self.blocks()["visible"].splitlines()[0], said)

    def test_a_stop_half_way_through_a_save_is_one_notice_beside_the_unsaved_edit(self):
        company = a_company()
        set_up_and_close(company)
        run_id, _shown = listed(company, LATER)
        join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
        with recovery.StopAfter(review, "_create_new") as stop:
            with self.assertRaises(recovery.Stopped):
                approve(run_id, company, LATER)
        self.assertTrue(stop.fired)
        said = recovery.visible(company)
        self.assertIn(session_start.DIRTY_TREE, said)
        self.assertEqual(1, said.count(FINISH))

    def test_nothing_is_said_once_every_segment_is_settled(self):
        company = a_company()
        set_up_and_close(company)
        finish_later(company, LATER)
        self.assertNotIn(FINISH, recovery.visible(company))

    def test_the_notice_meets_the_plain_language_rules(self):
        plain_language.assert_plain(
            self, os.path.join(support.TEMPLATES_DIR, "finish-import.md")
        )


# --- A stop at every step that changes anything resumes cleanly ----------------


def about(name):
    """Whether a call is about one segment's file."""
    wanted = slug(name)

    def when(*args, **kwargs):
        return any(wanted in str(item) for item in list(args) + list(kwargs.values()))

    return when


def marks(name, state):
    def when(base_id, which, written, *rest, **kwargs):
        return which == slug(name) and written == state

    return when


def steps_for(name):
    """Every step a segment's save takes that changes anything, in order."""
    return (
        ("the yes written down", lambda: recovery.StopAfter(
            segments, "mark", marks(name, segments.STATE_APPROVED))),
        ("the bytes put down under a temporary name", lambda: recovery.StopAfter(
            review, "_write_whole")),
        ("the page written", lambda: recovery.StopAfter(review, "_create_new", about(name))),
        ("the page staged", lambda: recovery.StopAfter(review, "_stage_bytes", about(name))),
        ("its line added", lambda: recovery.StopAfter(confirm, "_append_line", about(name))),
        ("its line staged", lambda: recovery.StopGit(recovery.adds_a_line_file)),
        ("the save", lambda: recovery.StopGit(recovery.is_commit)),
        ("the save written down", lambda: recovery.StopAfter(
            segments, "mark", marks(name, segments.STATE_COMMITTED))),
    )


class TestAStopAtEveryStep(Case):
    """A stop after every mutation step, each asserted to fire, and the next
    session ends where an uninterrupted run does: the same files, the same
    staging, the same saved work, nothing unsaved, and nothing kept."""

    def finish_everything(self, company):
        """What a later session does: finish, draft what is left, finish again."""
        for _round in range(3):
            run_id, resumed = resume(company)
            if resumed.done:
                return resumed
            for segment in resumed.to_draft:
                finish_later(company, segment.name)
        self.fail("finishing never came to an end")

    def test_a_stop_in_a_later_sessions_save_is_finished_by_the_session_after(self):
        company = a_company()
        set_up_and_close(company)
        snapshot = Snapshot(self.sandbox, "after-the-closing")
        self.finish_everything(company)
        expected = recovery.state_of(company)
        self.assertIsNone(expected["record"])
        self.assertEqual("", expected["unsaved"])
        for label, make_stop in steps_for(LATER):
            with self.subTest(step=label):
                snapshot.restore()
                run_id, _shown = listed(company, LATER)
                join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
                stop = make_stop()
                with stop:
                    with self.assertRaises(recovery.Stopped):
                        approve(run_id, company, LATER)
                self.assertTrue(stop.fired, label)
                run_two, resumed = resume(company)
                if label == "the yes written down":
                    self.assertEqual([LATER], [s.name for s in resumed.drafted_again])
                    self.assertIn(
                        join_flow.RESUME_DRAFT_AGAIN % {"name": LATER}, resumed.sentences()
                    )
                    self.assertEqual([LATER], [s.name for s in resumed.to_draft])
                elif label == "the save written down":
                    self.assertTrue(resumed.done, label)
                elif label == "the bytes put down under a temporary name":
                    self.assertEqual([LATER], [s.name for s in resumed.to_draft], label)
                else:
                    self.assertEqual([LATER], [s.name for s in resumed.drafts_saved], label)
                self.finish_everything(company)
                self.assertEqual(expected, recovery.state_of(company), label)
                found, bad = recovery.lines_for(company, company.destination(LATER))
                self.assertEqual([], bad)
                self.assertEqual(["drafted"], [line.trigger for line in found], label)

    def test_a_stop_in_setups_own_draft_step_is_finished_by_the_next_session(self):
        company = a_company()
        company.adopt(TAKEN_IN)
        snapshot = Snapshot(self.sandbox, "before-step-6c")
        approve(company.run, company, DRAFTED)
        self.finish_everything(company)
        expected = recovery.state_of(company)
        for label, make_stop in steps_for(DRAFTED):
            with self.subTest(step=label):
                snapshot.restore()
                stop = make_stop()
                with stop:
                    with self.assertRaises(recovery.Stopped):
                        approve(company.run, company, DRAFTED)
                self.assertTrue(stop.fired, label)
                # The window closed: no closing, and the next session finishes.
                self.finish_everything(company)
                self.assertEqual(expected, recovery.state_of(company), label)

    def test_a_stop_while_the_list_is_kept_or_agreed_to_is_harmless(self):
        company = a_company()
        set_up_and_close(company)
        snapshot = Snapshot(self.sandbox, "before-the-list")
        for target, name in ((join_flow, "atomic_write_json"), (segments, "save_candidates"), (segments, "save")):
            with self.subTest(write=name):
                snapshot.restore()
                run_id = join_flow.new_run(TODAY)
                with recovery.StopAfter(target, name) as stop:
                    with self.assertRaises(recovery.Stopped):
                        listed(company, LATER, run_id=run_id)
                self.assertTrue(stop.fired)
                _run, shown = listed(company, LATER, run_id=run_id)
                self.assertEqual([os.path.realpath(company.pages[LATER])], shown.paths)
                join_flow.draft_freeze(run_id, SESSION_TWO, today=TODAY)
                join_flow.assemble_step(
                    drafting.STEP_SEGMENT, run_id, "Acme", EMAIL, today=TODAY,
                    segment=slug(LATER),
                )
                approve(run_id, company, LATER)
                self.assertIsNotNone(company.read(company.destination(LATER)))

    def test_a_stop_after_leaving_it_out_is_harmless(self):
        company = a_company()
        set_up_and_close(company)
        with recovery.StopAfter(segments, "mark", marks(LATER, segments.STATE_LEFT_OUT)) as stop:
            with self.assertRaises(recovery.Stopped):
                join_flow.draft_leave_out(slug(LATER), company.root)
        self.assertTrue(stop.fired)
        _run, resumed = resume(company)
        self.assertTrue(resumed.done)
        self.assertFalse(segments.has_import(company.base_id))


# --- Through the script, as the assistant runs it -------------------------------


class TestTheScript(Case):
    def script(self, company, *argv):
        return adoption.run_script("join", "join.py", list(argv), company.root)

    def test_the_closing_says_segments_are_still_to_come(self):
        company = a_company()
        company.adopt(TAKEN_IN)
        code, printed = self.script(
            company, "close", "--run", company.run, "--base", company.root
        )
        self.assertEqual(0, code, printed)
        self.assertIn(join_flow.CLOSING_DRAFTS_UNFINISHED, printed)
        self.assertNotIn(join_flow.CLOSING_IMPORT_UNFINISHED, printed)

    def test_finishing_names_each_segment_to_draft_and_never_its_file(self):
        company = a_company()
        set_up_and_close(company)
        run_id = join_flow.new_run(TODAY)
        code, printed = self.script(
            company, "resume", "--run", run_id, "--base", company.root,
            "--session", SESSION_TWO,
        )
        self.assertEqual(0, code, printed)
        self.assertIn("to-draft=%s" % slug(LATER), printed)
        self.assertIn(join_flow.RESUME_TO_DRAFT_ONE, printed)
        self.assertNotIn(company.pages[LATER], printed)

    def test_the_list_the_yes_and_leaving_out_through_the_script(self):
        company = a_company()
        set_up_and_close(company)
        run_id = join_flow.new_run(TODAY)
        code, printed = self.script(
            company, "draft-list", "--run", run_id, "--segment", slug(LATER),
            "--base", company.root,
        )
        self.assertEqual(0, code, printed)
        self.assertIn(join_flow.DRAFT_LIST_OFFER % {"name": LATER}, printed)
        self.assertIn("number=1", printed)
        code, printed = self.script(
            company, "draft-freeze", "--run", run_id, "--session", SESSION_TWO
        )
        self.assertEqual(0, code, printed)
        self.assertIn("Nothing leaves this computer", printed)
        code, printed = self.script(
            company, "draft-leave", "--segment", slug(LATER), "--base", company.root
        )
        self.assertEqual(0, code, printed)
        self.assertIn(join_flow.DRAFT_LEFT_OUT % {"name": LATER}, printed)

    def test_missing_material_through_the_script(self):
        company = a_company()
        set_up_and_close(company)
        os.remove(company.pages[LATER])
        run_id = join_flow.new_run(TODAY)
        code, printed = self.script(
            company, "draft-list", "--run", run_id, "--segment", slug(LATER),
            "--base", company.root,
        )
        self.assertEqual(1, code, printed)
        self.assertIn("codes=%s" % join_flow.CODE_MATERIAL_GONE, printed)
        self.assertIn(join_flow.DRAFT_MATERIAL_GONE % {"name": LATER}, printed)
        self.assertNotIn("read=", printed)

    def test_approving_before_the_yes_is_refused_with_a_sentence(self):
        company = a_company()
        set_up_and_close(company)
        run_id = join_flow.new_run(TODAY)
        join_flow.draft_list(run_id, slug(LATER), company.root, today=TODAY)
        draft = write_draft(run_id, LATER)
        code, printed = self.script(
            company, "approve", "--step", "segment", "--segment", slug(LATER),
            "--draft", draft, "--run", run_id, "--base", company.root,
        )
        self.assertEqual(1, code, printed)
        self.assertIn(join_flow.DRAFT_NOT_AGREED, printed)


# --- The words -----------------------------------------------------------------


NEW_SENTENCES = (
    "CLOSING_DRAFTS_UNFINISHED",
    "RESUME_DRAFT_SAVED_ONE",
    "RESUME_DRAFT_SAVED",
    "RESUME_DRAFT_AGAIN",
    "RESUME_TO_DRAFT_ONE",
    "RESUME_TO_DRAFT",
    "RESUME_ALL_SETTLED",
    "DRAFT_LIST_OFFER",
    "DRAFT_MATERIAL_GONE",
    "DRAFT_NOTHING_ON_THE_LIST",
    "DRAFT_NOT_TO_FINISH",
    "DRAFT_RUN_TAKEN",
    "DRAFT_IN_PROGRESS",
    "DRAFT_NO_SUCH_NUMBER",
    "DRAFT_FOLDER_MISSING",
    "DRAFT_LIST_CHANGED",
    "DRAFT_NOT_AGREED",
    "DRAFT_LEFT_OUT",
)


class TestTheWords(unittest.TestCase):
    def test_every_new_sentence_is_registered_and_plain(self):
        registered = set(plain_language.PYTHON_SENTENCES)
        for name in NEW_SENTENCES:
            with self.subTest(name=name):
                self.assertTrue(("join_flow", name) in registered, name)
                text = getattr(join_flow, name)
                self.assertEqual([], plain_language.find_banned(text))
                self.assertEqual([], plain_language.find_dashes(text))
                self.assertEqual([], plain_language.find_banned_person_facing(text))
                self.assertNotIn("/", text)
                self.assertNotIn("decision", text.lower())

    def test_every_refusal_about_the_material_offers_the_two_choices(self):
        for name in ("DRAFT_MATERIAL_GONE", "DRAFT_NOTHING_ON_THE_LIST"):
            text = getattr(join_flow, name)
            self.assertIn("Name the folder", text, name)
            self.assertIn("leave that segment out", text, name)


if __name__ == "__main__":
    unittest.main()
