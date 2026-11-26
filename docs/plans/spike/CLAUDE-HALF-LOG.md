# Claude half of the S0 spike: run log

This log records what was done on Brandon's personal Claude account on 2026-11-26, in order, so that every setting can be put back. The runs were driven through Brandon's browser with the Claude browser extension.

## Account

The claude.ai tab is signed in to Brandon's personal account, on the Pro plan. It is not his work organization.

## Settings before anything changed (recorded 2026-11-26, before Step 1)

Settings, then Your Claude, then Memory:

- "Search and reference chats" was on.
- "Generate memory from chats" was on.
- "Include sensitive topics in memory" was off.
- "Instructions for Claude" was empty.

Settings, then Capabilities:

- "Artifacts" was on.
- "Charts and diagrams in chat" was on.
- "Create and edit files" was on, so skills can run without turning code execution on.
- "Use the internet while making files" was on.
- "Claude in Chrome" was on.
- "Suggest connectors" was on.
- "Switch models when a message is flagged" was on.

Plugins (the screen the hand-off calls Customize), then Your plugins:

- Needing a new sign-in: Ahrefs, Canva, Notion, Pitch, Profile Base (a custom connector at profilebase.ai), Slack and Webflow.
- Active connectors: GitHub (built-in integration), Gmail, Google Calendar and Google Drive.
- Skills: "Micw" (by you), plus the built-in skills.
- No "GTM Base test" connector and no Fernhill skill were installed.

The home screen also showed an "Auto is now the default" notice with an "I acknowledge" button. It was left alone.

## Steps

### Step 1. Add the connector (done 2026-11-26, about 18:52 UTC)

The hand-off's "Customize, then Connectors" is now Plugins, then Add, then "Add custom connector". The name was "GTM Base test" and the address was `https://gtm-base-connector-spike.netlify.app/spike/mcp`. After the address was entered, Claude checked the server and chose two settings on its own, each marked "Detected": Authentication "Sign in now", and OAuth client "Register automatically" (dynamic client registration). Both were left as detected, and no headers or advanced settings were added. Selecting Add connected it and showed "Connected to GTM Base test."

GitHub never showed an approval screen, so there was no approval click. GitHub approved on its own, most likely because Brandon had already authorized "GTM BaseLive". The server log confirms the whole sign-in in under three seconds:

- `register` at 18:52:26.746, client name "Claude", return address `https://claude.ai/api/mcp/auth_callback`, user agent `python-httpx/0.28.1`.
- `authorize` at 18:52:27.547, with PKCE method S256, scope "base" and the resource set to the connector address.
- `github-callback.ok` at 18:52:28.853, GitHub login `brandon-sellers13`.
- `token` at 18:52:29.290, an authorization-code exchange.
- The first tool traffic at 18:52:29.712: Claude sent `server/discover` under protocol version 2026-07-28 with client name "Anthropic/Toolbox" and user agent "Claude-User", then fell back to `initialize` and `tools/list` under 2025-11-25 and carried the MCP session id the spike handed out (`mcp-session-id`).

Claude also sent two unauthenticated probes before registering (`mcp.401`, then the two discovery documents), once when the address was entered and again when Add was selected.

The Plugins page with the "Profile Base" custom connector already present shows that this personal Pro account allows more than one custom connector.

### Step 2. Upload the native skill (done 2026-11-26, about 19:00 UTC)

Plugins, then Add, then "Upload plugin" took `fernhill-copy.zip` (byte-identical copy, same SHA-1 `dd4a9a2c`). Claude previewed it as "fernhill-copy" and, after Upload, showed "Fernhill copy is added and ready to use." Claude wrapped the bare skill as a plugin named "Fernhill copy" (version v1) with a generated `.claude-plugin/plugin.json`, and kept both `SKILL.md` and `positioning.md` under `skills/fernhill-copy/`. Code execution did not need turning on, because "Create and edit files" was already on.

### Step 3. Memory off (done 2026-11-26)

"Search and reference chats" was turned off. Turning off "Generate memory from chats" opened a dialog asking to "Pause memory" (keep existing memory) or "Reset memory" (delete it permanently). "Pause memory" was chosen. After a reload both showed off, and the "Include sensitive topics in memory" row was hidden while memory was paused (it was off before).

### Step 4. The test Project (paused 2026-11-26, waiting on Brandon)

A Project called "Fernhill spike test" was created from Projects, then "New project". On this account, new Projects are no longer the classic chat Projects. It opened at `claude.ai/code/project/chan_01THacP1Uu7D1P94cGStGD15`, titled "Claude Code", with a coordinator chat, Threads and a Context panel. Its settings hold a Coordinator model and a Threads model (both Opus 5.5, Threads at Medium), "Project instructions" described as being like a CLAUDE.md, an "Auto memory" file (`MEMORY.md`) that Claude writes itself and that every thread reads, a cloud environment, and "Your computer" set to On. The older Projects on the account (for example ProfileBase) still open as classic chat Projects at `claude.ai/project/<id>` with an Instructions panel, but the "New project" button only makes the new kind. The new Project does appear in the chat composer's Project picker, marked "Uses this project's settings".

No instruction has been entered yet, and no test conversation has been sent. The open problem is that the new Project's auto memory carries notes from one thread to the next, which would make the runs unequal, and the Project is a Claude Code surface rather than plain Claude chat.

Brandon chose to run both: plain chat with the instruction in the account's "Instructions for Claude" (the main Claude chat result), and the new Project as a second data point.

### Step 5. The runs in Claude chat (2026-11-26, 19:01 to 19:08 UTC)

The account's "Instructions for Claude" was set to "This Project is for Fernhill Coffee. Its GTM Base is brandon-sellers13/gtm-base-test." (it was empty before). Every run used Opus 5.5 at "Medium", a new conversation, and the bare task. Times are from pressing send to the stop button disappearing, measured in the page with `performance.now()`. The message box's tools menu lists connectors with on/off switches, and that switch carries over to new conversations; uploaded skills appear in the same menu without a switch and are turned on or off under Plugins.

| Run | Condition | Sent (UTC) | Seconds | Skill used? | Conversation |
|---|---|---|---|---|---|
| Task 1 | Native | 19:01:57 | 18.3 | Yes: "Read positioning.md", 72-hour lead, signed "The Fernhill roasting crew", closing line, 42-character subject | `claude.ai/chat/a9e6e2fa-ef71-470f-91c1-4c481a574d53` |
| Task 2 | Native | 19:02:50 | 13.4 | Yes: "Read positioning.md", lines of 40, 33 and 42 characters | `claude.ai/chat/ab1013ee-151d-4807-aca5-e6b88008bc2b` |
| Task 3 | Native | 19:03:26 | 15.4 | Yes: "Read positioning.md", 72-hour lead, 41-character headline, closing line | `claude.ai/chat/6e637662-6bda-4bc4-ba0f-fd999db21477` |
| Task 1 | Connector | 19:04:30 | 16.5 model time | Yes: "Used GTM Base test: Use a company skill", 72-hour lead, crew sign-off, closing line | `claude.ai/chat/ee490039-6e61-407e-9c4a-70711f4ce2bf` |
| Task 2 | Connector | 19:06:38 | 23.0 | Yes: "Used GTM Base test", lines of 41, 39 and 36 characters | `claude.ai/chat/2fac4eaa-bcf0-413e-9a4d-be09f6955b73` |
| Task 3 | Connector | 19:07:26 | 16.8 | Yes: "Used GTM Base test: Use a company skill", 72-hour lead, closing line | `claude.ai/chat/8fafb437-2e83-4f05-963b-7b7eec536ee9` |
| Write test | Connector | 19:08:10 | 15.2 | Write worked: "Used GTM Base test: Propose a context change" with base, what changed, why and evidence | `claude.ai/chat/635c3412-d2e1-44b6-8bf7-81e9c640a6e4` |

Between the native and connector runs, "Fernhill copy" was turned off under Plugins ("Fernhill copy has been turned off.") and the connector was switched on in the tools menu; the skill then no longer appeared in that menu.

The first connector run stopped after 6.6 seconds at a permission prompt: "Claude wants to use Use a company skill from GTM Base test", with Decline, Always allow and Allow once. Claude's rules for this session do not let it approve that prompt, so Brandon clicked "Always allow" (at 19:05:28 UTC). The answer finished 9.9 seconds later, so 16.5 seconds of model time; about 58 seconds passed on the clock. At the same moment the message box's permission mode changed from Manual to Auto, and the "Auto is now the default" notice was gone. No later run asked, including the write test.

Every conversation also showed "Brandon's MacBook Pro, Connected" (computer actions available), in both conditions.

### Step 4 continued. The new Project (19:09 to 19:11 UTC)

The new Project's "Project instructions" were set to the same line (they were empty). With the Project picked in the message box, the bare task went into the Project's one ongoing coordinator chat rather than a new conversation.

| Run | Condition | Sent (UTC) | Seconds | Skill used? |
|---|---|---|---|---|
| Task 1 | Connector on, skill off | 19:09:47 | 24.4 | No: signed "The Fernhill Coffee team", no 72-hour lead, no closing line, and no call reached the server |
| Task 2 | Skill on, connector off | 19:11:24 | 19.1 | No: no freshness lead, and "Come back to Fernhill, and your first order is on us" is 51 characters |

The Project's "+" menu offers only "Add files or photos", "Slash commands" and "Work locally", with no connectors. With the skill on, `/fernhill-copy` was listed in its slash commands. The coordinator's first message said it had read recent sessions. Its MEMORY.md was empty before the runs and was not checked afterwards.

### Step 6. Cowork

The desktop app is signed in to Brandon's work account, so the Cowork tab there was not run. On claude.ai, the mode switch's "Claude" option has the internal value "cowork", and every tool call from the chat runs reached the server marked `x-anthropic-client: Cowork` with client name `claude-code`, so the chat runs above ran on the Cowork harness.

### Step 7. Put everything back (19:12 to 19:14 UTC)

- "Instructions for Claude" was emptied and saved ("Saved").
- "Search and reference chats" and "Generate memory from chats" were turned back on. After a reload: both on, "Include sensitive topics in memory" off, Instructions empty. This matches the starting values.
- GTM Base test's tool permissions: "Use a company skill" was set back from "Always allow" to "Needs approval". After a reload all four tools showed "Needs approval".
- The message box's permission mode was set back from Auto to Manual, and stayed Manual after a reload. The "Auto is now the default" notice cannot be brought back.
- Left in place as evidence: the GTM Base test connector (connected, switched on in the tools menu), the Fernhill copy skill (installed and turned on, as it was after upload), the seven chat conversations, and the "Fernhill spike test" Claude Code project with its Project instructions set and its two runs.

### Step 8. What Claude sent (read from `spike-log` on 2026-11-26)

- No calls arrived during the native runs (19:01 to 19:04).
- Each connector conversation opened its own MCP connection: `server/discover` (2026-07-28), then `initialize`, `notifications/initialized` and `tools/list` under 2025-11-25, then the tool calls, all carrying the spike's `mcp-session-id` for that connection. From the first connector run on, the headers included `x-anthropic-client: Cowork`. One `server/discover` at 19:04:39 came from client "Anthropic/ClaudeAI" with `x-anthropic-client: ClaudeAI` before the permission prompt; the agent's own connection followed at 19:05:29 as `claude-code`.
- Every `tools/call` carried `_meta` with `com.anthropic/session`, `claudecode/toolUseId` and `progressToken`, and headers `mcp-method`, `mcp-name`, `mcp-protocol-version`, `mcp-session-id`, `user-agent: Claude-User` and `x-anthropic-client: Cowork`.
- `com.anthropic/session` by conversation: task 1 `v1.1941673e…`; task 2 `v1.61b73512…` on all four of its calls (three `read_document` calls that returned GitHub 404s for `context/brand-voice.md`, `context/icps.md` and `context/positioning.md`, then `use_skill`); task 3 `v1.67cc5366…`; write test `v1.9049fedd…`. The same value within a conversation and a different one between conversations.
- Sign-in records are under Step 1.

## Teardown: not done (as of 2026-11-26)

Brandon decided on 2026-11-26 not to tear the spike down yet. None of the teardown steps in `CLAUDE-HALF-HANDOFF.md` ("When the spike is finished") has been done, so all of these are still live:

- The Netlify site `gtm-base-connector-spike` (https://gtm-base-connector-spike.netlify.app) and its `spike-log` store.
- The extra redirect address `https://gtm-base-connector-spike.netlify.app/spike/oauth/github-callback` on the GTM BaseLive GitHub App.
- The "GTM Base test" connector and the "Fernhill copy" skill on Brandon's personal Claude account, and the test connector and skill on his ChatGPT account.
- The test conversations in Claude and the "Fernhill spike test" Claude Code project.

Each step waits for Brandon's go-ahead.
