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
3. No named deal is dropped.
4. Every claim is attributable to the source and the version it came from.
5. Nothing is invented. A choice the material leaves open is marked as open
   rather than settled by the draft.

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

**[TO FREEZE: the path where the answer key is kept. Brandon names one folder
outside this repository, the answer key for each case below is written there,
and that path is recorded here as a plain sentence, with no key content. Until
this is done, no case can be scored, because there is nothing to score
against.]**

## The corpora

The material is Gridwise's and lives outside this repository. None of its text or its figures is copied in here, and neither are its file names, because the names alone carry the company's segment list and the names of people and companies who wrote in, and this repository is public.

The frozen lists, one path and one sha256 content hash per file, are kept on Brandon's machine at `~/GTM Bases/Gridwise/fidelity-replay/corpora.md`, beside the base and outside it. That file was frozen on 2026-09-19 and its own sha256 is `81a10216c9dc9e7c7f1811f44a1a0db580d45b61f6da8bea083a072a421969a6`. A different hash on the day of a replay means the lists were edited after the freeze, and the record says so.

What that file holds, without the names:

| Case | What it is | Frozen? |
|---|---|---|
| One | The twelve finished segment pages the third real run read: eleven segments in twelve files, two of which are two versions of one segment. Taken from the `sources` field the plugin wrote into the real base | Yes, twelve files |
| Two | A company with several segments and no finished pages, so every segment is drafted. Recommended: the same Gridwise material with the twelve pages held out of consent, scored against those pages | **No.** The full list the third run consented to lived in that run's working folder, which the plugin deletes when a run ends. Brandon either points setup at the same folder again so the list is frozen afresh, or supplies a second real company. Until then the gate is incomplete |
| Three | Everything the positioning draft read on the third run: the twelve files of case one plus five more, replayed with the amount one request may read lowered | Files yes, seventeen. **The lowered amount is not set yet.** It is set before the case runs and written in both the private file and the result |

Case one is replayed against the shipped plugin as it stands today, in a session Brandon starts, as soon as the answer key exists, so a failure is known before the drafting work is built on top of it.

## What goes in this file afterwards

The unit that runs the replay adds, for each case: what was read, what survived,
what did not, what a reviewer had to correct, the result against each of the
five points of the bar, and the decision. Real results only, from real runs, and
no estimate anywhere in it. The number of tests passing on the day the decision
is recorded goes in with the decision.
