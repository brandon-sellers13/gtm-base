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
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <Header session={session} />
      <CleanUrl />
      <main className="py-8">
        <p className="font-mono text-xs text-ink-quiet">
          <Link href={`/b/${base.owner}/${base.repo}`} className="hover:underline">
            {base.owner} / {base.repo}
          </Link>
        </p>
        <h1 className="mt-1 text-3xl font-bold tracking-[-0.035em]">Team</h1>
        <p className="mt-3 text-ink-mid">
          Everyone here can read the base and propose changes from Claude Code. The owner of a document accepts or
          discards each proposal.
        </p>

        {notice && NOTICES[notice] && (
          <p className="mt-6 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{NOTICES[notice](shownWho)}</p>
        )}

        <h2 className="mt-10 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">People</h2>
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {team.members.map((m) => (
            <li key={m.login} className="flex items-center gap-3 px-4 py-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={m.avatarUrl} alt="" className="h-6 w-6 rounded-full" />
              <span className="font-medium">{m.login}</span>
              <span className="font-mono text-xs text-ink-quiet">{m.role === "admin" ? "admin" : "can propose"}</span>
            </li>
          ))}
        </ul>

        {team.invitations.length > 0 && (
          <>
            <h2 className="mt-10 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Invited</h2>
            <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
              {team.invitations.map((i) => (
                <li key={i.id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <span className="flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={i.avatarUrl} alt="" className="h-6 w-6 rounded-full" />
                    <span className="font-medium">{i.login}</span>
                    <span className="font-mono text-xs text-ink-quiet">invited {i.createdAt}</span>
                  </span>
                  {owner_ && (
                    <form action={cancelAction}>
                      {hidden}
                      <input type="hidden" name="invitation" value={i.id} />
                      <button className="text-sm text-ink-quiet underline-offset-4 hover:underline">Cancel</button>
                    </form>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}

        {owner_ ? (
          <form action={inviteAction} className="mt-10 rounded-lg border border-line bg-surface p-4">
            {hidden}
            <label className="block text-sm font-medium" htmlFor="username">
              Invite a teammate by their GitHub username
            </label>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                id="username"
                name="username"
                required
                maxLength={40}
                placeholder="their-github-username"
                className="w-full rounded-lg border border-line bg-ground px-3 py-2"
              />
              <button className="shrink-0 rounded-lg bg-ink px-5 py-2 text-sm font-medium text-ground">Invite</button>
            </div>
            <p className="mt-2 text-sm text-ink-quiet">
              They can read the base and propose changes. On GitHub&apos;s free plan they could also push a change
              straight to the base without a proposal; GTM Base will flag any change that skipped approval so it can be
              kept or undone.
            </p>
          </form>
        ) : (
          <p className="mt-10 text-sm text-ink-quiet">Only the owner of this base can invite people.</p>
        )}

        <h2 className="mt-10 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">How a teammate joins</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-ink-mid">
          <li>
            Accept GitHub&apos;s invitation, from the email or at{" "}
            <a href={`https://github.com/${base.owner}/${base.repo}/invitations`} className="text-source hover:underline">
              github.com/{base.owner}/{base.repo}/invitations
            </a>
            .
          </li>
          <li>
            Sign in to GTM Base at{" "}
            <a href={appUrl()} className="text-source hover:underline">
              {appUrl().replace(/^https?:\/\//, "")}
            </a>{" "}
            with that GitHub account. The base appears on their home page.
          </li>
          <li>
            To work on it from Claude Code, with the GTM Base plugin installed, say:{" "}
            <span className="font-mono text-xs text-ink">join a base from a link https://github.com/{base.owner}/{base.repo}</span>.
            Joining from Claude Code arrives with the next plugin release; until then the base is readable here.
          </li>
        </ol>
      </main>
    </div>
  );
}
