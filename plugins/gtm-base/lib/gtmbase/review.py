"""Looking at a draft with the person, and writing it down when they say yes.

Four answers end a step. Approve writes the draft into the base. Edit takes the
person's own rewrite and reads it back through the same checks. Skip writes a
file that says it was skipped, so nothing downstream mistakes an absence for a
decision. "What is wrong with this?" asks for the whole draft again with their
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
import os
from typing import List, Optional

from . import (
    base_reader,
    confirm,
    constants,
    create_base,
    drafting,
    formats,
    ids,
    paths,
    redaction_patterns,
    scan,
    state,
)
from .errors import PathError, ReviewError
from .gitcmd import GitRunner, runner_or_default

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
# definition, and the one decision entry setup writes is not one.
CODE_NO_DRAFTED_LINE = "no-drafted-line"
# No address could be found for the person who owns this base, so there is
# nobody to write on the owner line and nobody for the currency check to
# compare against later.
CODE_OWNER_MISSING = "owner-missing"
# A decision entry named a file it may not name, and the path itself said why.
CODE_BAD_AFFECTED_PATH = "bad-affected-path"

# What the saved work is called when a file is written during setup.
SAVE_MESSAGE = "Add %s from setup"

# The settings lines this plugin writes the base's own address onto a moment
# after the screen runs. Whatever a draft put on one of them is replaced, so
# reading them as a leak would only ever refuse the plugin's own value.
_OWNER_KEYS = ("owner", "owner_handle", "decided_by")
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
    decision entry's `decided_by` gets through while a prospect's address in
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
    return drafting.parse(draft.step, _fenced(formats.render_document(fields, body)))


def stamp_owner(draft, owner_email: str):
    """Put the base's own address on a draft, and read the draft back again.

    The profile and the positioning carry an `owner`. The decision entry
    carries `decided_by` instead, which is the same person saying the same
    thing about the same base, so it is stamped the same way.

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


# --- The decision entry ------------------------------------------------------


def _affects_of(draft) -> List[str]:
    value = draft.fields.get("affects", [])
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def canonical_affects(draft, base_root: Optional[str] = None) -> List[str]:
    """The files a decision entry says it affects, each one checked.

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
    """The name of the decision entry setup writes.

    It is worked out here and never read off the draft, because an identifier a
    model wrote is an identifier nobody can work out again.
    """
    return ids.staging_id("join", drafting.ICP_PATH, "join", sequence)


def stamp_entry(draft, run_id: str, owner_email: str, sequence: int = 0):
    """Put this plugin's own identifiers on a decision entry.

    The identifier, where it came from, and the run are all set here, over
    whatever the draft said, so the entry a person approves is the entry the
    rest of the plugin can find again.
    """
    block, body = formats.split_document(draft.text)
    fields = formats.parse_frontmatter(block)
    fields["id"] = entry_id(sequence)
    fields["origin"] = "join"
    fields["run_id"] = run_id
    if owner_email:
        fields["decided_by"] = owner_email
    return _reparse(draft, fields, body)


def entry_path(draft) -> str:
    """Where the decision entry is written."""
    return constants.DECISIONS_DIR + "/" + str(draft.fields["id"]) + ".md"


def path_for(draft) -> str:
    """Where in the base a draft belongs, whichever step it came from."""
    if draft.step == drafting.STEP_LEDGER:
        return entry_path(draft)
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


def _write(base_root: str, relative: str, text: str) -> str:
    full = os.path.join(base_root, relative.replace("/", os.sep))
    folder = os.path.dirname(full)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(full, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return full


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

    if draft.step == drafting.STEP_LEDGER:
        draft = stamp_entry(draft, run_id, address)
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
    relative = path_for(draft)

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
        )
        head = git.run(["rev-parse", "HEAD"], cwd=result.root).out()
        return ApproveResult(
            relative, head, list(result.codes or []), result.root, result.base_id
        )

    ready_to_write(base_root, git)
    if os.path.lexists(os.path.join(base_root, relative.replace("/", os.sep))):
        raise ReviewError(CODE_FILE_EXISTS)
    return _write_and_save(
        base_root, base_id, relative, draft.text, run_id, moment, git
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
    relative = (
        drafting.ICP_PATH if step == drafting.STEP_ICP else drafting.POSITIONING_PATH
    )
    text = drafting.skipped_text(step, address, state.today(moment).isoformat())

    ready_to_write(base_root, git)
    if os.path.lexists(os.path.join(base_root, relative.replace("/", os.sep))):
        raise ReviewError(CODE_FILE_EXISTS)
    _write(base_root, relative, text)
    _stage(git, base_root, relative)
    head = _save_it(git, base_root, relative)
    return ApproveResult(relative, head, [], base_root, base_id)
