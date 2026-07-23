"""@tool wrappers for the sentiment data sources (v0.4 M3).

The sentiment analyst's three social sources (StockTwits / Reddit / X) are
plain functions in ``dataflows`` — they pre-fetch into the prompt in v0.3.
For the v0.4 agent loop the analyst needs them as callable tools so it can
re-fetch or widen a source mid-loop ("StockTwits looks thin — pull more").
Each wrapper delegates to the underlying function and returns its plaintext
block, so the loop sees the same shape the pre-fetch produced. Best-effort:
a fetch failure returns a placeholder string, never raises.
"""

from __future__ import annotations

from langchain_core.tools import tool

from tradingagents.dataflows.reddit import fetch_reddit_posts
from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
from tradingagents.dataflows.x_twitter import fetch_x_posts


@tool
def fetch_stocktwits_tool(ticker: str, limit: int = 30) -> str:
    """Fetch recent StockTwits messages for the ticker.

    Retail-trader posts indexed by cashtag, each with a user-labeled
    Bullish/Bearish tag. Returns a plaintext block; use the Bullish/Bearish
    ratio as a leading retail-sentiment signal.
    """
    try:
        return fetch_stocktwits_messages(ticker, limit=limit)
    except Exception as exc:  # noqa: BLE001 — best-effort, never raises
        return f"<stocktwits unavailable: {type(exc).__name__}: {exc}>"


@tool
def fetch_reddit_tool(ticker: str) -> str:
    """Fetch Reddit posts (r/wallstreetbets, r/stocks, r/investing) for the ticker.

    Returns a plaintext block with post title + body excerpt + score/comment
    count. Weight by engagement (a 400-upvote thread vs a 3-upvote post).
    """
    try:
        return fetch_reddit_posts(ticker)
    except Exception as exc:  # noqa: BLE001
        return f"<reddit unavailable: {type(exc).__name__}: {exc}>"


@tool
def fetch_x_posts_tool(ticker: str, limit: int = 30) -> str:
    """Fetch public X (Twitter) posts about the ticker, indexed by Google.

    A discovery feed (not an exhaustive firehose, no like/retweet counts).
    Treat as opinion; corroborate against StockTwits/Reddit rather than any
    single post.
    """
    try:
        return fetch_x_posts(ticker, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return f"<x unavailable: {type(exc).__name__}: {exc}>"
