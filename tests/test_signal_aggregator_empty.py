"""Empty-report path — Orchestrator can skip an analyst (noop -> empty report);
the Signal Aggregator must not crash or hallucinate a direction for the
skipped lens. The skipped lens comes back direction=None / score=None and is
not counted in the consensus; the remaining lenses still produce a call.
"""

from __future__ import annotations

from tradingagents.agents.analysts.signal_aggregator import (
    aggregate_signals,
    create_signal_aggregator,
)

# fundamentals + industry skipped by the Orchestrator (empty reports);
# the other three lenses are present with a parseable direction header.
_STATE = {
    "company_of_interest": "MU",
    "trade_date": "2026-07-09",
    "regime_report": "**市场状态：** Uptrend / High volatility",
    "market_report": "**技术面观点：** **看跌 Bearish** （置信度：高 High）",
    "sentiment_report": "**综合情绪：** **温和看跌 Mildly Bearish**",
    "news_report": "**新闻面观点：** **中性 Neutral**",
    "fundamentals_report": "",   # Orchestrator skipped fundamentals
    "industry_report": "",       # ... and industry
}


def test_skipped_lens_direction_none_not_hallucinated():
    """A skipped lens (empty report) must parse to direction=None, not a
    fabricated Bullish/Bearish."""
    agg = aggregate_signals(_STATE)
    fund = next(s for s in agg.signals if s.lens == "Fundamentals")
    ind = next(s for s in agg.signals if s.lens == "Industry")
    assert fund.direction is None, "skipped lens must not fabricate a direction"
    assert ind.direction is None
    assert fund.score is None and ind.score is None  # not counted in consensus


def test_consensus_still_computed_from_remaining_lenses():
    """Consensus is computed from the 3 present lenses — no crash, a real call."""
    agg = aggregate_signals(_STATE)
    assert agg.consensus_direction is not None
    assert agg.weighted_score is not None
    # the skipped lenses (score None) are excluded from the weighted score
    scored = [s for s in agg.signals if s.score is not None]
    assert {s.lens for s in scored} == {"Technical", "Sentiment", "News"}


def test_node_path_does_not_crash_and_renders():
    """The full node (not just aggregate_signals) must not crash on empty lenses."""
    out = create_signal_aggregator()(_STATE)
    assert "signal_aggregation" in out and "analysis_depth" in out
    assert "融合信号" in out["signal_aggregation"]
