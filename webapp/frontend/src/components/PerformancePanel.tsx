import { useEffect, useState } from "react";
import { Loader2, TrendingUp, Info } from "lucide-react";
import { api } from "../api/client";
import type { PerformanceReport, PerfMetrics } from "../api/types";
import { cn, ratingCn } from "../lib/format";
import { PageHeader } from "./PageHeader";
import { Card } from "./ui/Card";
import { Kpi } from "./ui/Kpi";

const HOLDING_OPTIONS = [1, 5, 20];

const pct = (v: number | null | undefined, digits = 1) =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;
const num = (v: number | null | undefined, digits = 2) =>
  v == null || !isFinite(v) ? "—" : v.toFixed(digits);

function signTone(v: number | null | undefined): "good" | "bad" | "neutral" {
  if (v == null) return "neutral";
  return v > 0 ? "good" : v < 0 ? "bad" : "neutral";
}

export function PerformancePanel() {
  const [holding, setHolding] = useState(5);
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr(null);
    api
      .performance(holding)
      .then((r) => alive && setReport(r))
      .catch((e) => alive && setErr(e instanceof Error ? e.message : "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [holding]);

  const m: PerfMetrics | undefined = report?.metrics;

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<TrendingUp size={18} />}
        title="绩效归因"
        subtitle="对已完成分析的历史决策，按真实行情复盘打分（非重跑）"
        maxWidth="1180px"
        actions={
          <div className="flex rounded-[var(--radius-control)] border border-[var(--color-border)] p-0.5">
            {HOLDING_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setHolding(d)}
                className={cn(
                  "rounded-[6px] px-3 py-1 text-sm font-medium transition-colors",
                  holding === d
                    ? "bg-[var(--color-brand)] text-white"
                    : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
                )}
              >
                持有 {d} 日
              </button>
            ))}
          </div>
        }
      />
      <div className="mx-auto max-w-[1180px] px-8 py-6">

      {loading && (
        <div className="flex items-center gap-2 py-16 text-[var(--color-ink-faint)]">
          <Loader2 size={18} className="animate-spin" /> 正在按行情复盘…
        </div>
      )}
      {err && !loading && (
        <div className="rounded-[var(--radius-card)] bg-[var(--color-danger-tint)] p-4 text-sm text-[var(--color-danger)]">{err}</div>
      )}

      {m && !loading && (
        <>
          <div className="mb-3 flex items-center gap-1.5 text-xs text-[var(--color-ink-faint)]">
            <Info size={13} />
            共 {m.runs_total} 次分析 · 已复盘 {m.resolved} · 待定 {m.pending}
            （待定＝距分析日不足 {m.holding_days} 个交易日，行情未就绪）
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Kpi label="方向命中率" value={pct(m.hit_rate)} hint={`已打分 ${m.scored} 次`} tone={m.hit_rate != null && m.hit_rate >= 0.5 ? "good" : "bad"} />
            <Kpi label="策略平均收益/笔" value={pct(m.avg_strategy_return)} hint="按方向多空计" tone={signTone(m.avg_strategy_return)} />
            <Kpi label="平均超额 (α)" value={pct(m.avg_alpha_return)} hint="对基准指数" tone={signTone(m.avg_alpha_return)} />
            <Kpi label="胜率" value={pct(m.win_rate)} hint="盈利笔数占比" tone={m.win_rate != null && m.win_rate >= 0.5 ? "good" : "bad"} />
            <Kpi label="夏普比率" value={num(m.sharpe)} hint="每笔收益/波动" tone={signTone(m.sharpe)} />
            <Kpi label="索提诺比率" value={num(m.sortino)} hint="下行波动调整" tone={signTone(m.sortino)} />
            <Kpi label="最大回撤" value={pct(m.max_drawdown)} hint="权益曲线" tone={m.max_drawdown != null && m.max_drawdown < 0 ? "bad" : "neutral"} />
            <Kpi label="盈亏比" value={num(m.profit_factor)} hint="总盈利/总亏损" tone={m.profit_factor != null && m.profit_factor >= 1 ? "good" : "bad"} />
          </div>

          {/* by-rating hit rates */}
          {Object.keys(m.by_rating).length > 0 && (
            <div className="mt-5">
              <h2 className="mb-2 text-sm font-semibold text-[var(--color-ink)]">按评级命中率</h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(m.by_rating).map(([rating, s]) => (
                  <div key={rating} className="rounded-xl border border-[var(--color-border)] px-3 py-2 text-sm">
                    <span className="font-medium text-[var(--color-ink)]">{ratingCn(rating)}</span>
                    <span className="ml-2 text-[var(--color-ink-soft)]">
                      {s.correct}/{s.total} · {pct(s.hit_rate, 0)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* per-call table */}
          <Card className="mt-6 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs text-[var(--color-ink-faint)]">
                  <th className="px-4 py-2.5 font-medium">分析日</th>
                  <th className="px-4 py-2.5 font-medium">标的</th>
                  <th className="px-4 py-2.5 font-medium">评级</th>
                  <th className="px-4 py-2.5 font-medium text-right">区间收益</th>
                  <th className="px-4 py-2.5 font-medium text-right">超额 α</th>
                  <th className="px-4 py-2.5 font-medium text-center">结果</th>
                </tr>
              </thead>
              <tbody>
                {report!.outcomes.map((o, i) => (
                  <tr key={i} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="px-4 py-2.5 tnum text-[var(--color-ink-soft)]">{o.trade_date}</td>
                    <td className="px-4 py-2.5 font-medium text-[var(--color-ink)]">{o.ticker}</td>
                    <td className="px-4 py-2.5 text-[var(--color-ink-soft)]">{o.rating ? ratingCn(o.rating) : "—"}</td>
                    <td className={cn("px-4 py-2.5 text-right tnum", o.raw_return == null ? "text-[var(--color-ink-faint)]" : o.raw_return > 0 ? "text-[var(--color-bull)]" : o.raw_return < 0 ? "text-[var(--color-bear)]" : "text-[var(--color-ink-soft)]")}>
                      {o.raw_return == null ? "—" : `${o.raw_return > 0 ? "+" : ""}${pct(o.raw_return)}`}
                    </td>
                    <td className={cn("px-4 py-2.5 text-right tnum", o.alpha_return == null ? "text-[var(--color-ink-faint)]" : o.alpha_return > 0 ? "text-[var(--color-bull)]" : o.alpha_return < 0 ? "text-[var(--color-bear)]" : "text-[var(--color-ink-soft)]")}>
                      {o.alpha_return == null ? "—" : `${o.alpha_return > 0 ? "+" : ""}${pct(o.alpha_return)}`}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {o.status === "pending" ? (
                        <span className="text-xs text-[var(--color-ink-faint)]">待定</span>
                      ) : o.correct == null ? (
                        <span className="text-xs text-[var(--color-ink-faint)]">—</span>
                      ) : o.correct ? (
                        <span className="text-xs font-medium text-[var(--color-bull)]">✓ 命中</span>
                      ) : (
                        <span className="text-xs font-medium text-[var(--color-danger)]">✗ 未中</span>
                      )}
                    </td>
                  </tr>
                ))}
                {report!.outcomes.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-[var(--color-ink-faint)]">还没有可复盘的分析记录</td></tr>
                )}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
    </div>
  );
}
