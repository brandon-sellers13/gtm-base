"""Undo a command that switched GTM Base's own checks off, right after it ran.

From 0.3.6 to 0.3.10 the check on commands read each shell line before it ran
and asked about any line that could write one of the files that decide whether
GTM Base runs. Each release fixed the lines it was shown, and replaying the
person's own commands still gave fifteen to twenty questions in four hundred,
most of them about lines that only read. Proving from the words of a shell
line that it cannot write a file is a problem that does not end.

So 0.4.0 looks at what a command did instead of what it says. Before each
command runs, the check on commands keeps a copy of every file that decides
whether GTM Base's checks run (`snapshot`). After it runs, this module reads
the same files again and asks one question of each: did GTM Base's checks get
weaker (`check`)? If they did, it puts back only the part that keeps them
running, says what it undid to the person and to the assistant, and leaves
every other change the command made where it is. A change to a theme, a
permission another session added, or an update of GTM Base itself is not a
weakening and is never touched.

What counts as weaker, file by file:

- in a settings file, GTM Base turned off in `enabledPlugins`, every hook
  turned off with `disableAllHooks` or `allowManagedHooksOnly`, or a change to
  the environment settings that decide which program runs the checks
  (`PATH`, anything starting with `PYTHON`, `DYLD_` or `GTM_BASE`, and
  `CLAUDE_PLUGIN_ROOT`), or GTM Base's marketplace taken out of
  `extraKnownMarketplaces` or pointed somewhere else;
- in the list of installed plugins, GTM Base taken off it, or pointed at code
  outside the folder Claude Code keeps installed plugins in. A new version, a
  new commit or a new folder inside that one is an update, not a weakening;
- in the list of known marketplaces, GTM Base's marketplace taken off it or
  pointed at another source;
- any of these files deleted, or left so that it no longer reads as settings,
  when it held something that kept the checks running. Then the whole file
  is put back, because there is nothing left in it to keep.

What it cannot do, and the changelog says so: the change has already happened
when this runs, so for the moment between the command and this check the
checks are weaker. Claude Code's documentation does not say whether
`disableAllHooks` takes effect at once, and if it does, this check may not run
for the command that set it. A write that comes after this has run is not
seen: a command started in the background, a `nohup ... &`, or a job left for
`at` or `cron`. A command the person cancels is not checked. And this guards
against an assistant that switches the checks off in the course of ordinary
work, not against a command written to defeat GTM Base on purpose: anything
that runs as the person can also delete the copy kept here, or edit the
plugin's own code (adversarial review of 0.4.0, findings 1 and 8).

A change the person makes themselves, with `/plugin` or in their own editor,
happens outside any command the assistant runs and is not undone, unless they
make it while one of the assistant's commands is still running or waiting for
their yes, because the copy is kept before that (finding 9).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import fsutil, paths, write_hook

# How GTM Base is known to Claude Code, in the settings and in both lists.
PLUGIN_KEY = "gtm-base@gtm-base"
MARKETPLACE_KEY = "gtm-base"

# The three kinds of file, each read for its own part.
KIND_SETTINGS = "settings"
KIND_INSTALLED = "installed"
KIND_MARKETPLACES = "marketplaces"

# The environment settings that decide which program runs the checks and
# where it finds its code. Claude Code hands its environment, including the
# settings' `env`, to every hook it starts.
# `HOME` and `CLAUDE_CONFIG_DIR` move the folder every hook reads its own
# records and settings from (adversarial review of 0.4.0, finding 5).
_HOOK_ENVIRONMENT = re.compile(
    r"^(?:PATH|HOME|CLAUDE_CONFIG_DIR|CLAUDE_PLUGIN_ROOT|PYTHON.*|DYLD_.*|GTM_BASE.*)$"
)

# Where the copies are kept, inside the records folder no command may touch,
# and how long a copy whose command never reported back is kept.
GUARD_DIR = "guard"
_STALE_SECONDS = 24 * 60 * 60
_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")

# Hook events this module answers.
EVENT_AFTER = "PostToolUse"
EVENT_AFTER_FAILURE = "PostToolUseFailure"

_MISSING = object()


# --- Which files ------------------------------------------------------------


def _config_dir() -> str:
    """The folder Claude Code keeps the person's own settings and plugins in:
    the one `CLAUDE_CONFIG_DIR` names, or the assistant folder in the home
    folder."""
    told = os.environ.get("CLAUDE_CONFIG_DIR")
    if told:
        return os.path.abspath(os.path.expanduser(told))
    return os.path.join(os.path.expanduser("~"), write_hook.ASSISTANT_DIR_NAME)


def _own_install_folder() -> str:
    """Where Claude Code installs GTM Base, every version in a folder of its own."""
    return os.path.join(_config_dir(), "plugins", "cache", MARKETPLACE_KEY, PLUGIN_KEY.split("@")[0])


def _assistant_settings(folder: str) -> List[str]:
    return [
        os.path.join(folder, write_hook.ASSISTANT_DIR_NAME, name)
        for name in write_hook.LINKED_FOLDER_SETTINGS_FILES
    ]


def guarded_files(cwd: Optional[str], project_dir: Optional[str]) -> List[Tuple[str, str]]:
    """Every file that decides whether GTM Base's checks run here, with its kind.

    The person's own settings and both plugin lists, the settings of every
    folder linked to a base, and the settings of the project the session is
    open in and of the folder the command runs in, because Claude Code reads
    a project's own settings too and they can turn a plugin off there.
    """
    home = _config_dir()
    found = [
        (os.path.join(home, "settings.json"), KIND_SETTINGS),
        (os.path.join(home, "settings.local.json"), KIND_SETTINGS),
        (os.path.join(home, "plugins", "installed_plugins.json"), KIND_INSTALLED),
        (os.path.join(home, "plugins", "known_marketplaces.json"), KIND_MARKETPLACES),
    ]
    folders: List[str] = []
    try:
        from . import machine

        raw = machine.load_machine_state_raw()
        for entry in list(getattr(raw, "joined", None) or []):
            linked = entry.get("content_root") if isinstance(entry, dict) else None
            if isinstance(linked, str) and linked:
                folders.append(linked)
    except Exception:
        pass
    for folder in (project_dir, cwd):
        if isinstance(folder, str) and folder:
            folders.append(folder)
    seen = {os.path.realpath(path) for path, _kind in found}
    for folder in folders:
        for path in _assistant_settings(folder):
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                found.append((path, KIND_SETTINGS))
    return found


# --- Reading one file -------------------------------------------------------


def _read(path: str) -> Tuple[bool, Optional[str]]:
    """Whether a file is there, and its text when it reads as text.

    A link is followed, because people keep their settings in a folder of
    their own and link them in, and Claude Code reads through the link.
    """
    real = os.path.realpath(path)
    if not os.path.isfile(real):
        return os.path.lexists(path), None
    try:
        with open(real, encoding="utf-8", newline="") as stream:
            return True, stream.read()
    except (OSError, UnicodeDecodeError):
        return True, None


def _mode(path: str) -> Optional[int]:
    try:
        return os.stat(os.path.realpath(path)).st_mode & 0o777
    except OSError:
        return None


def _parsed(text: Optional[str]) -> Any:
    if text is None:
        return _MISSING
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        value = json.loads(text)
    except ValueError:
        return _MISSING
    return value if isinstance(value, dict) else _MISSING


# --- What counts as weaker --------------------------------------------------


class Finding(object):
    """One way a command weakened the checks, and how to put it back."""

    __slots__ = ("what", "repair")

    def __init__(self, what: str, repair: Callable[[Dict[str, Any]], None]):
        self.what = what
        self.repair = repair


def _section(document: Any, key: str) -> Dict[str, Any]:
    value = document.get(key) if isinstance(document, dict) else None
    return value if isinstance(value, dict) else {}


def _put_back(key: str, inner: Optional[str], value: Any) -> Callable[[Dict[str, Any]], None]:
    """A repair that puts one value back where it was, or takes it out again
    when it was not there before."""

    def repair(document: Dict[str, Any]) -> None:
        target = document
        if inner is not None:
            if not isinstance(document.get(key), dict):
                document[key] = {}
            target = document[key]
            name = inner
        else:
            name = key
        if value is _MISSING:
            target.pop(name, None)
        else:
            target[name] = value

    return repair


def _truthy(value: Any) -> bool:
    """Whether Claude Code, which is written in JavaScript, reads a value as
    switched on. A list or an object is, even an empty one, and so is any
    string but an empty one, `"false"` included."""
    if isinstance(value, (list, dict)):
        return True
    return bool(value)


def _enabled_rank(value: Any) -> int:
    if value is True:
        return 2
    if value is _MISSING:
        return 1
    return 0


def _settings_findings(before: Dict[str, Any], after: Dict[str, Any]) -> List[Finding]:
    found: List[Finding] = []
    was = _section(before, "enabledPlugins").get(PLUGIN_KEY, _MISSING)
    now = _section(after, "enabledPlugins").get(PLUGIN_KEY, _MISSING)
    if _enabled_rank(now) < _enabled_rank(was):
        found.append(Finding("turned GTM Base off", _put_back("enabledPlugins", PLUGIN_KEY, was)))
    for key, what in (
        ("disableAllHooks", "turned every hook off"),
        ("allowManagedHooksOnly", "turned off every hook your organisation does not manage"),
    ):
        was_on = _truthy(before.get(key, False))
        if _truthy(after.get(key, False)) and not was_on:
            found.append(Finding(what, _put_back(key, None, before.get(key, _MISSING))))
    was_env = _section(before, "env")
    now_env = _section(after, "env")
    for key in sorted(set(was_env) | set(now_env)):
        if _HOOK_ENVIRONMENT.match(key) and was_env.get(key, _MISSING) != now_env.get(key, _MISSING):
            found.append(
                Finding(
                    "changed %s in the environment settings, which decides how GTM Base's checks run" % key,
                    _put_back("env", key, was_env.get(key, _MISSING)),
                )
            )
    was_source = _section(before, "extraKnownMarketplaces").get(MARKETPLACE_KEY, _MISSING)
    now_source = _section(after, "extraKnownMarketplaces").get(MARKETPLACE_KEY, _MISSING)
    if was_source is not _MISSING and now_source != was_source:
        found.append(
            Finding(
                "took away or changed where GTM Base is downloaded from",
                _put_back("extraKnownMarketplaces", MARKETPLACE_KEY, was_source),
            )
        )
    return found


def _inside_its_own_install_folder(path: Any) -> bool:
    """Whether an install path is one of GTM Base's own version folders, by
    where it really leads. Anywhere else in the plugins folder, or a link out
    of it, is somebody else's code (adversarial review, finding 3)."""
    if not isinstance(path, str) or not path:
        return False
    folder = os.path.realpath(_own_install_folder())
    return os.path.realpath(os.path.expanduser(path)).startswith(folder + os.sep)


def _entries(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _scopes(value: Any) -> set:
    """Where GTM Base is installed for: each scope, with its project folder."""
    return {(entry.get("scope"), entry.get("projectPath")) for entry in _entries(value)}


def _installed_findings(before: Dict[str, Any], after: Dict[str, Any]) -> List[Finding]:
    was = _section(before, "plugins").get(PLUGIN_KEY, _MISSING)
    now = _section(after, "plugins").get(PLUGIN_KEY, _MISSING)
    if was is _MISSING or not was:
        return []
    repair = _put_back("plugins", PLUGIN_KEY, was)
    if now is _MISSING or not now or not _entries(now):
        return [Finding("took GTM Base off the list of installed plugins", repair)]
    if not _scopes(was) <= _scopes(now):
        # An update keeps every scope it was installed for; swapping the
        # person's own install for one in a project folder that is not this
        # one takes it away here (adversarial review, finding 4).
        return [Finding("changed where GTM Base is installed for", repair)]
    if all(_inside_its_own_install_folder(entry.get("installPath")) for entry in _entries(was)) and not all(
        _inside_its_own_install_folder(entry.get("installPath")) for entry in _entries(now)
    ):
        return [Finding("pointed GTM Base at code outside the folder its own versions are installed in", repair)]
    return []


def _marketplace_findings(before: Dict[str, Any], after: Dict[str, Any]) -> List[Finding]:
    was = before.get(MARKETPLACE_KEY, _MISSING)
    now = after.get(MARKETPLACE_KEY, _MISSING)
    if not isinstance(was, dict):
        return []
    repair = _put_back(MARKETPLACE_KEY, None, was)
    if not isinstance(now, dict):
        return [Finding("took GTM Base's marketplace off the list of known marketplaces", repair)]
    if now.get("source") != was.get("source"):
        return [Finding("changed where GTM Base's marketplace is downloaded from", repair)]
    return []


_JUDGES = {
    KIND_SETTINGS: _settings_findings,
    KIND_INSTALLED: _installed_findings,
    KIND_MARKETPLACES: _marketplace_findings,
}


def findings(
    kind: str, before_exists: bool, before_text: Optional[str], after_text: Optional[str]
) -> Tuple[List[Finding], bool]:
    """How a file got weaker between two readings, and whether the whole file
    has to be put back because the second reading is not settings at all.

    A file that was not there before reads as empty settings, so a new
    settings file that turns GTM Base off is found. One that was there but
    did not read as settings is left alone: there is nothing to compare."""
    before = {} if not before_exists else _parsed(before_text)
    if before is _MISSING:
        return [], False
    after = _parsed(after_text)
    judge = _JUDGES[kind]
    if after is _MISSING:
        return judge(before, {}), True
    return judge(before, after), False


# --- Keeping the copy -------------------------------------------------------


def _guard_dir() -> str:
    return os.path.join(paths.seat_home_path(), GUARD_DIR)


def _command_key(command: Any) -> str:
    return hashlib.sha256(str(command or "").encode("utf-8")).hexdigest()


def _snapshot_path(tool_use_id: str) -> str:
    return os.path.join(_guard_dir(), _SAFE_ID.sub("_", tool_use_id)[:128] + ".json")


def _project_dir(payload: Dict[str, Any]) -> Optional[str]:
    told = os.environ.get("CLAUDE_PROJECT_DIR")
    return told if told else None


def snapshot(payload: Dict[str, Any]) -> None:
    """Keep a copy of every guarded file before one command runs.

    Only a request that names its tool call is kept, because the copy is
    found again by that name after the command. Copies a command never
    reported back on are cleared after a day.
    """
    tool_use_id = payload.get("tool_use_id")
    if not isinstance(tool_use_id, str) or not tool_use_id:
        return
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    files = []
    for path, kind in guarded_files(cwd, _project_dir(payload)):
        exists, text = _read(path)
        files.append({"path": path, "kind": kind, "exists": exists, "text": text, "mode": _mode(path)})
    record = {
        "schema": 1,
        "taken": time.time(),
        "session_id": payload.get("session_id"),
        "command": _command_key(tool_input.get("command")),
        "files": files,
    }
    folder = fsutil.ensure_dir(_guard_dir())
    _clear_stale(folder)
    fsutil.atomic_write_json(_snapshot_path(tool_use_id), record)


def _clear_stale(folder: str) -> None:
    cutoff = time.time() - _STALE_SECONDS
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        path = os.path.join(folder, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            pass


def _load_snapshot(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """The copy kept for this tool call: by its name, or, when the name the
    client sends after a command is not the one it sent before, the newest
    copy from the same session for the same command."""
    tool_use_id = payload.get("tool_use_id")
    if isinstance(tool_use_id, str) and tool_use_id:
        path = _snapshot_path(tool_use_id)
        record = fsutil.read_json(path)
        if isinstance(record, dict):
            return path, record
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    wanted = _command_key(tool_input.get("command"))
    session = payload.get("session_id")
    best: Tuple[float, Optional[str], Optional[Dict[str, Any]]] = (-1.0, None, None)
    try:
        names = os.listdir(_guard_dir())
    except OSError:
        return None, None
    for name in names:
        path = os.path.join(_guard_dir(), name)
        record = fsutil.read_json(path)
        if not isinstance(record, dict):
            continue
        if record.get("session_id") != session or record.get("command") != wanted:
            continue
        taken = record.get("taken")
        if isinstance(taken, (int, float)) and taken > best[0]:
            best = (float(taken), path, record)
    return best[1], best[2]


# --- Putting it back --------------------------------------------------------


def _write_back(path: str, text: str, before_mode: Optional[int]) -> None:
    """Write a guarded file in place, through a link.

    It keeps the mode it has now unless that mode stops the person reading or
    writing it, as `chmod 000` does, and then takes the one it had before
    (adversarial review, finding 2). An empty folder put where the file was
    is taken away first; a folder with anything in it is not, and the person
    is told the file could not be put back."""
    real = os.path.realpath(path)
    if os.path.isdir(real):
        os.rmdir(real)
    mode = _mode(real)
    if mode is None or mode & 0o600 != 0o600:
        mode = before_mode if isinstance(before_mode, int) and before_mode & 0o600 == 0o600 else 0o600
    fsutil.atomic_write_text(real, text, mode=mode)


def _dumped(document: Dict[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _repair_file(
    path: str, kind: str, before_exists: bool, before_text: Optional[str], before_mode: Optional[int] = None
) -> List[str]:
    """Put back what made the checks weaker in one file, reading it again
    first so that a change made in the meantime is kept. Returns what was
    undone."""
    exists, text = _read(path)
    found, whole = findings(kind, before_exists, before_text, text)
    if not found:
        return []
    if whole and isinstance(before_text, str):
        _write_back(path, before_text, before_mode)
        if exists:
            return ["left %s unreadable, so the whole file was put back" % _shown(path)]
        return ["deleted %s, so the whole file was put back" % _shown(path)]
    document = json.loads((text or "{}").lstrip("\ufeff"))
    for finding in found:
        finding.repair(document)
    _write_back(path, _dumped(document), before_mode)
    return ["%s in %s" % (finding.what, _shown(path)) for finding in found]


def _shown(path: str) -> str:
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def check(payload: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Compare the guarded files with the copy kept before this command, and
    put back whatever made the checks weaker. Returns what was undone and
    what was found but could not be undone."""
    path, record = _load_snapshot(payload)
    if record is None:
        return [], []
    undone: List[str] = []
    failed: List[str] = []
    try:
        for entry in record.get("files") or []:
            if not isinstance(entry, dict):
                continue
            where, kind, text = entry.get("path"), entry.get("kind"), entry.get("text")
            existed = bool(entry.get("exists"))
            if not isinstance(where, str) or kind not in _JUDGES:
                continue
            if existed and not isinstance(text, str):
                continue
            try:
                undone.extend(_repair_file(where, kind, existed, text, entry.get("mode")))
            except Exception:
                _exists, now = _read(where)
                if findings(kind, existed, text, now)[0]:
                    failed.append(_shown(where))
    finally:
        if path:
            fsutil.remove(path)
    return undone, failed


# --- What is said -----------------------------------------------------------


def _sentences(undone: Sequence[str], failed: Sequence[str]) -> Tuple[str, str]:
    """What the person reads, and what the assistant is told."""
    parts = []
    if undone:
        parts.append(
            "GTM Base undid part of what the last command did, because it %s."
            % "; ".join(undone)
        )
        if any("whole file" not in item for item in undone):
            parts.append("Everything else the command changed was kept.")
    if failed:
        parts.append(
            "The last command weakened GTM Base's checks in %s, and GTM Base "
            "could not put that back. Open the file and check it." % ", ".join(failed)
        )
    person = " ".join(parts) + (
        " If you meant to make this change, make it yourself with /plugin in "
        "Claude Code or in your own editor. GTM Base only undoes changes made by "
        "commands the assistant runs."
    )
    assistant = " ".join(parts) + (
        " Do not try to make this change another way. If the person wants GTM "
        "Base switched off, tell them to do it themselves with /plugin or in "
        "their own editor."
    )
    return person, assistant


def verdict(event: str, undone: Sequence[str], failed: Sequence[str]) -> Optional[str]:
    """The answer to print, or nothing when the checks were left as they were."""
    if not undone and not failed:
        return None
    person, assistant = _sentences(undone, failed)
    answer: Dict[str, Any] = {
        "systemMessage": person,
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": assistant},
    }
    if event == EVENT_AFTER:
        answer["decision"] = "block"
        answer["reason"] = assistant
    return json.dumps(answer)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Read one after-the-command request and undo what weakened the checks."""
    del argv
    try:
        payload = json.loads(sys.stdin.read() or "null")
    except (OSError, UnicodeDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    event = payload.get("hook_event_name")
    if event not in (EVENT_AFTER, EVENT_AFTER_FAILURE):
        event = EVENT_AFTER
    undone, failed = check(payload)
    answer = verdict(event, undone, failed)
    if answer:
        sys.stdout.write(answer + "\n")
    return 0
