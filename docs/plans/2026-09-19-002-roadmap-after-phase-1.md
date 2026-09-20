---
title: "Roadmap after Phase 1: what a base holds, the other skills, and company skills"
type: roadmap
status: parked
date: 2026-09-19
origin:
  - docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md (revision 1, Phases 2 to 4, moved here unchanged by revision 2)
  - docs/reviews/2026-09-19-plan-review-astra.md
  - docs/reviews/2026-09-19-plan-review-fable.md
---

# Roadmap after Phase 1

This file is not an implementation plan. Both reviews of the build plan (Astra and Fable 5.1, 2026-09-19) said that twenty units across four phases is the wrong shape for one plan, so revision 2 of the build plan keeps Phase 1 plus the runner and the first skill, and the units below were moved here word for word. Each phase becomes its own plan, written after the first skill has been used on real work at Gridwise, because that use will change what the inventory and the rubric files need to hold.

**Order, set by Brandon on 2026-09-19: all of the context goes into the base first, and skills that use it come after.** So the next plan after Phase 1 is what a base holds (the inventory, then messaging, voice, design, competitors, personas, metric definitions, goals, and the sources-of-truth file), and the runner and the skills follow it. Revision 2 of the build plan briefly pulled the runner and the outbound sequence forward as Units 1.4b and 1.4c; revision 2.1 moved them back here. Their revision 2 text, which already carries the review fixes, is at the end of this file and replaces Units 3.1 and 3.4 below. The success criterion for the first skill (SC-C in the build plan) is that one output is used in real work and what happened is recorded.

## Review findings to fold in when each plan is written

Nothing below is decided again here. These are the reviewers' findings about the moved units, kept beside them so the next planning session starts from them.

| Finding | Units | What the next plan must do |
|---|---|---|
| Astra 8 | 2.2 to 2.5, 3.2, 3.3 | Optional kinds and rubrics must not sit in the company-base template, because base creation copies the whole tree and absent-only adoption then refuses the destination, and an existing base never receives them. Keep starter content in the plugin, put it in a base only through an owner-approved request, and provide rubrics to existing bases without overwriting a customized one. Test a fresh base and an upgraded one. Unit 1.4c in the build plan sets the pattern. |
| Astra 11, Fable M6 | 2.6 | Two local version readings cannot show that a newer release exists. Either always print the one refresh step with the installed version and claim nothing about being current, or allow one on-request network read and answer "unknown" when it fails. |
| Astra 12, Fable M7 | 3.2, 3.3 | Approved examples must test judgment: required claims, segment identity, contradiction found or not, proposal or no proposal, plus deliberately wrong outputs that must fail. Unit 1.4b in the build plan sets the contract. |
| Fable M8 | 3.2, 3.3 | Both read `context/work/`, which exists in neither the template nor the real base, and no kind fills it. Cut the in-flight contradiction feature or add the kind first. |
| Astra test table | 3.2 to 3.4 | A fence assertion cannot prove a model did not follow an instruction, and the screens do not catch arbitrary prospect names or unsupported claims. Keep deterministic screening tests apart from model-behavior and grounding evaluations. |
| Fable, low | 3.1 | `skills/references/thin-runner.md` puts a folder without a `SKILL.md` beside the skills. Resolved in Unit 1.4b. |
| Open questions 2, 3, 5, 7 | 2.1, 2.3, 4.1, atlas | Both reviewers say these wait for the Phase 2 and later plans: the design file's sections, the closed list of kinds, new atlas figures for skills, and whether the company-skills brainstorm may reopen the trust-surface refusal set. |

## The moved units, unchanged from revision 1

### Phase 2: what a base holds

Starts after Phase 1 ships. Setup stays at two documents throughout.

- [ ] **Unit 2.1: The base inventory**

**Goal:** A person can ask "what is my base missing?" and get a short answer against a named list, with the offer to adopt or draft each one.

**Requirements:** P30, P28.

**Dependencies:** 1.4 (the vocabulary), 1.7 (adoption).

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/inventory.py`, `plugins/gtm-base/skills/stale-check/references/base-kinds.md`, `tests/test_inventory.py`
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py` (`BASE_KINDS`: ordered, each with destination path, adoptable, draftable), `plugins/gtm-base/lib/gtmbase/stale_check.py` (the inventory is part of the review), `plugins/gtm-base/skills/stale-check/SKILL.md` ("what is my base missing?")
- Test: `tests/test_stale_check.py`, `tests/test_scaffold.py`

**Approach:** The inventory is a read over `base_reader.context_files` against `BASE_KINDS`, returned as a small table: the kind, whether the base has it, and when it was last confirmed. It offers adopt or draft per kind on request and does nothing on its own. The reference file says in plain words what each kind is for and what a good one contains, and a test holds the constant and the reference in step.

**Patterns to follow:** The review's one-list-in-one-sitting shape; the map-settings-and-reference pattern.

**Test scenarios:**
- Happy path: a base with the two setup files reports the other kinds as missing, in the stated order, as a table.
- Happy path: a base holding messaging reports it present with its last confirmation date.
- Edge case: a kind present but carrying an unanswered marker is reported as present and not confirmed.
- Edge case: a kind whose file exists with `status: skipped` is reported as skipped, not present.
- Error path: an unreadable file is reported as unreadable and does not make the kind missing.
- Integration: every entry in `constants.BASE_KINDS` has a section in `base-kinds.md` and every section has an entry.

**Verification:** Brandon asks the question on the Gridwise base and gets a table he can act on without a follow-up question.

**Atlas: figure 1.**

- [ ] **Unit 2.2: Messaging and voice, adopted or drafted**

**Goal:** The two kinds Brandon wants first in his own base arrive through the same guarded path as segments.

**Requirements:** P30, P20, P21, P28.

**Dependencies:** 2.1.

**Files:**
- Create: `plugins/gtm-base/skills/join/references/prompts/draft-messaging.md`, `draft-voice.md`, `templates/company-base/context/strategy/messaging.md` and `voice.md` (and the plugin-side copies), `tests/fixtures/drafts/messaging.md`, `voice.md`
- Modify: `plugins/gtm-base/lib/gtmbase/drafting.py` (two explicit document variants), `plugins/gtm-base/lib/gtmbase/inventory.py`, `plugins/gtm-base/lib/gtmbase/constants.py`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`, `tests/test_review.py`, `tests/test_prompt_guards_join.py`

**Approach:** Both kinds go through the adoption contract when a finished document exists and through a drafting prompt when it does not. The voice prompt is the one place where verbatim-first matters most, because a voice document written in the model's voice is worse than none, so it quotes the person's own sentences and marks anything it could not ground. Neither is required, and skipping either leaves the base complete.

**Patterns to follow:** The donor's verbatim-first rules and banned-word list already in `draft-positioning.md`; the always and only-if-signal section rule from `draft-icp.md`.

**Test scenarios:**
- Happy path: fixture sources produce a messaging document with no invented claim and a voice document quoting the sources' own sentences.
- Edge case: sources with nothing about voice produce a document that says which sections had no signal rather than filling them.
- Security: a draft carrying a contact detail is returned to the same step; a draft with a long dash or a banned word is refused.
- Happy path: a finished messaging document is adopted under the full contract, with its original metadata discarded.
- Edge case: skipping voice leaves the base complete and the inventory reports it skipped.
- Integration: both files are read by `base_reader`, owned, confirmed, and flagged by a change that affects them.

**Verification:** Brandon's own base holds a messaging document and a voice document he would send to a writer.

**Atlas: figure 1.**

- [ ] **Unit 2.3: The design file**

**Goal:** A base can hold the visual decisions a piece of work has to respect, as a context file rather than a stylesheet.

**Requirements:** P30, P28. Section list pending Brandon's answer to open question 2.

**Dependencies:** 2.2.

**Files:**
- Create: `templates/company-base/context/strategy/design.md` and the plugin-side copy, `plugins/gtm-base/skills/join/references/prompts/draft-design.md`, `tests/fixtures/drafts/design.md`
- Modify: `plugins/gtm-base/lib/gtmbase/drafting.py`, `constants.py`, `inventory.py`, `plugins/gtm-base/skills/stale-check/references/base-kinds.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`

**Approach:** The proposed sections are modeled on `brandkit/brand-lock.json`, which is a decided record with a forbidden list rather than an asset bundle: palette (named roles, not hex lists for their own sake), type (display, body, metadata families and how each is used), logo rules (construction, colour, the one-ink treatment, what may never be done to it), forbidden devices, and tone. It stays prose a person can confirm, with no code in it, because a stylesheet is an artifact and this is context about artifacts. Assets themselves stay out of the base.

**Patterns to follow:** `brandkit/brand-lock.json`'s own structure, read as a model and not imported.

**Test scenarios:**
- Happy path: fixture sources produce a design document with the agreed sections and no invented hex value.
- Edge case: sources with no logo rules produce a document that names the gap instead of inventing a rule.
- Security: no image, font, or binary is written into the base by this path.
- Edge case: the forbidden-devices section is present and empty rather than omitted, because an empty forbidden list is a real answer.
- Integration: the file is read, owned, confirmed, and flagged like any other context file.

**Verification:** A person handed the design file and a draft asset can say whether the asset respects the base.

**Atlas: figure 1.**

- [ ] **Unit 2.4: Competitors, personas, metric definitions, goals**

**Goal:** The remaining kinds arrive through the same path, with the honest limit on the two that depend on numbers.

**Requirements:** P30, P31 (the dependency), P28.

**Dependencies:** 2.1.

**Files:**
- Create: `templates/company-base/context/strategy/competitors.md`, `context/strategy/personas/.gitkeep`, `context/metrics/definitions.md`, `context/plan/goals.md` and the plugin-side copies, `plugins/gtm-base/skills/join/references/prompts/draft-competitors.md`, `draft-persona.md`, `draft-metric-definitions.md`, `draft-goals.md`
- Modify: `plugins/gtm-base/lib/gtmbase/drafting.py`, `constants.py`, `inventory.py`, `plugins/gtm-base/skills/stale-check/references/base-kinds.md`
- Test: `tests/test_drafting.py`, `tests/test_inventory.py`, `tests/test_base_reader.py`

**Approach:** Competitors and personas draft from the person's own material exactly as the other kinds do, with personas kept explicitly distinct from segments. Metric definitions and goals are different and the prompts say so: a definition of a new customer or of the price payback divides by is a decision the person states, and a target is a number that lives in a model outside the base. Both prompts therefore ask rather than infer, and both refuse to write a number the sources did not carry. This is the doctrine's own line: targets stay in the model, the judgment about targets lives in context, and the map points between them, which is what Unit 2.5 builds.

**Patterns to follow:** The never-hallucinate and leave-empty rules from the donor prompts; the standing rule against an invented number.

**Test scenarios:**
- Happy path: fixture sources produce a competitors document and one persona file, with personas written to `context/strategy/personas/` and never to `segments/`.
- Edge case: a source naming a competitor with no claim about it produces a named competitor and an empty claim section rather than an invented claim.
- Security: a metric definitions draft that contains a figure absent from the sources is refused and returned to the same step.
- Edge case: a goals draft with no target in the sources produces the definition and the question, never a number.
- Edge case: the inventory distinguishes personas (a folder that may hold many) from the single-file kinds.
- Integration: all four are read, owned, confirmed, and flagged like any other context file.

**Verification:** The metric definitions file in Brandon's base states the payback price rule he actually uses and cites where the number lives, without restating the number.

**Atlas: figure 1.**

- [ ] **Unit 2.5: The sources-of-truth file**

**Goal:** The map grows up. For each kind of data: where it lives outside the base, which connected tool reads it, and the fallback. Nothing reads it over the network at context time.

**Requirements:** P31, P28, P35.

**Dependencies:** 2.1, 2.4.

**Files:**
- Create: `templates/company-base/context/sources-of-truth.md` and the plugin-side copy, `plugins/gtm-base/lib/gtmbase/truth_map.py` (parse and validate the rows), `plugins/gtm-base/skills/join/references/prompts/draft-sources-of-truth.md`, `tests/test_sources_of_truth.py`
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py`, `inventory.py`, `plugins/gtm-base/skills/stale-check/references/base-kinds.md`, `templates/company-base/context/map.md` and the plugin-side copy (the "where things live" paragraph points at the new file and the map stays settings only)
- Test: `tests/test_inventory.py`, `tests/test_base_reader.py`, `tests/test_session_start.py`

**Approach:** One row per kind of data, with four columns: the kind, where it lives, which connected tool reads it, and the fallback when that tool is not connected. It is an ordinary context file, owned and confirmed, so it goes stale like everything else and the existing machinery catches it, which is the point. `truth_map.py` parses it for the skills that will use it and validates the shape; it never calls anything. The map keeps its two settings and gains a pointer, which preserves the settings-only contract Codex defended in condition E.

**Patterns to follow:** The map's settings parser and its range checks; the rule that context reads stay local.

**Test scenarios:**
- Happy path: a well-formed file parses into rows with all four columns; a row missing the fallback is reported as incomplete rather than accepted.
- Security: parsing makes no network call and no git call that reaches a remote, asserted with a runner that fails on any fetch.
- Edge case: a row naming a tool that is not connected on this seat is still valid, because the file is the team's record and not this seat's inventory.
- Edge case: session start injects the map and does not inject the sources-of-truth file, keeping the injection cap intact.
- Integration: the file is flagged by a change that affects it and confirmed like any other context file.

**Verification:** Brandon can answer "where does our spend data actually live and what reads it?" from the file alone.

**Atlas: figures 1 and 2.**

- [ ] **Unit 2.6: Update GTM Base**

**Goal:** A person can say "update GTM Base" and be told, in one sentence, the one thing to do.

**Requirements:** P32, P28.

**Dependencies:** 1.3.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/update_check.py`, `plugins/gtm-base/templates/update-step.md`, `tests/test_update_step.py`
- Modify: `plugins/gtm-base/skills/stale-check/SKILL.md` (the entry point), `docs/join-guide.md` (a section saying the plugin does not refresh on its own)
- Test: `tests/test_state.py`

**Approach:** Compare the version in `plugins/gtm-base/.claude-plugin/plugin.json` as the seat has it recorded against what the seat last recorded, print one sentence naming the step, and stop. It changes nothing itself, for the reason in the decisions table. The exact command is verified against the documentation at build time rather than written from memory.

**Patterns to follow:** The install sentence the hook wrapper prints when prerequisites are missing: one sentence, one step, exit cleanly.

**Test scenarios:**
- Happy path: a seat whose recorded version is behind gets the one sentence naming the step.
- Happy path: a seat that is current is told so in one sentence and nothing else happens.
- Security: the step runs no install command and writes nothing outside the seat's own records.
- Error path: the version cannot be read: one sentence, a recorded code, no guess.
- Integration: running it twice in a session says the same thing twice and changes nothing.

**Verification:** Brandon updates a seat by following the printed sentence and nothing else.

**Atlas: figure 2**, pending Brandon's answer to open question 5 about whether this earns a figure of its own.

### Phase 3: skills that use the base

Starts after Phase 2's inventory and Unit 2.2 have shipped, because a skill that reads voice and messaging needs them to exist. These ship in the core plugin ahead of backup and invite.

- [ ] **Unit 3.1: The thin-runner pattern and the examples-as-tests harness**

**Goal:** One shape for every skill that uses the base, and a way to execute an owner-approved example as a test.

**Requirements:** P33, P28, P9.

**Dependencies:** 1.3 (the moment-of-use check), 1.7, 2.1, 2.2.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/runner.py` (read the named context files, call `moment.check` on each, assemble the request with the rubric, screen the output, hand back the work product), `plugins/gtm-base/skills/references/thin-runner.md` (the pattern, written once and referenced by each skill), `tests/test_skill_examples.py` (the harness)
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py`, `tests/support.py` (a helper that builds a base holding a named set of context files)
- Test: `tests/test_moment_of_use.py`

**Approach:** The runner is the only place a skill touches the base, which keeps every skill thin and keeps the moment-of-use check from being something each skill remembers to do. An example is an input, the context files it was run against, and an owner-approved output. The harness asserts the deterministic parts: which context files were read, that the moment-of-use check ran for each, that the rubric came from a context file and not from the skill body, that the output carries no contact detail and no long dash, and that a missing context file produces the named gap rather than a guess. It does not assert model prose, because that would be a snapshot test over a non-deterministic output.

**Execution note:** Decide what the harness asserts before writing any skill, so the three skills are built against a fixed contract rather than the harness being widened to fit them.

**Patterns to follow:** `drafting.assemble` and `review.screen` as the two ends of an existing pipeline; the fenced data-not-instructions rule on every source.

**Test scenarios:**
- Happy path: a fixture skill declaring three context files reads exactly those three and calls `moment.check` on each.
- Edge case: a declared file missing from the base produces a named gap in the output and does not stop the run.
- Edge case: a declared file that is flagged produces the moment-of-use block before the work product.
- Security: a context file carrying an instruction sentence is fenced as data and the assertion covers the fence; the output is screened for contact details and keys before it is handed back.
- Happy path: an example folder with one input and one approved output runs and passes; changing the declared context file list fails it.
- Error path: a rubric named by a skill but absent from the base: the skill reports it and does not substitute its own judgment.

**Verification:** A fixture skill written against the pattern needs no code of its own beyond its declarations and its prompt.

**Atlas: figure 1**, pending open question 5.

- [ ] **Unit 3.2: Drift grade**

**Goal:** Score an artifact against the base's strategy and end in one of two places: a fix to the artifact, or a proposal to the context when the buyer has moved.

**Requirements:** P33, P28, P13.

**Dependencies:** 3.1.

**Files:**
- Create: `plugins/gtm-base/skills/drift-grade/SKILL.md`, `scripts/drift_grade.py` (a shim), `references/rubric-source.md`, `examples/`, `templates/company-base/context/strategy/messaging-rubric.md` and the plugin-side copy, `tests/test_drift_grade.py`
- Modify: `plugins/gtm-base/lib/gtmbase/constants.py`, `inventory.py` (the rubric is a kind), `plugins/gtm-base/skills/stale-check/references/base-kinds.md`
- Test: `tests/test_skill_examples.py`

**Approach:** Reads `context/strategy/icp.md`, the relevant `segments/`, `positioning.md`, `messaging.md`, `voice.md`, and `context/work/` for what else is in flight, so it can report a contradiction between two pieces rather than only a drift from strategy. The rubric lives in `context/strategy/messaging-rubric.md` and the skill is a runner over it. Its second output is a proposal, never an edit, which is P13.

**Patterns to follow:** The parent scope's drift-grade description, including reading across `context/work/`; the proposal path in `compose_proposal.py`.

**Test scenarios:**
- Happy path: an artifact matching the base scores clean and produces no proposal.
- Happy path: an artifact using a value proposition the positioning no longer carries produces a fix to the artifact.
- Happy path: evidence that the buyer moved produces a proposal to the context, with the evidence quoted, and no edit.
- Edge case: two pieces in flight that contradict each other are reported as a contradiction naming both.
- Edge case: the rubric file is missing: the skill says so and grades nothing.
- Security: the artifact is fenced as data; an instruction inside it is not followed, asserted.
- Integration: the approved examples pass through the harness.

**Verification:** Brandon runs it on a real piece of his own copy and agrees with both the score and the one thing it asked him to change.

**Atlas: figure 1**, pending open question 5.

- [ ] **Unit 3.3: Content brief**

**Goal:** Produce a brief a writer can work from, grounded in the base, with the gaps named rather than filled.

**Requirements:** P33, P28.

**Dependencies:** 3.1.

**Files:**
- Create: `plugins/gtm-base/skills/content-brief/SKILL.md`, `scripts/content_brief.py`, `references/brief-shape.md`, `examples/`, `templates/company-base/context/strategy/content-rules.md` and the plugin-side copy, `tests/test_content_brief.py`
- Modify: `constants.py`, `inventory.py`, `base-kinds.md`
- Test: `tests/test_skill_examples.py`

**Approach:** Reads the umbrella and the named segment, `positioning.md`, `messaging.md`, `voice.md`, `design.md` where present, and `context/work/` for what else is in flight, and produces the brief. Its rules live in `context/strategy/content-rules.md`. Anything it cannot ground is a named gap, which is the "leave fields empty, never hallucinate" rule the donor prompts already carry.

**Patterns to follow:** The horizontal-coherence argument in the definition: one audience, so each piece must know what the others said.

**Test scenarios:**
- Happy path: a brief for a named segment carries that segment's language and not the umbrella's generic version.
- Edge case: a segment with no file produces a brief against the umbrella and says so.
- Edge case: a piece already in flight on the same topic is named in the brief.
- Security: no contact detail reaches the output; the screens run before it is handed back.
- Edge case: `voice.md` missing produces a named gap, not a generic voice.
- Integration: the approved examples pass through the harness.

**Verification:** A writer handed the brief and nothing else produces a draft Brandon does not have to re-brief.

**Atlas: figure 1**, pending open question 5.

- [ ] **Unit 3.4: Outbound sequence**

**Goal:** Produce a sequence grounded in one segment's own language, with every claim attributable to the base.

**Requirements:** P33, P28.

**Dependencies:** 3.1.

**Files:**
- Create: `plugins/gtm-base/skills/outbound-sequence/SKILL.md`, `scripts/outbound_sequence.py`, `references/sequence-shape.md`, `examples/`, `templates/company-base/context/strategy/outbound-rules.md` and the plugin-side copy, `tests/test_outbound_sequence.py`
- Modify: `constants.py`, `inventory.py`, `base-kinds.md`
- Test: `tests/test_skill_examples.py`

**Approach:** Reads the named segment file, `positioning.md`, `messaging.md`, `voice.md`, and the competitors file where present, and writes the sequence against rules that live in `context/strategy/outbound-rules.md`. Every claim is attributable to a context file, and a claim that is not is dropped rather than softened.

**Patterns to follow:** The verbatim-first extraction and banned-word rules from the donor messaging prompt.

**Test scenarios:**
- Happy path: a sequence for a named segment uses that segment's felt needs in its own words.
- Edge case: a claim with no grounding in any context file is dropped and the drop is reported.
- Edge case: a competitor mentioned with no competitors file produces a named gap.
- Security: no prospect name, email, or phone number appears in the output, asserted by the screens.
- Edge case: the segment named does not exist: the skill lists the segments that do and stops.
- Integration: the approved examples pass through the harness.

**Verification:** Brandon reads a sequence and can point at the context file behind every claim in it.

**Atlas: figure 1**, pending open question 5.

### Phase 4: the brainstorm before the build

- [ ] **Unit 4.1: The company-skills brainstorm**

**Goal:** A requirements document for company skills shared across seats. No code.

**Requirements:** P34.

**Dependencies:** 3.1 (the thin-runner pattern is an input), 2.5 (the sources-of-truth file is an input).

**Files:**
- Create: `docs/brainstorms/2026-XX-company-skills-requirements.md`
- Modify: none.

**Approach:** Run the brainstorm with the skill lifecycle from the MKT1 comparison as an input (examples as tests, a propose-an-update step after a session for approval, weekly and monthly audits) and with this repository's trust posture as the constraint. The document answers the questions below or records why each is deferred. It proposes nothing that is not answerable.

**Open questions the brainstorm must answer:**
1. **The trust model for code on every seat.** A company skill is code that runs on every teammate's machine. Today the trust-surface check refuses `CLAUDE.md`, `AGENTS.md`, `plugins/`, and every `.sh`, `.py`, and `.js` file in a base, and the session-start pull refuses the same paths. What replaces that refusal, and who reviews what.
2. **How the pull refusal and the trust-surface check change**, path by path, and what a seat does when a pulled skill changes.
3. **Review and ownership.** Who owns a skill, who approves a change to one, and how that is enforced on a plan with no branch protection.
4. **Distribution.** Through the base as its own marketplace, or through the core plugin. The parent scope assumed the former; the MKT1 read suggests the latter is simpler for a small team.
5. **Examples as tests**, carried over from Unit 3.1: whether a company skill must ship examples before it may be distributed.
6. **Update after a session:** the step where the AI proposes edits to a skill it just used and a person approves, which is propose-a-change applied to skills.
7. **Audits** for stale and duplicate skills and rules, and where their output goes.
8. **The vacation test and scheduling.** Scheduled runs are the missing half of the vacation test. Whether they belong to this feature, to the web app, or nowhere yet.

**Test scenarios:** None. The deliverable is a document. Its acceptance is a review by Astra and by Fable 5.1 and Brandon's sign-off.

**Verification:** The document can be handed to a planning session and produce an implementation plan without a second round of questions.

**Atlas: none.** A brainstorm changes no behavior.

## The runner and the outbound sequence, as revision 2 wrote them

These replace Units 3.1 and 3.4 above. Their dependencies on Units 1.3, 1.4, and 1.2b of the build plan still hold.

- [ ] **Unit 1.4b: The thin runner and its contract test (pulled forward by r2 from Unit 3.1)**

**Goal:** One shape for every skill that uses the base, which is also the deterministic caller of the moment-of-use check.

**Requirements:** P33, P28, P9.

**Dependencies:** 1.3 (`moment.check`), 1.4 (so no skill is ever written in the old vocabulary). r2, Fable H1: revision 1 also listed 1.7, 2.1, and 2.2, but its own scenarios say a missing file produces a named gap, so those were soft. This unit creates new files only, apart from the two appends named below, and runs beside Unit 1.5.

**Files:**
- Create: `plugins/gtm-base/lib/gtmbase/runner.py` (read the declared context files, call `moment.check` on each, stop for the choice when one is flagged, fence every file as data, assemble the request with the rubric, screen the output, hand back the work product), `docs/thin-runner.md` (the pattern, written once for people who write skills; r2 moved it out of `plugins/gtm-base/skills/references/`, which would have put a folder with no `SKILL.md` beside the skills), `tests/test_runner_contract.py`
- Modify, append only: `plugins/gtm-base/lib/gtmbase/constants.py`, `tests/support.py` (a helper that builds a base holding a named set of context files)

**Approach:** The runner is the only place a skill touches the base, which keeps each skill thin and keeps the moment-of-use check from being something a skill has to remember. When a declared file is flagged the runner returns the moment-of-use block and produces nothing until the choice is recorded. An example is a folder holding an input, the list of context files it ran against, an owner-approved output, an expectations file, and at least one deliberately wrong output. r2 (Astra 12, Fable M7): revision 1 called its harness "examples as tests", but it asserted which files were read, which is identical for every example, and never looked at the approved output, so an irrelevant paragraph with no contact detail in it would have passed. The expectations file states what this example must contain: required claims, the segment it is about, and the outcome (for a sequence, the number of steps and that every claim names its context file). The contract test checks the approved output against its expectations and checks that each wrong output fails. It never calls a model and asserts no prose. Separately, before any release that touches a skill or a rubric, the approved examples are run again for real and Brandon reads them; that replay is where judgment is tested, and the plan calls it a replay and not a test.

**Execution note:** Fix what the contract test asserts before Unit 1.4c is written, so the skill is built against a fixed contract.

**Patterns to follow:** `drafting.assemble` and `review.screen` as the two ends of an existing pipeline; the fenced data-not-instructions rule on every source.

**Test scenarios:**
- Happy path: a fixture skill declaring three context files reads exactly those three and calls `moment.check` on each.
- Edge case: a declared file missing from the base produces a named gap and does not stop the run.
- Edge case: a declared file that is flagged returns the moment-of-use block, and no request is assembled until a choice is recorded.
- Security: a context file holding an instruction sentence reaches the request inside the data fence; the output is screened for contact details and keys before it is handed back. The test claims the fence is present, and does not claim a model would not follow the sentence.
- Happy path: an example whose approved output meets its expectations passes; its deliberately wrong output fails; an example with no wrong output is rejected as incomplete.
- Error path: a rubric named by a skill but absent from the base: the run reports it and substitutes nothing.

**Verification:** A fixture skill written against the pattern needs no code of its own beyond its declarations and its prompt.

**Atlas: figure 1** gains the runner as the way a skill reads the base.

- [ ] **Unit 1.4c: Outbound sequence (pulled forward by r2 from Unit 3.4)**

**Goal:** The base produces one piece of marketing work a marketer would send: a sequence grounded in one segment's own language, with every claim attributable to the base.

**Requirements:** P33, P37, P28, P13.

**Dependencies:** 1.4b, and 1.2b for adding the rules file to a base.

**Files:**
- Create: `plugins/gtm-base/skills/outbound-sequence/SKILL.md`, `scripts/outbound_sequence.py` (a shim), `references/sequence-shape.md`, `examples/`, `starter/outbound-rules.md` (the starter rules, kept in the plugin), `tests/test_outbound_sequence.py`
- Modify, append only: `plugins/gtm-base/lib/gtmbase/constants.py`
- Not created, by r2 (Astra 8): nothing under `templates/company-base/`. Base creation copies that whole tree, so a rules file placed there would already exist in every new base, absent-only writing would then refuse it, and the one existing base would never receive it.

**Approach:** Reads the named segment's file when the base has one and otherwise the customer profile, saying which it used; reads the positioning; reads messaging, voice, and competitors where present and names each one that is missing as a gap, never filling it. The Gridwise base holds a profile and a positioning today, so the first real run is against those two with the gaps named. The rules live in `context/strategy/outbound-rules.md`. When the base has no rules file the skill says so and offers the starter as a proposed change, which the owner approves through Unit 1.2b (or through the shipped path once a shared copy exists); nothing is written before that yes, and a customized rules file is never overwritten. Every claim in the sequence names the context file behind it in a short table under the sequence, and a claim with no grounding is dropped and the drop reported, not softened. It reads `context/work/` nowhere, because that folder exists in neither the template nor the real base (Fable M8).

**Execution note:** The deterministic tests cover what code can prove: which files were read, the fence, the contact and key screens, the claims table naming only files that were read. They do not prove the sequence is good or that no prospect's name slipped in, because the screens do not detect arbitrary names (`redaction_patterns.py` around line 124). That is what the owner replay and SC-C are for, and the two are kept apart in the test file and in the CHANGELOG.

**Patterns to follow:** The verbatim-first extraction and banned-word rules from `draft-positioning.md`; the step shape in `docs/ux-standard.md`.

**Test scenarios:**
- Happy path: a sequence for a named segment reads that segment's file and says so; on a base with no segment files it reads the profile and says so.
- Edge case: a claim with no grounding in any file that was read is dropped and the drop is reported.
- Edge case: every row of the claims table names a file that was in the read set; a row naming any other file fails.
- Edge case: messaging, voice, or competitors missing: each is a named gap.
- Edge case: the segment named does not exist: the skill lists the ones that do and stops.
- Edge case: no rules file: the skill offers the starter as a proposed change and produces no sequence until it is approved; a base that already has a rules file is never offered the starter over it.
- Security: no email address, phone number, or key appears in the output, asserted by the screens.
- Edge case: a flagged profile pauses the run at the moment-of-use block before any sequence is written.
- Integration: the approved examples pass the contract test, and each wrong output fails it.

**Verification (SC-C):** Brandon runs it on the Gridwise base, can point at the context file behind every claim, uses the sequence in real outreach, and the walkthrough record says what was sent, what he changed first, and what came back.

**Atlas: figure 1.**
