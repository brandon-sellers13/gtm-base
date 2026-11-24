// The diagonal overlap join: source over base, the overlap resolved to ink.
// Construction from brandkit/brand-lock.json (120 unit grid).
export function Mark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden="true">
      <rect x="46" y="46" width="60" height="60" rx="14" fill="var(--signal-resolved)" />
      <rect x="14" y="14" width="60" height="60" rx="14" fill="var(--signal-source)" />
      <rect x="46" y="46" width="28" height="28" rx="8" fill="var(--ink)" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <Mark />
      <span className="text-[17px] font-bold">GTM Base</span>
    </span>
  );
}
