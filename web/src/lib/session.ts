import "server-only";
import { cookies } from "next/headers";
import { EncryptJWT, jwtDecrypt } from "jose";
import { allowedLogins, isDevelopment, sessionSecret } from "./config";

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
  team?: boolean; // let in at sign-in because they reach a base on an allowed account
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
    // Checked on every request, so taking a login off the list ends its session at once.
    // A teammate let in at sign-in stays in for the session; if their access to
    // the base is removed, GitHub itself stops showing it to them.
    if (!session.team && !allowedLogins().has(session.login.toLowerCase())) return null;
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
