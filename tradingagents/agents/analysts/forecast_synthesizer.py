"""Forecast Synthesizer — a time-layered prediction node before the PM.

Every prior node answers "what is true now". A senior desk also wants "what to
expect, and when": tomorrow, next week, next month, next quarter — each with a
range, the trigger that decides it, a falsification condition, and a confidence
that reflects how good the inputs actually are.

This node runs after Risk Consensus (so it has the consolidated stop / ATR
multiple / Kelly anchor) and before the PM. It reads every artifact and makes one
structured LLM call. Short horizons (T+1/T+5) are anchored to ATR + technical
levels + the event calendar; long horizons (T+20/T+60) to the regime + industry
cycle + competitive structure. Same pre-fetch + free-text-fallback pattern as the
other synthesis nodes (key_question, event_impact).
"""

from __future__ import annotations

from tradingagents.agents.schemas import ForecastReport, render_forecast_report
from tradingagents.agents.utils.agent_utils import (
    get_framework_note_from_state,
    get_instrument_context_from_state,
    get_language_instruction,
    get_numeric_discipline,
    get_regime_context_from_state,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_forecast_synthesizer(llm):
    """Create the forecast-synthesis node (single structured call over state)."""
    structured_llm = bind_structured(llm, ForecastReport, "Forecast Synthesizer")

    def forecast_node(state):
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        framework_note = get_framework_note_from_state(state)

        def block(key, label):
            v = state.get(key, "")
            return f"\n## {label}\n{v}\n" if v else ""

        context = (
            block("signal_aggregation", "Fused signal (consensus, EV, payoff skew, scores)")
            + block("event_impact", "Event impact / premise-shift")
            + block("key_question", "Key question")
            + block("risk_consensus", "Risk consensus (unified stop, ATR multiple, Kelly sizing)")
            + block("overnight_transmission", "Overnight transmission (cross-market lead: US → underlying → listing open, with leverage-derived expected open)")
            + block("pattern_discovery", "Pattern discovery (anomaly days + pivot-vs-anchor deviation competition + algorithmic-precision verdict + evolution — forensics evidence, direction-neutral)")
        )

        system_message = f"""You are a senior strategist producing a TIME-LAYERED forecast for {state.get("company_of_interest", "this name")}. The desk already knows what is true now; your job is what to expect, and when — at T+1 (next session), T+5 (one week), T+20 (one month), T+60 (one quarter).

{instrument_context}
{framework_note}{regime_context}{context}
## The five analyst reports
### Technical / market (read ATR, levels, recent closes here for the short horizons)
{state.get("market_report", "")}

### Sentiment
{state.get("sentiment_report", "")}

### News / macro (event calendar lives here)
{state.get("news_report", "")}

### Fundamentals
{state.get("fundamentals_report", "")}

### Industry / supply chain (cycle + competitive structure for the long horizons)
{state.get("industry_report", "")}

## How to forecast

1. **Short horizons (T+1, T+5) — quantitative, not narrative.** Anchor the range to ATR (≈1σ from the latest close for T+1; widen for T+5) and the technical support/resistance in the market report. Drive them off the event CALENDAR (earnings, filings, scheduled releases) and the event-impact flag, NOT a story. When the overnight transmission block is present, anchor T+1 to its leverage-derived expected open (underlying overnight move × leverage) — a cross-market ETF's next-session open is set by the lead market, not by yesterday's own close. For an event-driven week (T+5), branch into scenarios (e.g. by the size of a pending dilution / the direction of a print).
2. **Long horizons (T+20, T+60) — structural, not momentum.** Frame these from the regime + industry cycle position + competitive moat + key dependencies, NOT short-term price momentum. T+60 is about where the industry is in its cycle and who is winning, not this week's candles.
3. **Confidence must track input quality.** Lower a horizon's confidence explicitly when a relevant lens was missing or weak, when the horizon hinges on an undisclosed event, or when the regime is unstable. Do not output uniform 'high' across all four.
4. **Every horizon needs a falsification** — a concrete, observable condition, at that horizon's timescale, that would prove the forecast wrong.
5. **Use the Risk Consensus ATR / stop** for the downside bound of the short-horizon ranges so the forecast and the risk framework agree.

Fill the structured fields: horizons (exactly four: T+1, T+5, T+20, T+60, each with price_range, direction, most_likely, scenarios (optional), key_trigger_or_calendar, falsification, confidence), scenario_table (the name-level bear/base/bull PRICE distribution — one row per leg with price_range + probability + trigger; fill when the call is event-driven enough to branch, e.g. a pending dilution / earnings print / transmission break, else leave empty), and fused_expected_path (one path sentence stitching the horizons together).
{get_numeric_discipline()}
{get_language_instruction()}"""

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            system_message,
            render_forecast_report,
            "Forecast Synthesizer",
            schema=ForecastReport,
        )

        return {"forecast_report": report_text}

    return forecast_node
