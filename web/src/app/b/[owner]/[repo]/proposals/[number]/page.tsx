import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Header } from "@/components/Header";
import { readForPage } from "@/lib/pageData";
import { acceptingEmail, getProposal, ProposalNotFound } from "@/lib/proposals";
import { docHref } from "@/lib/reader";
import { currentSession } from "@/lib/session";
import { acceptAction, discardAction } from "./actions";

const PROBLEMS: Record<string, string> = {
  "not-owner": "Only the owner of every document this proposal changes can accept it.",
  "not-mergeable":
    "GitHub cannot merge this proposal as it stands, usually because the base changed in the same place. Ask for the change to be proposed again.",
  "base-moved": "The base changed a moment ago. Reload the page and accept again.",
  gone: "This proposal is no longer open.",
  failed: "GitHub did not finish that. Nothing was changed; please try again.",
};

export default async function ProposalPage({
  params,
  searchParams,
}: {
  params: Promise<{ owner: string; repo: string; number: string }>;
  searchParams: Promise<{ problem?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo, number } = await params;
  const { problem } = await searchParams;
  const proposal = await readForPage(async () => {
    try {
      return await getProposal(session.token, owner, repo, Number(number));
    } catch (error) {
      if (error instanceof ProposalNotFound) return null;
      throw error;
    }
  });
  if (!proposal) notFound();

  const email = acceptingEmail(proposal, session.emails);
  const owned = proposal.files.filter((f) => f.ownedDocument);
  const owners = [...new Set(owned.flatMap((f) => f.owners))];
  const hidden = (
    <>
      <input type="hidden" name="owner" value={owner} />
      <input type="hidden" name="repo" value={repo} />
      <input type="hidden" name="number" value={proposal.number} />
    </>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <Header session={session} />
      <main className="py-8">
        <p className="font-mono text-xs text-ink-quiet">
          <Link href={`/b/${owner}/${repo}`} className="hover:underline">
            {owner} / {repo}
          </Link>{" "}
          ·{" "}
          <Link href={`/b/${owner}/${repo}/proposals`} className="hover:underline">
            Proposals
          </Link>
        </p>
        <h1 className="mt-1 text-2xl font-bold tracking-[-0.03em]">{proposal.title}</h1>
        <p className="mt-2 font-mono text-xs text-ink-quiet">
          #{proposal.number} · proposed by {proposal.author} on {proposal.createdAt} ·{" "}
          <a href={proposal.htmlUrl} className="hover:underline">
            on GitHub
          </a>
        </p>

        {problem && PROBLEMS[problem] && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{PROBLEMS[problem]}</p>
        )}

        <h2 className="mt-8 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Changes</h2>
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {proposal.files.map((file) => (
            <li key={file.path} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              {file.ownedDocument && file.status !== "added" ? (
                <Link href={docHref(owner, repo, file.path)} className="font-mono text-sm hover:underline">
                  {file.path}
                </Link>
              ) : (
                <span className="font-mono text-sm">{file.path}</span>
              )}
              <span className="font-mono text-xs text-ink-quiet">
                {file.status}
                {file.ownedDocument && <> · owner {file.owners.length ? file.owners.join(", ") : "not stated"}</>}
              </span>
            </li>
          ))}
        </ul>

        <article className="doc mt-10">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{proposal.body}</ReactMarkdown>
        </article>

        <section className="mt-10 rounded-lg border border-line bg-surface p-4">
          {email ? (
            <>
              <p className="text-sm text-ink-mid">
                You own {owned.length === 1 ? "the document" : "every document"} this proposal changes. Accepting puts
                the change into the base and records it as your confirmation, as {email}.
              </p>
              <form action={acceptAction} className="mt-4">
                {hidden}
                <button className="rounded-lg bg-ink px-5 py-3 text-sm font-medium text-ground">Accept</button>
              </form>
            </>
          ) : session.emails.length === 0 ? (
            <p className="text-sm text-ink-mid">
              To accept, GTM Base needs to see your verified email addresses.{" "}
              <a href="/api/auth/login" className="font-medium text-source underline-offset-4 hover:underline">
                Sign in again
              </a>{" "}
              and allow it.
            </p>
          ) : owned.length === 0 ? (
            <p className="text-sm text-ink-mid">This proposal changes no document with an owner, so nobody can accept it here.</p>
          ) : (
            <p className="text-sm text-ink-mid">
              Only the owner of {owned.length === 1 ? "this document" : "these documents"} can accept this proposal
              {owners.length > 0 && <> ({owners.join(", ")})</>}. None of your verified GitHub email addresses matches.
            </p>
          )}

          <form action={discardAction} className="mt-6 border-t border-line pt-4">
            {hidden}
            <label className="block text-sm font-medium" htmlFor="reason">
              Discard it instead (optional reason, posted on the pull request)
            </label>
            <input
              id="reason"
              name="reason"
              maxLength={500}
              className="mt-2 w-full rounded-lg border border-line bg-ground px-3 py-2 text-sm"
            />
            <button className="mt-3 rounded-lg border border-line px-4 py-2 text-sm">Discard</button>
          </form>
        </section>
      </main>
    </div>
  );
}
