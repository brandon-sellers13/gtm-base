"""Has this exact change already been proposed, anywhere, by anyone.

Two seats can read the same meeting and reach the same conclusion, and a change
that was already accepted or already turned down must not come back around as
though it were new. Both questions are answered by one line of plain text: the
marker every proposal carries, in its body and in the file it leaves behind
once it is accepted.

Nothing here writes anything. It reads the reviews on the shared copy through
the injectable tool runner and the accepted files in the base, and reports what
it found.
"""

from __future__ import annotations

import glob
import json
import os
from typing import List, Optional

from . import constants, ghcmd
from .formats import CorrectionsFile
from .fsutil import read_text
from .validate import find_marker, marker_line

# What the search can conclude.
KIND_NONE = "none"
KIND_OPEN = "open"
KIND_CLOSED = "closed"
KIND_MERGED = "merged-corrections"

# Codes worth recording. None of them is ever shown to a person as it stands.
CODE_LIST_FAILED = "review-list-failed"
CODE_LIST_UNREADABLE = "review-list-unreadable"
CODE_CORRECTIONS_UNREADABLE = "corrections-file-unreadable"

# Most reviews the search asks for at once.
SEARCH_LIMIT = 50


class DuplicateResult(object):
    """What the search found, and where."""

    __slots__ = ("kind", "pr_number", "pr_url", "path", "codes")

    def __init__(self, kind=KIND_NONE, pr_number=None, pr_url=None, path=None, codes=None):
        self.kind = kind
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.path = path
        self.codes = list(codes or [])

    @property
    def found(self) -> bool:
        return self.kind != KIND_NONE

    def __repr__(self) -> str:
        return "DuplicateResult(kind=%r, pr_number=%r)" % (self.kind, self.pr_number)


def marker_for(staging) -> str:
    """The exact line this proposal carries wherever it ends up.

    The line in the body a reviewer reads is the one that counts, because that
    is the text that travels. When the body carries none, the line is built
    from the proposal's own identifiers instead.
    """
    parsed = find_marker(getattr(staging, "pr_body", "") or "")
    if parsed is not None:
        return marker_line(parsed[0], parsed[1], parsed[2])
    return marker_line(staging.staging_id, None, staging.source_id)


def _accepted_files(base_root: str, staging_id: str, codes: List[str]) -> Optional[str]:
    """The accepted file already recording this proposal, if there is one."""
    folder = os.path.join(base_root, constants.CORRECTIONS_DIR)
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        text = read_text(path)
        if text is None:
            codes.append(CODE_CORRECTIONS_UNREADABLE)
            continue
        try:
            correction = CorrectionsFile.parse(text)
        except Exception:
            codes.append(CODE_CORRECTIONS_UNREADABLE)
            continue
        if correction.staging_id == staging_id:
            return os.path.relpath(path, base_root)
    return None


def _reviews_carrying(marker: str, base_root: str, gh, codes: List[str]) -> List[dict]:
    """Every review on the shared copy whose text carries this exact line."""
    code, output = ghcmd.call(
        gh,
        [
            "pr",
            "list",
            "--state",
            "all",
            "--search",
            marker,
            "--json",
            "number,state,body,url,headRefName",
            "--limit",
            str(SEARCH_LIMIT),
        ],
        cwd=base_root,
    )
    if code != 0:
        codes.append(CODE_LIST_FAILED)
        return []
    text = (output or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except ValueError:
        codes.append(CODE_LIST_UNREADABLE)
        return []
    if not isinstance(payload, list):
        codes.append(CODE_LIST_UNREADABLE)
        return []
    carrying = []
    for review in payload:
        if not isinstance(review, dict):
            continue
        body = review.get("body")
        if not isinstance(body, str):
            continue
        for line in body.splitlines():
            if line.strip() == marker:
                carrying.append(review)
                break
    return carrying


def _state_of(review: dict) -> str:
    return str(review.get("state") or "").strip().upper()


def _head_of(review: dict) -> str:
    return str(review.get("headRefName") or "").strip()


def check(
    staging, base_root: str, gh=None, runner=None, own_branch: Optional[str] = None
) -> DuplicateResult:
    """Whether this proposal has already been made, and how it ended.

    An accepted file in the base is the strongest answer, because the change is
    already in the shared copy. Otherwise an open review means another seat is
    carrying this one right now, and a closed one means somebody said no.

    A review this seat opened for this very proposal is not somebody else, so
    the caller says which line of work is its own and reviews on that line are
    left out. Without that, a run repeated after the review opened would report
    the seat's own review as another person's and never tidy itself up.
    """
    del runner  # git is not needed here; the argument keeps the callers alike.
    codes: List[str] = []
    marker = marker_for(staging)

    accepted = _accepted_files(base_root, staging.staging_id, codes)
    if accepted is not None:
        return DuplicateResult(KIND_MERGED, path=accepted, codes=codes)

    reviews = _reviews_carrying(marker, base_root, gh, codes)
    if own_branch:
        reviews = [review for review in reviews if _head_of(review) != own_branch]
    merged = [review for review in reviews if _state_of(review) == "MERGED"]
    if merged:
        first = merged[0]
        return DuplicateResult(
            KIND_MERGED,
            pr_number=first.get("number"),
            pr_url=first.get("url"),
            codes=codes,
        )
    open_reviews = [review for review in reviews if _state_of(review) == "OPEN"]
    if open_reviews:
        first = open_reviews[0]
        return DuplicateResult(
            KIND_OPEN,
            pr_number=first.get("number"),
            pr_url=first.get("url"),
            codes=codes,
        )
    if reviews:
        first = reviews[0]
        return DuplicateResult(
            KIND_CLOSED,
            pr_number=first.get("number"),
            pr_url=first.get("url"),
            codes=codes,
        )
    return DuplicateResult(KIND_NONE, codes=codes)


def open_review_for_branch(branch: str, base_root: str, gh=None):
    """The review already open for one line of work, if there is one.

    This is what makes a run that stopped after the review was opened safe to
    repeat: the review is found again rather than opened a second time.
    """
    code, output = ghcmd.call(
        gh,
        ["pr", "list", "--head", branch, "--json", "number,url", "--limit", "5"],
        cwd=base_root,
    )
    if code != 0:
        return None
    text = (output or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    return {"number": first.get("number"), "url": first.get("url")}
