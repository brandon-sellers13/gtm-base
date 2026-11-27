"use server";

import { redirect } from "next/navigation";
import { GitHubError } from "@/lib/github";
import { docHref } from "@/lib/reader";
import { currentSession } from "@/lib/session";
import { ConfirmRefused, confirmReflects } from "@/lib/stale/confirm";

// Next checks that a server action comes from this site's own pages. Whether
// this person may answer is worked out again inside confirmReflects from GitHub.
export async function confirmAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const owner = String(formData.get("owner") ?? "");
  const repo = String(formData.get("repo") ?? "");
  const path = String(formData.get("path") ?? "");
  const entryId = String(formData.get("entry") ?? "");
  const page = docHref(owner, repo, path);
  let notice = "confirmed";
  try {
    await confirmReflects({
      token: session.token,
      owner,
      repo,
      path,
      entryId,
      verifiedEmails: session.emails,
      name: session.name ?? session.login,
    });
  } catch (error) {
    if (error instanceof ConfirmRefused) notice = "confirm-refused";
    else if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    else notice = "confirm-failed";
  }
  redirect(`${page}?notice=${notice}`);
}
