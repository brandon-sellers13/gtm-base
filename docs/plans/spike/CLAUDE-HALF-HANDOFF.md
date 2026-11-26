# Hand-off: the Claude half of the connector spike (S0)

This file is the full brief for running the Claude chat and Cowork half of the spike on Brandon's personal Claude account. It can be followed by Brandon himself or handed to a Claude session that runs on that account and can use Brandon's browser. Nothing here needs the earlier conversation.

## What this is and why it matters

GTM Base is Brandon's product: a Claude Code plugin plus a company "base" of marketing context kept in a GitHub repository, with a web app on Netlify. The next goal is to reach people who work in Claude chat, Cowork and ChatGPT. The plan is one connector (a remote MCP server) that serves a company's documents and its approved skills into those products. The plan is `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`, and its section "Spike results (S0)" holds every answer so far.

The ChatGPT half is done. In ChatGPT, the skill served by the connector was used in 6 of 6 runs, and the same skill installed natively was used in 0 of 6, including a fair rerun with memory off and identical prompts. Sign-in, the conversation id and write calls were all verified in ChatGPT. Claude is untested because Brandon's work Claude organization only lets an Owner add a connector for everyone, so this half runs on his personal Claude account.

The Claude half answers three things:

1. Question 1: in Claude chat and in Cowork, is the connector's skill used as reliably and as quickly as the same skill installed natively?
2. Question 3: does the connector's sign-in work from Claude?
3. Question 5: does Claude send anything with each call that identifies the conversation?

## Ground rules

- Use only the invented test content (Fernhill Coffee, a made-up coffee roaster) and the private test base `brandon-sellers13/gtm-base-test`. Never use client material, and never touch Brandon's work Claude organization, GitHub organization or tools.
- Add the connector, the skill and the Projects at personal scope only.
- Before changing any setting, write down its current value, and put it back afterwards.
- The click that approves GitHub access is Brandon's. If GitHub approves on its own because he approved before, say so in the results.
- Write results in plain, full sentences, with no em dashes.

## What already exists

- The test connector, live on its own Netlify site: `https://gtm-base-connector-spike.netlify.app/spike/mcp`. The live web app is untouched.
- It offers four tools: list my bases, use a skill (returns the invented Fernhill skill with its positioning document), read a document (reads real files from `gtm-base-test`), and propose a change (records nothing).
- The native copy of the same skill: `docs/plans/spike/fernhill-copy.zip` in this repository. The same files unzipped are in `docs/plans/spike/fernhill-copy/`.
- Every call the connector receives is recorded in a Netlify Blobs store called `spike-log` on the test site, including any headers or metadata that could identify a conversation. Tokens are never recorded.
- The code lives on the branch `claude/connector-spike-d1143a`, in the worktree `~/Build/gtm-base/.claude/worktrees/connector-spike-d1143a`.

The skill is easy to spot when it has been used. Its emails and posts end with the line "Roasted in Oakland, delivered within 72 hours.", its emails are signed "The Fernhill roasting crew", it leads with "roasted within 72 hours of delivery", and its subject lines stay under 45 characters.

## Step 1. Add the connector in Claude

1. Sign in to claude.ai with the personal account.
2. Open Customize, then Connectors, then "Add custom connector".
3. Name it `GTM Base test`, give it the URL `https://gtm-base-connector-spike.netlify.app/spike/mcp`, and leave the advanced settings (client ID and secret) empty.
4. Select Connect. A GitHub window opens. Sign in if asked and approve "GTM BaseLive".
5. Write down whether it connected and the exact wording of any error. This is the answer to question 3 for Claude.

If the personal plan does not allow custom connectors, or allows only one and one is already in use, stop and tell Brandon. (Not verified: free accounts are believed to allow one custom connector.)

## Step 2. Upload the native skill

1. Open Customize, then Skills, and upload `docs/plans/spike/fernhill-copy.zip`.
2. Write down whether the upload worked. If Skills need code execution turned on, note that and ask Brandon before turning it on.

## Step 3. Turn memory off for the test

1. In Claude's Settings, find the memory settings (for example "Search and reference chats" and "Generate memory from chat history").
2. Write down each one's current value, then turn them off.
3. They go back on in Step 7.

## Step 4. Make the test Project

1. Create a Project called `Fernhill spike test`.
2. Give it this instruction, exactly: `This Project is for Fernhill Coffee. Its GTM Base is brandon-sellers13/gtm-base-test.`
3. Use the same model for every run, and write down which one.

## Step 5. The runs in Claude chat

There are two conditions and three tasks. Each run is a new conversation inside the Project, and the prompt is the bare task.

- Native condition: the native skill is on, and the GTM Base test connector is turned off for the conversation (use the tools menu under the message box).
- Connector condition: the connector is on for the conversation, and the native skill is turned off under Customize, then Skills.

The three tasks, pasted exactly:

1. `Write a short email to our office customers announcing that our decaf blend is now available.`
2. `Give me three subject lines for a win-back email to offices that cancelled.`
3. `Write a LinkedIn post on why roast dates matter for office coffee.`

For each run, record whether the skill was used (the signs above, and whether Claude shows it read the skill or called the connector) and the seconds from pressing send until the answer has finished. If a browser can be scripted, time it in the page; otherwise use a stopwatch, and say which.

After the connector runs, run one more conversation in the Project with this prompt, to see whether a write works from Claude: `Propose a context change to our base: we now offer oat milk with every delivery, because customers kept asking; evidence: 31 requests in November support tickets.`

## Step 6. The runs in Cowork

Repeat Step 5 in Cowork in the Claude desktop app, signed in to the same personal account, with a Cowork project carrying the same instruction. Cowork loads skills and connectors from the account, so Steps 1 and 2 already cover it. Record the same two things per run.

## Step 7. Put everything back

1. Turn the memory settings back to the values written down in Step 3, then reload the settings page and check.
2. Leave the Project and its conversations in place as evidence, unless Brandon says otherwise.
3. Leave the connector and the skill installed unless Brandon says otherwise, and say which way they were left.

## Step 8. Read what Claude sent (question 5)

On Brandon's computer, in a terminal, from the worktree's `web` folder (it is linked to the test site), list and read the stored calls:

```bash
cd ~/Build/gtm-base/.claude/worktrees/connector-spike-d1143a/web
netlify blobs:list spike-log
netlify blobs:get spike-log <key>
```

Each `rpc` record shows the method, the tool, its arguments, the call's `_meta`, the headers that could identify a session (names starting with `mcp-`, `x-anthropic`, `anthropic`, `x-conversation`, `x-session` and similar), and any MCP session id Claude sent back. Compare the records from two different conversations. Question 5 is answered for Claude when it is clear whether any value stays the same within one conversation and changes between conversations. If nothing does, write that down plainly: it means a server-side "one base per conversation" rule cannot be enforced in Claude.

Also check the records from Step 1 for the sign-in steps: `register` (which return address Claude used), `authorize`, `github-callback.ok` and `token`.

## Step 9. Write the results into the plan

In `docs/plans/2026-11-26-001-feat-chat-connector-plan.md`, on the branch `claude/connector-spike-d1143a`:

- Question 1: fill the Claude chat and Cowork rows of the table, with a short note on how the runs were done and anything that was not equal between the two conditions.
- Question 2: add whether the write worked from Claude.
- Question 3: replace "Claude, not yet tested" with what happened.
- Question 5: add what Claude sends, with the evidence.
- The recommendation on C1 to C5: confirm or change it in light of the Claude results.
- The S0 line under Units: mark it done if all five questions now have answers.

Commit on that branch. Do not merge to main, and do not deploy over the live site.

## When the spike is finished

Tell Brandon the results, then, with his go-ahead: delete the Netlify site `gtm-base-connector-spike`, remove the extra redirect address `https://gtm-base-connector-spike.netlify.app/spike/oauth/github-callback` from the GTM BaseLive GitHub App, and remove the test connector and skill from Claude and ChatGPT.
