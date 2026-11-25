"use client";

import { useEffect } from "react";

// Notices travel in the address (?notice=...), and on Netlify GitHub's sign-in
// code can be carried onto the page too. Once the page has shown the notice,
// take the query off the address so it does not stay in history or get shared.
export function CleanUrl() {
  useEffect(() => {
    if (window.location.search) window.history.replaceState(null, "", window.location.pathname);
  }, []);
  return null;
}
