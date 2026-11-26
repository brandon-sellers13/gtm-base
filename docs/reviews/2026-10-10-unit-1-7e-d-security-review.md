# Unit 1.7e, option D: security review

Reviewer: a security-review agent, read only, on `claude/release-b-finish-1e1203..unit-1-7e-d`, 2026-10-10. Probes of `approval.find` only; the ticket side was read, not run, because the live GTM Base gate in the reviewer's own session refused a probe that set the seat-folder variable.

1. **High.** Production code honoured "standing" tickets, made for the test suite, that never expire and are never used up, and the hook's text checks are plain substring matches that shell quoting defeats (`approve_local.p''y`, `GTM_BASE_APPRO''VAL`). One data file in the approvals folder would have allowed every approval for every later session without a question. Fix: no standing ticket in production code; tests hold their approval through a test-only file.
2. **Medium.** The sentence could describe a different action from the one the script runs: a line with two action flags (`--approve --drop`, `--not-now-move --record-change record`) was asked as the first while the script ran another, and any ticket opened any gated write. Fix: a line asking for more than one thing is refused, and the ticket says which writes it opens.
3. **Medium.** A rewritten line was accepted on its ticket alone, so a live ticket the assistant learned could carry any other command. Fix: the ticket holds a digest of the exact line it was made for.
4. **Medium.** Answers held in the seat folder (pending confirmations, the move's and approvals' notes) are acted on later without a ticket. Not fixed here: it is the decision recorded in 0.3.0 that seat files are not checked for tampering, because a key kept beside them could be read by the same assistant; the seat folder is guarded by the file-tool check and the command check's text rule.
5. **Low.** A setting placed before the command (`PYTHONPATH=<dir> python3 confirm.py ...`) was accepted as part of a clean approval line. Fix: any setting on an approval line refuses it.
6. **Low.** A plain file where the approvals folder should be refuses every approval with a sentence that says only to ask again. Recorded, not fixed.

Checked and fine: the not-gated list; parsers loaded by a fixed path; the rename before the age check makes a ticket single use. Also noted: `--dismiss-quiet-record` silences a reminder and is not in the documented not-gated list (now added, with its reason).
