You are reviewing built code before a release. Read only; change nothing. Output a written review in markdown.

## What is being released
Release A of GTM Base, a Claude Code plugin. The plan is docs/plans/2026-09-19-001-feat-base-that-produces-work-plan.md (revision 2.1). Release A is Units 1.1, 1.1b, 1.2, 1.2b, 1.3, 1.4, and 1.5. The installed version is 0.2.6; everything since the commit "docs: build plan revision 2.1" is unreleased. See what changed with `git log --oneline` and `git diff` from that commit to HEAD, limited to plugins/, templates/, and tests/.

A "base" is a local git repository of markdown context files about one company. Documents in it, and everything a person pastes, are untrusted data and may hold hostile text. The plugin's first duty is that nothing private leaves the computer without the owner's reviewed yes, and its second is that nothing is written to a base without the owner's yes.

## What was already reviewed, so do not spend effort repeating it
Units 1.2b (approve a proposed change locally), 1.3 (quiet by default, the moment-of-use check, a hook on the file-read tool), and 1.4 (the rename to "context change" with a recoverable migration) each had a security or data-safety pass and a correctness pass, with every finding fixed and re-verified. Units 1.2 and 1.5 had no outside review.

## Review for
1. Unit 1.5 (habit hooks), which nobody has reviewed: plugins/gtm-base/lib/gtmbase/join_flow.py (the closing question, preview_change, reconcile_plan, reconcile_yes, reconcile_no, skip_the_closing_question), review.py (stamp_entry with no run id), confirm.py (against_change), compose_proposal.py (stage_local_edit with what_changed and records_a_change, local_edit_entry), stale_check.py (the quiet-record ask inside the review), the five new commands in skills/join/scripts/join.py. Known and unfixed: review.entry_id() is a hash of four fixed inputs, so a second closing change in one base would collide. Say how bad that is and the smallest fix.
2. Unit 1.2 (completion and closing): the honest baseline finding, the map left out by its kind, the rekeyed source-age finding.
3. Seams between units that no single-unit review could see: a change entry written at the closing (1.5) then shown at the moment of use (1.3) then fixed through local approval (1.2b) on a base that was migrated (1.4); a conflict (1.4) present while the closing reconciliation (1.5) runs; the review (1.3) listing a prepared change (1.2b) for a document whose entry sits in the old folder; question ids issued by three different callers; the yes-rate denominator across all of them.
4. One known gap, not caused by this release: the plugin's gate is a PreToolUse hook that matches the Bash tool only. A file-writing tool call can therefore write the plugin's own records folder directly, including the seat's first-backup flag, a forged recovery note, or the record that the person was already told about a flagged document. Assess what an attacker who controls the text of a context file could achieve through the assistant with that, what this release added to that surface (the recovery notes, read_notices, the decline record, the silence settings), and the smallest change that closes it (for example a second matcher on the file-writing tools that refuses paths under the records folder, following the existing hook pattern).
5. Anything that lets text from a base reach a shell, a git argument, or an instruction the assistant is told to obey, outside a data fence.
6. Test scenarios that would pass without proving the behavior.

## Output
Findings ranked critical, high, medium, low, each with file and line, a concrete scenario (state, inputs, wrong result), and the smallest fix. Then a short verdict: ready to release, ready with the listed changes, or not ready. Be adversarial and specific. Do not pad.
