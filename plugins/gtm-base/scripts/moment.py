#!/usr/bin/env python3
"""Say whether a document about to be used has been overtaken by a change.

The text the session start hands the assistant names this script by its full
path, because the rule it belongs to is followed outside any skill. Everything
it does lives in `gtmbase.moment`; this file exists only to find the library,
work out which base the folder belongs to, and hand the answer back.

It prints nothing at all when nothing has overtaken the document, which is the
usual case, so following the rule costs one quiet line of output.
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

from gtmbase import confirm, machine, moment, paths, state  # noqa: E402
from gtmbase.errors import GtmBaseError, PathError, ValidationError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is "
    "nothing here to check."
)
NEEDS_A_FILE = "Name the file you are about to use, with --file."
NEEDS_A_QUESTION = (
    "Say which question you are answering, with --question, and give the "
    "answer with --answer."
)
NO_SESSION = (
    "GTM Base does not know which session this is, so nothing was recorded. "
    "Start a new session and ask again."
)
NOTHING_FLAGGED_NOW = (
    "Nothing has overtaken that document now, so there was nothing to answer."
)
WENT_WRONG = (
    "GTM Base could not check that document, so it said nothing about it."
)

# What each of the three answers is called on the command line.
ANSWER_AS_IS = "as-is"
ANSWER_FIX = "fix"
ANSWER_REFLECTS = "reflects"
ANSWERS = (ANSWER_AS_IS, ANSWER_FIX, ANSWER_REFLECTS)


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--file", help="the context file you are about to use")
    parser.add_argument(
        "--show",
        action="store_true",
        help="print the document itself as well, held apart as data",
    )
    parser.add_argument(
        "--answer",
        choices=list(ANSWERS),
        help="what the person said: as-is, fix, or reflects",
    )
    parser.add_argument(
        "--question", help="the question id this check gave you for that file"
    )
    return parser


def _base():
    """The base this folder belongs to, or nothing and one sentence."""
    resolution = paths.resolve_base(os.getcwd(), machine.load_machine_state())
    if not resolution.joined or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return None
    return resolution


def _say(found):
    """Print the flag, or print nothing, which is what silence has to mean."""
    if not found.flagged:
        return EXIT_DONE
    sys.stdout.write(found.block() + "\n")
    if found.question_id:
        sys.stdout.write(
            "The question id for this answer: %s\n" % found.question_id
        )
    return EXIT_DONE


def _answer(options, resolution, session):
    """Record one of the three answers to the flag on one document."""
    found = moment.check(
        resolution.root,
        resolution.base_id,
        options.file,
        session_id=session,
    )
    if found.code == moment.CODE_NOT_A_CONTEXT_FILE:
        sys.stderr.write(moment.NOT_A_CONTEXT_FILE + "\n")
        return EXIT_REFUSED
    if found.code == moment.CODE_UNREADABLE:
        sys.stderr.write(moment.COULD_NOT_READ + "\n")
        return EXIT_REFUSED
    if not found.flagged:
        sys.stderr.write(NOTHING_FLAGGED_NOW + "\n")
        return EXIT_REFUSED

    if options.answer == ANSWER_AS_IS:
        result = moment.use_as_is(
            found, base_id=resolution.base_id, question_id=options.question
        )
    elif options.answer == ANSWER_FIX:
        result = moment.fix_it_first(
            resolution.root, resolution.base_id, found
        )
    else:
        if not options.question:
            sys.stderr.write(NEEDS_A_QUESTION + "\n")
            return EXIT_ERROR
        found.question_id = options.question
        recorded = moment.already_reflects(
            resolution.root, resolution.base_id, found, session
        )
        text = "\n".join(recorded.reasons)
        if recorded.status == confirm.STATUS_RECORDED:
            sys.stdout.write(text + "\n")
            return EXIT_DONE
        sys.stderr.write(text + "\n")
        return EXIT_REFUSED

    text = "\n".join(result.reasons)
    if result.refused:
        sys.stderr.write(text + "\n")
        return EXIT_REFUSED
    sys.stdout.write(text + "\n")
    if result.staging_path:
        sys.stdout.write("Prepared file: %s\n" % result.staging_path)
    return EXIT_DONE


def main(argv=None):
    options = build_parser().parse_args(argv)
    if not options.file:
        sys.stderr.write(NEEDS_A_FILE + "\n")
        return EXIT_ERROR

    resolution = _base()
    if resolution is None:
        return EXIT_ERROR

    seat, _problems = state.load_seat(resolution.base_id)
    session = seat.get("session_id")

    if options.answer:
        if not session:
            sys.stderr.write(NO_SESSION + "\n")
            return EXIT_REFUSED
        try:
            return _answer(options, resolution, session)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR

    try:
        if options.show:
            text = moment.for_the_model(
                resolution.root,
                resolution.base_id,
                options.file,
                session_id=session,
            )
            sys.stdout.write(text + "\n")
            return EXIT_DONE
        found = moment.check(
            resolution.root,
            resolution.base_id,
            options.file,
            session_id=session,
        )
    except PathError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except ValidationError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR

    # Silence means one thing only: nothing has overtaken that document. Every
    # other ending says why, on the error stream, and ends with something other
    # than zero, because a rule that reads silence as permission has to be able
    # to trust the silence.
    if found.code == moment.CODE_NOT_A_CONTEXT_FILE:
        sys.stderr.write(moment.NOT_A_CONTEXT_FILE + "\n")
        return EXIT_REFUSED
    if found.code == moment.CODE_UNREADABLE:
        sys.stderr.write(moment.COULD_NOT_READ + "\n")
        return EXIT_REFUSED
    return _say(found)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
