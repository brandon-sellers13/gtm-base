import "server-only";
import { randomBytes, timingSafeEqual } from "node:crypto";
import { isDevelopment } from "./config";

// A one-time value tying a GitHub redirect back to the browser that started it.

export const newState = () => randomBytes(24).toString("base64url");

export function sameState(expected: string | undefined, received: string | null): boolean {
  if (!expected || !received) return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(received);
  return a.length === b.length && timingSafeEqual(a, b);
}

export const stateCookieOptions = {
  httpOnly: true,
  secure: !isDevelopment(),
  sameSite: "lax" as const,
  path: "/",
  maxAge: 10 * 60,
};
