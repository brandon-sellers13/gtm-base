"""The check that runs as a file is about to be written, and usually says nothing.

The check on the command tool reads every command before it runs, and for a
long time that was the only way anything reached this computer's disk on the
assistant's say-so. It is not. A file-writing tool writes a file without a
command ever being typed, and both reviewers of the 2026-09-20 release
reproduced the same thing from that: a plain write over one small file in GTM
Base's own records folder turns a refused backup into an allowed one, silences
the flag on a document with no end date, or takes away the rule that a session
which has read somebody's own documents may send nothing at all.

So this is the other half of the same idea. The client asks before it runs a
file-writing tool, and a write aimed at one of three places is refused.

1. Anything at all under the folder GTM Base keeps its own records in. Every
   record a person's answers are held in lives there, and not one of them is a
   file any assistant has a reason to write.
2. A joined base's own repository folder, which is where the safeguard the
   base runs before a send lives.
3. A joined base's assistant folder, because a settings file there could point
   the records folder somewhere else and a file there could run something.

A base's context files are not on that list, and must never be. The person
edits those by hand, the assistant edits them too, and proposing a change from
a hand edit is a path this plugin supports.

Four rules hold on every path through this module, and they are the read
check's four rules.

1. It exits at once, printing nothing, for any path that is not in one of the
   three places. That is almost every write on this computer, and it is the
   only reason a check on every file write is affordable at all.
2. It writes nothing anywhere.
3. It reaches no network, and runs nothing: no git, no subprocess of any kind,
   on any path through it.
4. Anything that goes wrong is nothing at all: no output, exit zero. It fails
   open on its own errors on purpose, because the layer that has to hold when
   a record is forged anyway is the gate, which fails closed by itself.

Claude Code's hook documentation, read on 2026-09-20 at
https://code.claude.com/docs/en/hooks, is what this relies on. What it gives a
hook to say yes or no with, for the tool-use event, is `permissionDecision`,
whose value "deny" blocks the call, with `permissionDecisionReason` carrying
the sentence back. The matcher `Edit|Write` is documented as matching either
tool exactly, so several tools are named on one matcher the same way, and
`Edit.*` is documented as matching both `Edit` and `NotebookEdit`, which is
what says the names here are the names the client uses. The documentation names
`file_path` as the field a file tool carries its path in. It does not document
the field names of the notebook tool, so the names this reads beyond
`file_path` are read defensively rather than on the documentation's word, and
nothing is refused for their absence.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

from . import constants, machine, paths, trust_surface

# The tools this hook is declared for. Anything else is somebody else's.
TOOL_NAMES = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# The event name the answer carries back.
EVENT_NAME = "PreToolUse"

# The one field the documentation names. The rest are read because a tool may
# carry its path under a name of its own, and reading them costs nothing.
DOCUMENTED_PATH_KEY = "file_path"

# The folder inside a base that holds the safeguard the base runs before a
# send, and the folder an assistant reads its own settings from.
REPOSITORY_DIR_NAME = ".git"
ASSISTANT_DIR_NAME = ".claude"

# Codes this run records. They are for the log, not for a person.
CODE_NOT_OUR_TOOL = "not-a-file-writing-tool"
CODE_NO_PATH = "no-file-named"
CODE_SEAT_FOLDER = "in-the-records-folder"
CODE_BASE_REPOSITORY = "in-a-bases-own-repository-folder"
CODE_BASE_ASSISTANT_FOLDER = "in-a-bases-assistant-folder"

# The one sentence a person reads when a write is refused. It is fixed text:
# it never names the file, the folder, or which of the three rules caught it,
# because a refusal that reads back the path is a refusal that can be used to
# find out where things are.
REFUSED = (
    "Some folders are GTM Base's own to keep, and this file is inside one of "
    "them, so nothing was written. Write what you meant somewhere else, or "
    "ask the person to make that change themselves."
)


def _folded(text: str) -> str:
    """One path with its letter case and its Unicode form folded away."""
    return trust_surface.normalize_component(text or "")


def _under(real: str, folder: str) -> bool:
    """Whether one resolved path sits inside one folder, folded on both sides.

    Both sides go through the same folding, so a folder that reads as `.GTM-Base`
    on a Mac, and a name written with its accents taken apart, are compared as
    the one name they open.
    """
    if not folder or not real:
        return False
    prefix = _folded(folder.rstrip(os.sep)) + os.sep
    return _folded(real).startswith(prefix)


def named_files(payload: Dict[str, Any]) -> List[str]:
    """Every file this call would write, as absolute paths on this computer.

    The documented field is read first. Any other field whose name ends in the
    same word is read after it, because a tool may carry its path under a name
    of its own and the documentation names only the one. Nothing that holds
    what would be written is read, so a file whose contents happen to spell a
    path is never mistaken for a write to it.
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    cwd = payload.get("cwd")
    cwd = cwd if isinstance(cwd, str) and os.path.isdir(cwd) else None
    found: List[str] = []
    for key in sorted(tool_input):
        if key != DOCUMENTED_PATH_KEY and key != "path" and not key.endswith("_path"):
            continue
        named = tool_input.get(key)
        if not isinstance(named, str) or not named.strip():
            continue
        named = os.path.expanduser(named.strip())
        if not os.path.isabs(named):
            if cwd is None:
                continue
            named = os.path.join(cwd, named)
        found.append(named)
    return found


def problem_with(real_file: str) -> Optional[str]:
    """Which of the three rules this path falls under, or nothing at all.

    Nothing here touches git and nothing here starts another program. The one
    thing it reads is this account's own short record of the bases it has
    joined, which is the same file the read check reads and for the same
    reason: it is the cheapest way to leave.
    """
    try:
        seat = os.path.realpath(paths.seat_home_path())
    except Exception:
        seat = ""
    if seat and _under(real_file, seat):
        return CODE_SEAT_FOLDER

    raw = machine.load_machine_state_raw()
    for entry in list(getattr(raw, "joined", None) or []):
        if not isinstance(entry, dict):
            continue
        root = entry.get("root")
        if not isinstance(root, str) or not root:
            continue
        for candidate in (root, os.path.realpath(root)):
            if not _under(real_file, candidate):
                continue
            if _under(real_file, os.path.join(candidate, REPOSITORY_DIR_NAME)):
                return CODE_BASE_REPOSITORY
            if _under(real_file, os.path.join(candidate, ASSISTANT_DIR_NAME)):
                return CODE_BASE_ASSISTANT_FOLDER
    return None


def run(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What this hook answers, from the request the client handed it.

    Nothing at all is the usual answer, and it is the answer for every write
    outside the three places. The other answer is a refusal and carries the one
    sentence.
    """
    if not isinstance(payload, dict):
        return None
    tool = payload.get("tool_name")
    if isinstance(tool, str) and tool not in TOOL_NAMES:
        return None
    for named in named_files(payload):
        real_file = os.path.realpath(named)
        if problem_with(real_file) is not None:
            return refusal()
    return None


def refusal() -> Dict[str, Any]:
    """The whole of what this hook prints, and nothing else is ever printed."""
    return {
        "hookSpecificOutput": {
            "hookEventName": EVENT_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": REFUSED[: constants.MAX_INJECTION_CHARS],
        }
    }


def main(argv: Sequence[str]) -> int:
    """Read the request from standard input and print at most one object.

    Every way this can go wrong ends the same way: nothing printed, and zero.
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
