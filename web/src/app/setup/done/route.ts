import { NextRequest, NextResponse } from "next/server";
import { appUrl, githubApp, isDevelopment } from "@/lib/config";
import { LIVE_ENV_FILE, LOCAL_ENV_FILE, newSessionSecret, writeEnv } from "@/lib/envfile";
import { convertManifest } from "@/lib/github";
import { sameState } from "@/lib/oauthState";

// Development only. GitHub sends the person back here after they create the app,
// with a one-time code that trades for the app's credentials. The credentials are
// written to web/.env.local (this computer's app) or web/.env.live (the live
// address's app) and are never shown on screen or logged.
export async function GET(request: NextRequest) {
  if (!isDevelopment()) return new NextResponse(null, { status: 404 });

  const target = request.cookies.get("gtmb_setup_target")?.value ?? "local";
  const liveUrl = target.startsWith("live ") ? target.slice(5) : null;
  if (!liveUrl && githubApp()) return new NextResponse(null, { status: 404 });

  const code = request.nextUrl.searchParams.get("code");
  const done = new URL("/setup", appUrl());
  if (!code || !sameState(request.cookies.get("gtmb_setup_state")?.value, request.nextUrl.searchParams.get("state"))) {
    done.searchParams.set("notice", "setup-expired");
    return NextResponse.redirect(done);
  }

  try {
    const app = await convertManifest(code);
    const owner = (app as unknown as { owner?: { login?: string } }).owner?.login ?? "";
    const credentials = {
      GITHUB_APP_ID: String(app.id),
      GITHUB_APP_SLUG: app.slug,
      GITHUB_APP_CLIENT_ID: app.client_id,
      GITHUB_APP_CLIENT_SECRET: app.client_secret,
      GITHUB_APP_PRIVATE_KEY: app.pem,
    };
    if (liveUrl) {
      // The live site gets its own session secret, never this computer's.
      await writeEnv(LIVE_ENV_FILE, {
        APP_URL: liveUrl,
        ...credentials,
        SESSION_SECRET: newSessionSecret(),
        ALLOWED_GITHUB_LOGINS: owner,
      });
      done.searchParams.set("notice", "live-created");
    } else {
      await writeEnv(LOCAL_ENV_FILE, {
        APP_URL: appUrl(),
        ...credentials,
        ...(process.env.SESSION_SECRET ? {} : { SESSION_SECRET: newSessionSecret() }),
        ...(process.env.ALLOWED_GITHUB_LOGINS ? {} : { ALLOWED_GITHUB_LOGINS: owner }),
      });
      done.searchParams.set("notice", "created");
    }
  } catch {
    done.searchParams.set("notice", "setup-failed");
  }
  const response = NextResponse.redirect(done);
  response.cookies.delete("gtmb_setup_state");
  response.cookies.delete("gtmb_setup_target");
  return response;
}
