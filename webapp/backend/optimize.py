"""Portfolio optimization — mean-variance allocation (PRD §7 P1).

Complements the Kelly sizer (how much of ONE name) and the risk view (how much
this book can lose) with the allocation question: **given a set of candidate
names, what weights maximize Sharpe / minimize volatility / sit on the
efficient frontier?**

Implementation notes:
- Pure numpy — no scipy dependency. min-vol and max-Sharpe have closed-form
  solutions on the unconstrained mean-variance problem; we apply a non-negative
  projection (clip + renormalise) so weights stay long-only, which matches how
  retail users actually trade. For 2-12 names this projection is a very good
  approximation of the true long-only optimum.
- Daily returns come from ``hedge._returns`` (same ``load_ohlcv`` source as the
  risk view), so US / HK / A all work with zero new vendor.
- The efficient frontier is traced by sweeping a target-return grid and solving
  the closed-form minimum-variance portfolio at each target, then projecting.
- Degrades per-name: names without enough price history are dropped with a note.
"""

from __future__ import annotations

import logging
import math
from datetime import date as _date

import numpy as np
import pandas as pd

from . import portfolio
from .hedge import _returns_series

logger = logging.getLogger(__name__)

_LOOKBACK = 120
_TRADING_DAYS = 252
_RF = 0.02          # risk-free proxy used for Sharpe
_MAX_NAMES = 12     # covariance is dense; beyond this the frontier gets noisy


def _returns_matrix(symbols: list[str], lookback: int = _LOOKBACK):
    """Aligned daily-return matrix for the given symbols.

    Returns (symbols, np.ndarray (n_days × n)) where each column is one name's
    returns. Names with < 6 days are dropped. Rows are aligned on the
    intersection of each name's trading dates (cross-market safe: US/HK/A have
    different calendars, so position-based alignment would mix different dates",
    and inject spurious covariance)."""
    series: dict[str, pd.Series] = {}
    skipped: list[str] = []
    for s in symbols:
        r = _returns_series(s, _date.today().isoformat(), lookback)
        if r is None or len(r) < 6:
            skipped.append(s)
        else:
            series[s] = r.iloc[-lookback:]

    usable = [s for s in symbols if s in series]
    if not usable:
        return [], np.zeros((0, 0)), skipped

    # 共同交易日交集（跨市场安全）
    common = set.intersection(*(set(r.index) for r in series.values()))
    if not common:
        return [], np.zeros((0, 0)), skipped + [f"{s}(无共同交易日)" for s in usable]
    common = sorted(common)
    mat = np.array([series[s].reindex(common).fillna(0.0).tolist() for s in usable], dtype=float).T
    return usable, mat, skipped


def _annual_stats(mat: np.ndarray):
    """(mean_annual, cov_annual) from a daily-return matrix (days × names).

    Note: numpy's ``np.cov`` returns a 0-d scalar for a single column, so we
    always wrap the result to at least 2D (1×1) — downstream code indexes
    ``cov[i, i]`` unconditionally."""
    mean_daily = mat.mean(axis=0)
    cov_daily = np.atleast_2d(np.cov(mat, rowvar=False))
    return mean_daily * _TRADING_DAYS, cov_daily * _TRADING_DAYS


def _port_return(w: np.ndarray, mean: np.ndarray) -> float:
    return float(np.dot(w, mean))


def _port_vol(w: np.ndarray, cov: np.ndarray) -> float:
    return float(math.sqrt(max(np.dot(w, np.dot(cov, w)), 0.0)))


def _sharpe(w: np.ndarray, mean: np.ndarray, cov: np.ndarray, rf: float = _RF) -> float:
    vol = _port_vol(w, cov)
    if vol <= 1e-12:
        return 0.0
    return (_port_return(w, mean) - rf) / vol


def _project_nonneg(w: np.ndarray) -> np.ndarray:
    """Clip to [0,1] and renormalise to sum 1 (long-only projection)."""
    x = np.clip(w, 0.0, None)
    s = x.sum()
    if s <= 1e-12:
        return np.full_like(w, 1.0 / len(w))
    return x / s


def _min_vol_weight(mean: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Closed-form global minimum-variance weights (unconstrained), projected long-only."""
    try:
        inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        return _equal_weight(len(mean))
    ones = np.ones(len(mean))
    w = inv @ ones / (ones @ inv @ ones)
    return _project_nonneg(w)


def _max_sharpe_weight(mean: np.ndarray, cov: np.ndarray, rf: float = _RF) -> np.ndarray:
    """Closed-form max-Sharpe weights (unconstrained), projected long-only."""
    try:
        inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        return _equal_weight(len(mean))
    excess = mean - rf
    num = inv @ excess
    den = np.ones(len(mean)) @ num
    if abs(den) <= 1e-12:
        return _equal_weight(len(mean))
    w = _project_nonneg(num / den)
    return _refine_sharpe(w, mean, cov, rf)


def _refine_sharpe(w: np.ndarray, mean: np.ndarray, cov: np.ndarray, rf: float,
                   iterations: int = 40, step: float = 0.02) -> np.ndarray:
    """Coordinate-descent polish of a long-only projected Sharpe solution.

    The closed-form max-Sharpe weights are optimal on the *unconstrained*
    problem; clipping to [0,1] + renormalising can move them off the true
    long-only optimum. This walks pair trades between names to recover most of
    that loss — cheap (O(n²·iter) numpy), no scipy needed."""
    n = len(w)
    best = w.copy()
    best_sharpe = _sharpe(best, mean, cov, rf)
    for _ in range(iterations):
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                for delta in (step, -step):
                    cand = best.copy()
                    cand[i] = max(0.0, cand[i] - delta)
                    cand[j] = max(0.0, cand[j] + delta)
                    s = cand.sum()
                    if s <= 1e-12:
                        continue
                    cand = cand / s
                    sh = _sharpe(cand, mean, cov, rf)
                    if sh > best_sharpe + 1e-12:
                        best, best_sharpe, improved = cand, sh, True
        if not improved:
            break
    return best


def _equal_weight(n: int) -> np.ndarray:
    return np.full(n, 1.0 / n)


def _frontier(mean: np.ndarray, cov: np.ndarray, n_points: int = 25):
    """Trace the efficient frontier via target-return sweep (long-only projected).

    Returns list of {ret_pct, vol_pct, sharpe} for the minimum-variance portfolio
    at each target return between the min/max name returns.
    """
    lo = float(mean.min())
    hi = float(mean.max())
    if hi - lo < 1e-9:
        return []
    points: list[dict] = []
    for target in np.linspace(lo, hi, n_points):
        try:
            inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            continue
        ones = np.ones(len(mean))
        # Lagrangian minimum-variance for fixed return: w(λ) = Σ⁻¹(μ - λ1) / 1ᵀΣ⁻¹(μ - λ1).
        # Solve λ so that wᵀμ = target: λ = (a - b·target) / (b - c·target)
        # where a = μᵀΣ⁻¹μ, b = 1ᵀΣ⁻¹μ, c = 1ᵀΣ⁻¹1. (Numerator sign matters:)
        # wᵀμ = (a - λb)/(b - λc); setting = target gives a - λb = target(b - λc)
        # ⇒ λ(b - c·target) = a - b·target.
        a = float(mean @ inv @ mean)
        b = float(ones @ inv @ mean)
        c = float(ones @ inv @ ones)
        lam = (a - b * target) / (b - c * target) if abs(b - c * target) > 1e-12 else 0.0
        w_num = inv @ (mean - lam * ones)          # Σ⁻¹(μ - λ1)
        w_den = float(ones @ w_num)                 # 1ᵀΣ⁻¹(μ - λ1)（归一化分母）
        # 拉格朗日解 w(λ) = Σ⁻¹(μ-λ1) / 1ᵀΣ⁻¹(μ-λ1) 本身已归一（Σwᵢ=1）。
        # 注意：λ 是从归一化约束推得的，所以必须除以 w_den 才能让 wᵀμ=target。
        if w_den == 0 or not np.isfinite(w_den):
            continue
        w_raw = w_num / w_den
        w = _project_nonneg(w_raw)
        ret = _port_return(w, mean)
        vol = _port_vol(w, cov)
        points.append({
            "ret_pct": round(ret * 100, 2),
            "vol_pct": round(vol * 100, 2),
            "sharpe": round(_sharpe(w, mean, cov), 3),
        })
    return points


def optimize_portfolio(
    symbols: list[str],
    strategy: str = "max_sharpe",
    lookback: int = _LOOKBACK,
) -> dict:
    """Mean-variance optimization over the given names.

    Args:
        symbols: candidate tickers (US / HK / A). Empty → use current holdings.
        strategy: "max_sharpe" | "min_volatility" | "equal_weight".
        lookback: daily-return window.

    Returns:
        dict with weights, portfolio stats, the efficient frontier, and (when
        derived from holdings) a comparison vs the current allocation.
    """
    from_holdings = False
    if not symbols:
        book = portfolio.get_user_portfolio()
        holdings = (book or {}).get("holdings") or []
        symbols = [h.get("ticker") for h in holdings if h.get("ticker")]
        from_holdings = True

    symbols = [s for s in dict.fromkeys(symbols) if s]  # dedupe, drop empties
    if not symbols:
        return {"error": "no_symbols", "message": "未提供标的且当前没有持仓。"}
    if len(symbols) > _MAX_NAMES:
        return {"error": "too_many",
                "message": f"一次最多优化 {_MAX_NAMES} 只标的（当前 {len(symbols)}），请分批。"}

    usable, mat, skipped = _returns_matrix(symbols, lookback)
    if not usable:
        return {"error": "no_prices",
                "message": f"所有标的都无法取得足够行情：{', '.join(skipped)}"}

    mean, cov = _annual_stats(mat)
    n = len(usable)

    if strategy == "min_volatility":
        w = _min_vol_weight(mean, cov)
    elif strategy == "equal_weight":
        w = _equal_weight(n)
    else:  # max_sharpe default
        w = _max_sharpe_weight(mean, cov)

    weights = {t: round(float(w[i]), 6) for i, t in enumerate(usable)}
    ret = _port_return(w, mean)
    vol = _port_vol(w, cov)
    sharpe = _sharpe(w, mean, cov)
    frontier = _frontier(mean, cov)

    # per-name stats for the chosen allocation
    per_name = []
    for i, t in enumerate(usable):
        per_name.append({
            "ticker": t,
            "weight_pct": round(float(w[i]) * 100, 2),
            "annual_return_pct": round(float(mean[i]) * 100, 2),
            "annual_vol_pct": round(float(math.sqrt(cov[i, i])) * 100, 2),
        })

    result: dict = {
        "strategy": strategy,
        "weights": weights,
        "expected_annual_return_pct": round(ret * 100, 2),
        "annual_volatility_pct": round(vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "per_name": per_name,
        "frontier": frontier,
        "skipped": skipped,
        "lookback_days": lookback,
    }

    if from_holdings:
        # current allocation for comparison
        book = portfolio.get_user_portfolio()
        holdings = {h.get("ticker"): float(h.get("shares") or 0) * float(h.get("last_close") or 0)
                    for h in (book or {}).get("holdings") or []}
        total = sum(holdings.values())
        current = {
            t: round(holdings.get(t, 0.0) / total * 100, 2)
            for t in usable if total > 0
        }
        result["current_weights_pct"] = current

    return result
