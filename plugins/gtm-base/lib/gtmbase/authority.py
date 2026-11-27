"""One authority rule for every document in a base, judged as of a saved version.

Unit 4.2a of Plan 1, from the signed company-skills requirements of
2026-10-10. Whoever creates a document or a skill owns it (CS1). A change to
it may be made and approved, and a confirmation that it is still right may be
given, only by an address in its authority set: its owners, the base owner,
and the administrators (CS3). The base owner is the one address on the map's
`owner:` line and the administrators are its `administrators:` line, both in
the settings block at the top of the map (CS2). Approval, confirmation, the
stale computation and the moment of use all ask this module, so the rule
cannot drift between them.

Authority is judged as it stood when the approval or confirmation happened,
read from the saved versions of the document and the map at that revision
(CS4). An unsaved edit to an owner line or to the map grants nothing. A
document the base has never saved has no saved version, and there the words
in front of the person are all there is, as `approve_local.owners_of` has
always said.

The rest of this module is what an approval is bound to and what this seat
keeps: a skill's manifest (CS10), this seat's list of trusted manifests
(CS11), and the record of conversations marked unattended (CS30). Both lists
live in the plugin's records on this computer, never in a base.

What this proves, and what it does not, is CS13 and CS14 of the requirements:
the address a computer is set up under is a setting on that computer, so the
rule says which address approved, not which human.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List, Optional

from . import constants, docpaths, formats, layout, paths, validate
from .errors import GtmBaseError, PathError, ValidationError
from .fsutil import atomic_write_json, atomic_write_text, ensure_dir, read_json, read_text
from .gitcmd import GitRunner, runner_or_default

# The roles that allow an approval or a confirmation, most particular first.
ROLE_OWNER = "owner"
ROLE_BASE_OWNER = "base-owner"
ROLE_ADMINISTRATOR = "administrator"
ROLES = (ROLE_OWNER, ROLE_BASE_OWNER, ROLE_ADMINISTRATOR)

# The map's settings that carry authority.
OWNER_SETTING = "owner"
ADMINISTRATORS_SETTING = "administrators"

# Why the map names fewer people than it seems to. Each one grants less, never
# more, because a role nobody can read is a role nobody holds.
CODE_MAP_UNREADABLE = "map-settings-unreadable"
CODE_MAP_OWNER_NOT_ONE = "map-owner-not-one-address"
CODE_ADMINISTRATORS_UNREADABLE = "administrators-unreadable"

# How long a local git call made while judging authority may take.
LOCAL_TIMEOUT_SECONDS = 5

# The files this seat keeps. A conversation marked unattended is one file of
# its own in a folder, made in one step, so two marks at once never lose one.
TRUSTED_FILE = "trusted-manifests.json"
UNATTENDED_FOLDER = "unattended-conversations"


class AuthorityUnavailable(GtmBaseError):
    """Who may approve could not be read from the saved history.

    A read that failed or ran out of time is not an answer (as
    `base_reader.AuthorsUnavailable` says of who wrote a line), so it never
    grants anything and never takes a confirmation away: the caller refuses,
    or says nothing.
    """


# --- The roles in the map --------------------------------------------------------


class Roles(object):
    """The base owner and the administrators one version of the map names."""

    __slots__ = ("base_owner", "administrators", "problems")

    def __init__(self, base_owner=None, administrators=None, problems=None):
        self.base_owner: Optional[str] = base_owner
        self.administrators: List[str] = list(administrators or [])
        self.problems: List[str] = list(problems or [])

    def __repr__(self) -> str:
        return "Roles(%r, %r)" % (self.base_owner, self.administrators)


def _settings_of(text: Optional[str]) -> Optional[Dict]:
    try:
        block, _body = formats.split_document(text or "")
        return formats.parse_frontmatter(block)
    except (ValidationError, PathError):
        return None


def _addresses(value) -> Optional[List[str]]:
    """The addresses one settings value lists, none when empty, None when unreadable."""
    if value is None or value == [] or value == "":
        return []
    try:
        return validate.validate_owner(value)
    except ValidationError:
        return None


def roles_from_map(map_text: Optional[str]) -> Roles:
    """The base owner and the administrators, as one version of the map names them.

    A map whose owner line holds anything but one address names no base owner
    (CS2), and an administrators line with anything in it that is not an
    address names no administrator, so a line nobody can read grants nothing.
    """
    fields = _settings_of(map_text)
    if fields is None:
        return Roles(problems=[CODE_MAP_UNREADABLE])
    problems: List[str] = []
    owners = _addresses(fields.get(OWNER_SETTING))
    base_owner = None
    if owners is not None and len(owners) == 1:
        base_owner = owners[0]
    else:
        problems.append(CODE_MAP_OWNER_NOT_ONE)
    administrators = _addresses(fields.get(ADMINISTRATORS_SETTING))
    if administrators is None:
        administrators = []
        problems.append(CODE_ADMINISTRATORS_UNREADABLE)
    return Roles(base_owner, administrators, problems)


# --- The authority set ------------------------------------------------------------


class AuthoritySet(object):
    """Everyone who may approve or confirm one document, with the role of each."""

    __slots__ = ("owners", "base_owner", "administrators")

    def __init__(self, owners=None, roles: Optional[Roles] = None):
        roles = roles or Roles()
        self.owners: List[str] = list(owners or [])
        self.base_owner: Optional[str] = roles.base_owner
        self.administrators: List[str] = list(roles.administrators)

    def role_of(self, address: Optional[str]) -> Optional[str]:
        """The most particular role this address holds here, or None.

        Addresses are compared exactly, letter for letter, as an owner line
        always has been compared with the author of a recorded change.
        """
        if not address:
            return None
        if address in self.owners:
            return ROLE_OWNER
        if address == self.base_owner:
            return ROLE_BASE_OWNER
        if address in self.administrators:
            return ROLE_ADMINISTRATOR
        return None

    def addresses(self) -> List[str]:
        """Every address in the set, owners first, each once."""
        found: List[str] = []
        for address in list(self.owners) + [self.base_owner] + list(self.administrators):
            if address and address not in found:
                found.append(address)
        return found

    def __repr__(self) -> str:
        return "AuthoritySet(%r)" % (self.addresses(),)


def owners_in(document_text: Optional[str]) -> List[str]:
    """The addresses a document's own `owner:` line names, or none."""
    fields = _settings_of(document_text)
    if fields is None:
        return []
    found = _addresses(fields.get(OWNER_SETTING))
    return found or []


def authority_from(document_text: Optional[str], map_text: Optional[str]) -> AuthoritySet:
    """The authority set one version of a document and one version of the map make."""
    return AuthoritySet(owners_in(document_text), roles_from_map(map_text))


def _unavailable() -> AuthorityUnavailable:
    return AuthorityUnavailable(
        "who may approve a document could not be read from the saved history",
        code="unreadable",
    )


def _saved(base_root: str, revision: str, relative: str, git: GitRunner) -> Optional[str]:
    """One file as a revision saved it, None when that revision has no such file.

    The tree is asked first, so a file the revision does not hold and a read
    that failed are told apart; only the first is an answer.
    """
    listed = git.run(
        ["ls-tree", "-z", revision, "--", relative],
        cwd=base_root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not listed.ok:
        raise _unavailable()
    if not listed.stdout.strip("\x00\n "):
        return None
    shown = git.run(
        ["show", "%s:%s" % (revision, relative)],
        cwd=base_root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not shown.ok:
        raise _unavailable()
    return shown.stdout


def _saved_document(
    base_root: str, revision: str, relative: str, git: GitRunner
) -> Optional[str]:
    """One document as a revision saved it, at its path then or its counterpart."""
    text = _saved(base_root, revision, relative, git)
    if text is None:
        other = layout.counterpart(relative)
        if other:
            text = _saved(base_root, revision, other, git)
    return text


def at(
    base_root: str,
    relative: str,
    revision: str = "HEAD",
    runner: Optional[GitRunner] = None,
) -> AuthoritySet:
    """The authority set of one document as a saved revision of the base has it.

    The revision is the moment the question is about: the last saved one for
    an approval happening now, and the one that added a confirmation line for
    a confirmation (CS4). Only when the question is about now is the disk ever
    read: a document the base has never saved is judged by the words in front
    of the person, and a base with no saved history at all by its map as it
    stands. A base that has saved anything is never judged by an unsaved map.
    A read that fails raises `AuthorityUnavailable` rather than answering.
    """
    git = runner_or_default(runner)
    if revision == "HEAD" and not _has_history(base_root, git):
        document = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
        map_text = read_text(os.path.join(base_root, constants.MAP_PATH.replace("/", os.sep)))
        return authority_from(document, map_text)
    document = _saved_document(base_root, revision, relative, git)
    map_text = _saved(base_root, revision, constants.MAP_PATH, git)
    if document is None and revision == "HEAD":
        document = read_text(os.path.join(base_root, relative.replace("/", os.sep)))
    return authority_from(document, map_text)


def _has_history(base_root: str, git: GitRunner) -> bool:
    """Whether the base has saved anything at all, or a refusal when that cannot be read."""
    head = git.run(
        ["rev-parse", "--verify", "-q", "HEAD"], cwd=base_root, timeout=LOCAL_TIMEOUT_SECONDS
    )
    if head.ok:
        return True
    if head.code == 1:
        return False
    raise _unavailable()


# --- What an approval is bound to ----------------------------------------------------


def bytes_hash(data: bytes) -> str:
    """The hash of a file's exact bytes, not one of them changed first."""
    return hashlib.sha256(data).hexdigest()


def file_hash(base_root: str, relative: str) -> Optional[str]:
    """The hash of one file as it sits on the disk now, or None when it cannot be read."""
    full = os.path.join(base_root, relative.replace("/", os.sep))
    if os.path.islink(full) or not os.path.isfile(full):
        return None
    try:
        with open(full, "rb") as handle:
            return bytes_hash(handle.read())
    except OSError:
        return None


class Manifest(object):
    """One version of a whole skill: the base, its name, every file, each file's hash.

    It is the unit a skill is approved and trusted as (CS10), so an extra
    file, a missing one, an edited one, or files of two approved versions put
    together each make a manifest nobody approved.
    """

    __slots__ = ("base_id", "skill", "files")

    def __init__(self, base_id: str, skill: str, files: Dict[str, str]):
        self.base_id = base_id
        self.skill = skill
        self.files = dict(files)

    def as_value(self) -> dict:
        return {"base_id": self.base_id, "skill": self.skill, "files": dict(self.files)}

    def digest(self) -> str:
        text = json.dumps(self.as_value(), sort_keys=True, separators=(",", ":"))
        return bytes_hash(text.encode("utf-8"))

    def __repr__(self) -> str:
        return "Manifest(%r, %d files)" % (self.skill, len(self.files))


def manifest_of(base_root: str, base_id: str, skill: str) -> Optional[Manifest]:
    """The manifest of one skill as it sits on the disk, or None when it cannot be one.

    Every file in the skill's folder has to be one of the skill's three shapes
    and a plain file. A link, a script, a hidden file or anything deeper means
    there is no skill here to trust, which is refused rather than skipped,
    because a file skipped is a file that runs unseen.
    """
    skills = os.path.join(base_root, constants.SKILLS_DIR)
    folder = os.path.join(skills, skill)
    if os.path.islink(skills) or os.path.islink(folder) or not os.path.isdir(folder):
        return None
    files: Dict[str, str] = {}
    unreadable: List[OSError] = []
    for dirpath, dirnames, filenames in os.walk(folder, onerror=unreadable.append):
        for name in list(dirnames):
            if os.path.islink(os.path.join(dirpath, name)):
                return None
        for name in filenames:
            full = os.path.join(dirpath, name)
            relative = os.path.relpath(full, base_root).replace(os.sep, "/")
            found = docpaths.classify(relative)
            if found is None or found.kind != docpaths.KIND_SKILL or found.skill != skill:
                return None
            hashed = file_hash(base_root, relative)
            if hashed is None:
                return None
            files[relative] = hashed
    if unreadable or constants.SKILLS_DIR + "/" + skill + "/SKILL.md" not in files:
        return None
    return Manifest(base_id, skill, files)


# --- What this seat trusts ------------------------------------------------------


def trusted_path(base_id: str) -> str:
    return os.path.join(paths.seat_dir(base_id), TRUSTED_FILE)


def _trusted(base_id: str) -> Optional[List[dict]]:
    """The manifests this seat trusts, none when there is no list, None when unreadable."""
    path = trusted_path(base_id)
    if not os.path.lexists(path):
        return []
    value = read_json(path)
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, dict)]


def trusts(base_id: str, manifest: Optional[Manifest]) -> bool:
    """Whether this seat trusts exactly this version of a skill (CS11)."""
    if manifest is None or manifest.base_id != base_id:
        return False
    listed = _trusted(base_id)
    if not listed:
        return False
    wanted = manifest.digest()
    return any(item.get("digest") == wanted for item in listed)


def trust(base_id: str, manifest: Manifest, approver: str, role: str) -> None:
    """Add one manifest to this seat's trusted list, with who approved it and how.

    A list that cannot be read is not written over, because that would trust
    this one manifest and quietly forget why the others were trusted.
    """
    if manifest.base_id != base_id or role not in ROLES:
        raise ValueError("this is not a manifest of this base, approved in a role")
    listed = _trusted(base_id)
    if listed is None:
        raise ValidationError(
            "this seat's list of trusted skills cannot be read", code="trusted-unreadable"
        )
    digest = manifest.digest()
    if any(item.get("digest") == digest for item in listed):
        return
    listed.append(
        {
            "digest": digest,
            "manifest": manifest.as_value(),
            "approver": approver,
            "role": role,
        }
    )
    atomic_write_json(trusted_path(base_id), listed, inside=paths.seat_dir(base_id))


# --- Conversations marked unattended (CS30) -------------------------------------------


def unattended_path() -> str:
    """The folder that holds one file for each conversation marked unattended."""
    return os.path.join(paths.seat_home_path(), UNATTENDED_FOLDER)


def _mark_name(conversation: str) -> str:
    return hashlib.sha256(conversation.encode("utf-8")).hexdigest()


def is_unattended(conversation: Optional[str]) -> bool:
    """Whether a conversation was marked unattended, which no later start undoes.

    A record that is there and cannot be read answers yes for every
    conversation, because a wrong yes only refuses approvals, which is the
    safe direction, and a wrong no would let one through in a run nobody is
    watching.
    """
    if not conversation:
        return False
    folder = unattended_path()
    if not os.path.lexists(folder):
        return False
    if os.path.islink(folder) or not os.path.isdir(folder):
        return True
    try:
        os.listdir(folder)
    except OSError:
        return True
    return os.path.lexists(os.path.join(folder, _mark_name(conversation)))


def mark_unattended(conversation: str) -> None:
    """Mark one conversation unattended for the rest of its life.

    Each mark is a file of its own, made in one step, so a second mark never
    rewrites the first, and a record that cannot be read is never replaced.
    """
    if not conversation or not isinstance(conversation, str):
        raise ValueError("only a conversation with an identifier can be marked")
    folder = unattended_path()
    if os.path.lexists(folder) and (os.path.islink(folder) or not os.path.isdir(folder)):
        raise ValidationError(
            "the record of runs nobody watches cannot be read", code="unattended-unreadable"
        )
    ensure_dir(folder)
    mark = os.path.join(folder, _mark_name(conversation))
    if not os.path.lexists(mark):
        atomic_write_text(mark, "unattended\n", inside=folder)
