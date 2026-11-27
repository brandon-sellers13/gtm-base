"""Sending a write from a base with a shared copy as a proposal (P3).

A base with a shared copy takes nothing straight onto the line of work the
team shares (`gate.REASON_SHARED_LINE`), so a write that on a base of one's
own would be a save there is prepared in a working folder of this seat's own,
on a line of work of its own, and sent as a proposal for the owner of the
document to accept in the GTM Base app or in Claude Code. Recording a context
change and the setup closing both go this way.

The order matters and follows `compose_proposal.propose`: the two conditions
that stop anything leaving this computer are asked first, the working folder
is made from the shared copy's latest line, the write is made there and saved,
everything the proposal would carry is read by the same check that runs
before any send, and only then is it sent and the review opened. The person's
own folder is never touched, and the working folder is removed whatever
happens.
"""

from __future__ import annotations

import os
from typing import Callable, Dict, List, NamedTuple, Optional

from . import (
    compose_proposal,
    constants,
    formats,
    gate,
    ghcmd,
    paths,
    push_conditions,
    scan,
    worktree,
)
from .errors import GtmBaseError
from .fsutil import atomic_write_text, remove
from .gitcmd import GitRunner, runner_or_default
from .validate import marker_line

CODE_CANNOT_PREPARE = "proposal-not-prepared"
CODE_SEND_FAILED = compose_proposal.CODE_PUSH_FAILED
CODE_REVIEW_FAILED = compose_proposal.CODE_REVIEW_FAILED
CODE_NO_DEFAULT_BRANCH = "no-default-branch"

CANNOT_PREPARE = (
    "GTM Base could not prepare this as a proposal in its own working folder, "
    "so nothing was sent and nothing was written. Nothing was lost; try again."
)
SEND_FAILED = (
    "GTM Base prepared the proposal but could not send it to the shared copy, "
    "so nothing was written. Check that git on this computer is signed in to "
    "GitHub, then try again."
)
REVIEW_FAILED = (
    "GTM Base sent the proposal but could not open the review for it, so its "
    "owner cannot see it yet. Check that the GitHub command line tool is "
    "signed in, then try again."
)
NO_DEFAULT_BRANCH = "GTM Base could not tell which line of work the team shares."


class Sent(NamedTuple):
    staging_id: str
    branch: str
    number: Optional[int]
    url: Optional[str]


class Refused(GtmBaseError):
    """Nothing was sent; the message is the one sentence the person is told."""


def _refuse(sentence: str, code: str) -> Refused:
    return Refused(sentence, code)


def new_staging_id() -> str:
    return "stg-" + os.urandom(8).hex()


def send(
    base_root: str,
    base_id: str,
    write: Callable[[str], List[str]],
    title: str,
    fields: Dict[str, str],
    entry_id: Optional[str] = None,
    session_id: Optional[str] = None,
    gh=None,
    runner: Optional[GitRunner] = None,
) -> Sent:
    """Make one write in a working folder of this seat's own and send it as a proposal.

    `write` is handed the working folder and returns the paths it wrote, each
    relative to it. `fields` are the proposal's own sections, as
    `formats.render_pr_body` takes them, without the marker line.
    """
    git = runner_or_default(runner)

    session = session_id if session_id is not None else compose_proposal._seat_session_id(base_id)
    blocked = push_conditions.check(base_id, session, base_root, git)
    if blocked:
        code, sentence = blocked[0]
        raise _refuse(sentence, code)

    default = gate.default_branch(git, base_root)
    if not default:
        raise _refuse(NO_DEFAULT_BRANCH, CODE_NO_DEFAULT_BRANCH)

    staging_id = new_staging_id()
    body = formats.render_pr_body(dict(fields, marker=marker_line(staging_id, entry_id)))
    allowlist, _code = scan.load_allowlist(base_root)
    hits = scan.scan_text(body + "\n" + title, allowlist, "the proposal")
    if hits:
        raise _refuse(hits[0].sentence(), hits[0].pattern_class)

    made = None
    try:
        made = worktree.ensure_worktree(base_root, base_id, staging_id, default, git)
        start = git.run(["rev-parse", "HEAD"], cwd=made.path).out()
        written = write(made.path)
        if not written:
            raise _refuse(CANNOT_PREPARE, CODE_CANNOT_PREPARE)
        name, address, _codes = compose_proposal._author(base_root, git)
        git.check(["add", "--"] + list(written), cwd=made.path)
        git.check(
            [
                "-c", "user.name=%s" % name,
                "-c", "user.email=%s" % address,
                "commit", "-q", "-m", title,
            ],
            cwd=made.path,
        )
        reason = gate.scan_range(git, made.path, start, "HEAD", allowlist)
        if reason:
            raise _refuse(reason, "scan-found")

        sent = git.run(["push", "origin", made.branch], cwd=made.path, timeout=60)
        if not sent.ok:
            raise _refuse(SEND_FAILED, CODE_SEND_FAILED)

        body_file = os.path.join(paths.worktrees_dir(base_id), staging_id + "-proposal.md")
        atomic_write_text(body_file, body)
        try:
            code, output = ghcmd.call(
                gh,
                [
                    "pr", "create",
                    "--base", default,
                    "--head", made.branch,
                    "--title", title,
                    "--body-file", body_file,
                ],
                cwd=made.path,
            )
        finally:
            remove(body_file)
        if code != 0:
            raise _refuse(REVIEW_FAILED, CODE_REVIEW_FAILED)
        number, url = compose_proposal._parse_review_answer(output)
        return Sent(staging_id, made.branch, number, url)
    except GtmBaseError:
        raise
    except Exception:
        raise _refuse(CANNOT_PREPARE, CODE_CANNOT_PREPARE)
    finally:
        if made is not None:
            worktree.remove_worktree(base_root, made.path, runner=git)
