import { type Client, returnAddressAllowed } from "@/lib/connector/clients";
import { connectorEnabled, notFound } from "@/lib/connector/config";
import { seal } from "@/lib/connector/seal";

// Dynamic client registration (RFC 7591). The client id is the sealed list of
// return addresses and the name the product gave, so registering stores nothing.
export async function POST(request: Request) {
  if (!connectorEnabled()) return notFound();
  let body: { redirect_uris?: unknown; client_name?: unknown };
  try {
    body = (await request.json()) as typeof body;
  } catch {
    return refuse("invalid_client_metadata", "The registration must be JSON.");
  }
  const uris = Array.isArray(body.redirect_uris)
    ? body.redirect_uris.filter((u): u is string => typeof u === "string")
    : [];
  if (!uris.length || uris.length > 5 || !uris.every(returnAddressAllowed)) {
    return refuse("invalid_redirect_uri", "GTM Base accepts only Claude, ChatGPT and Claude Code's return addresses.");
  }
  const name =
    typeof body.client_name === "string" && body.client_name.trim()
      ? body.client_name.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, 60)
      : "An unnamed program";
  const clientId = await seal("client", { r: uris, n: name } satisfies Client, 60 * 60 * 24 * 365);
  return Response.json(
    {
      client_id: clientId,
      client_name: name,
      redirect_uris: uris,
      token_endpoint_auth_method: "none",
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
      client_id_issued_at: Math.floor(Date.now() / 1000),
    },
    { status: 201, headers: { "Cache-Control": "no-store" } },
  );
}

const refuse = (error: string, description: string) =>
  Response.json({ error, error_description: description }, { status: 400, headers: { "Cache-Control": "no-store" } });
