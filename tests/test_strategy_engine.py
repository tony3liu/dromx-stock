"""Strategy engine + universe adapter isolation tests (no network, no LLM).

Covers the free full-market screening path added in v0.4.0:
  - eastmoney_universe: field normalisation, symbol suffixing, list/dict diff,
    percent handling — all against a mocked HTTP response.
  - DataAdapter: stage-1 prefilter → stage-2 indicator compute with load_ohlcv
    mocked to a synthetic OHLCV frame (deterministic, offline).
  - StrategyEngine: market gating, deterministic filter + scoring + ranking.
"""

from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd
import polars as pl
import pytest

BUILTIN_DIR = Path(__file__).resolve().parents[1] / "tradingagents" / "strategy" / "builtin"


# ---------------------------------------------------------------------------
# eastmoney_universe
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUniverseSnapshot:
    def _fake_response(self, diff, total):
        resp = mock.MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"data": {"total": total, "diff": diff}}
        return resp

    def test_hk_symbol_zero_padded_and_suffixed(self):
        from tradingagents.dataflows import eastmoney_universe as eu

        diff = [{"f12": "700", "f14": "腾讯", "f2": 400.0, "f3": 1.5,
                 "f5": 100, "f6": 200.0, "f8": 0.3, "f9": 20.0,
                 "f10": 1.1, "f20": 1e12, "f24": 5.0}]
        with mock.patch.object(eu._SESSION, "get",
                               return_value=self._fake_response(diff, 1)):
            rows = eu.fetch_universe_snapshot("hk")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "00700.HK"
        assert rows[0]["close"] == 400.0
        assert rows[0]["change_pct"] == 1.5

    def test_cn_symbol_exchange_suffix_by_prefix(self):
        from tradingagents.dataflows import eastmoney_universe as eu

        diff = [
            {"f12": "600519", "f14": "贵州茅台"},
            {"f12": "000001", "f14": "平安银行"},
            {"f12": "300750", "f14": "宁德时代"},
        ]
        with mock.patch.object(eu._SESSION, "get",
                               return_value=self._fake_response(diff, 3)):
            rows = eu.fetch_universe_snapshot("cn")
        syms = {r["name"]: r["symbol"] for r in rows}
        assert syms["贵州茅台"] == "600519.SS"
        assert syms["平安银行"] == "000001.SZ"
        assert syms["宁德时代"] == "300750.SZ"

    def test_diff_as_dict_is_parsed(self):
        # Eastmoney sometimes returns diff as an index-keyed dict, not a list.
        from tradingagents.dataflows import eastmoney_universe as eu

        diff = {"0": {"f12": "AAPL", "f14": "Apple", "f2": 190.0, "f3": 0.5},
                "1": {"f12": "MSFT", "f14": "Microsoft", "f2": 420.0, "f3": -0.2}}
        with mock.patch.object(eu._SESSION, "get",
                               return_value=self._fake_response(diff, 2)):
            rows = eu.fetch_universe_snapshot("us")
        assert {r["symbol"] for r in rows} == {"AAPL", "MSFT"}

    def test_missing_numeric_becomes_none(self):
        from tradingagents.dataflows import eastmoney_universe as eu

        diff = [{"f12": "00001", "f14": "X", "f2": "-", "f3": None, "f8": "-"}]
        with mock.patch.object(eu._SESSION, "get",
                               return_value=self._fake_response(diff, 1)):
            rows = eu.fetch_universe_snapshot("hk")
        assert rows[0]["close"] is None
        assert rows[0]["change_pct"] is None
        assert rows[0]["turnover_rate"] is None

    def test_unknown_market_returns_empty(self):
        from tradingagents.dataflows import eastmoney_universe as eu

        assert eu.fetch_universe_snapshot("mars") == []

    def test_network_failure_degrades_to_empty(self):
        from tradingagents.dataflows import eastmoney_universe as eu

        with mock.patch.object(eu._SESSION, "get", side_effect=Exception("boom")):
            assert eu.fetch_universe_snapshot("hk") == []


# ---------------------------------------------------------------------------
# DataAdapter (stage-1 prefilter + stage-2 compute)
# ---------------------------------------------------------------------------


def _synthetic_ohlcv(n=80, base=10.0, drift=0.01):
    """Deterministic rising OHLCV frame with enough rows for 60-day windows."""
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    closes = [base * (1 + drift) ** i for i in range(n)]
    return pd.DataFrame({
        "Date": dates,
        "Open": [c * 0.99 for c in closes],
        "High": [c * 1.02 for c in closes],
        "Low": [c * 0.98 for c in closes],
        "Close": closes,
        "Volume": [1_000_000 + i * 1000 for i in range(n)],
    })


@pytest.mark.unit
class TestDataAdapter:
    def test_load_universe_prefilter_and_compute(self):
        from tradingagents.strategy.data_adapter import DataAdapter

        snapshot = [
            {"symbol": "00001.HK", "name": "A", "close": 10.0, "change_pct": 8.0,
             "turnover_rate": 5.0, "vol_ratio": 1.2, "amount": 1e8, "pe": 12.0,
             "change_60d": 20.0, "market_cap": 1e10, "market": "hk"},
            {"symbol": "00002.HK", "name": "B", "close": 20.0, "change_pct": 0.1,
             "turnover_rate": 1.0, "vol_ratio": 0.9, "amount": 5e7, "pe": 30.0,
             "change_60d": 2.0, "market_cap": 5e9, "market": "hk"},
        ]
        adapter = DataAdapter(max_candidates=10, use_cache=False)
        with mock.patch(
            "tradingagents.strategy.data_adapter.fetch_universe_snapshot",
            return_value=snapshot,
        ), mock.patch(
            "tradingagents.dataflows.stockstats_utils.load_ohlcv",
            return_value=_synthetic_ohlcv(),
        ):
            df = adapter.load_universe(
                "hk", date(2026, 6, 30), prefilter=pl.col("change_pct") > 3.0
            )
        # Only 00001.HK passes the >3% prefilter.
        assert df.height == 1
        assert df.get_column("symbol").to_list() == ["00001.HK"]
        # Stage-2 indicators materialised, snapshot percents converted to fractions.
        row = df.to_dicts()[0]
        assert row["turnover_rate"] == pytest.approx(0.05)  # 5% -> 0.05
        assert "rsi_14" in row and row["ma20"] is not None
        assert isinstance(row["signal_ma20_breakout"], bool)

    def test_empty_snapshot_yields_empty_frame(self):
        from tradingagents.strategy.data_adapter import DataAdapter

        adapter = DataAdapter(use_cache=False)
        with mock.patch(
            "tradingagents.strategy.data_adapter.fetch_universe_snapshot",
            return_value=[],
        ):
            df = adapter.load_universe("hk", date(2026, 6, 30))
        assert df.is_empty()

    def test_symbol_with_failing_ohlcv_is_skipped(self):
        from tradingagents.strategy.data_adapter import DataAdapter

        snapshot = [
            {"symbol": "00001.HK", "name": "A", "close": 10.0, "change_pct": 8.0,
             "turnover_rate": 5.0, "market": "hk"},
            {"symbol": "00002.HK", "name": "B", "close": 20.0, "change_pct": 9.0,
             "turnover_rate": 6.0, "market": "hk"},
        ]

        def flaky_load(symbol, curr_date):
            if symbol == "00002.HK":
                raise RuntimeError("no data")
            return _synthetic_ohlcv()

        adapter = DataAdapter(max_candidates=10, use_cache=False)
        with mock.patch(
            "tradingagents.strategy.data_adapter.fetch_universe_snapshot",
            return_value=snapshot,
        ), mock.patch(
            "tradingagents.dataflows.stockstats_utils.load_ohlcv",
            side_effect=flaky_load,
        ):
            df = adapter.load_universe("hk", date(2026, 6, 30))
        assert df.get_column("symbol").to_list() == ["00001.HK"]


# ---------------------------------------------------------------------------
# StrategyEngine (loading, gating, filter, scoring)
# ---------------------------------------------------------------------------


def _mock_frame():
    return pl.DataFrame({
        "symbol": ["00001.HK", "00002.HK", "00003.HK"],
        "name": ["A", "B", "C"],
        "close": [10.0, 20.0, 30.0],
        "open": [9.5, 21.0, 29.0],
        "rsi_14": [25.0, 55.0, 28.0],
        "vol_ratio_5d": [2.0, 0.8, 1.5],
        "change_pct": [0.05, -0.02, 0.03],
        "momentum_5d": [0.04, 0.01, 0.02],
        "ma5": [9.8, 20.5, 29.5],
        "ma20": [9.0, 21.0, 28.0],
        "ma60": [8.0, 22.0, 27.0],
    })


@pytest.mark.unit
class TestStrategyEngine:
    def test_market_gating_hk_excludes_limit_up_strategies(self):
        from tradingagents.strategy.engine import StrategyEngine

        eng = StrategyEngine(lambda d: pl.DataFrame(), [BUILTIN_DIR], market="hk")
        ids = {s["id"] for s in eng.list_strategies()}
        assert "oversold_bounce" in ids
        assert "consecutive_limit_ups" not in ids  # CN-only
        assert eng.load_errors() == []

    def test_market_gating_cn_includes_all(self):
        from tradingagents.strategy.engine import StrategyEngine

        eng = StrategyEngine(lambda d: pl.DataFrame(), [BUILTIN_DIR], market="cn")
        ids = {s["id"] for s in eng.list_strategies()}
        assert "consecutive_limit_ups" in ids
        assert len(ids) == 18

    def test_run_filters_and_scores_deterministically(self):
        from tradingagents.strategy.engine import StrategyEngine

        eng = StrategyEngine(lambda d: _mock_frame(), [BUILTIN_DIR], market="hk")
        r = eng.run("oversold_bounce", date(2026, 6, 30))
        # RSI<30 + green + vol>=1.2 → 00001 and 00003.
        assert [row["symbol"] for row in r.rows] == ["00001.HK", "00003.HK"]
        assert r.scores["00001.HK"] > r.scores["00003.HK"]
        assert r.market == "hk"

    def test_run_unknown_strategy_raises(self):
        from tradingagents.strategy.engine import StrategyEngine

        eng = StrategyEngine(lambda d: _mock_frame(), [BUILTIN_DIR], market="hk")
        with pytest.raises(ValueError):
            eng.run("does_not_exist", date(2026, 6, 30))

    def test_run_on_empty_universe_returns_empty_result(self):
        from tradingagents.strategy.engine import StrategyEngine

        eng = StrategyEngine(lambda d: pl.DataFrame(), [BUILTIN_DIR], market="hk")
        r = eng.run("oversold_bounce", date(2026, 6, 30))
        assert r.total == 0 and r.rows == []

    def test_bad_strategy_filter_does_not_crash(self):
        # A strategy referencing a column absent from the frame must degrade to
        # an empty result, not propagate a Polars error to the API layer.
        from tradingagents.strategy.engine import StrategyEngine

        frame = pl.DataFrame({"symbol": ["X"], "close": [1.0]})
        eng = StrategyEngine(lambda d: frame, [BUILTIN_DIR], market="hk")
        r = eng.run("oversold_bounce", date(2026, 6, 30))  # needs rsi_14 etc.
        assert r.total == 0
