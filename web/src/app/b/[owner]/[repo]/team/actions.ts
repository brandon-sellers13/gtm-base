"use server";

import { redirect } from "next/navigation";
import { GitHubError } from "@/lib/github";
import { cancelInvitation, invite, TeamError } from "@/lib/team";
import { currentSession } from "@/lib/session";

// Next checks that a server action comes from this site's own pages. Whether the
// person is the base's owner is worked out again from GitHub on every call.

function base(formData: FormData) {
  return { owner: String(formData.get("owner") ?? ""), repo: String(formData.get("repo") ?? "") };
}

export async function inviteAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = base(formData);
  const username = String(formData.get("username") ?? "").trim().replace(/^@/, "");
  const page = `/b/${owner}/${repo}/team`;
  let outcome: string;
  try {
    outcome = await invite({
      token: session.token,
      owner,
      repo,
      username,
      login: session.login,
      verifiedEmails: session.emails,
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    outcome = error instanceof TeamError ? error.code : "failed";
  }
  redirect(`${page}?notice=${outcome}&who=${encodeURIComponent(username)}`);
}

export async function cancelAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = base(formData);
  let outcome = "cancelled";
  try {
    await cancelInvitation({
      token: session.token,
      owner,
      repo,
      invitationId: Number(formData.get("invitation")),
      verifiedEmails: session.emails,
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    outcome = error instanceof TeamError ? error.code : "failed";
  }
  redirect(`/b/${owner}/${repo}/team?notice=${outcome}`);
}
