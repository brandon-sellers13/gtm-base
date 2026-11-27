// Holds the web app's accept of a records-only proposal to the rule Brandon set
// on 2026-11-27 (C2's security review, the borderline pattern): a proposal that
// ends up changing records only, after one of its commits edited a document and
// a later one undid it, cannot be accepted here. The real getProposal runs
// against GitHub's answers, stubbed in place of the network.
//
// Run from web/ (the condition lets the server-only modules load outside Next):
//
//   npx tsx --conditions=react-server scripts/proposals-check.mjs

const { acceptingEmail, blockedReason, getProposal } = await import("../src/lib/proposals.ts");

const OWNER = "owner@example.com";
const RECORD = "learning/corrections/2026-11-10-stg-cccccccccccccccc.md";
const DOC = "context/positioning.md";
const MAP = "---\nkind: map\nowner: owner@example.com\nsources: []\nstatus: draft\n---\n\n# Map\n";

function github(commits) {
  const routes = {
    "/repos/acme/base/pulls/7": {
      number: 7,
      title: "A context change",
      body: "gtm-base proposal stg-cccccccccccccccc entry stg-aaaaaaaaaaaaaaaa source -",
      html_url: "https://github.com/acme/base/pull/7",
      user: { login: "teammate", avatar_url: "" },
      created_at: "2026-11-08T00:00:00Z",
      head: { sha: "h3", ref: "proposal" },
      base: { sha: "b0", ref: "main" },
      state: "open",
      merged: false,
      mergeable: true,
      merge_commit_sha: "m1",
    },
    "/repos/acme/base/pulls/7/files": [{ filename: RECORD, status: "added", patch: "+record" }],
    "/repos/acme/base/git/ref/heads/main": { object: { sha: "b0" } },
    "/repos/acme/base/contents/context/map.md": { content: Buffer.from(MAP).toString("base64") },
    "/repos/acme/base/pulls/7/commits": commits.map((c) => ({ sha: c.sha })),
  };
  for (const commit of commits) routes[`/repos/acme/base/commits/${commit.sha}`] = { files: commit.files.map((filename) => ({ filename })) };
  globalThis.fetch = async (url) => {
    const path = new URL(String(url)).pathname;
    if (!(path in routes)) return new Response("", { status: 404 });
    return new Response(JSON.stringify(routes[path]), { status: 200 });
  };
}

let failed = 0;
const check = (name, ok, detail = "") => {
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}${ok || !detail ? "" : `: ${detail}`}`);
  if (!ok) failed++;
};

// The pattern: edit the document and add its record, then undo the edit.
github([
  { sha: "h1", files: [DOC, RECORD] },
  { sha: "h2", files: [DOC] },
]);
let proposal = await getProposal("t", "acme", "base", 7);
check("an edit undone inside a records-only proposal blocks the accept", blockedReason(proposal) === "edits-undone", String(blockedReason(proposal)));
check("and nobody may accept it here, the base owner included", acceptingEmail(proposal, [OWNER]) === null, String(acceptingEmail(proposal, [OWNER])));

// The control: a proposal that only ever touched records is still the base owner's to accept.
github([{ sha: "h1", files: [RECORD] }]);
proposal = await getProposal("t", "acme", "base", 7);
check("a proposal that only ever touched records is not blocked", blockedReason(proposal) === null, String(blockedReason(proposal)));
check("and the base owner may accept it", acceptingEmail(proposal, [OWNER]) === OWNER, String(acceptingEmail(proposal, [OWNER])));

console.log(`\n${4 - failed} of 4 checks passed.`);
process.exit(failed ? 1 : 0);
