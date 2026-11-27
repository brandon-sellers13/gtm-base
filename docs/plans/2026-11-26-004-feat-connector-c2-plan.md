---
title: "C2: reading documents in chat, with the moment-of-use flag"
type: feat
status: approved by Brandon on 2026-11-26 with all five recommended answers; built with C4 and deployed to the test site, end-to-end run in progress
date: 2026-11-26
parent: docs/plans/2026-11-26-001-feat-chat-connector-plan.md (Unit C2)
unit: "C2"
---

# C2: reading documents in chat, with the moment-of-use flag

## What this builds

C2 makes the connector's "read a document" do what the plugin already does in Claude Code: when a recorded context change has overtaken the document someone is about to use, the connector says so before the document is used, shows the change, and offers the three answers (use it as it stands, fix it first, it already reflects this change). It also tells the model which documents exist, so it stops guessing paths.

This is the part of the connector no competitor offers (the roadmap puts it straight after C1 for that reason), so the bar is that chat says exactly what Claude Code would say about the same document on the same day.

## What C1 left, and what the research found (2026-11-26)

- C1's `read_document` (`web/src/lib/connector/tools.ts`) returns any `.md` file from a bound base as it stands, with no flag. The web app's own reader (`web/src/lib/reader.ts`) shows the facts the plugin writes (owner, confirmation lines, open changes) and says plainly that "whether a document is out of date stays the plugin's call". Its "open changes" for a document are only the open changes that name it, with no check of confirmations, so it over-reports.
- The plugin decides in `plugins/gtm-base/lib/gtmbase/moment.py` (the moment of use) on top of `stale.py` (the rules, about 1,240 lines, written so that "two seats reading the same base always reach the same result"). The moment of use fires for one reason only: an open context change names the document and has not been settled for it. Age and unanswered markers never interrupt; they wait for the review. The rules in plain words are in `plugins/gtm-base/skills/stale-check/references/rules.md`.
- A change is settled for a document in three ways, and all three depend on who did something, never on what a file says about who did it:
  1. **An owner's confirmation line** in `work/confirmations/<document>`, dated after the later of the day the change happened and the day it was written down, or naming the change, or written by setup in the same run. The identity is whoever added the line, read with `git blame`. A line added by anyone who does not own the document counts for nothing.
  2. **An accepted record** in `learning/corrections` that names the change, was added by the same commit that changed the document, and carries a hash matching the context files it lists as that commit left them.
  3. **An owner's acceptance**: when the person who brought that record onto the main line (read along its first parent) owns the document, accepting counts as their confirmation on that day. The web app's accept button (W4) builds exactly that merge commit, authored with the owner's verified email.
- Verified on 2026-11-26: GitHub's GraphQL API answers blame (`Commit.blame(path)`, with each range's commit author email). A live query on `brandon-sellers13/gtm-base-test` returned three ranges with author emails. Inferred, to check in step one: the same query works with a GitHub App user token, not only Brandon's own CLI token.
- Not available over GitHub's API in one call: "first parent only" history. It can be rebuilt by walking the main branch's commits and their first parents, which costs one call per page of history.

## Decisions for Brandon (decided 2026-11-26: the recommended answer to all five)

1. **How the connector reaches the same verdict as the plugin.**
   - **Recommended: port the moment-of-use rules to TypeScript and prove they agree with the plugin.** A pure function in the web app mirrors the part of `stale.compute` the moment of use needs: usable changes, changes written down twice, owner confirmation lines, accepted records and owner acceptances, and the "settles this change" rule. A small reader gathers its inputs over GitHub's API: the tree and files the web app already reads, blame for each confirmations file in one GraphQL query, and the commit that brought each corrections record onto main. A parity check runs the plugin's own Python on a set of input fixtures and requires the TypeScript to give the same flags. This is the largest unit in the connector so far, because every rule has to match.
   - Runner-up: a simpler rule that flags any open change naming the document unless an owner's blamed confirmation line settles it, and ignores accepted records. It is quick, but it would keep flagging documents an owner already fixed by accepting a proposal in the web app, which is the main way documents get fixed, so it would cry wolf.
   - Not recommended: a verdict file the plugin writes into the base. Anyone with push access could edit it, and it would be wrong between a web app accept and the next plugin run.
2. **The pause before use.**
   - **Recommended: a flagged document arrives in two steps.** The first answer carries only the flag, the change in its four fenced lines and the choices; the document itself comes back only when the model calls again with the person's choice. Nothing can be written from a document the person has not chosen to use, which is the plugin's "pause" made structural rather than requested. It costs one more call (a few seconds) only when a document is flagged.
   - Runner-up: the flag and the document in one answer, with the instruction to ask first. One call, but the model can skip the question, and the spike showed models fill gaps on their own.
3. **"It already reflects this change" from chat.** Connector decision 5 says approvals stay where a person approves them, and an owner's confirmation is the same kind of statement.
   - **Recommended: the answer links to the document's page in the web app, where the owner confirms it.** C2 adds an owner-only "It already reflects this change" button there. The web app writes the confirmation line that names the change, committed with the owner's verified email so blame attributes it to them, the same way W4 builds its accept commit. Only an owner is offered this answer, as in the plugin.
   - Runner-up: tell the owner to answer in Claude Code. No web app change, but it leaves chat users with no way to clear a flag themselves.
4. **"Fix it first" from chat.** Preparing a fix is a proposal, which is C4.
   - **Recommended: build C4's propose tool in the same release as C2**, so all three answers work in chat from day one. Until it lands, "fix it first" says a fix can be prepared in Claude Code or by the owner.
   - Runner-up: ship C2 first with "fix it first" pointing to Claude Code, and C4 after.
5. **Which documents the connector serves.** Recommended: the `context` folder only in C2, which is what the moment of use covers, plus the four fenced lines of a change when a flag shows it. Skills come with C3, and the other folders hold records, not documents to work from. Runner-up: also `standards`.

## What the connector offers after C2

| Tool | What it does |
|---|---|
| List my bases | Unchanged from C1. |
| **List documents** (new) | The base's context documents: path, title, owner, and a plain "behind a recorded change" marker on any document the moment of use would flag. Binds the conversation like any other base call. |
| **Read a document** | Not flagged: the document, fenced as data, with its owner and last confirmation. Flagged, with no choice given: the plugin's own sentences, the change's four fenced lines and the choices, and no document. Flagged, with `choice: "use_as_is"`: the document, with one line saying it stays flagged. `"already_reflects"`: for an owner, the link to the web app page (decision 3); for anyone else, the plugin's "not recorded as yours" sentence. `"fix_first"`: as decided in decision 4. A path that does not exist answers with the list of documents that do. |

The skill index stays C3's. The tool descriptions name `list_documents` as the first call in a conversation, which is recommendation 4 from the spike (in one Claude run the model guessed three missing paths before anything else).

## How it is built

1. **The rules, as a pure function** (`web/src/lib/stale/`): the moment-of-use subset of `stale.compute`, taking values only, with the same reason codes. It covers usable changes (with the plugin's validation), changes written down twice (which are said out loud and never hidden), owner lines, accepted records with their three tests, owner acceptances, the same-day exemption, and the `drafted` run exemption. Seat-only state (the plugin's "stay quiet") does not exist in chat and is not ported.
2. **The reader** (`web/src/lib/stale/github.ts`): from one bound base, the context files' front matter, the changes, the confirmations files with one GraphQL blame query for all of them, the corrections records, and for each record the commit that brought it onto main (walking first parents) with that commit's author, date, changed files, and the listed context files as that commit left them for the hash. If any of it cannot be read, the answer is the plugin's "GTM Base could not read what this base has recorded ... It is not saying the document is fine", never a clean document.
3. **The words.** The sentences, the four labeled lines, the 200-character limit, the marker-breaking and the fence note are taken from `moment.py` verbatim, so chat and Claude Code read the same. A test compares them to the plugin's template, as the plugin's own suite does.
4. **The tools** in `web/src/lib/connector/tools.ts`, as in the table.
5. **The owner's confirm button** on the web app's document page (decision 3), owner-only, checked against the map's owner list with the person's verified emails, as W4 does.
6. **The parity check.** A Python script under `tests/` runs `stale.compute` on JSON input fixtures and writes the expected flags; a script in `web/scripts/` runs the TypeScript on the same fixtures and fails on any difference. The fixtures cover each rule in `rules.md` (late write-down, same-day line, naming line, drafted run, non-owner line, accepted record passing and failing each test, owner and non-owner acceptance, written twice, two open changes on one document).

## Security points

- Everything shown from a base is data. The four lines go through the same cleaning as the plugin's (one line each, at most 200 characters, comment markers taken apart), and the document is fenced with the plugin's note that it is data, not instructions. A crafted change or document can still say things to the model; the fence, the one-base binding and the absence of any write tool in C2 limit what it can make a conversation do.
- A flag can never be cleared by text in the base: every settlement rests on GitHub's record of who committed what. A teammate with push access cannot confirm a document they do not own, because blame names them.
- When the records cannot be read in full, the connector says it cannot vouch for the document, never that it is fine.
- The confirm button writes as the owner only after checking the person's verified email against the map's owner list on the default branch, and it names exactly the change the person was shown.

## How it is tested

1. The parity check, all fixtures, with no difference between the plugin and the port.
2. The connector check script gains: the list of documents, a flagged document with no choice (flag only, no document), with `use_as_is` (document, still flagged), a non-owner asking for `already_reflects`, a missing path answered with the list, and a base whose records cannot be read.
3. End to end in ChatGPT on the test site, on `gtm-base-test`: record a context change that names `context/positioning.md` (with the plugin in Claude Code, so the base holds a real record); ask in chat for copy that needs positioning; see the flag and the change before any copy; choose "use it as it stands" and get the document; open the link and confirm as the owner in the web app; ask again and get the document with no flag. Then the same in Claude when its half runs.
4. One security pass on the new reader, the confirm button and the words before it reaches anyone but Brandon.

## What Brandon must do

1. ~~Answer the five decisions above.~~ Done 2026-11-26.
2. In Claude Code, record one context change in `gtm-base-test` that names its positioning document, for the end-to-end run (or let the agent write it there with the plugin).
3. Click through the ChatGPT run, and confirm as the owner in the web app.

## Where the build stands (2026-11-26)

Built on the branch `claude/connector-c2-plan`, together with C4's two proposal tools (decision 4), and deployed to the test site.

- **The rules and their proof.** `web/src/lib/stale/` holds the port (`formats.ts`, `rules.ts`, `words.ts`). `tests/stale_parity.py` builds 22 real git repositories, runs the plugin's own reader and rules on each, and writes the snapshots, the plugin's verdicts and its exact words to `web/scripts/fixtures/stale-parity.json`; `npx tsx scripts/stale-parity.mjs` holds the port to them: 46 of 46 (every verdict, and the flag's words for an owner and for anyone else). Covered: no confirmation, an owner's and a teammate's line, the same-day rule, a line before the change was written down, a line naming the change, setup's drafted line, a done change, two open changes, an open question, a skipped document, the map, an owner's and a teammate's acceptance, a bad hash, a record that did not change the document, a second owner, a change dated in the future, one change naming several documents, a malformed identifier (both refuse), and the older layout (refused by design).
- **Scope taken.** Only the current layout is read. A base that still holds `work/changes`, `work/decisions`, `corrections/` or the older `context/strategy` paths answers that GTM Base cannot vouch for the document; the person may still use it as it stands. The seat-only "stay quiet" setting does not exist in chat.
- **The GitHub reader** (`web/src/lib/stale/github.ts`) answers the plugin's git questions over GitHub's API: GraphQL blame for confirmation lines (verified live), and GraphQL commit history with each record's file at each commit for the commit that added it and the first-parent acceptance. Known difference: GitHub gives commit dates in UTC, the plugin the author's local date, so an acceptance made near midnight can land a day apart; the web app's own commits are UTC on both sides.
- **The tools.** `list_documents`; `read_document` in two steps (decision 2); `propose_change`, which records a context change as a proposal; and `propose_fix`, which keeps the document's settings block, replaces its body, and adds the corrections record that settles the change when the owner accepts. A fix is "already prepared" when an open proposal names that change and touches that document.
- **The web app.** The document page offers the owner "It already reflects this change" from the connector's link (decision 3), worked out again from GitHub when shown and when clicked, and written as one confirmation line naming the change, committed with the owner's address as the map spells it. A proposal that only records something (such as a change proposed from chat) is now accepted by the base's owner, the map's owner, since it touches no owned document.
- **Checked.** `tsc`, `eslint`, `next build`; the connector check, 45 of 45 locally and on the test site; parity, 46 of 46.
- **End to end in ChatGPT so far.** After "Refresh tools" in ChatGPT's plugin settings (ChatGPT keeps a connector's tool list until refreshed), `list_documents` listed `gtm-base-test`'s two documents and `propose_change` opened proposal #7 for a change naming `context/icps.md`; it showed in the test site's web app with the plugin's proposal text. The test site's web app sign-in needed its own callback address on GTM BaseLive (`/api/auth/callback`), which was added. Accepting #7 is the owner's click: Claude Code refused to press Accept on Brandon's behalf, which is the governance working as designed.
- **Brought in line with Plan 1 (PR #22, merged into this branch on 2026-11-26).** Plan 1's catch-up changed the rules this port follows, so the port and the parity check changed with them. A standard (`standards/<job>.md`) and the source map (`access/stack.md`) are documents now: checked, listed, readable and nameable in a change. A confirmation line or an accepted record counts when its author was in the document's authority set (its owners, the map's one `owner:`, and the map's `administrators:`) at the revision that added it, read from that revision's saved document and map, and the check fails closed when that history cannot be read. Anyone in the authority set today is offered "it already reflects this change", in chat and on the web app. Confirmation lines may carry a `role`, and records `approved_roles` and `approved_hashes`. The parity check grew to 35 scenarios (13 new: the base owner, an administrator, a teammate, a map naming two owners, an owner then but not now, an owner now but not then, a role on a line, the base owner accepting, approved roles on a record, a standard, a confirmed standard, the source map, and a file in `standards/` that is not a job): 69 of 69. The GitHub reader now carries each line's revision, each acceptance's commit, and the map and documents as those revisions saved them; on `gtm-base-test` it returned a full verdict and listed the source map. Connector checks 45 of 45 on this computer and on the test site.
- **The flagged read, end to end in ChatGPT (2026-11-26 evening, Pacific).** Brandon accepted #7 in the web app. In a new ChatGPT conversation, asking to read `context/icps.md` before writing cold email copy returned the flag with the change's four lines and no document, and ChatGPT offered the three choices. "Use it as it stands" returned the document, still marked as behind. "It already reflects this change" returned the web app link (ChatGPT adds `utm_source`, which the page ignores), and the page showed the confirm box with the change's words and the address the confirmation would be written as. That box was not clicked, so the fix path could be run on the same change. "Fix it first" had ChatGPT draft a new body and show it before sending; `propose_fix` then opened proposal #8, which changes `context/icps.md` and adds a corrections record naming the change, with its content hash and the plugin's marker line.
- **Seen on the way: Accept gives no sign it is working.** Accepting takes several seconds, and the button shows nothing while it runs, so Brandon clicked it more than once. The first click merged #7, and each later click found it closed and landed on a 404, because the proposal page refuses a closed proposal before it can show "This proposal is no longer open". This is the web app's accept page (W4), not C2.

## What stays the same

C1's sign-in, tokens, one base per conversation and refusals are unchanged. The plugin is unchanged; it stays the reference, and the parity check keeps the port honest whenever its rules change.
