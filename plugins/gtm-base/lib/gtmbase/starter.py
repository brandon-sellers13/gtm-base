"""The skills GTM Base ships, and how one reaches a base (Track 4, Unit T4.8).

A shipped skill is written in the plugin under `starter/skills/<job>/`, with
its standard at `starter/standards/<job>.md`. It reaches a base exactly as a
company's own skill does, and through nothing new: the skill folder through
the install operation of Plan 1 Unit 4.2b (the contract check first, the
creator's yes and the base owner's or an administrator's), and its standard
through the create operation of Unit 4.2a (written only where the base holds
no standard for that job yet, owned by whoever approves it). From then on the
company owns both, and changes them the way it changes anything else.

Preparing never writes into the base. It hands back what each approval shows.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from . import constants, operations, skill_install
from .errors import GtmBaseError
from .fsutil import read_bytes
from .gitcmd import GitRunner

_PLUGIN_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
STARTER_DIR = os.path.join(_PLUGIN_ROOT, "starter")

# Each shipped skill, the words it is called by, and the documents a base has
# to hold before it is offered: the ones the skill cannot run without.
DRIFT_GRADE = "drift-grade"
STARTER_SKILLS: Dict[str, tuple] = {
    DRIFT_GRADE: ("drift grade", ("context/icps.md", "context/positioning.md")),
}

CODE_NOT_A_STARTER = "not-a-starter"

NOT_A_STARTER = (
    "GTM Base does not ship a skill by that name, so nothing was prepared."
)
STANDARD_KEPT = (
    "Your base already holds a standard for this job, so it is kept exactly "
    "as it is and only the skill is prepared."
)
OFFER = (
    "Your base holds a customer profile and a positioning, so it can take the "
    "%s skill that comes with GTM Base, which checks a piece of marketing work "
    "against them. Say \"install %s\" when you want it."
)


class Prepared(object):
    """What each approval shows: the standard's creation, when there is one, and the skill."""

    def __init__(self, standard, skill):
        self.standard = standard
        self.skill = skill


def skill_folder(skill: str) -> Optional[str]:
    """The folder a shipped skill is written in, or None when GTM Base ships no such skill."""
    if skill not in STARTER_SKILLS:
        return None
    folder = os.path.join(STARTER_DIR, constants.SKILLS_DIR, skill)
    return folder if os.path.isdir(folder) else None


def standard_path(skill: str) -> str:
    return "%s/%s.md" % (constants.STANDARDS_DIR, skill)


def standard_text(skill: str) -> Optional[str]:
    data = read_bytes(os.path.join(STARTER_DIR, standard_path(skill).replace("/", os.sep)))
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def offered(base_root: str) -> List[str]:
    """The shipped skills this base could take: it holds what each needs, and not the skill."""
    found: List[str] = []
    for skill, (_said, needs) in STARTER_SKILLS.items():
        if os.path.lexists(os.path.join(base_root, constants.SKILLS_DIR, skill)):
            continue
        if all(os.path.isfile(os.path.join(base_root, *path.split("/"))) for path in needs):
            found.append(skill)
    return found


def offer_sentences(base_root: str) -> List[str]:
    return [
        OFFER % (STARTER_SKILLS[skill][0], STARTER_SKILLS[skill][0])
        for skill in offered(base_root)
    ]


def prepare(
    base_root: str,
    base_id: str,
    skill: str,
    reason: str,
    runner: Optional[GitRunner] = None,
) -> Prepared:
    """Prepare a shipped skill, and its standard when the base has none, to be shown.

    The skill is prepared first, so its contract check runs before anything
    else is kept on this computer.
    """
    folder = skill_folder(skill)
    text = standard_text(skill)
    if folder is None or text is None:
        raise GtmBaseError(NOT_A_STARTER, code=CODE_NOT_A_STARTER)
    files = skill_install.files_from_folder(folder, skill)
    prepared_skill = skill_install.prepare(base_root, base_id, skill, files, reason, runner_=runner)
    try:
        prepared_standard = operations.prepare_creation(
            base_root, base_id, [(standard_path(skill), text)], reason, runner=runner
        )
    except operations.Refused as refusal:
        if refusal.code != operations.CODE_ALREADY_THERE:
            raise
        prepared_standard = None
    return Prepared(prepared_standard, prepared_skill)
