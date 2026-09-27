Reviewed `eb8999d..4c8e35e` read-only. No files changed. Filesystem-writing tests were not rerun; counterfactual results below distinguish in-memory verification from source inspection.

| Original finding | Status | Evidence | Test fails without fix? |
|---|---|---|---|
| 1. Unlocked rollback deletes a concurrently saved page | **Closed** | `join_flow.py:2253,2336,2572` locks recovery through state rechecks and terminal record updates. | **Yes**, by inspection of the lock-wait regression. |
| 2. Cleanup deletes a replacement file | **Closed** | `review.py:719` claims the entry before checking its identity; the replacement survives. New recovery defect below. | **Yes**, verified with old/current in-memory probes. |
| 3. Retry shortcuts bypass current cleaning | **Closed** | `join_flow.py:2283` revalidates written pages through the shared finishing path. | **Yes**, for approval/show regressions by inspection. Resume-only cases already passed previously. |
| 4. Saved bytes mistaken for completed adoption | **Closed** | `review.py:1163` checks the confirmation’s run; `confirm_saved` saves the missing line separately. | **Yes**, old/current state classification verified in memory; commit regression inspected. |
| 5. Oversized hidden HTML survives | **Closed** | `adopt.py:682` refuses the reported oversized tag. New false refusal below. | **Yes**, verified against old/current cleaners in memory. |
| 6. Confirmation-write crash blocks recovery | **Closed** | `review.py:642` sweeps aged confirmation temporaries before cleanliness checks. New concurrency defect below. | **Yes**, verified with old/current sweep probes; SIGKILL test inspected. |
| 7. Hostile filename in removal notice | **Closed** | `join_flow.py:1796` uses the person’s segment name; `join.py:887` fences the numbered list without changing its numbering. | **Yes**, removal-notice counterfactual verified in memory; list regression inspected. |
| 8. Malformed candidate number crashes recovery | **Closed** | `segments.py:293` requires a positive, non-boolean integer. | **Yes**, infinity raises `OverflowError` before the fix and returns invalid afterward. |

The reentrant lock passed in-memory nesting, exception-release and thread-isolation checks. It does not span a user prompt; process death releases the underlying OS lock.

1. **Medium: Interrupted cleanup permanently strands a claim.**  
   [review.py:719](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-adb18d6bfdbbaf313/plugins/gtm-base/lib/gtmbase/review.py:719) renames the page to a random `.gtmbase-claim-*` entry. A crash before deletion or restoration leaves it behind. Sweeping explicitly excludes claims, and recovery rejects the orphan as unrelated dirty work. A failed put-back at line 735 has the same result, potentially leaving somebody else’s page under the private name. In-memory probes reproduced both cases. **Smallest fix:** retain recoverable original-path and identity information, reconcile interrupted claims under the writing lock, and surface failed restoration.

2. **Medium: Five seconds does not prove a temporary file’s writer died.**  
   [review.py:626](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-adb18d6bfdbbaf313/plugins/gtm-base/lib/gtmbase/review.py:626) permits deletion based only on modification time. Other confirmation writers do not hold the import lock. Pause one during its atomic write for over five seconds, then resume an import: sweeping deletes its temporary file and its eventual rename fails. A forward clock adjustment can trigger the same failure; a backward adjustment delays orphan recovery. **Smallest fix:** coordinate sweeping and every affected writer through an ownership lock, reclaiming only after the writer has released it.

3. **Medium: Ordinary comparisons now refuse adoption.**  
   [adopt.py:584](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-adb18d6bfdbbaf313/plugins/gtm-base/lib/gtmbase/adopt.py:584) treats every `<` followed by a letter as markup. A valid page containing `CAC<LTV.` passed before and now raises `screened`, verified in memory. The new comparison test covers only spaces or digits after `<`. **Smallest fix:** distinguish actual residual HTML from literal comparisons while retaining oversized-tag detection, and add this regression.

**Verdict: not ready.**