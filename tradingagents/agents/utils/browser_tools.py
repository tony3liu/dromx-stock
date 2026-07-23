"""Browser tools for the v0.4 agent loop — fill data gaps by reading a URL's
full text via the headless browser.

The project's data tools cover price / financials / news, but sometimes a
specific URL needs its full body read (an article beyond the ~200-char
snippet, an SEC filing, a data page no vendor covers). ``tradingagents.browser``
already exposes ``read_article`` (a plain function the news analyst's
pre-fetch uses); this wraps it as a ``@tool`` so the agent loop can call it
on demand. Best-effort: if the browser isn't enabled / the CLI is missing,
the tool returns an error string (the agent sees it and falls back) — never
raises, never blocks the run.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def web_read(url: str) -> str:
    """Read the full text of a web URL (article / filing / data page) via the
    headless browser. Use to deep-dive a news article's full body, read an
    SEC filing, or pull a data page the other tools don't cover. Needs the
    browser enabled (``enable_browser`` + the agent-browser CLI); returns an
    error string if unavailable — don't fabricate, fall back to the snippet.
    """
    try:
        from tradingagents.browser import browser_available, read_article
        if not browser_available():
            return (
                "<browser unavailable: set enable_browser=true and install the "
                "agent-browser CLI to use web_read>"
            )
        body = read_article(url)
        if not body:
            return f"<no readable content at {url}>"
        return body
    except Exception as exc:  # noqa: BLE001 — best-effort, never raises
        return f"<web_read failed: {type(exc).__name__}: {exc}>"


@tool
def web_search(query: str) -> str:
    """Search Google via the serper.dev API (real results, no headless-browser
    CAPTCHA). Returns titles + URLs + snippets for you to pick a URL to
    ``web_read`` for full content. Use when the data tools (get_news /
    get_stock_data / get_global_news) can't get the info — a pending event's
    outcome, a real-time price, a niche fact not in the fetched feeds. One
    search per gap, then ``web_read`` the best result. Needs SERPER_API_KEY
    in env (serper.dev, free tier); returns an error string if unavailable.
    """
    import json
    import os

    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return "<web_search unavailable: set SERPER_API_KEY env (serper.dev key)>"
    try:
        import requests

        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            data=json.dumps({"q": query, "hl": "zh-cn", "num": 8}),
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — best-effort, never raises
        return f"<web_search request failed: {type(exc).__name__}: {exc}>"
    results = (resp.json().get("organic") or [])[:8]
    if not results:
        return f"<no results for: {query}>"
    lines = []
    for r in results:
        lines.append(
            f"- {r.get('title', '')}\n  {r.get('link', '')}\n  {r.get('snippet', '')}"
        )
    return "\n".join(lines)[:6000]
