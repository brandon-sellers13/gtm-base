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
    machine,
    moment,
    paths,
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
        help="the number the review gave one open question in its document",
    )
    parser.add_argument(
        "--document",
        help="the document that question is in, as the review named it",
    )
    parser.add_argument(
        "--answer-file",
        help="a file holding the owner's answer, handed out by this script",
    )
    parser.add_argument(
        "--new-words-file",
        help="hand out a file to put somebody's own words in, of one kind",
    )
    return parser


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
