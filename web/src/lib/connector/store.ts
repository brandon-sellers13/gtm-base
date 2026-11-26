import "server-only";
import { randomUUID } from "node:crypto";
import { getStore } from "@netlify/blobs";
import { isDevelopment } from "../config";

// The connector's two small stores, both Netlify Blobs that last across deploys,
// every read and write strongly consistent:
//
// - "connector-bindings": which base each conversation is bound to (the store
//   Brandon approved on 2026-11-26). Never documents, tokens or conversation content.
// - "connector-grants": random ids and counters that make sign-in codes single
//   use and let a reused refresh token end its chain (approved the same day).
//   Never a token.
//
// On a developer's computer (`next dev`, off Netlify) a store held in memory
// stands in, with the same first-write-wins rules, so the checks can run locally.

export type StoreName = "connector-bindings" | "connector-grants";

export type Entry<T> = { data: T; etag: string };

export interface SmallStore {
  // Reads an entry that exists. Never call it for a key that may be missing:
  // on Netlify a strongly consistent read of a missing key is retried for about
  // 25 seconds before it answers (seen on 2026-11-26), so callers use `ensure`.
  read<T>(key: string): Promise<Entry<T> | null>;
  // Writes only when nothing is there yet; false when something already was.
  create(key: string, value: unknown): Promise<boolean>;
  // Writes only when the entry is still the one read; false when it changed.
  replace(key: string, value: unknown, etag: string): Promise<boolean>;
}

// Creates the entry with `initial` unless it exists, then reads it, so no read
// ever asks for a missing key. `created` says whether this call made it.
export async function ensure<T>(store: SmallStore, key: string, initial: T): Promise<Entry<T> & { created: boolean }> {
  const created = await store.create(key, initial);
  const found = await store.read<T>(key);
  if (!found) throw new Error("The connector's store did not keep an entry it just wrote.");
  return { ...found, created };
}

// No store call may hold a request for long: a stuck call fails instead.
const LIMIT_MS = 8000;
function limited<T>(work: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("The connector's store did not answer in time.")), LIMIT_MS);
  });
  return Promise.race([work, timeout]).finally(() => clearTimeout(timer));
}

function blobs(name: StoreName): SmallStore {
  const store = getStore({ name, consistency: "strong" });
  return {
    async read<T>(key: string) {
      const found = await limited(store.getWithMetadata(key, { type: "json", consistency: "strong" }));
      return found && found.etag ? { data: found.data as T, etag: found.etag } : null;
    },
    async create(key, value) {
      return (await limited(store.setJSON(key, value, { onlyIfNew: true }))).modified;
    },
    async replace(key, value, etag) {
      return (await limited(store.setJSON(key, value, { onlyIfMatch: etag }))).modified;
    },
  };
}

const memory = new Map<string, { data: unknown; etag: string }>();

function inMemory(name: StoreName): SmallStore {
  const k = (key: string) => `${name}/${key}`;
  return {
    async read<T>(key: string) {
      const found = memory.get(k(key));
      return found ? { data: structuredClone(found.data) as T, etag: found.etag } : null;
    },
    async create(key, value) {
      if (memory.has(k(key))) return false;
      memory.set(k(key), { data: structuredClone(value), etag: randomUUID() });
      return true;
    },
    async replace(key, value, etag) {
      const found = memory.get(k(key));
      if (!found || found.etag !== etag) return false;
      memory.set(k(key), { data: structuredClone(value), etag: randomUUID() });
      return true;
    },
  };
}

// Netlify sets NETLIFY on its builds and SITE_ID in its functions.
const onNetlify = () => !!(process.env.NETLIFY || process.env.SITE_ID || process.env.NETLIFY_BLOBS_CONTEXT);

export function smallStore(name: StoreName): SmallStore {
  if (!onNetlify() && isDevelopment()) return inMemory(name);
  return blobs(name);
}
