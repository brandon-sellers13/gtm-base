import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { TEMPLATE_SOURCE } from "@/lib/bases";
import { api, listInstallations } from "@/lib/github";
import { MAIN_RULE_SENTENCES, mainRuleState } from "@/lib/mainRule";
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
  "created-empty":
    "GitHub created the repository but GTM Base could not fill it in, so it is empty. Delete it on GitHub, then create the base again with the same name.",
  failed: "GitHub did not finish creating the base. Nothing else was changed; please try again.",
};

export default async function NewBase({
  searchParams,
}: {
  searchParams: Promise<{ problem?: string; repo?: string; ready?: string }>;
}) {
  const session = await currentSession();
  if (!session) redirect("/");
  if (session.team) redirect("/?notice=team-only");
  const { problem, repo, ready } = await searchParams;
  // An empty repository was just made for a backup: show its address and the
  // line to say in Claude Code. Only an owner/name the app itself could make is shown.
  const shaped = ready && /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}$/.test(ready) ? ready : null;
  // A link anybody can craft must not make this page show someone else's
  // address: it is shown only for a private, empty repository this person can
  // write to, read from GitHub with their own token.
  let readyFor: string | null = null;
  if (shaped) {
    try {
      const repoInfo = await api<{ private: boolean; size: number; permissions?: { push?: boolean } }>(
        `/repos/${shaped}`,
        { token: session.token },
      );
      if (repoInfo.private && repoInfo.size === 0 && repoInfo.permissions?.push) readyFor = shaped;
    } catch {
      readyFor = null;
    }
  }
  // Whether the new repository's main line is protected, read from GitHub.
  const readyRule = readyFor
    ? await mainRuleState(session.token, readyFor.split("/")[0], readyFor.split("/")[1])
    : null;
  const installations = await listInstallations(session.token);
  const usable = installations.filter(
    (i) => i.account.type === "Organization" || i.account.login.toLowerCase() === session.login.toLowerCase(),
  );

  return (
    <div>
      <Header session={session} />
      <main className="gb-page max-w-[640px]">
        <h1 className="gb-h2">Create a company base</h1>
        <p className="gb-lede mt-5">
          GTM Base makes a private repository on GitHub and fills it with the starting files: the map, the folders for each
          part of the base, and you as the owner of every document. Your team and its AI work from this repository.
        </p>

        {readyFor && (
          <div className="gb-card mt-8">
            <p className="gb-card-head">Your empty repository is ready.</p>
            <div className="gb-card-body">
              <p className="gb-ask">
                Open Claude Code in your base&apos;s folder, or a folder linked to it, in a new session, and say:
              </p>
              <p className="border-[1.5px] border-ink bg-ground px-3 py-2 font-mono text-[13px] break-all text-ink">
                back up my base to https://github.com/{readyFor}
              </p>
              <p className="gb-ask">
                GTM Base shows you what would be sent and asks before anything leaves your computer. Once it is sent, the
                base appears on your home page here.
              </p>
              {readyRule && <p className="gb-help">{MAIN_RULE_SENTENCES[readyRule]}</p>}
            </div>
          </div>
        )}

        {problem && PROBLEMS[problem] && (
          <p className="gb-notice problem mt-8" role="alert">
            {PROBLEMS[problem]}
          </p>
        )}

        {usable.length === 0 ? (
          <p className="gb-empty mt-8 text-ink-mid">
            GTM Base is not installed on an account you can create repositories in yet.{" "}
            <a href="/api/auth/login?install=1" className="gb-link">
              Install it on an account
            </a>
            , then come back here.
          </p>
        ) : (
          <form action={createBaseAction} className="gb-card p-4 sm:p-6 mt-8 space-y-6">
            <div>
              <label className="gb-field-label" htmlFor="installation">
                GitHub account
              </label>
              <select
                id="installation"
                name="installation"
                className="gb-input"
              >
                {usable.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.account.login} ({i.account.type === "Organization" ? "organization" : "personal"})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="gb-field-label" htmlFor="repo">
                Repository name
              </label>
              <input
                id="repo"
                name="repo"
                required
                maxLength={100}
                defaultValue={repo ?? "company-base"}
                className="gb-input"
              />
            </div>
            <div>
              <label className="gb-field-label" htmlFor="email">
                Your email, as the owner of the documents
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                defaultValue={session.emails[0] ?? ""}
                className="gb-input"
              />
              <p className="gb-help">
                Use the address your Claude Code uses for git, so the plugin recognises you as the owner.
              </p>
            </div>
            <button className="gb-btn primary w-full sm:w-auto">Create the base</button>
            <p className="gb-meta">
              template {TEMPLATE_SOURCE.ref} · {TEMPLATE_SOURCE.commit.slice(0, 7)}
            </p>
          </form>
        )}

        {usable.length > 0 && (
          <section className="mt-16 border-t-[1.5px] border-ink pt-12">
            <h2 className="gb-heading">Back up a base you already have</h2>
            <p className="mt-3 text-ink-mid">
              Already set up a base in Claude Code? GTM Base makes an empty private repository for it, and Claude Code
              sends your base there after showing you what would go.
            </p>
            <form action={createBaseAction} className="gb-card p-4 sm:p-6 mt-6 space-y-6">
              <input type="hidden" name="kind" value="backup" />
              <div>
                <label className="gb-field-label" htmlFor="backup-installation">
                  GitHub account
                </label>
                <select
                  id="backup-installation"
                  name="installation"
                  className="gb-input"
                >
                  {usable.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.account.login} ({i.account.type === "Organization" ? "organization" : "personal"})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="gb-field-label" htmlFor="backup-repo">
                  Repository name
                </label>
                <input
                  id="backup-repo"
                  name="repo"
                  required
                  maxLength={100}
                  defaultValue="company-base"
                  className="gb-input"
                />
              </div>
              <button className="gb-btn w-full sm:w-auto">Make an empty repository</button>
            </form>
          </section>
        )}
      </main>
    </div>
  );
}
