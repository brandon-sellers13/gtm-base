---
title: "feat: Track 4, what a base holds"
type: feat
status: draft, waiting for Brandon's answers under "For Brandon"; no code is written until then
date: 2026-11-27
origin:
  - docs/plans/2026-11-26-003-roadmap-to-full-experience.md (Track 4, and the order it runs in)
  - docs/plans/2026-09-19-002-roadmap-after-phase-1.md (Units 2.2 to 2.6 and 3.2 to 3.4, where these units were first listed, and the reviewers' findings beside them)
  - docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md, read from the local branch claude/plan-1-meta-skill-3d436e (the skills folder, the runner, the inventory and the starter pattern this plan builds on)
  - docs/plans/2026-10-10-001-phase-2-3-decisions.md on the same branch (D4, D6, D7, and the material M1 to M5 and M9 to M11)
  - docs/brainstorms/2026-10-10-company-skills-requirements.md on the same branch (signed by Brandon 2026-10-10)
  - docs/ideation/2026-11-24-messaging-reframe.md (untracked in the main checkout; the positioning)
  - docs/plans/2026-11-26-001-feat-chat-connector-plan.md (C3, which needs a real skill to serve)
---

# feat: Track 4, what a base holds

## What this plan covers

A new company's base holds a customer profile and a positioning today, and nothing that uses them. This plan adds the rest of what makes a base worth having, in three groups:

1. **Context documents.** Messaging and voice, design, competitors, buyer personas, and goals.
2. **The sources-of-truth file and keeping GTM Base up to date.** The source map at `access/stack.md` made useful for any company, and one sentence that tells a person how to update the plugin.
3. **The first skills that use a base.** Drift grade, content brief and outbound sequence, with drift grade built first so the connector's skills unit (C3) has a real skill to serve.

This is the plan Brandon's decision D4 of 2026-10-10 called Plan 2 (messaging, voice, design, product, buyer personas, updating GTM Base, drift grade and content brief), with the outbound sequence added back from the parked roadmap. D4 said Plan 2 would be written after the Meta ads skill had run on real nights. The roadmap of 2026-11-26 changed that order, running Track 4 alongside the connector and the Plan 1 catch-up, so this plan is written now and says below which of its units wait for what.

The positioning sets what each piece is for. The messaging reframe and the ICP work say GTM Base sells standardization: one approved version of the messaging, the brand and the processes, every agent using it, and the approved version kept current when the team decides something new. Every document in this plan is an approved version with an owner. Every skill in it is an approved process that reads approved versions and stops when one has fallen behind.

## Where things stand, verified on 2026-11-26

- **The company template** (`templates/company-base/`, read on main at 44b6fab) holds the map, the customer profile starter `context/icps.md`, the source map starter `access/stack.md` (prose with no rows), and empty `skills/`, `standards/`, `learning/` and `work/` folders. Setup drafts the profile and the positioning and nothing else (`REQUIRED_CONTEXT_FILES` in `constants.py`). The map already names the nine context files of the CLASS standard, so a base expects files it has no way to get.
- **The flag fires on decisions, not on time.** `moment.py` raises the moment-of-use flag only when an open context change names the document and its owner has not confirmed it. A document past its confirmation threshold (thirty days by default) is listed in the review a person asks for and never interrupts work. So "what makes a document overtaken" in this plan always means "which recorded decisions should name it".
- **Naming the documents a change affects is left to the assistant.** The record-a-change step in `skills/stale-check/SKILL.md` prints the base's documents and asks the assistant to say which it thinks the change affects. When a change names none, `stale._affected_files_proposals` suggests documents whose name or kind the change mentions, and otherwise falls back to every profile and positioning. Nothing knows that a profile change usually overtakes the messaging too.
- **Plan 1 is half built and not on main.** On `claude/plan-1-read-side-6c5559` (never merged, behind main by Release B, P1 and the web app): the signed company-skills requirements (4.1), one authority rule and one path rule (4.2a), the inventory with `BASE_KINDS` and `skills/stale-check/references/base-kinds.md` (2.1), and the source map parser (2.5a). Not built: the runner (3.1), the skills folder (4.2b), metric definitions and goals (2.4a), the creative-testing standard (3.5) and the Meta skill on the base (3.6). Another session is bringing the branch onto main now.
- **`BASE_KINDS` on that branch** lists, in order, goals, product, icps, buyer-personas, positioning, messaging, voice, design, metrics, the source map, a standard and a skill, each with its path, whether it differs by business, and whether it is adoptable or draftable. Every kind except the profile is marked not draftable.

Test files named below that do not exist on main yet (`test_inventory.py`, `test_stack.py`, `test_runner_contract.py`, `test_skill_install.py`) are created by the Plan 1 units this plan depends on.

## How this plan depends on Plan 1

Every code unit here is written against Plan 1 as it stands on `claude/plan-1-meta-skill-3d436e`, revision 2.9, and the signed company-skills requirements, and assumes no layout of its own. Concretely:

| What this plan uses | Where it comes from | Built? |
|---|---|---|
| `BASE_KINDS`, `base-kinds.md`, the inventory's "what is my base missing?" | Plan 1, Unit 2.1 | Yes, on the unmerged branch |
| One path rule (`docpaths`), one authority rule (`authority`), absent-only creation of a document, the owner-line operation | Plan 1, Unit 4.2a | Yes, on the unmerged branch |
| The source map parser `truth_map.py` and its five columns | Plan 1, Unit 2.5a | Yes, on the unmerged branch |
| The runner (`runner.py`, `use-skill`), declarations in a skill's settings block, required and optional documents, named outcomes, the contract test with examples and deliberately wrong outputs | Plan 1, Unit 3.1 | No |
| The skills folder: the exact shapes `skills/<job>/SKILL.md`, `skills/<job>/references/<name>.md` and `skills/<job>/examples/<example>/<name>.md` (company-skills requirement CS19), installing a skill as one approved manifest with the base owner's or an administrator's yes | Plan 1, Unit 4.2b | No |
| The goals and metric definitions prompts and starters in `plugins/gtm-base/starter/`, never in the company template | Plan 1, Unit 2.4a | No |
| The standard kind's five sections and its digit lint | Plan 1, Unit 3.5 | No |

Two consequences follow.

**No code unit in this plan starts before the Plan 1 catch-up merges into main.** Every unit edits files the catch-up is moving (`constants.py`, `drafting.py`, `inventory.py`, `base-kinds.md`). What can start now is collecting Brandon's material and writing the drift grade's examples and standard as plain documents.

**C3 waits on the runner as well as the skills folder.** The roadmap's Track 3 list puts the skills folder (4.2b) before the runner (3.1), but Plan 1 orders them the other way, because installing a skill runs the runner's contract check first (Plan 1, Execution Posture, step 4). So drift grade, and therefore C3's demo, needs both 3.1 and 4.2b merged. The roadmap's Track 3 list should be read in Plan 1's order.

## Decisions this plan rests on

These are already decided and are not reopened here, except where "For Brandon" says so.

- **The CLASS layout (2026-09-25 and 2026-09-26).** Nine context files flat in `context/`, segments under `context/icps/`, the source map at `access/stack.md`, each job's rules in `standards/<job>.md`, and skills in `skills/<job>/`.
- **Competitors are a section of the positioning (2026-09-25).** Call 10 folded `competitors.md` into the positioning's alternatives section. This plan recommends reversing that, as call 2 below, and is written so either answer changes one unit only.
- **Starters live in the plugin, not the template (Astra finding 8 of 2026-09-19).** Base creation copies the whole template, absent-only writing would then refuse a starter, and an existing base would never receive it. Every new document shape and every starter skill in this plan ships in the plugin and reaches a base only through an owner-approved creation.
- **Whoever creates a document or a skill owns it (D5).** A change may be approved by its owner, the base owner or an administrator. Creating a skill also needs the base owner's or an administrator's yes (CS requirements).
- **Work in flight stays outside the base (2026-09-19, Fable M8).** Nothing here reads a `context/work/` folder. Drift grade and the content brief lose the feature that compared one piece against other work in flight, unless a later plan reads that from a source at run time.
- **Examples test judgment through expectations, not through a model (Astra 12, Fable M7).** Each skill's examples hold an approved output, an expectations file and at least one deliberately wrong output, and the contract test never calls a model. Judgment is tested by Brandon's replay, kept apart from the tests.
- **Setup stays at two documents.** Everything in this plan arrives after setup, on request, from the inventory or from the offer setup's closing makes.

## Group 1: the context documents

### What each document is

Each document below is an ordinary base document: it has an `owner:` line, it is confirmed and flagged like the profile, and a change reaches it only as a proposal its owner approves. "Owned by" names the role that should own it in a team; the mechanism is the same for all of them, which is that the person who approves the first draft becomes its owner, and the owner-line operation of Plan 1 Unit 4.2a passes it to someone else.

**Messaging** (`context/messaging.md`, one per business)
- *What it holds.* The claims the business makes, to whom, and the proof behind each: the core message, one message per segment and per buyer persona, the proof points (customer results, numbers the sources carry, named customers only where the sources name them as public), the objections and their answers, and the words the business uses and avoids. It says what the business claims, not how it sounds.
- *Owned by.* The product marketing lead, or the head of marketing where there is none.
- *What setup reads to draft it.* The positioning and profile already in the base, then the material the person names: the home and product pages, the sales deck, one-pagers, launch posts, and any messaging guide that already exists. An existing guide that is finished is adopted as it stands under the adoption contract. Every claim is quoted or attributed to the source it came from, and a proof point with no source is left as a marker rather than written.
- *What overtakes it.* A change to the profile or a segment, to the positioning or its alternatives, to the buyer personas, or to the product (a feature added or dropped, a pricing tier changed), and any decision about a claim itself, such as legal flagging a claim or a customer withdrawing permission to be named.

**Voice** (`context/voice.md`, one for the whole company unless a business keeps its own)
- *What it holds.* How the company sounds in writing: a few principles, each shown with sentences quoted from the company's own writing, the words and constructions it uses and never uses, how formality changes by channel, and the rules a writer most often gets wrong. It holds no claims; those are messaging.
- *Owned by.* The brand or content lead, or the founder at a company whose voice is the founder's.
- *What setup reads to draft it.* Writing the company has published under its own name: blog posts, emails to customers, the founder's posts, help pages, and any existing style guide. This is where verbatim-first matters most, because a voice document written in the model's voice is worse than none, so every principle is backed by a quoted sentence and a principle the sources cannot show is left out.
- *What overtakes it.* Only a decision about voice itself (a rebrand, a new style rule, a word the company stops using). A change to the profile or positioning does not overtake it, which is deliberate: the voice is the document least often wrong, and flagging it on every strategy change would teach people to ignore the flag.

**Design** (`context/design.md`, one for the whole company unless a business keeps its own)
- *What it holds.* The visual decisions a piece of work has to respect, written as prose a person can confirm: colour by named role (the primary action colour, the background, the warning colour) rather than lists of codes, type (which family is used for what), logo rules (its construction, the colours it may appear in, and what may never be done to it), and the devices that are forbidden. Tone stays out, because it belongs in the voice document and two places would drift apart (D6, call 3). Assets stay out of the base: no image, font or binary is ever written by this path.
- *Owned by.* The brand or design lead.
- *What setup reads to draft it.* A brand guide or brand book the person names, read as text (a PDF's text, a design-system README, a decided record such as this repository's `brandkit/brand-lock.json`). Nothing is read from pixels, so a guide that exists only as images produces a document that names the gap. A colour code appears only where the source states it.
- *What overtakes it.* Only a decision about the brand itself (a rebrand, a new logo, a colour retired). Like voice, it is not flagged by strategy changes.

**Competitors** (`context/competitors.md`, one per business, if call 2 is answered as recommended)
- *What it holds.* One section per alternative the buyer actually considers, including doing nothing and building it in house: who it is for, what it claims, where it wins, where the business wins, its pricing where public, and the date and source of each fact. The positioning keeps a short list of the alternatives and the one-line reason the business is different from each, and points here for the detail.
- *Owned by.* The product marketing lead.
- *What setup reads to draft it.* The positioning's alternatives section, then battle cards, win and loss notes, and sales call notes the person names, and any competitor pages the person has saved or names. Setup reads only what the person names, as it does today, and does not browse on its own. A competitor the sources name with no claim about it gets an empty section, never an invented one.
- *What overtakes it.* A competitor's move (a launch, a price change, a new claim, an acquisition), a lost or won deal that shows a comparison is wrong, and a change to the business's own product or pricing that changes a comparison. Because competitor facts change far more often than positioning, keeping them in their own file means recording a competitor's price change flags this file only, and work that reads the positioning is not interrupted. That is the reason for call 2.

**Buyer personas** (`context/buyer-personas.md`, one per business)
- *What it holds.* Who inside a customer buys, uses and blocks the purchase: one section per persona with their role, what they are measured on, what they need from the product, the objections they raise, and where they look for answers. Personas are people inside an account; segments are kinds of account, and the two are kept apart, so a persona is never written into a file under `context/icps/`.
- *Owned by.* The product marketing lead, or whoever runs customer research.
- *What setup reads to draft it.* The profile and segments already in the base, then customer interview notes, sales call transcripts, won-deal notes from the CRM, and the job titles on deals, as the person names them. A persona the sources do not show talking or buying is not drafted.
- *What overtakes it.* A change to the profile or a segment (a move up-market changes who buys), a new buying role that shows up in deals, and a product change that brings in a new user.

**Goals** (`context/goals.md`, one per business)
- *What it holds.* What the business is trying to reach, each as a figure its owner stated, with the unit, the period, and where the actual value is measured. Targets that live in a planning model stay there, and the document says where.
- *Owned by.* The head of marketing, or whoever is accountable for the number.
- *What setup reads to draft it.* It asks rather than reads. Plan 1 Unit 2.4a builds the prompt (`draft-goals.md`) and the starter, which refuse a figure neither the sources nor the person's own words carry. This plan builds nothing for goals beyond the line in the "what overtakes" table below and the inventory's offer to a base with one business.
- *What overtakes it.* A planning decision: a new quarter, a board reset, a budget change, or a target moved. It is the document skills most often read for judgment, so a change to it flags the standards that relate a threshold to a goal (Plan 1, Unit 3.5).

**Product** is the one kind of the nine that no group above covers. It is listed in the map, the inventory reports it missing, and the messaging and the content brief both lean on it. Call 5 recommends adding it to the buyer personas unit, since both draft from the same sales material.

### What overtakes what, as one table

This table is what Unit T4.1 builds into the base, so that recording a decision about one document suggests the documents built on it. A row reads: a recorded change that affects the document on the left usually also overtakes the documents on the right.

| A change that affects | Usually also overtakes |
|---|---|
| The customer profile or a segment | Positioning, messaging, buyer personas, competitors |
| Positioning | Messaging, competitors |
| Product | Messaging, competitors, buyer personas |
| Buyer personas | Messaging |
| Competitors | Positioning's alternatives list (only when an alternative is added or dropped) |
| Goals | Every standard that relates a threshold to a goal |
| Voice | Nothing else |
| Design | Nothing else |
| Messaging | Nothing else |

### The units

- [ ] **Unit T4.1: A decision follows through to the documents built on it**

**Goal:** When someone records a context change, GTM Base suggests every document the change probably overtakes, using the table above, so the follow-through the messaging reframe calls the first pillar does not depend on the assistant guessing.

**Depends on:** The Plan 1 catch-up (Unit 2.1's `BASE_KINDS`).

**Files:**
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py` (append only: a `KIND_FOLLOWS` table keyed by kind, read beside `BASE_KINDS`), `stale.py` (`_affected_files_proposals` adds the documents that follow from any document the change names or mentions, and keeps its present fallback), `stale_check.py` and `record_change.py` (the documents step prints, after the numbered list, which documents usually follow from the ones the change mentions), `skills/stale-check/SKILL.md` (step 3 reads the suggestions out as suggestions and still asks), `skills/stale-check/references/base-kinds.md` (each kind's section gains one "overtaken when" sentence), `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_stale.py`, `tests/test_record_change.py`, `tests/test_inventory.py`

**Approach:** Suggestions only. The person still chooses the numbers, and nothing is flagged that they did not choose (call 8). A suggestion names only documents the base holds. A standard is suggested for a goals change only when its own settings name the goals document as one it relates to, so the table never guesses which standards care. The table lives once in `constants.py`, and a test holds it and the "overtaken when" sentences in `base-kinds.md` in step.

**Tests:**
- A change naming the profile suggests the positioning, messaging, personas and competitors the base holds, and none it does not hold.
- A change naming voice suggests nothing further.
- A change naming the goals suggests the standards that relate to the goals and no other standard.
- The person choosing fewer documents than suggested records only those; nothing is flagged that was only suggested.
- Every kind in `KIND_FOLLOWS` exists in `BASE_KINDS`, and every "overtaken when" sentence has a row.

**Done when:** Brandon records "we moved up-market" on a test base and is offered the profile, positioning, messaging and personas without naming them.

- [ ] **Unit T4.2: Messaging and voice, adopted or drafted (roadmap Unit 2.2)**

**Goal:** A base can take in a finished messaging guide or voice guide as it stands, or have one drafted from the company's own material, through the same guarded path as the profile.

**Depends on:** The Plan 1 catch-up (2.1's inventory and 4.2a's absent-only creation). Material: M1 and M2 for Gridwise, or the demo base's own material (call 6).

**Files:**
- Create: `plugins/gtm-base/skills/join/references/prompts/draft-messaging.md`, `draft-voice.md`, `plugins/gtm-base/starter/messaging.md`, `starter/voice.md` (shapes kept in the plugin, as Plan 1 keeps `starter/goals.md`), `tests/fixtures/drafts/messaging.md`, `voice.md`
- Modify: `drafting.py` (two document variants), `inventory.py`, `constants.py` (append only: both kinds draftable and adoptable in `BASE_KINDS`), `base-kinds.md`, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`, `tests/test_review.py`, `tests/test_prompt_guards_join.py`

**Approach:** Both kinds go through the adoption contract when a finished document exists and through a drafting prompt when it does not, and the inventory offers both. The messaging prompt reads the profile and positioning already in the base first, so its claims are tied to the approved strategy rather than to whatever the website says. The voice prompt quotes the person's own sentences for every principle and marks what it could not ground. The prompts carry the verbatim-first rules and the banned-word list already in `draft-positioning.md`.

**Tests:**
- Fixture sources produce a messaging document with no claim the sources lack and a voice document whose every principle carries a quoted sentence.
- Sources with nothing about voice produce a document that says which sections had no signal.
- A draft carrying a contact detail is returned to the same step; a draft with a long dash or a banned word is refused.
- A finished messaging guide is adopted with its original metadata discarded.
- Skipping either leaves the base complete, and the inventory reports it skipped.
- Both are read, owned, confirmed and flagged by a change that names them.

**Done when:** A base holds a messaging document and a voice document its owner would hand to a writer.

- [ ] **Unit T4.3: Buyer personas, and product if call 5 says so (roadmap Unit 2.4, its first half)**

**Goal:** Personas, and the product document, arrive through the same path, with personas kept apart from segments.

**Depends on:** The Plan 1 catch-up. Runs in parallel with T4.2.

**Files:**
- Create: `prompts/draft-buyer-personas.md`, `prompts/draft-product.md`, `starter/buyer-personas.md`, `starter/product.md`, fixtures for each
- Modify: `drafting.py`, `inventory.py`, `constants.py` (append only), `base-kinds.md`, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`, `tests/test_base_reader.py`

**Approach:** As T4.2. The product document separates what has shipped from what is planned, and says where pricing lives rather than restating it.

**Tests:**
- Personas are written to `context/buyer-personas.md` and never under `context/icps/`.
- A persona the sources do not show is not drafted, and the document names the gap.
- The product document separates shipped from planned.
- A figure absent from the sources is refused.

**Done when:** A base owner reads the personas and can tell which persona each segment's deals actually go through.

- [ ] **Unit T4.4: Competitors**

**Goal:** The alternatives buyers consider are kept with their facts, their dates and their sources, so a competitor's move can be recorded and followed through.

**Depends on:** Call 2. The Plan 1 catch-up.

**Files, if call 2 is answered as recommended:**
- Create: `prompts/draft-competitors.md`, `starter/competitors.md`, fixtures
- Modify: `constants.py` (append only: a `competitors` kind after positioning in `BASE_KINDS`, differing by business), `inventory.py`, `base-kinds.md`, `prompts/draft-positioning.md` (its alternatives section becomes the short list with a pointer), the map template's list of context files and its plugin copy, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`, `tests/test_scaffold.py`

**Files, if call 2 keeps competitors in the positioning:** only `prompts/draft-positioning.md` (the alternatives section gains the per-alternative facts with dates and sources) and its tests. No new kind.

**Approach:** Each fact carries a date and where it came from, because a competitor fact without a date cannot be judged stale. A base whose positioning already holds a long alternatives section is offered the move as a proposal to the positioning's owner, never moved on its own. A competitor named with no claim gets an empty section.

**Tests:**
- Every fact in a fixture draft carries a date and a source; one without is refused.
- A competitor named with no claim produces an empty section.
- A base with a long alternatives section is offered the move as a proposal and nothing is written before the owner's yes.
- A change recording a competitor's price change flags the competitors document and not the positioning.

**Done when:** A base owner records a competitor's launch and only the competitors document is flagged.

- [ ] **Unit T4.5: Design (roadmap Unit 2.3)**

**Goal:** A base can hold the visual decisions a piece of work must respect, as prose, not a stylesheet.

**Depends on:** Call 3 (D6). The Plan 1 catch-up. Material: M3 for Gridwise.

**Files:**
- Create: `prompts/draft-design.md`, `starter/design.md`, fixtures
- Modify: `drafting.py`, `inventory.py`, `constants.py` (append only), `base-kinds.md`, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`

**Approach:** Four sections (colour by role, type, logo rules, forbidden devices), with tone left to the voice document. The forbidden-devices section is present and may be empty, because an empty forbidden list is a real answer.

**Tests:**
- Fixture sources produce the four sections and no colour code the sources lack.
- Sources with no logo rules produce a document that names the gap.
- No image, font or binary is written into the base.
- The file is read, owned, confirmed and flagged like any other.

**Done when:** A person handed the design document and a draft asset can say whether the asset respects it.

## Group 2: the sources-of-truth file, and keeping GTM Base current

The roadmap's "sources-of-truth file" is `access/stack.md`, renamed by the CLASS layout on 2026-09-25. It answers, for each kind of data a job needs, where it lives, which connected tool reads it, and what to do when that tool is not connected. Plan 1's Unit 2.5a built its parser and its five columns (kind of data, business, where it lives, which tool reads it, the fallback) and drafts the driver-app rows for Gridwise only. Nothing reads a source over the network at context time, and no row ever holds a credential.

- [ ] **Unit T4.6: The source map for any company (roadmap Unit 2.5, the general half)**

**Goal:** Any base owner can have the source map's rows drafted from what they say and approve them, so a skill knows where the data it needs lives and says so when it cannot reach it.

**Depends on:** The Plan 1 catch-up (2.5a's parser and prompt).

**Files:**
- Modify: `prompts/draft-stack-rows.md` from Plan 1 (asks a company with no driver app: which tools hold spend, pipeline, customer conversations and product usage, and which connected tool reads each), `inventory.py` and `constants.py` (append only: the source map draftable), the setup closing in `skills/join/SKILL.md` (offers the source map once, after the two setup documents, never as a required step), `base-kinds.md`, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_stack.py`, `tests/test_inventory.py`, `tests/test_join_setup_flow.py`

**Approach:** The rows are drafted from the person's answers and the material they name, never from guessing which tools a company of that size usually has. A tool nobody named is not a row. A skill that declares the source map reads the rows for the kinds of data its job needs and names a missing row as a gap. The source map also gains a short section listing the base's own skills and the tools each needs installed, which Plan 1's requirement CS24 already asks for in words.

**Tests:**
- A person's answers produce rows with all five columns; a row missing its fallback is reported incomplete.
- A tool the person did not name never appears in a draft.
- A line shaped like a key or token is refused.
- The setup closing offers the source map once and a base without it is still complete.

**Done when:** A base owner can answer "where does our pipeline data live, and what reads it?" from the file alone.

- [ ] **Unit T4.7: Update GTM Base (roadmap Unit 2.6)**

**Goal:** A person can say "update GTM Base" and be told, in one sentence, the installed version and the one step that updates it, and is told which new kinds and starter skills their base can now take.

**Depends on:** Call 4 (D7). The Plan 1 catch-up, for the inventory part.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/update_check.py`, `tests/test_update_step.py`
- Modify: `skills/stale-check/SKILL.md` (the entry point), `inventory.py` (after an update, lists kinds and starter skills the base does not yet hold, as offers), `docs/join-guide.md` (the plugin does not refresh on its own), `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_state.py`, `tests/test_inventory.py`

**Approach:** Two halves. The plugin half reads the version in `plugins/gtm-base/.claude-plugin/plugin.json`, prints it with the one update step, makes no network call and claims nothing about a newer release existing (call 4). The update step is checked against Claude Code's documentation when the unit is built, not written from memory. The base half is what keeps an existing base current with the plugin: because starters live in the plugin, a base never receives a new kind or starter skill by itself, so after an update the inventory lists what is newly available and offers each through an owner-approved creation. Nothing is written on its own. People in Claude chat, Cowork and ChatGPT need neither half, because the connector serves from the base on every call.

**Tests:**
- The sentence names the installed version and the step, and runs no install command.
- The version cannot be read: one sentence and a recorded code, no guess.
- After a version that adds a kind, the inventory lists it as available and writes nothing.
- Running it twice says the same thing twice.

**Done when:** Brandon updates his own installed plugin by following the printed sentence and nothing else, which also closes the roadmap's Track 5 item "update the installed plugin".

## Group 3: the first skills that use a base

### Which skill comes first: drift grade

**Recommendation: build drift grade first. The runner-up is the outbound sequence.**

Drift grade takes a piece of marketing work (a page, an email, a post, an ad) and checks it against the base's approved versions: does every claim match what the positioning and messaging currently say, does it speak to the profile the team has approved, does it sound like the voice guide. It ends in one of two places: fixes to the piece, or, when the evidence says the buyer has moved, a proposed change to the context.

Why it should be first:

1. **It is the product's own promise, demonstrated.** The messaging reframe names the pain as output that is off-message and off-brand because nobody knows which version is approved. Drift grade is that check, run on demand. A content brief or a sequence shows that an AI can write from context, which every competitor in the reframe's table also shows. Drift grade shows that the base knows which version is approved and catches work that is not on it.
2. **It shows all three pillars in one demo through the connector.** In a chat Project, a person pastes their homepage and asks for a grade. The connector serves the skill with the profile, positioning, messaging and voice (C3). If a recorded decision has overtaken the positioning, the flag and its three choices appear before any grade (C2). If the grade finds the buyer has moved, it ends in a proposal the owner accepts in the web app (C4). Neither Notion Skills nor Calven claims the second or third step.
3. **It works on the smallest base.** It needs only the profile and the positioning, which every base has after setup, and names messaging and voice as gaps when they are missing. The outbound sequence also needs a rules file, a target segment and a real account; the content brief needs voice to be useful.
4. **It carries the least risk in a demo.** It reads no prospect data, sends nothing, and needs no tool beyond the base. The outbound sequence handles prospect names, which the screens cannot reliably catch (Plan 1, Unit 1.4c execution note).
5. **The pipeline line is short.** In a consulting sprint, grading the prospect's own live copy against the positioning they just approved is the moment the problem becomes theirs. That is the demo GTM Base is for as a lead magnet.

Why the outbound sequence is the runner-up and not first: it is the shortest line from a base to a customer's pipeline (a sequence, then sends, replies and meetings), and SC-C is its test. But C3's need is a demo that shows what is different about GTM Base, and a well-grounded sequence looks like what any AI writes. It is built third, and SC-C stays its success test.

### How a starter skill reaches a base

All three skills ship in the plugin as starter skills, beside Plan 1's document starters, and reach a base only through Plan 1 Unit 4.2b's install: the whole skill folder shown as one manifest, the contract check passing first, the creator's yes and the base owner's or an administrator's yes. From then on the skill is an ordinary company skill in `skills/<job>/`, owned by the person who installed it, changed only through a prepared change its owner approves, and served by the connector as the approved version (call 7). Its rules live in `standards/<job>.md`, installed with it, so a company that grades copy differently changes its standard, not the plugin.

One requirement follows for C3. The skill's own `SKILL.md` must not call the runner's commands itself. In Claude Code, Plan 1's `use-skill` wraps any base skill in the runner's `start` and `finish`; in chat, the connector serves the skill with its documents and their flags. A skill body that named `python3` commands would break in chat, so the starter skills keep their procedure in plain instructions and leave the runner to whatever serves them. The figure lint and the contact screens in `finish` therefore run in Claude Code only; in chat the connector cannot screen what the model writes, and C3's plan should say so.

- [ ] **Unit T4.8: Drift grade (roadmap Unit 3.2), built first**

**Goal:** Check a piece of marketing work against the base's approved versions and end in fixes to the piece or a proposed change to the context, in Claude Code through the runner and in chat through the connector.

**Depends on:** Plan 1 Units 3.1 and 4.2b merged. Plan 1 Unit 3.5's standard kind (for the digit lint), or this unit applies the same rule in its own test if 3.5 has not merged. Not on T4.2: messaging and voice are optional reads.

**Files:**
- Create: the starter skill `plugins/gtm-base/starter/skills/drift-grade/` holding `SKILL.md`, `references/what-to-check.md`, and `examples/<example>/` folders in CS19's shape (the exact sub-path under `starter/` is set by 4.2b's install operation, which reads it), the starter standard `starter/standards/drift-grade.md`, `tests/test_drift_grade.py`, `tests/fixtures/base-skills/drift-grade/` (a synthetic company, written from scratch)
- Modify: `inventory.py` (offers drift grade to a base that holds a profile and a positioning), `constants.py` (append only), `base-kinds.md`, `plugins/gtm-base/CHANGELOG.md`
- Test: `tests/test_runner_contract.py`, `tests/test_skill_install.py`

**Approach:**
- *Declarations.* Required: the standard `standards/drift-grade.md`, `context/icps.md` and `context/positioning.md`. Optional: the named segment under `context/icps/`, `context/messaging.md`, `context/voice.md`, `context/competitors.md` (or the positioning's alternatives, per call 2) and `context/buyer-personas.md`. Each missing optional document is a named gap in the grade.
- *The standard* uses Plan 1's five sections in words and no digits: the job's goal (work on the approved version), what is unacceptable (a claim the positioning or messaging no longer carries, a claim with no source in the base, a competitor comparison the base does not support, an audience the profile does not name), what needs approval (any change to the context, always as a proposal), the checks before the grade is handed back (every finding quotes the line in the piece and the line in the base it was judged against), and how a verdict relates to the base.
- *The output.* A verdict in plain words (on the approved version, drifting, or off it), then each finding with the line in the piece, the document and line in the base, and the fix. When several findings point the same way and the piece carries evidence the base does not (a customer quote, a new use case), the grade ends with a proposed context change instead, with that evidence quoted, through propose-change in Claude Code or C4 in chat. It never edits a context document.
- *Examples.* At least three, on the synthetic company: a piece that matches (no findings, no proposal), a piece using a value proposition the positioning dropped (fixes), and a piece carrying evidence that the buyer moved (a proposal). Each has an expectations file (the verdict, the documents each finding must cite, whether a proposal is expected) and a deliberately wrong output (a finding citing a document that was not read; a grade that edits the positioning instead of proposing).

**Tests:** These check written outputs and the shape; judgment is Brandon's replay.
- The starter passes the contract check, and each wrong output fails it.
- Installing it into a fixture base needs both yeses and writes the folder and the standard as one manifest.
- On a base without messaging, the runner returns ready with gaps, and the skill's instructions name the gap.
- With the positioning flagged, an attended run returns the moment-of-use block and no grade.
- The standard carries no digit outside a date.
- The skill body names no command, so the same text can be served by the connector.

**Done when:** Brandon runs it on a real piece of copy in the demo base (call 6), agrees with the verdict and with the one change it asked for, and the same skill is served through the connector in a chat Project once C3 is built.

- [ ] **Unit T4.9: Content brief (roadmap Unit 3.3)**

**Goal:** A brief a writer can work from, grounded in the base, with the gaps named rather than filled.

**Depends on:** T4.8 (the starter-skill pattern proven once), T4.2 (voice and messaging, which a brief is not useful without). Material: M10.

**Files:** As T4.8, for `content-brief`: the starter skill, `starter/standards/content-brief.md`, `references/brief-shape.md`, examples, a fixture and `tests/test_content_brief.py`.

**Approach:** Declares the profile and positioning (required), the named segment, messaging, voice, buyer personas and design (optional). The brief names the audience, the one claim the piece makes and its proof from the messaging, the persona it speaks to, the voice rules that matter most for the channel, and every gap. The roadmap's version also read other work in flight; that is cut (Fable M8).

**Tests:**
- A brief for a named segment uses that segment's language, not the profile's general version.
- A segment with no file produces a brief against the profile that says so.
- Voice missing produces a named gap, never a generic voice.
- The examples pass and the wrong outputs fail.

**Done when:** A writer handed the brief and nothing else produces a draft its owner does not have to re-brief.

- [ ] **Unit T4.10: Outbound sequence (roadmap Unit 3.4, as the reviewed Unit 1.4c text)**

**Goal:** A sequence grounded in one segment's own language, with every claim traced to the base.

**Depends on:** T4.8. T4.6 helps (the source map names the sending tool) but is not required. Material: M11.

**Files and approach:** The reviewed Unit 1.4c text at the end of the 2026-09-19 roadmap holds, with two changes. Its rules file is `standards/outbound-sequence.md`, installed with the skill through 4.2b rather than offered as a separate proposal, and the skill reaches the base as a starter skill like T4.8. Every claim names the document behind it in a short table under the sequence; a claim with no grounding is dropped and the drop reported. It reads no prospect data from the base, because the base holds none.

**Tests:** As Unit 1.4c lists them, run through the contract test.

**Done when (SC-C):** Brandon runs it on a real base, can point at the document behind every claim, uses the sequence in real outreach, and the walkthrough records what was sent, what he changed first, and what came back. No result is written before it happens.

## The order

| Step | Units | Waits on | Why |
|---|---|---|---|
| 0, now | Brandon's material (M1 to M5, M9) or the demo base's material; drift grade's examples and standard written as plain documents | Calls 1, 6 | Nothing here touches code the catch-up is moving |
| 1 | T4.1, T4.2, T4.3, T4.6 in parallel | The Plan 1 catch-up merged | Each touches its own prompt and appends to `constants.py` |
| 2 | T4.8 drift grade | Plan 1 Units 3.1 and 4.2b merged | C3 needs a real skill to serve |
| 3 | T4.4, T4.5, T4.7 | Calls 2, 3, 4 | None blocks the connector |
| 4 | T4.9, then T4.10 | T4.8, T4.2 | Both follow the pattern drift grade proves |

Files shared across units: `constants.py` and `tests/support.py` are append only, as in Plan 1. `drafting.py`, `inventory.py` and `base-kinds.md` are touched by several units, so units that run in parallel each add their own variant or section and nothing else, and the orchestrator merges them one at a time with the suite run after each.

## How we know Track 4 is done

1. On the demo base (call 6), Brandon asks "what is my base missing?" and drafts messaging, voice, personas and the source map from the inventory's offers, each approved by him.
2. He records a decision about the profile and is offered the positioning, messaging and personas without naming them (T4.1).
3. He runs drift grade in Claude Code on a real piece of copy, with one document flagged, and sees the flag before any grade.
4. Once C3 is built, the same drift grade runs in a Claude chat Project and in ChatGPT through the connector, with the same documents, and its proposal is accepted in the web app once C4 is built.
5. SC-C passes for the outbound sequence, recorded only from what happened.

## Review standard

Units get no review of their own (Brandon's rule), and the run above is the main check. Track 4 adds no sign-in, token, or path onto another person's computer: the skills folder's trust rules and the install operation are Plan 1's (4.2b), which carry their own security pass. So Track 4 needs no security review of its own. If C3's security review finds that a crafted starter skill could make a chat conversation do something it should not, the fix lands in the starter, and that is its one look.

## The line to pipeline, and the gap

The mechanism is the demo. GTM Base is a lead magnet for Brandon's consulting and for MICW, and the consulting sprint is where a prospect sees it work on their own material. Drift grade on the prospect's own live copy, through the connector in the tools they already use, is the moment the standardization problem becomes theirs. The outbound sequence adds a second line, this time inside the customer's business: a sequence, then sends, replies and meetings, which SC-C records.

Two gaps stay open, and this plan does not close them. The messaging reframe's five-call test (does a marketing lead have a story about AI working from an outdated document) has not been run, so the pain is still inferred. And the paid next step after the lead magnet is not yet defined, which the reframe names as the gap to close before launch. Drift grade is a better demo for the first gap, because a prospect can see their own copy fail, but it does not replace the calls.

## For Brandon

| # | The call | Recommended | Runner-up | Needed before |
|---|---|---|---|---|
| 1 | Which skill is built first | **Drift grade**, for the five reasons above: it demonstrates the standardization promise, shows the flag and the proposal in one chat demo, works on a base with only setup's two documents, handles no prospect data, and is the strongest demo in a consulting sprint | The outbound sequence, which is the shortest line to a customer's pipeline but looks like what any AI writes | T4.8 |
| 2 | Competitors as their own document or a section of the positioning (reopens call 10 of 2026-09-25) | **Their own document**, `context/competitors.md`, with the positioning keeping a short list of alternatives. Competitor facts change far more often than positioning, and in one file every competitor price change would flag the positioning and interrupt every skill that reads it | Keep them in the positioning's alternatives section, as decided on 2026-09-25. Simpler, one fewer document, but the flag fires on the positioning far more often | T4.4 |
| 3 | The design document's sections (D6, open since 2026-10-10) | **Four sections: colour by role, type, logo rules, forbidden devices. Tone left to the voice document**, so it lives in one place | The five sections in the roadmap, tone included | T4.5 |
| 4 | How "update GTM Base" knows a newer version exists (D7, open since 2026-10-10) | **It does not try.** It prints the installed version and the one update step and makes no network call, keeping the promise that the plugin reads nothing over the network | One network check, only when asked, answering "unknown" when it fails | T4.7 |
| 5 | The product document, which no group in Track 4 names | **Add it to T4.3 with buyer personas**, since both draft from the same sales material and the messaging and content brief lean on it | Leave it for later; the inventory keeps reporting it missing | T4.3 |
| 6 | Which base holds the first real runs and the C3 demo | **GTM Base's own company base**, built from its own material (the messaging reframe, the ICP page, the landing page draft). It holds no client data, so it can be shown to anyone, and drift grade on the current README, which still says "context files an AI can read", is a real finding the reframe already made by hand | The Gridwise base. Real daily use, but it is client material, which keeps it out of demos and out of this public repository's fixtures | Step 0 |
| 7 | Starter skills: installed into a base and owned by the company, or kept in the plugin | **Installed into a base through 4.2b**, so the company owns its copy, can change its standard, and the connector serves the approved version. This is the standardization the product sells: approved processes, not ours | Plugin-only skills a base cannot change. Simpler, but the connector could not serve them as the company's approved version, and C3 has nothing to serve | T4.8 |
| 8 | Whether recording a change preselects the documents it probably overtakes | **Suggest, never preselect.** The person still chooses, so nothing is flagged they did not mean to flag, and a wrong suggestion costs one sentence | Preselect the suggested documents and let the person untick | T4.1 |
| 9 | Drift grade may be installed in a base before the Meta skill (D2 made Meta the first skill on the base) | **Yes.** D2's reason holds for the runner's nightly test, and Meta still runs SC-M. Drift grade being first into a base changes nothing about that, and C3 cannot wait for the Meta plan's dry-run nights | Hold drift grade until the Meta skill is installed, which ties C3 to the Meta plan's Unit 8a | T4.8 |
| 10 | Linking documents that live in Notion, Google Docs and Drive, or Obsidian, which the second launch gate of 2026-11-25 requires before the landing page goes live | **Its own track, starting with a spike** on whether Notion's and Google's APIs let a base put owners, approvals and flags on a document it does not hold. Track 4 builds documents held in the base and nothing about linked ones | Fold it into Track 4, which would hold every unit here behind an unverified API question | Before the landing page goes live |

## Out of scope

- Linking or governing documents that live outside the base (call 10).
- Metric definitions, and the Analytics halves of goals and the source map for Gridwise. Metric definitions are Plan 1 Unit 2.4a in Track 3, and the Analytics halves need M6 to M8 answered.
- Noticing a change on its own from calls, deals or the market. The connector plan decided this is not a product feature.
- Reading work in flight (Fable M8).
- Any script file in a base (CS24).
- Lessons from results, beyond what Plan 1 Unit 3.6 already builds for the Meta skill.

## Sources

- Roadmap to the full experience: `docs/plans/2026-11-26-003-roadmap-to-full-experience.md`
- The roadmap after Phase 1 and its review findings: `docs/plans/2026-09-19-002-roadmap-after-phase-1.md`
- Plan 1, revision 2.9, and the company-skills requirements, signed 2026-10-10: on branch `claude/plan-1-meta-skill-3d436e`
- The decisions of 2026-10-10 (D2, D4, D5, D6, D7, M1 to M12): `docs/plans/2026-10-10-001-phase-2-3-decisions.md` on the same branch
- The built Plan 1 units: branch `claude/plan-1-read-side-6c5559`
- The connector plan and its spike results: `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`
- The positioning: `docs/ideation/2026-11-24-messaging-reframe.md` and `docs/ideation/2026-11-24-icp/` (untracked in the main checkout)
- The code read for "where things stand": `plugins/gtm-base/lib/gtmbase/moment.py`, `stale.py`, `record_change.py`, `constants.py`, `plugins/gtm-base/skills/stale-check/SKILL.md`, and `templates/company-base/`, on main at 44b6fab
