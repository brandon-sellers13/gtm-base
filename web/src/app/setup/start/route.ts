import { NextRequest, NextResponse } from "next/server";
import { appUrl, githubApp, isDevelopment } from "@/lib/config";
import { buildManifest } from "@/lib/manifest";
import { newState, stateCookieOptions } from "@/lib/oauthState";

// Development only. Hands the app's registration to GitHub, which shows the
// person a "Create GitHub App" page; nothing is created until they click it.
export async function POST(request: NextRequest) {
  if (!isDevelopment() || githubApp()) return new NextResponse(null, { status: 404 });

  const form = await request.formData();
  const name = String(form.get("name") ?? "").trim().slice(0, 34) || "GTM Base Dev";
  const state = newState();
  const manifest = JSON.stringify(buildManifest(appUrl(), name));
  const action = `https://github.com/settings/apps/new?state=${encodeURIComponent(state)}`;

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Continue to GitHub</title></head>
<body style="font-family:system-ui;padding:40px">
<form id="f" method="post" action="${action}">
<input type="hidden" name="manifest" value="${escapeAttribute(manifest)}">
<p>Taking you to GitHub to create the app.</p>
<button type="submit">Continue to GitHub</button>
</form>
<script>document.getElementById("f").submit()</script>
</body></html>`;

  const response = new NextResponse(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
  response.cookies.set("gtmb_setup_state", state, stateCookieOptions);
  return response;
}

function escapeAttribute(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
