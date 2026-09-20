# Every rule the stale check follows, in plain words

These are the rules exactly as the library applies them. Nothing here is a
guideline; each one is a comparison of dates, names, or text that either holds
or does not.

## The words used here

- A **context change** is one thing that happened that makes a document no
  longer true, written down in its own file with the day it happened, the day
  it was written down, who noted it, the files it affects, and the day it
  should be looked at again. It may be something the team settled, but it may
  equally be a competitor's launch, a price change, or something learned about
  how customers describe the problem. After this paragraph it is shortened to
  a change.
- A **confirmation** is one owner saying one document is still right on one day.
  It is one line in that document's own confirmations file. The line carries no
  name; the identity comes from whoever saved the line, so a line cannot be
  written in somebody else's name.
- The **threshold** is the number of days a document may go without a
  confirmation before it counts as out of date. The map sets it, and it is
  thirty days unless the map says otherwise.

## When a document is out of date

1. **A context change has moved past it.** A change that is still open and
   names the document flags it, unless an owner confirmed the document after
   the later of the day it happened and the day it was written down. This is
   why a change written down late still counts, because the comparison uses
   both dates and not just one.
2. **Nobody has ever confirmed it.** A document with no owner confirmation at
   all is out of date from the start.
3. **The confirmation is too old.** A document whose newest owner confirmation
   is more days old than the threshold is out of date. An owner accepting a
   change to the document counts as a confirmation on the day they accepted it,
   which is set out below.
4. **A confirmation from somebody who does not own the document counts for
   nothing.** It is counted and reported, and it settles nothing.

## The same day exemption

A confirmation dated the same day a change happened proves nothing, because it
could have been given before anybody knew. There is one exception. When setting
a base up, the person approves a document and a change in the same sitting, and
both are written with the same run identifier. A confirmation whose reason is
`drafted` and whose run identifier matches the change's own run identifier does
settle that change, and only that change.

That exemption does not depend on the dates at all. A change that happened in
August and was written down today, approved today alongside the document it
affects, is settled by that document's own drafted line, because the person was
shown the change and the document together in one sitting. A drafted line whose
run identifier is a different one is read by the ordinary rules above.

A confirmation that names the change by its identifier settles it whatever the
dates say, because naming it is proof the person saw it.

## When an accepted record settles a change for a document

An accepted record in the `corrections` folder can settle a change for a
document without anybody being asked. All three of these have to hold:

1. The record names that change.
2. The change that first added the record also changed that document. A record
   that arrived on its own, without the document changing, settles nothing.
3. The one hash the record carries matches. The hash is worked out one way and
   one way only: take every path in the `context` folder that the record lists,
   in the order the record lists them, read each file as that same change left
   it, put the texts end to end, and hash the result. Files outside the
   `context` folder, the change itself, and the record itself are not part of
   it.

A record that fails the second or the third test is reported as something that
could not be trusted, and it settles nothing.

## When accepting a change is the owner saying the document is right

A record that passes all three tests above says one more thing when the person
who accepted the change owns the document it changed. Accepting it is that
owner saying the document is right on the day they accepted it, so it counts
everywhere an owner's own confirmation would count: it starts the threshold
clock again, and it settles any other change that happened and was written down
before that day.

Two things follow from how acceptance is read. When the change is accepted with
a change of its own, which is what the button on the review page writes, the
person named is whoever pressed the button. When it is put on the end without a
change of its own, the only person named is whoever wrote it, so the writer and
the accepter cannot be told apart.

When the person who accepted the change does not own the document, nothing
changes. The record still settles the change it names, and the document is
still waiting on its owner to say it is right.

## What flags itself rather than a document

- **A change that names a file the base no longer holds** flags the change.
- **A change past the day it should be looked at again** is listed, with how
  many days have passed. The list is kept for the next session to raise.
- **The record of changes itself** is called quiet when it holds nothing newer
  than the threshold. That is a statement about dates only. No calendar and no
  inbox is consulted, because the base has neither. The person can say nothing
  about the business has changed, and it stays quiet for that many days.

## A change that names no files

Whoever writes a change down may leave the list of affected files blank. When
they do, GTM Base works out which files it most likely touches:

1. Any file the map attaches to a word the change uses.
2. Any context file whose own name, or whose kind, the change mentions.
3. When neither of those points anywhere, every ideal customer profile and
   positioning file the base holds, because those are the files a change moves
   most often.

The result is not applied. It is prepared as a proposal the owner approves, with
one line added to each file named saying GTM Base named it and asking for it to
be confirmed or removed. Accepting the proposal is the owner saying the list is
right. This proposal is identified by the change, the map's own path, and the
sequence number one, which keeps it separate from the prepared change for any
one document.

## What a prepared change looks like

For every document a change has moved past, one prepared file is written to
`work/proposals/pending/`. It carries:

- Where it came from, which is the base's own record of changes, and no source
  of its own.
- One edit. When the change's own words name a heading that the document
  actually has, the edit replaces what is under that heading. When they do not,
  the edit adds a new part under the heading "Context changes to reflect".
- A first draft of the words, which names the change and says the section
  should reflect it. It is a starting point for the assistant to rewrite, not
  finished text.
- The evidence, which is the change's identifier, the file it was written down
  in, the day it happened, and the change's own words quoted.
- How sure it is, which is medium, because a first draft never claims more.
- The rule it changes, which is none.
- The marker line naming both the prepared file and the change it is about.

The change itself is not written out a second time. It is already in the base,
so the prepared file names it and quotes it as evidence instead of carrying a
copy of it. That is what tells the two apart. A proposal whose marker names its
own identifier as the change is creating that change and has to carry it, and a
proposal naming any other change is pointing at one that already exists.

## How the same work is never done twice

A prepared change is identified by the change and the document together, and
the identifier is worked out from those two facts alone, so the same pair always
gives the same identifier however many times the check runs. Before anything is
written, the run looks in four places and prepares nothing when any of them
already has it:

1. A prepared file with that identifier already waiting under `work/proposals/`,
   including the copies kept once a proposal has been raised.
2. This seat's own index, which records the identifier once a proposal has been
   raised from it.
3. An accepted record naming that identifier, or naming the same change and
   the same document.
4. A proposal on the shared copy carrying that marker line, whether it is open,
   already accepted, or one somebody turned down.

## What the first run says

At the end of setting a base up, exactly one thing is said, and the order it is
looked for never changes:

1. A required document the person chose not to write.
2. No context change written down at all.
3. A document whose material is dated before the change it is meant to
   reflect, which is worth reading again.
4. Otherwise, that nothing is out of date yet, naming the first date it will
   watch and the change that date belongs to.

The wording never claims more than the dates show, and the finding is worked out
fresh every time it is asked for, never remembered from a previous run.

## What the review asks, and what the moment of use asks

Nothing is asked at the start of a session. Two things ask, and they ask under
different rules.

1. **The review a person asks for**, by saying "review my base". It lists every
   document the rules above call out of date and that this seat's address owns,
   one line each, and it issues one single-use question identifier per document
   listed. A document set aside for now is not listed until the day it comes
   back. The base's own map is never listed, whatever its dates say. Every
   prepared change waiting for the owner's yes is listed too, with no question
   identifier, because approving a change is not answering a question.
2. **The moment a document is about to be used.** This raises itself, and it is
   the only thing that does. It fires for one reason only: an open context
   change has moved past that document. A document nobody has confirmed for
   longer than the threshold does not raise it, and neither does an unanswered
   marker in the document; both of those wait for the review. It says a fix is
   ready only when a prepared change for that document is really waiting, and
   otherwise it offers to prepare one.

While the base has been asked to stay quiet, neither the weekly line nor the
moment of use says anything, and a review the person asks for still works.
Quiet asked for until they ask again ends the moment they ask for a review, and
the review says so in its first sentence. Quiet asked for as a month ends on
its own day, and no quiet lasts longer than a month however it was written
down.

## What one answer settles, and what it leaves alone

Each of these is one answer about one thing, and none of them reaches further
than what the person was shown.

1. **Use it as it stands.** Nothing is written about the document. The flag
   still stands, the document is still listed in the next review, and the next
   check says the same thing. What is recorded is only how the question ended,
   in this seat's own log, counted apart from the times somebody said a
   document was still right.
2. **It already reflects this change.** One confirmation line is written and it
   names that one change. It settles that change for that document and no
   other. A document behind two changes is still behind the second one
   afterwards, and the next check says so, because the person was shown one
   change and answered about one change.
3. **Not now**, inside a review. The document is left out of reviews for the
   number of days the map sets. It does not stop the moment of use. A document
   somebody is about to use, that a recorded change has overtaken, is the one
   case the base speaks up for, and setting a question aside in a review is not
   a statement that the document is fine to use.
4. **Fix it first.** A change is prepared for that document and that change,
   and nothing happens to the document until its owner approves it. A change
   already prepared for that pair is never prepared twice, and nothing is
   prepared at all while items are waiting to be read in the inbox.

Somebody who does not own the document can still carry on or stop, but the
confirmation is the owner's to give and is refused for anybody else before any
question is used up.
