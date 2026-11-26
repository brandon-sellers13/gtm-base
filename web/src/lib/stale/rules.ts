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
  checkContextPathSyntax,
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
};

export type Snapshot = {
  today: string; // YYYY-MM-DD
  // Text of every file under context/, learning/changes/, learning/corrections/
  // and work/confirmations/ on the default branch.
  files: Record<string, string>;
  // For each confirmations file, the author email of each line, by line number.
  confirmationAuthors: Record<string, Record<string, string>>;
  // For each records file under learning/corrections/.
  corrections: Record<string, CorrectionFacts>;
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

function contextDocuments(snapshot: Snapshot): DocumentInfo[] {
  // os.walk of context/: each folder's files sorted, folders sorted, depth first.
  const paths = Object.keys(snapshot.files).filter((path) => path.startsWith("context/") && path.endsWith(".md"));
  return walkOrder(paths).map((path) => {
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
        kept.push(checkContextPathSyntax(where));
      } catch (error) {
        if (!(error instanceof Refused)) throw error;
      }
    }
    entries.push({ ...entry, affects: kept });
  }
  return entries;
}

type OwnedLine = { file: string; date: string; trigger: string; entry: string | null; run: string | null };

function readConfirmations(snapshot: Snapshot): { line: ConfirmationLine; author: string | null }[] {
  const records: { line: ConfirmationLine; author: string | null }[] = [];
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
      records.push({ line, author: authors[String(index + 1)] ?? null });
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
      documents.set(checkContextPathSyntax(info.path), info);
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
  for (const { line, author } of readConfirmations(snapshot)) {
    try {
      validateConfirmationLine(line);
    } catch (error) {
      if (error instanceof Refused) continue;
      throw error;
    }
    const info = documents.get(line.file);
    if (!info) continue;
    if (author !== null && info.owners.includes(author)) {
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
    for (const touchedPath of touched) {
      const info = documents.get(touchedPath);
      if (!info) continue;
      if (!coModified.includes(touchedPath)) continue;
      if (!facts.hashAtCommit || facts.hashAtCommit !== record.contentHash) continue;
      settled.add(`${record.entryId}\n${touchedPath}`);
      if (!facts.mergedOn || !facts.mergedBy || !/^\d{4}-\d{2}-\d{2}$/.test(facts.mergedOn)) continue;
      if (!info.owners.includes(facts.mergedBy)) continue;
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
