"""Tencent Finance (gtimg.cn) market-data vendor.

A keyless, IP-stable alternative to Yahoo Finance for OHLCV history and
real-time quotes, covering A-shares, Hong Kong, and US equities. Added
because yfinance aggressively rate-limits (HTTP 429) shared/cloud IPs,
which aborts a run before any agent reasoning happens.

Endpoints (all public, no key):
  * Realtime quote:  https://qt.gtimg.cn/q=<code>
  * A-share / index: https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
  * Hong Kong:       https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get
  * US:              https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get

Symbol conventions Tencent expects:
  * A-share:  sh600000 / sz000001            (exchange prefix + 6 digits)
  * HK:       hk00700                          (hk + zero-padded code)
  * US:       usNVDA.OQ                         (us + ticker + market suffix)

US klines ONLY return history when the market suffix (.OQ for Nasdaq,
.N for NYSE) is present, so we resolve it once from the realtime quote
(field index 2, e.g. ``NVDA.OQ``) and cache it.

Output format mirrors ``y_finance`` exactly (a header comment block plus a
pandas ``to_csv()`` body with Date/Open/High/Low/Close/Volume columns) so the
vendor is a drop-in replacement in the routing layer.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import pandas as pd
import requests

from .errors import NoMarketDataError, VendorRateLimitError

logger = logging.getLogger(__name__)

_QUOTE_URL = "https://qt.gtimg.cn/q={code}"
_KLINE_URLS = {
    "cn": "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
    "hk": "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get",
    "us": "https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get",
}
_TIMEOUT = 15
# Tencent caps a single kline request; 640 trading days (~2.5 trading years)
# comfortably spans the lookback windows the indicators ask for.
_MAX_KLINE_ROWS = 640

# Cache resolved US market suffixes (NVDA -> NVDA.OQ) for the process lifetime.
_US_SUFFIX_CACHE: dict[str, str] = {}


def _http_get(url: str, params: dict) -> requests.Response:
    try:
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise VendorRateLimitError(f"Tencent request failed: {exc}") from exc
    if resp.status_code == 429:
        raise VendorRateLimitError("Tencent rate limited (HTTP 429)")
    resp.raise_for_status()
    return resp


def _classify(symbol: str) -> tuple[str, str]:
    """Map a user symbol to a (market, tencent_code) pair.

    market is one of "cn" / "hk" / "us". The Tencent code carries the
    exchange/market prefix the kline endpoints require.
    """
    s = symbol.strip().upper()

    # Exchange suffixes (Yahoo/Reuters style) win, since they name the market
    # unambiguously: 07709.HK, 600519.SS, 000001.SZ, AAPL.O. Strip the suffix
    # and route by it before the prefix/heuristic rules below — otherwise a
    # numeric HK code like "07709.HK" falls through to the US default and the
    # US kline endpoint 404s on a code it never had.
    if "." in s:
        base, _, suffix = s.rpartition(".")
        if base:
            if suffix == "HK":
                return "hk", "hk" + base.lstrip("0").zfill(5) if base.isdigit() else "hk" + base
            if suffix in ("SS", "SH"):
                return "cn", "sh" + base
            if suffix in ("SZ",):
                return "cn", "sz" + base
            # Any other suffix (.O/.OQ/.N for US, .L London, ...) — treat the
            # base as a US ticker; the US path resolves the real market suffix.
            if not base.isdigit():
                return "us", base

    # Explicit prefixes win: SH600000, SZ000001, HK00700, US AAPL.
    if s.startswith(("SH", "SZ")) and s[2:].isdigit():
        return "cn", s.lower()
    if s.startswith("HK") and s[2:].isdigit():
        return "hk", "hk" + s[2:].zfill(5)
    if s.startswith("US"):
        return "us", s[2:].lstrip(".")

    # Bare digits: infer the Chinese exchange from the leading digit.
    if s.isdigit():
        if len(s) <= 5:
            # 5-or-fewer digit numeric codes are Hong Kong (zero-padded).
            return "hk", "hk" + s.zfill(5)
        # 6-digit A-share: 6xxxxx is Shanghai, otherwise Shenzhen.
        prefix = "sh" if s.startswith(("6", "9")) else "sz"
        return "cn", prefix + s

    # Everything else is treated as a US ticker.
    return "us", s


def _resolve_us_code(ticker: str) -> str:
    """Return the Tencent US code with market suffix, e.g. ``usNVDA.OQ``.

    The suffix is mandatory for US kline history. We read it from the
    realtime quote (``v_usNVDA="...~NVDA.OQ~..."``) and cache it.
    """
    ticker = ticker.upper()
    if ticker in _US_SUFFIX_CACHE:
        return _US_SUFFIX_CACHE[ticker]

    resp = _http_get(_QUOTE_URL.format(code=f"us{ticker}"), {})
    text = resp.text.strip()
    # v_usNVDA="200~英伟达~NVDA.OQ~208.65~...";
    code = f"us{ticker}"
    if "~" in text and '="' in text:
        payload = text.split('="', 1)[1].rstrip('";\n')
        fields = payload.split("~")
        if len(fields) > 2 and fields[2]:
            # fields[2] is like "NVDA.OQ"
            code = f"us{fields[2]}"
    _US_SUFFIX_CACHE[ticker] = code
    return code


def _tencent_code(symbol: str) -> tuple[str, str]:
    """Return (market, full_code) ready for the kline endpoints."""
    market, code = _classify(symbol)
    if market == "us":
        code = _resolve_us_code(code)
    return market, code


def _fetch_kline(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch daily OHLCV from Tencent as a normalized DataFrame.

    Columns: Date (datetime), Open, High, Low, Close, Volume. Rows are
    inclusive of both start_date and end_date.
    """
    market, code = _tencent_code(symbol)
    url = _KLINE_URLS[market]
    param = f"{code},day,{start_date},{end_date},{_MAX_KLINE_ROWS},qfq"
    resp = _http_get(url, {"param": param})

    try:
        payload = resp.json()
    except ValueError as exc:
        raise NoMarketDataError(symbol, code, f"invalid JSON from Tencent: {exc}") from exc

    data = payload.get("data") or {}
    node = data.get(code)
    if node is None and data:
        # The response key sometimes drops/keeps the suffix; take the first.
        node = next(iter(data.values()))
    if not isinstance(node, dict):
        raise NoMarketDataError(symbol, code, "no data node in Tencent response")

    # Forward-adjusted series preferred ("qfqday"), else raw "day".
    rows = node.get("qfqday") or node.get("day") or []
    if not rows:
        raise NoMarketDataError(
            symbol, code, f"no rows between {start_date} and {end_date}"
        )

    # Each row: [date, open, close, high, low, volume, ...extras].
    records = []
    for r in rows:
        if len(r) < 6:
            continue
        records.append(
            {
                "Date": r[0],
                "Open": r[1],
                "Close": r[2],
                "High": r[3],
                "Low": r[4],
                "Volume": r[5],
            }
        )

    df = pd.DataFrame.from_records(records)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)

    # Clip to the requested inclusive window (Tencent may overshoot on the
    # left when the row count cap is hit before the start date).
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    df = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)].reset_index(drop=True)

    if df.empty:
        raise NoMarketDataError(
            symbol, code, f"no rows between {start_date} and {end_date}"
        )
    return df


# --- Public vendor API (mirrors y_finance signatures) ----------------------


def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """OHLCV history as a CSV string with a header block (yfinance-compatible)."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    _, code = _tencent_code(symbol)
    df = _fetch_kline(symbol, start_date, end_date)

    out = df.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    for col in ("Open", "High", "Low", "Close"):
        out[col] = out[col].round(2)
    out = out.set_index("Date")

    csv_string = out.to_csv()
    label = code if code.upper() == symbol.upper() else f"{code} (from {symbol})"
    header = f"# Stock data for {label} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(out)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: Tencent Finance (gtimg.cn)\n\n"
    return header + csv_string


def load_ohlcv_tencent(symbol: str, curr_date: str) -> pd.DataFrame:
    """Return ~2.5y of OHLCV up to curr_date for indicator calculation.

    Mirrors ``stockstats_utils.load_ohlcv``: a Date column plus OHLCV,
    filtered to ``<= curr_date`` to prevent look-ahead bias.
    """
    curr_dt = pd.to_datetime(curr_date)
    start_dt = curr_dt - pd.DateOffset(years=3)
    df = _fetch_kline(
        symbol, start_dt.strftime("%Y-%m-%d"), curr_dt.strftime("%Y-%m-%d")
    )
    return df[df["Date"] <= curr_dt].reset_index(drop=True)
