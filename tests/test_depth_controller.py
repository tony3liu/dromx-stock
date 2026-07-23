"""Tests for the DepthController node (v0.4 M3).

The node writes ``depth_decision`` (rendered markdown) + ``trigger_reanalysis``
(bool) + ``reanalysis_targets`` (analyst keys). The typed structured call is
exercised directly (mock returns a DepthDecision); the free-text fallback's
coarse parse is exercised by making the structured call raise.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tradingagents.agents.analysts.depth_controller import create_depth_controller
from tradingagents.agents.schemas import DepthDecision


def _state(**over):
    s = {
        "company_of_interest": "MU",
        "trade_date": "2026-07-09",
        "instrument_context": "",
        "regime_report": "Uptrend",
        "signal_aggregation": "**融合信号：** Bullish (Strong)",
        "event_impact": "**事件冲击：** 3/10 — no premise change",
        "analysis_depth": "Standard",
    }
    s.update(over)
    return s


def _llm_returning(decision: DepthDecision):
    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(return_value=decision)
    return llm


def test_conclude_no_reanalysis():
    d = DepthDecision(decision="conclude", reasoning="strong agreement, low impact")
    out = create_depth_controller(_llm_returning(d))(_state())
    assert "conclude" in out["depth_decision"]
    assert out["trigger_reanalysis"] is False
    assert out["reanalysis_targets"] == []


def test_deep_dive_with_targets_triggers_reanalysis():
    d = DepthDecision(decision="deep_dive", reasoning="split analysts",
                      recommend_reanalysis_of=["news", "fundamentals"])
    out = create_depth_controller(_llm_returning(d))(_state())
    assert "deep_dive" in out["depth_decision"]
    assert out["trigger_reanalysis"] is True
    assert out["reanalysis_targets"] == ["news", "fundamentals"]


def test_deep_dive_without_targets_does_not_trigger():
    d = DepthDecision(decision="deep_dive", reasoning="high volatility", recommend_reanalysis_of=[])
    out = create_depth_controller(_llm_returning(d))(_state())
    assert out["trigger_reanalysis"] is False
    assert out["reanalysis_targets"] == []


def test_standard_path():
    d = DepthDecision(decision="standard", reasoning="moderate agreement")
    out = create_depth_controller(_llm_returning(d))(_state())
    assert "standard" in out["depth_decision"]
    assert out["trigger_reanalysis"] is False


def test_freetext_fallback_parses_conclude():
    # structured call raises -> free-text fallback -> coarse parse of "conclude"
    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(side_effect=Exception("structured unavailable"))
    llm.invoke = MagicMock(return_value=MagicMock(content="**深度决策:** conclude\n\n**理由:** clear call"))
    out = create_depth_controller(llm)(_state())
    assert "conclude" in out["depth_decision"]
    assert out["trigger_reanalysis"] is False
