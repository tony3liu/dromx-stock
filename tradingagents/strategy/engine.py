"""Strategy engine — load, execute, score declarative screening strategies.

Adapted from TickFlow's ``StrategyEngine`` (backend/app/strategy/engine.py). The
strategy *format* is preserved verbatim (declarative Python modules with META /
``filter(df, params)`` / ENTRY_SIGNALS / STOP_LOSS …) so the builtin strategies
port over almost unchanged. What we changed:

  * The enriched-data source is TradingAgents' free ``DataAdapter.load_universe``
    (Eastmoney snapshot + on-demand stockstats), not TickFlow's paid parquet.
  * ``META["markets"]`` gates a strategy to specific markets (US / HK / CN). The
    engine is built for one market and only loads strategies that apply to it —
    so A-share-only limit-up strategies never surface in an HK/US run.

The engine knows nothing about AI, HTTP, the frontend, or persistence — those
live in ``webapp/backend/strategy.py``.
"""
from __future__ import annotations

import importlib.util
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

import polars as pl

logger = logging.getLogger(__name__)

# Engine-level default coarse filter — a strategy may override via BASIC_FILTER.
# Kept market-neutral (no A-share board concepts) since HK/US are the priority.
DEFAULT_BASIC_FILTER: dict = {
    "price_min": None,
    "price_max": None,
    "amount_min": None,
    "amount_max": None,
    "turnover_min": None,
    "turnover_max": None,
    "enabled": True,
}


@dataclass
class StrategyDef:
    """A loaded strategy definition (read-only data + filter fn reference)."""
    meta: dict
    basic_filter: dict
    entry_signals: list[str]
    exit_signals: list[str]
    stop_loss: float | None
    max_hold_days: int | None
    alerts: list[dict]
    filter_fn: Callable[[pl.DataFrame, dict], pl.Expr] | None
    source: str  # "builtin" | "custom" | "ai"
    file_path: Path | None = None

    @property
    def markets(self) -> list[str]:
        """Markets this strategy applies to; empty/absent → all markets."""
        return [m.lower() for m in self.meta.get("markets", [])]

    def applies_to(self, market: str) -> bool:
        m = self.markets
        return (not m) or (market or "").lower() in m


@dataclass
class StrategyResult:
    """Result of executing one strategy."""
    as_of: str
    strategy_id: str
    market: str = ""
    rows: list[dict] = field(default_factory=list)
    total: int = 0
    elapsed_ms: float = 0.0
    scores: dict[str, float] = field(default_factory=dict)


class StrategyEngine:
    """Strategy loading + execution + scoring for one market."""

    def __init__(
        self,
        enriched_loader: Callable[[date], pl.DataFrame],
        strategy_dirs: list[Path] | None = None,
        market: str = "",
    ):
        """
        Args:
            enriched_loader: (as_of) -> enriched Polars DataFrame for the market.
            strategy_dirs:   directories to search for strategy .py files.
            market:          the market this engine serves (gates ``markets``).
        """
        self._loader = enriched_loader
        self._market = (market or "").lower()
        self._strategies: dict[str, StrategyDef] = {}
        self._load_errors: list[dict] = []
        self._strategy_dirs = strategy_dirs or []
        self._load_all()

    # ================================================================
    # Loading
    # ================================================================

    def _load_all(self) -> None:
        self._strategies.clear()
        self._load_errors = []
        for d in self._strategy_dirs:
            if not d.exists():
                continue
            for f in sorted(d.glob("*.py")):
                if f.name.startswith("_"):
                    continue
                try:
                    s = self._load_file(f)
                    # Gate by market: only surface strategies that apply here.
                    if self._market and not s.applies_to(self._market):
                        continue
                    self._strategies[s.meta["id"]] = s
                except Exception as e:  # noqa: BLE001
                    logger.warning("load strategy %s failed: %s", f.name, e)
                    self._load_errors.append({"file": f.name, "error": str(e)})

    def load_errors(self) -> list[dict]:
        return list(self._load_errors)

    @staticmethod
    def _load_file(path: Path) -> StrategyDef:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load module from {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        meta = dict(getattr(mod, "META", {}))
        meta.setdefault("id", path.stem)
        meta.setdefault("name", path.stem)
        meta.setdefault("description", "")
        meta.setdefault("markets", [])
        meta.setdefault("tags", [])
        meta.setdefault("params", [])
        meta.setdefault("scoring", {})
        meta.setdefault("order_by", "score")
        meta.setdefault("descending", True)
        meta.setdefault("limit", 50)

        bf = {**DEFAULT_BASIC_FILTER}
        strat_bf = getattr(mod, "BASIC_FILTER", None)
        if strat_bf:
            bf.update(strat_bf)
        if meta.get("basic_filter"):
            bf.update(meta["basic_filter"])

        source = "custom"
        p = str(path).replace("\\", "/")
        if "builtin" in p:
            source = "builtin"
        elif "/ai/" in p:
            source = "ai"

        return StrategyDef(
            meta=meta,
            basic_filter=bf,
            entry_signals=getattr(mod, "ENTRY_SIGNALS", []),
            exit_signals=getattr(mod, "EXIT_SIGNALS", []),
            stop_loss=getattr(mod, "STOP_LOSS", None),
            max_hold_days=getattr(mod, "MAX_HOLD_DAYS", None),
            alerts=getattr(mod, "ALERTS", []),
            filter_fn=getattr(mod, "filter", None),
            source=source,
            file_path=path,
        )

    def reload(self) -> None:
        self._load_all()

    # ================================================================
    # Query
    # ================================================================

    def list_strategies(self) -> list[dict]:
        return [{**s.meta, "source": s.source} for s in self._strategies.values()]

    def get(self, strategy_id: str) -> StrategyDef:
        s = self._strategies.get(strategy_id)
        if not s:
            raise ValueError(f"unknown strategy: {strategy_id}")
        return s

    def has(self, strategy_id: str) -> bool:
        return strategy_id in self._strategies

    # ================================================================
    # Execution
    # ================================================================

    def run(
        self,
        strategy_id: str,
        as_of: date,
        pool: list[str] | None = None,
        params: dict | None = None,
        overrides: dict | None = None,
        precomputed: pl.DataFrame | None = None,
    ) -> StrategyResult:
        """Execute a strategy: basic filter → strategy filter → score → rank."""
        t0 = time.perf_counter()
        s = self.get(strategy_id)
        params = params or {}
        overrides = overrides or {}
        as_of_str = as_of.isoformat() if isinstance(as_of, date) else str(as_of)

        if precomputed is not None and not precomputed.is_empty():
            df = precomputed
        else:
            df = self._loader(as_of)
        if df is None or df.is_empty():
            return StrategyResult(as_of=as_of_str, strategy_id=strategy_id, market=self._market)

        # Stage 1: basic filter.
        bf = dict(s.basic_filter) if s.basic_filter else {}
        if overrides.get("basic_filter"):
            bf.update(overrides["basic_filter"])
        if bf and bf.get("enabled", True):
            df = self._apply_basic_filter(df, bf)

        if pool and "symbol" in df.columns:
            df = df.filter(pl.col("symbol").is_in(pool))

        # Stage 2: strategy filter.
        if s.filter_fn:
            try:
                expr = s.filter_fn(df, params)
                df = df.filter(expr)
            except Exception as e:  # noqa: BLE001 — a bad strategy must not crash the API
                logger.warning("strategy %s filter failed: %s", strategy_id, e)
                return StrategyResult(as_of=as_of_str, strategy_id=strategy_id, market=self._market)

        # Stage 3: scoring.
        scoring = dict(s.meta.get("scoring", {}))
        if overrides.get("scoring"):
            scoring.update(overrides["scoring"])
        df = self._apply_scoring(df, scoring)

        # Rank + limit.
        limit = int(s.meta.get("limit", 50))
        desc = s.meta.get("descending", True)
        if "score" in df.columns:
            df = df.sort("score", descending=desc, nulls_last=True)
        elif s.meta.get("order_by") and s.meta["order_by"] in df.columns:
            df = df.sort(s.meta["order_by"], descending=desc, nulls_last=True)
        df = df.head(limit)

        rows = _sanitize(df.to_dicts())
        scores: dict[str, float] = {}
        if "score" in df.columns:
            for r in df.iter_rows(named=True):
                scores[r["symbol"]] = float(r.get("score") or 0)

        return StrategyResult(
            as_of=as_of_str,
            strategy_id=strategy_id,
            market=self._market,
            rows=rows,
            total=len(rows),
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            scores=scores,
        )

    # ================================================================
    # Internal: basic filter + scoring
    # ================================================================

    @staticmethod
    def _apply_basic_filter(df: pl.DataFrame, bf: dict) -> pl.DataFrame:
        exprs: list[pl.Expr] = []
        if bf.get("price_min") is not None and "close" in df.columns:
            exprs.append(pl.col("close") >= bf["price_min"])
        if bf.get("price_max") is not None and "close" in df.columns:
            exprs.append(pl.col("close") <= bf["price_max"])
        if bf.get("amount_min") is not None and "amount" in df.columns:
            exprs.append(pl.col("amount") >= bf["amount_min"])
        if bf.get("amount_max") is not None and "amount" in df.columns:
            exprs.append(pl.col("amount") <= bf["amount_max"])
        if bf.get("turnover_min") is not None and "turnover_rate" in df.columns:
            exprs.append(pl.col("turnover_rate") >= bf["turnover_min"])
        if bf.get("turnover_max") is not None and "turnover_rate" in df.columns:
            exprs.append(pl.col("turnover_rate") <= bf["turnover_max"])
        if bf.get("market_cap_min") is not None and "market_cap" in df.columns:
            exprs.append(pl.col("market_cap") >= bf["market_cap_min"])
        if exprs:
            return df.filter(pl.all_horizontal(exprs))
        return df

    @staticmethod
    def _apply_scoring(df: pl.DataFrame, weights: dict) -> pl.DataFrame:
        """Generic scoring: min-max normalise each factor → weighted sum → 0-100."""
        if not weights or df.is_empty():
            return df
        total_weight = sum(weights.values())
        if total_weight <= 0:
            return df

        parts: list[pl.Expr] = []
        for col, weight in weights.items():
            if col not in df.columns:
                continue
            w = weight / total_weight
            col_min = pl.col(col).min()
            col_range = pl.col(col).max() - col_min
            normalized = (
                pl.when(col_range > 0)
                .then((pl.col(col) - col_min) / col_range)
                .otherwise(pl.lit(0.5))
            )
            parts.append(normalized * w)

        if not parts:
            return df
        expr = parts[0]
        for p in parts[1:]:
            expr = expr + p
        return df.with_columns((expr * 100).alias("score"))


def _sanitize(rows: list[dict]) -> list[dict]:
    """Replace NaN/inf floats with None so the result is JSON-safe."""
    for r in rows:
        for k, v in list(r.items()):
            if isinstance(v, float) and (v != v or abs(v) == float("inf")):
                r[k] = None
    return rows
