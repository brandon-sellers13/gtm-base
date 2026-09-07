"""The other name for the module that writes down a "not now" answer.

The plan named this module before the answer had anywhere to be written from,
and 0.1.5 shipped the answer as `offer_answer` because a person answering the
offer had to be recorded a release before setting a base up existed. Everything
lives there. This module exists so the name the plan uses still finds it.
"""

from __future__ import annotations

from .offer_answer import (  # noqa: F401
    COULD_NOT_WRITE,
    NOT_NOW,
    SETUP_RECORDS_ITSELF,
    main,
)

__all__ = ["COULD_NOT_WRITE", "NOT_NOW", "SETUP_RECORDS_ITSELF", "main"]
