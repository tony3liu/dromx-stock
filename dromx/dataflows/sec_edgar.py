"""SEC EDGAR financial statements (official, free, keyless).

The U.S. Securities and Exchange Commission publishes every public company's
financial statements as machine-readable XBRL via the data.sec.gov API. No API
key is required; the only obligation is a descriptive User-Agent. This is the
authoritative, point-in-time source for US-listed balance sheets, income
statements, and cash-flow statements — strictly better than scraping, and
immune to the rate-limiting that took Yahoo Finance offline here.

Endpoints used:
  * Ticker -> CIK map:  https://www.sec.gov/files/company_tickers.json
  * All facts for CIK:  https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json

Each XBRL concept yields dated data points (``end``/``val``/``form``/``fy``/
``fp``). We filter to points filed on or before ``curr_date`` to prevent
look-ahead bias in backtests, then render the most recent periods as a table
matching the other vendors' CSV-ish output.

Coverage is US filers only. Non-US symbols raise ``NoMarketDataError`` so the
router falls back to the next configured vendor (e.g. Tencent's overview).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import pandas as pd
import requests

from .errors import NoMarketDataError, VendorNotConfiguredError, VendorRateLimitError

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
# SEC asks for a descriptive UA identifying the caller; they 403 generic ones.
_HEADERS = {"User-Agent": "TradingAgents/1.0 (research; contact@tradingagents.local)"}
_TIMEOUT = 25

# Per-process caches: the ticker map is ~800KB and facts are large, so avoid
# refetching within a run.
_CIK_MAP: dict[str, str] | None = None
_FACTS_CACHE: dict[str, dict] = {}

# XBRL concepts grouped by statement. Several concepts are listed per line item
# because filers tag the same economic value under different (often
# version-dependent) US-GAAP tags; the first one present wins.
_BALANCE_SHEET = [
    ("Total Assets", ["Assets"]),
    ("Total Liabilities", ["Liabilities"]),
    ("Stockholders Equity", ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
    ("Cash & Equivalents", ["CashAndCashEquivalentsAtCarryingValue"]),
    ("Current Assets", ["AssetsCurrent"]),
    ("Current Liabilities", ["LiabilitiesCurrent"]),
    ("Long-Term Debt", ["LongTermDebtNoncurrent", "LongTermDebt"]),
    ("Inventory", ["InventoryNet"]),
]
_INCOME_STMT = [
    ("Revenue", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]),
    ("Cost of Revenue", ["CostOfRevenue", "CostOfGoodsAndServicesSold"]),
    ("Gross Profit", ["GrossProfit"]),
    ("Operating Income", ["OperatingIncomeLoss"]),
    ("Net Income", ["NetIncomeLoss"]),
    ("R&D Expense", ["ResearchAndDevelopmentExpense"]),
    ("EPS (Diluted)", ["EarningsPerShareDiluted"]),
]
_CASH_FLOW = [
    ("Operating Cash Flow", ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]),
    ("Investing Cash Flow", ["NetCashProvidedByUsedInInvestingActivities", "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"]),
    ("Financing Cash Flow", ["NetCashProvidedByUsedInFinancingActivities", "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"]),
    ("CapEx", ["PaymentsToAcquirePropertyPlantAndEquipment"]),
    ("Depreciation & Amort.", ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet"]),
]

# Number of most-recent reporting periods to render per statement.
_MAX_PERIODS = 6


def _http_json(url: str) -> dict:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise VendorRateLimitError(f"SEC request failed: {exc}") from exc
    if resp.status_code == 429:
        raise VendorRateLimitError("SEC rate limited (HTTP 429)")
    resp.raise_for_status()
    return resp.json()


def _load_cik_map() -> dict[str, str]:
    global _CIK_MAP
    if _CIK_MAP is None:
        data = _http_json(_TICKERS_URL)
        # Map upper-cased ticker -> 10-digit zero-padded CIK.
        _CIK_MAP = {
            row["ticker"].upper(): str(row["cik_str"]).zfill(10)
            for row in data.values()
        }
    return _CIK_MAP


def _resolve_cik(ticker: str) -> str:
    # SEC covers US filers only; reject obvious non-US/derived symbols early so
    # the router falls back to another vendor instead of erroring on a 404.
    t = ticker.strip().upper()
    if not t.isalpha():
        raise NoMarketDataError(ticker, ticker, "SEC EDGAR covers US-listed equities only")
    cik = _load_cik_map().get(t)
    if not cik:
        raise NoMarketDataError(ticker, ticker, "ticker not found in SEC EDGAR registry")
    return cik


def _load_facts(ticker: str) -> dict:
    cik = _resolve_cik(ticker)
    if cik not in _FACTS_CACHE:
        facts = _http_json(_FACTS_URL.format(cik=cik))
        _FACTS_CACHE[cik] = facts
    return _FACTS_CACHE[cik]


def _series_for(
    gaap: dict,
    concepts: list[str],
    cutoff: pd.Timestamp,
    span_mode: str = "quarter",
) -> dict[str, float]:
    """Return {period_end -> value} merged across candidate concepts.

    Only data points *filed on or before* ``cutoff`` are kept (look-ahead
    safety). Period end date is the column key.

    Duration concepts report both a quarterly value and an annual value under
    the SAME end date; mixing them misaligns columns and double-counts.
    ``span_mode`` controls which duration spans are kept:
      * "quarter" — only ~quarterly spans (80-100 days). Used for income-
        statement lines, which filers report per discrete quarter.
      * "any"     — keep all spans. Used for cash-flow lines, which NVDA (and
        many filers) report as YTD cumulative figures (Q1≈90d, H1≈181d,
        9M≈272d, FY≈363d); restricting to 90 days would drop most columns.
    Instant concepts (balance sheet) have no ``start`` and are always kept.
    The most recently filed value for an end date wins (captures restatements).

    Concepts are MERGED, not first-wins: filers migrate the same line item
    across US-GAAP tags over time (e.g. NVDA's revenue moved between
    ``Revenues`` and ``RevenueFromContractWithCustomerExcludingAssessedTax``),
    so a single tag covers only part of the history. We union all candidate
    tags and let the most-recently-filed value win per end date.
    """
    chosen: dict[str, tuple[str, float]] = {}
    for concept in concepts:
        node = gaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        # Most concepts are USD; EPS is USD/shares.
        points = units.get("USD") or units.get("USD/shares") or next(iter(units.values()), [])
        for p in points:
            end = p.get("end")
            filed = p.get("filed")
            val = p.get("val")
            if end is None or val is None or filed is None:
                continue
            if pd.to_datetime(filed) > cutoff:
                continue  # not yet public as of curr_date
            # For duration facts in "quarter" mode, keep only ~quarterly spans
            # so quarterly and annual figures never share a column.
            start = p.get("start")
            if start is not None and span_mode == "quarter":
                span_days = (pd.to_datetime(end) - pd.to_datetime(start)).days
                if not (80 <= span_days <= 100):
                    continue
            prev = chosen.get(end)
            if prev is None or filed > prev[0]:
                chosen[end] = (filed, val)
    return {end: v for end, (_f, v) in chosen.items()}


def _build_statement(
    ticker: str, line_items, curr_date: str | None, title: str, span_mode: str = "quarter"
) -> str:
    facts = _load_facts(ticker)
    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        raise NoMarketDataError(ticker, ticker, "no US-GAAP facts in SEC data")

    cutoff = pd.to_datetime(curr_date) if curr_date else pd.Timestamp.today()

    # Collect each line item's period->value series.
    rows: dict[str, dict[str, float]] = {}
    all_periods: set[str] = set()
    for label, concepts in line_items:
        series = _series_for(gaap, concepts, cutoff, span_mode=span_mode)
        if series:
            rows[label] = series
            all_periods.update(series.keys())

    if not rows:
        raise NoMarketDataError(ticker, ticker, f"no {title} data on/before {cutoff.date()}")

    # Most recent N period-end columns.
    periods = sorted(all_periods, reverse=True)[:_MAX_PERIODS]

    df = pd.DataFrame(index=[lbl for lbl, _ in line_items if lbl in rows], columns=periods)
    for label in df.index:
        for period in periods:
            val = rows[label].get(period)
            df.at[label, period] = val if val is not None else ""

    entity = facts.get("entityName", ticker)
    header = f"# {title} for {entity} ({ticker})\n"
    header += f"# Periods shown (most recent first), as filed on/before {cutoff.date()}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: SEC EDGAR (data.sec.gov), values in USD\n\n"
    return header + df.to_csv()


# --- Public vendor API (mirrors y_finance signatures) ----------------------


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; SEC returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, _BALANCE_SHEET, curr_date, "Balance Sheet")


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; SEC returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, _INCOME_STMT, curr_date, "Income Statement")


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; SEC returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(
        ticker,
        _CASH_FLOW,
        curr_date,
        "Cash Flow Statement (YTD cumulative per fiscal year)",
        span_mode="any",
    )


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Fundamentals overview assembled from the latest SEC statement lines."""
    facts = _load_facts(ticker)
    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        raise NoMarketDataError(ticker, ticker, "no US-GAAP facts in SEC data")

    cutoff = pd.to_datetime(curr_date) if curr_date else pd.Timestamp.today()
    overview = [
        ("Revenue", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]),
        ("Net Income", ["NetIncomeLoss"]),
        ("Gross Profit", ["GrossProfit"]),
        ("Operating Income", ["OperatingIncomeLoss"]),
        ("Total Assets", ["Assets"]),
        ("Total Liabilities", ["Liabilities"]),
        ("Stockholders Equity", ["StockholdersEquity"]),
        ("Cash & Equivalents", ["CashAndCashEquivalentsAtCarryingValue"]),
        ("Operating Cash Flow", ["NetCashProvidedByUsedInOperatingActivities"]),
        ("EPS (Diluted)", ["EarningsPerShareDiluted"]),
    ]

    lines = []
    for label, concepts in overview:
        series = _series_for(gaap, concepts, cutoff)
        if series:
            latest_end = max(series.keys())
            lines.append(f"{label}: {series[latest_end]} (period ending {latest_end})")

    if not lines:
        raise NoMarketDataError(ticker, ticker, f"no fundamentals on/before {cutoff.date()}")

    entity = facts.get("entityName", ticker)
    header = f"# Company Fundamentals for {entity} ({ticker})\n"
    header += f"# Latest reported values filed on/before {cutoff.date()}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: SEC EDGAR (data.sec.gov), values in USD\n\n"
    return header + "\n".join(lines)


def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol of the company"],
):
    """SEC Form 4 insider data needs separate parsing; not implemented here."""
    raise VendorNotConfiguredError(
        "SEC insider-transaction parsing (Form 4) is not implemented in this vendor"
    )
