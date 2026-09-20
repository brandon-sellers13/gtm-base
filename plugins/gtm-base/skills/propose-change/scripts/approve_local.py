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

from gtmbase import approve_local, machine, names, paths  # noqa: E402
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
