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

## 2026-09-23, Astra's third verification
- A shortcut that lets almost everything go has to come after every comparison
  that can be made cheaply, not before it. The write check let a path go on the
  strength of its name before asking whether it was a base's history folder
  kept somewhere else.
- A rollback is not finished when the bytes match. Whatever else the run
  touched, the index entry and the permissions, has to be kept, put back, and
  read back on its own, including when the bytes were never written.
- Consume input only after the work it feeds succeeds. A words file thrown
  away before a refusal is somebody's typing lost.
- A summary keyed by a name loses the second thing with that name. Key parts
  by name and position, and derive what is saved from the files, not from the
  summary.
- A documented command lives in sentences as well as in command lines. The
  walk has to read the additions a sentence names, or the sixth broken variant
  ships the way the first five did.
- A test fixture that is missing one of a real base's fixed entries proves
  nothing about a real base. Build it the way a base is really built.

## 2026-09-23, Astra's fourth verification
- A restore has three answers, not two: the kept value, this run's own value,
  and something newer that belongs to somebody else. Keep this run's own value
  before writing, and restore only over the first two.
- Read a file once. A value hashed from one read and a plan built from a second
  read is two files with one approval.
- Consume the thing that was read, not the name it was read from. A rename to a
  name only this command knows is the claim.
- When a listing and a selection both decide membership, they have to call the
  same function. Two rules for "in this folder" is a number that picks something
  else.
- Read machine output in its machine form (`-z`), never its display form.

## 2026-10-05, 0.3.4
- "Refuse once `git` appears anywhere in the command" (the 2026-09-05 lesson above) was too wide: a hyphen counted
  as a word edge, so one flag (`--skip-git-repo-check`) turned every Codex line into a refused line, and the
  refusal reused the parse-failure sentence so nobody could tell why. Decide "is this about git" by what each part
  runs, not by the letters on the line, and give every distinct refusal its own sentence.
- When widening an allowlist of harmless programs, check each one for an option that runs something (`find -exec`,
  `xargs`, `timeout`) before adding it; a harmless word with such an option is a bypass of the whole gate.

## 2026-10-10, 0.3.5
- A linked folder (`content_root`) is the person's own work folder, never a base. A rule written for a base's own
  folders must not loop over `content_root` as if it were another `root`: doing so refused every write in every
  Claude desktop session opened there, because the desktop app puts each session's working folder under `.claude`.
  When the only real risk in a person's folder is one file (here, the settings that can switch hooks off), ask about
  that file and leave the rest alone.
- A guard test only guards if it fails when the code it names is removed. Mutate the branch once and watch the test
  fail before trusting it; the first "base folders still refused" test passed with the changed branch deleted.

## 2026-10-10, Release B finish (Unit 1.7e option D, call 59, Astra's review)
- A check that recognises a command by its words decides only what the person is asked. The control is what the
  library refuses: every writer requires the ticket, so a spelling the hook misses writes nothing. Design the hook so
  every miss fails closed, then let reviewers attack the hook for false descriptions rather than for misses.
- Name the command the person allows exactly: the script's real path from the folder it runs in, nothing else on the
  line, no file opened by the shell, no setting in front. Each of those was a way for "Allowing it saves the draft"
  to describe less than what ran (Astra's findings 1 and 2).
- A suite that holds every approval cannot see a ticket and a writer disagreeing. Keep a test that runs every
  approval with no hold and a real ticket, and prove it by swapping two mappings once and watching it fail.
- A test-only way past a control must live in the tests, never in the plugin (the "standing" ticket did), and it must
  not import the plugin early: an eager import in sitecustomize loaded the real library ahead of a deliberately
  broken copy and hid a failure the suite exists to see.
- A name somebody typed is untrusted wherever it is printed, the lines for the assistant included. Fence by default in
  the printer (`held_apart`), then sweep every write in the script rather than the ones a review names; the first fix
  missed six print sites.
- The installed gate refuses any line holding git beside another program, and any line naming the seat folder or its
  variable, even inside a heredoc. Run git alone on its line, and put edits that mention either into a script file.
- When one module offers a choice and another acts on it, the test must check that what is acted on is what was
  offered, not only what the list shows. The replay fix that skipped a template when offering a segment page made the
  offered page the one version drafting leaves out; only a test against what drafting really reads caught it.
- Skip as little as possible when exempting text from a check. Skipping the whole sources line let "TBD" through, and
  "ends in a dot and a few letters" let "e.g" through; the exemption that held was an item ending in a file ending the
  plugin really reads or lists.
- Test fixtures are written from scratch, with an invented company, invented sentences and invented figures, even
  when the client material is already public. The live check's driver figure reached two test files that way; a push
  scan that only searches for the replay's own keys will not find wording carried in from an earlier session.

## 2026-10-15, 0.3.7
- A guarded folder should be the folder that holds the guarded files, not the whole tree above them. Counting all of
  `~/.claude` as guarded asked about every interpreter run from `~/.claude/projects`, where Claude Code saves large
  tool results for subagents to read back, about sixty prompts in one session. Guard the exact folders, and catch
  a climb back out with `..` by resolving the path rather than by widening the folder.

## 2026-10-19, 0.3.8
- A fail-closed check turns every bug in itself into a false prompt. Catch the narrow, known failure where it happens
  (here a pattern that cannot compile) and keep the catch-all for lines that genuinely cannot be read.
- `shlex` in posix mode throws quoting away. Anything that decides what the shell expands has to keep that
  information from before the split, or quoted program text gets read as shell syntax.

## 2026-10-19, 0.3.9
- A command reader has to know the shell's own words. `do`, `then`, `if`, `!` and `{` stand in front of a command;
  reading them as program names turns every loop over a variable into an "unknown program handed a variable".
- When a real line trips two rules, fix the one that is a bug and name the one that is a policy. sed handed a
  variable can genuinely hide a write; loosening that is a decision, not a fix.

## 2026-10-20, 0.3.10
- Every quote scanner in a shell reader must follow the same rules: inside double quotes a backslash escapes the next
  character, inside single quotes nothing does. One scanner that got it wrong (`split_segments`) both raised false
  prompts and let real writes through, because a mis-split line fails in both directions.
- When fixing a false positive in a security check, test the mirror image too. The same root cause hid two writes.

## 2026-10-20, 0.4.0
- When a security check keeps needing one parser fix per release, the check is asking the wrong question. Judge the
  effect (what changed on disk) instead of the intent (what the text might do), and replay real traffic to prove it.
- Restore by meaning, not by bytes: re-read the file at repair time and put back only the keys that matter, so a
  concurrent legitimate edit is never clobbered.

- `netlify link --id <other site>` on a folder that is already linked does not switch it: it keeps the old link and
  only says how to unlink. Run `netlify unlink` first, then link, then confirm with `netlify status` in the same
  command as any write (2026-11-26: connector variables meant for the live site went to the test site first, and
  were put back before any deploy read them).

## 2026-10-10, Plan 1 of Phases 2 and 3
- "Provable" ownership cannot rest on matching the owner line, the seat's address and history authors: all three are
  claims anyone with the computer can write. Bind each approval to the exact bytes approved, and trust a whole skill only
  as one manifest (every path and hash); per-file approval lets two approved versions be mixed into one nobody approved.
- A list of allowed tools does not keep a scheduled run from an approval: scheduled tasks inherit a person's allow rules
  and can wait on a question. Refuse in the plugin, and claim a second control only where it is independently tested.
- Redacting client figures in a later commit does not remove them from a public repository's history; check before the
  first commit that carries them, not before the push.
