# DromX/graph/setup.py

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from dromx.agents import (
    create_aggressive_debator,
    create_bear_researcher,
    create_bull_researcher,
    create_conservative_debator,
    create_event_impact_assessor,
    create_forecast_synthesizer,
    create_fundamentals_analyst,
    create_industry_analyst,
    create_key_question_analyst,
    create_market_analyst,
    create_neutral_debator,
    create_news_analyst,
    create_depth_controller,
    create_orchestrator,
    create_portfolio_manager,
    create_re_analysis,
    create_regime_analyst,
    create_research_manager,
    create_risk_consensus,
    create_sentiment_analyst,
    create_signal_aggregator,
    create_trader,
)
from dromx.agents.schemas import selected_analyst_keys
from dromx.core.agent_states import AgentState

from .analyst_execution import build_analyst_execution_plan
from .conditional_logic import ConditionalLogic


def _noop_aware(node, analyst_key: str, report_key: str):
    """Wrap an analyst node so it short-circuits when unselected by the plan.

    A static LangGraph graph can't add/drop analysts at runtime, so the
    Orchestrator's plan selects which analysts matter this run and the
    unselected ones noop out (return an empty report, 0 LLM calls) instead of
    being removed from the graph. When no plan is present (v0.3 path /
    Orchestrator disabled) ``selected_analyst_keys("")`` returns the full set,
    so every analyst runs — the wrapper is a no-op in v0.3 mode.
    """

    def _wrapped(state):
        plan = state.get("orchestration_plan", "") or ""
        if plan and analyst_key not in selected_analyst_keys(plan):
            return {report_key: ""}
        return node(state)

    return _wrapped


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        tool_nodes: dict[str, ToolNode],
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=("market", "social", "news", "fundamentals")
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        plan = build_analyst_execution_plan(selected_analysts)

        analyst_factories = {
            "market": lambda: create_market_analyst(self.quick_thinking_llm),
            "social": lambda: create_sentiment_analyst(self.quick_thinking_llm),
            "news": lambda: create_news_analyst(self.quick_thinking_llm),
            "fundamentals": lambda: create_fundamentals_analyst(self.quick_thinking_llm),
            "industry": lambda: create_industry_analyst(self.quick_thinking_llm),
        }

        # Regime detection runs once, before the analysts, and classifies the
        # market state so downstream analysts know how to weight their lenses.
        regime_node = create_regime_analyst(self.quick_thinking_llm)

        # Signal aggregation runs once, after the parallel analysts, fusing their
        # structured signals into a confidence-weighted consensus + disagreements.
        signal_aggregator_node = create_signal_aggregator()

        # Key Question runs after aggregation: it names the 1–2 pivotal questions
        # the call hinges on so the debate concentrates instead of arguing evenly.
        key_question_node = create_key_question_analyst(self.quick_thinking_llm)

        # Event Impact runs after aggregation too: it asks whether any datum
        # re-rates the premise (and catches unanimity-on-thin-info), so the desk
        # re-examines before committing rather than processing all data equally.
        event_impact_node = create_event_impact_assessor(self.quick_thinking_llm)

        # Create researcher and manager nodes. The research layer is now two
        # INDEPENDENT parallel analysts (no Bull⇄Bear debate): Growth & Quality
        # and Valuation & Risk each write one report; the Research Manager
        # synthesises both.
        growth_analyst_node = create_bull_researcher(self.quick_thinking_llm)
        risk_analyst_node = create_bear_researcher(self.quick_thinking_llm)
        research_manager_node = create_research_manager(self.deep_thinking_llm)
        trader_node = create_trader(self.quick_thinking_llm)

        # Create risk analysis nodes. The risk layer is now three INDEPENDENT
        # parallel specialists (no debate loop): Reward, Tail-Risk, Regime each
        # write one report; Risk Consensus reconciles them into one stop frame.
        reward_specialist = create_aggressive_debator(self.quick_thinking_llm)
        regime_specialist = create_neutral_debator(self.quick_thinking_llm)
        tailrisk_specialist = create_conservative_debator(self.quick_thinking_llm)
        risk_consensus_node = create_risk_consensus(self.quick_thinking_llm)
        forecast_node = create_forecast_synthesizer(self.quick_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        # Create workflow
        workflow = StateGraph(AgentState)

        # v0.4 agentic pipeline toggle. When on, an Orchestrator node sits
        # between Regime and the analysts and writes a run-specific plan; each
        # analyst reads the plan and noops out if not selected (a static graph
        # can't drop nodes at runtime, so unselected analysts short-circuit).
        from dromx.dataflows.config import get_config
        agent_loop_enabled = bool(
            (get_config().get("agent_loop") or {}).get("enabled", False)
        )

        # Regime detection node (pre-analysis).
        workflow.add_node("Regime Analyst", regime_node)

        # v0.4: Orchestrator writes the run plan; analysts noop if unselected.
        if agent_loop_enabled:
            workflow.add_node("Orchestrator", create_orchestrator(self.quick_thinking_llm))

        # Analyst nodes. Since v0.3.x the analysts pre-fetch their data and emit
        # structured output in a single LLM call (no tool-calling loop), so they
        # have no per-analyst tool/clear nodes and can run as a parallel fan-out.
        for spec in plan.specs:
            node = analyst_factories[spec.key]()
            if agent_loop_enabled:
                node = _noop_aware(node, spec.key, spec.report_key)
            workflow.add_node(spec.agent_node, node)

        # Add other nodes
        workflow.add_node("Signal Aggregator", signal_aggregator_node)
        workflow.add_node("Event Impact", event_impact_node)
        if agent_loop_enabled:
            workflow.add_node("Depth Controller", create_depth_controller(self.quick_thinking_llm))
            workflow.add_node("Re-Analysis", create_re_analysis(self.quick_thinking_llm))
        workflow.add_node("Key Question", key_question_node)
        workflow.add_node("Growth Analyst", growth_analyst_node)
        workflow.add_node("Risk Analyst", risk_analyst_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Reward Specialist", reward_specialist)
        workflow.add_node("Tail Risk Specialist", tailrisk_specialist)
        workflow.add_node("Regime Risk Specialist", regime_specialist)
        workflow.add_node("Risk Consensus", risk_consensus_node)
        workflow.add_node("Forecast Synthesizer", forecast_node)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # Define edges
        # Regime detection first, then fan OUT to every analyst in parallel.
        # v0.4 inserts the Orchestrator between Regime and the analysts.
        workflow.add_edge(START, "Regime Analyst")
        analyst_source = "Orchestrator" if agent_loop_enabled else "Regime Analyst"
        if agent_loop_enabled:
            workflow.add_edge("Regime Analyst", "Orchestrator")
        for spec in plan.specs:
            workflow.add_edge(analyst_source, spec.agent_node)
            # Fan IN: each analyst flows into the Signal Aggregator. LangGraph
            # runs the analysts concurrently (same superstep) and the Signal
            # Aggregator only fires once all its incoming analyst edges have
            # completed — so it sees every analyst's structured report.
            workflow.add_edge(spec.agent_node, "Signal Aggregator")

        # The aggregated signal feeds the Event Impact assessor (premise-shift
        # check) and then the Key Question node. Key Question fans OUT to the two
        # independent research analysts (Growth & Quality ∥ Valuation & Risk),
        # which run concurrently and fan IN to the Research Manager — no debate
        # loop. On Quick Scan (strong agreement, calm regime) the research layer
        # is skipped and Key Question routes straight to the Research Manager.
        # See ConditionalLogic.route_after_key_question.
        workflow.add_edge("Signal Aggregator", "Event Impact")
        if agent_loop_enabled:
            # v0.4: Depth Controller decides conclude / standard / deep_dive (+Re-Analysis).
            workflow.add_edge("Event Impact", "Depth Controller")
            workflow.add_conditional_edges(
                "Depth Controller",
                self.conditional_logic.route_after_depth_control,
                ["Key Question", "Re-Analysis", "Portfolio Manager"],
            )
            workflow.add_edge("Re-Analysis", "Key Question")
        else:
            workflow.add_edge("Event Impact", "Key Question")
        workflow.add_conditional_edges(
            "Key Question",
            self.conditional_logic.route_after_key_question,
            ["Growth Analyst", "Risk Analyst", "Research Manager"],
        )
        workflow.add_edge("Growth Analyst", "Research Manager")
        workflow.add_edge("Risk Analyst", "Research Manager")

        workflow.add_edge("Research Manager", "Trader")
        # Risk layer: the Trader fans OUT to three INDEPENDENT risk specialists
        # (Reward ∥ Tail-Risk ∥ Regime), which run concurrently and fan IN to the
        # Risk Consensus node — no debate loop. Risk Consensus reconciles their
        # stops/drawdowns into one framework before the PM decides.
        workflow.add_edge("Trader", "Reward Specialist")
        workflow.add_edge("Trader", "Tail Risk Specialist")
        workflow.add_edge("Trader", "Regime Risk Specialist")
        workflow.add_edge("Reward Specialist", "Risk Consensus")
        workflow.add_edge("Tail Risk Specialist", "Risk Consensus")
        workflow.add_edge("Regime Risk Specialist", "Risk Consensus")

        # Risk Consensus reconciles the three risk reports; the Forecast
        # Synthesizer then turns the whole picture into a time-layered forecast
        # before the PM makes the final call.
        workflow.add_edge("Risk Consensus", "Forecast Synthesizer")
        workflow.add_edge("Forecast Synthesizer", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow
