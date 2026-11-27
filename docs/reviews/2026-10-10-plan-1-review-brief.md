You are reviewing an implementation plan before any of it is built. Read only; change nothing. Output a written review in markdown.

## Read
- The plan: docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md (all of it), in the current checkout.
- Its source of truth: docs/plans/2026-10-10-001-phase-2-3-decisions.md (Brandon's decisions D1 to D10 and material M6, M7, M8, M12, settled 2026-10-10).
- The roadmap units it carries, on the release-b branch: `git show release-b:docs/plans/2026-09-19-002-roadmap-after-phase-1.md` (Units 2.1, 2.4, 2.5, 4.1, the reviewed Unit 1.4b text at the end, and the review findings table).
- The build plan's format and its "For Brandon" table: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, plus calls 57 to 59 on the Release B finish branch: `git show claude/release-b-finish-1e1203:docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md`.
- The code the plan names, on the release-b branch (the layout it builds on is not on main): `git show release-b:<path>` for plugins/gtm-base/lib/gtmbase/ (constants.py, layout.py, trust_surface.py, write_hook.py, approve_local.py, base_reader.py, moment.py, compose_proposal.py, names.py, drafting.py, review.py), templates/company-base/, and tests/. Check that the files, functions, and behaviors it cites exist and work as the plan assumes.
- The Meta ads skill as it runs today, read only: ~/.claude/skills/meta-ads/SKILL.md and references/, ~/Gridwise/meta-ads/README.md and config.toml, ~/Gridwise/docs/plans/2026-10-05-001-feat-meta-ads-skill-plan.md, ~/.claude/scheduled-tasks/meta-ads-daily-check/SKILL.md.
- docs/ux-standard.md and tasks/lessons.md.

## What the product owner decided (not up for review)
Both businesses (Gridwise Analytics and the driver app) in one base. The first skill is the Meta ads creative-testing skill, and the company-skills brainstorm runs and is signed off before it is built on the base. Two plans, split by what has to be learned; this is Plan 1. One live session by Brandon per release. Whoever creates a skill or a document owns it; a change may be made and approved only by its owner, the base's owner, or an administrator; ownership must be provable. One new atlas figure for the runner. Sol (gpt-5.6-sol) builds some units alongside Opus; Astra stays the outside review. The base holds the business goals, the engine keeps its own thresholds in config.toml, and the standard relates each threshold to a goal without restating numbers. The mads engine stays an installed tool outside the base. Nothing under ~/Gridwise is edited.

## Review for
1. Feasibility against the real code on release-b: any unit that cites a file, function, or behavior that does not exist or works differently; any approach that cannot work as written; dependencies the order gets wrong (including the dependency on Release B and Unit 1.7e option D).
2. The riskiest units: 4.2 (narrowing the skills refusal, the ownership chain read from history, the base owner and administrator roles, how this composes with 1.7e); 3.1 (the runner, the unattended run, the figure-grounding check); 3.6 (moving a live nightly skill, the scheduled run, what the scheduled session can and cannot load). Can ownership as designed actually be proven, and what does it not prove?
3. Whether the brainstorm answers in Unit 4.1 are answerable and complete against the roadmap's eight questions plus D5, including whether scripts may live in a base. Name any question dodged or answered in a way the build cannot carry out.
4. Test scenarios that are vague, missing a failure path, or would pass without proving the behavior. Keep deterministic screening tests apart from model-behavior claims.
5. The proposed success test SC-M: is it a real, honest test of "the base produced work", can it fail, and does the plan overclaim the line to pipeline anywhere?
6. Scope: what should be cut or moved to Plan 2 so Plan 1 ships, and what is missing that Plan 1 cannot ship without.
7. Contradictions inside the plan, and between the plan and its inputs (the decisions brief wins where they differ).
8. The seven "For Brandon" calls: say which are genuinely open, which the decisions brief already settled, and whether any genuinely open question is missing.
9. Confidentiality: this repository is public. Flag anything in the plan that carries a client figure, identifier, or name that should not be public.

## Output
Findings ranked by severity (blocker, high, medium, low), each with the plan section or unit number, the evidence (file and line in the code when it applies), and the smallest change to the plan that fixes it. Then a short verdict: ready to build as written, ready with the listed changes, or not ready. Be adversarial and specific. Do not pad.
