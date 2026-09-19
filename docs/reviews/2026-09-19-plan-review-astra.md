# Plan review: "A base that produces work" (Astra, through the Codex CLI)

Date: 2026-09-19. Reviewed: `docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md` revision 1, against the brief at `docs/reviews/2026-09-19-plan-review-brief.md`, in a read-only sandbox at high reasoning effort. It did not read the other reviewer's file. The text below is the reviewer's own, unchanged except that link targets were made relative to this repository. Revision 2 of the plan records what was done with each finding.

**Not ready to build Phase 1 as written.** The product decisions are implementable, but the plan leaves migration safety, local approval, and its release gate unresolved.

Read-only review completed against the full plan, supplied inputs, and relevant code. No files changed. Tests were inspected, not run.

## Blocker

### 1. Unit 1.4: Migration can hide entries and leave the base unable to recover

The plan combines “read new, otherwise old,” new-layout-only writes, refusal when both folders exist, and refusal on a dirty tree.

That produces two concrete failure paths:

- Migration refuses on an old-layout base; a subsequent writer creates `work/changes/`. The reader now ignores the old entries.
- Migration writes its correction record or moves files, then fails. Its own unfinished changes make the tree dirty, preventing retry.

The existing reader enumerates one directory, and existing writers reject dirty trees. [base_reader.py:195](../../plugins/gtm-base/lib/gtmbase/base_reader.py:195), [review.py:306](../../plugins/gtm-base/lib/gtmbase/review.py:306)

Tolerant reading also protects **new code reading old data**, not an old plugin reading migrated data. The current parser requires the old fields and kind. [formats.py:415](../../plugins/gtm-base/lib/gtmbase/formats.py:415)

**Smallest plan fix:** Specify recoverable migration with prevalidation, a recorded transaction, a defined commit point, and recovery that distinguishes migration changes from user edits. Read both directories by unchanged entry ID, reporting conflicting duplicates. Require coordinated upgrading of active seats before migration. Replace the reference to nonexistent `migrate.py` with an actual pattern.

**Required tests:** Interrupt after each mutation; retry; compare bodies, IDs, confirmations, and flags. Test both directories containing different entries, conflicting duplicate IDs, and an old plugin encountering migrated data.

### 2. Units 1.3 and 1.5: “Fix it first” cannot complete on a fresh base

The plan acknowledges that approval requires GitHub, but the earlier problem is that a fresh base cannot open the proposal at all. Proposal submission refuses source-reading sessions, requires first-backup review, and requires a remote. Backup remains deferred. [push_conditions.py:40](../../plugins/gtm-base/lib/gtmbase/push_conditions.py:40), [compose_proposal.py:562](../../plugins/gtm-base/lib/gtmbase/compose_proposal.py:562), [compose_proposal.py:660](../../plugins/gtm-base/lib/gtmbase/compose_proposal.py:660)

Unit 1.5’s setup → reconciliation “no” → proposal → approval → confirmation test therefore depends on functionality outside this release. The same blockage affects resolving saved unanswered markers.

**Smallest plan fix:** Add a narrowly scoped local proposal-review-and-apply path to Phase 1. Preserve screening, owner approval, evidence, and confirmation semantics. Test it on a newly created base without a remote. Do not weaken the outgoing-data gate to make this work.

### 3. Unit 1.9: The fidelity gate has two ways to pass without proving fidelity

The requirement demands three cases, including a company without finished segment pages. But the execution note permits deciding from whichever cases ran, and question 4 offers dropping that case. The dependency statement also allows shipping once summarize-first is *built*, without requiring a successful replay afterward. [Plan:549](../../docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md:549), [Plan:557](../../docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md:557)

Both weaken Codex G. The missing case is precisely the case adoption cannot rescue.

**Smallest plan fix:** Before implementation, name the scorer and freeze each corpus plus its expected segments, deals, figures, units, versions, and unresolved choices. Score the uncorrected output against the original corpus, including evidence beyond the input cutoff. Missing cases mean **incomplete**, not pass. Any remediation must pass the same three replays afterward.

## High

### 4. Unit 1.3: The moment-of-use flow lacks a safe action contract

Three assumptions do not hold:

- The deterministic consuming runner arrives in **3.1**, not Phase 1. Testing a fixture that voluntarily calls `moment.check` does not prove actual entry points check before use.
- The existing “drafted fix” is an `Update needed: …` placeholder requiring assistant rewriting. A lookup cannot guarantee a usable fix already exists. [stale_check.py:327](../../plugins/gtm-base/lib/gtmbase/stale_check.py:327)
- The integration test expects “yes” to create a confirmation, but permission to use stale content does not confirm its accuracy. Existing confirmation code records currency without changing the document. [confirm.py:472](../../plugins/gtm-base/lib/gtmbase/confirm.py:472)

**Smallest plan fix:** Define the full sequence: detect, prepare an actual candidate, pause, obtain the choice, then resume. “Use as is” must leave the flag intact. “Fix first” must wait for approved application. “Already reflects this change” is a separate confirmation action.

Move the checked-read boundary needed by actual Phase 1 consumers into 1.3. Test that no work product is generated before the choice. Keep outside-skill behavior explicitly instruction-dependent, with a live compliance check rather than claiming deterministic coverage.

Also remove the marker-only interruption in 1.3’s scenarios. It contradicts the settled rule that only an overtaking recorded change triggers unsolicited intervention.

### 5. Unit 1.7: Rejecting duplicate headings does not establish editing compatibility

Codex D explicitly included fenced examples and unsupported heading forms. The plan reduces this to duplicate headings at one level.

The real editor treats heading-shaped lines inside code fences as document headings. It also cannot extract every otherwise valid Markdown structure. An adopted document can pass the planned check and later receive an incorrect section replacement. [compose_proposal.py:213](../../plugins/gtm-base/lib/gtmbase/compose_proposal.py:213), [compose_proposal.py:969](../../plugins/gtm-base/lib/gtmbase/compose_proposal.py:969)

**Smallest plan fix:** Initially restrict adoption to the exact heading grammar the editor supports. Test fenced pseudo-headings, setext headings, unsupported body structure, and an adoption-to-proposal round trip. Duplicate-heading rejection alone is insufficient.

### 6. Unit 1.7: Partial-import recovery covers completed files, not interrupted writes

The existing writer writes the document, stages it, appends confirmation, then commits. Failure between these operations leaves an existing destination and possibly a dirty tree. Retrying then hits absent-only or clean-tree refusal. [review.py:348](../../plugins/gtm-base/lib/gtmbase/review.py:348)

“Interrupted after six” can pass while testing only six successful commits. Resuming from file presence can also mistake an unconfirmed partial write for completed adoption.

**Smallest plan fix:** Define per-file recovery bound to approved bytes and the document-plus-confirmation commit. Inject failure after writing, staging, confirmation, and commit. Preserve protection against overwriting unrelated files.

### 7. Unit 1.7: The later-read safety condition is promised but not assigned to Phase 1

The risk table promises adopted content remains data on every subsequent read. The concrete shared reader with fencing appears only in **3.1**. Existing skills direct the assistant to read documents during proposal improvement. [stale-check/SKILL.md:62](../../plugins/gtm-base/skills/stale-check/SKILL.md:62)

Owner-reviewed prose can contain ordinary-language instructions that pass contact/key screens. Approval establishes which document was adopted; it does not make its instructions authoritative.

**Smallest plan fix:** Name and update all Phase 1 model-facing consumption paths in 1.7. Test their rendered inputs with hostile adopted prose. Preserve the distinction between verifying a data fence and proving that a model never follows an instruction.

### 8. Units 2.2–2.5 and 3.2–3.4: Templates break optional adoption and existing-base upgrades

New optional context files are placed directly in the company-base template. Creation copies that entire tree, so a fresh base already contains those files before inventory approval. Absent-only adoption then refuses their destinations. Existing bases receive none of the new files, including the rubrics Phase 3 requires. [create_base.py:185](../../plugins/gtm-base/lib/gtmbase/create_base.py:185), [review.py:443](../../plugins/gtm-base/lib/gtmbase/review.py:443)

**Smallest plan fix:** Keep optional starter content outside the automatically copied tree. Materialize and confirm it only through an owner-approved request. Add explicit rubric provisioning for existing bases, preserving customized versions. Test both actual fresh creation and an existing-base upgrade.

## Medium

### 9. Unit 1.6: Version-body comparison is assigned to the pre-consent survey

The survey is deliberately limited to names and capped first headings. The plan assigns it conflict reporting while requiring detection of differing bodies. Implementing that literally broadens what is read before consent. [sources.py:659](../../plugins/gtm-base/lib/gtmbase/sources.py:659)

**Smallest plan fix:** Group names and rank versions during survey; compare bodies only after consent. Test that survey never reads the bodies.

### 10. Unit 1.8: The lint contradicts required wording and misses runtime output

P4’s exact closing request contains **zero question marks**. The proposed “exactly one question mark” rule rejects it. Paragraph limits also conflict with showing adopted bodies whole.

The rewrite scope omits runtime renderers and their owning tests, although user-facing sentences exist in Python. Existing tests pin both wording and safety sentences. [stale_check.py:134](../../plugins/gtm-base/lib/gtmbase/stale_check.py:134), [test_prompt_guards_join.py:32](../../tests/test_prompt_guards_join.py:32)

**Smallest plan fix:** Check one delimited request block, accepting imperative requests. Apply concise-output rules to the interaction wrapper, with the complete approval artifact separately reviewable. Include runtime renderers and existing assertions in the unit. Use mechanical checks for structure and live review for purpose, tie-back, and readability.

### 11. Unit 2.6: Two local version observations cannot establish whether an update exists

Comparing the installed manifest with a previously recorded installed version cannot discover a newer release. The unit also differs from the decision table’s marketplace-pin comparison.

**Smallest plan fix:** Either always provide the verified refresh instruction without claiming currency, or specify an on-request authoritative release lookup and an explicit “unknown” result when unavailable.

### 12. Unit 3.1: Approved examples do not test approved judgment

The harness checks which files were read, fencing, screening, and missing-file behavior. An irrelevant but contact-free paragraph could satisfy those checks. The approved output has no substantive role in acceptance.

**Smallest plan fix:** Add example-specific expectations such as required claims, segment identity, contradiction detection, and proposal/no-proposal outcome. Include deliberately wrong outputs that must fail. Exact prose snapshots are unnecessary.

## Codex condition coverage

“Covered” means assigned to a concrete unit, not proven implemented.

| Condition | Named units | Assessment |
|---|---|---|
| **A: amended setup contract, honest baseline, independent original acceptance test** | **1.1 Contract amendments; 1.2 Completion and closing; 1.9 Fidelity replay** | Substantially covered. Unit 1.1 omits the parent strategy structure required by the verdict. It also omits origin R22/R23 and first-plan Unit 3, which r2.5 explicitly amends. Add them. |
| **B: whole-entry preview, corrected fields, no self-confirmation, per-document reconciliation** | **1.5 Habit hooks** | Specified correctly. Applying the resulting correction is blocked by finding 2. |
| **C: strategic local edits, typo path, preserved evidence, reminder dismissal and accounting** | **1.3 Quiet by default; 1.5 Habit hooks** | Covered in intent. Moving the reminder into explicit review is authorized by r2.5. Name the actual dismissal window instead of leaving “one window” unresolved. |
| **D: explicit variants, authority manifest, sanitization, safe destinations, owner/byte-bound approval, currency, resumption** | **1.2; 1.7 Umbrella profile, segments, guarded adoption, scope, and unanswered-marker state** | Most clauses carried. Heading compatibility, intra-file recovery, and Phase 1 later-read boundaries are weakened. Malformed-frontmatter coverage is omitted. First-backup review is deferred appropriately, but must be an explicit prerequisite for backup shipping. |
| **E: scope in strategy context, enforced during selection/adoption/drafting** | **1.7** | Assigned. Add a mixed-product document case: filtering filenames cannot make an unchanged mixed-scope body valid. Specify refusal or separately approved extraction. |
| **F: explicit consent, version policy, manual inclusion, preview fidelity, unresolved lifecycle** | **1.6 Selection fixes; 1.7** | Assigned. Body comparison must follow consent. Later marker resolution depends on the missing local approval path. |
| **G: representative three-case fidelity gate** | **1.9 Fidelity replay** | Materially weakened by omitted-case and built-fallback escape clauses. |

## Tests that would otherwise give false confidence

| Unit | Problem | Required correction |
|---|---|---|
| **1.2** | A closed change *older than the file* is already excluded by the existing date comparison, even without checking closed status. [stale.py:885](../../plugins/gtm-base/lib/gtmbase/stale.py:885) | Use a closed change newer than the file’s sources, with an otherwise identical open-change control. |
| **1.2** | Baseline coverage only proves confirmations dated today. | Add resumed setup with earlier confirmation dates and identical results on another seat. |
| **1.3** | A runner failing on `fetch` does not prove no network calls. A fixture calling `moment.check` does not prove real integration. | Reject all remote-capable dependencies and exercise actual entry points. |
| **1.7** | Hostile fixtures omit malformed metadata and adoption-specific dirty-tree/default-branch failures. | Add refusals asserting no destination, confirmation, or unintended tracked write. |
| **1.7** | Marker detection alone does not prove ineffective confirmation. | Exercise drafted, ordinary, and post-proposal confirmation paths while markers remain. |
| **3.2–3.4** | Fence assertions cannot prove instruction noncompliance; current screens do not detect arbitrary prospect names or unsupported claims. [redaction_patterns.py:124](../../plugins/gtm-base/lib/gtmbase/redaction_patterns.py:124) | Separate deterministic screening tests from model-behavior and grounding evaluations. |

## Contradictions and open questions

There is **no enumerated five-contradiction list** in the supplied plan or inputs. These are five verifiable conflicts, not an attributed reconstruction of the planner’s list.

| Conflict | Disposition |
|---|---|
| New-layout-only reading/writing versus preserving old-layout entries | **Resolve before build**, finding 1. |
| Local-only Phase 1 versus completing “fix first” through proposals | **Resolve before build**, finding 2. |
| Three-case gate versus deciding from incomplete cases or merely building the fallback | **Resolve before build**, finding 3. |
| Only change-driven interruptions versus marker-only moment prompts | **Resolve before building 1.3**, remove the extra interruption. |
| Whole-document approval versus short-list/table-only output | **Resolve before building adoption/display**, separate the complete artifact from its concise interaction wrapper. |

| Planner question | Blocker or deferrable? |
|---|---|
| **1. What “Sol” means** | Assignment detail, not a technical blocker. Resolve when briefing agents. |
| **2. Design-file contents/location** | Defer to Phase 2 planning. |
| **3. Inventory kinds** | Defer to Phase 2 planning. |
| **4. Replay scorer and material** | **Resolve before behavior implementation.** Do not let implementation determine its own evidence standard. |
| **5. Additional atlas figures** | Defer Phase 2/3 figures. Phase 1 already names its figures. |
| **6. Live-check batching and release count** | Fix release semantics now: one gated Phase 1 release. Live checks can be scheduled or batched later. Intermediate unit merges must not ship changed skill instructions early. |
| **7. Whether the company-skills brainstorm may reconsider trust refusals** | Defer to that brainstorm. Current refusal rules remain unchanged. |

## Scope and verdict

Make **Phase 1 its own implementation plan**. Move Phase 2 and Phase 3 into separate plans, and keep Phase 4 as a brainstorm brief. The twenty-unit document works as a roadmap, but its later unresolved contracts should not be treated as implementation-ready.

Within Phase 1, split Unit 1.7 into separately testable scope/inventory, document variants, adoption, and recovery work. Move the minimal checked-read boundary and local approved-correction path forward. Keep migration recovery, adoption safeguards, and the full fidelity gate. Cut those and Phase 1 no longer satisfies its agreed contract.

**Verdict: not ready.** Resolve the migration transaction, local approval path, moment-of-use action semantics, and non-waivable fidelity gate before implementation begins.