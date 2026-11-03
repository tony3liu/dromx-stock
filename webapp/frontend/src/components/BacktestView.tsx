import { useEffect, useRef, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { FlaskConical, Loader2, AlertTriangle, Play, Square } from "lucide-react";
import { api } from "../api/client";
import type { BacktestRecord } from "../api/types";
import { PageHeader } from "./PageHeader";
import { Kpi } from "./ui/Kpi";
import { TOOLTIP_CONTENT_STYLE } from "../lib/chartTheme";
import { cn, ratingCn } from "../lib/format";

const todayISO = () => new Date().toISOString().slice(0, 10);
const daysAgoISO = (n: number) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
const pct = (v: number | null | undefined, d = 1) => (v == null || !isFinite(v) ? "—" : `${v.toFixed(d)}%`);
const numf = (v: number | null | undefined, d = 2) => (v == null || !isFinite(v) ? "—" : v.toFixed(d));

// Build a compounding equity curve from the per-day strategy returns.
function equityCurve(rec: BacktestRecord): { date: string; equity: number }[] {
  let eq = 1;
  const pts: { date: string; equity: number }[] = [];
  for (const d of rec.days) {
    if (d.direction != null && d.direction !== 0 && d.raw_return != null) {
      eq *= 1 + d.direction * d.raw_return;
    }
    pts.push({ date: d.date, equity: +((eq - 1) * 100).toFixed(2) });
  }
  return pts;
}

export function BacktestView() {
  const [ticker, setTicker] = useState("");
  const [start, setStart] = useState(daysAgoISO(30));
  const [end, setEnd] = useState(todayISO());
  const [holding, setHolding] = useState(5);
  const [estimate, setEstimate] = useState<{ days: number; capped: boolean } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [active, setActive] = useState<BacktestRecord | null>(null);
  const [history, setHistory] = useState<BacktestRecord[]>([]);
  const pollRef = useRef<number | null>(null);

  const refreshList = () => api.backtestList().then(setHistory).catch(() => {});
  useEffect(() => { refreshList(); }, []);

  // Cost estimate whenever inputs change.
  useEffect(() => {
    if (!ticker.trim()) { setEstimate(null); return; }
    let alive = true;
    api.backtestEstimate(ticker.trim().toUpperCase(), start, end)
      .then((e) => alive && setEstimate({ days: e.days, capped: e.capped }))
      .catch(() => alive && setEstimate(null));
    return () => { alive = false; };
  }, [ticker, start, end]);

  // Poll an active backtest until terminal.
  const poll = (id: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const rec = await api.backtestGet(id);
        setActive(rec);
        if (rec.status !== "running") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          refreshList();
        }
      } catch { /* keep polling */ }
    }, 3000);
  };
  useEffect(() => () => { if (pollRef.current) window.clearInterval(pollRef.current); }, []);

  const launch = async () => {
    if (!ticker.trim()) { setErr("请输入标的代码"); return; }
    setErr(null);
    try {
      const res = await api.backtestStart({
        ticker: ticker.trim().toUpperCase(), start_date: start, end_date: end,
        analysts: ["market", "social", "news", "fundamentals", "industry"],
        depth: 1, holding_days: holding,
      });
      // The backend writes an initial checkpoint synchronously, but if the first
      // GET still races, seed a minimal running record and let polling fill it in
      // — don't surface a scary error for a run that actually started.
      const rec = await api.backtestGet(res.id).catch((): BacktestRecord => ({
        id: res.id, ticker: ticker.trim().toUpperCase(), start_date: start, end_date: end,
        holding_days: holding, status: "running", days: [], days_total: res.days,
        days_done: 0, created_at: null, finished_at: null, metrics: null,
      }));
      setActive(rec);
      poll(res.id);
      refreshList();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "启动失败");
    }
  };

  const stop = async () => { if (active) { await api.backtestStop(active.id).catch(() => {}); } };

  const m = active?.metrics;
  const curve = active ? equityCurve(active) : [];

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<FlaskConical size={18} />}
        title="策略回测"
        subtitle="历史区间逐日重跑 AI 决策流程，按真实行情复盘信号表现"
        maxWidth="1180px"
      />
      <div className="mx-auto max-w-[1180px] px-8 py-6">

      {/* form */}
      <div className="mb-6 rounded-[var(--radius-panel)] border border-[var(--color-border)] p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">标的代码</span>
            <input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="NVDA"
              className="w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-brand)]" />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">起始日</span>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)}
              className="w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-brand)]" />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">结束日</span>
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)}
              className="w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-brand)]" />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-[var(--color-ink-faint)]">持有天数</span>
            <input type="number" min={1} max={60} value={holding} onChange={(e) => setHolding(Math.max(1, Number(e.target.value)))}
              className="w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm tnum outline-none focus:border-[var(--color-brand)]" />
          </label>
        </div>

        {estimate && (
          <div className={cn("mt-3 flex items-start gap-2 rounded-[var(--radius-control)] border px-3 py-2 text-xs",
            estimate.capped ? "border-[var(--color-danger)]/30 bg-[var(--color-danger-tint)] text-[var(--color-danger)]" : "border-[var(--color-warn-border)] bg-[var(--color-warn-tint)] text-[var(--color-warn)]")}>
            <AlertTriangle size={13} className="mt-0.5 shrink-0" />
            <span>
              预计 <strong>{estimate.days}</strong> 个交易日 → <strong>{estimate.days}</strong> 次全流程 LLM 调用（耗时+花费随之增加）。
              {estimate.capped && " 已达单次上限，请缩小区间。"}
              {" "}已分析过的同日会自动复用、不重复付费。
            </span>
          </div>
        )}
        {err && <div className="mt-3 rounded-[var(--radius-control)] border border-[var(--color-danger)]/30 bg-[var(--color-danger-tint)] px-3 py-2 text-sm text-[var(--color-danger)]">{err}</div>}

        <div className="mt-4 flex gap-2">
          <button onClick={launch} disabled={!!active && active.status === "running"}
            className="btn-brand flex items-center gap-2 rounded-[var(--radius-control)] px-4 py-1.5 text-sm font-semibold disabled:opacity-50">
            <Play size={15} /> 开始回测
          </button>
          {active?.status === "running" && (
            <button onClick={stop} className="flex items-center gap-2 rounded-[var(--radius-control)] border border-[var(--color-border)] px-4 py-1.5 text-sm font-medium text-[var(--color-ink-soft)] transition hover:border-[var(--color-danger)] hover:text-[var(--color-danger)]">
              <Square size={14} /> 停止
            </button>
          )}
        </div>
      </div>

      {/* active backtest */}
      {active && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
            {active.status === "running" && <Loader2 size={15} className="animate-spin text-[var(--color-brand-dark)]" />}
            <span className="font-semibold text-[var(--color-ink)]">{active.ticker}</span>
            <span>{active.start_date} → {active.end_date}</span>
            <span className="tnum">· 进度 {active.days_done}/{active.days_total}</span>
            <span className={cn("rounded-[5px] px-1.5 py-0.5 text-xs font-medium",
              active.status === "done" ? "bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]"
              : active.status === "error" ? "bg-[var(--color-danger-tint)] text-[var(--color-danger)]"
              : "bg-[var(--color-warn-tint)] text-[var(--color-warn)]")}>
              {active.status === "done" ? "完成" : active.status === "error" ? "失败" : "运行中"}
            </span>
          </div>

          {m && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Kpi label="累计收益" value={pct(m.cumulative_return_pct)} tone={sign(m.cumulative_return_pct)} />
              <Kpi label="命中率" value={pct(m.hit_rate != null ? m.hit_rate * 100 : null, 0)} tone={m.hit_rate != null && m.hit_rate >= 0.5 ? "good" : "bad"} />
              <Kpi label="最大回撤" value={pct(m.max_drawdown_pct)} tone={m.max_drawdown_pct != null && m.max_drawdown_pct < 0 ? "bad" : "neutral"} />
              <Kpi label="夏普" value={numf(m.sharpe)} tone={sign(m.sharpe)} />
              <Kpi label="胜率" value={pct(m.win_rate != null ? m.win_rate * 100 : null, 0)} />
              <Kpi label="盈亏比" value={numf(m.profit_factor)} />
              <Kpi label="交易笔数" value={String(m.trades)} />
              <Kpi label="已打分" value={String(m.days_scored)} />
            </div>
          )}

          {curve.length >= 2 && (
            <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)] p-5">
              <div className="mb-2 text-sm font-semibold text-[var(--color-ink)]">权益曲线 <span className="font-normal text-[var(--color-ink-faint)]">· 累计收益 %</span></div>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={curve} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
                    <defs>
                      <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-brand)" stopOpacity={0.25} />
                        <stop offset="100%" stopColor="var(--color-brand)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--color-ink-faint)" }} width={44} axisLine={false} tickLine={false} unit="%" />
                    <ReferenceLine y={0} stroke="var(--color-border-strong)" />
                    <Tooltip contentStyle={TOOLTIP_CONTENT_STYLE}
                      formatter={(v) => [`${v}%`, "累计收益"]} />
                    <Area type="monotone" dataKey="equity" stroke="var(--color-brand)" strokeWidth={2} fill="url(#eqFill)" isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* per-day table */}
          <div className="overflow-hidden rounded-[var(--radius-panel)] border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-left text-[11px] uppercase tracking-wider text-[var(--color-ink-faint)]">
                  <th className="px-4 py-2.5 font-medium">交易日</th>
                  <th className="px-4 py-2.5 font-medium">评级</th>
                  <th className="px-4 py-2.5 font-medium text-right">区间收益</th>
                  <th className="px-4 py-2.5 font-medium text-center">结果</th>
                </tr>
              </thead>
              <tbody>
                {active.days.slice().reverse().map((d, i) => (
                  <tr key={i} className={cn("border-b border-[var(--color-border)] last:border-0", i % 2 === 1 && "bg-[var(--color-surface-2)]/40")}>
                    <td className="px-4 py-2 tnum text-[var(--color-ink-soft)]">{d.date}</td>
                    <td className="px-4 py-2 text-[var(--color-ink)]">{d.rating ? ratingCn(d.rating) : "—"}</td>
                    <td className={cn("px-4 py-2 text-right tnum", d.raw_return == null ? "text-[var(--color-ink-faint)]" : d.raw_return > 0 ? "text-[var(--color-bull)]" : d.raw_return < 0 ? "text-[var(--color-bear)]" : "text-[var(--color-ink-soft)]")}>
                      {d.raw_return == null ? "—" : `${d.raw_return > 0 ? "+" : ""}${(d.raw_return * 100).toFixed(1)}%`}
                    </td>
                    <td className="px-4 py-2 text-center text-xs">
                      {d.correct == null ? <span className="text-[var(--color-ink-faint)]">—</span>
                        : d.correct ? <span className="font-medium text-[var(--color-bull)]">✓</span>
                        : <span className="font-medium text-[var(--color-danger)]">✗</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* history */}
      {!active && history.length > 0 && (
        <div className="rounded-[var(--radius-panel)] border border-[var(--color-border)]">
          <div className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-ink-faint)]">历史回测</div>
          {history.map((h) => (
            <button key={h.id} onClick={() => { api.backtestGet(h.id).then(setActive); if (h.status === "running") poll(h.id); }}
              className="flex w-full items-center justify-between border-b border-[var(--color-border)] px-4 py-3 text-left transition last:border-0 hover:bg-[var(--color-surface-2)]">
              <div>
                <span className="font-semibold text-[var(--color-ink)]">{h.ticker}</span>
                <span className="ml-2 text-xs text-[var(--color-ink-faint)] tnum">{h.start_date} → {h.end_date}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                {h.metrics?.cumulative_return_pct != null && (
                  <span className={cn("tnum font-semibold", h.metrics.cumulative_return_pct >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]")}>
                    {h.metrics.cumulative_return_pct >= 0 ? "+" : ""}{h.metrics.cumulative_return_pct}%
                  </span>
                )}
                <span className="text-xs text-[var(--color-ink-faint)]">{h.status === "done" ? "完成" : h.status === "error" ? "失败" : "运行中"}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
    </div>
  );
}

function sign(v: number | null | undefined): "good" | "bad" | "neutral" {
  if (v == null) return "neutral";
  return v > 0 ? "good" : v < 0 ? "bad" : "neutral";
}
