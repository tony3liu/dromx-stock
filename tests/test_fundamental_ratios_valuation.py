"""Tests for fundamental ratios + valuation models (P0-2 / P0-3)."""

from __future__ import annotations

import pytest

from dromx.dataflows.fundamental_ratios import (
    _get,
    build_fundamental_ratios,
    compute_ratios,
    parse_statement_csv,
)
from dromx.dataflows.valuation import (
    DCFInputs,
    MultipleValuationInputs,
    gordon_ddm,
    h_model_ddm,
    multiple_valuation,
    residual_income_valuation,
    two_stage_dcf,
    two_stage_ddm,
    valuation_summary,
)

_INCOME_EN = """# Income Statement data for AAPL (quarterly)
,2025-06-30,2025-03-31,2024-12-31
Total Revenue,85000000000,82000000000,90000000000
Cost of Revenue,48000000000,46000000000,50000000000
Gross Profit,37000000000,36000000000,40000000000
Operating Income,25000000000,24000000000,26000000000
Net Income,21000000000,20000000000,23000000000
Interest Expense,800000000,750000000,900000000"""

_BALANCE_EN = """# Balance Sheet data for AAPL (quarterly)
,2025-06-30,2025-03-31,2024-12-31
Total Assets,350000000000,340000000000,330000000000
Total Liabilities,250000000000,245000000000,240000000000
Stockholders Equity,100000000000,95000000000,90000000000
Current Assets,140000000000,130000000000,125000000000
Current Liabilities,110000000000,105000000000,100000000000
Cash & Equivalents,25000000000,22000000000,20000000000
Inventory,6000000000,5500000000,5000000000
Accounts Receivable,25000000000,24000000000,23000000000"""

_CASHFLOW_EN = """# Cash Flow data for AAPL (quarterly)
,2025-06-30,2025-03-31,2024-12-31
Operating Cash Flow,30000000000,28000000000,32000000000
CapEx,4000000000,3800000000,4500000000"""

_INCOME_CN = """# 利润表 for 贵州茅台 (600519.SS)
,2025-06-30,2024-12-31
营业总收入,85000000000,90000000000
营业成本,48000000000,50000000000
净利润,21000000000,23000000000"""

_BALANCE_CN = """# 资产负债表 for 贵州茅台 (600519.SS)
,2025-06-30,2024-12-31
资产总计,350000000000,330000000000
负债合计,250000000000,240000000000
股东权益合计,100000000000,90000000000"""


@pytest.mark.unit
class TestStatementParsing:
    def test_parse_english_csv(self):
        df = parse_statement_csv(_INCOME_EN)
        assert len(df) == 6
        assert "Total Revenue" in df.index
        # 数值已转数值类型（可能为 numpy int/float）
        import numpy as np
        assert isinstance(df.loc["Total Revenue"].iloc[0], (int, float, np.integer, np.floating))

    def test_parse_skips_comments(self):
        df = parse_statement_csv(_INCOME_EN)
        assert df.index[0] != "# Income Statement"

    def test_parse_empty(self):
        assert parse_statement_csv("").empty
        assert parse_statement_csv("   \n").empty
        assert parse_statement_csv("Error retrieving balance sheet for X").empty

    def test_get_latest_picks_newest_period(self):
        df = parse_statement_csv(_INCOME_EN)
        # 最新一期 2025-06-30: Revenue=85B
        assert _get(df, "revenue") == 85_000_000_000

    def test_get_latest_works_with_ascending_columns(self):
        # 列升序（最旧在前）也应取最新一期
        csv_asc = (
            "# Income Statement data for AAPL (quarterly)\n",
            ",2024-12-31,2025-03-31,2025-06-30\n",
            "Total Revenue,90000000000,82000000000,85000000000\n",
            "Net Income,23000000000,20000000000,21000000000\n",
        )
        df = parse_statement_csv("".join(csv_asc))
        assert _get(df, "revenue") == 85_000_000_000


@pytest.mark.unit
class TestRatioMath:
    def _ratios(self, income=_INCOME_EN, balance=_BALANCE_EN, cf=_CASHFLOW_EN):
        return compute_ratios(
            parse_statement_csv(income),
            parse_statement_csv(balance),
            parse_statement_csv(cf),
            price=200,
            shares_outstanding=1_500_000_000,
        )

    def test_profitability(self):
        r = self._ratios()
        # 85B rev, 21B NI
        assert r["net_margin"] == pytest.approx(21 / 85, rel=1e-3)
        assert r["gross_margin"] == pytest.approx(37 / 85, rel=1e-3)
        assert r["roe"] == pytest.approx(21 / 100, rel=1e-3)

    def test_dupont_decomposition(self):
        r = self._ratios()
        d = r["dupont"]
        # ROE ≈ 净利率 × 周转 × 乘数
        roe_check = d["net_margin"] * d["asset_turnover"] * d["equity_multiplier"]
        assert roe_check == pytest.approx(r["roe"], rel=1e-3)

    def test_liquidity(self):
        r = self._ratios()
        assert r["current_ratio"] == pytest.approx(140 / 110, rel=1e-3)
        assert r["quick_ratio"] == pytest.approx((140 - 6) / 110, rel=1e-3)

    def test_cashflow_quality(self):
        r = self._ratios()
        assert r["free_cashflow"] == 30_000_000_000 - 4_000_000_000
        assert r["earnings_quality"] == pytest.approx(30 / 21, rel=1e-3)

    def test_valuation_multiple(self):
        r = self._ratios()
        assert r["pe"] == pytest.approx(200 / (21_000_000_000 / 1_500_000_000), rel=1e-3)
        assert r["pb"] == pytest.approx(200 * 1_500_000_000 / 100_000_000_000, rel=1e-3)

    def test_chinese_vendors(self):
        r = self._ratios(income=_INCOME_CN, balance=_BALANCE_CN, cf=None)
        assert r["revenue"] == 85_000_000_000
        assert r["net_income"] == 21_000_000_000
        assert r["roe"] == pytest.approx(21 / 100, rel=1e-3)

    def test_missing_columns_return_none(self):
        r = self._ratios(income=_INCOME_EN, balance=_BALANCE_EN, cf=None)
        assert r["free_cashflow"] is None


@pytest.mark.unit
class TestValuation:
    def test_two_stage_dcf(self):
        res = two_stage_dcf(
            DCFInputs(
                base_fcf=100, years=5, high_growth=0.10, terminal_growth=0.03,
                discount_rate=0.10, net_debt=50, shares_outstanding=10,
            )
        )
        assert res.equity_value > res.pv_fcf  # 含终值
        assert res.per_share is not None and res.per_share > 0
        assert 0 < res.terminal_value_ratio < 1

    def test_dcf_terminal_invalid_growth(self):
        res = two_stage_dcf(
            DCFInputs(base_fcf=100, terminal_growth=0.12, discount_rate=0.10)
        )
        assert res.warnings  # 应有警告

    def test_gordon_ddm(self):
        v = gordon_ddm(3, 0.05, 0.10)
        assert v == pytest.approx(3 * 1.05 / 0.05, rel=1e-3)

    def test_gordon_invalid(self):
        assert gordon_ddm(3, 0.10, 0.05) is None

    def test_two_stage_ddm(self):
        v = two_stage_ddm(3, 0.15, 5, 0.05, 0.10)
        assert v > 3 * 1.05 / 0.05  # 高速增长期会抬升估值

    def test_h_model(self):
        v = h_model_ddm(3, 0.20, 0.05, 10, 0.10)
        assert v is not None and v > gordon_ddm(3, 0.05, 0.10)

    def test_multiples(self):
        r = multiple_valuation(
            MultipleValuationInputs(
                eps=5, pe_target=20, bvps=30, pb_target=3,
                sps=50, ps_target=4,
            )
        )
        assert r["P/E"] == 100
        assert r["P/B"] == 90
        assert r["P/S"] == 200

    def test_residual_income(self):
        v = residual_income_valuation(30, roe=0.15, required_return=0.10, terminal_growth=0.03)
        assert v > 30  # ROE > r → 溢价

    def test_valuation_summary_verdict(self):
        s = valuation_summary(
            price=80, per_share={}, multiple_results={"P/E": 100.0},
            dcf_result=two_stage_dcf(DCFInputs(base_fcf=100, years=5, high_growth=0.1, terminal_growth=0.03, discount_rate=0.1, net_debt=50, shares_outstanding=10)),
        )
        assert "结论" in s and "被低估" in s


@pytest.mark.unit
class TestBuildReport:
    def test_no_data_returns_sentinel(self, monkeypatch):
        from dromx.dataflows import interface

        monkeypatch.setattr(
            interface,
            "route_to_vendor",
            lambda *a, **k: "Error retrieving income statement for X: boom",
        )
        out = build_fundamental_ratios("X", "2026-01-01")
        assert out.startswith("NO_FUNDAMENTAL_DATA")

    def test_build_report_format(self, monkeypatch):
        from dromx.dataflows import interface

        monkeypatch.setattr(interface, "route_to_vendor",
                            lambda method, *a, **k: _INCOME_EN if "income" in method else _BALANCE_EN if "balance" in method else _CASHFLOW_EN)
        out = build_fundamental_ratios("AAPL", "2026-01-01")
        assert "## 盈利能力" in out
        assert "## DuPont" in out
        assert "毛利率" in out
        assert "PE" in out
