"""Tests for the v0.4 graph setup: Orchestrator wiring + noop + v0.3 fallback.

Uses a MagicMock LLM (``with_structured_output`` returns a mock) so the graph
compiles without a real provider. ``force_all_analysts=True`` makes the
Orchestrator write a deterministic full plan (no LLM invoke), so these tests
exercise topology + noop only, not the LLM call path.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from dromx.dataflows.config import set_config
from dromx.default_config import DEFAULT_CONFIG
from dromx.graph.conditional_logic import ConditionalLogic
from dromx.graph.setup import GraphSetup, _noop_aware

_ALL = ("market", "social", "news", "fundamentals", "industry")


def _per_analyst_on():
    return {k: {"enabled": True} for k in
            ["market", "sentiment", "news", "fundamentals", "industry"]}


def _mock_llm():
    llm = MagicMock()
    llm.with_structured_output = MagicMock(return_value=MagicMock())
    return llm


def _setup(agent_loop_enabled: bool, force_all: bool = False):
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": agent_loop_enabled, "per_analyst": _per_analyst_on()}
    cfg["orchestration"] = {"auto_select_analysts": True, "force_all_analysts": force_all}
    set_config(cfg)
    llm = _mock_llm()
    return GraphSetup(llm, llm, {}, ConditionalLogic()).setup_graph(_ALL)


def test_v04_has_orchestrator_and_compiles():
    wf = _setup(True, force_all=True)
    assert "Orchestrator" in wf.nodes
    wf.compile()  # topology must be valid (no dangling edges / fan-in deadlock)


def test_v03_has_no_orchestrator_and_compiles():
    wf = _setup(False)
    assert "Orchestrator" not in wf.nodes
    wf.compile()


def test_noop_aware_unselected_returns_empty_report():
    def node(state):
        return {"market_report": "RAN"}
    w = _noop_aware(node, "market", "market_report")
    assert w({"orchestration_plan": "**选中分析师:** news"}) == {"market_report": ""}


def test_noop_aware_selected_runs_node():
    def node(state):
        return {"market_report": "RAN"}
    w = _noop_aware(node, "market", "market_report")
    assert w({"orchestration_plan": "**选中分析师:** market,news"}) == {"market_report": "RAN"}


def test_noop_aware_no_plan_runs_node():
    def node(state):
        return {"market_report": "RAN"}
    w = _noop_aware(node, "market", "market_report")
    assert w({}) == {"market_report": "RAN"}
