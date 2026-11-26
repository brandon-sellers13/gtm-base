"""The two conditions every path out of this computer has to satisfy.

The check on the command tool enforces both already. A skill that is about to
send something asks these questions first anyway, so the person is told in one
sentence why nothing will be sent before any working folder is made, rather
than being refused halfway through with nothing to show for it.

Both answers come from the same places the command check reads, so the two can
never disagree: the record of a session having read the person's own documents,
and this seat's note of whether the first backup was reviewed.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from . import gate, marker

CODE_SOURCES_READ = gate.REASON_SOURCES_READ
CODE_FIRST_PUSH = gate.REASON_FIRST_PUSH


def sources_read_blocks(session_id: Optional[str]) -> bool:
    """Whether the record of reading somebody's own documents stops a send.

    It is not only this session's own record any more. A record young enough
    to still be about now stops one too, whatever session wrote it, and so
    does a record standing there that cannot be read at all, because both of
    those are what a record somebody wrote over looks like from here.
    """
    return marker.marker_blocks(session_id)


def first_push_unreviewed(base_id: str, root: Optional[str] = None, runner=None) -> bool:
    """Whether this base's sends must still be refused for want of its first backup review.

    Read from what the seat's record says was reviewed and sent, against the
    base itself (`backup.first_push_unreviewed`): the address it reviewed and
    the saved version it reviewed, never a bare yes. With no base folder to
    read against, the answer is yes.
    """
    from . import backup

    return backup.first_push_unreviewed(base_id, root, runner)


def check(
    base_id: str, session_id: Optional[str], root: Optional[str] = None, runner=None
) -> List[Tuple[str, str]]:
    """Every reason nothing may leave this computer right now.

    Each reason is a code and the one sentence the person is shown. An empty
    list means both conditions are satisfied.
    """
    reasons: List[Tuple[str, str]] = []
    if sources_read_blocks(session_id):
        reasons.append((CODE_SOURCES_READ, gate.sentence_for(CODE_SOURCES_READ)))
    if first_push_unreviewed(base_id, root, runner):
        reasons.append((CODE_FIRST_PUSH, gate.sentence_for(CODE_FIRST_PUSH)))
    return reasons
