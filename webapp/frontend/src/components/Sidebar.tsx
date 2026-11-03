import { Plus, History as HistoryIcon, GitCompareArrows, PanelLeftClose, PanelLeftOpen, Trash2, Check, X, TrendingUp, Shield, FlaskConical, Search, Bell, Settings as SettingsIcon, Bot, SlidersHorizontal, ShieldAlert, GitBranch } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { RunSummary } from "../api/types";
import { Logo } from "./Logo";
import { cn, ratingCn, ratingDir } from "../lib/format";
import type { Dir } from "../lib/format";

// Rating colors tuned for the dark shell (the shared dirClasses are calibrated
// for light surfaces — the amber is unreadable on near-black).
const shellRatingText: Record<Dir, string> = {
  bull: "text-[#3fe38f]",
  bear: "text-[#ff8a8e]",
  neutral: "text-[#ffc76b]",
};

export function Sidebar({
  activeId,
  onNew,
  onSelect,
  onCompare,
  onPerformance,
  onHedge,
  onRisk,
  onOptimize,
  onBacktest,
  onScreener,
  onMonitor,
  onMarket,
  onAssistant,
  onSettings,
  onConfig,
  onHome,
  onDeleted,
  compareActive,
  performanceActive,
  hedgeActive,
  riskActive,
  optimizeActive,
  backtestActive,
  screenerActive,
  monitorActive,
  marketActive,
  assistantActive,
  settingsActive,
  configActive,
  refreshKey,
  collapsed,
  onToggle,
}: {
  activeId: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onCompare: () => void;
  onPerformance: () => void;
  onHedge: () => void;
  onRisk: () => void;
  onOptimize: () => void;
  onBacktest: () => void;
  onScreener: () => void;
  onMonitor: () => void;
  onMarket: () => void;
  onAssistant: () => void;
  onSettings: () => void;
  onConfig: () => void;
  onHome: () => void;
  onDeleted: (id: string) => void;
  compareActive: boolean;
  performanceActive: boolean;
  hedgeActive: boolean;
  riskActive: boolean;
  optimizeActive: boolean;
  backtestActive: boolean;
  screenerActive: boolean;
  monitorActive: boolean;
  marketActive: boolean;
  assistantActive: boolean;
  settingsActive: boolean;
  configActive: boolean;
  refreshKey: number;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const doneCount = runs.filter((r) => r.status === "done").length;

  useEffect(() => {
    let alive = true;
    api
      .listRuns()
      .then((r) => alive && setRuns(r))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setDeleteError(null);
    try {
      await api.deleteRun(id);
      setRuns((rs) => rs.filter((r) => r.id !== id));
      onDeleted(id);
    } catch (e) {
      // Surface the backend reason (e.g. 409 while still running) inline —
      // never a blocking window.alert().
      setDeleteError(e instanceof Error ? e.message : "删除失败，请重试。");
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  };

  // Data-driven nav: one definition feeds both the expanded panel and the
  // collapsed icon rail. `locked` keeps an entry visible but disabled (with a
  // hint) instead of hiding it, so features are discoverable before unlock.
  const NAV: NavEntry[] = [
    { key: "assistant", icon: <Bot size={16} />, label: "投研助手", active: assistantActive, onClick: onAssistant, group: "工作区" },
    { key: "screener", icon: <Search size={16} />, label: "选股", active: screenerActive, onClick: onScreener, group: "工作区" },
    { key: "monitor", icon: <Bell size={16} />, label: "监控中心", active: monitorActive, onClick: onMonitor, group: "工作区" },
    { key: "market", icon: <TrendingUp size={16} />, label: "大盘", active: marketActive, onClick: onMarket, group: "工作区" },
    {
      key: "compare", icon: <GitCompareArrows size={16} />, label: "多标的对比",
      active: compareActive, onClick: onCompare, group: "工作区",
      locked: doneCount < 2, lockedHint: "完成至少 2 条分析后可用",
    },
    { key: "performance", icon: <TrendingUp size={16} />, label: "绩效归因", active: performanceActive, onClick: onPerformance, group: "工具" },
    { key: "hedge", icon: <Shield size={16} />, label: "跨品种对冲", active: hedgeActive, onClick: onHedge, group: "工具" },
    { key: "risk", icon: <ShieldAlert size={16} />, label: "组合风险 (VaR)", active: riskActive, onClick: onRisk, group: "工具" },
    { key: "optimize", icon: <GitBranch size={16} />, label: "组合优化", active: optimizeActive, onClick: onOptimize, group: "工具" },
    { key: "backtest", icon: <FlaskConical size={16} />, label: "策略回测", active: backtestActive, onClick: onBacktest, group: "工具" },
    { key: "settings", icon: <SettingsIcon size={16} />, label: "设置 · 通知", active: settingsActive, onClick: onSettings, group: "系统" },
    { key: "config", icon: <SlidersHorizontal size={16} />, label: "应用配置", active: configActive, onClick: onConfig, group: "系统" },
  ];
  const NAV_GROUPS = ["工作区", "工具", "系统"];

  // Collapsed: a slim icon rail. Clicking any icon expands the panel.
  if (collapsed) {
    return (
      <aside className="shell-bg flex h-full w-14 shrink-0 flex-col items-center gap-1.5 border-r border-[var(--color-shell-line)] py-4">
        <button onClick={onHome} title="返回首页" aria-label="返回首页" className="grid h-9 w-9 place-items-center overflow-hidden rounded-xl transition hover:opacity-80">
          <Logo size={36} />
        </button>
        <button
          onClick={onToggle}
          title="展开侧栏"
          aria-label="展开侧栏"
          className="mb-1 grid h-9 w-9 place-items-center rounded-[8px] text-[var(--color-shell-text-soft)] transition hover:bg-[var(--color-shell-hover)] hover:text-[var(--color-shell-text-strong)]"
        >
          <PanelLeftOpen size={18} />
        </button>
        <button
          onClick={onNew}
          title="新建分析"
          aria-label="新建分析"
          className="grid h-9 w-9 place-items-center rounded-[8px] text-[var(--color-shell-text)] transition hover:bg-[var(--color-shell-hover)] hover:text-[var(--color-shell-active-text)]"
        >
          <Plus size={18} />
        </button>
        {NAV.map((item) => (
          <button
            key={item.key}
            onClick={item.locked ? undefined : item.onClick}
            disabled={item.locked}
            title={item.locked ? `${item.label} · ${item.lockedHint}` : item.label}
            aria-label={item.label}
            className={cn(
              "grid h-9 w-9 place-items-center rounded-[8px] transition",
              item.active
                ? "bg-[var(--color-shell-active-bg)] text-[var(--color-shell-active-text)]"
                : item.locked
                  ? "cursor-not-allowed text-white/15"
                  : "text-[var(--color-shell-text)] hover:bg-[var(--color-shell-hover)] hover:text-[var(--color-shell-text-strong)]",
            )}
          >
            {item.icon}
          </button>
        ))}
      </aside>
    );
  }

  return (
    <aside className="shell-bg flex h-full w-72 shrink-0 flex-col border-r border-[var(--color-shell-line)]">
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <button onClick={onHome} title="返回首页" aria-label="返回首页" className="flex items-center gap-2 transition hover:opacity-80">
          <Logo size={32} className="rounded-xl" />
          <div className="text-[15px] font-black tracking-tight text-[var(--color-shell-text-strong)]">
            Drom<span className="gradient-text-static">X</span>
          </div>
        </button>
        <button
          onClick={onToggle}
          title="收起侧栏"
          aria-label="收起侧栏"
          className="text-[var(--color-shell-text-soft)] transition hover:text-[var(--color-shell-text-strong)]"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      <div className="px-3 pb-2">
        <button
          onClick={onNew}
          className="btn-brand flex w-full items-center justify-center gap-2 rounded-[var(--radius-control)] py-2 text-sm font-semibold"
        >
          <Plus size={17} /> 新建分析
        </button>
      </div>

      <nav className="px-2 pb-2">
        {NAV_GROUPS.map((g) => (
          <div key={g}>
            <div className="px-3 pb-1 pt-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--color-shell-text-soft)]">
              {g}
            </div>
            {NAV.filter((item) => item.group === g).map(({ key, ...item }) => (
              <NavItem key={key} {...item} />
            ))}
          </div>
        ))}
      </nav>

      <div className="mx-3 mb-1 border-t border-[var(--color-shell-line)]" />

      <div className="flex items-center gap-1.5 px-4 pb-2 pt-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-shell-text-soft)]">
        <HistoryIcon size={12} /> 历史记录
      </div>

      {deleteError && (
        <div className="mx-3 mb-2 rounded-[var(--radius-control)] bg-[rgba(255,90,95,0.14)] px-3 py-2 text-xs text-[#ff8a8e]">
          {deleteError}
        </div>
      )}

      <div className="stagger flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {runs.length === 0 && (
          <div className="px-3 py-6 text-center text-sm text-[var(--color-shell-text-soft)]">
            还没有分析记录
          </div>
        )}
        {runs.map((r) => {
          const isActive = activeId === r.id;
          const confirming = confirmId === r.id;
          const busy = deletingId === r.id;
          return (
            <div
              key={r.id}
              className={cn(
                "group relative w-full rounded-[8px] transition-colors",
                isActive
                  ? "bg-[var(--color-shell-active-bg)]"
                  : "hover:bg-[var(--color-shell-hover)]",
              )}
            >
              <button
                onClick={() => onSelect(r.id!)}
                className="flex w-full items-center gap-2 px-2.5 py-1.5 pr-8 text-left"
              >
                <span className="w-14 shrink-0 truncate text-sm font-medium text-[var(--color-shell-text-strong)]">{r.ticker}</span>
                <span className="tnum text-[11px] text-[var(--color-shell-text-soft)]">{r.trade_date}</span>
                <span className="ml-auto shrink-0">
                  {r.status === "running" ? (
                    <span className="text-[11px] text-[var(--color-shell-active-text)]">运行中…</span>
                  ) : r.status === "error" ? (
                    <span className="text-[11px] text-[var(--color-danger)]">失败</span>
                  ) : (
                    <span className={cn("inline-flex items-center gap-1 text-[11px] font-medium", shellRatingText[ratingDir(r.rating)])}>
                      <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      {ratingCn(r.rating)}
                    </span>
                  )}
                </span>
              </button>

              {/* Delete affordance: trash icon (hover/active reveal) → inline confirm */}
              {confirming ? (
                <div
                  className={cn(
                    "absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg py-1 pl-2 pr-1",
                    isActive ? "bg-[var(--color-shell-active-bg)]" : "bg-[var(--color-shell-deep)]",
                  )}
                >
                  <span className="mr-0.5 text-xs text-[var(--color-shell-text-soft)]">删除?</span>
                  <button
                    onClick={() => handleDelete(r.id!)}
                    disabled={busy}
                    title="确认删除"
                    aria-label="确认删除"
                    className="grid h-7 w-7 place-items-center rounded-lg bg-[var(--color-danger)] text-white transition hover:brightness-110 disabled:opacity-50"
                  >
                    <Check size={15} />
                  </button>
                  <button
                    onClick={() => setConfirmId(null)}
                    disabled={busy}
                    title="取消"
                    aria-label="取消删除"
                    className="grid h-7 w-7 place-items-center rounded-lg bg-[var(--color-shell-hover)] text-[var(--color-shell-text)] transition hover:bg-white/15"
                  >
                    <X size={15} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmId(r.id!)}
                  title="删除此记录"
                  aria-label="删除此记录"
                  className="absolute right-1.5 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-lg text-[var(--color-shell-text-soft)] opacity-0 transition hover:bg-[var(--color-shell-hover)] hover:text-[var(--color-danger)] focus:opacity-100 group-hover:opacity-100"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}

type NavEntry = {
  key: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  group?: string;
  locked?: boolean;
  lockedHint?: string;
};

// A left-aligned, borderless sidebar nav row (Linear/Vercel style): icon + label,
// hover/active background instead of a bordered rectangle, with a brand accent
// bar on the active item. Locked rows stay visible but inert so the feature is
// discoverable before it unlocks.
function NavItem({ icon, label, active, onClick, locked, lockedHint }: NavEntry) {
  return (
    <button
      onClick={locked ? undefined : onClick}
      disabled={locked}
      title={locked ? lockedHint : undefined}
      className={cn(
        "relative flex w-full items-center gap-2.5 rounded-[var(--radius-control)] px-3 py-2 text-[13.5px] font-medium transition-all duration-150",
        active
          ? "bg-[var(--color-shell-active-bg)] text-[var(--color-shell-active-text)] shadow-[inset_0_0_0_1px_rgba(6,193,103,0.28)]"
          : locked
            ? "cursor-not-allowed text-white/20"
            : "text-[var(--color-shell-text)] hover:bg-[var(--color-shell-hover)] hover:text-[var(--color-shell-text-strong)]",
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-[var(--color-brand)] shadow-[0_0_8px_rgba(6,193,103,0.8)]" />
      )}
      <span className={active ? "text-[var(--color-shell-active-text)]" : locked ? "text-white/15" : "text-[var(--color-shell-text-soft)]"}>{icon}</span>
      {label}
      {locked && <span className="ml-auto text-[10px] font-normal text-white/25">未解锁</span>}
    </button>
  );
}
