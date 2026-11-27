"use client";

import { useState } from "react";

// Copies a fixed piece of text, such as a Project instruction or the connector's
// address, and says so for a moment afterwards.
export function CopyButton({ text, label }: { text: string; label: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    setTimeout(() => setState("idle"), 2000);
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="shrink-0 rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium hover:bg-notice"
    >
      {state === "copied" ? "Copied" : state === "failed" ? "Select the text and copy it" : label}
    </button>
  );
}
