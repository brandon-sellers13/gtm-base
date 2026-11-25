// Every setting the app reads from its environment, in one place.
// Values come from web/.env.local in development and from Vercel in production.
// Nothing here is ever logged or sent to the browser.

export type GitHubAppConfig = {
  appId: string;
  slug: string;
  clientId: string;
  clientSecret: string;
};

export function appUrl(): string {
  return (process.env.APP_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}

export function isDevelopment(): boolean {
  return process.env.NODE_ENV !== "production";
}

// The GitHub App, or null when it has not been registered yet.
export function githubApp(): GitHubAppConfig | null {
  const appId = process.env.GITHUB_APP_ID;
  const slug = process.env.GITHUB_APP_SLUG;
  const clientId = process.env.GITHUB_APP_CLIENT_ID;
  const clientSecret = process.env.GITHUB_APP_CLIENT_SECRET;
  // The app's private key is kept on this computer (GitHub shows it only once) but
  // nothing in the app uses it, so the running app neither needs nor holds it.
  if (!appId || !slug || !clientId || !clientSecret) return null;
  return {
    appId,
    slug,
    clientId,
    clientSecret,
  };
}

export function sessionSecret(): Uint8Array {
  const raw = process.env.SESSION_SECRET;
  if (!raw) throw new Error("SESSION_SECRET is not set.");
  const bytes = Buffer.from(raw, "base64");
  if (bytes.length !== 32) throw new Error("SESSION_SECRET must be 32 bytes, base64 encoded.");
  return new Uint8Array(bytes);
}

// Version one is invite-only. An empty list lets nobody in, rather than everybody.
export function allowedLogins(): Set<string> {
  return new Set(
    (process.env.ALLOWED_GITHUB_LOGINS ?? "")
      .split(",")
      .map((login) => login.trim().toLowerCase())
      .filter(Boolean),
  );
}
