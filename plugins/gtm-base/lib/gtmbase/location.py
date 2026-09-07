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

# The person named a folder that already holds their marketing material.
REASON_BESIDE_CONTENT = "beside-your-content"
# Nothing was named, or what was named could not hold the base, so the base
# goes in a folder named for the company inside the person's home folder.
REASON_HOME_FOLDER = "home-folder"

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

# The characters that turn a name into a path, whatever the computer.
NAME_SEPARATORS = ("/", "\\", ":")


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

    __slots__ = ("target_path", "parent", "reason_code", "warning_code")

    def __init__(self, target_path, parent, reason_code, warning_code=None):
        self.target_path = target_path
        self.parent = parent
        self.reason_code = reason_code
        self.warning_code = warning_code

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


def check_parent(parent: str, confirmed_home: bool = False) -> None:
    """Refuse a parent folder a base may never be built in.

    This runs twice on purpose. Once when the place is proposed, so the
    person is never shown a folder a base may not go in, and once again at
    the moment the base is built, because everything the first check looked
    at could have changed between the proposal and the yes.
    """
    home = home_path()
    real_parent = os.path.realpath(parent) if os.path.exists(parent) else parent
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
    if os.path.lexists(target):
        raise LocationError("there is already something there", code=CODE_TARGET_EXISTS)
    stray = _stray_base_child(real_parent)
    if stray is not None:
        raise LocationError(
            "that folder already holds a folder named like a base",
            code=CODE_STRAY_BASE,
        )


def propose_target(
    cwd: str,
    company_name: str,
    named_content_folder: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    confirmed_home: bool = False,
) -> Proposal:
    """Propose the one place this person's base should go.

    When the person named a folder that holds their marketing material, the
    base goes beside that material, in a folder called `gtm-base` inside it.
    When they named nothing, the folder they are working in counts as the one
    they named as long as it holds something. Otherwise the base goes in a
    folder named for the company inside their home folder.

    A folder already looked after by another tool is never used, because a
    base inside it would be swept up by that tool. In that case the warning is
    reported and the home folder is proposed instead.
    """
    name = validate_company_name(company_name)
    git = runner_or_default(runner)

    holder = None
    if named_content_folder:
        holder = _resolve(named_content_folder)
    elif cwd and _holds_content(_resolve(cwd)):
        holder = _resolve(cwd)

    warning = None
    if holder is not None:
        home = home_path()
        if holder == home or _is_inside(home, holder):
            if not confirmed_home:
                raise LocationError(
                    "that folder is your home folder or holds it",
                    code=CODE_HOME_DIRECTORY,
                )
        elif is_repository(holder, runner=git):
            warning = WARNING_PARENT_IS_REPOSITORY
            holder = None

    if holder is not None:
        parent = holder
        reason = REASON_BESIDE_CONTENT
    else:
        parent = os.path.join(home_path(), name)
        reason = REASON_HOME_FOLDER

    check_parent(parent, confirmed_home)
    target = os.path.join(
        os.path.realpath(parent) if os.path.exists(parent) else parent,
        constants.BASE_FOLDER_NAME,
    )
    return Proposal(target, os.path.dirname(target), reason, warning)


def describe(proposal: Proposal) -> str:
    """One sentence telling the person where their base is about to go."""
    if proposal.warning_code == WARNING_PARENT_IS_REPOSITORY:
        return (
            "Your base will go in a new folder at %s, because the folder you "
            "named is already looked after by another tool and a base inside "
            "it would be swept up by that tool." % proposal.target_path
        )
    if proposal.reason_code == REASON_HOME_FOLDER:
        return (
            "Your base will go in a new folder at %s, which is a folder named "
            "for your company inside your home folder."
            % proposal.target_path
        )
    return (
        "Your base will go in a new folder at %s, beside the material that is "
        "already there, and nothing already there will be changed."
        % proposal.target_path
    )
