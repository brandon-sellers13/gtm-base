#!/usr/bin/env python3
"""Record what the owner of one document answered about it.

Everything this script does lives in `gtmbase.confirm`; this file exists only
to find the library, read the arguments, and print the answer in plain
sentences.
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

from gtmbase import confirm, machine, paths, state  # noqa: E402
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is nothing "
    "here to answer."
)
NO_SESSION = (
    "GTM Base does not know which session this is, so nothing was recorded. "
    "Start a new session and the question comes back."
)
NEEDS_A_QUESTION = (
    "Say which question you are answering and what the answer is. Run this with "
    "--pending to see the questions still open."
)
NOTHING_OPEN = "There are no questions waiting for an answer right now."
WENT_WRONG = "GTM Base could not record that answer, so nothing was written."


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--question", help="the question id this session was given")
    parser.add_argument(
        "--answer",
        choices=list(confirm.ANSWERS),
        help="what the person said: yes, no, or not-now",
    )
    parser.add_argument("--reason", help="what the person said, in their own words")
    parser.add_argument(
        "--pending",
        action="store_true",
        help="list the questions still waiting for an answer",
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="send an answer that could not be sent last time",
    )
    return parser


def show_pending(base_id):
    open_ones = confirm.pending_questions(base_id)
    if not open_ones:
        sys.stdout.write(NOTHING_OPEN + "\n")
        return EXIT_DONE
    sys.stdout.write("These questions are still waiting for an answer:\n")
    for item in open_ones:
        sys.stdout.write(
            "- %s is about %s, asked because %s.\n"
            % (item["id"], item["file"], _why(item))
        )
    return EXIT_DONE


def _why(item):
    if item.get("trigger") == "ledger":
        return "a decision the team wrote down has moved past it"
    if item.get("trigger") == "drafted":
        return "it was written while the base was being set up"
    return "nobody has said it is still right for a while"


def report(result):
    return "\n".join(result.reasons) if result.reasons else ""


def main(argv=None):
    options = build_parser().parse_args(argv)

    here = os.getcwd()
    resolution = paths.resolve_base(here, machine.load_machine_state())
    if not resolution.joined or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR

    if options.pending:
        return show_pending(resolution.base_id)

    seat, _problems = state.load_seat(resolution.base_id)

    if options.retry:
        try:
            result = confirm.retry_pending(resolution.base_id, resolution.root)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        if result is None:
            sys.stdout.write(confirm.NOTHING_TO_SEND + "\n")
            return EXIT_DONE
        sys.stdout.write(report(result) + "\n")
        return EXIT_DONE if result.status == confirm.STATUS_RECORDED else EXIT_REFUSED

    if not options.question or not options.answer:
        sys.stderr.write(NEEDS_A_QUESTION + "\n")
        return EXIT_ERROR

    session = seat.get("session_id")
    if not session:
        sys.stderr.write(NO_SESSION + "\n")
        return EXIT_REFUSED

    try:
        result = confirm.answer(
            resolution.root,
            resolution.base_id,
            options.question,
            options.answer,
            session,
            reason=options.reason,
        )
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR

    text = report(result)
    if result.status in (
        confirm.STATUS_RECORDED,
        confirm.STATUS_NOT_NOW,
        confirm.STATUS_PROPOSAL_STAGED,
    ):
        sys.stdout.write(text + "\n")
        if result.staging_path:
            sys.stdout.write("Prepared file: %s\n" % result.staging_path)
        return EXIT_DONE
    sys.stderr.write(text + "\n")
    return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
