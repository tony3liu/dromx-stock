"""Tool registry — 工具注册表

管理所有可用工具，按意图分类。支持：
- 数据工具（get_stock_data / get_news / get_indicators 等）
- 分析工具（run_deep_analysis / run_backtest / run_screener 等）
- 用户工具（get_my_portfolio / get_my_position / analyze_my_operation 等）
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool


class ToolRegistry:
    """工具注册表：管理所有可用工具"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._intent_map: dict[str, list[str]] = {}  # intent → tool names

    def register(self, tool: BaseTool, intents: list[str] | None = None) -> None:
        """注册工具

        Args:
            tool: LangChain tool 实例
            intents: 该工具支持的意图列表（如 ["sector_question", "capital_rotation"]）
        """
        self._tools[tool.name] = tool
        for intent in intents or []:
            self._intent_map.setdefault(intent, []).append(tool.name)

    def get_tool(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def get_tools_for_intent(self, intent: str) -> list[BaseTool]:
        """根据意图获取工具"""
        names = self._intent_map.get(intent, [])
        return [self._tools[n] for n in names if n in self._tools]

    def get_all_tools(self) -> list[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_all_intents(self) -> list[str]:
        """获取所有意图"""
        return list(self._intent_map.keys())

    def get_tools_description(self) -> str:
        """获取所有工具的描述（用于 LLM prompt）"""
        lines = []
        for name, tool in self._tools.items():
            desc = getattr(tool, "description", "") or ""
            lines.append(f"- {name}: {desc.split(chr(10))[0]}")
        return "\n".join(lines)
