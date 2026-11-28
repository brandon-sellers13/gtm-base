import "server-only";
import { api, GitHubError } from "./github";
import { validRepo } from "./reader";
import { validUsername } from "./team";
import { commitKeptByOwner } from "./unapproved";
import { CODEOWNERS_PATH, namesThePlaceholder, withOwnerHandle } from "./codeOwnersText";

// The main-line rule asks for a code owner's approval, and CODEOWNERS says who
// that is. A base set up in Claude Code and backed up still names the
// template's placeholder there, so on GitHub nobody's approval counts. When the
// owner protects the main line, the app puts their GitHub username in its place.

async function readCodeOwners(token: string, owner: string, repo: string): Promise<string | null> {
  try {
    const file = await api<{ content: string }>(`/repos/${owner}/${repo}/contents/${CODEOWNERS_PATH}`, { token });
    return Buffer.from(file.content, "base64").toString("utf8");
  } catch (error) {
    if (error instanceof GitHubError && error.status === 404) return null;
    throw error;
  }
}

// Whether the base's CODEOWNERS file still names the placeholder.
export async function codeOwnersNamePlaceholder(token: string, owner: string, repo: string): Promise<boolean> {
  if (!validRepo(owner, repo)) return false;
  const text = await readCodeOwners(token, owner, repo);
  return text !== null && namesThePlaceholder(text);
}

// Put the owner's GitHub username in place of the placeholder, as a change the
// owner makes and keeps at once. "already" when there is nothing to replace,
// "missing" when the base has no CODEOWNERS file.
export async function nameOwnerInCodeOwners(options: {
  token: string;
  owner: string;
  repo: string;
  login: string;
  emails: string[];
}): Promise<"named" | "already" | "missing"> {
  const { token, owner, repo, login, emails } = options;
  if (!validRepo(owner, repo) || !validUsername(login)) return "already";
  const text = await readCodeOwners(token, owner, repo);
  if (text === null) return "missing";
  if (!namesThePlaceholder(text)) return "already";
  await commitKeptByOwner({
    token,
    owner,
    repo,
    files: [{ path: CODEOWNERS_PATH, content: withOwnerHandle(text, login) }],
    message: `Name @${login} as the code owner in place of the template's placeholder\n\nDone in GTM Base when the main line was protected.`,
    login,
    emails,
  });
  return "named";
}
