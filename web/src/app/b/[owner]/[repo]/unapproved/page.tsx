import Link from "next/link";
import { redirect } from "next/navigation";
import { CleanUrl } from "@/components/CleanUrl";
import { Header } from "@/components/Header";
import { SubmitButton } from "@/components/SubmitButton";
import { readForPage } from "@/lib/pageData";
import { readBase } from "@/lib/reader";
import { currentSession } from "@/lib/session";
import { isBaseOwner } from "@/lib/team";
import { listUnapproved } from "@/lib/unapproved";
import { keepAction, undoAction } from "./actions";

const NOTICES: Record<string, string> = {
  kept: "Kept. The change stays in the base, and it is recorded that you kept it.",
  undone: "Undone. The base is back to how it was before that change, and the undo is recorded.",
  "not-owner": "Only the owner of this base can keep or undo a change.",
  "not-listed": "That change is no longer waiting for a decision.",
  "changed-since":
    "That change was edited again afterwards, so undoing it here could throw away the later work. Undo it on GitHub instead.",
  "not-undoable": "That change is a merge or too large to undo here. Undo it on GitHub instead.",
  "base-moved": "The base changed a moment ago. Reload the page and try again.",
  failed: "GitHub did not finish that. Nothing was changed; please try again.",
};

export default async function UnapprovedPage({
  params,
  searchParams,
}: {
  params: Promise<{ owner: string; repo: string }>;
  searchParams: Promise<{ notice?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = await params;
  const { notice } = await searchParams;
  const base = await readForPage(() => readBase(session.token, owner, repo));
  const { items } = await readForPage(() => listUnapproved(session.token, base.owner, base.repo));
  const isOwner = await readForPage(() => isBaseOwner(session.token, base.owner, base.repo, session.emails));

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
        <h1 className="mt-1 text-3xl font-bold tracking-[-0.035em]">Changes that skipped approval</h1>
        <p className="mt-3 text-ink-mid">
          These changes went straight into the base instead of coming in as a proposal the owner accepted. Keep each one
          if it is right, or undo it.
        </p>

        {notice && NOTICES[notice] && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{NOTICES[notice]}</p>
        )}

        {items.length === 0 ? (
          <p className="mt-10 rounded-lg border border-dashed border-line px-4 py-3 text-sm text-ink-quiet">
            Nothing here. Every recent change to this base came in through an approval.
          </p>
        ) : (
          <ul className="mt-10 space-y-4">
            {items.map((item) => (
              <li key={item.sha} className="rounded-lg border border-line bg-surface p-4">
                <p className="font-medium">{item.message}</p>
                <p className="mt-1 font-mono text-xs text-ink-quiet">
                  {item.author} · {item.date} ·{" "}
                  <a
                    href={`https://github.com/${base.owner}/${base.repo}/commit/${item.sha}`}
                    className="hover:underline"
                  >
                    {item.sha.slice(0, 7)} on GitHub
                  </a>
                </p>
                <ul className="mt-3 space-y-1 font-mono text-xs">
                  {item.files.map((f) => (
                    <li key={f.path}>
                      <span className="text-ink-quiet">{f.status}</span> {f.path}
                    </li>
                  ))}
                </ul>
                {isOwner && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <form action={keepAction}>
                      <input type="hidden" name="owner" value={base.owner} />
                      <input type="hidden" name="repo" value={base.repo} />
                      <input type="hidden" name="sha" value={item.sha} />
                      <SubmitButton pendingText="Keeping…" className="rounded-lg border border-line px-4 py-2 text-sm">
                        Keep
                      </SubmitButton>
                    </form>
                    {item.undoable ? (
                      <form action={undoAction}>
                        <input type="hidden" name="owner" value={base.owner} />
                        <input type="hidden" name="repo" value={base.repo} />
                        <input type="hidden" name="sha" value={item.sha} />
                        <SubmitButton pendingText="Undoing…" className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-ground">
                          Undo
                        </SubmitButton>
                      </form>
                    ) : (
                      <span className="self-center text-sm text-ink-quiet">Undo this one on GitHub.</span>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {!isOwner && items.length > 0 && (
          <p className="mt-6 text-sm text-ink-quiet">Only the owner of this base can keep or undo these.</p>
        )}
      </main>
    </div>
  );
}
