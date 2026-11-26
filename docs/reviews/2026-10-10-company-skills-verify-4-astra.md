| Fix | Result and evidence |
|---|---|
| Unit 4.2a test | **Closed.** [Lines 407–408](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:407) scope “writes nothing” to modes that ask and specify both unasked approval and marked-conversation denial in both other modes. |
| Named human-consent claims | **Closed at the cited locations.** CS8, CS11 and Plan 1 lines 113, 162, 356, 396 and 569 now explicitly include call 60’s exception. |

**Remaining finding: unconditional question wording survives elsewhere.**

| Location | Wording and smallest fix |
|---|---|
| [Requirements flow, lines 30 and 38](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/brainstorms/2026-10-10-company-skills-requirements.md:30) | Approval goes through a question and acceptance is “asked once.” Add a diagram note that those questions are skipped in the two modes that ask nobody, subject to CS30’s unattended refusal. |
| [Plan 1, line 191](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:191) | The assistant “still asks before acting.” Replace this with “acts under the configured permission mode.” |
| [Plan 1, line 554](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:554) | Acceptance ends with “then one ask.” Add the same call 60 qualification already present at line 569. |
| [Plan 1, line 692](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:692) | “The AI proposes and an owner approves” remains an unconditional invariant. State instead that approvals require an authorized address, with human confirmation subject to call 60. |

No remaining reliance on the old permission-mode refusal found.

**Verdict: ready with the listed changes.**