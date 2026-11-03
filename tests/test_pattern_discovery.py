"""Tests for the pattern-discovery forensics engine.

Direction-neutral: the same engine must surface a short hunt (Low touching an
anchor), a breakout (High touching an anchor), a range-bound prior-low touch,
and honestly return '' on a normal tape. The anchor is always the smallest-
deviation candidate — never assumed to be MA50.
"""

from __future__ import annotations

import pandas as pd
import dromx.dataflows.pattern_discovery as pdm


def _make_df(rows):
    """rows: list of (Open, High, Low, Close)."""
    dates = pd.date_range("2026-05-01", periods=len(rows), freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Open": [r[0] for r in rows],
        "High": [r[1] for r in rows],
        "Low": [r[2] for r in rows],
        "Close": [r[3] for r in rows],
    })


def _normal(c=100.0):
    """A ~1% amplitude normal day centered on c."""
    return (c, c + 0.5, c - 0.5, c)


def _patch_ohlcv(monkeypatch, df):
    import dromx.dataflows.stockstats_utils as ss
    monkeypatch.setattr(ss, "load_ohlcv", lambda *a, **k: df)


def test_short_hunt_low_touches_ma50(monkeypatch):
    """Anomaly days where the LOW touches MA50 precisely → short-direction read."""
    rows = [_normal(99.95) for _ in range(50)]
    highs = [115.0, 117.0, 119.0]  # increasing so prior-high isn't re-touched at 0%
    for i in range(10):
        if i in (0, 2, 4):  # 3 anomaly days
            # Low=99.94 vs MA50=99.95 → -0.01%; rising High (big amplitude)
            rows.append((99.0, highs[i // 2], 99.94, 99.95))
        else:
            rows.append(_normal(99.95))
    _patch_ohlcv(monkeypatch, _make_df(rows))

    out = pdm.build_pattern_discovery("000660.KS", "2026-07-08")
    assert "取证发现" in out
    assert "MA50" in out
    assert "算法精度" in out
    assert "做空方向" in out
    assert "低 99.94" in out


def test_breakout_high_touches_ma50(monkeypatch):
    """Anomaly days where the HIGH touches MA50 precisely → long-direction read."""
    rows = [_normal(99.95) for _ in range(50)]
    lows = [81.0, 83.0, 85.0]  # increasing so prior-low / round-80 isn't re-touched at 0%
    for i in range(10):
        if i in (0, 2, 4):
            # High=99.955 vs MA50=99.95 → +0.005%; Low=80 (big amplitude)
            rows.append((100.0, 99.955, lows[i // 2], 99.95))
        else:
            rows.append(_normal(99.95))
    _patch_ohlcv(monkeypatch, _make_df(rows))

    out = pdm.build_pattern_discovery("000660.KS", "2026-07-08")
    assert "MA50" in out
    assert "算法精度" in out
    assert "做多方向" in out
    assert "高 99.9" in out  # 99.955 → :.2f renders 99.95 or 99.96, both contain "高 99.9"


def test_prior_low_wins_over_ma50(monkeypatch):
    """When the prior low is closer than MA50, IT wins — anchor is not assumed."""
    rows = [_normal(100.0) for _ in range(50)]  # MA50=100, normal Low=99.5
    for i in range(10):
        if i in (0, 2, 4):
            # Low=99.5 touches prior low 99.5 (dev 0%); MA50=100 is 0.5% away
            rows.append((100.0, 119.5, 99.5, 100.0))
        else:
            rows.append(_normal(100.0))
    _patch_ohlcv(monkeypatch, _make_df(rows))

    out = pdm.build_pattern_discovery("X", "2026-07-08")
    assert "前低" in out
    assert "算法精度" in out


def test_normal_market_returns_empty(monkeypatch):
    """No anomaly days (all ~1% amplitude) → '' — don't fabricate a pattern."""
    rows = [_normal(100.0) for _ in range(60)]
    _patch_ohlcv(monkeypatch, _make_df(rows))
    assert pdm.build_pattern_discovery("X", "2026-07-08") == ""


def test_dispersed_when_no_anchor_dominates(monkeypatch):
    """Two anomaly days touching different anchors (1 win each) → 'dispersed'."""
    rows = [_normal(100.0) for _ in range(50)]
    rows.append((100.0, 119.5, 99.5, 100.0))   # day 51: Low touches prior low 99.5
    rows.append(_normal(100.0))
    rows.append((100.0, 119.5, 100.0, 100.0))  # day 53: Low touches MA50 100
    rows += [_normal(100.0) for _ in range(7)]
    _patch_ohlcv(monkeypatch, _make_df(rows))

    out = pdm.build_pattern_discovery("X", "2026-07-08")
    assert "分散" in out
    assert "算法精度" not in out


def test_thin_data_returns_empty(monkeypatch):
    """Fewer rows than the minimum → ''."""
    rows = [_normal(100.0) for _ in range(10)]  # < _MIN_ROWS (20)
    _patch_ohlcv(monkeypatch, _make_df(rows))
    assert pdm.build_pattern_discovery("X", "2026-07-08") == ""
