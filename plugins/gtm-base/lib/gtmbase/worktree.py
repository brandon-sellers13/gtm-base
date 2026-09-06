"""The working folders where this seat prepares work, away from the clone.

The person's own folder stays on the shared branch and keeps whatever they were
in the middle of. Everything this plugin prepares happens in a separate folder
under the seat directory, one per staged proposal and one for confirmations, so
a run that stops halfway leaves the person's folder exactly as it was.

Every git call goes through the injectable runner, so a test can watch what was
asked for without a network anywhere in sight.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from typing import List, Optional

from . import constants, paths
from .fsutil import ensure_dir
from .errors import GitError
from .gitcmd import GitRunner, runner_or_default

# How long the update from the shared copy may take before we carry on without
# it. A slow network must not stop a person from preparing a proposal.
FETCH_TIMEOUT_SECONDS = 10

# Codes this module reports. They are recorded, never shown as sentences.
CODE_FETCH_FAILED = "fetch-failed"
CODE_NO_REMOTE = "no-remote"
CODE_REUSED = "worktree-reused"
CODE_CREATED = "worktree-created"
CODE_REPLACED = "worktree-replaced"
CODE_REBRANCHED = "worktree-put-back-on-its-branch"

CONFIRMATIONS_FOLDER_NAME = "confirmations"


class WorktreeInfo(object):
    """One working folder: where it is, which line of work it holds, and why."""

    __slots__ = ("path", "branch", "codes", "start_point")

    def __init__(self, path: str, branch: str, codes=None, start_point: str = ""):
        self.path = path
        self.branch = branch
        self.codes = list(codes or [])
        self.start_point = start_point

    def __repr__(self) -> str:
        return "WorktreeInfo(path=%r, branch=%r)" % (self.path, self.branch)


def _has_remote(base_root: str, git: GitRunner) -> bool:
    return git.run(["remote", "get-url", "origin"], cwd=base_root).ok


def start_point_for(base_root: str, default_branch: str, git: GitRunner) -> "tuple":
    """The point new work starts from, and the codes worth recording.

    Work always starts from the shared branch, never from another proposal, so
    a proposal that is later dropped takes nothing with it. The shared copy is
    asked for its latest first; when that cannot be reached the local copy of
    the shared branch is used and the reason is recorded.
    """
    codes: List[str] = []
    if not default_branch:
        raise GitError("no-default-branch", code="no-default-branch")
    if not _has_remote(base_root, git):
        return default_branch, [CODE_NO_REMOTE]
    fetched = git.run(
        ["fetch", "origin", default_branch],
        cwd=base_root,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    remote_ref = "origin/" + default_branch
    if not fetched.ok:
        codes.append(CODE_FETCH_FAILED)
    exists = git.run(
        ["rev-parse", "--verify", "--quiet", remote_ref + "^{commit}"], cwd=base_root
    )
    if exists.ok:
        return remote_ref, codes
    if CODE_FETCH_FAILED not in codes:
        codes.append(CODE_FETCH_FAILED)
    return default_branch, codes


def list_worktrees(base_root: str, runner: Optional[GitRunner] = None) -> List[str]:
    """Every working folder git currently knows about for this base."""
    git = runner_or_default(runner)
    result = git.run(["worktree", "list", "--porcelain"], cwd=base_root)
    if not result.ok:
        return []
    found = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            found.append(os.path.realpath(line[len("worktree ") :].strip()))
    return found


def worktree_exists(
    base_root: str, path: str, runner: Optional[GitRunner] = None
) -> bool:
    """Whether this folder is there and git still counts it as a working folder."""
    if not os.path.isdir(path):
        return False
    return os.path.realpath(path) in list_worktrees(base_root, runner=runner)


def branch_of(path: str, runner: Optional[GitRunner] = None) -> str:
    """The name of the line of work a working folder is on."""
    git = runner_or_default(runner)
    result = git.run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    return result.out() if result.ok else ""


def remove_worktree(
    base_root: str, path: str, runner: Optional[GitRunner] = None
) -> bool:
    """Take a working folder away and forget it, whatever state it is in."""
    git = runner_or_default(runner)
    removed = False
    if os.path.isdir(path):
        result = git.run(["worktree", "remove", "--force", path], cwd=base_root)
        removed = result.ok
        if not result.ok:
            shutil.rmtree(path, ignore_errors=True)
            removed = not os.path.isdir(path)
    git.run(["worktree", "prune"], cwd=base_root)
    return removed


def _create(
    base_root: str, path: str, branch: str, start_point: str, git: GitRunner
) -> None:
    """Make the folder at the shared branch, then put it on its own line of work.

    The folder is made detached first and the line of work is started inside it,
    so nothing about the person's own folder, including which branch it is on,
    is touched at any point.
    """
    parent = os.path.dirname(path)
    ensure_dir(parent)
    git.check(["worktree", "add", "--detach", path, start_point], cwd=base_root)
    git.check(["checkout", "-B", branch], cwd=path)


def ensure_worktree(
    base_root: str,
    base_id: str,
    staging_id: str,
    default_branch: str,
    runner: Optional[GitRunner] = None,
) -> WorktreeInfo:
    """The working folder for one staged proposal, made or reused.

    A folder that is already there and still known to git is handed back as it
    stands, which is what makes a run that stopped halfway safe to repeat. A
    folder that is there but no longer known is thrown away and made again.
    """
    git = runner_or_default(runner)
    folder = os.path.join(paths.worktrees_dir(base_id), staging_id)
    branch = constants.PROPOSAL_BRANCH_PREFIX + staging_id

    if worktree_exists(base_root, folder, runner=git):
        return _reuse(folder, branch, git)

    codes: List[str] = []
    if os.path.isdir(folder):
        remove_worktree(base_root, folder, runner=git)
        shutil.rmtree(folder, ignore_errors=True)
        codes.append(CODE_REPLACED)

    start_point, start_codes = start_point_for(base_root, default_branch, git)
    codes.extend(start_codes)
    _create(base_root, folder, branch, start_point, git)
    codes.append(CODE_CREATED)
    return WorktreeInfo(folder, branch, codes, start_point)


def _reuse(folder: str, branch: str, git: GitRunner) -> WorktreeInfo:
    """Hand back a folder that is already there, on the line of work it needs.

    A run that stopped halfway can leave the folder on no line of work at all,
    which git calls a detached head. Work saved there has no name to send, so
    the folder is put back on its own line of work before it is handed on.
    """
    existing = branch_of(folder, runner=git)
    if existing == branch:
        return WorktreeInfo(folder, branch, [CODE_REUSED])
    git.check(["checkout", "-B", branch], cwd=folder)
    return WorktreeInfo(folder, branch, [CODE_REUSED, CODE_REBRANCHED])


def seat_short_id(
    base_root: str, base_id: str, runner: Optional[GitRunner] = None
) -> str:
    """A short name for one person's seat on one base.

    Confirmations are written by one seat at a time, so the line of work they
    are written on carries a name derived from the base and the address this
    seat saves work under. It holds no address itself.
    """
    git = runner_or_default(runner)
    result = git.run(["config", "--local", "--get", "user.email"], cwd=base_root)
    email = result.out() if result.ok else ""
    material = "%s\x1f%s" % (base_id, email)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def ensure_confirmations_worktree(
    base_root: str,
    base_id: str,
    default_branch: str,
    runner: Optional[GitRunner] = None,
) -> WorktreeInfo:
    """The one working folder where this seat records the owner's answers."""
    git = runner_or_default(runner)
    folder = os.path.join(paths.worktrees_dir(base_id), CONFIRMATIONS_FOLDER_NAME)
    branch = constants.CONFIRMATIONS_BRANCH_PREFIX + seat_short_id(
        base_root, base_id, runner=git
    )

    if worktree_exists(base_root, folder, runner=git):
        return _reuse(folder, branch, git)

    codes: List[str] = []
    if os.path.isdir(folder):
        remove_worktree(base_root, folder, runner=git)
        shutil.rmtree(folder, ignore_errors=True)
        codes.append(CODE_REPLACED)

    start_point, start_codes = start_point_for(base_root, default_branch, git)
    codes.extend(start_codes)
    _create(base_root, folder, branch, start_point, git)
    codes.append(CODE_CREATED)
    return WorktreeInfo(folder, branch, codes, start_point)
