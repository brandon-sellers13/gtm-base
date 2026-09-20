#!/usr/bin/env python3
"""Check one file the client is about to read, and usually say nothing.

The client hands this the request on standard input before it runs its
file-reading tool. Everything it does lives in `gtmbase.read_hook`; this file
exists only to find the library and hand the request over. It prints nothing
for any file that is not under a joined base's context folder, which is nearly
every read, and it exits zero whatever happens.
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


_lib = locate_lib(__file__)
if _lib is None:
    # A read must never fail because the library could not be found, so this
    # one script says nothing at all rather than saying what is wrong.
    raise SystemExit(0)
if _lib not in sys.path:
    sys.path.insert(0, _lib)
# --- end of shim ---


try:
    from gtmbase import read_hook  # noqa: E402
except Exception:
    raise SystemExit(0)


if __name__ == "__main__":
    try:
        raise SystemExit(read_hook.main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0)
