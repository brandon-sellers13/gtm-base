"""The one way this plugin runs the GitHub command line tool.

It mirrors the way git is run: one small object, handed in by the caller, so a
test can watch every call and answer it without a network. The tool acts as the
person who is signed in, which is why the proposals it opens say in their own
words that an assistant drafted them.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional, Sequence, Tuple

DEFAULT_TIMEOUT_SECONDS = 30

# Exit codes this library invents for the two failures the tool cannot report.
TIMEOUT_CODE = 124
MISSING_CODE = 127


class GhResult(object):
    """What one call returned: its exit code and its two output streams."""

    __slots__ = ("code", "stdout", "stderr")

    def __init__(self, code: int, stdout: str = "", stderr: str = ""):
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def ok(self) -> bool:
        return self.code == 0

    def out(self) -> str:
        return self.stdout.strip()

    def __repr__(self) -> str:
        return "GhResult(code=%r)" % (self.code,)


class GhRunner(object):
    """Runs the GitHub tool found on the path, with a time limit on every call."""

    def __init__(self, gh_path: str = "gh"):
        self.gh_path = gh_path

    def environment(self) -> dict:
        environment = dict(os.environ)
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GH_PROMPT_DISABLED"] = "1"
        environment["GH_NO_UPDATE_NOTIFIER"] = "1"
        environment["CLICOLOR"] = "0"
        environment["NO_COLOR"] = "1"
        return environment

    def __call__(
        self,
        args: Sequence[str],
        cwd: Optional[str] = None,
        stdin: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> Tuple[int, str]:
        """Run one call and return its exit code and what it printed."""
        result = self.run(args, cwd=cwd, stdin=stdin, timeout=timeout)
        return result.code, result.stdout

    def run(
        self,
        args: Sequence[str],
        cwd: Optional[str] = None,
        stdin: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> GhResult:
        command = [self.gh_path] + [str(argument) for argument in args]
        try:
            finished = subprocess.run(
                command,
                cwd=cwd,
                env=self.environment(),
                input=stdin.encode("utf-8") if stdin is not None else None,
                stdin=None if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return GhResult(TIMEOUT_CODE, "", "timeout")
        except (OSError, ValueError):
            return GhResult(MISSING_CODE, "", "gh-missing")
        return GhResult(
            finished.returncode,
            finished.stdout.decode("utf-8", "replace"),
            finished.stderr.decode("utf-8", "replace"),
        )


_DEFAULT_RUNNER = None


def default_runner() -> GhRunner:
    global _DEFAULT_RUNNER
    if _DEFAULT_RUNNER is None:
        _DEFAULT_RUNNER = GhRunner()
    return _DEFAULT_RUNNER


def runner_or_default(runner):
    """The runner the caller handed in, or the one that runs the real tool."""
    return runner if runner is not None else default_runner()


def call(runner, args, cwd=None, stdin=None) -> Tuple[int, str]:
    """Run one call through whichever runner the caller supplied.

    A runner is any callable taking the arguments, the folder to work in, and
    the text to hand over, and returning the exit code and what was printed.
    """
    result = runner_or_default(runner)(args, cwd, stdin)
    if isinstance(result, tuple):
        return int(result[0]), str(result[1] or "")
    return int(getattr(result, "code", 1)), str(getattr(result, "stdout", "") or "")
