import { randomBytes } from "node:crypto";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/Header";
import { githubApp, isDevelopment } from "@/lib/config";

const NOTICES: Record<string, string> = {
  created:
    "The GitHub App was created and its settings were saved on this computer. The app reloads them on its own; give it a few seconds, then sign in.",
  "setup-expired": "That took too long or was started in another window. Please start again.",
  "setup-failed": "GitHub did not hand back the app's settings. Please start again.",
  "live-created":
    "The GitHub App for the live address was created. Its settings are saved in web/.env.live, ready to send to Netlify with scripts/send-live-settings.mjs.",
  "live-url": "The live address must be a plain https address, such as https://gtm-base-app.netlify.app.",
};

export default async function Setup({ searchParams }: { searchParams: Promise<{ notice?: string }> }) {
  if (!isDevelopment()) notFound();
  const { notice } = await searchParams;
  const connected = githubApp() !== null;
  const suffix = randomBytes(2).toString("hex");

  return (
    <div>
      <Header session={null} linked={false} />
      <main className="gb-page max-w-[640px]">
        {notice && NOTICES[notice] && (
          <p
            className={`gb-notice mb-8 ${notice === "setup-expired" || notice === "setup-failed" || notice === "live-url" ? "problem" : ""}`}
            role="status"
          >
            {NOTICES[notice]}
          </p>
        )}
        {connected ? (
          <>
            <h1 className="gb-h2">Connected to GitHub.</h1>
            <Link href="/" className="gb-btn primary mt-8">
              Go to sign in
            </Link>

            <h2 className="gb-heading mt-16 border-t-[1.5px] border-ink pt-12">Connect the live address</h2>
            <p className="mt-3 text-ink-mid">
              The live site needs its own GitHub App, because GitHub only sends people back to the address an app was
              created for. GitHub sends you back here afterwards, and the app&apos;s settings are saved in{" "}
              <span className="font-mono text-[15px]">web/.env.live</span>, without being shown on screen.
            </p>
            <form action="/setup/start" method="post" className="gb-card p-4 sm:p-6 mt-6">
              <input type="hidden" name="target" value="live" />
              <label className="gb-field-label" htmlFor="liveUrl">
                Live address
              </label>
              <input
                id="liveUrl"
                name="liveUrl"
                defaultValue="https://gtm-base-app.netlify.app"
                className="gb-input"
              />
              <label className="gb-field-label mt-6" htmlFor="liveName">
                App name on GitHub (must be unique across GitHub)
              </label>
              <input
                id="liveName"
                name="name"
                defaultValue="GTM Base"
                maxLength={34}
                className="gb-input"
              />
              <button className="gb-btn primary mt-6 w-full sm:w-auto">
                Continue to GitHub
              </button>
            </form>
          </>
        ) : (
          <>
            <h1 className="gb-h2">Connect this copy of GTM Base to GitHub.</h1>
            <p className="gb-lede mt-5">
              GitHub will show you a page to create a GitHub App for GTM Base under your account. Nothing is created until
              you click the button on that page. The app&apos;s settings then come straight back to this computer and are
              saved in <span className="font-mono text-[15px]">web/.env.local</span>, without being shown on screen.
            </p>
            <p className="mt-4 text-ink-mid">
              It asks to read and write repository files and pull requests on the accounts you install it on, and nothing
              else for now.
            </p>
            <form action="/setup/start" method="post" className="gb-card p-4 sm:p-6 mt-8">
              <label className="gb-field-label" htmlFor="name">
                App name on GitHub (must be unique across GitHub)
              </label>
              <input
                id="name"
                name="name"
                defaultValue={`GTM Base Dev ${suffix}`}
                maxLength={34}
                className="gb-input"
              />
              <button className="gb-btn primary mt-6 w-full sm:w-auto">
                Continue to GitHub
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}
