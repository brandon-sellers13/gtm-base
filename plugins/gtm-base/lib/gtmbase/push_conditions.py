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

from . import gate, marker, state

CODE_SOURCES_READ = gate.REASON_SOURCES_READ
CODE_FIRST_PUSH = gate.REASON_FIRST_PUSH


def sources_read_blocks(session_id: Optional[str]) -> bool:
    """Whether this session read the person's own documents already."""
    return marker.marker_matches_session(session_id)


def first_push_unreviewed(base_id: str) -> bool:
    """Whether this base has never had its first backup reviewed."""
    seat, _problems = state.load_seat(base_id)
    return not bool(seat.get("first_push_reviewed"))


def check(base_id: str, session_id: Optional[str]) -> List[Tuple[str, str]]:
    """Every reason nothing may leave this computer right now.

    Each reason is a code and the one sentence the person is shown. An empty
    list means both conditions are satisfied.
    """
    reasons: List[Tuple[str, str]] = []
    if sources_read_blocks(session_id):
        reasons.append((CODE_SOURCES_READ, gate.sentence_for(CODE_SOURCES_READ)))
    if first_push_unreviewed(base_id):
        reasons.append((CODE_FIRST_PUSH, gate.sentence_for(CODE_FIRST_PUSH)))
    return reasons
