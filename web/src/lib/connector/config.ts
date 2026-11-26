import "server-only";
import { createHmac, hkdfSync } from "node:crypto";
import { appUrl } from "../config";

// The connector's settings. Every address it names (the issuer, the resource,
// each endpoint) is built from APP_URL, never from request headers, so the
// `iss` value, the metadata and each token's audience always agree.

// The connector answers 404 everywhere unless it is turned on for the site.
export const connectorEnabled = () => process.env.CONNECTOR_ENABLED === "1";

export const issuer = () => appUrl();
export const resourceUrl = () => `${appUrl()}/mcp`;
export const resourceMetadataUrl = () => `${appUrl()}/.well-known/oauth-protected-resource`;
export const githubCallbackUrl = () => `${appUrl()}/api/connector/oauth/github-callback`;
export const SCOPE = "base";

// A secret of its own, apart from the web app's SESSION_SECRET: changing it
// ends every connector sign-in at once and leaves the web app's alone.
function connectorSecret(): Buffer {
  const raw = process.env.CONNECTOR_SECRET;
  if (!raw) throw new Error("CONNECTOR_SECRET is not set.");
  const bytes = Buffer.from(raw, "base64");
  if (bytes.length !== 32) throw new Error("CONNECTOR_SECRET must be 32 bytes, base64 encoded.");
  return bytes;
}

export type KeyPurpose = "client" | "pending" | "consent" | "code" | "access" | "refresh" | "session" | "binding";

// One key per kind of value, so a value made for one purpose never opens as another.
export function connectorKey(purpose: KeyPurpose): Uint8Array {
  return new Uint8Array(hkdfSync("sha256", connectorSecret(), "gtm-base-connector", purpose, 32));
}

export function keyedHash(purpose: KeyPurpose, value: string): string {
  return createHmac("sha256", connectorKey(purpose)).update(value).digest("hex");
}

export function notFound(): Response {
  return new Response("Not found.", { status: 404 });
}
