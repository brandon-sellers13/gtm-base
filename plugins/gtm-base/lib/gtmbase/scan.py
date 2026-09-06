"""Reading outgoing content for the things that must not leave the computer.

Two entry points. `scan_text` reads any block of text, a message or a command
line. `scan_diff_added_lines` reads the change itself and looks only at what is
being added, because a line that is already in the shared copy has already left
this computer and refusing it now would only make the base impossible to work
in.

A hit carries the class it belongs to, the file it was found in, and the line
number. It never carries the value that matched.
"""

from __future__ import annotations

import os
import re
from typing import FrozenSet, List, Optional, Sequence, Tuple

from . import constants, redaction_patterns
from .fsutil import read_text

# How far into a file the frontmatter block can reach. An owner line below
# this is a line in the body, and an address in the body is a hit.
FRONTMATTER_MAX_LINES = 20

# Characters an allowed-words entry may never hold. Entries are compared
# literally, so these could do no harm on their own; refusing them is how the
# file stays a list of words rather than a way to turn the scan off. The full
# stop is not on this list, because an email address holds one.
ALLOWLIST_FORBIDDEN_CHARACTERS = "*+?[]{}()|^$\\"

# What a file has to be called for its lines to be exempt from the email class.
CODEOWNERS_NAME = os.path.basename(constants.CODEOWNERS_PATH)
ALLOWLIST_NAME = os.path.basename(constants.ALLOWLIST_PATH)

# What a file name may hold when it is repeated back to a person. Everything
# else is replaced, because the name comes out of the shared copy and the
# sentence it lands in is read by a person and by an assistant.
_PLAIN_PATH_CHARACTERS = re.compile(r"[^A-Za-z0-9._/-]")
# The longest piece of a file name that is ever repeated back.
MAX_PATH_IN_SENTENCE = 80

_OWNER_LINE = re.compile(r"^(?:owner|owner_handle)\s*:")
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

EMPTY_ALLOWLIST: FrozenSet[str] = frozenset()

# The code recorded when the allowed-words file could not be trusted.
ALLOWLIST_REJECTED = "allowlist-rejected"


class Hit(object):
    """One thing the scan refuses, named by class and by where it was found."""

    __slots__ = ("pattern_class", "label", "line_number", "context", "is_path")

    def __init__(
        self, pattern_class: str, line_number: int, context: str, is_path: bool = False
    ):
        self.pattern_class = pattern_class
        self.label = redaction_patterns.label_for(pattern_class)
        self.line_number = line_number
        self.context = context
        # A context taken from a file name in a diff is repository-controlled
        # and is sanitized before it is repeated back. A fixed phrase the
        # plugin wrote itself ("the command") is shown as it is.
        self.is_path = is_path

    def __repr__(self) -> str:
        return "Hit(class=%r, context=%r, line=%r)" % (
            self.pattern_class,
            self.context,
            self.line_number,
        )

    def sentence(self) -> str:
        """The one sentence a person is shown. It never holds the value."""
        if self.is_path:
            where = safe_path(self.context)
        else:
            where = self.context or "the command"
        if self.pattern_class == redaction_patterns.TRANSIENT_FOLDER:
            return (
                "GTM Base stopped this because %s is %s." % (where, self.label)
            )
        return "GTM Base stopped this because %s contains %s." % (where, self.label)


def safe_path(value: str) -> str:
    """A file name as a sentence may repeat it back.

    The name is shortened to the cap and everything outside plain letters,
    digits, and the four marks below is replaced with a question mark, so a
    name written to carry instructions cannot say anything in the sentence.
    """
    text = str(value or "")[:MAX_PATH_IN_SENTENCE]
    return _PLAIN_PATH_CHARACTERS.sub("?", text)


# --- The allowed-words list --------------------------------------------------


def load_allowlist(base_root: Optional[str]) -> Tuple[FrozenSet[str], Optional[str]]:
    """Read the base's allowed-words file, or refuse the whole file.

    One entry per line, compared literally, comments allowed. If any line holds
    a character that belongs to a pattern rather than a word, or the file is
    longer or wider than we accept, the whole file is ignored and a code comes
    back, so nothing is quietly let through on the strength of a bad file.
    """
    if not base_root:
        return EMPTY_ALLOWLIST, None
    text = read_text(os.path.join(base_root, constants.ALLOWLIST_PATH))
    if text is None:
        return EMPTY_ALLOWLIST, None
    entries = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) > constants.ALLOWLIST_MAX_LINE_LENGTH:
            return EMPTY_ALLOWLIST, ALLOWLIST_REJECTED
        for character in ALLOWLIST_FORBIDDEN_CHARACTERS:
            if character in stripped:
                return EMPTY_ALLOWLIST, ALLOWLIST_REJECTED
        entries.append(stripped)
        if len(entries) > constants.ALLOWLIST_MAX_LINES:
            return EMPTY_ALLOWLIST, ALLOWLIST_REJECTED
    return frozenset(entries), None


def _allowed(pattern_class: str, value: str, allowlist: Optional[FrozenSet[str]]) -> bool:
    """Whether this exact value was listed as one this base sends on purpose."""
    if not allowlist:
        return False
    if pattern_class in redaction_patterns.NEVER_ALLOWLISTED:
        return False
    return value in allowlist


# --- Scanning ----------------------------------------------------------------


def _scan_line(
    line: str,
    line_number: int,
    context: str,
    allowlist: Optional[FrozenSet[str]],
    exempt_classes: Sequence[str] = (),
) -> List[Hit]:
    hits: List[Hit] = []
    seen = set()
    for pattern_class, value in redaction_patterns.find_in_line(line):
        if pattern_class in exempt_classes:
            continue
        if _allowed(pattern_class, value, allowlist):
            continue
        if pattern_class in seen:
            continue
        seen.add(pattern_class)
        hits.append(Hit(pattern_class, line_number, context))
    return hits


def scan_text(
    text: Optional[str],
    allowlist: Optional[FrozenSet[str]] = None,
    context: str = "the command",
    skip_classes: Sequence[str] = (),
) -> List[Hit]:
    """Read a block of text and return everything in it we refuse to send."""
    if not text:
        return []
    hits: List[Hit] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        hits.extend(_scan_line(line, line_number, context, allowlist, skip_classes))
    return hits


# A command line is not outgoing content. It says where to work, so it holds
# folder names on this computer as a matter of course: the folder a send is run
# from, and the working folder a proposal is prepared in, both of which sit
# inside the person's home folder. Reading those as a leak would refuse every
# ordinary send. Every other class still applies to the command itself.
COMMAND_EXEMPT_CLASSES = (redaction_patterns.LOCAL_PATH,)


def scan_command(
    command: Optional[str], allowlist: Optional[FrozenSet[str]] = None
) -> List[Hit]:
    """Read a command line itself, without treating its folders as content."""
    return scan_text(command, allowlist, "the command", COMMAND_EXEMPT_CLASSES)


def _exempt_classes_for(path: str) -> Tuple[str, ...]:
    """The classes a file's own format makes legitimate."""
    name = os.path.basename(path)
    if name in (CODEOWNERS_NAME, ALLOWLIST_NAME):
        return (redaction_patterns.EMAIL,)
    return ()


def is_transient(path: str) -> bool:
    """Whether a file belongs to a folder that is one person's alone."""
    for folder in constants.TRANSIENT_DIRS:
        if path == folder or path.startswith(folder + "/"):
            return True
    return False


def scan_diff_added_lines(
    diff: Optional[str], allowlist: Optional[FrozenSet[str]] = None
) -> List[Hit]:
    """Read the added lines of a change and return everything we refuse.

    Only lines being added are read. The file a line belongs to comes from the
    `+++ b/<path>` header, so a hit can name the file without naming the line.
    """
    if not diff:
        return []
    hits: List[Hit] = []
    path: Optional[str] = None
    transient = False
    exempt: Tuple[str, ...] = ()
    is_markdown = False
    new_line = 0

    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            path = None
            transient = False
            exempt = ()
            is_markdown = False
            new_line = 0
            continue
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            if target == "/dev/null":
                path = None
                transient = False
                continue
            if target.startswith("b/"):
                target = target[2:]
            # git quotes a path holding unusual characters; keep it as given.
            path = target.split("\t")[0]
            transient = is_transient(path)
            exempt = _exempt_classes_for(path)
            is_markdown = path.endswith(".md")
            if transient:
                hits.append(Hit(redaction_patterns.TRANSIENT_FOLDER, 0, path, True))
            continue
        if raw.startswith("--- "):
            continue
        header = _HUNK_HEADER.match(raw)
        if header:
            new_line = int(header.group(1))
            continue
        if raw.startswith("+"):
            content = raw[1:]
            line_number = new_line
            new_line += 1
            if path is None or transient:
                continue
            line_exempt = exempt
            if (
                is_markdown
                and line_number <= FRONTMATTER_MAX_LINES
                and _OWNER_LINE.match(content)
            ):
                line_exempt = tuple(line_exempt) + (redaction_patterns.EMAIL,)
            for hit in _scan_line(
                content, line_number, path or "the change", allowlist, line_exempt
            ):
                hit.is_path = path is not None
                hits.append(hit)
            continue
        if raw.startswith("-"):
            continue
        if raw.startswith(" ") or raw == "":
            new_line += 1
    return hits


def first_sentence(hits: Sequence[Hit]) -> Optional[str]:
    """The one sentence a person is shown for a set of hits."""
    if not hits:
        return None
    return hits[0].sentence()
