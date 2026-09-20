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

from gtmbase import machine, moment, paths, report, stale_check, state  # noqa: E402
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
        "--dismiss-ledger-behind",
        action="store_true",
        help="stop mentioning a quiet ledger for a while",
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
        else:
            sys.stdout.write(
                "   [for the assistant] path=%s prepared=%s\n"
                % (item.path, item.entry_id or "-")
            )
    return EXIT_REFUSED if result.stopped else EXIT_DONE


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
    if not resolution.joined or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
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

    seat, _problems = state.load_seat(resolution.base_id)
    try:
        result = stale_check.run(
            resolution.root,
            resolution.base_id,
            session_id=seat.get("session_id"),
            mode=_mode_of(options),
            dismiss_ledger_behind=options.dismiss_ledger_behind,
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
