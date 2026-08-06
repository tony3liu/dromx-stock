import { useEffect, useState } from "react";
import { Loader2, ShieldAlert, Activity, TrendingDown } from "lucide-react";
import { api } from "../api/client";
import type { RiskReport } from "../api/types";
import { cn } from "../lib/format";
import { PageHeader } from "./PageHeader";
import { Card } from "./ui/Card";

function fmtMoney(v: number | null | undefined): string {
  if (v == null) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return v.toLocaleString();
}

function verdictBadge(level: string): { label: string; cls: string } {
  switch (level) {
    case "elevated": return { label: "风险偏高", cls: "bg-[var(--color-danger-tint)] text-[var(--color-danger)]" };
    case "moderate": return { label: "风险中等", cls: "bg-[var(--color-warn-tint)] text-[var(--color-warn)]" };
    case "low": return { label: "风险较低", cls: "bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]" };
    default: return { label: "数据不足", cls: "bg-[var(--color-surface-2)] text-[var(--color-ink-soft)]" };
  }
}

export function RiskView() {
  const [report, setReport] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.risk().then((r) => alive && setReport(r))
      .catch((e) => alive && setErr(e instanceof Error ? e.message : "加载失败"))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, []);

  const badge = report ? verdictBadge(report.verdict) : null;
  const book = report?.book;
  const stress = report?.stress;

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<ShieldAlert size={18} />}
        title="组合风险 (VaR)"
        subtitle="对当前持仓做 VaR 与压力测试：95%/99% 最大预期亏损、成分风险贡献、-10%/-20% 与历史最差单日情景"
        maxWidth="1180px"
      />
      <div className="mx-auto max-w-[1180px] px-8 py-6">

        {loading && (
          <div className="flex items-center gap-2 py-16 text-[var(--color-ink-faint)]">
            <Loader2 size={18} className="animate-spin" /> 计算 VaR 与压力情景…
          </div>
        )}
        {err && !loading && (
          <div className="rounded-[var(--radius-card)] bg-[var(--color-danger-tint)] p-4 text-sm text-[var(--color-danger)]">{err}</div>
        )}

        {report && !loading && !book && (
          <Card className="p-8 text-center text-[var(--color-ink-faint)]">{report.message}</Card>
        )}

        {report && !loading && book && stress && (
          <>
            {/* verdict banner */}
            {badge && (
              <div className="mb-5 flex items-center gap-3 rounded-[var(--radius-card)] p-4 text-sm"
                style={{ boxShadow: "var(--shadow-card)" }}>
                <span className={cn("rounded-full px-3 py-1 text-xs font-semibold", badge.cls)}>{badge.label}</span>
                <span className="text-[var(--color-ink)]">{report.message}</span>
              </div>
            )}

            {/* book VaR */}
            <Card className="mb-5 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-ink)]">
                <Activity size={16} className="text-[var(--color-brand-dark)]" />
                组合 VaR <span className="font-normal text-[var(--color-ink-faint)]">
                  · 组合市值 {fmtMoney(book.book_value)} · 近 {book.n_days} 个交易日 · 年化波动 {book.annualized_vol_pct ?? "—"}%
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {["p95", "p99"].map((k) => {
                  const v = book.var[k];
                  if (!v) return null;
                  const label = k === "p95" ? "95% (20 个交易日约 1 次)" : "99% (100 个交易日约 1 次)";
                  return (
                    <div key={k} className="rounded-[var(--radius-card)] bg-[var(--color-surface-2)] p-4">
                      <div className="text-xs text-[var(--color-ink-soft)]">{label} 最大预期亏损</div>
                      <div className="mt-1 flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-[var(--color-danger)]">{fmtMoney(v.historical_value)}</span>
                        <span className="text-xs text-[var(--color-ink-faint)]">({v.historical_pct ?? "—"}% 历史模拟)</span>
                      </div>
                      <div className="mt-1 text-xs text-[var(--color-ink-faint)]">
                        参数法: {v.parametric_value == null ? "—" : fmtMoney(v.parametric_value)}
                        {v.parametric_pct != null && ` (${v.parametric_pct}%)`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* component VaR */}
            <Card className="mb-5 overflow-x-auto p-4">
              <div className="mb-2 text-sm font-semibold text-[var(--color-ink)]">
                成分风险 <span className="font-normal text-[var(--color-ink-faint)]">· 各标的对组合 95% VaR 的贡献（含 β）</span>
              </div>
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="text-left text-xs text-[var(--color-ink-soft)]">
                    <th className="p-2 font-medium">标的</th>
                    <th className="p-2 font-medium text-right">权重</th>
                    <th className="p-2 font-medium text-right">市值</th>
                    <th className="p-2 font-medium text-right">β(对组合)</th>
                    <th className="p-2 font-medium text-right">成分 VaR</th>
                  </tr>
                </thead>
                <tbody>
                  {report.per_name.map((p) => (
                    <tr key={p.ticker} className="border-t border-[var(--color-surface-2)]">
                      <td className="p-2 font-medium text-[var(--color-ink)]">{p.ticker}</td>
                      <td className="p-2 text-right tnum text-[var(--color-ink)]">{p.weight_pct.toFixed(1)}%</td>
                      <td className="p-2 text-right tnum text-[var(--color-ink-soft)]">{fmtMoney(p.market_value)}</td>
                      <td className="p-2 text-right tnum text-[var(--color-ink-soft)]">{p.beta_to_book == null ? "—" : p.beta_to_book.toFixed(2)}</td>
                      <td className="p-2 text-right tnum font-semibold text-[var(--color-danger)]">
                        {p.component_var_value == null ? "—" : fmtMoney(p.component_var_value)}
                        {p.component_var_pct != null && <span className="ml-1 text-xs font-normal text-[var(--color-ink-faint)]">({p.component_var_pct.toFixed(1)}%)</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {/* stress scenarios */}
            <Card className="p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--color-ink)]">
                <TrendingDown size={16} className="text-[var(--color-danger)]" />
                压力情景
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { label: "大盘 -10%", val: stress.flat_m10 },
                  { label: "大盘 -20%", val: stress.flat_m20 },
                  { label: `历史最差单日${stress.worst_day_pct != null ? ` (${stress.worst_day_pct.toFixed(1)}%)` : ""}`, val: stress.crash_1d },
                ].map((s) => (
                  <div key={s.label} className="rounded-[var(--radius-card)] bg-[var(--color-surface-2)] p-4">
                    <div className="text-xs text-[var(--color-ink-soft)]">{s.label}</div>
                    <div className="mt-1 text-xl font-bold text-[var(--color-danger)]">{fmtMoney(s.val)}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 text-[11px] text-[var(--color-ink-faint)]">
                压力情景为同步平行冲击，未计入标的相关性差异；历史最差单日来自组合近 {book.n_days} 日实际收益。
                {report.skipped.length > 0 && <span> · 跳过（数据不足）：{report.skipped.join(", ")}</span>}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
