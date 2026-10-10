# Call 59, segment names in recording a change: correctness review

Reviewer: a correctness-review agent, read only, on commit d753c24 on claude/release-b-finish-1e1203, 2026-10-10. Verdict: the data fence holds, the join flow is unchanged, and no new path lets a name out of the fenced text. Four findings, all fixed with a test that failed first (tests/test_segment_names.py, TestTheReviewOfCall59 and TestEveryNamerIsOneThatReadsNoFileName).

1. Medium, verified. The cap on the four lines was measured on the names, so a change to the profile, the positioning and three segments with names of about forty characters was refused where it used to fit. Fixed: when the names overflow, the segments are counted as before.
2. Low to medium, verified. A segment was looked up by file name alone, so a copy in a folder under the segments folder, or the same file in the older segments folder, read out the live segment's name. Fixed: only a file directly in a segments folder is named, and neither is named when both folders hold it.
3. Low, verified. Letters that draw nothing (the Hangul fillers) and modifier letters that look like quotation marks passed the shape check. Fixed: category Lm and any character named a filler are refused.
4. Low, read. The guard on the lint's trust of `name_of` missed namers handed over by position, as defaults, or bound to the name by assignment. Fixed, with a test that the guard catches each.

Also done: the namer set after a change is written falls back to counting if it cannot be read, so a written change is never reported as unwritten.

Residual, accepted: names are read again at each step, so a profile changed between the showing and the answer can name a segment differently in the answer. A name in a script with no letters A to Z makes no file name and stays "one of your segments".
