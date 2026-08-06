"""Tests for macro cycle phase detection (C1)."""

from __future__ import annotations

import pandas as pd
import pytest

import dromx.dataflows.market_cycles as mc


def _series(values: list[float], freq: str = "MS", periods: int = 36) -> pd.Series:
    """合成带日期索引的序列（近端为最新）。"""
    dates = pd.date_range(end="2026-08-01", periods=periods, freq=freq)
    return pd.Series(values, index=dates)


def _yoy_series(base: float, yoy_pct: float, monthly: float = 0.01) -> pd.Series:
    """构造 12 个月同比 ≈ yoy_pct% 的序列：最新 = base*(1+yoy_pct/100)。"""
    n = 36
    dates = pd.date_range(end="2026-08-01", periods=n, freq="MS")
    # 线性插值：12 个月前 = base，最新 = base*(1+yoy/100)，中间平滑
    start = base
    end = base * (1 + yoy_pct / 100)
    vals = [start + (end - start) * max(0.0, (i - (n - 13))) / 12 for i in range(n)]
    return pd.Series(vals, index=dates)


@pytest.mark.unit
class TestYoY:
    def test_yoy_positive(self):
        s = _yoy_series(100, 5.0)
        assert mc._yoy(s) == pytest.approx(5.0, abs=1.0)

    def test_yoy_none_on_short(self):
        assert mc._yoy(None) is None
        s = _series([1.0], periods=1)
        assert mc._yoy(s) is None

    def test_trend_direction(self):
        rising = _series([10 + i for i in range(36)])
        falling = _series([50 - i for i in range(36)])
        flat = _series([10.0] * 36)
        assert mc._trend(rising) == "rising"
        assert mc._trend(falling) == "falling"
        assert mc._trend(flat) == "flat"


@pytest.mark.unit
class TestPhaseDetection:
    def _detect(self, growth_yoy, cpi_yoy, monkeypatch, gdp_yoy=None,
                curve=None, unemp=None, cpi_trend="flat"):
        def fake_fetch(series_id, curr_date, look_back_days=1100):
            if series_id == "INDPRO":
                return _yoy_series(100, growth_yoy)
            if series_id == "GDPC1":
                return _yoy_series(100, gdp_yoy if gdp_yoy is not None else growth_yoy)
            if series_id == "CPIAUCSL":
                s = _yoy_series(100, cpi_yoy)
                # 覆盖趋势
                if cpi_trend == "rising":
                    s.iloc[-1] = s.iloc[-1] * 1.01
                return s
            if series_id == "T10Y2Y":
                if curve is None:
                    return None
                return _series([curve] * 36)
            if series_id == "UNRATE":
                if unemp is None:
                    return None
                return _series([unemp] * 36)
            return None
        monkeypatch.setattr(mc, "_fetch_fred_series", fake_fetch)
        return mc.detect_cycle_phase("2026-08-06")

    def test_reflation(self, monkeypatch):
        r = self._detect(3.0, 2.0, monkeypatch)
        assert r["phase"] == "reflation"
        assert r["confidence"] >= 0.6

    def test_overheat(self, monkeypatch):
        r = self._detect(3.0, 5.0, monkeypatch, curve=0.5, unemp=4.0)
        assert r["phase"] == "overheat"
        assert r["confidence"] >= 0.7  # 曲线陡峭 + 低失业 → 置信提升

    def test_stagflation(self, monkeypatch):
        r = self._detect(-1.0, 5.0, monkeypatch)
        assert r["phase"] == "stagflation"

    def test_recession(self, monkeypatch):
        r = self._detect(-2.0, 1.0, monkeypatch, curve=-0.5, unemp=6.0)
        assert r["phase"] == "recession"
        assert r["confidence"] >= 0.8  # 倒挂 + 高失业 → 置信大幅提升

    def test_missing_growth_returns_none(self, monkeypatch):
        monkeypatch.setattr(mc, "_fetch_fred_series",
                            lambda sid, cd, lb=1100: _yoy_series(100, 3.0) if sid == "CPIAUCSL" else None)
        r = mc.detect_cycle_phase("2026-08-06")
        assert r["phase"] is None
        assert "增长" in r["reason"]

    def test_missing_inflation_returns_none(self, monkeypatch):
        monkeypatch.setattr(mc, "_fetch_fred_series",
                            lambda sid, cd, lb=1100: _yoy_series(100, 3.0) if sid in ("INDPRO", "GDPC1") else None)
        r = mc.detect_cycle_phase("2026-08-06")
        assert r["phase"] is None
        assert "通胀" in r["reason"]

    def test_phase_meta_has_sector_advice(self, monkeypatch):
        r = self._detect(3.0, 2.0, monkeypatch)
        assert r["sectors_favor"]
        assert r["sectors_avoid"]
        assert r["equity_strategy"]
        assert r["risk"]


@pytest.mark.unit
class TestBuildReport:
    def test_report_format(self, monkeypatch):
        monkeypatch.setattr(mc, "detect_cycle_phase", lambda d: {
            "phase": "reflation", "phase_cn": "复苏", "phase_label": "复苏 (Reflation)",
            "confidence": 0.7, "regime": "x", "assets": "y",
            "sectors_favor": ["科技"], "sectors_avoid": ["公用"],
            "equity_strategy": "z", "risk": "中",
            "evidence_notes": ["n1"], "raw_indicators": {
                "industrial_production_yoy_pct": 3.0, "gdp_yoy_pct": 2.0,
                "cpi_yoy_pct": 2.0, "inflation_trend": "flat",
                "curve_10y2y": 0.4, "unemployment_pct": 4.0,
            }})
        out = mc.build_cycle_report("2026-08-06")
        assert "复苏" in out
        assert "置信度 70%" in out
        assert "科技" in out

    def test_unavailable_report(self, monkeypatch):
        monkeypatch.setattr(mc, "detect_cycle_phase",
                            lambda d: {"phase": None, "reason": "无法取得增长数据"})
        out = mc.build_cycle_report("2026-08-06")
        assert out.startswith("MACRO_CYCLE_UNAVAILABLE")
        assert "不要臆测" in out
