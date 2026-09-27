---
title: "Release A: the live check"
type: walkthrough
status: waiting for Brandon
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
This is the trial the plan sets a bar for. The bar is ten real prompts with the flag firing on at least nine, unless Brandon sets another bar before starting. Write the bar here before step 7 begins: [BAR TK — Brandon].

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
