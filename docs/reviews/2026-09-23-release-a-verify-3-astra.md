Reviewed **HEAD `5f8076b`**, including `git log 457e034..HEAD`, each commit’s `git show --stat`, and the implementation and tests added by `6bdfdc8`, `ad4f2d4`, `7476eb7`, and `5f8076b`.

Verification used source inspection and read-only, in-memory probes. **No files changed. The filesystem-writing test suite was not run.** The documented live checklist still has no results.

All line numbers below are at HEAD. Paths are relative to `plugins/gtm-base/`, except `tests/` and `docs/`.

**Ranked findings**

No critical findings identified.

**R1. High: Failed approval still loses the original index state.**  
[approve_local.py:1465](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:1465)

Stage version B, continue editing the working file into C, then approve with a commit hook that rejects the commit. Approval stages C. Rollback sees that the working bytes equal its backup and skips restoration, leaving C in the index instead of B.

The probe returned no unresolved recovery work and made **zero Git calls**. Backup metadata still records only a `staged` boolean at line 1249. Restoration forces `0644` at line 1281 and ignores Git failures at lines 1288–1291.

Raw-byte backup is fixed. `tests/test_approve_local.py:2700` now checks those bytes, but not index contents or permissions.

**Smallest fix:** Preserve index blob/mode and filesystem permissions independently. Restore and verify the index even when working bytes already match; retain recovery records on failure.

**R2. High: Direct external Git metadata remains writable.**  
[write_hook.py:358](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:358)

If `/base/.git` resolves to `/external/repo-meta`, writing `/external/repo-meta/config` contains neither `.git` nor `.claude`. The shortcut returns before comparing known protected destinations.

The probe confirmed `_reaches=True` but `problem_with=None`. `tests/test_write_hook.py:801` tests a spelling containing `.git`, which does not cover this path.

**Smallest fix:** Resolve and compare protected metadata destinations before the filename shortcut, including gitfile targets and common/worktree directories.

**R3. High: Removing an unjoined base’s map still disables its write guard.**  
[write_hook.py:314](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:314)

In an unjoined clone, rename `context/map.md`, then write `.git/hooks/pre-push` or `.claude/settings.json`. `_base_above` requires the working map, and the joined-record fallback has no entry.

History-based identification now protects pushes, but the write guard does not use it. `tests/test_write_hook.py:879` empties joined records while retaining the map.

**Smallest fix:** Use durable base identification in the write guard, including committed identity when the working map is absent.

**R4. Medium: Runtime write-check errors still allow protected writes.**  
[write_hook.py:447](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:447)

An exception in `run()` returns success with no output. Output failures do the same at line 452. Consequently, the wrapper never enters its nonzero-status fallback.

An injected `OSError` produced status `0` and empty output. Import-failure tests establish a different failure path.

**Smallest fix:** Return the wrapper’s failure status for runtime and output errors, and test that those errors actually activate fallback.

**R5. Medium: Ordinary dot components bypass the rewritten fallback.**  
[write-check.sh:155](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/hooks/write-check.sh:155)

When Python cannot run:

| Destination | Actual fallback response |
|---|---|
| `$HOME/.claude/settings.json` | `ask` |
| `$HOME/.claude/./settings.json` | Nothing |
| `$HOME/./.gtm-base/machine.json` | Nothing |

These results came from executing the fallback definitions read from HEAD. A normal relative destination, `./settings.json` with `cwd=$HOME/.claude`, produces the second case.

This is separate from the acknowledged escaping and symlink limitations. `tests/test_third_look.py:823` checks canonical absolute paths.

**Smallest fix:** Normalize path components and resolve existing parents before protected-path and settings comparisons.

**R6. Medium: Config protection exempts the protected config itself.**  
[gate.py:705](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/gate.py:705)

The complete gate permits both commands:

```sh
git config -f .git/config --unset gtmbase.id
git config --local other.id anything && git config --local --rename-section other gtmbase
```

The first passes through the unconditional file-option exemption. The second installs identity because the section check examines the source name, not the destination. That can classify an ordinary repository as a base and block its sends indefinitely under Release A.

Conversely, `git config --local user.name gtmbase.id` is incorrectly refused because the value contains the protected key.

Removing identity does **not** resurrect the fixed historical push bypass. The defect is in config protection and classification. `tests/test_third_look.py:498` exempts `other.cfg`, without testing `.git/config`.

**Smallest fix:** Parse the action, selected config file, actual key, and both section names. Exempt explicit files only when they resolve outside protected repository config.

**R7. Medium: A second wording correction is refused after its input is deleted.**  
[compose_proposal.py:1215](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/compose_proposal.py:1215)

The first replacement clears both the proposal marker and seat record. If the owner requests another correction, the documented wording command consumes the new words file, then refuses with `not-a-first-draft`.

Consumption occurs at `skills/propose-change/scripts/approve_local.py:208`; `wordsfile.py:236` reads and deletes the file.

**Smallest fix:** Permit revisions to pending proposals, retain validation, and require a fresh preview/hash. Consume the words file only after success.

**R8. Medium: The whole-difference display still hides syntax and meaningful whitespace.**  
[approve_local.py:572](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:572)

The renderer at line 709 still uses `_quoted`. An added Markdown image renders as an image, link destinations disappear behind labels, and trailing spaces are stripped.

The probe confirmed that two trailing spaces disappear while Markdown remains active. `tests/test_approve_local.py:2433` checks artifact-source substrings, not faithful visible rendering.

**Smallest fix:** Render a literal, collision-resistant fenced diff, preserve whitespace, and visibly identify whitespace-only changes.

**R9. Medium: Source and folder numbers do not consistently identify what was displayed.**  
[join.py:633](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/skills/join/scripts/join.py:633), [join_flow.py:743](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/join_flow.py:743)

Two probes reproduced wrong selections:

- Display `/content/z-profile.md` first and `/content/a/positioning.md` second. Persisted/frozen paths are sorted, so `--only 1` selects positioning.
- Narrow folders `aaa,b,c,d,e` to `b,c,d,e`. The displayed numbering becomes `1=b`, but persistence retains `1=aaa`. Further narrowing by `1` selects the excluded folder.

There is also a newly broken documented variant: `skills/join/SKILL.md:338` still specifies `--only-folder <folder>`, while `join.py:405` now requires numbers. The real CLI rejects `--only-folder customers`. Small listings do not print the required folder-number map.

The command walker misses this because the optional arguments appear in prose, outside the extracted full commands.

**Smallest fix:** Use one ordered mapping for display, storage, and selection. Document numeric folder selection consistently, always expose its mapping, and execute the optional variants in tests.

**R10. Medium: Ordinary hand edits still cannot be prepared.**  
[compose_proposal.py:1486](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/compose_proposal.py:1486)

Both scenarios fail before approval:

- Delete an obsolete section, leaving all surviving sections unchanged.
- Edit the first of two identically named sections, leaving the second unchanged.

Preparation iterates only surviving headings; its dictionary also overwrites duplicate headings at line 1299. Both scenarios falsely report that the document has no headings.

In-memory calls to `stage_local_edit` reproduced both refusals. The new tests are weaker:

- `tests/test_approve_local.py:2797` edits the **second** duplicate.
- `tests/test_approve_local.py:2817` deletes a section **and changes another**.

**Smallest fix:** Derive hand-edit targets from changed files and their bytes independently of section summaries. Summaries must represent deleted and duplicate sections.

**R11. Low: The new waiting filter is not shared with the review.**  
[stale_check.py:536](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/stale_check.py:536), [approve_local.py:1864](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:1864)

Rename a valid pending proposal to `notes.md`. `_documents_with_a_change_waiting` ignores it, but local and shared review readers still list its embedded staging identifier. The resulting item points to a staging filename that no longer exists.

The probe returned no waiting documents from the new helper, while both review readers returned the proposal. The shared reader at `stale_check.py:1385` also lacks the new missing-target filter.

Tests at `tests/test_third_look.py:583` exercise the helper, not consistency with those readers.

**Smallest fix:** Share one validated pending-proposal inventory across closing and review.

**Disposition of the eleven previous findings**

“CLOSED” means the reported scenario is closed, not that every related guarantee holds.

| Previous finding | HEAD status | Evidence |
|---|---|---|
| 1. Committed deletion bypasses push safeguards | **CLOSED** | `gate.py:1212` checks marker history across all refs. `tests/test_gate.py:1354` now commits deletion and verifies recognition/scanning. The accompanying write-guard issue remains R3. |
| 2. Direct external metadata access | **STILL OPEN** | `write_hook.py:358`; R2. |
| 3. Failed approval loses index/bytes/permissions | **STILL OPEN** | Raw-byte backup is fixed at `approve_local.py:1236`; index and permission recovery remain defective, R1. |
| 4. Runtime write-check failure allows writes | **STILL OPEN** | `write_hook.py:447`; R4. |
| 5. Fallback refuses ordinary writes | **CLOSED** | `write-check.sh:87` excludes transcript paths; line 106 narrows destination checks. Transcript, `.gitignore`, and content scenarios are addressed. New bypass is R5. |
| 6. Setup omits company-file run identifier | **CLOSED** | `skills/join/SKILL.md:117` passes `--run`; `join.py:436` uses it for the words-file key. |
| 7. Cannot revise wording twice | **STILL OPEN** | `compose_proposal.py:1215`; R7. |
| 8. Diff hides Markdown/whitespace | **STILL OPEN** | `approve_local.py:572`, line 709; R8. |
| 9. Far-future dismissal never expires | **CLOSED** | `state.py:1029` rejects over-cap values. Probe returned `None` and `bad-value`; test line 166 now asserts rejection. |
| 10. Number selects the wrong source | **STILL OPEN** | Display order at `join.py:633` differs from persisted/frozen order; R9. |
| 11. Outgoing ignores first-draft marker | **CLOSED** | `compose_proposal.py:758` now shares `still_a_first_draft` with local approval at `approve_local.py:933`. |

**Updated residual risks**

- **Hand-edit bytes:** The new mechanism is sound for represented targets. Preparation hashes bytes at `compose_proposal.py:1547`; approval compares them at `approve_local.py:783`; writing leaves the working file untouched at line 1565. Missing/mismatched hash counts deliberately skip that check at lines 785–786. This is not transactional protection against concurrent changes.
- **First-draft provenance:** The seat record protects an identifier. A copied proposal with a new valid identifier, explicit `first_draft: false`, a replacement operation, and paraphrased placeholder wording can pass. The probe confirmed this. Exact-note and marker protection improved; authenticated provenance did not.
- **Words-file provenance:** `wordsfile.py:190` records no issuance. A matching filename in the private directory is sufficient, and pathname checks/read/delete remain separate operations.
- **Concurrency:** `approve_local.py:1227` removes a shared per-base backup directory. Concurrent approvals share recovery state; preview finalization and sequential ID allocation remain non-atomic.
- **Protection boundary:** All-ref identity remains heuristic. Same-account tampering, unmatched connector tools, constructed shell paths, and actual client handling of `ask` remain outside demonstrated guarantees.
- **Live behavior:** `docs/walkthroughs/2026-09-release-a-live-check.md:84` remains an empty results placeholder. The new checklist is evidence of planned verification, not completed verification.

**CHANGELOG assessment**

The later entries describe real improvements, but several guarantees still exceed HEAD:

| HEAD line | Assessment |
|---|---|
| `CHANGELOG.md:221` | Raw-byte backup and unchanged hand-file writes are supported. Index and permission preservation are not. |
| `:197`, `:213` | Record-independent protection and reliance on failure closing access remain contradicted by R3/R4. |
| `:241` | “Every ordinary shape of hand edit” is contradicted by R10. |
| `:243`, `:267` | The walker executes extracted full commands and catches missing handouts/unknown scripts. It does not execute every documented variant. Its regex at `tests/test_skills_and_scripts_agree.py:45` omits prose-only additions; the unrun assertion at line 677 checks only the extracted set. |
| `:249` | First-draft recognition still depends on editable identifiers and fields. The caveat at line 255 needs that concrete consequence. |
| `:251` | Config protection is overstated, R6. |
| `:259` | “Issued” means syntactically valid identifier plus filename agreement, not verified issuance. Review readers also remain inconsistent, R11. |
| `:257` | The assertion that nothing blocks release is contradicted by the retained findings. |

**Verdict: Not ready.**

**R1 through R10 block release.** R11 is a nonblocking consistency defect. The live checklist and client-level `ask` verification also remain outstanding.