import { SCOPE, connectorEnabled, issuer, notFound } from "@/lib/connector/config";

// Authorization server metadata (RFC 8414), served at
// /.well-known/oauth-authorization-server.
export function GET() {
  if (!connectorEnabled()) return notFound();
  const base = issuer();
  return Response.json({
    issuer: base,
    authorization_endpoint: `${base}/api/connector/oauth/authorize`,
    token_endpoint: `${base}/api/connector/oauth/token`,
    registration_endpoint: `${base}/api/connector/oauth/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    code_challenge_methods_supported: ["S256"],
    token_endpoint_auth_methods_supported: ["none"],
    scopes_supported: [SCOPE],
    authorization_response_iss_parameter_supported: true,
  });
}
