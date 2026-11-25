import "server-only";
import { notFound, redirect } from "next/navigation";
import { GitHubError } from "./github";
import { BaseNotFound, BaseTooLarge } from "./reader";

// Runs a read for a page and turns GitHub's answers into what the page should do:
// a missing or unreachable base is a 404, a refused token ends the session.
export async function readForPage<T>(read: () => Promise<T>): Promise<T> {
  let outcome: "not-found" | "token-refused" | "too-large" | null = null;
  let value: T | undefined;
  try {
    value = await read();
  } catch (error) {
    if (error instanceof BaseNotFound) outcome = "not-found";
    else if (error instanceof BaseTooLarge) outcome = "too-large";
    else if (error instanceof GitHubError && error.status === 401) outcome = "token-refused";
    else throw error;
  }
  // Outside the try, because notFound() and redirect() work by throwing.
  if (outcome === "not-found") notFound();
  if (outcome === "token-refused") redirect("/api/auth/expired");
  if (outcome === "too-large") redirect("/?notice=base-too-large");
  return value as T;
}
