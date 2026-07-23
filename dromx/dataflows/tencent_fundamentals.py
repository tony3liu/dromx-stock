"""Tencent Finance fundamentals (keyless overview snapshot).

A lightweight fundamentals fallback for when Yahoo Finance is rate-limited.
The realtime quote endpoint (``qt.gtimg.cn``) carries a handful of valuation
fields (market cap, P/E, 52-week range, turnover/amplitude) alongside the
price snapshot, which is enough for the Fundamentals analyst to anchor on.

IMPORTANT: these are CURRENT-snapshot values, not point-in-time history. The
header says so explicitly so the agent treats them as "latest known" rather
than as the value on a historical backtest date. For full point-in-time
financial statements use a vendor that serves them (alpha_vantage / yfinance).

US realtime field map (``~``-separated, index -> meaning), cross-checked
across multiple tickers:
    1 name(local) 3 price 33 day-high 34 day-low 35 currency
    39 P/E 44 float-cap(亿) 45 total-cap(亿) 46 name(English)
    48 52w-high 49 52w-low
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import requests

from .errors import NoMarketDataError, VendorRateLimitError
from .tencent import _classify, _resolve_us_code

logger = logging.getLogger(__name__)

_QUOTE_URL = "https://qt.gtimg.cn/q={code}"
_TIMEOUT = 15


def _quote_fields(code: str) -> list[str]:
    try:
        resp = requests.get(_QUOTE_URL.format(code=code), timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise VendorRateLimitError(f"Tencent quote failed: {exc}") from exc
    if resp.status_code == 429:
        raise VendorRateLimitError("Tencent rate limited (HTTP 429)")
    resp.raise_for_status()
    text = resp.text.strip()
    if '="' not in text:
        return []
    payload = text.split('="', 1)[1].rstrip('";\n')
    return payload.split("~")


def _g(fields: list[str], i: int) -> str | None:
    """Return field i if present and non-empty/non-zero, else None."""
    if i < len(fields):
        v = fields[i].strip()
        if v and v not in ("0", "0.00"):
            return v
    return None


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date (snapshot is latest, not historical)"] = None,
):
    """Company fundamentals overview from Tencent's realtime quote snapshot."""
    market, code = _classify(ticker)
    if market == "us":
        code = _resolve_us_code(code)

    fields = _quote_fields(code)
    if not fields or len(fields) < 4:
        raise NoMarketDataError(ticker, code, "no quote fields from Tencent")

    if market == "us":
        rows = [
            ("Name", _g(fields, 46) or _g(fields, 1)),
            ("Currency", _g(fields, 35)),
            ("Price", _g(fields, 3)),
            ("PE Ratio", _g(fields, 39)),
            ("Market Cap (100M)", _g(fields, 45)),
            ("Float Cap (100M)", _g(fields, 44)),
            ("52 Week High", _g(fields, 48)),
            ("52 Week Low", _g(fields, 49)),
            ("Day High", _g(fields, 33)),
            ("Day Low", _g(fields, 34)),
        ]
    else:
        # A-share / HK realtime layout: 1 name 3 price 39 P/E 45 cap 47 P/B.
        rows = [
            ("Name", _g(fields, 1)),
            ("Price", _g(fields, 3)),
            ("PE Ratio", _g(fields, 39)),
            ("Market Cap (100M)", _g(fields, 45)),
            ("PB Ratio", _g(fields, 46)),
            ("52 Week High", _g(fields, 48)),
            ("52 Week Low", _g(fields, 49)),
        ]

    lines = [f"{label}: {value}" for label, value in rows if value is not None]
    if len(lines) <= 1:
        raise NoMarketDataError(ticker, code, "no usable fundamental fields")

    header = f"# Company Fundamentals (overview) for {code}\n"
    header += (
        "# NOTE: Tencent provides a CURRENT-snapshot overview only "
        "(market cap / P/E / 52-week range reflect the latest session, "
        "not the historical analysis date). Treat as latest-known values.\n"
    )
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: Tencent Finance (gtimg.cn)\n\n"
    return header + "\n".join(lines)


def _no_statements(ticker, *_args, **_kwargs):
    """Statement-level financials are not served by Tencent.

    Raising NoMarketDataError (rather than returning prose) lets the routing
    layer emit one clean "data unavailable" sentinel, so the agent reports the
    gap honestly instead of fabricating values or crashing on a missing vendor.
    """
    raise NoMarketDataError(
        ticker,
        ticker,
        "Tencent serves an overview snapshot only, not full financial "
        "statements (balance sheet / cash flow / income statement)",
    )


# Statement-level entry points share the same "not covered" behavior; exposed
# separately so the router can map each method to a vendor implementation.
get_balance_sheet = _no_statements
get_cashflow = _no_statements
get_income_statement = _no_statements
get_insider_transactions = _no_statements
