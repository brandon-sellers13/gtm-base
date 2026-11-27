import Link from "next/link";
import { redirect } from "next/navigation";
import { CleanUrl } from "@/components/CleanUrl";
import { Header } from "@/components/Header";
import { readForPage } from "@/lib/pageData";
import { listProposals } from "@/lib/proposals";
import { readBase } from "@/lib/reader";
import { currentSession } from "@/lib/session";

export default async function ProposalsPage({
  params,
  searchParams,
}: {
  params: Promise<{ owner: string; repo: string }>;
  searchParams: Promise<{ notice?: string; number?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = await params;
  const { notice, number } = await searchParams;
  // Reading the base first makes a repository that is not a base a 404 here too.
  const base = await readForPage(() => readBase(session.token, owner, repo));
  const proposals = await readForPage(() => listProposals(session.token, owner, repo));

  return (
    <div>
      <Header session={session} />
      <CleanUrl />
      <main className="gb-page">
        <p className="gb-label-mono break-all">
          <Link href={`/b/${base.owner}/${base.repo}`} className="gb-link-quiet">
            <span aria-hidden="true">← </span>
            {base.owner} / {base.repo}
          </Link>
        </p>
        <h1 className="gb-h2 mt-2">Proposals</h1>
        <p className="gb-lede mt-4">
          Changes your team&apos;s Claude Code sessions propose to this base. The owner of each document accepts or
          discards them.
        </p>

        {notice === "accepted" && (
          <p className="gb-notice mt-8" role="status">
            Proposal #{number} is accepted. It is now part of the base, and it counts as your confirmation of the
            documents it changed.
          </p>
        )}
        {notice === "gone" && (
          <p className="gb-notice mt-8" role="status">
            Proposal #{number} is already closed, so nothing more was done. If you clicked Accept or Discard more than
            once, the first click finished it.
          </p>
        )}
        {notice === "discarded" && (
          <p className="gb-notice mt-8" role="status">
            Proposal #{number} is discarded. The base is unchanged, and the same change will not be proposed again.
          </p>
        )}

        {proposals.length === 0 ? (
          <p className="gb-empty mt-10">
            Nothing waiting. Proposals appear here when a teammate&apos;s Claude Code proposes a change to this base.
          </p>
        ) : (
          <ul className="gb-docs mt-10">
            {proposals.map((p) => (
              <li key={p.number} className="flex items-start gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.avatarUrl} alt="" className="gb-avatar mt-0.5 h-7 w-7" />
                <span className="min-w-0 break-words">
                  <Link href={`/b/${base.owner}/${base.repo}/proposals/${p.number}`} className="gb-link-quiet font-bold">
                    {p.title}
                  </Link>
                  <span className="gb-meta block">
                    #{p.number} · {p.author} · {p.createdAt}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
