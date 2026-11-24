import Link from "next/link";
import { redirect } from "next/navigation";
import { Wordmark } from "@/components/Mark";
import { githubApp, isDevelopment } from "@/lib/config";
import { GitHubError, type Installation, listInstallations } from "@/lib/github";
import { currentSession } from "@/lib/session";

const NOTICES: Record<string, string> = {
  "invite-only": "GTM Base is invite-only for now, and this GitHub account is not on the list yet.",
  "sign-in-expired": "That sign-in took too long or was started in another window. Please try again.",
  "sign-in-failed": "GitHub did not complete the sign-in. Please try again.",
  "signed-out-by-github": "GitHub ended this sign-in. Please sign in again.",
};

export default async function Home({ searchParams }: { searchParams: Promise<{ notice?: string }> }) {
  const { notice } = await searchParams;
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

      <main className="flex-1 py-10">
        {notice && NOTICES[notice] && (
          <p className="mb-8 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{NOTICES[notice]}</p>
        )}

        {!app ? <NotConnected /> : !session ? <SignedOut /> : <SignedIn token={session.token} name={session.name ?? session.login} />}
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

async function SignedIn({ token, name }: { token: string; name: string }) {
  let installations: Installation[] | null = null;
  let tokenRefused = false;
  try {
    installations = await listInstallations(token);
  } catch (error) {
    tokenRefused = error instanceof GitHubError && error.status === 401;
    installations = null;
  }
  // Outside the try, because redirect() works by throwing.
  if (tokenRefused) redirect("/api/auth/expired");

  return (
    <section>
      <h1 className="text-3xl font-bold tracking-[-0.035em]">Welcome, {name}.</h1>
      <p className="mt-3 text-ink-mid">
        GTM Base works on the GitHub accounts it is installed on. A company base lives in a private repository on one of
        them.
      </p>

      <h2 className="mt-10 font-mono text-xs font-bold uppercase tracking-wider text-ink-quiet">Accounts</h2>
      {installations === null ? (
        <p className="mt-3 text-sm text-ink-mid">GitHub did not return your accounts just now. Reload the page to try again.</p>
      ) : installations.length === 0 ? (
        <p className="mt-3 text-sm text-ink-mid">GTM Base is not installed on any of your accounts yet.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {installations.map((installation) => (
            <li key={installation.id} className="flex items-center gap-3 px-4 py-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={installation.account.avatar_url} alt="" className="h-6 w-6 rounded" />
              <span className="font-medium">{installation.account.login}</span>
              <span className="font-mono text-xs text-ink-quiet">
                {installation.account.type === "Organization" ? "organization" : "personal"} ·{" "}
                {installation.repository_selection === "all" ? "all repositories" : "selected repositories"}
              </span>
            </li>
          ))}
        </ul>
      )}
      <a href="/api/auth/login?install=1" className="mt-5 inline-block text-sm font-medium text-source underline-offset-4 hover:underline">
        Install GTM Base on an account
      </a>

      <p className="mt-12 rounded-lg border border-dashed border-line px-4 py-3 text-sm text-ink-quiet">
        Creating a base and reading it arrive next.
      </p>
    </section>
  );
}
