// Serving a base's own skills in chat (connector unit C3), ported from the
// plugin's runner.py (Unit 3.1), authority.read_skill and
// skill_install.approval_of (Unit 4.2b), so chat hands a person exactly what
// Claude Code hands them from the same base on the same day.
//
// It works on values only (a `SkillWorld`), which the connector gathers from
// GitHub and tests/skill_parity.py gathers from real git repositories; the
// parity check holds this file to the plugin.
//
// The connector is "another computer" in the plugin's terms. It keeps no list
// of trusted versions and can ask nobody to accept one, so it serves exactly
// the versions any other computer would be offered to accept: the version on
// the main line, every file of it, approved as a whole by somebody who held
// authority over the skill before their approval was added, and not replaced
// by a later approval. Anything else is refused. It never writes anything.

import {
  type ChangeEntry,
  Refused,
  Unreadable,
  type Value,
  checkRepoPathSyntax,
  classify,
  parseCorrectionsFile,
  parseFrontmatter,
  splitDocument,
} from "./formats";
import { type CorrectionFacts, type Verdict, roleOf, rolesFrom } from "./rules";
import { documentName, fenced, flagBlock, usedAsIs } from "./words";

export const SKILLS_DIR = "skills";
const MAP_PATH = "context/map.md";
const CORRECTIONS_DIR = "learning/corrections";
const NAME = "[a-z0-9]+(?:-[a-z0-9]+)*";
const NAME_RE = new RegExp(`^${NAME}$`);
const SKILL_RES = [
  new RegExp(`^skills/(${NAME})/SKILL\\.md$`),
  new RegExp(`^skills/(${NAME})/references/${NAME}\\.md$`),
  new RegExp(`^skills/(${NAME})/examples/${NAME}/${NAME}\\.(?:md|txt)$`),
];
const ROLES = ["owner", "base-owner", "administrator"];
const LINK_MODE = "120000";

// --- The words, from runner.py -------------------------------------------------

const fill = (template: string, ...values: string[]) => {
  let i = 0;
  return template.replace(/%s/g, () => values[i++] ?? "");
};

export const REFUSED_INVALID_SAYS =
  "GTM Base did not run %s, because it says it reads %s, which is not a document in this base it can check.";
export const REFUSED_NO_STANDARD = "GTM Base did not run %s, because it does not say which standard it follows, and every skill has to.";
export const REFUSED_NO_SKILL = "GTM Base did not run %s, because this base holds no skill by that name that it can read whole.";
export const REFUSED_UNREADABLE_SAYS =
  "GTM Base did not run %s, because it could not read this base well enough to check the documents the skill reads.";
export const REFUSED_REQUIRED_SAYS = "GTM Base did not run %s, because it needs %s, and the base has no saved copy of it that can be read.";
export const FLAGGED_ATTENDED_SAYS = "Before %s runs, a document it reads needs a choice from you.";
export const GAP_SAYS =
  "The base holds no saved copy of %s, so leave out whatever would have come from it and say that it is missing. Do not guess at it.";
export const INSTRUCTIONS_SAYS = "The approved instructions for %s follow. Follow them as written.";
export const DOCUMENTS_SAYS = "The documents the skill reads follow, each as the base last saved it.";
// Chat's own sentence for the runner's untrusted refusal: in chat there is no
// computer that trusts a version, only whether somebody with authority approved it.
export const REFUSED_NOT_APPROVED_SAYS =
  "GTM Base did not run %s, because nobody with authority over it has approved the skill exactly as it stands in the base.";

const opening = (sentence: string) => sentence.slice(0, 1).toUpperCase() + sentence.slice(1);

// --- What the connector gathers ------------------------------------------------------

export type SkillTreeEntry = { path: string; mode: string; type: string };

export type SkillWorld = {
  // The base's files on the main line, as the moment of use reads them: the
  // map, the documents, and the records of what changed.
  files: Record<string, string>;
  // For each record under learning/corrections: who brought it onto the main
  // line, on which day, in which revision (base_reader.accepted_at).
  corrections: Record<string, CorrectionFacts>;
  // Every entry of the main line's tree at or under `skills`.
  tree: SkillTreeEntry[];
  // Each skill file's text, exactly as saved (decoded as UTF-8), or null when
  // it could not be read as text.
  texts: Record<string, string | null>;
  // Each commit's parents (null when the walk could not read them all).
  parents: Record<string, string[] | null>;
  // For the first parent of each revision that brought an approval onto the
  // main line: the map and each skill's SKILL.md as that revision saved them.
  atParent: Record<string, { map: string | null; skills: Record<string, string | null> }>;
};

// The folders a skill may name in `reads_optional`, whose `.md` files are handed
// on one by one. Exactly the one folder the plugin's runner reads
// (`runner.SEGMENTS_FOLDER`, Track 4 T4.9 and T4.10), so any other folder is
// refused as the plugin refuses it. See `declarationOf` and `expandedReads`.
export const FOLDER_DECLARATIONS: readonly string[] = ["context/icps/"];

// --- Reading a skill whole (authority.read_skill) ---------------------------------

// docpaths.classify for a skill's own files: which skill a path belongs to.
export function skillOf(path: string): string | null {
  try {
    checkRepoPathSyntax(path, ["skills/"]);
  } catch (error) {
    if (error instanceof Refused) return null;
    throw error;
  }
  for (const pattern of SKILL_RES) {
    const match = path.match(pattern);
    if (match) return match[1];
  }
  return null;
}

export type ReadSkill = { files: Record<string, string>; texts: Record<string, string> };

async function sha256(text: string): Promise<string> {
  const { createHash } = await import("node:crypto");
  return createHash("sha256").update(Buffer.from(text, "utf8")).digest("hex");
}

// One skill read whole: every file's hash and text, or null when there is no
// skill here to trust. A link anywhere on the way, a file that is not one of
// a skill's three shapes, a file that cannot be read, or no SKILL.md, each
// mean null, because a file skipped is a file that runs unseen. Another
// repository nested in the folder is refused too, which is stricter than the
// plugin (a checkout shows it as an empty folder) and never looser.
export async function readSkill(world: SkillWorld, skill: string): Promise<ReadSkill | null> {
  if (!NAME_RE.test(skill)) return null;
  const folder = `${SKILLS_DIR}/${skill}`;
  const top = world.tree.find((entry) => entry.path === SKILLS_DIR);
  const own = world.tree.find((entry) => entry.path === folder);
  if (!top || top.type !== "tree" || !own || own.type !== "tree") return null;
  const files: Record<string, string> = {};
  const texts: Record<string, string> = {};
  for (const entry of world.tree) {
    if (!entry.path.startsWith(folder + "/")) continue;
    if (entry.mode === LINK_MODE || entry.type === "commit") return null;
    if (entry.type === "tree") continue;
    if (skillOf(entry.path) !== skill) return null;
    const text = world.texts[entry.path];
    if (typeof text !== "string") return null;
    files[entry.path] = await sha256(text);
    texts[entry.path] = text;
  }
  if (!(`${folder}/SKILL.md` in files)) return null;
  return { files, texts };
}

// --- Who approved this version (skill_install.approval_of) -----------------------------

export type Approval = { approver: string; role: string; day: string | null; record: string };

const sameFiles = (a: Record<string, string>, b: Record<string, string>) => {
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every((key) => key in b && a[key] === b[key]);
};

// git merge-base --is-ancestor older newer, over the walked history.
function isAncestor(parents: SkillWorld["parents"], older: string, newer: string): boolean {
  const seen = new Set<string>();
  const queue = [newer];
  while (queue.length) {
    const oid = queue.pop()!;
    if (oid === older) return true;
    if (seen.has(oid)) continue;
    seen.add(oid);
    const next = parents[oid];
    if (next === undefined || next === null) throw new Unreadable("history-unreadable");
    queue.push(...next);
  }
  return false;
}

type Found = { path: string; approvedRoles: Record<string, string>; approvedHashes: Record<string, string>; email: string; day: string | null; revision: string };

// Every saved approval of a version of this skill, in the plugin's order.
function approvalsOf(world: SkillWorld, skill: string): Found[] {
  const prefix = `${SKILLS_DIR}/${skill}/`;
  const found: Found[] = [];
  const records = Object.keys(world.files)
    .filter((p) => p.startsWith(CORRECTIONS_DIR + "/") && !p.slice(CORRECTIONS_DIR.length + 1).includes("/") && p.endsWith(".md"))
    .sort();
  for (const path of records) {
    const text = world.files[path];
    if (!text) continue;
    let record;
    try {
      record = parseCorrectionsFile(text);
    } catch (error) {
      if (error instanceof Refused) continue;
      throw error;
    }
    const approved = Object.keys(record.approvedHashes);
    if (!approved.length || !approved.every((p) => p.startsWith(prefix))) continue;
    const facts = world.corrections[path];
    if (!facts) throw new Unreadable("record-history-unavailable");
    if (facts.mergedBy && facts.mergedIn) {
      found.push({
        path,
        approvedRoles: record.approvedRoles,
        approvedHashes: record.approvedHashes,
        email: facts.mergedBy,
        day: facts.mergedOn,
        revision: facts.mergedIn,
      });
    }
  }
  return found;
}

// The first parent of each revision whose saved map and SKILL.md the approval
// check needs, so the connector can fetch exactly those.
export function revisionsToRead(world: Omit<SkillWorld, "atParent" | "texts">, skill: string): string[] {
  const wanted = new Set<string>();
  for (const one of approvalsOf({ ...world, texts: {}, atParent: {} }, skill)) {
    const parent = world.parents[one.revision]?.[0];
    if (parent) wanted.add(parent);
  }
  return [...wanted].sort();
}

export function approvalOf(world: SkillWorld, skill: string, files: Record<string, string>): Approval | null {
  const skillMd = `${SKILLS_DIR}/${skill}/SKILL.md`;
  const found = approvalsOf(world, skill);
  for (const one of found.filter((item) => sameFiles(item.approvedHashes, files))) {
    // A newer approval of this skill replaced this one, so the old version is
    // not brought back by putting its bytes back.
    if (found.some((other) => other.revision !== one.revision && isAncestor(world.parents, one.revision, other.revision))) continue;
    // Judged as the base stood before the change that added the record, so a
    // change cannot grant its own author the role it needs.
    const parent = world.parents[one.revision]?.[0];
    if (!parent) continue;
    const saved = world.atParent[parent];
    if (!saved) throw new Unreadable("authority-unavailable");
    const role = roleOf(rolesFrom(saved.skills[skillMd] ?? null, saved.map), one.email);
    if (!role || !ROLES.includes(one.approvedRoles[skillMd] ?? "")) continue;
    return { approver: one.email, role, day: one.day, record: one.path };
  }
  return null;
}

// --- What a skill declares it reads (runner.declaration_of) --------------------------

export type Declaration = {
  required: string[];
  optional: string[];
  standard: string | null;
  problems: [string, string][];
  description: string | null;
};

function listed(value: Value | undefined): string[] | null {
  if (value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) return [];
  if (typeof value === "string") return [value];
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) return [...(value as string[])];
  return null;
}

// A path the moment of use can run on (context, a standard, the source map),
// as docpaths.classify writes it, or null.
function documentPath(candidate: string): string | null {
  const kind = classify(candidate);
  if (kind !== "context" && kind !== "standard" && kind !== "stack") return null;
  return checkRepoPathSyntax(candidate, ["context/", "standards/", "access/"]);
}

export function declarationOf(skillText: string, folders: readonly string[] = FOLDER_DECLARATIONS): Declaration {
  let fields: Record<string, Value>;
  try {
    fields = parseFrontmatter(splitDocument(skillText).block);
  } catch (error) {
    if (error instanceof Refused) return { required: [], optional: [], standard: null, problems: [["settings", ""]], description: null };
    throw error;
  }
  const problems: [string, string][] = [];
  const lists: Record<string, string[]> = {};
  for (const key of ["reads_required", "reads_optional"]) {
    let value = listed(fields[key]);
    if (value === null) {
      problems.push([key, ""]);
      value = [];
    }
    const checked: string[] = [];
    for (const item of value) {
      // The seam for a folder declaration: only in reads_optional, only a
      // folder named in `folders`, written exactly with its closing slash.
      if (key === "reads_optional" && folders.includes(item.trim())) {
        checked.push(item.trim());
        continue;
      }
      const path = documentPath(item);
      if (path === null) problems.push([key, item]);
      else checked.push(path);
    }
    lists[key] = checked;
  }
  const standardValue = fields.standard;
  let standard: string | null = null;
  if (typeof standardValue !== "string" || !standardValue.trim()) problems.push(["standard", ""]);
  else if (classify(standardValue.trim()) !== "standard") problems.push(["standard", standardValue.trim()]);
  else standard = standardValue.trim();
  const description = typeof fields.description === "string" ? fields.description : null;
  return { required: lists.reads_required, optional: lists.reads_optional, standard, problems, description };
}

const once = (paths: string[]) => paths.filter((path, i) => paths.indexOf(path) === i);

export const requiredPaths = (d: Declaration) => once([...(d.standard ? [d.standard] : []), ...d.required]);
export const optionalPaths = (d: Declaration) => {
  const required = requiredPaths(d);
  return once(d.optional.filter((path) => !required.includes(path)));
};

// The documents a declaration hands on, in order: a folder declaration becomes
// the `.md` files sitting directly in that folder on the main line, in name
// order, never a file in a folder inside it and never a link. An empty or
// missing folder adds nothing and is not a gap.
export function expandedReads(
  declaration: Declaration,
  files: Record<string, string>,
  links: readonly string[],
): { path: string; required: boolean; folder: boolean }[] {
  const out: { path: string; required: boolean; folder: boolean }[] = [];
  const add = (path: string, required: boolean, folder: boolean) => {
    if (!out.some((one) => one.path === path)) out.push({ path, required, folder });
  };
  for (const path of requiredPaths(declaration)) add(path, true, false);
  for (const path of optionalPaths(declaration)) {
    if (!path.endsWith("/")) {
      add(path, false, false);
      continue;
    }
    const inside = Object.keys(files)
      .filter((file) => file.startsWith(path) && !file.slice(path.length).includes("/") && file.endsWith(".md"))
      .filter((file) => !links.includes(file) && classify(file) === "context")
      .sort();
    for (const file of inside) add(file, false, true);
  }
  return out;
}

// --- Starting a skill in chat (runner.start, attended) ----------------------------------

export type Outcome = "refused" | "flagged" | "ready-with-gaps" | "ready";
export type RefusalCode = "invalid-declaration" | "untrusted" | "unreadable" | "required";

export type Started = {
  skill: string;
  outcome: Outcome;
  refusal: RefusalCode | null;
  sentences: string[];
  instructions: [string, string][];
  documents: [string, string][];
  flagged: string[];
  gaps: string[];
  approval: Approval | null;
  // Flagged and the person has not chosen yet: nothing is handed on.
  waiting: boolean;
  moments: { path: string; entry: ChangeEntry }[];
};

export type StartOptions = {
  // The documents the person chose to use as they stand, in answer to a flag.
  useAsIs?: string[];
  // Links on the main line under the read folders, never handed on.
  links?: readonly string[];
  folders?: readonly string[];
};

export async function startSkill(
  world: SkillWorld,
  verdict: Verdict | null,
  skill: string,
  options: StartOptions = {},
): Promise<Started> {
  const started: Started = {
    skill,
    outcome: "refused",
    refusal: null,
    sentences: [],
    instructions: [],
    documents: [],
    flagged: [],
    gaps: [],
    approval: null,
    waiting: false,
    moments: [],
  };
  const refuse = (code: RefusalCode, sentence: string) => {
    started.outcome = "refused";
    started.refusal = code;
    started.sentences = [sentence];
    return started;
  };

  const read = await readSkill(world, skill);
  if (!read) return refuse("untrusted", fill(REFUSED_NO_SKILL, skill));
  const head = `${SKILLS_DIR}/${skill}/SKILL.md`;
  const declaration = declarationOf(read.texts[head], options.folders ?? FOLDER_DECLARATIONS);

  // Step 1: every declared path is a document the check can run on.
  if (declaration.problems.length) {
    const [key, value] = declaration.problems[0];
    if (value) return refuse("invalid-declaration", fill(REFUSED_INVALID_SAYS, skill, value));
    if (key === "standard") return refuse("invalid-declaration", fill(REFUSED_NO_STANDARD, skill));
    return refuse("invalid-declaration", fill(REFUSED_INVALID_SAYS, skill, key));
  }

  // Step 2: the version on the main line is one somebody with authority approved.
  started.approval = approvalOf(world, skill, read.files);
  if (!started.approval) return refuse("untrusted", fill(REFUSED_NOT_APPROVED_SAYS, skill));

  // Step 3: the base can be read for the check.
  if (!world.files[MAP_PATH]) return refuse("unreadable", fill(REFUSED_UNREADABLE_SAYS, skill));
  const reads = expandedReads(declaration, world.files, options.links ?? []);

  // Step 4: every required document is saved and readable.
  for (const one of reads) {
    if (one.required && world.files[one.path] === undefined) {
      return refuse("required", fill(REFUSED_REQUIRED_SAYS, skill, documentName(one.path)));
    }
  }

  // `SKILL.md` first, then its references by name. Examples are never handed on.
  const references = Object.keys(read.texts)
    .filter((path) => path.includes("/references/"))
    .sort();
  started.instructions = [head, ...references].map((path) => [path, read.texts[path]]);
  for (const one of reads) {
    const text = world.files[one.path];
    if (text === undefined) started.gaps.push(one.path);
    else started.documents.push([one.path, text]);
  }

  // Step 5 (a silenced seat) does not exist in chat. Step 6: the moment-of-use
  // check on each document handed on.
  if (!verdict) {
    started.instructions = [];
    started.documents = [];
    return refuse("unreadable", fill(REFUSED_UNREADABLE_SAYS, skill));
  }
  for (const [path] of started.documents) {
    const entry = verdict.overtakenBy.get(path);
    if (entry) {
      started.flagged.push(path);
      started.moments.push({ path, entry });
    }
  }
  const gapSentences = started.gaps.map((path) => fill(GAP_SAYS, documentName(path)));
  if (started.flagged.length) {
    started.outcome = "flagged";
    const chosen = started.flagged.filter((path) => (options.useAsIs ?? []).includes(path));
    if (chosen.length < started.flagged.length) {
      started.waiting = true;
      return started;
    }
    started.sentences = [...chosen.map((path) => opening(usedAsIs(path))), ...gapSentences];
    return started;
  }

  // Step 7: ready, with any gap named.
  started.outcome = started.gaps.length ? "ready-with-gaps" : "ready";
  started.sentences = gapSentences;
  return started;
}

// Everything a skill that runs hands on, in the runner's one order
// (Start.render), without the run line: chat has no `finish`.
export function rendered(started: Started): string {
  if (started.outcome === "refused") return started.sentences.join("\n");
  const pieces = [...started.sentences, "", fill(INSTRUCTIONS_SAYS, started.skill)];
  for (const [path, text] of started.instructions) {
    pieces.push("", `[for the assistant] instructions=${path}`, text.replace(/\n+$/, ""));
  }
  if (started.documents.length) {
    pieces.push("", DOCUMENTS_SAYS);
    for (const [path, text] of started.documents) pieces.push("", `[for the assistant] document=${path}`, fenced(text));
  }
  return pieces.join("\n");
}

// The flag before a skill runs: the runner's sentence, then each flagged
// document's block, as the plugin's moment of use words it.
export function renderedWaiting(
  started: Started,
  perDocument: Record<string, { owned: boolean; fixReady: boolean }>,
  today: string,
): string {
  const pieces = [fill(FLAGGED_ATTENDED_SAYS, started.skill)];
  for (const { path, entry } of started.moments) {
    const facts = perDocument[path] ?? { owned: false, fixReady: false };
    pieces.push("", flagBlock({ path, entry, fixReady: facts.fixReady, owned: facts.owned, today }));
  }
  return pieces.join("\n");
}

// --- Never a write into skills/ ----------------------------------------------------

// Whether any path would land in the skills folder, however it is spelled:
// with a leading slash or dot, a backslash, or in another case (a checkout on a
// Mac or Windows computer folds case, so `Skills/` lands in `skills/` there).
// A skill reaches a base only through the plugin's install, with its yeses.
export function touchesSkills(paths: string[]): boolean {
  return paths.some((raw) => {
    const path = raw.replace(/\\/g, "/").replace(/^(?:\.?\/)+/, "").toLowerCase();
    return path === SKILLS_DIR || path.startsWith(SKILLS_DIR + "/");
  });
}

// --- The index ------------------------------------------------------------------

const MARKERS_RE = /<!--+|--+>|\[\[block:/gi;
const DESCRIPTION_CHARS = 300;

function oneLine(text: string): string {
  let single = text.split(/\s+/).filter(Boolean).join(" ");
  single = single.replace(MARKERS_RE, (found) => found.split("").join(" "));
  return single.length <= DESCRIPTION_CHARS ? single : single.slice(0, DESCRIPTION_CHARS).trimEnd() + "...";
}

export type IndexEntry = { name: string; description: string };

// The skills chat may use: every skill in the base that reads whole, declares
// its reads properly, and is an approved version. Each with its own one line on
// when to use it, kept to one line.
export async function skillIndex(world: SkillWorld, folders: readonly string[] = FOLDER_DECLARATIONS): Promise<IndexEntry[]> {
  const names = world.tree
    .filter((entry) => entry.type === "tree" && entry.path.startsWith(SKILLS_DIR + "/") && !entry.path.slice(SKILLS_DIR.length + 1).includes("/"))
    .map((entry) => entry.path.slice(SKILLS_DIR.length + 1))
    .filter((name) => NAME_RE.test(name))
    .sort();
  const index: IndexEntry[] = [];
  for (const name of names) {
    const read = await readSkill(world, name);
    if (!read) continue;
    const declaration = declarationOf(read.texts[`${SKILLS_DIR}/${name}/SKILL.md`], folders);
    if (declaration.problems.length) continue;
    if (!approvalOf(world, name, read.files)) continue;
    index.push({ name, description: oneLine(declaration.description ?? "") || "No description given." });
  }
  return index;
}
