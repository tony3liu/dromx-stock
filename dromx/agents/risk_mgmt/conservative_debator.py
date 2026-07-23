"""Tail Risk & Drawdown Protection Specialist — independent parallel risk report.

Formerly the "conservative debator" in a three-way risk debate loop. The loop is
gone: this specialist writes ONE independent report from the downside-protection
lens and stops. Risk Consensus reconciles all three risk reports; the PM decides.
"""

from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)


def create_conservative_debator(llm):
    """Create the Tail Risk & Drawdown Protection Specialist node (independent report)."""

    def tailrisk_node(state) -> dict:
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        trader_decision = state["trader_investment_plan"]

        prompt = f"""You are the Tail Risk & Drawdown Protection Specialist on the risk committee. Your expertise is downside protection: identifying worst-case scenarios, correlation and concentration risk, hidden leverage, and liquidity traps. You are not simply "anti-risk" — you pinpoint which specific risks are underpriced and argue for hedges or size reduction only against those specific exposures. When the risk/reward is genuinely favorable, you say so.

Write ONE independent, objective report from this lens — you are not debating anyone. A Reward specialist and a Regime specialist write separate reports in parallel; the Risk Consensus node reconciles all three into one stop framework and the Portfolio Manager decides. Here is the trader's decision:

{trader_decision}
{regime_context}
Evaluate the trader's decision through the downside-protection lens. Draw from:

{instrument_context}
Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Quantify the downside, do not just assert it. Read the ATR / volatility figures from the Market Research Report and translate them into concrete loss estimates: a realistic max-drawdown scenario (e.g. "a 3 ATR adverse move ≈ −X%; on the stated position size that is a $Y loss"), and the stop level you would insist on. Run at least one stress scenario (a macro shock, an earnings miss, a regime shift to higher volatility) and estimate its impact in percentage and currency terms. In a high-volatility regime, argue for smaller size and wider stops with the numbers. Name the specific underpriced risks rather than blanket caution, and acknowledge where the margin of safety is genuinely adequate. Output conversationally without special formatting."""
        pos = state.get("position_context", "")
        if pos:
            prompt += f"\n\n**User's current position (for position_simulate):**\n{pos}"
        prompt += get_language_instruction()

        from dromx.dataflows.config import get_config
        agent_cfg = (get_config().get("agent_loop") or {})
        if bool(agent_cfg.get("enabled", False)):
            from dromx.agents.utils.agent_loop import build_analyst_react_invoker
            from dromx.agents.utils.agent_utils import get_stock_data
            from dromx.agents.managers.portfolio_manager import position_simulate
            report = build_analyst_react_invoker(
                llm=llm, tools=[get_stock_data, position_simulate],
                schema=None, render=lambda c: c,
                agent_name="Tail Risk & Drawdown Specialist",
                system_message=prompt,
                instruction=(
                    "Evaluate the trader's decision through the tail-risk/drawdown lens. "
                    "Use get_stock_data for historical max-drawdown distribution and "
                    "position_simulate for stop/stress P&L scenarios, then write the report."
                ),
                max_iterations=int(agent_cfg.get("analyst_max_iterations", 5)),
            )()
        else:
            report = llm.invoke(prompt).content
        return {"tailrisk_report": f"Tail Risk & Drawdown Specialist:\n{report}"}

    return tailrisk_node
