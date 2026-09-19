You are reviewing an implementation plan before any of it is built. Read only; change nothing. Output a written review in markdown.

## Read
- The plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md (all of it).
- Its inputs: join plan Amendment r2.4 at the end of docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md; first plan Amendment r2.5 at the end of docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md; docs/reviews/2026-09-19-codex-setup-shape-verdict.md; docs/ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md.
- The code the plan names, enough to check that files, functions, and patterns it cites exist and behave as the plan assumes: plugins/gtm-base/lib/gtmbase/, plugins/gtm-base/skills/, tests/.

## What the product owner decided (not up for review)
"Context change" replaces "decision". The base is quiet by default and speaks up only when a document in use has been overtaken by a recorded context change. The AI proposes and a person approves; nothing is applied on its own. Setup drafts two documents. Finished documents are adopted rather than summarized. Skills that use the base come before backup and invites. The UX standard: each step says what it is for, shows output readable in seconds, ties back, asks one thing.

## Review for
1. Feasibility against the real code: any unit that cites a file, function, or behavior that does not exist or works differently; any unit whose approach cannot work as written; hidden dependencies between units that the dependency order gets wrong.
2. The riskiest units. In particular: the rename and migration of the one existing base (data loss, a base half-migrated, a second seat on the old layout); the moment-of-use flag (how "about to use a document" is actually detected, and whether it can be relied on when it depends on an assistant following an instruction); guarded adoption (what reaches cross-seat context unreviewed); the plain-language rewrite (sentences that tests pin); the fidelity replay as a gate (who scores it, and whether it can fail honestly).
3. Whether each Codex condition from the setup-shape verdict is actually met by a unit, by name. List any that are dropped or weakened.
4. Test scenarios that are vague, missing a failure path, or would pass without proving the behavior.
5. Scope: what should be cut or moved later so Phase 1 ships, and what is missing that Phase 1 cannot ship without. Is twenty units across four phases in one plan the right shape, or should Phases 2 to 4 be separate plans?
6. Contradictions inside the plan, and between the plan and its inputs.
7. The five contradictions and seven open questions the planner surfaced: say which you think are real blockers before build and which can be deferred.

## Output
Findings ranked by severity (blocker, high, medium, low), each with the plan section or unit number, the evidence (file and line in the code when it applies), and the smallest change to the plan that fixes it. Then a short verdict: ready to build Phase 1 as written, ready with the listed changes, or not ready. Be adversarial and specific. Do not pad.
