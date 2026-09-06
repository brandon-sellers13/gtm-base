---
schema: 1
staging_id: stg-0000000000000000
origin: ledger
source_id: src-000000000000000000000000
intake_path: ledger
target_paths: [context/strategy/icp.md]
sequence: 0
rule_change: false
confidence: high
third_party: false
---

## Decision

```text
---
id: stg-0000000000000000
kind: decision
decided_on: 2026-01-01
written_on: 2026-01-02
decided_by: owner@example.com
source: src-000000000000000000000000
affects: [context/strategy/icp.md]
review_by: 2026-04-01
origin: ledger
run_id: run-2026-01-01-00000000
status: open
---

We decided to sell to heads of marketing at companies of twenty to two
hundred people, and to stop calling on companies below that size.
```

## Edits

### Edit 1

path: context/strategy/icp.md
heading: ## Firmographics
op: replace

```text
Companies of twenty to two hundred people, with a marketing team of one to five.
```

## Excerpt

```text
so from now on we are only going after companies between twenty and two hundred people
```

## What changed

Before: The customer profile says we sell to companies of any size.

After: The customer profile says we sell to companies of twenty to two hundred people.

## Why

The team decided this on the first of January and the document was never
brought in line with the decision.

## Evidence

Decision stg-0000000000000000, recorded on the first of January.

> so from now on we are only going after companies between twenty and two
> hundred people

## Confidence

high

## Rule being changed

None

## About this proposal

This proposal was drafted by an AI assistant from the evidence above and has not been reviewed by a person yet.

If the decision is right but the edit is wrong, say keep the decision and drop the edit.

gtm-base proposal stg-0000000000000000 entry stg-0000000000000000 source src-000000000000000000000000
