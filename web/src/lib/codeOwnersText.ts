// The base template's CODEOWNERS file names "@owner-handle" until somebody puts
// the owner's GitHub username in its place. The app does that when it creates a
// base, and when the owner protects the main line of a base that still names
// the placeholder (a base set up in Claude Code and backed up). Only rule lines
// change; the comment that explains the placeholder stays as written. Folders
// the template leaves unowned (learning/changes, work/confirmations) stay that
// way, because only lines that name the placeholder are touched.

export const CODEOWNERS_PATH = "CODEOWNERS";
export const OWNER_HANDLE_PLACEHOLDER = "@owner-handle";

const isRule = (line: string) => !line.startsWith("#");

export function withOwnerHandle(text: string, login: string): string {
  return text
    .split("\n")
    .map((line) => (isRule(line) ? line.replaceAll(OWNER_HANDLE_PLACEHOLDER, `@${login}`) : line))
    .join("\n");
}

export function namesThePlaceholder(text: string): boolean {
  return text.split("\n").some((line) => isRule(line) && line.includes(OWNER_HANDLE_PLACEHOLDER));
}
