# Unit 1.7e rebuilt: security review

Reviewer: a security-review agent run by the orchestrator, read only, on `git diff 8eefb71..c20f00e` in the unit-1-7e worktree, 2026-09-28. Verdict: the approval check can still be passed; three ways need no tooling bypass.

## Findings

1. **High, verified.** One person message answers every showing noted before it, and a showing never has to be displayed. A review notes one showing per due document plus the move offer; a single "yes" to any of them passes all. Fix: a person message answers only the latest showing noted before it; the showing prints a short fingerprint that the assistant's last text before the person's message must contain; the review notes one question at a time.
2. **High, verified.** A transcript line can be appended through Bash in spellings the gate misses (a `cd` then a relative append, a glob, a quote-split folder name, the session variable in the path). Fix: a text pattern cannot close this; recommend a Claude Code permission or sandbox configuration denying writes to the conversation records and the records folder; cheap raises in the plugin (refuse a redirect or write verb with `.jsonl`, `.claude`, the session variable, or a glob; record a digest of the real prompt in the hook and require a match; require sessionId).
3. **High, gate verdict verified.** A nested Claude Code run hidden inside `bash -c` or behind a variable passes the gate and can append a prompt to this session. Fix: recurse into `-c` arguments of shells and eval; refuse `claude` in any position except the allowed subcommands; reject entries whose entrypoint differs from the session's.
4. **Medium, verified.** Acknowledgements and partial answers read as yes ("ok, let me look", "yes to the first one only"); a full-width question mark is not a question. Fix: a yes only when the whole message, after punctuation and polite filler, is a yes phrase; any Unicode question mark is a question.
5. **Medium, inferred.** Keystroke injection (tmux send-keys, screen stuff, osascript keystroke) makes a genuine human entry. Fix: refuse those commands; state as a residual.
6. **Medium.** A script file that imports the library bypasses the check that lives in the library. Fix: the sandbox of finding 2; cheap raises (the write hook refuses file contents naming the library outside the plugin; the gate refuses python reading standard input); reword the claims.
7. **Medium.** The hooks match only Bash and the four file tools; Monitor, PowerShell and command-running MCP tools skip every rule. Fix: add matchers for those tools.
8. **Medium.** The session identity can be pointed elsewhere (`env -i`, an indirect export, a renamed copy of the hook with another config folder). Fix: fail closed when the session variable is absent; fix the transcript folder at session start from the real payload; refuse `env -i` and config-folder assignments; glob-aware matching of the hook's files.
9. **Low, verified.** A hard link to the transcript beats the write hook. Fix: refuse edits to a file matching a recorded transcript's device and inode, or any `.jsonl` with more than one link.
10. **Low, inferred.** A stopped move that is put back re-runs the whole move without a fresh yes. Fix: only finishing a landed run skips the yes.

## Residuals

No check inside the plugin can stop code running as the same user; the durable control is Claude Code's own permission or sandbox configuration denying writes to the conversation records and the records folder. Entries from the VS Code and SDK clients carry no origin field on this machine, so approvals there refuse (fails safe). Scheduled prompts and loops were not observed.
