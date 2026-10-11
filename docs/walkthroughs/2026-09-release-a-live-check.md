---
title: "Release A: the live check"
type: walkthrough
status: run; three blocking findings open (2026-10-10)
date: 2026-09-20
plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md
---

# Release A: the live check

This is the list Brandon works through in his own Claude Code once Release A is installed on his machine. Every unit in the release changed sentences a person reads, and three real runs have already shown that tests do not catch a sentence that is true and still wrong. Results go at the bottom of this file, from the real run only. Nothing here is filled in ahead of time.

One seat exists, so installing the release on that seat is the release. The version is bumped, the plugin is updated on Brandon's machine, and this check follows. If a step fails, it is fixed and the version is bumped again.

## Before starting

1. Update the plugin, then quit Claude Code and open it again, because hooks load when a session starts.
2. Release A adds two hooks that run in every session on the machine: one before a file is read and one before a file is written. If anything about ordinary work feels wrong during this check (a file write refused that should not be, a noticeable pause on every read), stop, turn the plugin off in the plugin manager, and tell Claude what happened. Turning it off is the way back.

## The steps

Each step says what to do, what should happen, and what to write down.

### 1. A quiet start
Open Claude Code in `~/Gridwise` and ask for something ordinary that has nothing to do with GTM Base.
- Expected: a working session with no question in it. The base does not ask about the map or about anything else.
- Write down: whether anything was asked.

### 2. Review my base
Say: review my base.
- Expected: one short line per item, each naming a document in plain words (your customer profile, your positioning), never a file path or an identifier. The offer to update how your context changes are stored appears once.
- Write down: whether every line could be read in seconds, and any line that named a path or an identifier.

### 3. Look before moving anything
Ask Claude to check what updating your context changes would do, without doing it.
- Expected: a plain description of what would move and that it would be offered. Nothing in the base changes.
- Write down: what it said.

### 4. The update itself
Say yes to the update.
- Expected: one sentence saying the update is done and that your context change says what it said before. The next review reads the same as the one in step 2, minus the offer.
- Write down: the sentence, and whether the next review matched.

### 5. A hand edit
Open `context/strategy/positioning.md` in the Gridwise base in Obsidian or any editor, change one real sentence, and save. Then tell Claude you edited your positioning and want it kept.
- Expected: one question, "What changed, and why?". After your answer, the whole difference between the saved version and your edit is shown, then one request: approve, leave it, or drop it. On approve, the document is saved and confirmed, and a context change carrying your own sentence is recorded.
- Write down: whether the difference shown was exactly your edit, and whether the recorded context change reads as your sentence.

### 6. A typo
Fix a typo in the same file and tell Claude to keep it, answering that it was only a typo.
- Expected: the edit is kept and no context change is recorded.
- Write down: whether anything was recorded.

### 7. The moment of use, measured
This is the trial the plan sets a bar for. The bar is ten real prompts with the flag firing on at least nine, unless Brandon sets another bar before starting. Write the bar here before step 7 begins: **9 of 10**, the default, set by Brandon on 2026-09-27 (in the orchestrating session).

First record a context change that makes the customer profile out of date (through the review, or by telling Claude what changed). Then, across ten separate ordinary requests that would use the customer profile (draft an email to a prospect in a segment, outline a landing page, summarize who we sell to), count how many times Claude stopped first and said the profile had not caught up with that change.
- Expected: it stops, names the document and the change in plain words, shows the four lines, and asks whether to use it as it stands, fix it first, or say it already reflects the change.
- Write down: the count out of ten, and for each miss, what the request was.
- Then answer one of each: "use it as it stands" (nothing is recorded and it still flags next time), "fix it first" (a real replacement is written, shown, and approved; the flag clears), and on a second change "it already reflects this" (one confirmation is recorded).

### 8. A setup closing
In a scratch folder holding two or three real marketing documents, say: set up my company base. Go through to the end.
- Expected: two documents drafted, then three plain sentences about what a context change is with one example, then the request: "Tell me if anything about the context of the business changed that we should account for. One sentence is enough, or say skip." Give it a real sentence. The entry is shown whole with each fact correctable. For each of the two documents it affects, it asks whether that document already says what the change says. Answer no for one: a replacement is written and approved, and the closing never says nothing is out of date while that change is waiting.
- Write down: whether the three sentences made sense on first hearing, and the closing sentence word for word.
- Afterwards the scratch base can be deleted.

### 9. Ordinary work is untouched
In a client repository that is not a base, make an ordinary commit and push, and have Claude write and edit a few ordinary files, including a file whose name begins with a dot.
- Expected: nothing is refused and nothing is asked.
- Write down: anything refused.

### 10. Your own settings
Ask Claude to add a harmless permission to your Claude settings.
- Expected: Claude Code's own permission prompt appears with GTM Base's reason attached. It is a question, not a refusal.
- Write down: whether it asked or refused.

## What would stop the release

Any ordinary write or push refused in step 9. Any document other than the one edited being changed in step 5. The update in step 4 losing or rewording the context change. The flag count in step 7 falling below the bar, which the plan answers by saying plainly in the changelog and the join guide that outside a skill the flag is best effort.

## Results

[RESULTS TK — Brandon: fill in from the real run, step by step, with the date. No estimates.]

### Step 2, run 2026-09-26 (from Brandon's screenshot of the session, and a read-only check of the base by Claude)

What happened: before answering, the assistant ran four commands, three of which failed, and said it did not know where the base was and that the plugin's records folder "blocks direct commands", so it asked the plugin for the linked folders instead. It then said: "Your base is up to date. Nothing in it is due a look today, and no changes are waiting for your approval. It lives at ~/GTM Bases/Gridwise/gtm-base and is linked to ~/Gridwise, so it comes along whenever you work in this folder."

Findings:
1. The offer to update how context changes are stored did not appear. A read-only `--check-move` on the base the same day says the base holds one context change in the old folder and "As things stand, GTM Base would offer this." Not yet known: whether the review ran in review mode and the assistant left the offer out, or the review never ran. Needs the two commands the session ran.
2. Three failed commands before the review, and internal plumbing narrated to the person. The assistant should not have to look for the base: the session's injected context should name it. Not yet known: whether the injected context arrived (was Claude Code restarted after the update?) and which commands failed.
3. "Your base is up to date" is the assistant's own summary and claims more than the review can know. The product's sentence is "Nothing in your base is due a look today". The skill should tell the assistant to relay the review's sentences rather than summarize them.
4. Found by the read-only check, not seen by Brandon: `--check-move` prints the raw change id to the person.

What worked: plain words, the base's location and link stated correctly, nothing written.

### Step 2 again, 2026-09-26, after Brandon confirmed he had quit and reopened Claude Code

Brandon reran "review my base" in ~/Gridwise and expanded the commands. The session ran the stale-check skill, failed to run the review from ~/Gridwise with "This folder is not a company base you have joined yet", then went looking for the base (read how the base is resolved, listed and showed the linked folders), ran the review from inside the base, and ran a dry-run stale check. Its answer summarized rather than relayed, named raw file paths, and told Brandon the review "only runs from inside the base folder".

Root causes, verified by Claude the same day with read-only checks against the installed 0.3.0:
1. **Every skill script refuses the folder the person actually works in (blocking).** From ~/Gridwise, `paths.resolve_base` returns code `linked` with the base's root and id, but `joined` is False, and six scripts refuse unless `resolution.joined` is true: skills/stale-check/scripts/stale_check.py (line 185), skills/confirm/scripts/confirm.py, skills/propose-change/scripts/propose.py and approve_local.py, scripts/moment.py, and scripts/seat.py. Session start resolves the same folder correctly, which is why the base "wakes" but no command works. This also explains the first run's three failed commands. Every later step of this check that runs in ~/Gridwise (moment of use, hand edit, confirm) would hit it. The tests missed it because every script-level test and the skill walk run from inside the base, never from a linked folder.
2. **The review never makes the update offer.** From inside the base, `stale_check.py --review --dry-run` printed only "Nothing in your base is due a look today, and no change is waiting for you to approve it.", while `--check-move` on the same base says "As things stand, GTM Base would offer this." Not yet known whether the review returns before reaching the offer when nothing is due, or whether a dry run skips it.
3. The skills let the assistant summarize and add advice (raw paths, "the review only runs from inside the base folder", adding Q4 targets to the base, which contradicts targets staying in their tools). The skills should tell the assistant to relay the review's own sentences.

Decision: the live check is paused at step 2 until finding 1 is fixed and released, because steps 3 to 7 all run in ~/Gridwise.


### 0.3.1 released, 2026-09-26: resume at step 2

All three root causes above are fixed in 0.3.1 (commit on main the same day, installed on Brandon's machine with `claude plugin update gtm-base@gtm-base`). The six scripts accept a folder linked to a base, the review makes the update offer when nothing is due, the look before the update counts changes in words rather than naming their identifiers, and the skills tell the assistant to run from the folder the person is in and to say the scripts' own sentences as they are. Every script-level test class and the skill walk now also run from a linked folder, and on the 0.3.0 code those new tests fail 18 times with one error. Suite: 2016 tests, plus 99 from a linked folder, all passing.

Not verified by Claude: the release against the real Gridwise base, because a read-only run from ~/Gridwise was blocked by the session's permission mode. Step 2 of this check is that verification.

To resume: quit Claude Code and open it again, open it in ~/Gridwise, and start again at step 2. Expected at step 2 now: no command fails before the answer, the answer is the review's own sentence ("Nothing in your base is due a look today, and no change is waiting for you to approve it."), followed (after the quiet-record question, if that is due) by the offer: "Your context changes are stored the old way. Updating them takes one step and changes nothing they say. Shall I do it?"

### 0.3.1 live check, run 2026-09-27 (from Brandon's screenshot of a new session opened in ~/Gridwise, plugin 0.3.1)

**Step 1, a quiet start: passed.** Brandon said "hey what's up". The reply offered his weekly-planning skill and named the branch and uncommitted files in ~/Gridwise, which come from his own setup in that folder, not from GTM Base. Nothing was asked on the base's behalf and nothing was said about the map.

**Step 2, review my base: passed.** Brandon said "review my base". The session ran one command and used one tool, with no failed command shown and no search for the base. Its whole answer was the review's own two sentences, word for word:

> Nothing in your base is due a look today, and no change is waiting for you to approve it.
>
> Your context changes are stored the old way. Updating them takes one step and changes nothing they say. Shall I do it?

Every line reads in seconds. No path, identifier, "up to date", or added advice appeared, and the offer that 0.3.0 never made appeared once. All three 0.3.1 root causes are confirmed fixed in the real run. Not yet confirmed: the expanded command, to see that it ran from ~/Gridwise without an error.

**Step 2, Brandon's note on the offer (2026-09-27).** At first glance the offer reads like a plugin update. It is really a change to how the base stores its files, made necessary by a newer version, and it names neither the version nor what moves. Finding for the build: the offer says which version introduced the change and what moves, in release-notes style, from the real base. Proposed for 0.3: "GTM Base 0.3 stores context changes in a new folder, and your base still keeps its one context change in the old one. Moving it changes nothing it says, and your base works either way until you do. Shall I move it now?" The Unit 1.5b offer has the same problem at a larger scale and should name the version and each kind of thing it moves, with counts and document names from the real base. Brandon has not yet approved these words.

**Step 3, look before moving anything: passed, with two findings.** Brandon asked what the update would do without doing it. The session previewed without writing and said:

> This would update one of your context changes and write one dated record of it under today's date, 2026-09-27. It would be saved as two separate pieces of work. Nothing has been written.
>
> As things stand, GTM Base would offer this.
>
> When you want to go ahead, I'll also need you to confirm that everyone who opens this base is on the current version of GTM Base.

The first sentence is the script's own, with no identifier (0.3.1's fix to finding 4 works), and nothing in the base changed.

1. "As things stand, GTM Base would offer this." is the script's own sentence (`changes.OFFER_STATE_NOW`), relayed correctly, but it is written for the builder rather than the person and means nothing to Brandon. Fix: say nothing when the offer would be made, and when it would not, say the plain reason (unsaved edits, a change written twice, a shared base whose seats are not yet updated).
2. The third sentence was added by the assistant and is wrong for this base. The script did not print it. `changes.migrate` asks for the every-seat confirmation only when the base has a shared copy (`paths.remote_url` is set), and the Gridwise base has none. The assistant took it from the stale-check skill's table of commands, which lists `--every-seat-updated` without saying it applies only to a shared base. This breaks 0.3.1's rule that the assistant adds no claim of its own. Fix: the skill says to ask about other seats only when the script's own sentence asks it, and the shared-base sentence keeps its one-line reason (an older version reads an updated base as empty, so a teammate would be told nothing is out of date). Brandon asked for that reason to be stated whenever the confirmation is asked.

**Step 4, the update itself: passed, with two findings.** Brandon said yes. The session ran the update and replied:

> I ran the update. You didn't confirm that everyone who opens this base is on the current version of GTM Base, and it didn't ask for that, so I left that confirmation out. Its result:
>
> Your context changes are now stored the way GTM Base stores them today, and all 1 of them say exactly what they said before.

He then said "review my base" again, and the answer was the review's own sentence and nothing more: "Nothing in your base is due a look today, and no change is waiting for you to approve it." It matches step 2 minus the offer, so the move landed and the context change reads the same.

1. The script's sentence (`changes.MIGRATED`) says "all 1 of them" for a base holding one context change. Fix: the count in words, and the singular for one ("your one context change says exactly what it said before"), as the look before the update already does with `changes.counted`. Unit 1.5b replaces this sentence, so the fix belongs there as well.
2. The assistant narrated how the command works, walking back its own invented claim from step 3. Same cause and same fix as step 3 finding 2: the skill never mentions the other-seats confirmation unless the script's own sentence asks it, and the reply after the update is the script's sentence alone.

**Step 5, a hand edit: in progress, findings so far (2026-09-27).** Brandon said he had edited his positioning and wanted it kept, before he had saved the file. The session said "Your positioning doc passed its check, and nothing has overtaken it." and then asked where the edit came from. After he saved, it summarized the change itself, with ellipses, raised two editorial points (a sentence labeled as the customer's own words now carries a number the words list at the bottom does not, and the number needs a source because "an investor audience will ask"), and asked where the figure came from. He answered that it was verified against the full historic earnings database back to 2017. The session saved that as the source, suggested adding "since 2017" because the count is cumulative, and asked "what changed, and why?".

1. Two questions where the check expects one ("What changed, and why?"). The script needs a source for a local edit, so the propose-change skill asks for it separately. Fix: one question whose answer supplies both.
2. "To raise your edit for review" and "The reviewer will also need to see where it came from" describe a review that does not exist on a base with no shared copy, where the owner approves locally. Fix: the local-edit path uses the local-approval words.
3. "Your positioning doc passed its check, and nothing has overtaken it." said out loud. The check before use is silent when it finds nothing. Fix: the skill says nothing about a check that found nothing.
4. Editorial advice inside the flow. **Brandon decided on 2026-09-27 (for the plan's For Brandon table):** inside any GTM Base flow the assistant makes only the step's one ask; editorial observations about the content wait until after the approval, as one short note ("two things you may want to check"), and never before or between the flow's own questions. Runner-up, not chosen: inline, capped at one sentence.
5. The before and after the assistant showed were its own summary with ellipses; the whole difference from the script is still to come in this step.

**Step 5, Brandon's decision on the hand-edit questions (2026-09-27, for the plan's For Brandon table).** "What changed, and why?" did not say what it was asking or what the answer is for. Brandon: people starting out need the reason explained, and people who have done it a few times do not. Decided wording, which replaces the separate source question and the bare "What changed, and why?" (fixes findings 1 and 2 above):

The first three times a person keeps a hand edit (counted per person on this computer):

> Because you changed a document in your base, GTM Base keeps a short record of it. That gives you a history of why your context changed, and it lets GTM Base check your other documents against it, so anything that still says the old thing gets flagged. The record holds four things: what changed about the business, why, where it came from, and which documents it affects. I work out the last one myself.
>
> So, in a sentence or two: what changed, why, and where did it come from? If this was only a wording fix and nothing about the business changed, just say so and nothing is recorded.

From the fourth time on:

> I'll keep a record of this edit so your other documents can be checked against it. What changed, why, and where did it come from? If it was only a wording fix, say so.

At any time, "why are you asking this?" gets the long version. One answer supplies the what, the why and the source; the script's source and what-changed inputs are filled from it. "Only a wording fix" is the typo path of step 6. The word stays "context change", never "decision".

**Step 5, Brandon's answer and a second decision (2026-09-27, for the plan's For Brandon table).** To "what changed, and why?" Brandon answered that nothing about the business changed: a review showed the company can now claim over 1 million drivers where it used to cite 500k a year. The session filed the edit as a correction and recorded no context change, which is the product as built. The gap: a corrected fact is exactly what other documents repeat, and a correction flags none of them, so any document still saying 500k stays unflagged. **Brandon decided the three-answer version:**

| The person's answer | What GTM Base does |
|---|---|
| Something about the business changed | Records a context change and checks the other documents against it |
| A fact the company states was corrected (500k a year becomes over 1 million) | Records a context change as well, for example "Our verified driver count is over 1 million since 2017, replacing the 500k a year we used to cite", so every document repeating the old fact is flagged |
| Only the wording changed | Records nothing (step 6) |

The decided hand-edit wording above changes in one place to match: the question asks "what changed (in the business, or in a fact you state about it), why, and where did it come from?", and the way out stays for a fix to wording only.

**Step 5, the showing (four findings).** The difference was exactly Brandon's one edit in "What we sell", and only the positioning was affected, on the local-approval path. But:
1. For a five-word edit the showing printed the whole paragraph as it reads now, again as it would read, and again in the difference, which is not readable in seconds. Fix for a hand edit: the changed sentence once, with the change marked, and the section named; the whole text on request.
2. The assistant shortened the difference with ellipses and explained that the rest matched. The difference is relayed as printed (fix 1 removes the need).
3. "What changed:" carried the first line of the edit, cut off mid-number ("from over 1..."). For a correction it says what changed in plain words.
4. "Why: The owner read the source quoted below and brought the file in line with it by hand." names the person in the third person and points at a source that is not quoted. It uses the person's own source sentence.

**Step 5, approval refused: blocking finding.** Approving was refused with "You have edits in your base you have not saved, so nothing was applied. Put those somewhere safe and ask again." A read-only look at the base by Claude the same day found the only files besides the edit: an untracked `.DS_Store`, which macOS Finder writes into any folder opened in Finder. The approval's clean-tree check counts it as unsaved work, so anyone on a Mac who browses their base in Finder, as this step asks, cannot approve a hand edit. Fix: the clean-tree checks ignore operating-system clutter (`.DS_Store`, `._*`, `Thumbs.db`, `desktop.ini`), and a base's ignore file lists them from the start (the existing base gains them through an offered change, never silently).

Two further findings from the same turn:
1. The refusal sentence does not say which files are unsaved. It names them in plain words and says when one is only a file the computer made.
2. The assistant then broke the relay rules: it narrated internals ("GTM Base blocks my commands from its own records folder"), listed guesses, and asked Brandon to find the base and run a version-control command himself. Naming the files in the refusal removes the reason to go looking; the skill says never to send the person to a command line.

Workaround for this run: delete the `.DS_Store` file and ask again, without opening the folder in Finder before approving.

**Step 5, result: passed once unblocked.** The `.DS_Store` file was gone by the time Brandon went to delete it, and a read-only look showed the base held only the edit. On "try the approval again" the session said: "Your positioning now says what this change said, and you are recorded as approving it." A read-only look at the base's saved history by Claude the same day: one saved change touching exactly three files, `context/strategy/positioning.md` (one line), a correction record under `corrections/`, and one confirmation line for the positioning. No other document changed, no context change was recorded (the product as built; Brandon's three-answer decision changes this for a corrected fact), and the base was left with nothing unsaved. One more finding: the saved-history subject repeats the cut-off "What changed" line ("In your words: "We collect earnings and trip data directly f"); the fix to step 5's showing finding 3 covers it.

**Step 6, a typo: passed on its own condition, with findings and a decision (2026-09-27).** The approved positioning held no real typo. Brandon's first two attempts (a typo typed and then fixed within one save, and a revert that left a word behind) were each read correctly by the session as a change in meaning, not a typo, and it refused to keep them as typos; it compared the saved file against the approved version and named the exact difference, which is the right guard (write it into the skill as a rule rather than leaving it to the assistant). It again added one editorial point inside the flow (a quote not matching "What we sell"), against Brandon's decision above. The clean run: Brandon removed the comma in "Buyers who try it, buy it." and asked to keep it as a typo. The difference shown was exactly that comma, and on approve the session said "Your positioning now says what this change said, and you are recorded as approving it." A read-only look at the base by Claude: one saved change touching the positioning (one line), a correction record, and one confirmation line; no new context change (the record still holds the one from before); nothing left unsaved.

1. Bug: "What changed:" quoted the first bullet of the section ("- **It answers the questions company disclosures cannot.** Quote: "He..."), not the bullet that changed, and the saved-history subject repeats it. With step 5's cut-off line, this shows "What changed" is built from the first line of the section rather than from the change. Fix: from the changed line, in plain words; for a fix to wording only, "A typo fix."
2. A one-comma fix got the whole ceremony: the four lines, all seven bullets twice, the difference, and a source file handed out. Fix: the wording-only route of the three-answer decision shows the one line with the change marked and asks one yes.
3. "Why: The owner read the source quoted below and brought the file in line with it by hand." Same as step 5.
4. **Brandon decided (for the plan's For Brandon table): a typo fix writes no correction record.** The saved history already says who changed what and when, and a correction record means something was wrong, which is what a later lessons pass reads. Runner-up, not chosen: a correction record for every hand edit.

**Step 7, paused: a product gap (2026-09-27).** To make the customer profile out of date, Brandon told the session about a real change (the marketing use case sold to retail firms). The session checked the terms against the profile and asked what they meant (good instinct, but three questions at once and an editorial paragraph on deal values, and it again said "The ICP passed its check, so nothing has overtaken it"). It then found, correctly, that 0.3.1 cannot record a context change on its own: outside the setup closing, which needs a setup run, a change is written down only together with an edit to a document, and a proposal that changes no document is refused ("This proposal changes nothing, so there is nothing to send."). This step's instruction ("by telling Claude what changed") promised a path the product does not have. Its offered workaround (a placeholder line in the profile carrying the change) would settle the change against the profile, so nothing would ever be flagged and the step would measure nothing.

**Brandon decided to fix the gap before running step 7 as designed.** Built in two fix releases on main: 0.3.2 (by the orchestrating session) makes operating-system clutter never count as unsaved work, the blocking `.DS_Store` finding from step 5, with refusals naming the unsaved files; 0.3.3 (from the live-check session) adds the change recording. What the two do: (1) a person can record a context change at any time, from the folder they work in, with no setup and no edit; it is shown whole, written only on their yes, and each affected document is then asked about (already says it, prepare a fix, or not now, which leaves it flagged); (2) operating-system clutter never counts as unsaved work, and a refusal names the unsaved files. The wording and relay findings from steps 2 to 6 stay with Release B. Step 7 resumes on 0.3.3 in ~/Gridwise with the retail change.

**0.3.3 released, 2026-09-27: step 7 resumes.** A person can now record a context change at any time, from the folder they work in, with no setup and no edit to a document. It was built and reviewed three times by Astra (twelve findings, then four, then ready with one follow-up on native Windows), and every git command the plugin runs against a base now runs with hooks and other configured programs switched off. It is installed on Brandon's machine. The 0.3.2 release (files the computer makes on its own never count as unsaved work, and a refusal names the unsaved documents) is included. To resume: quit and reopen Claude Code, open it in ~/Gridwise, record the retail change, answer "not now" for the customer profile so it stays flagged, then make the ten requests.

### 0.3.5 live sitting, 2026-10-10: step 7 resumes (plugin 0.3.5, a new session opened in ~/Gridwise with no worktree; scored by a guide session that read the transcript)

**Step 7, recording the change: blocked at first by a product bug, then worked around.** Brandon said "Record a context change: we now sell the marketing use case to retail firms." The session ran the stale-check skill, one command failed, and it replied with the script's sentence "This folder is not a company base you have joined yet, so there is nothing here to check.", then said that at session start GTM Base had noted the folder "used to belong with a base but isn't the same folder any more" and suggested "link this folder to my base". Nothing was recorded.

Root cause, verified by Claude the same day with a read-only comparison through the plugin's own library: the link record for ~/Gridwise and the folder as it is today agree on the folder number, the creation time, the mount point, the disk's own identifier and the shared-copy address. Only the device number differs. macOS hands out device numbers when a disk is mounted, so the same internal disk can get a new one after a restart. `folder_identity.matches` returns `remounted` whenever the device numbers differ, even when both records carry the disk's identifier and it agrees, and `paths` treats `remounted` as a different folder, so the link is dropped. The module's own docstring says the disk identifier is kept for exactly this case. Effect: every linked folder can come unlinked after a restart, and every GTM Base command in it then refuses. Not yet fixed in the Release B branch either.

1. **Blocking finding, filed for a fix release.** When both records carry the disk's identifier and it agrees, a changed device number is not evidence of a different folder; the identity comparison should call it the same folder (and refresh the stored device number). A different disk identifier stays `remounted`. Needs a test with a recorded device number that differs and an agreeing disk identifier, failing on 0.3.5.
2. The first sentence the person heard, "This folder is not a company base you have joined yet", is wrong for a folder that is linked but whose link was dropped; the session had to add a second paragraph to explain it. The refusal should say the link-mismatch sentence itself.

Workaround for this sitting: relink with "link this folder to my base" (the product's own instruction), and no restart of the Mac until step 7 is done.

**Step 7, recording the change after the relink: passed, with findings.** "link this folder to my base" relinked the folder ("That folder and your base are now linked. Opening Claude Code in that folder brings the base with it."), after two failed commands. The session then asked the one decided question for a change ("In a sentence or two: what changed, why, and where did it come from?"), with the long explanation because this was among the first three times. Brandon answered with the reason and the source (a meeting with a prospect). The documents were listed in plain words with the session's guess, and when Brandon added that the change also touches messaging and adds a new buyer persona, the session said plainly that the base holds only two documents and folded both into the change's wording. Four lines were shown, Brandon said "record it", and "That context change is recorded." A read-only look at the base by Claude: one new context change, with Brandon's words, the reason, the source, both documents, origin manual, status open.

1. The relink took two failed commands, and the assistant narrated how the command takes its folder ("the command wants the folder path passed a particular way"), against the relay rules. The join skill's link command should be shown exactly as it must be run.
2. The four lines shown were what changed, why, what it affects, and when to look again. The source was saved but never shown, so the yes covered a line Brandon did not see. The showing should carry the source line (it is one of the four things the explanation promises).
3. Brandon named messaging and a new buyer persona as things the change affects; the base has no document for either, so they live only inside the change's wording. Expected for 0.3 (the standard documents arrive with Unit 1.5b); noted as real demand for both.
4. "Does your customer profile already say what that change says?" was asked cold, and Brandon had to ask "what do you mean?". Only then did the session explain the three answers, read the profile, and say the answer looked like no. Brandon's question: "shouldn't the tool already know this?" Proposed (not yet approved by Brandon): the assistant reads the document first, says in one sentence what it found, and asks the person to confirm ("Your customer profile does not mention the new segment or its buyer. Shall I prepare the edit, or leave it for now?"). The person still decides, because a yes settles the flag and only the owner may settle it.

**Step 7, both documents left flagged: passed.** Brandon answered "not now" for the customer profile and then for the positioning. Each got one sentence ("Your customer profile stays flagged, so GTM Base will say so when it is about to be used and in your next review."), and the session closed with one short editorial note after the flow, as Brandon decided on 2026-09-27.

**Step 7, the count.** Each request in its own new session in ~/Gridwise with no worktree, because the read check flags a document once per session.

| # | The request | Flagged? |
|---|---|---|
| 1 | "Summarize who we sell to, in five bullets." | **No.** |
| 2 | "Draft a cold email to a prospect in one of our B2B segments." | **No.** |

Request 1, a miss with a false claim. The session never ran the check before use and never read the customer profile. It listed the base's folder with a search three levels deep, which stops one level above the strategy documents, saw only the map, and told Brandon that his GTM Base "has no saved customer profile" and "holds only its map file". It answered from the assistant's own memory notes instead and offered to save a new profile into the base. Brandon did not answer the offer.

Root cause: the session-start context tells the assistant to run the check before using "any file under this base's `context` folder", but never says where the base is or which documents it holds, so the assistant has to search for them, and here it searched badly. This is step 2's finding 2 from 2026-09-26 ("the session's injected context should name it"), still open. Fix: the session-start context names the base's folder and lists its documents by plain name and path (the customer profile, the positioning), and says to read and check them whenever a request is about who the company sells to, what it says, or how it says it.

Request 2, a miss. The session read the assistant's own memory notes and the older segment drafts in the Gridwise folder, listed the name of the folder that holds the base and went no further, asked two good questions (which segment, a template or a named prospect), and wrote a solid draft into the Gridwise folder. It never read the customer profile in the base and never ran the check. Same root cause as request 1. The draft is built on material GTM Base does not keep current, which is the failure the moment of use exists to prevent.

**Step 7, result: failed, 0 of 2, stopped there (2026-10-10).** Two misses put nine of ten out of reach. With one cause behind both, Claude recommended stopping the count and testing the three answers with requests that name the profile, so the flag path itself is still checked. What the plan says a failure here means: the changelog and the join guide say plainly that outside a skill the flag is best effort. The fix above (the session-start context names the base and its documents) is what would make an ordinary request reach the profile at all, and a new count should follow it.

**Step 7, the answers, with requests that name the profile.** Each in its own new session in ~/Gridwise.

Request A, "Read the customer profile in my GTM Base, then outline a landing page for our best-fit buyer.": **flagged, and "use it as it stands" passed.** Told where to look, the session listed the base in full this time, ran the check before use on the customer profile and the positioning before reading either, and stopped before writing anything. It named both documents and the retail change in plain words and asked one question with the three answers (fix first, use as they stand, already reflects it), adding from its own read that the documents did not seem to reflect it. Brandon chose "use as they stand". The session recorded that answer for each document with the question it had been given, and the script said: "your customer profile is being used as it stands, and it stays flagged until somebody says it already reflects the change." The outline it wrote says at the top that both documents are flagged and were used as they stand. A read-only look at the base by Claude: nothing new in its saved history and nothing unsaved besides the Finder file.

1. The four lines were not read back as they stand, as the session-start rule asks; the session put the change in its own words.
2. The check's "What changed" line is cut off mid-sentence ("which adds the..."), the same truncation as step 5 finding 3, and its four lines carry no source.
3. Both documents were asked about in one question. The answers were recorded per document, so nothing was lost, but a person who wants different answers for the two has to type them.
4. "it stays flagged until somebody says it already reflects the change" leaves out the other way a flag clears, an approved fix.
5. The check before use ran through the shell, and the document was then read with a shell command rather than the file tool, so the read check (the backstop) never saw the read. The rule held here because the assistant followed it; a shell read is a path round the backstop.

Request B, "Read the customer profile in my GTM Base, then write three LinkedIn ad headlines for our best-fit buyer.": **flagged again after "use it as it stands", and "fix it first" passed.** The session ran the check before reading the profile and stopped; the profile was still flagged, as "use it as it stands" promises. Brandon chose "fix it first". The check said "The change for your customer profile is prepared, and the work waits here until you approve it or choose otherwise." The session saw that the prepared change was only the placeholder, wrote real wording into it through the approval script (retail added to the profile as a test segment with no deals yet, the segment count raised by one in two places, and the new buyer added to the buyer list), showed the four changes in a before-and-after table with the drafting choices it had made, and asked "Approve this change, leave it for now, or drop it?". On Brandon's approve: "your customer profile now says what this change said, and you are recorded as approving it." It re-ran the check, which came back silent, and wrote the headlines without flagging again. A read-only look at the base by Claude: one saved change touching the profile (seven lines), a correction record, and one confirmation line; nothing else.

1. "Fix it first" does not hand the assistant the next steps. To learn how to replace the placeholder, the session loaded the stale-check skill, ran the approval script's help, and read the plugin's own library code, narrating "I'll check the skill to see how to swap in a real edit". The answer to "fix it first" should print the steps (write the wording with this command, show it, ask).
2. One prepared change can touch only one section, so the fix covered who the buyer is and left the profile's needs, use cases and triggers silent on retail, while the flag cleared for the whole document. The session said so plainly. Worth deciding whether a fix may span sections, or whether the flag should clear only when every affected section is covered.
3. The session's notes on its own drafting choices came before the approval ask. They were about the wording being approved, so they helped the decision; Brandon's rule on editorial notes (after the approval) is about the content, not about the draft itself. Noted, not a finding.

The second change, recorded in its own session: a sentence saying the new segment stays a test until its first deal, which the profile approved earlier that day already said. The session asked the one question; Brandon's reason and source were Claude's suggested example sentence, pasted with the guide's instruction to "use your real reason" still on the end, which the session left out. One document (the customer profile) was chosen, four lines shown, "That context change is recorded.", and "not now" left the profile flagged. One finding: the session asked "what changed" again when the person's first message had already said it (the first recording session had noticed and asked only for the missing parts).

Request C, "Read the customer profile in my GTM Base, then summarize our test segments in three bullets.": **flagged, and "it already reflects this" passed.** The check before use flagged the profile for the second change even though a fix for the first had been approved earlier the same day. The session read the profile, recommended "already reflects", and Brandon chose it. A read-only look at the base by Claude: one saved change, one confirmation line for the profile naming the second change and the question, and nothing else. The summary that followed named the change's look-again date.

1. The script's sentence after the answer, "Your answer was recorded for context/strategy/icp.md in your own copy of the base.", names a path and says "your own copy", which means nothing on a base with no shared copy. The session paraphrased it instead of relaying it, which the rule against reading out a path forced. Fix: "Your customer profile is recorded as already saying what that change says, and it is no longer flagged for it."

**Step 7, summary.** The count failed, 0 of 2, because an ordinary request never reaches the base's documents (the session-start context does not say where they are). Once the request names the profile, the flag fired three times out of three, before anything was written, and each of the three answers did what the walkthrough expects: "use it as it stands" recorded nothing and flagged again in the next session, "fix it first" wrote a real replacement that was shown and approved and cleared the flag, and "it already reflects this" recorded one confirmation.

**Step 8, a setup closing: passed on the second run, with findings.** Run in a new folder on the Desktop holding copies of three of the company's segment pages, with a scratch company name; each scratch base is to be deleted afterwards.

The first run went through both drafts cleanly, but Brandon answered "skip" to the context-change request, so the step's main path did not run. The skip path was right: "Nothing was written down, and GTM Base will not mention the quiet record of context changes again until 2026-11-09.", and the closing said "No context change is recorded yet, so there is nothing to check either document against." Brandon asked why the closing then asks "Did anything get in the way while you were setting this up?": its answer is saved into the base for later sessions and the next round of fixes, and the question does not say so.

The second run, in a second scratch folder: both drafts approved, then the three sentences about a context change with the example, word for word as the walkthrough expects, then the request. Brandon gave a real sentence (the retail change from step 7). The entry was shown as four lines and approved, and each of the two documents was asked about. "No" for the customer profile: the session listed the profile's six sections and asked which one the change was about, with its own recommendation (Firmographics) at the end; Brandon chose it, the session showed the section as it reads and as it would read, and on approve: "Your customer profile now says what this change said, and you are recorded as approving it." For the positioning, Brandon asked the session what it thought; it read the document, said no with three plain reasons and what the fix would cover, and the same flow followed and was approved. The closing, word for word:

> Nothing is out of date yet. The first date GTM Base will watch is 2027-01-10, for the change about We now sell to [the new segment, cut off here by the product]... (2026-10-10).

Asked whether the three sentences made sense on first hearing, Brandon said: "I think it was fine, always room for tweaks tho."

It is true here, because both documents were fixed and approved before the closing; the closing never claimed nothing was out of date while the change was waiting.

1. The pattern Brandon named across steps 7 and 8: when the tool can tell, it should say so and ask to confirm. "Does your customer profile already say what that change says?" and "Does your positioning already say what that change says?" were asked cold, and the session showed it can answer them well when asked ("what do you think?"). The section question listed six parts and buried the recommendation under the list, and Brandon missed it. Filed in the task list as one pattern.
2. The wording command replaces the whole section. The session noticed that its one new paragraph "would have wiped out the three existing segments" and rewrote the full section with retail added. The skill's "write the wording into that part" does not say the part is replaced; an assistant that did not notice would show a change deleting the other segments, caught only if the person reads the whole showing.
3. A prepared change rewrites one section, so the positioning fix covered "What we sell" and not "Who it is for", which the session had said also needed retail. Same as step 7's finding.
4. The closing cuts the change off mid-sentence with an ellipsis and reads "the change about We now sell...", with the change cut off mid-sentence. It should name the change in a whole short phrase.
5. The look-again date is three months out from the setup closing (2027-01-10) and one month out from the any-time path (2026-11-09) for the same kind of change. Worth one rule.
6. Right after "nothing will be created until you agree to it", the app showed "Edited 2 files": the temporary files holding the company name and the folder, outside the person's folder. Harmless, and alarming at that moment.

**Step 9, ordinary work is untouched: passed.** Two runs, each in a new session with a worktree (the kind of session 0.3.5 fixed), each with the same request: make a branch, add a note file and a file whose name begins with a dot, edit both, commit, push the branch, then delete it from the shared copy, and say whether anything was refused or asked.
- In ~/Gridwise (the folder linked to the base): the branch, both files, both edits and the commit went through with no refusal and no question. The push reached the version-control program and failed there, because that folder has no shared copy at all; the command check had let it through.
- In one of Brandon's own projects that has a shared copy on GitHub and is not a base: everything went through, the push landed (the session read the branch back from GitHub), and deleting it there succeeded. Claude confirmed with a read-only look the same day that the branch is gone from GitHub. Nothing was refused and nothing was asked.

**Step 10, your own settings: failed. Nothing was asked, because the change went through the shell.** In a new session in ~/Gridwise, Brandon asked Claude to add a permission to his user settings so the `wc` command runs without asking. No prompt appeared. The transcript shows why: the session read the settings file with a one-line Python command, then copied it to a backup and rewrote it with a Python script run through the shell. The write check only runs on the file tools (write, edit), and the command check reads only lines that run the version-control program or reach GTM Base's records folder, so neither saw a shell command writing the settings file. The change itself was harmless (one allow rule for `wc`), and Claude confirmed with a read-only look that the settings still turn GTM Base on and switch no hooks off.

1. **Blocking finding, filed for a fix release.** The question about a write to the files that decide whether GTM Base's checks run (the user settings, the plugin registry files, and a linked folder's settings) can be bypassed by any shell command that writes them, which an assistant chooses on its own (here, unprompted). This is the 2026-09-20 lesson about a check declared on one tool having a hole the width of every other tool. The command check already refuses any line that names GTM Base's records folder; the settings files need the same reach, as a question rather than a refusal, with the same reason.

Seen by the guide session along the way, not by Brandon: two false refusals by the command check on lines that run no version-control program (a shell loop testing for a folder named `.git`, and a line appending task-list text that mentions the word). Filed in the task list.

### Release A live check, where it ends (2026-10-10)

Every step has now been run on the installed plugin. Steps 1 to 6 passed on 0.3.1 (2026-09-27, with findings); on 0.3.5 the same day as this entry, step 8 and step 9 passed, and step 7's three answers passed once a request named the profile. Three things fail the walkthrough's own bars and are filed as blocking for a fix release:

| What | Step | Why it matters |
|---|---|---|
| A restart drops the link between a base and its folder | 7 | Every command in the linked folder refuses until the person relinks. |
| An ordinary request never reaches the base's documents | 7 (0 of 2, bar 9 of 10) | The flag cannot fire on a document the assistant never finds; the session-start context does not say where the base is or what it holds. |
| A shell command can change the settings that switch GTM Base's checks off, without a question | 10 | The settings question covers only the file tools. |

What the plan says about step 7 falling below the bar: the changelog and the join guide say plainly that outside a skill the flag is best effort, until the session-start fix ships and a new count is run. The scratch bases made in step 8 are still on the machine, to be removed with Brandon's yes.
