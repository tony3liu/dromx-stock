import { cn } from "../../lib/format";

/** One KPI tile. `tone` colours the value (good/bad/neutral). Hairline-border
 *  panel styling, matching the de-capsule data-tool card language. */
export function Kpi({ label, value, hint, tone = "neutral" }: {
  label: string;
  value: string;
  hint?: string;
  tone?: "good" | "bad" | "neutral";
}) {
  const toneCls =
    tone === "good" ? "text-[var(--color-bull)]"
    : tone === "bad" ? "text-[var(--color-bear)]"
    : "text-[var(--color-ink)]";
  return (
    <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)] p-4">
      <div className="text-xs text-[var(--color-ink-faint)]">{label}</div>
      <div className={cn("mt-1 text-xl font-bold tnum", toneCls)}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-[var(--color-ink-faint)]">{hint}</div>}
    </div>
  );
}
