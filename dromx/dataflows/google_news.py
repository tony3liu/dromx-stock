"""Google News RSS data source (keyless, IP-stable).

A drop-in news vendor for when Yahoo Finance is rate-limited. Google News
publishes a public RSS search feed that needs no API key and does not
aggressively throttle, covering both ticker-specific and macro headlines.

Feed: https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en

Output format mirrors ``yfinance_news`` (a ``## ... News`` header plus
``### Title (source: ...)`` blocks) so it is a drop-in routing replacement.
Articles are filtered to the requested [start, end] window for look-ahead
safety, exactly like the yfinance path.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests
from dateutil.relativedelta import relativedelta

from .config import get_config
from .symbol_utils import normalize_symbol
from .utils import format_news_headline

logger = logging.getLogger(__name__)

_RSS_URL = "https://news.google.com/rss/search"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DromX/1.0)"}
_TIMEOUT = 15


def _fetch_rss(query: str) -> list[dict]:
    """Fetch and parse a Google News RSS search into article dicts."""
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    try:
        resp = requests.get(_RSS_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Google News RSS request failed for %r: %s", query, exc)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        logger.warning("Google News RSS parse error for %r: %s", query, exc)
        return []

    articles = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = item.findtext("pubDate")
        source_el = item.find("source")
        publisher = (source_el.text if source_el is not None else "") or "Google News"

        pub_date = None
        if pub_raw:
            try:
                pub_date = parsedate_to_datetime(pub_raw).replace(tzinfo=None)
            except (TypeError, ValueError):
                pub_date = None

        if title:
            articles.append(
                {
                    "title": title,
                    "publisher": publisher.strip(),
                    "link": link,
                    "pub_date": pub_date,
                }
            )
    return articles


def _in_window(pub_date, start_dt, end_dt) -> bool:
    """Keep dated articles inside the window; keep undated ones only for live runs."""
    if pub_date is not None:
        return start_dt <= pub_date <= end_dt + relativedelta(days=1)
    return end_dt >= datetime.now() - relativedelta(days=1)


def _render(articles: list[dict], start_dt, end_dt, limit: int) -> str:
    """Render windowed articles into the shared news report format. Returns body or ''."""
    out = ""
    kept = 0
    for art in articles:
        if not _in_window(art["pub_date"], start_dt, end_dt):
            continue
        out += format_news_headline(art["title"], art["publisher"], art["pub_date"]) + "\n"
        if art["link"]:
            out += f"Link: {art['link']}\n"
        out += "\n"
        kept += 1
        if kept >= limit:
            break
    return out


def get_news_google(ticker: str, start_date: str, end_date: str) -> str:
    """Ticker-specific news from Google News RSS (yfinance-compatible output)."""
    limit = get_config()["news_article_limit"]
    canonical = normalize_symbol(ticker)
    resolved = "" if canonical == ticker else f" (resolved to {canonical})"

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Scope the query to the company/ticker plus "stock" to bias toward markets.
    articles = _fetch_rss(f"{ticker} stock")
    if not articles:
        return f"No news found for {ticker}{resolved}"

    body = _render(articles, start_dt, end_dt, limit)
    if not body:
        return f"No news found for {ticker}{resolved} between {start_date} and {end_date}"
    return f"## {ticker}{resolved} News, from {start_date} to {end_date}:\n\n{body}"


def get_global_news_google(
    curr_date: str,
    look_back_days: int | None = None,
    limit: int | None = None,
) -> str:
    """Global/macro news from Google News RSS (yfinance-compatible output)."""
    config = get_config()
    if look_back_days is None:
        look_back_days = config["global_news_lookback_days"]
    if limit is None:
        limit = config["global_news_article_limit"]
    search_queries = config["global_news_queries"]

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    all_articles: list[dict] = []
    seen = set()
    for query in search_queries:
        for art in _fetch_rss(query):
            if art["title"] not in seen:
                seen.add(art["title"])
                all_articles.append(art)
        if len(all_articles) >= limit * 3:
            break

    if not all_articles:
        return f"No global news found for {curr_date}"

    body = _render(all_articles, start_dt, curr_dt, limit)
    if not body:
        return f"No global news found between {start_date} and {curr_date}"
    return f"## Global Market News, from {start_date} to {curr_date}:\n\n{body}"
