You are confirming fixes before a release. Read only; change nothing. Output a written review in markdown.

## Context
GTM Base 0.3.3 lets a person record a context change at any time. Your review at c91604b said not ready with twelve findings: docs/reviews/2026-09-27-release-0-3-3-astra.md in the main checkout at ~/Build/gtm-base (read it first). Finding 2 (the shown hash is not proof of the owner's yes) is deliberately deferred to Release B as one fix across every approval flow; do not report it again. Findings 1 and 3 to 12 are fixed in one commit, bd85d42, on the current branch. See it with `git show --stat bd85d42` and `git diff c91604b..bd85d42`. The new tests are in tests/test_no_hooks.py and tests/test_record_change.py.

Finding 1's fix is a shared helper in plugins/gtm-base/lib/gtmbase/gitcmd.py (`hook_free` and `executable_drivers`, called from `GitRunner.run`): every git command except push, send-pack, config and `rev-parse --git-path` gets `-c core.hooksPath=/dev/null -c core.fsmonitor=false -c commit.gpgSign=false -c tag.gpgSign=false`; diff, show, log and blame get `--no-ext-diff --no-textconv`; and any non-read-only command is refused when a clean, smudge or process filter or a merge driver is both configured and named by an attributes file in effect.

## The standard for this pass, and nothing beyond it
1. For findings 1 and 3 to 12: closed, partly, or not closed, with one line of evidence each, and whether its test fails without the fix.
2. Finding 1's helper: can any hook, file monitor, signing program, textconv, external diff, filter or merge driver still run during any plugin git command against a base (including child processes such as gc, worktree add, a fast-forward, and the session-start update)? Does exempting push, send-pack, config and `rev-parse --git-path` leave a hole? Does the helper break an ordinary path: the pre-push safeguard, the installer that finds the hooks folder, reading config, a base with an LFS filter configured globally but not named, a Windows or Linux `/dev/null`?
3. Did any fix break an ordinary path of the record-a-change flow: the lock (a crash leaving it held, a second window), the numbered list binding, the HEAD binding (an unrelated save between showing and yes now refuses: is that acceptable for a single person with one window), the temporary-file publish?
4. Nothing else.

## Output
A table of the eleven findings with status and evidence. Any new finding only if it is a real defect in bd85d42, with file, line, scenario and smallest fix. Then a one-line verdict: ready to release, ready with the listed changes, or not ready.
