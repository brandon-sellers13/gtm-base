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
- [x] Ship 0.2.0, then Brandon runs "set up my company base" for real; write docs/walkthroughs/2026-09-user-one-paste-path.md from that run (Ticked 2026-10-10: shipped long before Release A.)
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
- [x] Brandon answers the eight calls under "For Brandon" in the plan. The plan (Ticked 2026-10-10: decided, calls 1 to 8.)
      is written to the recommended answer on each, so the build does not wait.

### Release A
- [x] Unit 1.1: contract amendments, the six UX rulings, the frozen replay bar (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.1b: the UX standard and the lint (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.2: completion and closing (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.2b: approve a proposed change locally (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.3: quiet by default (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.4: the rename to context change, with a recoverable migration (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Unit 1.4b: the thin runner and its contract test (side track) (Ticked 2026-10-10: moved to the roadmap in revision 2.1.)
- [x] Unit 1.4c: the outbound sequence (side track) (Ticked 2026-10-10: moved to the roadmap in revision 2.1.)
- [x] Unit 1.5: habit hooks (Ticked 2026-10-10: shipped in 0.3.0.)
- [x] Security pass and correctness pass, then the live check, then the version bump (Ticked 2026-10-10: 0.3.0 on 2026-09-24.)

### Release B, behind the fidelity gate
- [x] Unit 1.6: selection fixes (Ticked 2026-10-10: built and merged into release-b, in 0.4.0.)
- [x] Unit 1.7a: scope and the segment inventory (Ticked 2026-10-10: built and merged, in 0.4.0.)
- [x] Unit 1.7b: umbrella and segment drafts, the unanswered-marker state (Ticked 2026-10-10: built and merged, in 0.4.0.)
- [x] Unit 1.7c: guarded adoption (Ticked 2026-10-10: built and merged, in 0.4.0.)
- [x] Unit 1.7d: recovery of an interrupted import (Ticked 2026-10-10: built and merged, in 0.4.0.)
- [x] Unit 1.8: the sweep of text no unit touched (Ticked 2026-10-10: built and merged, in 0.4.0.)
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


## Release A, final confirmation pass (2026-09-20)

One reviewer drove every path end to end and one took the code apart. Every
path but setting a base up worked. The list is
`scratchpad/release-a-findings-round4.md`. A failing test came first for every
item, built from the reviewers' own scripts.

- [x] N1 and N8. The check for a hand edit that had moved on applied the parts
      the change was described by a second time and asked for the answer to
      equal the document, which only holds where applying an edit twice is the
      same as applying it once. Six ordinary shapes are not. Nothing is
      applied now: the document is saved as it stands, byte for byte, and the
      bytes recorded when the change was prepared are what say it moved.
- [x] G1. Setting a base up printed a command for a file nothing handed out,
      and the walk carried a hand-written copy with the old spelling. There is
      a command for it now, the skill prints it, and the walk takes every
      command line out of the skill text, fills the placeholders from a table,
      runs them, and fails when one was never run.
- [x] G2, G3 and G4. Three passages telling the assistant to write words to a
      file of its own, a company file reused after it had been taken away, and
      a step that never named where its draft goes.
- [x] G5, which is the first round's A7 still open. No all-clear while a
      prepared change is waiting, and the change is named the way a person
      names one rather than by its identifier.
- [x] G7. Raising a change by hand on a base with no shared copy ends well.
- [x] N2 and N3. The smaller check refuses only the plugin's folder, the
      records folder, and the two folders inside a real base. It folds the
      spelling, joins a path onto the folder the session is open in, and reads
      a path under any name ending in the same word.
- [x] N4. A first draft can always be finished: approval and the command that
      clears it ask one question, and dropping, approving or raising a change
      takes its name off this seat's record.
- [x] N5. What counts as a first draft no longer rests on the origin written
      in the same unprotected file.
- [x] N6. The folder the client keeps its plugins in is asked about.
- [x] N7. The two ways of taking a whole section away are refused, and a
      command that only reads a setting is allowed.

### What was decided along the way

A change somebody made by hand is the document in front of them, so the
document is what is saved and nothing is rebuilt from the parts it was
described by. The walk may hold the knowledge that two documented commands are
alternative answers to one thing, because that is the flow rather than a copy
of a command, and it takes one of each per pass. The smaller check that runs
when the real one cannot has to refuse what the real one refuses and no more,
because a Mac without the developer tools stays in that state.

## Release A, confirmation round (2026-09-21)

Both reviewers confirmed the round before: every earlier finding closed, every
path working as the skills are written, and nothing blocking. Six small things
were left, and each one has a failing test of its own built from the
reviewers' scripts.

- [x] P1. Only a file named after an identifier GTM Base issued, carrying that
      same name inside it, and about documents that are all still in the base
      counts as a change waiting. One waiting on a document that is gone is
      said out loud, with the words to say to be rid of it.
- [x] P2. A refusal wins over a question, so a link under the folder the
      client keeps its plugins in, pointing into a base's own folders, is
      refused.
- [x] P3. A document with no headings in it says so, in the wording command
      and on the hand-edit path alike.
- [x] P4. The smaller check asks about the files that say which checks run.
- [x] W1. The walk supplies a file only where a skill asks for one in words,
      and a line naming the path a command printed fails unless that command
      came before it. Two skills printed the hand-out after the use, and both
      now print it first.
- [x] W2. A documented command for a script the walk does not know stops it.

### 2026-09-20, release A is ready for the go-ahead
- [x] Units 1.1 to 1.5 merged; five release review rounds fixed test-first; 1853 tests passing at 7476eb7.
- [x] Brandon: go-ahead for the version bump (release with Astra's third look outstanding, or hold for it). (Ticked 2026-10-10: released as 0.3.0.)
- [x] Bump the version, update the plugin on the one seat, republish the atlas. (Ticked 2026-10-10: 0.3.0.)
- [x] Brandon: run docs/walkthroughs/2026-09-release-a-live-check.md and fill in its results. (Ticked 2026-10-10: superseded; steps 1 to 6 ran on 2026-09-26 and 27, and steps 7 to 10 are on the one list for Brandon in the 2026-10-10 section.)
- [x] Astra's third look, when the Codex limit resets on 2026-09-26 or credits are added. (Ticked 2026-10-10: done, verify-3 and verify-4 on 2026-09-23, final on 2026-09-24.)

#### Review
Every review round found real defects, and the later rounds mostly found what the earlier fixes introduced: a guard that could be switched off through itself, a data-loss path in a relaxed check, words files that read any file, a fallback that refused every write, a moved check that refused ordinary edits. Three things would have caught most of them sooner and are now tests: payloads shaped like what the client really sends, documented commands run from the skill text itself, and byte comparisons that compare bytes.

## Release A, Astra's third verification (2026-09-23)

Astra's third look at 5f8076b found ten things that block the release and one
that does not. The list is `docs/reviews/2026-09-23-release-a-verify-3-astra.md`.
A failing test came first for every one, built from Astra's own scenario, in
the order R10, R7, R9, then R1 to R6, R8, R11. Nothing is saved or sent.

- [x] R10. A hand edit that takes a part out, or edits the first of two parts
      with the same heading, can be prepared and approved. The documents come
      from the changed files and their bytes; the summary can say a part is
      taken out and which of two same-named parts it means.
- [x] R7. The wording of a prepared change can be revised any number of times.
      Each revision is held to the same rules, moves the shown value on, and
      the words file goes only after the wording is written.
- [x] R9. One numbered order for files, folders, and proposed places, printed,
      kept, and taken back alike. Every listing prints the folder numbers. The
      walk now runs the additions sentences describe and checks every flag a
      sentence names, and what it found is corrected in the skills.
- [x] R1. A failed approval puts back the index entry and the permissions,
      checks both, and keeps the recovery note when either cannot come back.
- [x] R2 and R3. The write check compares every place a known base keeps its
      history before the name shortcut, and knows a base whose map is gone by
      the same three questions as the send check. The miss path starts nothing.
- [x] R4. An error in the write check ends in the wrapper's failure status.
- [x] R5. The smaller check takes out dots and follows links before comparing.
- [x] R6. The config command is parsed: action, file, key, both section names.
- [x] R8. The whole difference is a literal fenced diff, and whitespace-only
      changes are shown again visibly.
- [x] R11. One validated inventory of what is waiting, read by the closing and
      both review readers.
- [x] CHANGELOG sentences Astra's table flags are corrected in place, and the
      still-open list names concurrency, words-file provenance, first-draft
      provenance, and the untested ask.
- [x] Atlas figures 6 and 7 brought up to date, not republished.
- [x] Brandon: an outside look at this round's fixes, since each fix to a (Ticked 2026-10-10: Astra's verify passes.)
      safety rule is new code.
- [x] Brandon: run docs/walkthroughs/2026-09-release-a-live-check.md. (Ticked 2026-10-10: superseded; steps 1 to 6 ran on 2026-09-26 and 27, and steps 7 to 10 are on the one list for Brandon in the 2026-10-10 section.)

#### Review
Nine of the eleven were the round before's fixes falling short at an edge the
tests did not reach: a rollback that stopped at bytes, a shortcut placed before
the comparison it was meant to protect, a summary keyed by heading, a words
file consumed before the refusal, a walk that read commands but not sentences.
Run over the committed skills, the extended walk flagged documented additions
in three of the four walked skills: folder names on the command line, a flag
that puts somebody's words on the command line, a folder narrowed by a name the
script refuses, and additions attached to the wrong command.

## Release A, Astra's fourth verification (2026-09-23)

Astra's fourth look at bd3bbcf found nine things that block the release and
one that does not. The list is `docs/reviews/2026-09-23-release-a-verify-4-astra.md`.
A failing test came first for every one, built from Astra's own scenario,
with a test of the ordinary path beside it, in the order N8, N5, N6, N4, N2,
N1, N9, N3, N7, N10, then the composed removals. Nothing is saved or sent.

- [x] N8. The index entry is read with `ls-files -s -z`, so a document named
      with an accent can be approved.
- [x] N5. `-t path` is read as an option and its value; opening the settings
      to edit is refused only in a base.
- [x] N6. A subsection header is kept whole, so `[gtmbase "demo"]` is not the
      name of a base.
- [x] N4. Narrowing by folder number uses the listing's own top-folder rule,
      `.` included; a folder to add must be the survey folder or directly in
      it, and anything else is refused with a sentence of its own.
- [x] N2. Approval parses, checks, hashes, and writes from its one reading.
- [x] N1. This run's own index value and permissions are kept before it
      writes; recovery restores each only from the kept or this run's value,
      keeps newer permissions, and keeps a newer index entry and the note
      until that entry is saved.
- [x] N9. A words file is claimed by renaming it before it is read; the
      wording command gives it back on a refusal and says when it could not
      be taken away.
- [x] N3. A write straight into the session's own repository's history
      folder kept elsewhere is asked about its saved history before the
      shortcut.
- [x] N7. The shell fallback follows each existing piece before `..`, and
      follows a link to a file at the end of a path.
- [x] N10. The walk fails on a sentence flag that belongs to no command;
      four are assigned by name and the update's two answers, the folder
      hand-out, and link without a base are run.
- [x] Shared hand edits: removals are numbered against the document as it
      stood, on this computer and on a shared copy.
- [x] CHANGELOG lines 273, 275, 277, 279, 281, 285, 287 corrected in place;
      the fourth look added; the still-open list says what is left.
- [x] Atlas figures 6 and 7 brought up to date, not republished.
- [x] Brandon: an outside look at this round's fixes. (Ticked 2026-10-10: Astra's verify passes.)
- [x] Brandon: run docs/walkthroughs/2026-09-release-a-live-check.md. (Ticked 2026-10-10: superseded; steps 1 to 6 ran on 2026-09-26 and 27, and steps 7 to 10 are on the one list for Brandon in the 2026-10-10 section.)

#### Review
All ten sat in code the round before added or at an edge its tests did not
reach: a restore that never asked what was there now, a second read of a file
the first read had already hashed, a words file consumed by its name rather
than by what was read, a parser that knew long options but not short ones, a
folder rule that differed between the listing and the narrowing, git's display
quoting read as a name, and a check that asked about every known base except
the one the session was standing in. Found in passing and left open: a hand
edit to a document with an accent in its name is still refused.

## Names git quotes, read as the names they are (2026-09-24)

- [x] Every call that reads names out of git's output asks for records ending
      in a NUL, read by `gitcmd.nul_fields` and `gitcmd.status_entries`
      (a rename's old name is a field of its own); patch headers are read
      back through `gitcmd.unquote_path`.
- [x] Hand edit through both scripts on `stratégie.md`, and the ordinary name.
- [x] One test per changed call site, in tests/test_quoted_names.py and
      tests/test_session_start.py, each failing on the code as it was.
- [x] CHANGELOG entry; the accent line taken off the still-open list.
- [ ] Brandon: decide the shape of a confirmation line for a document whose
      name holds a space. It separates its values with spaces, so such a
      document can be prepared and shown but not approved or confirmed. The
      two tests for it are marked as expected to fail until then.

#### Review
Git's quoting was read as a name in eight places, not two. Two of them were
worse than a refusal: an update carrying a settings file with an accent in its
name was taken, and a file with such a name in a folder that never leaves was
not recognised by the check before sending. A name with a space turned out to
be stopped a second time, by the confirmation line's own format, which is left
open on purpose.

## A name with a space, refused up front (2026-09-24)

- [x] One shared sentence and check in formats.py (`NAME_WITH_A_SPACE`,
      `name_has_a_space`), registered in tests/plain_language.py. The
      confirmation line format is unchanged.
- [x] Refused at the earliest point of every path that ends in a
      confirmation line: the hand edit (library and script, before either
      words file is read), local approval show and approve, a yes to a
      question (before it is used up), the closing yes against a change, the
      line written with a new document, moment "it already reflects this" and
      "fix it first" (library and script), and the closing reconciliation yes.
- [x] The review and the moment check still list or flag such a document,
      offer only the rename, and issue no question for it.
- [x] The two expected failures in tests/test_compose_proposal.py now assert
      the refusal; tests/test_names_with_a_space.py covers the other entry
      points.
- [x] Join skill says a folder to add has to sit directly inside the one named.
- [x] CHANGELOG entry, and the still-open line updated.
- [ ] Brandon: the record format change that lets such a name be kept, in a
      later release.

#### Review
Full suite: 1987 tests, OK, no expected failures left. The rename sentence
names no document, because names.py reads "our strategy.md" as "your our
strategy" and an accented name as "one of your documents"; the flag or review
line it follows already names the document.

### 2026-09-24, release A shipped
- [x] Astra's reviews at HEAD and their fixes (R1 to R11, N1 to N10, quoted names, names with a space refused up front).
- [x] Astra's narrow final pass: ready to release.
- [x] Version 0.3.0 in both manifests and the library; CHANGELOG section dated; 1987 tests; pushed as 45d4454.
- [x] Plugin updated on Brandon's machine (0.2.6 to 0.3.0); atlas republished.
- [x] Brandon: restart, then the live check; fill in its results. (Ticked 2026-10-10: superseded; steps 1 to 6 ran on 2026-09-26 and 27, and steps 7 to 10 are on the one list for Brandon in the 2026-10-10 section.)
- [ ] Release B: Unit 1.6 onward, plus the confirmation line format that allows names with a space. (Noted 2026-10-10: Unit 1.6 onward is built and in 0.4.0; the format for a name with a space is still open, the two items above.)

### 2026-09-25, revision 2.2: the CLASS context standard
- [x] Plan revision 2.2: Unit 1.5b, P38, calls 9 to 11; roadmap kinds mapped to the standard; docs/ux-standard.md ties every step to CLASS.
- [x] Brandon: calls 9 to 11. (Ticked 2026-10-10: decided 2026-09-25.)
- [x] Unit 1.5b, after the live check and before Unit 1.6. (Ticked 2026-10-10: built and merged, in 0.4.0.)
- [x] 2026-09-25 revision 2.3: Unit 1.5b widened to lay a base out by the five CLASS parts (calls 12 to 14 decided).

### 2026-09-26, live check paused at step 2
- [x] Fix first: every skill script refuses a linked folder (`resolution.joined` required; a linked resolution carries root and id but joined False). Accept a linked resolution in all six scripts, and run every script-level test and the skill walk from a linked folder as well as from inside the base. (Ticked 2026-10-10: 0.3.1.)
- [x] The review never makes the update offer that --check-move says it would make. (Ticked 2026-10-10: 0.3.1.)
- [x] The skills tell the assistant to relay the review's sentences, not summarize or advise. (Ticked 2026-10-10: 0.3.1.)
- [x] Release as 0.3.1, then Brandon resumes the live check at step 2. (Ticked 2026-10-10: 0.3.1 on 2026-09-26.)

### 2026-09-26, 0.3.1: the linked folder
- [x] Finding 1: the six scripts (stale_check.py, confirm.py, propose.py, approve_local.py, moment.py, seat.py) accept `resolution.active`, so a folder linked to a base works exactly as the base's own folder does. The NOT_JOINED sentence stays for a folder that is neither. gate.py keeps `.joined` on purpose: a linked folder is the person's own repository, which the gate does not read.
- [x] A `--staging` path inside the base is read against the base root (`paths.in_the_base`), not the folder the command runs in. Document paths already were (`moment.context_path_of`); no other script reads the current folder after resolving.
- [x] Finding 2: the review makes the update offer when nothing is due, once, after the nothing-due sentence and the quiet record ask, in a dry run too.
- [x] Finding 4: `--check-move` counts context changes in words (`changes.counted`) and names no identifier; the sentence after the move names no folder.
- [x] Finding 3: stale-check, confirm and propose-change skills say commands run from the folder the person works in, base or linked, and that the assistant relays each sentence as it is, never reads out a path, an identifier or a `[for the assistant]` line, and adds no advice. "From inside the base" is gone; the join skill says not to go looking for the base.
- [x] Tests: tests/test_linked_folder.py (each script from a linked folder, relative staging path, refusal kept, the offer when nothing is due in both modes, the skills' wording); the skill walk runs from a linked folder too (TestTheSkillsFromALinkedFolder); `support.where_a_script_runs` lets every script-running module run from a linked folder (the eight modules, with the skill walk and the new module, pass that way: 544 tests), and tests/run.sh runs the 22 classes in them that start a script a second time that way, with a test that fails when a class that starts a script is missing from that list.
- [x] CHANGELOG: draft Unreleased (0.3.1) section. Version not bumped.
- [x] Orchestrator: review, commit, release as 0.3.1, update the installed plugin. (Ticked 2026-10-10: 0.3.1.)
- [x] Brandon: resume the live check at step 2. (Ticked 2026-10-10: steps 2 to 6 run on 2026-09-27.)

#### Review
The linked folder was refused in six places for one reason, a check for a base joined in that very folder, and the tests could not see it because they all ran inside the base. The same tests now run from a linked folder, made with `machine.link_content` as the join skill makes one. A path inside the base given to `--staging` had the same blind spot and is fixed with it. The review's early return skipped the offer; it now makes it once in both modes. Not fixed here: the review's line for a prepared change hands the assistant the change's identifier, not a path, so the assistant has to build the path itself from the folder the skills name.
Full suite after the change: 2016 tests OK in 739 seconds, then the second run from a linked folder, 99 tests OK in 98 seconds (tests/run.sh exit 0).

### 2026-09-27, 0.3.2: files the computer makes on its own (branch fix-0-3-2)
- [x] Blocking finding of live check step 5: one shared predicate, `unsaved.look` in the new lib/gtmbase/unsaved.py, runs `status --porcelain -z --untracked-files=all` and leaves out untracked clutter (`.DS_Store`, `._*`, `Thumbs.db`, `desktop.ini`, `Icon\r`, and anything inside `.Spotlight-V100`, `.Trashes`, `.fseventsd`). A tracked clutter file that changed, or one lined up to be saved, still counts.
- [x] Routed through it: approve_local `_ready_to_write_here` (hand edit and local approval), changes `_ready_to_write` (the Unit 1.4 move, its offer and its read-only look), changes `_anything_left_over` and `_theirs_before_finishing` (recovery; the folder walk also skips clutter), stale_check's pull before a review, review `ready_to_write` (setup writes, the onboarding note, and confirm's closing yes), confirm `_add_to_the_local_copy`, session_start's update. location `_holds_content` skips clutter; create_base `_copy_template` never copies it. No `git add` in the library stages clutter: every add names exact files, and create_base's `add -A` runs on a fresh folder behind the template's ignore file.
- [x] Both company-base templates' `.gitignore` list the clutter (`Icon[^ -~]` for `Icon\r`, checked against git). Existing bases: ignore files untouched, no offer in this release (said in the CHANGELOG).
- [x] Refusals name the unsaved files (`unsaved.where_sentence`): approve_local (also its recovery refusal), changes, stale_check, confirm's closing yes. Document names via names.document_name, other plain names as they are, the rest "one of your files", clutter "a file your computer made on its own". New sentences registered in tests/plain_language.py.
- [x] Skill relay rules (a) to (d) in stale-check, propose-change and confirm SKILL.md; the stale-check table no longer asks about other seats unprompted.
- [x] Tests: tests/test_os_clutter.py (failing first, 36 tests), one class added to tests/run.sh's linked-folder list and to test_linked_folder's runner map; six existing assertions now expect the named refusal.
- [x] Logic atlas captions updated (not published). CHANGELOG draft Unreleased (0.3.2). Version not bumped.
- [x] Orchestrator: review, release as 0.3.2, update the installed plugin. (Ticked 2026-10-10: 0.3.2.)
- [ ] Later unit: an offered, undoable change adding the clutter lines to an existing base's ignore file; the rest of the live-check findings.
- Note: a fresh checkout has no templates/company-base/work/inbox or work/proposals folder (their .gitkeep files are ignored by the template's own ignore file), so tests/test_scaffold.py fails there until the folders are made by hand. Not fixed here.

#### Review (0.3.2)
One correctness review of the diff. Fixed, each with a test in tests/test_os_clutter.py: a context file whose name has no words (`-.md`) made naming the files raise instead of refuse; the stopped-move refusal (`changes.THEIR_WORDS`) printed a raw path, now a plain name ("one of your context changes" for a change's file, three migration tests and one quoted-name test now assert the identifier is absent); two files reading out the same name were counted as one; names made of dots or spaces were read out; `_copy_template` made empty clutter folders. Accepted and written in the CHANGELOG: a new document in a new folder under context now counts as part of a hand edit, and clutter tracked on the shared copy meeting untracked clutter here gives the could-not-update sentence (no data lost). Not done: an offered change to existing bases' ignore files.

### 2026-09-27, 0.3.2: Astra's review (docs/reviews/2026-09-27-release-0-3-2-astra.md, not ready) and the seat folder
- [x] Finding 1: clutter is only a regular file (never a link or folder) named exactly `.DS_Store`, `Thumbs.db`, `desktop.ini` or `Icon\r`, or a `._` file that starts with the AppleDouble bytes 00 05 16 07. No folder or folder-contents exemption. `context/._notes.md` holding markdown, `context/.Trashes/notes.md` and a link named `.DS_Store` all count as unsaved and stop an approval.
- [x] Finding 2: both templates ignore only the four exact names (no `._*`). All three fast-forward updates (session start, the review, a yes on a base with no shared copy) pass `--no-overwrite-ignore`; an ignored local file survives an incoming saved file of the same name, and a source scan fails if a merge or pull in the library lacks the flag.
- [x] Finding 3: refusals never repeat an arbitrary name. Context documents by `names.document_name` (now `fullmatch`), everything else counted; the read-the-name branch is gone. Astra's instruction-shaped name and a trailing newline are tested.
- [x] The seat folder: tests/support.py points the seat folder at a temporary one before any test runs, always; tests/run.sh makes that folder, and fails the run if either run wrote into it. tests/test_seat_isolation.py proves it inside temporary folders; the real seat folder is never read. The guard's first full run caught two offenders, both now given a temporary seat folder: test_sources (wrote its read marker) and test_gate's check of this repository (made the seat folder). test_paths got the same guard as on the unit-1-7d line.
- [x] Orchestrator: review, release as 0.3.2. (Ticked 2026-10-10: 0.3.2.)

### 2026-09-27, 0.3.2: Astra's confirmation (docs/reviews/2026-09-27-release-0-3-2-verify-astra.md)
- [x] Findings 1 and 2 closed by Astra. Finding 3 still open for an ordinary `.md` name under context, now fixed in the unsaved refusal only: a context document is named by a fixed label only when the product knows its path (the two required documents, the map, the nine context-standard documents of Unit 1.5b, and a segment under the segments folder whose slug is lowercase words joined by hyphens, at most five and forty characters); every other file under context is "one of your documents", counted like the rest. names.py's other callers are unchanged; the product-wide hardening is for a later unit.
- [x] Unit 1.5b: check the nine standard labels in unsaved.KNOWN_DOCUMENT_LABELS against the words that unit settles on. Done in the merge of main into release-b: the labels are names.KNOWN_DOCUMENTS as Unit 1.5b set them, current and older paths.

### 2026-09-27, Release B list additions from Astra's review of 0.3.3
- [x] Unit 1.7e, a yes only a person can give (Astra 0.3.3 finding 2, deferred from 0.3.3 to Release B by the live-check session; Brandon may veto the deferral): a UserPromptSubmit hook records when the person actually sends a message, and every approval flow (confirm, approve_local, the closing, adoption, segment drafts, the move, 0.3.3's change recording) refuses a yes unless a message from the person arrived after its showing. Built before Astra's review of all of Release B. (Ticked 2026-10-10: rebuilt as option D, calls 57 and 58, in 0.4.0.)
- [x] When 0.3.3 merges into release-b: every save Release B added (the layout move, approve_adopted, finish_adopted, confirm_saved, put_back paths, call 29's segment approvals) goes through 0.3.3's hook-free commit helper (Astra 0.3.3 finding 1, critical), each with a test that a planted commit hook does not run.
- [x] Unit 1.8 also covers: sentences in changes.py (`DOCUMENT_TAKEN`, `DESTINATION_TAKEN`, `UNREADABLE_ENTRY`, `CANNOT_PUT_BACK`, `CANNOT_FINISH`) and names.py's other callers must never read a name out of a file name. (Ticked 2026-10-10: Unit 1.8.)
### 2026-09-27, 0.3.3: record a context change at any time (branch fix-0-3-3, on fix-0-3-2)
Built on fix-0-3-2 (the clutter fix and the seat-folder guard), which releases as 0.3.2; this is 0.3.3. Item 2 of the brief (clutter) is fix-0-3-2's and is not touched here.
- [x] Library: `record_change.py` for the any-time path, reusing the closing's pieces (the four lines and the whole-entry showing, the free identifier, the entry written with no run, `where_to_write_the_entry`, `reconcile_plan`/`reconcile_yes`/`reconcile_no`, `unsaved.where_sentence`). The entry is built from the person's words (never through the model-draft parser, which refuses a person's own dash or word), screened for contact details and keys, held in the seat folder between the showing and the yes, and bound to what was shown. (Ticked 2026-10-10: 0.3.3.)
- [x] `reconcile_plan` and `confirm.against_change` take the any-time path's wider set (every affected context document this seat owns), the closing's two-document rule unchanged. (Ticked 2026-10-10: 0.3.3.)
- [x] stale_check.py: `--new-words-file`, `--record-change-ask`, `--record-change-documents`, `--record-change-preview`, `--record-change`, `--record-change-leave`, `--record-change-answer`. (Ticked 2026-10-10: 0.3.3.)
- [x] A base with a shared copy is refused with one sentence at every step (the closing only ever writes a local save and has no path to a shared copy). (Ticked 2026-10-10: 0.3.3.)
- [x] stale-check SKILL.md section "Record a context change", description triggers; injection.md one line for the assistant. (Ticked 2026-10-10: 0.3.3.)
- [x] Tests: tests/test_record_change.py end to end through the real script, from the base and from a linked folder (run.sh list and test_linked_folder runner map), both layouts, shared copy, yes/no/not now, nothing written before the yes, no run id, flagged at the moment of use and in the review. (Ticked 2026-10-10: 0.3.3.)
- [x] Lint registry, CHANGELOG "Unreleased (0.3.3)", logic atlas figures 5 and 7. (Ticked 2026-10-10: 0.3.3.)
- [x] Two reviews (correctness, security), fixes with tests, full suite twice OK. (Ticked 2026-10-10: 0.3.3.)
- [x] Built as planned above (commits 4d47028, then the docs commit, then the review fixes). Item 2 of the brief is fix-0-3-2's, released as 0.3.2.
- [x] Merge main (0.3.2 release) into fix-0-3-3: the merge command was refused by this session's permission check; left for the coordinator. (Ticked 2026-10-10: merged.)

#### Review (0.3.3)
Two reviews. Security: S1, file names read out as instructions in the documents list, the questions and the answers (fixed: `record_change.safe_name`, only safely named documents are asked about); S2, `--record-change answer` settled any change for any owned document (fixed: answers bound to what the yes asked, once, origin manual only). Correctness: words files thrown away before a refusal that asks for a retry (fixed: claimed, given back on refusal); a name with a space asked about and never recordable (fixed: left flagged); the second screen ignored the allowlist (fixed); a refused correction left the earlier showing recordable (fixed); rollback could delete a file it did not write or undo a save that went through (fixed); identifiers named by corrections or prepared changes (fixed). Each has a test in tests/test_record_change.py. Not done: `--happened-on` carries a date typed on the command line (validated as a date); the closing's own `free_entry_id` still ignores confirmation lines.

### 2026-09-27, 0.3.3: Brandon's calls on the open questions (after merge e828d7a)
- [x] Q3: the any-time path shows only the four labeled lines inside the data fence, then the one ask; no identifier, path or settings block. The yes stays bound to the whole entry (a comment in record_change.preview says why that is safe). The closing's preview is unchanged.
- [x] Q1, Q2, Q4 kept as built; Q5 wording accepted.

### 2026-09-26, Unit 1.5b: the base laid out by the five CLASS parts
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.5b (revision 2.3). Built on its own branch; not merged, not released.
- [x] Constants and one layout module: the new paths (`context/icps.md`, `context/positioning.md`, `learning/changes`, `learning/corrections`, `learning/lessons`, `access/stack.md`, `skills/`, `standards/`), the older ones kept read-only, and the one table from each older document path to its new one. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Read both layouts: entries from three folders, records from two, every path a change, a confirmation line, a record, a seat setting or a staged change names followed to where the document lives now; the two required documents found in either place. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Write one: setup, entries, records and the onboarding note go to the new paths; the change identifier setup works out stays the same. (Ticked 2026-10-10: Unit 1.5b.)
- [x] `skills/` refused by the trust check (so by every pull), by the file-writing hook and by the check before a send; the empty folder and its placeholder allowed. (Ticked 2026-10-10: Unit 1.5b.)
- [x] One offered move in "review my base" that takes a base on `work/decisions`, on `work/changes`, or half moved all the way to the current layout: `changes.py` generalized, not duplicated (a pure rename saved first, the settings rewrite second, the dated record third), with its recovery and read-back rules. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Both company-base templates, the skills and prompts, names for every new kind. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Tests: tests/test_context_standard.py for every scenario in the plan; tests naming old paths updated; the old-path lint. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Atlas figures 1 and 7, the roadmap, the join guide, the UX standard, a draft Unreleased CHANGELOG section. (Ticked 2026-10-10: Unit 1.5b.)
- [x] Full suite, both runs. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, Unit 1.5b (2026-09-26)
- [x] Constants and `layout.py`: the current paths, the older ones read only, and one table from each older document path to its new one.
- [x] Both layouts read: entries from three folders, records from two (found where first added, across both names, and accepted by the change that last added or edited them, never by a rename), every path followed to where the document lives, both required documents found in either place, and a prepared change naming an older path followed in memory with the prepared file untouched.
- [x] One layout written: setup, entries, records, the onboarding note; setup's change identifier seeded from the older profile path so a resumed run agrees; setup refuses to write a document already present at its other path.
- [x] `skills/` refused by the trust check (so every pull and every open), the file-writing hook and the check before a send; the folder and its placeholder allowed.
- [x] `changes.py` generalized: one offer, one move from `work/decisions`, `work/changes`, both, or a half-finished 0.3.x run; rename, then settings and the map paragraph (only when still the one GTM Base wrote), then the record; schema 2 note, schema 1 notes finished as 0.3.x would and carried on.
- [x] Correctness review of the move (a subagent): note paths now limited to exactly what a run writes, older copies to take away that somebody edited are theirs, a 0.3.x rewrite-only note finishes, a failed save after something landed keeps its note, same-name-different-case destinations refused, acceptance query keeps every change but a rename. Each has a test.
- [x] Templates, skills, prompts, names; atlas figures 1 and 7 (not republished); roadmap; join guide; UX standard; draft Unreleased CHANGELOG section.
- [x] tests/test_context_standard.py (every plan scenario) and the old-path lint; tests naming old paths updated; a support helper names the profile in a prepared change the way the test bases hold it.
- [ ] Brandon: the words listed in the hand-back report; then the live move of the Gridwise base through the offer. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)
- [x] Orchestrator: review, merge after the live check, version bump, atlas republish. (Ticked 2026-10-10: merged into release-b; the bump is 0.4.0.)

Review: 1.4's move was generalized rather than a second one written, so the recovery rules Astra hardened carry over unchanged and all 168 of 1.4's migration tests pass against it. The worktree needed its ignored `work/inbox` and `work/proposals` template folders created by hand for tests/test_scaffold.py, because the template's own ignore file keeps their placeholders out of the repository; a fresh clone fails that test on main too.

#### Astra's review of Unit 1.5b (2026-09-26), all thirteen findings
Review: docs/reviews/2026-09-26-unit-1-5b-astra.md in the main checkout. Every finding has a test in tests/test_unit_1_5b_review.py or tests/test_context_standard.py that fails on fb13268 and passes now.
- [x] 1 Giving up never brings a copy back over words of theirs; every restore is checked again just before.
- [x] 2 The dated record takes the next free name rather than writing over a file; the note records the name used.
- [x] 3 A change written down twice names its documents where they live now.
- [x] 4 Acceptance of a record ignores renames and deletions; confirmation dates are identical before and after the move.
- [x] 5 The ownership list's rules follow the move with their owners, and the new parts get the records rule's owners.
- [x] 6 The check before a send reads every outgoing piece of work, merges included. The gate had no refusal for a plugins folder, so there was no second hole of that shape to close.
- [x] 7 No sentence the move says reads out a file name: documents by their plain name, context changes by a validated identifier, anything else "one of your records" or "one of your files".
- [x] 8 The skills placeholder must be an empty ordinary file at the trust check, the file-writing check, an incoming update, and a send.
- [x] 9 The skills refusal holds for a joined base whose map is gone, and in the smaller shell check.
- [x] 10 The source map is screened for keys and tokens at the file-writing check and on an incoming update.
- [x] 11 A prepared change is resolved again against the shared copy it is written into.
- [x] 12 The move writes the starter source map with the map's owner, never over an existing one.
- [x] 13 One stop test enumerates all 28 steps of a run (moves, removals, staging, saves, file writes, the note written and taken away) and stops before and after each, asserting each stop fired.

#### Astra's confirmation pass on Unit 1.5b (2026-09-26), five findings
Pass: docs/reviews/2026-09-26-unit-1-5b-verify-astra.md in the main checkout. Tests in tests/test_unit_1_5b_verify.py, each failing on 2a6fd91 before its fix.
- [x] 1 Giving up looks at each file again right before a put-back or a removal, in the undo loop and in putting back, and names what holds their words.
- [x] 2 Ownership defaults go before every existing rule, with owners only from the broad records rule, and none without one.
- [x] 3 An edit to the source map is judged by the whole file it would leave.
- [x] 4 The source map is screened for credentials only; ordinary lines pass at Write, Edit, MultiEdit and a real incoming update.
- [x] 5 The shell fallback needs the map and a history, or a registered root, before it calls a folder a base.
- [x] The merge regression from finding 6 of the first review: a merge that adds a skill neither side had, taken away after; it fails on fb13268.
- [ ] Open: the check before a send still refuses a source map holding a link in angle brackets, because every outgoing file is held to the hidden-content rule.

### 2026-09-26, Unit 1.6: selection fixes
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.6 (requirements P24 to P26). Built on its own branch, `unit-1-6`, on top of the unmerged Unit 1.5b; not merged, not released.
- [x] Survey: plans and metrics count only beside a profile, persona, or positioning file (`plans-alone` note); each place says what it mostly holds from paths only; per-file candidates and same-stem version sets in the survey output; the first heading read in one bounded read of 4096 bytes as well as forty lines.
- [x] Provenance: the listing and the yes record `choice` (explicit or plain-yes), the folders the person named, and a manifest digest. `--keep <place number>` names the places to use. An explicit choice is never narrowed again and gets a plain count; a plain yes to a list that is itself too large is narrowed once (the old rule let any plain yes with folders past it); a list shown after the yes stops reading with `codes=asks-again` until it has a yes of its own.
- [x] Preview: the count, the files left out, and why a draft reads a limited amount; one version of each document (final over a newer date, else the newest), each version left out named and a body conflict said aloud, after consent only; the narrowing question printed only after a plain yes; assemble no longer repeats it. Preview and assemble share one chooser, so they read the same files.
- [x] `order_sources`: templates and read-me files last for every step.
- [x] Join skill steps 5 and 6 rewritten as 5, 5b, 5c, 6, 6b, each opening with its purpose and asking one thing; the consent paragraph cut to three short lines and the question; Unit 1.6's four exemptions removed; new sentences registered with the lint.
- [x] Tests: every plan scenario (tests/test_sources.py, tests/test_join_setup_flow.py, tests/test_drafting.py), including a guarded reader that fails any survey read past its byte cap.
- [x] Atlas figure 7 (not republished), the reading rules, the join guide, the draft Unreleased CHANGELOG.
- [ ] Brandon: the words listed in the hand-back report; then the live survey of ~/Gridwise. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)
- [x] Orchestrator: review, merge after 1.5b, version bump, atlas republish. (Ticked 2026-10-10: merged into release-b; the bump is 0.4.0.)

### 2026-09-26, Unit 1.7a: scope and the segment inventory
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.7a (requirements P18, P19, P23), with call 11's path: segments under `context/icps/`, not the plan text's older folder. Built on its own branch, `unit-1-7a`, on top of the unmerged Units 1.5b and 1.6; not merged, not released.
- [x] Scope, steps 1 and 2 of the plan's order: `join.py scope` holds the answer in the run folder (a short name, or `--whole`), refused once the list is agreed to; the survey prints `splits=` and one sentence only when two or more places each keep their own copy of a positioning document of the same name beside a customer profile; the listing and the yes record the scope beside the places dropped; the approved profile carries `covers:` from the held answer and never from a draft.
- [x] The inventory, step 3: `join.py segments` numbers the documents on the agreed list that each describe one segment (versions once, templates never); `join.py segments-settle` reads one line per segment (adopt, draft, or leave-out; a number or a hyphen; the name), checks every name and file name before anything is kept, saves it in the run folder, and reads it back.
- [x] Slug safety in `segments.py`: letters A to Z, digits and single hyphens after case and unicode folding; collisions, empty names, trust-refused names and reserved device names refused with one sentence naming the segment; a slug read back from the file is checked again.
- [x] `validate.validate_covers`; `drafting.parse` reads `covers` on the profile only; `sources.Consent` carries the scope; words-file kinds `scope` and `segments`; both templates hold `context/icps/.gitkeep`; `TEMPLATE_TREE_DIRS` gains the folder.
- [x] Join skill steps 5a and 5d; new sentences registered with the lint; the skill walk knows the two new words kinds.
- [x] Tests: tests/test_segments.py (new), and additions to tests/test_join_setup_flow.py, tests/test_sources.py, tests/test_validate.py, tests/test_scaffold.py, tests/test_skills_and_scripts_agree.py.
- [x] Atlas figure 7 (not republished), the join guide, the draft Unreleased CHANGELOG.
- [x] Correctness review of the diff (a subagent), seven findings, each fixed with a test: a scope the profile's checks would refuse is refused when given; a scope held after the list was shown asks for the list again, and the listing and the yes keep "never asked" apart from "the whole company"; the scope is fixed once the profile is approved in a pasted-only run, and that run is told there are no documents to number; an inventory file is settled again on reading and compared whole; a lone segment left out reads back as left out; no numbers are kept when no numbered list was shown; a dash or a letter with no plainer form keeps words apart in a file name, and com0 and lpt0 are reserved.
- [ ] Brandon: the words listed in the hand-back report; the non-Latin name rule; then the live run on the Gridwise material. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)
- [x] Orchestrator: review, merge after 1.6, then 1.7b to 1.7d before release B ships, because the read-back promises drafting and adoption. (Ticked 2026-10-10: merged.)

### 2026-09-26, Unit 1.7b: umbrella and segment drafts, and the unanswered-marker state
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.7b (requirements P18, P19, P27), with call 11's paths: the umbrella at `context/icps.md`, each segment at `context/icps/<slug>.md`. Built on its own branch, `unit-1-7b`, from `release-b` (1.5b, 1.6 and 1.7a merged); not merged, not released.
- [x] The marker as a state: one small module finds every `[your call: ...]` in a context file's body; `ContextFileInfo` carries them; `stale.compute` counts no owner line or acceptance for a file that holds one, so it is neither confirmed nor complete whatever its status; the first-run finding fills the slot Unit 1.2 left empty. (Ticked 2026-10-10: Unit 1.7b.)
- [x] No confirmation path settles a file while a marker remains: a yes to a review question, the moment of use's "it already reflects this", and the closing's reconcile yes are refused with one sentence; setup's own line is written and counts for nothing until the question is answered; the closing asks nothing about a document with a question open. (Ticked 2026-10-10: Unit 1.7b.)
- [x] The review lists each marker, one line each, with the question held apart as data, and asks; the answer becomes a prepared change to the part that holds the question (never a setup overwrite), approved through Unit 1.2b; the wording is refused while it still asks the question it answers; after approval the file can be confirmed. (Ticked 2026-10-10: Unit 1.7b.)
- [x] Drafting: explicit `umbrella` and `segment` steps with their own prompts, sections and checks, added beside the profile's rather than weakening them; the umbrella names every segment of the inventory, a segment left out as still to come in words, nothing in it a link; `draft-icp.md` stays the prompt for one segment. (Ticked 2026-10-10: Unit 1.7b.)
- [x] Setup: several segments draft the umbrella in the profile's place; each segment to draft gets its own preview, draft, check and approval after the positioning; a segment file is refused by name when the base already holds a file whose name folds to the same one, in either segment folder, and when its folder is not an ordinary folder; a draft with a marker says so and is approved only after the person chose to leave its questions open. (Ticked 2026-10-10: Unit 1.7b.)
- [x] Prompts: `draft-icp.md` and `draft-positioning.md` reconciled with the rule; new `draft-umbrella.md` and `draft-segment.md` (depth, no compression) carry the segment names and what the base is for inside the data fence. (Ticked 2026-10-10: Unit 1.7b.)
- [x] Tests for every plan scenario plus the collision checks; the join skill, the stale-check and confirm skills, the closing rules; atlas figures 7 and 8 (not republished); draft Unreleased CHANGELOG. (Ticked 2026-10-10: Unit 1.7b.)
- [x] Full suite, both runs; one correctness review of the diff, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, Unit 1.7b (2026-09-26)
- [x] The marker as a state: `callmarkers.py` finds every `[your call: ...]` in a body; `ContextFileInfo.open_questions` and `complete`; `stale.compute` counts no owner line or acceptance for a file holding one; the first-run finding's second slot is filled (`FINDING_OPEN_QUESTION`).
- [x] No confirmation path settles it: `confirm.answer` yes and `confirm.against_change` refuse with one sentence before the question is used up; the closing leaves such a document flagged and asks nothing; setup's own line is written and counts for nothing until the question is answered.
- [x] The review lists each question first with the question held apart as data; `stale_check.py --answer-question <token> --document <path> --answer-file <words>` prepares a first-draft change to the part holding it; wording that still asks it is refused; local approval settles it and the file can be confirmed.
- [x] `umbrella` and `segment` drafting steps, their prompts, the umbrella's parts and link check, and the check against the settled inventory; the single profile refused with several segments; each segment drafted into `context/icps/<name>.md` after the positioning and before the closing.
- [x] A segment file is refused by name when either segment folder already holds a file whose name folds to the same one (letter case, encoding, a name a move kept, the older folder), and when the folder is a link.
- [x] A draft's open questions are counted before it is shown and approved only with `--questions-open`, on the person's say.
- [x] `draft-icp.md` and `draft-positioning.md` say what a mark costs; new `draft-umbrella.md` and `draft-segment.md`.
- [x] Tests: tests/test_umbrella_and_segments.py and tests/test_open_questions.py (new), the slot test in tests/test_stale.py, the walk in tests/test_skills_and_scripts_agree.py, the lint registry, the run.sh linked-folder list.
- [x] Atlas figures 7 and 8 (not republished), the join guide, the skills and closing rules, the stale-check rules, the draft Unreleased CHANGELOG.
- [x] Correctness review of the diff (a subagent), nine findings, each fixed with a test: one prepared answer per part and the part's text in its name; a stable token for each question; a segment's own page pinned first after ordering; wrapped wording still refused; a set-aside document's questions still asked; refusals said in sentences; a segment's draft tied to its file; the collision refusal names nobody; no skipped single profile with several segments.
- [ ] Brandon: the words listed in the hand-back report; then the live run where he reads an umbrella drafted from the Gridwise material. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)
- [x] Orchestrator: review, merge into release-b, then 1.7c and 1.7d before release B ships. (Ticked 2026-10-10: merged.)

Review: the plan's `tests/test_drafting.py`, `test_base_reader.py`, `test_confirm.py` and `test_prompt_guards_join.py` scenarios live in the two new test modules instead, because each crosses more than one of those modules; the existing prompt guards now cover the two new prompts through `drafting.STEPS`. The closing's finding names how many questions are open rather than the question itself, because the question comes out of the file and the closing sentence is said without a fence.

### 2026-09-26, Unit 1.7c: guarded adoption
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.7c (requirements P20 to P23), with call 11's paths: each adopted segment at `context/icps/<slug>.md`. Built on its own branch, `unit-1-7c`, from `release-b` (1.5b, 1.6, 1.7a and 1.7b merged); not merged, not released. Test-first: every clause of the contract has a hostile fixture under `tests/fixtures/adoption/` that fails it, and a clause with no failing fixture is not built.
- [x] Fixtures and failing tests first: tests/test_adoption.py over every plan scenario and every fixture. (Ticked 2026-10-10: Unit 1.7c.)
- [x] `adopt.py`: the contract in order (destination; the original settings discarded, malformed refused; hidden content removed and counted, then the fence-marker, contact and key screens; the heading grammar the proposal editor supports; the recorded scope; open questions; the library's own settings; the hash of the exact bytes). (Ticked 2026-10-10: Unit 1.7c.)
- [x] Showing: what was removed, the opening lines, and where the whole cleaned file is, kept in the run's own folder with the hash; the yes bound to that hash, and a changed source or cleaned file asks again; a yes covering several only after each was shown. (Ticked 2026-10-10: Unit 1.7c.)
- [x] Writing: `review.approve_adopted`, clean tree, default branch, absent only, the segment folder and name checks, one confirmation line, one saved piece of work; the original never touched. (Ticked 2026-10-10: Unit 1.7c.)
- [x] A refused segment may be drafted instead; the join skill gains step 6d before the closing, because the inventory lives in the run folder the closing clears. (Ticked 2026-10-10: Unit 1.7c.)
- [x] The fence on every path that hands a context file to the model, proved with a hostile adopted document. (Ticked 2026-10-10: Unit 1.7c.)
- [x] Lint registry, atlas figures 1 and 7 (not republished), the join guide, the draft Unreleased CHANGELOG with the residual-risk sentence. (Ticked 2026-10-10: Unit 1.7c.)
- [x] Full suite, both runs; a correctness review and a security review of the diff, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, Unit 1.7c (2026-09-26)
- [x] Fixtures and failing tests first: tests/fixtures/adoption (one per clause, plus a question under a part, a question above every part, no parts, and a page that is not Markdown) and tests/test_adoption.py; the first run failed on the missing module, as it should.
- [x] `adopt.py`: the contract in order; `join.py adopt-show`, `adopt-read`, `adopt`; `review.approve_adopted`; a page the contract refused may be drafted instead.
- [x] The yes bound to the hash of the exact bytes: the page cleaned again from the original and the cleaned file read again at the yes; a yes to several counts only for pages each shown.
- [x] The fence on every path that hands the page to the model, proved with a hostile adopted page; the session's context carries none of it.
- [x] Join skill step 6d (before the closing), adoption rules, lint registry, the skill walk adopts a page, the linked-folder second run covers the class that starts scripts.
- [x] Atlas figures 1 and 7 (not republished), the join guide, the draft Unreleased CHANGELOG with the residual-risk sentence.
- [x] Full suite before the reviews: 2314 tests OK, then 103 from a linked folder OK (tests/run.sh exit 0).
- [x] Correctness review and security review of the diff (subagents): eleven findings and two smaller ones from their residual risks, each fixed with a test that failed before (tests/test_adoption.py, TestTheCorrectnessReview and TestTheSecurityReview).
- [x] Full suite after the fixes. (Ticked 2026-10-10: done with its unit.)
- [ ] Brandon: the words listed in the hand-back report, the question marker call, and the live replay of the Gridwise pages. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)
- [x] Orchestrator: review, merge into release-b, then 1.7d, which must keep the record of what was shown past the closing. (Ticked 2026-10-10: merged.)

Review: the contract's scope clause is a heading naming a place dropped for the scope, because 1.7a settled that no filter reads the words of a document and the places dropped are what apply the scope. A `[your call: ...]` question in a finished page is kept as an open question rather than refused, only under a heading and only on the person's say, because adoption never edits the page and P27 already makes such a file unconfirmed until it is answered.
- [x] Full suite after the review fixes: 2330 tests OK in 861 seconds, then 103 from a linked folder OK in 85 seconds (tests/run.sh exit 0).

#### Astra's review of Unit 1.7c (2026-09-26), findings 1, 3, 4, 6 and 7
Review: docs/reviews/2026-09-26-unit-1-7c-astra.md in the main checkout. Findings 2 and 5 (the write path and the take-back after a save) are the Unit 1.7d agent's, who owns recovery and the write. Each fix below has a test in tests/test_adoption.py that failed at the commit holding only the tests.
- [x] 1 The prepared change is read through `approve_local.py --read`, inside the fence; `--sections` prints its headings inside the fence; the wording command writes the Before and After lines; the stale-check skill and join step 9 never open a prepared file or a document themselves.
- [x] 3 The screens also read an inspection copy (selectors out, character codes decoded, compatibility forms folded, wrapped lines joined); the saved bytes are the approved bytes; a set of ordinary marketing lines still passes.
- [x] 4 Hidden markup is found across the whole text, never across a blank line, and closing tags count; the cleaned bytes and the count are asserted for a tag over two lines.
- [x] 6 A question marker split over two lines refuses the page; the same question on one line is open, unconfirmed and listed.
- [x] 7 A question on a heading line refuses the page, with the round trip that shows an answer there leaves it open and the one under the heading that settles it.
- [x] Call 23: the whole-file sentence drops "or tell you where it is"; the script prints no location; the skill says never to give it.
- [x] Full suite after these fixes: 2346 tests OK in 937 seconds, then 107 from a linked folder OK in 108 seconds (tests/run.sh exit 0).
- [x] Follow-up (coordinator): the approval showing (`approve_local.py --show`) holds every piece of document text inside the data fence (the four labeled lines, the context change it carries, each part with its heading before and after, the whole difference); only GTM Base's sentences and the shown value are outside. New sentences for each part; the R8 difference test reads the data fence. tests/test_adoption.py TestTheApprovalShowing fails against the old renderer and passes now.
- [x] Full suite after the follow-up: 2348 tests OK in 997 seconds, then 109 from a linked folder OK in 101 seconds (tests/run.sh exit 0).

### 2026-09-26, Unit 1.7d: recovery of an interrupted import
Plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md, Unit 1.7d (requirements P19 and P22), with call 11's paths and call 18 (the segment inventory outlives the closing). Built on its own branch, `unit-1-7d`, from `unit-1-7c`; not merged, not released. Also carries Astra's findings 2 and 5 on Unit 1.7c (the write and the save of an adopted page), assigned here because they sit in the write and recovery path.
- [x] Where the import is kept: one record per base in this seat's own folder for that base, never in the base and never in the run folder, holding the settled inventory, the numbered documents, the narrowest consent that can read the pages to adopt (those pages only), the scope, the run the import belongs to, and each page's state; read and written under a lock, so two adoptions at once cannot lose a record. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Per-file state: the yes (the approved hash and the day it was shown) is written before anything touches the base, and committed after the save; written, staged and confirmed are read from the base itself; a no and a refusal are kept so they are never asked again. (Ticked 2026-10-10: Unit 1.7d.)
- [x] The write (Astra 2): folders walked one descriptor at a time with no link followed, the page created only where nothing is, the verified bytes staged rather than whatever is on disk, the installed file checked against the hash before the save, and a take-back that removes only the file this write created. (Ticked 2026-10-10: Unit 1.7d.)
- [x] The save (Astra 5): a failure before the save is put back; a save that landed, or one whose outcome cannot be read, is never put back, and is finished or reported from what the base really holds. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Recovery per file: a page whose bytes match the yes is finished (staged, its line, saved); a page with other bytes is never written over and is reported; a tree dirtied only by this import's own step is recovered, one the person dirtied is refused; a yes whose source changed asks again; the others proceed. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Resume in a later session: a fresh run is seeded from the record, finishes what was already said yes to without asking, and shows only what was never answered; the next session is told once that the import stopped. (Ticked 2026-10-10: Unit 1.7d.)
- [x] The first-backup review recorded as a condition of release two in the closing rules and the join guide. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Tests with a stop injected after every mutation step (journal, write, stage, confirmation line, its staging, save, state), each asserted to have fired, each resumed run byte-identical in content, index and state to an uninterrupted run; every scenario of the plan's list. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Join skill, lint registry, atlas figure 7 (not republished), the draft Unreleased CHANGELOG. (Ticked 2026-10-10: Unit 1.7d.)
- [x] Full suite, both runs; a correctness review and a data-integrity review of the diff, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, Unit 1.7d (2026-09-26)
- [x] Where the import is kept: `segments.ImportRecord`, one file per base in this seat's own folder for that base, carried from the run when the profile creates the base, at every page shown or approved, and at the closing; let go once every page is saved, left out, or refused. Its yes reaches only the pages to take in. Read and written under `fsutil.HeldLock`, as is the run folder's record of what was shown.
- [x] Per-file state: approved (hash and day) before the base is touched, committed after the save lands, left out (`join.py adopt-leave`), refused; written, staged and confirmed read from the base (`review.page_state`).
- [x] The write (Astra 2): `review._create_new` walks the folders with no link followed and creates only where nothing is; `_stage_bytes` stages the approved bytes from memory, checked against git's own name for them; `_still_the_page` before staging and again before the save; `_take_back` removes only the file this write created. Every setup write goes through `_create_new`.
- [x] The save (Astra 5): `review.saved_state` reads the base after any failure at the save: landed is kept, plainly not landed is put back, unknown is left untouched and said (`save-outcome-unknown`), and the next attempt or session finishes it.
- [x] Recovery per file: `review.finish_adopted` finishes a written page from its own bytes, keeping this run's own line; `put_back_unwritten` clears only this page's staging and this run's own line; other bytes are never written over and are named once; a tree the person dirtied is refused.
- [x] Resume: `join.py resume` seeds a fresh run from the record, finishes every yes, shows a changed original again, and names only the pages never answered; the next session start says so once, beside unsaved edits too.
- [x] The first-backup review recorded as a condition of release two in the closing rules and the join guide.
- [x] Tests: tests/test_import_recovery.py (new), a stop after each of the seven mutation steps of an adoption, after five steps inside the resumed run, and after each of the three writes that seed it; each asserted to fire, each resumed run byte-identical to an uninterrupted one in files, staging, saved work and the record; every plan scenario; findings 2 and 5 at each boundary. The walk leaves a page out; the linked-folder run covers the new script class.
- [x] Join skill, the lint registry, atlas figure 7 (not republished), the join guide, the closing rules, the draft Unreleased CHANGELOG.
- [x] Full suite, both runs; a correctness review and a data-integrity review of the diff, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)
- [ ] Brandon: the words listed in the hand-back report, the new trigger sentence, and the live run where he stops an import on purpose. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)

Review: the plan named tests/test_adoption.py, test_segments.py and test_join_setup_flow.py; the scenarios live in one new module instead, because each crosses the record, the write, the save, the run and the session start. The per-file states written, staged and confirmed are read from the base rather than written down, because the plan's lifecycle table says every state is observable from the file and the base's own records, and a state written beside each step would be one more step to stop after. A page finished in a later session carries the import's own run on its line, so the result is byte-identical to an uninterrupted run.
- [x] Full suite before the reviews: 2368 tests OK, then 106 from a linked folder OK (tests/run.sh exit 0).
- [x] Correctness review and data-integrity review of the diff (subagents): fourteen and ten findings, overlapping; all fixed with a test in tests/test_import_recovery.py (TestTheReviews) except a yes to several pages written down one at a time and a line not recognized under changed line endings, both recorded in the CHANGELOG. The lock is now the operating system's (fcntl), one page at a time is written into a base, a page is put down under a temporary name and then named, a page saved at any point is saved, a page changed before its save is taken back and left, an unreadable original keeps its yes, a live run is never cleared by a resume, the record is read as kept and an unreadable one is set aside.
- [x] Full suite after the review fixes. (Ticked 2026-10-10: done with its unit.)
- Both reviewers noted that `unit-1-7c` gained two commits after this branch was cut (Astra's findings 1, 3, 4, 6 and 7); the orchestrator merges them, and the combined code has not been tested together here.
- [x] Full suite after the review fixes: 2386 tests OK in 1005 seconds, then 106 from a linked folder OK in 95 seconds (tests/run.sh exit 0).

#### Astra's review of the merged Units 1.7c and 1.7d (2026-09-27)
Review: docs/reviews/2026-09-27-unit-1-7c-1-7d-astra.md, not ready, eight findings including the two partial closures. Each has a test in tests/test_import_astra_merged.py that failed on eb8999d and passes after.
- [x] 1. Every take-back (leave out, resume, finishing) holds the per-base writing lock, reentrant per thread, reads the page and the record again inside it, and keeps it through the record update.
- [x] 2. Cleanup moves the file to a private name, removes it only when its identity is this write's, and otherwise puts it back.
- [x] 3. One revalidation (`join_flow._revalidate`: today's cleaning and inspection copy, bytes equal to the yes) for every route that finishes an unsaved page: resume, showing again, approving again.
- [x] 4. A saved page is a finished adoption only with a drafted line naming the import's run; one saved without it gets the line (`review.confirm_saved`).
- [x] 5. Markup the cleaning could not take out refuses the page, including an opening tag longer than the pattern reads.
- [x] 6. Temporary files a killed writer left, in the page's folder and the confirmations folder, are swept under the writing lock once older than five seconds; tested with a child process killed with SIGKILL inside the confirmation write.
- [x] 7. The removal notice names the segment, never the file; the numbered documents at the segments step are fenced.
- [x] 8. Candidate and inventory numbers must be positive counting numbers; a record holding anything else is set aside.
- [x] Full suite after the fixes. (Ticked 2026-10-10: done with its unit.)
- [x] Full suite after Astra's merged-line fixes: 2427 tests OK in 1219 seconds, then 115 from a linked folder OK in 101 seconds (tests/run.sh exit 0).

#### Astra's confirmation pass on the merged units (2026-09-27)
Review: docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-astra.md, all eight closed, three new medium findings, not ready. Tests in tests/test_import_astra_verify.py, committed failing first.
- [x] 1. Claims carry the inode, the hash and the original name; a sweep settles any claim left by a stop (own file removed, another put back, or kept aside under a plain name with a sentence); a failed put-back is kept aside and reported.
- [x] 2. No clock: every temporary-file writer holds a shared folder ownership lock (fsutil.FolderLock) for its write and move; the sweep reclaims only when it can take the lock exclusively. Tested with a child stopped with SIGSTOP (its file survives and its move succeeds after SIGCONT) and one killed with SIGKILL (reclaimed at once).
- [x] 3. Only real markup refuses a page; CAC<LTV., a<b, x <y, LTV<3x and <3 pass; the oversized tag, with or without a value, is refused.
- [x] Full suite after the confirmation-pass fixes: 2436 tests OK in 1325 seconds, then 115 from a linked folder OK in 131 seconds (tests/run.sh exit 0).

#### Astra's second confirmation pass on the merged units (2026-09-27)
Review: docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-2-astra.md, five findings, not ready. Tests in tests/test_import_astra_verify_2.py, committed failing first.
- [x] 1. Folder locks in the seat folder's own locks folder, one for every session; seat and locks folders refused when a link, not this account's, or writable by others.
- [x] 2. A writer that cannot take its lock refuses with a sentence (no-writing-lock).
- [x] 3. Claims settled only when their names validate exactly; malformed ones, including a superscript digit and a nested claim, are left alone and counted as somebody's unsaved work.
- [x] 4. Markup decided by Python's HTML reader, plus a leftover comment opener or closing tag; a quoted value with a blank line is refused; the comparisons still pass.
- [x] 5. A put-back stopped after its link finishes by removing only the claim.

#### Astra's third confirmation pass on the merged units (2026-09-27)
Review: docs/reviews/2026-09-27-unit-1-7c-1-7d-verify-3-astra.md, ready with one change. Tests in tests/test_import_astra_verify_3.py, committed failing first.
- [x] A start tag is markup only with an element name (the HTML standard, older names browsers honor, SVG and MathML), a custom element name, or an attribute with a value; end tags, comments, declarations and processing instructions always refuse. Comparisons before a quoted reply or a later greater-than sign pass; the script, div, oversized span, custom element and valued made up tag cases still refuse.
- [x] LOCKS_NOT_PRIVATE reworded, the orchestrator's call open to Brandon's veto.

### 2026-09-27, merging 0.3.2 into release-b
- [x] Every clean-tree check on release-b goes through `unsaved.look`, including the four Unit 1.7d added in review.py (`_only_this_pages_edits`, `put_back_unwritten`, `take_back_unsaved`, `confirm_saved`) and the move's `_theirs_before_finishing`.
- [x] Every refusal about unsaved words in changes.py (`THEIR_WORDS`, `GAVE_UP_LEFT_ALONE`) names files by `unsaved.plain_name`; a record is "one of your records", a context change in any of the three folders "one of your context changes".
- [x] session_start keeps the stopped-import sentence beside the unsaved-edits sentence, after the shared look.
- [x] Orchestrator: review and commit the merge. (Ticked 2026-10-10: merged.)
#### Call 29: a segment settled to be drafted but not drafted before the closing (2026-09-27)
Brandon's call 29: a later session asks again for consent to the material and finishes it. Branch `call-29` from `release-b`.
- [x] The import record carries a segment left to draft as one more per-file state (name and settled answer from the inventory; state approved with the hash of the approved draft, saved, or left out), never material or a draft body, and never a yes to read anything. It is kept from the moment the base exists, including an import with no finished page to take in. (Ticked 2026-10-10: call 29.)
- [x] Setup's step 6c writes a segment through the same write-ahead path as a finished page (the yes written down, then written, staged, its line, saved, then saved written down), so a stop anywhere is finished by the next session. (Ticked 2026-10-10: call 29.)
- [x] The closing keeps the record while a segment is left to draft and says so in one sentence. (Ticked 2026-10-10: call 29.)
- [x] "Finish setting up my base" finishes a draft whose yes was given and names each segment still to draft; a stop partway through a draft's save is finished, taken back, or drafted again, never written over. (Ticked 2026-10-10: call 29.)
- [x] A segment still to draft is drafted in a run of its own, after the same survey-free consent step as Unit 1.6: only the numbered document the record kept for it is offered, the person may add a folder or drop a file, a changed list asks again, and nothing is read before the yes. Material gone or changed is said plainly with two choices, leave it out or name new material, and nothing is drafted from nothing. (Ticked 2026-10-10: call 29.)
- [x] The draft is shown whole and approved exactly as step 6c; leaving a segment out ends it and it is never offered again. (Ticked 2026-10-10: call 29.)
- [x] The session-start notice covers both kinds in one notice; a segment left out is not "to finish". (Ticked 2026-10-10: call 29.)
- [x] Tests failing first: survives the closing and finished after a fresh consent; a changed list asks again; missing material said with the two choices; leave-out ends it; one notice; a stop at every mutation step resumes cleanly. run.sh linked-folder list and its guard for any new script-starting class. (Ticked 2026-10-10: call 29.)
- [x] Join skill, lint registry, atlas figure 7 (not republished), join guide and closing rules if they describe it, the draft Unreleased CHANGELOG. (Ticked 2026-10-10: call 29.)
- [x] Full suite, both runs; a correctness review of release-b to HEAD, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, call 29 (2026-09-27)
- [x] Record: `segments.ImportRecord.to_draft`, `drafts_unfinished`, `pages_unfinished`; `unfinished` covers both; kept from the first approval even with no page to take in. No second record; names, answers, and the approved draft's hash and day only.
- [x] Step 6c and later drafts both go through `join_flow._approve_a_segment` (yes written down, `review.approve_adopted`, saved written down); resume settles each with `_settle_a_draft`.
- [x] Later session: `join.py draft-list`, `draft-freeze`, `draft-leave` in a run of its own; `resume` prints `to-draft=`; `close` prints one sentence; one notice (`finish-import.md` segment blocks).
- [x] Tests: tests/test_segments_left_to_draft.py (committed failing first), the linked-folder run and its guard, the skill walk leaves one segment for the later session.
- [x] Join skill, lint registry, atlas figure 7 (not republished), join guide, closing rules, draft Unreleased CHANGELOG.
- [x] Full suite before the review: 2484 tests OK, then 120 from a linked folder OK (tests/run.sh exit 0).
- [x] Correctness review (subagent): three medium, two medium-low, four low findings; all fixed with a test in TestTheCorrectnessReview, committed failing first.
- [x] Full suite after the review fixes: 2495 tests OK in 1339 seconds, then 120 from a linked folder OK in 193 seconds (tests/run.sh exit 0).
- [ ] Brandon: the new sentences, and a live run that closes with a segment undrafted and finishes it in the next session. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)

### 2026-09-27, the live-check follow-up unit (calls 32, 33, 34, 36, 37, 40, 45 and 49)
Branch `live-check-follow-up` from `release-b` (cddb588). Input: the 0.3.1 live check, steps 2 to 7, in docs/walkthroughs/2026-09-release-a-live-check.md on main, and the plan's For Brandon table. Record-a-context-change-at-any-time is 0.3.3's, on main, and is not built here.
- [x] 1. The hand edit (calls 33, 34, 49): one question, long for the first three hand edits a person keeps on this computer (counted in the seat) and short from the fourth, the long version on "why are you asking this?"; three answers (the business changed, a corrected fact worded as replacing the old one, wording only); the assistant names the exact difference before accepting "only a typo" (a rule in the skill); wording only writes no correction record and takes the short route. (Ticked 2026-10-10: the live-check follow-up.)
- [x] 2. The showing of a hand edit: the changed sentence once, the change marked, the section named, the whole text on request; "What changed:" from the changed line in plain words, never cut mid-word, and the saved-history subject the same; "Why:" the person's own sentence; no reviewer on the local path. (Ticked 2026-10-10: the live-check follow-up.)
- [x] 3. Relay and flow (call 32): one ask per step, editorial notes after the approval as one short note, no mention of a check that found nothing, never several questions at once, in every skill. (Ticked 2026-10-10: the live-check follow-up.)
- [x] 4. Move offers (call 40): the version that introduced the layout and what moves, with counts and plain document names; the read-only look says nothing when the offer would be made and the plain reason when not; every count in words, the singular for one. (Ticked 2026-10-10: the live-check follow-up.)
- [x] 5. Setup (call 45): the plain-yes backstop says the list is larger than one draft can read. (Ticked 2026-10-10: the live-check follow-up.)
- [x] 6. Segments (calls 36, 37): leaving a segment out after the umbrella names it prepares a change to the umbrella; a refused page whose draft-instead was not finished is kept to draft later. (Ticked 2026-10-10: the live-check follow-up.)
- [x] Tests failing first for each; the skill walk; run.sh linked-folder list and its guard; lint registry; CHANGELOG; atlas captions. (Ticked 2026-10-10: the live-check follow-up.)
- [x] Full suite, both runs; a correctness review of release-b to HEAD, fixes with tests, suite again. (Ticked 2026-10-10: done with its unit.)

#### Progress and review, the live-check follow-up unit (2026-09-27)
- [x] 1 and 2. `hand_edit.py` holds the one question (Brandon's words, long three times per person in the seat, short from the fourth, long on `--why`), the three kinds, and the marked showing; `stage_local_edit` takes `kind` and `also_affects`, refuses a corrected fact without "replacing", and a wording fix carries `wording_only` and writes no correction record on either path; `approve_local.show` is short for a hand edit and whole with `--whole`, one shown value for both; "What changed:" and the saved history from `what_changed_line`, never cut; "Why:" the person's own answer; `propose.py --hand-edit-question`, `--hand-edit-difference`, `--documents`, `--kind`, `--also-affects`.
- [x] 3. Every skill's relay rules: one ask, notes after the approval as one short note, never a check that found nothing.
- [x] 4. The move offer from `changes.offer_sentence` (version `constants.CURRENT_LAYOUT_VERSION`, documents by name, the rest counted, it or them); the look says only the not-now reason; every person-facing count through `names.counted` or `names.how_many` (the report's figures left as figures).
- [x] 5. The plain-yes warning says the list is more than one draft can read.
- [x] 6. Leaving a segment out prepares the umbrella change (call 36); a refused page's segment is `draft-instead` and kept to draft later (call 37).
- [x] Tests failing first (tests/test_live_check_follow_up.py), the skill walk, run.sh's linked-folder list and its guard, the lint registry, CHANGELOG, atlas captions (not republished), join guide.
- [x] Full suite before the review: 2603 tests OK, then 143 from a linked folder OK (tests/run.sh exit 0).
- [x] Correctness review (subagent): one high, three medium, two low; all fixed with a test in TestTheCorrectnessReview and its two siblings, committed failing first.
- [ ] Brandon: the new sentences; the version the offer names (0.4 assumed for Release B); whether a corrected fact's "nothing about the business changed" way out in the long question needs rewording; a live run of the hand edit and the move offer. (Noted 2026-10-10: the words were decided as recommended in calls 35 to 47 and 52; the live run is folded into the 0.4.0 live check on the one list for Brandon in the 2026-10-10 section.)

### 2026-09-27, merging 0.3.3 into release-b
- [x] Conflicts resolved: confirm.py (0.3.3's any-document rule over release-b's `layout.required_paths`), join_flow.py (`reconcile_plan` follows the move and counts both flagged sentences in words), the stale-check script (both `--answer-question` and `--record-change`, one `--document`), CHANGELOG (Unreleased on top, 0.3.3 exactly as released), this file (main's first), run.sh and test_linked_folder (union, then the seat guard), plain_language (both registries), test_skills_and_scripts_agree (both fillers), the logic atlas (release-b's figure 7 with 0.3.3's line and sentence).
- [x] One locking system: `locks.py` holds Unit 1.7d's design (operating-system locks never removed, the owner-checked `locks` folder in the seat folder, a refused write when its lock cannot be taken, a sweep only under the lock, per-thread reentrancy) with 0.3.3's lock file as the fallback where `fcntl` is missing. `fsutil.FolderLock`, `fsutil.HeldLock` and join_flow's writing lock are that module; `record_change._locked` keeps its lock file in the same folder; `record_change.record` and its yes and no answers hold the base's writing lock.
- [x] Every Release B save goes through `GitRunner.run`; tests/test_no_hooks.py plants every hook and a file monitor for the move and its recovery, adoption and import recovery, call 29's segments and the umbrella change, the hand edits, and setup. Found and fixed: `gitcmd._plain` ran the base's file monitor in the filter look.
- [x] 0.3.3's recording on the CLASS layout: `learning/changes`, both layouts, release-b's names, counts in words, the shared unsaved refusal, answers matched across the move (tests/test_record_change.py TestTheCurrentLayout).
- [x] Found by the combined skill walk and fixed: `compose_proposal.parts_of` read a moved document at its older path.
- [x] Orchestrator: review and commit the merge. (Ticked 2026-10-10: merged.)

### 2026-09-27, Unit 1.8: the sweep of text no unit touched, plus three additions
Branch `unit-1-8` from `release-b` (8eefb71). Spec: the Unit 1.8 section of the plan, P28, call 54, and the Release B list additions from Astra's review of 0.3.3 (the changes.py sentences and every other caller of `names.document_name` or `_named`).
- [x] 1. Work the exemption list to empty: join steps 1 to 4 rewritten to the four checks (step 4 split into 4 and 4a so each asks one thing); `EXEMPTIONS = ()` and the two tests that assumed a non-empty list changed with their reasons.
- [x] 2. The closing question says it is feedback for the people who make GTM Base, that it is optional, and where it is kept (P28).
- [x] 3. No sentence is filled from a file name: `names.document_name` counts segments and any other document; `names.documents_named` names the known ones and counts the rest; `changes._named` never reads a context change's file name; `record_change.safe_name` is `document_name` (which documents are asked about is unchanged); confirm, stale_check, compose_proposal, moment and approve_local sentences that read a path now name the document.
- [x] 4. The lint: `find_file_name_fills` in tests/plain_language.py reads the code that fills every registered sentence and every sentence-shaped string filled where it is written; folder locations the person must find are the only excused fills, each with a lasting reason.
- [x] 5. Call 54 in the four document prompts (profile, umbrella, segment, positioning), with a prompt-guard test.
- [x] 6. CHANGELOG, the UX standard's Human names section, the stale-check skill's written-twice paragraph. The atlas quotes none of the changed sentences, so it is unchanged.
- [x] 7. Full suite twice, correctness review, fixes failing first, suite again. (Ticked 2026-10-10: Unit 1.8's review section below.)
- [ ] Brandon: read three steps aloud (join steps 1, 4a and 10).
- [x] Brandon decided 2026-10-10 (call 59): keep the names people gave their segments where every seat can read them. Done on claude/release-b-finish-1e1203, see the 2026-10-10 section.

#### Review (Unit 1.8, 2026-09-27)
- [x] First full run (before the review fixes): 2744 tests, 24 failures, every one a sentence a test pinned by its path, its file name or an identifier read from a file name; each test changed with its reason recorded in it, and the protected SC1 scenario's hash moved with a comment saying why.
- [x] Correctness review (subagent), eleven findings. Fixed, each with a test that failed first: `document_name` raised on a file named by its ending alone, where it used to say "one of your documents"; `documents_named` counted one document twice; the lint missed f-strings, joining with `+`, a template chosen by `if` or held in a local name, a value added with `append`, `.affects`, plurals such as `candidates`, and trusted any function called `describe`; the closing question called the answer feedback without saying it stays in the base where invited people can read it and is sent nowhere. Fixed without a new test: the candidates list in a prepared change read out paths (now caught by the lint), sentences that did not agree with a plural name ("your goals is"), step 4a asking a question the printed sentence already asks, the worktree name worked out before the worktree was taken away, three comments the change made untrue. A stale exemption (`MULTIPLE_CHILDREN`) removed, found by the new check that every exemption still excuses something.
- [x] (Fixed 2026-10-10 under call 59.) Not fixed, for Brandon: after setup no record keeps the names people gave their segments, so the any-time record-a-change list and its questions call every segment "one of your segments" and cannot tell two apart (review finding 1, high). The fix is to keep the settled names where every seat can read them, which changes what a base stores. Refusals in the layout move no longer say which context change could not be read (finding 6); the brief named those sentences, so they follow the brief.
- [x] Full suite after the review fixes (tests/run.sh): 2748 tests OK, then 210 from a linked folder OK, exit 0, the seat guard silent.

### 2026-10-05, 0.3.4: the command check refused lines that only held the letters "git"
Observed in the Gridwise folder on 2026-10-05: every `codex exec --skip-git-repo-check` line and most pipelines out of git refused with the "could not tell" sentence.
- [x] A line is about git only when a part of it runs git or gh as its program (prefixes stripped, shell `-c` and substitutions read recursively); an unknown program handed the word git still counts.
- [x] Widen the harmless words (cut, uniq, tr, find, du, df, date, which, basename, dirname, realpath, stat, diff, jq, tee, less, column, codex); `find -exec` leaves the list; `timeout` read as a prefix.
- [x] A refusal of its own for an unknown program beside git, naming the program; "could not tell" kept for parse failures.
- [x] Tests: flag case passes, pipeline into cut and uniq passes, a real push is still a push, unknown wrapper still refused.
- [x] Full suite run; version 0.3.4 in both manifests; changelog entry.
- [x] Brandon: review the pull request, then update the installed plugin. (Ticked 2026-10-10: merged as pull request #1.)

Review: the fix is in `plugins/gtm-base/lib/gtmbase/gate.py` (`mentions_git_or_gh`, `_INERT_WORDS`, `_strip_prefixes`, `REASON_STRICT_UNKNOWN`) with tests in `tests/test_gate.py`. One judgment call: the first-token rule alone would have let `find . -exec git push` and `watch "git push"` run unread, so an unknown program handed the word git keeps the old refusal.

### 2026-10-10, finishing Release B (0.4.0), branch claude/release-b-finish-1e1203 from release-b
Brandon's calls 57 to 59 (plan, "For Brandon"): 1.7e rebuilt as option D, Claude Code's own permission prompt forced by a hook; 1.7e stays in Release B with a time limit (ships as 0.4.1 if not through review by the time the replay is scored); segment names kept where every seat can read them.
- [x] Merge main (0.3.4) into the branch; CHANGELOG and this file kept both sides.
- [x] Calls 57 to 59 and the change log recorded in the plan; call 56 marked superseded.
- [x] Merge 0.3.5 from main once it lands (write_hook.py and hooks/write-check.sh are the 0.3.5 session's; not edited here). (Ticked 2026-10-10: merged on 2026-10-10.)
- [x] Unit 1.8 finding 1: segment names kept where every seat can read them. Nothing new stored: the customer profile already names each segment under a `###` heading that `drafting.check_umbrella` matches to the settled inventory by slug, so `record_change.segment_names` reads it (one heading per slug, plain words only, at most 80 characters) and the list, the four lines, the questions and the answers say `your segment "Name"` inside the data fence; anything else stays "one of your segments". tests/test_segment_names.py, 9 tests, the first 8 failing before the fix (4 failures, 4 errors): a base made through the real join flow, an older-layout base before and after `--move-changes`, names refused, and a guard that every namer handed over reads no file name (the lint now trusts `name_of`).
- [x] Unit 1.7e, option D, verified before building. Docs (read 2026-10-10, hooks reference, permission modes, VS Code page, CHANGELOG): a hook "ask" prompts in default and in auto ("the classifier can still deny the tool call, but it can't approve the call silently"); the reason is shown in the prompt; updatedInput with ask shows the modified input. Not documented: acceptEdits, bypassPermissions, dontAsk, the VS Code extension, the desktop Code tab. Live on CLI 2.1.276: default and acceptEdits show "Hook PreToolUse:Bash requires confirmation for this command:", the reason, Yes/No. auto started in a terminal tab but the auto-mode classifier refused this session reading or closing it; bypassPermissions launch refused by the classifier. Notes: side-session-notes/.../release-b-finish-hook-ask-docs.md.
- [x] Unit 1.7e, option D, built on branch unit-1-7e-d: `gtmbase.approval` (classify with each script's own parser, ask + sentence + updatedInput ticket, ticket in the seat folder, taken back by the next command in the conversation, 6 hours at most), wired into the Bash gate (also on Monitor and PowerShell), fifteen library writers gated, `state.go_quiet`, the gate refuses commands naming the ticket. Approvals refused in bypassPermissions/dontAsk (call 60, awaiting Brandon) and for Codex. Tests: tests/test_approval_ask.py, three failing first by design (commit "test: every approval asks the person"), 16 passing after.
- [x] Unit 1.7e, option D: security and correctness reviews, fixes with failing tests first, full suite twice. (Ticked 2026-10-10: two reviews and a confirmation pass, findings fixed, see docs/reviews/2026-10-10-unit-1-7e-d-*.)
- [x] Brandon: call 60, decided 2026-10-10: let them run. The refusal in bypassPermissions and dontAsk is taken out (test rewritten first, then the code), and the CHANGELOG, the approval module and the atlas say an approval may go through there with nobody asked, a limit Brandon accepted.
- [ ] Brandon: a live run of D (default, auto, VS Code extension, the desktop Code tab, and whether bypassPermissions shows the question at all).
- [x] Unit 1.9 prepared: both answer keys unchanged since Brandon's review of 2026-09-27; their sha256 values recorded in the private replay folder (`freeze-and-limit-2026-10-10.md`), frozen the moment Brandon says approved; corpora.md still matches its frozen hash. Case three's limit rechecked with Release B's own reading code: 40,000 characters reads ten of sixteen files (the older version set aside first) and drops six, two segment pages among them. Proposal stands, runner-up 35,000.
- [x] Brandon, 2026-10-10: approved, so both answer keys are frozen at the recorded hashes (checked again after the answer); yes to 40,000 for case three, written into the private corpora.md (its hash changed for that alone; the earlier version is kept) and the walkthrough.
- [x] The three replay cases run on 2026-10-10 on Brandon's instruction (on the stand-in's confirmation of finding 5), on 114a73a, through Release B's own setup flow in sandboxes, every draft by a fresh agent given only its request. Outputs and a blank scoring sheet per case: ~/GTM Bases/Gridwise/fidelity-replay/runs/2026-10-10/README.md. Case two's list frozen first (70 files, case-two-list-2026-10-10.md). One correction made during the run (case two: `todo.md` taken out of twelve sources lists to get past the placeholder check), recorded.
- [ ] Brandon: score the three cases against the five-point bar, in the private README.
- [ ] Two defects the replay found, to fix after Brandon scores (fixing them changes the build that was replayed, so whether to run again is his call): the older version of a finished page is offered and taken in (segment_candidates should prefer the final version, as drafting already does); the placeholder check reads the sources list (it should read only the body).
- [ ] When Codex resets on 2026-10-14, run Astra's confirmation of finding 5 anyway; if it finds something, fix it and say whether the fix could affect any replay result.
- [x] Astra's review of all of Release B (docs/reviews/2026-10-10-release-b-review-astra.md: not ready; 2 critical, 3 high, 2 medium, 1 low), every finding fixed with a test, then two confirmations (verify: six closed, findings 5 and 8 open; verify-2: 8 closed, 5 open), fixed again (every setup step's output in one data fence).
- [ ] Astra's third confirmation (brief: docs/reviews/2026-10-10-release-b-verify-3-brief.md). Blocked: Codex is at its usage limit until 2026-10-14 06:08. An interim confirmation by a review subagent stands in until then.
- [x] Release prepared, not merged: 0.4.0 in both manifests and the library, CHANGELOG dated 2026-10-10 (the date changes to the day it ships), atlas figures 5, 6 and 8 and its version, this file ticked (finished work since 2026-09-05 ticked with a note on each), lessons recorded.

#### Review (2026-10-10)
- Merged into this branch: main at 0.3.4, then 0.3.5 (PR #2). `write_hook.py` and `hooks/write-check.sh` were not edited here.
- Call 59 (Unit 1.8 finding 1): nothing new stored in a base; names read from the profile's own headings, fenced. Correctness review, four findings fixed; Astra's finding 7 fixed.
- Unit 1.7e, option D: built on unit-1-7e-d and merged; two reviews and a confirmation pass, then Astra. Fifteen approval points plus five Astra added; the residuals are in the CHANGELOG.
- Unit 1.9: keys hashed for Brandon's approval; case three's 40,000 rechecked on Release B's code.
- Suites (tests/run.sh): the 0.4.0 commit 9141219, 2815 OK then 213 from a linked folder OK; the head's code at e527480, 2818 OK then 214 OK; the final head ae88eb1, 2819 OK then 215 OK. Each exit 0, the seat guard silent.
- A commit that was on local main, dff9f24 "docs: Phase 2 and 3 decisions, settled for Plan 1", is on no branch since main moved to 0.3.5; it is kept on branch keep/phase-2-3-decisions-dff9f24 for whoever wrote it.

#### For Brandon, exactly what is left (2026-10-10)
1. Call 60: decided 2026-10-10, let them run (done; the refusal is taken out).
2. A live run of option D on 0.4.0: in the default mode, in auto mode, in the VS Code extension, and in the desktop app's Code tab, approve one change and refuse one, and check the question shows "Hook PreToolUse:Bash requires confirmation", GTM Base's sentence, and Yes or No; then in bypassPermissions note whether the question appears at all, since under call 60 an approval may run there unasked. Close the terminal tab "hook ask: auto" left from this session's live test, which the auto-mode classifier would not let this session close.
3. The live check, steps 7 to 10 (docs/walkthroughs/2026-09-release-a-live-check.md) on 0.4.0: the moment of use against the 9 of 10 bar, a setup closing in a scratch folder (now with segments, and every approval asked), ordinary work untouched, your own settings.
4. Read three steps aloud: join steps 1, 4a and 10 (Unit 1.8).
5. The fidelity replay: keys frozen and 40,000 set (done, 2026-10-10). Left for you: score the three cases once they are run and presented. Case two's list is frozen at the start of its run.
6. Astra's third confirmation once Codex resets on 2026-10-14 (or with more credits): docs/reviews/2026-10-10-release-b-verify-3-brief.md.
7. Then your yes to merge this branch into release-b and to release 0.4.0 to main. release-b has moved since this branch began (the 0.3.5 carry, d275d70), so that merge will need a small conflict resolution in the CHANGELOG and this file.

### 2026-10-10, 0.3.5: the write check refused every write inside a linked folder (branch claude/fix-0-3-5-linked-folder-writes, from main)
Reproduced on the installed 0.3.4: a Write under `~/Gridwise/.claude/worktrees/<session>/` was denied with "Some folders are GTM Base's own to keep". `write_hook.problem_with` held each joined entry's `content_root` to a base's rules, refusing `<content_root>/.git` and `<content_root>/.claude`, which is where every Claude desktop session there works and where the person's own skills and agents live.
- [x] Reproduce with the piped request against this branch's script (deny for the session file, the linked skills file and both linked settings files).
- [x] Tests that fail first in tests/test_write_hook.py: `TestTheFolderABaseIsLinkedTo` (a real linked repository with a desktop-style working folder inside `.claude/worktrees`), the old "linked settings are refused" test flipped to expect the question, and a fallback test. Five failed before the fix; the two guards (a base's own folders, a link into a base) passed before and after.
- [x] Fix: only a base's `root` keeps the refusal on `.git` and `.claude`. Inside a linked folder, `.claude/settings.json` and `.claude/settings.local.json` are asked about (`LINKED_FOLDER_SETTINGS_FILES`, `_a_linked_folders_settings`), at the linked folder's top and in any folder inside it such as a desktop session's working folder, because a session opened there reads them and they can switch the plugin's checks off. Everything else in a linked folder is allowed. `_settings_name_a_base` reads a repository's git settings for a `gtmbase.id`; writing one into a linked folder's `.git/config` can only make it look like a base and add protection, never remove a real base's, so the linked `.git` needs no guard.
- [x] Shell fallback (`write-check.sh` `is_protected`) already refused `.git`/`.claude` only under a folder holding the map, so it never caught linked folders; no change, now pinned by a test.
- [x] Read hook and command gate checked for the same over-reach: neither has it. `read_hook._base_for` walks only each entry's `root`; the gate's scope questions use `resolve_base(...).joined`, and a linked folder resolves as linked, not joined.
- [x] Version 0.3.5 in both manifests, the library and the tests that pin it; CHANGELOG entry; logic atlas caption and stamp.
- [x] Correctness review subagent, findings fixed.
- [x] Full suite green (tests/run.sh, 2026-10-10: 2189 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened (brandon-sellers13/gtm-base#2); the fix brought into release-b (d275d70, a merge of this branch with 0.3.4; full suite 2764 OK, then 210 OK).
- [ ] Brandon: review, then update the installed plugin.

#### Review (0.3.5)
One correctness review. It confirmed nothing a real base protected is now open, that the read hook and the gate do not over-reach, and that the shell fallback is consistent. It found three things, all fixed with tests: (1) medium, a desktop session's own `.claude/settings*.json` inside the linked folder went from refused to allowed with no question, now asked about; (2) low, when the linked folder's `.claude` is a link, a write to its target skipped the question because the shortcut ran first, so the linked-settings question now runs before the shortcut; (3) low, the atlas stamp went on the wrong figure, now moved. Its testing gap is closed too: a new test refuses a base known only by the account record (map and history removed), and removing that branch of the check fails it. Checked against the 0.3.4 write hook: six of the new tests fail there, and the guards pass. Left as it was: the fallback looks only at the first `.claude` in a path, older than 0.3.5 and an edge case (a base checked out inside a session's working folder).

### 2026-10-10, live sitting findings (Release A live check, step 7 on 0.3.5)
- [x] (0.3.6) **Blocking: a restart unlinks every linked folder.** `folder_identity.matches` returns `remounted` when the device numbers differ even though both records carry the same disk identifier, and `paths._linked` then treats the folder as a different one (`CODE_LINK_MISMATCH`). Seen live: ~/Gridwise's link dropped with only the device number changed (folder number, creation time, mount, disk identifier and remote all agree). Fix: with an agreeing disk identifier on both sides, a changed device number is the same folder (refresh the stored number); a differing disk identifier stays `remounted`. Test first, failing on 0.3.5. Also missing from the Release B branch.
- [ ] A command run from a linked folder whose link was dropped says the not-joined sentence ("This folder is not a company base you have joined yet"); it should say the link-mismatch sentence, so the assistant does not have to explain.
- [x] (0.3.6) The join skill's link command: the assistant needed two failed tries to pass the folder and narrated why; show the command exactly as it must be run.
- [ ] Record a context change, the showing: show the source line too; today the yes covers a saved source the person never saw.
- [ ] Record a context change, the per-document question: the assistant reads the document first and says what it found, then asks the person to confirm (Brandon's "shouldn't the tool already know this?"). Wording proposed in the walkthrough, not yet approved by Brandon. The person still gives the answer; a yes is never inferred.
- [x] (0.3.6, a new count of step 7 still to run) **The moment of use misses because the session never learns where the base's documents are.** The session-start context names the check but not the base's folder or its documents; a request about who we sell to searched three levels deep, missed `context/strategy/icp.md`, and told the person the base has no customer profile. Fix: name the base's folder and list each context document by plain name and path in the session-start context, with when to use them. Same as live check step 2 finding 2 (2026-09-26).
- [ ] Moment of use, the flag: "What changed" is cut off mid-sentence and the four lines carry no source; the assistant summarized instead of reading the four lines back. Make the four lines whole and short enough to read back as they stand.
- [ ] Moment of use, "use it as it stands" sentence: also name the other way the flag clears (an approved fix).
- [ ] Read check backstop: a document read through a shell command (`cat`) is never seen by the read check. Decide whether the command gate should flag a shell read of a base's context file, or say plainly that the backstop covers the file tool only.
- [ ] Moment of use, "fix it first": print the next steps with the prepared change (write the wording with `approve_local.py --wording`, show it, ask), so the assistant does not read the plugin's code to find them.
- [ ] A prepared change touches one section, and the flag clears for the whole document on its approval. Decide: a fix may span sections, or the flag clears only when the sections the change names are covered.
- [ ] Moment of use, "already reflects" sentence: names a path and "your own copy of the base"; replace with a plain sentence about the document.
- [ ] Record a context change: when the person's first message already says what changed, ask only for the why and the source.
- [ ] **Pattern (Brandon, 2026-10-10): when the tool can tell, it says so and asks to confirm, rather than asking an open question.** Seen three times: "Does your customer profile already say what that change says?" asked cold (step 7), the list of six sections with "Which one is this change about?" when the assistant already knew it belonged in Firmographics (step 8), and the closing's "Did anything get in the way?" with no reason given (step 8). The person still decides; a yes is never inferred.
- [ ] The setup shows "Edited 2 files" right after "nothing will be created until you agree": the files are the temporary words files for the company name and folder, outside the person's folder. Say nothing is in their folder, or keep the words files out of the app's edit list.
- [ ] `approve_local.py --wording --section` replaces the whole section; the skill text says "write the wording into that part". Say plainly that the wording is the whole section as it should read, or offer an add-to-section form, so an assistant cannot propose a change that deletes the rest of the section by accident.
- [ ] The setup closing names the change cut off with an ellipsis ("the change about We now sell to ...", cut off mid-sentence); use a whole short phrase.
- [ ] One rule for the look-again date: the setup closing sets three months, the any-time recording one month.
- [x] (0.3.6) **Blocking: the settings question is bypassed through the shell.** Live check step 10: asked to add a permission to `~/.claude/settings.json`, the session rewrote the file with a Python script run through Bash, and nothing was asked. `write_hook` runs only on Write/Edit/MultiEdit/NotebookEdit, and the command gate does not look at lines that write the client settings files. Fix: the command gate asks (never refuses) about a line that names any file in `write_hook.CLIENT_SETTINGS_FILES` or a linked folder's `LINKED_FOLDER_SETTINGS_FILES`, with `ASK_ABOUT_SETTINGS` as the reason, the same way it already refuses lines naming the records folder. Test with the exact command the session ran.
- [ ] Command check false refusals (seen by the guide session, 2026-10-10): a shell `for` loop testing `[ -d "$d/.git" ]` runs no git and was refused ("it runs for on the same line as a git or GitHub command"), and an `echo`/`cat` heredoc appending task text that merely mentions git was refused ("it runs another program on the same line as a git or GitHub command"). A folder name ending in `.git`, or the word inside text being written, is not the program git.

### 2026-10-10, 0.3.6: the three blocking findings of the live check (branch claude/fix-0-3-6-live-check-blockers, from main)
The live check's record (walkthrough and task list from branch claude/live-check-sitting-917408, commits 9efc69e and d28d214) is carried on this branch.
- [x] Restart: `folder_identity.matches` calls a changed device number the same folder when both records carry the disk's identifier and it agrees; a different identifier stays `remounted`, and so does a missing one. `paths._linked` hands back `repair_identity`, and the half of the session start that writes stores the new number through `machine.rewrite_content_root`. Tests: tests/test_restart_keeps_the_link.py; the one old test that held the agreeing-disk case to be a remount now holds the no-identifier case.
- [x] Relink: `join.py words-file` finds the base the way `link` does (by its folder, its company name, or as the only base), `link` with no folder links the folder it runs in, and the join skill shows each linking command as it is run, with `${CLAUDE_SKILL_DIR}` (documented by Claude Code for exactly this, checked 2026-10-10). Reproduced first: `words-file --base Acme --for folder` from an unlinked folder refused with the setup-run sentence.
- [x] The session start names the base's folder and every document by plain name and whole path, before the map, with the instruction to read and check them for any request about who the company sells to, what it says, or how it says it. The map now gets the room the rest leaves, so the 8,000-character cap can no longer cut off the end of the rule (it could on 0.3.5 with a full map; a test shows it). Tests read the text the hook really injects: tests/test_session_start_documents.py.
- [x] Command check: `settings_writes.writes_a_settings_file`, called from `gate.main` after the refusals, answers "ask" with `write_hook.ASK_ABOUT_SETTINGS` for a line that writes the user settings, the plugin registry or plugins folder, or a linked folder's settings. `write_hook.asks_about` is now the one answer both checks share. Tests: tests/test_command_check_settings.py, with the live step-10 shape through the real hook (0.3.5 said nothing).
- [x] Version 0.3.6 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.3.6 says what the command check still cannot see; the join guide says the flag is best effort outside a skill.
- [x] Correctness review and security review by subagents, findings fixed (see the review below).
- [x] Full suite green (tests/run.sh, 2026-10-10: 2231 tests OK, then 161 in the linked-folder rerun OK). The first full run caught three version pins in tests/test_shim.py and the skill walk, which ran the new bare `link` from inside the base; the walk now runs it from the folder being linked, as the skill says.
- [x] Pull request opened for Brandon.
- [ ] Astra (Codex) review: rate-limited until 2026-10-14 06:08. Pending; run it then.
- [ ] Brandon: review and merge, update the installed plugin, restart the Mac once to see the link hold, then run step 7's count of ten again.
- [ ] Follow-ups not in this release: the not-joined sentence for a folder whose link was dropped (step 7, first finding 2), and the command check's two false refusals on lines that run no git.

#### Review (0.3.6)
Two reviews by subagents, one for correctness and one for security, run on the first draft of all three fixes. Both found the same top gap, and every finding below is fixed with a test.
- High, both reviews: `cp ... ~/.claude/settings.json 2>/dev/null` got no question, because splitting the line at the shell's marks left the `2` as the copy's destination. A number right before a redirection is now dropped.
- High, both: a script typed in below an interpreter (`python3 - <<'PY'`) went unread when its path sat in an assignment (`p=Path.home()/...`) or was joined onto the home folder's value (`os.environ['HOME'] + '/.claude/settings.json'`). Lines typed in for an interpreter are now read as its script, an assignment's value counts, a path starting at `/.claude` counts as built in pieces, and text typed in for a program that only reads (`cat > notes.md <<EOF`) is data and asks nothing.
- Medium: a path built by a command inside the line (`$(echo ~/.claude)/settings.json`) and a here-string handed to `xargs` slipped through; a mark is now left where the inner command was, and the word after `<<<` is read. A write to a place a variable decides, on a line that names one of the files, is asked about.
- Medium: a command run from inside the assistant folder (`cd ~/.claude && rm -rf plugins`, `cp /tmp/x .`, `sed -i ... *.json`) was never looked at because no word named a file; every word is now looked at there. The desktop app's working folders inside a linked folder's assistant folder are deliberately not on that list.
- Low, security: a pattern (`~/.cl*/sett*.json`) and a spliced name (`.cl""aude`) are now recognised, by comparing the pattern with the files' whole paths and by reading the line with quotes taken out.
- Medium, security: `link` with no folder could link the home folder after an earlier `cd`; the home folder and the top of the disk are refused.
- Medium, correctness: with two bases, `words-file` said it needed a setup run; it now names the bases, and the skill says `--base` applies to every command. `words_key` looks for a base the old way first, so an unjoined base it used to accept still works.
- Low, security: a copy of the whole disk mounted elsewhere carries the same disk identifier; a new device number in a new place is now still a remount, and the refreshed record is written only if the stored record is still the one this run read.
- Left as it is, and said in the CHANGELOG: a script in a file (`python3 fix.py`), a name built from pieces inside a script (`'.clau' + 'de'`), a write over the folder above the assistant folder as a whole, and a question for some lines that only read or only mention a file in passing (a commit message).
- Residual risks noted by the reviews, not changed: whether a PreToolUse "ask" can turn a command the person's own settings deny into one they can approve is not documented (the write check has asked the same way since 0.3.0); Codex gets "ask" here as the write check already sends it; right after a restart the disk tool may be slow past its two seconds, and then the folder still comes back unlinked, which the person fixes with "link this folder to my base"; a record written without a disk identifier is never filled in; and with a full list of documents the map gets about 2,000 characters instead of 4,000.


### 2026-10-11, the summarize-first stage (branch summarize-first, from claude/release-b-finish-1e1203)
The fidelity replay failed on Brandon's scores of 2026-10-10 (8 rule passes, 7 fails; every case fails at least one rule), so the gate builds the summarize-first stage in this release. Plan approved by Brandon in plan mode on 2026-10-11, with the three recommended options: the full evidence list in the positioning and the profile and each segment page holding its own, the independent support check kept, and a counts-only rehearsal on the real corpora before the scored re-run. The two prepared defect fixes are folded in, and all three cases are re-run once afterwards. Brandon scores; the builder scores nothing. Private figures stay in `~/GTM Bases/Gridwise/fidelity-replay/`.
- [x] U0: branch from the finish branch; merge origin/main (0.3.6) and `replay-defect-fixes`; the settings question goes before approvals and still takes a waiting ticket back (two tests, the first failed first).
- [x] U0: full suite on the merged head (2,871 tests OK, then 215 OK).
- [x] Hygiene (parent, 2026-10-11): the fixtures in `tests/test_record_change.py` and `tests/test_live_check_follow_up.py` (and one assertion in `tests/test_no_hooks.py`) rewritten from scratch with an invented company and figures; Brandon confirmed the live check's figure is public, so the walkthrough, plan and CHANGELOG lines stay and no history is rewritten. Still carrying the figure, for Brandon's call: the worked example in `skills/propose-change/SKILL.md` and two comments in `lib/gtmbase/hand_edit.py`.
- [x] U1: packing and notes requests (`notes.py`, `references/prompts/notes.md`, `notes-plan`, `notes-assemble`): every batch under the limit at 240,000 and 40,000, a file over the limit split into parts that join back exactly, nothing dropped, a stable batch digest, a changed list refused.
- [x] U2: the notes check (`notes-check`, `notes-status`): quotes found word for word in their file after evening out spacing, quotes, dashes and table marks; figures and customer names inside their quote; every file accounted for; quotes screened; setup numbers the notes; the status floor (proposed, on hold, to be clarified and the like lower a note to open); storage tied to the agreed list and resume; three attempts, then the failing items are recorded as not noted.
- [x] U3: draft requests read the notes, grouped by segment; a segment reads its own notes and the company-wide ones; adopted pages' customers placed under their segment; the preview says every file was read.
- [x] U4: citation checks in review: every paragraph and bullet cites notes; unknown citations refused; figures in a paragraph must be in a cited note; no customer named in the model's own prose; a paragraph citing a note that is not settled sits inside a `[your call: ...]` marker; the positioning names every segment; after the third refusal the failing paragraph becomes a question.
- [x] U5: the support check: an independent read of each paragraph beside only its cited words and the same segment's other notes; its answer must cover every paragraph; a flagged paragraph becomes a question.
- [x] U6: setup writes Evidence by segment, Still open in the material, and Where this came from (footnotes with file, version date and the exact words); `sources:` rebuilt from the notes cited; the same bytes shown and saved; base readers, stale-check and propose-change read the new sections.
- [x] U7: prompts, the join skill's steps 6 to 6c (subagents, resume, the loop limit), plain-language registration, CHANGELOG, atlas figure 7, plan Unit 1.9b.
- [x] Correctness and security reviews by subagents, each finding fixed with a failing test first; full suite green (712601c).
- [ ] Astra's review once Codex resets (2026-10-14).
- [x] Counts-only rehearsal, case three only (lean plan, Brandon 2026-11-25), 2026-11-24: see the section below.
- [ ] The scored re-run of all three cases, for Brandon to score.

## 0.3.7: the command check asks about reads inside the assistant folder (2026-10-15)

- [x] Reproduced: a line that moves into a session's tool-results folder under `~/.claude/projects` and reads a file with `python3 -c` was asked about whenever the script held braces or a pattern character, because `_inside_a_guarded_folder` counted every folder inside `~/.claude`.
- [x] Fix: `_inside_a_guarded_folder` covers `~/.claude` itself, `~/.claude/plugins` and everything inside it, and a linked folder's `.claude` folder. A word with `..` run from anywhere inside `~/.claude` is still worked out in full, so climbing back to the plugins folder is still asked about.
- [x] Tests in tests/test_command_check_settings.py (`TestTheOtherFoldersInsideTheAssistantFolder`). The read test failed with the 0.3.6 module swapped back in, and all four pass with the fix.
- [x] Version 0.3.7 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.3.7.
- [x] Full suite green (tests/run.sh, 2026-10-15: 2235 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened for Brandon.

## 0.3.8: the command check asks about quoted jq programs with brackets (2026-10-19)

- [x] Reproduced against the installed 0.3.7: `jq -r '... .[0:2200] ... [.attachments[]?.filename?] ...' /tmp/a` raised `re.error: bad character range 6-1` inside `fnmatch` on the macOS Python 3.9, and `gate._asks_about_settings` turns any exception into the question.
- [x] Fix 1: `_tokens` holds quoted and backslashed `*`, `?` and `[` aside while `shlex` splits the line, so each word knows whether the shell fills it in. A quoted word as a whole is a name, never a pattern; the paths inside it are still patterns, for scripts that glob.
- [x] Fix 2: `_pattern_lands_on_one` compiles the pattern once and treats a pattern that cannot compile as matching no file. Unreadable lines still ask.
- [x] Tests in tests/test_command_check_settings.py (`TestQuotedWordsAndBrokenPatterns`). With the 0.3.7 module swapped in, four fail; with either half of the fix taken out, its own test fails.
- [x] Version 0.3.8 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.3.8.
- [x] Full suite green (tests/run.sh, 2026-10-19: 2242 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened for Brandon. Not installed or released.

## 0.3.9: a line that reads a settings file and runs a reading loop is asked about (2026-10-19)

- [x] Reproduced on 0.3.8: `grep x ~/.claude/plugins/installed_plugins.json; for f in a; do grep -c x "$f"; done` asked. `do` was read as the program, an unknown program handed `$f` set `unseen_write`, and the guarded name in the first part set `named_anywhere`.
- [x] Fix: `_line_writes` reads past `do`, `then`, `else`, `elif`, `if`, `while`, `until`, `!` and `{` to the real command, and treats `for`, `select` and `case` as running nothing (a command substitution in the list is still read on its own).
- [x] Tests in tests/test_command_check_settings.py (`TestTheShellsOwnWords`). The read test fails with the 0.3.8 module swapped in.
- [x] Not fixed, on purpose: the real line still asks because of `sed "s|^|$f: |"`. sed can write (`w`) and run commands (`e`) from its script, so a variable in it stays an unseen write. Decision for Brandon.
- [x] Version 0.3.9 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.3.9.
- [x] Full suite green (tests/run.sh, 2026-10-19: 2245 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened for Brandon. Not merged, installed or released.

## 0.3.10: a double-quoted pattern with an escaped quote is asked about (2026-10-20)

- [x] Reproduced on 0.3.9: `grep -oE "gridwise[a-z0-9.-]*\.(io|ca)[^\"& ]{0,200}" /tmp/x | sort -u` asked from any folder. `gate.split_segments` ignored backslashes inside double quotes, so `\"` closed the quotes, `&` split the line, and the second part had an unclosed quote (tokens None, so ask).
- [x] Found while reproducing: the same flaw hid writes. After `\"'` the rest of the line read as single-quoted, so `grep -oE "[^\"'x]" /tmp/a | tee ~/.claude/settings.json` and `...; rm ~/.claude/settings.json` were not asked about on 0.3.9.
- [x] Fix: `split_segments` keeps the character after a backslash inside double quotes. Single quotes unchanged (no escapes there). Shared with the git check.
- [x] Tests in tests/test_command_check_settings.py (`TestABackslashInsideDoubleQuotes`). All three fail on 0.3.9.
- [x] Version 0.3.10 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.3.10.
- [x] Full suite green (tests/run.sh, 2026-10-20: 2248 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened for Brandon. Not merged, installed or released.

## 0.4.0: check what a command changed instead of reading what it says (2026-10-20)

Approved by Brandon ("ok try it") after 0.3.8 to 0.3.10 each fixed one parser case and replays still prompted on reads.

- [x] Baseline replay: 457 real Bash commands since 2026-10-20 05:00 UTC from ~/.claude/projects. PR #7 (0.3.10): 19 settings asks, 2 push-gate refusals.
- [x] Facts from the Claude Code docs (hooks, settings, plugins pages, read 2026-10-20): PostToolUse output (`decision`/`reason`, `systemMessage`, `additionalContext`); a failed command fires PostToolUseFailure; settings `env` reaches hook processes; plugin enable state needs /reload-plugins. Not documented: when `disableAllHooks` takes effect, and when Post fires for background commands.
- [x] `settings_guard.py`: snapshot in PreToolUse (inside `gate.main`, after the refusal check, only when `tool_use_id` is present), compare in PostToolUse and PostToolUseFailure, judge by meaning per file kind, put back only GTM Base's keys (whole file only when deleted or unreadable), re-read before writing so concurrent edits survive, write through links.
- [x] Removed the Bash "ask about settings" path and `settings_writes.py`. Write/Edit check and push gate untouched. Built on PR #7, whose splitter fix still matters for the push gate.
- [x] Adversarial review (subagent): 8 bypasses fixed with tests (chmod 000, install path elsewhere in cache or through a link, scope swap, env HOME and CLAUDE_CONFIG_DIR, empty folder in place of the file, byte-order mark, CLAUDE_CONFIG_DIR folder unguarded). Documented, not fixable: a command written to defeat it on purpose, delayed writes, the person's own change during a running command.
- [x] Tests: tests/test_settings_guard.py (38) and tests/fixtures/real-commands.json (42 scrubbed real commands). All 15 tamper tests fail with the guard switched off.
- [x] Full local replay on 0.4.0: 0 asks, the same 2 push-gate refusals.
- [x] Version 0.4.0 in both manifests, the library, the tests that pin it, and the atlas stamp; CHANGELOG 0.4.0.
- [x] Full suite green (tests/run.sh, 2026-10-21: 2252 tests OK, then 161 in the linked-folder rerun OK).
- [x] Pull request opened for Brandon. Not merged, installed or released.
- [ ] Live check after install (Brandon): does `disableAllHooks` written by a command still let the PostToolUse hook run; does Post fire at launch or completion for `run_in_background`; does `decision: block` reach Claude.


## 2026-11-24, the web app, version one (plan: docs/plans/2026-11-24-001-feat-web-app-plan.md)
Brandon decided to build the web app now and productize from the start. No review per unit; the end-to-end run is the main check. Two security reviews in the whole build: before anyone but Brandon signs in, and before P1 and P2 are released. Waiting for Brandon's check-in on the plan and the four "For Brandon" questions before any code.
- [x] W1. Skeleton, sign in with GitHub, and the spike (done 2026-11-24: live at https://gtm-base-app.netlify.app, commits 1729ade and 1b843e9) (can the GitHub App create a repository in a personal account; can a free organization give read-only access).
- [x] W2. Create a base from the template, or connect an existing one. (done 2026-11-24, PR #10)
- [x] W3. Read the base by CLASS part, with owner, last confirmation and open changes. (done 2026-11-24)
- [x] W4. Proposals inbox: accept (owner only, records the confirmation) or discard. (done 2026-11-24)
- [ ] W5. Invite a teammate and give them the line to join from Claude Code. (built and live 2026-11-25, PR #13; the real invite test waits for Simona's GitHub username and the Administration approval on the dev install)
- [x] W6. Changes that skipped approval: Keep or Undo. (done 2026-11-25)
- [x] Protect each base's main line with a GitHub ruleset (built 2026-11-27 on `claude/base-main-ruleset`): a pull request with a code owner's approval, no force pushes or deletion, and only the GTM Base App and repository admins can bypass it. Applied on create and backup, with a button on the Team page for an existing base, and a plain refusal with today's behaviour where GitHub's plan does not allow it.
  - [ ] Verified live only once a base is on a plan that enforces rulesets (GitHub Pro or Team) or public: a teammate's direct push to main and their merge of their own proposal on GitHub are refused; the owner's accept, keep, undo and confirm in the app, confirmation lines from Claude Code and backup still land; and whether a teammate who owns a document can accept a proposal to it in the app (the App's bypass for a teammate's own sign-in, not stated in GitHub's documentation).
  - [ ] A teammate's confirmation lines from Claude Code are refused on a protected base, because the plugin pushes them straight to main (`confirm.py`). Send them as a proposal instead: `confirm.py` already has a `plan_requires_review` path that no caller turns on; turn it on when the base's main line is protected and the seat is not an admin.
  - [ ] A base set up in Claude Code and backed up keeps the template's `@owner-handle` placeholder in CODEOWNERS, so on GitHub nobody can give a code owner's approval for it. When the app protects a base, it should fill in the owner's GitHub handle, as it already does for a base it creates.
- [x] P1. Back up a base to its repository. (done 2026-11-26, PR #16; the approval question is seen live once Brandon updates the installed plugin)
- [x] P2. Join a base from a link. (built 2026-11-27 on `claude/p2-join-from-link`: `join.py join-review` and `join-link`, the seat record, and no straight send to main from a base with a shared copy beyond confirmation lines; not merged)
  - [ ] The one-pass security review of P2 (what joining writes onto a teammate's computer, the sign-in it relies on, and the shared-line rule), before P2 ships.
  - [ ] After the web reskin (#35) merges: drop the team page's sentence that joining from Claude Code arrives with the next plugin release.
- [x] P3. Shared base: record-change and the setup closing send proposals; no direct push to main from a seat. (built 2026-11-27 on `claude/p3-shared-base`, cut from P2: `shared_send.py`, record-change's yes, `review.approve` after setup, and the closing's note; the push rule itself is in P2; not merged)
  - [ ] Other writes that still save onto a shared base's own line and would now be held at the send: creating a document or a setting through `operations.py`, the move to the current layout (`changes.py`), skipping a document, taking a finished page in after setup, and installing a skill. Each should go as a proposal the same way.
- [ ] The end-to-end run with a second GitHub account.

## 2026-11-26, the chat connector, C1 (plan: docs/plans/2026-11-26-002-feat-connector-c1-plan.md)
Brandon took the recommended answer to all four decisions. Built on branch claude/intelligent-joliot-f9b12e and deployed to the test site (https://gtm-base-connector-spike.netlify.app), which replaced the spike there.
- [x] The plan, with the library choice, the endpoint and store design, the security points and the tests. (bd11591, decisions ee2f994)
- [x] The connector built: the endpoint on the official MCP library, sign-in through GitHub with consent, single-use codes and refresh chains, the shared invite rule, one base per conversation. (fcc5d8a, ea2c330)
- [x] 40 of 40 checks pass on this computer and on the test site against the real store.
- [x] ChatGPT, end to end on the test site: sign-in, 2026-07-28 with ChatGPT's conversation id, and the one-base runs. (1c94961, b09efaa)
- [ ] The Claude half (connect, sign in, the one-base runs, whether Claude sends `com.anthropic/session` under 2026-07-28). Brandon chose on 2026-11-26 to skip it for now and come back to it together with Simona's invite (W5's real invite test), since the browser's Claude is on a work organization and the run needs his personal Claude account.
- [ ] The server's own refusal of a second base, seen from a product or from the check script's one-base section with a real GitHub App token. ChatGPT refused to send that call on its own.
- [x] The security review (one pass, 2026-11-26, on PR #18): no high or medium finding. Eighteen candidates were traced and rejected. The one residual is inherent to OAuth: someone could forward a victim their own Claude or ChatGPT sign-in link, and since GitHub signs a returning person in silently, one click on Allow would finish it. Whether that works depends on Claude's and ChatGPT's own callbacks tying `state` to the person who started the sign-in, which cannot be checked from here; the consent page's product name, return destination and warning are the defense.
- [ ] Test the forwarded sign-in risk (C1 plan, "Known risk: a forwarded sign-in link") with two accounts: start adding the connector in one ChatGPT or Claude account, finish the sign-in in a browser signed in as a different GitHub user, and see whether the first account ends up connected. Fits the end-to-end run with a second GitHub account.
- [x] The live site's settings (2026-11-26, at Brandon's request): CONNECTOR_SECRET (secret) and CONNECTOR_ENABLED set on gtm-base-app for production only, and `https://gtm-base-app.netlify.app/api/connector/oauth/github-callback` added to GTM BaseLive. They take effect only when the live site is next deployed.
- [x] PR #18 merged (6baaadb) after the nine CodeRabbit findings were fixed (1a39a7e, 45 of 45 checks on the test site), and main deployed to the live site on 2026-11-26 (deploy 6b08b757ddcfc03acda297a1; the one before it, for a rollback, was 6b084fb94460772b6bc76b50). The live site is not connected to GitHub, so it is deployed from the command line, from a checkout linked to gtm-base-app. Afterwards the web app's home page, sign-in and the 19 public connector checks all passed on the live site. The connector is on there; no product has connected to it yet.
- [ ] Teardown when C1 is done: the spike's old callback address on GTM BaseLive, the old "GTM Base test" connector in ChatGPT, and the test site.

### 2026-11-24, the Release B replay gate on the summarize-first build (branch claude/release-b-replay-40efb2)
The lean plan Brandon approved on 2026-11-25: merge main, rehearse case three alone with counts only, measure usage, and ask before the scored run of all three cases. Client figures and names stay in the private replay folder; this list holds counts only.
- [x] Merged origin/main (0.3.7 to 0.4.0 and the web app, W1 to W6). Release B ships as 0.5.0: version pins, the atlas stamp, and the layout version the move offer names (0.5). The command check keeps 0.4.0's copy-and-undo for settings and Release B's approval question; the two Release B tests of the 0.3.6 settings question now test 0.4.0's behaviour.
- [x] A stale test fixed: narrowing a draft to one file expected the run's day as the file's date, but the fixture has given that file its own date since U6.
- [x] The namer lint flagged a local dictionary in the notes code named `name_of`, the one name the lint trusts; renamed `settled_names` (pre-existing since U3 to U7).
- [x] Main's replay of 457 real commands met Release B's rule that an approval script runs only from the running plugin's own folder: one command named the 0.3.8 install folder. The test now replays it against the plugin that runs, as it was run that day; the rule is unchanged.
- [x] Rehearsal of case three at 40,000 characters in a sandbox, all seventeen files matching their frozen hashes: 2 note batches, 2 refusals (one per batch, first try), no loop limits, no file left not noted; both drafts ready on the first review; the support check turned 7 of 13 profile lines and 2 of 20 positioning lines into questions. Record in the private folder, `runs/2026-11-24-rehearsal/`.
- [x] The note request now states the three rules the notes check refused by and never told the note taker (contact details in a quote, a segment named outside its quote, a note credited to a segment its own heading does not name); a test failed first.
- [x] Brandon's decision (2026-11-24): every draft reads the notes, and at 40,000 characters both drafts left out 209 of 516 notes (whole segments among them), because the notes are as large as the files they come from (108%). The sections setup writes (evidence, still open, footnotes) use every note, so the loss is to the drafted prose. Brandon chose the digest; plan written at `docs/plans/2026-11-24-002-feat-note-digests-plan.md` (Unit 1.9c), waiting for his review and his three decisions.
- [x] Unit 1.9c approved by Brandon on 2026-11-24 with the recommended answers to all three decisions.
- [x] D1 to D4: `digests.py` (the plan, the request, the check, what a draft reads), `references/prompts/digest.md`, the four commands `digest-plan`, `digest-assemble`, `digest-check` and `digest-status`, the notebook carrying the digests (so a request, review and support all see the same lines), and the preview sentences. `tests/test_digests.py`: the core tests were written just after the module rather than before it, so each guard (the carry rule, the status rule, the figure rule, largest first, customers kept, narrowing) was proven by breaking it once in place and watching its test fail; the last-resort test (a request never goes over the limit, open lines kept longest) failed first.
- [x] D5: join skill step 5f and its wait line, a paragraph in each draft prompt on condensed lines (cite the ids, never quote a shorter line as the company's words), the CHANGELOG, the atlas caption, plan Unit 1.9c.
- [x] D6, the correctness review (one subagent pass): five findings, each with a test that failed first. (1, high) the last resort sized whole groups with customer words held back and printed them in full, so a request could go over the limit; (2, high) it left out open, customer and segment notes before settled shorter lines; both fixed by one ordered last resort (settled shorter lines, then customer words, then settled facts, then the rest, and a request still over says so). (3) a narrowed draft could lose an open note and count it as settled; setup now carries it and only settled facts are counted. (4) review and support took the full view's notes, not the narrowed request's; each request now remembers its own notes. (5) checking a done digest again wiped it; a kept digest now stays kept. The check also sizes lines as they are drawn.
- [ ] Follow-up, not in this change: `notes-check` on a batch already done starts it again at attempt 1 and throws its notes away, the same pattern as finding 5.
- [x] D6: full suite on 008598b (3,021 OK, then 215 OK); committed.
- [x] Rehearsal two of case three on 008598b, counts only (record in the private folder, `runs/2026-11-24-rehearsal-two/`): notes 2 batches, both accepted first time; 8 digests, none hit the loop limit; each draft read 412 of 514 notes, and every note it did not read was a settled fact (rehearsal one: 307 of 516, with 51 customer and 13 segment notes unread); usage 10 points of the five-hour window and 1 of the week.
- [x] Two defects in the digest check, found in rehearsal two and fixed test first: the check counted each line's note numbers and status, then a line break per line, against a room the request gives for the words alone.
- [ ] Follow-up (tuning, not correctness): the plan gives each digest room for its words only, so the note numbers and status of each line push the last resort to leave out settled lines (70 in rehearsal two).
- [x] Brandon's go-ahead for the scored re-run of all three cases (2026-11-24). Cases one and three drafted, outputs, blank sheets and evidence packs in the private folder `runs/2026-11-24/`. Case two stopped after its notes (all thirteen batches checked): its customer and segment lines alone exceed one draft request.
- [x] Brandon's call (2026-11-25): stop case two and fix the design. Plan written: `docs/plans/2026-11-25-001-feat-digests-at-scale-plan.md` (Unit 1.9d), approved the same day with the recommended answers.
- [x] Unit 1.9d built test-first: customers of a condensed group as a count, three segment notes kept in their words, honest rooms (no floor without room, note numbers and line additions counted, a digest with no room carried by setup, the plan says up front when setup's own lines do not fit), each draft waits only for the groups it reads. Plan counts on case two's kept notes, no subagent: 17 digests (was 38), not over; with digests kept to their rooms a draft reading every group comes to 237,972 of 240,000 characters with nothing left out, and every segment's draft fits. One correctness review: three findings fixed test-first (rooms now also count the numbers of settled notes and each line break; the count of the whole company's customers no longer says a document lists them, since a segment's document does not; the skill says the over-the-limit sentence before anything else), and a room smaller than one average line is now no room. Risk to watch: digest 1 (the whole company's notes) must carry 915 open notes in 21,236 characters, so lines have to join several open notes each.
- [x] Unit 1.9d: full suite twice, green both times (3,038 main tests and 215 linked-folder tests, exit 0 each run), committed.
- [x] Found during case two's digests (2026-11-25): the figure check read an amount with a capital unit ($900K, $1.4M) as the bare number, so a figure word for word in its note was refused (digests 8, 10 and 12 each lost figures to pass). Fixed test-first in citations (units read in any case); the citation, digest and review tests pass. Case two's drafts run on the fix; cases one and three were drafted before it.
- [x] Figure fix: full suite twice, green both times (3,039 main tests and 215 linked-folder tests, exit 0 each run).
- [x] Case two resumed and finished on 2026-11-25: 17 digests accepted (12 first try, 5 second), all 13 documents approved with questions open; outputs, evidence pack and README filed with the run (outside this repository).
- [x] Brandon scored all three cases on 2026-11-25: every rule and every case passed, on his instruction "pass all", given after he was told the record would carry no notes for each rule. The scores, in his words, are in the run's README outside this repository. Nothing merged or released.
- [x] Case two resumes from its kept notes on a plugin copy of the new commit (done 2026-11-25, above).
- [x] Brandon scores cases one and three, and case two once it is run (done 2026-11-25, above).
- [x] The scored re-run of all three cases (done 2026-11-25). The gate passes.
- [x] Customer-name check fix: it went into Release B and is on main as 990e1a9 (PR #15). Brandon decided on 2026-11-27 that a city's name recorded as a customer's name stays refused, and the refusal now says how to fix it: record that customer under a fuller name, such as the company's full name (branch `claude/decisions-1127`).
- [x] Brandon: review and merge Release B (0.5.0) into main. (merged 2026-11-25, PR #15)

## 2026-11-26, the connector for Claude chat, Cowork and ChatGPT (plan: docs/plans/2026-11-26-001-feat-chat-connector-plan.md)
The order across every track is in `docs/plans/2026-11-26-003-roadmap-to-full-experience.md`. No review per unit; one security review before anyone but Brandon connects.
- [x] S0. The spike: what Claude and ChatGPT accept from a remote connector. (done 2026-11-26, PR #17)
- [x] C1. The endpoint, GitHub sign-in and one base per conversation. (merged and live, PR #18)
- [x] C2. Reading documents, with the moment-of-use flag in the answer. (PR #23, merged as 429da77 and deployed to the live site on 2026-11-26 as deploy 6b08e688339d2aae566195f8; the one before it, for a rollback, is C1's 6b08b757ddcfc03acda297a1. The ChatGPT run passed end to end on the test site, the security review found nothing at the bar, and on the live site the home page, sign-in and the 19 public connector checks pass. The Claude half waits for Simona's invite.)
- [x] C3. Skills served live: `use_skill` ("Use a company skill"), the skill index in the instructions and at the end of `list_documents`, only versions another computer would accept, each declared document through the moment-of-use check, no write into `skills/`, and a tested seam for Track 4's `context/icps/` folder declaration. (branch `claude/connector-c3`; built 2026-11-27; deployed to the test site only)
- [x] C4. Proposing a context change from chat. (shipped with C2 in PR #23)
- [x] C5. The setup guide and a Project instruction for each base, shown on each base's page when the connector is on. (branch `claude/c5-setup-guide`; web build, lint, type check and the 69 stale-parity checks pass; deployed to the test site gtm-base-connector-spike on 2026-11-26 as deploy 6b08e9a83a9d29a0988fe498 and checked there on the gtm-base-test page, including the copy button. Not deployed to the live site.)
- [ ] Carried over from C1 and C2, all needing Simona's account: the Claude half of the run, the refusal of a second base in one conversation, and the sign-in test with two GitHub accounts.
- [x] Brandon: decide the borderline proposal pattern from C2's security review, once for the plugin and the connector. (decided 2026-11-27: it is closed in C3's security pull request, for both together)
- [ ] Take down the connector's test site once the Claude half has passed.
- [x] The security review of C3 (one pass on 4e10ddb): four findings, fixed in the plugin and the connector together on branch `claude/c3-security-fixes` (roles read only from approved state, an approval ends when its skill's folder changes after it, and segment names limited to lowercase letters, digits and hyphens), and the skill index moved out of the instructions into `list_documents` only. Deployed to the test site only.
- [ ] The reviewer confirms the four fixes, then the end-to-end run in Claude and ChatGPT across two Projects.
- [x] When Track 4's runner reads `reads_optional: [context/icps/]`, add `context/icps/` to `FOLDER_DECLARATIONS` in `web/src/lib/stale/skills.ts` and regenerate the skill parity fixtures (`tests/skill_parity.py`). (PR #36, merged as 4e10ddb)

## 2026-11-27, Brandon's decisions on the roadmap (`docs/plans/2026-11-26-003-roadmap-to-full-experience.md`)
- [x] The borderline proposal pattern: closed in C3's security pull request, for the plugin and the connector together.
- [x] Denver: the customer-name check keeps refusing a city's name that the notes record as a customer's name, and the refusal now says how to fix it (record that customer under a fuller name, such as the company's full name).
- [x] Simona's GitHub username: on hold, by Brandon's choice. The invite test (W5) and the two-person end-to-end runs wait with it.
- [x] Sign-up: opens only after C3's security fixes are confirmed, P2's security review is done and both end-to-end runs pass, and then by invitation to a short list before anything is public.
- [x] Pricing: GTM Base stays 100 percent free and may be open-sourced. Step 6 of the roadmap is now sign-up and a domain, with no pricing or billing work. The plugin already declares the MIT license.
- [ ] Brandon: buy the domain on Monday, 2026-11-30. It blocks nothing before sign-up.

## Plan 1, company skills and the Meta ads skill (plan: docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md)
Step 2 of `docs/plans/2026-11-26-003-roadmap-to-full-experience.md`. The planning documents and the four built units were brought up to date with main on 2026-11-26 (branch `claude/plan-1-catchup`), keeping every Release B and backup rule (full suite on the merge 5e80a5b: 3323 tests OK, then 223 OK from a linked folder). The sections below are the original build records from 2026-10-10.
- [x] Unit 4.1. The company-skills requirements, signed by Brandon on 2026-10-10.
- [x] Unit 2.1. The base inventory.
- [x] Unit 2.5a. The source map parser.
- [x] Unit 4.2a. One authority rule, one path rule, approvals bound to bytes, and the refusal in an unattended run.
- [x] Unit 3.1. The thin runner, its contract test, and atlas figure 9. Built 2026-11-27 on `claude/plan-1-runner`: `runner.py`, the use-skill skill, `docs/thin-runner.md`, `tests/test_runner_contract.py`, figure 9. A skill's own text names no runner command (the Track 4 plan). The moment-of-use check reads documents as last saved when the runner asks. Outside review (Astra security and correctness) still owed before Release C.
- [x] Unit 4.2b. The skills folder. Built 2026-11-27 on `claude/plan-1-skills-folder` (cut from the 3.1 branch): `skillshape.py` (what the folder admits, asked by the trust check, the update and the send), `skill_install.py` (install with both yeses, change, accept), the write check still refusing file tools, the runner's attended showing. Needs its own security pass before it merges.
- [ ] Unit 4.2b follow-ups: a skill listed by the review when it goes stale (CS28), and the map paragraph in `changes.py` that still says the skills folder is kept empty. (The session start naming trusted skills, CS25, is built with Unit 3.6.)
- [x] Unit 2.4a. Metric definitions and goals. Built 2026-11-27 on `claude/plan-1-goals-and-standard`: drafted after setup from the owner's answers, in a business's folder when one is named. The Gridwise driver-app content itself is drafted in live session C, outside this repository.
- [x] Unit 3.5. The standard kind, its five parts and its digit lint, drafted for a named job. The creative-testing standard itself is drafted in live session C from the Meta skill's rules, outside this repository.
- [x] Unit 3.6, the repository side. Built 2026-11-27 on `claude/plan-1-meta-skill-shape`: the session start lists trusted base skills (CS25), and a made-up nightly ad skill in `tests/fixtures/base-skills/meta-ads/` is tested on the runner.
- [ ] Brandon: live session D for Unit 3.6, outside this repository. Move the real Meta ads skill into the Gridwise base through the install, after the migration checklist; check the scheduled task before the move; approve its new prompt and tool list; watch the first night attended.
- [ ] Brandon: the SC-M window and its walkthrough (`docs/walkthroughs/2026-10-meta-skill-on-the-base.md`), written from real nights only.
- [x] Brandon: review and merge the catch-up pull request. (merged 2026-11-26, PR #22)

## Track 4, what a base holds (plan: docs/plans/2026-11-27-001-feat-track-4-base-contents-plan.md)
All ten decisions made on 2026-11-27. No review per unit; the end-to-end run in the plan is the check.
- [x] T4.1. A recorded decision suggests the documents built on it.
- [x] T4.2. Messaging and voice, adopted or drafted.
- [x] T4.3. Buyer personas and product.
- [x] T4.6. The source map for any company.
- [x] T4.8. Drift grade, the first skill on a base. (waits on Plan 1's 3.1 and 4.2b)
- [x] T4.4. Competitors.
- [x] T4.5. Design.
- [x] T4.7. Update GTM Base.
- [x] T4.9. The content brief. (after T4.8 and T4.2)
- [x] T4.10. The outbound sequence. (after T4.8)

### 2026-10-10, Plan 1 of Phases 2 and 3 (branch claude/plan-1-meta-skill-3d436e)
Plan: `docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md`. Planning only; no product code.
- [x] Read the decisions brief (D1 to D10, M6, M7, M8, M12), the roadmap on release-b, the build plan through call 59 on the finish branch, and the Meta skill as it runs today (read only)
- [x] Write revision 1: Units 4.1, 4.2, 2.1, 3.1, 2.4a, 2.5a, 3.5, 3.6 in two releases; SC-M proposed; seven calls for Brandon
- [x] Astra reviews the plan read only (brief: docs/reviews/2026-10-10-plan-1-review-brief.md); fix and confirm until ready.
      r1 not ready (16 findings, 2 blockers on the ownership proof) -> r2 not ready (9 narrower) -> r2.1 ready with 2 changes
      -> r2.2 ready with 1 change -> r2.3 ready to build as written (docs/reviews/2026-10-10-plan-1-verify-4-astra.md)
- [x] Rebuilt this branch from origin/main with a cleaned decisions brief (no goal figures, pipeline figure or workbook name);
      the six Plan 1 commits replayed on top. Local backup ref plan-1-backup-before-rebuild still holds the old history:
      delete it once checked, and never push it
- [x] Local main reset to origin/main (3c2c377), dropping the uncleaned decisions commit
- [x] This repository's git address set to Brandon's personal one (repo config, all worktrees); the branch rebased onto
      origin/main and every commit re-authored under it. 120 older commits already on the public main carry the Gridwise
      address; changing those means rewriting the public main, which is Brandon's call
- [x] Brandon answered the seven calls on 2026-10-10, all as recommended (1 two businesses, 2 SC-M, 3 unattended flag, 4 old skill copy, 5 releases, 6 ownership guarantee, 7 lessons)
- [x] Unit 4.1 written: docs/brainstorms/2026-10-10-company-skills-requirements.md, revision 3. Astra and Fable 5.1 said
      not ready on r1 (Astra 8 findings; Fable 1 blocker, 3 high, 9 medium, 8 low); r2 ready with 3 changes; r3 ready for
      signature (docs/reviews/2026-10-10-company-skills-verify-2-astra.md). Plan 1 kept in step, now revision 2.6
- [x] Corrected for Release B's call 60 (approvals go through unasked in bypassPermissions and dontAsk): requirements
      revision 6, Plan 1 revision 2.9; Astra ready for signature again (docs/reviews/2026-10-10-company-skills-verify-5-astra.md)
- [x] Brandon signs Unit 4.1 (covers scripts, the extra yes for creating a skill, and the guarantee in CS13 and CS14); signed 2026-10-10;
      Unit 4.2a is not briefed before he signs

#### Review (Plan 1)
Nine units in two releases (C: 4.2a, 2.1, 2.5a, 3.1, 4.2b, 2.4a, 3.5; D: 3.6), plus 4.1 first. The hard part was D5's
"provable": history fields prove nothing on one computer, so the plan binds each approval to exact bytes and a seat runs a
skill only as a whole manifest it approved or accepted, with the guarantee stated exactly as call 6. Planning only; no code.

### 2026-10-10, Plan 1 read side: Unit 2.1's inventory and Unit 2.5a's parser (branch claude/plan-1-read-side-6c5559, from the Release B finish branch)
Built ahead of Release B shipping and ahead of Unit 4.2a, as the plan's "dependency on Release B" paragraph allows: nothing here writes, approves, or touches a base's `skills/` folder. New files wherever possible; shared files touched only append-only (`constants.py`, `names.py`, `tests/plain_language.py`) or by one small read-only flag (the stale-check script and its skill).
- [x] `businesses.py` (new): the map's `businesses:` setting and a document's `business:` line, read only. Provisional grammar; Unit 4.2a owns it and adopts or replaces this reader.
- [x] `BASE_KINDS` (constants, appended) and `base-kinds.md` (stale-check reference), every entry with a section and every section with an entry.
- [x] `inventory.py` (new): the table per business, business not stated, documents for a business the map does not list, the scope finding against the customer profile, drafting offered only for what this release drafts (nothing yet).
- [x] `--inventory` on the stale-check script and one section in its skill; the documented command walked by the existing test.
- [x] `truth_map.py` (new): the source map's five-column table parsed and validated, screened, never calling anything; the template's empty table.
- [x] Tests first: `tests/test_inventory.py`, `tests/test_stack.py`; watch them fail, then build.
- [x] Full suite, correctness review subagent, findings fixed, suite again.
- [x] Commit 977cf64 (suite 2918 OK, then 217 OK from a linked folder); hand-over note in the shared notes folder.
Deferred, with the reason (they need Unit 4.2a's path rule or its operations): a standard flagged and blocked at the moment of use; a skill past its threshold due in the review; reading the base at its last saved revision for the runner; the inventory inside the review; human names for business-folder documents in sentences; a prepared change adding a source map row; the drafting prompt for source map rows.

#### Review (Plan 1 read side)
- Built test-first: `tests/test_inventory.py` and `tests/test_stack.py` failed on import before any code existed; 80 tests then passed. Mutation check: eight guards (not-stated counting, unreadable not missing, the key screen, an incomplete row, folder and setting disagreeing, a profile that states its business, reserved names, the source map's own password screen) each fail when their code is removed. The first password-screen test passed without proving its claim (the email screen caught the row too) and was replaced.
- Correctness review subagent: one high finding and nine lower, all fixed with a test that failed first. High: the screens split lines by a wider rule than the parser, so a page break or line separator above the table moved the refusal onto the wrong row and let a key row through; screening is now one line at a time. Others: a short name or a name ending in a full stop in `covers:` read as leaving a business out; a negation reached across a full stop; a document at both its older and current path counted twice; with no businesses listed, a subfolder was reported as an unlisted business (now ignored, "exactly as before"); a four-cell row was malformed rather than incomplete; a dash counted as a fallback; several documents claimed "not all confirmed" when confirmations could not be read; a linked context or access folder was followed; "nothing missing" was said over a skipped kind. Also from its residual list: a heading inside a block of code no longer ends the table's section, a row's business is not judged when the map's list cannot be read, and a `business:` line may give the name the map gives.
- Recorded for Brandon (the review's "decision" item): for a kind one document serves the whole company (voice, design, source map, standard, skill), a flat document with no `business:` line counts for the whole company. Requirement P40 says such a document "counts for no business"; read literally, every base that lists its businesses would show its voice guide, source map and standards as missing. Brandon to confirm or overrule.
- Not done here, each waiting on Unit 4.2a: a standard flagged and blocked at the moment of use; a skill past its threshold due in the review; the base read at its last saved revision for the runner; the inventory inside the review; names for business-folder documents in sentences; a prepared change adding a source map row; the drafting prompt for rows. No CHANGELOG entry and no version change (both belong to the release that ships this). The map's `businesses:` grammar is provisional and Unit 4.2a's to settle.
- Follow-up: Astra's outside review of this branch (Codex is rate-limited until 2026-10-14).

### 2026-10-10, Plan 1 Unit 4.2a: one authority rule, one path rule, approvals bound to bytes (same branch)
Briefed by the orchestrating session after Brandon signed the company-skills requirements (commit 80378c6 on claude/plan-1-meta-skill-3d436e). Built from CS1 to CS18 and CS30 and the plan's Unit 4.2a text. The two `approval.py` edits were cleared by the orchestrating session first and sit in commits of their own.
- [x] The map's settings block (CS2): one `owner:`, `administrators:` (may be empty), `businesses:`; 2.1's reader moved to the block.
- [x] `docpaths.py`: which paths may be a base document, of what kind, and which operation may write each; every module that answered part of that asks it.
- [x] `authority.py`: the authority set as of a saved revision (CS3, CS4), failing closed when the history cannot be read; a skill's manifest (CS10); this seat's trusted manifests (CS11); one file per conversation marked unattended (CS30).
- [x] Approve, confirm, the stale computation, the review, the moment of use and setup's closing ask `authority` only. Records carry roles and byte hashes; confirmation lines carry the role; no new field writes an address.
- [x] Creation, absent-only in either layout and all or nothing, with the creator's confirmation; a lesson at `learning/lessons/<slug>.md`.
- [x] The five settings operations, each shown with the one line before and after, bound, re-worked out from the base at approval, recorded with the reason; a hand edit may not move an owner or business line.
- [x] Prepared changes reach standards and the source map; every way into the source map runs its credential screen, the send check included.
- [x] `approval.py` (own commits): CS30 refusal as `decide()`'s first test in every mode; create and the five settings operations in the table, each with its own sentence.
- [x] Tests first; correctness and security review subagents (2 high and 9 lower, and 1 high and 5 lower), every finding fixed with a test that failed first.
- [ ] The propose-change skill text for `operations.py` (needs the skill-walk test's placeholders), before live session C.
- [ ] Astra's outside review of all four commits (Codex rate-limited until 2026-10-14).

#### Review (Unit 4.2a)
- Commits 94aa730, a523d9a (approval.py), 16fd6a4 (review fixes), db647ab (approval.py). Suites: 94aa730 3018 OK then 217 OK; db647ab 3063 OK then 223 OK from a linked folder, exit 0.
- Deviations recorded for Brandon: (1) CS9's address is the author of the saved record or line, not text in it, because the check before a send refuses any address but the base owner's; (2) a standard or the source map joins the time-based review only once first confirmed; (3) CS3 changed three older tests' premises (a document with no owner is the base owner's to approve; the base owner's confirmation counts anywhere; a stranger's yes is refused before it is written); (4) CS9 records are written on approvals made on this computer, not yet on the shared-copy path, which the backup plan decides.
- The security review's high finding: a prepared operation kept on the seat was trusted at approval, so a rewritten file could pass the map's owner role through a "creation" question. Approval now works every change out again from the base and refuses anything that differs from what was shown.
