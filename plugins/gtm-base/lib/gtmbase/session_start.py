"""What GTM Base does at the start of a session, before the first prompt.

Four things can happen here, and exactly one of them happens per session.

1. The current folder is a base this account has opened before. The session is
   recorded, and once a day's work begins (a session that started fresh or was
   picked up again) the base is brought up to date with the shared copy, the
   map is added to the session, and at most one file's owner is asked to say
   their file is still right.
2. The folder looks like a base but this account has never opened it. Nothing
   is read or installed. The whole folder is checked for anything that would
   run on trusting it, and only then is the person asked whether this is their
   company's base.
3. The folder holds more than one base folder. One sentence says so.
4. Nothing here is a base. The person is offered a base of their own, once.

Everything a person sees is fixed text held in `templates/`, so the words can
be reviewed in one place. Nothing here ever prints an address that carries a
sign in, an option a person typed, or anything git wrote to its error stream.

The work is done in two parts, because a client reads a hook's output either as
one JSON object or as plain text and never as both. The first part prints only
the sentence the person sees, as one object holding that message. It writes
nothing at all and reaches nothing over the network. The second part prints
only the text the assistant reads, as plain text, and it is the one that
records the session, brings the base up to date, issues the question id, and
installs the safeguard. Both parts work the same decision out from the same
inputs, so what the person is told and what the assistant is primed with always
agree.

The client runs the two parts at the same time rather than one after the other,
so neither part may rely on the other having finished. That is why the part
that prints what a person sees decides the setup offer from the kind of session
this is: a session that started fresh has not been offered anything yet,
whatever the other part has written down by the time this one looks.

One sentence cannot be worked out without reaching the shared copy: the one
saying an update carried files GTM Base does not take on its own. The part that
reaches out records a fixed code in this seat's own settings when that happens,
and the first part of the next session says the sentence while the second part
clears the code once its own work is done. That sentence therefore arrives one
session late, which is the price of never reaching the network before a person
is shown anything.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Union

from . import (
    base_reader,
    constants,
    ids,
    install_git_hook,
    machine,
    paths,
    stale,
    state,
    trust_surface,
)
from .errors import PathError, ValidationError
from .fsutil import read_text
from .gitcmd import GitRunner, runner_or_default

# The two sources that mean a person is starting work, not continuing a turn.
WORKING_SOURCES = ("startup", "resume")

# The source that means this session has only just begun. A session id sees it
# once, which is what lets the part that prints what a person sees decide the
# offer without waiting on the part that writes the record.
FRESH_SOURCE = "startup"

# The two halves of the session start. The first prints only what the person
# sees; the second prints only what the assistant reads and is the one of the
# two that writes anything down.
SESSION_START_PARTS = ("visible", "context")

# How long a local git call inside the hook may take.
LOCAL_TIMEOUT_SECONDS = 5

# The one script allowed to write a confirmation line. The injected question
# names it, so the assistant runs it rather than writing the record itself.
CONFIRM_SCRIPT = "scripts/confirm.py"

# What one seat records when the shared copy carried something it will not take.
CODE_PULL_REFUSED = "pull-refused-paths"

# --- The fixed sentences ----------------------------------------------------

NOT_DEFAULT_BRANCH = (
    "Your base is not on its main line right now, so nothing was updated. "
    "Ask GTM Base to put it back."
)
DIRTY_TREE = "You have unsaved edits in your base, so nothing was updated this time."
UNREACHABLE = (
    "GTM Base could not reach the shared copy, so you are seeing the base as "
    "of %s."
)
COULD_NOT_UPDATE = (
    "GTM Base could not bring this base up to date on its own, so you are "
    "seeing the base as of %s."
)
PULL_REFUSED = (
    "The shared copy contains changes to files GTM Base does not update on "
    "its own. Ask the owner to review them by hand."
)
TRUST_FAILED = (
    "This folder looks like a base but it carries files GTM Base does not "
    "accept (%s), so it was not opened."
)
COPY_FOUND = (
    "This folder is a copy of a base already joined at %s. To use this copy "
    "separately, say: give this copy its own id."
)
MULTIPLE_CHILDREN = (
    "This folder holds more than one base folder, named %s and %s, so GTM "
    "Base did nothing here."
)
AS_OF = "You are seeing the base as of %s."
TRUST_AFTER_UPDATE = (
    "The update from the shared copy left this base holding files GTM Base "
    "does not accept. Ask the owner to look at it."
)

NO_REMOTE_TEXT = "no remote"
NO_EMAIL_TEXT = "none set"

_DATE_IN_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")
# A file name from the shared copy is only ever shown when it is made of these.
_PLAIN_FILE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
# The longest run of backward quotes anywhere in a piece of text.
_BACKTICK_RUN = re.compile(r"`+")
_BLAME_HEADER = re.compile(r"^[0-9a-f]{7,40} \d+ (\d+)(?: \d+)?$")


# --- The output shape -------------------------------------------------------


def render_output(
    context_text: Optional[str], visible_text: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Build the combined object, or nothing at all.

    The combined form carries both halves in one object. It was tried live on
    2026-09-06 and the message never appeared on screen, so the plugin ships
    the two parts below instead. This is kept for a client that renders it, and
    is what the default part still produces.
    """
    payload: Dict[str, Any] = {}
    if context_text:
        payload["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": context_text[: constants.MAX_INJECTION_CHARS],
        }
    if visible_text:
        payload["systemMessage"] = visible_text
    return payload or None


class _Part(object):
    """Which half of the session start this run is doing.

    "visible" prints only the sentence the person reads and writes nothing at
    all: no session record, no offer record, no question id, no asked line, no
    update from the shared copy, and no safeguard installed. "context" prints
    only the text the assistant reads and does everything that is written down.
    "both" is the combined form above, and is what a caller naming no part gets.
    """

    __slots__ = ("name",)

    def __init__(self, name: Optional[str] = None):
        self.name = name if name in SESSION_START_PARTS + ("both",) else "both"

    @property
    def writes(self) -> bool:
        """Whether this part may write anything down."""
        return self.name != "visible"

    @property
    def reaches_out(self) -> bool:
        """Whether this part may reach the shared copy."""
        return self.name != "visible"

    def __repr__(self) -> str:
        return "_Part(%r)" % (self.name,)


def _render(
    part: _Part, context_text: Optional[str], visible_text: Optional[str]
) -> Union[Dict[str, Any], str, None]:
    """What this part prints, which is at most one of the two halves.

    The visible part prints one object holding the message. The context part
    prints plain text, because a client reads a hook's output as one object or
    as plain text by its first character, and never as both.
    """
    if part.name == "visible":
        return {"systemMessage": visible_text} if visible_text else None
    if part.name == "context":
        if not context_text:
            return None
        return context_text[: constants.MAX_INJECTION_CHARS]
    return render_output(context_text, visible_text)


# --- Templates --------------------------------------------------------------


def find_plugin_root(explicit: Optional[str] = None) -> str:
    """The folder the plugin was installed into, however the caller found it."""
    if explicit:
        return explicit
    named = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if named and os.path.isdir(named):
        return named
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def load_blocks(root: str, name: str) -> Dict[str, str]:
    """Read one template into its named blocks, comments left out."""
    text = read_text(os.path.join(root, "templates", name))
    if text is None:
        return {}
    blocks: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("[[block:") and stripped.endswith("]]"):
            current = stripped[len("[[block:") : -2].strip()
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(line)
    return {name: "\n".join(lines).strip("\n") for name, lines in blocks.items()}


def fill(text: str, values: Dict[str, Any]) -> str:
    """Put the values into a fixed template, one place at a time."""
    filled = text
    for key, value in values.items():
        filled = filled.replace("{{%s}}" % key, "" if value is None else str(value))
    return filled


# --- The entry points -------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """Read the session from standard input and print at most one thing.

    The two hook entries pass "visible" and "context". The visible one prints
    one JSON object holding the message; the context one prints plain text.
    """
    client = "claude"
    part = "both"
    args = list(argv or [])
    if "--client" in args:
        position = args.index("--client")
        if position + 1 < len(args):
            client = args[position + 1]
    if "--part" in args:
        position = args.index("--part")
        if position + 1 < len(args):
            part = args[position + 1]
    if client not in constants.CLIENTS:
        client = "claude"
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        result = run(payload, client=client, part=part)
    except Exception:
        return 0
    if isinstance(result, str):
        sys.stdout.write(result + "\n")
    elif result:
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
    return 0


class _Environment(object):
    """Put a caller's environment in place for the length of one run."""

    def __init__(self, values: Optional[Dict[str, str]]):
        self.values = values or {}
        self.saved: Dict[str, Optional[str]] = {}

    def __enter__(self):
        for name, value in self.values.items():
            self.saved[name] = os.environ.get(name)
            os.environ[name] = value
        return self

    def __exit__(self, kind, value, trace):
        for name, previous in self.saved.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous
        return False


def run(
    payload: Dict[str, Any],
    client: str = "claude",
    now: Optional[datetime.datetime] = None,
    runner: Optional[GitRunner] = None,
    plugin_root: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    part: str = "both",
) -> Union[Dict[str, Any], str, None]:
    """Everything the hook decides, from values the caller hands in.

    An object comes back for the visible part and for the combined form, plain
    text for the context part, and nothing at all when there is nothing to say.
    """
    with _Environment(env):
        return _run(
            payload,
            client if client in constants.CLIENTS else "claude",
            now or state.now_utc(),
            runner_or_default(runner),
            find_plugin_root(plugin_root),
            _Part(part),
        )


def _run(payload, client, now, git, root_of_plugin, part):
    session_id = payload.get("session_id")
    source = payload.get("source")
    cwd = payload.get("cwd")
    if not isinstance(session_id, str):
        session_id = ""
    if not isinstance(source, str):
        source = ""
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        cwd = os.getcwd()

    account = machine.load_machine_state(git)
    resolution = paths.resolve_base(cwd, account, runner=git)

    if resolution.code == paths.CODE_MULTIPLE_CHILDREN:
        names = _child_base_names(cwd)
        first = names[0] if names else "gtm-base"
        second = names[1] if len(names) > 1 else "gtm-base"
        return _render(part, None, MULTIPLE_CHILDREN % (first, second))

    if resolution.code == paths.CODE_JOINED:
        if part.writes:
            state.update_seat(resolution.base_id, session_id=session_id, client=client)
        if source not in WORKING_SOURCES:
            return None
        return _daily_block(
            resolution.root,
            resolution.base_id,
            session_id,
            now,
            git,
            root_of_plugin,
            part,
        )

    if resolution.code in (paths.CODE_BASE_SHAPED, paths.CODE_UNJOINED):
        # This branch runs on every source, not only on the two that start a
        # day's work, because a base whose folder was renamed is picked up
        # again here and the session it belongs to has to be recorded whatever
        # started the session.
        return _base_shaped(
            resolution.root, client, session_id, now, git, root_of_plugin, source, part
        )

    if source not in WORKING_SOURCES:
        return None

    return _offer(cwd, account, session_id, source, now, git, root_of_plugin, part)


# --- The folder that looks like a base --------------------------------------


def _child_base_names(cwd: str) -> List[str]:
    """The names of every folder inside this one that is called gtm-base."""
    try:
        entries = sorted(os.listdir(cwd))
    except OSError:
        return []
    wanted = "gtm-base".casefold()
    return [
        name
        for name in entries
        if name.casefold() == wanted and os.path.isdir(os.path.join(cwd, name))
    ]


def safe_origin(address: Optional[str]) -> str:
    """A remote address as a person may see it, or the words for having none."""
    if not address:
        return NO_REMOTE_TEXT
    cleaned = "".join(
        character
        for character in str(address)
        if ord(character) >= 32 and ord(character) != 127
    ).strip()
    cleaned = ids.strip_userinfo(cleaned) if cleaned else cleaned
    if not cleaned:
        return NO_REMOTE_TEXT
    return cleaned[: constants.MAX_ORIGIN_CHARS]


def _repo_email(root: str, git: GitRunner) -> Optional[str]:
    """The address this folder records for the person working in it."""
    return base_reader.repo_email(root, git)


def _base_shaped(root, client, session_id, now, git, root_of_plugin, source, part):
    working = source in WORKING_SOURCES
    verdict = trust_surface.check(root, runner=git)
    if not verdict.ok:
        if not working:
            return None
        return _render(part, None, TRUST_FAILED % trust_surface.describe(verdict.codes))

    base_id = paths.read_base_id(root, runner=git)
    if base_id:
        raw = machine.load_machine_state_raw()
        entry = machine.find_joined_by_id(raw, base_id)
        if entry is not None:
            old_root = entry.get("root")
            known = bool(old_root) and os.path.isdir(old_root)
            if known and os.path.realpath(old_root) != os.path.realpath(root):
                return _render(part, None, COPY_FOUND % old_root) if working else None
            if not known:
                if part.writes:
                    machine.rewrite_joined_root(base_id, root)
                    state.update_seat(base_id, session_id=session_id, client=client)
                if not working:
                    return None
                return _daily_block(
                    root, base_id, session_id, now, git, root_of_plugin, part
                )

    if not working:
        return None

    blocks = load_blocks(root_of_plugin, "base-shaped-question.md")
    if not blocks:
        return None
    values = {
        "origin": safe_origin(paths.remote_url(root, runner=git)),
        "email": _repo_email(root, git) or NO_EMAIL_TEXT,
    }
    return _render(
        part,
        fill(blocks.get("context", ""), values),
        fill(blocks.get("visible", ""), values),
    )


# --- The offer --------------------------------------------------------------


def _folder_is_empty(cwd: str) -> bool:
    try:
        entries = os.listdir(cwd)
    except OSError:
        return False
    return not [name for name in entries if name != ".DS_Store"]


def _offer(cwd, account, session_id, source, now, git, root_of_plugin, part):
    if account.joined:
        return None
    if account.answer in ("set-up", "join"):
        return None
    if _other_part_is_offering(account, session_id, source, part):
        show = True
    elif machine.offer_was_shown_this_session(account, session_id):
        return None
    else:
        shown_before = bool(account.offer.get("shown_at"))
        if account.answer == "unset" and not shown_before:
            show = True
        else:
            show = _folder_is_empty(cwd)
    if not show:
        return None
    blocks = load_blocks(root_of_plugin, "offer.md")
    if not blocks:
        return None
    if part.writes:
        machine.record_offer_shown(session_id, now)
    return _render(part, blocks.get("context", ""), blocks.get("visible", ""))


def _other_part_is_offering(account, session_id, source, part):
    """Whether the part that writes is making the offer in this same session.

    The client runs the two parts at the same time, so the part that prints
    what a person sees cannot tell a record left by an earlier session from one
    the other part left a moment ago, and going quiet on the second would mean
    the offer never appears at all. It does not have to tell them apart. This
    session's own record is only ever written by a run that decided to make the
    offer, and a session id sees exactly one fresh start, so a record carrying
    this session id on a fresh start means the offer is being made right now and
    this part is the half of it the person reads.
    """
    if part.writes or source != FRESH_SOURCE:
        return False
    return machine.offer_was_shown_this_session(account, session_id)


# --- The daily block --------------------------------------------------------


def _as_of(root: str, git: GitRunner) -> str:
    """The day the base was last changed, which is what "as of" means here."""
    result = git.run(
        ["log", "-1", "--format=%cd", "--date=short"],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    value = result.out() if result.ok else ""
    return value if _DATE_IN_TEXT.match(value) else state.today().isoformat()


def _map_text(root: str) -> str:
    return base_reader.map_text(root)


def _settings_of(map_text: str) -> stale.MapSettings:
    return base_reader.settings_of(map_text)


def _is_refused_path(path: str) -> bool:
    """Whether an incoming change to this path is one no update may carry.

    The answer is the trust surface's own answer, so the set of names a folder
    may not hold and the set an update may not carry are the one set, compared
    the one way: after case folding and after Unicode composition.
    """
    cleaned = path.strip().replace("\\", "/")
    if not cleaned:
        return False
    parts = cleaned.split("/")
    # The trust check allows one file under the settings folder at join time.
    # An update is stricter: nothing under that folder is ever taken on its
    # own, because a changed settings file would re-point the plugin itself.
    first = [part for part in parts if part not in ("", ".")]
    if first and trust_surface.normalize_component(first[0]) == ".claude":
        return True
    return trust_surface.path_is_refused(parts)


def _incoming_symlinks(root: str, target: str, git: GitRunner) -> List[str]:
    """The paths the shared copy would bring in as links rather than as files.

    A link is a way to make one name stand for a file somewhere else on this
    computer, so an update carrying one is refused the same way an update
    carrying an instruction file is.
    """
    listed = git.run(
        ["diff", "--raw", "HEAD.." + target],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    )
    if not listed.ok:
        return []
    found: List[str] = []
    for line in listed.stdout.split("\n"):
        if not line.startswith(":"):
            continue
        head, _, path = line.partition("\t")
        fields = head[1:].split()
        if len(fields) < 2:
            continue
        if fields[1] == "120000":
            found.append(path.split("\t")[0].strip() or "a link")
    return found


def _record_pull_refusal(
    base_id: str,
    refused: Sequence[str],
    today: datetime.date,
    part: _Part,
    left_again: List[str],
):
    """Record that an update was refused, in this seat's own settings.

    The day, one fixed code, and the refused paths as hashes. The paths
    themselves are never written down, because a path can name a customer.

    Only the part that reaches the shared copy can find this out, and that part
    prints nothing a person sees, so it also leaves a note for the other part of
    the next session to say out loud. The combined form says it there and then,
    so it leaves no note. `left_again` tells the caller a note was left by this
    run, so a note said last session is not cleared while the update behind it
    is still being refused.
    """
    hashes = sorted(ids.path_hash(path) for path in refused)
    note = {}
    if part.name == "context":
        note["pending_visible_note"] = CODE_PULL_REFUSED
        left_again.append(CODE_PULL_REFUSED)
    state.update_seat(
        base_id,
        last_pull_refusal=today.isoformat(),
        last_pull_refusal_code=CODE_PULL_REFUSED,
        last_pull_refusal_path_hashes=hashes,
        **note
    )
    return {
        "date": today.isoformat(),
        "code": CODE_PULL_REFUSED,
        "path_hashes": hashes,
    }


def _retry_pending(base_id: str, root: str, git: GitRunner) -> None:
    """Send a confirmation that could not be sent last time, if we can yet."""
    try:
        from . import confirm  # noqa: F401
    except ImportError:
        return
    retry = getattr(confirm, "retry_pending", None)
    if retry is None:
        return
    try:
        retry(base_id=base_id, base_root=root, runner=git)
    except Exception:
        return


def _daily_block(root, base_id, session_id, now, git, root_of_plugin, part):
    """The whole of a joined base's session start, for one part of it.

    The note left by an earlier session is said here and cleared only once this
    run's own work is finished, because the two parts run at the same time and
    clearing it first could take it away before the other part had read it.
    """
    seat, _problems = state.load_seat(base_id)
    pending = seat.get("pending_visible_note")
    if part.name == "visible" and pending == CODE_PULL_REFUSED:
        return _render(part, None, PULL_REFUSED)

    left_again: List[str] = []
    result = _daily_work(
        root, base_id, session_id, now, git, root_of_plugin, part, seat, left_again
    )

    if pending and part.writes and not left_again:
        try:
            state.update_seat(base_id, pending_visible_note=None)
        except Exception:
            pass
    return result


def _daily_work(
    root, base_id, session_id, now, git, root_of_plugin, part, seat, left_again
):
    if part.writes:
        if not seat.get("git_hook_installed"):
            try:
                install_git_hook.install(
                    root, root_of_plugin, runner=git, base_id=base_id
                )
            except Exception:
                pass
        if seat.get("pending_confirmation"):
            _retry_pending(base_id, root, git)

    blocks = load_blocks(root_of_plugin, "injection.md")
    if not blocks:
        return None

    on_default, _code = paths.head_is_default_branch(root, runner=git)
    if not on_default:
        return _stalled(blocks, root, git, NOT_DEFAULT_BRANCH, part)

    status = git.run(
        ["status", "--porcelain"], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
    )
    if not status.ok or status.out():
        return _stalled(blocks, root, git, DIRTY_TREE, part)

    has_remote = paths.remote_url(root, runner=git) is not None

    if not part.reaches_out:
        # This part never reaches the shared copy and never records where the
        # base stood, so everything below is not its work. The one thing left
        # for it to say is the offer to finish a setup that stopped halfway,
        # and the base itself answers that.
        return _render(
            part,
            None,
            _question_text(
                root,
                base_id,
                session_id,
                now,
                git,
                blocks,
                _settings_of(_map_text(root)),
                has_remote,
                root_of_plugin,
                part,
            ).visible
            or None,
        )

    branch = git.run(
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        timeout=LOCAL_TIMEOUT_SECONDS,
    ).out()
    changes = 0

    if has_remote:
        fetched = git.run(
            ["fetch", "origin", branch, "--quiet"],
            cwd=root,
            timeout=constants.FETCH_TIMEOUT_SECONDS,
        )
        if not fetched.ok:
            return _stalled(blocks, root, git, UNREACHABLE % _as_of(root, git), part)
        target = "origin/" + branch
        incoming = git.run(
            ["diff", "--name-only", "HEAD.." + target],
            cwd=root,
            timeout=LOCAL_TIMEOUT_SECONDS,
        )
        if not incoming.ok:
            return _stalled(blocks, root, git, UNREACHABLE % _as_of(root, git), part)
        names = [line.strip() for line in incoming.stdout.split("\n") if line.strip()]
        refused = [name for name in names if _is_refused_path(name)]
        refused.extend(
            name for name in _incoming_symlinks(root, target, git) if name not in refused
        )
        if refused:
            _record_pull_refusal(base_id, refused, now.date(), part, left_again)
            return _stalled(blocks, root, git, PULL_REFUSED, part)
        if names:
            before = git.run(
                ["rev-parse", "HEAD"], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
            ).out()
            merged = git.run(
                ["merge", "--ff-only", target],
                cwd=root,
                timeout=constants.FETCH_TIMEOUT_SECONDS,
            )
            if not merged.ok:
                return _stalled(
                    blocks, root, git, COULD_NOT_UPDATE % _as_of(root, git), part
                )
            after = git.run(
                ["rev-parse", "HEAD"], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
            ).out()
            counted = git.run(
                ["rev-list", "--count", before + ".." + after],
                cwd=root,
                timeout=LOCAL_TIMEOUT_SECONDS,
            )
            try:
                changes = int(counted.out()) if counted.ok else 0
            except ValueError:
                changes = 0
            state.update_seat(base_id, last_seen_commit=after)
            trust_note = _trust_after_update(root, base_id, now.date(), git)
            if trust_note:
                return _stalled(blocks, root, git, trust_note, part)
        else:
            head = git.run(
                ["rev-parse", "HEAD"], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
            ).out()
            if head:
                state.update_seat(base_id, last_seen_commit=head)
    else:
        head = git.run(
            ["rev-parse", "HEAD"], cwd=root, timeout=LOCAL_TIMEOUT_SECONDS
        ).out()
        if head:
            state.update_seat(base_id, last_seen_commit=head)

    map_text = _map_text(root)
    settings = _settings_of(map_text)
    question = _question_text(
        root,
        base_id,
        session_id,
        now,
        git,
        blocks,
        settings,
        has_remote,
        root_of_plugin,
        part,
    )
    context = _fill_main(blocks, map_text, settings, changes, "", question.context)
    return _render(part, context, question.visible or None)


def _trust_after_update(root, base_id, today, git) -> Optional[str]:
    """Check the whole folder again once an update has landed.

    The update itself already refused the paths that would make opening this
    folder run something, so this is a report and not a second refusal: the
    update stays, and the person is told to have the owner look at the folder.
    Undoing it here would leave the base in a state nobody chose.
    """
    try:
        verdict = trust_surface.check(root, runner=git)
    except Exception:
        return None
    if verdict.ok:
        return None
    try:
        state.update_seat(
            base_id,
            last_pull_refusal=today.isoformat(),
            last_pull_refusal_code=CODE_PULL_REFUSED,
            last_pull_refusal_path_hashes=[],
        )
    except Exception:
        pass
    return TRUST_AFTER_UPDATE


class _Question(object):
    """The part of the injection that asks for something, and what to show."""

    __slots__ = ("context", "visible")

    def __init__(self, context: str = "", visible: str = ""):
        self.context = context
        self.visible = visible


def _stalled(blocks, root, git, sentence, part):
    """Say the one sentence, add the map as it stands, and ask nothing."""
    if part.name == "visible":
        return _render(part, None, sentence)
    map_text = _map_text(root)
    settings = _settings_of(map_text)
    note = AS_OF % _as_of(root, git)
    context = _fill_main(blocks, map_text, settings, 0, note, "")
    return _render(part, context, sentence)


def fence_for(text: str) -> str:
    """The marks that hold a piece of text apart from the words around it.

    The text comes out of the base, so it can hold marks of its own. The fence
    is always one mark longer than the longest run in the text itself, and
    never shorter than three, so nothing the text holds can end it early.
    """
    longest = 0
    for match in _BACKTICK_RUN.finditer(text or ""):
        longest = max(longest, len(match.group(0)))
    return "`" * max(3, longest + 1)


def _fill_main(blocks, map_text, settings, changes, status_note, question_text):
    shown_map = map_text[: constants.MAX_MAP_CHARS]
    text = fill(
        blocks.get("main", ""),
        {
            "changes": changes,
            "status_note": status_note,
            "fence": fence_for(shown_map),
            "map": shown_map,
            "threshold_days": settings.confirmation_threshold_days,
            "not_now_days": settings.not_now_days,
            "question": question_text,
        },
    )
    return text[: constants.MAX_INJECTION_CHARS]


# --- Reading the base for the question --------------------------------------


def _newest_date_in(value) -> Optional[str]:
    return base_reader.newest_date_in(value)


def _context_files(root: str) -> List[stale.ContextFileInfo]:
    return base_reader.context_files(root)


def _ledger(root: str, base_id: str, today: datetime.date) -> List[stale.LedgerInput]:
    return base_reader.ledger(root, base_id, today)


def _line_authors(root: str, relative: str, git: GitRunner) -> Dict[int, str]:
    return base_reader.line_authors(root, relative, git)


def _confirmations(root: str, git: GitRunner) -> List[stale.ConfirmationRecord]:
    return base_reader.confirmations(root, git)


def _corrections(root: str, git: GitRunner) -> List[stale.CorrectionRecord]:
    return base_reader.corrections(root, git)


def _seat_input(base_id: str, has_remote: bool) -> stale.SeatInput:
    return base_reader.seat_input(base_id, has_remote)


def _missing_required(files: Dict[str, stale.ContextFileInfo]) -> List[str]:
    """The files a base needs before anyone can be asked to confirm anything."""
    return base_reader.missing_required(files)


def _question_text(
    root,
    base_id,
    session_id,
    now,
    git,
    blocks,
    settings,
    has_remote,
    root_of_plugin,
    part,
) -> _Question:
    """The one question this session asks, or the reason it asks none.

    Only one thing here is ever said out loud, which is the offer to finish a
    setup that stopped halfway, so the part that prints what a person sees works
    that out from the same files and then stops. Which file is asked about is
    text the assistant reads, and settling it reads the base line by line and
    issues an id that may be issued once, so neither belongs in a part that must
    write nothing.
    """
    today = state.today(now)
    files = _context_files(root)
    ledger = _ledger(root, base_id, today)
    by_path = {info.path: info for info in files}

    missing = _missing_required(by_path)
    usable_entries = [item for item in ledger if item.entry is not None and not item.error]
    if missing or not usable_entries:
        setup = load_blocks(root_of_plugin, "continue-setup.md")
        named = ", ".join(missing) if missing else "a first decision written down"
        return _Question(
            fill(setup.get("context", ""), {"missing": named}),
            fill(setup.get("visible", ""), {"missing": named}),
        )

    if not part.writes:
        return _Question("", "")

    email = _repo_email(root, git)
    owned = [path for path, info in by_path.items() if email and email in info.owners]
    if not owned:
        return _Question(blocks.get("no-owner", ""), "")

    report = stale.compute(
        today=today,
        settings=settings,
        files=files,
        ledger=ledger,
        confirmations=_confirmations(root, git),
        corrections=_corrections(root, git),
        seat=_seat_input(base_id, has_remote),
        owner_email=email,
    )
    candidates = report.candidate_questions(email)
    chosen = None
    rest: List[str] = []
    for candidate in candidates:
        try:
            path = paths.canonical_context_path(root, candidate.path)
        except (PathError, ValidationError) as failure:
            state.append_dropped_path(
                base_id, candidate.path, "dropped-path", candidate.entry_id, today
            )
            continue
        if chosen is None:
            chosen = (candidate, path)
        else:
            rest.append(path)
    if chosen is None:
        return _Question("", "")

    candidate, path = chosen
    question = state.issue_question_id(
        base_id, path, candidate.trigger, session_id, candidate.entry_id, now
    )
    state.append_asked(base_id, question, path, candidate.trigger, "unanswered", today)

    entry_note = ""
    entry_show = ""
    trigger_note = blocks.get("trigger-threshold", "")
    if candidate.trigger == stale.TRIGGER_LEDGER and candidate.entry_id:
        trigger_note = blocks.get("trigger-ledger", "")
        entry_file = _entry_file_name(ledger, candidate.entry_id)
        block = "entry-note" if entry_file else "entry-note-plain"
        entry_note = fill(
            blocks.get(block, ""),
            {"entry_id": candidate.entry_id, "entry_file": entry_file},
        )
        if entry_note:
            entry_note += "\n"
        entry_show = blocks.get("entry-show", "")
    also = ""
    if rest:
        also = fill(blocks.get("also-waiting", ""), {"paths": ", ".join(rest)})

    text = fill(
        blocks.get("question", ""),
        {
            "path": path,
            "trigger_note": trigger_note,
            "entry_note": entry_note,
            "entry_show": entry_show,
            "question_id": question,
            "script": CONFIRM_SCRIPT,
            "also_waiting": also,
        },
    )
    return _Question(text, "")


def _entry_file_name(ledger: Sequence[stale.LedgerInput], entry_id: str) -> str:
    """The name of the file one decision was written in, when it is plain.

    The name comes out of the shared copy, and it lands outside the fenced part
    of the injection, so a name holding anything but plain letters, digits, and
    the three marks below is left out rather than passed on.
    """
    for item in ledger:
        if item.entry is not None and item.entry.id == entry_id:
            name = (item.path or "").rsplit("/", 1)[-1]
            return name if _PLAIN_FILE_NAME.match(name) else ""
    return ""
