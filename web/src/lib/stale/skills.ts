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
import { type CorrectionFacts, LEGACY_CORRECTIONS_DIR, type Roles, type Verdict, recordNames, roleOf, rolesFrom } from "./rules";
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
const SEGMENT_NAME = /^[a-z0-9-]+\.md$/;
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
  // The main line, newest first: the head and each first parent back to the root.
  mainLine: string[];
  // For the map and for each skill's folder (`skills/<name>`), every commit on
  // the main line whose copy differs from its first parent's, newest first.
  changes: Record<string, string[]>;
  // For each revision the approval check reads: the map and each skill's
  // SKILL.md exactly as that revision saved them.
  atRevision: Record<string, { map: string | null; skills: Record<string, string | null> }>;
  // Both records folders (learning/corrections and the older corrections) at
  // each commit on the main line that changed either, oldest first: each
  // record's full path and blob id.
  recordTrees: { oid: string; entries: Record<string, string> }[];
};

// skill_install.records_intact: whether every record ever added to the main
// line is still there with the bytes it was first saved with. The authority
// replay reads only the records that exist today, so one taken away or changed
// could bring back a role the base owner removed; then nothing is accepted.
// Putting the record back exactly as it was first saved makes it whole again.
// Both records folders count, and a record is still there when either of its
// names holds the bytes it was first saved with, so the layout move, which
// carries records over byte for byte, keeps a base whole.
export function recordsIntact(world: Pick<SkillWorld, "recordTrees">): boolean {
  const first = new Map<string, string>();
  for (const { entries } of world.recordTrees) {
    for (const [path, oid] of Object.entries(entries)) if (!first.has(path)) first.set(path, oid);
  }
  const now = world.recordTrees.at(-1)?.entries ?? {};
  return [...first].every(([path, oid]) => recordNames(path).some((name) => now[name] === oid));
}

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

const isSkillApproval = (approvedHashes: Record<string, string>, skill: string) => {
  const approved = Object.keys(approvedHashes);
  return approved.length > 0 && approved.every((p) => p.startsWith(`${SKILLS_DIR}/${skill}/`));
};

// Every saved approval of this skill or of the map (skill_install._saved_approvals).
function approvalsOf(world: SkillWorld, skill: string): Found[] {
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
    if (!isSkillApproval(record.approvedHashes, skill) && !(MAP_PATH in record.approvedHashes)) continue;
    const facts = world.corrections[path];
    if (!facts) throw new Unreadable("record-history-unavailable");
    // Judged by the change that first added it, never the newest one.
    if (facts.addedBy === undefined || facts.addedIn === undefined) throw new Unreadable("record-history-unavailable");
    if (facts.addedBy && facts.addedIn) {
      found.push({
        path,
        approvedRoles: record.approvedRoles,
        approvedHashes: record.approvedHashes,
        email: facts.addedBy,
        day: facts.addedOn ?? null,
        revision: facts.addedIn,
      });
    }
  }
  return found;
}

// The commit that first saved the map on the main line: the base being set up.
const firstMap = (world: Pick<SkillWorld, "changes">) => world.changes[MAP_PATH]?.at(-1) ?? null;

// Each revision whose saved map and SKILL.md the approval check reads, so the
// connector can fetch exactly those.
export function revisionsToRead(world: Omit<SkillWorld, "atRevision" | "texts" | "recordTrees">, skill: string): string[] {
  const wanted = new Set<string>();
  for (const one of approvalsOf({ ...world, texts: {}, atRevision: {}, recordTrees: [] }, skill)) wanted.add(one.revision);
  const first = firstMap(world);
  if (first) wanted.add(first);
  return [...wanted].sort();
}

async function hashOf(text: string | null | undefined): Promise<string | null> {
  return typeof text === "string" ? sha256(text) : null;
}

// skill_install._approved_authority: the skill's authority set as authority
// itself had approved it before this revision. The map's roles start as the map
// the base first saved on the main line and change only with a record of the
// map approved by the base owner those roles name, whose map bytes are exactly
// the ones approved. The skill's owners are the owner line of the last valid
// approval of the skill, from the SKILL.md bytes it approved. Changes in one
// revision are judged on what stood before it. Whatever merely sat on the main
// line is never read as authority (the C3 security review, finding 1).
async function approvedRoles(world: SkillWorld, skill: string, revision: string, saved: Found[]): Promise<Roles> {
  const place = new Map(world.mainLine.map((oid, index) => [oid, index]));
  const at = place.get(revision);
  if (at === undefined) throw new Unreadable("authority-unavailable");
  const skillMd = `${SKILLS_DIR}/${skill}/SKILL.md`;
  type Event = { order: number; path: string; kind: "first-map" | "map" | "skill"; one?: Found };
  const events = new Map<number, Event[]>();
  const add = (index: number, event: Event) => events.set(index, [...(events.get(index) ?? []), event]);
  const first = firstMap(world);
  if (first && place.has(first)) add(place.get(first)!, { order: 0, path: "", kind: "first-map" });
  for (const one of saved) {
    const index = place.get(one.revision);
    if (index === undefined) continue;
    if (MAP_PATH in one.approvedHashes) add(index, { order: 1, path: one.path, kind: "map", one });
    if (isSkillApproval(one.approvedHashes, skill)) add(index, { order: 2, path: one.path, kind: "skill", one });
  }
  const textAt = (oid: string) => {
    const texts = world.atRevision[oid];
    if (!texts) throw new Unreadable("authority-unavailable");
    return texts;
  };
  let roles: Roles = { owners: [], baseOwner: null, administrators: [] };
  const older = [...events.keys()].filter((index) => index > at).sort((a, b) => b - a);
  for (const index of older) {
    const oid = world.mainLine[index];
    let next: Roles = roles;
    const ordered = events.get(index)!.sort((a, b) => a.order - b.order || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
    for (const event of ordered) {
      if (event.kind === "first-map") {
        const fromMap = rolesFrom(null, textAt(oid).map);
        next = { ...next, baseOwner: fromMap.baseOwner, administrators: fromMap.administrators };
        continue;
      }
      const one = event.one!;
      if (event.kind === "map") {
        if (!roles.baseOwner || one.email !== roles.baseOwner) continue;
        if (!ROLES.includes(one.approvedRoles[MAP_PATH] ?? "")) continue;
        const text = textAt(oid).map;
        if ((await hashOf(text)) === one.approvedHashes[MAP_PATH]) {
          const fromMap = rolesFrom(null, text);
          next = { ...next, baseOwner: fromMap.baseOwner, administrators: fromMap.administrators };
        }
        continue;
      }
      if (!roleOf(roles, one.email) || !ROLES.includes(one.approvedRoles[skillMd] ?? "")) continue;
      const text = textAt(oid).skills[skillMd];
      if ((await hashOf(text)) === one.approvedHashes[skillMd]) next = { ...next, owners: rolesFrom(text ?? null, null).owners };
    }
    roles = next;
  }
  return roles;
}

// skill_install._changed_since: whether a commit on the main line after this
// revision changed the skill's folder, each compared with its own first parent,
// so a folder changed and then put back still counts (the C3 security review,
// finding 2).
function changedSince(world: SkillWorld, skill: string, revision: string): boolean {
  const at = world.mainLine.indexOf(revision);
  const changed = world.changes[`${SKILLS_DIR}/${skill}`];
  if (at < 0 || !changed) throw new Unreadable("history-unreadable");
  return changed.some((oid) => {
    const index = world.mainLine.indexOf(oid);
    return index >= 0 && index < at;
  });
}

export async function approvalOf(world: SkillWorld, skill: string, files: Record<string, string>): Promise<Approval | null> {
  const skillMd = `${SKILLS_DIR}/${skill}/SKILL.md`;
  if (!recordsIntact(world)) return null;
  // The connector never reads a record in the older records folder, which the
  // plugin's replay does read, so a role taken away there would go unseen.
  // While any record sits in that folder, nothing is accepted here.
  if (Object.keys(world.recordTrees.at(-1)?.entries ?? {}).some((path) => path.startsWith(`${LEGACY_CORRECTIONS_DIR}/`))) return null;
  const saved = approvalsOf(world, skill);
  const found = saved.filter((item) => isSkillApproval(item.approvedHashes, skill));
  for (const one of found.filter((item) => sameFiles(item.approvedHashes, files))) {
    // A newer approval of this skill replaced this one, so the old version is
    // not brought back by putting its bytes back.
    if (found.some((other) => other.revision !== one.revision && isAncestor(world.parents, one.revision, other.revision))) continue;
    if (changedSince(world, skill, one.revision)) continue;
    const role = roleOf(await approvedRoles(world, skill, one.revision, saved), one.email);
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
    // runner._SEGMENT_NAME: only lowercase letters, digits and hyphens, because
    // the name goes out on the document= line outside the fence, and so never a
    // hidden file (the C3 security review, findings 3 and 4).
    const inside = Object.keys(files)
      .filter((file) => file.startsWith(path) && SEGMENT_NAME.test(file.slice(path.length)))
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
  started.approval = await approvalOf(world, skill, read.files);
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
    if (!(await approvalOf(world, name, read.files))) continue;
    index.push({ name, description: oneLine(declaration.description ?? "") || "No description given." });
  }
  return index;
}
