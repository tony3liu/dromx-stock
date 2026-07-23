"""Forecast Synthesizer node schemas + render (time-layered forecast)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ._shared import _NULLISH_FLOAT, _conf_cn, _dir_cn


# ---------------------------------------------------------------------------
# Forecast Synthesizer (time-horizon prediction node)
# ---------------------------------------------------------------------------
#
# Runs after Risk Consensus, before the PM. Synthesises every prior artifact
# (5 analyst reports, regime, fused signal/EV/skew, event impact, key question,
# risk consensus stop/Kelly) into a TIME-LAYERED forecast: what the desk should
# expect at T+1 / T+5 / T+20 / T+60, each with a range, scenarios, a
# falsification condition, and a confidence tied to input-data quality. Short
# horizons lean on ATR + technical levels + the event calendar; long horizons on
# the industry cycle + competitive structure — never the other way round.


class PriceScenario(BaseModel):
    """One leg of the name-level price scenario distribution (bear/base/bull).

    Complements the time-layered horizons: the horizons say what to expect WHEN;
    the scenario table says the bear/base/bull PRICE distribution for the call,
    each with a range, a probability, and a trigger — the desk's open-call
    format. Fill it when the call is event-driven enough to branch; leave empty
    when a single path suffices.
    """

    label: Literal["bear", "base", "bull"] = Field(
        description="Which leg: 'bear', 'base', or 'bull'.",
    )
    price_range: str = Field(
        description=(
            "Expected price range for this leg in the quote currency, e.g. "
            "'98-103'. Derive from the leverage-derived expected open + ATR + "
            "technical levels."
        ),
    )
    probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Probability of this leg as a fraction in [0, 1].",
    )
    trigger: str = Field(
        description="The concrete, observable condition that puts this leg in play.",
    )

    @field_validator("probability", mode="before")
    @classmethod
    def _probability_coerce(cls, v):
        """Strip placeholders/percent signs, then fold a percent to a fraction.

        '35%' -> 0.35; 35 -> 0.35; 0.35 -> 0.35; 'N/A' -> 0.0.
        """
        if isinstance(v, str):
            s = v.strip().rstrip("%").strip()
            if s.lower() in _NULLISH_FLOAT or s == "":
                return 0.0
            try:
                v = float(s)
            except ValueError:
                return 0.0
        try:
            f = float(v)
        except (TypeError, ValueError):
            return v
        return f / 100.0 if f > 1.0 else f


class ForecastHorizon(BaseModel):
    """One time-slice of the forecast (e.g. T+1, T+5, T+20, T+60)."""

    horizon: str = Field(
        description="The time slice label: exactly one of 'T+1', 'T+5', 'T+20', 'T+60'."
    )
    price_range: str = Field(
        description=(
            "Expected price range for this horizon in the quote currency, e.g. "
            "'170-200'. For short horizons (T+1/T+5) derive it from ATR (≈1σ) and "
            "technical levels in the market report; for long horizons frame it "
            "from the regime + industry cycle, and say so."
        ),
    )
    direction: str = Field(
        description=(
            "Directional lean for this horizon: Bullish / Mildly Bullish / "
            "Neutral / Mildly Bearish / Bearish."
        ),
    )
    most_likely: str = Field(
        description="One sentence: the single most likely path over this horizon."
    )
    scenarios: str = Field(
        default="",
        description=(
            "Optional branching scenarios for this horizon (e.g. ADR dilution "
            "<3% / 3-8% / >8% → range + probability each). Use mainly for T+5 / "
            "event-driven horizons; leave empty when a single path suffices."
        ),
    )
    key_trigger_or_calendar: str = Field(
        description=(
            "The concrete trigger or dated calendar item that decides this "
            "horizon (e.g. 'ADR terms released after close → gap next day', "
            "'Korean FSS filing', 'Fed speaker'). Be specific and observable."
        ),
    )
    falsification: str = Field(
        description=(
            "What would prove THIS horizon's forecast wrong — a concrete, "
            "observable condition checkable at this horizon's timescale."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "Confidence for THIS horizon, tied to input-data quality: lower it "
            "explicitly when a relevant lens was missing/weak, when the horizon "
            "hinges on an undisclosed event, or when the regime is unstable. Say "
            "why in the narrative."
        ),
    )


class ForecastReport(BaseModel):
    """Time-layered forecast across T+1 / T+5 / T+20 / T+60."""

    horizons: list[ForecastHorizon] = Field(
        description=(
            "Exactly four horizons in order: T+1 (next session), T+5 (one week), "
            "T+20 (one month), T+60 (one quarter)."
        ),
    )
    scenario_table: list[PriceScenario] = Field(
        default_factory=list,
        description=(
            "The name-level bear/base/bull PRICE distribution for this call — "
            "one row per leg, each with a price range, a probability, and a "
            "trigger. Fill when the call is event-driven enough to branch (e.g. "
            "a pending dilution, an earnings print, a transmission break). Leave "
            "empty when a single path suffices; probabilities should sum to "
            "roughly 1.0."
        ),
    )
    fused_expected_path: str = Field(
        description=(
            "A single concise path sentence stitching the horizons together, e.g. "
            "'tomorrow 175-195 → one week hinges on ADR → one month likely 180-220 "
            "if dilution is mild → one quarter depends on HBM ramp + competition'."
        ),
    )


def render_forecast_report(report: ForecastReport) -> str:
    """Render a ForecastReport to the markdown shape stored in state."""
    parts = ["**时间轴预测：**"]
    for h in report.horizons:
        parts.extend([
            "",
            f"### {h.horizon} — {_dir_cn(h.direction)}（置信度：{_conf_cn(h.confidence)}）",
            f"- **区间：** {h.price_range}",
            f"- **最可能：** {h.most_likely}",
        ])
        if h.scenarios:
            parts.append(f"- **情景：** {h.scenarios}")
        parts.extend([
            f"- **触发 / 日历：** {h.key_trigger_or_calendar}",
            f"- **证伪条件：** {h.falsification}",
        ])
    if report.scenario_table:
        order = {"bear": 0, "base": 1, "bull": 2}
        legs = sorted(report.scenario_table, key=lambda x: order.get(x.label, 1))
        parts.extend([
            "",
            "**情景分布（标的层面）：**",
            "| 情景 | 价位区间 | 概率 | 触发条件 |",
            "|---|---|---:|---|",
        ])
        for s in legs:
            parts.append(
                f"| {s.label.capitalize()} | {s.price_range} | "
                f"{s.probability * 100:.0f}% | {s.trigger} |"
            )
    parts.extend(["", f"**预期路径：** {report.fused_expected_path}"])
    return "\n".join(parts)
