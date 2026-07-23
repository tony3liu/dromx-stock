"""DromX Browser Module — "read the web" capability.

Lets Analysts read JS-rendered finance pages, full article bodies, and rendered
filing/announcement pages that the existing HTTP/API pipelines can't reach. It
is a SUPPLEMENT to the data pipelines, not a replacement — use it only when an
API can't return the content (see docs/requirements/browser-integration.md).

Backed by the ``agent-browser`` CLI (Node.js + Playwright Chromium); no paid API.
Everything degrades gracefully: if the CLI/Chromium is missing or a page fails,
functions return an error dict / ``"<read_article failed: ...>"`` placeholder and
never raise, so a DromX pipeline is never blocked.

Usage:
    from dromx.browser import read_article, navigate, eval_js
    text = read_article("https://finance.eastmoney.com/a/20250101.html")
"""

from __future__ import annotations

from dromx.browser._cli import find_agent_browser, run_browser_command
from dromx.browser._session import get_or_create_session
from dromx.browser._snapshot import truncate_snapshot

__all__ = [
    "navigate",
    "snapshot",
    "eval_js",
    "screenshot",
    "read_article",
    "browser_available",
]

_SNAPSHOT_MAX = 8000


def navigate(url: str, task_id: str = "default") -> dict:
    """Open ``url`` and return a compact page snapshot.

    Mirrors Hermes ``browser_navigate``: ``open`` the URL, then take a separate
    compact ``snapshot -c`` (the open response doesn't reliably carry one).
    Returns ``{"success", "url", "title", "snapshot"}`` or ``{"success": False,
    "error"}``.
    """
    session = get_or_create_session(task_id)
    opened = run_browser_command(session, "open", [url], timeout=60)
    if not opened.get("success"):
        return {"success": False, "error": opened.get("error", "Navigation failed")}

    data = opened.get("data", {})
    text = data.get("snapshot", "")
    if not text:
        snap = run_browser_command(session, "snapshot", ["-c"], timeout=30)
        if snap.get("success"):
            text = snap.get("data", {}).get("snapshot", "")
    if len(text) > _SNAPSHOT_MAX:
        text = truncate_snapshot(text, _SNAPSHOT_MAX)

    return {
        "success": True,
        "url": data.get("url", url),
        "title": data.get("title", ""),
        "snapshot": text,
    }


def snapshot(full: bool = False, task_id: str = "default") -> dict:
    """Refresh the current page snapshot. ``full=False`` → compact (-c)."""
    session = get_or_create_session(task_id)
    args = [] if full else ["-c"]
    result = run_browser_command(session, "snapshot", args)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Snapshot failed")}
    data = result.get("data", {})
    text = data.get("snapshot", "")
    if len(text) > _SNAPSHOT_MAX:
        text = truncate_snapshot(text, _SNAPSHOT_MAX)
    return {"success": True, "snapshot": text, "element_count": len(data.get("refs", {}) or {})}


def eval_js(expression: str, task_id: str = "default") -> dict:
    """Run JavaScript in the page context and return its (JSON-parsed) result."""
    session = get_or_create_session(task_id)
    result = run_browser_command(session, "eval", [expression], timeout=15)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Eval failed")}
    raw = result.get("data", {}).get("result")
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"success": True, "result": raw}


def screenshot(task_id: str = "default") -> dict:
    """Capture the current page; returns ``{"success", "path"}``."""
    session = get_or_create_session(task_id)
    result = run_browser_command(session, "screenshot", [], timeout=30)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Screenshot failed")}
    return {"success": True, "path": result.get("data", {}).get("path", "")}


def browser_available() -> bool:
    """True if the agent-browser CLI can be located (cheap, no launch)."""
    try:
        find_agent_browser()
        return True
    except FileNotFoundError:
        return False


# ── High-level API (for Analyst pre-fetch) ───────────────────────────────────

def read_article(url: str, task_id: str = "default") -> str:
    """Navigate to ``url`` and return the page's text snapshot.

    The Analyst pre-fetch entry point: wraps navigate + text extraction. Never
    raises — returns ``"<read_article failed: ...>"`` on error (follows the
    DromX ``_safe`` convention so it can be dropped straight into a
    prompt string).
    """
    result = navigate(url, task_id)
    if result.get("success"):
        return result.get("snapshot", "")
    return f"<read_article failed: {result.get('error', 'unknown')}>"
