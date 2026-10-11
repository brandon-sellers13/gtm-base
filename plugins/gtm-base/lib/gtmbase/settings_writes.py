"""Whether a shell line writes one of the files that can switch the checks off.

Step 10 of the Release A live check (2026-10-10). Asked to add a permission to
the person's own settings, a session read the settings file with a one-line
Python command, copied it to a backup, and rewrote it with a Python script run
through the shell. Nothing was asked. The write check asks about these files,
but it runs on the file tools, and the command check only read lines that run
git or GitHub or name GTM Base's records folder. The width of every other tool
was the hole, which is the 2026-09-20 lesson again.

So the command check now asks the write check's question, with the write
check's sentence, about any shell line that writes one of the same files: the
person's own settings and the plugin registry under the assistant folder in
their home folder, anything else the client keeps its plugins in, and a linked
folder's settings. It is a question rather than a refusal for the reason the
write check gives: these files hold everything else the person has set up.

What counts as a write, part by part:

- an output redirection aimed at one of the files;
- `cp` with one of the files as where it copies to;
- `sed` with its in-place option, and `find` asked to delete or run something;
- any other program handed one of the files, or one of the assistant folders
  that hold them: `mv`, `rm`, `tee`, `ln`, `install`, `rsync`, `dd`, an
  interpreter, an editor, and every program this does not know. A program
  that only reads (`cat`, `grep`, `jq`, and the others below) is not asked
  about;
- any line that names one of the files and hands text to another program to
  run (`xargs`, `eval`, `source`, a shell reading what it is piped).

A file is recognised when the line names it, by whole path, from the home
folder, through the home folder's variable, or from the folder the line is in
by then. A name this cannot work out where it leads, because a variable other
than the home folder's builds it, a pattern stands for part of it, or the line
moved to a folder this could not follow, counts as one of the files. So does a
file name of theirs written on its own in a line that also names the assistant
folder, which is how a script builds the path in pieces.

What it cannot see, and the changelog says so: a script in a file (`python3
fix.py`) that writes the settings without the line naming them; a path built
somewhere this cannot read, such as a variable set in an earlier command or a
file of paths; a write to a folder above the assistant folder as a whole, such
as copying a saved home folder over the real one; and a program the line runs
that changes the settings through its own commands. The question also comes up
for some lines that only read, when the program reading is one this does not
know, such as an interpreter.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shlex
from typing import List, Optional, Sequence, Tuple

from . import trust_surface, write_hook

# The file names that can be one of the asked-about files, and the folder name
# that holds them. Folded before they are compared.
GUARDED_NAMES = (
    "settings.json",
    "settings.local.json",
    "installed_plugins.json",
    "known_marketplaces.json",
)
ASSISTANT_DIR = ".claude"

# Programs that read what they are handed and write nothing back to it.
READ_ONLY = (
    "cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg",
    "wc", "ls", "stat", "file", "diff", "cmp", "jq", "test", "[", "shasum",
    "sha1sum", "sha256sum", "md5", "md5sum", "echo", "printf", "realpath",
    "readlink", "dirname", "basename", "du", "pwd", "true", "false",
)
# Programs that run text they are handed or read from what is piped to them.
RUNS_WHAT_IT_IS_HANDED = ("xargs", "eval", "source", ".", "parallel")
SHELLS = ("sh", "bash", "zsh", "dash", "ksh", "fish")
FOLDER_WORDS = ("cd", "pushd")
_FIND_WRITES = (
    "-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0",
    "-fprintf", "-fls",
)

# A redirection, once the line is split at the marks the shell splits at.
# One holding ">" writes, and "<>" opens the file to write as well as read.
_OPERATOR = re.compile(r"^[<>&|]*[<>][<>&|-]*$")
# What separates one path out of a longer piece of text, such as a script.
_RUN_SPLIT = re.compile(r"[\s()\[\]{},;:=<>|&+'\"]+")
# What makes a path one this cannot work out at all.
_UNRESOLVABLE = re.compile(r"[$`{}]")
# What makes a path a pattern the shell fills in.
_GLOB = re.compile(r"[*?\[]")
_HOME_VARIABLE = re.compile(r"^(?:\$HOME|\$\{HOME\})(?=/|$)")
# What stands where a command written inside another one was: something no
# path can be worked out from (security review of 0.3.6).
_SUBSTITUTED = "$_"


def _folded(text: str) -> str:
    return trust_surface.normalize_component(text or "")


def _could_name_one(text: str) -> bool:
    """The cheap way out, which almost every command takes."""
    folded = _folded(text)
    return ASSISTANT_DIR in folded or any(name in folded for name in GUARDED_NAMES)


def _worth_reading(text: str) -> bool:
    """Whether a piece of text could name one of the files at all.

    Quotes and backslashes are taken out first, because `.cl""aude` is the
    folder's name to the shell. A pattern the shell fills in is worth reading
    too, because `~/.cl*/sett*.json` names the file without spelling it.
    """
    from . import gate

    plain = gate.strip_quoting(text or "")
    return _could_name_one(plain) or bool(_GLOB.search(plain))


class _Where(object):
    """The folder each part of the line runs in, as far as it can be followed."""

    __slots__ = ("path",)

    def __init__(self, path: Optional[str]):
        self.path = path

    def follow(self, arguments: Sequence[str]) -> None:
        if not arguments:
            self.path = os.path.expanduser("~")
            return
        if len(arguments) > 1 or arguments[0] == "-":
            self.path = None
            return
        target = _expanded(arguments[0])
        if target is None or _GLOB.search(target):
            self.path = None
        elif os.path.isabs(target):
            self.path = os.path.normpath(target)
        elif self.path is not None:
            self.path = os.path.normpath(os.path.join(self.path, target))


def _expanded(text: str) -> Optional[str]:
    """A path with the home folder written out, or None when it cannot be."""
    text = _HOME_VARIABLE.sub(lambda _m: os.path.expanduser("~"), text)
    if text.startswith("~"):
        text = os.path.expanduser(text)
        if text.startswith("~"):
            return None
    if _UNRESOLVABLE.search(text):
        return None
    return text


def _linked_folders() -> List[str]:
    from . import machine

    found = []
    try:
        raw = machine.load_machine_state_raw()
        for entry in list(getattr(raw, "joined", None) or []):
            linked = entry.get("content_root") if isinstance(entry, dict) else None
            if isinstance(linked, str) and linked:
                found.append(linked)
    except Exception:
        pass
    return found


def _guarded_folders() -> List[str]:
    """The assistant folders that hold the files, as folders of their own."""
    return [os.path.join(os.path.expanduser("~"), ASSISTANT_DIR)] + [
        os.path.join(linked, ASSISTANT_DIR) for linked in _linked_folders()
    ]


def _guarded_paths() -> List[str]:
    """Every file and folder a pattern is compared with, by whole path."""
    found = list(write_hook.client_settings_files())
    found.append(write_hook.client_plugins_dir())
    for folder in _guarded_folders():
        found.append(folder)
        for name in write_hook.LINKED_FOLDER_SETTINGS_FILES:
            found.append(os.path.join(folder, name))
    return found


def _lands_on_one(path: str) -> bool:
    """Whether a whole path is one of the files, or a folder holding them."""
    try:
        real = os.path.realpath(path)
    except Exception:
        real = path
    if write_hook.asks_about(path, real):
        return True
    for folder in _guarded_folders():
        for side in (path, real):
            for place in (folder, os.path.realpath(folder)):
                if _folded(side.rstrip(os.sep)) == _folded(place.rstrip(os.sep)):
                    return True
    return False


def _pattern_lands_on_one(pattern: str) -> bool:
    """Whether a pattern the shell fills in could fill in one of the files."""
    wanted = _folded(pattern.rstrip(os.sep))
    for path in _guarded_paths():
        for side in (path, os.path.realpath(path)):
            if fnmatch.fnmatchcase(_folded(side.rstrip(os.sep)), wanted):
                return True
    return False


def _inside_a_guarded_folder(path: Optional[str]) -> bool:
    """Whether a folder the line runs in is the assistant folder in the home
    folder, anything inside it, or a linked folder's assistant folder itself.

    Every word of a command run there is looked at, whatever it is called,
    because `rm -rf plugins` there names the plugins folder without saying so
    (correctness review of 0.3.6). The working folders the desktop app makes
    inside a linked folder's assistant folder are not on the list: the person
    works in those all day, and the settings in them are named in full.
    """
    if not path:
        return False
    home_folder = os.path.join(os.path.expanduser("~"), ASSISTANT_DIR)
    folded = _folded(path.rstrip(os.sep))
    for place in (home_folder, os.path.realpath(home_folder)):
        wanted = _folded(place.rstrip(os.sep))
        if folded == wanted or folded.startswith(wanted + os.sep):
            return True
    for linked in _linked_folders():
        for place in (linked, os.path.realpath(linked)):
            if folded == _folded(os.path.join(place, ASSISTANT_DIR)):
                return True
    return False


def _names_one(text: str, where: _Where, pieces_name_the_folder: bool) -> bool:
    """Whether one word of a command, or a path inside it, names one of the files."""
    everything = _inside_a_guarded_folder(where.path)
    if not everything and not _worth_reading(text):
        return False
    candidates = [text] + [run for run in _RUN_SPLIT.split(text) if run]
    for candidate in candidates:
        folded = _folded(candidate)
        could = ASSISTANT_DIR in folded or any(name in folded for name in GUARDED_NAMES)
        if everything and not candidate.startswith("-"):
            could = True
        if not could and not _GLOB.search(candidate):
            continue
        if _folded(candidate).startswith("/" + ASSISTANT_DIR):
            # No real folder sits there. It is what a script's own words
            # leave of a path it joins onto the home folder's value, as in
            # `os.environ['HOME'] + '/.claude/settings.json'`.
            return True
        bare = "/" not in candidate
        if bare and folded in GUARDED_NAMES and pieces_name_the_folder:
            # A script building the path in pieces: the folder in one piece
            # and the file in another. Where they lead cannot be read here.
            return True
        expanded = _expanded(candidate)
        if expanded is None:
            if could:
                return True
            continue
        if not os.path.isabs(expanded):
            if where.path is None:
                if could:
                    return True
                continue
            expanded = os.path.join(where.path, expanded)
        expanded = os.path.normpath(expanded)
        if _GLOB.search(expanded):
            if _pattern_lands_on_one(expanded):
                return True
            continue
        if _lands_on_one(expanded):
            return True
    return False


def _pieces_name_the_folder(segment: str) -> bool:
    return any(
        _folded(run).rstrip("/") == ASSISTANT_DIR
        or _folded(run).rstrip("/").endswith("/" + ASSISTANT_DIR)
        for run in _RUN_SPLIT.split(segment)
        if run
    )


def _strip_prefixes(tokens: List[str]) -> List[str]:
    from . import gate

    rest, _assignments = gate._strip_prefixes(tokens)
    return rest


def _segments(command: str) -> List[str]:
    from . import gate

    return gate.split_segments(command)


def _cut_out_commands(text: str) -> Tuple[List[str], str]:
    """Every command written inside another one, and what is left around it.

    The same two forms the command check reads, with a mark left where each
    one was. Cutting them out without a mark turned `$(echo ~/.claude)/x`
    into `/x`, a path that led nowhere near the folder (security review of
    0.3.6).
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
            rest.append(_SUBSTITUTED)
            index = scan
            continue
        if character == "`":
            end = text.find("`", index + 1)
            if end == -1:
                bodies.append(text[index + 1 :])
                rest.append(_SUBSTITUTED)
                break
            bodies.append(text[index + 1 : end])
            rest.append(_SUBSTITUTED)
            index = end + 1
            continue
        rest.append(character)
        index += 1
    return bodies, "".join(rest)


def writes_a_settings_file(command: str, cwd: Optional[str]) -> bool:
    """Whether this shell line writes a file that can switch the checks off."""
    if not command:
        return False
    if not _worth_reading(command) and not _inside_a_guarded_folder(cwd):
        return False
    return _line_writes(command, _Where(cwd), 0)


def _line_writes(command: str, where: _Where, depth: int) -> bool:
    """Read one line part by part. Every part that names a file is weighed.

    Two things are only known by the end of the line: whether some part named
    one of the files, and whether some part writes where this cannot see, by
    handing text to another program, by feeding an interpreter a script typed
    into the line, or by writing to a place a variable decides. Either of the
    second kind on a line that also names one of the files is asked about.
    """
    if depth > 3:
        return True
    unseen_write = False
    named_anywhere = False
    body_ends = None
    body_is_data = False
    for segment in _segments(command):
        if body_ends is not None:
            # A line of text typed in for a program to read. Text a program
            # that only reads is handed is data, as in a note written with
            # `cat > notes.md <<EOF`, and is never a command. Text an
            # interpreter is handed is its script: what it names counts, and
            # the interpreter has already been counted as writing unseen.
            if segment.strip() == body_ends:
                body_ends = None
                continue
            if not body_is_data and _names_one(segment, where, True):
                named_anywhere = True
            continue
        bodies, remainder = _cut_out_commands(segment)
        for body in bodies:
            if _line_writes(body, _Where(where.path), depth + 1):
                return True
            if _worth_reading(body) and _could_name_one(body):
                named_anywhere = True
        pieces = _pieces_name_the_folder(remainder)
        tokens = _tokens(remainder)
        if tokens is None:
            if _worth_reading(remainder):
                return True
            continue
        targets: List[str] = []
        read_from: List[str] = []
        words: List[str] = []
        fed_a_script = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if _OPERATOR.match(token):
                following = tokens[index + 1] if index + 1 < len(tokens) else ""
                # `2>` is split into `2` and `>`; the number says which
                # stream, and is no word of the command (security review).
                if words and words[-1].isdigit() and index > 0 and tokens[index - 1] == words[-1]:
                    words.pop()
                index += 2
                if token in (">&", "<&") and (following.isdigit() or following == "-"):
                    continue
                if token.startswith("<<") and token != "<<<":
                    # A script typed into the line for the program to read.
                    fed_a_script = True
                    body_ends = following
                    body_is_data = False
                    continue
                if ">" in token:
                    targets.append(following)
                else:
                    read_from.append(following)
                continue
            if token.strip("()"):
                # A bracket that opens or closes a group of commands is not
                # a word of the command inside it.
                words.append(token)
            index += 1
        for target in targets:
            if _names_one(target, where, pieces):
                return True
            if _UNRESOLVABLE.search(target):
                unseen_write = True
        if any(_names_one(word, where, pieces) for word in read_from):
            named_anywhere = True
        # Named before the words in front of the program are taken off, so a
        # path kept in a setting (`p=~/.claude/settings.json`) still counts.
        named = [word for word in words if _names_one(word, where, pieces)]
        if named:
            named_anywhere = True
        words = _strip_prefixes(words)
        if not words:
            continue
        program = os.path.basename(words[0])
        arguments = words[1:]
        body_is_data = program in READ_ONLY
        if program in FOLDER_WORDS:
            where.follow(arguments)
            continue
        if program in SHELLS:
            script = _shell_script(arguments)
            if script is not None:
                if _line_writes(script, _Where(where.path), depth + 1):
                    return True
                continue
            unseen_write = True
        if program in RUNS_WHAT_IT_IS_HANDED:
            unseen_write = True
        if program not in READ_ONLY:
            if fed_a_script:
                unseen_write = True
            if any(_UNRESOLVABLE.search(argument) for argument in arguments):
                unseen_write = True
        if not named:
            continue
        if _a_write(program, arguments, where, pieces):
            return True
    return unseen_write and named_anywhere


def _tokens(text: str) -> Optional[List[str]]:
    """The words of one part, split at spaces and at the shell's own marks.

    A redirection written with no space before it (`echo x>file`) is still
    split off from the word it follows, which a split at spaces alone missed.
    """
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def _shell_script(arguments: Sequence[str]) -> Optional[str]:
    for position, token in enumerate(arguments):
        if re.match(r"^-[A-Za-z]*c$", token) and position + 1 < len(arguments):
            return arguments[position + 1]
    return None


def _a_write(program, arguments, where, pieces) -> bool:
    """Whether a part that names one of the files writes to it."""
    if program == "sed":
        return any(
            token.startswith("--in-place")
            or (token.startswith("-") and not token.startswith("--") and "i" in token[1:])
            for token in arguments
        )
    if program == "find":
        return any(token in _FIND_WRITES for token in arguments)
    if program == "cp":
        if any(
            token == "-t" or token.startswith("--target-directory")
            for token in arguments
        ):
            return True
        plain = [token for token in arguments if not token.startswith("-")]
        return bool(plain) and _names_one(plain[-1], where, pieces)
    if program in READ_ONLY:
        return False
    return True
