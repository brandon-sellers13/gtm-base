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
  // Styled inline from the design tokens in src/app/globals.css: the page's
  // Content-Security-Policy allows inline styles and nothing else.
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GTM Base</title><body style="margin:0;background:#faf9f6;color:#151515;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:17px;line-height:1.6"><div style="height:60px;display:flex;align-items:center;gap:10px;padding:0 16px;border-bottom:1.5px solid #151515;font-weight:800;letter-spacing:-0.03em"><svg width="30" height="30" viewBox="0 0 120 120" aria-hidden="true"><rect x="34" y="6" width="80" height="80" fill="#dfe6fb" stroke="#151515" stroke-width="7"/><rect x="20" y="20" width="80" height="80" fill="#9db0ee" stroke="#151515" stroke-width="7"/><rect x="6" y="34" width="80" height="80" fill="#3d63dd" stroke="#151515" stroke-width="7"/></svg>GTM Base</div><main style="max-width:560px;margin:48px auto;padding:0 16px"><p style="margin:0;padding:24px;background:#fff;border:1.5px solid #151515;box-shadow:4px 4px 0 #151515">${message
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")}</p></main></body>`;
  return new Response(html, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
    },
  });
}
