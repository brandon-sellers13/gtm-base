import Link from "next/link";
import { Wordmark } from "./Mark";
import type { Session } from "@/lib/session";

// The bar at the top of every page. `linked` is off on pages that sit inside a
// flow (setup, the connector consent page), where the mark was never a link.
export function Header({ session, linked = true }: { session: Session | null; linked?: boolean }) {
  return (
    <header className="site-nav">
      {linked ? (
        <Link href="/" className="-m-1 p-1">
          <Wordmark />
        </Link>
      ) : (
        <Wordmark />
      )}
      {session && (
        <div className="flex min-w-0 items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={session.avatarUrl} alt="" width={28} height={28} className="avatar h-7 w-7" />
          <span className="meta-mono hidden truncate text-ink-mid sm:inline">{session.login}</span>
          <form action="/api/auth/logout" method="post">
            <button className="label-mono min-h-[44px] px-1 transition-colors hover:text-state-error">Sign out</button>
          </form>
        </div>
      )}
    </header>
  );
}
