"""Regression: agent_loop.enabled=false reverts to v0.3 (PRD M7 contract).

v0.4 is fully feature-flagged. With the flag off the graph has no
Orchestrator / DepthController / Re-Analysis nodes, and analysts take the
v0.3 single-call path — ``build_analyst_loop_invoker`` is never invoked.
This is the promise that existing users are unaffected by the upgrade.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import dromx.agents.analysts.news_analyst as na
import dromx.agents.utils.agent_loop as al
from dromx.dataflows.config import set_config
from dromx.default_config import DEFAULT_CONFIG
from dromx.graph.conditional_logic import ConditionalLogic
from dromx.graph.setup import GraphSetup

_ALL = ("market", "social", "news", "fundamentals", "industry")


def _per_on():
    return {k: {"enabled": True} for k in
            ["market", "sentiment", "news", "fundamentals", "industry"]}


def _v03_cfg():
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": False, "per_analyst": _per_on()}
    return cfg


def _mock_llm():
    llm = MagicMock()
    llm.with_structured_output = MagicMock(return_value=MagicMock())
    return llm


def test_v03_graph_has_no_v04_nodes():
    set_config(_v03_cfg())
    wf = GraphSetup(_mock_llm(), _mock_llm(), {}, ConditionalLogic()).setup_graph(_ALL)
    for node in ("Orchestrator", "Depth Controller", "Re-Analysis"):
        assert node not in wf.nodes, f"{node} should not exist in v0.3 graph"
    wf.compile()


def test_v03_analyst_never_invokes_loop(monkeypatch):
    """With the flag off, the news analyst takes the v0.3 single-call path —
    build_analyst_loop_invoker is never called."""
    set_config(_v03_cfg())
    monkeypatch.setattr(na.get_news, "func", lambda *a, **k: "NEWS")
    monkeypatch.setattr(na.get_global_news, "func", lambda *a, **k: "GLOBAL")
    monkeypatch.setattr(na.get_macro_indicators, "func", lambda *a, **k: "MACRO")
    monkeypatch.setattr(na.get_prediction_markets, "func", lambda *a, **k: "PRED")

    called = []

    def spy(**kw):
        called.append(True)
        return "LOOP"

    monkeypatch.setattr(al, "build_analyst_loop_invoker", spy)

    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(side_effect=Exception("structured unavailable"))
    llm.invoke = MagicMock(return_value=MagicMock(content="V03 REPORT"))

    out = na.create_news_analyst(llm)({
        "company_of_interest": "MU", "trade_date": "2026-07-09",
        "instrument_context": "", "regime_report": "Uptrend",
        "instrument_type": "equity",
    })
    assert called == []  # the v0.4 loop helper was never invoked
    assert "V03 REPORT" in out["news_report"]
