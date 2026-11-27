"""Installing a skill, changing one, and accepting one on this computer.

Plan 1, Unit 4.2b, from the signed company-skills requirements (CS6, CS7,
CS9 to CS11, CS22, CS26, CS27, CS30). These are the only ways a skill reaches
a base's `skills/` folder; a file tool writing there stays refused (CS22).

Installing writes a whole new skill folder. The creator's address is stamped
on its `SKILL.md` owner line before it is shown (CS7), the contract check
runs before anything is shown and again before anything is written (CS26),
and it needs two yeses (CS6): the creator's, and the base owner's or an
administrator's. When the creator is the base owner or an administrator their
one yes counts as both. The two come in either order (Brandon's decision of
2026-11-27): the first waits on this computer as a prepared creation outside
`skills/` and writes nothing, and the second writes. A yes kept in a file
this computer can rewrite is protected only as far as this computer is
(CS14). On every other computer a version is accepted only when the record's
own author held a role before the install, so when the creator's yes is the
one that writes, other computers see no authority behind it and refuse it,
which is the safe direction.

Changing replaces a skill that is already there with a whole new version,
shown whole, the contract check passing first, approved by one address in the
skill's authority set (its owner, the base owner, or an administrator, CS3).
Its owner line changes only through the owner operation (CS15).

Both record one approval of the whole manifest in the record of corrections,
with the role and the hash of every file (CS9), and add that manifest to this
computer's trusted manifests (CS11).

Accepting is how a computer comes to trust a version somebody with authority
approved elsewhere (CS11). It is shown who approved it, in which role, on what
day, and which files changed since the version this computer last trusted, and
asked once. It never approves anything. A version no recorded approval covers
cannot be accepted at all.

All three are approvals, so each goes through Claude Code's own question
(`approval.require`) and is refused in a conversation marked unattended.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import secrets
from typing import Dict, List, Optional, Sequence, Tuple

from . import (
    approval,
    authority,
    base_reader,
    compose_proposal,
    constants,
    docpaths,
    formats,
    ids,
    paths,
    review,
    runner,
    scan,
    skillshape,
    state,
    unsaved,
    validate,
)
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_json, atomic_write_text, ensure_dir, read_bytes, read_json, remove
from .gitcmd import GitRunner, runner_or_default

WRITE_INSTALL = "skill_install.approve"
WRITE_ACCEPT = "skill_install.accept"

KIND_INSTALL = "install"
KIND_CHANGE = "change"

FOLDER = "prepared-skills"
_MODE = 0o644

CODE_NOT_A_SKILL = "not-a-skill"
CODE_SHAPE = "shape"
CODE_SCREENED = "screened"
CODE_CONTRACT = "contract"
CODE_NO_ADDRESS = "no-address"
CODE_NOT_WAITING = "not-waiting"
CODE_MOVED = "moved"
CODE_NOT_ALLOWED = "not-allowed"
CODE_WAITING = "waiting-for-the-base-owner"
CODE_UNSAVED = "unsaved-work"
CODE_NOT_ON_MAIN = "not-on-the-shared-line"
CODE_COULD_NOT_SAVE = "could-not-save"
CODE_NO_APPROVAL = "no-approval"
CODE_TRUSTED = "already-trusted"

# --- The sentences a person reads ---------------------------------------------------

NOT_A_SKILL = (
    "That is not a skill GTM Base can install, because a skill is a folder "
    "holding a SKILL.md, with references and examples in their own folders and "
    "nothing else. Nothing was prepared."
)
SHAPE_REFUSED = (
    "Nothing was prepared, because one of the skill's files is not a shape a "
    "base admits: it is too large, not plain text, or its settings hold a key "
    "a skill may not carry."
)
SCREENED = (
    "Nothing was prepared, because the skill holds something that is never "
    "written into a base, such as an email address, a phone number or a key."
)
CONTRACT_FAILS = (
    "Nothing was prepared, because the skill's own examples do not pass the "
    "contract check. Fix what it says and prepare it again."
)
NO_ADDRESS = (
    "Nothing was prepared, because GTM Base does not know the address this "
    "computer saves work under."
)
NOT_WAITING = "There is no prepared skill by that name waiting here, so nothing was written."
MOVED = (
    "Nothing was written, because the skill or the base changed since it was "
    "shown. Prepare it again and read it again."
)
NOT_ALLOWED = (
    "Nothing was written, because the address this computer saves work under "
    "may not approve this skill."
)
WAITING_FOR_THE_BASE_OWNER = (
    "Your yes as the skill's creator is recorded on this computer, and nothing "
    "is written yet. The base owner or an administrator approves it next."
)
WAITING_FOR_THE_CREATOR = (
    "Your yes is recorded on this computer, and nothing is written yet. The "
    "skill's creator approves it next."
)
UNSAVED = (
    "Nothing was written, because this base has unsaved work in it. Save or "
    "set it aside first."
)
NOT_ON_MAIN = (
    "Nothing was written, because this base is not on its shared line of work "
    "right now."
)
COULD_NOT_SAVE = "GTM Base could not save the skill, so nothing was written and nothing is left behind."
INSTALLED = "The skill is in the base and this computer trusts it, so it can run."
CHANGED = "The skill is changed in the base and this computer trusts the new version."
ACCEPTED = "This computer now trusts this version of the skill, so it can run here."
ALREADY_TRUSTED = "This computer already trusts the skill exactly as it stands."
NO_APPROVAL = (
    "Nobody with authority over this skill approved it exactly as it stands, "
    "so it cannot be accepted. It can only be changed through a prepared "
    "change its owner, the base owner or an administrator approves."
)
SHOWING_WHO = "%s approved this version as %s on %s."
SHOWING_CHANGED = "Since the version this computer last trusted, %s."
SHOWING_FIRST = "This computer has not trusted any version of this skill before."

# How a role is said.
_ROLE_WORDS = {
    authority.ROLE_OWNER: "its owner",
    authority.ROLE_BASE_OWNER: "the base owner",
    authority.ROLE_ADMINISTRATOR: "an administrator",
}


class Refused(GtmBaseError):
    """Preparing was refused; the message is the sentence a person reads."""


class Prepared(object):
    __slots__ = ("prepared_id", "shown", "artifact")

    def __init__(self, prepared_id: str, shown: str, artifact: str):
        self.prepared_id = prepared_id
        self.shown = shown
        self.artifact = artifact


class Done(object):
    __slots__ = ("done", "code", "sentence", "saved_work")

    def __init__(self, done: bool, code: Optional[str], sentence: str, saved_work=None):
        self.done = done
        self.code = code
        self.sentence = sentence
        self.saved_work = saved_work

    def __repr__(self) -> str:
        return "Done(%r, %r)" % (self.done, self.code)


def _refuse(code: str, sentence: str) -> Refused:
    return Refused(sentence, code=code)


# --- Reading what is there ---------------------------------------------------------


def _address(base_root: str, git: GitRunner) -> str:
    address = base_reader.repo_email(base_root, git)
    if not address:
        raise _refuse(CODE_NO_ADDRESS, NO_ADDRESS)
    return address


def _skill_md(skill: str) -> str:
    return "%s/%s/%s" % (constants.SKILLS_DIR, skill, skillshape.SKILL_FILE)


def _saved_skill_files(base_root: str, skill: str, git: GitRunner) -> Dict[str, str]:
    """The skill's files as the base last saved them, none when it holds none."""
    listed = git.run(
        ["ls-tree", "-r", "-z", "--name-only", "HEAD", "--", "%s/%s" % (constants.SKILLS_DIR, skill)],
        cwd=base_root,
    )
    if not listed.ok:
        if authority._has_history(base_root, git):
            raise _refuse(CODE_MOVED, MOVED)
        return {}
    found: Dict[str, str] = {}
    for name in listed.stdout.split("\0"):
        if not name:
            continue
        text = authority.saved_file(base_root, name, runner=git)
        if text is None:
            raise _refuse(CODE_MOVED, MOVED)
        found[name] = text
    return found


def _on_disk(base_root: str, skill: str) -> bool:
    folder = os.path.join(base_root, constants.SKILLS_DIR, skill)
    return os.path.lexists(folder)


def _stamped(text: str, address: str) -> str:
    try:
        block, body = formats.split_document(text)
        fields = formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        raise _refuse(CODE_SHAPE, SHAPE_REFUSED)
    fields["owner"] = address
    return formats.render_document(fields, body)


def _owner_line(text: str):
    try:
        block, _body = formats.split_document(text)
        return formats.parse_frontmatter(block).get("owner")
    except (ValidationError, PathError):
        return None


def _checked_files(
    base_root: str, skill: str, files: Dict[str, str], address: str
) -> Dict[str, str]:
    """The files, each a shape the folder admits, screened, with the contract passing."""
    if not docpaths.classify(_skill_md(skill)) or _skill_md(skill) not in files:
        raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
    for path, text in files.items():
        found = docpaths.classify(path)
        if found is None or found.kind != docpaths.KIND_SKILL or found.skill != skill:
            raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
        if not isinstance(text, str):
            raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
        if "\ufffd" in text:
            # The check before a send reads this character as bytes that were
            # not text, so a file holding it could never be sent.
            raise _refuse(CODE_SHAPE, SHAPE_REFUSED)
        if skillshape.file_problem(path, text.encode("utf-8"), skillshape.REGULAR_MODE):
            raise _refuse(CODE_SHAPE, SHAPE_REFUSED)
        lines = review.frontmatter_line_numbers(text) if path == _skill_md(skill) else set()
        if review.screen(text, owner_email=address, frontmatter_lines=lines):
            raise _refuse(CODE_SCREENED, SCREENED)
    if skillshape.too_many(files):
        raise _refuse(CODE_SHAPE, SHAPE_REFUSED)
    contract = runner.check_skill(skill, files)
    if not contract.passed:
        raise _refuse(CODE_CONTRACT, " ".join([CONTRACT_FAILS] + contract.problems))
    return files


def _screen_reason(base_root: str, reason: str) -> None:
    allowlist, _code = scan.load_allowlist(base_root)
    if not reason.strip() or scan.scan_text(reason, allowlist, "the reason"):
        raise _refuse(CODE_SCREENED, SCREENED)


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
    parts = [
        kept["kind"],
        kept["skill"],
        kept["reason"],
        kept["by"],
        str(kept.get("made") or ""),
        json.dumps(kept["files"], sort_keys=True),
        json.dumps(kept["before"], sort_keys=True),
    ]
    return ids.content_hash("\x1f".join(parts))


def _artifact(kept: dict) -> str:
    pieces = []
    for path in sorted(kept["files"]):
        pieces.append("[[file: %s]]\n%s[[end file]]" % (path, kept["files"][path]))
    for path in sorted(set(kept["before"]) - set(kept["files"])):
        pieces.append("[[taken away: %s]]" % path)
    pieces.append("[[reason]]\n%s\n[[end reason]]" % kept["reason"])
    return "\n\n".join(pieces)


def prepare(
    base_root: str,
    base_id: str,
    skill: str,
    files: Dict[str, str],
    reason: str,
    runner_: Optional[GitRunner] = None,
) -> Prepared:
    """Prepare a whole skill to be installed, or a whole new version of one, to be shown.

    `files` maps each base path under `skills/<skill>/` to its text. Nothing is
    written into the base. A new skill's owner line is stamped with this
    computer's address; a changed skill keeps the owner line it has.
    """
    git = runner_or_default(runner_)
    address = _address(base_root, git)
    before = _saved_skill_files(base_root, skill, git)
    if before:
        kind = KIND_CHANGE
        head = _skill_md(skill)
        if head not in files or _owner_line(files[head]) != _owner_line(before.get(head, "")):
            raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
    else:
        if _on_disk(base_root, skill):
            raise _refuse(CODE_MOVED, MOVED)
        kind = KIND_INSTALL
        files = dict(files)
        if _skill_md(skill) in files:
            files[_skill_md(skill)] = _stamped(files[_skill_md(skill)], address)
    _checked_files(base_root, skill, files, address)
    _screen_reason(base_root, reason)
    kept = {
        "kind": kind,
        "skill": skill,
        "reason": reason,
        "by": address,
        "made": datetime.datetime.now().isoformat(),
        "files": dict(files),
        "before": dict(before),
        "creator_yes": False,
    }
    prepared_id = "stg-" + secrets.token_hex(8)
    kept["prepared_id"] = prepared_id
    atomic_write_json(
        os.path.join(_folder(base_id), prepared_id + ".json"), kept, inside=_folder(base_id)
    )
    return Prepared(prepared_id, _shown_value(kept), _artifact(kept))


def files_from_folder(folder: str, skill: str) -> Dict[str, str]:
    """A skill written outside the base, read into the base paths it would take."""
    found: Dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(folder, followlinks=False):
        for name in list(dirnames):
            if os.path.islink(os.path.join(dirpath, name)):
                raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
        for name in filenames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
            inside = os.path.relpath(full, folder).replace(os.sep, "/")
            data = read_bytes(full)
            if data is None:
                raise _refuse(CODE_NOT_A_SKILL, NOT_A_SKILL)
            try:
                found["%s/%s/%s" % (constants.SKILLS_DIR, skill, inside)] = data.decode("utf-8")
            except UnicodeDecodeError:
                raise _refuse(CODE_SHAPE, SHAPE_REFUSED)
    return found


# --- Approving ---------------------------------------------------------------------


def _too_old(kept: dict) -> bool:
    try:
        made = datetime.datetime.fromisoformat(str(kept.get("made")))
    except (TypeError, ValueError):
        return True
    age = (datetime.datetime.now() - made).total_seconds()
    return age < 0 or age > approval.KEPT_SECONDS


def _authority_role(base_root: str, skill: str, kind: str, address: str, git: GitRunner) -> Optional[str]:
    """The role that lets this address give the yes that writes, or None."""
    try:
        if kind == KIND_CHANGE:
            return authority.at(base_root, _skill_md(skill), runner=git).role_of(address)
        map_text = authority.saved_file(base_root, constants.MAP_PATH, runner=git)
    except authority.AuthorityUnavailable:
        return None
    roles = authority.roles_from_map(map_text)
    if address == roles.base_owner:
        return authority.ROLE_BASE_OWNER
    if address in roles.administrators:
        return authority.ROLE_ADMINISTRATOR
    return None


def _record(kept: dict, role: str, creator_too: bool, today: datetime.date) -> Tuple[str, str]:
    staging_id = kept["prepared_id"]
    files = kept["files"]
    touched = sorted(files)
    if kept["kind"] == KIND_INSTALL:
        what = "Installed the skill %s, %s." % (
            kept["skill"],
            "approved by its creator and by %s" % _ROLE_WORDS[role]
            if creator_too
            else "approved by %s, who also created it" % _ROLE_WORDS[role],
        )
    else:
        what = "Changed the skill %s, approved by %s." % (kept["skill"], _ROLE_WORDS[role])
    record = formats.CorrectionsFile(
        kind="correction",
        date=today.isoformat(),
        staging_id=staging_id,
        intake_path="none",
        mode="none",
        third_party=False,
        content_hash=ids.content_hash("".join(files[path] for path in touched)),
        correction_class="other",
        marker=validate.marker_line(staging_id),
        touched_paths=touched,
        what_changed=what,
        why=str(kept.get("reason") or ""),
        approved_roles={path: role for path in touched},
        approved_hashes={
            path: authority.bytes_hash(files[path].encode("utf-8")) for path in touched
        },
    ).validate()
    where = "%s/%s-%s.md" % (constants.CORRECTIONS_DIR, today.isoformat(), staging_id)
    return where, record.render()


def _save(base_root: str, written: List[str], subject: str, git: GitRunner) -> str:
    git.check(["add", "-A", "--"] + written, cwd=base_root)
    name, address, _codes = compose_proposal._author(base_root, git)
    git.check(
        ["-c", "user.name=%s" % name, "-c", "user.email=%s" % address, "commit", "-q", "-m", subject],
        cwd=base_root,
    )
    return git.run(["rev-parse", "HEAD"], cwd=base_root).out()


def _put_back(base_root: str, kept_bytes: Dict[str, Optional[bytes]], git: GitRunner) -> None:
    """Undo this run's writes: new files taken away, changed or removed ones put back."""
    for relative, data in kept_bytes.items():
        full = os.path.join(base_root, relative.replace("/", os.sep))
        if data is None:
            remove(full)
        else:
            ensure_dir(os.path.dirname(full))
            with open(full, "wb") as handle:
                handle.write(data)
    if kept_bytes:
        git.run(["reset", "-q", "--"] + list(kept_bytes), cwd=base_root)
    # Folders the install made and left empty go too, so nothing is left
    # that looks like a skill.
    for relative in kept_bytes:
        folder = os.path.dirname(os.path.join(base_root, relative.replace("/", os.sep)))
        while folder.startswith(os.path.join(base_root, constants.SKILLS_DIR) + os.sep):
            try:
                os.rmdir(folder)
            except OSError:
                break
            folder = os.path.dirname(folder)


def approve(
    base_root: str,
    base_id: str,
    prepared_id: str,
    shown: str,
    runner_: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> Done:
    """Give one yes to a prepared skill, and write it once the yeses it needs are given."""
    approval.require(WRITE_INSTALL)
    git = runner_or_default(runner_)
    today = now.date() if isinstance(now, datetime.datetime) else (now or state.today())
    where = _kept_path(base_id, prepared_id)
    kept = read_json(where) if where else None
    if not isinstance(kept, dict) or kept.get("prepared_id") != prepared_id:
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
        skill = str(kept["skill"])
        files = kept["files"]
        if not isinstance(files, dict):
            return Done(False, CODE_NOT_WAITING, NOT_WAITING)
        # Nothing kept since the showing is trusted: what is there now has to
        # be what was there then, and the files are checked again in full.
        if _saved_skill_files(base_root, skill, git) != kept["before"]:
            return Done(False, CODE_MOVED, MOVED)
        if kept["kind"] == KIND_INSTALL:
            if _on_disk(base_root, skill) or _owner_line(files.get(_skill_md(skill), "")) != kept["by"]:
                return Done(False, CODE_MOVED, MOVED)
        elif kept["kind"] != KIND_CHANGE:
            return Done(False, CODE_NOT_WAITING, NOT_WAITING)
        _checked_files(base_root, skill, files, kept["by"])
        role = _authority_role(base_root, skill, kept["kind"], address, git)
        creator_too = False
        approver = address
        if kept["kind"] == KIND_INSTALL:
            # Two yeses, in either order (CS6, Brandon's decision of
            # 2026-11-27): the creator's, and the base owner's or an
            # administrator's. One person holding both gives both. Whichever
            # comes first waits on this computer and writes nothing; the
            # second writes.
            is_creator = address == kept["by"]
            if role is None and not is_creator:
                return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
            if is_creator:
                kept["creator_yes"] = True
            if role is not None:
                kept["authority_yes"] = {"address": address, "role": role}
            given = kept.get("authority_yes")
            if not kept.get("creator_yes") or not isinstance(given, dict):
                atomic_write_json(where, kept, inside=_folder(base_id))
                return Done(
                    False,
                    CODE_WAITING,
                    WAITING_FOR_THE_BASE_OWNER if kept.get("creator_yes") else WAITING_FOR_THE_CREATOR,
                )
            role = given.get("role")
            approver = given.get("address")
            if role not in authority.ROLES or not approver:
                return Done(False, CODE_NOT_WAITING, NOT_WAITING)
            # A yes kept from earlier counts only while its giver still holds
            # the role, read from the map as it stands at the write.
            if _authority_role(base_root, skill, kept["kind"], approver, git) != role:
                return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
            creator_too = approver != kept["by"]
        elif role is None:
            return Done(False, CODE_NOT_ALLOWED, NOT_ALLOWED)
        record_path, record_text = _record(kept, role, creator_too, today)
    except Refused as refusal:
        return Done(False, refusal.code, str(refusal))
    except (GtmBaseError, KeyError, TypeError, ValueError):
        return Done(False, CODE_NOT_WAITING, NOT_WAITING)

    writes = [(path, files[path]) for path in sorted(files)]
    writes.append((record_path, record_text))
    removed = sorted(set(kept["before"]) - set(files))
    kept_bytes: Dict[str, Optional[bytes]] = {}
    written: List[str] = []
    try:
        for relative, text in writes:
            full = os.path.join(base_root, relative.replace("/", os.sep))
            kept_bytes[relative] = read_bytes(full) if os.path.lexists(full) else None
            ensure_dir(os.path.dirname(full))
            atomic_write_text(full, text, mode=_MODE, inside=base_root)
            written.append(relative)
        for relative in removed:
            full = os.path.join(base_root, relative.replace("/", os.sep))
            kept_bytes[relative] = read_bytes(full)
            remove(full)
            written.append(relative)
        saved = _save(
            base_root, written, "GTM Base: %s skill %s" % (kept["kind"], prepared_id), git
        )
    except (GtmBaseError, OSError):
        _put_back(base_root, kept_bytes, git)
        return Done(False, CODE_COULD_NOT_SAVE, COULD_NOT_SAVE)
    manifest = authority.Manifest(
        base_id,
        skill,
        {path: authority.bytes_hash(files[path].encode("utf-8")) for path in files},
    )
    authority.trust(base_id, manifest, approver, role)
    remove(where)
    return Done(
        True, None, INSTALLED if kept["kind"] == KIND_INSTALL else CHANGED, saved_work=saved
    )


# --- Accepting a version approved elsewhere (CS11) ------------------------------------


class Showing(object):
    """What a person is shown before accepting a version of a skill."""

    def __init__(self, skill: str):
        self.skill = skill
        self.manifest: Optional[authority.Manifest] = None
        self.trusted = False
        self.approver: Optional[str] = None
        self.role: Optional[str] = None
        self.day: Optional[str] = None
        self.record: Optional[str] = None
        self.changed: List[str] = []
        self.first = True

    @property
    def acceptable(self) -> bool:
        return bool(self.manifest and not self.trusted and self.approver and self.role)

    @property
    def shown(self) -> str:
        if not self.acceptable:
            return ""
        return ids.content_hash(
            "\x1f".join([self.manifest.digest(), self.record or "", self.approver or ""])
        )

    def sentences(self) -> List[str]:
        if self.trusted:
            return [ALREADY_TRUSTED]
        if not self.acceptable:
            return [NO_APPROVAL]
        said = [SHOWING_WHO % (self.approver, _ROLE_WORDS[self.role], self.day)]
        if self.first:
            said.append(SHOWING_FIRST)
        elif self.changed:
            said.append(SHOWING_CHANGED % _changes_in_words(self.changed))
        return said


def _changes_in_words(changed: Sequence[str]) -> str:
    if len(changed) == 1:
        return "one file changed"
    return "%d files changed" % len(changed)


def approval_of(
    base_root: str, base_id: str, skill: str, runner_: Optional[GitRunner] = None
) -> Showing:
    """Who approved this skill exactly as it stands, if anybody with authority did."""
    git = runner_or_default(runner_)
    showing = Showing(skill)
    showing.manifest = authority.manifest_of(base_root, base_id, skill)
    if showing.manifest is None:
        return showing
    showing.trusted = authority.trusts(base_id, showing.manifest)
    if showing.trusted:
        return showing
    files = showing.manifest.files
    default = base_reader._default_branch(base_root, git)
    if not records_intact(base_root, default, git):
        # A record was taken away or changed after it was saved, so who holds
        # which role cannot be replayed safely, and nothing is accepted.
        return showing
    saved = _saved_approvals(base_root, skill, default, git)
    found = [item for item in saved if _is_skill_approval(item[1], skill)]
    matching = [item for item in found if item[1].approved_hashes == files]
    for record_path, record, email, day, revision in matching:
        if any(
            other_revision != revision and _is_ancestor(base_root, revision, other_revision, git)
            for _p, _r, _e, _d, other_revision in found
        ):
            # A newer approval of this skill replaced this one, so the old
            # version is not brought back by putting its bytes back.
            continue
        try:
            # Anything on the main line that changed the skill's folder after
            # the approval ends it, even when the files now match its hashes
            # again, so deleting a newer record and putting the older bytes
            # back does not bring the older version back (the C3 security
            # review, finding 2).
            if _changed_since(base_root, skill, revision, default, git):
                continue
            # Judged only from what authority already approved before this
            # record reached the main line: the skill's owner line as its last
            # valid approval had it, and the map's roles as the base owner
            # last approved them. Whatever simply sat on the main line before
            # the approval is never read, so a teammate who names themself
            # owner or administrator in one change cannot approve in the next
            # (the C3 security review, finding 1).
            role = _approved_authority(base_root, skill, revision, saved, default, git).role_of(
                email
            )
        except authority.AuthorityUnavailable:
            continue
        if role is None or record.approved_roles.get(_skill_md(skill)) not in authority.ROLES:
            continue
        showing.approver, showing.role, showing.day, showing.record = email, role, day, record_path
        break
    last = _last_trusted(base_id, skill)
    if last is not None:
        showing.first = False
        showing.changed = sorted(
            path
            for path in set(last) | set(files)
            if last.get(path) != files.get(path)
        )
    return showing


def _is_skill_approval(record, skill: str) -> bool:
    """Whether a record approves a version of this skill and nothing else."""
    prefix = "%s/%s/" % (constants.SKILLS_DIR, skill)
    return bool(record.approved_hashes) and all(
        path.startswith(prefix) for path in record.approved_hashes
    )


def _saved_approvals(base_root: str, skill: str, default, git: GitRunner) -> list:
    """Every saved approval of this skill or of the map: (path, record, address, day, revision)."""
    found = []
    for record_path in base_reader.correction_files(base_root):
        text = authority.saved_file(base_root, record_path, runner=git)
        if not text:
            continue
        try:
            record = formats.CorrectionsFile.parse(text)
        except (ValidationError, PathError):
            continue
        if not _is_skill_approval(record, skill) and constants.MAP_PATH not in record.approved_hashes:
            continue
        email, day, revision = first_added(base_root, record_path, default, git)
        if email and revision:
            found.append((record_path, record, email, day, revision))
    return found


def first_added(base_root: str, record_path: str, default, git: GitRunner):
    """Who first added a record to the main line, on what day, in which revision.

    The first change, never the newest: whoever edits a record later does not
    become its approver (the C3 security review, the follow-up finding). Both
    of the record's names are asked about, so a record the layout move carried
    over is found where it was first added.
    """
    args = ["log", "--first-parent", "-M", "--diff-filter=A", "--format=%H%x1f%ae%x1f%ad", "--date=short"]
    if default:
        args.append(default)
    args.append("--")
    args.extend(base_reader.record_names(record_path))
    listed = git.run(args, cwd=base_root, timeout=authority.LOCAL_TIMEOUT_SECONDS)
    if not listed.ok:
        return None, None, None
    found = (None, None, None)
    for line in listed.stdout.split("\n"):
        parts = line.strip().split("\x1f")
        if len(parts) == 3 and parts[1] and re.match(r"\d{4}-\d{2}-\d{2}$", parts[2]):
            found = (parts[1], parts[2], parts[0])
    return found


def records_intact(base_root: str, default, git: GitRunner) -> bool:
    """Whether every record ever added to the main line is still there, byte for byte.

    The authority replay reads only the records that exist today, so a record
    taken away, or changed after it was saved, could bring back a role the base
    owner removed. When any record under the corrections folder is missing or
    differs from what was first saved, no approval is accepted at all. Putting
    the record back exactly as it was first saved makes it whole again. Records
    the layout move brought into the folder count from the day they arrived.
    """
    tip = default or "HEAD"
    folder = constants.CORRECTIONS_DIR + "/"
    added = git.run(
        ["log", "--first-parent", "--diff-merges=first-parent", "--no-renames", "--diff-filter=A",
         "--raw", "--no-abbrev", "--format=", tip, "--", folder],
        cwd=base_root,
        timeout=authority.LOCAL_TIMEOUT_SECONDS,
    )
    now = git.run(["ls-tree", "-r", tip, "--", folder], cwd=base_root, timeout=authority.LOCAL_TIMEOUT_SECONDS)
    if not added.ok or not now.ok:
        return False
    first: Dict[str, str] = {}
    for line in added.stdout.split("\n"):
        if not line.startswith(":") or "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 4:
            first[path] = parts[3]  # newest first, so the oldest addition is kept
    current: Dict[str, str] = {}
    for line in now.stdout.split("\n"):
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) == 3:
            current[path] = parts[2]
    return all(current.get(path) == oid for path, oid in first.items())


def _git_lines(base_root: str, args: List[str], git: GitRunner) -> List[str]:
    """One git listing, line by line, or a refusal when it cannot be read."""
    listed = git.run(args, cwd=base_root, timeout=authority.LOCAL_TIMEOUT_SECONDS)
    if not listed.ok:
        raise authority.AuthorityUnavailable(
            "the main line could not be read", code="unreadable"
        )
    return [line.strip() for line in listed.stdout.split("\n") if line.strip()]


def _changed_since(base_root: str, skill: str, revision: str, default, git: GitRunner) -> bool:
    """Whether a change on the main line after this revision touched the skill's folder.

    Each change is compared with its own first parent, which is how the main
    line moved, so a folder changed and then put back still counts as changed.
    """
    folder = "%s/%s/" % (constants.SKILLS_DIR, skill)
    return bool(
        _git_lines(
            base_root,
            ["log", "--first-parent", "--format=%H", "%s..%s" % (revision, default or "HEAD"), "--", folder],
            git,
        )
    )


def _approved_authority(
    base_root: str, skill: str, revision: str, saved: list, default, git: GitRunner
) -> authority.AuthoritySet:
    """The skill's authority set as authority itself had approved it before this revision.

    The main line is walked from its oldest change. The map's roles start as
    the map the base first saved there, which is the base being set up, and
    change only with a record of the map approved by the base owner those
    roles name, whose map bytes are exactly the ones approved. The skill's
    owners are the owner line of the last approval of the skill that was
    itself valid, read from the SKILL.md bytes it approved, so a skill nobody
    has validly approved yet has no owner at all. Changes in the same revision
    are judged on what stood before it. Nothing that merely sat on the main
    line is ever read as authority.
    """
    tip = default or "HEAD"
    line = _git_lines(base_root, ["rev-list", "--first-parent", tip], git)
    place = dict((oid, index) for index, oid in enumerate(line))
    if revision not in place:
        raise authority.AuthorityUnavailable("the approval is not on the main line", code="unreadable")
    skill_md = _skill_md(skill)
    events: Dict[int, list] = {}
    map_changes = _git_lines(
        base_root, ["log", "--first-parent", "--format=%H", tip, "--", constants.MAP_PATH], git
    )
    if map_changes and map_changes[-1] in place:
        events.setdefault(place[map_changes[-1]], []).append((0, "", "first-map", None, None))
    for record_path, record, email, _day, at in saved:
        if at not in place:
            continue
        if constants.MAP_PATH in record.approved_hashes:
            events.setdefault(place[at], []).append((1, record_path, "map", record, email))
        if _is_skill_approval(record, skill):
            events.setdefault(place[at], []).append((2, record_path, "skill", record, email))
    roles = authority.Roles()
    owners: List[str] = []
    for index in sorted((i for i in events if i > place[revision]), reverse=True):
        at = line[index]
        judged = authority.AuthoritySet(owners, roles)
        new_roles, new_owners = roles, owners
        for _order, _path, kind, record, email in sorted(events[index], key=lambda e: (e[0], e[1])):
            if kind == "first-map":
                new_roles = authority.roles_from_map(
                    authority._saved(base_root, at, constants.MAP_PATH, git)
                )
                continue
            if kind == "map":
                if not roles.base_owner or email != roles.base_owner:
                    continue
                if record.approved_roles.get(constants.MAP_PATH) not in authority.ROLES:
                    continue
                text = authority._saved(base_root, at, constants.MAP_PATH, git)
                if text is not None and authority.bytes_hash(
                    text.encode("utf-8")
                ) == record.approved_hashes[constants.MAP_PATH]:
                    new_roles = authority.roles_from_map(text)
                continue
            if judged.role_of(email) is None or record.approved_roles.get(skill_md) not in authority.ROLES:
                continue
            text = authority._saved(base_root, at, skill_md, git)
            if text is not None and authority.bytes_hash(
                text.encode("utf-8")
            ) == record.approved_hashes.get(skill_md):
                new_owners = authority.owners_in(text)
        roles, owners = new_roles, new_owners
    return authority.AuthoritySet(owners, roles)


def _is_ancestor(base_root: str, older: str, newer: str, git: GitRunner) -> bool:
    return git.run(["merge-base", "--is-ancestor", older, newer], cwd=base_root).ok


def _last_trusted(base_id: str, skill: str) -> Optional[Dict[str, str]]:
    listed = authority._trusted(base_id) or []
    found = None
    for item in listed:
        manifest = item.get("manifest")
        if isinstance(manifest, dict) and manifest.get("skill") == skill:
            if isinstance(manifest.get("files"), dict):
                found = manifest["files"]
    return found


def accept(
    base_root: str,
    base_id: str,
    skill: str,
    shown: str,
    runner_: Optional[GitRunner] = None,
) -> Done:
    """Trust on this computer a version somebody with authority already approved."""
    approval.require(WRITE_ACCEPT)
    showing = approval_of(base_root, base_id, skill, runner_)
    if showing.trusted:
        return Done(False, CODE_TRUSTED, ALREADY_TRUSTED)
    if not showing.acceptable:
        return Done(False, CODE_NO_APPROVAL, NO_APPROVAL)
    if not shown or shown != showing.shown:
        return Done(False, CODE_MOVED, MOVED)
    authority.trust(base_id, showing.manifest, showing.approver, showing.role)
    return Done(True, None, ACCEPTED)
