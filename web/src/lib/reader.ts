import "server-only";
import { api, GitHubError } from "./github";

// Reads one base straight from its repository with the person's own GitHub
// token, so they only ever see what GitHub already lets them see. Nothing is
// stored. The app shows the facts the plugin wrote (owner, confirmation lines,
// context changes); whether a document is out of date stays the plugin's call.

export type Part = { key: string; title: string; blurb: string };

// The five CLASS parts, plus the approvals folder, in reading order.
export const PARTS: Part[] = [
  { key: "context", title: "Context", blurb: "What is true about the business." },
  { key: "learning", title: "Learning", blurb: "How the base gets better: context changes, corrections, lessons." },
  { key: "access", title: "Access", blurb: "Where the work comes from and where it goes." },
  { key: "skills", title: "Skills", blurb: "The jobs the AI can run on this base." },
  { key: "standards", title: "Standard", blurb: "What good work looks like for each job." },
  { key: "work", title: "Approvals", blurb: "The owners' confirmations." },
];

const NAME = /^[A-Za-z0-9._-]{1,100}$/;
export const validRepo = (owner: string, repo: string) =>
  NAME.test(owner) && NAME.test(repo) && !owner.startsWith(".") && !repo.startsWith(".");

export type Doc = {
  path: string;
  part: string; // a PARTS key, or "other"
  title: string;
  owner: string | null;
  kind: string | null;
  status: string | null;
  lastConfirmed: { date: string; trigger: string } | null;
  openChanges: Change[];
};

export type Change = {
  path: string;
  id: string;
  happenedOn: string | null;
  summary: string;
  affects: string[];
  status: string | null;
};

export type BaseView = {
  owner: string;
  repo: string;
  htmlUrl: string;
  branch: string;
  docs: Doc[];
  changes: Change[];
  truncated: boolean; // GitHub could not list the whole repository at once
};

export class BaseNotFound extends Error {}

export function docHref(owner: string, repo: string, path: string) {
  return `/b/${owner}/${repo}/doc/${path.split("/").map(encodeURIComponent).join("/")}`;
}

type Tree = { tree: { path: string; type: string; sha: string }[]; truncated: boolean };

// --- Front matter ----------------------------------------------------------

// The plugin writes simple front matter: key: value, and key: [a, b] for lists.
export function frontMatter(text: string): { fields: Record<string, string | string[]>; body: string } {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!match) return { fields: {}, body: text };
  const fields: Record<string, string | string[]> = {};
  let lastKey: string | null = null;
  for (const line of match[1].split(/\r?\n/)) {
    // A list written one "- item" per line, under a key with no value of its own.
    const item = line.match(/^\s+-\s+(.*)$/);
    if (item && lastKey && (fields[lastKey] === "" || Array.isArray(fields[lastKey]))) {
      const list = Array.isArray(fields[lastKey]) ? (fields[lastKey] as string[]) : [];
      list.push(item[1].trim().replace(/^["']|["']$/g, ""));
      fields[lastKey] = list;
      continue;
    }
    const pair = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!pair) continue;
    lastKey = pair[1];
    const value = pair[2].trim();
    const list = value.match(/^\[(.*)\]$/);
    fields[pair[1]] = list
      ? list[1].split(",").map((item) => item.trim().replace(/^["']|["']$/g, "")).filter(Boolean)
      : value.replace(/^["']|["']$/g, "");
  }
  return { fields, body: text.slice(match[0].length) };
}

const one = (value: string | string[] | undefined) => (typeof value === "string" && value !== "" ? value : null);
const many = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value : typeof value === "string" && value ? [value] : [];

function titleOf(path: string, body: string): string {
  const heading = body.match(/^#\s+(.+)$/m);
  if (heading) return heading[1].trim();
  const name = path.split("/").pop() ?? path;
  return name.replace(/\.md$/, "").replace(/[-_]+/g, " ");
}

// --- Reading ----------------------------------------------------------------

async function readText(token: string, owner: string, repo: string, sha: string): Promise<string> {
  const blob = await api<{ content: string; encoding: string }>(`/repos/${owner}/${repo}/git/blobs/${sha}`, { token });
  return blob.encoding === "base64" ? Buffer.from(blob.content, "base64").toString("utf8") : blob.content;
}

async function inBatches<T, R>(items: T[], size: number, work: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += size) results.push(...(await Promise.all(items.slice(i, i + size).map(work))));
  return results;
}

async function repoAndTree(token: string, owner: string, repo: string) {
  if (!validRepo(owner, repo)) throw new BaseNotFound();
  let info: { html_url: string; default_branch: string };
  try {
    info = await api(`/repos/${owner}/${repo}`, { token });
  } catch (error) {
    // Only 404 means "no such base for this person"; a 403 (a rate limit, single
    // sign-on) is a real error and is shown as one.
    if (error instanceof GitHubError && error.status === 404) throw new BaseNotFound();
    throw error;
  }
  const tree = await api<Tree>(
    `/repos/${owner}/${repo}/git/trees/${encodeURIComponent(info.default_branch)}?recursive=1`,
    { token },
  );
  const blobs = tree.tree.filter((entry) => entry.type === "blob");
  if (!blobs.some((entry) => entry.path === "context/map.md")) throw new BaseNotFound();
  return { info, blobs, truncated: tree.truncated };
}

export async function readBase(token: string, owner: string, repo: string): Promise<BaseView> {
  return (await load(token, owner, repo)).base;
}

const confirmationsFileFor = (path: string) => `work/confirmations/${path.replace(/\//g, "--")}`;

// `only` limits which file contents are downloaded to one document, its
// confirmations file and the change entries; the base page downloads them all.
async function load(token: string, owner: string, repo: string, only?: string) {
  const { info, blobs, truncated } = await repoAndTree(token, owner, repo);

  const markdown = blobs.filter((b) => b.path.endsWith(".md") && !b.path.startsWith("work/confirmations/"));
  const confirmationFiles = blobs.filter((b) => b.path.startsWith("work/confirmations/") && !b.path.endsWith(".gitkeep"));

  const wanted = (b: { path: string }) =>
    !only || b.path === only || b.path === confirmationsFileFor(only) || b.path.startsWith("learning/changes/");
  const texts = new Map<string, string>();
  await inBatches([...markdown, ...confirmationFiles].filter(wanted), 8, async (b) => {
    texts.set(b.path, await readText(token, owner, repo, b.sha));
  });

  // Context changes: one dated entry per file in learning/changes.
  const changes: Change[] = markdown
    .filter((b) => b.path.startsWith("learning/changes/"))
    .map((b) => {
      const { fields, body } = frontMatter(texts.get(b.path) ?? "");
      return {
        path: b.path,
        id: one(fields.id) ?? b.path.split("/").pop()!.replace(/\.md$/, ""),
        happenedOn: one(fields.happened_on),
        summary: body.trim().split(/\r?\n\r?\n/)[0]?.replace(/\s+/g, " ") ?? "",
        affects: many(fields.affects),
        status: one(fields.status),
      };
    })
    .sort((a, b) => (b.happenedOn ?? "").localeCompare(a.happenedOn ?? ""));

  // The last confirmation line recorded for each document (the plugin's own
  // rules decide which lines count; this shows the latest one written).
  const lastConfirmed = new Map<string, { date: string; trigger: string }>();
  for (const file of confirmationFiles) {
    for (const line of (texts.get(file.path) ?? "").split(/\r?\n/)) {
      if (!line.startsWith("date=")) continue;
      const fields = Object.fromEntries(line.split(" ").map((pair) => pair.split("=") as [string, string]));
      if (!fields.file || !fields.date) continue;
      const previous = lastConfirmed.get(fields.file);
      if (!previous || fields.date >= previous.date) lastConfirmed.set(fields.file, { date: fields.date, trigger: fields.trigger ?? "-" });
    }
  }

  const docs: Doc[] = markdown
    .filter((b) => !b.path.startsWith("learning/changes/"))
    .map((b) => {
      const text = texts.get(b.path) ?? "";
      const { fields, body } = frontMatter(text);
      const top = b.path.includes("/") ? b.path.split("/")[0] : "";
      return {
        path: b.path,
        part: PARTS.some((p) => p.key === top) ? top : "other",
        title: titleOf(b.path, body),
        owner: one(fields.owner),
        kind: one(fields.kind),
        status: one(fields.status),
        lastConfirmed: lastConfirmed.get(b.path) ?? null,
        openChanges: changes.filter((c) => c.status === "open" && c.affects.includes(b.path)),
      };
    })
    .sort((a, b) => (a.path === "context/map.md" ? -1 : b.path === "context/map.md" ? 1 : a.path.localeCompare(b.path)));

  const base: BaseView = { owner, repo, htmlUrl: info.html_url, branch: info.default_branch, docs, changes, truncated };
  return { base, blobs, texts };
}

export async function readDocument(
  token: string,
  owner: string,
  repo: string,
  path: string,
): Promise<{ base: BaseView; doc: Doc; body: string; fields: Record<string, string | string[]> }> {
  const { base, texts } = await load(token, owner, repo, path);
  // Only a path the tree actually holds; nothing built from the address alone.
  const doc = base.docs.find((d) => d.path === path) ?? null;
  const change = base.changes.find((c) => c.path === path) ?? null;
  if (!doc && !change) throw new BaseNotFound();
  const { fields, body } = frontMatter(texts.get(path) ?? "");
  const asDoc: Doc = doc ?? {
    path,
    part: "learning",
    title: `Context change ${change!.id}`,
    owner: one(fields.noted_by),
    kind: "change",
    status: change!.status,
    lastConfirmed: null,
    openChanges: [],
  };
  return { base, doc: asDoc, body, fields };
}
