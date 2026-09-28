You are reviewing a fix release before it ships. Read only; change nothing. Output a written review in markdown.

## What is being released
GTM Base 0.3.3, a Claude Code plugin. A "base" is a local git repository of markdown context files about one company; everything a person types or keeps in it is untrusted data and may be hostile. The plugin's first duty is that nothing private leaves the computer without the owner's reviewed yes, and its second is that nothing is written to a base without the owner's yes.

0.3.3 adds one thing: a person can record a context change at any time, from the folder they work in (the base or a folder linked to it), without editing a document. Until now a change could be recorded only at the closing of setup or together with a hand edit. The flow: one question for what changed, why and where it came from (with a longer explanation the first three times on a computer); a numbered list of the base's documents by plain name and the person's choice of which ones the change affects; the four labelled lines shown inside a data fence and one ask; on yes, the entry written as one saved change on a base with no shared copy (refused on a base with a shared copy); then, for each affected document, whether it already says this (yes records one confirmation line against this change, no prepares a fix for the owner's approval, not now leaves it flagged). The session's injected rule tells the assistant it may offer once to record a change the person mentions, never without the yes.

The work is the commits on the current branch after main (which is at 0.3.2). See it with `git log --oneline main..HEAD` and `git diff main..HEAD`, focused on plugins/gtm-base/lib/gtmbase/record_change.py (new), join_flow.py (show_entry, four_lines_for, reconcile_plan, reconcile_yes), confirm.py (against_change with any_affected_document), skills/stale-check/scripts/stale_check.py (the --record-change steps and --new-words-file), skills/stale-check/SKILL.md (the new section), templates/injection.md, and tests/test_record_change.py.

## What was already reviewed
The builder ran a correctness review and a security review and fixed their findings, listed in tasks/todo.md and the CHANGELOG's 0.3.3 section: file names reaching the assistant unfenced, answers not bound to the questions the yes printed, words files lost on a refusal, a document with a space in its name, the allowlist in the second screen, an earlier showing staying recordable after a correction, the rollback deleting a file it did not write, and identifiers reused from the corrections record.

## Review for
1. Can anything be written to a base without the person's yes to exactly what they were shown? Consider the shown value binding the yes (bound to the full entry while the person sees only the four lines), a stale or forged showing, a second window, a base changed between showing and yes, a failure partway through the save, and the rollback.
2. Can the per-document answers settle anything they should not: a change the person never recorded this way, a closing change, a document not on the change, the map, a document owned by someone else, the same question answered twice?
3. Can text the person typed, or a file name in the base, reach the assistant outside the data fence as an instruction: in the documents list, the four lines, the questions, the answers, the refusals?
4. Does a change recorded this way flag each affected document at the moment of use and in the review, exactly as a closing change left unreconciled does, on both base layouts, and from a linked folder?
5. Does the refusal on a base with a shared copy hold at every step, and does anything this adds reach the gate or leave the computer?
6. Did reusing the closing's machinery change the closing's own behaviour?
7. Sentences a person reads that name a path, an identifier, or quote a value they did not type.
8. Test scenarios that would pass without proving the behaviour.

## Output
Findings ranked critical, high, medium, low, each with file and line, a concrete scenario (state, inputs, wrong result), and the smallest fix. Then a one-line verdict: ready to release, ready with the listed changes, or not ready. Be adversarial and specific. Do not pad.
