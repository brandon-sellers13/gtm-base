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

