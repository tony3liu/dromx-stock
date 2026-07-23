import { useEffect, useMemo, useState } from "react";
import { GitCompareArrows, Check, AlertCircle } from "lucide-react";
import { api } from "../api/client";
import type { RunRecord, RunSummary } from "../api/types";
import { RatingBadge } from "./RatingBadge";
import { ComparePriceChart } from "./ComparePriceChart";
import { parseDecision } from "../lib/parse";
import { cn } from "../lib/format";
import { PageHeader } from "./PageHeader";

const MAX = 4;

interface Row {
  label: string;
  get: (d: ReturnType<typeof parseDecision>) => string | null;
}
const ROWS: Row[] = [
  { label: "执行摘要", get: (d) => d.executiveSummary },
  { label: "目标价", get: (d) => d.priceTarget },
  { label: "止损", get: (d) => d.stop },
  { label: "仓位", get: (d) => d.sizing },
  { label: "时间框架", get: (d) => d.horizon },
];

/** Side-by-side comparison of 2–4 finished runs + a normalized price overlay. */
export function CompareView({ runs }: { runs: RunSummary[] }) {
  const finished = useMemo(
    () => runs.filter((r) => r.status === "done"),
    [runs],
  );
  const [selected, setSelected] = useState<string[]>([]);
  const [records, setRecords] = useState<Record<string, RunRecord>>({});

  // Default-select the two most recent finished runs.
  useEffect(() => {
    if (selected.length === 0 && finished.length >= 2) {
      setSelected(finished.slice(0, 2).map((r) => r.id));
    }
  }, [finished]); // eslint-disable-line

  // Fetch records for any selected id we don't have yet.
  useEffect(() => {
    selected.forEach((id) => {
      if (records[id]) return;
      api
        .getRun(id)
        .then((rec) => setRecords((m) => ({ ...m, [id]: rec })))
        .catch(() => {});
    });
  }, [selected]); // eslint-disable-line

  const toggle = (id: string) => {
    setSelected((cur) => {
      if (cur.includes(id)) return cur.filter((x) => x !== id);
      if (cur.length >= MAX) return cur; // cap at MAX
      return [...cur, id];
    });
  };

  const chosen = selected.map((id) => records[id]).filter(Boolean) as RunRecord[];
  const tickers = chosen.map((r) => r.ticker);
  const compareDate = chosen[0]?.trade_date;

  if (finished.length < 2) {
    return (
      <div className="mx-auto mt-20 max-w-md text-center">
        <AlertCircle size={32} className="mx-auto mb-3 text-[var(--color-ink-faint)]" />
        <p className="text-[var(--color-ink-soft)]">
          多标的对比需要至少 2 个已完成的分析。先去新建几个分析吧。
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<GitCompareArrows size={18} />}
        title="多标的对比"
        subtitle={`选择 2–${MAX} 个分析进行对比`}
        maxWidth="1180px"
      />
      <div className="mx-auto max-w-[1180px] space-y-5 px-8 py-6">

        {/* picker */}
        <div className="flex flex-wrap gap-2">
          {finished.map((r) => {
            const on = selected.includes(r.id);
            const full = !on && selected.length >= MAX;
            return (
              <button
                key={r.id}
                onClick={() => toggle(r.id)}
                disabled={full}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition",
                  on
                    ? "border-[var(--color-brand)] bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]"
                    : full
                      ? "border-[var(--color-border)] text-[var(--color-ink-faint)] opacity-50"
                      : "border-[var(--color-border)] text-[var(--color-ink-soft)] hover:border-[var(--color-brand)]",
                )}
              >
                {on && <Check size={14} />}
                <span className="font-semibold">{r.ticker}</span>
                <span className="text-xs opacity-70 tnum">{r.trade_date}</span>
              </button>
            );
          })}
        </div>

        {chosen.length >= 2 && (
          <>
            <ComparePriceChart tickers={tickers} date={compareDate} />

            {/* comparison table */}
            <section
              className="overflow-hidden rounded-[var(--radius-card)] bg-[var(--color-surface)]"
              style={{ boxShadow: "var(--shadow-card)" }}
            >
              <div
                className="grid border-b border-[var(--color-border)]"
                style={{ gridTemplateColumns: `120px repeat(${chosen.length}, 1fr)` }}
              >
                <div className="p-4 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                  维度
                </div>
                {chosen.map((r) => (
                  <div key={r.id} className="border-l border-[var(--color-border)] p-4">
                    <div className="font-bold text-[var(--color-ink)]">{r.ticker}</div>
                    <div className="mt-0.5 mb-2 text-xs text-[var(--color-ink-faint)] tnum">
                      {r.trade_date}
                    </div>
                    <RatingBadge rating={r.rating} size="sm" />
                  </div>
                ))}
              </div>

              {ROWS.map((row, ri) => (
                <div
                  key={row.label}
                  className={cn(
                    "grid",
                    ri % 2 ? "bg-[var(--color-surface)]" : "bg-[var(--color-surface-2)]/40",
                  )}
                  style={{ gridTemplateColumns: `120px repeat(${chosen.length}, 1fr)` }}
                >
                  <div className="p-4 text-sm font-medium text-[var(--color-ink-soft)]">
                    {row.label}
                  </div>
                  {chosen.map((r) => {
                    const md = String(
                      (r.final_state as Record<string, unknown>)?.final_trade_decision ?? "",
                    );
                    const val = row.get(parseDecision(md));
                    return (
                      <div
                        key={r.id}
                        className="border-l border-[var(--color-border)] p-4 text-sm text-[var(--color-ink)]"
                      >
                        {val ?? <span className="text-[var(--color-ink-faint)]">—</span>}
                      </div>
                    );
                  })}
                </div>
              ))}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
