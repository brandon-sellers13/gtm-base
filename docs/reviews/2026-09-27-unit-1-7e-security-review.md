# Unit 1.7e, a yes only a person can give: security review

Reviewer: a security-review subagent started by the Unit 1.7e builder, on the diff from release-b to unit-1-7e (commits f0eaa45 and 7c5d297), 2026-09-27. Recorded here by the orchestrator. Verdict: the approval check can be passed without a real message from the person.

## Findings

1. **High, verified.** The assistant can raise the person-message count by running the plugin's own hook script (`hooks/person-message.sh` or `scripts/person_message.py`) with a hand-made payload; the gate allows it because the command names neither git nor the records folder. The claim in person.py and the CHANGELOG that nothing an assistant runs can raise the count is false. Smallest fix: verify a genuine person entry in the session's own transcript after the showing, instead of trusting a counter the hook script writes; refuse commands that run the hook's entry points; correct the claim.
2. **High, gate verdicts verified, effect inferred.** Assigning `CLAUDE_CODE_SESSION_ID` inline or by export, and starting a nested `claude` session with `--session-id` or `--resume`, both pass the gate and let the assistant point approvals at a session it controls. Smallest fix: refuse commands that assign that variable and commands that start a Claude Code conversation; bind the session to the transcript this process tree writes.
3. **Medium, verified by reading.** The check sits in the script entry points, not in the library functions that write, so a `python3 -c` call into the shipped library approves with no check. Fix: move the check into every writing library function.
4. **Medium, verified.** A showing shown again keeps its first count and is never used up, so a stale showing stays approvable, and any later message (even "no") counts. Fix: a showing is used once; hand-back showings get a fresh value; optionally a short window.
5. **Low, verified.** If the person folder is replaced by a link, the hook writes a lock file outside the records folder and its cleanup can delete other records. Fix: refuse a linked folder; check the path before locking and before cleanup.
6. **Low, inferred.** The move check is skipped whenever a stopped-partway journal file exists, even a forged one. Fix: skip only for a journal `_checked_journal` accepts.
7. **Low, verified by reading.** The draft is digested once and read again later. Fix: read once and pass the verified bytes on.

## Residual risks the reviewer named

- The design proves only that some message arrived after the showing, not that it was a yes.
- Nothing inside the plugin can stop an assistant with open Bash access that is deliberately working around it; the CHANGELOG should say so plainly.
- `CLAUDE_CODE_SESSION_ID` is undocumented; if it stops matching, every approval refuses (safe, but the product stops working).
- Not checked live: whether automatic turns (a background command finishing, scheduled wakeups) fire the prompt hook.

## Testing gaps

No test runs the hook's entry points through the gate; none covers the session variable or a nested session; none covers showing a question again and answering at once; none covers a linked person folder.
