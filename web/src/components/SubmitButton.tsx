"use client";

import { useFormStatus } from "react-dom";

// A form's submit button that says it is working. Accepting, discarding and
// confirming each write to GitHub and take several seconds; without this the
// page shows nothing, people click again, and the second click finds the work
// already done.
export function SubmitButton({
  children,
  pendingText,
  className,
}: {
  children: React.ReactNode;
  pendingText: string;
  className: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} aria-busy={pending} className={`${className} disabled:cursor-wait disabled:opacity-60`}>
      {pending ? pendingText : children}
    </button>
  );
}
