import { NextRequest, NextResponse } from "next/server";
import { signInDecision } from "@/lib/access";
import { appUrl, githubApp } from "@/lib/config";
import { connectorEnabled, githubCallbackUrl, notFound } from "@/lib/connector/config";
import type { Grant } from "@/lib/connector/grants";
import { open, randomId, seal } from "@/lib/connector/seal";
import {
  CONSENT_COOKIE,
  type Consent,
  PENDING_COOKIE,
  type Pending,
  SIGNIN_SECONDS,
  backToProduct,
  signinCookieOptions,
  stoppedPage,
} from "@/lib/connector/signin";
import { exchangeCodeForTokens, getUser } from "@/lib/github";
import { sameState } from "@/lib/oauthState";

// GitHub sends the person back here. The server exchanges GitHub's code itself,
// keeping GitHub's refresh token so the connector lasts past GitHub's eight-hour
// tokens, applies the web app's invite rule, and shows the consent page.
export async function GET(request: NextRequest) {
  if (!connectorEnabled()) return notFound();
  const app = githubApp();
  const pending = await open<Pending>("pending", request.cookies.get(PENDING_COOKIE)?.value);
  const p = request.nextUrl.searchParams;
  const code = p.get("code");
  if (!app || !pending || !sameState(pending.ghState, p.get("state"))) {
    return stoppedPage("This sign-in took too long or was started somewhere else. Start again from Claude or ChatGPT.");
  }
  // The person cancelled on GitHub (or GitHub refused): tell the product so it
  // stops waiting, and clear the sign-in in progress.
  if (!code) {
    const cancelled = backToProduct(pending.redirectUri, pending.state, { error: "access_denied" });
    cancelled.cookies.delete(PENDING_COOKIE);
    return cancelled;
  }

  let response: NextResponse;
  try {
    const gh = await exchangeCodeForTokens(code, app.clientId, app.clientSecret, githubCallbackUrl());
    const user = await getUser(gh.token);
    const { allowed, team } = await signInDecision(gh.token, user.login);
    if (!allowed) {
      response = backToProduct(pending.redirectUri, pending.state, {
        error: "access_denied",
        error_description: "GTM Base is invite-only for now, and this GitHub account is not on the list yet.",
      });
    } else {
      const now = Date.now();
      const grant: Grant = {
        gh: gh.token,
        ghExp: gh.expiresInSeconds === null ? null : now + gh.expiresInSeconds * 1000,
        ghRefresh: gh.refreshToken,
        ghRefreshExp: gh.refreshExpiresInSeconds ? now + gh.refreshExpiresInSeconds * 1000 : null,
        login: user.login,
        team,
      };
      const { ghState: _unused, ...rest } = pending;
      void _unused;
      const consent: Consent = { ...rest, nonce: randomId(), grant };
      // A query of its own: on Netlify, a redirect without one gets GitHub's
      // code and state carried onto it.
      response = NextResponse.redirect(new URL("/connect/consent?step=consent", appUrl()), 303);
      response.cookies.set(CONSENT_COOKIE, await seal("consent", consent, SIGNIN_SECONDS), signinCookieOptions);
    }
  } catch {
    response = backToProduct(pending.redirectUri, pending.state, { error: "server_error" });
  }
  response.cookies.delete(PENDING_COOKIE);
  return response;
}
