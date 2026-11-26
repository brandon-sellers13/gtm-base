| Finding | Status | Evidence in [revision 2](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/brainstorms/2026-10-10-company-skills-requirements.md) |
|---|---|---|
| Astra 1, acceptance bypasses authority | Closed | CS11 requires an authorized approval matching the entire manifest; acceptance cannot approve previously unapproved bytes. |
| Astra 2, ordinary-document write boundary | Partly | CS3 requires authority-checked saves and excludes unsaved edits from skill inputs; the check-result gap remains in N1 below. |
| Astra 3, unattended marking starts too narrowly | Partly | CS30 marks any unattended invocation and retains the mark; the runner’s conflicting classification remains in N2. |
| Astra 4, blanket `.claude/` ban | Partly | CS23 preserves validated root `.claude/settings.json`; Plan 1 still states the blanket ban, as detailed in N3. |
| Astra 5, business assignment omitted | Closed | CS21 admits validated `business`; CS17 restores its authority-approved operation and the five operations’ preview, binding and recording requirements. |
| Astra 6, unattended outcomes and write scope | Closed | CS31 incorporates ordered flag outcomes; CS30 expressly preserves operational records and authorized engine work. |
| Astra 7, file rules reject required files | Partly | CS19 exempts `SKILL.md`, admits the empty placeholder and fixes example depth; Plan 1’s hidden-file wording remains inconsistent under N3. |
| Astra 8, unclear terminology | Closed | The glossary names both maps and defines fingerprints, computer, runner and contract check; the deferred settings wording is simplified. |
| Fable B1, unapproved acceptance | Closed | CS11 rejects absent or mismatched approvals and requires an authority-approved change before trust can be established. |
| Fable H1, overstated document guarantee | Closed | CS14 explicitly limits the guarantee to GTM Base’s saves, approvals and records, and acknowledges externally saved document changes. |
| Fable H2, missing document settings | Closed | CS21 admits `kind`, `sources`, `status`, `business` and `last_confirmed`. |
| Fable H3, unsupported nested `reads` | Closed | CS21 replaces it with flat `reads_required` and `reads_optional` lists. |
| Fable M1, uppercase `SKILL.md` | Closed | CS19 explicitly exempts the fixed filename from lowercase naming. |
| Fable M2, administrators location | Closed | CS2 places `administrators:` beside `owner:` in the map’s top settings block. |
| Fable M3, confirmation identity and role | Closed | CS9 records both in the confirmation line and defines treatment of older lines. |
| Fable M4, two-approval mechanics | Closed | CS6 requires two approvals of the same manifest, permits either order and holds the creation outside `skills/` until both arrive. |
| Fable M5, unattended marking | Partly | CS30 fixes marking time and the scheduled prompt’s first command; N2 remains for subsequent starts. |
| Fable M6, installation screens | Closed | CS22 applies prepared-change contact and key screens before showing skill files, with the owner-address exception. |
| Fable M7, four admission paths | Closed | CS19 names shared-copy updates, opening a base, file-writing checks and checks before sending. |
| Fable M8, downstream briefs | Closed | Next Steps explicitly includes Units 3.1 and 3.6. |
| Fable M9, creating standards | Closed | CS5 permits a joined person to create and own a standard. |

1. **N1. High, CS3 and CS31: saved content can receive the working copy’s flag result.**  
   [Unit 3.1, line 500](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:500) now requires saved document contents, while line 526 still requires `moment.check`. On `release-b`, that check reads working-copy metadata through `base_reader` (`moment.py:611`, `base_reader.py:162`). An unsaved `status: skipped` edit suppresses the document’s flag (`stale.py:214`, `:1078`), although the runner would return its saved contents. The new requirement does not assign the corresponding reader/check change. **Smallest fix:** require checks and returned documents to use the same saved revision, assign the reader and moment-check changes to a named unit, and test that an unsaved status change cannot clear the saved document’s flag.

2. **N2. High, CS30: the persistent unattended mark conflicts with the runner’s mode rule.**  
   CS30 retains the mark after a later attended start, but [Unit 3.1, line 519](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:519) classifies a run without the command-line word as attended; line 530 also says its conversation is unmarked. Its flagged outcome then waits for a choice. On `release-b`, `moment.check` creates that confirmation question when supplied a session (`moment.py:679`). **Smallest fix:** make an existing conversation mark override omission of the unattended word for runner outcomes. Test an unattended start followed by a start without that word against a flagged document, requiring no question and no wait.

3. **N3. Medium, CS19 and CS23: Plan 1 still omits the preserved file exceptions.**  
   [Unit 4.1’s path table, line 359](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:359) still refuses hidden files and `.claude/` without exceptions; the scope boundary at line 142 repeats the latter. Revision 2 explicitly permits empty `skills/.gitkeep` and validated root `.claude/settings.json`, matching `release-b`. **Smallest fix:** repeat those exact exceptions in Plan 1’s active boundary and path table.

**Verdict: ready with the listed changes.**