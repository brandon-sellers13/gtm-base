"""Setting a base up, from the first question to the closing sentence.

This is the library behind the join skill. The skill does the talking; every
step that touches the disk happens here, in the order a person lives through
it: where their material lives, where the base will go, what would be read,
the yes that fixes that list, one draft at a time, and the closing.

Two things are worth knowing about the shape.

The run has a folder of its own. Setting a base up takes several separate
calls, and a person's pasted text and the requests built from it have to
survive between them, so each run gets a folder inside this person's own seat
folder, readable by them and nobody else. It holds what they pasted, the list
of files they agreed to, and the request built for each step. The closing step
deletes it. Nothing in it is ever written into the base and nothing in it is
ever sent anywhere.

Everything else here is wiring. The listing, the consent, the fencing, the
prompts, the screen, and the writing all live in modules of their own that were
built and tested before this one. What this module adds is the order, the run
folder, and the closing: one honest finding, the note about what got in the
way, the answer to the offer, and the message that says where the base is and
how to come back to it.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import shutil
import stat
import tempfile
import threading
from typing import List, Optional, Sequence

from . import (
    adopt,
    base_reader,
    callmarkers,
    confirm,
    constants,
    create_base,
    drafting,
    extract,
    formats,
    fsutil,
    ids,
    layout,
    location,
    machine,
    marker,
    moment,
    names,
    paths,
    review,
    segments,
    sources as sources_module,
    stale_check,
    state,
    validate,
    wordsfile,
)
from .errors import (
    ConsentError,
    DraftError,
    GtmBaseError,
    PathError,
    ReviewError,
    SourceRejected,
    StateError,
    ValidationError,
)
from .fsutil import (
    HeldLock,
    atomic_write_json,
    atomic_write_text,
    ensure_dir,
    read_bytes,
    read_json,
    read_text,
)
from .gitcmd import GitRunner, runner_or_default

# What the run folder holds.
CONSENT_FILE = "consent.json"
LISTING_FILE = "listing.json"
SURVEY_FILE = "survey.json"
# The part of the company the person said the base is for (Unit 1.7a). It is
# held here because the profile that will carry it does not exist yet.
SCOPE_FILE = "scope.json"
PASTES_DIR = "pastes"

# What the folder holding one run's drafts is called, under the folder this
# computer keeps temporary work in. `wordsfile` owns it now, because a
# person's own answers go in a folder beside the drafts and both are held to
# the same rules.
DRAFTS_PARENT = wordsfile.PARENT_NAME

# A change cannot be shown at all without the base it is for.
CODE_NEEDS_THE_BASE = "needs-the-base"
NEEDS_THE_BASE = (
    "GTM Base cannot show that change without knowing which base it is for, "
    "so nothing was shown. Run it again and say which base."
)

# Why a yes could not be taken.
CODE_NO_LISTING = "no-listing"
CODE_LISTING_CHANGED = "listing-changed"
# The list shown was large and spread out and nobody said which folders matter,
# so the yes is not taken over the whole of it.
CODE_NARROW_FIRST = "narrow-first"
# A folder was named that the list does not hold.
CODE_NO_SUCH_FOLDER = "no-such-folder"
# A folder named to add is not directly inside the folder being looked
# through, so no folder of the listing is the one they meant (finding N4 of
# Astra's fourth look).
CODE_ADDED_NOT_DIRECTLY_INSIDE = "added-folder-not-directly-inside"
ADDED_NOT_DIRECTLY_INSIDE = (
    "The folder named to add is not directly inside the folder being looked "
    "through, so nothing was shown. Ask for a folder that sits directly "
    "inside it instead."
)
# A list was asked for from a finding step that has not been run for this run.
CODE_NO_SURVEY = "no-survey"
# Every place the finding step proposed was dropped and none was added, so
# there is nothing left to show.
CODE_NO_FOLDERS_CHOSEN = "no-folders-chosen"
# A different list was shown after the yes was given, so the yes does not
# carry over to it and nothing is read until that list has one (Unit 1.6).
CODE_ASK_AGAIN = "asks-again"
# The note about what got in the way could not be saved into the base.
NOTE_NOT_SAVED = "note-not-saved"

# The modes this release does not do yet, and the one it never does while the
# session is holding text nobody has vetted.
MODE_BACKUP = "backup"
MODE_INVITE = "invite"
MODE_JOIN_LINK = "join-link"
NOT_IN_THIS_RELEASE = {
    MODE_BACKUP: constants.BACKUP_NOT_IN_THIS_RELEASE,
    MODE_INVITE: constants.INVITE_NOT_IN_THIS_RELEASE,
    MODE_JOIN_LINK: constants.JOIN_LINK_NOT_IN_THIS_RELEASE,
}

# What the closing step writes, and where.
ONBOARDING_NOTE_KIND = "onboarding-note"
ONBOARDING_NOTE_HEADING = "What got in the way"
ONBOARDING_NOTE_MESSAGE = "Add the note from setting the base up"
NOTE_NOT_WRITTEN = (
    "That note was not written down, because it held something that must not "
    "be saved into the base."
)
NOTE_NOT_SAVED_MESSAGE = (
    "That note could not be saved into the base, so the rest of the closing "
    "carried on without it."
)

# Where the closing message lives, so the sentences a person reads are one
# document a person can edit rather than strings scattered through code.
CLOSING_RULES = os.path.join("skills", "join", "references", "closing-rules.md")
CLOSING_MARKER = "## The closing message"
CLOSING_LINKED_MARKER = "## The closing message when a folder is linked"
# The three sentences, the example, and the one request that make up the
# closing question live in the same document for the same reason the closing
# message does: they are words a person reads, so they belong somewhere a
# person can read and edit them rather than in a string in this file.
CLOSING_QUESTION_MARKER = "## The closing question"

# The four labels one context change is shown by, and the markers around them.
# `docs/ux-standard.md` is where the form comes from and
# `plugins/gtm-base/templates/change-four-lines.md` holds it as a template.
CHANGE_OPEN = "<!-- change -->"
CHANGE_CLOSE = "<!-- end change -->"
ARTIFACT_OPEN = "<!-- artifact -->"
ARTIFACT_CLOSE = "<!-- end artifact -->"
CHANGE_LABELS = (
    "What changed:",
    "Why:",
    "What it affects:",
    "When to look again:",
)

# The three facts about a change that are the person's to correct before it is
# written down, each named the way they would say it. "Who noted it" was on
# this list until finding A10 of the release review: the address is written by
# GTM Base a moment after the preview, so offering it as correctable was
# taking a correction and throwing it away.
DETAIL_LABELS = (
    "The day it happened",
    "What it affects",
    "When to look at it again",
)
# Said under the three, so nobody is left wondering why the address on the
# change is not theirs to set.
NOTED_BY_IS_THE_BASES_RECORD = (
    "Who noted this is the address your base records your work under, so it is "
    "not one of the things to correct here."
)

# Said as the "why" line when the sentence somebody gave at the closing is one
# sentence and holds no separate reason. It is only ever reached for a change
# that came out of the closing question, where it is the whole of the truth.
WHY_FROM_THE_CLOSING = (
    "You said so when you were setting your base up."
)
ENTRY_PREVIEW_ASK = (
    "Approve this, correct anything in it, skip it, or say what is wrong with it."
)
# One reconciliation question, asked once per document and never about two at
# once. Requirement P6, and Codex condition B: a document is only settled
# against a change by somebody saying it is.
RECONCILE_ASK = "Does %s already say what that change says?"
RECONCILE_RECORDED = (
    "%s is written down as already saying what that change says."
)
RECONCILE_FLAGGED = (
    "%s has not caught up with that change, so it stays flagged and GTM Base "
    "has prepared a change for it to be approved."
)
RECONCILE_NOT_PREPARED = (
    "%s has not caught up with that change, so it stays flagged. GTM Base "
    "could not prepare a change for it, so that one is yours to make."
)
# Ruling 4 of the acceptance matrix. Only the two required documents are asked
# about at the closing, and everything else the change reaches is said in one
# line and picked up by the review.
OTHERS_FLAGGED_ONE = (
    "One other document this change affects is left flagged for your next review."
)
OTHERS_FLAGGED_MANY = (
    "%d other documents this change affects are left flagged for your next review."
)
# Skip is a whole answer. Requirement P7.
SKIP_RECORDED = (
    "Nothing was written down, and GTM Base will not mention the quiet record "
    "of context changes again until %s."
)


class Assembled(object):
    """One request, written down, with what went into it and what did not."""

    __slots__ = (
        "path",
        "step",
        "included_labels",
        "dropped_labels",
        "codes",
        "left_out",
        "removed",
        "superseded",
    )

    def __init__(
        self,
        path,
        step,
        included_labels,
        dropped_labels,
        codes=None,
        left_out=None,
        removed=None,
        superseded=None,
    ):
        self.path = path
        self.step = step
        self.included_labels = list(included_labels)
        self.dropped_labels = list(dropped_labels)
        self.codes = list(codes or [])
        # Pairs of the label and the reason, one for each source that could not
        # be used at all, as against the ones dropped for length.
        self.left_out = list(left_out or [])
        # Pairs of the label and the counts of what was taken out of it.
        self.removed = list(removed or [])
        # Each version of a document left out because another version of it
        # was used (Unit 1.6).
        self.superseded = list(superseded or [])

    def __repr__(self) -> str:
        return "Assembled(step=%r, included=%d)" % (
            self.step,
            len(self.included_labels),
        )


class Previewed(object):
    """What one step would read, worked out without writing anything down."""

    __slots__ = (
        "step",
        "included_labels",
        "dropped_labels",
        "ordered_labels",
        "codes",
        "left_out",
        "removed",
        "total",
        "superseded",
        "choice",
        "narrowed",
    )

    def __init__(
        self,
        step,
        included_labels,
        dropped_labels,
        ordered_labels,
        codes=None,
        left_out=None,
        removed=None,
        superseded=None,
        choice=None,
        narrowed=False,
    ):
        self.step = step
        self.included_labels = list(included_labels)
        self.dropped_labels = list(dropped_labels)
        self.ordered_labels = list(ordered_labels)
        self.codes = list(codes or [])
        self.left_out = list(left_out or [])
        self.removed = list(removed or [])
        # Each version of a document left out because another version of it
        # was used, with the reason and whether the two say different things.
        self.superseded = list(superseded or [])
        # Whether the list this draft reads from was folders the person named
        # or a plain yes to a proposal. Only a plain yes is asked, before a
        # draft, whether to narrow it (ruling 2 of the acceptance matrix).
        self.choice = choice or constants.CHOICE_PLAIN_YES
        # Whether the person narrowed this draft to part of the list. A draft
        # they narrowed has had its question answered, so it is not asked
        # again (finding 3 of the unit's correctness review).
        self.narrowed = bool(narrowed)
        # Every document named for this step, including the ones that could
        # not be used at all and the versions another version stood in for,
        # which is the number the person recognises as the size of their own
        # folder.
        self.total = (
            len(self.ordered_labels) + len(self.left_out) + len(self.superseded)
        )

    def __repr__(self) -> str:
        return "Previewed(step=%r, included=%d, dropped=%d)" % (
            self.step,
            len(self.included_labels),
            len(self.dropped_labels),
        )


class Reviewed(object):
    """What the checks made of one draft before anybody was asked about it.

    `questions` is how many `[your call: ...]` markers the draft carries, the
    questions it leaves for the person (Unit 1.7b).
    """

    __slots__ = ("step", "ready", "codes", "draft", "questions")

    def __init__(self, step, ready, codes=None, draft=None, questions=0):
        self.step = step
        self.ready = bool(ready)
        self.codes = list(codes or [])
        self.draft = draft
        self.questions = int(questions or 0)

    def __repr__(self) -> str:
        return "Reviewed(step=%r, ready=%r, codes=%r)" % (
            self.step,
            self.ready,
            self.codes,
        )


class CloseResult(object):
    """Everything the last step of setting a base up produced."""

    __slots__ = (
        "finding",
        "note_path",
        "note_codes",
        "closing",
        "answer_recorded",
        "import_unfinished",
        "drafts_unfinished",
    )

    def __init__(
        self,
        finding,
        closing,
        note_path=None,
        note_codes=None,
        answer_recorded=False,
        import_unfinished=False,
        drafts_unfinished=False,
    ):
        self.finding = finding
        self.closing = closing
        self.note_path = note_path
        self.note_codes = list(note_codes or [])
        self.answer_recorded = bool(answer_recorded)
        # Some finished pages chosen for the base are not in it yet, and the
        # record that lets a later session finish them was kept (Unit 1.7d).
        self.import_unfinished = bool(import_unfinished)
        # Some of what is still to finish is a segment to draft, which a later
        # session drafts after asking again to read its material (call 29).
        self.drafts_unfinished = bool(drafts_unfinished)

    def __repr__(self) -> str:
        return "CloseResult(note=%r)" % (self.note_path,)


# --- The run's own folder ----------------------------------------------------


def join_home() -> str:
    """The folder inside this person's seat folder holding every setup run."""
    return ensure_dir(os.path.join(paths.seat_home(), constants.JOIN_SCRATCH_DIR))


def scratch_dir(run_id: str) -> str:
    """The folder one setup run works in. Owner only, and deleted at the end."""
    ids.check_run_id(run_id)
    return ensure_dir(os.path.join(join_home(), run_id))


def new_run(today: Optional[datetime.date] = None) -> str:
    """Start a run: a dated identifier, and the folder it works in.

    Every folder left behind by a run from an earlier day is cleared away
    first. A run that stopped part way, because the window was closed or the
    machine went down, never reaches its closing step, so nothing else would
    ever delete what it was holding, and what it was holding is the text the
    person pasted in.
    """
    day = today or datetime.date.today()
    sweep_old_runs(day)
    sweep_drafts_without_a_run()
    run_id = ids.run_id(day)
    scratch_dir(run_id)
    return run_id


def sweep_old_runs(today: Optional[datetime.date] = None) -> List[str]:
    """Delete the folders of runs from an earlier day. Returns what went.

    The rules are the ones that hold for deleting a half built base folder.
    Only folders sitting directly inside the runs folder are looked at, only
    names that are run identifiers are considered, a link is never followed,
    and the day in the name has to be a real day earlier than today.
    """
    day = today or datetime.date.today()
    home = join_home()
    removed: List[str] = []
    try:
        names = sorted(os.listdir(home))
    except OSError:
        return removed
    for name in names:
        if not ids.is_run_id(name):
            continue
        folder = os.path.join(home, name)
        if os.path.islink(folder) or not os.path.isdir(folder):
            continue
        if os.path.dirname(os.path.abspath(folder)) != os.path.abspath(home):
            continue
        when = _day_of_run(name)
        if when is None or when >= day:
            continue
        shutil.rmtree(folder, ignore_errors=True)
        clear_drafts(name)
        if not os.path.isdir(folder):
            removed.append(name)
    return removed


def _day_of_run(run_id: str) -> Optional[datetime.date]:
    """The day a run identifier is named after, or None when it names none."""
    parts = run_id.split("-")
    if len(parts) < 5:
        return None
    try:
        return datetime.date(int(parts[1]), int(parts[2]), int(parts[3]))
    except ValueError:
        return None


def clear_scratch(run_id: str) -> bool:
    """Delete everything one run was working with. Returns whether there was any."""
    ids.check_run_id(run_id)
    folder = os.path.join(join_home(), run_id)
    drafts_gone = clear_drafts(run_id)
    if not os.path.isdir(folder):
        return drafts_gone
    shutil.rmtree(folder, ignore_errors=True)
    return not os.path.isdir(folder)


def write_paste(run_id: str, label: str, text: str, session_id: str) -> str:
    """Hold a piece of pasted text for the rest of this run, and nowhere else.

    It is screened here, as everything read is, so text that must never reach a
    prompt never reaches the folder either.

    This is also where the marker gets written on the paste route. A person can
    set a base up without ever naming a folder, by pasting their material in or
    by handing over a PDF, a web page, or something a connected tool returned,
    and every one of those arrives here. The session is then holding text
    nobody has vetted just as surely as if a folder had been read, so the
    safeguard has to know it before the text lands anywhere.
    """
    marker.write_sources_read_marker(session_id)
    source = sources_module.make_source(label, text, "paste")
    folder = ensure_dir(os.path.join(scratch_dir(run_id), PASTES_DIR))
    path = os.path.join(folder, _file_name_for(source.label) + ".txt")
    atomic_write_text(path, source.text, inside=paths.seat_home())
    return path


def _file_name_for(label: str) -> str:
    keep = [character if character.isalnum() else "-" for character in label]
    name = "".join(keep).strip("-")
    return name or "paste"


# --- Where the base goes -----------------------------------------------------


def propose_location(
    company: str,
    cwd: Optional[str] = None,
    content_folder: Optional[str] = None,
    confirmed_home: bool = False,
    runner: Optional[GitRunner] = None,
    beside: bool = False,
):
    """Where this person's base would go, and the sentence that says so.

    The folder they named is not where the base goes. It is the folder the base
    will be recorded as belonging with, so that opening Claude Code there brings
    the base along. `beside` is them asking, in words, for the base to sit in
    that folder after all.
    """
    return location.propose_target(
        cwd or os.getcwd(),
        company,
        named_content_folder=content_folder,
        runner=runner,
        confirmed_home=confirmed_home,
        beside=beside,
    )


# --- The folder a base belongs with ------------------------------------------


# Why a base could not be found from what the person called it.
NO_SUCH_BASE = "no-base"
MORE_THAN_ONE_BASE = "more-than-one-base"


def _named_base(named: Optional[str], runner: Optional[GitRunner] = None):
    """The one base this account has under this company name, or a refusal.

    Connecting a folder has to work from a session that has no base in it at
    all, which is the ordinary case: the person is sitting in their own folder
    and that is exactly the folder they want to connect. So a base can be named
    by the company it is for as well as by its folder. What is matched is the
    folder the base sits in, which for every base built centrally is the folder
    named for the company.
    """
    wanted = (named or "").strip().casefold()
    if not wanted:
        raise GtmBaseError("no base was named", NO_SUCH_BASE)
    found = []
    for entry in machine.load_machine_state_raw().joined:
        root = entry.get("root")
        if not isinstance(root, str):
            continue
        company = os.path.basename(os.path.dirname(root.rstrip(os.sep)))
        if company.casefold() == wanted:
            found.append(entry)
    if not found:
        raise GtmBaseError("no base of that name on this computer", NO_SUCH_BASE)
    if len(found) > 1:
        failure = GtmBaseError("more than one base of that name", MORE_THAN_ONE_BASE)
        failure.roots = sorted(str(entry.get("root") or "") for entry in found)
        raise failure
    return found[0]


def find_base(
    named: Optional[str], cwd: Optional[str] = None, runner: Optional[GitRunner] = None
):
    """The base a person meant, whether they gave its folder, its name, or neither.

    A folder is tried first, because a folder says exactly which base is meant.
    What they gave is then read as the name of a company and looked up in the
    list of bases.

    When they named nothing at all, which is the ordinary case for somebody
    sitting in their own folder saying to connect it, the folder they are in is
    tried, and then the list itself: on an account with one base there is
    nothing to be ambiguous about, and on an account with more than one they are
    asked which, rather than one being picked for them.
    """
    git = runner_or_default(runner)
    for folder in (named, None if named else cwd):
        if folder and os.path.isdir(folder):
            resolution = paths.resolve_base(
                folder, machine.load_machine_state(git), git
            )
            if resolution.active and resolution.base_id and resolution.root:
                return resolution.root, resolution.base_id
    if named:
        entry = _named_base(named, runner=git)
        return entry.get("root"), entry.get("base_id")

    joined = [
        entry
        for entry in machine.load_machine_state_raw().joined
        if isinstance(entry.get("root"), str)
    ]
    if not joined:
        raise GtmBaseError("there is no base on this computer yet", NO_SUCH_BASE)
    if len(joined) > 1:
        failure = GtmBaseError("more than one base on this computer", MORE_THAN_ONE_BASE)
        failure.roots = sorted(str(entry.get("root") or "") for entry in joined)
        raise failure
    return joined[0].get("root"), joined[0].get("base_id")


def link_folder(named: str, folder: str, runner: Optional[GitRunner] = None):
    """Record that a base belongs with the folder a person works in.

    The base is found the same way every other step finds it, so a folder that
    merely looks like a base is never connected to anything.
    """
    git = runner_or_default(runner)
    root, base_id = find_base(named, runner=git)
    machine.link_content(base_id, folder, runner=git)
    return root


def unlink_folder(named: str, runner: Optional[GitRunner] = None):
    """Forget the folder a base belongs with. The base itself is untouched."""
    git = runner_or_default(runner)
    root, base_id = find_base(named, runner=git)
    machine.unlink_content(base_id)
    return root


def linked_folders(runner: Optional[GitRunner] = None):
    """Every base this account has joined, with the folder it belongs with.

    The list is taken without checking the folders, so a base on a drive that
    is unplugged today is still listed rather than looking as though it was
    never there.
    """
    state_now = machine.load_machine_state_raw()
    listed = []
    for entry in state_now.joined:
        listed.append((entry.get("root"), entry.get("content_root")))
    return listed


# --- What would be read ------------------------------------------------------


def survey_sources(run_id: str, folder: str, today=None):
    """Find the places inside a folder that look like marketing material.

    This runs before any list is shown. It looks at nothing but file names and
    first headings, and what it finds is written down in the run's own folder,
    so the places the person agrees to are the places they were proposed rather
    than whatever a second walk would find a minute later.
    """
    found = sources_module.survey(folder, today=today)
    if run_id:
        atomic_write_json(
            os.path.join(scratch_dir(run_id), SURVEY_FILE),
            {
                "root": found.root,
                "places": [
                    {
                        "folder": place.relative_folder,
                        "counts": dict(place.counts_by_kind),
                        "samples": list(place.sample_labels),
                        "score": place.score,
                        "mostly": place.mostly,
                        "candidates": [
                            {"path": relative, "kind": kind}
                            for relative, kind in place.candidates
                        ],
                    }
                    for place in found.places
                ],
                "notes": list(found.notes),
                "skipped": dict(found.skipped_counts),
                "version_sets": [list(group) for group in found.version_sets],
            },
            inside=paths.seat_home(),
        )
    return found


def load_survey(run_id: str):
    """The places this run proposed, exactly as they were proposed."""
    payload = read_json(os.path.join(scratch_dir(run_id), SURVEY_FILE))
    if not isinstance(payload, dict):
        return None
    places = payload.get("places")
    if not isinstance(places, list):
        return None
    return {
        "root": str(payload.get("root") or ""),
        "places": [
            str(item.get("folder") or "")
            for item in places
            if isinstance(item, dict) and item.get("folder")
        ],
        "notes": [str(item) for item in payload.get("notes") or []],
    }


def _added_place(root: str, name: str) -> Optional[str]:
    """The place a folder named to add is, or None when it is not one.

    Finding N4 of Astra's fourth look. The name was cut down to its last part,
    so a folder outside the one being looked through chose the folder of the
    same name inside it. It is read against the folder being looked through
    now, and it has to be that folder or one directly inside it, because the
    listing counts files by the folder at the top they sit in.
    """
    if not root:
        return None
    top = os.path.realpath(root)
    candidate = os.path.expanduser(name)
    if not os.path.isabs(candidate):
        candidate = os.path.join(top, candidate)
    real = os.path.realpath(candidate)
    if real == top:
        return "."
    if os.path.dirname(real) != top:
        return None
    return os.path.basename(real)


def chosen_places(run_id: str, added=None, dropped=None, kept=None):
    """The places to list: what was proposed, plus adds, less drops.

    A name nobody proposed and nobody added is refused rather than quietly
    listed, and so is a name dropped that was never on offer, because both of
    those are somebody naming a folder that is not the one they think it is.
    """
    return settle_places(run_id, added=added, dropped=dropped, kept=kept)[0]


def settle_places(run_id: str, added=None, dropped=None, kept=None):
    """The places to list, and which of them the person named themselves.

    Unit 1.6, requirement P25. `kept` is the proposed places the person named
    as the ones to use, and when it is given every other proposed place is
    left out. `added` is folders they named that were not proposed. Both are
    folders the person named, and a list made only of folders they named is
    an explicit choice; a plain yes to what was proposed, with or without a
    place dropped, is not, because the folders on it are still the ones GTM
    Base picked.
    """
    found = load_survey(run_id)
    if found is None:
        raise ConsentError(
            "no places have been proposed for this run yet", code=CODE_NO_SURVEY
        )
    proposed = list(found["places"])
    chosen = list(proposed)
    named: List[str] = []
    keep = [str(item).strip() for item in (kept or []) if str(item).strip()]
    if keep:
        wanted_places = []
        for name in keep:
            wanted = name.strip("/").replace(os.sep, "/").split("/")[-1] or name
            if wanted not in proposed:
                raise ConsentError(
                    "that folder is not one of the places that were proposed",
                    code=CODE_NO_SUCH_FOLDER,
                )
            if wanted not in wanted_places:
                wanted_places.append(wanted)
        chosen = [place for place in proposed if place in wanted_places]
        named.extend(chosen)
    for name in [str(item).strip() for item in (dropped or []) if str(item).strip()]:
        wanted = name.strip("/").replace(os.sep, "/").split("/")[-1] or name
        if wanted not in proposed:
            raise ConsentError(
                "that folder is not one of the places that were proposed",
                code=CODE_NO_SUCH_FOLDER,
            )
        if wanted in chosen:
            chosen.remove(wanted)
        if wanted in named:
            named.remove(wanted)
    for name in [str(item).strip() for item in (added or []) if str(item).strip()]:
        wanted = _added_place(found["root"], name)
        if wanted is None:
            raise ConsentError(
                "that folder is not one at the top of the folder being looked through",
                code=CODE_ADDED_NOT_DIRECTLY_INSIDE,
            )
        if wanted not in chosen:
            chosen.append(wanted)
        # A folder named to add that GTM Base had already proposed is still a
        # proposed folder, so adding it cannot turn a plain yes into a choice
        # that skips the narrowing question.
        if wanted not in proposed and wanted not in named:
            named.append(wanted)
    if not chosen:
        raise ConsentError(
            "no places are left to show", code=CODE_NO_FOLDERS_CHOSEN
        )
    return chosen, named


def list_sources(
    folder: str,
    run_id: Optional[str] = None,
    today=None,
    only_folders: Optional[Sequence[str]] = None,
    from_survey: bool = False,
    added: Optional[Sequence[str]] = None,
    dropped: Optional[Sequence[str]] = None,
    kept: Optional[Sequence[str]] = None,
):
    """Everything in a folder that could be read, and everything left out.

    When a run is named, the list is written down in that run's own folder
    along with one value standing for the whole of it. The person says yes to a
    list they were shown, and the yes is taken against that written down list
    rather than against whatever a second walk of the folder would find, so a
    file that appeared in the meantime cannot ride in on a yes given about a
    list it was never on.

    When the places come from the finding step, the folders it proposed, with
    the person's own adds and drops applied, are the folders listed, and both
    the proposal and the adjustments are written down with the list.

    When folders are named, the list is cut down to those folders before it is
    shown and before it is written down. The value standing for the whole of
    it still covers the whole folder, because that value is what says whether
    the folder itself has changed since the person looked at it.

    Unit 1.6: the list also records how it came to be. Folders the person
    named, at the narrowing question or as the places to use or add, make an
    explicit choice. Anything else is a plain yes to what GTM Base proposed.
    An explicit choice is not asked to be narrowed again, however many files
    it holds, and gets a plain count to confirm instead. A plain yes to a list
    too large and spread out to read through is still narrowed first, because
    a proposed list is populated with folders too, and folders on a list say
    nothing about who picked them.
    """
    whole = sources_module.list_folder(folder, today=today)
    chosen = [str(name).strip() for name in (only_folders or []) if str(name).strip()]
    named = list(chosen)
    adjustments = {"added": [], "dropped": []}
    if from_survey:
        adjustments = {
            "added": sorted(
                set(str(name).strip() for name in (added or []) if str(name).strip())
            ),
            "dropped": sorted(
                set(str(name).strip() for name in (dropped or []) if str(name).strip())
            ),
        }
        chosen, named = settle_places(
            run_id, added=added, dropped=dropped, kept=kept
        )
    listing = whole
    if chosen:
        missing = [
            name
            for name in chosen
            if name.strip("/").split("/")[-1] not in whole.by_folder
        ]
        if missing:
            raise ConsentError(
                "that folder is not one of the folders in the list",
                code=CODE_NO_SUCH_FOLDER,
            )
        listing = sources_module.narrow_to_folders(whole, chosen)
    choice = choice_of(chosen, named)
    if choice == constants.CHOICE_EXPLICIT:
        # Folders the person named are not narrowed again, however many files
        # they hold. The third real run asked a second time after four
        # folders had been named, and that is the question this takes away.
        listing.codes = [
            code for code in listing.codes if code != sources_module.CODE_NARROW_FIRST
        ]
    narrow_first = sources_module.CODE_NARROW_FIRST in listing.codes
    shown_paths = [os.path.realpath(entry.path) for entry in files_in_order(listing)]
    if run_id:
        atomic_write_json(
            os.path.join(scratch_dir(run_id), LISTING_FILE),
            {
                "root": listing.root,
                "digest": sources_module.listing_digest(whole),
                "note": sources_module.CODE_NARROW_FIRST in whole.codes,
                "narrow_first": narrow_first,
                "choice": choice,
                "named": sorted(set(_folder_name(name) for name in named)),
                "manifest": manifest_digest(listing.root, chosen, choice, shown_paths),
                "folders": sorted(set(chosen)),
                "from_survey": bool(from_survey),
                "added": list(adjustments["added"]),
                "dropped": list(adjustments["dropped"]),
                # What the base is for, beside the places dropped for it
                # (Unit 1.7a): a name, "" for the whole company, or None when
                # nobody was asked.
                "scope": held_scope(run_id),
                # The folders the counts named, in the order they were printed,
                # so the skill can name one by its number afterwards rather
                # than by a name a folder's author chose (finding F6).
                "folder_names": folders_in_order(listing),
                "paths": shown_paths,
            },
            inside=paths.seat_home(),
        )
    return listing


def _folder_name(name) -> str:
    """One folder of a list, as the last part of whatever named it."""
    text = str(name or "").strip()
    return text.strip("/").replace(os.sep, "/").split("/")[-1] or text


def choice_of(chosen, named) -> str:
    """Whether a list is an explicit choice or a plain yes to a proposal.

    It is explicit only when there is a list of folders and the person named
    every one of them. A list of the whole folder, or one holding any folder
    GTM Base proposed and the person only let stand, is a plain yes.
    """
    folders = set(_folder_name(name) for name in (chosen or []) if str(name).strip())
    if not folders:
        return constants.CHOICE_PLAIN_YES
    if folders <= set(_folder_name(name) for name in (named or [])):
        return constants.CHOICE_EXPLICIT
    return constants.CHOICE_PLAIN_YES


def manifest_digest(root, folders, choice, shown_paths) -> str:
    """One value standing for the list a yes is given to, and how it was chosen.

    The listing digest says whether the folder itself has changed. This one
    says whether the list has: which folders it covers, whether they were named
    or proposed, and exactly which files are on it, in the order they were
    shown. A yes is kept with this value, and a list whose value differs is a
    different list that needs a yes of its own (Unit 1.6).
    """
    payload = json.dumps(
        {
            "root": os.path.realpath(str(root or "")),
            "folders": sorted(set(_folder_name(name) for name in (folders or []))),
            "choice": str(choice or ""),
            "paths": list(shown_paths or []),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def files_in_order(listing) -> list:
    """The files of a listing in the one order they are shown and numbered.

    Finding R9 of Astra's third look. The listing was printed in the order the
    folder was walked and written down sorted, so the number printed beside a
    file chose a different file afterwards. This is the one order: what is
    printed, what is written down, and what a number is taken back against.
    """
    kept = []
    seen = set()
    for entry in listing.readable:
        real = os.path.realpath(entry.path)
        if real in seen:
            continue
        seen.add(real)
        kept.append(entry)
    return kept


def folders_in_order(listing) -> List[str]:
    """The folders of a listing in the one order they are shown and numbered.

    These are the folders of the list as it is shown, narrowed or not. They
    used to be written down from the whole folder while the narrowed list was
    printed, so the folder shown as number one was one that had just been
    left out (finding R9 of Astra's third look).
    """
    return sorted(listing.by_folder)


def folders_shown(run_id: str) -> List[str]:
    """The folders the last listing counted, in the order it printed them."""
    payload = read_json(os.path.join(scratch_dir(run_id), LISTING_FILE))
    if not isinstance(payload, dict):
        return []
    held = payload.get("folder_names")
    if not isinstance(held, list):
        return []
    return [str(item) for item in held if isinstance(item, str) and item]


def load_listing(run_id: str):
    """The list this run showed the person, exactly as it was shown."""
    payload = read_json(os.path.join(scratch_dir(run_id), LISTING_FILE))
    if not isinstance(payload, dict):
        return None
    wanted = payload.get("paths")
    digest = payload.get("digest")
    if not isinstance(wanted, list) or not isinstance(digest, str) or not digest:
        return None
    folders = payload.get("folders")

    def names(key):
        found = payload.get(key)
        return [str(item) for item in found] if isinstance(found, list) else []

    extra = {}
    if "scope" in payload:
        # A list written before Unit 1.7a carries no scope, and is not held
        # to one.
        extra["scope"] = _stored_scope(payload.get("scope"))
    if isinstance(payload.get("finishing"), str):
        # A list shown to draft one segment in a later session (call 29).
        extra["finishing"] = payload["finishing"]

    folders =[str(item) for item in folders] if isinstance(folders, list) else []
    note = bool(payload.get("note"))
    narrow_first = payload.get("narrow_first")
    if not isinstance(narrow_first, bool):
        # A list written before Unit 1.6 carries no answer of its own, so it
        # keeps the rule it was written under.
        narrow_first = note and not folders
    choice = payload.get("choice")
    if choice not in constants.CONSENT_CHOICES:
        choice = constants.CHOICE_PLAIN_YES
    manifest = payload.get("manifest")
    return {
        "root": str(payload.get("root") or ""),
        "digest": digest,
        "note": note,
        "narrow_first": narrow_first,
        "choice": choice,
        "named": names("named"),
        "manifest": manifest if isinstance(manifest, str) else "",
        "folders": folders,
        "from_survey": bool(payload.get("from_survey")),
        "added": names("added"),
        "dropped": names("dropped"),
        "paths": [str(item) for item in wanted],
        **extra,
    }


def freeze_sources(folder: str, session_id: str, run_id: str, today=None):
    """Take the person's yes: fix the set of files, and hold nothing back.

    The yes is taken against the list this run wrote down when it showed it. To
    make sure that list is still true, the folder is walked once more and the
    two are compared. When they differ the yes is refused with the code saying
    so, and the skill shows the new list and asks again, because a person can
    only agree to a list they have actually seen.

    A list that was too large and too spread out to be read through is refused
    as well, until the person has said which of its folders hold their
    marketing material. A yes nobody could have read is not a yes. Since Unit
    1.6 that is asked of the list as it was shown, not of the whole folder, so
    a plain yes to a proposal that is itself too large is narrowed too, and an
    explicit choice is never narrowed again.

    The yes is written down with the value standing for the list it was given
    to. If a different list is shown afterwards, that yes does not carry over
    to it: nothing is read until the new list has a yes of its own.
    """
    shown = load_listing(run_id)
    if shown is None:
        raise ConsentError(
            "no list has been shown for this run yet", code=CODE_NO_LISTING
        )
    fresh = sources_module.list_folder(folder, today=today)
    if sources_module.listing_digest(fresh) != shown["digest"]:
        raise ConsentError(
            "that folder is not what it was when the list was shown",
            code=CODE_LISTING_CHANGED,
        )
    if shown["narrow_first"]:
        raise ConsentError(
            "that list is too large to be agreed to whole",
            code=CODE_NARROW_FIRST,
        )
    # The scope kept with the yes is the one the list was shown under, and
    # it sits beside the places dropped for it (Unit 1.7a). An answer given
    # after the list was shown was not in front of the person when they
    # dropped places, so the list is shown again before a yes is taken
    # (finding 2 of the unit's correctness review).
    scope = held_scope(run_id)
    if "scope" in shown and shown["scope"] != scope:
        raise ConsentError(
            "what the base is for changed after the list was shown",
            code=CODE_SCOPE_CHANGED,
        )
    consent = sources_module.ConsentList.freeze_paths(
        shown["paths"], session_id, scope=scope or ""
    )
    atomic_write_json(
        os.path.join(scratch_dir(run_id), CONSENT_FILE),
        {
            "root": shown["root"],
            "folders": list(shown["folders"]),
            "choice": shown["choice"],
            "named": list(shown["named"]),
            "manifest": shown["manifest"],
            "from_survey": bool(shown["from_survey"]),
            "added": list(shown["added"]),
            "dropped": list(shown["dropped"]),
            "scope": scope,
            "session_id": consent.session_id,
            "frozen_at": consent.frozen_at,
            "paths": list(consent.paths),
        },
        inside=paths.seat_home(),
    )
    return consent


def _consent_payload(run_id: str):
    payload = read_json(os.path.join(scratch_dir(run_id), CONSENT_FILE))
    return payload if isinstance(payload, dict) else None


def load_consent(run_id: str):
    """The list of files this run was allowed to read, as it was frozen."""
    payload = _consent_payload(run_id)
    if payload is None:
        return None
    wanted = payload.get("paths")
    if not isinstance(wanted, list):
        return None
    return sources_module.Consent(
        [str(item) for item in wanted],
        str(payload.get("session_id") or ""),
        str(payload.get("frozen_at") or ""),
        scope=_scope_value(payload.get("scope")),
    )


def consent_choice(run_id: str) -> str:
    """Whether the yes this run holds was an explicit choice or a plain yes."""
    payload = _consent_payload(run_id)
    choice = payload.get("choice") if payload else None
    if choice in constants.CONSENT_CHOICES:
        return choice
    return constants.CHOICE_PLAIN_YES


def _refuse_a_yes_given_to_another_list(run_id: str) -> None:
    """Refuse to read when the list shown last is not the list the yes was for.

    Unit 1.6: a changed list asks again. The yes is kept with the value
    standing for the list it was given to, and the list shown last is kept
    with its own. When they differ the person has been shown a list they have
    not said yes to, and the old yes is not reused for it. A yes or a list
    written before this unit carries no value, and is read as it always was.
    """
    payload = _consent_payload(run_id)
    shown = load_listing(run_id)
    if payload is None or shown is None:
        return
    given = payload.get("manifest")
    if not isinstance(given, str) or not given or not shown["manifest"]:
        return
    if given != shown["manifest"]:
        raise ConsentError(
            "a different list has been shown since the yes",
            code=CODE_ASK_AGAIN,
        )


def consent_root(run_id: str) -> str:
    """The folder the frozen list was taken from, which paths are named against."""
    payload = _consent_payload(run_id)
    if payload is None:
        return ""
    return str(payload.get("root") or "")


# --- What the base is for (Unit 1.7a) ----------------------------------------

# Why the part of the company a base is for could not be held.
CODE_BAD_SCOPE = "bad-scope"
# The list was already agreed to, or the profile already approved, so it is
# too late in this run to say what the base is for.
CODE_SCOPE_AFTER_THE_YES = "scope-after-the-yes"
# The answer changed after the list was shown, so the list has to be shown
# again before a yes is taken over it.
CODE_SCOPE_CHANGED = "scope-changed"

# The sections of the smallest profile the profile step accepts, used to
# check a scope before it is held, each with one word under it. Nobody reads
# it; it is only ever parsed and screened.
_SCOPE_PROBE_SECTIONS = drafting.ALWAYS_SECTIONS


def _stored_scope(value):
    """A scope as a run's own file keeps it: None when nobody was asked."""
    if value is None:
        return None
    return _scope_value(value)


def _survives_the_profile(label: str) -> bool:
    """Whether a profile carrying this scope passes every check approval runs.

    Finding 1 of the unit's correctness review. The approved profile is read
    back through the words a draft may never use and through the screen for
    contact details and keys, and the scope line is part of what they read.
    A scope that fails them made the profile impossible to approve for the
    rest of the run, because the scope cannot change once the list is agreed
    to. So the same checks run on the scope before it is held.
    """
    owner = constants.OWNER_PLACEHOLDER_EMAIL
    body = "# Ideal customer profile\n" + "".join(
        "\n## %s\n\nWritten\n" % heading for heading in _SCOPE_PROBE_SECTIONS
    )
    text = formats.render_document(
        {
            "kind": drafting.KINDS[drafting.STEP_ICP],
            "owner": owner,
            "last_confirmed": "2026-01-01",
            "sources": [],
            "status": "draft",
            constants.COVERS_FIELD: label,
        },
        body,
    )
    try:
        draft = drafting.parse(
            drafting.STEP_ICP, "```markdown\n" + text.rstrip("\n") + "\n```\n"
        )
    except (DraftError, ValidationError, PathError):
        return False
    return not review.screen(draft, owner)


def _scope_value(value) -> str:
    """A scope read back from a run's own file, or nothing when it is not one."""
    if not value:
        return ""
    try:
        return validate.validate_covers(value)
    except ValidationError:
        return ""


def places_that_split(run_id: str) -> List[str]:
    """The places that each keep their own copy of the same positioning document.

    Material plainly covers more than one part of the company when two or more
    places each hold a customer profile and a positioning document of the same
    name, such as a `positioning.md` in a folder for each product line: the
    same document written once per part. That is one of the two times the
    scope question is asked; the other is the person saying so. A folder of
    positioning and a folder holding a sales pitch are not that, because a
    pitch and a positioning are two documents about one thing, so the rule
    looks for the same name and not merely the same kind. It is worked out
    from the file names and first headings the finding step already
    recorded, so it reads nothing the finding step did not.
    """
    payload = read_json(os.path.join(scratch_dir(run_id), SURVEY_FILE))
    if not isinstance(payload, dict) or not isinstance(payload.get("places"), list):
        return []
    places_by_stem = {}
    for item in payload["places"]:
        if not isinstance(item, dict):
            continue
        folder = str(item.get("folder") or "")
        candidates = item.get("candidates")
        if not folder or not isinstance(candidates, list):
            continue
        kinds = set()
        stems = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            kind = candidate.get("kind")
            kinds.add(kind)
            if kind == "positioning":
                stems.add(sources_module.version_stem(str(candidate.get("path") or "")))
        if "customer-profile" not in kinds:
            continue
        for stem in stems:
            places_by_stem.setdefault(stem, [])
            if folder not in places_by_stem[stem]:
                places_by_stem[stem].append(folder)
    found: List[str] = []
    for stem in sorted(places_by_stem):
        folders = places_by_stem[stem]
        if len(folders) > 1:
            found.extend(folder for folder in folders if folder not in found)
    return found


def scope_question_needed(run_id: str, raised: bool = False) -> bool:
    """Whether to ask what part of the company the base is for.

    Requirement P23: asked once, when the person says the base is for one
    part of the company or the material plainly splits, and never otherwise.
    """
    return bool(raised) or bool(places_that_split(run_id))


def hold_scope(run_id: str, covers: Optional[str] = None, whole: bool = False) -> str:
    """Hold the answer in the run's own folder until the profile can carry it.

    `covers` is the name of the part of the company the base is for, checked
    as a short name. `whole` is the answer that it is for the whole company,
    which is held too, so the question is not asked again in this run. An
    answer given after the list was agreed to is refused, because the places
    on that list were settled without it.
    """
    if _consent_payload(run_id) is not None or _scope_payload(run_id).get("fixed"):
        raise ValidationError(
            "the list was already agreed to", code=CODE_SCOPE_AFTER_THE_YES
        )
    if whole:
        label = ""
    else:
        try:
            label = validate.validate_covers(covers)
        except ValidationError as refusal:
            raise ValidationError(str(refusal), code=CODE_BAD_SCOPE)
        if not _survives_the_profile(label):
            raise ValidationError(
                "the scope would not pass the checks the profile meets",
                code=CODE_BAD_SCOPE,
            )
    atomic_write_json(
        os.path.join(scratch_dir(run_id), SCOPE_FILE),
        {"whole": not label, "covers": label},
        inside=paths.seat_home(),
    )
    return label


def held_scope(run_id: str) -> Optional[str]:
    """What the base covers: a name, "" for the whole company, None if not asked.

    Once the list is agreed to, the scope kept with that yes is the answer,
    because it is the one the places were settled under.
    """
    payload = _consent_payload(run_id)
    if payload is not None and "scope" in payload:
        return _stored_scope(payload.get("scope"))
    held = _scope_payload(run_id)
    if held.get("whole") is True:
        return ""
    return _scope_value(held.get("covers")) or None


def _scope_payload(run_id: str) -> dict:
    held = read_json(os.path.join(scratch_dir(run_id), SCOPE_FILE))
    return held if isinstance(held, dict) else {}


def fix_the_scope(run_id: str) -> None:
    """Keep the scope as it is from the moment the profile is approved.

    A run that read only pasted text has no agreed list to fix the scope
    with, so without this the scope could change after the profile already
    carried it, and the base and the run would disagree (finding 4 of the
    unit's correctness review).
    """
    held = held_scope(run_id)
    atomic_write_json(
        os.path.join(scratch_dir(run_id), SCOPE_FILE),
        {"whole": held == "", "covers": held or "", "fixed": True},
        inside=paths.seat_home(),
    )


def with_scope(draft, covers: Optional[str]):
    """The profile with the scope GTM Base holds on it, and no other.

    Whatever the draft said about what it covers is taken off first, and the
    held answer is written in its place, so the value in the base is always
    the one the person gave. A base for the whole company carries none.
    """
    block, body = formats.split_document(draft.text)
    fields = formats.parse_frontmatter(block)
    fields.pop(constants.COVERS_FIELD, None)
    if covers:
        fields[constants.COVERS_FIELD] = validate.validate_covers(covers)
    text = formats.render_document(fields, body)
    return drafting.parse(draft.step, "```markdown\n" + text.rstrip("\n") + "\n```\n")


# --- Which segments the base will hold (Unit 1.7a) ---------------------------

# There is no agreed list of files yet, so there is nothing to find segments in.
CODE_NO_CONSENT = "no-consent"


def segment_candidates(run_id: str, today=None) -> List[segments.Candidate]:
    """The documents on the agreed list that each look like one segment.

    Only files the person agreed to are looked at, and each one only through
    the check every read goes through. A document counts when its name or its
    first heading says it is a customer profile, and it is not a template or a
    read-me. Versions of one document, grouped by name the way the drafts
    group them, count once, as the version a draft would read. The numbered
    list is kept in the run's own folder, so a number the person names later
    means the document shown beside it.
    """
    consent = load_consent(run_id)
    if consent is None:
        if _holds_pastes(run_id):
            # A run that read only pasted text has no documents to number,
            # and every segment it names is named with no document (finding 4
            # of the unit's correctness review).
            segments.save_candidates(scratch_dir(run_id), [], paths.seat_home())
            return []
        raise ConsentError("no list has been agreed to yet", code=CODE_NO_CONSENT)
    root = consent_root(run_id)
    day = today or state.today()

    class _Found(object):
        __slots__ = ("path",)

        def __init__(self, path):
            self.path = path

    found = []
    for path in consent.paths:
        try:
            real = sources_module.read_allowed(consent, path)
        except ConsentError:
            continue
        if not os.path.isfile(real):
            continue
        name = os.path.basename(real)
        heading = "" if name.casefold().endswith(".csv") else sources_module.first_heading(real)
        if sources_module.kind_of(name, heading) != "customer-profile":
            continue
        words = ("%s %s" % (name, heading)).casefold()
        stem = os.path.splitext(name)[0].casefold()
        if any(word in words for word in constants.DRAFT_LAST_WORDS) or (
            stem in constants.DRAFT_LAST_NAMES
        ):
            continue
        found.append(_Found(real))
    groups = sources_module.version_groups(
        found, lambda item: sources_module.date_for_file(item.path, today=day).date
    )
    candidates = []
    for number, group in enumerate(groups, start=1):
        path = group[0].path
        try:
            label = os.path.relpath(path, root) if root else os.path.basename(path)
        except ValueError:
            label = os.path.basename(path)
        candidates.append(
            segments.Candidate(number, path, label.replace(os.sep, "/"))
        )
    # A number means the document shown beside it. With fewer than two, no
    # numbered list is shown, so none is kept either, and a segment is then
    # named with no document (finding 6 of the unit's correctness review).
    segments.save_candidates(
        scratch_dir(run_id),
        candidates if len(candidates) > 1 else [],
        paths.seat_home(),
    )
    return candidates


def _holds_pastes(run_id: str) -> bool:
    folder = os.path.join(scratch_dir(run_id), PASTES_DIR)
    try:
        return any(name.endswith(".txt") for name in os.listdir(folder))
    except OSError:
        return False


def settle_segments(run_id: str, text: str) -> segments.Inventory:
    """Read the person's answers and keep the inventory, or refuse all of it.

    The numbers are taken against the documents this run last showed, never
    against a fresh look, so a number means the document the person saw
    beside it. Nothing is kept unless every segment passes.
    """
    # A run that read only pasted text has no documents to number, and every
    # segment it names is named with no document.
    shown = segments.load_candidates(scratch_dir(run_id)) or []
    inventory = segments.settle(segments.read_lines(text), shown)
    segments.save(scratch_dir(run_id), inventory, paths.seat_home())
    return inventory


def load_inventory(run_id: str) -> Optional[segments.Inventory]:
    """The inventory this run settled, exactly as it was kept, or None."""
    return segments.load(scratch_dir(run_id))


# --- The umbrella and the segment drafts (Unit 1.7b) ------------------------

# The profile step asked for when the inventory holds several segments, which
# is the umbrella's place, and the umbrella asked for when it does not.
CODE_UMBRELLA_INSTEAD = "umbrella-instead"
CODE_NO_SEVERAL_SEGMENTS = "no-several-segments"
# A segment's draft handed in under another segment's name.
CODE_NOT_THIS_SEGMENTS_DRAFT = "not-this-segments-draft"
# A step that needs the run, asked for without it.
CODE_NO_RUN = "no-run"
# A draft carrying questions for the person may only be written once they have
# chosen to leave those questions open.
CODE_QUESTIONS_OPEN = "questions-open"
# Said when a draft carries questions only the person can answer. It is said
# after the check says the draft is ready, and before it is shown.
DRAFT_HAS_ONE_QUESTION = (
    "This draft leaves one question for you to answer, marked where it comes "
    "up. Answer it now and it is written in before anything is saved, or "
    "approve the draft with it left open and your next review of your base "
    "asks it again."
)
DRAFT_HAS_QUESTIONS = (
    "This draft leaves %d questions for you to answer, each marked where it "
    "comes up. Answer them now and they are written in before anything is "
    "saved, or approve the draft with them left open and your next review of "
    "your base asks them again."
)


def draft_questions_sentence(count: int) -> str:
    """The sentence said about a draft's open questions, or nothing at all."""
    if count <= 0:
        return ""
    if count == 1:
        return DRAFT_HAS_ONE_QUESTION
    return DRAFT_HAS_QUESTIONS % count


def several_segments(run_id: str) -> Optional[segments.Inventory]:
    """The inventory, when it holds more than one segment, and None otherwise.

    One segment, or no inventory at all, is a company the customer profile
    describes in full, and `draft-icp.md` stays its prompt.
    """
    inventory = load_inventory(run_id)
    if inventory is None or inventory.is_single:
        return None
    return inventory


def profile_step(run_id: str) -> str:
    """Which step drafts the customer profile in this run."""
    return drafting.STEP_UMBRELLA if several_segments(run_id) else drafting.STEP_ICP


def segment_to_draft(run_id: str, slug: Optional[str]) -> segments.Segment:
    """The one settled segment a segment draft is for, or a refusal.

    It has to be a segment the person said to draft, in an inventory of more
    than one. A segment taken from its finished document is the next part's,
    and one left out is drafted by nobody.
    """
    inventory = several_segments(run_id)
    if inventory is not None and slug:
        for segment in inventory.segments:
            if segment.slug != slug:
                continue
            if segment.answer == constants.SEGMENT_DRAFT:
                return segment
            # A finished page the adoption contract refused may be drafted
            # instead, which is the offer every such refusal makes (Unit 1.7c).
            if segment.answer == constants.SEGMENT_ADOPT and adopt.was_refused(
                scratch_dir(run_id), slug
            ):
                return segment
    raise ReviewError(segments.CODE_NOT_TO_DRAFT, code=segments.CODE_NOT_TO_DRAFT)


def _step_is_this_runs(run_id: str, step: str, segment: Optional[str] = None):
    """Refuse a profile step the inventory rules out, and return the segment.

    Several segments are drafted as an umbrella and never folded into one
    profile, which is the defect the third real run found, so the profile
    step is refused once the inventory holds several, and the umbrella step
    is refused until it does.
    """
    if step == drafting.STEP_ICP and several_segments(run_id) is not None:
        raise ReviewError(CODE_UMBRELLA_INSTEAD, code=CODE_UMBRELLA_INSTEAD)
    if step == drafting.STEP_UMBRELLA and several_segments(run_id) is None:
        raise ReviewError(CODE_NO_SEVERAL_SEGMENTS, code=CODE_NO_SEVERAL_SEGMENTS)
    if step == drafting.STEP_SEGMENT:
        settled = segment_to_draft(run_id, segment)
        if _finishing(run_id) is not None:
            # A run a later session made to draft one segment holds no yes
            # until the person gives one to the list it shows, and a segment
            # is never drafted from nothing (call 29).
            consent = load_consent(run_id)
            if consent is None or not consent.paths:
                raise ReviewError(CODE_DRAFT_NOT_AGREED, code=CODE_DRAFT_NOT_AGREED)
        return settled
    return None


def _what_the_base_is_for(run_id: str) -> str:
    held = held_scope(run_id)
    return held if held else "the whole company"


def _inventory_lines(inventory: segments.Inventory) -> str:
    """The settled segments as plain lines, for the request to hold as data."""
    said = {
        constants.SEGMENT_ADOPT: "taken from its finished document",
        constants.SEGMENT_DRAFT: "drafted from the material",
        constants.SEGMENT_LEAVE_OUT: "left out for now",
    }
    return "\n".join(
        "- %s (%s)" % (segment.name, said[segment.answer])
        for segment in inventory.segments
    )


def _extra_for(run_id: str, step: str, segment) -> dict:
    """What the umbrella and a segment request carry besides the material.

    Every value is the person's own words, so each is held apart as data the
    same way their documents are.
    """
    if step not in (drafting.STEP_UMBRELLA, drafting.STEP_SEGMENT):
        return {}
    inventory = several_segments(run_id)
    try:
        extra = {
            "scope": drafting.said_as_data(
                "what the base is for", _what_the_base_is_for(run_id)
            ),
            "inventory": drafting.said_as_data(
                "the segments", _inventory_lines(inventory)
            ),
        }
        if segment is not None:
            extra["segment"] = drafting.said_as_data("the segment", segment.name)
    except SourceRejected:
        raise DraftError(step, "unusable-name")
    return extra


# --- Taking a finished page into the base (Unit 1.7c) --------------------------


def segment_to_adopt(run_id: str, slug: Optional[str]) -> segments.Segment:
    """The one settled segment to take from its finished page, or a refusal.

    It has to be a segment the person said to take from a finished document,
    named with that document's number, in an inventory of more than one. A
    company with one segment keeps only the profile, at full depth.
    """
    inventory = several_segments(run_id) if _finishing(run_id) is None else None
    if inventory is not None and slug:
        for segment in inventory.segments:
            if (
                segment.slug == slug
                and segment.answer == constants.SEGMENT_ADOPT
                and segment.number is not None
                and segment.source
            ):
                return segment
    raise adopt.AdoptionRefused(adopt.CODE_NOT_TO_ADOPT)


def adoption_file(run_id: str, slug: str) -> str:
    """Where the whole cleaned page is kept for the person to read before a yes.

    It sits beside the run's drafts, in the folder that is this person's
    alone, and is worked out here from the run and the segment's file name,
    both checked, and never chosen by the assistant.
    """
    if segments.slug_problem(slug) is not None:
        raise adopt.AdoptionRefused(adopt.CODE_NOT_TO_ADOPT)
    return os.path.join(drafts_dir(run_id), "adopt-%s.md" % slug)


def _adoption_base(base_root: Optional[str], git: GitRunner):
    """The base a page is taken into, once both required documents are in it.

    Adoption runs after the umbrella and the positioning, because the
    umbrella is what creates the base and names every segment first.
    """
    if not base_root:
        raise adopt.AdoptionRefused(adopt.CODE_BASE_NOT_READY)
    resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
    if not resolution.active or not resolution.root or not resolution.base_id:
        raise adopt.AdoptionRefused(adopt.CODE_BASE_NOT_READY)
    # Each required document has been answered: written, or, for the
    # positioning, written down as skipped. Both steps come before this one.
    by_path = dict((info.path, info) for info in base_reader.context_files(resolution.root))
    for required in constants.REQUIRED_CONTEXT_FILES:
        held = [
            by_path.get(candidate)
            for candidate in (required, layout.older_of(required))
            if candidate
        ]
        if not any(info is not None and info.exists for info in held):
            raise adopt.AdoptionRefused(adopt.CODE_BASE_NOT_READY)
    return resolution.root, resolution.base_id


def _dropped_places(run_id: str) -> List[str]:
    payload = _consent_payload(run_id) or {}
    held = payload.get("dropped")
    return [str(item) for item in held] if isinstance(held, list) else []


def _owner_address(root, email, git) -> str:
    address = _address_for(root, email, git)
    if not address or not validate.is_valid_email(address):
        raise ReviewError(review.CODE_OWNER_MISSING, code=review.CODE_OWNER_MISSING)
    return address


def _original_digest(run_id, segment) -> Optional[str]:
    """The hash of a page's original file as it is now, or None when unreadable.

    It is kept beside the yes, so a later run can tell an original that
    changed from one that GTM Base now cleans differently.
    """
    try:
        real = sources_module.read_allowed(load_consent(run_id), segment.source)
    except ConsentError:
        return None
    held = read_bytes(real)
    return hashlib.sha256(held).hexdigest() if held is not None else None


def _cleaned_page(run_id, segment, root, address, day, check_destination=True):
    """Run the whole contract on one settled segment's page, in its order.

    Clause one, the destination, comes first. The page is then read through
    the same check every read in setup goes through, so a page no longer on
    the agreed list is never opened, and one bounded read is made of it. A
    resume checking a page this import already wrote at its name leaves the
    destination out, because that page is what stands there.
    """
    problem = adopt.destination_problem(root, segment.slug) if check_destination else None
    if problem == adopt.CODE_RESERVED_NAME:
        raise adopt.AdoptionRefused(
            problem, segments.RESERVED_NAME % {"name": segment.name}
        )
    if problem is not None:
        raise adopt.AdoptionRefused(problem)
    consent = load_consent(run_id)
    try:
        real = sources_module.read_allowed(consent, segment.source)
    except ConsentError:
        raise adopt.AdoptionRefused(adopt.CODE_UNREADABLE)
    if not adopt.is_markdown(real):
        raise adopt.AdoptionRefused(adopt.CODE_NOT_MARKDOWN)
    try:
        raw, notes = extract.extract(real, "markdown")
    except SourceRejected:
        raise adopt.AdoptionRefused(adopt.CODE_UNREADABLE)
    if extract.NOTE_CHARACTERS_REPLACED in notes:
        # Some bytes were not the text the file said it was, and saving the
        # stand-ins would not be the page as it stands (correctness review C7).
        raise adopt.AdoptionRefused(adopt.CODE_UNREADABLE)
    when = sources_module.date_for_file(real, today=day).date
    return adopt.clean(
        raw,
        _label_for(real),
        day,
        address,
        adopt.source_line_for(segment.label, when),
        covers=held_scope(run_id),
        dropped=_dropped_places(run_id),
    )


class Shown(object):
    """One page as the person is shown it: what went, the first lines, where."""

    __slots__ = ("segment", "cleaned", "path")

    def __init__(self, segment, cleaned, path):
        self.segment = segment
        self.cleaned = cleaned
        self.path = path

    @property
    def digest(self) -> str:
        return self.cleaned.digest

    def sentences(self) -> List[str]:
        """What is said about the page, in order, ending in the one ask."""
        said = [adopt.SHOW_OPENING % {"name": self.segment.name}]
        if self.cleaned.settings_set_aside:
            said.append(adopt.SETTINGS_SET_ASIDE)
        # Named by the segment the person named, never by the file's own name,
        # which is not text the fence holds (Astra, finding 7 of the merged units).
        hidden = sources_module.removed_sentence(self.segment.name, self.cleaned.removed)
        if hidden:
            said.append(hidden)
        if not self.cleaned.settings_set_aside and not hidden:
            said.append(adopt.NOTHING_TAKEN_OUT)
        said.append(adopt.OPENING_SAID)
        said.append(adopt.WHOLE_FILE)
        if self.cleaned.questions == 1:
            said.append(adopt.ONE_QUESTION)
        elif self.cleaned.questions > 1:
            said.append(adopt.QUESTIONS % self.cleaned.questions)
        said.append(adopt.ASK_WITH_QUESTIONS if self.cleaned.questions else adopt.ASK)
        return said

    def __repr__(self) -> str:
        return "Shown(%r)" % (self.segment.slug,)


def adoption_show(
    run_id: str,
    slug: Optional[str],
    base_root: Optional[str],
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    today=None,
) -> Shown:
    """Run the contract on one page and keep the result for the person to read.

    Nothing is written into the base. The whole cleaned page is written into
    the run's own folder, and the hash of exactly those bytes is kept beside
    the day it was shown, which is what a later yes is bound to. A page the
    contract refuses is remembered as refused, so it can be drafted instead.
    """
    segment = segment_to_adopt(run_id, slug)
    git = runner_or_default(runner)
    root, base_id = _adoption_base(base_root, git)
    day = today or state.today()
    address = _owner_address(root, email, git)
    path = adoption_file(run_id, segment.slug)
    # What the import needs past the closing is kept from the first page
    # shown, because a session can end at any moment after it (Unit 1.7d).
    record = _carry(run_id, base_id)
    yes = record.approved(segment.slug) if record is not None else None
    if yes is not None and review.page_state(
        git, root, segment.destination, yes["approved"], run=record.run
    ) in review.PAGES_TO_FINISH:
        # The person already said yes and the page is at its name, so it is
        # finished rather than shown again or refused as a name in the way
        # (the correctness review of Unit 1.7d, finding 4). Finishing cleans
        # it again under today's rules first; a page that no longer comes out
        # to what the yes was to is taken back and shown here afresh (Astra's
        # review of the merged units, finding 3).
        try:
            _finish_one(run_id, root, base_id, segment, record, None, git, None, address)
            raise adopt.AdoptionRefused(CODE_ALREADY_SAVED, ALREADY_SAVED)
        except adopt.AdoptionRefused as refusal:
            if refusal.code not in (CODE_CLEANED_AGAIN, adopt.CODE_CHANGED):
                raise
        record = _carry(run_id, base_id)
    try:
        cleaned = _cleaned_page(run_id, segment, root, address, day)
    except adopt.AdoptionRefused as refusal:
        # A cleaned page from an earlier showing is not left to be read as
        # though it were this one.
        if os.path.lexists(path):
            os.remove(path)
        if refusal.code in adopt.OFFERS_A_DRAFT:
            adopt.record_refused(
                scratch_dir(run_id), segment.slug, refusal.code, paths.seat_home()
            )
            _mark_refused(record, segment.slug)
        raise
    atomic_write_text(path, cleaned.text, inside=drafts_dir(run_id))
    adopt.record_shown(
        scratch_dir(run_id),
        segment.slug,
        cleaned.digest,
        day.isoformat() if hasattr(day, "isoformat") else str(day),
        paths.seat_home(),
    )
    return Shown(segment, cleaned, path)


def adoption_read(run_id: str, slug: Optional[str]) -> str:
    """The whole cleaned page, for the assistant to show, if it is the one shown.

    The assistant reads the page through this and never by opening the file,
    so the page reaches it inside the data fence like every other context
    document, and a cleaned file somebody changed after the showing is not
    read out at all (the unit's security review, S2).
    """
    segment = segment_to_adopt(run_id, slug)
    record = adopt.shown(scratch_dir(run_id), segment.slug)
    if record is None:
        raise adopt.AdoptionRefused(adopt.CODE_NOT_SHOWN)
    held = read_bytes(adoption_file(run_id, segment.slug))
    if held is None or hashlib.sha256(held).hexdigest() != record["shown"]:
        raise adopt.AdoptionRefused(adopt.CODE_CHANGED)
    return held.decode("utf-8")


def adoption_approve(
    run_id: str,
    slug: Optional[str],
    base_root: Optional[str],
    shown_digest: str,
    questions_open: bool = False,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
):
    """Write one page the person said yes to, exactly as they were shown it.

    The yes is bound to the hash kept when the page was shown. The contract is
    run again from the original, on the day it was shown, and the cleaned file
    the person could read is read again, and both have to come out to that
    same hash, so a page or a cleaned file that changed after the showing is
    asked about again rather than written. A yes covering several pages
    counts only for the pages that were each shown this way.

    The yes is written down before anything touches the base, and the save
    after it lands (Unit 1.7d), so an import that stops anywhere in between
    is finished by the next attempt, or the next session, without asking
    again. A page this same page's earlier attempt left written and not saved
    is finished rather than refused.
    """
    segment = segment_to_adopt(run_id, slug)
    git = runner_or_default(runner)
    root, base_id = _adoption_base(base_root, git)
    record = adopt.shown(scratch_dir(run_id), segment.slug)
    if record is None:
        raise adopt.AdoptionRefused(adopt.CODE_NOT_SHOWN)
    given = str(shown_digest or "")
    if not adopt.is_a_digest(given) or not hmac.compare_digest(given, record["shown"]):
        # Anything but the hash that was shown, including something that is
        # not a hash at all, asks again (correctness review C6).
        raise adopt.AdoptionRefused(adopt.CODE_CHANGED)
    try:
        day = datetime.date.fromisoformat(record["day"])
    except (TypeError, ValueError):
        raise adopt.AdoptionRefused(adopt.CODE_NOT_SHOWN)
    address = _owner_address(root, email, git)
    kept = _carry(run_id, base_id)
    if kept is None:
        raise adopt.AdoptionRefused(adopt.CODE_NOT_TO_ADOPT)
    try:
        cleaned = _cleaned_page(run_id, segment, root, address, day)
    except adopt.AdoptionRefused as refusal:
        if refusal.code == adopt.CODE_FILE_TAKEN:
            # This page's own earlier attempt may be what stands at its
            # name, written or saved. That is finished, never refused.
            cleaned = None
        else:
            if refusal.code in adopt.OFFERS_A_DRAFT:
                adopt.record_refused(
                    scratch_dir(run_id), segment.slug, refusal.code, paths.seat_home()
                )
                _mark_refused(kept, segment.slug)
            raise
    if cleaned is None:
        yes = kept.approved(segment.slug)
        if yes is None or yes["approved"] != record["shown"]:
            raise adopt.AdoptionRefused(adopt.CODE_FILE_TAKEN)
        return _finish_one(run_id, root, base_id, segment, kept, None, git, now, address)
    on_disk = read_bytes(adoption_file(run_id, segment.slug))
    if (
        cleaned.digest != record["shown"]
        or on_disk is None
        or hashlib.sha256(on_disk).hexdigest() != record["shown"]
    ):
        raise adopt.AdoptionRefused(adopt.CODE_CHANGED)
    if cleaned.questions and not questions_open:
        raise adopt.AdoptionRefused(adopt.CODE_QUESTIONS_OPEN)
    kept = segments.mark(
        base_id, segment.slug, segments.STATE_APPROVED, record["shown"], record["day"],
        run=kept.run, original=_original_digest(run_id, segment),
    )
    return _finish_one(run_id, root, base_id, segment, kept, cleaned.text, git, now, address)


# --- An import kept past the closing, and finished later (Unit 1.7d) ---------

# Why an import could not be finished or noted, beside the refusals above.
CODE_IMPORT_UNREADABLE = "import-record-unreadable"
CODE_RUN_HAS_ITS_OWN = "run-has-its-own-segments"
CODE_ANOTHER_IMPORT = segments.CODE_ANOTHER_IMPORT
CODE_ALREADY_SAVED = "already-saved"
CODE_PAGE_EDITED = review.PAGE_EDITED
CODE_LOCKED = "locked"
# A page with a yes that today's cleaning no longer turns into those bytes.
CODE_CLEANED_AGAIN = "cleaned-again-differently"
# The name of the lock held, per base, while one page is written and saved,
# so two windows never write into one base's staging at once.
WRITING_LOCK = "segments-import-writing"

# Said after a person says to leave a finished page out.
LEFT_OUT_SAID = "That document is left out, and nothing was saved."
# Said when nothing is kept about an import for this base.
RESUME_NOTHING = (
    "Nothing is left to finish from taking your finished documents into your "
    "base."
)
RESUME_UNREADABLE = (
    "GTM Base could not read what it kept about taking your finished "
    "documents in, so it set that aside, and nothing was saved."
)
RESUME_RUN_HAS_ITS_OWN = (
    "This setup run already settled its own segments, so nothing was "
    "finished. Start a new run and ask again."
)
RESUME_FINISHED_ONE = (
    "One finished document you had already said yes to is now saved into "
    "your base."
)
RESUME_FINISHED = (
    "%d finished documents you had already said yes to are now saved into "
    "your base."
)
RESUME_CHANGED = (
    "%(name)s changed after you said yes to it, so it will be shown to you "
    "again before anything is saved."
)
RESUME_TAKEN = (
    "%(name)s was not saved, because your base already holds a different "
    "document where it would go, and that document was left exactly as it is."
)
RESUME_EDITED = (
    "%(name)s was changed before it could be saved, so what GTM Base had "
    "started for it was taken back, and your changed copy was left exactly "
    "as it is."
)
RESUME_RECHECKED = (
    "%(name)s will be shown to you again before anything is saved, because "
    "GTM Base now checks finished documents more closely than when you said "
    "yes to it, and would not save exactly what you saw."
)
RESUME_CANNOT_READ = (
    "%(name)s could not be read just now, so it was left for next time, and "
    "your yes to it still stands."
)
RESUME_STOPPED = (
    "Finishing stopped at %(name)s, and everything before it is saved. Ask "
    "again to carry on."
)
RESUME_TO_SHOW_ONE = (
    "One finished document still waits for your answer, and it is shown to "
    "you before anything is saved."
)
RESUME_TO_SHOW = (
    "%d finished documents still wait for your answer, and each is shown to "
    "you before anything is saved."
)
RESUME_DONE = (
    "Every finished document you chose is now settled, and nothing is left "
    "to finish."
)
# Said at the closing when some chosen pages are not in the base yet.
CLOSING_IMPORT_UNFINISHED = (
    "Some of the finished documents you chose are not in your base yet, and "
    "the next session will offer to finish taking them in."
)
# Said when a save may or may not have landed, so nothing was taken back.
SAVE_UNCERTAIN = (
    "GTM Base could not tell whether that document was saved, so nothing was "
    "taken back. Ask again and it will finish saving it or say what it found."
)
# Said when something was put where a page was being written, before the save.
PAGE_REPLACED = (
    "Something else was put where that document was being saved, so nothing "
    "was saved, and what was put there was left as it is."
)
# Said when a page this import wrote was changed before its save.
PAGE_EDITED_SAID = (
    "That document was changed before it could be saved, so what GTM Base "
    "had started for it was taken back, and your changed copy was left "
    "exactly as it is."
)
# Said when a page with a yes turns out to be saved already.
ALREADY_SAVED = (
    "You already said yes to that document, and it is saved into your base, "
    "so nothing more is asked about it."
)
# Said when an earlier import of this base still waits on a page.
IMPORT_PENDING = (
    "Taking in the finished documents from an earlier setup of this base is "
    "not finished yet, so nothing was saved. Say \"finish setting up my "
    "base\" first."
)
# Said when a page is asked about again and today's cleaning no longer turns
# its original into the bytes the person said yes to.
CLEANED_AGAIN_SAID = (
    "GTM Base now checks finished documents more closely than when you said "
    "yes to that one, so nothing was saved. Show it again, then ask again."
)
# Said when somebody else's file was found where one of the person's
# documents was being put, and could not go back under its own name because
# that name had been taken again.
KEPT_ASIDE = (
    "Another file was found where one of your documents was being saved, and "
    "its name had been taken again, so it was kept beside it under the same "
    "name with the words kept aside added. Nothing of it was lost. Look at "
    "it, then ask again."
)
# Said when a write could not make sure no other window was writing to the
# same place, or the folder that makes sure of it is not this account's
# alone, so nothing was written.
NO_LOCK = (
    "GTM Base could not make sure no other window was writing to the same "
    "place, so nothing was written. Ask again in a moment."
)
LOCKS_NOT_PRIVATE = (
    "The folder GTM Base keeps its own records in can be changed by somebody "
    "other than you, so nothing was written. Ask whoever looks after this "
    "computer to make it yours alone, then ask again."
)
# Said when another window holds the base for a moment.
LOCKED = (
    "Another window is saving into your base right now, so nothing more was "
    "done. Ask again in a moment."
)
# Said when saving did not finish and nothing of it was kept.
WRITE_FAILED = (
    "Saving that document did not finish, and nothing of it was kept. Ask "
    "again and it will try once more."
)

# The one sentence said for each refusal the base itself can give while a
# page is written or finished. The script and the resume both read it.
BASE_REFUSALS = {
    review.CODE_UNSAVED_EDITS: adopt.UNSAVED_EDITS,
    review.CODE_NOT_DEFAULT_BRANCH: adopt.NOT_ON_THE_MAIN_LINE,
    segments.CODE_FILE_TAKEN: segments.FILE_TAKEN,
    review.CODE_FILE_EXISTS: segments.FILE_TAKEN,
    segments.CODE_FOLDER_NOT_ORDINARY: segments.FOLDER_NOT_ORDINARY,
    review.CODE_SAVE_UNCERTAIN: SAVE_UNCERTAIN,
    review.CODE_PAGE_REPLACED: PAGE_REPLACED,
    review.CODE_GIT_FAILED: WRITE_FAILED,
    CODE_PAGE_EDITED: PAGE_EDITED_SAID,
    CODE_LOCKED: LOCKED,
    CODE_CLEANED_AGAIN: CLEANED_AGAIN_SAID,
    review.CODE_KEPT_ASIDE: KEPT_ASIDE,
    fsutil.CODE_NO_LOCK: NO_LOCK,
    fsutil.CODE_LOCKS_NOT_PRIVATE: LOCKS_NOT_PRIVATE,
}


def _carry(run_id: str, base_id: Optional[str]):
    """The record kept for this base's import, made from this run when needed.

    Returns None when this run takes no finished page in. An earlier import
    of this base that still waits on a page is refused with the sentence that
    says so, because this run's pages cannot be kept beside it.
    """
    if not base_id:
        return None
    inventory = several_segments(run_id)
    if inventory is None:
        return None
    finishing = _finishing(run_id)
    if finishing is not None:
        # A run a later session made to draft one segment was given the
        # inventory from the record, and never makes a record of its own
        # (call 29): the one it finishes is the only one it may use.
        held = segments.load_import(base_id)
        if (
            held is None
            or finishing["base_id"] != base_id
            or held.run != finishing["run"]
            or held.inventory != inventory
        ):
            return None
        return held
    try:
        record = segments.carry_import(
            base_id,
            run_id,
            inventory,
            segments.load_candidates(scratch_dir(run_id)) or [],
            _consent_payload(run_id) or {},
        )
    except segments.InventoryRefused as refusal:
        if refusal.code == CODE_ANOTHER_IMPORT:
            raise adopt.AdoptionRefused(CODE_ANOTHER_IMPORT, IMPORT_PENDING)
        raise
    if record is None or record.inventory != inventory:
        return None
    return record


def _mark_refused(record, slug: str) -> None:
    """Keep that the contract refused a page. A saved page stays saved."""
    if record is None:
        return
    segments.mark(record.base_id, slug, segments.STATE_REFUSED, run=record.run)


# How many times this thread holds each base's writing lock, so a call that
# already holds it, such as a resume finishing one of its pages, never waits
# on itself, while another thread still waits like any other window.
_WRITING_HELD = threading.local()


def _held_counts() -> dict:
    counts = getattr(_WRITING_HELD, "counts", None)
    if counts is None:
        counts = _WRITING_HELD.counts = {}
    return counts


class _Writing(object):
    """This base's writing lock, held across every step that changes it.

    Every write, every take-back, and every record update that ends them is
    made with it held, and the state of the page is read again once it is
    held, so no other window can come between the look and the change
    (Astra's review of the merged units, finding 1). Waiting too long gives up
    with the sentence that says another window is saving.
    """

    def __init__(self, base_id: str):
        self.path = os.path.join(paths.seat_dir(base_id), WRITING_LOCK)
        self.lock = None

    def __enter__(self):
        held = _held_counts().get(self.path, 0)
        if held == 0:
            lock = HeldLock(self.path)
            try:
                lock.__enter__()
            except PathError:
                raise ReviewError(CODE_LOCKED, code=CODE_LOCKED)
            self.lock = lock
        _held_counts()[self.path] = held + 1
        return self

    def __exit__(self, *_exc):
        counts = _held_counts()
        left = counts.get(self.path, 1) - 1
        if left <= 0:
            counts.pop(self.path, None)
            if self.lock is not None:
                self.lock.__exit__(None, None, None)
        else:
            counts[self.path] = left
        return False


def _revalidate(run_id, segment, root, address, yes, written):
    """Clean the original again under today's rules and say whether the yes stands.

    This is the one check every route that finishes a page not yet saved goes
    through: finishing an import, showing a page again, and approving it
    again. A yes binds to the exact bytes the person was shown, so the page
    has to come out to them today, through today's cleaning and its
    inspection copy. The answer is the same, unreadable just now, changed
    (the original itself is different), or rechecked (the original is the
    same and GTM Base now cleans or refuses it differently).
    """
    original = _original_digest(run_id, segment)
    if original is None:
        return "unreadable", None
    day = datetime.date.fromisoformat(yes["day"])
    try:
        cleaned = _cleaned_page(
            run_id, segment, root, address, day, check_destination=not written
        )
    except adopt.AdoptionRefused as refusal:
        if refusal.code in _COULD_NOT_READ:
            return "unreadable", None
        cleaned = None
    if cleaned is not None and cleaned.digest == yes["approved"]:
        return "same", cleaned
    if yes.get("original") == original:
        return "rechecked", None
    return "changed", None


def _finish_one(run_id, root, base_id, segment, record, text, git, now, address):
    """Take one page with a yes as far as it still has to go, and note the save.

    All of it happens with this base's writing lock held, from the look at
    the page's name to the record update that ends it, and the record is
    read again once the lock is held. What stands at the name decides: saved
    with its line, the save is only written down; saved without its line,
    the line is added and saved; written and not saved, it is cleaned again
    under today's rules and finished only when it still comes out to the
    bytes of the yes, and otherwise taken back and shown again; changed by
    the person before its save, what this import started is taken back and
    the changed copy left; nothing there, it is written from `text`, which
    has to be the approved bytes; anything else there, it is never written
    over. The line recording the yes names the run the import belongs to,
    so a page finished in a later session is written exactly as an
    uninterrupted run would have.
    """
    relative = segment.destination
    with _Writing(base_id):
        record = segments.load_import(base_id) or record
        yes = record.approved(segment.slug)
        if yes is None:
            raise adopt.AdoptionRefused(adopt.CODE_NOT_SHOWN)
        digest = yes["approved"]
        if record.state_of(segment.slug) == segments.STATE_COMMITTED:
            where = review.page_state(git, root, relative, digest, run=record.run)
            if where == review.PAGE_SAVED:
                return review.ApproveResult(
                    relative, review.head_now(git, root), [], root, base_id
                )
        where = review.page_state(git, root, relative, digest, run=record.run)
        if where == review.PAGE_OTHER:
            raise ReviewError(segments.CODE_FILE_TAKEN, code=segments.CODE_FILE_TAKEN)
        if where == review.PAGE_EDITED:
            review.take_back_unsaved(root, relative, digest, runner=git)
            raise ReviewError(CODE_PAGE_EDITED, code=CODE_PAGE_EDITED)
        if where == review.PAGE_SAVED:
            result = review.ApproveResult(
                relative, review.head_now(git, root), [], root, base_id
            )
        elif where == review.PAGE_SAVED_UNCONFIRMED:
            # Saved by another window before its line was added: the line is
            # added and saved now, because an adoption is finished only when
            # the page, its line, and the import's own run are all there
            # (Astra's review of the merged units, finding 4).
            result = review.confirm_saved(
                root, base_id, relative, record.run, runner=git, now=now
            )
        elif where == review.PAGE_WRITTEN:
            verdict, _cleaned = _revalidate(
                run_id, segment, root, address, yes, written=True
            )
            if verdict == "unreadable":
                raise adopt.AdoptionRefused(adopt.CODE_UNREADABLE)
            if verdict != "same":
                review.take_back_unsaved(root, relative, digest, runner=git)
                segments.clear(base_id, segment.slug, run=record.run)
                if verdict == "rechecked":
                    raise adopt.AdoptionRefused(CODE_CLEANED_AGAIN, CLEANED_AGAIN_SAID)
                raise adopt.AdoptionRefused(adopt.CODE_CHANGED)
            result = review.finish_adopted(
                root, base_id, relative, digest, record.run,
                runner=git, now=now, email=address,
            )
        else:
            if text is None:
                raise adopt.AdoptionRefused(adopt.CODE_CHANGED)
            review.put_back_unwritten(root, relative, runner=git)
            result = review.approve_adopted(
                root, base_id, relative, text, digest, record.run,
                runner=git, now=now, email=address,
            )
        segments.mark(
            base_id, segment.slug, segments.STATE_COMMITTED, digest, yes["day"],
            run=record.run,
        )
    return result


def adoption_leave_out(
    run_id: str,
    slug: Optional[str],
    base_root: Optional[str],
    runner: Optional[GitRunner] = None,
) -> str:
    """Write down the person's no to one finished page, so it is never asked again.

    Nothing is written into the base. A page already saved stays saved, is
    given its line when another window saved it without one, and is said to
    be saved. A page this import wrote and did not save is taken back first,
    its staging and its line with it, so nothing of it is left half done; a
    copy the person changed is left where it is. All of it happens with the
    base's writing lock held, and the page is looked at again once it is
    held, so a page another window has just saved is never taken back
    (Astra's review of the merged units, finding 1).
    """
    segment = segment_to_adopt(run_id, slug)
    git = runner_or_default(runner)
    root, base_id = _adoption_base(base_root, git)
    if _carry(run_id, base_id) is None:
        return LEFT_OUT_SAID
    with _Writing(base_id):
        record = segments.load_import(base_id)
        if record is None:
            return LEFT_OUT_SAID
        yes = record.approved(segment.slug)
        if yes is not None:
            where = review.page_state(
                git, root, segment.destination, yes["approved"], run=record.run
            )
            if where in (review.PAGE_SAVED, review.PAGE_SAVED_UNCONFIRMED):
                address = _owner_address(root, None, git)
                _finish_one(run_id, root, base_id, segment, record, None, git, None, address)
                return ALREADY_SAVED
            if where in (review.PAGE_WRITTEN, review.PAGE_EDITED, review.PAGE_ABSENT):
                review.take_back_unsaved(
                    root, segment.destination, yes["approved"], runner=git
                )
        segments.mark(base_id, segment.slug, segments.STATE_LEFT_OUT, run=record.run)
    return LEFT_OUT_SAID


class Resumed(object):
    """What finishing an import did, and what is still to be shown and asked."""

    __slots__ = (
        "finished",
        "changed",
        "taken",
        "edited",
        "unreadable",
        "rechecked",
        "to_show",
        "done",
        "set_aside",
        "stopped",
        "to_draft",
        "drafts_saved",
        "drafted_again",
        "had_drafts",
    )

    def __init__(
        self,
        finished=(),
        changed=(),
        taken=(),
        to_show=(),
        done=False,
        edited=(),
        unreadable=(),
        set_aside=False,
        stopped=None,
        rechecked=(),
        to_draft=(),
        drafts_saved=(),
        drafted_again=(),
        had_drafts=False,
    ):
        self.finished = list(finished)
        self.changed = list(changed)
        self.taken = list(taken)
        self.edited = list(edited)
        self.unreadable = list(unreadable)
        self.rechecked = list(rechecked)
        self.to_show = list(to_show)
        self.done = bool(done)
        self.set_aside = bool(set_aside)
        # (the segment it stopped at, the code, the sentence), or None.
        self.stopped = stopped
        # Call 29: segments still to draft, drafts with a yes now saved, and
        # drafts approved whose save never started, which are drafted again.
        self.to_draft = list(to_draft)
        self.drafts_saved = list(drafts_saved)
        self.drafted_again = list(drafted_again)
        # Whether the import held any segment to draft, which decides the
        # words said once nothing is left.
        self.had_drafts = bool(had_drafts)

    def sentences(self) -> List[str]:
        said = []
        if self.set_aside:
            said.append(RESUME_UNREADABLE)
        if len(self.finished) == 1:
            said.append(RESUME_FINISHED_ONE)
        elif self.finished:
            said.append(RESUME_FINISHED % len(self.finished))
        if len(self.drafts_saved) == 1:
            said.append(RESUME_DRAFT_SAVED_ONE)
        elif self.drafts_saved:
            said.append(RESUME_DRAFT_SAVED % len(self.drafts_saved))
        for segment in self.taken:
            said.append(RESUME_TAKEN % {"name": segment.name})
        for segment in self.edited:
            said.append(RESUME_EDITED % {"name": segment.name})
        for segment in self.unreadable:
            said.append(RESUME_CANNOT_READ % {"name": segment.name})
        if self.stopped is not None:
            segment, _code, sentence = self.stopped
            said.append(sentence)
            said.append(RESUME_STOPPED % {"name": segment.name})
            return said
        for segment in self.changed:
            said.append(RESUME_CHANGED % {"name": segment.name})
        for segment in self.rechecked:
            said.append(RESUME_RECHECKED % {"name": segment.name})
        for segment in self.drafted_again:
            said.append(RESUME_DRAFT_AGAIN % {"name": segment.name})
        if len(self.to_show) == 1:
            said.append(RESUME_TO_SHOW_ONE)
        elif self.to_show:
            said.append(RESUME_TO_SHOW % len(self.to_show))
        if len(self.to_draft) == 1:
            said.append(RESUME_TO_DRAFT_ONE)
        elif self.to_draft:
            said.append(RESUME_TO_DRAFT % len(self.to_draft))
        if self.done:
            said.append(RESUME_ALL_SETTLED if self.had_drafts else RESUME_DONE)
        if not said:
            said.append(RESUME_NOTHING)
        return said

    def __repr__(self) -> str:
        return "Resumed(finished=%d, to_show=%d)" % (len(self.finished), len(self.to_show))


def _run_is_free(run_id: str, record_run: Optional[str]) -> bool:
    """Whether a run holds nothing of its own, or only what a resume gave it.

    A run in the middle of its own setup, with a list agreed to, segments
    settled, text pasted in, or a list shown, is never cleared or seeded by
    a resume, whatever run identifier it was handed.
    """
    consent = _consent_payload(run_id)
    if consent is not None:
        return bool(consent.get("resumed")) and (
            record_run is None or consent.get("resumed") == record_run
        )
    return (
        load_inventory(run_id) is None
        and not _holds_pastes(run_id)
        and load_listing(run_id) is None
    )


def _seed_run(run_id: str, record, session_id: str) -> None:
    """Give a fresh run what the import needs, from the record kept for it.

    The run is given the inventory, the numbered documents, what the base is
    for, and a yes that reaches only the pages still to be finished, so every
    step of Unit 1.7c runs in it exactly as it ran in the run that started
    the import. A run that settled segments of its own is not seeded. The
    session is recorded as one that has read the person's own writing before
    a page is opened, because nothing may leave the computer after that.
    """
    folder = scratch_dir(run_id)
    if not _run_is_free(run_id, record.run):
        raise adopt.AdoptionRefused(CODE_RUN_HAS_ITS_OWN, RESUME_RUN_HAS_ITS_OWN)
    still = set(segment.source for segment in record.pages_unfinished())
    marker.write_sources_read_marker(session_id)
    atomic_write_json(
        os.path.join(folder, CONSENT_FILE),
        {
            "root": record.consent["root"],
            "folders": [],
            "choice": record.consent["choice"],
            "named": [],
            "from_survey": False,
            "added": [],
            "dropped": list(record.consent["dropped"]),
            "scope": record.consent["scope"],
            "session_id": session_id,
            "frozen_at": record.consent["frozen_at"],
            "paths": [path for path in record.consent["paths"] if path in still],
            "resumed": record.run,
        },
        inside=paths.seat_home(),
    )
    segments.save_candidates(folder, record.candidates, paths.seat_home())
    segments.save(folder, record.inventory, paths.seat_home())


# Refusals from reading a page's original that say it could not be read, as
# against a page that was read and came out different.
_COULD_NOT_READ = (adopt.CODE_UNREADABLE,)


def resume_import(
    run_id: str,
    base_root: Optional[str],
    session_id: str,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> Resumed:
    """Finish an import that stopped, in a fresh run, asking nothing already answered.

    Every page the person said yes to is finished from what the base holds: a
    page saved at some point is noted, a page written and not saved is
    finished from its bytes, and a page not written yet is cleaned again from
    its original on the day it was shown and written when it comes out to the
    same bytes. A page whose original changed since the yes is shown again;
    one whose original could not be read just now keeps its yes for next
    time. A page with other bytes at its name is never written over, and is
    named. A page changed by the person before its save has what this import
    started taken back. A page left out or refused stays that way. What is
    left is only the pages nobody has answered for, which the skill shows and
    asks about in this run. When one page cannot be finished, finishing stops
    there, and what was already finished is still said. Once nothing is left,
    the record is let go and this run's folder is cleared.
    """
    git = runner_or_default(runner)
    root, base_id = _adoption_base(base_root, git)
    on_default, _code = paths.head_is_default_branch(root, runner=git)
    if not on_default:
        raise ReviewError(review.CODE_NOT_DEFAULT_BRANCH, code=review.CODE_NOT_DEFAULT_BRANCH)
    record = segments.load_import(base_id)
    if record is None:
        if not _run_is_free(run_id, None):
            raise adopt.AdoptionRefused(CODE_RUN_HAS_ITS_OWN, RESUME_RUN_HAS_ITS_OWN)
        set_aside = segments.set_aside_unreadable(base_id)
        clear_scratch(run_id)
        return Resumed(set_aside=set_aside)
    if not record.unfinished():
        if not _run_is_free(run_id, record.run):
            raise adopt.AdoptionRefused(CODE_RUN_HAS_ITS_OWN, RESUME_RUN_HAS_ITS_OWN)
        segments.forget_import(base_id)
        clear_scratch(run_id)
        return Resumed(done=True, had_drafts=bool(record.to_draft()))
    _seed_run(run_id, record, session_id)
    address = _owner_address(root, email, git)
    result = Resumed(had_drafts=bool(record.to_draft()))
    order = [segment.slug for segment in record.kept()]
    current = record.unfinished()[0]

    def finish(segment, text):
        """Finish one page through the one shared path, and sort the answer."""
        try:
            _finish_one(run_id, root, base_id, segment, record, text, git, now, address)
        except adopt.AdoptionRefused as refusal:
            if refusal.code == CODE_CLEANED_AGAIN:
                result.rechecked.append(segment)
                result.to_show.append(segment)
                return
            if refusal.code == adopt.CODE_CHANGED:
                result.changed.append(segment)
                result.to_show.append(segment)
                return
            if refusal.code in _COULD_NOT_READ:
                result.unreadable.append(segment)
                return
            raise
        except ReviewError as refusal:
            if refusal.code == CODE_PAGE_EDITED:
                result.edited.append(segment)
                return
            raise
        result.finished.append(segment)

    try:
        # Everything that looks at a page and changes it happens with the
        # base's writing lock held, and the record is read again once it is
        # (Astra's review of the merged units, finding 1).
        with _Writing(base_id):
            record = segments.load_import(base_id) or record
            # Pages already at their name come first: finishing one clears the
            # only unsaved work an import can leave, and every other write
            # needs a base with nothing half done in it.
            waiting = []
            for segment in record.pages_unfinished():
                current = segment
                yes = record.approved(segment.slug)
                if yes is None:
                    result.to_show.append(segment)
                    continue
                where = review.page_state(
                    git, root, segment.destination, yes["approved"], run=record.run
                )
                if where == review.PAGE_OTHER:
                    # Never written over. One the base has saved is named once
                    # and settled; an unsaved one is left for the person, and
                    # its yes stands for when it is gone.
                    result.taken.append(segment)
                    if review.held_at_head(git, root, segment.destination):
                        segments.mark(
                            base_id, segment.slug, segments.STATE_REFUSED, run=record.run
                        )
                elif where == review.PAGE_ABSENT:
                    waiting.append((segment, yes))
                else:
                    finish(segment, None)
            for segment, yes in waiting:
                current = segment
                verdict, cleaned = _revalidate(
                    run_id, segment, root, address, yes, written=False
                )
                if verdict == "unreadable":
                    result.unreadable.append(segment)
                elif verdict == "same":
                    finish(segment, cleaned.text)
                else:
                    segments.clear(base_id, segment.slug, run=record.run)
                    (result.rechecked if verdict == "rechecked" else result.changed).append(
                        segment
                    )
                    result.to_show.append(segment)
            # Then each segment settled to be drafted and not yet saved
            # (call 29): a draft with a yes is finished from what the base
            # holds, and the rest are named, to be drafted after a fresh yes.
            record = segments.load_import(base_id) or record
            for segment in record.drafts_unfinished():
                current = segment
                _settle_a_draft(root, base_id, segment, record, git, now, address, result)
    except (ReviewError, adopt.AdoptionRefused, segments.InventoryRefused, PathError) as refusal:
        code = getattr(refusal, "code", None) or review.CODE_GIT_FAILED
        sentence = getattr(refusal, "sentence", "") or BASE_REFUSALS.get(code) or ""
        result.stopped = (current, code, sentence)
        return result
    result.to_show.sort(key=lambda segment: order.index(segment.slug))
    result.to_draft.sort(key=lambda segment: order.index(segment.slug))
    left = segments.load_import(base_id)
    result.done = (
        not result.to_show
        and not result.to_draft
        and (left is None or not left.unfinished())
    )
    if result.done:
        segments.forget_import(base_id)
        clear_scratch(run_id)
    return result


# --- A segment left to draft past the closing (Brandon's call 29) -------------
#
# Setup drafts each segment settled to be drafted in step 6c, before the
# closing, and the yes to read the material it is drafted from is the run's,
# which the closing clears. A segment nobody drafted by then is kept in the
# import record Unit 1.7d keeps (its name and settled answer, which the
# inventory holds, and one state), and a later session drafts it after asking
# again to read its material. The yes is never carried over: the later
# session drafts in a run of its own, shows the list of files that would be
# read, and takes a new yes, exactly as Unit 1.6's consent step does. Only the
# numbered document the record kept for the segment is offered, and the
# person may add a folder or drop a file. A list changed after the yes needs a
# yes of its own. Material that is gone is said plainly, with two choices,
# and nothing is drafted from nothing.
#
# A segment's draft is written the same way a finished page is: the yes (the
# hash of the approved bytes and the day) is written down first, then the
# file, its staging, its line and the save, and then the save is written
# down. So a session that stops anywhere in between is finished by the next
# one from what the base holds, and a draft whose save never started is
# drafted again, because the record never holds a draft.

# The file in a run's own folder saying it was made to draft one segment of
# one import, and which.
FINISHING_FILE = "finishing.json"

CODE_NOT_TO_FINISH = "not-a-segment-to-finish"
CODE_DRAFT_RUN_TAKEN = "run-holds-its-own-list"
CODE_DRAFT_IN_PROGRESS = "segment-being-saved"
CODE_MATERIAL_GONE = "material-gone"
CODE_NOTHING_ON_THE_LIST = "nothing-on-the-list"
CODE_DRAFT_NO_SUCH_NUMBER = "no-such-file-number"
CODE_DRAFT_FOLDER_MISSING = "no-such-folder-to-add"
CODE_DRAFT_LIST_CHANGED = "draft-list-changed"
CODE_DRAFT_NO_LIST = "no-draft-list"
CODE_DRAFT_NOT_AGREED = "draft-list-not-agreed"

# Said at the closing when a segment settled to be drafted is not in the base.
CLOSING_DRAFTS_UNFINISHED = (
    "Some of the segments you chose are not in your base yet, and the next "
    "session will offer to finish them, asking you again before it reads any "
    "of your files to draft one."
)
# Said when finishing saved segments whose drafts had already been approved.
RESUME_DRAFT_SAVED_ONE = (
    "One segment you had already approved is now saved into your base."
)
RESUME_DRAFT_SAVED = (
    "%d segments you had already approved are now saved into your base."
)
# Said when a draft was approved and the session stopped before its save began.
RESUME_DRAFT_AGAIN = (
    "%(name)s was approved, but the session stopped before it was saved, so "
    "it will be drafted again."
)
# Said when segments settled to be drafted are still to be drafted.
RESUME_TO_DRAFT_ONE = (
    "One segment you chose to have drafted is not in your base yet. Before it "
    "is drafted, you will see which of your files it would read and be asked "
    "again."
)
RESUME_TO_DRAFT = (
    "%d segments you chose to have drafted are not in your base yet. Before "
    "each one is drafted, you will see which of your files it would read and "
    "be asked again."
)
# Said once nothing is left, when the import held a segment to draft.
RESUME_ALL_SETTLED = (
    "Every segment you chose is now settled, and nothing is left to finish."
)
# Said above the list of files a segment's draft would read.
DRAFT_LIST_OFFER = (
    "To draft %(name)s, GTM Base would read the files below and nothing else."
)
# Said when the document named for the segment is gone or can no longer be read.
DRAFT_MATERIAL_GONE = (
    "The document you named for %(name)s is gone, or has changed so that it "
    "can no longer be read, so nothing will be drafted from it. Name the "
    "folder that holds its material now, or leave that segment out."
)
# Said when there is nothing on the list at all.
DRAFT_NOTHING_ON_THE_LIST = (
    "Nothing is on the list to draft %(name)s from yet. Name the folder that "
    "holds its material, or leave that segment out."
)
DRAFT_NOT_TO_FINISH = (
    "That segment is not one still waiting to be drafted, so nothing was done."
)
DRAFT_RUN_TAKEN = (
    "This setup run already holds a list of its own, so nothing was shown. "
    "Start a new run and ask again."
)
DRAFT_IN_PROGRESS = (
    "That segment was approved and is still being saved, so nothing was "
    "shown. Say \"finish setting up my base\" to finish saving it."
)
DRAFT_NO_SUCH_NUMBER = (
    "That is not one of the numbers beside the files on the list, so nothing "
    "was changed. Read the list out again and ask which of those."
)
DRAFT_FOLDER_MISSING = (
    "That folder is not on this computer, so nothing was added to the list."
)
DRAFT_LIST_CHANGED = (
    "One of those files changed after the list was shown, so the yes was not "
    "taken. Show the list again and ask again."
)
DRAFT_NO_LIST = (
    "No list has been shown for this segment yet, so there is no yes to take. "
    "Show the list first."
)
DRAFT_NOT_AGREED = (
    "Nothing has been agreed to be read for that segment yet, so nothing was "
    "written. Show the list of files it would read and ask first."
)
DRAFT_LEFT_OUT = "%(name)s is left out, and nothing was drafted for it."

# The one sentence said for each refusal of the steps above that names no
# segment. The script reads it.
DRAFT_SENTENCES = {
    CODE_NOT_TO_FINISH: DRAFT_NOT_TO_FINISH,
    CODE_DRAFT_RUN_TAKEN: DRAFT_RUN_TAKEN,
    CODE_DRAFT_IN_PROGRESS: DRAFT_IN_PROGRESS,
    CODE_DRAFT_NO_SUCH_NUMBER: DRAFT_NO_SUCH_NUMBER,
    CODE_DRAFT_FOLDER_MISSING: DRAFT_FOLDER_MISSING,
    CODE_DRAFT_LIST_CHANGED: DRAFT_LIST_CHANGED,
    CODE_DRAFT_NO_LIST: DRAFT_NO_LIST,
    CODE_DRAFT_NOT_AGREED: DRAFT_NOT_AGREED,
}


def _draft_refusal(code: str, sentence: str = "") -> ConsentError:
    refusal = ConsentError(code, code=code)
    refusal.sentence = sentence or DRAFT_SENTENCES.get(code, "")
    return refusal


def _finishing(run_id: str) -> Optional[dict]:
    """What a run made to draft one segment is for, or None for any other run."""
    try:
        payload = read_json(os.path.join(scratch_dir(run_id), FINISHING_FILE))
    except GtmBaseError:
        return None
    if not isinstance(payload, dict):
        return None
    run = payload.get("run")
    slug = payload.get("segment")
    base_id = payload.get("base_id")
    if not ids.is_run_id(run) or not isinstance(base_id, str) or not base_id:
        return None
    if not isinstance(slug, str) or segments.slug_problem(slug) is not None:
        return None
    return {"run": run, "segment": slug, "base_id": base_id}


def _run_holds_nothing(run_id: str) -> bool:
    """Whether a run holds no yes, no list, no segments, and no pasted text."""
    return (
        _consent_payload(run_id) is None
        and load_listing(run_id) is None
        and load_inventory(run_id) is None
        and not _holds_pastes(run_id)
    )


def _to_finish(record, slug: Optional[str]) -> segments.Segment:
    """The segment settled to be drafted and still waiting, or a refusal."""
    segment = record.find(slug) if (record is not None and slug) else None
    if segment is None or not record.is_a_draft(segment.slug):
        raise _draft_refusal(CODE_NOT_TO_FINISH)
    if segment not in record.drafts_unfinished():
        raise _draft_refusal(CODE_NOT_TO_FINISH)
    if record.approved(segment.slug) is not None:
        raise _draft_refusal(CODE_DRAFT_IN_PROGRESS)
    return segment


def _seed_draft_run(run_id: str, record, segment) -> None:
    """Give a run what drafting one segment needs from the record, and no yes.

    The run is given the settled inventory, the numbered documents, and what
    the base is for, so every step of step 6c runs in it as it ran in setup.
    It is never given a list of files anybody agreed to: that is asked again.
    A run holding anything of its own is refused, and so is one already made
    to draft another segment. Giving it all of this again is harmless, so a
    stop partway through is finished by asking again.
    """
    held = _finishing(run_id)
    if held is not None:
        if (
            held["run"] != record.run
            or held["segment"] != segment.slug
            or held["base_id"] != record.base_id
        ):
            raise _draft_refusal(CODE_DRAFT_RUN_TAKEN)
    elif not _run_holds_nothing(run_id):
        raise _draft_refusal(CODE_DRAFT_RUN_TAKEN)
    folder = scratch_dir(run_id)
    atomic_write_json(
        os.path.join(folder, FINISHING_FILE),
        {"run": record.run, "segment": segment.slug, "base_id": record.base_id},
        inside=paths.seat_home(),
    )
    segments.save_candidates(folder, record.candidates, paths.seat_home())
    segments.save(folder, record.inventory, paths.seat_home())
    scope = record.consent.get("scope")
    if scope is not None:
        covers = _scope_value(scope)
        atomic_write_json(
            os.path.join(folder, SCOPE_FILE),
            {"whole": not covers, "covers": covers, "fixed": True},
            inside=paths.seat_home(),
        )


def _kept_document(record, segment) -> Optional[str]:
    """The numbered document the record kept for a segment, or None."""
    if segment.number is None:
        return None
    for candidate in record.candidates:
        if candidate.number == segment.number:
            return candidate.path
    return None


def _list_digest(entries) -> str:
    """One value standing for exactly the files shown and how each would be read."""
    lines = ["%s\t%s" % (os.path.realpath(entry.path), entry.kind) for entry in entries]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _list_manifest(paths_) -> str:
    """The value a yes to this list is kept with, as Unit 1.6 keeps one."""
    payload = json.dumps(
        {"finishing": True, "choice": constants.CHOICE_EXPLICIT, "paths": list(paths_)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DraftList(object):
    """The files a segment's draft would read, shown before any yes."""

    __slots__ = ("segment", "entries", "left_out", "gone")

    def __init__(self, segment, entries, left_out=None, gone=False):
        self.segment = segment
        self.entries = list(entries)
        # How many files of each folder added were left out, by reason.
        self.left_out = dict(left_out or {})
        # Whether the document named for the segment is gone, or has changed
        # so that it can no longer be read.
        self.gone = bool(gone)

    @property
    def paths(self) -> List[str]:
        return [os.path.realpath(entry.path) for entry in self.entries]

    @property
    def code(self) -> Optional[str]:
        if self.entries:
            return None
        return CODE_MATERIAL_GONE if self.gone else CODE_NOTHING_ON_THE_LIST

    def sentences(self) -> List[str]:
        named = {"name": self.segment.name}
        if self.entries:
            return [DRAFT_LIST_OFFER % named]
        if self.gone:
            return [DRAFT_MATERIAL_GONE % named]
        return [DRAFT_NOTHING_ON_THE_LIST % named]

    def __repr__(self) -> str:
        return "DraftList(%r, files=%d)" % (self.segment.slug, len(self.entries))


def draft_list(
    run_id: str,
    slug: Optional[str],
    base_root: Optional[str],
    added: Sequence[str] = (),
    dropped: Sequence[int] = (),
    today=None,
    runner: Optional[GitRunner] = None,
) -> DraftList:
    """Show the files one segment still to draft would be drafted from.

    Nothing is read but what the walk reads to decide whether a file could
    be read at all, and nothing is agreed to here. The first time, the list
    holds the numbered document the record kept for the segment, checked
    again as the walk would check it now. `dropped` takes files off the list
    last shown in this run, by the numbers printed beside them, and never
    adds. `added` puts the readable files of a folder the person named on it,
    which is their own choice and so is never narrowed again. The list is
    written down in the run with the value a yes to it is kept with, so a
    list shown after a yes is a list that needs a yes of its own.
    """
    git = runner_or_default(runner)
    day = today or state.today()
    _root, base_id = _adoption_base(base_root, git)
    record = segments.load_import(base_id)
    segment = _to_finish(record, slug)
    _seed_draft_run(run_id, record, segment)

    kept = _kept_document(record, segment)
    gone = False
    if kept is not None:
        entry, _code = sources_module.file_entry(kept, today=day)
        gone = entry is None
    shown = load_listing(run_id)
    if shown is not None and shown.get("finishing") == segment.slug:
        start = list(shown["paths"])
    else:
        start = [os.path.realpath(kept)] if (kept is not None and not gone) else []

    wanted = []
    for number in dropped or ():
        if isinstance(number, bool) or not isinstance(number, int):
            raise _draft_refusal(CODE_DRAFT_NO_SUCH_NUMBER)
        if number < 1 or number > len(start):
            raise _draft_refusal(CODE_DRAFT_NO_SUCH_NUMBER)
        wanted.append(start[number - 1])
    chosen = [path for path in start if path not in wanted]

    left_out = {}
    for folder in added or ():
        root = os.path.realpath(os.path.abspath(os.path.expanduser(str(folder or ""))))
        if not folder or not os.path.isdir(root):
            raise _draft_refusal(CODE_DRAFT_FOLDER_MISSING)
        listing = sources_module.list_folder(root, today=day)
        for entry in files_in_order(listing):
            real = os.path.realpath(entry.path)
            if real not in chosen:
                chosen.append(real)
        for reason, count in listing.excluded_counts.items():
            left_out[reason] = left_out.get(reason, 0) + count

    entries = []
    for path in chosen:
        entry, code = sources_module.file_entry(path, today=day)
        if entry is None:
            left_out[code] = left_out.get(code, 0) + 1
            continue
        entries.append(entry)
    result = DraftList(segment, entries, left_out, gone)

    paths_ = result.paths
    atomic_write_json(
        os.path.join(scratch_dir(run_id), LISTING_FILE),
        {
            "root": "",
            "digest": _list_digest(entries),
            "note": False,
            "narrow_first": False,
            "choice": constants.CHOICE_EXPLICIT,
            "named": [],
            "manifest": _list_manifest(paths_),
            "folders": [],
            "from_survey": False,
            "added": [],
            "dropped": [],
            "scope": held_scope(run_id),
            "folder_names": [],
            "paths": paths_,
            "finishing": segment.slug,
        },
        inside=paths.seat_home(),
    )
    return result


def draft_freeze(run_id: str, session_id: str, today=None):
    """Take the yes to the list a segment's draft would read, and fix it.

    The list shown is checked again, file by file, the way it was checked
    when it was shown, and a list that changed in between is not agreed to.
    From this yes on, nothing leaves this computer for the rest of the
    session, exactly as after the yes in setup.
    """
    held = _finishing(run_id)
    shown = load_listing(run_id)
    if held is None or shown is None:
        raise _draft_refusal(CODE_DRAFT_NO_LIST)
    record = segments.load_import(held["base_id"])
    segment = _to_finish(record, held["segment"])
    if record.run != held["run"] or shown.get("finishing") != segment.slug:
        raise _draft_refusal(CODE_DRAFT_NO_LIST)
    paths_ = list(shown["paths"])
    if not paths_:
        raise _draft_refusal(
            CODE_NOTHING_ON_THE_LIST,
            DRAFT_NOTHING_ON_THE_LIST % {"name": segment.name},
        )
    day = today or state.today()
    entries = []
    for path in paths_:
        entry, _code = sources_module.file_entry(path, today=day)
        if entry is None or os.path.realpath(entry.path) != path:
            raise _draft_refusal(CODE_DRAFT_LIST_CHANGED)
        entries.append(entry)
    if _list_digest(entries) != shown["digest"] or _list_manifest(paths_) != shown["manifest"]:
        raise _draft_refusal(CODE_DRAFT_LIST_CHANGED)
    scope = held_scope(run_id)
    consent = sources_module.ConsentList.freeze_paths(
        paths_, session_id, scope=scope or ""
    )
    atomic_write_json(
        os.path.join(scratch_dir(run_id), CONSENT_FILE),
        {
            "root": "",
            "folders": [],
            "choice": constants.CHOICE_EXPLICIT,
            "named": [],
            "manifest": shown["manifest"],
            "from_survey": False,
            "added": [],
            "dropped": [],
            "scope": scope,
            "session_id": consent.session_id,
            "frozen_at": consent.frozen_at,
            "paths": list(consent.paths),
            "finishing": held["run"],
        },
        inside=paths.seat_home(),
    )
    return consent


def _approve_a_segment(run_id, draft, slug, base_root, email, git, now):
    """Write an approved segment through the write-ahead path, or None.

    None means no record is kept for this segment, which is a run that never
    kept one, and the draft is written the way it always was. Otherwise the
    yes is written down before anything touches the base and the save after
    it lands, exactly as for a finished page, so a stop anywhere is finished
    by the next session (call 29). In a run a later session made to draft the
    segment, the draft is written only once that run holds a yes to read its
    material, to the list shown last, because a draft is never written from
    nothing.
    """
    resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
    root = resolution.root or base_root
    base_id = resolution.base_id
    finishing = _finishing(run_id)
    if finishing is not None:
        consent = load_consent(run_id)
        if consent is None or not consent.paths:
            raise ReviewError(CODE_DRAFT_NOT_AGREED, code=CODE_DRAFT_NOT_AGREED)
        try:
            _refuse_a_yes_given_to_another_list(run_id)
        except ConsentError:
            raise ReviewError(CODE_DRAFT_NOT_AGREED, code=CODE_DRAFT_NOT_AGREED)
    try:
        record = _carry(run_id, base_id)
    except GtmBaseError:
        record = None
    if finishing is not None and record is None:
        raise ReviewError(CODE_NOT_TO_FINISH, code=CODE_NOT_TO_FINISH)
    if record is None or not record.is_a_draft(slug or ""):
        return None
    segment = record.find(slug)
    relative = segment.destination
    address = _owner_address(root, email, git)
    text = review.stamp_owner(draft, address).text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    day = state.today(now) if now else state.today()
    with _Writing(base_id):
        record = segments.load_import(base_id) or record
        # Every check the write makes, before the yes is written down, so a
        # refusal leaves nothing written anywhere.
        review.check_segment_write(root, relative, git)
        codes = review.screen(text, address, review.frontmatter_line_numbers(text))
        if codes:
            raise ReviewError(review.CODE_SCREENED, codes=codes)
        segments.mark(
            base_id, segment.slug, segments.STATE_APPROVED, digest, day.isoformat(),
            run=record.run,
        )
        try:
            result = review.approve_adopted(
                root, base_id, relative, text, digest, record.run,
                runner=git, now=now, email=address,
            )
        except ReviewError:
            # Nothing of it is in the base, so the yes goes too, and asking
            # again writes it. Anything that might be is left for the next
            # attempt to finish from what the base holds.
            if review.page_state(git, root, relative, digest, run=record.run) == (
                review.PAGE_ABSENT
            ):
                segments.clear(base_id, segment.slug, run=record.run)
            raise
        segments.mark(
            base_id, segment.slug, segments.STATE_COMMITTED, digest, day.isoformat(),
            run=record.run,
        )
    if finishing is not None:
        # The yes to read was this run's alone, and the segment is saved.
        clear_scratch(run_id)
    return result


def _settle_a_draft(root, base_id, segment, record, git, now, address, result) -> None:
    """Take one segment still to draft as far as it can go, and sort the answer.

    A segment with no yes is named to be drafted, unless something already
    stands at its name, which is never written over and is named once. A yes
    whose bytes were saved is written down as saved, given its line first
    when another window saved it without one. A yes whose bytes sit at the
    name unsaved is finished from those bytes. A yes whose save never began is
    taken back, and the segment is drafted again, because the draft itself
    was never kept. A copy the person changed before its save has what this
    import started taken back and is left as it is.
    """
    relative = segment.destination
    yes = record.approved(segment.slug)
    if yes is None:
        found = segments.already_in_base(root, segment.slug)
        if found is None:
            result.to_draft.append(segment)
            return
        result.taken.append(segment)
        if review.held_at_head(git, root, found):
            segments.mark(base_id, segment.slug, segments.STATE_REFUSED, run=record.run)
        return
    digest = yes["approved"]
    where = review.page_state(git, root, relative, digest, run=record.run)
    if where == review.PAGE_OTHER:
        result.taken.append(segment)
        if review.held_at_head(git, root, relative):
            segments.mark(base_id, segment.slug, segments.STATE_REFUSED, run=record.run)
        return
    if where == review.PAGE_ABSENT:
        review.put_back_unwritten(root, relative, runner=git)
        segments.clear(base_id, segment.slug, run=record.run)
        result.drafted_again.append(segment)
        result.to_draft.append(segment)
        return
    if where == review.PAGE_EDITED:
        review.take_back_unsaved(root, relative, digest, runner=git)
        segments.clear(base_id, segment.slug, run=record.run)
        result.edited.append(segment)
        result.to_draft.append(segment)
        return
    if where == review.PAGE_SAVED_UNCONFIRMED:
        review.confirm_saved(root, base_id, relative, record.run, runner=git, now=now)
    elif where == review.PAGE_WRITTEN:
        review.finish_adopted(
            root, base_id, relative, digest, record.run,
            runner=git, now=now, email=address,
        )
    segments.mark(
        base_id, segment.slug, segments.STATE_COMMITTED, digest, yes["day"],
        run=record.run,
    )
    result.drafts_saved.append(segment)


def draft_leave_out(
    slug: Optional[str], base_root: Optional[str], runner: Optional[GitRunner] = None
) -> str:
    """Write down that the person left one segment still to draft out.

    Nothing is written into the base, and the segment is never offered again.
    A draft approved and not yet saved is taken back first, and one already
    saved stays saved and is said to be. Once nothing is left to finish, the
    record is let go.
    """
    git = runner_or_default(runner)
    root, base_id = _adoption_base(base_root, git)
    with _Writing(base_id):
        record = segments.load_import(base_id)
        segment = record.find(slug) if (record is not None and slug) else None
        if segment is None or not record.is_a_draft(segment.slug):
            raise _draft_refusal(CODE_NOT_TO_FINISH)
        now_in = record.state_of(segment.slug)
        if now_in == segments.STATE_COMMITTED:
            return ALREADY_SAVED
        if now_in in (segments.STATE_LEFT_OUT, segments.STATE_REFUSED):
            return DRAFT_LEFT_OUT % {"name": segment.name}
        yes = record.approved(segment.slug)
        if yes is not None:
            where = review.page_state(
                git, root, segment.destination, yes["approved"], run=record.run
            )
            if where in (review.PAGE_SAVED, review.PAGE_SAVED_UNCONFIRMED):
                if where == review.PAGE_SAVED_UNCONFIRMED:
                    review.confirm_saved(root, base_id, segment.destination, record.run, runner=git)
                segments.mark(
                    base_id, segment.slug, segments.STATE_COMMITTED, yes["approved"],
                    yes["day"], run=record.run,
                )
                return ALREADY_SAVED
            if where in (review.PAGE_WRITTEN, review.PAGE_EDITED, review.PAGE_ABSENT):
                review.take_back_unsaved(
                    root, segment.destination, yes["approved"], runner=git
                )
        segments.mark(base_id, segment.slug, segments.STATE_LEFT_OUT, run=record.run)
    segments.forget_import(base_id)
    return DRAFT_LEFT_OUT % {"name": segment.name}


class SourcesRead(object):
    """The text this run may draft from, and what had to be left out of it."""

    __slots__ = ("sources", "left_out", "removed")

    def __init__(self, sources, left_out=None, removed=None):
        self.sources = list(sources)
        # Pairs of the label and the short reason, one for each source that
        # could not be used.
        self.left_out = list(left_out or [])
        # Pairs of the label and the counts of each kind of hidden thing that
        # was taken out of it, one for each source something went from.
        self.removed = list(removed or [])

    def __repr__(self) -> str:
        return "SourcesRead(sources=%d, left_out=%d)" % (
            len(self.sources),
            len(self.left_out),
        )


# What a narrowing may name that the frozen list does not hold.
CODE_NOT_CONSENTED = "not-consented"


def _in_folder(path: str, root: str, wanted: str) -> bool:
    """Whether one file sits inside a named folder of the list that was agreed.

    By the listing's own rule, the folder at the top a file sits in, with a
    full stop for the files lying loose at the top. Finding N4 of Astra's
    fourth look: a folder name matched anywhere in a file's path, so the
    folder `b` took in a file shown under `a`, and `.` matched nothing.
    """
    if not root:
        return False
    try:
        relative = os.path.relpath(path, root)
    except ValueError:
        return False
    if relative == ".." or relative.startswith(".." + os.sep):
        return False
    return sources_module.top_folder(path, root) == wanted


def narrow(labelled, root: str = "", only=None, only_folder=None, only_index=None):
    """Keep only the part of the agreed list the person named for this draft.

    This never widens what may be read. It takes the list they already said
    yes to and keeps a part of it, so a name that is not on that list is
    refused rather than looked for on the disk. More than one folder may be
    named, and each one has to hold something, so a folder named by mistake is
    said out loud rather than quietly adding nothing.

    `only_index` is how the skill names files, by the number beside each one on
    the list that was printed. Finding N2 of the 2026-09-20 verification round:
    a label comes off a file name, a file may be named anything at all, and a
    name written into a command is somebody else's text in a command.
    """
    kept = list(labelled)
    chosen: Optional[List[str]] = None
    if only_index:
        chosen = []
        for number in only_index:
            if not isinstance(number, int) or number < 1 or number > len(labelled):
                raise ConsentError(
                    "that is not one of the files on the list you agreed to",
                    code=CODE_NOT_CONSENTED,
                )
            chosen.append(labelled[number - 1][1])
    if only_folder:
        names = [only_folder] if isinstance(only_folder, str) else list(only_folder)
        found = []
        seen = set()
        for name in names:
            wanted = str(name).strip().strip("/").replace(os.sep, "/").split("/")[-1]
            if not wanted:
                continue
            part = [pair for pair in kept if _in_folder(pair[1], root, wanted)]
            if not part:
                raise ConsentError(
                    "that folder is not part of the list you agreed to",
                    code=CODE_NOT_CONSENTED,
                )
            for pair in part:
                if pair[1] not in seen:
                    seen.add(pair[1])
                    found.append(pair)
        kept = found
    if only:
        asked = [str(name).strip() for name in only if str(name).strip()]
        held = set(label for label, _path in kept)
        for name in asked:
            if name not in held:
                raise ConsentError(
                    "that file is not on the list you agreed to",
                    code=CODE_NOT_CONSENTED,
                )
        kept = [pair for pair in kept if pair[0] in asked]
    if chosen is not None:
        kept = [pair for pair in kept if pair[1] in chosen]
        if not kept:
            raise ConsentError(
                "that is not one of the files on the list you agreed to",
                code=CODE_NOT_CONSENTED,
            )
    return kept


def read_sources(
    run_id: str,
    paste_files: Sequence[str] = (),
    today=None,
    only=None,
    only_folder=None,
    only_index=None,
) -> SourcesRead:
    """Every piece of text this run may draft from, screened and labelled.

    The files come off the frozen list, one bounded read each, and every one of
    them goes through the check that the file is on that list. The pastes, the
    PDFs, the web pages, and anything a connector handed back arrive as files
    in this run's own folder, written by the step that read them.

    One source that cannot be used never stops the rest. A single hidden
    character in one of five documents used to end the whole session, which
    turned a document the person could simply have been told about into a wall.
    What comes back instead is the sources that survived and, beside them, the
    label and the reason for every one that did not, so the person hears which
    of their own documents was left out and why. Anything a reader of the file
    would not have seen is taken out of the text rather than costing the whole
    document, and the counts of what went come back beside the sources.

    `only` and `only_folder` narrow what is read to a part of the list the
    person already agreed to. They never widen it: a name that is not on the
    frozen list is refused.

    A list shown after the yes, which the person has not said yes to, stops
    the reading altogether (Unit 1.6): the yes they gave was to another list.
    """
    _refuse_a_yes_given_to_another_list(run_id)
    consent = load_consent(run_id)
    found: List["sources_module.Source"] = []
    left_out: List[tuple] = []
    removed: List[tuple] = []

    labelled = []
    if consent is not None:
        labelled = [(_label_for(path), path) for path in consent.paths]
    for path in paste_files or ():
        labelled.append((_label_for(path), path))
    pastes = set(os.path.realpath(path) for path in (paste_files or ()))
    labelled = narrow(
        labelled, consent_root(run_id), only, only_folder, only_index
    )

    for label, path in labelled:
        if os.path.realpath(path) in pastes:
            text = read_text(path)
            if text is None:
                raise ConsentError(
                    "that pasted text is not where it was said to be",
                    code="no-paste-file",
                )
            try:
                source = sources_module.paste_source(label, text)
            except SourceRejected as refusal:
                left_out.append((label, refusal.code or "source-rejected"))
                continue
            found.append(source)
            if source.removed:
                removed.append((source.label, dict(source.removed)))
            continue

        real = sources_module.read_allowed(consent, path)
        kind = constants.SOURCE_READABLE_SUFFIXES.get(
            os.path.splitext(real)[1].lower()
        )
        if kind is None:
            left_out.append((label, sources_module.CODE_UNSUPPORTED))
            continue
        try:
            text, _notes = extract.extract(real, kind)
            when = sources_module.date_for_file(real, today=today)
            source = sources_module.make_source(
                label,
                text,
                kind,
                date=when.date,
                path=real,
                clamped=when.clamped,
            )
        except SourceRejected as refusal:
            left_out.append((label, refusal.code or "source-rejected"))
            continue
        found.append(source)
        if source.removed:
            removed.append((source.label, dict(source.removed)))
    return SourcesRead(found, left_out, removed)


def _label_for(path: str) -> str:
    name = os.path.basename(path)
    keep = [
        character if (character.isalnum() or character in " ._-") else "-"
        for character in name
    ]
    label = "".join(keep).strip()[:80]
    return label or "a source"


# --- Building the request for one step ---------------------------------------


def preview_step(
    run_id: str,
    step: str,
    paste_files: Sequence[str] = (),
    today=None,
    only=None,
    only_folder=None,
    only_index=None,
    segment: Optional[str] = None,
) -> Previewed:
    """Say what one draft would read, and what it would leave out, writing nothing.

    This is the step that goes in front of every draft. It does the reading,
    the ordering, and the cap, and then stops, so the person can be shown what
    is about to go in and can say that the documents for this one live in a
    particular folder before anything is drafted from the wrong half of their
    material.
    """
    day = today or state.today()
    settled = _step_is_this_runs(run_id, step, segment)
    read, chosen, superseded = _sources_for_a_draft(
        run_id, paste_files, day, only, only_folder, only_index, settled
    )
    plan = drafting.plan_sources(step, chosen, _own_page(settled))
    codes = list(plan.codes)
    if chosen and not plan.included:
        codes.append(drafting.CODE_NO_SOURCES)
    return Previewed(
        step,
        plan.included_labels,
        plan.dropped_labels,
        plan.ordered_labels,
        codes,
        read.left_out,
        read.removed,
        superseded=superseded,
        choice=consent_choice(run_id),
        narrowed=bool(only or only_folder or only_index),
    )


def assemble_step(
    step: str,
    run_id: str,
    company: str,
    owner_email: str,
    paste_files: Sequence[str] = (),
    today=None,
    plugin_root: Optional[str] = None,
    only=None,
    only_folder=None,
    only_index=None,
    segment: Optional[str] = None,
) -> Assembled:
    """Build the request for one step and write it into the run's own folder.

    A refusal carries the labels of the sources that could not be used, so the
    person still hears which of their own documents was left out and why even
    when nothing was left to draft from.
    """
    day = today or state.today()
    settled = _step_is_this_runs(run_id, step, segment)
    read, chosen, superseded = _sources_for_a_draft(
        run_id, paste_files, day, only, only_folder, only_index, settled
    )
    try:
        assembly = drafting.assemble(
            step,
            chosen,
            company,
            day.isoformat() if hasattr(day, "isoformat") else str(day),
            owner_email,
            plugin_root=plugin_root,
            extra=_extra_for(run_id, step, settled),
            first_path=_own_page(settled),
        )
    except DraftError as refusal:
        refusal.left_out = list(read.left_out)
        raise
    path = os.path.join(
        scratch_dir(run_id), "%s-prompt.md" % _file_stem(step, settled)
    )
    atomic_write_text(path, assembly.text, inside=paths.seat_home())
    return Assembled(
        path,
        step,
        assembly.included_labels,
        assembly.dropped_labels,
        assembly.codes,
        read.left_out,
        read.removed,
        superseded=superseded,
    )


class VersionLeftOut(object):
    """One version of a document a draft does not use, and why.

    `reason` is one of the cases the preview has a sentence for, and
    `differs` says whether its words differ from the version that was used,
    which is a conflict the person is told about rather than one settled for
    them in silence.
    """

    __slots__ = ("older", "winner", "older_line", "reason", "differs")

    FINAL = "final"
    FINAL_OVER_NEWER = "final-over-newer"
    SET_ASIDE = "set-aside"
    LATER_NUMBER = "later-number"
    NEWER = "newer"
    SAME_DAY = "same-day"

    def __init__(self, older, winner, older_line, reason, differs):
        self.older = older
        self.winner = winner
        self.older_line = older_line
        self.reason = reason
        self.differs = bool(differs)

    def __repr__(self) -> str:
        return "VersionLeftOut(older=%r, winner=%r, reason=%r)" % (
            self.older,
            self.winner,
            self.reason,
        )


def _day_of(source):
    when = getattr(source, "date", None)
    return when if hasattr(when, "toordinal") else None


def _why_this_version(winner, older) -> str:
    """Which reason put one version ahead of another, in the order they rank."""
    winner_path = getattr(winner, "path", "") or ""
    older_path = getattr(older, "path", "") or ""
    winner_day = _day_of(winner)
    older_day = _day_of(older)
    if sources_module.is_final(winner_path) and not sources_module.is_final(
        older_path
    ):
        if older_day and winner_day and older_day > winner_day:
            return VersionLeftOut.FINAL_OVER_NEWER
        if older_day and not winner_day:
            return VersionLeftOut.FINAL_OVER_NEWER
        return VersionLeftOut.FINAL
    if sources_module.is_set_aside(older_path) and not sources_module.is_set_aside(
        winner_path
    ):
        return VersionLeftOut.SET_ASIDE
    if sources_module.version_number(winner_path) > sources_module.version_number(
        older_path
    ):
        return VersionLeftOut.LATER_NUMBER
    if winner_day and (older_day is None or winner_day > older_day):
        return VersionLeftOut.NEWER
    return VersionLeftOut.SAME_DAY


def _words_of(source) -> str:
    return " ".join(str(getattr(source, "text", "") or "").split())


def choose_versions(found):
    """Keep one version of each document, and say which versions went and why.

    Unit 1.6, requirement P26. Versions are grouped by name alone, exactly as
    the survey groups them, and the one used is the one whose name says final,
    or else the newest. It takes the place of the first version of it on the
    list, so it is read as early as any version of it would have been. Now
    that the person has said yes, the words of each version left out are
    compared with the one used, and a difference is reported as a conflict
    rather than settled without a word, because a date on a file says when it
    was touched and not which version is right.

    This only ever takes versions away from what was agreed. It never adds.
    """
    groups = sources_module.version_groups(found, _day_of)
    winner_of = {}
    left: List[VersionLeftOut] = []
    for group in groups:
        winner = group[0]
        for member in group:
            winner_of[id(member)] = winner
        for older in group[1:]:
            left.append(
                VersionLeftOut(
                    older.label,
                    winner.label,
                    drafting.source_line(older),
                    _why_this_version(winner, older),
                    _words_of(older) != _words_of(winner),
                )
            )
    kept = []
    placed = set()
    for source in found:
        winner = winner_of.get(id(source), source)
        if id(winner) in placed:
            continue
        placed.add(id(winner))
        kept.append(winner)
    return kept, left


def _sources_for_a_draft(
    run_id, paste_files, day, only, only_folder, only_index, segment=None
):
    """What one draft reads: the agreed list, narrowed, one version of each.

    The preview and the request go through this one function, so the two can
    never disagree about which files a draft reads. A segment's draft reads
    the document the person named for that segment first, when they named
    one, so the cap never leaves out the one page about it.
    """
    read = read_sources(
        run_id,
        paste_files,
        today=day,
        only=only,
        only_folder=only_folder,
        only_index=only_index,
    )
    chosen, superseded = choose_versions(read.sources)
    named = getattr(segment, "source", "") if segment is not None else ""
    if named:
        wanted = os.path.realpath(named)
        first = [
            source
            for source in chosen
            if getattr(source, "path", None)
            and os.path.realpath(source.path) == wanted
        ]
        chosen = first + [source for source in chosen if source not in first]
    return read, chosen, superseded


def _own_page(segment) -> Optional[str]:
    """The document the person named for a segment, which its draft reads first."""
    return getattr(segment, "source", "") or None if segment is not None else None


def _file_stem(step: str, segment=None) -> str:
    """The start of the name of one step's request and draft in the run folder."""
    if step == drafting.STEP_SEGMENT and segment is not None:
        return "%s-%s" % (step, segment.slug)
    return step


def drafts_dir(run_id: str) -> str:
    """The folder one run's drafts are written into, made by us and not them.

    It sits under the folder this computer keeps temporary work in, and not
    under GTM Base's own records, because the check that runs before the
    file-writing tools refuses every write under the records folder and the
    consent records of this very run sit there. The assistant never chooses
    this path: it is worked out here from the run and printed for it to use.

    The folder is this person's alone, and `wordsfile` is what makes it so.
    A person's own answers sit in a folder inside this one, for the same
    reason and under the same rules.
    """
    ids.check_run_id(run_id)
    return wordsfile.run_dir(run_id)


def _private_dir(path: str) -> str:
    """One folder only this person can read, made or checked but never trusted."""
    return wordsfile.private_dir(path)


def sweep_drafts_without_a_run() -> List[str]:
    """Delete the drafts of runs this account no longer has a folder for.

    Finding N9 of the 2026-09-20 verification round. A run that is closed, or
    swept away because its day has passed, takes its own folder with it, and
    the drafts beside it were left standing whenever the closing step never
    happened. Those drafts are the company's own writing, so they go.
    """
    removed: List[str] = []
    try:
        parent = wordsfile.parent_dir()
    except StateError:
        return removed
    home = join_home()
    try:
        names = sorted(os.listdir(parent))
    except OSError:
        return removed
    for name in names:
        if not ids.is_run_id(name):
            continue
        folder = os.path.join(parent, name)
        if os.path.islink(folder) or not os.path.isdir(folder):
            continue
        if os.path.isdir(os.path.join(home, name)):
            continue
        shutil.rmtree(folder, ignore_errors=True)
        if not os.path.isdir(folder):
            removed.append(name)
    return removed


def draft_path(run_id: str, step: str, segment=None) -> str:
    """Where the assistant writes the draft for one step, and one segment."""
    return os.path.join(drafts_dir(run_id), "%s-draft.md" % _file_stem(step, segment))


def clear_drafts(run_id: str) -> bool:
    """Delete one run's drafts. Returns whether there were any to delete."""
    ids.check_run_id(run_id)
    try:
        folder = drafts_dir(run_id)
    except StateError:
        return False
    if not os.path.isdir(folder):
        return False
    shutil.rmtree(folder, ignore_errors=True)
    return not os.path.isdir(folder)


# --- Looking at a draft ------------------------------------------------------


def _address_for(base_root: Optional[str], email: Optional[str], git) -> str:
    if email:
        return email
    if base_root:
        from . import base_reader

        return base_reader.repo_email(base_root, git) or ""
    return create_base.global_email(runner=git) or ""


def review_step(
    step: str,
    draft_file: str,
    base_root: Optional[str] = None,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    run_id: Optional[str] = None,
    segment: Optional[str] = None,
) -> Reviewed:
    """Read one draft back and say whether it may be shown to the person.

    What comes back is either the word that it is ready or the classes of thing
    that were found in it, never a line of the draft itself. An umbrella is
    also measured against the inventory this run settled, and a segment is
    given the one place in the base it may be written to.
    """
    git = runner_or_default(runner)
    settled = None
    if run_id:
        settled = _step_is_this_runs(run_id, step, segment)
    elif step in (drafting.STEP_UMBRELLA, drafting.STEP_SEGMENT):
        # Both are measured against the run's own inventory, so neither can
        # be checked without the run.
        raise ReviewError(CODE_NO_RUN, code=CODE_NO_RUN)
    if settled is not None and os.path.basename(draft_file) != os.path.basename(
        draft_path(run_id, step, settled)
    ):
        # A segment's text is written only into that segment's own file, so
        # the draft has to be the one named for it (finding 7 of the unit's
        # correctness review).
        raise ReviewError(CODE_NOT_THIS_SEGMENTS_DRAFT, code=CODE_NOT_THIS_SEGMENTS_DRAFT)
    text = read_text(draft_file)
    if text is None:
        return Reviewed(step, False, ["no-draft-file"])
    draft = _parse_draft(step, text)
    if settled is not None:
        draft.destination = settled.destination
    codes = review.screen(draft, _address_for(base_root, email, git))
    if step == drafting.STEP_UMBRELLA:
        codes.extend(drafting.check_umbrella(draft, several_segments(run_id)))
    return Reviewed(
        step, not codes, codes, draft, questions=callmarkers.count(draft.text)
    )


def _parse_draft(step: str, text: str):
    """Read a draft back whether or not the file holds the fence around it.

    The assistant writes its whole answer to the file, which usually still has
    the fence in it and sometimes is the document on its own. Both are read the
    same way here, so nobody is told their document is unreadable because of a
    fence they never saw.
    """
    try:
        return drafting.parse(step, text)
    except DraftError as refusal:
        if refusal.code != drafting.CODE_NO_FENCE:
            raise
    return drafting.parse(step, "```markdown\n" + text.rstrip("\n") + "\n```\n")


def what_is_wrong(step: str, answer: str) -> str:
    """The note that asks for the same draft again. It writes nothing."""
    if step not in drafting.STEPS:
        raise ReviewError("unknown-step", code="unknown-step")
    return drafting.what_is_wrong(None, answer)


# --- Writing a draft into the base ------------------------------------------


def approve_step(
    step: str,
    draft_file: str,
    run_id: str,
    base_root: Optional[str] = None,
    parent: Optional[str] = None,
    company: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    plugin_root: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    cwd: Optional[str] = None,
    confirmed_home: bool = False,
    content_folder: Optional[str] = None,
    beside: bool = False,
    segment: Optional[str] = None,
    questions_open: bool = False,
):
    """Write one approved draft down, building the base when it is the first.

    The first approved file is what makes the base exist, so this call is where
    a folder appears on the person's computer for the first time. Every file
    after it is written into the base that is already there.

    What gets written into is the folder the resolver settled on, never the one
    the caller happened to name. A person working in the company folder names
    that folder, and the base is the `gtm-base` folder inside it.

    `content_folder` is the folder the person named at the step where they were
    told where the base would go. It is carried all the way here so that the
    base is recorded as belonging with it at the moment the base first exists,
    rather than in a later step that a closed window could skip.
    """
    git = runner_or_default(runner)
    reviewed = review_step(
        step,
        draft_file,
        base_root=base_root,
        email=email,
        runner=git,
        run_id=run_id,
        segment=segment,
    )
    if not reviewed.ready:
        raise ReviewError(review.CODE_SCREENED, codes=reviewed.codes)
    if reviewed.questions and not questions_open:
        # A draft still asking the person something is written down only once
        # they have been asked and chose to leave it open. The third real run
        # saved one nobody had looked at twice (requirement P27).
        raise ReviewError(CODE_QUESTIONS_OPEN, code=CODE_QUESTIONS_OPEN)
    if reviewed.draft.step == drafting.STEP_SEGMENT and not base_root:
        # A segment goes into a base the umbrella and the positioning already
        # made, and never makes one.
        raise ReviewError(review.CODE_NO_BASE, code=review.CODE_NO_BASE)
    if reviewed.draft.step == drafting.STEP_SEGMENT:
        written = _approve_a_segment(
            run_id, reviewed.draft, segment, base_root, email, git, now
        )
        if written is not None:
            return written
    profile = reviewed.draft.step in drafting.PROFILE_STEPS
    if profile:
        # What the base covers goes onto the profile from the answer this run
        # holds, and from nothing a draft said (Unit 1.7a, requirement P23).
        reviewed.draft = with_scope(reviewed.draft, held_scope(run_id))

    first_file = not base_root
    where = parent
    if first_file and not where:
        if not company:
            raise ReviewError("no-parent", code="no-parent")
        where = propose_location(
            company,
            cwd=cwd,
            content_folder=content_folder,
            confirmed_home=confirmed_home,
            runner=git,
            beside=beside,
        ).parent
    base_id = None
    root = base_root
    if not first_file:
        resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
        base_id = resolution.base_id
        root = resolution.root or base_root

    result = review.approve(
        reviewed.draft,
        root,
        base_id,
        run_id,
        plugin_root or drafting.plugin_root_default(),
        runner=git,
        now=now,
        first_file=first_file,
        parent=where,
        email=email,
        name=name,
        confirmed_home=confirmed_home,
        content_root=content_folder if first_file else None,
    )
    if profile:
        fix_the_scope(run_id)
    # From the moment the base exists, the finished pages this run will take
    # in, and the segments it will draft, are kept where the closing and a
    # later day cannot clear them, so an import that stops anywhere after this
    # can still be finished (calls 18 and 29). Keeping it never stands in the
    # way of the approval that just landed.
    try:
        _carry(run_id, result.base_id or base_id)
    except GtmBaseError:
        pass
    return result


def skip_step(
    step: str,
    base_root: str,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    run_id: Optional[str] = None,
):
    """Write the file a skipped step leaves behind, saying it was skipped.

    As with an approved file, what gets written into is the folder the resolver
    settled on rather than the one the caller named.

    A context change has no file to leave behind, so skipping one is the whole
    answer requirement P7 describes rather than a document written down as
    skipped. It used to be refused outright, which took skip away at exactly
    the moment the person had been shown what they would be skipping (finding
    A11 of the release review).
    """
    git = runner_or_default(runner)
    if run_id and step == drafting.STEP_ICP:
        # A run that settled several segments never writes the single
        # profile, skipped or not (finding 9 of the unit's correctness review).
        _step_is_this_runs(run_id, step)
    resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
    if step not in drafting.SKIPPED_HEADINGS and (
        drafting.step_named(step) != drafting.STEP_CHANGE
    ):
        # Only the two required documents are written down as skipped. A
        # segment nobody wants is left out, which writes nothing at all.
        raise ReviewError("cannot-skip", code="cannot-skip")
    if drafting.step_named(step) == drafting.STEP_CHANGE:
        root = resolution.root or base_root
        if not resolution.base_id:
            raise ReviewError(review.CODE_NO_BASE, code=review.CODE_NO_BASE)
        return SkippedTheChange(
            skip_the_closing_question(
                root, resolution.base_id, today=state.today(now) if now else None
            )
        )
    return review.skip(
        step,
        resolution.root or base_root,
        base_id=resolution.base_id,
        owner_email=email,
        runner=git,
        now=now,
    )


class SkippedTheChange(object):
    """What skipping the closing question leaves behind, which is one sentence.

    It looks enough like the result of skipping a document for one caller to
    print both the same way, and it carries no path, because nothing at all
    was written.
    """

    __slots__ = ("path", "codes", "sentence")

    def __init__(self, sentence):
        self.path = None
        self.codes = []
        self.sentence = sentence

    def __repr__(self) -> str:
        return "SkippedTheChange()"


# --- The closing -------------------------------------------------------------


def closing_message(
    base_root: str,
    plugin_root: Optional[str] = None,
    content_root: Optional[str] = None,
) -> str:
    """The message that ends a first session, with the folders filled in.

    There are two of them. A base that was linked to the folder a person's
    material lives in has to name both folders, because the folder they will
    open from then on is their own one and the base's own folder is the thing
    they should not have to remember. A base with no folder linked names only
    itself.
    """
    root = plugin_root or drafting.plugin_root_default()
    text = read_text(os.path.join(root, CLOSING_RULES))
    if text is None:
        raise GtmBaseError("the closing message is missing", "no-closing-rules")
    marker = CLOSING_LINKED_MARKER if content_root else CLOSING_MARKER
    _before, marker_line, after = text.partition(marker)
    if not marker_line:
        raise GtmBaseError("the closing message is missing", "no-closing-rules")
    if not content_root:
        # The plain message ends where the next heading in the file starts.
        after = after.split("\n## ")[0]
    message = after.strip("\n").replace("{{folder}}", base_root)
    if content_root:
        message = message.replace("{{content}}", content_root)
    return message + "\n"


def closing_question(plugin_root: Optional[str] = None) -> str:
    """The one question the closing asks about the business, word for word.

    What comes back is the three plain sentences that say what a context
    change is, why the base wants one, and how it is used, the one concrete
    example, and then the request itself. Requirement P4 fixes the request
    word for word, and it is read out of the closing rules rather than built
    here so that the words a person hears are the words somebody can read and
    change in one place.
    """
    root = plugin_root or drafting.plugin_root_default()
    text = read_text(os.path.join(root, CLOSING_RULES))
    if text is None:
        raise GtmBaseError("the closing question is missing", "no-closing-rules")
    _before, found, after = text.partition(CLOSING_QUESTION_MARKER)
    if not found:
        raise GtmBaseError("the closing question is missing", "no-closing-rules")
    return after.split("\n## ")[0].strip("\n") + "\n"


# --- The change somebody gives at the closing --------------------------------


class ProposedChange(object):
    """One context change, shown whole before a word of it is written down."""

    __slots__ = (
        "entry",
        "four_lines",
        "details",
        "artifact",
        "affects",
        "summary",
    )

    def __init__(self, entry, four_lines, details, artifact, affects, summary=""):
        self.entry = entry
        self.four_lines = four_lines
        # Each item is (label, value), in the order they are read out.
        self.details = list(details)
        self.artifact = artifact
        self.affects = list(affects)
        # The four lines and the three facts, all of it held apart as data.
        self.summary = summary

    def __repr__(self) -> str:
        return "ProposedChange(entry=%r)" % (getattr(self.entry, "id", None),)


def _one_line(text: str) -> str:
    """One run of words with every line break taken out of it."""
    return " ".join(str(text or "").split())


def _what_changed(entry) -> str:
    """The first line of the change, which is the sentence somebody gave."""
    return names.change_name(entry.body, None)


def _why_of(entry) -> str:
    """The reason the change gives, or the plain truth when it gives none."""
    lines = [line.strip() for line in str(entry.body or "").split("\n")]
    seen_first = False
    for line in lines:
        if not line:
            continue
        if not seen_first:
            seen_first = True
            continue
        return _one_line(line)
    return WHY_FROM_THE_CLOSING


def four_lines_for(entry) -> str:
    """One context change as the four labeled lines, and nothing else.

    Every value comes out of a file somebody typed into and is read out inside
    an instruction the assistant follows, so each one is put on a single line
    with anything that could end the block taken apart first. `moment` owns
    that rule and is asked for it rather than having it written out again
    here, because two copies of a rule is how one of them ends up not doing it.
    """
    values = (
        moment._one_line(_what_changed(entry)),
        moment._one_line(_why_of(entry)),
        moment._one_line(
            ", ".join(names.document_name(path) for path in entry.affects)
            or "nothing yet"
        ),
        moment._one_line(str(entry.review_by)),
    )
    lines = [CHANGE_OPEN]
    for label, value in zip(CHANGE_LABELS, values):
        lines.append("%s %s" % (label, value))
    lines.append(CHANGE_CLOSE)
    return "\n".join(lines)


def preview_change(
    draft,
    base_root: Optional[str] = None,
    owner_email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
) -> ProposedChange:
    """Everything about a proposed context change, before it is written.

    The change is finalized first, with the identifier and the noting address
    this plugin writes onto it, so what is shown is what gets written rather
    than a draft of it. The preview used to offer the noting address as the
    person's to correct and then write the base's own address over it a moment
    later, which is a correction taken and thrown away (finding A10).

    The four labeled lines are the wrapper, readable at a glance. The three
    facts under them really are the person's to correct. The whole entry,
    exactly as it will be written down, is the artifact, and it is held apart
    as data, because a drafted entry is a file somebody typed into and a
    heading in it must never read as an instruction (finding A9).
    """
    if draft.step != drafting.STEP_CHANGE:
        raise DraftError(draft.step, "not-a-context-change")
    git = runner_or_default(runner)
    address = owner_email
    if base_root and not address:
        address = base_reader.repo_email(base_root, git) or ""
    if not base_root or not address:
        # Finding V10 of the 2026-09-20 verification round. Without the base
        # there is no address and no free identifier, so what a preview could
        # show is a draft of the change rather than the change itself, and
        # approving it would write down something nobody had read.
        raise ReviewError(NEEDS_THE_BASE, code=CODE_NEEDS_THE_BASE)
    draft = review.stamp_entry(
        draft, None, address, entry_name=review.free_entry_id(base_root)
    )
    entry = formats.ChangeEntry.parse(draft.text)
    affected = ", ".join(names.document_name(path) for path in entry.affects)
    details = (
        (DETAIL_LABELS[0], str(entry.happened_on)),
        (DETAIL_LABELS[1], affected or "nothing yet"),
        (DETAIL_LABELS[2], str(entry.review_by)),
    )
    artifact = "\n".join(
        [ARTIFACT_OPEN, moment.fenced(draft.text.rstrip("\n")), ARTIFACT_CLOSE]
    ) + "\n"
    # Finding V9. The four lines and the three facts are read straight out of
    # a file somebody typed into, so all of them are held apart as data and
    # not only the whole change underneath them.
    four = four_lines_for(entry)
    summary = moment.fenced(
        "\n".join(
            [four, ""] + ["%s: %s" % (label, value) for label, value in details]
        )
    )
    return ProposedChange(
        entry, four, details, artifact, list(entry.affects), summary
    )


# --- Asking, once per document, whether it already says this -----------------


class Reconciliation(object):
    """Which documents the closing asks about, and which it leaves flagged."""

    __slots__ = ("ask_about", "left_flagged", "sentence")

    def __init__(self, ask_about, left_flagged, sentence=None):
        self.ask_about = list(ask_about)
        self.left_flagged = list(left_flagged)
        self.sentence = sentence

    def questions(self) -> List[str]:
        """The one question to ask about each document, in the order asked."""
        return [RECONCILE_ASK % names.document_name(path) for path in self.ask_about]

    def __repr__(self) -> str:
        return "Reconciliation(ask_about=%r, left_flagged=%d)" % (
            self.ask_about,
            len(self.left_flagged),
        )


def reconcile_plan(
    base_root: str,
    base_id: str,
    affects: Sequence[str],
    today=None,
    runner: Optional[GitRunner] = None,
) -> Reconciliation:
    """Work out which documents the closing asks about, one question each.

    Only the two documents a base needs are asked about here, because a change
    can name a dozen files once a base holds segments and the closing is the
    worst place in the product to ask a dozen questions (ruling 4 of
    `docs/plans/2026-09-19-001-acceptance-matrix.md`). Everything else the
    change affects is left flagged and said in one line, and the review picks
    it up.

    A document a context change is written down twice about is left flagged
    too and never asked about, because settling it would settle a change
    nobody has read either copy of.
    """
    git = runner_or_default(runner)
    day = today or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    ask_about: List[str] = []
    left_flagged: List[str] = []
    # The two required documents wherever they really are on this base, and
    # every path the change names followed to where that document lives.
    required = list(layout.required_paths(base_root))
    affects = layout.all_where_they_live(base_root, affects)
    for path in affects:
        if path not in required:
            left_flagged.append(path)
            continue
        if not os.path.isfile(os.path.join(base_root, path.replace("/", os.sep))):
            left_flagged.append(path)
            continue
        if confirm.refusal_while_written_twice(
            base_root, base_id, path, day, git=git
        ) is not None:
            left_flagged.append(path)
            continue
        if confirm.refusal_while_a_question_is_open(base_root, path) is not None:
            # A document still asking a question nobody answered cannot be
            # said to say anything yet, so it is left for the review, which
            # asks the question first (Unit 1.7b).
            left_flagged.append(path)
            continue
        ask_about.append(path)
    ask_about.sort(key=required.index)
    sentence = None
    if len(left_flagged) == 1:
        sentence = OTHERS_FLAGGED_ONE
    elif left_flagged:
        sentence = OTHERS_FLAGGED_MANY % len(left_flagged)
    return Reconciliation(ask_about, left_flagged, sentence)


class Reconciled(object):
    """What one answer to one reconciliation question led to."""

    __slots__ = ("path", "answered_yes", "sentence", "staging_path", "codes")

    def __init__(self, path, answered_yes, sentence, staging_path=None, codes=None):
        self.path = path
        self.answered_yes = bool(answered_yes)
        self.sentence = sentence
        self.staging_path = staging_path
        self.codes = list(codes or [])

    def __repr__(self) -> str:
        return "Reconciled(path=%r, answered_yes=%r)" % (self.path, self.answered_yes)


def entry_in_base(base_root: str, base_id: str, entry_id: str, day=None):
    """One context change the base holds, and the file it is written in."""
    if day is None:
        day = state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    for item in base_reader.ledger(base_root, base_id, day):
        if item.entry is not None and item.entry.id == entry_id:
            return item.entry, (item.path or "").rsplit("/", 1)[-1]
    return None, ""


def reconcile_yes(
    base_root: str,
    base_id: str,
    path: str,
    entry_id: str,
    now=None,
    runner: Optional[GitRunner] = None,
) -> Reconciled:
    """The person says this document already says what the change says."""
    if formats.name_has_a_space(path):
        return Reconciled(
            path,
            False,
            formats.NAME_WITH_A_SPACE,
            codes=[formats.CODE_NAME_WITH_A_SPACE],
        )
    result = confirm.against_change(
        base_root, base_id, path, entry_id, now=now, runner=runner
    )
    if result.status != confirm.STATUS_RECORDED:
        return Reconciled(path, False, result.reasons[0] if result.reasons else "",
                          codes=list(result.codes or []))
    return Reconciled(path, True, RECONCILE_RECORDED % names.document_name(path))


def reconcile_no(
    base_root: str,
    base_id: str,
    path: str,
    entry_id: str,
    now=None,
    runner: Optional[GitRunner] = None,
) -> Reconciled:
    """The document has not caught up, so it stays flagged and a fix is prepared.

    Setting a base up never edits a file it has already written, so the fix
    does not happen here. What happens here is that a change is prepared, and
    it waits for the person to approve it the way every other prepared change
    does.
    """
    day = now or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    entry, entry_file = entry_in_base(base_root, base_id, entry_id, day)
    document = names.document_name(path)
    if entry is None:
        return Reconciled(
            path, False, RECONCILE_NOT_PREPARED % document,
            codes=[stale_check.CODE_NO_ENTRY],
        )
    try:
        staging = stale_check.build_file_proposal(base_root, entry, entry_file, path)
    except (ValidationError, PathError) as failure:
        return Reconciled(
            path,
            False,
            RECONCILE_NOT_PREPARED % document,
            codes=[failure.code or stale_check.CODE_MISSING_FILE],
        )
    already = stale_check.already_prepared(
        base_root, base_id, staging, entry_id, [path]
    )
    if already is not None:
        return Reconciled(
            path,
            False,
            RECONCILE_FLAGGED % document,
            staging_path=stale_check.staging_path_for(base_root, staging.staging_id),
            codes=[already],
        )
    written = stale_check.save_staging(base_root, staging)
    return Reconciled(path, False, RECONCILE_FLAGGED % document, staging_path=written)


def skip_the_closing_question(
    base_root: str, base_id: str, today=None
) -> str:
    """Skip is a whole answer: nothing is written, and the reminder rests.

    Requirement P7. Nothing goes into the base and nothing goes into the log
    of questions the base asked, so the rate at which its questions are
    answered yes is untouched by this. What it does is put off the reminder
    that the record of context changes looks quiet, for exactly as long as
    this base lets a confirmation stand, which is the same window the review
    itself uses.
    """
    day = today or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    settings = base_reader.settings_of(base_reader.map_text(base_root))
    until = day + datetime.timedelta(
        days=int(settings.confirmation_threshold_days)
    )
    # The day that comes back is the day that was written down, which is
    # nearer than the day asked for on a base whose window is longer than the
    # longest quiet. Saying the day that was kept is finding N5.
    kept = state.set_ledger_behind_dismissed_until(base_id, until, today=day)
    return SKIP_RECORDED % kept.isoformat()


def _linked_folder_of(resolution) -> Optional[str]:
    """The folder this base belongs with, taken from the record, or nothing.

    It is read from the account's own record rather than from anything the
    caller passed in, so the closing can only ever name a folder that is
    actually written down as this base's.
    """
    entry = getattr(resolution, "entry", None)
    if isinstance(entry, dict) and isinstance(entry.get("content_root"), str):
        return entry["content_root"]
    base_id = getattr(resolution, "base_id", None)
    if not base_id:
        return None
    found = machine.find_joined_by_id(machine.load_machine_state_raw(), base_id)
    if isinstance(found, dict) and isinstance(found.get("content_root"), str):
        return found["content_root"]
    return None


def onboarding_note_path(base_root: str, day) -> str:
    """Where the note about what got in the way is written."""
    return os.path.join(
        constants.CORRECTIONS_DIR, "%s-onboarding-note.md" % day.isoformat()
    )


def write_onboarding_note(
    base_root: str,
    text: str,
    day,
    run_id: str,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
):
    """Write down, in the person's own words, what got in the way.

    It is screened the way a draft is, because it is the person's own typing
    and it is about to become part of the base. Nothing in it is exempt from
    that screen. What arrives here is raw typing rather than a document this
    plugin read back and understood, so a note that happens to open with three
    dashes is still just typing, and every line of it is read.

    Nothing here is allowed to end the closing. The person is at the last step
    of setting their base up, and losing the finding and the message that says
    where the base is, because saving one note did not work, would be a poor
    trade. When the note cannot be saved, that is said and the closing carries
    on without it.
    """
    git = runner_or_default(runner)
    body = str(text or "").strip()
    if not body:
        return None, []
    codes = review.screen(body, _address_for(base_root, email, git))
    if codes:
        return None, codes

    from . import formats

    try:
        review.ready_to_write(base_root, git)
    except GtmBaseError:
        return None, [NOTE_NOT_SAVED]

    relative = onboarding_note_path(base_root, day)
    document = formats.render_document(
        {"kind": ONBOARDING_NOTE_KIND, "date": day.isoformat(), "run_id": run_id},
        "## %s\n\n%s\n" % (ONBOARDING_NOTE_HEADING, body),
    )
    full = os.path.join(base_root, relative.replace("/", os.sep))
    folder = os.path.dirname(full)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(full, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(document)
    try:
        git.check(["add", "--", relative], cwd=base_root)
        # A second closing with the same words leaves nothing to save, because
        # the note already in the base says exactly this. Saving nothing is a
        # failure, so the step is skipped rather than attempted.
        nothing_staged = git.run(
            ["diff", "--cached", "--quiet", "--", relative], cwd=base_root
        )
        if not nothing_staged.ok:
            git.check(
                ["commit", "-q", "-m", ONBOARDING_NOTE_MESSAGE, "--", relative],
                cwd=base_root,
            )
    except GtmBaseError:
        return relative, [NOTE_NOT_SAVED]
    return relative, []


def close_run(
    base_root: str,
    run_id: str,
    got_in_the_way: Optional[str] = None,
    email: Optional[str] = None,
    plugin_root: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now=None,
) -> CloseResult:
    """End the first session: one honest finding, the note, and the way back.

    The finding is worked out here, every time, from the base as it stands. It
    is never kept from an earlier call, because the whole point of it is to be
    true about the base the person is looking at now, and a date they corrected
    a minute ago has to change it.
    """
    git = runner_or_default(runner)
    day = now or state.today()
    if isinstance(day, datetime.datetime):
        day = day.date()
    resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
    if not resolution.root or not resolution.base_id:
        raise GtmBaseError("this folder is not a base yet", "no-base")

    seat, _problems = state.load_seat(resolution.base_id)
    result = stale_check.run(
        resolution.root,
        resolution.base_id,
        runner=git,
        now=day,
        session_id=seat.get("session_id"),
        mode="first-run",
    )
    finding = stale_check.first_run_text(result)

    try:
        note_path, note_codes = write_onboarding_note(
            resolution.root, got_in_the_way, day, run_id, email=email, runner=git
        )
    except GtmBaseError:
        note_path, note_codes = None, [NOTE_NOT_SAVED]

    recorded = False
    try:
        machine.record_offer_answer("set-up")
        recorded = True
    except GtmBaseError:
        recorded = False

    # The import is kept past the closing, which is about to clear the run's
    # own folder, so a page not yet taken in can be finished by a later
    # session; one with nothing left to finish is let go (call 18).
    import_unfinished = False
    drafts_unfinished = False
    try:
        record = _carry(run_id, resolution.base_id)
        if record is not None:
            if record.unfinished():
                import_unfinished = True
                drafts_unfinished = bool(record.drafts_unfinished())
            else:
                segments.forget_import(resolution.base_id)
    except GtmBaseError:
        import_unfinished = segments.has_import(resolution.base_id)
        held = segments.load_import(resolution.base_id) if import_unfinished else None
        drafts_unfinished = bool(held is not None and held.drafts_unfinished())

    clear_scratch(run_id)
    # And anything an earlier run left behind that nothing else will ever take
    # away, because a run that stopped part way is never closed (finding L2).
    sweep_drafts_without_a_run()
    return CloseResult(
        finding,
        closing_message(
            resolution.root, plugin_root, content_root=_linked_folder_of(resolution)
        ),
        note_path,
        note_codes,
        recorded,
        import_unfinished,
        drafts_unfinished,
    )


# --- What this release does not do yet --------------------------------------


def refuse_mode(name: str, session_id: Optional[str] = None) -> str:
    """The one sentence GTM Base says when it is asked for one of these.

    A session that has already read the person's own documents is holding text
    nobody has vetted, so it says that first: nothing leaves this computer
    until the session ends. Otherwise it says plainly that the thing being
    asked for arrives with the next release.
    """
    if name not in NOT_IN_THIS_RELEASE:
        raise GtmBaseError("that is not something setup does", "unknown-mode")
    if marker.marker_matches_session(session_id):
        return constants.SOURCES_READ_REFUSAL
    return NOT_IN_THIS_RELEASE[name]
