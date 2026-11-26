Code citations below refer to `release-b:plugins/gtm-base/lib/gtmbase/` unless another branch or location is named. I made no edits. I verified source behavior with read-only inspection and an in-memory probe; I did not run the filesystem-writing test suite or the live scheduled task.

1. **Blocker: Units 4.1 and 4.2 prove consistency between identity claims, not authorization.**

   Plan lines 139, 296 and 333 compare ownership against addresses recorded in history. The seat address comes from mutable Git configuration (`base_reader.py:127`), and `accepted_by` reads unsigned author metadata (`base_reader.py:610`). Matching those fields does not authenticate the creator or establish that the person approved those bytes. Option D’s approval ticket is consumed and seat-local, not a durable attestation available to this history-only checker (`unit-1-7e-d:approval.py:554`).

   **Smallest fix:** specify a trusted ownership bootstrap and durable authorization evidence bound to each approved revision. Imported or unsupported history must require local approval before execution. Replace line 348’s “no seat-local state” guarantee unless a verifiable portable attestation is designed. State the boundary explicitly: this can protect supported operations on a trusted computer; it cannot establish a human’s identity, resist someone controlling that computer, or already make another seat safe.

2. **Blocker: Unit 4.2’s chain accepts unauthorized instruction changes.**

   The chain checks creation and subsequent changes to **owner or role lines**, not every content revision (lines 139, 296, 333). A non-owner can change only the body of `SKILL.md`, preserving the entire defined chain. Unit 3.1 then emits those instructions unfenced as approved (line 430). The hostile test at line 342 tests only an owner-line rewrite.

   **Smallest fix:** require authorization for every instruction and reference revision, and bind execution to the exact approved bytes. Add failure cases for a body-only commit, an uncommitted edit, a changed reference with unchanged `SKILL.md`, and a file changed between verification and reading.

3. **High: Unit 4.2 does not define the operations needed to install the first skill or administer roles.**

   Unit 3.6 creates complete skill, reference and example files through the prepared-change path (line 523). That path currently requires an existing target (`approve_local.py:582`), edits body headings, and explicitly forbids the map (`compose_proposal.py:345`). Widening permitted destinations does not provide file creation or safe map-role changes.

   There is also a creator/approver conflict: line 300 preserves the creator as owner while requiring an administrator’s approval, but the proposed chain equates the creation commit’s author with the initial owner.

   **Smallest fix:** specify absent-only file creation and narrowly defined ownership/administrator transitions. Record creator and approver separately, evaluate authority before the change, and define whether references/examples inherit the skill’s owner. Require complete previews, approval binding and rollback. Test failed installation leaving no partially runnable skill.

4. **High: Units 2.1 and 4.2 understate the change needed to support standards and the source map throughout the workflow.**

   These paths remain excluded by several independent checks:

   - `paths.py:121` accepts only `context/`.
   - `formats.py:629`, `:899` and `:1188` restrict affected paths, confirmations and edits.
   - `base_reader.py:456` drops non-context affected paths.
   - `base_reader.py:553` excludes them from correction-content hashes.

   An in-memory probe confirmed that `Edit.validate` accepts a business-scoped context path but rejects standard, source-map and skill paths.

   **Smallest fix:** make a shared, explicit document-path policy part of the unit, covering proposal creation, records, hashing, confirmation and moment-of-use. Add an end-to-end test that changes a standard, approves it, records the confirmation, clears the appropriate flag and reads it through the runner. Merely widening `context_files` cannot prove that lifecycle.

5. **High: Unit 4.2 broadens approval authority without consistently broadening confirmation authority.**

   The proposed `_owner_problems` change does not cover independent owner-only checks in `moment.py:560`, `confirm.py:1177` and `stale.py:902`. An administrator’s accepted correction can settle its associated change but still fail to count as a confirmation (`stale.py:955`). Transfers can also cause valid historical confirmations to be judged against today’s owners.

   **Smallest fix:** use the same authority service throughout approval, confirmation and stale computation, with historical authority evaluated at the relevant approval. Test administrator confirmation, ownership transfer and administrator revocation through the complete workflow.

6. **High: Units 3.1 and 3.6 infer scheduled-task behavior from the wrong execution environment.**

   Lines 106 and 299 infer that forced permission prompts are denied during unattended scheduled runs. Official documentation distinguishes these cases: Desktop scheduled tasks have their own permission mode and can **stall awaiting approval**; automatic denial is documented for non-interactive `-p` execution. Reading the task’s `SKILL.md` does not establish its actual working folder or permission configuration. [Scheduled-task permissions](https://code.claude.com/docs/en/desktop-scheduled-tasks#permissions-for-scheduled-tasks), [hook permission behavior](https://code.claude.com/docs/en/hooks#pretooluse-decision-control).

   **Smallest fix:** make the actual scheduled task’s mode, grants, working folder, plugin availability and installed client version a pre-cutover check. Explicitly prevent approval mutations in scheduled execution, and verify that attempted approval neither writes nor stalls. A caller-supplied `--unattended` flag and an attended manual replay are insufficient proof.

7. **High: Unit 3.6 lacks the dependency that makes SC-M possible.**

   The current scheduled prompt explicitly selects collect mode and forbids `decide` and `record` (`~/.claude/scheduled-tasks/meta-ads-daily-check/SKILL.md:6`). This is separate from the configuration switch controlling pauses (`references/daily-check.md:9`). Adding the runner command does not change that workflow or supply the additional read access and connector permissions.

   SC-M requires `decide`, but the Monday readout also requires recorded run events (`~/Gridwise/meta-ads/mads/readout.py:214`).

   **Smallest fix:** require completion of the Meta plan’s Unit 8a, or explicitly include its approved collect-to-dry-run transition in the migration. Specify `decide`, `record`, required access and failure handling without changing pausing settings. Line 565’s indefinite wait is not a sufficient release dependency.

8. **High: Unit 3.6’s “everything else moves as it is” instruction preserves broken links and conflicting rules.**

   The current skill hard-codes its old directory (`~/.claude/skills/meta-ads/SKILL.md:10`), explicitly loads the removed `rules.md` (`:28`) and repeats thresholds (`:61`). `references/launch-settings.md:42` and `:50` also duplicate engine settings. Its creation prohibition at line 3 conflicts with the current skill’s creation procedure and permissions.

   **Smallest fix:** replace copying unchanged with a migration checklist for every internal reference, path, duplicated threshold and instruction conflict. Resolve existing authorized behavior, retarget references to the standard/configuration, and replay both nightly and Monday workflows before replacing the old entrypoint.

9. **High: Unit 3.1 does not distinguish an optional context gap from a failed safety check.**

   The runner’s three branches depend on whether a document is flagged (line 430). But `moment.check` returns non-flagged results for unreadable records and invalid paths (`moment.py:603`, `:624`); quiet mode can also suppress flags (`:641`). These are not equivalent to verified current context.

   The plan also permits a missing standard to produce only a gap (line 446), although Unit 3.6 moves approval and write rules into that standard.

   **Smallest fix:** define explicit outcomes for current, flagged, missing optional context, missing required instructions, unreadable state and invalid ownership. Missing goals may permit the independent engine check; missing approval rules must not permit the full procedure. Add tests for each outcome, including quiet mode, no question issuance and failure before `finish`.

10. **High: Units 3.1, 2.4a and 3.6 overstate what numeric screening can prove.**

    “The figure appears in a supplied file” cannot establish that it belongs to the claimed metric, platform or period. A wrong figure borrowed from another metric passes; a valid calculated difference from a business goal can fail. Checking only currency and percentages also does not enforce the stated prohibition on every invented number.

    The proposed false-pause test at line 535 is unsupported by this contract: number membership cannot establish that a pause was planned or executed. Existing `review.screen` checks sensitive content, not numeric grounding (`review.py:177`); the in-memory probe accepted an unsupported synthetic amount and percentage.

    **Smallest fix:** describe value membership as a limited lexical screen. Validate operational claims against structured engine results, and bind reported figures to their named metric/source. Permit derived values only through an explicit calculation. Separate these deterministic checks from model replay. Tests saying fixture sources “produce” correct prose must not be satisfied merely by validating a prewritten correct answer.

11. **High: Unit 2.1 will report Analytics-only material as driver-app coverage.**

    The plan identifies the existing flat profile and positioning as Analytics material (line 53), leaves those files in place until Plan 2 (line 210), then treats flat files as company-wide (line 368). Changing the profile’s first paragraph does not make its underlying positioning applicable to the driver app.

    **Smallest fix:** assign explicit business scope to existing flat documents without moving them, or move them into the Analytics folder now. Test that Analytics-only positioning does not satisfy the driver-app inventory. D1 requires one base, not interchangeable context.

12. **High: Call 7’s proposed redaction still publishes confidential history.**

    The confidential decisions brief is already present in ancestor commit `dff9f24`. Replacing its contents in a later commit leaves the original figures available when the branch is pushed. Decisions lines 55 and 56 also include a client workbook filename and confidential planning material.

    The proposed replacement claiming the values were recorded in the base on the decision date is unsupported; lines 172 and 466 place that write in a future live session. Plan lines 44 and 495 additionally disclose identifiable internal campaign and engine-coverage details.

    **Smallest fix:** preserve the complete authority privately, sanitize the unpublished history and inspect every outgoing revision before publication. Use truthful private-source references and genericize internal operational examples. A scan of the final working tree or synthetic fixtures cannot establish confidentiality of Git history.

13. **High: SC-M can count the wrong artifact or the wrong implementation as success.**

    The existing weekly workflow consumes the engine-produced readout (`~/.claude/skills/meta-ads/SKILL.md:69`; `~/Gridwise/meta-ads/mads/readout.py:862`). The runner’s `finish` only specifies screening and a run record. The plan never names where the base-enriched draft is saved or how that version reaches the meeting.

    Line 77 also incorrectly says the existing readout compares against the business goal; it uses engine targets (`mads/readout.py:267`). Finally, line 563 allows a user-level fallback to count toward SC-M after ownership fails review, contradicting P42.

    **Smallest fix:** name the approved handoff and inspect the exact artifact used. Record run completion/failure and its output identity, not just successful `finish` calls. Keep the old skill as operational rollback, with Plan 1 incomplete. Describe current comparisons as engine-target comparisons and withhold business-goal comparisons where measurement definitions remain unresolved.

    SC-M is otherwise falsifiable and useful: missed nights, absent engine runs or no adopted readout can fail it. It proves operational integration and a used work product, not improved acquisition economics. Line 38’s path to subscribers is a business hypothesis, not an observed result.

14. **Medium: The dependency graph and parallel file ownership are inconsistent.**

    Unit 3.1 depends only on 2.1 but calls 4.2’s ownership checker. Conversely, skill admission requires 3.1’s contract tests before approval (line 305). Units 4.2 and 2.1 both modify `formats.py`; 2.5a modifies the reference file that 2.1 creates and validates business settings whose grammar is still deferred.

    **Smallest fix:** define the ownership interface first, make runner integration depend on it, and keep skill admission disabled until both are complete. Give shared settings/reference files one owner. Independent work may proceed before option D, but integrated skill approval cannot ship without it.

15. **Medium: The brainstorm leaves consequential questions unresolved while describing them as settled.**

    All eight roadmap headings are present. Distribution, examples, requested updates and scheduling have concrete proposals. However:

    - Question 3’s enforcement answer depends on the invalid ownership proof above.
    - Question 7 answers duplicate detection, but “only one skill exists” does not explain deferring stale-skill review.
    - D5 explicitly leaves scripts open for the brainstorm. “No scripts” is a reasonable recommendation, but lines 88 and 187 incorrectly label it resolved before signature.
    - Deferring all lessons from results at line 94 conflicts with the first-reporting-skill requirement in the roadmap, build-plan call 14 and `docs/ux-standard.md:123`.

    **Smallest fix:** keep the current script refusal pending the brainstorm’s explicit decision. State how the first skill’s instructions become stale and where findings go; defer duplicate detection until a second skill. Retain a minimal evidence-backed, owner-requested lesson proposal, or obtain an explicit decision to defer it.

16. **Medium: Several tests would pass without proving their stated requirement.**

    The standard’s digit ban accepts “twice the target” or “six days,” so it does not enforce the absence of duplicated threshold values (lines 144, 495). Static approved/wrong examples can continue passing after instructions change because no generated result is evaluated. The file-tool tests also contradict each other: line 345 accepts allowed files through a file tool, while line 346 refuses those direct writes.

    **Smallest fix:** label the digit rule as a lint, retain semantic review for number words and rule preservation, and require a reviewed replay when behavior changes. Separate file admission from file writing in the tests. Public fixture confidentiality should rely on synthetic provenance and private review, not an unspecified scan claiming to recognize every real name or figure.

The seven calls should be classified as follows:

| Call | Status |
|---|---|
| **1. Business layout** | Open. D1 settled both businesses in one base, not storage or scope inheritance. |
| **2. SC-M** | Open. D2 settled the first skill, not its acceptance test. |
| **3. Unattended flags** | Open. This changes the prior pause-before-work behavior. |
| **4. Old skill copy** | Open migration choice. Include a concrete rollback procedure. |
| **5. Sol’s write mechanism** | An implementation choice. D9 already settled that Sol builds alongside Opus. |
| **6. Release count** | Open. D3 settled one live session per release, not how many releases. |
| **7. Public disclosure** | Not an ordinary product choice. Standing confidentiality instructions require protection; the remaining work is safe sanitization. |

Missing explicit decisions are the learning deferral, if retained, and acceptance of the precise ownership guarantee the implementation can supply. The brainstorm signature must cover scripts and the additional administrator approval for skill creation. The scheduler’s collect-to-dry-run transition also needs a named owner and prerequisite.

Keep Plan 1 focused on the required ownership boundary, runner, driver-app documents and verified migration. Leave shared-copy authentication, duplicate-skill audits and autonomous improvement in Plan 2 or the backup plan. Cut the claim of general numeric-grounding proof; retain narrowly checkable engine facts and reviewed interpretation.

**Verdict: not ready.** The ownership proof, skill-installation contract and scheduled migration need design changes before building.