import Link from "next/link";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { readForPage } from "@/lib/pageData";
import { type Doc, docHref, PARTS, readBase } from "@/lib/reader";
import { currentSession } from "@/lib/session";

export default async function BasePage({ params }: { params: Promise<{ owner: string; repo: string }> }) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = await params;
  const base = await readForPage(() => readBase(session.token, owner, repo));

  const openChanges = base.changes.filter((c) => c.status === "open");
  const parts = [...PARTS, { key: "other", title: "Other documents", blurb: "" }];

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <Header session={session} />
      <main className="py-8">
        <p className="font-mono text-xs text-ink-quiet">
          {base.owner} / {base.repo}
        </p>
        <h1 className="mt-1 text-3xl font-bold tracking-[-0.035em]">Company base</h1>
        <p className="mt-3 text-ink-mid">
          {base.docs.length} documents
          {openChanges.length > 0 && (
            <>
              {" "}
              · {openChanges.length} open context {openChanges.length === 1 ? "change" : "changes"}
            </>
          )}{" "}
          ·{" "}
          <a href={base.htmlUrl} className="underline-offset-4 hover:underline">
            Open on GitHub
          </a>
        </p>

        {base.truncated && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">
            This repository is too large for GitHub to list in one go, so some documents may be missing below.
          </p>
        )}

        {openChanges.length > 0 && (
          <section className="mt-10">
            <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Open context changes</h2>
            <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
              {openChanges.map((change) => (
                <li key={change.path} className="px-4 py-3">
                  <Link href={docHref(base.owner, base.repo, change.path)} className="hover:underline">
                    {change.summary || change.id}
                  </Link>
                  <p className="mt-1 font-mono text-xs text-ink-quiet">
                    {change.happenedOn ?? "date not given"} · affects {change.affects.length || "no"}{" "}
                    {change.affects.length === 1 ? "document" : "documents"}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {parts.map((part) => {
          const docs = base.docs.filter((d) => d.part === part.key);
          // The five CLASS parts always show, so the shape of a base is visible from day one.
          if (docs.length === 0 && (part.key === "other" || part.key === "work")) return null;
          return (
            <section key={part.key} className="mt-10">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">{part.title}</h2>
              {part.blurb && <p className="mt-1 text-sm text-ink-quiet">{part.blurb}</p>}
              {docs.length === 0 ? (
                <p className="mt-3 rounded-lg border border-dashed border-line px-4 py-3 text-sm text-ink-quiet">
                  Nothing here yet.
                </p>
              ) : (
              <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
                {docs.map((doc) => (
                  <DocRow key={doc.path} doc={doc} owner={base.owner} repo={base.repo} />
                ))}
              </ul>
              )}
            </section>
          );
        })}
      </main>
    </div>
  );
}

// Owners confirm what the business relies on; the README and records are not confirmed.
const CONFIRMED_PARTS = new Set(["context", "access", "skills", "standards"]);

function DocRow({ doc, owner, repo }: { doc: Doc; owner: string; repo: string }) {
  return (
    <li className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="min-w-0">
        <Link href={docHref(owner, repo, doc.path)} className="font-medium hover:underline">
          {doc.title}
        </Link>
        <span className="ml-2 font-mono text-xs text-ink-quiet">{doc.path}</span>
      </span>
      <span className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-ink-quiet">
        {doc.openChanges.length > 0 && (
          <span className="text-resolved">
            {doc.openChanges.length} open {doc.openChanges.length === 1 ? "change" : "changes"}
          </span>
        )}
        {doc.status === "draft" && <span>draft</span>}
        {CONFIRMED_PARTS.has(doc.part) && (
          <span>{doc.lastConfirmed ? `confirmed ${doc.lastConfirmed.date}` : "not confirmed"}</span>
        )}
      </span>
    </li>
  );
}
