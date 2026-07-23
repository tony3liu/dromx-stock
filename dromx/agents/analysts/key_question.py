"""Key Question — an LLM node that names the 1–2 questions the call hinges on.

A junior analyst spreads attention evenly across every lens; a senior one first
finds the ONE question whose answer decides the call and spends the debate
there. This node runs right after the Signal Aggregator, so it already sees all
four analyst reports, the fused/consensus signal, and the market regime. It does
NOT fetch data — like the Signal Aggregator it is a pure synthesis step over
state — but unlike that deterministic node it needs judgement, so it makes a
single structured LLM call returning a ``KeyQuestionReport``.

Design mirrors ``regime_analyst`` (bind_structured + invoke_structured_or_freetext
with a graceful free-text fallback). Placed between "Signal Aggregator" and
"Bull Researcher" so the debate and the managers can center on the pivotal
question instead of arguing every lens evenly.
"""

from __future__ import annotations

from dromx.agents.schemas import KeyQuestionReport, render_key_question_report
from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)
from dromx.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_key_question_analyst(llm):
    """Create the key-question node (synthesis over state, single structured call)."""
    structured_llm = bind_structured(llm, KeyQuestionReport, "Key Question Analyst")

    def key_question_node(state):
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")
        signal_block = (
            f"\n## Aggregated analyst signal (consensus, fused EV, disagreements)\n"
            f"{signal_aggregation}\n"
            if signal_aggregation
            else ""
        )
        event_impact = state.get("event_impact", "")
        event_block = (
            f"\n## Event-impact flag (premise-shift check — fold a flagged "
            f"event into the key question if it re-rates the thesis)\n{event_impact}\n"
            if event_impact
            else ""
        )

        system_message = f"""You are a senior analyst triaging {state.get("company_of_interest", "this name")} before the investment debate. The team has produced four lens reports and a fused signal. Your single job is to name the ONE question (at most two) on which this call actually turns — the question whose answer, more than anything else, decides whether the rating is right.
{regime_context}{signal_block}{event_block}
## The four analyst reports
### Technical / market
{state.get("market_report", "")}

### Sentiment
{state.get("sentiment_report", "")}

### News / macro
{state.get("news_report", "")}

### Fundamentals
{state.get("fundamentals_report", "")}

## How to choose the key question

1. **Look at the disagreements and the expectation gaps**, not the points everyone already agrees on — the call is decided where the evidence is contested or where price implies an expectation the analysts dispute.
2. **Phrase it so the answer moves the rating.** "Does data-center revenue re-accelerate next quarter?" is a key question; "Is the company good?" is not.
3. **Demand at most two.** Prefer one sharp question. Add a second only if it is genuinely independent and nearly as pivotal. Resist listing every open issue — the point is to concentrate attention, not enumerate it.
4. **Say what would answer each** — the specific, observable data point, filing, print, or price level — so the debate hunts for evidence instead of speculating.
5. **Write a one-line focus directive** telling the debate where to spend ~70% of its effort.

Fill the structured fields: key_questions (each with question, why_it_matters, what_would_answer_it) and focus_directive.

{get_language_instruction()}"""

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            system_message,
            render_key_question_report,
            "Key Question Analyst",
            schema=KeyQuestionReport,
        )

        return {"key_question": report_text}

    return key_question_node
