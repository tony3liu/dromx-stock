"""Cancellation registry — 会话级协作式取消

前端断开 SSE（用户点停止/新对话/关页面）时，后端置位对应 session 的
``threading.Event``；长时间运行的工具（如 run_deep_analysis 的逐节点
graph stream）和 planner 的流式循环在协作点检查该事件并尽快中止，
避免白白烧 LLM token。

注意：Python 无法安全地强杀线程，所以这是协作式取消 —— 粒度是
「图节点 / LLM chunk / 工具调用」级别，无法中断单次进行中的 LLM 请求。
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_events: dict[str, threading.Event] = {}


def register(key: str) -> threading.Event:
    """为会话注册（或重置）一个取消事件"""
    with _lock:
        ev = threading.Event()
        _events[key] = ev
        return ev


def cancel(key: str) -> bool:
    """置位取消事件；会话不存在返回 False"""
    with _lock:
        ev = _events.get(key)
    if ev is None:
        return False
    ev.set()
    return True


def get(key: str) -> threading.Event | None:
    with _lock:
        return _events.get(key)


def clear(key: str) -> None:
    """清理会话的取消事件（请求结束后调用）"""
    with _lock:
        _events.pop(key, None)


class CancelledError(Exception):
    """协作式取消触发时抛出，工具层捕获后转成友好提示"""
