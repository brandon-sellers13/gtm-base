import "server-only";
import { McpServer, type ServerContext } from "@modelcontextprotocol/server";
import * as z from "zod";
import { listBases } from "../bases";
import { GitHubError, api, listInstallations } from "../github";
import { type Choice, Refusal as DocumentRefusal, listDocuments, proposeChange, proposeFix, readDocument } from "./documents";
import { validRepo } from "../reader";
import { type Conversation, bindOrCheck, boundBase, conversationFrom } from "./bindings";
import type { AccessBody } from "./grants";

// The connector's tools, made fresh for every request by the MCP library:
// list my bases (C1), list documents and read a document with the
// moment-of-use flag (C2), and propose a change or a fix (C4). C3 adds skills.

// Per-request facts the endpoint verified before the library ran.
export type CallFacts = {
  access: AccessBody;
  sessionId: string | null;
  // Set when GitHub refuses the person's token, so the endpoint answers 401
  // and the product signs in again.
  githubRefused: boolean;
};

const INSTRUCTIONS =
  "GTM Base holds a company's approved marketing context (its base), kept in a GitHub repository. " +
  "Each conversation works with exactly one base, named as owner/repo. Use the base the person or the Project's " +
  "instructions name, exactly as written; never guess one or recall one from memory. If no base is named, ask the " +
  "person which base to use. Once a conversation has used a base, it cannot use another; to work on a different " +
  "base, the person starts a new conversation.";

const BASE_FIELD = z
  .string()
  .max(140)
  .describe("The base, as owner/repo, exactly as the person or the Project's instructions name it. Never guess one.");

const text = (value: string, isError = false) => ({ content: [{ type: "text" as const, text: value }], isError });

const NO_CONVERSATION =
  "Refused: GTM Base could not tell which conversation this call belongs to, so it cannot keep this conversation to one base. Nothing was read.";

function factsOf(ctx: ServerContext): CallFacts {
  const facts = ctx.http?.authInfo?.extra?.facts as CallFacts | undefined;
  if (!facts) throw new Error("The connector endpoint did not pass its checks to the tools.");
  return facts;
}

function conversationOf(ctx: ServerContext, facts: CallFacts): Conversation | null {
  return conversationFrom(ctx.mcpReq._meta as Record<string, unknown> | undefined, facts.sessionId);
}

class Refusal extends Error {}

// Checks a base before anything is read from it: its form, this conversation's
// binding, and that the person's own GitHub token reaches it and it is a base.
// Binds the conversation to it when it has no base yet. Returns a note for the
// model the first time.
async function admitBase(facts: CallFacts, conversation: Conversation, raw: string): Promise<{ base: string; note: string }> {
  const base = raw.trim();
  const [owner, repo, extra] = base.split("/");
  if (!owner || !repo || extra !== undefined || !validRepo(owner, repo)) {
    throw new Refusal("Refused: name the base as owner/repo, exactly as the person or the Project's instructions give it. Ask the person if you do not know it; never guess.");
  }
  const login = facts.access.grant.login;
  const already = await boundBase(conversation, login);
  if (already && already.toLowerCase() !== base.toLowerCase()) throw refusalFor(already);

  try {
    await api(`/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/context/map.md`, {
      token: facts.access.grant.gh,
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 401) {
      facts.githubRefused = true;
      throw error;
    }
    if (error instanceof GitHubError && (error.status === 404 || error.status === 403)) {
      throw new Refusal(`Refused: ${base} is not a base this GitHub account can reach. Check the name with the person.`);
    }
    throw error;
  }

  if (already) return { base, note: "" };
  const bound = await bindOrCheck(conversation, login, base);
  if (!bound.ok) throw refusalFor(bound.bound);
  return {
    base,
    note: bound.first
      ? `This conversation now uses the base ${base}. To work on a different base, start a new conversation.\n\n`
      : "",
  };
}

const refusalFor = (bound: string) =>
  new Refusal(
    `Refused: this conversation uses the base ${bound}, and a conversation can use only one base. To work on a different base, start a new conversation.`,
  );

async function guarded(facts: CallFacts, work: () => Promise<ReturnType<typeof text>>) {
  try {
    return await work();
  } catch (error) {
    if (error instanceof Refusal) return text(error.message, true);
    if (error instanceof GitHubError && error.status === 401) {
      facts.githubRefused = true;
      return text("GitHub no longer accepts this sign-in. Reconnect GTM Base.", true);
    }
    return text("The base could not be read just now. Try again in a moment.", true);
  }
}


export function connectorServer(): McpServer {
  const server = new McpServer({ name: "gtm-base", title: "GTM Base", version: "1.0.0" }, { instructions: INSTRUCTIONS });

  server.registerTool(
    "list_bases",
    {
      title: "List my bases",
      description:
        "The bases this person's GitHub account can reach, as owner/repo. In a conversation that already uses a base, only that base.",
      inputSchema: z.object({}),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async (_args, ctx) => {
      const facts = factsOf(ctx);
      return guarded(facts, async () => {
        const conversation = conversationOf(ctx, facts);
        if (!conversation) return text(NO_CONVERSATION, true);
        const bound = await boundBase(conversation, facts.access.grant.login);
        if (bound) return text(`This conversation uses the base ${bound}.`);
        const gh = facts.access.grant.gh;
        const bases = await listBases(gh, await listInstallations(gh));
        // A read running alongside may have bound the conversation while GitHub
        // was being asked: then only that base may be shown.
        const boundSince = await boundBase(conversation, facts.access.grant.login);
        if (boundSince) return text(`This conversation uses the base ${boundSince}.`);
        return text(bases.map((b) => `${b.owner}/${b.name}`).join("\n") || "This GitHub account reaches no bases yet.");
      });
    },
  );

  // Every tool below names a base, which binds the conversation like any read.
  const withBase = <A extends { base: string }>(
    run: (facts: CallFacts, owner: string, repo: string, args: A) => Promise<string>,
  ) =>
    async (args: A, ctx: ServerContext) => {
      const facts = factsOf(ctx);
      return guarded(facts, async () => {
        const conversation = conversationOf(ctx, facts);
        if (!conversation) return text(NO_CONVERSATION, true);
        const admitted = await admitBase(facts, conversation, args.base);
        const [owner, repo] = admitted.base.split("/");
        try {
          return text(admitted.note + (await run(facts, owner, repo, args)));
        } catch (error) {
          if (error instanceof DocumentRefusal) return text(admitted.note + error.message, true);
          throw error;
        }
      });
    };

  server.registerTool(
    "list_documents",
    {
      title: "List documents",
      description:
        "Call this first in a conversation: the base's documents (context, standards, source map), with each one's path, title and owner, " +
        "and which are behind a recorded context change. Use these paths with read_document; never guess a path.",
      inputSchema: z.object({ base: BASE_FIELD }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    withBase((facts, owner, repo) => listDocuments(facts.access.grant.gh, owner, repo)),
  );

  server.registerTool(
    "read_document",
    {
      title: "Read a document",
      description:
        "Read one document from the base (a context document, a standard or the source map), by a path list_documents gave. When a recorded context change has " +
        "overtaken it, the first answer is only the flag and the choices: tell the person, wait for their choice, and " +
        "call again with choice set to it (use_as_is, fix_first, or already_reflects when offered).",
      inputSchema: z.object({
        base: BASE_FIELD,
        path: z.string().max(300).describe("The document's path, such as context/positioning.md, from list_documents."),
        choice: z
          .enum(["use_as_is", "fix_first", "already_reflects"])
          .optional()
          .describe("Only after the person has chosen, in answer to a flag."),
      }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    withBase((facts, owner, repo, args: { base: string; path: string; choice?: Choice }) =>
      readDocument(facts.access.grant.gh, owner, repo, args.path, args.choice),
    ),
  );

  server.registerTool(
    "propose_change",
    {
      title: "Propose a context change",
      description:
        "Record something that happened and makes documents in the base no longer true (a decision, a launch, a price " +
        "change, something learned from customers), with what changed, why and the evidence, as a proposal the base's " +
        "owner accepts. It never approves anything. Name the documents it affects by their paths from list_documents.",
      inputSchema: z.object({
        base: BASE_FIELD,
        what_changed: z.string().min(1).max(500).describe("One sentence: what changed."),
        why: z.string().min(1).max(1000).describe("Why it changed."),
        evidence: z.string().min(1).max(2000).describe("Where this comes from: the call, document or message, in plain words."),
        affects: z.array(z.string().max(300)).min(1).max(20).describe("Paths of the documents it makes out of date."),
        happened_on: z.string().max(10).optional().describe("The day it happened, YYYY-MM-DD; today if left out."),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    },
    withBase(
      (
        facts,
        owner,
        repo,
        args: { base: string; what_changed: string; why: string; evidence: string; affects: string[]; happened_on?: string },
      ) =>
        proposeChange(facts.access.grant.gh, owner, repo, {
          whatChanged: args.what_changed,
          why: args.why,
          evidence: args.evidence,
          affects: args.affects,
          happenedOn: args.happened_on,
        }),
    ),
  );

  server.registerTool(
    "propose_fix",
    {
      title: "Prepare a fix for a document",
      description:
        "Only after the person chose fix_first on a flagged document and agreed to the draft: prepare the corrected " +
        "document as a proposal its owner approves. Give the new body (everything after the settings block); the " +
        "settings block, including the owner, is kept as it is. It never approves anything.",
      inputSchema: z.object({
        base: BASE_FIELD,
        path: z.string().max(300),
        entry_id: z.string().max(40).describe("The change's id, as read_document gave it."),
        new_body: z.string().min(1).max(100_000),
        what_changed: z.string().min(1).max(500).describe("One sentence: what the fix changes in the document."),
        why: z.string().min(1).max(1000),
      }),
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
    },
    withBase(
      (
        facts,
        owner,
        repo,
        args: { base: string; path: string; entry_id: string; new_body: string; what_changed: string; why: string },
      ) =>
        proposeFix(facts.access.grant.gh, owner, repo, {
          path: args.path,
          entryId: args.entry_id,
          newBody: args.new_body,
          whatChanged: args.what_changed,
          why: args.why,
        }),
    ),
  );

  return server;
}
