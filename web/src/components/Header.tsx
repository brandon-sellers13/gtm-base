import Link from "next/link";
import { Wordmark } from "./Mark";
import type { Session } from "@/lib/session";

export function Header({ session }: { session: Session | null }) {
  return (
    <header className="flex items-center justify-between py-6">
      <Link href="/">
        <Wordmark />
      </Link>
      {session && (
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={session.avatarUrl} alt="" className="h-7 w-7 rounded-full border border-line" />
          <span className="hidden font-mono text-xs text-ink-mid sm:inline">{session.login}</span>
          <form action="/api/auth/logout" method="post">
            <button className="text-sm text-ink-quiet underline-offset-4 hover:underline">Sign out</button>
          </form>
        </div>
      )}
    </header>
  );
}
