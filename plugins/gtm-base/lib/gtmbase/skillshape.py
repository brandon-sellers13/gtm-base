"""What the skills folder of a base admits: exact shapes, and nothing else.

Plan 1, Unit 4.2b, from the signed company-skills requirements (CS19 to CS21).
Until this unit the folder held nothing but its empty placeholder. It now
admits, on every path that refuses today (an update from the shared copy, a
file on the disk when a base is opened, the check before a send), exactly:

- `skills/<job>/SKILL.md`;
- `skills/<job>/references/<name>.md`;
- `skills/<job>/examples/<example>/<name>.md` or `.txt`, one flat folder per
  example;

each a plain, non-executable file of at most 64,000 bytes, written in UTF-8,
in a skill of at most 50 files, and a `SKILL.md` whose settings block holds
only the keys CS21 lists. Every other name is refused, and so is anything a
check cannot read, because a gate that admits what it cannot parse fails open.

Admitting a file (may it exist here) and writing one (who may put it there)
are separate rules. This module is only the first. Writing is GTM Base's own
install and change operations, and a file tool writing into `skills/` stays
refused by the write check (CS22).
"""

from __future__ import annotations

import re
from typing import Iterable, Optional, Sequence

from . import constants, docpaths, formats
from .errors import PathError, ValidationError

# CS20.
MAX_FILE_BYTES = 64000
MAX_FILES = 50

# CS21: the keys a skill's settings block may hold, and nothing else, which
# keeps out keys that would grant a skill power in Claude Code.
SKILL_KEYS = frozenset(
    (
        "name",
        "description",
        "owner",
        "kind",
        "business",
        "sources",
        "status",
        "last_confirmed",
        "reads_required",
        "reads_optional",
        "standard",
    )
)

SKILL_FILE = "SKILL.md"
REFERENCES = "references"
EXAMPLES = "examples"

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The modes a saved file may have. Only a plain file that nobody can run.
REGULAR_MODE = "100644"


def admitted_shape(parts: Sequence[str], is_dir: bool = False) -> bool:
    """Whether a path under `skills/` has one of the admitted shapes, by its names.

    `parts` are the names from the top of the base, already compared the way
    the caller compares names (case folded), so the exact case is checked by
    `file_problem`, which every check that reads a file also asks.
    """
    names = [part for part in parts if part not in ("", ".")]
    if not names or names[0] != constants.SKILLS_DIR:
        return False
    rest = names[1:]
    if not rest:
        return True
    if len(rest) == 1:
        if not is_dir and rest[0] == constants.PLACEHOLDER_NAME:
            return True
        return is_dir and _name(rest[0])
    if not _name(rest[0]):
        return False
    if len(rest) == 2:
        if is_dir:
            return rest[1] in (REFERENCES, EXAMPLES)
        return rest[1] == SKILL_FILE.casefold()
    if rest[1] == REFERENCES and len(rest) == 3:
        return not is_dir and _file_name(rest[2], (".md",))
    if rest[1] == EXAMPLES:
        if len(rest) == 3:
            return is_dir and _name(rest[2])
        if len(rest) == 4:
            return not is_dir and _name(rest[2]) and _file_name(rest[3], (".md", ".txt"))
    return False


def _name(text: str) -> bool:
    return bool(_NAME_RE.match(text or ""))


def _file_name(text: str, endings: Sequence[str]) -> bool:
    for ending in endings:
        if text.endswith(ending) and _name(text[: -len(ending)]):
            return True
    return False


def file_problem(relative: str, data: Optional[bytes], mode: Optional[str] = None) -> Optional[str]:
    """Why one file under `skills/` may not be in a base, or None when it may.

    `relative` is the path as written, in its own case. `mode` is the saved
    mode when the file comes from saved work, or "executable" for a file on
    the disk anybody can run. A file whose bytes could not be read is refused.
    """
    found = docpaths.classify(relative)
    if found is None or found.kind != docpaths.KIND_SKILL:
        return "shape"
    if mode is not None and mode != REGULAR_MODE:
        return "mode"
    if data is None:
        return "unreadable"
    if len(data) > MAX_FILE_BYTES:
        return "size"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "encoding"
    if relative.endswith("/" + SKILL_FILE):
        return settings_problem(text)
    return None


def settings_problem(text: str) -> Optional[str]:
    """Why a `SKILL.md` settings block may not be admitted, or None (CS21).

    A carriage return not followed by a new line is refused, because another
    reader may take it as a line break and see a key this one did not.
    """
    if re.search("\r(?!\n)", text):
        return "settings"
    try:
        block, _body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        return "settings"
    if set(fields) - SKILL_KEYS:
        return "settings-key"
    return None


def too_many(paths: Iterable[str]) -> bool:
    """Whether any one skill among these paths holds more files than CS20 allows."""
    counted = {}
    for path in paths:
        found = docpaths.classify(path)
        if found is None or found.kind != docpaths.KIND_SKILL:
            continue
        counted[found.skill] = counted.get(found.skill, 0) + 1
    return any(count > MAX_FILES for count in counted.values())


def written_only_by_gtm_base(parts: Sequence[str], is_dir: bool = False) -> bool:
    """Whether a file tool writing here is refused: anything in `skills/` but its placeholder.

    The placeholder and the folder itself stay as they were before this unit.
    """
    names = [part for part in parts if part not in ("", ".")]
    if not names or names[0] != constants.SKILLS_DIR or len(names) == 1:
        return False
    if len(names) == 2 and not is_dir and names[1] == constants.PLACEHOLDER_NAME:
        return False
    return True
