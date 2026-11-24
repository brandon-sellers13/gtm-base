import { NextResponse } from "next/server";
import { appUrl } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/session";

// GitHub stopped accepting the person's token (they removed the app's access, or
// GitHub ended it early). Clear the session and ask them to sign in again.
export async function GET() {
  const response = NextResponse.redirect(new URL("/?notice=signed-out-by-github", appUrl()));
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
