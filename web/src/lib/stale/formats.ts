// The plugin's file formats, ported from plugins/gtm-base/lib/gtmbase
// (formats.py, paths.py, ids.py, validate.py, callmarkers.py) for the one
// question the connector asks: has a recorded context change overtaken this
// document. Every rule here mirrors the Python exactly, including what it
// refuses, and the parity check (web/scripts/stale-parity.mjs) holds the two
// together. Pure functions only: no network, no clock, no file system.

// --- Errors, mirroring the plugin's three kinds ------------------------------

// ValidationError and PathError in the plugin: a refusal a reader skips past.
export class Refused extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "Refused";
  }
}
// The plugin raises a bare ValueError for a malformed identifier, which nothing
// on the moment-of-use path catches, so the whole check fails. Mirrored as its
// own kind so the caller can say it cannot vouch for the document.
export class Unreadable extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "Unreadable";
  }
}

// --- Plain values ------------------------------------------------------------

export type Scalar = string | number | boolean;
export type Value = Scalar | Scalar[];

const KEY_RE = /^[a-z0-9_]+$/;
const INT_RE = /^-?\d+$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^\d{2}:\d{2}:\d{2}Z$/;
export const EMPTY = "-";

// Python's str() of a parsed value, which is how the plugin reads every field.
export function pyStr(value: Value | null | undefined): string {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) {
    return "[" + value.map((item) => (typeof item === "string" ? `'${item}'` : pyStr(item))).join(", ") + "]";
  }
  return value;
}

// Python's str.strip(): only whitespace, which in Python includes more than JS's \s
// for a few control characters; the plugin's files are text, so \s is close enough
// for every character a base holds, and the parity fixtures check it.
const strip = (text: string) => text.replace(/^\s+|\s+$/g, "");

// --- The settings block ------------------------------------------------------

export function splitDocument(text: string): { block: string; body: string } {
  let body = text;
  if (body.startsWith("﻿")) body = body.slice(1);
  const lines = body.split("\n");
  if (!lines.length || strip(lines[0]) !== "---") throw new Refused("no-frontmatter");
  for (let index = 1; index < lines.length; index++) {
    if (strip(lines[index]) === "---") {
      const block = lines.slice(1, index).join("\n");
      let rest = lines.slice(index + 1).join("\n");
      if (rest.startsWith("\n")) rest = rest.slice(1);
      return { block, body: rest };
    }
  }
  throw new Refused("unclosed-frontmatter");
}

export function parseScalar(text: string): Scalar {
  const value = strip(text);
  if (value.startsWith("{")) throw new Refused("nested-mapping");
  if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) {
    const inner = value.slice(1, -1);
    if (inner.includes(value[0])) throw new Refused("bad-quote");
    return inner;
  }
  if (value === "true") return true;
  if (value === "false") return false;
  if (INT_RE.test(value)) return Number.parseInt(value, 10);
  return value;
}

function parseInlineList(text: string): Scalar[] {
  const inner = strip(strip(text).slice(1, -1));
  if (!inner) return [];
  if (inner.includes("[") || inner.includes("]")) throw new Refused("nested-list");
  return inner.split(",").map(parseScalar);
}

export function parseFrontmatter(block: string): Record<string, Value> {
  const fields: Record<string, Value> = {};
  let openListKey: string | null = null;
  for (const raw of block.split("\n")) {
    if (raw.includes("\t")) throw new Refused("tab");
    if (!strip(raw)) {
      openListKey = null;
      continue;
    }
    const stripped = raw.replace(/^ +/, "");
    if (stripped.startsWith("- ") || stripped === "-") {
      if (openListKey === null) throw new Refused("orphan-list-item");
      const item = strip(stripped.slice(1));
      (fields[openListKey] as Scalar[]).push(item ? parseScalar(item) : "");
      continue;
    }
    if (raw !== stripped) throw new Refused("nested-mapping");
    if (!raw.includes(":")) throw new Refused("not-a-setting");
    const at = raw.indexOf(":");
    const key = strip(raw.slice(0, at));
    const value = strip(raw.slice(at + 1));
    if (!KEY_RE.test(key)) throw new Refused("bad-key");
    if (key in fields) throw new Refused("duplicate-key");
    if (!value) {
      fields[key] = [];
      openListKey = key;
      continue;
    }
    openListKey = null;
    fields[key] = value.startsWith("[") && value.endsWith("]") ? parseInlineList(value) : parseScalar(value);
  }
  return fields;
}

function requireField(fields: Record<string, Value>, name: string): Value {
  if (!(name in fields)) throw new Refused("missing-field");
  const value = fields[name];
  if (typeof value === "string" && !strip(value)) throw new Refused("missing-field");
  return value;
}

export function asDate(value: string): string {
  const text = strip(value);
  if (!DATE_RE.test(text)) throw new Refused("bad-date");
  const [y, m, d] = [Number(text.slice(0, 4)), Number(text.slice(5, 7)), Number(text.slice(8, 10))];
  const day = new Date(Date.UTC(y, m - 1, d));
  if (y < 1 || day.getUTCFullYear() !== y || day.getUTCMonth() !== m - 1 || day.getUTCDate() !== d) {
    throw new Refused("bad-date");
  }
  return text;
}

function asList(value: Value | undefined): string[] {
  if (Array.isArray(value)) return value.map((item) => pyStr(item));
  if (value === undefined || value === "" || value === EMPTY) return [];
  throw new Refused("not-a-list");
}

function asBool(value: Value): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string" && (strip(value) === "true" || strip(value) === "false")) return strip(value) === "true";
  throw new Refused("not-a-boolean");
}

function optional(value: Value | undefined): string | null {
  if (value === undefined) return null;
  const text = strip(pyStr(value));
  return text === "" || text === EMPTY ? null : text;
}

function inVocabulary(value: string, allowed: readonly string[]): string {
  const text = strip(value);
  if (!allowed.includes(text)) throw new Refused("unknown-value");
  return text;
}

export function splitSections(body: string): Record<string, string> {
  const sections: Record<string, string> = {};
  let name: string | null = null;
  let collected: string[] = [];
  for (const line of body.split("\n")) {
    if (line.startsWith("## ")) {
      if (name !== null) sections[name] = collected.join("\n").replace(/^\n+|\n+$/g, "");
      name = strip(line.slice(3));
      collected = [];
    } else if (name !== null) {
      collected.push(line);
    }
  }
  if (name !== null) sections[name] = collected.join("\n").replace(/^\n+|\n+$/g, "");
  return sections;
}

// --- Identifiers and paths ---------------------------------------------------

const STAGING_RE = /^stg-[0-9a-f]{16}$/;
const RUN_RE = /^run-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$/;
const QUESTION_RE = /^q-[0-9a-f]{20}$/;

export const isStagingId = (value: unknown) => typeof value === "string" && STAGING_RE.test(value);
export function checkStagingId(value: string): string {
  if (!isStagingId(value)) throw new Unreadable("bad-staging-id");
  return value;
}
function checkRunId(value: string): string {
  if (!RUN_RE.test(value)) throw new Unreadable("bad-run-id");
  return value;
}

const MAX_PATH_LENGTH = 400;
const FORBIDDEN_PATH_CHARACTERS = ["[", "]", "(", ")", "\\", '"', "'", "|", "*", "?", "`", "$", ";", "&", "<", ">"];

export function checkRepoPathSyntax(candidate: unknown, prefixes: readonly string[]): string {
  if (typeof candidate !== "string" || !strip(candidate)) throw new Refused("empty-path");
  const text = strip(candidate);
  if (text.length > MAX_PATH_LENGTH) throw new Refused("long-path");
  for (const character of text) {
    const code = character.codePointAt(0)!;
    if (code < 32 || code === 127) throw new Refused("control-character");
  }
  for (const character of FORBIDDEN_PATH_CHARACTERS) if (text.includes(character)) throw new Refused("bad-character");
  if (text.startsWith("/") || text.startsWith("~")) throw new Refused("absolute-path");
  if (text.length > 1 && text[1] === ":") throw new Refused("absolute-path");
  for (const segment of text.split("/")) if (segment === "" || segment === "." || segment === "..") throw new Refused("climbing-path");
  for (const prefix of prefixes) if (text.startsWith(prefix) && text.length > prefix.length) return text;
  throw new Refused("outside-base");
}

export const checkContextPathSyntax = (candidate: unknown) => checkRepoPathSyntax(candidate, ["context/"]);

// docpaths.py: since Plan 1's Unit 4.2a a standard (standards/<job>.md) and
// the source map (access/stack.md) are documents too, wherever a record names one.
const JOB_NAME = "[a-z0-9]+(?:-[a-z0-9]+)*";
const STANDARD_RE = new RegExp(`^standards/(${JOB_NAME})\\.md$`);
export const STACK_PATH = "access/stack.md";
const DOC_PREFIXES = ["context/", "standards/", "access/", "skills/", "learning/lessons/"];

export type DocKind = "context" | "standard" | "stack" | "other";

// docpaths.classify, for the kinds the moment of use reads.
export function classify(candidate: unknown): DocKind | null {
  let text: string;
  try {
    text = checkRepoPathSyntax(candidate, DOC_PREFIXES);
  } catch (error) {
    if (error instanceof Refused) return null;
    throw error;
  }
  if (text.startsWith("context/")) return text === "context/map.md" || !text.endsWith(".md") ? null : "context";
  if (text === STACK_PATH) return "stack";
  if (STANDARD_RE.test(text)) return "standard";
  return "other";
}

// docpaths.check_syntax: the context folder's check, widened to a standard and the source map.
export function checkDocumentPathSyntax(candidate: unknown): string {
  try {
    return checkContextPathSyntax(candidate);
  } catch (error) {
    const kind = classify(candidate);
    if (kind === "standard" || kind === "stack") return checkRepoPathSyntax(candidate, DOC_PREFIXES);
    throw error;
  }
}

const EMAIL_RE =
  /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/;

export function isValidEmail(value: unknown): boolean {
  if (typeof value !== "string") return false;
  if (value.length > 254 || value !== strip(value)) return false;
  if (!/^[\x00-\x7f]*$/.test(value)) return false;
  return EMAIL_RE.test(value);
}

export function validateOwner(value: Value | undefined): string[] {
  let candidates: Scalar[];
  if (Array.isArray(value)) candidates = value;
  else if (typeof value === "string") {
    const text = strip(value);
    if (text.startsWith("[") && text.endsWith("]")) {
      const inner = strip(text.slice(1, -1));
      candidates = inner ? inner.split(",").map(strip) : [];
    } else candidates = [text];
  } else throw new Refused("owner-invalid");
  if (!candidates.length) throw new Refused("owner-empty");
  return candidates.map((candidate) => {
    if (!isValidEmail(candidate)) throw new Refused("owner-invalid");
    return candidate as string;
  });
}

// --- A context change --------------------------------------------------------

const CHANGE_FIELDS = ["id", "kind", "happened_on", "written_on", "noted_by", "source", "affects", "review_by", "origin", "run_id", "status"];
const CHANGE_REQUIRED = ["id", "kind", "happened_on", "written_on", "noted_by", "source", "review_by", "origin", "status"];
const ENTRY_FIELD_PAIRS: [string, string][] = [
  ["happened_on", "decided_on"],
  ["noted_by", "decided_by"],
];
const ENTRY_KINDS = ["change", "decision"];
const LEDGER_ORIGINS = ["inbox", "ledger", "local-edit", "reject-keep", "join", "manual"];
const LEDGER_STATUSES = ["open", "done", "dismissed"];

export type ChangeEntry = {
  id: string;
  happenedOn: string;
  writtenOn: string;
  notedBy: string;
  source: string;
  reviewBy: string;
  origin: string;
  status: string;
  affects: string[];
  runId: string | null;
  body: string;
};

function foldFieldNames(fields: Record<string, Value>): Record<string, Value> {
  const folded = { ...fields };
  for (const [next, old] of ENTRY_FIELD_PAIRS) {
    if (!(old in folded)) continue;
    const older = folded[old];
    delete folded[old];
    const current = folded[next];
    const empty = current === undefined || (typeof current === "string" && !strip(current));
    if (empty) {
      folded[next] = older;
      continue;
    }
    if (strip(pyStr(current)) !== strip(pyStr(older))) throw new Refused("two-spellings-disagree");
  }
  return folded;
}

export function parseChangeEntry(text: string): ChangeEntry {
  const { block, body } = splitDocument(text);
  const fields = foldFieldNames(parseFrontmatter(block));
  for (const name of Object.keys(fields)) if (!CHANGE_FIELDS.includes(name)) throw new Refused("unknown-field");
  for (const name of CHANGE_REQUIRED) requireField(fields, name);
  if (!ENTRY_KINDS.includes(strip(pyStr(fields.kind)))) throw new Refused("wrong-kind");
  const s = (name: string) => strip(pyStr(fields[name]));
  return {
    id: s("id"),
    happenedOn: s("happened_on"),
    writtenOn: s("written_on"),
    notedBy: s("noted_by"),
    source: s("source"),
    reviewBy: s("review_by"),
    origin: s("origin"),
    status: s("status"),
    affects: asList(fields.affects ?? []),
    runId: optional(fields.run_id),
    body: body.replace(/^\n+|\n+$/g, ""),
  };
}

// ChangeEntry.validate: the order of the checks matters, because a malformed
// identifier stops the whole check (Unreadable) where any other problem only
// sets the entry aside (Refused).
export function validateChangeEntry(entry: ChangeEntry, today: string): ChangeEntry {
  checkStagingId(entry.id);
  if (!strip(entry.notedBy)) throw new Refused("missing-field");
  if (!strip(entry.source)) throw new Refused("missing-field");
  const happened = asDate(entry.happenedOn);
  const written = asDate(entry.writtenOn);
  const review = asDate(entry.reviewBy);
  if (happened > today) throw new Refused("decided-in-future");
  if (review < happened) throw new Refused("review-before-decision");
  if (written < happened) throw new Refused("written-before-decision");
  inVocabulary(entry.origin, LEDGER_ORIGINS);
  inVocabulary(entry.status, LEDGER_STATUSES);
  if (entry.runId !== null) checkRunId(entry.runId);
  for (const path of entry.affects) checkDocumentPathSyntax(path);
  if (!strip(entry.body)) throw new Refused("missing-body");
  return entry;
}

// --- A confirmation line -----------------------------------------------------

const CONFIRMATION_TOKENS = ["date", "time", "file", "trigger", "entry", "question", "run"];
const CONFIRMATION_TRIGGERS = ["threshold", "ledger", "drafted"];

export type ConfirmationLine = {
  date: string;
  time: string;
  file: string;
  trigger: string;
  entry: string | null;
  question: string | null;
  run: string | null;
  role: string | null;
};

export function parseConfirmationLine(line: string): ConfirmationLine {
  const parts = strip(line)
    .split(" ")
    .filter((part) => part);
  // An eighth value, the role that allowed it, may follow (Plan 1, Unit 4.2a).
  const expectedTokens =
    parts.length === CONFIRMATION_TOKENS.length + 1 ? [...CONFIRMATION_TOKENS, "role"] : CONFIRMATION_TOKENS;
  if (parts.length !== expectedTokens.length) throw new Refused("wrong-token-count");
  const values: Record<string, string> = {};
  expectedTokens.forEach((expected, index) => {
    const part = parts[index];
    const at = part.indexOf("=");
    if (at < 0 || part.slice(0, at) !== expected) throw new Refused("wrong-token-order");
    values[expected] = part.slice(at + 1);
  });
  return validateConfirmationLine({
    date: values.date,
    time: values.time,
    file: values.file,
    trigger: values.trigger,
    entry: optional(values.entry),
    question: optional(values.question),
    run: optional(values.run),
    role: "role" in values ? values.role : null,
  });
}

export function validateConfirmationLine(line: ConfirmationLine): ConfirmationLine {
  if (!DATE_RE.test(line.date)) throw new Refused("bad-date");
  asDate(line.date);
  if (!TIME_RE.test(line.time)) throw new Refused("bad-time");
  checkDocumentPathSyntax(line.file);
  inVocabulary(line.trigger, CONFIRMATION_TRIGGERS);
  if (line.entry !== null) checkStagingId(line.entry);
  if (line.question !== null && !QUESTION_RE.test(line.question)) throw new Refused("bad-question-id");
  if (line.run !== null) checkRunId(line.run);
  if (line.trigger === "drafted" && line.run === null) throw new Refused("drafted-without-run");
  if (line.trigger === "ledger" && line.entry === null) throw new Refused("ledger-without-entry");
  return line;
}

// --- An accepted record of what changed --------------------------------------

const CORRECTIONS_FIELDS = [
  "kind",
  "date",
  "staging_id",
  "entry_id",
  "source_id",
  "intake_path",
  "mode",
  "third_party",
  "content_hash",
  "touched_paths",
  "correction_class",
  "marker",
  "approved_roles",
  "approved_hashes",
];

// formats._pairs: a list of path=value items, read into a mapping from path
// to value (a later item for the same path wins, as in a Python dict).
function pairs(value: Value | undefined): Record<string, string> {
  const found: Record<string, string> = {};
  for (const item of asList(value ?? [])) {
    const at = item.lastIndexOf("=");
    if (at < 0 || !item.slice(0, at) || !item.slice(at + 1)) throw new Refused("bad-pair");
    found[item.slice(0, at)] = item.slice(at + 1);
  }
  return found;
}

export type CorrectionsFile = {
  entryId: string | null;
  contentHash: string;
  touchedPaths: string[];
  // Since Plan 1's Unit 4.2b: the role and the exact hash each approved file
  // was approved with (a skill's approval names every file of the skill).
  approvedRoles: Record<string, string>;
  approvedHashes: Record<string, string>;
};

// CorrectionsFile.parse; the plugin does not validate it on this path.
export function parseCorrectionsFile(text: string): CorrectionsFile {
  const { block } = splitDocument(text);
  const fields = parseFrontmatter(block);
  for (const name of Object.keys(fields)) if (!CORRECTIONS_FIELDS.includes(name)) throw new Refused("unknown-field");
  for (const name of ["kind", "date", "staging_id", "intake_path", "mode", "content_hash", "correction_class", "marker"]) {
    requireField(fields, name);
  }
  if (!("third_party" in fields)) throw new Refused("missing-field");
  asBool(fields.third_party);
  const touchedPaths = asList(fields.touched_paths ?? []);
  const approvedRoles = pairs(fields.approved_roles);
  const approvedHashes = pairs(fields.approved_hashes);
  return {
    entryId: optional(fields.entry_id),
    contentHash: strip(pyStr(fields.content_hash)),
    touchedPaths,
    approvedRoles,
    approvedHashes,
  };
}

// --- An open question a draft left in a document -----------------------------

const YOUR_CALL_RE = /\[\s*your\s+call\s*:([^\]\n]*)(?:\]|$)/i;

export function holdsAnOpenQuestion(text: string): boolean {
  const lines = text.split("\n");
  let start = 0;
  if (lines.length && strip(lines[0]) === "---") {
    for (let index = 1; index < lines.length; index++) {
      if (strip(lines[index]) === "---") {
        start = index + 1;
        break;
      }
    }
  }
  return lines.slice(start).some((line) => YOUR_CALL_RE.test(line));
}
