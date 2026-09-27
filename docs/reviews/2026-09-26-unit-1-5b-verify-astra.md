| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Abandonment overwrites edits | **Partly** | The edited duplicate regression fails on the old code and is fixed, but the separate undo loop still restores without rechecking bytes. |
| 2 | Generated record collision | **Closed** | A free name is selected, journaled, and reused during recovery. The collision test detects the former overwrite; journal/hash reconstruction also checked in memory. |
| 3 | Old-path conflicts | **Closed** | Conflicting copies now resolve affected paths. The regression distinguishes the old path from `context/icps.md`, confirmed in memory. |
| 4 | Duplicate removal refreshes confirmation | **Closed** | Acceptance history excludes deletions. The dated duplicate-record test fails with the former filter. |
| 5 | Migrated ownership | **Partly** | The older template’s correction rule moves correctly, and its test detects the fix. Hand-edited ownership precedence is not preserved. |
| 6 | Intermediate outgoing skills | **Closed** | The add-then-delete test detects the fix. The merge test passes either version, so adds no regression evidence. |
| 7 | Hostile filename in refusal | **Closed** | Refusals use safe names. The hostile-filename assertions fail on the old implementation, confirmed in memory. |
| 8 | Nonempty placeholder bypass | **Closed** | Trust, write, incoming-content, and gate checks reject content. Trust/write/gate tests detect the old bypass; the incoming test only exercises its helper. |
| 9 | Missing-map and shell bypasses | **Closed** | Registered/history-based discovery and shell protection cover both original failures. Both regression tests exercise the affected entry points and fail without the fixes. |
| 10 | Source-map credentials | **Partly** | Full-token Write/Edit tests detect the original bypass, but replacements are screened separately. The incoming helper test does not verify its integration. |
| 11 | Proposal uses wrong layout | **Closed** | `_prepare()` resolves against the destination worktree. The test checks the updated old-path document; the former implementation refuses it. |
| 12 | Missing Access part | **Closed** | The starter source map is planned, journaled, and recovered. Creation/owner assertions fail without the fix; interruption snapshots include it. |
| 13 | Interruption tests never stop | **Closed** | Tests enumerate observed mutations and require both an exception and `fired`, including journal operations, removals, and writes. |

Verification used source comparison and in-memory probes; filesystem-writing integration tests were not run. Read-only gate probes handled empty and first-push ranges correctly. The 2,000-commit guard precedes the new history scan; merge-parent raw records parse correctly.

1. **High, residual #1: abandonment can still destroy a concurrent edit.** At [changes.py:2506](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a6ae23de3d5abbaf4/plugins/gtm-base/lib/gtmbase/changes.py:2506), an edit arriving after classification is read but never compared before `checkout HEAD` or removal. Reproduced in memory. **Smallest fix:** compare those bytes with the journaled write immediately before either operation; preserve and report changed files.

2. **High: generated ownership rules override hand-edited rules.** At [changes.py:1096](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a6ae23de3d5abbaf4/plugins/gtm-base/lib/gtmbase/changes.py:1096), `access/stack.md @security` followed by `corrections/** @owner` gains a later `access/** @owner`, removing the security requirement. A specific correction exception can also become the owner for every new folder. **Smallest fix:** insert defaults before existing rules and obtain their owners only from the broad correction-folder rule.

3. **Medium, residual #10: edits can assemble credentials.** At [write_hook.py:627](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a6ae23de3d5abbaf4/plugins/gtm-base/lib/gtmbase/write_hook.py:627), an Edit completing an existing token passes because only its replacement fragment is scanned. The completed text fails the scanner. **Smallest fix:** apply Edit/MultiEdit replacements in memory and screen the resulting file.

4. **Medium: ordinary source-map URLs are refused.** At [write_hook.py:673](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a6ae23de3d5abbaf4/plugins/gtm-base/lib/gtmbase/write_hook.py:673), `<https://app.hubspot.com>` triggers the outgoing scanner’s hidden-content rule on Write, Edit, and MultiEdit. Incoming screening uses the same scanner. **Smallest fix:** distinguish ordinary Markdown URLs from credentials and add ordinary-content boundary tests.

5. **Medium: shell skills protection reaches outside bases.** At [write-check.sh:244](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a6ae23de3d5abbaf4/plugins/gtm-base/hooks/write-check.sh:244), a copied template with `context/map.md` but no repository is treated as a base. The subsequent unkeyed registration search also matches an ordinary linked project’s `content_root`. **Smallest fix:** require a repository marker for map discovery and match registered base `root` fields specifically.

**Verdict: not ready.**