"""Deterministic Signal Aggregation containers + render (non-LLM node)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._shared import _conf_cn, _dir_cn


# ---------------------------------------------------------------------------
# Signal Aggregation (deterministic post-analyst node)
# ---------------------------------------------------------------------------
#
# The Signal Aggregator is a NON-LLM node: it parses the four rendered analyst
# reports back into (direction, confidence) via
# ``tradingagents.agents.utils.rating.parse_analyst_signal``, computes a
# confidence-weighted consensus, and surfaces the explicit points of
# disagreement so the bull/bear debate can target them instead of re-deriving
# them. These schemas are plain data containers (the node fills them directly,
# no model call); ``render_signal_aggregation`` produces the markdown stored in
# state and shown in the report tree.


class AnalystSignal(BaseModel):
    """One analyst's parsed directional signal feeding the aggregation."""

    lens: str = Field(description="Analyst lens, e.g. 'Technical', 'News'.")
    direction: str | None = Field(
        default=None, description="Parsed direction phrase, or None if unavailable."
    )
    confidence: str | None = Field(
        default=None, description="Parsed confidence tier (low/medium/high), or None."
    )
    score: int | None = Field(
        default=None, description="Signed direction score (Bullish +2 … Bearish −2)."
    )
    weight: float = Field(
        default=1.0, description="Confidence weight applied to the score."
    )
    accuracy_note: str | None = Field(
        default=None,
        description="Optional historical hit-rate note for this lens in this regime.",
    )


class SignalAggregation(BaseModel):
    """Confidence-weighted consensus across the structured analysts."""

    consensus_direction: str = Field(
        description="Overall directional band derived from the weighted mean score."
    )
    weighted_score: float = Field(
        description="Confidence-weighted mean of the analyst direction scores (−2..+2)."
    )
    agreement: str = Field(
        description="Qualitative agreement level: Strong / Moderate / Split."
    )
    signals: list[AnalystSignal] = Field(
        description="Per-analyst parsed signals that fed the aggregation."
    )
    disagreements: list[str] = Field(
        default_factory=list,
        description="Explicit pairwise disagreements for the debate to resolve.",
    )
    expected_value_pct: float | None = Field(
        default=None,
        description=(
            "Confidence-weighted portfolio expected percent move, fused from the "
            "analysts' scenario distributions. None when no analyst supplied a "
            "scenario distribution."
        ),
    )
    payoff_skew: str | None = Field(
        default=None,
        description=(
            "Payoff asymmetry of the fused distribution: left-tailed / "
            "right-tailed / roughly symmetric. None when no scenarios available."
        ),
    )


def _consensus_band(score: float) -> str:
    """Map a weighted mean score (−2..+2) to a directional band."""
    if score >= 1.25:
        return "Bullish"
    if score >= 0.4:
        return "Mildly Bullish"
    if score > -0.4:
        return "Neutral"
    if score > -1.25:
        return "Mildly Bearish"
    return "Bearish"


def render_signal_aggregation(agg: SignalAggregation) -> str:
    """Render a SignalAggregation to the markdown shape stored in state."""
    header = (
        f"**融合信号：** **{_dir_cn(agg.consensus_direction)}** "
        f"（加权分 {agg.weighted_score:+.2f}，一致性：{agg.agreement}）"
    )
    if agg.expected_value_pct is not None:
        skew = f" · 收益偏度 {agg.payoff_skew}" if agg.payoff_skew else ""
        header += (
            f"\n**融合期望值 ≈ {agg.expected_value_pct:+.1f}%**{skew} "
            f"（按各分析师情景分布的概率加权 —— 据分布而非仅方向定仓）。"
        )
    table = ["", "| 分析师 | 方向 | 置信度 | 评分 |", "|---|---|---|---:|"]
    for s in agg.signals:
        d = _dir_cn(s.direction) if s.direction else "—"
        c = _conf_cn(s.confidence) if s.confidence else "—"
        sc = "—" if s.score is None else f"{s.score:+d}"
        note = f"（{s.accuracy_note}）" if s.accuracy_note else ""
        table.append(f"| {s.lens}{note} | {d} | {c} | {sc} |")
    parts = [header, "\n".join(table)]
    if agg.disagreements:
        parts.append("")
        parts.append("**分歧点（需重点辩论）：**")
        parts.extend(f"- {d}" for d in agg.disagreements)
    else:
        parts.append("")
        parts.append("**分歧点：** 无 —— 各分析师大体一致。")
    return "\n".join(parts)
