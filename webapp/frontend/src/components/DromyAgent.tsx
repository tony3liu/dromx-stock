import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { Mascot, type MascotPose, type MascotAnimation } from "./Mascot";
import { NODE_CN } from "../lib/nodes";
import { decisionPose } from "../lib/mascot";
import type { NodeStatus } from "../hooks/useRunStream";
import { cn } from "../lib/format";

const NODE_MESSAGES: Record<string, string> = {
  "Regime Analyst": "先看整体市场环境…",
  "Market Analyst": "K 线形态扫描中…",
  "Sentiment Analyst": "多空情绪正在读取…",
  "News Analyst": "翻一下新闻和宏观…",
  "Fundamentals Analyst": "基本面数据核对中…",
  "Industry Analyst": "产业链上下游看看…",
  "Signal Aggregator": "把各维度信号揉起来…",
  "Event Impact": "评估事件冲击…",
  "Key Question": "提炼关键问题…",
  "Growth Analyst": "增长质量打分…",
  "Risk Analyst": "估值风险检查…",
  "Research Manager": "研究经理写结论…",
  Trader: "交易员做方案…",
  "Reward Specialist": "算收益风险比…",
  "Tail Risk Specialist": "尾部风险再筛一遍…",
  "Regime Risk Specialist": "环境风险复核…",
  "Risk Consensus": "风险共识汇总…",
  "Forecast Synthesizer": "时间轴预测生成中…",
  "Portfolio Manager": "最终决策出炉中…",
};

const THINKING_NODES = new Set([
  "Signal Aggregator",
  "Event Impact",
  "Key Question",
  "Growth Analyst",
  "Risk Analyst",
  "Research Manager",
  "Trader",
  "Reward Specialist",
  "Tail Risk Specialist",
  "Regime Risk Specialist",
  "Risk Consensus",
  "Forecast Synthesizer",
  "Portfolio Manager",
]);

function getPose(
  runningNode: string | null,
  complete: boolean,
  error: string | null,
  rating?: string | null,
): MascotPose {
  if (error) return "thinking";
  if (complete) {
    if (rating) return decisionPose(rating);
    return "celebrating";
  }
  if (runningNode && THINKING_NODES.has(runningNode)) return "thinking";
  return "working";
}

interface DromyAgentProps {
  nodeStatus: Record<string, NodeStatus>;
  running: boolean;
  complete: boolean;
  error: string | null;
  rating?: string | null;
}

/** Dromy — 会动的小浣熊分析师助手。
 *
 * 在分析过程中从右下角冒出来，根据当前运行的节点切换表情和文案，
 * 分析完成后根据评级庆祝一会儿，然后自动消失。支持点击关闭。
 */
export function DromyAgent({ nodeStatus, running, complete, error, rating }: DromyAgentProps) {
  const [dismissed, setDismissed] = useState(false);
  const [autoHidden, setAutoHidden] = useState(false);

  // 分析完成后自动庆祝 4 秒，然后消失
  useEffect(() => {
    if (!running && complete) {
      const t = setTimeout(() => setAutoHidden(true), 4000);
      return () => clearTimeout(t);
    }
  }, [running, complete]);

  const runningNode = useMemo(
    () => Object.entries(nodeStatus).find(([, s]) => s === "running")?.[0] ?? null,
    [nodeStatus],
  );

  const total = Object.keys(nodeStatus).length || 19;
  const done = Object.values(nodeStatus).filter((s) => s === "done").length;

  const pose = useMemo(
    () => getPose(runningNode, complete, error, rating),
    [runningNode, complete, error, rating],
  );

  const animation: MascotAnimation = complete ? "bob" : "float";

  const message = useMemo(() => {
    if (error) return "分析遇到点问题，Dromy 在复盘…";
    if (complete) return "分析完成！Dromy 已整理好报告 🎉";
    if (!runningNode) return "Dromy 正在召集分析师团队…";
    return NODE_MESSAGES[runningNode] ?? `${NODE_CN[runningNode] ?? runningNode}中…`;
  }, [error, complete, runningNode]);

  if (dismissed || autoHidden || (!running && !complete)) return null;

  return (
    <div
      className={cn(
        "fixed bottom-5 right-5 z-40 flex flex-col items-end gap-2",
        "md:flex-row md:items-end md:gap-3",
        "animate-agent-wander",
      )}
      role="status"
      aria-live="polite"
    >
      <div
        className={cn(
          "animate-bubble-pop relative max-w-[220px] rounded-2xl border border-[var(--color-border)]",
          "bg-[var(--color-surface)] px-4 py-3 shadow-[var(--shadow-pop)]",
        )}
      >
        <button
          onClick={() => setDismissed(true)}
          className="absolute -top-2 -right-2 grid h-5 w-5 place-items-center rounded-full bg-[var(--color-surface-2)] text-[var(--color-ink-faint)] transition hover:text-[var(--color-ink)]"
          aria-label="收起 Dromy"
        >
          <X size={10} />
        </button>
        <p className="text-sm font-medium text-[var(--color-ink)]">{message}</p>
        {running && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-[var(--color-ink-soft)]">
            <span
              className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--color-brand)]"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--color-brand)]"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--color-brand)]"
              style={{ animationDelay: "300ms" }}
            />
            <span className="ml-1 tnum">
              {done}/{total}
            </span>
          </div>
        )}
      </div>
      <Mascot pose={pose} animation={animation} size={120} className="drop-shadow-[0_16px_40px_rgba(1,4,9,0.6)]" />
    </div>
  );
}
