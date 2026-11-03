# DromX/graph/conditional_logic.py

from dromx.core.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters.

        ``max_debate_rounds`` / ``max_risk_discuss_rounds`` are retained for
        API/config back-compat but no longer gate a debate loop — the research
        and risk layers now run as one-shot parallel reports (no back-and-forth).
        """
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    # Analyst tool-loop routing was removed in v0.3.x (analysts pre-fetch + emit
    # structured output in one call). Both DEBATE loops were removed in the
    # de-debate refactor: the research layer (Growth & Quality ∥ Valuation &
    # Risk, PN-1) and the risk layer (Reward ∥ Tail-Risk ∥ Regime, PN-2) now run
    # as parallel one-shot reports that fan in to a single synthesiser (Research
    # Manager / Risk Consensus). No should_continue_* gates remain.

    def route_after_key_question(self, state: AgentState) -> list[str]:
        """Fan out to the parallel research analysts, or skip them on Quick Scan.

        Returns a LIST so LangGraph schedules the targets concurrently. On Quick
        Scan (strong agreement, calm regime) the research layer is skipped and we
        go straight to the Research Manager, which synthesises the analyst
        reports directly.
        """
        if state.get("analysis_depth", "") == "Quick Scan":
            return ["Research Manager"]
        return ["Growth Analyst", "Risk Analyst"]

    def route_after_depth_control(self, state: AgentState) -> list[str]:
        """Route after the Depth Controller (v0.4).

        - ``trigger_reanalysis`` -> Re-Analysis (re-examine the analysts the event
          impacted), which then flows to Key Question.
        - ``conclude`` -> Portfolio Manager (skip Research / Risk / Forecast — the
          PM reads the empty research/risk/forecast fields and degrades gracefully).
        - ``standard`` / ``deep_dive`` -> Key Question (the normal path; the
          research layer's own depth is still gated by route_after_key_question
          reading analysis_depth).
        """
        if state.get("trigger_reanalysis"):
            return ["Re-Analysis"]
        if "conclude" in (state.get("depth_decision") or "").lower():
            return ["Portfolio Manager"]
        return ["Key Question"]
