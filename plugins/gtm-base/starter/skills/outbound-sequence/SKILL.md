---
name: outbound-sequence
description: Write a short outbound email sequence for one customer segment, grounded in that segment's own language and the company's approved positioning, messaging and voice, with every claim traced to the document behind it. Use when the person asks for an outbound sequence, a cold email sequence, or prospecting emails for a segment.
kind: skill
sources: []
status: draft
reads_required: [context/icps.md, context/positioning.md]
reads_optional: [context/icps/, context/messaging.md, context/voice.md, context/competitors.md]
standard: standards/outbound-sequence.md
---

# Outbound sequence

You are writing a short sequence of outbound emails for one customer segment.
Every claim in it rests on a document in the base, and a table under the
sequence names the document behind each one. A claim nothing in the base
supports is dropped, and the drop is reported, never softened into a vaguer
claim.

## What you work from

- The segment the person named, and anything they asked the sequence to say.
- The standard for this job, which holds the rules for the sequence. Follow
  it.
- The segment's own document when the base holds one; otherwise the customer
  profile. Say which you used.
- The positioning, which you always have.
- The messaging, the voice guide and the competitors, when the base holds
  them. Name each one that is missing as a gap, and never fill it.

When the person names a segment and the base holds documents for other
segments but not that one, list the segments it does hold and stop, so they
can choose.

The base holds no prospects and no customer list. Write to a role and a kind
of company, never to a named person, and write no email address, phone number
or name of anybody into the sequence.

## The shape

```
Segment: [the segment, and the path of the document its words came from]

Email one
Subject: [the subject line]
[the body]

Email two
...

Claims and where each comes from:
| Claim | Document |
|---|---|
| [the claim, as the email makes it] | [the path of the document behind it] |

Dropped: [each claim asked for that nothing in the base supports, quoted, or "none"]

Gaps: [each optional document the base does not hold, by name, or "none"]
```

Use "[first name]" and "[company]" where the sender fills in the prospect.
Every row of the claims table names a document you were given and nothing
else.
