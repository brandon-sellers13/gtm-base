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
  read<T>(key: string): Promise<Entry<T> | null>;
  // Writes only when nothing is there yet; false when something already was.
  create(key: string, value: unknown): Promise<boolean>;
  // Writes only when the entry is still the one read; false when it changed.
  replace(key: string, value: unknown, etag: string): Promise<boolean>;
}

function blobs(name: StoreName): SmallStore {
  const store = getStore({ name, consistency: "strong" });
  return {
    async read<T>(key: string) {
      const found = await store.getWithMetadata(key, { type: "json", consistency: "strong" });
      return found && found.etag ? { data: found.data as T, etag: found.etag } : null;
    },
    async create(key, value) {
      return (await store.setJSON(key, value, { onlyIfNew: true })).modified;
    },
    async replace(key, value, etag) {
      return (await store.setJSON(key, value, { onlyIfMatch: etag })).modified;
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
