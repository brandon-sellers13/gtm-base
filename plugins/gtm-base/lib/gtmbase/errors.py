"""The small family of errors every GTM Base module raises.

Every error carries a short machine-readable `code` as well as its message, so
a caller can report what went wrong without repeating free text that came from
outside the plugin. Hooks catch these and turn them into one fixed sentence.
"""


class GtmBaseError(Exception):
    """Base class for everything this library raises on purpose."""

    default_code = "error"

    def __init__(self, message="", code=None):
        super(GtmBaseError, self).__init__(message)
        self.code = code or (message if message else self.default_code)


class PathError(GtmBaseError):
    """A path was outside the base, or shaped in a way we never accept."""

    default_code = "bad-path"


class ValidationError(GtmBaseError):
    """A file or a value did not match the shape this library requires."""

    default_code = "invalid"


class StateError(GtmBaseError):
    """Stored state could not be read or written in the way the caller asked."""

    default_code = "state"


class GitError(GtmBaseError):
    """A git command failed. The message is a fixed code, never git's output."""

    default_code = "git-failed"

    def __init__(self, message="git-failed", code=None, result=None):
        super(GitError, self).__init__(message, code)
        self.result = result
