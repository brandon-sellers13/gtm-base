// Holds the web app's moment-of-use port to the plugin.
//
//   npx tsx scripts/stale-parity.mjs
//
// Reads web/scripts/fixtures/stale-parity.json, which tests/stale_parity.py
// writes by running the plugin's own reader and rules on real git
// repositories, runs the port on the same snapshots, and fails on any
// difference: which change has overtaken each document, and the exact words
// said about it. Regenerate the fixtures whenever the plugin's rules change.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { OLDER_LAYOUT, verdictOf } from "../src/lib/stale/rules.ts";
import { flagBlock } from "../src/lib/stale/words.ts";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(join(here, "fixtures", "stale-parity.json"), "utf8"));

let failed = 0;
let checks = 0;
const fail = (name, what) => {
  failed++;
  console.log(`FAIL  ${name}: ${what}`);
};

for (const { name, snapshot, expected, words } of fixtures) {
  checks++;
  let verdict;
  try {
    verdict = verdictOf(snapshot);
  } catch (error) {
    if (error?.name !== "Unreadable") throw error;
    const olderLayout = Object.keys(snapshot.files).some((p) => p.startsWith("work/decisions/") || p.startsWith("work/changes/") || p.startsWith("corrections/"));
    if (error.code === OLDER_LAYOUT && olderLayout) {
      console.log(`ok    ${name} (refused: older layout, by design)`);
      continue;
    }
    if (expected.unreadable) {
      console.log(`ok    ${name} (both refuse: ${error.code})`);
      continue;
    }
    fail(name, `the port refused (${error.code}) where the plugin answered`);
    continue;
  }
  if (expected.unreadable) {
    fail(name, `the plugin refused (${expected.unreadable}) where the port answered`);
    continue;
  }
  const got = {};
  for (const path of verdict.documents.keys()) got[path] = verdict.overtakenBy.get(path)?.id ?? null;
  const paths = new Set([...Object.keys(expected), ...Object.keys(got)]);
  let same = true;
  for (const path of paths) {
    if ((expected[path] ?? null) !== (got[path] ?? null)) {
      same = false;
      fail(name, `${path}: plugin says ${expected[path]}, port says ${got[path]}`);
    }
  }
  for (const [path, said] of Object.entries(words)) {
    const entry = verdict.overtakenBy.get(path);
    if (!entry) continue;
    for (const [key, owned] of [["owned", true], ["notOwned", false]]) {
      checks++;
      const ours = flagBlock({ path, entry, fixReady: false, owned, today: snapshot.today });
      if (ours !== said[key]) {
        same = false;
        fail(name, `the words for ${path} (${key}) differ:\n--- plugin\n${said[key]}\n--- port\n${ours}`);
      }
    }
  }
  if (same) console.log(`ok    ${name}`);
}

console.log(`\n${checks - failed} of ${checks} checks passed.`);
process.exit(failed ? 1 : 0);
