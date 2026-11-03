import type { ReactNode } from "react";

/**
 * Shared sticky page header — the single source of truth for page titles across
 * the app so every module's heading uses the exact same size/weight/rhythm.
 *
 * Layout: a sticky hairline bar with an icon + title + optional subtitle on the
 * left and optional actions (buttons, toggles) pinned right. Matches the
 * data-tool aesthetic used by Screener/Monitor/Settings.
 */
export function PageHeader({
  icon,
  title,
  subtitle,
  actions,
  maxWidth = "1180px",
}: {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  maxWidth?: string;
}) {
  return (
    <div className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-canvas)]/75 px-8 backdrop-blur-md">
      <div className="mx-auto flex items-center gap-2.5 py-5" style={{ maxWidth }}>
        <span className="grid h-7 w-7 place-items-center rounded-[8px] bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">{icon}</span>
        <h1 className="text-[15px] font-semibold tracking-tight text-[var(--color-ink)]">{title}</h1>
        {subtitle && <span className="truncate text-xs text-[var(--color-ink-faint)]">· {subtitle}</span>}
        {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
