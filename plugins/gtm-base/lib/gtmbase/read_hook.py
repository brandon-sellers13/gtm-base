"""The backstop: a check that runs as a context file is about to be read.

The rule the session carries tells the assistant to run the moment-of-use check
before it uses a context file. An instruction is a real mechanism with a real
failure rate, so this is the deterministic half of the same thing: the client
asks before it runs its file-reading tool, and a file under a joined base's
`context` folder that a context change has overtaken comes back with the flag
attached to the read itself.

Claude Code's hook documentation, read on 2026-09-20 at
https://code.claude.com/docs/en/hooks, is what makes this possible. Its
decision-control table for the tool-use event lists `additionalContext` as
"Text added to Claude's context before the tool call runs, shown in the
transcript", beside `permissionDecision` and `permissionDecisionReason`. So the
flag can be delivered without touching the permission decision at all, which is
exactly what this does: it never denies, never asks, and never defers. The read
goes ahead every time.

Four rules hold on every path through this module.

1. It exits at once, printing nothing, for any path that is not a file under
   the `context` folder of a base this account has joined. That is almost every
   read on this computer, and it is the only reason a hook on every file read
   is affordable at all. The check that reads every command already works this
   way.
2. It never writes anywhere but this seat's own folder, and what it writes
   there is one line saying this session has already been told about this
   document, so one session is never told twice.
3. It reaches no network and makes no call that could reach a remote.
4. Anything that goes wrong is nothing at all: no output, exit zero, and a code
   recorded for somebody reading the log later. A file read must never fail
   because of anything here.

It issues no question identifier of its own. The identifier belongs to whoever
actually asks, which is the script the rule names, and that script hands back
one already open for the same document rather than issuing a second.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any, Dict, Optional, Sequence

from . import constants, gitcmd, machine, moment, paths, state, trust_surface
from .errors import GtmBaseError
from .gitcmd import GitRunner

def _folded_prefix(real_file: str, prefix: str) -> bool:
    """The same first pass, with letter case and Unicode form folded away."""
    folded = trust_surface.normalize_component(prefix)
    return trust_surface.normalize_component(real_file).startswith(folded)


# The tool this hook is declared for. Anything else is somebody else's.
TOOL_NAME = "Read"

# The event name the answer carries back.
EVENT_NAME = "PreToolUse"

# How much of its time the whole check may spend on git between everything it
# does. The session-start hook works to the same kind of budget and for the
# same reason: a run that has already waited too long stops waiting.
GIT_BUDGET_SECONDS = 4

# Codes this run records. They are for the log, not for a person.
CODE_NOT_OUR_TOOL = "not-the-file-reading-tool"
CODE_NO_PATH = "no-file-named"
CODE_OUTSIDE_A_BASE = "not-in-a-joined-base"
CODE_NOT_A_CONTEXT_FILE = moment.CODE_NOT_A_CONTEXT_FILE
CODE_ALREADY_SAID = "already-said-this-session"
CODE_WENT_WRONG = "the-check-could-not-finish"


def _named_file(payload: Dict[str, Any]) -> Optional[str]:
    """The file this read is about, as an absolute path on this computer.

    The documentation says the path comes through as an absolute one, and this
    does not rely on that: a path that arrives relative is read against the
    folder the session is in, which is the only thing it could mean.
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    named = tool_input.get("file_path")
    if not isinstance(named, str) or not named.strip():
        return None
    named = named.strip()
    if not os.path.isabs(named):
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not os.path.isdir(cwd):
            return None
        named = os.path.join(cwd, named)
    return named


def _under(real_file: str, folder: str) -> bool:
    """A cheap first pass: does this path even look like it sits in there?

    It is compared as text, which can be wrong in one direction only: a name
    spelled in other letters, or in the other Unicode form, opens the same file
    and reads as different text. Everything that gets past this is checked
    properly afterwards by `moment.context_path_of`, which asks the file system
    rather than the spelling. What this is for is leaving at once, and text is
    the cheapest way to leave.
    """
    if not folder:
        return False
    prefix = folder.rstrip(os.sep) + os.sep
    return real_file.startswith(prefix) or _folded_prefix(real_file, prefix)


def _base_for(real_file: str, payload: Dict[str, Any], git: GitRunner):
    """The joined base this file belongs to, or nothing at all.

    A base is asked about the same way everything else here asks, through the
    one resolver, so a folder that only looks like a base, or one whose record
    and whose written identifier disagree, is no more a base to this hook than
    it is to anything else. What this adds is the step from a file to the base
    it is inside, because the resolver answers about a folder and a context
    file sits some way down inside one.

    The account's own record of the bases it has joined is what is walked, so a
    file in a folder nobody joined is answered with nothing after one pass over
    a short list. The folder the session was opened in is tried after that,
    which is what covers a session opened in the folder somebody keeps their
    material in rather than in the base itself.
    """
    del payload
    raw = machine.load_machine_state_raw()
    for entry in list(getattr(raw, "joined", None) or []):
        if not isinstance(entry, dict):
            continue
        root = entry.get("root")
        if not isinstance(root, str) or not root:
            continue
        # Nothing has touched the disk yet. A folder that is not there, and a
        # folder on a drive that has gone away, both cost a stopped hook when
        # they are asked about, so the one entry whose path this file could sit
        # under is found by looking at the text first.
        if not _under(real_file, root) and not _under(
            real_file, os.path.realpath(root)
        ):
            continue
        account = machine.load_machine_state(git)
        resolution = _resolved(root, account, git)
        if resolution is not None:
            return resolution
    return None


def _resolved(where: str, account, git: GitRunner):
    """One folder put through the resolver, when it answers with a joined base."""
    try:
        resolution = paths.resolve_base(where, account, runner=git)
    except GtmBaseError:
        return None
    if resolution.active and resolution.root and resolution.base_id:
        return resolution
    return None


def run(
    payload: Dict[str, Any],
    now: Optional[datetime.date] = None,
    runner: Optional[GitRunner] = None,
) -> Optional[Dict[str, Any]]:
    """What this hook answers, from the request the client handed it.

    Nothing at all is the usual answer, and it is the answer for every read
    outside a joined base's context folder. The other answer carries the flag
    and never carries a permission decision of any kind.
    """
    if not isinstance(payload, dict):
        return None
    tool = payload.get("tool_name")
    if isinstance(tool, str) and tool != TOOL_NAME:
        return None

    named = _named_file(payload)
    if not named:
        return None
    real_file = os.path.realpath(named)
    if not os.path.isfile(real_file):
        return None

    git = gitcmd.with_deadline(runner, GIT_BUDGET_SECONDS)
    resolution = _base_for(real_file, payload, git)
    if resolution is None:
        return None
    relative = moment.context_path_of(resolution.root, real_file)
    if not relative:
        return None

    session_id = payload.get("session_id")
    session_id = session_id if isinstance(session_id, str) else ""

    found = moment.check(
        resolution.root,
        resolution.base_id,
        relative,
        session_id=None,
        runner=git,
        now=now,
    )
    if not found.flagged:
        # A check that could not read the records says nothing, and says
        # nothing for that reason rather than because the document is fine.
        # Saying anything else here would be guessing.
        return None

    # Told once per session, per document, and per change, so a change written
    # down in the middle of a session is still raised on the next read.
    if session_id and state.notice_was_said(
        resolution.base_id, session_id, relative, found.entry_id
    ):
        return None
    if session_id:
        try:
            state.record_notice(
                resolution.base_id, session_id, relative, found.entry_id
            )
        except Exception:
            pass
    return answer_for(found)


def answer_for(found: "moment.Moment") -> Dict[str, Any]:
    """The whole of what this hook prints, and nothing else is ever printed.

    There is no permission decision in it. The read goes ahead, and what the
    assistant gets is the flag, so it can stop and ask before it uses what it
    just read rather than being stopped from reading it.
    """
    text = "\n".join([moment.PAUSE_BEFORE_USING, "", found.block()])
    return {
        "hookSpecificOutput": {
            "hookEventName": EVENT_NAME,
            "additionalContext": text[: constants.MAX_INJECTION_CHARS],
        }
    }


def main(argv: Sequence[str]) -> int:
    """Read the request from standard input and print at most one object.

    Every way this can go wrong ends the same way: nothing printed, and zero.
    A file read must never fail because of anything here.
    """
    del argv
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        return 0
    try:
        answer = run(payload)
    except Exception:
        return 0
    if answer:
        try:
            sys.stdout.write(json.dumps(answer, ensure_ascii=False) + "\n")
        except Exception:
            return 0
    return 0
