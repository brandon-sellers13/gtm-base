# Unit 1.7e, a yes only a person can give: correctness review

Reviewer: a correctness-review subagent started by the Unit 1.7e builder, on the diff from release-b to unit-1-7e (commits f0eaa45 and 7c5d297), 2026-09-27. Recorded here by the orchestrator; read it with the security review of the same day.

## Findings

1. **High.** Leaving a segment out is refused for good when the draft list refuses because a file already stands where the segment would go: that refusal records no showing, and the leave-out needs one. Fix: that refusal is the showing of the leave-out choice.
2. **High.** Leaving out a page that adoption refused (unreadable, not Markdown, a destination problem) is refused for good, because no showing is recorded on those refusals or on resume. Fix: record a leave-out showing on those refusals and for each unreadable page resume names.
3. **Medium.** The closing's reconciliation records a showing for every document at once while the skill asks one at a time, so one answer authorizes the next document's answer before it was asked. Fix: record only the document being asked now.
4. **Medium.** Showings are never used up, so one message authorizes contradictory answers (not now, then move, in the same turn). Fix: use a showing once, after a successful write.
5. **Low.** Pruning old records can delete a lock file another process still holds.
6. **Low.** The pruning cutoff mixes a naive UTC time with a local-time conversion.
7. **Low.** After "not now", a later explicit request to move is refused with a sentence pointing at a showing that cannot happen for the put-off window.

## Residual risks named

The session identity rests on an undocumented variable matching the hook's session; a message typed while a turn runs may count as after a showing it never saw; a showing is really "printed to the assistant", and a check before use records one even when the person never sees the question; derived preview values can change between preview and approve; the count is read outside the showings lock.

## Testing gaps named

No tests for the two stuck leave-out flows; several "refused before a message" tests pass for a different reason and assert no code; one test would pass with the gate removed; the hand-edit path is not exercised; no tests for two-document reconciliation, not-now then move, concurrent writers, or lock pruning.
