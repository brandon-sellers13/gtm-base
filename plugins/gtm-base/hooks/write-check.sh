#!/bin/sh
# What runs just before the client writes a file, on every file it writes.
#
# The client name is the first argument, the way the Clay plugin does it, so
# one script serves every client. Two rules hold on every path through this
# file: it exits 0, and it prints nothing it is not sure of. A file write must
# never fail because of anything here, and must only ever be refused by a rule
# that was actually run.
#
# Nearly every write on this computer is not aimed at a folder GTM Base keeps
# for itself, so the work below has to be cheap to say nothing about. The check
# that runs before a file is read already works this way: it looks at one thing
# and leaves.
#
# Unlike the session-start wrapper this one does not explain how to install the
# developer tools, because a missing python3 here is not something to interrupt
# somebody's file write about. It goes quiet instead.
#
# There is one thing it will not go quiet about. A reviewer of the 2026-09-20
# release wrote over the plugin's own code with an ordinary file write, which
# made every later run of the real check fail to start, and a check that failed
# to start used to mean the write went through unlooked at. So when the real
# check says it could not run, this does a much smaller one of its own on the
# text it was handed: a request that so much as mentions one of the places GTM
# Base keeps is refused, and everything else is let through, because a plugin
# that is broken must never stop somebody working on this machine.

set -u

client="${1:-claude}"

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  plugin_root="$CLAUDE_PLUGIN_ROOT"
else
  plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fi

request=$(cat)

# The one sentence said when the real check could not run. It is the same
# sentence `write_hook.COULD_NOT_CHECK` holds, and a test holds the two
# together, so the words a person reads live in one place.
could_not_check='GTM Base could not run its own safety check just now, and this file is in a folder it keeps for itself, so nothing was written. Try again, and if it keeps happening the plugin needs installing again.'

refuse_without_checking() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$could_not_check"
}

# The smaller check. It reads the request as text, nothing more, and it names
# the folders by name rather than working anything out.
fall_back() {
  seat_name=".gtm-base"
  case "$request" in
    *"$seat_name"* | *"$plugin_root"* | *".git"* | *".claude"*)
      refuse_without_checking
      return
      ;;
  esac
  if [ -n "${GTM_BASE_HOME:-}" ]; then
    case "$request" in
      *"$GTM_BASE_HOME"*)
        refuse_without_checking
        return
        ;;
    esac
  fi
}

if ! command -v python3 > /dev/null 2>&1; then
  fall_back
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
  fall_back
  exit 0
fi

if [ -n "$output" ]; then
  printf '%s\n' "$output"
fi

exit 0
