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

## Live install day (2026-09-06)

- [x] Plugin installed from the public marketplace at brandon-sellers13/gtm-base; manifest fix (0.1.1), two-entry
      session-start hook (0.1.2), offer delivered in the first reply (0.1.3), gate scoped to bases and seat working
      folders with the offer repeating until answered (0.1.4), not-now written down and the bridge sentence (0.1.5)
- [x] Decided 2026-09-06: the owner accepting a change counts as the owner's yes; built and tested
- Open: a forced send to the default line of work is still refused in every repository (it needs nothing read);
  narrow it to bases if it gets in the way

## Join plan release one (2026-09-06)

- [x] Unit 1 (account state, trust surface, offer) landed with the first plan's Unit 3 and the 0.1.x fixes
- [x] Unit 2 create_base and location; migration left for release two
- [x] Unit 3 source intake, test-first
- [x] Unit 4 drafting prompts and the review loop
- [x] Unit 5 the join skill, setup mode, closing; same-run exemption keyed on the run id
- [x] Security and correctness review of the four units: 21 findings, all fixed with tests (948 green)
- [ ] Ship 0.2.0, then Brandon runs "set up my company base" for real; write docs/walkthroughs/2026-09-user-one-paste-path.md from that run
- [ ] Release step before a second seat joins: replace the forty-zero pinned id in the settings template with a real one

## Join release-one review fixes (agent record, 2026-09-06)

Working from the security and correctness review of the uncommitted join units.
Every fix got a failing-then-passing test and a CHANGELOG bullet.

## Security

- [x] join-01 freeze the listing the person saw, refuse `listing-changed`
- [x] join-02 screen exemptions only from a parsed draft's frontmatter lines
- [x] join-03 sanitize every value printed into the name and value channel
- [x] join-04 stamp every owner key, refuse unknown frontmatter keys
- [x] join-05 revalidate the parent on create, require a joined base in the shim
- [x] join-06 sniff the whole head for a key header
- [x] join-07 the paste path writes the sources-read marker
- [x] join-08 validate the company name before it reaches a prompt
- [x] join-09 refuse a fence marker whatever its letter case
- [x] residual: the reading rules say where a paste is held
- [x] residual: a bad affected path comes back as a refusal with its own code

## Correctness

- [x] C1 one rejected source no longer kills the whole step
- [x] C2 an assembly with no surviving source is refused
- [x] C3 skip is offered only from the second document onward
- [x] C4 the shim asks for a work email address when there is none
- [x] C5 the offer answer is recorded when the base is created
- [x] C6 a second closing with the same note does not throw the finding away
- [x] C7 an unfinished run's folder is cleared at the next start
- [x] C8 the future-date clamp is carried through and reported
- [x] C9 the resolved root is what gets written into
- [x] residual: an empty owner address is refused
- [x] residual: the closing note goes through the same write checks

## Verification

- [x] `sh tests/run.sh` fully green: 948 tests, up from 893
- [x] no long dashes in any touched file
- [x] the plain-language lint clean over the skill, both reference files, and
      the four new CHANGELOG bullets

## Review

Twenty one findings closed, none left open.

Two of the fixes changed shapes other code depended on, and both were worth it.
`read_sources` now returns the sources and, beside them, the label and reason
for every one that could not be used, which is what lets the assistant tell the
person which of their own documents was left out. And `list_sources` now writes
the list it showed down inside the run's folder, which is the only way the yes
can be taken against what the person actually saw rather than against a second
look at the folder.

Two existing tests changed because the behaviour they pinned was the behaviour
being fixed. The offer answer is now recorded when the base is created rather
than at the closing, and a decision entry naming a file outside the base now
comes back as a refusal rather than as a path failure escaping the call.

One thing worth knowing for the next change. On a computer that does not tell
one letter case from another in a folder name, a parent already holding a
folder called `GTM-Base` is refused as `target-exists` rather than
`stray-base`. Both refusals are correct and the test accepts either.

# 0.2.3: what the first real run on a hundred and four files showed

Two defects, found on Brandon's own setup run on 2026-09-06 against a folder of
one hundred and four readable files. Seven documents were refused outright for
holding comments the author had written to themselves, and ninety-six were
dropped because the cap was applied in folder order, which put all fourteen of
the customer segment files past it.

## Plan

- [x] A. Hidden content is removed from a source and counted, never fatal. The
      refusal for text that writes the fence's own lines stands and now runs
      after the removal.
- [x] B. Each step orders its sources before the cap: the profile reads the
      customer files first, the positioning the messaging files, the decision
      entry the newest. The cap goes from sixty thousand to two hundred and
      forty thousand characters.
- [x] C. A preview runs in front of every draft, writing nothing, and says what
      goes in and what does not with the reason for each. `--only` and
      `--only-folder` narrow one draft to part of the list already agreed to.
- [x] D. The sentence a person reads says the numbers, names what is left out,
      and asks which files or folder matter for this document.
- [x] the amendment appended to the join plan as r2.2, with the deferred brief
      pipeline's trigger recorded as fired and the pipeline still deferred
- [x] `sh tests/run.sh` green, no long dashes in any touched file

## Review

Nine hundred and seventy seven tests pass, twenty eight of them new.

Three existing tests changed because the behaviour they pinned was the
behaviour being fixed. Two asserted that a hidden character and a comment
refuse the whole source, and they now assert that the part goes and the
document stays. The third pinned the shim reading out a source left out for
hidden content, and it now uses a document that writes the fence's own lines,
which is the reason that is left.

Two decisions worth knowing about. The removal takes out exactly what the
outgoing-content check calls hidden and nothing more, so a closing tag such as
the one that ends a span is left in the text, because the check reads it as
ordinary words and this module should not decide on its own what somebody meant
to write down. And the version was moved to 0.2.3 in the manifest, the library,
the guide, and the plugin README, because a changelog heading for a release the
manifest does not name would be the first thing to go stale.
