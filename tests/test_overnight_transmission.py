"""Tests for the overnight transmission builder.

The builder is pure deterministic math over a resolved ETF structure + one LLM
transmission-link judgement. These tests mock both (plus the OHLCV fetchers) so
they run offline and exercise the render + degradation logic only.
"""

from __future__ import annotations

import tradingagents.dataflows.overnight_transmission as ot
from tradingagents.dataflows.overnight_transmission import build_overnight_transmission


class _FakeStructure:
    """Stand-in for ``etf_data.ETFStructure`` with the fields the builder reads."""

    def __init__(self, **kw):
        self.is_etf = kw.get("is_etf", True)
        self.leverage = kw.get("leverage", 2.0)
        self.direction = kw.get("direction", "long")
        self.underlying_name = kw.get("underlying_name", "SK Hynix")
        self.underlying_proxy = kw.get("underlying_proxy", "000660.KS")
        self.underlying_market = kw.get("underlying_market", "Korea")
        self.listing_currency = kw.get("listing_currency", "HKD")
        self.underlying_currency = kw.get("underlying_currency", "KRW")
        self.confidence = kw.get("confidence", "medium")


def _patch(monkeypatch, *, structure=None, link=None, und_1d=None,
           ref_1d=None, prev_close=None):
    """Replace every network/LLM touchpoint in the builder with fixed values."""
    import tradingagents.dataflows.etf_data as etf_data

    if structure is not None:
        monkeypatch.setattr(etf_data, "resolve_etf_structure",
                            lambda *a, **k: structure)
    if link is not None:
        monkeypatch.setattr(ot, "_resolve_transmission_link",
                            lambda *a, **k: link)
    monkeypatch.setattr(ot, "_underlying_returns_1d", lambda *a, **k: und_1d)
    monkeypatch.setattr(ot, "_returns_1d", lambda *a, **k: ref_1d)
    monkeypatch.setattr(ot, "_last_close", lambda *a, **k: prev_close)


def test_non_etf_returns_empty(monkeypatch):
    """A plain stock is out of P0 scope → no segment at all."""
    _patch(monkeypatch, structure=_FakeStructure(is_etf=False))
    assert build_overnight_transmission("AAPL", "2026-07-07") == ""


def test_same_market_etf_returns_empty(monkeypatch):
    """An LLM 'no cross-market link' verdict (e.g. HK tracking HSI) → ''."""
    struct = _FakeStructure(underlying_market="Hong Kong")
    link = {"has_cross_market_transmission": False,
            "overnight_ref_proxy": None,
            "reason": "same-market ETF, no lead"}
    _patch(monkeypatch, structure=struct, link=link)
    assert build_overnight_transmission("02800.HK", "2026-07-07") == ""


def test_full_chain_computes_open_price(monkeypatch):
    """2x SK Hynix ETF: -3.84% × 2 = -7.68% → 116.80 × 0.9232 ≈ 107.83."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS",
                            underlying_name="SK Hynix")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU",
            "reason": "HK-listed 2x Korea-semis, Seoul leads HK"}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=-3.84, ref_1d=0.96, prev_close=116.80)
    out = build_overnight_transmission("07709.HK", "2026-07-07")

    assert "隔夜传导" in out
    assert "000660.KS" in out
    assert "116.80" in out
    assert "107.83" in out  # leverage-derived expected open
    # MU +0.96% vs SK Hynix -3.84% → opposite directions → broken
    assert "⚠️ 传导断裂" in out


def test_transmission_intact_when_same_direction(monkeypatch):
    """Lead and underlying both up → transmission intact."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=3.0, ref_1d=2.5, prev_close=100.0)
    out = build_overnight_transmission("07709.HK", "2026-07-07")
    assert "✅ 传导正常" in out


def test_no_underlying_proxy_returns_empty(monkeypatch):
    """LLM judged a link exists but no loadable underlying symbol → honest ''."""
    struct = _FakeStructure(underlying_proxy=None)
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link)
    assert build_overnight_transmission("07709.HK", "2026-07-07") == ""


def test_underlying_return_unavailable_degrades(monkeypatch):
    """Underlying OHLCV fetch failed → 'n/a', no open price, no verdict."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=None, ref_1d=0.96, prev_close=116.80)
    out = build_overnight_transmission("07709.HK", "2026-07-07")
    assert "n/a" in out
    assert "107.83" not in out
    assert "传导状态" not in out  # can't verdict without the underlying move


def test_holdings_fallback_for_lead_reference(monkeypatch):
    """LLM gave no lead ref; a cross-market holding (MU) is used as fallback."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": None, "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=-3.84, ref_1d=0.96, prev_close=116.80)
    out = build_overnight_transmission(
        "07709.HK", "2026-07-07", config={"holdings": ["MU"]}
    )
    assert "MU" in out
    assert "⚠️ 传导断裂" in out


def test_etf_underlying_map_override(monkeypatch):
    """Manual override fills a missing underlying_proxy → open price computed."""
    struct = _FakeStructure(underlying_proxy=None)  # LLM failed to resolve
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=-3.84, ref_1d=0.96, prev_close=116.80)
    config = {"etf_underlying_map": {
        "07709.HK": {"underlying": "000660.KS", "currency": "KRW"}}}
    out = build_overnight_transmission("07709.HK", "2026-07-07", config=config)
    assert "000660.KS" in out
    assert "107.83" in out


def test_inverse_etf_direction_sign(monkeypatch):
    """An inverse ETF: underlying up → the wrapper down."""
    struct = _FakeStructure(leverage=2.0, direction="inverse",
                            underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=3.0, ref_1d=2.5, prev_close=100.0)
    out = build_overnight_transmission("07709.HK", "2026-07-07")
    # underlying +3% × 2x inverse = -6% → 100 × 0.94 = 94.00
    assert "94.00" in out
    assert "反向" in out


def test_reporting_includes_overnight_section(tmp_path):
    """The report tree renders the 0.7 section + drops a standalone .md."""
    from tradingagents.reporting import write_report_tree

    final_state = {
        "overnight_transmission": "## 隔夜传导\n- test chain content\n",
    }
    out = write_report_tree(final_state, "07709.HK", tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "## 隔夜传导" in text
    assert "test chain content" in text
    assert (tmp_path / "0_regime" / "overnight_transmission.md").exists()


def test_reporting_omits_section_when_empty(tmp_path):
    """No overnight_transmission in state → no section, no file (additive)."""
    from tradingagents.reporting import write_report_tree

    out = write_report_tree({}, "AAPL", tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "隔夜传导" not in text
    assert not (tmp_path / "0_regime" / "overnight_transmission.md").exists()


def test_overnight_reference_intraday_and_reversal(monkeypatch):
    """The reference line shows OHLC + flags a bearish intraday reversal."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=0.96, ref_1d=0.96, prev_close=116.80)
    # MU: open 1007, high 1019, low 980.85, close 984.75 → gave back hard
    monkeypatch.setattr(ot, "_ohlc_row",
                        lambda *a, **k: (1007.0, 1019.0, 980.85, 984.75))
    out = build_overnight_transmission("07709.HK", "2026-07-07")
    assert "开 1007.00" in out
    assert "高 1019.00" in out
    assert "低 980.85" in out
    assert "收 984.75" in out
    assert "⚠️反转" in out


def test_no_reversal_when_close_strong(monkeypatch):
    """Close near the high → no reversal flag."""
    struct = _FakeStructure(leverage=2.0, underlying_proxy="000660.KS")
    link = {"has_cross_market_transmission": True,
            "overnight_ref_proxy": "MU", "reason": "..."}
    _patch(monkeypatch, structure=struct, link=link,
           und_1d=2.0, ref_1d=2.5, prev_close=100.0)
    monkeypatch.setattr(ot, "_ohlc_row",
                        lambda *a, **k: (100.0, 105.0, 99.0, 104.0))
    out = build_overnight_transmission("07709.HK", "2026-07-07")
    assert "⚠️反转" not in out


def test_premarket_call_card_extracts_overnight_and_decision():
    from tradingagents.reporting import _premarket_call_card

    state = {
        "overnight_transmission": (
            "## 隔夜传导\n"
            "- **结构:** 2x long tracking SK Hynix（underlying_proxy=000660.KS）\n"
            "- **期望开盘:** 前收 116.80 × ... ≈ **107.83**（-7.68%）\n"
            "- **传导状态:** ⚠️ 传导断裂 —— 背离\n"
        ),
        "final_trade_decision": "## 决策：买入\n详细理由...",
    }
    card = _premarket_call_card(state)
    assert "盘前 Call" in card
    assert "107.83" in card
    assert "传导断裂" in card
    assert "决策" in card
    assert "买入" in card


def test_premarket_call_card_empty_when_nothing():
    from tradingagents.reporting import _premarket_call_card
    assert _premarket_call_card({}) == ""


def test_reporting_premarket_card_sits_at_top(tmp_path):
    """The card sits above the regime section in the consolidated report."""
    from tradingagents.reporting import write_report_tree

    final_state = {
        "regime_report": "**市场状态：** Uptrend",
        "overnight_transmission": (
            "- **期望开盘:** ≈ **107.83**\n"
            "- **传导状态:** ⚠️ 传导断裂\n"
        ),
    }
    out = write_report_tree(final_state, "07709.HK", tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "盘前 Call" in text
    assert text.index("盘前 Call") < text.index("市场状态")
