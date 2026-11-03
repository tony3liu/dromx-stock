"""Tests for the Naver foreign-flow (chip) builder.

Direction-correct: the consecutive run is counted from the NEWEST day
(Naver table is newest-first), so a tape that flipped to buy today shows zero
consecutive-sell days even if the prior 22 were all sells.
"""

from __future__ import annotations

import dromx.dataflows.naver as nv
from dromx.dataflows.naver import build_foreign_flow


_HTML = """
<html><body>
<table>
<tr><th>날짜</th><th>종가</th><th>전일비</th><th>외국인</th><th>기관</th></tr>
<tr><td>07/08</td><td>2,076,000</td><td>하향125,000</td><td>+88,312</td><td>-285,353</td></tr>
<tr><td>07/07</td><td>2,201,000</td><td>하향142,000</td><td>-542,009</td><td>-23,811</td></tr>
</table>
<table>
<tr><th>외국인비율(%)</th><td>50.05</td><td>46.55</td></tr>
</table>
</body></html>
"""


def test_kr_code():
    assert nv._kr_code("000660.KS") == "000660"
    assert nv._kr_code("000660.KQ") == "000660"
    assert nv._kr_code("AAPL") is None
    assert nv._kr_code("07709.HK") is None


def test_parse_ownership_pct():
    assert nv._parse_ownership_pct(_HTML) == 50.05


def test_parse_daily_net():
    assert nv._parse_daily_net(_HTML) == [("07/08", 88312), ("07/07", -542009)]


def test_consecutive_run_helper():
    # newest-first: the run is counted from daily[0]
    assert nv._consecutive_run([("a", -1), ("b", -1), ("c", -1)]) == ("sell", 3)
    assert nv._consecutive_run([("a", 1), ("b", 1)]) == ("buy", 2)
    assert nv._consecutive_run([("a", -1), ("b", 1)]) == ("sell", 1)  # flipped at b
    assert nv._consecutive_run([("a", 1), ("b", -1)]) == ("buy", 1)  # flipped at b
    assert nv._consecutive_run([]) == ("flat", 0)


def test_build_consecutive_sell(monkeypatch):
    """23 newest-first days all net-sell → ⚠️ outflow + 23 days."""
    daily = [(f"07/{i:02d}", -1000) for i in range(23, 0, -1)]
    monkeypatch.setattr(nv, "fetch_foreign_trading",
                        lambda *a, **k: {"foreign_ownership_pct": 50.06, "daily_net": daily})
    out = build_foreign_flow("000660.KS", "2026-07-08")
    assert "外资筹码" in out
    assert "50.06%" in out
    assert "连续净卖天数:** 23 日" in out
    assert "⚠️ 外资持续流出" in out


def test_build_consecutive_buy(monkeypatch):
    daily = [(f"07/{i:02d}", 1000) for i in range(10, 0, -1)]
    monkeypatch.setattr(nv, "fetch_foreign_trading",
                        lambda *a, **k: {"foreign_ownership_pct": 51.0, "daily_net": daily})
    out = build_foreign_flow("000660.KS", "2026-07-08")
    assert "连续净买天数:** 10 日" in out
    assert "⚠️ 外资持续流入" in out


def test_build_flip_today_breaks_run(monkeypatch):
    """22 sell days then today flips to buy → 0 consecutive-sell (run broke)."""
    daily = [("07/08", +500)] + [(f"07/{i:02d}", -1000) for i in range(7, 0, -1)]
    monkeypatch.setattr(nv, "fetch_foreign_trading",
                        lambda *a, **k: {"foreign_ownership_pct": 50.0, "daily_net": daily})
    out = build_foreign_flow("000660.KS", "2026-07-08")
    # today is buy, run of sells is broken — no outflow flag
    assert "⚠️ 外资持续流出" not in out


def test_build_non_kr_returns_empty(monkeypatch):
    monkeypatch.setattr(nv, "fetch_foreign_trading", lambda *a, **k: None)
    assert build_foreign_flow("AAPL", "2026-07-08") == ""
    assert build_foreign_flow("07709.HK", "2026-07-08") == ""


def test_build_fetch_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(nv, "fetch_foreign_trading", lambda *a, **k: None)
    assert build_foreign_flow("000660.KS", "2026-07-08") == ""


def test_build_no_consecutive_no_flag(monkeypatch):
    daily = [("07/08", +1000), ("07/07", -1000), ("07/06", +1000), ("07/05", -1000),
             ("07/04", +1000), ("07/03", -1000)]  # alternating, newest-first
    monkeypatch.setattr(nv, "fetch_foreign_trading",
                        lambda *a, **k: {"foreign_ownership_pct": 50.0, "daily_net": daily})
    out = build_foreign_flow("000660.KS", "2026-07-08")
    assert "⚠️" not in out
    assert "连续" not in out  # no run ≥2 (alternating)
