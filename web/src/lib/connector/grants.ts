import "server-only";
import { SCOPE, resourceUrl } from "./config";
import { open, seal } from "./seal";
import { smallStore } from "./store";

// What a sign-in grants, carried sealed inside the tokens the product holds.
// GitHub's own tokens live here and nowhere else (decision 2 of the C1 plan).
export type Grant = {
  gh: string;
  ghExp: number; // when GitHub's access token ends, in milliseconds since the epoch
  ghRefresh: string | null;
  ghRefreshExp: number | null;
  login: string;
  team: boolean;
};

export type AccessBody = { aud: string; cid: string; chain: string; grant: Pick<Grant, "gh" | "login" | "team"> };
export type RefreshBody = { aud: string; cid: string; chain: string; gen: number; grant: Grant };
export type CodeBody = {
  jti: string;
  cid: string;
  redirectUri: string;
  challenge: string;
  resource: string | null;
  grant: Grant;
};

const ACCESS_SECONDS = 60 * 60;
const REFRESH_SECONDS_WITHOUT_GITHUB_EXPIRY = 30 * 24 * 60 * 60;
export const CODE_SECONDS = 120;

export async function issueTokens(cid: string, chain: string, gen: number, grant: Grant) {
  const now = Date.now();
  // Never outlive GitHub's own token: the product refreshes before it ends.
  const accessSeconds = Math.max(60, Math.min(ACCESS_SECONDS, Math.floor((grant.ghExp - now) / 1000) - 60));
  const refreshSeconds = grant.ghRefreshExp
    ? Math.max(60, Math.floor((grant.ghRefreshExp - now) / 1000) - 60)
    : REFRESH_SECONDS_WITHOUT_GITHUB_EXPIRY;
  const aud = resourceUrl();
  return {
    access_token: await seal(
      "access",
      { aud, cid, chain, grant: { gh: grant.gh, login: grant.login, team: grant.team } } satisfies AccessBody,
      accessSeconds,
    ),
    token_type: "Bearer",
    expires_in: accessSeconds,
    refresh_token: await seal("refresh", { aud, cid, chain, gen, grant } satisfies RefreshBody, refreshSeconds),
    scope: SCOPE,
  };
}

export const openAccess = (value: string | null | undefined) => open<AccessBody>("access", value);
export const openRefresh = (value: string | null | undefined) => open<RefreshBody>("refresh", value);
export const openCode = (value: string | null | undefined) => open<CodeBody>("code", value);

// --- Single-use codes and refresh chains (the "connector-grants" store) -------

type Chain = { gen: number; ended: boolean };

const chainKey = (id: string) => `chain/${id}`;

// A code's id is also the id of the chain of refresh tokens it starts, and the
// chain's record is the mark that the code was used: it can be created once.
// Returns false when the code was already used; that use ends its chain too.
export async function spendCode(jti: string): Promise<boolean> {
  if (await smallStore("connector-grants").create(chainKey(jti), { gen: 0, ended: false } satisfies Chain)) return true;
  await endChain(jti);
  return false;
}

export async function endChain(id: string): Promise<void> {
  const store = smallStore("connector-grants");
  for (let attempt = 0; attempt < 3; attempt++) {
    const found = await store.read<Chain>(chainKey(id));
    if (!found) return; // never started, so there is nothing to end
    if (found.data.ended) return;
    if (await store.replace(chainKey(id), { ...found.data, ended: true }, found.etag)) return;
  }
}

// Moves a chain on by one when `gen` is its current generation. A refresh token
// from an earlier generation means a copy is in use somewhere: the chain ends.
export async function advanceChain(id: string, gen: number): Promise<"ok" | "refused"> {
  const store = smallStore("connector-grants");
  const found = await store.read<Chain>(chainKey(id));
  if (!found || found.data.ended) return "refused";
  if (found.data.gen !== gen) {
    await endChain(id);
    return "refused";
  }
  // Two refreshes at once with the same token: only one moves the chain on.
  return (await store.replace(chainKey(id), { gen: gen + 1, ended: false } satisfies Chain, found.etag))
    ? "ok"
    : "refused";
}
