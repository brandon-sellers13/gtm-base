"""The four numbers one seat can honestly report for the last four weeks.

Every number here is counted from something already written down: the accepted
records in the base, this seat's own log of questions asked, the reviews on the
shared copy, and this seat's own index of what it read. Nothing is estimated,
nothing is filled in, and a number that is zero is reported as zero rather than
left out, because a missing number reads as a good one.

All four are this seat's numbers. Another person on the same base has their own
log of questions and their own index, so their numbers are their own.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
from typing import Any, Dict, List, Optional

from . import constants, formats, ghcmd, state
from .errors import PathError, ValidationError
from .fsutil import read_text
from .gitcmd import GitRunner, runner_or_default
from .validate import MARKER_PREFIX

# The window every number is counted over.
WINDOW_DAYS = 28

# The note saved with work a proposal prepared, which is how a decision nobody
# typed by hand is told from one somebody did.
DRAFTED_COMMIT_PREFIX = "Proposal "

# The decisions a catch is counted for: ones that came out of a run rather than
# out of somebody sitting down and writing them.
CAUGHT_ORIGINS = ("inbox", "ledger")

# Most reviews the summary asks the shared copy for at once.
REVIEW_LIMIT = 200

SEAT_LABEL = "These are this seat's numbers."


def _as_date(value) -> Optional[datetime.date]:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        parts = [int(part) for part in text.split("-")]
        return datetime.date(parts[0], parts[1], parts[2])
    except (ValueError, IndexError):
        return None


def _in_window(day: Optional[datetime.date], today: datetime.date) -> bool:
    """Whether a day falls in the window, which is today and the 27 before it.

    Today counts and the day 28 days ago does not, so the window is the 28 days
    the summary says it is rather than 29.
    """
    if day is None:
        return False
    return 0 <= (today - day).days < WINDOW_DAYS


def _introducing_subject(base_root: str, relative: str, git: GitRunner) -> str:
    """The note saved with the change that first added one file."""
    result = git.run(
        ["log", "--diff-filter=A", "--format=%s", "--", relative], cwd=base_root
    )
    if not result.ok:
        return ""
    subjects = [line.strip() for line in result.stdout.split("\n") if line.strip()]
    return subjects[-1] if subjects else ""


# --- Catches -----------------------------------------------------------------


def catches(
    base_root: str, git: GitRunner, today: datetime.date
) -> Dict[str, Any]:
    """Accepted records for decisions no person had entered before the run.

    A decision counts as one nobody entered by hand when the file holding it was
    first added by a prepared proposal, which the note saved with that change
    says in its own first word. A decision somebody typed and saved themselves
    carries their own note, so it is not counted, which is the point: a catch is
    something the run found, not something the person already knew.
    """
    found: List[Dict[str, Any]] = []
    considered = 0
    folder = os.path.join(base_root, constants.CORRECTIONS_DIR)
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        text = read_text(path)
        if text is None:
            continue
        try:
            correction = formats.CorrectionsFile.parse(text)
        except (ValidationError, PathError):
            continue
        if not _in_window(_as_date(correction.date), today):
            continue
        considered += 1
        if not correction.entry_id:
            continue
        entry_relative = "%s/%s.md" % (constants.DECISIONS_DIR, correction.entry_id)
        entry_text = read_text(os.path.join(base_root, entry_relative))
        if entry_text is None:
            continue
        try:
            entry = formats.LedgerEntry.parse(entry_text)
        except (ValidationError, PathError):
            continue
        if entry.origin not in CAUGHT_ORIGINS:
            continue
        subject = _introducing_subject(base_root, entry_relative, git)
        if not subject.startswith(DRAFTED_COMMIT_PREFIX):
            continue
        found.append({"entry_id": entry.id, "date": correction.date})
    return {
        "count": len(found),
        "records_in_window": considered,
        "entries": found,
    }


# --- The yes rate ------------------------------------------------------------


def yes_rate(base_id: str, today: datetime.date) -> Dict[str, Any]:
    """How often a question this seat asked was answered yes.

    Every question asked in the window is in the denominator, including the ones
    put off for now, the ones answered no, and the ones never answered at all. A
    rate that counted only the answered ones would say a seat nobody replies to
    is doing well.
    """
    rows, _problems = state.load_asked(base_id)
    counts = {outcome: 0 for outcome in constants.ASKED_OUTCOMES}
    for row in rows:
        if not _in_window(_as_date(row.get("date")), today):
            continue
        outcome = row.get("outcome")
        if outcome in counts:
            counts[outcome] += 1
    asked = sum(counts.values())
    return {
        "asked": asked,
        "yes": counts["yes"],
        "no": counts["no"],
        "not_now": counts["not-now"],
        "unanswered": counts["unanswered"],
        "rate": (float(counts["yes"]) / asked) if asked else None,
    }


# --- The rejection rate ------------------------------------------------------


def rejection_rate(
    base_root: str, gh, today: datetime.date
) -> Dict[str, Any]:
    """How often a proposal was turned down rather than accepted."""
    code, output = ghcmd.call(
        gh,
        [
            "pr",
            "list",
            "--state",
            "all",
            "--json",
            "number,state,mergedAt,closedAt,createdAt,body",
            "--limit",
            str(REVIEW_LIMIT),
        ],
        cwd=base_root,
    )
    result = {"opened": 0, "turned_down": 0, "accepted": 0, "rate": None, "read": True}
    if code != 0:
        result["read"] = False
        return result
    try:
        payload = json.loads((output or "").strip() or "[]")
    except ValueError:
        result["read"] = False
        return result
    if not isinstance(payload, list):
        result["read"] = False
        return result
    for review in payload:
        if not isinstance(review, dict):
            continue
        body = review.get("body")
        if not isinstance(body, str) or MARKER_PREFIX not in body:
            continue
        opened_on = _as_date(review.get("createdAt")) or _as_date(
            review.get("mergedAt")
        ) or _as_date(review.get("closedAt"))
        if not _in_window(opened_on, today):
            continue
        result["opened"] += 1
        merged = bool(review.get("mergedAt"))
        state_word = str(review.get("state") or "").strip().upper()
        if merged or state_word == "MERGED":
            result["accepted"] += 1
        elif state_word == "CLOSED":
            result["turned_down"] += 1
    if result["opened"]:
        result["rate"] = float(result["turned_down"]) / result["opened"]
    return result


# --- The first run's intake share --------------------------------------------


def first_run_share(base_id: str) -> Dict[str, Any]:
    """How the material this seat has read reached the base."""
    seat, _problems = state.load_seat(base_id)
    index, _more = state.load_index(base_id)
    counts = {"connected": 0, "drop": 0, "other": 0}
    for row in index.values():
        path = row.get("intake_path")
        if path in ("connected", "drop"):
            counts[path] += 1
        elif path:
            counts["other"] += 1
    named = counts["connected"] + counts["drop"]
    return {
        "first_run_path": seat.get("first_run_path"),
        "connected": counts["connected"],
        "drop": counts["drop"],
        "other": counts["other"],
        "share_connected": (float(counts["connected"]) / named) if named else None,
    }


# --- The whole summary -------------------------------------------------------


def four_week_summary(
    base_root: str,
    base_id: str,
    runner: Optional[GitRunner] = None,
    gh=None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """The four numbers, over the last four weeks, for this seat."""
    git = runner_or_default(runner)
    day = today or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    return {
        "window_days": WINDOW_DAYS,
        "from": (day - datetime.timedelta(days=WINDOW_DAYS - 1)).isoformat(),
        "to": day.isoformat(),
        "seat_label": SEAT_LABEL,
        "catches": catches(base_root, git, day),
        "yes_rate": yes_rate(base_id, day),
        "rejection_rate": rejection_rate(base_root, gh, day),
        "first_run": first_run_share(base_id),
    }


def _percent(value: Optional[float]) -> str:
    return "%d in every 100" % int(round(value * 100))


def render_summary(summary: Dict[str, Any]) -> str:
    """The summary as a person reads it, with every zero written out."""
    lines = [
        "The last %d days, from %s to %s."
        % (summary["window_days"], summary["from"], summary["to"]),
        summary["seat_label"],
        "",
    ]

    found = summary["catches"]
    lines.append(
        "Things GTM Base caught: %d. That is how many accepted records in this "
        "window are about a decision GTM Base wrote down for you rather than one "
        "you typed yourself. Accepted records in the window: %d."
        % (found["count"], found["records_in_window"])
    )

    yes = summary["yes_rate"]
    lines.append(
        "Questions asked: %d. Answered yes: %d. Answered no: %d. Put off for "
        "now: %d. Never answered: %d."
        % (yes["asked"], yes["yes"], yes["no"], yes["not_now"], yes["unanswered"])
    )
    if yes["rate"] is None:
        lines.append("No questions were asked in this window, so there is no yes rate.")
    else:
        lines.append("That is a yes about %s asked." % _percent(yes["rate"]))

    turned = summary["rejection_rate"]
    if not turned["read"]:
        lines.append(
            "GTM Base could not read the proposals on the shared copy, so it has "
            "no number for how many were turned down."
        )
    else:
        lines.append(
            "Proposals raised: %d. Accepted: %d. Turned down: %d."
            % (turned["opened"], turned["accepted"], turned["turned_down"])
        )
        if turned["rate"] is None:
            lines.append(
                "No proposals were raised in this window, so there is no turned "
                "down rate."
            )
        else:
            lines.append(
                "That is a no about %s raised." % _percent(turned["rate"])
            )

    first = summary["first_run"]
    lines.append(
        "Material read through a tool you already had connected: %d. Material "
        "you handed over yourself: %d. Anything else: %d."
        % (first["connected"], first["drop"], first["other"])
    )
    if first["share_connected"] is None:
        lines.append(
            "Nothing has been read into this base yet, so there is no share to "
            "report."
        )
    else:
        lines.append(
            "That is about %s came through a connected tool."
            % _percent(first["share_connected"])
        )
    if first["first_run_path"]:
        lines.append("Your first run used the %s path." % first["first_run_path"])
    else:
        lines.append("No first run path is recorded for this seat.")
    return "\n".join(lines)
