# How a first session ends

The closing has two halves. The first is one true thing about the base that now
exists, worked out from the dates in it. The second is the message that says
where the base is and how to come back to it. Both are below, word for word,
and neither one is written fresh each time.

## The one finding, in a fixed order

The finding is worked out by `python3 scripts/join.py close`, which reads the
base as it stands and takes the first of these that is true. The order never
changes, so the same base always produces the same finding.

The order below is amended 2026-09-19, r2.4 section A. It is the contract that
Unit 1.2 of `docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md`
builds, and it is written here before the code changes so that no promise in
this repository is ahead of what the base actually says.

1. **A file the person did not write.** One of the two files a base needs is
   missing, or it was skipped. The finding names that file and says there is
   nothing there to keep current yet.
2. **A file with a question still open in it.** An approved file still carries
   a question nobody has answered, written into the file as `[your call: ...]`.
   The finding names the file and says how many questions are open in it. The
   questions themselves are not read out here, because they come out of the
   file; the review shows each one, held apart as data. (Added 2026-09-19, r2.4
   section F. Built by Unit 1.7b on 2026-09-26, which is when this place in the
   order began to be reached.)
3. **A document older than the context change it is meant to reflect.** The
   material a document was written from is dated before the day the change
   happened. The finding names the document, both dates, and says it is worth a
   read. It looks only at the files that change affects, and only at changes
   that are still open.
4. **The honest baseline, when nothing has been recorded yet.** Both documents
   are confirmed and no context change is recorded, so the base cannot yet
   check whether a change has made either document out of date. The finding
   says exactly that. It names each document and the day its owner confirmed
   it, which is usually today and is a different day for each document when
   setting up was resumed on a later day, and it names the day each document
   comes up for review. It never says that nothing is out of date, and it never says that
   there is no date to watch. (Amended 2026-09-19, r2.4 section A. This
   replaces the older line that said nothing had been written down yet, which
   mistook missing evidence for a base that was known to be current.)
5. **Nothing is out of date.** None of the above is true, and at least one
   context change is recorded. The finding says so and names the first date GTM
   Base will watch, which is the earliest review date any open change carries.

## Never claim more than the dates show

The finding is a statement about dates and about which files exist. It is
allowed to say nothing more than that. Do not add what you think the base is
missing, do not guess at what the person should do next, and do not turn
"nothing is out of date" into a promise that everything is right. Do not turn
the honest baseline into that promise either, because a base with nothing
recorded yet has not been checked, it has only been set up. If the run produced
no finding at all, say that plainly rather than inventing one.

Say the finding once, in the words the command printed, before the closing
message.

## The closing question

A context change is anything that happened that makes a document in your base
no longer true. GTM Base wants one because a base that holds documents and
nothing about what has moved since cannot tell you when a document has been
overtaken. What it does with one is check it against each document it affects,
and speak up when a document you are about to use is behind it.

For example: you stopped selling to companies under twenty people in August,
so the part of your customer profile that says who you sell to is no longer
true.

Tell me if anything about the context of the business changed that we should account for. One sentence is enough, or say skip.

## The words of that request never change

The request above is fixed. It is written here once, it is said as it is
written, and nothing is added to it. It carries no question mark, which is on
purpose, because "or say skip" is the second half of the request and turning
the whole thing into a question would make skip sound like a failure to
answer. Skip is a whole answer and the person who gives it has finished this
step.

## Finished documents still to come

When some of the finished documents the person chose to take in as they stand
are not in the base yet, the closing message is followed by one more sentence,
printed by the command, saying that the next session will offer to finish
them. Say it as printed. What they chose, and every answer they gave about
each document, is kept on this computer outside the base, where the closing
does not clear it (Brandon's call 18 of the 2026-09-19 plan, built by Unit
1.7d). Saying "finish setting up my base" finishes it without asking anything
they already answered.

When a segment the person settled to be drafted is not in the base yet, the
sentence says instead that the next session will offer to finish the
segments, and that it will ask again before it reads any of their files to
draft one. The yes to read their material ends with the setup, so a later
session never drafts from it without asking again (Brandon's call 29). Say it
as printed. Only one of the two sentences is ever said.

## Before a base holding many files is first backed up

The review of what leaves the computer the first time a base is backed up was
designed for a base holding two or three documents. A base that took in a
dozen finished segment pages holds more than anybody can read through in one
sitting, so that review has to be rewritten for a base holding many files
before backing up ships. This is a condition of the release that brings
backing up, recorded here by Unit 1.7d because the review itself is not built
yet.

## Both versions of the closing message

There are two versions of the closing message, and which one is said depends on
whether the base was linked to the folder the person's marketing material lives
in. The command works that out and prints the right one. Both are below word for
word, and neither is written fresh each time.

## The closing message

Your base is set up. It lives in {{folder}}, on this computer, and nowhere
else. Nothing in it has left this machine.

Open that folder the next time you want to work on your base. On recent
versions of Claude Code you can move there right now by typing:
/cd {{folder}}

Your base can also say where your data lives and which tool reads it, which
is what lets a skill find its data and say plainly when it cannot reach it.
Say "draft my source map" whenever you want that; nothing about it is
needed today.

When you want a copy of your base kept somewhere off this computer, or you want
somebody else on your team to work in it with you, say so and GTM Base will
walk you through it. Both of those arrive with the next release, so today the
base stays here with you.

When you have a recording or a written record of a sales call, you will be able
to hand it over and have GTM Base read what it says into the base. That arrives
with a later release, and it is honestly not here yet.

## The closing message when a folder is linked

Your base is set up. It lives in {{folder}}, on this computer, and nowhere
else. Nothing in it has left this machine.

Open the folder you named, {{content}}, and your base will be there; you can
also open the base's own folder at {{folder}}. Nothing was written into the
folder you named and nothing in it was changed.

Your base can also say where your data lives and which tool reads it, which
is what lets a skill find its data and say plainly when it cannot reach it.
Say "draft my source map" whenever you want that; nothing about it is
needed today.

When you want a copy of your base kept somewhere off this computer, or you want
somebody else on your team to work in it with you, say so and GTM Base will
walk you through it. Both of those arrive with the next release, so today the
base stays here with you.

When you have a recording or a written record of a sales call, you will be able
to hand it over and have GTM Base read what it says into the base. That arrives
with a later release, and it is honestly not here yet.
