"use server";

import { redirect } from "next/navigation";
import { CreateBaseError, createBase } from "@/lib/bases";
import { listInstallations } from "@/lib/github";
import { currentSession } from "@/lib/session";

const REPO_NAME = /^[A-Za-z0-9._-]{1,100}$/;
const EMAIL = /^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]+$/;

// Next checks that a server action comes from this site's own pages, so another
// site cannot submit this form on somebody's behalf.
export async function createBaseAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  // Someone let in only as a teammate on another person's base does not start
  // bases of their own; the allowlist decides who starts using GTM Base.
  if (session.team) redirect("/?notice=team-only");

  const installationId = Number(formData.get("installation"));
  const repoName = String(formData.get("repo") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const forBackup = formData.get("kind") === "backup";

  // The repository name comes back so it can be fixed; the email never goes in an address.
  const back = (problem: string) => redirect(`/new?problem=${problem}&repo=${encodeURIComponent(repoName)}`);

  if (!REPO_NAME.test(repoName) || repoName.startsWith(".")) back("bad-name");
  // A backup target holds nothing yet, so it needs no owner email.
  if (!forBackup && (!EMAIL.test(email) || email.length > 254)) back("bad-email");

  // The account must be one GTM Base is installed on and this person can see.
  const installation = (await listInstallations(session.token)).find((i) => i.id === installationId);
  if (!installation) back("bad-account");
  const isOrganization = installation!.account.type === "Organization";
  if (!isOrganization && installation!.account.login.toLowerCase() !== session.login.toLowerCase()) back("bad-account");

  let created: { owner: string; name: string };
  try {
    created = await createBase({
      token: session.token,
      accountLogin: installation!.account.login,
      accountIsOrganization: isOrganization,
      repoName,
      email,
      login: session.login,
      empty: forBackup,
    });
  } catch (error) {
    back(error instanceof CreateBaseError ? error.code : "failed");
    return;
  }
  if (forBackup) redirect(`/new?ready=${encodeURIComponent(`${created.owner}/${created.name}`)}`);
  redirect(`/?notice=base-created&base=${encodeURIComponent(`${created.owner}/${created.name}`)}`);
}
