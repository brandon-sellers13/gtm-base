This is the final, deliberately narrow check on Release A of GTM Base. Your fourth report is docs/reviews/2026-09-23-release-a-verify-4-astra.md (findings N1 to N10, plus the residual about composed removals). They are reported fixed in commit 9d52ce1. Commit 1ebc799 then made every list of file names read from git immune to git's quoting of unusual names. HEAD is 1ebc799. Read only; change nothing. Output a written review in markdown with line numbers at HEAD.

The owner has set the release standard for this pass. Answer exactly two questions and do not open a new general hunt; anything else you notice goes in a short "noticed, not assessed" list at the end.

## Question 1: are N1 to N10 closed?
For each of N1 to N10 and the composed-removal residual, rerun your own scenario at HEAD and say CLOSED or STILL OPEN, with evidence. Say where the builder departed from your smallest fix (N1 keeps newer permissions without holding the recovery note; N4 refuses a nested added folder rather than widening it; N7 also follows a final file link; N10 uses an explicit table tying prose flags to commands) and whether each departure is sound.

## Question 2: did these two commits break any ordinary path?
Check, by reading the code and by in-memory probes where you can, that each of these still works as the skills document it: a full setup run; a closing with a context change, a no on one required document, a real replacement, and a local approval; a hand edit with the question answered ending in a local approval, on a plain name and on an accented name; a second and third wording revision; "review my base"; each of the three moment-of-use answers; the update of how context changes are stored (check, then move); an ordinary write in an ordinary repository, including its assistant settings file and `git config --edit`; and ordinary pushes from an ordinary repository, from a folder that is not a repository, and from the plugin's own repository. Say WORKS or BROKEN for each, with the failing file and line.

A known, recorded limit you should confirm rather than re-report: a hand edit to a document whose name contains a space is prepared and shown and then stops at approval, with a sentence saying nothing was applied or lost.

## Output
The two answers, then the short "noticed, not assessed" list, then the verdict against this standard: ready to release (N1 to N10 closed and no ordinary path broken), or not ready (naming exactly which item fails).
