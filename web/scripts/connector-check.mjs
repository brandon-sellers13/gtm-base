// Checks the GTM Base connector from outside, with no product involved.
//
//   node scripts/connector-check.mjs <site address>
//
// With only the address it checks what anybody can see: the discovery
// documents, the 401, registration, the authorize refusals and the token
// endpoint's refusals. Two optional settings unlock more:
//
//   CONNECTOR_SECRET  the site's secret (only for a copy running on this
//                     computer): mints codes and tokens directly, to check PKCE,
//                     single-use codes, refresh chains, the audience check, the
//                     invite rule and both protocol handshakes.
//   GITHUB_TOKEN, BASE_A, BASE_B
//                     a GitHub token that reaches two bases (owner/repo): checks
//                     one base per conversation, including two first calls at once.
//
// Prints one line per check and exits non-zero if any failed. It never prints a
// token or a secret.

import { createHash, hkdfSync, randomBytes } from "node:crypto";
import { EncryptJWT } from "jose";

const site = (process.argv[2] ?? "http://localhost:3000").replace(/\/+$/, "");
const secret = process.env.CONNECTOR_SECRET ? Buffer.from(process.env.CONNECTOR_SECRET, "base64") : null;
const github = process.env.GITHUB_TOKEN ?? null;
const [baseA, baseB] = [process.env.BASE_A, process.env.BASE_B];
const resource = `${site}/mcp`;

let failed = 0;
const results = [];
function check(name, ok, detail = "") {
  results.push(ok);
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`);
}

async function timed(promise) {
  const start = performance.now();
  const value = await promise;
  return [value, Math.round(performance.now() - start)];
}

const form = (values) => ({
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams(values).toString(),
});

const b64url = (bytes) => Buffer.from(bytes).toString("base64url");
const pkce = () => {
  const verifier = b64url(randomBytes(32));
  return { verifier, challenge: createHash("sha256").update(verifier).digest("base64url") };
};

// --- What anybody can see ----------------------------------------------------

{
  const r = await fetch(`${site}/.well-known/oauth-protected-resource`);
  const body = r.ok ? await r.json() : {};
  check("resource metadata names /mcp and this server", r.ok && body.resource === resource && body.authorization_servers?.[0] === site);
  const r2 = await fetch(`${site}/.well-known/oauth-protected-resource/mcp`);
  check("resource metadata also at the path-suffixed address", r2.ok && (await r2.json()).resource === resource);
  const r3 = await fetch(`${site}/.well-known/oauth-authorization-server`);
  const as = r3.ok ? await r3.json() : {};
  check(
    "authorization server metadata: issuer, S256, iss in responses",
    r3.ok &&
      as.issuer === site &&
      as.code_challenge_methods_supported?.includes("S256") &&
      as.authorization_response_iss_parameter_supported === true,
  );
}

{
  const r = await fetch(`${site}/mcp`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  const header = r.headers.get("www-authenticate") ?? "";
  check("a call with no token gets 401 pointing at the metadata", r.status === 401 && header.includes(`resource_metadata="${site}/.well-known/oauth-protected-resource"`));
  const r2 = await fetch(`${site}/mcp`, { method: "POST", headers: { Authorization: "Bearer nonsense", "Content-Type": "application/json" }, body: "{}" });
  check("a call with a made-up token gets 401", r2.status === 401);
}

async function register(uris) {
  const r = await fetch(`${site}/api/connector/oauth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_name: "Connector check", redirect_uris: uris }),
  });
  return [r.status, r.ok ? await r.json() : await r.json().catch(() => ({}))];
}

const CLAUDE = "https://claude.ai/api/mcp/auth_callback";
const [claudeStatus, claudeClient] = await register([CLAUDE]);
check("Claude's return address registers", claudeStatus === 201 && typeof claudeClient.client_id === "string");
check("ChatGPT's return address registers", (await register(["https://chatgpt.com/connector_platform_oauth_redirect"]))[0] === 201);
check("Claude Code's loopback address registers", (await register(["http://localhost:53682/callback"]))[0] === 201);
{
  const [status, body] = await register(["https://example.com/steal"]);
  check("any other return address is refused", status === 400 && body.error === "invalid_redirect_uri");
  const nullBody = await fetch(`${site}/api/connector/oauth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "null",
  });
  check("a registration that is not a JSON object is refused cleanly", nullBody.status === 400 && (await nullBody.json()).error === "invalid_client_metadata");
}

async function authorize(params) {
  const url = new URL(`${site}/api/connector/oauth/authorize`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  return fetch(url, { redirect: "manual" });
}

{
  const { challenge } = pkce();
  const good = {
    client_id: claudeClient.client_id,
    redirect_uri: CLAUDE,
    response_type: "code",
    code_challenge: challenge,
    code_challenge_method: "S256",
    state: "check-state",
    scope: "base",
    resource,
  };
  const unknown = await authorize({ ...good, client_id: "made-up" });
  check("authorize with an unknown client stops on a page, sending nothing back", unknown.status === 400);
  const back = (r) => (r.headers.get("location") ? new URL(r.headers.get("location")) : null);
  const noPkce = back(await authorize({ ...good, code_challenge: "" }));
  check(
    "authorize without PKCE goes back with invalid_request, iss and state",
    noPkce?.origin === "https://claude.ai" &&
      noPkce.searchParams.get("error") === "invalid_request" &&
      noPkce.searchParams.get("iss") === site &&
      noPkce.searchParams.get("state") === "check-state",
  );
  const plain = back(await authorize({ ...good, code_challenge_method: "plain" }));
  check("authorize with a plain PKCE challenge is refused", plain?.searchParams.get("error") === "invalid_request");
  const foreign = back(await authorize({ ...good, resource: "https://example.com/mcp" }));
  check("authorize for another server's resource is refused", foreign?.searchParams.get("error") === "invalid_target");
  const huge = back(await authorize({ ...good, state: "s".repeat(1025) }));
  check(
    "authorize with an oversized state is refused before any cookie is set",
    huge?.origin === "https://claude.ai" && huge.searchParams.get("error") === "invalid_request" && !huge.searchParams.get("state"),
  );
  const ok = await authorize(good);
  const toGitHub = back(ok);
  check(
    "a good authorize request goes to GitHub with the connector's callback",
    toGitHub?.origin === "https://github.com" &&
      toGitHub.searchParams.get("redirect_uri") === `${site}/api/connector/oauth/github-callback` &&
      (ok.headers.get("set-cookie") ?? "").includes("gtmb_connector_pending="),
  );
}

{
  const json = await fetch(`${site}/api/connector/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grant_type: "authorization_code", code: "x" }),
  });
  check("the token endpoint refuses JSON", json.status === 400 && (await json.json()).error === "invalid_request");
  const odd = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "password" }));
  check("the token endpoint refuses other grant types", (await odd.json()).error === "unsupported_grant_type");
  const fake = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code: "made-up", code_verifier: "x".repeat(43) }));
  check("a made-up code is refused", (await fake.json()).error === "invalid_grant");
}

// --- With the site's secret (a copy on this computer only) --------------------

const key = (purpose) => new Uint8Array(hkdfSync("sha256", secret, "gtm-base-connector", purpose, 32));
const sealAs = (purpose, body, seconds) =>
  new EncryptJWT({ b: body })
    .setProtectedHeader({ alg: "dir", enc: "A256GCM" })
    .setIssuedAt()
    .setExpirationTime(`${seconds}s`)
    .encrypt(key(purpose));

function grantFor(login, gh = "not-a-real-github-token") {
  const now = Date.now();
  return { gh, ghExp: now + 8 * 3600_000, ghRefresh: null, ghRefreshExp: null, login, team: false };
}

async function mcp(token, message, { session, protocol } = {}) {
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
  if (session) headers["Mcp-Session-Id"] = session;
  if (protocol) headers["MCP-Protocol-Version"] = protocol;
  // 2026-07-28 names the method (and a tool call's tool) in headers as well as the body.
  if (protocol === "2026-07-28") {
    headers["Mcp-Method"] = message.method;
    if (message.method === "tools/call") headers["Mcp-Name"] = message.params?.name;
  }
  const r = await fetch(`${site}/mcp`, { method: "POST", headers, body: JSON.stringify({ jsonrpc: "2.0", id: 1, ...message }) });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    const data = text.split("\n").find((line) => line.startsWith("data: "));
    body = data ? JSON.parse(data.slice(6)) : null;
  }
  return { status: r.status, headers: r.headers, body };
}

const toolText = (answer) => answer.body?.result?.content?.[0]?.text ?? JSON.stringify(answer.body?.error ?? answer.body);
const callTool = (token, name, args, conversation, options) =>
  mcp(token, { method: "tools/call", params: { name, arguments: args, ...(conversation ? { _meta: { "com.anthropic/session": conversation } } : {}) } }, { protocol: "2025-11-25", ...options });

if (secret) {
  const login = process.env.CHECK_LOGIN ?? "brandon-sellers13";
  const cid = claudeClient.client_id;

  // PKCE, single-use codes, refresh chains.
  const { verifier, challenge } = pkce();
  const jti = b64url(randomBytes(18));
  const code = await sealAs("code", { jti, cid, redirectUri: CLAUDE, challenge, resource, grant: grantFor(login) }, 120);
  const wrong = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code, code_verifier: pkce().verifier, client_id: cid, redirect_uri: CLAUDE }));
  check("a code with the wrong PKCE verifier is refused", (await wrong.json()).error === "invalid_grant");
  const [first, ms] = await timed(fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code, code_verifier: verifier, client_id: cid, redirect_uri: CLAUDE, resource })));
  const tokens = first.ok ? await first.json() : {};
  check("the code with its verifier gives tokens, well inside ten seconds", first.ok && !!tokens.access_token && !!tokens.refresh_token && ms < 10_000, `${ms} ms`);
  const again = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code, code_verifier: verifier, client_id: cid }));
  check("the same code a second time is refused", (await again.json()).error === "invalid_grant");
  const afterReuse = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: tokens.refresh_token ?? "", client_id: cid }));
  check("reusing the code ended the refresh chain it started", (await afterReuse.json()).error === "invalid_grant");

  const jti2 = b64url(randomBytes(18));
  const p2 = pkce();
  const code2 = await sealAs("code", { jti: jti2, cid, redirectUri: CLAUDE, challenge: p2.challenge, resource, grant: grantFor(login) }, 120);
  const t2 = await (await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code: code2, code_verifier: p2.verifier, client_id: cid }))).json();
  const r1 = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: t2.refresh_token, client_id: cid }));
  const t3 = r1.ok ? await r1.json() : {};
  check("a refresh token gives new tokens", r1.ok && !!t3.refresh_token && t3.refresh_token !== t2.refresh_token);
  const replay = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: t2.refresh_token, client_id: cid }));
  check("an old refresh token is refused", (await replay.json()).error === "invalid_grant");
  const newest = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: t3.refresh_token ?? "", client_id: cid }));
  check("and replaying it ended the chain, so the newest one stops too", (await newest.json()).error === "invalid_grant");

  // A chain whose refresh needs GitHub, given a refresh token GitHub refuses
  // outright: GitHub's own refusal ends the chain.
  async function startChain(grant) {
    const p = pkce();
    const id = b64url(randomBytes(18));
    const c = await sealAs("code", { jti: id, cid, redirectUri: CLAUDE, challenge: p.challenge, resource, grant }, 120);
    return (await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code: c, code_verifier: p.verifier }))).json();
  }
  const nearEnd = await startChain({ ...grantFor(login), ghExp: Date.now() + 5 * 60_000, ghRefresh: "not-a-real-refresh-token" });
  const refused = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: nearEnd.refresh_token ?? "" }));
  check("a refresh GitHub refuses outright is invalid_grant", (await refused.json()).error === "invalid_grant", `status ${refused.status}`);

  // A GitHub token that never expires is never renewed at GitHub, and keeps refreshing.
  const forever = await startChain({ ...grantFor(login), ghExp: null });
  const r2 = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "refresh_token", refresh_token: forever.refresh_token ?? "" }));
  const r2body = r2.ok ? await r2.json() : {};
  check("a GitHub token that never expires refreshes without asking GitHub, for a full hour", r2.ok && r2body.expires_in === 3600);

  // Cancelling on GitHub goes back to the product as access_denied.
  {
    const ghState = b64url(randomBytes(18));
    const pendingCookie = await sealAs(
      "pending",
      { cid, clientName: "Claude", redirectUri: CLAUDE, challenge: pkce().challenge, state: "cancel-state", resource, ghState },
      600,
    );
    const r = await fetch(`${site}/api/connector/oauth/github-callback?error=access_denied&state=${ghState}`, {
      redirect: "manual",
      headers: { Cookie: `gtmb_connector_pending=${pendingCookie}` },
    });
    const to = r.headers.get("location") ? new URL(r.headers.get("location")) : null;
    check(
      "cancelling on GitHub goes back to the product with access_denied, state and iss",
      to?.origin === "https://claude.ai" &&
        to.searchParams.get("error") === "access_denied" &&
        to.searchParams.get("state") === "cancel-state" &&
        to.searchParams.get("iss") === site &&
        (r.headers.get("set-cookie") ?? "").includes("gtmb_connector_pending=;"),
    );
  }

  // The consent page and its answer.
  {
    const p3 = pkce();
    const nonce = b64url(randomBytes(18));
    const consent = await sealAs(
      "consent",
      { cid, clientName: "Claude", redirectUri: CLAUDE, challenge: p3.challenge, state: "consent-state", resource, nonce, grant: grantFor(login) },
      600,
    );
    const cookie = `gtmb_connector_consent=${consent}`;
    const page = await fetch(`${site}/connect/consent?step=consent`, { headers: { Cookie: cookie } });
    const html = await page.text();
    check(
      "the consent page names the product, where the answer goes, and the account",
      page.ok && html.includes("Claude") && html.includes("claude.ai") && html.includes(login) && (page.headers.get("content-security-policy") ?? "").includes("frame-ancestors 'none'"),
    );
    const answer = (origin, decision, n = nonce) =>
      fetch(`${site}/api/connector/oauth/consent`, {
        method: "POST",
        redirect: "manual",
        headers: { Cookie: cookie, Origin: origin, "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ nonce: n, decision }).toString(),
      });
    check("an answer posted from another site is refused", (await answer("https://example.com", "allow")).status === 403);
    check("an answer without the page's one-time value is refused", (await answer(site, "allow", "wrong")).status === 400);
    const cancel = new URL((await answer(site, "cancel")).headers.get("location") ?? "http://x");
    check("Cancel goes back with access_denied and iss", cancel.searchParams.get("error") === "access_denied" && cancel.searchParams.get("iss") === site);
    const allowed = new URL((await answer(site, "allow")).headers.get("location") ?? "http://x");
    const issued = allowed.searchParams.get("code");
    check(
      "Allow goes back to the product with a code, iss and state",
      allowed.origin === "https://claude.ai" && !!issued && allowed.searchParams.get("iss") === site && allowed.searchParams.get("state") === "consent-state",
    );
    const exchanged = await fetch(`${site}/api/connector/oauth/token`, form({ grant_type: "authorization_code", code: issued ?? "", code_verifier: p3.verifier, client_id: cid, redirect_uri: CLAUDE }));
    check("that code exchanges for tokens", exchanged.ok);
  }

  // The endpoint's own checks.
  const access = (body, seconds = 600) => sealAs("access", body, seconds);
  const foreign = await access({ aud: "https://example.com/mcp", cid, chain: "x", grant: { gh: "x", login, team: false } });
  check("a token made for another server is refused", (await mcp(foreign, { method: "ping" })).status === 401);
  const stranger = await access({ aud: resource, cid, chain: "x", grant: { gh: "x", login: "not-on-the-list-zz9", team: false } });
  check("a login not on the allowlist is refused on every call", (await mcp(stranger, { method: "ping" })).status === 401);

  const token = await access({ aud: resource, cid, chain: "x", grant: { gh: "not-a-real-github-token", login, team: false } });
  const init = await mcp(token, {
    method: "initialize",
    params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "connector-check", version: "1" } },
  });
  check(
    "a 2025-11-25 initialize is answered, with a session id",
    init.status === 200 && !!init.body?.result?.serverInfo && !!init.headers.get("mcp-session-id"),
    init.body?.result?.protocolVersion,
  );
  const discover = await mcp(
    token,
    {
      method: "server/discover",
      params: { _meta: { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientInfo": { name: "connector-check", version: "1" }, "io.modelcontextprotocol/clientCapabilities": {} } },
    },
    { protocol: "2026-07-28" },
  );
  check("a 2026-07-28 server/discover is answered", discover.status === 200 && !!discover.body?.result, JSON.stringify(discover.body).slice(0, 160));
  const tools = await mcp(token, { method: "tools/list" }, { protocol: "2025-11-25" });
  const names = (tools.body?.result?.tools ?? []).map((t) => t.name).sort().join(",");
  check(
    "the tools are list_bases, list_documents, propose_change, propose_fix, read_document and use_skill",
    names === "list_bases,list_documents,propose_change,propose_fix,read_document,use_skill",
    names,
  );
  const skillTool = (tools.body?.result?.tools ?? []).find((t) => t.name === "use_skill");
  check(
    "use_skill is titled Use a company skill, read only, and says how to find the skills",
    skillTool?.title === "Use a company skill" && skillTool?.annotations?.readOnlyHint === true && /list_documents names them/.test(skillTool?.description ?? ""),
    skillTool?.description?.slice(0, 120),
  );
  check(
    "the instructions say how skills are used, with no base's skills when none can be tied to the call",
    /call use_skill before doing the work/.test(init.body?.result?.instructions ?? ""),
  );

  const noConversation = await callTool(token, "list_bases", {}, null);
  check("a call with no conversation id is refused", /could not tell which conversation/.test(toolText(noConversation)));
  const noBase = await callTool(token, "read_document", { base: "", path: "context/map.md" }, "v1.check-no-base");
  check("a call that names no base is refused", /name the base as owner\/repo/.test(toolText(noBase)));
  const refusedByGitHub = await callTool(token, "read_document", { base: "someone/somebase", path: "context/map.md" }, "v1.check-github");
  check("a GitHub token GitHub refuses turns into 401, so the product signs in again", refusedByGitHub.status === 401, `status ${refusedByGitHub.status}`);

  // Under 2026-07-28 the library lifts its own envelope out of _meta; the
  // product's conversation id must still reach the tool.
  const envelope = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": { name: "connector-check", version: "1" },
    "io.modelcontextprotocol/clientCapabilities": {},
  };
  const modern = (meta) =>
    mcp(
      token,
      { method: "tools/call", params: { name: "read_document", arguments: { base: "someone/somebase", path: "context/map.md" }, _meta: { ...envelope, ...meta } } },
      { protocol: "2026-07-28" },
    );
  const modernNone = await modern({});
  check("under 2026-07-28, a call with no conversation id is refused", /could not tell which conversation/.test(toolText(modernNone)), `status ${modernNone.status}`);
  const modernWith = await modern({ "openai/session": "check-openai-session" });
  check("under 2026-07-28, the product's conversation id reaches the tool (it went on to GitHub)", modernWith.status === 401, `status ${modernWith.status}`);

  if (github && baseA && baseB) {
    const real = await access({ aud: resource, cid, chain: "x", grant: { gh: github, login, team: false } });
    const conv = (name) => `v1.check-${name}-${randomBytes(6).toString("hex")}`;
    const one = conv("one");
    const a1 = await callTool(real, "read_document", { base: baseA, path: "context/map.md" }, one);
    check("the first base a conversation reads binds it", /now uses the base/.test(toolText(a1)) && !a1.body?.result?.isError, toolText(a1).slice(0, 80));
    const b1 = await callTool(real, "read_document", { base: baseB, path: "context/map.md" }, one);
    const refusal = toolText(b1);
    check("another base in the same conversation is refused, naming only the first", /uses the base/.test(refusal) && refusal.includes(baseA) && !refusal.includes(baseB));
    const l1 = await callTool(real, "list_bases", {}, one);
    check("list_bases in a bound conversation shows only its base", toolText(l1).trim() === `This conversation uses the base ${baseA}.`);
    const b2 = await callTool(real, "read_document", { base: baseB, path: "context/map.md" }, conv("two"));
    check("a new conversation can use the other base", /now uses the base/.test(toolText(b2)));

    const race = conv("race");
    const [x, y] = await Promise.all([
      callTool(real, "read_document", { base: baseA, path: "context/map.md" }, race),
      callTool(real, "read_document", { base: baseB, path: "context/map.md" }, race),
    ]);
    // A winner is a real success: HTTP 200, an MCP result, and no error. The
    // other call must be the binding refusal, not some other failure.
    const won = (r) => r.status === 200 && !!r.body?.result && r.body.result.isError === false;
    const refusedForBinding = (r) =>
      r.status === 200 && r.body?.result?.isError === true && /a conversation can use only one base/.test(toolText(r));
    const wins = [x, y].filter(won).length;
    const other = won(x) ? y : x;
    check(
      "two first calls at once for different bases: exactly one binds, the other is refused for the binding",
      wins === 1 && refusedForBinding(other),
      `${wins} bound`,
    );

    const missing = await callTool(real, "read_document", { base: baseA, path: "context/no-such-document.md" }, one);
    check("a document that does not exist points to the map", /no document at/i.test(toolText(missing)));

    const session = init.headers.get("mcp-session-id");
    const s1 = await callTool(real, "read_document", { base: baseA, path: "context/map.md" }, null, { session });
    const s2 = await callTool(real, "read_document", { base: baseB, path: "context/map.md" }, null, { session });
    check("without a conversation id, the minted session id binds instead", /now uses the base/.test(toolText(s1)) && /uses the base/.test(toolText(s2)) && toolText(s2).includes(baseA));
  } else {
    console.log("skip  the one-base checks (set GITHUB_TOKEN, BASE_A and BASE_B)");
  }

  // C3: a base holding an approved drift grade.
  const skillBase = process.env.SKILL_BASE;
  if (github && skillBase) {
    const real = await access({ aud: resource, cid, chain: "x", grant: { gh: github, login, team: false } });
    const conv = `v1.check-skills-${randomBytes(6).toString("hex")}`;
    const listed = toolText(await callTool(real, "list_documents", { base: skillBase }, conv));
    check("list_documents ends with the approved skills, drift grade among them", /approved skills, each with when to use it:\n(?:.*\n)*- drift-grade: /.test(listed), listed.slice(-300));
    const [served, ms] = await timed(callTool(real, "use_skill", { base: skillBase, skill: "drift-grade" }, conv));
    const text = toolText(served);
    const flaggedFirst = /a document it reads needs a choice from you/.test(text);
    check(
      "use_skill serves drift grade's approved instructions with its documents, or the flag first",
      !served.body?.result?.isError &&
        (flaggedFirst ||
          (text.includes("The approved instructions for drift-grade follow.") &&
            text.includes("[for the assistant] instructions=skills/drift-grade/SKILL.md") &&
            text.includes("[for the assistant] document=standards/drift-grade.md") &&
            !text.includes("/examples/"))),
      `${ms} ms; ${text.slice(0, 200)}`,
    );
    const unknown = toolText(await callTool(real, "use_skill", { base: skillBase, skill: "no-such-skill" }, conv));
    check("a skill the base does not hold is refused, naming the ones it does", /holds no skill by that name/.test(unknown) && /- drift-grade: /.test(unknown));
    const listing = await mcp(real, { method: "tools/list", params: { _meta: { "com.anthropic/session": conv } } }, { protocol: "2025-11-25" });
    const description = (listing.body?.result?.tools ?? []).find((t) => t.name === "use_skill")?.description ?? "";
    check("once the conversation uses that base, the tool list carries its skill index", description.includes(`The base ${skillBase} holds these approved skills`) && description.includes("- drift-grade: "), description.slice(-200));
  } else {
    console.log("skip  the skill checks (set GITHUB_TOKEN and SKILL_BASE, a base holding an approved drift grade)");
  }
} else {
  console.log("skip  the token and protocol checks (set CONNECTOR_SECRET, for a copy on this computer)");
}

console.log(`\n${results.length - failed} of ${results.length} checks passed.`);
process.exit(failed ? 1 : 0);
