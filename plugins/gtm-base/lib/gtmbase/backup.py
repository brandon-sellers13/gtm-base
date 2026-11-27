"""Back up a base to its GitHub repository: the first backup review (P1).

Until now nothing could leave a base, because the first backup was never
reviewed and no code set that record. This is the review, in two steps that
are two separate commands:

1. `review` reads, writes nothing to the base, and sends nothing. It checks
   the address is a GitHub repository that is empty, shows what would go up
   (how many documents in each part of the base, how many saved versions),
   and runs the very scan the git hook runs before any send, over everything
   the first backup would carry. If the scan finds nothing, it records in this
   seat the address it reviewed and the exact saved version it reviewed.
2. `send` is an approval only a person can give: Claude Code asks them itself
   (see `approval`). It sends only the version that was reviewed, only to the
   address that was reviewed, and only into a repository that is still empty.
   Git's own pre-push hook still runs on the send and checks everything again.

The record says what was reviewed and what was sent, never a bare yes, which
is what `push_conditions.first_push_unreviewed` now reads.
"""

from __future__ import annotations

import datetime
import re
from typing import Dict, List, NamedTuple, Optional

from . import approval, gate, ids, machine, scan, state
from .errors import GtmBaseError
from .gitcmd import GitRunner, runner_or_default

# The browser address of a repository on GitHub, and nothing else: no sign-in,
# no other host, no extra path.
_ADDRESS_RE = re.compile(
    r"\Ahttps://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?\Z"
)

# How long a review stays good for, and how long a yes to send stays good for.
REVIEW_GOOD_FOR = datetime.timedelta(hours=1)
APPROVAL_GOOD_FOR = datetime.timedelta(minutes=15)
PUSH_TIMEOUT_SECONDS = 180

CODE_BAD_ADDRESS = "backup-bad-address"
CODE_NOT_EMPTY = "backup-not-empty"
CODE_CANNOT_REACH = "backup-cannot-reach"
CODE_OTHER_REMOTE = "backup-other-remote"
CODE_ALREADY = "backup-already"
CODE_NOT_ON_BRANCH = "backup-not-on-branch"
CODE_NOTHING_SAVED = "backup-nothing-saved"
CODE_REVIEW_AGAIN = "backup-review-again"
CODE_SEND_FAILED = "backup-send-failed"
CODE_PUBLIC = "backup-public"

SENTENCES = {
    CODE_BAD_ADDRESS: (
        "That is not the address of a GitHub repository. Use the address the "
        "GTM Base app gave you, which looks like https://github.com/your-account/your-base."
    ),
    CODE_NOT_EMPTY: (
        "That repository already holds something, and a first backup only goes "
        "into an empty one, so nothing was sent. Create an empty one in the GTM "
        "Base app and use its address."
    ),
    CODE_CANNOT_REACH: (
        "GitHub did not let this computer read that repository. Check the "
        "address, and that git on this computer is signed in to GitHub with an "
        "account that can reach it."
    ),
    CODE_OTHER_REMOTE: (
        "This base already sends its copy somewhere else, so it was not pointed "
        "at a second place."
    ),
    CODE_ALREADY: "This base is already backed up to that repository.",
    CODE_PUBLIC: (
        "Anyone can read that repository without signing in, so nothing was sent. "
        "A base only goes into a private repository; make it private on GitHub, "
        "or create a new one in the GTM Base app."
    ),
    CODE_NOT_ON_BRANCH: (
        "This base is not on its main line of saved work right now, so nothing "
        "was sent. Switch back to it first."
    ),
    CODE_NOTHING_SAVED: "This base has nothing saved yet, so there is nothing to back up.",
    CODE_REVIEW_AGAIN: (
        "The base or the address changed since the review, or the review is "
        "more than an hour old, so nothing was sent. Run the review again."
    ),
    CODE_SEND_FAILED: (
        "Git could not send the base to GitHub, so nothing was sent and the "
        "base is as it was. Check that git on this computer is signed in to "
        "GitHub, then run the review again."
    ),
}


def _check_target(git: GitRunner, root: str, address: str) -> None:
    """The repository is reachable with this computer's sign-in, private, and empty."""
    listed = git.run(["ls-remote", address], cwd=root, timeout=60)
    if not listed.ok:
        raise _refuse(CODE_CANNOT_REACH)
    if listed.out().strip():
        raise _refuse(CODE_NOT_EMPTY)
    if readable_without_sign_in(git, root, address):
        raise _refuse(CODE_PUBLIC)


def readable_without_sign_in(git: GitRunner, root: str, address: str) -> bool:
    """Whether anybody can read the repository: asked with every sign-in helper off."""
    return git.run(["-c", "credential.helper=", "ls-remote", address], cwd=root, timeout=60).ok


def _refuse(code: str) -> GtmBaseError:
    return GtmBaseError(SENTENCES[code], code)


def parse_address(text: str) -> str:
    """The one form of a GitHub repository address this sends to."""
    match = _ADDRESS_RE.match((text or "").strip())
    if not match:
        raise _refuse(CODE_BAD_ADDRESS)
    return "https://github.com/%s/%s.git" % (match.group("owner"), match.group("repo"))


def _same_place(one: Optional[str], other: Optional[str]) -> bool:
    try:
        return bool(one and other) and ids.canonical_remote_address(one) == ids.canonical_remote_address(other)
    except ValueError:
        return False


# The plugin's own clock and format (naive UTC), so records read back alike.
def _now() -> datetime.datetime:
    return state.now_utc()


def _iso(moment: datetime.datetime) -> str:
    return state.iso_utc(moment)


def _age(text: Optional[str]) -> Optional[datetime.timedelta]:
    moment = state.parse_iso_utc(text) if isinstance(text, str) else None
    return None if moment is None else _now() - moment


def _origin(git: GitRunner, root: str) -> Optional[str]:
    """The shared copy's address as the base's settings store it.

    Read from the settings rather than asked of git's remote command, which
    applies any address rewriting this computer's git settings hold, so the
    same base would answer differently on two computers.
    """
    found = git.run(["config", "--local", "--get", "remote.origin.url"], cwd=root)
    address = found.out() if found.ok else ""
    return ids.strip_userinfo(address) if address else None


def _head(git: GitRunner, root: str) -> Optional[str]:
    found = git.run(["rev-parse", "--verify", "--quiet", "HEAD^{commit}"], cwd=root)
    return found.out() if found.ok and found.out() else None


def _branch(git: GitRunner, root: str) -> Optional[str]:
    found = git.run(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=root)
    name = found.out() if found.ok else ""
    return name if name in ("main", "master") else None


class Review(NamedTuple):
    address: str
    head: str
    branch: str
    commits: int
    documents_by_part: Dict[str, int]
    files: int
    problem: Optional[str]  # the scan's own sentence, or None when nothing was found


def review(root: str, base_id: str, address_text: str, runner: Optional[GitRunner] = None) -> Review:
    """Check, show and (when the scan is clean) record what a first backup would send."""
    git = runner_or_default(runner)
    address = parse_address(address_text)
    existing = _origin(git, root)
    if _joined_record(base_id) is not None:
        # A seat joined from a link is a copy of a base that is already backed
        # up, and it never sends its whole history anywhere.
        raise _refuse(CODE_ALREADY if _same_place(existing, address) else CODE_OTHER_REMOTE)
    if existing:
        seat, _problems = state.load_seat(base_id)
        record = seat.get("first_backup") or {}
        if _same_place(existing, address) and record.get("sent_at"):
            raise _refuse(CODE_ALREADY)
        if not _same_place(existing, address):
            raise _refuse(CODE_OTHER_REMOTE)
    branch = _branch(git, root)
    if branch is None:
        raise _refuse(CODE_NOT_ON_BRANCH)
    head = _head(git, root)
    if head is None:
        raise _refuse(CODE_NOTHING_SAVED)

    _check_target(git, root, address)

    # The same scan the git hook runs before any send, over everything this
    # first backup would carry.
    allowlist, _code = scan.load_allowlist(root)
    problem = gate.scan_range(git, root, gate.EMPTY_TREE, head, allowlist)

    names = git.run(["ls-tree", "-r", "--name-only", head], cwd=root)
    by_part: Dict[str, int] = {}
    files = 0
    for name in names.out().splitlines() if names.ok else []:
        files += 1
        top = name.split("/", 1)[0] if "/" in name else ""
        if name.endswith(".md") and top in ("context", "learning", "access", "skills", "standards"):
            by_part[top] = by_part.get(top, 0) + 1
    counted = git.run(["rev-list", "--count", head], cwd=root)
    commits = int(counted.out()) if counted.ok and counted.out().isdigit() else 0

    if problem is None:
        state.update_seat(
            base_id,
            first_backup={
                "address": address,
                "branch": branch,
                "reviewed_head": head,
                "reviewed_at": _iso(_now()),
                "approved_at": None,
                "sent_at": None,
            },
        )
    return Review(address, head, branch, commits, by_part, files, problem)


def send(root: str, base_id: str, address_text: str, runner: Optional[GitRunner] = None) -> str:
    """Send the reviewed version to the reviewed address. Returns the address."""
    approval.require("backup.send")
    git = runner_or_default(runner)
    address = parse_address(address_text)
    seat, _problems = state.load_seat(base_id)
    record = seat.get("first_backup")
    if not isinstance(record, dict) or record.get("sent_at"):
        raise _refuse(CODE_REVIEW_AGAIN if not isinstance(record, dict) else CODE_ALREADY)
    head = _head(git, root)
    age = _age(record.get("reviewed_at"))
    if (
        record.get("address") != address
        or record.get("reviewed_head") != head
        or age is None
        or age > REVIEW_GOOD_FOR
    ):
        raise _refuse(CODE_REVIEW_AGAIN)
    branch = _branch(git, root)
    if branch is None or branch != record.get("branch"):
        raise _refuse(CODE_NOT_ON_BRANCH if branch is None else CODE_REVIEW_AGAIN)
    _check_target(git, root, address)

    existing = _origin(git, root)
    added = False
    if existing is None:
        if not git.run(["remote", "add", "origin", address], cwd=root).ok:
            raise _refuse(CODE_SEND_FAILED)
        added = True
    elif not _same_place(existing, address):
        raise _refuse(CODE_OTHER_REMOTE)

    # The yes, written just before the send, is what lets git's own pre-push
    # check through, for this one version to this one branch at this one
    # address. It is taken back whatever happens, so it never stays open.
    record["approved_at"] = _iso(_now())
    state.update_seat(base_id, first_backup=record)
    pushed = None
    try:
        pushed = git.run(
            ["push", "--set-upstream", "origin", "%s:refs/heads/%s" % (head, branch)],
            cwd=root,
            timeout=PUSH_TIMEOUT_SECONDS,
        )
    finally:
        record["approved_at"] = None
        if pushed is not None and pushed.ok:
            record["sent_at"] = _iso(_now())
        state.update_seat(base_id, first_backup=record)
    if not pushed.ok:
        if added:
            git.run(["remote", "remove", "origin"], cwd=root)
        raise _refuse(CODE_SEND_FAILED)
    # Name the shared line of work here too, so later sends are read from it.
    git.run(["branch", "--set-upstream-to", "origin/%s" % branch, branch], cwd=root)
    git.run(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/%s" % branch], cwd=root)
    machine.record_remote(base_id, address)
    return address


def _record(base_id: str) -> Optional[dict]:
    seat, _problems = state.load_seat(base_id)
    record = seat.get("first_backup")
    if not isinstance(record, dict):
        return None
    # Only ever a GitHub repository address, whoever wrote the record.
    try:
        if parse_address(str(record.get("address") or "")) != record.get("address"):
            return None
    except GtmBaseError:
        return None
    return record


def _joined_record(base_id: str) -> Optional[str]:
    """The repository a seat joined from a link was copied from, or None."""
    from . import join_link

    return join_link.joined_address(base_id)


def shared_address(base_id: str) -> Optional[str]:
    """The one GitHub repository this base's sends may go to, or None.

    The repository a first backup went to, or the one a seat joined from a
    link was copied from. Before either, there is none.
    """
    joined = _joined_record(base_id)
    if joined:
        return joined
    record = _record(base_id)
    if record is not None and record.get("sent_at"):
        return record.get("address")
    return None


def first_push_unreviewed(base_id: str, root: Optional[str], runner: Optional[GitRunner] = None) -> bool:
    """Whether sends from this base are still held back for want of a first backup.

    Answered from what the record says was sent, read against the base: the
    base's own shared copy must be the address the backup went to. A seat
    joined from a link has nothing to back up, so its record of where it was
    copied from stands in for the backup's, read against the base the same way.
    Where each send goes is checked on its own by `destination_allowed`.
    Anything that cannot be read is answered yes.
    """
    if not root:
        return True
    try:
        joined = _joined_record(base_id)
        if joined is not None:
            return not _same_place(_origin(runner_or_default(runner), root), joined)
        record = _record(base_id)
        if record is None or not record.get("sent_at"):
            return True
        return not _same_place(_origin(runner_or_default(runner), root), record.get("address"))
    except Exception:
        return True


def destination_allowed(
    base_id: str,
    root: Optional[str],
    destination: Optional[str],
    refs: Optional[List[tuple]] = None,
    runner: Optional[GitRunner] = None,
) -> bool:
    """Whether a send from this base may go to `destination`.

    Only ever to the one GitHub repository the base was backed up to, never
    anywhere else, whatever the base's settings now say. Before the first
    backup has gone, only git's own pre-push check, handed `refs` (each
    `(local_sha, remote_ref)` being sent), may let the reviewed version through
    to the reviewed branch, and only in the minutes after the person's yes.
    """
    if not root or not destination:
        return False
    try:
        joined = _joined_record(base_id)
        if joined is not None:
            return _same_place(destination, joined)
        record = _record(base_id)
        if record is None or not _same_place(destination, record.get("address")):
            return False
        if record.get("sent_at"):
            return True
        if refs is None:
            return False
        approved = _age(record.get("approved_at"))
        if approved is None or approved > APPROVAL_GOOD_FOR:
            return False
        wanted = ("refs/heads/%s" % record.get("branch"), record.get("reviewed_head"))
        return bool(refs) and all((remote_ref, local_sha) == wanted for local_sha, remote_ref in refs)
    except Exception:
        return False


# One whole sentence per part of the base, with only the count filled in.
_PART_SENTENCES = {
    "context": ("One is a context document.", "%d are context documents."),
    "learning": ("One is a learning record.", "%d are learning records."),
    "access": ("One is an access document.", "%d are access documents."),
    "skills": ("One is a skill.", "%d are skills."),
    "standards": ("One is a standard.", "%d are standards."),
}


def describe(found: Review) -> List[str]:
    """The review as plain sentences for the person; only counts are filled in."""
    lines = [
        "This would send a copy of your base to the GitHub repository on the address line below.",
        "It holds one file." if found.files == 1 else "It holds %d files." % found.files,
    ]
    for part in ("context", "learning", "access", "skills", "standards"):
        count = found.documents_by_part.get(part, 0)
        if count:
            one, many = _PART_SENTENCES[part]
            lines.append(one if count == 1 else many % count)
    lines.append(
        "It carries the one saved version of your work. Anything you have not saved stays on this computer."
        if found.commits == 1
        else "It carries %d saved versions of your work, the newest as it stands now. "
        "Anything you have not saved stays on this computer." % found.commits
    )
    if found.problem:
        lines.append(found.problem)
        lines.append("Nothing can be sent until that is fixed, so nothing was recorded.")
    else:
        lines.append(
            "The check that runs before anything leaves this computer found nothing "
            "that looks like a password, key or private link."
        )
    return lines
