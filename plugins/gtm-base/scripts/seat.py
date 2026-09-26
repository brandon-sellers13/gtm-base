#!/usr/bin/env python3
"""Change what this base does on your own computer, and nothing about the base.

Three things live here, and all three are settings for this seat rather than
anything the rest of the team ever sees: whether the one line a week is said,
whether GTM Base has been asked to stay quiet, and letting it speak again.
Everything it does lives in `gtmbase.state`; this file exists only to find the
library and hand the arguments over.
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
import datetime  # noqa: E402

from gtmbase import machine, paths, state  # noqa: E402
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is "
    "nothing here to change."
)
NOTHING_ASKED = (
    "Say what to change: --weekly-line on or off, --quiet month or "
    "until-asked, or --speak."
)
WEEKLY_LINE_ON = (
    "GTM Base will say one line a week about what is due a look. Turn it off "
    "again whenever you want."
)
WEEKLY_LINE_OFF = "GTM Base will not say the weekly line again."
QUIET_FOR_A_MONTH = (
    "GTM Base will stay quiet until %s. It will still go through what is due "
    "whenever you ask for a review."
)
QUIET_UNTIL_ASKED = (
    "GTM Base will stay quiet until you ask for a review. Asking for one is "
    "what brings it back."
)
SPEAKING_AGAIN = (
    "GTM Base will speak up again when a document you are about to use has "
    "been overtaken by a context change."
)
WENT_WRONG = "GTM Base could not change that setting, so nothing was changed."


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--weekly-line",
        choices=("on", "off"),
        help="whether to say one line a week about what is due a look",
    )
    parser.add_argument(
        "--quiet",
        choices=("month", "until-asked"),
        help="keep GTM Base quiet for a month, or until you ask for a review",
    )
    parser.add_argument(
        "--speak",
        action="store_true",
        help="let GTM Base speak up again from now on",
    )
    return parser


def main(argv=None):
    options = build_parser().parse_args(argv)
    if not options.weekly_line and not options.quiet and not options.speak:
        sys.stderr.write(NOTHING_ASKED + "\n")
        return EXIT_ERROR

    resolution = paths.resolve_base(os.getcwd(), machine.load_machine_state())
    # These are settings for this seat and this base, so a folder linked to
    # the base changes them as well as the base's own folder does (finding 1
    # of the release A live check).
    if not resolution.active or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR

    said = []
    try:
        if options.weekly_line:
            on = options.weekly_line == "on"
            state.set_weekly_line(resolution.base_id, on)
            said.append(WEEKLY_LINE_ON if on else WEEKLY_LINE_OFF)
        if options.quiet == "month":
            until = state.today() + datetime.timedelta(days=state.SILENCE_DAYS)
            state.set_silent_until(resolution.base_id, until)
            said.append(QUIET_FOR_A_MONTH % until.isoformat())
        elif options.quiet == "until-asked":
            state.set_silent_until(resolution.base_id, state.SILENT_UNTIL_ASKED)
            said.append(QUIET_UNTIL_ASKED)
        if options.speak:
            state.set_silent_until(resolution.base_id, None)
            said.append(SPEAKING_AGAIN)
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR

    sys.stdout.write("\n".join(said) + "\n")
    return EXIT_DONE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
