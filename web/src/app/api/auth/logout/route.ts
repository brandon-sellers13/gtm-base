import { NextResponse } from "next/server";
import { appUrl } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/session";

// POST only, so following a link cannot sign somebody out. (A form on another
// site still could; that only signs a person out, so it is accepted here, and
// routes that change anything must check where the request came from.)
export async function POST() {
  const response = NextResponse.redirect(new URL("/", appUrl()), 303);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
