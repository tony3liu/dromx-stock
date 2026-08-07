"""Portfolio risk measurement — VaR + stress testing over the user's holdings (PRD §7 P1).

Complements the hedge advisor (correlation/clusters) and the Kelly sizer (how
much to size) with the risk question the user actually feels: **how much can this
book lose?**

What it computes, per name and for the whole book:
- Historical-simulation VaR at 95% / 99% (worst N% of recent daily P&L).
- Parametric (variance-covariance) VaR using the same return window.
- Component VaR — how much each position contributes to the book's total risk.
- Stress scenarios: parallel market moves (-10% / -20%) and a "crash" leg using
  the worst recent single-day return per name, scaled to the book.

Data: holdings from ``portfolio.json`` (shares × last close = market value),
daily returns from ``load_ohlcv`` (same source as the hedge advisor, so US / HK /
A all work with zero new vendor). Per-name degradation: anything unfetchable is
skipped with a note. If the book is empty or no prices resolve, returns a clear
"no data" verdict instead of a fabricated number.
"""

from __future__ import annotations

import logging
import math
from datetime import date as _date

import pandas as pd

from . import portfolio
from .hedge import _returns_series

logger = logging.getLogger(__name__)

_LOOKBACK = 120          # daily return window for VaR
_DAILY_TO_ANNUAL = math.sqrt(252)


def _holdings_snapshot() -> list[dict]:
    """Flatten the user's tracked portfolio into [(ticker, market_value)].

    ``get_user_portfolio`` already enriches each holding with a last close,
    so we reuse its output instead of re-fetching prices: the P&L column and
    this risk view always agree on what is held and at what price.
    """
    book = portfolio.get_user_portfolio()
    raw = (book or {}).get("holdings") or []
    out: list[dict] = []
    for h in raw:
        ticker = (h or {}).get("ticker") or ""
        shares = float(h.get("shares") or 0)
        px = h.get("last_close")
        if not ticker or shares <= 0 or px is None or float(px) <= 0:
            continue
        out.append({
            "ticker": ticker,
            "shares": shares,
            "price": float(px),
            "market_value": round(shares * float(px), 2),
        })
    return out


def _percentile(sorted_returns: list[float], q: float) -> float | None:
    """Quantile of a sorted loss distribution (q in [0,1]; 0.95 → 95th % worst)."""
    if not sorted_returns:
        return None
    n = len(sorted_returns)
    idx = min(n - 1, max(0, int(math.ceil(q * n) - 1)))
    return sorted_returns[idx]


def _parametric_var(returns: list[float], z: float) -> float | None:
    """Parametric VaR factor: z * sigma (per daily return)."""
    if len(returns) < 6:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    sigma = math.sqrt(var)
    return z * sigma


# Standard normal quantiles: z(0.95)=1.645, z(0.99)=2.326
_Z = {0.95: 1.6448536269514722, 0.99: 2.3263478740408408}


def build_risk_report(
    conf_levels: tuple[float, ...] = (0.95, 0.99),
    lookback: int = _LOOKBACK,
) -> dict:
    """VaR + stress report over the user's current holdings.

    Returns a dict with per-name and book-level risk figures; everything
    degrades gracefully when data is missing.
    """
    snapshot = _holdings_snapshot()
    if not snapshot:
        return {
            "verdict": "no_holdings",
            "message": "当前没有可计价持仓（无 shares 或价格无法解析）。"
                       "请先记录交易（portfolio.json）后再看风险。",
            "book_value": 0.0,
            "per_name": [], "book": None, "stress": None,
        }

    book_value = sum(p["market_value"] for p in snapshot)

    # ---- daily return series per name (date-indexed, aligned on calendar intersection) ----
    # Cross-market names (US/HK/A) have different trading calendars; pairing by
    # list position would mix different dates and inject spurious correlation,
    # so we align on the intersection of each name's trading dates.
    name_returns: dict[str, pd.Series] = {}
    skipped: list[str] = []
    for p in snapshot:
        r = _returns_series(p["ticker"], _date.today().isoformat(), lookback)
        if r is None or len(r) < 6:
            skipped.append(p["ticker"])
        else:
            name_returns[p["ticker"]] = r.iloc[-lookback:]

    usable = [p for p in snapshot if p["ticker"] in name_returns]
    if not usable:
        return {
            "verdict": "no_prices",
            "message": "持仓存在但无法取得足够行情（收益序列 < 6 天）。",
            "book_value": round(book_value, 2),
            "per_name": [], "book": None, "stress": None, "skipped": skipped,
        }

    # ---- weights & portfolio daily P&L (in currency, not %) ----
    weights = {p["ticker"]: p["market_value"] / book_value for p in usable}
    # 对齐到所有标的中出现的共同交易日（日期交集，跨市场安全）
    common_dates = set.intersection(*(set(r.index) for r in name_returns.values())) if name_returns else set()
    if not common_dates:
        return {
            "verdict": "no_prices",
            "message": "标的不存在共同交易日，无法计算组合 VaR。",
            "book_value": round(book_value, 2),
            "per_name": [], "book": None, "stress": None, "skipped": skipped,
        }
    common_dates = sorted(common_dates)
    aligned = {tkr: r.reindex(common_dates) for tkr, r in name_returns.items()}
    book_returns = [
        sum(weights[tkr] * (aligned[tkr].iloc[t] if pd.notna(aligned[tkr].iloc[t]) else 0.0)
            for tkr in aligned)
        for t in range(len(common_dates))
    ]
    n_days = len(book_returns)

    # ---- book-level VaR (historical + parametric) ----
    losses = sorted(-r for r in book_returns)  # ascending worst→best of -ret
    book: dict = {
        "book_value": round(book_value, 2),
        "n_days": n_days,
        "var": {},
        "annualized_vol_pct": round(_DAILY_TO_ANNUAL * _std(book_returns) * 100, 2)
        if len(book_returns) >= 6 else None,
    }
    for c in conf_levels:
        hist = _percentile(losses, c)
        param = _parametric_var(book_returns, _Z[c])
        book["var"][f"p{int(c * 100)}"] = {
            "historical_pct": round(hist * 100, 2) if hist is not None else None,
            "parametric_pct": round(param * 100, 2) if param is not None else None,
            "historical_value": round(hist * book_value, 2) if hist is not None else None,
            "parametric_value": round(param * book_value, 2) if param is not None else None,
        }

    # ---- component VaR: contribution of each name to book historical VaR ----
    # Approximation: component = weight × beta_to_book × book_VaR.
    # beta_to_book = cov(r_i, r_book) / var(r_book).
    comp: list[dict] = []
    for p in usable:
        # 用已对齐到 common_dates 的序列（与 book_returns 同日历）
        ri = aligned[p["ticker"]].fillna(0.0).tolist()
        beta = _beta(ri, book_returns)
        contrib_pct = weights[p["ticker"]] * beta if beta is not None else None
        var95 = book["var"].get("p95", {}).get("historical_value")
        comp.append({
            "ticker": p["ticker"],
            "weight_pct": round(weights[p["ticker"]] * 100, 2),
            "market_value": round(p["market_value"], 2),
            "beta_to_book": round(beta, 2) if beta is not None else None,
            "component_var_pct": round(contrib_pct * 100, 2) if contrib_pct is not None else None,
            "component_var_value": round(contrib_pct * var95, 2) if (contrib_pct is not None and var95 is not None) else None,
            "notes": None,
        })
    comp.sort(key=lambda x: -(x["component_var_value"] or 0))

    # ---- stress scenarios ----
    stress = {
        "flat_m10": round(book_value * -0.10, 2),
        "flat_m20": round(book_value * -0.20, 2),
        "crash_1d": None,
        "worst_day_pct": None,
    }
    worst_day = min(book_returns) if book_returns else None
    if worst_day is not None:
        stress["crash_1d"] = round(worst_day * book_value, 2)
        stress["worst_day_pct"] = round(worst_day * 100, 2)

    # ---- plain-language verdict ----
    verdict = _verdict(book, stress, weights, skipped)

    return {
        "verdict": verdict["level"],
        "message": verdict["message"],
        "book_value": round(book_value, 2),
        "per_name": comp,
        "book": book,
        "stress": stress,
        "skipped": skipped,
        "lookback_days": lookback,
    }


def _var(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mean = sum(xs) / len(xs)
    return sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)


def _std(xs: list[float]) -> float | None:
    v = _var(xs)
    return math.sqrt(v) if v is not None else None


def _beta(asset_returns: list[float], book_returns: list[float]) -> float | None:
    n = min(len(asset_returns), len(book_returns))
    if n < 6:
        return None
    a, b = asset_returns[-n:], book_returns[-n:]
    va = _var(a)
    vb = _var(b)
    if not va or not vb or va <= 1e-12 or vb <= 1e-12:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
    return cov / vb


def _verdict(book: dict, stress: dict, weights: dict, skipped: list) -> dict:
    """Turn the numbers into a short plain-language risk read."""
    var95 = (book.get("var") or {}).get("p95", {}) or {}
    hist_val = var95.get("historical_value")
    hist_pct = var95.get("historical_pct")
    ann_vol = book.get("annualized_vol_pct")

    if hist_val is None:
        return {"level": "insufficient", "message": "收益序列不足，无法给出 VaR 结论。"}

    parts = [
        f"组合市值 {book['book_value']:,.0f}，95% VaR（历史模拟）≈ {hist_val:,.0f}"
        f"（{hist_pct:.1f}%），年化波动 {ann_vol}%。"
    ]
    # concentration warning（用权重 dict 而非 snapshot 条目）
    top = max(weights.values()) if weights else 0.0
    if top >= 0.60:
        parts.append("单标的高度集中（权重 ≥60%），组合风险≈该标的自身风险，分散效果有限。")
    elif len(weights) >= 3 and top <= 0.40:
        parts.append("分散度尚可（最大权重 ≤40%）。")
    if stress.get("crash_1d") is not None:
        parts.append(f"历史最差单日 ≈ {stress['crash_1d']:,.0f}（{stress['worst_day_pct']:.1f}%）。")
    if skipped:
        parts.append(f"无法取得行情：{', '.join(skipped)}（已跳过，未计入风险）。")

    level = "elevated" if (hist_pct or 0) >= 5 else "moderate" if (hist_pct or 0) >= 3 else "low"
    return {"level": level, "message": " ".join(parts)}
