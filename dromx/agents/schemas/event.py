"""Event Impact node schema + render (premise-shift detector)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event Impact (post-aggregation premise-shift detector)
# ---------------------------------------------------------------------------
#
# The pipeline treats all data equally: every lens flows in, gets fused, and the
# debate proceeds. Nothing asks "does any of this DATA invalidate the premise
# the conclusion rests on?". A senior analyst's edge is spotting the one item
# that changes the game (a $29B raise re-rates the capital structure) versus the
# noise it sits next to. This node runs after the Signal Aggregator — so it sees
# every report plus the fused signal — and judges whether a premise-changing
# event is present and whether the desk should re-examine before committing.
# Critically it also catches the "everyone is unanimously bullish on incomplete
# information" failure, which the Key Question node (which hunts disagreement)
# cannot see. A light structured LLM call; free-text fallback.


class EventImpactReport(BaseModel):
    """Premise-shift assessment: does any event here invalidate the conclusion?"""

    impact_score: int = Field(
        ge=0, le=10,
        description=(
            "0–10 score by DECISIVENESS — how much this event determines whether "
            "the rating is right, not how dramatic the headline is. 0–3 = routine, "
            "thesis holds regardless; 4–6 = notable, shifts conviction not the "
            "call; 7–10 = decisive: if this single event is the variable the "
            "Buy/Hold/Sell call hinges on (even if not yet happened — an "
            "undigested capital raise, a pending earnings print the thesis "
            "depends on), score 8–10. If it is THE pivotal factor it cannot be a 5."
        ),
    )
    affected_dimensions: list[str] = Field(
        default_factory=list,
        description=(
            "Which analyst assumptions the event undercuts or reshapes, e.g. "
            "'fundamentals: per-share value (dilution)', 'technical: the breakout "
            "premise'. Empty when impact is routine."
        ),
    )
    recommend_reanalysis: bool = Field(
        default=False,
        description=(
            "True when impact_score is high enough that the PM should explicitly "
            "re-examine the premise before committing — including the case where "
            "the analysts are UNANIMOUS but on visibly incomplete information."
        ),
    )
    assessment: str = Field(
        description=(
            "1–3 sentences: the single most premise-relevant event (or 'no "
            "premise-changing event'), what it changes, and — if unanimity rests "
            "on thin information — say so explicitly."
        ),
    )


def render_event_impact(report: EventImpactReport) -> str:
    """Render an EventImpactReport to the markdown shape stored in state."""
    flag = "⚠️ 重新审视前提" if report.recommend_reanalysis else "前提无变化"
    parts = [
        f"**事件冲击：** {report.impact_score}/10 —— {flag}",
        "",
        report.assessment,
    ]
    if report.affected_dimensions:
        parts.append("")
        parts.append("**受影响的前提：**")
        parts.extend(f"- {d}" for d in report.affected_dimensions)
    return "\n".join(parts)
