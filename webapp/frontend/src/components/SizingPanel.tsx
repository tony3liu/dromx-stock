import { useEffect, useMemo, useState } from "react";
import { Loader2, Calculator } from "lucide-react";
import { api } from "../api/client";
import type { SizingReport } from "../api/types";
import { cn } from "../lib/format";
import { Card } from "./ui/Card";

// Persist the user's account size across runs (local only).
const ACCT_KEY = "ta_account_size";
const RISK_LEVELS = [
  { key: "quarter", label: "¼ Kelly", mult: 0.25, hint: "保守" },
  { key: "half", label: "½ Kelly", mult: 0.5, hint: "标准" },
  { key: "full", label: "满 Kelly", mult: 1.0, hint: "激进" },
] as const;

/** Currency symbol by ticker suffix: HK → HK$, A-share (6-digit / .SS / .SZ) → ¥, else $. */
function currencySymbol(ticker?: string): string {
  if (!ticker) return "$";
  const t = ticker.toUpperCase();
  if (t.endsWith(".HK")) return "HK$";
  if (/^\d{6}$/.test(t) || t.endsWith(".SS") || t.endsWith(".SZ")) return "¥";
  return "$";
}

const fmtMoney = (v: number, sym: string) =>
  v >= 1000 ? `${sym}${Math.round(v).toLocaleString()}` : `${sym}${v.toFixed(0)}`;

const scLabelCn: Record<string, string> = { bear: "看跌", base: "中性", bull: "看涨" };
const scColor: Record<string, string> = {
  bear: "text-[var(--color-bear)]", base: "text-[var(--color-warn)]", bull: "text-[var(--color-bull)]",
};

/** Interactive position sizer: fused scenario distribution + fractional Kelly
 *  from the engine, turned into a concrete position for the user's account. */
export function SizingPanel({ runId, ticker, date }: { runId: string; ticker?: string; date?: string }) {
  const [report, setReport] = useState<SizingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [price, setPrice] = useState<number | undefined>();
  const [account, setAccount] = useState<number>(() => {
    const s = Number(localStorage.getItem(ACCT_KEY));
    return s > 0 ? s : 100000;
  });
  const [risk, setRisk] = useState<(typeof RISK_LEVELS)[number]["key"]>("half");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.sizing(runId).then((r) => alive && setReport(r)).catch(() => alive && setReport(null))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [runId]);

  // Last close → convert the % position into share count (best-effort).
  useEffect(() => {
    if (!ticker) return;
    let alive = true;
    api.price(ticker, date, 5)
      .then((s) => {
        const pts = s.points;
        if (alive && pts.length) setPrice(pts[pts.length - 1].close);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [ticker, date]);

  useEffect(() => {
    if (account > 0) localStorage.setItem(ACCT_KEY, String(account));
  }, [account]);

  const level = RISK_LEVELS.find((l) => l.key === risk)!;

  // Chosen fraction = min(full_kelly * multiplier, single-name cap).
  const chosenPct = useMemo(() => {
    if (!report?.full_kelly_pct) return null;
    return Math.min(report.full_kelly_pct * level.mult, report.max_fraction_pct);
  }, [report, level]);

  const dollars = chosenPct != null ? (account * chosenPct) / 100 : null;
  const shares = dollars != null && price && price > 0 ? Math.floor(dollars / price) : null;
  const sym = currencySymbol(ticker);

  return (
    <Card className="p-5">
      <div className="mb-1 flex items-center gap-2">
        <Calculator size={15} className="text-[var(--color-brand-dark)]" />
        <h2 className="text-sm font-bold text-[var(--color-ink)]">仓位测算</h2>
        <span className="text-xs text-[var(--color-ink-faint)]">· 分数 Kelly</span>
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-6 text-sm text-[var(--color-ink-faint)]">
          <Loader2 size={16} className="animate-spin" /> 计算中…
        </div>
      )}

      {!loading && report && !report.has_scenarios && (
        <p className="py-4 text-sm text-[var(--color-ink-faint)]">
          本次分析无情景概率分布（分析师走了自由文本回退），无法定量测算仓位。
        </p>
      )}

      {!loading && report?.has_scenarios && report.full_kelly_pct == null && (
        <p className="py-4 text-sm text-[var(--color-ink-soft)]">
          融合期望值为负（EV {report.expected_value_pct}%）——Kelly 判定<strong>不建仓</strong>。
        </p>
      )}

      {!loading && report?.has_scenarios && report.full_kelly_pct != null && (
        <>
          {/* fused scenario distribution */}
          <div className="mb-3 space-y-1">
            {report.scenarios.map((s) => (
              <div key={s.label} className="flex items-center gap-2 text-xs">
                <span className={cn("w-8 font-medium", scColor[s.label])}>{scLabelCn[s.label]}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                  <div className={cn("h-full rounded-full", s.label === "bull" ? "bg-[var(--color-bull)]" : s.label === "bear" ? "bg-[var(--color-bear)]" : "bg-[var(--color-neutral)]")}
                    style={{ width: `${Math.round(s.probability * 100)}%` }} />
                </div>
                <span className="w-10 text-right tnum text-[var(--color-ink-soft)]">{Math.round(s.probability * 100)}%</span>
                <span className={cn("w-14 text-right tnum", s.magnitude_pct >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]")}>
                  {s.magnitude_pct >= 0 ? "+" : ""}{s.magnitude_pct}%
                </span>
              </div>
            ))}
          </div>
          <div className="mb-3 flex items-center justify-between rounded-lg bg-[var(--color-surface-2)] px-3 py-1.5 text-xs">
            <span className="text-[var(--color-ink-soft)]">融合期望值 EV</span>
            <span className={cn("font-semibold tnum", (report.expected_value_pct ?? 0) >= 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]")}>
              {report.expected_value_pct}% · 满 Kelly {report.full_kelly_pct}%
            </span>
          </div>

          {/* account input */}
          <label className="mb-1 block text-xs text-[var(--color-ink-faint)]">账户规模</label>
          <div className="mb-3 flex items-center rounded-xl border border-[var(--color-border)] px-3 focus-within:border-[var(--color-brand)]">
            <span className="text-sm text-[var(--color-ink-faint)]">{sym}</span>
            <input
              type="number" min={0} step={1000} value={account}
              onChange={(e) => setAccount(Math.max(0, Number(e.target.value)))}
              className="w-full bg-transparent px-2 py-2 text-sm tnum text-[var(--color-ink)] outline-none"
            />
          </div>

          {/* risk appetite */}
          <div className="mb-3 flex items-center gap-1 rounded-full bg-[var(--color-surface-2)] p-1">
            {RISK_LEVELS.map((l) => (
              <button key={l.key} onClick={() => setRisk(l.key)}
                className={cn("flex-1 rounded-full py-1 text-xs font-medium transition",
                  risk === l.key ? "bg-[var(--color-surface)] text-[var(--color-brand-dark)] shadow-sm" : "text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]")}>
                {l.label}
              </button>
            ))}
          </div>

          {/* result */}
          <div className="rounded-xl bg-[var(--color-brand-tint)] p-3">
            <div className="flex items-baseline justify-between">
              <span className="text-xs text-[var(--color-ink-soft)]">建议仓位（{level.hint}）</span>
              <span className="text-lg font-bold tnum text-[var(--color-brand-dark)]">{chosenPct?.toFixed(1)}%</span>
            </div>
            <div className="mt-1 flex items-baseline justify-between text-sm">
              <span className="tnum font-semibold text-[var(--color-ink)]">{dollars != null ? fmtMoney(dollars, sym) : "—"}</span>
              {shares != null && (
                <span className="tnum text-[var(--color-ink-soft)]">≈ {shares.toLocaleString()} 股 @ {sym}{price?.toFixed(2)}</span>
              )}
            </div>
            {chosenPct != null && chosenPct >= report.max_fraction_pct && (
              <div className="mt-1.5 text-xs text-[var(--color-ink-faint)]">
                已触及单标的上限 {report.max_fraction_pct}%——视为不可超越的锚，而非目标。
              </div>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-[var(--color-ink-faint)]">
            基于融合情景分布的分数 Kelly（防高估：¼–½ 为实践区间）。概率是估计而非真相，请据此审慎。
          </p>
        </>
      )}
    </Card>
  );
}
