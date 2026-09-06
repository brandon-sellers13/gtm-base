# Fixtures

One valid example of every file GTM Base reads or writes. The tests parse these
rather than building strings inline, so a change to a format shows up as a
failing test in one place.

Every example here describes the same imagined situation. A meeting on the
twelfth of January decided that the company sells to organisations of twenty to
two hundred people, the customer profile still said any size, and a proposal was
raised to bring the document in line with the decision. The identifiers are the
real ones the library computes for that material, so a test can recompute them
and check that they match.

| File | What it is |
|---|---|
| `inbox-item.md` | A transcript dropped into the inbox, waiting to be read. |
| `ledger-entry.md` | One decision the team made, in the ledger. |
| `confirmations.md` | Three confirmations for one context file: drafted, decision, and threshold. |
| `corrections-file.md` | What the run found wrong and which rule changed as a result. |
| `pending-item.json` | What the analysis step proposes, before any check has run on it. |
| `proposal-staging.md` | The staged proposal: the decision, the edits, the excerpt, and the body a reviewer reads. |
| `pr-body.md` | The body on its own, which is the one document the review surface shows unchanged. |
| `machine.json` | Account state: the answer to the offer and the list of joined bases. |
| `seat.json` | Seat state for one base on one machine. |

The two identifiers that run through the whole set are the source,
`src-f9b4fc4d3b3d46561948ee51`, and the proposal, `stg-0d15637d82690cc7`. The
folders named in `machine.json` do not exist, because that file is only used to
check the shape of the record.
