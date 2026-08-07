"""Cross-instrument hedge advisor over the user's tracked names (PRD §7 P2).

``portfolio_context`` already computes, at analysis time, how ONE candidate
correlates with configured holdings. This module gives the book-level view over
ALL the names the user has analysed: a pairwise correlation matrix, the
high-correlation clusters ("three tickers, one bet"), and concrete
hedge / diversifier / de-dup suggestions.

Prices only (``load_ohlcv`` daily returns), so it works across US / HK / A with
zero new vendor. Degrades per-name: anything unfetchable is skipped.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from . import store

_LOOKBACK = 60
_HIGH_CORR = 0.7   # "same bet in disguise"
_HEDGE_CORR = -0.4  # genuine hedge


def _returns(symbol: str, curr_date: str, lookback: int = _LOOKBACK):
    from dromx.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(symbol, curr_date)
    if df is None or getattr(df, "empty", True):
        return None
    cols = {c.lower(): c for c in df.columns}
    dcol, ccol = cols.get("date"), cols.get("close")
    if ccol is None:
        return None
    closes = []
    for _, row in df.iterrows():
        d = str(row[dcol])[:10] if dcol else ""
        if d and d <= curr_date:
            try:
                closes.append(float(row[ccol]))
            except (TypeError, ValueError):
                continue
    closes = closes[-(lookback + 1):]
    if len(closes) < 6:
        return None
    return [(closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes)) if closes[i - 1] > 0]


def _returns_series(symbol: str, curr_date: str, lookback: int = _LOOKBACK):
    """Daily returns as a date-indexed pd.Series (for cross-market alignment).

    ``_returns`` returns a bare list, which is fine for same-calendar names but
    wrong across markets (US ~252 / HK ~247 / A ~242 trading days per year plus
    different holidays): pairing by list position mixes different dates and
    injects spurious correlation into VaR / covariance / beta. This variant
    keeps the date, so callers can reindex on the intersection of calendars."""
    from dromx.dataflows.stockstats_utils import load_ohlcv

    df = load_ohlcv(symbol, curr_date)
    if df is None or getattr(df, "empty", True):
        return None
    cols = {c.lower(): c for c in df.columns}
    dcol, ccol = cols.get("date"), cols.get("close")
    if dcol is None or ccol is None:
        return None
    out: list[tuple] = []
    for _, row in df.iterrows():
        d = str(row[dcol])[:10]
        if not d or d > curr_date:
            continue
        try:
            out.append((d, float(row[ccol])))
        except (TypeError, ValueError):
            continue
    closes = out[-(lookback + 1):]
    if len(closes) < 7:
        return None
    rets = {}
    for i in range(1, len(closes)):
        prev = closes[i - 1][1]
        cur = closes[i][1]
        if prev > 0:
            rets[closes[i][0]] = (cur - prev) / prev
    import pandas as pd
    return pd.Series(rets).sort_index()


def _corr(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 5:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 1e-12 or vb <= 1e-12:
        return None
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / (va ** 0.5 * vb ** 0.5)


def build_hedge_report() -> dict:
    """Correlation matrix + clusters + hedge suggestions over analysed names."""
    # Latest done run per ticker (dedup — one row per name).
    latest: dict[str, dict] = {}
    for r in store.list_runs():
        if r.get("status") != "done":
            continue
        t = (r.get("ticker") or "").strip()
        if not t:
            continue
        if t not in latest or (r.get("trade_date") or "") > (latest[t].get("trade_date") or ""):
            latest[t] = r

    from datetime import date as _date
    today = _date.today().isoformat()

    names = sorted(latest)
    rets: dict[str, list[float]] = {}
    skipped: list[str] = []
    for t in names:
        r = _returns(t, today)
        if r is None:
            skipped.append(t)
        else:
            rets[t] = r
    usable = [t for t in names if t in rets]

    # pairwise correlation matrix
    matrix: list[dict] = []
    pairs: list[dict] = []
    for i, a in enumerate(usable):
        row = {"ticker": a, "corr": {}}
        for j, b in enumerate(usable):
            if a == b:
                row["corr"][b] = 1.0
                continue
            c = _corr(rets[a], rets[b])
            row["corr"][b] = round(c, 2) if c is not None else None
            if j > i and c is not None:
                pairs.append({"a": a, "b": b, "corr": round(c, 2)})
        matrix.append(row)

    # clusters of mutually high-correlated names (simple union-find over pairs)
    parent = {t: t for t in usable}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        if p["corr"] >= _HIGH_CORR:
            ra, rb = find(p["a"]), find(p["b"])
            if ra != rb:
                parent[ra] = rb
    groups: dict[str, list[str]] = {}
    for t in usable:
        groups.setdefault(find(t), []).append(t)
    clusters = [sorted(g) for g in groups.values() if len(g) > 1]

    # suggestions
    suggestions: list[dict] = []
    for cl in clusters:
        suggestions.append({
            "kind": "concentration",
            "tickers": cl,
            "text": f"{', '.join(cl)} 高度相关（≥{_HIGH_CORR:.0%}）——本质是同一笔押注。"
                    f"建议在其中择一保留、或减少总敞口，而非并列持有。",
        })
    for p in sorted(pairs, key=lambda x: x["corr"]):
        if p["corr"] <= _HEDGE_CORR:
            suggestions.append({
                "kind": "hedge",
                "tickers": [p["a"], p["b"]],
                "text": f"{p['a']} 与 {p['b']} 负相关（{p['corr']:+.2f}）——可作为彼此的对冲/分散腿。",
            })

    return {
        "names": usable,
        "skipped": skipped,
        "matrix": matrix,
        "pairs": sorted(pairs, key=lambda x: -abs(x["corr"])),
        "clusters": clusters,
        "suggestions": suggestions,
        "lookback_days": _LOOKBACK,
    }
