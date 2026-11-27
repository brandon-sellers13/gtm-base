import Link from "next/link";
import { redirect } from "next/navigation";
import { CleanUrl } from "@/components/CleanUrl";
import { Header } from "@/components/Header";
import { appUrl } from "@/lib/config";
import { readForPage } from "@/lib/pageData";
import { readBase } from "@/lib/reader";
import { currentSession } from "@/lib/session";
import { isBaseOwner, listTeam, validUsername } from "@/lib/team";
import { cancelAction, inviteAction } from "./actions";

const NOTICES: Record<string, (who: string) => string> = {
  invited: (who) => `${who} is invited. GitHub has emailed them; once they accept, they appear under People.`,
  already: (who) => `${who} already has access to this base.`,
  cancelled: () => "The invitation is cancelled.",
  "not-owner": () => "Only the owner of this base can invite people or cancel an invitation.",
  "bad-username": () => "That does not look like a GitHub username.",
  "no-such-user": (who) => `GitHub has no account called ${who}.`,
  self: () => "You already have access to this base.",
  refused: () =>
    "GitHub refused the invitation. Only an admin of the repository can invite, and GitHub limits how many invitations a repository can have open.",
  failed: () => "GitHub did not finish that. Nothing was changed; please try again.",
};

export default async function TeamPage({
  params,
  searchParams,
}: {
  params: Promise<{ owner: string; repo: string }>;
  searchParams: Promise<{ notice?: string; who?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = await params;
  const { notice, who } = await searchParams;
  const base = await readForPage(() => readBase(session.token, owner, repo));
  const team = await readForPage(() => listTeam(session.token, base.owner, base.repo));
  const owner_ = await readForPage(() => isBaseOwner(session.token, base.owner, base.repo, session.emails));
  const shownWho = who && validUsername(who) ? who : "They";
  const hidden = (
    <>
      <input type="hidden" name="owner" value={base.owner} />
      <input type="hidden" name="repo" value={base.repo} />
    </>
  );

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
        <h1 className="gb-h2 mt-2">Team</h1>
        <p className="gb-lede mt-4">
          Everyone here can read the base and propose changes from Claude Code. The owner of a document accepts or
          discards each proposal.
        </p>

        {notice && NOTICES[notice] && (
          <p
            className={`gb-notice mt-8 ${["not-owner", "bad-username", "no-such-user", "refused", "failed"].includes(notice) ? "problem" : ""}`}
            role="status"
          >
            {NOTICES[notice](shownWho)}
          </p>
        )}

        <h2 className="gb-heading gb-section">People</h2>
        <ul className="gb-docs">
          {team.members.map((m) => (
            <li key={m.login} className="flex flex-wrap items-center gap-x-3 gap-y-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={m.avatarUrl} alt="" className="gb-avatar h-7 w-7" />
              <span className="min-w-0 font-bold break-all">{m.login}</span>
              <span className="gb-meta">{m.role === "admin" ? "admin" : "can propose"}</span>
            </li>
          ))}
        </ul>

        {team.invitations.length > 0 && (
          <>
            <h2 className="gb-heading gb-section">Invited</h2>
            <ul className="gb-docs">
              {team.invitations.map((i) => (
                <li key={i.id} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                  <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={i.avatarUrl} alt="" className="gb-avatar h-7 w-7" />
                    <span className="font-bold break-all">{i.login}</span>
                    <span className="gb-meta">invited {i.createdAt}</span>
                  </span>
                  {owner_ && (
                    <form action={cancelAction}>
                      {hidden}
                      <input type="hidden" name="invitation" value={i.id} />
                      <button className="gb-btn small">Cancel</button>
                    </form>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}

        {owner_ ? (
          <form action={inviteAction} className="gb-card p-4 sm:p-6 mt-12">
            {hidden}
            <label className="gb-field-label" htmlFor="username">
              Invite a teammate by their GitHub username
            </label>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <input
                id="username"
                name="username"
                required
                maxLength={40}
                placeholder="their-github-username"
                className="gb-input"
              />
              <button className="gb-btn primary min-h-[48px] shrink-0 sm:min-w-[120px]">Invite</button>
            </div>
            <p className="gb-help">
              They can read the base and propose changes. On GitHub&apos;s free plan they could also push a change
              straight to the base without a proposal; GTM Base will flag any change that skipped approval so it can be
              kept or undone.
            </p>
          </form>
        ) : (
          <p className="gb-empty mt-12">Only the owner of this base can invite people.</p>
        )}

        <h2 className="gb-heading gb-section">How a teammate joins</h2>
        <ol className="gb-numbered text-ink-mid">
          <li>
            Accept GitHub&apos;s invitation, from the email or at{" "}
            <a href={`https://github.com/${base.owner}/${base.repo}/invitations`} className="gb-link break-all">
              github.com/{base.owner}/{base.repo}/invitations
            </a>
            .
          </li>
          <li>
            Sign in to GTM Base at{" "}
            <a href={appUrl()} className="gb-link break-all">
              {appUrl().replace(/^https?:\/\//, "")}
            </a>{" "}
            with that GitHub account. The base appears on their home page.
          </li>
          <li>
            To work on it from Claude Code, with the GTM Base plugin installed, say:{" "}
            <span className="font-mono text-[14px] break-words text-ink">join a base from a link https://github.com/{base.owner}/{base.repo}</span>.
            Joining from Claude Code arrives with the next plugin release; until then the base is readable here.
          </li>
        </ol>
      </main>
    </div>
  );
}
