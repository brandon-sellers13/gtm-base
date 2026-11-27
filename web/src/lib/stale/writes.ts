import "server-only";
import { randomBytes } from "node:crypto";
import { GitHubError, api } from "../github";
import {
  checkDocumentPathSyntax,
  parseChangeEntry,
  parseConfirmationLine,
  parseCorrectionsFile,
  splitDocument,
  validateChangeEntry,
} from "./formats";
import { contentHash } from "./rules";
import { touchesSkills } from "./skills";

// Everything the connector and the web app write into a base, in the plugin's
// own formats, so Claude Code reads it exactly as it reads its own. Each text is
// read back with the ported parsers before anything is written; a text they
// refuse is never sent.

export const newStagingId = () => `stg-${randomBytes(8).toString("hex")}`;

const ABOUT_SENTENCE =
  "This proposal was drafted by an AI assistant from the evidence above and has not been reviewed by a person yet.";
const KEEP_THE_CHANGE_HINT = "If the context change is right but the edit is wrong, say keep the change and drop the edit.";

export const markerLine = (staging: string, entry: string | null) =>
  `gtm-base proposal ${staging} entry ${entry ?? "-"} source -`;

const oneLine = (text: string) => text.replace(/\s+/g, " ").trim();

// formats.render_pr_body
export function prBody(fields: { before: string; after: string; why: string; evidence: string; confidence: string; marker: string }) {
  return (
    `## What changed\n\nBefore: ${fields.before.trim()}\n\nAfter: ${fields.after.trim()}\n\n` +
    `## Why\n\n${fields.why.trim()}\n\n## Evidence\n\n${fields.evidence.trim()}\n\n` +
    `## Confidence\n\n${fields.confidence.trim()}\n\n## Rule being changed\n\nNone\n\n` +
    `## About this proposal\n\n${ABOUT_SENTENCE}\n\n${KEEP_THE_CHANGE_HINT}\n\n${fields.marker}\n`
  );
}

// One new context change, as the plugin writes one.
export function changeEntryText(options: {
  id: string;
  happenedOn: string;
  today: string;
  reviewBy: string;
  notedBy: string;
  source: string;
  affects: string[];
  whatChanged: string;
  why: string;
}): string {
  for (const path of options.affects) {
    checkDocumentPathSyntax(path);
    if (path.includes(",")) throw new Error("A document path with a comma cannot be listed.");
  }
  const text =
    [
      "---",
      `id: ${options.id}`,
      "kind: change",
      `happened_on: ${options.happenedOn}`,
      `written_on: ${options.today}`,
      `noted_by: ${options.notedBy}`,
      `source: ${oneLine(options.source)}`,
      `affects: [${options.affects.join(", ")}]`,
      `review_by: ${options.reviewBy}`,
      "origin: manual",
      "status: open",
      "---",
      "",
      oneLine(options.whatChanged),
      oneLine(options.why),
    ].join("\n") + "\n";
  validateChangeEntry(parseChangeEntry(text), options.today);
  return text;
}

// The record an accepted fix leaves behind, which settles the change for the
// document it fixed (the three tests of rules.md).
export async function correctionsRecordText(options: {
  staging: string;
  entryId: string;
  today: string;
  path: string;
  newDocumentText: string;
  whatChanged: string;
  why: string;
}): Promise<string> {
  const text =
    [
      "---",
      "kind: correction",
      `date: ${options.today}`,
      `staging_id: ${options.staging}`,
      `entry_id: ${options.entryId}`,
      "source_id: -",
      "intake_path: ledger",
      "mode: decision",
      "third_party: false",
      `content_hash: ${await contentHash(options.newDocumentText)}`,
      `touched_paths: [${options.path}]`,
      "correction_class: new-decision",
      `marker: ${markerLine(options.staging, options.entryId)}`,
      "---",
      "",
      "## What changed",
      "",
      oneLine(options.whatChanged),
      "",
      "## Why",
      "",
      oneLine(options.why),
    ].join("\n") + "\n";
  const parsed = parseCorrectionsFile(text);
  if (parsed.entryId !== options.entryId || parsed.touchedPaths[0] !== options.path) throw new Error("record did not read back");
  return text;
}

// A document with its settings block kept exactly as it is and a new body.
export function withNewBody(current: string, newBody: string): string {
  const { block } = splitDocument(current);
  const body = newBody.replace(/^\s*---[\s\S]*?\n---\s*\n/, "").replace(/^\n+/, "");
  return `---\n${block}\n---\n\n${body.endsWith("\n") ? body : body + "\n"}`;
}

// --- Writing through GitHub ----------------------------------------------------------

const path = (owner: string, repo: string) => `/repos/${owner}/${repo}`;

export async function openProposal(options: {
  token: string;
  owner: string;
  repo: string;
  staging: string;
  files: Record<string, string>;
  title: string;
  body: string;
}): Promise<{ number: number; url: string }> {
  const { token, owner, repo } = options;
  // The connector never writes into a base's skills folder (C3).
  if (touchesSkills(Object.keys(options.files))) throw new Error("A proposal may not write into the skills folder.");
  const info = await api<{ default_branch: string }>(path(owner, repo), { token });
  const tip = await api<{ object: { sha: string } }>(
    `${path(owner, repo)}/git/ref/heads/${encodeURIComponent(info.default_branch)}`,
    { token },
  );
  const base = await api<{ tree: { sha: string } }>(`${path(owner, repo)}/git/commits/${tip.object.sha}`, { token });
  const tree = await api<{ sha: string }>(`${path(owner, repo)}/git/trees`, {
    token,
    method: "POST",
    body: JSON.stringify({
      base_tree: base.tree.sha,
      tree: Object.entries(options.files).map(([file, content]) => ({ path: file, mode: "100644", type: "blob", content })),
    }),
  });
  const commit = await api<{ sha: string }>(`${path(owner, repo)}/git/commits`, {
    token,
    method: "POST",
    body: JSON.stringify({ message: options.title, tree: tree.sha, parents: [tip.object.sha] }),
  });
  const branch = `proposal/${options.staging}`;
  await api(`${path(owner, repo)}/git/refs`, {
    token,
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${branch}`, sha: commit.sha }),
  });
  const pull = await api<{ number: number; html_url: string }>(`${path(owner, repo)}/pulls`, {
    token,
    method: "POST",
    body: JSON.stringify({ title: options.title, head: branch, base: info.default_branch, body: options.body }),
  });
  return { number: pull.number, url: pull.html_url };
}

export const confirmationsFileFor = (document: string) => `work/confirmations/${document.replace(/\//g, "--")}`;

// The owner's "it already reflects this change": one confirmation line naming
// that change, committed on the default branch with the owner's verified email
// as its author, which is the identity the rules read with blame.
export async function appendConfirmation(options: {
  token: string;
  owner: string;
  repo: string;
  document: string;
  entryId: string;
  email: string;
  name: string;
  now: Date;
}): Promise<void> {
  const { token, owner, repo } = options;
  const iso = options.now.toISOString();
  const line = `date=${iso.slice(0, 10)} time=${iso.slice(11, 19)}Z file=${options.document} trigger=ledger entry=${options.entryId} question=- run=-`;
  parseConfirmationLine(line);
  const file = confirmationsFileFor(options.document);
  const url = `${path(owner, repo)}/contents/${file.split("/").map(encodeURIComponent).join("/")}`;
  let current = "";
  let sha: string | undefined;
  try {
    const found = await api<{ content: string; sha: string }>(url, { token });
    current = Buffer.from(found.content, "base64").toString("utf8");
    sha = found.sha;
  } catch (error) {
    if (!(error instanceof GitHubError && error.status === 404)) throw error;
  }
  const text = (current && !current.endsWith("\n") ? current + "\n" : current) + line + "\n";
  await api(url, {
    token,
    method: "PUT",
    body: JSON.stringify({
      message: `Confirm ${options.document} reflects ${options.entryId}`,
      content: Buffer.from(text, "utf8").toString("base64"),
      ...(sha ? { sha } : {}),
      author: { name: options.name, email: options.email, date: iso },
      committer: { name: options.name, email: options.email, date: iso },
    }),
  });
}
