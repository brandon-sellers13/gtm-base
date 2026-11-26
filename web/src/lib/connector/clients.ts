import "server-only";

// Which products may register, by the return address they register with.
// Claude and ChatGPT's addresses are from their docs and were used in the
// spike; Claude Code signs in through a loopback address on any port (RFC 8252).

const PRODUCTS: { pattern: RegExp; where: string }[] = [
  { pattern: /^https:\/\/claude\.ai\/api\/mcp\/auth_callback$/, where: "claude.ai" },
  { pattern: /^https:\/\/claude\.com\/api\/mcp\/auth_callback$/, where: "claude.com" },
  { pattern: /^https:\/\/chatgpt\.com\/connector_platform_oauth_redirect$/, where: "chatgpt.com" },
  { pattern: /^http:\/\/localhost:\d{1,5}\/callback$/, where: "a program on this computer" },
  { pattern: /^http:\/\/127\.0\.0\.1:\d{1,5}\/callback$/, where: "a program on this computer" },
];

export const returnAddressAllowed = (uri: string) => PRODUCTS.some((p) => p.pattern.test(uri));

// Where an answer goes, in words a person can check on the consent page.
export const returnDestination = (uri: string) => PRODUCTS.find((p) => p.pattern.test(uri))?.where ?? "an unknown place";

export type Client = { r: string[]; n: string };
