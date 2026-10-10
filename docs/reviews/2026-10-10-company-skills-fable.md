# Review of `docs/brainstorms/2026-10-10-company-skills-requirements.md` (revision 1), Fable 5.1

Run by the planning session on 2026-10-10, read only, against `docs/reviews/2026-10-10-company-skills-brief.md`. Line numbers refer to revision 1 of the document unless a file is named.

## Blocker

**B1. CS11 lets a version nobody approved become trusted through "accept".** CS11 never says what happens when there is no approval record to show, which is the common case for a hand edit committed to `skills/` outside Claude's file tools. Plan 1 Unit 4.2b's integration scenario reads the gap permissively. *Fix:* a version with no approval record, or whose record's hashes do not match the files, cannot be accepted; the only way forward is a change approved under CS3. Accepting goes through Claude Code's own question and does not repeat the authority check.

## High

- **H1. CS3 promises more than GTM Base can enforce for documents.** Nothing binds what is read to what was approved for documents under `context/`, `standards/` and `access/`; the write hook deliberately leaves context files alone. *Fix:* state the limit in CS14: the rule governs what is approved and recorded; for a document it does not stop an edit, for a skill it does.
- **H2. CS21 forbids the keys every base document is read by** (`kind`, `sources`, `status`, `business`, `last_confirmed`), which Unit 2.1 and the stale lifecycle need. *Fix:* add them.
- **H3. CS21's `reads` key cannot be written in the settings grammar**, which holds plain values and lists, nothing nested. *Fix:* `reads_required` and `reads_optional`, each a list.

## Medium

- **M1.** CS19's naming rule refuses `SKILL.md`. *Fix:* except `SKILL.md` itself.
- **M2.** CS2 does not say which of the map's two settings places holds `administrators:`; the body section reads whole numbers only. *Fix:* the block at the top of the map, beside `owner:`.
- **M3.** CS9 says nothing about how a confirmation records its address and role. *Fix:* recorded the same way; older lines judged by the owner line.
- **M4.** CS6 leaves the two-yes mechanics open. *Fix:* two approvals of the same manifest, in either order; the skill waits outside `skills/`; either yes alone writes nothing.
- **M5.** CS30 says "a conversation started as unattended" while the plan marks it at the runner's start. *Fix:* from the moment the runner's start marks it, and the scheduled prompt makes that its first command.
- **M6.** Whether an installed skill passes the proposal screens is not said. *Fix:* the same screens, owner's address exempt.
- **M7.** Roadmap question 2 is not answered path by path. *Fix:* name the four admission paths.
- **M8.** Next Steps briefs 4.2a and 4.2b only. *Fix:* add Units 3.1 and 3.6.
- **M9.** CS5 does not let anyone create a standard. *Fix:* add standards.

## Low

- **L1.** CS19 narrows the plan's `examples/**` without saying so.
- **L2.** "64 KB" and "18.6 KB" leave the unit open. *Fix:* bytes.
- **L3.** Where a skill's owner is read from, and when it is stamped, is not said.
- **L4.** CS2's "single address" is not what the owner-line parser accepts.
- **L5.** CS25's "one-sentence description" is not what the first skill has.
- **L6.** The required replay is a duty of whoever approves, which the plugin cannot check.
- **L7.** Roadmap open question 7 is answered but never named.
- **L8.** Plain language: gloss "hash", "runner" and "contract check" before use; give the acceptance node a "no" branch.

## Complete and sound as written

Every row of Unit 4.1's table and all eight roadmap questions are answered or deferred with a reason. CS13 and CS14 match call 6, including Unit 1.7e's three limits. CS15 to CS18 match the plan's settings operations and the current-owner-only transfer. CS24 matches D5 and the existing refusals. CS10 and CS12 match P44. CS29 and CS30 match P43.

**Verdict: not ready.** B1, H1 and H2 change what Brandon is signing; with B1, H1 to H3 and the medium items applied, revision 2 should be ready for signature.
