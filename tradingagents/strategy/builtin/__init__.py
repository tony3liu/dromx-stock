"""Builtin screening strategies (ported from TickFlow).

Each strategy is a declarative module: ``META`` (with a ``markets`` gate),
``filter(df, params) -> pl.Expr``, and optional ENTRY/EXIT signals, STOP_LOSS,
MAX_HOLD_DAYS. The engine loads every ``*.py`` here (files starting with ``_``
are skipped).

UNIT CONVENTION: ratio-like columns (change_pct, turnover_rate, momentum_*,
annual_vol_20d, amplitude) are FRACTIONS (0.05 == 5%), matching what
``strategy.data_adapter`` produces.
"""
