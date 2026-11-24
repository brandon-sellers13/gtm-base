"use server";

import { redirect } from "next/navigation";
import { GitHubError } from "@/lib/github";
import { AcceptError, acceptProposal, discardProposal, ProposalNotFound } from "@/lib/proposals";
import { currentSession } from "@/lib/session";

// Next checks that a server action comes from this site's own pages. Who may
// accept is worked out again inside acceptProposal from GitHub, never trusted
// from the form.

function target(formData: FormData) {
  return {
    owner: String(formData.get("owner") ?? ""),
    repo: String(formData.get("repo") ?? ""),
    number: Number(formData.get("number")),
  };
}

export async function acceptAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo, number } = target(formData);
  const page = `/b/${owner}/${repo}/proposals/${number}`;
  let problem: string | null = null;
  try {
    await acceptProposal({
      token: session.token,
      owner,
      repo,
      number,
      verifiedEmails: session.emails,
      name: session.name ?? session.login,
    });
  } catch (error) {
    if (error instanceof AcceptError) problem = error.code;
    else if (error instanceof ProposalNotFound) problem = "gone";
    else if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    else problem = "failed";
  }
  if (problem) redirect(`${page}?problem=${problem}`);
  redirect(`/b/${owner}/${repo}/proposals?notice=accepted&number=${number}`);
}

export async function discardAction(formData: FormData) {
  const session = await currentSession();
  if (!session) redirect("/");
  const { owner, repo, number } = target(formData);
  const reason = String(formData.get("reason") ?? "").trim().slice(0, 500);
  let problem: string | null = null;
  try {
    await discardProposal({ token: session.token, owner, repo, number, reason });
  } catch (error) {
    if (error instanceof ProposalNotFound) problem = "gone";
    else if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    else problem = "failed";
  }
  if (problem) redirect(`/b/${owner}/${repo}/proposals/${number}?problem=${problem}`);
  redirect(`/b/${owner}/${repo}/proposals?notice=discarded&number=${number}`);
}
