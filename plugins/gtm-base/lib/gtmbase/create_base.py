"""Turning the first approved file into a base the person owns.

Everything is built in a half built folder beside where the base is going, and
the single rename of that folder to `gtm-base` is the moment the base exists.
Nothing before the rename can leave a folder that another part of the plugin
would treat as a base, and nothing after it can undo a base that is already
there. That one rename is why this module exists at all.

The approved draft is never lost. It is handed in, it is written into the half
built folder, and on any failure before the rename the half built folder is
left exactly where it is and `CreateFailed` names it, so the skill still holds
the text and can offer it again.

The recovery table lives at the bottom of this file, one function per state a
run can stop in.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
from typing import List, Optional

from . import (
    confirm,
    constants,
    formats,
    ids,
    install_git_hook,
    location,
    machine,
    paths,
    state,
)
from .errors import CreateFailed, GtmBaseError, IdentityNeeded, ValidationError
from .gitcmd import GitRunner, runner_or_default
from .validate import is_valid_email

# The name saved work is recorded under when neither the machine nor the
# company gives one.
DEFAULT_AUTHOR_NAME = constants.COMMIT_AUTHOR_FALLBACK_NAME

# What can go wrong while the half built folder is being filled.
CODE_NO_TEMPLATE = "template-missing"
CODE_BAD_EMAIL = "bad-email"
CODE_NO_OWNER_FIELD = "approved-file-has-no-owner"
CODE_APPROVED_FILE_MALFORMED = "approved-file-malformed"
CODE_GIT_FAILED = "git-failed"
CODE_CONFIRMATION_REFUSED = "confirmation-refused"
CODE_RENAME_FAILED = "rename-failed"

# The answer the offer records the moment a base exists.
OFFER_ANSWER_SET_UP = "set-up"

# What `repair` did.
CODE_HOOK_INSTALLED = "hook-installed"
CODE_NOTHING_TO_REPAIR = "nothing-to-repair"


class ApprovedFile(object):
    """The first file the person said yes to, and where it belongs."""

    __slots__ = ("path", "text")

    def __init__(self, path: str, text: str):
        self.path = path
        self.text = text

    def __repr__(self) -> str:
        return "ApprovedFile(path=%r)" % (self.path,)


class CreateResult(object):
    """What a finished base is: where it is, what it is called, who owns it."""

    __slots__ = ("root", "base_id", "email", "codes")

    def __init__(self, root, base_id, email, codes=None):
        self.root = root
        self.base_id = base_id
        self.email = email
        self.codes: List[str] = list(codes or [])

    def __repr__(self) -> str:
        return "CreateResult(root=%r, base_id=%r)" % (self.root, self.base_id)


# --- Finding the template ----------------------------------------------------


def template_root(plugin_root: str) -> str:
    """The folder holding the files every new base starts with.

    The plugin ships its own copy at `templates/company-base` inside itself,
    and that copy is the one used when a base is built, because an installed
    plugin is fetched as the `plugins/gtm-base` folder on its own and the
    repository's copy two levels above it is not there. The repository's copy
    is kept as the one a person edits, and a test holds the two identical.
    """
    inside = os.path.join(plugin_root, "templates", "company-base")
    if os.path.isdir(inside):
        return inside
    repository = os.path.join(plugin_root, "..", "..", "templates", "company-base")
    repository = os.path.abspath(repository)
    if os.path.isdir(repository):
        return repository
    raise CreateFailed(CODE_NO_TEMPLATE, None)


# --- The identity that owns the base -----------------------------------------


def global_email(runner: Optional[GitRunner] = None) -> Optional[str]:
    """The address this machine already puts on saved work, if it has one."""
    result = runner_or_default(runner).run(["config", "--global", "--get", "user.email"])
    if not result.ok:
        return None
    value = result.out()
    return value or None


def global_name(runner: Optional[GitRunner] = None) -> Optional[str]:
    """The name this machine already puts on saved work, if it has one."""
    result = runner_or_default(runner).run(["config", "--global", "--get", "user.name"])
    if not result.ok:
        return None
    value = result.out()
    return value or None


def resolve_email(email: Optional[str], runner: Optional[GitRunner] = None) -> str:
    """The address that will own this base, or a request to ask the person.

    This runs before anything is built, so a machine with no address at all
    leaves nothing behind on disk for the person to wonder about.
    """
    candidate = email if email else global_email(runner)
    if not candidate:
        raise IdentityNeeded(
            "no work email address is recorded on this computer",
            code="identity-needed",
        )
    if not is_valid_email(candidate):
        raise IdentityNeeded(
            "that is not one plain email address", code=CODE_BAD_EMAIL
        )
    return candidate


# --- Filling the half built folder -------------------------------------------


def _settings_text() -> str:
    """The two settings a base carries, and nothing else.

    The pinned identifier is a placeholder until the release step replaces it
    with a real one. A second person joining a base whose settings still carry
    the placeholder would install nothing.
    """
    payload = {
        "extraKnownMarketplaces": {
            constants.MARKETPLACE_NAME: {
                "source": {
                    "source": "github",
                    "repo": constants.MARKETPLACE_REPO,
                    "sha": constants.PINNED_SHA_PLACEHOLDER,
                }
            }
        },
        "enabledPlugins": {constants.PLUGIN_KEY: True},
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _copy_template(source: str, destination: str, email: str) -> None:
    """Copy the template in, putting the owner's own address where it belongs.

    The placeholder address is replaced in the files under `context` and in the
    list of text the outgoing check lets through. Every other file is copied as
    it is, and the empty folders keep their marker files so they survive.
    """
    for folder, _subfolders, filenames in os.walk(source):
        relative = os.path.relpath(folder, source)
        target_folder = (
            destination if relative == "." else os.path.join(destination, relative)
        )
        if not os.path.isdir(target_folder):
            os.makedirs(target_folder)
        for filename in sorted(filenames):
            source_file = os.path.join(folder, filename)
            target_file = os.path.join(target_folder, filename)
            repo_relative = (
                filename if relative == "." else os.path.join(relative, filename)
            )
            repo_relative = repo_relative.replace(os.sep, "/")
            if repo_relative == constants.SETTINGS_PATH:
                continue
            text = _read(source_file)
            if text is None:
                shutil.copyfile(source_file, target_file)
                continue
            if repo_relative.startswith(constants.CONTEXT_DIR + "/"):
                text = text.replace(
                    "owner: " + constants.OWNER_PLACEHOLDER_EMAIL, "owner: " + email
                )
            elif repo_relative == constants.ALLOWLIST_PATH:
                text = text.replace(constants.OWNER_PLACEHOLDER_EMAIL, email)
            _write(target_file, text)

    for name in constants.TEMPLATE_TREE_DIRS:
        folder = os.path.join(destination, name.replace("/", os.sep))
        if not os.path.isdir(folder):
            os.makedirs(folder)
    settings = os.path.join(destination, constants.SETTINGS_PATH.replace("/", os.sep))
    _write(settings, _settings_text())


def _read(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def _write(path: str, text: str) -> str:
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def stamp_owner(text: str, email: str) -> str:
    """Put the owner's own address on an approved draft.

    A draft with no owner setting is refused rather than given one, because a
    file whose shape we do not recognise is not a file we may rewrite.
    """
    block, body = formats.split_document(text)
    fields = formats.parse_frontmatter(block)
    if "owner" not in fields:
        raise ValidationError(
            "this draft has no owner setting", code=CODE_NO_OWNER_FIELD
        )
    fields["owner"] = email
    return formats.render_document(fields, body)


# --- Building a base ---------------------------------------------------------


def create(
    parent: str,
    approved_file: ApprovedFile,
    run_id: str,
    plugin_root: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    confirmed_home: bool = False,
) -> CreateResult:
    """Build a base from one approved file, and join this account to it.

    The order matters and is the whole design. Everything is built in a folder
    named `gtm-base.partial-<random>` beside where the base is going; the
    rename of that folder is the moment the base exists; the account's record
    and the safeguard git runs follow it. A failure before the rename leaves
    the half built folder alone and raises `CreateFailed` naming it.

    The folder the base is going into is checked here as well as when it was
    proposed. A place is proposed at one moment and approved at another, and
    the rules about where a base may go have to hold at the moment it is built
    rather than at the moment somebody suggested it.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    ids.check_run_id(run_id)

    # Asked and answered before anything is built, so a machine with no
    # address on it leaves no folder behind for the person to wonder about.
    address = resolve_email(email, runner=git)
    template = template_root(plugin_root)

    remove_stale_seat_dirs(machine.load_machine_state_raw(), runner=git)

    parent_folder = os.path.realpath(os.path.abspath(os.path.expanduser(parent)))
    location.check_parent(parent_folder, confirmed_home)
    if not os.path.isdir(parent_folder):
        os.makedirs(parent_folder)
        parent_folder = os.path.realpath(parent_folder)
    target = os.path.join(parent_folder, constants.BASE_FOLDER_NAME)
    if os.path.lexists(target):
        raise CreateFailed("target-exists", None)

    partial = os.path.join(
        parent_folder, constants.PARTIAL_FOLDER_PREFIX + os.urandom(4).hex()
    )
    os.makedirs(partial)

    base_id = _fill_partial(
        partial, template, address, name, approved_file, run_id, moment, git
    )

    try:
        os.rename(partial, target)
    except OSError:
        raise CreateFailed(CODE_RENAME_FAILED, partial)

    # From here the base exists. Nothing below is allowed to delete it, and a
    # failure below is repaired on the next run rather than undone.
    machine.append_joined(root=target, base_id=base_id, remote=None)
    # The answer to the offer is recorded here, at the moment the base exists,
    # rather than at the closing. A person who approves their first document
    # and then closes the window has set a base up, and the offer must not come
    # back at them the next morning asking whether they would like to.
    try:
        machine.record_offer_answer(OFFER_ANSWER_SET_UP)
    except GtmBaseError:
        pass
    codes: List[str] = []
    hook_code, _folder = install_git_hook.install(target, plugin_root, git, base_id)
    codes.append(hook_code)
    state.update_seat(base_id, first_push_reviewed=False, client="claude")
    return CreateResult(target, base_id, address, codes)


def _fill_partial(
    partial: str,
    template: str,
    address: str,
    name: Optional[str],
    approved_file: ApprovedFile,
    run_id: str,
    moment: datetime.datetime,
    git: GitRunner,
) -> str:
    """Everything that happens inside the half built folder, in order."""
    try:
        git.check(["init", "-b", "main", "-q"], cwd=partial)
    except GtmBaseError:
        raise CreateFailed(CODE_GIT_FAILED, partial)

    try:
        git.check(["config", "--local", "user.email", address], cwd=partial)
        author = name or global_name(git) or DEFAULT_AUTHOR_NAME
        git.check(["config", "--local", "user.name", author], cwd=partial)
    except GtmBaseError:
        raise CreateFailed(CODE_GIT_FAILED, partial)

    base_id = ids.base_id_random()
    try:
        paths.write_base_id(partial, base_id, runner=git)
    except GtmBaseError:
        raise CreateFailed(CODE_GIT_FAILED, partial)

    try:
        _copy_template(template, partial, address)
    except OSError:
        raise CreateFailed(CODE_NO_TEMPLATE, partial)

    try:
        stamped = stamp_owner(approved_file.text, address)
    except ValidationError as failure:
        raise CreateFailed(failure.code or CODE_APPROVED_FILE_MALFORMED, partial)
    relative = approved_file.path.replace("/", os.sep)
    _write(os.path.join(partial, relative), stamped)

    try:
        git.check(["add", "--", approved_file.path], cwd=partial)
    except GtmBaseError:
        raise CreateFailed(CODE_GIT_FAILED, partial)

    result = confirm.drafted(
        partial, base_id, approved_file.path, run_id, now=moment, runner=git
    )
    if result.status != confirm.STATUS_RECORDED:
        raise CreateFailed(
            (result.codes or [CODE_CONFIRMATION_REFUSED])[0], partial
        )

    try:
        git.check(["add", "-A"], cwd=partial)
        git.check(["commit", "-q", "-m", constants.FIRST_COMMIT_MESSAGE], cwd=partial)
    except GtmBaseError:
        raise CreateFailed(CODE_GIT_FAILED, partial)
    return base_id


# --- The recovery table ------------------------------------------------------
#
# A run can stop in four places, and each one has a rule.
#
# Before the rename. A `gtm-base.partial-*` folder is never a base, whatever is
# inside it. `find_partial_folders` lists them and `remove_partial` deletes one
# once the person has been asked.
#
# After the rename, before the account's record. The folder is a base and it
# carries its identifier, so the session start hook sees a folder shaped like a
# base and asks its own question about it. Nothing is done here.
#
# After the record, before the safeguard git runs. `repair` puts the safeguard
# in place.
#
# A seat folder for a base whose folder never got its first piece of work saved
# is left over from a run that stopped early. `remove_stale_seat_dirs` clears
# them, and a base build calls it before it starts.


def find_partial_folders(parent: str) -> List[str]:
    """Every half built base folder sitting in this folder."""
    folder = os.path.abspath(os.path.expanduser(parent))
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    found = []
    for name in sorted(names):
        if not name.startswith(constants.PARTIAL_FOLDER_PREFIX):
            continue
        path = os.path.join(folder, name)
        if os.path.isdir(path) and not os.path.islink(path):
            found.append(path)
    return found


def remove_partial(path: str, parent: Optional[str] = None) -> bool:
    """Delete one half built base folder, and refuse to delete anything else.

    The name has to be a half built base name, and when a folder is named the
    path has to sit directly inside it. Ask the person first: this deletes what
    a run that stopped early left behind, and it never comes back.
    """
    candidate = os.path.abspath(os.path.expanduser(path))
    name = os.path.basename(candidate.rstrip(os.sep))
    if not name.startswith(constants.PARTIAL_FOLDER_PREFIX):
        raise CreateFailed("not-a-partial-folder", candidate)
    if parent is not None:
        expected = os.path.abspath(os.path.expanduser(parent))
        if os.path.dirname(candidate.rstrip(os.sep)) != expected:
            raise CreateFailed("not-in-that-folder", candidate)
    if os.path.islink(candidate) or not os.path.isdir(candidate):
        return False
    shutil.rmtree(candidate)
    return True


def repair(
    root: str, plugin_root: str, runner: Optional[GitRunner] = None
) -> List[str]:
    """Finish a base whose build stopped after the folder was already there.

    The only state this can fix is a base the account has a record of with no
    safeguard installed. A folder with saved work but no record is left to the
    question the session start hook asks about a folder shaped like a base,
    because adopting a folder without asking is exactly what that question is
    there to prevent.
    """
    git = runner_or_default(runner)
    base_root = os.path.abspath(os.path.expanduser(root))
    machine_state = machine.load_machine_state(runner=git)
    entry = machine.find_joined_by_root(machine_state, base_root)
    if entry is None:
        return [CODE_NOTHING_TO_REPAIR]
    seat, _problems = state.load_seat(entry["base_id"])
    if seat.get("git_hook_installed"):
        return [CODE_NOTHING_TO_REPAIR]
    code, _folder = install_git_hook.install(
        base_root, plugin_root, git, entry["base_id"]
    )
    return [CODE_HOOK_INSTALLED, code]


def remove_stale_seat_dirs(machine_state, runner: Optional[GitRunner] = None) -> List[str]:
    """Delete the seat folders of bases whose folder never got that far.

    A base folder with nothing saved in it yet was never finished, so what this
    seat remembers about it is about nothing. Only folders directly inside the
    seat's own bases folder are ever deleted.

    A folder that is not on this computer right now is left alone rather than
    treated as unfinished, because a base on a drive that is unplugged looks
    exactly like a base that was never built.
    """
    git = runner_or_default(runner)
    bases = paths.bases_dir()
    removed: List[str] = []
    for entry in list(getattr(machine_state, "joined", None) or []):
        root = entry.get("root") if isinstance(entry, dict) else None
        base_id = entry.get("base_id") if isinstance(entry, dict) else None
        if not root or not ids.is_base_id(base_id):
            continue
        if not os.path.isdir(root):
            continue
        if os.path.exists(os.path.join(root, ".git")):
            if git.run(["rev-parse", "--verify", "--quiet", "HEAD"], cwd=root).ok:
                continue
        folder = os.path.join(bases, base_id)
        if not os.path.isdir(folder) or os.path.islink(folder):
            continue
        if os.path.dirname(os.path.abspath(folder)) != os.path.abspath(bases):
            continue
        shutil.rmtree(folder)
        removed.append(base_id)
    return removed
