# Joining GTM Base

Status: as of version 0.2.6 the offer, setting a base up, and linking a base to
the folder your material lives in are all live.
Backing a base up somewhere off your computer, inviting a teammate, and joining
a base from a link arrive with the next release, so those sections below
describe what is coming rather than what works today. This guide is updated as
each piece lands.

## What you need before you start

You need Claude Code installed and working. On a Mac you also need the Apple
developer tools, which you can install by running `xcode-select --install` in
your terminal and following the prompt. You only need those two things to set up
a base for yourself and use it on your own computer.

Keep Claude Code up to date if you can. One thing GTM Base does needs a recent
version: as a document from your base is read, GTM Base checks whether a
context change you recorded has already overtaken it, and says so before that
document gets used for anything. Carrying that answer back is something Claude
Code gained in a release of its own, so on an older version the check simply
says nothing and everything else works exactly as described here. What holds either way is the
instruction GTM Base gives the assistant to run the same check itself, and an
instruction is followed most of the time rather than every time.

If you want to back the base up somewhere safe, or invite a teammate into it,
you also need a GitHub account and the GitHub command line tool. You can add
both later, and nothing asks you for them until the moment you want to back up
or invite.

Before you invite a second person, everybody who will open that base has to be
on the current version of GTM Base. A base set up by an earlier version is laid
out the older way, and when you ask GTM Base to review your base it offers once
to move it to the current layout, which is described under "What your base
holds" below. That one move takes the base all the way, whichever earlier
version set it up. Somebody running an older version reads a moved base as
though it held nothing, so it would tell them nothing in their base is out of
date at a moment when things really are. Updating everybody first costs nothing
and avoids that entirely.

On a base nobody else can reach, GTM Base simply offers. On a base that has a
copy other people could reach, it does not offer at all: it tells you the
condition instead and waits for you to say that everyone is on the current
version. Either way nothing is touched until you say so, and if you say not
now it stops asking for a month.

You can see exactly where you stand before deciding anything. Ask for a check
of the move and GTM Base says what it would do and how many of your documents,
context changes, and records it would move, and when it would not offer the
move, it says why. That reads your base and writes nothing, so it is safe to
run whenever you like. If anything in your base would stop the move, it names the file rather
than the problem in general, so you know where to look. The move never
overwrites anything: if a second copy of a document already sits where the
move would put it, and the two say different things, it stops and asks you
which one is right.

If an update ever stops partway, nothing is lost and nothing is left in a
state only GTM Base understands. It either finishes where it stopped or puts
back what it had done, and it will not take away a copy of anything unless it
has confirmed another copy is there. If it cannot do either, it says so, keeps
its note, and leaves your base alone until you ask again.

## Install the plugin

Run these two lines in your terminal.

```
claude plugin marketplace add brandon-sellers13/gtm-base
claude plugin install gtm-base@gtm-base
```

## Open Claude Code and answer the offer

Open Claude Code in any folder and type anything at all, even hello. The reply
opens with the offer, because the plugin has noticed that you have not set up a
base yet and is offering to make one for you. Nothing on your computer is
touched until you answer.

If you already have a folder your marketing material lives in, open Claude Code
in that one. It is the folder you will be asked about, and your base will be
linked to it afterwards, so opening it later brings the base with it. Any other
folder works too, and you can name your material folder in the conversation
instead.

Name the folder your material is in, roughly. A whole company folder is fine,
and so is a folder you keep for marketing, because you are not the one who has
to work out which folder holds what. GTM Base looks through the folder you named
and comes back with the places inside it that look like your marketing material,
naming each one with a count of what it found there, and asks you whether that
is it. You say yes, or you name a folder to add, or you name one to drop. Only
then are you shown the list of files and asked whether they may be read. Before
any of that, to find those places, GTM Base looks at the name of each file and
the first heading inside each document, and at nothing else.

If you say the base is for one part of the company, such as one product line,
or if your material plainly covers more than one part, you are asked once
which part the base is for, and you drop the places that are about another
part. Your customer profile records the answer once you approve it. If the
list you agree to holds several documents that each describe one group of
customers, you then say for each one whether to use the finished document,
draft that segment fresh, or leave it out for now, before anything is drafted.
With more than one segment, your customer profile is drafted across all of
them, one short paragraph each, and every segment you said to draft gets a
document of its own at full depth, which you read whole and approve like any
other. A segment you left out is named in the profile as still to come.

A finished document you said to use is taken into your base as it stands
rather than drafted again, and your original is never changed or moved. You
are told what was taken out of it, such as settings at its top or a comment
nobody reading it would see, you see its first lines, and the whole cleaned
document is kept where you can read it in full before you answer. Nothing is
saved until you say yes to it, and your yes is to exactly what you were
shown. A document holding an email address, a phone number, or something
shaped like a key, one whose headings a later change could not find, or one
covering more than the part of the company your base is for is not taken in,
and you are offered a draft of that segment instead. If you take that offer
and the draft is not finished before the end of setup, the segment is kept to
draft later like any other.

If a session stops while your finished documents are being taken in, even in
the middle of saving one of them, nothing is lost and nothing is saved twice.
Your list of segments and your answers are kept on this computer, outside your
base, where the end of setup does not clear them, and the next session tells
you once that taking them in stopped. Say "finish setting up my base" and
every document you already said yes to is saved without being asked about
again, unless its original changed since, in which case you see it again
first. You are then shown only the documents you had not answered for yet. A
file already sitting where a document would go is never written over, and you
are told which document that was.

A segment you chose to have drafted that was not drafted before the end of
setup is kept too, as its name and your answer, and never as your material or
a draft. The next session offers to finish it. Because reading your files
needs your yes, and that yes ended with setup, you are shown the files its
draft would read, at first only the document you named for it, and asked
again. You can add a folder or drop a file first. If that document is gone,
or you named none, you are told so and asked to name the folder that holds
its material or leave the segment out, because nothing is drafted from
nothing. The draft is shown whole and approved exactly as in setup, and a
segment you leave out is never offered again. When your customer profile
already names a segment you leave out, a change saying it is left out is
prepared for you to approve in your next review; the profile is never
rewritten without your yes.

A draft sometimes leaves a question only you can answer, marked in it where it
comes up. You are told how many there are before you read it, and you can
answer them there or approve the draft with them left open. A document with a
question still open in it is not counted as confirmed until you answer it, and
your next review of your base asks each one.

Answer in plain words in your next message. Say yes to set a base up, say that
you have an invitation link if a teammate already made a base and sent you a
link to it, or say not now if this is a bad moment.

If you say not now, the assistant writes that answer down for you and the reply
gives you back the one sentence that starts setup again whenever you are ready,
and that sentence is this one.

Say "set up my company base" whenever you are ready.

Because the answer is written down, a not now holds. After a not now, the offer
stays out of the projects you work in. It comes back only when you open Claude
Code in an empty folder or in a folder that already looks like a base, because
those are the two places where you probably do want one.

If you say anything else, such as hello or a question about your work, the reply
has three parts in this order. It opens with the offer, then gives you the one
sentence that starts setup again, then says that this can wait and turns to
what you actually asked, and the rest of the reply is the answer to your
question. The offer is made once and does not come back later in that same
session.

Until you give one of those three answers, the offer appears again at the top
of the first reply in each new session, wherever you are working. That is
deliberate. Your app shows you nothing before your first message, so an offer
you never read is an offer you were never really given.

## What setting up does

Setting up is a conversation, not a form. You are asked for your company name,
and you are told where the base will go, which is a folder kept for bases inside
your home folder. You are asked whether there is a folder of existing material
worth reading, and the folder you name there becomes the folder your base is
linked to, so you open your own folder from then on and the base comes with it.
When you name a folder of material, the assistant
reads only the documents you approve and only from the folder you named. Name
that folder roughly, because a whole company folder is fine. GTM Base looks
through the folder you named before you are shown any list of files, and
proposes the places inside it that look like your marketing material, with a
count of what it found in each one, and asks you whether that is it. You say
yes, add a folder, or drop one, and the list you are then asked about covers
only those places. If you name the folders yourself, you are shown a count of
the files in them to confirm, and you are never asked to narrow them again. That finding step looks at the name of each file and the
first heading inside each document, and at nothing else. It works this way
because a list of a hundred and fifty files offered for one yes is a list
nobody can really read, and working out which folder holds what is not a job to
hand back to you. Lists of people are left out on purpose. A file of rows holding email
addresses or phone numbers, which is what a prospect list looks like, is never
offered for reading and cannot be named back in, because that is other people's
personal information rather than a document about your business. Before
each of the two drafts you are shown what that draft will read and what it
will leave out, and you can narrow it to the files or the folder that matter for
that one document, which is worth doing when the folder you named is large. You
are asked whether to narrow it only when you said yes to the places GTM Base
proposed rather than naming your own. When a draft cannot read everything, you
are told why. When two files are versions of one document, the draft reads the
one whose name says final, or else the newer one, and you are told which one it
left out and whether the two say different things. It
then drafts two things for you, which are your ideal customer profile and your
positioning. You read each
draft as a whole document and either approve it, edit it, or skip it. Nothing is
saved until you approve it, and you can stop at any point and pick up where you
left off.

Before the very end you are asked one question about the business itself. You
are told first what a context change is, which is anything that happened that
makes a document in your base no longer true, why the base wants one, and what
it does with one, with one example. Then you are asked to say in one sentence
whether anything about the context of the business changed that the base should
account for. Saying skip is a whole answer and it writes nothing at all.

If you do give a sentence, you are shown the whole of what would be written
down before a word of it is written. That includes the day it happened, who
noted it, which documents it affects, and when it comes back for a look, and
every one of those is yours to correct. Once you approve it, you are asked
separately about each of your two documents whether that document already says
what the change says. Saying yes writes that down against that one change.
Saying no leaves the document flagged and prepares a change for it, which waits
for you to approve it, because setting up never edits a document it has already
written for you.

At the end you get one real finding about your own context rather than a
congratulations message. When your base is brand new and you recorded nothing,
that finding is three short lines: what you confirmed and when, that nothing is
recorded yet to check either document against, and when the base will ask you
about them again. Once you have recorded something that changed, the finding
tells you instead whether a document is now behind it.

## What your base holds

Your base is laid out by the five parts of the CLASS framework, so anyone who
knows the framework can open it and find each part by the name of its folder.

| Folder | What it holds |
|---|---|
| `context` | What is true about the business, one file for each subject: your goals, your product, your ideal customer profiles, your buyer personas, your positioning, your messaging, your voice, your design, and your metric definitions. Each customer segment gets its own file in `context/icps`. Setting a base up writes the first two of those, the ideal customer profile and the positioning, and the rest arrive later when you ask for them. |
| `learning` | How the base gets better: one dated entry for each context change, and a record of what each approved fix changed and why. A third folder is kept for lessons from results, which arrive later. |
| `access` | The source map, which says where your material lives, which tools read it, and where finished work is saved. It never holds a password, a key, or a token. |
| `skills` | Kept empty for now. Until your team has settled who may approve a change to a skill, GTM Base refuses any file put there, however it arrives. |
| `standards` | What good work looks like for each job, and what needs approval before it is used. |
| `work` | The approvals: your confirmations that a document is still right, the notes you drop in for the assistant to read, and the changes being prepared for you. |

## Where the base lives

Your base lives in a folder called `gtm-base`, inside a folder named for your
company, inside a folder called `GTM Bases` in your home folder. So a company
called Acme gets `~/GTM Bases/Acme/gtm-base`. Every base goes there, and there
is one folder per company.

It goes there rather than into the folder your marketing material is already in,
for two reasons. A folder you already work in is often a folder another tool
already keeps a history for, and a base built inside one of those gets tangled
up with it. It is also often a folder some other program copies to the internet
on its own, and your base holds raw notes and the context you approved, which
should not leave your computer that way. GTM Base refuses those places rather
than warning you about them, because a warning does not stop an upload.

If you would rather have the base sit beside your material anyway, say so and it
will, as long as the folder you name passes the same checks.

You do not have to remember where the base is in order to use it. When you set
the base up you name the folder your marketing material lives in, and the base
is linked to that folder. From then on, opening Claude Code in your own folder
brings the base with it: the map, the one question for the day, and anything a
teammate changed. Opening the base's own folder works too, and so does opening
the folder that contains it. Restarting your computer does not disconnect the
two.

Each session opened there also starts knowing where your base is and which
documents it holds, and it is told to read them, and to check each one against
the context changes you recorded before using it, whenever you ask for
something about who you sell to, what you say, or how you say it. Outside GTM
Base's own skills that check is best effort. The assistant is told to run it,
and a second check catches a document as it is opened, but nothing can make an
assistant open your documents for a request that does not seem to need them.
Naming the document in your request, as in "read my customer profile, then
draft the email", is the sure way.

Three things you can say about that link at any time:

1. Say "link this folder to my base" while you are in the folder you want to
   connect. If you have more than one base, name the company it is for, as in
   "link this folder to my Acme base". If another base already belongs with that
   folder, you are told which one, because a folder can belong with only one
   base.
2. Say "unlink this folder from my base" to disconnect them. The base itself is
   untouched, and you can still open it in its own folder.
3. Say "show my linked folders" to see every base on this computer, its name,
   and the folder each one belongs with.

If you rename or move the folder your material is in, the link follows it and
nothing is needed from you. If you delete that folder and make a new one with
the same name, GTM Base can tell the two apart and will ask you to connect the
new one, because a folder that happens to have the same name is not the folder
you connected. The same thing happens when the folder is on an external disk
that comes back looking like a different disk.

The link is a record GTM Base keeps for itself, on this computer only. It never
puts anything in your folder, it never changes anything in it, and connecting a
folder does not give GTM Base permission to read your documents again. The
documents it read while you were setting the base up were read once, from the
list you agreed to, and that list ended when the session did.

## Your work email address

The base records one work email address for you, and it records it inside the
base only. It never changes the email settings you use for anything else on your
computer.

That address is how the base knows a confirmation is really yours. When a file
is getting old and you are asked whether it is still right, your yes counts as
the owner's yes only when the change carrying it comes from that address. If you
answer from a different address, the file is still treated as unconfirmed, so it
is worth getting this right at the start.

## What ownership actually means

On a free GitHub account, ownership is a convention the plugin asks everyone to
follow rather than a rule the service enforces. The plugin records who owns each
file and asks the right person, and everyone on the team can see the record, but
nothing stops a teammate from saving a change that names the owner's address.
Treat the yes rate on a free account as self-reported.

On a paid GitHub plan you can require that the owner reviews changes to the
files they own before those changes are accepted, which turns the same
convention into something the service enforces. If your team cares about that,
this is the reason to be on a paid plan.

## What the safety check cannot catch

Before anything leaves your computer, a check reads the outgoing content and
stops it if it finds an email address, a phone number, something shaped like a
key or a token, a link to a shared document, or a path from inside your own home
folder. It runs in two places, once inside Claude Code and once inside the base
itself.

There are two ways around it and you should know both. A desktop app that sends
your changes for you may not run the check inside the base, so content can leave
without being read. A tool that writes to GitHub directly through its web
interface or its programming interface never touches your computer at all, so
neither layer of the check ever sees it. Use the terminal or Claude Code for
anything you want checked.

The first time a base is backed up, you will be asked to look over what is
about to leave your computer. That look was planned for a base holding two or
three documents, and a base that took in a dozen finished segment pages holds
far more than anybody can read through in one sitting. So that first look is
being redesigned for a base with many files before backing up arrives, and
backing up does not ship until it is.

## Removing someone's access

If you remove a teammate from the base, they stop getting anything new. What
they already have stays where it is, because every person working on a base has
a full copy of it on their own laptop, and nothing you do afterward reaches that
copy. The same is true of their AI assistant, which may still hold the text of
past sessions in its own history. Removing access is the right first step and it
is not a recall.

## Keeping the plugin version fixed

Your base carries a small settings file that says which marketplace the plugin
comes from and names one exact version of it. That is deliberate, so that
everyone on the team runs the same version and nobody is upgraded without
noticing.

It also means upgrades are not automatic. When there is a new version, you get a
new settings file and put it in place yourself. The fixed version protects you
from a different marketplace pretending to be this one. It does not protect you
from a problem in this marketplace itself, so it is worth knowing where the
plugin comes from and trusting the person who publishes it.
