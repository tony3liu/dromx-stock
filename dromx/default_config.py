import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

# Single source of truth for env-var → config-key overrides. To expose
# a new config key for environment-based override, add a row here — no
# entry-point script changes required. Coercion is driven by the type
# of the existing default, so users can keep writing plain strings in
# their .env file.
_ENV_OVERRIDES = {
    "TRADINGAGENTS_LLM_PROVIDER":         "llm_provider",
    "TRADINGAGENTS_DEEP_THINK_LLM":       "deep_think_llm",
    "TRADINGAGENTS_QUICK_THINK_LLM":      "quick_think_llm",
    "TRADINGAGENTS_LLM_BACKEND_URL":      "backend_url",
    "TRADINGAGENTS_OUTPUT_LANGUAGE":      "output_language",
    "TRADINGAGENTS_MAX_DEBATE_ROUNDS":    "max_debate_rounds",
    "TRADINGAGENTS_MAX_RISK_ROUNDS":      "max_risk_discuss_rounds",
    "TRADINGAGENTS_CHECKPOINT_ENABLED":   "checkpoint_enabled",
    "TRADINGAGENTS_BENCHMARK_TICKER":     "benchmark_ticker",
    "TRADINGAGENTS_TEMPERATURE":          "temperature",
    "TRADINGAGENTS_PEER_TICKERS":         "peer_tickers",
    "TRADINGAGENTS_HOLDINGS":             "holdings",
    "TRADINGAGENTS_ENABLE_BROWSER":       "enable_browser",
    # Provider-specific reasoning/thinking knobs (None = each provider's own
    # default). Settable here for non-interactive runs; the CLI also offers an
    # interactive choice, which is skipped when the matching var is set.
    "TRADINGAGENTS_GOOGLE_THINKING_LEVEL":   "google_thinking_level",
    "TRADINGAGENTS_OPENAI_REASONING_EFFORT": "openai_reasoning_effort",
    "TRADINGAGENTS_ANTHROPIC_EFFORT":        "anthropic_effort",
}


_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference):
    """Coerce env-var string to the type of the existing default value.

    Invalid values raise ``ValueError`` rather than silently falling back to a
    default — a misspelled boolean (e.g. ``treu``) or non-numeric int should fail
    loudly at startup, not quietly misconfigure an unattended run.
    """
    if isinstance(reference, bool):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(
            f"expected a boolean ({'/'.join(_BOOL_TRUE + _BOOL_FALSE)}), got {value!r}"
        )
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    if isinstance(reference, list):
        # Comma-separated env value → list of trimmed, non-empty strings.
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _apply_env_overrides(config: dict) -> dict:
    """Apply TRADINGAGENTS_* env vars to the config dict in-place."""
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid value for {env_var}: {exc}") from exc
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md")),
    # Optional cap on the number of resolved memory log entries. When set,
    # the oldest resolved entries are pruned once this limit is exceeded.
    # Pending entries are never pruned. None disables rotation entirely.
    "memory_log_max_entries": None,
    # Signal-level scorecard: tracks each analyst's directional hit-rate by
    # market regime so the Signal Aggregator can up-weight historically
    # accurate lenses. None / empty disables tracking.
    "analyst_scorecard_path": os.getenv(
        "TRADINGAGENTS_SCORECARD_PATH",
        os.path.join(_TRADINGAGENTS_HOME, "memory", "analyst_scorecard.json"),
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.5",
    "quick_think_llm": "gpt-5.4-mini",
    # When None, each provider's client falls back to its own default endpoint
    # (api.openai.com for OpenAI, generativelanguage.googleapis.com for Gemini, ...).
    # The CLI overrides this per provider when the user picks one. Keeping a
    # provider-specific URL here would leak (e.g. OpenAI's /v1 was previously
    # being forwarded to Gemini, producing malformed request URLs).
    "backend_url": None,
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Sampling temperature, forwarded to every provider when set. None leaves
    # each provider at its own default. Lower values reduce run-to-run
    # variation on models that honor it; reasoning models largely ignore it
    # and no setting makes LLM output bit-identical across runs (see README).
    "temperature": None,
    # Checkpoint/resume: when True, LangGraph saves state after each node
    # so a crashed run can resume from the last successful step.
    "checkpoint_enabled": False,
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # News / data fetching parameters
    # Increase for longer lookback strategies or to broaden macro coverage;
    # decrease to reduce token usage in agent prompts.
    "news_article_limit": 20,             # max articles per ticker (ticker-news)
    "global_news_article_limit": 10,      # max articles for global/macro news
    "global_news_lookback_days": 7,       # macro news lookback window
    # Search queries used by get_global_news for macro headlines. Extend or
    # replace to broaden geographic / sector coverage.
    "global_news_queries": [
        "Federal Reserve interest rates inflation",
        "S&P 500 earnings GDP economic outlook",
        "geopolitical risk trade war sanctions",
        "ECB Bank of England BOJ central bank policy",
        "oil commodities supply chain energy",
    ],
    # Data vendor configuration
    # Category-level configuration (default for all tools in category).
    # The configured value is the exact vendor chain — requests are NOT silently
    # routed to vendors you didn't choose. For ordered fallback, list several,
    # e.g. "yfinance,alpha_vantage". "default" uses all available vendors.
    "data_vendors": {
        # Vendor chains are ordered fallbacks (left = preferred). They span all
        # three markets so a single config serves US / HK / A-share runs: each
        # vendor raises NoMarketDataError for symbols it doesn't cover, and the
        # router advances to the next vendor automatically.
        "core_stock_apis": "tencent,mootdx",           # Options: tencent, mootdx, alpha_vantage, yfinance
        "technical_indicators": "tencent,mootdx",      # Options: tencent, mootdx, alpha_vantage, yfinance
        "fundamental_data": "sec,eastmoney,mootdx,tencent",  # US->SEC, US/HK->eastmoney, A->mootdx, fallback tencent
        # Three-statement vendors: SEC (US), Eastmoney (US/HK), Sina (A-share).
        "financial_statements": "sec,eastmoney,sina,tencent",
        "news_data": "google,eastmoney_news",          # Options: google, eastmoney_news, alpha_vantage, yfinance
        "macro_data": "fred",                          # Options: fred (needs FRED_API_KEY)
        "prediction_markets": "polymarket",            # Options: polymarket (keyless)
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # Optional peer tickers for relative comparison. When non-empty, the market
    # analyst pulls each peer's verified snapshot (relative strength) and the
    # fundamentals analyst pulls each peer's overview (relative valuation).
    # Empty list disables peer context entirely. Settable via
    # TRADINGAGENTS_PEER_TICKERS as a comma-separated list (e.g. "MSFT,GOOGL").
    "peer_tickers": [],
    # Current portfolio holdings for PRE-TRADE portfolio context: the PM is told
    # how adding the analysed name interacts with what is already held (cross-
    # holding correlation, sector/currency concentration). Each entry is
    # "TICKER" or "TICKER:weight" (weight in % of book, optional). Empty = no
    # portfolio context (single-name analysis, unchanged). Settable via
    # TRADINGAGENTS_HOLDINGS as a comma-separated list, e.g. "MU,07709.HK:20,03121.HK:15".
    "holdings": [],
    # Optional explicit overnight reference tickers for the transmission chain
    # (see ``dataflows.overnight_transmission``). When analysing a cross-market
    # ETF, this is the overnight LEAD reference (e.g. ["MU"] when analysing a
    # HK-listed Korea-semis ETF) — a market that opens before the listing market
    # and leads it. Empty = let the LLM judge the lead from the ETF structure,
    # then fall back to any cross-market holding. Settable via
    # TRADINGAGENTS_OVERNIGHT_REFS as a comma-separated list.
    "overnight_refs": [],
    # Browser web-reading (tradingagents/browser): when True, the News Analyst
    # pre-fetch step opens the top news links and reads the full article body via
    # a headless Chromium (agent-browser CLI) instead of relying on the ~200-char
    # API snippet. OFF by default — it needs Node.js + Chromium and is slower; the
    # whole pipeline runs unchanged when off. Settable via TRADINGAGENTS_ENABLE_BROWSER.
    "enable_browser": False,
    # ETF passthrough is AUTO-DETECTED for any ticker (resolve_etf_structure reads
    # the fund name + yfinance fields via an LLM — no per-ticker table needed).
    # This map is an OPTIONAL manual OVERRIDE only: use it to force/correct the
    # underlying proxy + currency when auto-detection is wrong or you want exact
    # tracking against a specific symbol. Empty (default) = pure auto-detection.
    # Key = ETF ticker; value = {"underlying": <symbol load_ohlcv understands>,
    # "currency": <ISO of the underlying market>}.
    "etf_underlying_map": {
        # Optional overrides, e.g.:
        # "03121.HK": {"underlying": "^KS200", "currency": "KRW"},
    },
    # Benchmark for alpha calculation in the reflection layer.
    # ``benchmark_ticker`` (when set) overrides the suffix map for all
    # tickers; leave it None to use ``benchmark_map`` for auto-detection
    # based on the ticker's exchange suffix. SPY remains the US default
    # so the reflection label keeps reading "Alpha vs SPY" for US tickers
    # while non-US tickers get their regional index automatically.
    "benchmark_ticker": None,
    "benchmark_map": {
        ".NS":  "^NSEI",       # NSE India (Nifty 50)
        ".BO":  "^BSESN",      # BSE India (Sensex)
        ".T":   "^N225",       # Tokyo (Nikkei 225)
        ".HK":  "^HSI",        # Hong Kong (Hang Seng)
        ".L":   "^FTSE",       # London (FTSE 100)
        ".TO":  "^GSPTSE",     # Toronto (TSX Composite)
        ".AX":  "^AXJO",       # Australia (ASX 200)
        ".SS":  "000001.SS",   # Shanghai (SSE Composite)
        ".SZ":  "399001.SZ",   # Shenzhen (SZSE Component)
        "":     "SPY",         # default for US-listed tickers (no suffix)
    },
    # v0.4.0 Phase 2 — scheduled jobs (APScheduler). OFF by default: the webapp
    # only starts the scheduler when enabled, so a normal run is unaffected.
    # ``timezone`` is used for cron interpretation. Settable via
    # TRADINGAGENTS_SCHEDULER_ENABLED / TRADINGAGENTS_SCHEDULER_TIMEZONE.
    "scheduler": {
        "enabled": False,
        "timezone": "Asia/Shanghai",
    },
    # v0.4.0 Phase 2 — poll-based monitoring (no realtime push). OFF by default.
    # ``poll_interval_seconds`` is how often the monitor job re-evaluates rules.
    # Settable via TRADINGAGENTS_MONITOR_ENABLED / TRADINGAGENTS_MONITOR_POLL_SECONDS.
    "monitor": {
        "enabled": False,
        "poll_interval_seconds": 60,
        "market": "hk",           # which market the monitor poll screens
    },
    # v0.4 agentic pipeline. ``agent_loop.enabled=false`` reverts to v0.3 behaviour
    # everywhere (no Orchestrator/DepthController/Re-Analysis, analysts pre-fetch +
    # 1 structured call, route_after_key_question uses analysis_depth).
    "agent_loop": {
        "enabled": True,
        "analyst_max_iterations": 5,
        "analyst_timeout_seconds": 120,
        "pm_max_iterations": 8,             # Phase 5 (not built this round)
        "pm_timeout_seconds": 180,
        "auto_terminate_after_idle": 3,
        "per_analyst": {                    # per-analyst override; false -> v0.3 single call
            "market": {"enabled": True},
            "sentiment": {"enabled": True},
            "news": {"enabled": True},
            "fundamentals": {"enabled": True},
            "industry": {"enabled": True},
        },
    },
    "orchestration": {
        "auto_select_analysts": True,       # false -> skip Orchestrator LLM, run full panel
        "force_all_analysts": False,        # true -> Orchestrator writes a full plan, no LLM call
    },
    "depth_control": {
        "agreement_threshold_conclude": 0.8,
        "agreement_threshold_deep": 0.4,
        "impact_threshold_deep": 7,
    },
    "skills": {
        "enabled": True,
        "path": "~/.tradingagents/skills/",  # user skill dir (built-in always loaded too)
        "auto_load": True,                   # SkillSelector rule-engine auto-pick
        "max_per_analyst": 5,
        "dynamic_request": True,             # allow request_skill tool in the loop
        "max_dynamic_loads": 2,
    },
    "cross_session": {
        "scorecard_driven_selection": True,
        "max_memory_entries": 50,
    },
})
