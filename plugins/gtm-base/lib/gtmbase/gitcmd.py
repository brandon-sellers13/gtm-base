"""The one way this plugin runs git.

Every git call in the library goes through a runner object, so tests can hand
in a stand-in and no module reaches for a subprocess of its own. The runner
never lets git ask for a password, always sets a time limit, and keeps git's
own error text on the result rather than passing it into anything a person or
a model sees.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Optional, Sequence

from .errors import GitError

DEFAULT_TIMEOUT_SECONDS = 20

# Exit codes this library invents for the two failures git cannot report itself.
TIMEOUT_CODE = 124
MISSING_CODE = 127


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
        """Run one git command and return its result. This never raises."""
        command = [self.git_path] + list(args)
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
