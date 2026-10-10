"""Every approval is put to the person by Claude Code itself (Unit 1.7e).

Every approval in GTM Base is a command the assistant runs, and nothing about
a command proves a person wanted it. The value that binds a yes to what was
shown proves that what is written is what was shown, not that anybody said
yes, because an assistant steered by text hidden in a document could run the
showing and the approval straight after one another (Astra's review of
0.3.3, finding 2). Brandon's call 57 (option D) is that every approval goes
through Claude Code's own permission question, which a plugin's check can
force: the check every command already passes through answers "ask" for an
approval, with one plain sentence saying what it does, and Claude Code puts
the question to the person. The assistant cannot answer it.

Claude Code's hook documentation, read on 2026-10-10 at
https://code.claude.com/docs/en/hooks, is what this rests on. "`"ask"`
prompts the user to confirm." The reason is, "For `"ask"`, shown to the user
in the permission prompt." `updatedInput` "Modifies the tool's input
parameters before execution. Combine with `"allow"` to auto-approve, or
`"ask"` to show the modified input to the user." And "A hook's `"ask"` also
forces a permission prompt in auto mode: the classifier can still deny the
tool call, but it can't approve the call silently." The question was seen on
Claude Code 2.1.276 in its default mode and with edits accepted, on the same
day. The documentation does not say what a hook's "ask" does when Claude Code
is set to run commands without asking at all, so an approval is refused there
(Brandon's call 60).

How the approval knows it was asked. The command the person allows is the
command the assistant wrote with one thing put in front of it: a ticket, a
long random value made at the moment of asking, held in a file in this
person's seat folder under a digest of itself, and handed to the command in
the variable `GTM_BASE_APPROVAL`. The assistant has never seen the value
before the person allows the command, because it exists only in the command
Claude Code runs after the yes. Every library function that writes an
approval calls `require` first, which takes the ticket and throws it away, so
it is used once; one command is one approval, and the process that took the
ticket goes on holding it for the writes that one approval makes. A ticket
the person said no to is taken back by the next command in the same
conversation, since any use of it would have to be a command, and one older
than `KEPT_SECONDS` is never taken. A ticket opens only the library writes
the approval it was made for performs, and runs only on the exact line it was
made for.

Which approvals are put to the person: approving and dropping a prepared
change or a hand edit; yes, no and not now to a question from the review or
the flag; fixing a document first, and saying it already says it, at the
moment of use; approving any setup draft, the first that makes the base
included, and the closing's change; taking a finished page in and leaving
one out; leaving out a segment still to draft; the closing's yes and no about
each document; recording a context change at any time and each answer after
it; the move to the current layout and not now to it; and staying quiet for a
month or until asked. These are the points the first two builds of this unit
settled on.

Which are not, and why. Using a document as it is writes nothing. The yes to
read the files setup lists reads and writes nothing in a base, and is bound
to the exact list shown. Answering an open question prepares a change, which
is approved like any other. Skipping a document writes a file saying it was
skipped, which every later step treats as not finished. Closing, resuming,
giving up a stopped move, putting off the reminder about a long quiet, the
weekly line and speaking again either write nothing into a base or undo
something, never decide anything for the person.

What this proves, and what it does not. An approval is written only by a
command the person allowed through Claude Code's own question, which shows
them the command and says what it does. It cannot stop an assistant with open
command access that sets out to work around it, for example by writing its
own program that imports this library and makes a ticket; the check on
commands refuses one that names the ticket, and no check inside the plugin
refuses them all. Claude Code's own permission settings are the lasting
control. A setting or another plugin that answers Claude Code's questions on
the person's behalf answers this one too.
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import re
import secrets
import shlex
from typing import Dict, List, Optional, Sequence, Tuple

from . import paths
from .errors import ReviewError
from .fsutil import atomic_write_json, ensure_dir, read_json, remove

# The variable the allowed command carries its ticket in.
ENV = "GTM_BASE_APPROVAL"

# The folder in this person's seat folder that holds the tickets waiting.
FOLDER = "approvals"

# How long a ticket waits for the person to answer Claude Code's question.
KEPT_SECONDS = 6 * 60 * 60

# A ticket is this many random bytes, written as hexadecimal.
TICKET_BYTES = 24
_TICKET_RE = re.compile(r"\A[0-9a-f]{%d}\Z" % (TICKET_BYTES * 2))
_REWRITTEN_RE = re.compile(
    r"\Aexport %s=([0-9a-f]{%d}); " % (ENV, TICKET_BYTES * 2)
)

# The permission settings in which Claude Code is documented to run a command
# without putting any question to the person.
NOBODY_ASKED_MODES = ("bypassPermissions", "dontAsk")

# The one client that can put a question to the person.
CLIENT_CLAUDE = "claude"

# --- What the person reads -----------------------------------------------------

# Claude Code's question opens with the line "Hook PreToolUse:Bash requires
# confirmation for this command:", then this, then Yes and No.
ASK_OPENING = (
    "GTM Base asks you here, rather than the assistant, because only you can "
    "approve this."
)
ASK_CLOSING = "Choose Yes only if this is what you agreed to."

SAYS_APPROVE_CHANGE = (
    "Allowing it saves the prepared change you were just shown into your base."
)
SAYS_DROP_CHANGE = "Allowing it throws away the prepared change you were just shown."
SAYS_STILL_RIGHT = (
    "Allowing it records that the document you were just asked about is still "
    "right."
)
SAYS_NO_LONGER_RIGHT = (
    "Allowing it records that the document you were just asked about is no "
    "longer right."
)
SAYS_PUT_OFF = (
    "Allowing it puts off the question you were just asked about that document."
)
SAYS_FIX_FIRST = (
    "Allowing it records that the document you were about to use has to be "
    "fixed first."
)
SAYS_ALREADY_SAYS = (
    "Allowing it records that the document you were just asked about already "
    "says what the change says."
)
SAYS_NOT_CAUGHT_UP = (
    "Allowing it records that the document you were just asked about has not "
    "caught up, and prepares a change to it for you to approve."
)
SAYS_LEFT_FLAGGED = (
    "Allowing it leaves the document you were just asked about flagged."
)
SAYS_SAVE_DRAFT = "Allowing it saves the draft you were just shown into your base."
SAYS_ADOPT_PAGE = (
    "Allowing it takes the finished page you were just shown into your base as "
    "it stands."
)
SAYS_LEAVE_PAGE_OUT = "Allowing it leaves that finished page out of your base."
SAYS_LEAVE_SEGMENT_OUT = (
    "Allowing it leaves that segment out, so it gets no document of its own."
)
SAYS_RECORD_CHANGE = "Allowing it records the context change you were just shown."
SAYS_MOVE = "Allowing it moves your base to the current layout."
SAYS_MOVE_LATER = "Allowing it puts off moving your base to the current layout."
SAYS_QUIET_MONTH = "Allowing it keeps GTM Base quiet for a month."
SAYS_QUIET_UNTIL_ASKED = (
    "Allowing it keeps GTM Base quiet until you ask for a review."
)

# The refusals.
NOT_ASKED = (
    "Nothing was written, because GTM Base could not match this approval to a "
    "yes you gave in Claude Code's own question. That happens when it was run "
    "some other way, or when something else ran while you were being asked. "
    "Ask for it again as the skill writes it, and answer that question "
    "yourself."
)
ONE_LINE = (
    "GTM Base did not run this, because an approval has to be on a line of its "
    "own, so the question you are asked covers everything that runs. Ask for "
    "it again on its own."
)
NOBODY_WOULD_BE_ASKED = (
    "GTM Base did not run this approval, because Claude Code is set to run "
    "commands without asking you, so nobody would be asked. Set Claude Code "
    "to ask before it runs commands, then ask for it again."
)
TWO_THINGS = (
    "GTM Base did not run this, because it asks for more than one thing at "
    "once and you would be asked about only one of them. Ask for each on its "
    "own."
)
UNREADABLE = (
    "GTM Base did not run this approval, because it could not read what the "
    "approval asks for. Run it exactly as the skill writes it, on a line of "
    "its own."
)
CANNOT_ASK = (
    "GTM Base did not run this approval, because this assistant cannot put "
    "the question to you itself. Approve it in Claude Code instead."
)
COULD_NOT_PREPARE = (
    "GTM Base could not get the question about this approval ready, so it did "
    "not run. Ask for it again."
)

# Every sentence above, for the plain-language checks.
SENTENCE_NAMES = (
    "ASK_OPENING",
    "ASK_CLOSING",
    "SAYS_APPROVE_CHANGE",
    "SAYS_DROP_CHANGE",
    "SAYS_STILL_RIGHT",
    "SAYS_NO_LONGER_RIGHT",
    "SAYS_PUT_OFF",
    "SAYS_FIX_FIRST",
    "SAYS_ALREADY_SAYS",
    "SAYS_NOT_CAUGHT_UP",
    "SAYS_LEFT_FLAGGED",
    "SAYS_SAVE_DRAFT",
    "SAYS_ADOPT_PAGE",
    "SAYS_LEAVE_PAGE_OUT",
    "SAYS_LEAVE_SEGMENT_OUT",
    "SAYS_RECORD_CHANGE",
    "SAYS_MOVE",
    "SAYS_MOVE_LATER",
    "SAYS_QUIET_MONTH",
    "SAYS_QUIET_UNTIL_ASKED",
    "NOT_ASKED",
    "ONE_LINE",
    "TWO_THINGS",
    "UNREADABLE",
    "NOBODY_WOULD_BE_ASKED",
    "CANNOT_ASK",
    "COULD_NOT_PREPARE",
)

CODE_NOT_ASKED = "approval-not-asked"


class ApprovalRefused(ReviewError):
    """An approval arrived without the ticket the person's yes hands over."""

    default_code = CODE_NOT_ASKED

    def __init__(self, message=NOT_ASKED, code=CODE_NOT_ASKED):
        super(ApprovalRefused, self).__init__(message, code=code)


# --- Which commands are approvals --------------------------------------------

# Each script that can approve something, where it lives in the plugin.
_PLUGIN_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SCRIPTS = {
    "approve_local.py": ("skills", "propose-change", "scripts", "approve_local.py"),
    "confirm.py": ("skills", "confirm", "scripts", "confirm.py"),
    "moment.py": ("scripts", "moment.py"),
    "join.py": ("skills", "join", "scripts", "join.py"),
    "stale_check.py": ("skills", "stale-check", "scripts", "stale_check.py"),
    "seat.py": ("scripts", "seat.py"),
}

_PYTHON_RE = re.compile(r"\Apython(?:3(?:\.\d+)?)?\Z")
# What reaches into another command, so a line holding one is more than the
# approval it shows.
_SUBSTITUTIONS = ("$(", "`", "<(", ">(")
_FOLDER_WORDS = ("cd", "pushd")


class Unreadable(Exception):
    """An approval script's settings could not be read the way it reads them."""


class TwoThings(Exception):
    """One run of an approval script that asks for more than one thing."""


# The settings of each script that each choose what it does. An approval may
# not share its run with any other, because the script does only one of them
# and the person must be asked about the one it does (the security review of
# 2026-10-10, finding 2).
_ACTIONS = {
    "approve_local.py": (
        "show", "approve", "not_yet", "drop", "list", "sections", "read",
        "wording", "new_words_file",
    ),
    "confirm.py": ("pending", "retry", "show_document", "new_words_file", "answer"),
    "moment.py": ("show", "answer"),
    "join.py": (),
    "stale_check.py": (
        "first_run", "dismiss_quiet_record", "dismiss_ledger_behind",
        "move_changes", "abandon_move", "not_now_move", "check_move", "report",
        "review", "show_document", "answer_question", "new_words_file",
        "record_change",
    ),
    "seat.py": ("weekly_line", "quiet", "speak"),
}


def _answer(options) -> str:
    return str(getattr(options, "answer", None) or "").strip().lower().replace(" ", "-")


def _what(script: str, options) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """What a run does and which library writes it opens, or None.

    None is a run that approves nothing. A run that approves something with
    an answer the script does not know is unreadable, so it is never asked
    with a sentence that guesses (the correctness review of 2026-10-10,
    finding 6).
    """
    get = lambda name: getattr(options, name, None)  # noqa: E731
    found: Optional[Tuple[str, Tuple[str, ...]]] = None
    if script == "approve_local.py":
        if get("approve"):
            found = (SAYS_APPROVE_CHANGE, ("approve_local.approve",))
        elif get("drop"):
            found = (SAYS_DROP_CHANGE, ("approve_local.drop",))
    elif script == "confirm.py":
        if get("answer") is not None:
            says = {
                "yes": SAYS_STILL_RIGHT,
                "no": SAYS_NO_LONGER_RIGHT,
                "not-now": SAYS_PUT_OFF,
            }.get(_answer(options))
            if says is None:
                raise Unreadable()
            found = (says, ("confirm.answer",))
    elif script == "moment.py":
        answer = _answer(options)
        if answer == "fix":
            found = (SAYS_FIX_FIRST, ("moment.fix_it_first",))
        elif answer == "reflects":
            found = (SAYS_ALREADY_SAYS, ("confirm.answer",))
    elif script == "join.py":
        mode = get("mode")
        if mode == "approve":
            found = (SAYS_SAVE_DRAFT, ("join_flow.approve_step",))
        elif mode == "adopt":
            found = (SAYS_ADOPT_PAGE, ("join_flow.adoption_approve",))
        elif mode == "adopt-leave":
            found = (SAYS_LEAVE_PAGE_OUT, ("join_flow.adoption_leave_out",))
        elif mode == "draft-leave":
            found = (SAYS_LEAVE_SEGMENT_OUT, ("join_flow.draft_leave_out",))
        elif mode == "reconcile-answer":
            answer = _answer(options)
            if answer == "yes":
                found = (SAYS_ALREADY_SAYS, ("join_flow.reconcile_yes",))
            elif answer == "no":
                found = (SAYS_NOT_CAUGHT_UP, ("join_flow.reconcile_no",))
            else:
                raise Unreadable()
    elif script == "stale_check.py":
        if get("move_changes") and not get("dry_run"):
            found = (SAYS_MOVE, ("changes.migrate",))
        elif get("not_now_move"):
            found = (SAYS_MOVE_LATER, ("changes.not_now",))
        elif get("record_change") == "record":
            found = (SAYS_RECORD_CHANGE, ("record_change.record",))
        elif get("record_change") == "answer":
            found = {
                "yes": (SAYS_ALREADY_SAYS, ("record_change.answer", "join_flow.reconcile_yes")),
                "no": (SAYS_NOT_CAUGHT_UP, ("record_change.answer", "join_flow.reconcile_no")),
                "not-now": (SAYS_LEFT_FLAGGED, ("record_change.answer",)),
            }.get(_answer(options))
            if found is None:
                raise Unreadable()
    elif script == "seat.py":
        quiet = get("quiet")
        if quiet == "month":
            found = (SAYS_QUIET_MONTH, ("state.go_quiet",))
        elif quiet == "until-asked":
            found = (SAYS_QUIET_UNTIL_ASKED, ("state.go_quiet",))
    if found is not None:
        chosen = [name for name in _ACTIONS[script] if get(name)]
        if len(chosen) > 1:
            raise TwoThings()
    return found


def _parser_for(script: str):
    """The script's own way of reading its settings, so both read them alike."""
    where = os.path.join(_PLUGIN_ROOT, *SCRIPTS[script])
    spec = importlib.util.spec_from_file_location("gtm_base_approval_" + script[:-3], where)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_parser()


def _read_settings(script: str, arguments: Sequence[str]):
    """The script's settings as it would read them, or Unreadable."""
    parser = _parser_for(script)
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(
            io.StringIO()
        ):
            return parser.parse_args(list(arguments))
    except SystemExit:
        raise Unreadable()


def _script_and_arguments(words: List[str]) -> Tuple[Optional[str], List[str]]:
    """The approval script a simple command runs, and what it hands it."""
    if not words:
        return None, []
    first = os.path.basename(words[0])
    if first in SCRIPTS:
        return first, words[1:]
    if not _PYTHON_RE.match(first):
        return None, []
    index = 1
    while index < len(words) and words[index].startswith("-"):
        if words[index].startswith(("-c", "-m")):
            return None, []
        index += 1
    if index >= len(words):
        return None, []
    script = os.path.basename(words[index])
    if script in SCRIPTS:
        return script, words[index + 1 :]
    if index > 1 and any(name in " ".join(words[index:]) for name in SCRIPTS):
        # An option that takes a value, such as -X utf8, put the value where
        # the script goes; the script is further on and cannot be read.
        raise Unreadable()
    return None, []


def mentions_an_approval_script(command: str) -> bool:
    """Whether the line names any script that can approve something."""
    return any(name in str(command or "") for name in SCRIPTS)


class Found(object):
    """What one command line holds, as the hook reads it."""

    __slots__ = (
        "says", "opens", "anything_else", "substituted", "scripts",
        "unreadable", "two_things",
    )

    def __init__(self):
        self.says: List[str] = []
        self.opens: List[Tuple[str, ...]] = []
        self.anything_else = False
        # Whether the line runs another command inside it, and how many times
        # it runs a script that can approve something, whatever it asks of it.
        self.substituted = False
        self.scripts = 0
        self.unreadable = False
        self.two_things = False


def find(command: str) -> Found:
    """Read a command line for approvals, the way the script reads itself.

    This reading decides only what the person is asked. It is not what keeps
    an approval from being written: a spelling it misses runs without a
    ticket, and every library function that writes an approval refuses that.
    """
    from . import gate

    found = Found()
    text = str(command or "")
    if not mentions_an_approval_script(text):
        return found
    if any(mark in text for mark in _SUBSTITUTIONS):
        found.anything_else = True
        found.substituted = True
    for segment in gate.split_segments(text):
        try:
            words = shlex.split(segment)
        except ValueError:
            found.anything_else = True
            continue
        words = gate._strip_redirections(words)
        rest, assignments = gate._strip_prefixes(words)
        if not rest:
            found.anything_else = True
            continue
        if os.path.basename(rest[0]) in _FOLDER_WORDS and len(rest) <= 2 and not assignments:
            continue
        what = None
        try:
            script, arguments = _script_and_arguments(rest)
            if script is not None:
                found.scripts += 1
                what = _what(script, _read_settings(script, arguments))
        except Unreadable:
            found.scripts += 1
            found.unreadable = True
            continue
        except TwoThings:
            found.two_things = True
            continue
        if what is None:
            found.anything_else = True
            continue
        if assignments or len(rest) != len(words):
            # A setting or a word such as env in front of the program can
            # change what runs inside the approving process, so it is more
            # than the approval it shows (the security review, finding 5).
            found.anything_else = True
        found.says.append(what[0])
        found.opens.append(what[1])
    return found


# --- The tickets ------------------------------------------------------------


def folder_path() -> str:
    """Where the tickets wait, whether or not the folder is there yet."""
    return os.path.join(paths.seat_home_path(), FOLDER)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ticket_path(ticket: str) -> str:
    return os.path.join(folder_path(), _digest(ticket) + ".json")


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _age_seconds(kept: dict) -> Optional[float]:
    try:
        made = datetime.datetime.fromisoformat(str(kept.get("made")))
    except (TypeError, ValueError):
        return None
    return (_now() - made).total_seconds()


def _rewritten(ticket: str, command: str) -> str:
    return "export %s=%s; %s" % (ENV, ticket, command)


def _make(session: Optional[str], says: str, opens: Sequence[str], command: str) -> str:
    """Make a ticket, keep it, and hand back its value."""
    ticket = secrets.token_hex(TICKET_BYTES)
    folder = ensure_dir(folder_path())
    if not os.path.isdir(folder) or os.path.islink(folder):
        raise OSError("the folder for approvals is not a folder")
    atomic_write_json(
        _ticket_path(ticket),
        {
            "session": session or "",
            "made": _now().isoformat(),
            "says": says,
            "opens": list(opens),
            # The one line this ticket may run on, so a ticket somebody
            # learned can never carry another command (the security review,
            # finding 3).
            "line": _digest(_rewritten(ticket, command)),
        },
        inside=folder,
    )
    return ticket


def take_back(session: Optional[str], keep: Optional[str] = None) -> None:
    """Take back every ticket this conversation still has, and any too old.

    A ticket waits only for the one command it was made for. Any other
    command in the same conversation means the person answered the question
    some other way, or something else ran while they were being asked, so
    the ticket goes, and a ticket they said no to can never be used.
    Another conversation's tickets are left alone, apart from those too old.
    """
    folder = folder_path()
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if not name.endswith(".json") or name == keep:
            continue
        path = os.path.join(folder, name)
        kept = read_json(path)
        if not isinstance(kept, dict):
            remove(path)
            continue
        age = _age_seconds(kept)
        if age is None or age > KEPT_SECONDS or kept.get("session", "") == (session or ""):
            remove(path)


def rewritten_rest(command: str, session: Optional[str]) -> Optional[str]:
    """The command after the ticket, when this is exactly a line this wrote.

    Only the very line a ticket of this conversation was made for counts.
    Anything else naming the ticket's variable is refused by the check on
    commands, because only this module may set it.
    """
    text = str(command or "")
    match = _REWRITTEN_RE.match(text)
    if not match:
        return None
    path = _ticket_path(match.group(1))
    kept = read_json(path)
    if (
        not isinstance(kept, dict)
        or kept.get("session", "") != (session or "")
        or kept.get("line") != _digest(text)
    ):
        return None
    return text[match.end():]


# --- The check every command passes through ------------------------------------


def _verdict(decision: str, reason: str, updated: Optional[dict] = None) -> dict:
    output = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if updated is not None:
        output["updatedInput"] = updated
    return {"hookSpecificOutput": output}


def decide(payload: dict, client: str = CLIENT_CLAUDE) -> Optional[dict]:
    """Claude Code's answer for one command: nothing, a question, or a refusal."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return None
    session = payload.get("session_id")
    session = session if isinstance(session, str) else None
    if rewritten_rest(command, session) is not None:
        match = _REWRITTEN_RE.match(command)
        take_back(session, keep=_digest(match.group(1)) + ".json")
        return None
    take_back(session)
    found = find(command)
    if not (found.says or found.unreadable or found.two_things):
        # A command run inside the line can hand an approval script words
        # nobody can read beforehand, so such a line is never let through.
        if found.substituted and found.scripts and client == CLIENT_CLAUDE:
            return _verdict("deny", ONE_LINE)
        return None
    if client != CLIENT_CLAUDE:
        return _verdict("deny", CANNOT_ASK)
    if found.substituted:
        return _verdict("deny", ONE_LINE)
    if found.two_things:
        return _verdict("deny", TWO_THINGS)
    if found.unreadable:
        return _verdict("deny", UNREADABLE)
    if payload.get("permission_mode") in NOBODY_ASKED_MODES:
        return _verdict("deny", NOBODY_WOULD_BE_ASKED)
    if len(found.says) != 1 or found.anything_else:
        return _verdict("deny", ONE_LINE)
    says, opens = found.says[0], found.opens[0]
    try:
        ticket = _make(session, says, opens, command)
    except (OSError, ValueError):
        return _verdict("deny", COULD_NOT_PREPARE)
    updated = dict(tool_input)
    updated["command"] = _rewritten(ticket, command)
    return _verdict("ask", " ".join((ASK_OPENING, says, ASK_CLOSING)), updated)


# --- The library's side ------------------------------------------------------

# The library writes the process may make, once it has taken its ticket. One
# command is one approval, so the ticket is taken once and what it opens is
# held for the writes that one approval makes, and no others.
_held: frozenset = frozenset()


def require(write: str) -> None:
    """Refuse an approval that did not come through Claude Code's question.

    Called first by every library function that writes an approval, with its
    own name, before it reads a single argument, so a refusal leaves
    everything as it was. A ticket opens only the writes the person was asked
    about (the security review of 2026-10-10, finding 2).
    """
    global _held
    if write in _held:
        return
    if _held:
        raise ApprovalRefused()
    ticket = os.environ.get(ENV, "")
    if not _TICKET_RE.match(ticket):
        raise ApprovalRefused()
    path = _ticket_path(ticket)
    # Taken by renaming it out of the way first, so two processes handed the
    # same ticket can never both use it, and read only once it is taken.
    taken = "%s.taken-%d" % (path, os.getpid())
    try:
        if os.path.islink(path):
            raise OSError("a link")
        os.rename(path, taken)
    except OSError:
        raise ApprovalRefused()
    kept = read_json(taken)
    remove(taken)
    if not isinstance(kept, dict):
        raise ApprovalRefused()
    age = _age_seconds(kept)
    if age is None or age < 0 or age > KEPT_SECONDS:
        raise ApprovalRefused()
    opens = kept.get("opens")
    if not isinstance(opens, list) or write not in opens:
        raise ApprovalRefused()
    _held = frozenset(str(name) for name in opens)
