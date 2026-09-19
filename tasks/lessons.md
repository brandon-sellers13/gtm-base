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

## 2026-09-19, the plan reviews
- A test that fixes a moment and separately hard-codes the day it fell on passes only in the zone it was written in.
  Three tests in `tests/test_review.py` failed on a machine set to Hawaii time. `tests/run.sh` now fixes the zone.
  Run the suite before trusting a handoff's test count.
- A "happy path" that passes because a fake stands in for the shared copy proves nothing about a base that has none.
  Both reviewers found that no proposal could complete on the only real base. Build at least one integration test on a
  base made the way `create_base` really makes one.
- A long script passed to the shell inline is read by the plugin's gate, and prose that mentions the version-control
  tool by name gets the whole command refused. Write the script to a file with the file tool and run the file.
