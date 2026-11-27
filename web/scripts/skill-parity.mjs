// Holds the connector's skill serving (C3) to the plugin.
//
//   npx tsx scripts/skill-parity.mjs
//
// Reads web/scripts/fixtures/skill-parity.json, which tests/skill_parity.py
// writes by asking the plugin's own approval check and runner about real git
// repositories, runs the port on the same values, and fails on any difference:
// which skills are approved and listed, each start's outcome, refusal, flags
// and gaps, and, for a skill that runs, the exact text handed to the
// assistant. Then a few checks of what only the connector has: a person's
// "use it as it stands", the folder-declaration seam, and the refusal to
// write into the skills folder.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { verdictOf } from "../src/lib/stale/rules.ts";
import {
  approvalOf,
  declarationOf,
  expandedReads,
  readSkill,
  rendered,
  skillIndex,
  startSkill,
  touchesSkills,
} from "../src/lib/stale/skills.ts";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(join(here, "fixtures", "skill-parity.json"), "utf8"));

let failed = 0;
let checks = 0;
function check(name, ok, detail = "") {
  checks++;
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}${!ok && detail ? `\n${detail}` : ""}`);
}

const verdictFor = (snapshot) => {
  try {
    return verdictOf(snapshot);
  } catch (error) {
    if (error?.name === "Unreadable" || error?.constructor?.name === "Unreadable") return null;
    throw error;
  }
};

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

for (const { name, snapshot, world, expected } of fixtures) {
  const verdict = verdictFor(snapshot);
  const index = (await skillIndex(world)).map((entry) => entry.name);
  const wantIndex = Object.entries(expected)
    .filter(([, e]) => e.indexed)
    .map(([skill]) => skill)
    .sort();
  check(`${name}: the skills listed`, same(index, wantIndex), `plugin ${JSON.stringify(wantIndex)}, port ${JSON.stringify(index)}`);
  for (const [skill, want] of Object.entries(expected)) {
    const read = await readSkill(world, skill);
    const approved = read ? await approvalOf(world, skill, read.files) : null;
    check(`${name}: ${skill} approved is ${want.acceptable}`, !!approved === want.acceptable && (!approved || approved.role === want.role), `port ${JSON.stringify(approved)}`);
    const started = await startSkill(world, verdict, skill, { links: world.links });
    const got = {
      outcome: started.outcome,
      refusal: started.refusal,
      waiting: started.waiting,
      flagged: started.flagged,
      gaps: started.gaps,
    };
    const wantShape = { outcome: want.outcome, refusal: want.refusal, waiting: want.waiting, flagged: want.flagged, gaps: want.gaps };
    check(`${name}: ${skill} starts as ${want.outcome}${want.refusal ? ` (${want.refusal})` : ""}`, same(got, wantShape), `plugin ${JSON.stringify(wantShape)}\nport   ${JSON.stringify(got)}`);
    if (want.text !== null) {
      const text = rendered(started);
      check(`${name}: ${skill} hands on the same words`, text === want.text, firstDifference(want.text, text));
    }
  }
}

function firstDifference(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return `first difference at ${i}:\n--- plugin\n${a.slice(Math.max(0, i - 80), i + 120)}\n--- port\n${b.slice(Math.max(0, i - 80), i + 120)}`;
}

// --- What only the connector has ------------------------------------------------

{
  const flagged = fixtures.find((f) => f.name === "a document the skill reads is behind a recorded change");
  const verdict = verdictFor(flagged.snapshot);
  const started = await startSkill(flagged.world, verdict, "drift-grade", { useAsIs: ["context/positioning.md"] });
  check(
    "a person who chose to use the flagged document as it stands gets the skill, told it stays flagged",
    started.outcome === "flagged" &&
      !started.waiting &&
      started.sentences[0] === "Your positioning is being used as it stands, and it stays flagged until somebody says it already reflects the change." &&
      started.documents.some(([path]) => path === "context/positioning.md"),
    JSON.stringify(started.sentences),
  );
  const wrongChoice = await startSkill(flagged.world, verdict, "drift-grade", { useAsIs: ["context/icps.md"] });
  check("a choice for another document leaves it waiting", wrongChoice.waiting && wrongChoice.outcome === "flagged");
}

{
  // Track 4's folder declaration: only context/icps/, only among what a skill
  // reads if present, and refused whenever that folder is not open.
  const text = "---\nreads_required: [context/icps.md]\nreads_optional: [context/icps/, context/voice.md]\nstandard: standards/x.md\n---\n\n# X\n";
  check("a folder in reads_optional is refused while no folder is open", declarationOf(text, []).problems[0]?.[1] === "context/icps/");
  check("context/icps/ is the one folder open by default, as the plugin's runner reads it", declarationOf(text).problems.length === 0);
  const other = declarationOf(text.replace("context/icps/, ", "context/strategy/, "));
  check("any other folder is refused by default", other.problems[0]?.[1] === "context/strategy/");
  const open = declarationOf(text, ["context/icps/"]);
  check("with context/icps/ open, the same declaration is valid", open.problems.length === 0);
  const required = declarationOf(text.replace("reads_required: [context/icps.md]", "reads_required: [context/icps/]"), ["context/icps/"]);
  check("a folder is never a required read", required.problems[0]?.[1] === "context/icps/");
  const files = {
    "context/icps.md": "a",
    "context/icps/b-segment.md": "b",
    "context/icps/a-segment.md": "a",
    "context/icps/deeper/c.md": "c",
    "context/icps/notes.txt": "n",
    "context/icps/linked.md": "l",
    "context/voice.md": "v",
  };
  const reads = expandedReads(open, files, ["context/icps/linked.md"]);
  check(
    "the folder hands on only the .md files directly in it, in name order, no link and nothing deeper",
    same(
      reads.map((r) => r.path),
      ["standards/x.md", "context/icps.md", "context/icps/a-segment.md", "context/icps/b-segment.md", "context/voice.md"],
    ),
    JSON.stringify(reads),
  );
  const empty = expandedReads(open, { "context/icps.md": "a" }, []);
  check("an empty or missing folder adds nothing", same(empty.map((r) => r.path), ["standards/x.md", "context/icps.md", "context/voice.md"]));

  // Through a whole start: the approved scenario, with a folder declared and opened.
  const base = fixtures.find((f) => f.name === "an approved skill that names the segments folder, with two segments saved");
  const world = {
    ...base.world,
    files: { ...base.world.files, "context/icps/enterprise.md": "---\nkind: icp\nowner: owner@example.com\nsources: []\nstatus: draft\n---\n\n# Enterprise\n" },
  };
  const verdict = verdictFor({ ...base.snapshot, files: world.files });
  const started = await startSkill(world, verdict, "drift-grade");
  check(
    "with the folder open, a start hands on each segment through the check, and an absent folder file is no gap",
    started.outcome === "ready-with-gaps" &&
      started.documents.some(([path]) => path === "context/icps/enterprise.md") &&
      !started.gaps.some((path) => path.startsWith("context/icps/")),
    JSON.stringify({ outcome: started.outcome, gaps: started.gaps, documents: started.documents.map(([p]) => p) }),
  );
  const flaggedWorld = {
    ...world,
    files: {
      ...world.files,
      "learning/changes/stg-ffffffffffffffff.md":
        "---\nid: stg-ffffffffffffffff\nkind: change\nhappened_on: 2026-11-10\nwritten_on: 2026-11-11\nnoted_by: owner@example.com\nsource: a call\naffects: [context/icps/enterprise.md]\nreview_by: 2026-12-15\norigin: manual\nstatus: open\n---\n\nEnterprise buyers moved.\n",
    },
  };
  const flaggedStart = await startSkill(flaggedWorld, verdictFor({ ...base.snapshot, files: flaggedWorld.files }), "drift-grade");
  check("a segment behind a recorded change is flagged like any document", flaggedStart.waiting && same(flaggedStart.flagged, ["context/icps/enterprise.md"]), JSON.stringify(flaggedStart.flagged));
}

{
  check("a proposal path in skills/ is refused", touchesSkills(["skills/drift-grade/SKILL.md"]));
  check("so is one spelled with a slash, a dot, a backslash or capitals", ["/skills/x/SKILL.md", "./skills/x", "Skills/x/SKILL.md", "SKILLS\\x\\SKILL.md", "skills"].every((p) => touchesSkills([p])));
  check("a document path is not", !touchesSkills(["context/positioning.md", "learning/corrections/stg-x.md", "standards/skills.md"]));
}

console.log(`\n${checks - failed} of ${checks} checks passed.`);
process.exit(failed ? 1 : 0);
