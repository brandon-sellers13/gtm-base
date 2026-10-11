# Correctness review of the replay defect fixes (2026-10-10)

The fidelity replay of 2026-10-10 found two defects. Both were fixed on the branch `replay-defect-fixes`, cut from the replayed build (commit 114a73a), and kept off the finish branch so the replayed build stays exactly as it was run. The first fix is commit 211a0ad. A correctness review subagent then read that commit and found five things. This record says what each one was and what became of it.

## What the review found

1. **Medium. A change entry's source was still checked.** The first fix skipped only the `sources:` line of a profile or positioning. A change entry names its file on a `source:` line, so a change entry citing `todo.md` was still refused. Fixed: the check now treats a change entry's `source:` line the same way. Test: `test_a_change_entry_may_cite_todo_as_its_source`, which failed before.
2. **Medium. Skipping the whole sources line let unfilled text through.** A draft whose sources line said `[TBD]`, held a long dash, or used one of the words that say nothing would have passed. Fixed: only an item shaped like a file's name, with or without the date beside it, is left out of the check, and everything else on the line is still read. Test: `test_the_sources_line_still_checks_what_is_not_a_file_name`, which failed before.
3. **Low. A sources list written one item per line was still refused.** Fixed: items listed under `sources:` or `source:` one per line are treated the same as items inside brackets. Test: `test_a_sources_list_one_item_per_line_may_cite_todo`, which failed before.
4. **Low. A final version that is only a template could be offered.** If the version named final was a blank form, the list of segment documents offered it. The first fix offered the best version that was not a template instead, but the confirm pass below found that this made things worse, so it was replaced. The version offered is now always the one drafting keeps, and the blank-template case is a limit recorded below.
5. **Low, and older than this fix. The version offered can still differ from the version a draft reads in one rare case.** The list of segment documents groups the versions it can read. If the final version of a page can be listed but not read when drafting begins, the draft may read a different version from the one offered. This was true before the fix and is unchanged by it. It is recorded here as a known limit rather than fixed, because fixing it means changing how drafting chooses among versions, which the replayed build should not change.

## The confirm pass (commit 0dcc457)

A second correctness review read both commits together. It confirmed that findings 1, 2 and 3 are fixed, that the rewrite changes only the text the word checks read and never what is parsed, and that no other setting's list items are skipped. It found three more things.

- **C1, medium. The version offered could differ from the version a draft reads.** The fix for finding 4 skipped a template when offering, but drafting does not skip it. It keeps the version that ranks first, so the page the person picked was the one version the draft left out. Its test for a template was also looser than drafting's, so a heading such as "buyers who contemplate switching" was wrongly taken for one. Fixed: the version offered is always the one drafting keeps. Test: `test_every_version_offered_is_the_one_a_draft_reads`, which failed before and checks both headings against what drafting really reads.
- **C2, low. Text that only ends like a file's name was skipped.** "TBD pending interviews e.g" or "todo see v2.1" passed as a file name. Fixed: an item counts as a file's name only when it ends in a file ending GTM Base reads (`.md`, `.markdown`, `.txt`, `.csv`) or lists for the assistant to read (`.pdf`, `.docx` and the rest). Test: `test_text_that_only_ends_like_a_file_is_still_checked`, which failed before.
- **C3, low. Some ways of writing the sources list were still refused.** A quoted file name, an item written one per line with no indent, and `sources :` with a space were refused even though the settings block accepts them. Fixed. Test: `test_every_way_of_writing_the_sources_may_cite_todo`, which failed before.

## Limits that stay

- When the version whose name says final is a blank template, drafting reads that template, and it is the version offered. Changing that means changing how drafting ranks versions, which this fix leaves alone so the replayed build's drafting is unchanged.
- Finding 5 above, a final version that can be listed but not read when drafting begins, is unchanged.
- A file named without an ending, such as `TODO`, and pasted text whose label holds "todo" or "tbd" are still refused, because neither is shaped like a file's name.

## What a file's name looks like to the check

An item counts as a file's name when it has no brackets or commas, ends in a file ending GTM Base reads or lists, and is followed by nothing or by a date in brackets, such as `(2026-09-17)`. One pair of quotation marks around it is allowed. Pasted text is labelled in the person's own words, so it is not shaped like a file's name and is still checked.
