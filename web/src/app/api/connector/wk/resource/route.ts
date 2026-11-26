import { SCOPE, connectorEnabled, issuer, notFound, resourceUrl } from "@/lib/connector/config";

// Protected resource metadata (RFC 9728), served at
// /.well-known/oauth-protected-resource and /.well-known/oauth-protected-resource/mcp.
export function GET() {
  if (!connectorEnabled()) return notFound();
  return Response.json({
    resource: resourceUrl(),
    authorization_servers: [issuer()],
    scopes_supported: [SCOPE],
    bearer_methods_supported: ["header"],
    resource_name: "GTM Base",
  });
}
