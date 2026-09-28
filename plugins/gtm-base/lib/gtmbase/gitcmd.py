"""The one way this plugin runs git.

Every git call in the library goes through a runner object, so tests can hand
in a stand-in and no module reaches for a subprocess of its own. The runner
never lets git ask for a password, always sets a time limit, and keeps git's
own error text on the result rather than passing it into anything a person or
a model sees.

It also runs nothing the base itself names to run (Astra's review of 0.3.3,
finding 1). A base is a folder of somebody's files, and git runs programs a
folder can name: hooks on a save, an update, a checkout or a change of any
reference; a monitor on a status; a signing program on a save; and the
filter and merge programs its attribute files point at. One `post-commit`
file was enough to send a base's private files anywhere the moment the owner
approved a local save. `hook_free` and `executable_drivers` below are the one
place that is closed, and every call the runner makes goes through them, so
every save, update and move in the plugin, and every one added later, is
covered without asking each caller to remember.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from typing import List, Optional, Sequence, Tuple

from .errors import GitError

DEFAULT_TIMEOUT_SECONDS = 20

# Exit codes this library invents for the two failures git cannot report itself.
TIMEOUT_CODE = 124
MISSING_CODE = 127
# And for the one it refuses before git runs at all: the base names a filter or
# merge program for its files, which the command could run.
DRIVER_CODE = 125
CODE_EXECUTABLE_DRIVER = "executable-driver"

# --- Running nothing the base names ------------------------------------------

# The settings every command runs with, ahead of anything else on its line.
# `core.hooksPath` pointed at the null device finds no hook of any name, and
# nobody can put one there, which an empty folder cannot promise. It covers
# every hook git has: the ones a save runs (pre-commit, prepare-commit-msg,
# commit-msg, post-commit, and pre-auto-gc for the tidying a save can start),
# the one an update runs (post-merge), the ones a checkout, a switch or a new
# working folder runs (post-checkout), the ones a rewrite runs (pre-rebase,
# post-rewrite), and reference-transaction, which every change of a reference
# runs. A setting given this way reaches every git process the command
# starts, so a tidy-up a save starts is covered too. The monitor a status can
# run, and the program that signs a save, are switched off beside it.
HOOK_FREE_SETTINGS = (
    ("core.hooksPath", os.devnull),
    ("core.fsmonitor", "false"),
    ("commit.gpgSign", "false"),
    ("tag.gpgSign", "false"),
    # Checking a signature runs the configured program as surely as making
    # one does: a signed save read back with signatures shown, or an update
    # told to check them (Astra's confirmation of 0.3.3, defect 2).
    ("log.showSignature", "false"),
    ("merge.verifySignatures", "false"),
)
# A send keeps its hooks, and runs no signing program either.
SEND_SETTINGS = (("push.gpgSign", "false"),)
# A send keeps its hooks. The plugin's own safeguard before anything leaves
# this computer is a pre-push hook, and turning hooks off for a send would
# turn that off with them.
KEEPS_ITS_HOOKS = ("push", "send-pack")
# Reading a setting back would read the value set here rather than the
# base's own, and the safeguard's installer asks where the hooks folder is.
READS_ITS_SETTINGS = ("config",)
# Commands that read what is already saved and never run a filter or a merge
# program, so they need no look at the base's attribute files first.
NO_DRIVER_CAN_RUN = (
    "rev-parse",
    "config",
    "ls-files",
    "cat-file",
    "check-attr",
    "symbolic-ref",
    "remote",
    "rev-list",
    "for-each-ref",
    "merge-base",
    "ls-tree",
    "ls-remote",
    "fetch",
    "push",
    "send-pack",
    "init",
    "var",
    "version",
    "log",
    "show",
    "blame",
)
# Reading a difference can run a program the base names for showing one, so
# those commands are told not to, whatever the base says.
NO_DIFF_PROGRAMS = {
    "diff": ("--no-ext-diff", "--no-textconv"),
    "show": ("--no-ext-diff", "--no-textconv"),
    "log": ("--no-ext-diff", "--no-textconv"),
    "blame": ("--no-textconv",),
}
# The options that come before the command itself and take a value.
_GLOBAL_WITH_VALUE = ("-c", "-C", "--git-dir", "--work-tree", "--namespace")
# The attribute that names a program, and the setting that says what it runs.
_ATTRIBUTE_RE = re.compile(r"(?:^|\s)(filter|merge)=([^\s]+)")
_DRIVER_SETTING_RE = r"^(filter|merge)\..+\.(clean|smudge|process|driver)$"


def subcommand_of(args: Sequence[str]) -> Tuple[int, str]:
    """Where the command itself sits in a line of arguments, and what it is."""
    words = [str(one) for one in args]
    index = 0
    while index < len(words):
        word = words[index]
        if word in _GLOBAL_WITH_VALUE:
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        return index, word
    return len(words), ""


def hook_free(args: Sequence[str]) -> List[str]:
    """One command, with every hook, monitor and signing program switched off.

    A send is left exactly as it was, because the safeguard before a send is
    a hook, and so is a command that reads the base's own settings back.
    """
    words = [str(one) for one in args]
    index, command = subcommand_of(words)
    if command in KEEPS_ITS_HOOKS:
        # The pre-push safeguard is a hook, so the hooks stay; signing a send
        # would run a program the base names, so that does not.
        prefix = []
        for name, value in SEND_SETTINGS:
            prefix += ["-c", "%s=%s" % (name, value)]
        return prefix + words
    if command in READS_ITS_SETTINGS:
        return words
    if "--git-path" in words:
        # Where the hooks folder is, which the safeguard's installer asks.
        return words
    extra = NO_DIFF_PROGRAMS.get(command)
    if extra:
        words = words[: index + 1] + list(extra) + words[index + 1 :]
    prefix: List[str] = []
    for name, value in HOOK_FREE_SETTINGS:
        prefix += ["-c", "%s=%s" % (name, value)]
    return prefix + words


def needs_a_driver_check(args: Sequence[str]) -> bool:
    """Whether a command could run a filter or merge program the base names."""
    words = [str(one) for one in args]
    _index, command = subcommand_of(words)
    if not command or command in NO_DRIVER_CAN_RUN:
        return False
    if command == "worktree" and "add" not in words:
        return False
    return True


def _plain(git_path: str, args: Sequence[str], cwd: Optional[str], env: dict) -> str:
    """One read of the base's settings, run without any of the checks above."""
    try:
        finished = subprocess.run(
            [git_path] + list(args),
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return ""
    if finished.returncode != 0:
        return ""
    return finished.stdout.decode("utf-8", "replace")


# The most one attribute file may hold before it is refused rather than read.
# An attribute file this long is not one anybody wrote by hand, and reading
# part of one would be reading past the line that names a program.
ATTRIBUTES_MAX_BYTES = 1024 * 1024
# What stands in for a driver name when an attribute file could not be read
# whole, so a file too long to read is refused like one that names a program.
UNREADABLE_ATTRIBUTES = "an attribute file too large to read"
# The commands that write files out of another tree, and so read that tree's
# own attribute files first (Astra's confirmation of 0.3.3, defect 1).
FROM_ANOTHER_TREE = ("worktree", "checkout", "switch", "merge", "reset", "read-tree", "restore")


def _whole(path: str) -> Optional[str]:
    """One attribute file on the disk, whole, or the stand-in when too long."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(ATTRIBUTES_MAX_BYTES + 1)
    except OSError:
        return None
    if len(data) > ATTRIBUTES_MAX_BYTES:
        return UNREADABLE_ATTRIBUTES
    return data.decode("utf-8", "replace")


def _blob_text(git_path: str, blob: str, cwd: Optional[str], env: dict) -> str:
    """One attribute file saved in the history, whole, or the stand-in."""
    size = _plain(git_path, ["cat-file", "-s", blob], cwd, env).strip()
    if not size.isdigit() or int(size) > ATTRIBUTES_MAX_BYTES:
        return UNREADABLE_ATTRIBUTES
    return _plain(git_path, ["cat-file", "blob", blob], cwd, env)


def _attribute_blobs(listing: str) -> List[str]:
    """The saved attribute files in one NUL-separated listing of a tree or index."""
    found: List[str] = []
    for record in listing.split("\0"):
        meta, tab, name = record.partition("\t")
        if not tab or os.path.basename(name) != ".gitattributes":
            continue
        parts = meta.split()
        # A tree listing is "mode type blob", an index listing "mode blob stage".
        blob = parts[2] if len(parts) >= 3 and parts[1] == "blob" else (
            parts[1] if len(parts) >= 2 else ""
        )
        if blob:
            found.append(blob)
    return found


def _trees_named_by(git_path: str, args: Sequence[str], cwd: Optional[str], env: dict) -> List[str]:
    """The trees a command would write files out of, when it names any."""
    words = [str(one) for one in args]
    index, command = subcommand_of(words)
    if command not in FROM_ANOTHER_TREE:
        return []
    trees: List[str] = []
    for word in words[index + 1 :]:
        if word == "--":
            break
        if not word or word.startswith("-") or word == "add":
            continue
        tree = _plain(
            git_path,
            ["rev-parse", "--verify", "--quiet", "--end-of-options", word + "^{tree}"],
            cwd,
            env,
        ).strip()
        if tree and tree not in trees:
            trees.append(tree)
    return trees


def _attribute_texts(
    git_path: str, cwd: Optional[str], env: dict, args: Sequence[str] = ()
) -> List[str]:
    """Every attribute file git would read for this command, as text.

    The files in the working folder, the one this repository keeps for
    itself, and the one the person's own settings name, read the way git
    reads them: a relative name is read from the top of the working folder,
    where git runs, not from wherever this happens to be running. Then the
    attribute files lined up to be saved, which git reads first when it
    writes files out, and those in any tree the command would write files
    out of, such as the tree a new working folder starts from (Astra's
    confirmation of 0.3.3, defect 1). Every file is read whole or refused.
    """
    texts: List[str] = []
    places: List[str] = []
    top = _plain(git_path, ["rev-parse", "--show-toplevel"], cwd, env).strip()
    where = top or cwd or os.getcwd()
    common = _plain(git_path, ["rev-parse", "--git-common-dir"], cwd, env).strip()
    if common and not os.path.isabs(common):
        common = os.path.join(cwd or os.getcwd(), common)
    if common:
        places.append(os.path.join(common, "info", "attributes"))
    configured = _plain(
        git_path, ["config", "--type=path", "--get", "core.attributesFile"], cwd, env
    ).strip()
    if configured:
        configured = os.path.expanduser(configured)
        if not os.path.isabs(configured):
            configured = os.path.join(where, configured)
        places.append(configured)
    else:
        home = env.get("XDG_CONFIG_HOME") or os.path.join(
            env.get("HOME") or os.path.expanduser("~"), ".config"
        )
        places.append(os.path.join(home, "git", "attributes"))
    if top:
        for folder, folders, files in os.walk(top):
            folders[:] = [one for one in folders if one != ".git"]
            if ".gitattributes" in files:
                places.append(os.path.join(folder, ".gitattributes"))
    for place in places:
        text = _whole(place)
        if text is not None:
            texts.append(text)
    blobs = _attribute_blobs(_plain(git_path, ["ls-files", "-s", "-z"], cwd, env))
    for tree in _trees_named_by(git_path, args, cwd, env):
        blobs += _attribute_blobs(
            _plain(git_path, ["ls-tree", "-r", "-z", tree], cwd, env)
        )
    for blob in dict.fromkeys(blobs):
        texts.append(_blob_text(git_path, blob, cwd, env))
    return texts


def executable_drivers(
    cwd: Optional[str],
    git_path: str = "git",
    env: Optional[dict] = None,
    args: Sequence[str] = (),
) -> List[str]:
    """The filter and merge programs this folder's attributes would run.

    Only a program that is both configured and named by an attribute file in
    effect here counts, so somebody whose own settings carry a filter for
    another kind of project is not refused in a base that never names it.
    Nothing is read out of the answer but the names.
    """
    env = env if env is not None else GitRunner().environment()
    configured = _plain(
        git_path, ["config", "--get-regexp", _DRIVER_SETTING_RE], cwd, env
    )
    drivers = set()
    for line in configured.splitlines():
        key = line.split(" ", 1)[0]
        kind, _dot, rest = key.partition(".")
        name = rest.rsplit(".", 1)[0]
        if kind and name:
            drivers.add((kind.lower(), name))
    if not drivers:
        return []
    found: List[str] = []
    for text in _attribute_texts(git_path, cwd, env, args):
        if text == UNREADABLE_ATTRIBUTES:
            if text not in found:
                found.append(text)
            continue
        for kind, name in _ATTRIBUTE_RE.findall(text):
            if (kind, name) in drivers and name not in found:
                found.append(name)
    return found


class GitResult(object):
    """What one git call returned: its exit code and its two output streams."""

    __slots__ = ("code", "stdout", "stderr")

    def __init__(self, code: int, stdout: str = "", stderr: str = ""):
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self) -> bool:
        return self.code == 0

    def out(self) -> str:
        """The standard output with trailing blank space removed."""
        return self.stdout.strip()

    def __repr__(self) -> str:
        return "GitResult(code=%r)" % (self.code,)


class GitRunner(object):
    """Runs git with prompting turned off and a time limit on every call."""

    def __init__(self, git_path: str = "git"):
        self.git_path = git_path

    def environment(self) -> dict:
        env = dict(os.environ)
        # Never let git open a terminal prompt or a password helper.
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = ""
        env["SSH_ASKPASS"] = ""
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        # Fixed messages, so anything this library matches on stays stable.
        env["LC_ALL"] = "C"
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        return env

    def run(
        self,
        args: Sequence[str],
        cwd: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        input: Optional[str] = None,
    ) -> GitResult:
        """Run one git command and return its result. This never raises.

        Every command runs with hooks, the file monitor and signing switched
        off, and one that could run a filter or merge program the base's
        attribute files name is not run at all (`hook_free`,
        `executable_drivers`).
        """
        if needs_a_driver_check(args) and executable_drivers(
            cwd, self.git_path, self.environment(), args
        ):
            return GitResult(DRIVER_CODE, "", CODE_EXECUTABLE_DRIVER)
        command = [self.git_path] + hook_free(args)
        try:
            finished = subprocess.run(
                command,
                cwd=cwd,
                env=self.environment(),
                input=input.encode("utf-8") if input is not None else None,
                stdin=None if input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return GitResult(TIMEOUT_CODE, "", "timeout")
        except (OSError, ValueError):
            return GitResult(MISSING_CODE, "", "git-missing")
        return GitResult(
            finished.returncode,
            finished.stdout.decode("utf-8", "replace"),
            finished.stderr.decode("utf-8", "replace"),
        )

    def check(
        self,
        args: Sequence[str],
        cwd: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        input: Optional[str] = None,
    ) -> GitResult:
        """Run one git command and raise a fixed-code error when it fails."""
        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if result.ok:
            return result
        if result.code == TIMEOUT_CODE:
            raise GitError("git-timeout", code="git-timeout", result=result)
        if result.code == MISSING_CODE:
            raise GitError("git-missing", code="git-missing", result=result)
        if result.code == DRIVER_CODE:
            raise GitError(
                CODE_EXECUTABLE_DRIVER, code=CODE_EXECUTABLE_DRIVER, result=result
            )
        raise GitError("git-failed", code="git-failed", result=result)


class DeadlineRunner(object):
    """Another runner with a moment past which no git call may still be running.

    The session start hook has fifteen seconds for everything it does, and git
    calls are the only part of it that can wait on a network or a lock. Each
    call is given whatever is left of the budget rather than its own full time
    limit, so a run that is already late cannot spend twenty more seconds
    finding that out. A call made after the moment has passed is not made at
    all and comes back as a call that timed out, which every caller already
    knows how to handle.
    """

    def __init__(self, inner: "GitRunner", deadline: float):
        self.inner = inner
        self.deadline = deadline

    def remaining(self) -> float:
        return self.deadline - time.monotonic()

    def _budget(self, timeout: int) -> Optional[float]:
        left = self.remaining()
        if left <= 0:
            return None
        return min(float(timeout), left)

    def run(self, args, cwd=None, timeout=DEFAULT_TIMEOUT_SECONDS, input=None):
        budget = self._budget(timeout)
        if budget is None:
            return GitResult(TIMEOUT_CODE, "", "deadline")
        return self.inner.run(args, cwd=cwd, timeout=budget, input=input)

    def check(self, args, cwd=None, timeout=DEFAULT_TIMEOUT_SECONDS, input=None):
        budget = self._budget(timeout)
        if budget is None:
            raise GitError(
                "git-timeout", code="git-timeout", result=GitResult(TIMEOUT_CODE, "", "deadline")
            )
        return self.inner.check(args, cwd=cwd, timeout=budget, input=input)


# --- Reading names out of what git prints -------------------------------------
#
# Git writes a name holding an accent, a space, a quotation mark, or anything
# else unusual inside quotation marks with escapes in its ordinary output, so a
# name read from that output is not the name on the disk. Every call that reads
# names asks for records ending in a NUL instead, where names come out exactly
# as they are, and reads them with the two functions below. A patch has no such
# form, so its headers are read back with `unquote_path`.


def nul_fields(stdout: str) -> List[str]:
    """Every field of output git wrote with `-z`, in order, empty ones left out."""
    return [field for field in stdout.split("\0") if field]


def status_entries(stdout: str) -> Optional[List[Tuple[str, List[str]]]]:
    """Each entry of `git status --porcelain -z`, as (its two letters, its paths).

    A rename or a copy names two paths, the new one first and then the one it
    came from, and with `-z` the second is a field of its own rather than the
    far side of an arrow. Output that does not have this shape gives back
    nothing at all, which every caller treats as work it may not write over.
    """
    fields = stdout.split("\0")
    entries: List[Tuple[str, List[str]]] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        if len(field) < 4 or field[2] != " ":
            return None
        letters, named = field[:2], [field[3:]]
        if "R" in letters or "C" in letters:
            if index >= len(fields) or not fields[index]:
                return None
            named.append(fields[index])
            index += 1
        entries.append((letters, named))
    return entries


_C_ESCAPES = {
    "a": 7,
    "b": 8,
    "t": 9,
    "n": 10,
    "v": 11,
    "f": 12,
    "r": 13,
    '"': 34,
    "\\": 92,
}


def unquote_path(text: str) -> str:
    """One name as git printed it, back to the name it really is.

    A name git left alone comes back as it is. A quoted one has its quotation
    marks taken off and every escape turned back into the bytes it stands for,
    which is how an accent arrives. An escape this cannot read leaves the text
    as git printed it, so nothing is guessed.
    """
    if len(text) < 2 or not (text.startswith('"') and text.endswith('"')):
        return text
    body = text[1:-1]
    out = bytearray()
    index = 0
    while index < len(body):
        char = body[index]
        if char != "\\":
            out.extend(char.encode("utf-8"))
            index += 1
            continue
        after = body[index + 1 : index + 2]
        if after in _C_ESCAPES:
            out.append(_C_ESCAPES[after])
            index += 2
            continue
        octal = body[index + 1 : index + 4]
        if len(octal) == 3 and all(digit in "01234567" for digit in octal):
            out.append(int(octal, 8) & 0xFF)
            index += 4
            continue
        return text
    return out.decode("utf-8", "replace")


def with_deadline(runner: Optional["GitRunner"], seconds: float) -> "DeadlineRunner":
    """Bound a runner to a stretch of time starting now."""
    return DeadlineRunner(runner_or_default(runner), time.monotonic() + float(seconds))


_DEFAULT_RUNNER = None


def default_runner() -> GitRunner:
    """The runner every module uses when the caller hands in none of its own."""
    global _DEFAULT_RUNNER
    if _DEFAULT_RUNNER is None:
        _DEFAULT_RUNNER = GitRunner()
    return _DEFAULT_RUNNER


def runner_or_default(runner: Optional[GitRunner]) -> GitRunner:
    return runner if runner is not None else default_runner()
