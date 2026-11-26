import "server-only";

// Small, explicit calls to GitHub. No SDK: each call names exactly what it asks for.

const API = "https://api.github.com";

export class GitHubError extends Error {
  constructor(
    message: string,
    readonly status: number,
    // Set when GitHub's sign-in service itself refused (for example
    // bad_refresh_token): a definite answer, unlike a network failure or an outage.
    readonly oauthError: string | null = null,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/vnd.github+json");
  headers.set("X-GitHub-Api-Version", "2022-11-28");
  if (init.token) headers.set("Authorization", `Bearer ${init.token}`);
  const response = await fetch(`${API}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    // The body can echo request details, so only the status is kept.
    throw new GitHubError(`GitHub answered ${response.status} for ${path.split("?")[0]}`, response.status);
  }
  // 204 No Content (an invitation cancelled, a collaborator already there) has no body.
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

export type GitHubUser = { login: string; name: string | null; avatar_url: string };
export type GitHubEmail = { email: string; verified: boolean; primary: boolean };
export type Installation = {
  id: number;
  account: { login: string; type: string; avatar_url: string };
  repository_selection: "all" | "selected";
};

// A GitHub App user token, with its refresh token when GitHub's token expiry is
// on. GitHub leaves out expires_in only for a token that never expires, so null
// here means exactly that.
export type UserTokens = {
  token: string;
  expiresInSeconds: number | null;
  refreshToken: string | null;
  refreshExpiresInSeconds: number | null;
};

async function userTokens(body: Record<string, string>): Promise<UserTokens> {
  const response = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  let answer: {
    access_token?: string;
    expires_in?: number;
    refresh_token?: string;
    refresh_token_expires_in?: number;
    error?: string;
  };
  try {
    answer = (await response.json()) as typeof answer;
  } catch {
    // Not GitHub's sign-in service answering (an outage page, a proxy): no verdict.
    throw new GitHubError(`GitHub's sign-in service answered ${response.status} without JSON`, response.status || 502);
  }
  if (answer.error) {
    // GitHub's own refusal, such as bad_refresh_token or bad_verification_code.
    throw new GitHubError(`GitHub refused the sign-in (${answer.error})`, response.status || 400, answer.error);
  }
  if (!response.ok || !answer.access_token) {
    throw new GitHubError(`GitHub's sign-in service answered ${response.status}`, response.status || 502);
  }
  return {
    token: answer.access_token,
    expiresInSeconds: answer.expires_in ?? null,
    refreshToken: answer.refresh_token ?? null,
    refreshExpiresInSeconds: answer.refresh_token_expires_in ?? null,
  };
}

export const exchangeCodeForTokens = (code: string, clientId: string, clientSecret: string, redirectUri: string) =>
  userTokens({ client_id: clientId, client_secret: clientSecret, code, redirect_uri: redirectUri });

export const refreshUserTokens = (refreshToken: string, clientId: string, clientSecret: string) =>
  userTokens({ client_id: clientId, client_secret: clientSecret, grant_type: "refresh_token", refresh_token: refreshToken });

export async function exchangeCode(
  code: string,
  clientId: string,
  clientSecret: string,
  redirectUri: string,
): Promise<{ token: string; expiresInSeconds: number }> {
  const { token, expiresInSeconds } = await exchangeCodeForTokens(code, clientId, clientSecret, redirectUri);
  // The web app's own session keeps its eight-hour limit either way.
  return { token, expiresInSeconds: expiresInSeconds ?? 8 * 60 * 60 };
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
