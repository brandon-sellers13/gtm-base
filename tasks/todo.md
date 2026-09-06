# GTM Base build, Phase A1 (started 2026-09-05)

Plans: docs/plans/2026-09-04-001 (first feature, r2 + amendments) and docs/plans/2026-09-05-001 (join, r2; its
"Changes to the first feature's units" apply while building). One Opus subagent per unit; orchestrator runs
tests and the plain-language lint after each unit and merges only when every test scenario is covered.

- [x] Unit 1: scaffold, manifests, template, join guide, test runner, fake gh
- [x] Unit 2: shared library (formats, paths, state, ids, validate, shim, machine, gitcmd, fsutil, errors)
- [x] Unit 9a: stale library
- [x] Unit 4: pre-push gate
- [x] Unit 3: session-start hook
- [x] Unit 7: propose-change
- [x] Unit 9b: stale-check skill and report
- [x] Unit 10: confirm
- [ ] SC1 and SC5 end to end on a real test base (gate before Phase A2)
- [ ] Ask Brandon to confirm GitHub remote and visibility before the first commit

## Notes
- Local git repository initialized 2026-09-05 (branch main, no remote, no commits yet).
- System python is 3.9.6; all code must run on 3.9 (no match statements, no X | Y unions at runtime).
- Unit 2 landed 2026-09-05: 197 new tests, 210 in the suite, all green. Decisions taken where the
  plans were open are listed in the unit's report and reflected in the module docstrings.

## Review
(filled at the end)

## GTM Base identity sprint

- [x] Approve continuity palette treatment 3
- [x] Create 12 monochrome structural mark mechanisms
- [x] Render and inspect display-size and favicon tests
- [x] Advance A1, A2, B4, and C4 from the monochrome sheet
- [x] Apply the approved color behavior and DM Sans wordmark consistently
- [x] Render and inspect color, monochrome, reverse, and 48, 24, and 16 pixel tests
- [x] Select B4 as the preferred direction
- [x] Test B4 across website, product, plugin, editorial, and small-format applications
- [x] Lock the B4 refinement brief and preserve the approved palette behavior
- [x] Generate three significantly refined B4 constructions with Higgsfield Recraft
- [x] Inspect exact SVG outputs for craft, distinctiveness, and small-size viability
- [ ] Review the three refinements with Brandon (moot: B4 retired 2026-09-05, see below)
- [ ] Select one construction before final production (superseded by the items below)
- [x] Retire B4. The mark direction moved to the diagonal overlap join after four rounds of
      sketches, 2026-09-05. Boards live in the Claude artifacts from that session.
- [x] Approve wordmark typography: DM Sans 700, tight at display and open at nav, chosen over
      JetBrains Mono from a side by side, 2026-09-05. Recorded in brandkit/brand-lock.json.
- [ ] Draw the diagonal mark to production: optical corrections, corner radii, overlap proportion
- [x] Decide the one-ink treatment: three tints of the system ink ramp, decided 2026-09-05
      (the cut-out was considered and not chosen). Recorded in brandkit/brand-lock.json.
- [ ] Define the fallback for contexts that allow only one value (embossing, single colour print)
- [ ] Cut the final SVG, favicon, and app icon from the approved drawing

### Identity sprint review

- The sheet compares four letter-derived, four foundation-derived, and four alignment-derived mechanisms on one surface.
- Every candidate is shown at display size and approximately 16 pixels.
- The user advanced A1, A2, B4, and C4 for precise construction.
- The user prefers B4. In application, it performs best as a navigation mark, app icon, favicon, and compact product signature.
- Large standalone use amplifies the mountain reading. Dark surfaces need a dedicated color-reverse mark to preserve the central join and foundation.
- One geometry decision remains before producing final identity assets and the broader design system.
- Higgsfield refinement round 1 produced three editable SVGs. None is production-ready: candidate 1 breaks the shared base, candidate 2 is visually heavy and drifts from the palette, and candidate 3 has the strongest structure but reads as paired A forms around a T-like spine.

## Review (2026-09-05, end of Phase A1 build)

- All eight Phase A1 units landed, each by one Opus subagent, with the join plan's changes folded in as built.
- Test suite: 602 tests green (`sh tests/run.sh`, about two minutes, system Python 3.9.6).
- SC1 and SC5 passed end to end on real test bases (template copy, real git, local bare remote, the fake gh, the actual
  skill scripts and the session-start wrapper). Record: docs/walkthroughs/2026-09-05-phase-a1-sc1-sc5-test-base.md.
- Two review passes (security, correctness) found 12 and 8 confirmed defects; all fixed with failing-then-passing tests,
  plus the orchestrator's own fix: updates refuse anything under `.claude/`.
- Not done, waiting on Brandon: GitHub remote and visibility, then the first commit and push; SC1/SC5 against a real
  GitHub remote; live Claude Code checks (combined hook output, plugin root in hook env, real gh output shapes).
- Open decision for Brandon: after a ledger-drafted proposal merges, the file is settled against the decision but is
  still asked for a threshold confirmation because no owner line exists.
