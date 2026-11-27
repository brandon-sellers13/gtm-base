"""Update GTM Base: the installed version and the one step (Track 4, Unit T4.7).

Two halves. The plugin half reads the version this copy of the plugin says it
is, from its own `plugin.json`, and says it with the one step that updates it.
It makes no network call, so it never claims a newer release exists or does
not (Brandon's call 4 of the Track 4 plan), and it runs nothing: the step is
said, never run.

The base half keeps an existing base current with the plugin. The shapes of
new documents and the skills GTM Base ships live in the plugin, so a base
never receives one by itself. After an update the base is told what it can
now take that it does not hold, each only through an owner-approved creation.
It is read only, so saying it twice says the same thing twice.

People in a Claude chat, Cowork or ChatGPT need neither half, because the
connector serves from the base on every call.
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from . import inventory, names, starter
from .fsutil import read_bytes
from .gitcmd import GitRunner

_PLUGIN_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
PLUGIN_JSON = os.path.join(_PLUGIN_ROOT, ".claude-plugin", "plugin.json")

# The one step, as Claude Code's own documentation gives it, checked on
# 2026-11-27 when this unit was built rather than written from memory
# (code.claude.com/docs/en/plugins/install.md and cli-reference.md). A plugin
# from a marketplace of its own does not refresh by itself, so the listing is
# refreshed first; the new version then loads after `/reload-plugins` in a
# session that is already open, or in the next one.
REFRESH_COMMAND = "claude plugin marketplace update gtm-base"
UPDATE_COMMAND = "claude plugin update gtm-base@gtm-base"
RELOAD_COMMAND = "/reload-plugins"

CODE_VERSION_UNREADABLE = "version-unreadable"

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

INSTALLED = (
    "You have GTM Base %s installed. To update it, run %s and then %s in a "
    "terminal, then %s in any Claude Code session that is open. GTM Base does "
    "not look online, so it cannot say whether a newer version is out."
)
UNREADABLE = (
    "GTM Base could not read which version is installed, so it says nothing "
    "about the version rather than guess. Running %s and then %s in a "
    "terminal, then %s in any Claude Code session that is open, puts the "
    "latest one in place."
)
_STEP = (REFRESH_COMMAND, UPDATE_COMMAND, RELOAD_COMMAND)
CAN_TAKE = (
    "Your base can take these, each written only once you say yes: %s."
)
TAKES_EVERYTHING = (
    "Your base already holds every kind of document and every skill this "
    "version of GTM Base can add."
)


class Update(object):
    """The version this copy says it is, the sentence about it, and a code when it could not be read."""

    def __init__(self, version: Optional[str], code: Optional[str], sentence: str):
        self.version = version
        self.code = code
        self.sentence = sentence


def installed_version(plugin_json: str = PLUGIN_JSON) -> Optional[str]:
    """The version `plugin.json` names, or None when it cannot be read as one."""
    data = read_bytes(plugin_json)
    if data is None:
        return None
    try:
        found = json.loads(data.decode("utf-8")).get("version")
    except (ValueError, UnicodeDecodeError, AttributeError):
        return None
    if not isinstance(found, str) or not _VERSION_RE.match(found.strip()):
        return None
    return found.strip()


def check(plugin_json: str = PLUGIN_JSON) -> Update:
    """The plugin half: the installed version and the one step, or why it cannot say."""
    version = installed_version(plugin_json)
    if version is None:
        return Update(None, CODE_VERSION_UNREADABLE, UNREADABLE % _STEP)
    return Update(version, None, INSTALLED % ((version,) + _STEP))


def _joined(items: List[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def base_can_take(
    base_root: str, base_id: str, runner: Optional[GitRunner] = None
) -> List[str]:
    """The base half: what this base can now take and does not hold, by name.

    Each kind the plugin can draft that the base is missing, then each skill
    GTM Base ships that the base could take. Nothing is written.
    """
    found = inventory.take(base_root, base_id, runner=runner)
    said: List[str] = []
    for kind, _column in found.draftable_missing:
        name = names.KIND_IN_A_SENTENCE[kind]
        if name not in said:
            said.append(name)
    for skill in starter.offered(base_root):
        said.append("the %s skill" % starter.STARTER_SKILLS[skill][0])
    return said


def sentence_for(items: List[str]) -> str:
    """What is said about what a base can take: fixed names, never a file's."""
    return CAN_TAKE % _joined(items) if items else TAKES_EVERYTHING


def base_sentence(base_root: str, base_id: str, runner: Optional[GitRunner] = None) -> str:
    return sentence_for(base_can_take(base_root, base_id, runner=runner))
