#!/usr/bin/env python3
"""Say what in this base is out of date, and prepare the change for each answer.

Everything this script does lives in `gtmbase.stale_check` and
`gtmbase.report`; this file exists only to find the library, read the
arguments, and print the answer in plain sentences.
"""

# --- gtm-base shim (copy from here) ---
import os
import sys


def locate_lib(start):
    """Find the folder holding `gtmbase`: beside the script, then the plugin."""
    here = os.path.dirname(os.path.abspath(start))
    while True:
        candidate = os.path.join(here, "lib")
        if os.path.isfile(os.path.join(candidate, "gtmbase", "__init__.py")):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for folder in (
        os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "lib"),
        os.environ.get("GTM_BASE_LIB", ""),
    ):
        if folder and os.path.isfile(os.path.join(folder, "gtmbase", "__init__.py")):
            return folder
    return None


_lib = locate_lib(__file__)
if _lib is None:
    sys.stderr.write(
        "GTM Base could not find its library; reinstall the plugin with: "
        "claude plugin install gtm-base@gtm-base\n"
    )
    raise SystemExit(3)
if _lib not in sys.path:
    sys.path.insert(0, _lib)
# --- end of shim ---


import argparse  # noqa: E402

from gtmbase import (  # noqa: E402
    alternatives,
    changes,
    inventory,
    machine,
    moment,
    paths,
    record_change,
    report,
    stale_check,
    state,
    update_check,
    wordsfile,
)
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is nothing "
    "here to check."
)
WENT_WRONG = "GTM Base could not finish the check, so nothing was prepared."
NOT_RECORDED = "GTM Base could not finish that step, so nothing was written."


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="say what would be prepared without writing anything",
    )
    parser.add_argument(
        "--first-run",
        action="store_true",
        help="say the one honest thing a first run can say",
    )
    parser.add_argument(
        "--dismiss-quiet-record",
        # The name this had before the rename is still accepted, because a
        # session holding the older instructions will ask for it by that name
        # and being refused would lose the answer the person just gave.
        "--dismiss-ledger-behind",
        dest="dismiss_quiet_record",
        action="store_true",
        help="stop mentioning a quiet record of context changes for a while",
    )
    parser.add_argument(
        "--move-changes",
        action="store_true",
        help="move the base to the current layout, after the owner says yes",
    )
    parser.add_argument(
        "--every-seat-updated",
        action="store_true",
        help="say that everyone who opens this base is on the current version",
    )
    parser.add_argument(
        "--abandon-move",
        action="store_true",
        help="give up on an update that stopped partway and put back what is ours",
    )
    parser.add_argument(
        "--not-now-move",
        action="store_true",
        help="record that the person does not want to be asked about this yet",
    )
    parser.add_argument(
        "--check-move",
        action="store_true",
        help="say what the update would do and whether it would be offered",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="show the four numbers for the last four weeks",
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="say what the base holds and what it is missing, for each business",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="say the installed version and the one step that updates it, and what the base can now take",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="walk what is due and what has been prepared, one line each",
    )
    parser.add_argument(
        "--show-document",
        help="print one context file, with the check run before it is read",
    )
    parser.add_argument(
        "--answer-question",
        help="the open-question value the review printed for one question",
    )
    parser.add_argument(
        "--answer-file",
        help="a file holding the owner's answer, handed out by this script",
    )
    parser.add_argument(
        "--new-words-file",
        help="hand out a file to put somebody's own words in, of one kind",
    )
    parser.add_argument(
        "--record-change",
        choices=RECORD_STEPS,
        help="one step of recording a context change without editing a document",
    )
    parser.add_argument(
        "--long",
        action="store_true",
        help="give the whole explanation, as when somebody asks why",
    )
    parser.add_argument(
        "--what-changed-file", help="a file holding what changed, in their words"
    )
    parser.add_argument(
        "--reason-file", help="a file holding why it changed, in their words"
    )
    parser.add_argument(
        "--source-file", help="a file holding where it came from, in their words"
    )
    parser.add_argument(
        "--documents",
        action="append",
        default=[],
        help="the numbers of the documents it affects, separated by commas",
    )
    parser.add_argument(
        "--happened-on", help="the day it happened, as year-month-day"
    )
    parser.add_argument("--shown", help="the shown value the yes is bound to")
    parser.add_argument(
        "--list", help="the token of the numbered list the numbers come from"
    )
    parser.add_argument("--change", help="the context change an answer is about")
    parser.add_argument(
        "--document",
        help="the document an answer or an open question is about, as named",
    )
    parser.add_argument(
        "--answer", help="yes, no, or not-now, about one document"
    )
    return parser


# The steps of recording a context change without editing a document, in the
# order they happen.
RECORD_STEPS = ("ask", "documents", "show", "record", "leave", "answer")


def print_review(result):
    """The review as the assistant reads it: a line to say, then a line to use.

    Every item is one sentence for the person and one machine line underneath
    it. The machine line carries the path and the question identifier, which
    are the two things the assistant needs to show the document and to record
    an answer, and which are the two things nobody wants read aloud. The skill
    says plainly that the second line is never said out loud.
    """
    said = set()
    for line in result.lines():
        sys.stdout.write(line + "\n")
        item = _item_for(result, line)
        if item is None or id(item) in said:
            continue
        said.add(id(item))
        if item.kind == "document":
            sys.stdout.write(
                "   [for the assistant] path=%s question=%s\n"
                % (item.path, item.question_id or "-")
            )
        elif item.kind == "question":
            # The question came out of the document, so it is shown held
            # apart as data, and read out to the person as a question rather
            # than followed as an instruction.
            sys.stdout.write(
                "   [for the assistant] path=%s open-question=%s prepared=%s\n"
                % (item.path, item.open_question, item.prepared or "-")
            )
            sys.stdout.write(moment.fenced(item.question_text or "") + "\n")
        else:
            sys.stdout.write(
                "   [for the assistant] path=%s prepared=%s\n"
                % (item.path, item.entry_id or "-")
            )
    return EXIT_REFUSED if result.stopped else EXIT_DONE


NEEDS_THE_ANSWER = (
    "Say which question this answers, which document it is in, and where the "
    "answer is, with the file this script handed out for it."
)


def answer_a_question(options, resolution):
    """Prepare the change that settles one open question, and say so.

    The answer is the owner's own words, so it arrives in a file this script
    handed out and never on the command line. Nothing in the document changes
    here; the prepared change waits for the owner's yes.
    """
    if not options.document or not options.answer_file:
        sys.stderr.write(NEEDS_THE_ANSWER + "\n")
        return EXIT_ERROR
    words = wordsfile.read_words(options.answer_file, resolution.base_id)
    if words is None:
        sys.stdout.write(wordsfile.NOT_OURS + "\n")
        return EXIT_REFUSED
    try:
        answered = stale_check.answer_a_question(
            resolution.root,
            resolution.base_id,
            options.document,
            options.answer_question,
            words,
        )
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR
    for code in answered.codes:
        sys.stdout.write("codes=%s\n" % code)
    if answered.staging_path:
        sys.stdout.write("Prepared file: %s\n" % answered.staging_path)
    sys.stdout.write(answered.sentence + "\n")
    return EXIT_DONE if answered.prepared else EXIT_REFUSED


def _claim(path, base_id, claims):
    """Somebody's own words, from a file this script handed out, or nothing.

    The file is held rather than taken away, and taken away only once the
    showing it is for has worked, because a showing can still be refused and
    its sentence asks for it again (the correctness review of 0.3.3). A path
    it did not hand out is refused with the one sentence that says so.
    """
    if not path:
        return ""
    claim = wordsfile.claim_words(path, base_id)
    if claim is None:
        raise record_change.Refused(wordsfile.NOT_OURS, code=wordsfile.CODE_NOT_OURS)
    claims.append(claim)
    return claim.text


def _peek(options, base_id):
    """What changed and why, read without taking the files away.

    The same files are taken by the showing on the next step, so they are
    only looked at here, and a path this script did not hand out is read as
    nothing rather than refused: suggesting documents is never a reason to
    stop (Track 4, Unit T4.1).
    """
    said = []
    for path in (options.what_changed_file, options.reason_file):
        if not path:
            continue
        claim = wordsfile.claim_words(path, base_id)
        if claim is None:
            continue
        said.append(claim.text)
        wordsfile.release_words(claim)
    return " ".join(said)


def record_a_change(options, resolution):
    """One step of recording a context change, from the folder the person is in.

    Every step refuses a base with a shared copy first, so nobody is asked a
    question whose answer could not be written down.
    """
    root, base_id = resolution.root, resolution.base_id
    step = options.record_change
    if step == "show":
        # Before anything else, so a showing refused for any reason, a words
        # file included, never leaves the one before it to be recorded.
        record_change.forget_showing(base_id)
    record_change.refuse_a_shared_copy(root)

    if step == "ask":
        for sentence in record_change.ask(long=options.long):
            sys.stdout.write(sentence + "\n")
        return EXIT_DONE

    if step == "documents":
        token, listed = record_change.show_list(root, base_id)
        if not listed:
            sys.stdout.write(record_change.NO_DOCUMENTS + "\n")
            return EXIT_REFUSED
        sys.stdout.write(record_change.DOCUMENTS_INTRO + "\n")
        # No name here comes from a file name since Unit 1.8, and the list is
        # still held apart as data (Astra's review of 0.3.3, finding 3), so
        # nothing about how it is shown depends on that staying true.
        sys.stdout.write(
            moment.fenced(
                "\n".join("%d. %s" % (number, name) for number, _path, name in listed)
            )
            + "\n"
        )
        # The token the numbers are read against on the next step.
        sys.stdout.write("   [for the assistant] list=%s\n" % token)
        suggested = record_change.suggestions(
            root, listed, _peek(options, base_id)
        )
        if suggested:
            sys.stdout.write(record_change.SUGGESTED_INTRO + "\n")
            sys.stdout.write(
                moment.fenced(
                    "\n".join("%d. %s" % (number, name) for number, _path, name in suggested)
                )
                + "\n"
            )
            sys.stdout.write(
                "   [for the assistant] suggested=%s\n"
                % ",".join(str(number) for number, _path, _name in suggested)
            )
        return EXIT_DONE

    if step == "show":
        claims = []
        try:
            what = _claim(options.what_changed_file, base_id, claims)
            why = _claim(options.reason_file, base_id, claims)
            source = _claim(options.source_file, base_id, claims)
            shown = record_change.preview(
                root,
                base_id,
                what,
                why,
                source,
                options.documents,
                happened_on=options.happened_on,
                list_token=options.list,
            )
        except BaseException:
            for claim in claims:
                wordsfile.release_words(claim)
            raise
        for claim in claims:
            wordsfile.consume_claim(claim)
        sys.stdout.write(shown.showing + "\n\n")
        sys.stdout.write(record_change.PREVIEW_ASK + "\n")
        sys.stdout.write("   [for the assistant] shown=%s\n" % shown.shown)
        return EXIT_DONE

    if step == "leave":
        sys.stdout.write(record_change.leave(base_id) + "\n")
        return EXIT_DONE

    if step == "record":
        done = record_change.record(root, base_id, options.shown or "")
        sys.stdout.write(record_change.RECORDED + "\n")
        asked = []
        for path, question in zip(done.plan.ask_about, done.plan.questions()):
            asked.append(question)
            asked.append(
                "   [for the assistant] path=%s change=%s" % (path, done.entry.id)
            )
        if asked:
            # The lines for the assistant carry the paths, so all of it is
            # held apart as data.
            sys.stdout.write(moment.fenced("\n".join(asked)) + "\n")
        if done.plan.sentence:
            sys.stdout.write(done.plan.sentence + "\n")
        return EXIT_DONE

    # The one answer about one document.
    given = (options.answer or "").strip().lower().replace(" ", "-")
    result = record_change.answer(
        root, base_id, options.change or "", options.document or "", given
    )
    said = [result.sentence]
    if result.staging_path:
        said.append("   [for the assistant] prepared=%s" % result.staging_path)
    # The answer names the document, so it is held apart as data too.
    sys.stdout.write(moment.fenced("\n".join(said)) + "\n")
    if given == record_change.ANSWER_YES and not result.answered_yes:
        return EXIT_REFUSED
    return EXIT_DONE


def print_inventory(resolution):
    """What the base holds against the list of kinds, read only (Plan 1, Unit 2.1).

    The table carries the names the map gives each business, which somebody
    typed, so the whole table is held apart as data. Every sentence around it
    is fixed and filled only with counts.
    """
    try:
        found = inventory.take(resolution.root, resolution.base_id)
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR
    sys.stdout.write(inventory.PURPOSE + "\n")
    sys.stdout.write(moment.fenced(found.table()) + "\n")
    for sentence in found.sentences():
        sys.stdout.write(sentence + "\n")
    # A positioning written before competitors had a document of their own
    # (Track 4, Unit T4.4). Said, never done, and never a second question.
    moved = alternatives.move_offer(resolution.root)
    if moved:
        sys.stdout.write(moved + "\n")
    asked = found.ask()
    if asked:
        sys.stdout.write(asked + "\n")
    return EXIT_DONE


def print_update(resolution):
    """The installed version and the one step, then what the base can take (Unit T4.7).

    Read only, and it runs nothing: the step is said, never run. Outside a
    base only the version is said, because there is no base to bring current.
    """
    found = update_check.check()
    sys.stdout.write(found.sentence + "\n")
    if found.code:
        sys.stdout.write("[for the assistant] code=%s\n" % found.code)
    if resolution.active and resolution.root and resolution.base_id:
        try:
            said = update_check.base_sentence(resolution.root, resolution.base_id)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        sys.stdout.write(said + "\n")
    return EXIT_DONE if not found.code else EXIT_REFUSED


def _item_for(result, sentence):
    """The item one sentence of the review came from, when it came from one."""
    for item in result.review:
        if item.sentence == sentence:
            return item
    return None


def _mode_of(options):
    """Which of the three ways of running this the person asked for."""
    if options.first_run:
        return "first-run"
    if options.review:
        return "review"
    return "normal"


def main(argv=None):
    options = build_parser().parse_args(argv)

    here = os.getcwd()
    resolution = paths.resolve_base(here, machine.load_machine_state())
    if options.update:
        return print_update(resolution)
    # The folder somebody works in is as good as the base's own folder. A
    # folder linked to a base resolves to that base with its folder and its
    # identifier, which is everything below needs, and asking for a base that
    # was joined in this very folder refused the one place people actually
    # work (finding 1 of the release A live check). Every path below is read
    # against the base, never against the folder the command runs in.
    if not resolution.active or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR

    if options.new_words_file:
        if options.new_words_file not in wordsfile.KINDS:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        # A words file belongs to the base, never to a session, so a second
        # window opening in between cannot strand what somebody typed.
        wordsfile.ensure_words_dir(resolution.base_id)
        sys.stdout.write(
            "words=%s\n"
            % wordsfile.new_words_path(resolution.base_id, options.new_words_file)
        )
        return EXIT_DONE

    if options.answer_question:
        return answer_a_question(options, resolution)

    if options.record_change:
        try:
            return record_a_change(options, resolution)
        except record_change.Refused as refusal:
            sys.stdout.write(str(refusal) + "\n")
            return EXIT_REFUSED
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(NOT_RECORDED + "\n")
            return EXIT_ERROR

    if options.show_document:
        seat, _problems = state.load_seat(resolution.base_id)
        try:
            text = moment.for_the_model(
                resolution.root,
                resolution.base_id,
                options.show_document,
                session_id=seat.get("session_id"),
            )
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        sys.stdout.write(text + "\n")
        return EXIT_DONE

    if options.report:
        try:
            summary = report.four_week_summary(resolution.root, resolution.base_id)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        sys.stdout.write(report.render_summary(summary) + "\n")
        return EXIT_DONE

    if options.inventory:
        return print_inventory(resolution)

    if options.check_move:
        # Read only. It opens files and writes none, so it is the one thing
        # somebody can run on a real base before deciding anything.
        try:
            said = changes.what_would_happen(resolution.root, resolution.base_id)
            offer = changes.what_to_offer(resolution.root, resolution.base_id)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        sys.stdout.write(said + "\n")
        # Nothing is said about the offer when it would be made, and the plain
        # reason is said when it would not and the look above has not said it
        # already (the 0.3.1 live check, step 3, finding 1).
        why_not = changes.why_not_offered(resolution.base_id, offer)
        if why_not:
            sys.stdout.write(why_not + "\n")
        return EXIT_DONE

    if options.not_now_move:
        try:
            until = changes.not_now(resolution.base_id)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        sys.stdout.write(changes.PUT_OFF % until.isoformat() + "\n")
        return EXIT_DONE

    if options.abandon_move:
        try:
            given_up = changes.abandon(resolution.root, resolution.base_id)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        sys.stdout.write(given_up.sentence + "\n")
        return EXIT_DONE if given_up.ok else EXIT_REFUSED

    if options.move_changes:
        if options.dry_run:
            # A look only writes nothing at all, which is what the skill says
            # a look only does. It says what would happen and stops.
            try:
                would = changes.what_would_happen(
                    resolution.root, resolution.base_id
                )
            except GtmBaseError as failure:
                sys.stderr.write(str(failure) + "\n")
                return EXIT_REFUSED
            except Exception:
                sys.stderr.write(WENT_WRONG + "\n")
                return EXIT_ERROR
            sys.stdout.write(would + "\n")
            return EXIT_DONE
        try:
            moved = changes.migrate(
                resolution.root,
                resolution.base_id,
                every_seat_updated=options.every_seat_updated,
            )
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        sys.stdout.write(moved.sentence + "\n")
        return EXIT_DONE if moved.ok else EXIT_REFUSED

    seat, _problems = state.load_seat(resolution.base_id)
    try:
        result = stale_check.run(
            resolution.root,
            resolution.base_id,
            session_id=seat.get("session_id"),
            mode=_mode_of(options),
            dismiss_quiet_record=options.dismiss_quiet_record,
            dry_run=options.dry_run,
        )
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR

    if options.review:
        return print_review(result)

    for line in result.lines():
        sys.stdout.write(line + "\n")
    for item in result.staged:
        sys.stdout.write("Prepared file: %s\n" % item.path)
    return EXIT_REFUSED if result.stopped else EXIT_DONE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
