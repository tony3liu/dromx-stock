"""Tests for the Portfolio Manager v0.4 branch (Phase 5: PM with tools).

PM upgrades from a single structured call to a react agent loop with a
``read_analyst_report`` tool (closure over state — pulls an analyst's FULL
original report, not the aggregated summary) plus the raw-data tools. The
mock-LLM path degrades to v0.3; the read_analyst_report closure logic is
verified by capturing the tools list handed to the invoker.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import tradingagents.agents.utils.agent_loop as al
from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG


def _state(**over):
    s = {
        "company_of_interest": "MU", "trade_date": "2026-07-09",
        "instrument_context": "", "regime_report": "Uptrend with low volatility",
        "framework_note": "", "market_context": "",
        "signal_aggregation": "**融合信号:** Bullish (Strong)",
        "key_question": "Q?", "event_impact": "**事件冲击:** 3/10 — no change",
        "risk_consensus": "", "forecast_report": "",
        "reward_risk_report": "", "tailrisk_report": "", "regime_risk_report": "",
        "investment_plan": "research plan", "trader_investment_plan": "trader plan",
        "past_context": "", "portfolio_context": "", "position_context": "",
        "market_report": "FULL MARKET REPORT", "news_report": "FULL NEWS REPORT",
        "instrument_type": "equity",
    }
    s.update(over)
    return s


def _mock_llm(content="PM DECISION"):
    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(side_effect=Exception("structured unavailable"))
    llm.invoke = MagicMock(return_value=MagicMock(content=content))
    return llm


def test_v03_fallback():
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": False}
    set_config(cfg)
    out = create_portfolio_manager(_mock_llm("V03 PM DECISION"))(_state())
    assert "V03 PM DECISION" in out["final_trade_decision"]


def test_v04_degrades_to_v03_under_mock_llm():
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": True, "pm_max_iterations": 8}
    set_config(cfg)
    out = create_portfolio_manager(_mock_llm("V04 PM DECISION"))(_state())
    assert "V04 PM DECISION" in out["final_trade_decision"]


def test_read_analyst_report_closure_returns_full_report(monkeypatch):
    """The read_analyst_report tool is a closure over state — verify it pulls
    the FULL analyst report (not the summary) and handles unknown/empty."""
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": True, "pm_max_iterations": 8}
    set_config(cfg)

    captured = {}

    def fake_invoker(*, llm, tools, schema, render, agent_name, system_message,
                     skills, instruction, max_iterations):
        captured["tools"] = tools
        captured["max_iterations"] = max_iterations
        return lambda: "PM DECISION"

    monkeypatch.setattr(al, "build_analyst_react_invoker", fake_invoker)
    create_portfolio_manager(MagicMock())(_state())

    names = [getattr(t, "name", "") for t in captured["tools"]]
    assert "read_analyst_report" in names
    assert "_get_stock_data" in names and "_get_fundamentals" in names and "_get_news" in names
    assert "position_simulate" in names
    assert "web_read" in names
    assert captured["max_iterations"] == 8  # pm_max_iterations, not the analyst 5

    rat = next(t for t in captured["tools"] if getattr(t, "name", "") == "read_analyst_report")
    assert "FULL MARKET REPORT" in rat.invoke({"analyst_name": "market"})
    assert "FULL NEWS REPORT" in rat.invoke({"analyst_name": "news"})
    assert "unknown" in rat.invoke({"analyst_name": "zzz"}).lower()
    assert "empty" in rat.invoke({"analyst_name": "sentiment"}).lower()  # not in state

    # position_simulate is a pure P&L calculator (no state needed)
    ps = next(t for t in captured["tools"] if getattr(t, "name", "") == "position_simulate")
    pout = ps.invoke({"shares": 800, "cost_basis": 166.875, "current_price": 96,
                      "target_price": 110, "stop_price": 85})
    assert "Position simulate" in pout and "-42" in pout  # ~-42.5% loss

    # Verify closure tools auto-inject ticker — calling with no args works
    stock = next(t for t in captured["tools"] if getattr(t, "name", "") == "_get_stock_data")
    assert stock.invoke({})  # no ticker arg needed — closure provides it
