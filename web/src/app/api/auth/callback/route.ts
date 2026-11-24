import { NextRequest, NextResponse } from "next/server";
import { allowedLogins, appUrl, githubApp } from "@/lib/config";
import { exchangeCode, getUser, getVerifiedEmails } from "@/lib/github";
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
    if (!allowedLogins().has(user.login.toLowerCase())) {
      response = NextResponse.redirect(home("invite-only"));
    } else {
      const sealed = await sealSession({
        login: user.login,
        name: user.name,
        avatarUrl: user.avatar_url,
        emails: await getVerifiedEmails(token),
        token,
        expiresAt: Date.now() + expiresInSeconds * 1000,
      });
      response = NextResponse.redirect(home());
      response.cookies.set(SESSION_COOKIE, sealed, sessionCookieOptions);
    }
  } catch {
    response = NextResponse.redirect(home("sign-in-failed"));
  }
  response.cookies.delete("gtmb_oauth_state");
  return response;
}
