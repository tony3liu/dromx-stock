"""Full-market data adapter — the free ``universe`` loader for the strategy engine.

The strategy engine (``strategy.engine``) is a straight adaptation of TickFlow's
declarative screener, but TickFlow fed it a pre-computed A-share parquet built
from a paid feed. We have neither the parquet nor the paid feed, so this adapter
manufactures the same shape of DataFrame from TradingAgents' free data layer.

Two-stage design (the only tractable approach for a free, no-key setup — you
cannot pull 5000 symbols' OHLCV history on every run):

  Stage 1 — coarse screen (cheap, one HTTP call):
      ``eastmoney_universe.fetch_universe_snapshot(market)`` returns every listed
      name's latest snapshot (close / change_pct / turnover / vol_ratio / amount /
      60-day change / market cap). A ``prefilter`` narrows this to a candidate
      shortlist so stage 2 stays bounded.

  Stage 2 — fine compute (per candidate, cached):
      For each shortlisted symbol we pull its OHLCV history via the existing free
      vendors (``load_ohlcv`` → tencent / mootdx / yfinance), run it through
      ``stockstats`` to compute ma/rsi/macd/boll, derive momentum + rolling
      extremes + the ``signal_*`` booleans the builtin strategies reference, and
      keep the ``as_of`` row.

The resulting Polars DataFrame carries the union of columns the builtin
strategies read (see ``strategy/builtin/*.py``). The whole day's result is cached
to ``~/.tradingagents/strategy_cache/{market}_{as_of}.parquet`` so re-running any
strategy the same day is instant.

Everything is best-effort: a symbol whose OHLCV fetch or indicator computation
fails is skipped, never fatal.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import pandas as pd
import polars as pl
from stockstats import wrap

from tradingagents.dataflows.eastmoney_universe import fetch_universe_snapshot

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(os.path.expanduser("~")) / ".tradingagents" / "strategy_cache"

# Default ceiling on how many snapshot names get promoted to stage-2 compute.
# Pulling OHLCV history is the expensive part; the prefilter should cut well
# below this, but we hard-cap so a permissive prefilter can't blow up a run.
DEFAULT_MAX_CANDIDATES = 120

# Columns produced by stage-2 compute (the union of what builtin strategies read).
# UNIT CONVENTION (matches TickFlow strategies so they port verbatim): ratio-like
# fields — change_pct, turnover_rate, momentum_*, annual_vol_20d, amplitude — are
# FRACTIONS (0.05 == 5%), NOT percents. The Eastmoney snapshot delivers percents,
# so we divide by 100 on merge.
_ENRICHED_NUMERIC = [
    "ma5", "ma10", "ma20", "ma60",
    "rsi_14", "macd_dif", "macd_dea", "macd_hist",
    "boll", "boll_upper", "boll_lower",
    "vol_ratio_5d", "momentum_5d", "momentum_20d", "momentum_60d",
    "high_60d", "low_60d", "prev_close", "atr_14", "annual_vol_20d",
    "change_pct", "amplitude",
]
_SIGNAL_COLS = [
    "signal_ma_golden_5_20", "signal_ma_dead_5_20",
    "signal_macd_golden", "signal_macd_dead",
    "signal_ma20_breakout", "signal_ma20_breakdown",
    "signal_n_day_high", "signal_n_day_low",
    "signal_boll_breakout_upper", "signal_boll_breakdown_lower",
    "signal_volume_surge",
]


def _pct_to_frac(v):
    """Eastmoney percent (5.0 == 5%) → strategy fraction (0.05). None-safe."""
    if v is None:
        return None
    try:
        return float(v) / 100.0
    except (TypeError, ValueError):
        return None


class DataAdapter:
    """Loads a full-market enriched Polars frame for a given market + date.

    Args:
        max_candidates: stage-2 compute ceiling (0 or None → DEFAULT).
        use_cache:      read/write the per-day parquet cache.
    """

    def __init__(self, *, max_candidates: int | None = None, use_cache: bool = True):
        self._max_candidates = max_candidates or DEFAULT_MAX_CANDIDATES
        self._use_cache = use_cache

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load_universe(
        self,
        market: str,
        as_of: date,
        *,
        prefilter: "pl.Expr | None" = None,
        max_candidates: int | None = None,
    ) -> pl.DataFrame:
        """Return the enriched full-market frame for ``market`` on ``as_of``.

        ``prefilter`` is an optional Polars boolean expression over the *snapshot*
        columns (close/change_pct/turnover_rate/vol_ratio/amount/change_60d/
        market_cap) used to shortlist candidates before the expensive per-symbol
        indicator compute. When None, candidates are the top names by absolute
        change (a sensible generic default).
        """
        market = (market or "").strip().lower()
        cap = max_candidates or self._max_candidates

        cached = self._read_cache(market, as_of)
        if cached is not None:
            return cached

        snapshot = fetch_universe_snapshot(market)
        if not snapshot:
            logger.warning("empty universe snapshot for %s", market)
            return pl.DataFrame()

        snap_df = pl.DataFrame(snapshot)

        # Stage 1: coarse screen over cheap snapshot fields.
        candidates = snap_df
        if prefilter is not None:
            try:
                candidates = snap_df.filter(prefilter)
            except Exception as e:  # noqa: BLE001 — a bad prefilter must not crash the run
                logger.warning("prefilter failed (%s); using full snapshot", e)
                candidates = snap_df

        # Bound stage-2 cost: keep the most active names (by |change_pct|).
        if candidates.height > cap and "change_pct" in candidates.columns:
            candidates = candidates.sort(
                pl.col("change_pct").abs(), descending=True, nulls_last=True
            ).head(cap)
        elif candidates.height > cap:
            candidates = candidates.head(cap)

        symbols = candidates.get_column("symbol").to_list()
        logger.info(
            "universe %s %s: %d snapshot -> %d candidates for compute",
            market, as_of, snap_df.height, len(symbols),
        )

        # Stage 2: per-candidate indicator compute (best-effort, skip failures).
        enriched_rows: list[dict] = []
        snap_by_symbol = {r["symbol"]: r for r in snapshot}
        as_of_str = as_of.isoformat() if isinstance(as_of, date) else str(as_of)
        for sym in symbols:
            row = self._compute_one(sym, as_of_str, snap_by_symbol.get(sym, {}))
            if row is not None:
                enriched_rows.append(row)

        if not enriched_rows:
            logger.warning("no candidate produced indicators for %s %s", market, as_of)
            return pl.DataFrame()

        df = pl.DataFrame(enriched_rows)
        # A-share only: merge the free limit-up pool so the CN limit-up strategies
        # (连板/涨停接力/断板反包) get signal_limit_up + consecutive_limit_ups. Other
        # markets have no limit concept — skip (their limit-up strategies are gated
        # out by markets anyway).
        if market == "cn":
            df = self._inject_limit_up(df, as_of)

        self._write_cache(market, as_of, df)
        return df

    @staticmethod
    def _inject_limit_up(df: pl.DataFrame, as_of: date) -> pl.DataFrame:
        """Add signal_limit_up / consecutive_limit_ups / limit_up_broken_count.

        One pooled fetch for the whole day (not per symbol). On failure the pool is
        empty → all-False / 0, so limit-up strategies simply find nothing.
        """
        from tradingagents.dataflows.eastmoney_limitup import fetch_limit_up_pool

        try:
            pool = fetch_limit_up_pool(as_of)
        except Exception as e:  # noqa: BLE001 — best-effort, never crash the screen
            logger.warning("limit-up pool fetch failed: %s", e)
            pool = {}

        syms = df.get_column("symbol").to_list()
        sig = [s in pool for s in syms]
        consec = [int(pool.get(s, {}).get("consecutive", 0)) for s in syms]
        broken = [int(pool.get(s, {}).get("broken", 0)) for s in syms]
        return df.with_columns([
            pl.Series("signal_limit_up", sig),
            pl.Series("consecutive_limit_ups", consec),
            pl.Series("limit_up_broken_count", broken),
        ])

    # ------------------------------------------------------------------
    # Stage 2: per-symbol indicator compute
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_one(symbol: str, as_of_str: str, snap: dict) -> dict | None:
        """Compute the enriched row for one symbol; None on any failure."""
        from tradingagents.dataflows.stockstats_utils import load_ohlcv

        try:
            ohlcv = load_ohlcv(symbol, as_of_str)
        except Exception as e:  # noqa: BLE001 — best-effort per symbol
            logger.debug("load_ohlcv failed for %s: %s", symbol, e)
            return None
        if ohlcv is None or ohlcv.empty or len(ohlcv) < 20:
            return None

        try:
            enriched = DataAdapter._indicators(ohlcv)
        except Exception as e:  # noqa: BLE001
            logger.debug("indicator compute failed for %s: %s", symbol, e)
            return None
        if enriched is None:
            return None

        # Merge snapshot fields (name / turnover / vol_ratio / amount / …) — the
        # snapshot is the freshest source for those; indicators fill the rest.
        # Snapshot percents → fractions to match the strategy unit convention.
        row = {
            "symbol": symbol,
            "name": snap.get("name") or symbol,
            "turnover_rate": _pct_to_frac(snap.get("turnover_rate")),
            "vol_ratio": snap.get("vol_ratio"),
            "amount": snap.get("amount"),
            "pe": snap.get("pe"),
            "change_60d": _pct_to_frac(snap.get("change_60d")),
            "market_cap": snap.get("market_cap"),
        }
        row.update(enriched)
        return row

    @staticmethod
    def _indicators(ohlcv: pd.DataFrame) -> dict | None:
        """Run stockstats + derive strategy columns; return the last row as dict.

        Column names map onto what the builtin strategies read (TickFlow schema):
        stockstats ``close_5_sma`` → ``ma5``, ``macd``/``macds``/``macdh`` →
        ``macd_dif``/``macd_dea``/``macd_hist``, ``boll_ub``/``boll_lb`` →
        ``boll_upper``/``boll_lower``.
        """
        df = wrap(ohlcv.copy())
        # Trigger stockstats to materialise each indicator column.
        for ind in ("rsi_14", "close_5_sma", "close_10_sma", "close_20_sma",
                    "close_60_sma", "macd", "macds", "macdh",
                    "boll", "boll_ub", "boll_lb", "atr_14"):
            try:
                df[ind]
            except Exception:  # noqa: BLE001 — some indicators need more rows
                pass

        # stockstats lower-cases OHLC; normalise back to a clean pandas frame.
        pdf = pd.DataFrame({
            "close": df["close"].astype(float),
            "open": df["open"].astype(float),
            "high": df["high"].astype(float),
            "low": df["low"].astype(float),
            "volume": df["volume"].astype(float),
            "ma5": df.get("close_5_sma"),
            "ma10": df.get("close_10_sma"),
            "ma20": df.get("close_20_sma"),
            "ma60": df.get("close_60_sma"),
            "rsi_14": df.get("rsi_14"),
            "macd_dif": df.get("macd"),
            "macd_dea": df.get("macds"),
            "macd_hist": df.get("macdh"),
            "boll": df.get("boll"),
            "boll_upper": df.get("boll_ub"),
            "boll_lower": df.get("boll_lb"),
            "atr_14": df.get("atr_14"),
        })
        if pdf.empty:
            return None

        # Derived columns (rolling windows over the price series). Ratio-like
        # fields are FRACTIONS (0.05 == 5%) to match the strategy convention.
        pdf["prev_close"] = pdf["close"].shift(1)
        pdf["change_pct"] = pdf["close"] / pdf["prev_close"] - 1.0
        pdf["amplitude"] = (pdf["high"] - pdf["low"]) / pdf["prev_close"]
        vol_ma5 = pdf["volume"].rolling(5).mean()
        pdf["vol_ratio_5d"] = pdf["volume"] / vol_ma5
        pdf["momentum_5d"] = pdf["close"] / pdf["close"].shift(5) - 1.0
        pdf["momentum_20d"] = pdf["close"] / pdf["close"].shift(20) - 1.0
        pdf["momentum_60d"] = pdf["close"] / pdf["close"].shift(60) - 1.0
        pdf["high_60d"] = pdf["high"].rolling(60, min_periods=1).max()
        pdf["low_60d"] = pdf["low"].rolling(60, min_periods=1).min()
        pdf["annual_vol_20d"] = pdf["close"].pct_change().rolling(20).std() * (252 ** 0.5)

        # signal_* booleans (ported from TickFlow indicators/pipeline.py).
        prev = pdf.shift(1)
        pdf["signal_ma_golden_5_20"] = (pdf["ma5"] > pdf["ma20"]) & (prev["ma5"] <= prev["ma20"])
        pdf["signal_ma_dead_5_20"] = (pdf["ma5"] < pdf["ma20"]) & (prev["ma5"] >= prev["ma20"])
        pdf["signal_macd_golden"] = (pdf["macd_dif"] > pdf["macd_dea"]) & (prev["macd_dif"] <= prev["macd_dea"])
        pdf["signal_macd_dead"] = (pdf["macd_dif"] < pdf["macd_dea"]) & (prev["macd_dif"] >= prev["macd_dea"])
        pdf["signal_ma20_breakout"] = (pdf["close"] > pdf["ma20"]) & (prev["close"] <= prev["ma20"])
        pdf["signal_ma20_breakdown"] = (pdf["close"] < pdf["ma20"]) & (prev["close"] >= prev["ma20"])
        pdf["signal_n_day_high"] = pdf["close"] >= pdf["high_60d"]
        pdf["signal_n_day_low"] = pdf["close"] <= pdf["low_60d"]
        pdf["signal_boll_breakout_upper"] = pdf["close"] > pdf["boll_upper"]
        pdf["signal_boll_breakdown_lower"] = pdf["close"] < pdf["boll_lower"]
        pdf["signal_volume_surge"] = pdf["vol_ratio_5d"] >= 2.0

        last = pdf.iloc[-1]
        out: dict = {}
        for col in ("close", "open", "high", "low", "volume", *_ENRICHED_NUMERIC):
            if col in pdf.columns:
                v = last[col]
                out[col] = None if pd.isna(v) else float(v)
        for col in _SIGNAL_COLS:
            v = last[col]
            out[col] = False if pd.isna(v) else bool(v)
        return out

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_path(self, market: str, as_of: date) -> Path:
        as_of_str = as_of.isoformat() if isinstance(as_of, date) else str(as_of)
        return _CACHE_DIR / f"{market}_{as_of_str}.parquet"

    def _read_cache(self, market: str, as_of: date) -> pl.DataFrame | None:
        if not self._use_cache:
            return None
        path = self._cache_path(market, as_of)
        if not path.exists():
            return None
        try:
            df = pl.read_parquet(path)
            logger.info("universe cache hit %s (%d rows)", path.name, df.height)
            return df
        except Exception as e:  # noqa: BLE001
            logger.warning("universe cache read failed %s: %s", path.name, e)
            return None

    def _write_cache(self, market: str, as_of: date, df: pl.DataFrame) -> None:
        if not self._use_cache or df.is_empty():
            return
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.write_parquet(self._cache_path(market, as_of))
        except Exception as e:  # noqa: BLE001
            logger.warning("universe cache write failed: %s", e)
