import "server-only";
import { api, GitHubError, type Installation } from "./github";
import { listBases } from "./bases";
import { frontMatter, validRepo } from "./reader";

// Who works on a base is who GitHub says has access to its repository. The app
// stores nothing about it. Only the base's owner (the map's owner, matched to a
// verified GitHub email) may invite or cancel an invitation, and GitHub also
// requires the person to be an admin of the repository.

export type Member = { login: string; avatarUrl: string; role: string };
export type Invitation = { id: number; login: string; avatarUrl: string; createdAt: string };

const USERNAME = /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/;
export const validUsername = (name: string) => USERNAME.test(name);

export async function listTeam(token: string, owner: string, repo: string) {
  if (!validRepo(owner, repo)) return { members: [], invitations: [] };
  const [collaborators, invitations] = await Promise.all([
    api<{ login: string; avatar_url: string; role_name: string }[]>(
      `/repos/${owner}/${repo}/collaborators?per_page=100`,
      { token },
    ),
    api<{ id: number; invitee: { login: string; avatar_url: string } | null; created_at: string }[]>(
      `/repos/${owner}/${repo}/invitations?per_page=100`,
      { token },
    ).catch((error) => {
      // Only admins can see pending invitations; everyone else just sees members.
      if (error instanceof GitHubError && (error.status === 403 || error.status === 404)) return [];
      throw error;
    }),
  ]);
  return {
    members: collaborators.map((c) => ({ login: c.login, avatarUrl: c.avatar_url, role: c.role_name })),
    invitations: invitations
      .filter((i) => i.invitee)
      .map((i) => ({
        id: i.id,
        login: i.invitee!.login,
        avatarUrl: i.invitee!.avatar_url,
        createdAt: i.created_at.slice(0, 10),
      })),
  };
}

// The base's owner: the map's owner line on the default branch, as it stands now.
export async function baseOwnerEmails(token: string, owner: string, repo: string): Promise<string[]> {
  const file = await api<{ content: string }>(`/repos/${owner}/${repo}/contents/context/map.md`, { token });
  const { fields } = frontMatter(Buffer.from(file.content, "base64").toString("utf8"));
  const value = fields.owner;
  return (Array.isArray(value) ? value : value ? [value] : []).map((e) => e.toLowerCase());
}

export async function isBaseOwner(token: string, owner: string, repo: string, verifiedEmails: string[]) {
  if (!validRepo(owner, repo)) return false;
  const owners = await baseOwnerEmails(token, owner, repo);
  return verifiedEmails.some((e) => owners.includes(e.toLowerCase()));
}

export class TeamError extends Error {
  constructor(readonly code: "not-owner" | "bad-username" | "no-such-user" | "self" | "refused" | "failed") {
    super(code);
  }
}

export async function invite(options: {
  token: string;
  owner: string;
  repo: string;
  username: string;
  login: string;
  verifiedEmails: string[];
}): Promise<"invited" | "already"> {
  const { token, owner, repo, username, login, verifiedEmails } = options;
  if (!validUsername(username)) throw new TeamError("bad-username");
  if (username.toLowerCase() === login.toLowerCase()) throw new TeamError("self");
  if (!(await isBaseOwner(token, owner, repo, verifiedEmails))) throw new TeamError("not-owner");
  try {
    // "push" lets a teammate's Claude Code open proposals on their own branches.
    // Changes to the main branch still come in through the owner's accept.
    const response = await api<unknown>(`/repos/${owner}/${repo}/collaborators/${username}`, {
      token,
      method: "PUT",
      body: JSON.stringify({ permission: "push" }),
    });
    return response ? "invited" : "already";
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) throw new TeamError("no-such-user");
    if (error instanceof GitHubError && (error.status === 403 || error.status === 422)) throw new TeamError("refused");
    throw new TeamError("failed");
  }
}

export async function cancelInvitation(options: {
  token: string;
  owner: string;
  repo: string;
  invitationId: number;
  verifiedEmails: string[];
}): Promise<void> {
  const { token, owner, repo, invitationId, verifiedEmails } = options;
  if (!Number.isInteger(invitationId) || invitationId < 1) throw new TeamError("failed");
  if (!(await isBaseOwner(token, owner, repo, verifiedEmails))) throw new TeamError("not-owner");
  await api(`/repos/${owner}/${repo}/invitations/${invitationId}`, { token, method: "DELETE" });
}

// Invite-only, extended to teams: someone not on the allowlist may still sign in
// when they can reach a base kept on an allowed person's account. Their own
// bases on their own account do not count, so the allowlist still decides who
// starts using GTM Base.
export async function reachesAllowedBase(
  token: string,
  installations: Installation[],
  allowed: Set<string>,
): Promise<boolean> {
  const onAllowedAccounts = installations.filter((i) => allowed.has(i.account.login.toLowerCase()));
  if (onAllowedAccounts.length === 0) return false;
  const bases = await listBases(token, onAllowedAccounts);
  return bases.some((b) => allowed.has(b.owner.toLowerCase()));
}
