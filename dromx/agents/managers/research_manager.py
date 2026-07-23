"""Research Manager: synthesises the two independent research reports into a plan.

Reads the Growth & Quality and Valuation & Risk analysts' independent reports
(no debate) plus the aggregated signal and pivotal question, and produces one
structured investment plan for the trader.
"""

from __future__ import annotations

from dromx.agents.schemas import ResearchPlan, render_research_plan
from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)
from dromx.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_research_manager(llm):
    structured_llm = bind_structured(llm, ResearchPlan, "Research Manager")

    def research_manager_node(state) -> dict:
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")
        signal_block = (
            f"\n**Aggregated Analyst Signal:**\n{signal_aggregation}\n"
            if signal_aggregation
            else ""
        )
        key_question = state.get("key_question", "")
        key_question_block = (
            f"\n**Pivotal question(s) the team flagged:**\n{key_question}\n"
            if key_question
            else ""
        )
        growth_report = state.get("growth_report", "")
        risk_report = state.get("risk_report", "")

        prompt = f"""As the Research Manager, synthesize the two independent research reports below into a clear, actionable investment plan for the trader.

{instrument_context}
{regime_context}{signal_block}{key_question_block}
---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction in the constructive thesis; recommend taking or growing the position
- **Overweight**: Constructive view; recommend gradually increasing exposure
- **Hold**: Balanced view; recommend maintaining the current position
- **Underweight**: Cautious view; recommend trimming exposure
- **Sell**: Strong conviction in the downside thesis; recommend exiting or avoiding the position

Commit to a clear stance whenever the evidence warrants one; reserve Hold for situations where the two lenses are genuinely balanced.

These are two INDEPENDENT analyses from complementary lenses (Growth & Quality vs Valuation & Risk), not a debate — neither was written to rebut the other. Judge them on evidence, not forcefulness: weight the points best supported by the data, and where the two reports disagree, decide which side's evidence is stronger on that specific point rather than splitting the difference. A genuine concession or honest weakness in either report makes its other points more credible.

Identify the crux. The team pre-flagged the pivotal question(s) above; treat that as your starting point, but if the reports revealed a more decision-relevant question, override it and say why. Either way, name the single most important UNRESOLVED question on which this call actually hinges (e.g. "does data-center revenue growth re-accelerate next quarter?" or "is the margin of safety adequate at this multiple?"). State it explicitly in your rationale, say which way the current evidence leans on it and how confidently, and let the strength of the evidence on THAT question — not the volume of points — drive the rating.

---

**Growth & Quality report:**
{growth_report}

**Valuation & Risk report:**
{risk_report}""" + get_language_instruction()

        investment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_plan,
            "Research Manager",
            schema=ResearchPlan,
        )

        return {"investment_plan": investment_plan}

    return research_manager_node

