"""Portfolio Manager structured decision (+ weighted price drivers) + render."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ._shared import _coerce_optional_float
from .rating import PortfolioRating


# ---------------------------------------------------------------------------
# Portfolio Manager
# ---------------------------------------------------------------------------


class PriceDriver(BaseModel):
    """One weighted driver of the instrument's price (PH-4 multi-variable view).

    A decision is almost never explained by a single variable. The PM lists the
    ≥3 drivers that actually move this name, each with a rough weight, so the
    output is an explicit weighted decomposition rather than a "the only variable
    that matters is X" fallacy. (This coexists with the Key Question / Event
    Impact single-pivot view — that names the most CONTESTED unknown; this names
    what DRIVES the price. Different axes.)
    """

    driver: str = Field(description="The price driver, e.g. 'SK Hynix spot price', 'ADR dilution', 'KRW/HKD'.")
    weight_pct: float = Field(
        ge=0.0, le=100.0,
        description="Rough share of price influence in percent (the drivers should sum to ~100).",
    )
    direction: str = Field(
        description="Current lean of this driver for the position: tailwind / headwind / neutral.",
    )

    @field_validator("weight_pct", mode="before")
    @classmethod
    def _coerce_weight(cls, v):
        v = _coerce_optional_float(v)
        if isinstance(v, str):
            v = v.strip().rstrip("%").strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v if v is not None else 0.0


class PortfolioDecision(BaseModel):
    """Structured output produced by the Portfolio Manager.

    The model fills every field as part of its primary LLM call; no separate
    extraction pass is required. Field descriptions double as the model's
    output instructions, so the prompt body only needs to convey context and
    the rating-scale guidance.
    """

    rating: PortfolioRating = Field(
        description=(
            "The final position rating. Exactly one of Buy / Overweight / Hold / "
            "Underweight / Sell, picked based on the analysts' debate."
        ),
    )
    executive_summary: str = Field(
        description=(
            "A concise action plan covering entry strategy, position sizing, "
            "key risk levels, and time horizon. Two to four sentences."
        ),
    )
    investment_thesis: str = Field(
        description=(
            "Detailed reasoning anchored in specific evidence from the analysts' "
            "debate. If prior lessons are referenced in the prompt context, "
            "incorporate them; otherwise rely solely on the current analysis. "
            "Close with the key question and a falsification trigger whose "
            "timescale matches time_horizon (a multi-month horizon needs a "
            "monthly/weekly trigger, not an intraday one)."
        ),
    )
    key_drivers: list[PriceDriver] = Field(
        default_factory=list,
        description=(
            "At least 3 weighted price drivers (driver + weight% + tailwind/"
            "headwind/neutral), summing to ~100%. This is the multi-variable "
            "decomposition of what moves the name — never collapse it to a single "
            "'only variable that matters'."
        ),
    )
    price_target: float | None = Field(
        default=None,
        description="Optional target price in the instrument's quote currency.",
    )
    time_horizon: str | None = Field(
        default=None,
        description=(
            "Optional recommended holding period, e.g. '3-6 months'. The "
            "falsification trigger in the thesis must be checkable at this "
            "horizon's resolution."
        ),
    )
    # v0.4: the rating binds to ONE primary horizon; the others are conditional views.
    primary_horizon: str | None = Field(
        default=None,
        description=(
            "The ONE horizon the rating is anchored to (T+1 / T+5 / T+20 / T+60). "
            "The rating holds at THIS horizon; the t1/t5/t20 views below are "
            "conditional, NOT separate ratings. Never give a rating that's a blend "
            "of horizons — pick the primary, state it, and let the others be risks."
        ),
    )
    t1_view: str | None = Field(
        default=None,
        description="T+1 (next session) view — conditional/short-term, NOT the rating.",
    )
    t5_view: str | None = Field(
        default=None,
        description="T+5 (one week) view — conditional, NOT the rating.",
    )
    t20_view: str | None = Field(
        default=None,
        description="T+20 (one month) view — conditional, NOT the rating.",
    )
    action: str | None = Field(
        default=None,
        description=(
            "Concrete action tied to the primary horizon + rating, e.g. "
            "'scale in on a pullback to $X or a break above $Y'. Not a vague 'hold'."
        ),
    )

    @field_validator("price_target", mode="before")
    @classmethod
    def _nullish_float_to_none(cls, v):
        return _coerce_optional_float(v)


def render_pm_decision(decision: PortfolioDecision) -> str:
    """Render a PortfolioDecision back to the markdown shape the rest of the system expects.

    Memory log, CLI display, and saved report files all read this markdown,
    so the rendered output preserves the exact section headers (``**Rating**``,
    ``**Executive Summary**``, ``**Investment Thesis**``) that downstream
    parsers and the report writers already handle.
    """
    parts = [
        f"**评级**：{decision.rating.value}",
        "",
        f"**执行摘要**：{decision.executive_summary}",
        "",
        f"**投资论点**：{decision.investment_thesis}",
    ]
    if decision.price_target is not None:
        parts.extend(["", f"**目标价**：{decision.price_target}"])
    if decision.time_horizon:
        parts.extend(["", f"**时间框架**：{decision.time_horizon}"])
    if decision.primary_horizon:
        parts.extend(["", f"**主评级期限**：{decision.primary_horizon}（评级锚定此期限，其余为条件/风险）"])
    if decision.t1_view:
        parts.extend(["", f"**T+1（下一交易日）**：{decision.t1_view}"])
    if decision.t5_view:
        parts.extend(["", f"**T+5（一周）**：{decision.t5_view}"])
    if decision.t20_view:
        parts.extend(["", f"**T+20（一月）**：{decision.t20_view}"])
    if decision.action:
        parts.extend(["", f"**操作**：{decision.action}"])
    if decision.key_drivers:
        parts.extend(["", "**加权关键驱动：**"])
        for d in decision.key_drivers:
            parts.append(f"- {d.driver} —— {d.weight_pct:.0f}%（{d.direction}）")
    return "\n".join(parts)
