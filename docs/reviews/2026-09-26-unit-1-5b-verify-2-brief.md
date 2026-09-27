You are confirming fixes before a merge. Read only; change nothing. Output a written review in markdown.

## Context
Unit 1.5b of GTM Base (a Claude Code plugin) lays a base out by the five CLASS parts and moves an older base through one offered, recoverable move. Read, in the main checkout at ~/Build/gtm-base: your first review (docs/reviews/2026-09-26-unit-1-5b-astra.md, thirteen findings, at fb13268) and your confirmation pass (docs/reviews/2026-09-26-unit-1-5b-verify-astra.md, at 2a6fd91: findings 1, 5 and 10 partly closed, and five findings). The fixes to the confirmation pass are one commit, 98052cb, on the current branch. See them with `git diff 2a6fd91..98052cb`. The new tests are in tests/test_unit_1_5b_verify.py.

Exactly one real base exists, on the older layout with one context change in work/decisions, and its owner will run this move on it.

## The standard for this pass, and nothing beyond it
1. Are the five findings of the confirmation pass, and findings 1, 5 and 10 of the first review, now closed? Check each fix and that its test would fail without it.
2. Is any ordinary path broken by 98052cb: an ordinary edit or write to the source map, an ordinary ownership list, an ordinary undo of a stopped move, an ordinary file write outside a base when the Python check cannot run?
3. Known and accepted for now, do not report: the check before a send still applies the outgoing hidden-content rule to the source map, so an angle-bracket link there would be refused when sending. No base has a shared copy until a later release.

## Output
A short table: each finding, closed or not, one line of evidence. Any new finding only if it is a real defect in 98052cb, with file, line, scenario and smallest fix. Then a one-line verdict: ready to merge, ready with the listed changes, or not ready.
