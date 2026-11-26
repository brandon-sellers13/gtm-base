import "server-only";
import { keyedHash } from "./config";
import { ensure, smallStore } from "./store";

// One base per conversation. The first base a conversation uses is bound to it,
// and any other base is refused there. The store holds only that binding: the
// key is a keyed hash of the product, its conversation id and the GitHub login,
// so no product's raw conversation id is ever stored, and two people can never
// share a key.

export type Conversation = { product: "anthropic" | "openai" | "session"; id: string };

const ID = /^[\x21-\x7e]{1,200}$/; // printable, no spaces, bounded

// Claude sends `com.anthropic/session` and ChatGPT `openai/session` in each tool
// call's _meta (seen in the S0 spike). Failing both, the MCP session id this
// server minted at `initialize` (2025-11-25 clients only; 2026-07-28 has none).
export function conversationFrom(meta: Record<string, unknown> | undefined, sessionId: string | null): Conversation | null {
  const anthropic = meta?.["com.anthropic/session"];
  if (typeof anthropic === "string" && ID.test(anthropic)) return { product: "anthropic", id: anthropic };
  const openai = meta?.["openai/session"];
  if (typeof openai === "string" && ID.test(openai)) return { product: "openai", id: openai };
  if (sessionId) return { product: "session", id: sessionId };
  return null;
}

// A conversation's record starts unbound (base null) the first time it calls,
// so every later read finds an entry (see `ensure` in store.ts). Binding then
// replaces the unbound record only if nobody changed it in between.
type Binding = { base: string | null; product: Conversation["product"]; at: string };

const keyOf = (conversation: Conversation, login: string) =>
  `conversation/${keyedHash("binding", `${conversation.product}\n${conversation.id}\n${login.toLowerCase()}`)}`;

const recordOf = (conversation: Conversation, login: string) =>
  ensure<Binding>(smallStore("connector-bindings"), keyOf(conversation, login), {
    base: null,
    product: conversation.product,
    at: new Date().toISOString(),
  });

export async function boundBase(conversation: Conversation, login: string): Promise<string | null> {
  return (await recordOf(conversation, login)).data.base;
}

// Bases compare without regard to case, as GitHub's owner and repository names do.
const same = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();

export async function bindOrCheck(
  conversation: Conversation,
  login: string,
  base: string,
): Promise<{ ok: true; first: boolean } | { ok: false; bound: string }> {
  const store = smallStore("connector-bindings");
  const key = keyOf(conversation, login);
  const found = await recordOf(conversation, login);
  if (found.data.base) return same(found.data.base, base) ? { ok: true, first: false } : { ok: false, bound: found.data.base };
  const bound: Binding = { base, product: conversation.product, at: new Date().toISOString() };
  if (await store.replace(key, bound, found.etag)) return { ok: true, first: true };
  // A call running alongside this one bound the conversation first.
  const winner = await store.read<Binding>(key);
  if (!winner?.data.base) return { ok: false, bound: "another base" };
  return same(winner.data.base, base) ? { ok: true, first: false } : { ok: false, bound: winner.data.base };
}
