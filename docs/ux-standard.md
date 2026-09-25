---
title: "The UX standard: how a step reads"
type: reference
status: active
date: 2026-09-19
plan: docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md
unit: "Unit 1.1b: The UX standard and the lint that holds it"
---

# The UX standard

This is the standard every step of every GTM Base skill is written to. It is
one page because a standard nobody rereads is not a standard. Requirement P28
of the plan is the source, and the six rulings in
`docs/plans/2026-09-19-001-acceptance-matrix.md` are how it applies to the six
steps that break it worst today.

## The shape of a step

A step does four things, in this order.

1. It says what it is for, in one sentence, before it tells anybody to do
   anything.
2. It shows something that can be read in a few seconds. That means a short
   list or a small table, and it never means paragraphs of evidence.
3. It ties what it showed back to why the person is here.
4. It asks for one thing.

A step that asks for nothing is allowed, because some steps exist only to tell
somebody something before they are asked to approve anything. A step that asks
for two things is not allowed. Split it.

## The four-line form for a context change

A context change shown to a person is four labeled lines, in this order, and
nothing else.

<!-- change -->
What changed: We stopped selling to companies under twenty people.
Why: The last four of them took the longest to close and left the soonest.
What it affects: your customer profile, your positioning
When to look again: 2026-12-19
<!-- end change -->

`plugins/gtm-base/templates/change-four-lines.md` holds this form as a template
so no step has to remember it. The word for what the base tracks is "context
change" everywhere a person reads it.

## The words, and the two that are gone

What the base tracks is a **context change**: anything that happened that makes
a document in the base no longer true. It may be something the team settled, and
it may equally be a competitor's launch, a price change, or something learned
about how customers describe the problem. In running text it may be shortened to
"change" once the full term has been used in that text, and never before.

Two words are banned from anything a person reads, and `tests/plain_language.py`
checks for both in their ordinary forms, alongside the version-control words
that were already banned:

| Banned | Why | Say instead |
|---|---|---|
| `decision`, `decisions` | Too narrow for what the base tracks, and the live setup run needed three explanations of it before it was understood. Most of what makes a document wrong is not something anybody decided. | context change, and then change |
| `ledger`, `ledgers` | A bookkeeping word for a folder of dated notes. Nobody outside this code ever called it that. | the record of context changes, or name the folder, `work/changes` |

The check has three deliberate exceptions, each of them a name somebody else
owns rather than ours. The folder path `work/decisions`, which a base set up
before the rename really holds and a person may have to look in. The settings
block at the top of a file, and any settings block shown inside an example,
where values such as `origin` and `mode` come from fixed vocabularies recorded
in every base that already exists and cannot be spelled differently now. And
the client's own tool-use interface, which calls the answer it returns a
permission decision and spells its fields that way, so a file explaining what
it does with them has to write the name it was given.

The settings inside an entry read the same way. `happened_on` is the day the
change happened, and `noted_by` is whoever wrote it down, because there is not
always somebody who decided it.

A sentence that says something went wrong names the document. "You have
unsaved edits" sends somebody looking through their whole base; "there are
words in this file that you have not saved" sends them to the file. Every
refusal that knows which file it means says which file it means.

An offer names no path. A person is offered a thing that happens to their
base, not a folder it happens to. "Your context changes are stored the old
way" is the offer; the folder it moves them into is GTM Base's business.

## The short wrapper and the complete artifact

Two rules that look like they contradict each other both hold, and this is how.

The **wrapper** is what a person is shown in the conversation. It is short,
readable at a glance, and the readable-in-seconds rule applies to it. For an
adopted document the wrapper says what was removed, shows the opening lines,
and says where the whole cleaned file is.

The **artifact** is the complete thing a person approves: a whole cleaned
document, a whole prepared change. It is written out in full, it can be read in
full before any answer is given, and the yes is bound to exactly those bytes.
The readable-in-seconds rule does not apply to it, because the whole point of
an artifact is that nothing was hidden.

So "shown whole" is true of the artifact and "never paragraphs" is true of the
wrapper, and there was never a real conflict between them.

## Human names

A document is called what a person calls it, never what the file system calls
it. "Your customer profile", never `context/strategy/icp.md`. A change is
called by its first line and the day it happened, never by its identifier.
`plugins/gtm-base/lib/gtmbase/names.py` is the one place that does this, so a
name cannot drift between one step and the next. Paths and identifiers stay in
the machine-readable lines, which nobody reads aloud.

## CLASS: the framework every step ties back to

Adopted 2026-09-25 from Brandon's AI-native framework (MICW Issue #4, v10), replacing the draft four questions of 2026-09-19. The plugin and the newsletter use one framework, so a person who read the article recognises every part of the product. The name is subject to the trademark check the article lists as open.

| Part | The question it answers | Where it lives in a base | What GTM Base does about it |
|---|---|---|---|
| **Context** | What is true about the business? | `context/` | Holds the core files, each with an owner and a date it was last confirmed. |
| **Learning** | How do the other parts get better? | `learning/` | Records each context change and each approved fix, proposes the fix to what a change overtook, and applies nothing without the owner's yes. Lessons from results arrive with the first reporting skill. |
| **Access** | Can the AI reach the tools the job needs? | `access/stack.md` | Maps where each source lives, what reads it, and where each output is written. The connections themselves belong to the tools, and no credential ever sits in a base. |
| **Skills** | How does the work get done? | `skills/` | Later. The folder exists and is refused until the team has settled who may approve a skill change. A skill points to the context and the standard and holds neither. |
| **Standard** | What does good look like, and what needs approval? | `standards/` and `work/` | The approval half now: the AI proposes and a person approves, through `work/`. Each job's goal and checks live in `standards/`. |

Every step says which part it serves, in plain words, when that helps the person understand why they are being asked. No lint check reads this section; it governs wording, and Brandon's reading aloud is its test.

## The lint is a floor

`tests/plain_language.py` holds four mechanical checks on top of the banned
words and the long dashes. They are a floor and nothing more. They can tell
that a step opened with an order instead of a purpose; they cannot tell whether
the purpose sentence means anything. An agent building to a green lint will
satisfy "opens with a purpose sentence" with boilerplate, and the lint will not
notice.

**The acceptance test for this standard is Brandon reading the steps aloud.**
He should be able to read three steps he has never seen and say, in one
sentence each, what the step is for and what it is asking him. That is the bar.
A green lint is the price of admission, not the verdict.

## What the four checks actually check

Checks one, two and three read a step section. A step section is a heading
whose title begins with the word "Step", or any section carrying the marker
`<!-- step -->` on the line under its heading. A section nobody marked is not
checked, so a later unit opts its own rewritten step in by marking it. Check
four reads any change block, wherever it appears.

| Check | What it does | What it cannot do |
|---|---|---|
| purpose | Reads the first paragraph under the step's heading and fails when the first sentence is an order rather than a statement. | Tell whether the statement says anything useful. |
| one-request | Counts the blocks marked `<!-- ask -->` and fails when a step holds more than one. A request may be a question or an imperative, which is why nothing counts question marks. | Notice a second request somebody wrote outside an ask block. |
| prose | Counts a run of plain prose lines and fails over five. A list, a table, an ask block, and an artifact block are not prose. | Tell a dense five lines from an airy five lines. |
| four-lines | Reads each block marked `<!-- change -->` and fails unless it is the four labels, in order, one per line. | Tell whether the four values are true. |
| the two banned words | Reads every line a person reads as prose and fails on either of the two words in the table above, in any ordinary form. | Catch the idea said in other words. |
| the full term first | Fails when a text that uses "context change" somewhere says a bare "the change" before it. | Catch a text that talks about what the base tracks and never once says the full term. That one is the read-aloud check's. |

The counting rule behind the one-request check is worth stating, because an
earlier draft of it was wrong. Revision 1 of the plan proposed counting
question marks. The closing request that requirement P4 fixes word for word,
"Tell me if anything about the context of the business changed that we should
account for. One sentence is enough, or say skip.", contains no question mark
at all, so that check would have rejected the product's own required wording.
Requests are counted as delimited blocks instead.

## The exemption list

Unit 1.1b changed no sentence anybody reads. Every text that fails one of the
four checks today is on the exemption list in `tests/plain_language.py`, and
every entry on it carries two things: the reason it fails, and the unit that
removes it. A unit rewriting a step clears its own entries as part of that
rewrite. Unit 1.8 empties whatever is left.

An entry that names no unit is not allowed. "Later" is not a unit.

## The sentences held in Python

Not every sentence a person reads lives in a document. Some of them are Python
strings, which means they were outside the lint entirely until this unit. The
registry `PYTHON_SENTENCES` in `tests/plain_language.py` lists every one of
them by module and constant name, and a test walks the library and fails on any
sentence-shaped constant that is in neither the registry nor the short list of
constants no person ever reads. That is how the registry stays honest as the
code grows.
