"""Tests for the OrchestrationPlan schema + the rendered-plan parser.

The parser (``selected_analyst_keys``) is what analyst nodes call to decide
whether to noop, so it must round-trip the renderer exactly — including the
``**`` bold-wrap quirk where the colon sits inside the bold markers.
"""

from __future__ import annotations

from dromx.agents.analysts.orchestrator import _ALL_KEYS, _force_all_plan
from dromx.agents.schemas import (
    OrchestrationPlan,
    orchestrator_skills_for,
    render_orchestration_plan,
    selected_analyst_keys,
)

_FULL = {"market", "sentiment", "news", "fundamentals", "industry"}


def test_render_and_parse_round_trip():
    plan = OrchestrationPlan(
        analysts=[
            {"key": "market", "depth": "deep", "priority": 1, "skills": ["ma50-hunting"]},
            {"key": "news", "depth": "standard", "priority": 2, "skills": []},
        ],
        skip_research_layer=False,
        reasoning="r",
    )
    md = render_orchestration_plan(plan)
    assert selected_analyst_keys(md) == {"market", "news"}


def test_selected_empty_returns_full_set():
    assert selected_analyst_keys("") == _FULL
    assert selected_analyst_keys("## other\n**foo:** bar") == _FULL


def test_force_all_plan_covers_every_analyst():
    plan = _force_all_plan()
    assert [a.key for a in plan.analysts] == _ALL_KEYS
    assert selected_analyst_keys(render_orchestration_plan(plan)) == set(_ALL_KEYS)


def test_skills_and_skip_fields_round_trip():
    plan = OrchestrationPlan(
        analysts=[{"key": "market", "skills": ["ma50-hunting", "semiconductor-cycle"]}],
        skip_research_layer=True,
        reasoning="x",
    )
    assert plan.analysts[0].skills == ["ma50-hunting", "semiconductor-cycle"]
    assert plan.skip_research_layer is True


def test_orchestrator_skills_for_parses_table_row():
    plan = OrchestrationPlan(
        analysts=[
            {"key": "news", "skills": ["adr-shelf-offering", "korea-cross-market"]},
            {"key": "market", "skills": ["ma50-hunting"]},
        ],
        skip_research_layer=False, reasoning="r",
    )
    md = render_orchestration_plan(plan)
    assert orchestrator_skills_for(md, "news") == ["adr-shelf-offering", "korea-cross-market"]
    assert orchestrator_skills_for(md, "market") == ["ma50-hunting"]


def test_orchestrator_skills_for_absent_analyst_returns_empty():
    plan = OrchestrationPlan(
        analysts=[{"key": "news", "skills": ["adr-shelf-offering"]}],
        skip_research_layer=False, reasoning="r",
    )
    assert orchestrator_skills_for(render_orchestration_plan(plan), "fundamentals") == []


def test_orchestrator_skills_for_empty_plan_returns_empty():
    assert orchestrator_skills_for("", "news") == []
    assert orchestrator_skills_for("## no table here", "news") == []
