import "server-only";
import { api, GitHubError } from "./github";
import { frontMatter, validRepo } from "./reader";
import { baseOwnerEmails } from "./team";

// Changes that reached a base without an approval. A base whose main line is
// protected (mainRule.ts) refuses them at GitHub, apart from what GTM Base and
// the repository's admins write directly. On a private repository on a free plan,
// where GitHub will not protect it, anyone with push access can commit
// straight to the main branch; this finds those commits so the base's owner
// can keep or undo each one.
//
// A commit on the main line (first parents only) is fine when it is:
// - the merge of a GTM Base proposal (GitHub records the accept commit as the
//   pull request's merge commit) authored with an owner's email, which is the
//   plugin's own rule; a teammate merging their own proposal on GitHub is listed;
// - part of the base's history from before it was shared (committed before
//   the repository existed, or in its first two minutes, which covers GitHub's
//   first commit and the app's template commit);
// - confirmation lines only, written by the owner of the document they confirm;
// - a keep or undo: a commit updating the review record, written by the base's
//   owner as the base stood just before it;
// - already answered (kept or undone) in that record.
// Everything else is listed. This catches mistakes; it is not a lock, because
// a teammate with push access could also write the record. The lock is the
// protection mainRule.ts puts on the main line, which GitHub enforces on a
// private repository only on its paid plans.

export const REVIEW_FILE = "work/reviewed-changes.md";
const REVIEW_HEADER =
  "# Changes that reached the base without an approval, and what the owner decided.\n" +
  "# One line per decision, added at the end and never edited.\n";
const BOOKKEEPING = (path: string) => path.startsWith("work/confirmations/");
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
  commit: { message: string; author: { name: string; email: string; date: string }; committer: { date: string } };
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

async function ownersAt(token: string, owner: string, repo: string, path: string, ref: string): Promise<string[]> {
  try {
    const file = await api<{ content: string }>(
      `/repos/${owner}/${repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}?ref=${encodeURIComponent(ref)}`,
      { token },
    );
    const value = frontMatter(Buffer.from(file.content, "base64").toString("utf8")).fields.owner;
    return (Array.isArray(value) ? value : value ? [value] : []).map((e) => e.toLowerCase());
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) return [];
    throw error;
  }
}

const OWNED = (path: string) =>
  ["context/", "access/", "standards/", "skills/"].some((p) => path.startsWith(p)) && path.endsWith(".md");

// Whether this commit's author owns what it touches, read as the base stood just
// before it: every owned document it changes (a new one: the map's owner), and
// for confirmation lines, the document each confirms.
async function authoredByOwner(token: string, owner: string, repo: string, c: FullCommit): Promise<boolean> {
  const email = c.commit.author.email.toLowerCase();
  const before = c.parents[0]?.sha;
  if (!before) return false;
  const mapOwners = await ownersAt(token, owner, repo, "context/map.md", before);
  for (const file of c.files ?? []) {
    let owners: string[] | null = null;
    if (file.filename.startsWith("work/confirmations/")) {
      const confirmed = file.filename.slice("work/confirmations/".length).replace(/--/g, "/");
      owners = await ownersAt(token, owner, repo, confirmed, before);
    } else if (OWNED(file.filename)) {
      owners = file.status === "added" ? mapOwners : await ownersAt(token, owner, repo, file.filename, before);
    }
    if (owners !== null && !owners.includes(email)) return false;
  }
  return true;
}

async function authoredByBaseOwner(token: string, owner: string, repo: string, c: FullCommit): Promise<boolean> {
  const before = c.parents[0]?.sha;
  if (!before) return false;
  return (await ownersAt(token, owner, repo, "context/map.md", before)).includes(c.commit.author.email.toLowerCase());
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
  let c: ListedCommit | undefined = listed[0];
  while (c && mainLine.length < LOOK_BACK) {
    mainLine.push(c);
    const parent: string | undefined = c.parents[0]?.sha;
    if (!parent) break;
    // A first parent beyond the fetched page (after a merge that brought in many
    // commits) is fetched on its own, so the walk does not stop early.
    c = bySha.get(parent) ?? (await api<ListedCommit>(`/repos/${owner}/${repo}/commits/${parent}`, { token }));
  }

  const candidates = mainLine.filter((m) => !done.has(m.sha) && Date.parse(m.commit.committer.date) > sharedFrom);
  const full = await inBatches(candidates, 8, (m) => api<FullCommit>(`/repos/${owner}/${repo}/commits/${m.sha}`, { token }));

  const flagged: FullCommit[] = [];
  for (const commit of full) {
    const files = commit.files ?? [];
    if (files.length === 0) continue;
    const proposalMerge = accepted.has(commit.sha);
    const bookkeeping = files.every((f) => BOOKKEEPING(f.filename));
    // A keep or an undo: it updates the review record and the base's owner wrote it.
    const reviewAction = files.some((f) => f.filename === REVIEW_FILE);
    if (reviewAction && (await authoredByBaseOwner(token, owner, repo, commit))) continue;
    // An accepted proposal or bookkeeping counts only when an owner wrote it.
    if ((proposalMerge || bookkeeping) && (await authoredByOwner(token, owner, repo, commit))) continue;
    flagged.push(commit);
  }

  const items = flagged.map((c) => ({
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
  author: { name: string; email: string },
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
    body: JSON.stringify({
      message,
      tree: newTree.sha,
      parents: [tipSha],
      // Signed with the owner's own address, so the record holds up under the
      // same rule as everything else: bookkeeping counts when an owner wrote it.
      author: { ...author, date: new Date().toISOString() },
    }),
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
  const owners = await baseOwnerEmails(token, owner, repo);
  const email = emails.map((e) => e.toLowerCase()).find((e) => owners.includes(e));
  if (!email) throw new ReviewError("not-owner");
  const { branch, items } = await listUnapproved(token, owner, repo);
  const item = items.find((i) => i.sha === sha);
  if (!item) throw new ReviewError("not-listed");
  const tip = await api<{ object: { sha: string } }>(`/repos/${owner}/${repo}/git/ref/heads/${encodeURIComponent(branch)}`, {
    token,
  });
  const review = await readReviewFile(token, owner, repo, tip.object.sha);
  return { branch, item, tipSha: tip.object.sha, reviewText: review.text || REVIEW_HEADER, email };
}

export async function keepChange(options: { token: string; owner: string; repo: string; sha: string; login: string; emails: string[] }) {
  const { token, owner, repo, sha, login, emails } = options;
  const { branch, item, tipSha, reviewText, email } = await prepare(token, owner, repo, sha, emails);
  await commitOnTop(
    token,
    owner,
    repo,
    branch,
    tipSha,
    [{ path: REVIEW_FILE, mode: "100644", type: "blob", content: reviewText + reviewLine({ sha, answer: "kept", by: login }) }],
    `Keep a change that skipped approval: ${item.message.slice(0, 60)}\n\nKept in GTM Base by ${login}.`,
    { name: login, email },
  );
}

export async function undoChange(options: { token: string; owner: string; repo: string; sha: string; login: string; emails: string[] }) {
  const { token, owner, repo, sha, login, emails } = options;
  const { branch, item, tipSha, reviewText, email } = await prepare(token, owner, repo, sha, emails);
  if (!item.undoable) throw new ReviewError("not-undoable");
  const path = `/repos/${owner}/${repo}`;

  const commit = await api<FullCommit>(`${path}/commits/${sha}`, { token });
  const parent = commit.parents[0].sha;
  // Both trees are read whole, so each file's exact content and mode are known.
  const treeOf = async (ref: string) => {
    const c = await api<{ tree: { sha: string } }>(`${path}/git/commits/${ref}`, { token });
    const t = await api<{ tree: { path: string; mode: string; type: string; sha: string }[]; truncated: boolean }>(
      `${path}/git/trees/${c.tree.sha}?recursive=1`,
      { token },
    );
    if (t.truncated) throw new ReviewError("not-undoable");
    return new Map(t.tree.filter((e) => e.type === "blob").map((e) => [e.path, { sha: e.sha, mode: e.mode }]));
  };
  const [nowTree, beforeTree] = await Promise.all([treeOf(tipSha), treeOf(parent)]);
  const blobAt = async (filePath: string, ref: string) => (ref === tipSha ? nowTree : beforeTree).get(filePath) ?? null;

  const tree: { path: string; mode: string; type: string; sha: string | null }[] = [];
  for (const file of commit.files ?? []) {
    // Never undo over a later change: the file must still be exactly as that commit left it.
    const now = await blobAt(file.filename, tipSha);
    const leftAs = file.status === "removed" ? null : file.sha;
    if ((now?.sha ?? null) !== leftAs) throw new ReviewError("changed-since");
    const before = await blobAt(file.filename, parent);
    tree.push({ path: file.filename, mode: before?.mode ?? now?.mode ?? "100644", type: "blob", sha: before?.sha ?? null });
    if (file.status === "renamed" && file.previous_filename) {
      const old = await blobAt(file.previous_filename, parent);
      if (old) tree.push({ path: file.previous_filename, mode: old.mode, type: "blob", sha: old.sha });
    }
  }
  // The undo and its record are one commit, signed by the owner; it counts as the
  // owner's own review action, judged by who owned the base just before it.
  await commitOnTop(
    token,
    owner,
    repo,
    branch,
    tipSha,
    [
      ...tree,
      { path: REVIEW_FILE, mode: "100644", type: "blob", content: reviewText + reviewLine({ sha, answer: "undone", by: login }) },
    ],
    `Undo a change that skipped approval: ${item.message.slice(0, 60)}\n\nUndone in GTM Base by ${login}. Reverts ${sha}.`,
    { name: login, email },
  );
}
