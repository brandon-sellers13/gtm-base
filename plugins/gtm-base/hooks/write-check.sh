#!/bin/sh
# What runs just before the client writes a file, on every file it writes.
#
# The client name is the first argument, the way the Clay plugin does it, so
# one script serves every client. Two rules hold on every path through this
# file: it exits 0, and it prints nothing it is not sure of. A file write must
# never fail because of anything here, and must only ever be refused by the
# one rule the check itself found.
#
# Nearly every write on this computer is not aimed at a folder GTM Base keeps
# for itself, so the work below has to be cheap to say nothing about. The check
# that runs before a file is read already works this way: it looks at one thing
# and leaves.
#
# Unlike the session-start wrapper this one does not explain how to install the
# developer tools, because a missing python3 here is not something to interrupt
# somebody's file write about. It goes quiet instead.

set -u

client="${1:-claude}"

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  plugin_root="$CLAUDE_PLUGIN_ROOT"
else
  plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fi

request=$(cat)

if ! command -v python3 > /dev/null 2>&1; then
  exit 0
fi

# The time limit is best effort. The timeout command is not on every Mac, so
# the work is done without it when it is missing, and the client's own limit is
# what holds.
if command -v timeout > /dev/null 2>&1; then
  output=$(printf '%s' "$request" | timeout 8 python3 "$plugin_root/scripts/write_check.py" --client "$client" 2> /dev/null)
else
  output=$(printf '%s' "$request" | python3 "$plugin_root/scripts/write_check.py" --client "$client" 2> /dev/null)
fi
status=$?

if [ "$status" -ne 0 ]; then
  exit 0
fi

if [ -n "$output" ]; then
  printf '%s\n' "$output"
fi

exit 0
