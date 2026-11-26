import "server-only";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { EncryptJWT, jwtDecrypt } from "jose";
import { type KeyPurpose, connectorKey } from "./config";

// Every value the connector hands out (client id, sign-in in progress, code,
// access token, refresh token, legacy session id) is encrypted with A256GCM
// under a key only the server holds. Whoever holds one can neither read nor
// change it.

export async function seal(purpose: KeyPurpose, body: Record<string, unknown>, seconds: number): Promise<string> {
  return new EncryptJWT({ b: body })
    .setProtectedHeader({ alg: "dir", enc: "A256GCM" })
    .setIssuedAt()
    .setExpirationTime(`${Math.max(1, Math.floor(seconds))}s`)
    .encrypt(connectorKey(purpose));
}

export async function open<T>(purpose: KeyPurpose, value: string | null | undefined): Promise<T | null> {
  if (!value || value.length > 8192) return null;
  try {
    const { payload } = await jwtDecrypt(value, connectorKey(purpose));
    return (payload.b as T) ?? null;
  } catch {
    return null;
  }
}

export const randomId = () => randomBytes(18).toString("base64url");

export const s256 = (verifier: string) => createHash("sha256").update(verifier).digest("base64url");

export function sameText(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}
