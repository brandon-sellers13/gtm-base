import "server-only";

// Small, explicit calls to GitHub. No SDK: each call names exactly what it asks for.

const API = "https://api.github.com";

export class GitHubError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function api<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/vnd.github+json");
  headers.set("X-GitHub-Api-Version", "2022-11-28");
  if (init.token) headers.set("Authorization", `Bearer ${init.token}`);
  const response = await fetch(`${API}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    // The body can echo request details, so only the status is kept.
    throw new GitHubError(`GitHub answered ${response.status} for ${path.split("?")[0]}`, response.status);
  }
  return (await response.json()) as T;
}

export type GitHubUser = { login: string; name: string | null; avatar_url: string };
export type GitHubEmail = { email: string; verified: boolean; primary: boolean };
export type Installation = {
  id: number;
  account: { login: string; type: string; avatar_url: string };
  repository_selection: "all" | "selected";
};

export async function exchangeCode(
  code: string,
  clientId: string,
  clientSecret: string,
  redirectUri: string,
): Promise<{ token: string; expiresInSeconds: number }> {
  const response = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, code, redirect_uri: redirectUri }),
    cache: "no-store",
  });
  const body = (await response.json()) as { access_token?: string; expires_in?: number; error?: string };
  if (!response.ok || !body.access_token) {
    throw new GitHubError(`GitHub refused the sign-in code (${body.error ?? response.status})`, response.status);
  }
  return { token: body.access_token, expiresInSeconds: body.expires_in ?? 8 * 60 * 60 };
}

export const getUser = (token: string) => api<GitHubUser>("/user", { token });

export async function getVerifiedEmails(token: string): Promise<string[]> {
  try {
    const emails = await api<GitHubEmail[]>("/user/emails", { token });
    return emails.filter((e) => e.verified).map((e) => e.email.toLowerCase());
  } catch (error) {
    // Without the email permission the list is simply empty; owner matching then fails closed.
    if (error instanceof GitHubError && (error.status === 403 || error.status === 404)) return [];
    throw error;
  }
}

export async function listInstallations(token: string): Promise<Installation[]> {
  const body = await api<{ installations: Installation[] }>("/user/installations?per_page=100", { token });
  return body.installations;
}

// The manifest flow: GitHub hands back the new app's credentials once, for this code.
export type ManifestConversion = {
  id: number;
  slug: string;
  client_id: string;
  client_secret: string;
  pem: string;
  html_url: string;
};

export const convertManifest = (code: string) =>
  api<ManifestConversion>(`/app-manifests/${encodeURIComponent(code)}/conversions`, { method: "POST" });
