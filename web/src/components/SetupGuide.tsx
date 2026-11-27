import { CopyButton } from "./CopyButton";

// C5: how to use one base from Claude or ChatGPT, shown on that base's page.
// The instruction names this base exactly, so a conversation in the Project
// binds to it and to nothing else. The steps follow what the connector spike
// found on 2026-11-26 (docs/plans/2026-11-26-001-feat-chat-connector-plan.md).

export function projectInstruction(owner: string, repo: string): string {
  const base = `${owner}/${repo}`;
  return (
    `Use the GTM Base connector with the base ${base}, written exactly like that, and never with any other base. ` +
    `Before you write anything for this company, list the documents in ${base} and read the ones the work needs. ` +
    `When something we discuss makes one of those documents out of date, offer to propose a context change for its owner to approve.`
  );
}

export function SetupGuide({ owner, repo, connectorUrl }: { owner: string; repo: string; connectorUrl: string }) {
  const instruction = projectInstruction(owner, repo);

  return (
    <section id="use-in-chat" className="mt-16 scroll-mt-24 border-t border-ink pt-12">
      <h2 className="heading">Use this base in Claude or ChatGPT</h2>
      <p className="mt-3 text-ink-mid">
        Claude and ChatGPT can read this base through the GTM Base connector. You add the connector to your account once,
        and then you give this company its own Project with the instruction below, so every conversation in that Project
        works from this base and no other.
      </p>

      <div className="rows mt-6">
        <div className="flex flex-col gap-3 border-b-[1.5px] border-ink bg-ground px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="min-w-0 font-bold break-words">The Project instruction for {owner}/{repo}</span>
          <CopyButton text={instruction} label="Copy the instruction" />
        </div>
        <p className="px-4 py-4 font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words">{instruction}</p>
      </div>

      <div className="rows mt-6">
        <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="min-w-0">
            <span className="block font-bold">The connector address</span>
            <span className="meta-mono block break-all">{connectorUrl}</span>
          </span>
          <CopyButton text={connectorUrl} label="Copy the address" />
        </div>
      </div>

      <p className="mt-6 text-ink-mid">
        If you work for several clients, add the connector once and make one Project for each client, each with the
        instruction from that client&apos;s base page. A conversation can use only one base, so to switch clients you start
        a new conversation in the other client&apos;s Project.
      </p>

      <Steps title="Set it up in Claude">
        <li>
          In Claude, go to Plugins, choose Add, and then choose Add custom connector. Name it GTM Base, paste the
          connector address, and sign in with GitHub when Claude asks you to.
        </li>
        <li>
          On a Claude Team or Enterprise plan, only an Owner can add a custom connector, and it is added for the whole
          organization. Ask an Owner to add GTM Base once. After that, each person signs in with their own GitHub
          account and sees only the bases that account can reach.
        </li>
        <li>
          Paste the instruction into the instructions of a classic Claude Project. Claude&apos;s new Projects, which the
          New project button makes on some accounts, are Claude Code projects that cannot use connectors yet, so the
          base will not reach them. If you work for one company only, you can paste the instruction into your
          account&apos;s Instructions for Claude instead, where it applies to every conversation.
        </li>
        <li>
          When Claude&apos;s permission mode is Manual, it asks before it uses each tool for the first time. Choose
          Always allow for List my bases, List documents, Read a document and Use a company skill. Leave Propose a
          context change and
          Prepare a fix for a document on Needs approval, so you see every proposal before Claude sends it. You can
          change these choices later in the connector&apos;s settings in Claude.
        </li>
        <li>
          If you work in Cowork, propose changes through the connector rather than through the GTM Base plugin. Cowork
          blocks sending anything to GitHub by default, so a proposal the plugin tries to send from there fails, while
          the connector sends it through GTM Base.
        </li>
        <li>
          If Claude does not use the base in a conversation, check that GTM Base is turned on in the tools menu of the
          message box.
        </li>
      </Steps>

      <Steps title="Set it up in ChatGPT">
        <li>
          In ChatGPT, go to Plugins, choose Add, and then choose Add custom MCP server. Name it GTM Base, paste the
          connector address, and sign in with GitHub when ChatGPT asks you to.
        </li>
        <li>
          On ChatGPT Business, Enterprise or Edu, your workspace administrator may have to allow custom connectors
          before you can add one.
        </li>
        <li>Make a ChatGPT Project for this company and paste the instruction into the Project&apos;s instructions.</li>
        <li>ChatGPT may ask you to confirm before it proposes a change. Read the proposal before you agree to it.</li>
      </Steps>
    </section>
  );
}

function Steps({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="group rows mt-6">
      <summary className="flex min-h-[52px] cursor-pointer list-none items-center gap-3 px-4 py-3 font-bold [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className="inline-block w-3 text-source transition-transform group-open:rotate-90">
          →
        </span>
        {title}
      </summary>
      <ol className="list-decimal space-y-3 border-t-[1.5px] border-ink py-4 pr-4 pl-10 text-[15px] leading-relaxed text-ink-mid marker:font-mono marker:text-[13px] marker:font-bold marker:text-ink">
        {children}
      </ol>
    </details>
  );
}
