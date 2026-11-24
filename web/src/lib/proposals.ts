import "server-only";
import { api, GitHubError } from "./github";
import { frontMatter, validRepo } from "./reader";

// Proposals are pull requests the plugin opens from a seat. Their body ends with
// one marker line, and the plugin's own records decide everything else:
// - Accepting is a merge onto the default branch. The plugin counts it as the
//   owner's confirmation when the commit that lands the change on the main line
//   (read along its first parent) is authored with an owner's email. So the app
//   builds that merge commit itself, authored with the owner's verified email.
// - Discarding is closing the pull request; the plugin treats a closed proposal
//   as turned down and does not raise it again.

const MARKER = /^gtm-base proposal (stg-[0-9a-f]+) entry (\S+) source (\S+)\s*$/m;
// Documents that carry an owner; records (changes, corrections) do not.
const OWNED_PREFIXES = ["context/", "access/", "standards/", "skills/"];

type PullSummary = {
  number: number;
  title: string;
  body: string | null;
  html_url: string;
  user: { login: string; avatar_url: string };
  created_at: string;
  head: { sha: string; ref: string };
  base: { sha: string; ref: string };
};

type Pull = PullSummary & {
  state: string;
  merged: boolean;
  mergeable: boolean | null;
  merge_commit_sha: string | null;
};

export type ProposalSummary = {
  number: number;
  title: string;
  author: string;
  avatarUrl: string;
  createdAt: string;
  proposalId: string;
};

export type ProposalFile = {
  path: string;
  status: string;
  owners: string[]; // empty for records, or for a document that names no owner
  ownedDocument: boolean;
  allowed: boolean; // an owned document or one of the plugin's records
};

export type Proposal = ProposalSummary & {
  htmlUrl: string;
  body: string; // markdown, with the marker line taken off
  files: ProposalFile[];
  complete: boolean; // false when the proposal changes too many files to check
  baseRef: string;
  headSha: string; // the version the person was shown
};

export class ProposalNotFound extends Error {}

function marker(body: string | null) {
  const match = (body ?? "").match(MARKER);
  return match ? { proposalId: match[1], entryId: match[2], sourceId: match[3] } : null;
}

function summary(pull: PullSummary, proposalId: string): ProposalSummary {
  return {
    number: pull.number,
    title: pull.title,
    author: pull.user.login,
    avatarUrl: pull.user.avatar_url,
    createdAt: pull.created_at.slice(0, 10),
    proposalId,
  };
}

export async function listProposals(token: string, owner: string, repo: string): Promise<ProposalSummary[]> {
  if (!validRepo(owner, repo)) return [];
  const pulls = await api<PullSummary[]>(`/repos/${owner}/${repo}/pulls?state=open&per_page=100`, { token });
  return pulls.flatMap((pull) => {
    const found = marker(pull.body);
    return found ? [summary(pull, found.proposalId)] : [];
  });
}

async function readOwners(token: string, owner: string, repo: string, path: string, ref: string): Promise<string[]> {
  try {
    const file = await api<{ content: string }>(
      `/repos/${owner}/${repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}?ref=${encodeURIComponent(ref)}`,
      { token },
    );
    const { fields } = frontMatter(Buffer.from(file.content, "base64").toString("utf8"));
    const value = fields.owner;
    return (Array.isArray(value) ? value : value ? [value] : []).map((e) => e.toLowerCase());
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) return [];
    throw error;
  }
}

async function getPull(token: string, owner: string, repo: string, number: number): Promise<Pull> {
  if (!validRepo(owner, repo) || !Number.isInteger(number) || number < 1) throw new ProposalNotFound();
  try {
    return await api<Pull>(`/repos/${owner}/${repo}/pulls/${number}`, { token });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) throw new ProposalNotFound();
    throw error;
  }
}

// Records a proposal may add alongside the documents it changes.
const RECORD_PREFIXES = ["learning/changes/", "learning/corrections/"];
const MAX_FILE_PAGES = 10; // 1,000 files; a bigger proposal is refused, never half-checked

export async function getProposal(token: string, owner: string, repo: string, number: number): Promise<Proposal> {
  const pull = await getPull(token, owner, repo, number);
  const found = marker(pull.body);
  if (!found || pull.state !== "open") throw new ProposalNotFound();

  const changed: { filename: string; status: string }[] = [];
  let complete = false;
  for (let page = 1; page <= MAX_FILE_PAGES; page++) {
    const batch = await api<{ filename: string; status: string }[]>(
      `/repos/${owner}/${repo}/pulls/${number}/files?per_page=100&page=${page}`,
      { token },
    );
    changed.push(...batch);
    if (batch.length < 100) {
      complete = true;
      break;
    }
  }

  // Owners come from the base branch as it stands now, the same commit an
  // accept is built on, never from the proposal's own version of a file.
  const tip = await api<{ object: { sha: string } }>(
    `/repos/${owner}/${repo}/git/ref/heads/${encodeURIComponent(pull.base.ref)}`,
    { token },
  );
  const baseOwners = await readOwners(token, owner, repo, "context/map.md", tip.object.sha);

  const files = await Promise.all(
    changed.map(async (file) => {
      const ownedDocument = OWNED_PREFIXES.some((prefix) => file.filename.startsWith(prefix)) && file.filename.endsWith(".md");
      const record = RECORD_PREFIXES.some((prefix) => file.filename.startsWith(prefix)) && file.filename.endsWith(".md");
      // A brand-new document has no saved owner yet, so the base's owner (the map's)
      // decides, whatever owner the proposal writes into it.
      const owners = !ownedDocument
        ? []
        : file.status === "added"
          ? baseOwners
          : await readOwners(token, owner, repo, file.filename, tip.object.sha);
      return { path: file.filename, status: file.status, owners, ownedDocument, allowed: ownedDocument || record };
    }),
  );

  return {
    ...summary(pull, found.proposalId),
    htmlUrl: pull.html_url,
    body: (pull.body ?? "").replace(MARKER, "").trim(),
    files,
    complete,
    baseRef: pull.base.ref,
    headSha: pull.head.sha,
  };
}

// Why this proposal cannot be accepted here at all, whoever asks. Only owned
// documents and the plugin's records may come in through an accept: anything
// else (settings, hooks, scripts, CLAUDE.md, other files) would run or apply on
// every seat, which the plugin's own checks refuse in a base.
export function blockedReason(proposal: Proposal): "too-large" | "other-files" | null {
  if (!proposal.complete) return "too-large";
  if (proposal.files.some((f) => !f.allowed)) return "other-files";
  return null;
}

// The one email this person may accept with: a verified address of theirs that
// owns every owned document the proposal touches. Null when there is none.
export function acceptingEmail(proposal: Proposal, verifiedEmails: string[]): string | null {
  if (blockedReason(proposal)) return null;
  const owned = proposal.files.filter((f) => f.ownedDocument);
  if (owned.length === 0 || owned.some((f) => f.owners.length === 0)) return null;
  const mine = verifiedEmails.map((e) => e.toLowerCase());
  return mine.find((email) => owned.every((f) => f.owners.includes(email))) ?? null;
}

export class AcceptError extends Error {
  constructor(
    readonly code: "not-owner" | "blocked" | "changed" | "checking" | "not-mergeable" | "base-moved" | "failed",
  ) {
    super(code);
  }
}

export async function acceptProposal(options: {
  token: string;
  owner: string;
  repo: string;
  number: number;
  shownHeadSha: string;
  verifiedEmails: string[];
  name: string;
}): Promise<void> {
  const { token, owner, repo, number, shownHeadSha, verifiedEmails, name } = options;
  // Everything is worked out again here from GitHub, never from the page.
  const proposal = await getProposal(token, owner, repo, number);
  if (blockedReason(proposal)) throw new AcceptError("blocked");
  const email = acceptingEmail(proposal, verifiedEmails);
  if (!email) throw new AcceptError("not-owner");
  // The owner accepts what they were shown, never a newer version of it.
  if (proposal.headSha !== shownHeadSha) throw new AcceptError("changed");

  // GitHub works out whether it can merge a moment after a change; wait for it.
  let pull = await getPull(token, owner, repo, number);
  for (let attempt = 0; pull.mergeable === null && attempt < 4; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    pull = await getPull(token, owner, repo, number);
  }
  if (pull.mergeable === null) throw new AcceptError("checking");
  if (pull.mergeable !== true || !pull.merge_commit_sha) throw new AcceptError("not-mergeable");
  if (pull.head.sha !== shownHeadSha) throw new AcceptError("changed");

  const path = `/repos/${owner}/${repo}`;
  const branch = await api<{ object: { sha: string } }>(`${path}/git/ref/heads/${encodeURIComponent(pull.base.ref)}`, {
    token,
  });
  // GitHub's trial merge holds the merged files. Use it only if it was made
  // against the branch as it stands now.
  const trial = await api<{ tree: { sha: string }; parents: { sha: string }[] }>(
    `${path}/git/commits/${pull.merge_commit_sha}`,
    { token },
  );
  if (trial.parents[0]?.sha !== branch.object.sha) throw new AcceptError("base-moved");
  // And only if it merged the very version the owner was shown.
  if (trial.parents[1]?.sha !== shownHeadSha) throw new AcceptError("changed");

  try {
    const now = new Date().toISOString();
    const commit = await api<{ sha: string }>(`${path}/git/commits`, {
      token,
      method: "POST",
      body: JSON.stringify({
        message: `Accept proposal ${proposal.proposalId}: ${proposal.title}\n\nAccepted in GTM Base by the document owner (#${number}).`,
        tree: trial.tree.sha,
        parents: [branch.object.sha, pull.head.sha],
        author: { name, email, date: now },
      }),
    });
    // Not forced: if the branch moved in the meantime, GitHub refuses and nothing lands.
    await api(`${path}/git/refs/heads/${encodeURIComponent(pull.base.ref)}`, {
      token,
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha, force: false }),
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 422) throw new AcceptError("base-moved");
    throw new AcceptError("failed");
  }
}

export async function discardProposal(options: {
  token: string;
  owner: string;
  repo: string;
  number: number;
  reason: string;
  login: string;
  verifiedEmails: string[];
}): Promise<void> {
  const { token, owner, repo, number, reason, login, verifiedEmails } = options;
  const proposal = await getProposal(token, owner, repo, number); // only open GTM Base proposals
  if (!mayDiscard(proposal, login, verifiedEmails)) throw new DiscardError();
  const path = `/repos/${owner}/${repo}`;
  if (reason) {
    await api(`${path}/issues/${number}/comments`, {
      token,
      method: "POST",
      body: JSON.stringify({ body: `Discarded in GTM Base: ${reason}` }),
    });
  }
  await api(`${path}/pulls/${number}`, { token, method: "PATCH", body: JSON.stringify({ state: "closed" }) });
}

export class DiscardError extends Error {}

// The person who proposed it, or an owner of a document it changes.
export function mayDiscard(proposal: Proposal, login: string, verifiedEmails: string[]): boolean {
  if (proposal.author.toLowerCase() === login.toLowerCase()) return true;
  const mine = new Set(verifiedEmails.map((e) => e.toLowerCase()));
  return proposal.files.some((f) => f.ownedDocument && f.owners.some((o) => mine.has(o)));
}
