"""Putting the safeguard git itself runs in place, without ever tracking it.

The check inside the AI client only sees commands the client runs. A send from
a plain terminal never passes it, so the same check is installed as the hook
git runs before a send. It is written into the folder git reports, never into
the shared files, because a safeguard that everyone can save changes to is a
way to run code on every teammate's laptop.

An existing hook is moved aside and still runs after ours. When the folder
cannot be written, nothing is written and a fixed code is recorded, so the
person can be told the terminal layer is not in place.

The hook only ever exists inside a base. `install` is called from the joined
branch of the work done at the start of a session and from the join skill and
from nowhere else, so the folder the hook reads is always one the gate reads.
"""

from __future__ import annotations

import os
import shlex
from typing import Optional, Tuple

from . import state
from .gitcmd import GitRunner, runner_or_default

# The line that says a hook is ours. Anything without it belongs to someone
# else and is moved aside rather than overwritten.
MARKER_LINE = "# gtm-base pre-push gate"

HOOK_NAME = "pre-push"
CHAINED_NAME = "pre-push.local"
HOOK_MODE = 0o755
# The folder the safeguard goes in, when it has to be made.
DIR_MODE = 0o700

# What the outcome can be. Every one of them is a code seat state accepts.
CODE_OK = "ok"
CODE_CHAINED = "hook-chained"
CODE_RENAMED = "hook-renamed"
CODE_NOT_WRITABLE = "hooks-path-not-writable"
CODE_UNMOVABLE = "existing-hook-unmovable"
CODE_TRACKED = "hooks-dir-tracked"
CODE_NOT_INSTALLED = "hook-not-installed"

MISSING_PYTHON_SENTENCE = (
    "GTM Base could not run its safety check because python3 is missing; "
    "install the developer tools and try again"
)


def hook_text(plugin_root: str, hooks_dir: str) -> str:
    """The safeguard git runs, as a POSIX shell script."""
    script = os.path.join(plugin_root, "scripts", "push_gate.py")
    chained = os.path.join(hooks_dir, CHAINED_NAME)
    return """#!/bin/sh
{marker}
# Written by GTM Base. It reads what this send would carry and stops the send
# when it finds something that should not leave this computer. Delete this file
# to remove the check; GTM Base will put it back the next time it runs.

set -u

saved=$(mktemp "${{TMPDIR:-/tmp}}/gtm-base-push.XXXXXX") || exit 1
cat > "$saved"

if ! command -v python3 > /dev/null 2>&1; then
  rm -f "$saved"
  printf '%s\\n' "{missing}" >&2
  exit 1
fi

python3 {script} --client git --mode git-hook "$@" < "$saved"
status=$?
if [ "$status" -ne 0 ]; then
  rm -f "$saved"
  exit 1
fi

if [ -x {chained} ]; then
  {chained} "$@" < "$saved"
  status=$?
  rm -f "$saved"
  exit "$status"
fi

rm -f "$saved"
exit 0
""".format(
        marker=MARKER_LINE,
        missing=MISSING_PYTHON_SENTENCE,
        script=shlex.quote(script),
        chained=shlex.quote(chained),
    )


def _is_ours(path: str) -> bool:
    if not os.path.isfile(path) or os.path.islink(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return MARKER_LINE in handle.read(4000)
    except OSError:
        return False


def _configured_hooks_path(git: GitRunner, base_root: str) -> Optional[str]:
    result = git.run(["config", "--get", "core.hooksPath"], cwd=base_root)
    if not result.ok or not result.out():
        return None
    value = os.path.expanduser(result.out())
    if not os.path.isabs(value):
        value = os.path.join(base_root, value)
    return os.path.abspath(value)


def _default_hooks_dir(git: GitRunner, base_root: str) -> Optional[str]:
    result = git.run(["rev-parse", "--git-path", "hooks"], cwd=base_root)
    if not result.ok or not result.out():
        return None
    value = result.out()
    if not os.path.isabs(value):
        value = os.path.join(base_root, value)
    return os.path.abspath(value)


def _is_writable(folder: str) -> bool:
    """Whether the safeguard could be written here, without writing anything.

    A folder that is not there yet is judged by its parent. Nothing is created
    to find out, because the check that the folder is not part of the shared
    files runs after this one and creating a folder before that answer is known
    would leave a folder behind in a place we then refuse to write to.
    """
    if os.path.isdir(folder):
        return os.access(folder, os.W_OK | os.X_OK)
    parent = os.path.dirname(folder.rstrip(os.sep))
    return bool(parent) and os.path.isdir(parent) and os.access(parent, os.W_OK | os.X_OK)


def _is_tracked(git: GitRunner, base_root: str, folder: str) -> bool:
    """Whether the folder is part of the files everyone on the team shares."""
    try:
        relative = os.path.relpath(folder, base_root)
    except ValueError:
        return False
    if relative.startswith(".."):
        return False
    return git.run(["ls-files", "--error-unmatch", relative], cwd=base_root).ok


def install(
    base_root: str,
    plugin_root: str,
    runner: Optional[GitRunner] = None,
    base_id: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Put the safeguard in place. Return (code, folder it went in)."""
    git = runner_or_default(runner)
    code, hooks_dir = _install(git, base_root, plugin_root)
    if base_id:
        try:
            state.update_seat(
                base_id,
                git_hook_installed=code in (CODE_OK, CODE_CHAINED, CODE_RENAMED),
                git_hook_code=code,
            )
        except Exception:
            pass
    return code, hooks_dir


def _install(
    git: GitRunner, base_root: str, plugin_root: str
) -> Tuple[str, Optional[str]]:
    configured = _configured_hooks_path(git, base_root)
    hooks_dir = configured or _default_hooks_dir(git, base_root)
    if not hooks_dir:
        return CODE_NOT_INSTALLED, None
    if not _is_writable(hooks_dir):
        return CODE_NOT_WRITABLE, hooks_dir
    if _is_tracked(git, base_root, hooks_dir):
        return CODE_TRACKED, hooks_dir
    if not os.path.isdir(hooks_dir):
        try:
            os.makedirs(hooks_dir, DIR_MODE)
        except OSError:
            return CODE_NOT_WRITABLE, hooks_dir

    hook_path = os.path.join(hooks_dir, HOOK_NAME)
    chained_path = os.path.join(hooks_dir, CHAINED_NAME)
    code = CODE_OK
    if os.path.lexists(hook_path) and not _is_ours(hook_path):
        if os.path.lexists(chained_path):
            return CODE_UNMOVABLE, hooks_dir
        try:
            os.rename(hook_path, chained_path)
        except OSError:
            return CODE_UNMOVABLE, hooks_dir
        code = CODE_RENAMED
    elif os.path.lexists(chained_path):
        code = CODE_CHAINED

    text = hook_text(plugin_root, hooks_dir)
    try:
        with open(hook_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.chmod(hook_path, HOOK_MODE)
    except OSError:
        return CODE_NOT_WRITABLE, hooks_dir
    return code, hooks_dir
