# Your company base

This folder is your company's marketing context in one place. It holds what your
AI assistant needs to read before it can do real marketing work for you, and it
holds the record of how that context stays current as the business moves.

## What each folder holds

**context** is everything the assistant reads for meaning. Inside it,
`strategy` holds your ideal customer profile, your positioning, and your
messaging. `metrics` holds your numbers and what each one means. `plan` holds
your goals and targets. `notes` holds your own working notes and the thinking
behind decisions that never became a document. `context/map.md` is the map,
which says where everything lives and carries two settings you can change.

**work** holds the record of how the base stays current. `decisions` holds one
dated entry per decision the team made. `confirmations` holds the record of the
owner saying that a file is still right. `inbox` is where you drop meeting notes
and transcripts for the assistant to read. `proposals` holds suggested changes
while they are being prepared.

**corrections** holds what each run found wrong and which rule changed as a
result.

**CODEOWNERS** lists the files that need the owner's review before a change to
them is accepted. **gate-allowlist.txt** lists the exact pieces of text the
outgoing-content check is allowed to let through.

## Two things to know

The owner address in these files is a placeholder. When your base is created,
the setup step replaces it everywhere with your own work email address.

Everything in this folder is shared with everyone you invite to the base, so
treat it as a document your whole team can read. The two exceptions are
`work/inbox` and `work/proposals`, which stay on your own computer and are never
shared.
