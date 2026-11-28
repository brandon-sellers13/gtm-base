// Holds the web app's accept of a records-only proposal to the rule Brandon set
// on 2026-11-27 (C2's security review, the borderline pattern): a proposal that
// ends up changing records only, after one of its commits edited a document and
// a later one undid it, cannot be accepted here. The same rule holds for a
// teammate's confirmation review, recognised by its branch name, which the base
// owner accepts like any records-only proposal. The real getProposal runs
// against GitHub's answers, stubbed in place of the network.
//
// Run from web/ (the condition lets the server-only modules load outside Next):
//
//   npx tsx --conditions=react-server scripts/proposals-check.mjs

const { acceptingEmail, blockedReason, getProposal, ProposalNotFound } = await import("../src/lib/proposals.ts");

const OWNER = "owner@example.com";
const TEAMMATE = "teammate@example.com";
const RECORD = "learning/corrections/2026-11-10-stg-cccccccccccccccc.md";
const DOC = "context/positioning.md";
const LINE = "work/confirmations/context--positioning.md";
const MAP = "---\nkind: map\nowner: owner@example.com\nsources: []\nstatus: draft\n---\n\n# Map\n";
const POSITIONING = "---\nkind: positioning\nowner: teammate@example.com\nstatus: approved\n---\n\n# Positioning\n";
const MARKED = "gtm-base proposal stg-cccccccccccccccc entry stg-aaaaaaaaaaaaaaaa source -";
const CONFIRMATION_REF = "confirmations/0123456789ab-cdef01234567";

function github({ commits, files = [RECORD], body = MARKED, ref = "proposal" }) {
  const routes = {
    "/repos/acme/base/pulls/7": {
      number: 7,
      title: "A context change",
      body,
      html_url: "https://github.com/acme/base/pull/7",
      user: { login: "teammate", avatar_url: "" },
      created_at: "2026-11-08T00:00:00Z",
      head: { sha: "h3", ref },
      base: { sha: "b0", ref: "main" },
      state: "open",
      merged: false,
      mergeable: true,
      merge_commit_sha: "m1",
    },
    "/repos/acme/base/pulls/7/files": files.map((f) => (typeof f === "string" ? { filename: f, status: "added", patch: "+line" } : { patch: "+line", ...f })),
    "/repos/acme/base/git/ref/heads/main": { object: { sha: "b0" } },
    "/repos/acme/base/contents/context/map.md": { content: Buffer.from(MAP).toString("base64") },
    "/repos/acme/base/contents/context/positioning.md": { content: Buffer.from(POSITIONING).toString("base64") },
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
let ran = 0;
const check = (name, ok, detail = "") => {
  ran++;
  console.log(`${ok ? "ok  " : "FAIL"}  ${name}${ok || !detail ? "" : `: ${detail}`}`);
  if (!ok) failed++;
};

// The pattern: edit the document and add its record, then undo the edit.
github({ commits: [
  { sha: "h1", files: [DOC, RECORD] },
  { sha: "h2", files: [DOC] },
] });
let proposal = await getProposal("t", "acme", "base", 7);
check("an edit undone inside a records-only proposal blocks the accept", blockedReason(proposal) === "edits-undone", String(blockedReason(proposal)));
check("and nobody may accept it here, the base owner included", acceptingEmail(proposal, [OWNER]) === null, String(acceptingEmail(proposal, [OWNER])));

// The control: a proposal that only ever touched records is still the base owner's to accept.
github({ commits: [{ sha: "h1", files: [RECORD] }] });
proposal = await getProposal("t", "acme", "base", 7);
check("a proposal that only ever touched records is not blocked", blockedReason(proposal) === null, String(blockedReason(proposal)));
check("and the base owner may accept it", acceptingEmail(proposal, [OWNER]) === OWNER, String(acceptingEmail(proposal, [OWNER])));

// A teammate's confirmation review: no marker, its own branch, one confirmation line.
const confirmation = { body: "Its owner confirmed on 2026-11-27 that the positioning is still right.", ref: CONFIRMATION_REF, files: [LINE] };
github({ ...confirmation, commits: [{ sha: "h1", files: [LINE] }] });
proposal = await getProposal("t", "acme", "base", 7);
check("a confirmation review is recognised by its branch", proposal.kind === "confirmation", proposal.kind);
check("its body is kept whole", proposal.body === confirmation.body, proposal.body);
check("a confirmation line is a record, so it is not blocked", blockedReason(proposal) === null, String(blockedReason(proposal)));
check("the base owner may accept it", acceptingEmail(proposal, [OWNER]) === OWNER, String(acceptingEmail(proposal, [OWNER])));
check("the teammate may not accept their own", acceptingEmail(proposal, [TEAMMATE]) === null, String(acceptingEmail(proposal, [TEAMMATE])));

// The same rule as any records-only proposal: one commit touched a document.
github({ ...confirmation, commits: [
  { sha: "h1", files: [DOC, LINE] },
  { sha: "h2", files: [DOC] },
] });
proposal = await getProposal("t", "acme", "base", 7);
check("a confirmation review whose commit touched a document is blocked", blockedReason(proposal) === "edits-undone", String(blockedReason(proposal)));
check("and nobody may accept it here", acceptingEmail(proposal, [OWNER]) === null, String(acceptingEmail(proposal, [OWNER])));

// A branch named like one gains nothing: a file that is no record still blocks it.
github({ ...confirmation, files: [LINE, ".claude/settings.json"], commits: [{ sha: "h1", files: [LINE, ".claude/settings.json"] }] });
proposal = await getProposal("t", "acme", "base", 7);
check("a confirmation branch carrying another file is blocked", blockedReason(proposal) === "other-files", String(blockedReason(proposal)));

// A pull request with neither a marker nor a confirmation branch is not GTM Base's.
github({ body: "Some other change.", ref: "feature/x", commits: [{ sha: "h1", files: [LINE] }], files: [LINE] });
let missing = false;
try {
  await getProposal("t", "acme", "base", 7);
} catch (error) {
  missing = error instanceof ProposalNotFound;
}
check("a pull request with neither is not read as a proposal", missing);

// A P3 proposal carries the document and the line recording the yes together;
// before confirmation lines counted as records it was blocked as other files.
github({ files: [{ filename: DOC, status: "modified" }, LINE], commits: [{ sha: "h1", files: [DOC, LINE] }] });
proposal = await getProposal("t", "acme", "base", 7);
check("a document with its confirmation line is not blocked", blockedReason(proposal) === null, String(blockedReason(proposal)));
check("and the document's owner accepts it, not the base owner", acceptingEmail(proposal, [TEAMMATE]) === TEAMMATE && acceptingEmail(proposal, [OWNER]) === null, `${acceptingEmail(proposal, [TEAMMATE])} / ${acceptingEmail(proposal, [OWNER])}`);

console.log(`\n${ran - failed} of ${ran} checks passed.`);
process.exit(failed ? 1 : 0);
