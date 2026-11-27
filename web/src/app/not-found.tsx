import Link from "next/link";
import { Header } from "@/components/Header";
import { currentSession } from "@/lib/session";

// Base pages answer 404 for a base that does not exist or that this account
// cannot reach. Next's own 404 page carries none of the app's look.
export default async function NotFound() {
  const session = await currentSession();
  return (
    <div>
      <Header session={session} />
      <main className="gb-page max-w-[640px]">
        <p className="gb-label-mono">404</p>
        <h1 className="gb-h2 mt-2">This page could not be found.</h1>
        <Link href="/" className="gb-btn mt-8">
          Go to the home page
        </Link>
      </main>
    </div>
  );
}
