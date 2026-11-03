"""Conversation manager — 多轮对话管理

管理用户会话历史，支持多轮对话、上下文记忆。
"""

from __future__ import annotations

import threading
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class ConversationManager:
    """多轮对话管理器"""

    def __init__(self, max_history: int = 20):
        self._sessions: dict[str, list[BaseMessage]] = {}
        self._max_history = max_history
        self._lock = threading.Lock()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到会话

        Args:
            session_id: 会话 ID
            role: "user" 或 "assistant"
            content: 消息内容
        """
        msg: BaseMessage
        if role == "user":
            msg = HumanMessage(content=content)
        else:
            msg = AIMessage(content=content)

        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(msg)
            # 限制历史长度
            if len(self._sessions[session_id]) > self._max_history:
                self._sessions[session_id] = self._sessions[session_id][-self._max_history:]

    def get_history(self, session_id: str) -> list[BaseMessage]:
        """获取会话历史"""
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> None:
        """清除会话历史"""
        with self._lock:
            self._sessions.pop(session_id, None)

    def has_session(self, session_id: str) -> bool:
        """检查会话是否存在"""
        with self._lock:
            return session_id in self._sessions
