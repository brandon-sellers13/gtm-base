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
CODE_LINKED = "linked"
CODE_UNJOINED = "unjoined"
CODE_BASE_SHAPED = "base-shaped"
CODE_MULTIPLE_CHILDREN = "multiple-children"
CODE_LINK_CONFLICT = "link-conflict"
CODE_LINK_MISMATCH = "link-identity-mismatch"
CODE_CONTENT_INSIDE_BASE = "content-inside-base"
CODE_NONE = "none"

# The two codes that mean a base is working in this session.
ACTIVE_CODES = (CODE_JOINED, CODE_LINKED)

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

    __slots__ = (
        "root",
        "base_id",
        "code",
        "entry",
        "content_root",
        "repair_root",
        "conflict_roots",
    )

    def __init__(
        self,
        root=None,
        base_id=None,
        code=CODE_NONE,
        entry=None,
        content_root=None,
        repair_root=None,
        conflict_roots=None,
    ):
        self.root = root
        self.base_id = base_id
        self.code = code
        self.entry = entry
        # The folder this base belongs with, when it was reached through one.
        self.content_root = content_root
        # The folder the record should be pointed at, when the folder a base
        # belongs with turns out to have been renamed. Working this out is a
        # question, so it happens here; writing it down is a change, so it
        # happens in the one half of the session start that may write.
        self.repair_root = repair_root
        # The base folders of every base claiming this folder, when more than
        # one of them does and nothing may therefore be opened.
        self.conflict_roots = list(conflict_roots or [])

    @property
    def joined(self) -> bool:
        return self.code == CODE_JOINED

    @property
    def active(self) -> bool:
        """Whether this session has a base to work in, however it was reached."""
        return self.code in ACTIVE_CODES

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


def _linked(here: str, entries, git):
    """The one base this folder belongs with, or the reason there is not one.

    Every claim is collected before any of them is chosen. A folder that two
    bases both claim is a stop rather than a guess, and picking the one whose
    path happens to be current would hand a session opened for one company the
    context of another.

    A folder at a recorded path whose evidence no longer agrees was deleted and
    built again, or is sitting on a disk that came back as a different disk.
    Neither is the folder that was recorded, so neither opens a base, and both
    are reported by their own code so the person can be told how to connect the
    folder again.
    """
    from . import folder_identity  # imported here to keep the import order simple

    linked = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        recorded_root = entry.get("content_root")
        recorded = folder_identity.clean(entry.get("content_identity"))
        if isinstance(recorded_root, str) and recorded is not None:
            linked.append((entry, recorded_root, recorded))
    if not linked:
        # Nothing on this account belongs with any folder, so there is nothing
        # to compare this one against and no reason to look at it at all.
        return None

    # The disk's own identifier is only worth the wait when at least one record
    # has one to compare against.
    wants_volume = any(record.get("volume") is not None for _e, _r, record in linked)
    try:
        current = folder_identity.capture(here, runner=git, with_volume=wants_volume)
    except StateError:
        return None

    claims = []
    mismatched = False
    for entry, recorded_root, recorded in linked:
        verdict = folder_identity.matches(recorded, current, recorded_root)
        if verdict in (folder_identity.SAME, folder_identity.MOVED):
            claims.append((entry, verdict))
            continue
        if folder_identity.points_at(recorded_root, current) or (
            os.path.exists(recorded_root)
            and os.path.realpath(recorded_root) == current.path
        ):
            mismatched = True

    if len(claims) > 1:
        roots = sorted(
            str(entry.get("root") or "") for entry, _verdict in claims
        )
        return Resolution(None, None, CODE_LINK_CONFLICT, None, conflict_roots=roots)
    if not claims:
        if mismatched:
            return Resolution(None, None, CODE_LINK_MISMATCH, None)
        return None

    entry, verdict = claims[0]
    root = entry.get("root")
    if not isinstance(root, str) or not is_base_shaped(root):
        return None
    real = os.path.realpath(root)
    # A folder that has since come to sit inside another base could hand one
    # company's session the context of another, so it is checked again here
    # rather than trusted because it passed when it was written down.
    for other in entries:
        if not isinstance(other, dict) or other is entry:
            continue
        other_root = other.get("root")
        if not isinstance(other_root, str) or not os.path.isdir(other_root):
            continue
        other_real = os.path.realpath(other_root)
        if current.path == other_real or current.path.startswith(
            other_real.rstrip(os.sep) + os.sep
        ):
            return Resolution(None, None, CODE_CONTENT_INSIDE_BASE, None)

    base_id = read_base_id(real, runner=git)
    if base_id is None or base_id != entry.get("base_id"):
        return None
    return Resolution(
        real,
        base_id,
        CODE_LINKED,
        entry,
        content_root=current.path,
        repair_root=current.path if verdict == folder_identity.MOVED else None,
    )


def resolve_base(cwd: str, machine_state, runner: Optional[GitRunner] = None):
    """The only way any hook or skill decides which base it is working in.

    Four questions, in this order, and the first one that answers wins.

    The folder itself, or a `gtm-base` folder inside it. A base counts as joined
    only when this account's own record names that folder and the identifier
    written in the folder matches the record, so a copied folder or an invented
    record never opens anything.

    A folder that looks like a base but that this account has never opened. That
    answer comes back before any association is looked at, so a base whose own
    folder was renamed is recognised as itself rather than as somebody else's.

    The folder a base belongs with. One base may claim it, and the folder has to
    still be the folder that was recorded.

    Nothing here, in which case the offer rules decide what happens.

    Nothing in this function writes anything down.
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

    linked = _linked(here, entries, git)
    if linked is not None:
        return linked
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
