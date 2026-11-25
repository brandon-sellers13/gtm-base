#!/bin/sh
# The check that runs right after a command, and usually says nothing.
#
# Before each command the check on commands keeps a copy of the files that
# decide whether GTM Base's checks run. This compares them afterwards and puts
# back only a change that switched the checks off or weakened them, telling
# the person and the assistant what it undid. Claude Code sends the same shape
# after a command that succeeded and after one that failed, so one script
# answers both.
#
# The command has already run by the time this is called, so there is nothing
# to refuse: when python3 is missing or the check cannot finish, it says
# nothing. The check before the command refuses every command when python3 is
# missing, so that case never gets this far.

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

output=$(printf '%s' "$request" | python3 "$plugin_root/scripts/settings_guard.py" --client "$client" 2> /dev/null)
status=$?

if [ "$status" -ne 0 ]; then
  exit 0
fi

if [ -n "$output" ]; then
  printf '%s\n' "$output"
fi

exit 0
