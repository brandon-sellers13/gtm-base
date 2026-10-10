# Unit 1.7e rebuilt: two correctness reviews

Two correctness-review agents, read only, on the diff from 8eefb71 to c20f00e in the unit-1-7e worktree, 2026-09-28. Their findings overlap; together they show that reading a yes out of the person's words, and tracking which conversation is which, are the two sources of nearly every defect.

## Reading the person's words
- Only the first message after a showing counts, and a refusal keeps the showing, so after any first reply that is not the expected answer (a question, a "hmm", a no) the item can never be approved, while the refusal sentence says to "say yes yourself". Quiet, record-change's later documents, the join closing's second document, and a prepared change all dead-end.
- The review records every question at once, so answering items one at a time refuses every item after the first whose answer differs, and one yes can answer several items.
- Ordinary yes wording is refused: "Yes, I approve this change", "Yes, record the change", "Yes, that's what I want", any reply over eight words; "Yes, no changes needed" reads as a no.
- Opposite meanings are accepted: "don't drop it" reads as drop; "No, it's already out of date" reads as already reflects; "yes, nothing to fix" reads as fix.
- A message typed while the assistant is working is stored as a queued-command attachment and never read.
- Clients before Claude Code 2.1.187, and the VS Code extension observed, write no origin field, so every approval refuses there with a misleading sentence.

## Tracking the conversation
- The showing and the approval look the session up in different ways; the base's recorded session goes stale after a restart outside the base, and any other Claude Code window opened on the account during setup breaks every setup approval, which sending a message does not repair.
- After the move to the new layout, record-change keys the showing and the answer on different paths.

## Other
The command guard blocks ordinary commands in other projects (a data path under a projects folder, "claude" inside a quoted commit message, claude --help or update). Several tests write the person's message into every session they can find, which hides the session defects, and one test asserts the dead end as correct.

## Orchestrator's conclusion
Both classes of defect come from the design, not the implementation. The orchestrator proposed to Brandon replacing it with Claude Code's own permission prompt (option D), which a plugin hook can force and which auto mode still shows the person.
