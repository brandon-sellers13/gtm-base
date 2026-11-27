---
title: "feat: The GTM Base connector for Claude chat, Cowork and ChatGPT"
date: 2026-11-26
status: draft, waiting for Brandon's check-in before any code; the spike runs first
origin: Brandon's decisions of 2026-11-25 and 2026-11-26 in the web app session (context and skills through one connector, skills fetched live, noticing changes is not a product feature, one Project per client)
---

# The GTM Base connector for Claude chat, Cowork and ChatGPT

## What this builds

A connector that gives anyone working in Claude chat, Cowork or ChatGPT the company's base inside their own conversations: the approved documents, the company's approved skills, and a way to propose a change. Today GTM Base reaches only people in Claude Code (the plugin) and people in the web app (who read and approve). The marketers who never open Claude Code, which is most of the buyers, get nothing in their conversations. This connector is how GTM Base reaches them.

The connector is a remote MCP server served by the GTM Base web app (https://gtm-base-app.netlify.app). Both Claude and ChatGPT add custom connectors over MCP, so one server serves both. Like the rest of the app, it is a view onto each base's GitHub repository and never a second copy: every read comes from the repository at the moment it is asked, with the person's own GitHub access.

## Decisions already made

1. **Context and skills come through the same connector.** The company's skills are not installed anywhere. Claude or ChatGPT fetches a skill from the connector each time it is used, so every conversation uses the current approved version, and nobody reinstalls or republishes anything. Claude Code is unchanged: there the base is a local copy kept in sync by git, so skills are ordinary files.
2. **Noticing that the business changed is not a product feature.** Reading calls, deals and competitors is something the person's own AI already does through its own connectors, on request or on a schedule; at most a skill helps. GTM Base owns what happens after: recording the change with its evidence, following it through to every document it overtakes, the owner's approval, the flag at the moment of use, and the history. So the connector needs a way to propose a change, which is how any AI's noticing lands in the governed record.
3. **One Claude or ChatGPT Project per client.** Chat has no folders, so a Project plays the part a folder plays in Claude Code. A person working for several companies adds one GTM Base connector to their account and gives each client's Project a one-line instruction naming its base.
4. **The connector keeps clients walled off on its own.** It never guesses a base: a call that names no base is refused. Once a conversation has used one base, it refuses to read another in that conversation. It sees only bases the person's own GitHub account can reach.
5. **Approvals stay where a person approves them.** Chat and ChatGPT cannot force a person-only question the way Claude Code's permission prompt can, so the connector may read and propose, never approve. The owner accepts proposals in the web app (W4) or in Claude Code.

## Why this is defensible

Reading company context over MCP is now table stakes: Notion Skills serves pages and skills to Claude and ChatGPT, and Calven serves an approved "Universe" of positioning and messaging over a read-only MCP server (both in the competitor table in `docs/ideation/2026-11-24-messaging-reframe.md`). A connector that only reads would put GTM Base level with them at best. What they do not claim, and this connector carries into chat:

- **The flag at the moment of use.** When a conversation asks for a document that a recorded change has overtaken, the connector returns the document with the flag and the three choices (use it as it is, fix it first, it already says this), so the AI stops and asks instead of working from an outdated document.
- **Skills governed like documents.** A company playbook changes only through an owner's approval, and every conversation gets the approved version.
- **Proposals with evidence.** A change suggested in chat arrives as a proposal with what changed, why and the evidence, for the owner to accept.

## What the connector offers

| Action | What it does | Writes? |
|---|---|---|
| List my bases | The names of the bases this GitHub account can reach, so a person can name one in a Project's instructions | No |
| Read a document | One approved document from the named base, with its owner, last confirmation, and the flag and three choices when a recorded change has overtaken it | No |
| Use a skill | One approved skill from the named base, together with the base documents it needs, in one answer | No |
| Propose a context change | A change with what changed, why and the evidence, recorded as a proposal for the owner to accept | Opens a proposal; never approves |

The skill index (each skill's name and one line on when to use it) goes in the connector's own instructions, so the AI knows what exists without asking first. Together with skills arriving with their documents, a skill should cost about one step, the same as a native skill. The spike measures this.

## Open questions the spike answers

1. **Does a skill served by a connector get used reliably?** Run the same three tasks in Claude chat, Cowork and ChatGPT with a skill served by the connector and with the same skill installed natively; record whether it was used and the time to the first answer.
2. **Can ChatGPT Business propose a change?** OpenAI's help center says Business and Enterprise get full MCP, but a forum thread reports write actions blocked on a Business workspace. Test the write on a real workspace.
3. **Can a connector on Netlify do the sign-in both products need?** Both connect with OAuth from their own cloud. The web app would sign the person in with GitHub and hand the product a token for this server. Build the smallest version and connect it to Claude and ChatGPT.
4. **Cowork:** whether it can use the base the folder way, as Claude Code does, and whether a private Cowork plugin marketplace can point straight at a company's GitHub repository.
5. **Where "one base per conversation" is remembered.** Products send a session identifier with each call; holding which base it used needs a small store (Netlify Blobs or similar). That is the app's first stored state; confirm it is acceptable or find a stateless way.

## Spike results (S0), as of 2026-11-26

**Where it stands.** The test connector is built and deployed, and both halves have been run on 2026-11-26: ChatGPT on Brandon's personal ChatGPT Pro account and Claude on his personal Claude Pro account (`docs/plans/spike/CLAUDE-HALF-LOG.md`). Question 4 is answered from the official docs and from what Claude reported about itself during the runs. Each answer says what is verified, what is inferred, and what is still open. Docs were read on 2026-11-26.

**The test connector.** A throwaway MCP server inside the web app (`web/src/app/spike/` and `web/src/lib/spike/`, kept only on the branch `claude/connector-spike-d1143a` and never merged to main), deployed to its own Netlify site, https://gtm-base-connector-spike.netlify.app, so the live app is untouched. It signs people in through the existing "GTM BaseLive" GitHub App and offers four tools: list my bases, use a skill (an invented Fernhill Coffee skill returned with its positioning document), read a document (real files from `gtm-base-test`, read with the person's own GitHub token), and propose a change (a write call that records nothing). It stores nothing: every client id, code and token it hands out is an encrypted value only it can open. It logs what each product sends with each call, never tokens. The native copy of the same skill is `docs/plans/spike/fernhill-copy.zip`.

### 1. Is a connector skill used as reliably and as quickly as a native one?

Answered for ChatGPT and Claude chat; the Cowork tab in the desktop app was not run. Known before the runs:

- Verified: native skills exist on all three surfaces. Claude chat and Cowork load skills from the person's account, and ChatGPT Business has its own Skills (Plugins, then Skills, then Upload), so the comparison can run everywhere ([Claude plugin support](https://claude.com/docs/plugins/platform-support), [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt)).
- Built into the test: the skill index sits in two places, the server's instructions and the description of the "use a skill" tool. A product may not show a server's instructions to the model, and the tool description is always shown. Inferred: ChatGPT is the likelier one to skip the instructions, since OpenAI's docs do not describe using them.

**ChatGPT, run 2026-11-26** (Brandon's personal ChatGPT Pro account, default model at "Medium" thinking). Each run was a new conversation. "Seconds" is from pressing send to a finished answer, timed in the page. The connector runs had the native skill uninstalled; the native runs had the connector uninstalled. In place of a Project, each prompt began with the Project's one-line instruction ("This is for Fernhill Coffee.", plus "Its GTM Base is brandon-sellers13/gtm-base-test." for the connector).

| Task | Native: used? | Native: seconds | Connector: used? | Connector: seconds |
|---|---|---|---|---|
| 1. Decaf email | No | 34.1 | Yes | about 6 (ChatGPT's own figure) |
| 2. Win-back subject lines | No | 6.0 | Yes | 6.3 |
| 3. LinkedIn post | No | 6.4 | Yes | 8.0 |

- **The connector skill was used every time, in about the same time as an answer without it.** The store shows exactly one "use a skill" call per run, and each answer followed the skill: freshness first, the tagline, the sign-off, subject lines under 45 characters, and proof points from the positioning document.
- **The native skill was never used unprompted.** None of the three answers followed it (no tagline, no 72-hour claim, a different sign-off). When a fourth prompt named the skill ("Use the fernhill copy skill"), the answer did follow the rules, but ChatGPT said it had used "previously retrieved Fernhill copy rules" and could not reach the positioning document. That points to ChatGPT's memory of the earlier connector conversations rather than the native skill. So in this test ChatGPT's native skill did not work as an automatic trigger, and whether it loads at all when named is unconfirmed. A forum thread reports the same symptom on Business workspaces ([skills not available at runtime](https://community.openai.com/t/chatgpt-business-skills-appear-installed-enabled-in-ui-but-are-not-available-at-runtime/1380754)).
- **With both installed, ChatGPT chose the connector.** In a first run with both present, ChatGPT called the connector's "use a skill" rather than the native skill, and filled in the base itself (see question 5).
- **Caveat on the first run:** ChatGPT's memory carried facts between these conversations (the base's name, the skill's rules), and the two conditions used different prompts. So the runs were repeated fairly, below.

**ChatGPT, fair rerun 2026-11-26** (same account, at Brandon's request). ChatGPT memory was turned off for the rerun and back on afterwards; every setting was checked against its starting state. Both conditions ran in one ChatGPT Project ("Fernhill spike test") with one shared instruction, "This Project is for Fernhill Coffee. Its GTM Base is brandon-sellers13/gtm-base-test.", the same "Medium" model setting, and the bare task as the prompt. Native runs had the connector uninstalled; connector runs had the native skill uninstalled.

| Task | Native: used? | Native: seconds | Connector: used? | Connector: seconds |
|---|---|---|---|---|
| 1. Decaf email | No | 4.9 | Yes | 7.1 |
| 2. Win-back subject lines | No | 4.5 | Yes | 13.5 |
| 3. LinkedIn post | No | 6.4 | Yes | 7.8 |

- The result held. The connector skill was used 3 of 3 times (one "use a skill" call per conversation in the store, each with its own conversation id), and the native skill 0 of 3. The native answers were faster only because they skipped the skill: generic copy, no tagline, a wrong sign-off, and a subject line over 45 characters.
- Cost of the connector: about 2 to 9 seconds more per answer, which is the tool call plus reading the skill.
- Why, as far as can be told: the connector's tool is listed to the model on every turn with a description that names the skill and says to fetch it first (verified, it is our text). How ChatGPT decides to load an uploaded native skill is not documented (not known), and here it never did, even with the company named in the Project instruction.

**Claude chat, run 2026-11-26** (Brandon's personal Claude Pro account at claude.ai, driven in his browser; Opus 5.5 at "Medium" for every run; full log in `docs/plans/spike/CLAUDE-HALF-LOG.md`). Claude memory ("Search and reference chats" and "Generate memory from chats") was turned off for the runs and back on afterwards. On this account "New project" now makes only a Claude Code style project (see below), so the Project's one-line instruction, "This Project is for Fernhill Coffee. Its GTM Base is brandon-sellers13/gtm-base-test.", was put in the account's "Instructions for Claude" for the runs and removed afterwards. Each run was a new conversation with the bare task as the prompt. Native runs had the native skill on and the connector turned off in the message box's tools menu; connector runs had the native skill turned off under Plugins and the connector on. "Seconds" is from pressing send to a finished answer, timed in the page.

| Task | Native: used? | Native: seconds | Connector: used? | Connector: seconds |
|---|---|---|---|---|
| 1. Decaf email | Yes | 18.3 | Yes | 16.5 (see the permission note) |
| 2. Win-back subject lines | Yes | 13.4 | Yes | 23.0 |
| 3. LinkedIn post | Yes | 15.4 | Yes | 16.8 |

- **In Claude both ways worked every time, at about the same speed.** The native skill was used 3 of 3 times (Claude showed "Read positioning.md" before each answer) and the connector skill 3 of 3 (Claude showed "Used GTM Base test: Use a company skill"). Every answer led with the 72-hour roast, kept subject lines and headlines under 45 characters, and ended emails and posts with "Roasted in Oakland, delivered within 72 hours." The averages were 15.7 seconds native and 18.8 seconds through the connector.
- **The slow connector run guessed at documents first.** In task 2 Claude called "read a document" three times for paths that do not exist in the base (`context/brand-voice.md`, `context/icps.md`, `context/positioning.md`, each a 404 from GitHub) before calling "use a skill". The other two connector runs went straight to "use a skill".
- **The first connector call needed a click.** Custom connector tools start at "Needs approval" in Claude. The first call stopped at "Claude wants to use Use a company skill from GTM Base test" (Decline, Always allow, Allow once). Brandon chose "Always allow". The 16.5 seconds for task 1 is model time only (6.6 seconds before the prompt plus 9.9 after it); the wait for the click is left out. The native skill never asked. At the same moment the message box's permission mode changed from Manual to Auto. Both were set back afterwards.
- **Not equal between the conditions:** the instruction sat in the account's Instructions rather than a Project; the connector-off and skill-off switches are account-wide in Claude, so the two conditions ran one after the other rather than interleaved; Gmail, Google Calendar, Google Drive and Claude in Chrome stayed on in both.

**Cowork.** On this account the claude.ai "Claude" mode carries the internal value "cowork" in the page, and every tool call from these chat runs reached the server marked `x-anthropic-client: Cowork`, with client name `claude-code` ("Anthropic's agentic coding tool"). So the chat runs above ran on the Cowork harness (verified from the server log). The Cowork tab in the desktop app was not run, because the desktop app is signed in to Brandon's work account (not run; inferred to behave the same, since it reports the same client).

**Claude's new Projects, two runs.** A Project made from "New project" opens at `claude.ai/code/project/...` as a Claude Code project: one ongoing coordinator chat, Threads, "Project instructions" described as a CLAUDE.md, and an auto-memory file every thread reads. With the instruction in its Project instructions, a connector-condition run of task 1 and a native-condition run of task 2 both went into the same coordinator chat, and **neither used the skill** (no 72-hour lead, a 51-character subject line). The project's message box offers no connectors, and no call reached the server. The native skill was listed in its slash commands but not used from a bare prompt. These two runs are weak evidence (one shared chat, auto memory on), but they say a GTM Base connector does not reach Claude's new Projects today.

| Product | Task | Native: used? | Native: seconds | Connector: used? | Connector: seconds |
|---|---|---|---|---|---|
| Claude chat (Cowork harness) | 1, 2, 3 | 3 of 3 | 18.3, 13.4, 15.4 | 3 of 3 | 16.5, 23.0, 16.8 |
| Cowork tab in the desktop app | 1, 2, 3 | not run | | not run | |
| Claude Code project (new Projects) | 1 or 2 | 0 of 1 | 19.1 | 0 of 1 (connector not offered) | 24.4 |

### 2. Can ChatGPT Business call a write tool?

Partly answered; the real test is the "propose a change" call in the runbook.

- Verified (OpenAI help, [developer mode and MCP](https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-connectors)): full MCP with write actions is in beta for Business, Enterprise and Edu. On Business only admins use developer mode, and ChatGPT may ask the person to confirm a write. A newer version of the page says custom MCP servers are now added from Plugins without turning on developer mode.
- Reported, not confirmed: a Business owner found the workspace developer mode toggle marked "Enterprise" and write tools blocked ([forum thread](https://community.openai.com/t/write-actions-blocked-on-custom-mcp-server-business-plan-workspace-developer-mode-unavailable-at-workspace-level/1384381)).
- The test tool is marked as a write that changes nothing destructive, which is the mildest kind ChatGPT knows.
- **Verified on ChatGPT Pro (personal) on 2026-11-26: write calls work.** Asked to propose the oat milk change, ChatGPT called "propose a change" with what changed, why and the evidence filled in, and showed the proposal as pending the owner's approval. It did not ask for confirmation first, which matches the plugin's default permission ("Allow low-risk tools") and the tool being marked non-destructive. Still open: whether a Business workspace blocks the same call. That needs a Business workspace to test in.
- **Verified in Claude (personal Pro) on 2026-11-26: write calls work.** Asked to propose the oat milk change, Claude called "Propose a context change" with the base, what changed, why and the evidence, and told the person the change waits for the owner. Claude lists `propose_change` under "Write/delete tools" (the three others under "Read-only tools"), and all four start at "Needs approval". This call ran without a prompt because the permission mode had switched to Auto by then; in Manual mode it would have asked first.

### 3. Can a connector in the web app on Netlify do the sign-in both products need?

Yes. The round trip is verified with both ChatGPT and Claude.

- Verified (docs): Claude needs a 401 that points to the server's discovery document, discovery metadata, dynamic client registration or a client metadata document, S256 PKCE, form-encoded token requests, answers within 10 seconds, and the return address `https://claude.ai/api/mcp/auth_callback` ([Claude connector authentication](https://claude.com/docs/connectors/building/authentication)). ChatGPT needs the same, sends a `resource` value with each request, and uses its stable return address only when the server names itself (`iss`) in every sign-in response ([OpenAI authentication](https://developers.openai.com/plugins/build/auth)). The test server does all of this.
- Verified on the deployed site: the discovery documents, registration (and refusal of a return address that is not Claude's or ChatGPT's), the 401 with its pointer, and the hand-off to GitHub. Verified on a local run: the code exchange with PKCE (a wrong verifier is refused), refresh, refusal of a call that names no base, the skill fetch and the write call.
- **ChatGPT, verified end to end on 2026-11-26** (Brandon's personal ChatGPT Pro account). Added from Plugins, then Add, then "Add custom MCP server", with no developer mode and visible only to its creator. ChatGPT read the discovery documents, chose dynamic registration (it noted that the server offers no client metadata document), registered with its stable return address `https://chatgpt.com/connector_platform_oauth_redirect` (the `iss` value worked), sent the `resource` value, and exchanged the code with PKCE. GitHub's token came back with an eight-hour life and a refresh token. In a conversation ChatGPT then called "list my bases" (an empty answer, correctly: the GTM BaseLive app is installed on no account yet) and "use a skill", and repeated the Fernhill skill's rules back exactly.
- **ChatGPT speaks a newer MCP first.** Its first call was `server/discover` under protocol version 2026-07-28. When the spike answered "method not found", it fell back to `initialize` under 2025-11-25. C1 should use a current MCP library rather than the spike's hand-written handler.
- **Claude, verified end to end on 2026-11-26** (Brandon's personal Claude Pro account). Added from Plugins, then Add, then "Add custom connector", with the name and address only. Claude checked the server and chose "Sign in now" and "Register automatically" (dynamic registration) on its own, both marked "Detected". It registered as "Claude" with the return address `https://claude.ai/api/mcp/auth_callback`, sent S256 PKCE, scope "base" and the `resource` value, and exchanged the code; the whole sign-in took under three seconds and ended with "Connected to GTM Base test." GitHub showed no approval screen, because Brandon had already authorized GTM BaseLive, so there was no approval click. Like ChatGPT, Claude sent `server/discover` under 2026-07-28 first and fell back to `initialize` under 2025-11-25. A personal Pro account let one person add it alone, next to another custom connector already there.
- **On a Team or Enterprise plan it is different.** On Brandon's Claude Team organization a custom connector can be added only by an Owner, for everyone in the organization. That is a finding for C5: in such a company, adding GTM Base to Claude is an Owner's step for the whole organization, not something one marketer does alone.
- What it costs: no new service and no store. The GitHub App gains one callback address. GitHub's sign-in tokens last eight hours and come with refresh tokens, which the connector passes through when the product refreshes.
- Left for C1 and its security review: a consent page that shows which product is asking, single use of sign-in codes, revoking old refresh tokens, and whether the GitHub token should travel inside the access token (encrypted, as now) or stay on the server, which would need a store.

### 4. Cowork

Answered from the docs.

- **The folder way works for reading, not for proposing.** Cowork works on folders on the person's computer, runs commands in a virtual machine, and loads a plugin's skills and hooks ([platform support](https://claude.com/docs/plugins/platform-support)). But inside a Cowork task github.com is download-only: clone, fetch and pull work, and `git push` is blocked unless the organization allows all domains ([Cowork network access](https://claude.com/docs/cowork/guide/network-access)). GTM Base pushes when it sends a proposal and when it backs up (`compose_proposal.py`, `backup.py`), so both fail in Cowork under the default setting. Not run: whether the plugin's Python scripts and hooks run cleanly in the Cowork machine. Consequence: for Cowork the connector is the better path, because its writes go through the web app, which can reach GitHub.
- **A private Cowork plugin marketplace can point straight at a private GitHub repository.** An Owner of a Team or Enterprise organization syncs a private or internal repository as the organization's marketplace (Organization settings, then Plugins and skills, then Sync from GitHub), through the Claude GitHub App, with automatic sync on every push to the default branch. Members need no access to the repository. Plugins in it must sit inside that repository or in another repository with the same owner, and none may have a top-level `bin/` folder ([organization sync](https://claude.com/docs/plugins/org-sync)). A person can also add one for themselves (Customize, then Plugins, then Add marketplace) by connecting GitHub ([Cowork plugins](https://claude.com/docs/cowork/guide/plugins)).
- **Seen in the Claude runs on 2026-11-26:** on Brandon's personal account, claude.ai chat runs on the Cowork harness. Its tool calls reached the connector marked `x-anthropic-client: Cowork` with client name `claude-code`, and the account's connectors and uploaded skills both worked there (question 1). So for a person on such an account, the connector already reaches Cowork through claude.ai.
- What this means for GTM Base: a base repository could double as the company's skill marketplace in Claude, updated on every approved merge. It would carry skills only (no documents, no flag at the moment of use), needs a `marketplace.json` in the base, and has no ChatGPT equivalent. It is an optional Claude-only extra for C3, not a replacement for the connector.

### 5. Where is "one base per conversation" remembered?

Answered for both products.

- Verified (OpenAI [Apps SDK reference](https://developers.openai.com/apps-sdk/reference)): ChatGPT sends an anonymized conversation id (`openai/session`) with every tool call, along with an anonymized user id and organization id.
- **Verified in ChatGPT on 2026-11-26.** Every tool call carried `openai/session`, both in the call's `_meta` and as an `x-openai-session` header. Two calls in one conversation carried the same value; a call in a new conversation carried a different one. ChatGPT sent no MCP session id with its tool calls and did not reconnect between them. So in ChatGPT, "one base per conversation" can be enforced with a small store keyed by that value. The store itself also works: the spike writes each call's metadata to Netlify Blobs on the test site (`netlify blobs:list spike-log`), with no setup beyond one package.
- **The model fills in the base itself.** Twice in ChatGPT, a request that named no base ("Read the ideal customer profile from my GTM Base", and a Fernhill task with no base in it) produced a call naming `brandon-sellers13/gtm-base-test`, taken from ChatGPT's memory of earlier conversations. So "refuse a call that names no base" never fires: the server cannot tell a base the person chose from one the model recalled. Walling clients off therefore cannot rest on the base parameter alone. It needs the conversation-keyed store (bind the first base, refuse any other) and, for the first call, something the server can check, such as a base the person confirmed in the web app for that conversation or Project.
- **Verified in Claude on 2026-11-26: Claude sends a conversation id too.** Every tool call carried `com.anthropic/session` in the call's `_meta`, a value of the form `v1.` followed by 32 hex characters (not as a header). In the one conversation that made four calls, all four carried the same value; the four connector conversations carried four different values. Claude also opened a new MCP connection (`initialize`) for each conversation and sent back the session id the spike handed out on every call in it, so a per-connection id lines up with a conversation as well, but only if the server hands one out. Each call also carried a per-call `claudecode/toolUseId`. Not checked: whether Anthropic documents `com.anthropic/session` or promises it stays stable, so treat it as observed behavior.
- The choices: (a) a store keyed by conversation id, the only way to enforce "refuse a second base", and only where a conversation id arrives; (b) every call names its base and the server refuses calls without one (built in the test), which walls clients off by instruction rather than by enforcement; (c) one connector address per base, which needs no store but undoes decision 3 (one connector per account), and Claude turns connectors on per conversation rather than per Project.

### Recommendation on C1 to C5 (both halves run)

The units stand, with these changes:

1. **C1, walling clients off:** the ChatGPT runs showed the model filling in a base from memory, so "refuse a call with no base" is not enough on its own. Keep it, and add a small store (Netlify Blobs works on this site) keyed by the conversation id each product sends: `openai/session` from ChatGPT and `com.anthropic/session` from Claude. The first base a conversation uses is bound to it, and any other base is refused. That makes the store the app's first stored state, which is Brandon's decision 2 under "For Brandon". Since Claude's id is observed rather than documented, C1 should also fall back to the MCP session id it hands out, which Claude keeps for one conversation.
2. **C1, protocol:** build on a current MCP library, since both ChatGPT and Claude ask for MCP 2026-07-28 first.
3. **C3, skills: confirmed.** Serving skills through the connector was used 6 of 6 times in ChatGPT, where the native skill was used 0 of 6, and 3 of 3 in Claude, where the native skill was also used 3 of 3 at about the same speed. One connector therefore covers both products, and Claude gives up nothing by using it. The fallback to the marketplace sync is not needed; keep it as a later, Claude-only extra. Put the skill index in the tool description as well as the server's instructions.
4. **C2, documents:** in one Claude run the model guessed three document paths that do not exist before fetching the skill. "Read a document" should name the documents that exist (in its description or in a 404 answer that lists them), so a guess costs one call at most.
5. **C4 and C5:** proposing works from ChatGPT (on Pro) and from Claude (on Pro). The guide for Cowork users should send them to the connector for proposing, since pushing from Cowork is blocked by default. In a company on Claude Team or Enterprise, adding the connector is an Owner's step for the whole organization, and C5's guide should say so. C5's guide should also say that Claude asks before each tool's first use in Manual mode, and suggest "Always allow" for the read tools while leaving "Propose a context change" on "Needs approval".
6. **C5, where the instruction goes in Claude:** on accounts that have Claude's new Projects, "New project" makes a Claude Code project that offers no connectors, and the connector did not reach it. The copyable instruction worked in the account's Instructions and should work in a classic Project. C5 should say where to put it, and step 2 of "How we know it is done" should name a classic Project or the account's Instructions until Claude's new Projects can use connectors.

## Units

- [x] **S0. The spike** (the five questions above). Done when each has an answer written into this plan, with the measurements. Built and deployed 2026-11-26. ChatGPT half and Claude half both run the same day. Two small gaps remain, both written into the answers: whether a ChatGPT Business workspace blocks the write call, and the Cowork tab in the desktop app, which was not run because the desktop app is on Brandon's work account. **Teardown not done:** Brandon chose on 2026-11-26 to keep the spike up for now, so the test Netlify site, the extra GitHub App redirect address, and the test connector and skill in Claude and ChatGPT are all still live (listed in `docs/plans/spike/CLAUDE-HALF-LOG.md`, under "Teardown").
- [ ] **C1. The connector itself:** the MCP endpoint in the web app, built on a current MCP library; sign-in through GitHub; the refusal of any call without a named base; and the one-base-per-conversation rule, enforced with the small store Brandon approved on 2026-11-26 (Netlify Blobs, keyed by `openai/session` from ChatGPT and `com.anthropic/session` from Claude, falling back to the MCP session id the connector hands out). The store binds a conversation to the first base it uses and refuses any other. Technical plan: `docs/plans/2026-11-26-002-feat-connector-c1-plan.md` (written and approved 2026-11-26, with the recommended answer to all four decisions).
- [ ] **C2. Reading documents,** with the moment-of-use flag and the three choices in the answer. Technical plan: `docs/plans/2026-11-26-004-feat-connector-c2-plan.md` (written and approved 2026-11-26, with the recommended answer to all five decisions).
- [x] **C3. Skills:** the index at the end of "List documents", and a skill served with the documents it needs. Depends on where approved skills live in a base: the plan for company skills (Plan 1, Unit 4.2b, `skills/`) settles the folder and the trust rules; the connector serves only skills approved on the main branch, as instructions, never code. Built on 2026-11-27 (branch `claude/connector-c3`, see "C3 as built" below); its security review and the end-to-end runs are still open.
- [ ] **C4. Proposing a context change** from chat, as a proposal the owner accepts in the web app or in Claude Code. Brandon decided on 2026-11-26 to ship it in the same release as C2, so "fix it first" works in chat from the start (decision 4 of the C2 plan).
- [x] **C5. Setting it up for a client:** a short guide and a copyable Project instruction per base, shown on each base's page in the web app.

## C3 as built (2026-11-27)

**What a person gets.** A new tool, "Use a company skill" (`use_skill`), takes the base and a skill's name and answers with what Claude Code's runner hands back for the same skill on the same day: the runner's sentences, the skill's approved instructions (`SKILL.md`, then its references by name; examples are never handed on), and each document it declares, fenced as data and read from the main line. "List documents" now ends with the base's approved skills, one line each on when to use it, and a skill name it does not hold is refused with that list.

**Which versions are served.** The connector is another computer in the plugin's terms. It keeps no list of trusted versions and cannot ask anybody to accept one, so it serves exactly the version another computer would be offered to accept (`skill_install.approval_of`): the whole skill as it stands on the main line, every file matching one approval record's hashes, brought onto the main line by somebody who held authority over the skill as authority itself had last approved it (see "The C3 security review" below), not replaced by a later approval, and with no change on the main line to the skill's folder since. A link, a hidden file, a file in no shape a skill admits, an unreadable or binary file, or another repository nested in the folder means the skill is not served (the last is stricter than the plugin, never looser). Declarations are checked first, as the runner's step 1 does, so a skill that declares a read the moment of use cannot check is refused even when approved.

**The moment of use.** Every declared document goes through the same check as `read_document` (C2's port of the plugin's rules). When one is behind a recorded change, the first answer is the runner's sentence and the flag for each such document, and nothing else. The person's choice comes back as `use_as_is` (the document paths they chose to use as they stand), and then the skill runs and says each stays flagged; "fix it first" and "it already reflects this change" go through `read_document` with that choice, as in C2.

**What does not run in chat.** The runner's `finish` (the screen for contact details and keys, the figure lint and the engine-block check) has no equivalent in chat: nothing in chat hands the work product back to GTM Base. The skill's own standard still tells the model what to check before it answers. A silenced seat (the runner's step 5) does not exist in chat.

**Where the skill index appears.** Only at the end of `list_documents`, which is tied to one base. The server's instructions and the `use_skill` description carry one general sentence saying how skills are used and that `list_documents` names them, the same for every person and every base. A product may keep one tool listing across conversations, so a list there could put one client's skills in front of another client's conversation (changed by the C3 security review).

**Never a write into `skills/`.** The connector's only write path (`openProposal`) refuses any path in the skills folder, however it is spelled. A skill reaches a base only through the plugin's install and its yeses.

**The seam for a folder declaration.** Track 4 is adding `reads_optional` naming the folder `context/icps/`. Until the runner reads it, a skill that declares a folder is refused as invalid, as the plugin refuses it today (a parity scenario holds this). The connector's reading already takes a folder declaration when the folder is listed in `FOLDER_DECLARATIONS` (`web/src/lib/stale/skills.ts`, empty today): it hands on the `.md` files directly in the folder, in name order, never a file in a folder inside it and never a link, each through the moment-of-use check, and an empty or missing folder is not a gap. Turning it on is adding `context/icps/` to that list once Track 4's runner change is on main, then regenerating the parity fixtures so the plugin's own order is held.

**How it is checked.** `tests/skill_parity.py` builds 17 real git repositories (the base owner, an administrator, a teammate with no role, a teammate who makes themself an administrator in the same change, a file edited or added after the approval, an older version put back after a newer approval, a change approved by the skill's own owner, a skill accepted through a proposal, a bad declaration, a folder declaration, a link, a hidden file, a flagged document, every document present, and one approved skill beside one nobody approved), asks the plugin's own `approval_of` and `runner.start`, and writes `web/scripts/fixtures/skill-parity.json`. `npx tsx scripts/skill-parity.mjs` holds the port to it, including the exact text the runner hands the assistant for every skill that runs, and checks the choice to use a document as it stands, the folder seam and the refusal to write into `skills/`.

## The C3 security review (2026-11-27)

The one-pass review of C3 found four problems, fixed in the plugin and the connector together so the parity check still holds them to each other.

1. **A teammate could make their own skill count as approved (high).** The approver's role was read from whatever sat on the main line just before the approval, so a teammate could name themself the skill's owner, or add themself to the map's administrators, in one change and approve in the next. Roles are now read only from what authority already approved. The map's roles start as the map the base first saved on the main line, when it was set up, and change only with a record of the map approved by the base owner those roles name, whose map bytes match the approval exactly, which is how the plugin's own settings operations change them. The skill's owners are the owner line of the last valid approval of that skill, read from the bytes it approved, so a skill nobody has validly approved has no owner yet. One consequence is deliberate: an administrators line edited by hand, even by the base owner, grants nothing until it goes through the plugin's operation.
2. **A replaced approval came back when the newer record was deleted (medium).** An approval is now refused when any change on the main line after it touched the skill's folder, each change compared with its own first parent, so putting back identical bytes, directly or through a merge, still counts as a change. One consequence: an unapproved edit to a skill that is later reverted leaves it unserved until somebody with authority approves it again.
3. **A hidden file in `context/icps/` was handed on in chat (low).** The connector now skips it, as the runner always did.
4. **A segment's file name went out outside the fence (low).** Both the runner and the connector now hand on only names made of lowercase letters, digits and hyphens ending in `.md`. Such a name can still spell words with hyphens, but it cannot hold a sentence, punctuation or markup.

The connector reads what these rules need from the history walk it already made: the main line and, for the map and each skill's folder, every change along it.

## Review standard

Units get no review of their own; the end-to-end run below is the main check. One security review (one pass) before anyone but Brandon connects: the sign-in, the tokens the products hold, the one-base rules, and what a crafted document or skill could make a conversation do.

## How we know it is done

1. Brandon adds the connector to Claude and to ChatGPT once.
2. In a Claude Project set to one test base, a conversation reads the customer profile, gets the moment-of-use flag on an overtaken document, uses a company skill, and proposes a change.
3. Brandon accepts that proposal in the web app.
4. In a second Project set to another base, the conversation sees only that base, and a request for the first base is refused.
5. The same reading and skill use work in ChatGPT, and proposing works there too or the plan says plainly why it does not.

## For Brandon

1. Pricing and packaging: whether the connector is part of every plan or a paid tier. Calven anchors at $99 a month for one seat and $1,000 a month for unlimited seats.
2. ~~Whether a small store for "one base per conversation" is acceptable.~~ **Decided 2026-11-26: approved.** Brandon approved a small store after the spike. It is the web app's first stored state, and it holds only which base each conversation is bound to, keyed by the product's conversation id. It never holds documents, tokens or the content of conversations.
