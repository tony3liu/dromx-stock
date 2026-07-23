"""Strategy engine layer (v0.4.0) — declarative screening strategies over the
free full-market snapshot.

This package adds a "选股 (screening)" capability on top of DromX'
existing analysis/reflection engine. It is inspired by TickFlow's strategy
system but shares none of its paid API dependency: the full-market universe
comes from Eastmoney's keyless ``clist`` endpoint
(``dromx.dataflows.eastmoney_universe``) and per-name technical
indicators are computed on demand from the existing free OHLCV vendors
(tencent / mootdx / yfinance) via ``stockstats``.

Public surface:
  - ``StrategyEngine`` / ``StrategyDef`` / ``StrategyResult`` — load + run strategies
  - ``DataAdapter`` — free full-market ``load_universe(market, as_of)`` loader
  - ``AIStrategyGenerator`` — LLM-authored strategy code (safety-checked)
"""
from __future__ import annotations

from dromx.strategy.data_adapter import DataAdapter
from dromx.strategy.engine import StrategyDef, StrategyEngine, StrategyResult

__all__ = [
    "StrategyEngine",
    "StrategyDef",
    "StrategyResult",
    "DataAdapter",
]
