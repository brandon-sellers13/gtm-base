# Correctness review of the replay defect fixes (2026-10-10)

The fidelity replay of 2026-10-10 found two defects. Both were fixed on the branch `replay-defect-fixes`, cut from the replayed build (commit 114a73a), and kept off the finish branch so the replayed build stays exactly as it was run. The first fix is commit 211a0ad. A correctness review subagent then read that commit and found five things. This record says what each one was and what became of it.

## What the review found

1. **Medium. A change entry's source was still checked.** The first fix skipped only the `sources:` line of a profile or positioning. A change entry names its file on a `source:` line, so a change entry citing `todo.md` was still refused. Fixed: the check now treats a change entry's `source:` line the same way. Test: `test_a_change_entry_may_cite_todo_as_its_source`, which failed before.
2. **Medium. Skipping the whole sources line let unfilled text through.** A draft whose sources line said `[TBD]`, held a long dash, or used one of the words that say nothing would have passed. Fixed: only an item shaped like a file's name, with or without the date beside it, is left out of the check, and everything else on the line is still read. Test: `test_the_sources_line_still_checks_what_is_not_a_file_name`, which failed before.
3. **Low. A sources list written one item per line was still refused.** Fixed: items listed under `sources:` or `source:` one per line are treated the same as items inside brackets. Test: `test_a_sources_list_one_item_per_line_may_cite_todo`, which failed before.
4. **Low. A final version that is only a template could be offered.** If the version named final was a blank form, the list of segment documents offered it. Fixed: the best version that is not a template or a read-me is offered. Test: `test_a_template_version_is_never_the_one_offered`, which failed before.
5. **Low, and older than this fix. The version offered can still differ from the version a draft reads in one rare case.** The list of segment documents groups the versions it can read. If the final version of a page can be listed but not read when drafting begins, the draft may read a different version from the one offered. This was true before the fix and is unchanged by it. It is recorded here as a known limit rather than fixed, because fixing it means changing how drafting chooses among versions, which the replayed build should not change.

## What a file's name looks like to the check

An item counts as a file's name when it has no brackets or commas, ends in a dot and one to eight letters or digits (such as `.md`, `.txt` or `.csv`), and is followed by nothing or by a date in brackets, such as `(2026-09-17)`. Pasted text is labelled in the person's own words, so it is not shaped like a file's name and is still checked.
