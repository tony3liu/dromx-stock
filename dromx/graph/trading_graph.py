# DromX/graph/trading_graph.py

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf

# Instrument-identity helpers (the data tools themselves now live inside the
# analyst nodes, which pre-fetch via ``.func(...)`` — the graph no longer wires
# per-analyst ToolNodes).
from dromx.core.agent_utils import (
    build_instrument_context,
    resolve_instrument_identity,
)
from dromx.core.memory import TradingMemoryLog
from dromx.core.signal_tracker import AnalystScorecard
from dromx.dataflows.config import set_config
from dromx.dataflows.utils import safe_ticker_component
from dromx.default_config import DEFAULT_CONFIG
from dromx.llm_clients import create_llm_client
from dromx.reporting import write_report_tree

from .checkpointer import checkpoint_step, clear_checkpoint, get_checkpointer, thread_id
from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .reflection import Reflector
from .setup import GraphSetup
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


class DromXGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=("market", "social", "news", "fundamentals", "industry"),
        debug=False,
        config: dict[str, Any] = None,
        callbacks: list | None = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        # Initialize LLMs with provider-specific thinking configuration
        llm_kwargs = self._get_provider_kwargs()

        # Add callbacks to kwargs if provided (passed to LLM constructor)
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        self.memory_log = TradingMemoryLog(self.config)
        self.scorecard = AnalystScorecard(self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.conditional_logic,
        )

        self.propagator = Propagator(
            max_recur_limit=self.config.get("max_recur_limit", 100),
        )
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph: keep the workflow for recompilation with a checkpointer.
        self.workflow = self.graph_setup.setup_graph(selected_analysts)
        self.graph = self.workflow.compile()
        self._checkpointer_ctx = None

    def _get_provider_kwargs(self) -> dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        elif provider == "anthropic":
            effort = self.config.get("anthropic_effort")
            if effort:
                kwargs["effort"] = effort

        # Sampling temperature is cross-provider: forward it whenever set.
        # float() here so a value coming from a DROMX_TEMPERATURE env
        # string ("0.2") works the same as a programmatic float.
        temperature = self.config.get("temperature")
        if temperature is not None and temperature != "":
            kwargs["temperature"] = float(temperature)

        return kwargs

    def _create_tool_nodes(self) -> dict:
        """Tool nodes for the analyst graph.

        Since v0.3.x the analysts pre-fetch their data and emit structured
        output in a single LLM call (no tool-calling loop), so they no longer
        need per-analyst ToolNodes. The data tools are still imported and used
        directly (via ``.func(...)``) inside the analyst nodes. This returns an
        empty mapping; it is kept so the GraphSetup constructor signature and any
        external callers stay stable.
        """
        return {}

    def _resolve_benchmark(self, ticker: str) -> str:
        """Pick the benchmark ticker for alpha calculation against ``ticker``.

        ``config["benchmark_ticker"]`` overrides everything when set; otherwise
        the suffix map matches the ticker's exchange suffix (e.g. ``.T`` for
        Tokyo). US-listed tickers without a dotted suffix fall through to the
        empty-suffix entry (SPY by default). Unrecognised suffixes (including
        US tickers with dots like ``BRK.B``) also fall back to the empty-suffix
        entry, which is the right default because the alpha calculation works
        in USD.
        """
        explicit = self.config.get("benchmark_ticker")
        if explicit:
            return explicit
        benchmark_map = self.config.get("benchmark_map", {})
        ticker_upper = ticker.upper()
        for suffix, benchmark in benchmark_map.items():
            if suffix and ticker_upper.endswith(suffix.upper()):
                return benchmark
        return benchmark_map.get("", "SPY")

    def _fetch_returns(
        self, ticker: str, trade_date: str, holding_days: int = 5,
        benchmark: str = "SPY",
    ) -> tuple[float | None, float | None, int | None]:
        """Fetch raw and alpha return for ticker over holding_days from trade_date.

        ``benchmark`` is the index used as the alpha baseline (resolved by the
        caller via ``_resolve_benchmark``). Returns ``(raw_return, alpha_return,
        actual_holding_days)`` or ``(None, None, None)`` if price data is
        unavailable (too recent, delisted, or network error).
        """
        from dromx.dataflows.symbol_utils import normalize_symbol

        try:
            start = datetime.strptime(trade_date, "%Y-%m-%d")
            end = start + timedelta(days=holding_days + 7)  # buffer for weekends/holidays
            end_str = end.strftime("%Y-%m-%d")

            # Normalize so the realized-return lookup hits the same instrument
            # the analysis priced (e.g. XAUUSD -> GC=F) (#984). The benchmark is
            # already a canonical Yahoo symbol from ``_resolve_benchmark``.
            stock = yf.Ticker(normalize_symbol(ticker)).history(start=trade_date, end=end_str)
            bench = yf.Ticker(benchmark).history(start=trade_date, end=end_str)

            if len(stock) < 2 or len(bench) < 2:
                return None, None, None

            actual_days = min(holding_days, len(stock) - 1, len(bench) - 1)
            raw = float(
                (stock["Close"].iloc[actual_days] - stock["Close"].iloc[0])
                / stock["Close"].iloc[0]
            )
            bench_ret = float(
                (bench["Close"].iloc[actual_days] - bench["Close"].iloc[0])
                / bench["Close"].iloc[0]
            )
            alpha = raw - bench_ret
            return raw, alpha, actual_days
        except Exception as e:
            logger.warning(
                "Could not resolve outcome for %s on %s vs %s (will retry next run): %s",
                ticker, trade_date, benchmark, e,
            )
            return None, None, None

    def _resolve_pending_entries(self, ticker: str) -> None:
        """Resolve pending log entries for ticker at the start of a new run.

        Fetches returns for each same-ticker pending entry, generates reflections,
        then writes all updates in a single atomic batch write to avoid redundant I/O.
        Skips entries whose price data is not yet available (too recent or delisted).

        Trade-off: only same-ticker entries are resolved per run.  Entries for
        other tickers accumulate until that ticker is run again.
        """
        pending = [e for e in self.memory_log.get_pending_entries() if e["ticker"] == ticker]
        if not pending:
            return

        benchmark = self._resolve_benchmark(ticker)
        updates = []
        for entry in pending:
            raw, alpha, days = self._fetch_returns(
                ticker, entry["date"], benchmark=benchmark,
            )
            if raw is None:
                continue  # price not available yet — try again next run
            # Score each analyst's directional signal for this entry against the
            # realized return (signal-level scorecard, separate from the
            # decision-level reflection below).
            self.scorecard.resolve(ticker, entry["date"], raw)
            reflection = self.reflector.reflect_on_final_decision(
                final_decision=entry.get("decision", ""),
                raw_return=raw,
                alpha_return=alpha,
                benchmark_name=benchmark,
            )
            updates.append({
                "ticker": ticker,
                "trade_date": entry["date"],
                "raw_return": raw,
                "alpha_return": alpha,
                "holding_days": days,
                "reflection": reflection,
            })

        if updates:
            self.memory_log.batch_update_with_outcomes(updates)

    def resolve_instrument_context(self, ticker: str, asset_type: str = "stock") -> str:
        """Resolve ticker identity once and return the full instrument context.

        Deterministic yfinance lookup (cached, fail-open) injected into a
        context string so every agent anchors to the real company instead of
        hallucinating one from the price chart (#814). Both the propagate()
        path and the CLI call this so the resolved identity reaches the whole
        graph regardless of entry point.
        """
        identity = resolve_instrument_identity(ticker)
        return build_instrument_context(ticker, asset_type, identity)

    def _build_portfolio_context(self, ticker: str, trade_date: str) -> str:
        """Pre-trade portfolio-interaction context, or '' when no holdings configured.

        Best-effort and fully degrading (the builder swallows fetch failures), so
        a configured but unreachable holding never blocks the run.
        """
        try:
            from dromx.agents.portfolio.portfolio_context import (
                build_portfolio_context,
                parse_holdings,
            )

            holdings = parse_holdings(self.config.get("holdings"))
            if not holdings:
                return ""
            return build_portfolio_context(
                ticker, str(trade_date), holdings, llm=self.quick_thinking_llm
            )
        except Exception as exc:  # noqa: BLE001 — portfolio context is best-effort
            logger.warning("Portfolio context unavailable for %s: %s", ticker, exc)
            return ""

    def _build_market_context(self, ticker: str, trade_date: str) -> str:
        """Cross-validation block (move vs index vs peers), or '' on failure.

        Best-effort and fully degrading so a missing benchmark/peer never blocks
        the run.
        """
        try:
            from dromx.dataflows.market_context import build_market_context

            return build_market_context(ticker, str(trade_date), self.config)
        except Exception as exc:  # noqa: BLE001 — market context is best-effort
            logger.warning("Market context unavailable for %s: %s", ticker, exc)
            return ""

    def _build_overnight_transmission(self, ticker: str, trade_date: str) -> str:
        """Cross-market overnight transmission block, or '' on failure.

        Stitches the US-overnight → underlying-morning → listing-open chain for
        a cross-market ETF (leverage-derived expected open + transmission
        intact/broken flag). Best-effort and fully degrading: a non-ETF, a
        same-market fund, an LLM "no link" verdict, or any fetch failure yields
        '' so the run is never blocked. See ``dataflows.overnight_transmission``.
        """
        try:
            from dromx.dataflows.overnight_transmission import (
                build_overnight_transmission,
            )

            return build_overnight_transmission(
                ticker, str(trade_date), self.config, llm=self.quick_thinking_llm
            )
        except Exception as exc:  # noqa: BLE001 — overnight transmission is best-effort
            logger.warning("Overnight transmission unavailable for %s: %s", ticker, exc)
            return ""

    def _build_pattern_discovery(self, ticker: str, trade_date: str) -> str:
        """Forensics discovery block (anomaly → reverse anchor → precision), or ''.

        Deterministic (no LLM): finds anomaly days, competes candidate anchors
        (MA/prior/round-number) by deviation from each day's pivot low, and
        flags algorithmic-precision evidence. The anchor is discovered, not
        assumed. Best-effort and fully degrading: a normal tape or thin data
        yields '' so the run is never blocked. See ``dataflows.pattern_discovery``.
        """
        try:
            from dromx.dataflows.pattern_discovery import (
                build_pattern_discovery,
            )

            return build_pattern_discovery(ticker, str(trade_date), self.config)
        except Exception as exc:  # noqa: BLE001 — pattern discovery is best-effort
            logger.warning("Pattern discovery unavailable for %s: %s", ticker, exc)
            return ""

    def _build_foreign_flow(self, ticker: str, trade_date: str) -> str:
        """Foreign-flow (chip) block — Naver foreign ownership + net trading, or ''.

        Korea-only: foreign-ownership% snapshot + daily net-trading series with a
        consecutive net-sell/buy-days flag (the case study's lead indicator).
        Best-effort and fully degrading: non-Korea tickers or fetch failure yield
        '' so the run is never blocked. See ``dataflows.naver``.
        """
        try:
            from dromx.dataflows.naver import build_foreign_flow

            return build_foreign_flow(ticker, str(trade_date), self.config)
        except Exception as exc:  # noqa: BLE001 — foreign flow is best-effort
            logger.warning("Foreign flow unavailable for %s: %s", ticker, exc)
            return ""

    def _resolve_instrument_type(self, ticker: str, trade_date: str) -> tuple[str, str]:
        """Resolve the instrument TYPE once at run start so downstream agents pick
        the right analysis framework (a 2x ETF must not be analysed like a stock).

        Returns ``(instrument_type, framework_note)``: type is
        equity/etf/leveraged_etf/inverse_etf; framework_note is the injected
        instruction block (empty for a plain equity). Best-effort — any failure
        degrades to ("equity", "") so the run is never blocked.
        """
        try:
            from dromx.dataflows.etf_data import resolve_etf_structure

            struct = resolve_etf_structure(ticker, str(trade_date), llm=self.quick_thinking_llm)
            return struct.instrument_type(), struct.framework_note()
        except Exception as exc:  # noqa: BLE001 — type resolution is best-effort
            logger.warning("Instrument-type resolution failed for %s: %s", ticker, exc)
            return "equity", ""

    def propagate(self, company_name, trade_date, asset_type: str = "stock"):
        """Run the trading agents graph for a company on a specific date.

        ``asset_type`` selects between the stock pipeline (default) and the
        crypto pipeline (``"crypto"``) shipped in #567 — the CLI auto-detects
        from the ticker; programmatic callers pass it explicitly. When
        ``checkpoint_enabled`` is set in config, the graph is recompiled with
        a per-ticker SqliteSaver so a crashed run can resume from the last
        successful node on a subsequent invocation with the same ticker+date.
        """
        self.ticker = company_name

        # Resolve any pending memory-log entries for this ticker before the pipeline runs.
        self._resolve_pending_entries(company_name)

        # Recompile with a checkpointer if the user opted in.
        if self.config.get("checkpoint_enabled"):
            self._checkpointer_ctx = get_checkpointer(
                self.config["data_cache_dir"], company_name
            )
            saver = self._checkpointer_ctx.__enter__()
            self.graph = self.workflow.compile(checkpointer=saver)

            step = checkpoint_step(
                self.config["data_cache_dir"], company_name, str(trade_date)
            )
            if step is not None:
                logger.info(
                    "Resuming from step %d for %s on %s", step, company_name, trade_date
                )
            else:
                logger.info("Starting fresh for %s on %s", company_name, trade_date)

        try:
            return self._run_graph(company_name, trade_date, asset_type=asset_type)
        finally:
            if self._checkpointer_ctx is not None:
                self._checkpointer_ctx.__exit__(None, None, None)
                self._checkpointer_ctx = None
                self.graph = self.workflow.compile()

    def save_reports(self, final_state, ticker, save_path=None) -> Path:
        """Write the markdown report tree for a completed run, like the CLI does.

        Programmatic callers get the same on-disk reports the CLI produces. Pass
        an explicit ``save_path`` or let it default under ``results_dir``.
        """
        if save_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = (
                Path(self.config["results_dir"])
                / "reports"
                / f"{safe_ticker_component(ticker)}_{stamp}"
            )
        return write_report_tree(final_state, ticker, save_path)

    def _run_graph(self, company_name, trade_date, asset_type: str = "stock"):
        """Execute the graph and write the resulting state to disk and memory log."""
        # Initialize state — inject memory log context for PM and the
        # deterministically resolved instrument identity for all agents.
        # 8 项上下文互相独立（纯查询，各自 degrade），并行预取省掉整条串行链。
        from dromx.graph.prefetch import parallel_prefetch

        ctx = parallel_prefetch({
            "past_context": lambda: self.memory_log.get_past_context(company_name),
            "instrument_context": lambda: self.resolve_instrument_context(company_name, asset_type),
            "portfolio_context": lambda: self._build_portfolio_context(company_name, trade_date),
            "market_context": lambda: self._build_market_context(company_name, trade_date),
            "overnight_context": lambda: self._build_overnight_transmission(company_name, trade_date),
            "pattern_context": lambda: self._build_pattern_discovery(company_name, trade_date),
            "foreign_flow": lambda: self._build_foreign_flow(company_name, trade_date),
            "instrument_type": lambda: self._resolve_instrument_type(company_name, trade_date),
        }, label=f"run-start context({company_name})")
        instrument_type, framework_note = ctx["instrument_type"]
        init_agent_state = self.propagator.create_initial_state(
            company_name,
            trade_date,
            asset_type=asset_type,
            past_context=ctx["past_context"],
            instrument_context=ctx["instrument_context"],
            portfolio_context=ctx["portfolio_context"],
            market_context=ctx["market_context"],
            overnight_transmission=ctx["overnight_context"],
            pattern_discovery=ctx["pattern_context"],
            foreign_flow=ctx["foreign_flow"],
            instrument_type=instrument_type,
            framework_note=framework_note,
        )
        args = self.propagator.get_graph_args()

        # Inject thread_id so same ticker+date resumes, different date starts fresh.
        if self.config.get("checkpoint_enabled"):
            tid = thread_id(company_name, str(trade_date))
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = tid

        if self.debug:
            trace = []
            last_printed = None
            for chunk in self.graph.stream(init_agent_state, **args):
                if chunk["messages"]:
                    msg = chunk["messages"][-1]
                    # Nodes after the trader don't append to messages, so the
                    # same trailing message repeats across chunks. Print it only
                    # when it changes (#1027); the trace/state merge is unchanged.
                    signature = (type(msg).__name__, getattr(msg, "content", None))
                    if signature != last_printed:
                        msg.pretty_print()
                        last_printed = signature
                    trace.append(chunk)
            # Streamed chunks are per-node deltas. Merge them so the returned
            # state matches what graph.invoke() yields in the non-debug path.
            final_state = {}
            for chunk in trace:
                final_state.update(chunk)
        else:
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection.
        self.curr_state = final_state

        # Log state to disk.
        self._log_state(trade_date, final_state)

        # Store decision for deferred reflection on the next same-ticker run.
        self.memory_log.store_decision(
            ticker=company_name,
            trade_date=trade_date,
            final_trade_decision=final_state["final_trade_decision"],
        )

        # Record each analyst's directional signal (with the regime) so the next
        # same-ticker run can score it once the realized return is known.
        self.scorecard.record_run(company_name, str(trade_date), final_state)

        # Clear checkpoint on successful completion to avoid stale state.
        if self.config.get("checkpoint_enabled"):
            clear_checkpoint(
                self.config["data_cache_dir"], company_name, str(trade_date)
            )

        return final_state, self.process_signal(final_state["final_trade_decision"])

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "aggressive_history": final_state["risk_debate_state"]["aggressive_history"],
                "conservative_history": final_state["risk_debate_state"]["conservative_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file. Reject ticker values that would escape the
        # results directory when joined as a path component.
        safe_ticker = safe_ticker_component(self.ticker)
        directory = Path(self.config["results_dir"]) / safe_ticker / "DromXStrategy_logs"
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"full_states_log_{trade_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_states_dict[str(trade_date)], f, indent=4)

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
