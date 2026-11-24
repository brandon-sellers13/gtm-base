import "server-only";
import { cookies } from "next/headers";
import { EncryptJWT, jwtDecrypt } from "jose";
import { isDevelopment, sessionSecret } from "./config";

// The session is an encrypted cookie. It holds the person's GitHub user token,
// so it is encrypted (not only signed) and never readable from the browser.

export const SESSION_COOKIE = "gtmb_session";
const SESSION_HOURS = 8; // GitHub App user tokens expire after eight hours.

export type Session = {
  login: string;
  name: string | null;
  avatarUrl: string;
  emails: string[]; // verified addresses only, used to match document owners
  token: string;
  expiresAt: number; // milliseconds since the epoch
};

export async function sealSession(session: Session): Promise<string> {
  return new EncryptJWT({ s: session })
    .setProtectedHeader({ alg: "dir", enc: "A256GCM" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_HOURS}h`)
    .encrypt(sessionSecret());
}

export async function openSession(value: string | undefined): Promise<Session | null> {
  if (!value) return null;
  try {
    const { payload } = await jwtDecrypt(value, sessionSecret());
    const session = payload.s as Session | undefined;
    if (!session || session.expiresAt < Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export async function currentSession(): Promise<Session | null> {
  const store = await cookies();
  return openSession(store.get(SESSION_COOKIE)?.value);
}

export const sessionCookieOptions = {
  httpOnly: true,
  secure: !isDevelopment(),
  sameSite: "lax" as const,
  path: "/",
  maxAge: SESSION_HOURS * 60 * 60,
};
