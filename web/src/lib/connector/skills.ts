import "server-only";
import { GitHubError } from "../github";
import { Unreadable } from "../stale/formats";
import { CORRECTIONS_DIR } from "../stale/rules";
import { type BaseSnapshot, fixIsReady } from "../stale/github";
import {
  type IndexEntry,
  REFUSED_NO_SKILL,
  type SkillWorld,
  SKILLS_DIR,
  renderedWaiting,
  rendered,
  revisionsToRead,
  skillIndex,
  startSkill,
} from "../stale/skills";
import { Refusal, load, ownsIt } from "./documents";

// C3: the base's own approved skills, served live in chat. Every read comes
// from the base's main line on GitHub at the moment it is asked, with the
// person's own token, through the same rules the plugin's runner applies
// (lib/stale/skills.ts). Nothing here writes anything.

const MAX_SKILL_FILES = 300;
const MAX_INDEX = 50;

const quote = (text: string) => JSON.stringify(text);

async function graphql<T>(token: string, query: string, variables: Record<string, unknown>): Promise<T> {
  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
    cache: "no-store",
  });
  if (!response.ok) throw new GitHubError(`GitHub GraphQL answered ${response.status}`, response.status);
  const body = (await response.json()) as { data?: T; errors?: { type?: string }[] };
  if (body.errors?.some((error) => error.type !== "NOT_FOUND") || !body.data) throw new Unreadable("github-graphql-refused");
  return body.data;
}

type BlobText = { text: string | null; isBinary: boolean | null; isTruncated: boolean } | null;

// Each skill file's text, as GitHub holds it. A binary or cut-short file has
// no text, so the skill it belongs to cannot be read whole and is not served.
async function skillTexts(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<Record<string, string | null>> {
  const blobs = snapshot.skillTree.filter((entry) => entry.type === "blob" && entry.mode !== "120000");
  if (blobs.length > MAX_SKILL_FILES) throw new Unreadable("skills-too-large");
  const texts: Record<string, string | null> = {};
  for (let at = 0; at < blobs.length; at += 50) {
    const batch = blobs.slice(at, at + 50);
    const fields = batch.map((entry, i) => `b${i}: object(oid: ${quote(entry.sha)}) { ... on Blob { text isBinary isTruncated } }`).join("\n");
    const data = await graphql<{ repository: Record<string, BlobText> }>(
      token,
      `query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { ${fields} } }`,
      { owner, name: repo },
    );
    batch.forEach((entry, i) => {
      const blob = data.repository[`b${i}`];
      texts[entry.path] = blob && !blob.isBinary && !blob.isTruncated && typeof blob.text === "string" ? blob.text : null;
    });
  }
  return texts;
}

// The map and each skill's SKILL.md as each revision the approval check reads saved them.
async function savedAt(
  token: string,
  owner: string,
  repo: string,
  revisions: string[],
  skills: string[],
): Promise<SkillWorld["atRevision"]> {
  const saved: SkillWorld["atRevision"] = {};
  const paths = ["context/map.md", ...skills.map((name) => `${SKILLS_DIR}/${name}/SKILL.md`)];
  const blob = (path: string, i: number) => `f${i}: file(path: ${quote(path)}) { object { ... on Blob { text } } }`;
  for (let at = 0; at < revisions.length; at += 10) {
    const batch = revisions.slice(at, at + 10);
    const fields = batch.map((oid, j) => `c${j}: object(oid: ${quote(oid)}) { ... on Commit { ${paths.map(blob).join(" ")} } }`).join("\n");
    const data = await graphql<{ repository: Record<string, Record<string, { object: { text: string | null } | null } | null> | null> }>(
      token,
      `query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { ${fields} } }`,
      { owner, name: repo },
    );
    batch.forEach((oid, j) => {
      const commit = data.repository[`c${j}`];
      if (!commit) throw new Unreadable("authority-unavailable");
      const text = (i: number) => commit[`f${i}`]?.object?.text ?? null;
      const entry: SkillWorld["atRevision"][string] = { map: text(0), skills: {} };
      paths.slice(1).forEach((path, i) => {
        entry.skills[path] = text(i + 1);
      });
      saved[oid] = entry;
    });
  }
  return saved;
}

// The records folder at each commit on the main line that changed it, oldest
// first, with each entry's name and blob id (for recordsIntact).
async function recordTreesOf(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<SkillWorld["recordTrees"]> {
  const commits = [...(snapshot.changes[CORRECTIONS_DIR] ?? [])].reverse();
  const trees: SkillWorld["recordTrees"] = [];
  for (let at = 0; at < commits.length; at += 20) {
    const batch = commits.slice(at, at + 20);
    const fields = batch
      .map((oid, j) => `c${j}: object(oid: ${quote(oid)}) { ... on Commit { file(path: ${quote(CORRECTIONS_DIR)}) { object { ... on Tree { entries { name oid } } } } } }`)
      .join("\n");
    const data = await graphql<{ repository: Record<string, { file: { object: { entries: { name: string; oid: string }[] } | null } | null } | null> }>(
      token,
      `query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { ${fields} } }`,
      { owner, name: repo },
    );
    batch.forEach((oid, j) => {
      const commit = data.repository[`c${j}`];
      if (!commit) throw new Unreadable("history-unreadable");
      const entries: Record<string, string> = {};
      for (const entry of commit.file?.object?.entries ?? []) entries[entry.name] = entry.oid;
      trees.push({ oid, entries });
    });
  }
  return trees;
}

export async function worldOf(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<SkillWorld> {
  const tree = snapshot.skillTree.map(({ path, mode, type }) => ({ path, mode, type }));
  const names = tree
    .filter((entry) => entry.type === "tree" && entry.path.startsWith(SKILLS_DIR + "/") && !entry.path.slice(SKILLS_DIR.length + 1).includes("/"))
    .map((entry) => entry.path.slice(SKILLS_DIR.length + 1));
  const partial = {
    files: snapshot.files,
    corrections: snapshot.corrections,
    tree,
    parents: snapshot.parents,
    mainLine: snapshot.mainLine,
    changes: snapshot.changes,
  };
  const revisions = [...new Set(names.flatMap((name) => revisionsToRead(partial, name)))].sort();
  const [texts, atRevision, recordTrees] = await Promise.all([
    names.length ? skillTexts(token, owner, repo, snapshot) : Promise.resolve({}),
    savedAt(token, owner, repo, revisions, names),
    recordTreesOf(token, owner, repo, snapshot),
  ]);
  return { ...partial, texts, atRevision, recordTrees };
}

// --- The index ---------------------------------------------------------------

const indexLines = (index: IndexEntry[]) =>
  index
    .slice(0, MAX_INDEX)
    .map((entry) => `- ${entry.name}: ${entry.description}`)
    .join("\n");

const HOW_TO_USE =
  "When the person asks for work one of these fits, call use_skill with the base and the skill's name before doing the work, and follow what it returns.";

async function indexOf(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<IndexEntry[] | null> {
  try {
    return await skillIndex(await worldOf(token, owner, repo, snapshot));
  } catch (error) {
    if (error instanceof Unreadable) return null;
    throw error;
  }
}

// The index as list_documents ends with it.
export async function indexText(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<string> {
  const index = await indexOf(token, owner, repo, snapshot);
  if (index === null) return "GTM Base could not read this base's skills just now, so none are offered.";
  if (!index.length) return "This base holds no approved skills yet.";
  return `The base's approved skills, each with when to use it:\n${indexLines(index)}\n\n${HOW_TO_USE}`;
}

// The connector's instructions and use_skill's description only ever say how
// skills work, never which skills a base holds. A client may keep one tool
// listing across conversations, so a list there could put one client's skills
// in front of another client's conversation. The list comes only from
// list_documents, which is tied to one base (the C3 security review).
export const SKILLS_SENTENCE =
  "A base may hold the company's own approved skills. list_documents names them, with when to use each. When the " +
  "person asks for work one of them fits, call use_skill before doing the work, and follow what it returns.";

// --- Use a skill -----------------------------------------------------------------

const ASK_FIRST =
  "Stop here. Say the above to the person in your own plain words and wait for their choice for each document. " +
  "To use a document as it stands, call use_skill again with the same base and skill and use_as_is listing its path. " +
  "To fix it first, or to say it already reflects the change when that is offered, call read_document with that path and that choice. " +
  "Do not start the work, and do not use any of it, before the person has chosen.";

export async function useSkill(
  token: string,
  owner: string,
  repo: string,
  rawName: string,
  useAsIs: string[] | undefined,
): Promise<string> {
  const name = rawName.trim();
  const { snapshot, verdict } = await load(token, owner, repo);
  let world: SkillWorld;
  try {
    world = await worldOf(token, owner, repo, snapshot);
  } catch (error) {
    if (error instanceof Unreadable) throw new Refusal("GTM Base could not read this base's skills just now, so it ran none. Try again in a moment.");
    throw error;
  }
  let started;
  try {
    started = await startSkill(world, verdict, name, { useAsIs: (useAsIs ?? []).map((p) => p.trim()), links: snapshot.links });
  } catch (error) {
    if (error instanceof Unreadable) throw new Refusal("GTM Base could not read this base's skills just now, so it ran none. Try again in a moment.");
    throw error;
  }

  if (started.outcome === "refused") {
    if (started.sentences[0] === REFUSED_NO_SKILL.replace("%s", name)) {
      const index = await skillIndex(world).catch(() => []);
      const known = index.length ? `Its approved skills are:\n${indexLines(index)}` : "It holds no approved skills yet.";
      throw new Refusal(`${rendered(started)}\n\n${known}`);
    }
    throw new Refusal(rendered(started));
  }
  if (started.waiting) {
    const facts: Record<string, { owned: boolean; fixReady: boolean }> = {};
    for (const { path, entry } of started.moments) {
      const info = verdict?.documents.get(path);
      facts[path] = {
        owned: info ? await ownsIt(token, info.authority) : false,
        fixReady: await fixIsReady(token, owner, repo, entry.id, path),
      };
    }
    return `${renderedWaiting(started, facts, snapshot.today)}\n\n${ASK_FIRST}`;
  }
  return rendered(started);
}
