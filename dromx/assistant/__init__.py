"""DromX Assistant — 投研助手

v0.5.0 架构升级：从"固定流水线"到"投研助手 + 工具箱"。

核心组件：
- ``AssistantPlanner`` — 意图识别 + 工具规划 + 多轮对话
- ``ConversationManager`` — 多轮对话管理

使用统一的 `dromx.tools.registry` 作为工具注册表。
"""

from .planner import AssistantPlanner
from .conversation import ConversationManager

__all__ = ["AssistantPlanner", "ConversationManager"]
