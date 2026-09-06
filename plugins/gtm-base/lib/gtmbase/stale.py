"""Unit 9a: what is out of date, worked out from inputs the caller hands in.

Nothing in this module reads a file, runs git, looks at the clock, or reaches
the network. The session-start hook and the stale-check skill do all of that
and hand the answers in, so the same rules can be tested on plain values and
so two seats reading the same base always reach the same result.

The vocabulary, in one place:

- A **confirmation line** is one owner saying one file is still true on one
  day. Only a line whose recorded author matches one of the file's owner
  addresses counts for anything; every other line is ignored and counted.
- An **owner's acceptance** is the same thing said a second way: when the
  person who accepted a prepared change is one of the affected file's owners,
  accepting it is that owner saying the file is right on the day they accepted
  it. It counts everywhere an owner's confirmation line counts.
- An **entry** is one decision the team wrote down. An entry is newer than a
  file's confirmation state when the file was last confirmed before the later
  of the day the decision was made and the day the entry was written.
- The **threshold** is the number of days a file may go without a confirmation
  before it is treated as out of date.
"""

from __future__ import annotations

import datetime
from collections import namedtuple
from typing import Any, Dict, List, Optional, Sequence

from . import constants
from .errors import PathError, ValidationError
from .paths import check_context_path_syntax
from .validate import read_map_settings

# --- The fixed codes this module reports ------------------------------------

# A file the ledger has moved past: an entry affects it and it was not
# confirmed against that entry.
REASON_LEDGER_NEWER = "ledger-newer"
# A file with no owner confirmation at all.
REASON_UNCONFIRMED = "unconfirmed"
# A file whose newest owner confirmation is older than the threshold.
REASON_THRESHOLD = "threshold"
# An entry that names a file the base no longer holds.
REASON_ENTRY_MISSING_FILE = "entry-affects-missing-file"

REASON_CODES = (
    REASON_LEDGER_NEWER,
    REASON_UNCONFIRMED,
    REASON_THRESHOLD,
    REASON_ENTRY_MISSING_FILE,
)

# Which of the two questions a flag would raise.
TRIGGER_LEDGER = "ledger"
TRIGGER_THRESHOLD = "threshold"

# What a confirmation carries when it came from an owner accepting a prepared
# change rather than from a line that owner saved.
TRIGGER_ACCEPTED = "accepted"

# The one finding the first run reports, in the order it is looked for.
FINDING_REQUIRED_FILE_MISSING = "required-file-missing"
FINDING_REQUIRED_ENTRY_MISSING = "required-entry-missing"
FINDING_DOCUMENT_OLDER = "document-older-than-decision"
FINDING_NOTHING_OUT_OF_DATE = "nothing-out-of-date-yet"

# What a file's status says when the person chose not to write it.
STATUS_SKIPPED = "skipped"
# What a confirmation line's trigger says when setup wrote it.
TRIGGER_DRAFTED = "drafted"
# The files the first run expects a new base to hold.
REQUIRED_FILES = ("context/strategy/icp.md", "context/strategy/positioning.md")
# The kinds a decision is assumed to touch when nothing else points anywhere.
FALLBACK_KINDS = ("icp", "positioning")

# Codes reported against something that could not be read or trusted.
MALFORMED_MISSING_ENTRY = "missing-entry"
MALFORMED_NOT_CO_MODIFIED = "corrections-file-did-not-change-the-file"
MALFORMED_HASH_MISMATCH = "corrections-file-hash-does-not-match"


# --- What the caller hands in ------------------------------------------------


class MapSettings(object):
    """The two numbers the map is allowed to set, both counted in days."""

    __slots__ = ("confirmation_threshold_days", "not_now_days")

    def __init__(
        self,
        confirmation_threshold_days=constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS,
        not_now_days=constants.DEFAULT_NOT_NOW_DAYS,
    ):
        self.confirmation_threshold_days = int(confirmation_threshold_days)
        self.not_now_days = int(not_now_days)

    @classmethod
    def from_map_text(cls, text: str) -> "MapSettings":
        """Read both settings out of the map's own text."""
        values = read_map_settings(text)
        return cls(
            confirmation_threshold_days=values["confirmation_threshold_days"],
            not_now_days=values["not_now_days"],
        )

    @classmethod
    def coerce(cls, value) -> "MapSettings":
        if isinstance(value, MapSettings):
            return value
        if value is None:
            return cls()
        if isinstance(value, dict):
            return cls(
                confirmation_threshold_days=value.get(
                    "confirmation_threshold_days",
                    constants.DEFAULT_CONFIRMATION_THRESHOLD_DAYS,
                ),
                not_now_days=value.get(
                    "not_now_days", constants.DEFAULT_NOT_NOW_DAYS
                ),
            )
        raise ValidationError("these are not map settings", code="bad-settings")

    def __repr__(self) -> str:
        return "MapSettings(confirmation_threshold_days=%d, not_now_days=%d)" % (
            self.confirmation_threshold_days,
            self.not_now_days,
        )


class ContextFileInfo(object):
    """One context file, as the caller found it on disk.

    `sources_date` is the newest date the file's `sources` field carries, or
    None when no source it names carries a date. A file with no source date is
    left out of the date comparison rather than given one.
    """

    __slots__ = ("path", "owners", "exists", "sources_date", "status", "kind")

    def __init__(
        self,
        path: str,
        owners: Optional[Sequence[str]] = None,
        exists: bool = True,
        sources_date=None,
        status: str = "",
        kind: str = "",
    ):
        self.path = path
        self.owners = list(owners or [])
        self.exists = bool(exists)
        self.sources_date = _as_date(sources_date)
        self.status = status or ""
        self.kind = kind or ""

    @property
    def skipped(self) -> bool:
        return self.status == STATUS_SKIPPED

    @property
    def present(self) -> bool:
        """Whether the base actually holds this file today."""
        return self.exists and not self.skipped

    def __repr__(self) -> str:
        return "ContextFileInfo(path=%r, status=%r)" % (self.path, self.status)


class ConfirmationRecord(object):
    """One confirmation line, with the identity the caller worked out for it.

    The line itself carries no author, so the caller reads the author from the
    change that added the line. `author_email` is None when that lookup found
    nothing, and a line with no author never counts as an owner's yes.
    """

    __slots__ = ("line", "author_email", "commit")

    def __init__(self, line, author_email: Optional[str] = None, commit=None):
        self.line = line
        self.author_email = author_email
        self.commit = commit

    def __repr__(self) -> str:
        return "ConfirmationRecord(file=%r, author_email=%r)" % (
            getattr(self.line, "file", None),
            self.author_email,
        )


class CorrectionRecord(object):
    """One accepted corrections file, with what its change actually touched.

    `co_modified_paths` are the files the change that introduced the
    corrections file also changed. `content_hash_at_commit` is one hash, worked
    out the one way the whole plugin works it out: take every path under the
    context folder that the corrections file lists in `touched_paths`, in that
    order, read each one as the introducing change left it, put the texts end to
    end, and hash the result. It is None when any of those files could not be
    read from that change.

    `merged_by_email` and `merged_on` are the address and the day of whoever
    brought the record onto the line of work the team shares. Both are None
    when the caller could not work that out. When the address is one of the
    affected file's owners, accepting the change is that owner saying the file
    is right, which is Brandon's rule of 2026-09-05.
    """

    __slots__ = (
        "file",
        "introducing_commit",
        "co_modified_paths",
        "content_hash_at_commit",
        "merged_by_email",
        "merged_on",
    )

    def __init__(
        self,
        file,
        introducing_commit=None,
        co_modified_paths: Optional[Sequence[str]] = None,
        content_hash_at_commit: Optional[str] = None,
        merged_by_email: Optional[str] = None,
        merged_on=None,
    ):
        self.file = file
        self.introducing_commit = introducing_commit
        self.co_modified_paths = list(co_modified_paths or [])
        self.content_hash_at_commit = content_hash_at_commit
        self.merged_by_email = merged_by_email
        self.merged_on = _as_date(merged_on)

    def __repr__(self) -> str:
        return "CorrectionRecord(staging_id=%r)" % (
            getattr(self.file, "staging_id", None),
        )


class LedgerInput(object):
    """One ledger file as the caller read it, whether or not it could be read.

    A file the caller could not parse arrives with `entry` None and `error`
    set. An entry that parsed is still checked here, so one library decides
    what a usable entry is.
    """

    __slots__ = ("entry", "path", "error")

    def __init__(self, entry=None, path: str = "", error: Optional[str] = None):
        self.entry = entry
        self.path = path
        self.error = error

    def __repr__(self) -> str:
        return "LedgerInput(path=%r, error=%r)" % (self.path, self.error)


class SeatInput(object):
    """What this one seat remembers, which is never shared with the team.

    `has_remote` is False for a base that has nowhere to send its work yet. A
    base with no remote is treated as already up to date, because there is
    nothing it could be behind.
    """

    __slots__ = (
        "dropped_paths",
        "asked_log",
        "suppressions",
        "ledger_behind_dismissed_until",
        "has_remote",
    )

    def __init__(
        self,
        dropped_paths: Optional[Sequence[dict]] = None,
        asked_log: Optional[Sequence[dict]] = None,
        suppressions: Optional[Dict[str, Any]] = None,
        ledger_behind_dismissed_until=None,
        has_remote: bool = True,
    ):
        self.dropped_paths = list(dropped_paths or [])
        self.asked_log = list(asked_log or [])
        self.suppressions = dict(suppressions or {})
        self.ledger_behind_dismissed_until = _as_date(ledger_behind_dismissed_until)
        self.has_remote = bool(has_remote)

    def __repr__(self) -> str:
        return "SeatInput(has_remote=%r)" % (self.has_remote,)


# --- What comes back ---------------------------------------------------------

FileFlag = namedtuple(
    "FileFlag",
    "path reason trigger entry_ids newest_confirmation non_owner_lines",
)
EntryFlag = namedtuple("EntryFlag", "entry_id path reason")
AffectedFilesProposal = namedtuple("AffectedFilesProposal", "entry_id candidate_paths")
ReviewByItem = namedtuple("ReviewByItem", "entry_id review_by days_overdue")
ReviewItem = namedtuple("ReviewItem", "path entry_id sources_date decided_on reason")
LedgerBehind = namedtuple("LedgerBehind", "behind newest_entry_date window_days")
MalformedItem = namedtuple("MalformedItem", "kind reference code")
DroppedPath = namedtuple("DroppedPath", "path_hash code entry_id")
Question = namedtuple("Question", "path trigger entry_id reason")
# One owner accepting a prepared change, kept as the evidence behind a file
# nobody has to be asked about because its owner accepted the change itself.
MergeConfirmation = namedtuple("MergeConfirmation", "path date entry_id merged_by")
Finding = namedtuple("Finding", "code path date entry_id")


class StaleReport(object):
    """Everything one stale-check run needs to say, and nothing it has to fetch."""

    def __init__(
        self,
        today,
        settings,
        files,
        entries,
        file_flags,
        entry_flags,
        affected_files_proposals,
        review_by_items,
        review_items,
        ledger_behind,
        malformed,
        dropped,
        has_remote,
    ):
        self.today = today
        self.settings = settings
        self.files = files
        self.entries = entries
        self.file_flags = list(file_flags)
        self.entry_flags = list(entry_flags)
        self.affected_files_proposals = list(affected_files_proposals)
        self.review_by_items = list(review_by_items)
        self.review_items = list(review_items)
        self.ledger_behind = ledger_behind
        self.malformed = list(malformed)
        self.dropped = list(dropped)
        self.has_remote = bool(has_remote)
        self.suppressions = {}
        # Keyed by path: the newest acceptance by one of that file's owners,
        # which is why the file may carry a confirmation nobody typed.
        self.merge_confirmations: Dict[str, MergeConfirmation] = {}

    # A base with nowhere to send its work cannot be behind anyone.
    @property
    def treat_as_fast_forwarded(self) -> bool:
        return not self.has_remote

    @property
    def summary_counts(self) -> Dict[str, int]:
        behind = self.ledger_behind
        return {
            "files_flagged": len(self.file_flags),
            "entries_flagged": len(self.entry_flags),
            "affected_files_proposals": len(self.affected_files_proposals),
            "review_by_items": len(self.review_by_items),
            "review_items": len(self.review_items),
            "malformed": len(self.malformed),
            "dropped": len(self.dropped),
            "ledger_behind": 1 if (behind is not None and behind.behind) else 0,
        }

    def candidate_questions(self, owner_email: Optional[str] = None) -> List[Question]:
        """The questions this owner could be asked, best one first.

        Ledger questions come before threshold questions, because a decision
        the team already made is a better reason to ask than the calendar. A
        file this owner does not own, a file that was set aside for now, and a
        file the person chose not to write are all left out. One decision
        raises at most one question, so a decision that touches three files
        does not ask three times.
        """
        ledger_questions = []
        threshold_questions = []
        seen_entries = set()
        for flag in self.file_flags:
            info = self.files.get(flag.path)
            if info is None or not info.present:
                continue
            if owner_email is not None and owner_email not in info.owners:
                continue
            if self._suppressed(flag.path):
                continue
            if flag.trigger == TRIGGER_LEDGER:
                entry_id = flag.entry_ids[0] if flag.entry_ids else None
                if entry_id is not None and entry_id in seen_entries:
                    continue
                if entry_id is not None:
                    seen_entries.add(entry_id)
                ledger_questions.append(
                    Question(flag.path, TRIGGER_LEDGER, entry_id, flag.reason)
                )
            else:
                threshold_questions.append(
                    Question(flag.path, TRIGGER_THRESHOLD, None, flag.reason)
                )
        return ledger_questions + threshold_questions

    def _suppressed(self, path: str) -> bool:
        until = _as_date(self.suppressions.get(path))
        if until is None:
            return False
        return self.today < until

    def first_run_finding(
        self,
        required_files: Sequence[str] = REQUIRED_FILES,
        required_entry: bool = True,
    ) -> Finding:
        """The one honest thing to say at the end of a first run.

        The order is fixed so every run of the same base says the same thing: a
        file the person did not write, then a document older than the decision
        it is supposed to reflect, then the plain statement that nothing is out
        of date yet, naming the earliest date it will watch.
        """
        for path in required_files:
            info = self.files.get(path)
            if info is None or not info.present:
                return Finding(FINDING_REQUIRED_FILE_MISSING, path, None, None)
        if required_entry and not self.entries:
            return Finding(FINDING_REQUIRED_ENTRY_MISSING, None, None, None)
        if self.review_items:
            item = self.review_items[0]
            return Finding(
                FINDING_DOCUMENT_OLDER, item.path, item.sources_date, item.entry_id
            )
        review_by = None
        entry_id = None
        for entry in self.entries:
            if entry.status != "open":
                continue
            candidate = _as_date(entry.review_by)
            if candidate is None:
                continue
            if review_by is None or candidate < review_by:
                review_by = candidate
                entry_id = entry.id
        return Finding(FINDING_NOTHING_OUT_OF_DATE, None, review_by, entry_id)

    def __repr__(self) -> str:
        return "StaleReport(%r)" % (self.summary_counts,)


# --- Small helpers -----------------------------------------------------------


def _as_date(value):
    """Read a date from a date, an ISO day, or nothing at all."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            parts = [int(part) for part in value.strip().split("-")]
        except ValueError:
            raise ValidationError("this is not a date", code="bad-date")
        if len(parts) != 3:
            raise ValidationError("this is not a date", code="bad-date")
        try:
            return datetime.date(parts[0], parts[1], parts[2])
        except ValueError:
            raise ValidationError("this is not a date", code="bad-date")
    raise ValidationError("this is not a date", code="bad-date")


def _text_of(entry) -> str:
    """Everything about an entry a file name could plausibly be mentioned in."""
    return " ".join(
        str(part or "")
        for part in (entry.body, entry.source, entry.decided_by)
    ).lower()


def _stem(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0].lower()


# --- The computation ---------------------------------------------------------


def compute(
    today,
    settings,
    files: Sequence[ContextFileInfo],
    ledger: Sequence[LedgerInput],
    confirmations: Sequence[ConfirmationRecord],
    corrections: Sequence[CorrectionRecord],
    seat: Optional[SeatInput] = None,
    owner_email: Optional[str] = None,
    map_hints: Optional[Dict[str, Sequence[str]]] = None,
) -> StaleReport:
    """Work out what is out of date, from values only.

    `owner_email` narrows the flags to the files this seat's owner owns. Left
    out, every file is considered, which is what the whole-base report wants.
    """
    day = _as_date(today)
    if day is None:
        raise ValidationError("the run needs a date to compare against", code="no-today")
    options = MapSettings.coerce(settings)
    seat = seat or SeatInput()
    malformed: List[MalformedItem] = []

    known = _index_files(files, malformed)
    entries = _usable_entries(ledger, day, malformed)
    owner_lines, non_owner_counts = _index_confirmations(known, confirmations, malformed)
    settled, accepted = _corrections_confirmations(known, corrections, malformed)

    file_flags = _file_flags(
        day,
        options,
        known,
        entries,
        owner_lines,
        non_owner_counts,
        settled,
        accepted,
        owner_email,
    )
    entry_flags = _entry_flags(known, entries)
    proposals = _affected_files_proposals(known, entries, map_hints)
    review_by_items = _review_by_items(day, entries)
    review_items = _review_items(known, entries, owner_lines)
    ledger_behind = _ledger_behind(day, options, entries, seat)
    dropped = [
        DroppedPath(
            row.get("path_hash"), row.get("code"), row.get("entry_id")
        )
        for row in seat.dropped_paths
        if isinstance(row, dict)
    ]

    report = StaleReport(
        today=day,
        settings=options,
        files=known,
        entries=entries,
        file_flags=file_flags,
        entry_flags=entry_flags,
        affected_files_proposals=proposals,
        review_by_items=review_by_items,
        review_items=review_items,
        ledger_behind=ledger_behind,
        malformed=malformed,
        dropped=dropped,
        has_remote=seat.has_remote,
    )
    report.suppressions = dict(seat.suppressions)
    report.merge_confirmations = dict(accepted)
    return report


def _index_files(files, malformed) -> "Dict[str, ContextFileInfo]":
    known: Dict[str, ContextFileInfo] = {}
    for info in files or []:
        try:
            path = check_context_path_syntax(info.path)
        except (PathError, ValidationError) as failure:
            malformed.append(MalformedItem("file", info.path, failure.code))
            continue
        known[path] = info
    return known


def _usable_entries(ledger, day, malformed) -> list:
    entries = []
    for item in ledger or []:
        if item.error:
            malformed.append(MalformedItem("ledger", item.path or "", item.error))
            continue
        if item.entry is None:
            malformed.append(
                MalformedItem("ledger", item.path or "", MALFORMED_MISSING_ENTRY)
            )
            continue
        try:
            item.entry.validate(day)
        except (ValidationError, PathError) as failure:
            malformed.append(
                MalformedItem(
                    "ledger", item.path or item.entry.id or "", failure.code
                )
            )
            continue
        entries.append(item.entry)
    entries.sort(key=lambda entry: (entry.written_on, entry.id))
    return entries


def _index_confirmations(known, confirmations, malformed):
    """Split the lines into the owner's yes lines and everybody else's."""
    owner_lines: Dict[str, List[Any]] = {}
    non_owner_counts: Dict[str, int] = {}
    for record in confirmations or []:
        line = record.line
        try:
            line.validate()
        except (ValidationError, PathError) as failure:
            malformed.append(
                MalformedItem("confirmation", getattr(line, "file", ""), failure.code)
            )
            continue
        info = known.get(line.file)
        if info is None:
            continue
        if record.author_email is not None and record.author_email in info.owners:
            owner_lines.setdefault(line.file, []).append(line)
        else:
            non_owner_counts[line.file] = non_owner_counts.get(line.file, 0) + 1
    return owner_lines, non_owner_counts


def _corrections_confirmations(known, corrections, malformed):
    """What an accepted corrections file really does confirm.

    Three things have to be true before an accepted record settles a decision
    for a file: the record names the decision, the change that introduced the
    record also changed that file, and the one hash over every context file the
    record lists, in the order it lists them, is the hash the record carries.

    A record that passes all three says one more thing when the person who
    accepted it owns the file: accepting the change is that owner saying the
    file is right on the day they accepted it. That is Brandon's rule of
    2026-09-05. A record accepted by anybody else settles the decision and
    nothing more.

    Two things come back: the set of (decision, file) pairs that are settled,
    and, keyed by file, the newest acceptance by one of that file's owners.
    """
    settled = set()
    accepted: Dict[str, MergeConfirmation] = {}
    for record in corrections or []:
        correction = record.file
        entry_id = getattr(correction, "entry_id", None)
        if not entry_id:
            continue
        for path in getattr(correction, "touched_paths", []) or []:
            if path not in known:
                continue
            if path not in record.co_modified_paths:
                malformed.append(
                    MalformedItem(
                        "corrections",
                        getattr(correction, "staging_id", path),
                        MALFORMED_NOT_CO_MODIFIED,
                    )
                )
                continue
            recorded = record.content_hash_at_commit
            if not recorded or recorded != getattr(correction, "content_hash", None):
                malformed.append(
                    MalformedItem(
                        "corrections",
                        getattr(correction, "staging_id", path),
                        MALFORMED_HASH_MISMATCH,
                    )
                )
                continue
            settled.add((entry_id, path))
            merged_on = _as_date(record.merged_on)
            merged_by = record.merged_by_email
            if merged_on is None or not merged_by:
                continue
            if merged_by not in known[path].owners:
                continue
            standing = accepted.get(path)
            if standing is None or merged_on > standing.date:
                accepted[path] = MergeConfirmation(
                    path, merged_on, entry_id, merged_by
                )
    return settled, accepted


class _AcceptedLine(object):
    """An owner's acceptance, shaped like the confirmation line it stands for.

    It names no decision and carries no run, so it settles a decision only the
    way any dated line does, by being later than the decision. The pair it was
    accepted for is already settled by the record itself.
    """

    __slots__ = ("file", "date", "trigger", "entry", "run")

    def __init__(self, path: str, date):
        self.file = path
        self.date = date
        self.trigger = TRIGGER_ACCEPTED
        self.entry = None
        self.run = None

    def __repr__(self) -> str:
        return "_AcceptedLine(file=%r, date=%r)" % (self.file, self.date)


def _line_confirms(line, entry) -> bool:
    """Whether one owner line settles one decision for one file.

    A line that names the decision settles it whatever day it carries, because
    naming the decision is the owner saying they were shown this decision and
    the file together. That is exactly what an answer given on the day the
    decision was written down looks like, so it is checked first.

    A line that names no decision has only its date to go on, and a date of the
    day the decision was made proves nothing, because the answer could have
    been given before the decision existed. The one exception is setup, which
    writes the file and the answer in the same run and says so by carrying the
    same run on both.
    """
    decided = _as_date(entry.decided_on)
    written = _as_date(entry.written_on)
    line_date = _as_date(line.date)
    if line.entry and line.entry == entry.id:
        return True
    if line_date == decided:
        return bool(
            line.trigger == TRIGGER_DRAFTED
            and line.run
            and entry.run_id
            and line.run == entry.run_id
        )
    later = written if written > decided else decided
    return line_date > later


def _file_flags(
    day,
    options,
    known,
    entries,
    owner_lines,
    non_owner_counts,
    settled,
    accepted,
    owner_email,
):
    flags = []
    for path in sorted(known):
        info = known[path]
        if not info.present:
            continue
        if owner_email is not None and owner_email not in info.owners:
            continue
        lines = list(owner_lines.get(path, []))
        acceptance = accepted.get(path)
        if acceptance is not None:
            lines.append(_AcceptedLine(path, acceptance.date))
        newest = None
        for line in lines:
            line_date = _as_date(line.date)
            if newest is None or line_date > newest:
                newest = line_date
        unconfirmed_entries = []
        for entry in entries:
            if entry.status != "open" or path not in entry.affects:
                continue
            if (entry.id, path) in settled:
                continue
            if any(_line_confirms(line, entry) for line in lines):
                continue
            unconfirmed_entries.append(entry.id)
        non_owner = non_owner_counts.get(path, 0)
        if unconfirmed_entries:
            reason = REASON_UNCONFIRMED if newest is None else REASON_LEDGER_NEWER
            flags.append(
                FileFlag(
                    path, reason, TRIGGER_LEDGER, unconfirmed_entries, newest, non_owner
                )
            )
            continue
        if newest is None:
            flags.append(
                FileFlag(
                    path, REASON_UNCONFIRMED, TRIGGER_THRESHOLD, [], None, non_owner
                )
            )
            continue
        if (day - newest).days > options.confirmation_threshold_days:
            flags.append(
                FileFlag(
                    path, REASON_THRESHOLD, TRIGGER_THRESHOLD, [], newest, non_owner
                )
            )
    return flags


def _entry_flags(known, entries):
    """A decision that names a file the base no longer holds flags itself."""
    flags = []
    for entry in entries:
        if entry.status != "open":
            continue
        for path in entry.affects:
            info = known.get(path)
            if info is None or not info.exists:
                flags.append(EntryFlag(entry.id, path, REASON_ENTRY_MISSING_FILE))
    return flags


def _affected_files_proposals(known, entries, map_hints):
    """Name the files a decision touches when the person left that blank.

    The rule is deliberately small and stated here in full. A path the caller's
    map hints attach to a word the entry uses is a candidate. So is any context
    file whose own name, or whose kind, the entry mentions. When neither points
    anywhere, the candidates are every ideal customer profile and positioning
    file the base holds, because those are the files a decision most often
    moves. A file the base does not hold is never a candidate.
    """
    hints = {str(key).lower(): list(value) for key, value in (map_hints or {}).items()}
    proposals = []
    for entry in entries:
        if entry.status != "open" or entry.affects:
            continue
        text = _text_of(entry)
        candidates = set()
        for word, paths in hints.items():
            if word and word in text:
                candidates.update(paths)
        for path, info in known.items():
            if not info.present:
                continue
            stem = _stem(path)
            if stem and stem in text:
                candidates.add(path)
            elif info.kind and info.kind.lower() in text:
                candidates.add(path)
        if not candidates:
            candidates = {
                path
                for path, info in known.items()
                if info.present and info.kind.lower() in FALLBACK_KINDS
            }
        candidates = {path for path in candidates if path in known and known[path].present}
        proposals.append(AffectedFilesProposal(entry.id, sorted(candidates)))
    return proposals


def _review_by_items(day, entries):
    items = []
    for entry in entries:
        if entry.status != "open":
            continue
        review_by = _as_date(entry.review_by)
        if review_by is None or review_by >= day:
            continue
        items.append(ReviewByItem(entry.id, review_by, (day - review_by).days))
    return items


def _review_items(known, entries, owner_lines):
    """Documents setup wrote from material older than the decision itself."""
    items = []
    for path in sorted(known):
        info = known[path]
        if not info.present or info.sources_date is None:
            continue
        runs = set()
        for line in owner_lines.get(path, []):
            if line.trigger == TRIGGER_DRAFTED and line.run:
                runs.add(line.run)
        if not runs:
            continue
        for entry in entries:
            if not entry.run_id or entry.run_id not in runs:
                continue
            decided = _as_date(entry.decided_on)
            if decided is None or info.sources_date >= decided:
                continue
            items.append(
                ReviewItem(
                    path,
                    entry.id,
                    info.sources_date,
                    decided,
                    FINDING_DOCUMENT_OLDER,
                )
            )
    return items


def _ledger_behind(day, options, entries, seat):
    """Whether the ledger looks behind on age alone, and by when."""
    window = options.confirmation_threshold_days
    dismissed = seat.ledger_behind_dismissed_until
    # Left alone up to, but not including, the day it comes back, which is the
    # same boundary a file put off for now is left alone by.
    if dismissed is not None and day < dismissed:
        return None
    newest = None
    for entry in entries:
        written = _as_date(entry.written_on)
        if written is not None and (newest is None or written > newest):
            newest = written
    behind = newest is None or (day - newest).days > window
    return LedgerBehind(behind, newest, window)
