"""连板股 — 涨停且连续涨停≥2天。

A股专属 (markets: CN)：依赖涨跌停板概念列 signal_limit_up /
consecutive_limit_ups，这些列由 Phase 4 的 A 股专用数据适配补齐，届时才真正启用。
HK/US 运行时本策略被 markets 门控排除，不会加载。
"""
import polars as pl

META = {
    "id": "consecutive_limit_ups",
    "name": "连板股",
    "description": "当日涨停且连续涨停≥2天, 强势追涨",
    "markets": ["CN"],
    "tags": ["涨停", "连板"],
    "params": [
        {"id": "min_boards", "label": "最少连板数", "type": "int",
         "default": 2, "min": 1, "max": 20, "step": 1},
    ],
    "scoring": {"consecutive_limit_ups": 0.5, "change_pct": 0.3, "amount": 0.2},
    "order_by": "score",
    "descending": True,
    "limit": 100,
}

ENTRY_SIGNALS = ["signal_limit_up"]
EXIT_SIGNALS = []
STOP_LOSS = -0.05
MAX_HOLD_DAYS = 5
ALERTS = []


def filter(df: pl.DataFrame, params: dict) -> pl.Expr:
    min_boards = params.get("min_boards", 2)
    return (
        pl.col("signal_limit_up").fill_null(False)
        & (pl.col("consecutive_limit_ups") >= min_boards)
    )
