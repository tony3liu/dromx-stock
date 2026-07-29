import { useCallback, useEffect, useState } from "react";
import { Bell, Plus, Pencil, Trash2, Loader2, AlertTriangle } from "lucide-react";
import { api } from "../api/client";
import type { MonitorRule, AlertEvent, RuleSeverity } from "../api/types";
import { RuleEditor } from "./RuleEditor";
import { PageHeader } from "./PageHeader";
import { cn } from "../lib/format";

const TYPE_CN: Record<string, string> = { price: "价格阈值", signal: "技术信号", strategy: "策略池" };

function sevColor(s: RuleSeverity): string {
  if (s === "critical") return "var(--color-danger)";
  if (s === "warn") return "var(--color-warn)";
  return "var(--color-brand-dark)";
}

export function Monitor() {
  const [rules, setRules] = useState<MonitorRule[]>([]);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [strategies, setStrategies] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<MonitorRule | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const loadRules = useCallback(() => {
    api.monitorRules().then((r) => setRules(r.rules)).catch((e) => setErr(e instanceof Error ? e.message : "加载规则失败"));
  }, []);

  const loadAlerts = useCallback(() => {
    api.alerts(100).then((r) => setAlerts(r.alerts)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.monitorRules().then((r) => setRules(r.rules)),
      api.alerts(100).then((r) => setAlerts(r.alerts)),
      api.strategies("hk").then((r) => setStrategies(r.strategies.map((s) => ({ id: s.id, name: s.name })))).catch(() => {}),
    ]).catch((e) => setErr(e instanceof Error ? e.message : "加载失败")).finally(() => setLoading(false));
  }, []);

  // Poll alerts every 15s (monitoring is a polling model — no SSE).
  useEffect(() => {
    const t = setInterval(loadAlerts, 15000);
    return () => clearInterval(t);
  }, [loadAlerts]);

  const toggleEnabled = async (rule: MonitorRule) => {
    try {
      await api.updateRule(rule.id, { ...rule, enabled: !rule.enabled });
      loadRules();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "更新失败");
    }
  };

  const del = async (id: string) => {
    try {
      await api.deleteRule(id);
      setConfirmId(null);
      loadRules();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "删除失败");
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        icon={<Bell size={18} />}
        title="监控中心"
        subtitle="价格 / 信号 / 策略池规则轮询触发告警"
        actions={
          <button
            onClick={() => { setEditing(null); setShowEditor(true); }}
            className="btn-brand flex items-center gap-2 rounded-[var(--radius-control)] px-4 py-1.5 text-sm font-semibold"
          >
            <Plus size={15} /> 新建规则
          </button>
        }
      />

      <div className="mx-auto max-w-[1180px] px-8 py-6">
        <div className="mb-5 flex items-start gap-2 rounded-[var(--radius-panel)] border border-[var(--color-warn-border)] bg-[var(--color-warn-tint)] px-3.5 py-2.5 text-[13px] text-[var(--color-ink-soft)]">
          <AlertTriangle size={15} className="mt-0.5 shrink-0 text-[var(--color-warn)]" />
          <span>监控由后端定时轮询驱动，需以 <code className="rounded bg-[var(--color-warn-border)] px-1 font-mono text-[12px]">DROMX_MONITOR_ENABLED=true</code> 启动服务后才会自动评估规则。规则在此随时增改，下一轮轮询即生效。</span>
        </div>

        {err && <div className="mb-4 rounded-[var(--radius-panel)] border border-[var(--color-danger)]/30 bg-[var(--color-danger-tint)] px-4 py-3 text-sm text-[var(--color-danger)]">{err}</div>}

        {loading ? (
          <div className="flex items-center gap-2 py-16 text-sm text-[var(--color-ink-faint)]"><Loader2 size={16} className="animate-spin" /> 加载中…</div>
        ) : (
          <div className="grid gap-x-8 gap-y-6 lg:grid-cols-2">
            {/* rules */}
            <div>
              <div className="mb-2 flex items-baseline gap-2 border-b border-[var(--color-border)] pb-2">
                <span className="text-[13px] font-semibold uppercase tracking-wider text-[var(--color-ink-faint)]">规则</span>
                <span className="tnum text-xs text-[var(--color-ink-faint)]">{rules.length}</span>
              </div>
              {rules.length === 0 && (
                <div className="flex flex-col items-center gap-3 py-12 text-center">
                  <span className="grid h-11 w-11 place-items-center rounded-full bg-[var(--color-brand-tint)] text-[var(--color-brand-dark)]">
                    <Bell size={18} />
                  </span>
                  <div className="text-sm font-medium text-[var(--color-ink)]">还没有监控规则</div>
                  <p className="max-w-[36ch] text-xs leading-relaxed text-[var(--color-ink-faint)]">
                    设定价格、信号或策略池规则，后端轮询命中后自动推送告警。
                  </p>
                  <button
                    onClick={() => { setEditing(null); setShowEditor(true); }}
                    className="btn-brand mt-1 flex items-center gap-1.5 rounded-[var(--radius-control)] px-3.5 py-1.5 text-[13px] font-semibold"
                  >
                    <Plus size={14} /> 新建第一条规则
                  </button>
                </div>
              )}
              <div className="divide-y divide-[var(--color-border)]">
                {rules.map((rule) => (
                  <div key={rule.id} className="group flex items-center justify-between gap-2 py-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-[var(--color-ink)]">{rule.name}</span>
                        <span className="rounded-[5px] bg-[var(--color-surface-2)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--color-ink-faint)]">{TYPE_CN[rule.type] ?? rule.type}</span>
                      </div>
                      <div className="mt-0.5 truncate font-mono text-[12px] text-[var(--color-ink-faint)]">
                        {rule.scope === "all" ? "全市场" : rule.symbols.join(", ")}
                        {rule.type === "strategy" && rule.strategy_id ? ` · ${rule.strategy_id}` : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {confirmId === rule.id ? (
                        <>
                          <span className="text-xs text-[var(--color-ink-faint)]">确认删除？</span>
                          <button onClick={() => del(rule.id)}
                            className="rounded-[5px] bg-[var(--color-danger)] px-2 py-0.5 text-[11px] font-medium text-white transition hover:brightness-110">
                            是
                          </button>
                          <button onClick={() => setConfirmId(null)}
                            className="rounded-[5px] bg-[var(--color-surface-2)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-ink-soft)] transition hover:bg-[var(--color-border)]">
                            否
                          </button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => toggleEnabled(rule)} title={rule.enabled ? "停用" : "启用"} aria-label={rule.enabled ? "停用" : "启用"}
                            className={cn("flex items-center gap-1 rounded-[5px] px-1.5 py-0.5 text-[11px] font-medium transition",
                              rule.enabled ? "text-[var(--color-brand-dark)]" : "text-[var(--color-ink-faint)]")}>
                            <span className={cn("inline-block h-1.5 w-1.5 rounded-full", rule.enabled ? "bg-[var(--color-brand)]" : "bg-[var(--color-border-strong)]")} />
                            {rule.enabled ? "启用中" : "已停用"}
                          </button>
                          <button onClick={() => { setEditing(rule); setShowEditor(true); }} title="编辑规则" aria-label="编辑规则" className="grid h-7 w-7 place-items-center rounded-[6px] text-[var(--color-ink-faint)] opacity-0 transition hover:bg-[var(--color-surface-2)] hover:text-[var(--color-brand-dark)] group-hover:opacity-100"><Pencil size={14} /></button>
                          <button onClick={() => setConfirmId(rule.id)} title="删除规则" aria-label="删除规则" className="grid h-7 w-7 place-items-center rounded-[6px] text-[var(--color-ink-faint)] opacity-0 transition hover:bg-[var(--color-surface-2)] hover:text-[var(--color-danger)] group-hover:opacity-100"><Trash2 size={14} /></button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* alerts */}
            <div>
              <div className="mb-2 flex items-baseline gap-2 border-b border-[var(--color-border)] pb-2">
                <span className="text-[13px] font-semibold uppercase tracking-wider text-[var(--color-ink-faint)]">告警历史</span>
                <span className="text-xs text-[var(--color-ink-faint)]">每 15s 刷新</span>
              </div>
              {alerts.length === 0 && (
                <div className="py-10 text-center text-sm text-[var(--color-ink-faint)]">暂无告警</div>
              )}
              <div className="divide-y divide-[var(--color-border)]">
                {alerts.map((a, i) => (
                  <div key={`${a.rule_id}-${a.ts}-${i}`} className="flex gap-3 py-3">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: sevColor(a.severity) }} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="truncate text-sm font-medium text-[var(--color-ink)]">{a.name || a.symbol || a.rule_name}</span>
                        <span className="tnum shrink-0 text-[11px] text-[var(--color-ink-faint)]">{new Date(a.ts).toLocaleString()}</span>
                      </div>
                      <div className="mt-0.5 text-[13px] text-[var(--color-ink-soft)]">{a.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {showEditor && (
        <RuleEditor
          initial={editing ?? undefined}
          strategies={strategies}
          onSaved={() => { setShowEditor(false); loadRules(); }}
          onCancel={() => setShowEditor(false)}
        />
      )}
    </div>
  );
}
