You are reviewing a requirements document before anything is built from it. Read only; change nothing. Output a written review in markdown.

## Read
- The document: docs/brainstorms/2026-10-10-company-skills-requirements.md (all of it).
- What it must satisfy: Unit 4.1 in docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md (the table of questions and its verification line), and the requirements and units it feeds there (P39, P43, P44, Units 4.2a, 4.2b, 3.1).
- Decision D5 in docs/plans/2026-10-10-001-phase-2-3-decisions.md, and the roadmap's eight questions for Unit 4.1 (`git show release-b:docs/plans/2026-09-19-002-roadmap-after-phase-1.md`, section Unit 4.1).
- Unit 1.7e option D as built: `git show unit-1-7e-d:plugins/gtm-base/lib/gtmbase/approval.py`.
- The code it constrains, on release-b: `git show release-b:<path>` for plugins/gtm-base/lib/gtmbase/layout.py, trust_surface.py, write_hook.py, approve_local.py, base_reader.py, formats.py, and templates/company-base/.
- The Meta skill it will first admit, read only: ~/.claude/skills/meta-ads/ (its file shapes, sizes and settings keys).
- Your earlier reviews of the plan: docs/reviews/2026-10-10-plan-1-*-astra.md.

## What the product owner decided (not up for review)
Whoever creates a skill or a document owns it; a change may be made and approved only by its owner, the base's owner, or an administrator; ownership must be provable. Plan 1's seven calls were accepted as recommended on 2026-10-10, including call 6 (the ownership guarantee as stated) and call 7 (a minimal lesson on request). The Meta engine stays an installed tool outside the base.

## Review for
1. Completeness against Unit 4.1: every question in its table and the roadmap's eight questions answered or explicitly deferred with a reason, including script files, the extra yes for creating a skill, how ownership is recorded and proven, how it passes when someone leaves, and how it fits Unit 1.7e.
2. Buildability: could the builder of Units 4.2a and 4.2b work from this without a second round of questions? Name every requirement that is ambiguous, contradicts the plan, or cannot be built against the real code.
3. Soundness: any requirement that would let an unapproved version of a skill run, let someone outside the authority set approve or confirm, let an unattended run write or wait, or overstate the guarantee.
4. Contradictions inside the document and with the plan (the plan's revision 2.4 wins unless the document says it is changing it and why).
5. Plain language: it is written for Brandon to sign. Flag jargon or sentences he could not act on.

## Output
Findings ranked by severity (blocker, high, medium, low), each with the requirement number or section, the evidence, and the smallest change that fixes it. Then a one-line verdict: ready for Brandon's signature as written, ready with the listed changes, or not ready. Be adversarial and specific. Do not pad.
