import Link from "next/link";
import { redirect } from "next/navigation";
import { Wordmark } from "@/components/Mark";
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
  installed: "GTM Base is installed. If you are not signed in yet, sign in to see your accounts.",
  "base-created": "Your company base is created. Its repository is private, and you own every document in it.",
};

export default async function Home({ searchParams }: { searchParams: Promise<{ notice?: string; base?: string }> }) {
  const { notice, base } = await searchParams;
  const app = githubApp();
  const session = app ? await currentSession() : null;

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between py-6">
        <Wordmark />
        {session && (
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={session.avatarUrl} alt="" className="h-7 w-7 rounded-full border border-line" />
            <span className="font-mono text-xs text-ink-mid">{session.login}</span>
            <form action="/api/auth/logout" method="post">
              <button className="text-sm text-ink-quiet underline-offset-4 hover:underline">Sign out</button>
            </form>
          </div>
        )}
      </header>

      <CleanUrl />
      <main className="flex-1 py-10">
        {notice && NOTICES[notice] && (
          <p className="mb-8 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{NOTICES[notice]}</p>
        )}

        {!app ? <NotConnected /> : !session ? <SignedOut /> : <SignedIn token={session.token} name={session.name ?? session.login} created={base} />}
      </main>
    </div>
  );
}

function NotConnected() {
  return (
    <section className="max-w-xl">
      <h1 className="text-3xl font-bold tracking-[-0.035em]">GTM Base is not connected to GitHub yet.</h1>
      {isDevelopment() ? (
        <>
          <p className="mt-4 text-ink-mid">
            This copy of the app runs on your computer. Connecting it registers a GitHub App that the app signs people in
            with and uses to read and change each company base.
          </p>
          <Link href="/setup" className="mt-8 inline-block rounded-lg bg-ink px-5 py-3 text-sm font-medium text-ground">
            Connect to GitHub
          </Link>
        </>
      ) : (
        <p className="mt-4 text-ink-mid">The person running this app has not finished setting it up.</p>
      )}
    </section>
  );
}

function SignedOut() {
  return (
    <section className="max-w-xl">
      <h1 className="text-4xl font-bold tracking-[-0.035em]">Your team and its AI, working from the same company context.</h1>
      <p className="mt-5 text-lg text-ink-mid">
        Read your company base, approve the changes your team proposes, and see anything that changed without approval.
      </p>
      <a
        href="/api/auth/login"
        className="mt-8 inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-3 text-sm font-medium text-ground"
      >
        Sign in with GitHub
      </a>
      <p className="mt-4 text-sm text-ink-quiet">GTM Base is invite-only while it is being built.</p>
    </section>
  );
}

async function SignedIn({ token, name, created }: { token: string; name: string; created?: string }) {
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
    <section>
      <h1 className="text-3xl font-bold tracking-[-0.035em]">Welcome, {name}.</h1>

      <div className="mt-10 flex items-baseline justify-between">
        <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Your bases</h2>
        <Link href="/new" className="text-sm font-medium text-source underline-offset-4 hover:underline">
          Create a base
        </Link>
      </div>
      {bases === null ? (
        <p className="mt-3 text-sm text-ink-mid">GitHub did not answer just now. Reload the page to try again.</p>
      ) : bases.length === 0 ? (
        <p className="mt-3 text-sm text-ink-mid">
          No company base yet. Create one, or give GTM Base access to a repository that already holds one (it has a{" "}
          <span className="font-mono text-xs">context/map.md</span>) in the account settings below.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {bases.map((base) => (
            <li key={`${base.owner}/${base.name}`} className="flex items-center justify-between gap-3 px-4 py-3">
              <span>
                <span className="text-ink-quiet">{base.owner} / </span>
                <span className="font-medium">{base.name}</span>
                {created === `${base.owner}/${base.name}` && (
                  <span className="ml-2 font-mono text-xs text-resolved">new</span>
                )}
              </span>
              <a href={base.htmlUrl} className="text-sm text-ink-quiet underline-offset-4 hover:underline">
                Open on GitHub
              </a>
            </li>
          ))}
        </ul>
      )}

      <h2 className="mt-12 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Accounts</h2>
      {installations === null ? null : installations.length === 0 ? (
        <p className="mt-3 text-sm text-ink-mid">GTM Base is not installed on any of your accounts yet.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {installations.map((installation) => (
            <li key={installation.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="flex items-center gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={installation.account.avatar_url} alt="" className="h-6 w-6 rounded" />
                <span className="font-medium">{installation.account.login}</span>
                <span className="font-mono text-xs text-ink-quiet">
                  {installation.repository_selection === "all" ? "all repositories" : "selected repositories"}
                </span>
              </span>
              <a
                href={
                  installation.account.type === "Organization"
                    ? `https://github.com/organizations/${installation.account.login}/settings/installations/${installation.id}`
                    : `https://github.com/settings/installations/${installation.id}`
                }
                className="text-sm text-ink-quiet underline-offset-4 hover:underline"
              >
                Choose repositories
              </a>
            </li>
          ))}
        </ul>
      )}
      <a href="/api/auth/login?install=1" className="mt-5 inline-block text-sm font-medium text-source underline-offset-4 hover:underline">
        Install GTM Base on another account
      </a>
    </section>
  );
}
