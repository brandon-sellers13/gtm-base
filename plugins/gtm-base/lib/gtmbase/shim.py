"""How every script finds this library, wherever it was copied to.

A script that ships inside the plugin sits next to `lib/`. A skill folder
copied out of the plugin does not, so it falls back to the plugin folder the
client names, and then to an override a person can set by hand. When none of
the three works it prints one fixed sentence and stops, because a script that
cannot find its library has nothing useful to say.

Copy this block, unchanged, at the top of any script. It must run before the
script imports anything from this library.

    import os
    import sys

    def locate_lib(start):
        here = os.path.dirname(os.path.abspath(start))
        while True:
            candidate = os.path.join(here, "lib")
            if os.path.isfile(os.path.join(candidate, "gtmbase", "__init__.py")):
                return candidate
            parent = os.path.dirname(here)
            if parent == here:
                break
            here = parent
        for folder in (
            os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "lib"),
            os.environ.get("GTM_BASE_LIB", ""),
        ):
            if folder and os.path.isfile(
                os.path.join(folder, "gtmbase", "__init__.py")
            ):
                return folder
        return None

    _lib = locate_lib(__file__)
    if _lib is None:
        sys.stderr.write(
            "GTM Base could not find its library; reinstall the plugin with: "
            "claude plugin install gtm-base@gtm-base\n"
        )
        raise SystemExit(3)
    if _lib not in sys.path:
        sys.path.insert(0, _lib)
"""

from __future__ import annotations

import os
import sys
from typing import Optional

NOT_FOUND_SENTENCE = (
    "GTM Base could not find its library; reinstall the plugin with: "
    "claude plugin install gtm-base@gtm-base"
)

EXIT_NO_LIBRARY = 3


def locate_lib(start: str) -> Optional[str]:
    """Find the folder holding `gtmbase`, or return None when there is none."""
    here = os.path.dirname(os.path.abspath(start))
    while True:
        candidate = os.path.join(here, "lib")
        if os.path.isfile(os.path.join(candidate, "gtmbase", "__init__.py")):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for folder in (
        os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "lib"),
        os.environ.get("GTM_BASE_LIB", ""),
    ):
        if folder and os.path.isfile(os.path.join(folder, "gtmbase", "__init__.py")):
            return folder
    return None


def ensure_lib(start: str) -> str:
    """Put the library on the import path, or stop with the fixed sentence."""
    folder = locate_lib(start)
    if folder is None:
        sys.stderr.write(NOT_FOUND_SENTENCE + "\n")
        raise SystemExit(EXIT_NO_LIBRARY)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return folder
