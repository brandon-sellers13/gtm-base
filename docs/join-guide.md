# Joining GTM Base

Status: as of version 0.2.2 the offer and setting a base up are both live.
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

Setting up is a conversation, not a form. You are asked for your company name
and where the base should live on your computer. You are asked whether there is
a folder of existing material worth reading, and if there is, the assistant
reads only the documents you approve and only from the folder you named. It then
drafts three things for you, which are your ideal customer profile, one entry
recording a real decision your team made, and your positioning. You read each
draft as a whole document and either approve it, edit it, or skip it. Nothing is
saved until you approve it, and you can stop at any point and pick up where you
left off.

At the end you get one real finding about your own context rather than a
congratulations message. If nothing is out of date yet, it says so and tells you
the date it will start watching.

## Where the base lives

Your base lives in its own folder called `gtm-base`, inside the company folder
you chose. The plugin is active when you open Claude Code in that folder, and
also when you open Claude Code in the folder that contains it, so you can keep
your other company material beside the base and everything still works.

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
