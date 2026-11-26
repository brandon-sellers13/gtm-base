---
title: "Phases 2 and 3: the decisions and material Brandon owns"
type: decisions
status: decided for Plan 1
date: 2026-10-10
plan: docs/plans/2026-09-19-002-roadmap-after-phase-1.md
---

# Phases 2 and 3: the decisions and material Brandon owns

Brandon wants the build to reach the end of Phase 3. Release B is being finished in its own session, and this document collects everything after it that only Brandon can answer, so the next plan can be written once and built without stopping. Each decision has a recommended answer and a runner-up. Where a fact comes from a note rather than a live check, it says so.

The Gridwise base today covers Gridwise Analytics only. Its customer profile says so in its first paragraph, and it holds two documents, the customer profile and the positioning, both drafts last confirmed on September 19, 2026. It is still on the older layout, which Release B moves to the new one.

## Decisions

### Scope and order

| # | Decision | Recommended | Runner-up | Answer |
|---|---|---|---|---|
| D1 | What the base covers through Phase 3 | Gridwise Analytics only. The test at the end of Phase 3 is a real outbound sequence, and outbound is how Analytics sells, while the driver app is sold through paid acquisition. | Add the driver app as a second set of context in the same base | **Decided 2026-10-10: both businesses, in one base.** The first answer was Analytics only, and it changed once the Meta ads skill became the first skill, because that skill tests driver-app creative and an Analytics-only base gives it nothing to read. |
| D2 | Whether call 13 (no skill until the company-skills brainstorm settles who may approve a skill change) also holds back the outbound sequence | No. The outbound sequence ships inside the plugin, not as a file under a base's `skills/` folder, so call 13's refusal never touches it. Holding it back delays the first pipeline result by a full brainstorm cycle. | Yes, the brainstorm runs and is signed off first | **Decided 2026-10-10, a different answer: the outbound sequence is not the first skill. The first skill is the Meta ads creative-testing skill, because it is the one in daily use, and the company-skills brainstorm runs and is signed off before it.** |
| D3 | How Brandon checks the work live | One live session per release rather than one per unit. That makes about three sittings for Phases 2 and 3 instead of about nine. | Keep the plan's rule of one live check for every unit that changes a sentence | **Decided 2026-10-10: one live session per release.** |
| D4 | How many plans | One plan covering Phases 2 and 3, in the order call 48 set: the inventory, the runner and the outbound sequence first, with the company-skills brainstorm alongside, then the rest of Phase 2, then drift grade and content brief. | One plan per phase, as the roadmap first said | **Decided 2026-10-10: two plans, split by what has to be learned.** Plan 1 is the company-skills brainstorm, the inventory, the runner, metric definitions, goals, the source map, the Meta creative-testing standard, and the Meta ads skill running on the runner. Plan 2 is written after the Meta ads skill has run on real nights, and holds messaging, voice, design, product, buyer personas, updating GTM Base, drift grade and content brief. One plan for both phases was not chosen because Astra and Fable both said on 2026-09-19 that a plan that size is the wrong shape. |

### Product rules

| # | Decision | Recommended | Runner-up | Answer |
|---|---|---|---|---|
| D5 | Who may approve a change to a file under a base's `skills/` folder (the brainstorm's first question) | The base's owner, through the same local approval every context document already uses, recorded the same way. Only written instructions are allowed there; script files stay refused, because a script in a shared base runs on every teammate's computer. For the Meta ads skill this means its engine (`~/Gridwise/meta-ads`, written in Python) stays an installed tool outside the base, and the base holds the skill's instructions and its standard. The brainstorm still answers its other seven questions, and Brandon signs it off before the Meta ads skill is built. | Any person who has joined the base may approve | **Decided 2026-10-10, Brandon's own model: whoever makes a thing owns it.** The person who creates a skill owns that skill, and the person who creates a piece of the context layer (a messaging document, any context document) owns that document. A change to a skill or a document may be made and approved by its owner, or by the base's owner or administrator, and nobody else. Ownership has to be provable, not just claimed. The brainstorm works out how ownership is recorded and proven (the `owner:` line each document already carries, the saved history of who created it, and the seat's identity), how it passes when someone leaves, and how this fits Unit 1.7e's proof that a person said yes. Whether script files may live in a base stays one of the brainstorm's open questions. |
| D6 | The sections of the design file (needed for Plan 2, can wait) | Colour (named roles rather than lists of codes), type (which family is used for what), logo rules (including what may never be done to it), and forbidden devices. Tone is left out, because it belongs in the voice document and two places would drift apart. | The five sections in the roadmap, tone included | |
| D7 | How "update GTM Base" knows a newer version exists (needed for Plan 2, can wait) | It does not try. It prints the installed version and the one step that updates the plugin, and makes no network call, which keeps the promise that the plugin reads nothing over the network. | One network check, only when the person asks, answering "unknown" when it fails | |
| D8 | Whether skills get diagrams of their own in the logic atlas | No new diagrams. Each skill is described on the existing first diagram, since every skill runs through the same runner. | One new diagram for the runner | **Decided 2026-10-10: one new diagram for the runner.** |

### Housekeeping

| # | Decision | Recommended | Runner-up | Answer |
|---|---|---|---|---|
| D9 | What "Sol agents" means (call 7) | From my notes of September 16, 2026, Sol is the Codex model `gpt-5.6-sol`, the default in `~/.claude/tools/codex-copy.sh`. Recommended use: Opus builds each unit, Astra gives the outside review, and Sol runs the cheaper confirmation passes after Astra's fixes. | Opus builds, and Sol is not used | **Decided 2026-10-10: Sol builds alongside Opus.** Units are split between Opus and Sol builders, and Astra stays the outside review. Which units go to Sol is set in Plan 1. |
| D10 | Add `~/GTM Bases/` to the home-folder rule in the global CLAUDE.md (call 8) | Yes, one line saying it holds one folder per company base and is product data, not client work. | Leave the rule alone | **Decided 2026-10-10: yes, and done the same day.** The line also says never to move a base, because the plugin records where each base lives. |

## Material only Brandon can point to

Plan 1 needs M6, M7, M8 and M12, and only their driver-app halves, because the Meta ads skill is Plan 1's only skill. The Analytics halves of M6 to M8 move to Plan 2 with the rest.

Each item names the unit that needs it and the source I would propose from my notes. Brandon confirms the source or names a better one. Nothing here is copied into the base until Brandon approves the draft built from it.

| # | Unit | What is needed | Proposed source (from notes, not checked today) | Brandon's answer |
|---|---|---|---|---|
| M1 | 2.2 Messaging | The documents that say what Analytics claims, to whom, and with what proof | The positioning already in the base, the eleven segment pages in the Notion segment strategy, and the Q4 marketing strategy slides | |
| M2 | 2.2 Voice | The voice authority, and whether Analytics has its own business-to-business voice | The Gridwise Voice and Writing Guide in Notion, which my notes rank as the authority on all copy. It permits emoji sparingly, which contradicts the design system's no-emoji rule, and that conflict is unresolved. | |
| M3 | 2.3 Design | The visual authority | The "Gridwise Style Guide" in Figma, which my notes rank above `~/Gridwise/design-system/`. The two have not been compared, and the repository's README describes the logo wrongly. | |
| M4 | 2.4 Product | What Analytics sells, in the company's own words | Sales material and the reports at reports.gridwise.io | |
| M5 | 2.4 Buyer personas | Who inside each segment buys, kept separate from the segments themselves | The segment pages and the Analytics customer profile and messaging work from August 2026 | |
| M6 | 2.4 Metric definitions | The definitions the team actually uses, and where each number lives | For Analytics: the qualified-lead definition and the revenue-retention model in the Analytics workbooks, and pipeline from HubSpot. For the driver app: what counts as a trial start, a paying subscriber and monthly recurring revenue, which come from RevenueCat only, and cost per trial on Meta | **Brandon, 2026-10-10:** a driver-app trial is a "True Trial" in Mixpanel. Subscribers, payers and monthly recurring revenue still come from RevenueCat only. The Analytics definitions are not yet confirmed. |
| M7 | 2.4 Goals | The current targets | The Q4 2026 objectives and the Q4 marketing strategy's target accounts for Analytics, and the cost-per-trial target for the driver app | **Brandon, 2026-10-10:** the overall driver-app target is a payback period. There are targets for cost per trial and for cost per account link, each set separately for the app and for the web, and cost per account link is the number to watch most closely. The figures are kept privately by Brandon, outside this repository, and enter the Gridwise base through its goals document. The Analytics goals are not yet confirmed. |
| M8 | 2.5 Source map | Where spend, pipeline and contact data live, and what reads each one | HubSpot, Supermetrics, Clay, Instantly, Expandi and LinkedIn Campaign Manager for Analytics; the Meta ad account, RevenueCat, Mixpanel and the Notion creative registry for the driver app | **Brandon, 2026-10-10:** spend lives in the paid media dashboard. The other sources are not yet confirmed. |
| M12 | Plan 1, the Meta ads skill | The creative-testing rules in words, and confirmation that the numbers stay in the engine's settings file | `~/Gridwise/meta-ads/config.toml` for the numbers, the rules reference in the skill, and the Notion Meta Creative Tests registry | **Brandon, 2026-10-10: option A.** The base holds the business goals, and the engine keeps its own test thresholds in `config.toml`. The standard explains how each threshold relates to a goal, and a threshold changes only when Brandon decides it should. Having the engine read its targets from the goals was not chosen, because on the web it would kill every creative. |
| M9 | 3.2 Drift grade | One real piece of Analytics copy to grade | A live landing page or a recent outbound email | |
| M10 | 3.3 Content brief | One real brief, and the writer who will be handed it | | |
| M11 | 3.4 Outbound sequence | One real target account, the sending tool, and Brandon's yes before anything is sent | One of the target accounts, sent through Instantly or Expandi | |

## What happens with the answers

The answers are recorded as new calls in the build plan's "For Brandon" table, and the plan for Phases 2 and 3 is written from them. That plan is reviewed by Astra before building starts.
