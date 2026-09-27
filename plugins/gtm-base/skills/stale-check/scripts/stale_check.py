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
    changes,
    join_flow,
    machine,
    moment,
    paths,
    record_change,
    report,
    stale_check,
    state,
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
        help="store the context changes the new way, after the owner says yes",
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
        "--review",
        action="store_true",
        help="walk what is due and what has been prepared, one line each",
    )
    parser.add_argument(
        "--show-document",
        help="print one context file, with the check run before it is read",
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
    parser.add_argument("--change", help="the context change an answer is about")
    parser.add_argument("--document", help="the document an answer is about")
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
        else:
            sys.stdout.write(
                "   [for the assistant] path=%s prepared=%s\n"
                % (item.path, item.entry_id or "-")
            )
    return EXIT_REFUSED if result.stopped else EXIT_DONE


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


def record_a_change(options, resolution):
    """One step of recording a context change, from the folder the person is in.

    Every step refuses a base with a shared copy first, so nobody is asked a
    question whose answer could not be written down.
    """
    root, base_id = resolution.root, resolution.base_id
    step = options.record_change
    record_change.refuse_a_shared_copy(root)

    if step == "ask":
        for sentence in record_change.ask(long=options.long):
            sys.stdout.write(sentence + "\n")
        return EXIT_DONE

    if step == "documents":
        listed = record_change.documents(root)
        if not listed:
            sys.stdout.write(record_change.NO_DOCUMENTS + "\n")
            return EXIT_REFUSED
        sys.stdout.write(record_change.DOCUMENTS_INTRO + "\n")
        for number, _path, name in listed:
            sys.stdout.write("%d. %s\n" % (number, name))
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
            )
        except BaseException:
            for claim in claims:
                wordsfile.release_words(claim)
            raise
        for claim in claims:
            wordsfile.consume_claim(claim)
        sys.stdout.write(shown.proposed.summary + "\n\n")
        sys.stdout.write(join_flow.NOTED_BY_IS_THE_BASES_RECORD + "\n")
        sys.stdout.write("\n" + shown.proposed.artifact + "\n")
        sys.stdout.write(record_change.PREVIEW_ASK + "\n")
        sys.stdout.write("   [for the assistant] shown=%s\n" % shown.shown)
        return EXIT_DONE

    if step == "leave":
        sys.stdout.write(record_change.leave(base_id) + "\n")
        return EXIT_DONE

    if step == "record":
        done = record_change.record(root, base_id, options.shown or "")
        sys.stdout.write(record_change.RECORDED + "\n")
        for path, question in zip(done.plan.ask_about, done.plan.questions()):
            sys.stdout.write(question + "\n")
            sys.stdout.write(
                "   [for the assistant] path=%s change=%s\n" % (path, done.entry.id)
            )
        if done.plan.sentence:
            sys.stdout.write(done.plan.sentence + "\n")
        return EXIT_DONE

    # The one answer about one document.
    given = (options.answer or "").strip().lower().replace(" ", "-")
    result = record_change.answer(
        root, base_id, options.change or "", options.document or "", given
    )
    sys.stdout.write(result.sentence + "\n")
    if result.staging_path:
        sys.stdout.write("   [for the assistant] prepared=%s\n" % result.staging_path)
    if given == record_change.ANSWER_YES and not result.answered_yes:
        return EXIT_REFUSED
    return EXIT_DONE


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
        wordsfile.ensure_words_dir(resolution.base_id)
        sys.stdout.write(
            "words=%s\n"
            % wordsfile.new_words_path(resolution.base_id, options.new_words_file)
        )
        return EXIT_DONE

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
        sys.stdout.write(changes.offer_state_sentence(offer) + "\n")
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
