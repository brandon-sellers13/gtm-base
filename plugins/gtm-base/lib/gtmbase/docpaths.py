"""Which paths may be a base document, of what kind, and what may write each.

Unit 4.2a of Plan 1. Before it, the question "may this path be a base
document?" was answered in several modules, each saying the `context` folder
and nothing else, so a standard or the source map could never be owned,
confirmed, flagged or changed through a prepared change. This module is the
one answer, and every module that answered part of the question asks it.

A document is anything under `context` apart from the map, a standard at
`standards/<job>.md`, the source map at `access/stack.md`, and the three
shapes of a skill's files (the signed company-skills requirements, CS19).
One more destination is create-only: a lesson at `learning/lessons/<slug>.md`,
written once by the create operation and never edited. Everything else in a
base, the rest of `learning` and all of `work` included, is no document, and
the map is written only by its own settings operations.

The skills folder's files are documents here, so they can be named and
counted, but no operation may write one until Unit 4.2b opens the folder.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from . import constants, paths
from .errors import PathError

KIND_CONTEXT = "context"
KIND_STANDARD = "standard"
KIND_STACK = "stack"
KIND_SKILL = "skill"
KIND_LESSON = "lesson"

# What can be done to a document. A prepared change edits one, the create
# operation writes one that is not there yet, a confirmation says one is still
# right, and the settings operations change its owner or business line.
OP_EDIT = "edit"
OP_CREATE = "create"
OP_CONFIRM = "confirm"
OP_SETTINGS = "settings"
OPERATIONS = (OP_EDIT, OP_CREATE, OP_CONFIRM, OP_SETTINGS)

_EVERYTHING = frozenset(OPERATIONS)
_ALLOWED = {
    KIND_CONTEXT: _EVERYTHING,
    KIND_STANDARD: _EVERYTHING,
    KIND_STACK: _EVERYTHING,
    KIND_LESSON: frozenset([OP_CREATE]),
    # Unit 4.2b opens the skills folder; until then nothing writes there.
    KIND_SKILL: frozenset(),
}

# A job, an example, a lesson or a file's name: lower-case letters, digits and
# hyphens (CS19).
_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_STANDARD_RE = re.compile(r"^%s/(%s)\.md$" % (constants.STANDARDS_DIR, _NAME))
_LESSON_RE = re.compile(r"^%s/(%s)\.md$" % (constants.LESSONS_DIR, _NAME))
_SKILL_RES = (
    re.compile(r"^%s/(%s)/SKILL\.md$" % (constants.SKILLS_DIR, _NAME)),
    re.compile(r"^%s/(%s)/references/%s\.md$" % (constants.SKILLS_DIR, _NAME, _NAME)),
    re.compile(
        r"^%s/(%s)/examples/%s/%s\.(?:md|txt)$"
        % (constants.SKILLS_DIR, _NAME, _NAME, _NAME)
    ),
)

# The folders a path is checked under before its shape is looked at.
_PREFIXES = (
    constants.CONTEXT_DIR + "/",
    constants.STANDARDS_DIR + "/",
    constants.ACCESS_DIR + "/",
    constants.SKILLS_DIR + "/",
    constants.LESSONS_DIR + "/",
)


class DocPath(object):
    """One path, the kind of document it is, and the skill it belongs to."""

    __slots__ = ("path", "kind", "skill")

    def __init__(self, path: str, kind: str, skill: Optional[str] = None):
        self.path = path
        self.kind = kind
        self.skill = skill

    def __repr__(self) -> str:
        return "DocPath(%r, %r)" % (self.path, self.kind)


def _shape(candidate) -> Optional[str]:
    """The path when its shape is a safe one under the base's folders, or None."""
    try:
        return paths.check_repo_path_syntax(candidate, _PREFIXES)
    except PathError:
        return None


def classify(candidate) -> Optional[DocPath]:
    """The document a path names, or None when it may never be one."""
    text = _shape(candidate)
    if text is None:
        return None
    if text.startswith(constants.CONTEXT_DIR + "/"):
        if text == constants.MAP_PATH or not text.endswith(".md"):
            return None
        return DocPath(text, KIND_CONTEXT)
    if text == constants.STACK_PATH:
        return DocPath(text, KIND_STACK)
    if _STANDARD_RE.match(text):
        return DocPath(text, KIND_STANDARD)
    if _LESSON_RE.match(text):
        return DocPath(text, KIND_LESSON)
    for pattern in _SKILL_RES:
        match = pattern.match(text)
        if match:
            return DocPath(text, KIND_SKILL, skill=match.group(1))
    return None


def may(found: Optional[DocPath], operation: str) -> bool:
    """Whether an operation may write this document at all.

    Who may is the authority rule's question (`authority`); this one is only
    whether anybody may.
    """
    if operation not in OPERATIONS:
        raise ValueError("there is no such operation")
    if found is None:
        return False
    return operation in _ALLOWED.get(found.kind, frozenset())


def check_syntax(candidate) -> str:
    """The shape check every file format runs on a path it read, widened.

    It takes everything the `context` folder's check took, which is what every
    recorded change, confirmation and prepared change already holds, and the
    documents outside it: a standard and the source map. Lessons and a skill's
    files are not named by those records, so they are not taken here.
    """
    try:
        return paths.check_context_path_syntax(candidate)
    except PathError:
        found = classify(candidate)
        if found is not None and found.kind in (KIND_STANDARD, KIND_STACK):
            return found.path
        raise


def check_record_path(candidate) -> str:
    """A path a record of what changed may list: what a proposal may touch, and the documents.

    A record lists the files its change wrote: context files, the record of
    context changes, the record itself, and, since this unit, a standard, the
    source map and a new lesson.
    """
    try:
        return paths.check_repo_path_syntax(candidate, paths.PROPOSAL_PATH_PREFIXES)
    except PathError:
        found = classify(candidate)
        if found is not None and found.kind in (KIND_STANDARD, KIND_STACK, KIND_LESSON):
            return found.path
        raise


def check_proposal_path(candidate) -> str:
    """A path a prepared change may name: what every proposal is held to, a standard, the source map."""
    try:
        return paths.check_repo_path_syntax(candidate, paths.PROPOSAL_PATH_PREFIXES)
    except PathError:
        found = classify(candidate)
        if found is not None and found.kind in (KIND_STANDARD, KIND_STACK):
            return found.path
        raise


def canonical(base_root: str, candidate) -> str:
    """The base-relative path of a document a change, a confirmation or a check may name.

    It is `paths.canonical_context_path` for anything under `context`, exactly
    as before, and for a standard or the source map the same two checks: the
    shape first, then the real path, so a link pointing out of the base is
    refused although its name looks ordinary.
    """
    try:
        return paths.canonical_context_path(base_root, candidate)
    except PathError:
        found = classify(candidate)
        if found is None or found.kind not in (KIND_STANDARD, KIND_STACK):
            raise
        return check(base_root, found.path).path


def check(base_root: str, candidate) -> DocPath:
    """The document a path names on this base, with every folder on the way checked.

    A link anywhere on the way, the file itself included, is refused, and so
    is anything that resolves outside the base, because a document reached
    through a link may be any file on this computer.
    """
    found = classify(candidate)
    if found is None:
        raise PathError("this is not a document in the base", code="not-a-document")
    here = os.path.realpath(base_root)
    walked = here
    for part in found.path.split("/"):
        walked = os.path.join(walked, part)
        if os.path.islink(walked):
            raise PathError("this path passes through a link", code="link")
    resolved = os.path.realpath(os.path.join(here, found.path))
    if not resolved.startswith(here.rstrip(os.sep) + os.sep):
        raise PathError("this path leaves the base", code="outside-base")
    return found
