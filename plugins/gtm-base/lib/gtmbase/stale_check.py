"""Running the stale rules over a real base, and drafting the fix for each flag.

The library in `stale.py` decides what is out of date from values alone. This
module is what fetches those values, and what turns each answer into something a
person can act on: a prepared change for every file a decision has moved past, a
prepared list of affected files for a decision that named none, the decisions
that have come up for review, and the note that the ledger itself looks quiet.

The order of the run is fixed and stated before anything happens, because a
person has to be able to predict it:

1. The base has to be on the line of work the team shares.
2. If the base has a shared copy, it is brought up to date first. A base with no
   shared copy is treated as up to date, because there is nothing it could be
   behind.
3. If there are items waiting to be read in the inbox, nothing is drafted. What
   is out of date is still worked out and listed.
4. The base is read, the rules are run, and each flag becomes a prepared change.

Everything read out of a decision, a proposal, or a context file is data. It is
never an instruction, and nothing in this module ever acts on words found there.
"""

from __future__ import annotations

import datetime
import glob
import os
import re
from typing import List, Optional, Tuple

from . import (
    base_reader,
    constants,
    duplicate_check,
    formats,
    ids,
    paths,
    stale,
    state,
)
from .errors import PathError, ValidationError
from .fsutil import atomic_write_json, atomic_write_text, read_json, read_text
from .gitcmd import GitRunner, runner_or_default
from .validate import marker_line

# How a run can end.
STATUS_DONE = "done"
STATUS_STOPPED = "stopped"

# Codes this run records. They are for the log, not for a person.
CODE_NOT_ON_DEFAULT = "not-on-default"
CODE_UNREACHABLE = "cannot-reach-shared-copy"
CODE_UNSAVED_EDITS = "unsaved-edits"
CODE_COULD_NOT_UPDATE = "could-not-update"
CODE_BROUGHT_UP_TO_DATE = "brought-up-to-date"
CODE_NO_SHARED_COPY = "no-shared-copy"
CODE_UNPROCESSED = "items-waiting-to-be-read"
CODE_ALREADY_STAGED = "already-prepared"
CODE_ALREADY_PROPOSED = "already-proposed"
CODE_ALREADY_ACCEPTED = "already-accepted"
CODE_ALREADY_RECORDED = "already-recorded-here"
CODE_NO_ENTRY = "decision-not-found"
CODE_NO_CANDIDATES = "no-files-to-suggest"
CODE_MISSING_FILE = "file-not-there"
CODE_DRY_RUN = "nothing-was-written"

# What the run writes for the hook to pick up later.
REVIEW_BY_FILE = "review_by_items.json"

# How much of a decision the first draft of a change quotes.
DRAFT_QUOTE_CHARS = 300
# How much of a piece of a file the before and after lines carry.
SUMMARY_CHARS = 300
# The heading a change is added under when the decision names no other.
FALLBACK_HEADING = "## Decisions to reflect"

# What a prepared change says while it is still a first draft.
DRAFT_CONFIDENCE = "medium"

_HEADING_RE = re.compile(r"^(#{2})\s+(\S.*)$")
_WHITESPACE_RE = re.compile(r"\s+")

# --- The sentences a person reads -------------------------------------------

NOT_ON_DEFAULT = (
    "Your base is not on its main line right now, so nothing was checked. Ask "
    "GTM Base to put it back."
)
UNREACHABLE = (
    "GTM Base could not reach the shared copy of your base, so nothing was "
    "checked this time."
)
UNSAVED_EDITS = (
    "Your base is behind the shared copy and you have edits you have not saved, "
    "so nothing was checked. Put those edits somewhere safe and ask again."
)
COULD_NOT_UPDATE = (
    "GTM Base could not bring your base up to date on its own, so nothing was "
    "checked this time."
)
BROUGHT_UP_TO_DATE = "Your base was brought up to date with the shared copy first."
UNPROCESSED = (
    "There are %d items waiting to be read in your inbox, so nothing was "
    "prepared. Everything that is out of date is still listed below, and the "
    "changes can be prepared once those items have been read."
)
NOTHING_FLAGGED = "Nothing in your base is out of date today."
DRY_RUN_NOTE = "This was a look only, so nothing was written."
LEDGER_BEHIND = (
    "The ledger holds nothing newer than %s, which is more than %d days ago. If "
    "nothing has been decided since then, say so and GTM Base will stop "
    "mentioning it for %d days."
)
LEDGER_BEHIND_EMPTY = (
    "The ledger holds no decisions at all yet. If there is nothing to write "
    "down, say so and GTM Base will stop mentioning it for %d days."
)
LEDGER_BEHIND_DISMISSED = (
    "GTM Base will not mention the quiet ledger again until %s."
)
REVIEW_BY = (
    "Decision %s came up for review on %s, which was %d days ago."
)
MALFORMED = (
    "%d things in your base could not be read, so they were left alone."
)
DROPPED = (
    "%d file names in your decisions point outside the base, so they were "
    "skipped."
)

# The first-run findings, in the order the first run looks for them.
FINDING_REQUIRED_FILE = (
    "You have not written %s yet, so there is nothing there to keep current."
)
FINDING_REQUIRED_ENTRY = (
    "No decision has been written down yet, so there is nothing for GTM Base to "
    "check your documents against."
)
FINDING_DOCUMENT_OLDER = (
    "The material behind %s is dated %s, and decision %s was made on %s, so that "
    "document is older than the decision it is meant to reflect. It is worth a "
    "read."
)
FINDING_NOTHING_YET = (
    "Nothing is out of date yet. The first date GTM Base will watch is %s, when "
    "decision %s comes up for review."
)
FINDING_NOTHING_YET_NO_DATE = (
    "Nothing is out of date yet, and no decision has a review date set, so there "
    "is no date to watch."
)


# --- What comes back ---------------------------------------------------------


class Staged(object):
    """One prepared change, and where it was written."""

    __slots__ = ("staging_id", "path", "target_paths", "entry_id", "kind")

    def __init__(self, staging_id, path, target_paths, entry_id, kind):
        self.staging_id = staging_id
        self.path = path
        self.target_paths = list(target_paths)
        self.entry_id = entry_id
        self.kind = kind

    def __repr__(self) -> str:
        return "Staged(staging_id=%r, kind=%r)" % (self.staging_id, self.kind)


class Skipped(object):
    """One flag that was not prepared, and the reason in one code."""

    __slots__ = ("staging_id", "entry_id", "path", "code")

    def __init__(self, staging_id, entry_id, path, code):
        self.staging_id = staging_id
        self.entry_id = entry_id
        self.path = path
        self.code = code

    def __repr__(self) -> str:
        return "Skipped(staging_id=%r, code=%r)" % (self.staging_id, self.code)


class StaleCheckResult(object):
    """Everything one run of the stale check has to say."""

    def __init__(self, status=STATUS_DONE, mode="normal"):
        self.status = status
        self.mode = mode
        self.codes: List[str] = []
        self.sentences: List[str] = []
        self.staged: List[Staged] = []
        self.skipped: List[Skipped] = []
        self.report = None
        self.finding = None
        self.finding_sentence = ""
        self.drafting_refused = False
        self.unprocessed_count = 0
        self.dry_run = False

    @property
    def stopped(self) -> bool:
        return self.status == STATUS_STOPPED

    def lines(self) -> List[str]:
        """Every sentence this run prints, in the order it prints them."""
        return list(self.sentences)

    def __repr__(self) -> str:
        return "StaleCheckResult(status=%r, staged=%d)" % (
            self.status,
            len(self.staged),
        )


# --- Small helpers -----------------------------------------------------------


def _collapse(text: str, cap: int = SUMMARY_CHARS) -> str:
    """One line of plain words, short enough to sit in a sentence."""
    single = _WHITESPACE_RE.sub(" ", str(text or "")).strip()
    if len(single) <= cap:
        return single
    return single[:cap].rstrip() + "..."


def _quote(text: str) -> str:
    """A piece of the base, marked as something read rather than written."""
    lines = [line.strip() for line in str(text or "").strip().split("\n")]
    return "\n".join("> " + line if line else ">" for line in lines)


def _headings_of(text: str) -> List[str]:
    """Every second level heading in a file, as it is written."""
    found = []
    for line in (text or "").split("\n"):
        match = _HEADING_RE.match(line.rstrip())
        if match:
            found.append(line.strip())
    return found


def _section_text(text: str, heading: str) -> str:
    """The words under one heading, up to the next heading as big or bigger."""
    lines = (text or "").split("\n")
    wanted = heading.strip()
    for index, line in enumerate(lines):
        if line.strip() != wanted:
            continue
        collected = []
        for following in lines[index + 1 :]:
            if following.startswith("#"):
                break
            collected.append(following)
        return "\n".join(collected).strip()
    return ""


def _heading_named_by(entry_text: str, file_text: str) -> Optional[str]:
    """The heading in the file that the decision itself talks about."""
    haystack = (entry_text or "").lower()
    for heading in _headings_of(file_text):
        title = heading.lstrip("#").strip()
        if title and title.lower() in haystack:
            return heading
    return None


def _entry_citation(entry, entry_file: str) -> str:
    """The one sentence that says which decision this came from."""
    name = (entry_file or "").rsplit("/", 1)[-1]
    return "Decision %s, written down in %s, decided on %s." % (
        entry.id,
        name or "the ledger",
        entry.decided_on,
    )


def _proposals_glob(base_root: str) -> List[str]:
    folder = os.path.join(base_root, constants.PROPOSALS_DIR)
    return glob.glob(os.path.join(folder, "**", "*.md"), recursive=True)


def _staging_exists(base_root: str, staging_id: str) -> bool:
    """Whether a prepared change with this identifier is already waiting."""
    wanted = staging_id + ".md"
    return any(os.path.basename(path) == wanted for path in _proposals_glob(base_root))


def _corrections_citing(base_root: str) -> List["formats.CorrectionsFile"]:
    """Every accepted record the base holds, as far as it can be read."""
    found = []
    folder = os.path.join(base_root, constants.CORRECTIONS_DIR)
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        text = read_text(path)
        if text is None:
            continue
        try:
            found.append(formats.CorrectionsFile.parse(text))
        except (ValidationError, PathError):
            continue
    return found


def _recorded_in_index(base_id: str, staging_id: str) -> bool:
    """Whether this seat already recorded a proposal for this identifier."""
    index, _problems = state.load_index(base_id)
    for row in index.values():
        for value in row.get("staging_ids") or []:
            if str(value) == staging_id:
                return True
        for value in row.get("proposal_ids") or []:
            if str(value).startswith(staging_id + ":"):
                return True
    return False


# --- Writing one prepared change ---------------------------------------------


def draft_text_for(entry) -> str:
    """The first draft of the words that go into the file.

    It is deliberately a plain sentence naming the decision, because the words
    that end up in the file are the assistant's job to write from the decision
    and the file, and a first draft that pretends to be finished is worse than
    one that says what it is.
    """
    quoted = _collapse(entry.body, DRAFT_QUOTE_CHARS).rstrip(".")
    return "Update needed: %s. This section should reflect that decision." % quoted


def build_file_proposal(
    base_root: str, entry, entry_file: str, path: str
) -> "formats.ProposalStaging":
    """The prepared change for one file one decision has moved past."""
    staging_id = ids.staging_id(entry.id, path, "ledger", 0)
    text = read_text(os.path.join(base_root, path))
    if text is None:
        raise ValidationError(
            "GTM Base could not read %s, so it prepared nothing for it." % path,
            code=CODE_MISSING_FILE,
        )
    heading = _heading_named_by(entry.body, text)
    if heading is not None:
        operation = "replace"
        before = _collapse(_section_text(text, heading))
    else:
        heading = FALLBACK_HEADING
        operation = "add"
        before = ""
    if not before:
        before = "This part of %s does not say anything about that decision yet." % path
    drafted = draft_text_for(entry)

    body = formats.render_pr_body(
        {
            "before": before,
            "after": _collapse(drafted),
            "why": (
                "The team wrote this decision down and %s was never brought in "
                "line with it. The words below are a first draft for the owner "
                "to correct or replace." % path
            ),
            "evidence": "%s\n\n%s" % (_entry_citation(entry, entry_file), _quote(entry.body)),
            "confidence": DRAFT_CONFIDENCE,
            "rule_changed": "None",
            "marker": marker_line(staging_id, entry.id, None),
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
        edits=[formats.Edit(path, heading, operation, drafted + "\n")],
        excerpt=_collapse(entry.body, constants.MAX_EXCERPT_CHARS),
    )
    return staging.validate()


def build_affected_files_proposal(
    entry, entry_file: str, candidates: List[str]
) -> "formats.ProposalStaging":
    """The prepared list of files a decision touches, when it named none.

    A decision that names no files is not a change to any one file, so this
    proposal asks the owner to approve the list itself. Each named file gets one
    line saying it was named by GTM Base, and accepting the proposal is the
    owner saying the list is right.
    """
    staging_id = ids.staging_id(entry.id, constants.MAP_PATH, "ledger", 1)
    edits = [
        formats.Edit(
            path,
            FALLBACK_HEADING,
            "add",
            "This file was named by GTM Base as affected by decision %s; confirm "
            "or remove it.\n" % entry.id,
        )
        for path in candidates
    ]
    body = formats.render_pr_body(
        {
            "before": "Decision %s does not say which files it affects." % entry.id,
            "after": "Decision %s is marked as affecting %s."
            % (entry.id, ", ".join(candidates)),
            "why": (
                "Whoever wrote this decision down left the list of files it "
                "affects blank, so GTM Base worked out which files it most "
                "likely touches. The owner is approving that list. Accepting "
                "this marks each file named above as one the decision touches, "
                "and turning it down leaves the list as it was."
            ),
            "evidence": "%s\n\n%s" % (_entry_citation(entry, entry_file), _quote(entry.body)),
            "confidence": DRAFT_CONFIDENCE,
            "rule_changed": "None",
            "marker": marker_line(staging_id, entry.id, None),
        }
    )
    staging = formats.ProposalStaging(
        staging_id=staging_id,
        origin="ledger",
        intake_path="ledger",
        target_paths=list(candidates),
        sequence=1,
        rule_change=False,
        confidence=DRAFT_CONFIDENCE,
        third_party=False,
        pr_body=body,
        source_id=None,
        decision_block=None,
        edits=edits,
        excerpt=_collapse(entry.body, constants.MAX_EXCERPT_CHARS),
    )
    return staging.validate()


def staging_path_for(base_root: str, staging_id: str) -> str:
    return os.path.join(
        base_root, constants.PROPOSALS_PENDING_DIR, staging_id + ".md"
    )


def save_staging(base_root: str, staging) -> str:
    """Write one prepared change where the review skill looks for it.

    Both this module and the confirmation flow prepare changes, and both write
    them the same way, so the writing lives in one place.
    """
    path = staging_path_for(base_root, staging.staging_id)
    atomic_write_text(path, staging.render(), mode=0o600)
    return path


# --- The review-by list the hook picks up ------------------------------------


def save_review_by_items(base_id: str, items, today: datetime.date) -> str:
    """Write the decisions that have come up for review, for the next session."""
    payload = {
        "schema": 1,
        "date": today.isoformat(),
        "items": [
            {
                "entry_id": item.entry_id,
                "review_by": item.review_by.isoformat()
                if hasattr(item.review_by, "isoformat")
                else str(item.review_by),
                "days_overdue": int(item.days_overdue),
            }
            for item in items
        ],
    }
    path = os.path.join(paths.seat_dir(base_id), REVIEW_BY_FILE)
    atomic_write_json(path, payload)
    return path


def load_review_by_items(base_id: str) -> List[dict]:
    """The decisions the last run found waiting for review, or none."""
    payload = read_json(os.path.join(paths.seat_dir(base_id), REVIEW_BY_FILE))
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


# --- Getting the base ready --------------------------------------------------


def _fast_forward(base_root: str, branch: str, git: GitRunner, result) -> bool:
    """Bring the base up to date, or say in one sentence why it was not."""
    fetched = git.run(
        ["fetch", "origin", branch, "--quiet"],
        cwd=base_root,
        timeout=constants.FETCH_TIMEOUT_SECONDS,
    )
    if not fetched.ok:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_UNREACHABLE)
        result.sentences.append(UNREACHABLE)
        return False
    target = "origin/" + branch
    counted = git.run(
        ["rev-list", "--count", "HEAD.." + target], cwd=base_root
    )
    try:
        behind = int(counted.out()) if counted.ok else 0
    except ValueError:
        behind = 0
    if behind <= 0:
        return True
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok or status.out():
        result.status = STATUS_STOPPED
        result.codes.append(CODE_UNSAVED_EDITS)
        result.sentences.append(UNSAVED_EDITS)
        return False
    merged = git.run(
        ["merge", "--ff-only", target],
        cwd=base_root,
        timeout=constants.FETCH_TIMEOUT_SECONDS,
    )
    if not merged.ok:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_COULD_NOT_UPDATE)
        result.sentences.append(COULD_NOT_UPDATE)
        return False
    result.codes.append(CODE_BROUGHT_UP_TO_DATE)
    result.sentences.append(BROUGHT_UP_TO_DATE)
    return True


def _retry_pending(base_id: str, base_root: str, git: GitRunner) -> None:
    """Send a confirmation that could not be sent last time, if we can yet."""
    try:
        from . import confirm  # noqa: F401
    except ImportError:
        return
    retry = getattr(confirm, "retry_pending", None)
    if retry is None:
        return
    try:
        retry(base_id=base_id, base_root=base_root, runner=git)
    except Exception:
        return


# --- The first run's one finding ---------------------------------------------


def finding_sentence(report, finding) -> str:
    """The one honest thing a first run says, in plain words.

    It never claims more than the dates show. When nothing is out of date it
    says exactly that, and names the first date it will watch.
    """
    if finding.code == stale.FINDING_REQUIRED_FILE_MISSING:
        return FINDING_REQUIRED_FILE % finding.path
    if finding.code == stale.FINDING_REQUIRED_ENTRY_MISSING:
        return FINDING_REQUIRED_ENTRY
    if finding.code == stale.FINDING_DOCUMENT_OLDER:
        decided = None
        for item in report.review_items:
            if item.path == finding.path and item.entry_id == finding.entry_id:
                decided = item.decided_on
                break
        return FINDING_DOCUMENT_OLDER % (
            finding.path,
            finding.date,
            finding.entry_id,
            decided,
        )
    if finding.date is None:
        return FINDING_NOTHING_YET_NO_DATE
    return FINDING_NOTHING_YET % (finding.date, finding.entry_id)


# --- The run -----------------------------------------------------------------


def run(
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    gh=None,
    now: Optional[datetime.date] = None,
    session_id: Optional[str] = None,
    mode: str = "normal",
    dismiss_ledger_behind: bool = False,
    dry_run: bool = False,
) -> StaleCheckResult:
    """Work out what is out of date, and prepare the change for each answer."""
    git = runner_or_default(runner)
    today = now or state.today()
    if isinstance(today, datetime.datetime):
        today = today.date()
    result = StaleCheckResult(mode="first-run" if mode == "first-run" else "normal")
    result.dry_run = bool(dry_run)

    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        result.status = STATUS_STOPPED
        result.codes.append(CODE_NOT_ON_DEFAULT)
        result.sentences.append(NOT_ON_DEFAULT)
        return result

    has_remote = paths.remote_url(base_root, runner=git) is not None
    branch = git.run(
        ["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=base_root
    ).out()
    if has_remote:
        if not _fast_forward(base_root, branch, git, result):
            return result
    else:
        result.codes.append(CODE_NO_SHARED_COPY)

    seat, _problems = state.load_seat(base_id)
    if seat.get("pending_confirmation"):
        _retry_pending(base_id, base_root, git)

    waiting = state.unprocessed_rows(base_id)
    result.unprocessed_count = len(waiting)
    if waiting:
        result.drafting_refused = True
        result.codes.append(CODE_UNPROCESSED)
        result.sentences.append(UNPROCESSED % len(waiting))

    inputs = base_reader.read_base(
        base_root, base_id, runner=git, today=today, record_dropped=not dry_run
    )
    report = stale.compute(
        today=today,
        settings=inputs.settings,
        files=inputs.files,
        ledger=inputs.ledger,
        confirmations=inputs.confirmations,
        corrections=inputs.corrections,
        seat=inputs.seat,
        owner_email=None,
    )
    result.report = report
    entry_files = inputs.entry_files()

    if result.mode == "first-run":
        finding = report.first_run_finding()
        result.finding = finding
        result.finding_sentence = finding_sentence(report, finding)
        result.sentences.append(result.finding_sentence)
        _report_the_rest(result, report, base_id, today, dry_run)
        return result

    if not result.drafting_refused:
        _prepare_everything(
            result, report, inputs, entry_files, base_root, base_id, gh, dry_run
        )
    else:
        _list_without_preparing(result, report)

    _report_the_rest(result, report, base_id, today, dry_run)

    if dismiss_ledger_behind and not dry_run:
        window = report.settings.confirmation_threshold_days
        until = today + datetime.timedelta(days=window)
        state.set_ledger_behind_dismissed_until(base_id, until)
        result.sentences.append(LEDGER_BEHIND_DISMISSED % until.isoformat())

    if dry_run:
        result.codes.append(CODE_DRY_RUN)
        result.sentences.append(DRY_RUN_NOTE)
    return result


def _ledger_flags(report) -> List[Tuple[str, str]]:
    """Every (decision, file) pair a decision has moved past, in a fixed order."""
    pairs = []
    for flag in report.file_flags:
        if flag.trigger != stale.TRIGGER_LEDGER:
            continue
        for entry_id in flag.entry_ids:
            pairs.append((entry_id, flag.path))
    return sorted(set(pairs))


def _list_without_preparing(result, report) -> None:
    """Say what a decision has moved past without preparing anything for it."""
    for entry_id, path in _ledger_flags(report):
        result.sentences.append(
            "%s is out of date against decision %s." % (path, entry_id)
        )


def _list_waiting_on_the_owner(result, report) -> None:
    """The documents nobody has said are still right, which nothing can fix."""
    for flag in report.file_flags:
        if flag.trigger == stale.TRIGGER_LEDGER:
            continue
        if flag.newest_confirmation is None:
            result.sentences.append(
                "Nobody has ever said %s is still right." % flag.path
            )
        else:
            accepted = report.merge_confirmations.get(flag.path)
            if accepted is not None and accepted.date == flag.newest_confirmation:
                result.sentences.append(
                    "%s was last said to be right on %s, when its owner accepted "
                    "the change that rewrote it, which is longer ago than this "
                    "base allows." % (flag.path, accepted.date.isoformat())
                )
            else:
                result.sentences.append(
                    "%s was last said to be right on %s, which is longer ago than "
                    "this base allows."
                    % (flag.path, flag.newest_confirmation.isoformat())
                )


def _already_done(
    base_root: str, base_id: str, staging, entry_id: str, target_paths, gh
) -> Optional[str]:
    """The reason this exact change does not need preparing again, or nothing."""
    if _staging_exists(base_root, staging.staging_id):
        return CODE_ALREADY_STAGED
    if _recorded_in_index(base_id, staging.staging_id):
        return CODE_ALREADY_RECORDED
    for correction in _corrections_citing(base_root):
        if correction.staging_id == staging.staging_id:
            return CODE_ALREADY_ACCEPTED
        if correction.entry_id != entry_id:
            continue
        if any(path in correction.touched_paths for path in target_paths):
            return CODE_ALREADY_ACCEPTED
    found = duplicate_check.check(staging, base_root, gh=gh)
    if found.kind == duplicate_check.KIND_MERGED:
        return CODE_ALREADY_ACCEPTED
    if found.kind in (duplicate_check.KIND_OPEN, duplicate_check.KIND_CLOSED):
        return CODE_ALREADY_PROPOSED
    return None


def _prepare_everything(
    result, report, inputs, entry_files, base_root, base_id, gh, dry_run
) -> None:
    """One prepared change per flag, and one per decision that named no files."""
    for entry_id, path in _ledger_flags(report):
        entry = base_reader.entry_by_id(inputs, entry_id)
        if entry is None:
            result.skipped.append(Skipped(None, entry_id, path, CODE_NO_ENTRY))
            continue
        try:
            staging = build_file_proposal(
                base_root, entry, entry_files.get(entry_id, ""), path
            )
        except (ValidationError, PathError) as failure:
            result.skipped.append(
                Skipped(None, entry_id, path, failure.code or CODE_MISSING_FILE)
            )
            continue
        _write_one(
            result, base_root, base_id, staging, entry_id, [path], "file", gh, dry_run
        )

    for proposal in report.affected_files_proposals:
        entry = base_reader.entry_by_id(inputs, proposal.entry_id)
        if entry is None:
            continue
        if not proposal.candidate_paths:
            result.skipped.append(
                Skipped(None, proposal.entry_id, None, CODE_NO_CANDIDATES)
            )
            result.sentences.append(
                "Decision %s does not say which files it affects, and GTM Base "
                "could not work out which files it touches." % proposal.entry_id
            )
            continue
        staging = build_affected_files_proposal(
            entry, entry_files.get(proposal.entry_id, ""), list(proposal.candidate_paths)
        )
        _write_one(
            result,
            base_root,
            base_id,
            staging,
            proposal.entry_id,
            list(proposal.candidate_paths),
            "affected-files",
            gh,
            dry_run,
        )


def _write_one(
    result, base_root, base_id, staging, entry_id, target_paths, kind, gh, dry_run
) -> None:
    reason = _already_done(base_root, base_id, staging, entry_id, target_paths, gh)
    if reason is not None:
        result.skipped.append(Skipped(staging.staging_id, entry_id, target_paths[0], reason))
        return
    path = staging_path_for(base_root, staging.staging_id)
    if not dry_run:
        save_staging(base_root, staging)
    result.staged.append(
        Staged(staging.staging_id, path, target_paths, entry_id, kind)
    )
    if kind == "affected-files":
        result.sentences.append(
            "Decision %s named no files, so GTM Base prepared a list of the %d "
            "files it looks like it touches, for you to approve."
            % (entry_id, len(target_paths))
        )
    else:
        result.sentences.append(
            "%s is out of date against decision %s, and a change for it is "
            "prepared as %s." % (target_paths[0], entry_id, staging.staging_id)
        )


def _report_the_rest(result, report, base_id, today, dry_run) -> None:
    """The parts of the answer that are the same whatever else happened."""
    if report.review_by_items:
        for item in report.review_by_items:
            result.sentences.append(
                REVIEW_BY
                % (
                    item.entry_id,
                    item.review_by.isoformat()
                    if hasattr(item.review_by, "isoformat")
                    else str(item.review_by),
                    item.days_overdue,
                )
            )
        if not dry_run:
            save_review_by_items(base_id, report.review_by_items, today)

    behind = report.ledger_behind
    if behind is not None and behind.behind:
        window = report.settings.confirmation_threshold_days
        if behind.newest_entry_date is None:
            result.sentences.append(LEDGER_BEHIND_EMPTY % window)
        else:
            result.sentences.append(
                LEDGER_BEHIND
                % (behind.newest_entry_date.isoformat(), behind.window_days, window)
            )

    _list_waiting_on_the_owner(result, report)

    if report.malformed:
        result.sentences.append(MALFORMED % len(report.malformed))
    if report.dropped:
        result.sentences.append(DROPPED % len(report.dropped))

    if (
        result.mode == "normal"
        and not result.staged
        and not report.file_flags
        and not result.drafting_refused
    ):
        result.sentences.append(NOTHING_FLAGGED)
