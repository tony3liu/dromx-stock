"""A-share limit-up pool + data_adapter injection + CN strategy tests (no network)."""

from datetime import date
from unittest import mock

import pandas as pd
import polars as pl
import pytest

BUILTIN_DIR = __import__("pathlib").Path(__file__).resolve().parents[1] / "dromx" / "strategy" / "builtin"


# ---------------------------------------------------------------------------
# eastmoney_limitup fetcher
# ---------------------------------------------------------------------------


def _zt_response(pool):
    resp = mock.MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"tc": len(pool), "qdate": 20260706, "pool": pool}}
    return resp


@pytest.mark.unit
class TestLimitUpPool:
    def test_normalize_symbol_and_fields(self):
        from dromx.dataflows import eastmoney_limitup as lu

        pool = [
            {"c": "603137", "m": 1, "n": "恒尚节能", "p": 5000, "zdp": 10.0,
             "lbc": 5, "zbc": 0, "hybk": "装修装饰", "fund": 1e8, "zttj": {"days": 5, "ct": 5}},
            {"c": "000656", "m": 0, "n": "金科股份", "p": 1430, "zdp": 10.0,
             "lbc": 3, "zbc": 4, "hybk": "房地产开", "fund": 1e7, "zttj": {"days": 3, "ct": 3}},
        ]
        with mock.patch.object(lu._SESSION, "get", return_value=_zt_response(pool)):
            out = lu.fetch_limit_up_pool(date(2026, 7, 6))
        assert set(out) == {"603137.SS", "000656.SZ"}          # m=1→.SS, m=0→.SZ
        assert out["603137.SS"]["consecutive"] == 5
        assert out["000656.SZ"]["broken"] == 4
        assert out["000656.SZ"]["hybk"] == "房地产开"

    def test_empty_pool(self):
        from dromx.dataflows import eastmoney_limitup as lu

        with mock.patch.object(lu._SESSION, "get", return_value=_zt_response([])):
            assert lu.fetch_limit_up_pool(date(2026, 7, 6)) == {}

    def test_network_failure_degrades_to_empty(self):
        from dromx.dataflows import eastmoney_limitup as lu

        with mock.patch.object(lu._SESSION, "get", side_effect=Exception("boom")):
            assert lu.fetch_limit_up_pool(date(2026, 7, 6)) == {}

    def test_limit_down_pool(self):
        from dromx.dataflows import eastmoney_limitup as lu

        pool = [{"c": "605598", "m": 1, "n": "上海港湾", "zdp": -10.0, "oc": 9, "days": 1, "hybk": "专业工程"}]
        with mock.patch.object(lu._SESSION, "get", return_value=_zt_response(pool)):
            out = lu.fetch_limit_down_pool(date(2026, 7, 6))
        assert out["605598.SS"]["open_count"] == 9


# ---------------------------------------------------------------------------
# DataAdapter CN limit-up injection
# ---------------------------------------------------------------------------


def _synthetic_ohlcv(n=80, base=10.0):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    closes = [base * (1 + 0.01) ** i for i in range(n)]
    return pd.DataFrame({
        "Date": dates, "Open": [c * 0.99 for c in closes], "High": [c * 1.02 for c in closes],
        "Low": [c * 0.98 for c in closes], "Close": closes, "Volume": [1e6 + i for i in range(n)],
    })


@pytest.mark.unit
class TestAdapterLimitUpInjection:
    def _snapshot(self):
        return [
            {"symbol": "600001.SS", "name": "A", "close": 10.0, "change_pct": 9.9, "market": "cn"},
            {"symbol": "000002.SZ", "name": "B", "close": 20.0, "change_pct": 4.0, "market": "cn"},
        ]

    def test_cn_injects_limit_up_columns(self):
        from dromx.strategy.data_adapter import DataAdapter

        pool = {"600001.SS": {"consecutive": 3, "broken": 1}}
        adapter = DataAdapter(max_candidates=10, use_cache=False)
        with mock.patch("dromx.strategy.data_adapter.fetch_universe_snapshot", return_value=self._snapshot()), \
             mock.patch("dromx.dataflows.stockstats_utils.load_ohlcv", return_value=_synthetic_ohlcv()), \
             mock.patch("dromx.dataflows.eastmoney_limitup.fetch_limit_up_pool", return_value=pool):
            df = adapter.load_universe("cn", date(2026, 7, 6))
        assert "signal_limit_up" in df.columns and "consecutive_limit_ups" in df.columns
        rec = {r["symbol"]: r for r in df.to_dicts()}
        assert rec["600001.SS"]["signal_limit_up"] is True
        assert rec["600001.SS"]["consecutive_limit_ups"] == 3
        assert rec["000002.SZ"]["signal_limit_up"] is False
        assert rec["000002.SZ"]["consecutive_limit_ups"] == 0

    def test_non_cn_does_not_inject(self):
        from dromx.strategy.data_adapter import DataAdapter

        snap = [{"symbol": "00700.HK", "name": "T", "close": 400.0, "change_pct": 5.0, "market": "hk"}]
        adapter = DataAdapter(max_candidates=10, use_cache=False)
        with mock.patch("dromx.strategy.data_adapter.fetch_universe_snapshot", return_value=snap), \
             mock.patch("dromx.dataflows.stockstats_utils.load_ohlcv", return_value=_synthetic_ohlcv()), \
             mock.patch("dromx.dataflows.eastmoney_limitup.fetch_limit_up_pool") as fetch:
            df = adapter.load_universe("hk", date(2026, 7, 6))
        fetch.assert_not_called()  # HK must not hit the A-share pool
        assert "signal_limit_up" not in df.columns

    def test_pool_failure_yields_all_false(self):
        from dromx.strategy.data_adapter import DataAdapter

        adapter = DataAdapter(max_candidates=10, use_cache=False)
        with mock.patch("dromx.strategy.data_adapter.fetch_universe_snapshot", return_value=self._snapshot()), \
             mock.patch("dromx.dataflows.stockstats_utils.load_ohlcv", return_value=_synthetic_ohlcv()), \
             mock.patch("dromx.dataflows.eastmoney_limitup.fetch_limit_up_pool", side_effect=RuntimeError("down")):
            df = adapter.load_universe("cn", date(2026, 7, 6))
        assert df.get_column("signal_limit_up").to_list() == [False, False]


# ---------------------------------------------------------------------------
# CN limit-up strategies run against an injected frame
# ---------------------------------------------------------------------------


def _cn_frame():
    # 3 limit-up names with varying board counts + one non-limit name.
    return pl.DataFrame({
        "symbol": ["600001.SS", "000002.SZ", "300003.SZ", "600004.SS"],
        "name": ["A", "B", "C", "D"],
        "close": [10.0, 20.0, 30.0, 40.0],
        "open": [9.5, 19.0, 29.0, 40.5],
        "change_pct": [0.10, 0.10, 0.06, -0.01],
        "vol_ratio_5d": [2.0, 1.8, 3.0, 0.5],
        "momentum_5d": [0.1, 0.1, 0.05, -0.02],
        "amount": [1e9, 8e8, 5e8, 2e8],
        "ma20": [9.0, 18.0, 28.0, 42.0],
        "signal_ma20_breakdown": [False, False, False, True],
        "signal_limit_up": [True, True, True, False],
        "consecutive_limit_ups": [3, 2, 1, 0],
        "limit_up_broken_count": [0, 1, 0, 0],
    })


@pytest.mark.unit
class TestCNStrategies:
    def _engine(self):
        from dromx.strategy.engine import StrategyEngine
        return StrategyEngine(lambda d: _cn_frame(), [BUILTIN_DIR], market="cn")

    def test_all_four_cn_strategies_loaded(self):
        ids = {s["id"] for s in self._engine().list_strategies()}
        for sid in ("consecutive_limit_ups", "near_limit_up", "limit_up_momentum", "broken_board_recovery"):
            assert sid in ids

    def test_consecutive_limit_ups_hits_multi_board(self):
        r = self._engine().run("consecutive_limit_ups", date(2026, 7, 6), params={"min_boards": 2})
        # Only names with signal_limit_up AND consecutive >= 2 (600001, 000002).
        assert set(r.scores) == {"600001.SS", "000002.SZ"}

    def test_broken_board_recovery_hits_limit_up_with_volume(self):
        r = self._engine().run("broken_board_recovery", date(2026, 7, 6))
        # signal_limit_up & vol_ratio>=1.5 & change_pct>0.03 → 600001,000002,300003.
        assert "600004.SS" not in r.scores  # not a limit-up name
        assert len(r.scores) >= 1
