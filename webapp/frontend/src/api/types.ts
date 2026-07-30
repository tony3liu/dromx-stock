// Shared types mirroring the FastAPI backend (webapp/backend).

export type RunStatus = "running" | "done" | "error";

export interface RunSummary {
  id: string;
  ticker: string | null;
  trade_date: string | null;
  status: RunStatus | null;
  rating: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface RunRecord {
  id: string;
  ticker: string;
  trade_date: string;
  analysts: string[];
  depth: number;
  status: RunStatus;
  rating: string | null;
  created_at: string | null;
  finished_at: string | null;
  final_state: Record<string, unknown>;
  error?: string;
}

export interface CreateRunRequest {
  ticker: string;
  trade_date: string;
  analysts: string[];
  depth: number;
  shares?: number | null;
  cost_basis?: number | null;
  holdings?: string[];
  strategy_id?: string | null;
  on_complete_notify?: boolean;
}

export interface PricePoint {
  date: string;
  close: number;
  open?: number;
  high?: number;
  low?: number;
}

export interface IntradayPoint {
  time: number; // Unix timestamp (seconds)
  close: number;
  open?: number;
  high?: number;
  low?: number;
}

export interface PriceSeries {
  ticker: string;
  points: PricePoint[];
}

export interface IntradaySeries {
  ticker: string;
  interval: string;
  points: IntradayPoint[];
}

// SSE event shapes emitted by backend/runner.py
export type RunEvent =
  | { type: "start"; run_id: string; ticker: string; nodes: string[] }
  | { type: "section"; key: string; label: string; markdown: string }
  | { type: "complete"; run_id: string; rating: string | null }
  | { type: "error"; message: string }
  | { type: "queued"; message: string };

// The 16 report sections in pipeline order (mirrors backend store.REPORT_SECTIONS).
export const REPORT_SECTIONS: { key: string; label: string }[] = [
  { key: "regime_report", label: "Market Regime" },
  { key: "market_context", label: "Move Cross-Validation" },
  { key: "portfolio_context", label: "Portfolio Context" },
  { key: "market_report", label: "Technical / Market" },
  { key: "sentiment_report", label: "Sentiment" },
  { key: "news_report", label: "News & Macro" },
  { key: "fundamentals_report", label: "Fundamentals" },
  { key: "industry_report", label: "Industry & Supply Chain" },
  { key: "signal_aggregation", label: "Aggregated Signal" },
  { key: "event_impact", label: "Event Impact" },
  { key: "key_question", label: "Key Question" },
  { key: "investment_plan", label: "Research Manager" },
  { key: "trader_investment_plan", label: "Trader Plan" },
  { key: "risk_consensus", label: "Risk Consensus" },
  { key: "forecast_report", label: "Forecast (T+1/5/20/60)" },
  { key: "final_trade_decision", label: "Portfolio Manager Decision" },
];

// Chinese display labels for the report dimensions (UI shows these; the English
// labels above stay canonical for export/markdown).
export const SECTION_CN: Record<string, string> = {
  regime_report: "市场状态",
  market_context: "异动归因",
  portfolio_context: "组合上下文",
  market_report: "技术面",
  sentiment_report: "情绪面",
  news_report: "新闻宏观",
  fundamentals_report: "基本面",
  industry_report: "行业链",
  signal_aggregation: "信号融合",
  event_impact: "事件冲击",
  key_question: "关键问题",
  investment_plan: "研究综合",
  trader_investment_plan: "交易方案",
  risk_consensus: "风险共识",
  forecast_report: "时间轴预测",
  final_trade_decision: "最终决策",
};

export const ANALYSTS: { key: string; label: string }[] = [
  { key: "market", label: "Technical" },
  { key: "social", label: "Sentiment" },
  { key: "news", label: "News & Macro" },
  { key: "fundamentals", label: "Fundamentals" },
  { key: "industry", label: "Industry" },
];

export const DEPTHS: { value: number; label: string; hint: string }[] = [
  { value: 1, label: "Shallow", hint: "Quick — fewest rounds" },
  { value: 3, label: "Medium", hint: "Balanced depth" },
  { value: 5, label: "Deep", hint: "Most thorough" },
];

export interface PerfOutcome {
  ticker: string;
  trade_date: string;
  rating: string | null;
  direction: number | null; // 1 bull, 0 hold, -1 bear
  raw_return: number | null;
  alpha_return: number | null;
  holding_days: number | null;
  benchmark?: string;
  correct: boolean | null;
  status: "resolved" | "pending";
}

export interface PerfMetrics {
  runs_total: number;
  resolved: number;
  pending: number;
  scored: number;
  hit_rate: number | null;
  avg_raw_return: number | null;
  avg_alpha_return: number | null;
  avg_strategy_return: number | null;
  win_rate: number | null;
  sharpe: number | null;
  sortino: number | null;
  max_drawdown: number | null;
  profit_factor: number | null;
  calmar: number | null;
  holding_days: number;
  by_rating: Record<string, { total: number; correct: number; hit_rate: number | null }>;
}

export interface PerformanceReport {
  metrics: PerfMetrics;
  outcomes: PerfOutcome[];
}

export interface SizingScenario {
  label: "bear" | "base" | "bull";
  probability: number; // 0..1
  magnitude_pct: number; // signed % move
}

export interface SizingSuggestion {
  low_pct: number;
  high_pct: number;
  full_kelly_pct: number;
  capped: boolean;
  note: string;
}

export interface SizingReport {
  run_id: string;
  ticker: string | null;
  rating: string | null;
  has_scenarios: boolean;
  scenarios: SizingScenario[];
  expected_value_pct: number | null;
  full_kelly_pct: number | null;
  sizing: SizingSuggestion | null;
  max_fraction_pct: number;
}

export interface FactorExposure {
  ticker: string;
  benchmark: string;
  available: boolean;
  window_days?: number;
  beta?: number;
  alpha_annual_pct?: number;
  r_squared?: number | null;
  total_vol_annual_pct?: number;
  idio_vol_annual_pct?: number;
  systematic_vol_annual_pct?: number;
  idio_share?: number | null;
  downside_beta?: number | null;
  momentum_pct?: number;
  beta_hedge_ratio?: number;
  note: string;
}

export interface HedgePair { a: string; b: string; corr: number }
export interface HedgeSuggestion { kind: "concentration" | "hedge"; tickers: string[]; text: string }
export interface HedgeMatrixRow { ticker: string; corr: Record<string, number | null> }
export interface HedgeReport {
  names: string[];
  skipped: string[];
  matrix: HedgeMatrixRow[];
  pairs: HedgePair[];
  clusters: string[][];
  suggestions: HedgeSuggestion[];
  lookback_days: number;
}

export interface BacktestDay {
  date: string;
  rating: string | null;
  direction: number | null;
  raw_return: number | null;
  held_days: number;
  correct: boolean | null;
}

export interface BacktestMetrics {
  days_scored: number;
  hit_rate: number | null;
  cumulative_return_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  trades: number;
}

export interface BacktestRecord {
  id: string;
  ticker: string;
  start_date: string;
  end_date: string;
  analysts?: string[];
  depth?: number;
  holding_days: number;
  status: "running" | "done" | "error";
  days: BacktestDay[];
  days_total: number;
  days_done: number;
  created_at: string | null;
  finished_at: string | null;
  metrics: BacktestMetrics | null;
}

export interface BacktestEstimate { days: number; max_days: number; capped: boolean }

// ─────────────────────────────────────────────────────────────────────────
// v0.4.0 Phase 3 — strategy screening / monitoring / scheduled jobs / notify
// ─────────────────────────────────────────────────────────────────────────

export type Market = "hk" | "us" | "cn";

export interface StrategyParam {
  id: string;
  label: string;
  type: string;
  default: number;
  min?: number;
  max?: number;
  step?: number;
}

export interface StrategyMeta {
  id: string;
  name: string;
  description: string;
  markets: string[];
  tags: string[];
  source: "builtin" | "custom" | "ai";
  params: StrategyParam[];
  params_defaults: Record<string, number>;
  scoring: Record<string, number>;
  entry_signals: string[];
  exit_signals: string[];
  stop_loss: number | null;
  max_hold_days: number | null;
  limit: number;
}

export interface StrategyListResponse {
  market: string;
  strategies: StrategyMeta[];
  load_errors: { file: string; error: string }[];
}

// A screening hit row. Core fields are typed; the rest of the enriched columns
// (ma20/rsi_14/…) come through dynamically.
export interface StrategyHit {
  symbol: string;
  name?: string;
  close?: number | null;
  change_pct?: number | null;
  turnover_rate?: number | null;
  vol_ratio_5d?: number | null;
  rsi_14?: number | null;
  score?: number | null;
  [key: string]: unknown;
}

export interface StrategyRunResult {
  as_of: string;
  strategy_id: string;
  market: string;
  rows: StrategyHit[];
  total: number;
  elapsed_ms: number;
  scores: Record<string, number>;
}

export interface AIGenerateResult {
  code: string;
  meta: Record<string, unknown>;
  valid: boolean;
  error: string | null;
  saved_path?: string;
}

export type RuleType = "price" | "signal" | "strategy";
export type RuleScope = "symbols" | "all";
export type RuleSeverity = "info" | "warn" | "critical";

export interface RuleCondition {
  field: string;
  op: string;     // ">" ">=" "<" "<=" "==" "!=" | "truth"
  value?: number;
}

export interface MonitorRule {
  id: string;
  name: string;
  type: RuleType;
  scope: RuleScope;
  symbols: string[];
  market: string;
  strategy_id: string | null;
  direction: "entry" | "exit" | "both";
  conditions: RuleCondition[];
  logic: "and" | "or";
  cooldown_seconds: number;
  severity: RuleSeverity;
  message: string;
  enabled: boolean;
  created_at?: string;
}

export interface AlertEvent {
  ts: number;
  rule_id: string;
  rule_name: string;
  source: string;
  type: string;
  symbol: string;
  name: string;
  message: string;
  price: number | null;
  change_pct: number | null;
  signals: string[];
  severity: RuleSeverity;
}

export type JobKind = "analysis" | "screen" | "warmup";

export interface Job {
  id: string;
  kind: JobKind;
  cron: string;
  params: Record<string, unknown>;
  enabled: boolean;
}

export interface NotifyChannels {
  system: { enabled: boolean; available: boolean };
  feishu: { configured: boolean };
}

export interface NotifySettings {
  system?: { enabled: boolean };
  feishu?: { webhook_url?: string; secret?: string };
}

export interface EnvSettingItem {
  key: string;
  label: string;
  group: string;
  secret: boolean;
  hint: string;
  placeholder: string;
  source: "page" | "env" | null;
  configured: boolean;
  preview?: string;
  value?: string;
}
