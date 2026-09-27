"""Looking at a draft with the person, and writing it down when they say yes.

Four answers end a step. Approve writes the draft into the base. Edit takes the
person's own rewrite and reads it back through the same checks. Skip writes a
file that says it was skipped, so nothing downstream mistakes an absence for a
change. "What is wrong with this?" asks for the whole draft again with their
answer applied, and it writes nothing anywhere.

Two things stand between a draft and the disk. The first is the screen: the
draft is read for anything that would be somebody's contact details, anything
shaped like a key, and anything a reader of the file would not see. A match
sends the step back to be drafted again, and what comes back to the caller is
the class that matched and never the value. The second is the state of the
folder: later files are only written onto the line of work the team shares, in
a folder with nothing else half done in it, and only when the base does not
already hold that file. Setting up writes files that were not there. It never
edits one that was.

The file and the line recording the person's yes are saved together, as one
piece of work, so a base can never hold a file nobody approved.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
import stat
from typing import List, Optional

from . import (
    base_reader,
    confirm,
    constants,
    create_base,
    drafting,
    formats,
    fsutil,
    ids,
    layout,
    paths,
    redaction_patterns,
    scan,
    segments,
    state,
)
from .errors import PathError, ReviewError
from .gitcmd import GitRunner, runner_or_default, status_entries

# What the screen reads a draft for. A share link and a path from inside a home
# folder are left to the check that runs when something is about to leave the
# machine; here the question is only whether the draft picked up a person's
# details or a key out of the material it read.
SCREENED_CLASSES = (
    redaction_patterns.HIDDEN_CONTENT,
    redaction_patterns.EMAIL,
    redaction_patterns.PHONE,
    redaction_patterns.KEY_SHAPE,
    redaction_patterns.VENDOR_URL_TOKEN,
)
SKIPPED_CLASSES = tuple(
    name
    for name, _pattern, _label in redaction_patterns.PATTERN_CLASSES
    if name not in SCREENED_CLASSES
)

# The reasons a write is refused.
CODE_SCREENED = "screened"
CODE_UNSAVED_EDITS = "unsaved-edits"
CODE_NOT_DEFAULT_BRANCH = "not-the-shared-line-of-work"
CODE_FILE_EXISTS = "file-already-there"
CODE_NO_BASE = "no-base"
CODE_GIT_FAILED = "git-failed"
CODE_CONFIRMATION_REFUSED = "confirmation-refused"
# Recorded when an approved file lives outside `context`, so no line saying the
# owner approved it can be written. A confirmation line names a context file by
# definition, and the one context change setup writes is not one.
CODE_NO_DRAFTED_LINE = "no-drafted-line"
# No address could be found for the person who owns this base, so there is
# nobody to write on the owner line and nobody for the currency check to
# compare against later.
CODE_OWNER_MISSING = "owner-missing"
# A context change named a file it may not name, and the path itself said why.
CODE_BAD_AFFECTED_PATH = "bad-affected-path"
# Every identifier this plugin can work out for a context change is already
# taken on this base, so there is nowhere to write another one.
CODE_NO_ROOM_FOR_A_CHANGE = "no-room-for-another-change"
# A finished page handed in to be written is not the one the person was shown
# and said yes to (Unit 1.7c).
CODE_NOT_WHAT_WAS_SHOWN = "not-what-was-shown"

# What the saved work is called when a file is written during setup.
SAVE_MESSAGE = "Add %s from setup"
# What it is called when only the line recording the yes to one is saved.
CONFIRM_SAVED_MESSAGE = "Record the yes to %s from setup"

# The settings lines this plugin writes the base's own address onto a moment
# after the screen runs. Whatever a draft put on one of them is replaced, so
# reading them as a leak would only ever refuse the plugin's own value.
# Both spellings of the setting that names a person are here. A draft written
# by a model that learned the older name still carries an address, and a line
# let through and then left as the draft wrote it would be a way to put
# somebody's address into the base on a line nobody checks.
_OWNER_KEYS = ("owner", "owner_handle", "noted_by", "decided_by")
# The one settings line setting a base up never writes a value onto, so a draft
# that carries it has it taken off rather than written over.
HANDLE_KEY = "owner_handle"


class ApproveResult(object):
    """Where the draft landed, the work that holds it, and what was noted."""

    __slots__ = ("path", "commit", "codes", "root", "base_id")

    def __init__(self, path, commit, codes=None, root=None, base_id=None):
        self.path = path
        self.commit = commit
        self.codes = list(codes or [])
        self.root = root
        self.base_id = base_id

    def __repr__(self) -> str:
        return "ApproveResult(path=%r, codes=%r)" % (self.path, self.codes)


# --- The screen --------------------------------------------------------------


def frontmatter_line_numbers(text: str) -> set:
    """The line numbers of the settings block at the top of a parsed document.

    The block is the lines between the two fence lines, counted from one. When
    the text has no closed settings block at all, nothing is in the block, and
    the answer is the empty set rather than a guess.
    """
    lines = str(text or "").split("\n")
    if not lines or lines[0].strip() != formats.FRONTMATTER_FENCE:
        return set()
    for index in range(1, len(lines)):
        if lines[index].strip() == formats.FRONTMATTER_FENCE:
            return set(range(2, index + 1))
    return set()


def _exempt_lines(text: str, owner_email: Optional[str], block: set) -> set:
    """The line numbers in the settings block that hold an address on purpose.

    The owner line is exempt whatever it says, because the owner's address is
    written there by this plugin a moment later. Any other settings line whose
    value is exactly the owner's own address is exempt too, which is how the
    context change's `noted_by` gets through while a prospect's address in
    the body does not.

    Only the lines the caller named as the settings block are ever considered.
    A piece of raw typing that happens to open with three dashes is not a
    document with settings in it, and nothing in it is exempt from anything.
    """
    exempt = set()
    if not block:
        return exempt
    lines = text.split("\n")
    for number, line in enumerate(lines, start=1):
        if number not in block:
            continue
        name, separator, value = line.partition(":")
        if not separator:
            continue
        if name.strip() in _OWNER_KEYS:
            exempt.add(number)
        elif owner_email and value.strip().strip("\"'") == owner_email:
            exempt.add(number)
    return exempt


def screen(
    draft, owner_email: Optional[str] = None, frontmatter_lines=None
) -> List[str]:
    """Every class of thing found in a draft that must not be written down.

    What comes back is the names of the classes, in the order the scan reports
    them, with no duplicates. The value that matched never leaves the scan.

    Only a document that was read back as a draft gets any exemption, and only
    on the lines that draft says are its settings block. Anything handed in as
    plain text, such as a person's own note about what got in the way, is read
    from the first character to the last with nothing let through, because text
    that merely starts with three dashes is not a document with settings.
    """
    text = getattr(draft, "text", draft)
    if frontmatter_lines is None:
        block = (
            frontmatter_line_numbers(text) if hasattr(draft, "text") else set()
        )
    else:
        block = set(frontmatter_lines)
    exempt = _exempt_lines(text, owner_email, block)
    found: List[str] = []
    for hit in scan.scan_text(text, None, "the draft", SKIPPED_CLASSES):
        if hit.line_number in exempt:
            continue
        if hit.pattern_class not in found:
            found.append(hit.pattern_class)
    return found


def _fenced(text: str) -> str:
    """Put a document back inside a fence so the parse can read it again."""
    return "```markdown\n" + text.rstrip("\n") + "\n```\n"


def _reparse(draft, fields, body):
    fresh = drafting.parse(draft.step, _fenced(formats.render_document(fields, body)))
    # Where a segment goes was worked out from the settled inventory, never
    # read off the draft, so it is carried across rather than lost.
    fresh.destination = getattr(draft, "destination", None)
    return fresh


def stamp_owner(draft, owner_email: str):
    """Put the base's own address on a draft, and read the draft back again.

    The profile and the positioning carry an `owner`. The context change
    carries `noted_by` instead, which is the same person saying the same thing
    about the same base, so it is stamped the same way.

    Every settings line the screen lets an address through on is written over
    here. A line that is let through and then left as the draft wrote it would
    be a way to put somebody's address into the base by writing it on a line
    nobody checks. Setting a base up never records a handle for anybody, so a
    handle line is taken off the document rather than written over.
    """
    block, body = formats.split_document(draft.text)
    fields = formats.parse_frontmatter(block)
    fields.pop(HANDLE_KEY, None)
    for key in _OWNER_KEYS:
        if key != HANDLE_KEY and key in fields:
            fields[key] = owner_email
    return _reparse(draft, fields, body)


def edit(draft, new_text: str, owner_email: Optional[str] = None):
    """Read the person's own rewrite back through everything a draft goes through.

    A rewrite is a draft. It goes through the same parse and the same screen,
    and whatever the screen found is carried on the draft that comes back, so
    the caller decides what to do about it rather than being told.
    """
    fresh = drafting.parse(draft.step, new_text)
    fresh.codes = screen(fresh, owner_email)
    return fresh


def what_is_wrong(draft, answer: str) -> str:
    """The note that asks for the same draft again. It writes nothing."""
    return drafting.what_is_wrong(draft, answer)


# --- The context change ------------------------------------------------------


def _affects_of(draft) -> List[str]:
    value = draft.fields.get("affects", [])
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def canonical_affects(draft, base_root: Optional[str] = None) -> List[str]:
    """The files a context change says it affects, each one checked.

    The shape is checked always, so a path climbing out of the base is refused
    even with no base to check it against. When there is a base, the real path
    is resolved too, so a link pointing out of the context folder is refused as
    well.
    """
    checked = []
    for candidate in _affects_of(draft):
        if base_root:
            checked.append(paths.canonical_context_path(base_root, candidate))
        else:
            checked.append(paths.check_context_path_syntax(candidate))
    return checked


def entry_id(sequence: int = 0) -> str:
    """The name of the context change setup writes.

    It is worked out here and never read off the draft, because an identifier a
    model wrote is an identifier nobody can work out again.
    """
    return ids.staging_id("join", drafting.ENTRY_ID_SEED_PATH, "join", sequence)


# How many identifiers are tried before a base is said to have no room for
# another context change. It is far more closings than any base will see, and
# the bound is here so a folder somebody filled by hand cannot make this run
# for ever.
ENTRY_SEQUENCE_CAP = 1000


def free_entry_id(base_root: Optional[str]) -> str:
    """The first identifier for a closing change that no folder already holds.

    The four things the identifier is worked out from are fixed, so the first
    one is the same on every base and for every closing. That was fine while
    setting a base up wrote one change and never ran twice, and it stopped
    being fine the moment the closing became a question somebody can answer
    more than once. Two states went wrong. On a base whose changes are still
    in the older folder, a second entry under the same identifier landed in
    the newer folder and the two disagreed, which is the one state nothing
    here can resolve and which quietly unflags every document that change is
    about. On a base already using the newer folder, a second closing was
    refused because the file was there.

    Both folders are looked in, so an identifier counts as free only when
    neither holds it.
    """
    if not base_root:
        return entry_id(0)
    for sequence in range(ENTRY_SEQUENCE_CAP):
        candidate = entry_id(sequence)
        relative, _text = base_reader.entry_path_and_text(base_root, candidate)
        if relative is None:
            return candidate
    raise ReviewError(CODE_NO_ROOM_FOR_A_CHANGE, code=CODE_NO_ROOM_FOR_A_CHANGE)


def stamp_entry(
    draft,
    run_id: Optional[str],
    owner_email: str,
    sequence: int = 0,
    entry_name: Optional[str] = None,
):
    """Put this plugin's own identifiers on a context change.

    The identifier and where it came from are set here, over whatever the
    draft said, so the entry a person approves is the entry the rest of the
    plugin can find again.

    A context change given at the closing carries no run, and the caller says
    so by handing in nothing for it. The run is what the currency rules read
    when they decide that a file drafted in one sitting was put in front of
    the owner beside the change written in that same sitting. A sentence the
    person gave at the closing was not, so the entry that comes out of it must
    not claim it was, and the setting is taken off rather than left as the
    draft wrote it (requirement P5, and Codex condition B of
    `docs/reviews/2026-09-19-codex-setup-shape-verdict.md`).
    """
    block, body = formats.split_document(draft.text)
    fields = formats.parse_frontmatter(block)
    fields["id"] = entry_name or entry_id(sequence)
    fields["origin"] = "join"
    if run_id:
        fields["run_id"] = run_id
    else:
        fields.pop("run_id", None)
    if owner_email:
        # The older spelling is taken off rather than left beside the new one,
        # because a file holding both would be a file with two answers to the
        # question of who noted the change.
        fields.pop("decided_by", None)
        fields["noted_by"] = owner_email
    return _reparse(draft, fields, body)


def entry_path(draft, base_root: Optional[str] = None) -> str:
    """Where the context change is written.

    A base that has not been updated yet keeps its changes in the older
    folder, and a change it already holds is written where it already is, so
    one identifier never names two files. `base_reader` owns that rule and it
    is asked rather than repeated here.
    """
    name = str(draft.fields["id"])
    if base_root:
        return base_reader.where_to_write_the_entry(base_root, name)
    return constants.CHANGES_DIR + "/" + name + ".md"


def _already_there(base_root: str, relative: str) -> bool:
    """Whether this document is already in the base, at its path in either layout.

    Setup writes a document only where nothing is, and a base laid out before
    Unit 1.5b holds the same document at its older path. Writing the new one
    beside it would leave one document in two places saying two things.
    """
    for candidate in (relative, layout.counterpart(relative)):
        if candidate and os.path.lexists(
            os.path.join(base_root, candidate.replace("/", os.sep))
        ):
            return True
    return False


def _segment_file_is_free(base_root: str, relative: str) -> None:
    """Refuse a segment's file when anything already stands in its way.

    The folder has to be an ordinary folder inside the base, and no file in
    either folder segments have been kept in may fold to the same name, which
    is how a file a Unit 1.5b move left under its original name, or one that
    differs only in letter case or in how a letter is encoded, is found
    before it could be written over (Unit 1.7a's note to Unit 1.7b).
    """
    if not segments.folder_is_ordinary(base_root):
        raise ReviewError(
            segments.CODE_FOLDER_NOT_ORDINARY, code=segments.CODE_FOLDER_NOT_ORDINARY
        )
    name = relative.rsplit("/", 1)[-1]
    slug = name[: -len(".md")] if name.endswith(".md") else name
    if (
        relative != segments.destination(slug)
        or segments.slug_problem(slug) is not None
        or segments.already_in_base(base_root, slug) is not None
    ):
        raise ReviewError(segments.CODE_FILE_TAKEN, code=segments.CODE_FILE_TAKEN)


def check_segment_write(base_root: str, relative: str, git: GitRunner) -> None:
    """Refuse a segment's file for every reason the write itself would refuse it.

    The same checks, in the same order, as `approve_adopted` makes before it
    writes: the line of work the team shares with nothing half done on it, an
    ordinary folder, and no file already there whose name folds to the same
    one. A segment drafted with a record kept for it runs these before its
    yes is written down (Brandon's call 29), so a refusal leaves nothing
    written anywhere.
    """
    ready_to_write(base_root, git)
    _segment_file_is_free(base_root, relative)
    if _already_there(base_root, relative):
        raise ReviewError(CODE_FILE_EXISTS)


def path_for(draft, base_root: Optional[str] = None) -> str:
    """Where in the base a draft belongs, whichever step it came from."""
    if draft.step == drafting.STEP_CHANGE:
        return entry_path(draft, base_root)
    return draft.path


# --- Writing it down ---------------------------------------------------------


def ready_to_write(base_root: str, git: GitRunner) -> None:
    """Refuse to write while the folder has something else half done in it.

    Every path that writes into a base runs this first, the closing note
    included, so nothing is written onto a line of work the team does not share
    and nothing lands on top of edits somebody has not dealt with yet.
    """
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        raise ReviewError(CODE_NOT_DEFAULT_BRANCH)
    status = git.run(["status", "--porcelain"], cwd=base_root)
    if not status.ok:
        raise ReviewError(CODE_GIT_FAILED)
    if status.out():
        raise ReviewError(CODE_UNSAVED_EDITS)


# --- Putting a new file down, and nothing else (Astra's finding 2 on 1.7c) ---
#
# Every check above looks at a name and then lets it go, and something can be
# put at that name in between: a file, a link to somewhere outside the base, or
# a link in place of one of the folders on the way. So a new file is put down
# the one way that cannot be redirected. The folders are walked one at a time
# from the top of the base, each opened with links refused and the next found
# inside the one already open. The bytes are written whole to a temporary name
# in the last of them, made only where nothing is, and then given their real
# name in one step that fails when anything at all is already there, a link
# included. So the real name only ever holds the whole of the bytes or nothing,
# however the run stops (the correctness review of Unit 1.7d, finding 1). What
# was created is known by its identity on the disk, so taking it back later
# removes that file and never one somebody put in its place.

_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
# What a temporary name starts with. A run that stopped between writing one
# and naming it leaves it behind, and it is swept before the next write.
TEMPORARY_PREFIX = ".gtmbase-new-"
# Whether this computer can open, make, name, and remove a name inside a
# folder already open. Where it cannot, the ordinary checks above are all
# there is, and that is said.
DESCRIPTOR_WRITES = (
    os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.unlink in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.stat in os.supports_follow_symlinks
    and os.link in os.supports_dir_fd
    and os.link in os.supports_follow_symlinks
    and os.rename in os.supports_dir_fd
    and bool(_NO_FOLLOW)
)


def _open_folders(base_root: str, parts, make: bool):
    """Open each folder on the way down, links refused, and return them all.

    The caller closes them. A folder that is a link, or a name on the way that
    is not a folder, is refused.
    """
    opened = [os.open(os.path.realpath(base_root), os.O_RDONLY | _DIRECTORY)]
    try:
        for part in parts:
            if make:
                try:
                    os.mkdir(part, 0o777, dir_fd=opened[-1])
                except FileExistsError:
                    pass
            try:
                opened.append(
                    os.open(
                        part,
                        os.O_RDONLY | _DIRECTORY | _NO_FOLLOW,
                        dir_fd=opened[-1],
                    )
                )
            except OSError:
                raise ReviewError(
                    segments.CODE_FOLDER_NOT_ORDINARY,
                    code=segments.CODE_FOLDER_NOT_ORDINARY,
                )
        return opened
    except BaseException:
        _close_all(opened)
        raise


def _close_all(opened) -> None:
    for handle in opened:
        try:
            os.close(handle)
        except OSError:
            pass


def _write_whole(handle, data: bytes):
    with os.fdopen(handle, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        found = os.fstat(stream.fileno())
    return (found.st_dev, found.st_ino)


def _create_new(base_root: str, relative: str, data: bytes):
    """Create one file that was not there, whole, and return who it is on the disk.

    Nothing already at the name is ever opened, truncated, or followed: a
    file, a link, or anything else there refuses the write.
    """
    parts = relative.split("/")
    if not DESCRIPTOR_WRITES:
        full = os.path.join(base_root, relative.replace("/", os.sep))
        folder = os.path.dirname(full)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        try:
            handle = os.open(full, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            raise ReviewError(CODE_FILE_EXISTS, code=CODE_FILE_EXISTS)
        return tuple(_write_whole(handle, data)) + (hashlib.sha256(data).hexdigest(),)
    opened = _open_folders(base_root, parts[:-1], make=True)
    folder = opened[-1]
    temporary = TEMPORARY_PREFIX + os.urandom(8).hex()
    owning = fsutil.FolderLock(_real_folder(base_root, parts[:-1]))
    owning.__enter__()
    try:
        handle = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW,
            0o666,
            dir_fd=folder,
        )
        try:
            identity = _write_whole(handle, data)
            # The real name is given in one step, which fails when anything
            # at all is already there.
            os.link(
                temporary,
                parts[-1],
                src_dir_fd=folder,
                dst_dir_fd=folder,
                follow_symlinks=False,
            )
        except FileExistsError:
            raise ReviewError(CODE_FILE_EXISTS, code=CODE_FILE_EXISTS)
        finally:
            try:
                os.unlink(temporary, dir_fd=folder)
            except OSError:
                pass
        return tuple(identity) + (hashlib.sha256(data).hexdigest(),)
    finally:
        owning.__exit__(None, None, None)
        _close_all(opened)


def _real_folder(base_root: str, parts) -> str:
    """The folder a name sits in, as the ownership lock names it."""
    return os.path.realpath(os.path.join(base_root, *parts)) if parts else os.path.realpath(base_root)


# The names every writer here gives a file before it is complete: a page
# (above), and a whole file put down in one move by `fsutil`, which is how a
# confirmations file is written. A claimed name is never among them.
_TEMPORARY_PREFIXES = (TEMPORARY_PREFIX, ".gtmbase-", ".tmp-")


def _is_temporary(name: str) -> bool:
    return name.startswith(_TEMPORARY_PREFIXES) and not name.startswith(CLAIM_PREFIX)


def sweep_temporary(base_root: str, folder_relative: str) -> List[str]:
    """Take away the temporary files writers that died left in one folder.

    Every writer of such a file holds the folder's ownership lock for its
    whole write and move, and the operating system lets go of it the moment
    the writer dies. The sweep takes that lock exclusively without waiting:
    when it gets it, no writer is alive in the folder, so every temporary
    file there was left by one that died, and each goes; when it does not,
    nothing is taken, however old anything looks. No clock is read (Astra's
    confirmation pass on the merged units, finding 2). A cleanup that stopped
    after moving a file to its private name is settled here too.
    """
    removed: List[str] = []
    if not DESCRIPTOR_WRITES:
        return removed
    parts = folder_relative.split("/")
    try:
        opened = _open_folders(base_root, parts, make=False)
    except (ReviewError, OSError):
        return removed
    try:
        with fsutil.FolderLock(_real_folder(base_root, parts), exclusive=True) as sweeping:
            if not sweeping.held:
                return removed
            for name in os.listdir(opened[-1]):
                if name.startswith(CLAIM_PREFIX):
                    _settle_claim(opened[-1], name)
                    continue
                if not _is_temporary(name):
                    continue
                try:
                    found = os.stat(name, dir_fd=opened[-1], follow_symlinks=False)
                except OSError:
                    continue
                if not stat.S_ISREG(found.st_mode):
                    continue
                try:
                    os.unlink(name, dir_fd=opened[-1])
                    removed.append(name)
                except OSError:
                    pass
    finally:
        _close_all(opened)
    return removed


def sweep_for_a_page(base_root: str, relative: str) -> None:
    """Sweep the two folders one page's write touches: its own and its line's."""
    folder = relative.rsplit("/", 1)[0]
    sweep_temporary(base_root, folder)
    sweep_temporary(base_root, constants.CONFIRMATIONS_DIR)


def installed(base_root: str, relative: str):
    """What sits at a name in the base, as (its bytes, who it is), or None.

    Read without following a link, in the folder reached the same way a new
    file is written, so what is read is what the write would have touched.
    Anything that is not an ordinary file comes back as None, and opening it
    never waits, so a pipe put at the name cannot hold a run up.
    """
    parts = relative.split("/")
    if not DESCRIPTOR_WRITES:
        full = os.path.join(base_root, relative.replace("/", os.sep))
        if os.path.islink(full) or not os.path.isfile(full):
            return None
        data = fsutil.read_bytes(full)
        if data is None:
            return None
        found = os.lstat(full)
        return data, (found.st_dev, found.st_ino)
    try:
        opened = _open_folders(base_root, parts[:-1], make=False)
    except (ReviewError, OSError):
        return None
    try:
        try:
            handle = os.open(
                parts[-1], os.O_RDONLY | _NO_FOLLOW | _NONBLOCK, dir_fd=opened[-1]
            )
        except OSError:
            return None
        with os.fdopen(handle, "rb") as stream:
            found = os.fstat(stream.fileno())
            if not stat.S_ISREG(found.st_mode):
                return None
            return stream.read(), (found.st_dev, found.st_ino)
    finally:
        _close_all(opened)


# What a name is moved to while cleanup looks at who it is. The private name
# carries what a later run needs to settle it if this one stops there: who the
# file this run made is on the disk, the hash of what it made, and the name
# the file came from. It is never swept as a temporary file; a sweep settles
# it instead (Astra's confirmation pass on the merged units, finding 1).
CLAIM_PREFIX = ".gtmbase-claim-"
# What a file that could not go back under its own name is kept under, beside
# it: the name it had, this mark, a number, and its ending.
KEPT_MARK = ".kept-aside-"
# Somebody else's file could not go back under its name and was kept aside.
CODE_KEPT_ASIDE = "kept-aside"


def _claim_name(identity, original: str) -> str:
    inode = str(int(identity[1])) if identity and len(identity) > 1 else "0"
    digest = str(identity[2])[:16] if identity and len(identity) > 2 else "0" * 16
    return "%s%s-%s-%s" % (CLAIM_PREFIX, inode, digest, original)


# A claim's name exactly as `_claim_name` writes one: digits from 0 to 9 for
# the inode, sixteen lowercase hexadecimal characters for the hash, and the
# name the file came from (Astra's second confirmation pass, finding 3).
_CLAIM_RE = re.compile(r"\A" + re.escape(CLAIM_PREFIX) + r"([0-9]+)-([0-9a-f]{16})-(.+)\Z")
# The names a claimed file can have come from: a segment page, or a file of
# confirmations.
_PAGE_NAME_RE = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\.md\Z")
_CONFIRMATIONS_NAME_RE = re.compile(r"\Acontext(?:--[a-z0-9]+(?:-[a-z0-9]+)*)+\.md\Z")


def _claim_parts(name: str):
    """What a claim's name says, or None when it is not exactly one.

    Anything else shaped like a claim is somebody's file, left exactly where
    it is and never renamed or removed; the base then counts it as work half
    done, which is how it is reported.
    """
    found = _CLAIM_RE.match(name)
    if not found:
        return None
    inode, digest, original = found.group(1), found.group(2), found.group(3)
    if original.startswith(".") or CLAIM_PREFIX in original:
        return None
    if _PAGE_NAME_RE.match(original):
        if segments.slug_problem(original[: -len(".md")]) is not None:
            return None
    elif not _CONFIRMATIONS_NAME_RE.match(original):
        return None
    return int(inode), digest, original


def _is_the_claimed_own(folder: int, claimed: str, inode: int, digest: str) -> bool:
    try:
        found = os.stat(claimed, dir_fd=folder, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISREG(found.st_mode) or found.st_ino != inode:
        return False
    try:
        handle = os.open(claimed, os.O_RDONLY | _NO_FOLLOW | _NONBLOCK, dir_fd=folder)
    except OSError:
        return False
    with os.fdopen(handle, "rb") as stream:
        if os.fstat(stream.fileno()).st_ino != inode:
            return False
        return hashlib.sha256(stream.read()).hexdigest()[:16] == digest


def _same_file(folder: int, one: str, other: str) -> bool:
    """Whether two names in a folder are the very same file on the disk."""
    try:
        first = os.stat(one, dir_fd=folder, follow_symlinks=False)
        second = os.stat(other, dir_fd=folder, follow_symlinks=False)
    except OSError:
        return False
    return (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)


def _put_back(folder: int, claimed: str, original: str) -> bool:
    """Give a claimed file that is not this run's its name back, or keep it aside.

    It goes back under its own name only when that name is free, so nothing
    put there since is written over. Otherwise it is kept beside it under a
    plain name that says so, never deleted, and the caller is told.
    """
    try:
        os.link(claimed, original, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
    except OSError:
        if _same_file(folder, claimed, original):
            # A run stopped between giving the file its name back and
            # letting go of the private name: the name already is this very
            # file, so only the private name goes, and no copy is kept
            # (Astra's second confirmation pass, finding 5).
            try:
                os.unlink(claimed, dir_fd=folder)
            except OSError:
                pass
            return True
        stem, dot, ending = original.rpartition(".")
        if not dot:
            stem, ending = original, ""
        for number in range(1, 1000):
            kept = "%s%s%d%s" % (stem, KEPT_MARK, number, ("." + ending) if ending else "")
            try:
                os.link(claimed, kept, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
            except FileExistsError:
                continue
            except OSError:
                return False
            try:
                os.unlink(claimed, dir_fd=folder)
            except OSError:
                pass
            return False
        return False
    try:
        os.unlink(claimed, dir_fd=folder)
    except OSError:
        pass
    return True


def _settle_claim(folder: int, claimed: str) -> None:
    """Settle a claim a stopped cleanup left: remove it if it is that run's own
    file, otherwise give it its name back, or keep it aside and say so."""
    parts = _claim_parts(claimed)
    if parts is None:
        return
    inode, digest, original = parts
    if _is_the_claimed_own(folder, claimed, inode, digest):
        try:
            os.unlink(claimed, dir_fd=folder)
        except OSError:
            pass
        return
    if not _put_back(folder, claimed, original):
        raise ReviewError(CODE_KEPT_ASIDE, code=CODE_KEPT_ASIDE)


def _remove_if_ours(base_root: str, relative: str, identity) -> bool:
    """Remove the file at a name only when it is the very file this run made.

    The name is first moved, in one step, to a private name nobody else uses,
    so whatever is looked at is exactly what will be removed: a file somebody
    puts at the page's name after that move is a different entry and is never
    touched (Astra's review of the merged units, finding 2). The private name
    carries who this run's file is and the hash of what it holds, so a run
    that stops after the move is settled by the next one. The moved file is
    removed only when it is this run's own; anything else goes back under its
    name, or, when that name has been taken again meanwhile, is kept beside it
    under a plain name and the caller is told, never left under the private
    name (Astra's confirmation pass on the merged units, finding 1).
    """
    if identity is None:
        return False
    parts = relative.split("/")
    if not DESCRIPTOR_WRITES:
        full = os.path.join(base_root, relative.replace("/", os.sep))
        try:
            found = os.lstat(full)
        except OSError:
            return False
        if (found.st_dev, found.st_ino) != tuple(identity)[:2] or not stat.S_ISREG(found.st_mode):
            return False
        return fsutil.remove(full)
    try:
        opened = _open_folders(base_root, parts[:-1], make=False)
    except (ReviewError, OSError):
        return False
    folder = opened[-1]
    claimed = _claim_name(identity, parts[-1])
    try:
        with fsutil.FolderLock(_real_folder(base_root, parts[:-1])):
            try:
                os.rename(parts[-1], claimed, src_dir_fd=folder, dst_dir_fd=folder)
            except OSError:
                return False
            try:
                found = os.stat(claimed, dir_fd=folder, follow_symlinks=False)
            except OSError:
                return False
            if (found.st_dev, found.st_ino) == tuple(identity)[:2] and stat.S_ISREG(
                found.st_mode
            ):
                try:
                    os.unlink(claimed, dir_fd=folder)
                except OSError:
                    # Left under its private name, which says it is this
                    # run's own, for the next sweep to remove.
                    return False
                return True
            if not _put_back(folder, claimed, parts[-1]):
                raise ReviewError(CODE_KEPT_ASIDE, code=CODE_KEPT_ASIDE)
            return False
    finally:
        _close_all(opened)


def _write(base_root: str, relative: str, text: str) -> str:
    """Put a new file down, only where nothing is, with no link followed."""
    _create_new(base_root, relative, text.encode("utf-8"))
    return os.path.join(base_root, relative.replace("/", os.sep))


def _stage(git: GitRunner, base_root: str, relative: str) -> None:
    try:
        git.check(["add", "--", relative], cwd=base_root)
    except Exception:
        raise ReviewError(CODE_GIT_FAILED)


def _save_it(git: GitRunner, base_root: str, relative: str) -> str:
    try:
        git.check(["commit", "-q", "-m", SAVE_MESSAGE % relative], cwd=base_root)
        return git.check(["rev-parse", "HEAD"], cwd=base_root).out()
    except Exception:
        raise ReviewError(CODE_GIT_FAILED)


def _write_and_save(base_root, base_id, relative, text, run_id, moment, git):
    """Write one file, add the line recording the yes, and save both together."""
    _write(base_root, relative, text)
    _stage(git, base_root, relative)

    codes: List[str] = []
    if relative.startswith(constants.CONTEXT_DIR + "/"):
        result = confirm.drafted(
            base_root, base_id, relative, run_id, now=moment, runner=git
        )
        if result.status != confirm.STATUS_RECORDED:
            raise ReviewError(
                (result.codes or [CODE_CONFIRMATION_REFUSED])[0],
                codes=list(result.codes or []),
            )
    else:
        codes.append(CODE_NO_DRAFTED_LINE)

    head = _save_it(git, base_root, relative)
    return ApproveResult(relative, head, codes, base_root, base_id)


def approve(
    draft,
    base_root: Optional[str],
    base_id: Optional[str],
    run_id: str,
    plugin_root: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    first_file: bool = False,
    parent: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    confirmed_home: bool = False,
    content_root: Optional[str] = None,
) -> ApproveResult:
    """Write an approved draft into the base, with the record of the yes.

    The first approved file has no base to go into yet, so it builds one. Every
    file after it is written into the base that already exists, onto the line of
    work the team shares, in one piece of saved work holding the file and the
    line together.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()

    if first_file:
        address = create_base.resolve_email(email, runner=git)
    else:
        if not base_root:
            raise ReviewError(CODE_NO_BASE)
        address = email or base_reader.repo_email(base_root, git) or ""
    if not address:
        # An empty owner line would leave a file nobody owns, and the check
        # that says whether a document is still current would have nobody to
        # compare against. Ask the person for the address instead.
        raise ReviewError(CODE_OWNER_MISSING, code=CODE_OWNER_MISSING)

    codes = screen(draft, address)
    if codes:
        raise ReviewError(CODE_SCREENED, codes=codes)

    if draft.step == drafting.STEP_CHANGE:
        # No run is written onto it. See `stamp_entry` for why. The identifier
        # is the first one no folder of this base already holds, because the
        # closing can be answered more than once and two changes under one
        # name is the state nothing here can resolve.
        draft = stamp_entry(
            draft, None, address, entry_name=free_entry_id(base_root)
        )
        try:
            canonical_affects(draft, base_root)
        except PathError as refusal:
            # A path climbing out of the base is a refusal the person should
            # hear in the same words as every other refusal, rather than as a
            # sentence saying something went wrong.
            code = refusal.code or CODE_BAD_AFFECTED_PATH
            raise ReviewError(code, code=code)
    else:
        draft = stamp_owner(draft, address)
    relative = path_for(draft, base_root)

    if first_file:
        result = create_base.create(
            parent,
            create_base.ApprovedFile(relative, draft.text),
            run_id,
            plugin_root,
            runner=git,
            now=moment,
            email=email,
            name=name,
            confirmed_home=confirmed_home,
            content_root=content_root,
        )
        head = git.run(["rev-parse", "HEAD"], cwd=result.root).out()
        return ApproveResult(
            relative, head, list(result.codes or []), result.root, result.base_id
        )

    ready_to_write(base_root, git)
    if draft.step == drafting.STEP_SEGMENT:
        _segment_file_is_free(base_root, relative)
    if _already_there(base_root, relative):
        raise ReviewError(CODE_FILE_EXISTS)
    return _write_and_save(
        base_root, base_id, relative, draft.text, run_id, moment, git
    )


def approve_adopted(
    base_root: str,
    base_id: Optional[str],
    relative: str,
    text: str,
    digest: str,
    run_id: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    email: Optional[str] = None,
) -> ApproveResult:
    """Write a finished page the person said yes to, bound to its exact bytes.

    Unit 1.7c. The page was cleaned and shown by `adopt`, and the person's yes
    is to the hash of exactly those bytes, so they are hashed again here and
    nothing is written unless they are the same. Everything a drafted segment
    meets before it is written, this meets too, in the same order: the screen
    over the whole file with only the owner's own line let through, the line
    of work the team shares with nothing else half done on it, an ordinary
    folder, no file already there whose name folds to the same one, and the
    page and the line recording the yes saved together as one piece of work.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    if not base_root:
        raise ReviewError(CODE_NO_BASE)
    address = email or base_reader.repo_email(base_root, git) or ""
    if not address:
        raise ReviewError(CODE_OWNER_MISSING, code=CODE_OWNER_MISSING)
    text = str(text)
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != str(digest or ""):
        raise ReviewError(CODE_NOT_WHAT_WAS_SHOWN, code=CODE_NOT_WHAT_WAS_SHOWN)
    codes = screen(text, address, frontmatter_line_numbers(text))
    if codes:
        raise ReviewError(CODE_SCREENED, codes=codes)
    # A write that stopped between putting its bytes down and naming them
    # leaves a temporary name behind, which is this plugin's own and goes.
    sweep_for_a_page(base_root, relative)
    ready_to_write(base_root, git)
    _segment_file_is_free(base_root, relative)
    if _already_there(base_root, relative):
        raise ReviewError(CODE_FILE_EXISTS)
    before = head_now(git, base_root)
    if before is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    data = text.encode("utf-8")
    confirmations = confirm.confirmations_path_for(relative)
    kept = fsutil.read_bytes(os.path.join(base_root, confirmations.replace("/", os.sep)))
    created = _create_new(base_root, relative, data)
    try:
        _still_the_page(base_root, relative, data, created)
        blob = _stage_bytes(git, base_root, relative, data)
        _add_the_line(base_root, base_id, relative, run_id, moment, git)
        # Checked once more at the last moment before the save, so the file
        # the person keeps is the one saved, and not something put there
        # after the bytes were staged.
        _still_the_page(base_root, relative, data, created)
    except Exception:
        # Nothing has been saved yet, so the page this run made, its staging
        # and the line recording the yes are all taken back, and the base is
        # exactly as it was before the yes (the unit's correctness review, C2).
        _take_back(git, base_root, relative, confirmations, kept, created)
        raise
    return _save_adopted(
        git, base_root, base_id, relative, blob, before, confirmations, kept, created
    )


# --- Saving an adopted page, and reading whether it was saved ----------------
#
# Astra's finding 5 on Unit 1.7c. A save can fail in a way that says nothing
# about whether it happened: the save itself can land and the question after
# it, which saved piece of work the base now stands at, can fail. Putting the
# page back then deleted a page the base had already saved. So after anything
# goes wrong at the save, what the base really holds is read. Saved: the work
# is done and nothing is touched. Plainly not saved, the base standing exactly
# where it stood: the page is taken back. Anything that cannot be read: nothing
# is touched at all, and the next attempt, or the next session, reads the base
# again and finishes or reports.

CODE_SAVE_UNCERTAIN = "save-outcome-unknown"
# The file at the page's name is no longer the file this run wrote there.
CODE_PAGE_REPLACED = "page-replaced"

LANDED = "landed"
NOT_LANDED = "not-landed"
UNKNOWN = "unknown"


def head_now(git: GitRunner, base_root: str) -> Optional[str]:
    found = git.run(["rev-parse", "--verify", "-q", "HEAD"], cwd=base_root)
    value = found.out() if found.ok else ""
    if len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value):
        return value
    return None


def blob_id(data: bytes) -> str:
    """The name git gives these exact bytes, worked out without asking git."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _stage_bytes(git: GitRunner, base_root: str, relative: str, data: bytes) -> str:
    """Stage exactly these bytes under this name, whatever sits on the disk.

    The bytes go to git from memory, and git's name for them is checked
    against the one worked out here, so what is staged is what was approved
    and never what a file happened to hold at the moment of staging.
    """
    expected = blob_id(data)
    stored = git.run(
        ["hash-object", "-w", "--stdin"], cwd=base_root, input=data.decode("utf-8")
    )
    if not stored.ok or stored.out() != expected:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    try:
        git.check(
            ["update-index", "--add", "--cacheinfo", "100644,%s,%s" % (expected, relative)],
            cwd=base_root,
        )
    except Exception:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    return expected


def _still_the_page(base_root: str, relative: str, data: bytes, identity) -> None:
    """Refuse unless the file at the name is the one written, holding these bytes."""
    found = installed(base_root, relative)
    if found is None or found[0] != data:
        raise ReviewError(CODE_PAGE_REPLACED, code=CODE_PAGE_REPLACED)
    if identity is not None and tuple(found[1]) != tuple(identity)[:2]:
        raise ReviewError(CODE_PAGE_REPLACED, code=CODE_PAGE_REPLACED)


def _add_the_line(base_root, base_id, relative, run_id, moment, git) -> None:
    result = confirm.drafted(base_root, base_id, relative, run_id, now=moment, runner=git)
    if result.status != confirm.STATUS_RECORDED:
        raise ReviewError(
            (result.codes or [CODE_CONFIRMATION_REFUSED])[0],
            codes=list(result.codes or []),
        )


def saved_state(git: GitRunner, base_root: str, relative: str, blob: str, before: str) -> str:
    """Whether the save holding this page landed, did not, or cannot be told.

    Landed: the base stands somewhere new and what it saved at the name is
    these very bytes. Not landed: the base stands exactly where it stood
    before. Anything else, including a question git would not answer, is
    unknown, and unknown is never treated as not landed.
    """
    head = head_now(git, base_root)
    if head is None:
        return UNKNOWN
    if head == before:
        return NOT_LANDED
    found = git.run(["rev-parse", "--verify", "-q", "HEAD:" + relative], cwd=base_root)
    if found.ok and found.out() == blob:
        return LANDED
    return UNKNOWN


def _save_adopted(git, base_root, base_id, relative, blob, before, confirmations, kept, created):
    """Save the staged page and its line, and settle what happened from the base."""
    failed = False
    try:
        git.check(["commit", "-q", "-m", SAVE_MESSAGE % relative], cwd=base_root)
    except Exception:
        failed = True
    outcome = saved_state(git, base_root, relative, blob, before)
    if outcome == LANDED:
        return ApproveResult(relative, head_now(git, base_root), [], base_root, base_id)
    if outcome == NOT_LANDED and failed:
        _take_back(git, base_root, relative, confirmations, kept, created)
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    raise ReviewError(CODE_SAVE_UNCERTAIN, code=CODE_SAVE_UNCERTAIN)


def _unstage(git: GitRunner, base_root: str, *names) -> bool:
    """Take names off the staging, and say whether git really did it."""
    return git.run(["reset", "-q", "--"] + list(names), cwd=base_root).ok


def _take_back(git, base_root, relative, confirmations, kept, created=None) -> None:
    """Put a base back as it was before one page was written into it.

    Only ever called while nothing has been saved. When git will not take the
    page and its line off the staging, nothing on the disk is touched either,
    so what is staged and what is on the disk never disagree, and the next
    attempt reads the base and finishes the page. Otherwise the page is
    removed only when the file at its name is still the very file this run
    created, and the line recording the yes goes back to what the file held
    before, written the way every file in a base is, with no link at its name
    followed.
    """
    if not _unstage(git, base_root, relative, confirmations):
        return
    _remove_if_ours(base_root, relative, created)
    held = os.path.join(base_root, confirmations.replace("/", os.sep))
    if kept is None:
        if os.path.lexists(held) and not os.path.isdir(held):
            fsutil.remove(held)
    else:
        fsutil.atomic_write_bytes(held, kept, mode=0o644, inside=base_root)


# --- Finishing a page an import stopped in the middle of (Unit 1.7d) ----------

# What one adopted page's name holds, read from the base itself.
PAGE_SAVED = "saved"
PAGE_WRITTEN = "written"
PAGE_ABSENT = "absent"
PAGE_EDITED = "edited-before-the-save"
PAGE_OTHER = "other-bytes"
# Saved by somebody, with no line recording the yes of this import's run.
PAGE_SAVED_UNCONFIRMED = "saved-without-its-line"
# The states in which a page with a yes is finished from what is there.
PAGES_TO_FINISH = (PAGE_SAVED, PAGE_SAVED_UNCONFIRMED, PAGE_WRITTEN)


def _text_at(git: GitRunner, base_root: str, spec: str) -> Optional[str]:
    found = git.run(["cat-file", "-p", spec], cwd=base_root)
    return found.stdout if found.ok else None


def _text_at_head(git: GitRunner, base_root: str, relative: str) -> Optional[str]:
    return _text_at(git, base_root, "HEAD:" + relative)


def held_at_head(git: GitRunner, base_root: str, relative: str) -> bool:
    """Whether the saved work the base stands at holds anything at this name."""
    return _text_at_head(git, base_root, relative) is not None


def _digest_of(text: Optional[str]) -> Optional[str]:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None


def _saved_once(git: GitRunner, base_root: str, relative: str, digest: str) -> bool:
    """Whether any saved piece of work on this line ever held these bytes at the name.

    A page this import saved and the person edited afterward, by a prepared
    change or by hand, was still saved by this import, and is never reported
    as a page that was not.
    """
    found = git.run(["log", "--format=%H", "--", relative], cwd=base_root)
    if not found.ok:
        return False
    for saved in found.out().split():
        if _digest_of(_text_at(git, base_root, "%s:%s" % (saved, relative))) == digest:
            return True
    return False


def _staged_is_ours(git: GitRunner, base_root: str, relative: str, digest: str) -> bool:
    """Whether what is staged at the name is exactly the approved bytes."""
    return _digest_of(_text_at(git, base_root, ":" + relative)) == digest


def _drafted_lines_at_head(git: GitRunner, base_root: str, relative: str):
    saved = _text_at_head(git, base_root, confirm.confirmations_path_for(relative))
    found, _bad = formats.parse_confirmations_file(saved or "")
    return [line for line in found if line.trigger == "drafted" and line.file == relative]


def page_state(
    git: GitRunner, base_root: str, relative: str, digest: str, run: Optional[str] = None
) -> str:
    """How far one page with a yes got, read from what the base holds.

    Saved: some saved piece of work held these bytes at the name, whatever the
    name holds now, and, when `run` is given, the saved line recording the yes
    names that run. Saved without its line: the bytes were saved, by another
    window saving what was staged, and no line recording the yes was saved
    with them (Astra's review of the merged units, finding 4). Written: the
    bytes sit at the name, unsaved, staged or not, with its line or not.
    Edited before the save: this import staged or recorded the page, and the
    file at the name was changed before the save. Absent: nothing at the name
    and nothing saved there. Other bytes: something else is at the name, or a
    line for another run was saved for it, which is never written over.
    """
    if _saved_once(git, base_root, relative, digest):
        if run is None:
            return PAGE_SAVED
        lines = _drafted_lines_at_head(git, base_root, relative)
        if not lines:
            return PAGE_SAVED_UNCONFIRMED
        if any(line.run == run for line in lines):
            return PAGE_SAVED
        return PAGE_OTHER
    if _text_at_head(git, base_root, relative) is not None:
        return PAGE_OTHER
    here = installed(base_root, relative)
    full = os.path.join(base_root, relative.replace("/", os.sep))
    if here is None:
        return PAGE_OTHER if os.path.lexists(full) else PAGE_ABSENT
    if hashlib.sha256(here[0]).hexdigest() == digest:
        return PAGE_WRITTEN
    if _staged_is_ours(git, base_root, relative, digest) or (
        _line_state(git, base_root, relative) == "ours"
    ):
        return PAGE_EDITED
    return PAGE_OTHER


def _line_state(git: GitRunner, base_root: str, relative: str) -> str:
    """Whether the page's confirmations file is as saved, holds this run's line, or neither.

    This run's line is exactly one line added at the end of what was saved:
    the line setting up writes when a file is written, naming this page.
    """
    confirmations = confirm.confirmations_path_for(relative)
    saved = _text_at_head(git, base_root, confirmations)
    now = fsutil.read_text_exactly(
        os.path.join(base_root, confirmations.replace("/", os.sep))
    )
    if now == saved:
        return "as-saved"
    if now is None:
        return "other"
    if saved is None:
        prefix = confirm.FILE_HEADER
    elif saved and not saved.endswith("\n"):
        prefix = saved + "\n"
    else:
        prefix = saved
    if not now.startswith(prefix):
        return "other"
    added = now[len(prefix):]
    if not added.endswith("\n") or "\n" in added[:-1]:
        return "other"
    try:
        line = formats.ConfirmationLine.parse(added.strip())
    except Exception:
        return "other"
    if line.trigger != "drafted" or line.file != relative:
        return "other"
    return "ours"


def _only_this_pages_edits(git: GitRunner, base_root: str, relative: str) -> str:
    """The state of the page's line, when nothing but this page is half done.

    Anything else unsaved in the base is the person's, and is refused, apart
    from the temporary names a stopped write leaves, which are swept first.
    """
    confirmations = confirm.confirmations_path_for(relative)
    sweep_for_a_page(base_root, relative)
    status = git.run(["status", "--porcelain", "-z", "--untracked-files=all"], cwd=base_root)
    entries = status_entries(status.stdout) if status.ok else None
    if entries is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    for _letters, named in entries:
        if any(name not in (relative, confirmations) for name in named):
            raise ReviewError(CODE_UNSAVED_EDITS, code=CODE_UNSAVED_EDITS)
    line = _line_state(git, base_root, relative)
    if line == "other":
        raise ReviewError(CODE_UNSAVED_EDITS, code=CODE_UNSAVED_EDITS)
    return line


def _restore_line(git: GitRunner, base_root: str, relative: str, line: str) -> None:
    """Put this run's own line back to what was saved, and nothing else."""
    if line != "ours":
        return
    confirmations = confirm.confirmations_path_for(relative)
    saved = _text_at_head(git, base_root, confirmations)
    held = os.path.join(base_root, confirmations.replace("/", os.sep))
    if saved is None:
        fsutil.remove(held)
    else:
        fsutil.atomic_write_bytes(held, saved.encode("utf-8"), mode=0o644, inside=base_root)


def put_back_unwritten(base_root: str, relative: str, runner: Optional[GitRunner] = None) -> None:
    """Clear what an import left of a page that is no longer at its name.

    Only this page's staging and this run's own line are taken back, and only
    when nothing else is half done in the base.
    """
    git = runner_or_default(runner)
    line = _only_this_pages_edits(git, base_root, relative)
    status = git.run(["status", "--porcelain", "-z", "--untracked-files=all"], cwd=base_root)
    if status.ok and not status.stdout.strip("\0"):
        # Nothing is half done at all, which is the ordinary case.
        return
    confirmations = confirm.confirmations_path_for(relative)
    if not _unstage(git, base_root, relative, confirmations):
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    _restore_line(git, base_root, relative, line)


def take_back_unsaved(
    base_root: str, relative: str, digest: str, runner: Optional[GitRunner] = None
) -> None:
    """Take back what an import did toward a page that was never saved.

    Its staging and its own line are taken back. The file at the name is
    removed only when it still holds exactly the approved bytes, which this
    import wrote; a file changed since is the person's, and stays. Nothing is
    done while anything else is half done in the base.
    """
    git = runner_or_default(runner)
    if _saved_once(git, base_root, relative, digest):
        return
    confirmations = confirm.confirmations_path_for(relative)
    sweep_for_a_page(base_root, relative)
    status = git.run(["status", "--porcelain", "-z", "--untracked-files=all"], cwd=base_root)
    entries = status_entries(status.stdout) if status.ok else None
    if entries is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    for _letters, named in entries:
        if any(name not in (relative, confirmations) for name in named):
            raise ReviewError(CODE_UNSAVED_EDITS, code=CODE_UNSAVED_EDITS)
    line = _line_state(git, base_root, relative)
    if not _unstage(git, base_root, relative, confirmations):
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    _restore_line(git, base_root, relative, line)
    here = installed(base_root, relative)
    if here is not None and hashlib.sha256(here[0]).hexdigest() == digest:
        _remove_if_ours(
            base_root, relative, tuple(here[1]) + (hashlib.sha256(here[0]).hexdigest(),)
        )


def confirm_saved(
    base_root: str,
    base_id: Optional[str],
    relative: str,
    run_id: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> ApproveResult:
    """Add and save the line recording the yes to a page already saved without it.

    Another window can save what an import had staged before the import added
    the line recording the yes. The page is then saved and nobody's yes is,
    which is not a finished adoption. The line is added now, naming the
    import's own run, and saved on its own; nothing else in the base is
    touched, and a base with anything else half done is refused.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    if isinstance(moment, datetime.date) and not isinstance(moment, datetime.datetime):
        moment = datetime.datetime(moment.year, moment.month, moment.day)
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        raise ReviewError(CODE_NOT_DEFAULT_BRANCH, code=CODE_NOT_DEFAULT_BRANCH)
    confirmations = confirm.confirmations_path_for(relative)
    sweep_for_a_page(base_root, relative)
    status = git.run(["status", "--porcelain", "-z", "--untracked-files=all"], cwd=base_root)
    entries = status_entries(status.stdout) if status.ok else None
    if entries is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    for _letters, named in entries:
        if any(name != confirmations for name in named):
            raise ReviewError(CODE_UNSAVED_EDITS, code=CODE_UNSAVED_EDITS)
    line = _line_state(git, base_root, relative)
    if line == "other":
        raise ReviewError(CODE_UNSAVED_EDITS, code=CODE_UNSAVED_EDITS)
    before = head_now(git, base_root)
    if before is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    held = os.path.join(base_root, confirmations.replace("/", os.sep))
    kept = _text_at_head(git, base_root, confirmations)
    if line == "as-saved":
        today = state.today(moment)
        recorded = formats.ConfirmationLine(
            date=today.isoformat(),
            time=moment.strftime("%H:%M:%SZ"),
            file=relative,
            trigger="drafted",
            entry=None,
            question=None,
            run=run_id,
        )
        recorded.validate()
        confirm._append_line(base_root, confirmations, recorded)
    failed = False
    try:
        git.check(["add", "--", confirmations], cwd=base_root)
        git.check(
            ["commit", "-q", "-m", CONFIRM_SAVED_MESSAGE % relative, "--", confirmations],
            cwd=base_root,
        )
    except Exception:
        failed = True
    head = head_now(git, base_root)
    if head is not None and head != before and any(
        found.run == run_id for found in _drafted_lines_at_head(git, base_root, relative)
    ):
        return ApproveResult(relative, head, [], base_root, base_id)
    if head == before and failed:
        if _unstage(git, base_root, confirmations):
            if kept is None:
                fsutil.remove(held)
            else:
                fsutil.atomic_write_bytes(held, kept.encode("utf-8"), mode=0o644, inside=base_root)
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    raise ReviewError(CODE_SAVE_UNCERTAIN, code=CODE_SAVE_UNCERTAIN)


def finish_adopted(
    base_root: str,
    base_id: Optional[str],
    relative: str,
    digest: str,
    run_id: str,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
    email: Optional[str] = None,
) -> ApproveResult:
    """Finish a page an import wrote and did not save, from the bytes at its name.

    The page is finished only when the bytes at its name are exactly the ones
    the person said yes to, the base is on its main line, and nothing but this
    page and its own line is half done. It is staged from those bytes, given
    its line unless this run already added it, and saved. The page is never
    taken away here: it was not made by this call, and it is the page the
    person approved.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    address = email or base_reader.repo_email(base_root, git) or ""
    if not address:
        raise ReviewError(CODE_OWNER_MISSING, code=CODE_OWNER_MISSING)
    on_default, _code = paths.head_is_default_branch(base_root, runner=git)
    if not on_default:
        raise ReviewError(CODE_NOT_DEFAULT_BRANCH, code=CODE_NOT_DEFAULT_BRANCH)
    if not segments.folder_is_ordinary(base_root):
        raise ReviewError(
            segments.CODE_FOLDER_NOT_ORDINARY, code=segments.CODE_FOLDER_NOT_ORDINARY
        )
    found = installed(base_root, relative)
    if found is None or hashlib.sha256(found[0]).hexdigest() != str(digest or ""):
        raise ReviewError(segments.CODE_FILE_TAKEN, code=segments.CODE_FILE_TAKEN)
    data, identity = found
    text = data.decode("utf-8")
    codes = screen(text, address, frontmatter_line_numbers(text))
    if codes:
        raise ReviewError(CODE_SCREENED, codes=codes)
    line = _only_this_pages_edits(git, base_root, relative)
    before = head_now(git, base_root)
    if before is None:
        raise ReviewError(CODE_GIT_FAILED, code=CODE_GIT_FAILED)
    confirmations = confirm.confirmations_path_for(relative)
    kept = fsutil.read_bytes(os.path.join(base_root, confirmations.replace("/", os.sep)))
    try:
        blob = _stage_bytes(git, base_root, relative, data)
        if line == "ours":
            git.check(["add", "--", confirmations], cwd=base_root)
        else:
            _add_the_line(base_root, base_id, relative, run_id, moment, git)
        _still_the_page(base_root, relative, data, identity)
    except Exception:
        # Taken back to where this call found it: unstaged, and the line file
        # as it was. The page stays, because this call did not make it.
        if _unstage(git, base_root, relative, confirmations):
            held = os.path.join(base_root, confirmations.replace("/", os.sep))
            if kept is None:
                fsutil.remove(held)
            else:
                fsutil.atomic_write_bytes(held, kept, mode=0o644, inside=base_root)
        raise
    return _save_adopted(
        git, base_root, base_id, relative, blob, before, confirmations, kept, None
    )


def skip(
    step: str,
    base_root: str,
    base_id: Optional[str] = None,
    owner_email: Optional[str] = None,
    runner: Optional[GitRunner] = None,
    now: Optional[datetime.datetime] = None,
) -> ApproveResult:
    """Write the file a skipped step leaves behind, and save it.

    There is no line saying anybody approved it, because nobody did. The file
    says `skipped`, which is what makes the next session offer to finish setting
    the base up rather than treat it as done.
    """
    git = runner_or_default(runner)
    moment = now or state.now_utc()
    if not base_root:
        raise ReviewError(CODE_NO_BASE)
    address = owner_email or base_reader.repo_email(base_root, git) or ""
    if step not in drafting.SKIPPED_HEADINGS:
        # Only the two required documents are ever written down as skipped. A
        # segment the person does not want is left out, which writes nothing.
        raise ReviewError("cannot-skip", code="cannot-skip")
    relative = (
        drafting.ICP_PATH if step == drafting.STEP_ICP else drafting.POSITIONING_PATH
    )
    text = drafting.skipped_text(step, address, state.today(moment).isoformat())

    ready_to_write(base_root, git)
    if _already_there(base_root, relative):
        raise ReviewError(CODE_FILE_EXISTS)
    _write(base_root, relative, text)
    _stage(git, base_root, relative)
    head = _save_it(git, base_root, relative)
    return ApproveResult(relative, head, [], base_root, base_id)
