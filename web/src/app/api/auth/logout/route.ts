import { NextResponse } from "next/server";
import { appUrl } from "@/lib/config";
import { SESSION_COOKIE } from "@/lib/session";

// POST only, so a link on another site cannot sign somebody out.
export async function POST() {
  const response = NextResponse.redirect(new URL("/", appUrl()), 303);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
