"""Tests for the ForecastReport scenario_table field (P1 name-level price table)."""

from __future__ import annotations

from tradingagents.agents.schemas.forecast import (
    ForecastHorizon,
    ForecastReport,
    PriceScenario,
    render_forecast_report,
)


def _horizon(label: str = "T+1") -> ForecastHorizon:
    return ForecastHorizon(
        horizon=label,
        price_range="100-110",
        direction="Mildly Bearish",
        most_likely="drifts lower on the open",
        key_trigger_or_calendar="the overnight lead",
        falsification="a close above 110",
        confidence="medium",
    )


def test_scenario_table_rendered_and_ordered():
    """Three legs render as a table, ordered bear → base → bull."""
    r = ForecastReport(
        horizons=[_horizon()],
        scenario_table=[
            PriceScenario(label="bull", price_range="112-118", probability=0.15, trigger="bounce"),
            PriceScenario(label="bear", price_range="98-103", probability=0.35, trigger="breaks 2200"),
            PriceScenario(label="base", price_range="105-110", probability=0.50, trigger="holds"),
        ],
        fused_expected_path="path sentence",
    )
    out = render_forecast_report(r)
    assert "情景分布" in out
    assert "| Bear | 98-103 | 35% |" in out
    assert "| Base | 105-110 | 50% |" in out
    assert "| Bull | 112-118 | 15% |" in out
    # ordering is bear -> base -> bull regardless of input order
    assert out.index("Bear") < out.index("Base") < out.index("Bull")


def test_scenario_table_omitted_when_empty():
    r = ForecastReport(horizons=[_horizon()], fused_expected_path="path")
    out = render_forecast_report(r)
    assert "情景分布" not in out
    assert "预期路径" in out  # rest of the report intact


def test_probability_percent_string_coerced():
    """'50%' and 35 both fold to a fraction, like the analyst Scenario."""
    s1 = PriceScenario(label="base", price_range="100-110", probability="50%", trigger="x")
    assert s1.probability == 0.5
    s2 = PriceScenario(label="base", price_range="100-110", probability=35, trigger="x")
    assert s2.probability == 0.35
    s3 = PriceScenario(label="base", price_range="100-110", probability=0.15, trigger="x")
    assert s3.probability == 0.15
