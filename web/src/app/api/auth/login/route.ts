import { NextRequest, NextResponse } from "next/server";
import { appUrl, githubApp } from "@/lib/config";
import { newState, stateCookieOptions } from "@/lib/oauthState";

// Starts sign-in with GitHub. With ?install=1 it starts installing the app on an
// account instead; GitHub signs the person in at the end of either path.
export async function GET(request: NextRequest) {
  const app = githubApp();
  if (!app) return NextResponse.redirect(new URL("/", appUrl()));

  const state = newState();
  const install = request.nextUrl.searchParams.get("install") === "1";
  const target = install
    ? new URL(`https://github.com/apps/${encodeURIComponent(app.slug)}/installations/new`)
    : new URL("https://github.com/login/oauth/authorize");
  if (!install) {
    target.searchParams.set("client_id", app.clientId);
    target.searchParams.set("redirect_uri", `${appUrl()}/api/auth/callback`);
  }
  target.searchParams.set("state", state);

  const response = NextResponse.redirect(target);
  response.cookies.set("gtmb_oauth_state", state, stateCookieOptions);
  return response;
}
