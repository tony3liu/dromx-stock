"""Tests for the IndustryReport competition_matrix field (P1 horizontal table)."""

from __future__ import annotations

from tradingagents.agents.schemas.analysts import (
    AnalystDirection,
    IndustryPhase,
    IndustryReport,
    MoatTrend,
    render_industry_report,
)


def _report(**kw) -> IndustryReport:
    """Build a minimal valid IndustryReport, overriding only what the test needs."""
    overrides = {
        "competition_matrix": "",
    }
    overrides.update(kw)
    return IndustryReport(
        direction=AnalystDirection.NEUTRAL,
        confidence="medium",
        scenarios=[],
        industry_phase=IndustryPhase.UNCLEAR,
        competitive_moat=MoatTrend.STABLE,
        key_dependency="a sole-source input",
        disruption_risk="a substitution force",
        key_evidence=["- [data] something fetched"],
        risks=["a risk"],
        narrative="A short narrative.",
        **overrides,
    )


def test_competition_matrix_rendered_when_present():
    table = "| Player | Status | Share |\n|---|---|---|\n| SK Hynix | leading | 55% |"
    out = render_industry_report(_report(competition_matrix=table))
    assert "竞争格局横向对比" in out
    assert "| SK Hynix | leading | 55% |" in out


def test_competition_matrix_omitted_when_empty():
    out = render_industry_report(_report())
    assert "竞争格局横向对比" not in out
    # The rest of the report is still intact.
    assert "关键依赖" in out
    assert "颠覆风险" in out


def test_competition_matrix_omitted_when_whitespace_only():
    out = render_industry_report(_report(competition_matrix="   \n  "))
    assert "竞争格局横向对比" not in out
