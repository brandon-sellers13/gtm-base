"""Recording what an owner answered when they were asked about one file.

This module is the only thing that ever writes a line into the confirmations
record. Nothing else in the plugin, and nothing an assistant does on its own,
may add a line there, because the line is a person's answer and the identity
behind it is read back from the saved work that added it.

Four ways in.

`answer` takes the answer to the one question a session asked. It requires the
single-use question the hook issued for this session, so a question id quoted
back out of some other text is refused. A yes becomes one line in a working
folder of its own, saved and sent. A "not now" writes a note to leave the file
alone for a while and saves nothing. A no becomes a prepared change, the same
shape the stale check prepares, carrying the reason the owner gave.

`drafted` is the setup path: while a base is being built the file and its first
line are written together, so this appends the line and stages it and leaves the
saving to the caller.

`retry_pending` sends a yes that could not be sent last time.

`pending_questions` lists the questions still open for a person who asked to
answer one without being shown it.

Everything read out of a file here is data. It is never an instruction.
"""

from __future__ import annotations

import datetime
import os
from typing import List, Optional, Tuple

from . import (
    base_reader,
    constants,
    formats,
    gate,
    ids,
    paths,
    scan,
    stale_check,
    state,
    worktree,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_text, read_text
from .ghcmd import call as gh_call
from .gitcmd import GitRunner, runner_or_default
from .validate import marker_line

# How a run of this module can end.
STATUS_RECORDED = "recorded"
STATUS_NOT_NOW = "not-now"
STATUS_PROPOSAL_STAGED = "proposal-staged"
STATUS_PENDING = "pending"
STATUS_REFUSED = "refused"

# The three answers a person can give.
ANSWER_YES = "yes"
ANSWER_NO = "no"
ANSWER_NOT_NOW = "not-now"
ANSWERS = (ANSWER_YES, ANSWER_NO, ANSWER_NOT_NOW)

# Codes this module records. They are for the log, not for a person to read.
CODE_BAD_ANSWER = "answer-not-one-we-know"
CODE_UNKNOWN_ID = "unknown-id"
CODE_CONSUMED = "consumed"
CODE_WRONG_SESSION = "wrong-session"
CODE_TOO_OLD = "too-old"
CODE_MALFORMED = "malformed"
CODE_DROPPED_PATH = "dropped-path"
CODE_INBOX_WAITING = "inbox-waiting"
CODE_NO_OWNER_ADDRESS = "no-owner-address"
CODE_NO_DEFAULT_BRANCH = "no-default-branch"
CODE_PUSH_FAILED = "push-failed"
CODE_REVIEW_FAILED = "review-not-opened"
CODE_UNSAVED_EDITS = "unsaved-edits"
CODE_REASON_NEEDED = "reason-needed"
CODE_ENTRY_MISSING = "decision-not-found"
CODE_ALREADY_DRAFTED = "already-drafted"
CODE_NOT_A_NEW_FILE = "not-a-new-file"
CODE_NOTHING_PENDING = "nothing-pending"

# The one code this module is allowed to leave in seat state.
PENDING_CODE = "pending-push"

# The header a confirmations file is created with. The test suite checks this
# against `templates/confirmation-line.md`, so the two can never drift apart.
FILE_HEADER = (
    "# One file per context file. One line per confirmation, added at the end "
    "and\n"
    "# never edited. The values are always in this order, and a value that does "
    "not\n"
    "# apply is written as a single dash.\n"
)

# What the saved work says it is. The path and the reason, and nothing else.
SAVE_SUBJECT = "Confirm %s (%s)"

# The heading the reason goes under when a no has no decision behind it.
FALLBACK_HEADING = stale_check.FALLBACK_HEADING
DRAFT_CONFIDENCE = stale_check.DRAFT_CONFIDENCE
# How much of a reason a prepared change carries.
REASON_CHARS = 600

# --- The sentences a person reads -------------------------------------------

UNKNOWN_ID = (
    "GTM Base does not know that question, so nothing was recorded. Ask for the "
    "question again."
)
ALREADY_ANSWERED = (
    "That question was answered already, so nothing was recorded a second time."
)
WRONG_SESSION = (
    "That question was asked in a different session, so nothing was recorded. "
    "Ask for the question again in this one."
)
TOO_OLD = (
    "That question was asked more than an hour ago, so nothing was recorded. "
    "Ask for it again."
)
MALFORMED_QUESTION = (
    "GTM Base could not tell when that question was asked, so nothing was "
    "recorded."
)
DROPPED_PATH = (
    "The file that question is about is not somewhere GTM Base is allowed to "
    "write, so nothing was recorded."
)
INBOX_WAITING = (
    "There are %d items waiting to be read in your inbox, so nothing was "
    "recorded yet. Read those first and the question comes back."
)
NO_OWNER_ADDRESS = (
    "GTM Base does not know which address to record your answer under, so "
    "nothing was recorded. Set your address on this base and answer again."
)
NO_DEFAULT_BRANCH = (
    "GTM Base could not tell which line of work the team shares, so nothing was "
    "recorded."
)
RECORDED = "Your answer was recorded for %s."
RECORDED_LOCALLY = "Your answer was recorded for %s in your own copy of the base."
SENT_FOR_REVIEW = (
    "Your answer for %s was raised for review, because this base has somebody "
    "read every change before it reaches the shared copy."
)
PENDING_SENTENCE = (
    "Your answer for %s is safe here but could not reach the shared copy, so "
    "GTM Base will send it the next time it can."
)
UNSAVED_EDITS = (
    "You have edits you have not saved, so your answer is being held here and "
    "will be added the next time GTM Base can add it."
)
NOT_NOW_SENTENCE = "GTM Base will leave %s alone until %s."
ASK_WHAT_CHANGED = (
    "Ask what has changed about this file, then say no again with that answer, "
    "so GTM Base can prepare the change."
)
PROPOSAL_STAGED = (
    "GTM Base prepared a change for %s from what you said. Improve the wording "
    "and hand it to the propose-change skill."
)
ENTRY_MISSING = (
    "GTM Base could not find the decision behind that question any more, so it "
    "prepared nothing."
)
DRAFTED_ALREADY = (
    "This file already carries the answer given when it was written, so nothing "
    "was added."
)
NOT_A_NEW_FILE = (
    "This answer can only be recorded for a file that is being written for the "
    "first time."
)
NOTHING_TO_SEND = "There is no answer waiting to be sent."


class ConfirmResult(object):
    """What one answer led to: where it ended up, and what to say about it."""

    __slots__ = ("status", "codes", "reasons", "staging_path", "line")

    def __init__(self, status, codes=None, reasons=None, staging_path=None, line=None):
        self.status = status
        self.codes = list(codes or [])
        self.reasons = list(reasons or [])
        self.staging_path = staging_path
        self.line = line

    @property
    def refused(self) -> bool:
        return self.status == STATUS_REFUSED

    def __repr__(self) -> str:
        return "ConfirmResult(status=%r, codes=%r)" % (self.status, self.codes)


def _refused(code: str, sentence: str) -> ConfirmResult:
    return ConfirmResult(STATUS_REFUSED, codes=[code], reasons=[sentence])


# --- Where a confirmation line lives ----------------------------------------


def confirmations_path_for(context_path: str) -> str:
    """The one file holding every answer about one context file."""
    return constants.CONFIRMATIONS_DIR + "/" + context_path.replace("/", "--")


def checked_confirmations_path(root: str, relative: str) -> str:
    """Where one confirmations file may be written, checked in that very folder.

    The check is made against the folder the writing happens in and nowhere
    else, because a name can be an ordinary file in one copy of a base and a
    link to somewhere else entirely in another. The folder it sits in has to be
    inside this copy once every link is followed, the name itself may never be
    a link, and anything already there has to be an ordinary file.
    """
    if not relative or relative.startswith("/") or ".." in relative.split("/"):
        raise PathError("this is not a name we write", code="bad-path")
    root_real = os.path.realpath(root)
    full = os.path.join(root_real, relative)
    parent_real = os.path.realpath(os.path.dirname(full))
    if parent_real != root_real and not parent_real.startswith(root_real + os.sep):
        raise PathError("this path leaves the working folder", code="outside-base")
    checked = os.path.join(parent_real, os.path.basename(full))
    if os.path.islink(checked):
        raise PathError("this name is a link to somewhere else", code="symlink")
    if os.path.lexists(checked) and not os.path.isfile(checked):
        raise PathError("this name is there but is not a file", code="not-a-file")
    return checked


def _append_line(root: str, relative: str, line: "formats.ConfirmationLine") -> str:
    """Add one line at the end of a confirmations file, making it when absent."""
    full = checked_confirmations_path(root, relative)
    existing = read_text(full)
    if existing is None:
        text = FILE_HEADER + line.render() + "\n"
    else:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        text = existing + line.render() + "\n"
    atomic_write_text(full, text, mode=0o644, inside=root)
    return full


def _line_already_there(root: str, relative: str, rendered: str) -> bool:
    text = read_text(checked_confirmations_path(root, relative))
    if text is None:
        return False
    return any(raw.strip() == rendered for raw in text.split("\n"))


# --- Identity ----------------------------------------------------------------


def _author(base_root: str, git: GitRunner) -> Tuple[Optional[str], str]:
    """The address and name this base saves work under, or nothing at all."""
    email = git.run(["config", "--local", "--get", "user.email"], cwd=base_root)
    name = git.run(["config", "--local", "--get", "user.name"], cwd=base_root)
    address = email.out() if email.ok else ""
    if not address:
        return None, constants.COMMIT_AUTHOR_FALLBACK_NAME
    return address, (name.out() if name.ok and name.out() else constants.COMMIT_AUTHOR_FALLBACK_NAME)


# --- The question --------------------------------------------------------


def _record_for(base_id: str, question: str) -> Optional[dict]:
    records, _problems = state.load_question_ids(base_id)
    for record in records:
        if record.get("id") == question:
            return record
    return None


def _question_problem(
    record: dict, session_id: str, now: datetime.datetime
) -> Optional[Tuple[str, str]]:
    """Why this question cannot be answered, without using it up."""
    if record.get("consumed"):
        return CODE_CONSUMED, ALREADY_ANSWERED
    if record.get("session_id") != session_id:
        return CODE_WRONG_SESSION, WRONG_SESSION
    issued = state.parse_iso_utc(record.get("issued_at", ""))
    if issued is None:
        return CODE_MALFORMED, MALFORMED_QUESTION
    if (now - issued).total_seconds() > constants.QUESTION_ID_WINDOW_SECONDS:
        return CODE_TOO_OLD, TOO_OLD
    return None


def pending_questions(
    base_id: str, now: Optional[datetime.datetime] = None
) -> List[dict]:
    """Every question still open: issued, never answered, not yet stale."""
    moment = now or state.now_utc()
    records, _problems = state.load_question_ids(base_id)
    open_ones = []
    for record in records:
        if record.get("consumed"):
            continue
        issued = state.parse_iso_utc(record.get("issued_at", ""))
        if issued is None:
            continue
        if (moment - issued).total_seconds() > constants.QUESTION_ID_WINDOW_SECONDS:
            continue
        open_ones.append(
            {
                "id": record.get("id"),
                "file": record.get("file"),
                "trigger": record.get("trigger"),
                "entry_id": record.get("entry_id"),
                "issued_at": record.get("issued_at"),
            }
        )
    return open_ones


# --- The answer --------------------------------------------------------------


def answer(
    base_root: str,
    base_id: str,
    question_id: str,
    answer: str,
    session_id: str,
    now: Optional[datetime.datetime] = None,
    runner: Optional[GitRunner] = None,
    gh=None,
    reason: Optional[str] = None,
    plan_requires_review: bool = False,
) -> ConfirmResult:
    """Record one answer to the one question this session asked.

    The question is single use, and using it up is the last thing that happens
    before the answer is recorded, never the first. Every refusal a person can
    do something about, and then answer again, is decided before the question
    is used up: an inbox with items still waiting to be read, a no that needs
    the owner to say what changed, and anything the owner said that must never
    leave this computer. The sentence each of those refusals prints asks for
    another answer to the same question, so the question has to still be there
    to answer.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    if isinstance(moment, datetime.date) and not isinstance(moment, datetime.datetime):
        moment = datetime.datetime(moment.year, moment.month, moment.day)
    # Dates are compared with the dates in the base, so they are the day it is
    # where the person is. Only the time on the line stays in universal time.
    today = state.today(moment)

    if answer not in ANSWERS:
        return _refused(
            CODE_BAD_ANSWER,
            "GTM Base takes yes, no, or not now, and nothing else.",
        )

    record = _record_for(base_id, question_id)
    if record is None:
        return _refused(CODE_UNKNOWN_ID, UNKNOWN_ID)
    problem = _question_problem(record, session_id, moment)
    if problem is not None:
        return _refused(problem[0], problem[1])

    trigger = record.get("trigger")
    entry_id = record.get("entry_id") or None
    try:
        path = paths.canonical_context_path(base_root, record.get("file") or "")
    except (PathError, ValidationError):
        state.append_dropped_path(
            base_id, str(record.get("file") or ""), "dropped-path", entry_id, today
        )
        return _refused(CODE_DROPPED_PATH, DROPPED_PATH)

    waiting = state.unprocessed_rows(base_id)
    if waiting:
        return _refused(CODE_INBOX_WAITING, INBOX_WAITING % len(waiting))

    def use_the_question():
        """Use the question up. Everything after this records the answer."""
        used, code = state.consume_question_id(
            base_id, question_id, session_id, moment
        )
        if used:
            return None
        return _refused(
            code, UNKNOWN_ID if code == CODE_UNKNOWN_ID else ALREADY_ANSWERED
        )

    if answer == ANSWER_NOT_NOW:
        spent = use_the_question()
        if spent is not None:
            return spent
        return _not_now(base_root, base_id, question_id, path, today)
    if answer == ANSWER_NO:
        return _no(
            base_root,
            base_id,
            question_id,
            path,
            trigger,
            entry_id,
            reason,
            today,
            git,
            use_the_question,
        )
    return _yes(
        base_root,
        base_id,
        question_id,
        path,
        trigger,
        entry_id,
        moment,
        today,
        git,
        gh,
        plan_requires_review,
        use_the_question,
    )


# --- Not now -----------------------------------------------------------------


def _not_now(base_root, base_id, question_id, path, today) -> ConfirmResult:
    """Leave the file alone for a while, and save nothing anywhere."""
    settings = base_reader.settings_of(base_reader.map_text(base_root))
    until = today + datetime.timedelta(days=int(settings.not_now_days))
    state.suppress(base_id, path, until)
    state.set_outcome(base_id, question_id, "not-now")
    return ConfirmResult(
        STATUS_NOT_NOW, reasons=[NOT_NOW_SENTENCE % (path, until.isoformat())]
    )


# --- Yes ---------------------------------------------------------------------


def _yes(
    base_root,
    base_id,
    question_id,
    path,
    trigger,
    entry_id,
    moment,
    today,
    git,
    gh,
    plan_requires_review,
    use_the_question=None,
) -> ConfirmResult:
    """Write the line, save it, read it, and send it."""
    address, name = _author(base_root, git)
    if not address:
        return _refused(CODE_NO_OWNER_ADDRESS, NO_OWNER_ADDRESS)
    default = gate.default_branch(git, base_root)
    if not default:
        return _refused(CODE_NO_DEFAULT_BRANCH, NO_DEFAULT_BRANCH)

    line = formats.ConfirmationLine(
        date=today.isoformat(),
        time=moment.strftime("%H:%M:%SZ"),
        file=path,
        trigger=trigger,
        entry=entry_id if trigger == "ledger" else None,
        question=question_id,
        run=None,
    )
    try:
        line.validate()
    except (ValidationError, PathError) as failure:
        return _refused(failure.code or CODE_MALFORMED, DROPPED_PATH)

    made = worktree.ensure_confirmations_worktree(base_root, base_id, default, git)
    relative = confirmations_path_for(path)
    codes = list(made.codes)
    try:
        hits = _save_the_line(base_root, made.path, relative, line, address, name, git)
        if hits:
            _undo(made.path, git)
            worktree.remove_worktree(base_root, made.path, runner=git)
            return ConfirmResult(
                STATUS_REFUSED,
                codes=[hit.pattern_class for hit in hits],
                reasons=[hits[0].sentence()],
            )
        if use_the_question is not None:
            spent = use_the_question()
            if spent is not None:
                _undo(made.path, git)
                worktree.remove_worktree(base_root, made.path, runner=git)
                return spent
        state.set_outcome(base_id, question_id, "yes")
        result = _send(
            base_root,
            base_id,
            made,
            default,
            line,
            relative,
            path,
            git,
            gh,
            plan_requires_review,
            codes,
        )
    except GtmBaseError as failure:
        worktree.remove_worktree(base_root, made.path, runner=git)
        return _refused(failure.code or CODE_MALFORMED, str(failure))
    worktree.remove_worktree(base_root, made.path, runner=git)
    return result


def _save_the_line(base_root, worktree_path, relative, line, address, name, git):
    """Add the line, save it on its own, and read what the saving would send."""
    _append_line(worktree_path, relative, line)
    git.check(["add", "--", relative], cwd=worktree_path)
    subject = SAVE_SUBJECT % (line.file, line.trigger)
    git.check(
        [
            "-c",
            "user.name=%s" % name,
            "-c",
            "user.email=%s" % address,
            "commit",
            "-q",
            "-m",
            subject,
        ],
        cwd=worktree_path,
    )
    allowlist, _code = scan.load_allowlist(base_root)
    shown = git.run(["show", "--format=", "--patch", "HEAD"], cwd=worktree_path)
    hits = scan.scan_diff_added_lines(shown.stdout if shown.ok else "", allowlist)
    hits.extend(scan.scan_text(subject, allowlist, "the note saved with the answer"))
    return hits


def _undo(worktree_path: str, git: GitRunner) -> None:
    """Put the working folder back the way it was before the line was added."""
    git.run(["reset", "--hard", "HEAD~1"], cwd=worktree_path)


def _send(
    base_root,
    base_id,
    made,
    default,
    line,
    relative,
    path,
    git,
    gh,
    plan_requires_review,
    codes,
) -> ConfirmResult:
    """Get the saved answer to the shared copy, or hold it for next time."""
    if not git.run(["remote", "get-url", "origin"], cwd=base_root).ok:
        return _add_to_the_local_copy(base_root, base_id, made, line, path, git, codes)

    # The line of work this seat carries its answers on belongs to this seat
    # alone and is only a carrier, so it is always written over rather than
    # added to. An answer that never reached the shared copy is held in this
    # seat's own settings, so nothing is lost by writing over it.
    sent = git.run(
        ["push", "--force", "origin", made.branch], cwd=made.path, timeout=60
    )
    if not sent.ok:
        return _hold(base_id, line, path, codes, CODE_PUSH_FAILED)

    if plan_requires_review:
        return _open_a_review(base_root, base_id, made, default, line, path, gh, codes)

    if _push_to_default(made.path, made.branch, default, git):
        return ConfirmResult(STATUS_RECORDED, codes=codes, reasons=[RECORDED % path], line=line)

    # The shared copy moved while this was being written. Start again from where
    # it is now, add the one line once more, and try the one time.
    worktree.remove_worktree(base_root, made.path, runner=git)
    address, name = _author(base_root, git)
    second = worktree.ensure_confirmations_worktree(base_root, base_id, default, git)
    codes.extend(second.codes)
    try:
        hits = _save_the_line(base_root, second.path, relative, line, address, name, git)
    except GtmBaseError:
        worktree.remove_worktree(base_root, second.path, runner=git)
        return _hold(base_id, line, path, codes, CODE_PUSH_FAILED)
    if hits:
        _undo(second.path, git)
        worktree.remove_worktree(base_root, second.path, runner=git)
        return ConfirmResult(
            STATUS_REFUSED,
            codes=[hit.pattern_class for hit in hits],
            reasons=[hits[0].sentence()],
        )
    pushed = git.run(
        ["push", "--force", "origin", second.branch], cwd=second.path, timeout=60
    )
    if pushed.ok and _push_to_default(second.path, second.branch, default, git):
        worktree.remove_worktree(base_root, second.path, runner=git)
        return ConfirmResult(
            STATUS_RECORDED, codes=codes, reasons=[RECORDED % path], line=line
        )
    worktree.remove_worktree(base_root, second.path, runner=git)
    return _hold(base_id, line, path, codes, CODE_PUSH_FAILED)


def _push_to_default(worktree_path: str, branch: str, default: str, git: GitRunner) -> bool:
    """Add this one saved answer to the line of work the team shares."""
    result = git.run(
        ["push", "origin", "%s:%s" % (branch, default)], cwd=worktree_path, timeout=60
    )
    return result.ok


def _open_a_review(
    base_root, base_id, made, default, line, path, gh, codes
) -> ConfirmResult:
    """Raise the answer for review, for a base that reviews every change."""
    body_path = os.path.join(
        paths.worktrees_dir(base_id), "confirmation-review.md"
    )
    atomic_write_text(
        body_path,
        "%s was confirmed as still right by its owner on %s.\n"
        % (line.file, line.date),
        mode=0o600,
    )
    try:
        code, _output = gh_call(
            gh,
            [
                "pr",
                "create",
                "--base",
                default,
                "--head",
                made.branch,
                "--title",
                "Confirmation for %s" % line.file,
                "--body-file",
                body_path,
            ],
            cwd=made.path,
        )
    finally:
        try:
            os.remove(body_path)
        except OSError:
            pass
    if code != 0:
        return _hold(base_id, line, path, codes, CODE_REVIEW_FAILED)
    return ConfirmResult(
        STATUS_RECORDED, codes=codes, reasons=[SENT_FOR_REVIEW % path], line=line
    )


def _add_to_the_local_copy(
    base_root, base_id, made, line, path, git, codes
) -> ConfirmResult:
    """A base with no shared copy keeps the answer in the person's own folder.

    The person's folder stays on the line of work the team shares and keeps
    whatever they were in the middle of, so this only goes ahead when there is
    nothing unsaved in it, and it only ever moves that folder forward by the one
    saved answer.
    """
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok or status.out():
        return _hold(base_id, line, path, codes, CODE_UNSAVED_EDITS, UNSAVED_EDITS)
    moved = git.run(["merge", "--ff-only", made.branch], cwd=base_root)
    if not moved.ok:
        return _hold(base_id, line, path, codes, CODE_PUSH_FAILED)
    return ConfirmResult(
        STATUS_RECORDED, codes=codes, reasons=[RECORDED_LOCALLY % path], line=line
    )


def _hold(base_id, line, path, codes, code, sentence=None) -> ConfirmResult:
    """Keep an answer that could not be added, and say so in one sentence.

    Answers waiting to be sent are kept as a list, because a person offline for
    a morning can say yes about three files and every one of those answers has
    to survive. The same answer twice over is kept once.
    """
    rendered = line.render()
    seat, _problems = state.load_seat(base_id)
    held = [dict(item) for item in (seat.get("pending_confirmations") or [])]
    if not any(item.get("line") == rendered for item in held):
        held.append(
            {"line": rendered, "file": line.file, "held_at": state.iso_utc()}
        )
    state.update_seat(
        base_id,
        pending_confirmation=PENDING_CODE,
        pending_confirmation_line=rendered,
        pending_confirmations=held,
    )
    return ConfirmResult(
        STATUS_PENDING,
        codes=list(codes) + [code],
        reasons=[sentence or (PENDING_SENTENCE % path)],
        line=line,
    )


def _save_pending(base_id, held) -> None:
    """Write back the answers still waiting, or clear the lot when none are."""
    if held:
        state.update_seat(
            base_id,
            pending_confirmation=PENDING_CODE,
            pending_confirmation_line=held[0].get("line"),
            pending_confirmations=[dict(item) for item in held],
        )
        return
    state.update_seat(
        base_id,
        pending_confirmation=None,
        pending_confirmation_line=None,
        pending_confirmations=[],
    )


# --- No ----------------------------------------------------------------------


def _no(
    base_root,
    base_id,
    question_id,
    path,
    trigger,
    entry_id,
    reason,
    today,
    git,
    use_the_question=None,
) -> ConfirmResult:
    """Turn a no into a prepared change, the way the stale check prepares one.

    The two refusals here both ask the owner to answer the same question again,
    one with words and one with different words, so neither of them uses the
    question up and neither of them records an answer.
    """
    allowlist, _code = scan.load_allowlist(base_root)
    if reason:
        hits = scan.scan_text(reason, allowlist, "what you said")
        if hits:
            return ConfirmResult(
                STATUS_REFUSED,
                codes=[hit.pattern_class for hit in hits],
                reasons=[hits[0].sentence()],
            )
    if not reason and not (trigger == "ledger" and entry_id):
        return _refused(CODE_REASON_NEEDED, ASK_WHAT_CHANGED)

    if use_the_question is not None:
        spent = use_the_question()
        if spent is not None:
            return spent
    state.set_outcome(base_id, question_id, "no")

    if trigger == "ledger" and entry_id:
        return _no_about_a_decision(
            base_root, base_id, path, entry_id, reason, today, git
        )
    return _no_about_the_calendar(base_root, question_id, path, reason)


def _no_about_a_decision(
    base_root, base_id, path, entry_id, reason, today, git
) -> ConfirmResult:
    """The file is out of date and a decision already says why."""
    inputs = base_reader.ledger(base_root, base_id, today)
    entry = None
    entry_file = ""
    for item in inputs:
        if item.entry is not None and item.entry.id == entry_id:
            entry = item.entry
            entry_file = (item.path or "").rsplit("/", 1)[-1]
            break
    if entry is None:
        return _refused(CODE_ENTRY_MISSING, ENTRY_MISSING)
    try:
        staging = stale_check.build_file_proposal(base_root, entry, entry_file, path)
    except (ValidationError, PathError) as failure:
        return _refused(failure.code or CODE_MALFORMED, str(failure))
    if reason:
        staging.pr_body = _with_the_owners_words(
            staging.pr_body, "The owner said: %s" % _short(reason)
        )
        staging.validate()
    written = stale_check.save_staging(base_root, staging)
    return ConfirmResult(
        STATUS_PROPOSAL_STAGED,
        reasons=[PROPOSAL_STAGED % path],
        staging_path=written,
    )


def _no_about_the_calendar(base_root, question_id, path, reason) -> ConfirmResult:
    """The file is out of date and the owner is the only one who has said so.

    The question is part of what names the prepared change, because the same
    owner can say no about the same file more than once, weeks apart, and each
    of those is its own change rather than the same one over again.
    """
    staging_id = ids.staging_id("threshold-" + str(question_id), path, "ledger", 0)
    words = _short(reason)
    body = formats.render_pr_body(
        {
            "before": "%s is written as though it is still right." % path,
            "after": "%s says what the owner told GTM Base has changed." % path,
            "why": (
                "The owner of %s was asked whether it is still right and said it "
                "is not. The words below are what they said, written into the "
                "file as a first draft for them to correct or replace." % path
            ),
            "evidence": "The owner said this file is no longer true: %s" % words,
            "confidence": DRAFT_CONFIDENCE,
            "rule_changed": "None",
            "marker": marker_line(staging_id, None, None),
        }
    )
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin="ledger",
        intake_path="ledger",
        target_paths=[path],
        sequence=0,
        rule_change=False,
        confidence=DRAFT_CONFIDENCE,
        third_party=False,
        pr_body=body,
        source_id=None,
        decision_block=None,
        edits=[formats.Edit(path, FALLBACK_HEADING, "add", words + "\n")],
        excerpt=words,
    )
    staging.validate()
    written = stale_check.save_staging(base_root, staging)
    return ConfirmResult(
        STATUS_PROPOSAL_STAGED,
        reasons=[PROPOSAL_STAGED % path],
        staging_path=written,
    )


def _short(text: str) -> str:
    """One line of what the owner said, no longer than a proposal may carry."""
    collapsed = " ".join((text or "").split())
    return collapsed[:REASON_CHARS]


def _with_the_owners_words(pr_body: str, sentence: str) -> str:
    """Add what the owner said to the evidence, leaving the rest untouched."""
    fields = formats.parse_pr_body(pr_body)
    fields["evidence"] = "%s\n\n%s" % (fields.get("evidence", ""), sentence)
    return formats.render_pr_body(fields)


# --- The setup path ----------------------------------------------------------


def drafted(
    base_root: str,
    base_id: str,
    path: str,
    run_id: str,
    now: Optional[datetime.datetime] = None,
    runner: Optional[GitRunner] = None,
) -> ConfirmResult:
    """Add the answer given when a file was written, and leave it staged.

    Setting a base up writes the file and this line together, so this adds the
    line and stages it and saves nothing. The caller saves the file and the line
    as one piece of work.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    if isinstance(moment, datetime.date) and not isinstance(moment, datetime.datetime):
        moment = datetime.datetime(moment.year, moment.month, moment.day)
    today = state.today(moment)
    try:
        relative_context = paths.canonical_context_path(base_root, path)
    except (PathError, ValidationError):
        return _refused(CODE_DROPPED_PATH, DROPPED_PATH)

    status = git.run(["status", "--porcelain", "--", relative_context], cwd=base_root)
    if not status.ok:
        return _refused(CODE_NOT_A_NEW_FILE, NOT_A_NEW_FILE)
    first = (status.stdout.split("\n") or [""])[0]
    if not (first.startswith("??") or first.startswith("A")):
        return _refused(CODE_NOT_A_NEW_FILE, NOT_A_NEW_FILE)

    relative = confirmations_path_for(relative_context)
    existing = read_text(os.path.join(base_root, relative)) or ""
    lines, _bad = formats.parse_confirmations_file(existing)
    for line in lines:
        if line.trigger == "drafted" and line.file == relative_context:
            return _refused(CODE_ALREADY_DRAFTED, DRAFTED_ALREADY)

    line = formats.ConfirmationLine(
        date=today.isoformat(),
        time=moment.strftime("%H:%M:%SZ"),
        file=relative_context,
        trigger="drafted",
        entry=None,
        question=None,
        run=run_id,
    )
    try:
        line.validate()
        _append_line(base_root, relative, line)
    except (ValidationError, PathError) as failure:
        return _refused(failure.code or CODE_MALFORMED, str(failure))
    git.check(["add", "--", relative], cwd=base_root)
    return ConfirmResult(
        STATUS_RECORDED, reasons=[RECORDED % relative_context], line=line
    )


# --- Sending an answer that could not be sent last time ----------------------


def retry_pending(
    base_id: str,
    base_root: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> Optional[ConfirmResult]:
    """Send every answer being held, and keep only the ones that stay stuck.

    Each answer is sent on its own and cleared on its own, so one answer that
    still cannot go does not take the others down with it. Nothing here is
    thrown away until the shared copy has it.
    """
    git = runner_or_default(runner)
    seat, _problems = state.load_seat(base_id)
    if not seat.get("pending_confirmation"):
        return None
    held = [dict(item) for item in (seat.get("pending_confirmations") or [])]
    if not held:
        _save_pending(base_id, [])
        return _refused(CODE_MALFORMED, NOTHING_TO_SEND)

    address, name = _author(base_root, git)
    if not address:
        return _refused(CODE_NO_OWNER_ADDRESS, NO_OWNER_ADDRESS)
    default = gate.default_branch(git, base_root)
    if not default:
        return _refused(CODE_NO_DEFAULT_BRANCH, NO_DEFAULT_BRANCH)

    still_waiting: List[dict] = []
    landed: List[ConfirmResult] = []
    stuck: List[ConfirmResult] = []
    unreadable = 0
    for item in held:
        try:
            line = formats.ConfirmationLine.parse(item.get("line") or "")
        except (ValidationError, PathError):
            unreadable += 1
            continue
        result = _send_one_held(base_root, base_id, line, address, name, default, git)
        if result.status == STATUS_RECORDED:
            landed.append(result)
        else:
            still_waiting.append(item)
            stuck.append(result)

    _save_pending(base_id, still_waiting)
    if stuck:
        return stuck[0]
    if landed:
        return landed[-1]
    del unreadable
    return _refused(CODE_MALFORMED, NOTHING_TO_SEND)


def _send_one_held(
    base_root, base_id, line, address, name, default, git
) -> ConfirmResult:
    """One held answer, added to a fresh working folder and sent from there."""
    folder = os.path.join(
        paths.worktrees_dir(base_id), worktree.CONFIRMATIONS_FOLDER_NAME
    )
    worktree.remove_worktree(base_root, folder, runner=git)
    made = worktree.ensure_confirmations_worktree(base_root, base_id, default, git)
    relative = confirmations_path_for(line.file)
    codes = list(made.codes)

    try:
        if _line_already_there(made.path, relative, line.render()):
            worktree.remove_worktree(base_root, made.path, runner=git)
            return ConfirmResult(
                STATUS_RECORDED, codes=codes, reasons=[RECORDED % line.file], line=line
            )
        hits = _save_the_line(base_root, made.path, relative, line, address, name, git)
    except GtmBaseError as failure:
        worktree.remove_worktree(base_root, made.path, runner=git)
        return _refused(failure.code or CODE_MALFORMED, str(failure))
    if hits:
        _undo(made.path, git)
        worktree.remove_worktree(base_root, made.path, runner=git)
        return ConfirmResult(
            STATUS_REFUSED,
            codes=[hit.pattern_class for hit in hits],
            reasons=[hits[0].sentence()],
        )

    result = _send(
        base_root,
        base_id,
        made,
        default,
        line,
        relative,
        line.file,
        git,
        None,
        False,
        codes,
    )
    worktree.remove_worktree(base_root, made.path, runner=git)
    return result
