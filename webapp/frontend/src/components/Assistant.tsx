import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Bot, User, Wrench, AlertCircle, Square } from "lucide-react";
import { api } from "../api/client";
import { cn } from "../lib/format";
import { Markdown } from "./Markdown";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls?: ToolCall[];
}

interface ToolCall {
  name: string;
  args?: Record<string, unknown>;
  result?: string;
}

// 工具函数名 → 前端中文显示名（函数名是内部实现细节，不直接暴露给用户）
const TOOL_LABELS: Record<string, string> = {
  // 数据工具
  get_stock_data: "查询行情数据",
  get_news: "查询个股新闻",
  get_global_news: "查询宏观新闻",
  get_indicators: "计算技术指标",
  get_fundamentals: "查询基本面",
  get_insider_transactions: "查询内部人交易",
  get_macro_data: "查询宏观数据",
  get_prediction_markets: "查询预测市场",
  get_verified_market_snapshot: "获取市场快照",
  fetch_stocktwits: "查询散户情绪",
  fetch_reddit: "查询社区讨论",
  fetch_x_posts: "查询社媒讨论",
  // 板块工具
  list_sectors: "查看板块列表",
  get_sector_quote: "查询板块行情",
  get_capital_flow: "查询资金流向",
  get_sector_news: "查询板块新闻",
  // 分析工具
  run_deep_analysis: "深度分析",
  run_backtest: "历史回测",
  run_screener: "条件选股",
  run_hedge_analysis: "对冲分析",
  run_factor_analysis: "因子分析",
  run_sizing_analysis: "仓位分析",
  // 用户工具
  get_my_portfolio: "查询我的持仓",
  get_my_position: "查询个股持仓",
  analyze_my_operation: "复盘我的操作",
  // 联网核实
  resolve_ticker: "核实证券代码",
  web_search: "搜索最新信息",
  web_read: "阅读网页全文",
  // 监控
  create_monitor_rule: "创建监控规则",
  get_alerts: "查询预警记录",
};

const QUICK_QUESTIONS = [
  "存储板块见底了吗？",
  "资金会轮动到哪些板块？",
  "帮我分析一下 NVDA",
  "我该怎么操作 600519.SS？",
  "回测一下 0700.HK 去年表现",
  "帮我看看持仓风险",
];

export function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const stop = () => {
    abortRef.current?.abort();
  };

  const ask = async (question?: string) => {
    const q = (question || input).trim();
    if (!q || loading) return;

    setInput("");
    setError(null);
    setLoading(true);

    const userMsg: Message = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);

    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    // 每个会话一个 session_id：首次提问时生成，后端用它维护多轮上下文
    const sid = sessionId ?? crypto.randomUUID();
    if (!sessionId) setSessionId(sid);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const params = new URLSearchParams({ question: q, session_id: sid });

      const res = await fetch(`/api/assistant/ask?${params}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      if (!reader) throw new Error("No response body");

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        const frames = buf.split("\n\n");
        buf = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          try {
            const ev = JSON.parse(line.slice(5).trim());
            if (ev.type === "delta") {
              assistantMsg.content += ev.text;
              setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
            } else if (ev.type === "tool_start") {
              assistantMsg.toolCalls = [
                ...(assistantMsg.toolCalls ?? []),
                { name: ev.tool, args: ev.args },
              ];
              setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
            } else if (ev.type === "tool_end") {
              const tcs = assistantMsg.toolCalls ?? [];
              const pending = [...tcs].reverse().find((t) => t.name === ev.tool && !t.result);
              if (pending) pending.result = "done";
              setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
            } else if (ev.type === "cancelled") {
              assistantMsg.content += assistantMsg.content ? "\n\n_（已停止生成）_" : "_（已停止）_";
              setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
            } else if (ev.type === "done") {
              if (ev.session_id) setSessionId(ev.session_id);
            } else if (ev.type === "error") {
              setError(ev.message);
            }
          } catch {
            /* ignore malformed frame */
          }
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // 用户主动停止：保留已生成的内容，追加停止标记
        assistantMsg.content += assistantMsg.content ? "\n\n_（已停止生成）_" : "_（已停止）_";
        setMessages((prev) => [...prev.slice(0, -1), { ...assistantMsg }]);
      } else {
        setError(e instanceof Error ? e.message : "请求失败");
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "assistant", content: "抱歉，我遇到了技术问题，请稍后再试。" },
        ]);
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  const newChat = () => {
    // 新对话：中断当前任务 + 清屏 + 新 session（旧上下文在后端清掉）
    stop();
    if (sessionId) {
      api.assistantClear?.(sessionId).catch(() => {});
    }
    setMessages([]);
    setSessionId(null);
    setError(null);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[var(--color-canvas)]">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
            <Bot size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[var(--color-ink)]">投研助手</h1>
            <p className="text-xs text-[var(--color-ink-faint)]">问我任何投研问题，我会调用工具帮你分析</p>
          </div>
        </div>
        <button
          onClick={newChat}
          className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-sm text-[var(--color-ink-soft)] transition hover:bg-[var(--color-surface-2)]"
        >
          新对话
        </button>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="mx-auto max-w-2xl">
            <div className="mb-6 text-center">
              <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
                <Bot size={32} />
              </div>
              <h2 className="text-xl font-bold text-[var(--color-ink)]">你好，我是 DromX 投研助手</h2>
              <p className="mt-2 text-sm text-[var(--color-ink-soft)]">
                我可以帮你分析板块趋势、资金流向、个股诊断、操作复盘等问题
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-left text-sm text-[var(--color-ink)] transition hover:border-[var(--color-brand)]/40 hover:bg-[var(--color-brand-tint)]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-4">
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-[var(--color-ink-faint)]">
              <Loader2 size={16} className="animate-spin" />
              正在思考...
              <button
                onClick={stop}
                className="ml-2 flex items-center gap-1 rounded-[var(--radius-control)] border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-ink-soft)] transition hover:bg-[var(--color-surface-2)]"
              >
                <Square size={10} />
                停止
              </button>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 rounded-[var(--radius-control)] border border-[var(--color-danger)]/30 bg-[var(--color-danger-tint)] px-3 py-2 text-sm text-[var(--color-danger)]">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-canvas)] px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
              placeholder="问我任何投研问题，比如：存储板块见底了吗？"
              disabled={loading}
              className="flex-1 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-ink)] outline-none transition placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-brand)] disabled:opacity-50"
            />
            <button
              onClick={() => (loading ? stop() : ask())}
              disabled={!loading && !input.trim()}
              className="btn-brand flex h-11 w-11 items-center justify-center rounded-[var(--radius-control)] disabled:opacity-50"
              aria-label={loading ? "停止" : "发送"}
            >
              {loading ? <Square size={16} /> : <Send size={18} />}
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-[var(--color-ink-faint)]">
            投研助手会调用工具获取数据，回答仅供参考，不构成投资建议
          </p>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
          <Bot size={16} />
        </div>
      )}
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-[var(--color-brand)] text-white"
            : "bg-[var(--color-surface)] text-[var(--color-ink)]",
        )}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="space-y-2">
            {/* 工具调用发生在思考阶段，展示在回答上方 */}
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-border)] pb-2">
                {message.toolCalls.map((tool, i) => (
                  <ToolCallBadge key={i} tool={tool} />
                ))}
              </div>
            )}
            {message.content && <Markdown>{message.content}</Markdown>}
          </div>
        )}
      </div>
      {isUser && (
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--color-surface-2)] text-[var(--color-ink-soft)]">
          <User size={16} />
        </div>
      )}
    </div>
  );
}

function ToolCallBadge({ tool }: { tool: ToolCall }) {
  return (
    <div className="flex items-center gap-1.5 rounded-md bg-[var(--color-surface-2)] px-2 py-1 text-xs text-[var(--color-ink-soft)]">
      <Wrench size={12} />
      <span className="font-medium">{TOOL_LABELS[tool.name] ?? tool.name}</span>
      {tool.result && <span className="text-[var(--color-ink-faint)]">✓</span>}
    </div>
  );
}
