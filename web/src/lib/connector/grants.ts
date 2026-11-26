import "server-only";
import { SCOPE, resourceUrl } from "./config";
import { open, seal } from "./seal";
import { ensure, smallStore } from "./store";

// What a sign-in grants, carried sealed inside the tokens the product holds.
// GitHub's own tokens live here and nowhere else (decision 2 of the C1 plan).
export type Grant = {
  gh: string;
  ghExp: number | null; // when GitHub's access token ends, in milliseconds since the epoch; null if it never does
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
  const accessSeconds =
    grant.ghExp === null
      ? ACCESS_SECONDS
      : Math.max(60, Math.min(ACCESS_SECONDS, Math.floor((grant.ghExp - now) / 1000) - 60));
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

// A chain has two records. `chain/<id>` holds the current refresh generation
// (and is created already ended for a chain that never started, so reading it
// never asks the store for a missing key, see `ensure`). `ended/<id>` is the
// mark that ends the chain: it is written unconditionally, so no number of
// refreshes running alongside can stop it from landing.
type Chain = { gen: number; ended: boolean };
type Ended = { ended: boolean };

const chainKey = (id: string) => `chain/${id}`;
const endedKey = (id: string) => `ended/${id}`;
const NEVER_STARTED: Chain = { gen: 0, ended: true };

// A code's id is also the id of the chain of refresh tokens it starts, and the
// chain's record is the mark that the code was used: it can be created once.
// Returns false when the code was already used; that use ends its chain too.
export async function spendCode(jti: string): Promise<boolean> {
  if (await smallStore("connector-grants").create(chainKey(jti), { gen: 0, ended: false } satisfies Chain)) return true;
  await endChain(jti);
  return false;
}

export async function endChain(id: string): Promise<void> {
  await smallStore("connector-grants").put(endedKey(id), { ended: true } satisfies Ended);
}

// Moves a chain on by one when `gen` is its current generation, and returns the
// new record's ETag so a refresh GitHub could not complete can be undone. A
// refresh token from an earlier generation means a copy is in use somewhere: the
// chain ends.
export async function advanceChain(id: string, gen: number): Promise<{ ok: true; etag: string } | { ok: false }> {
  const store = smallStore("connector-grants");
  const found = await ensure(store, chainKey(id), NEVER_STARTED);
  if (found.data.ended || (await ensure<Ended>(store, endedKey(id), { ended: false })).data.ended) return { ok: false };
  if (found.data.gen !== gen) {
    await endChain(id);
    return { ok: false };
  }
  // Two refreshes at once with the same token: only one moves the chain on.
  const etag = await store.replace(chainKey(id), { gen: gen + 1, ended: false } satisfies Chain, found.etag);
  return etag ? { ok: true, etag } : { ok: false };
}

// Puts a chain back one generation, when GitHub could not be reached to finish
// the refresh that moved it on, so the product can retry with the same token.
// Does nothing if the chain has moved since.
export async function rewindChain(id: string, gen: number, etag: string): Promise<void> {
  await smallStore("connector-grants").replace(chainKey(id), { gen, ended: false } satisfies Chain, etag);
}
