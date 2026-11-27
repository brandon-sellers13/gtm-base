"""Where each document lives, in the layout a base has today and the older one.

A base is laid out by the five parts of the CLASS framework (Unit 1.5b of the
2026-09-19 plan). A base set up before that holds the same documents at older
paths: the customer profile in `context/strategy/icp.md` rather than
`context/icps.md`, its context changes in `work/changes` or `work/decisions`
rather than `learning/changes`, and its records in `corrections` rather than
`learning/corrections`.

Both layouts are read and only the current one is written, exactly as Unit 1.4
did for the folder of context changes. This module is the one place the two
layouts are related to each other, so that every reader answers the question
"where is this document on this base" the same way.

The rule is simple and it is the whole of it. A path somebody wrote down, in
a context change, a confirmation line, a record of what changed, a prepared
change, or a seat's own settings, names a document. That document lives at
the path as written when a file is there. When no file is there and the
document's other path holds one, it lives there instead. When neither holds a
file, the path is left exactly as written, because a document nobody can find
is still the document it names.

Nothing here writes anything, reaches the network, or runs git.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional, Sequence, Tuple

from . import constants

# The current path of each document, keyed by where a base laid out before
# this held it, and the reverse.
_TO_CURRENT = dict(constants.LEGACY_DOCUMENT_PATHS)
_TO_OLDER = dict((current, older) for older, current in constants.LEGACY_DOCUMENT_PATHS)


def _clean(path) -> str:
    return str(path or "").replace(os.sep, "/").strip()


def _one_segment(path: str, folder: str) -> Optional[str]:
    """The file name of a segment directly inside one folder, or None."""
    prefix = folder + "/"
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :]
    if not rest or "/" in rest or not rest.endswith(".md"):
        return None
    return rest


def current_of(path) -> Optional[str]:
    """Where a document at an older path lives in the current layout, or None."""
    text = _clean(path)
    found = _TO_CURRENT.get(text)
    if found:
        return found
    name = _one_segment(text, constants.LEGACY_SEGMENTS_DIR)
    if name:
        return constants.SEGMENTS_DIR + "/" + name
    return None


def older_of(path) -> Optional[str]:
    """Where a base laid out before this held a document now at this path."""
    text = _clean(path)
    found = _TO_OLDER.get(text)
    if found:
        return found
    name = _one_segment(text, constants.SEGMENTS_DIR)
    if name:
        return constants.LEGACY_SEGMENTS_DIR + "/" + name
    return None


def counterpart(path) -> Optional[str]:
    """The same document's path in the other layout, or None when it has none."""
    return current_of(path) or older_of(path)


def is_older_path(path) -> bool:
    """Whether this is a document path only the older layout uses."""
    return current_of(path) is not None


def _present(root: str, relative: str) -> bool:
    return os.path.lexists(os.path.join(root, relative.replace("/", os.sep)))


def where_it_lives(root: Optional[str], path) -> str:
    """The path the document this names is at on this base.

    A path is left exactly as written when a file is there, and when neither
    it nor its counterpart is there. Only when the file is missing and its
    counterpart is present does the answer change.
    """
    text = _clean(path)
    if not text or not root:
        return text
    if _present(root, text):
        return text
    other = counterpart(text)
    if other and _present(root, other):
        return other
    return text


def all_where_they_live(root: Optional[str], values: Iterable) -> List[str]:
    """Each path followed to where its document lives, with repeats taken out."""
    found: List[str] = []
    for value in values or []:
        where = where_it_lives(root, value)
        if where and where not in found:
            found.append(where)
    return found


def required_paths(root: Optional[str]) -> Tuple[str, ...]:
    """The two required documents, each where it really is on this base.

    A base on the current layout, and a fresh folder with neither yet, get the
    current paths. A base laid out before this gets the older path of each
    document it still holds there.
    """
    return tuple(
        where_it_lives(root, path) for path in constants.REQUIRED_CONTEXT_FILES
    )


def same_document(first, second) -> bool:
    """Whether two paths name the same document, in either layout."""
    one = _clean(first)
    two = _clean(second)
    if not one or not two:
        return False
    return one == two or counterpart(one) == two


def is_required(path) -> bool:
    """Whether a path names one of the two required documents, in either layout."""
    text = _clean(path)
    return text in constants.REQUIRED_CONTEXT_FILES or (
        text in constants.LEGACY_REQUIRED_CONTEXT_FILES
    )


def follow_the_move(root: Optional[str], staging) -> None:
    """Point a prepared change at where its documents live on this base.

    A change prepared before the base was moved names each document at its
    older path. It is still accepted afterwards: the paths are followed in
    memory, and the prepared file itself is never touched, because the yes the
    owner gives is bound to that file exactly as it was written.
    """
    if staging is None or not root:
        return
    targets = list(getattr(staging, "target_paths", None) or [])
    if targets:
        staging.target_paths = all_where_they_live(root, targets)
    for edit in list(getattr(staging, "edits", None) or []):
        path = getattr(edit, "path", None)
        if path:
            edit.path = where_it_lives(root, path)


# --- The skills folder, refused until a trust model exists -------------------


def is_refused_in_skills(parts: Sequence[str], is_dir: bool = False) -> bool:
    """Whether one path under the base's own skills folder must be refused.

    Since Plan 1's Unit 4.2b the folder admits exact shapes (`skillshape`):
    the placeholder, `<job>/SKILL.md`, `<job>/references/<name>.md`, and
    `<job>/examples/<example>/<name>.md` or `.txt`, and the folders that hold
    them. Anything else is refused by every path that can put one there: an
    update from the shared copy, a file on the disk when the base is opened,
    and a send. A file tool writing into the folder is refused by its own
    rule (`skillshape.written_only_by_gtm_base`), because admitting a file and
    writing one are separate questions.

    `parts` are the path's names from the top of the base, already compared the
    way the caller compares names. The checks that read a file also ask
    `skillshape.file_problem`, which reads its exact case, mode, size and
    settings.
    """
    from . import skillshape

    names = [part for part in parts if part not in ("", ".")]
    if not names or names[0] != constants.SKILLS_DIR:
        return False
    if len(names) == 1:
        # The folder on its own. A file named `skills` at the top is not a
        # folder of skills and holds nothing, so it is allowed as well.
        return False
    return not skillshape.admitted_shape(names, is_dir)


def is_the_skills_placeholder(relative) -> bool:
    """Whether a path relative to the base is the skills folder's placeholder.

    The name alone is never enough: every check that allows it also requires
    it to be an empty ordinary file, because a placeholder holding a whole
    procedure is a skill by another name (Astra's review of Unit 1.5b,
    finding 8).
    """
    text = _clean(relative)
    parts = [part.casefold() for part in text.split("/") if part not in ("", ".")]
    return parts == [constants.SKILLS_DIR, constants.PLACEHOLDER_NAME]


def placeholder_is_empty(full_path: str) -> bool:
    """Whether a file on the disk is an empty ordinary file, and nothing else."""
    try:
        return (
            not os.path.islink(full_path)
            and os.path.isfile(full_path)
            and os.path.getsize(full_path) == 0
        )
    except OSError:
        return False


def names_a_skill_file(relative) -> bool:
    """Whether a path relative to the base names a refused file under skills."""
    text = _clean(relative)
    if not text:
        return False
    parts = [part.casefold() for part in text.split("/")]
    return is_refused_in_skills(parts)
