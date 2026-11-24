#!/usr/bin/env node
// Sends the live site's settings from web/.env.live to the linked Netlify site.
// Run it yourself from web/:  node scripts/send-live-settings.mjs
//
// Values are passed to the Netlify CLI directly (no shell), the CLI's own output
// is discarded, and only the setting names are printed, so no value reaches the
// screen or the shell history. Anything that can act on GitHub or open a session
// is stored as a Netlify secret.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const SECRET = new Set(["GITHUB_APP_CLIENT_SECRET", "GITHUB_APP_PRIVATE_KEY", "SESSION_SECRET"]);
const ORDER = [
  "APP_URL",
  "GITHUB_APP_ID",
  "GITHUB_APP_SLUG",
  "GITHUB_APP_CLIENT_ID",
  "GITHUB_APP_CLIENT_SECRET",
  "GITHUB_APP_PRIVATE_KEY",
  "SESSION_SECRET",
  "ALLOWED_GITHUB_LOGINS",
];

let text;
try {
  text = readFileSync(".env.live", "utf8");
} catch {
  console.error("No web/.env.live yet. Create the live GitHub App from the setup page first.");
  process.exit(1);
}

const settings = new Map();
for (const line of text.split("\n")) {
  const match = line.match(/^([A-Z0-9_]+)="(.*)"$/);
  if (match) settings.set(match[1], match[2]); // the private key keeps its \n escapes; the app turns them back
}

const missing = ORDER.filter((key) => !settings.get(key));
if (missing.length) {
  console.error(`web/.env.live is missing: ${missing.join(", ")}. Nothing was sent.`);
  process.exit(1);
}

// The Netlify command line reads a value starting with dashes as an option, so the
// private key (which starts "-----BEGIN") is sent as base64; the app decodes it.
settings.set(
  "GITHUB_APP_PRIVATE_KEY",
  Buffer.from(settings.get("GITHUB_APP_PRIVATE_KEY").replace(/\\n/g, "\n"), "utf8").toString("base64"),
);

for (const key of ORDER) {
  const args = ["env:set", key, settings.get(key), "--force"];
  // Secrets cannot be read back in Netlify and are not given to local development.
  if (SECRET.has(key)) args.push("--secret", "--context", "production", "--context", "deploy-preview", "--context", "branch-deploy");
  try {
    execFileSync("netlify", args, { stdio: ["ignore", "pipe", "pipe"], encoding: "utf8", timeout: 60000 });
    console.log(`set ${key}${SECRET.has(key) ? " (secret)" : ""}`);
  } catch (error) {
    // Show Netlify's reason, with the value cut out and any long run of key-like text dropped.
    const said = `${error.stdout ?? ""}\n${error.stderr ?? ""}`
      .split(settings.get(key))
      .join("<value>")
      .split("\n")
      .filter((line) => line.trim() && !/[A-Za-z0-9+/]{40,}/.test(line))
      .slice(-5)
      .join("\n");
    console.error(`Netlify refused ${key}. Stopped; the settings before it were sent.\n${said || error.message.split("\n")[0]}`);
    process.exit(1);
  }
}
console.log("All live settings are on Netlify. Tell Claude to deploy.");
