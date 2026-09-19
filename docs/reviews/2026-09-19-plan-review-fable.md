# Plan review: "A base that produces work" (Fable 5.1)

Date: 2026-09-19. Reviewed: `docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md` revision 1, its four inputs, and the shipped code at 0.2.6. I did not read the other reviewer's file. Everything marked "verified" was checked against a file or a command today. Everything else is labeled as inference.

Two lenses were added to the brief: whether the plan actually produces the owner's UX standard (says what it is for, readable in seconds, ties back, asks one thing), and whether the order puts usable marketing work in the owner's hands soon enough.

## Verdict

**Ready to build Phase 1 only with the listed changes.** Units 1.1 and 1.2 can start as written once B1 is answered. Units 1.3, 1.5, and 1.7 cannot be briefed as written. Phases 2 to 4 should leave this plan and become their own plans, with one exception that should move earlier (see H1).

## The three changes I would make first

1. **Give a local base a way to approve a proposed change (fixes B1).** Without it, every "goes through the proposal path" sentence in Phase 1 ends in a refusal on the only real base.
2. **Move the UX standard from Unit 1.8 to directly after Unit 1.1, and point its lint at the sentences people actually read (fixes H2 and H3).** Today it lands last, after seven units of live-checked wording it then rewrites.
3. **Pull the thin runner and one work-producing skill forward to right after Unit 1.4 (fixes H1).** As ordered, sixteen serial units ship before the base produces one piece of marketing work.

## Blocker

### B1. The proposal path cannot complete on any base that exists, and Phase 1 routes five behaviors through it
Units 1.3, 1.5, 1.7, 3.2; requirements P6, P9, P16, P27.

Evidence, all verified:
- `compose_proposal.py:660-669` refuses with "This base has no shared copy yet" when the base has no `origin`.
- `git remote -v` on `~/GTM Bases/Gridwise/gtm-base` returns nothing. The one real base has no shared copy.
- `push_conditions.py:28-31` refuses while the seat's `first_push_reviewed` is false. `create_base.py:372` sets it false. No shipped code ever sets it true. Only tests do (`tests/test_stale_check.py:120`, `:895`), which is why the SC1 "opens a review" test passes.
- Backup is unbuilt (`skills/join/SKILL.md:419-428`), and the plan defers it past Phase 3.

Consequence: a "no" at the closing reconciliation (P6), a hand edit raised for review (P16), settling a `[your call: ...]` marker later (P27), "fix it first" at the moment of use (P9), turning a pending segment in the umbrella into a real one (1.7), and drift grade's second output (3.2) all end at a refusal sentence. The 1.5 integration scenario ("reconciliation no, proposal, review, approve, and the affected file ends confirmed") passes only because fakes stand in for the shared copy. The plan's Risks table mentions that approval happens "only on the GitHub page", which understates it: on this base approval cannot happen anywhere.

Smallest change: add one unit before 1.5, "approve a proposed change locally". When a base has no shared copy, the staged change is shown in Claude in the four-line form and applied to the local base on the owner's yes, with the same corrections record. This is the local half of the first plan's Unit 8, it keeps "the AI proposes, a person approves", and it does not reorder backup ahead of skills. Runner-up: give the Gridwise base a shared copy by hand, which is faster but leaves every future setup-created base broken and still needs a setter for the first-backup flag.

## High

### H1. Sixteen plumbing units ship before one unit of usable work, and the dependency that forces that order is soft
Phase order; Units 3.1 to 3.4.

Pipeline view of the twenty units:

| Produces work a marketer can use | Produces context a marketer would hand to someone | Plumbing |
|---|---|---|
| 3.2 drift grade, 3.3 content brief, 3.4 outbound sequence | 1.7 (adopted segments), 2.2 (messaging, voice), 2.3, 2.4 | 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 1.9, 2.1, 2.5, 2.6, 3.1, 4.1 |

Unit 3.1 lists 1.7, 2.1, and 2.2 as dependencies, but the plan's own scenarios say a missing file "produces a named gap" (3.1), a segment with no file briefs "against the umbrella and says so" (3.3), and "`voice.md` missing produces a named gap" (3.3). The Gridwise base already holds a confirmed profile and positioning. The hard dependencies are only 1.3 (`moment.check`) and 1.4 (so no skill is written in the old vocabulary). The serial rule in Phase 1 comes from Codex's order, and Codex's order says nothing about skills.

Smallest change: after 1.4 merges, run 3.1 plus one skill as a parallel track that owns only new files. I recommend the outbound sequence first because its line to pipeline is the shortest (sequence, sends, replies, meetings); the content brief is the runner-up. Also add a success criterion the plan lacks: one skill output used in real work at Gridwise, with what happened recorded. Today neither SC-A nor SC-B tests whether the base produced anything, and both come from a source the ideation file itself labels an unchecked summary of a partly paywalled page.

### H2. The UX standard is asserted last and rewrites wording the owner has already live-checked
Unit 1.8; Execution Posture.

The plan schedules live checks for 1.2, 1.3, 1.5, 1.6, and 1.7, then 1.8 "rewrites the sentences the earlier units wrote". Every earlier live check is spent on sentences that will not ship. Codex's order does not include the plain-language unit at all, so moving it breaks nothing.

Smallest change: split 1.8. A new Unit 1.1b lands the written standard, the four-line change format, and the lint checks with an exemption list, before any behavior unit. Each later unit writes to it. What is left of 1.8 is the sweep of text no unit touched.

### H3. The extended lint checks the instructions to the assistant, not the sentences the person reads
Unit 1.8; Context section, line 125.

The plan says "Every sentence a person reads lives in a skill body, a reference file, or a template." That is false (verified). `stale_check.py:86-152` holds the out-of-date findings, the quiet-record sentences, and the review-date sentence as Python strings. `constants.py:342-346` holds the narrowing question. `confirm.py:151-159` and `join_flow.py:94-104` hold more. The skill tells the assistant to say these "word for word". Unit 1.8's file list has no Python file in it, so the sentences most often read aloud are outside the lint. Separately, the four checks measure the shape of `SKILL.md`, which the person never sees, and agents building to a green lint will satisfy "opens with a purpose sentence" with boilerplate.

Smallest change: add the Python sentence constants to the lint (one registry list of them, asserted complete by a test), and make the owner's read-aloud check the acceptance test for the standard, with the lint described honestly as a floor.

### H4. Three current steps break the standard worst, and no unit fixes them; two units make them heavier
Units 1.5, 1.6, 1.7, 1.3.

| Step today | Why it fails the standard | Covered? |
|---|---|---|
| Join step 5 consent paragraph (`SKILL.md:210`): seven sentences before "May I read these?" | Not readable in seconds. It is long because of a real-run lesson (0.2.2), and `tests/test_join_setup_flow.py:1595` pins it | No. 1.6 adds a count confirmation and a "why a draft reads a limited amount" explanation to the same step. The plan never reconciles P28 with the lesson |
| Join step 6 preview (`SKILL.md:275-281`): before every draft the person is asked whether to draft from the list or narrow it | A second and third narrowing ask after an explicit folder choice, the same defect r2.4 finding 4 names | No. 1.6 removes the repeat in step 5 only |
| Confirm skill "How to ask" (`confirm/SKILL.md:29-38`): show the whole document, then explain all three answers, for every question | In a review of many due files this repeats per item | Partly. 1.3 changes where the skill is entered, not what it shows |
| Closing (step 7) after 1.5 | Becomes five or more asks in a row: what got in the way, the context change, the entry preview with four correctable fields, then one reconciliation question per affected document. With segments, "affects" can name twelve files | No cap is stated |
| Adoption after 1.7 | P21 requires each of twelve cleaned bodies shown whole. P28 says never paragraphs, detail on request. Amendment r2.4 D and H carry the same conflict and the plan inherits it silently | No |
| Findings name raw paths and entry ids ("decision stg-bbca... comes up for review") | A marketer reads `context/strategy/icp.md` and a hash | No unit gives documents and changes human names |

Smallest change: in 1.1, record one ruling per row. My recommendations: the consent paragraph becomes three short lines plus the question; the per-draft narrowing ask is dropped when the choice was explicit; the review shows a one-line summary per item with the document on request; reconciliation is asked only for the two required documents at the closing and the rest are left flagged for the review; adoption shows what was removed plus the opening lines and writes the full cleaned file to the run folder for reading, with the yes bound to that file's hash (this needs the owner and Codex to agree it still meets condition D).

### H5. After Phase 1 the base has no dependable way to speak or to learn about a change
Unit 1.3, 1.5; P9, P17. Quiet by default is decided and I am not reopening it. The defect is that the plan does not supply the replacement it promises.

- In Phase 1 no skill "uses" a context file. Join, stale-check, propose-change, and confirm do not. The deterministic `moment.check` caller first exists in Unit 3.1. Until then P9 rests entirely on the injected instruction, which the plan itself calls unmeasured. The 1.3 integration scenario "runs a skill that calls `moment.check`" has no real skill to run.
- The quiet-record ask moves inside "review my base" (P17), and the weekly line is off by default. Codex condition C asked for the "daily-question behavior". A reminder that only appears inside a review the person must remember to request is condition C weakened.
- 1.2 removes the required entry before 1.5 wires the habit. If open question 6 is answered "several releases", a release exists in which setup captures no change at all, which is the exact case Codex's opposing argument warned about.
- `moment.check` "offers the fix it has already written", but nothing writes a fix unless stale-check has run since the change was recorded (verified: `session_start.py` makes no staging call).

Smallest change: (a) state that 1.2 through 1.5 ship in one release; (b) add a measured trial to 1.3's live check, a fixed number of real prompts that use a flagged document, with the count of times the flag fired recorded in the CHANGELOG and the bar set by the owner beforehand; (c) have `moment.check` say a fix is ready only when a staged file exists and otherwise offer to prepare one; (d) evaluate a read hook scoped to files under a joined base's `context` folder as the deterministic backstop. The plan rejects a read hook because it "would fire on every file in every repository", but the Bash gate already reads every command and exits early, so the rejection needs a better reason or a measurement.

### H6. Unit 1.2 and Unit 1.5 contradict each other on the source-age finding
`stale.py:869-897` (verified). `_review_items` only considers entries whose `run_id` matches the run on a drafted confirmation line. Unit 1.5 writes closing entries with no run id. After 1.5 the function returns nothing for every entry setup can produce, so the finding P22 "corrects" in 1.2 is dead two units later, and 1.2's scenario "twelve files, one open change affecting two, items for those two only" cannot occur in the product.

Smallest change: in 1.2, state what the finding keys on once run ids are gone (a drafted line on the file, an open entry that affects it, and material dated before the change happened), or delete the finding and its sentence.

### H7. Unit 1.7's write order is contradictory, so the unit cannot be briefed
The approach says the inventory is settled before the umbrella, adoption runs per file, and an interrupted import resumes "because the two required files have already made the base complete", which puts adoption after both required files. The scenarios say "the umbrella names all twelve" and names excluded ones as pending, which puts adoption before the umbrella. If adoption is first, a segment file is the document that creates the base, and `SKILL.md:341-345` plus `approve --parent` assume the first document is the profile. If adoption is last, the umbrella is approved listing every segment as pending and is wrong the moment the import finishes, and setup may not edit it, and the repair path is B1.

Scope has the same problem: `covers:` lives in the umbrella's frontmatter, which does not exist while selection and adoption are using it. And "narrows both the selection list and the adoption offer" is not testable as written, because nothing says how free text filters files. Codex itself called folder names a heuristic.

Smallest change: write the order as numbered steps in the unit (scope held in the run folder, inventory decided, adoption writes, umbrella drafted from what was written, positioning), say which document may create the base, and define scope enforcement as the person dropping named places, recorded with the scope label, instead of a text filter.

### H8. The rename misses consumers, cites a file that does not exist, and breaks one metric
Unit 1.4.

- "The migration ordering pattern from `migrate.py`" does not exist (verified). The only `migrate` is `paths.py:510-519`, a stub that raises "migration-not-available".
- The file list omits verified users of the old folder: `paths.py:27-31` (`PROPOSAL_PATH_PREFIXES`, which decides what a proposal may change, so a staged or kept proposal naming the old path is refused after the rename), `report.py:113`, both `CODEOWNERS` templates, `templates/corrections-file.md:11`, and tests `test_create_base.py`, `test_paths.py`, `test_report.py`, `test_review.py`, `test_trust_surface.py`.
- `report.py:72-80` finds the change that first added an entry with a log query that does not follow renames. After a move plus a field rewrite in one change, the migrated entry's first-added change is the migration, so the "catches" number silently drops. "Moves the folder with git so history follows" is not a property git guarantees when content changes in the same change.
- The migration's record in `corrections/` must parse as a `CorrectionsFile` (entry id, staging id, content hash, correction class) or `report.py` skips or miscounts it.
- The lint bans "decision" but not "ledger", which people read today in `stale_check.py:110-121` and in `--dismiss-ledger-behind`.
- `decided_by` becoming `noted_by` changes meaning (who decided versus who wrote it down) while P5 still shows "who decided". P14 says meanings are kept.
- Scale check (verified): the real base holds one entry, no corrections, and no proposals. An idempotent migrator with a both-folders refusal is heavy for one file, but P15 is the owner's call, so I only ask that the move and the field rewrite be two separate changes and that `report.py` look under both paths.

## Medium

- **M1. P3 cannot be "rerun unchanged" across 1.4.** The SC1 test builds entries with the old field names. Say instead that the old-layout SC1 test stays byte-identical as tolerant-reading proof and a new-layout twin is added.
- **M2. One 1.5 scenario passes today with no code change.** `stale.py:913` already treats an empty record as behind immediately. Codex stated that as existing behavior, and the plan turned it into a requirement (P17). Replace the scenario with the dismissal-then-return case only.
- **M3. The fidelity replay can pass on one case, scored by nobody named.** Cases two and three have no real material (the Gridwise input was under the cap). The execution note lets the gate be "decided on the cases that were run", which drops the exact case Codex required. Smallest change: build case two from real material by withholding the twelve finished pages from consent and scoring the drafted segments against those pages as the answer key, build case three by lowering the cap for the replay and labeling it, name the owner as scorer with the builder barred from scoring, and run case one against 0.2.6 now so a failure is known before 1.7 is built.
- **M4. The map fix invites the question it is meant to end.** Giving the map a confirmation line (1.2) makes it come due again after the threshold and appear in the review. Exclude `kind: map` from questions and reviews instead, which also covers the base created before this unit.
- **M5. Adopted text is unfenced on the only read path Phase 1 has.** The Risks table says "the fence is the whole defense", but outside a skill the assistant reads context files directly. Add the data-not-instructions sentence to the injected instruction and record the residual risk.
- **M6. Unit 2.6 cannot know a seat is behind.** Both versions it compares are local. Either always print the one step with the installed version, or allow one on-request network read and say so.
- **M7. "Examples as tests" do not test the examples.** The 3.1 harness asserts which files were read, which is identical for every example, and never looks at the approved output. Call it a runner contract test, and make the approved examples a replay the owner reads before any release that touches a skill or rubric.
- **M8. Units 3.2 and 3.3 read `context/work/`, which does not exist** in the template or the real base (verified), and no Phase 2 kind fills it. Cut the in-flight contradiction feature or add the kind.
- **M9. "Ordered exactly as Codex sets out" is inaccurate.** The plan inserts 1.3, 1.4, and 1.8 into Codex's six steps, and Codex never reviewed Amendment r2.5. The moment-of-use design has had no outside review until this one.

## Low

- `plugins/gtm-base/skills/references/thin-runner.md` puts a folder without a `SKILL.md` beside the skills. Put it under `lib` or a skill's own references.
- `draft-positioning.md:83` also asks for `[your call: ...]`; 1.7 reconciles only the profile prompt.
- P16 "asks what changed and why" is two questions under the plan's own lint, on top of the existing "where did this come from".
- Amendment r2.4 C.2 still says the daily block asks about a quiet record; 1.1 should amend it to match P17.
- A second seat on an older plugin would read a migrated base as empty and report nothing out of date. Record it against release two.

## Codex conditions, by name

| Condition | Unit | Status |
|---|---|---|
| A | 1.1, 1.2, P3 | Met, subject to M1 |
| B | 1.5 | Met in tests, dead on a real base until B1 |
| C | 1.5 | Weakened: the daily ask became an ask inside an on-request review (H5) |
| D | 1.7 | Contract met by name. Write order unresolved (H7). First-backup review rewrite is deferred to a note |
| E | 1.7 | Storage met. Enforcement asserted, not designed (H7) |
| F | 1.6, 1.7 | Met, except settling a marker later depends on B1 |
| G | 1.9 | Weakened by the run-what-exists escape (M3) |

## The planner's open questions and contradictions

The brief mentions five contradictions the planner surfaced. They are not written in the plan or any file I was pointed to, so I could not rank them. Of the seven open questions: **4 (who scores the replay) and 6 (one release or several) are blockers before build**, because 6 decides whether H5's gap ships and 4 decides whether the gate can fail. **1 ("Sol") blocks briefing, not design.** Questions 2, 3, 5, and 7 can wait for Phase 2 and later.

## Scope

Twenty units in one plan is the wrong shape. Keep Phase 1 plus the pulled-forward runner and one skill here. Move 2.3, 2.4, 2.5, 2.6, the other two skills, and 4.1 to their own plans, written after the first skill has been used on real work, because that use will change what the inventory and the rubric files need to hold.
