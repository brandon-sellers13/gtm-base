"""Whether a folder may be trusted as a base before anything acts on it.

Trusting a folder is what turns a pile of files into something the plugin
reads, updates, and installs a safeguard into, so the whole surface is checked
first and not one file at the top of it. Two things are checked. The settings
file that installs and pins the plugin has to hold exactly what the template
ships and nothing else. And the whole tree has to be free of the files that
would make opening the folder run something: instruction files any assistant
loads on its own, agent folders, code files, a folder of plugins, and links
that point somewhere else.

Every name is compared after case folding and after Unicode composition, so a
folder that reads as `.Claude` on a Mac and a name written with its accents
taken apart are both compared as the one name a person meant.

Nothing here writes anything, and nothing here follows a link.
"""

from __future__ import annotations

import json
import os
import unicodedata
from typing import Iterable, Optional, Sequence, Set

from . import constants
from .gitcmd import GitRunner, runner_or_default

# How long any single git call inside the check may take.
GIT_TIMEOUT_SECONDS = 5

# --- The codes this check reports -------------------------------------------

# The settings file that installs and pins the plugin is not there at all.
CODE_SETTINGS_MISSING = "settings-missing"
# The settings name is there but it is a link or not a file.
CODE_SETTINGS_NOT_A_FILE = "settings-not-a-file"
# The settings file could not be read as the kind of file it claims to be.
CODE_SETTINGS_MALFORMED = "settings-malformed"
# The settings file holds a key beyond the two the template ships, or misses one.
CODE_SETTINGS_KEYS = "settings-keys"
# The place the plugin is installed from is not the one this plugin ships from.
CODE_MARKETPLACE_SOURCE = "marketplace-source"
# The repository named there is not the GTM Base repository.
CODE_MARKETPLACE_REPO = "marketplace-repo"
# The pin is not one exact forty character version name.
CODE_MARKETPLACE_SHA = "marketplace-sha"
# The plugin the settings file turns on is not this plugin.
CODE_PLUGIN_KEY = "plugin-key"
# The tree holds a file an assistant would read as instructions.
CODE_INSTRUCTION_FILE = "instruction-file"
# The tree holds a folder another agent tool reads its settings from.
CODE_AGENT_FOLDER = "agent-folder"
# The tree holds a file that would attach an outside tool server.
CODE_MCP_FILE = "mcp-file"
# The tree holds a file that changes how the shared files themselves behave.
CODE_GIT_SETTINGS_FILE = "git-settings-file"
# The tree holds a folder of plugins.
CODE_PLUGINS_FOLDER = "plugins-folder"
# The tree holds a code file.
CODE_CODE_FILE = "code-file"
# The tree holds something under the settings folder other than the settings file.
CODE_CLAUDE_FOLDER_ENTRY = "claude-folder-entry"
# The tree holds a link, anywhere.
CODE_SYMLINK = "symlink"
# The map is a link, or is not a file.
CODE_MAP_NOT_A_FILE = "map-not-a-file"
# The tree is larger than this check will walk, so the folder is refused.
CODE_TREE_TOO_LARGE = "tree-too-large"
# The tree could not be listed, so nothing about it can be promised.
CODE_TREE_UNREADABLE = "tree-unreadable"

# What each refused name in the shared list is refused for.
_NAME_CODES = {
    "claude.md": CODE_INSTRUCTION_FILE,
    "agents.md": CODE_INSTRUCTION_FILE,
    ".codex": CODE_AGENT_FOLDER,
    ".agents": CODE_AGENT_FOLDER,
    ".mcp.json": CODE_MCP_FILE,
    ".gitmodules": CODE_GIT_SETTINGS_FILE,
    ".gitattributes": CODE_GIT_SETTINGS_FILE,
    "plugins": CODE_PLUGINS_FOLDER,
}

# The folder the settings file lives in, and the one name allowed inside it.
CLAUDE_DIR = ".claude"

_SHA_CHARACTERS = set("0123456789abcdef")


class TrustResult(object):
    """Whether the folder may be trusted, and every reason it may not be."""

    __slots__ = ("ok", "codes")

    def __init__(self, ok: bool, codes: Optional[Sequence[str]] = None):
        self.ok = bool(ok)
        self.codes = list(codes or [])

    def __repr__(self) -> str:
        return "TrustResult(ok=%r, codes=%r)" % (self.ok, self.codes)


def normalize_component(name) -> str:
    """One name written the single way every comparison here uses.

    Composition runs first so that a name whose accents are stored apart from
    their letters becomes the same text as the name written whole, then case is
    folded, then composition runs again because folding can take a composed
    letter apart.
    """
    text = unicodedata.normalize("NFC", str(name))
    return unicodedata.normalize("NFC", text.casefold())


def _is_forty_hex(value) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(character in _SHA_CHARACTERS for character in value)


def _settings_codes(root: str) -> Set[str]:
    """Check the file that installs and pins the plugin for a whole team."""
    codes: Set[str] = set()
    path = os.path.join(root, constants.SETTINGS_PATH)
    if not os.path.lexists(path):
        codes.add(CODE_SETTINGS_MISSING)
        return codes
    if os.path.islink(path) or not os.path.isfile(path):
        codes.add(CODE_SETTINGS_NOT_A_FILE)
        return codes
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, UnicodeDecodeError):
        codes.add(CODE_SETTINGS_MALFORMED)
        return codes
    if not isinstance(payload, dict):
        codes.add(CODE_SETTINGS_MALFORMED)
        return codes
    if set(payload.keys()) != {"extraKnownMarketplaces", "enabledPlugins"}:
        codes.add(CODE_SETTINGS_KEYS)

    marketplaces = payload.get("extraKnownMarketplaces")
    entry = marketplaces.get(constants.MARKETPLACE_NAME) if isinstance(marketplaces, dict) else None
    source = entry.get("source") if isinstance(entry, dict) else None
    if not isinstance(source, dict):
        codes.add(CODE_MARKETPLACE_SOURCE)
    else:
        if source.get("source") != "github":
            codes.add(CODE_MARKETPLACE_SOURCE)
        if source.get("repo") != constants.MARKETPLACE_REPO:
            codes.add(CODE_MARKETPLACE_REPO)
        if not _is_forty_hex(source.get("sha")):
            codes.add(CODE_MARKETPLACE_SHA)

    if payload.get("enabledPlugins") != {constants.PLUGIN_KEY: True}:
        codes.add(CODE_PLUGIN_KEY)
    return codes


def _component_codes(parts: Sequence[str], is_dir: bool) -> Set[str]:
    """Every reason one path inside the tree is not allowed to be there."""
    codes: Set[str] = set()
    normalized = [normalize_component(part) for part in parts]
    for position, part in enumerate(normalized):
        code = _NAME_CODES.get(part)
        if code is None:
            continue
        if part == "plugins":
            # A folder named plugins is refused; a file with that name is not.
            if is_dir or position != len(normalized) - 1:
                codes.add(code)
            continue
        codes.add(code)
    if CLAUDE_DIR in normalized:
        position = normalized.index(CLAUDE_DIR)
        allowed = position == 0 and (
            len(normalized) == 1
            or (
                len(normalized) == 2
                and not is_dir
                and normalized[1] == constants.TRUST_ALLOWED_CLAUDE_ENTRY
            )
        )
        if not allowed:
            codes.add(CODE_CLAUDE_FOLDER_ENTRY)
    if not is_dir:
        for suffix in constants.TRUST_REFUSED_SUFFIXES:
            if normalized[-1].endswith(suffix):
                codes.add(CODE_CODE_FILE)
                break
    return codes


def path_is_refused(components: Sequence[str], is_dir: bool = False) -> bool:
    """Whether one path is one no folder may hold and no update may carry.

    This is the one place the refused set is written down. The trust check
    calls it through the codes it builds, and the session-start update calls it
    to decide whether the shared copy carried something it will not take, so
    the two can never drift apart.
    """
    parts = [part for part in components if part not in ("", ".")]
    if not parts:
        return False
    return bool(_component_codes(parts, is_dir))


def _tracked_symlinks(git: GitRunner, root: str) -> Set[str]:
    """The links git already knows about, which a walk alone could miss."""
    codes: Set[str] = set()
    listed = git.run(["ls-files", "-s"], cwd=root, timeout=GIT_TIMEOUT_SECONDS)
    if not listed.ok:
        return {CODE_TREE_UNREADABLE}
    for line in listed.stdout.split("\n"):
        if line.startswith("120000 "):
            codes.add(CODE_SYMLINK)
            break
    return codes


def _ignored_paths(git: GitRunner, root: str) -> Set[str]:
    """The paths the shared settings say are this seat's own business."""
    listed = git.run(
        ["ls-files", "-o", "-i", "--exclude-standard", "--directory"],
        cwd=root,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if not listed.ok:
        return set()
    return set(
        line.strip().rstrip("/")
        for line in listed.stdout.split("\n")
        if line.strip()
    )


def _walk_codes(root: str, ignored: Set[str]) -> Set[str]:
    """Walk the tree once, never following a link, and stop at the cap."""
    codes: Set[str] = set()
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        relative_dir = os.path.relpath(dirpath, root)
        prefix = "" if relative_dir == "." else relative_dir.replace(os.sep, "/") + "/"
        kept = []
        for name in sorted(dirnames):
            relative = prefix + name
            if relative == ".git" or relative in ignored:
                continue
            seen += 1
            if seen > constants.TRUST_WALK_CAP:
                return {CODE_TREE_TOO_LARGE}
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                codes.add(CODE_SYMLINK)
                continue
            codes.update(_component_codes(relative.split("/"), True))
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            relative = prefix + name
            if relative in ignored:
                continue
            seen += 1
            if seen > constants.TRUST_WALK_CAP:
                return {CODE_TREE_TOO_LARGE}
            if os.path.islink(os.path.join(dirpath, name)):
                codes.add(CODE_SYMLINK)
                continue
            codes.update(_component_codes(relative.split("/"), False))
    return codes


def check(root: str, runner: Optional[GitRunner] = None) -> TrustResult:
    """Whether this folder may be trusted as a base, and why it may not be."""
    git = runner_or_default(runner)
    if not root or not os.path.isdir(root):
        return TrustResult(False, [CODE_TREE_UNREADABLE])

    codes: Set[str] = set()
    codes.update(_settings_codes(root))

    map_path = os.path.join(root, constants.MAP_PATH)
    if os.path.islink(map_path) or not os.path.isfile(map_path):
        codes.add(CODE_MAP_NOT_A_FILE)

    tracked = _tracked_symlinks(git, root)
    if CODE_TREE_UNREADABLE in tracked:
        codes.add(CODE_TREE_UNREADABLE)
    else:
        codes.update(tracked)
        try:
            codes.update(_walk_codes(root, _ignored_paths(git, root)))
        except OSError:
            codes.add(CODE_TREE_UNREADABLE)

    return TrustResult(not codes, sorted(codes))


def describe(codes: Iterable[str]) -> str:
    """The codes as one short list a person can read out loud."""
    return ", ".join(sorted(set(codes)))
