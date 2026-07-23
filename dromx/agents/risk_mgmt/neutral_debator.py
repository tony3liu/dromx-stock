"""Regime & Macro Context Specialist — independent parallel risk report (no debate).

Formerly the "neutral debator" in a three-way risk debate loop. The loop is
gone: this specialist writes ONE independent report from the regime-conditional
lens and stops. Risk Consensus reconciles all three risk reports; the PM decides.
"""

from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)


def create_neutral_debator(llm):
    """Create the Regime & Macro Context Specialist node (independent report)."""

    def regime_risk_node(state) -> dict:
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        trader_decision = state["trader_investment_plan"]

        prompt = f"""You are the Regime & Macro Context Specialist on the risk committee. Your expertise is regime-conditional analysis: judging whether the CURRENT market environment amplifies or dampens the risks and rewards in play. You adjust conviction by volatility regime, macro backdrop, and cross-asset signals.

Write ONE independent, objective report from this lens — you are not debating anyone. A Reward specialist and a Tail-Risk specialist write separate reports in parallel; the Risk Consensus node reconciles all three into one stop framework and the Portfolio Manager decides. Rather than rebutting them, state which KIND of risk framework this regime favors (reward-taking vs downside-protection) and why. Here is the trader's decision:

{trader_decision}
{regime_context}
Evaluate the trader's decision through the regime lens. Use:

{instrument_context}
Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Anchor your read in numbers. Read the ATR / volatility figures from the Market Research Report and frame a regime-conditioned expected range (e.g. "in this volatility regime, ±1.5 ATR ≈ ±X% over the horizon"). Propose the position size and stop the current regime warrants, and state explicitly how that would shift if the regime changed (e.g. vol expands, trend breaks). Where the regime is ambiguous, say so rather than splitting the difference. Output conversationally without special formatting."""
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
                agent_name="Regime & Macro Context Specialist",
                system_message=prompt,
                instruction=(
                    "Evaluate the trader's decision through the regime/macro lens. "
                    "Use get_stock_data for historical regime-conditioned range and "
                    "position_simulate for position/stop scenarios, then write the report."
                ),
                max_iterations=int(agent_cfg.get("analyst_max_iterations", 5)),
            )()
        else:
            report = llm.invoke(prompt).content
        return {"regime_risk_report": f"Regime & Macro Context Specialist:\n{report}"}

    return regime_risk_node
