You are reviewing a small fix release before it ships. Read only; change nothing. Output a written review in markdown.

## What is being released
GTM Base 0.3.2, a fix to the installed 0.3.1 of this Claude Code plugin. The live check (docs/walkthroughs/2026-09-release-a-live-check.md, step 5) found that approving a hand edit was refused as "unsaved edits" because macOS Finder wrote an untracked `.DS_Store` into the base. The fix is on the current branch after main's d8d37e5: see `git log --oneline d8d37e5..HEAD` and `git diff d8d37e5..HEAD`. A new shared predicate (plugins/gtm-base/lib/gtmbase/unsaved.py) decides unsaved work for every clean-tree check; untracked operating-system clutter is ignored; refusals name the unsaved files in plain words; both company-base templates ignore clutter; four skill files gain relay rules. Tests in tests/test_os_clutter.py.

A base is a local git repository of markdown context files. Nothing may be written to it without the owner's yes, and nothing private may leave the computer without the owner's reviewed yes.

## The standard for this pass
1. Is the one real bug fixed on every path (approve a hand edit or prepared change, the context-change move and its recovery, the review's pull, setup writes, a confirmation on a base with no shared copy, the session-start update, setup's folder checks)? Is any clean-tree check left unrouted?
2. Can ignoring clutter ever let a write save over, stage, commit, delete, or send something it should not: a tracked clutter file that changed, a staged one, a clutter-named file that is really content (for example a folder named like a clutter folder holding markdown), a symlink named `.DS_Store`, a name with `._` in front of a real document, clutter inside the context folder? Does the gate's check before a send still read everything it read before?
3. Do the refusals that now name files ever read out a path, an identifier, or a hostile name, and are they plain?
4. Is any ordinary path broken?
Nothing else.

## Output
Findings ranked critical, high, medium, low, each with file and line, a concrete scenario, and the smallest fix. Then a one-line verdict: ready to release, ready with the listed changes, or not ready. Be specific. Do not pad.
