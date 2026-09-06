#!/bin/sh
# What runs at the start of a session, before the person's first prompt.
#
# The client name is the first argument, the way the Clay plugin does it, so
# one script serves every client. Two rules hold on every path through this
# file: it exits 0, and it writes nothing to the error stream. A session must
# never fail to start because of anything here.
#
# The second argument is which half of the work to do. "visible" prints only
# the sentence the person reads, as one JSON object, and writes nothing at all.
# "context" prints only the plain text the assistant reads and does everything
# that is written down. Both are declared, so a client that reads a hook's
# output as one object or as plain text but never as both still shows the
# person their sentence. With no second argument the combined form is used.
#
# The prerequisite check comes first and is done in the shell, not in Python,
# because on a Mac with no developer tools the git and python3 names exist as
# stubs that pass a plain lookup and then open a dialog and fail. Asking
# xcode-select is the only check that tells the truth there.

set -u

client="${1:-claude}"
part="${2:-both}"

install_sentence='GTM Base needs the developer tools before it can run. On a Mac, open Terminal and run: xcode-select --install. Then open Claude Code again.'

emit_message() {
  printf '{"systemMessage":"%s"}\n' "$1"
}

if [ "$(uname -s 2> /dev/null)" = "Darwin" ]; then
  if ! xcode-select -p > /dev/null 2>&1; then
    emit_message "$install_sentence"
    exit 0
  fi
else
  if ! command -v git > /dev/null 2>&1 || ! command -v python3 > /dev/null 2>&1; then
    emit_message "$install_sentence"
    exit 0
  fi
fi

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  plugin_root="$CLAUDE_PLUGIN_ROOT"
else
  plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fi

if ! command -v python3 > /dev/null 2>&1; then
  emit_message "$install_sentence"
  exit 0
fi

# The time limit is best effort. The timeout command is not on every Mac, so
# the work is done without it when it is missing, and the client's own limit
# is what holds.
if command -v timeout > /dev/null 2>&1; then
  output=$(timeout 14 python3 "$plugin_root/scripts/session_start.py" --client "$client" --part "$part" 2> /dev/null)
else
  output=$(python3 "$plugin_root/scripts/session_start.py" --client "$client" --part "$part" 2> /dev/null)
fi
status=$?

if [ "$status" -ne 0 ]; then
  exit 0
fi

if [ -n "$output" ]; then
  printf '%s\n' "$output"
fi

exit 0
