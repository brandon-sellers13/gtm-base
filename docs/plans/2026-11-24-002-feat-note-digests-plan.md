---
title: "Digests of the notes, so every draft knows what every note says"
type: feat
status: approved by Brandon on 2026-11-24 with the recommended answers to all three decisions
date: 2026-11-24
parent: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md (Unit 1.9b, the summarize-first stage)
unit: "Unit 1.9c"
---

# Digests of the notes, so every draft knows what every note says

## Why

The summarize-first stage reads every file into checked notes, and every draft is written from those notes. The case three rehearsal of 2026-11-24 (counts only, at the frozen limit of 40,000 characters) showed that the notes are larger than the material they come from: 76,176 characters of notes from 70,664 characters of files, because each note carries the file's own words. So the limit moved from reading to drafting. Both the customer profile and the positioning read 307 of the 516 notes, and 209 were left out from the end of the list, so three segments reached the draft with almost none of their notes. The preview said nothing about it.

What the drafts lose is limited to their own prose. Setup writes the evidence for each segment, what the material leaves open, and the footnotes from every note, whatever the draft read. But a positioning written without most of three segments' notes cannot say anything true about them, and case two is about ten times larger than one request before any notes are taken (70 files, 2,305,471 characters, at the shipped limit of 240,000), so its drafts would see roughly a tenth of their notes.

The fix is a digest: when the notes do not fit one draft, the largest groups of notes are condensed by a subagent into short lines, each citing the notes it rests on, and checked by setup before any draft reads them. Every customer note and every segment note reaches the draft as a short line setup writes itself, and every note the material leaves open is carried by a digest line, so the draft is never blind to a segment, a customer, or an open choice.

## What stays the same

- When every note fits one draft, nothing changes. Case one fits at the shipped limit, and its path is not touched.
- Drafts cite notes, as `[n12]`, never digest lines. The digest lines show the notes each one rests on, so the draft cites those.
- Review's citation checks, the support check, and the three sections setup writes all work on the notes themselves, unchanged. The support check still shows each draft line beside the material's own words from its cited notes, never beside the digest, so a digest that says more than its notes cannot carry that into a draft unseen.
- Context changes (step 8) still read their few files directly.

## How it works

### Which notes are digested

Setup groups the notes by segment, with the notes about the whole company as a group of their own. When all of them fit one draft, there is no digest. When they do not, setup digests the fewest groups it can, largest first, until what the draft reads fits. A group too large for one digest request is split into batches that each fit, the way the notes are packed now.

A segment's own draft (step 6c) reads its own group and the company group. If those fit, it reads them whole, even when the profile and the positioning read digests.

### What setup writes itself, and what the subagent writes

- **Customer and segment notes, written by setup.** Each becomes one short line: its number, its kind, its segment, the customer's name, its status, and any figure, without the quote. These are never condensed or left out, so every customer and every segment the material names reaches every draft that reads that group. The quotes are still in the evidence section setup writes.
- **Fact notes, condensed by a subagent.** The subagent is given one batch of a group's fact notes, with their words, and writes short lines in its own words, each citing the notes it rests on and carrying a status. A line may join several notes.

### The digest check

Each digest batch is checked before any draft reads it, line by line, never by what a line says:

1. Every note a line cites is a fact note in that batch.
2. Every fact note the material leaves open, proposes, or puts on hold is cited by at least one line. A settled fact may be folded into another line or left out, and setup counts how many were.
3. A line's status is the weakest status among its notes. A line that cites an open note is open.
4. Every figure in a line appears, with its unit, in the words of a note it cites.
5. No customer is named in a line unless a note it cites names that customer.
6. No line holds contact details.
7. Each line is no longer than 300 characters, and the whole digest fits the share of the request the plan gave its group.

A refused batch goes back to a subagent with the problem lines, as notes do now. After the third refusal, setup keeps the lines that held up, and for every open, proposed or on-hold note still not carried it adds that note's own words itself, shortened if it must be. Nothing open is ever lost to a loop limit.

### What the person is told

The preview says how the notes reach each draft, in plain sentences: every note in full; or every customer and segment, with the facts about named segments condensed, and how many settled facts were folded into others. If anything still had to be left out after the digest, the preview names the segments it came from. It is never silent about notes left out, which today it is.

## Units

Each unit's tests are written first and fail first. Client material never enters this repository; every test fixture is invented.

- **D1. The digest plan.** Grouping, the largest-first choice, each group's share of the request, batches that fit, a stable digest identifier, and a changed set of notes invalidating the digests. Command: `digest-plan`, which prints how many digest batches are needed, or none.
- **D2. The digest request.** The prompt (`references/prompts/digest.md`), which states every rule the check refuses by, and `digest-assemble`, which writes one batch's request and names the file for the answer.
- **D3. The digest check.** `digest-check` and `digest-status`, the seven rules above, three attempts, the fallback that carries every open note in the material's own words, and resume from where a session stopped.
- **D4. Drafts read the digests.** The request renders setup's short lines and the digest lines grouped by segment. The notes a draft may cite are exactly those its request shows. Review and the support check use that same set. The preview sentences, registered with the plain-language lint.
- **D5. The skill and the records.** A new step 5f in the join skill (digests run after the notes and before the previews, up to four subagents at once, and only when the plan says they are needed), the CHANGELOG entry for 0.5.0, the atlas figure, and plan Unit 1.9c.
- **D6. Verification.** The full suite, twice. One correctness review by a subagent, each finding fixed with a failing test first. No security review: nothing here involves tokens or another machine. Then the case three rehearsal again, counts only, with usage read before and after.

## What it costs to run

In case three at 40,000 characters, a digest of the largest groups should take about three to four more subagent runs than the rehearsal did, roughly three more points of the five-hour window (an estimate from the rehearsal's measurement). In case two it adds about one digest run for each 240,000 characters of fact notes, likely eight to twelve, on top of the notes themselves.

## Decisions for Brandon

1. **May a settled fact be folded away?** Recommended: yes, as long as every customer note, every segment note, and every open, proposed or on-hold note is carried. That is what lets a digest be shorter than its notes. The runner-up requires every note to be cited by some line, which is stronger but may not fit case two at all and would loop.
2. **Digest only the groups needed, largest first, or every group whenever the notes do not fit?** Recommended: only the groups needed, so as much as possible reaches the draft in the material's own words.
3. **The order of work.** Recommended: build this, rehearse case three again (counts only), then the scored run of all three cases. The runner-up is to score the three cases now on the current build, since the sections setup writes already carry every customer and open item, and build this only if the prose fails. That is cheaper if it passes, and costs a full scored run (about 17 to 32 weekly points, estimated) if it does not.

## Out of scope

- How large the evidence section grows for a base with thousands of notes. It is written by setup, not read by a draft, so it does not hit the limit, but its readability for case two is worth a look after the scored run.
- Anything about how the notes themselves are taken. The note request was corrected on 2026-11-24 to state every rule its check refuses by; nothing else changes there.
