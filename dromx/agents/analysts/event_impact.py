"""Event Impact Assessor — asks whether any data here invalidates the premise.

The pipeline treats every lens equally: news, technicals, sentiment, and
fundamentals all flow in, get fused, and the debate proceeds. Nothing asks the
question a senior analyst asks first — "does any of this DATA change the premise
the conclusion rests on?". A $29B capital raise is not the same kind of fact as
"the sector rallied 2%", but the flat pipeline processes them side by side.

This node runs after the Signal Aggregator (so it sees all four reports plus the
fused signal) and judges: is a premise-changing event present, which assumptions
does it undercut, and should the PM re-examine before committing? It also catches
the failure the Key Question node structurally cannot — analysts UNANIMOUS on
visibly incomplete information (unanimity reads as agreement, not as risk). A
light structured LLM call with a free-text fallback.
"""

from __future__ import annotations

from dromx.agents.schemas import EventImpactReport, render_event_impact
from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_market_context_from_state,
    get_overnight_transmission_from_state,
    get_pattern_discovery_from_state,
    get_foreign_flow_from_state,
    get_source_freshness_discipline,
)
from dromx.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_event_impact_assessor(llm):
    """Create the event-impact node (premise-shift detector, single structured call)."""
    structured_llm = bind_structured(llm, EventImpactReport, "Event Impact Assessor")

    def event_impact_node(state):
        instrument_context = get_instrument_context_from_state(state)
        market_context = get_market_context_from_state(state)
        overnight_transmission = get_overnight_transmission_from_state(state)
        pattern_discovery = get_pattern_discovery_from_state(state)
        foreign_flow = get_foreign_flow_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")

        system_message = f"""You are a senior analyst doing one job before the debate: deciding whether any item in this analysis CHANGES THE PREMISE the conclusion rests on. Not "is the news good or bad" — "does this re-rate the thesis?".

{instrument_context}
{market_context}{overnight_transmission}{pattern_discovery}{foreign_flow}
## Fused signal (consensus, EV, agreement, disagreements)
{signal_aggregation}

## News / macro report (look here first for premise-changing events)
{state.get("news_report", "")}

## Fundamentals report
{state.get("fundamentals_report", "")}

## Technical report
{state.get("market_report", "")}

## How to assess

1. **Find the one premise-changing event, if any.** Capital raises / dilution, M&A, regulatory actions, management changes, guidance resets, covenant/default events re-rate the thesis even when they don't flip the direction. Ordinary price moves, routine coverage, and sentiment swings do NOT. **Check each event's [date] against today first:** an event dated BEFORE today has already happened — judge the thesis on its actual outcome, and flag if the upstream reports are still reasoning from a pre-event prediction (a stale premise IS a premise-changing problem). Do not invent a date for an event the data doesn't date.
2. **Score the impact 0–10** by DECISIVENESS, not by how dramatic the headline sounds. The question is: how much does this event determine whether the rating is right? 0–3 = routine, the thesis holds regardless; 4–6 = notable, shifts conviction but not the call; 7–10 = decisive — if this single event is the variable the whole Buy/Hold/Sell call hinges on (even when it has not happened yet, e.g. an undigested capital raise, a pending earnings print the thesis depends on), score it 8–10. If the Key Question or the PM would treat this event as THE pivotal factor, it cannot be a 5. Name which analyst assumptions it undercuts.
3. **Watch for false comfort.** If the analysts are UNANIMOUS but the information is visibly incomplete (a major event mentioned but not yet digested, thin data, a number nobody quantified), that unanimity is itself a risk — recommend re-analysis even though there is no disagreement.
4. **Set recommend_reanalysis** when the PM should explicitly re-examine the premise before committing.

Fill the structured fields: impact_score, affected_dimensions, recommend_reanalysis, assessment. If nothing changes the premise, score it low and say so plainly — do not manufacture an event.
{get_source_freshness_discipline()}
{get_language_instruction()}"""

        report_text = invoke_structured_or_freetext(
            structured_llm,
            llm,
            system_message,
            render_event_impact,
            "Event Impact Assessor",
            schema=EventImpactReport,
        )

        return {"event_impact": report_text}

    return event_impact_node
