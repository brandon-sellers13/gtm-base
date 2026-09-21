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
# check says it could not run, this does a much smaller one of its own.
#
# That smaller one reads the path and nothing else. The third look found the
# first version of it reading the whole request as one piece of text, and the
# client puts the path of the session transcript on every request it sends,
# under the assistant's own folder in the person's home folder. So every file
# write on this computer was refused the moment the real check could not run,
# including the write that would have repaired it. What is read now is only the
# file the tool was about to write, taken out of the request by name, and the
# names are matched as whole pieces of a path rather than as text anywhere in
# it. A request this cannot read at all is allowed, because a check that
# understood nothing has found nothing.

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
# together, so the words a person reads live in one place. It names installing
# the plugin again on purpose: that is how the installed copy's own files are
# repaired, and writing over them is the one thing this will not allow.
could_not_check='GTM Base could not run its own safety check just now, and this file is in a folder it keeps for itself, so nothing was written. Installing the plugin again is what repairs its own files, and it is worth doing if this keeps happening.'

refuse_without_checking() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$could_not_check"
}

# Every file the request says the tool is about to write, and nothing else. The
# three names are the ones the file tools carry a path under. The path of the
# session transcript is deliberately not one of them: it is on every request
# the client sends, it is always under the assistant's own folder, and it is
# not a file anything here is writing.
named_files() {
  printf '%s' "$request" |
    grep -o '"[a-z_]*path"[[:space:]]*:[[:space:]]*"[^"]*"' 2> /dev/null |
    grep -v '^"transcript_path"' |
    sed 's/^[^:]*:[[:space:]]*"//; s/"$//'
}

# Whether one path is inside one of the places GTM Base keeps. Finding N2 of
# the final confirmation pass narrowed this a long way. It used to refuse any
# path holding either folder name anywhere in it, which is an ordinary
# repository's own exclude file, a project's folder of assistant commands, and
# everything the assistant keeps under the person's home folder, including its
# own memory. A Mac without the developer tools stays in this state for ever,
# so what it refuses has to be what the real check refuses and no more.
#
# Three things, then. The folder the plugin is installed in. The folder GTM
# Base keeps its records in. And the two folders inside a base, which are told
# apart from the same two names anywhere else by looking for the map beside
# them, the way the real check does by walking up from the file.
is_protected() {
  candidate=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  lower_plugin=$(printf '%s' "$plugin_root" | tr '[:upper:]' '[:lower:]')
  case "$candidate" in
    "$lower_plugin" | "$lower_plugin"/*) return 0 ;;
  esac
  seat="${GTM_BASE_HOME:-$HOME/.gtm-base}"
  lower_seat=$(printf '%s' "$seat" | tr '[:upper:]' '[:lower:]')
  case "$candidate" in
    "$lower_seat" | "$lower_seat"/*) return 0 ;;
  esac
  for name in ".git" ".claude"; do
    case "$candidate/" in
      */"$name"/*)
        # Everything before that folder name is the folder holding it, and a
        # folder holding the map is a base. The length is measured on the
        # folded spelling and the characters are taken from the one on the
        # disk, so a name written in other letters finds the same folder.
        folded=${candidate%%/"$name"/*}
        before=$(printf '%s' "$1" | cut -c "1-${#folded}")
        if [ -f "$before/context/map.md" ]; then
          return 0
        fi
        ;;
    esac
  done
  return 1
}

# The folder the session is open in, which a path written from where somebody
# is standing is joined onto.
here() {
  printf '%s' "$request" |
    grep -o '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' 2> /dev/null |
    sed 's/^[^:]*:[[:space:]]*"//; s/"$//' |
    head -n 1
}

# The smaller check. Nothing at all comes back when no path could be read out
# of the request, because a check that understood nothing has found nothing.
fall_back() {
  if ! command -v grep > /dev/null 2>&1 || ! command -v sed > /dev/null 2>&1; then
    return
  fi
  found=$(named_files)
  [ -n "$found" ] || return
  cwd=$(here)
  printf '%s\n' "$found" | while IFS= read -r named; do
    [ -n "$named" ] || continue
    case "$named" in
      /*) ;;
      *) [ -n "$cwd" ] && named="$cwd/$named" ;;
    esac
    if is_protected "$named"; then
      refuse_without_checking
      break
    fi
  done
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

# A slow start and a written-over file end the same way here on purpose: the
# smaller check looks at the one file the tool was about to write, and anything
# that is not one of GTM Base's own places goes through. Running out of time is
# not evidence of anything, and the safety check that runs before a command
# fails closed by itself whatever happens here.
if [ "$status" -ne 0 ]; then
  fall_back
  exit 0
fi

if [ -n "$output" ]; then
  printf '%s\n' "$output"
fi

exit 0
