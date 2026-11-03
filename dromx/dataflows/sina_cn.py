"""Sina Finance A-share financial statements (balance / income / cash flow).

Sina's openapi exposes A-share three-statement data keyed by report period,
keyless. It fills the gap left by the other A-share sources: Tencent has only a
current snapshot, SEC EDGAR is US-only, and Eastmoney's three-statement reports
cover US/HK (the A-share datacenter reports differ and are rate-limited).

Source: adapted from the verified ``sina_financial_report`` function in the
``a-stock-data`` skill (https://github.com/simonlin1212/a-stock-data), §6.4.

Sina's response shape (the part that bit the skill author):
  ``result.data.report_list`` is a dict keyed by report period (e.g. "20260331");
  each period object's ``data`` field is the list of line items
  ``[{item_title, item_value, item_tongbi}, ...]``.

We pivot those into a per-period CSV table, filter to periods on or before
``curr_date`` (look-ahead safety), and render the same header-comment shape as
the other vendors. A-share only — non-numeric / non-A-share symbols raise
``NoMarketDataError`` so the router falls back to the next vendor.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import pandas as pd
import requests

from .errors import NoMarketDataError, VendorRateLimitError

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_URL = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
_TIMEOUT = 20

# Statement -> Sina ``source`` code.
_SOURCE_MAP = {
    "balance": "fzb",   # 资产负债表
    "income": "lrb",    # 利润表
    "cashflow": "llb",  # 现金流量表
}

_MAX_PERIODS = 6
# Pull more than we render so curr_date filtering still leaves enough columns.
_FETCH_PERIODS = 12


def _normalize_cn(symbol: str) -> str:
    """Resolve an A-share symbol to a 6-digit code, else raise.

    Accepts: 600519, SH600519, 600519.SH, sz000001, 000001.SZ, BJ832000.
    Anything that isn't a 6-digit A-share code raises NoMarketDataError so the
    router moves on (this vendor is A-share only).
    """
    s = symbol.strip().upper()
    # Strip exchange affixes in either position.
    for pre in ("SH", "SZ", "BJ"):
        if s.startswith(pre) and s[len(pre):].isdigit():
            s = s[len(pre):]
            break
    if "." in s:
        base, _, suffix = s.rpartition(".")
        # .SH/.SZ/.BJ 之外，.SS（上证雅虎/腾讯风格后缀）也归一为 A股 6 位码
        if suffix in ("SH", "SZ", "BJ", "SS") and base.isdigit():
            s = base
    if len(s) == 6 and s.isdigit():
        return s
    raise NoMarketDataError(symbol, symbol, "not a 6-digit A-share code for Sina")


def _paper_code(code: str) -> str:
    """6-digit code -> Sina paperCode (sh/sz/bj prefix)."""
    if code.startswith(("6", "9")):
        return f"sh{code}"
    if code.startswith("8"):
        return f"bj{code}"
    return f"sz{code}"


def _fetch_report(code: str, source: str) -> dict[str, dict]:
    """Return Sina's ``report_list`` dict (period -> period object)."""
    params = {
        "paperCode": _paper_code(code),
        "source": source,
        "type": "0",
        "page": "1",
        "num": str(_FETCH_PERIODS),
    }
    try:
        r = requests.get(_URL, params=params, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise VendorRateLimitError(f"Sina request failed: {exc}") from exc
    if r.status_code == 429:
        raise VendorRateLimitError("Sina rate limited (HTTP 429)")
    try:
        payload = r.json()
    except ValueError as exc:
        raise VendorRateLimitError(f"Sina non-JSON response: {exc}") from exc
    return payload.get("result", {}).get("data", {}).get("report_list", {}) or {}


def _build_statement(symbol: str, stmt_key: str, curr_date: str | None, title: str) -> str:
    code = _normalize_cn(symbol)
    report_list = _fetch_report(code, _SOURCE_MAP[stmt_key])
    if not report_list:
        raise NoMarketDataError(symbol, code, f"no {stmt_key} data from Sina")

    cutoff = pd.to_datetime(curr_date) if curr_date else pd.Timestamp.today()

    # Pivot period -> {item -> value}, preserving first-seen item order.
    by_item: dict[str, dict[str, float]] = {}
    item_order: list[str] = []
    kept_periods: list[str] = []
    for raw_period in sorted(report_list.keys(), reverse=True):
        # raw_period like "20260331" -> 2026-03-31
        if len(raw_period) != 8 or not raw_period.isdigit():
            continue
        period = f"{raw_period[:4]}-{raw_period[4:6]}-{raw_period[6:8]}"
        if pd.to_datetime(period) > cutoff:
            continue  # look-ahead safety
        if len(kept_periods) >= _MAX_PERIODS:
            break
        kept_periods.append(period)
        for it in report_list[raw_period].get("data", []) or []:
            title_cn = it.get("item_title")
            value = it.get("item_value")
            if not title_cn or value is None:
                continue
            if title_cn not in by_item:
                by_item[title_cn] = {}
                item_order.append(title_cn)
            by_item[title_cn][period] = value

    if not by_item:
        raise NoMarketDataError(symbol, code, f"no {stmt_key} data on/before {cutoff.date()}")

    df = pd.DataFrame(index=item_order, columns=kept_periods)
    for name in item_order:
        for period in kept_periods:
            df.at[name, period] = by_item[name].get(period, "")

    header = f"# {title} for {_paper_code(code)}\n"
    header += f"# Periods shown (most recent first), reported on/before {cutoff.date()}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: Sina Finance (quotes.sina.cn), line items in Chinese, currency: CNY\n\n"
    return header + df.to_csv()


# --- Public vendor API (mirrors sec_edgar / eastmoney signatures) ----------


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Sina returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "balance", curr_date, "Balance Sheet")


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Sina returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "income", curr_date, "Income Statement")


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency (unused; Sina returns all periods)"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    return _build_statement(ticker, "cashflow", curr_date, "Cash Flow Statement")
