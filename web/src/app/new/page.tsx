import Link from "next/link";
import { redirect } from "next/navigation";
import { Wordmark } from "@/components/Mark";
import { TEMPLATE_SOURCE } from "@/lib/bases";
import { listInstallations } from "@/lib/github";
import { currentSession } from "@/lib/session";
import { createBaseAction } from "./actions";

const PROBLEMS: Record<string, string> = {
  "bad-name": "A repository name can use letters, numbers, dots, dashes and underscores, and cannot start with a dot.",
  "bad-email": "That email address does not look complete.",
  "bad-account": "Pick one of the accounts GTM Base is installed on.",
  "name-taken": "That account already has a repository with this name. Pick another name.",
  "no-permission":
    "GitHub did not let GTM Base create a repository there. The app needs the repository creation permission, and on an organization you need to be allowed to create repositories.",
  "no-access":
    "GitHub created the repository, but GTM Base cannot write to it yet. Give GTM Base access to it in the account's GitHub App settings, then the base can be filled in.",
  failed: "GitHub did not finish creating the base. Nothing else was changed; please try again.",
};

export default async function NewBase({
  searchParams,
}: {
  searchParams: Promise<{ problem?: string; repo?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { problem, repo } = await searchParams;
  const installations = await listInstallations(session.token);
  const usable = installations.filter(
    (i) => i.account.type === "Organization" || i.account.login.toLowerCase() === session.login.toLowerCase(),
  );

  return (
    <div className="mx-auto max-w-xl px-4 py-6 sm:px-6">
      <Link href="/">
        <Wordmark />
      </Link>
      <main className="py-12">
        <h1 className="text-3xl font-bold tracking-[-0.035em]">Create a company base</h1>
        <p className="mt-4 text-ink-mid">
          GTM Base makes a private repository on GitHub and fills it with the starting files: the map, the folders for each
          part of the base, and you as the owner of every document. Your team and its AI work from this repository.
        </p>

        {problem && PROBLEMS[problem] && (
          <p className="mt-8 rounded-lg border border-line bg-notice px-4 py-3 text-sm">{PROBLEMS[problem]}</p>
        )}

        {usable.length === 0 ? (
          <p className="mt-8 text-ink-mid">
            GTM Base is not installed on an account you can create repositories in yet.{" "}
            <a href="/api/auth/login?install=1" className="font-medium text-source underline-offset-4 hover:underline">
              Install it on an account
            </a>
            , then come back here.
          </p>
        ) : (
          <form action={createBaseAction} className="mt-8 space-y-6">
            <div>
              <label className="block text-sm font-medium" htmlFor="installation">
                GitHub account
              </label>
              <select
                id="installation"
                name="installation"
                className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-2"
              >
                {usable.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.account.login} ({i.account.type === "Organization" ? "organization" : "personal"})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium" htmlFor="repo">
                Repository name
              </label>
              <input
                id="repo"
                name="repo"
                required
                maxLength={100}
                defaultValue={repo ?? "company-base"}
                className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium" htmlFor="email">
                Your email, as the owner of the documents
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                defaultValue={session.emails[0] ?? ""}
                className="mt-2 w-full rounded-lg border border-line bg-surface px-3 py-2"
              />
              <p className="mt-2 text-sm text-ink-quiet">
                Use the address your Claude Code uses for git, so the plugin recognises you as the owner.
              </p>
            </div>
            <button className="rounded-lg bg-ink px-5 py-3 text-sm font-medium text-ground">Create the base</button>
            <p className="font-mono text-xs text-ink-quiet">
              template {TEMPLATE_SOURCE.ref} · {TEMPLATE_SOURCE.commit.slice(0, 7)}
            </p>
          </form>
        )}
      </main>
    </div>
  );
}
