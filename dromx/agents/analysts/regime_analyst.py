"""Regime detection — a lightweight market-state node that runs before the analysts.

Professional research frames a name against the prevailing environment before
diving in: a trend-following technical setup means something different in a
choppy, high-volatility tape than in a clean uptrend. This node answers "what
regime are we in?" once, up front, and hands the downstream analyst team a
weighting hint so each lens (technical / fundamental / sentiment / news) can be
emphasised or discounted accordingly.

Design mirrors the Sentiment Analyst: it PRE-FETCHES a deterministic market
snapshot (the same ``build_verified_market_snapshot`` the market analyst trusts
as ground truth) for the instrument and, when distinct, its benchmark index,
then makes a single structured LLM call. No tool-calling loop — which keeps the
node cheap and, crucially, lets it run as a parallel fan-out source alongside
the analysts without contending on the shared ``messages`` channel.
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from tradingagents.agents.schemas import RegimeReport, render_regime_report
from tradingagents.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.market_data_validator import build_verified_market_snapshot

logger = logging.getLogger(__name__)


def _safe_snapshot(symbol: str, curr_date: str) -> str:
    """Verified snapshot for ``symbol``, or a clear placeholder on any failure.

    The regime node must never abort the run — a missing benchmark or a thinly
    traded name should degrade to a placeholder the LLM can reason about, the
    same graceful-degradation contract the sentiment fetchers follow.
    """
    try:
        return build_verified_market_snapshot(symbol, curr_date, look_back_days=30)
    except Exception as exc:  # noqa: BLE001 — degrade, don't crash the pipeline
        logger.warning("Regime snapshot unavailable for %s: %s", symbol, exc)
        return f"<snapshot unavailable for {symbol}: {type(exc).__name__}>"


def create_regime_analyst(llm):
    """Create the regime-detection node for the trading graph.

    Pre-fetches verified snapshots for the instrument (and its benchmark when
    different), injects them into the prompt, and produces a deterministic
    structured ``RegimeReport`` with a free-text fallback.
    """
    structured_llm = bind_structured(llm, RegimeReport, "Regime Analyst")

    def regime_analyst_node(state):
        ticker = state["company_of_interest"]
        curr_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)

        benchmark = str(get_config().get("benchmark_ticker") or "").strip()

        instrument_snapshot = _safe_snapshot(ticker, curr_date)
        benchmark_block = ""
        if benchmark and benchmark.upper() != ticker.upper():
            benchmark_snapshot = _safe_snapshot(benchmark, curr_date)
            benchmark_block = (
                f"\n### Benchmark snapshot — {benchmark} (broad-market context)\n"
                f"<start_of_benchmark>\n{benchmark_snapshot}\n<end_of_benchmark>\n"
            )

        system_message = _build_system_message(
            ticker=ticker,
            curr_date=curr_date,
            instrument_snapshot=instrument_snapshot,
            benchmark_block=benchmark_block,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a market-regime analyst running before the rest of the"
                    " research team. Today's date is {current_date}; treat it as 'now'."
                    " {instrument_context}\n{system_message}",
                ),
            ]
        )
        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=curr_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        formatted_messages = prompt.format_messages()

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            formatted_messages,
            render_regime_report,
            "Regime Analyst",
            schema=RegimeReport,
        )

        return {
            "messages": [AIMessage(content=report_text)],
            "regime_report": report_text,
        }

    return regime_analyst_node


def _build_system_message(
    *,
    ticker: str,
    curr_date: str,
    instrument_snapshot: str,
    benchmark_block: str,
) -> str:
    """Assemble the regime-analyst system message with the verified snapshot blocks."""
    return f"""Classify the current market regime for {ticker} as of {curr_date}, so the downstream analyst team knows how to weight their lenses.

You are given verified, deterministic market snapshots (latest OHLCV row, moving averages, RSI, MACD, ATR, recent closes). Treat these numbers as ground truth — base your classification on them, do not invent levels.

### Instrument snapshot — {ticker}
<start_of_instrument>
{instrument_snapshot}
<end_of_instrument>
{benchmark_block}
## How to classify

1. **Trend direction.** Uptrend: price holds above rising 50/200 SMAs and the 10 EMA leads higher. Downtrend: price below falling averages. Sideways: price oscillates around flat averages with no clear slope.

2. **Volatility level.** Judge from ATR and the recent high-low range relative to price. High: ATR/range elevated vs the trailing norm (breakouts can run, stops must be wider). Low: unusually compressed (mean-reversion more reliable, breakouts suspect). Normal otherwise.

3. **Weighting hint.** Translate the regime into concrete guidance for the analysts:
   - Trending + normal/low vol → favour technical momentum signals; treat mean-reversion setups skeptically.
   - Range-bound → lean on fundamentals/valuation; discount technical breakouts.
   - High vol (any trend) → widen risk tolerances, expect the risk debate to matter more, discount precise short-term price targets.

4. **Be honest about uncertainty.** If the snapshot is sparse (newly listed, few rows) or signals conflict, set confidence to 'low' and say so.

{get_language_instruction()}"""
