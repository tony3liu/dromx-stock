"""Risk Consensus — distils the risk debate into one stop-loss framework.

The three risk debators (Reward / Tail-Risk / Regime specialists) each argue
their own stop level, drawdown estimate, and stress scenario in prose. Without
this node the Portfolio Manager stitched those together by hand, with no unified
numbers and no single figure for the position-sizing step to divide into.

This node runs after the risk debate and before the Portfolio Manager. It reads
the full risk-debate history plus the market report (for the ATR anchor) and
emits a structured RiskConsensusReport: one reconciled stop level, its ATR
multiple, the max acceptable drawdown, the key tail risk, and a short framework.
A light structured LLM call (the debate is free-form prose, often non-English,
so regex extraction would be brittle) with a free-text fallback.
"""

from __future__ import annotations

from dromx.agents.schemas import RiskConsensusReport, render_risk_consensus
from dromx.core.agent_utils import (
    get_framework_note_from_state,
    get_instrument_context_from_state,
    get_language_instruction,
    get_numeric_discipline,
    get_regime_context_from_state,
)
from dromx.core.rating import parse_scenarios, suggest_position_size
from dromx.core.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)

# (state key) for each structured analyst report whose scenarios feed sizing.
# Must mirror signal_aggregator._REPORT_LENSES so the Kelly sizer fuses the SAME
# five scenario sets the Signal Aggregator does — otherwise the two EV estimates
# diverge (industry was missing here before PF-2).
_REPORT_KEYS = (
    "market_report", "sentiment_report", "news_report",
    "fundamentals_report", "industry_report",
)


def _sizing_anchor(state) -> str:
    """Deterministic position-size anchor from the fused scenario distribution.

    Re-parses each analyst report's scenario table (same source the Signal
    Aggregator fuses) and runs the fractional-Kelly sizer. Returns a markdown
    line for the PM, or an empty string when no scenarios / no positive edge —
    in which case the PM sizes from the qualitative framework alone.
    """
    pairs: list[tuple[float, float]] = []
    for key in _REPORT_KEYS:
        for _label, prob, magnitude in parse_scenarios(state.get(key) or ""):
            pairs.append((prob, magnitude))
    sizing = suggest_position_size(pairs)
    if not sizing:
        return ""
    return (
        f"\n\n**Suggested position size (sizing anchor):** "
        f"{sizing['low_pct']:.1f}%–{sizing['high_pct']:.1f}% of book "
        f"— {sizing['note']}."
    )


def create_risk_consensus(llm):
    """Create the risk-consensus node (light structured synthesis of the debate)."""
    structured_llm = bind_structured(llm, RiskConsensusReport, "Risk Consensus")

    def risk_consensus_node(state):
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        framework_note = get_framework_note_from_state(state)
        reward_report = state.get("reward_risk_report", "")
        tailrisk_report = state.get("tailrisk_report", "")
        regime_risk_report = state.get("regime_risk_report", "")
        market_report = state.get("market_report", "")

        system_message = f"""You are the risk officer consolidating three independent risk reports into ONE stop-loss framework for the Portfolio Manager. Three specialists analysed the trade from different lenses — Position Sizing & Reward, Tail Risk & Drawdown, and Regime & Macro Context — each writing independently (not a debate). Your job is to reconcile their numbers into a single, usable framework.

{instrument_context}
{framework_note}{regime_context}
## Market report (read the ATR / volatility figures here — anchor the stop to ATR, do not invent levels)
{market_report}

## Position Sizing & Reward report
{reward_report}

## Tail Risk & Drawdown report
{tailrisk_report}

## Regime & Macro Context report
{regime_risk_report}

## How to consolidate

1. **Reconcile the stop.** The three reports may propose different stop levels. Pick ONE recommended stop, leaning to the more protective level when they disagree materially. Express it both as a price and as a multiple of ATR (read ATR from the market report).
2. **Set the max acceptable drawdown** (a positive percent, e.g. 18 for −18%), reconciled across the reports — this is the unit of risk the position-sizing step will divide into.
3. **Name the single key tail risk** the stop is actually protecting against.
4. **Write the framework** (2-4 sentences): where the reports agreed, and how you reconciled the level where they did not.

Fill the structured fields: recommended_stop, stop_atr_multiple, max_drawdown_pct, key_risk, framework. If a number genuinely cannot be derived from the reports, leave it null rather than inventing it.
{get_numeric_discipline()}
{get_language_instruction()}"""

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            system_message,
            render_risk_consensus,
            "Risk Consensus",
            schema=RiskConsensusReport,
        )

        # Deterministic sizing anchor appended after the LLM synthesis, so the PM
        # gets a Kelly-based range it can anchor to (or deviate from with reason).
        report_text += _sizing_anchor(state)

        return {"risk_consensus": report_text}

    return risk_consensus_node
