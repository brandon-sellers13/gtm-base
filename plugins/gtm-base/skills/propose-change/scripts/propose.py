#!/usr/bin/env python3
"""Raise one prepared change for review, and say in one line how it went.

Everything this script does lives in `gtmbase.compose_proposal`; this file
exists only to find the library, read the arguments, and print the answer.
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
    compose_proposal,
    machine,
    moment,
    paths,
    state,
    wordsfile,
)
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is nothing "
    "here to propose a change to."
)


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--staging", help="the staged file to raise for review")
    parser.add_argument(
        "--local-edit",
        action="store_true",
        help="build a proposal from the change you made by hand",
    )
    parser.add_argument("--source", help="where the change came from, in your words")
    parser.add_argument(
        "--source-file",
        help="a file holding where the change came from, in their own words",
    )
    parser.add_argument(
        "--what-changed-file",
        help="a file holding what changed and why, in their own words",
    )
    parser.add_argument(
        "--records-a-change",
        action="store_true",
        help="what they said is about the business and becomes a context change",
    )
    parser.add_argument("--reopen", help="raise a kept proposal again by its id")
    parser.add_argument(
        "--show-document",
        help="print the document a change is about, with the check run first",
    )
    parser.add_argument(
        "--new-words-file",
        help="hand out a file to put somebody's own words in, of one kind",
    )
    return parser


COULD_NOT_READ = (
    "GTM Base could not read the file holding their words, so nothing was "
    "proposed. Write it again and run this with the path to it."
)
NEEDS_THE_WORDS = (
    "A context change needs what they said about what changed. Write it to a "
    "file and run this again with the path to it."
)


def words_from(path, session):
    """What somebody typed, read out of a file this script itself handed out.

    Their words go in a file and the path goes on the command line, because a
    person's own sentence with a dollar sign and a bracket in it is a shell
    instruction the moment it is written into a command. The words are read as
    text and nothing in them is ever run.

    The path has to be one this script handed out. Finding V6 of the
    2026-09-20 verification round: any path at all used to be read this way, so
    a document could have somebody's private notes read into their base and
    written down with nobody asked.
    """
    return wordsfile.read_words(path, session)


def a_session(base_id):
    """Which base a words file belongs to.

    It used to be the session this seat was last in, and finding L3 of the
    third look is what that cost: a second window opening between the file
    being handed out and the file being read moved the session on, and the
    answer somebody had just typed became a file nothing would read. The base
    does not move.
    """
    return base_id


def report(result):
    """One short answer a person can read, and nothing they cannot act on."""
    lines = ["Proposal %s: %s." % (result.staging_id or "", result.status)]
    if result.pr_url:
        lines.append("It is waiting for review at %s" % result.pr_url)
    elif result.pr_number:
        lines.append("It is waiting for review as number %s." % result.pr_number)
    for reason in result.reasons:
        lines.append(reason)
    return "\n".join(lines)


def main(argv=None):
    parser = build_parser()
    options = parser.parse_args(argv)

    if options.show_document:
        here = os.getcwd()
        resolution = paths.resolve_base(here, machine.load_machine_state())
        if not resolution.joined or not resolution.root or not resolution.base_id:
            sys.stderr.write(NOT_JOINED + "\n")
            return EXIT_ERROR
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

    if options.new_words_file:
        here = os.getcwd()
        resolution = paths.resolve_base(here, machine.load_machine_state())
        if not resolution.joined or not resolution.base_id:
            sys.stderr.write(NOT_JOINED + "\n")
            return EXIT_ERROR
        if options.new_words_file not in wordsfile.KINDS:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        session = a_session(resolution.base_id)
        wordsfile.ensure_words_dir(session)
        sys.stdout.write(
            "words=%s\n" % wordsfile.new_words_path(session, options.new_words_file)
        )
        return EXIT_DONE

    chosen = [bool(options.staging), bool(options.local_edit), bool(options.reopen)]
    if sum(1 for value in chosen if value) != 1:
        sys.stderr.write(
            "Say which one you mean: a staged file, a change you made by hand, "
            "or a kept proposal to raise again.\n"
        )
        return EXIT_ERROR

    here = os.getcwd()
    resolution = paths.resolve_base(here, machine.load_machine_state())
    if not resolution.joined or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR

    try:
        if options.local_edit:
            # Before either words file is read, so a refusal leaves both where
            # they are for the next attempt once the document is renamed.
            compose_proposal.refuse_a_name_with_a_space(resolution.root)
            session = a_session(resolution.base_id)
            source = options.source
            if options.source_file:
                source = words_from(options.source_file, session)
                if source is None:
                    sys.stdout.write(wordsfile.NOT_OURS + "\n")
                    return EXIT_REFUSED
            if not source:
                sys.stderr.write(
                    "Say where the change came from, in your own words, so the "
                    "reviewer can see the evidence.\n"
                )
                return EXIT_ERROR
            what_changed = None
            if options.what_changed_file:
                what_changed = words_from(options.what_changed_file, session)
                if what_changed is None:
                    sys.stdout.write(wordsfile.NOT_OURS + "\n")
                    return EXIT_REFUSED
            if options.records_a_change and not what_changed:
                sys.stdout.write(NEEDS_THE_WORDS + "\n")
                return EXIT_REFUSED
            staged = compose_proposal.stage_local_edit(
                resolution.root,
                resolution.base_id,
                source,
                what_changed=what_changed,
                records_a_change=bool(options.records_a_change),
            )
            result = compose_proposal.propose(
                staged, resolution.root, resolution.base_id
            )
        elif options.reopen:
            result = compose_proposal.reopen_from_opened(
                options.reopen, resolution.root, resolution.base_id
            )
        else:
            staged = options.staging
            if not os.path.isabs(staged):
                staged = os.path.join(here, staged)
            result = compose_proposal.propose(
                staged, resolution.root, resolution.base_id
            )
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED

    sys.stdout.write(report(result) + "\n")
    if result.status in (
        compose_proposal.STATUS_OPENED,
        compose_proposal.STATUS_RESUMED,
        # A base with no shared copy has nowhere to send a change, and the
        # prepared change waiting for its owner to approve it here is the
        # ordinary ending on such a base rather than a failure (finding G7).
        compose_proposal.STATUS_APPROVE_HERE,
    ):
        return EXIT_DONE
    return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
