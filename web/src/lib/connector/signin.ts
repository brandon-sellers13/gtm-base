import "server-only";
import { NextResponse } from "next/server";
import { isDevelopment } from "../config";
import { issuer } from "./config";
import type { Grant } from "./grants";

// The sign-in in progress, carried between the product, GitHub and the consent
// page in short sealed cookies.

export const PENDING_COOKIE = "gtmb_connector_pending";
export const CONSENT_COOKIE = "gtmb_connector_consent";
export const SIGNIN_SECONDS = 10 * 60;

export type Pending = {
  cid: string;
  clientName: string;
  redirectUri: string;
  challenge: string;
  state: string | null;
  resource: string | null;
  ghState: string;
};

export type Consent = Omit<Pending, "ghState"> & { nonce: string; grant: Grant };

export const signinCookieOptions = {
  httpOnly: true,
  secure: !isDevelopment(),
  sameSite: "lax" as const,
  path: "/",
  maxAge: SIGNIN_SECONDS,
};

// Sends the person back to the product, always naming this server (RFC 9207),
// with the product's own state.
export function backToProduct(
  redirectUri: string,
  state: string | null,
  values: Record<string, string>,
  status: 302 | 303 = 302,
): NextResponse {
  const back = new URL(redirectUri);
  for (const [name, value] of Object.entries(values)) back.searchParams.set(name, value);
  back.searchParams.set("iss", issuer());
  if (state) back.searchParams.set("state", state);
  return NextResponse.redirect(back, status);
}

// A plain page for a sign-in that cannot go back to a product.
export function stoppedPage(message: string, status = 400): Response {
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GTM Base</title><body style="font-family:system-ui,sans-serif;max-width:36rem;margin:4rem auto;padding:0 1rem;line-height:1.5"><p>${message
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")}</p></body>`;
  return new Response(html, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
    },
  });
}
