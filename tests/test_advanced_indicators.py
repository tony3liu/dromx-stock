"""Tests for advanced technical indicators (P0-1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dromx.dataflows.advanced_indicators import (
    adx,
    atr,
    compute_advanced_indicators,
    ichimoku,
    list_advanced_indicators,
    mfi,
    obv,
)


def _sample_ohlcv(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2025-01-01", periods=n)
    close = 100 * (1 + rng.normal(0.0005, 0.02, n)).cumprod()
    high = close * (1 + np.abs(rng.normal(0, 0.01, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    vol = rng.integers(1_000_000, 5_000_000, n)
    return pd.DataFrame(
        {"Date": dates, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}
    )


@pytest.mark.unit
class TestIndicatorRegistry:
    def test_registry_has_33_indicators(self):
        assert len(list_advanced_indicators()) >= 33

    def test_all_indicators_compute_on_sample(self):
        df = _sample_ohlcv()
        res = compute_advanced_indicators(df)
        assert "adx" in res
        assert "ichimoku_verdict" in res
        assert "mfi" in res
        # 所有数值应有限（非 NaN）
        for k, v in res.items():
            if isinstance(v, float):
                assert not np.isnan(v), f"{k} is NaN"

    def test_subset_selection(self):
        df = _sample_ohlcv()
        res = compute_advanced_indicators(df, ["adx", "mfi"])
        assert "adx" in res and "mfi" in res
        assert "kst" not in res

    def test_unknown_indicator_warns_and_continues(self):
        df = _sample_ohlcv()
        res = compute_advanced_indicators(df, ["adx", "no_such_indicator"])
        assert "adx" in res

    def test_empty_frame_returns_error(self):
        res = compute_advanced_indicators(pd.DataFrame())
        assert "error" in res


@pytest.mark.unit
class TestIndicatorMath:
    def test_ichimoku_detects_uptrend(self):
        # 单调上涨序列 → 价格应在云层上方
        n = 120
        dates = pd.bdate_range("2025-01-01", periods=n)
        close = pd.Series(np.linspace(100, 200, n))
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": close * 0.99,
                "High": close * 1.02,
                "Low": close * 0.98,
                "Close": close,
                "Volume": np.full(n, 1_000_000),
            }
        )
        res = ichimoku(df)
        assert "多头" in res["ichimoku_verdict"]

    def test_atr_positive_and_proportional(self):
        df = _sample_ohlcv()
        res = atr(df)
        assert res["atr"] > 0
        assert res["atr_pct_of_price"] > 0

    def test_mfi_bounded(self):
        df = _sample_ohlcv()
        res = mfi(df)
        assert 0 <= res["mfi"] <= 100

    def test_obv_monotonic_trend(self):
        # 每天上涨 + 固定量 → OBV 严格递增
        n = 60
        dates = pd.bdate_range("2025-01-01", periods=n)
        close = pd.Series(np.linspace(100, 150, n))
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": close * 0.99,
                "High": close * 1.01,
                "Low": close * 0.99,
                "Close": close,
                "Volume": np.full(n, 1_000_000),
            }
        )
        res = obv(df)
        assert res["obv"] > 0
        assert "上行" in res["obv_verdict"] or "支持" in res["obv_verdict"]

    def test_adx_weak_in_range(self):
        # 震荡数据 → ADX 应偏低
        n = 120
        rng = np.random.default_rng(7)
        dates = pd.bdate_range("2025-01-01", periods=n)
        close = pd.Series(100 + rng.normal(0, 1.0, n).cumsum() * 0.3)
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": close * 0.995,
                "High": close + 1.5,
                "Low": close - 1.5,
                "Close": close,
                "Volume": np.full(n, 1_000_000),
            }
        )
        res = adx(df)
        assert res["adx"] < 40  # 震荡市 ADX 通常低于强趋势阈值 25-40
