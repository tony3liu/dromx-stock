import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { Send, MessageCircleQuestion, Loader2, X } from "lucide-react";
import { api } from "../api/client";
import { Markdown } from "./Markdown";
import { cn } from "../lib/format";
import mascot from "../assets/brand/mascot.png";

interface Turn {
  q: string;
  a: string | null; // null while loading
}

const QUICK = ["为什么是这个评级？", "止损是怎么算出来的？", "如果标的涨5%会到多少？", "最大的风险是什么？"];

/** Report-grounded Q&A. Floating drawer: a FAB when closed, a right-side
 *  overlay drawer when open — no longer a fixed 4th column. */
export function QAPanel({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    /* Scroll the message list directly instead of endRef.scrollIntoView():
       scrollIntoView walks every scrollable ancestor — including the
       off-canvas drawer's overflow-hidden wrapper (programmatically
       scrollable despite overflow:hidden) — and dragged the closed drawer
       back into view from the right edge. */
    const c = listRef.current;
    if (c) c.scrollTo({ top: c.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  // Dialog behaviour: Escape closes; focus moves into the drawer on open and
  // back to the element that opened it on close.
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, [open]);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    const history: [string, string][] = turns
      .filter((t) => t.a)
      .map((t) => [t.q, t.a as string]);
    // Add the question with an empty (non-null) answer so deltas append live.
    setTurns((prev) => [...prev, { q, a: "" }]);
    try {
      let any = false;
      await api.askStream(runId, q, history, (delta) => {
        any = true;
        setTurns((prev) =>
          prev.map((t, i) => (i === prev.length - 1 ? { ...t, a: (t.a ?? "") + delta } : t)),
        );
      });
      if (!any) {
        setTurns((prev) =>
          prev.map((t, i) => (i === prev.length - 1 ? { ...t, a: "（无内容）" } : t)),
        );
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "回答失败";
      setTurns((prev) => prev.map((t, i) => (i === prev.length - 1 ? { ...t, a: `（出错：${msg}）` } : t)));
    } finally {
      setBusy(false);
    }
  };

  /* Portal to <body>: the workbench route uses transform-based entry
     animations, and any transformed ancestor would turn this drawer's
     `fixed` positioning relative to that ancestor instead of the viewport —
     which is what made the "closed" drawer peek in from the right edge. */
  return createPortal(
    <>
      {/* Floating action button (always present so it can re-open the drawer) */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="btn-brand fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full px-4 py-3 font-semibold"
        >
          <MessageCircleQuestion size={18} /> 追问
        </button>
      )}

      {/* Scrim + slide-in drawer. overflow-hidden on the fixed wrapper clips the
          off-canvas drawer — otherwise its translated box spills past the
          viewport edge, becomes scrollable overflow on <main>, and scrollIntoView
          anywhere on the page can drag the whole workbench left off-canvas. */}
      <div
        className={cn(
          "fixed inset-0 z-40 overflow-hidden transition",
          open ? "pointer-events-auto" : "pointer-events-none",
        )}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={cn(
            "absolute inset-0 bg-black/50 backdrop-blur-[2px] transition-opacity duration-300",
            open ? "opacity-100" : "opacity-0",
          )}
        />
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="报告追问"
          className="absolute right-0 top-0 flex h-full w-[24rem] max-w-[90vw] flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl transition-transform duration-300 ease-out"
          /* Inline transform, not translate-x-* classes: the Tailwind v4
             translate utility proved unreliable here (drawer stayed visible
             when closed), so the open/closed offset is set directly. */
          style={{ transform: open ? "translateX(0)" : "translateX(100%)" }}
        >
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
            <div className="flex items-center gap-2.5 font-semibold text-[var(--color-ink)]">
              <img src={mascot} alt="Dromy" className="h-8 w-8 rounded-full bg-[var(--color-surface-2)] object-cover ring-1 ring-[var(--color-border)]" />
              报告追问
              <span className="rounded-full bg-[var(--color-brand-tint)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-brand-dark)]">Dromy AI</span>
            </div>
            <button onClick={() => setOpen(false)} aria-label="关闭追问面板" className="text-[var(--color-ink-faint)] hover:text-[var(--color-ink)]">
              <X size={18} />
            </button>
          </div>

          <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto p-4">
            {turns.length === 0 && (
              <div className="space-y-3">
                <div className="flex flex-col items-center pt-6 pb-2 text-center">
                  <img src={mascot} alt="DromX 吉祥物 Dromy" className="animate-float h-28 w-auto drop-shadow-[0_8px_24px_rgba(16,185,129,0.15)]" />
                  <p className="mt-3 text-sm font-medium text-[var(--color-ink)]">我是 Dromy，你的 AI 投研助手</p>
                  <p className="mt-1 max-w-[26ch] text-xs leading-relaxed text-[var(--color-ink-soft)]">
                    基于本次分析提问，我会引用报告中的具体数字作答（不会重新跑分析）。
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {QUICK.map((q) => (
                    <button
                      key={q}
                      onClick={() => ask(q)}
                      className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1.5 text-xs text-[var(--color-ink-soft)] transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand-dark)]"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((t, i) => (
              <div key={i} className="space-y-2">
                <div className="ml-6 rounded-2xl rounded-tr-sm bg-[var(--color-brand)] px-3.5 py-2 text-sm text-white">
                  {t.q}
                </div>
                <div className="mr-6 rounded-2xl rounded-tl-sm bg-[var(--color-surface-2)] px-3.5 py-2 text-sm">
                  {!t.a ? (
                    <span className="flex items-center gap-2 text-[var(--color-ink-faint)]">
                      <Loader2 size={14} className="animate-spin" /> 思考中…
                    </span>
                  ) : (
                    <Markdown>{t.a}</Markdown>
                  )}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <div className="border-t border-[var(--color-border)] p-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    ask(input);
                  }
                }}
                rows={1}
                placeholder="输入问题，回车发送…"
                className="max-h-28 flex-1 resize-none rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-sm text-[var(--color-ink)] outline-none placeholder:text-[var(--color-ink-faint)] focus:border-[var(--color-brand)]"
              />
              <button
                onClick={() => ask(input)}
                disabled={busy || !input.trim()}
                aria-label="发送问题"
                className={cn(
                  "grid h-9 w-9 shrink-0 place-items-center rounded-[var(--radius-btn)] text-white transition",
                  busy || !input.trim() ? "bg-[var(--color-border-strong)]" : "btn-brand",
                )}
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </>,
    document.body,
  );
}
