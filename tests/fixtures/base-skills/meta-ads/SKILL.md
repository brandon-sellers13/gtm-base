---
name: meta-ads
description: Check the night's ad creative tests against the base's standard and goals, and report what the engine did.
owner: owner@example.com
kind: skill
sources: []
status: draft
reads_required: []
reads_optional: [context/courier-app/goals.md, context/courier-app/metrics.md, access/stack.md]
standard: standards/meta-creative-testing.md
---

# Nightly ad creative check

This skill reports on the night's ad creative tests for the courier app. The
engine decides what is paused, promoted or left alone, using the numbers in
its own settings. This skill never decides any of that and never repeats one
of those numbers. It explains each decision against the standard and the
goals, in the standard's words.

## The order every night

1. Run the engine's nightly check exactly as `references/daily-check.md` says.
   The check always runs, even when a document the skill reads is flagged or
   missing, because its decisions come from the engine's settings.
2. Quote what was paused, promoted or fired only inside a marked engine block,
   copied line for line from the engine's summary. Never describe an action
   anywhere else.
3. Write the goal relation section: for each threshold the standard names,
   say which goal it serves, in the standard's words.

## When a document is flagged or missing

- When the goals are flagged, report that first, hold the goal relation
  section, and still report the engine check.
- When the goals or the metric definitions are missing, the goal relation
  section says which is missing and relates nothing to it.
- When the standard is missing, nothing runs: nothing is paused, promoted or
  written tonight, and the refusal is the night's report.
