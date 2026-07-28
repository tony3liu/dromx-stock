"""Position Sizing & Reward Specialist — independent parallel risk report (no debate).

Formerly the "aggressive debator" in a three-way risk debate loop. The loop is
gone: this specialist writes ONE independent report from the reward-optimization
lens and stops. Risk Consensus reads all three risk reports and reconciles one
stop framework; the Portfolio Manager decides. Multi-angle, no persuasion.
"""

from dromx.core.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)


def create_aggressive_debator(llm):
    """Create the Position Sizing & Reward Specialist node (independent report)."""

    def reward_node(state) -> dict:
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        trader_decision = state["trader_investment_plan"]
        signal_aggregation = state.get("signal_aggregation", "")
        signal_block = (
            f"\n## Fused scenario distribution & expected value (the desk's shared EV anchor)\n"
            f"{signal_aggregation}\n"
            if signal_aggregation
            else ""
        )

        prompt = f"""You are the Position Sizing & Reward Specialist on the risk committee. Your expertise is position optimization: maximizing expected return per unit of risk. Because that is your discipline, you accept wider risk budgets — but only when the payoff is asymmetric. You are not reckless and you are not an "advocate for risk": you quantify the upside explicitly (ATR-based) and argue for size only when the expected gain genuinely justifies the drawdown. When the risk/reward is not favorable, say so plainly.

Write ONE independent, objective report from this lens — you are not debating anyone. A Tail-Risk specialist and a Regime specialist write separate reports in parallel; the Risk Consensus node reconciles all three into one stop framework and the Portfolio Manager decides. Here is the trader's decision:

{trader_decision}
{regime_context}{signal_block}
Evaluate the trader's decision through the reward-optimization lens. Draw from:

{instrument_context}
Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Ground your case quantitatively, not rhetorically. Read the ATR / volatility figures from the Market Research Report and use them: size the upside scenario explicitly (e.g. "with ATR ≈ X, a 2-3 ATR move to the upside implies +Y%"), and state the stop you would tolerate to chase it.

**Anchor your expected value to the fused scenario distribution above** (the desk's shared EV, built from every analyst's bear/base/bull scenarios). If you compute your own EV with different probability weights, that is allowed — but you MUST state your weights AND explain why they differ from the consensus, so the desk sees one reconciled number, not two contradictory EVs with no explanation. Acknowledge the downside in numbers too, and be honest where the asymmetry is NOT favorable. Output conversationally without special formatting."""
        pos = state.get("position_context", "")
        if pos:
            prompt += f"\n\n**User's current position (for position_simulate):**\n{pos}"
        prompt += get_language_instruction()

        from dromx.dataflows.config import get_config
        agent_cfg = (get_config().get("agent_loop") or {})
        if bool(agent_cfg.get("enabled", False)):
            from dromx.core.agent_loop import build_analyst_react_invoker
            from dromx.core.agent_utils import get_stock_data
            from dromx.agents.managers.portfolio_manager import position_simulate
            report = build_analyst_react_invoker(
                llm=llm, tools=[get_stock_data, position_simulate],
                schema=None, render=lambda c: c,
                agent_name="Position Sizing & Reward Specialist",
                system_message=prompt,
                instruction=(
                    "Evaluate the trader's decision through the reward-optimization lens. "
                    "Use get_stock_data for historical drawdown distribution and "
                    "position_simulate for stop/P&L scenarios, then write the report."
                ),
                max_iterations=int(agent_cfg.get("analyst_max_iterations", 5)),
            )()
        else:
            report = llm.invoke(prompt).content
        return {"reward_risk_report": f"Position Sizing & Reward Specialist:\n{report}"}

    return reward_node
