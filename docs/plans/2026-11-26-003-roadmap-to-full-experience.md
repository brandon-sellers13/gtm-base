---
title: "Roadmap: from today to the full GTM Base experience"
date: 2026-11-26
status: agreed order, written for Brandon; each track keeps its own detailed plan; status brought up to date on 2026-11-27
---

# Roadmap: from today to the full GTM Base experience

## What the full experience is

A marketing team keeps one company base, and every person on it gets that base wherever they work. People in Claude Code work from a local copy that stays in sync. People in Claude chat, Cowork and ChatGPT get the same documents and the company's own skills through one connector. Changes come in as proposals with evidence, the owner of each document accepts them, every document a decision overtakes is flagged, and an outdated document is caught at the moment an AI is about to use it. A company can find GTM Base, sign up, set up a base, bring its team in and pay for it.

This plan lists everything left to build for that, in the order it should be built. Each track already has, or will get, its own detailed plan; this document only holds the order and how the tracks depend on each other.

## Where things stand on 2026-11-27

Built and live:

- The plugin through Release B (0.5.0), including the summarize-first setup that passed the fidelity gate.
- P1, backing up a base to its own private GitHub repository, with the security review's eight findings fixed.
- The web app (W1 to W6) at https://gtm-base-app.netlify.app: sign in with GitHub, create or back up a base, read it by CLASS part, accept or discard proposals, invite teammates, and keep or undo changes that skipped approval.
- The connector spike (S0), whose answers are in `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`.
- C1, C2 and C4 of the connector (pull requests #18 and #23), live on the same site: GitHub sign-in, one base per conversation, reading documents with the moment-of-use flag, and proposing a context change from chat. The ChatGPT run passed end to end on the test site. The Claude half of the run waits for Simona's invite.
- Four of Plan 1's nine units, merged into main by pull request #22: the signed company-skills requirements (4.1), who may approve what (4.2a), the base inventory (2.1) and the source map (2.5a).

## What is left, by track

### Track 1: the connector for Claude chat, Cowork and ChatGPT

Plan: `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`.

1. **C1, C2 and C4** are done and live.
2. **C3.** Skills served live, with the skill index in the connector's instructions and each skill arriving with the documents it needs. Built on 2026-11-27 on top of the runner, the skills folder and drift grade, and deployed to the test site only; it waits on its security review before anyone but Brandon connects.
3. **C5.** A short setup guide and a copyable Project instruction for each base, so a person working for several clients sets up one Project per client. Nothing blocks it.
4. Carried over from C1 and C2: the Claude half of the run, the refusal when a conversation asks for a second base, and the sign-in test with two GitHub accounts. All three need Simona's account.
5. A security review (one pass) of C3 before anyone but Brandon connects, then an end-to-end run in Claude and in ChatGPT across two Projects. C2's review found nothing at the bar, apart from one borderline proposal pattern, which Brandon decided on 2026-11-27 to close in C3's security pull request, for the plugin and the connector together.

### Track 2: teammates in Claude Code on a shared base

Plan: `docs/plans/2026-11-24-001-feat-web-app-plan.md` (units P2 and P3).

1. **P2.** Join a base from a link: a teammate says one line in Claude Code and gets the base on their computer as a seat. Today the plugin still refuses this with one sentence.
2. **P3.** Working on a shared base: recording a context change and the setup closing send their writes as proposals instead of refusing a base with a shared copy, and a seat never pushes straight to the main branch.
3. The end-to-end run with a second GitHub account: create, back up, invite, join, propose, accept, and undo a change that skipped approval. It needs a second account; Simona is the planned tester, waiting on her GitHub username and on Administration being approved on the development app's install.

### Track 3: company skills

Plan: `docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md` (Plan 1).

Four of its nine units are on main (see above). What is left, in Plan 1's order:

1. **3.1, the thin runner,** so a skill can run against a base the same way every time. It comes before the skills folder because installing a skill runs the runner's check.
2. **4.2b, the skills folder:** where a base keeps its own approved skills, and the rules for trusting them. Track 1's C3 and Track 4's drift grade wait on this and on the runner.
3. **2.4a, metric definitions and goals,** and **3.5, the creative-testing standard.**
4. **3.6, the first real skill on the runner** (Meta ads).

### Track 4: what a base holds

Plan: `docs/plans/2026-11-27-001-feat-track-4-base-contents-plan.md`, with all ten of its decisions made on 2026-11-27.

These make a base worth having. Without them, a new company's base holds little more than a customer profile and positioning.

1. **Unblocked now that the Plan 1 catch-up is merged:** T4.1 (a recorded decision suggests the documents built on it), T4.2 (messaging and voice), T4.3 (buyer personas and product) and T4.6 (the source map for any company), then T4.4 (competitors), T4.5 (design) and T4.7 (updating GTM Base).
2. **T4.8, drift grade,** the first skill that uses a base. It waits on Plan 1's runner and skills folder, and it is what gives C3 something worth serving in a demo.
3. **T4.9, the content brief, then T4.10, the outbound sequence,** which follow the pattern drift grade proves.

### Track 5: from a working product to one people can use

1. **Pricing.** Decided by Brandon on 2026-11-27: GTM Base stays 100 percent free and may be open-sourced, so there is no pricing or billing work. The plugin already declares the MIT license.
2. **Sign-up.** The app is invite-only through one allowlist, and opening it needs a sign-up path and the security review that goes with it. Brandon decided on 2026-11-27 that sign-up opens only after C3's security fixes are confirmed, P2's security review is done and both end-to-end runs pass, and that it then opens by invitation to a short list before anything is public.
3. **A domain and the app's public name,** in place of `gtm-base-app.netlify.app`. Brandon is buying the domain on Monday, 2026-11-30, and it blocks nothing before sign-up.
4. **Brandon's own live checks:** update the installed plugin from 0.4.0 to the current version, and see Claude Code's approval question for a backup with his own eyes.
5. **Loose ends:** the invite test with Simona (on hold by Brandon's choice, along with her GitHub username), deleting the two test repositories (`gtm-base-backup-test` and `gtm-base-backup-test-2`), and taking down the connector's test site once the Claude half of the run has passed.

## The order

| Step | What | Why this order |
|---|---|---|
| 1 | C1, C2 and C4 | Done on 2026-11-26 |
| 2 | The runner (3.1), then the skills folder (4.2b); alongside them, Track 4's T4.1, T4.2, T4.3 and T4.6, and the connector's C5 | C3 cannot serve skills until a base has an approved skills folder, and installing a skill runs the runner's check. The Track 4 units and C5 touch different files and wait on nothing |
| 3 | Drift grade (T4.8), then C3 | C3 needs a real skill to serve |
| 4 | P2 and P3 | Teammates in Claude Code can work on a shared base |
| 5 | Both end-to-end runs, with the security reviews for C3 and P2 | The checks that the full experience works for two people |
| 6 | Sign-up and a domain, with no pricing or billing work | Open the free product, by invitation to a short list first and then to everyone |

The rest of Track 4 (T4.4, T4.5, T4.7, then T4.9 and T4.10) and of Plan 1 (2.4a, 3.5, 3.6) runs alongside steps 3 to 5.

## Decisions waiting on Brandon

Brandon decided each of these on 2026-11-27, so none is waiting on him now.

1. **The borderline proposal pattern** C2's security review found is being closed in C3's security pull request, for the plugin and the connector together.
2. **A city's name that is also a customer's name** (for example a customer recorded simply as "Denver") stays refused by the customer-name check. The refusal now tells the person how to fix it, which is to record that customer under a fuller name, such as the company's full name.
3. **Simona's GitHub username** is on hold, by Brandon's choice. The invite test and the two-person end-to-end runs wait with it.
4. **Sign-up** opens only after C3's security fixes are confirmed, P2's security review is done and both end-to-end runs pass. It then opens by invitation to a short list before anything is public.
5. **Pricing.** GTM Base stays 100 percent free and may be open-sourced, so step 6 is sign-up and a domain, with no pricing or billing work. The plugin already declares the MIT license.
6. **The domain.** Brandon is buying it on Monday, 2026-11-30, and it blocks nothing before sign-up.

## Review standard

Units get no review of their own; the end-to-end runs are the main checks. A security review (one pass) happens where a sign-in token, another person's computer, or the connector's sign-in is involved: before C3 reaches anyone but Brandon, before P2 ships, before 4.2b's skill install ships, and before sign-up opens.
