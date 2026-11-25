import { NextRequest, NextResponse } from "next/server";
import { appUrl } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/session";

// GitHub stopped accepting the person's token (they removed the app's access, or
// GitHub ended it early). Clear the session and ask them to sign in again.
export async function GET(request: NextRequest) {
  // Only a page navigation may sign someone out here; an image or other embed
  // pointing at this address (say, inside a document) must not.
  const dest = request.headers.get("sec-fetch-dest");
  if (dest && dest !== "document") return new NextResponse(null, { status: 400 });
  const response = NextResponse.redirect(new URL("/?notice=signed-out-by-github", appUrl()));
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
