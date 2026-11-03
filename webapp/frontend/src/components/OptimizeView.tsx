import { useEffect, useState } from "react";
import { Loader2, GitBranch, PieChart as PieIcon, Activity, Target } from "lucide-react";
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ZAxis, ReferenceDot, Legend,
} from "recharts";
import { api } from "../api/client";
import type { OptimizeReport } from "../api/types";
import { cn } from "../lib/format";
import { PageHeader } from "./PageHeader";
import { Card } from "./ui/Card";

const STRATEGIES = [
  { key: "max_sharpe", label: "最大夏普", desc: "风险调整后收益最优（默认）" },
  { key: "min_volatility", label: "最小波动", desc: "组合波动率最低" },
  { key: "equal_weight", label: "等权", desc: "基准：每只均分" },
] as const;

// Recharts needs stable colours per series; use the shell palette.
const BRAND = "var(--color-brand-dark)";
const DANGER = "var(--color-danger)";

export function OptimizeView() {
  const [symbolsInput, setSymbolsInput] = useState("");
  const [strategy, setStrategy] = useState<string>("max_sharpe");
  const [report, setReport] = useState<OptimizeReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [source, setSource] = useState<"holdings" | "custom">("holdings");

  const run = (symInput: string, strat: string) => {
    setLoading(true);
    setErr(null);
    const symbols = symInput.split(",").map((s) => s.trim()).filter(Boolean);
    api.optimize(symbols, strat)
      .then((r) => {
        if (r.error) { setErr(r.message || r.error); setReport(null); }
        else setReport(r);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // 默认：优化当前持仓（空 symbols → 后端用持仓）
    run("", "max_sharpe");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const weights = report?.weights ? Object.entries(report.weights) : [];
  const maxW = Math.max(1, ...weights.map(([, v]) => v));

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<GitBranch size={18} />}
        title="组合优化"
        subtitle="均值-方差配置：最大夏普 / 最小波动 / 等权，附有效边界与当前持仓对比（近 120 日日收益）"
        maxWidth="1180px"
      />
      <div className="mx-auto max-w-[1180px] px-8 py-6">

        {/* controls */}
        <Card className="mb-5 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[280px] flex-1">
              <label className="mb-1 block text-xs text-[var(--color-ink-soft)]">
                标的（逗号分隔；留空 = 用当前持仓）
              </label>
              <input
                value={symbolsInput}
                onChange={(e) => { setSymbolsInput(e.target.value); setSource("custom"); }}
                placeholder="AAPL, MSFT, 600519.SS"
                className="w-full rounded-[var(--radius-card)] border border-[var(--color-shell-line)] bg-[var(--color-surface-2)] px-3 py-2 text-sm outline-none focus:border-[var(--color-brand-dark)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--color-ink-soft)]">策略</label>
              <div className="flex gap-1 rounded-[var(--radius-card)] bg-[var(--color-surface-2)] p-1">
                {STRATEGIES.map((s) => (
                  <button key={s.key}
                    onClick={() => { setStrategy(s.key); run(symbolsInput, s.key); }}
                    title={s.desc}
                    className={cn(
                      "rounded-lg px-3 py-1.5 text-xs transition",
                      strategy === s.key
                        ? "bg-[var(--color-brand-tint)] font-semibold text-[var(--color-brand-dark)]"
                        : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]")}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={() => run(symbolsInput, strategy)}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-[var(--radius-card)] bg-[var(--color-brand-dark)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Target size={14} />}
              优化
            </button>
          </div>
          <div className="mt-2 text-[11px] text-[var(--color-ink-faint)]">
            {source === "holdings" ? "当前为持仓模式：空标的列表 → 对现有持仓做配置建议。" : "自定义标的模式。"}
          </div>
        </Card>

        {err && !loading && (
          <div className="rounded-[var(--radius-card)] bg-[var(--color-danger-tint)] p-4 text-sm text-[var(--color-danger)]">{err}</div>
        )}

        {loading && (
          <div className="flex items-center gap-2 py-16 text-[var(--color-ink-faint)]">
            <Loader2 size={18} className="animate-spin" /> 计算有效边界…
          </div>
        )}

        {report && !loading && (
          <>
            {/* headline stats */}
            <div className="mb-5 grid gap-3 sm:grid-cols-3">
              <Card className="p-4">
                <div className="flex items-center gap-1.5 text-xs text-[var(--color-ink-soft)]"><Activity size={13} /> 预期年化收益</div>
                <div className="mt-1 text-2xl font-bold text-[var(--color-brand-dark)]">{report.expected_annual_return_pct.toFixed(1)}%</div>
              </Card>
              <Card className="p-4">
                <div className="flex items-center gap-1.5 text-xs text-[var(--color-ink-soft)]"><PieIcon size={13} /> 年化波动</div>
                <div className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{report.annual_volatility_pct.toFixed(1)}%</div>
              </Card>
              <Card className="p-4">
                <div className="flex items-center gap-1.5 text-xs text-[var(--color-ink-soft)]"><Target size={13} /> 夏普比率</div>
                <div className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{report.sharpe_ratio.toFixed(2)}</div>
              </Card>
            </div>

            <div className="mb-5 grid gap-5 lg:grid-cols-2">
              {/* weights */}
              <Card className="p-4">
                <div className="mb-3 text-sm font-semibold text-[var(--color-ink)]">
                  建议权重 <span className="font-normal text-[var(--color-ink-faint)]">· {STRATEGIES.find((s) => s.key === report.strategy)?.label}</span>
                </div>
                <div className="space-y-2.5">
                  {weights.map(([t, v]) => (
                    <div key={t}>
                      <div className="mb-0.5 flex justify-between text-xs">
                        <span className="font-medium text-[var(--color-ink)]">{t}</span>
                        <span className="tnum text-[var(--color-ink-soft)]">{(v * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                        <div className="h-full rounded-full bg-[var(--color-brand-dark)] transition-all"
                          style={{ width: `${(v / maxW) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                {report.current_weights_pct && (
                  <div className="mt-4 border-t border-[var(--color-shell-line)] pt-3 text-[11px] text-[var(--color-ink-faint)]">
                    当前持仓权重：
                    {Object.entries(report.current_weights_pct).map(([t, v]) => (
                      <span key={t} className="mr-3">{t} {v.toFixed(0)}%</span>
                    ))}
                  </div>
                )}
              </Card>

              {/* efficient frontier */}
              <Card className="p-4">
                <div className="mb-1 text-sm font-semibold text-[var(--color-ink)]">有效边界</div>
                <div className="mb-2 text-[11px] text-[var(--color-ink-faint)]">
                  蓝点 = 每个目标收益下的最小波动组合；红点 = 当前所选策略
                </div>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 6, right: 12, bottom: 4, left: -8 }}>
                      <XAxis type="number" dataKey="vol_pct" name="波动率" unit="%"
                        tick={{ fontSize: 11, fill: "var(--color-ink-soft)" }} stroke="var(--color-shell-line)" />
                      <YAxis type="number" dataKey="ret_pct" name="收益" unit="%"
                        tick={{ fontSize: 11, fill: "var(--color-ink-soft)" }} stroke="var(--color-shell-line)" />
                      <ZAxis range={[50, 50]} />
                      <Tooltip
                        cursor={{ strokeDasharray: "3 3", stroke: "var(--color-shell-line)" }}
                        contentStyle={{ background: "var(--color-surface-2)", border: "1px solid var(--color-shell-line)", borderRadius: 10, fontSize: 12 }}
                        formatter={(value, name) => [value == null ? "—" : `${value}%`, name === "波动率" ? "波动" : "收益"]}
                      />
                      <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-ink-soft)" }} />
                      <Scatter name="有效边界" data={report.frontier} fill={BRAND} />
                      <ReferenceDot
                        x={report.annual_volatility_pct} y={report.expected_annual_return_pct} r={6}
                        fill={DANGER} stroke="#fff" strokeWidth={2} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>

            {/* per-name table */}
            <Card className="overflow-x-auto p-4">
              <div className="mb-2 text-sm font-semibold text-[var(--color-ink)]">
                标的明细 <span className="font-normal text-[var(--color-ink-faint)]">· 年化口径 · 近 {report.lookback_days} 日</span>
              </div>
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="text-left text-xs text-[var(--color-ink-soft)]">
                    <th className="p-2 font-medium">标的</th>
                    <th className="p-2 font-medium text-right">建议权重</th>
                    <th className="p-2 font-medium text-right">年化收益</th>
                    <th className="p-2 font-medium text-right">年化波动</th>
                  </tr>
                </thead>
                <tbody>
                  {report.per_name.map((p) => (
                    <tr key={p.ticker} className="border-t border-[var(--color-surface-2)]">
                      <td className="p-2 font-medium text-[var(--color-ink)]">{p.ticker}</td>
                      <td className="p-2 text-right tnum font-semibold text-[var(--color-brand-dark)]">{p.weight_pct.toFixed(1)}%</td>
                      <td className="p-2 text-right tnum text-[var(--color-ink)]">{p.annual_return_pct.toFixed(1)}%</td>
                      <td className="p-2 text-right tnum text-[var(--color-ink-soft)]">{p.annual_vol_pct.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {report.skipped.length > 0 && (
                <div className="mt-2 text-[11px] text-[var(--color-ink-faint)]">跳过（数据不足）：{report.skipped.join(", ")}</div>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
