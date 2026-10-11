"""Creating a document, and the five settings operations, each approved once.

Unit 4.2a of Plan 1, from the signed company-skills requirements of
2026-10-10. A prepared change edits a document that is already there; these
are the two other ways GTM Base writes into a base.

Creating (CS1, CS5) writes documents that are not there yet: a context
document, a standard, the source map, or a lesson at `learning/lessons`. It is
absent-only, the creator's address is stamped on each `owner:` line before
anything is shown, the creator approves it, and it is written in one step that
leaves nothing behind when any part fails.

The settings operations (CS15 to CS17) each change one line of one settings
block and nothing else: a document's `owner:` line and its `business:` line
(that document's authority set), the map's `owner:` line (the current base
owner only, which is how the role passes), the map's `administrators:` line
(the base owner only), and the map's `businesses:` line (the base owner or an
administrator). No other change to a settings block, and no other change to
the map, can be made through GTM Base.

Both go the same way. Preparing reads what is there, works out every byte to
be written, screens it, and keeps it on this seat with a value bound to what
was shown, and the whole of it is the artifact the person reads. Approving is
an approval, so it goes through Claude Code's own question first (Unit 1.7e,
`approval.require`), then the authority rule, then a check that nothing moved
since the showing and that nothing else in the base is unsaved, and only then
writes, saves, and records who approved it, in which role, the hash of each
file's exact bytes, and the reason given (CS9). A prepared operation is used
once.
"""

from __future__ import annotations

import datetime
import os
import secrets
from typing import Dict, List, Optional, Sequence, Tuple

from . import (
    approval,
    authority,
    base_reader,
    businesses,
    compose_proposal,
    constants,
    docpaths,
    formats,
    ids,
    paths,
    review,
    scan,
    state,
    unsaved,
    validate,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import (
    atomic_write_json,
    atomic_write_text,
    ensure_dir,
    read_bytes,
    read_json,
    read_text_exactly,
    remove,
)
from .gitcmd import GitRunner, runner_or_default

# The five settings operations.
SET_OWNER = "owner"
SET_BUSINESS = "business"
SET_MAP_OWNER = "map-owner"
SET_ADMINISTRATORS = "administrators"
SET_BUSINESSES = "businesses"
SETTINGS_OPERATIONS = (
    SET_OWNER,
    SET_BUSINESS,
    SET_MAP_OWNER,
    SET_ADMINISTRATORS,
    SET_BUSINESSES,
)
_DOCUMENT_OPERATIONS = (SET_OWNER, SET_BUSINESS)
# The line each one changes.
_KEY = {
    SET_OWNER: "owner",
    SET_BUSINESS: businesses.BUSINESS_FIELD,
    SET_MAP_OWNER: authority.OWNER_SETTING,
    SET_ADMINISTRATORS: authority.ADMINISTRATORS_SETTING,
    SET_BUSINESSES: businesses.BUSINESSES_SETTING,
}
KIND_CREATE = "create"
KIND_SETTING = "setting"

# The library write an approval of either kind performs, which the ticket
# Claude Code's question hands over has to open (Unit 1.7e).
WRITE = "operations.approve"

# Where a prepared operation waits on this seat.
FOLDER = "prepared-operations"
_MODE = 0o644

# Why something was refused. A code is never said to a person.
CODE_NOT_A_DOCUMENT = "not-a-document-here"
CODE_ALREADY_THERE = "already-there"
CODE_SCREENED = "screened"
CODE_NO_ADDRESS = "no-address"
CODE_BAD_VALUE = "bad-value"
CODE_NOT_AN_OPERATION = "not-an-operation"
CODE_NOT_WAITING = "not-waiting"
CODE_MOVED = "moved"
CODE_NOT_ALLOWED = "not-allowed"
CODE_UNSAVED = "unsaved-work"
CODE_NOT_ON_MAIN = "not-on-the-shared-line"
CODE_COULD_NOT_SAVE = "could-not-save"

# The sentences a person reads.
NOT_A_DOCUMENT = (
    "That is not a place in your base a document can be written to, so nothing "
    "was prepared."
)
ALREADY_THERE = (
    "Your base already has a document there, so nothing was prepared; a change "
    "to it is prepared the usual way."
)
SCREENED = (
    "What would be written holds something that is never kept in a base, such "
    "as a contact detail or a key, so nothing was prepared."
)
NO_ADDRESS = (
    "GTM Base does not know which address this base is yours under, so it "
    "cannot record who approved this."
)
BAD_VALUE = (
    "That is not a value this setting can hold, so nothing was prepared."
)
NOT_AN_OPERATION = (
    "GTM Base can change only a document's owner or business, or the map's "
    "owner, administrators or businesses, so nothing was prepared."
)
NOT_WAITING = (
    "Nothing prepared is waiting under that name, so nothing was written."
)
MOVED = (
    "What was shown is no longer what would be written, so nothing was "
    "written. Ask for it to be prepared and shown again."
)
NOT_ALLOWED = (
    "This base is set up under an address that may not approve this change, "
    "so nothing was written."
)
UNSAVED = (
    "There is unsaved work in your base, so nothing was written. Save or put "
    "it aside first."
)
NOT_ON_MAIN = (
    "Your base is not on the line of work the team shares, so nothing was "
    "written."
)
COULD_NOT_SAVE = (
    "GTM Base could not save this, so it put back everything it had written "
    "and nothing changed."
)
DONE_CREATED = "Written and saved, and the approval is recorded."
DONE_SETTING = "Changed and saved, and the approval is recorded with the reason."


class Refused(GtmBaseError):
    """Preparing was refused; the message is the sentence a person reads."""


class Prepared(object):
    """One operation waiting for its yes: its name, the value it is bound to, and the whole artifact."""

    __slots__ = ("prepared_id", "shown", "artifact")

    def __init__(self, prepared_id: str, shown: str, artifact: str):
        self.prepared_id = prepared_id
        self.shown = shown
        self.artifact = artifact


class Done(object):
    """How an approval ended."""

    __slots__ = ("done", "code", "sentence", "paths", "saved_work")

    def __init__(self, done: bool, code: Optional[str], sentence: str, paths=None, saved_work=None):
        self.done = done
        self.code = code
        self.sentence = sentence
        self.paths = list(paths or [])
        self.saved_work = saved_work

    def __repr__(self) -> str:
        return "Done(%r, %r)" % (self.done, self.code)


def _refuse(code: str, sentence: str) -> Refused:
    return Refused(sentence, code=code)


# --- Keeping what was prepared ------------------------------------------------------


def _folder(base_id: str) -> str:
    return ensure_dir(os.path.join(paths.seat_dir(base_id), FOLDER))


def _kept_path(base_id: str, prepared_id: str) -> Optional[str]:
    try:
        validate.check_staging_id(prepared_id)
    except ValidationError:
        return None
    return os.path.join(_folder(base_id), prepared_id + ".json")


def _shown_value(kept: dict) -> str:
    """The value a yes is bound to: every byte to be written and everything it rests on."""
    parts = [kept["kind"], kept.get("operation") or "", kept["reason"], kept["by"]]
    for change in kept["changes"]:
        parts.extend([change["path"], change["before"] or "-", change["after"]])
    return ids.content_hash("\x1f".join(parts))


def _keep(base_id: str, kept: dict) -> Prepared:
    prepared_id = "stg-" + secrets.token_hex(8)
    kept["prepared_id"] = prepared_id
    atomic_write_json(
        os.path.join(_folder(base_id), prepared_id + ".json"), kept, inside=_folder(base_id)
    )
    return Prepared(prepared_id, _shown_value(kept), _artifact(kept))


def _artifact(kept: dict) -> str:
    """The whole of what would be written, each file under its path, and the reason."""
    pieces = []
    for change in kept["changes"]:
        pieces.append("[[file: %s]]\n%s[[end file]]" % (change["path"], change["after"]))
    pieces.append("[[reason]]\n%s\n[[end reason]]" % kept["reason"])
    return "\n\n".join(pieces)


# --- Reading what is there ---------------------------------------------------------


def _address(base_root: str, git: GitRunner) -> str:
    address = base_reader.repo_email(base_root, git)
    if not address:
        raise _refuse(CODE_NO_ADDRESS, NO_ADDRESS)
    return address


def _in_head(base_root: str, relative: str, git: GitRunner) -> bool:
    return git.run(["cat-file", "-e", "HEAD:" + relative], cwd=base_root).ok


def _screen_reason(base_root: str, reason: str) -> None:
    allowlist, _code = scan.load_allowlist(base_root)
    if scan.scan_text(reason, allowlist, "the reason"):
        raise _refuse(CODE_SCREENED, SCREENED)


def _stamped(text: str, address: str) -> str:
    """A new document with its creator on its owner line, everything else as written (CS1)."""
    try:
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    fields["owner"] = address
    return formats.render_document(fields, body)


# --- Creating ----------------------------------------------------------------------


def prepare_creation(
    base_root: str,
    base_id: str,
    files: Sequence[Tuple[str, str]],
    reason: str,
    runner: Optional[GitRunner] = None,
) -> Prepared:
    """Prepare new documents to be written together, stamped with their creator.

    Every path has to be a place the create operation may write, nothing may
    be there yet, and every file has to pass the screens a prepared change
    gets, with the creator's own address on the owner line let through as it
    always is.
    """
    git = runner_or_default(runner)
    address = _address(base_root, git)
    if not files:
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    seen = set()
    changes = []
    for relative, text in files:
        try:
            found = docpaths.check(base_root, relative)
        except PathError:
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        if not docpaths.may(found, docpaths.OP_CREATE) or found.path in seen:
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        seen.add(found.path)
        full = os.path.join(base_root, found.path.replace("/", os.sep))
        if os.path.lexists(full) or _in_head(base_root, found.path, git):
            raise _refuse(CODE_ALREADY_THERE, ALREADY_THERE)
        stamped = _stamped(text, address)
        if review.screen(
            stamped,
            owner_email=address,
            frontmatter_lines=review.frontmatter_line_numbers(stamped),
        ):
            raise _refuse(CODE_SCREENED, SCREENED)
        changes.append({"path": found.path, "before": None, "after": stamped})
    _screen_reason(base_root, reason)
    return _keep(
        base_id,
        {"kind": KIND_CREATE, "operation": None, "reason": reason, "by": address, "changes": changes},
    )


# --- The settings operations ---------------------------------------------------------


def _list_value(value) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [part.strip() for part in text.split(",")] if text.strip() else []


def _rendered(operation: str, value, base_root: str, relative: Optional[str], git) -> str:
    """The new value as its settings line writes it, or a refusal when it is not one."""
    if any(
        isinstance(piece, str) and ("\n" in piece or "\r" in piece)
        for piece in (value if isinstance(value, (list, tuple)) else [value])
    ):
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)
    try:
        if operation in (SET_OWNER, SET_MAP_OWNER):
            addresses = validate.validate_owner(_list_value(value))
            if operation == SET_MAP_OWNER and len(addresses) != 1:
                raise ValidationError("the base has one owner", code=CODE_BAD_VALUE)
            return addresses[0] if len(addresses) == 1 else "[%s]" % ", ".join(addresses)
        if operation == SET_ADMINISTRATORS:
            listed = _list_value(value)
            addresses = validate.validate_owner(listed) if listed else []
            if len(set(addresses)) != len(addresses):
                raise ValidationError("an address listed twice", code=CODE_BAD_VALUE)
            return "[%s]" % ", ".join(addresses)
        if operation == SET_BUSINESSES:
            listed = businesses.businesses_from(_list_value(value))
            return ", ".join(
                one.slug if not one.name else "%s (%s)" % (one.slug, one.name)
                for one in listed
            )
        if operation == SET_BUSINESS:
            said = str(value or "").strip()
            if said == businesses.WHOLE_COMPANY:
                return said
            map_text = _head_or_disk(base_root, constants.MAP_PATH, git)
            listed = [one.slug for one in businesses.read_map_businesses(map_text)]
            folder = businesses.folder_of(relative or "")
            if said not in listed or (
                folder is not None
                and folder not in businesses.RESERVED_SLUGS
                and folder != said
            ):
                raise ValidationError("not a business the map lists", code=CODE_BAD_VALUE)
            return said
    except ValidationError:
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)
    raise _refuse(CODE_NOT_AN_OPERATION, NOT_AN_OPERATION)


def _head_or_disk(base_root: str, relative: str, git: GitRunner) -> str:
    shown = git.run(["show", "HEAD:" + relative], cwd=base_root)
    if shown.ok:
        return shown.stdout
    return read_text_exactly(os.path.join(base_root, relative.replace("/", os.sep))) or ""


def _with_setting(text: str, key: str, rendered: str) -> str:
    """The same file with one settings line set, every other byte as it was.

    A line already there, with any list lines under it, is replaced by one
    line. A setting not there yet goes in right after the owner line, or last
    in the block when there is none.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != formats.FRONTMATTER_FENCE:
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == formats.FRONTMATTER_FENCE:
            end = index
            break
    if end is None:
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    new_line = "%s: %s" % (key, rendered) if rendered != "" else "%s:" % key
    at = None
    stop = None
    for index in range(1, end):
        name = lines[index].partition(":")[0].strip()
        if lines[index] and not lines[index].startswith((" ", "-")) and name == key:
            at = index
            stop = index + 1
            while stop < end and lines[stop].lstrip(" ").startswith("-"):
                stop += 1
            break
    if at is not None:
        lines[at:stop] = [new_line]
    else:
        owner = None
        for index in range(1, end):
            if lines[index].partition(":")[0].strip() == "owner":
                owner = index
                while owner + 1 < end and lines[owner + 1].lstrip(" ").startswith("-"):
                    owner += 1
                break
        place = owner + 1 if owner is not None else end
        lines.insert(place, new_line)
    return "\n".join(lines)


def _only_that_changed(before: str, after: str, key: str) -> None:
    """Refuse a new file whose settings or body differ in anything but one line."""
    try:
        old_block, old_body = formats.split_document(before)
        new_block, new_body = formats.split_document(after)
        old = formats.parse_frontmatter(old_block)
        new = formats.parse_frontmatter(new_block)
    except (ValidationError, PathError):
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)
    old.pop(key, None)
    new.pop(key, None)
    if old != new or old_body != new_body:
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)


def prepare_setting(
    base_root: str,
    base_id: str,
    operation: str,
    reason: str,
    path: Optional[str] = None,
    value=None,
    runner: Optional[GitRunner] = None,
) -> Prepared:
    """Prepare one settings line to change, the whole new file shown first."""
    git = runner_or_default(runner)
    if operation not in SETTINGS_OPERATIONS:
        raise _refuse(CODE_NOT_AN_OPERATION, NOT_AN_OPERATION)
    if operation in _DOCUMENT_OPERATIONS:
        try:
            found = docpaths.check(base_root, path)
        except PathError:
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        if not docpaths.may(found, docpaths.OP_SETTINGS):
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        relative = found.path
    else:
        if path not in (None, constants.MAP_PATH):
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        relative = constants.MAP_PATH
    address = _address(base_root, git)
    full = os.path.join(base_root, relative.replace("/", os.sep))
    if os.path.islink(full):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    before = read_text_exactly(full)
    if before is None or not _in_head(base_root, relative, git):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    key = _KEY[operation]
    after = _with_setting(before, key, _rendered(operation, value, base_root, relative, git))
    _only_that_changed(before, after, key)
    _screen_reason(base_root, reason)
    return _keep(
        base_id,
        {
            "kind": KIND_SETTING,
            "operation": operation,
            "reason": reason,
            "by": address,
            "changes": [
                {"path": relative, "before": ids.exact_hash(before), "after": after}
            ],
        },
    )


# --- Approving --------------------------------------------------------------------


def _role_for(kept: dict, base_root: str, address: str, git: GitRunner) -> Optional[str]:
    """The role that lets this address approve this operation, or None."""
    if kept["kind"] == KIND_CREATE:
        # The creator approves what they create and owns it (CS1, CS5). Only
        # the address stamped on it at the showing may.
        return authority.ROLE_OWNER if address == kept["by"] else None
    operation = kept["operation"]
    relative = kept["changes"][0]["path"]
    if operation in _DOCUMENT_OPERATIONS:
        return authority.at(base_root, relative, runner=git).role_of(address)
    roles = authority.roles_from_map(_head_or_disk(base_root, constants.MAP_PATH, git))
    if address == roles.base_owner:
        return authority.ROLE_BASE_OWNER
    if operation == SET_BUSINESSES and address in roles.administrators:
        return authority.ROLE_ADMINISTRATOR
    return None


def _unmoved(base_root: str, change: dict, git: GitRunner) -> bool:
    full = os.path.join(base_root, change["path"].replace("/", os.sep))
    if change["before"] is None:
        return not os.path.lexists(full) and not _in_head(base_root, change["path"], git)
    text = read_text_exactly(full)
    if text is None or ids.exact_hash(text) != change["before"]:
        return False
    return _head_or_disk(base_root, change["path"], git) == text


def _record(kept: dict, address: str, role: str, today: datetime.date) -> Tuple[str, str]:
    """The record of this approval, and where it goes in the record of corrections."""
    staging_id = kept["prepared_id"]
    touched = [change["path"] for change in kept["changes"]]
    if kept["kind"] == KIND_CREATE:
        what = "Created %s." % ", ".join(touched)
    else:
        what = "Set the %s line of %s." % (_KEY[kept["operation"]], touched[0])
    record = formats.CorrectionsFile(
        kind="correction",
        date=today.isoformat(),
        staging_id=staging_id,
        intake_path="none",
        mode="none",
        third_party=False,
        content_hash=ids.content_hash("".join(change["after"] for change in kept["changes"])),
        correction_class="other",
        marker=validate.marker_line(staging_id),
        touched_paths=touched,
        what_changed=what,
        why=kept["reason"],
        approved_roles={path: role for path in touched},
        approved_hashes={
            change["path"]: authority.bytes_hash(change["after"].encode("utf-8"))
            for change in kept["changes"]
        },
    ).validate()
    where = "%s/%s-%s.md" % (constants.CORRECTIONS_DIR, today.isoformat(), staging_id)
    return where, record.render()


def _creators_yes(base_root, kept, address, role, today, moment):
    """The creator's confirmation of each new document a confirmation may name.

    Creating a document is its owner saying it is right, so it joins the
    review's clock from the day it is created, recorded with who said so and
    the role (CS9). A lesson is never confirmed, so it gets none.
    """
    from . import confirm

    lines = []
    for change in kept["changes"]:
        if not docpaths.may(docpaths.classify(change["path"]), docpaths.OP_CONFIRM):
            continue
        line = formats.ConfirmationLine(
            date=today.isoformat(),
            time=moment.strftime("%H:%M:%SZ"),
            file=change["path"],
            trigger="threshold",
            role=role,
        )
        line.validate()
        target = confirm.confirmations_path_for(change["path"])
        existing = read_text_exactly(os.path.join(base_root, target.replace("/", os.sep)))
        text = (existing if existing else confirm.FILE_HEADER) + line.render() + "\n"
        lines.append((target, text))
    return lines


def _save(base_root: str, written: List[str], subject: str, git: GitRunner) -> str:
    git.check(["add", "--"] + written, cwd=base_root)
    name, address, _codes = compose_proposal._author(base_root, git)
    git.check(
        ["-c", "user.name=%s" % name, "-c", "user.email=%s" % address, "commit", "-q", "-m", subject],
        cwd=base_root,
    )
    return git.run(["rev-parse", "HEAD"], cwd=base_root).out()


def _put_back(base_root: str, kept_bytes: Dict[str, Optional[bytes]], git: GitRunner) -> None:
    """Undo this run's writes: new files taken away, changed ones put back, the index too."""
    for relative, data in kept_bytes.items():
        full = os.path.join(base_root, relative.replace("/", os.sep))
        if data is None:
            remove(full)
        else:
            with open(full, "wb") as handle:
                handle.write(data)
    if kept_bytes:
        git.run(["reset", "-q", "--"] + list(kept_bytes), cwd=base_root)


def approve(
    base_root: str,
    base_id: str,
    prepared_id: str,
    shown: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    kind: Optional[str] = None,
) -> Done:
    """Write one prepared operation, if this address may and nothing has moved.

    `kind` is what the command that approves it says it approves, a creation
    or a setting, because Claude Code's question said that and nothing else.
    A prepared operation of the other kind is not written.
    """
    # Only a command the person allowed through Claude Code's own question
    # writes an approval (Unit 1.7e, Brandon's call 57).
    approval.require(WRITE)
    git = runner_or_default(runner)
    today = now.date() if isinstance(now, datetime.datetime) else (now or state.today())

    where = _kept_path(base_id, prepared_id)
    kept = read_json(where) if where else None
    if not isinstance(kept, dict) or kept.get("prepared_id") != prepared_id:
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)
    if kind is not None and kept.get("kind") != kind:
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)
    if not shown or shown != _shown_value(kept):
        return Done(False, CODE_MOVED, MOVED)
    try:
        address = _address(base_root, git)
    except Refused as refusal:
        return Done(False, refusal.code, str(refusal))
    role = _role_for(kept, base_root, address, git)
    if role is None:
        return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
    on_main, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_main:
        return Done(False, CODE_NOT_ON_MAIN, NOT_ON_MAIN)
    if not unsaved.look(base_root, git).clean:
        return Done(False, CODE_UNSAVED, UNSAVED)
    if not all(_unmoved(base_root, change, git) for change in kept["changes"]):
        return Done(False, CODE_MOVED, MOVED)

    record_path, record_text = _record(kept, address, role, today)
    writes = [(change["path"], change["after"]) for change in kept["changes"]]
    writes.append((record_path, record_text))
    if kept["kind"] == KIND_CREATE:
        moment = now if isinstance(now, datetime.datetime) else state.now_utc()
        writes.extend(_creators_yes(base_root, kept, address, role, today, moment))
    targets = [relative for relative, _text in writes]
    if os.path.lexists(os.path.join(base_root, record_path.replace("/", os.sep))):
        return Done(False, CODE_MOVED, MOVED)
    kept_bytes: Dict[str, Optional[bytes]] = {}
    written: List[str] = []
    try:
        for relative, text in writes:
            full = os.path.join(base_root, relative.replace("/", os.sep))
            kept_bytes[relative] = read_bytes(full) if os.path.lexists(full) else None
            atomic_write_text(full, text, mode=_MODE, inside=base_root)
            written.append(relative)
        saved = _save(
            base_root,
            written,
            "GTM Base: %s %s" % ("create" if kept["kind"] == KIND_CREATE else "set", prepared_id),
            git,
        )
    except (GtmBaseError, OSError):
        _put_back(base_root, kept_bytes, git)
        return Done(False, CODE_COULD_NOT_SAVE, COULD_NOT_SAVE)
    remove(where)
    return Done(
        True,
        None,
        DONE_CREATED if kept["kind"] == KIND_CREATE else DONE_SETTING,
        paths=targets,
        saved_work=saved,
    )
