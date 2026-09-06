---
kind: map
owner: owner@example.com
last_confirmed: 2026-01-01
sources: []
status: draft
---

# Map

## Settings

confirmation_threshold_days: 30
not_now_days: 7

## Where things live

The `context` folder holds everything the AI reads for meaning, with strategy
documents in `context/strategy`, numbers and their definitions in
`context/metrics`, goals and targets in `context/plan`, and your own working
notes in `context/notes`. The `work` folder holds the record of how the base
stays current, with one dated entry per decision in `work/decisions` and the
owner's confirmations in `work/confirmations`. The `corrections` folder holds
what each run found wrong and which rule changed because of it.
