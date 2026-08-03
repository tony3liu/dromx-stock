"""Eastmoney full-market snapshot — the free ``universe`` source for screening.

DromX' data layer fetches one symbol at a time (``load_ohlcv``); it has
no notion of "every stock in a market". The v0.4.0 strategy engine needs that
universe to screen across. Eastmoney's public ``clist`` endpoint provides it for
free (no key): a single paginated call returns every listed name in a market
with its latest-day snapshot fields.

Verified live (2026-07): HK ~4700 names, US ~13600, A-share ~5500 — keyless.

  GET https://push2.eastmoney.com/api/qt/clist/get
      ?pn=<page>&pz=<page_size>&po=1&np=1&fltt=2&fid=f3&fs=<market>&fields=<csv>

``fltt=2`` makes every market return real floats (omitting it yields price×100
integers). ``fs`` selects the market. ``data.total`` is the full count; ``diff``
is the page — which Eastmoney returns as either a JSON list OR a dict keyed by
index, so we normalise both.

Field map (keyless snapshot):
  f12 symbol   f14 name   f2 close     f3 change_pct   f5 volume
  f6 amount    f8 turnover_rate        f9 pe           f10 vol_ratio
  f20 market_cap           f24 change_60d

This is a *snapshot* only — no OHLC history, no moving averages. Technical
indicators (ma/rsi/macd/…) are computed on demand per candidate in
``strategy.data_adapter`` from the existing free OHLCV vendors.

Design: fully ``_safe`` — any network/parse failure yields an empty list, never
an exception, so a screening run degrades to "no candidates" instead of crashing.
"""
from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_TIMEOUT = 20
_PAGE_SIZE = 100  # Eastmoney caps a page at 100 rows regardless of the pz asked
_MAX_PAGES = 400  # hard stop: 400 * 100 = 40k names, well above any single market

# Market -> Eastmoney ``fs`` selector. Verified against the live endpoint.
#   hk: mainboard + GEM + others (t:1..4 under m:128)
#   us: NASDAQ / NYSE / AMEX (m:105/106/107)
#   cn: SH/SZ mainboard + ChiNext + STAR (the standard A-share screen filter)
_MARKET_FS = {
    "hk": "m:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2",
    "us": "m:105,m:106,m:107",
    "cn": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
}

# Snapshot fields we request + how they map onto our normalised column names.
_FIELDS = "f12,f14,f2,f3,f5,f6,f8,f9,f10,f20,f24"
_FIELD_MAP = {
    "f12": "symbol",
    "f14": "name",
    "f2": "close",
    "f3": "change_pct",
    "f5": "volume",
    "f6": "amount",
    "f8": "turnover_rate",
    "f9": "pe",
    "f10": "vol_ratio",
    "f20": "market_cap",
    "f24": "change_60d",
}
# Numeric fields: Eastmoney writes "-" for missing values → coerce to None.
_NUMERIC = {"close", "change_pct", "volume", "amount", "turnover_rate",
            "pe", "vol_ratio", "market_cap", "change_60d"}

_SESSION = requests.Session()
# 强制直连：macOS 系统代理/VPN 访问 push2.eastmoney.com 会被直接断连
# (RemoteDisconnected)，导致全市场快照返回 0 只、选股全空
_SESSION.trust_env = False
_SESSION.headers.update({
    "User-Agent": _UA,
    # Eastmoney sometimes drops connections for requests without a Referer.
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "*/*",
})

_PAGE_RETRIES = 3       # per-page attempts before giving up on the page
_RETRY_BACKOFF = 0.6    # seconds, multiplied by attempt index


def _num(v):
    """Coerce an Eastmoney cell to float or None ('-'/''/None → None)."""
    if v is None or v == "-" or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize_symbol(market: str, code: str) -> str:
    """Turn Eastmoney's bare code into the symbol the OHLCV vendors understand.

    HK: 5-digit code -> ``00700.HK``. A-share: 6-digit code -> ``600519.SS`` /
    ``000001.SZ`` by prefix. US: the ticker is already the symbol.
    """
    code = str(code).strip()
    if market == "hk":
        return f"{code.zfill(5)}.HK"
    if market == "cn":
        # 6/68/9 -> Shanghai; 0/3/2 -> Shenzhen; 4/8 -> Beijing.
        if code.startswith(("5", "6", "9")) or code.startswith("68"):
            return f"{code}.SS"
        if code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SZ"
    return code  # us


def _parse_diff(diff) -> list[dict]:
    """Eastmoney returns ``diff`` as either a list or an index-keyed dict."""
    if isinstance(diff, dict):
        return list(diff.values())
    if isinstance(diff, list):
        return diff
    return []


def _fetch_page_curl(url: str, params: dict) -> dict | None:
    """Fallback: 用系统 curl 拉一页（macOS SecureTransport 指纹过 WAF）。

    东财 push2 的 WAF 按 TLS 指纹拦截 OpenSSL 系客户端（requests/urllib3/
    curl_cffi 全部 RemoteDisconnected），但放行 macOS 系统 curl。仅在
    requests 失败时兜底；无 curl 或失败返回 None。
    """
    import json
    import shutil
    import subprocess
    import urllib.parse

    if not shutil.which("curl"):
        return None
    qs = urllib.parse.urlencode(params)
    try:
        out = subprocess.run(
            [
                "curl", "-sS", "-m", str(_TIMEOUT),
                "-H", f"User-Agent: {_UA}",
                "-H", "Referer: https://quote.eastmoney.com/",
                f"{url}?{qs}",
            ],
            capture_output=True, text=True, check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return json.loads(out.stdout)
    except Exception:  # noqa: BLE001
        return None


def _fetch_page(params: dict) -> dict | None:
    """Fetch one clist page with retry/backoff. None if all attempts fail.

    Eastmoney intermittently drops connections (RemoteDisconnected) under
    repeated access; a couple of retries turns a transient blip into success
    instead of an empty universe. requests 全部失败时兜底系统 curl（TLS 指纹）。
    """
    for attempt in range(1, _PAGE_RETRIES + 1):
        try:
            resp = _SESSION.get(_CLIST_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — best-effort free source
            if attempt < _PAGE_RETRIES:
                time.sleep(_RETRY_BACKOFF * attempt)
                continue
            logger.warning("universe snapshot page fetch failed after %d tries: %s",
                           _PAGE_RETRIES, e)
    # requests 全部失败 → 系统 curl 兜底（push2 WAF 按 TLS 指纹拦截 Python 客户端）
    payload = _fetch_page_curl(_CLIST_URL, params)
    if payload is None:
        logger.warning("universe snapshot page fetch failed (requests + curl)")
    return payload


def fetch_universe_snapshot(market: str) -> list[dict]:
    """Return the latest-day snapshot for every listed name in ``market``.

    ``market`` is one of ``hk`` / ``us`` / ``cn``. Each row is a dict with the
    normalised keys in ``_FIELD_MAP`` plus a vendor-ready ``symbol``. Returns an
    empty list on any failure (network, unknown market, malformed JSON) — this
    is a best-effort free source, never a hard dependency.
    """
    market = (market or "").strip().lower()
    fs = _MARKET_FS.get(market)
    if not fs:
        logger.warning("unknown market for universe snapshot: %r", market)
        return []

    rows: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        params = {
            "pn": page, "pz": _PAGE_SIZE, "po": 1, "np": 1,
            "fltt": 2, "fid": "f3", "fs": fs, "fields": _FIELDS,
        }
        payload = _fetch_page(params)
        if payload is None:
            break

        data = (payload or {}).get("data") or {}
        diff = _parse_diff(data.get("diff"))
        if not diff:
            break

        for raw in diff:
            code = raw.get("f12")
            if not code:
                continue
            row: dict = {"symbol": _normalize_symbol(market, code), "market": market}
            for fk, name in _FIELD_MAP.items():
                if name in ("symbol",):
                    continue
                val = raw.get(fk)
                row[name] = _num(val) if name in _NUMERIC else val
            rows.append(row)

        total = data.get("total") or 0
        if page * _PAGE_SIZE >= total or len(diff) < _PAGE_SIZE:
            break
        # Be polite to the public endpoint between pages.
        time.sleep(0.15)

    logger.info("universe snapshot %s: %d names", market, len(rows))
    return rows
