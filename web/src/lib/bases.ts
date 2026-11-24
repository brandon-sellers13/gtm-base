import "server-only";
import template from "./base-template.generated.json";
import { api, GitHubError, type Installation } from "./github";

// A base is any repository GTM Base can reach that holds context/map.md. Nothing
// about which repositories are bases is stored anywhere else.

export type Base = {
  owner: string;
  name: string;
  private: boolean;
  htmlUrl: string;
  installationId: number;
};

type Repo = { name: string; owner: { login: string }; private: boolean; html_url: string; default_branch: string };

const MAP_PATH = "context/map.md";
const REPOS_PER_ACCOUNT = 100; // version one looks at the first hundred repositories per account

export async function listBases(token: string, installations: Installation[]): Promise<Base[]> {
  const perAccount = await Promise.all(
    installations.map(async (installation) => {
      const body = await api<{ repositories: Repo[] }>(
        `/user/installations/${installation.id}/repositories?per_page=${REPOS_PER_ACCOUNT}`,
        { token },
      );
      const checked = await Promise.all(
        body.repositories.map(async (repo) => ((await hasMap(token, repo)) ? repo : null)),
      );
      return checked
        .filter((repo): repo is Repo => repo !== null)
        .map((repo) => ({
          owner: repo.owner.login,
          name: repo.name,
          private: repo.private,
          htmlUrl: repo.html_url,
          installationId: installation.id,
        }));
    }),
  );
  return perAccount.flat().sort((a, b) => `${a.owner}/${a.name}`.localeCompare(`${b.owner}/${b.name}`));
}

async function hasMap(token: string, repo: Repo): Promise<boolean> {
  try {
    await api(`/repos/${repo.owner.login}/${repo.name}/contents/${MAP_PATH}`, { token });
    return true;
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) return false;
    throw error;
  }
}

// --- Creating a base ---------------------------------------------------------

export const TEMPLATE_SOURCE = template.source;

const OWNER_PLACEHOLDER_EMAIL = "owner@example.com";

// The same replacements the plugin's create_base makes, plus the CODEOWNERS
// handle, which the web app knows and the plugin does not.
export function fillTemplate(email: string, login: string): { path: string; content: string }[] {
  return template.files.map(({ path, content }) => {
    let text = content;
    if (path.startsWith("context/") || path.startsWith("access/")) {
      text = text.replaceAll(`owner: ${OWNER_PLACEHOLDER_EMAIL}`, `owner: ${email}`);
    } else if (path === "gate-allowlist.txt") {
      text = text.replaceAll(OWNER_PLACEHOLDER_EMAIL, email);
    } else if (path === "CODEOWNERS") {
      // Rules only; the comment that explains the placeholder stays as written.
      text = text
        .split("\n")
        .map((line) => (line.startsWith("#") ? line : line.replaceAll("@owner-handle", `@${login}`)))
        .join("\n");
    }
    return { path, content: text };
  });
}

export class CreateBaseError extends Error {
  constructor(readonly code: "name-taken" | "no-permission" | "no-access" | "failed") {
    super(code);
  }
}

export async function createBase(options: {
  token: string;
  accountLogin: string;
  accountIsOrganization: boolean;
  repoName: string;
  email: string;
  login: string;
}): Promise<{ owner: string; name: string; htmlUrl: string }> {
  const { token, accountLogin, accountIsOrganization, repoName, email, login } = options;

  // 1. The repository: private, with one first commit so it has a branch to build on.
  let repo: Repo;
  try {
    repo = await api<Repo>(accountIsOrganization ? `/orgs/${accountLogin}/repos` : "/user/repos", {
      token,
      method: "POST",
      body: JSON.stringify({
        name: repoName,
        private: true,
        auto_init: true,
        description: "Company base for GTM Base: the context the team and its AI work from.",
      }),
    });
  } catch (error) {
    if (error instanceof GitHubError && error.status === 422) throw new CreateBaseError("name-taken");
    if (error instanceof GitHubError && (error.status === 403 || error.status === 404)) {
      throw new CreateBaseError("no-permission");
    }
    throw new CreateBaseError("failed");
  }

  // 2. The template, as one commit on top of GitHub's first commit.
  const path = `/repos/${repo.owner.login}/${repo.name}`;
  try {
    const head = await api<{ object: { sha: string } }>(`${path}/git/ref/heads/${repo.default_branch}`, { token });
    const parent = await api<{ tree: { sha: string } }>(`${path}/git/commits/${head.object.sha}`, { token });
    const tree = await api<{ sha: string }>(`${path}/git/trees`, {
      token,
      method: "POST",
      body: JSON.stringify({
        base_tree: parent.tree.sha,
        tree: fillTemplate(email, login).map((file) => ({
          path: file.path,
          mode: "100644",
          type: "blob",
          content: file.content,
        })),
      }),
    });
    const commit = await api<{ sha: string }>(`${path}/git/commits`, {
      token,
      method: "POST",
      body: JSON.stringify({
        message: `Start the company base from the GTM Base template\n\nTemplate: ${template.source.ref} at ${template.source.commit.slice(0, 7)}.`,
        tree: tree.sha,
        parents: [head.object.sha],
      }),
    });
    await api(`${path}/git/refs/heads/${repo.default_branch}`, {
      token,
      method: "PATCH",
      body: JSON.stringify({ sha: commit.sha }),
    });
  } catch (error) {
    // The repository exists but GTM Base could not write to it, usually because the
    // installation only covers selected repositories and this one is not among them.
    if (error instanceof GitHubError && (error.status === 403 || error.status === 404)) {
      throw new CreateBaseError("no-access");
    }
    throw new CreateBaseError("failed");
  }

  return { owner: repo.owner.login, name: repo.name, htmlUrl: repo.html_url };
}
