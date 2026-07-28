"""DromX Assistant Tool Registry — 工具注册表（Hermes-inspired）

参考 Hermes Agent 的 `tools/registry.py` 设计：
- 自注册工具：每个 tool 文件在模块级别调用 `registry.register()`
- ToolEntry 元数据：name / toolset / schema / handler / description
- Toolset 分组：data / analysis / user / monitor
- Dispatch：统一执行，错误统一 JSON 化
- 可用性检查：check_fn + TTL 缓存（简化版）

与 Hermes 的区别：
- 去掉 plugin override policy（暂不需要）
- 去掉 MCP dynamic refresh（暂不需要）
- 简化 check_fn 缓存（保留 TTL，去掉 grace period）
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """单个注册工具的元数据"""

    name: str
    toolset: str
    schema: dict
    handler: Callable
    check_fn: Optional[Callable] = None
    description: str = ""
    requires_env: List[str] = field(default_factory=list)


class ToolRegistry:
    """工具注册表：收集 tool schema + handler

    每个 tool 文件在模块级别调用 `registry.register()` 注册自己。
    """

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._lock = threading.RLock()
        self._check_fn_cache: Dict[Callable, tuple[float, bool]] = {}
        self._check_fn_ttl = 30.0  # 30 秒缓存

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Optional[Callable] = None,
        description: str = "",
        requires_env: Optional[List[str]] = None,
    ) -> None:
        """注册工具。在 tool 文件的模块级别调用。

        Args:
            name: 工具名称（如 "get_stock_data"）
            toolset: 工具集（如 "data" / "analysis" / "user" / "monitor"）
            schema: OpenAI function-calling schema
            handler: 工具执行函数（接收 dict 参数，返回 str 或 dict）
            check_fn: 可用性检查函数（返回 bool）
            description: 工具描述（用于 LLM prompt）
            requires_env: 需要的环境变量列表
        """
        with self._lock:
            existing = self._tools.get(name)
            if existing and existing.toolset != toolset:
                logger.warning(
                    "Tool '%s': toolset '%s' overwriting existing toolset '%s'",
                    name, toolset, existing.toolset,
                )
            self._tools[name] = ToolEntry(
                name=name,
                toolset=toolset,
                schema=schema,
                handler=handler,
                check_fn=check_fn,
                description=description or schema.get("description", ""),
                requires_env=requires_env or [],
            )

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """按名称获取工具元数据"""
        with self._lock:
            return self._tools.get(name)

    def get_all_entries(self) -> List[ToolEntry]:
        """获取所有工具元数据"""
        with self._lock:
            return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return sorted(entry.name for entry in self.get_all_entries())

    def get_toolsets(self) -> List[str]:
        """获取所有工具集名称"""
        return sorted({entry.toolset for entry in self.get_all_entries()})

    def get_tools_by_toolset(self, toolset: str) -> List[ToolEntry]:
        """按工具集获取工具"""
        return [entry for entry in self.get_all_entries() if entry.toolset == toolset]

    def _check_fn_cached(self, fn: Callable) -> bool:
        """可用性检查（TTL 缓存）"""
        now = time.monotonic()
        with self._lock:
            cached = self._check_fn_cache.get(fn)
            if cached is not None:
                ts, value = cached
                if now - ts < self._check_fn_ttl:
                    return value
        try:
            value = bool(fn())
        except Exception:
            value = False
        with self._lock:
            self._check_fn_cache[fn] = (now, value)
        return value

    def get_definitions_description(self) -> str:
        """获取所有工具的描述（用于 LLM prompt）"""
        lines = []
        for entry in self.get_all_entries():
            desc = entry.description or entry.schema.get("description", "")
            lines.append(f"- {entry.name}: {desc}")
        return "\n".join(lines)

    def get_definitions(self, tool_names: Optional[List[str]] = None) -> List[dict]:
        """返回 OpenAI-format tool schemas

        Args:
            tool_names: 要返回的工具名称列表；None 表示全部可用工具
        """
        entries = self.get_all_entries()
        if tool_names is not None:
            entries = [e for e in entries if e.name in tool_names]

        result = []
        for entry in entries:
            if entry.check_fn and not self._check_fn_cached(entry.check_fn):
                continue
            schema_with_name = {**entry.schema, "name": entry.name}
            result.append({"type": "function", "function": schema_with_name})
        return result

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """执行工具

        Args:
            name: 工具名称
            args: 工具参数（dict）
            **kwargs: 额外参数（如 llm, config 等）

        Returns:
            JSON 字符串（成功或错误）
        """
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

        try:
            result = entry.handler(args, **kwargs)
            # 统一返回 JSON 字符串
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.exception("Tool %s dispatch error: %s", name, e)
            return json.dumps(
                {"error": f"Tool execution failed: {type(e).__name__}: {e}"},
                ensure_ascii=False,
            )


# 模块级单例
registry = ToolRegistry()


# 便捷函数：tool_error / tool_result（Hermes 风格）

def tool_error(message: str, **extra) -> str:
    """返回 JSON 错误字符串"""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data=None, **kwargs) -> str:
    """返回 JSON 结果字符串"""
    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return json.dumps(kwargs, ensure_ascii=False)
