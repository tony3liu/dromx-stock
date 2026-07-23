import { useState } from "react";
import {
  Sparkles, Loader2, Briefcase, Search, LineChart, MessagesSquare,
  Newspaper, Building2, Network, Check, ArrowRight,
} from "lucide-react";
import { api } from "../api/client";
import { ANALYSTS, DEPTHS } from "../api/types";
import { cn } from "../lib/format";
import { Input } from "./ui/Input";

const todayISO = () => new Date().toISOString().slice(0, 10);

// Rich presentation for each analyst — the team is the product's story, so
// each member gets an icon and a one-line mandate, not a bare chip.
const ANALYST_META: Record<string, { icon: typeof LineChart; desc: string }> = {
  market: { icon: LineChart, desc: "价格 · 量能 · 形态" },
  social: { icon: MessagesSquare, desc: "舆情 · 多空情绪" },
  news: { icon: Newspaper, desc: "新闻 · 宏观事件" },
  fundamentals: { icon: Building2, desc: "财务 · 估值" },
  industry: { icon: Network, desc: "产业链 · 供需" },
};

export function NewAnalysis({ onStarted }: { onStarted: (id: string) => void }) {
  const [ticker, setTicker] = useState("");
  const [date, setDate] = useState(todayISO());
  const [analysts, setAnalysts] = useState<string[]>(ANALYSTS.map((a) => a.key));
  const [depth, setDepth] = useState(1);
  const [hasPosition, setHasPosition] = useState(false);
  const [shares, setShares] = useState("");
  const [costBasis, setCostBasis] = useState("");
  const [otherHoldings, setOtherHoldings] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const toggle = (k: string) =>
    setAnalysts((prev) => (prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]));

  const submit = async () => {
    if (!ticker.trim()) {
      setErr("请输入标的代码");
      return;
    }
    if (!analysts.length) {
      setErr("至少选择一个分析师");
      return;
    }
    setErr(null);
    setSubmitting(true);
    try {
      const sh = hasPosition && shares.trim() ? Number(shares) : null;
      const cb = hasPosition && costBasis.trim() ? Number(costBasis) : null;
      // Other holdings drive the portfolio-context factor; only sent when the
      // user declares them (empty → factor skipped, no stale list).
      const holdings = hasPosition
        ? otherHoldings.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
        : [];
      const { id } = await api.createRun({
        ticker: ticker.trim().toUpperCase(),
        trade_date: date,
        analysts,
        depth,
        shares: sh != null && isFinite(sh) ? sh : null,
        cost_basis: cb != null && isFinite(cb) && cb > 0 ? cb : null,
        holdings,
      });
      onStarted(id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "启动失败");
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-[720px]">
      {/* command-center hero — serif display ties the console to the landing */}
      <div className="mb-10 text-center">
        <div className="mx-auto mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
          <Sparkles size={22} />
        </div>
        <h1 className="font-display text-[clamp(1.8rem,3.5vw,2.5rem)] leading-[1.12] tracking-[-0.015em] text-[var(--color-ink)]">
          发起一次深度投研
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-[var(--color-ink-soft)]">
          19 节点 AI 投研团队并行工作，产出带概率、仓位与证伪条件的结构化决策。
        </p>
      </div>

      {/* ticker — the one required input, sized like a command bar */}
      <div className="rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6" style={{ boxShadow: "var(--shadow-card)" }}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_180px]">
          <div className="relative">
            <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]" />
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="输入标的代码：NVDA / 07709.HK / 600519.SS"
              aria-label="标的代码"
              autoFocus
              className="tnum h-14 w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface-2)] pl-11 pr-4 text-[17px] font-medium tracking-wide text-[var(--color-ink)] outline-none transition placeholder:font-sans placeholder:text-[15px] placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-brand)] focus:bg-[var(--color-surface)]"
            />
          </div>
          <Input
            tone="inset"
            size="lg"
            type="date"
            aria-label="分析日期"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="!h-14 text-[15px]"
          />
        </div>
      </div>

      {/* analyst team — rich selectable cards */}
      <div className="mt-4 rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6" style={{ boxShadow: "var(--shadow-card)" }}>
        <SectionLabel>分析师团队</SectionLabel>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          {ANALYSTS.map((a) => {
            const on = analysts.includes(a.key);
            const meta = ANALYST_META[a.key];
            return (
              <button
                key={a.key}
                onClick={() => toggle(a.key)}
                aria-pressed={on}
                className={cn(
                  "relative rounded-[var(--radius-control)] border p-3.5 text-left transition-all duration-150",
                  on
                    ? "border-[var(--color-brand)] bg-[var(--color-brand-tint)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-[var(--color-border-strong)]",
                )}
              >
                {on && (
                  <span className="absolute right-2.5 top-2.5 grid h-4.5 w-4.5 place-items-center rounded-full bg-[var(--color-brand)] text-white">
                    <Check size={11} strokeWidth={3} />
                  </span>
                )}
                <meta.icon size={18} className={on ? "text-[var(--color-brand-dark)]" : "text-[var(--color-ink-faint)]"} />
                <div className={cn("mt-2.5 text-sm font-semibold", on ? "text-[var(--color-brand-dark)]" : "text-[var(--color-ink)]")}>
                  {a.label}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--color-ink-faint)]">{meta?.desc}</div>
              </button>
            );
          })}
        </div>

        <div className="mt-6">
          <SectionLabel>研究深度</SectionLabel>
          <div className="grid grid-cols-3 gap-2.5">
            {DEPTHS.map((d) => {
              const on = depth === d.value;
              return (
                <button
                  key={d.value}
                  onClick={() => setDepth(d.value)}
                  aria-pressed={on}
                  className={cn(
                    "rounded-[var(--radius-control)] border px-3.5 py-3 text-left transition-all duration-150",
                    on
                      ? "border-[var(--color-brand)] bg-[var(--color-brand-tint)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-[var(--color-border-strong)]",
                  )}
                >
                  <div className={cn("text-sm font-semibold", on ? "text-[var(--color-brand-dark)]" : "text-[var(--color-ink)]")}>
                    {d.label}
                  </div>
                  <div className="mt-0.5 text-[11px] text-[var(--color-ink-faint)]">{d.hint}</div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-6">
          <SectionLabel>我的持仓（可选）</SectionLabel>
          <div className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3.5">
            <button
              type="button"
              onClick={() => setHasPosition((v) => !v)}
              className="flex w-full items-center gap-2 text-left"
            >
              <span
                className={cn(
                  "grid h-5 w-9 shrink-0 items-center rounded-full px-0.5 transition",
                  hasPosition ? "bg-[var(--color-brand)]" : "bg-[var(--color-border-strong)]",
                )}
              >
                <span className={cn("h-4 w-4 rounded-full bg-white transition", hasPosition && "translate-x-4")} />
              </span>
              <Briefcase size={15} className="text-[var(--color-ink-soft)]" />
              <span className="text-sm text-[var(--color-ink)]">我已持有该标的</span>
              <span className="ml-auto text-xs text-[var(--color-ink-faint)]">
                {hasPosition ? "按持仓管理分析" : "按新建仓分析"}
              </span>
            </button>
            {hasPosition && (
              <>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="mb-1 block text-xs text-[var(--color-ink-soft)]">持仓股数（做空填负数）</span>
                    <Input
                      tone="white"
                      type="number"
                      value={shares}
                      onChange={(e) => setShares(e.target.value)}
                      placeholder="如 100"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs text-[var(--color-ink-soft)]">成本价 / 股（可选）</span>
                    <Input
                      tone="white"
                      type="number"
                      value={costBasis}
                      onChange={(e) => setCostBasis(e.target.value)}
                      placeholder="如 50.0"
                    />
                  </label>
                </div>
                <label className="mt-3 block">
                  <span className="mb-1 block text-xs text-[var(--color-ink-soft)]">
                    其他持仓（可选，用于组合上下文 · 逗号分隔）
                  </span>
                  <Input
                    tone="white"
                    value={otherHoldings}
                    onChange={(e) => setOtherHoldings(e.target.value)}
                    placeholder="如 MU, 07709.HK:20, 600519.SS"
                  />
                  <span className="mt-1 block text-[11px] text-[var(--color-ink-faint)]">
                    填了才做「组合上下文」（相关性/集中度）；留空则不做该因子。
                  </span>
                </label>
              </>
            )}
          </div>
        </div>
      </div>

      {err && (
        <div className="mt-4 rounded-[var(--radius-control)] border border-[var(--color-bear)]/30 bg-[var(--color-bear-tint)] px-3.5 py-2.5 text-sm text-[var(--color-bear)]">
          {err}
        </div>
      )}

      <button
        onClick={submit}
        disabled={submitting}
        className="btn-brand group mt-5 flex h-13 w-full items-center justify-center gap-2 rounded-[var(--radius-control)] py-3.5 text-[16px] font-semibold disabled:opacity-60"
      >
        {submitting ? <Loader2 size={19} className="animate-spin" /> : <Sparkles size={19} />}
        {submitting ? "投研团队启动中…" : "开始分析"}
        {!submitting && <ArrowRight size={17} className="transition-transform group-hover:translate-x-0.5" />}
      </button>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-ink-faint)]">
      {children}
    </div>
  );
}
