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

# 0.2.4: where a base lives, and the folder it belongs with

Two reviews by Codex on 2026-09-07 (`docs/reviews/2026-09-07-codex-base-location-critique.md`
and `docs/reviews/2026-09-07-codex-base-link-round-two.md`) and Brandon's decision
after them: every new base goes to `~/GTM Bases/<Company>/gtm-base`, and the base
is linked to the folder the person's marketing material lives in so that opening
Claude Code there brings the base with it.

## Plan

- [x] A. `folder_identity`: take and compare what makes one folder the same
      folder, with the device number, the inode, the day it was made, the mount
      point, the volume identifier, and the address of the shared copy when the
      folder is itself the top of a repository.
- [x] B. The joined entry gains the folder a base belongs with and the evidence
      about it, read and written together, with every change to the account file
      made with the lock held for the whole read, decide, write.
- [x] C. Central placement, with a destination inside another tool's history, a
      folder kept in cloud storage, a base, or GTM Base's own records refused at
      the moment it is proposed and again at the moment the base is built.
- [x] D. One read-only resolver that collects every claim on a folder before it
      chooses any of them, and a session start that says both halves of what it
      found and repairs a rename only in the half that may write.
- [x] E. Three sentences in the join skill: link this folder, unlink this folder,
      show my linked folders, each of them working with no base in the session
      and taking the company name as well as the folder.
- [x] F. The sentence at the location step and the message at the closing both
      name the folder the person will open and the base's own folder.
- [x] G. Amendment r2.3 in the join plan, with J14, J15, J16, J19 amended and R5
      clarified; the join guide and the logic atlas brought up to date.
- [x] `sh tests/run.sh` green, no long dashes in any touched file

## Review

One thousand and seventy seven tests pass, one hundred and twenty one of them
new since 0.2.3. The whole run is `sh tests/run.sh`, and the summary line is
"Ran 1077 tests in 210.539s" followed by OK.

Six decisions worth knowing about, beyond what the plan already records.

The comparison of one folder with another answers with four words rather than
three. A folder that was renamed and a folder on a disk that came back as a
different disk are not the same situation for a person: the first is followed
without them being asked anything, and the second is a question. Folding them
into one answer would have meant either following a disk that might be somebody
else's or asking about a rename that needed no asking.

The names of the folder record's parts are `Identity`, `capture`, `matches`,
`as_dict`, and `clean` rather than the ones the brief sketched, and the codes
are `content-taken`, `content-inside-base`, `link-conflict`,
`link-identity-mismatch`, `identity-unstable`, and `link-failed`. They were
already written and already tested under those names, and renaming them would
have been churn with no reader better off. The case of a folder that a base
sitting directly inside it would always shadow is refused under
`content-inside-base` rather than under a code of its own, because the person is
told the same thing either way.

The three sentences about the link are "link this folder to my base", "unlink
this folder from my base", and "show my linked folders". The brief proposed
"this base belongs with this folder", and that phrasing was turned down for the
reason Codex gave: it is at its most ambiguous exactly when nothing has been
opened, which is when a person needs it. The chosen wording says which folder
and which base without either being open.

Naming the base is now optional. Connecting a folder happens from inside that
folder, which is never a base, so the step cannot ask the resolver what base the
session is in. A base can be named by its folder or by the company it is for,
and on an account with one base it need not be named at all. With more than one
and none named, both are named back and nothing is changed.

The base and the folder it belongs with are written down together, under one
lock, and the folder is asked about before a single folder is made. It used to
be two writes with the base built in between, which left a moment where a window
that closed produced a base with no record of the folder and nothing saying so.
A refusal that arrives anyway still leaves the base joined, because a base
nothing has a record of is a base the person cannot get back to.

Figure 2 of the atlas was drawing the wrong order. It showed the link being
considered before a folder that merely looks like a base, and the code does the
opposite, so a base whose own folder was renamed is recognised as itself first.
The figure and its caption now say what the code does.

One thing that was left as it is. The closing message lives in
`closing-rules.md` twice, once for a base with a linked folder and once for a
base without one, rather than once with a line swapped into it. That file exists
so a person can read the message as a message and edit it, and a template with a
hole in the middle of it stops being readable as one.

## 0.2.5 (2026-09-12): contact lists left out, and a sprawling folder narrowed first

- [x] A file of rows is classified `contact-list` and never offered for reading,
      when its heading row names an email, phone, mobile, or social column, or
      when at least a third of the first fifty rows hold something shaped like
      an email address. Only the first sixteen kilobytes are looked at, and only
      whole lines of it.
- [x] A listing now counts its readable files per folder at the top of the one
      that was named, and carries `narrow-first` when there are more than forty
      files across more than three of those folders.
- [x] `list-sources` prints the counts and the question, takes one
      `--only-folder` per folder, and writes the chosen folders down with the
      list. `freeze-sources` refuses `narrow-first` until folders were chosen.
- [x] The one opening question asks for the narrowest folder.
- [x] The join guide, the reading rules, and figure 7 of the atlas say all three.

### Review

The guard against a whole working repository is two guards, and they sit at
different points on purpose. The contact-list rule runs during the walk, so a
prospect list never reaches the list a person is shown and cannot be named back
in later, because a file that was never readable is not on the frozen list and
every read goes through that list. The narrowing rule runs between the list and
the yes, and it is enforced where the yes is taken rather than only in the
skill's wording, so a large sprawling list cannot be frozen whole even if the
conversation skips a step.

Two decisions beyond the brief.

The value standing for the whole listing still covers the whole folder even when
the shown list was narrowed to two of its folders. That value is what says
whether the folder changed while the person was reading, and narrowing it to the
chosen folders would have made a file appearing elsewhere in the named folder
invisible to that check.

Naming a folder that is not one of the folders in the list is refused, with the
code `no-such-folder`, rather than quietly producing an empty list. An empty
list silently taken as a yes would have frozen nothing and left the run with no
material and no explanation.

One thing left as it is. Narrowing for a single draft (`--only-folder` on
preview and assemble) now accepts several folders as well, which fell out of the
same change, but the skill still describes one folder there, because a draft
narrowed to several folders is not a thing anybody has asked for yet.

## 0.2.6 (2026-09-12): the places found and proposed, instead of asked for

- [x] `sources.survey` finds the places inside a folder that look like marketing
      material, from file names and first headings only, and says one sentence
      about them.
- [x] `constants.MARKETING_KINDS`, the weights, the plural names, and the three
      sentences a person hears.
- [x] `join_flow.survey_sources` writes the proposal down in the run's folder,
      and `list-sources --from-survey` lists the places with the person's adds
      and drops applied.
- [x] The frozen yes records the proposal and the adjustments alongside the
      list.
- [x] The shim gains `survey`, `--from-survey`, `--add`, and `--drop`.
- [x] Step 3 asks where the material is roughly. Step 5 runs the finding step
      first and the consent sentence says what was looked at.
- [x] The reading rules, the join guide, and figure 7 of the atlas say the same.

### Review

The finding step sits in front of the list rather than inside it. It runs the
listing's own walk and then looks at nothing but names and first headings, so
everything the list refuses is refused here too and a document that says
something about itself on line fifty says it to nobody. The narrowing rule from
0.2.5 is still enforced where the yes is taken, as the backstop it now is.

Three decisions beyond the brief.

The files lying loose at the top of the named folder are a place like any other,
and the sentence calls them "the files loose at the top" rather than reading a
full stop out loud. The `place=` line still names that place with a full stop,
which is what `--drop` takes.

A folder named to drop that nobody proposed is refused with `no-such-folder`,
the same as a folder added that is not there, because both are somebody naming a
folder that is not the one they think it is. Dropping every place comes back as
`no-folders-chosen` rather than quietly listing the whole folder again.

The engineering folder in the fixtures is kept out by the thin rule rather than
by the weighting: one plan-shaped name among five files is fewer than a quarter
of what the folder holds and fewer than three, so the folder is dropped with the
note `thin:engineering`. The weighting alone would have ranked it last and still
proposed it.


## 2026-09-19: the plan reviews, revision 2, and the start of Phase 1

Plan: `docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md` (revision 2).
This file is append-only. Agents add below; nobody rewrites what is above.

- [x] Run the Astra review through the Codex CLI from a script file, written to
      `docs/reviews/2026-09-19-plan-review-astra.md`. Verdict on revision 1: not ready.
- [x] Read both reviews and fold every finding into the plan as revision 2, with
      a table from finding to unit.
- [x] Move Phases 2 to 4, unchanged, to `docs/plans/2026-09-19-002-roadmap-after-phase-1.md`.
- [x] Baseline before the build: 1127 tests passing. `tests/run.sh` now fixes the
      time zone, because three tests in `tests/test_review.py` assumed a Pacific date.
- [ ] Brandon answers the eight calls under "For Brandon" in the plan. The plan
      is written to the recommended answer on each, so the build does not wait.

### Release A
- [ ] Unit 1.1: contract amendments, the six UX rulings, the frozen replay bar
- [ ] Unit 1.1b: the UX standard and the lint
- [ ] Unit 1.2: completion and closing
- [ ] Unit 1.2b: approve a proposed change locally
- [ ] Unit 1.3: quiet by default
- [ ] Unit 1.4: the rename to context change, with a recoverable migration
- [ ] Unit 1.4b: the thin runner and its contract test (side track)
- [ ] Unit 1.4c: the outbound sequence (side track)
- [ ] Unit 1.5: habit hooks
- [ ] Security pass and correctness pass, then the live check, then the version bump

### Release B, behind the fidelity gate
- [ ] Unit 1.6: selection fixes
- [ ] Unit 1.7a: scope and the segment inventory
- [ ] Unit 1.7b: umbrella and segment drafts, the unanswered-marker state
- [ ] Unit 1.7c: guarded adoption
- [ ] Unit 1.7d: recovery of an interrupted import
- [ ] Unit 1.8: the sweep of text no unit touched
- [ ] Unit 1.9: the fidelity replay, scored by Brandon

### 2026-09-19, revision 2.1
Brandon's call: context first, skills after. Units 1.4b and 1.4c above are withdrawn from release A and live in the roadmap. Release A is Units 1.1 to 1.5.

- [x] 2026-09-19: Unit 1.1 merged and pushed (921a0d7), suite at 1127 passing. The replay corpus lists are kept outside the repository at ~/GTM Bases/Gridwise/fidelity-replay/. Left open: case two corpus, the answer key, the lowered read amount for case three; figure 7 of the atlas still says three drafts and moves with Unit 1.2.

- [x] 2026-09-19: Unit 1.1b built, suite at 1193 passing. Eleven exemptions, all in the join skill, cleared by Units 1.5, 1.6, and 1.8. The registry found 71 sentences held as Python strings across eight modules.

- [x] 2026-09-20: Unit 1.2 built, suite at 1217 passing. Carried forward: the older sentence that says there is no date to watch can still be reached when every recorded change is closed; it belongs to the Unit 1.4 wording pass.

- [x] 2026-09-20: Unit 1.2b built, suite at 1264 passing. A prepared change can be
      approved by its owner in Claude on a base with no shared copy, in two calls
      bound together by the hash of what was shown. `push_conditions.py` and
      `gate.py` are byte for byte as they were, and the seat's `first_push_reviewed`
      is still false after a change is approved. `compose_proposal.propose` now
      asks about the shared copy before the two conditions, because the one real
      base fails both and the person was being told about a backup that was never
      going to happen; no existing test pinned the old refusal sentence. Carried
      forward: the shared-copy half of reviewing proposals, which is listing open
      proposals, reject-but-keep, and the branch hash check, still ships with backup.

- [x] 2026-09-20: Unit 1.2b reviewed twice from outside and every FIX folded in,
      suite at 1310 passing. Three defects were reproduced first and then fixed:
      the map rule could be reached by letter case or by a folder link, throwing
      a prepared change away deleted whatever path it was handed, and recovery
      wrote over the person's own edits on a path its note named. The note now
      records the content it will write at each path and puts nothing back that
      does not match it. Also fixed: not knowing whether a base has a shared copy
      is no longer read as not having one, what is shown is the whole of what
      gets written, the screens read the headings and the note saved with the
      work, a change is never recorded twice, and one context change counts once.
      `push_conditions.py` and `gate.py` are still byte for byte as they were.
      Recorded as residual in the CHANGELOG: the turned down rate still comes
      only from a shared copy, and the command check reads commands only, which
      belongs to the release security pass.

- [x] 2026-09-20: Unit 1.3 built, quiet by default. A session start records the
      session, updates from the shared copy, hands over the map and the change
      summary and the moment-of-use rule, and asks nothing: no question text, no
      question identifier, no line in the asked log. The question machinery moved
      whole into a review mode on `stale_check.run`, entered by saying "review my
      base", which lists one line per item using `names.py`, issues one
      single-use identifier per document it asks about, and lists prepared
      changes waiting for a local yes as items with no question. New
      `moment.py` holds the action contract: detect by local lookup, say a fix is
      ready only when a staged change for that file is really waiting, pause, and
      three answers, one of which writes nothing, one of which prepares a change
      for `approve_local`, and one of which is the confirmation that already
      exists. The three Phase 1 entry points that hand a context file to the
      model each gained `--show-document`, which runs the check first and fences
      the file, and each is tested on what its own script really prints. The
      weekly line and a month of quiet live in seat state.

      The read hook was evaluated and NOT built. Claude Code's hook
      documentation (https://code.claude.com/docs/en/hooks, read 2026-09-20)
      names the events whose plain output reaches the assistant as
      UserPromptSubmit, UserPromptExpansion, SessionStart and PostModelSwitch,
      and the tool-use event is not among them; the only documented answer shape
      for a tool-use hook is a permission decision. There is no documented way
      for it to deliver the flag without blocking the read, so building it would
      have been a guess. Recorded in the CHANGELOG in those terms.

      Tests moved rather than deleted, each with its reason written in the test:
      six scenarios in `tests/test_session_start.py` that pinned the question,
      the single-use identifier, the also-waiting list, whose yes counts, the
      map, and the refused path, plus one in `tests/test_confirm.py` that held
      the injected text to naming the confirm script. What they proved is proved
      of the review in `tests/test_moment_of_use.py`.

      Carried forward, and not done here: the review lists unanswered markers
      only once Unit 1.7b makes a marker a state of its own, so this unit proves
      only that a marker alone never interrupts. The measured trial of the
      injected instruction is Brandon's to run, and nothing about its
      reliability is claimed anywhere.

- [x] 2026-09-20: Unit 1.3's read hook built after the first verdict was
      overturned. The verdict was wrong. I had read the rule about which events
      put plain output into the assistant's context and treated the absence of a
      tool-use example as the answer; the decision-control table on the same
      page settles it the other way. Re-read at
      https://code.claude.com/docs/en/hooks on 2026-09-20 and quoted in the
      CHANGELOG: the tool-use event honours `permissionDecision`,
      `permissionDecisionReason`, and `additionalContext`, the last described as
      "Text added to Claude's context before the tool call runs, shown in the
      transcript". The page also says the same events fire in the terminal, the
      IDE extensions, the Desktop app and cloud sessions, and that all matching
      hooks run in parallel.

      Built as `lib/gtmbase/read_hook.py`, `scripts/read_check.py`, and
      `hooks/read-check.sh`, declared with matcher Read beside the untouched
      Bash entry; the manifest still does not name hooks.json. It leaves at once
      for anything outside a joined base's context folder, resolves through
      `machine.load_machine_state` plus `paths.resolve_base` plus
      `paths.canonical_context_path` rather than a new resolver, folds letter
      case with `trust_surface.normalize_component` and recovers the spelling
      the disk uses, follows links and refuses one leading out of the base,
      never sets any permission decision, always exits 0, reaches nothing, and
      writes only this seat's own `read_notices.json`.

      Double asking is prevented twice over. The hook issues no question
      identifier at all, and `moment.check` now hands back a question already
      open for the same document in the same session instead of issuing a
      second, so the hook and the script the rule names can never add up to two.
      The hook also says a given document once per session.

      Two things reported to me I could not verify and therefore did not print
      anywhere a person reads: the Claude Code changelog entries said to be at
      2.1.9 and 2.1.110 (the public CHANGELOG.md is truncated at 2.1.267, so it
      neither confirms nor refutes them, and the release-notes page is a 404),
      and the statement that the read tool's `file_path` is always absolute.
      The CHANGELOG and the join guide therefore say "a release of its own"
      rather than a version number, and the hook resolves a relative path
      against the session folder rather than assuming an absolute one.

- [x] 2026-09-20: Unit 1.3 corrected after two outside reviews, every FIX item
      closed. The eight they reproduced were real. In the order they were
      fixed: the refused path used to hand back any file on the computer (S2);
      the injected rule's own script reported a flagged document as clear for
      the absolute path an assistant actually passes, and printed nothing on
      every kind of failure, so silence did not mean what the rule says it
      means (C1); the four lines were an injection channel through the change
      body, the source, and file names (S1); a question was handed back across
      sessions and across changes (C2); one answer settled every older change
      on the file (C3); nothing could record the three answers or set the
      weekly line and quiet (C4). Then the mediums: shell characters in paths
      and unquoted paths in the rule (S3), the miss path's cost (S4), false
      flags from an exhausted budget (S6), the review hiding files and ids and
      inflating the asked log (C5, C6, C7), told-once ignoring new changes
      (C10), and a prepared change for another change counting as a fix (C11).
      Then the lows: the case-folded prefix (S7), one document listed twice
      (C12), the review's empty and shared-copy cases (C13), the unfilled
      plugin path (C14), what a not now does and does not do (C15), and the
      two-pass fill (S9).

      C3 changed `stale._line_confirms`, which the whole product rests on. Not
      one existing test needed changing: `test_stale`, `test_stale_check`,
      `test_approve_local` and `test_confirm` all pass untouched, 244 of them.
      The reason is that the rule only narrowed a case nothing else relied on,
      a line that names one change being read as an answer about another.

      Two things measured rather than asserted, on this computer on 2026-09-20:
      the miss path went from 11.0 to 0.3 milliseconds at the median and from
      201 to 4.4 at its worst with one base joined, and from 10.5 to 0.2 with
      five bases joined and four of their folders gone; the whole wrapper end
      to end is 58 milliseconds a miss, nearly all of it starting Python. The
      scripts are in the scratchpad and the numbers are in the CHANGELOG.

      One existing scenario of mine was rewritten rather than deleted: a
      prepared change waiting on a document that is also due used to be its own
      item and is now folded into that document's one line, which is finding
      C12, and the test says so.

      Recorded as open in the CHANGELOG and not fixed: two sessions in one base
      at once, the backstop writing "told" before the client delivers the text,
      and unsalted path hashes.

- [x] 2026-09-20: Unit 1.4 built, the rename to context change, suite at 1446
      passing. What the base tracks is a context change everywhere a person
      reads it. `work/decisions` became `work/changes`, entries say
      `kind: change`, and `decided_on` and `decided_by` became `happened_on`
      and `noted_by`. Entry identifiers are untouched, which is what keeps
      every confirmation, correction record, and prepared change pointing at
      the same thing.

      The reader came first and nothing else could have gone before it.
      `base_reader.ledger` now reads both folders and joins by identifier, so
      there was never a moment at which an old entry could be hidden. An
      identifier in both folders saying two different things comes back as one
      problem naming it and neither version is used. Two copies that say the
      same thing under different spellings are one entry, because they are
      compared on what they say and not on their bytes.

      The migration is in a new `changes.py`, written on the recovery pattern
      `approve_local.py` already uses: a note in the seat folder before any
      mutation, the pre-run head, a hash per path of what the run will write,
      validated on load, undoing only what still matches, and the note kept
      whenever a path holds the person's own words. It makes two saved changes
      on purpose, the move with no content change and then the rewrite, because
      `report.py` works out the "catches" number from which saved change first
      added each file, and a move saved together with a rewrite reads as a new
      file. `report.py` now recognises the move's own note and looks again
      under the older path rather than following renames, which was tried and
      miscounted a second entry whose content happened to be similar.

      Measured before wiring: twelve runs on a fresh sandbox base shaped like
      the real one (one entry, no corrections, no proposals) gave a median of
      0.211 seconds and a slowest run of 0.294, against a session start budget
      of fifteen seconds, and the question of whether it is needed is one
      folder listing at 0.09 milliseconds. The cost is not what decided it. It
      is offered inside "review my base" and carried out only by
      `--move-changes` after a yes, because nothing is applied to a base
      without one.

      Existing tests changed and why: every reference to the renamed constant,
      the renamed drafting step, and the two renamed settings, which is
      mechanical; five sentences a test pinned by their old words. The
      old-layout SC1 test in `test_stale_check.py` is byte-identical, proved by
      comparing it against the version on the previous save; its fixture's
      `add_entry` gained a `folder` argument defaulting to the older folder, so
      the class body and `entry_text` are untouched. A new-layout twin sits
      beside it. `test_stale.py` was not touched at all.

      Carried forward, recorded and not fixed: a seat on 0.2.6 reads a migrated
      base as empty. There is a test that freezes the 0.2.6 parse rule and
      asserts it, the CHANGELOG says so, and `docs/join-guide.md` makes every
      seat updating a condition of inviting a second one.

- [x] 2026-09-20: Unit 1.4 corrected after two outside reviews, suite at 1536
      passing. Two critical and five high data-safety findings, plus the
      mediums from the correctness review, every one of them reproduced on a
      sandbox base before it was touched. Nothing was committed.

      The rule the recovery follows now is one sentence: work out what every
      file is before touching any of them, and if one holds words the person
      has not saved, stop there, change nothing, and name that file. The two
      criticals were both the absence of that rule. One took a context change
      away and only then noticed the next path was theirs, leaving that change
      in neither folder with a deletion staged and every retry repeating it.
      The other put an older path back without looking at it and wrote over an
      unsaved edit to a change the move had not reached, then reported that
      everything said what it said before.

      Why the criticals were missed the first time: the failure injection only
      ever stopped at a commit. It now also stops between two file moves, part
      way through the rewrite, and between writing the dated record and saving
      it, and what an interrupted run is compared against is no longer entries
      and folder listings alone. It is also the confirmations, the flags the
      stale rules compute, the review dates, what git says is unsaved, and
      what is staged. Three of those comparisons would have caught a critical
      on their own.

      The rewrite is now a line-level rename that leaves every other byte
      alone, proved by a script that migrates a file with carriage returns,
      trailing spaces, a tab, runs of blank lines and the older setting name
      written inside the body, and shows exactly three lines changed. Before
      this it parsed the file and wrote a fresh one in its place, which
      reformatted the person's own writing underneath them.

      Two findings turned out to be better than the fix asked for. The rule
      that every file is named after the change inside it makes K9's own case,
      two files in one folder claiming one identifier, unreachable, so that
      test asserts the reachable form instead and the code is kept for a disk
      that cannot tell two names apart. And a value no writer could write out,
      a comma inside an affected path, now survives the move untouched rather
      than being a refusal, because the rewrite never writes the whole file.

      One new defect was found by the new tests rather than by the reviewers:
      git names a whole folder when nothing in it has been saved yet, so the
      run that had just written the first record read `corrections/` as
      somebody else's work. And a second by the case test: on a disk that does
      not tell `work/Decisions` from `work/decisions`, the move handed git a
      path it did not hold and failed. Both fixed.

      Not fixed, recorded: a seat on 0.2.6 still reads an updated base as
      empty, which is why the update now refuses on a base other people can
      reach until the owner says every seat is on this release.

- [x] 2026-09-20: Unit 1.4 corrected again after a second data-safety pass,
      suite at 1586 passing. The pass reran every first-pass critical and high
      and confirmed them closed, then found that the line-level rename I added
      to fix D-M3 had introduced one critical, three highs and four mediums.
      All reproduced before being touched. Nothing committed.

      The invariant went in first and closed a whole class at once: every
      renamed entry is read back with the both-spellings reader and refused,
      by name and before anything is written, unless every field and the body
      compare equal. A byte-order mark, the oldest kind of line ending, both
      spellings of one setting on two lines, and a quoted word where a plain
      one was expected were all files the rename turned into something the
      base could not read back, and the run reported success on every one.

      The critical was a folder named with a capital letter. Most Macs cannot
      tell that from the same name in lower case; git can. The note recorded
      the name git did not hold, so every question about that path came back
      no, the restore list came back empty, and the undo list deleted the copy
      anyway. Every change ended in neither folder, on every retry. Fixed by
      recording the real name and by writing the general rule into the code:
      no recovery removes a file unless another readable copy of that change
      is confirmed to be there at that moment. Put-back also restores before
      it removes now, so there is no instant in which a change is nowhere.

      The lesson I want recorded: my first-pass fix for the whole-file rewrite
      was right about the problem and created a new class of its own, because
      a rename that only touches some lines can leave a file whose remaining
      lines no longer make sense together. Writing a file is not finished
      until it has been read back. That is now the rule in this module rather
      than a thing I remembered to check in four places.

      Three findings improved on what was asked. A conflict now blocks the
      question, the yes, the "it already reflects this", and the local
      approval, rather than only being said out loud, because saying it while
      still accepting a yes was how the change got hidden for good. Quiet
      never hides a conflict. And a base left half updated is recognised as
      having work still to do, so the second half can be offered and finished
      rather than falling off the edge.

      Also added because the reviewer asked and it was right: a read-only
      check of the update the owner can run on a real base before deciding
      anything, and a way to say not now that is actually recorded.

- [x] 2026-09-20: Unit 1.4, third pass. The reviewer reran N1 to N8 and every
      low and confirmed them closed, could not fool the read-back check, and
      called it safe for the real base. Two mediums were left, neither losing
      data, and both are fixed. Suite at 1592 passing, nothing committed.

      R1: a run killed before its first save, then saved by the person
      themselves, wedged every retry with a sentence saying the file had never
      been saved and telling them to save a base with nothing left to save.
      The note can only record what this run did; it cannot record what
      somebody else did afterwards. So the question is now asked of the base:
      every file the run moved gone from what was last saved, every copy it
      made there instead holding what the run wrote, means the move landed,
      whoever saved it, and the run finishes.

      R2: giving up left behind the dated record it had written and not saved,
      because the rule about never deleting the last copy of something applied
      to it. That rule is about context changes, which are the thing that
      cannot be got back; the record of a run being undone is not one. Giving
      up now also keeps its note until nothing of its own is left, which is
      the rule putting work back already followed.

      One thing the fix exposed that nobody had asked about: the sentence for
      a half updated base claimed the settings still carried their older
      names, which is true when the run stopped before the rewrite and false
      when it stopped after. It now says only what it can know. That is the
      same mistake as the one I recorded last pass, in a sentence rather than
      in code: a claim about a state that varies, written as though it did not.

## Unit 1.5: Habit hooks (2026-09-20)

- [x] `stamp_entry` takes the run off a context change setup writes, and
      `review.approve` hands it nothing for the change step. P5, and the
      reason is Codex condition B: a matching run on a file and on a change
      settled the one against the other with nobody having read them side by
      side.
- [x] The closing question, its three sentences and its example, written into
      `skills/join/references/closing-rules.md` and read out of there by
      `join_flow.closing_question`, the same way the closing message already
      was. P4's wording is fixed word for word.
- [x] `join_flow.preview_change`: the four labeled lines, the four facts that
      are the person's to correct, and the whole entry as an artifact. P5.
- [x] `join_flow.reconcile_plan`, `reconcile_yes`, `reconcile_no`: one
      question per required document, a confirmation naming that one change,
      or a flagged document with a change prepared for it. Everything else
      affected is left flagged and counted in one line. P6 and ruling 4.
- [x] `join_flow.skip_the_closing_question` and `confirm.against_change`. Skip
      writes nothing, rests the reminder for the base's own threshold, and is
      outside the yes-rate denominator, which `tests/test_report.py` asserts
      on the number itself. P7.
- [x] `compose_proposal.stage_local_edit` asks one more thing, what changed
      and why. A strategic answer becomes the proposal's change entry and
      `decision_block` stops being unconditionally None; a typo answer leaves
      the proposal byte for byte what it was, which a test asserts by
      comparing the two files. P16.
- [x] The quiet-record ask moved out of the run that prepares changes and into
      the review, at most once a session, kept in the seat by session id. P17.
- [x] The baseline closing rewritten as three short lines, with a shared day
      named once, and Unit 1.2's tests rewritten with the reason recorded.
- [x] Join skill step 7 rewritten as steps 7 to 10, one request each, marked
      with the step, ask, artifact and change markers, and both of this unit's
      exemptions removed from `tests/plain_language.py`.
- [x] Atlas figures 5, 7 and 8, the join guide, the propose-change skill, the
      drafting prompt, the change entry template, and the changelog.

### Review

What I would flag to whoever picks this up. The closing question, the entry
preview and the reconciliation are library functions plus four new commands on
`skills/join/scripts/join.py`; the skill orchestrates them, because there is no
single call that can ask a person four things in turn. The owner's call on the
baseline wording is still open: the old sentence is preserved in this session's
report so he can take it back, and taking it back is one constant and two tests.

The lesson I carried in held. `FINDING_BASELINE` was one sentence naming four
dates, and on a base set up in one sitting it named the same day twice and the
same review date twice, which reads as though they were different days. The
rewrite has one form per state and a test in each state.

## Release A review, part two: the records folder, the gate, local approval, the moment of use (2026-09-20)

Findings A1/H1, H4, A6, M2, M3/A8 from `docs/reviews/2026-09-20-release-a-review-astra.md`
and the second reviewer's reproductions. Failing test first for every one.

- [x] A1/H1 step 0. Move every file the assistant writes with the file-writing
      tool out of GTM Base's own records folder, into a per-run folder the
      scripts make and name under the system temp location.
- [x] A1/H1 step 1. A check before the file-writing tools that refuses a write
      under the records folder, under a joined base's own repository folder,
      and under a joined base's assistant folder. Cheap miss path, no
      subprocess, always exits zero.
- [x] A1/H1 step 2. The gate fails closed: scope from the folder's own shape,
      the first backup always unreviewed, an unreadable sources-read marker
      blocks, silence and the dismissal date capped on load.
- [x] A1/H1 step 3. No integrity check on seat files this release; recorded.
- [x] A1/H1. Tighten the seat folder name rule where it is cheap.
- [x] H4. The note behind a local approval is checked the way the migration
      note is: a saved point written the one way a saved point is written,
      never an empty list of paths, and work counted as saved only when the
      saved work found also touches the paths the note names.
- [x] A6. A placeholder is never approvable, and the skills say to write the
      real replacement, show before and after, and only then ask.
- [x] M2. A document whose only problem is being written down twice gets the
      answer from the read check.
- [x] M3/A8. Preparing a fix records its own outcome, left out of the rate;
      answering an expired question issues nothing.
- [x] The hooks assertion, atlas figures 2 and 6, the changelog, the full run.

### Review, part two

What I would flag to whoever picks this up.

The check before a file write is a new module built the way the check before a
file read is built, with the same four rules and a miss path that runs nothing.
It is declared on one matcher naming four tools, and the documentation names
the path field of only one of them, so it reads the documented field and, as a
precaution rather than on the documentation's word, any other field whose name
ends the same way. It never reads anything holding what would be written, so a
file whose words happen to spell a path is not mistaken for a write to it.

The drafts a setup run asks the assistant for moved out of the records folder
rather than an allowance being cut into the check for them. That was the
choice offered and it is the right one: the consent records of that very run
sit beside those drafts, and an allowance beside them is an allowance that has
to be exactly right for ever. The scripts make a per-run folder under the
folder this computer keeps temporary work in, readable by that person alone,
and refuse a name already standing there that is a link, that belongs to
somebody else, or that anybody else can write to.

The one thing worth arguing with is the size of what the fail-closed rule
costs. The first backup is unreviewed always, so no send from a base completes
in this release at all, which means the part of the check that reads what a
send would carry cannot be reached from a base through the ordinary path. The
scenarios that cover that reading are run with the answer the first backup
review will give once it ships, through one helper in `tests/support.py` whose
docstring says exactly that and why. Nothing stands in for the rule itself.
The alternative was deleting that coverage, which would have left the reading
untested on the day the review ships.

Two spellings of the records folder on a command line still get past the text
rule and cannot be caught by any pattern: a name built out of a variable, and a
name joined together inside another program. That is said plainly in the
changelog and in the check's own docstring, and it is survivable only because
nothing the check decides is read out of that folder any more.

One thing in this change costs something real, and it is here as well as in the
changelog so that whoever reads this sees it. The record of having read
somebody's own documents now stops a send while it is young enough to still be
about now, whichever session wrote it, which is what the finding asked for. It
lasts twelve hours, nothing in this release clears it, and while it stands it
stops a send from every repository on the machine rather than only from a base.
Somebody who sets a base up in the morning and pushes an unrelated repository
in the afternoon is refused. Clearing the record when a setup run closes is the
obvious fix and it is not here, because it changes what the rule means, which
is the owner's call.

Decided the same day, after the note above was written. The record of having
read somebody's own documents does not block every repository on the machine.
An unreadable record blocks a send from anywhere, and a record this session
wrote blocks a send from anywhere, which is the rule as it has always been. A
record another session wrote, young enough to still be about now, blocks only a
send the check reads at all, which is one from a base or from a working folder
GTM Base made for itself. The reasoning is the owner's: a twelve hour block on
every repository is not something somebody working across many client
repositories in a day can live with, and the age rule buys little anyway,
because whoever can write that file can delete it just as easily as they can
put another session's name in it. The safeguard the base itself runs is
unchanged and keeps the age rule whole, since it has no session to compare
against and only ever runs inside a base.

## Release A, verification round (2026-09-20)

Two reviewers re-checked the first round of fixes. Four findings were still
open, and the fixes themselves had introduced several new defects. The list is
`scratchpad/release-a-findings-round2.md` and Astra's report is
`docs/reviews/2026-09-20-release-a-verify-astra.md`. A failing test came first
for every one of them, and a finding reachable only through a script has a test
that runs the script.

- [x] V4. A failed local approval put a document back the way it was last
      saved, which throws away a change somebody made by hand, because a hand
      edit is unsaved by definition. The exact bytes are kept beside the note
      before anything is written, those are what comes back, and the restore is
      read back and measured before the note is cleared.
- [x] V5 and N8. A document with an unrelated unsaved change further down was
      saved whole while the person had read only the part the change was about.
      Only a change somebody made by hand may have its own files unsaved now,
      and for those the whole of what saving the file would write is shown.
- [x] V6 and N9. Every flag that read somebody's words out of a file read any
      file on the computer. The scripts hand out the path now, inside a folder
      only the person can open, and a path they did not hand out is refused.
      Drafts are read from the run's own folder for the same reason, a folder
      somebody else stood up first is not used, and drafts whose run is gone
      are swept.
- [x] N2. The company name, the label on a piece of pasted text, and the files
      to draft from all stood on command lines where a document could choose
      what the shell did. The first two travel in words files and the third is
      named by the number the listing prints.
- [x] V9. The summary of the closing preview was ordinary text read out of a
      file somebody typed into. All of it is held apart as data now.
- [x] V10. The documented preview command left the base out, so it skipped
      finishing the change off and showed attribution that approving replaced.
      The base is required, the command is corrected, and the skill no longer
      calls who noted the change correctable.
- [x] A test that reads every command out of every skill and puts it to the
      parser of the script it names, which is the class of miss V10 was.

- [x] V1. The check before a file write used to tidy the path up and then check
      the tidy one, so a link named with a space in front of it reached the
      records folder. The name is used exactly as given, both spellings are
      checked against both spellings of every protected folder, and the folder
      a base keeps its history in is protected as an entry rather than only as
      a folder.
- [x] V2. The guard could be turned off by writing over its own code, because
      plugin code sat outside every protected place and a failure to start used
      to mean silence. The installed plugin's folder and the settings that load
      it are protected, a checkout of your own elsewhere is not, and when the
      check cannot run the wrapper refuses only what names one of those places.
- [x] N6. A base's own folders are protected by the shape of the folder rather
      than by a record that one write can empty, and so is the folder a base
      belongs with.
- [x] V3 and N1. What counts as a base is the base id in the folder's own
      settings, the joined list, or the saved history, and never one file in
      the working folder. An ordinary repository holding a file of that name is
      not a base.
- [x] V7. The first backup rule is checked against every folder a command would
      send from.
- [x] V8 and N4. The first draft carries a marker GTM Base writes, one command
      takes it off, and the wording replaces the part that went out of date.
- [x] V11 and N5. A day far enough in the future no longer defeats the quiet
      cap, and putting a reminder off works on a longer confirmation window
      because the day is clamped when it is written.
- [x] N7. A settings file with a second name is not read.
- [x] N3. A second change made by hand gets a name of its own.
- [x] N10. Recorded in the CHANGELOG as open: file tools from a connected
      server are not matched, and a command can still build a path no pattern
      reads. The fail-closed safety check and the client's own permission
      prompt are what stand behind both.

### What was decided along the way

A broken plugin must never stop ordinary work on the machine, so the wrapper's
fail-closed refusal applies only to a request that mentions a protected place
by name, and everything else goes through unlooked at. Development in a source
checkout that is not the installed copy keeps working, which is why only two
plugin folders are protected rather than every copy on the disk. A folder
shaped like a base is protected whether or not this account has joined it,
which changed one existing scenario. For a change somebody made by hand, the
whole difference from the saved version is what they approve, because that is
what saying yes writes down. The scripts choose where a person's words live and
the assistant never does.


## Release A, third look (2026-09-20)

Two reviewers checked the round above. Three findings stopped the release and
nine more had to be fixed before it. The list is
`scratchpad/release-a-findings-round3.md`. A failing test came first for every
one, built from the reviewers' own reproduction scripts, and three lessons of
that round are now built into the tests rather than only remembered: a test
payload is shaped the way the real client sends one, a documented command is
run rather than only parsed, and byte for byte compares bytes.

- [x] H1 and F1. The smaller check that runs when the real one cannot refused
      every file write on the computer, because the client puts the session
      transcript's path on every request and that path is always under the
      assistant's own folder. It reads the one file the tool was about to
      write now, matches the folder names as whole pieces of a path, allows
      anything it cannot read a path out of, and treats running out of time
      the same way.
- [x] H2. Approving a change made by hand saved the older prepared wording
      over newer unsaved work while showing the newer wording. A change made
      by hand is the unsaved document, so a document that has moved on since
      the change was prepared stops the run and the change is prepared again.
- [x] H3. The documented company step was refused every time for want of the
      run. The command carries it, the script says which argument is missing,
      and a test walks the whole setup skill as it is written and runs every
      command in it.
- [x] M1. One ordinary edit of the prepared change cleared the first-draft
      marker. This seat's own records carry it too, an absent marker on a
      change the check wrote reads as yes, and a change that would still add a
      part of its own is refused whatever the file says.
- [x] M3. A put-off day beyond the cap is thrown away on the way in rather
      than brought back, which is what made a forged day roll forward for ever.
- [x] M5. Who owns a document is read from the saved version, so rewriting the
      owner line by hand no longer makes its author the owner.
- [x] F3, M2 and L4. Identity asks every line of work the folder has saved, no
      command may set or take away the name a base is known by, and a question
      git was stopped from answering leaves a base in reach.
- [x] F2 and M4. A write to your own client settings is asked about rather
      than refused, with the two registry files on the same footing.
- [x] L1 and F4. The kept copy is bytes, measured and read back as bytes, and
      a document that cannot be copied stops the run.
- [x] L2. The drafts of a run that is gone are swept when a run begins and
      when one closes.
- [x] L3. A words file belongs to the base rather than to the window.
- [x] F5. The path that raises a change on a shared copy asks the same
      question about a first draft that approval asks.
- [x] F6. A folder is never named on a command line: the one somebody names
      travels in a file, and one chosen off a list is chosen by its number.

### What was decided along the way

Running out of time is not a broken plugin, so it is allowed unless the file
named is one of GTM Base's own. The installed copy's files are repaired by
installing the plugin again, and the sentence says so, because writing over
them is the one thing the smaller check will not allow. Your own client
settings are yours, so they are asked about rather than refused. A number is
not somebody else's text, so every choice off a list GTM Base printed is made
by number.
