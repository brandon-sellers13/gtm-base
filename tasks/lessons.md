# Lessons

- For identity work, resolve the mark, wordmark relationship, typography, palette, and primitive language before composing product or editorial applications. A polished application mockup cannot substitute for a coherent core identity and can make an unresolved direction feel more finished than it is.
# Lessons

## 2026-09-05, Phase A1 build
- Probing a hook wrapper against a real repository path creates the real `~/.gtm-base` folder; probe only with
  `GTM_BASE_HOME` pointed at a temp folder.
- A whole-command regex scan must exempt path classes (a local path in `cd /Users/...` is not outgoing content) or every
  worktree push is refused. Decide per class whether it applies to commands or only to content.
- A gate that allows anything it cannot parse fails open. The default must be refusal once `git` or `gh` appears
  anywhere in the command, and the false-refusal rate is accepted.
- Two agents editing shared modules concurrently need explicit file ownership and append-only rules for constants.
- macOS caches bytecode under `~/Library/Caches/com.apple.python`; a stale cache made a correct fix look broken.
