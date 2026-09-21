#!/usr/bin/env python3
"""Check one file the client is about to write, and usually say nothing.

The client hands this the request on standard input before it runs one of its
file-writing tools. Everything it does lives in `gtmbase.write_hook`; this file
exists only to find the library and hand the request over. It says nothing for
any file outside the three places GTM Base keeps for itself, which is nearly
every write, and it exits zero whatever happens.
"""

# --- gtm-base shim (copy from here) ---
import os
import sys


def locate_lib(start):
    """Find the folder holding `gtmbase`: beside the script, then the plugin."""
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


# What this says when it could not do its work at all. The wrapper reads it and
# does its own much smaller check rather than letting the write through
# unlooked at, which is finding V2 of the 2026-09-20 verification round: a
# write over this plugin's own code made the next run fail, and a failure was
# silence, so the write after it went wherever it liked.
COULD_NOT_RUN = 70


_lib = locate_lib(__file__)
if _lib is None:
    raise SystemExit(COULD_NOT_RUN)
if _lib not in sys.path:
    sys.path.insert(0, _lib)
# --- end of shim ---


try:
    from gtmbase import write_hook  # noqa: E402
except Exception:
    raise SystemExit(COULD_NOT_RUN)


if __name__ == "__main__":
    try:
        raise SystemExit(write_hook.main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(COULD_NOT_RUN)
