// Whether a recorded context change has overtaken a document, ported from the
// plugin's base_reader.py and stale.py (the part the moment of use needs) so
// the connector says what Claude Code says about the same base on the same day.
// It works on a snapshot of the base: the files' text, who added each
// confirmation line, and what GitHub says about the commit that brought each
// accepted record onto the main line. The parity check holds it to the plugin.
//
// Only the current layout is read. A base that still holds anything in the
// older layout's folders is refused as a whole (OLDER_LAYOUT), so the caller
// says it cannot vouch for the document rather than guessing.

import {
  type ChangeEntry,
  type ConfirmationLine,
  Refused,
  Unreadable,
  STACK_PATH,
  checkDocumentPathSyntax,
  classify,
  holdsAnOpenQuestion,
  parseChangeEntry,
  parseConfirmationLine,
  parseCorrectionsFile,
  parseFrontmatter,
  pyStr,
  splitDocument,
  validateChangeEntry,
  validateConfirmationLine,
  validateOwner,
  type Value,
} from "./formats";

export type CorrectionFacts = {
  // The files the commit that first added the record also changed.
  coModified: string[];
  // The plugin's one hash over the context files the record lists, as that
  // commit left them, or null when any of them could not be read.
  hashAtCommit: string | null;
  // Who brought the record onto the main line (first parent), and the day.
  mergedBy: string | null;
  mergedOn: string | null;
  // The commit that brought it onto the main line, whose saved map and
  // documents decide whether that person could accept it then.
  mergedIn: string | null;
  // Who first added it to the main line, the day, and the commit
  // (skill_install.first_added). Approvals are judged by these, never by the
  // newest change, so whoever edits a record later does not become its approver.
  addedBy?: string | null;
  addedOn?: string | null;
  addedIn?: string | null;
  // The files the commit that first brought it onto the main line changed,
  // compared with its first parent. A record
  // settles a document only when this lists it, so a proposal that edits a
  // document, adds its record and undoes the edit settles nothing (C2's
  // security review, closed 2026-11-27). Null means it was not worked out.
  acceptedPaths?: string[] | null;
};

export type LineAuthor = { email: string; revision: string };

// One saved revision: the map and the documents as that commit held them, a
// null for one it did not hold.
export type SavedRevision = { map: string | null; documents: Record<string, string | null> };

export type Snapshot = {
  today: string; // YYYY-MM-DD
  // Text of every file under context/, standards/, access/, learning/changes/,
  // learning/corrections/ and work/confirmations/ on the default branch.
  files: Record<string, string>;
  // For each confirmations file, who added each line and in which revision.
  confirmationAuthors: Record<string, Record<string, LineAuthor>>;
  // For each records file under learning/corrections/.
  corrections: Record<string, CorrectionFacts>;
  // Every revision a line or an acceptance came from.
  revisions: Record<string, SavedRevision>;
};

export const CHANGES_DIR = "learning/changes";
export const CORRECTIONS_DIR = "learning/corrections";
export const CONFIRMATIONS_DIR = "work/confirmations";
export const OLDER_LAYOUT = "older-layout";

const OLDER_FOLDERS = ["work/changes/", "work/decisions/", "corrections/", "context/strategy/", "context/plan/"];
const OLDER_FILES = ["context/metrics/definitions.md"];

const LEGACY_DOCUMENT_PATHS: [string, string][] = [
  ["context/plan/goals.md", "context/goals.md"],
  ["context/strategy/icp.md", "context/icps.md"],
  ["context/strategy/positioning.md", "context/positioning.md"],
  ["context/strategy/messaging.md", "context/messaging.md"],
  ["context/strategy/voice.md", "context/voice.md"],
  ["context/strategy/design.md", "context/design.md"],
  ["context/metrics/definitions.md", "context/metrics.md"],
];
const SEGMENTS_DIR = "context/icps";
const LEGACY_SEGMENTS_DIR = "context/strategy/segments";

export type DocumentInfo = {
  path: string;
  owners: string[];
  // Who may confirm it today: its owners, the base owner and the administrators.
  authority: string[];
  present: boolean;
  isMap: boolean;
  openQuestion: boolean;
};

export type Verdict = {
  // Every context document the base holds, by path.
  documents: Map<string, DocumentInfo>;
  // The open change that has overtaken each document, oldest first; a document
  // missing from the map has not been overtaken.
  overtakenBy: Map<string, ChangeEntry>;
  entries: Map<string, ChangeEntry>;
};

// --- Where a document lives (layout.where_it_lives) ---------------------------

function segmentName(path: string, folder: string): string | null {
  if (!path.startsWith(folder + "/")) return null;
  const rest = path.slice(folder.length + 1);
  return rest && !rest.includes("/") && rest.endsWith(".md") ? rest : null;
}

function counterpart(path: string): string | null {
  for (const [older, current] of LEGACY_DOCUMENT_PATHS) {
    if (path === older) return current;
  }
  const fromOlder = segmentName(path, LEGACY_SEGMENTS_DIR);
  if (fromOlder) return `${SEGMENTS_DIR}/${fromOlder}`;
  for (const [older, current] of LEGACY_DOCUMENT_PATHS) {
    if (path === current) return older;
  }
  const fromCurrent = segmentName(path, SEGMENTS_DIR);
  if (fromCurrent) return `${LEGACY_SEGMENTS_DIR}/${fromCurrent}`;
  return null;
}

function whereItLives(snapshot: Snapshot, value: string): string {
  const text = value.replace(/^\s+|\s+$/g, "");
  const present = (p: string) => p in snapshot.files || Object.keys(snapshot.files).some((f) => f.startsWith(p + "/"));
  if (!text || present(text)) return text;
  const other = counterpart(text);
  return other && present(other) ? other : text;
}

// --- Reading the snapshot (base_reader) ----------------------------------------

function sortedPaths(snapshot: Snapshot, folder: string): string[] {
  // os.listdir order, sorted, of the .md files directly inside one folder.
  return Object.keys(snapshot.files)
    .filter((path) => path.startsWith(folder + "/") && !path.slice(folder.length + 1).includes("/") && path.endsWith(".md"))
    .sort();
}

// --- Who may confirm (authority.py) ----------------------------------------------

function settingsOf(text: string | null): Record<string, Value> | null {
  try {
    return parseFrontmatter(splitDocument(text ?? "").block);
  } catch (error) {
    if (error instanceof Refused) return null;
    throw error;
  }
}

function addresses(value: Value | undefined): string[] | null {
  if (value === undefined || (Array.isArray(value) && value.length === 0) || value === "") return [];
  try {
    return validateOwner(value);
  } catch (error) {
    if (error instanceof Refused) return null;
    throw error;
  }
}

// authority.authority_from: the document's owners, the map's one owner, and
// the map's administrators, as one saved version of each names them.
export type Roles = { owners: string[]; baseOwner: string | null; administrators: string[] };

export function rolesFrom(documentText: string | null, mapText: string | null): Roles {
  const owners = addresses(settingsOf(documentText)?.owner) ?? [];
  const map = settingsOf(mapText);
  let baseOwner: string | null = null;
  let administrators: string[] = [];
  if (map) {
    const named = addresses(map.owner);
    if (named && named.length === 1) baseOwner = named[0];
    administrators = addresses(map.administrators) ?? [];
  }
  return { owners, baseOwner, administrators };
}

// AuthoritySet.role_of: the most particular role an address holds, compared
// letter for letter, or null.
export function roleOf(roles: Roles, address: string | null): "owner" | "base-owner" | "administrator" | null {
  if (!address) return null;
  if (roles.owners.includes(address)) return "owner";
  if (address === roles.baseOwner) return "base-owner";
  if (roles.administrators.includes(address)) return "administrator";
  return null;
}

export function authorityFrom(documentText: string | null, mapText: string | null): string[] {
  const { owners, baseOwner, administrators } = rolesFrom(documentText, mapText);
  const found: string[] = [];
  for (const address of [...owners, baseOwner, ...administrators]) if (address && !found.includes(address)) found.push(address);
  return found;
}

// base_reader._allowed_then: whether an address was in a document's authority
// set at the revision that added a line or accepted a record. Fails closed.
function allowedThen(snapshot: Snapshot, path: string, address: string | null, revision: string | null): boolean {
  if (!address || !revision || /^0+$/.test(revision)) return false;
  const saved = snapshot.revisions[revision];
  if (!saved) throw new Unreadable("authority-unavailable");
  return authorityFrom(saved.documents[path] ?? null, saved.map).includes(address);
}

function documentPaths(snapshot: Snapshot): string[] {
  // os.walk of context/ (each folder's files sorted, folders sorted, depth
  // first), then the standards in name order, then the source map.
  const context = walkOrder(Object.keys(snapshot.files).filter((path) => path.startsWith("context/") && path.endsWith(".md")));
  const standards = Object.keys(snapshot.files)
    .filter((path) => path.startsWith("standards/") && !path.slice(10).includes("/"))
    .sort((a, b) => cmp(a, b))
    .filter((path) => classify(path) === "standard");
  const stack = STACK_PATH in snapshot.files ? [STACK_PATH] : [];
  return [...context, ...standards, ...stack];
}

function contextDocuments(snapshot: Snapshot): DocumentInfo[] {
  const mapText = snapshot.files["context/map.md"] ?? null;
  return documentPaths(snapshot).map((path) => {
    const text = snapshot.files[path];
    let fields: Record<string, Value> = {};
    try {
      fields = parseFrontmatter(splitDocument(text).block);
    } catch (error) {
      if (!(error instanceof Refused)) throw error;
    }
    let owners: string[] = [];
    try {
      owners = validateOwner(fields.owner);
    } catch (error) {
      if (!(error instanceof Refused)) throw error;
    }
    // Python's `str(value or "")`: an empty list is falsy there, unlike here.
    const truthy = (value: Value | undefined) => (Array.isArray(value) ? value.length > 0 : !!value);
    const status = truthy(fields.status) ? pyStr(fields.status) : "";
    const kind = truthy(fields.kind) ? pyStr(fields.kind) : "";
    return {
      path,
      owners,
      authority: authorityFrom(text, mapText),
      present: status !== "skipped",
      isMap: kind.trim().toLowerCase() === "map",
      openQuestion: holdsAnOpenQuestion(text),
    };
  });
}

function walkOrder(paths: string[]): string[] {
  type Node = { files: string[]; dirs: Map<string, Node> };
  const root: Node = { files: [], dirs: new Map() };
  for (const path of paths) {
    const parts = path.split("/").slice(1);
    let node = root;
    for (const part of parts.slice(0, -1)) {
      if (!node.dirs.has(part)) node.dirs.set(part, { files: [], dirs: new Map() });
      node = node.dirs.get(part)!;
    }
    node.files.push(path);
  }
  const out: string[] = [];
  const visit = (node: Node) => {
    out.push(...[...node.files].sort((a, b) => cmp(a.split("/").pop()!, b.split("/").pop()!)));
    for (const name of [...node.dirs.keys()].sort(cmp)) visit(node.dirs.get(name)!);
  };
  visit(root);
  return out;
}

// Python compares strings by code point; so does this.
function cmp(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function readEntries(snapshot: Snapshot): ChangeEntry[] {
  const entries: ChangeEntry[] = [];
  for (const path of sortedPaths(snapshot, CHANGES_DIR)) {
    let entry: ChangeEntry;
    try {
      entry = parseChangeEntry(snapshot.files[path]);
    } catch (error) {
      if (error instanceof Refused) continue;
      throw error;
    }
    if (path.split("/").pop() !== `${entry.id}.md`) continue;
    const kept: string[] = [];
    for (const affected of entry.affects) {
      const where = whereItLives(snapshot, affected);
      try {
        kept.push(checkDocumentPathSyntax(where));
      } catch (error) {
        if (!(error instanceof Refused)) throw error;
      }
    }
    entries.push({ ...entry, affects: kept });
  }
  return entries;
}

type OwnedLine = { file: string; date: string; trigger: string; entry: string | null; run: string | null };

function readConfirmations(snapshot: Snapshot): { line: ConfirmationLine; allowed: boolean }[] {
  const records: { line: ConfirmationLine; allowed: boolean }[] = [];
  for (const path of sortedPaths(snapshot, CONFIRMATIONS_DIR)) {
    const authors = snapshot.confirmationAuthors[path];
    if (!authors) throw new Unreadable("authors-unavailable");
    snapshot.files[path].split("\n").forEach((raw, index) => {
      const text = raw.replace(/^\s+|\s+$/g, "");
      if (!text || text.startsWith("#")) return;
      let line: ConfirmationLine;
      try {
        line = parseConfirmationLine(text);
      } catch (error) {
        if (error instanceof Refused) return;
        throw error;
      }
      line = { ...line, file: whereItLives(snapshot, line.file) };
      const author = authors[String(index + 1)];
      records.push({ line, allowed: allowedThen(snapshot, line.file, author?.email ?? null, author?.revision ?? null) });
    });
  }
  return records;
}

// --- The rules (stale.compute, the moment-of-use part) -------------------------

function lineConfirms(line: OwnedLine, entry: ChangeEntry): boolean {
  if (line.entry) return line.entry === entry.id;
  if (line.trigger === "drafted" && line.run && entry.runId && line.run === entry.runId) return true;
  if (line.date === entry.happenedOn) return false;
  const later = entry.writtenOn > entry.happenedOn ? entry.writtenOn : entry.happenedOn;
  return line.date > later;
}

export function verdictOf(snapshot: Snapshot): Verdict {
  const all = Object.keys(snapshot.files);
  if (all.some((path) => OLDER_FOLDERS.some((folder) => path.startsWith(folder)) || OLDER_FILES.includes(path))) {
    throw new Unreadable(OLDER_LAYOUT);
  }
  const day = snapshot.today;

  // _index_files
  const documents = new Map<string, DocumentInfo>();
  for (const info of contextDocuments(snapshot)) {
    try {
      documents.set(checkDocumentPathSyntax(info.path), info);
    } catch (error) {
      if (!(error instanceof Refused)) throw error;
    }
  }

  // _usable_entries, ordered by (written_on, id)
  const entries: ChangeEntry[] = [];
  for (const entry of readEntries(snapshot)) {
    try {
      entries.push(validateChangeEntry(entry, day));
    } catch (error) {
      if (!(error instanceof Refused)) throw error;
    }
  }
  entries.sort((a, b) => cmp(a.writtenOn, b.writtenOn) || cmp(a.id, b.id));

  // _index_confirmations
  const ownerLines = new Map<string, OwnedLine[]>();
  for (const { line, allowed } of readConfirmations(snapshot)) {
    try {
      validateConfirmationLine(line);
    } catch (error) {
      if (error instanceof Refused) continue;
      throw error;
    }
    const info = documents.get(line.file);
    if (!info) continue;
    // Counted when its author could confirm this document when they saved it.
    if (allowed) {
      const list = ownerLines.get(line.file) ?? [];
      list.push(line);
      ownerLines.set(line.file, list);
    }
  }

  // _corrections_confirmations
  const settled = new Set<string>();
  const accepted = new Map<string, string>(); // path -> newest owner acceptance date
  for (const path of sortedPaths(snapshot, CORRECTIONS_DIR)) {
    let record;
    try {
      record = parseCorrectionsFile(snapshot.files[path]);
    } catch (error) {
      if (error instanceof Refused) continue;
      throw error;
    }
    const facts = snapshot.corrections[path];
    if (!facts) throw new Unreadable("record-history-unavailable");
    if (!record.entryId) continue;
    const touched = record.touchedPaths.map((p) => whereItLives(snapshot, p));
    const coModified = facts.coModified.map((p) => whereItLives(snapshot, p));
    const acceptedPaths = facts.acceptedPaths == null ? null : facts.acceptedPaths.map((p) => whereItLives(snapshot, p));
    // Whether whoever accepted it could do so then, for each document it touched.
    const mergedAllowed = new Map(touched.map((p) => [p, allowedThen(snapshot, p, facts.mergedBy, facts.mergedIn)]));
    for (const touchedPath of touched) {
      const info = documents.get(touchedPath);
      if (!info) continue;
      if (!coModified.includes(touchedPath)) continue;
      if (!facts.hashAtCommit || facts.hashAtCommit !== record.contentHash) continue;
      if (acceptedPaths && !acceptedPaths.includes(touchedPath)) continue;
      settled.add(`${record.entryId}\n${touchedPath}`);
      if (!facts.mergedOn || !facts.mergedBy || !/^\d{4}-\d{2}-\d{2}$/.test(facts.mergedOn)) continue;
      if (!mergedAllowed.get(touchedPath)) continue;
      const standing = accepted.get(touchedPath);
      if (!standing || facts.mergedOn > standing) accepted.set(touchedPath, facts.mergedOn);
    }
  }

  // _file_flags, the ledger trigger only. A document still holding an open
  // question counts none of its owners' yeses (_while_no_question_is_open).
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  const overtakenBy = new Map<string, ChangeEntry>();
  for (const path of [...documents.keys()].sort(cmp)) {
    const info = documents.get(path)!;
    if (!info.present || info.isMap) continue;
    const lines: OwnedLine[] = info.openQuestion ? [] : [...(ownerLines.get(path) ?? [])];
    const acceptance = info.openQuestion ? undefined : accepted.get(path);
    if (acceptance) lines.push({ file: path, date: acceptance, trigger: "accepted", entry: null, run: null });
    for (const entry of entries) {
      if (entry.status !== "open" || !entry.affects.includes(path)) continue;
      if (settled.has(`${entry.id}\n${path}`)) continue;
      if (lines.some((line) => lineConfirms(line, entry))) continue;
      overtakenBy.set(path, entry);
      break;
    }
  }
  return { documents, overtakenBy, entries: byId };
}

// ids.content_hash: SHA-256 of the text with line endings made uniform.
export async function contentHash(text: string): Promise<string> {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const { createHash } = await import("node:crypto");
  return createHash("sha256").update(normalized, "utf8").digest("hex");
}
