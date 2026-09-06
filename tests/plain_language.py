"""The plain-language lint every user-facing document must pass.

User-facing documents are written for a marketer, so they never use the words a
version-control tool uses, and they never use an em dash or an en dash. Later
units import this helper rather than repeating the rules.
"""

import re

from gtmbase import constants


EM_DASH = "\u2014"  # the em dash, written as an escape so the file holds none
EN_DASH = "\u2013"  # the en dash, written as an escape so the file holds none

# Inflections the lint must catch alongside each banned word.
_INFLECTIONS = {
    "commit": ["commit", "commits", "commited", "committed", "committing"],
    "branch": ["branch", "branches", "branched", "branching"],
    "pull request": ["pull request", "pull requests"],
    "merge": ["merge", "merges", "merged", "merging"],
    "rebase": ["rebase", "rebases", "rebased", "rebasing"],
    "clone": ["clone", "clones", "cloned", "cloning"],
}


def _pattern_for(word):
    forms = _INFLECTIONS.get(word, [word])
    alternatives = "|".join(re.escape(form).replace("\\ ", r"\s+") for form in forms)
    return re.compile(r"\b(?:" + alternatives + r")\b", re.IGNORECASE)


_PATTERNS = [(word, _pattern_for(word)) for word in constants.BANNED_GIT_WORDS]


def find_banned(text):
    """Return a list of (word, line_number) for every banned word found."""
    found = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for word, pattern in _PATTERNS:
            if pattern.search(line):
                found.append((word, line_number))
    return found


def find_dashes(text):
    """Return a list of (dash, line_number) for every em dash and en dash."""
    found = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if EM_DASH in line:
            found.append((EM_DASH, line_number))
        if EN_DASH in line:
            found.append((EN_DASH, line_number))
    return found


def assert_plain(testcase, path):
    """Fail the test case when the file at path breaks either rule."""
    with open(str(path), encoding="utf-8") as handle:
        text = handle.read()
    banned = find_banned(text)
    testcase.assertEqual(
        [], banned, "banned words in %s: %s" % (path, banned)
    )
    dashes = find_dashes(text)
    testcase.assertEqual(
        [], dashes, "em or en dashes in %s: %s" % (path, dashes)
    )
