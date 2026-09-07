# Every rule the stale check follows, in plain words

These are the rules exactly as the library applies them. Nothing here is a
guideline; each one is a comparison of dates, names, or text that either holds
or does not.

## The words used here

- A **decision** is one thing the team decided, written down in its own file
  with the day it was decided, the day it was written down, who decided it, the
  files it affects, and the day it should be looked at again.
- A **confirmation** is one owner saying one document is still right on one day.
  It is one line in that document's own confirmations file. The line carries no
  name; the identity comes from whoever saved the line, so a line cannot be
  written in somebody else's name.
- The **threshold** is the number of days a document may go without a
  confirmation before it counts as out of date. The map sets it, and it is
  thirty days unless the map says otherwise.

## When a document is out of date

1. **A decision has moved past it.** A decision that is still open and names the
   document flags it, unless an owner confirmed the document after the later of
   the day it was decided and the day it was written down. This is why a
   decision written down late still counts: the comparison uses both dates, not
   just one.
2. **Nobody has ever confirmed it.** A document with no owner confirmation at
   all is out of date from the start.
3. **The confirmation is too old.** A document whose newest owner confirmation
   is more days old than the threshold is out of date. An owner accepting a
   change to the document counts as a confirmation on the day they accepted it,
   which is set out below.
4. **A confirmation from somebody who does not own the document counts for
   nothing.** It is counted and reported, and it settles nothing.

## The same day exemption

A confirmation dated the same day the decision was made proves nothing, because
it could have been given before anybody knew. There is one exception. When
setting a base up, the person approves a document and a decision in the same
sitting, and both are written with the same run identifier. A confirmation whose
reason is `drafted` and whose run identifier matches the decision's own run
identifier does settle that decision, and only that decision.

That exemption does not depend on the dates at all. A decision made in August
and written down today, approved today alongside the document it affects, is
settled by that document's own drafted line, because the person was shown the
decision and the document together in one sitting. A drafted line whose run
identifier is a different one is read by the ordinary rules above.

A confirmation that names the decision by its identifier settles it whatever the
dates say, because naming it is proof the person saw it.

## When an accepted record settles a decision for a document

An accepted record in the `corrections` folder can settle a decision for a
document without anybody being asked. All three of these have to hold:

1. The record names that decision.
2. The change that first added the record also changed that document. A record
   that arrived on its own, without the document changing, settles nothing.
3. The one hash the record carries matches. The hash is worked out one way and
   one way only: take every path in the `context` folder that the record lists,
   in the order the record lists them, read each file as that same change left
   it, put the texts end to end, and hash the result. Files outside the
   `context` folder, the decision itself, and the record itself are not part of
   it.

A record that fails the second or the third test is reported as something that
could not be trusted, and it settles nothing.

## When accepting a change is the owner saying the document is right

A record that passes all three tests above says one more thing when the person
who accepted the change owns the document it changed. Accepting it is that
owner saying the document is right on the day they accepted it, so it counts
everywhere an owner's own confirmation would count: it starts the threshold
clock again, and it settles any other decision made and written down before
that day.

Two things follow from how acceptance is read. When the change is accepted with
a change of its own, which is what the button on the review page writes, the
person named is whoever pressed the button. When it is put on the end without a
change of its own, the only person named is whoever wrote it, so the writer and
the accepter cannot be told apart.

When the person who accepted the change does not own the document, nothing
changes. The record still settles the decision it names, and the document is
still waiting on its owner to say it is right.

## What flags itself rather than a document

- **A decision that names a file the base no longer holds** flags the decision.
- **A decision past the day it should be looked at again** is listed, with how
  many days have passed. The list is kept for the next session to raise.
- **The ledger itself** is called quiet when it holds no decision newer than the
  threshold. That is a statement about dates only. No calendar and no inbox is
  consulted, because the base has neither. The person can say nothing has been
  decided, and it stays quiet for that many days.

## A decision that names no files

Whoever writes a decision down may leave the list of affected files blank. When
they do, GTM Base works out which files it most likely touches:

1. Any file the map attaches to a word the decision uses.
2. Any context file whose own name, or whose kind, the decision mentions.
3. When neither of those points anywhere, every ideal customer profile and
   positioning file the base holds, because those are the files a decision moves
   most often.

The result is not applied. It is prepared as a proposal the owner approves, with
one line added to each file named saying GTM Base named it and asking for it to
be confirmed or removed. Accepting the proposal is the owner saying the list is
right. This proposal is identified by the decision, the map's own path, and the
sequence number one, which keeps it separate from the prepared change for any
one document.

## What a prepared change looks like

For every document a decision has moved past, one prepared file is written to
`work/proposals/pending/`. It carries:

- Where it came from, which is the ledger, and no source of its own.
- One edit. When the decision's own words name a heading that the document
  actually has, the edit replaces what is under that heading. When they do not,
  the edit adds a new part under the heading "Decisions to reflect".
- A first draft of the words, which names the decision and says the section
  should reflect it. It is a starting point for the assistant to rewrite, not
  finished text.
- The evidence: the decision's identifier, the file it was written down in, the
  day it was decided, and the decision's own words quoted.
- How sure it is, which is medium, because a first draft never claims more.
- The rule it changes, which is none.
- The marker line naming both the prepared change and the decision it is about.

The decision itself is not written out a second time. It is already in the base,
so the prepared change names it and quotes it as evidence instead of carrying a
copy of it. That is what tells the two apart: a proposal whose marker names its
own identifier as the decision is creating that decision and has to carry it,
and a proposal naming any other decision is pointing at one that already exists.

## How the same work is never done twice

A prepared change is identified by the decision and the document together, and
the identifier is worked out from those two facts alone, so the same pair always
gives the same identifier however many times the check runs. Before anything is
written, the run looks in four places and prepares nothing when any of them
already has it:

1. A prepared file with that identifier already waiting under `work/proposals/`,
   including the copies kept once a proposal has been raised.
2. This seat's own index, which records the identifier once a proposal has been
   raised from it.
3. An accepted record naming that identifier, or naming the same decision and
   the same document.
4. A proposal on the shared copy carrying that marker line, whether it is open,
   already accepted, or one somebody turned down.

## What the first run says

At the end of setting a base up, exactly one thing is said, and the order it is
looked for never changes:

1. A required document the person chose not to write.
2. No decision written down at all.
3. A document whose material is dated before the decision it is meant to
   reflect, which is worth reading again.
4. Otherwise, that nothing is out of date yet, naming the first date it will
   watch and the decision that date belongs to.

The wording never claims more than the dates show, and the finding is worked out
fresh every time it is asked for, never remembered from a previous run.
