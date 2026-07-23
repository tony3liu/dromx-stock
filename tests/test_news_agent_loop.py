"""Tests for the News Analyst v0.4 branch selection + v0.3 fallback.

Does NOT run a real react-agent loop (that needs a live LLM — covered by the
M4 end-to-end run). Instead: the branch picks ``_run_news_agent_loop`` when
the flag is on, the v0.3 single-call path when off (or per-analyst off), and
the v0.3 path produces a report end-to-end with a mock LLM + monkeypatched
pre-fetch (no network).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import tradingagents.agents.analysts.news_analyst as na
from tradingagents.agents.analysts.news_analyst import _extract_market, create_news_analyst
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG


def _per_analyst_on():
    return {k: {"enabled": True} for k in
            ["market", "sentiment", "news", "fundamentals", "industry"]}


def _stub_prefetch(monkeypatch):
    """Make every pre-fetch return a placeholder so the node never hits the network."""
    monkeypatch.setattr(na.get_news, "func", lambda *a, **k: "<news>")
    monkeypatch.setattr(na.get_global_news, "func", lambda *a, **k: "<global>")
    monkeypatch.setattr(na.get_macro_indicators, "func", lambda *a, **k: "<macro>")
    monkeypatch.setattr(na.get_prediction_markets, "func", lambda *a, **k: "<pred>")


def _state():
    return {
        "company_of_interest": "MU",
        "trade_date": "2026-07-09",
        "instrument_type": "equity",
        "regime_report": "Uptrend with low volatility",
    }


def test_extract_market_by_suffix():
    assert _extract_market("MU") == "US"
    assert _extract_market("07709.HK") == "HK"
    assert _extract_market("000660.KS") == "KR"
    assert _extract_market("600519.SS") == "CN"


def test_v03_fallback_returns_report(monkeypatch):
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": False, "per_analyst": _per_analyst_on()}
    set_config(cfg)
    _stub_prefetch(monkeypatch)

    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(side_effect=Exception("structured unavailable"))
    llm.invoke = MagicMock(return_value=MagicMock(content="FREE-TEXT NEWS REPORT"))

    out = create_news_analyst(llm)(_state())
    assert "FREE-TEXT NEWS REPORT" in out["news_report"]


def test_v04_branch_calls_run_loop(monkeypatch):
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": True, "analyst_max_iterations": 5, "per_analyst": _per_analyst_on()}
    cfg["skills"] = {"enabled": True, "path": "~/.tradingagents/skills/",
                     "auto_load": True, "max_per_analyst": 5,
                     "dynamic_request": True, "max_dynamic_loads": 2}
    set_config(cfg)
    _stub_prefetch(monkeypatch)

    called = {}

    def fake_run(*, llm, cfg, state, ticker, curr_date, system_message):
        called["yes"] = True
        return "LOOP REPORT"

    monkeypatch.setattr(na, "_run_news_agent_loop", fake_run)
    out = create_news_analyst(MagicMock())(_state())
    assert called.get("yes") is True
    assert out["news_report"] == "LOOP REPORT"


def test_v04_per_analyst_off_falls_back_to_v03(monkeypatch):
    per = _per_analyst_on()
    per["news"] = {"enabled": False}  # global on, news specifically off
    cfg = dict(DEFAULT_CONFIG)
    cfg["agent_loop"] = {"enabled": True, "per_analyst": per}
    set_config(cfg)
    _stub_prefetch(monkeypatch)

    called = {}
    monkeypatch.setattr(na, "_run_news_agent_loop",
                        lambda **kw: called.__setitem__("yes", True) or "LOOP")

    llm = MagicMock()
    sl = MagicMock()
    llm.with_structured_output = MagicMock(return_value=sl)
    sl.invoke = MagicMock(side_effect=Exception)
    llm.invoke = MagicMock(return_value=MagicMock(content="V03 REPORT"))

    out = create_news_analyst(llm)(_state())
    assert not called.get("yes")  # loop never invoked
    assert "V03 REPORT" in out["news_report"]
