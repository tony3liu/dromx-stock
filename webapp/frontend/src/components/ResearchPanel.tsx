import { useState } from "react";
import { ExternalLink, LineChart, CalendarClock, Sparkles, Copy, Check } from "lucide-react";
import { googleFinanceLinks } from "../lib/googleFinance";
import { copyText } from "../lib/export";

// Google Finance research panel (PRD §4.3, P0). No scraping / no API: we hand the
// user the right deep links for this ticker plus a ready-to-paste prompt for
// Google Finance's own AI research panel. Complements DromX' analysis
// with realtime data + Gemini research the engine doesn't fetch itself.
export function ResearchPanel({ ticker, date }: { ticker: string; date?: string }) {
  const [copied, setCopied] = useState(false);
  const gf = googleFinanceLinks(ticker, date);

  const copyPrompt = async () => {
    if (await copyText(gf.aiPrompt)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const links = [
    { href: gf.quote, icon: LineChart, label: "实时行情 / 估值", hint: gf.symbol },
    { href: gf.earnings, icon: CalendarClock, label: "走势 / 财报窗口", hint: "近 6 个月" },
  ];

  return (
    <section
      className="rounded-[var(--radius-card)] bg-[var(--color-surface)] p-5"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-1 flex items-center gap-2">
        <Sparkles size={15} className="text-[var(--color-brand-dark)]" />
        <h2 className="text-sm font-bold text-[var(--color-ink)]">Google Finance 研究</h2>
      </div>
      <p className="mb-3 text-xs text-[var(--color-ink-faint)]">
        用 Google Finance 的实时数据与 Gemini 研究面板补充本次分析。
      </p>

      <div className="space-y-1.5">
        {links.map((l) => (
          <a
            key={l.label}
            href={l.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 rounded-xl border border-[var(--color-border)] px-3 py-2 transition hover:border-[var(--color-brand)] hover:bg-[var(--color-brand-tint)]"
          >
            <l.icon size={16} className="shrink-0 text-[var(--color-brand-dark)]" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-[var(--color-ink)]">{l.label}</div>
              <div className="truncate text-xs text-[var(--color-ink-faint)] tnum">{l.hint}</div>
            </div>
            <ExternalLink size={13} className="shrink-0 text-[var(--color-ink-faint)]" />
          </a>
        ))}
      </div>

      <button
        onClick={copyPrompt}
        className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-[var(--color-border-strong)] px-3 py-2 text-sm font-medium text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)]"
        title="复制后粘贴到 Google Finance 的 AI 研究面板"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
        {copied ? "已复制 AI 提示词" : "复制 AI 研究提示词"}
      </button>
    </section>
  );
}
