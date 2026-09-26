| Finding | Status | Evidence |
|---|---|---|
| Confirmation #1 and original #1, undo overwrites edits | Closed | Journal-hash rechecks preserve and name late edits. Both regression scenarios fail before the fix and pass after in memory; ordinary restore/removal still works. |
| Confirmation #2 and original #5, ownership rules | Closed | Defaults precede existing rules and inherit only broad correction-folder owners. All four ownership tests pass now and fail against `2a6fd91`. |
| Confirmation #3 and original #10, source-map credentials | Closed | Edit/MultiEdit scan the resulting file; both assembled-token regressions fail before and pass after in memory. Incoming screening runs before merge, and tests now exercise the actual update path. |
| Confirmation #4, ordinary source-map content refused | Closed | Ordinary Write/Edit/MultiEdit scenarios pass now and fail before with mocked filesystem access. Incoming probes accept ordinary content and reject all credential fixtures. |
| Confirmation #5, fallback reaches outside bases | Closed | Read-only shell probes reproduce the old copied-template refusal and confirm its removal. Registration matching excludes `content_root`; ordinary outside-base writes pass when Python fails. |

No new defects found in `98052cb` within the requested paths. Verification used source inspection, pure tests, and read-only/in-memory probes. Filesystem-writing integration tests were not run.

**Verdict: ready to merge.**