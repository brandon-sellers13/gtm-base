import Link from "next/link";
import { redirect } from "next/navigation";
import { CleanUrl } from "@/components/CleanUrl";
import { Header } from "@/components/Header";
import { SubmitButton } from "@/components/SubmitButton";
import { mainRuleState } from "@/lib/mainRule";
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
  const rule = await mainRuleState(session.token, base.owner, base.repo);

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
        <h1 className="gb-h2 mt-2">Changes that skipped approval</h1>
        <p className="gb-lede mt-4">
          These changes went straight into the base instead of coming in as a proposal the owner accepted. Keep each one
          if it is right, or undo it.
        </p>
        <p className="gb-help mt-3">
          {rule === "on"
            ? "The main line of this base is protected, so only GTM Base and the repository's admins can write to it directly. Anything listed here came from one of them."
            : rule === "off"
              ? "The main line of this base is not protected yet. Its owner can protect it on the Team page, and then GitHub refuses changes that skip approval."
              : rule === "needs-paid-plan"
                ? "GitHub only protects the main line of a private repository on a paid plan, so on this plan a teammate can still write to it directly. This list is how those changes are caught."
                : "This list is how changes that skipped approval are caught."}
        </p>

        {notice && NOTICES[notice] && (
          <p
            className={`gb-notice mt-8 ${["not-owner", "changed-since", "not-undoable", "base-moved", "failed"].includes(notice) ? "problem" : ""}`}
            role="status"
          >
            {NOTICES[notice]}
          </p>
        )}

        {items.length === 0 ? (
          <p className="gb-empty mt-10">
            Nothing here. Every recent change to this base came in through an approval.
          </p>
        ) : (
          <ul className="mt-10 space-y-6">
            {items.map((item) => (
              <li key={item.sha} className="gb-card p-4 sm:p-6">
                <p className="gb-heading-sm break-words">{item.message}</p>
                <p className="gb-meta mt-2">
                  {item.author} · {item.date} ·{" "}
                  <a
                    href={`https://github.com/${base.owner}/${base.repo}/commit/${item.sha}`}
                    className="gb-link-quiet"
                  >
                    {item.sha.slice(0, 7)} on GitHub
                  </a>
                </p>
                <ul className="mt-4 space-y-1 border-t border-rule pt-3 font-mono text-[13px] break-all">
                  {item.files.map((f) => (
                    <li key={f.path}>
                      <span className="text-ink-quiet">{f.status}</span> {f.path}
                    </li>
                  ))}
                </ul>
                {isOwner && (
                  <div className="gb-choices mt-5">
                    <form action={keepAction}>
                      <input type="hidden" name="owner" value={base.owner} />
                      <input type="hidden" name="repo" value={base.repo} />
                      <input type="hidden" name="sha" value={item.sha} />
                      <SubmitButton pendingText="Keeping…" className="gb-chip min-w-[96px]">
                        Keep
                      </SubmitButton>
                    </form>
                    {item.undoable ? (
                      <form action={undoAction}>
                        <input type="hidden" name="owner" value={base.owner} />
                        <input type="hidden" name="repo" value={base.repo} />
                        <input type="hidden" name="sha" value={item.sha} />
                        <SubmitButton pendingText="Undoing…" className="gb-chip go min-w-[96px]">
                          Undo
                        </SubmitButton>
                      </form>
                    ) : (
                      <span className="self-center text-[15px] text-ink-mid">Undo this one on GitHub.</span>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {!isOwner && items.length > 0 && (
          <p className="gb-empty mt-8">Only the owner of this base can keep or undo these.</p>
        )}
      </main>
    </div>
  );
}
