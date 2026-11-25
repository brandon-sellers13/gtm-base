import "server-only";
import { api, GitHubError } from "./github";
import { validRepo } from "./reader";
import { isBaseOwner } from "./team";

// Changes that reached a base without an approval. On GitHub's free plan
// anyone with push access can commit straight to the main branch; this finds
// those commits so the base's owner can keep or undo each one.
//
// A commit on the main line (first parents only) is fine when it is:
// - the merge of an accepted GTM Base proposal (GitHub records the accept
//   commit as the pull request's merge commit);
// - part of the base's history from before it was shared (committed before
//   the repository existed, or in its first two minutes, which covers GitHub's
//   first commit and the app's template commit);
// - bookkeeping only: owners' confirmation lines, or this review's own record;
// - already answered (kept or undone) in that record.
// Everything else is listed. This catches mistakes; it is not a lock, because
// a teammate with push access could also write the record. The real lock is
// branch protection, which GitHub sells on its paid plans.

export const REVIEW_FILE = "work/reviewed-changes.md";
const REVIEW_HEADER =
  "# Changes that reached the base without an approval, and what the owner decided.\n" +
  "# One line per decision, added at the end and never edited.\n";
const BOOKKEEPING = (path: string) => path.startsWith("work/confirmations/") || path === REVIEW_FILE;
const MARKER = /^gtm-base proposal stg-[0-9a-f]+ entry \S+ source \S+\s*$/m;
const LOOK_BACK = 50; // newest commits on the main line that are looked at
const SHARED_GRACE_MS = 2 * 60 * 1000;

export type Unapproved = {
  sha: string;
  message: string;
  author: string;
  date: string;
  files: { path: string; status: string }[];
  undoable: boolean;
};

type ListedCommit = {
  sha: string;
  parents: { sha: string }[];
  commit: { message: string; author: { name: string; date: string }; committer: { date: string } };
};
type FullCommit = ListedCommit & {
  files?: { filename: string; status: string; sha: string | null; previous_filename?: string }[];
};

async function inBatches<T, R>(items: T[], size: number, work: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += size) results.push(...(await Promise.all(items.slice(i, i + size).map(work))));
  return results;
}

async function readReviewFile(token: string, owner: string, repo: string, ref: string) {
  try {
    const file = await api<{ content: string; sha: string }>(
      `/repos/${owner}/${repo}/contents/${REVIEW_FILE}?ref=${encodeURIComponent(ref)}`,
      { token },
    );
    return { text: Buffer.from(file.content, "base64").toString("utf8"), sha: file.sha };
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) return { text: "", sha: null };
    throw error;
  }
}

function answered(text: string): Set<string> {
  const shas = new Set<string>();
  for (const line of text.split("\n")) {
    if (!line.startsWith("date=")) continue;
    for (const pair of line.split(" ")) {
      const [key, value] = pair.split("=");
      if ((key === "sha" || key === "undo") && value && /^[0-9a-f]{40}$/.test(value)) shas.add(value);
    }
  }
  return shas;
}

export async function listUnapproved(token: string, owner: string, repo: string) {
  if (!validRepo(owner, repo)) return { branch: "main", items: [] as Unapproved[] };
  const info = await api<{ default_branch: string; created_at: string }>(`/repos/${owner}/${repo}`, { token });
  const branch = info.default_branch;
  const sharedFrom = Date.parse(info.created_at) + SHARED_GRACE_MS;

  const [listed, closed, review] = await Promise.all([
    api<ListedCommit[]>(`/repos/${owner}/${repo}/commits?sha=${encodeURIComponent(branch)}&per_page=100`, { token }),
    api<{ merged_at: string | null; merge_commit_sha: string | null; body: string | null }[]>(
      `/repos/${owner}/${repo}/pulls?state=closed&per_page=100`,
      { token },
    ),
    readReviewFile(token, owner, repo, branch),
  ]);

  const accepted = new Set(
    closed.filter((p) => p.merged_at && p.merge_commit_sha && MARKER.test(p.body ?? "")).map((p) => p.merge_commit_sha!),
  );
  const done = answered(review.text);

  // Walk the main line from the tip, first parents only.
  const bySha = new Map(listed.map((c) => [c.sha, c]));
  const mainLine: ListedCommit[] = [];
  for (let c = listed[0]; c && mainLine.length < LOOK_BACK; c = bySha.get(c.parents[0]?.sha ?? "")!) mainLine.push(c);

  const candidates = mainLine.filter(
    (c) => !accepted.has(c.sha) && !done.has(c.sha) && Date.parse(c.commit.committer.date) > sharedFrom,
  );
  const full = await inBatches(candidates, 8, (c) => api<FullCommit>(`/repos/${owner}/${repo}/commits/${c.sha}`, { token }));

  const items = full
    .filter((c) => (c.files ?? []).length > 0 && !(c.files ?? []).every((f) => BOOKKEEPING(f.filename)))
    .map((c) => ({
      sha: c.sha,
      message: c.commit.message.split("\n")[0],
      author: c.commit.author.name,
      date: c.commit.author.date.slice(0, 10),
      files: (c.files ?? []).map((f) => ({ path: f.filename, status: f.status })),
      // Undo here handles ordinary commits only; a merge is undone on GitHub.
      undoable: c.parents.length === 1 && (c.files ?? []).length <= 100,
    }));
  return { branch, items };
}

// --- Keep and undo -----------------------------------------------------------

export class ReviewError extends Error {
  constructor(readonly code: "not-owner" | "not-listed" | "changed-since" | "not-undoable" | "base-moved" | "failed") {
    super(code);
  }
}

function reviewLine(fields: Record<string, string>) {
  return `date=${new Date().toISOString().slice(0, 10)} ${Object.entries(fields)
    .map(([k, v]) => `${k}=${v}`)
    .join(" ")}\n`;
}

async function commitOnTop(
  token: string,
  owner: string,
  repo: string,
  branch: string,
  tipSha: string,
  tree: { path: string; mode: string; type: string; sha?: string | null; content?: string }[],
  message: string,
): Promise<string> {
  const path = `/repos/${owner}/${repo}`;
  const tip = await api<{ tree: { sha: string } }>(`${path}/git/commits/${tipSha}`, { token });
  const newTree = await api<{ sha: string }>(`${path}/git/trees`, {
    token,
    method: "POST",
    body: JSON.stringify({ base_tree: tip.tree.sha, tree }),
  });
  const commit = await api<{ sha: string }>(`${path}/git/commits`, {
    token,
    method: "POST",
    body: JSON.stringify({ message, tree: newTree.sha, parents: [tipSha] }),
  });
  try {
    // Not forced: if the branch moved in the meantime, nothing lands.
    await api(`${path}/git/refs/heads/${encodeURIComponent(branch)}`, {
      token,
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha, force: false }),
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 422) throw new ReviewError("base-moved");
    throw error;
  }
  return commit.sha;
}

async function prepare(token: string, owner: string, repo: string, sha: string, emails: string[]) {
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new ReviewError("not-listed");
  if (!(await isBaseOwner(token, owner, repo, emails))) throw new ReviewError("not-owner");
  const { branch, items } = await listUnapproved(token, owner, repo);
  const item = items.find((i) => i.sha === sha);
  if (!item) throw new ReviewError("not-listed");
  const tip = await api<{ object: { sha: string } }>(`/repos/${owner}/${repo}/git/ref/heads/${encodeURIComponent(branch)}`, {
    token,
  });
  const review = await readReviewFile(token, owner, repo, tip.object.sha);
  return { branch, item, tipSha: tip.object.sha, reviewText: review.text || REVIEW_HEADER };
}

export async function keepChange(options: { token: string; owner: string; repo: string; sha: string; login: string; emails: string[] }) {
  const { token, owner, repo, sha, login, emails } = options;
  const { branch, item, tipSha, reviewText } = await prepare(token, owner, repo, sha, emails);
  await commitOnTop(
    token,
    owner,
    repo,
    branch,
    tipSha,
    [{ path: REVIEW_FILE, mode: "100644", type: "blob", content: reviewText + reviewLine({ sha, answer: "kept", by: login }) }],
    `Keep a change that skipped approval: ${item.message.slice(0, 60)}\n\nKept in GTM Base by ${login}.`,
  );
}

export async function undoChange(options: { token: string; owner: string; repo: string; sha: string; login: string; emails: string[] }) {
  const { token, owner, repo, sha, login, emails } = options;
  const { branch, item, tipSha, reviewText } = await prepare(token, owner, repo, sha, emails);
  if (!item.undoable) throw new ReviewError("not-undoable");
  const path = `/repos/${owner}/${repo}`;

  const commit = await api<FullCommit>(`${path}/commits/${sha}`, { token });
  const parent = commit.parents[0].sha;
  const blobAt = async (filePath: string, ref: string): Promise<{ sha: string; mode: string } | null> => {
    const dir = filePath.includes("/") ? filePath.slice(0, filePath.lastIndexOf("/")) : "";
    const name = filePath.slice(filePath.lastIndexOf("/") + 1);
    try {
      const listing = await api<{ name: string; sha: string; type: string }[]>(
        `${path}/contents/${dir.split("/").map(encodeURIComponent).join("/")}?ref=${encodeURIComponent(ref)}`,
        { token },
      );
      const entry = Array.isArray(listing) ? listing.find((e) => e.name === name && e.type === "file") : null;
      return entry ? { sha: entry.sha, mode: "100644" } : null;
    } catch (error) {
      if (error instanceof GitHubError && error.status === 404) return null;
      throw error;
    }
  };

  const tree: { path: string; mode: string; type: string; sha: string | null }[] = [];
  for (const file of commit.files ?? []) {
    // Never undo over a later change: the file must still be exactly as that commit left it.
    const now = await blobAt(file.filename, tipSha);
    const leftAs = file.status === "removed" ? null : file.sha;
    if ((now?.sha ?? null) !== leftAs) throw new ReviewError("changed-since");
    const before = await blobAt(file.filename, parent);
    tree.push({ path: file.filename, mode: "100644", type: "blob", sha: before?.sha ?? null });
    if (file.status === "renamed" && file.previous_filename) {
      const old = await blobAt(file.previous_filename, parent);
      if (old) tree.push({ path: file.previous_filename, mode: "100644", type: "blob", sha: old.sha });
    }
  }
  // The undo lands first, then a record-only commit naming both the change and
  // its undo, so neither is listed again.
  const undoSha = await commitOnTop(
    token,
    owner,
    repo,
    branch,
    tipSha,
    tree,
    `Undo a change that skipped approval: ${item.message.slice(0, 60)}\n\nUndone in GTM Base by ${login}. Reverts ${sha}.`,
  );
  await commitOnTop(
    token,
    owner,
    repo,
    branch,
    undoSha,
    [
      {
        path: REVIEW_FILE,
        mode: "100644",
        type: "blob",
        content: reviewText + reviewLine({ sha, answer: "undone", by: login, undo: undoSha }),
      },
    ],
    `Record the undo of ${sha.slice(0, 7)}`,
  );
}
