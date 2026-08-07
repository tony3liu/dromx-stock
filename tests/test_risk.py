"""Tests for the portfolio risk (VaR + stress) module (A1)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

import webapp.backend.risk as risk


def _flat_returns(n: int, level: float) -> list[float]:
    """Constant daily return series (deterministic, easy to assert)."""
    return [level] * n


def _flat_returns_series(n: int, level: float, start: str = "2026-01-05") -> pd.Series:
    """Date-indexed constant return series (for _returns_series mocks)."""
    dates = pd.bdate_range(start, periods=n)
    return pd.Series([level] * n, index=dates)


@pytest.mark.unit
class TestMath:
    def test_percentile(self):
        # 升序（最差在后）：[-5,-4,-3,-2,-1]；q=0.8 → 最差 20% 门槛 = -4
        losses = [-1, -2, -3, -4, -5]
        assert risk._percentile(losses, 0.8) == -4
        assert risk._percentile(losses, 1.0) == -5   # 100% 置信 = 最差情形
        assert risk._percentile([], 0.95) is None

    def test_parametric_var_flat_series(self):
        # 恒定收益 → 方差 0 → VaR ≈ 0
        r = _flat_returns(60, 0.001)
        v = risk._parametric_var(r, risk._Z[0.95])
        assert v is not None and abs(v) < 1e-9

    def test_parametric_var_matches_std(self):
        r = [0.01, -0.01, 0.02, -0.02, 0.005, -0.005, 0.03, -0.03, 0.0, 0.0]
        v = risk._parametric_var(r, risk._Z[0.95])
        mean = sum(r) / len(r)
        sd = math.sqrt(sum((x - mean) ** 2 for x in r) / (len(r) - 1))
        assert v == pytest.approx(risk._Z[0.95] * sd)

    def test_beta(self):
        a = [0.01 * i for i in range(1, 11)]      # perfectly correlated w/ b
        b = [0.02 * i for i in range(1, 11)]
        assert risk._beta(a, b) == pytest.approx(0.5, rel=1e-6)

    def test_beta_constant_input(self):
        a = [0.001] * 10
        b = [0.001] * 10
        assert risk._beta(a, b) is None  # 零方差 → 无意义


@pytest.mark.unit
class TestBuildReport:
    def test_no_holdings(self, monkeypatch):
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {"holdings": []})
        out = risk.build_risk_report()
        assert out["verdict"] == "no_holdings"
        assert out["book"] is None

    def test_holdings_without_price_skipped(self, monkeypatch):
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "AAPL", "shares": 100, "cost_basis": 150, "last_close": None}]})
        out = risk.build_risk_report()
        assert out["verdict"] == "no_holdings"

    def test_single_name_book(self, monkeypatch):
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "AAPL", "shares": 100, "cost_basis": 150, "last_close": 200.0}]})
        monkeypatch.setattr(risk, "_returns_series", lambda s, d, lb=120: _flat_returns_series(60, 0.01))
        out = risk.build_risk_report()
        assert out["book_value"] == 20_000.0
        assert out["book"] is not None
        # 恒定 +1% 收益 → 无亏损日，历史 VaR 为负（最坏情形仍是盈利）
        assert out["book"]["var"]["p95"]["historical_value"] == pytest.approx(-200.0, rel=1e-6)
        assert out["book"]["annualized_vol_pct"] == 0.0

    def test_two_names_component_var(self, monkeypatch):
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "AAPL", "shares": 100, "cost_basis": 150, "last_close": 200.0},
                         {"ticker": "MSFT", "shares": 50, "cost_basis": 300, "last_close": 400.0}]})
        # AAPL 恒定 -1%，MSFT 恒定 +1% → 组合分散，AAPL 主导风险
        ret = {"AAPL": _flat_returns_series(60, -0.01), "MSFT": _flat_returns_series(60, 0.01)}
        monkeypatch.setattr(risk, "_returns_series", lambda s, d, lb=120: ret[s])
        out = risk.build_risk_report()
        assert out["book_value"] == 20_000 + 20_000
        assert len(out["per_name"]) == 2
        # AAPL 权重 50%
        aapl = next(c for c in out["per_name"] if c["ticker"] == "AAPL")
        assert aapl["weight_pct"] == 50.0
        # 组合日收益 = 0.5*(-1%) + 0.5*(+1%) = 0 → VaR = 0
        assert out["book"]["var"]["p95"]["historical_value"] == 0.0
        # stress: flat -10% / -20% 为书面的 book_value 百分比
        assert out["stress"]["flat_m10"] == pytest.approx(-4_000.0, rel=1e-6)
        assert out["stress"]["flat_m20"] == pytest.approx(-8_000.0, rel=1e-6)

    def test_stress_crash_day(self, monkeypatch):
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "AAPL", "shares": 100, "cost_basis": 150, "last_close": 200.0}]})
        # 最后一天 -5%，其余 0 → 历史最差单日 -5%
        r = [0.0] * 59 + [-0.05]
        monkeypatch.setattr(risk, "_returns_series",
                            lambda s, d, lb=120: pd.Series(r, index=pd.bdate_range("2026-01-05", periods=60)))
        out = risk.build_risk_report()
        assert out["stress"]["worst_day_pct"] == pytest.approx(-5.0, rel=1e-6)
        assert out["stress"]["crash_1d"] == pytest.approx(-1_000.0, rel=1e-6)
        # 60 天窗口仅 1 天 -5%：95% 分位（第 57 个最差）落在 0
        assert out["book"]["var"]["p95"]["historical_pct"] == pytest.approx(0.0, rel=1e-6)
        # 99% 分位（ceil(0.99*60)-1 = 59）才触到那唯一的 -5% 日
        assert out["book"]["var"]["p99"]["historical_pct"] == pytest.approx(5.0, rel=1e-6)


    def test_cross_market_alignment(self, monkeypatch):
        """不同交易日历的标的不再按位置错位配对（跨市场对齐修复）。"""
        monkeypatch.setattr(risk.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "US1", "shares": 1, "cost_basis": 100, "last_close": 100.0},
                         {"ticker": "HK1", "shares": 1, "cost_basis": 100, "last_close": 100.0}]})
        # US1 有 60 个交易日；HK1 只有 55 个，且日期错开（模拟不同节假日）
        us_dates = pd.bdate_range("2026-01-05", periods=60)
        hk_dates = [d for d in us_dates if d.day != 15][:55]  # 去掉每月 15 号
        hk_dates = pd.DatetimeIndex(hk_dates)
        # US1 恒 +1%，HK1 恒 -1% → 若正确按共同日期对齐，组合收益 = 0
        us_r = pd.Series([0.01] * 60, index=us_dates)
        hk_r = pd.Series([-0.01] * len(hk_dates), index=hk_dates)
        monkeypatch.setattr(risk, "_returns_series",
                            lambda s, d, lb=120: us_r if s == "US1" else hk_r)
        out = risk.build_risk_report()
        # 共同日期数 = 60 - (每月15号的次数) ≈ 55 左右
        assert out["book"]["n_days"] == len(set(us_dates) & set(hk_dates))
        # 组合 = 0.5*1% + 0.5*(-1%) = 0 → VaR ≈ 0
        assert abs(out["book"]["var"]["p95"]["historical_pct"]) < 0.001


class TestVerdict:
    def _book(self):
        return {"book_value": 10000, "annualized_vol_pct": 20.0,
                "var": {"p95": {"historical_value": 500.0, "historical_pct": 5.0}}}

    def test_concentration_warning_single_name(self):
        v = risk._verdict(self._book(), {"crash_1d": -300.0, "worst_day_pct": -3.0},
                          {"AAPL": 1.0}, [])
        assert "高度集中" in v["message"]
        assert v["level"] == "elevated"

    def test_diversified_no_warning(self):
        v = risk._verdict(self._book(), {"crash_1d": -300.0, "worst_day_pct": -3.0},
                          {"AAPL": 0.3, "MSFT": 0.3, "TSM": 0.4}, [])
        assert "分散度尚可" in v["message"]

    def test_empty_weights(self):
        v = risk._verdict(self._book(), {"crash_1d": None, "worst_day_pct": None}, {}, ["X"])
        assert "无法取得行情" in v["message"]
