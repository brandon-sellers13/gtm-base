# Changelog

## 0.1.0

- Manifest no longer names hooks/hooks.json; Claude Code loads that file on its own and refused the plugin when it was named twice (found on the first live install, 2026-09-06). The offer and the join guide now say to type the answer as the first message.

- An owner accepting a prepared change now counts as that owner saying the
  affected document is right, on the day they accepted it, so the clock starts
  again rather than the same document being asked about next session. When the
  person who accepted it does not own the document, nothing changes: the record
  settles the decision it names and the document still waits on its owner.
  Brandon's decision of 2026-09-05.
- Session-start update refuses anything under the settings folder (`.claude/`), including the one file the join-time trust check allows, because a changed settings file would re-point the plugin itself.

Correctness review fixes (C1, C2, C3, C4, C5, C6, C7, and SEC-5).

- An owner's answer that names the decision it was given about now settles that
  decision whatever day the answer carries, which is what a yes on the day the
  decision was written down looks like (C1).
- A question is used up only when the answer is recorded. Asking the owner what
  changed, refusing something in what they said that must never leave, and an
  inbox with items still waiting are all decided first, so the answer the
  sentence asks for can be given to the same question (C2).
- Answers waiting to be sent are held as a list rather than one at a time, so a
  morning offline can hold several and none is written over. Sending them again
  clears each one on its own and keeps only the ones that still cannot go (C3).
- A run repeated after its own review opened now finishes and tidies up rather
  than reporting the seat's own review as somebody else's (C4).
- Every date compared with a date in the base is the day it is where the person
  is sitting. Only the time on a confirmation line and the moments in this
  seat's own files stay in coordinated universal time (C5).
- A path a decision names that GTM Base will not write is recorded once rather
  than on every reading, and a run that is only looking records nothing at
  all (C6).
- A working folder left with no line of work on it is put back on its own
  before anything is sent, and a failure preparing one is reported as a refusal
  rather than raised (C7).
- The file a change is written to is checked in the folder it is written in, so
  a name that is an ordinary file in one copy of a base and a link to somewhere
  else in another is refused (SEC-5).
- Also: a no about the calendar names the question it answers, so two answers
  about one file weeks apart are two changes; the report window is the 28 days
  it says it is; a reminder put off comes back on the day it says, the same
  boundary a document put off for now uses; and a joined base cannot be pointed
  at a folder another base already claims.

## 0.1.0

Security review fixes (SEC-1, SEC-2, SEC-3, SEC-4, SEC-6, SEC-7, SEC-8, SEC-9,
SEC-10, SEC-11, SEC-12, and C8): the check that reads a command now strips
quotes and backslashes before it looks for git, accounts for every part of a
command that names git, follows a command written inside another one, reads a
send against the folder the command names, refuses the settings and options
that hand git another program to run, and refuses any command that touches the
folder holding this seat's own records. The update from the shared copy now
refuses the same set of names the folder check refuses, compared the same way,
and refuses an update carrying a link. A file name from the shared copy is
checked before it is repeated back, the map is held apart by marks the map
itself cannot end, and the safeguard folder is only made once every reason to
refuse has been ruled out.

Unit 10, the confirmation flow: the owner's answer to the one question a
session asks.

- Added the `confirm` skill and its script. The skill is not one a person calls
  by name. It carries the instructions for showing the document, showing the
  decision behind the question when there is one, asking in plain words, saying
  what each answer does before it is given, and calling the script in the same
  turn as the answer. The assistant never writes in the confirmations folder
  itself.
- Added `lib/gtmbase/confirm.py`, the only thing that ever writes a
  confirmation line. It requires a question this session was given, that has
  not been answered and is less than an hour old, and it refuses while anything
  is still waiting to be read in the inbox, without using the question up, so
  the same question can be answered once those items have been read.
- A yes writes one line carrying the file, the date, the time, the reason it was
  asked, the decision when there is one, and the question, and no address at
  all. Identity is read back from the saved work that added the line. The line
  is prepared in a working folder of its own, read by the same check every send
  passes, and added to the shared copy. The person's own folder is left exactly
  as it is.
- A yes that cannot reach the shared copy is never lost. When the shared copy
  moves underneath it, the answer is written again from where the shared copy
  is now and sent once more; when that fails too, the answer is held in this
  seat's own settings and the next session or the next check sends it.
- A base with no shared copy of its own moves the person's own folder forward by
  that one answer, and only when there is nothing unsaved in it.
- A base where somebody reads every change before it reaches the shared line
  gets a review for the answer instead, and the skill says so.
- A "not now" leaves the document alone for the days the map sets and writes
  nothing anywhere. A no becomes a prepared change: for a question about a
  decision it is the same prepared change the stale check writes, carrying the
  owner's words as evidence; for a question about the calendar the owner is
  asked what changed first, and their answer becomes the change.
- Added a setup path for the answer given when a document is written for the
  first time. It adds the line and stages it, saves nothing, is allowed once per
  document, and only for a document that is not part of the base yet.
- Added the list of questions still waiting for an answer, which the script
  prints when it is run without one.
- The question the hook adds to a session now names the script and says the
  confirmations folder is never written by hand.

## 0.1.0

Unit 9b, the stale check a person runs and the four week report.

- Added the `stale-check` skill, its script, and `references/rules.md`, which
  states every rule the check follows in plain words: how a decision and a
  document are compared, what counts as a confirmation, the one exemption for
  the day a base is set up, when an accepted record settles a decision, what a
  decision that names no files leads to, and the identifier that stops the same
  work being done twice.
- Added `lib/gtmbase/stale_check.py`. It asserts the base is on the main line of
  work the team shares, brings it up to date when it has a shared copy and
  treats a base with none as up to date, prepares nothing while items are
  waiting to be read in the inbox but still lists what is out of date, reads the
  base, runs the rules, and writes one prepared change for every document a
  decision has moved past. For a decision that names no files it prepares the
  list of files instead, for the owner to approve. It lists the decisions that
  have come up for review and keeps them for the next session, reports a quiet
  ledger with the way to stop it being mentioned, and lists what could not be
  read. A look only run says what it would prepare and writes nothing.
- Added the first run mode: one honest finding, looked for in a fixed order and
  worked out fresh every time, saying either a document the person skipped, that
  no decision has been written down, that a document is older than the decision
  it should reflect, or that nothing is out of date yet and naming the first
  date it will watch.
- Added `lib/gtmbase/report.py`, the four numbers for the last four weeks, all
  of them labelled as this seat's own: what GTM Base caught, how often a
  question was answered yes with every question asked in the denominator, how
  often a proposal was turned down, and how the material read into the base
  arrived. Nothing is estimated, and a zero is written out as a zero.
- Added `lib/gtmbase/base_reader.py`, the one way a base is read into the values
  the stale library works on. The hook at the start of a session and the stale
  check now share it, so two readings of the same folder can never disagree.
- Fixed the rule for the hash an accepted record carries, which had two forms
  and so could never match for a proposal touching more than one file. There is
  now one rule: the hash is taken over every path in the `context` folder the
  record lists, in the order it lists them, read as the accepted change left
  them and joined end to end. `references/pr-body-rules.md` says the same thing.
- Allowed a proposal to name a decision the base already holds without writing a
  second copy of it. A marker naming the proposal's own identifier as the
  decision still means a new decision the proposal has to carry.
- Moved the record of an update this seat refused out of a file of its own and
  into this seat's own settings, as a date, one fixed code, and the refused
  paths as hashes.
- Made the check on the command tool and the check a skill runs before it
  prepares anything ask the same question in one place, so they cannot disagree
  about whether the first send from a base has been reviewed.

## 0.1.0

Unit 7, turning a staged change into a review the team can read.

- Added the `propose-change` skill, its script, and
  `references/pr-body-rules.md`, which says what the text of a proposal has to
  contain, in what order, and how the hash it carries can be worked out again
  from the change itself.
- Added `lib/gtmbase/compose_proposal.py`: it reads the staged file, refuses a
  change to the map, to the settings at the top of a file, or to anything
  outside the context folder, asks the two conditions that stop anything
  leaving the computer, reads everything the proposal would carry for contact
  details, keys, links, and hidden text, searches for the same change
  everywhere it might already be, applies the change in a working folder of its
  own, writes the decision and the record of what changed beside it, sends it,
  and opens the review. Every step is safe to repeat: a run that stopped
  halfway picks up the folder it left, never saves the same work twice, and
  never opens a second review.
- Added the path for a change somebody made by hand: their own file is left
  exactly as they left it, the source they state becomes the evidence, and the
  same checks run before anything is sent.
- Added `lib/gtmbase/worktree.py`, the working folders under the seat
  directory, one per staged change and one for confirmations. The person's own
  folder never changes what it is on and never loses what they were doing.
- Added `lib/gtmbase/duplicate_check.py`, which finds the one marker line a
  proposal carries in the reviews on the shared copy and in the records already
  accepted, so the same change is never raised twice and one that was turned
  down comes back only when the person says so.
- Added `lib/gtmbase/ghcmd.py`, the one way this plugin runs the GitHub tool,
  and `lib/gtmbase/push_conditions.py`, which asks the same two questions the
  check on the command tool asks, so a skill can say why nothing will be sent
  before it prepares anything.
- Added the decision itself to `templates/proposal-staging.md`, which carried
  only its settings before and so could never have produced a usable entry.

## 0.1.0

Unit 3, what happens at the start of a session.

- Added `hooks/session-start.sh`, declared in `hooks/hooks.json` as a
  SessionStart hook with no matcher and a 15 second limit, so every kind of
  session start is seen. It checks the prerequisites itself before Python runs,
  because on a fresh Mac the git and python3 names exist as stubs that pass a
  plain lookup, so it asks `xcode-select` instead and prints one install
  sentence when that fails. It exits 0 on every path and writes nothing to the
  error stream.
- Added `scripts/session_start.py` and `lib/gtmbase/session_start.py`. In a base
  this account has opened, every session records its session id and the client,
  and a session that is starting or being picked up again also brings the base
  up to date with the shared copy, adds the map with a trust note and a length
  cap, and asks at most one owner one question with a single use id. An update
  whose incoming files touch the settings folder, an instruction file, or any
  code file is refused with one fixed sentence and the last known good map. A
  base with no shared copy skips the update, says nothing about it, and still
  asks its question. A base still missing a required file offers to finish
  setting it up instead, issues no question id, and writes nothing to the
  asked log.
- Added the setup offer: the first session on an account with no base shows it
  on screen and primes the assistant to act on the answer, once per session id,
  and after a not now it comes back only in an empty folder or a folder that
  looks like a base.
- Added `lib/gtmbase/trust_surface.py`: before a folder that looks like a base
  is offered as one, its whole tree is checked for instruction files, agent
  folders, code files, a folder of plugins, anything under the settings folder
  other than the settings file itself, and links, with every name compared after
  case folding and Unicode composition, and the settings file itself checked for
  exactly two keys, the GTM Base repository, a pinned forty character version,
  and this plugin.
- Added `templates/injection.md`, `templates/offer.md`,
  `templates/base-shaped-question.md`, and `templates/continue-setup.md`, so
  every sentence a person reads sits in one reviewable place.
- Unverified assumption: that one hook may return both the text the assistant
  reads and the text the person sees in a single object. It has not yet been
  seen render in a real session. `render_output` in `session_start.py` is the
  one place that changes if the fallback of two hook entries is needed.

Unit 4, the check before anything leaves the computer.

- Added `hooks/pre-push-gate.sh` and declared it in `hooks/hooks.json` as a
  PreToolUse hook on the command tool with a 20 second limit. It finds python3,
  hands the request over, and refuses when either step cannot be done.
- Added `scripts/push_gate.py` and `lib/gtmbase/gate.py`: it reads any command
  holding `git` or `gh`, works out whether the command would send anything,
  refuses the GitHub commands no skill uses, and reads what a send would carry
  before it runs.
- Added `lib/gtmbase/scan.py` and `lib/gtmbase/redaction_patterns.py`: the added
  lines of a change, the notes saved with it, the command itself, and any file a
  GitHub command would send are read for addresses, phone numbers, key shapes,
  web addresses carrying a key, links to shared documents, paths from inside a
  home folder, and text that would be hidden from a reader. A refusal names the
  file and the kind of thing found, never the thing itself.
- Added the allowed-words file rules: exact words only, comments allowed, caps
  on how many and how long, the whole file thrown away if any line holds pattern
  syntax, and no word can ever excuse a key or a folder that is yours alone.
- Added `lib/gtmbase/marker.py`, the record of a session having read the
  person's own documents, and the two session conditions the check enforces:
  nothing leaves while that record matches, and nothing leaves a base whose
  first backup has not been reviewed.
- Added `lib/gtmbase/install_git_hook.py`, which puts the same check in the
  folder git looks in, moves an existing one aside and still runs it, follows a
  folder named in the account settings, never writes a file the team shares, and
  records a fixed code when it could not be installed.

Unit 1, the scaffold. Nothing acts yet.

- Added the marketplace manifest and the plugin manifest. The plugin manifest
  declares no MCP servers.
- Added `hooks/hooks.json` as an empty event map, so the plugin installs and no
  hook fires.
- Added `lib/gtmbase/constants.py` with the folder paths, size caps, time
  windows, refusal sets, and placeholders the later units share.
- Added the shared library the later units build on: `formats.py` for every
  file the plugin reads or writes, `ids.py` for identifiers that stay the same
  across runs, `paths.py` for the seat folder and for keeping a path inside the
  base, `state.py` for what one seat remembers, `machine.py` for the one record
  of what this account joined, `validate.py` for the map's settings and owner
  addresses, `gitcmd.py` for the single way this plugin runs git, `fsutil.py`
  for writes that either happen or do not, `errors.py`, and `shim.py` for the
  loader every script copies.
- Added the six file templates under `templates/` and a fixture of every
  artifact under `tests/fixtures/`, each one parsed by a test.
- Added `scripts/_shim_template.py` and `scripts/gtmbase_version.py`, the
  smallest script that uses the loader and the target of the packaging test.
- Added the `company-base` template, the join guide, the test runner, and a fake
  GitHub command line tool for tests.
- Added `lib/gtmbase/stale.py`, the stale-check library: it works out which
  context files a decision has moved past, which have gone too long without
  the owner's yes, and the one honest finding a first run reports, from values
  the caller hands in and nothing it fetches itself.
