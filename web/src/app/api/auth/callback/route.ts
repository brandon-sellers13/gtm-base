import { NextRequest, NextResponse } from "next/server";
import { allowedLogins, appUrl, githubApp } from "@/lib/config";
import { exchangeCode, getUser, getVerifiedEmails, listInstallations } from "@/lib/github";
import { reachesAllowedBase } from "@/lib/team";
import { sameState } from "@/lib/oauthState";
import { SESSION_COOKIE, sealSession, sessionCookieOptions } from "@/lib/session";

function home(notice?: string) {
  const url = new URL("/", appUrl());
  if (notice) url.searchParams.set("notice", notice);
  return url;
}

export async function GET(request: NextRequest) {
  const app = githubApp();
  if (!app) return NextResponse.redirect(home());

  const params = request.nextUrl.searchParams;
  const code = params.get("code");
  if (!code || !sameState(request.cookies.get("gtmb_oauth_state")?.value, params.get("state"))) {
    // Installing or updating the app from GitHub's own pages returns here without
    // our state. That is not a sign-in, so nobody is signed in by it; the person
    // just goes home, where an existing session still works.
    if (params.get("setup_action")) return NextResponse.redirect(home("installed"));
    return NextResponse.redirect(home("sign-in-expired"));
  }

  let response: NextResponse;
  try {
    const { token, expiresInSeconds } = await exchangeCode(
      code,
      app.clientId,
      app.clientSecret,
      `${appUrl()}/api/auth/callback`,
    );
    const user = await getUser(token);
    const allowed = allowedLogins();
    const listed = allowed.has(user.login.toLowerCase());
    const team = !listed && (await reachesAllowedBase(token, await listInstallations(token), allowed));
    if (!listed && !team) {
      response = NextResponse.redirect(home("invite-only"));
    } else {
      const sealed = await sealSession({
        login: user.login,
        name: user.name,
        avatarUrl: user.avatar_url,
        emails: await getVerifiedEmails(token),
        token,
        expiresAt: Date.now() + expiresInSeconds * 1000,
        ...(team ? { team: true } : {}),
      });
      // A notice the page ignores: on Netlify, a redirect with no query of its own
      // gets GitHub's code and state carried onto it.
      response = NextResponse.redirect(home("signed-in"));
      response.cookies.set(SESSION_COOKIE, sealed, sessionCookieOptions);
    }
  } catch {
    response = NextResponse.redirect(home("sign-in-failed"));
  }
  response.cookies.delete("gtmb_oauth_state");
  return response;
}
