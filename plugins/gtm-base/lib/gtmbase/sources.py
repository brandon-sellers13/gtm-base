"""What the person names, listed safely, agreed to once, and fenced.

Three jobs live here, in the order they happen.

Listing. A person names a folder. We look through it without ever following a
link, without opening anything that looks like a key, and without leaving the
folder they named. What comes back is two lists: the files we would read, and
the files we would not, each with a short code saying why. Nothing has been
read at this point. The list is what the person is shown.

Consent. The person says yes to that list, and the list is frozen. From then
on the only files that may be read are the ones on it, compared by their real
path, so a file dropped into the folder a minute later is refused until a new
list has been shown and agreed to. Saying yes also writes the marker that
tells the safeguard nothing may leave this computer for the rest of the
session.

Fencing. Every piece of text, whether it came off the disk here or out of the
assistant's own reader, has everything a person reading the file would not see
taken out of it and counted, and is then wrapped in a fence that says what it
is before it says anything else. Text inside the fence is what somebody wrote
down. It is never a set of instructions to follow.
"""

from __future__ import annotations

import datetime
import hashlib
import os
import re
from typing import Dict, List, Optional, Sequence

from . import constants, marker, paths, redaction_patterns, scan
from .errors import ConsentError, SourceRejected

# --- The codes a listing reports --------------------------------------------

# The name is a link, so we neither followed it nor opened it.
CODE_SYMLINK = "symlink"
# The name says the file holds a key, a certificate, or settings with secrets.
CODE_SECRET_NAME = "secret-name"
# The name starts with a full stop, so it was not meant to be read.
CODE_DOTFILE = "dotfile"
# The folder holds somebody else's code rather than the person's own writing.
CODE_DEPENDENCY_FOLDER = "dependency-folder"
# The file holds other files inside it.
CODE_ARCHIVE = "archive"
# The folder is a company base of its own, so the whole of it is left alone.
CODE_ANOTHER_BASE = "another-base"
# The plugin does not open this kind of file. Save it as a PDF or paste it in.
CODE_EXPORT_OR_PASTE = "export-or-paste"
# We have no way to read this kind of file at all.
CODE_UNSUPPORTED = "unsupported"
# The file is larger than we read.
CODE_TOO_LARGE = "too-large"
# The first line of the file says it holds a key.
CODE_KEY_HEADER = "key-header"
# The file or folder could not be looked at.
CODE_UNREADABLE = "unreadable"
# The real file turned out to sit outside the folder that was named.
CODE_OUTSIDE_FOLDER = "outside-folder"
# The folder is larger than we will look through, so none of it is offered.
CODE_FOLDER_TOO_LARGE = "folder-too-large"
# The date on a file was in the future and was pulled back to today.
CODE_DATE_CLAMPED = "date-clamped"
# Something a reader would not have seen was taken out of the text.
CODE_HIDDEN_REMOVED = "hidden-removed"

# The three kinds of hidden thing, named as a person would name them. They are
# the words that reach a sentence somebody reads, so they are singular here and
# the sentence adds the letter s when there is more than one.
REMOVED_COMMENT = "comment"
REMOVED_TAG = "tag"
REMOVED_HIDDEN_CHARACTER = "hidden character"

# --- Small pieces of shape ---------------------------------------------------

# What a label may be made of. It is repeated back inside the fence, so it
# holds letters, digits, spaces, and three pieces of punctuation, and nothing
# that could start a new line or close the fence early.
_LABEL = re.compile(r"^[A-Za-z0-9 ._-]{1,80}$")

# The line a key file carries about itself.
_KEY_HEADER_START = b"-----BEGIN"
# How much of a file is read to see whether it holds a key. The whole of this
# much is searched rather than only the first line, because a file that opens
# with a blank line, a comment, or a byte order mark still holds the key that
# comes after it.
KEY_SNIFF_BYTES = 512
# The three bytes some editors put at the very start of a file.
_BYTE_ORDER_MARK = b"\xef\xbb\xbf"

# The leading word of a file name, when the name is built from two words.
_LEADING_WORD = re.compile(r"^([a-z][a-z0-9]{2,})[-_]")
# Leading words that say nothing about which company a file belongs to.
_NOT_A_COMPANY = frozenset(
    [
        "the",
        "our",
        "new",
        "old",
        "draft",
        "final",
        "copy",
        "main",
        "current",
        "updated",
        "internal",
        "external",
        "working",
        "company",
        "client",
        "customer",
        "product",
        "team",
        "sales",
        "marketing",
    ]
)
# The words in a file name that say the file is about who a company sells to.
_COMPANY_MARKERS = ("positioning", "icp")

# Every class the outgoing-content scan knows about except the one this module
# runs. Passing the rest as skipped is how the hidden-content class is run on
# its own without a second copy of the patterns living here.
_EVERYTHING_ELSE = tuple(
    name
    for name, _pattern, _label in redaction_patterns.PATTERN_CLASSES
    if name != redaction_patterns.HIDDEN_CONTENT
)


class Limits(object):
    """How much of a folder a listing will take in. Tests make these small."""

    __slots__ = ("max_bytes", "walk_cap")

    def __init__(self, max_bytes: Optional[int] = None, walk_cap: Optional[int] = None):
        self.max_bytes = (
            constants.SOURCE_MAX_BYTES if max_bytes is None else int(max_bytes)
        )
        self.walk_cap = (
            constants.SOURCE_WALK_CAP if walk_cap is None else int(walk_cap)
        )


class Entry(object):
    """One file the plugin would read, and what is known about it."""

    __slots__ = ("path", "kind", "size", "modified_date", "clamped")

    def __init__(self, path: str, kind: str, size: int, modified_date, clamped=False):
        self.path = path
        self.kind = kind
        self.size = size
        self.modified_date = modified_date
        # True when the file said it was changed on a day still to come and
        # the date was pulled back to today.
        self.clamped = bool(clamped)

    def __repr__(self) -> str:
        return "Entry(path=%r, kind=%r)" % (self.path, self.kind)


class Skipped(object):
    """One file or folder the plugin left alone, and the code saying why."""

    __slots__ = ("path", "reason_code")

    def __init__(self, path: str, reason_code: str):
        self.path = path
        self.reason_code = reason_code

    def __repr__(self) -> str:
        return "Skipped(path=%r, reason_code=%r)" % (self.path, self.reason_code)


class Listing(object):
    """Everything the person is shown before they say yes to anything."""

    __slots__ = (
        "root",
        "readable",
        "skipped",
        "excluded_counts",
        "needs_second_yes",
        "appears_multi_company",
        "company_hints",
        "codes",
    )

    def __init__(
        self,
        root: str,
        readable: Sequence[Entry],
        skipped: Sequence[Skipped],
        needs_second_yes: bool = False,
        appears_multi_company: bool = False,
        company_hints: Optional[Sequence[str]] = None,
    ):
        self.root = root
        self.readable = list(readable)
        self.skipped = list(skipped)
        self.excluded_counts = _counts(self.skipped)
        self.needs_second_yes = bool(needs_second_yes)
        self.appears_multi_company = bool(appears_multi_company)
        self.company_hints = list(company_hints or [])
        # What the person should be told about the list as a whole, as short
        # codes. A date pulled back to today is the one this release reports.
        self.codes = (
            [CODE_DATE_CLAMPED]
            if any(entry.clamped for entry in self.readable)
            else []
        )

    def __repr__(self) -> str:
        return "Listing(root=%r, readable=%d, skipped=%d)" % (
            self.root,
            len(self.readable),
            len(self.skipped),
        )


def listing_digest(listing: Listing) -> str:
    """One short value standing for exactly what a person was shown.

    It covers the folder, every file that would be read, and every file that
    was left out with the reason it was left out, so a file appearing, a file
    disappearing, or a file changing from left out to readable all change it.
    That is what lets the yes be checked against the folder as it is now.
    """
    parts = [os.path.realpath(listing.root or "")]
    parts.append("readable")
    parts.extend(sorted(os.path.realpath(entry.path) for entry in listing.readable))
    parts.append("skipped")
    parts.extend(
        sorted("%s\t%s" % (item.path, item.reason_code) for item in listing.skipped)
    )
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _counts(skipped: Sequence[Skipped]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in skipped:
        counts[item.reason_code] = counts.get(item.reason_code, 0) + 1
    return counts


# --- The walk ---------------------------------------------------------------


def list_folder(folder: str, limits: Optional[Limits] = None, today=None) -> Listing:
    """Look through a folder and say what could be read and what could not.

    Nothing is opened except the first few bytes of a file we would otherwise
    offer, which is how a file that starts like a key is caught even when its
    name says nothing. Links are listed and never followed, whether they point
    at a file or at a folder, and every file that survives is checked once more
    to make sure the real thing sits inside the folder that was named.
    """
    limits = limits or Limits()
    today = today or datetime.date.today()
    if not folder:
        return Listing("", [], [Skipped("", CODE_UNREADABLE)])
    root = os.path.realpath(os.path.abspath(os.path.expanduser(folder)))
    if not os.path.isdir(root):
        return Listing(root, [], [Skipped(root, CODE_UNREADABLE)])

    readable: List[Entry] = []
    skipped: List[Skipped] = []
    seen = 0

    def note_failure(failure):
        skipped.append(Skipped(getattr(failure, "filename", root), CODE_UNREADABLE))

    for dirpath, dirnames, filenames in os.walk(
        root, followlinks=False, onerror=note_failure
    ):
        kept = []
        for name in sorted(dirnames):
            seen += 1
            if seen > limits.walk_cap:
                return Listing(root, [], [Skipped(root, CODE_FOLDER_TOO_LARGE)])
            full = os.path.join(dirpath, name)
            code = _folder_code(name, full)
            if code is not None:
                skipped.append(Skipped(full, code))
                continue
            kept.append(name)
        dirnames[:] = kept

        for name in sorted(filenames):
            seen += 1
            if seen > limits.walk_cap:
                return Listing(root, [], [Skipped(root, CODE_FOLDER_TOO_LARGE)])
            full = os.path.join(dirpath, name)
            entry, code = _file_verdict(full, name, root, limits, today)
            if entry is not None:
                readable.append(entry)
            else:
                skipped.append(Skipped(full, code))

    multi, hints = _company_reading(readable, root)
    return Listing(
        root,
        readable,
        skipped,
        needs_second_yes=_is_home_or_above(root),
        appears_multi_company=multi,
        company_hints=hints,
    )


def _folder_code(name: str, full: str) -> Optional[str]:
    """Why a folder is left alone, or None when we look inside it."""
    if os.path.islink(full):
        return CODE_SYMLINK
    folded = name.casefold()
    if folded in constants.SOURCE_DEPENDENCY_FOLDERS:
        return CODE_DEPENDENCY_FOLDER
    if paths.is_base_shaped(full):
        return CODE_ANOTHER_BASE
    if name.startswith("."):
        return CODE_DOTFILE
    if _is_secret_name(folded):
        return CODE_SECRET_NAME
    return None


def _file_verdict(full: str, name: str, root: str, limits: Limits, today):
    """Either an entry we would read, or the code saying why we would not."""
    if os.path.islink(full):
        return None, CODE_SYMLINK
    folded = name.casefold()
    if _is_secret_name(folded):
        return None, CODE_SECRET_NAME
    if name.startswith("."):
        return None, CODE_DOTFILE
    suffix = os.path.splitext(folded)[1]
    if suffix in constants.SOURCE_ARCHIVE_SUFFIXES:
        return None, CODE_ARCHIVE
    if suffix in constants.SOURCE_EXPORT_SUFFIXES:
        return None, CODE_EXPORT_OR_PASTE
    kind = constants.SOURCE_READABLE_SUFFIXES.get(suffix)
    if kind is None:
        return None, CODE_UNSUPPORTED
    if not os.path.isfile(full):
        return None, CODE_UNREADABLE
    try:
        size = os.path.getsize(full)
    except OSError:
        return None, CODE_UNREADABLE
    if size > limits.max_bytes:
        return None, CODE_TOO_LARGE
    if os.path.realpath(full) != full:
        return None, CODE_OUTSIDE_FOLDER
    if not full.startswith(root.rstrip(os.sep) + os.sep):
        return None, CODE_OUTSIDE_FOLDER
    starts_like_a_key = _starts_like_a_key(full)
    if starts_like_a_key is None:
        return None, CODE_UNREADABLE
    if starts_like_a_key:
        return None, CODE_KEY_HEADER
    when = date_for_file(full, today)
    return Entry(full, kind, size, when.date, when.clamped), None


def _is_secret_name(folded: str) -> bool:
    """Whether a name says on its own that the file holds something private."""
    if folded in constants.SOURCE_EXCLUDED_NAMES:
        return True
    for prefix in constants.SOURCE_EXCLUDED_PREFIXES:
        if folded.startswith(prefix):
            return True
    for suffix in constants.SOURCE_EXCLUDED_SUFFIXES:
        if folded.endswith(suffix):
            return True
    return False


def _starts_like_a_key(full: str) -> Optional[bool]:
    """Whether the start of the file says it holds a key. None means unreadable.

    The whole of the sniffed head is searched, not only its first line. A key
    file written with a byte order mark, a blank first line, or a comment above
    the key would otherwise be offered as an ordinary document.
    """
    try:
        with open(full, "rb") as stream:
            head = stream.read(KEY_SNIFF_BYTES)
    except OSError:
        return None
    if head.startswith(_BYTE_ORDER_MARK):
        head = head[len(_BYTE_ORDER_MARK) :]
    return _KEY_HEADER_START in head.lstrip()


def _is_home_or_above(root: str) -> bool:
    """Whether the folder named is the home folder or holds it."""
    home = os.path.realpath(os.path.expanduser("~"))
    if root == home:
        return True
    return home.startswith(root.rstrip(os.sep) + os.sep)


def _company_reading(readable: Sequence[Entry], root: str):
    """Whether the folder looks like it holds more than one company's work.

    The rule is deliberately plain, because its only job is to decide whether
    to ask. A file counts when its name holds the word positioning or the
    letters icp, since those are the two documents every company has exactly
    one of. Two of them sitting in different folders at the top of what was
    named, or two of them named after different companies, is enough to ask.
    """
    markers = []
    for entry in readable:
        name = os.path.basename(entry.path).casefold()
        if any(word in name for word in _COMPANY_MARKERS):
            markers.append(entry)
    if len(markers) < 2:
        return False, []

    places = set()
    words = set()
    for entry in markers:
        relative = os.path.relpath(entry.path, root).replace(os.sep, "/")
        places.add(relative.split("/")[0] if "/" in relative else ".")
        found = _LEADING_WORD.match(os.path.basename(entry.path).casefold())
        if found and found.group(1) not in _NOT_A_COMPANY:
            words.add(found.group(1))

    hints = set()
    if len(places) > 1:
        hints.update(places)
    if len(words) > 1:
        hints.update(words)
    return bool(hints), sorted(hints)


# --- Dates ------------------------------------------------------------------


class FileDate(object):
    """A file's date, and whether it had to be pulled back to today."""

    __slots__ = ("date", "clamped")

    def __init__(self, date, clamped: bool):
        self.date = date
        self.clamped = bool(clamped)

    def __repr__(self) -> str:
        return "FileDate(date=%r, clamped=%r)" % (self.date, self.clamped)


def date_for_file(path: str, today=None) -> FileDate:
    """The day a file was last changed, never later than today.

    A clock that is ahead, or a file copied from a machine whose clock was,
    would otherwise date a source in the future, and a date in the future
    makes every comparison after it wrong.
    """
    today = today or datetime.date.today()
    try:
        stamp = os.path.getmtime(path)
        found = datetime.date.fromtimestamp(stamp)
    except (OSError, OverflowError, ValueError):
        return FileDate(None, False)
    if found > today:
        return FileDate(today, True)
    return FileDate(found, False)


# --- Consent ----------------------------------------------------------------


class Consent(object):
    """The exact set of files a person agreed to have read, and when."""

    __slots__ = ("paths", "session_id", "frozen_at", "_set")

    def __init__(self, paths_, session_id: str, frozen_at: str):
        self.paths = tuple(paths_)
        self.session_id = session_id
        self.frozen_at = frozen_at
        self._set = frozenset(self.paths)

    def allows(self, path: str) -> bool:
        """Whether this exact file, as it really is now, is on the list."""
        if not path:
            return False
        return os.path.realpath(path) in self._set

    def __repr__(self) -> str:
        return "Consent(files=%d, session_id=%r)" % (len(self.paths), self.session_id)


class ConsentList(object):
    """The one way a list of files becomes a list that may be read."""

    @staticmethod
    def freeze(listing: Listing, session_id: str) -> Consent:
        """Take the person's yes over a listing they were just shown."""
        return ConsentList.freeze_paths(
            [entry.path for entry in listing.readable], session_id
        )

    @staticmethod
    def freeze_paths(paths_, session_id: str) -> Consent:
        """Take the person's yes: fix the set, and say nothing may leave.

        This takes the paths rather than a listing, because the set a person
        agreed to is the one they were shown and written down at that moment,
        not whatever a second look at the folder would find now.

        The marker is written as part of the same step on purpose. The moment
        a person agrees to have their own files read, this session is holding
        text nobody has vetted, and the safeguard has to know it before a
        single file is opened rather than after.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("a frozen list needs the session it belongs to")
        wanted = sorted(set(os.path.realpath(path) for path in paths_))
        frozen_at = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        marker.write_sources_read_marker(session_id)
        return Consent(wanted, session_id.strip(), frozen_at)


def read_allowed(consent: Optional[Consent], path: str) -> str:
    """The real path of a file that may be read, or a refusal.

    This is the check every read goes through. A file added to the folder
    after the person said yes fails it, and so does a file whose name still
    matches but which now points somewhere else. The only way past it is a new
    list, shown to the person and agreed to again.
    """
    if consent is None or not consent.allows(path):
        raise ConsentError(
            "this file is not on the list you agreed to", code="not-consented"
        )
    return os.path.realpath(path)


# --- Sources and the fence --------------------------------------------------


class Source(object):
    """One piece of text, with everything needed to say where it came from."""

    __slots__ = (
        "label",
        "text",
        "kind",
        "date",
        "path",
        "screened",
        "clamped",
        "removed",
        "codes",
    )

    def __init__(
        self,
        label,
        text,
        kind,
        date=None,
        path=None,
        screened=False,
        clamped=False,
        removed=None,
    ):
        self.label = label
        self.text = text
        self.kind = kind
        self.date = date
        self.path = path
        self.screened = bool(screened)
        # True when the date on this source was in the future and was pulled
        # back to today, so the person can be told the date is not the file's.
        self.clamped = bool(clamped)
        # How many of each kind of hidden thing were taken out of the text,
        # so the person hears what was done to their own document.
        self.removed = dict(removed or {})
        self.codes = [CODE_HIDDEN_REMOVED] if self.removed else []

    def __repr__(self) -> str:
        return "Source(label=%r, kind=%r, date=%r)" % (
            self.label,
            self.kind,
            self.date,
        )


# How many times the removal is run over one piece of text before it is taken
# as done. One pass clears comments inside comments; the rest is safety.
_STRIP_PASSES = 5


def strip_hidden(text: str):
    """Take out everything a reader of the file would not have seen.

    What comes back is the text as the person would read it on the page, and a
    count of each kind of thing that went. Nothing is refused here. A comment
    in a template, a tag in a note pasted out of a web page, and a zero-width
    character carried in from a word processor are all ordinary things to find
    in somebody's own writing, and refusing the whole document over one of them
    turned a document that could simply have been cleaned into a wall.
    """
    if not scan.scan_text(text, None, "a source", _EVERYTHING_ELSE):
        return text, {}
    removed: Dict[str, int] = {}
    cleaned = text
    for _pass in range(_STRIP_PASSES):
        cleaned, counted = _strip_once(cleaned)
        for kind, count in counted.items():
            removed[kind] = removed.get(kind, 0) + count
        if not scan.scan_text(cleaned, None, "a source", _EVERYTHING_ELSE):
            break
    return cleaned, removed


def _strip_once(text: str):
    """One pass of the removal, and what that pass took out."""
    counted: Dict[str, int] = {}

    def drop(pattern, kind, value):
        cleaned, count = pattern.subn("", value)
        if count:
            counted[kind] = counted.get(kind, 0) + count
        return cleaned

    # Whole comments first, then any opening or closing mark left behind by a
    # comment that had another one inside it, and both count as comments.
    text = drop(redaction_patterns.HIDDEN_COMMENT, REMOVED_COMMENT, text)
    text = drop(redaction_patterns.HIDDEN_COMMENT_MARK, REMOVED_COMMENT, text)
    text = drop(redaction_patterns.HIDDEN_TAG, REMOVED_TAG, text)
    text = drop(
        redaction_patterns.HIDDEN_CHARACTER, REMOVED_HIDDEN_CHARACTER, text
    )
    return text, counted


def removed_sentence(label: str, removed) -> str:
    """The one sentence saying what was taken out of one of their documents."""
    if not removed:
        return ""
    parts = []
    for kind in (REMOVED_COMMENT, REMOVED_TAG, REMOVED_HIDDEN_CHARACTER):
        count = int(removed.get(kind, 0))
        if count:
            parts.append("%d %s%s" % (count, kind, "" if count == 1 else "s"))
    if len(parts) > 1:
        listed = ", ".join(parts[:-1]) + " and " + parts[-1]
    else:
        listed = parts[0]
    return "Hidden parts removed from %s: %s." % (label, listed)


def make_source(
    label: str, text: str, kind: str, date=None, path=None, clamped: bool = False
) -> Source:
    """Screen a piece of text and turn it into something a prompt may hold.

    Anything a person reading the file would not see is taken out and counted,
    because text nobody can read is text nobody agreed to, and the person is
    told what went rather than told their document could not be used at all.

    One thing still stops text here: anything that writes the fence's own
    lines, which would let a document end its own fence and carry on as though
    it were the assistant's own words. That is checked after the removal, so a
    document cannot hide one of those lines inside a tag and have it appear
    once the tag is gone.
    """
    checked = _checked_label(label)
    if kind not in constants.SOURCE_KINDS:
        raise SourceRejected("this is not a kind of source", code="unknown-kind")
    if not isinstance(text, str):
        raise SourceRejected("this source is not text", code="unreadable")
    cleaned, removed = strip_hidden(text)
    _refuse_fence_markers(cleaned)
    return Source(checked, cleaned, kind, date, path, True, clamped, removed)


def paste_source(label: str, text: str) -> Source:
    """Text a person pasted in. It has no date, because a paste has none."""
    return make_source(label, text, "paste", date=None, path=None)


def fence(source: Source) -> str:
    """Wrap a source so that what it is has been said before it says anything.

    The label and the text are checked again here rather than trusted, because
    this is the last thing that happens before the text reaches a prompt, and
    the cost of checking twice is nothing next to the cost of being wrong.
    """
    label = _checked_label(getattr(source, "label", None))
    text = getattr(source, "text", None)
    if not isinstance(text, str):
        raise SourceRejected("this source is not text", code="unreadable")
    if not getattr(source, "screened", False):
        raise SourceRejected("this source was never screened", code="not-screened")
    _refuse_fence_markers(text)
    body = text.rstrip("\n")
    return "\n".join(
        [
            constants.SOURCE_FENCE_HEADER % label,
            constants.SOURCE_FENCE_SENTENCE,
            body,
            constants.SOURCE_FENCE_FOOTER,
        ]
    ) + "\n"


def _checked_label(label) -> str:
    if not isinstance(label, str) or not _LABEL.match(label):
        raise SourceRejected("this label is not one we repeat", code="bad-label")
    return label


def _refuse_fence_markers(text: str) -> None:
    """Refuse text that writes either of the fence's own lines.

    Both sides are folded to one letter case first. The fence is read back by
    people and by the assistant, and `[[SOURCE:` reads exactly like the line
    this module writes, so a difference of letter case must not get past.
    """
    folded = text.casefold()
    footer = constants.SOURCE_FENCE_FOOTER.casefold()
    # The opener without the space after it, so a header written as
    # `[[source:notes]]` is refused as surely as `[[source: notes]]`.
    opener = constants.SOURCE_FENCE_HEADER.split("%s")[0].rstrip().casefold()
    for marker_line in (footer, opener):
        if marker_line and marker_line in folded:
            raise SourceRejected(
                "this text writes the fence's own lines", code="fence-marker"
            )
