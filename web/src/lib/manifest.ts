// The GitHub App's registration, sent to GitHub through the manifest flow so the
// app's credentials go straight from GitHub to this computer without anyone
// copying them by hand.
//
// siteUrl is where the app will run (this computer, or the live address).
// returnUrl is where GitHub sends the person back with the credentials, which is
// always this computer, because only the development copy may save them.
//
// No webhook: version one reads GitHub when a page loads, and GitHub refuses a
// webhook address it cannot reach (such as localhost) even when switched off.
// GitHub refused "email_addresses" in a manifest; the app settings form names the
// same permission "emails", which is what is asked for here. If GitHub refuses it
// too, remove it and set "Email addresses: Read-only" in the app's settings.

export function buildManifest(siteUrl: string, returnUrl: string, name: string) {
  return {
    name,
    url: siteUrl,
    description: "GTM Base: one maintained company context for a marketing team and its AI.",
    callback_urls: [`${siteUrl}/api/auth/callback`],
    redirect_url: `${returnUrl}/setup/done`,
    request_oauth_on_install: true,
    // Public so a teammate's own GitHub account can sign in; the app's own
    // allowlist keeps version one invite-only.
    public: true,
    default_permissions: {
      metadata: "read",
      contents: "write",
      pull_requests: "write",
      repository_creation: "write",
      // Inviting a teammate to a base's repository needs this; it also covers
      // repository settings, and the app's code only ever calls the invite endpoints.
      administration: "write",
      emails: "read",
    },
  };
}
