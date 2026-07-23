"""Growth & Quality Analyst — independent parallel report (no debate).

Formerly the "Bull Researcher" in a Bull⇄Bear debate loop. The debate form
itself manufactured adversarial framing ("respond to the other's points") even
after the role was recast as a specialist. We removed the loop entirely: this
analyst now writes ONE independent report from the growth-and-quality lens and
stops. The Research Manager reads this report alongside the Valuation & Risk
report and synthesises once — multi-angle analysis without the rhetoric of
persuasion.
"""

from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)


def create_bull_researcher(llm):
    """Create the Growth & Quality Analyst node (independent report, no debate)."""

    def growth_node(state) -> dict:
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

        prompt = f"""You are a Growth & Quality Analyst on the investment committee for this {target_label}. Your expertise is evaluating growth trajectories, competitive moats, revenue scalability, earnings quality, and positive catalysts. Write ONE independent, objective report from this lens — you are not debating anyone and not trying to "win". A colleague (the Valuation & Risk Analyst) writes a separate report in parallel; the Research Manager will synthesise both. Your job is to give the most honest, evidence-grounded read your lens produces — including where the growth-and-quality case is WEAK, not just where it is strong.
{regime_context}
Apply your framework:
- Growth Potential: market opportunity, revenue trajectory, scalability — how durable and how well-evidenced?
- Competitive Advantages: moat, pricing power, branding, market position — real and widening, or eroding?
- Quality & Positive Catalysts: earnings quality, balance-sheet strength, industry tailwinds, recent positive developments.
- Honest weaknesses: name the points where the growth/quality thesis is thin or unsupported by the data. Conviction should track the evidence, not your lens.

How to use the shared context: center your analysis on the pivotal question(s) and the points of disagreement the aggregated signal surfaced — that is where the call is decided. Give more weight to high-confidence analysts. Adapt to the market regime above. If a separate industry report is provided, fold the industry cycle / competitive-structure view into your growth read.

Resources available:
{instrument_context}
{key_question_block}{signal_block}Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
{industry_block}{fundamentals_label}: {fundamentals_report}
Write your growth-and-quality report: the strongest evidence for the constructive case, the honest weaknesses, and your overall read. Be specific and data-grounded.
""" + get_language_instruction()

        response = llm.invoke(prompt)

        return {"growth_report": f"Growth & Quality Analyst:\n{response.content}"}

    return growth_node
