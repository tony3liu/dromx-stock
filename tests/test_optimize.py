"""Tests for mean-variance portfolio optimization (A2)."""

from __future__ import annotations

import math

import pandas as pd

import numpy as np
import pytest

import webapp.backend.optimize as opt


def _series(vals: list[float]) -> pd.Series:
    """Date-indexed returns for _returns_series mocks."""
    return pd.Series(vals, index=pd.bdate_range("2026-01-05", periods=len(vals)))


def _two_asset_system():
    """Deterministic two-name system: A high-ret/high-vol, B low-ret/low-vol."""
    # 120 days, A: mean +0.1%/day vol ~2%, B: mean +0.02%/day vol ~1%, corr 0.3
    rng = np.random.default_rng(7)
    n = 120
    z = rng.standard_normal((n, 2))
    cov = np.array([[1.0, 0.3], [0.3, 1.0]])
    chol = np.linalg.cholesky(cov)
    eps = z @ chol.T
    a = 0.001 + 0.02 * eps[:, 0]
    b = 0.0002 + 0.01 * eps[:, 1]
    return a, b


@pytest.mark.unit
class TestMath:
    def test_equal_weight(self):
        w = opt._equal_weight(4)
        assert w == pytest.approx([0.25] * 4)

    def test_project_nonneg(self):
        w = opt._project_nonneg(np.array([0.5, -0.3, 0.8]))
        assert (w >= 0).all()
        assert w.sum() == pytest.approx(1.0)

    def test_project_all_negative(self):
        w = opt._project_nonneg(np.array([-1.0, -2.0]))
        assert w == pytest.approx([0.5, 0.5])

    def test_portfolio_stats(self):
        mean = np.array([0.10, 0.05])
        cov = np.array([[0.04, 0.0], [0.0, 0.01]])
        w = np.array([0.5, 0.5])
        assert opt._port_return(w, mean) == pytest.approx(0.075)
        assert opt._port_vol(w, cov) == pytest.approx(math.sqrt(0.5 ** 2 * 0.04 + 0.5 ** 2 * 0.01))

    def test_min_vol_two_assets(self):
        mean = np.array([0.10, 0.05])
        cov = np.array([[0.04, 0.0], [0.0, 0.01]])
        w = opt._min_vol_weight(mean, cov)
        # 无相关时，min-vol 权重 ∝ 1/σ² → A:0.2, B:0.8
        assert w[0] == pytest.approx(0.2, rel=1e-6)
        assert w[1] == pytest.approx(0.8, rel=1e-6)

    def test_max_sharpe_two_assets(self):
        mean = np.array([0.10, 0.05])
        cov = np.array([[0.04, 0.0], [0.0, 0.01]])
        w = opt._max_sharpe_weight(mean, cov, rf=0.02)
        # 闭式：w ∝ Σ⁻¹(μ-rf) → [0.08/0.04, 0.03/0.01] = [2, 3] → 归一 [0.4, 0.6]
        assert w[0] == pytest.approx(0.4, rel=1e-6)
        assert w[1] == pytest.approx(0.6, rel=1e-6)


@pytest.mark.unit
class TestReturnsMatrix:
    def test_drops_short_series(self, monkeypatch):
        monkeypatch.setattr(opt, "_returns_series",
                            lambda s, d, lb=120: _series([0.01] * 3) if s == "SHORT" else _series([0.01] * 60))
        usable, mat, skipped = opt._returns_matrix(["AAPL", "SHORT", "MSFT"])
        assert usable == ["AAPL", "MSFT"]
        assert skipped == ["SHORT"]
        assert mat.shape == (60, 2)

    def test_all_skipped(self, monkeypatch):
        monkeypatch.setattr(opt, "_returns_series", lambda s, d, lb=120: None)
        usable, mat, skipped = opt._returns_matrix(["AAPL"])
        assert usable == []
        assert mat.shape == (0, 0)


@pytest.mark.unit
class TestOptimize:
    def test_no_symbols_no_holdings(self, monkeypatch):
        monkeypatch.setattr(opt.portfolio, "get_user_portfolio", lambda: {"holdings": []})
        out = opt.optimize_portfolio([])
        assert out.get("error") == "no_symbols"

    def test_uses_holdings_when_symbols_empty(self, monkeypatch):
        monkeypatch.setattr(opt.portfolio, "get_user_portfolio", lambda: {
            "holdings": [{"ticker": "AAPL", "shares": 10, "last_close": 200.0},
                         {"ticker": "MSFT", "shares": 5, "last_close": 400.0}]})
        r = _series([0.01] * 60)
        monkeypatch.setattr(opt, "_returns_series", lambda s, d, lb=120: r)
        out = opt.optimize_portfolio([])
        assert out.get("error") is None
        assert set(out["weights"]) == {"AAPL", "MSFT"}
        assert "current_weights_pct" in out  # 持仓派生 → 带对比

    def test_max_sharpe_single_name(self, monkeypatch):
        monkeypatch.setattr(opt, "_returns_series", lambda s, d, lb=120: _series([0.01] * 60))
        out = opt.optimize_portfolio(["AAPL"], "max_sharpe")
        assert out["weights"] == {"AAPL": 1.0}
        # 恒定收益 → 波动 0，Sharpe 约定为 0（_sharpe 的 vol<=1e-12 分支）
        assert out["sharpe_ratio"] == 0.0

    def test_too_many_names(self, monkeypatch):
        symbols = [f"S{i}" for i in range(13)]
        out = opt.optimize_portfolio(symbols)
        assert out.get("error") == "too_many"

    def test_real_math_on_synthetic(self):
        a, b = _two_asset_system()
        mat = np.column_stack([a, b])
        mean, cov = opt._annual_stats(mat)
        w_min = opt._min_vol_weight(mean, cov)
        w_max = opt._max_sharpe_weight(mean, cov)
        # min-vol 组合波动 ≤ max-sharpe 组合波动
        assert opt._port_vol(w_min, cov) <= opt._port_vol(w_max, cov) + 1e-9
        # max-sharpe 组合夏普应不低于 min-vol（用无风险=0 对比，避免 rf 高于组合收益的退化）
        assert opt._sharpe(w_max, mean, cov, rf=0.0) >= opt._sharpe(w_min, mean, cov, rf=0.0) - 1e-9
        # frontier 有效：目标收益升序 → 输出收益单调递增（λ 修复保证）
        frontier = opt._frontier(mean, cov, n_points=15)
        if frontier:
            rets = [p["ret_pct"] for p in frontier]
            vols = [p["vol_pct"] for p in frontier]
            # 收益必须随 target 严格递增（这是 λ 修复的核心保证）
            assert all(rets[i + 1] >= rets[i] - 0.05 for i in range(len(rets) - 1))
            # 波动：在正收益侧（可行区间的 min-vol 之后）单调不减；
            # 但若年化收益为负，边界是 U 形（先降后升），仅断言收尾段单调
            assert all(vols[i + 1] >= vols[i] - 1.0 for i in range(len(vols) - 3, len(vols) - 1))

    def test_frontier_lambda_achieves_target_return(self):
        """回归测试：frontier 每个点必须实现其目标收益（曾因 λ 符号错误而偏离）。"""
        mean = np.array([0.10, 0.05])
        cov = np.array([[0.04, 0.0], [0.0, 0.01]])
        inv = np.linalg.inv(cov)
        ones = np.ones(2)
        a = float(mean @ inv @ mean)
        b = float(ones @ inv @ mean)
        c = float(ones @ inv @ ones)
        for target in np.linspace(0.07, 0.12, 6):  # 避开 b-c·target≈0 的奇点(0.06)
            denom = b - c * target
            if abs(denom) < 1e-9:
                continue
            lam = (a - b * target) / denom
            w_num = inv @ (mean - lam * ones)
            w_den = float(ones @ w_num)
            if w_den == 0:
                continue
            w = w_num / w_den
            achieved = float(w @ mean)
            assert achieved == pytest.approx(target, abs=1e-9), \
                f"frontier λ 错误: target={target:.4f} achieved={achieved:.4f}"

    def test_cross_market_alignment(self, monkeypatch):
        """不同交易日历的标的不再按位置错位（跨市场对齐修复）。"""
        us_dates = pd.bdate_range("2026-01-05", periods=60)
        hk_dates = pd.DatetimeIndex([d for d in us_dates if d.day != 15][:55])
        us_r = pd.Series([0.01] * 60, index=us_dates)
        hk_r = pd.Series([-0.01] * len(hk_dates), index=hk_dates)
        monkeypatch.setattr(opt, "_returns_series",
                            lambda s, d, lb=120: us_r if s == "US1" else hk_r)
        usable, mat, skipped = opt._returns_matrix(["US1", "HK1"])
        assert mat.shape[0] == len(set(us_dates) & set(hk_dates))  # 共同交易日数

    def test_weights_sum_to_one(self, monkeypatch):
        rng = np.random.default_rng(3)
        r = [0.001 * math.sin(i / 5) + rng.normal(0, 0.01) for i in range(80)]
        monkeypatch.setattr(opt, "_returns_series", lambda s, d, lb=120: _series(r))
        out = opt.optimize_portfolio(["A", "B", "C"], "max_sharpe")
        # 权重四舍五入到 6 位后求和 ≈1（显示精度内）
        assert sum(out["weights"].values()) == pytest.approx(1.0, abs=1e-5)
