"""Tests for the Re-Analysis node (v0.4 M3).

A static graph can't route back to an earlier analyst, so Re-Analysis is a
forward node that re-examines each target analyst's report in light of the
Event Impact assessment and overwrites the report_key. Best-effort: empty
targets / unknown keys / empty reports / short outputs are all skipped.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tradingagents.agents.analysts.re_analysis import _KEY_TO_REPORT, create_re_analysis

_LONG = "UPDATED REPORT CONTENT THAT IS LONG ENOUGH TO PASS THE FIFTY CHAR MINIMUM CHECK"


def _state(targets, **over):
    s = {
        "company_of_interest": "MU",
        "trade_date": "2026-07-09",
        "instrument_context": "",
        "event_impact": "**事件冲击：** 8/10 — capital raise re-rates the structure",
        "reanalysis_targets": targets,
        "news_report": "ORIGINAL NEWS REPORT",
        "fundamentals_report": "ORIGINAL FUNDAMENTALS REPORT",
    }
    s.update(over)
    return s


def test_key_map_covers_all_five_analysts():
    assert set(_KEY_TO_REPORT) == {"market", "news", "sentiment", "fundamentals", "industry"}


def test_no_targets_returns_empty():
    llm = MagicMock()
    assert create_re_analysis(llm)(_state([])) == {}
    llm.invoke.assert_not_called()


def test_unknown_key_skipped():
    llm = MagicMock()
    assert create_re_analysis(llm)(_state(["does_not_exist"])) == {}
    llm.invoke.assert_not_called()


def test_empty_report_skipped():
    llm = MagicMock()
    assert create_re_analysis(llm)(_state(["news"], news_report="")) == {}
    llm.invoke.assert_not_called()


def test_re_examines_target_and_overwrites():
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=MagicMock(content=_LONG))
    out = create_re_analysis(llm)(_state(["news"]))
    assert out == {"news_report": _LONG}


def test_short_output_is_rejected_leaving_original_intact():
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=MagicMock(content="too short"))  # < 50 chars
    assert create_re_analysis(llm)(_state(["news"])) == {}


def test_multiple_targets_each_updated():
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=MagicMock(content=_LONG))
    out = create_re_analysis(llm)(_state(["news", "fundamentals"]))
    assert set(out) == {"news_report", "fundamentals_report"}
    assert llm.invoke.call_count == 2


def test_lens_label_mapped_to_key():
    """LLMs sometimes write lens labels (Technical/News) instead of keys into
    reanalysis_targets; Re-Analysis maps them back so the report is still found."""
    llm = MagicMock()
    llm.invoke = MagicMock(return_value=MagicMock(content=_LONG))
    # "Technical" is the lens label for market; "News" is both a lens and a key
    out = create_re_analysis(llm)(_state(
        ["Technical", "News"], market_report="ORIGINAL MARKET REPORT"))
    assert set(out) == {"market_report", "news_report"}
