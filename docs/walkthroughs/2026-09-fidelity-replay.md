---
title: "The fidelity replay: the frozen bar"
type: walkthrough
status: frozen bar recorded, no case run yet
date: 2026-09-19
plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md
unit_that_froze_the_bar: "Unit 1.1: Contract amendments to the documents"
unit_that_records_results: "Unit 1.9: The fidelity replay, as the release gate"
---

# The fidelity replay: the frozen bar

This file holds the bar, and only the bar. It is written before any behavior
unit of this phase is built, so that the build cannot set the standard it is
later judged against. That was the point of the finding in the Astra review of
2026-09-19 that said the gate had two ways to pass without proving anything.

**There are no results in this file yet, and none are to be added by anyone but
the unit that runs the replay.** If a case is not run, the record says so, names
the case, and the gate is incomplete. Incomplete is never pass. The gate is
never decided on whichever cases happened to run.

## Who scores

Brandon scores every case. The person or agent who built the behavior being
replayed does not score, ever, and does not help score. This is not a comment on
anyone's care; it is that a builder scoring their own output is not evidence.

## The pass bar, stated before anything is run

A case passes only when all five of these hold on the uncorrected output, before
anyone has fixed anything:

1. Every segment the material names appears in the output.
2. No figure is altered. A figure keeps its units.
3. No customer named as evidence is dropped or credited to the wrong segment.
   Deal stages and values are pipeline data, so an output need not carry them,
   but any it carries must match.
4. Every claim is attributable to the source and the version it came from.
5. Nothing is invented. A choice the material leaves open is marked as open
   rather than settled by the draft.

**Rule 3 was amended by Brandon on 2026-09-27, before any case ran.** It used to
read "No named deal is dropped." Context documents hold definitions and never
tracking: customers, deals, and pipeline live in the CRM, and a named customer
belongs in a context document only as evidence. The old rule would have rewarded
a draft for copying pipeline data into the base. The amendment is the owner's,
not the builder's, which is the distinction the freeze exists to keep. In case
two, a customer counts as one the output must keep only when the material case
two actually reads names it, since the twelve pages it is scored against are held
out of that material.

The output is scored against the whole original corpus, including material that
fell past the point where the draft stopped reading. What the cap dropped is
exactly what this gate exists to find, so scoring only against what went in
would score the wrong thing.

A fail on any of the five builds the summarize-first stage inside this release,
as a step between reading and drafting. Building it is not passing. The same
three cases must be replayed and must pass afterwards.

## The answer key

The answer key for each case is the list of segments, named deals, figures with
their units, source versions, and unresolved choices that a correct output has
to keep. It is client material, and this repository is public, so **the answer
key is not written here and is never to be written here.**

The answer key is kept outside this repository, at a path Brandon chooses. The default, unless he names another, is the same private folder as the corpora: `~/GTM Bases/Gridwise/fidelity-replay/`.

The answer key is kept at `~/GTM Bases/Gridwise/fidelity-replay/`, the folder Brandon named on 2026-09-27. Claude drafts it there from the frozen files, Brandon corrects it, and it is frozen with its own sha256 recorded in that folder before any case runs. Case two is scored against the facts of the same twelve finished pages as case one, so one key serves both; case three has a key of its own from its seventeen files. No key content is written in this repository. Until the key is frozen, no case can be scored.

## The corpora

The material is Gridwise's and lives outside this repository. None of its text or its figures is copied in here, and neither are its file names, because the names alone carry the company's segment list and the names of people and companies who wrote in, and this repository is public.

The frozen lists, one path and one sha256 content hash per file, are kept on Brandon's machine at `~/GTM Bases/Gridwise/fidelity-replay/corpora.md`, beside the base and outside it. That file was frozen on 2026-09-19 and its own sha256 is `81a10216c9dc9e7c7f1811f44a1a0db580d45b61f6da8bea083a072a421969a6`. A different hash on the day of a replay means the lists were edited after the freeze, and the record says so.

What that file holds, without the names:

| Case | What it is | Frozen? |
|---|---|---|
| One | The twelve finished segment pages the third real run read: eleven segments in twelve files, two of which are two versions of one segment. Taken from the `sources` field the plugin wrote into the real base | Yes, twelve files |
| Two | A company with several segments and no finished pages, so every segment is drafted. Recommended: the same Gridwise material with the twelve pages held out of consent, scored against those pages | **Material decided, list not yet frozen.** Brandon decided on 2026-09-27: the same Gridwise folder with the twelve pages held out of consent. The list is frozen at the start of the case two run: setup surveys that folder as the product really would, the twelve pages are dropped from consent, and the remaining list is written into the private folder with one sha256 per file before anything is drafted. Until then the gate is incomplete |
| Three | Everything the positioning draft read on the third run: the twelve files of case one plus five more, replayed with the amount one request may read lowered | Files yes, seventeen. The private list both says the positioning draft read only the final version of the segment that has two, and lists both versions among the seventeen; Brandon decided on 2026-09-27 to keep all seventeen as frozen, so the release's own handling of an older version is tested along the way. **The lowered amount is not set yet.** Proposed: 40,000 characters per request, about half of the seventeen files, where the shipped limit is 240,000 and all seventeen fit. It is set before the case runs and written in both the private file and the result |

Case one is replayed against the shipped plugin as it stands today, in a session Brandon starts, as soon as the answer key exists, so a failure is known before the drafting work is built on top of it.

## What goes in this file afterwards

The unit that runs the replay adds, for each case: what was read, what survived,
what did not, what a reviewer had to correct, the result against each of the
five points of the bar, and the decision. Real results only, from real runs, and
no estimate anywhere in it. The number of tests passing on the day the decision
is recorded goes in with the decision.
