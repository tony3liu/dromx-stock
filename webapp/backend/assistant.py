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
def ask(
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
    """
    def event_gen():
        try:
            planner = _get_planner()
            answer = planner.answer(question, session_id=session_id, context=context)

            # 发送回答（模拟流式，后续可以改成真流式）
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "delta",
                    "text": answer,
                }, ensure_ascii=False),
            }
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "session_id": session_id,
                }, ensure_ascii=False),
            }
        except Exception as e:
            logger.exception("Assistant ask failed")
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "message": f"Assistant error: {type(e).__name__}: {e}",
                }, ensure_ascii=False),
            }

    return EventSourceResponse(event_gen())


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
