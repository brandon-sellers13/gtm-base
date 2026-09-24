**Not ready to release.** The exact R1 through R11 scenarios are closed, but HEAD retains release-blocking defects, including recovery overwriting newer work and approval accepting an unreviewed revision.

Reviewed `bd3bbcfc44fd80a68078e6e61ce7ad7548a3e569` against `5f8076b`. No files changed. Verification used read-only inspection, in-memory scenario probes, shell-fallback execution, and seven passing static skill tests. All 110 Python files parsed successfully. **The filesystem-writing suite was not run.**

All references below use HEAD line numbers.

**Critical**

None identified.

**High**

**N1. Recovery overwrites newer index entries and permissions.**  
[approve_local.py:1763](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:1763), [restore:1517](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:1517)

Approval captures staged B, working C, and mode `0640`. After an interrupted approval, the owner stages D and changes permissions to `0600`, leaving working bytes C. Recovery sees the original working bytes and unconditionally restores index B and mode `0640`.

The probe returned `([], [])`, indicating no conflict or incomplete recovery, while discarding both newer states. The index is checked **after** replacement, never against what this approval actually staged.

Smallest fix: record this run’s expected index and permission changes. Restore each component only when its current value matches either the original or this run’s value; otherwise preserve it and retain recovery records.

The test at `tests/test_approve_local.py:3247` now proves original-state restoration, but supplies no newer index or permission changes.

**N2. A concurrent wording revision bypasses the fresh-preview requirement.**  
[approve_local.py:985](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:985)

During approval, the first read captures reviewed revision 1. A wording command then writes revision 2 before `load_staging()` reopens the file at line 989. Validation and the write plan use revision 2, but the approval hash uses revision 1’s text at line 1165.

The in-memory probe, using the real parser, edit application, and hash functions, produced revision 2’s new wording with **exactly revision 1’s approval hash**. The existing hash comparison therefore accepts the old approval.

Smallest fix: parse and validate the already-read `staged_text`; use that same immutable snapshot for the hash and write plan.

`tests/test_first_draft_marker.py:468` revises before approval begins. It does not exercise these two reads straddling a revision.

**N3. External metadata remains writable when identity exists only in history.**  
[write_hook.py:497](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:497), [shortcut:541](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:541)

Use an unjoined clone without local `gtmbase.id`, rename its map, and point `.git` at `/external/repo-meta`. With the session inside that clone, directly writing `/external/repo-meta/config` is allowed.

The probe returned no refusal and made **zero Git calls**. `_known_bases()` excludes the clone using only cheap identification; the filename shortcut then prevents historical identification. The same fixture correctly refuses paths spelled through `.git` or `.claude`.

Smallest fix: discover the current repository’s metadata destinations before the shortcut, then perform durable identification when the destination reaches one.

`tests/test_write_hook.py:1403` removes joined records but retains the map. Tests at lines 1483 and 1491 remove the map but use guarded path spellings. Their combination remains untested.

**Medium**

**N4. Setup still selects folders other than those shown or requested.**  
[join_flow.py:932](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/join_flow.py:932), [added folders:666](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/join_flow.py:666)

Three reproduced cases:

| Selection | Actual result |
|---|---|
| Select the displayed folder `b` | Includes `/content/a/b/notes.md`, displayed under `a`. |
| Select the displayed root folder `.` | Refused with `not-consented`. |
| Supply `/outside/customers` through `--add-file` | Reduced to `customers`, selecting `/content/customers` if it exists. |

Draft narrowing matches any directory component, whereas listing groups by top-level folder. Added paths lose everything except their basename.

Smallest fix: use the listing’s exact folder-membership predicate for numbered choices, including `.`. Resolve added paths against the survey root and reject outside destinations instead of substituting a namesake.

The new ordering tests lack nested duplicate folder names and root-folder selection. `tests/test_join_setup_flow.py:3446` tests only the simple added name `engineering`.

**N5. The config parser both misses a valid mutation and refuses ordinary editor use.**  
[gate.py:833](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/gate.py:833), [editor handling:843](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/gate.py:843)

The complete gate allows:

```sh
git config --local -t path gtmbase.id anything
```

It skips `-t` without consuming `path`, then mistakes `path` for the key. Local Git confirmed that `-t path` is valid syntax.

Conversely, `git config --edit` is refused even in an ordinary repository.

Smallest fix: parse valued short options correctly, and scope the editor restriction to protected base configuration.

The “every spelling” test at `tests/test_gate.py:1449` omits type options. The editor test at line 1466 checks only a base.

**N6. A valid config subsection falsely turns an ordinary repository into a base.**  
[write_hook.py:415](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/write_hook.py:415)

This ordinary configuration is treated as base identity:

```ini
[gtmbase "demo"]
    id = ordinary-demo
```

Git identifies its key as `gtmbase.demo.id`; querying `gtmbase.id` returns nothing. The new parser discards the subsection, and the complete hook refuses an ordinary `.claude/settings.json` write without consulting history.

Smallest fix: distinguish exact sections from subsections.

`tests/test_write_hook.py:1514` checks an ordinary repository containing only default configuration.

**N7. The shell fallback resolves parent traversal before symlinks.**  
[write-check.sh:92](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/hooks/write-check.sh:92)

On this Mac, `/etc` points to `/private/etc`. With the protected plugin root `/private/gtm-install`, `/etc/../gtm-install/code.py` physically reaches the plugin. HEAD’s fallback returns no decision because lexical normalization first changes the destination to `/gtm-install/code.py`.

Smallest fix: follow existing path components before interpreting subsequent `..` components, then append unresolved suffixes.

The tests exercise symlinks and parent traversal separately. They do not cover `link/..`. Final-component file symlinks also remain unresolved.

**N8. Index capture refuses valid non-ASCII document paths.**  
[approve_local.py:1400](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/approve_local.py:1400)

A valid prepared proposal targeting `context/stratégie.md` reaches index capture. Git’s default quoted `ls-files -s` output does not equal the literal path, so line 1415 rejects the entry and approval cannot continue.

The probe confirmed that GTM Base accepts this path syntax but rejects its quoted index record. Existing capture tests use ASCII paths.

Smallest fix: request NUL-delimited output with `ls-files -s -z` and parse records without Git’s display quoting.

**N9. Deferred words-file consumption permits replay and deletes replacement input.**  
[wordsfile.py:245](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/wordsfile.py:245), [consumption:254](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/wordsfile.py:254)

Two wording commands can read the same file before either succeeds. If the owner replaces its contents while the first command runs, that command’s eventual `consume_words()` deletes the newer answer. Consumption revalidates the pathname, not the file or contents originally read.

The probe returned the same answer twice, then deleted substituted newer contents. A failed unlink is also ignored, allowing successful commands to reuse the file afterward.

Smallest fix: exclusively claim the input, retain its identity through processing, and consume only that claim. Preserve retryable input on refusal and report consumption failures.

The R7 tests cover sequential success and refusal, not overlapping reads or replacement before consumption.

**Low**

**N10. The extended command walker still skips documented executable variants.**  
[test_skills_and_scripts_agree.py:152](/Users/brandonsellers/Build/gtm-base/tests/test_skills_and_scripts_agree.py:152), [filter:865](/Users/brandonsellers/Build/gtm-base/tests/test_skills_and_scripts_agree.py:865)

Extraction marks `--move-changes`, `--every-seat-updated`, and `--not-now-move` at `skills/stale-check/SKILL.md:206`, `:207`, and `:214` as non-runnable because their section lacks a preceding complete command. They disappear before the exhaustive-coverage assertion.

It also attaches `--for folder` at `join/SKILL.md:129` to `propose-location`, rather than its words-file command. An accepting parser does not establish execution of the intended variant.

Smallest fix: explicitly associate these variants with their commands, reject unassigned executable instructions, and run required flag combinations.

**Disposition of R1 through R11**

“CLOSED” below means the exact previously reported scenario, not the broader guarantee.

| Finding | HEAD status | Rerun result |
|---|---|---|
| R1 | **CLOSED** | Original staged B, working C, and permissions are restored. Newer-state protection fails, N1. |
| R2 | **CLOSED** | Direct external metadata of a known base is refused. History-only combination fails, N3. |
| R3 | **CLOSED** | Missing-map unjoined clone refuses `.git` and `.claude` destinations through history. |
| R4 | **CLOSED** | Injected runtime failure returns `70`; the wrapper enters fallback on nonzero status. |
| R5 | **CLOSED** | Original dot-spelled settings path asks; dot-spelled records path denies. Link/parent combination fails, N7. |
| R6 | **CLOSED** | Explicit protected-config removal and rename into `gtmbase` are refused; `user.name gtmbase.id` is allowed. |
| R7 | **CLOSED** | Second and third revisions succeed. Identical-word revisions change the hash; stale sequential approval is refused. Concurrent revision fails, N2. |
| R8 | **CLOSED** | The diff preserves Markdown syntax and trailing spaces inside a collision-resistant fence, with visible whitespace annotations. |
| R9 | **CLOSED** | File 1 remains `z-profile.md`; narrowed folder 1 remains `b`. Numeric membership still fails, N4. |
| R10 | **CLOSED** | Delete-only preparation produces `remove`; editing the first duplicate produces occurrence 1. |
| R11 | **CLOSED** | `notes.md` is ignored consistently; valid proposals appear consistently; missing targets are excluded from both review lists. |

The replacement R1, R7, R8, R10, and R11 tests now assert the original findings substantially more directly. Remaining weaker assertions are identified above. The isolated shared-edit test at `tests/test_approve_local.py:3151` additionally proves individual operations, not their composition.

**Updated residual risks**

- **Shared hand edits:** Removing occurrences 2 and 3 of three identical headings fails during sequential application because removing occurrence 2 renumbers occurrence 3. The probe raised `heading-missing`. Apply removals against stable original positions. Shared preparation still omits changes outside represented sections.
- **Ordinary hand edits:** Title/opening-only edits remain explicitly refused at `compose_proposal.py:1708`; emptying a section can still fail validation. These are acknowledged limitations, not support for “every ordinary shape.”
- **Concurrency:** Approvals still share a backup directory that `_save_originals()` removes at `approve_local.py:1433`. Identifier allocation and preview finalization remain non-atomic.
- **Provenance:** Words-file issuance is inferred from location and filename. First-draft protection remains bypassable through copied identifiers and edited fields.
- **Fallback boundary:** Historical identification can issue three Git calls. Timeout can transfer a history-only base to the map-only fallback. Unmatched tools and constructed shell paths remain outside demonstrated protection.
- **Live behavior:** The [live checklist:84](/Users/brandonsellers/Build/gtm-base/docs/walkthroughs/2026-09-release-a-live-check.md:84) remains unfilled, including client handling of `ask`.

**CHANGELOG assessment**

| HEAD reference | Assessment |
|---|---|
| `CHANGELOG.md:271`, `:289`, `:291` | Original hand-edit fixes, literal diff rendering, and shared waiting inventory are supported within their stated scope. |
| `:273` | Sequential revisions work. “Every” revision invalidating earlier approval is contradicted by N2. |
| `:275` | Exact folder selection remains overstated, N4. |
| `:277` | The prose-command walk is broader but still incomplete, N10. |
| `:279` | Original recovery is fixed; preserving newer index and permission work is not, N1. |
| `:281`, `:285`, `:287` | Metadata coverage, physical path resolution, and config parsing remain overstated, N3 and N5 through N7. |
| `:283` | Runtime failure-status correction is supported. |
| `:293` | The disclosed limitations remain relevant; add the demonstrated preview race, recovery overwrite, words-file replacement loss, and composed-removal failure. |

**Verdict: Not ready.**

**N1 through N9 block release.** N10 is a nonblocking coverage defect requiring a qualified CHANGELOG claim. Recorded live-check results also remain outstanding.