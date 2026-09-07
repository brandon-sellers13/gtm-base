"""Where a new base is allowed to go, and what the person is told about it.

Two questions are answered here. Is the name the person gave for their company
a name a folder may safely carry, and which folder should the base go in.

Nothing here writes anything. It proposes a place and it refuses the places a
base must never go, and the skill shows the person the one sentence `describe`
returns before anything is built.
"""

from __future__ import annotations

import os
from typing import Optional

from . import constants, paths
from .errors import LocationError
from .gitcmd import GitRunner, runner_or_default

# --- Why a place was proposed ------------------------------------------------

# The person asked for the base to go beside their material, and the folder
# they named passed every check.
REASON_BESIDE_CONTENT = "beside-your-content"
# Nothing was named, or what was named could not hold the base, so the base
# goes in a folder named for the company inside the person's home folder.
REASON_HOME_FOLDER = "home-folder"

# Where every base goes unless the person asks for somewhere else: a folder
# kept for bases alone inside the home folder, with one folder per company.
REASON_BASES_FOLDER = "bases-folder"

# --- What the person is warned about -----------------------------------------

# The folder they named is already looked after by another tool.
WARNING_PARENT_IS_REPOSITORY = "parent-is-repository"

# --- Why a place was refused -------------------------------------------------

CODE_EMPTY_NAME = "empty-name"
CODE_LEADING_DOT = "leading-dot"
CODE_PATH_SEPARATOR = "path-separator"
CODE_CLIMBING_NAME = "climbing-name"
CODE_CONTROL_CHARACTER = "control-character"
CODE_LONG_NAME = "long-name"
CODE_TARGET_EXISTS = "target-exists"
CODE_STRAY_BASE = "stray-base"
CODE_HOME_DIRECTORY = "home-directory"
CODE_INSIDE_SEAT_HOME = "inside-seat-home"
CODE_INSIDE_REPOSITORY = "inside-repository"
CODE_SYNCED = "synced-folder"
CODE_SYNC_UNKNOWN = "sync-unknown"
CODE_INSIDE_BASE = "inside-base"
CODE_COMPANY_FOLDER_EXISTS = "company-folder-exists"

# The characters that turn a name into a path, whatever the computer.
NAME_SEPARATORS = ("/", "\\", ":")

# --- Folders another program copies to the internet by itself -----------------
#
# A base holds raw notes and approved company context, and a folder that some
# other program copies off this computer on its own is a folder GTM Base cannot
# make any promise about. It refuses those places rather than warning about
# them, because a warning does not stop an upload.

# Folders under the home folder that Apple's own cloud storage keeps.
SYNCED_HOME_FOLDERS = (
    os.path.join("Library", "Mobile Documents"),
    os.path.join("Library", "CloudStorage"),
)
# The folder Apple's cloud storage puts a person's own documents in.
ICLOUD_MARKER = os.path.join("Library", "Mobile Documents", "com~apple~CloudDocs")
# The setting that says the two folders below are being kept in the cloud.
ICLOUD_DESKTOP_MARKER = "com.apple.icloud.desktop"
# The two folders that setting covers.
ICLOUD_COVERED_FOLDERS = ("Desktop", "Documents")
# The starts of folder names other companies' cloud storage uses.
SYNCED_NAME_PREFIXES = ("Google Drive", "Dropbox", "OneDrive")


def validate_company_name(name) -> str:
    """Return the company name, or refuse it as a name a folder may carry.

    Spaces and ordinary punctuation are kept, because a company is allowed to
    be called what it is called. What is refused is everything that would turn
    the name into a path or into a hidden folder: a name that is empty, one
    that starts with a dot, one holding a slash of either kind or a colon, one
    holding two dots in a row, one holding a control character, and one longer
    than the cap.
    """
    if not isinstance(name, str):
        raise LocationError("a company name is needed", code=CODE_EMPTY_NAME)
    text = name.strip()
    if not text:
        raise LocationError("a company name is needed", code=CODE_EMPTY_NAME)
    for character in text:
        if ord(character) < 32 or ord(character) == 127:
            raise LocationError(
                "that name holds a character a folder may not carry",
                code=CODE_CONTROL_CHARACTER,
            )
    for separator in NAME_SEPARATORS:
        if separator in text:
            raise LocationError(
                "that name holds a character that would turn it into a path",
                code=CODE_PATH_SEPARATOR,
            )
    if ".." in text:
        raise LocationError(
            "that name holds two dots in a row", code=CODE_CLIMBING_NAME
        )
    if text.startswith("."):
        raise LocationError(
            "a name that starts with a dot makes a hidden folder",
            code=CODE_LEADING_DOT,
        )
    if len(text) > constants.COMPANY_NAME_MAX:
        raise LocationError("that name is too long", code=CODE_LONG_NAME)
    return text


class Proposal(object):
    """One place a base could go, and why it was proposed."""

    __slots__ = (
        "target_path",
        "parent",
        "reason_code",
        "warning_code",
        "content_folder",
    )

    def __init__(
        self, target_path, parent, reason_code, warning_code=None, content_folder=None
    ):
        self.target_path = target_path
        self.parent = parent
        self.reason_code = reason_code
        self.warning_code = warning_code
        # The folder the person named as the one their material lives in, when
        # they named one. It is not where the base goes. It is the folder the
        # base will be recorded as belonging with, and the sentence the person
        # reads has to name it, because that is the folder they will open.
        self.content_folder = content_folder

    def __repr__(self) -> str:
        return "Proposal(target_path=%r, reason_code=%r, warning_code=%r)" % (
            self.target_path,
            self.reason_code,
            self.warning_code,
        )


def home_path() -> str:
    return os.path.realpath(os.path.expanduser("~"))


def _resolve(folder: str) -> str:
    return os.path.realpath(os.path.abspath(os.path.expanduser(folder)))


def _is_inside(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def is_repository(folder: str, runner: Optional[GitRunner] = None) -> bool:
    """Whether this folder is already looked after by another tool.

    A folder inside a repository counts as well as the top of one, because a
    base built inside somebody else's repository would be swept up by it.
    """
    if not os.path.isdir(folder):
        return False
    return paths.git_root(folder, runner=runner_or_default(runner)) is not None


def _holds_content(folder: str) -> bool:
    """Whether a folder already has something of the person's in it."""
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    for name in names:
        if name.startswith("."):
            continue
        if name.casefold() == constants.BASE_FOLDER_NAME:
            continue
        return True
    return False


def _stray_base_child(parent: str) -> Optional[str]:
    """A child of the parent named like a base, whatever its letter case."""
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    wanted = constants.BASE_FOLDER_NAME.casefold()
    for name in sorted(names):
        if name.casefold() == wanted:
            return os.path.join(parent, name)
    return None


def _resolved_ancestry(parent: str) -> str:
    """The parent folder with every part of it that exists resolved through links.

    A base is usually built in a folder that is not there yet, and the checks
    below are about where that folder would really end up. So the deepest part
    of the path that does exist is resolved, and the parts that do not exist
    yet are put back on the end of it. Without this a link named halfway up the
    path could put an approved document somewhere the checks never looked.
    """
    absolute = os.path.abspath(os.path.expanduser(parent))
    missing = []
    here = absolute
    while True:
        if os.path.exists(here):
            break
        parent_of = os.path.dirname(here)
        if parent_of == here:
            return absolute
        missing.append(os.path.basename(here))
        here = parent_of
    resolved = os.path.realpath(here)
    for name in reversed(missing):
        resolved = os.path.join(resolved, name)
    return resolved


def _synced_verdict(folder: str) -> Optional[str]:
    """Whether another program keeps this folder in the cloud by itself.

    Nothing comes back when the folder is plainly the person's own. A code
    comes back when the folder is somewhere a cloud program keeps, and a
    different code comes back when the answer cannot be established, because
    "we could not tell" has to reach the person as a question and must never be
    quietly read as "no".
    """
    home = home_path()
    parts = folder.split(os.sep)
    for part in parts:
        for prefix in SYNCED_NAME_PREFIXES:
            if part.casefold().startswith(prefix.casefold()):
                return CODE_SYNCED
    for relative in SYNCED_HOME_FOLDERS:
        kept = os.path.join(home, relative)
        if _is_inside(folder, kept):
            return CODE_SYNCED

    if not os.path.isdir(os.path.join(home, ICLOUD_MARKER)):
        return None
    # Apple's cloud storage is switched on. Whether it covers the two folders
    # below is a separate setting, and the two ways of telling are the folder
    # having been turned into a link and the marker file being in it.
    for name in ICLOUD_COVERED_FOLDERS:
        covered = os.path.join(home, name)
        if not _is_inside(folder, covered) and folder != os.path.realpath(covered):
            continue
        if os.path.islink(covered):
            return CODE_SYNCED
        if os.path.exists(os.path.join(covered, ICLOUD_DESKTOP_MARKER)):
            return CODE_SYNCED
        return CODE_SYNC_UNKNOWN
    return None


def _joined_base_roots() -> list:
    """Every base folder this account has a record of, however it stands today."""
    try:
        from . import machine

        state = machine.load_machine_state_raw()
    except Exception:
        return []
    found = []
    for entry in getattr(state, "joined", None) or []:
        root = entry.get("root") if isinstance(entry, dict) else None
        if not isinstance(root, str):
            continue
        found.append(os.path.realpath(root) if os.path.exists(root) else os.path.abspath(root))
    return found


def check_parent(
    parent: str, confirmed_home: bool = False, runner: Optional[GitRunner] = None
) -> None:
    """Refuse a parent folder a base may never be built in.

    This runs twice on purpose. Once when the place is proposed, so the
    person is never shown a folder a base may not go in, and once again at
    the moment the base is built, because everything the first check looked
    at could have changed between the proposal and the yes. The second run
    happens before the half built folder receives anything the person
    approved, so an approved document never lands somewhere that would then be
    refused.
    """
    home = home_path()
    real_parent = _resolved_ancestry(parent)
    if real_parent == home or _is_inside(home, real_parent):
        if not confirmed_home:
            raise LocationError(
                "that folder is your home folder or holds it",
                code=CODE_HOME_DIRECTORY,
            )
    seat_home = paths.seat_home_path()
    target = os.path.join(real_parent, constants.BASE_FOLDER_NAME)
    if _is_inside(target, seat_home) or _is_inside(real_parent, seat_home):
        raise LocationError(
            "that folder is inside the folder GTM Base keeps for itself",
            code=CODE_INSIDE_SEAT_HOME,
        )
    for root in _joined_base_roots():
        if _is_inside(real_parent, root):
            raise LocationError(
                "that folder is a base or sits inside one", code=CODE_INSIDE_BASE
            )
    synced = _synced_verdict(real_parent)
    if synced == CODE_SYNCED:
        raise LocationError(
            "another program copies that folder off this computer by itself",
            code=CODE_SYNCED,
        )
    if synced == CODE_SYNC_UNKNOWN:
        raise LocationError(
            "we cannot tell whether another program copies that folder off this "
            "computer",
            code=CODE_SYNC_UNKNOWN,
        )
    inside_repository = _first_existing(real_parent)
    if inside_repository is not None and is_repository(
        inside_repository, runner=runner_or_default(runner)
    ):
        raise LocationError(
            "that folder already keeps its own change history",
            code=CODE_INSIDE_REPOSITORY,
        )
    if os.path.lexists(target):
        raise LocationError("there is already something there", code=CODE_TARGET_EXISTS)
    stray = _stray_base_child(real_parent)
    if stray is not None:
        raise LocationError(
            "that folder already holds a folder named like a base",
            code=CODE_STRAY_BASE,
        )


def _first_existing(folder: str) -> Optional[str]:
    """The deepest part of this path that is on the disk right now.

    The check for another tool's change history has to run against a folder
    that exists, and the folder a base is going into usually does not yet, so
    it runs against the nearest folder above it that does.
    """
    here = folder
    while True:
        if os.path.isdir(here):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def propose_target(
    cwd: str,
    company_name: str,
    named_content_folder: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    confirmed_home: bool = False,
    beside: bool = False,
) -> Proposal:
    """Propose the one place this person's base should go.

    Every base goes in a folder kept for bases inside the home folder, one
    folder per company. That is where it goes whatever folder the person is
    working in and whatever folder they named, because a folder somebody
    already works in is a folder some other tool may already be looking after
    and some other program may already be copying to the internet, and a base
    holds raw notes and company context that must not leave this computer on
    its own.

    The base being somewhere else than the material is not a cost the person
    pays, because the base is told which folder it belongs with and opening
    that folder brings it along.

    `beside` is the person asking, in words, for the base to sit beside their
    material instead. Then the folder they named is used, but only if it passes
    every check the central place passes.
    """
    name = validate_company_name(company_name)
    git = runner_or_default(runner)

    if beside:
        holder = _resolve(named_content_folder) if named_content_folder else None
        if holder is None and cwd and _holds_content(_resolve(cwd)):
            holder = _resolve(cwd)
        if holder is None:
            raise LocationError(
                "no folder was named for the base to go beside",
                code=CODE_EMPTY_NAME,
            )
        home = home_path()
        if holder == home or _is_inside(home, holder):
            if not confirmed_home:
                raise LocationError(
                    "that folder is your home folder or holds it",
                    code=CODE_HOME_DIRECTORY,
                )
        check_parent(holder, confirmed_home, runner=git)
        target = os.path.join(
            os.path.realpath(holder) if os.path.exists(holder) else holder,
            constants.BASE_FOLDER_NAME,
        )
        return Proposal(
            target,
            os.path.dirname(target),
            REASON_BESIDE_CONTENT,
            None,
            content_folder=holder,
        )

    parent = os.path.join(home_path(), constants.BASES_FOLDER_NAME, name)
    # A company that already has a folder here already has a base, or had one,
    # and a second base written over the first would be a company's context
    # lost without a word. So the name is sent back for a name that tells the
    # two apart rather than the folder being used again.
    if os.path.lexists(parent):
        raise LocationError(
            "there is already a folder for a company of that name",
            code=CODE_COMPANY_FOLDER_EXISTS,
        )
    check_parent(parent, confirmed_home, runner=git)
    target = os.path.join(
        os.path.realpath(parent) if os.path.exists(parent) else parent,
        constants.BASE_FOLDER_NAME,
    )
    named = _resolve(named_content_folder) if named_content_folder else None
    return Proposal(
        target,
        os.path.dirname(target),
        REASON_BASES_FOLDER,
        None,
        content_folder=named,
    )


def describe(proposal: Proposal) -> str:
    """The sentences telling the person where their base is about to go.

    When they named the folder their material lives in, that folder is named
    back to them here, because it is the folder they will open from then on and
    the base's own folder is not something they should have to remember.
    """
    if proposal.reason_code == REASON_BESIDE_CONTENT:
        return (
            "Your base will go in a new folder at %s, beside the material that "
            "is already there, and nothing already there will be changed."
            % proposal.target_path
        )
    if proposal.content_folder:
        return (
            "Your base will go in a new folder at %s, a folder kept for bases "
            "inside your home folder. To work with it, open Claude Code in the "
            "folder you named, %s, and it will be there. Nothing in the folder "
            "you named will be changed. Is that the right place for it?"
            % (proposal.target_path, proposal.content_folder)
        )
    return (
        "Your base will go in a new folder at %s, a folder kept for bases "
        "inside your home folder. To work with it, open Claude Code in that "
        "folder. Is that the right place for it?" % proposal.target_path
    )
