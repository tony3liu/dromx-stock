"""Jin10 (金十数据) MCP vendor — 全球宏观快讯 / 财经日历

官方 MCP 服务（https://mcp.jin10.com/mcp，Bearer Token）的极简同步客户端，
协议为 MCP streamable-HTTP：JSON-RPC POST → SSE 响应。

- initialize → notifications/initialized → tools/call
- 响应是 text/event-stream，取第一个 message 事件的 data 载荷
- 会话 ID 由响应头 mcp-session-id 携带，进程内复用
- 连接级失败走与 google_news 相同的熔断模式（TTL 内直接抛错跳过，
  让 route_to_vendor 立即降级到 google/eastmoney 等备用源）

环境变量（任一即可）：``jin10_token`` / ``JIN10_BEARER_TOKEN`` / ``JIN10_TOKEN``
未配置时抛 VendorNotConfiguredError，vendor router 自动跳过本源。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any

import requests
from dateutil.relativedelta import relativedelta

from .config import get_config
from .errors import VendorNotConfiguredError
from .utils import format_news_headline

logger = logging.getLogger(__name__)

_SERVER_URL = os.environ.get("JIN10_MCP_SERVER_URL", "https://mcp.jin10.com/mcp")
_PROTOCOL_VERSION = os.environ.get("JIN10_MCP_PROTOCOL_VERSION", "2025-11-25")
_TIMEOUT = 20

# 熔断器（与 google_news 同款）：连接级失败说明服务不可达/网络受限，
# TTL 内直接抛错，避免每次白等超时
_CIRCUIT_TTL_SECONDS = 1800
_circuit_open_until = 0.0

# 进程内 MCP 会话（initialize 一次，复用 session id）
_session_id: str | None = None
_request_id = 0
_lock = threading.Lock()


# 直连会话：macOS 系统代理/VPN 对国内服务（mcp.jin10.com）会间歇性
# SSL 重置，trust_env=False 忽略系统/环境代理，强制直连
_SESSION = requests.Session()
_SESSION.trust_env = False


class Jin10UnreachableError(Exception):
    """金十 MCP 服务不可达（熔断器开启或连接失败）"""


def _get_token() -> str:
    for name in ("jin10_token", "JIN10_BEARER_TOKEN", "JIN10_TOKEN"):
        token = os.environ.get(name, "").strip()
        if token:
            return token
    raise VendorNotConfiguredError(
        "jin10 token not configured (set jin10_token in .env)"
    )


def _next_id() -> int:
    global _request_id
    _request_id += 1
    return _request_id


def _check_circuit() -> None:
    if time.monotonic() < _circuit_open_until:
        raise Jin10UnreachableError(
            "jin10 MCP unreachable (circuit open, "
            f"{int(_circuit_open_until - time.monotonic())}s left)"
        )


def _trip_circuit(exc: Exception) -> None:
    global _circuit_open_until
    _circuit_open_until = time.monotonic() + _CIRCUIT_TTL_SECONDS
    logger.warning(
        "Jin10 MCP unreachable (%s); circuit open for %ds",
        exc, _CIRCUIT_TTL_SECONDS,
    )


def _parse_sse(text: str) -> dict:
    """从 SSE 响应中取第一个 message 事件的 JSON 载荷"""
    for block in text.replace("\r\n", "\n").split("\n\n"):
        data_lines = [
            ln[5:].lstrip() for ln in block.split("\n") if ln.startswith("data:")
        ]
        if not data_lines:
            continue
        try:
            return json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
    raise Jin10UnreachableError(f"no JSON-RPC message in SSE response: {text[:200]}")


def _post_rpc(body: dict, *, expect_response: bool = True) -> Any:
    """发一次 JSON-RPC；连接失败开熔断并重抛"""
    global _session_id
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {_get_token()}",
    }
    if _session_id:
        headers["Mcp-Session-Id"] = _session_id

    try:
        # 通知类请求（expect_response=False）：金十对 notifications 不回包，
        # 用短超时 + 忽略超时，当作 fire-and-forget
        timeout = _TIMEOUT if expect_response else 5
        last_exc: requests.RequestException | None = None
        for _attempt in range(2):  # 网络抖动重试一次
            try:
                resp = _SESSION.post(_SERVER_URL, headers=headers, json=body, timeout=timeout)
                break
            except requests.RequestException as exc:
                last_exc = exc
                continue
        else:
            raise last_exc  # type: ignore[misc]
    except requests.ReadTimeout:
        if not expect_response:
            return None  # 通知不回包属正常，直接视为成功
        raise
    except requests.RequestException as exc:
        # 连接级失败才开熔断（ReadTimeout 是服务慢，不是不可达）
        if isinstance(exc, (requests.ConnectTimeout, requests.ConnectionError)):
            _trip_circuit(exc)
        raise

    sid = resp.headers.get("mcp-session-id")
    if sid:
        _session_id = sid

    if not expect_response:
        return None
    if resp.status_code == 401:
        raise VendorNotConfiguredError("jin10 token rejected (401 Unauthorized)")
    if not resp.ok:
        raise Jin10UnreachableError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    if "text/event-stream" not in (resp.headers.get("content-type") or ""):
        raise Jin10UnreachableError(f"unexpected content-type: {resp.headers.get('content-type')}")

    # SSE 无 charset 时 requests 默认按 ISO-8859-1 解码，中文快讯会变乱码
    resp.encoding = "utf-8"
    rpc = _parse_sse(resp.text)
    if rpc.get("error"):
        err = rpc["error"]
        raise Jin10UnreachableError(f"JSON-RPC error {err.get('code')}: {err.get('message')}")
    return rpc.get("result")


def _ensure_session() -> None:
    """MCP 握手（进程内一次）"""
    global _session_id
    with _lock:
        if _session_id:
            return
        _check_circuit()
        _post_rpc({
            "jsonrpc": "2.0",
            "id": _next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "dromx", "version": "1.0.0"},
            },
        })
        _post_rpc(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            expect_response=False,
        )
        logger.info("Jin10 MCP session established")


def call_tool(name: str, arguments: dict | None = None) -> Any:
    """调用金十 MCP 工具，返回结构化数据（session 失效自动重连一次）"""
    _check_circuit()
    for attempt in (1, 2):
        try:
            _ensure_session()
            result = _post_rpc({
                "jsonrpc": "2.0",
                "id": _next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            })
            if isinstance(result, dict) and result.get("isError"):
                raise Jin10UnreachableError(
                    f"tool {name} error: {json.dumps(result.get('content'))[:200]}"
                )
            return _pick_primary_data(result)
        except Jin10UnreachableError:
            if attempt == 1:
                # session 可能过期：清空重连一次
                with _lock:
                    globals()["_session_id"] = None
                continue
            raise
    return None  # unreachable


def _pick_primary_data(result: Any) -> Any:
    """tools/call 结果 → 结构化数据（structuredContent 优先，其次 content[0].text 的 JSON）"""
    if isinstance(result, dict):
        if "structuredContent" in result:
            return result["structuredContent"]
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        return json.loads(item.get("text") or "")
                    except (json.JSONDecodeError, TypeError):
                        return item.get("text")
    return result


def _as_list(data: Any, *keys: str) -> list[dict]:
    """从工具返回里宽松地取出条目列表（兼容 {data:{items:[...]}} 信封）"""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in keys or ("items", "data", "list", "flash", "news"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                inner = _as_list(v)
                if inner:
                    return inner
    return []


def _parse_pub(item: dict) -> datetime | None:
    """宽松解析快讯时间字段（支持 ISO 字符串 / 秒 / 毫秒时间戳）"""
    raw = (
        item.get("time") or item.get("pub_time") or item.get("created_at")
        or item.get("datetime") or item.get("date")
    )
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        ts = raw / 1000 if raw > 1e12 else raw
        try:
            return datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def get_global_news(
    curr_date: str,
    look_back_days: int | None = None,
    limit: int | None = None,
) -> str:
    """金十 7x24 快讯（google_news/eastmoney_news 兼容输出）。

    时效性最强的中文宏观快讯源（非农/CPI/央行决议等）。连接失败抛异常，
    让 vendor router 降级到 google/eastmoney。
    """
    config = get_config()
    if look_back_days is None:
        look_back_days = config["global_news_lookback_days"]
    if limit is None:
        limit = config["global_news_article_limit"]

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    data = call_tool("list_flash", {})
    items = _as_list(data)

    body = ""
    kept = 0
    for item in items:
        pub = _parse_pub(item)
        if pub is not None and not (start_dt <= pub <= curr_dt + relativedelta(days=1)):
            continue
        title = (
            item.get("content") or item.get("title") or item.get("text") or ""
        ).strip()
        if not title:
            continue
        # 快讯 content 可能很长，截到一句
        first_line = title.splitlines()[0].strip()
        important = item.get("important") in (1, True, "1")
        prefix = "【重要】" if important else ""
        body += format_news_headline(prefix + first_line[:200], "金十快讯", pub) + "\n\n"
        kept += 1
        if kept >= limit:
            break

    if not body:
        return f"No global news found between {start_date} and {curr_date}"
    return f"## Global Market News, from {start_date} to {curr_date}:\n\n{body}"
