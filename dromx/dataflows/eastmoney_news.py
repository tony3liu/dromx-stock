"""Eastmoney news (stock-specific + 7x24 global) for A-share coverage.

Google News indexes Chinese-listed companies thinly, so A-share runs benefit
from a native Chinese-language news source. Eastmoney exposes a keyless
stock-news search and a 7x24 global financial wire.

Source: adapted from §5.1 (eastmoney_stock_news) and §5.3 (eastmoney_global
_news) of the ``a-stock-data`` skill (https://github.com/simonlin1212/a-stock-data).

Output mirrors ``google_news`` / ``yfinance_news`` (a ``## ... News`` header
plus ``### Title (source: ...)`` blocks) so it is a drop-in routing replacement.
All Eastmoney requests go through the shared throttle (serial, ≥1s + jitter,
Keep-Alive session); the stock-news endpoint occasionally returns empty under
Eastmoney's IP throttling, which we surface as "no news" rather than an error so
the router can fall back to Google.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
import uuid
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta

from .config import get_config
from .utils import format_news_headline

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_SEARCH_URL = "https://search-api-web.eastmoney.com/search/jsonp"
_GLOBAL_URL = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
_TIMEOUT = 15

# Shared Eastmoney throttle (same policy as eastmoney.py — kept local to avoid a
# cross-module import cycle through interface.py).
_EM_SESSION = requests.Session()
_EM_SESSION.headers.update({"User-Agent": _UA})
_EM_MIN_INTERVAL = 1.0
_em_last_call = [0.0]

_TAG_RE = re.compile(r"<[^>]+>")


def _em_get(url: str, params: dict, headers: dict | None = None) -> requests.Response | None:
    """Throttled Eastmoney GET. Returns None on request failure (news is best-effort)."""
    wait = _EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return _EM_SESSION.get(url, params=params, headers=headers, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("Eastmoney news request failed: %s", exc)
        return None
    finally:
        _em_last_call[0] = time.time()


def _strip(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _normalize_cn(ticker: str) -> str:
    """Best-effort 6-digit A-share code; returns the raw keyword if not numeric."""
    s = ticker.strip().upper()
    for pre in ("SH", "SZ", "BJ"):
        if s.startswith(pre) and s[len(pre):].isdigit():
            return s[len(pre):]
    if "." in s:
        base, _, suffix = s.rpartition(".")
        if suffix in ("SH", "SZ", "BJ") and base.isdigit():
            return base
    return s


def _parse_dt(raw: str):
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip()[:19], fmt)
        except ValueError:
            continue
    return None


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    """A-share stock-specific news from Eastmoney (google_news-compatible output)."""
    limit = get_config()["news_article_limit"]
    code = _normalize_cn(ticker)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    inner = json.dumps(
        {
            "uid": "",
            "keyword": code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": max(limit, 20),
                    "preTag": "",
                    "postTag": "",
                }
            },
        },
        separators=(",", ":"),
    )
    resp = _em_get(_SEARCH_URL, {"cb": "jQuery_news", "param": inner},
                   headers={"Referer": "https://so.eastmoney.com/"})
    if resp is None:
        return f"No news found for {ticker}"

    try:
        text = resp.text
        payload = json.loads(text[text.index("(") + 1: text.rindex(")")])
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Eastmoney news parse error for %s: %s", code, exc)
        return f"No news found for {ticker}"

    articles = payload.get("result", {}).get("cmsArticleWebOld", []) or []
    body = ""
    kept = 0
    for a in articles:
        pub = _parse_dt(a.get("date", ""))
        if pub is not None and not (start_dt <= pub <= end_dt + relativedelta(days=1)):
            continue
        title = _strip(a.get("title", ""))
        if not title:
            continue
        source = _strip(a.get("mediaName", "")) or "Eastmoney"
        body += format_news_headline(title, source, pub) + "\n"
        snippet = _strip(a.get("content", ""))[:200]
        if snippet:
            body += f"{snippet}\n"
        if a.get("url"):
            body += f"Link: {a['url']}\n"
        body += "\n"
        kept += 1
        if kept >= limit:
            break

    if not body:
        return f"No news found for {ticker} between {start_date} and {end_date}"
    return f"## {ticker} News, from {start_date} to {end_date}:\n\n{body}"


def get_global_news(
    curr_date: str,
    look_back_days: int | None = None,
    limit: int | None = None,
) -> str:
    """Eastmoney 7x24 global financial wire (google_news-compatible output)."""
    config = get_config()
    if look_back_days is None:
        look_back_days = config["global_news_lookback_days"]
    if limit is None:
        limit = config["global_news_article_limit"]

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    resp = _em_get(
        _GLOBAL_URL,
        {
            "client": "web",
            "biz": "web_724",
            "fastColumn": "102",
            "sortEnd": "",
            "pageSize": str(max(limit * 3, 50)),
            "req_trace": str(uuid.uuid4()),
        },
        headers={"Referer": "https://kuaixun.eastmoney.com/"},
    )
    if resp is None:
        return f"No global news found for {curr_date}"

    try:
        items = resp.json().get("data", {}).get("fastNewsList", []) or []
    except ValueError as exc:
        logger.warning("Eastmoney global news parse error: %s", exc)
        return f"No global news found for {curr_date}"

    body = ""
    kept = 0
    for item in items:
        pub = _parse_dt(item.get("showTime", ""))
        if pub is not None and not (start_dt <= pub <= curr_dt + relativedelta(days=1)):
            continue
        title = _strip(item.get("title", "")) or _strip(item.get("summary", ""))[:80]
        if not title:
            continue
        body += format_news_headline(title, "Eastmoney 7x24", pub) + "\n"
        summary = _strip(item.get("summary", ""))[:200]
        if summary:
            body += f"{summary}\n"
        body += "\n"
        kept += 1
        if kept >= limit:
            break

    if not body:
        return f"No global news found between {start_date} and {curr_date}"
    return f"## Global Market News, from {start_date} to {curr_date}:\n\n{body}"
