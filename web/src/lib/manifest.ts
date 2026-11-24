// The GitHub App's registration, sent to GitHub through the manifest flow so the
// app's credentials go straight from GitHub into web/.env.local without anyone
// copying them by hand.
//
// Permissions are the narrowest set version one needs so far. W2 adds
// "Repository creation" and W5 adds what invites need; changing them later asks
// each installation to accept the new permissions on GitHub.

export function buildManifest(baseUrl: string, name: string) {
  return {
    name,
    url: baseUrl,
    description: "GTM Base: one maintained company context for a marketing team and its AI.",
    callback_urls: [`${baseUrl}/api/auth/callback`],
    redirect_url: `${baseUrl}/setup/done`,
    request_oauth_on_install: true,
    // Public so a teammate's own GitHub account can sign in; the app's own
    // allowlist keeps version one invite-only.
    public: true,
    // No webhook: version one reads GitHub when a page loads, and GitHub refuses a
    // webhook address it cannot reach (such as localhost) even when switched off.
    // Only repository permissions here: GitHub refuses the account-level "Email
    // addresses" permission in a manifest, so W4 adds it in the app's settings.
    default_permissions: {
      metadata: "read",
      contents: "write",
      pull_requests: "write",
    },
  };
}
