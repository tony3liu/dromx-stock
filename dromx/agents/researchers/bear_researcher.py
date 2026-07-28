"""Valuation & Risk Analyst — independent parallel report (no debate).

Formerly the "Bear Researcher" in a Bull⇄Bear debate loop. The loop is gone:
this analyst writes ONE independent report from the valuation-and-risk lens and
stops. The Research Manager reads it alongside the Growth & Quality report and
synthesises once. Multi-angle analysis, no persuasion.
"""

from dromx.core.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)


def create_bear_researcher(llm):
    """Create the Valuation & Risk Analyst node (independent report, no debate)."""

    def risk_node(state) -> dict:
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        industry_report = state.get("industry_report", "")
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")
        signal_block = (
            f"\nAggregated analyst signal (consensus, confidence weighting, points "
            f"of disagreement):\n{signal_aggregation}\n"
            if signal_aggregation
            else ""
        )
        key_question = state.get("key_question", "")
        key_question_block = (
            f"\nThe team flagged the pivotal question(s) this call hinges on. "
            f"Concentrate your analysis there:\n{key_question}\n"
            if key_question
            else ""
        )
        industry_block = (
            f"Industry & supply-chain report: {industry_report}\n"
            if industry_report
            else ""
        )
        asset_type = state.get("asset_type", "stock")
        target_label = "stock" if asset_type == "stock" else "asset"
        fundamentals_label = (
            "Company fundamentals report"
            if asset_type == "stock"
            else "Asset fundamentals report (may be unavailable for crypto)"
        )

        prompt = f"""You are a Valuation & Risk Analyst on the investment committee for this {target_label}. Your expertise is assessing whether the current price compensates for the downside: valuation versus fundamentals, balance-sheet fragility, competitive threats, and macro/regulatory headwinds. Write ONE independent, objective report from this lens — you are not debating anyone and not trying to "win". A colleague (the Growth & Quality Analyst) writes a separate report in parallel; the Research Manager will synthesise both. Give the most honest read your lens produces — including where the risk case is WEAK and the margin of safety is actually adequate, not just where it is thin.
{regime_context}
Apply your framework:
- Valuation: does current pricing already discount the growth story? Where is the margin of safety thin or absent?
- Balance-sheet & Fragility: leverage, liquidity, cash-flow quality, refinancing or dilution risk.
- Competitive & Macro Threats: share loss, margin pressure, rate/inflation/regulatory or sector headwinds.
- Honest counter-points: name where the downside case is weak — where valuation is genuinely supported or risks are overstated. Conviction should track the evidence, not your lens.

How to use the shared context: center your analysis on the pivotal question(s) and the points of disagreement the aggregated signal surfaced. Give more weight to high-confidence analysts. Adapt to the market regime above. If a separate industry report is provided, fold the industry cycle / competitive-structure risks into your read.

Resources available:
{instrument_context}
{key_question_block}{signal_block}Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
{industry_block}{fundamentals_label}: {fundamentals_report}
Write your valuation-and-risk report: the most defensible downside/valuation concerns, the points where the risk case is weak, and your overall read. Be specific and data-grounded.
""" + get_language_instruction()

        response = llm.invoke(prompt)

        return {"risk_report": f"Valuation & Risk Analyst:\n{response.content}"}

    return risk_node
