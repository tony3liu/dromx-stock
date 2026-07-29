"""Web tools — 联网核实工具（搜索 / 网页读取 / 证券代码解析）

参考 Hermes Agent 的 `tools/web_tools.py` 设计：
- web_search 后端探测链：serper（SERPER_API_KEY）→ ddgs（pip 包，免 key）
  → 都没有时通过 check_fn 把工具从可用列表隐藏
- web_read 走 headless browser（独立的可用性检查，与搜索后端无关）
- resolve_ticker：Yahoo Finance `/v1/finance/search`，零 key，
  公司名/别名 → 代码 + 交易所（如「海力士」→ 000660.KS / SKHY），
  用于回答前核实证券代码，避免凭模型记忆断言
"""

from __future__ import annotations

import json
import logging
import os

from dromx.tools.registry import registry, tool_error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 后端可用性探测（Hermes 风格：env / 包存在与否决定后端链）
# ---------------------------------------------------------------------------

def _has_serper() -> bool:
    return bool(os.environ.get("SERPER_API_KEY"))


def _ddgs_importable() -> bool:
    try:
        import ddgs  # noqa: F401
        return True
    except ImportError:
        try:
            import duckduckgo_search  # noqa: F401
            return True
        except ImportError:
            return False


def _search_available() -> bool:
    return _has_serper() or _ddgs_importable()


def _browser_available() -> bool:
    try:
        from dromx.browser import browser_available

        return bool(browser_available())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# web_search：serper → ddgs 降级
# ---------------------------------------------------------------------------

def _search_serper(query: str, limit: int) -> str | None:
    """serper.dev Google 搜索；不可用/失败返回 None"""
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return None
    try:
        import requests

        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            data=json.dumps({"q": query, "hl": "zh-cn", "num": limit}),
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        logger.warning("serper search failed: %s", e)
        return None
    results = (resp.json().get("organic") or [])[:limit]
    if not results:
        return f"<no results for: {query}>"
    lines = []
    for r in results:
        lines.append(
            f"- {r.get('title', '')}\n  {r.get('link', '')}\n  {r.get('snippet', '')}"
        )
    return "\n".join(lines)[:6000]


def _search_ddgs(query: str, limit: int) -> str | None:
    """DuckDuckGo 搜索（免 key，需 ddgs/duckduckgo_search 包）；不可用返回 None"""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
    except ImportError:
        return None
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
    except Exception as e:  # noqa: BLE001
        logger.warning("ddgs search failed: %s", e)
        return None
    if not results:
        return f"<no results for: {query}>"
    lines = []
    for r in results:
        lines.append(
            f"- {r.get('title', '')}\n  {r.get('href', '')}\n  {r.get('body', '')}"
        )
    return "\n".join(lines)[:6000]


def _web_search(args: dict) -> str:
    query = (args.get("query") or "").strip()
    limit = int(args.get("limit") or 5)
    limit = max(1, min(limit, 20))
    if not query:
        return tool_error("Missing required param: query")

    # 后端链：serper → ddgs（Hermes：未显式配置时按可用性探测）
    for backend in (_search_serper, _search_ddgs):
        out = backend(query, limit)
        if out is not None:
            return out
    return tool_error(
        "web_search 不可用：请配置 SERPER_API_KEY（serper.dev，有免费额度）"
        "或安装 ddgs 包（pip install ddgs，免 key）"
    )


# ---------------------------------------------------------------------------
# web_read：headless browser 读网页正文
# ---------------------------------------------------------------------------

def _web_read(args: dict) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        return tool_error("Missing required param: url")
    try:
        from dromx.browser.tools import web_read

        return web_read.invoke({"url": url})
    except Exception as e:
        return tool_error(f"web_read failed: {e}")


# ---------------------------------------------------------------------------
# resolve_ticker：公司名/别名 → 证券代码（Yahoo Finance search，零 key）
# ---------------------------------------------------------------------------

def _yahoo_search(query: str, count: int) -> list[dict] | None:
    """Yahoo /v1/finance/search，query1 失败降级 query2（Hermes stocks skill 同款）"""
    import requests

    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            resp = requests.get(
                f"https://{host}/v1/finance/search",
                params={"q": query, "quotesCount": count, "newsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            return (resp.json().get("quotes") or [])[:count]
        except Exception as e:  # noqa: BLE001
            logger.debug("yahoo search via %s failed: %s", host, e)
    return None


def _resolve_ticker(args: dict) -> str:
    query = (args.get("query") or "").strip()
    count = int(args.get("count") or 5)
    count = max(1, min(count, 10))
    if not query:
        return tool_error("Missing required param: query")

    quotes = _yahoo_search(query, count)
    if quotes is None:
        return tool_error("ticker 解析失败：Yahoo Finance 搜索接口不可用（网络受限）")
    if not quotes:
        return tool_error(f"没有找到与 {query!r} 匹配的证券")

    results = []
    for q in quotes:
        results.append({
            "symbol": q.get("symbol"),
            "name": q.get("longname") or q.get("shortname"),
            "exchange": q.get("exchange") or q.get("exchDisp"),
            "type": q.get("quoteType"),
            "sector": q.get("sector"),
        })
    return json.dumps({"query": query, "results": results}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

registry.register(
    name="web_search",
    toolset="web",
    schema={
        "description": (
            "搜索互联网最新信息。返回标题 + URL + 摘要，可配合 web_read 读取全文。"
            "当问题涉及你不确定的事实时——某公司在哪个市场上市、股票代码、最新事件、"
            "实时数据——必须先搜索核实，不要凭记忆断言。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "limit": {"type": "integer", "description": "返回条数，默认 5，最大 20"},
            },
            "required": ["query"],
        },
    },
    handler=_web_search,
    check_fn=_search_available,
    description="搜索互联网（核实事实/最新信息）",
)

registry.register(
    name="web_read",
    toolset="web",
    schema={
        "description": "读取网页正文（新闻全文、公告、数据页）。通常配合 web_search：搜索后读取最相关的结果页面。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "网页 URL"},
            },
            "required": ["url"],
        },
    },
    handler=_web_read,
    check_fn=_browser_available,
    description="读取网页正文",
)

registry.register(
    name="resolve_ticker",
    toolset="web",
    schema={
        "description": (
            "把公司名/别名解析为证券代码和上市交易所（如『海力士』→ 000660.KS 韩股主板 "
            "/ SKHY 美股；『茅台』→ 600519.SS）。当用户提到公司名而非代码，或你不确定"
            "某公司是否在某个市场上市时，必须先调用此工具核实。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "公司名、别名或代码片段（英文名命中率最高，如海力士→SK Hynix）"},
                "count": {"type": "integer", "description": "返回条数，默认 5，最大 10"},
            },
            "required": ["query"],
        },
    },
    handler=_resolve_ticker,
    description="公司名 → 证券代码/交易所解析",
)
