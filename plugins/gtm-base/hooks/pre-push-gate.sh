#!/bin/sh
# The check that reads what a command would send, before the client runs it.
#
# The client name is the first argument, the way the Clay plugin does it, so
# one script serves every client. Claude Code sends a PreToolUse request on
# standard input; Codex sends the same shape and understands the same verdict,
# except that it has no "ask", so both are refused with "deny" here. The
# verdict is built in one place below so a client that wants a different shape
# is a change to one function.
#
# This script never decides anything itself. It finds python3, hands the
# request over, and refuses when that cannot be done, because a check that
# cannot run must not let a send through.

set -u

client="${1:-claude}"

# The one place the verdict shape is built.
emit_deny() {
  reason="$1"
  case "$client" in
    codex | claude | *)
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
      ;;
  esac
}

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  plugin_root="$CLAUDE_PLUGIN_ROOT"
else
  plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fi

request=$(cat)

if ! command -v python3 > /dev/null 2>&1; then
  emit_deny "GTM Base could not run its safety check because python3 is missing; install the developer tools and try again"
  exit 0
fi

printf '%s' "$request" | python3 "$plugin_root/scripts/push_gate.py" --client "$client"
status=$?

if [ "$status" -ne 0 ]; then
  emit_deny "GTM Base's safety check could not complete, so the command was not run"
fi

exit 0
