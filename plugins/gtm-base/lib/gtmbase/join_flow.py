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
import os
import shutil
from typing import List, Optional, Sequence

from . import (
    constants,
    create_base,
    drafting,
    extract,
    ids,
    location,
    machine,
    marker,
    paths,
    review,
    sources as sources_module,
    stale_check,
    state,
)
from .errors import (
    ConsentError,
    DraftError,
    GtmBaseError,
    ReviewError,
    SourceRejected,
)
from .fsutil import atomic_write_json, atomic_write_text, ensure_dir, read_json, read_text
from .gitcmd import GitRunner, runner_or_default

# What the run folder holds.
CONSENT_FILE = "consent.json"
LISTING_FILE = "listing.json"
PASTES_DIR = "pastes"

# Why a yes could not be taken.
CODE_NO_LISTING = "no-listing"
CODE_LISTING_CHANGED = "listing-changed"
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


class Assembled(object):
    """One request, written down, with what went into it and what did not."""

    __slots__ = ("path", "step", "included_labels", "dropped_labels", "codes", "left_out")

    def __init__(
        self, path, step, included_labels, dropped_labels, codes=None, left_out=None
    ):
        self.path = path
        self.step = step
        self.included_labels = list(included_labels)
        self.dropped_labels = list(dropped_labels)
        self.codes = list(codes or [])
        # Pairs of the label and the reason, one for each source that could not
        # be used at all, as against the ones dropped for length.
        self.left_out = list(left_out or [])

    def __repr__(self) -> str:
        return "Assembled(step=%r, included=%d)" % (
            self.step,
            len(self.included_labels),
        )


class Reviewed(object):
    """What the checks made of one draft before anybody was asked about it."""

    __slots__ = ("step", "ready", "codes", "draft")

    def __init__(self, step, ready, codes=None, draft=None):
        self.step = step
        self.ready = bool(ready)
        self.codes = list(codes or [])
        self.draft = draft

    def __repr__(self) -> str:
        return "Reviewed(step=%r, ready=%r, codes=%r)" % (
            self.step,
            self.ready,
            self.codes,
        )


class CloseResult(object):
    """Everything the last step of setting a base up produced."""

    __slots__ = ("finding", "note_path", "note_codes", "closing", "answer_recorded")

    def __init__(
        self,
        finding,
        closing,
        note_path=None,
        note_codes=None,
        answer_recorded=False,
    ):
        self.finding = finding
        self.closing = closing
        self.note_path = note_path
        self.note_codes = list(note_codes or [])
        self.answer_recorded = bool(answer_recorded)

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
    if not os.path.isdir(folder):
        return False
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
):
    """Where this person's base would go, and the sentence that says so."""
    return location.propose_target(
        cwd or os.getcwd(),
        company,
        named_content_folder=content_folder,
        runner=runner,
        confirmed_home=confirmed_home,
    )


# --- What would be read ------------------------------------------------------


def list_sources(folder: str, run_id: Optional[str] = None, today=None):
    """Everything in a folder that could be read, and everything left out.

    When a run is named, the list is written down in that run's own folder
    along with one value standing for the whole of it. The person says yes to a
    list they were shown, and the yes is taken against that written down list
    rather than against whatever a second walk of the folder would find, so a
    file that appeared in the meantime cannot ride in on a yes given about a
    list it was never on.
    """
    listing = sources_module.list_folder(folder, today=today)
    if run_id:
        atomic_write_json(
            os.path.join(scratch_dir(run_id), LISTING_FILE),
            {
                "root": listing.root,
                "digest": sources_module.listing_digest(listing),
                "paths": sorted(
                    os.path.realpath(entry.path) for entry in listing.readable
                ),
            },
            inside=paths.seat_home(),
        )
    return listing


def load_listing(run_id: str):
    """The list this run showed the person, exactly as it was shown."""
    payload = read_json(os.path.join(scratch_dir(run_id), LISTING_FILE))
    if not isinstance(payload, dict):
        return None
    wanted = payload.get("paths")
    digest = payload.get("digest")
    if not isinstance(wanted, list) or not isinstance(digest, str) or not digest:
        return None
    return {
        "root": str(payload.get("root") or ""),
        "digest": digest,
        "paths": [str(item) for item in wanted],
    }


def freeze_sources(folder: str, session_id: str, run_id: str, today=None):
    """Take the person's yes: fix the set of files, and hold nothing back.

    The yes is taken against the list this run wrote down when it showed it. To
    make sure that list is still true, the folder is walked once more and the
    two are compared. When they differ the yes is refused with the code saying
    so, and the skill shows the new list and asks again, because a person can
    only agree to a list they have actually seen.
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
    consent = sources_module.ConsentList.freeze_paths(shown["paths"], session_id)
    atomic_write_json(
        os.path.join(scratch_dir(run_id), CONSENT_FILE),
        {
            "root": shown["root"],
            "session_id": consent.session_id,
            "frozen_at": consent.frozen_at,
            "paths": list(consent.paths),
        },
        inside=paths.seat_home(),
    )
    return consent


def load_consent(run_id: str):
    """The list of files this run was allowed to read, as it was frozen."""
    payload = read_json(os.path.join(scratch_dir(run_id), CONSENT_FILE))
    if not isinstance(payload, dict):
        return None
    wanted = payload.get("paths")
    if not isinstance(wanted, list):
        return None
    return sources_module.Consent(
        [str(item) for item in wanted],
        str(payload.get("session_id") or ""),
        str(payload.get("frozen_at") or ""),
    )


class SourcesRead(object):
    """The text this run may draft from, and what had to be left out of it."""

    __slots__ = ("sources", "left_out")

    def __init__(self, sources, left_out=None):
        self.sources = list(sources)
        # Pairs of the label and the short reason, one for each source that
        # could not be used.
        self.left_out = list(left_out or [])

    def __repr__(self) -> str:
        return "SourcesRead(sources=%d, left_out=%d)" % (
            len(self.sources),
            len(self.left_out),
        )


def read_sources(
    run_id: str, paste_files: Sequence[str] = (), today=None
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
    of their own documents was left out and why.
    """
    consent = load_consent(run_id)
    found: List["sources_module.Source"] = []
    left_out: List[tuple] = []
    if consent is not None:
        for path in consent.paths:
            real = sources_module.read_allowed(consent, path)
            label = _label_for(real)
            kind = constants.SOURCE_READABLE_SUFFIXES.get(
                os.path.splitext(real)[1].lower()
            )
            if kind is None:
                left_out.append((label, sources_module.CODE_UNSUPPORTED))
                continue
            try:
                text, _notes = extract.extract(real, kind)
                when = sources_module.date_for_file(real, today=today)
                found.append(
                    sources_module.make_source(
                        label,
                        text,
                        kind,
                        date=when.date,
                        path=real,
                        clamped=when.clamped,
                    )
                )
            except SourceRejected as refusal:
                left_out.append((label, refusal.code or "source-rejected"))
    for path in paste_files or ():
        text = read_text(path)
        if text is None:
            raise ConsentError(
                "that pasted text is not where it was said to be",
                code="no-paste-file",
            )
        label = _label_for(path)
        try:
            found.append(sources_module.paste_source(label, text))
        except SourceRejected as refusal:
            left_out.append((label, refusal.code or "source-rejected"))
    return SourcesRead(found, left_out)


def _label_for(path: str) -> str:
    name = os.path.basename(path)
    keep = [
        character if (character.isalnum() or character in " ._-") else "-"
        for character in name
    ]
    label = "".join(keep).strip()[:80]
    return label or "a source"


# --- Building the request for one step ---------------------------------------


def assemble_step(
    step: str,
    run_id: str,
    company: str,
    owner_email: str,
    paste_files: Sequence[str] = (),
    today=None,
    plugin_root: Optional[str] = None,
) -> Assembled:
    """Build the request for one step and write it into the run's own folder.

    A refusal carries the labels of the sources that could not be used, so the
    person still hears which of their own documents was left out and why even
    when nothing was left to draft from.
    """
    day = today or state.today()
    read = read_sources(run_id, paste_files, today=day)
    try:
        assembly = drafting.assemble(
            step,
            read.sources,
            company,
            day.isoformat() if hasattr(day, "isoformat") else str(day),
            owner_email,
            plugin_root=plugin_root,
        )
    except DraftError as refusal:
        refusal.left_out = list(read.left_out)
        raise
    path = os.path.join(scratch_dir(run_id), "%s-prompt.md" % step)
    atomic_write_text(path, assembly.text, inside=paths.seat_home())
    return Assembled(
        path,
        step,
        assembly.included_labels,
        assembly.dropped_labels,
        assembly.codes,
        read.left_out,
    )


def draft_path(run_id: str, step: str) -> str:
    """Where the assistant writes the draft for one step."""
    return os.path.join(scratch_dir(run_id), "%s-draft.md" % step)


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
) -> Reviewed:
    """Read one draft back and say whether it may be shown to the person.

    What comes back is either the word that it is ready or the classes of thing
    that were found in it, never a line of the draft itself.
    """
    git = runner_or_default(runner)
    text = read_text(draft_file)
    if text is None:
        return Reviewed(step, False, ["no-draft-file"])
    draft = _parse_draft(step, text)
    codes = review.screen(draft, _address_for(base_root, email, git))
    return Reviewed(step, not codes, codes, draft)


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
):
    """Write one approved draft down, building the base when it is the first.

    The first approved file is what makes the base exist, so this call is where
    a folder appears on the person's computer for the first time. Every file
    after it is written into the base that is already there.

    What gets written into is the folder the resolver settled on, never the one
    the caller happened to name. A person working in the company folder names
    that folder, and the base is the `gtm-base` folder inside it.
    """
    git = runner_or_default(runner)
    reviewed = review_step(step, draft_file, base_root=base_root, email=email, runner=git)
    if not reviewed.ready:
        raise ReviewError(review.CODE_SCREENED, codes=reviewed.codes)

    first_file = not base_root
    where = parent
    if first_file and not where:
        if not company:
            raise ReviewError("no-parent", code="no-parent")
        where = propose_location(
            company, cwd=cwd, confirmed_home=confirmed_home, runner=git
        ).parent
    base_id = None
    root = base_root
    if not first_file:
        resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
        base_id = resolution.base_id
        root = resolution.root or base_root

    return review.approve(
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
    )


def skip_step(
    step: str,
    base_root: str,
    email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
):
    """Write the file a skipped step leaves behind, saying it was skipped.

    As with an approved file, what gets written into is the folder the resolver
    settled on rather than the one the caller named.
    """
    git = runner_or_default(runner)
    resolution = paths.resolve_base(base_root, machine.load_machine_state(), git)
    return review.skip(
        step,
        resolution.root or base_root,
        base_id=resolution.base_id,
        owner_email=email,
        runner=git,
        now=now,
    )


# --- The closing -------------------------------------------------------------


def closing_message(base_root: str, plugin_root: Optional[str] = None) -> str:
    """The message that ends a first session, with the folder filled in."""
    root = plugin_root or drafting.plugin_root_default()
    text = read_text(os.path.join(root, CLOSING_RULES))
    if text is None:
        raise GtmBaseError("the closing message is missing", "no-closing-rules")
    _before, marker_line, after = text.partition(CLOSING_MARKER)
    if not marker_line:
        raise GtmBaseError("the closing message is missing", "no-closing-rules")
    return after.strip("\n").replace("{{folder}}", base_root) + "\n"


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

    clear_scratch(run_id)
    return CloseResult(
        finding,
        closing_message(resolution.root, plugin_root),
        note_path,
        note_codes,
        recorded,
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
