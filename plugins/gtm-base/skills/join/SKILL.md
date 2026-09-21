---
name: join
description: Set up a company base for somebody who does not have one yet, reading the marketing material they name and drafting their ideal customer profile and their positioning for approval. Use when the person says "set up my company base", asks to set up a company base, says they want to start a base, or answers yes to the setup offer. Say "set up my company base" whenever you are ready. Also handles "link this folder to my base", "unlink this folder from my base", and "show my linked folders", which connect a base to the folder somebody keeps their marketing material in. Also handles "join a base from a link" and "back this up", both of which arrive with the next release and are refused today with one sentence.
---

# Set up a company base

This skill runs the whole first session with somebody who has no base yet. You
do the talking. Every step that touches their computer happens through
`scripts/join.py`, and every sentence you say about what is about to happen is
in this file or in `references/closing-rules.md`. Say those sentences as they
are written.

### What the script prints

Every command prints two kinds of line. Whole sentences are for the person and
you say them as they are. Lines of the form `name=value` are for you and you
never read them out. In one of those lines, the name runs from the start of the
line to the first equals sign, and everything after that sign is the value. A
value that holds a space, an equals sign, or a quotation mark arrives inside
quotation marks, with any quotation mark or backslash inside it marked off by a
backslash. Read a quoted value by taking the quotation marks off and undoing
those marks. A value is never longer than three hundred characters, and one
that was longer ends in three full stops. A value never holds a line break, so
one line is always one value.

Three rules hold for the whole session.

1. Say what is about to happen before it happens. Every step below starts with
   the sentence that belongs to it.
2. Never ask for one field at a time. Each of the two documents is drafted
   whole and shown whole.
3. Never say how long anything will take, and never reassure them about it.
   Not as a number, not as a promise of speed, not as an aside.

### Words somebody typed never go on a command line
<!-- step -->

A sentence a person wrote can hold a dollar sign, a bracket, or a pair of
backticks, and each of those is an instruction to the shell the moment their
words are written into a command. So their words will travel in a file, and
the command will carry the path to it.

- Ask for somewhere to put them first, with this:

  ```
  python3 scripts/join.py words-file --run <run identifier> --for <kind>
  ```

- It prints `words=<path>`. Write their words to that path.

- Give the command that path, never the words.

- Every command that takes words this way ends in `-file`.

- A path GTM Base did not hand out is refused, and each file is read once and
  then taken away, so ask for a fresh one every time.

### Step 1. Say what setting up a base does

Before running anything, say these three things and then the line about
stopping. This is the first thing in the session and nothing else comes before
it.

- A company base is one folder on this computer holding your strategy, your
  numbers, and the context changes behind them, in a form your AI can read at
  the start of every session.
- Setting it up means reading the marketing material you already have and
  writing two documents from it: who you sell to, and how you describe what
  you sell.
- You see every document whole before anything is written down, and nothing is
  written down until you say yes to it.

Then say, word for word:

You can stop at any time, and nothing you have not approved is kept. Say "set up my company base" whenever you are ready.

When you are ready to begin, the run will need an identifier of its own, so
start it with:

```
python3 scripts/join.py new-run
```

It prints `run=<identifier>`. Every later command in this session takes that
same identifier.

### Step 2. The sharing notice

Say this once, before the first draft is written, and never again:

Files you approve here may later be shared with everyone invited to this base.

Nothing runs in this step. It is said so that the person deciding whether to
approve a document already knows who may end up reading it.

### Step 3. The one opening question

Ask exactly one question, and ask it in these words:

Where is your company's material, roughly? A company folder is fine, and so is a folder you keep for marketing. It can also be something you would rather paste in, or a tool you already have connected.

Wait for the answer. Do not offer a list of examples beyond those three, and do
not ask a second question before they have answered the first one.

### Step 4. The company name, and where the base will go

Ask for the company name, in one short question. Then say that GTM Base will
propose a folder and that nothing will be created until they agree to it, and
run:

Their answer is a name they typed, so it travels in a file rather than in the
command. Ask this run for one, put the name in it, and use it:

```
python3 scripts/join.py words-file --run <run identifier> --for company
python3 scripts/join.py propose-location --run <run identifier> --company-file <the path it printed>
```

The first command prints `words=<path>`. Write the company name into that file
with your file-writing tool, exactly as they said it, and pass that path back
along with the same run. Both commands need the run: that is what says which
setup this file belongs to, and without it the file is not one GTM Base can
read. The file is read once and then taken away, so ask for a fresh one for
each step that needs the name. Never put their name in the command itself.

Add `--content-folder <path>` when they named a folder that holds their
material. That folder is not where the base goes. It is the folder the base will
be linked to, so that opening Claude Code there brings the base along. The
command creates nothing. It prints one sentence saying where the base would go,
and the machine readable lines `target=`, `parent=`, `reason=`, and, when they
named a folder, `belongs-with=`.

Every base goes in a folder kept for bases inside their home folder, one folder
per company. Show them the sentence the command printed and ask whether that is
the right place. The sentence names the folder they named as the one to open
from then on, and that is the point to make: the base lives in its own folder,
and it wakes up in theirs. Say as well that nothing in their folder is changed
or read again.

When the command prints `codes=company-folder-exists`, there is already a folder
for a company of that name, so ask them for a name that tells the two apart and
run the command again with it. Never build over a folder that is already there.

If they say they would rather have the base sit inside the folder their material
is in, run the command again with `--beside` as well as `--content-folder`. The
same checks run on that folder, and it is refused when another tool already
keeps a history for it, when another program copies it off the computer on its
own, or when it is inside a base or inside the folder GTM Base keeps for itself.
When the command says `sync-unknown`, ask them the question it could not answer:
does any app automatically copy this folder, or your whole home folder, to cloud
storage. If they say yes, do not build there.

Only when they have said yes does anything get created, and that happens later,
at the moment they approve the first document. Pass the same
`--content-folder <path>` to `approve` on that first document, so the base is
linked at the moment it comes into being.

### Step 5. What will be read, and the yes that fixes the list

Start by finding the likely material rather than asking them to find it. Say
that GTM Base will look through the folder they named for the places their
marketing material sits in, and that it will look at nothing but file names and
first headings while it does. Then run:

```
python3 scripts/join.py words-file --run <run identifier> --for folder
python3 scripts/join.py survey --folder-file <the path it printed> --run <run identifier>
```

The first command prints `words=<path>`. Write the folder they named into that
path and pass it back. A folder name is whatever somebody called their folder,
so it never goes in the command itself, and the file is read once and then
taken away, so ask for a fresh one before each of the three steps below.

It prints one sentence and then one `place=<folder> score=<number>` line for
each place it found, with a count of each kind of document after it, and a
`note=` line for anything it left out. Say that sentence word for word and say
nothing else about the places. It is one of these three:

It looks like your marketing material sits in these places: <folder> (<number> customer profiles, <number> persona files), <folder> (...). Is this it? Say yes, name a folder to add, or name one to drop.

It looks like your marketing material sits in <folder> (<number> customer profiles, <number> persona files). Is this it? Say yes, name a folder to add, or name one to drop.

I could not find anything that looks like marketing material in <folder> by its file names and headings. You can name a folder inside it, or paste the material in.

Wait for their answer. On a plain yes, and on any answer that adds or drops
folders, run the list for the places they settled on:

```
python3 scripts/join.py words-file --run <run identifier> --for folder
python3 scripts/join.py list-sources --folder-file <the path it printed> --run <run identifier> --from-survey
```

Add one `--add <folder>` for each folder they named to add and one
`--drop <folder>` for each one they named to drop. The files lying loose at the
top of the folder they named are a place of their own, and its name on the
`place=` line is a single full stop, so that is what to pass to `--drop` when
they say those files do not belong. A name that is not a folder of the one they
named comes back as `codes=no-such-folder` and nothing is shown, so ask them
for a folder that is there. Dropping every place comes back as
`codes=no-folders-chosen`, and the answer to that is to ask which folder holds
the material and list that one.

It prints the files that would be read, with a date on each one that has a date,
and then what was left out, counted by the reason it was left out. Show them
both halves. The command also writes that list down inside the run's own
folder, which is what their yes is taken against. If it prints
`note=date-clamped`, one of the files says it was changed on a day still to
come, and the date shown for it is today rather than the day the file claims.
Say so. If the command says a second yes is needed, or that the folder looks
like it holds work for more than one company, follow
`references/reading-rules.md` before going any further.

If the command prints `note=narrow-first`, the places they settled on still hold
a large number of files spread across several folders, which is what a whole
working repository looks like rather than a folder of marketing material. This
is the backstop behind the step above and it rarely happens once the places
have been settled. Do not ask for a yes over that list. The command has already printed the sentence that
names the two numbers and the `folder=<name> count=<number>` lines that go with
it. Say that sentence and read the folders and their counts out. It is this
sentence:

That folder holds <number> files across <number> folders, most of which are probably not marketing material. Which of these folders hold your customer profiles, positioning, messaging, or plans?

When they name the folders, run the same command again with one
`--only-folder <name>` for each folder they named:

```
python3 scripts/join.py words-file --run <run identifier> --for folder
python3 scripts/join.py list-sources --folder-file <the path it printed> --run <run identifier> --only-folder <number> --only-folder <number>
```

Name the folders by the number the listing printed beside each one, as above.
A folder name is whatever somebody called their folder, and quotation marks
are not enough: a folder called Brandon's Docs breaks the command that carries
its name. A number that is not on the list is refused and nothing is shown.

Show them that shorter list, and only then ask for the yes. A name that is not
one of the folders the counts named comes back as `codes=no-such-folder` and
nothing is shown, so ask them for one of the names from the counts. Asking for
the yes over the long list is refused anyway: `freeze-sources` prints
`codes=narrow-first` and takes nothing, because a list nobody could read
through is not a list anybody can agree to.

Contact lists are left out of every list on purpose. A file of rows whose
heading names an email address, a phone number, or a social profile, or whose
rows are mostly email addresses, is counted under `left-out=contact-list` and
is never offered for reading, whatever else it looks like. Say so if they ask
where their prospect list went, and say that naming it by hand will not bring
it back either.

Before asking for their yes, say what the yes is for, in these words, because
the list can read as a list of files about to be copied somewhere, and it is
not:

To find these places I looked only at file names and the first heading of each document, and nothing else has been opened. These are the documents I would read to draft your ideal customer profile and your positioning. None of them is copied into the base or changed in any way. The base only ever gets the two drafts you approve, one at a time. Once you say yes, this list is fixed, and from that point nothing leaves this computer for the rest of this session. A file added to the folder afterwards will not be read until you are shown a new list. May I read these?

Ask it that way, as a question about reading, and never as a question about
taking or importing the files.

A document that holds a comment, a tag, or a character a reader of the file
would never see is still read. Those parts are taken out of the text and
counted, and the drafting step below prints one sentence for each document
something was taken out of. Say that sentence when it appears. Nobody has to be
told about it before it happens, because nothing is lost by it.

On a plain yes, run:

```
python3 scripts/join.py words-file --run <run identifier> --for folder
python3 scripts/join.py freeze-sources --folder-file <the path it printed> --session <session id> --run <run identifier>
```

This takes their yes against the list they were actually shown. It looks at the
folder once more first, and if anything in it has changed since the list was
shown it prints `codes=listing-changed` and refuses. That is not a failure and
you do not treat it as one. Run `list-sources` again, show them the new list,
say plainly that the folder changed while they were reading, and ask again.

From the moment the yes is taken, nothing leaves this computer for the rest of
the session, and you say so.

Pastes, PDFs, web pages, and anything a connected tool hands back are read the
way `references/reading-rules.md` sets out, with your own tools, one bounded
read each. Every one of them, including anything a connector returned, is
handed over the same way, and every piece of that text is held for the run
with:

```
python3 scripts/join.py words-file --run <run identifier> --for label
python3 scripts/join.py add-paste --run <run identifier> --label-file <the path it printed> --session <session id> --from <file you wrote it to>
```

The short label is usually taken from the name of the file it came out of, and
a file may be named anything at all, so it goes in a file the first command
hands out rather than in the command itself.

Handing text over this way is also what tells the safeguard this session has
read the person's own material, which is why the session identifier belongs on
it. From the first one, nothing leaves this computer for the rest of the
session, exactly as after a yes to a folder, and you say so.

That folder is this person's own, readable by nobody else, and it is deleted at
the closing. Nothing in it is ever written into the base. A run that stops part
way is never closed, so the next run started on a later day clears away what it
was holding.

### Step 6. The two drafts, one at a time

Say that GTM Base will now draft the first document, that they will see it
whole, and that nothing is written until they say yes. The order is fixed: the
ideal customer profile, then the positioning. (Amended 2026-09-19, r2.4 section
A: setup used to draft a third document, an entry recording something the team
had decided. It is no longer a drafted step here.)

For each step in turn, with `<step>` being `icp` and then `positioning`, start
by seeing what this one document would read:

```
python3 scripts/join.py preview --step <step> --run <run identifier>
```

This writes nothing at all. It prints `going-in=`, the number of files this
draft would read, `left-out-count=`, the number it would not, and `total=`, the
number named for this step. Then it prints the first twenty labels going in,
and one line for each file left out, with `reason=over-the-cap` when there was
no room for it and `reason=unusable:<code>` when it could not be read at all.

Say those numbers to the person in plain words and name what is being left out.
Then ask whether to draft from that or to narrow it to the files or the folder
that matter for this document. If the command prints the sentence that begins
"Your folder holds more than one draft can read at once", say that sentence as
it is written. When everything but a handful of their files would be left out,
say so plainly and suggest naming the folder that holds the documents for this
draft.

When they name files or a folder, run the preview again with `--only` or with
`--only-folder <folder>`, and show them the new numbers. Both of those narrow
the list they already agreed to and neither widens it.

`--only` takes the numbers the listing printed beside each file, separated by
commas, and nothing else: `--only 1,4,7`. It never takes a file name. A file
name is whatever somebody called their file, so writing one into a command puts
their text where a command goes, and a command line naming a file is refused
outright. A number that is not on the list is refused with
`codes=not-consented`, and the answer to that is to read the list out again and
ask which of those they mean.

Only when they have said what to draft from, build the request, carrying the
same narrowing if they gave one:

```
python3 scripts/join.py words-file --run <run identifier> --for company
python3 scripts/join.py assemble --step <step> --run <run identifier> --company-file <the path it printed> --email <their address>
```

The company file from step 4 has already been read and taken away, so this
step asks for a fresh one, and so does every step after it that needs the
name.

Add `--paste-file <path>` once for each piece of text held in step 5. The
command prints `prompt=<path>` along with the labels of what went in and what
had to be left out. Read that file and follow it: it is the request you write
the draft from. Write your draft to the file the command names as `draft=`.

Four of its other lines need something said out loud.

- Every line beginning `Left out:` names one of the person's own documents that
  could not be used at all, with the reason in brackets. Read those out. They
  named that material and they are entitled to know it did not go in.
- Every line beginning `Hidden parts removed from` names one of their own
  documents and says what was taken out of it, such as three comments in a
  template. Read it out in one sentence and carry on. The document was used,
  with those parts gone.
- `note=date-clamped` means one of the sources says it was changed on a day
  still to come, so the date recorded for it is today. Say so.
- When the command exits saying `codes=no-sources`, nothing survived and no
  request was built. Read out the lines beginning `Left out:`, say plainly that
  there was nothing left to draft from, and ask them for a shorter paste or a
  narrower folder. Do not write a draft from nothing.

Before each wait, say the line for that step, and say nothing else while the
person is waiting:

- Reading what you named.
- Drafting your ideal customer profile.
- Drafting your positioning.
- Saving that into the base.

Then check the draft before showing it:

```
python3 scripts/join.py review --step <step> --run <run identifier> --draft <draft file>
```

The draft file is the one `assemble` printed as `draft=`, and it is the only
file this step will read. A draft written anywhere else is refused, because a
step that reads any path it is handed is a step a document can point at
somebody's private notes.

It prints `ready`, or one line of `codes=` naming what it found. On any code,
write the draft again from the same request and check it again. Never show the
person a draft that has not come back ready, and never repeat a line of a
refused draft to them.

When it is ready, show them the whole document and offer the answers they
actually have.

On the first document, there are three: approve it, edit it themselves, or ask
what is wrong with it. Skipping is not one of them. A skipped document is
written into the base saying it was skipped, and until the first document is
approved there is no base to write it into. From the second document onward
there are four, with skip among them.

- **What is wrong with this?** Ask this run for a file to put their answer in
  with `python3 scripts/join.py words-file --run <run identifier> --for answer`,
  write what they said into the path it prints, and run
  `python3 scripts/join.py what-is-wrong --step <step> --run <run identifier> --answer-file <the path it printed>`.
  It prints a note. Follow the note, write the whole document again, and show
  them the new one. Their words go here and nowhere else.
- **Edit.** Take their own wording, put it in the draft file, and check it again
  with `review`.
- **Approve.** For the first document they approve, which is the one that
  creates the base:
  `python3 scripts/join.py approve --step <step> --draft <draft file> --run <run identifier> --parent <the parent from step 4> --company-file <a fresh company file>`.
  Add `--email <address>` when they gave one. For every document after it:
  `python3 scripts/join.py approve --step <step> --draft <draft file> --run <run identifier> --base <base folder>`.
  The command prints `base=` and `file=`.
  If it prints the sentence saying GTM Base needs their work email address,
  this computer has no address recorded on it. Ask them for the address they
  work under, then run the same approve again with `--email <address>`.
  Nothing was written, so nothing has to be undone.
- **Skip**, from the second document onward.
  `python3 scripts/join.py skip --step <step> --base <base folder>`.
  Say plainly that a skipped document is written down as skipped and that the
  next session will offer to finish it.

If a draft cannot be read back at all, go back to the same step and write it
again. Do not move on to the next document and do not ask the person to fix it.

### Step 7. The one question about what changed
<!-- step -->

The base now holds two documents and nothing about what has moved since they
were written, so this step is where anything that has already made one of them
out of date will be recorded. Run:

```
python3 scripts/join.py closing-question
```

It prints three sentences, one example, and the request. Say all of it, in the
words it printed, and add nothing:

<!-- ask -->
Tell me if anything about the context of the business changed that we should account for. One sentence is enough, or say skip.
<!-- end ask -->

Skip is a whole answer and it is not a failure. When they say skip, run
`python3 scripts/join.py skip-change --base <base folder>`, say the one
sentence it prints, and go to step 10. Nothing is written into the base and
nothing else is asked.

### Step 8. The change, as it would be written down
<!-- step -->

What they just said is not a context change until they have read the whole of
what GTM Base would write down from it, because the day it happened, the
documents it affects, and the day it will come back are all worked out rather
than given. Build the request the same way every other draft is built, which is
also what names the file the draft goes in:

```
python3 scripts/join.py words-file --run <run identifier> --for company
python3 scripts/join.py assemble --step change-entry --run <run identifier> --company-file <the path it printed> --email <their address>
```

It prints `prompt=` and `draft=`. Write the change from
`references/prompts/draft-change-entry.md` into the file it named as `draft=`,
which is the only place this step will read one from, check it with
`review --step change-entry --run <run identifier> --draft <draft file>`, and
then run:

```
python3 scripts/join.py preview-change --draft <draft file> --run <run identifier> --base <base folder>
```

The base has to be on that command. Without it the preview cannot finish the
change off, and what it shows is not what approving writes.

It prints the four lines first, which is what you show:

<!-- change -->
What changed: We stopped selling to companies under twenty people.
Why: The last four of them took the longest to close and left the soonest.
What it affects: your customer profile, your positioning
When to look again: 2026-12-19
<!-- end change -->

Then it prints the three things that are theirs to correct, one per line: the
day it happened, which documents it affects, and when to look at it again. Who
noted the change is not one of them, and the command prints the sentence
saying why, so read that out too. Then comes the whole change, exactly as it
would be written down, between these two markers:

<!-- artifact -->
The whole change, settings and all, as `preview-change` printed it.
<!-- end artifact -->

<!-- ask -->
Approve this, correct anything in it, skip it, or say what is wrong with it.
<!-- end ask -->

The four answers work exactly as they do in step 6. A correction goes back
through `review` and `preview-change` before it is shown again. Approving is
`python3 scripts/join.py approve --step change-entry --draft <draft file> --run <run identifier> --base <base folder>`.

### Step 9. Whether each document already says it
<!-- step -->

Approving the change says what happened, and it does not say whether either
document has caught up with it, so that will be asked here rather than assumed.
Run:

```
python3 scripts/join.py reconcile --base <base folder> --entry <the id the approve printed>
```

It prints one line per document to ask about, and one line saying how many
other documents are left flagged for the review. Ask about one document at a
time, never two in one breath, in the order it printed them:

<!-- ask -->
Does your customer profile already say what that change says?
<!-- end ask -->

Record each answer on its own, and say the one sentence it prints. A yes is:

```
python3 scripts/join.py reconcile-answer --base <base folder> --entry <id> --file <the path it printed> --answer yes
```

A no is the same command with the other answer:

```
python3 scripts/join.py reconcile-answer --base <base folder> --entry <id> --file <the path it printed> --answer no
```

- **Yes** writes down that the document already says it, naming that one change.
- **No** leaves the document flagged and prepares a change for it. Setting a
  base up never edits a file it has already written, so the prepared change
  waits for them to approve it.

What a "no" prepares is a note asking you for the real wording rather than the
wording, and it is not approvable while it is still that.

1. Read the document and the change, and write what that part of the document
   should say now, in the document's own voice.
2. Ask for somewhere to put it with
   `python3 ../propose-change/scripts/approve_local.py --new-words-file answer`,
   which prints `words=<path>`, and write your wording into that path.
3. If the prepared change does not already say which part of the document it
   is about, list the parts with
   `python3 ../propose-change/scripts/approve_local.py --staging <path> --sections`,
   read them out, and ask which one this is about. It prints one numbered line
   for each part.
4. Write it in. When you asked which part it is about, name that part:

   ```
   python3 ../propose-change/scripts/approve_local.py --staging <path> --wording --words <the path it printed> --section <number>
   ```

   When the prepared change already says which part it is about, leave the
   part off:

   ```
   python3 ../propose-change/scripts/approve_local.py --staging <path> --wording --words <the path it printed>
   ```

   Wording that is the note over again is refused, and so is a file this skill
   did not hand out.
5. Show them what that part says today and what it would say instead, in that
   order, both in full.
6. Ask whether to approve it. Asking before the wording is written in is
   refused, because the prepared change carries a marker saying it is still a
   first draft and only the command above takes that marker off.

### Step 10. The closing
<!-- step -->

This is where GTM Base will look at the base as a whole and tell them one true
thing about it, and say where the base is and how to come back to it. Before
running it, say that what they say about setting up is saved into the base
itself so the next session can see it.

<!-- ask -->
Did anything get in the way while you were setting this up?
<!-- end ask -->

```
python3 scripts/join.py close --base <base folder> --run <run identifier>
```

Add `--got-in-the-way-file <path to their words>` when they said something.

- The command prints the finding first and then the closing message. Say both,
  in that order, in the words it printed, and add nothing to them.
- `references/closing-rules.md` holds the order the finding is worked out in,
  the rule that it never claims more than the dates show, and both messages.
- When the base was linked to a folder, the closing message names both
  folders. It says to open the folder they named and that the base will be
  there, and it gives the base's own folder as well.
- Say it exactly as printed. Which of the two messages is right depends on
  whether a folder was linked, and the command has already worked that out.

## Linking a folder

Three sentences reach this skill at any time, from any session, and each one is
one command. None of them needs a base to be open in the session, which matters,
because the folder somebody wants to link is their own folder and is not a base.

Say "link this folder to my base", ask for somewhere to put the folder with
`python3 scripts/join.py words-file --base <base folder or company name> --for folder`,
write the folder into the path it prints, and run
`python3 scripts/join.py link --base <base folder or company name> --folder-file <the path it printed>`,
using the folder they are working in when they did not name one. The base can be
named by its folder or by the company it is for, so "link this folder to my Acme
base" is enough, and `--base` can be left off altogether when there is only one
base on the computer. When there is more than one and they named none, the
command names the ones it could have meant and changes nothing, so ask which.
It refuses a folder that already belongs with another base and names that base, a
folder that is a base or sits inside one, and a folder that is not on the
computer.

Say "unlink this folder from my base" and run
`python3 scripts/join.py unlink --base <base folder or company name>`. The base
itself is not touched, and it still opens in its own folder.

Say "show my linked folders" and run `python3 scripts/join.py links`, which
prints one line per base with its name, its own folder, and the folder it belongs
with, or `none`. Run this whenever a name they gave was not found, and show them
the list so they can name one from it.

## What this release does not do yet

Three things reach this skill and are answered with one sentence each, said
once, with no apology.

- `python3 scripts/join.py backup` for keeping a copy of the base somewhere off
  this computer.
- `python3 scripts/join.py invite` for putting somebody else on the base.
- `python3 scripts/join.py join-link` for joining a base somebody sent a link
  to.

Each prints the sentence to say. In a session that has already read the
person's own documents, the sentence says instead that nothing leaves this
computer until the session ends, which is the same rule they agreed to in step
5.

## When they say not now

If the person answers the setup offer with "not now", run:

```
python3 scripts/join.py not-now
```

It writes their answer down and prints one sentence. Say that sentence and
nothing more.
