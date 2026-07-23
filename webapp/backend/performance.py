"""Performance attribution over completed web runs (PRD §7 [P1]).

Each finished run is a dated, directional call (its PM rating → bull / neutral /
bear). This module scores those calls against realized market prices — WITHOUT
re-running the pipeline — and rolls them up into the standard desk metrics
(hit rate, Sharpe / Sortino / Calmar, max drawdown, win rate, profit factor),
plus a breakdown by rating bucket.

It mirrors the engine's own outcome logic (``trading_graph._fetch_returns`` +
``signal_tracker``): realized return over a holding window that starts at the
run's ``trade_date``, alpha vs the same suffix→benchmark map, and a ±1% noise
band below which a move doesn't confirm or refute a directional call.

Everything degrades gracefully: a run too recent to have forward prices, or a
vendor failure, is reported as ``pending`` rather than dropped or errored.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime

from . import store

logger = logging.getLogger(__name__)

# Rating (PM decision) → directional sign. Matches the frontend RATING_DIR.
_RATING_DIR: dict[str, int] = {
    "buy": 1, "overweight": 1,
    "hold": 0, "neutral": 0,
    "underweight": -1, "sell": -1,
}

# A directional call is confirmed only when the realized move clears this band;
# smaller moves are noise (same threshold the engine's scorecard uses).
_NOISE = 0.01  # ±1%

# Default holding window (trading days) over which a call's return is measured.
_HOLDING_DAYS = 5

# Suffix → benchmark index for alpha (mirrors default_config benchmark_map).
_BENCHMARK_MAP: dict[str, str] = {
    ".NS": "^NSEI", ".BO": "^BSESN", ".T": "^N225", ".HK": "^HSI",
    ".L": "^FTSE", ".TO": "^GSPTSE", ".AX": "^AXJO",
    ".SS": "000001.SS", ".SZ": "399001.SS", "": "SPY",
}

# Cache resolved outcomes so repeated dashboard loads don't re-fetch prices.
# Keyed by (ticker, trade_date, holding_days). Value is the per-run outcome dict.
_OUTCOME_CACHE: dict[tuple[str, str, int], dict] = {}


def _rating_dir(rating: str | None) -> int | None:
    if not rating:
        return None
    return _RATING_DIR.get(rating.strip().lower())


def _benchmark_for(ticker: str) -> str:
    up = ticker.upper()
    for suffix, bench in _BENCHMARK_MAP.items():
        if suffix and up.endswith(suffix.upper()):
            return bench
    return _BENCHMARK_MAP[""]


def _forward_return(ticker: str, trade_date: str, holding_days: int) -> tuple[float, int] | None:
    """Realized close-to-close return from ``trade_date`` over ``holding_days``.

    Uses the engine data layer (``load_ohlcv``), taking only rows on/after the
    trade date so there is no look-ahead. Returns ``(return, actual_days)`` or
    ``None`` when fewer than 2 forward bars exist (too recent / delisted).
    """
    try:
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        df = load_ohlcv(ticker, datetime.now().strftime("%Y-%m-%d"))
        if df is None or getattr(df, "empty", True):
            return None
        cols = {c.lower(): c for c in df.columns}
        dcol, ccol = cols.get("date"), cols.get("close")
        if ccol is None:
            return None

        rows = []
        for _, row in df.iterrows():
            d = str(row[dcol])[:10] if dcol else ""
            if d and d >= trade_date:
                try:
                    rows.append(float(row[ccol]))
                except (TypeError, ValueError):
                    continue
        if len(rows) < 2:
            return None
        actual = min(holding_days, len(rows) - 1)
        entry, exit_ = rows[0], rows[actual]
        if entry <= 0:
            return None
        return (exit_ - entry) / entry, actual
    except Exception as exc:  # noqa: BLE001 — attribution is best-effort
        logger.warning("forward_return(%s, %s) failed: %s", ticker, trade_date, exc)
        return None


def _resolve_outcome(ticker: str, trade_date: str, rating: str | None,
                     holding_days: int) -> dict:
    """Score one run: direction, raw & alpha return, correct/incorrect/pending."""
    key = (ticker, trade_date, holding_days)
    if key in _OUTCOME_CACHE:
        cached = dict(_OUTCOME_CACHE[key])
        cached["rating"] = rating
        cached["direction"] = _rating_dir(rating)
        cached["correct"] = _score(cached["direction"], cached.get("raw_return"))
        return cached

    direction = _rating_dir(rating)
    fwd = _forward_return(ticker, trade_date, holding_days)
    if fwd is None:
        out = {"ticker": ticker, "trade_date": trade_date, "rating": rating,
               "direction": direction, "raw_return": None, "alpha_return": None,
               "holding_days": None, "correct": None, "status": "pending"}
        return out  # don't cache pending — prices may arrive later

    raw, actual = fwd
    bench = _benchmark_for(ticker)
    bench_fwd = _forward_return(bench, trade_date, holding_days)
    alpha = raw - bench_fwd[0] if bench_fwd else None

    out = {"ticker": ticker, "trade_date": trade_date, "rating": rating,
           "direction": direction, "raw_return": raw, "alpha_return": alpha,
           "holding_days": actual, "benchmark": bench,
           "correct": _score(direction, raw), "status": "resolved"}
    _OUTCOME_CACHE[key] = {k: out[k] for k in
                           ("ticker", "trade_date", "raw_return", "alpha_return",
                            "holding_days", "benchmark", "status")}
    return out


def _score(direction: int | None, raw: float | None) -> bool | None:
    """Was the directional call right? None when unscoreable (no dir / no return)."""
    if direction is None or raw is None:
        return None
    if direction == 0:  # Hold/Neutral is "right" when the move stayed in the band
        return abs(raw) < _NOISE
    if abs(raw) < _NOISE:
        return False  # a directional call needs a real move to be confirmed
    return (raw > 0) == (direction > 0)


# --- portfolio-style metrics over the sequence of per-call returns ------------

def _sharpe(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    sd = math.sqrt(var)
    return mean / sd if sd > 1e-12 else None


def _sortino(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return None
    dvar = sum(r ** 2 for r in downside) / len(downside)
    dd = math.sqrt(dvar)
    return mean / dd if dd > 1e-12 else None


def _max_drawdown(returns: list[float]) -> float | None:
    """Max drawdown of the compounding equity curve of sequential per-call returns."""
    if not returns:
        return None
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for r in returns:
        equity *= 1 + r
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)
    return mdd  # negative or 0


def _profit_factor(returns: list[float]) -> float | None:
    gains = sum(r for r in returns if r > 0)
    losses = -sum(r for r in returns if r < 0)
    if losses <= 1e-12:
        return None if gains <= 1e-12 else math.inf
    return gains / losses


def build_performance(holding_days: int = _HOLDING_DAYS) -> dict:
    """Score all completed runs and aggregate into a performance report."""
    runs = [r for r in store.list_runs() if r.get("status") == "done"]
    outcomes = []
    for r in runs:
        ticker = (r.get("ticker") or "").strip()
        trade_date = (r.get("trade_date") or "").strip()
        if not ticker or not trade_date:
            continue
        outcomes.append(_resolve_outcome(ticker, trade_date, r.get("rating"), holding_days))

    resolved = [o for o in outcomes if o["status"] == "resolved"]
    scored = [o for o in resolved if o["correct"] is not None]
    raw_returns = [o["raw_return"] for o in resolved if o["raw_return"] is not None]
    alpha_returns = [o["alpha_return"] for o in resolved if o["alpha_return"] is not None]

    # "Strategy return" = the signed return a directional call captured (long
    # bull, short bear, flat on hold): direction * raw_return.
    strat_returns = [
        o["direction"] * o["raw_return"]
        for o in resolved
        if o["direction"] is not None and o["raw_return"] is not None and o["direction"] != 0
    ]

    hits = sum(1 for o in scored if o["correct"])
    win_returns = [r for r in strat_returns if r > 0]

    # rating-bucket hit rates
    buckets: dict[str, dict] = {}
    for o in scored:
        b = (o.get("rating") or "—")
        d = buckets.setdefault(b, {"total": 0, "correct": 0})
        d["total"] += 1
        d["correct"] += 1 if o["correct"] else 0

    def _avg(xs: list[float]) -> float | None:
        return sum(xs) / len(xs) if xs else None

    metrics = {
        "runs_total": len(runs),
        "resolved": len(resolved),
        "pending": sum(1 for o in outcomes if o["status"] == "pending"),
        "scored": len(scored),
        "hit_rate": (hits / len(scored)) if scored else None,
        "avg_raw_return": _avg(raw_returns),
        "avg_alpha_return": _avg(alpha_returns),
        "avg_strategy_return": _avg(strat_returns),
        "win_rate": (len(win_returns) / len(strat_returns)) if strat_returns else None,
        "sharpe": _sharpe(strat_returns),
        "sortino": _sortino(strat_returns),
        "max_drawdown": _max_drawdown(strat_returns),
        "profit_factor": _profit_factor(strat_returns),
        "holding_days": holding_days,
        "by_rating": {
            k: {"total": v["total"], "correct": v["correct"],
                "hit_rate": v["correct"] / v["total"] if v["total"] else None}
            for k, v in sorted(buckets.items())
        },
    }
    # Calmar = annualized-ish return / |max drawdown|; use avg strategy return as
    # a simple per-trade proxy (no annualization — holding windows vary).
    mdd = metrics["max_drawdown"]
    avg_strat = metrics["avg_strategy_return"]
    metrics["calmar"] = (avg_strat / abs(mdd)) if (mdd and abs(mdd) > 1e-12 and avg_strat is not None) else None

    outcomes.sort(key=lambda o: o["trade_date"], reverse=True)
    return {"metrics": metrics, "outcomes": outcomes}
