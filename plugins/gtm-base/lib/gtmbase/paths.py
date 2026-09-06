"""Where everything lives, and the checks that keep a path where it belongs.

Three questions are answered here. Which folder on this machine holds what one
person's seat must remember. Which folder is the base, and has this account
joined it. And whether a path a model or a file handed us really points at a
file inside the base's `context` folder and nowhere else.
"""

from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

from . import constants, ids
from .errors import PathError, StateError
from .fsutil import ensure_dir
from .gitcmd import GitRunner, runner_or_default

# The longest a repository-relative path may be, counted in characters.
MAX_PATH_LENGTH = 400

# Characters a path may never hold, because they either break a line-based
# record or turn a path into a link when a person reads it as markdown.
FORBIDDEN_PATH_CHARACTERS = ("[", "]", "(", ")", "\\", '"', "'", "|", "*", "?")

# The folders a proposal is allowed to change.
PROPOSAL_PATH_PREFIXES = (
    constants.CONTEXT_DIR + "/",
    constants.DECISIONS_DIR + "/",
    constants.CORRECTIONS_DIR + "/",
)

# The codes `resolve_base` can report.
CODE_JOINED = "joined"
CODE_UNJOINED = "unjoined"
CODE_BASE_SHAPED = "base-shaped"
CODE_MULTIPLE_CHILDREN = "multiple-children"
CODE_NONE = "none"

# The codes `head_is_default_branch` can report.
CODE_DEFAULT_BRANCH = "default-branch"
CODE_NOT_DEFAULT_BRANCH = "not-default-branch"
CODE_DETACHED = "detached"
CODE_NO_DEFAULT_BRANCH = "no-default-branch"
CODE_GIT_FAILED = "git-failed"

BASE_ID_CONFIG_KEY = "gtmbase.id"


# --- Path shape -------------------------------------------------------------


def check_repo_path_syntax(
    candidate, prefixes: Sequence[str] = (constants.CONTEXT_DIR + "/",)
) -> str:
    """Check the shape of a repository-relative path without touching the disk.

    This is the check a file format runs on a path it read out of frontmatter,
    where the base itself may not be present. It refuses an absolute path, a
    path that climbs out with `..`, a path holding a line break or any other
    control character, markdown link punctuation, and anything that does not
    sit under one of the folders the caller allows.
    """
    if not isinstance(candidate, str) or not candidate.strip():
        raise PathError("this path is empty", code="empty-path")
    text = candidate.strip()
    if len(text) > MAX_PATH_LENGTH:
        raise PathError("this path is too long", code="long-path")
    for character in text:
        if ord(character) < 32 or ord(character) == 127:
            raise PathError("this path holds a control character", code="control-character")
    for character in FORBIDDEN_PATH_CHARACTERS:
        if character in text:
            raise PathError("this path holds punctuation we never allow", code="bad-character")
    if text.startswith("/") or text.startswith("~"):
        raise PathError("this path is not relative to the base", code="absolute-path")
    if len(text) > 1 and text[1] == ":":
        raise PathError("this path names a drive", code="absolute-path")
    segments = text.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise PathError("this path climbs out of the base", code="climbing-path")
    for prefix in prefixes:
        if text.startswith(prefix) and len(text) > len(prefix):
            return text
    raise PathError("this path is outside the folders we allow", code="outside-base")


def check_context_path_syntax(candidate) -> str:
    """The shape check for a path that must sit under the `context` folder."""
    return check_repo_path_syntax(candidate, (constants.CONTEXT_DIR + "/",))


def canonical_context_path(base_root: str, candidate: str) -> str:
    """Return the repository-relative path of a file inside `context`.

    The shape is checked first, then the real path is resolved, so a link that
    points out of the base is refused even though its name looks ordinary.
    """
    relative = check_context_path_syntax(candidate)
    context_root = os.path.realpath(os.path.join(base_root, constants.CONTEXT_DIR))
    resolved = os.path.realpath(os.path.join(base_root, relative))
    if resolved == context_root or not _is_inside(resolved, context_root):
        raise PathError("this path leaves the context folder", code="outside-context")
    return relative


def _is_inside(path: str, folder: str) -> bool:
    prefix = folder.rstrip(os.sep) + os.sep
    return path.startswith(prefix)


# --- The seat directory -----------------------------------------------------


def seat_home_path() -> str:
    """Where this person's seat folder is, whether or not it is there yet.

    Anything that only needs to compare a path against the seat folder asks
    for this, so a check never brings the folder into being as a side effect
    of asking a question about it.
    """
    override = os.environ.get(constants.SEAT_HOME_ENV)
    raw = override if override else constants.SEAT_HOME_DEFAULT
    return os.path.abspath(os.path.expanduser(raw))


def seat_home() -> str:
    """The folder holding everything this person's seat remembers.

    It is `~/.gtm-base` unless the override says otherwise. The plugin data
    folder some clients offer is never used, because it does not reach the
    place the skills' own scripts run.
    """
    return ensure_dir(seat_home_path())


def bases_dir() -> str:
    return ensure_dir(os.path.join(seat_home(), "bases"))


def seat_dir(base_id: str) -> str:
    """The folder holding what this seat remembers about one base."""
    ids.check_base_id(base_id)
    return ensure_dir(os.path.join(bases_dir(), base_id))


def worktrees_dir(base_id: str) -> str:
    """The folder where this seat does its git work, away from the clone."""
    return ensure_dir(os.path.join(seat_dir(base_id), "worktrees"))


def machine_state_path() -> str:
    """The one file per account holding the offer answer and the joined list."""
    return os.path.join(seat_home(), constants.MACHINE_STATE_FILE)


def armed_sentinel_path() -> str:
    """The file that says a capture run is armed right now."""
    return os.path.join(seat_home(), constants.ARMED_SENTINEL)


# --- The base ---------------------------------------------------------------


def git_root(cwd: str, runner: Optional[GitRunner] = None) -> Optional[str]:
    """The top of the repository holding cwd, or None when there is none."""
    result = runner_or_default(runner).run(["rev-parse", "--show-toplevel"], cwd=cwd)
    if not result.ok:
        return None
    top = result.out()
    return os.path.realpath(top) if top else None


def read_base_id(root: str, runner: Optional[GitRunner] = None) -> Optional[str]:
    """The identifier of the base at root, or None when it has none yet.

    A base carries its own identifier in the local git settings of its clone.
    When it has none but does have a remote address, every seat derives the
    same identifier from that address instead.
    """
    git = runner_or_default(runner)
    result = git.run(["config", "--local", "--get", BASE_ID_CONFIG_KEY], cwd=root)
    if result.ok:
        value = result.out()
        if ids.is_base_id(value):
            return value
    address = remote_url(root, runner=git)
    if address:
        try:
            return ids.base_id_for_remote(address)
        except ValueError:
            return None
    return None


def write_base_id(root: str, base_id: str, runner: Optional[GitRunner] = None) -> str:
    """Record a base's identifier in the local git settings of its clone."""
    ids.check_base_id(base_id)
    runner_or_default(runner).check(
        ["config", "--local", BASE_ID_CONFIG_KEY, base_id], cwd=root
    )
    return base_id


def remote_url(root: str, runner: Optional[GitRunner] = None) -> Optional[str]:
    """The address of the base's remote copy, with any user name removed."""
    result = runner_or_default(runner).run(["remote", "get-url", "origin"], cwd=root)
    if not result.ok:
        return None
    address = result.out()
    if not address:
        return None
    return ids.strip_userinfo(address)


def canonical_remote(root: str, runner: Optional[GitRunner] = None) -> Optional[str]:
    """The one form of the remote address every seat agrees on."""
    address = remote_url(root, runner=runner)
    if not address:
        return None
    try:
        return ids.canonical_remote_address(address)
    except ValueError:
        return None


def head_is_default_branch(
    root: str, runner: Optional[GitRunner] = None
) -> Tuple[bool, str]:
    """Whether the clone is sitting on the branch the team shares.

    The shared branch is the one the remote points at when there is a remote,
    and otherwise `main` if it exists and `master` if it does not.
    """
    git = runner_or_default(runner)
    current = git.run(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=root)
    if not current.ok:
        inside = git.run(["rev-parse", "--is-inside-work-tree"], cwd=root)
        if not inside.ok:
            return False, CODE_GIT_FAILED
        return False, CODE_DETACHED
    branch = current.out()

    default = git.run(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd=root
    )
    if default.ok and default.out():
        name = default.out().split("/", 1)[-1]
    else:
        name = None
        for candidate in ("main", "master"):
            exists = git.run(
                ["show-ref", "--verify", "--quiet", "refs/heads/" + candidate], cwd=root
            )
            if exists.ok:
                name = candidate
                break
        if name is None:
            return False, CODE_NO_DEFAULT_BRANCH
    if branch == name:
        return True, CODE_DEFAULT_BRANCH
    return False, CODE_NOT_DEFAULT_BRANCH


def is_base_shaped(directory: str) -> bool:
    """Whether a folder looks like a base: a repository holding the map.

    The map must be a real file, not a link, because a link is a way to make
    one folder read as two different bases.
    """
    if not directory or not os.path.isdir(directory):
        return False
    if not os.path.exists(os.path.join(directory, ".git")):
        return False
    map_path = os.path.join(directory, constants.MAP_PATH)
    if os.path.islink(map_path) or not os.path.isfile(map_path):
        return False
    return True


class Resolution(object):
    """The answer to "which base is this session working in, if any"."""

    __slots__ = ("root", "base_id", "code", "entry")

    def __init__(self, root=None, base_id=None, code=CODE_NONE, entry=None):
        self.root = root
        self.base_id = base_id
        self.code = code
        self.entry = entry

    @property
    def joined(self) -> bool:
        return self.code == CODE_JOINED

    def __repr__(self) -> str:
        return "Resolution(code=%r, root=%r)" % (self.code, self.root)


def _child_bases(cwd: str) -> List[str]:
    """Every direct child of cwd named `gtm-base`, whatever its letter case."""
    try:
        names = os.listdir(cwd)
    except OSError:
        return []
    wanted = "gtm-base".casefold()
    found = []
    for name in sorted(names):
        if name.casefold() != wanted:
            continue
        path = os.path.join(cwd, name)
        if os.path.isdir(path):
            found.append(path)
    return found


def resolve_base(cwd: str, machine_state, runner: Optional[GitRunner] = None):
    """The only way any hook or skill decides which base it is working in.

    The current folder is checked first, then a `gtm-base` folder inside it.
    A base counts as joined only when this account's own record names that
    folder and the identifier written in the folder matches the record, so a
    copied folder or an invented record never activates anything.
    """
    git = runner_or_default(runner)
    here = os.path.realpath(cwd)

    children = _child_bases(here)
    if len(children) > 1:
        return Resolution(None, None, CODE_MULTIPLE_CHILDREN, None)

    candidates = [here] + children
    entries = list(getattr(machine_state, "joined", None) or [])

    fallback = None
    for candidate in candidates:
        if not is_base_shaped(candidate):
            continue
        base_id = read_base_id(candidate, runner=git)
        real = os.path.realpath(candidate)
        if base_id is not None:
            for entry in entries:
                entry_root = entry.get("root") if isinstance(entry, dict) else None
                entry_id = entry.get("base_id") if isinstance(entry, dict) else None
                if not entry_root:
                    continue
                if os.path.realpath(entry_root) != real:
                    continue
                if entry_id != base_id:
                    continue
                return Resolution(real, base_id, CODE_JOINED, entry)
        if fallback is None:
            code = CODE_UNJOINED if base_id is not None else CODE_BASE_SHAPED
            fallback = Resolution(real, base_id, code, None)
    if fallback is not None:
        return fallback
    return Resolution(None, None, CODE_NONE, None)


def migrate(base_id: str, new_base_id: str, **unused):
    """Move a seat's folder to the identifier derived from a new remote.

    Not available yet. Moving a seat's folder is part of the release that adds
    the remote copy, and it has to record the pair of identifiers before the
    move, refuse while any git work folder still exists, and refuse when a
    folder for the new identifier is already there. Until that lands this
    raises, so no caller can quietly carry on as though the move happened.
    """
    raise StateError("migration-not-available", code="migration-not-available")
