"""DepthController (v0.4 PRD §4.3) — decide analysis depth after SignalAgg + EventImpact.

Replaces the coarser ``analysis_depth`` routing (signal-agreement only) by
adding the event-impact dimension. Single structured LLM call: the rules are
in the prompt (clear cases -> conclude / standard / deep_dive), the LLM
judges the ambiguous middle. Writes ``depth_decision`` (rendered markdown) +
``trigger_reanalysis`` (bool) + ``reanalysis_targets`` (analyst keys) so the
graph can route to the Re-Analysis node when an event drove a deep_dive.
"""

from __future__ import annotations

from dromx.agents.schemas import DepthDecision, render_depth_decision
from dromx.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
    get_regime_context_from_state,
)
from dromx.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_depth_controller(llm):
    """Create the Depth Controller node (single structured call)."""
    structured_llm = bind_structured(llm, DepthDecision, "Depth Controller")

    def depth_controller_node(state):
        instrument_context = get_instrument_context_from_state(state)
        regime_context = get_regime_context_from_state(state)
        signal_aggregation = state.get("signal_aggregation", "")
        event_impact = state.get("event_impact", "")
        analysis_depth = state.get("analysis_depth", "")

        prompt = f"""You are the Depth Controller. After the analysts ran and their signals were fused, decide how much MORE analysis this call needs before the PM commits.

{instrument_context}
{regime_context}
## Fused signal (consensus, agreement, EV, disagreements)
{signal_aggregation}

## Event impact (premise-shift assessment, 0-10 score, recommend_reanalysis flag, affected_dimensions)
{event_impact}

## Signal Aggregator's own depth hint
{analysis_depth}

## Decision rules
- **conclude** — skip the Research (Growth/Risk) and Risk layers entirely, go straight to PM. Use when: analysts strongly agree AND no event re-rates the premise (impact < 4, no reanalysis flag). The call is clear; don't manufacture debate.
- **standard** — run the Research layer (Growth & Quality / Valuation & Risk) as normal. Use when: moderate agreement, no decisive event.
- **deep_dive** — run the Research layer AND re-examine the analysts the event impacted. Use when: analysts are split (agreement = Split), OR a premise-changing event is present (impact >= 7 or recommend_reanalysis), OR the Signal Aggregator already flagged Deep Dive. Set recommend_reanalysis_of to the affected analyst KEYS (market / news / sentiment / fundamentals / industry) — NOT lens labels like Technical/Sentiment. Map a lens label to its key if needed (Technical->market, Sentiment->sentiment, News->news, Fundamentals->fundamentals, Industry->industry). Draw from the event-impact report's affected_dimensions.

Read the agreement level and impact score from the blocks above. Output the DepthDecision: decision, one-sentence reasoning, and recommend_reanalysis_of (only when deep_dive was driven by an event).
{get_language_instruction()}"""

        # Try the typed structured call first so we get the decision + targets
        # without parsing markdown. Fall back to free-text + a coarse parse.
        decision = None
        if structured_llm is not None:
            try:
                decision = structured_llm.invoke(prompt)
                if not isinstance(decision, DepthDecision):
                    decision = None
            except Exception:  # noqa: BLE001 — fall back to free-text
                decision = None

        if decision is not None:
            depth_text = render_depth_decision(decision)
            trigger = (
                decision.decision == "deep_dive"
                and bool(decision.recommend_reanalysis_of)
            )
            targets = list(decision.recommend_reanalysis_of) if trigger else []
        else:
            depth_text = invoke_structured_or_freetext(
                structured_llm, llm, prompt, render_depth_decision,
                "Depth Controller", schema=DepthDecision,
            )
            low = depth_text.lower()
            if "deep_dive" in low:
                verdict = "deep_dive"
            elif "conclude" in low:
                verdict = "conclude"
            else:
                verdict = "standard"
            trigger = verdict == "deep_dive" and (
                "重审视" in depth_text or "reanalysis" in low
            )
            targets = []  # can't reliably parse keys from free text

        return {
            "depth_decision": depth_text,
            "trigger_reanalysis": trigger,
            "reanalysis_targets": targets,
        }

    return depth_controller_node
