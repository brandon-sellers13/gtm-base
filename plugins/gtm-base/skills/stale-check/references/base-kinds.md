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

Nothing on this list can be drafted from the inventory yet. Units 2.4a and 3.5
of Plan 1 make the goals, the metric definitions and a standard draftable, and
Unit 2.5a's prompt does the same for rows of the source map, each in its own
release. Until then the inventory says drafting arrives later.

## Goals (`goals`)

What the business is trying to reach, each as a figure the owner stated, with
its unit and where its actual value is measured. Kept at `context/goals.md`,
or in a business's folder. Each business has its own.

## Product (`product`)

What the business sells, in its own words. Kept at `context/product.md`, or in
a business's folder. Each business has its own.

## Customer profile (`icps`)

Who the business sells to, with one document for each segment beside it.
Kept at `context/icps.md`, or in a business's folder. Each business has its
own. Setup drafts it, and can take in a finished page for one segment as it
stands.

## Buyer personas (`buyer-personas`)

Who inside each segment buys, kept apart from the segments themselves. Kept at
`context/buyer-personas.md`, or in a business's folder. Each business has its
own.

## Positioning (`positioning`)

How the business describes itself against the alternatives, with its
competitors folded in. Kept at `context/positioning.md`, or in a business's
folder. Each business has its own. Setup drafts it.

## Messaging (`messaging`)

What the business claims, to whom, and with what proof. Kept at
`context/messaging.md`, or in a business's folder. Each business has its own.

## Voice guide (`voice`)

How the company sounds in writing. Kept at `context/voice.md`. One serves the
whole company, so it needs no `business:` line, though a business may keep its
own in its folder.

## Design guide (`design`)

How the company looks: colour by named role, type, and the rules for its
logo. Kept at `context/design.md`. One serves the whole company, so it needs
no `business:` line, though a business may keep its own in its folder.

## Metric definitions (`metrics`)

What each number the team uses counts and where it lives, such as what counts
as a trial or a paying subscriber. Kept as `metrics.md` in the context
folder, or in a business's folder. Each business has its own.

## Source map (`stack`)

For each kind of data a job needs, where it lives, which connected tool reads
it, and what to do when that tool is not connected, in one table whose rows
each say which business they are for. Kept at `access/stack.md`. One serves the
whole company. It never holds a password, a key or a token.

## Standards (`standard`)

One for each job: its goal, what is unacceptable, what needs approval, the
checks before work is handed back, and how any threshold set somewhere else
relates to a goal. Kept at `standards/<job>.md`. Each serves the whole
company, and the inventory counts them rather than naming them.

## Skills (`skill`)

The written instructions for one job that uses the base. Kept at
`skills/<job>/SKILL.md`. The skills folder stays closed until the
company-skills brainstorm is signed and Plan 1's Unit 4.2b opens it, so for
now the inventory only counts what is there.
