# TradingAgents/graph/propagation.py

from typing import Any

from tradingagents.agents.utils.agent_states import (
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self,
        company_name: str,
        trade_date: str,
        asset_type: str = "stock",
        past_context: str = "",
        instrument_context: str = "",
        portfolio_context: str = "",
        market_context: str = "",
        overnight_transmission: str = "",
        pattern_discovery: str = "",
        foreign_flow: str = "",
        instrument_type: str = "equity",
        framework_note: str = "",
        position_context: str = "",
    ) -> dict[str, Any]:
        """Create the initial state for the agent graph.

        ``instrument_context`` is the deterministic ticker-identity string
        resolved once at run start (see
        ``TradingAgentsGraph.resolve_instrument_context``). When empty, agents
        fall back to ticker-only context via
        ``get_instrument_context_from_state``. ``portfolio_context`` is the
        pre-trade holdings-interaction block (empty when no holdings configured).
        ``instrument_type`` / ``framework_note`` select the analysis framework so
        a fund wrapper (e.g. a 2x ETF) is not analysed like a company.
        """
        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "asset_type": asset_type,
            "instrument_context": instrument_context,
            "trade_date": str(trade_date),
            "past_context": past_context,
            "portfolio_context": portfolio_context,
            "market_context": market_context,
            "overnight_transmission": overnight_transmission,
            "pattern_discovery": pattern_discovery,
            "foreign_flow": foreign_flow,
            "instrument_type": instrument_type,
            "framework_note": framework_note,
            "position_context": position_context,
            "investment_debate_state": InvestDebateState(
                {
                    "bull_history": "",
                    "bear_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "regime_report": "",
            "industry_report": "",
            "signal_aggregation": "",
            "key_question": "",
            "event_impact": "",
            "analysis_depth": "",
            "growth_report": "",
            "risk_report": "",
            "reward_risk_report": "",
            "tailrisk_report": "",
            "regime_risk_report": "",
            "risk_consensus": "",
            "forecast_report": "",
            # v0.4 agentic pipeline — initialised empty so every node can read
            # them unconditionally (Orchestrator/DepthController fill them in).
            "orchestration_plan": "",
            "depth_decision": "",
            "trigger_reanalysis": False,
            "reanalysis_targets": [],
            "analyst_iterations": {},
            "analyst_tool_calls": {},
        }

    def get_graph_args(self, callbacks: list | None = None) -> dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            callbacks: Optional list of callback handlers for tool execution tracking.
                       Note: LLM callbacks are handled separately via LLM constructor.
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
