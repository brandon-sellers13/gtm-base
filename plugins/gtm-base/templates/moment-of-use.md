<!-- What GTM Base says at the one moment it speaks up on its own, written out
     here so the words can be read in one place. The check in
     `lib/gtmbase/moment.py` says these same sentences, and a test holds the
     two against each other so they cannot drift apart. -->

# The moment a document is about to be used
<!-- step -->

This is what GTM Base says when somebody is about to use a document that a
recorded context change has overtaken, which is the one thing it ever raises on
its own. It says which document, which change, and the day the change happened,
and then it asks which of the three answers the person wants.

The first two sentences, in this order:

- `%s has not caught up with a context change that was recorded on %s.`
- Then one of these two, and never both. `A change for it is already prepared
  and is waiting for you to approve it.` when a prepared change for that
  document really is waiting. `No change for it is prepared yet, and GTM Base
  can prepare one now.` when none is.

Then the change itself, as the four labeled lines and nothing else:

<!-- change -->
What changed: We stopped selling to companies under twenty people.
Why: The last four of them took the longest to close and left the soonest.
What it affects: your customer profile, your positioning
When to look again: 2026-12-19
<!-- end change -->

Then the one thing the person is asked:

<!-- ask -->
Use it as it stands, fix it first, or tell GTM Base it already reflects this
change?
<!-- end ask -->

## What each of the three answers does

Each answer is said once, here, rather than once for every document.

| The answer | What it does |
|---|---|
| Use it as it stands | The work carries on with the document as it is. Nothing is written and the document stays flagged, because permission to use a document that is behind is not a statement that it is right. |
| Fix it first | The change for that document is prepared, and the work waits until its owner approves it in their own copy of the base or chooses otherwise. |
| It already reflects this change | One confirmation line is written, naming the change, by the one script allowed to write one. The document is no longer flagged against that change. |
