"""mootdx (TongDaXin TCP) A-share OHLCV and financial snapshot.

mootdx speaks the TongDaXin binary protocol over TCP 7709 — keyless and, unlike
the HTTP vendors, not IP-rate-limited, so it can be polled freely from a China
IP. It provides A-share daily K-line and a 37-field quarterly financial
snapshot (EPS / ROE / net profit / revenue).

Source: adapted from the verified ``tdx_client`` helper and §1.1 / §6.1 of the
``a-stock-data`` skill (https://github.com/simonlin1212/a-stock-data).

Caveat (documented in the skill): TongDaXin servers sit behind TCP 7709, which
overseas networks almost always cannot reach — connections simply time out. We
probe a known-good server list first and, if none are reachable (or mootdx
errors for any reason), raise ``VendorRateLimitError`` so the router falls back
to the next configured vendor (Tencent already covers A-share OHLCV over HTTP).
mootdx is therefore best treated as a China-IP optimization, not a hard
dependency of the analysis.

mootdx 0.11.x has a BESTIP bug (empty ``BESTIP.HQ`` string -> unpack error); the
``_client`` helper sidesteps it by passing an explicit reachable server.
"""

from __future__ import annotations

import logging
import socket
from datetime import datetime
from typing import Annotated

import pandas as pd

from .errors import NoMarketDataError, VendorRateLimitError

logger = logging.getLogger(__name__)

# Known-good TongDaXin servers (by latency, per the skill's 2026-06 probe).
_TDX_SERVERS = [
    ("119.97.185.59", 7709), ("124.70.133.119", 7709), ("116.205.183.150", 7709),
    ("123.60.73.44", 7709), ("116.205.163.254", 7709), ("121.36.225.169", 7709),
    ("123.60.70.228", 7709), ("124.71.9.153", 7709), ("110.41.147.114", 7709),
    ("124.71.187.122", 7709),
]
_PROBE_TIMEOUT = 2.0
# Daily K-line bars to request (~2.5 trading years, enough for indicators).
_KLINE_BARS = 640


def _probe(ip: str, port: int, timeout: float = _PROBE_TIMEOUT) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _client():
    """Create a mootdx Quotes client, sidestepping the 0.11.x BESTIP bug.

    Raises VendorRateLimitError if no TongDaXin server is reachable (the typical
    overseas case) so the router falls back to the next vendor.
    """
    try:
        from mootdx.quotes import Quotes
    except ImportError as exc:
        raise VendorRateLimitError(f"mootdx not installed: {exc}") from exc

    for ip, port in _TDX_SERVERS:
        if _probe(ip, port):
            try:
                return Quotes.factory(market="std", server=(ip, port))
            except Exception as exc:  # noqa: BLE001 — try the next server
                logger.debug("mootdx factory failed on %s:%s (%s)", ip, port, exc)
                continue
    raise VendorRateLimitError(
        "no TongDaXin server reachable (TCP 7709 — overseas networks usually "
        "time out); falling back to next vendor"
    )


def _normalize_cn(symbol: str) -> str:
    """Resolve an A-share symbol to a 6-digit code, else raise NoMarketDataError."""
    s = symbol.strip().upper()
    for pre in ("SH", "SZ", "BJ"):
        if s.startswith(pre) and s[len(pre):].isdigit():
            s = s[len(pre):]
            break
    if "." in s:
        base, _, suffix = s.rpartition(".")
        if suffix in ("SH", "SZ", "BJ") and base.isdigit():
            s = base
    if len(s) == 6 and s.isdigit():
        return s
    raise NoMarketDataError(symbol, symbol, "not a 6-digit A-share code for mootdx")


def _fetch_bars(code: str) -> pd.DataFrame:
    """Daily OHLCV DataFrame (Date/Open/High/Low/Close/Volume) via mootdx."""
    client = _client()
    try:
        # category=4 -> daily; offset = number of most-recent bars.
        bars = client.bars(symbol=code, category=4, offset=_KLINE_BARS)
    except Exception as exc:  # noqa: BLE001 — network/protocol hiccup -> fall back
        raise VendorRateLimitError(f"mootdx bars() failed for {code}: {exc}") from exc

    if bars is None or len(bars) == 0:
        raise NoMarketDataError(code, code, "mootdx returned no bars")

    df = pd.DataFrame(bars)
    # mootdx returns a 'datetime' column like "2026-06-20 00:00" plus
    # open/high/low/close/vol. Normalize to the canonical OHLCV frame.
    if "datetime" not in df.columns:
        raise NoMarketDataError(code, code, "mootdx bars missing datetime column")
    out = pd.DataFrame({
        "Date": pd.to_datetime(df["datetime"], errors="coerce"),
        "Open": pd.to_numeric(df.get("open"), errors="coerce"),
        "High": pd.to_numeric(df.get("high"), errors="coerce"),
        "Low": pd.to_numeric(df.get("low"), errors="coerce"),
        "Close": pd.to_numeric(df.get("close"), errors="coerce"),
        "Volume": pd.to_numeric(df.get("vol"), errors="coerce"),
    })
    out = out.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
    if out.empty:
        raise NoMarketDataError(code, code, "mootdx bars unparseable")
    return out


# --- Public vendor API -----------------------------------------------------


def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """A-share OHLCV history as a CSV string (yfinance/tencent-compatible)."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")
    code = _normalize_cn(symbol)
    df = _fetch_bars(code)

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    df = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)].reset_index(drop=True)
    if df.empty:
        raise NoMarketDataError(symbol, code, f"no rows between {start_date} and {end_date}")

    out = df.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    for col in ("Open", "High", "Low", "Close"):
        out[col] = out[col].round(2)
    out = out.set_index("Date")

    header = f"# Stock data for {code} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(out)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: mootdx (TongDaXin TCP)\n\n"
    return header + out.to_csv()


def load_ohlcv_mootdx(symbol: str, curr_date: str) -> pd.DataFrame:
    """Return daily OHLCV up to curr_date for indicator calculation.

    Mirrors ``tencent.load_ohlcv_tencent`` / ``stockstats_utils.load_ohlcv``:
    a Date column plus OHLCV, filtered to ``<= curr_date`` to prevent
    look-ahead bias. Raises VendorRateLimitError when no TongDaXin server is
    reachable so the caller can fall back to Tencent.
    """
    code = _normalize_cn(symbol)
    df = _fetch_bars(code)
    curr_dt = pd.to_datetime(curr_date)
    return df[df["Date"] <= curr_dt].reset_index(drop=True)


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
):
    """37-field quarterly financial snapshot via mootdx finance()."""
    code = _normalize_cn(ticker)
    client = _client()
    try:
        fin = client.finance(symbol=code)
    except Exception as exc:  # noqa: BLE001
        raise VendorRateLimitError(f"mootdx finance() failed for {code}: {exc}") from exc

    if fin is None or (isinstance(fin, pd.DataFrame) and fin.empty):
        raise NoMarketDataError(ticker, code, "mootdx returned no financial snapshot")

    # mootdx returns a single-row frame or dict of named fields. Surface the
    # most decision-relevant ones with readable labels.
    if isinstance(fin, pd.DataFrame):
        row = fin.iloc[0].to_dict() if not fin.empty else {}
    elif isinstance(fin, dict):
        row = fin
    else:
        row = dict(fin)

    label_map = [
        ("EPS (每股收益)", "eps"),
        ("BVPS (每股净资产)", "bvps"),
        ("ROE %", "roe"),
        ("Net Profit (净利润)", "profit"),
        ("Revenue (主营收入)", "income"),
        ("Total Shares (总股本)", "zongguben"),
        ("Float Shares (流通股本)", "liutongguben"),
    ]
    lines = [f"{label}: {row[key]}" for label, key in label_map if key in row and row[key] is not None]
    if not lines:
        raise NoMarketDataError(ticker, code, "mootdx snapshot had no usable fields")

    header = f"# Company Fundamentals (quarterly snapshot) for {code}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "# Source: mootdx (TongDaXin) finance snapshot\n\n"
    return header + "\n".join(lines)
