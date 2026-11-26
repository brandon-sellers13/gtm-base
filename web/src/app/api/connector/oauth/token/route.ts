import { stillAllowed } from "@/lib/access";
import { githubApp } from "@/lib/config";
import { connectorEnabled, notFound, resourceUrl } from "@/lib/connector/config";
import {
  type Grant,
  advanceChain,
  endChain,
  issueTokens,
  openCode,
  openRefresh,
  spendCode,
} from "@/lib/connector/grants";
import { s256, sameText } from "@/lib/connector/seal";
import { refreshUserTokens } from "@/lib/github";

// The token endpoint: form-encoded only, as Claude's docs require. Trades a code
// (with its PKCE verifier) or a refresh token for new tokens. No step calls
// GitHub except a refresh when GitHub's own token is near its end.

const headers = { "Cache-Control": "no-store", Pragma: "no-cache" };
const fail = (error: string, status = 400) => Response.json({ error }, { status, headers });

// Refresh at GitHub when its token has less than this long left.
const GITHUB_REFRESH_MARGIN_MS = 65 * 60 * 1000;

export async function POST(request: Request) {
  if (!connectorEnabled()) return notFound();
  const type = request.headers.get("content-type") ?? "";
  if (!type.toLowerCase().startsWith("application/x-www-form-urlencoded")) return fail("invalid_request");
  const form = new URLSearchParams(await request.text());
  const clientId = form.get("client_id");
  const resource = form.get("resource");
  if (resource && resource.replace(/\/+$/, "") !== resourceUrl()) return fail("invalid_target");

  const grantType = form.get("grant_type");

  if (grantType === "authorization_code") {
    const code = await openCode(form.get("code"));
    if (!code) return fail("invalid_grant");
    if (clientId && !sameText(clientId, code.cid)) return fail("invalid_grant");
    const redirectUri = form.get("redirect_uri");
    if (redirectUri && redirectUri !== code.redirectUri) return fail("invalid_grant");
    const verifier = form.get("code_verifier");
    if (!verifier || !/^[A-Za-z0-9._~-]{43,128}$/.test(verifier) || !sameText(s256(verifier), code.challenge)) {
      return fail("invalid_grant");
    }
    // Each code works once. A second use ends the chain the first one started.
    if (!(await spendCode(code.jti))) return fail("invalid_grant");
    return Response.json(await issueTokens(code.cid, code.jti, 0, code.grant), { headers });
  }

  if (grantType === "refresh_token") {
    const refresh = await openRefresh(form.get("refresh_token"));
    if (!refresh || refresh.aud !== resourceUrl()) return fail("invalid_grant");
    if (clientId && !sameText(clientId, refresh.cid)) return fail("invalid_grant");
    if (!stillAllowed(refresh.grant.login, refresh.grant.team)) {
      await endChain(refresh.chain);
      return fail("invalid_grant");
    }
    if ((await advanceChain(refresh.chain, refresh.gen)) !== "ok") return fail("invalid_grant");

    let grant: Grant = refresh.grant;
    if (grant.ghExp - Date.now() < GITHUB_REFRESH_MARGIN_MS) {
      const app = githubApp();
      if (!grant.ghRefresh || !app) return fail("invalid_grant");
      try {
        const gh = await refreshUserTokens(grant.ghRefresh, app.clientId, app.clientSecret);
        const now = Date.now();
        grant = {
          ...grant,
          gh: gh.token,
          ghExp: now + gh.expiresInSeconds * 1000,
          ghRefresh: gh.refreshToken,
          ghRefreshExp: gh.refreshExpiresInSeconds ? now + gh.refreshExpiresInSeconds * 1000 : grant.ghRefreshExp,
        };
      } catch {
        // GitHub ended the sign-in (the person revoked the app, or its refresh
        // token ran out): the product must sign in again.
        await endChain(refresh.chain);
        return fail("invalid_grant");
      }
    }
    return Response.json(await issueTokens(refresh.cid, refresh.chain, refresh.gen + 1, grant), { headers });
  }

  return fail("unsupported_grant_type");
}
