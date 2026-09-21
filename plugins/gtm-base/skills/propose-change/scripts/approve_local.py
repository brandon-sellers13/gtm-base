#!/usr/bin/env python3
"""Show one prepared change to its owner, and apply it when they say yes.

Everything this script does lives in `gtmbase.approve_local`; this file exists
only to find the library, read the arguments, and print the answer. It is two
runs on purpose: one to show the change, and one to apply it, because a person
answers in between.
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
    approve_local,
    compose_proposal,
    machine,
    names,
    paths,
    state,
    wordsfile,
)
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is "
    "nothing here to approve."
)
NEED_THE_HASH = (
    "Say which shown change this yes is about, using the value the showing "
    "printed, so nothing is applied to a change that moved since."
)
NOTHING_WAITING = "No prepared change is waiting for you to approve."
NEEDS_THE_WORDING = (
    "Say where the wording is, with the file this skill handed out for it."
)
NOT_ONE_OF_THE_PARTS = (
    "That is not one of the numbers beside the parts of the document, so "
    "nothing was written. List them again and name one of those."
)


def a_session(base_id):
    """Which session this seat is in, which is what its words files belong to."""
    seat, _problems = state.load_seat(base_id)
    return seat.get("session_id") or base_id


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--staging", help="the prepared change to work on")
    parser.add_argument(
        "--show",
        action="store_true",
        help="read the whole prepared change, and nothing else",
    )
    parser.add_argument(
        "--approve", action="store_true", help="apply the change that was shown"
    )
    parser.add_argument(
        "--not-yet", action="store_true", help="leave the prepared change as it is"
    )
    parser.add_argument(
        "--drop", action="store_true", help="throw the prepared change away"
    )
    parser.add_argument("--shown", help="the value the showing printed")
    parser.add_argument(
        "--list", action="store_true", help="say what is waiting to be approved"
    )
    parser.add_argument(
        "--sections",
        action="store_true",
        help="list the parts of the document this change is about, numbered",
    )
    parser.add_argument(
        "--wording",
        action="store_true",
        help="write the real wording into a first draft",
    )
    parser.add_argument("--words", help="the file holding the real wording")
    parser.add_argument(
        "--section", help="which numbered part of the document the wording is for"
    )
    parser.add_argument(
        "--new-words-file",
        help="hand out a file to put somebody's own words in, of one kind",
    )
    return parser


def report(result):
    """One answer a person can read, and nothing they cannot act on."""
    lines = []
    if result.artifact:
        lines.append(result.artifact.rstrip("\n"))
        lines.append("")
        lines.append("Shown value: %s" % result.shown_hash)
    lines.extend(result.reasons)
    return "\n".join(line for line in lines if line is not None)


def main(argv=None):
    options = build_parser().parse_args(argv)

    here = os.getcwd()
    resolution = paths.resolve_base(here, machine.load_machine_state())
    if not resolution.joined or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR

    if options.new_words_file:
        if options.new_words_file not in wordsfile.KINDS:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        session = a_session(resolution.base_id)
        wordsfile.ensure_words_dir(session)
        sys.stdout.write(
            "words=%s\n" % wordsfile.new_words_path(session, options.new_words_file)
        )
        return EXIT_DONE

    if options.list:
        waiting = approve_local.waiting(resolution.root)
        if not waiting:
            sys.stdout.write(NOTHING_WAITING + "\n")
            return EXIT_DONE
        for staging_id, targets in waiting:
            sys.stdout.write(
                "%s: %s\n"
                % (
                    staging_id,
                    ", ".join(names.document_name(path) for path in targets),
                )
            )
        return EXIT_DONE

    if not options.staging:
        sys.stderr.write("Say which prepared change you mean.\n")
        return EXIT_ERROR
    staged = options.staging
    if not os.path.isabs(staged):
        staged = os.path.join(here, staged)

    if options.sections:
        try:
            staging = compose_proposal.load_staging(staged)
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        for number, (path, heading) in enumerate(
            compose_proposal.parts_of(resolution.root, staging), start=1
        ):
            sys.stdout.write(
                "section=%d document=%s heading=%s\n"
                % (number, names.document_name(path), heading.lstrip("#").strip())
            )
        return EXIT_DONE

    if options.wording:
        if not options.words:
            sys.stderr.write(NEEDS_THE_WORDING + "\n")
            return EXIT_ERROR
        words = wordsfile.read_words(
            options.words, a_session(resolution.base_id)
        )
        if words is None:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        part = None
        if options.section:
            try:
                staging = compose_proposal.load_staging(staged)
                numbered = compose_proposal.parts_of(resolution.root, staging)
                part = numbered[int(options.section) - 1]
                if int(options.section) < 1:
                    raise IndexError
            except (GtmBaseError, ValueError, IndexError):
                sys.stdout.write(NOT_ONE_OF_THE_PARTS + "\n")
                return EXIT_REFUSED
        try:
            compose_proposal.write_the_wording(
                resolution.root, staged, words, part=part
            )
        except GtmBaseError as failure:
            sys.stdout.write(str(failure) + "\n")
            return EXIT_REFUSED
        sys.stdout.write(
            "That wording is in the prepared change, and it is ready to be "
            "read and approved.\n"
        )
        return EXIT_DONE

    try:
        if options.not_yet:
            result = approve_local.keep(staged)
        elif options.drop:
            result = approve_local.drop(
                staged, resolution.root, resolution.base_id
            )
        elif options.approve:
            if not options.shown:
                sys.stderr.write(NEED_THE_HASH + "\n")
                return EXIT_ERROR
            result = approve_local.approve(
                staged, resolution.root, resolution.base_id, options.shown
            )
        else:
            result = approve_local.show(staged, resolution.root, resolution.base_id)
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED

    sys.stdout.write(report(result) + "\n")
    return EXIT_REFUSED if result.refused else EXIT_DONE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
