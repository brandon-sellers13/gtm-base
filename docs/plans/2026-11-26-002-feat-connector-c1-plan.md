---
title: "C1: the connector itself (MCP endpoint, sign-in, one base per conversation)"
type: feat
status: approved by Brandon on 2026-11-26 with all four recommended answers; built and checked locally, waiting for the test site
date: 2026-11-26
parent: docs/plans/2026-11-26-001-feat-chat-connector-plan.md (Unit C1)
unit: "C1"
---

# C1: the connector itself

## What this builds

C1 puts the GTM Base connector into the web app, so that Claude chat, Cowork, ChatGPT and Claude Code can sign in with GitHub and call it. It has four parts: the MCP endpoint at `https://gtm-base-app.netlify.app/mcp`, built on the official MCP library; a small OAuth server in front of the web app's existing GitHub sign-in; the same invite rules the web app uses today; and the one-base-per-conversation rule, kept in the store Brandon approved on 2026-11-26.

C1 ships two tools, which is the least that lets the walls be tested end to end. "List my bases" names the bases the person can reach. "Read a document" returns one file from a base as it stands on GitHub, without the moment-of-use flag. C2 adds the flag and the list of documents that exist, C3 adds skills and C4 adds proposing, all on top of what C1 builds.

The spike's server (branch `claude/connector-spike-d1143a`) is the evidence for what both products accept. C1 does not copy it: the protocol handling moves to the library, and every gap the spike left is closed below.

## What the research found (2026-11-26)

Each line says whether it is verified (read in official docs or seen working), inferred (follows from what was read, not seen) or guessed (not checked).

| Point | Status | Source |
|---|---|---|
| The official MCP library is now `@modelcontextprotocol/server` 2.4.0 (published 2026-10-23), version two of the TypeScript SDK, implementing the 2026-07-28 spec. The old `@modelcontextprotocol/sdk` 1.32.2 is the previous line. | Verified | npm registry; the package's README |
| Version two has `createMcpHandler`, whose `handler.fetch` takes a web-standard `Request` and returns a `Response`. | Verified | ts.sdk.modelcontextprotocol.io/v2/serving/http |
| A Next.js route handler can call `handler.fetch(request, { authInfo })` directly, with no Express. | Inferred | The docs do not mention Next.js, but route handlers take and return the same web-standard objects |
| By default the handler answers 2026-07-28 clients and also answers 2025-era clients (`initialize`) on the same address, holding nothing between requests. It runs its factory once per request, which suits Netlify's functions. | Verified | The serving guide and the "support 2026-07-28" migration page |
| The 2026-07-28 spec removes MCP sessions, the `Mcp-Session-Id` header and the `initialize` handshake. | Verified | modelcontextprotocol.io/specification/2026-07-28/changelog |
| The 2026-07-28 spec deprecates dynamic client registration in favor of client metadata documents, makes clients check `iss`, and requires servers to check that a token was issued for them (its audience). | Verified | The same changelog and the authorization page |
| The library's handler checks no token, `Host` or `Origin` itself; the server must verify the bearer token and pass the result in. | Verified | The serving guide |
| The library's ready-made authorization server lives in `@modelcontextprotocol/server-legacy` and is built for Express. | Verified (names only) | The library's API index |
| Netlify Blobs: a store from `getStore` lasts across deploys; reads are eventually consistent (up to 60 seconds) unless `consistency: "strong"` is asked for; `set` and `setJSON` take `onlyIfNew` and `onlyIfMatch` and answer `modified: false` when the condition fails. There is no expiry on entries. | Verified | docs.netlify.com Netlify Blobs page; `onlyIfNew` and `modified` read in the type definitions of `@netlify/blobs` 10.7.13, the version the spike ran on Netlify |
| `@netlify/blobs` is now at 11.1.12. | Verified | npm registry |
| `getStore` works with no settings inside the web app's route handlers on Netlify. | Verified | The spike wrote its call log this way on its own Netlify site |
| Rewrites from `/.well-known/...` to route handlers work on Netlify, and both products accepted the discovery documents served that way. | Verified | The spike |
| Both products still send their conversation id (`com.anthropic/session`, `openai/session`) in a tool call's `_meta` when the server speaks 2026-07-28. | Not known | Seen only under 2025-11-25, because the spike answered "method not found" to `server/discover`. C1's first step checks it |
| A tool written with the version two library can read the call's `_meta`. | Inferred | The library passes request context to tools; the exact field is checked in step one |
| Netlify's time limit for a synchronous function on this site. | Guessed, not checked | The Next.js runtime page does not state it; step one measures the slowest call instead |
| GitHub invalidates a GitHub App's refresh token once it has been used. | Guessed, not checked | Step four tests it |

## The library choice

**Recommended: `@modelcontextprotocol/server` (version two), mounted in a Next.js route handler with `createMcpHandler`, in its default stateless mode.** It is the official library, it is the stable line, it speaks 2026-07-28 (which both products ask for first) and still answers `initialize` for anything older, and it keeps nothing in memory between calls, which is how Netlify runs the app. It brings `zod` 4 with it. The web app's TypeScript 5 needs no change; the README's note about `"types": ["node"]` applies only from TypeScript 6.

**Runner-up: `mcp-handler`**, the adapter Vercel publishes for Next.js (2.4.0, 2026-11-12). Its documentation could not be read (npm refused the request), so which protocol it speaks and whether it needs Redis are unknown. It would put a second maintainer between GTM Base and the protocol for no gain.

**Not chosen: a hand-written handler, as in the spike.** Both products already ask for 2026-07-28, and its shape (no handshake, no sessions, new metadata) is what a library should carry.

**The OAuth server stays our own code**, about five small route handlers rewritten from the spike with its gaps closed. The library's own authorization server is Express-shaped and in a package marked legacy, and the spike's version is already proven with both products. The library's `bearerAuth` and metadata helpers are used where they fit the route handlers; if they assume Express, the checks are written directly with `jose`, which the app already uses.

## The endpoint

| Address | What it does |
|---|---|
| `POST /mcp` | The MCP endpoint. Checks the bearer token first, then hands the request to the library. |
| `GET /.well-known/oauth-protected-resource` and `/.well-known/oauth-protected-resource/mcp` | Resource metadata (RFC 9728): the resource `https://gtm-base-app.netlify.app/mcp`, the authorization server, the scope `base`. Served by a rewrite, as in the spike. |
| `GET /.well-known/oauth-authorization-server` | Authorization server metadata (RFC 8414), with `authorization_response_iss_parameter_supported: true`. |
| `POST /api/connector/oauth/register` | Dynamic client registration (RFC 7591). |
| `GET /api/connector/oauth/authorize` | Starts sign-in. |
| `GET /api/connector/oauth/github-callback` | GitHub returns here. |
| `GET` and `POST /connect/consent` | The consent page (a page in the web app, in its design). |
| `POST /api/connector/oauth/token` | Code and refresh token exchange. |

Every address the server names (the issuer, the resource, each endpoint) is built from `APP_URL`, never from request headers, so `iss`, the metadata and the token's audience always agree. The spike built them from forwarded headers, which is one more thing a request could influence.

**The off switch.** All of the above answers 404 unless `CONNECTOR_ENABLED` is set on the site. So C1 can merge to main and deploy to the live site with the connector closed, and Brandon turns it on after the security review.

**A 401 that products can follow.** A call with no token, an unreadable token, a token for another audience, a login taken off the allowlist, or a GitHub token GitHub no longer accepts all get the same answer: 401 with `WWW-Authenticate: Bearer resource_metadata="https://gtm-base-app.netlify.app/.well-known/oauth-protected-resource", scope="base"`. Both products then run sign-in again on their own.

## Sign-in, step by step

1. **Registration.** The product registers with a name and its return addresses. The answer's client id is a sealed value holding those addresses and the name, as in the spike, so registration stores nothing and costs nothing to repeat. Only these return addresses are accepted:
   - Claude: `https://claude.ai/api/mcp/auth_callback` and `https://claude.com/api/mcp/auth_callback` (the first verified in the spike, both in Claude's docs).
   - ChatGPT: `https://chatgpt.com/connector_platform_oauth_redirect` (verified in the spike).
   - Claude Code: `http://localhost:<any port>/callback` and `http://127.0.0.1:<any port>/callback`. The path is inferred and checked in step one; a loopback address may use any port, as RFC 8252 asks.

   Client metadata documents, which the new spec prefers, are left out of C1: both products registered dynamically in the spike, and fetching a metadata document from an address the client names means the server makes outbound requests on a stranger's say-so, which needs its own care. It is the runner-up and a later addition when a product stops offering dynamic registration.

2. **Authorize.** The request must name a registered return address, `response_type=code`, an S256 PKCE challenge, and, when it sends `resource`, exactly this server's resource (anything else is refused as `invalid_target`). Errors that can go back to the product go back with `iss` and `state`. The request is kept in a short sealed cookie (ten minutes), and the person goes to GitHub.

3. **GitHub callback.** The server exchanges GitHub's code itself and keeps GitHub's access token, its refresh token and their lifetimes. This needs one more callback address on the GTM BaseLive GitHub App (see "What Brandon must do"). It reuses nothing of the web app's own sign-in cookie, because that cookie keeps only GitHub's access token, which ends after eight hours, and a connector without GitHub's refresh token would make people sign in again every eight hours.

4. **The invite rule.** The same rule as the web app: the login is on `ALLOWED_GITHUB_LOGINS`, or the person reaches a base on an allowed account (the team rule in `team.ts`). Both sign-ins call one shared function, moved out of `/api/auth/callback`, so the two can never drift. Someone the rule turns away sees the web app's invite-only message and the product gets `access_denied`.

5. **Consent.** A page in the web app says, in full sentences, which product is asking and who is signed in: the name the product gave when it registered (shown as the name it gives itself, since anyone can register any name), the place the answer goes back to in words ("claude.ai", "chatgpt.com", or "a program on this computer" for a loopback address), the GitHub account, and what the connector can do (read the bases this GitHub account can reach; later, propose changes; never approve). Allow sends the code back to the product with `iss`; Cancel sends `access_denied`. The page cannot be framed by another site (`frame-ancestors 'none'`), and the Allow form is accepted only from the app's own origin with the sealed request in both the form and the cookie. The page shows every time a product connects, which happens once per product per person, plus whenever someone reconnects.

6. **Token.** Form-encoded only, as Claude's docs require. The code must open, must not be older than two minutes, must match the client id and the return address, and the PKCE verifier must match. Each code works once (see the grants store). The answer carries an access token for one hour, a refresh token, `token_type` Bearer and the scope. No step here calls GitHub, so the answer comes well inside Claude's ten seconds; step four measures it.

7. **Refresh.** The refresh token is rotated every time: the old one stops working and a new one is issued. A refresh token used a second time ends the whole chain it belongs to, so a stolen copy and the real one cannot both live. When GitHub's own token is near its end, the refresh also refreshes at GitHub. The allowlist is checked again here. The refresh token lasts as long as GitHub's own refresh token, so a person who stops using the connector for longer than that signs in again.

## Where the GitHub token lives

**Recommended: inside the tokens the product holds, encrypted, as in the spike.** The access token carries GitHub's access token, and the refresh token carries GitHub's refresh token, each sealed with A256GCM under a key only the server holds. The product can neither read nor change them. The approved store never holds a token, which is what Brandon approved, and the app never becomes a place where every user's GitHub token sits together.

The keys come from a new secret, `CONNECTOR_SECRET`, with a separate key for each kind of value (client, pending sign-in, code, access, refresh). The spike used the web app's `SESSION_SECRET`; a separate secret means changing one never signs people out of the other, and changing `CONNECTOR_SECRET` ends every connector sign-in at once, which is the emergency off switch.

Every access token names its audience (the `/mcp` resource), its client, the GitHub login, whether the person came in by the team rule, and the chain it belongs to. The endpoint refuses a token whose audience is not this server.

**Runner-up: keep GitHub's tokens on the server** and hand the product only a reference. That allows revoking one person at once, but it puts every user's GitHub tokens in one store and goes beyond what Brandon approved for the store, so it is not recommended. A person can already cut the connector off at once by revoking GTM BaseLive in their GitHub settings, after which every call gets the 401 above.

## The store

Two Netlify Blobs stores from `getStore` (site-wide, so they last across deploys), every read and write with `consistency: "strong"`.

**`connector-bindings`, the store Brandon approved.** It binds a conversation to the first base it uses and holds nothing else.

- **Key:** an HMAC (keyed by `CONNECTOR_SECRET`) of the product, the conversation id and the GitHub login. The store therefore never holds a product's raw conversation id, and two people can never collide on one key.
- **Value:** the base (`owner/repo`), the product, and when it was bound.
- **Which conversation id**, in order: `com.anthropic/session` or `openai/session` from the call's `_meta`; if neither arrives and the call came in under 2025-11-25, the MCP session id. Since the version two library holds no sessions, the endpoint mints that session id itself at `initialize` (a sealed random value in the `Mcp-Session-Id` header) and Claude sends it back on every call, as the spike saw. Under 2026-07-28 there is no session id at all, so the product's conversation id is the only key there.
- **No conversation id at all:** the call is refused, saying the connector could not tell which conversation it belongs to (decision 3).
- **Binding, race-free:** read the key; if a base is there and it is a different one, refuse. If nothing is there, `setJSON` with `onlyIfNew`; if that answers `modified: false` because a parallel call bound it first, read again and compare. A base is bound only after the person's own GitHub token has shown it is a base (it holds `context/map.md`), so a guessed or misspelled name cannot take the slot.
- **What the model sees:** the first answer in a conversation says "This conversation now uses the base owner/repo. To work on a different base, start a new conversation." A refusal names the conversation's base and never the one asked for, and never lists other bases.
- **"List my bases" in a bound conversation** answers only that conversation's base, so another client's name never shows up in it. In an unbound conversation it lists every base the person can reach, as now.
- **Kept until removed.** Blobs has no expiry, and letting a binding lapse would let an old conversation switch bases. Each record is under 200 bytes; a cleanup job can come later if the count ever matters.

**`connector-grants`, needed for single-use codes and revoking rotated refresh tokens (decision 1).** It holds random ids and counters only, never a token.

- `chain/<id>`, where the id is the code's own id: created with `onlyIfNew` when a code is exchanged, so its existence is the mark that the code was used. A second exchange finds it, is refused, and ends the chain that code started, as OAuth 2.1 asks. (As built: one record rather than a separate dated code mark, because a dated key would have let a code used just before midnight be used again just after it.)
- The same record holds the current refresh generation and whether the chain was ended. A refresh with the current generation moves it on by one (`onlyIfMatch` on the record's ETag, so two refreshes at once cannot both win); a refresh with an old generation ends the chain.
- Access tokens are not checked against this store on every call, to keep calls fast; an ended chain stops at the next refresh, within the access token's one hour.

## Invite rules and walls, as the endpoint applies them

1. The token must open, be for this audience and be within its life.
2. The login must still pass the invite rule. A login on the allowlist is checked against the list on every call, exactly as the web app's session is, so removing a login ends its access at once. Someone let in by the team rule keeps access while GitHub keeps showing them the base, also as in the web app.
3. Every tool except "List my bases" requires a base, in the `owner/repo` form the web app already checks (`validRepo`). A call without one is refused with an instruction to ask the person and never to guess.
4. The base must be reachable with the person's own GitHub token and hold `context/map.md`.
5. The base must match the conversation's binding, or bind it if there is none.

The wall stops a conversation from switching to another client's base once its first base is bound, whether the switch comes from memory, a guess or an instruction planted in a document. It does not check that the first base is the one the person meant: the first call binds any real base the person can reach, so a base the model recalls from memory can bind a conversation to the wrong client, and only a guessed name that is not a real base is refused. The first answer names the bound base so the person can see it, but confirming the first base (for example against a base the person chose for that Project in the web app) is an open item, carried from the parent plan's note on the first call. It is not access control: a person can read every base their GitHub account reaches, in GitHub itself, and the connector never shows them more than that. The security review should judge it on that basis.

Nothing is logged that identifies a conversation or holds content: no tokens, no `_meta` values, no arguments. The spike's call log (`spike-log`) is not carried over.

## Build steps

1. **Probe on the test site.** Deploy the library handler with C1's sign-in to the test site, connect Claude chat, ChatGPT and Claude Code, and record, as key names and counts only: which protocol each speaks to a version two server, whether `com.anthropic/session` and `openai/session` still arrive in `_meta` under 2026-07-28, whether each sends `client_id` at the token endpoint (if all do, it becomes required), the path Claude Code's loopback uses, and the slowest call. If a product drops its conversation id under 2026-07-28, the fallback is to serve that product only the 2025-11-25 protocol (the library's `legacy` setting, or not answering `server/discover`), where the session id exists. This step decides decision 3's details before the walls are built on it.
2. **The OAuth server:** discovery, registration, authorize, GitHub callback, consent page, token and refresh, the shared invite rule, `CONNECTOR_SECRET`, `CONNECTOR_ENABLED`.
3. **The endpoint and the stores:** `/mcp` on the library, the token and audience check, the two tools, the bindings store and the grants store.
4. **The checks and the end-to-end run** below, on the test site.
5. **The security review** (one pass), then Brandon turns the connector on for the live site.

### Where the build stands (2026-11-26)

Steps 2 and 3 are built on this branch, checked on a copy running on this computer, and deployed on 2026-11-26 to the test site (https://gtm-base-connector-spike.netlify.app, the spike's site, which Brandon chose to replace; the spike's `/spike/...` addresses are gone). `CONNECTOR_SECRET` (marked secret) and `CONNECTOR_ENABLED` are set there. Steps 1, 4 and 5 wait for Brandon's GitHub App callback address and the product runs.

- **ChatGPT, run on 2026-11-26** (Brandon's personal ChatGPT account, through his browser). The callback address was added to the GTM BaseLive GitHub App (its two existing addresses left as they were). A new custom MCP server, "GTM Base C1 test", was added at `/mcp`. ChatGPT registered dynamically, GitHub signed in without a click (GTM BaseLive was already authorized), the consent page named ChatGPT, chatgpt.com and the GitHub login correctly, Allow returned a code, and ChatGPT showed the connector as connected. In a conversation, "read a document" and "list my bases" both reached the tools.
- **Step 1, answered for ChatGPT by behavior.** Netlify's log reader keeps a line but drops its text (as the spike found), so logs could not say which protocol arrived. Instead a temporary build refused every 2025-era request, and a new ChatGPT conversation still got "This GitHub account reaches no bases yet." So ChatGPT speaks 2026-07-28 to this server and still sends `openai/session` there, which keys the binding with no fallback needed. The temporary build was then replaced with the committed code.
- **The first read found no base, correctly.** GitHub answered that the account cannot reach `gtm-base-test`, and "list my bases" found none: a GitHub App's sign-in token reaches only repositories the app is installed on, and GTM BaseLive was installed on no account. With Brandon's approval, GTM BaseLive was then installed on his personal account for exactly two repositories, `gtm-base-test` and `gtm-base-backup-test` ("Only select repositories"). The live web app will now show those two bases to him.
- **One base per conversation in ChatGPT, run on 2026-11-26.** In conversation one, reading `context/map.md` from `gtm-base-test` answered "This conversation now uses the base brandon-sellers13/gtm-base-test..." and the document. "List my bases" in that conversation answered only "This conversation uses the base brandon-sellers13/gtm-base-test.", so the binding is stored and keyed by ChatGPT's conversation id. In a new conversation, "list my bases" listed both bases, and reading from `gtm-base-backup-test` bound that conversation to it. Asked twice to read the second base inside the first conversation, ChatGPT refused on its own, following the connector's instructions, and never sent the call, so the server's own refusal of a second base has not yet been triggered by a product. It is covered by the check script's one-base section, which still needs a real GitHub App token to run.
- **Claude is not run yet.** The browser's claude.ai is signed in to a work organization on a Team plan, where a custom connector is added for the whole organization; nothing was added there. The Claude half waits for a personal Claude account in the browser. Brandon chose on 2026-11-26 to skip it for now and run it together with the teammate invite test (W5), tracked in `tasks/todo.md`.
- **Checked on the test site, 40 of 40** with the same script and the real Netlify Blobs store, which proves `onlyIfNew` and `onlyIfMatch` there (single-use codes, refresh chains). Exchanging a code took 111 to 187 ms.
- **Found on Netlify and fixed.** A strongly consistent Blobs read of a key that does not exist is retried by `@netlify/blobs` (five times, five seconds apart) and ran past Netlify's 30-second limit, so the first call in every conversation timed out. No read now asks for a missing key: a record is created first with `onlyIfNew` (a conversation starts unbound, a chain that never started is created already ended) and then read, and binding replaces the unbound record with `onlyIfMatch`, which keeps two first calls at once from both binding. Every store call also gives up after eight seconds rather than holding a request. The bindings store therefore holds a record for each conversation that has called, unbound until it reads a base; it still holds nothing but the binding.

- **The code.** `web/src/lib/connector/` (settings and keys, sealing, return addresses, the two stores, the tokens, the tools), `web/src/lib/access.ts` (the invite rule, now shared by the web app's sign-in and the connector's, and by the web app's session check), `web/src/app/mcp/route.ts`, `web/src/app/api/connector/` (discovery, registration, authorize, GitHub callback, consent answer, token) and `web/src/app/connect/consent/page.tsx`. The libraries added are `@modelcontextprotocol/server` 2.4.0, `@netlify/blobs` 11.1.12 and `zod` 4.
- **Checked locally, 40 of 40** with `web/scripts/connector-check.mjs` against `next dev` (which uses an in-memory stand-in for Netlify Blobs with the same first-write-wins rules): discovery, the 401, registration, every authorize refusal, the token endpoint's refusals, PKCE, single-use codes, refresh rotation and the chain ending on reuse, the consent page and its answer (including a post from another site and a missing one-time value), the audience check, the allowlist on every call, both the 2025-11-25 `initialize` and the 2026-07-28 `server/discover`, refusal with no conversation id under both protocols, a product conversation id reaching the tools under 2026-07-28, and a token GitHub refuses turning into a 401. `tsc`, `eslint` and `next build` pass.
- **Found and fixed while checking.** The library answers 2025-era calls as a stream that ends only when the tool finishes, so the endpoint now reads the whole answer before deciding whether GitHub refused the token. The consent page was being built as a fixed page while the connector was off, which would have left it a 404 after turning the connector on; it now always renders per request.
- **Not yet checked.** The one-base checks in the script (binding, refusal of a second base, two first calls at once, the session id fallback) need a real GitHub token for two bases, and the GTM Base guard hook rightly stops an agent from reading `gh auth token`. They run on the test site in the product runs, and Brandon can run them locally with `GITHUB_TOKEN=$(gh auth token) BASE_A=... BASE_B=...`. Netlify Blobs' own `onlyIfNew` and `onlyIfMatch` are checked only on the test site.
- **Step 1 needs no logging.** Whether a product sends its conversation id under 2026-07-28 shows in its behavior: a call that works was keyed by the product's id, because 2026-07-28 has no session id to fall back to, and a missing id answers with the "could not tell which conversation" refusal.

## How it is tested

**A check script, `web/scripts/connector-check.mjs`,** run against the test site (or `next dev`), with no product involved. It checks: both discovery documents and their values; the 401 and its header; registration with each allowed return address and refusal of others; authorize refusing a missing or plain PKCE challenge, an unknown client and a foreign `resource`, each with `iss`; the token endpoint refusing JSON, a wrong verifier, a reused code and an old refresh token, and ending the chain after reuse; a token minted for another audience refused at `/mcp`; and the time of each answer. The web app has no test framework today, so this is a plain Node script rather than a new framework; the sign-in steps that need GitHub are covered by the product runs instead.

**The MCP Inspector** (`npx @modelcontextprotocol/inspector`) against the test site, once under 2026-07-28 and once forced to 2025-11-25, to see both handshakes answer.

**The product runs**, on Brandon's personal Claude and ChatGPT accounts and in Claude Code, against the test site:

1. Each product connects: registration, the consent page naming it correctly, sign-in, the first call.
2. In one conversation, read a document from base A. It binds. Ask for base B in the same conversation: refused, and the answer names only base A. "List my bases" shows only base A.
3. In a new conversation, base B works.
4. Two parallel first calls for different bases in one new conversation (from the check script with a fixed conversation id): exactly one binds.
5. Take Brandon's login off the test site's allowlist: the next call gets 401 and the product asks to sign in again, which the invite rule then refuses. Put it back.
6. Change `CONNECTOR_SECRET` on the test site: every product's next call gets 401. Change it back by signing in again.
7. Revoke GTM BaseLive in GitHub's settings: the next call gets 401.
8. Leave a product connected past one hour: the refresh works and the old refresh token is refused when the check script replays it. Past eight hours, GitHub's token is refreshed too, and the old GitHub refresh token no longer works (the open question in the research table).

The test site needs two bases the test login can reach; `gtm-base-test` is one, and a second empty base made from the template is the other.

## Security points for the review

The review after the build covers at least: the consent page (framing, cross-site posting, what the product name can claim); the return address list, especially the loopback rule; PKCE, single-use codes and refresh reuse; the audience check and the `resource` value; what the sealed tokens hold and the key handling; the invite rule on every call; the bindings (race, key choice, what a refusal reveals); what a document read through the connector could make a conversation do (C2 and C3 widen this); and that nothing sensitive is logged. Nobody but Brandon connects to the live site before it passes.

### The review's result (2026-11-26)

One pass, on PR #18, read every connector file and traced each sealed value and each check. It found no high or medium vulnerability; eighteen candidates were traced and rejected (listed in the review's report and summarized in `tasks/todo.md`). One risk remains, and it belongs to OAuth sign-in itself rather than to this code.

### Known risk: a forwarded sign-in link

**What could happen.** Someone starts adding GTM Base as a connector in their own Claude or ChatGPT account. Their product sends them to GTM Base's sign-in address, which carries their product's own one-time value (`state`) and its PKCE challenge. Instead of finishing it themselves, they send that link to a GTM Base user, for example dressed up as "connect GTM Base here". If the user is already signed in to GitHub and has approved GTM BaseLive before, GitHub lets them through without a click, and the only step left is GTM Base's consent page. If the user clicks Allow, the sign-in code goes back to the product's own return address with the attacker's `state`.

**Why it may or may not work.** Whether the attacker's account then receives a working connection to the victim's bases depends on Claude's and ChatGPT's servers, not on GTM Base. If their return address checks that the `state` belongs to the person whose browser arrives with it, the forwarded sign-in fails there. If it accepts any `state` it issued, the attacker's account is connected as the victim and can read every base the victim's GitHub account reaches, until the victim revokes GTM BaseLive in GitHub or the secret is changed. This cannot be checked from this code. It can be tested with two accounts (see `tasks/todo.md`).

**What defends against it today.** The consent page is shown every time, never remembered. It names the product as it named itself, the place the sign-in goes back to (from a fixed list), and the GitHub account, and it says to choose Cancel if the person did not just add GTM Base themselves. Only Claude's, ChatGPT's and loopback return addresses can register, so the code can never be sent to an address the attacker controls.

**Options if the test shows the products accept a forwarded sign-in,** in order of preference:

1. Ask GitHub to show its account picker on every connector sign-in (`prompt=select_account` on GitHub's authorize address), so a forwarded link stops at a GitHub screen the person did not expect. Inferred from GitHub's documentation, not yet checked with a GitHub App.
2. Make the consent page harder to click through: name the date and time the sign-in was started and require the person to type or confirm something specific to their own setup.
3. Accept the risk for the invite-only stage, where every user is known to Brandon, and say so in the setup guide (C5).

## What Brandon must do

1. ~~Answer the decisions below.~~ Done 2026-11-26.
2. **Add callback addresses to the GTM BaseLive GitHub App:** `https://gtm-base-connector-spike.netlify.app/api/connector/oauth/github-callback` for the test site now, and `https://gtm-base-app.netlify.app/api/connector/oauth/github-callback` for the live site before it is turned on. (GitHub Apps take several callback addresses; the spike's existing one stays until teardown.)
3. **Set `CONNECTOR_SECRET`** (32 random bytes, base64) on the test site now and on the live site later, marked Sensitive in Netlify: it opens every connector token, so it is the kind of key that rule is for. Set `CONNECTOR_ENABLED` on the test site only.
4. **Run the product half of the end-to-end test** with the agent, as in the spike: connect, click Allow on the consent page, approve each product's tool prompts.
5. **After the security review, turn the connector on for the live site** (set `CONNECTOR_ENABLED` there), and then decide the spike teardown.

## Decisions for Brandon (decided 2026-11-26: the recommended answer to all four)

1. **A second small store for sign-in safety. Decided: yes, the `connector-grants` store.** Single-use codes and revoking rotated refresh tokens, the two fixes the spike deferred, need the server to remember that a code was used and which refresh token in a chain is current. Recommended: a `connector-grants` store holding only random ids, a counter and a used-or-ended mark, never a token or any content. Runner-up: no store, relying on PKCE (a stolen code is useless without the verifier) and on GitHub ending its own used refresh tokens, which leaves a reused refresh token working until GitHub's token needs refreshing, up to eight hours.
2. **GitHub's tokens stay inside the encrypted tokens the product holds**, never in a store. **Decided: yes.** Recommended, and it keeps the approved store as approved. Runner-up: keep them on the server for instant revocation of one person, which the store approval does not cover.
3. **A call that carries no conversation id is refused. Decided: yes.** Recommended, since it can only be bound by guessing, and both products sent one on every call in the spike. Runner-up: bind it to the GitHub login for an hour, which would let a product without conversation ids work but would also join that person's separate conversations into one wall.
4. **Use the spike's Netlify site as C1's test site. Decided: yes.** Recommended: it already has its environment, its Blobs and a GitHub App entry, and it keeps every test away from the live site's store. It is torn down with the spike after C1. Runner-up: a new site, which means one more site, one more set of variables and one more callback address.

## What stays the same

The web app's own sign-in, its pages and its session cookie do not change, except that the invite rule moves into a shared function both sign-ins call. Claude Code users with the plugin keep working from their local copy; the connector is an extra way in, not a replacement.
