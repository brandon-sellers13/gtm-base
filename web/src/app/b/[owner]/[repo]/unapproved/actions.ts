"use server";

import { redirect } from "next/navigation";
import { GitHubError } from "@/lib/github";
import { keepChange, ReviewError, undoChange } from "@/lib/unapproved";
import { currentSession } from "@/lib/session";

// Next checks that a server action comes from this site's own pages. Whether the
// person is the base's owner, and whether the change is still listed, is worked
// out again from GitHub on every call.

async function run(formData: FormData, answer: "kept" | "undone") {
  const session = await currentSession();
  if (!session) redirect("/");
  const owner = String(formData.get("owner") ?? "");
  const repo = String(formData.get("repo") ?? "");
  const sha = String(formData.get("sha") ?? "");
  const options = { token: session.token, owner, repo, sha, login: session.login, emails: session.emails };
  let notice: string = answer;
  try {
    if (answer === "kept") await keepChange(options);
    else await undoChange(options);
  } catch (error) {
    if (error instanceof GitHubError && error.status === 401) redirect("/api/auth/expired");
    notice = error instanceof ReviewError ? error.code : "failed";
  }
  redirect(`/b/${owner}/${repo}/unapproved?notice=${notice}`);
}

export async function keepAction(formData: FormData) {
  await run(formData, "kept");
}

export async function undoAction(formData: FormData) {
  await run(formData, "undone");
}
