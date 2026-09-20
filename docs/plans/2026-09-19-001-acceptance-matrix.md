---
title: "Acceptance matrix: the lifecycle of one context file, and the six UX rulings"
type: reference
status: active
date: 2026-09-19
plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md
unit: "Unit 1.1: Contract amendments to the documents"
---

# Acceptance matrix

This is the consistency proof the Codex verdict of 2026-09-19 asked for in its
first ordered step. It has two tables. The first says, for every state a context
file can be in, what each of the four parts of the product does about it. The
second records one ruling for each of the six steps that the Fable review
listed as breaking the product's own standard for how a step reads.

Every later unit of Phase 1 adds to these tables rather than inventing a state
of its own. If a unit needs a state that is not here, the matrix is wrong and
the matrix gets fixed first.

Throughout this document, the words a person reads for what the base tracks are
"context change". The older word, "decision", appears only where this document
quotes something written before 2026-09-19.

## One row per state, one column per part of the product

The states are the ones in the lifecycle table of the plan. Setup means the
first session, run by the join skill. Review means the walk a person asks for
by saying "review my base". Moment of use means the check that runs when a
document is about to be used. Stale computation means the pure calculation that
the other three read their answers from.

| State | What setup does | What the review does | What the moment of use does | What the stale computation does |
|---|---|---|---|---|
| **drafted** | Writes the file after the person's yes, stamps the owner, and appends one confirmation line dated today with the trigger "drafted". This is how both required documents come into being. | Lists the file when its confirmation has passed the base's threshold, and asks the owner whether it is still true as written. | Lets the document be used without a word, unless a recorded context change affects it. | Counts the file as complete. Starts the review clock from the date on the confirmation line. |
| **adopted** | Runs the per-file adoption contract, writes the cleaned file with library-written settings naming the original path and its date, and takes the owner's yes against exactly those bytes. Never edits or moves the original. | Treats it exactly as a drafted file. Being adopted earns it no extra credit and costs it none. | Treats it exactly as a drafted file. | Treats it exactly as a drafted file. The word "adopted" carries no meaning of its own about how current the file is; only the owner's confirmation does. |
| **confirmed** | Writes the confirmation line for a file it has just drafted, dated today, with the trigger "drafted". | Writes a confirmation line when the owner answers yes, and names the context change when the question was about one. | Writes a confirmation line when the owner answers that the document already reflects the change. That is a separate answer from choosing to use the document as it is. | Restarts the review clock. Settles, for that one file, the change the line names. A line whose author is not an owner of the file is recorded and treated as no confirmation at all. |
| **flagged** | Cannot produce this state for a document it wrote in the same run, because it never edits a file it has already written. A context change captured at the closing can leave a document flagged, and setup leaves it that way. | Lists the file, names the change and its date, and offers a prepared fix. A no becomes a prepared change the owner can approve. | Speaks up. Names the document, the change, and the date, and asks whether to use the document as it is or fix it first. Offers to prepare a fix when none is ready. Produces no work product before the answer. | Computes the flag from the recorded changes and the confirmations. It is never stored, so it can never drift out of step with the files. |
| **unanswered marker** | Must not approve a file that still carries a `[your call: ...]` marker without the person having answered it. | Lists every marker in the base, one line each, and asks about them. | Does not speak up for a marker on its own. A marker alone never interrupts work. | Counts the file as not confirmed and not complete, computed by reading the body, independently of the `status` field, so a retained draft can never pass as finished. |
| **skipped** | Writes the file with `status: skipped` and no body, says plainly that it is written down as skipped, and offers to finish it in a later session. | Offers to finish the document. Does not ask a confirmation question about it. | Says the document is not written yet rather than treating an empty file as usable. | Counts the file as not complete. Names it first in the closing finding order. Never counts it in the yes rate, in either direction. |
| **the map** | Creates it from the template with its settings and no placeholder date, and never asks about it. | Leaves it out. It is never listed and never asked about. | Leaves it out. | Leaves it out of flags, questions, and the review, by its kind. No confirmation line is written for it, because a confirmation line would only bring it back after the threshold and it would have nothing to say when it did. This also covers the one base created before this change. |

Two notes on reading the table. First, no cell says "nothing", because every
part of the product does something in every state, even if that something is
deliberately to stay quiet. Second, the moment-of-use column describes the
check inside a skill, which is deterministic, and the instruction the assistant
is given for reading a context file outside a skill, which is not. The plan
records that difference as a real risk rather than treating the two as equal.

## UX rulings

The Fable review of 2026-09-19 listed six steps that break the product's own
standard for how a step should read: say what it is for in one sentence, show
something that can be read in a few seconds, tie it back, and then ask one
thing. This table records one ruling for each, and names the unit that carries
it out.

**These six rulings are written to the recommended answers in call 5 of the
plan's "For Brandon" table, and the whole table is awaiting Brandon's yes.** A
different answer on any row is a one-row edit here and a change to the unit
named in that row, and to nothing else.

| # | The step today | Why it breaks the standard | The ruling | Unit that carries it out |
|---|---|---|---|---|
| 1 | The consent step, where the person is asked whether their material may be read. It runs to seven sentences before the question arrives. | It cannot be read in a few seconds. It is long for a good reason, because a real run showed that a list of files offered for one yes reads as a list about to be copied somewhere, so the length is protecting something real. | The paragraph becomes three short lines and then the question. The three lines keep what the real run taught: that only file names and first headings have been looked at, that nothing is copied or changed, and that the list is fixed once the person says yes. Nothing that a run proved necessary is dropped, it is only said shorter. | 1.6 |
| 2 | The step before each draft, where the person is asked whether to draft from the list or narrow it. After an explicit choice of folders this is the second and third time they are asked. | It asks something that has already been answered, which is the same defect the third real run reported. | When the person chose their folders explicitly, the narrowing question is not asked again before each draft. They are still shown what the draft will read and what it will leave out, and they can still narrow it when they want to. When the consent was a plain yes to a proposed list rather than an explicit choice, the question stays. | 1.6 |
| 3 | The confirm step's instructions, which show the whole document and then explain all three answers, for every question. | In a review with many documents due, the whole document and the full explanation repeat for each one. | The review shows one line per item. The document itself is there on request. The three answers are explained once at the top of the review, not once per item. | 1.5, in the review entry point on the stale-check skill |
| 4 | The closing, which after the new closing question becomes several asks in a row: what got in the way, the context change, the proposed entry with four correctable fields, and then one reconciliation question per affected document. With segments, the list of affected documents can be long. | Too many asks in a row at the point where the person is finishing. | At the closing, the person is asked whether a document already reflects the change only for the two required documents. Any other affected document is left flagged and is picked up in the review. | 1.5 |
| 5 | Adoption, where a promise to show each cleaned document whole meets a standard that says never paragraphs of evidence. | The two rules contradict each other as soon as there is more than one document to approve. | The interaction is a short wrapper: what was removed, the opening lines, and where the whole cleaned file is. The whole cleaned file is written out and can be read in full before any answer is given, and the yes is bound to a hash of exactly those bytes. The complete artifact and the short wrapper around it are two different things, and the readable-in-seconds rule applies only to the wrapper. | 1.7c |
| 6 | Findings that name a file by its path and a change by its identifier, so a marketing lead reads a folder path and a string of characters. | Neither is a name a person recognizes, so the finding is about something the reader cannot place. | Documents and changes get human names. A document is "your customer profile", never its path. A change is its first line and its date, never its identifier. The paths and identifiers stay in the machine-readable lines, which nobody reads aloud. | 1.1b |

## What this matrix does not decide

It does not decide anything about how a change is approved on a base that has
no shared copy, which is its own unit. It does not decide the wording of any
sentence; wording is written in the unit that owns the sentence and is read
aloud by Brandon before the release that ships it. And it holds no results from
the fidelity replay, which live in `docs/walkthroughs/2026-09-fidelity-replay.md`
and are written there by one unit and by no other.
