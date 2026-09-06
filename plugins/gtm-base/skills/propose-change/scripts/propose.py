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

from gtmbase import compose_proposal, machine, paths  # noqa: E402
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
    parser.add_argument("--reopen", help="raise a kept proposal again by its id")
    return parser


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
            if not options.source:
                sys.stderr.write(
                    "Say where the change came from, in your own words, so the "
                    "reviewer can see the evidence.\n"
                )
                return EXIT_ERROR
            staged = compose_proposal.stage_local_edit(
                resolution.root, resolution.base_id, options.source
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
    if result.status in (compose_proposal.STATUS_OPENED, compose_proposal.STATUS_RESUMED):
        return EXIT_DONE
    return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
