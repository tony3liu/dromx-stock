"""Eastmoney limit-up / limit-down pool — the free A-share 涨停/跌停 data source.

A-share limit-up strategies (连板/涨停接力/断板反包) need per-name limit-up state
that cannot be derived from OHLCV alone — specifically the *consecutive* board
count (连板数). Eastmoney's public ``push2ex`` topic-pool endpoint provides it
free (no key):

  GET https://push2ex.eastmoney.com/getTopicZTPool  (涨停池 / limit-up)
  GET https://push2ex.eastmoney.com/getTopicDTPool  (跌停池 / limit-down)
      ?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt
      &Pageindex=0&pagesize=<n>&sort=fbt:asc&date=YYYYMMDD

Verified live (2026-07): the ZT pool returns ``data.tc`` (total) + ``data.pool``,
each row carrying the fields the CN strategies need:
  c code   m market(0=SZ,1=SH)   n name   p price×100   zdp change%%
  lbc 连板数(consecutive)         zttj.days 连板天数        zbc 炸板次数(broken)
  hybk 行业板块                    fund 封单资金             hs 换手

Design: fully ``_safe`` — any failure yields an empty dict, so the CN universe
simply gets no limit-up flags (strategies find nothing) instead of crashing.
"""
from __future__ import annotations

import logging
import time
from datetime import date

import requests

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_ZT_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
_DT_URL = "https://push2ex.eastmoney.com/getTopicDTPool"
_UT = "7eea3edcaed734bea9cbfc24409ed989"
_TIMEOUT = 20
_PAGE_SIZE = 800  # A-share never has >~200 limit-ups in a day; 800 is ample
_RETRIES = 3
_BACKOFF = 0.6

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": _UA,
    "Referer": "https://quote.eastmoney.com/ztb/",
    "Accept": "*/*",
})


def _normalize_symbol(m: int, code: str) -> str:
    """ZT-pool (code, market) → vendor-ready symbol. m=0→深(.SZ), m=1→沪(.SS)."""
    code = str(code).strip()
    return f"{code}.SS" if m == 1 else f"{code}.SZ"


def _get(url: str, date_str: str) -> dict | None:
    """Fetch a pool page with retry/backoff. None on total failure."""
    params = {
        "ut": _UT, "dpt": "wz.ztzt", "Pageindex": 0,
        "pagesize": _PAGE_SIZE, "sort": "fbt:asc", "date": date_str,
    }
    for attempt in range(1, _RETRIES + 1):
        try:
            resp = _SESSION.get(url, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — best-effort free source
            if attempt < _RETRIES:
                time.sleep(_BACKOFF * attempt)
                continue
            logger.warning("limit pool fetch failed after %d tries: %s", _RETRIES, e)
            return None
    return None


def _date_str(as_of: date) -> str:
    return as_of.strftime("%Y%m%d") if isinstance(as_of, date) else str(as_of).replace("-", "")


def fetch_limit_up_pool(as_of: date) -> dict[str, dict]:
    """Return ``{symbol: {...limit-up state...}}`` for the limit-up pool on ``as_of``.

    Each value: ``{name, consecutive, zt_days, broken, hybk, sealed_fund,
    change_pct}``. Empty dict on any failure (→ no limit-up flags, never a crash).
    """
    payload = _get(_ZT_URL, _date_str(as_of))
    if not payload:
        return {}
    pool = ((payload or {}).get("data") or {}).get("pool") or []
    out: dict[str, dict] = {}
    for r in pool:
        code = r.get("c")
        if not code:
            continue
        sym = _normalize_symbol(r.get("m", 0), code)
        zttj = r.get("zttj") or {}
        out[sym] = {
            "name": r.get("n"),
            "consecutive": int(r.get("lbc") or 0),
            "zt_days": int(zttj.get("days") or 0),
            "broken": int(r.get("zbc") or 0),
            "hybk": r.get("hybk"),
            "sealed_fund": r.get("fund"),
            "change_pct": r.get("zdp"),
        }
    logger.info("limit-up pool %s: %d names", _date_str(as_of), len(out))
    return out


def fetch_limit_down_pool(as_of: date) -> dict[str, dict]:
    """Return ``{symbol: {...limit-down state...}}`` for the limit-down pool.

    Each value: ``{name, open_count, days, hybk, change_pct}``. Empty on failure.
    """
    payload = _get(_DT_URL, _date_str(as_of))
    if not payload:
        return {}
    pool = ((payload or {}).get("data") or {}).get("pool") or []
    out: dict[str, dict] = {}
    for r in pool:
        code = r.get("c")
        if not code:
            continue
        sym = _normalize_symbol(r.get("m", 0), code)
        out[sym] = {
            "name": r.get("n"),
            "open_count": int(r.get("oc") or 0),
            "days": int(r.get("days") or 0),
            "hybk": r.get("hybk"),
            "change_pct": r.get("zdp"),
        }
    logger.info("limit-down pool %s: %d names", _date_str(as_of), len(out))
    return out
