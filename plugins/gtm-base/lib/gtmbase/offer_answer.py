"""Write down what a person answered when GTM Base offered to set a base up.

The offer reaches a person inside the first reply of a session, so their answer
arrives as ordinary words in a chat rather than as anything this plugin can see.
The priming the session start hands the assistant names this script, and the
assistant runs it, which is the only way an answer given in words becomes an
answer this account remembers.

Only "not now" is recorded here. Set up and join are recorded by the step that
actually makes a base or joins one, because an account that answered yes and
then stopped halfway has not set anything up and should be asked again.

Nothing here reads standard input and nothing here prints a path, because what
it prints lands in a reply a person reads.
"""

from __future__ import annotations

import sys
from typing import Sequence

from . import constants, machine

# The one answer this script records.
NOT_NOW = "not-now"

# What it says when it is handed any other answer.
SETUP_RECORDS_ITSELF = (
    "That answer is recorded by the setup itself, so there is nothing to write "
    "down here."
)

# What it says when the answer could not be written down.
COULD_NOT_WRITE = (
    "GTM Base could not remember that answer, so it may ask again next time."
)


def _answer_in(argv: Sequence[str]) -> str:
    """The value the caller gave for --answer, or nothing at all."""
    args = list(argv or [])
    if "--answer" not in args:
        return ""
    position = args.index("--answer")
    if position + 1 >= len(args):
        return ""
    return args[position + 1]


def main(argv: Sequence[str]) -> int:
    """Record the answer and print the one sentence that belongs with it."""
    if _answer_in(argv) != NOT_NOW:
        sys.stdout.write(SETUP_RECORDS_ITSELF + "\n")
        return 1
    try:
        machine.record_offer_answer(NOT_NOW)
    except Exception:
        sys.stdout.write(COULD_NOT_WRITE + "\n")
        return 1
    sys.stdout.write(constants.RESTART_SENTENCE + "\n")
    return 0
