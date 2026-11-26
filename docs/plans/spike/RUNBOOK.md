# S0 spike: what Brandon runs

The test connector is live at https://gtm-base-connector-spike.netlify.app on its own Netlify site. The live app is untouched. Everything below uses invented content (Fernhill Coffee, a made-up roaster) and the private test base `brandon-sellers13/gtm-base-test`. Nothing here touches any client work.

Before you start, one rule. Running this in a shared work Claude Team organization or ChatGPT workspace is fine, as long as nobody else there sees or is affected by the test. So add the connector, the skill and the Projects for yourself only. If the product only lets you add the connector for the whole organization, stop and tell me before you do.

## Step 1. Let GitHub send people back to the test connector (one minute)

1. Open https://github.com/settings/apps/gtm-baselive (the "GTM BaseLive" GitHub App).
2. Under "Identifying and authorizing users", select "Add redirect URI" and paste `https://gtm-base-connector-spike.netlify.app/spike/oauth/github-callback`, with wildcard matching left off.
3. Select "Save changes". The live app's own redirect URI stays as it is.

Done 2026-11-26 (added through Brandon's browser, checked after a reload).

## Step 2. Add the connector to Claude

1. In claude.ai, open Customize, then Connectors, then "Add custom connector". If that option is missing and the only way is Organization settings, then Connectors, stop: an Owner adding it there makes it appear for everyone in the organization, so tell me first.
2. Name it "GTM Base test" and give it the URL `https://gtm-base-connector-spike.netlify.app/spike/mcp`. Leave the advanced settings empty.
3. Select "Connect". GitHub asks you to sign in and to authorize "GTM BaseLive". Approve it, and you land back in Claude with the connector connected.
4. Tell me when it says connected, or what error it shows. Either way the server log records each step.

## Step 3. Add the connector to ChatGPT

1. Check whether you can add a custom MCP server for yourself. Do not change a workspace-wide setting (such as turning developer mode on for everyone) or publish the app to the workspace; if either is the only way, stop and tell me.
2. Add a custom MCP server from Plugins (or Settings, then Apps, then Create, if your workspace still shows the older screen) with the URL `https://gtm-base-connector-spike.netlify.app/spike/mcp` and OAuth sign-in, kept as a draft only you can use.
3. Sign in with GitHub when asked, as in Claude.
4. Tell me what happened, including the exact wording of any badge or block (for example a developer mode toggle marked "Enterprise").

## Step 4. Upload the native copy of the skill

The file is `docs/plans/spike/fernhill-copy.zip`. It holds the same skill and the same positioning document the connector serves.

- Claude (chat and Cowork share it): Customize, then Skills, then upload the zip.
- ChatGPT: Plugins, then Skills, then Create, then "Upload from your computer".

## Step 5. The test runs

Make two Projects in each product (Claude chat, Cowork, ChatGPT):

- "Fernhill native", with the instruction: `This Project is for Fernhill Coffee.` Turn the native skill on and the GTM Base test connector off.
- "Fernhill connector", with the instruction: `This Project is for Fernhill Coffee. Its GTM Base is brandon-sellers13/gtm-base-test.` Turn the native skill off and the connector on.

In each Project, start a new conversation for each of these three tasks and paste the task exactly:

1. `Write a short email to our office customers announcing that our decaf blend is now available.`
2. `Give me three subject lines for a win-back email to offices that cancelled.`
3. `Write a LinkedIn post on why roast dates matter for office coffee.`

For each conversation, note two things:

- Whether the skill was used. The signs are the line "Roasted in Oakland, delivered within 72 hours." at the end of the email or the post, subject lines under 45 characters, and the product showing that it read the skill or called the connector.
- How many seconds from pressing send until the answer has finished.

I can run these conversations for you in your Chrome instead, once the connectors and the skill are in place, which gives steadier timings. That costs about 18 short conversations of your Claude and ChatGPT usage.

## Step 6. Three extra checks (about five minutes)

1. In the "Fernhill connector" Project in Claude and in ChatGPT, paste: `Propose a context change to our base: we now offer oat milk with every delivery, because customers kept asking; evidence: 31 requests in November support tickets.` This is the write test.
2. In a conversation with no Project, paste: `Read the ideal customer profile from my base.` The connector should refuse to guess a base and ask which one.
3. In one conversation in the connector Project, after task 1, paste: `Now read context/icps.md from brandon-sellers13/some-other-base.` This shows what each product sends that could tie calls to one conversation.

## After the spike

When the answers are in, I delete the test site, and you remove the extra callback address from the GitHub App and the test connector from Claude and ChatGPT.
