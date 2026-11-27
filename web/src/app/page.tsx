import Link from "next/link";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { githubApp, isDevelopment } from "@/lib/config";
import { CleanUrl } from "@/components/CleanUrl";
import { type Base, listBases } from "@/lib/bases";
import { GitHubError, type Installation, listInstallations } from "@/lib/github";
import { currentSession } from "@/lib/session";

const NOTICES: Record<string, string> = {
  "invite-only": "GTM Base is invite-only for now, and this GitHub account is not on the list yet.",
  "sign-in-expired": "That sign-in took too long or was started in another window. Please try again.",
  "sign-in-failed": "GitHub did not complete the sign-in. Please try again.",
  "signed-out-by-github": "GitHub ended this sign-in. Please sign in again.",
  "base-too-large": "That base holds more files than GTM Base reads here. Open it on GitHub instead.",
  "team-only": "You are here as a teammate on someone else's base, so creating a base of your own is not open to you yet.",
  installed: "GTM Base is installed. If you are not signed in yet, sign in to see your accounts.",
  "base-created": "Your company base is created. Its repository is private, and you own every document in it.",
};
// Notices that report a sign-in which did not finish, shown as a problem.
const FAILED = new Set(["sign-in-expired", "sign-in-failed", "signed-out-by-github"]);

export default async function Home({ searchParams }: { searchParams: Promise<{ notice?: string; base?: string }> }) {
  const { notice, base } = await searchParams;
  const app = githubApp();
  const session = app ? await currentSession() : null;

  return (
    <div className="flex min-h-screen flex-col">
      <Header session={session} linked={false} />
      <CleanUrl />
      <main className="flex-1">
        {notice && NOTICES[notice] && (
          <div className="page pb-0">
            <p className={`notice ${FAILED.has(notice) ? "notice-problem" : ""}`} role="status">
              {NOTICES[notice]}
            </p>
          </div>
        )}

        {!app ? <NotConnected /> : !session ? <SignedOut /> : <SignedIn token={session.token} name={session.name ?? session.login} created={base} team={!!session.team} />}
      </main>
    </div>
  );
}

function NotConnected() {
  return (
    <section className="page">
      <h1 className="title">GTM Base is not connected to GitHub yet.</h1>
      {isDevelopment() ? (
        <>
          <p className="lede mt-5">
            This copy of the app runs on your computer. Connecting it registers a GitHub App that the app signs people in
            with and uses to read and change each company base.
          </p>
          <Link href="/setup" className="btn mt-8">
            Connect to GitHub
          </Link>
        </>
      ) : (
        <p className="lede mt-5">The person running this app has not finished setting it up.</p>
      )}
    </section>
  );
}

function SignedOut() {
  return (
    <section className="band">
      <div className="mx-auto max-w-[880px] text-center">
        <h1 className="display">Your team and its AI, working from the same company context.</h1>
        <p className="lede mx-auto mt-6">
          Read your company base, approve the changes your team proposes, and see anything that changed without approval.
        </p>
        <a href="/api/auth/login" className="btn mt-9 min-w-[200px]">
          Sign in with GitHub
        </a>
        <p className="mt-5 text-[15px] text-ink-mid">GTM Base is invite-only while it is being built.</p>
      </div>
    </section>
  );
}

async function SignedIn({
  token,
  name,
  created,
  team,
}: {
  token: string;
  name: string;
  created?: string;
  team: boolean;
}) {
  let installations: Installation[] | null = null;
  let bases: Base[] | null = null;
  let tokenRefused = false;
  try {
    installations = await listInstallations(token);
    bases = await listBases(token, installations);
  } catch (error) {
    tokenRefused = error instanceof GitHubError && error.status === 401;
  }
  // Outside the try, because redirect() works by throwing.
  if (tokenRefused) redirect("/api/auth/expired");

  return (
    <section className="page">
      <h1 className="title">Welcome, {name}.</h1>

      <div className="section-label flex items-end justify-between gap-4">
        <h2 className="heading">Your bases</h2>
        {!team && (
          <Link href="/new" className="btn btn-sm shrink-0">
            Create a base
          </Link>
        )}
      </div>
      {bases === null ? (
        <p className="notice notice-problem mt-6">GitHub did not answer just now. Reload the page to try again.</p>
      ) : bases.length === 0 ? (
        <p className="empty mt-6 text-ink-mid">
          No company base yet. Create one, or give GTM Base access to a repository that already holds one (it has a{" "}
          <span className="font-mono text-[13px]">context/map.md</span>) in the account settings below.
        </p>
      ) : (
        <ul className="rows mt-6">
          {bases.map((base) => (
            <li key={`${base.owner}/${base.name}`} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
              <span className="min-w-0 break-words">
                <span className="text-ink-quiet">{base.owner} / </span>
                <Link href={`/b/${base.owner}/${base.name}`} className="link-quiet font-bold">
                  {base.name}
                </Link>
                {created === `${base.owner}/${base.name}` && <span className="tag ml-2 bg-ok-tint text-ok">new</span>}
              </span>
              <a href={base.htmlUrl} className="meta-mono link-quiet">
                Open on GitHub
              </a>
            </li>
          ))}
        </ul>
      )}

      <h2 className="heading section-label">Accounts</h2>
      {installations === null ? null : installations.length === 0 ? (
        <p className="empty mt-6 text-ink-mid">GTM Base is not installed on any of your accounts yet.</p>
      ) : (
        <ul className="rows mt-6">
          {installations.map((installation) => (
            <li key={installation.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
              <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={installation.account.avatar_url} alt="" className="avatar h-6 w-6" />
                <span className="font-bold">{installation.account.login}</span>
                <span className="meta-mono">
                  {installation.repository_selection === "all" ? "all repositories" : "selected repositories"}
                </span>
              </span>
              <a
                href={
                  installation.account.type === "Organization"
                    ? `https://github.com/organizations/${installation.account.login}/settings/installations/${installation.id}`
                    : `https://github.com/settings/installations/${installation.id}`
                }
                className="meta-mono link-quiet"
              >
                Choose repositories
              </a>
            </li>
          ))}
        </ul>
      )}
      {!team && (
        <a href="/api/auth/login?install=1" className="link mt-6 inline-block">
          Install GTM Base on another account
        </a>
      )}
    </section>
  );
}
