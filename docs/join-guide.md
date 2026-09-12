# Joining GTM Base

Status: as of version 0.2.5 the offer, setting a base up, and linking a base to
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

If you want to back the base up somewhere safe, or invite a teammate into it,
you also need a GitHub account and the GitHub command line tool. You can add
both later, and nothing asks you for them until the moment you want to back up
or invite.

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

Name the narrowest folder you can. The folder you want is the one holding your
customer profiles, your positioning, your messaging, and your plans, rather than
a whole company folder or a whole project folder that happens to have some
marketing material somewhere inside it. If you do name a large folder, you are
not asked to say yes to all of it. GTM Base tells you how many files it found
and which folders they sit in, asks you which of those folders hold the
marketing material, and then shows you the list for just those folders before
anything is read.

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
the narrowest folder you can, the one that holds your customer profiles,
positioning, messaging, and plans. If the folder you name turns out to be large
and spread across several folders, you are asked which of those folders hold the
marketing material before you are asked to say yes to anything, because a list
of a hundred and fifty files offered for one yes is a list nobody can really
read. Lists of people are left out on purpose. A file of rows holding email
addresses or phone numbers, which is what a prospect list looks like, is never
offered for reading and cannot be named back in, because that is other people's
personal information rather than a document about your business. Before
each of the three drafts you are shown what that draft will read and what it
will leave out, and you can narrow it to the files or the folder that matter for
that one document, which is worth doing when the folder you named is large. It
then drafts three things for you, which are your ideal customer profile, one
entry recording a real decision your team made, and your positioning. You read each
draft as a whole document and either approve it, edit it, or skip it. Nothing is
saved until you approve it, and you can stop at any point and pick up where you
left off.

At the end you get one real finding about your own context rather than a
congratulations message. If nothing is out of date yet, it says so and tells you
the date it will start watching.

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
the folder that contains it.

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
