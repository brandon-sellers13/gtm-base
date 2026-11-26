import { NextRequest, NextResponse } from "next/server";
import { githubApp } from "@/lib/config";
import type { Client } from "@/lib/connector/clients";
import { SCOPE, connectorEnabled, githubCallbackUrl, notFound, resourceUrl } from "@/lib/connector/config";
import { open, seal } from "@/lib/connector/seal";
import {
  PENDING_COOKIE,
  type Pending,
  SIGNIN_SECONDS,
  backToProduct,
  signinCookieOptions,
  stoppedPage,
} from "@/lib/connector/signin";
import { newState } from "@/lib/oauthState";

// Starts a product's sign-in: checks the request, keeps it in a short sealed
// cookie, and sends the person to GitHub.
export async function GET(request: NextRequest) {
  if (!connectorEnabled()) return notFound();
  const p = request.nextUrl.searchParams;
  const cid = p.get("client_id");
  const redirectUri = p.get("redirect_uri") ?? "";
  const client = await open<Client>("client", cid);
  // Without a known client and one of its own return addresses, nothing may be
  // sent anywhere: the person sees the problem here instead.
  if (!cid || !client || !client.r.includes(redirectUri)) {
    return stoppedPage("This sign-in did not come from a product registered with GTM Base. Start again from Claude or ChatGPT.");
  }
  const state = p.get("state");
  const fail = (error: string) => backToProduct(redirectUri, state, { error });

  if (p.get("response_type") !== "code") return fail("unsupported_response_type");
  const challenge = p.get("code_challenge");
  if (!challenge || p.get("code_challenge_method") !== "S256" || !/^[A-Za-z0-9_-]{43,128}$/.test(challenge)) {
    return fail("invalid_request");
  }
  const resource = p.get("resource");
  if (resource && resource.replace(/\/+$/, "") !== resourceUrl()) return fail("invalid_target");
  const scope = p.get("scope");
  if (scope && !scope.split(" ").every((s) => s === SCOPE)) return fail("invalid_scope");

  const app = githubApp();
  if (!app) return fail("server_error");

  const ghState = newState();
  const pending: Pending = { cid, clientName: client.n, redirectUri, challenge, state, resource, ghState };
  const target = new URL("https://github.com/login/oauth/authorize");
  target.searchParams.set("client_id", app.clientId);
  target.searchParams.set("redirect_uri", githubCallbackUrl());
  target.searchParams.set("state", ghState);
  const response = NextResponse.redirect(target);
  response.cookies.set(PENDING_COOKIE, await seal("pending", pending, SIGNIN_SECONDS), signinCookieOptions);
  return response;
}
