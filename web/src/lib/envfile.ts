import "server-only";
import { randomBytes } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

// Development only: merges new settings into an env file, keeping every line
// it does not replace. Values are written, never returned or logged.

export const LOCAL_ENV_FILE = path.join(process.cwd(), ".env.local");
// Settings for the live address. Next never loads this file; scripts/send-live-settings.mjs sends it to Netlify.
export const LIVE_ENV_FILE = path.join(process.cwd(), ".env.live");

export function mergeEnv(existing: string, updates: Record<string, string>): string {
  const lines = existing === "" ? [] : existing.replace(/\n+$/, "").split("\n");
  const seen = new Set<string>();
  const merged = lines.map((line) => {
    const key = line.match(/^([A-Z0-9_]+)=/)?.[1];
    if (key && key in updates) {
      seen.add(key);
      return `${key}=${quote(updates[key])}`;
    }
    return line;
  });
  for (const [key, value] of Object.entries(updates)) {
    if (!seen.has(key)) merged.push(`${key}=${quote(value)}`);
  }
  return merged.join("\n") + "\n";
}

function quote(value: string): string {
  // One line, double quoted, with real newlines written as \n, which Next's env
  // loader turns back into newlines. Quotes and backslashes cannot round-trip that
  // loader, and no GitHub credential contains them, so they are refused.
  if (/["\\]/.test(value)) throw new Error("A setting contained a quote or backslash and was not written.");
  return `"${value.replace(/\r?\n/g, "\\n")}"`;
}

export async function writeEnv(file: string, updates: Record<string, string>): Promise<void> {
  let existing = "";
  try {
    existing = await readFile(file, "utf8");
  } catch {
    // No file yet.
  }
  await writeFile(file, mergeEnv(existing, updates), { mode: 0o600 });
}

export const newSessionSecret = () => randomBytes(32).toString("base64");
