"""Factor / risk exposure of a name, from prices alone (PRD §7 P2, v1).

FULL Fama-French 5-factor (Mkt/SMB/HML/RMW/CMA) needs the Ken French factor
return series (Dartmouth, US-only) PLUS per-name market cap / book-to-market /
profitability / asset-growth — i.e. a new data vendor and fundamentals, US-only.
See ``FACTOR_V2_NOTE`` below.

This v1 uses ONLY data we already have (the engine's OHLCV via ``load_ohlcv`` +
the same suffix→benchmark map used for alpha), so it works across US / HK / A
markets with zero new vendor. It regresses the name's daily returns on its
benchmark index to decompose risk into:

  * market **beta** (systematic sensitivity) and **alpha** (annualised intercept)
  * **R²** — how much of the move the market explains
  * total vs **idiosyncratic volatility** (annualised; residual after market)
  * **downside beta** (beta measured on down-market days only)
  * **momentum** (trailing return)

and derives a beta-neutral hedge ratio (how much index to short to flatten beta).
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

FACTOR_V2_NOTE = (
    "完整 Fama-French 5 因子（SMB/HML/RMW/CMA）需接入 Ken French 因子收益序列"
    "（Dartmouth，仅美股）+ 个股市值/账面市值比/盈利能力/资产增长，属新数据源。"
    "本版为价格型风险分解（Beta/α/特质波动等），覆盖美/港/A 全市场、零新依赖。"
)

_BENCHMARK_MAP: dict[str, str] = {
    ".NS": "^NSEI", ".BO": "^BSESN", ".T": "^N225", ".HK": "^HSI",
    ".L": "^FTSE", ".TO": "^GSPTSE", ".AX": "^AXJO",
    ".SS": "000001.SS", ".SZ": "399001.SS", "": "SPY",
}
_TRADING_DAYS = 252


def _benchmark_for(ticker: str) -> str:
    up = ticker.upper()
    for suffix, bench in _BENCHMARK_MAP.items():
        if suffix and up.endswith(suffix.upper()):
            return bench
    return _BENCHMARK_MAP[""]


def _returns(symbol: str, curr_date: str, lookback: int):
    """Daily-return list (chronological) for ``symbol`` up to ``curr_date``.

    Best-effort: the configured vendor (tencent/mootdx) doesn't cover index
    benchmarks like ^HSI / ^KS200 — fall back to yfinance for those so the
    /factor endpoint still returns a beta instead of 500.
    """
    from datetime import datetime, timedelta

    from tradingagents.dataflows.errors import NoMarketDataError
    from tradingagents.dataflows.stockstats_utils import load_ohlcv

    try:
        df = load_ohlcv(symbol, curr_date)
    except NoMarketDataError:
        df = None  # vendor doesn't cover this symbol (e.g. index benchmark)
    if df is None or getattr(df, "empty", True):
        # yfinance fallback for symbols the configured vendor doesn't cover
        # (index benchmarks: ^HSI / ^KS200 / ^NSEI / SPY — tencent/mootdx lack).
        try:
            import yfinance as yf

            d0 = datetime.strptime(curr_date, "%Y-%m-%d")
            start = (d0 - timedelta(days=lookback * 2 + 60)).strftime("%Y-%m-%d")
            end = (d0 + timedelta(days=7)).strftime("%Y-%m-%d")
            hd = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False)
            if hd is not None and not hd.empty:
                df = hd.reset_index().rename(columns={"Datetime": "Date"})
        except Exception:  # noqa: BLE001 — best-effort, never 500 the endpoint
            return None
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


def _align(a: list[float], b: list[float]) -> tuple[list[float], list[float]]:
    """Right-align two return series to their common (most recent) length."""
    n = min(len(a), len(b))
    return a[-n:], b[-n:]


def _ols(y: list[float], x: list[float]) -> tuple[float, float, float] | None:
    """Simple OLS y = alpha + beta·x. Returns (alpha, beta, r_squared) or None."""
    n = len(x)
    if n < 5:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx <= 1e-12:
        return None
    sxy = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    beta = sxy / sxx
    alpha = my - beta * mx
    ss_tot = sum((yi - my) ** 2 for yi in y)
    ss_res = sum((y[i] - (alpha + beta * x[i])) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-12 else None
    return alpha, beta, r2


def _std(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return math.sqrt(sum((v - m) ** 2 for v in xs) / (n - 1))


def build_factor_exposure(ticker: str, curr_date: str, lookback: int = 120) -> dict:
    """Price-based factor/risk decomposition for ``ticker`` as of ``curr_date``."""
    bench = _benchmark_for(ticker)
    r_stock = _returns(ticker, curr_date, lookback)
    r_bench = _returns(bench, curr_date, lookback)
    if not r_stock or not r_bench:
        return {"ticker": ticker, "benchmark": bench, "available": False,
                "note": FACTOR_V2_NOTE}

    y, x = _align(r_stock, r_bench)
    fit = _ols(y, x)
    if fit is None:
        return {"ticker": ticker, "benchmark": bench, "available": False,
                "note": FACTOR_V2_NOTE}
    alpha_d, beta, r2 = fit

    # residuals → idiosyncratic vol; total vol from the stock series.
    resid = [y[i] - (alpha_d + beta * x[i]) for i in range(len(y))]
    total_vol = _std(y) * math.sqrt(_TRADING_DAYS)
    idio_vol = _std(resid) * math.sqrt(_TRADING_DAYS)
    syst0 = max(total_vol ** 2 - idio_vol ** 2, 0.0)
    syst_vol = math.sqrt(syst0)

    # downside beta: regress on down-market days only.
    down_y = [y[i] for i in range(len(x)) if x[i] < 0]
    down_x = [x[i] for i in range(len(x)) if x[i] < 0]
    down_fit = _ols(down_y, down_x) if len(down_x) >= 5 else None
    downside_beta = down_fit[1] if down_fit else None

    momentum = math.prod(1 + r for r in y) - 1  # trailing cumulative over window

    return {
        "ticker": ticker,
        "benchmark": bench,
        "available": True,
        "window_days": len(y),
        "beta": round(beta, 3),
        "alpha_annual_pct": round(alpha_d * _TRADING_DAYS * 100, 2),
        "r_squared": round(r2, 3) if r2 is not None else None,
        "total_vol_annual_pct": round(total_vol * 100, 1),
        "idio_vol_annual_pct": round(idio_vol * 100, 1),
        "systematic_vol_annual_pct": round(syst_vol * 100, 1),
        "idio_share": round(idio_vol ** 2 / total_vol ** 2, 3) if total_vol > 1e-9 else None,
        "downside_beta": round(downside_beta, 3) if downside_beta is not None else None,
        "momentum_pct": round(momentum * 100, 1),
        # beta-neutral hedge: short this fraction of book in the index to flatten.
        "beta_hedge_ratio": round(beta, 3),
        "note": FACTOR_V2_NOTE,
    }
