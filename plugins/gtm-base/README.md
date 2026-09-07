# GTM Base plugin

The plugin half of GTM Base. It keeps a company's marketing context current by
reading meeting notes you drop into the base, drafting proposals with evidence,
recording decisions in a ledger, and asking the owner of a file to confirm that
it is still right.

## Status

Version 0.1.5 is the scaffold plus the check that runs before anything leaves
the computer. `hooks/hooks.json` declares the check on the command tool and the
work done at the start of a session; no skills or agents ship yet, and the
manifest declares no MCP servers by design. The plugin never connects to a
vendor; the sources reach the base through the tools you already have connected
in your own client. The check reads what a send would carry only when the send
comes from a base you have joined or from a working folder GTM Base made for
itself; every other repository on the machine is left alone, apart from the few
refusals that need nothing read.

## How the session-start hook prints what it has to say

A client reads a hook's output either as one JSON object or as plain text, by
its first character, and never as both. So the work at the start of a session is
declared as two entries running the same script, `session-start.sh claude
visible` and `session-start.sh claude context`. The first prints one object
holding the sentence the person reads and writes nothing at all: no session
record, no offer record, no question id, and nothing over the network. The
second prints the plain text the assistant reads and is the one that records the
session, brings the base up to date, issues the question id, and installs the
safeguard. Both work the same decision out from the same inputs.

The client runs the two entries at the same time rather than one after the
other, so neither waits on the other. The one sentence that cannot be worked out
without reaching the shared copy, the one saying an update carried files GTM
Base does not take on its own, is left as a fixed code in this seat's own
settings and said at the start of the next session.

## Layout

- `.claude-plugin/plugin.json` is the manifest.
- `hooks/hooks.json` is where hooks are declared as they land.
- `lib/gtmbase/` is the shared Python library every script uses. It is Python 3
  standard library only and must import cleanly on Python 3.9.

## Note on the repository field

The manifest's `repository` value, the marketplace entry, and the pinned settings
file in `templates/company-base/.claude/settings.json` all name the same public
repository, `https://github.com/brandon-sellers13/gtm-base`. The settings file
pins one exact version by its 40-character id; the release step replaces the
placeholder id with a real one.

## Library

`lib/gtmbase/` is Python 3 standard library only and imports cleanly on Python
3.9. One module per job.

- `constants.py` holds the folder paths, size caps, time windows, and
  vocabularies every other module shares.
- `errors.py` holds the small family of errors, each carrying a short code.
- `fsutil.py` writes files so that a reader sees either the old one or the new
  one, owner only.
- `ids.py` produces every identifier: sources, proposals, questions, runs, and
  the identifier a base carries.
- `gitcmd.py` is the only way this plugin runs git, with prompting turned off
  and a time limit on every call.
- `paths.py` finds the seat folder and the base, and keeps every path inside the
  `context` folder where it belongs.
- `formats.py` reads and writes every file: the inbox item, the ledger entry,
  the confirmation line, the corrections file, the pending file, the staged
  proposal, and the body a reviewer reads.
- `state.py` holds what one seat remembers about one base, and refuses to record
  anything but fixed codes.
- `machine.py` holds account state: the answer to the offer, and the one record
  of which bases this person joined.
- `offer_answer.py` writes down a "not now" answer to the setup offer, which is
  the only one of the three answers with nothing else to record it. Set up and
  join are left to the step that makes a base or joins one.
- `validate.py` checks the map's settings, owner addresses, file names, and the
  marker line that names a proposal wherever it ends up.
- `shim.py` documents and implements the loader every script copies.
- `gate.py` reads any command holding `git` or `gh`, works out whether it would
  send anything, and refuses when what it would send should not leave. It reads
  what a send carries only from a base you have joined, from a folder inside
  one, or from a working folder of its own; a send from any other repository is
  left alone, apart from the refusals that need nothing read.
- `scan.py` reads the added lines of a change, the notes saved with it, and any
  file a GitHub command would send, and reports what it found by class only.
- `redaction_patterns.py` holds those classes: addresses, phone numbers, key
  shapes, web addresses carrying a key, links to shared documents, paths from
  inside a home folder, and text that would be hidden from a reader.
- `marker.py` records that a session has read the person's own documents, which
  is what stops anything leaving for the rest of that session.
- `install_git_hook.py` puts the same check in the folder git looks in, so a
  send from a plain terminal is read as well.
- `stale.py` works out what is out of date, from values the caller hands in.
- `session_start.py` is everything that happens at the start of a session:
  recording the session, bringing a base up to date safely, adding the map, one
  question for one owner, the setup offer, and the question asked about a folder
  that looks like a base.
- `trust_surface.py` decides whether a folder may be trusted as a base at all,
  by checking its settings file and its whole tree.
- `worktree.py` makes and takes away the working folders under the seat
  directory where every change is prepared, so the person's own folder is never
  touched.
- `ghcmd.py` is the only way this plugin runs the GitHub tool, with prompting
  turned off and a time limit on every call.
- `duplicate_check.py` finds out whether this exact change is already under
  review, was already turned down, or is already part of the shared copy.
- `push_conditions.py` asks the two questions that stop anything leaving this
  computer, in the same words the check on the command tool uses.
- `compose_proposal.py` turns one staged change into one review, carrying the
  decision behind it and the record of what changed, and picks up a run that
  stopped halfway rather than starting again.
- `base_reader.py` reads one base into the values the stale library works on:
  the map's settings, every context file with its owners and dates, every
  decision, every confirmation with whoever saved it, and every accepted record
  with the files its own change touched and the one hash over them.
- `stale_check.py` runs the stale rules over a real base and prepares the change
  for each answer, stays safe to repeat, refuses to prepare anything while items
  are waiting to be read, and has a first run mode that says one honest thing.
- `report.py` counts the four numbers for the last four weeks from what is
  already written down, and labels them as this seat's own.
- `confirm.py` is the only thing that writes a confirmation line: it takes the
  answer to the one question a session asked, records a yes in a working folder
  of its own and gets it to the shared copy, leaves a document alone for a while
  on a "not now", turns a no into a prepared change, adds the answer given when
  a document is first written, and holds an answer that could not be sent until
  it can be.

`templates/` holds one real example of each file format, and `scripts/` holds
the copyable loader, the smallest script that uses it, and
`offer_answer.py`, which the assistant runs to record a "not now" answer to the
setup offer. The text the session start hands the assistant names that script by
its full path.

`skills/` holds the skills as they land. `propose-change` takes a staged change,
or a change somebody made by hand, and raises it for review. `stale-check` works
out what has fallen behind the decisions the team wrote down, prepares the
change for each one, and shows the last four weeks of numbers for this seat.
`confirm` is the counterpart to the question a session opens with: it is not
called by name, and it holds the instructions for asking the owner whether a
document is still right and recording what they say.

## Tests

From the root of this repository, run `sh tests/run.sh`.
