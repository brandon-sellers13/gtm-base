import { NextRequest, NextResponse } from "next/server";
import { appUrl, githubApp, isDevelopment } from "@/lib/config";
import { buildManifest } from "@/lib/manifest";
import { newState, stateCookieOptions } from "@/lib/oauthState";

// Development only. Hands the app's registration to GitHub, which shows the
// person a "Create GitHub App" page; nothing is created until they click it.
// target=local registers the app this computer signs in with; target=live
// registers a separate app for the live address, whose settings are saved to
// web/.env.live for sending to the host.
export async function POST(request: NextRequest) {
  if (!isDevelopment()) return new NextResponse(null, { status: 404 });
  // Only this app's own setup page may start this; a page on another site may not.
  if (request.headers.get("origin") !== appUrl()) return new NextResponse(null, { status: 403 });

  const form = await request.formData();
  const live = form.get("target") === "live";
  let siteUrl = appUrl();
  if (live) {
    const parsed = safeUrl(String(form.get("liveUrl") ?? ""));
    if (!parsed) return NextResponse.redirect(new URL("/setup?notice=live-url", appUrl()), 303);
    siteUrl = parsed;
  } else if (githubApp()) {
    return new NextResponse(null, { status: 404 });
  }

  const name = String(form.get("name") ?? "").trim().slice(0, 34) || "GTM Base Dev";
  const state = newState();
  const manifest = JSON.stringify(buildManifest(siteUrl, appUrl(), name));
  const action = `https://github.com/settings/apps/new?state=${encodeURIComponent(state)}`;

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Continue to GitHub</title></head>
<body style="margin:0;padding:48px 16px;background:#faf9f6;color:#151515;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:17px;line-height:1.6">
<form id="f" method="post" action="${action}">
<input type="hidden" name="manifest" value="${escapeAttribute(manifest)}">
<p>Taking you to GitHub to create the app.</p>
<button type="submit" style="min-height:44px;padding:12px 18px;border:1.5px solid #151515;background:#3d63dd;color:#fff;font:inherit;font-weight:800;box-shadow:4px 4px 0 #151515;cursor:pointer">Continue to GitHub</button>
</form>
<script>document.getElementById("f").submit()</script>
</body></html>`;

  const response = new NextResponse(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  response.cookies.set("gtmb_setup_state", state, stateCookieOptions);
  response.cookies.set("gtmb_setup_target", live ? `live ${siteUrl}` : "local", stateCookieOptions);
  return response;
}

// Only a plain https address with no path, query or credentials.
function safeUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) return null;
    if (url.pathname !== "/" && url.pathname !== "") return null;
    return url.origin;
  } catch {
    return null;
  }
}

function escapeAttribute(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
