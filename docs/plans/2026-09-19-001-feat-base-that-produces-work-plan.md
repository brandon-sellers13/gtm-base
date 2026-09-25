---
title: "feat: A base that produces work"
type: feat
status: active
date: 2026-09-19
origin:
  - docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md (Amendment r2.4, sections A to I)
  - docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md (Amendment r2.5)
  - docs/reviews/2026-09-19-codex-setup-shape-verdict.md
reviews:
  - docs/reviews/2026-09-19-plan-review-astra.md (Astra through Codex; verdict on revision 1: not ready)
  - docs/reviews/2026-09-19-plan-review-fable.md (Fable 5.1; verdict on revision 1: ready only with changes)
revision: 2.3
---

# feat: A base that produces work

**Target repo:** `gtm-base` (this repository). This plan carries out Amendment r2.4 of `docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md` and Amendment r2.5 of `docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md`, under the conditions set in `docs/reviews/2026-09-19-codex-setup-shape-verdict.md`, and then takes the base past setup into the work it is supposed to produce. Where it changes a behavior either earlier plan defined, the change is named in the unit that makes it, so all three documents stay true.

## Overview

GTM Base today can be set up and can notice that a document is out of date. What it cannot do is produce marketing work, and after three real setup runs it also interrupts the person, uses a word for its own central idea that needed three explanations, and holds two files and no skills when setup ends.

As of revision 2.1 this plan covers Phase 1 only. Brandon's call on 2026-09-19: the context goes into the base first, and skills that use it come after, so the runner and the outbound sequence that revision 2 pulled forward went to the roadmap with the rest. Revision 1 held twenty units in four phases. Both reviews of it said that was the wrong shape for one plan, so Phases 2 to 4 moved, word for word, to `docs/plans/2026-09-19-002-roadmap-after-phase-1.md`, and each becomes its own plan after the first skill has been used on real work.

Phase 1 is the correction. It follows the six steps `docs/reviews/2026-09-19-codex-setup-shape-verdict.md` sets under "Smallest ordered change set and proving tests", and it adds units that verdict never covered, each named as an addition: the UX standard lands second so every later unit writes to it, approving a proposed change locally lands before anything depends on a proposal, quiet by default and the rename come from Amendment r2.5. The fidelity replay still gates the release that changes how setup drafts.

"Revision 2: what the two reviews changed" below is the map from each review finding to the unit that answers it. An agent briefed on a unit reads that unit and its rows in that table.

## Revision 2: what the two reviews changed

Astra (through Codex) and Fable 5.1 reviewed revision 1 on 2026-09-19 without reading each other. Astra's verdict was not ready; Fable's was ready only with changes. They agree on the three things that matter most: no proposal can complete on a base that has no shared copy, the fidelity gate could pass without proving anything, and twenty units is too many for one plan. Findings are named A1 to A12 for Astra and B1, H1 to H8, M1 to M9 for Fable. Everything in this table is decided and recorded. The calls that are Brandon's are listed under "For Brandon", each with the default this revision is written to.

| Finding | What was wrong | What revision 2 does | Where |
|---|---|---|---|
| B1, A2 (both blockers) | `compose_proposal` refuses a base with no shared copy, the Gridwise base has none, and no shipped code ever marks the first backup as reviewed. Every "no becomes a proposed change" ended at a refusal | New Unit 1.2b: the owner approves a staged change inside Claude and it is applied to the local base, with the same screens, evidence, confirmation, and corrections record. The outgoing-data gate is not weakened | 1.2b, P36 |
| A1 (blocker), H8 | The migration could hide entries (a refusal, then a writer creating the new folder, then the reader ignoring the old one), could block its own retry by dirtying the tree, cited a `migrate.py` that does not exist, missed consumers, and broke the "catches" number | The reader reads both folders and joins by entry id. The migration is a recorded transaction with a commit point and a recovery step, and the folder move and the field rewrite are two separate changes. Consumer list completed. `report.py` looks under both paths | 1.4 |
| A3 (blocker), M3 | The fidelity gate could pass on one case, scored by nobody named, or by merely building the fallback | Scorer named and the builder barred from scoring. Each corpus and its answer key frozen before any behavior unit is built. A missing case means incomplete, never pass. Any fix must pass the same three replays afterward. Case one is run against 0.2.6 now | 1.9, 1.1 |
| A4, H5 | The moment-of-use flag had no action contract, offered a fix nobody had written, treated "use it as is" as a confirmation, and had no real caller in Phase 1 | The sequence is defined: detect, prepare a real candidate, pause, get the choice, resume. "Use as is" leaves the flag standing. "Fix first" waits for an approved application through 1.2b. "It already reflects this" is a separate confirmation. The marker-only interruption is removed. A measured live trial and a read-hook evaluation are added. Until a skill exists, the deterministic callers are the three Phase 1 entry points that hand a document to the model | 1.3 |
| H1 | Sixteen units shipped before one piece of usable work, and the dependency forcing that order was soft | Revision 2 pulled the runner and the outbound sequence forward. Revision 2.1 reversed that on Brandon's call: context first, skills after. Both units, P37, and SC-C are in the roadmap, which now orders what a base holds ahead of any skill | Roadmap |
| H2, H3, A10 | The UX standard landed last and rewrote wording already checked live. Its lint read the instructions to the assistant, not the sentences people read, which live in Python. The one-question check rejected P4's own required wording, which has no question mark | New Unit 1.1b lands the standard, the four-line format, and the lint second. The lint covers a registry of the Python sentences, asserted complete by a test. The ask check counts one delimited request block and accepts an imperative. The owner's read-aloud check is the acceptance test and the lint is described as a floor. 1.8 shrinks to a sweep of text no unit touched | 1.1b, 1.8 |
| H4, A contradiction 5 | Six current steps break the standard and no unit fixed them; "show each cleaned body whole" contradicted "never paragraphs" | One ruling per step is recorded in 1.1. The interaction is a short wrapper (what was removed, the opening lines, where the whole cleaned file is) and the complete artifact is separately readable, with the yes bound to its hash | 1.1, 1.7c, P21, P28 |
| H6 | `_review_items` keys on a run id that closing entries will no longer carry, so the finding 1.2 corrects was dead by 1.5 | 1.2 rekeys the finding: a drafted line on the file, an open entry that affects it, and source material dated before the change happened | 1.2, P22 |
| H7, A5, A6, A7 | Unit 1.7's write order contradicted itself; duplicate-heading rejection did not establish that a document can be edited later; resumption covered finished files and not interrupted writes; "adopted text stays data on every later read" was promised and assigned to no Phase 1 unit | 1.7 splits into four units. Order is written as numbered steps and the profile still creates the base. Adoption accepts only the heading grammar the editor supports. Recovery is per file, bound to the approved bytes, with a failure injected after each step. Every Phase 1 path that hands a context file to the model is named and fenced | 1.7a to 1.7d, 1.3 |
| A8 | Optional kinds and rubrics placed in the company-base template get copied into every new base, which makes absent-only adoption refuse them, and never reach an existing base | Recorded for the roadmap: starter content lives in the plugin and enters a base only by an owner-approved request | Roadmap |
| A9 | Comparing version bodies was assigned to the survey, which runs before consent and reads names and first headings only | The survey groups and ranks by name. Bodies are compared only after consent, and a test proves the survey reads no body | 1.6 |
| M1 | P3 could not be "rerun unchanged" across the rename | The old-layout SC1 test stays byte-identical as the tolerant-reading proof and a new-layout twin is added | P3, 1.4 |
| M2, Astra test table | Some scenarios would pass with no code change or without proving the behavior | Each is replaced in its unit: closed change newer than the sources with an open control; resumed setup with earlier dates and the same result on another seat; real entry points rather than a fixture for the moment-of-use check; malformed metadata, dirty-tree and default-branch refusals for adoption; confirmation paths exercised while a marker remains | 1.2, 1.3, 1.5, 1.7c, 1.7d |
| M4 | Giving the map a confirmation line makes it come due again later | The map is excluded from questions and reviews by its kind, which also covers the base created before this unit. No confirmation line is written for it | 1.2, P12 |
| M5, A7 | Adopted text is unfenced on the only read path Phase 1 has | The injected instruction gains the data-not-instructions sentence, and the residual risk is recorded | 1.3, 1.7c |
| M9 | "Ordered exactly as Codex sets out" was not accurate | The Overview and the Phase 1 header say which units are Codex's six steps and which are additions, and that Amendment r2.5 had no outside review before these two | Overview, Phase 1 header |
| A, condition A | Unit 1.1 omitted the parent strategy structure, origin R22 and R23, and the first plan's Unit 3 | Added to 1.1's file list | 1.1 |
| A, condition C | "One window" was never named | The dismissal lasts the base's confirmation threshold, 30 days unless the map sets another, which is what `stale_check.run` already uses | 1.5, P7, P17 |
| A, condition E | A mixed-product document cannot be made valid by filtering file names | A document that covers more than the recorded scope is refused for adoption with the offer to draft that segment instead. Scope is enforced by the person dropping named places, recorded with the scope label, not by a text filter | 1.7a, 1.7c |
| H8, last items | `decided_by` became `noted_by` while P5 still showed "who decided"; the lint banned "decision" and not "ledger" | The line a person reads says who noted the change, because a competitor's launch has no decider. "Ledger" joins the banned words for text a person reads | 1.4, P5 |
| Fable lows | Thin-runner reference location; `draft-positioning.md` also asks for the marker; P16 asks two questions; r2.4 C.2 still says the daily block asks; an older plugin reads a migrated base as empty | Each fixed in the named unit. The last is recorded against release two, because one seat exists today | Roadmap, 1.7b, 1.5, 1.1, Later phases |
| H5(a), A question 6 | Shipping 1.2 without 1.5 would give a release in which setup captures no change at all | Release semantics are fixed now. See "Releases" under Execution Posture | Execution Posture |

## Problem Frame

Three real runs and one competitive read produced this plan. The runs are recorded in the two amendments; the read is `docs/ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md`.

**The base holds two files and no skills.** At the end of setup a base holds `context/strategy/icp.md`, `context/strategy/positioning.md`, a confirmation line for each, and a template tree of empty folders. The parent scope (`~/Obsidian/Vault/Work/GTM-Base/2026-09-04-gtm-base-scope-v1.md`) promised `messaging.md`, `voice.md`, `competitors.md`, `personas/`, `metrics/`, `plan/`, six core skills and three starter skills. None of the skills that use a base exist. The MKT1 comparison is blunt about the consequence: the thing a marketing team is already building by hand is shared skills, and GTM Base's addition to that is the trust model and the approval flow, neither of which matters if there is nothing to trust.

**Setup summarizes finished work.** On the third run (2026-09-19, `~/Gridwise`, Gridwise Analytics, 97 consented files) the customer profile draft read twelve finished, reviewed segment pages and returned one document under four fixed sections. It rewrote material the person had already finished. Codex's verdict on G is that the volume was not the cause: the reported character count fits below the current input cap at `plugins/gtm-base/lib/gtmbase/constants.py` (`DRAFT_SOURCES_MAX_CHARS`), so the loss is in output shape and synthesis, and the deferral of a summarize-first stage has to be earned by a replay rather than assumed.

**The base interrupts.** The first real return session opened a working session by asking whether the base's own map was still right. That is the worst possible first sentence: it interrupts work to ask about the one file that carries no meaning, only settings. Amendment r2.5 makes the base quiet by default.

**The vocabulary confuses.** The decision entry step was not understood by the product's own designer after three explanations, and on the day it is written it changes nothing the person can see, because a file drafted in the same run as the entry is confirmed against it by the same-run exemption in `plugins/gtm-base/lib/gtmbase/stale.py`. Amendment r2.5 replaces the word: what the base tracks is a **context change**, and the asking sentence is "Tell me if anything about the context of the business changed that we should account for."

Six more findings from the third run carry into Phase 1: plan and metrics words matched engineering folders and proposed ten places where two were right; the narrowing question was asked again after the person had already chosen four folders; draft ordering read an older file and left out its final sibling and spent room on templates; the preview said files were left out without saying why a draft reads a limited amount; an approved file was saved with an unanswered `[your call: ...]` marker in it; and nothing in setup asked whether the base was for the whole company or for one product line.

## Requirements Trace

Each requirement is numbered P1 and upward, and names its source: a section letter of Amendment r2.4, a numbered section of Amendment r2.5, a condition from `docs/reviews/2026-09-19-codex-setup-shape-verdict.md`, or a decision Brandon made on 2026-09-19 that this plan carries rather than reopens.

| Id | Requirement | Source |
|---|---|---|
| P1 | Setup drafts two documents, the customer profile and the positioning. The context-change entry is not a required drafted step. J8, J9, J10, J17, join SC1 and SC3 are amended in writing before any code changes. | r2.4 A; Codex condition A and ordered step 1 |
| P2 | A base with two confirmed files and no recorded changes gets an honest baseline finding that says both documents were confirmed today, that no context change is recorded, that the base therefore cannot yet check whether a change has made either document out of date, and that names the date each confirmation comes up for review. It never says there is no date to watch. | r2.4 A; Codex condition A |
| P3 | The first feature's own SC1 (a hand-entered change yields a correct flag and a drafted proposal) keeps its independent test and is rerun after every Phase 1 unit. Across the rename, the old-layout test stays byte-identical as the proof of tolerant reading, and a new-layout twin is added beside it (r2, Fable M1). | Codex condition A and ordered step 6 |
| P4 | The optional closing question is asked once, after three plain sentences explaining what a context change is, why the base wants it, and how it is used, with one concrete example. Its words are "Tell me if anything about the context of the business changed that we should account for. One sentence is enough, or say skip." | r2.4 B and I; r2.5 "Context change, not decision" |
| P5 | A sentence given at the closing becomes a proposed entry shown whole before it is written: the date it happened, who noted it, which documents it affects, and the review date are each the person's to correct (r2: "who noted it", because a competitor's launch has no decider and the field is `noted_by`). The entry does not carry the setup run's id, so the same-run exemption never applies to it. | r2.4 B; Codex condition B |
| P6 | For each affected document the person is asked separately whether that document already reflects the change. A yes writes a confirmation naming the change. A no leaves the document flagged and the fix goes through the proposal path, because setup never edits a file it has already written. At the closing this is asked only for the two required documents; any other affected document is left flagged for the review (r2, Fable H4). | r2.4 B; Codex condition B |
| P7 | Skip is a complete answer. It dismisses the quiet-record reminder for the base's confirmation threshold (30 days unless the map sets another) and is counted apart from the file-confirmation yes rate. | r2.4 B; Codex condition C |
| P8 | At the start of a session the base loads its context and says nothing. No question leads the first reply and no question id is issued. | r2.5 item 1 |
| P9 | The base speaks up on its own in exactly one case: a document about to be used has been overtaken by a recorded context change. It names the document, the change, and the date, and asks whether to use the document as it is or fix it first. It says a fix is ready only when a prepared one exists, and otherwise offers to prepare one. "Use it as is" leaves the flag standing and confirms nothing. "Fix it first" waits until the owner has approved the change (P36). "It already reflects this" is a separate answer that writes a confirmation. No work product is produced before the choice. An unanswered marker alone never interrupts. The check is a local lookup and makes no network call (r2, Astra 4, Fable H5). | r2.5 item 2 |
| P10 | "Review my base" walks what is due and what has been proposed as one short list in one sitting. Question ids, the asked log, not now, and a no that becomes a prepared change all work as before, inside the review. | r2.5 item 3 |
| P11 | A weekly one-line nudge exists and is off by default. A person can turn it on, and can silence the base for a month or until they ask. | r2.5 item 4 |
| P12 | The map is never asked about. It is left out of questions and reviews by its kind, which also covers a base created earlier, and the template's placeholder date is removed (r2, Fable M4: a confirmation line would only make it come due again). | r2.5 item 5 |
| P13 | The AI always proposes and never applies without the owner's yes. Auto-apply is a later rung earned from a base's own record of approvals and corrections, and is out of scope here. | r2.5 item 6; Brandon 2026-09-19 |
| P14 | Everywhere a person reads it the word is "context change". Internally `work/decisions/` becomes `work/changes/`, the entry gains `kind: change`, and its fields keep their meaning with plainer names (`happened_on`, `written_on`, `noted_by`, `source`, `affects`, `review_by`). | r2.5 "Context change, not decision" |
| P15 | The one existing base is migrated by the plugin, and a base that still holds `work/decisions/` is read correctly. | r2.5; Brandon 2026-09-19 |
| P16 | A local hand edit to a context file asks what changed and why. A strategic answer travels with the proposal as its change entry. A typo fix records no change and is not blocked. | r2.4 C; Codex condition C |
| P17 | A quiet record is asked about inside the review, not at session start, at most once a session, with a dismissal that expires, outside the yes-rate accounting. An empty record is behind immediately rather than after the window, which the shipped code already does, so the new behavior to prove is the dismissal and its return. The dismissal lasts the confirmation threshold. | r2.4 C; Codex condition C |
| P18 | `context/strategy/icp.md` is the umbrella profile: who the company sells to overall, each segment in one short paragraph, and what they share. `context/strategy/segments/<slug>.md` holds one segment at full depth with `kind: segment`. A company with one segment has only the umbrella, at full depth. Segments are distinct from buyer personas, which keep their own folder. | r2.4 D |
| P19 | The segment inventory is settled before the umbrella is approved. A segment the person left out is named in the umbrella as pending, in words, never as a link; a segment chosen for adoption is named plainly, and whether its file exists yet is computed, never written into the umbrella. An interrupted import resumes, including a write interrupted partway through one file (r2, Fable H7, Astra 6). | r2.4 D; Codex condition D and the umbrella write-order finding |
| P20 | A finished document may be adopted instead of redrafted only when it passes a per-file contract: named by the person as the authoritative version for one segment; original settings block discarded and a library-written one put in its place; hidden content removed and counted, then fence-marker, contact and key screens run on what is left; headings limited to the grammar the proposal editor supports, so a later edit lands in the right section (no duplicate headings at one level, no heading-shaped line inside a code fence, no underlined headings); the document covers no more than the recorded scope; destination a safe slug that collides with nothing, under a folder that is not a link. | r2.4 D; Codex condition D |
| P21 | The person is shown, for each document, what was removed, its opening lines, and where the whole cleaned file is, and can read it whole before answering; approval is bound to those exact bytes (r2, pending Brandon's yes to call 5; revision 1 required every body shown whole in the conversation, which contradicts P28). A yes to many at once is allowed only after each has been shown, and individual exclusions are kept. Adoption never edits or moves the original. An adopted file is confirmed by the owner's own yes and by nothing else. | r2.4 D; Codex condition D, the batch-yes finding |
| P22 | The source-age finding keys on a drafted line on the file, an open change that affects it, and source material dated before the change happened, never on a run id, because closing entries carry none (r2, Fable H6). It looks only at files the change affects and only at open changes, so twelve segment files do not multiply unrelated findings. The first-backup review is rewritten for a base that can hold many files. | r2.4 D; Codex condition D, currency row |
| P23 | Setup asks once whether the base is for the whole company or for one part of it, when the person says so or the material plainly splits. The answer is recorded in the umbrella profile, not in the map, and is applied to selection and adoption as well as to the drafting prompts. | r2.4 E; Codex condition E |
| P24 | Plans and metrics count as marketing signals by default only in a place that also holds a profile, persona, or positioning file. A person can still add a standalone plans folder by name. | r2.4 F; Codex condition F |
| P25 | The consent record distinguishes a plain yes to the survey from an explicit choice of folders. An explicit choice is honored without a second narrowing question and gets a plain count to confirm. A changed list asks again. | r2.4 F; Codex condition F |
| P26 | The folder table says what each folder mostly holds, from paths only. Same-stem files are grouped as versions, a name carrying "final" outranks a newer date, a conflict between versions is said out loud, and templates and READMEs rank last. The preview says why a draft reads a limited amount. | r2.4 F; Codex condition F |
| P27 | An unanswered `[your call: ...]` marker is a state of its own, defined independently of `status`. A file carrying one is not confirmed and does not count as complete, the review step lists each marker and asks, and a later session can settle them without setup overwriting a file. The rule is enforced for adoption too. | r2.4 F; Codex condition F |
| P28 | Every step of every skill says what it is for in one sentence, shows output readable in seconds (a short list or a small table, never paragraphs), ties it back, then asks one thing. A context change is shown as four short lines: what changed, why, what it affects, when to look again. The plain-language lint grows to check this. | r2.4 H; Brandon 2026-09-19 |
| P29 | Before Phase 1 ships, three cases are replayed and read: the twelve finished pages, a company with several segments and no finished pages, and positioning inputs larger than one request. The check is whether segments, named deals, figures, and source versions survive. A fail builds the summarize-first step in this release, and the same three replays must then pass. The scorer is named and the builder does not score. Each corpus and its answer key are frozen before any behavior unit is built. A case that was not run means the gate is incomplete, never passed (r2, Astra 3, Fable M3). | r2.4 G; Codex condition G and ordered step 6 |
| P30 (moved to the roadmap) | A base inventory answers "what is my base missing?" against a named list of kinds, and adopts or drafts each on request. Setup stays at two documents. | Brandon 2026-09-19 |
| P31 (moved to the roadmap) | The map grows into a sources-of-truth file: for each kind of data, where it lives outside the base, which connected tool reads it, and the fallback. Context reads stay local. Source reads may be network calls and are never made at context-loading time. | MKT1 comparison item 3; Brandon 2026-09-19 |
| P32 (moved to the roadmap) | A plain "update GTM Base" step exists, because plugins do not refresh on their own. | MKT1 comparison item 5; Brandon 2026-09-19 |
| P33 (moved to the roadmap) | Skills that use the base ship in the core plugin ahead of backup and invite. This plan builds the runner and the outbound sequence; drift grade and the content brief moved to the roadmap. Each is a thin runner over context files, states which context files it reads, triggers the moment-of-use flag, keeps its rubric in a context file, and has owner-approved examples as its tests. | Brandon 2026-09-19; parent scope "rubrics live in context files and skills are thin runners", "an examples folder per skill" |
| P34 (moved to the roadmap) | Company skills shared across seats get a brainstorm whose deliverable is a requirements document. No code is written for them in this plan. | Brandon 2026-09-19; MKT1 comparison item 1 |
| P35 | Nothing is written outside the base, the plugin's own records folder, and a configured hooks directory. No MCP servers are declared. The logic atlas is updated in the same change as the code and republished. No invented number or timing appears anywhere, in the product or in the records. | Standing rules, Brandon 2026-09-19 |
| P36 | When a base has no shared copy, the owner can approve a proposed change inside Claude. The staged change is shown in the four-line form with the before and after, and on the owner's yes it is applied to the local base with the same screens, the same evidence, the same confirmation, and the same corrections record a merged proposal gets. A no discards or keeps the staged change. Nothing about what may leave the computer changes. | r2; Astra 2 and Fable B1, both blockers; the local half of the first plan's Unit 8 |
| P37 (moved to the roadmap) | One output of a skill that uses the base is used in real work at Gridwise, and what happened is recorded from the real run. | r2; Fable H1 |
| P38 | A base has one top-level folder per CLASS part: `context/` (nine files flat, following Brandon's published context standard: goals, product, icps, buyer-personas, positioning, messaging, voice, design, metrics; segments under `context/icps/`), `learning/` (changes, corrections, lessons), `access/` (`stack.md`), `skills/` (refused until a trust model exists), and `standards/`, with `work/` holding the approval machinery. Both layouts are read; one is written; the move is offered, recoverable, and never automatic. | Brandon 2026-09-25 (calls 9 to 14); MICW Issue #4 v10 and its context standard |

### Success criteria

Adopted from `docs/ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md`, stated honestly about what is in and out of scope.

**SC-A, the new computer test.** A person is fully productive on a new machine quickly. **In scope:** install the plugin, join a base from an invite link, and reach a rendered daily block and a working skill run without re-entering any context, which is the second-seat join plus a backup. **Out of scope in this plan:** the second seat and backup themselves are release two of the join plan and a later phase here; what this plan owes SC-A is that everything Phases 1 to 3 add travels in the base rather than on a laptop, so nothing new has to be re-entered. Measured by: every context file, rubric, and example this plan adds is a tracked file in the base or in the core plugin, and nothing this plan adds reads seat-local state for meaning.

**SC-C, the base produced work (added in r2, moved to the roadmap by r2.1, kept here as the test the first skill will be held to).** SC-A and SC-B both come from a source the ideation file itself labels an unchecked summary, and neither tests whether the base produced anything. **In scope:** one outbound sequence written by Unit 1.4c from the Gridwise base is used in real outreach, and the record says what was sent, what Brandon changed before sending, and what came back. The line from this to pipeline is the shortest one the product has: sequence, sends, replies, meetings. **Measured by:** a walkthrough record written from the real run, with no estimate in it.

**SC-B, the vacation test.** The work runs when the person is offline. **In scope, once a skill exists:** it runs from context alone with no person carrying context in, which is the doctrine's own test, and a run's output is a proposal a second person can approve. **Out of scope, stated plainly:** no scheduling exists in GTM Base and none is built here. Nothing in this plan makes a run happen without a person starting it, so the vacation test cannot pass in full, and this plan does not claim it does. What it can pass is the half that is a context problem rather than a scheduling problem.

## Scope Boundaries

Carried from both earlier plans, and added to here.

- **No scheduling.** Nothing runs on its own. The vacation test is partially out of reach and the plan says so rather than implying otherwise.
- **No hosted component.** The web app remains its own brainstorm. The review queue moving there is a later phase, one paragraph only.
- **No auto-apply.** The AI proposes; the owner approves. Auto-apply is a later rung earned from a base's record.
- **No company-skills build.** The roadmap's brainstorm produces a requirements document and nothing else. The trust-surface refusal of `CLAUDE.md`, `AGENTS.md`, and `plugins/` in a base stands unchanged until that brainstorm says otherwise.
- **No MCP servers declared** in the plugin manifest, unchanged.
- **Setup stays at two documents.** Everything else a base holds arrives later, on request. The inventory that offers it is in the roadmap, not in this plan.
- **No skills, no runner, no inventory, no new kinds, no update step, no company-skills brainstorm.** All moved to `docs/plans/2026-09-19-002-roadmap-after-phase-1.md` by revision 2.
- **Local approval is not the review queue.** Unit 1.2b approves one staged change on a base with no shared copy. Listing open proposals from a shared copy, reject-but-keep, and the branch hash check stay with the first plan's Unit 8.
- **No redesign of the pre-push gate or the folder link.** Both shipped, both have real-run evidence behind them, and neither is in the path of anything here. Units that touch them touch them only as this plan names.
- **No re-running setup to refresh a complete base**, unchanged from the join plan.
- **No new document parsing.** Markdown, text, and CSV, as today.
- **No changes to the trust-surface check's refusal set**, which is what keeps a cloned base from carrying code onto a seat.

## Context & Research

### Relevant Code and Patterns

Every path below is real and was read for this plan.

- **The shared library**, `plugins/gtm-base/lib/gtmbase/`: `constants.py` holds every folder path, cap, window, and vocabulary the rest shares, including `DECISIONS_DIR`, `REQUIRED_CONTEXT_FILES`, `LEDGER_ORIGINS`, `LEDGER_STATUSES`, `CONFIRMATION_TRIGGERS`, `MARKETING_KINDS`, `DRAFT_RELEVANCE`, `DRAFT_SOURCES_MAX_CHARS`, `CONSENT_NARROW_*`, and `BANNED_GIT_WORDS`. Every unit that adds a vocabulary adds it here, append-only, because two agents editing shared modules concurrently is a recorded lesson.
- **`stale.py`** is pure computation over values handed in: `compute`, `_file_flags`, `_entry_flags`, `_affected_files_proposals`, `_review_by_items`, `_review_items`, `_ledger_behind`, `_line_confirms`. It fetches nothing. The same-run exemption and the confirmation expiry both live here. Units 1.2, 1.4, 1.5 and 1.7 change it; none of them may give it a network call.
- **`base_reader.py`** is the single way a base becomes those values: `read_base`, `context_files`, `ledger`, `confirmations`, `corrections`, `missing_required`, `usable_entries`. Codex verified that it reads every `.md` under `context/` recursively and accepts arbitrary `kind` and `status`, which is why segments and adopted files work on the read side while `drafting.py` rejects them on the write side. Tolerant reading of `work/decisions/` belongs here.
- **`stale_check.py`** turns the report into what a person reads: `first_run_text`, `finding_sentence`, `run`, `build_file_proposal`, `build_affected_files_proposal`, `save_review_by_items`, `_report_the_rest`. The honest baseline finding lands in `first_run_text`.
- **`session_start.py`** is where the base decides what to say: `_daily_block`, `_daily_work`, `_question_text`, `_offer`, `_base_shaped`, `_missing_required`, `render_output`. Quiet by default is mostly a subtraction here.
- **`join_flow.py`** is the setup flow end to end: `survey_sources`, `chosen_places`, `list_sources`, `freeze_sources`, `load_consent`, `narrow`, `preview_step`, `assemble_step`, `review_step`, `approve_step`, `skip_step`, `close_run`, `closing_message`, `write_onboarding_note`. Selection, scope, adoption and the closing question all touch it.
- **`sources.py`** holds the survey and the safe walk: `survey`, `kind_of`, `first_heading`, `counted_kinds`, `place_label`, `list_folder`, `narrow_to_folders`, `listing_digest`, `make_source`, `strip_hidden`, `removed_sentence`, `fence`, `_refuse_fence_markers`, `Consent`, `ConsentList`. Codex established that classification is filename and heading substrings, and that `listing_digest` establishes a file list and not content identity, which is exactly why adoption needs its own byte-bound approval.
- **`drafting.py`** and **`review.py`** are the write side: `order_sources`, `plan_sources`, `assemble`, `parse`, `check_words`, `skipped_text`; and `screen`, `stamp_owner`, `canonical_affects`, `ready_to_write`, `approve`, `skip`. `drafting.parse` enforces the four ICP sections and rejects unknown steps and kinds; `review.approve` writes absent-only after a clean-tree check. New document variants are added explicitly here rather than by weakening validation.
- **`compose_proposal.py`** carries the local-edit path and the section addressing. Codex found the real hazard: local-edit extraction overwrites duplicate heading keys while proposal application chooses the first matching heading, so a second `## Overview` can change the first. That is why the adoption contract requires unambiguous headings.
- **`confirm.py`** is the sole writer of confirmation lines: `answer`, `drafted`, `pending_questions`, `retry_pending`, `_yes`, `_no`, `_not_now`. Drafted mode appends and stages without committing, once per file path, for an untracked or newly staged file only.
- **`machine.py`**, **`paths.py`**, **`state.py`**, **`formats.py`**, **`validate.py`**: account state as the only joined record, `resolve_base` as the sole resolver, seat state, every file shape the plugin reads or writes, and the map settings and owner-email validators.
- **The skills**, `plugins/gtm-base/skills/`: `join/SKILL.md` with `references/closing-rules.md`, `references/reading-rules.md`, and `references/prompts/draft-icp.md`, `draft-positioning.md`, `draft-ledger-entry.md`; `stale-check/SKILL.md` with `references/rules.md`; `propose-change/SKILL.md` with `references/pr-body-rules.md`; `confirm/SKILL.md`, which is not user-invocable and carries the instructions for asking one question. Every sentence a person reads lives in a skill body, a reference file, or a template, and that rule holds for everything added here.
- **The templates**: `plugins/gtm-base/templates/` (`injection.md`, `offer.md`, `base-shaped-question.md`, `continue-setup.md`, `ledger-entry.md`, `confirmation-line.md`, `corrections-file.md`, `proposal-staging.md`, `pending-item.json`, `pr-body.md`), plus the company-base template at `templates/company-base/` and its plugin-side copy at `plugins/gtm-base/templates/company-base/`, which a test holds identical file for file. `context/map.md` in both copies carries `last_confirmed: 2026-01-01`, the placeholder date P12 removes.
- **The tests**: `tests/run.sh` runs `python3 -m unittest discover` with the fakes ahead of the real tools on `PATH`. `tests/support.py` provides `FakeGitRunner`, `Sandbox`, `TempHome`, `make_base`, `commit`, `trust_checkout`, `RecordingGh`, `IndexingGh`, `base_with_a_shared_copy`. `tests/plain_language.py` provides `find_banned`, `find_dashes`, `assert_plain`, today checking only the banned git words from `constants.BANNED_GIT_WORDS` and the two dash characters. There is no `tests/test_plain_language.py`; the lint is asserted from the tests that own each text. Unit 1.8 changes that.
- **`docs/join-guide.md`** is the only user-facing document besides the offer, the closing message, and the invite. **`plugins/gtm-base/CHANGELOG.md`** records each unit as it lands, in plain language, with the real-run evidence that caused it.
- **`brandkit/brand-lock.json`** is the model for the design context file in the roadmap's Unit 2.3. Its top-level keys are `version`, `brand_context` (name, offering, industry, positioning, audience, tone), `concept` (visual premise, research principles, reference preferences, avoid), `visual_axes`, `authoritative_assets` (logo with construction and colour rules, fonts, references), `palette` (primary, accent, neutral, semantic roles, forbidden), and `typography` (display, body, metadata). It is a decided record with a forbidden list, which is the shape a context file wants, and it is not a stylesheet.

### Institutional Learnings

From `tasks/lessons.md`, `plugins/gtm-base/CHANGELOG.md`, and the three real runs.

- **Probe only against a temp home.** Probing a hook wrapper against a real repository path creates the real records folder; point the home override at a temp folder first. (`tasks/lessons.md`, 2026-09-05.)
- **A gate that allows what it cannot parse fails open.** The default is refusal, and the false-refusal rate is accepted. Any new scanning in this plan inherits that posture.
- **Two agents editing shared modules concurrently need explicit file ownership and append-only rules for constants.** This plan gives one unit per agent and names the files each unit owns.
- **macOS caches bytecode**; a stale cache made a correct fix look broken. Clear it before calling a test failure real.
- **A whole-command regex scan must exempt path classes**, or every legitimate push is refused. Decide per class whether a rule applies to commands or only to content.
- **From 0.2.2 and 0.2.3:** a list of files offered for one yes reads as a list about to be copied somewhere unless the sentence says otherwise; one unreadable document must not end a session; a step with nothing left to draft from is refused rather than handed an empty request. All three are wording lessons and all three came from a real run, not a test.
- **From 0.2.5 and 0.2.6:** a yes nobody could read through is not a yes, which is why the narrowing rule exists; and the person least likely to know where their own material sits should not be the one asked to find it, which is why the survey proposes places. Unit 1.6 must not undo either while fixing the double ask.
- **From 0.1.5 and 0.1.3:** a step planned in a skill that does not exist yet writes nothing, and the desktop app renders no session-start hook output on screen. Both are reasons to check a live run rather than a test for anything a person reads.
- **From the three runs:** every defect in Amendment r2.4 was found by a person using the product, and none was found by the 1127 tests. That is the whole justification for the live check before any release that touches setup wording.

### External References

Limited to what this repository already cites, and not re-verified here.

- Claude Code hooks, settings, plugins, skills, and MCP behavior, as recorded under "External References" in `docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md` and `docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md`.
- The AI-native definition block in `~/Personal/CLAUDE.md`: six properties, five kinds of place, five stages, the three arrows back, and the rule that context reads stay local while sources are read through APIs. This plan's sources-of-truth file is the "mapped" property, and its skills are stage 4.
- The parent scope, `~/Obsidian/Vault/Work/GTM-Base/2026-09-04-gtm-base-scope-v1.md`.
- `docs/ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md`, itself a summary of a partly paywalled page by a small model, labeled as such in the document and treated here as direction rather than evidence.

## Key Technical Decisions

| Decision | Rationale | Rejected alternative |
|---|---|---|
| **The rename is a vocabulary change plus a folder move plus a field rename, done in one unit while one base exists.** `constants.DECISIONS_DIR` becomes `work/changes`, `formats` gains the change entry with `kind: change` and the fields `happened_on`, `written_on`, `noted_by`, `source`, `affects`, `review_by`, and every sentence a person reads says "context change". | Doing it later means migrating many bases instead of one, and the word is the thing that confused the designer, so it cannot wait behind nine other units. Doing the folder, the fields, and the words separately would leave three half-renamed states in the tree at once. | A user-facing alias over the old internals (leaves `decisions` in every file name a person can see); deferring the rename until after the second seat. |
| **Migration is performed by the plugin, once, on the base it finds, as a recorded transaction that can always be finished or undone (r2).** A dedicated `changes.py` first checks every entry parses and that no entry id appears in both folders with different content, then writes a transaction record under the plugin's own records folder naming each step, then makes two separate changes: the folder move with no content change, so history follows, and then the field rewrite. The commit point is the second change. A run that finds an unfinished transaction finishes it or puts it back, and it tells its own unfinished work apart from the person's edits by that record, so a half-done migration never blocks its own retry. It records what it did in `corrections/` in a shape `report.py` parses. It refuses on a tree the person has dirtied and reports rather than raising. | Entry ids are the join key for confirmations, corrections, proposals, and the index; changing them would orphan every one of them. Astra's blocker: revision 1 could refuse, let a writer create the new folder, and leave the reader ignoring every old entry; and a failure partway dirtied the tree and blocked the retry. `report.py` finds the change that first added an entry with a log query that does not follow a rename when content changes in the same change, which is why the move and the rewrite are separate. | A script the person runs by hand; renaming ids to match the new vocabulary; one change for move and rewrite; the "migration ordering pattern from `migrate.py`" revision 1 cited, which does not exist (the only `migrate` is a stub in `paths.py`). |
| **Both layouts are read and joined by entry id; only the new one is written (r2).** `base_reader.ledger` reads `work/changes/` and `work/decisions/` together, accepts old and new field names, returns one entry per id, and reports an id that appears twice with different content as a conflict instead of choosing. Every writer writes the new layout only. `report.py` looks under both paths. | A second seat, a stale clone, or a restored backup can present the old layout at any time. Revision 1's "new first, then fall back" reader hid the old entries the moment anything created the new folder. Tolerant reading protects new code reading old data and nothing else: a seat on an older plugin reads a migrated base as empty, which is recorded against release two because one seat exists today. | Refusing the old layout; writing both layouts; reading the new folder first and falling back. |
| **Scope is stored in the umbrella profile's frontmatter as a `covers:` field, validated like any other field, and passed to selection, adoption, and drafting.** | Codex condition E: the map is settings only and its parser ignores free text, so a descriptive scope line there is both a contract break and inert. The profile is the document scope is about, it is owned, and it is confirmed, so scope inherits an owner and a review date for free. Wording alone cannot keep another product line's material out of an adopted file, so the value has to reach selection, not just the prompt. | A line in `context/map.md`; a prompt-only instruction; a separate `context/strategy/scope.md`. |
| **The adoption contract is a per-file manifest, checked in `adopt.py`, and approval is bound to the exact saved bytes.** The manifest names the segment, the authoritative version, and the destination. The checks run in this order: canonicalize the destination and reject unsafe slugs, normalized collisions, symlink parents and trust names; discard the original metadata; run `make_source` so hidden content is removed and counted; then run fence-marker, contact and key screens on what is left; then reject duplicate headings at one level; then write the library-generated frontmatter; then show the cleaned body whole with the removals; then bind the yes to a hash of those bytes. | Every clause answers a verified finding in the Codex verdict's compatibility table: classification by filename establishes neither "finished" nor "one file equals one segment"; fence-marker rejection must run after hidden-content removal; the trust-surface check examines paths, not instructions inside markdown, so adopted content must stay data on later reads; variable destinations need the checks that fixed destinations get from `lexists`; and first-matching-heading addressing makes duplicate headings a correctness problem, not a style problem. | A batch yes over titles and sizes; `listing_digest` as the approval binding; weakening `drafting.parse` to accept anything. |
| **"About to use a document" is detected at skill time, not by watching the filesystem (r2: with an action contract, a measured trial, and a read-hook evaluation).** The flow is detect, prepare a real candidate, pause, get the choice, resume, with the three answers P9 defines. Unit 1.3 also evaluates a hook on the file-read tool that exits at once unless the path is under a joined base's `context/` folder, because revision 1 rejected it for a reason the Bash gate already disproves (it reads every command and exits early), and builds it if Claude Code's documented hook behavior allows it to deliver the flag. Two mechanisms are certain: every core skill that opens a context file calls `moment.check(path)` before it reads, which is a local lookup against the recorded changes and the confirmations; and the session context carries an instruction telling the assistant to run the same check before it uses a context file outside a skill. | This is the honest limit. There is no filesystem watcher, no editor integration, and no way to know what the person is about to type. Inside a skill the check is deterministic and testable. Outside a skill it depends on the assistant following an instruction, which is a real mechanism with a real failure rate, and the plan records it as such rather than claiming coverage it does not have. | A file watcher (nothing to hang it on, and it would fire on reads the person never made); a hook on the Read tool (would fire on every file in every repository, which 0.1.4 already retreated from for the gate); claiming the coverage is complete. |
| **Approving a proposed change locally reuses the proposal's own parts (r2).** Unit 1.2b adds `approve_local.py`. It loads the staged change with `compose_proposal.load_staging`, checks it with `check_edits`, screens it with `scan_everything`, shows it in the four-line form, and on the owner's yes applies it with `apply_edit` to the local base in one commit together with the confirmation and a corrections file built by `corrections_for`. It runs only when the base has no shared copy. | Both reviewers' blocker. It keeps "the AI proposes, a person approves", it does not reorder backup ahead of skills, and it touches neither `push_conditions.py` nor the gate, so nothing new can leave the computer. It is the local half of the first plan's Unit 8 and that unit later adds the shared-copy half beside it. | Giving the Gridwise base a shared copy by hand (every future base is still broken, and the first-backup flag still has no setter); setting `first_push_reviewed` from code (weakens the outgoing-data gate). |
| **The review is a new entry point on the existing stale-check skill, not a new skill.** "Review my base" runs `stale_check.run` in a review mode that walks what is due and what has been proposed as one short list, issues the question ids the hook used to issue, and hosts the quiet-record ask. | The computation, the idempotency rules, the question-id lifecycle, and the proposal path already live there, and the review is the same walk with a different trigger and a different first sentence. A second skill would duplicate all of it and then drift from it. The confirm skill's entry point moves from the injected question to this review and to the moment-of-use flag, and `confirm.pending_questions` already exists for the case where a question is answered outside the turn that issued it. | A new `review-base` skill; leaving the question at session start behind a setting. |
| *(Moved to the roadmap with its unit.)* **The inventory's list of kinds is a constant plus a documented reference.** `constants.BASE_KINDS` holds the ordered list with, for each kind, its destination path, whether it may be adopted, and whether it may be drafted. `plugins/gtm-base/skills/stale-check/references/base-kinds.md` says in plain words what each kind is for and what a good one contains. | A list that lives only in prose cannot be enumerated by the inventory, and a list that lives only in code cannot be read by the person deciding whether they want one. The two are kept in step by a test that asserts every constant has a section and every section a constant, which is the pattern already used for the map settings and the rules reference. | Hard-coding the list in the skill body; deriving it from the template tree (which holds empty folders, not kinds). |
| *(Moved to the roadmap with its unit.)* **The sources-of-truth file is `context/sources-of-truth.md`, one row per kind of data, with where it lives, which connected tool reads it, and the fallback. Nothing reads it over the network at context time.** It is an ordinary context file with an owner, a confirmation, and a review date. | This is the "mapped" property, and the doctrine is explicit that context reads stay local while sources are read through APIs. Making it a context file rather than a skill means it goes stale like everything else and gets caught by the same machinery, which is the whole product. Keeping the network out of context loading keeps session start quiet, offline-safe, and cheap. | A skill that queries each tool for freshness; folding it into `context/map.md` (settings only); a JSON file no person reads. |
| **Skills that use the base are thin runners; the judgment lives in context files; approved examples are a replay the owner reads, and the automated test is a runner contract test (r2).** Revision 1 called the harness "examples as tests", but it asserted which files were read, which is the same for every example, and never looked at the approved output. Each example now carries its own expectations (required claims, segment identity, outcome) and at least one deliberately wrong output that must fail. Rubric starters live in the plugin and enter a base only by an owner-approved request, never through the copied template. What follows is revision 1's row. Each skill reads a named set of context files, applies a rubric that lives in a context file, produces a work product, calls the moment-of-use check first, and ships an `examples/` folder whose owner-approved input and output pairs are executed by a test harness. | Parent scope, verbatim: rubrics live in context files and skills are thin runners, with an examples folder per skill. It is also the only way a company can change the judgment without changing code, which is what "the context improves and the model is swapped" means in the definition. Examples as tests is the MKT1 lifecycle step that applies without a trust model. | Rubrics inside SKILL.md (uneditable by the company, unconfirmable, invisible to staleness); snapshot tests over model output (non-deterministic). |
| *(Moved to the roadmap with its unit.)* **The update step checks the installed version against the marketplace pin and tells the person the one thing to do; it never updates anything itself.** `update_check.py` compares `plugins/gtm-base/.claude-plugin/plugin.json` with what the seat has recorded and prints one sentence. | Plugins do not refresh on their own, which both MKT1 and this repository hit. But the plugin cannot reinstall itself, and a step that silently changed what code runs on a seat would be exactly the thing the trust model exists to prevent. Telling the person the single step is honest and sufficient. | Running the install command on the person's behalf; a background check at session start (breaks quiet by default and needs the network). |
| **Every unit that changes a sentence a person reads gets a live check by Brandon before release.** | Three real runs found nine defects that 1127 tests did not. The tests assert the sentence that was written; only a person discovers that the sentence was the wrong one. | Relying on the plain-language lint alone. |

## Execution Posture

Decided by Brandon on 2026-09-19.

Implementation units are built by Opus 5 agents at high reasoning effort, one unit per agent, together with "Sol" agents. What "Sol" refers to is to be confirmed with Brandon and is recorded here exactly that way; it is not guessed at, and it is listed under Open Questions for Brandon.

Reviews are done by Astra, through the Codex CLI, run from a script file, and by Fable 5.1. Three review points: the plan before any build; a security pass and a correctness pass before each release; and design questions during the build, taken to whichever reviewer fits the question.

The orchestrating session holds this plan and the test suite. It runs `sh tests/run.sh` and the plain-language lint after every unit, and never merges a unit whose test scenarios are not all covered. Units that touch wording a person reads (1.1, 1.1b, 1.2, 1.2b, 1.3, 1.5, 1.6, 1.7a to 1.7d, 1.8) get a live check by Brandon before release, because three real runs found defects no test caught.

**Releases (r2).** Units merge to main as they pass, and nothing reaches an installed seat until the version is bumped, so a merged unit is not a shipped unit. Units 1.1 to 1.5 ship together as release A: a release holding 1.2 without 1.5 would be one in which setup captures no context change at all. Units 1.6 to 1.8 ship as release B, gated by the fidelity replay in 1.9, because that gate is about how setup drafts and nothing in release A makes drafting worse than 0.2.6. This is the default the plan is written to; the alternative, one gated release, is call 4 under "For Brandon". Live checks batch once per release.

**Until the Astra and Fable passes are done on the built code,** the units both reviewers marked riskiest (1.2b, 1.3, 1.4, 1.7c, 1.7d) each get a security pass and a correctness pass before their release, not only the release as a whole.

While the GTM Base plugin is live in a build session, its gate reads every Bash command. Keep git on its own command line, commit with a message file, never name the plugin's records folder or its environment variable on a command line, and run Codex from a script file.

## Open Questions

### Resolved During Planning

- **Where scope lives:** the umbrella profile's frontmatter, as `covers:`, validated and passed to selection, adoption, and drafting. Not the map.
- **Whether the review is a new skill:** no. A new entry point on the stale-check skill, hosting the question ids and the quiet-record ask.
- **Where the weekly nudge setting lives:** seat state, not the map, because it is a per-person preference and the map is what the team shares. The silence window is recorded the same way, as a date the seat is quiet until.
- **How the old ledger layout is handled:** read both, write one. Migration by the plugin, idempotent, recorded in `corrections/`.
- **What the moment-of-use check is:** a skill-time local lookup plus an instruction in the session context, with the instruction's reliability named as a risk rather than assumed away.
- **Whether adoption may take a document with duplicate headings:** no. It is refused with the reason and the offer to draft that segment instead, per Codex's "restrict incompatible heading structures initially".
- **Whether the closing question can confirm its own entry:** no. The entry carries no run id, and each affected document is reconciled separately.
- **How a no gets approved on a base with no shared copy (r2):** locally, inside Claude, by the owner, through Unit 1.2b.
- **What creates the base when segments are adopted (r2):** the umbrella, as the profile does today. Adoption runs after both required files exist.
- **How the map stays unasked (r2):** by its kind, not by a confirmation line.
- **Whether a skill that uses the base may read a source tool:** no. They read context files only. Source reads belong to the sources-of-truth file's own later phase.

### Deferred to Implementation

- The exact wording of the honest baseline finding, which is written in Unit 1.2 and then read aloud by Brandon in the live check before release.
- Whether `_review_items` can be corrected to affected-and-open without changing any currently passing scenario in `tests/test_stale.py`, or whether one existing scenario is genuinely wrong and must be rewritten. Decided by reading the test, not by assumption.
- What a hook on the file-read tool may deliver to the assistant, verified against Claude Code's hook documentation when Unit 1.3 is built, because that decides whether the read hook exists.
- Whether the migration can run inside the session-start hook's budget or must be offered as a step the person accepts. Measured on the one real base before it is wired.
- The slug rules for `context/strategy/segments/<slug>.md` beyond the safety checks: how a segment named in prose becomes a file name that a person recognizes a year later.
- How many examples per skill the harness needs before an example set is meaningful, decided when the first set exists rather than picked now.

### For Brandon

Revision 2 is written to the recommended answer on each call, so the build can start. A different answer changes the named unit and nothing before it. Calls 2, 3, 5 and 7 of revision 1 (design file contents, the list of kinds, atlas figures for skills, the trust-surface question) moved to the roadmap, because both reviewers said they wait for those plans.

| # | The call | Recommended (what r2 assumes) | Runner-up | Needed before |
|---|---|---|---|---|
| 1 | Approving a proposed change inside Claude moves into Phase 1 | Yes, as Unit 1.2b, for a base with no shared copy. Both reviewers call its absence a blocker | Give the Gridwise base a shared copy by hand. Faster, but every base setup creates afterward is still broken | 1.2b is briefed |
| 2 | One skill is pulled forward so the base produces usable work early | **Answered 2026-09-19: no.** Context goes in first, skills after. The runner and the sequence are in the roadmap | | Closed |
| 3 | Who scores the fidelity replay, and on what material | Brandon scores and the builder never does. Case two is built from the real Gridwise material by holding the twelve finished pages out of consent and scoring the drafted segments against those pages as the answer key. Case three lowers the input cap for the replay and says so in the record. A case not run means incomplete | Brandon supplies a second real company with several segments and no finished pages | 1.1 freezes the corpora |
| 4 | One release or two | Two. Release A is 1.1 to 1.5. Release B is selection, segments, and adoption, behind the fidelity gate. One live check per release | One gated release, as Astra recommends. Simpler to reason about, but quiet by default, the rename, and local approval wait behind adoption and the replay | The first version bump |
| 5 | The six UX rulings from Fable H4, recorded in 1.1 | Accept all six: the consent paragraph becomes three short lines plus the question; the per-draft narrowing ask is dropped when the folder choice was explicit; the review shows one line per item with the document on request; the closing reconciles only the two required documents; adoption shows what was removed, the opening lines, and where the whole cleaned file is, with the yes bound to that file's hash; documents and changes get human names instead of paths and ids | Accept five and keep every adopted body shown whole in the conversation, as revision 1 and Amendment r2.4 D say | 1.1 is merged |
| 6 | The bar for the moment-of-use trial, set before it runs | Ten real prompts that each use a flagged document, outside any skill. The flag must fire on at least nine. Below that, the read hook is built if Claude Code allows it, and if it does not, the CHANGELOG and the join guide say plainly that outside a skill the flag is best effort | Record the count and set no bar | 1.3's live check |
| 7 | What "Sol" refers to in "Opus 5 high agents along with Sol agents" | Not guessed at. Units are built by Opus 5 agents at high effort until this is answered | None | Whenever it is answered |
| 8 | Add `~/GTM Bases/` to the home-folder rule in the global CLAUDE.md | Add one line: "`~/GTM Bases/` (one folder per company base created by the GTM Base plugin; product data, not client work)" | Leave the rule alone and treat the folder as plugin-managed | Any time |
| 9 | Exact file names for the context standard | **Decided 2026-09-25: yes.** Your standard's names exactly: `goals.md`, `product.md`, `icps.md`, `buyer-personas.md`, `positioning.md`, `messaging.md`, `voice.md`, `design.md`, `metrics.md`, flat in `context/`, plus `stack.md` for the source map | Keep the `strategy/`, `metrics/`, `plan/` subfolders and use the standard's names inside them | Unit 1.5b is briefed |
| 10 | Competitors | **Decided 2026-09-25: yes.** Fold into `positioning.md`, which your standard says holds the alternatives buyers consider | Keep `competitors.md` as an optional tenth file | Unit 1.5b is briefed |
| 11 | Where segments live | **Decided 2026-09-25: yes.** Under the ICPs: `context/icps.md` is the umbrella and `context/icps/<slug>.md` holds each segment, so a reader sees one idea in one place | Beside them: `context/segments/<slug>.md` | Unit 1.7a is briefed |
| 12 | Lay the base out by CLASS part | **Decided 2026-09-25: yes.** Top-level `context/`, `learning/`, `access/`, `skills/`, `standards/`, plus `work/` for approvals. `stack.md` moves to `access/`, and the change record moves a second time, in the same offered move | Keep `context/` and `work/`, and add only `skills/` and `standards/` | Unit 1.5b is briefed |
| 13 | Skills in the base | **Decided 2026-09-25: yes.** Create `skills/` now and refuse anything in it until the company-skills brainstorm settles who may approve a skill change; that brainstorm runs before the first skill | Leave `skills/` out of the layout until then | Unit 1.5b is briefed |
| 14 | Lessons from results | **Decided 2026-09-25: yes.** Reserve `learning/lessons/` now; the first reporting skill fills it with proposed changes that carry their evidence and need the same approval | Defer entirely | Unit 1.5b is briefed |

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```mermaid
flowchart TB
    subgraph RA[Release A]
        A11[1.1 contract amendments, UX rulings, frozen replay corpora]
        A11b[1.1b UX standard and the lint, added by r2]
        A12[1.2 completion and closing]
        A12b[1.2b approve a proposed change locally, added by r2]
        A13[1.3 quiet by default, r2.5]
        A14[1.4 rename to context change, with migration, r2.5]
        A15[1.5 habit hooks]
    end
    subgraph RB[Release B, behind the fidelity gate]
        A16[1.6 selection fixes]
        A17a[1.7a scope and the segment inventory]
        A17b[1.7b umbrella and segment drafts, the marker state]
        A17c[1.7c guarded adoption]
        A17d[1.7d recovery of an interrupted import]
        A18[1.8 sweep of text no unit touched]
        A19[1.9 fidelity replay: the gate]
    end
    A11 --> A11b --> A12 --> A12b --> A13 --> A14 --> A15
    A15 --> A16 --> A17a --> A17b --> A17c --> A17d --> A18 --> A19
    A11 -. case one replayed against 0.2.6 now .-> A19
```

Codex's six ordered steps are 1.1, 1.2, 1.5, 1.6, 1.7a to 1.7d, and 1.9. Units 1.1b, 1.2b, 1.3, 1.4, and 1.8 are additions Codex's verdict never covered.

### The lifecycle of one context file

Directional guidance. Every state is observable from the file plus the base's own records, and no state is inferred from a modification time.

| State | How it is reached | How it is recognized | What the base does in it |
|---|---|---|---|
| **drafted** | Setup or an inventory draft writes it after a yes | File present, library-written frontmatter, one confirmation line with trigger `drafted` dated today | Counts as complete; the confirmation starts the review clock |
| **adopted** | The adoption contract passes and the owner's yes is bound to the cleaned bytes | File present, frontmatter written by the library with `sources` naming the original path and its date | Identical to drafted for every rule. `status: adopted` carries no freshness meaning of its own |
| **confirmed** | The owner answers yes, inside the review or at the moment of use | A confirmation line whose commit author matches an owner email in the file's frontmatter | Clock restarts; any change the line names is settled for that file |
| **flagged** | A recorded context change affects the file and no owner confirmation settles it | Computed by `stale.compute`, never stored | The moment-of-use flag fires when the file is about to be used; the review lists it; a fix is drafted as a proposal |
| **unanswered marker** | An approved or adopted file carries `[your call: ...]` | Detected by scanning the body, independent of `status` | Not confirmed and not complete. The review lists each marker and asks. Settling one later goes through the proposal path, never a setup overwrite |
| **skipped** | The person skips a document during setup | Present with `status: skipped` and no body | Not complete. The continue-setup path offers to finish it. Never counted in the yes rate |

## Implementation Units

### Phase 1: the correction

Codex's six ordered steps from `docs/reviews/2026-09-19-codex-setup-shape-verdict.md` are Units 1.1, 1.2, 1.5, 1.6, 1.7a to 1.7d, and 1.9, in that order. Units 1.1b, 1.2b, 1.3, 1.4, and 1.8 are additions that verdict never covered, and Amendment r2.5 (quiet by default, the rename) had no outside review before the two plan reviews of 2026-09-19. On the main line no unit starts before the one above it has merged with its scenarios covered.

- [ ] **Unit 1.1: Contract amendments to the documents**

**Goal:** Every written promise matches what is about to be built, before a line of code moves. Nothing in the repository still says setup drafts three documents, or that a base with no recorded change is up to date.

**Requirements:** P1, P2, P4, P5, P6, P7, P12, P17, P18, P19, P21, P23, P27, P28, P29.

**Dependencies:** None. This is the first unit in the phase.

**Files:**
- Modify: `docs/brainstorms/2026-09-05-join-and-onboarding-requirements.md` (J8, J9, J10, J17, SC1, SC3 recorded as amended, each with a one-line pointer to Amendment r2.4), `docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md` (the Overview's three-draft wording, the Key Technical Decisions rows "A base is joined at the first approved file", "Drafting is direct", "The closing finding is computed by", Units 4 and 5), `docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md` (a pointer from Units 3, 9a, 9b and 10 to Amendment r2.5, and a note on r2.5 item 5 that the map is left out by its kind rather than confirmed at creation, per P12), `docs/brainstorms/2026-09-04-current-without-integrations-requirements.md` (origin R22 and R23 recorded as amended by r2.5), the join plan's Amendment r2.4 section C.2 (the quiet-record ask lives inside the review, not the daily block, per P17) and sections D and H (the conflict between "shown whole" and "never paragraphs" resolved by the ruling below), the parent scope's strategy structure at `~/Obsidian/Vault/Work/GTM-Base/2026-09-04-gtm-base-scope-v1.md` (one dated note appended saying the umbrella and `segments/` replace the single profile; it sits outside this repository, so it is appended to and never rewritten), `plugins/gtm-base/skills/join/SKILL.md` (the description, step 1, step 6's fixed order, step 7), `plugins/gtm-base/skills/join/references/closing-rules.md` (the finding order and both closing messages), `docs/join-guide.md` ("What setting up does")
- Create: `docs/plans/2026-09-19-001-acceptance-matrix.md` (one row per state in the file-lifecycle table above, with what setup, the review, the moment-of-use check, and the stale computation each do in that state, followed by a "UX rulings" table with one ruling for each of the six steps Fable H4 lists), `docs/walkthroughs/2026-09-fidelity-replay.md` (created here holding only the frozen bar: the named scorer, the three corpora listed by path and content hash, and the answer key for each: the segments, named deals, figures with units, source versions, and unresolved choices a correct output must keep. Results are added by Unit 1.9 and by nobody else)

**Approach:** Amend in place and record the amendment, never silently rewrite, because both plans are the record of why things are the way they are. Each amended requirement keeps its id and gains an "(amended 2026-09-19, r2.4 section A)" marker. The acceptance matrix is the consistency proof Codex asked for in ordered step 1: it is a table, not prose, and every later Phase 1 unit adds its own row rather than inventing a state.

**Execution note (r2):** The six UX rulings are written to the recommended answers in call 5 under "For Brandon" and marked as awaiting his yes; a different answer is a one-row edit. The corpora are frozen before any behavior unit is built so the build cannot set its own evidence standard (Astra 3). Freezing lists paths and hashes and copies no source text into this repository. Case one is replayed against 0.2.6 as soon as it is frozen, in a session Brandon starts, so a fail is known before 1.7b is built.

**Execution note:** Documents only. This unit writes no code and no test beyond the lint. It is the unit most likely to be rushed and the one whose omissions cause the rest of the phase to contradict itself, so its brief carries the whole Codex verdict, not a summary.

**Patterns to follow:** The existing amendment sections r2.1 to r2.5, which state what was observed, what changed, and where it is implemented, in that order.

**Test scenarios:**
- Lint: no amended text contains a banned git word or a long dash, asserted by `tests/plain_language.py` over each modified user-facing file.
- Happy path: a search of the repository for the phrase "three documents" and for "one decision" in user-facing text returns nothing outside the historical amendment sections.
- Edge case: the acceptance matrix has a row for every state in the lifecycle table and a column for each of setup, review, moment of use, and stale computation, with no cell left empty.
- Edge case (r2): the rulings table has one row for each of the six steps, each naming the unit that carries the ruling out.
- Edge case (r2): the replay record names the scorer, lists three corpora with a hash per file, and states the pass bar, and holds no result.
- Integration: `sh tests/run.sh` still passes unchanged, since no behavior moved.

**Verification:** A reader who has never seen the code can read `plugins/gtm-base/skills/join/SKILL.md` and `references/closing-rules.md` end to end and describe exactly what setup writes and what the closing says, with no contradiction against either plan.

**Atlas: figures 7 and 8.** Figure 7 ("Setting up a base, step by step") loses the third draft; figure 8 ("Confirmations and the stale rules") gains the honest baseline state.

- [ ] **Unit 1.1b: The UX standard and the lint that holds it (added by r2)**

**Goal:** The standard is written down once, the four-line change format exists, documents and changes have human names, and the lint reads the sentences a person actually reads, before any behavior unit writes a sentence.

**Requirements:** P28.

**Dependencies:** 1.1. Moved here from Unit 1.8 by r2 (Fable H2, H3; Astra 10), because revision 1 landed the standard last and rewrote wording Brandon would already have checked live.

**Files:**
- Create: `docs/ux-standard.md` (one page: each step says what it is for in one sentence, shows output readable in seconds, ties it back, asks one thing; the four-line change format; the short interaction wrapper versus the complete artifact a person approves; human names), `plugins/gtm-base/templates/change-four-lines.md` (what changed, why, what it affects, when to look again), `plugins/gtm-base/lib/gtmbase/names.py` (the name a person reads for a context file, "your customer profile" and never `context/strategy/icp.md`, and for a change, its first line and its date and never its id), `tests/test_plain_language.py` (the lint's own tests, which do not exist today), `tests/test_names.py`
- Modify: `tests/plain_language.py` (four new checks beside `find_banned` and `find_dashes`; `PYTHON_SENTENCES`, a registry of every sentence a person reads that is held as a Python string, which today means `stale_check.py` lines 86 to 152, `constants.py` lines 342 to 346, `confirm.py` lines 151 to 159, `join_flow.py` lines 94 to 104, and whatever else the completeness test finds; `EXEMPTIONS`, each entry carrying its reason and the unit that removes it)

**Approach:** Four mechanical checks, because a lint that tries to judge prose fails. One: a step section opens with a sentence saying what the step is for, before any imperative. Two: a step makes exactly one request, counted as one delimited request block that may be a question or an imperative, because P4's required closing wording ("One sentence is enough, or say skip.") has no question mark and revision 1's question-mark count would have rejected it. Three: an interaction block is a short list or a small table, measured by consecutive prose lines over a stated cap, and the complete artifact a person approves (a whole document, a cleaned file) is a separately marked block the cap does not apply to, which is how "shown whole" and "never paragraphs" both hold. Four: a change shown to a person is the four labeled lines. The registry is asserted complete by a test that walks the library's module-level string constants and fails on any sentence-shaped constant that is neither registered nor exempted with a reason. Texts that fail today are not rewritten here: each goes on the exemption list naming the later unit that owns it, each later unit removes its own entries, and Unit 1.8 empties the list. The lint is a floor. The acceptance test for the standard is Brandon reading steps aloud.

**Execution note:** Agents building to a green lint will satisfy "opens with a purpose sentence" with boilerplate. The brief says so, and says the read-aloud check is what the unit is judged by.

**Patterns to follow:** `assert_plain` and how each test file asserts the texts it owns; the test that holds the map settings and their reference in step, as the model for the registry completeness test.

**Test scenarios:**
- Happy path: a fixture step that makes two requests fails; one that makes one passes; P4's exact closing wording passes.
- Happy path: a fixture step that opens with an imperative fails; one that opens with a purpose sentence passes.
- Happy path: a fixture interaction block of six prose lines fails; the same content as a five-row table passes; a whole document inside a marked artifact block passes.
- Happy path: a change shown as a paragraph fails; the same change as four labeled lines passes.
- Edge case: a sentence-shaped constant added to a fixture module and left out of the registry fails the completeness test.
- Edge case: every exemption carries a reason and the unit that removes it; an entry with neither fails.
- Edge case: `names.py` gives a readable name for each of the two required files, for a segment file, and for a change, and never returns a path or an id.
- Edge case: the existing banned-word and dash checks still catch what they caught.
- Integration: `sh tests/run.sh` passes with the lint asserted over every user-facing file in the plugin and over the registry.

**Verification:** Brandon reads `docs/ux-standard.md` and says it is the standard he meant.

**Atlas: none.** No behavior changes.

- [ ] **Unit 1.2: Completion and closing**

**Goal:** Setup completes on two documents, the closing tells the truth about a base with nothing recorded, the map is never asked about, and the source-age finding stops multiplying.

**Requirements:** P1, P2, P3, P12, P22.

**Dependencies:** 1.1.

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py` (`REQUIRED_CONTEXT_FILES` confirmed at two and documented as the completion contract; a new finding code for the honest baseline), `plugins/gtm-base/lib/gtmbase/stale.py` (`first_run_finding` gains the baseline state and loses the "no date to watch" claim; `_review_items` restricted to files the entry affects and to open entries), `plugins/gtm-base/lib/gtmbase/stale_check.py` (`first_run_text`, `finding_sentence`), `plugins/gtm-base/lib/gtmbase/session_start.py` (`_missing_required` and the continue-setup branch stop expecting an entry), `plugins/gtm-base/lib/gtmbase/join_flow.py` (`close_run`, `closing_message`), `plugins/gtm-base/skills/join/references/closing-rules.md`, `templates/company-base/context/map.md` and `plugins/gtm-base/templates/company-base/context/map.md` (placeholder date removed), `plugins/gtm-base/lib/gtmbase/stale.py` and `stale_check.py` again (a file whose kind is the map is left out of flags, questions, and the review)
- Test: `tests/test_stale.py`, `tests/test_stale_check.py`, `tests/test_session_start.py`, `tests/test_join_setup_flow.py`, `tests/test_scaffold.py` (the two template copies stay identical)

**Approach:** The baseline finding is a new state in the existing fixed order, not a new code path: skipped file first, then an unanswered marker, then a source older than an affecting change, then the baseline, then nothing-out-of-date. The map is left out of questions and reviews by its kind (r2, Fable M4): a confirmation line would make it come due again after the threshold, and leaving it out also covers the base that was created before this unit. `_review_items` today only considers entries whose run id matches the run on a drafted line (`stale.py`, around line 869), and Unit 1.5 writes closing entries with no run id, so the finding is rekeyed here (r2, Fable H6): a drafted line on the file, an open entry that affects the file, and source material dated before the change happened. It compares only against entries that both affect the file and are open; the currently passing scenarios are read first and any scenario that only passed because of the wider comparison is rewritten with its reason recorded in the test.

**Patterns to follow:** The deterministic finding order already in `closing-rules.md`; the rule that the finding is recomputed and never cached.

**Test scenarios:**
- Happy path: two confirmed files, no entries: the finding states both were confirmed today, that no context change is recorded, that the base cannot yet check whether a change made either document out of date, and names the review date for each confirmation. It does not say nothing is out of date and does not say there is no date to watch.
- Happy path (P3): the first feature's SC1 scenario, a hand-entered change affecting `context/strategy/icp.md` with no confirmation, still produces one flag and one staged proposal, unchanged.
- Edge case: positioning skipped: the finding names the skipped file and nothing else changes.
- Edge case: a file carrying an unanswered `[your call: ...]` marker outranks the baseline in the finding order. (The marker detection itself lands in 1.7; this unit asserts the ordering slot exists and is empty until then.)
- Edge case: twelve context files and one open change affecting two of them: `_review_items` returns items for those two only; the other ten produce nothing.
- Edge case (r2, replaces a scenario the date comparison already passed): a closed change newer than the file's sources produces no review item, and the same change left open produces one.
- Edge case (r2): an entry with no run id that affects a file with a drafted line and older sources still produces the review item.
- Edge case (r2): setup resumed on a later day, so the two confirmations carry different dates: the baseline finding names each date correctly, and a second seat reading the same base computes the same finding.
- Error path: the map has no confirmation line, in a new base and in one created before this unit: it is never asked about, never listed in the review, and never flagged.
- Integration: a full setup run through `tests/test_join_setup_flow.py` ends with two files, two drafted confirmation lines, no line for the map, and the baseline finding.

**Verification:** A real setup run that approves both documents and records nothing else ends with a sentence Brandon reads aloud and agrees is true of that base.

**Atlas: figures 5, 7, 8.**

- [ ] **Unit 1.2b: Approve a proposed change locally (added by r2)**

**Goal:** On a base with no shared copy, a prepared change can be read, approved by its owner inside Claude, and applied, so every "no becomes a proposed change" has somewhere to end.

**Requirements:** P36, P13, P28.

**Dependencies:** 1.2, 1.1b. Both reviewers' blocker (Astra 2, Fable B1). Verified on 2026-09-19: `compose_proposal.py` around line 660 refuses a base with no shared copy; the Gridwise base has none; `push_conditions.py` refuses while `first_push_reviewed` is false, `create_base.py` sets it false, and only tests ever set it true.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/approve_local.py`, `plugins/gtm-base/skills/propose-change/scripts/approve_local.py` (a shim), `plugins/gtm-base/skills/propose-change/references/local-approval-rules.md`, `tests/test_approve_local.py`
- Modify: `plugins/gtm-base/lib/gtmbase/compose_proposal.py` (on a base with no shared copy the refusal becomes a handoff: the staged change is kept and the result says it can be approved here), `plugins/gtm-base/skills/propose-change/SKILL.md`, `plugins/gtm-base/lib/gtmbase/stale_check.py` and `plugins/gtm-base/skills/stale-check/SKILL.md` (prepared changes awaiting approval are listed), `plugins/gtm-base/lib/gtmbase/report.py` (a locally approved change counts exactly as a merged one)
- Test: `tests/test_compose_proposal.py`, `tests/test_stale_check.py`, `tests/test_report.py`
- Not touched, and a test says so: `push_conditions.py`, `gate.py`, and the seat's `first_push_reviewed` value.

**Approach:** It runs only when the base has no shared copy; with one, the shipped path is unchanged and this unit refuses and points at it. The steps, in order: load the staged change with `load_staging`; check it still fits the files with `check_edits`, and on a conflict say so and offer to prepare it again; run `scan_everything`, the same screens an outgoing proposal gets, because a local base becomes the shared copy at the first backup; show the change in the four-line form with the before and after of each edited section as the complete artifact; ask one thing (approve, not yet, or drop it). The yes is bound to `content_hash_for` the staged content, so a staged change that moved between the showing and the yes is asked about again. Only an owner of each edited file may approve, by the same author-email rule confirmations use, and anyone else is told who owns it. On a yes, one commit on the base holds the edited files through `apply_edit`, the change entry when the staging carries one, the confirmation line (an owner accepting a proposal is the owner's confirmation, decided 2026-09-06), and a corrections file built by `corrections_for` that `report.py` parses. The tree must be clean first. The staging copy is retired last. Listing open proposals from a shared copy, reject-but-keep, and the branch hash check stay with the first plan's Unit 8, which later adds that half beside this one.

**Execution note:** Do not make this work by loosening anything about what may leave the computer. If a step seems to need `first_push_reviewed` set, the design is wrong.

**Patterns to follow:** "Approve exactly what the reviewer saw" from the first plan's Unit 8; the absent-only, clean-tree write in `review.approve`; the partial-then-commit point from `create_base.py`.

**Test scenarios:**
- Happy path: on a base built by `create_base` with no shared copy and no fake standing in for one, a no inside the review produces a staged change; it is shown in four lines, approved, and applied; the file changed, one confirmation line names the change, one corrections file parses and is counted by `report.py`, there is one commit, and the staging copy is gone.
- Happy path: "not yet" leaves the staged change and the flag as they were; "drop it" retires the staged change and leaves the file flagged.
- Edge case: the staged content changes between the showing and the yes: nothing is applied and the person is asked again.
- Edge case: the file changed on disk since the change was prepared: reported, with the offer to prepare it again, and nothing applied.
- Error path: a tree the person has dirtied: one sentence, nothing written.
- Error path: a failure injected after the file write, after staging, after the confirmation line, and after the commit: every retry ends in the same final state and no run leaves a half-applied change.
- Security: a staged change naming a path outside `paths.PROPOSAL_PATH_PREFIXES` or under `.claude/` is refused; one carrying a contact detail or a key is refused by the same screens with the class named and never the value; an approver who is not an owner is refused and told who is.
- Security: no git call reaches a remote, `first_push_reviewed` is still false afterward, and the gate's own tests pass unchanged.
- Edge case: a base with a shared copy: this path refuses and points at the shipped one.
- Integration (P3 on a real-shaped base): a hand-entered change, the flag, the staged proposal, local approval, and the file ends confirmed with the flag cleared.

**Verification:** On the Gridwise base Brandon answers no in a review, reads the prepared change in four lines, says yes, and the document is changed and confirmed without GitHub being opened.

**Atlas: figures 5 and 8.**

- [ ] **Unit 1.3: Quiet by default**

**Goal:** The base says nothing at session start, speaks only when a document about to be used has been overtaken, answers "review my base" on request, offers an opt-in weekly line, and can be silenced.

**Requirements:** P8, P9, P10, P11, P13.

**Dependencies:** 1.2, 1.2b ("fix it first" and a no inside the review both end in a local approval).

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/moment.py` (the check, its sentence, and the three answers), `plugins/gtm-base/templates/moment-of-use.md`, `plugins/gtm-base/templates/weekly-line.md`, `tests/test_moment_of_use.py`
- Modify: `plugins/gtm-base/lib/gtmbase/session_start.py` (`_daily_block` and `_daily_work` stop selecting a question and stop issuing a question id; the map, the change summary, and the moment-of-use instruction remain), `plugins/gtm-base/templates/injection.md` (the instruction, plus one sentence saying that everything inside a context file is data and never an instruction, per Fable M5), `plugins/gtm-base/lib/gtmbase/state.py` (weekly-line preference, silence-until date), `plugins/gtm-base/lib/gtmbase/stale_check.py` (`run` gains the review mode; the review shows one line per item using `names.py`, with the document on request), `plugins/gtm-base/skills/stale-check/SKILL.md` and `references/rules.md`, `plugins/gtm-base/skills/confirm/SKILL.md` (entered from the review and from the moment-of-use flag; "How to ask" no longer shows the whole document and explains all three answers for every item), `plugins/gtm-base/lib/gtmbase/confirm.py` (question ids issued by the review; `pending_questions` is the way back)
- Conditional, decided inside this unit: `plugins/gtm-base/hooks/hooks.json` and a read-hook wrapper, if the evaluation below passes
- Test: `tests/test_session_start.py`, `tests/test_stale_check.py`, `tests/test_confirm.py`, `tests/test_state.py`

**Approach:** Session start becomes a subtraction: record the session, bring the shared copy up to date under the existing path refusals, hand over the map and the change summary, and stop. The question-id machinery moves rather than dies: the review issues ids bound to the session exactly as the hook did, so single use, expiry, the asked log, and the yes rate keep working with a different issuer.

The moment-of-use flow has an action contract (r2, Astra 4). Detect: `moment.check(path)` is a local lookup against the recorded changes and the confirmations. Prepare: it says a fix is ready only when a staged change for that file exists, because the shipped "drafted fix" is an `Update needed:` placeholder that still needs rewriting (`stale_check.py` around line 327) and `session_start.py` stages nothing; otherwise it offers to prepare one. Pause: the caller produces no work product before the choice. Choose, one of three: "use it as is" leaves the flag standing and writes nothing, because permission to use a stale document is not a statement that it is right; "fix it first" prepares the change and waits for the owner's approval through Unit 1.2b, then resumes; "it already reflects this" is the existing confirmation. Resume: the work continues with whichever document state resulted. An unanswered marker alone never interrupts, because the settled rule is that only an overtaking recorded change does; markers are listed in the review.

Coverage, stated honestly. The Phase 1 skills that hand a context file to the model (stale-check while improving a prepared change, propose-change, confirm) call `moment.check` before they do, and each is tested at its real entry point. Outside a skill the flag rests on the injected instruction, so this unit also does two things revision 1 did not. It evaluates a hook on the file-read tool that exits at once unless the path is under a joined base's `context/` folder; revision 1 rejected this because it "would fire on every file in every repository", but the Bash gate already reads every command and exits early, so the rejection needs a measurement, not an assumption. What such a hook may deliver to the assistant is verified against Claude Code's hook documentation at build time, and it is built only if it can deliver the flag. And the live check is a measured trial with the bar set beforehand (call 6 under "For Brandon"), with the count recorded in the CHANGELOG.

**Execution note:** Write the injected instruction as a hard rule in the same shape the reader agents use. Record in the CHANGELOG exactly what was measured, and nothing that was not.

**Patterns to follow:** The hook posture (always exit 0, fixed sentences, never a stack trace); the existing question-id lifecycle in `confirm.py`; the gate's early exit as the model for a cheap hook.

**Test scenarios:**
- Happy path: session start on a joined base with two overdue files: the map and the change summary are injected, no question text appears, no question id is issued, and the asked log is unchanged.
- Happy path: `moment.check` on a file affected by an open change returns the four lines and the change's date; with a staged change present it says a fix is ready; with none it offers to prepare one and never claims one exists.
- Happy path: "use it as is" writes no confirmation line and the file is still flagged on the next check.
- Happy path: "it already reflects this" writes one confirmation line naming the change.
- Happy path: "fix it first" prepares a change, and the work does not resume until Unit 1.2b has applied it or the person chose otherwise.
- Edge case: a file with an unanswered marker and no overtaking change: `moment.check` returns nothing; the review lists the marker.
- Edge case (r2): at each real entry point (the stale-check improvement step, propose-change, confirm), no context file is handed to the model before `moment.check` ran for it, asserted on the rendered input and not on a fixture that calls the check voluntarily.
- Happy path: "review my base" lists what is due and what has been proposed as one line per item with readable names, issues one question id per item asked, and records outcomes in the asked log exactly as the hook did.
- Edge case: a no inside the review becomes a prepared change that Unit 1.2b can apply, and a not now writes a suppression.
- Edge case: the weekly line is off by default; once on it appears once in a week and not twice; after a month's silence is set nothing appears until the date passes or the person asks.
- Security: `moment.check` imports and calls nothing that can reach a network, asserted by failing on any use of the git runner's remote-capable commands and of the network modules, not only on a fetch.
- Security: a context file holding an instruction sentence reaches the model inside the data fence on every path this unit touches.
- Error path: a base whose records cannot be read: the check returns nothing and records a code; it never guesses.
- Conditional: if the read hook is built, it exits at once for a path outside a joined base's `context/` folder, delivers the flag for a flagged file inside one, and always exits 0.

**Verification:** Brandon opens `~/Gridwise` and gets a working session with no question in it, asks "review my base" and walks the list in one sitting, and then runs the measured trial: the agreed number of real prompts that each use a flagged document, with the count of times the flag fired written down.

**Atlas: figures 2 and 5.**

- [ ] **Unit 1.4: The rename to context change, with a recoverable migration and both layouts read**

**Goal:** One word everywhere a person reads, one folder name and one set of field names inside, the existing base migrated without any moment at which an entry is hidden or a retry is blocked, and the old layout still read.

**Requirements:** P14, P15, P3.

**Dependencies:** 1.3.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/changes.py` (the migration transaction and its recovery), `tests/test_changes_migration.py`
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py` (`DECISIONS_DIR` becomes `work/changes`; the old value kept as a read-only constant; `LEDGER_ORIGINS` and `LEDGER_STATUSES` keep their values and gain the `change` kind; "decision" as the name of what the base tracks, and "ledger", join the words banned from text a person reads), `plugins/gtm-base/lib/gtmbase/formats.py` (the change entry, reading both spellings of every field, writing one; today's parser around line 415 requires the old fields and kind), `plugins/gtm-base/lib/gtmbase/base_reader.py` (`ledger` today enumerates one directory, around line 195; it reads both folders, joins by entry id, and reports an id that appears twice with different content as a conflict), `plugins/gtm-base/lib/gtmbase/paths.py` (`PROPOSAL_PATH_PREFIXES`, lines 27 to 31, accepts both folders, or a staged or kept proposal naming the old path is refused after the rename), `plugins/gtm-base/lib/gtmbase/report.py` (line 113 and the first-added query at lines 72 to 80 look under both paths), `plugins/gtm-base/lib/gtmbase/stale.py` and `stale_check.py` (vocabulary in every sentence, including the "ledger" sentences at `stale_check.py` lines 110 to 121 and the person-facing name of `--dismiss-ledger-behind`), `session_start.py`, `join_flow.py`, `compose_proposal.py`, `confirm.py`, `review.py`, `approve_local.py`, `plugins/gtm-base/templates/ledger-entry.md` (renamed `change-entry.md`), `injection.md`, `proposal-staging.md`, `pr-body.md`, `templates/corrections-file.md` (line 11), both `CODEOWNERS` templates, `plugins/gtm-base/skills/*/SKILL.md` and every `references/*.md`, `plugins/gtm-base/skills/join/references/prompts/draft-ledger-entry.md` (renamed `draft-change-entry.md`), `templates/company-base/` and `plugins/gtm-base/templates/company-base/` (`work/decisions/` becomes `work/changes/`, and the map's "where things live" paragraph), `docs/join-guide.md`
- Test: `tests/test_formats.py`, `tests/test_base_reader.py`, `tests/test_stale.py`, `tests/test_stale_check.py`, `tests/test_compose_proposal.py`, `tests/test_confirm.py`, `tests/test_join_setup_flow.py`, `tests/test_scaffold.py`, `tests/test_create_base.py`, `tests/test_paths.py`, `tests/test_report.py`, `tests/test_review.py`, `tests/test_trust_surface.py`, `tests/test_plain_language.py`, `tests/fixtures/ledger-entry.md` and `tests/fixtures/drafts/ledger-entry.md` (kept as old-layout fixtures and joined by new-layout ones)

**Approach:** Three renames land in one unit, because splitting them leaves the tree half-renamed: the folder, the fields, and the words. Entry ids are untouched. What r2 changes is how the base gets from one layout to the other (Astra 1, Fable H8).

The reader comes first. `base_reader.ledger` reads both folders and joins by id, so there is no state in which an old entry is hidden, whatever the migration did or did not do. Then `changes.migrate`, in this order: check that every entry parses and that no id exists in both folders with different content, and refuse with a report if not; refuse on a tree the person has dirtied; write a transaction record under the plugin's own records folder naming each step; make change one, the folder move with no content change, so git follows the history; make change two, the field rewrite, which is the commit point; write the dated corrections file in a shape `CorrectionsFile` parses (entry id, staging id, content hash, correction class), or `report.py` skips or miscounts it; close the transaction record. A later run that finds an open transaction finishes it or puts it back, and it knows its own unfinished work from the person's edits by that record, so a half-done migration never blocks its own retry. A base holding both folders with no conflicting ids is migrated by moving what is still in the old one, not refused. `decided_by` becomes `noted_by` as Amendment r2.5 says, and every line a person reads says who noted the change. The user-facing wording is written to `docs/ux-standard.md` and this unit removes its own entries from the lint's exemption list.

**Execution note:** This unit touches more files than any other and owns all of them for its duration; nothing on the main line runs beside it. Whether the migration runs inside the session-start budget or is offered as a step the person accepts is measured on the real base before it is wired. One seat exists today. An older plugin reading a migrated base sees it as empty, which is recorded against release two as a condition of inviting a second seat: every seat updates before a base migrates.

**Patterns to follow:** The append-only rule for `constants.py`; the partial-folder-then-rename commit point in `create_base.py` and the transactional registry in `machine.py`, which are the real patterns (revision 1 cited a `migrate.py` that does not exist; the only `migrate` is a stub in `paths.py` lines 510 to 519 that raises).

**Test scenarios:**
- Happy path: a base holding `work/decisions/` with three entries migrates to `work/changes/` in two changes, keeps all three ids, rewrites the field names, records one corrections file that `report.py` parses, and closes its transaction. Running it again changes nothing.
- Happy path: a base already holding `work/changes/` is read normally and the migration does nothing.
- Error path (r2): a failure injected after each mutation in turn (the transaction record, the move, the rewrite, the corrections file): every retry finishes or puts back, and bodies, ids, confirmations, and computed flags are identical to an uninterrupted run.
- Edge case (r2): both folders hold different entries: the reader returns all of them, and the migration moves the old ones.
- Edge case (r2): both folders hold the same id with different content: the reader reports the conflict and chooses neither; the migration refuses and names the id.
- Edge case (r2): the migration refuses on an old-layout base, a writer then creates `work/changes/` with a new entry, and the reader still returns the old entries beside it.
- Edge case: an entry written with old field names inside the new folder is read correctly.
- Error path: a tree the person dirtied: one sentence, nothing written; a tree dirtied only by this migration's own open transaction: recovery runs.
- Edge case: a confirmation line naming an entry id survives the migration and still settles that entry for its file.
- Edge case (r2): the "catches" number from `report.py` is the same before and after the migration on a base with recorded catches.
- Edge case (r2): a staged proposal that names `work/decisions/` is still accepted after the rename.
- Edge case (r2, recorded and not fixed): the 0.2.6 parser reading a migrated base is asserted to see no entries, so the known limit is a test and not a surprise.
- P3 (r2): the old-layout SC1 test stays byte-identical and passes; a new-layout twin is added beside it.
- Lint: no text a person reads contains "decision" as the name of what the base tracks, or "ledger"; "context change" appears before the short form "change" in every text.
- Integration: a full setup run, a local edit, a review, and a local approval all work end to end on a migrated base.

**Verification:** The one real base at `~/GTM Bases/Gridwise/gtm-base` migrates in a live run, keeps its entry id, and its next review reads identically to the one before. Scale, for honesty: that base holds one entry, no corrections, and no proposals.

**Atlas: figures 1 and 8.**

- [ ] **Unit 1.5: Habit hooks**

**Goal:** The base learns about context changes at the two moments a person actually has one to give: when they have edited a file by hand, and at the closing of setup. Neither moment confirms itself.

**Requirements:** P4, P5, P6, P7, P16, P17.

**Dependencies:** 1.4, and 1.2b for every path that ends in an approved change.

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/compose_proposal.py` (the local-edit path asks one thing, "What changed, and why?", in one request block; a strategic answer becomes the proposal's change entry, and `decision_block=None` stops being unconditional), `plugins/gtm-base/skills/propose-change/SKILL.md` (the two questions and the four-line display), `plugins/gtm-base/lib/gtmbase/join_flow.py` (`close_run` asks the optional closing question and runs per-document reconciliation), `plugins/gtm-base/skills/join/SKILL.md` (step 7), `plugins/gtm-base/skills/join/references/closing-rules.md` (the three explaining sentences, the example, the exact question), `plugins/gtm-base/lib/gtmbase/review.py` (`stamp_entry` writes a closing entry with no run id), `plugins/gtm-base/lib/gtmbase/stale.py` (`_ledger_behind`: an empty record is behind immediately; the dismissal window and its expiry), `plugins/gtm-base/lib/gtmbase/stale_check.py` (the quiet-record ask lives in the review), `plugins/gtm-base/lib/gtmbase/confirm.py` (a confirmation that names a closing change), `plugins/gtm-base/templates/change-entry.md`
- Test: `tests/test_compose_proposal.py`, `tests/test_join_setup_flow.py`, `tests/test_stale.py`, `tests/test_stale_check.py`, `tests/test_confirm.py`, `tests/test_review.py`

**Approach:** The closing question is asked once, after the three plain sentences and the example. A sentence becomes a proposed entry shown whole, as four short lines plus the date, the person who decided, the affected documents, and the review date, each correctable. It carries no run id. Then, for each of the two required documents the change affects, separately, the person is asked whether that document already reflects the change (r2, Fable H4: with segments "affects" can name twelve files, so any other affected document is left flagged for the review and the closing says how many): a yes writes a confirmation naming the change, a no leaves the document flagged and hands the fix to the proposal path. Skip writes nothing, dismisses the quiet-record reminder for the confirmation threshold (30 days unless the map sets another, the window `stale_check.run` already uses), and is recorded outside the yes-rate denominator. On the local-edit path the one request, what changed and why, is made once, on top of the existing "where did this come from"; a typo answer records no change and the proposal proceeds unchanged, which is the case that must keep working.

**Execution note:** Codex's condition C is that these hooks are built before they are presented as the replacement habit. The unit is not done when the code exists; it is done when the closing and the local-edit path have both been run live.

**Patterns to follow:** The existing review loop (approve, edit, skip, what is wrong) for the entry preview; the four-line display from P28.

**Test scenarios:**
- Happy path: a closing sentence produces a proposed entry shown whole; correcting the date changes the entry; approving writes it to `work/changes/` with no run id.
- Happy path: an entry affecting both documents asks twice, once per document; a yes on the profile writes a confirmation naming the change, a no on the positioning leaves it flagged and produces one staged proposal.
- Edge case (the case Codex named): the approved profile targets small fleets and the closing sentence says the company stopped selling to small fleets. The earlier same-run confirmation does not settle it, the reconciliation question is asked, and a no flags the file.
- Edge case: skip writes nothing, dismisses the quiet-record reminder for the stated window, and does not appear in the yes-rate denominator; `tests/test_report.py` confirms the denominator is unchanged.
- Edge case (r2, replaces a scenario `stale.py` already passed): after a dismissal the quiet-record ask is silent until the threshold passes, then returns once, inside the review only.
- Edge case (r2): an entry affecting the two required documents and ten segment files asks twice at the closing, leaves the ten flagged, and says so in one line.
- Happy path: a local edit with a strategic answer produces a proposal carrying a change entry with the stated source; the same edit with a typo answer produces a proposal with no entry and the edit intact.
- Error path: a refused proposal leaves the person's own edit and the stated source in place, unchanged.
- Edge case: the quiet-record ask happens at most once a session and only inside the review, never at session start.
- Integration (r2): on a base with no shared copy, built the way `create_base` really builds one and with no fake standing in for a remote: setup, closing sentence, reconciliation no, staged change, local approval through Unit 1.2b, and the affected file ends changed and confirmed against that change.

**Verification:** Brandon runs a setup closing live and, separately, hand-edits a context file and raises it, and in both cases the base ends holding a change entry he recognizes as his own sentence.

**Atlas: figures 5 and 8.**

- [ ] **Unit 1.5b: The base is laid out by the five CLASS parts (added by r2.2, widened by r2.3)**

**Goal:** A base has one top-level folder for each CLASS part, so anyone who read the article can open a base and see the framework in its folder names; its context folder follows Brandon's published context standard; and the move happens while one real base exists.

**Requirements:** P38, P14, P15, P28.

**Dependencies:** 0.3.0 shipped, and the live check done, so any fix it finds lands first. Before 1.6, because Release B writes segments and adoption into these paths.

**Source:** the CLASS framework in `~/Obsidian/Vault/Work/Newsletter/MICW-04-ai-native-definition-v10.md` (Context, Learning, Access, Skills, Standard) and its context standard in `MICW-04-marketing-context-standard.md`: nine Markdown files in `context/`, each with an owner, an approval status, a last verification date, and authoritative sources; a short source map in `context/stack.md`; stable meaning in the files and changing values in the tools that own them.

**The layout, as Brandon decided it on 2026-09-25 (calls 9 to 14):**

| Part | Folder | Holds | Today |
|---|---|---|---|
| Context | `context/goals.md` | objectives, horizons, priorities, constraints, and where the targets live; never the targets | roadmap `context/plan/goals.md` |
| Context | `context/product.md` | what is sold, what it can deliver, limitations, shipped versus planned, where pricing lives | none |
| Context | `context/icps.md` | the umbrella: which companies fit and which do not, one short paragraph per segment | `context/strategy/icp.md` |
| Context | `context/icps/<slug>.md` | one segment at full depth (Release B, Unit 1.7) | planned `context/strategy/segments/<slug>.md` |
| Context | `context/buyer-personas.md` | the people in the purchase, their needs, objections, criteria, and roles | roadmap `context/strategy/personas/` |
| Context | `context/positioning.md` | category, alternatives buyers consider, differentiated value, evidence | `context/strategy/positioning.md`; roadmap `competitors.md` folds in here |
| Context | `context/messaging.md`, `voice.md`, `design.md` | as the standard says | roadmap, under `context/strategy/` |
| Context | `context/metrics.md` | funnel stages, qualified opportunity, attribution, formulas, caveats; never target values | roadmap `context/metrics/definitions.md` |
| Context | `context/map.md` | settings only, unchanged in meaning | unchanged |
| Learning | `learning/changes/` | each recorded context change | `work/changes/` (and the older `work/decisions/`) |
| Learning | `learning/corrections/` | what each approved fix changed, and why | `corrections/` |
| Learning | `learning/lessons/` | lessons from results, proposed by a reporting skill with the evidence attached and accepted like any change; reserved now, empty until the first reporting skill (call 14) | none |
| Access | `access/stack.md` | the source map: for each kind of data, work in flight, and notes, where it lives and which connected tool reads it; for each kind of output, where it is written; what is missing. Never a credential. | `context/map.md`'s "where things live" paragraph plus roadmap `sources-of-truth.md` |
| Skills | `skills/<job>/` | one folder per recurring job: the procedure and its approved examples. Created empty; the plugin refuses any file in it until the company-skills brainstorm settles who may approve a skill change (call 13) | none |
| Standard | `standards/<job>.md` | a job's goal, what is unacceptable, what needs approval, and the checks run before work is handed back | roadmap per-skill rubric files |
| Approvals | `work/proposals/`, `work/confirmations/`, `work/inbox/` | the machinery behind the approval half of Standard: prepared changes, who said yes, and what never leaves the computer | unchanged |

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py` (the path constants and `REQUIRED_CONTEXT_FILES`, which becomes `context/icps.md` and `context/positioning.md`; old paths kept as read-only constants), `base_reader.py` and `names.py` (both layouts read; names for every new kind), `drafting.py` and the join skill and prompts (setup writes the new paths), `changes.py` (a second recoverable move, reusing the Unit 1.4 transaction pattern: offered, never automatic, read back before anything is written; it moves the context files, `work/changes/` or `work/decisions/` into `learning/changes/`, and `corrections/` into `learning/corrections/`, in one offered move), `trust_surface.py`, `gate.py`, `write_hook.py`, and the session-start pull refusals (anything under `skills/` is refused, the same way `plugins/` is today, until the trust model exists), `report.py` (catches read from `learning/corrections/` and the old path), `stale.py`, `stale_check.py`, `moment.py`, `read_hook.py`, `write_hook.py` (any path they name), both company-base templates, `docs/join-guide.md`, `docs/ux-standard.md` (the draft four questions replaced by CLASS, as the framework every step ties back to), the atlas figure 1.
- Modify: `docs/plans/2026-09-19-002-roadmap-after-phase-1.md` (every kind renamed to the standard; `competitors.md` removed; Standard added as a kind; the inventory's list of kinds is the nine files, `access/stack.md`, and `standards/`; the company-skills brainstorm is scheduled before the first skill and must settle who may approve a change under `skills/`).
- Test: new `tests/test_context_standard.py`, plus the tests that name old paths.

**Approach:** Read both layouts and write one, exactly as Unit 1.4 did for the change folder. The move is a pure rename in one saved change, then any front-matter the new kinds need in a second, with the note, recovery, and read-back rules Astra's reviews hardened. A base still on the old layout is read correctly and offered the move in "review my base". `product.md` and the other new kinds are not drafted at setup: setup stays at two documents, and the inventory in the next plan offers the rest.

**Execution note:** Reuse `changes.py`'s transaction and recovery code rather than writing a second one; if it cannot be reused cleanly, extract it first as its own small change with its own tests. The live Gridwise base is moved only by Brandon, through the offer.

**Test scenarios:**
- Happy path: a base on the old layout reads identically before the move, is offered it, moves in two saved changes, and reads identically after; every confirmation still settles its file.
- Happy path: setup on a fresh folder writes `context/icps.md` and `context/positioning.md`, and the closing, the review, and the moment-of-use check name them in plain words.
- Error path: a stop injected after each step of the move finishes or puts back, with the same bytes, index, and flags as an uninterrupted run.
- Edge case: a file already present at a new path with different content is a named refusal, never an overwrite.
- Edge case (r2.3): the change record moves from `work/changes/` or `work/decisions/` into `learning/changes/` and keeps every entry id; the reader returns every entry from all three folders during and after the move; the report counts catches the same before and after.
- Security (r2.3): any file under `skills/`, arriving by a pull, a local write, or the file-writing tools, is refused with one sentence, exactly as a file under `plugins/` is; the empty folder and its placeholder are allowed.
- Happy path (r2.3): `access/stack.md` holds no credential, and a line shaped like a key or a token is refused by the same screens a proposal gets.
- Edge case: a hand edit, a local approval, and the read hook on a moved base all work; a staged change naming an old path is still accepted.
- Lint: no text a person reads names an old path.

**Verification:** The Gridwise base moves in a live run through the offer, and its next review reads identically to the one before.

**Atlas: figures 1 and 7.**

- [ ] **Unit 1.6: Selection fixes**

**Goal:** The survey proposes the right places, an explicit choice is honored once, versions are ordered deterministically with conflicts said out loud, and the preview says why.

**Requirements:** P24, P25, P26.

**Dependencies:** 1.5.

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/sources.py` (`survey` and `kind_of`: plans and metrics count only beside a profile, persona, or positioning file; `Place` gains what the folder mostly holds, from paths only; per-file candidates in the survey output; same-stem version grouping by name, with "final" outranking a newer date. r2, Astra 9: the survey runs before consent and reads names and capped first headings only, so it groups and ranks and never compares bodies), `plugins/gtm-base/lib/gtmbase/constants.py` (`MARKETING_KIND_WEIGHTS` and the version and template ranking vocabulary), `plugins/gtm-base/lib/gtmbase/join_flow.py` (`chosen_places` and `freeze_sources` record explicit selection distinctly from a plain yes; a changed manifest asks again; `preview_step` says why a draft reads a limited amount, compares the bodies of grouped versions now that consent exists and says a conflict out loud, and no longer asks before every draft whether to narrow when the folder choice was explicit), `plugins/gtm-base/lib/gtmbase/drafting.py` (`order_sources` ranks templates and READMEs last), `plugins/gtm-base/skills/join/SKILL.md` (step 5: the count confirmation for an explicit choice, the narrowing question asked at most once, and the consent paragraph cut from seven sentences to three short lines plus the question, keeping the 0.2.2 lesson that the sentence must say the files are read and not copied anywhere; step 6: the per-draft narrowing ask dropped for an explicit choice; `tests/test_join_setup_flow.py` around line 1595 pins the old paragraph and is rewritten with it)
- Test: `tests/test_sources.py`, `tests/test_join_setup_flow.py`, `tests/test_drafting.py`, and the fixture tree under `tests/fixtures/sources/`, which already holds an `engineering/` folder with `deploy-plan.md`, `queue-notes.md`, `retry-rules.md`, `runbook.md`, `schema.md` and a `marketing/` folder with `_spine.md`, `icp-fintech.md`, `persona-ops-lead.md`, `positioning.md`, plus a top-level `metrics.csv`

**Approach:** Provenance is the heart of it. The consent record gains a field distinguishing a plain yes to the survey from an explicit list the person named, because Codex established that a plain yes also populates selected folders, so checking whether folders exist preserves the broad-list problem. An explicit choice is honored without a second narrowing question and gets a plain count to confirm; a changed manifest re-consents. The plans-and-metrics rule keeps manual inclusion by name, because Codex's trade-off is that requiring a profile nearby also hides a legitimate standalone `Plans/` folder. Version grouping is deterministic: same stem groups together, a name carrying "final" outranks a newer modification time, and when two versions disagree the conflict is stated rather than silently ordered away, because modification time is not review authority.

**Patterns to follow:** The frozen consent list and the listing digest; the rule that narrowing only ever takes part of a list already agreed to and never widens it.

**Test scenarios:**
- Happy path: the fixture tree's `engineering/` folder is not proposed as a marketing place although it holds a plan and a schema; `marketing/` is proposed with its counts.
- Edge case: a top-level `Plans/` folder with no profile beside it is not proposed, and adding it by name works and is recorded as an explicit inclusion.
- Happy path: the person names four folders: the narrowing question is not asked again, a plain count confirms the list, and the consent record shows an explicit choice.
- Edge case: a plain yes to a survey of the same four folders is recorded as a plain yes, and the narrowing backstop still applies to it.
- Edge case: the chosen list changes between the survey and the freeze: consent is asked again and the old manifest is not reused.
- Happy path: `positioning.md` and `positioning.final.md` group as one version set, the final wins, and the fact that a newer sibling was not used is stated.
- Edge case: two versions whose bodies disagree: after consent, the preview reports the conflict in words rather than resolving it silently.
- Security (r2): the survey opens no file body. Asserted with a reader that fails on any read past the capped first heading.
- Edge case (r2): with an explicit folder choice, no draft is preceded by a narrowing ask; with a plain yes, the backstop still asks.
- Edge case: a template and a README rank last in `order_sources` and are the first things the cap drops.
- Happy path: the preview says how many files this draft reads, how many it leaves out, which ones, and why a draft reads a limited amount at all.
- Integration: preview and assemble include exactly the same files for the same narrowing, asserted by comparing their label lists.

**Verification:** A live survey of `~/Gridwise` proposes the places Brandon would have picked, asks the narrowing question at most once, and the preview explains itself.

**Atlas: figure 7.**

- [ ] **Unit 1.7a: Scope and the segment inventory (split from Unit 1.7 by r2)**

**Goal:** Setup knows what part of the company the base is for and which segments it will hold, before anything is drafted or adopted.

**Requirements:** P18, P19, P23.

**Dependencies:** 1.6. r2 split revision 1's Unit 1.7 into four, because Astra asked for separately testable pieces and Fable H7 found its write order contradicted itself. The order below is the design for all four.

**The order, as numbered steps (r2):**
1. The scope question is asked once, when the person says the base is for one part of the company or the material plainly splits. The answer is held in the run folder, because the umbrella that will carry it does not exist yet.
2. Scope is applied to selection by the person dropping named places that fall outside it, and the consent record keeps the scope label beside what was dropped. There is no text filter: nothing in revision 1 said how free text would filter files, and Codex itself called folder names a heuristic.
3. The segment inventory is settled. For each candidate the person says one of three things: adopt this finished document as the authoritative version for one segment, draft this segment, or leave it out. The inventory is saved in the run folder.
4. The umbrella is drafted from the settled inventory and approved. It creates the base, exactly as the profile does today (`SKILL.md` lines 341 to 345 and `approve --parent` assume the first document is the profile, and that stays true). `covers:` is written into its frontmatter from the held scope. A segment left out is named as pending, in words. A segment chosen for adoption or drafting is named plainly, and whether its file exists yet is computed and never written into the umbrella, so the umbrella does not become wrong when the import finishes.
5. The positioning is drafted and approved. The base is complete.
6. Adoption runs per file through the contract (1.7c), and segments with no finished page are drafted (1.7b).
7. An interrupted import resumes from the saved inventory (1.7d).

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/segments.py` (the inventory, slugs, the three answers, the saved state), `tests/test_segments.py`
- Modify: `plugins/gtm-base/lib/gtmbase/validate.py` (the `covers:` field), `plugins/gtm-base/lib/gtmbase/join_flow.py` (steps 1 to 3 and the held scope), `plugins/gtm-base/lib/gtmbase/sources.py` (the scope label on the consent record), `plugins/gtm-base/lib/gtmbase/constants.py` (the segment kind and the slug rules, append only), `plugins/gtm-base/skills/join/SKILL.md`, `templates/company-base/` and the plugin-side copy (an empty `context/strategy/segments/` folder only)
- Test: `tests/test_join_setup_flow.py`, `tests/test_sources.py`, `tests/test_scaffold.py`

**Test scenarios:**
- Happy path: the scope answer is held, then written to the umbrella's `covers:` field and validated; the places the person dropped are recorded with the scope label.
- Edge case: no scope question is asked when the person did not raise it and the material does not split.
- Happy path: an inventory of twelve with two left out is saved and read back identically after the session ends.
- Edge case: a company with one segment has an inventory of one and gets only the profile, at full depth.
- Edge case: two candidates that slug to the same name are caught at the inventory, before anything is written.

**Verification:** On the Gridwise material Brandon settles scope and the inventory in one short exchange and the saved inventory matches what he said.

**Atlas: figure 7.**

- [ ] **Unit 1.7b: Umbrella and segment drafts, and the unanswered-marker state (split from Unit 1.7 by r2)**

**Goal:** A company with several segments gets an umbrella plus a drafted file for each segment that has no finished page, and an unanswered `[your call: ...]` marker is a real state.

**Requirements:** P18, P19, P27.

**Dependencies:** 1.7a.

**Files:**
- Create: `plugins/gtm-base/skills/join/references/prompts/draft-umbrella.md`, `draft-segment.md` (asks for depth and forbids compression), `tests/fixtures/drafts/umbrella.md`, `segment.md`
- Modify: `plugins/gtm-base/lib/gtmbase/drafting.py` (explicit `umbrella` and `segment` variants, added rather than validation weakened), `plugins/gtm-base/lib/gtmbase/stale.py` and `base_reader.py` (the marker is detected from the body and is a state independent of `status`; a file carrying one is not complete and not confirmed), `plugins/gtm-base/lib/gtmbase/constants.py` (the marker pattern), `plugins/gtm-base/lib/gtmbase/stale_check.py` (the review lists each marker and asks; the ordering slot Unit 1.2 left empty is filled), `plugins/gtm-base/lib/gtmbase/confirm.py` (no confirmation path settles a file while a marker remains), `plugins/gtm-base/skills/join/references/prompts/draft-icp.md` and `draft-positioning.md` (both ask for the marker today, the second at line 83; both are reconciled with the rule)
- Test: `tests/test_drafting.py`, `tests/test_stale.py`, `tests/test_base_reader.py`, `tests/test_confirm.py`, `tests/test_prompt_guards_join.py`

**Approach:** The umbrella says who the company sells to overall, gives each segment one short paragraph, and says what they share. `draft-icp.md` stays the prompt for a company with one segment. Settling a marker later is a prepared change approved through Unit 1.2b, never a setup step overwriting a file. A marker alone never triggers the moment-of-use flag.

**Test scenarios:**
- Happy path: fixture sources for three segments produce an umbrella with three short paragraphs and three segment drafts at depth.
- Edge case: a segment left out in the inventory appears in the umbrella as pending in words, and nothing in the umbrella is a link.
- Edge case: a file carrying a marker is not complete and not confirmed whatever its `status`.
- Edge case (r2, Astra test table): with a marker still in the file, a drafted confirmation, an ordinary yes, and a confirmation after an approved change each leave the file not confirmed.
- Happy path: the review lists each marker and asks; answering one produces a prepared change, and after local approval the marker is gone and the file can be confirmed.

**Verification:** Brandon reads an umbrella drafted from the Gridwise material and recognizes every segment in it.

**Atlas: figures 7 and 8.**

- [ ] **Unit 1.7c: Guarded adoption (split from Unit 1.7 by r2)**

**Goal:** A finished document is adopted under a per-file contract instead of being rewritten, the person approves exactly the bytes that are saved, and adopted text stays data every time it is read afterward.

**Requirements:** P20, P21, P22, P23.

**Dependencies:** 1.7b, 1.2b.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/adopt.py` (the contract, in the order in the decisions table), `plugins/gtm-base/skills/join/references/adoption-rules.md`, `tests/test_adoption.py`, `tests/fixtures/adoption/` (a clean finished profile; one with embedded frontmatter; one with malformed frontmatter; one with a fence marker hidden inside a comment; one with `owner:` and a phone number in the body; one with a private key block; one with two `## Overview` headings; one with a heading-shaped line inside a code fence; one with underlined headings; one that covers two product lines; one whose name slugs into a collision; one under a symlinked folder)
- Modify: `plugins/gtm-base/lib/gtmbase/review.py` (`approve` accepts an adopted file bound to a byte hash; destination checks for variable paths before any write: canonical form, safe slug, normalized collision, symlink parent, trust names), `plugins/gtm-base/lib/gtmbase/join_flow.py` (adoption offered per file from the saved inventory), `plugins/gtm-base/skills/stale-check/SKILL.md` (around line 62 the assistant reads the document while improving a prepared change), `plugins/gtm-base/skills/propose-change/SKILL.md`, `plugins/gtm-base/skills/confirm/SKILL.md` (every Phase 1 path that hands a context file to the model puts it inside the data fence; with `injection.md` from Unit 1.3, that is all of them)
- Test: `tests/test_review.py`, `tests/test_join_setup_flow.py`, `tests/test_stale.py`

**Approach:** The checks run in the decisions table's order, and r2 adds three. Heading grammar (Astra 5): the proposal editor treats a heading-shaped line inside a code fence as a heading (`compose_proposal.py` around lines 213 and 969) and cannot address every valid Markdown structure, so adoption accepts only the grammar the editor supports, and the proof is a round trip: adopt, prepare an edit to one section, apply it, and the right section changed. Scope (Astra, condition E): a document that covers more than the recorded scope is refused with the reason and the offer to draft that segment instead, because dropping file names cannot make a mixed body valid. Display (Fable H4, Astra's fifth contradiction, call 5): the person is shown what was removed and counted, the document's opening lines, and where the whole cleaned file sits in the run folder, and can read it whole before answering; the yes is bound to a hash of that file, and changing the source or the cleaned file between the showing and the yes asks again. A yes covering several is accepted only after each has been shown this way, and leaving one out disturbs no other. Adoption never edits or moves the original.

Later reads (Astra 7, Fable M5). Approval establishes which document was adopted. It does not make an instruction inside it authoritative. Ordinary-language instructions pass every screen, so the fence is the whole defense, and this unit puts it on every Phase 1 path named above and records the residual risk in the CHANGELOG in those words.

**Execution note:** Build the contract test-first against the hostile fixtures before any adoption code writes a file. Every fixture exists to fail one clause, and a clause with no failing fixture is not built.

**Patterns to follow:** `trust_checkout` in `tests/support.py` as the model for hostile fixtures; the absent-only write with `lexists` in `drafting.py` and `review.py`.

**Test scenarios:**
- Happy path: twelve finished pages, each shown and then adopted: twelve files under `context/strategy/segments/`, each with library-written frontmatter, `sources` naming the original path and its date, and one drafted confirmation line; every original is byte-identical afterward.
- Edge case: the person leaves out two of the twelve: ten are adopted and nothing else changes.
- Security: embedded frontmatter is discarded and the library's applied; malformed frontmatter is refused; the hidden fence marker is caught after hidden-content removal, not before; the body `owner:` and phone number are refused with the class named and never the value; the key block is refused.
- Security (r2): two `## Overview` headings, a heading-shaped line inside a code fence, and underlined headings are each refused with the reason and the offer to draft instead.
- Integration (r2): the round trip. An adopted document takes a prepared edit to one named section and the right section changes.
- Security (r2): the document covering two product lines is refused under a one-line scope.
- Security: a colliding slug, a destination under a symlinked folder, and a slug matching a trust-refused name are each refused before any write.
- Security (r2): a tree the person dirtied, and a base not on its default branch: refused, and the test asserts no destination file, no confirmation line, and no other tracked write.
- Security: the approval hash covers the exact cleaned bytes; changing the source between the showing and the yes invalidates it.
- Security (r2): with a hostile adopted document in the base, the rendered input of the stale-check improvement step, propose-change, confirm, and the injected context each carry it inside the fence. The test claims the fence, not the model's behavior.
- Edge case: an adopted file is confirmed only by the owner's own yes, and `status: adopted` gives it no freshness of its own.
- Edge case: twelve adopted segments and one open change affecting one of them produce one review item.

**Verification:** A live replay of the Gridwise material leaves twelve segment files whose bodies are the ones Brandon already reviewed, and no file he had no chance to read whole before it was written.

**Atlas: figures 1 and 7.**

- [ ] **Unit 1.7d: Recovery of an interrupted import (split from Unit 1.7 by r2)**

**Goal:** An import that stops anywhere, including partway through one file, finishes on the next run with no duplicate, no overwrite, and no file that looks adopted without being confirmed.

**Requirements:** P19, P22.

**Dependencies:** 1.7c.

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/adopt.py`, `plugins/gtm-base/lib/gtmbase/segments.py` (per-file state in the saved inventory: approved hash, written, confirmed, committed), `plugins/gtm-base/lib/gtmbase/review.py`, `plugins/gtm-base/skills/join/references/closing-rules.md` and `docs/join-guide.md` (the first-backup review must be rewritten for a base holding many files, recorded as a condition of release two starting, since `push_review.py` is not built)
- Test: `tests/test_adoption.py`, `tests/test_segments.py`, `tests/test_join_setup_flow.py`

**Approach:** r2 (Astra 6): the shipped writer writes the document, stages it, appends the confirmation, then commits (`review.py` around line 348). A failure between those steps leaves a destination that exists and perhaps a dirty tree, and a retry then meets the absent-only refusal or the clean-tree refusal. Revision 1's "interrupted after six" could pass by testing six successful commits, and resuming from file presence would mistake a half-written file for an adopted one. Recovery is therefore per file and bound to the approved bytes: a destination whose bytes match the approved hash and that lacks its confirmation or its commit is finished; a destination whose bytes do not match is never overwritten and is reported; a tree dirtied only by this import's own recorded step is recovered, and one the person dirtied is refused. The two required files already made the base complete, so a half-finished import never makes it incomplete again.

**Test scenarios:**
- Error path: a failure injected after the write, after staging, after the confirmation line, and after the commit, for one file in the middle of twelve: the next run finishes that file and the rest, writes no duplicate, and ends in the same state as an uninterrupted run.
- Security: a destination that exists with other bytes (an unrelated file at that path) is never overwritten, and is reported.
- Edge case: the import stops after six complete files: the next run adopts the remaining six and touches none of the first six.
- Edge case: the approved hash for a file no longer matches its source on the resumed run: that file is asked about again and the others proceed.
- Integration: a second seat reading the same base computes the same flags for the adopted files, with no seat-local state involved.

**Verification:** Brandon stops an import partway on purpose and the next session finishes it without asking him anything he already answered.

**Atlas: figure 7.**

- [ ] **Unit 1.8: The sweep of text no unit touched**

**Goal:** Every text a person reads meets `docs/ux-standard.md`, and the lint's exemption list is empty or every entry left has a reason that is not "later".

**Requirements:** P28.

**Dependencies:** 1.7d. r2 moved the standard and the lint to Unit 1.1b. What is left is the text no unit owned.

**Files:**
- Modify: whatever the exemption list in `tests/plain_language.py` still names, which by construction is text no earlier unit touched: parts of `plugins/gtm-base/skills/join/references/reading-rules.md`, `plugins/gtm-base/skills/propose-change/references/pr-body-rules.md`, the templates under `plugins/gtm-base/templates/` that no unit changed, the remaining registered Python sentences, and `docs/join-guide.md`
- Test: `tests/test_plain_language.py` and the tests that pin each rewritten sentence, including the safety sentences `tests/test_prompt_guards_join.py` pins around line 32, which keep their meaning word for word where the meaning is a safety promise

**Approach:** Work the exemption list to empty. The closing question about what got in the way gains the three things P28 requires: that it is feedback for the people who make GTM Base, that it is optional, and where it is kept. A sentence a test pins is changed together with its test and the reason is recorded in the test. Nothing here changes behavior.

**Test scenarios:**
- Lint: every SKILL.md, every reference file, every template, and every registered Python sentence passes all four checks; the exemption list is empty or every entry carries a lasting reason.
- Edge case: every safety sentence pinned by `tests/test_prompt_guards_join.py` still says what it said.
- Integration: `sh tests/run.sh` passes.

**Verification:** Brandon reads three steps he has never seen and can say, in one sentence each, what the step is for and what it is asking him.

**Atlas: figures 5 and 7**, only where a sentence quoted in the atlas changed.

- [ ] **Unit 1.9: The fidelity replay, as the release gate on Phase 1**

**Goal:** Decide with evidence whether the summarize-first step must be built in this release, instead of deferring it a third time.

**Requirements:** P29, P3.

**Dependencies:** 1.1 (the frozen bar), 1.8. Release B does not ship until all three cases have been run and pass. If a case fails, the summarize-first step is built and the same three replays must pass afterward; building it is not passing (r2, Astra 3).

**Files:**
- Modify: `docs/walkthroughs/2026-09-fidelity-replay.md` (created by 1.1 with the frozen bar; this unit adds what was read, what survived, what did not, and the decision)
- Modify: `docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md` (the deferred brief pipeline's entry records the replay result), `plugins/gtm-base/CHANGELOG.md`

**Approach:** Three cases, replayed through the flow as Phase 1 leaves it. Case one: the twelve finished Gridwise pages, which after 1.7 go through adoption rather than drafting, so what is being tested is the umbrella and the positioning that are still written from them. Case two: a company with several segments and no finished pages, so every segment is drafted; by default this is the real Gridwise material with the twelve finished pages held out of consent, and the drafted segments are scored against those pages as the answer key. Case three: positioning inputs larger than one request, produced by lowering the input cap for the replay, which the record states. Brandon scores every case and the builder scores none. The uncorrected output is scored against the whole original corpus, including material past the input cutoff, because what the cap dropped is exactly what the gate is looking for. What is read, in each case: whether every segment the material names appears in the output, whether named deals survive, whether figures survive with their units, whether the source and version each claim came from is attributable, whether unresolved choices are marked rather than invented, and what a reviewer had to correct. The pass bar is stated before the replay is run, not after: every segment present, no figure altered, no named deal dropped, every claim attributable, and no invented content. A fail on any of those builds the summarize-first step in this release, as a stage between reading and drafting, with its own unit written then.

**Execution note:** This unit produces a record and a decision, not a feature. The record holds real results only. If a case cannot be run, the record says so, names it, and the gate is incomplete; it is never decided on the cases that happened to run (r2).

**Patterns to follow:** `docs/walkthroughs/2026-09-05-phase-a1-sc1-sc5-test-base.md` as the shape of a walkthrough record; the standing rule that walkthrough records come from real runs only.

**Test scenarios:**
- Not a code unit. The proving test is P3: the first feature's hand-entered-change flag-and-proposal scenario in `tests/test_stale.py` and `tests/test_stale_check.py` is rerun independently after the replay, to prove Phase 1 did not break the path the whole product rests on.
- Integration: `sh tests/run.sh` passes in full immediately before the gate decision is recorded, and the test count is recorded with the decision.

**Verification:** The record names the three cases, states the bar, states the result against the bar, and states the decision, with no estimate anywhere in it.

**Atlas: figure 7**, which gains the note about what a draft reads and why.

### Later phases, not detailed here

**What a base holds, the other two skills, and company skills.** Revision 1's Phases 2 to 4, moved word for word to `docs/plans/2026-09-19-002-roadmap-after-phase-1.md` with the review findings that apply to them. Each becomes its own plan after the outbound sequence has been used on real work, because that use will change what the inventory and the rubric files need to hold.

**Reviewing proposals from a shared copy in Claude.** Unit 1.2b builds the local half of the first plan's Unit 8 (`review-proposals`): approving one prepared change on a base with no shared copy. The other half is still unbuilt: listing the open proposals on a shared copy, rendering each as before-and-after prose, checking the branch hash against what the reviewer saw, and reject-but-keep. Until it exists, a base that has a shared copy can only approve on the GitHub page, which is the gap the parent scope's marketer critique named, because the founder approver never opens GitHub. It is the first unit of the plan that ships backup, since no base has a shared copy before then.

**Reading calls and threads for context changes.** Phase A2 of the first plan (Units 5 and 6) turns transcripts into proposals. Applied to context changes, its hard part is the relevance bar: an entry is written only from a specific line that is change-shaped, the quote is carried as evidence, the number written per run is capped, and rejections teach the bar rather than being discarded. Its surface is the weekly review, not an interruption, which is what makes it compatible with quiet by default.

**Backup, invite, the second seat, and the pinned plugin id.** Release two of the join plan. Before any of it, the release step has to put a real forty-character identifier in the company template's settings file in place of the row of zeros that ships today, because a base created before that installs nothing for the person who joins it. The first-backup review also has to be rewritten for a base holding many files, since its original rationale was that inspection is cheap when there are at most three drafts, and it now also covers every change that was approved locally before the backup. And every seat updates its plugin before a base is migrated to `work/changes/`, because a seat on an older plugin reads a migrated base as empty and reports nothing out of date (Fable, recorded by Unit 1.4 as a test).

**Codex packaging.** The first plan's Unit 11 and its Tier B verifications, which decide which Bash gate is live on Codex and what that client can and cannot enforce.

**The web app as the home of the review queue.** Amendment r2.3 of the first plan and r2.5 item 7: the queue lives there, with a way to open a proposed change in Claude to talk it through. It is the answer to the approver who opens neither Claude Code nor GitHub, and it is also where the pin-bump problem and the rollback threat get solved.

## System-Wide Impact

**Interaction graph.** The session-start hook loses a branch (the question) and keeps the rest: record the session, pull under the existing path refusals, inject the map, the change summary, and the moment-of-use instruction. The stale-check skill gains one entry point, the review, which also lists prepared changes awaiting local approval, and keeps one computation. The confirm skill's entry point moves from the injected question to the review and to the moment-of-use flag, with `confirm.pending_questions` as the way back. The join skill gains the scope question, the segment inventory, adoption, and the closing question, and loses one drafted document. `propose-change` gains the one local-edit request and, on a base with no shared copy, the local approval. No new skill is added. The plugin's records folder gains the weekly-line preference and the silence date; nothing else new is written there, and nothing at all is written outside the base, that folder, and a configured hooks directory.

**Error propagation.** Unchanged posture: hooks exit 0 with fixed sentences, skills narrate and return to the same step, the gate and the path guard fail closed, everything else fails silent but visible. Three new failure surfaces: a migration that cannot run or stops partway leaves a recorded transaction that the next run finishes or puts back, while the reader goes on returning every entry from both folders; an adoption that fails any clause of its contract writes nothing and names the clause without naming the value; and a local approval that fails partway ends, on retry, in the same state as one that did not fail.

**State lifecycle risks.** The migration is the sharpest one: entry ids are the join key for confirmations, corrections, proposals, and the index, so the migration moves the folder and renames fields and touches no id. Partial adoption is the second: an interrupted import must resume rather than restart, and the umbrella must never hold a link to a file that was skipped, which is why the inventory is settled before the umbrella is approved. The unanswered-marker state is the third: it is computed from the body and not stored, so it cannot drift out of step with the file, and it is deliberately independent of `status` so a retained draft cannot count as complete.

**Unchanged invariants.** No MCP servers declared. Context reads stay local and make no network call. Nothing is written outside the base, the plugin's records folder, and a configured hooks directory. The proposal body remains the single artifact, so the web app will render it unchanged. Tracked files are written only through a proposal, a confirmation, or setup mode for files absent from the base, and adoption is explicitly inside that last clause rather than an exception to it. The AI proposes and the owner approves. The trust-surface refusal set is untouched.

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| The rename breaks the one existing base | Both folders are read and joined by entry id, so no state hides an entry. The migration is a recorded transaction with a commit point and a recovery step, makes the move and the field rewrite as two changes so history follows, touches no entry id, refuses on a tree the person dirtied, and records what it did in `corrections/` in a shape the report parses. A failure is injected after every mutation in the tests. The old layout stays readable forever. The migration is run live on the Gridwise base before the release ships, and its next review is compared with the one before |
| Adoption imports a bad document into cross-seat context | The per-file contract, run in a fixed order, with a hostile fixture per clause; original metadata discarded; fence-marker rejection after hidden-content removal; contact and key screens on the cleaned text; approval bound to the exact bytes shown; adopted content fenced as data on every later read. Residual: ordinary-language instructions inside a document are not detectable by any screen, so the fence is the whole defense and it is stated as such |
| The moment-of-use flag is unreliable because it depends on the assistant following an instruction | Inside a core skill the check is deterministic and covered by tests. Outside a skill it is an instruction, so Unit 1.3 measures it in a live trial against a bar set beforehand and evaluates a scoped read hook as the deterministic backstop. Whatever was measured is what the CHANGELOG says. The review remains the surface the product tells people to use |
| Plain-language rewrites drift from tested sentences | The standard and the lint land second (Unit 1.1b), so each unit writes its sentences once, to the standard, before Brandon checks them live. Every exemption names its reason and the unit that removes it, and Unit 1.8 only sweeps what no unit touched. Each unit's own tests assert its texts, so a rewrite that breaks a promise fails a test rather than a review |
| Scope creep | Revision 2 cut this plan to Phase 1 and moved the rest to the roadmap. Release B is gated by the fidelity replay. Setup stays at two documents in every phase. The scope boundaries list what is not built |
| One real user so far | Every unit that changes a sentence gets a live check. Walkthrough records come from real runs only. The fidelity replay's second case may not exist in real material, which is an open question for Brandon rather than a fixture quietly standing in for evidence |
| The fidelity replay fails and the summarize-first step must be built | The gate is stated before the replay runs, and a fail adds a unit inside this release rather than deferring a third time. The cost is a slip in Phase 1's release date, which is accepted |
| No proposal could complete on a base with no shared copy, which is every base that exists | Unit 1.2b, before anything depends on a proposal. It changes nothing about what may leave the computer. The shared-copy half of `review-proposals` ships with backup |
| Two releases let release A ship without adoption or the fidelity gate | Nothing in release A changes how setup drafts, so it cannot make fidelity worse than 0.2.6. Units 1.2 to 1.5 ship together so no release captures no context change. If Brandon chooses one release instead, only the version bump moves |
| Two template copies drift | `tests/test_scaffold.py` holds them identical file for file, and every unit that touches one touches both |
| The atlas falls behind the code | Every unit names the figures it updates, the atlas is changed in the same commit as the code, and it is republished on release |

## Documentation / Operational Notes

- `plugins/gtm-base/CHANGELOG.md` gains an entry per unit as it lands, written in plain language, naming the real-run evidence behind it. No entry claims a result that was not observed.
- The version in `plugins/gtm-base/.claude-plugin/plugin.json` is bumped per release, because installed seats fetch by version and an unbumped release reaches nobody.
- `docs/diagrams/logic-atlas.html` is updated in the same change as the code and republished to its artifact after each release. Units name their figures; Brandon's answer to open question 5 decides whether Phases 2 and 3 get figures of their own.
- Walkthrough records come from real runs only: `docs/walkthroughs/2026-09-fidelity-replay.md` for the gate, and a record for the first live run of the quiet start and the first live adoption.
- `docs/join-guide.md` gains the update step and loses the third document. It stays the only user-facing document besides the offer, the closing message, and the invite.
- The memory file `gtm-base-product-direction.md` and `docs/handoff-2026-09-19.md` are kept current as each phase ships, since they are what a new session reads first.
- `tasks/lessons.md` gains a line for each correction found during the build, per the standing practice.

## Sources & References

- The two reviews of revision 1: [docs/reviews/2026-09-19-plan-review-astra.md](../reviews/2026-09-19-plan-review-astra.md) and [docs/reviews/2026-09-19-plan-review-fable.md](../reviews/2026-09-19-plan-review-fable.md); the brief both answered: [docs/reviews/2026-09-19-plan-review-brief.md](../reviews/2026-09-19-plan-review-brief.md)
- The roadmap that now holds Phases 2 to 4: [docs/plans/2026-09-19-002-roadmap-after-phase-1.md](2026-09-19-002-roadmap-after-phase-1.md)
- Amendment r2.4 (sections A to I) and Amendments r2.1 to r2.3: [docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md](2026-09-05-001-feat-join-and-onboarding-plan.md)
- Amendment r2.5 and Units 5, 6, 8, 11, 12: [docs/plans/2026-09-04-001-feat-current-without-integrations-plan.md](2026-09-04-001-feat-current-without-integrations-plan.md)
- Codex verdict and its ordered change set: [docs/reviews/2026-09-19-codex-setup-shape-verdict.md](../reviews/2026-09-19-codex-setup-shape-verdict.md); the brief it answered: [docs/reviews/2026-09-19-codex-setup-shape-brief.md](../reviews/2026-09-19-codex-setup-shape-brief.md)
- The competitive read: [docs/ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md](../ideation/2026-09-19-mkt1-multiplayer-ai-comparison.md)
- Handoff and the atlas: [docs/handoff-2026-09-19.md](../handoff-2026-09-19.md), [docs/diagrams/logic-atlas.html](../diagrams/logic-atlas.html)
- Origin requirements: [docs/brainstorms/2026-09-05-join-and-onboarding-requirements.md](../brainstorms/2026-09-05-join-and-onboarding-requirements.md), [docs/brainstorms/2026-09-04-current-without-integrations-requirements.md](../brainstorms/2026-09-04-current-without-integrations-requirements.md)
- Parent scope: `~/Obsidian/Vault/Work/GTM-Base/2026-09-04-gtm-base-scope-v1.md`
- Doctrine: the AI-native definition block in `~/Personal/CLAUDE.md`
- Lessons and the released behavior: `tasks/lessons.md`, `plugins/gtm-base/CHANGELOG.md`

## Revision Log

- 2026-09-19 r1: written from Amendment r2.4 of the join plan, Amendment r2.5 of the first plan, the Codex setup-shape verdict, and the MKT1 comparison, grounded in the shipped code at 0.2.6. Four phases, twenty units. Nothing built.
- 2026-09-19 r2: both plan reviews folded in (Astra through Codex: not ready; Fable 5.1: ready only with changes). Cut to Phase 1 plus the runner and the outbound sequence; Phases 2 to 4 moved unchanged to `2026-09-19-002-roadmap-after-phase-1.md`. Added Units 1.1b (UX standard and lint, second), 1.2b (approve a proposed change locally), 1.4b (runner), 1.4c (outbound sequence). Split 1.7 into 1.7a to 1.7d with the write order as numbered steps. Rewrote 1.3 with an action contract, a measured trial, and a read-hook evaluation, and 1.4 with both folders read and a recoverable migration. Made the fidelity gate unable to pass on missing cases. Added P36, P37, and SC-C. Two releases by default. Eight calls for Brandon, each with the default the plan is written to. Baseline before the build: 1127 tests passing, after `tests/run.sh` was given a fixed time zone (three tests in `tests/test_review.py` assumed a Pacific date and failed on a machine set to Hawaii time). Nothing built.
- 2026-09-19 r2.1: Brandon's call, context first and skills after. Units 1.4b (runner) and 1.4c (outbound sequence), P33, P37, and SC-C moved to the roadmap, which now puts what a base holds ahead of any skill. Call 2 closed. Release A is Units 1.1 to 1.5.
- 2026-09-25 r2.2: Brandon's CLASS framework (MICW Issue #4 v10: Context, Learning, Access, Skills, Standard) and its context standard adopted as the base's layout. Added Unit 1.5b before Release B, requirement P38, and calls 9 to 11. GTM Base supplies Context, Learning, and the approval half of Standard; Skills and the checks half of Standard follow in the roadmap; Access stays with the tools. The draft four questions in docs/ux-standard.md are replaced by CLASS. The base still refuses an `AGENTS.md` inside it; the plugin delivers the map through its hook and the base holds `context/stack.md`.
- 2026-09-25: calls 9 to 11 decided as recommended (the standard's names flat in `context/`, competitors folded into positioning, segments under `context/icps/`). The article's AGENTS.md note: GTM Base delivers the map through its hook, and the article says so.
- 2026-09-25 r2.3: Brandon's calls 12 to 14. A base is laid out by the five CLASS parts (`context/`, `learning/`, `access/`, `skills/`, `standards/`, with `work/` for the approval machinery). `stack.md` moves to `access/`, which departs from the article's draft path `context/stack.md`. The change record moves from `work/changes/` to `learning/changes/` in the same offered move as the context files. `skills/` exists but is refused until the company-skills brainstorm settles the trust model, which runs before the first skill. `learning/lessons/` is reserved for lessons from results, the second input to Learning in the article, which no plan covered.
