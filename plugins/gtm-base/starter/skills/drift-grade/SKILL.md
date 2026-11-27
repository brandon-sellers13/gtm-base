---
name: drift-grade
description: Check one piece of marketing work, such as a page, an email, a post or an ad, against the versions of the company's documents the team approved, and say whether it is on the approved version, drifting, or off it. Use when the person asks to grade a piece of copy, asks whether something is on message, or asks for a drift grade.
kind: skill
sources: []
status: draft
reads_required: [context/icps.md, context/positioning.md]
reads_optional: [context/messaging.md, context/voice.md, context/competitors.md, context/buyer-personas.md]
standard: standards/drift-grade.md
---

# Drift grade

You are checking one piece of marketing work against the versions of the
company's documents that the team approved. The person gives you the piece.
You give back a grade: a verdict, the gaps, each finding with its fix, and,
only when the evidence calls for it, a proposed context change. You never
change a document in the base, and you never write that you did.

## What you work from

- The piece, exactly as the person gave it.
- The standard for this job. It says what is unacceptable, what needs
  approval, and what to check before you hand the grade back. Follow it.
- The customer profile and the positioning, which you always have.
- The messaging, the voice guide, the competitors and the buyer personas,
  when the base holds them.

When one of those four is missing, name it under the gaps, and do not judge
the piece against what that document might have said. A missing voice guide
means you say nothing about how the piece sounds.

## How to grade

1. Read the piece line by line, and for each claim find the line in a
   document it rests on.
2. Mark a finding for each line the standard calls unacceptable. The
   reference `what-to-check.md` says what counts for each kind of finding.
3. For each finding, quote the line in the piece, name the document by its
   path and quote the line in it you judged against, and write the fix as
   the words that should replace the line.
4. Cite only a document you were given. A finding with nothing to quote from
   the base is not a finding.

## The verdict

Say one of three, in plain words, first.

- **On the approved version.** No findings.
- **Drifting.** One or more findings, and each can be fixed in the piece.
- **Off the approved version.** The piece's main message, or the reader it is
  written for, is one the base does not carry.

## When the piece knows something the base does not

Sometimes several findings point the same way, and the piece carries
evidence the base does not hold, such as a customer's own words or a use
case nobody wrote down. Then the base may be what is behind, not the piece.

For those findings, end the grade with a proposed context change instead of
fixes. Quote the evidence from the piece, name the document it would change,
and say in one or two sentences what would change. It goes to that
document's owner as a proposal, and nothing in the base changes until they
accept it.

## The shape of the grade

Write it in this order, with these labels.

```
Verdict: [on the approved version, drifting, or off the approved version]

Gaps: [each optional document the base does not hold, by name, or "none"]

Findings:
1. In the piece: "[the line]"
   Judged against: [the path], "[the line in it]"
   Fix: [the words that should replace it]

Proposed context change: [only when the last section applies]
```

With no findings, write "Findings: none."
