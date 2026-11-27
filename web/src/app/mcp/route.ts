import { createMcpHandler } from "@modelcontextprotocol/server";
import { stillAllowed } from "@/lib/access";
import { SCOPE, connectorEnabled, notFound, resourceMetadataUrl, resourceUrl } from "@/lib/connector/config";
import { openAccess } from "@/lib/connector/grants";
import { open, randomId, seal } from "@/lib/connector/seal";
import { type CallFacts, connectorServer } from "@/lib/connector/tools";

// The GTM Base connector's MCP endpoint, on the official MCP library (version
// two). It answers 2026-07-28 clients (`server/discover`) and, statelessly,
// 2025-era clients (`initialize`). Nothing is held between requests. The
// instructions and the tool list are the same for every person and every
// base, so nothing from one base can reach a listing another conversation keeps.

const handler = createMcpHandler(() => connectorServer(), { responseMode: "json" });

const MAX_BODY = 1024 * 1024;
const SESSION_SECONDS = 24 * 60 * 60;

// The same answer for every sign-in problem, so the product signs in again.
function unauthorized(): Response {
  return Response.json(
    { error: "invalid_token" },
    {
      status: 401,
      headers: {
        "WWW-Authenticate": `Bearer resource_metadata="${resourceMetadataUrl()}", scope="${SCOPE}"`,
        "Cache-Control": "no-store",
      },
    },
  );
}

async function serve(request: Request): Promise<Response> {
  if (!connectorEnabled()) return notFound();
  const bearer = request.headers.get("authorization")?.match(/^Bearer ([^\s]+)$/i)?.[1];
  const access = await openAccess(bearer);
  if (!bearer || !access || access.aud !== resourceUrl() || !stillAllowed(access.grant.login, access.grant.team)) {
    return unauthorized();
  }

  let parsedBody: unknown;
  if (request.method === "POST") {
    const raw = await request.text();
    if (raw.length > MAX_BODY) return Response.json({ error: "too_large" }, { status: 413 });
    try {
      parsedBody = JSON.parse(raw);
    } catch {
      return Response.json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, { status: 400 });
    }
  }

  // 2025-11-25 clients: the session id this server minted at `initialize`, the
  // fallback conversation key when a product sends no conversation id of its own.
  const session = await open<{ id: string }>("session", request.headers.get("mcp-session-id"));
  const facts: CallFacts = { access, sessionId: session?.id ?? null, githubRefused: false };

  const answer = await handler.fetch(request, {
    parsedBody,
    authInfo: {
      token: bearer,
      clientId: access.cid,
      scopes: [SCOPE],
      resource: new URL(resourceUrl()),
      extra: { facts },
    },
  });
  // 2025-era answers can come back as a stream that ends only when the tool has
  // finished, so the whole answer is read before deciding. Nothing here streams
  // for long: every tool answers once.
  const body = await answer.arrayBuffer();
  if (facts.githubRefused) return unauthorized();

  const headers = new Headers(answer.headers);
  const isInitialize =
    !!parsedBody && typeof parsedBody === "object" && (parsedBody as { method?: unknown }).method === "initialize";
  if (isInitialize && answer.ok) headers.set("Mcp-Session-Id", await seal("session", { id: randomId() }, SESSION_SECONDS));
  return new Response(body, { status: answer.status, statusText: answer.statusText, headers });
}

export const POST = serve;
export const GET = serve;
export const DELETE = serve;
