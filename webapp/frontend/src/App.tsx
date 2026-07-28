import { useState, useCallback, useEffect, createContext, useContext } from "react";
import {
  Routes, Route, Navigate, Outlet, useNavigate, useLocation, useParams,
} from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { NewAnalysis } from "./components/NewAnalysis";
import { RunWorkbench } from "./components/RunWorkbench";
import { CompareView } from "./components/CompareView";
import { PerformancePanel } from "./components/PerformancePanel";
import { HedgeView } from "./components/HedgeView";
import { BacktestView } from "./components/BacktestView";
import { Screener } from "./components/Screener";
import { Monitor } from "./components/Monitor";
import { Market } from "./components/Market";
import { Assistant } from "./components/Assistant";
import { Settings } from "./components/Settings";
import { Landing } from "./components/Landing";
import { Login } from "./components/Login";
import { api } from "./api/client";
import { getToken, onUnauthorized } from "./lib/auth";
import type { RunSummary } from "./api/types";

/**
 * Real routing (react-router): every view has a URL, so the browser back/forward
 * buttons work and any view — including a single run at /app/run/:id — is
 * deep-linkable and survives a refresh.
 *
 *   /                     marketing landing
 *   /app                  new-analysis form
 *   /app/run/:id          run workbench
 *   /app/screener|monitor|compare|performance|hedge|backtest|settings
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingRoute />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route path="/app" element={
            <div className="h-full overflow-y-auto px-6 py-12">
              <NewAnalysisBridge />
            </div>
          } />
          <Route path="/app/run/:id" element={<RunRoute />} />
          <Route path="/app/screener" element={<ScreenerBridge />} />
          <Route path="/app/monitor" element={<Monitor />} />
          <Route path="/app/market" element={<Market />} />
          <Route path="/app/assistant" element={<Assistant />} />
          <Route path="/app/compare" element={<CompareBridge />} />
          <Route path="/app/performance" element={<PerformancePanel />} />
          <Route path="/app/hedge" element={<HedgeView />} />
          <Route path="/app/backtest" element={<BacktestView />} />
          <Route path="/app/settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function LandingRoute() {
  const navigate = useNavigate();
  return <Landing onEnter={() => navigate("/app")} />;
}

/** Auth gate for everything under /app. null = still checking (splash),
 *  false = show login in place (URL is preserved, so a successful login lands
 *  exactly where the user was headed). */
function RequireAuth() {
  const { authed, onAuthed } = useAppState();
  if (authed === null) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[var(--color-canvas)]">
        <div className="skeleton h-10 w-40 rounded-full" />
      </div>
    );
  }
  if (!authed) return <Login onSuccess={onAuthed} />;
  return <Outlet />;
}

/** App shell: sidebar + routed main pane. Active states are derived from the
 *  URL — there is no parallel "current view" state to get out of sync. */
function Shell() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { refreshKey, onDeleted, openRun } = useAppState();
  const [navCollapsed, setNavCollapsed] = useState(false);

  const activeId = pathname.startsWith("/app/run/") ? pathname.split("/")[3] : null;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-canvas)]">
      <Sidebar
        activeId={activeId}
        refreshKey={refreshKey}
        onHome={() => navigate("/")}
        compareActive={pathname === "/app/compare"}
        performanceActive={pathname === "/app/performance"}
        hedgeActive={pathname === "/app/hedge"}
        backtestActive={pathname === "/app/backtest"}
        screenerActive={pathname === "/app/screener"}
        monitorActive={pathname === "/app/monitor"}
        marketActive={pathname === "/app/market"}
        assistantActive={pathname === "/app/assistant"}
        settingsActive={pathname === "/app/settings"}
        collapsed={navCollapsed}
        onToggle={() => setNavCollapsed((v) => !v)}
        onNew={() => navigate("/app")}
        onSelect={(id) => openRun(id)}
        onCompare={() => navigate("/app/compare")}
        onPerformance={() => navigate("/app/performance")}
        onHedge={() => navigate("/app/hedge")}
        onBacktest={() => navigate("/app/backtest")}
        onScreener={() => navigate("/app/screener")}
        onMonitor={() => navigate("/app/monitor")}
        onMarket={() => navigate("/app/market")}
        onAssistant={() => navigate("/app/assistant")}
        onSettings={() => navigate("/app/settings")}
        onDeleted={onDeleted}
      />
      <main className="flex-1 overflow-hidden">
        {/* key on pathname → every navigation replays the page-enter rise */}
        <div key={pathname} className="page-enter h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function RunRoute() {
  const { id } = useParams();
  const { state } = useLocation();
  const { openRun, onStatusSettled } = useAppState();
  // ticker arrives via navigation state for instant header render; on a deep
  // link / refresh it is absent and the workbench fills it from the run data.
  const ticker = (state as { ticker?: string } | null)?.ticker;
  return (
    <RunWorkbench
      key={id}
      runId={id!}
      ticker={ticker}
      onOpenRun={openRun}
      onStatusSettled={onStatusSettled}
    />
  );
}

function NewAnalysisBridge() {
  const { onStarted } = useAppState();
  return <NewAnalysis onStarted={onStarted} />;
}

function ScreenerBridge() {
  const { onStarted } = useAppState();
  return <Screener onStarted={onStarted} />;
}

function CompareBridge() {
  const { runs } = useAppState();
  return <CompareView runs={runs} />;
}

/* ── Shared session state ──────────────────────────────────────────────────
   Auth status, run list and navigation helpers live in one context so the
   router branches above can stay declarative. */

type AppState = {
  authed: boolean | null;
  onAuthed: () => void;
  runs: RunSummary[];
  refreshKey: number;
  openRun: (id: string, ticker?: string) => void;
  onStarted: (id: string) => void;
  onDeleted: (id: string) => void;
  onStatusSettled: () => void;
};

const AppStateContext = createContext<AppState | null>(null);

function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState outside provider");
  return ctx;
}

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const checkAuth = useCallback(() => {
    api
      .authStatus()
      .then((s) => setAuthed(!s.auth_required || !!getToken()))
      .catch(() => setAuthed(true)); // if status call fails, don't hard-block
  }, []);

  useEffect(() => {
    checkAuth();
    return onUnauthorized(() => setAuthed(false));
  }, [checkAuth]);

  // Keep a run list for the compare view (also refreshed when a run starts).
  useEffect(() => {
    if (!authed) return;
    api.listRuns().then(setRuns).catch(() => {});
  }, [authed, refreshKey]);

  const openRun = useCallback(
    (id: string, ticker?: string) => {
      navigate(`/app/run/${id}`, { state: { ticker } });
    },
    [navigate],
  );

  const onStarted = useCallback(
    (id: string) => {
      navigate(`/app/run/${id}`);
      setRefreshKey((k) => k + 1); // refresh history to show the new running run
    },
    [navigate],
  );

  const onDeleted = useCallback(
    (id: string) => {
      // If the deleted run is the one on screen, fall back to the new-analysis view.
      if (pathname === `/app/run/${id}`) navigate("/app");
      setRefreshKey((k) => k + 1); // refresh history + compare list
    },
    [pathname, navigate],
  );

  const onStatusSettled = useCallback(() => setRefreshKey((k) => k + 1), []);

  const value: AppState = {
    authed,
    onAuthed: () => setAuthed(true),
    runs,
    refreshKey,
    openRun,
    onStarted,
    onDeleted,
    onStatusSettled,
  };
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}
