# Correctness and security reviews of the summarize-first build (2026-10-11)

Two review subagents read the summarize-first build (commits from the merge of the replay fixes to 148d430): one for correctness and one for security. The correctness review found five high, seven medium and two low findings. The security review found one high, three medium and two low. Several overlapped. Every finding below was fixed with a test that failed first, in `tests/test_summarize_first_reviews.py`, except where it says otherwise.

## What was fixed

- **A note keeps the file's own words, never the model's copy.** A quote is still matched after spacing, quotation marks, dashes and markup are evened out, but what is kept is the exact stretch of the file it matched. So an address or a key disguised in the copy, with a full-width at sign or a star inside it, is screened as the file has it and refused. A quote that runs across two rows of a table, across a heading, or across a blank line is refused, and so is one holding a fence or the source fence's own brackets. A customer or a figure holding a line break or markup is refused. (Security S2 and S5, correctness H3 and M7.)
- **A segment is one the person settled, or a name the file's own words hold.** A note's segment that is neither is refused, so nothing else reaches the base as a label, and a customer note under a heading that names a settled segment may not name another. (Security S1, correctness M7.)
- **Figures keep their units.** A figure is matched whole, with its currency sign and unit, inside one cited quote, and a number written with no unit never matches one that has one. (Correctness H1.)
- **Headings are checked.** A heading the draft writes may not cite a note, name a customer, or carry a figure, unless the heading is a settled segment's own name. (Correctness H4.)
- **Customers are matched by their names as written.** An ordinary word that is also a customer's name, such as box, is not refused; a short form of a customer's name, without its formal ending, is; and the company's own name is never taken for a customer. (Correctness M11.)
- **Everything the person sees is bound to what is written.** A draft's request remembers the notes it held, and a draft reviewed after the notes were taken again is refused. The support check's answer counts only for the draft and the notes it was asked about. Approval writes only the exact text the person was shown, checked by its digest. (Correctness H5 and M6, security S3.)
- **Nothing is dropped without being said.** A batch whose notes had no fence, or whose file was missing, records every file in it as not noted after the third try, and a line that could not be read marks the batch's files as possibly not fully noted. (Correctness H2 and L14.)
- **The status floor reads the whole place the words sit.** Every heading above the words counts, not only the nearest, and so does the sentence they sit in; where the same words sit in two places, the less settled counts; "value proposition" no longer reads as a proposal; and a question mark counts only in the quote's own sentence. (Correctness M8.)
- **The loop limit counts the right thing.** Only a review the assistant runs counts toward the three tries, a draft that holds up starts the count again, and so does a new request. (Correctness M9.)
- **Lines taken out stay readable.** Each question left in place of a line is a paragraph of its own, and a table's header row needs no citation. (Correctness M10 and L13.)
- **Setup's sections are exempt only in documents written from the notes.** A context change can no longer hide words under one of those headings. (Correctness M12.)
- **Pasted text comes only from the run's own folder.** A file named as a paste from anywhere else is refused, and the notes read only the pastes the run holds. (Security S4.)
- **Footnotes name a file by its folder and its own name,** such as `segments/pricing.md`, so a base never carries the person's home folder layout. (Security S6.)
- Smaller: the request for one batch fills its placeholders in one pass, and the line a third try takes out is written only inside the run's drafts folder.

## Limits that stay

- A notes writer can mark a file with real content as having nothing to note. Nothing checks that, because there is no quote to check; the support check does not read files. (Correctness, residual.)
- Whether a quote that leaves out a qualifier such as "up to" or "pilot" is fair is a judgement the support check makes, not code. The evidence list shows the quote as kept.
- The support check's verdicts are a model's judgement. An answer of supported for every line passes; what the check adds is a second reader who did not write the draft.
- A segment the person left out is still listed in the evidence when the material names customers under it, because the material names it.
