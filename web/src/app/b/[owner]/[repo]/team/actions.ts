"use server";

import { redirect } from "next/navigation";
import { GitHubError } from "@/lib/github";
import { nameOwnerInCodeOwners } from "@/lib/codeOwners";
import { applyMainRule } from "@/lib/mainRule";
import { cancelInvitation, invite, isBaseOwner, TeamError } from "@/lib/team";
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

// Protect an existing base's main line. Only the base's owner may, worked out
// again from GitHub here, and GitHub itself also requires a repository admin.
export async function protectAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo } = base(formData);
  let outcome: string;
  try {
    if (!(await isBaseOwner(session.token, owner, repo, session.emails))) {
      outcome = "not-owner";
    } else {
      const state = await applyMainRule(session.token, owner, repo);
      outcome = state === "on" ? "protected" : `rule-${state}`;
      // With the rule on, a proposal needs a code owner's approval, so the
      // owner is named in CODEOWNERS wherever the template's placeholder is.
      if (state === "on") {
        try {
          const named = await nameOwnerInCodeOwners({
            token: session.token,
            owner,
            repo,
            login: session.login,
            emails: session.emails,
          });
          if (named === "named") outcome = "protected-owner-named";
        } catch (error) {
          if (error instanceof GitHubError && error.status === 401) throw error;
          outcome = "protected-owner-not-named";
        }
      }
    }
  } catch (error) {
    if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    outcome = "failed";
  }
  redirect(`/b/${owner}/${repo}/team?notice=${outcome}`);
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
