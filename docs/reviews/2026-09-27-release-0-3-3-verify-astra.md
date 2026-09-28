Nine findings are closed; two are partly closed. Reviewed `bd85d42` read-only. Three pure helper tests and targeted in-memory probes passed. Filesystem-writing tests were not run; the counterfactual test results below are assessed from source.

| Finding | Status | Evidence | Test fails without fix? |
|---|---|---|---|
| 1. Git executes configured programs | **Partly** | `gitcmd.py:54` disables ordinary hooks, monitoring and commit/tag signing, but misses attribute sources and signature execution described below. | Yes, planted-hook regressions; they miss the remaining holes. |
| 3. Filenames escape the data fence | Closed | `stale_check.py:253,303,317` fences the list, questions, answers and filename-derived metadata. | Yes, hostile hyphenated-name test at `test_record_change.py:1021`. |
| 4. Approval omits affected documents | Closed | `record_change.py:748` refuses oversized selections before keeping state; accepted names are rendered whole. | Yes, tests at `:1054,1065`. |
| 5. Numbers and showing are unbound | **Partly** | `record_change.py:444,1064` checks list membership and HEAD, but another window can replace the stored list. | Yes, tests at `:1088,1098`; neither covers replacement by another window’s list. |
| 6. An answer confirms replacement content | Closed | `record_change.py:1153,1200` stores and checks the entry’s full content hash before reconciliation. | Yes, replacement-entry test at `:1113`. |
| 7. Rollback deletes another window’s work | Closed | `record_change.py:1009` checks the staged blob, file identity and contents before undoing its changes. | Yes, file-edit and staged-edit tests at `:913,927`. |
| 8. Unrelated HEAD movement means success | Closed | `record_change.py:1122` requires HEAD to contain the exact approved entry before reporting success. | Yes, unrelated-save test at `:944`. |
| 9. Partial writes survive refusal | Closed | `record_change.py:981` completes, syncs and closes an exclusive temporary file before publishing through a non-overwriting link. | Yes, test at `:977`, although its injection targets the new helper rather than reproducing the old write failure directly. |
| 10. Concurrent answers resurrect questions | Closed | `record_change.py:1191` locks validation through consumption; `:1151` locks additions to the same state. | Yes when the tested overlap occurs; `:1131` uses timing rather than a deterministic barrier. |
| 11. Early correction refusal preserves approval | Closed | `stale_check.py:237` forgets the previous showing before claiming words files. | Yes, invalid-words-file test at `:1178`. |
| 12. Renamed maps remain confirmable | Closed | `record_change.py:408,1190` and `confirm.py:1094` reject maps by kind. | Yes, moved-map tests at `:1204,1210`. |

Remaining defects in `bd85d42`:

1. **Finding 1: executable filters can escape the attributes check.** At [gitcmd.py:185](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a2ab96c0d369bb0b7/plugins/gtm-base/lib/gtmbase/gitcmd.py:185), relative `core.attributesFile` paths are opened relative to Python’s directory, while Git runs in the base. Line 201 also silently stops reading after 256 KiB. Both cases produced an empty driver list in in-memory probes despite a matching configured filter. The scan also misses attributes in the index or incoming worktree tree: creating a proposal worktree from fetched `origin/main` can first introduce an attribute naming a configured smudge/process filter. Git uses index attributes during checkout. **Smallest fix:** resolve paths against Git’s effective directory, read complete attributes or refuse oversized files, and inspect the index/target tree before checkout. [Git attributes documentation](https://git-scm.com/docs/gitattributes).

2. **Finding 1: configured signature programs remain enabled.** [gitcmd.py:54](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a2ab96c0d369bb0b7/plugins/gtm-base/lib/gtmbase/gitcmd.py:54) leaves `log.showSignature` and `merge.verifySignatures` active. A signed commit can therefore invoke the configured verification program during plugin history reads or a session-start fast-forward. The push exemption also preserves `push.gpgSign`. **Smallest fix:** disable those signature settings while retaining the required pre-push hook. [Git configuration documentation](https://git-scm.com/docs/git-config).

3. **Finding 5: another window can replace the numbered mapping.** [record_change.py:424](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a2ab96c0d369bb0b7/plugins/gtm-base/lib/gtmbase/record_change.py:424) stores one list per base. Window A sees `context/b/notes.md` as number 1. Window B adds `context/a/notes.md` and requests a new list. A’s original selection of 1 now selects `a/notes.md`, with both displayed as “your notes.” Actual function calls reproduced this in memory. **Smallest fix:** issue a list token and require that same token when resolving numbers, or scope the snapshot to its originating conversation.

4. **Native Windows import failure.** The new unconditional [record_change.py:45](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-a2ab96c0d369bb0b7/plugins/gtm-base/lib/gtmbase/record_change.py:45) imports `fcntl`, unavailable in native Windows Python. Consequently, the stale-check script fails before reaching the flow. **Smallest fix:** use a platform-specific locking implementation behind a shared interface. This is separate from the null-device setting; Windows support was not established or runtime-tested.

The other requested ordinary paths hold by inspection:

- Hook and monitor overrides propagate to Git children, including automatic maintenance. Current diff/show/log protections suppress external diff and textconv; blame suppresses textconv.
- Config reads and the installer’s `rev-parse --git-path hooks` remain correct. Push preserves the pre-push safeguard, including existing hooks it chains; it deliberately does not provide a blanket no-hook guarantee.
- An unused global LFS filter remains allowed. Linux uses `/dev/null`; Windows uses `os.devnull`’s `nul`. No null-device defect was established.
- Session start already refuses incoming `.gitattributes`, so that particular incoming-attributes bypass applies to worktree creation, not its normal update.
- On POSIX, a crash releases the lock; a second window waits or receives the busy refusal. Refusing approval after an unrelated save is conservative but acceptable for one person in one window, with a fresh showing as recovery. No ordinary POSIX temporary-publish regression was found.

**Verdict: not ready.**