"""DromX Tools — 统一工具层

v0.5.0 架构升级：统一工具注册表，替代分散的 agents/utils/*_tools.py 和 assistant/tools/。

参考 Hermes Agent 的 `tools/registry.py` 设计：
- 自注册工具：每个 tool 文件在模块级别调用 `registry.register()`
- ToolEntry 元数据：name / toolset / schema / handler / description
- Toolset 分组：data / analysis / user / monitor
- Dispatch：统一执行，错误统一 JSON 化
- 可用性检查：check_fn + TTL 缓存
"""

from .registry import registry, ToolRegistry, tool_error, tool_result

# 导入所有 tool 模块，触发自注册
from . import data, analysis, user, monitor

__all__ = ["registry", "ToolRegistry", "tool_error", "tool_result", "data", "analysis", "user", "monitor"]
