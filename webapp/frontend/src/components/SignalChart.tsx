import { parseSignal } from "../lib/parse";
import { cn } from "../lib/format";

const DIR_COLOR: Record<string, string> = {
  bullish: "var(--color-bull)",
  "mildly bullish": "var(--color-bull)",
  neutral: "var(--color-neutral)",
  mixed: "var(--color-neutral)",
  "mildly bearish": "var(--color-bear)",
  bearish: "var(--color-bear)",
};

function scoreToPct(score: string): number {
  // score in [-2, +2] → 0..100 with 50 = neutral
  const n = parseFloat(score.replace("+", ""));
  if (Number.isNaN(n)) return 50;
  return ((n + 2) / 4) * 100;
}

/** Fused signal panel: EV / agreement headline + per-analyst direction bars. */
export function SignalChart({ md }: { md: string }) {
  const s = parseSignal(md);
  const evNum = s.ev ? parseFloat(s.ev) : null;
  const evColor = evNum == null ? "var(--color-ink)" : evNum >= 0 ? "var(--color-bull)" : "var(--color-bear)";

  return (
    <div
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-[var(--color-brand-dark)]">
        融合信号
      </h2>

      <div className="mb-5 flex flex-wrap gap-3">
        <Stat label="共识方向" value={s.consensus ?? "—"} />
        <Stat label="加权分" value={s.weightedScore ?? "—"} />
        <Stat label="一致性" value={s.agreement ?? "—"} />
        <Stat label="期望收益 EV" value={s.ev ?? "—"} color={evColor} />
      </div>

      {s.skew && (
        <div className="mb-4 inline-block rounded-full bg-[var(--color-surface-2)] px-3 py-1 text-xs text-[var(--color-ink-soft)]">
          payoff · {s.skew}
        </div>
      )}

      <div className="space-y-2.5">
        {s.rows.map((r) => {
          const known = r.direction !== "—";
          const pct = scoreToPct(r.score);
          const color = DIR_COLOR[r.direction.toLowerCase()] ?? "var(--color-border-strong)";
          return (
            <div key={r.analyst} className="flex items-center gap-3">
              <div className="w-24 shrink-0 text-sm text-[var(--color-ink-soft)]">{r.analyst}</div>
              <div className="relative h-2.5 flex-1 rounded-full bg-[var(--color-surface-2)]">
                {/* center tick */}
                <div className="absolute left-1/2 top-1/2 h-3 w-px -translate-y-1/2 bg-[var(--color-border-strong)]" />
                {known && (
                  <div
                    className="absolute top-0 h-2.5 rounded-full transition-all"
                    style={
                      pct >= 50
                        ? { left: "50%", width: `${pct - 50}%`, background: color }
                        : { right: "50%", width: `${50 - pct}%`, background: color }
                    }
                  />
                )}
              </div>
              <div className={cn("w-28 shrink-0 text-right text-xs", known ? "text-[var(--color-ink)]" : "text-[var(--color-ink-faint)]")}>
                {known ? `${r.direction} · ${r.score}` : "未解析"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-[10px] bg-[var(--color-surface-2)] px-4 py-2.5">
      <div className="text-xs text-[var(--color-ink-faint)]">{label}</div>
      <div className="mt-0.5 text-base font-bold tnum" style={{ color: color ?? "var(--color-ink)" }}>
        {value}
      </div>
    </div>
  );
}
