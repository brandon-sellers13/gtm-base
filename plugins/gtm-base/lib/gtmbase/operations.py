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
import json
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
    layout,
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
    parts = [
        kept["kind"],
        kept.get("operation") or "",
        json.dumps(kept.get("value"), sort_keys=True),
        str(kept.get("path") or ""),
        kept["reason"],
        kept["by"],
        str(kept.get("made") or ""),
    ]
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
    """The whole of what would be written, each file under its path, and the reason.

    A settings change opens with the one line as it is and as it would be, so
    a change of who owns the base is not one line lost in a whole map.
    """
    pieces = []
    for change in kept["changes"]:
        if "line_before" in change:
            pieces.append(
                "[[the line now]]\n%s\n[[the line after]]\n%s\n[[end line]]"
                % (change["line_before"], change["line_after"])
            )
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


def _screened(base_root: str, relative: str, text: str, address: str) -> None:
    """Refuse a document holding what a prepared change may never carry.

    The screens a prepared change gets, with the owner's own address let
    through on its settings lines as it always is, and for the source map its
    own check for credentials, which the check before a send and the start of
    a session both hold it to.
    """
    if review.screen(
        text, owner_email=address, frontmatter_lines=review.frontmatter_line_numbers(text)
    ):
        raise _refuse(CODE_SCREENED, SCREENED)
    if relative == constants.STACK_PATH:
        allowlist, _code = scan.load_allowlist(base_root)
        if scan.scan_source_map(text, allowlist):
            raise _refuse(CODE_SCREENED, SCREENED)


def _creatable(base_root: str, relative: str, git: GitRunner) -> str:
    """The path of a document that may be created here and is not here yet, in either layout.

    A path only the older layout uses is never written, and a path whose other
    layout's counterpart is already there is refused too, because the new
    file would stand in for a document somebody else owns wherever the two
    layouts are read as one.
    """
    try:
        found = docpaths.check(base_root, relative)
    except PathError:
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    if not docpaths.may(found, docpaths.OP_CREATE) or layout.is_older_path(found.path):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    for candidate in [found.path] + [layout.counterpart(found.path) or ""]:
        if not candidate:
            continue
        full = os.path.join(base_root, candidate.replace("/", os.sep))
        if os.path.lexists(full) or _in_head(base_root, candidate, git):
            raise _refuse(CODE_ALREADY_THERE, ALREADY_THERE)
    return found.path


def _owners_of(text: str) -> List[str]:
    return authority.owners_in(text)


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
    be there yet in either layout, and every file has to pass the screens a
    prepared change gets.
    """
    git = runner_or_default(runner)
    address = _address(base_root, git)
    if not files:
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    seen = set()
    changes = []
    for relative, text in files:
        path = _creatable(base_root, relative, git)
        if path in seen:
            raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
        seen.add(path)
        stamped = _stamped(text, address)
        _screened(base_root, path, stamped, address)
        changes.append({"path": path, "before": None, "after": stamped})
    _screen_reason(base_root, reason)
    return _keep(
        base_id,
        {
            "kind": KIND_CREATE,
            "operation": None,
            "value": None,
            "reason": reason,
            "by": address,
            "made": _now().isoformat(),
            "changes": changes,
        },
    )


# --- The settings operations ---------------------------------------------------------


def _list_value(value) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [part.strip() for part in text.split(",")] if text.strip() else []


def _intended(operation: str, value, base_root: str, relative: str, git):
    """What the setting is meant to read as afterwards, and the line that writes it."""
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
            line = addresses[0] if len(addresses) == 1 else "[%s]" % ", ".join(addresses)
            return addresses, line
        if operation == SET_ADMINISTRATORS:
            listed = _list_value(value)
            addresses = validate.validate_owner(listed) if listed else []
            if len(set(addresses)) != len(addresses):
                raise ValidationError("an address listed twice", code=CODE_BAD_VALUE)
            return addresses, "[%s]" % ", ".join(addresses)
        if operation == SET_BUSINESSES:
            listed = businesses.businesses_from(_list_value(value))
            line = ", ".join(
                one.slug if not one.name else "%s (%s)" % (one.slug, one.name)
                for one in listed
            )
            # A business's name is somebody's typing that lands in the map, so
            # it gets the screens any other typing gets.
            allowlist, _code = scan.load_allowlist(base_root)
            if scan.scan_text(line, allowlist, "the businesses"):
                raise _refuse(CODE_SCREENED, SCREENED)
            return [(one.slug, one.name) for one in listed], line
        if operation == SET_BUSINESS:
            said = str(value or "").strip()
            if said == businesses.WHOLE_COMPANY:
                return said, said
            map_text = _saved_text(base_root, constants.MAP_PATH, git)
            listed = [one.slug for one in businesses.read_map_businesses(map_text)]
            folder = businesses.folder_of(relative or "")
            if said not in listed or (
                folder is not None
                and folder not in businesses.RESERVED_SLUGS
                and folder != said
            ):
                raise ValidationError("not a business the map lists", code=CODE_BAD_VALUE)
            return said, said
    except ValidationError:
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)
    raise _refuse(CODE_NOT_AN_OPERATION, NOT_AN_OPERATION)


def _reads_back(operation: str, after: str, intended) -> bool:
    """Whether the new file, read the way each setting's reader reads it, says what was meant."""
    try:
        block, _body = formats.split_document(after)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        return False
    try:
        if operation == SET_OWNER:
            return validate.validate_owner(fields.get("owner")) == intended
        if operation == SET_MAP_OWNER:
            return authority.roles_from_map(after).base_owner == intended[0]
        if operation == SET_ADMINISTRATORS:
            roles = authority.roles_from_map(after)
            return (
                authority.CODE_ADMINISTRATORS_UNREADABLE not in roles.problems
                and roles.administrators == intended
            )
        if operation == SET_BUSINESSES:
            listed = businesses.read_map_businesses(after)
            return [(one.slug, one.name) for one in listed] == intended
        if operation == SET_BUSINESS:
            return str(fields.get(businesses.BUSINESS_FIELD) or "").strip() == intended
    except ValidationError:
        return False
    return False


def _saved_text(base_root: str, relative: str, git: GitRunner) -> str:
    """One file as the base last saved it, or nothing when it never has."""
    shown = git.run(["show", "HEAD:" + relative], cwd=base_root)
    return shown.stdout if shown.ok else ""


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


def _the_line(text: str, key: str) -> str:
    """The one settings line a key is on, with any list lines under it, for the showing."""
    lines = text.split("\n")
    found: List[str] = []
    for index in range(1, len(lines)):
        if lines[index].strip() == formats.FRONTMATTER_FENCE:
            break
        if found:
            if lines[index].lstrip(" ").startswith("-"):
                found.append(lines[index])
                continue
            break
        if lines[index].partition(":")[0].strip() == key and not lines[index].startswith((" ", "-")):
            found.append(lines[index])
    return "\n".join(found) if found else "(no %s line)" % key


def _setting_change(base_root: str, operation: str, path, value, git: GitRunner) -> dict:
    """Work out one settings change from the base as it is now, checking every rule.

    Preparing runs this, and approving runs it again from the base as it is
    then, so what is written never depends on anything kept between the two.
    """
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
    full = os.path.join(base_root, relative.replace("/", os.sep))
    if os.path.islink(full) or os.path.islink(os.path.dirname(full)):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    before = read_text_exactly(full)
    if before is None or not _in_head(base_root, relative, git):
        raise _refuse(CODE_NOT_A_DOCUMENT, NOT_A_DOCUMENT)
    key = _KEY[operation]
    intended, line = _intended(operation, value, base_root, relative, git)
    after = _with_setting(before, key, line)
    _only_that_changed(before, after, key)
    if not _reads_back(operation, after, intended):
        raise _refuse(CODE_BAD_VALUE, BAD_VALUE)
    return {
        "path": relative,
        "before": ids.exact_hash(before),
        "after": after,
        "line_before": _the_line(before, key),
        "line_after": _the_line(after, key),
    }


def prepare_setting(
    base_root: str,
    base_id: str,
    operation: str,
    reason: str,
    path: Optional[str] = None,
    value=None,
    runner: Optional[GitRunner] = None,
) -> Prepared:
    """Prepare one settings line to change, the line and the whole new file shown first."""
    git = runner_or_default(runner)
    change = _setting_change(base_root, operation, path, value, git)
    address = _address(base_root, git)
    _screen_reason(base_root, reason)
    return _keep(
        base_id,
        {
            "kind": KIND_SETTING,
            "operation": operation,
            "value": value if isinstance(value, (str, type(None))) else list(value),
            "path": path,
            "reason": reason,
            "by": address,
            "made": _now().isoformat(),
            "changes": [change],
        },
    )


# --- Approving --------------------------------------------------------------------


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _too_old(kept: dict) -> bool:
    """Whether a prepared operation has waited longer than an approval question may."""
    try:
        made = datetime.datetime.fromisoformat(str(kept.get("made")))
    except (TypeError, ValueError):
        return True
    age = (_now() - made).total_seconds()
    return age < 0 or age > approval.KEPT_SECONDS


def _rebuilt(kept: dict, base_root: str, address: str, git: GitRunner) -> List[dict]:
    """Every change, worked out again from the base as it stands, or a refusal.

    The prepared operation waits in this seat's folder, and a file there can be
    rewritten by anything that runs commands, value bound to it included. So
    nothing about where or what to write is taken from it: a creation's every
    path is checked again and its bytes screened again, with the approving
    address on its owner line, and a setting is worked out again from the
    operation and the value. What comes back has to be exactly what was shown.
    """
    changes = kept.get("changes")
    if not isinstance(changes, list) or not changes:
        raise _refuse(CODE_NOT_WAITING, NOT_WAITING)
    if kept.get("kind") == KIND_CREATE:
        if kept.get("operation") is not None or kept.get("value") is not None:
            raise _refuse(CODE_NOT_WAITING, NOT_WAITING)
        rebuilt = []
        seen = set()
        for change in changes:
            path = _creatable(base_root, str(change.get("path")), git)
            after = change.get("after")
            if path in seen or not isinstance(after, str) or change.get("before") is not None:
                raise _refuse(CODE_MOVED, MOVED)
            seen.add(path)
            if _owners_of(after) != [address] or _stamped(after, address) != after:
                raise _refuse(CODE_MOVED, MOVED)
            _screened(base_root, path, after, address)
            rebuilt.append({"path": path, "before": None, "after": after})
        return rebuilt
    if kept.get("kind") == KIND_SETTING and len(changes) == 1:
        again = _setting_change(
            base_root, kept.get("operation"), kept.get("path"), kept.get("value"), git
        )
        if (again["path"], again["before"], again["after"]) != (
            changes[0].get("path"),
            changes[0].get("before"),
            changes[0].get("after"),
        ):
            raise _refuse(CODE_MOVED, MOVED)
        return [again]
    raise _refuse(CODE_NOT_WAITING, NOT_WAITING)


def _role_for(kept: dict, changes: List[dict], base_root: str, address: str, git: GitRunner) -> Optional[str]:
    """The role that lets this address approve this operation, or None."""
    try:
        if kept["kind"] == KIND_CREATE:
            # The creator approves what they create and owns it (CS1, CS5).
            # The owner line was checked to name exactly this address.
            return authority.ROLE_OWNER
        operation = kept["operation"]
        relative = changes[0]["path"]
        if operation in _DOCUMENT_OPERATIONS:
            return authority.at(base_root, relative, runner=git).role_of(address)
        roles = authority.roles_from_map(_saved_text(base_root, constants.MAP_PATH, git))
    except authority.AuthorityUnavailable:
        return None
    if address == roles.base_owner:
        return authority.ROLE_BASE_OWNER
    if operation == SET_BUSINESSES and address in roles.administrators:
        return authority.ROLE_ADMINISTRATOR
    return None


def _record(kept: dict, changes: List[dict], role: str, today: datetime.date) -> Tuple[str, str]:
    """The record of this approval, and where it goes in the record of corrections."""
    staging_id = kept["prepared_id"]
    touched = [change["path"] for change in changes]
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
        content_hash=ids.content_hash("".join(change["after"] for change in changes)),
        correction_class="other",
        marker=validate.marker_line(staging_id),
        touched_paths=touched,
        what_changed=what,
        why=str(kept.get("reason") or ""),
        approved_roles={path: role for path in touched},
        approved_hashes={
            change["path"]: authority.bytes_hash(change["after"].encode("utf-8"))
            for change in changes
        },
    ).validate()
    where = "%s/%s-%s.md" % (constants.CORRECTIONS_DIR, today.isoformat(), staging_id)
    return where, record.render()


def _creators_yes(base_root, changes, role, today, moment):
    """The creator's confirmation of each new document a confirmation may name.

    Creating a document is its owner saying it is right, so it joins the
    review's clock from the day it is created, recorded with the role (CS9).
    A lesson is never confirmed, so it gets none.
    """
    from . import confirm

    lines = []
    for change in changes:
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
        existing = read_text_exactly(confirm.checked_confirmations_path(base_root, target))
        if existing and not existing.endswith("\n"):
            existing += "\n"
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
    operation: Optional[str] = None,
) -> Done:
    """Write one prepared operation, if this address may and nothing has moved.

    `kind`, and for a setting `operation`, are what the command that approves
    it names, because Claude Code's question said exactly that. A prepared
    operation of another kind or another operation is not written. Nothing
    kept since the showing is trusted: every change is worked out again.
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
    if operation is not None and kept.get("operation") != operation:
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)
    try:
        if not shown or shown != _shown_value(kept):
            return Done(False, CODE_MOVED, MOVED)
    except (KeyError, TypeError):
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)
    if _too_old(kept):
        return Done(False, CODE_MOVED, MOVED)
    try:
        address = _address(base_root, git)
        on_main, _code = paths.head_is_default_branch(base_root, runner=git)
        if not on_main:
            return Done(False, CODE_NOT_ON_MAIN, NOT_ON_MAIN)
        if not unsaved.look(base_root, git).clean:
            return Done(False, CODE_UNSAVED, UNSAVED)
        changes = _rebuilt(kept, base_root, address, git)
        if kept["kind"] == KIND_CREATE and address != kept.get("by"):
            return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
        role = _role_for(kept, changes, base_root, address, git)
        if role is None:
            return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
        record_path, record_text = _record(kept, changes, role, today)
        if os.path.lexists(os.path.join(base_root, record_path.replace("/", os.sep))):
            return Done(False, CODE_MOVED, MOVED)
        writes = [(change["path"], change["after"]) for change in changes]
        writes.append((record_path, record_text))
        if kept["kind"] == KIND_CREATE:
            moment = now if isinstance(now, datetime.datetime) else state.now_utc()
            writes.extend(_creators_yes(base_root, changes, role, today, moment))
    except Refused as refusal:
        return Done(False, refusal.code, str(refusal))
    except (GtmBaseError, KeyError, TypeError, ValueError):
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)
    targets = [relative for relative, _text in writes]
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


# --- What a hand edit may not change ------------------------------------------------


def authority_lines_changed(before: str, after: str) -> bool:
    """Whether one version of a document says a different owner or business than the other.

    Those two lines change only through their own operations (CS15 and CS17),
    shown whole and recorded with the reason, so a change made by hand that
    moves either is refused. Every other setting a person may still edit by
    hand. A settings block that cannot be read on either side counts as moved.
    """
    try:
        old_block, _old = formats.split_document(before)
        new_block, _new = formats.split_document(after)
        old = formats.parse_frontmatter(old_block)
        new = formats.parse_frontmatter(new_block)
    except (ValidationError, PathError):
        return True
    return any(
        old.get(key) != new.get(key) for key in ("owner", businesses.BUSINESS_FIELD)
    )
