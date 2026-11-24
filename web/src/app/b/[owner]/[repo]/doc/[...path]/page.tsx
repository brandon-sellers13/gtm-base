import Link from "next/link";
import { redirect } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Header } from "@/components/Header";
import { readForPage } from "@/lib/pageData";
import { docHref, PARTS, readDocument } from "@/lib/reader";
import { currentSession } from "@/lib/session";

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ owner: string; repo: string; path: string[] }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo, path } = await params;
  // Next has already decoded each segment; decoding again would break names with "%".
  const filePath = path.join("/");
  const { base, doc, body, fields } = await readForPage(() => readDocument(session.token, owner, repo, filePath));
  const part = PARTS.find((p) => p.key === doc.part);

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <Header session={session} />
      <main className="py-8">
        <p className="font-mono text-xs text-ink-quiet">
          <Link href={`/b/${base.owner}/${base.repo}`} className="hover:underline">
            {base.owner} / {base.repo}
          </Link>
          {part && <> · {part.title}</>}
        </p>

        <dl className="mt-6 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 rounded-lg border border-line bg-surface px-4 py-3 text-sm">
          <dt className="font-mono text-xs leading-5 text-ink-quiet">file</dt>
          <dd className="font-mono text-xs leading-5">{doc.path}</dd>
          <dt className="font-mono text-xs leading-5 text-ink-quiet">owner</dt>
          <dd>{doc.owner ?? "not stated"}</dd>
          {doc.status && (
            <>
              <dt className="font-mono text-xs leading-5 text-ink-quiet">status</dt>
              <dd>{doc.status}</dd>
            </>
          )}
          {doc.kind !== "change" && (
            <>
              <dt className="font-mono text-xs leading-5 text-ink-quiet">confirmed</dt>
              <dd>
                {doc.lastConfirmed
                  ? `${doc.lastConfirmed.date} (${doc.lastConfirmed.trigger})`
                  : "No confirmation recorded yet"}
              </dd>
            </>
          )}
          {doc.kind === "change" && (
            <>
              <dt className="font-mono text-xs leading-5 text-ink-quiet">happened</dt>
              <dd>{typeof fields.happened_on === "string" ? fields.happened_on : "not given"}</dd>
              <dt className="font-mono text-xs leading-5 text-ink-quiet">affects</dt>
              <dd className="font-mono text-xs leading-5">
                {Array.isArray(fields.affects) ? fields.affects.join(", ") : String(fields.affects ?? "nothing named")}
              </dd>
            </>
          )}
        </dl>

        {doc.openChanges.length > 0 && (
          <div className="mt-4 rounded-lg border border-line bg-notice px-4 py-3 text-sm">
            <p className="font-medium">
              {doc.openChanges.length === 1 ? "A context change names" : `${doc.openChanges.length} context changes name`}{" "}
              this document.
            </p>
            <ul className="mt-2 space-y-1">
              {doc.openChanges.map((change) => (
                <li key={change.path}>
                  <Link
                    href={docHref(base.owner, base.repo, change.path)}
                    className="underline-offset-4 hover:underline"
                  >
                    {change.summary || change.id}
                  </Link>{" "}
                  <span className="font-mono text-xs text-ink-quiet">{change.happenedOn}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <article className="doc mt-10">
          {/* Raw HTML in a document is shown as text, never run: react-markdown escapes it by default. */}
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
        </article>
      </main>
    </div>
  );
}
