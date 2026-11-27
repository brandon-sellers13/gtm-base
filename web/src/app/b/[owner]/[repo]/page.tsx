import Link from "next/link";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { SetupGuide } from "@/components/SetupGuide";
import { connectorEnabled, resourceUrl } from "@/lib/connector/config";
import { readForPage } from "@/lib/pageData";
import { listProposals } from "@/lib/proposals";
import { listUnapproved } from "@/lib/unapproved";
import { type Doc, docHref, PARTS, readBase } from "@/lib/reader";
import { currentSession } from "@/lib/session";

export default async function BasePage({ params }: { params: Promise<{ owner: string; repo: string }> }) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = await params;
  const base = await readForPage(() => readBase(session.token, owner, repo));
  const proposals = await readForPage(() => listProposals(session.token, owner, repo));
  const { items: unapproved } = await readForPage(() => listUnapproved(session.token, owner, repo));

  const openChanges = base.changes.filter((c) => c.status === "open");
  const parts = [...PARTS, { key: "other", title: "Other documents", blurb: "" }];
  const showGuide = connectorEnabled();

  return (
    <div>
      <Header session={session} />
      <main className="page">
        <p className="label-mono break-all">
          {base.owner} / {base.repo}
        </p>
        <h1 className="title mt-2">Company base</h1>
        <p className="mt-4 leading-[1.9] text-ink-mid">
          {base.docs.length} documents
          {openChanges.length > 0 && (
            <>
              {" "}
              · {openChanges.length} open context {openChanges.length === 1 ? "change" : "changes"}
            </>
          )}{" "}
          ·{" "}
          <Link href={`/b/${base.owner}/${base.repo}/proposals`} className="link">
            {proposals.length === 0
              ? "No proposals waiting"
              : `${proposals.length} ${proposals.length === 1 ? "proposal" : "proposals"} waiting`}
          </Link>{" "}
          ·{" "}
          <Link href={`/b/${base.owner}/${base.repo}/team`} className="link-quiet text-ink">
            Team
          </Link>{" "}
          ·{" "}
          <a href={base.htmlUrl} className="link-quiet text-ink">
            Open on GitHub
          </a>
          {showGuide && (
            <>
              {" "}
              ·{" "}
              <a href="#use-in-chat" className="link-quiet text-ink">
                Use in Claude or ChatGPT
              </a>
            </>
          )}
        </p>

        {unapproved.length > 0 && (
          <p className="notice notice-flag mt-8">
            {unapproved.length === 1 ? "One change" : `${unapproved.length} changes`} went into this base without an
            approval.{" "}
            <Link href={`/b/${base.owner}/${base.repo}/unapproved`} className="link">
              Keep or undo {unapproved.length === 1 ? "it" : "them"}
            </Link>
          </p>
        )}

        {base.truncated && (
          <p className="notice mt-8">
            This repository is too large for GitHub to list in one go, so some documents may be missing below.
          </p>
        )}

        {openChanges.length > 0 && (
          <section>
            <h2 className="heading section-label">Open context changes</h2>
            <ul className="rows">
              {openChanges.map((change) => (
                <li key={change.path}>
                  <Link href={docHref(base.owner, base.repo, change.path)} className="link-quiet font-bold break-words">
                    {change.summary || change.id}
                  </Link>
                  <p className="meta-mono mt-1">
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
            <section key={part.key}>
              <h2 className="heading section-label !mb-0">{part.title}</h2>
              {part.blurb && <p className="mt-2 text-[15px] text-ink-mid">{part.blurb}</p>}
              {docs.length === 0 ? (
                <p className="empty mt-4">Nothing here yet.</p>
              ) : (
              <ul className="rows mt-4">
                {docs.map((doc) => (
                  <DocRow key={doc.path} doc={doc} owner={base.owner} repo={base.repo} />
                ))}
              </ul>
              )}
            </section>
          );
        })}

        {showGuide && <SetupGuide owner={base.owner} repo={base.repo} connectorUrl={resourceUrl()} />}
      </main>
    </div>
  );
}

// Owners confirm what the business relies on; the README and records are not confirmed.
const CONFIRMED_PARTS = new Set(["context", "access", "skills", "standards"]);

function DocRow({ doc, owner, repo }: { doc: Doc; owner: string; repo: string }) {
  return (
    <li className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <span className="min-w-0 break-words">
        <Link href={docHref(owner, repo, doc.path)} className="link-quiet font-bold">
          {doc.title}
        </Link>
        <span className="meta-mono ml-2 break-all">{doc.path}</span>
      </span>
      <span className="meta-mono flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1">
        {doc.openChanges.length > 0 && (
          <span className="tag bg-resolved-tint text-resolved">
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
