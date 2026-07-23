import { Check, Loader2 } from "lucide-react";
import { cn } from "../lib/format";
import type { NodeStatus } from "../hooks/useRunStream";

// Pipeline nodes grouped by team for a readable progress tree.
const GROUPS: { team: string; nodes: string[] }[] = [
  { team: "Regime", nodes: ["Regime Analyst"] },
  {
    team: "Analyst Team",
    nodes: ["Market Analyst", "Sentiment Analyst", "News Analyst", "Fundamentals Analyst", "Industry Analyst"],
  },
  { team: "Signal & Triage", nodes: ["Signal Aggregator", "Event Impact", "Key Question"] },
  { team: "Research", nodes: ["Growth Analyst", "Risk Analyst", "Research Manager"] },
  { team: "Trading", nodes: ["Trader"] },
  { team: "Risk", nodes: ["Reward Specialist", "Tail Risk Specialist", "Regime Risk Specialist", "Risk Consensus"] },
  { team: "Forecast & Decision", nodes: ["Forecast Synthesizer", "Portfolio Manager"] },
];

const NODE_CN: Record<string, string> = {
  "Regime Analyst": "市场状态",
  "Market Analyst": "技术面",
  "Sentiment Analyst": "情绪面",
  "News Analyst": "新闻宏观",
  "Fundamentals Analyst": "基本面",
  "Industry Analyst": "行业链",
  "Signal Aggregator": "信号融合",
  "Event Impact": "事件冲击",
  "Key Question": "关键问题",
  "Growth Analyst": "增长质量",
  "Risk Analyst": "估值风险",
  "Research Manager": "研究综合",
  Trader: "交易方案",
  "Reward Specialist": "收益专家",
  "Tail Risk Specialist": "尾部风险",
  "Regime Risk Specialist": "环境风险",
  "Risk Consensus": "风险共识",
  "Forecast Synthesizer": "时间轴预测",
  "Portfolio Manager": "最终决策",
};

function Dot({ status }: { status: NodeStatus }) {
  if (status === "done")
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-[var(--color-brand)] text-white animate-pop">
        <Check size={12} strokeWidth={3} />
      </span>
    );
  if (status === "running")
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)] pulse-brand">
        <Loader2 size={12} className="animate-spin" />
      </span>
    );
  return <span className="h-5 w-5 rounded-full border-2 border-[var(--color-border-strong)]" />;
}

export function ProgressTree({
  nodeStatus,
  onPick,
  activeKey,
}: {
  nodeStatus: Record<string, NodeStatus>;
  onPick?: (node: string) => void;
  activeKey?: string;
}) {
  const total = Object.keys(nodeStatus).length || 19;
  const done = Object.values(nodeStatus).filter((s) => s === "done").length;
  const pct = Math.round((done / total) * 100);

  return (
    <div className="space-y-5">
      <div>
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="font-semibold text-[var(--color-ink)]">分析进度</span>
          <span className="tnum text-[var(--color-ink-soft)]">
            {done}/{total} · {pct}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-surface-2)]">
          <div
            className="h-full rounded-full bg-[var(--color-brand)] transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="space-y-4">
        {GROUPS.map((g) => {
          const present = g.nodes.filter((n) => n in nodeStatus);
          if (!present.length) return null;
          return (
            <div key={g.team}>
              <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                {g.team}
              </div>
              <div className="space-y-1">
                {present.map((n) => {
                  const status = nodeStatus[n];
                  const clickable = status === "done" && onPick;
                  return (
                    <button
                      key={n}
                      disabled={!clickable}
                      onClick={() => clickable && onPick?.(n)}
                      className={cn(
                        "flex w-full items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-left transition",
                        clickable && "hover:bg-[var(--color-surface-2)] cursor-pointer",
                        activeKey === n && "bg-[var(--color-brand-tint)]",
                      )}
                    >
                      <Dot status={status} />
                      <span
                        className={cn(
                          "text-sm",
                          status === "pending" ? "text-[var(--color-ink-faint)]" : "text-[var(--color-ink)]",
                          status === "running" && "font-medium",
                        )}
                      >
                        {NODE_CN[n] ?? n}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
