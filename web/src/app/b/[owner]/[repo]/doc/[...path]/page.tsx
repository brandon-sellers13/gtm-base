import Link from "next/link";
import { redirect } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Header } from "@/components/Header";
import { SubmitButton } from "@/components/SubmitButton";
import { readForPage } from "@/lib/pageData";
import { docHref, PARTS, readDocument } from "@/lib/reader";
import { currentSession } from "@/lib/session";
import { confirmOffer } from "@/lib/stale/confirm";
import { documentName, fourLines } from "@/lib/stale/words";
import { confirmAction } from "./actions";

const NOTICES: Record<string, string> = {
  confirmed: "Recorded: you confirmed this document already reflects that context change.",
  "confirm-refused":
    "Nothing was recorded. That change no longer overtakes this document, or this GitHub account is not recorded as its owner.",
  "confirm-failed": "GitHub did not save the confirmation. Nothing was recorded; please try again.",
};

export default async function DocumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ owner: string; repo: string; path: string[] }>;
  searchParams: Promise<{ confirm?: string; notice?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo, path } = await params;
  // Next has already decoded each segment; decoding again would break names with "%".
  const filePath = path.join("/");
  const { base, doc, body, fields } = await readForPage(() => readDocument(session.token, owner, repo, filePath));
  const part = PARTS.find((p) => p.key === doc.part);
  const { confirm, notice } = await searchParams;
  // The connector's "it already reflects this change" link: shown only when the
  // change still overtakes this document and this person owns it.
  const offer =
    typeof confirm === "string" && /^stg-[0-9a-f]{16}$/.test(confirm)
      ? await confirmOffer(session.token, owner, repo, filePath, confirm, session.emails)
      : null;

  return (
    <div>
      <Header session={session} />
      <main className="gb-page">
        <p className="gb-label-mono break-all">
          <Link href={`/b/${base.owner}/${base.repo}`} className="gb-link-quiet">
            <span aria-hidden="true">← </span>
            {base.owner} / {base.repo}
          </Link>
          {part && <> · {part.title}</>}
        </p>

        {notice && NOTICES[notice] && (
          <p className={`gb-notice mt-6 ${notice === "confirm-failed" ? "problem" : ""}`} role="status">
            {NOTICES[notice]}
          </p>
        )}

        {offer && (
          <section className="gb-flag mt-6">
            <p className="t">
              Does {documentName(filePath)} already reflect this context change?
            </p>
            <p>
              It was recorded on {offer.entry.happenedOn}. The record says, in its own words:
            </p>
            <pre className="border-[1.5px] border-ink bg-surface px-3 py-2 font-mono text-[13px] leading-relaxed break-words whitespace-pre-wrap">
              {fourLines(filePath, offer.entry, new Date().toISOString().slice(0, 10))
                .split("\n")
                .slice(1, -1)
                .join("\n")}
            </pre>
            <p>
              Confirm only if the document below already says this. If it does not, leave it flagged and have a fix prepared
              instead. The confirmation is recorded as {offer.email}.
            </p>
            <form action={confirmAction} className="gb-choices mt-1">
              <input type="hidden" name="owner" value={owner} />
              <input type="hidden" name="repo" value={repo} />
              <input type="hidden" name="path" value={filePath} />
              <input type="hidden" name="entry" value={offer.entry.id} />
              <SubmitButton pendingText="Recording…" className="gb-chip go">
                It already reflects this change
              </SubmitButton>
            </form>
          </section>
        )}

        <dl className="gb-card mt-6 grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-2 px-4 py-4 text-[15px] [&_dd]:break-words">
          <dt className="gb-label-mono leading-6">file</dt>
          <dd className="font-mono text-[13px] leading-6">{doc.path}</dd>
          <dt className="gb-label-mono leading-6">owner</dt>
          <dd>{doc.owner ?? "not stated"}</dd>
          {doc.status && (
            <>
              <dt className="gb-label-mono leading-6">status</dt>
              <dd>{doc.status}</dd>
            </>
          )}
          {doc.kind !== "change" && (
            <>
              <dt className="gb-label-mono leading-6">confirmed</dt>
              <dd>
                {doc.lastConfirmed
                  ? `${doc.lastConfirmed.date} (${doc.lastConfirmed.trigger})`
                  : "No confirmation recorded yet"}
              </dd>
            </>
          )}
          {doc.kind === "change" && (
            <>
              <dt className="gb-label-mono leading-6">happened</dt>
              <dd>{typeof fields.happened_on === "string" ? fields.happened_on : "not given"}</dd>
              <dt className="gb-label-mono leading-6">affects</dt>
              <dd className="font-mono text-[13px] leading-6">
                {Array.isArray(fields.affects) ? fields.affects.join(", ") : String(fields.affects ?? "nothing named")}
              </dd>
            </>
          )}
        </dl>

        {doc.openChanges.length > 0 && (
          <div className="gb-flag mt-6">
            <p className="t">
              {doc.openChanges.length === 1 ? "A context change names" : `${doc.openChanges.length} context changes name`}{" "}
              this document.
            </p>
            <ul className="space-y-1.5">
              {doc.openChanges.map((change) => (
                <li key={change.path}>
                  <Link
                    href={docHref(base.owner, base.repo, change.path)}
                    className="gb-link-quiet font-bold text-ink"
                  >
                    {change.summary || change.id}
                  </Link>{" "}
                  <span className="gb-meta text-ink-mid">{change.happenedOn}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-12 border-t-[1.5px] border-ink pt-10"><article className="doc">
          {/* Raw HTML in a document is shown as text, never run: react-markdown escapes it by default. */}
          {/* Images are left out: one pointing elsewhere would tell its owner who read the document, and when. */}
          <ReactMarkdown remarkPlugins={[remarkGfm]} disallowedElements={["img"]} unwrapDisallowed>
            {body}
          </ReactMarkdown>
        </article></div>
      </main>
    </div>
  );
}
