import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, Download, Check, Loader2, ChevronLeft, ChevronRight, AlertTriangle, RotateCw, FileText } from "lucide-react";
import { useRunStream } from "../hooks/useRunStream";
import { ProgressTree } from "./ProgressTree";
import { Markdown } from "./Markdown";
import { RatingBadge } from "./RatingBadge";
import { DecisionCard } from "./DecisionCard";
import { ForecastTimeline } from "./ForecastTimeline";
import { SignalChart } from "./SignalChart";
import { PriceChart } from "./PriceChart";
import { ScenarioChart } from "./ScenarioChart";
import { ResearchPanel } from "./ResearchPanel";
import { SizingPanel } from "./SizingPanel";
import { FactorPanel } from "./FactorPanel";
import { QAPanel } from "./QAPanel";
import { REPORT_SECTIONS, SECTION_CN } from "../api/types";
import { api } from "../api/client";
import { buildReportMarkdown, copyText, downloadText } from "../lib/export";
import { cn } from "../lib/format";
import { MascotScene } from "./Mascot";

const DECISION_KEY = "final_trade_decision";
const label = (key: string) => SECTION_CN[key] ?? key;

// Pipeline node → report section. Nodes without a section (Growth/Risk
// Analyst, the three risk specialists) feed other nodes and stay non-navigable.
const NODE_TO_SECTION: Record<string, string> = {
  "Regime Analyst": "regime_report",
  "Market Analyst": "market_report",
  "Sentiment Analyst": "sentiment_report",
  "News Analyst": "news_report",
  "Fundamentals Analyst": "fundamentals_report",
  "Industry Analyst": "industry_report",
  "Signal Aggregator": "signal_aggregation",
  "Event Impact": "event_impact",
  "Key Question": "key_question",
  "Research Manager": "investment_plan",
  Trader: "trader_investment_plan",
  "Risk Consensus": "risk_consensus",
  "Forecast Synthesizer": "forecast_report",
  "Portfolio Manager": DECISION_KEY,
};
const SECTION_TO_NODE: Record<string, string> = Object.fromEntries(
  Object.entries(NODE_TO_SECTION).map(([n, k]) => [k, n]),
);

// Sections rendered as a bespoke widget rather than plain markdown.
function SectionBody({ sectionKey, md }: { sectionKey: string; md: string }) {
  if (sectionKey === DECISION_KEY) return <DecisionCard decisionMd={md} />;
  if (sectionKey === "forecast_report")
    return (
      <div className="space-y-4">
        <ScenarioChart forecastMd={md} />
        <ForecastTimeline md={md} />
      </div>
    );
  if (sectionKey === "signal_aggregation") return <SignalChart md={md} />;
  return (
    <section
      className="animate-pop rounded-[var(--radius-card)] bg-[var(--color-surface)] p-7"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-4 border-b border-[var(--color-border)] pb-3">
        <h2 className="text-[19px] font-semibold tracking-tight text-[var(--color-ink)]">{label(sectionKey)}</h2>
        <div className="mt-0.5 text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-faint)]">
          {REPORT_SECTIONS.find((r) => r.key === sectionKey)?.label ?? sectionKey}
        </div>
      </div>
      <Markdown>{md}</Markdown>
    </section>
  );
}

export function RunWorkbench({ runId, ticker, onOpenRun, onStatusSettled }: { runId: string; ticker?: string; onOpenRun?: (id: string, ticker?: string) => void; onStatusSettled?: () => void }) {
  const s = useRunStream(runId);
  const [tk, setTk] = useState(ticker);
  const [date, setDate] = useState<string | undefined>();
  const [copied, setCopied] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfErr, setPdfErr] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const paramsRef = useRef<{ ticker: string; trade_date: string; analysts: string[]; depth: number } | null>(null);

  // Stage navigation: which dimension is shown. Auto-advance to the newest
  // arrived section UNLESS the user has manually navigated.
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const userPinnedRef = useRef(false);
  const completedOnceRef = useRef(false);
  const chipsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTk(ticker);
    api
      .getRun(runId)
      .then((r) => {
        if (!ticker) setTk(r.ticker);
        setDate(r.trade_date);
        paramsRef.current = {
          ticker: r.ticker,
          trade_date: r.trade_date,
          analysts: r.analysts || [],
          depth: r.depth || 3,
        };
      })
      .catch(() => {});
  }, [runId, ticker]);

  const onRetry = async () => {
    const p = paramsRef.current;
    if (!p || retrying) return;
    setRetrying(true);
    try {
      const { id } = await api.createRun(p);
      onOpenRun?.(id, p.ticker);
    } catch {
      setRetrying(false);
    }
  };

  // Reset stage state when switching runs.
  useEffect(() => {
    userPinnedRef.current = false;
    completedOnceRef.current = false;
    setActiveKey(null);
  }, [runId]);

  const running = !s.complete && !s.error;

  // When the run settles (complete / error), tell the parent so the history
  // sidebar refreshes its status badge (it was stuck on "运行中" otherwise).
  const settledRef = useRef(false);
  useEffect(() => {
    settledRef.current = false;
  }, [runId]);
  useEffect(() => {
    if ((s.complete || s.error) && !settledRef.current) {
      settledRef.current = true;
      onStatusSettled?.();
    }
  }, [s.complete, s.error, onStatusSettled]);

  // Stage list EXCLUDES the final decision — that's pinned as a hero card on top.
  const ordered = useMemo(
    () => REPORT_SECTIONS.filter((sec) => sec.key !== DECISION_KEY && s.sections[sec.key]),
    [s.sections],
  );
  const orderedKeys = ordered.map((o) => o.key);
  const decisionMd = s.sections[DECISION_KEY];

  // Progress counters for the collapsed pill.
  const nodeTotal = Object.keys(s.nodeStatus).length || 19;
  const nodeDone = Object.values(s.nodeStatus).filter((v) => v === "done").length;

  // Auto-advance to the most recently arrived (non-decision) section while the
  // run is STREAMING. The moment the run completes, jump to the FIRST stage so
  // the user reads top-down instead of being left at the last dimension.
  const newest = [...s.sectionOrder].reverse().find((k) => k !== DECISION_KEY) ?? null;
  const first = orderedKeys[0] ?? null;
  useEffect(() => {
    if (userPinnedRef.current) return;
    if (s.complete) {
      if (!completedOnceRef.current) {
        completedOnceRef.current = true;
        if (first) setActiveKey(first);
      }
    } else if (newest) {
      setActiveKey(newest);
    }
  }, [newest, s.complete, first]);

  // Keep activeKey valid.
  useEffect(() => {
    if (activeKey && !s.sections[activeKey] && orderedKeys.length) {
      setActiveKey(orderedKeys[orderedKeys.length - 1]);
    }
  }, [activeKey, orderedKeys.length]); // eslint-disable-line

  const pick = (key: string) => {
    userPinnedRef.current = true;
    setActiveKey(key);
    document.getElementById("stage-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  // Pipeline rail navigation: a done node jumps to its report section; the
  // Portfolio Manager node scrolls to the pinned decision hero instead.
  const pickNode = (node: string) => {
    const key = NODE_TO_SECTION[node];
    if (!key) return;
    if (key === DECISION_KEY) {
      document.getElementById("decision-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    pick(key);
  };
  const idx = activeKey ? orderedKeys.indexOf(activeKey) : -1;
  const go = (delta: number) => {
    const ni = idx + delta;
    if (ni >= 0 && ni < orderedKeys.length) pick(orderedKeys[ni]);
  };

  // Keep the active chip scrolled into view.
  useEffect(() => {
    chipsRef.current
      ?.querySelector('[data-active="true"]')
      ?.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
  }, [activeKey]);

  const exportMd = () => buildReportMarkdown(tk ?? runId, date ?? "", s.rating, s.sections);
  const onCopy = async () => {
    if (await copyText(exportMd())) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };
  const onDownload = () =>
    downloadText(`${(tk ?? runId).replace(/[^\w.-]/g, "_")}_${date ?? ""}.md`, exportMd());
  const onExportPdf = async () => {
    if (pdfBusy) return;
    setPdfBusy(true);
    setPdfErr(null);
    try {
      const fn = `DromX_${(tk ?? runId).replace(/[^\w.-]/g, "_")}_${date ?? ""}.pdf`;
      await api.downloadReportPdf(runId, fn);
    } catch (e) {
      setPdfErr(e instanceof Error ? e.message : "报告生成失败");
    } finally {
      setPdfBusy(false);
    }
  };

  return (
    <div className="relative h-full overflow-y-auto">
      {/* sticky header: identity + progress pill + actions, then the chip nav */}
      <div className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-canvas)_88%,transparent)] backdrop-blur">
        <div className="mx-auto max-w-[1760px] px-6">
          <div className="flex items-center justify-between gap-3 py-3.5">
            {/* identity: the ticker is the page's anchor — display-sized, mono */}
            <div className="flex items-baseline gap-3">
              <h1 className="tnum text-[22px] font-bold tracking-tight text-[var(--color-ink)]">{tk ?? "分析"}</h1>
              {date && <span className="text-[13px] text-[var(--color-ink-faint)] tnum">{date}</span>}
              {s.complete && <RatingBadge rating={s.rating} size="sm" />}
            </div>

            <div className="flex items-center gap-2">
              {(ordered.length > 0 || decisionMd) && (
                <>
                  <button onClick={onCopy} className="flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-ink-soft)] transition hover:border-[var(--color-border-strong)] hover:text-[var(--color-ink)]">
                    {copied ? <Check size={15} className="text-[var(--color-brand)]" /> : <Copy size={15} />}
                    {copied ? "已复制" : "复制"}
                  </button>
                  <button onClick={onDownload} className="flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-ink-soft)] transition hover:border-[var(--color-border-strong)] hover:text-[var(--color-ink)]">
                    <Download size={15} /> 下载
                  </button>
                  {s.complete && (
                    <button
                      onClick={onExportPdf}
                      disabled={pdfBusy}
                      title={pdfErr ?? "生成综合研报 PDF"}
                      className="flex items-center gap-1.5 rounded-[var(--radius-btn)] bg-[var(--color-brand)] px-3 py-1.5 text-sm font-medium text-white transition hover:brightness-105 disabled:opacity-60"
                    >
                      {pdfBusy ? <Loader2 size={15} className="animate-spin" /> : <FileText size={15} />}
                      {pdfBusy ? "生成中…" : "导出 PDF"}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* slim live progress bar while running (replaces the giant tree) */}
          {running && (
            <div className="pb-2.5">
              <div className="h-1 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
                <div
                  className="h-full rounded-full bg-[var(--color-brand)] transition-all duration-500"
                  style={{ width: `${Math.round((nodeDone / nodeTotal) * 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* dimension chip bar — narrow-screen fallback nav (the wide-screen
              layout uses the pipeline rail on the left instead) */}
          {ordered.length > 0 && (
            <div className="flex items-center gap-2 pb-2.5 lg:hidden">
              <div ref={chipsRef} className="flex flex-1 gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {ordered.map((sec) => (
                  <button
                    key={sec.key}
                    data-active={sec.key === activeKey}
                    onClick={() => pick(sec.key)}
                    className={cn(
                      "shrink-0 rounded-full px-3 py-1.5 text-sm transition",
                      sec.key === activeKey
                        ? "bg-[var(--color-brand)] font-medium text-white"
                        : "bg-[var(--color-surface-2)] text-[var(--color-ink-soft)] hover:text-[var(--color-ink)]",
                    )}
                  >
                    {label(sec.key)}
                  </button>
                ))}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  onClick={() => go(-1)}
                  disabled={idx <= 0}
                  className="grid h-7 w-7 place-items-center rounded-full border border-[var(--color-border)] text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)] disabled:opacity-40"
                >
                  <ChevronLeft size={15} />
                </button>
                <button
                  onClick={() => go(1)}
                  disabled={idx >= orderedKeys.length - 1}
                  className="grid h-7 w-7 place-items-center rounded-full border border-[var(--color-border)] text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)] disabled:opacity-40"
                >
                  <ChevronRight size={15} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* report body — two-column dashboard on wide screens:
          left = the active dimension (reading column), right = sticky overview
          (decision + price chart) so the horizontal space is actually used. */}
      <div className="mx-auto max-w-[1760px] px-6 py-6">
        {s.error && (
          <div className="mx-auto flex max-w-lg flex-col items-center gap-3 rounded-[var(--radius-card)] bg-[var(--color-surface)] p-8 text-center" style={{ boxShadow: "var(--shadow-card)" }}>
            <div className="grid h-12 w-12 place-items-center rounded-full bg-[var(--color-bear-tint)]">
              <AlertTriangle size={22} className="text-[var(--color-bear)]" />
            </div>
            <div className="font-semibold text-[var(--color-ink)]">分析未完成</div>
            <p className="text-sm text-[var(--color-ink-soft)]">{s.error}</p>
            {paramsRef.current && (
              <button
                onClick={onRetry}
                disabled={retrying}
                className="mt-1 flex items-center gap-2 rounded-[var(--radius-btn)] bg-[var(--color-brand)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-105 disabled:opacity-60"
              >
                {retrying ? <Loader2 size={15} className="animate-spin" /> : <RotateCw size={15} />}
                重新发起分析
              </button>
            )}
          </div>
        )}

        {ordered.length === 0 && !decisionMd && !s.error && (
          <div
            className="mx-auto max-w-md rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-10"
            style={{ boxShadow: "var(--shadow-card)" }}
          >
            <MascotScene
              pose="working"
              animation="float"
              size={180}
              title="分析师团队正在工作"
              body="Dromy 会跟随 19 节点流水线，把每阶段结论逐个呈现。"
            />
          </div>
        )}

        {(ordered.length > 0 || decisionMd) && (
          <div className="flex flex-col-reverse gap-6 lg:flex-row lg:items-start">
            {/* pipeline rail — the 19-node agent流水线 as the primary report
                nav: done nodes jump to their section, running node spins. */}
            <aside className="hidden w-56 shrink-0 lg:sticky lg:top-24 lg:block lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto lg:pr-2">
              <ProgressTree
                nodeStatus={s.nodeStatus}
                onPick={pickNode}
                activeKey={activeKey ? SECTION_TO_NODE[activeKey] : undefined}
              />
            </aside>

            {/* center: the single active dimension (primary reading column) */}
            {ordered.length > 0 && (
              <div id="stage-anchor" className="min-w-0 max-w-[840px] flex-1 space-y-2">
                <div className="flex items-baseline justify-between">
                  <div className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                    分项报告 · {idx + 1}/{orderedKeys.length}
                  </div>
                  <div className="hidden items-center gap-1 lg:flex">
                    <button
                      onClick={() => go(-1)}
                      disabled={idx <= 0}
                      aria-label="上一节"
                      className="grid h-7 w-7 place-items-center rounded-full border border-[var(--color-border)] text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)] disabled:opacity-40"
                    >
                      <ChevronLeft size={15} />
                    </button>
                    <button
                      onClick={() => go(1)}
                      disabled={idx >= orderedKeys.length - 1}
                      aria-label="下一节"
                      className="grid h-7 w-7 place-items-center rounded-full border border-[var(--color-border)] text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)] disabled:opacity-40"
                    >
                      <ChevronRight size={15} />
                    </button>
                  </div>
                </div>
                {activeKey && s.sections[activeKey] && (
                  <div key={activeKey} className="animate-pop">
                    <SectionBody sectionKey={activeKey} md={s.sections[activeKey]} />
                  </div>
                )}
              </div>
            )}

            {/* right: sticky intelligence rail — decision + price, always in view */}
            <div id="decision-anchor" className="space-y-4 lg:sticky lg:top-24 lg:w-[24rem] lg:shrink-0 xl:w-[26rem]">
              {decisionMd && (
                <DecisionCard decisionMd={decisionMd} rating={s.rating} />
              )}
              {tk && <PriceChart ticker={tk} date={date} />}
              {tk && <SizingPanel runId={runId} ticker={tk} date={date} />}
              {tk && <FactorPanel runId={runId} />}
              {tk && <ResearchPanel ticker={tk} date={date} />}
            </div>
          </div>
        )}
      </div>

      {s.complete && <QAPanel runId={runId} />}
    </div>
  );
}
