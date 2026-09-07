"""The check that runs before anything leaves this computer.

It runs in two places. Inside the AI client it is a hook on the command tool:
every command holding `git` or `gh` is read, the ones that send something are
worked out, and what they would send is read before the command is allowed to
run. Inside the base it is the safeguard git itself runs before a send.

Both layers fail closed. A command that cannot be read, a change larger than
the cap, a missing interpreter, a settings override that would turn the
safeguard off: all of them refuse. A refusal names the file and what kind of
thing was found, and never the thing itself.

The check only reads a command that names git or GitHub. A command that names
neither is outside it, so a script of its own that runs git from inside itself
is a known gap: `python3 tool.py` is allowed and whatever `tool.py` does with
the shared copy is not read here. The safeguard git itself runs is the layer
that covers that gap.

Once a command does name git or GitHub, every part of it has to be accounted
for. A part whose first word is not git, not GitHub, and not one of the small
set of harmless words listed below is refused rather than assumed to be
harmless, because a word this check does not know can carry a send inside it.

What the gate reads, and where
------------------------------

The thing this check is here to stop is a company's own writing leaving a
base, so what a send would carry is only read when the send comes from a base
this account has joined, from a folder inside one, or from a working folder
this seat made under its own folder. That is the whole of what
`folder_is_in_scope` answers, and it is decided once for each command.

Everywhere else on the machine, which is every other repository the person
works in, the send is not read at all: not the change, not the notes saved
with it, not the file a GitHub command would send, not the command line
itself, and not the folders that belong to one seat alone. A push from a
repository that is not a base is left alone by decision (Brandon, 2026-09-06),
because reading every repository on a consultant's machine refused ordinary
work, and a check people turn off protects nothing.

The refusals that need nothing read stay everywhere: the GitHub commands no
skill uses, skipping the safeguard, forcing over the branch the team shares,
pointing git at other safeguards, handing git another program to run, naming
the seat's own folder, a command that cannot be read at all, and the rule that
nothing may leave a session that has read the person's own documents.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import List, Optional, Sequence, Tuple

from . import constants, machine, marker, paths, scan, state
from .gitcmd import GitRunner, runner_or_default

# --- What the gate can decide ------------------------------------------------

CLIENT_CLAUDE = "claude"
CLIENT_CODEX = "codex"
CLIENT_GIT = "git"

MODE_HOOK = "hook"
MODE_GIT_HOOK = "git-hook"

# The reasons a refusal can carry. The gate never invents free text.
REASON_UNTOKENIZABLE = "untokenizable"
REASON_UNREADABLE = "unreadable-range"
REASON_DENIED_COMMAND = "denied-command"
REASON_NO_VERIFY = "no-verify"
REASON_FORCE_DEFAULT = "force-to-default-branch"
REASON_HOOKS_PATH = "hooks-path-override"
REASON_MIRROR = "mirror-push"
REASON_STDIN_BODY = "body-from-stdin"
REASON_TOO_LARGE = "change-too-large"
REASON_TOO_MANY_COMMITS = "too-many-commits"
REASON_SOURCES_READ = "sources-read-this-session"
REASON_FIRST_PUSH = "first-push-not-reviewed"
REASON_INTERNAL = "check-failed"
REASON_BAD_PAYLOAD = "unreadable-request"
REASON_MISSING_FILE = "body-file-unreadable"
REASON_SEAT_FOLDER = "seat-folder"

SENTENCES = {
    REASON_UNTOKENIZABLE: (
        "GTM Base could not tell what this command does with the shared copy, "
        "so it was not run."
    ),
    REASON_UNREADABLE: (
        "GTM Base could not read what this command would send, so it was not "
        "run."
    ),
    REASON_SEAT_FOLDER: (
        "GTM Base keeps its own records in a folder that commands are not "
        "allowed to touch."
    ),
    REASON_DENIED_COMMAND: (
        "GTM Base stopped this because it changes the shared copy or your "
        "account settings, and nothing GTM Base does needs that command."
    ),
    REASON_NO_VERIFY: (
        "GTM Base stopped this because it would skip the safety check inside "
        "the base."
    ),
    REASON_FORCE_DEFAULT: (
        "GTM Base stopped this because it would overwrite the shared history "
        "everyone else works from."
    ),
    REASON_HOOKS_PATH: (
        "GTM Base stopped this because it would point git at a different set "
        "of safeguards."
    ),
    REASON_MIRROR: (
        "GTM Base stopped this because it would send every part of the base at "
        "once, which the check cannot read."
    ),
    REASON_STDIN_BODY: (
        "GTM Base stopped this because the text it would send is typed in "
        "rather than saved in a file, so the check cannot read it."
    ),
    REASON_TOO_LARGE: (
        "GTM Base stopped this because the change is larger than the check can "
        "read. Send it in smaller pieces."
    ),
    REASON_TOO_MANY_COMMITS: (
        "GTM Base stopped this because there is more saved work here than the "
        "check can read at once."
    ),
    REASON_SOURCES_READ: (
        "GTM Base stopped this because this session read your own documents, "
        "so nothing may leave the computer until you start a new session."
    ),
    REASON_FIRST_PUSH: (
        "This base has never been backed up before; run the first backup "
        "review in the join skill before anything leaves this computer."
    ),
    REASON_INTERNAL: (
        "GTM Base's safety check could not complete, so the command was not "
        "run."
    ),
    REASON_BAD_PAYLOAD: (
        "GTM Base's safety check could not read what it was asked about, so "
        "the command was not run."
    ),
    REASON_MISSING_FILE: (
        "GTM Base stopped this because it could not read the file holding the "
        "text that would be sent."
    ),
}

# Most saved work the check will read through before it refuses.
MAX_PUSH_COMMITS = 2000
# The empty tree, so a first send can be read as though every line were added.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
# Roughly how many bytes a changed line takes, used to size a change up before
# the whole of it is read.
ESTIMATED_BYTES_PER_LINE = 80

_GIT_OR_GH = re.compile(r"(?<![A-Za-z0-9_])(?:git|gh)(?![A-Za-z0-9_])")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SHELL_C = re.compile(r"^-[A-Za-z]*c$")
_STAT_SUMMARY = re.compile(r"(\d+) insertions?\(\+\)|(\d+) deletions?\(-\)")
_ZERO_SHA = re.compile(r"^0{40,}$")

# Settings that would point git at a different set of safeguards.
_HOOKS_PATH_KEYS = ("core.hookspath", "hooks.path")

# Shells whose `-c` argument is another command to read.
_SHELLS = ("sh", "bash", "zsh", "dash", "ksh")
# Words that stand in front of a real command without changing what it is.
_PREFIX_WORDS = ("command", "sudo", "nice", "exec", "nohup", "time", "builtin", "env")
# Those words' options that take a value of their own.
_PREFIX_VALUE_FLAGS = ("-n", "-u", "-g", "-C", "--user", "--group", "-S")

# The options that make `gh api` a write.
_GH_API_WRITE_FLAGS = ("-f", "-F", "--input", "--raw-field", "--field")
# The options that name a file holding the text a command would send.
_BODY_FILE_FLAGS = ("--body-file", "-F", "--input")
# `gh` options that take a value, so the value is not read as a subcommand.
_GH_VALUE_FLAGS = ("-R", "--repo", "--hostname", "-H")

# Everything a quote or a backslash could hide, taken out before any word is
# matched, so `g""it push` and `gi\t push` read as the command they are.
_QUOTING = re.compile(r"[\\'\"]")

# The words a part of a command may start with without being read any further.
# Anything outside this set, in a command that names git or GitHub, is refused.
_INERT_WORDS = (
    "echo", "printf", "cat", "ls", "cd", "pushd", "pwd", "test", "[", "true",
    "false", "head", "tail", "grep", "wc", "sort", "sed", "awk", "mkdir",
    "touch", "cp", "mv",
)
# The words that move the rest of the command line into another folder.
_FOLDER_WORDS = ("cd", "pushd")
# The two interpreters, allowed only when they are handed a file to run and
# nothing after that file names git or GitHub.
_INTERPRETERS = ("python3", "python")
# The word that hands what it reads to another command, and its own options.
_XARGS = "xargs"
_XARGS_VALUE_FLAGS = (
    "-n", "-I", "-i", "-L", "-P", "-s", "-d", "-E", "-a",
    "--max-args", "--replace", "--max-lines", "--max-procs", "--max-chars",
    "--delimiter", "--eof", "--arg-file",
)

# Settings that would run something of their own or hand git a different
# program to run. Any other setting whose name starts with GIT_ is refused too.
_DENIED_ASSIGNMENTS = ("SSH_ASKPASS", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES")
_ALLOWED_GIT_ASSIGNMENTS = ("GIT_TERMINAL_PROMPT", "GIT_PAGER", "GIT_EDITOR")
# The two settings that name the folder git would work in.
_DIRECTORY_ASSIGNMENTS = ("GIT_DIR", "GIT_WORK_TREE")

# Options that hand git a different program to run on either end of a send.
_DENIED_GIT_FLAGS = ("--exec-path", "--upload-pack", "--receive-pack", "--exec")

# Where a part of a command sends its output. None of it is content.
_REDIRECTION_HEAD = re.compile(r"^(?:\d+|&)?(?:>>|>\||>&|<&|<>|>|<)")

# The shape of a git working folder the plugin makes for itself, which sits
# inside the seat folder and is the one part of it a send may name.
_WORKING_FOLDER = re.compile(r"\S*/bases/[^/\s]+/worktrees/\S*")


# --- Verdicts ----------------------------------------------------------------


def deny_payload(client: str, reason_sentence: str) -> str:
    """The refusal one client understands, built in the one place it is built.

    Claude Code and Codex both read a PreToolUse verdict of the same shape.
    Codex has no "ask", so both get "deny" here; the day a client wants a
    different shape, this function is the only thing that changes.
    """
    verdict = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason_sentence,
        }
    }
    del client
    return json.dumps(verdict)


def sentence_for(reason: str) -> str:
    return SENTENCES.get(reason, SENTENCES[REASON_INTERNAL])


# --- Reading a command -------------------------------------------------------


def strip_quoting(text: str) -> str:
    """One command with every quote and backslash taken out.

    Quoting is how a command hides the name of the program it runs, so the
    name is only ever matched against text this has been through.
    """
    return _QUOTING.sub("", text or "")


def mentions_git_or_gh(command: str) -> bool:
    """Whether a command names git or GitHub as a word of its own."""
    return bool(command) and bool(_GIT_OR_GH.search(strip_quoting(command)))


def split_segments(text: str) -> List[str]:
    """Split a command line into the simple commands it is made of.

    Quoted separators do not separate anything, so a semicolon inside a message
    stays part of the message.
    """
    segments: List[str] = []
    current: List[str] = []
    quote = ""
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if quote:
            current.append(character)
            if character == quote:
                quote = ""
            index += 1
            continue
        if character in ("'", '"'):
            quote = character
            current.append(character)
            index += 1
            continue
        if character == "\\" and index + 1 < length:
            if text[index + 1] == "\n":
                # A line carried on to the next one is still one command.
                index += 2
                continue
            current.append(character)
            current.append(text[index + 1])
            index += 2
            continue
        if character == "&" and _is_part_of_a_redirection(current, text, index):
            current.append(character)
            index += 1
            continue
        if character in (";", "\n", "|", "&"):
            segments.append("".join(current))
            current = []
            index += 1
            # A doubled separator is still one separator.
            while index < length and text[index] == character:
                index += 1
            continue
        current.append(character)
        index += 1
    segments.append("".join(current))
    return [segment.strip() for segment in segments if segment.strip()]


def _is_part_of_a_redirection(current: List[str], text: str, index: int) -> bool:
    """Whether this ampersand joins two output streams rather than parting two
    commands, as it does in `2>&1` and in `&> out.txt`."""
    if index + 1 < len(text) and text[index + 1] == ">":
        return True
    for character in reversed(current):
        if character in (" ", "\t"):
            return False
        return character in (">", "<")
    return False


class PushSpec(object):
    """One send, as the command asked for it."""

    __slots__ = (
        "remote", "refspecs", "force", "delete", "all_refs", "tags", "source",
        "directory", "folder",
    )

    def __init__(self, remote=None, refspecs=None, force=False, delete=False,
                 all_refs=False, tags=False, source="git-push", directory=None,
                 folder=None):
        # The folder the send would run in, when the command named one of its
        # own. It starts as the text the command held and is replaced by the
        # real folder once that folder has been checked.
        self.directory = directory
        # The folder this part of the command line runs in, when an earlier
        # part moved out of the folder the command was typed in. It is not
        # named by the send itself, so it is not checked the same way: it is
        # simply where the send would be read from.
        self.folder = folder
        self.remote = remote
        self.refspecs = list(refspecs or [])
        self.force = force
        self.delete = delete
        self.all_refs = all_refs
        self.tags = tags
        self.source = source

    def __repr__(self) -> str:
        return "PushSpec(remote=%r, refspecs=%r, force=%r)" % (
            self.remote,
            self.refspecs,
            self.force,
        )


class Classification(object):
    """What one command line turned out to be."""

    __slots__ = ("deny_reason", "pushes", "gh_writes", "has_gh", "has_git")

    def __init__(self):
        self.deny_reason: Optional[str] = None
        self.pushes: List[PushSpec] = []
        self.gh_writes: List[List[str]] = []
        self.has_gh = False
        self.has_git = False

    @property
    def needs_scan(self) -> bool:
        return bool(self.pushes or self.gh_writes)

    def deny(self, reason: str) -> None:
        if self.deny_reason is None:
            self.deny_reason = reason

    def __repr__(self) -> str:
        return "Classification(deny=%r, pushes=%d, gh=%d)" % (
            self.deny_reason,
            len(self.pushes),
            len(self.gh_writes),
        )


class _Folder(object):
    """The folder each part of one command line would run in.

    A command line can move itself before it sends anything, so the folder a
    send runs in is not always the folder the command was typed in. This walks
    that along: it starts where the request said the person is, and every part
    that changes folder changes it. A change this cannot follow, such as one
    written with a variable or one that goes back to wherever the last change
    came from, leaves the folder unknown, and a send from an unknown folder is
    refused rather than read against the wrong folder.
    """

    __slots__ = ("path", "start", "unknown")

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.start = path
        self.unknown = False

    @property
    def moved(self) -> bool:
        """Whether the command line has left the folder it was typed in."""
        return not self.unknown and self.path is not None and self.path != self.start

    def here(self) -> Optional[str]:
        """The folder to read a send against, or None to use the typed-in one."""
        return self.path if self.moved else None

    def resolve(self, raw: str) -> str:
        """One folder name a command held, as a whole path where we can."""
        candidate = os.path.expanduser(raw)
        if os.path.isabs(candidate):
            return os.path.normpath(candidate)
        if self.path:
            return os.path.normpath(os.path.join(self.path, candidate))
        return candidate

    def follow(self, tokens: Sequence[str], has_substitution: bool) -> None:
        """Read one folder change and move with it, or lose track of it."""
        word = os.path.basename(tokens[0])
        arguments = list(tokens[1:])
        if has_substitution or any("$" in argument for argument in arguments):
            self.unknown = True
            return
        if not arguments:
            if word == "pushd":
                # With nothing named it swaps two folders we never saw.
                self.unknown = True
                return
            self.path = os.path.expanduser("~")
            self.unknown = False
            return
        if len(arguments) > 1 or arguments[0] == "-":
            self.unknown = True
            return
        self.path = self.resolve(arguments[0])
        self.unknown = False


def _strip_prefixes(tokens: List[str]) -> Tuple[List[str], List[str]]:
    """Drop the words and settings that stand in front of the real command.

    The settings themselves are handed back, because a setting can hand git a
    different program to run or point it at another folder.
    """
    assignments: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _ASSIGNMENT.match(token):
            assignments.append(token)
            index += 1
            continue
        word = os.path.basename(token)
        if word not in _PREFIX_WORDS:
            break
        index += 1
        while index < len(tokens):
            following = tokens[index]
            if _ASSIGNMENT.match(following):
                assignments.append(following)
                index += 1
                continue
            if following.startswith("-"):
                index += 1
                if following in _PREFIX_VALUE_FLAGS and index < len(tokens):
                    index += 1
                continue
            break
    return tokens[index:], assignments


def _strip_redirections(tokens: List[str]) -> List[str]:
    """Drop where a command sends its output. None of it is content."""
    kept: List[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        match = _REDIRECTION_HEAD.match(token)
        if match:
            if match.end() == len(token):
                # The place it writes to is the next word.
                index += 2
                continue
            index += 1
            continue
        kept.append(token)
        index += 1
    return kept


def _strip_xargs(tokens: List[str]) -> List[str]:
    """Drop the word that hands what it reads to another command, and its
    options, so the command it would run is read as itself."""
    while tokens and os.path.basename(tokens[0]) == _XARGS:
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if not token.startswith("-"):
                break
            index += 1
            if token in _XARGS_VALUE_FLAGS and index < len(tokens):
                index += 1
        tokens = tokens[index:]
    return tokens


def _substitution_bodies(text: str) -> Tuple[List[str], str]:
    """Every command written inside another one, and what is left over.

    Both forms are read: the one written with a dollar sign and brackets, and
    the older one written between two backward quotes.
    """
    bodies: List[str] = []
    rest: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == "$" and index + 1 < length and text[index + 1] == "(":
            depth = 1
            start = index + 2
            scan = start
            while scan < length and depth:
                if text[scan] == "(":
                    depth += 1
                elif text[scan] == ")":
                    depth -= 1
                scan += 1
            bodies.append(text[start : scan - 1] if depth == 0 else text[start:])
            index = scan
            continue
        if character == "`":
            end = text.find("`", index + 1)
            if end == -1:
                bodies.append(text[index + 1 :])
                index = length
                continue
            bodies.append(text[index + 1 : end])
            index = end + 1
            continue
        rest.append(character)
        index += 1
    return bodies, "".join(rest)


def _is_inert(tokens: Sequence[str]) -> bool:
    """Whether a part of a command is one of the few we read no further."""
    word = os.path.basename(tokens[0])
    if word in _INERT_WORDS:
        return True
    if word in _INTERPRETERS:
        if len(tokens) < 2 or not tokens[1].endswith(".py"):
            return False
        for token in tokens[2:]:
            lowered = strip_quoting(token).lower()
            if "git" in lowered or "gh" in lowered:
                return False
        return True
    return False


def _assignment_codes(assignments: Sequence[str], result: "Classification") -> Optional[str]:
    """Read the settings in front of a command. Return a folder one names."""
    directory = None
    for token in assignments:
        name = token.split("=", 1)[0]
        if name in _DIRECTORY_ASSIGNMENTS:
            value = token.split("=", 1)[1] if "=" in token else ""
            if value:
                directory = value
            continue
        if name in _DENIED_ASSIGNMENTS:
            result.deny(REASON_DENIED_COMMAND)
            continue
        if name.startswith("GIT_") and name not in _ALLOWED_GIT_ASSIGNMENTS:
            result.deny(REASON_DENIED_COMMAND)
    return directory


def _shell_script_argument(tokens: List[str]) -> Optional[str]:
    """The command a shell was asked to run, when that is what this is."""
    if not tokens:
        return None
    if os.path.basename(tokens[0]) not in _SHELLS:
        return None
    for position, token in enumerate(tokens[1:], start=1):
        if _SHELL_C.match(token) and position + 1 < len(tokens):
            return tokens[position + 1]
    return None


def _classify_git(
    tokens: List[str],
    result: Classification,
    directory: Optional[str] = None,
    folder: Optional["_Folder"] = None,
) -> None:
    result.has_git = True
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-c" or token == "--config-env":
            index += 1
            if index < len(tokens):
                key = tokens[index].split("=", 1)[0].strip().lower()
                if key in _HOOKS_PATH_KEYS:
                    result.deny(REASON_HOOKS_PATH)
                index += 1
            continue
        if token.startswith("--config-env=") or token.startswith("-c"):
            body = token.split("=", 1)[0]
            key = (
                token.split("=", 1)[1].split("=", 1)[0]
                if body == "--config-env"
                else token[2:].split("=", 1)[0]
            ).strip().lower()
            if key in _HOOKS_PATH_KEYS:
                result.deny(REASON_HOOKS_PATH)
            index += 1
            continue
        name = token.split("=", 1)[0]
        if name in _DENIED_GIT_FLAGS:
            result.deny(REASON_DENIED_COMMAND)
            index += 1 if "=" in token else 2
            continue
        if name in ("-C", "--git-dir", "--work-tree"):
            if "=" in token:
                value = token.split("=", 1)[1]
                index += 1
            else:
                value = tokens[index + 1] if index + 1 < len(tokens) else ""
                index += 2
            if value:
                directory = value
            continue
        if token == "--namespace":
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    if index >= len(tokens):
        return
    subcommand = tokens[index]
    rest = tokens[index + 1 :]
    if subcommand not in ("push", "send-pack"):
        return
    push = _parse_push(rest, result)
    push.directory = folder.resolve(directory) if (directory and folder) else directory
    push.folder = folder.here() if folder else None
    result.pushes.append(push)


def _parse_push(rest: Sequence[str], result: Classification) -> PushSpec:
    push = PushSpec()
    positional: List[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--":
            positional.extend(rest[index + 1 :])
            break
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            if name == "--no-verify":
                result.deny(REASON_NO_VERIFY)
            elif name in ("--force", "--force-with-lease", "--force-if-includes"):
                push.force = True
            elif name == "--mirror":
                result.deny(REASON_MIRROR)
            elif name == "--all":
                push.all_refs = True
            elif name == "--tags":
                push.tags = True
            elif name == "--delete":
                push.delete = True
            elif name in _DENIED_GIT_FLAGS:
                result.deny(REASON_DENIED_COMMAND)
                if "=" not in token:
                    index += 1
            elif name in ("--push-option", "--repo") and "=" not in token:
                index += 1
            index += 1
            continue
        if token.startswith("-") and len(token) > 1:
            letters = token[1:]
            if "f" in letters:
                push.force = True
            if "d" in letters:
                push.delete = True
            if letters.endswith("o"):
                index += 1
            index += 1
            continue
        positional.append(token)
        index += 1
    if positional:
        push.remote = positional[0]
        push.refspecs = positional[1:]
    return push


def _gh_words(tokens: List[str]) -> List[str]:
    """The subcommand words of a GitHub command, with option values skipped."""
    words: List[str] = []
    index = 1
    while index < len(tokens) and len(words) < 2:
        token = tokens[index]
        if token.startswith("-"):
            index += 1
            if token in _GH_VALUE_FLAGS:
                index += 1
            continue
        words.append(token)
        index += 1
    return words


def _gh_api_is_a_write(tokens: Sequence[str]) -> bool:
    index = 0
    while index < len(tokens):
        token = tokens[index]
        name = token.split("=", 1)[0]
        if name in _GH_API_WRITE_FLAGS:
            return True
        if name in ("-X", "--method"):
            value = token.split("=", 1)[1] if "=" in token else (
                tokens[index + 1] if index + 1 < len(tokens) else ""
            )
            if value.strip().upper() not in ("GET", ""):
                return True
        index += 1
    return False


def _classify_gh(tokens: List[str], result: Classification) -> None:
    result.has_gh = True
    words = _gh_words(tokens)
    if not words:
        return
    pair = tuple(words[:2])
    single = (words[0],)
    for denied in constants.GH_DENIED_OUTRIGHT:
        if denied == single or denied == pair:
            result.deny(REASON_DENIED_COMMAND)
            return
    if pair in constants.GH_GATED_WRITES:
        result.gh_writes.append(list(tokens))
        return
    if words[0] == "api" and _gh_api_is_a_write(tokens[1:]):
        result.gh_writes.append(list(tokens))
        return
    if pair == ("repo", "create") and (
        "--push" in tokens or "--source" in tokens
        or any(token.startswith("--source=") for token in tokens)
    ):
        result.gh_writes.append(list(tokens))
        result.pushes.append(PushSpec(source="gh-repo-create"))
        return


def classify(
    command: str, depth: int = 0, cwd: Optional[str] = None
) -> Classification:
    """Work out what a command line would send, or refuse to guess.

    A command that never names git or GitHub is left alone. Once it does name
    one of them, every part of it has to be accounted for: a part whose first
    word is neither of them and is not on the short harmless list is refused,
    rather than read as though it did nothing.

    The parts are read in the order they run, because a part that changes
    folder changes where every part after it would send from.
    """
    result = Classification()
    if depth > 3:
        result.deny(REASON_UNTOKENIZABLE)
        return result
    strict = mentions_git_or_gh(command)
    folder = _Folder(cwd)
    for segment in split_segments(command):
        _classify_segment(segment, result, depth, strict, folder)
    return result


def _classify_segment(
    segment: str,
    result: Classification,
    depth: int,
    strict: bool,
    folder: Optional["_Folder"] = None,
) -> None:
    """Read one simple command, and every command written inside it."""
    if folder is None:
        folder = _Folder(None)
    bodies, remainder = _substitution_bodies(segment)
    for body in bodies:
        _merge(result, classify(body, depth + 1, cwd=folder.path))
    try:
        tokens = shlex.split(remainder, posix=True)
    except ValueError:
        result.deny(REASON_UNTOKENIZABLE)
        return
    tokens = _strip_redirections(tokens)
    tokens, assignments = _strip_prefixes(tokens)
    directory = _assignment_codes(assignments, result)
    if not tokens:
        return
    script = _shell_script_argument(tokens)
    if script is not None:
        # A shell of its own starts where this part does and ends there too,
        # so a folder change inside it is not carried out to what follows.
        _merge(result, classify(script, depth + 1, cwd=folder.path))
        return
    tokens = _strip_xargs(tokens)
    if not tokens:
        return
    word = os.path.basename(tokens[0])
    if word in _FOLDER_WORDS:
        folder.follow(tokens, bool(bodies))
        return
    if word in ("git", "gh"):
        if folder.unknown:
            # We lost track of the folder, so we cannot read what this would
            # send. It is refused rather than read against the wrong folder.
            result.deny(REASON_UNTOKENIZABLE)
            return
        if word == "git":
            _classify_git(tokens, result, directory, folder)
        else:
            _classify_gh(tokens, result)
        return
    if strict and not _is_inert(tokens):
        result.deny(REASON_UNTOKENIZABLE)


def _merge(result: Classification, other: Classification) -> None:
    if other.deny_reason:
        result.deny(other.deny_reason)
    result.pushes.extend(other.pushes)
    result.gh_writes.extend(other.gh_writes)
    result.has_gh = result.has_gh or other.has_gh
    result.has_git = result.has_git or other.has_git


# --- Working out what a send would carry -------------------------------------


def default_branch(git: GitRunner, cwd: str, remote: str = "origin") -> Optional[str]:
    """The branch the team shares, as this clone understands it."""
    head = git.run(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/%s/HEAD" % remote], cwd=cwd
    )
    if head.ok and head.out():
        return head.out().split("/", 1)[-1]
    for candidate in ("main", "master"):
        exists = git.run(
            ["show-ref", "--verify", "--quiet", "refs/heads/" + candidate], cwd=cwd
        )
        if exists.ok:
            return candidate
    return None


def _target_names(push: PushSpec) -> List[str]:
    """The branches on the shared copy a send would write to."""
    names = []
    for spec in push.refspecs:
        text = spec[1:] if spec.startswith("+") else spec
        target = text.split(":", 1)[1] if ":" in text else text
        names.append(target.rsplit("/", 1)[-1])
    return names


def _forces_default_branch(git, cwd, push, branch_now) -> bool:
    if not push.force and not any(spec.startswith("+") for spec in push.refspecs):
        return False
    name = default_branch(git, cwd, push.remote or "origin")
    if not name:
        return True
    targets = _target_names(push)
    if not targets:
        return branch_now == name
    return name in targets


def _current_branch(git: GitRunner, cwd: str) -> Optional[str]:
    result = git.run(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd)
    return result.out() if result.ok and result.out() else None


def _upstream_for(git, cwd, remote, source_ref, target_ref) -> Optional[str]:
    """The point on the shared copy a send would build on, if we can find it."""
    if source_ref in ("HEAD", "") or source_ref == target_ref:
        tracked = git.run(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=cwd
        )
        if tracked.ok and tracked.out() and "@{u}" not in tracked.out():
            return tracked.out()
    name = target_ref.rsplit("/", 1)[-1]
    candidate = "refs/remotes/%s/%s" % (remote, name)
    if git.run(["rev-parse", "--verify", "--quiet", candidate], cwd=cwd).ok:
        return candidate
    branch = default_branch(git, cwd, remote)
    if branch:
        base = git.run(["merge-base", source_ref or "HEAD", branch], cwd=cwd)
        if base.ok and base.out():
            return base.out()
    return None


def ranges_for_push(git: GitRunner, cwd: str, push: PushSpec) -> List[Tuple[str, str]]:
    """Every (starting point, ending point) a send would carry."""
    remote = push.remote or "origin"
    specs = list(push.refspecs) or ["HEAD"]
    ranges: List[Tuple[str, str]] = []
    for spec in specs:
        text = spec[1:] if spec.startswith("+") else spec
        if ":" in text:
            source_ref, target_ref = text.split(":", 1)
        else:
            source_ref, target_ref = text, text
        if not source_ref:
            continue
        upstream = _upstream_for(git, cwd, remote, source_ref, target_ref)
        ranges.append((upstream or EMPTY_TREE, source_ref))
    return ranges


def _stat_estimate_bytes(git: GitRunner, cwd: str, start: str, end: str) -> int:
    """How large a change looks, before any of it is read."""
    result = git.run(["diff", "%s..%s" % (start, end), "--stat", "--no-color"], cwd=cwd)
    if not result.ok:
        result = git.run(["diff", start, end, "--stat", "--no-color"], cwd=cwd)
    if not result.ok:
        return 0
    text = result.stdout
    lines = 0
    for match in _STAT_SUMMARY.finditer(text):
        for group in match.groups():
            if group:
                lines += int(group)
    if lines == 0:
        return len(text.encode("utf-8", "replace"))
    return lines * ESTIMATED_BYTES_PER_LINE


def _diff_text(git: GitRunner, cwd: str, start: str, end: str) -> Optional[str]:
    """The change one range would send, or None when git could not read it."""
    result = git.run(
        [
            "diff",
            "%s..%s" % (start, end),
            "--unified=0",
            "--no-color",
            "--diff-filter=ACMR",
        ],
        cwd=cwd,
    )
    if not result.ok:
        result = git.run(
            [
                "diff",
                start,
                end,
                "--unified=0",
                "--no-color",
                "--diff-filter=ACMR",
            ],
            cwd=cwd,
        )
    return result.stdout if result.ok else None


def _messages_text(git: GitRunner, cwd: str, start: str, end: str) -> Optional[str]:
    """The saved notes one range would send, or None when they cannot be read."""
    if start == EMPTY_TREE:
        result = git.run(
            ["log", end, "--format=%B", "--max-count=%d" % MAX_PUSH_COMMITS], cwd=cwd
        )
    else:
        result = git.run(["log", "%s..%s" % (start, end), "--format=%B"], cwd=cwd)
    return result.stdout if result.ok else None


def _commit_count(git: GitRunner, cwd: str, start: str, end: str) -> int:
    if start == EMPTY_TREE:
        args = ["rev-list", "--max-count=%d" % (MAX_PUSH_COMMITS + 1), "--count", end]
    else:
        args = [
            "rev-list",
            "--max-count=%d" % (MAX_PUSH_COMMITS + 1),
            "--count",
            "%s..%s" % (start, end),
        ]
    result = git.run(args, cwd=cwd)
    if not result.ok:
        return 0
    try:
        return int(result.out())
    except ValueError:
        return 0


# --- The body a GitHub command would send ------------------------------------


def body_files(tokens: Sequence[str]) -> Tuple[List[str], bool]:
    """The files a GitHub command would read its text from, and whether it
    would read that text from what a person typed in instead."""
    files: List[str] = []
    from_stdin = False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        name = token.split("=", 1)[0]
        if name in _BODY_FILE_FLAGS:
            if "=" in token:
                value = token.split("=", 1)[1]
            else:
                index += 1
                value = tokens[index] if index < len(tokens) else ""
            if name == "-F" and "=" in value:
                # `gh api -F key=@file` names a field, not a body file.
                field_value = value.split("=", 1)[1]
                if field_value.startswith("@"):
                    candidate = field_value[1:]
                    if candidate == "-":
                        from_stdin = True
                    elif candidate:
                        files.append(candidate)
                index += 1
                continue
            if value == "-":
                from_stdin = True
            elif value:
                files.append(value)
        index += 1
    return files, from_stdin


# --- The two session conditions ----------------------------------------------


def first_push_is_unreviewed(cwd: str, git: Optional[GitRunner] = None) -> bool:
    """Whether this base has never had its first backup reviewed.

    The answer itself comes from `push_conditions`, so the check on the command
    tool and the skills that ask before they prepare anything can never
    disagree. All this adds is working out which base the folder belongs to.
    """
    from . import push_conditions

    try:
        resolution = paths.resolve_base(cwd, machine.load_machine_state(runner=git), runner=git)
    except Exception:
        return False
    if not resolution.joined or not resolution.base_id:
        return False
    return push_conditions.first_push_unreviewed(resolution.base_id)


def named_folder_path(raw: str, cwd: str) -> str:
    """The whole path one folder name in a command points at.

    A name written relative to somewhere is joined onto the folder the command
    runs in, and the folder git keeps its own records in is read as the folder
    holding it, so `--git-dir` and `-C` end at the same place.
    """
    candidate = os.path.expanduser(raw)
    if not os.path.isabs(candidate):
        candidate = os.path.join(cwd, candidate)
    real = os.path.realpath(candidate)
    if os.path.basename(real) == ".git":
        real = os.path.dirname(real)
    return real


def resolve_working_folder(
    raw: str, cwd: str, git: Optional[GitRunner] = None
) -> Optional[str]:
    """The real folder a command named, when it is one the gate knows.

    The two it knows are a base this account has joined and a folder inside
    this seat's own folder, which is where the plugin does its git work. Any
    other folder gets no answer here: it is a repository of the person's own,
    the send from it is not read, and it is not taken out of the text the seat
    folder rule reads.
    """
    try:
        real = named_folder_path(raw, cwd)
        if not os.path.isdir(real):
            return None
        seat = os.path.realpath(paths.seat_home_path())
        if real == seat or real.startswith(seat + os.sep):
            return real
        resolution = paths.resolve_base(
            real, machine.load_machine_state(runner=git), runner=git
        )
        if resolution.joined and resolution.root:
            return resolution.root
    except Exception:
        return None
    return None


def _resolve_push_folders(
    result: Classification, cwd: str, git: Optional[GitRunner]
) -> List[str]:
    """Point every send at the folder it would really run in.

    The text of the folders the gate knows comes back, so the seat folder rule
    can leave those names alone. A folder it does not know is still filled in,
    because the scope question below is asked of the folder each send would
    run in, and a send from a folder outside the gate's reach is allowed.
    """
    accepted: List[str] = []
    for push in result.pushes:
        raw = push.directory
        if not raw:
            continue
        real = resolve_working_folder(raw, cwd, git)
        if real is None:
            try:
                push.directory = named_folder_path(raw, cwd)
            except Exception:
                push.directory = None
            continue
        accepted.append(raw)
        push.directory = real
    return accepted


def _is_a_working_folder(real: str) -> bool:
    """Whether a path sits inside the git work folders this seat makes.

    The shape is `<seat folder>/bases/<base>/worktrees/<folder>`. It is read as
    a path rather than looked up in the seat's records, so asking the question
    never brings the seat folder into being.
    """
    try:
        seat = os.path.realpath(paths.seat_home_path())
    except Exception:
        return False
    bases = os.path.join(seat, "bases") + os.sep
    if not real.startswith(bases):
        return False
    parts = real[len(bases) :].split(os.sep)
    return len(parts) > 2 and parts[1] == "worktrees"


def folder_is_in_scope(folder: str, runner: Optional[GitRunner] = None) -> bool:
    """Whether what a send from this folder would carry is read at all.

    Two answers are yes. A base this account has joined, including any folder
    inside it, because that is where the company's own writing lives. And a
    working folder under this seat's own folder, because that is where the
    plugin prepares a change before it is sent. Every other folder on the
    machine belongs to work that is not a base, and none of it is read.
    """
    try:
        real = os.path.realpath(folder or "")
        if _is_a_working_folder(real):
            return True
        account = machine.load_machine_state(runner=runner)
        if paths.resolve_base(real, account, runner=runner).joined:
            return True
        root = paths.git_root(real, runner=runner)
        if root and root != real:
            return bool(paths.resolve_base(root, account, runner=runner).joined)
    except Exception:
        return False
    return False


def _scope_by_folder(result: Classification, cwd: str, runner: Optional[GitRunner]):
    """For every folder this command would send from, whether the gate reads it.

    A GitHub command names no folder of its own, so it is read against the
    folder the command was typed in, which is also the folder the file holding
    its text is looked for in.
    """
    answers = {}
    for push in result.pushes:
        folder = push.directory or push.folder or cwd
        if folder not in answers:
            answers[folder] = folder_is_in_scope(folder, runner)
    if result.gh_writes and cwd not in answers:
        answers[cwd] = folder_is_in_scope(cwd, runner)
    return answers


def names_the_seat_folder(command: str, accepted: Sequence[str] = ()) -> bool:
    """Whether a command names the folder holding this seat's own records.

    The folder a send was allowed to run in is taken out of the text first, so
    the one command that may name that folder is not refused for naming it.
    The git working folders the plugin makes for itself are taken out as well:
    they sit inside this folder, a send may name one, and the check that a send
    naming one is really pointed at a working folder has already run by then.
    """
    text = strip_quoting(command or "")
    for value in accepted:
        if value:
            text = text.replace(value, " ")
    text = _WORKING_FOLDER.sub(" ", text)
    if constants.SEAT_HOME_ENV in text:
        return True
    if ".gtm-base" in text:
        return True
    try:
        home = paths.seat_home_path()
    except Exception:
        home = None
    return bool(home and home in text)


def base_root_for(cwd: str, git: Optional[GitRunner] = None) -> Optional[str]:
    try:
        resolution = paths.resolve_base(cwd, machine.load_machine_state(runner=git), runner=git)
    except Exception:
        return None
    return resolution.root


# --- The check itself --------------------------------------------------------


def check_command(
    command: str,
    cwd: str,
    session_id: Optional[str],
    git: Optional[GitRunner] = None,
) -> Optional[str]:
    """Read one command line. Return the reason to refuse, or None to allow."""
    runner = runner_or_default(git)
    if not mentions_git_or_gh(command):
        if names_the_seat_folder(command):
            return sentence_for(REASON_SEAT_FOLDER)
        return None
    result = classify(command, cwd=cwd)
    accepted = _resolve_push_folders(result, cwd, runner)
    if names_the_seat_folder(command, accepted):
        return sentence_for(REASON_SEAT_FOLDER)

    if result.deny_reason == REASON_UNTOKENIZABLE:
        # The command is refused either way. Saying which class it holds means
        # reading the command line as content, so that is only done where the
        # gate reads content at all.
        if folder_is_in_scope(cwd, runner):
            hits = scan.scan_command(command, None)
            if hits:
                return hits[0].sentence()
        return sentence_for(REASON_UNTOKENIZABLE)
    if result.deny_reason:
        return sentence_for(result.deny_reason)

    if (result.has_gh or result.pushes) and marker.marker_matches_session(session_id):
        return sentence_for(REASON_SOURCES_READ)

    if not result.needs_scan:
        return None

    # Whether each folder this command would send from is one the gate reads,
    # worked out once, because the answer costs a look at the base's records.
    scope = _scope_by_folder(result, cwd, runner)
    reads_something = any(scope.values())

    allowlist = None
    if reads_something:
        if first_push_is_unreviewed(cwd, git=runner):
            return sentence_for(REASON_FIRST_PUSH)

        allowlist, _code = scan.load_allowlist(base_root_for(cwd, git=runner))

        hits = scan.scan_command(command, allowlist)
        if hits:
            return hits[0].sentence()

        for tokens in result.gh_writes:
            files, from_stdin = body_files(tokens)
            if from_stdin:
                return sentence_for(REASON_STDIN_BODY)
            for name in files:
                path = name if os.path.isabs(name) else os.path.join(cwd, name)
                text = None
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        text = handle.read(constants.MAX_ARTIFACT_BYTES + 1)
                except OSError:
                    return sentence_for(REASON_MISSING_FILE)
                if len(text.encode("utf-8", "replace")) > constants.MAX_ARTIFACT_BYTES:
                    return sentence_for(REASON_TOO_LARGE)
                found = scan.scan_text(text, allowlist, name)
                if found:
                    return found[0].sentence()

    for push in result.pushes:
        # A send that named a folder of its own is read against that folder,
        # and a send an earlier part of the command line moved into is read
        # against the folder it was moved into, not against the folder the
        # command was typed in.
        where = push.directory or push.folder or cwd
        reads_this_one = scope.get(where, False)
        if paths.git_root(where, runner=runner) is None:
            if reads_this_one:
                # Nothing here to read the send against, so there is no way to
                # know what it would send.
                return sentence_for(REASON_UNREADABLE)
            # Outside the gate's reach and not a repository either. Git says so
            # itself, and nothing here has to be read to let it.
            continue
        branch_now = _current_branch(runner, where)
        # Overwriting the branch the team shares is refused wherever it is run,
        # because knowing what it would undo takes nothing being read.
        if _forces_default_branch(runner, where, push, branch_now):
            return sentence_for(REASON_FORCE_DEFAULT)
        if push.delete or not reads_this_one:
            continue
        for start, end in ranges_for_push(runner, where, push):
            reason = scan_range(runner, where, start, end, allowlist)
            if reason:
                return reason
    return None


def scan_range(
    git: GitRunner,
    cwd: str,
    start: str,
    end: str,
    allowlist=None,
) -> Optional[str]:
    """Read everything one range would send. Return a sentence, or None."""
    if _commit_count(git, cwd, start, end) > MAX_PUSH_COMMITS:
        return sentence_for(REASON_TOO_MANY_COMMITS)
    if _stat_estimate_bytes(git, cwd, start, end) > constants.MAX_DIFF_BYTES:
        return sentence_for(REASON_TOO_LARGE)
    diff = _diff_text(git, cwd, start, end)
    if diff is None:
        return sentence_for(REASON_UNREADABLE)
    if len(diff.encode("utf-8", "replace")) > constants.MAX_DIFF_BYTES:
        return sentence_for(REASON_TOO_LARGE)
    hits = scan.scan_diff_added_lines(diff, allowlist)
    if hits:
        return hits[0].sentence()
    messages = _messages_text(git, cwd, start, end)
    if messages is None:
        return sentence_for(REASON_UNREADABLE)
    hits = scan.scan_text(messages, allowlist, "a saved note on your work")
    if hits:
        return hits[0].sentence()
    return None


# --- The safeguard git itself runs -------------------------------------------


def check_git_hook(
    stdin_text: str, cwd: str, git: Optional[GitRunner] = None
) -> Optional[str]:
    """Read every range git is about to send. Return a sentence, or None."""
    runner = runner_or_default(git)
    if marker.marker_is_recent():
        return sentence_for(REASON_SOURCES_READ)
    if first_push_is_unreviewed(cwd, git=runner):
        return sentence_for(REASON_FIRST_PUSH)
    allowlist, _code = scan.load_allowlist(base_root_for(cwd, git=runner))
    branch = default_branch(runner, cwd)
    for line in (stdin_text or "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local_ref, local_sha, _remote_ref, remote_sha = parts[:4]
        if _ZERO_SHA.match(local_sha):
            continue
        if _ZERO_SHA.match(remote_sha):
            start = None
            if branch:
                base = runner.run(["merge-base", local_sha, branch], cwd=cwd)
                if base.ok and base.out():
                    start = base.out()
            start = start or EMPTY_TREE
        else:
            start = remote_sha
        reason = scan_range(runner, cwd, start, local_ref or local_sha, allowlist)
        if reason:
            return reason
    return None


# --- The entry point ---------------------------------------------------------


def _read_arguments(argv: Sequence[str]) -> Tuple[str, str, List[str]]:
    client = CLIENT_CLAUDE
    mode = MODE_HOOK
    rest: List[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--client" and index + 1 < len(argv):
            client = argv[index + 1]
            index += 2
            continue
        if token == "--mode" and index + 1 < len(argv):
            mode = argv[index + 1]
            index += 2
            continue
        rest.append(token)
        index += 1
    return client, mode, rest


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Read one request and either say nothing or refuse, never both."""
    argv = list(sys.argv[1:] if argv is None else argv)
    client, mode, _rest = _read_arguments(argv)
    try:
        stdin_text = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        stdin_text = ""

    if mode == MODE_GIT_HOOK:
        try:
            reason = check_git_hook(stdin_text, os.getcwd())
        except Exception:
            reason = sentence_for(REASON_INTERNAL)
        if reason:
            sys.stderr.write(reason + "\n")
            return 1
        return 0

    try:
        payload = json.loads(stdin_text) if stdin_text.strip() else None
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        sys.stdout.write(deny_payload(client, sentence_for(REASON_BAD_PAYLOAD)) + "\n")
        return 0

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool_name != "Bash" or not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        cwd = os.getcwd()
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = None

    try:
        reason = check_command(command, cwd, session_id)
    except Exception:
        reason = sentence_for(REASON_INTERNAL)
    if reason:
        sys.stdout.write(deny_payload(client, reason) + "\n")
    return 0
