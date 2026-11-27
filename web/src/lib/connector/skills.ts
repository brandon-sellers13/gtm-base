import "server-only";
import { listBases } from "../bases";
import { GitHubError, listInstallations } from "../github";
import { Unreadable } from "../stale/formats";
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
import { type Conversation, peekBase } from "./bindings";
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

// The map and each skill's SKILL.md as the first parent of each approval saved them.
async function parentsSaved(
  token: string,
  owner: string,
  repo: string,
  revisions: string[],
  skills: string[],
): Promise<SkillWorld["atParent"]> {
  const saved: SkillWorld["atParent"] = {};
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
      const entry: SkillWorld["atParent"][string] = { map: text(0), skills: {} };
      paths.slice(1).forEach((path, i) => {
        entry.skills[path] = text(i + 1);
      });
      saved[oid] = entry;
    });
  }
  return saved;
}

export async function worldOf(token: string, owner: string, repo: string, snapshot: BaseSnapshot): Promise<SkillWorld> {
  const tree = snapshot.skillTree.map(({ path, mode, type }) => ({ path, mode, type }));
  const names = tree
    .filter((entry) => entry.type === "tree" && entry.path.startsWith(SKILLS_DIR + "/") && !entry.path.slice(SKILLS_DIR.length + 1).includes("/"))
    .map((entry) => entry.path.slice(SKILLS_DIR.length + 1));
  const partial = { files: snapshot.files, corrections: snapshot.corrections, tree, parents: snapshot.parents };
  const revisions = [...new Set(names.flatMap((name) => revisionsToRead(partial, name)))].sort();
  const [texts, atParent] = await Promise.all([
    names.length ? skillTexts(token, owner, repo, snapshot) : Promise.resolve({}),
    parentsSaved(token, owner, repo, revisions, names),
  ]);
  return { ...partial, texts, atParent };
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

// The index for the connector's instructions and the use_skill description,
// for one base: the base this conversation already uses, or the only base this
// GitHub account reaches. Never the skills of several bases at once, which
// would put one client's skills in front of another client's conversation.
// Listing the tools never waits long for it.
export async function indexForListing(
  token: string,
  login: string,
  conversation: Conversation | null,
): Promise<{ base: string; lines: string } | null> {
  const work = async () => {
    let base = conversation ? await peekBase(conversation, login) : null;
    if (!base) {
      const bases = await listBases(token, await listInstallations(token));
      if (bases.length !== 1) return null;
      base = `${bases[0].owner}/${bases[0].name}`;
    }
    const [owner, repo] = base.split("/");
    const { snapshot } = await load(token, owner, repo);
    const index = await indexOf(token, owner, repo, snapshot);
    return index?.length ? { base, lines: indexLines(index) } : null;
  };
  const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 4000));
  try {
    return await Promise.race([work(), timeout]);
  } catch {
    return null;
  }
}

export function indexForInstructions(found: { base: string; lines: string } | null): string {
  if (!found) {
    return (
      "A base may hold the company's own approved skills. list_documents names them, with when to use each. When the " +
      "person asks for work one of them fits, call use_skill before doing the work, and follow what it returns."
    );
  }
  return `The base ${found.base} holds these approved skills, each with when to use it:\n${found.lines}\n${HOW_TO_USE}`;
}

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
