#!/usr/bin/env node
// Copies the company-base template the plugin ships into the web app, so a base
// created in the browser starts with exactly the files a base created in Claude
// Code does. Run from web/:  npm run bundle-template [-- <git ref>]
//
// The default ref is HEAD, the commit you are on, so the bundle is taken from the
// same commit as the template beside it. A local `main` can lag the remote one,
// and bundling from it would copy an older template without a word.
// tests/test_web_template_bundle.py fails whenever the bundle and the template on
// the same commit disagree, so run this after any change to the template.
// .claude/settings.json is left out on purpose: the plugin writes that file itself
// when a seat joins, pinned to the plugin version it trusts.

import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const ref = process.argv[2] ?? "HEAD";
const root = "plugins/gtm-base/templates/company-base/";
const git = (...args) => execFileSync("git", ["-C", "..", ...args], { encoding: "utf8" });

const commit = git("rev-parse", ref).trim();
const files = git("ls-tree", "-r", "--name-only", commit, root)
  .split("\n")
  .filter(Boolean)
  .map((path) => path.slice(root.length))
  .filter((path) => path !== ".claude/settings.json" && !path.endsWith(".DS_Store"))
  .sort()
  .map((path) => ({ path, content: git("show", `${commit}:${root}${path}`) }));

const out = { source: { ref, commit, folder: root }, files };
writeFileSync("src/lib/base-template.generated.json", JSON.stringify(out, null, 2) + "\n");
console.log(`Bundled ${files.length} files from ${ref} (${commit.slice(0, 7)}).`);
