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
CODE_PLUGIN_CODE = "in-the-plugins-own-folder"
CODE_PLUGINS_FOLDER = "in-the-folder-plugins-are-kept-in"

# What the client calls the folder it installed this plugin into.
PLUGIN_ROOT_ENV = "CLAUDE_PLUGIN_ROOT"
CODE_CLIENT_SETTINGS = "in-the-settings-that-load-this-plugin"

# The files the client reads to decide whether this plugin runs at all. They
# are the person's own settings and hold everything else they have set up, so
# a write to one is asked about rather than refused (finding F2 of the third
# look). The two registry files are on the list for the same reason: taking
# this plugin out of either of them stops its checks running (finding M4).
CLIENT_SETTINGS_FILES = (
    "settings.json",
    "settings.local.json",
    os.path.join("plugins", "installed_plugins.json"),
    os.path.join("plugins", "known_marketplaces.json"),
)

# How far up from a file this walks looking for a base. A base sits at the top
# of its own folders, so a file more levels down than this is not in one.
MAX_FOLDERS_WALKED = 40

# The one sentence a person reads when a write is refused. It is fixed text:
# it never names the file, the folder, or which of the three rules caught it,
# because a refusal that reads back the path is a refusal that can be used to
# find out where things are.
# What is said when a write is one to ask about rather than one to refuse.
# The documentation for this hook, read on 2026-09-20 at
# https://code.claude.com/docs/en/hooks, lists the three values it may take:
# `permissionDecision`, "\"allow\", \"deny\", or \"ask\". Overrides the
# permission system's own answer for this tool call", with
# `permissionDecisionReason`, "Text shown to the user when denying or asking".
ASK_ABOUT_SETTINGS = (
    "This file is where your assistant is told which safety checks to run, so "
    "a change here can switch GTM Base's own checks off. Read what it would "
    "write before you say yes."
)

REFUSED = (
    "Some folders are GTM Base's own to keep, and this file is inside one of "
    "them, so nothing was written. Write what you meant somewhere else, or "
    "ask the person to make that change themselves."
)

# The one sentence the wrapper says when this check could not run at all. The
# shell script holds the same words, and a test holds the two to each other.
COULD_NOT_CHECK = (
    "GTM Base could not run its own safety check just now, and this file is "
    "in a folder it keeps for itself, so nothing was written. Installing the "
    "plugin again is what repairs its own files, and it is worth doing if "
    "this keeps happening."
)


def _folded(text: str) -> str:
    """One path with its letter case and its Unicode form folded away."""
    return trust_surface.normalize_component(text or "")


def _at_or_under(path: str, folder: str) -> bool:
    """Whether one path is a folder, or sits inside it, folded on both sides.

    Both sides go through the same folding, so a folder that reads as
    `.GTM-Base` on a Mac, and a name written with its accents taken apart, are
    compared as the one name they open.

    The folder itself counts, which is finding V1 of the 2026-09-20
    verification round. A working folder keeps the version-control entry as a
    file rather than a folder, so a rule that only ever looked inside that name
    left the one entry that matters wide open.
    """
    if not folder or not path:
        return False
    one = _folded(path.rstrip(os.sep))
    other = _folded(folder.rstrip(os.sep))
    return one == other or one.startswith(other + os.sep)


def _reaches(named: str, real: str, folder: str) -> bool:
    """Whether a write aimed at this path would land in this folder.

    Both the name as it was given and the name with every link followed are
    checked, against the folder both as it is written and with its own links
    followed. A link inside a protected folder pointing somewhere else is still
    a write into that folder as far as the name goes, and a link outside one
    pointing in is still a write into it as far as the disk goes, so one of the
    two forms alone lets one of the two through.
    """
    if not folder:
        return False
    try:
        settled = os.path.realpath(folder)
    except Exception:
        settled = folder
    for side in (named, real):
        for place in (folder, settled):
            if _at_or_under(side, place):
                return True
    return False


def _under(real: str, folder: str) -> bool:
    """Kept for callers that only have the resolved form of a path."""
    return _at_or_under(real, folder)


def named_files(payload: Dict[str, Any]) -> List[str]:
    """Every file this call would write, as absolute paths on this computer.

    The documented field is read first. Any other field whose name ends in the
    same word is read after it, because a tool may carry its path under a name
    of its own and the documentation names only the one. Nothing that holds
    what would be written is read, so a file whose contents happen to spell a
    path is never mistaken for a write to it.

    The name is used exactly as it was given. It used to have its spaces taken
    off first, and a link named with a space in front of it then pointed at the
    records folder while the check looked at a name nothing on the disk
    answered to (finding V1).
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
        named = os.path.expanduser(named)
        if not os.path.isabs(named):
            if cwd is None:
                continue
            named = os.path.join(cwd, named)
        found.append(named)
    return found


def plugin_roots() -> List[str]:
    """Every folder this plugin's own code is running from, as best we can tell.

    Two answers, because either one on its own can be wrong. The client says
    where it installed the plugin, and that is the copy whose code the hooks
    really run. This file's own place on the disk says where the code answering
    right now came from, and that is the copy an attacker would have to reach.
    Both are protected, so neither a client that says nothing nor a client that
    says the wrong thing leaves the guard writable.

    Only those two. A second copy of this repository somewhere else on the
    computer is somebody working on the plugin, and their work must go on
    (finding V2).
    """
    found: List[str] = []
    told = os.environ.get(PLUGIN_ROOT_ENV) or ""
    if told:
        found.append(os.path.abspath(os.path.expanduser(told)))
    here = os.path.dirname(os.path.abspath(__file__))
    # <root>/lib/gtmbase/write_hook.py, so the root is two folders up.
    found.append(os.path.dirname(os.path.dirname(here)))
    return [item for item in found if item]


# Where the client keeps every plugin it has, including the copy of the
# marketplace the next update is installed from. Finding N6: a write in there
# is not this plugin's own code, so it is not refused outright, and it is not
# an ordinary file either, so it is not waved through.
CLIENT_PLUGINS_DIR = "plugins"


def client_plugins_dir() -> str:
    """The folder under the person's home folder holding their plugins."""
    return os.path.join(
        os.path.expanduser("~"), ASSISTANT_DIR_NAME, CLIENT_PLUGINS_DIR
    )


def client_settings_files() -> List[str]:
    """The files that say whether this plugin's own checks run at all.

    A write to one of these turns the guard off without touching a line of its
    code, which is the same hole from the other side (finding V2).
    """
    home = os.path.expanduser("~")
    folder = os.path.join(home, ASSISTANT_DIR_NAME)
    return [os.path.join(folder, name) for name in CLIENT_SETTINGS_FILES]


def _names_a_guarded_folder(named: str, real: str) -> bool:
    """Whether either spelling of this path names one of the two folder names.

    This is the cheap way out, and it is the reason a check on every file write
    on this computer is affordable. Almost no write anywhere names either of
    these, and the ones that do are the only ones worth walking a folder tree
    over.
    """
    wanted = (_folded(REPOSITORY_DIR_NAME), _folded(ASSISTANT_DIR_NAME))
    for side in (named, real):
        for part in str(side or "").replace("\\", "/").replace(os.sep, "/").split("/"):
            if _folded(part) in wanted:
                return True
    return False


def _guarded_folders_of(root: str) -> List[str]:
    """The two folders inside one base or one linked folder that are ours."""
    return [
        os.path.join(root, REPOSITORY_DIR_NAME),
        os.path.join(root, ASSISTANT_DIR_NAME),
    ]


def _base_above(named: str) -> Optional[str]:
    """The first folder above this path that is shaped like a base.

    Finding N6. The protection of a base's own folders used to be read off this
    account's list of joined bases, and that list is a file: a write that
    empties it takes the protection with it. So the folder tree is walked
    instead, upwards, with no program started and nothing read but the presence
    of two names. A base holds the map and keeps its own history, and a folder
    holding both is treated as one.
    """
    folder = named if os.path.isdir(named) else os.path.dirname(named)
    for _step in range(MAX_FOLDERS_WALKED):
        if not folder:
            return None
        try:
            looks_right = os.path.isfile(
                os.path.join(folder, constants.MAP_PATH)
            ) and os.path.lexists(os.path.join(folder, REPOSITORY_DIR_NAME))
        except Exception:
            return None
        if looks_right:
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent
    return None


def problem_with(named: str, real_file: str) -> Optional[str]:
    """Which rule this path falls under, or nothing at all.

    Nothing here touches git and nothing here starts another program. The
    reading it does of the disk is the presence of two names on the way up from
    the file, and this account's own short record of the bases it has joined,
    which is the same file the read check reads and for the same reason: it is
    the cheapest way to leave.
    """
    try:
        seat = paths.seat_home_path()
    except Exception:
        seat = ""
    if seat and _reaches(named, real_file, seat):
        return CODE_SEAT_FOLDER

    for root in plugin_roots():
        if _reaches(named, real_file, root):
            return CODE_PLUGIN_CODE
    # A question is remembered rather than answered with, because one path can
    # be both: a link under the folder the client keeps its plugins in,
    # pointing into a base's own history folder, is a refusal wearing a
    # question's hat. Finding P2 of the confirmation round.
    asking = None
    for settings in client_settings_files():
        if _reaches(named, real_file, settings):
            asking = CODE_CLIENT_SETTINGS
    if asking is None and _reaches(named, real_file, client_plugins_dir()):
        asking = CODE_CLIENT_SETTINGS

    if not _names_a_guarded_folder(named, real_file):
        return asking

    inside = _base_above(named)
    if inside is None and real_file != named:
        inside = _base_above(real_file)
    if inside is not None:
        for folder in _guarded_folders_of(inside):
            if _reaches(named, real_file, folder):
                return CODE_BASE_REPOSITORY
    raw = machine.load_machine_state_raw()
    for entry in list(getattr(raw, "joined", None) or []):
        if not isinstance(entry, dict):
            continue
        for key in ("root", "content_root"):
            root = entry.get(key)
            if not isinstance(root, str) or not root:
                continue
            for folder in _guarded_folders_of(root):
                if _reaches(named, real_file, folder):
                    return (
                        CODE_BASE_REPOSITORY
                        if folder.endswith(REPOSITORY_DIR_NAME)
                        else CODE_BASE_ASSISTANT_FOLDER
                    )
    return asking


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
    asking = False
    for named in named_files(payload):
        try:
            real_file = os.path.realpath(named)
        except Exception:
            real_file = named
        found = problem_with(named, real_file)
        if found == CODE_CLIENT_SETTINGS:
            asking = True
            continue
        if found is not None:
            return refusal()
    return question() if asking else None


def refusal() -> Dict[str, Any]:
    """The whole of what this hook prints when a write is one to refuse."""
    return _answer("deny", REFUSED)


def question() -> Dict[str, Any]:
    """The whole of what it prints when a write is one to ask about."""
    return _answer("ask", ASK_ABOUT_SETTINGS)


def _answer(say: str, sentence: str) -> Dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": EVENT_NAME,
            "permissionDecision": say,
            "permissionDecisionReason": sentence[: constants.MAX_INJECTION_CHARS],
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
