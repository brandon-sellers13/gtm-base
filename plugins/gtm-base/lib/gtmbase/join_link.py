"""Joining a base somebody else backed up, from its GitHub address (P2).

A teammate is invited to a base's private GitHub repository in the GTM Base
app, and the app gives them one line to say in Claude Code. This is what that
line runs, in two steps that are two separate commands:

1. `review` reads and writes nothing. It checks the address is a GitHub
   repository this computer's own git sign-in can read, that the repository is
   private and holds something, that this computer does not already have it,
   and works out the folder the base would go in, which is the usual place for
   bases: `~/GTM Bases/<repository name>/gtm-base`.
2. `join` is an approval only a person can give: Claude Code asks them itself
   (see `approval`), and the address on the command line is the one they are
   asked about. It copies the base into a half built folder beside where it is
   going, reads everything it copied before anything acts on it, and only then
   renames the folder into place and records this computer as a seat on it.

What this never does:

- It holds no sign-in of its own. Git on this computer reads the repository
  with whatever sign-in the person already gave it, through the same well-known
  helpers every other GTM Base network command uses (`gitcmd`), and nothing git
  prints is ever repeated, because a sign-in failure can echo an address.
- It writes nothing outside the folder the base goes in and this person's own
  GTM Base folder. A copy that fails any check is removed whole, and the folder
  made for it is removed too when it was made for this join and is empty.
- It never sends anything. A seat's own changes leave this computer only as
  proposals, which `gate` holds it to: a seat never sends straight to the line
  of work the team shares, apart from the confirmation lines the app counts as
  bookkeeping.

A copied base is checked twice before anything acts on it. The shared copy's
own list of files is read first, before a single file is written, and a link
or a folder of another repository is refused there. The written folder is then
read by the trust check every session start runs (`trust_surface`), which
refuses instruction files, code files, agent folders, a settings file that
does anything beyond installing this plugin, and anything in the skills folder
that is not a skill this base keeps the way a skill must be kept.
"""

from __future__ import annotations

import datetime
import os
import shutil
from typing import List, NamedTuple, Optional

from . import (
    approval,
    backup,
    constants,
    ids,
    install_git_hook,
    location,
    machine,
    paths,
    state,
    trust_surface,
)
from .errors import GtmBaseError, LocationError
from .gitcmd import GitRunner, runner_or_default
from .validate import is_valid_email

FETCH_TIMEOUT_SECONDS = 180

CODE_BAD_ADDRESS = backup.CODE_BAD_ADDRESS
CODE_CANNOT_REACH = "join-cannot-reach"
CODE_PUBLIC = "join-public"
CODE_EMPTY = "join-empty"
CODE_ALREADY_HERE = "join-already-here"
CODE_FOLDER_TAKEN = "join-folder-taken"
CODE_BAD_PLACE = "join-bad-place"
CODE_BAD_NAME = "join-bad-name"
CODE_NOT_A_BASE = "join-not-a-base"
CODE_NOT_TRUSTED = "join-not-trusted"
CODE_COPY_FAILED = "join-copy-failed"

SENTENCES = {
    CODE_BAD_ADDRESS: backup.SENTENCES[backup.CODE_BAD_ADDRESS],
    CODE_CANNOT_REACH: (
        "GitHub did not let this computer read that repository, so nothing was "
        "copied. Accept the invitation to it first, from the email GitHub sent "
        "or from the repository's page, and check that git on this computer is "
        "signed in to GitHub with the account that was invited."
    ),
    CODE_PUBLIC: (
        "Anyone can read that repository without signing in, so nothing was "
        "copied. A base only lives in a private repository; ask whoever sent "
        "the link to make it private on GitHub."
    ),
    CODE_EMPTY: (
        "That repository is empty, so there is no base in it to join yet. Ask "
        "whoever sent the link to back their base up first."
    ),
    CODE_ALREADY_HERE: (
        "This computer already has that base, in the folder on the base line "
        "below, so nothing was copied."
    ),
    CODE_FOLDER_TAKEN: (
        "There is already a folder for a base of that name on this computer, "
        "on the folder line below, so nothing was copied. Move or rename that "
        "folder first if it is not this base."
    ),
    CODE_BAD_PLACE: (
        "The folder kept for bases on this computer is not a place a base may "
        "go right now, because another program copies it off this computer or "
        "it sits inside another project, so nothing was copied."
    ),
    CODE_BAD_NAME: (
        "That repository's name cannot be used as the name of a folder, so "
        "nothing was copied."
    ),
    CODE_NOT_A_BASE: (
        "That repository does not hold a company base, so nothing was kept on "
        "this computer."
    ),
    CODE_NOT_TRUSTED: (
        "That repository holds files a company base never holds, such as "
        "instructions an assistant would follow on its own, code, or links to "
        "other places on this computer, so nothing was kept on this computer. "
        "Ask whoever sent the link to have the base's owner look at it."
    ),
    CODE_COPY_FAILED: (
        "Git could not copy the base onto this computer, so nothing was kept. "
        "Check that git on this computer is signed in to GitHub, then ask "
        "again."
    ),
}

# The file modes a base's saved files may have. A link (120000) and a folder
# that is another repository (160000) are never part of a base.
_FILE_MODES = ("100644", "100755")


def _refuse(code: str) -> GtmBaseError:
    return GtmBaseError(SENTENCES[code], code)


class Place(NamedTuple):
    address: str  # https://github.com/<owner>/<repo>.git
    name: str  # the repository's name, which names the folder
    parent: str  # ~/GTM Bases/<name>
    target: str  # ~/GTM Bases/<name>/gtm-base
    base_id: str


class Joined(NamedTuple):
    root: str
    base_id: str
    address: str
    branch: str
    hook_code: str


def _name_of(address: str) -> str:
    match = backup._ADDRESS_RE.match(address)
    if not match:
        raise _refuse(CODE_BAD_ADDRESS)
    return match.group("repo")


def already_here(address: str) -> Optional[str]:
    """The folder this computer already keeps the base at `address` in, if any."""
    wanted = ids.canonical_remote_address(address)
    wanted_id = ids.base_id_for_remote(address)
    for entry in machine.load_machine_state_raw().joined:
        if entry.get("base_id") == wanted_id:
            return entry.get("root")
        remote = entry.get("remote")
        try:
            if remote and ids.canonical_remote_address(remote) == wanted:
                return entry.get("root")
        except ValueError:
            continue
    return None


def place_parent(address_text: str) -> str:
    """The folder a base at this address goes in, unchecked: for naming it back."""
    address = backup.parse_address(address_text)
    return os.path.join(location.home_path(), constants.BASES_FOLDER_NAME, _name_of(address))


def place_for(address_text: str, runner: Optional[GitRunner] = None) -> Place:
    """Where the base at this address would go on this computer, checked."""
    address = backup.parse_address(address_text)
    try:
        name = location.validate_company_name(_name_of(address)[: constants.COMPANY_NAME_MAX + 1])
    except LocationError:
        raise _refuse(CODE_BAD_NAME)
    parent = os.path.join(location.home_path(), constants.BASES_FOLDER_NAME, name)
    target = os.path.join(parent, constants.BASE_FOLDER_NAME)
    if os.path.lexists(parent):
        raise _refuse(CODE_FOLDER_TAKEN)
    try:
        location.check_parent(parent, runner=runner_or_default(runner))
    except LocationError:
        raise _refuse(CODE_BAD_PLACE)
    return Place(address, name, parent, target, ids.base_id_for_remote(address))


def _check_repository(git: GitRunner, address: str) -> None:
    """Readable with this computer's own sign-in, private, and not empty."""
    listed = git.run(["ls-remote", "--heads", address], cwd=location.home_path(), timeout=60)
    if not listed.ok:
        raise _refuse(CODE_CANNOT_REACH)
    if backup.readable_without_sign_in(git, location.home_path(), address):
        raise _refuse(CODE_PUBLIC)
    if not listed.out().strip():
        raise _refuse(CODE_EMPTY)


def review(address_text: str, runner: Optional[GitRunner] = None) -> Place:
    """Check the address and the place, and write nothing at all."""
    git = runner_or_default(runner)
    address = backup.parse_address(address_text)
    if already_here(address):
        raise _refuse(CODE_ALREADY_HERE)
    found = place_for(address, runner=git)
    _check_repository(git, address)
    return found


def _shared_branch(git: GitRunner, folder: str) -> Optional[str]:
    """The line of work the shared copy names as its own, read from it."""
    found = git.run(["ls-remote", "--symref", "origin", "HEAD"], cwd=folder, timeout=60)
    if found.ok:
        for line in found.out().splitlines():
            if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
                name = line[len("ref: refs/heads/") : -len("\tHEAD")]
                if name in ("main", "master"):
                    return name
    for name in ("main", "master"):
        if git.run(
            ["rev-parse", "--verify", "--quiet", "refs/remotes/origin/%s^{commit}" % name],
            cwd=folder,
        ).ok:
            return name
    return None


def _saved_files_are_plain(git: GitRunner, folder: str, ref: str) -> bool:
    """Whether every saved file is a plain file, read before any is written."""
    listed = git.run(["ls-tree", "-r", "-z", "--full-tree", ref], cwd=folder, timeout=60)
    if not listed.ok:
        return False
    names: List[str] = []
    for record in listed.stdout.split("\0"):
        if not record:
            continue
        head, _tab, name = record.partition("\t")
        settings = head.split()
        if len(settings) < 3 or settings[0] not in _FILE_MODES or settings[1] != "blob":
            return False
        names.append(name)
    present = set(names)
    return all(marker in present for marker in (
        constants.MAP_PATH,
        constants.CODEOWNERS_PATH,
        constants.ALLOWLIST_PATH,
    ))


def _remove_half_built(partial: str, parent: str, made_parent: bool) -> None:
    """Take away the half built copy, and the folder made for it when empty."""
    name = os.path.basename(partial.rstrip(os.sep))
    if (
        name.startswith(constants.PARTIAL_FOLDER_PREFIX)
        and os.path.dirname(partial) == parent
        and os.path.isdir(partial)
        and not os.path.islink(partial)
    ):
        shutil.rmtree(partial, ignore_errors=True)
    if made_parent:
        try:
            os.rmdir(parent)
        except OSError:
            pass


def _copy(git: GitRunner, partial: str, address: str) -> str:
    """Copy the shared copy into the half built folder. Returns its branch."""
    if not git.run(["init", "-q", "-b", "main"], cwd=partial).ok:
        raise _refuse(CODE_COPY_FAILED)
    # A link stays a plain file in this copy whatever a later update carries,
    # so a name in the base can never stand for a file elsewhere on this
    # computer. The update at session start refuses links on its own as well.
    for setting in (("core.symlinks", "false"), ("core.fsmonitor", "false")):
        if not git.run(["config", "--local", setting[0], setting[1]], cwd=partial).ok:
            raise _refuse(CODE_COPY_FAILED)
    if not git.run(["remote", "add", "origin", address], cwd=partial).ok:
        raise _refuse(CODE_COPY_FAILED)
    fetched = git.run(
        ["fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "origin"],
        cwd=partial,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    if not fetched.ok:
        raise _refuse(CODE_COPY_FAILED)
    branch = _shared_branch(git, partial)
    if branch is None:
        raise _refuse(CODE_EMPTY)
    shared = "refs/remotes/origin/%s" % branch
    if not _saved_files_are_plain(git, partial, shared):
        raise _refuse(CODE_NOT_A_BASE)
    checked_out = git.run(
        ["checkout", "-q", "-B", branch, "--track", "origin/%s" % branch],
        cwd=partial,
        timeout=FETCH_TIMEOUT_SECONDS,
    )
    if not checked_out.ok:
        raise _refuse(CODE_COPY_FAILED)
    if not git.run(
        ["symbolic-ref", "refs/remotes/origin/HEAD", shared], cwd=partial
    ).ok:
        raise _refuse(CODE_COPY_FAILED)
    return branch


def _record_who_saves_here(git: GitRunner, folder: str) -> None:
    """Save work in this base under the person's own git name and address.

    A proposal and a recorded change say who wrote them from the base's own
    settings, as a base set up on this computer does. Taken from this person's
    git settings, and left unset when those hold no address, so the step that
    needs one asks for it.
    """
    from . import create_base

    address = create_base.global_email(runner=git)
    if not address or not is_valid_email(address):
        return
    git.run(["config", "--local", "user.email", address], cwd=folder)
    name = create_base.global_name(runner=git)
    if name:
        git.run(["config", "--local", "user.name", name], cwd=folder)


def join(
    address_text: str,
    plugin_root: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> Joined:
    """Copy the base at this address onto this computer as a seat (an approval)."""
    approval.require("join_link.join")
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    found = review(address_text, runner=git)

    made_parent = not os.path.isdir(found.parent)
    os.makedirs(found.parent, exist_ok=True)
    parent = os.path.realpath(found.parent)
    partial = os.path.join(parent, constants.PARTIAL_FOLDER_PREFIX + os.urandom(4).hex())
    os.makedirs(partial, mode=0o700)
    try:
        branch = _copy(git, partial, found.address)
        verdict = trust_surface.check(partial, runner=git)
        if not verdict.ok:
            raise _refuse(CODE_NOT_TRUSTED)
        paths.write_base_id(partial, found.base_id, runner=git)
        _record_who_saves_here(git, partial)
        target = os.path.join(parent, constants.BASE_FOLDER_NAME)
        if os.path.lexists(target):
            raise _refuse(CODE_FOLDER_TAKEN)
        os.rename(partial, target)
    except GtmBaseError:
        _remove_half_built(partial, parent, made_parent)
        raise
    except Exception:
        _remove_half_built(partial, parent, made_parent)
        raise _refuse(CODE_COPY_FAILED)

    # From here the base is on this computer. Nothing below removes it, and a
    # step below that fails is put right by the next session start.
    try:
        machine.append_joined(root=target, base_id=found.base_id, remote=found.address, runner=git)
    except GtmBaseError:
        pass
    try:
        machine.record_offer_answer("join")
    except GtmBaseError:
        pass
    hook_code, _folder = install_git_hook.install(target, plugin_root, git, found.base_id)
    state.update_seat(
        found.base_id,
        client="claude",
        joined_from={"address": found.address, "joined_at": state.iso_utc(moment)},
    )
    return Joined(target, found.base_id, found.address, branch, hook_code)


def joined_address(base_id: str) -> Optional[str]:
    """The GitHub repository this seat was joined from, or None.

    Only ever a plain GitHub repository address, whoever wrote the record.
    """
    try:
        seat, _problems = state.load_seat(base_id)
    except Exception:
        return None
    record = seat.get("joined_from")
    if not isinstance(record, dict):
        return None
    address = record.get("address")
    try:
        if not isinstance(address, str) or backup.parse_address(address) != address:
            return None
    except GtmBaseError:
        return None
    return address


def describe(found: Place) -> List[str]:
    """The review as plain sentences for the person; the paths go on lines of their own."""
    return [
        "This computer's own GitHub sign-in can read that repository, and it is private.",
        "Joining copies the base into a new folder kept for bases inside your home folder, on the folder line below, and makes this computer a seat on it.",
        "Everything copied is read before it is kept, and anything a company base never holds stops the join and is removed.",
        "Nothing is sent anywhere. From then on, any change you make to the base goes to its owner as a proposal, and nothing changes in the shared base until they accept it.",
    ]
