# Phase A1 end-to-end run: SC1 and SC5 on a test base

Date: 2026-09-05. Run by the orchestrating session after Units 1, 2, 9a, 4, 3, 7, 9b, and 10 landed
(555 tests green). This is a record of a real run, not a projection. The remote was a local bare
repository and the GitHub CLI was the test fake on PATH, because no GitHub remote exists yet
(Brandon has not yet confirmed the remote and its visibility). Everything else was the real code:
two bases copied from `templates/company-base`, real git, the actual skill scripts, the actual
session-start wrapper, a seat directory under a temporary `GTM_BASE_HOME`.

Script: the orchestrator's scratchpad `e2e.sh` (setup: copy the template, first save, add the
remote, write the base id into the base's git settings, record the base as joined, mark the
first-push review as done, set a session id).

## SC1: one hand-entered ledger line yields a flag and a drafted proposal

Hand-entered entry: `work/decisions/stg-e2e0000000000001.md`, decided 2026-09-01, written
2026-09-03, affects `context/strategy/icp.md`, no confirmation line for that file.

`stale_check.py` produced one staging file, `work/proposals/pending/stg-39e8875c800551f4.md`,
with `origin: ledger` and the entry cited in its Evidence section. `propose.py --staging` opened a
review through the fake CLI (four calls logged: two duplicate searches, one head check, one create),
and the remote gained the branch `proposal/stg-39e8875c800551f4` with exactly two files changed:

```
 context/strategy/icp.md                        |  5 +++++
 corrections/2026-09-05-stg-39e8875c800551f4.md | 24 ++++++++++++++++++++++++
```

The corrections file carried `entry_id: stg-e2e0000000000001`, the content hash, the touched path,
and the visible marker line. The clone stayed on main with a clean tree. A second `stale_check.py`
run staged nothing (the staging file had moved to `work/proposals/opened/`). After the merge was
simulated on the remote (main fast-forwarded to the proposal branch), a dry run reported no flag
against the decision; it still listed the file as never confirmed by an owner, because the merged
corrections file settles the decision but is not an owner's confirmation line. That was the
rule Unit 9a pinned at the time; Brandon's decision on it is recorded below.

## SC5: a Thursday entry about Tuesday flags Wednesday's confirmation

Second base. A confirmation line for `context/strategy/icp.md` dated 2026-09-02 (Wednesday) was
saved with the owner's address, then the same entry as above (decided Tuesday 2026-09-01, written
Thursday 2026-09-03). `stale_check.py` printed:

```
context/strategy/icp.md is out of date against decision stg-e2e0000000000001, and a change for it is prepared as stg-39e8875c800551f4.
```

The staging file's Evidence section cited the entry id, the entry file name, the decision date,
and quoted the decision. Control: after a further confirmation dated 2026-09-04 (Friday) was saved,
a dry run flagged nothing against the decision.

## Session-start hook on the SC1 base

A `startup` payload through `hooks/session-start.sh claude` returned one JSON object with a
visible message and an assistant context. The context carried "since your last session: 0 changes",
the map inside a data fence with the trust note, the two settings in plain words, and, because the
template base has no `positioning.md`, the continue-setup block instead of a question.

## What was not exercised here

- A real GitHub remote, real `gh pr create`, a real merge from the GitHub page, and the installed
  git hook on a push to GitHub. These wait on Brandon's confirmation of the remote.
- A live Claude Code session showing the combined visible-plus-context hook output.
- The confirmation flow (Unit 10) end to end from an injected question; it is covered by its tests
  only.

## Decision after this run

Brandon decided on 2026-09-05 that when the person who merges a proposal drafted from a ledger
entry is an owner of the affected file, that merge counts as the owner's confirmation of the file.
It resets the threshold clock exactly as an owner's own confirmation line would, rather than only
settling the ledger entry. When the merger is not an owner, behavior is unchanged: the corrections
file settles the entry and the file still waits on its owner. That rule is implemented in the stale
library and the base reader, with the merger read from the first-parent history of the default
branch, and it is covered by tests.
