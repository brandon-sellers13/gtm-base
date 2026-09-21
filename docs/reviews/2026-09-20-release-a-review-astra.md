# Release A review (Astra, through the Codex CLI)

Date: 2026-09-20. Brief: `docs/reviews/2026-09-20-release-a-review-brief.md`. Read-only sandbox, high reasoning effort. The text below is the reviewer's own, unchanged except that link targets were made relative to this repository. A second, independent reviewer worked from the same brief; every finding from both was fixed test-first before the release.

Reviewed `e27f941..83370e8`. Verification used source inspection and read-only, in-memory probes. The filesystem-writing test suite was not run.

1. **High: File-writing tools can forge consent and recovery records.**  
   [hooks.json:5](../../plugins/gtm-base/hooks/hooks.json:5)

   A malicious context file that persuades the assistant to use `Write` or `Edit` can bypass the Bash-only gate. It can forge `first_push_reviewed` and clear the source-read marker, allowing confidential prose past consent checks if it does not match the secret scanner.

   Release A expands the consequences:

   - Forged recovery records can cause `approve_local.show()` to restore or delete base files before approval, through [approve_local.py:1030](../../plugins/gtm-base/lib/gtmbase/approve_local.py:1030).
   - Forged `read_notices` can suppress a document warning.
   - Forged decline records can postpone the quiet-record reminder indefinitely.
   - Forged silence settings can suppress moment-of-use warnings.

   **Smallest fix:** Add a file-writing-tool matcher that refuses records-folder writes after resolving relative paths, `..`, and symlink aliases. Move assistant-written drafts outside that protected folder, or permit only exact validated draft filenames. Exempting all of `join/` would also expose its consent records.

2. **High: A closing “yes” can commit unrelated confirmations as the owner.**  
   [confirm.py:1046](../../plugins/gtm-base/lib/gtmbase/confirm.py:1046)

   Suppose the confirmation file contains an uncommitted line confirming change B. The owner answers yes about change A. `against_change()` appends A, stages the entire file, and commits both lines. The currency calculation trusts commit authorship, so B becomes confirmed without its own approval. This path also permits writes on a nondefault branch.

   **Smallest fix:** Run the existing clean-tree/default-branch precondition before appending. Test that unrelated uncommitted confirmation lines leave both the file and HEAD untouched.

3. **High: The hand-edit instructions put untrusted prose into executable shell syntax.**  
   [propose-change/SKILL.md:66](../../plugins/gtm-base/skills/propose-change/SKILL.md:66)

   The prescribed `--what-changed "<their words>"` interpolation executes shell substitutions in pasted text. For example, `We now quote $(printf twenty) seats` is altered before Python receives it; hostile substitutions can execute commands. Double quotes do not protect this boundary. Expansion happens even though the CLI currently rejects the new flags.

   **Smallest fix:** Accept the answer through `--what-changed-file`, or explicitly require proper shell escaping. Test literal substitutions, backticks, quotes, and newlines arriving unchanged.

4. **Medium: The hand-edit habit hook is unreachable through the shipped command.**  
   [propose.py:68](../../plugins/gtm-base/skills/propose-change/scripts/propose.py:68), [propose.py:135](../../plugins/gtm-base/skills/propose-change/scripts/propose.py:135)

   The skill requires `--what-changed` and `--records-a-change`, but the parser accepts neither. Verified result: exit code 2, “unrecognized arguments.” Removing the flags silently takes the old path, which never forwards the business-change answer.

   **Smallest fix:** Add and forward the inputs, using the safe transport above. Exercise the actual CLI; the current library-only tests cannot catch this.

5. **Medium: Closing entries reuse one ID, blocking subsequent changes or creating a migration conflict.**  
   [review.py:275](../../plugins/gtm-base/lib/gtmbase/review.py:275), [review.py:465](../../plugins/gtm-base/lib/gtmbase/review.py:465)

   Every closing produces `stg-bbca87f4c11717e1`. In the new layout, the second approval fails with `file-exists`; it does **not** overwrite the first entry. If the earlier entry remains under `work/decisions`, the new-path-only existence check permits a different entry under `work/changes` with the same ID, creating a conflict.

   **Smallest fix:** Incorporate the actual setup-run identifier into ID generation while keeping the entry’s `run_id` field absent. Check both layouts before writing. Test successive closings on migrated and unmigrated bases.

6. **Medium: A closing “no” can be resolved by approving a TODO instead of correcting the document.**  
   [join_flow.py:1528](../../plugins/gtm-base/lib/gtmbase/join_flow.py:1528), [stale_check.py:512](../../plugins/gtm-base/lib/gtmbase/stale_check.py:512)

   Reconciliation prepares “Update needed … This section should reflect that change.” Local approval can insert that text and clear the flag while the obsolete business claim remains. The new closing workflow never requires replacing this placeholder before approval.

   [test_join_setup_flow.py:799](../../tests/test_join_setup_flow.py:799) explicitly treats the presence of “Update needed” as proof that the document was corrected.

   **Smallest fix:** Require a real replacement draft before presenting the proposal for approval; keep placeholders nonapprovable. Test that the obsolete claim disappears and the approved replacement appears.

7. **Medium: The closing reports an all-clear immediately after an unresolved “no.”**  
   [stale.py:508](../../plugins/gtm-base/stale.py:508)

   Both documents have drafted confirmations. A closing change affects the profile, whose source has no date. The owner answers no. The computed report correctly flags the profile, but `first_run_finding()` checks source-age items instead of active flags and returns “Nothing is out of date yet.” Verified with an in-memory calculation.

   **Smallest fix:** Check unresolved document flags and conflicts before returning an all-clear, including changes awaiting approval.

8. **Medium: Answering an expired question creates an unseen question in the yes-rate denominator.**  
   [scripts/moment.py:128](../../plugins/gtm-base/scripts/moment.py:128)

   Q1 expires before the person answers “use as is.” The answer handler first performs a fresh check, issuing and logging Q2. It then marks Q1 excluded, leaving unseen Q2 unanswered. An in-memory CLI probe confirmed that the denominator still contains one unanswered question. “Already reflects” similarly leaves Q2 behind while rejecting Q1.

   **Smallest fix:** Inspect without issuing a question on the answer path, then validate the supplied ID. Issue replacement questions only when displaying them. Test through the CLI, not just the library.

9. **Medium: The closing preview exposes untrusted instructions outside a proper data fence.**  
   [join_flow.py:1375](../../plugins/gtm-base/lib/gtmbase/join_flow.py:1375)

   A valid draft containing a heading such as “Instructions for the assistant” followed by a command passes parsing and screening. `preview_change()` prints it as ordinary Markdown surrounded only by HTML comments. The body-derived summary has the same problem. This creates an instruction-injection surface; it does not guarantee assistant obedience.

   **Smallest fix:** Reuse the existing protected data renderer for both outputs, with a data-only warning. The current marker-presence tests should verify containment of hostile headings and instructions.

10. **Medium: The approved preview differs from the entry written to disk.**  
    [join_flow.py:1371](../../plugins/gtm-base/lib/gtmbase/join_flow.py:1371), [review.py:307](../../plugins/gtm-base/lib/gtmbase/review.py:307)

    The preview presents `noted_by` as correctable. A verified draft preview showed `Alice`; stamping changed the saved value to `owner@example.com`. Correcting that field therefore does not survive approval.

    **Smallest fix:** Finalize all plugin-controlled fields before preview, explain any fixed attribution, and approve the exact finalized artifact.

11. **Medium: “Skip” stops working after the closing draft is shown.**  
    [join/SKILL.md:431](../../plugins/gtm-base/skills/join/SKILL.md:431), [drafting.py:607](../../plugins/gtm-base/lib/gtmbase/drafting.py:607)

    Step 8 says its four answers work like step 6. Following that instruction for skip invokes the generic skipped-document path, which rejects `change-entry` with `cannot-skip`. The intended reminder dismissal is never recorded.

    **Smallest fix:** Route change-entry skips to `skip_the_closing_question()` and document that command explicitly. Test skipping after preview, not only before drafting.

**Verdict: Not ready to release.** The consent-record bypass and unapproved-confirmation commit violate the release’s primary safety requirements.