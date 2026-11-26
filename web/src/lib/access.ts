import "server-only";
import { allowedLogins } from "./config";
import { listInstallations } from "./github";
import { reachesAllowedBase } from "./team";

// Who may use GTM Base at all. The web app's sign-in and the connector's
// sign-in both call this, so the two can never let in different people.
//
// Invite-only, extended to teams: a login on the allowlist, or someone who can
// reach a base kept on an allowed person's account.
export async function signInDecision(token: string, login: string): Promise<{ allowed: boolean; team: boolean }> {
  const allowed = allowedLogins();
  if (allowed.has(login.toLowerCase())) return { allowed: true, team: false };
  const team = await reachesAllowedBase(token, await listInstallations(token), allowed);
  return { allowed: team, team };
}

// Checked on every request after sign-in. Taking a login off the list ends its
// access at once. A teammate let in at sign-in stays in; if their access to the
// base is removed, GitHub itself stops showing it to them.
export function stillAllowed(login: string, team: boolean | undefined): boolean {
  return !!team || allowedLogins().has(login.toLowerCase());
}
