This is how one context change is shown to a person: four labeled lines, in
this order, and nothing else. The markers around it say where the change starts
and stops, so the lint can find it and so nothing else in the reply gets
mistaken for part of it. The markers do not show up when the document is read.

The example below is filled in so the shape is obvious. Replace the four values
and keep the four labels exactly as they are.

<!-- change -->
What changed: We stopped selling to companies under twenty people.
Why: The last four of them took the longest to close and left the soonest.
What it affects: your customer profile, your positioning
When to look again: 2026-12-19
<!-- end change -->

The value after "What it affects" is the name a person reads, never a file
path. The value after "When to look again" is a date. The identifier of the
change belongs in the machine-readable record and never in these four lines.
