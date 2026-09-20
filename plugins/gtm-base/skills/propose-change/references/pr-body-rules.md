# What the text of a proposal has to say

The text of a proposal is the single thing everybody reads. The assistant shows
it, the GitHub page shows it, and the hosted view planned for later shows the
same text again without changing a word of it. Nothing is rendered from
anywhere else, so anything a reviewer needs has to be in here.

A proposal carries an edit to one document and, where there is one, the context
change behind that edit. Below, the edit is called a change, and the context
change is named in full wherever the two could be confused.

## The parts, in this order

1. **What changed.** One line starting `Before:` and one line starting `After:`,
   both in plain words. Not the file as it stands, but what it says now and what
   it would say.
2. **Why.** The reason the change is being proposed at all.
3. **Evidence.** The quoted source, already stripped of names and contact
   details, or the source the person stated when they made the change by hand.
4. **Confidence.** One of low, medium, or high.
5. **Rule being changed.** The rule this would change, or `None`. A change to a
   rule, a threshold, a definition, or a customer boundary is never shown to a
   reviewer alongside anything else.
6. **About this proposal.** Two fixed sentences: that an assistant drafted it
   from the evidence above and that no person has reviewed it yet, and that the
   reviewer can keep the context change and drop the edit.

The last line of the text is the marker. It reads
`gtm-base proposal <proposal id> entry <change id> source <source id>`, with a
single dash standing in wherever there is no context change or no source.

## The marker is visible text, never a hidden note

It is written as an ordinary line that a reader can see. Hidden text is refused
by the check that reads everything before it leaves the computer, so a marker
written as a hidden note would refuse every proposal GTM Base writes. It is also
what a later run searches for to find out whether this exact change has already
been raised, accepted, or turned down, so it has to survive being copied from
one place to another as plain text.

## The hash of what changed

The record of what changed carries one hash, and there is only one rule for it.
Take every path in the `context` folder that the record itself lists in
`touched_paths`, in the order it lists them. Read each of those files as the
change leaves them. Put the texts end to end, one after another, and hash the
result with line endings made uniform first. That single value is the hash.

The record lists the files the proposal edits in that same order, followed by
the context change it carries and anything else it adds. Those other files, and the
record itself, are not part of the hash, because only files in the `context`
folder count.

Anybody can work the hash out again from the change alone, which is the point.
The step that decides whether an accepted record really does settle a context
change for a file does exactly that: it reads each of those files as the accepted
change left them, joins them in the listed order, hashes the result, and accepts
the record only when the value matches the one the record carries. A record
whose value does not match settles nothing, and it is reported.

## Naming a context change the base already holds

A proposal that carries a new context change writes that change out in full,
and the change takes the same identifier as the proposal itself. A proposal
that only brings a file in line with a change the base already holds is
different, it names that change in its marker line and quotes it in the
evidence, and it carries no change of its own, because the change is already
written down. The two cases are told apart by the identifiers. A marker whose
change identifier is the proposal's own identifier means a new context change,
and the proposal has to carry it. A marker naming any other change means one
that is already there, and the proposal must not carry a second copy of it.

## What can change after a proposal is raised, and what cannot

Fixed from the moment it is raised: the context change it carries, the
identifier of that change, the identifier of the source, the identifier of the
proposal, and the name of the line of work it sits on.

May still change: the words in the files it changes, the Before and After lines
in the text, and the "What changed" part of the record along with its hash. The
two always move together, and the record says in one added sentence that it was
edited before it was accepted, and by whom.

## Plain words only

The text is read by a marketer on a web page, not by an engineer. It never uses
the words a version-control tool uses, it never uses an em dash or an en dash,
and it never quotes a value that the check would refuse to let leave the
computer. Every sentence is a whole sentence.
