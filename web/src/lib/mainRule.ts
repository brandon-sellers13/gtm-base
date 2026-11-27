import "server-only";
import { githubApp } from "./config";
import { api, GitHubError } from "./github";
import { validRepo } from "./reader";

// The rule that keeps a base's main line for accepted proposals.
//
// Teammates get GitHub's "push" permission so their Claude Code can open
// proposals on branches of their own, and on its own that permission also lets
// them write to the main line from a plain terminal. A repository ruleset on the
// default branch closes that on GitHub's side, whatever a computer's own checks
// miss: every change reaches it through a pull request a code owner approved,
// nobody can force a push over it or delete it, and only GTM Base itself can
// bypass it, which is how the app's accept, keep, undo and confirm land.
//
// Not verified yet, because no base GTM Base can reach is on a plan that
// enforces rulesets: that GitHub counts a write the app makes with a person's
// own sign-in as the app's, for the bypass. If it does not, those writes are
// refused while the rule is on, and the app says it could not finish.
//
// GitHub only enforces rulesets on a private repository when its account is on
// a paid plan (GitHub Pro for a person, GitHub Team for an organization). On a
// free plan GitHub refuses, the app says so in plain words, and the base works
// as before: a change that skipped approval is listed for its owner to keep or
// undo.

export const RULE_NAME = "GTM Base: the main line takes accepted proposals only";

export type MainRuleState =
  | "on" // the rule is in place and enforced
  | "off" // the base has no such rule yet, and the plan allows one
  | "needs-paid-plan" // GitHub only enforces rules on this repository on a paid plan
  | "no-permission" // the app or the person cannot read or set the repository's rules
  | "unknown"; // GitHub did not answer in a way that settles it

type Ruleset = { id: number; name: string; enforcement: string; source_type?: string };

function rulesetBody(appId: number) {
  return {
    name: RULE_NAME,
    target: "branch",
    enforcement: "active",
    conditions: { ref_name: { include: ["~DEFAULT_BRANCH"], exclude: [] } },
    rules: [
      {
        // A pull request, approved by a code owner (the base's CODEOWNERS file
        // names its owner), so a teammate cannot merge their own proposal on
        // GitHub or move the main line through GitHub's interface.
        type: "pull_request",
        parameters: {
          required_approving_review_count: 1,
          dismiss_stale_reviews_on_push: true,
          require_code_owner_review: true,
          require_last_push_approval: false,
          required_review_thread_resolution: false,
        },
      },
      { type: "non_fast_forward" },
      { type: "deletion" },
    ],
    // GTM Base alone, so the app's own accept, keep, undo and confirm land and
    // nothing else does. Nobody's own push to the main line is let through,
    // the repository's admins included.
    bypass_actors: [{ actor_id: appId, actor_type: "Integration", bypass_mode: "always" }],
  };
}

function stateOf(error: unknown): MainRuleState {
  if (error instanceof GitHubError) {
    // A sign-in that ran out is handled by the page around this, which reads
    // GitHub again; here it only means the answer is not known.
    if (error.needsPaidPlan) return "needs-paid-plan";
    if (error.status === 403 || error.status === 404) return "no-permission";
  }
  return "unknown";
}

async function ours(token: string, owner: string, repo: string): Promise<Ruleset | null> {
  const listed = await api<Ruleset[]>(`/repos/${owner}/${repo}/rulesets?includes_parents=false&per_page=100`, {
    token,
  });
  return listed.find((r) => r.name === RULE_NAME) ?? null;
}

export async function mainRuleState(token: string, owner: string, repo: string): Promise<MainRuleState> {
  if (!validRepo(owner, repo)) return "unknown";
  try {
    const found = await ours(token, owner, repo);
    return found && found.enforcement === "active" ? "on" : "off";
  } catch (error) {
    return stateOf(error);
  }
}

// Put the rule in place, or bring an older copy of it up to date. Never throws
// for a refusal: the state it returns is what the person is told.
export async function applyMainRule(token: string, owner: string, repo: string): Promise<MainRuleState> {
  if (!validRepo(owner, repo)) return "unknown";
  const app = githubApp();
  const appId = Number(app?.appId);
  if (!Number.isInteger(appId) || appId < 1) return "unknown";
  try {
    const found = await ours(token, owner, repo);
    await api(`/repos/${owner}/${repo}/rulesets${found ? `/${found.id}` : ""}`, {
      token,
      method: found ? "PUT" : "POST",
      body: JSON.stringify(rulesetBody(appId)),
    });
    return mainRuleState(token, owner, repo);
  } catch (error) {
    return stateOf(error);
  }
}

// What the base's owner reads about the rule, in plain sentences.
export const MAIN_RULE_SENTENCES: Record<MainRuleState, string> = {
  on:
    "The main line of this base is protected. Changes reach it only as proposals accepted in GTM Base, nobody " +
    "can overwrite or delete it, and nobody can write to it directly, its owner included.",
  off:
    "The main line of this base is not protected yet, so a teammate could write to it directly from a terminal. " +
    "Protecting it means changes reach it only as accepted proposals.",
  "needs-paid-plan":
    "GitHub only protects the main line of a private repository on a paid plan (GitHub Pro for a personal " +
    "account, GitHub Team for an organization). Until then a teammate could write to it directly, and GTM Base " +
    "lists any change that skipped approval so you can keep or undo it.",
  "no-permission":
    "GTM Base could not read or set this repository's rules. Only an admin of the repository can, and GTM Base " +
    "needs its Administration permission approved on this account. Until then GTM Base lists any change that " +
    "skipped approval so you can keep or undo it.",
  unknown:
    "GTM Base could not tell whether the main line of this base is protected. Nothing was changed; try again in " +
    "a moment.",
};
