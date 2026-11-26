import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { appUrl } from "@/lib/config";
import { connectorEnabled, notFound } from "@/lib/connector/config";
import { CODE_SECONDS, type CodeBody } from "@/lib/connector/grants";
import { open, randomId, sameText, seal } from "@/lib/connector/seal";
import { CONSENT_COOKIE, type Consent, backToProduct, stoppedPage } from "@/lib/connector/signin";

// The consent page's answer. Accepted only from this site's own pages, and only
// when the form carries the same one-time value as the sealed cookie.
export async function POST(request: Request) {
  if (!connectorEnabled()) return notFound();
  const own = new URL(appUrl()).origin;
  const origin = request.headers.get("origin");
  const site = request.headers.get("sec-fetch-site");
  if ((origin && origin !== own) || (site && site !== "same-origin")) {
    return stoppedPage("This answer did not come from the GTM Base consent page.", 403);
  }
  const store = await cookies();
  const consent = await open<Consent>("consent", store.get(CONSENT_COOKIE)?.value);
  const form = await request.formData().catch(() => null);
  const nonce = form?.get("nonce");
  if (!consent || typeof nonce !== "string" || !sameText(nonce, consent.nonce)) {
    return stoppedPage("This sign-in has expired. Start again from Claude or ChatGPT.");
  }

  let response: NextResponse;
  if (form?.get("decision") !== "allow") {
    response = backToProduct(consent.redirectUri, consent.state, { error: "access_denied" }, 303);
  } else {
    const code: CodeBody = {
      jti: randomId(),
      cid: consent.cid,
      redirectUri: consent.redirectUri,
      challenge: consent.challenge,
      resource: consent.resource,
      grant: consent.grant,
    };
    response = backToProduct(consent.redirectUri, consent.state, { code: await seal("code", code, CODE_SECONDS) }, 303);
  }
  response.cookies.delete(CONSENT_COOKIE);
  return response;
}
