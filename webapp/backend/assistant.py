"""Assistant API — 投研助手接口

提供 SSE 流式问答接口。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from webapp.backend import auth
from dromx.assistant.planner import AssistantPlanner
from dromx.assistant.conversation import ConversationManager
from dromx.tools.registry import registry

logger = logging.getLogger("dromx.web.assistant")

router = APIRouter()

# 全局单例
_conversation_manager = ConversationManager()
_planner: Optional[AssistantPlanner] = None


def _get_planner() -> AssistantPlanner:
    """获取或创建 AssistantPlanner 单例"""
    global _planner
    if _planner is None:
        from dromx.default_config import DEFAULT_CONFIG
        from dromx.llm_clients import create_llm_client

        cfg = DEFAULT_CONFIG.copy()
        client = create_llm_client(
            provider=cfg["llm_provider"],
            model=cfg["quick_think_llm"],
            base_url=cfg.get("backend_url"),
        )
        llm = client.get_llm()
        _planner = AssistantPlanner(llm=llm, conversation_manager=_conversation_manager)
    return _planner


@router.post("/api/assistant/ask")
async def ask(
    question: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    _: None = Depends(auth.require_auth),
):
    """投研助手问答接口（SSE 流式）

    Args:
        question: 用户问题
        session_id: 会话 ID（用于多轮对话）
        context: 额外上下文（如 ticker, holdings 等）

    取消语义：客户端断开 SSE（用户点停止/新对话/关页面）时，本请求的
    finally 会置位该 session 的 cancel_event —— planner 的流式循环和
    run_deep_analysis 等长工具在协作点检查该事件并尽快中止，避免继续烧 token。
    """
    import asyncio
    import queue
    import threading

    from dromx.assistant import cancel as cancel_mod

    async def event_gen():
        planner = _get_planner()
        # 没有 session_id 时用一次性 key，取消事件只对本次请求生效
        cancel_key = session_id or f"__anon_{id(question)}"
        cancel_event = cancel_mod.register(cancel_key)

        events: queue.Queue = queue.Queue()

        def worker():
            try:
                for event in planner.answer_stream(
                    question, session_id=session_id, context=context,
                    cancel_event=cancel_event,
                ):
                    events.put(event)
            except Exception as e:  # noqa: BLE001
                logger.exception("Assistant worker failed")
                events.put({"type": "error", "message": f"{type(e).__name__}: {e}"})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        loop = asyncio.get_running_loop()

        try:
            while True:
                event = await loop.run_in_executor(None, events.get)
                if event is None:
                    break
                etype = event.get("type")
                if etype == "error":
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "error",
                            "message": f"Assistant error: {event.get('message', '')}",
                        }, ensure_ascii=False),
                    }
                    return
                # status / delta / tool_start / tool_end / cancelled 直接透传
                yield {
                    "event": "message",
                    "data": json.dumps(event, ensure_ascii=False),
                }
                if etype in ("final", "cancelled"):
                    break
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "session_id": session_id,
                }, ensure_ascii=False),
            }
        finally:
            # 客户端断开 / 正常结束：置位取消事件，通知 worker 尽快停。
            # worker 是 daemon 线程，即使残留也不会阻塞进程退出。
            cancel_event.set()
            cancel_mod.clear(cancel_key)

    # ping=5：长工具调用期间每 5s 一次心跳，客户端断开能更快触发取消
    return EventSourceResponse(event_gen(), ping=5)


@router.get("/api/assistant/tools")
def list_tools(_: None = Depends(auth.require_auth)):
    """列出所有可用工具"""
    entries = registry.get_all_entries()
    return {
        "tools": [
            {
                "name": entry.name,
                "toolset": entry.toolset,
                "description": entry.description,
            }
            for entry in entries
        ]
    }


@router.get("/api/assistant/intents")
def list_intents(_: None = Depends(auth.require_auth)):
    """列出支持的意图分类"""
    planner = _get_planner()
    return {"intents": planner.get_supported_intents()}


@router.post("/api/assistant/clear")
def clear_conversation(
    session_id: str,
    _: None = Depends(auth.require_auth),
):
    """清除会话历史"""
    _conversation_manager.clear(session_id)
    return {"ok": True}
