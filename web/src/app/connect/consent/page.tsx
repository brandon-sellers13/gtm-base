import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { Header } from "@/components/Header";
import { returnDestination } from "@/lib/connector/clients";
import { connectorEnabled } from "@/lib/connector/config";
import { open } from "@/lib/connector/seal";
import { CONSENT_COOKIE, type Consent } from "@/lib/connector/signin";

// The consent page: which product is asking, where the answer goes, and who is
// signed in. The product's name is whatever it called itself when it
// registered, so the page also names the place the answer goes back to, which
// the server checked against a fixed list.
export default async function ConsentPage() {
  // The cookie is read first so this page is always made per request; checking
  // the switch first would let the build freeze it as a 404.
  const sealed = (await cookies()).get(CONSENT_COOKIE)?.value;
  if (!connectorEnabled()) notFound();
  const consent = await open<Consent>("consent", sealed);

  return (
    <div>
      <Header session={null} linked={false} />
      <main className="page max-w-[560px]">
        {!consent ? (
          <section>
            <h1 className="title">This sign-in has expired.</h1>
            <p className="lede mt-5">Start again from Claude or ChatGPT, where you added GTM Base.</p>
          </section>
        ) : (
          <section>
            <h1 className="title break-words">Connect GTM Base to {consent.clientName}?</h1>
            <div className="panel mt-8 space-y-4 text-ink-mid">
            <p>
              A product calling itself <strong className="text-ink">{consent.clientName}</strong> wants to use GTM Base as
              the GitHub account <strong className="font-mono text-[15px] break-words text-ink">{consent.grant.login}</strong>. If you allow it,
              GTM Base sends the sign-in back to <strong className="text-ink">{returnDestination(consent.redirectUri)}</strong>.
            </p>
            <p>
              It will be able to read the company bases this GitHub account can reach, one base per conversation. It can
              never approve a change; approvals stay with each base&apos;s owner.
            </p>
            <p className="font-bold text-ink">If you did not just add GTM Base to a product yourself, choose Cancel.</p>
            <form action="/api/connector/oauth/consent" method="post" className="flex flex-wrap gap-4 pt-2">
              <input type="hidden" name="nonce" value={consent.nonce} />
              <button
                name="decision"
                value="allow"
                className="btn min-w-[120px]"
              >
                Allow
              </button>
              <button
                name="decision"
                value="cancel"
                className="btn btn-secondary min-w-[120px]"
              >
                Cancel
              </button>
            </form>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
