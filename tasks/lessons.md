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

## 2026-09-20, the release A review, part two
- A hook matcher is a list of tool names, so a check declared on one tool is a check
  with a hole the width of every other tool. Both reviewers found the same one.
- Making a check fail closed moves work into the tests, not out of them: about thirty
  scenarios were about what happens further down a path than the rule that now stops
  everything. One shared helper standing where the unshipped step will stand, with the
  reason in its docstring, beat thirty edited assertions.
- A first draft the product writes and a correction a person approves have to be told
  apart by the exact text the product writes, registered as a constant. Guessing at
  what an unfinished edit looks like would refuse somebody's own wording eventually.
- `find . -not -path "./.git/*"` is read by the plugin's own check as a command about
  the shared copy and refused. Name no folder that reads as the version-control tool
  on a command line, in this repository.

## 2026-09-20, the release A reviews
- Test the command a skill tells the assistant to run, taken from the skill's own text, not the library behind it and not a hand copy of the command. Five defects of that kind shipped across four rounds before the walk read the text itself.
- A test payload must be shaped like what the real client sends. A fallback that refused every write passed its tests because the payloads had no transcript path.
- A fix to a safety rule is new code and needs its own outside look. Most findings after the first round were introduced by the round before.
- A sentence that makes a claim about a state that varies is a bug, in the product and in the CHANGELOG. Put each sentence in every state that can produce it.
- When a rule is relaxed for one case (unsaved edits allowed for a hand edit), scope it to exactly that case and ask what the failure and the success path each do to the person's bytes.
- Writing a file is not finished until it has been read back and compared.
- Never write a client's file names into a public repository; the names alone carry segments and prospects.
