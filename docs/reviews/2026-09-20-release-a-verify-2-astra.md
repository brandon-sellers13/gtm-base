Reviewed **`d5a3525..457e034`**, the requested second-round fix commit. Later commits in the checkout are excluded. Verification used source inspection and isolated in-memory probes; the filesystem-writing suite was not run. No files changed.

All references below use **line numbers at `457e034`**. Paths are relative to `plugins/gtm-base/`, except `tests/`.

**Findings, ranked by severity**

**1. High: A committed deletion removes an unjoined base from both push safeguards.**  
`lib/gtmbase/gate.py:1156`

A fresh clone has neither local `gtmbase.id` nor a joined-account record. Delete `gate-allowlist.txt`, commit that deletion, then push. The current `HEAD` no longer contains all three marker paths, so the repository becomes “ordinary” and escapes both scanning and the first-backup lock. Its confidential history remains in the push. Git hooks are not inherited by the clone.

The in-memory probe confirmed that removing one committed marker changes identification from true to false. `tests/test_gate.py:1225` removes only the working-tree map, a weaker scenario.

**Smallest fix:** Recognize inherited base identity across committed marker deletion, including relevant history. Share that recognition with the write guard: `_base_above` at `write_hook.py:277` still loses an unjoined base immediately when its working-tree map disappears, reopening its `.git` and `.claude` files.

**2. High: Direct access to external Git metadata bypasses the corrected path comparison.**  
`lib/gtmbase/write_hook.py:314`

Suppose `/base/.git` points to `/external/repo-meta`. Writing `/external/repo-meta/config` contains neither `.git` nor `.claude`, so the early return skips comparisons against known bases. `_reaches` correctly recognizes the protected destination, but never gets called for it.

The probe confirmed `_reaches=True` while `problem_with=None`. `tests/test_write_hook.py:768` writes through a spelling containing `.git`, missing the direct destination.

**Smallest fix:** Compare known protected destinations, including resolved aliases and worktree metadata, before applying the filename shortcut.

**3. High: Failed approval still destroys the original index state.**  
`lib/gtmbase/approve_local.py:1083`, `:1093`, `:1123`, `:1304`

Stage version B of a document, then continue editing its working copy into C. Approval stages C. If a commit hook rejects the commit, rollback sees that working text already equals its backup and skips restoration. The journal is cleared, but the index no longer contains B.

Even when restoration runs, the backup holds only a `staged` boolean. Adding the entire restored working copy cannot reconstruct a partially staged version. Git restoration failures are also ignored at line 1130.

The claimed byte preservation is incomplete too: `read_text` normalizes line endings, and restoration forces `0644`. Backup files themselves are correctly written `0600`; restored files can lose their original privacy.

`tests/test_approve_local.py:2334` compares normalized text, not raw bytes, permissions, or index contents.

**Smallest fix:** Preserve working bytes, original permissions, and index blob/mode independently. Restore and verify the index even when working text already matches. Retain recovery records on any failure. Refusing partially staged targets is the smallest immediate containment.

**4. Medium: Runtime write-check failures still allow the write.**  
`lib/gtmbase/write_hook.py:389`

An exception during `run()` returns zero with no output. Consequently, the new script failure status and shell fallback never activate. A broken runtime check can therefore permit protected writes despite the import-failure fix.

The probe produced exit status `0` and empty output after an injected `OSError`. The wrapper tests at `tests/test_write_hook.py:887` break Python loading, not runtime execution.

**Smallest fix:** Propagate runtime failures or return the wrapper’s failure status, including failures emitting a denial.

**5. Medium: The broken-plugin fallback can refuse every ordinary write.**  
`hooks/write-check.sh:53`

It scans the entire request, including content and metadata. A normal request containing a transcript path under `.claude` triggers denial regardless of the destination. So does writing a README containing a repository URL ending in `.git`, or writing `.gitignore`.

The fallback’s ordinary-write tests omit these realistic fields and contents.

**Smallest fix:** Inspect destination fields with component-aware path checks. Do not use unrelated payload text to classify the destination.

**6. Medium: Following the documented setup command immediately refuses the company file.**  
`skills/join/SKILL.md:106`; `skills/join/scripts/join.py:1177`

The preceding command issues a company file under `--run <id>`. The documented `propose-location --company-file ...` command supplies neither run nor session. The reader receives an empty key and refuses the file it just issued.

`tests/test_skills_and_scripts_agree.py:105` only compares flag names against parser metadata. It does **not** parse or execute the documented commands, validate required combinations, or check propagation. Its coverage is weaker than both its description and the CHANGELOG claim.

**Smallest fix:** Add the run identifier to this command and test the actual handout-to-consumption sequence extracted from the skill.

**7. Medium: A person cannot revise wording after the first replacement.**  
`lib/gtmbase/compose_proposal.py:1133`; `skills/propose-change/scripts/approve_local.py:202`

The first `--wording` operation clears `first_draft`. The owner then requests a correction during review. Repeating the documented command consumes the new words file and refuses with `not-a-first-draft`.

**Smallest fix:** Allow subsequent wording revisions on pending proposals, retain validation, and require a fresh preview/hash. Consume the words file only after the operation succeeds.

**8. Medium: The whole-difference artifact hides Markdown syntax and meaningful whitespace.**  
`lib/gtmbase/approve_local.py:485`, `:620`

An additional change containing `![Offer](https://example.org/offer)` becomes a blockquoted image, not a literal depiction of the committed syntax. Link destinations similarly disappear behind their labels. `_quoted` also strips trailing spaces, hiding changes to Markdown line-break behavior.

`whole_difference` includes the additional textual edits, but its renderer does not faithfully display them. `tests/test_approve_local.py:2433` checks substrings in artifact source, not visible rendering.

**Smallest fix:** Render the diff literally using a collision-resistant fence, preserve whitespace, and visibly identify whitespace-only changes.

**9. Medium: The load-time dismissal cap never expires a far-future value.**  
`lib/gtmbase/state.py:982`

A persisted `ledger_behind_dismissed_until="9999-12-31"` becomes today plus thirty days on every read. That normalized deadline is never persisted.

The exact function returned `2026-10-23` for a simulated `2026-09-23`, then `2027-10-23` a year later. The reminder remains suppressed. `tests/test_quiet_caps_and_second_edits.py:144` asserts one capped read, not eventual expiry.

**Smallest fix:** Reject over-cap persisted values, since legitimate writes now cap them, or persist one fixed normalized expiry.

**10. Medium: Numbered source selection can read a different file from the one selected.**  
`skills/join/scripts/join.py:572`; `lib/gtmbase/join_flow.py:739`, `:905`

The listing numbers files in directory-walk order, while persisted consent sorts paths. `--only` indexes the latter.

For `/content/z-profile.md` and `/content/a/positioning.md`, the root document is displayed as item 1, but `--only 1` selects positioning. The in-memory probe reproduced that mismatch. Existing narrowing tests exercise filename selection or invalid numbers, not displayed-number identity.

**Smallest fix:** Use one stable ordered mapping for display, persistence, and selection.

**11. Medium, contained by the send lock: Outgoing proposals ignore `first_draft`.**  
`lib/gtmbase/compose_proposal.py:690`

The outgoing path still uses the old exact placeholder-tail check. Delete its final period while leaving `first_draft: true`, and this check passes. Local approval correctly refuses it; outgoing processing currently stops later because Release A prohibits sends.

`tests/test_first_draft_marker.py:124` exercises local approval only.

**Smallest fix:** Share the marker and normalized-note check between both approval paths.

**Disposition of the eleven prior findings**

“CLOSED” below refers to the reported scenario, not every broader guarantee associated with it.

| Prior finding | Status | Verification |
|---|---|---|
| 1. Guard checks a different path | **STILL OPEN** | Leading spaces and equality are fixed. Direct external metadata access still bypasses protection, finding 2 above. |
| 2. Guard disables itself and allows errors | **STILL OPEN** | Installed code and home settings are protected; import failures reach the fallback. Runtime errors still allow writes, finding 4. |
| 3. Removing the working-tree map disables push checks | **CLOSED** | Config, joined records, and committed markers survive the original uncommitted rename. Committed identity removal remains a separate defect, finding 1. |
| 4. Failed approval loses hand edits | **STILL OPEN** | Ordinary working prose is preserved, but index state, exact bytes, and permissions are not, finding 3. |
| 5. Unrelated same-file edits are committed unseen | **CLOSED** | Non-hand proposals reject dirty targets. Hand proposals include the whole textual difference and bind current content into approval. Rendering remains defective, finding 8. |
| 6. Words flags read arbitrary private documents | **CLOSED** | All three scripts now enforce the private run/session directory, regular-file ownership, link count, and size restrictions. This closes direct arbitrary-path ingestion, not provenance or substitution risks below. |
| 7. First-push consent uses original directory | **CLOSED** | `gate.py:1470` checks every resolved in-scope push folder. |
| 8. Punctuation makes placeholders approvable | **STILL OPEN** | Local approval checks marker and normalized wording; outgoing approval retains the weaker check, finding 11. |
| 9. Closing summary is unfenced | **CLOSED** | `join_flow.py:1589` fences the complete summary, and the CLI prints that summary. |
| 10. Documented preview changes attribution at approval | **CLOSED** | The documented command supplies base/run, the CLI requires the base, and preview stamps attribution before rendering. Concurrent changes remain a separate risk. |
| 11. Future date defeats silence cap | **CLOSED** | `state.py:515` validates calendar dates and rejects future `silent_until_set_on`. The dismissal-cap defect in finding 9 concerns a different field. |

**Residual risk, separate from the defects**

- **Words files establish location, not provenance.** `wordsfile.py:189` records no issuance, and `read_words` accepts any matching filename in the permitted directory. The probe accepted a never-issued name. Same-account replacement remains possible; pathname checks and reading are not one descriptor-bound operation. Existing tests reject already-present links, not substitution during reading. A private directory limits other users, but cannot authenticate the assistant’s transcription.
- **Recovery is not concurrency-safe.** `_save_originals` deletes the single per-base backup directory before saving replacements. Concurrent approvals can interfere with that directory and the shared journal. Sequential recovery checks backup hashes and preserves newer ordinary prose; that does not establish safety against concurrent writers.
- **First-draft recognition remains heuristic.** Paraphrased TODOs can pass, while legitimate wording beginning “Update needed” can fail. The editable marker is not protected provenance.
- **Identity remains an approximation.** Healthy ordinary repositories, the plugin repository, and nonrepositories are not classified as bases by the three checks. A missing repository top alone does **not** answer yes in this commit; an exception does. Such exceptions can therefore refuse ordinary work. Arbitrary config values or committed marker names can also satisfy identification.
- **Sequential hand-edit IDs are fixed.** `free_local_edit_id` checks all named storage locations. Its remaining limits are a 200-ID ceiling and non-atomic allocation between concurrent calls.
- **Preview finalization is not transactional.** Another operation can consume the chosen closing ID or change owner configuration between preview and approval.
- The acknowledged shell-path construction, unmatched connector tools, and same-account state tampering remain outside the effective protection boundary.

**CHANGELOG assessment**

The open-risk list is candid about several important limitations, but **it is neither complete nor consistently accurate**.

Its claims of exact-byte recovery at line 177, issued-file exclusivity at line 183, harmless fallback behavior at line 195, record-independent linked-folder protection at line 197, and command-parser testing at line 205 exceed the implementation. Line 213’s reliance on the check failing closed conflicts with finding 4. Approval concurrency, words-file substitution, and preview binding are missing from the residual-risk accounting.

**Verdict: Not ready.**

Findings **1 through 10 block release**: they permit safeguard bypass, lose user state, obstruct ordinary/setup/revision workflows, misrepresent approved changes, suppress reminders indefinitely, or select the wrong source. Finding **11 must be fixed before enabling outgoing proposals**; the current send lock contains that path.