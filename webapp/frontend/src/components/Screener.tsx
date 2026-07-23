import { useCallback, useEffect, useState } from "react";
import { Search, Loader2, Sparkles, RefreshCw, ChevronDown } from "lucide-react";
import { api } from "../api/client";
import type { Market, StrategyMeta, StrategyHit } from "../api/types";
import { cn } from "../lib/format";

const MARKETS: { value: Market; label: string }[] = [
  { value: "hk", label: "港股" },
  { value: "us", label: "美股" },
  { value: "cn", label: "A股" },
];

const todayISO = () => new Date().toISOString().slice(0, 10);

// A ratio-like fraction → signed percent string, red/green coloured.
function pctCell(v: number | null | undefined) {
  if (v == null) return <span className="text-[var(--color-ink-faint)]">—</span>;
  const pct = v * 100;
  const cls = pct > 0 ? "text-[var(--color-bull)]" : pct < 0 ? "text-[var(--color-bear)]" : "text-[var(--color-ink-soft)]";
  return <span className={cn("tnum font-semibold", cls)}>{pct > 0 ? "+" : ""}{pct.toFixed(2)}%</span>;
}

function num(v: unknown, digits = 2): string {
  return typeof v === "number" && isFinite(v) ? v.toFixed(digits) : "—";
}

export function Screener({ onStarted }: { onStarted: (id: string) => void }) {
  const [market, setMarket] = useState<Market>("hk");
  const [strategies, setStrategies] = useState<StrategyMeta[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [rows, setRows] = useState<StrategyHit[] | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [analyzingSym, setAnalyzingSym] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  // Load the strategy list whenever the market changes.
  useEffect(() => {
    let alive = true;
    setLoadingList(true);
    setRows(null);
    setErr(null);
    api.strategies(market)
      .then((r) => {
        if (!alive) return;
        setStrategies(r.strategies);
        setSelected(r.strategies[0]?.id ?? "");
      })
      .catch((e) => alive && setErr(e instanceof Error ? e.message : "加载策略失败"))
      .finally(() => alive && setLoadingList(false));
    return () => { alive = false; };
  }, [market]);

  const strat = strategies.find((s) => s.id === selected);

  const run = useCallback(async () => {
    if (!selected) return;
    setRunning(true);
    setErr(null);
    setRows(null);
    try {
      const res = await api.runStrategy(selected, { market });
      setRows(res.rows);
      setElapsed(res.elapsed_ms);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "选股执行失败");
    } finally {
      setRunning(false);
    }
  }, [selected, market]);

  const analyze = useCallback(async (sym: string) => {
    setAnalyzingSym(sym);
    try {
      const { id } = await api.createRun({
        ticker: sym,
        trade_date: todayISO(),
        analysts: ["market", "social", "news", "fundamentals", "industry"],
        depth: 1,
        strategy_id: selected || null,
      });
      onStarted(id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "发起分析失败");
      setAnalyzingSym(null);
    }
  }, [selected, onStarted]);

  return (
    <div className="h-full overflow-y-auto">
      {/* Sticky hairline toolbar — a data-tool control bar, not a floating card. */}
      <div className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-canvas)]/75 px-8 backdrop-blur-md">
        <div className="mx-auto max-w-[1180px]">
          <div className="flex items-center gap-2.5 pt-6">
            <span className="grid h-7 w-7 place-items-center rounded-[8px] bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]"><Search size={16} /></span>
            <h1 className="text-[15px] font-semibold tracking-tight text-[var(--color-ink)]">选股</h1>
            <span className="text-xs text-[var(--color-ink-faint)]">· 声明式策略全市场筛选，命中可一键深度分析</span>
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4">
            {/* market segmented control */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[var(--color-ink-faint)]">市场</span>
              <div className="flex rounded-[var(--radius-control)] border border-[var(--color-border)] p-0.5">
                {MARKETS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMarket(m.value)}
                    className={cn(
                      "rounded-[6px] px-3 py-1 text-sm font-medium transition-colors",
                      market === m.value
                        ? "bg-[var(--color-brand)] text-white"
                        : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
                    )}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* strategy select */}
            <div className="flex min-w-[240px] max-w-[420px] flex-1 items-center gap-2">
              <span className="text-xs font-medium text-[var(--color-ink-faint)]">策略</span>
              <div className="relative flex-1">
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                  disabled={loadingList || !strategies.length}
                  className="w-full appearance-none rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] py-1.5 pl-3 pr-8 text-sm text-[var(--color-ink)] outline-none transition focus:border-[var(--color-brand)] disabled:opacity-60"
                >
                  {loadingList && <option>加载中…</option>}
                  {strategies.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}（{s.id}）</option>
                  ))}
                </select>
                <ChevronDown size={15} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]" />
              </div>
            </div>

            <button
              onClick={run}
              disabled={running || !selected}
              className="btn-brand flex items-center gap-2 rounded-[var(--radius-control)] px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
            >
              {running ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
              运行选股
            </button>
          </div>

          {strat && (
            <p className="pb-3 text-xs text-[var(--color-ink-soft)]">
              {strat.description}
              {strat.tags.length > 0 && (
                <span className="ml-2 text-[var(--color-ink-faint)]">
                  {strat.tags.map((t) => `#${t}`).join(" ")}
                </span>
              )}
            </p>
          )}
        </div>
      </div>

      {/* body */}
      <div className="mx-auto max-w-[1180px] px-8 py-6">
        {err && (
          <div className="mb-4 rounded-[var(--radius-panel)] border border-[var(--color-bear)]/30 bg-[var(--color-bear-tint)] px-4 py-3 text-sm text-[var(--color-bear)]">{err}</div>
        )}

        {running && (
          <div className="flex items-center gap-2 py-20 text-sm text-[var(--color-ink-faint)]">
            <Loader2 size={16} className="animate-spin" /> 正在拉取全市场快照并计算指标（首次较慢，当日缓存后秒开）…
          </div>
        )}

        {rows && !running && rows.length === 0 && (
          <div className="py-20 text-center text-sm text-[var(--color-ink-faint)]">
            今日该策略无命中标的。可换个策略或调整市场再试。
          </div>
        )}

        {rows && !running && rows.length > 0 && (
          <div>
            <div className="mb-3 flex items-baseline justify-between">
              <span className="text-sm font-semibold text-[var(--color-ink)]">命中 <span className="text-[var(--color-brand-dark)]">{rows.length}</span> 只</span>
              {elapsed != null && <span className="text-xs text-[var(--color-ink-faint)]">耗时 {(elapsed / 1000).toFixed(1)}s</span>}
            </div>
            <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-[var(--color-border)]">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-2)] text-[11px] uppercase tracking-wider text-[var(--color-ink-faint)]">
                    <th className="px-3 py-2.5 text-left font-medium">代码</th>
                    <th className="px-3 py-2.5 text-left font-medium">名称</th>
                    <th className="px-3 py-2.5 text-right font-medium">现价</th>
                    <th className="px-3 py-2.5 text-right font-medium">涨跌幅</th>
                    <th className="px-3 py-2.5 text-right font-medium">换手</th>
                    <th className="px-3 py-2.5 text-right font-medium">RSI14</th>
                    <th className="px-3 py-2.5 text-right font-medium">评分</th>
                    <th className="px-3 py-2.5 text-right font-medium"></th>
                  </tr>
                </thead>
                <tbody className="stagger-fade">
                  {rows.map((r, i) => (
                    <tr
                      key={r.symbol}
                      className={cn(
                        "group transition-colors hover:bg-[var(--color-brand-tint)]/40",
                        i % 2 === 1 && "bg-[var(--color-surface-2)]/40",
                      )}
                    >
                      <td className="px-3 py-2 font-mono text-[13px] font-medium text-[var(--color-ink)] whitespace-nowrap">{r.symbol}</td>
                      <td className="px-3 py-2 text-[var(--color-ink-soft)] whitespace-nowrap">{r.name ?? "—"}</td>
                      <td className="px-3 py-2 text-right tnum text-[var(--color-ink)]">{num(r.close)}</td>
                      <td className="px-3 py-2 text-right">{pctCell(r.change_pct)}</td>
                      <td className="px-3 py-2 text-right tnum text-[var(--color-ink-soft)]">
                        {r.turnover_rate != null ? `${(r.turnover_rate * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-3 py-2 text-right tnum text-[var(--color-ink-soft)]">{num(r.rsi_14, 1)}</td>
                      <td className="px-3 py-2 text-right">
                        <ScoreCell score={r.score} />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => analyze(r.symbol)}
                          disabled={analyzingSym === r.symbol}
                          title="发起深度分析"
                          className="inline-flex items-center gap-1 rounded-[6px] px-2 py-1 text-xs font-medium text-[var(--color-ink-faint)] opacity-0 transition hover:bg-[var(--color-brand-tint)] hover:text-[var(--color-brand-dark)] focus:opacity-100 group-hover:opacity-100 disabled:opacity-100"
                        >
                          {analyzingSym === r.symbol ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                          分析
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Score with a thin inline bar (0–100) — visual weight without a chip.
function ScoreCell({ score }: { score?: number | null }) {
  if (score == null || !isFinite(score)) return <span className="text-[var(--color-ink-faint)]">—</span>;
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="inline-flex items-center gap-2">
      <span className="h-1 w-10 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
        <span className="block h-full rounded-full bg-[var(--color-brand)]" style={{ width: `${pct}%` }} />
      </span>
      <span className="tnum w-6 text-right text-[13px] font-semibold text-[var(--color-ink)]">{score.toFixed(0)}</span>
    </div>
  );
}
