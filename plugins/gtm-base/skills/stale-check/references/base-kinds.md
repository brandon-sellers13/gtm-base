# The kinds of document a base can hold

This is the list the inventory reads a base against when somebody asks what
their base is missing. It is the same list, in the same order, as
`BASE_KINDS` in the plugin's settings, and a test fails if the two ever
disagree. Each section below says what the kind holds, where a base keeps it,
whether each business the base covers needs its own, and whether GTM Base can
draft it yet.

A base that covers more than one business lists them in its map. A document
belongs to the business of the folder it sits in under `context`, such as
`context/courier-app/goals.md`, or to the business its own settings name with
a `business:` line. A document kept flat in `context` that names no business
counts for no business when the kind differs by business, and the inventory
lists it once so the owner can say which. A base whose map lists no business
is read for the whole company, exactly as before.

The messaging, the voice guide, the buyer personas and the product can be
drafted on request from material the person names, or taken in as they stand
when a finished one exists. The source map's rows can be drafted from what the
person says. Units 2.4a and 3.5 of Plan 1 make the goals, the metric
definitions and a standard draftable in their own release, and until then the
inventory says drafting arrives later for the rest.

A context change recorded against one document usually makes others out of
date too. Each kind below that has one says what overtakes it, and the line
"Usually also overtakes" names the kinds GTM Base suggests alongside it when a
change is recorded. Those are suggestions only: the person chooses every
document a change affects, and nothing is flagged that they did not choose. A
test holds these lines and the table in the plugin's settings in step.

## Goals (`goals`)

What the business is trying to reach, each as a figure the owner stated, with
its unit and where its actual value is measured. Kept at `context/goals.md`,
or in a business's folder. Each business has its own.

Overtaken by a change of plan: a new quarter, a board reset, a budget
change, or a target moved.

Usually also overtakes: standards (only a standard whose own sources name the goals).

## Product (`product`)

What the business sells, in its own words, with what has shipped kept apart
from what is planned, and a pointer to where pricing lives rather than the
prices themselves. Kept at `context/product.md`, or in a business's folder.
Each business has its own. GTM Base can draft it, or take in a finished one.

Overtaken when a feature ships or is dropped, a plan or price changes, or
something planned is cancelled.

Usually also overtakes: messaging, buyer personas.

## Customer profile (`icps`)

Who the business sells to, with one document for each segment beside it.
Kept at `context/icps.md`, or in a business's folder. Each business has its
own. Setup drafts it, and can take in a finished page for one segment as it
stands.

Overtaken when the business changes who it sells to, such as a move up-market
or a segment added or dropped.

Usually also overtakes: positioning, messaging, buyer personas.

## Buyer personas (`buyer-personas`)

Who inside each segment buys, kept apart from the segments themselves. Kept at
`context/buyer-personas.md`, or in a business's folder, and never in the
segments' folder. Each business has its own. GTM Base can draft it, or take in
a finished one.

Overtaken when a new buying role shows up in deals, or a product change brings
in a new user.

Usually also overtakes: messaging.

## Positioning (`positioning`)

How the business describes itself against the alternatives, with its
competitors folded in. Kept at `context/positioning.md`, or in a business's
folder. Each business has its own. Setup drafts it.

Overtaken when the business changes how it describes itself or which
alternatives it is compared with.

Usually also overtakes: messaging.

## Messaging (`messaging`)

What the business claims, to whom, and with what proof. Kept at
`context/messaging.md`, or in a business's folder. Each business has its own.
GTM Base can draft it, reading the profile and the positioning first, or take
in a finished one.

Overtaken when a claim changes, such as legal flagging one or a customer
withdrawing permission to be named.

Usually also overtakes: nothing else.

## Voice guide (`voice`)

How the company sounds in writing, each principle shown with a sentence quoted
from the company's own writing. Kept at `context/voice.md`. One serves the
whole company, so it needs no `business:` line, though a business may keep its
own in its folder. GTM Base can draft it, or take in a finished one.

Overtaken only by a change to the voice itself, such as a new style rule or a
word the company stops using. A strategy change does not overtake it.

Usually also overtakes: nothing else.

## Design guide (`design`)

How the company looks: colour by named role, type, and the rules for its
logo. Kept at `context/design.md`. One serves the whole company, so it needs
no `business:` line, though a business may keep its own in its folder.

Overtaken only by a change to the brand itself, such as a new logo or a
colour retired. A strategy change does not overtake it.

Usually also overtakes: nothing else.

## Metric definitions (`metrics`)

What each number the team uses counts and where it lives, such as what counts
as a trial or a paying subscriber. Kept as `metrics.md` in the context
folder, or in a business's folder. Each business has its own.

## Source map (`stack`)

For each kind of data a job needs, where it lives, which connected tool reads
it, and what to do when that tool is not connected, in one table whose rows
each say which business they are for. Kept at `access/stack.md`. One serves the
whole company. It never holds a password, a key or a token. GTM Base can draft
its rows from what the person says, and a tool nobody named is never a row.

## Standards (`standard`)

One for each job: its goal, what is unacceptable, what needs approval, the
checks before work is handed back, and how any threshold set somewhere else
relates to a goal. Kept at `standards/<job>.md`. Each serves the whole
company, and the inventory counts them rather than naming them.

## Skills (`skill`)

The written instructions for one job that uses the base. Kept at
`skills/<job>/SKILL.md`. A skill reaches the base only through GTM Base's own
install, which needs the creator's yes and the base owner's or an
administrator's, and the inventory counts what is there.

GTM Base comes with one skill, drift grade, which checks a piece of marketing
work against the customer profile, the positioning and, when the base holds
them, the messaging, the voice guide, the competitors and the buyer
personas. The inventory offers it once a base holds a customer profile and a
positioning and does not have it yet. It is installed with its standard,
`standards/drift-grade.md`, and the base owns both from then on.
