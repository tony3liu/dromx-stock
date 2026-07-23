import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, Loader2 } from "lucide-react";
import { api } from "../api/client";
import type { MonitorRule, RuleType, RuleScope, RuleSeverity, RuleCondition } from "../api/types";
import { cn } from "../lib/format";
import { Input } from "./ui/Input";

// Threshold-comparable fields (subset of monitor_rules.ALLOWED_FIELDS, the ones
// worth exposing in a simple UI). Others still work if typed, but these cover it.
const THRESHOLD_FIELDS = [
  "change_pct", "close", "turnover_rate", "vol_ratio_5d", "rsi_14",
  "momentum_20d", "amount", "ma20", "ma60", "change_60d",
];
const SIGNAL_FIELDS = [
  "signal_ma_golden_5_20", "signal_macd_golden", "signal_ma20_breakout",
  "signal_n_day_high", "signal_boll_breakout_upper", "signal_volume_surge",
];
const OPS = [">", ">=", "<", "<=", "==", "!="];

const emptyRule = (): MonitorRule => ({
  id: "", name: "", type: "price", scope: "symbols", symbols: [], market: "hk",
  strategy_id: null, direction: "entry", conditions: [{ field: "change_pct", op: ">", value: 0.05 }],
  logic: "and", cooldown_seconds: 3600, severity: "info", message: "", enabled: true,
});

export function RuleEditor({ initial, strategies, onSaved, onCancel }: {
  initial?: MonitorRule;
  strategies: { id: string; name: string }[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const editing = !!initial;
  const [r, setR] = useState<MonitorRule>(initial ? { ...initial } : emptyRule());
  const [symbolsText, setSymbolsText] = useState((initial?.symbols ?? []).join(", "));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef(onCancel);
  cancelRef.current = onCancel;

  // Dialog behaviour: Escape closes, focus moves into the panel on open and is
  // returned to the previously focused element on close.
  useEffect(() => {
    const prev = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    panelRef.current?.querySelector<HTMLElement>("input, select, button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") cancelRef.current();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, []);

  const set = <K extends keyof MonitorRule>(k: K, v: MonitorRule[K]) => setR((p) => ({ ...p, [k]: v }));

  const setCond = (i: number, patch: Partial<RuleCondition>) =>
    setR((p) => ({ ...p, conditions: p.conditions.map((c, j) => (j === i ? { ...c, ...patch } : c)) }));
  const addCond = () => setR((p) => ({ ...p, conditions: [...p.conditions, { field: "change_pct", op: ">", value: 0 }] }));
  const rmCond = (i: number) => setR((p) => ({ ...p, conditions: p.conditions.filter((_, j) => j !== i) }));

  const save = async () => {
    setErr(null);
    const symbols = symbolsText.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean);
    const payload: MonitorRule = { ...r, symbols };
    setSaving(true);
    try {
      if (editing) await api.updateRule(r.id, payload);
      else await api.createRule(payload);
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "保存失败");
      setSaving(false);
    }
  };

  const inputCls = "w-full rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-ink)] outline-none focus:border-[var(--color-brand)]";
  const selCls = inputCls + " sel";

  /* Portal to <body> so `fixed` is always viewport-relative, even if an
     ancestor route container carries a transform-based entry animation. */
  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4 backdrop-blur-[2px]" onClick={onCancel}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={editing ? "编辑规则" : "新建监控规则"}
        className="max-h-[90vh] w-full max-w-[560px] overflow-y-auto rounded-[var(--radius-card)] bg-[var(--color-surface)] p-5"
        style={{ boxShadow: "var(--shadow-pop)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[17px] font-semibold tracking-tight text-[var(--color-ink)]">{editing ? "编辑规则" : "新建监控规则"}</h2>
          <button onClick={onCancel} aria-label="关闭" className="text-[var(--color-ink-faint)] hover:text-[var(--color-ink)]"><X size={20} /></button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">规则 ID</label>
              <Input value={r.id} disabled={editing} onChange={(e) => set("id", e.target.value)}
                placeholder="如 r_hk_bigmove" className={editing ? "opacity-60" : undefined} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">名称</label>
              <Input value={r.name} onChange={(e) => set("name", e.target.value)} placeholder="港股大涨提醒" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">类型</label>
              <select value={r.type} onChange={(e) => set("type", e.target.value as RuleType)} className={selCls}>
                <option value="price">价格阈值</option>
                <option value="signal">技术信号</option>
                <option value="strategy">策略选股池</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">范围</label>
              <select value={r.scope} onChange={(e) => set("scope", e.target.value as RuleScope)} className={selCls}>
                <option value="symbols">指定标的</option>
                <option value="all">全市场</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">冷却(秒)</label>
              <Input type="number" value={r.cooldown_seconds} onChange={(e) => set("cooldown_seconds", Number(e.target.value))} />
            </div>
          </div>

          {r.scope === "symbols" && (
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">标的代码（逗号分隔）</label>
              <Input value={symbolsText} onChange={(e) => setSymbolsText(e.target.value)} placeholder="00700.HK, 09988.HK" />
            </div>
          )}

          {r.type === "strategy" ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">策略</label>
                <select value={r.strategy_id ?? ""} onChange={(e) => set("strategy_id", e.target.value)} className={selCls}>
                  <option value="">选择策略…</option>
                  {strategies.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">方向</label>
                <select value={r.direction} onChange={(e) => set("direction", e.target.value as MonitorRule["direction"])} className={selCls}>
                  <option value="entry">新入选</option>
                  <option value="exit">移出</option>
                  <option value="both">入选+移出</option>
                </select>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-1 flex items-center justify-between">
                <label className="text-xs font-semibold text-[var(--color-ink-faint)]">条件</label>
                <select value={r.logic} onChange={(e) => set("logic", e.target.value as "and" | "or")}
                  className="sel rounded-lg border border-[var(--color-border)] py-0.5 pl-2 text-xs">
                  <option value="and">全部满足 (AND)</option>
                  <option value="or">任一满足 (OR)</option>
                </select>
              </div>
              <div className="space-y-2">
                {r.conditions.map((c, i) => {
                  const isSignal = r.type === "signal";
                  return (
                    <div key={i} className="flex items-center gap-2">
                      <select value={c.field} onChange={(e) => setCond(i, { field: e.target.value })}
                        className={cn(selCls, "flex-1")}>
                        {(isSignal ? SIGNAL_FIELDS : THRESHOLD_FIELDS).map((f) => <option key={f} value={f}>{f}</option>)}
                      </select>
                      {isSignal ? (
                        <span className="text-xs text-[var(--color-ink-faint)]">为真</span>
                      ) : (
                        <>
                          <select value={c.op} onChange={(e) => setCond(i, { op: e.target.value })}
                            className="sel rounded-[var(--radius-control)] border border-[var(--color-border)] py-2 pl-2 text-sm">
                            {OPS.map((o) => <option key={o} value={o}>{o}</option>)}
                          </select>
                          <Input type="number" step="any" value={c.value ?? 0} fullWidth={false}
                            onChange={(e) => setCond(i, { value: Number(e.target.value) })}
                            className="w-24" />
                        </>
                      )}
                      {r.conditions.length > 1 && (
                        <button onClick={() => rmCond(i)} aria-label="删除条件" className="text-[var(--color-ink-faint)] hover:text-[var(--color-bear)]"><X size={16} /></button>
                      )}
                    </div>
                  );
                })}
              </div>
              <button onClick={addCond} className="mt-2 text-xs font-medium text-[var(--color-brand-dark)] hover:underline">+ 添加条件</button>
              {r.type === "signal" && (
                <p className="mt-1 text-xs text-[var(--color-ink-faint)]">提示：价格阈值用小数（0.05 = 5%）。</p>
              )}
              {r.type === "price" && (
                <p className="mt-1 text-xs text-[var(--color-ink-faint)]">提示：涨跌幅/换手等为小数（0.05 = 5%）。</p>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">市场</label>
              <select value={r.market} onChange={(e) => set("market", e.target.value)} className={selCls}>
                <option value="hk">港股</option>
                <option value="us">美股</option>
                <option value="cn">A股</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--color-ink-faint)]">级别</label>
              <select value={r.severity} onChange={(e) => set("severity", e.target.value as RuleSeverity)} className={selCls}>
                <option value="info">info</option>
                <option value="warn">warn</option>
                <option value="critical">critical</option>
              </select>
            </div>
          </div>
        </div>

        {err && <div className="mt-3 rounded-lg bg-[var(--color-bear-tint)] p-2.5 text-sm text-[var(--color-bear)]">{err}</div>}

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onCancel} className="rounded-[var(--radius-control)] border border-[var(--color-border)] px-4 py-2 text-sm font-medium text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]">取消</button>
          <button onClick={save} disabled={saving}
            className="btn-brand flex items-center gap-2 rounded-[var(--radius-control)] px-5 py-2 text-sm font-semibold disabled:opacity-50">
            {saving && <Loader2 size={15} className="animate-spin" />} 保存
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
