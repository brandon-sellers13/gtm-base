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
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <Header session={session} />
      <CleanUrl />
      <main className="py-8">
        <p className="font-mono text-xs text-ink-quiet">
          <Link href={`/b/${base.owner}/${base.repo}`} className="hover:underline">
            {base.owner} / {base.repo}
          </Link>
        </p>
        <h1 className="mt-1 text-3xl font-bold tracking-[-0.035em]">Proposals</h1>
        <p className="mt-3 text-ink-mid">
          Changes your team&apos;s Claude Code sessions propose to this base. The owner of each document accepts or
          discards them.
        </p>

        {notice === "accepted" && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">
            Proposal #{number} is accepted. It is now part of the base, and it counts as your confirmation of the
            documents it changed.
          </p>
        )}
        {notice === "gone" && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">
            Proposal #{number} is already closed, so nothing more was done. If you clicked Accept or Discard more than
            once, the first click finished it.
          </p>
        )}
        {notice === "discarded" && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">
            Proposal #{number} is discarded. The base is unchanged, and the same change will not be proposed again.
          </p>
        )}

        {proposals.length === 0 ? (
          <p className="mt-10 rounded-lg border border-dashed border-line px-4 py-3 text-sm text-ink-quiet">
            Nothing waiting. Proposals appear here when a teammate&apos;s Claude Code proposes a change to this base.
          </p>
        ) : (
          <ul className="mt-10 divide-y divide-line rounded-lg border border-line bg-surface">
            {proposals.map((p) => (
              <li key={p.number} className="flex items-center gap-3 px-4 py-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.avatarUrl} alt="" className="h-6 w-6 shrink-0 rounded-full" />
                <span className="min-w-0">
                  <Link href={`/b/${base.owner}/${base.repo}/proposals/${p.number}`} className="font-medium hover:underline">
                    {p.title}
                  </Link>
                  <span className="block font-mono text-xs text-ink-quiet">
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
