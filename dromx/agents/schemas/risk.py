"""Risk Consensus node schema + render (unified stop framework)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ._shared import _coerce_optional_float


# ---------------------------------------------------------------------------
# Risk Consensus (post risk-debate synthesis node)
# ---------------------------------------------------------------------------
#
# The three risk debators (Reward / Tail-Risk / Regime specialists) each argue
# their own stop level, drawdown estimate, and stress scenario in prose. Until
# now the Portfolio Manager stitched those together by hand in its prompt, with
# no unified numbers. This node distils the debate into ONE stop-loss framework
# with explicit figures the PM consumes directly — and that the position-sizing
# (Kelly) step reads for its unit-of-risk input. A light structured LLM call
# (the debate is free-form prose, often non-English, so regex extraction would
# be brittle); free-text fallback degrades to the raw synthesis text.


class RiskConsensusReport(BaseModel):
    """Unified stop-loss / drawdown framework distilled from the risk debate."""

    recommended_stop: float | None = Field(
        default=None,
        description=(
            "The single recommended stop-loss price in the instrument's quote "
            "currency, reconciled from the three risk analysts' proposals (lean "
            "to the more protective level when they disagree materially). None "
            "if the debate gave no usable price."
        ),
    )
    stop_atr_multiple: float | None = Field(
        default=None,
        description=(
            "The stop distance expressed as a multiple of ATR (e.g. 2.5 means "
            "the stop sits ~2.5 ATR from entry), so sizing is volatility-aware. "
            "None if ATR was not usable."
        ),
    )
    max_drawdown_pct: float | None = Field(
        default=None,
        description=(
            "The maximum acceptable drawdown for this position, in percent "
            "(positive number, e.g. 18 for -18%), reconciled across the analysts. "
            "This is the unit of risk the position-sizing step divides into."
        ),
    )
    key_risk: str = Field(
        description=(
            "The single most important downside risk the debate surfaced, in one "
            "sentence — the tail the stop is actually protecting against."
        ),
    )
    framework: str = Field(
        description=(
            "2-4 sentences: the unified stop/drawdown framework the PM should "
            "apply, noting where the analysts agreed and how you reconciled the "
            "level when they did not."
        ),
    )

    @field_validator("recommended_stop", "stop_atr_multiple", "max_drawdown_pct", mode="before")
    @classmethod
    def _nullish_float_to_none(cls, v):
        return _coerce_optional_float(v)


def render_risk_consensus(report: RiskConsensusReport) -> str:
    """Render a RiskConsensusReport to the markdown shape stored in state."""
    parts = ["**风险共识 —— 统一止损框架：**", ""]
    if report.recommended_stop is not None:
        line = f"- **建议止损：** {report.recommended_stop}"
        if report.stop_atr_multiple is not None:
            line += f"（约 {report.stop_atr_multiple:.1f}× ATR）"
        parts.append(line)
    elif report.stop_atr_multiple is not None:
        parts.append(f"- **止损距离：** 约 {report.stop_atr_multiple:.1f}× ATR")
    if report.max_drawdown_pct is not None:
        parts.append(f"- **最大可接受回撤：** −{report.max_drawdown_pct:.1f}%")
    parts.append(f"- **关键风险：** {report.key_risk}")
    parts.extend(["", report.framework])
    return "\n".join(parts)
