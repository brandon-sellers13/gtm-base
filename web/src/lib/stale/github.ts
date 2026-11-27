import "server-only";
import { GitHubError, api } from "../github";
import { validRepo } from "../reader";
import { classify, parseCorrectionsFile, Refused, Unreadable } from "./formats";
import {
  CONFIRMATIONS_DIR,
  CORRECTIONS_DIR,
  type ChainNode,
  type CorrectionFacts,
  LEGACY_CORRECTIONS_DIR,
  type SavedRevision,
  type Snapshot,
  contentHash,
  firstAddedIn,
} from "./rules";

// Builds the snapshot the moment-of-use rules read, from one base on GitHub,
// with the person's own token. It answers the same questions the plugin asks
// git, over GitHub's API:
//
// - who added each confirmation line, and in which revision: GraphQL blame;
// - the map and the documents as each of those revisions saved them, which
//   decide whether that person could confirm or accept then (authority.py);
// - which commit first added each accepted record (the oldest commit that is
//   not a merge and adds it relative to its first parent), what else that
//   commit changed, and the record's listed context files as it left them;
// - who brought each record onto the main line: the newest commit on the
//   default branch's first-parent chain that changed it.
//
// Known difference: GitHub reports commit dates in UTC, where the plugin reads
// each author's local date, so an acceptance made near midnight local time can
// land a day apart. Commits the web app makes are UTC on both sides.

const FOLDERS = ["context/", "standards/", "access/", "learning/changes/", "learning/corrections/", "work/confirmations/"];
const OLDER = ["work/changes/", "work/decisions/", "corrections/"];
const MAX_FILES = 400;
const MAX_COMMITS = 2000;

export class BaseUnavailable extends Error {}

type Tree = { tree: { path: string; mode: string; type: string; sha: string }[]; truncated: boolean };

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
    .map((path, i) => `b${i}: blame(path: ${quote(path)}) { ranges { startingLine endingLine commit { oid author { email } } } }`)
    .join("\n");
  const data = await graphql<{
    repository: {
      object: Record<
        string,
        { ranges: { startingLine: number; endingLine: number; commit: { oid: string; author: { email: string | null } } }[] } | null
      >;
    };
  }>(
    token,
    `query($owner: String!, $name: String!, $oid: GitObjectID!) { repository(owner: $owner, name: $name) { object(oid: $oid) { ... on Commit { ${fields} } } } }`,
    { owner, name: repo, oid: head },
  );
  paths.forEach((path, i) => {
    const blame = data.repository.object[`b${i}`];
    if (!blame) throw new Unreadable("authors-unavailable");
    const lines: Snapshot["confirmationAuthors"][string] = {};
    for (const range of blame.ranges) {
      const email = range.commit.author.email;
      if (!email) continue;
      for (let line = range.startingLine; line <= range.endingLine; line++) {
        lines[String(line)] = { email, revision: range.commit.oid };
      }
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
  [file: `f${number}` | `g${number}` | `w${number}`]: { oid: string } | null;
};

// Each commit's parents, for every commit the history walk saw; null for a
// commit with more parents than the walk read (an octopus merge), which a
// caller treats as history it cannot read.
export type Parents = Record<string, string[] | null>;

// The main line, newest first, and for each watched path (the map and each
// skill's folder) every commit on it whose copy differs from its first
// parent's, newest first: the plugin's `git log --first-parent -- <path>`.
export type MainLine = { mainLine: string[]; changes: Record<string, string[]> };

async function recordFacts(
  token: string,
  owner: string,
  repo: string,
  head: string,
  records: { path: string; touched: string[] }[],
  parents: Parents,
  watched: string[],
  line: MainLine,
): Promise<Snapshot["corrections"]> {
  const facts: Snapshot["corrections"] = {};
  if (!records.length) return facts;
  const fileFields = [
    ...records.map((r, i) => `f${i}: file(path: ${quote(r.path)}) { oid }`),
    ...records.map((r, i) => `g${i}: file(path: ${quote(`${LEGACY_CORRECTIONS_DIR}/${r.path.split("/").pop()}`)}) { oid }`),
    ...watched.map((path, i) => `w${i}: file(path: ${quote(path)}) { oid }`),
  ].join(" ");
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
  for (const node of nodes.values()) {
    parents[node.oid] = node.parents.totalCount > node.parents.nodes.length ? null : node.parents.nodes.map((p) => p.oid);
  }

  const fileAt = (node: HistoryNode | undefined, i: number) => (node ? (node[`f${i}`]?.oid ?? null) : null);
  const watchedAt = (node: HistoryNode | undefined, i: number) => (node ? (node[`w${i}`]?.oid ?? null) : null);

  // The main line, and where each watched path changed along it. A skill's
  // folder the head holds must show an id at the head, or the walk did not
  // read it: it is then left out, and serving that skill is refused as
  // unreadable (skills.ts, changedSince), while every other tool goes on.
  for (let node = nodes.get(head); node; ) {
    line.mainLine.push(node.oid);
    const first = node.parents.nodes[0]?.oid;
    if (first && !nodes.has(first)) {
      // A main line the walk did not reach the root of cannot say where the
      // map was first saved, so it judges no approval at all.
      line.mainLine.length = 0;
      break;
    }
    node = first ? nodes.get(first) : undefined;
  }
  for (const [i, path] of watched.entries()) {
    if (path.startsWith("skills/") && !watchedAt(nodes.get(head), i)) continue;
    line.changes[path] = line.mainLine.filter((oid) => {
      const node = nodes.get(oid)!;
      const parent = node.parents.nodes[0] ? nodes.get(node.parents.nodes[0].oid) : undefined;
      return watchedAt(node, i) !== watchedAt(parent, i);
    });
  }

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
      // base_reader._context_paths_of: context files, standards and the source map.
      const listed = record.touched.filter((path) => {
        if (typeof path !== "string") return false;
        const kind = classify(path);
        return path.startsWith("context/") || kind === "standard" || kind === "stack";
      });
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
    // What the commit that first brought it onto the main line changed,
    // compared with its first parent (base_reader: the oldest first-parent
    // commit that added it, then git show --diff-merges=first-parent). A list
    // GitHub cuts short counts as changing nothing, so the record then settles
    // nothing.
    // The commit that first added it on the main line under either of its
    // names (skill_install.first_added).
    const legacy = `${LEGACY_CORRECTIONS_DIR}/${record.path.split("/").pop()}`;
    const chain: ChainNode[] = line.mainLine.map((oid) => {
      const node = nodes.get(oid)!;
      return {
        oid,
        email: node.author.email,
        day: node.author.date?.slice(0, 10) ?? null,
        names: { [record.path]: fileAt(node, i), [legacy]: node[`g${i}`]?.oid ?? null },
      };
    });
    const firstAdded = firstAddedIn(chain);
    const firstIn: HistoryNode | null = firstAdded ? nodes.get(firstAdded.oid)! : null;
    let acceptedPaths: string[] | null = null;
    if (merged && firstIn) {
      const first = firstIn.parents.nodes[0]?.oid;
      const shown = first
        ? await api<{ files?: { filename: string }[] }>(`/repos/${owner}/${repo}/compare/${first}...${firstIn.oid}`, { token })
        : await api<{ files?: { filename: string }[] }>(`/repos/${owner}/${repo}/commits/${firstIn.oid}`, { token });
      const names = (shown.files ?? []).map((file) => file.filename);
      acceptedPaths = names.length >= 300 ? [] : names;
    }
    const day = merged?.author.date?.slice(0, 10) ?? null;
    const addedDay = firstIn?.author.date?.slice(0, 10) ?? null;
    facts[record.path] = {
      addedBy: firstIn?.author.email ?? null,
      addedOn: addedDay && /^\d{4}-\d{2}-\d{2}$/.test(addedDay) ? addedDay : null,
      addedIn: firstIn?.oid ?? null,
      acceptedPaths,
      coModified,
      hashAtCommit,
      mergedBy: merged?.author.email ?? null,
      mergedOn: day && /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null,
      mergedIn: merged?.oid ?? null,
    } satisfies CorrectionFacts;
  }
  return facts;
}

// --- The map and documents as each revision saved them -----------------------------

async function savedRevisions(
  token: string,
  owner: string,
  repo: string,
  revisions: string[],
  documents: string[],
): Promise<Snapshot["revisions"]> {
  const saved: Snapshot["revisions"] = {};
  const paths = ["context/map.md", ...documents];
  const blob = (path: string, i: number) => `f${i}: file(path: ${quote(path)}) { object { ... on Blob { text } } }`;
  for (let at = 0; at < revisions.length; at += 10) {
    const batch = revisions.slice(at, at + 10);
    const fields = batch
      .map((oid, j) => `c${j}: object(oid: ${quote(oid)}) { ... on Commit { ${paths.map(blob).join(" ")} } }`)
      .join("\n");
    const data = await graphql<{
      repository: Record<string, Record<string, { object: { text: string | null } | null } | null> | null>;
    }>(token, `query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { ${fields} } }`, {
      owner,
      name: repo,
    });
    batch.forEach((oid, j) => {
      const commit = data.repository[`c${j}`];
      if (!commit) throw new Unreadable("authority-unavailable");
      const text = (i: number) => commit[`f${i}`]?.object?.text ?? null;
      const entry: SavedRevision = { map: text(0), documents: {} };
      documents.forEach((path, i) => {
        entry.documents[path] = text(i + 1);
      });
      saved[oid] = entry;
    });
  }
  return saved;
}

// --- The whole snapshot -----------------------------------------------------------

// One entry of the main line's tree under `skills/`, as GitHub lists it: the
// mode tells a plain file (100644, 100755) from a link (120000), and the type
// a folder ("tree") from a file ("blob") or another repository ("commit").
export type TreeEntry = { path: string; mode: string; type: string; sha: string };

export type BaseSnapshot = Snapshot & MainLine & { branch: string; head: string; skillTree: TreeEntry[]; parents: Parents; links: string[] };

export async function snapshotOf(token: string, owner: string, repo: string, today: string): Promise<BaseSnapshot> {
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

  const parents: Parents = {};
  const line: MainLine = { mainLine: [], changes: {} };
  const watched = [
    "context/map.md",
    CORRECTIONS_DIR,
    LEGACY_CORRECTIONS_DIR,
    ...tree.tree
      .filter((entry) => entry.type === "tree" && entry.path.startsWith("skills/") && !entry.path.slice("skills/".length).includes("/"))
      .map((entry) => entry.path)
      .sort(),
  ];
  const [confirmationAuthors, corrections] = await Promise.all([
    blameAll(token, owner, repo, head, confirmations),
    recordFacts(token, owner, repo, head, records, parents, watched, line),
  ]);
  // The skills folder is only listed here; a skill's files are read when a
  // skill is served (connector/skills.ts), never as documents.
  const skillTree = tree.tree
    .filter((entry) => entry.path === "skills" || entry.path.startsWith("skills/"))
    .map(({ path, mode, type, sha }) => ({ path, mode, type, sha }));
  // Links among the files read above, which a skill's folder declaration never
  // hands on (the plugin's runner follows no link).
  const links = wanted.filter((entry) => entry.mode === "120000").map((entry) => entry.path);
  // Every revision a confirmation or an acceptance came from, with the map
  // and every document as that revision held them.
  const revisions = new Set<string>();
  for (const lines of Object.values(confirmationAuthors)) for (const { revision } of Object.values(lines)) revisions.add(revision);
  for (const facts of Object.values(corrections)) if (facts.mergedIn) revisions.add(facts.mergedIn);
  const documents = [
    ...new Set([
      ...Object.keys(files).filter((path) => {
        const kind = classify(path);
        return kind === "context" || kind === "standard" || kind === "stack";
      }),
      ...records.flatMap((record) => record.touched.filter((path) => typeof path === "string")),
    ]),
  ].sort();
  const saved = await savedRevisions(token, owner, repo, [...revisions].sort(), documents);
  return {
    today,
    files,
    confirmationAuthors,
    corrections,
    revisions: saved,
    branch: info.default_branch,
    head,
    skillTree,
    parents,
    links,
    ...line,
  };
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
