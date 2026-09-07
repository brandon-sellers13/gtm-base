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


class ConsentError(GtmBaseError):
    """A file was asked for that the person never agreed to have read."""

    default_code = "not-consented"


class SourceRejected(GtmBaseError):
    """A piece of source text may not be used, and the code says why."""

    default_code = "source-rejected"


class GitError(GtmBaseError):
    """A git command failed. The message is a fixed code, never git's output."""

    default_code = "git-failed"

    def __init__(self, message="git-failed", code=None, result=None):
        super(GitError, self).__init__(message, code)
        self.result = result


class LocationError(GtmBaseError):
    """The place a base was going to go is not a place a base may go."""

    default_code = "bad-location"


class IdentityNeeded(GtmBaseError):
    """No work email address could be found, so the person has to be asked."""

    default_code = "identity-needed"


class CreateFailed(GtmBaseError):
    """Building a base stopped part way, and the half built folder is still there.

    It carries the code for what went wrong and the path of the half built
    folder, and nothing else, so the caller can offer the approved draft again
    without any of the failure's own text reaching a person.
    """

    default_code = "create-failed"

    def __init__(self, code="create-failed", partial_path=None):
        super(CreateFailed, self).__init__(code, code)
        self.partial_path = partial_path


class DraftError(GtmBaseError):
    """A draft the assistant wrote back could not be used, and the step says
    which draft it was.

    The code names one thing that is wrong and nothing else, so the caller can
    go back to the same step and ask again without repeating any of the draft's
    own text to a person.
    """

    default_code = "draft-rejected"

    def __init__(self, step, code=None):
        super(DraftError, self).__init__(code or self.default_code, code)
        self.step = step

    def tag(self):
        """The step and the code together, which is how a failure is logged."""
        return "%s:%s" % (self.step, self.code)


class ReviewError(GtmBaseError):
    """A draft could not be written into the base, and the code says why."""

    default_code = "review-refused"

    def __init__(self, message="review-refused", code=None, codes=None):
        super(ReviewError, self).__init__(message, code)
        # The classes an outgoing-content screen found, never the values.
        self.codes = list(codes or [])
