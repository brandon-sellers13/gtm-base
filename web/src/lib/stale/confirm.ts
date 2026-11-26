import "server-only";
import { Unreadable } from "./formats";
import { snapshotOf } from "./github";
import { verdictOf } from "./rules";
import { appendConfirmation } from "./writes";
import type { ChangeEntry } from "./formats";

// The owner's "it already reflects this change", answered in the web app
// (decision 3 of the C2 plan). Everything is worked out again from GitHub at
// the moment of asking and again at the moment of answering; nothing from the
// link or the form is trusted beyond which document and which change it names.

export type ConfirmOffer = { entry: ChangeEntry; email: string };

const today = () => new Date().toISOString().slice(0, 10);

// The offer to show, or null when this person may not answer it now: the
// change no longer overtakes the document, or they do not own it.
export async function confirmOffer(
  token: string,
  owner: string,
  repo: string,
  path: string,
  entryId: string,
  verifiedEmails: string[],
): Promise<ConfirmOffer | null> {
  let verdict;
  try {
    verdict = verdictOf(await snapshotOf(token, owner, repo, today()));
  } catch (error) {
    if (error instanceof Unreadable) return null;
    throw error;
  }
  const entry = verdict.overtakenBy.get(path);
  const info = verdict.documents.get(path);
  if (!entry || entry.id !== entryId || !info) return null;
  const owners = info.owners.map((e) => e.toLowerCase());
  // The rules match the line's author exactly as the map writes it, so the
  // line is written with the owner address as the map spells it.
  const mine = verifiedEmails.map((e) => e.toLowerCase());
  const index = owners.findIndex((email) => mine.includes(email));
  if (index < 0) return null;
  return { entry, email: info.owners[index] };
}

export class ConfirmRefused extends Error {}

export async function confirmReflects(options: {
  token: string;
  owner: string;
  repo: string;
  path: string;
  entryId: string;
  verifiedEmails: string[];
  name: string;
}): Promise<void> {
  const offer = await confirmOffer(
    options.token,
    options.owner,
    options.repo,
    options.path,
    options.entryId,
    options.verifiedEmails,
  );
  if (!offer) throw new ConfirmRefused();
  await appendConfirmation({
    token: options.token,
    owner: options.owner,
    repo: options.repo,
    document: options.path,
    entryId: offer.entry.id,
    email: offer.email,
    name: options.name,
    now: new Date(),
  });
}
