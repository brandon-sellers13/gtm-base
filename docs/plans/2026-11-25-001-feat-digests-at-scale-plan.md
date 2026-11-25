---
title: "Digests at scale: drafts that fit however large the material"
type: feat
status: approved by Brandon on 2026-11-25 with the recommended answers; built
date: 2026-11-25
parent: docs/plans/2026-11-24-002-feat-note-digests-plan.md (Unit 1.9c)
unit: "Unit 1.9d"
---

# Digests at scale: drafts that fit however large the material

## Why

The scored re-run of 2026-11-24 stopped case two after its notes. Case two is a company folder of seventy files, about ten times what one request holds. Its notes were all taken and checked (thirteen batches, none at the loop limit), but the digests of Unit 1.9c cannot make them fit one draft, for three reasons the counts show:

1. **Every customer note reaches the draft as a line of its own.** Case two has several thousand, and those lines alone are larger than a whole request before any fact.
2. **Every segment note does too**, and case two's notes name about four times as many segment groups as the person settled, because the material mentions many groupings in passing.
3. **Every draft waits for every digest.** A segment's own draft, which reads only its own notes and the company's, waits for digests of groups it never reads.

Case one fits without any of this, and case three fits with the digests as built. So this is a change for large material, and it must leave both as they are.

## The key observation

A draft never names a customer: review refuses any line that does, and setup writes the evidence for each segment itself, from every customer note, with the material's own words and a footnote. Setup also writes what the material leaves open from every open note. So the drafted prose does not need one line per customer to keep a customer from being lost, and the sections setup writes already keep every customer and every open item whatever the prose reads. What the prose needs from a large group is that the segment exists, what the material says about it, and what it leaves open.

## What changes

1. **Customers, as a count.** In a condensed group, the customer notes reach the draft as one line setup writes: how many customers the material names as evidence for that segment, and that setup lists them in the document. The draft cannot cite them, and never could name them. When the notes fit, nothing changes.
2. **Segment notes, a few kept.** In a condensed group, the first three segment notes keep their words, so the draft knows what the material calls the segment; the rest are condensed with the facts.
3. **Open notes, joined.** Every open, proposed or on-hold note is still carried by a digest line, but one line may carry many notes that say the same kind of thing, and the room counts only the words, never the note numbers. That already holds; this unit relies on it.
4. **Rooms planned honestly.** The plan works out each digest's room after the lines setup writes, and no longer gives every digest a fixed floor when there is no room left. When even the lines setup writes do not fit, the plan says so before anything is condensed, and the preview names it.
5. **Each draft waits only for what it reads.** A segment's draft reads its own notes and the company's, and waits only for the digests of the condensed groups among them, and for none when they fit as they are. The profile and the positioning wait for theirs.

   As built, there is one plan of digests shared by every draft, sized for the drafts that read every group, rather than a plan for each view. A plan for each view would condense the company's notes once for every segment, and the shared rooms are smaller than any one view needs, so every draft still fits.

## What stays the same

- When every note fits, nothing changes (case one).
- The evidence for each segment, what the material leaves open, and the footnotes are still written by setup from every note.
- Drafts still cite notes. Review and the support check still read exactly the notes the request showed.
- The notes themselves, their check, and how they are batched do not change, so case two's thirteen checked batches stay valid and the scored run resumes from them, with no notes taken again.

## Units

Each with tests that fail first.

- **E1. Customers as a count, segment notes capped,** in what a condensed group shows a draft and in what the plan counts.
- **E2. Honest rooms:** no floor when there is no room, and a plan that says up front when the lines setup writes do not fit.
- **E3. Views:** the plan and the wait per draft, so a segment's draft waits only on its own view.
- **E4. The skill and the records:** step 5f, the preview sentences, the CHANGELOG, plan Unit 1.9d.
- **E5. Verification:** the full suite twice; one correctness review; then, on case two's kept notes and at no cost, the plan's own counts (how many digests, each one's room, and whether the lines setup writes fit), before any subagent runs. Then the scored run resumes from case two's digests.

## Decisions for Brandon

1. **Customers in a condensed group reach the draft as a count.** Recommended. The runner-up lists the customers' names per segment, without note numbers, which tells the draft more but in case two is still tens of thousands of characters.
2. **Keep three segment notes per condensed group in their own words.** Recommended. The runner-up keeps one.
3. **After the build, resume case two from its kept notes and score all three cases together,** rather than scoring cases one and three now. Recommended only if you would rather score once; scoring cases one and three now costs nothing extra and their evidence is ready.

## What it should cost

Resuming case two costs the digests (fewer than the thirty-eight planned before, because small groups stay whole) and thirteen drafts with their support checks, which is most of the remaining estimate of 2026-11-24: roughly 10 to 20 weekly points. The notes, already paid for, are not taken again.
