---
title: "Roadmap: from today to the full GTM Base experience"
date: 2026-11-26
status: agreed order, written for Brandon; each track keeps its own detailed plan
---

# Roadmap: from today to the full GTM Base experience

## What the full experience is

A marketing team keeps one company base, and every person on it gets that base wherever they work. People in Claude Code work from a local copy that stays in sync. People in Claude chat, Cowork and ChatGPT get the same documents and the company's own skills through one connector. Changes come in as proposals with evidence, the owner of each document accepts them, every document a decision overtakes is flagged, and an outdated document is caught at the moment an AI is about to use it. A company can find GTM Base, sign up, set up a base, bring its team in and pay for it.

This plan lists everything left to build for that, in the order it should be built. Each track already has, or will get, its own detailed plan; this document only holds the order and how the tracks depend on each other.

## Where things stand on 2026-11-26

Built and live:

- The plugin through Release B (0.5.0), including the summarize-first setup that passed the fidelity gate.
- P1, backing up a base to its own private GitHub repository, with the security review's eight findings fixed.
- The web app (W1 to W6) at https://gtm-base-app.netlify.app: sign in with GitHub, create or back up a base, read it by CLASS part, accept or discard proposals, invite teammates, and keep or undo changes that skipped approval.
- The connector spike (S0), whose answers are in `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`.

In review: C1, the connector's endpoint, GitHub sign-in and one base per conversation (pull request #18).

## What is left, by track

### Track 1: the connector for Claude chat, Cowork and ChatGPT

Plan: `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`.

1. **C1.** The endpoint, sign-in and one base per conversation. In review.
2. **C2.** Reading documents, with the moment-of-use flag and its three choices in the answer. This is the part competitors such as Notion Skills and Calven do not do, so it comes before anything else in this track.
3. **C3.** Skills served live, with the skill index in the connector's instructions and each skill arriving with the documents it needs. It is blocked until Track 3 builds the runner and gives a base an approved skills folder.
4. **C4.** Proposing a context change from chat, as a proposal the owner accepts in the web app or in Claude Code. This is how any AI's noticing of a change lands in the governed record.
5. **C5.** A short setup guide and a copyable Project instruction for each base, so a person working for several clients sets up one Project per client.
6. A security review (one pass) before anyone but Brandon connects, then an end-to-end run in Claude and in ChatGPT across two Projects.

### Track 2: teammates in Claude Code on a shared base

Plan: `docs/plans/2026-11-24-001-feat-web-app-plan.md` (units P2 and P3).

1. **P2.** Join a base from a link: a teammate says one line in Claude Code and gets the base on their computer as a seat. Today the plugin still refuses this with one sentence.
2. **P3.** Working on a shared base: recording a context change and the setup closing send their writes as proposals instead of refusing a base with a shared copy, and a seat never pushes straight to the main branch.
3. The end-to-end run with a second GitHub account: create, back up, invite, join, propose, accept, and undo a change that skipped approval. It needs a second account; Simona is the planned tester, waiting on her GitHub username and on Administration being approved on the development app's install.

### Track 3: company skills

Plan: `docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md` (Plan 1).

Four of its nine units are built (4.1, the signed requirements; 4.2a, who may approve what; 2.1, the base inventory; 2.5a, the source map), on the branch `claude/plan-1-read-side-6c5559`, which has never been merged and is now behind main by Release B, P1 and the web app.

1. **Bring the Plan 1 branch up to date with main** and merge its four built units. This is real work, because main has changed in the same areas, and the full suite has to pass afterwards.
2. **3.1, the thin runner,** so a skill can run against a base the same way every time. It comes before the skills folder because installing a skill runs the runner's check.
3. **4.2b, the skills folder:** where a base keeps its own approved skills, and the rules for trusting them. Track 1's C3 waits on this and on the runner.
4. **2.4a, metric definitions and goals,** and **3.5, the creative-testing standard.**
5. **3.6, the first real skill on the runner** (Meta ads).

### Track 4: what a base holds

Plan: `docs/plans/2026-09-19-002-roadmap-after-phase-1.md`. Not planned in detail yet.

These make a base worth having. Without them, a new company's base holds little more than a customer profile and positioning.

1. Context documents: messaging and voice, design, competitors, personas, goals.
2. The sources-of-truth file, and keeping GTM Base itself up to date.
3. The first skills that use a base: drift grade, content brief, outbound sequence. The first of these is also what gives the connector's skills something worth serving in a demo.

### Track 5: from a working product to one people can buy

1. **Pricing and packaging.** Not decided. Calven, the nearest competitor, charges $99 a month for one seat and $1,000 a month (or $800 a month billed annually) for unlimited seats.
2. **Sign-up.** The app is invite-only through one allowlist; opening it needs a sign-up path and the security review that goes with it.
3. **A domain and the app's public name,** in place of `gtm-base-app.netlify.app`.
4. **Brandon's own live checks:** update the installed plugin from 0.4.0 to the current version, and see Claude Code's approval question for a backup with his own eyes.
5. **Loose ends:** the invite test with Simona, and deleting the two test repositories (`gtm-base-backup-test` and `gtm-base-backup-test-2`).

## The order

| Step | What | Why this order |
|---|---|---|
| 1 | Finish C1 and C2 | The connector's reading half, including the moment-of-use flag, is what reaches the most buyers and what competitors lack |
| 2 | Bring Plan 1 up to date, then build the runner (3.1) and the skills folder (4.2b) | C3 cannot serve skills until a base has an approved skills folder, and installing a skill runs the runner's check |
| 3 | C3 and C4 | Skills and proposals from chat complete the connector |
| 4 | P2 and P3 | Teammates in Claude Code can work on a shared base |
| 5 | Both end-to-end runs, with the connector's security review | The checks that the full experience works for two people |
| 6 | Pricing, sign-up and a domain | Turn the working product into one people can buy |

Track 4 runs alongside steps 2 to 5, starting with the first skill that uses a base, so that C3 has a real skill to serve.

## Decisions waiting on Brandon

1. Pricing and packaging, including whether the connector comes with every plan or a paid tier.
2. Whether the connector may keep a small store for "one base per conversation" (the spike's recommendation is in the connector plan).
3. Simona's GitHub username, for the invite test and the two-person end-to-end runs.
4. When to open sign-up beyond the allowlist.

## Review standard

Units get no review of their own; the end-to-end runs are the main checks. A security review (one pass) happens where a sign-in token, another person's computer, or the connector's sign-in is involved: before the connector reaches anyone but Brandon, before P2 ships, and before sign-up opens.
