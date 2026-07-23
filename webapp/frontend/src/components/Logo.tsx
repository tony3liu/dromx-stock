/** DromX brand mark (spec: scripts/reference_ui/ui 规范.html §01 Logo).
 *  An ascending signal line with node dots + dashed AI connection lines on a
 *  deep-dark rounded badge. Inlined so it scales crisply and needs no fetch.
 *  Size via the `size` prop (px). */
export function Logo({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 72 72"
      className={className}
      role="img"
      aria-label="DromX"
    >
      <rect width="72" height="72" rx="16" fill="#0D1117" />
      <rect width="72" height="72" rx="16" fill="#10B981" fillOpacity="0.08" />
      <path
        d="M16 52L26 38L36 44L48 26L56 20"
        stroke="#10B981"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="26" cy="38" r="3" fill="#10B981" opacity="0.7" />
      <circle cx="36" cy="44" r="3" fill="#10B981" opacity="0.5" />
      <circle cx="48" cy="26" r="3.5" fill="#10B981" />
      <circle cx="56" cy="20" r="4" fill="#10B981" />
      <circle cx="56" cy="20" r="7" fill="#10B981" opacity="0.15" />
      <path d="M26 38L48 26" stroke="#10B981" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
      <path d="M36 44L56 20" stroke="#10B981" strokeWidth="1" strokeDasharray="3 3" opacity="0.3" />
    </svg>
  );
}

/** Wordmark lockup: mark + "Drom" white / "X" brand gradient (spec §01). */
export function LogoLockup({ size = 30, className = "" }: { size?: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Logo size={size} className="rounded-[22%]" />
      <span
        className="font-black tracking-tight text-[var(--color-ink)]"
        style={{ fontFamily: "var(--font-display)", fontSize: size * 0.62 }}
      >
        Drom<span className="gradient-text-static">X</span>
      </span>
    </span>
  );
}
