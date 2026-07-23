"""X (Twitter) public-post sentiment via Google's index.

X has no free, keyless, searchable API in 2026: Nitter instances have shut
down, the syndication API does not expose search (and rate-limits server
IPs), and Scweet / the official API both require credentials. As a pragmatic
fallback we surface PUBLIC X posts that Google has indexed, by scoping a
Google News RSS query to ``site:x.com``/``site:twitter.com``. Each RSS item's
title is the post text and the source is ``x.com``.

This is a discovery feed, not a full firehose: it returns whatever Google has
indexed for the query, not every tweet, and carries no like/retweet counts.
It needs no API key and does not rate-limit the way the X endpoints do, which
is the trade-off we accept here.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)

_RSS_URL = "https://news.google.com/rss/search"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TradingAgents/1.0)"}
_TIMEOUT = 15


def fetch_x_posts(ticker: str, limit: int = 30, timeout: float = _TIMEOUT) -> str:
    """Fetch public X posts about ``ticker`` indexed by Google.

    Returns a formatted plaintext block ready for prompt injection, or a clear
    placeholder string on any failure / empty result — the caller never has to
    special-case None or exceptions (matches ``fetch_stocktwits_messages``).
    """
    query = f"{ticker} stock (site:x.com OR site:twitter.com)"
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    try:
        resp = requests.get(_RSS_URL, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError) as exc:
        logger.warning("X (Google-indexed) fetch failed for %s: %s", ticker, exc)
        return f"<X posts unavailable: {type(exc).__name__}>"

    items = root.findall(".//item")
    if not items:
        return f"<no X posts found for {ticker}>"

    lines = []
    for item in items[:limit]:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        source_el = item.find("source")
        author = (source_el.text if source_el is not None else "x.com") or "x.com"
        pub_raw = item.findtext("pubDate")
        when = ""
        if pub_raw:
            try:
                when = parsedate_to_datetime(pub_raw).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                when = ""
        # Google often appends " - <publisher>" to titles; keep it, it names
        # the X account / outlet.
        lines.append(f"[{when} · {author}] {title}")

    if not lines:
        return f"<no X posts found for {ticker}>"

    header = (
        f"Public X (Twitter) posts about {ticker} indexed by Google "
        f"({len(lines)} most-relevant). Discovery feed — no engagement metrics, "
        f"not exhaustive. Retrieved {datetime.now().strftime('%Y-%m-%d')}."
    )
    return header + "\n\n" + "\n".join(lines)
