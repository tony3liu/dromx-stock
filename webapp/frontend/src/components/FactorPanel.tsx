import { useEffect, useState } from "react";
import { Loader2, Activity, Info } from "lucide-react";
import { api } from "../api/client";
import type { FactorExposure } from "../api/types";
import { cn } from "../lib/format";

const num = (v: number | null | undefined, d = 2) =>
  v == null || !isFinite(v) ? "—" : v.toFixed(d);
const pct = (v: number | null | undefined, d = 1) =>
  v == null || !isFinite(v) ? "—" : `${v.toFixed(d)}%`;

function Metric({ label, value, hint, tone }: {
  label: string; value: string; hint?: string; tone?: "hot" | "neutral";
}) {
  return (
    <div className="rounded-xl bg-[var(--color-surface-2)] px-3 py-2">
      <div className="text-[11px] text-[var(--color-ink-faint)]">{label}</div>
      <div className={cn("mt-0.5 text-base font-bold tnum",
        tone === "hot" ? "text-[var(--color-danger)]" : "text-[var(--color-ink)]")}>{value}</div>
      {hint && <div className="text-[10px] text-[var(--color-ink-faint)]">{hint}</div>}
    </div>
  );
}

/** Price-based factor / risk exposure of the analysed name (beta, α, vol split). */
export function FactorPanel({ runId }: { runId: string }) {
  const [fx, setFx] = useState<FactorExposure | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.factor(runId).then((r) => alive && setFx(r)).catch(() => alive && setFx(null))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [runId]);

  const betaHot = fx?.available && fx.beta != null && Math.abs(fx.beta) >= 2;

  return (
    <section className="rounded-[var(--radius-card)] bg-[var(--color-surface)] p-5" style={{ boxShadow: "var(--shadow-card)" }}>
      <div className="mb-1 flex items-center gap-2">
        <Activity size={15} className="text-[var(--color-brand-dark)]" />
        <h2 className="text-sm font-bold text-[var(--color-ink)]">因子暴露</h2>
        {fx?.benchmark && <span className="text-xs text-[var(--color-ink-faint)]">· vs {fx.benchmark}</span>}
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-6 text-sm text-[var(--color-ink-faint)]">
          <Loader2 size={16} className="animate-spin" /> 计算中…
        </div>
      )}

      {!loading && !fx?.available && (
        <p className="py-4 text-sm text-[var(--color-ink-faint)]">价格历史不足，无法做因子分解。</p>
      )}

      {!loading && fx?.available && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Metric label="市场 Beta" value={num(fx.beta)} hint={betaHot ? "高系统性敞口" : "系统性敏感度"} tone={betaHot ? "hot" : "neutral"} />
            <Metric label="年化 α" value={pct(fx.alpha_annual_pct)} hint="回归截距" />
            <Metric label="R²" value={num(fx.r_squared)} hint="被市场解释比例" />
            <Metric label="下行 Beta" value={num(fx.downside_beta)} hint="跌市中的敏感度" tone={fx.downside_beta != null && Math.abs(fx.downside_beta) >= 2 ? "hot" : "neutral"} />
            <Metric label="总波动 (年化)" value={pct(fx.total_vol_annual_pct)} />
            <Metric label="特质波动 (年化)" value={pct(fx.idio_vol_annual_pct)} hint={fx.idio_share != null ? `占总风险 ${Math.round(fx.idio_share * 100)}%` : undefined} />
          </div>

          {/* systematic vs idiosyncratic split */}
          {fx.idio_share != null && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-[11px] text-[var(--color-ink-faint)]">
                <span>系统性风险 {Math.round((1 - fx.idio_share) * 100)}%</span>
                <span>特质风险 {Math.round(fx.idio_share * 100)}%</span>
              </div>
              <div className="flex h-2 overflow-hidden rounded-full">
                <div className="h-full bg-[var(--color-brand)]" style={{ width: `${(1 - fx.idio_share) * 100}%` }} />
                <div className="h-full bg-[var(--color-neutral)]" style={{ width: `${fx.idio_share * 100}%` }} />
              </div>
            </div>
          )}

          {/* beta-neutral hedge */}
          {fx.beta_hedge_ratio != null && (
            <div className="mt-3 rounded-xl bg-[var(--color-brand-tint)] px-3 py-2 text-xs text-[var(--color-ink-soft)]">
              <span className="font-semibold text-[var(--color-brand-dark)]">Beta 中性对冲：</span>
              {" "}做空约 <span className="font-semibold tnum">{Math.abs(fx.beta_hedge_ratio).toFixed(2)}×</span> 仓位价值的 {fx.benchmark}，
              可将市场敞口压平（保留 α 与特质收益）。
            </div>
          )}

          <div className="mt-2 flex items-start gap-1 text-[10px] leading-relaxed text-[var(--color-ink-faint)]">
            <Info size={11} className="mt-0.5 shrink-0" />
            <span>{fx.note}</span>
          </div>
        </>
      )}
    </section>
  );
}
