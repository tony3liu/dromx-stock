// Thin REST client for the backend. All paths go through the Vite /api proxy.
import type { AIGenerateResult, AIScreenResult, AlertEvent, BacktestEstimate, BacktestRecord, CreateRunRequest, EnvSettingItem, FactorExposure, HedgeReport, IntradaySeries, Job, Market, MonitorRule, NotifyChannels, NotifySettings, PerformanceReport, PriceSeries, RunRecord, RunSummary, ScreenHistorySummary, SizingReport, StrategyListResponse, StrategyMeta, StrategyRunResult } from "./types";
import { authHeaders, notifyUnauthorized } from "../lib/auth";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
  });
  if (res.status === 401) {
    notifyUnauthorized();
    throw new Error("401 — 登录已失效，请重新登录");
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  authStatus: () => jsonFetch<{ auth_required: boolean }>("/api/auth/status"),

  login: (password: string) =>
    jsonFetch<{ token: string; auth_required: boolean }>("/api/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  createRun: (body: CreateRunRequest) =>
    jsonFetch<{ id: string; status: string }>("/api/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listRuns: () => jsonFetch<RunSummary[]>("/api/runs"),

  performance: (holdingDays = 5) =>
    jsonFetch<PerformanceReport>(`/api/performance?holding_days=${holdingDays}`),

  getRun: (id: string) => jsonFetch<RunRecord>(`/api/runs/${id}`),

  sizing: (id: string) => jsonFetch<SizingReport>(`/api/runs/${id}/sizing`),

  factor: (id: string) => jsonFetch<FactorExposure>(`/api/runs/${id}/factor`),

  hedge: () => jsonFetch<HedgeReport>("/api/hedge"),

  backtestEstimate: (ticker: string, start: string, end: string) =>
    jsonFetch<BacktestEstimate>(
      `/api/backtest/estimate?ticker=${encodeURIComponent(ticker)}&start_date=${start}&end_date=${end}`,
    ),

  backtestList: () => jsonFetch<BacktestRecord[]>("/api/backtest"),

  backtestStart: (body: {
    ticker: string; start_date: string; end_date: string;
    analysts: string[]; depth: number; holding_days: number;
  }) => jsonFetch<{ id: string; status: string; days: number }>("/api/backtest", {
    method: "POST",
    body: JSON.stringify(body),
  }),

  backtestGet: (id: string) => jsonFetch<BacktestRecord>(`/api/backtest/${id}`),

  backtestStop: (id: string) =>
    jsonFetch<{ ok: boolean; id: string }>(`/api/backtest/${id}/stop`, { method: "POST" }),

  deleteRun: (id: string) =>
    jsonFetch<{ ok: boolean; id: string }>(`/api/runs/${id}`, { method: "DELETE" }),


  price: (ticker: string, date?: string, days = 120) =>
    jsonFetch<PriceSeries>(
      `/api/price/${encodeURIComponent(ticker)}?days=${days}${date ? `&date=${encodeURIComponent(date)}` : ""}`,
    ),

  intradayPrice: (ticker: string, interval = "5m") =>
    jsonFetch<IntradaySeries>(
      `/api/price/intraday/${encodeURIComponent(ticker)}?interval=${interval}`,
    ),

  assistantClear: (sessionId: string) =>
    jsonFetch<{ ok: boolean }>(`/api/assistant/clear?session_id=${encodeURIComponent(sessionId)}`, {
      method: "POST",
    }),

  ask: (id: string, question: string, history: [string, string][]) =>
    jsonFetch<{ answer: string }>(`/api/runs/${id}/qa`, {
      method: "POST",
      body: JSON.stringify({ question, history }),
    }),

  // Streaming Q&A: POST can't use EventSource, so we read the SSE body via fetch
  // + ReadableStream and invoke onDelta for each token chunk.
  askStream: async (
    id: string,
    question: string,
    history: [string, string][],
    onDelta: (text: string) => void,
    signal?: AbortSignal,
  ): Promise<void> => {
    const res = await fetch(`/api/runs/${id}/qa/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question, history }),
      signal,
    });
    if (res.status === 401) {
      notifyUnauthorized();
      throw new Error("401 — 登录已失效，请重新登录");
    }
    if (!res.ok || !res.body) {
      const detail = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail}` : ""}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      // Normalize CRLF -> LF: sse-starlette delimits frames with \r\n\r\n, which
      // contains no "\n\n" substring, so splitting on "\n\n" alone never fires.
      buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      // SSE frames are separated by a blank line; each frame has `data: ...`.
      const frames = buf.split("\n\n");
      buf = frames.pop() ?? "";
      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        try {
          const ev = JSON.parse(line.slice(5).trim());
          if (ev.type === "delta" && ev.text) onDelta(ev.text);
          else if (ev.type === "done") return;
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  },

  // ── v0.4.0 Phase 3: strategy screening ─────────────────────────────────
  strategies: (market: Market) =>
    jsonFetch<StrategyListResponse>(`/api/strategies?market=${market}`),

  getStrategy: (id: string, market: Market) =>
    jsonFetch<StrategyMeta>(`/api/strategies/${id}?market=${market}`),

  runStrategy: (id: string, body: { market: Market; as_of?: string | null; params?: Record<string, number>; pool?: string[] }) =>
    jsonFetch<StrategyRunResult>(`/api/strategies/${id}/run`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  aiScreen: (body: { prompt: string; market: Market; as_of?: string | null; review_top_n?: number; refine_from?: string | null; feedback?: string | null }) =>
    jsonFetch<AIScreenResult>("/api/strategies/ai-screen", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  screenHistory: () => jsonFetch<{ history: ScreenHistorySummary[] }>("/api/strategies/history"),

  screenHistoryDetail: (id: string) => jsonFetch<AIScreenResult & { id: string }>(`/api/strategies/history/${id}`),

  generateStrategy: (prompt: string, save = false) =>
    jsonFetch<AIGenerateResult>("/api/strategies/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, save }),
    }),

  deleteStrategy: (id: string, market: Market) =>
    jsonFetch<{ ok: boolean; id: string }>(`/api/strategies/${id}?market=${market}`, { method: "DELETE" }),

  // ── monitor rules + alerts ─────────────────────────────────────────────
  monitorRules: () => jsonFetch<{ rules: MonitorRule[] }>("/api/monitor/rules"),

  createRule: (rule: MonitorRule) =>
    jsonFetch<MonitorRule>("/api/monitor/rules", { method: "POST", body: JSON.stringify(rule) }),

  updateRule: (id: string, rule: MonitorRule) =>
    jsonFetch<MonitorRule>(`/api/monitor/rules/${id}`, { method: "PUT", body: JSON.stringify(rule) }),

  deleteRule: (id: string) =>
    jsonFetch<{ ok: boolean; id: string }>(`/api/monitor/rules/${id}`, { method: "DELETE" }),

  alerts: (limit = 200, source?: string) =>
    jsonFetch<{ alerts: AlertEvent[] }>(`/api/monitor/alerts?limit=${limit}${source ? `&source=${source}` : ""}`),

  // ── scheduled jobs ─────────────────────────────────────────────────────
  jobs: () => jsonFetch<{ jobs: Job[]; running: boolean }>("/api/jobs"),

  createJob: (job: Job) =>
    jsonFetch<Job>("/api/jobs", { method: "POST", body: JSON.stringify(job) }),

  updateJob: (id: string, job: Job) =>
    jsonFetch<Job>(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(job) }),

  deleteJob: (id: string) =>
    jsonFetch<{ ok: boolean; id: string }>(`/api/jobs/${id}`, { method: "DELETE" }),

  runJob: (id: string) =>
    jsonFetch<Record<string, unknown>>(`/api/jobs/${id}/run`, { method: "POST" }),

  // ── notification config ────────────────────────────────────────────────
  notifyChannels: () => jsonFetch<NotifyChannels>("/api/notify/channels"),

  testNotify: (channels?: string[]) =>
    jsonFetch<{ ok: boolean; results: Record<string, boolean> }>("/api/notify/test", {
      method: "POST",
      body: JSON.stringify({ channels: channels ?? null }),
    }),

  updateNotify: (settings: NotifySettings) =>
    jsonFetch<Record<string, unknown>>("/api/notify/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  // ── 应用配置（页面配置层，优先级高于 .env） ──────────────────────────────
  envSettings: () => jsonFetch<{ settings: EnvSettingItem[] }>("/api/settings/env"),

  updateEnvSettings: (updates: Record<string, string>) =>
    jsonFetch<{ updated: string[]; llm_changed: boolean }>("/api/settings/env", {
      method: "PUT",
      body: JSON.stringify({ updates }),
    }),

  // ── comprehensive report PDF ───────────────────────────────────────────
  // Fetch the generated report as a PDF blob (carries the auth token) and
  // trigger a direct browser download — no print dialog.
  downloadReportPdf: async (id: string, filename: string): Promise<void> => {
    const res = await fetch(`/api/runs/${id}/report.pdf`, { headers: { ...authHeaders() } });
    if (res.status === 401) {
      notifyUnauthorized();
      throw new Error("401 — 登录已失效，请重新登录");
    }
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}${detail ? ` — ${detail}` : ""}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
