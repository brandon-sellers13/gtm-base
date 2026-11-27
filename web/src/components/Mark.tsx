// The GTM Base mark: three stacked squares in source-tint, source-mid and
// source, each outlined in ink, on a 120 unit box (from the GTM Base design
// system's gtm-base-mark.svg). Its colours are fixed: never recolour, round or
// shadow it.
export function Mark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden="true" className="shrink-0">
      <rect x="34" y="6" width="80" height="80" fill="#dfe6fb" stroke="#151515" strokeWidth="7" />
      <rect x="20" y="20" width="80" height="80" fill="#9db0ee" stroke="#151515" strokeWidth="7" />
      <rect x="6" y="34" width="80" height="80" fill="#3d63dd" stroke="#151515" strokeWidth="7" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-[10px] whitespace-nowrap">
      <Mark />
      <span className="text-[17px] leading-none font-extrabold tracking-[-0.03em]">GTM Base</span>
    </span>
  );
}
