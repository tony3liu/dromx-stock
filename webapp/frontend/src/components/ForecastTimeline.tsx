import { parseForecast } from "../lib/parse";
import { Markdown } from "./Markdown";
import { cn } from "../lib/format";

const HORIZON_CN: Record<string, string> = {
  "T+1": "明日",
  "T+5": "一周",
  "T+20": "一月",
  "T+60": "一季",
};

function dirColor(dir: string | null): string {
  if (!dir) return "var(--color-ink-faint)";
  const d = dir.toLowerCase();
  if (d.includes("bull") || d.includes("看涨") || d.includes("偏多")) return "var(--color-bull)";
  if (d.includes("bear") || d.includes("看跌") || d.includes("偏空")) return "var(--color-bear)";
  return "var(--color-neutral)";
}

/** Forecast as a horizontal T+1/5/20/60 timeline; falls back to markdown. */
export function ForecastTimeline({ md }: { md: string }) {
  const { legs, path } = parseForecast(md);

  return (
    <div
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-[var(--color-brand-dark)]">
        时间轴预测
      </h2>

      {legs.length >= 2 ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {legs.map((leg) => {
              const color = dirColor(leg.direction);
              return (
                <div
                  key={leg.horizon}
                  className="relative rounded-[10px] border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4"
                >
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-bold text-[var(--color-ink)]">{leg.horizon}</span>
                    <span className="text-xs text-[var(--color-ink-faint)]">
                      {HORIZON_CN[leg.horizon] ?? ""}
                    </span>
                  </div>
                  <div className="mt-2 text-base font-bold tnum" style={{ color }}>
                    {leg.range ?? "—"}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
                    <span className="text-xs" style={{ color }}>
                      {leg.direction ?? "—"}
                    </span>
                  </div>
                  {leg.confidence && (
                    <div className="mt-1 text-xs text-[var(--color-ink-faint)]">
                      置信度 {leg.confidence}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          {path && (
            <div className="mt-4 rounded-[10px] bg-[var(--color-brand-tint)] px-4 py-3 text-sm text-[var(--color-ink)]">
              <span className="font-semibold text-[var(--color-brand-dark)]">路径 · </span>
              {path}
            </div>
          )}
          <details className="mt-4 group">
            <summary className={cn(
              "cursor-pointer text-sm text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
            )}>
              展开完整预测
            </summary>
            <div className="mt-3 border-t border-[var(--color-border)] pt-3">
              <Markdown>{md}</Markdown>
            </div>
          </details>
        </>
      ) : (
        <Markdown>{md}</Markdown>
      )}
    </div>
  );
}
