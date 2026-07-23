"""Eastmoney (datacenter) financial statements for US & HK equities.

Eastmoney's public datacenter API exposes US/HK balance sheets, income
statements, and cash-flow statements (Chinese line-item names) plus a key-
indicator overview (GMAININDICATOR), all keyless. It fills two gaps the other
vendors leave open:

  * SEC EDGAR covers US filers only — HK equities have no statement source.
  * Tencent only has a current-snapshot overview, not the three statements.

Source: adapted from the verified functions in the ``global-stock-data`` skill
(https://github.com/simonlin1212/global-stock-data), §4.1 (financial_statements
_eastmoney) and §4.2 (key_indicators_eastmoney).

SECUCODE format Eastmoney expects:
  * US NASDAQ:  ``AAPL.O``
  * US NYSE:    ``BABA.N``
  * HK:         ``00700.HK``

We resolve the user's symbol to a SECUCODE, query the matching report, group the
flat ITEM_NAME rows back into per-period columns, filter to periods reported on
or before ``curr_date`` (look-ahead safety, mirroring sec_edgar.py), and render
a CSV table with the same header-comment shape as the other vendors.

All Eastmoney requests go through the shared throttle ``em_get`` (serial, ≥1s
spacing + jitter, Keep-Alive session) because Eastmoney rate-limits aggressive
callers — the skill documents temporary IP bans above ~5 req/s.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from typing import Annotated

import pandas as pd
import requests

from .errors import NoMarketDataError, VendorRateLimitError

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_TIMEOUT = 20

# Eastmoney anti-ban throttle: one shared Keep-Alive session, serial requests
# with a minimum interval + jitter. The skill measured temporary IP bans past
# ~5 req/s; ≥1s spacing keeps us comfortably under that.
_EM_SESSION = requests.Session()
_EM_SESSION.headers.update({"User-Agent": _UA})
_EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]

# Statement -> report-name per market. Note Eastmoney's own naming is
# inconsistent (balance/income use F10, cashflow uses SK).
_REPORT_MAP = {
    "balance": {"us": "RPT_USF10_FN_BALANCE", "hk": "RPT_HKF10_FN_BALANCE"},
    "income": {"us": "RPT_USF10_FN_INCOME", "hk": "RPT_HKF10_FN_INCOME"},
    "cashflow": {"us": "RPT_USSK_FN_CASHFLOW", "hk": "RPT_HKSK_FN_CASHFLOW"},
}
_GMAIN_REPORT = {"us": "RPT_USF10_FN_GMAININDICATOR", "hk": "RPT_HKF10_FN_GMAININDICATOR"}

# Number of most-recent reporting periods to render per statement.
_MAX_PERIODS = 6
# Key-indicator fields worth surfacing in the fundamentals overview, in order.
# Field set is the US/HK common core documented in the skill (§4.2).
_OVERVIEW_FIELDS = [
    ("Revenue", "OPERATE_INCOME"),
    ("Gross Profit", "GROSS_PROFIT"),
    ("Gross Margin %", "GROSS_PROFIT_RATIO"),
    ("Net Income (parent)", "PARENT_HOLDER_NETPROFIT"),
    ("Net Margin %", "NET_PROFIT_RATIO"),
    ("Basic EPS", "BASIC_EPS"),
    ("Diluted EPS", "DILUTED_EPS"),
    ("ROE (avg) %", "ROE_AVG"),
    ("ROA %", "ROA"),
    ("Debt/Asset %", "DEBT_ASSET_RATIO"),
    ("Current Ratio", "CURRENT_RATIO"),
    ("Revenue YoY %", "OPERATE_INCOME_YOY"),
    ("EPS YoY %", "BASIC_EPS_YOY"),
]


def _em_get(url: str, params: dict) -> requests.Response:
    """Throttled Eastmoney GET: serial, ≥1s spacing + jitter, shared session."""
    wait = _EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return _EM_SESSION.get(url, params=params, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise VendorRateLimitError(f"Eastmoney request failed: {exc}") from exc
    finally:
        _em_last_call[0] = time.time()


def _datacenter(report_name: str, secucode: str, page_size: int = 200) -> list[dict]:
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }
    r = _em_get(_DATACENTER_URL, params)
    if r.status_code == 429:
        raise VendorRateLimitError("Eastmoney rate limited (HTTP 429)")
    try:
        d = r.json()
    except ValueError as exc:
        raise VendorRateLimitError(f"Eastmoney non-JSON response: {exc}") from exc
    result = d.get("result")
    if result and result.get("data"):
        return result["data"]
    return []


def _to_secucode(symbol: str) -> tuple[str, str]:
    """Resolve a user symbol to (market, SECUCODE).

    market is "us" or "hk". Accepts:
      * AAPL / AAPL.O / AAPL.OQ / AAPL.N           -> us
      * 00700.HK / 0700.HK / HK00700 / bare 5-digit -> hk
    Anything that can't be mapped to a US/HK SECUCODE raises NoMarketDataError
    so the router falls back to the next vendor.
    """
    s = symbol.strip().upper()

    # Hong Kong: explicit .HK suffix, HK prefix, or a bare numeric code.
    base = None
    if s.endswith(".HK"):
        base = s[:-3]
    elif s.startswith("HK") and s[2:].isdigit():
        base = s[2:]
    elif s.isdigit():
        base = s
    if base is not None and base.isdigit():
        return "hk", f"{base.zfill(5)}.HK"

    # US: strip any exchange suffix, classify NASDAQ (.O) vs NYSE (.N).
    if "." in s:
        ticker, _, suffix = s.rpartition(".")
        if ticker and ticker.isalpha():
            mkt_suffix = ".N" if suffix.startswith("N") else ".O"
            return "us", f"{ticker}{mkt_suffix}"
    if s.isalpha():
        # Default US tickers to NASDAQ (.O); if Eastmoney returns nothing the
        # caller retries via the .N path below in _query_statement.
        return "us", f"{s}.O"

    raise NoMarketDataError(symbol, symbol, "not a recognized US/HK symbol for Eastmoney")


def _candidate_secucodes(symbol: str) -> tuple[str, list[str]]:
    """Return (market, [secucode candidates]).

    For bare US tickers we try NASDAQ (.O) then NYSE (.N), since we can't know
    the listing exchange up front and Eastmoney keys strictly on the suffix.
    """
    market, secucode = _to_secucode(symbol)
    if market == "us" and secucode.endswith(".O") and "." in symbol.strip():
        # Caller gave an explicit suffix; trust it, don't guess the other board.
        return market, [secucode]
    if market == "us":
        ticker = secucode.rsplit(".", 1)[0]
        return market, [f"{ticker}.O", f"{ticker}.N"]
    return market, [secucode]


def _period_label(row: dict) -> str | None:
    """Period-end date (YYYY-MM-DD) from a datacenter row's REPORT_DATE."""
    raw = row.get("REPORT_DATE")
    if not raw:
        return None
    ts = pd.to_datetime(str(raw).split()[0], errors="coerce")
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def _query_statement(symbol: str, report_key: str, curr_date: str | None) -> tuple[str, list[dict]]:
    """Return (secucode_used, rows) for the given statement, trying US boards."""
    market, candidates = _candidate_secucodes(symbol)
    report_name = _REPORT_MAP[report_key][market]
    last_secucode = candidates[0]
    for secucode in candidates:
        rows = _datacenter(report_name, secucode)
        if rows:
            return secucode, rows
        last_secucode = secucode
    raise NoMarketDataError(symbol, last_secucode, f"no {report_key} rows from Eastmoney")


def _build_statement(symbol: str, report_key: str, curr_date: str | None, title: str) -> str:
    secucode, rows = _query_statement(symbol, report_key, curr_date)

    cutoff = pd.to_datetime(curr_date) if curr_date else pd.Timestamp.today()

    # Group the flat ITEM_NAME rows into {item -> {period -> amount}}.
    by_item: dict[str, dict[str, float]] = {}
    item_order: list[str] = []
    all_periods: set[str] = set()
    for row in rows:
        period = _period_label(row)
        if period is None or pd.to_datetime(period) > cutoff:
            continue  # not yet reported as of curr_date (look-ahead safety)
        name = row.get("ITEM_NAME")
        amount = row.get("AMOUNT")
        if not name or amount is None:
            continue
        if name not in by_item:
            by_item[name] = {}
            item_order.append(name)
        by_item[name][period] = amount
        all_periods.add(period)

    if not by_item:
        raise NoMarketDataError(symbol, secucode, f"no {report_key} data on/before {cutoff.date()}")

    periods = sorted(all_periods, reverse=True)[:_MAX_PERIODS]
    df = pd.DataFrame(index=item_order, columns=periods)
    for name in item_order:
        for period in periods:
            df.at[name, period] = by_item[name].get(period, "")

    name_abbr = rows[0].get("SECURITY_NAME_ABBR", symbol) if rows else symbol
    currency = rows[0].get("CURRENCY", "") if rows else ""
    header = f"# {title} for {name_abbr} ({secucode})\n"
    header += f"# Periods shown (most recent first), reported on/before {cutoff.date()}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += f"# Source: Eastmoney datacenter, line items in Chinese, currency: {currency or 'native'}\n\n"
    return header + df.to_csv()


# --- Public vendor API (mirrors sec_edgar / y_finance signatures) ----------


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Eastmoney returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "balance", curr_date, "Balance Sheet")


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Eastmoney returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "income", curr_date, "Income Statement")


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Eastmoney returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "cashflow", curr_date, "Cash Flow Statement")


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """Key-indicator overview from Eastmoney's GMAININDICATOR report."""
    market, candidates = _candidate_secucodes(ticker)
    report_name = _GMAIN_REPORT[market]

    rows: list[dict] = []
    secucode_used = candidates[0]
    for secucode in candidates:
        rows = _datacenter(report_name, secucode, page_size=8)
        if rows:
            secucode_used = secucode
            break

    cutoff = pd.to_datetime(curr_date) if curr_date else pd.Timestamp.today()
    rows = [r for r in rows if (_period_label(r) and pd.to_datetime(_period_label(r)) <= cutoff)]
    if not rows:
        raise NoMarketDataError(ticker, secucode_used, f"no fundamentals on/before {cutoff.date()}")

    latest = rows[0]
    period = _period_label(latest)
    lines = [f"{label}: {latest.get(key)}" for label, key in _OVERVIEW_FIELDS if latest.get(key) is not None]
    if not lines:
        raise NoMarketDataError(ticker, secucode_used, "Eastmoney returned no usable indicator fields")

    name_abbr = latest.get("SECURITY_NAME_ABBR", ticker)
    header = f"# Company Fundamentals for {name_abbr} ({secucode_used})\n"
    header += f"# Latest key indicators for period ending {period} (on/before {cutoff.date()})\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: Eastmoney datacenter GMAININDICATOR\n\n"
    return header + "\n".join(lines)
