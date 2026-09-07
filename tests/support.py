"""Helpers the Unit 2 tests share: a stand-in for git, and temporary folders.

The stand-in belongs here rather than in the library, because the library must
never carry a way to pretend that git said something.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base", "lib")
PLUGIN_DIR = os.path.join(REPO_ROOT, "plugins", "gtm-base")
TEMPLATES_DIR = os.path.join(PLUGIN_DIR, "templates")
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

for _path in (LIB_DIR,):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from gtmbase.gitcmd import GitResult  # noqa: E402


class FakeGitRunner(object):
    """Records every call and answers from a script the test wrote."""

    def __init__(self, results=None, default=None):
        # results maps a tuple of arguments to a GitResult.
        self.results = dict(results or {})
        self.default = default or GitResult(1, "", "")
        self.calls = []

    def add(self, args, code=0, stdout="", stderr=""):
        self.results[tuple(args)] = GitResult(code, stdout, stderr)
        return self

    def run(self, args, cwd=None, timeout=20, input=None):
        self.calls.append({"args": list(args), "cwd": cwd})
        return self.results.get(tuple(args), self.default)

    def check(self, args, cwd=None, timeout=20, input=None):
        from gtmbase.errors import GitError

        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result


class CountingRunner(object):
    """The real runner, with every call and the folder it ran in written down."""

    def __init__(self):
        from gtmbase.gitcmd import GitRunner

        self.inner = GitRunner()
        self.calls = []

    def run(self, args, cwd=None, timeout=20, input=None):
        self.calls.append({"args": list(args), "cwd": cwd})
        return self.inner.run(args, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        self.calls.append({"args": list(args), "cwd": cwd})
        return self.inner.check(args, cwd=cwd, timeout=timeout, input=input)


class SlowRunner(object):
    """A runner that waits before answering, for the checks about the budget."""

    def __init__(self, seconds=4.0):
        from gtmbase.gitcmd import GitResult, GitRunner

        self.inner = GitRunner()
        self.seconds = seconds
        self.calls = []
        self.timeouts = []
        self._result = GitResult

    def run(self, args, cwd=None, timeout=20, input=None):
        import time

        self.calls.append(list(args))
        self.timeouts.append(timeout)
        waited = min(float(timeout), self.seconds)
        time.sleep(waited)
        if waited < self.seconds:
            return self._result(124, "", "timeout")
        return self.inner.run(args, cwd=cwd, timeout=timeout, input=input)

    def check(self, args, cwd=None, timeout=20, input=None):
        from gtmbase.errors import GitError

        result = self.run(args, cwd=cwd, timeout=timeout, input=input)
        if not result.ok:
            raise GitError("git-failed", code="git-failed", result=result)
        return result


def git(args, cwd, check=True, author=None):
    """Run the real git binary in a test folder, with a fixed identity.

    `author` puts a different address on whatever this call writes, which is
    how a test says somebody other than the seat's owner accepted a change.
    """
    environment = dict(os.environ)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_AUTHOR_NAME"] = "Test Owner"
    environment["GIT_AUTHOR_EMAIL"] = author or "owner@example.com"
    environment["GIT_COMMITTER_NAME"] = "Test Owner"
    environment["GIT_COMMITTER_EMAIL"] = author or "owner@example.com"
    finished = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and finished.returncode != 0:
        raise AssertionError(
            "git %s failed in %s: %s"
            % (" ".join(args), cwd, finished.stderr.decode("utf-8", "replace"))
        )
    return finished


MAP_TEXT = """---
kind: map
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Map

## Settings

confirmation_threshold_days: 30
not_now_days: 7
"""

ICP_TEXT = """---
kind: icp
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Ideal customer profile

## Firmographics

Companies of any size.
"""


def write(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def make_base(root, base_id=None, remote=None, commit=True):
    """Build a folder shaped like a base: a repository holding the map."""
    os.makedirs(root, exist_ok=True)
    git(["init", "-b", "main", "-q"], cwd=root)
    git(["config", "--local", "user.email", "owner@example.com"], cwd=root)
    git(["config", "--local", "user.name", "Test Owner"], cwd=root)
    write(os.path.join(root, "context", "map.md"), MAP_TEXT)
    write(os.path.join(root, "context", "strategy", "icp.md"), ICP_TEXT)
    if base_id:
        git(["config", "--local", "gtmbase.id", base_id], cwd=root)
    if remote:
        git(["remote", "add", "origin", remote], cwd=root)
    if commit:
        git(["add", "-A"], cwd=root)
        git(["commit", "-q", "-m", "first"], cwd=root)
    return root


class TempHome(object):
    """A temporary seat folder, put in place for the length of one test."""

    def __init__(self):
        self.path = None
        self._previous = None

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="gtm-base-home-")
        self._previous = os.environ.get("GTM_BASE_HOME")
        os.environ["GTM_BASE_HOME"] = os.path.join(self.path, "seat")
        return self

    def __exit__(self, kind, value, trace):
        if self._previous is None:
            os.environ.pop("GTM_BASE_HOME", None)
        else:
            os.environ["GTM_BASE_HOME"] = self._previous
        shutil.rmtree(self.path, ignore_errors=True)
        return False


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Sandbox(object):
    """A temporary home, a temporary seat folder, and real repositories.

    Every test that touches git or seat state uses this, so nothing a test does
    can reach the person's own home folder, their git settings, or their real
    seat folder.
    """

    def __enter__(self):
        self.path = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-sandbox-"))
        self.saved = {name: os.environ.get(name) for name in ("HOME", "GTM_BASE_HOME")}
        os.environ["HOME"] = os.path.join(self.path, "home")
        os.makedirs(os.environ["HOME"])
        os.environ["GTM_BASE_HOME"] = os.path.join(self.path, "seat")
        return self

    def __exit__(self, kind, value, trace):
        for name, previous in self.saved.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous
        shutil.rmtree(self.path, ignore_errors=True)
        return False

    def base(self, name="base", joined=True, reviewed=True):
        """A base with a shared copy of its own, already sent once."""
        from gtmbase import constants, ids, machine, state

        remote = os.path.join(self.path, name + "-origin.git")
        git(["init", "--bare", "-q", "-b", "main", remote], cwd=self.path)
        root = os.path.join(self.path, name)
        base_id = ids.base_id_random()
        make_base(root, base_id=base_id, remote=remote)
        write(os.path.join(root, constants.ALLOWLIST_PATH), "# ours\n")
        write(os.path.join(root, constants.CODEOWNERS_PATH), "/context/ @owner\n")
        git(["add", "-A"], cwd=root)
        git(["commit", "-q", "-m", "files"], cwd=root)
        git(["push", "-q", "-u", "origin", "main"], cwd=root)
        if joined:
            machine.append_joined(root=root, base_id=base_id, remote=remote)
            state.update_seat(base_id, first_push_reviewed=bool(reviewed))
        return root, base_id


def commit(root, path, lines, message="a change"):
    """Save a change to one file in a test repository."""
    write(os.path.join(root, path), "\n".join(lines) + "\n")
    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", message], cwd=root)
    return path


def head_of(root):
    """The identifier of the newest saved work in a test repository."""
    finished = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


# --- Folders the trust check is meant to refuse (Unit 3) ---------------------

SETTINGS_TEXT = """{
  "extraKnownMarketplaces": {
    "gtm-base": {
      "source": {
        "source": "github",
        "repo": "brandon-sellers13/gtm-base",
        "sha": "%s"
      }
    }
  },
  "enabledPlugins": {
    "gtm-base@gtm-base": true
  }
}
""" % ("a" * 40)


def trust_checkout(parent, flaw=None, name=None, settings_text=None):
    """Build one folder shaped like a base, with one thing wrong with it.

    The hostile names are built here rather than kept in the repository,
    because a link and a file whose name holds a letter written with its accent
    taken apart do not survive being stored and handed around.
    """
    import unicodedata

    root = os.path.join(parent, name or ("trust-" + (flaw or "clean")))
    os.makedirs(root, exist_ok=True)
    git(["init", "-b", "main", "-q"], cwd=root)
    git(["config", "--local", "user.email", "owner@example.com"], cwd=root)
    git(["config", "--local", "user.name", "Test Owner"], cwd=root)
    write(os.path.join(root, "context", "map.md"), MAP_TEXT)
    write(os.path.join(root, "context", "strategy", "icp.md"), ICP_TEXT)
    write(
        os.path.join(root, ".claude", "settings.json"),
        SETTINGS_TEXT if settings_text is None else settings_text,
    )

    if flaw == "claude-md":
        write(os.path.join(root, "claude.md"), "read me first\n")
    elif flaw == "claude-folder":
        write(os.path.join(root, ".Claude", "commands", "x"), "do a thing\n")
    elif flaw == "nested-claude":
        write(os.path.join(root, "context", "CLAUDE.md"), "read me first\n")
    elif flaw == "decomposed":
        composed = "CLAUDÉ.md"
        write(os.path.join(root, unicodedata.normalize("NFD", composed)), "hello\n")
    elif flaw == "code-file":
        write(os.path.join(root, "context", "helper.py"), "print('hello')\n")
    elif flaw == "symlink":
        os.symlink("context/map.md", os.path.join(root, "shortcut.md"))
    elif flaw == "plugins-folder":
        write(os.path.join(root, "plugins", "other", "README.md"), "a plugin\n")
    elif flaw == "symlinked-map":
        os.remove(os.path.join(root, "context", "map.md"))
        write(os.path.join(root, "real-map.md"), MAP_TEXT)
        os.symlink(
            os.path.join(root, "real-map.md"), os.path.join(root, "context", "map.md")
        )
    elif flaw == "agents-md":
        write(os.path.join(root, "work", "AGENTS.md"), "read me first\n")

    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", "first"], cwd=root)
    return root


# --- Shared helpers for the proposal and stale-check tests -------------------


class RecordingGh(object):
    """A stand-in for the GitHub tool: it answers from a script and records."""

    def __init__(self, search=None, head=None, number=41, raise_on_create=False):
        self.search = search if search is not None else []
        self.head = head if head is not None else []
        self.number = number
        self.raise_on_create = raise_on_create
        self.calls = []
        self.bodies = []

    def created(self):
        return [call for call in self.calls if call[:2] == ["pr", "create"]]

    def __call__(self, args, cwd=None, stdin=None):
        arguments = [str(argument) for argument in args]
        if arguments[:2] == ["pr", "create"]:
            if self.raise_on_create:
                raise RuntimeError("the tool stopped halfway")
            self.calls.append(arguments)
            path = arguments[arguments.index("--body-file") + 1]
            self.bodies.append(read(path))
            return 0, json.dumps(
                {
                    "number": self.number,
                    "url": "https://example.test/pull/%d" % self.number,
                }
            )
        self.calls.append(arguments)
        if arguments[:2] == ["pr", "list"]:
            if "--head" in arguments:
                return 0, json.dumps(self.head)
            return 0, json.dumps(self.search)
        return 0, ""


def base_with_a_shared_copy(sandbox, name="base", reviewed=True):
    """A base whose transient folders are already excluded and already sent."""
    from gtmbase import constants

    root, base_id = sandbox.base(name=name, reviewed=reviewed)
    write(os.path.join(root, ".gitignore"), "work/inbox/\nwork/proposals/\n")
    write(
        os.path.join(root, constants.ALLOWLIST_PATH),
        "# ours\nowner@example.com\n",
    )
    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", "settings"], cwd=root)
    git(["push", "-q", "origin", "main"], cwd=root)
    remote = os.path.join(sandbox.path, name + "-origin.git")
    return root, base_id, remote


def show(remote, ref, path):
    """One file as a shared copy holds it on one line of work."""
    finished = subprocess.run(
        ["git", "--git-dir", remote, "show", "%s:%s" % (ref, path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if finished.returncode != 0:
        raise AssertionError(
            "%s is not in %s: %s" % (path, ref, finished.stderr.decode("utf-8"))
        )
    return finished.stdout.decode("utf-8")


def status_of(root):
    finished = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


def branch_of(root):
    finished = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


def ref_of(root, name):
    finished = subprocess.run(
        ["git", "rev-parse", name], cwd=root, stdout=subprocess.PIPE
    )
    return finished.stdout.decode("utf-8").strip()


class IndexingGh(RecordingGh):
    """A stand-in that remembers the reviews it opened, as the real tool does.

    The plain stand-in answers every search with the script the test wrote, so
    a run that opened a review a moment ago still looks to the next run like a
    base nobody has proposed anything on. This one keeps what it was handed:
    a review opened here is found again both by a search for the line the body
    carries and by a look for the line of work it was opened from.
    """

    def __init__(self, *arguments, **options):
        RecordingGh.__init__(self, *arguments, **options)
        self.opened = []

    def _matching_search(self, term):
        found = [
            review
            for review in self.opened
            if term in (review.get("body") or "")
        ]
        return found + list(self.search)

    def _matching_head(self, branch):
        return [
            review for review in self.opened if review.get("headRefName") == branch
        ] + list(self.head)

    def __call__(self, args, cwd=None, stdin=None):
        arguments = [str(argument) for argument in args]
        if arguments[:2] == ["pr", "list"]:
            self.calls.append(arguments)
            if "--head" in arguments:
                branch = arguments[arguments.index("--head") + 1]
                return 0, json.dumps(self._matching_head(branch))
            if "--search" in arguments:
                return 0, json.dumps(
                    self._matching_search(arguments[arguments.index("--search") + 1])
                )
            return 0, json.dumps(list(self.search))
        code, output = RecordingGh.__call__(self, args, cwd=cwd, stdin=stdin)
        if arguments[:2] == ["pr", "create"] and code == 0:
            head = ""
            if "--head" in arguments:
                head = arguments[arguments.index("--head") + 1]
            self.opened.append(
                {
                    "number": self.number,
                    "state": "OPEN",
                    "body": self.bodies[-1],
                    "url": "https://example.test/pull/%d" % self.number,
                    "headRefName": head,
                }
            )
        return code, output
