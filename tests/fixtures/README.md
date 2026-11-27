# Fixtures

One valid example of every file GTM Base reads or writes. The tests parse these
rather than building strings inline, so a change to a format shows up as a
failing test in one place.

Every example here describes the same imagined situation. A meeting on the
twelfth of January settled that the company sells to organisations of twenty to
two hundred people, the customer profile still said any size, and a proposal was
raised to bring the document in line with that context change. The identifiers
are the real ones the library computes for that material, so a test can
recompute them and check that they match.

| File | What it is |
|---|---|
| `inbox-item.md` | A transcript dropped into the inbox, waiting to be read. |
| `change-entry.md` | One context change, written the way every entry is written today. |
| `ledger-entry.md` | The same context change in the older layout, which a base set up before the rename still holds. It is kept so the tolerant reader always has something old to read. |
| `drafts/change-entry.md` | A drafted context change in today's layout, as the model hands it back. |
| `drafts/ledger-entry.md` | The same drafted change in the older layout, kept for the same reason. |
| `drafts/umbrella.md` | A drafted customer profile across three segments, one short paragraph each, as the model hands it back. |
| `drafts/segment.md` | One of those segments drafted at full depth, as the model hands it back. |
| `drafts/messaging.md`, `drafts/voice.md`, `drafts/buyer-personas.md`, `drafts/product.md`, `drafts/competitors.md`, `drafts/design.md` | The six documents a base takes after setup (Track 4), drafted for a made-up freight software company, as the model hands them back. |
| `confirmations.md` | Three confirmations for one context file: drafted, a context change, and the threshold. |
| `corrections-file.md` | What the run found wrong and which rule changed as a result. |
| `pending-item.json` | What the analysis step proposes, before any check has run on it. |
| `proposal-staging.md` | The staged proposal: the context change, the edits, the excerpt, and the body a reviewer reads. |
| `pr-body.md` | The body on its own, which is the one document the review surface shows unchanged. |
| `machine.json` | Account state: the answer to the offer and the list of joined bases. |
| `seat.json` | Seat state for one base on one machine. |
| `sources/template-with-comments.md` | A marketing template carrying three authoring comments, which are taken out of the text rather than costing the whole document. |
| `adoption/` | Finished segment pages for Unit 1.7c. `clean-profile.md` passes the adoption contract; every other file exists to fail one clause of it: settings of its own at the top (discarded) or never closed (refused), a fence marker hidden inside a comment, contact details or a private key in the body, a heading used twice, a heading inside a block of code, underlined headings, no parts at all, a question above the first part, a question under a part (kept only on the person's say), two product lines, a name that folds into a file already in the base, a page whose folder the test makes a link, and a page that is not Markdown. |

The two identifiers that run through the whole set are the source,
`src-f9b4fc4d3b3d46561948ee51`, and the proposal, `stg-0d15637d82690cc7`. The
folders named in `machine.json` do not exist, because that file is only used to
check the shape of the record.
