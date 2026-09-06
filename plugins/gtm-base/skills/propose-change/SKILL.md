---
name: propose-change
description: Turn a prepared change to a context file, or a change the person made by hand, into a proposal the team can review, carrying the decision behind it and a record of what changed. Use when a staged proposal is waiting, or when the person says they edited a file themselves and wants it raised for review.
---

# Propose a change

This skill takes one prepared change to a file in the `context` folder and
raises it for review, so somebody on the team can read it and accept or turn it
down. It never changes the shared copy of the base by itself, and it never
touches the person's own folder.

## The two ways a proposal starts

The first way is a staged file another skill has already written. The stale
check writes one for every file a decision has moved past, and the reading
skills write one for every change a meeting suggested. Each staged file names
the file to change, the heading inside it, the new words, the evidence behind
them, and the decision that prompted them.

The second way is the person's own hand. Somebody reads a report, opens
`context/strategy/icp.md`, changes a paragraph, and saves it. Their change stays
exactly where they put it, and this skill builds the proposal around it. It asks
one thing first: where the change came from, in their own words. That answer
becomes the evidence the reviewer reads, so nobody has to take the change on
trust.

## What happens, in this order

1. The staged file is read and checked. A change to the map is refused, and so
   is a change to the settings at the top of a file or to anything outside the
   `context` folder.
2. Two conditions are asked. If this session has already read the person's own
   documents, nothing may leave the computer until they start a new one. If this
   base has never had its first backup reviewed, that review comes first.
3. Everything the proposal would carry is read for things that must never leave
   the computer: email addresses, phone numbers, keys, web addresses carrying a
   key, links to shared documents, paths from inside a home folder, and text a
   reader would not see. Anything found stops the run, and the reason names the
   kind of thing found and never the thing itself.
4. The same change is looked for everywhere it might already be, by the one
   marker line every proposal carries. Already accepted, and the run stops.
   Already under review by somebody else, and the run stops and records their
   review. Turned down before, and the run stops until the person says to raise
   it anyway.
5. A working folder is prepared away from the person's own folder, the change is
   applied there, the decision behind it is written beside the change, and so is
   the record of what changed and why.
6. The whole lot is sent and the review is opened. The staged file is then kept
   as the copy a proposal can be raised from again, and the working folder is
   taken away.

Every step is safe to repeat. A run that stops halfway leaves the working folder
behind, and running it again picks up where it left off rather than starting a
second review.

## What it refuses, and why

- A change to the map, because the map is what tells the assistant where
  everything lives.
- A change to the settings at the top of a file, because those settings carry
  who owns the file and when they last confirmed it, and a proposal that could
  rewrite them could confirm itself.
- A change to anything outside the `context` folder.
- Anything carrying a contact detail, a key, a link to a shared document, or a
  path from inside a home folder.
- A change to a part of a file that is no longer there, because the shared copy
  has moved on since the change was prepared. The proposal is kept and can be
  raised again once the file is put back in order.

## Running it

From inside the base:

- `python3 scripts/propose.py --staging <path to the staged file>`
- `python3 scripts/propose.py --local-edit --source "<where the change came from, in your words>"`
- `python3 scripts/propose.py --reopen <proposal id>`

The last one raises a proposal again from the copy kept when it was first sent.
Use it after the file it changes has been put back in order, or when the person
says to raise a change that was turned down before.

`references/pr-body-rules.md` in this folder says what the text of a proposal
has to contain and in what order. The text says, in its own words, that an
assistant drafted it and that no person has reviewed it yet, so nobody reading
it later mistakes it for a person's own writing.
