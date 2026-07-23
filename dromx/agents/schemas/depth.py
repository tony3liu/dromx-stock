"""DepthController structured output (v0.4 PRD §4.3).

Sits after SignalAgg + EventImpact. Decides whether to conclude (skip
Research/Risk, go straight to PM), run the standard Research layer, or
deep-dive (Research layer + re-examine the analysts the event impacted).
Replaces the coarser ``analysis_depth`` routing (signal-agreement only) by
adding the event-impact dimension.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DepthVerdict = Literal["conclude", "standard", "deep_dive"]


class DepthDecision(BaseModel):
    """The Depth Controller's verdict on how much more analysis the call needs."""

    decision: DepthVerdict = Field(
        description=(
            "conclude = skip Research/Risk layers, go straight to PM; "
            "standard = run the Research layer (Growth & Quality / Valuation & "
            "Risk); deep_dive = run Research AND re-examine the analysts the "
            "event impacted."
        ),
    )
    reasoning: str = Field(description="One sentence: why this depth for this setup.")
    recommend_reanalysis_of: list[str] = Field(
        default_factory=list,
        description=(
            "Analyst keys to re-examine in the Re-Analysis node. Set only when "
            "deep_dive was driven by a premise-changing event (impact >= 7 or "
            "recommend_reanalysis); draw from the event-impact report's "
            "affected_dimensions."
        ),
    )


def render_depth_decision(d: DepthDecision) -> str:
    """Render the decision to the markdown shape the state + report tree expect."""
    parts = [
        f"**深度决策:** {d.decision}",
        "",
        f"**理由:** {d.reasoning}",
    ]
    if d.recommend_reanalysis_of:
        parts.extend(["", f"**建议重审视的分析师:** {', '.join(d.recommend_reanalysis_of)}"])
    return "\n".join(parts)
