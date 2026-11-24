import { NextRequest, NextResponse } from "next/server";
import { appUrl, githubApp, isDevelopment } from "@/lib/config";
import { newSessionSecret, writeEnv } from "@/lib/envfile";
import { convertManifest } from "@/lib/github";
import { sameState } from "@/lib/oauthState";

// Development only. GitHub sends the person back here after they create the app,
// with a one-time code that trades for the app's credentials. The credentials are
// written to web/.env.local and are never shown on screen or logged.
export async function GET(request: NextRequest) {
  if (!isDevelopment() || githubApp()) return new NextResponse(null, { status: 404 });

  const code = request.nextUrl.searchParams.get("code");
  const done = new URL("/setup", appUrl());
  if (!code || !sameState(request.cookies.get("gtmb_setup_state")?.value, request.nextUrl.searchParams.get("state"))) {
    done.searchParams.set("notice", "setup-expired");
    return NextResponse.redirect(done);
  }

  try {
    const app = await convertManifest(code);
    const owner = (app as unknown as { owner?: { login?: string } }).owner?.login ?? "";
    await writeEnv({
      APP_URL: appUrl(),
      GITHUB_APP_ID: String(app.id),
      GITHUB_APP_SLUG: app.slug,
      GITHUB_APP_CLIENT_ID: app.client_id,
      GITHUB_APP_CLIENT_SECRET: app.client_secret,
      GITHUB_APP_PRIVATE_KEY: app.pem,
      ...(process.env.SESSION_SECRET ? {} : { SESSION_SECRET: newSessionSecret() }),
      ...(process.env.ALLOWED_GITHUB_LOGINS ? {} : { ALLOWED_GITHUB_LOGINS: owner }),
    });
    done.searchParams.set("notice", "created");
  } catch {
    done.searchParams.set("notice", "setup-failed");
  }
  const response = NextResponse.redirect(done);
  response.cookies.delete("gtmb_setup_state");
  return response;
}
