# The thin runner

This is the contract every skill kept in a company base is built against. It is Plan 1's Unit 3.1 (`docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md`), built from the signed company-skills requirements (`docs/brainstorms/2026-10-10-company-skills-requirements.md`, CS3, CS10 to CS12, CS21, CS26, CS30 and CS31). The code is `plugins/gtm-base/lib/gtmbase/runner.py`, the skill that wraps it is `plugins/gtm-base/skills/use-skill/`, the tests are `tests/test_runner_contract.py`, and the picture is figure 9 of the logic atlas.

## What a skill is

A skill in a base is a folder under `skills/<job>/` holding a `SKILL.md`, any number of references under `references/`, and at least one example under `examples/<example>/`. It holds no code. Its `SKILL.md` settings block declares what it reads:

```
reads_required: [context/goals.md, context/positioning.md]
reads_optional: [context/voice.md]
standard: standards/<job>.md
```

Each declared path must be a context document, a standard or the source map, because those are the documents the moment-of-use check runs on. One folder may be declared among what a skill reads if the base holds it: `context/icps/`, which stands for every segment document the base last saved there, each read and checked like any other declared document. A segment's name differs by company, so it cannot be declared by path, and an empty folder is not a gap (Track 4, Units T4.9 and T4.10). The standard is always required. A skill's own text never names the runner's commands (`use_skill.py`, `use-skill`, `gtmbase`), because in a chat the connector serves the skill and those commands do not exist there. The contract check refuses a skill that does.

## Start

`start` reads every file of the skill once, builds the manifest of what it read (every path and the hash of its exact bytes), and hands back exactly those bytes as the instructions, so nothing can change between the check and the use. It then works through seven steps in order, and the first that fails decides the outcome:

1. Every declared path is a document the check can run on. If not, refused as an invalid declaration, whether the path was declared required or optional.
2. The manifest matches one this computer trusts (approved here, or accepted here after being shown who approved it). If not, refused as untrusted.
3. The base can be read for the check. If not, refused as unreadable.
4. The standard and every required document have a saved copy that can be read. If not, refused as required.
5. The base was asked to stay quiet. If so, not checked: the instructions and documents are handed back with a sentence saying nothing was checked, which is never a statement that they are current.
6. A declared document is flagged by the moment-of-use check, or a context change about it is written down twice. If so, flagged.
7. An optional document has no saved copy. If so, ready with gaps, each gap named. Otherwise, ready.

Every document is read as the base last saved it, and the moment-of-use check runs against that same saved version (`moment.check(..., saved=True)`), so an unsaved edit on the disk changes nothing the check finds. When a declared document has unsaved edits, the run says they were left out.

### Flagged, attended and unattended

A run is unattended when its command says `--unattended`, or when its conversation was marked by an earlier unattended start. The command check (`approval.decide`) marks the conversation before the command runs, so from the runner's first line every approval in that conversation is refused in every permission mode. A mark that cannot be written stops the start. A later start without the word does not make a marked conversation attended.

Attended and flagged, the runner hands back the moment-of-use block and nothing else, and the run is closed at once. The person answers the way the rule for a document about to be used says. If they choose to use the document as it stands, the next start goes ahead and says the document is still flagged. If they choose to fix it first, the work waits for the prepared change. If they say it already reflects the change, the flag clears.

Unattended and flagged, the runner hands back the instructions and documents with the flag said first and the parts that depend on the flagged document named as held (Brandon's call 3). No question is issued and none is written.

## Finish

`finish` takes the work product and every file it was built from, and refuses the work when:

- it holds an email address, a phone number, something shaped like a key, or any other class the screens for a prepared change refuse;
- a money figure or a percentage in it appears in none of those files. This is a lint. It catches a made-up number and cannot tell whether a figure belongs to the right measure, platform or period;
- a marked engine block is not quoted line for line, in order, from the file it names. A block opens with a line `[engine: <file>]` naming one of the files handed in, and closes with `[end engine]`. The markers are visible lines, because the screens refuse hidden text.

Refused work is fixed and handed back. Accepted work closes the run.

## The run lines

`start` writes a "started" line to `skill-runs.jsonl` in the plugin's records for that base, never in the base. It names the job, the date, whether the run was attended, the outcome, each document read with its hash, the flags, what was held, the gaps and the unsaved documents. `finish` writes a "completed" line with the outcome and the hashes of the output and its source files. A start that hands nothing back (refused, or flagged and attended) writes its completed line at once, because nothing ran. A started line with no completed line is an incomplete run, stopping point unknown until it is compared with the skill's own records, such as an engine's audit log. `use_skill.py --incomplete` lists them.

## The contract check

An example is one flat folder holding `input.md` (or `.txt`), the documents it ran against (any other file), `output.md` (the approved output), `expectations.md`, and at least one `wrong-<name>.md` (a deliberately wrong output). The expectations file lists lines of two kinds:

```
- must include: cost per link
- must not include: guaranteed
```

The check runs each output through the same screens as `finish`, with the input and the documents as its source files, and then through the expectations. The approved output must pass and every wrong output must fail. An example missing a part, with no wrong output, or whose expectations ask for nothing, fails. A skill with no examples fails. No model is called. Whether a skill does good work is judged by whoever approves it, reading a real run, and the tests do not claim otherwise.

Unit 4.2b calls `runner.check_skill` before any new or changed skill is shown for approval.

## What the runner does not do

It never decides, never calls a tool, and never writes into the base. It does not add skills to the session start (that is the delivery Unit 4.2b and CS25 describe), and it does not open the skills folder to writes, which stays refused until Unit 4.2b.
