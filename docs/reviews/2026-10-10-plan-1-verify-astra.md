| Finding | Status | [Revision 2 evidence](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md) |
|---|---|---|
| 1. Authorization proof | Partly | Local trusted approvals replace unsigned history, but call 6’s human-approval guarantee omits option D’s exceptions (lines 255, 371). |
| 2. Unauthorized instruction changes | Partly | Hashing and returning one read addresses the four requested edits, but approval membership remains per file rather than per complete revision (469, 492). |
| 3. Creation and role operations | Closed | Absent-only creation, separate creator and approver, inherited reference ownership, role operations and rollback are specified (170, 332, 371, 524 to 526). |
| 4. Shared document-path policy | Closed | `docpaths` covers proposals, records, hashes, confirmation and moment-of-use, with a standard lifecycle test (367 to 388). |
| 5. Historical authority | Closed | One rule evaluates authority when approval or confirmation occurred; tests cover administrator confirmation, transfer and revocation (371, 381 to 383). |
| 6. Scheduled execution | Partly | The live environment check is present, but exclusion from the task’s tool list is still treated as enforced prohibition (618). |
| 7. SC-M prerequisite | Closed | The window explicitly requires Meta Unit 8a and nightly completion of both `decide` and `record` (106, 596). |
| 8. Migration defects | Closed | The checklist covers paths, removed references, repeated thresholds, conflicting instructions and both workflow replays (607 to 616). |
| 9. Runner outcomes | Partly | Named outcomes distinguish gaps from required-document failures, but overlapping states lack precedence and invalid optional paths lack an outcome (473 to 479). |
| 10. Numeric screening | Partly | The numeric check is correctly called a lint, but operational quotations have no specified verification against engine output (175, 481, 613). |
| 11. Business scope | Partly | Explicit scope prevents Analytics coverage counting for the driver app, but the promised settings migration lacks a supported writer (235, 407, 414). |
| 12. Confidential history | Closed | Rebuilding history, preserving the complete authority privately and inspecting every outgoing commit are mandatory before any push (221). |
| 13. SC-M artifact and evidence | Partly | The adopted artifact and rollback exclusion are explicit, but unfinished runs are incorrectly recorded as stopped at `start` (108, 110, 481, 614). |
| 14. Dependencies and file ownership | Partly | Sequential ownership and runner/install ordering are repaired; 4.2a’s lifecycle test still needs 2.1’s later reader expansion (201 to 205, 385, 404). |
| 15. Brainstorm completeness | Partly | Scripts await signature, stale-skill review is specified and lessons have a call, but the recommended lesson operation targets a refused path (246, 345, 387, 615). |
| 16. Test claims | Closed | Static examples are separated from replay, digits are only a lint, admission and writing are distinct, and fixtures require synthetic provenance (343, 522 to 523, 574, 634). |
| Calls classification | Closed | Sol’s mechanism becomes an implementation default, confidentiality becomes mandatory, and ownership and lessons receive explicit calls; the other product choices remain open (197, 221, 250 to 256). |

1. **High: Approval of individual files does not establish approval of the assembled skill.**  
   **Unit 3.1, lines 99, 169 and 469.** The stated check accepts each file against any trusted approval. An approved version-two `SKILL.md` combined with an approved version-one reference satisfies that rule, although nobody approved the combination. Deleting a reference can also leave every remaining file approved. **Smallest fix:** approve and trust one manifest containing the base, skill, complete path set and every file hash. Match the returned snapshot against that manifest; test mixed versions and deletions.

2. **High: Call 6 overstates the inherited approval guarantee.**  
   **Call 6 and Unit 4.1, lines 255 and 333.** Both promise that a person answered. Call 57 explicitly retains permission-configuration risks, and `unit-1-7e-d:plugins/gtm-base/lib/gtmbase/approval.py:63` documents that settings or another plugin can answer on the person’s behalf, and unrestricted command access can manufacture tickets. **Smallest fix:** qualify call 6 by the verified client and permission configuration, prohibit automated approval responders within that guarantee, and carry forward option D’s actual limitations. Keep the chosen mechanism.

3. **High: The scheduled tool list does not prove approval commands are unreachable.**  
   **Unit 3.6, lines 179, 618 and 658.** The design adds allowed commands but specifies no enforced denial. Scheduled tasks inherit user allow rules, and ungranted calls can stall; allow rules skip prompts, while deny rules prohibit calls. [Scheduled-task permissions](https://code.claude.com/docs/en/desktop-scheduled-tasks#permissions-for-scheduled-tasks), [permission enforcement](https://code.claude.com/docs/en/permissions#manage-permissions). **Smallest fix:** specify an enforced boundary for scheduled execution covering approval, confirmation, installation and trusted-skill acceptance, including inherited grants and alternative invocation paths. Require verification before cutover; one attempted command is insufficient.

4. **High: The runner’s outcome table is incomplete for combined failures.**  
   **Unit 3.1, lines 469 to 479.** A missing required standard can coexist with an optional gap or a silenced seat, yet those rows respectively return refusal or instructions. An invalid optional declaration matches no row. **Smallest fix:** establish precedence explicitly. Validate trust, declaration paths and required-document readability before flags, silence or optional gaps; invalid declarations always refuse. Test combined conditions, including a missing standard on a silenced seat.

5. **Medium: The required integration tests precede their reader dependency.**  
   **Execution Posture and Units 4.2a/2.5a, lines 201 to 210, 385 and 450.** Those units must pass before the standard/source-map enumeration assigned to 2.1 at line 404. On `release-b`, `base_reader.py:154` walks only `context/`, and `stale.py:899` and `:933` discard confirmations for unenumerated paths. **Smallest fix:** move minimal document enumeration into 4.2a, or explicitly defer these integration tests until 2.1 merges. The sequential file handoffs otherwise work.

6. **Medium: Business-scope migration has no permitted settings operation.**  
   **Unit 2.1 and Execution Posture, lines 235 and 371.** Existing documents receive business scope through a prepared settings change, but prepared changes exclude settings (`release-b:compose_proposal.py:348`), and 4.2a adds only creation and the two role operations. **Smallest fix:** add a narrow, authority-checked operation for document business scope and the map’s business list, with complete preview and approval binding.

7. **Medium: The recommended lesson cannot be created through the named operation.**  
   **Units 4.2a and 3.6, lines 387 and 615.** `docpaths` must refuse everything under `learning/`, while the migration requires creating a lesson there through 4.2a. **Smallest fix:** define a narrow approved creation operation for `learning/lessons/`, retaining refusals for the other learning destinations.

8. **Medium: Operational quotation is still only an instruction.**  
   **Units 3.1 and 3.6, lines 481, 494 and 613.** The specified checks inspect sensitive content and numeric membership. A fabricated pause claim containing no new number still passes, despite the requirement to quote engine facts. **Smallest fix:** preserve operational facts as an identified, verbatim engine block and verify equality at `finish`; leave the model’s goal interpretation to the stated replay review.

9. **Medium: An unfinished run is assigned an unobserved stopping point.**  
   **Unit 3.1 and SC-M, lines 108 and 481.** Missing `finish` does not mean execution stopped at `start`; engine actions may already have completed. **Smallest fix:** record `started`, then completion with the output identity. An unmatched start means incomplete with an unknown stopping point until reconciled against engine records.

**Verdict: not ready.**