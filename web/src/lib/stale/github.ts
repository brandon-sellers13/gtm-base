import "server-only";
import { GitHubError, api } from "../github";
import { validRepo } from "../reader";
import { parseCorrectionsFile, Refused, Unreadable } from "./formats";
import { CONFIRMATIONS_DIR, CORRECTIONS_DIR, type CorrectionFacts, type Snapshot, contentHash } from "./rules";

// Builds the snapshot the moment-of-use rules read, from one base on GitHub,
// with the person's own token. It answers the same questions the plugin asks
// git, over GitHub's API:
//
// - who added each confirmation line: GraphQL blame on the default branch;
// - which commit first added each accepted record (the oldest commit that is
//   not a merge and adds it relative to its first parent), what else that
//   commit changed, and the record's listed context files as it left them;
// - who brought each record onto the main line: the newest commit on the
//   default branch's first-parent chain that changed it.
//
// Known difference: GitHub reports commit dates in UTC, where the plugin reads
// each author's local date, so an acceptance made near midnight local time can
// land a day apart. Commits the web app makes are UTC on both sides.

const FOLDERS = ["context/", "learning/changes/", "learning/corrections/", "work/confirmations/"];
const OLDER = ["work/changes/", "work/decisions/", "corrections/"];
const MAX_FILES = 400;
const MAX_COMMITS = 2000;

export class BaseUnavailable extends Error {}

type Tree = { tree: { path: string; type: string; sha: string }[]; truncated: boolean };

async function graphql<T>(token: string, query: string, variables: Record<string, unknown>): Promise<T> {
  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
    cache: "no-store",
  });
  if (!response.ok) throw new GitHubError(`GitHub GraphQL answered ${response.status}`, response.status);
  const body = (await response.json()) as { data?: T; errors?: { type?: string }[] };
  // A file that is not there at one commit is reported as NOT_FOUND next to
  // the data, and is an answer (null). Anything else is not.
  if (body.errors?.some((error) => error.type !== "NOT_FOUND") || !body.data) {
    throw new Unreadable("github-graphql-refused");
  }
  return body.data;
}

const quote = (text: string) => JSON.stringify(text);

async function readText(token: string, owner: string, repo: string, sha: string): Promise<string> {
  const blob = await api<{ content: string; encoding: string }>(`/repos/${owner}/${repo}/git/blobs/${sha}`, { token });
  return blob.encoding === "base64" ? Buffer.from(blob.content, "base64").toString("utf8") : blob.content;
}

async function inBatches<T, R>(items: T[], size: number, work: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += size) results.push(...(await Promise.all(items.slice(i, i + size).map(work))));
  return results;
}

// --- Who added each confirmation line -----------------------------------------

async function blameAll(
  token: string,
  owner: string,
  repo: string,
  head: string,
  paths: string[],
): Promise<Snapshot["confirmationAuthors"]> {
  const authors: Snapshot["confirmationAuthors"] = {};
  if (!paths.length) return authors;
  const fields = paths
    .map((path, i) => `b${i}: blame(path: ${quote(path)}) { ranges { startingLine endingLine commit { author { email } } } }`)
    .join("\n");
  const data = await graphql<{ repository: { object: Record<string, { ranges: { startingLine: number; endingLine: number; commit: { author: { email: string | null } } }[] } | null> } }>(
    token,
    `query($owner: String!, $name: String!, $oid: GitObjectID!) { repository(owner: $owner, name: $name) { object(oid: $oid) { ... on Commit { ${fields} } } } }`,
    { owner, name: repo, oid: head },
  );
  paths.forEach((path, i) => {
    const blame = data.repository.object[`b${i}`];
    if (!blame) throw new Unreadable("authors-unavailable");
    const lines: Record<string, string> = {};
    for (const range of blame.ranges) {
      const email = range.commit.author.email;
      if (!email) continue;
      for (let line = range.startingLine; line <= range.endingLine; line++) lines[String(line)] = email;
    }
    authors[path] = lines;
  });
  return authors;
}

// --- The history of each accepted record ----------------------------------------

type HistoryNode = {
  oid: string;
  author: { email: string | null; date: string | null };
  parents: { totalCount: number; nodes: { oid: string }[] };
  [file: `f${number}`]: { oid: string } | null;
};

async function recordFacts(
  token: string,
  owner: string,
  repo: string,
  head: string,
  records: { path: string; touched: string[] }[],
): Promise<Snapshot["corrections"]> {
  const facts: Snapshot["corrections"] = {};
  if (!records.length) return facts;
  const fileFields = records.map((r, i) => `f${i}: file(path: ${quote(r.path)}) { oid }`).join(" ");
  const nodes = new Map<string, HistoryNode>();
  let after: string | null = null;
  let seen = 0;
  for (;;) {
    const data: { repository: { object: { history: { pageInfo: { hasNextPage: boolean; endCursor: string }; nodes: HistoryNode[] } } } } =
      await graphql(
        token,
        `query($owner: String!, $name: String!, $oid: GitObjectID!, $after: String) { repository(owner: $owner, name: $name) { object(oid: $oid) { ... on Commit { history(first: 100, after: $after) { pageInfo { hasNextPage endCursor } nodes { oid author { email date } parents(first: 2) { totalCount nodes { oid } } ${fileFields} } } } } } }`,
        { owner, name: repo, oid: head, after },
      );
    const history = data.repository.object.history;
    for (const node of history.nodes) nodes.set(node.oid, node);
    seen += history.nodes.length;
    if (!history.pageInfo.hasNextPage) break;
    if (seen >= MAX_COMMITS) throw new Unreadable("history-too-long");
    after = history.pageInfo.endCursor;
  }

  const fileAt = (node: HistoryNode | undefined, i: number) => (node ? (node[`f${i}`]?.oid ?? null) : null);

  for (const [i, record] of records.entries()) {
    // The commit that first added it: the oldest commit, not a merge, holding
    // the record where its first parent did not (git log --diff-filter=A).
    let introducing: HistoryNode | null = null;
    for (const node of nodes.values()) {
      if (node.parents.totalCount > 1) continue;
      const parent = node.parents.nodes[0] ? nodes.get(node.parents.nodes[0].oid) : undefined;
      if (fileAt(node, i) && !fileAt(parent, i)) introducing = node; // history is newest first; keep the last (oldest)
    }
    // Who brought it onto the main line: the newest commit on the first-parent
    // chain whose record differs from its first parent's.
    let merged: HistoryNode | null = null;
    for (let node = nodes.get(head); node; ) {
      const parent = node.parents.nodes[0] ? nodes.get(node.parents.nodes[0].oid) : undefined;
      if (fileAt(node, i) !== fileAt(parent, i) && fileAt(node, i)) {
        merged = node;
        break;
      }
      node = parent;
    }
    let coModified: string[] = [];
    let hashAtCommit: string | null = null;
    if (introducing) {
      const commit = await api<{ files?: { filename: string }[] }>(`/repos/${owner}/${repo}/commits/${introducing.oid}`, { token });
      coModified = (commit.files ?? []).map((file) => file.filename);
      const listed = record.touched.filter((path) => typeof path === "string" && path.startsWith("context/"));
      if (listed.length) {
        try {
          const texts = await Promise.all(
            listed.map(async (path) => {
              const file = await api<{ content: string }>(
                `/repos/${owner}/${repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}?ref=${introducing!.oid}`,
                { token },
              );
              return Buffer.from(file.content, "base64").toString("utf8");
            }),
          );
          hashAtCommit = await contentHash(texts.join(""));
        } catch (error) {
          if (!(error instanceof GitHubError) || error.status === 401) throw error;
          hashAtCommit = null;
        }
      }
    }
    const day = merged?.author.date?.slice(0, 10) ?? null;
    facts[record.path] = {
      coModified,
      hashAtCommit,
      mergedBy: merged?.author.email ?? null,
      mergedOn: day && /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null,
    } satisfies CorrectionFacts;
  }
  return facts;
}

// --- The whole snapshot -----------------------------------------------------------

export async function snapshotOf(
  token: string,
  owner: string,
  repo: string,
  today: string,
): Promise<Snapshot & { branch: string }> {
  if (!validRepo(owner, repo)) throw new BaseUnavailable();
  let info: { default_branch: string };
  try {
    info = await api(`/repos/${owner}/${repo}`, { token });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) throw new BaseUnavailable();
    throw error;
  }
  const branch = await api<{ object: { sha: string } }>(
    `/repos/${owner}/${repo}/git/ref/heads/${encodeURIComponent(info.default_branch)}`,
    { token },
  );
  const head = branch.object.sha;
  const tree = await api<Tree>(`/repos/${owner}/${repo}/git/trees/${head}?recursive=1`, { token });
  if (tree.truncated) throw new Unreadable("tree-truncated");
  const wanted = tree.tree.filter(
    (entry) => entry.type === "blob" && [...FOLDERS, ...OLDER].some((folder) => entry.path.startsWith(folder)),
  );
  if (wanted.length > MAX_FILES) throw new Unreadable("base-too-large");

  const files: Record<string, string> = {};
  await inBatches(wanted, 8, async (entry) => {
    // The older layout's folders only need to be seen, never read.
    files[entry.path] = OLDER.some((folder) => entry.path.startsWith(folder)) ? "" : await readText(token, owner, repo, entry.sha);
  });

  const confirmations = Object.keys(files).filter(
    (path) => path.startsWith(CONFIRMATIONS_DIR + "/") && !path.slice(CONFIRMATIONS_DIR.length + 1).includes("/") && path.endsWith(".md"),
  );
  const records: { path: string; touched: string[] }[] = [];
  for (const path of Object.keys(files).sort()) {
    if (!path.startsWith(CORRECTIONS_DIR + "/") || path.slice(CORRECTIONS_DIR.length + 1).includes("/") || !path.endsWith(".md")) continue;
    try {
      records.push({ path, touched: parseCorrectionsFile(files[path]).touchedPaths });
    } catch (error) {
      if (!(error instanceof Refused)) throw error;
    }
  }

  const [confirmationAuthors, corrections] = await Promise.all([
    blameAll(token, owner, repo, head, confirmations),
    recordFacts(token, owner, repo, head, records),
  ]);
  return { today, files, confirmationAuthors, corrections, branch: info.default_branch };
}

// An open proposal, prepared for this change and touching this document,
// is the web side of the plugin's "a change for it is already prepared".
export async function fixIsReady(token: string, owner: string, repo: string, entryId: string, path: string): Promise<boolean> {
  const pulls = await api<{ number: number; body: string | null }[]>(`/repos/${owner}/${repo}/pulls?state=open&per_page=100`, { token });
  const MARKER = /^gtm-base proposal (stg-[0-9a-f]+) entry (\S+) source (\S+)\s*$/m;
  for (const pull of pulls) {
    const marker = (pull.body ?? "").match(MARKER);
    if (!marker || marker[2] !== entryId) continue;
    const changed = await api<{ filename: string }[]>(`/repos/${owner}/${repo}/pulls/${pull.number}/files?per_page=100`, { token });
    if (changed.some((file) => file.filename === path)) return true;
  }
  return false;
}
