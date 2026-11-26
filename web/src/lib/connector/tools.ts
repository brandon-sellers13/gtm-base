import "server-only";
import { McpServer, type ServerContext } from "@modelcontextprotocol/server";
import * as z from "zod";
import { listBases } from "../bases";
import { GitHubError, api, listInstallations } from "../github";
import { validRepo } from "../reader";
import { type Conversation, bindOrCheck, boundBase, conversationFrom } from "./bindings";
import type { AccessBody } from "./grants";

// The connector's tools, made fresh for every request by the MCP library.
// C1 has two: "List my bases" and a plain "Read a document". C2 adds the
// moment-of-use flag, C3 skills and C4 proposing.

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

const DOC_PATH = /^[A-Za-z0-9_][A-Za-z0-9._/-]{0,299}\.md$/;
const MAX_CHARS = 200_000;

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
        return text(bases.map((b) => `${b.owner}/${b.name}`).join("\n") || "This GitHub account reaches no bases yet.");
      });
    },
  );

  server.registerTool(
    "read_document",
    {
      title: "Read a document",
      description:
        "Read one document from the base as it stands now, by its path in the base, such as context/map.md.",
      inputSchema: z.object({
        base: BASE_FIELD,
        path: z.string().max(300).describe("The document's path in the base, such as context/map.md."),
      }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ base, path }, ctx) => {
      const facts = factsOf(ctx);
      return guarded(facts, async () => {
        const conversation = conversationOf(ctx, facts);
        if (!conversation) return text(NO_CONVERSATION, true);
        const clean = path.trim().replace(/^\/+/, "");
        if (!DOC_PATH.test(clean) || clean.split("/").some((part) => !part || part.startsWith("."))) {
          return text("Refused: give the document's path in the base, such as context/map.md.", true);
        }
        const admitted = await admitBase(facts, conversation, base);
        const [owner, repo] = admitted.base.split("/");
        let file: { type?: string; encoding?: string; content?: string } | unknown[];
        try {
          file = await api(
            `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${clean.split("/").map(encodeURIComponent).join("/")}`,
            { token: facts.access.grant.gh },
          );
        } catch (error) {
          if (error instanceof GitHubError && error.status === 404) {
            return text(`${admitted.note}There is no document at ${clean} in ${admitted.base}. Start from context/map.md, which lists the base's documents.`, true);
          }
          throw error;
        }
        if (Array.isArray(file) || file.type !== "file" || file.encoding !== "base64" || typeof file.content !== "string") {
          return text(`${admitted.note}${clean} in ${admitted.base} is not a document GTM Base can read here.`, true);
        }
        const body = Buffer.from(file.content, "base64").toString("utf8");
        const shown = body.length > MAX_CHARS ? `${body.slice(0, MAX_CHARS)}\n\n[Cut short: the document is longer than GTM Base returns at once.]` : body;
        return text(`${admitted.note}Document ${clean} from ${admitted.base}:\n\n${shown}`);
      });
    },
  );

  return server;
}
